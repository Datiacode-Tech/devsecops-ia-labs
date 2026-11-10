import json
import os
from pathlib import Path

STAGE = json.loads(Path(__file__).resolve().parents[1].joinpath('course_stage.json').read_text(encoding='utf-8'))['stage']

API_KEY_ENV = 'DEMO_API_KEY'
API_KEY_PLACEHOLDER = 'cambia-esta-clave'
API_KEY_MIN_LENGTH = 16

def load_api_key() -> str:
    """Lee la clave del laboratorio del entorno. Sin clave válida, la API no arranca."""
    key = os.getenv(API_KEY_ENV, '').strip()
    if not key or key.startswith(API_KEY_PLACEHOLDER) or len(key) < API_KEY_MIN_LENGTH:
        # El mensaje nunca incluye el valor recibido.
        raise RuntimeError(
            f'{API_KEY_ENV} no está configurada o no es válida: copia .env.example a .env '
            f'y genera una clave de al menos {API_KEY_MIN_LENGTH} caracteres (ver README).'
        )
    return key

API_KEY = load_api_key()
