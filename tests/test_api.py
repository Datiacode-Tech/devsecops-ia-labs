from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app, QUESTION_MAX_LENGTH

client = TestClient(app)
WRONG = {'x-api-key': 'clave-incorrecta-de-prueba'}

# --- Endpoint público ---

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'
    assert r.json()['model'] == 'mock'

# --- Autenticación (Unidad 3) ---

def test_ask_requires_api_key():
    r = client.post('/ask', json={'question': 'vacaciones'})
    assert r.status_code == 401
    assert r.json()['detail'] == 'Credencial ausente o incorrecta'

def test_ask_rejects_wrong_api_key(auth):
    r = client.post('/ask', headers=WRONG, json={'question': 'vacaciones'})
    assert r.status_code == 401
    assert auth['x-api-key'] not in r.text

@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_ask_returns_answer_and_sources(mock_infer, auth):
    r = client.post('/ask', headers=auth, json={'question': 'vacaciones', 'tenant': 'empresa-a'})
    assert r.status_code == 200
    assert set(r.json()) == {'answer', 'sources', 'stage'}
    assert r.json()['answer'].startswith('[SIMULADO]')

def test_tools_requires_api_key():
    r = client.post('/tools/execute', json={'operation': 'read_document', 'document_id': 'empresa-a-001'})
    assert r.status_code == 401

@patch('app.main.call_tools_service', return_value={'status': 'read-only'})
def test_tools_allowed_operation_with_valid_key(mock_tools, auth):
    r = client.post('/tools/execute', headers=auth, json={'operation': 'read_document', 'document_id': 'empresa-a-001'})
    assert r.status_code == 200
    assert mock_tools.call_args.args[0]['tenant'] == 'empresa-a'

def test_mutation_is_denied(auth):
    r = client.post('/tools/execute', headers=auth, json={'operation': 'delete_document', 'document_id': 'empresa-a-001'})
    assert r.status_code == 403
    assert r.json()['detail'] == 'Operación no permitida'

def test_auth_is_checked_before_body_validation():
    # Contrato: sin credencial válida la respuesta es 401 aunque el cuerpo también sea inválido.
    r = client.post('/ask', json={'question': 'x' * (QUESTION_MAX_LENGTH + 1)})
    assert r.status_code == 401

# --- Validación de entradas (Unidad 3) ---

def test_empty_question_is_rejected(auth):
    assert client.post('/ask', headers=auth, json={'question': ''}).status_code == 422

def test_blank_question_is_rejected(auth):
    assert client.post('/ask', headers=auth, json={'question': '   '}).status_code == 422

def test_question_length(auth):
    r = client.post('/ask', headers=auth, json={'question': 'x' * (QUESTION_MAX_LENGTH + 1)})
    assert QUESTION_MAX_LENGTH == 300
    assert r.status_code == 422

@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_question_at_limit_is_accepted(mock_infer, auth):
    r = client.post('/ask', headers=auth, json={'question': 'x' * QUESTION_MAX_LENGTH})
    assert r.status_code == 200

# --- Riesgos pendientes de otras unidades ---

@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_tenant_isolation_still_pending(mock_infer, auth):
    # R-02 sigue abierto: una API key válida no limita los documentos al tenant (Unidad 10).
    r = client.post('/ask', headers=auth, json={'question': 'presupuesto', 'tenant': 'empresa-a'})
    assert r.status_code == 200
    assert 'empresa-b-001' in r.json()['sources']
