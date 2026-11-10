import hmac
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.config import API_KEY

# Esquema de seguridad integrado de FastAPI: Swagger muestra el botón «Authorize»
# y documenta la cabecera. auto_error=False para devolver siempre nuestro 401.
api_key_header = APIKeyHeader(
    name='x-api-key',
    auto_error=False,
    description='Clave del laboratorio definida en DEMO_API_KEY (fichero .env).',
)

def require_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Dependencia reutilizable: exige una API key válida y devuelve la identidad.

    Autentica, pero no autoriza por tenant: todas las peticiones válidas se atribuyen
    a la misma identidad ficticia del laboratorio.
    """
    # Comparación en tiempo constante; se comparan bytes para admitir cualquier carácter.
    if api_key is None or not hmac.compare_digest(api_key.encode('utf-8'), API_KEY.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credencial ausente o incorrecta',
            headers={'WWW-Authenticate': 'ApiKey'},
        )
    return 'empresa-a'
