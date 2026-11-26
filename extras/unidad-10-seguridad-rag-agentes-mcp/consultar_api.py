"""Envía una pregunta al /ask REAL del laboratorio desde dentro del contenedor de la API.

Sirve para consultar la API con otra colección de documentos montada en
/code/data/documents.json (ejemplo 2). Usa la clave DEMO_API_KEY del contenedor.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient
from app.main import app

respuesta = TestClient(app).post("/ask", headers={"x-api-key": os.environ["DEMO_API_KEY"]},
                                 json={"question": sys.argv[1]})
print(respuesta.json())
