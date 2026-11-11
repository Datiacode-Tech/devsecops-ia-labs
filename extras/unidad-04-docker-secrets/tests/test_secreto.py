"""Pruebas del Ejemplo 4. Se ejecutan dentro del contenedor api-secreto:

    docker compose -f compose.secrets-demo.yaml run --rm --no-deps -v ./tests:/demo/tests:ro api-secreto python -m pytest -q -p no:cacheprovider /demo/tests

Ninguna aserción incluye el valor de la clave: se comparan resultados booleanos para que
pytest no lo muestre si una prueba falla. Las comprobaciones de los metadatos del contenedor
(docker inspect) se hacen desde el equipo con scripts/verificar.sh o scripts/verificar.ps1.
"""
import hmac
import logging
import os
from pathlib import Path

import pytest

RUTA = Path('/run/secrets/demo_api_key')
pytestmark = pytest.mark.skipif(not RUTA.exists(), reason='solo dentro del contenedor api-secreto')


class Oculto(str):
    """Cadena que pytest muestra como '***' (por ejemplo, con --showlocals)."""
    def __repr__(self) -> str:
        return "'***'"


def leer_secreto() -> Oculto:
    return Oculto(RUTA.read_text(encoding='utf-8').strip())


def test_secret_file_is_mounted_and_readable():
    montado = any(linea.split()[1] == str(RUTA) for linea in Path('/proc/self/mounts').read_text().splitlines())
    assert RUTA.is_file(), 'no existe /run/secrets/demo_api_key'
    assert montado, 'el secreto no aparece como punto de montaje'
    assert os.access(RUTA, os.R_OK), 'el proceso no puede leer el secreto'
    assert len(leer_secreto()) >= 16, 'el secreto está vacío o es demasiado corto'


def test_app_uses_the_secret_file():
    from app import main
    coincide = hmac.compare_digest(main.CLAVE, leer_secreto())
    assert main.ORIGEN == 'secreto'
    assert coincide, 'la aplicación no usa el contenido del secreto'


def test_key_is_not_in_environment():
    clave = leer_secreto()
    variable_definida = 'DEMO_API_KEY' in os.environ
    en_algun_valor = any(clave in valor for valor in os.environ.values())
    en_pid1 = clave.encode() in Path('/proc/1/environ').read_bytes()
    assert not variable_definida, 'DEMO_API_KEY está definida como variable de entorno'
    assert not en_algun_valor, 'la clave aparece en una variable de entorno'
    assert not en_pid1, 'la clave aparece en el entorno del proceso principal'


@pytest.fixture
def cliente():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_authentication_401_401_200(cliente):
    sin_clave = cliente.get('/protegido')
    incorrecta = cliente.get('/protegido', headers={'x-api-key': 'clave-incorrecta-de-prueba'})
    correcta = cliente.get('/protegido', headers={'x-api-key': leer_secreto()})
    assert (sin_clave.status_code, incorrecta.status_code, correcta.status_code) == (401, 401, 200)
    assert correcta.json() == {'mensaje': 'Acceso autorizado', 'origen_clave': 'secreto'}


def test_key_is_not_in_responses_or_logs(cliente, caplog, capfd):
    clave = leer_secreto()
    caplog.set_level(logging.DEBUG)
    cuerpos = [cliente.get(ruta, headers=cab).text for ruta, cab in [
        ('/health', {}), ('/protegido', {}), ('/protegido', {'x-api-key': 'x' * 20}), ('/protegido', {'x-api-key': clave})]]
    salida = capfd.readouterr()
    en_respuestas = any(clave in c for c in cuerpos)
    en_registros = clave in caplog.text or clave in salida.out or clave in salida.err
    assert caplog.text, 'no se ha capturado ningún registro'
    assert not en_respuestas, 'la clave aparece en una respuesta'
    assert not en_registros, 'la clave aparece en los registros'
