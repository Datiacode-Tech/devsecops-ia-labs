from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_health():
    body = client.get('/health').json()
    assert body['status'] == 'ok'
    assert body['model'] == 'mock'

@patch('app.main.infer', return_value='[SIMULADO] ok')
def test_ask_returns_answer_and_sources(mock_infer):
    r = client.post('/ask', json={'question': 'vacaciones', 'tenant': 'empresa-a'})
    assert r.status_code == 200
    assert set(r.json()) == {'answer', 'sources', 'stage'}
    assert r.json()['answer'].startswith('[SIMULADO]')

def test_empty_question_is_rejected():
    assert client.post('/ask', json={'question': ''}).status_code == 422

def test_question_length():
    assert client.post('/ask', json={'question': 'x' * 4010}).status_code == 422

def test_mutation_is_denied():
    r = client.post('/tools/execute', json={'operation': 'delete_document', 'document_id': 'empresa-a-001'})
    assert r.status_code == 403
    assert r.json()['detail'] == 'Operación no permitida'
