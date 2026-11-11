import json
import os
from pathlib import Path

STAGE = json.loads(Path(__file__).resolve().parents[1].joinpath('course_stage.json').read_text(encoding='utf-8'))['stage']

API_KEY_ENV = 'DEMO_API_KEY'
API_KEY_PLACEHOLDER = 'cambia-esta-clave'
API_KEY_MIN_LENGTH = 16
API_KEY_MIN_DISTINCT_CHARS = 8

# Fragmentos de valores de ejemplo, de documentación o fáciles de adivinar. Una clave que
# los contenga no se acepta aunque sea larga (comparación sin distinguir mayúsculas).
INSECURE_KEY_FRAGMENTS = (
    API_KEY_PLACEHOLDER,
    'curso-demo-key',
    'changeme',
    'password',
    'contrasena',
    'secreto',
    'example',
    'ejemplo',
)

def api_key_problem(key: str) -> str | None:
    """Devuelve el motivo por el que una clave no es aceptable, o None si es válida.

    El motivo nunca incluye el valor recibido.
    """
    if not key:
        return 'ausente'
    if len(key) < API_KEY_MIN_LENGTH:
        return 'longitud insuficiente'
    if any(fragment in key.lower() for fragment in INSECURE_KEY_FRAGMENTS):
        return 'valor de ejemplo o inseguro'
    if len(set(key)) < API_KEY_MIN_DISTINCT_CHARS:
        return 'poca variedad de caracteres'
    return None

def load_api_key() -> str:
    """Lee la clave del laboratorio del entorno. Sin clave válida, la API no arranca."""
    key = os.getenv(API_KEY_ENV, '').strip()
    problem = api_key_problem(key)
    if problem:
        raise RuntimeError(
            f'{API_KEY_ENV} no está configurada o no es válida ({problem}): copia .env.example a .env '
            f'y genera una clave aleatoria de al menos {API_KEY_MIN_LENGTH} caracteres (ver README).'
        )
    return key

# Se lee una sola vez, al arrancar. Para cambiarla hay que recrear el contenedor (rotación).
API_KEY = load_api_key()
