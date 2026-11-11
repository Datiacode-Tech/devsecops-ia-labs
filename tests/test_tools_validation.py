import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize('document_id', ['empresa-a-001; rm -rf /', '../etc/passwd', 'EMPRESA-A-001', 'empresa-a-1', ''])
def test_tool_document_id_invalid_format(auth, document_id):
    r = client.post('/tools/execute', headers=auth, json={'operation': 'read_document', 'document_id': document_id})
    assert r.status_code == 422

def test_tool_document_id_too_long(auth):
    r = client.post('/tools/execute', headers=auth, json={'operation': 'read_document', 'document_id': 'empresa-' + 'a' * 60 + '-001'})
    assert r.status_code == 422

def test_tool_operation_too_long(auth):
    r = client.post('/tools/execute', headers=auth, json={'operation': 'x' * 41, 'document_id': 'empresa-a-001'})
    assert r.status_code == 422

@patch('app.main.call_tools_service', return_value={'status': 'read-only'})
def test_tool_valid_document_id(mock_tools, auth):
    r = client.post('/tools/execute', headers=auth, json={'operation': 'read_document', 'document_id': 'empresa-a-001'})
    assert r.status_code == 200

def test_tool_validation_requires_auth_first():
    r = client.post('/tools/execute', json={'operation': 'read_document', 'document_id': '../etc/passwd'})
    assert r.status_code == 401

@patch('app.main.call_tools_service', return_value={'status': 'read-only'})
def test_tool_format_is_not_tenant_authorization(mock_tools, auth):
    # Formato válido de otro tenant: la validación no lo impide (aislamiento en la Unidad 10).
    r = client.post('/tools/execute', headers=auth, json={'operation': 'read_document', 'document_id': 'empresa-b-001'})
    assert r.status_code == 200
