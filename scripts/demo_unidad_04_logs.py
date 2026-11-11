"""Ejemplo 4 de la Unidad 4: un registro mal diseñado frente a uno protegido.

Usa una clave FICTICIA generada al vuelo. No lee la DEMO_API_KEY real, no escribe ficheros
y todo desaparece al terminar el contenedor.

Uso (desde la carpeta del proyecto, igual en WSL/Linux y PowerShell):
    docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro api python -m scripts.demo_unidad_04_logs
"""
import io
import logging
import secrets
from app.log_redaction import SecretRedactionFilter

clave_ficticia = 'ficticia-' + secrets.token_urlsafe(12)
cabeceras = {'accept': 'application/json', 'x-api-key': clave_ficticia, 'user-agent': 'curl/8.5'}

def registrar(nombre: str, filtro: logging.Filter | None, mensaje: str, *args) -> str:
    """Registra un mensaje en un logger aislado y devuelve lo que se habría escrito."""
    salida = io.StringIO()
    manejador = logging.StreamHandler(salida)
    manejador.setFormatter(logging.Formatter('%(levelname)s %(name)s - %(message)s'))
    logger = logging.getLogger(nombre)
    logger.handlers, logger.propagate = [manejador], False
    logger.setLevel(logging.INFO)
    if filtro:
        logger.addFilter(filtro)
    logger.info(mensaje, *args)
    return salida.getvalue().strip()

casos = [
    ('1. Mal diseño: se registran todas las cabeceras',
     registrar('demo.inseguro', None, 'Petición recibida con cabeceras %s', cabeceras)),
    ('2. Mismo registro con el filtro de redacción de la API',
     registrar('demo.filtrado', SecretRedactionFilter(lambda: [clave_ficticia]), 'Petición recibida con cabeceras %s', cabeceras)),
    ('3. Diseño correcto: se registra el hecho, no el valor',
     registrar('demo.correcto', None, 'Petición recibida: credencial %s', 'presente' if cabeceras.get('x-api-key') else 'ausente')),
]
for titulo, linea in casos:
    print(titulo)
    print('   ', linea)
    print('    ¿Contiene la clave ficticia?', 'SÍ' if clave_ficticia in linea else 'no')
