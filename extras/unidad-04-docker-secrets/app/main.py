"""Ejemplo 4 (Unidad 4): API mínima que lee su API key de un secreto de Docker Compose.

Aplicación independiente del laboratorio principal, con la misma idea que app/security.py
(cabecera x-api-key, comparación en tiempo constante y 401 único):
- Opción B (servicio api-secreto): lee la clave de /run/secrets/demo_api_key.
- Opción A (servicio api-entorno, solo para comparar): no hay fichero de secreto y la lee
  de la variable de entorno DEMO_API_KEY.
Ninguna respuesta ni ningún registro incluye el valor de la clave.
"""
import hmac
import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader

RUTA_SECRETO = Path('/run/secrets/demo_api_key')
LONGITUD_MINIMA = 16

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
log = logging.getLogger('demo_secretos')


def cargar_clave() -> tuple[str, str]:
    """Devuelve (clave, origen). Si falta o es demasiado corta, la API no arranca."""
    if RUTA_SECRETO.is_file():
        clave, origen = RUTA_SECRETO.read_text(encoding='utf-8').strip(), 'secreto'
    else:
        clave, origen = os.getenv('DEMO_API_KEY', '').strip(), 'entorno'
    if len(clave) < LONGITUD_MINIMA:
        # El mensaje nunca incluye el valor leído.
        raise RuntimeError(
            f'Clave ausente o de menos de {LONGITUD_MINIMA} caracteres (origen: {origen}). '
            'Genera secrets/demo_api_key.txt siguiendo el README del ejemplo.'
        )
    return clave, origen


CLAVE, ORIGEN = cargar_clave()
log.info('Clave cargada desde: %s', ORIGEN)

app = FastAPI(title='Ejemplo 4 · Docker Secrets', version='1.0')
cabecera = APIKeyHeader(name='x-api-key', auto_error=False)


def exigir_clave(clave: str | None = Security(cabecera)) -> None:
    if clave is None or not hmac.compare_digest(clave.encode('utf-8'), CLAVE.encode('utf-8')):
        log.warning('Petición rechazada: credencial ausente o incorrecta')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credencial ausente o incorrecta',
            headers={'WWW-Authenticate': 'ApiKey'},
        )


@app.get('/health')
def health():
    return {'status': 'ok', 'origen_clave': ORIGEN}


@app.get('/protegido', dependencies=[Depends(exigir_clave)])
def protegido():
    log.info('Petición autenticada')
    return {'mensaje': 'Acceso autorizado', 'origen_clave': ORIGEN}
