import csv
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / 'security' / 'risk_register.csv'
COLUMNS = ['id', 'activo', 'amenaza', 'impacto', 'probabilidad', 'control', 'evidencia', 'estado']

def rows():
    if not REGISTER.exists():
        pytest.skip('security/risk_register.csv no disponible: monta la carpeta security/')
    with REGISTER.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return list(reader)

def existing_tests():
    names = set()
    for path in Path(__file__).resolve().parent.glob('test_*.py'):
        names.update(re.findall(r'^def (test_\w+)', path.read_text(encoding='utf-8'), re.MULTILINE))
    return names

def is_pending(evidence: str) -> bool:
    return evidence.startswith('pendiente_') or evidence.endswith('_pendiente')

def test_risk_register_structure():
    data = rows()
    ids = [r['id'] for r in data]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r'R-\d{2}', i) for i in ids)
    assert {'R-01', 'R-02', 'R-03'} <= set(ids)
    assert all(value.strip() for r in data for value in r.values())

def test_evidence_exists_or_is_pending():
    tests = existing_tests()
    for r in rows():
        if is_pending(r['evidencia']):
            # Un control documentado pero no verificado no puede figurar como mitigado.
            assert r['estado'] != 'Mitigado', r['id']
        else:
            assert r['evidencia'] in tests, f"{r['id']}: la prueba {r['evidencia']} no existe"
