"""Funcionamiento básico del informe de soporte (app/soporte.py)."""
from app.soporte import generar_informe

ENTORNO = {'MODEL_URL': 'http://mock-llm:8100/respond', 'TOOLS_URL': 'http://tools:8200/execute'}
CABECERAS = {'content-type': 'application/json', 'user-agent': 'cliente-interno/1.4'}

def test_support_report_includes_error_and_context():
    informe = generar_informe(ENTORNO, CABECERAS, 'Proveedor simulado no disponible (HTTP 503)')
    assert 'Proveedor simulado no disponible (HTTP 503)' in informe
    assert 'MODEL_URL=http://mock-llm:8100/respond' in informe
    assert 'TOOLS_URL=http://tools:8200/execute' in informe
    assert 'content-type: application/json' in informe
    assert 'user-agent: cliente-interno/1.4' in informe
