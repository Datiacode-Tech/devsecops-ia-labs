from app.retrieval import documents
from app.config import STAGE

def test_documents_have_tenant_and_id():
    for d in documents():
        assert d['id'].startswith(d['tenant'] + '-')

def test_stage_is_valid():
    assert 1 <= STAGE <= 11
