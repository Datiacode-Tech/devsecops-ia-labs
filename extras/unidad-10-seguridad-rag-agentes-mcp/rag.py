"""Recuperación de documentos (RAG) con y sin controles, sobre los documentos del laboratorio.

Uso: python3 rag.py {vulnerable|tenant-cliente|protegido} "PREGUNTA" [--sesion S] [--tenant T] [--documentos RUTA]

  vulnerable      sin filtro de empresa, como /ask hoy
  tenant-cliente  filtra por la empresa que declara el cliente (--tenant)
  protegido       filtra por la empresa de la sesión, que decide el servidor (sesiones.json),
                  y descarta los documentos cuya huella no coincide con huellas-documentos.json

No llama a ningún modelo: muestra el contexto que recibiría.
"""
import argparse, hashlib, json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LAB = AQUI.parents[1]                      # carpeta raíz del laboratorio
SESIONES = json.loads((AQUI / "sesiones.json").read_text(encoding="utf-8"))
HUELLAS = json.loads((AQUI / "huellas-documentos.json").read_text(encoding="utf-8"))

def buscar(pregunta, docs):
    # Misma lógica que app/retrieval.py: los 2 documentos con más palabras (de más de 3 letras) en común.
    palabras = {w.strip(".,:;!?").lower() for w in pregunta.split() if len(w) > 3}
    return sorted(docs, key=lambda d: len(palabras & set(d["text"].lower().split())), reverse=True)[:2]

def huella(doc):
    return hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()

def recuperar(modo, pregunta, docs, sesion="ana", tenant_cliente="empresa-a"):
    avisos = []
    if modo == "tenant-cliente":
        docs = [d for d in docs if d["tenant"] == tenant_cliente]        # lo decide el cliente
    elif modo == "protegido":
        tenant = SESIONES[sesion]["tenant"]                              # lo decide el servidor
        docs = [d for d in docs if d["tenant"] == tenant]
        avisos = [f"AVISO: {d['id']} descartado: su huella no coincide con el registro" for d in docs if huella(d) != HUELLAS.get(d["id"])]
        docs = [d for d in docs if huella(d) == HUELLAS.get(d["id"])]
    return buscar(pregunta, docs), avisos

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="RAG con y sin controles (Unidad 10)")
    p.add_argument("modo", choices=["vulnerable", "tenant-cliente", "protegido"])
    p.add_argument("pregunta")
    p.add_argument("--sesion", default="ana", choices=sorted(SESIONES))
    p.add_argument("--tenant", default="empresa-a")
    p.add_argument("--documentos", default=str(LAB / "data" / "documents.json"))
    a = p.parse_args()
    if not Path(a.documentos).is_file():
        raise SystemExit("ERROR: no se encuentra data/documents.json. Copia la carpeta en artifacts/ de la raíz del laboratorio y ejecuta el script desde allí." if a.documentos.endswith("data/documents.json") else f"ERROR: no existe {a.documentos}")
    docs = json.loads(Path(a.documentos).read_text(encoding="utf-8"))
    if a.modo == "protegido":
        print(f"Sesión {a.sesion}: empresa {SESIONES[a.sesion]['tenant']} (según el servidor)")
    elegidos, avisos = recuperar(a.modo, a.pregunta, docs, a.sesion, a.tenant)
    for aviso in avisos:
        print(aviso)
    print("Documentos entregados al modelo:", ", ".join(d["id"] for d in elegidos) or "ninguno")
    for d in elegidos:
        print(f"  [{d['id']}] {d['text']}")
