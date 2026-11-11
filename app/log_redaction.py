"""Redacción de credenciales en los registros (Unidad 4).

Primera regla: no registrar cabeceras ni variables de entorno completas.
Segunda línea de defensa: este filtro sustituye por [REDACTADO] cualquier aparición
de la clave configurada o de una credencial con nombre conocido antes de escribir el registro.
"""
import logging
import re
from collections.abc import Callable, Iterable

REDACTED = '[REDACTADO]'

# Nombre de credencial seguido de su valor: «x-api-key: valor», «'x-api-key': 'valor'»,
# «DEMO_API_KEY=valor», «authorization: Bearer valor».
_CREDENTIAL = re.compile(
    r"""(?P<name>x-api-key|demo_api_key|authorization)(?P<sep>['"]?\s*[:=]\s*['"]?)(?P<value>(?:bearer\s+)?[^\s'",;}]+)""",
    re.IGNORECASE,
)

# Loggers de la aplicación y de uvicorn (servidor y registro de accesos).
PROTECTED_LOGGERS = ('lab', 'uvicorn', 'uvicorn.error', 'uvicorn.access')

def redact(text: str, secrets: Iterable[str] = ()) -> str:
    """Devuelve el texto sin los valores secretos indicados ni credenciales con nombre conocido."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return _CREDENTIAL.sub(lambda m: m.group('name') + m.group('sep') + REDACTED, text)

class SecretRedactionFilter(logging.Filter):
    """Filtro de logging que elimina credenciales del mensaje antes de escribirlo."""

    def __init__(self, secrets: Callable[[], Iterable[str]]):
        super().__init__()
        # Se consulta en cada registro: tras una rotación se protege la clave nueva.
        self._secrets = secrets

    def filter(self, record: logging.LogRecord) -> bool:
        secrets = [s for s in self._secrets() if s]
        message = record.getMessage()
        clean = redact(message, secrets)
        if clean != message and not self._redact_args(record, secrets, clean):
            record.msg, record.args = clean, ()
        if record.exc_info and not record.exc_text:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info), secrets)
        return True

    @staticmethod
    def _redact_args(record: logging.LogRecord, secrets: list[str], clean: str) -> bool:
        """Limpia mensaje y argumentos por separado si así se obtiene el mismo resultado.

        Conserva la estructura mensaje + argumentos que esperan algunos formateadores,
        como el del registro de accesos de uvicorn.
        """
        if not isinstance(record.args, tuple) or not record.args:
            return False
        msg = redact(str(record.msg), secrets)
        args = tuple(redact(a, secrets) if isinstance(a, str) else a for a in record.args)
        try:
            if msg % args != clean:
                return False
        except (TypeError, ValueError):
            return False
        record.msg, record.args = msg, args
        return True

def install_redaction(secrets: Callable[[], Iterable[str]], loggers: Iterable[str] = PROTECTED_LOGGERS) -> SecretRedactionFilter:
    """Instala el filtro en los loggers indicados y en sus manejadores (idempotente)."""
    redaction = SecretRedactionFilter(secrets)
    lab = logging.getLogger('lab')
    if not lab.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s:     %(name)s - %(message)s'))
        lab.addHandler(handler)
        lab.setLevel(logging.INFO)
    for name in loggers:
        logger = logging.getLogger(name)
        targets = [logger, *logger.handlers]
        for target in targets:
            if not any(isinstance(f, SecretRedactionFilter) for f in target.filters):
                target.addFilter(redaction)
    return redaction
