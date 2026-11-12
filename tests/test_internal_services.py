"""Unidad 5: tras el endurecimiento, la API sigue funcionando de extremo a extremo.

Sin simulaciones: la API llama de verdad a mock-llm y tools por la red interna (backend).
Requiere que los servicios estén en marcha, como ocurre con la batería completa
(`docker compose run ... api python -m pytest ...` arranca primero las dependencias).
Fuera de un contenedor se omiten.
"""
import os
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(not Path('/.dockerenv').exists(), reason='requiere la red interna de Docker')

MODEL_URL = os.getenv('MODEL_URL', 'http://mock-llm:8100/respond')
TOOLS_URL = os.getenv('TOOLS_URL', 'http://tools:8200/execute')
QUESTION = {'question': '¿Cuántos días de vacaciones tengo?', 'tenant': 'empresa-a'}

def test_mock_llm_is_reachable_from_api():
    r = httpx.post(MODEL_URL, json={'question': 'prueba', 'context': []}, timeout=5)
    assert r.status_code == 200
    assert r.json()['answer'].startswith('[SIMULADO]')

def test_tools_is_reachable_from_api():
    lectura = {'operation': 'read_document', 'document_id': 'empresa-a-001', 'tenant': 'empresa-a'}
    r = httpx.post(TOOLS_URL, json=lectura, timeout=5)
    assert r.status_code == 200 and r.json()['status'] == 'read-only'
    # tools mantiene su propia restricción de solo lectura.
    r = httpx.post(TOOLS_URL, json={**lectura, 'operation': 'delete_document'}, timeout=5)
    assert r.status_code == 403

def test_ask_end_to_end_with_authentication(auth):
    from app.main import app
    client = TestClient(app)
    assert client.post('/ask', json=QUESTION).status_code == 401
    r = client.post('/ask', json=QUESTION, headers=auth)
    assert r.status_code == 200
    assert r.json()['answer'].startswith('[SIMULADO]')
    r = client.post('/tools/execute', json={'operation': 'read_document', 'document_id': 'empresa-a-001'}, headers=auth)
    assert r.status_code == 200
    r = client.post('/tools/execute', json={'operation': 'delete_document', 'document_id': 'empresa-a-001'}, headers=auth)
    assert r.status_code == 403
