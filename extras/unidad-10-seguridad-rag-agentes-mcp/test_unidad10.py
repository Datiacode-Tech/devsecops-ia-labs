"""Pruebas de los controles de la Unidad 10 (recuperación, integridad y herramientas).

Verifican las demostraciones de esta carpeta, no la API: /ask y /tools/execute
siguen sin filtrar por empresa (riesgos R-02 y R-22).
"""
import copy, json, sys
import pytest
import rag
import servidor_mcp_simulado as mcp

sys.path.insert(0, str(rag.LAB))
from app import retrieval   # recuperación real del laboratorio

DOCS = json.loads((rag.LAB / "data" / "documents.json").read_text(encoding="utf-8"))
PREGUNTAS = ["¿Cuál es el presupuesto de la política financiera?", "vacaciones", "política de gastos", "presupuesto confidencial"]

@pytest.mark.parametrize("pregunta", PREGUNTAS)
def test_buscar_ordena_igual_que_la_api(pregunta):
    assert [d["id"] for d in rag.buscar(pregunta, DOCS)] == [d["id"] for d in retrieval.search_documents(pregunta, "empresa-a")]

def test_vulnerable_mezcla_empresas():
    elegidos, _ = rag.recuperar("vulnerable", "presupuesto", DOCS)
    assert "empresa-b-001" in [d["id"] for d in elegidos]

def test_tenant_del_cliente_se_puede_falsear():
    elegidos, _ = rag.recuperar("tenant-cliente", "presupuesto", DOCS, sesion="ana", tenant_cliente="empresa-b")
    assert [d["id"] for d in elegidos] == ["empresa-b-001"]

@pytest.mark.parametrize("sesion", ["ana", "bruno"])
@pytest.mark.parametrize("pregunta", PREGUNTAS)
def test_protegido_solo_devuelve_la_empresa_de_la_sesion(sesion, pregunta):
    elegidos, _ = rag.recuperar("protegido", pregunta, DOCS, sesion=sesion, tenant_cliente="empresa-b")
    assert elegidos and all(d["tenant"] == rag.SESIONES[sesion]["tenant"] for d in elegidos)

def test_documento_manipulado_se_descarta():
    manipulados = copy.deepcopy(DOCS)
    manipulados[0]["text"] = manipulados[0]["text"].replace("quince", "dos")
    elegidos, avisos = rag.recuperar("protegido", "vacaciones", manipulados)
    assert avisos == ["AVISO: empresa-a-001 descartado: su huella no coincide con el registro"]
    assert "empresa-a-001" not in [d["id"] for d in elegidos]

@pytest.mark.parametrize("sesion, herramienta, argumentos, permitido", [
    ("ana", "read_document", {"document_id": "empresa-a-001"}, True),
    ("ana", "delete_document", {"document_id": "empresa-a-001"}, False),
    ("ana", "send_email", {"to": "x"}, False),
    ("ana", "read_document", {"document_id": "../../etc/passwd"}, False),
    ("ana", "read_document", {"document_id": "empresa-a-001", "tenant": "empresa-b"}, False),
    ("ana", "read_document", {"document_id": "empresa-b-001"}, False),
    ("bruno", "read_document", {"document_id": "empresa-b-001"}, True),
    ("desconocida", "read_document", {"document_id": "empresa-a-001"}, False),
])
def test_controles_del_servidor_mcp_simulado(sesion, herramienta, argumentos, permitido):
    assert mcp.ejecutar(sesion, herramienta, argumentos)[0] is permitido
