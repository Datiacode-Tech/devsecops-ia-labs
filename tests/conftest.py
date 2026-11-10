import os
import secrets
import pytest

# Fuera de Docker no existe .env: se genera una clave aleatoria solo para esta sesión de pruebas.
# Dentro del contenedor se usa la DEMO_API_KEY que Docker Compose toma de .env.
os.environ.setdefault('DEMO_API_KEY', secrets.token_urlsafe(24))

@pytest.fixture
def auth():
    return {'x-api-key': os.environ['DEMO_API_KEY']}
