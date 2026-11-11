"""Simula la incidencia del ejercicio de la Unidad 4 y escribe el informe en la salida estándar.

Todas las credenciales son ficticias: se generan al vuelo en cada ejecución, no sirven para
nada y no se guardan en ningún fichero. No lee la DEMO_API_KEY real del contenedor.

Uso (desde la carpeta del proyecto, igual en WSL/Linux y PowerShell):
    docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro api python -m scripts.incidencia_unidad_04
"""
import secrets
from app.soporte import generar_informe

entorno_ficticio = {
    'DEMO_API_KEY': secrets.token_urlsafe(24),
    'LLM_PROVIDER_TOKEN': 'tok_' + secrets.token_hex(20),
    'MODEL_URL': 'http://mock-llm:8100/respond',
    'TOOLS_URL': 'http://tools:8200/execute',
    'PYTHON_VERSION': '3.12',
    'HOSTNAME': 'api-incidencia',
}
cabeceras_ficticias = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'user-agent': 'cliente-interno/1.4',
    'x-api-key': entorno_ficticio['DEMO_API_KEY'],
    'authorization': 'Bearer ' + secrets.token_urlsafe(32),
}

print(generar_informe(entorno_ficticio, cabeceras_ficticias, 'Proveedor simulado no disponible (HTTP 503)'), end='')
