import pytest
from app.retrieval import documents
from app.config import STAGE, API_KEY_ENV, load_api_key

def test_documents_have_tenant_and_id():
    for d in documents():
        assert d['id'].startswith(d['tenant'] + '-')

def test_stage_is_valid():
    assert 1 <= STAGE <= 11

def test_course_stage_is_unit_4():
    assert STAGE == 4

@pytest.mark.parametrize('value', [None, '', 'cambia-esta-clave', 'corta'])
def test_api_key_config_rejects_missing_or_weak(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(API_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(API_KEY_ENV, value)
    with pytest.raises(RuntimeError) as exc:
        load_api_key()
    if value:
        assert value not in str(exc.value)
