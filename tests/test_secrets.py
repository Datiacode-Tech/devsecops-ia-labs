"""Pruebas de la Unidad 4: gestión segura de secretos y credenciales."""
import logging
import os
import secrets
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app import config
from app.config import API_KEY_ENV, load_api_key
from app.log_redaction import REDACTED, SecretRedactionFilter, redact
from app.main import app

client = TestClient(app)
ROOT = Path(config.__file__).resolve().parents[1]
QUESTION = {'question': '¿Cuántos días de vacaciones tengo?', 'tenant': 'empresa-a'}

def fresh_key() -> str:
    return secrets.token_urlsafe(24)

# --- Configuración de la credencial (ejemplo 2) ---

@pytest.mark.parametrize('value', [
    'curso-demo-key-local',        # clave fija de una versión anterior del laboratorio
    'CAMBIA-ESTA-CLAVE-2026',      # valor de .env.example con añadidos
    'password-password-2026',
    'mi-clave-de-ejemplo-123',
    'a' * 32,                      # larga, pero sin variedad
])
def test_api_key_config_rejects_demo_values(monkeypatch, value):
    monkeypatch.setenv(API_KEY_ENV, value)
    with pytest.raises(RuntimeError) as exc:
        load_api_key()
    assert value not in str(exc.value)

def test_generated_api_key_is_accepted(monkeypatch):
    key = fresh_key()
    monkeypatch.setenv(API_KEY_ENV, key)
    assert load_api_key() == key

def test_api_key_not_hardcoded_in_source():
    # La clave en uso no aparece en ningún fichero de código, datos o configuración de la imagen.
    files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py', '.json', '.yaml', '.yml', '.toml', '.txt'}]
    assert files
    for path in files:
        assert config.API_KEY not in path.read_text(encoding='utf-8', errors='ignore'), path

# --- Respuestas HTTP (ejemplos 2 y 7) ---

@patch('app.main.call_tools_service', return_value={'status': 'read-only'})
@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_responses_never_expose_api_key(mock_infer, mock_tools, auth):
    key = auth['x-api-key']
    wrong = 'erronea-' + fresh_key()
    calls = [
        ('get', '/health', {}, None, 200),
        ('get', '/openapi.json', {}, None, 200),
        ('post', '/ask', {}, QUESTION, 401),
        ('post', '/ask', {'x-api-key': wrong}, QUESTION, 401),
        ('post', '/ask', auth, QUESTION, 200),
        ('post', '/ask', auth, {'question': ''}, 422),
        ('post', '/tools/execute', auth, {'operation': 'read_document', 'document_id': 'empresa-a-001'}, 200),
        ('post', '/tools/execute', auth, {'operation': 'delete_document', 'document_id': 'empresa-a-001'}, 403),
    ]
    for method, path, headers, body, status in calls:
        r = client.request(method.upper(), path, headers=headers, json=body)
        assert r.status_code == status, path
        exposed = r.text + ' '.join(f'{k}: {v}' for k, v in r.headers.items())
        assert key not in exposed, path
        assert wrong not in exposed, path

# --- Registros (ejemplo 4) ---

def test_redaction_filter_is_installed():
    for name in ('lab', 'uvicorn', 'uvicorn.error', 'uvicorn.access'):
        assert any(isinstance(f, SecretRedactionFilter) for f in logging.getLogger(name).filters), name

def test_redact_masks_key_and_named_credentials():
    key, other = fresh_key(), fresh_key()
    text = (f"clave={key} cabeceras={{'x-api-key': '{other}', 'authorization': 'Bearer {other}'}} "
            f'DEMO_API_KEY={other} x-api-key: {other}')
    clean = redact(text, [key])
    assert key not in clean and other not in clean
    assert clean.count(REDACTED) == 5

def test_auth_failures_are_logged_without_credentials(caplog, auth):
    wrong = 'erronea-' + fresh_key()
    with caplog.at_level(logging.WARNING, logger='lab'):
        client.post('/ask', json=QUESTION)
        client.post('/ask', headers={'x-api-key': wrong}, json=QUESTION)
    assert 'credencial ausente' in caplog.text
    assert 'credencial incorrecta' in caplog.text
    assert wrong not in caplog.text
    assert auth['x-api-key'] not in caplog.text

def test_logs_redact_api_key(caplog):
    # Registros mal diseñados: el filtro impide que la clave llegue a la salida.
    with caplog.at_level(logging.INFO):
        logging.getLogger('lab').info('Cabeceras recibidas: %s', {'x-api-key': config.API_KEY, 'accept': '*/*'})
        logging.getLogger('uvicorn.error').info('Configuración: DEMO_API_KEY=%s', config.API_KEY)
    assert config.API_KEY not in caplog.text
    assert caplog.text.count(REDACTED) == 2

def test_access_log_redaction_keeps_uvicorn_format():
    from uvicorn.logging import AccessFormatter
    record = logging.LogRecord('uvicorn.access', logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                               ('127.0.0.1:5000', 'GET', f'/health?x-api-key={config.API_KEY}', '1.1', 200), None)
    for f in logging.getLogger('uvicorn.access').filters:
        f.filter(record)
    line = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s', use_colors=False).format(record)
    assert config.API_KEY not in line
    assert line.endswith('" 200 OK') and REDACTED in line

# --- Rotación (ejemplo 5) ---

@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_key_change_requires_restart(mock_infer, monkeypatch, auth):
    # Cambiar el valor en el entorno no basta: la clave se carga al arrancar el proceso.
    monkeypatch.setenv(API_KEY_ENV, fresh_key())
    assert client.post('/ask', headers=auth, json=QUESTION).status_code == 200
    assert client.post('/ask', headers={'x-api-key': os.environ[API_KEY_ENV]}, json=QUESTION).status_code == 401

@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_rotation_rejects_old_key_and_accepts_new(mock_infer, monkeypatch, caplog, auth):
    old, new = auth['x-api-key'], fresh_key()
    monkeypatch.setenv(API_KEY_ENV, new)
    # Simula el arranque del contenedor recreado: la configuración se vuelve a leer del entorno.
    monkeypatch.setattr(config, 'API_KEY', load_api_key())
    assert client.post('/ask', headers={'x-api-key': old}, json=QUESTION).status_code == 401
    r = client.post('/ask', headers={'x-api-key': new}, json=QUESTION)
    assert r.status_code == 200 and new not in r.text
    # El filtro de registros protege la clave nueva.
    with caplog.at_level(logging.INFO, logger='lab'):
        logging.getLogger('lab').info('clave en uso %s', new)
    assert new not in caplog.text
