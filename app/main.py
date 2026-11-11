from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
import httpx
import os
from app.security import require_api_key
from app.retrieval import search_documents
from app.config import STAGE

app = FastAPI(title='Asistente documental seguro — DevSecOps IA', version='1.0')

# Límite de seguridad para las preguntas: reduce el abuso del modelo con entradas largas.
QUESTION_MAX_LENGTH = 300

class Question(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=QUESTION_MAX_LENGTH)]
    tenant: str = Field(default='empresa-a', min_length=1, max_length=60)

# Identificadores con el formato de los documentos del laboratorio: empresa-<nombre>-<tres dígitos>
DOCUMENT_ID_PATTERN = r'^empresa-[a-z]+-[0-9]{3}$'

class ToolCall(BaseModel):
    operation: str = Field(min_length=1, max_length=40)
    document_id: str = Field(max_length=60, pattern=DOCUMENT_ID_PATTERN)

@app.get('/health')
def health():
    return {'status': 'ok', 'stage': STAGE, 'model': 'mock'}

def infer(question: str, snippets: list[str]) -> str:
    with httpx.Client(timeout=5.0) as client:
        return client.post(os.getenv('MODEL_URL', 'http://mock-llm:8100/respond'), json={'question': question, 'context': snippets}).json()['answer']

def call_tools_service(body: dict) -> dict:
    with httpx.Client(timeout=5.0) as client:
        response = client.post(os.getenv('TOOLS_URL', 'http://tools:8200/execute'), json=body)
        response.raise_for_status()
        return response.json()

@app.post('/ask')
def ask(payload: Question, identity: str = Depends(require_api_key)):
    # La API key autentica la petición, pero el tenant sigue llegando en el cuerpo
    # y la recuperación no lo usa: la autorización por tenant está pendiente.
    docs = search_documents(payload.question, payload.tenant)
    snippets = [d['text'] for d in docs]
    try:
        answer = infer(payload.question, snippets)
    except (httpx.HTTPError, KeyError) as exc:
        raise HTTPException(status_code=503, detail='Proveedor simulado no disponible') from exc
    return {'answer': answer, 'sources': [d['id'] for d in docs], 'stage': STAGE}

@app.post('/tools/execute')
def tool_call(payload: ToolCall, identity: str = Depends(require_api_key)):
    # Regla permanente del laboratorio: nunca se admiten efectos destructivos reales.
    if payload.operation != 'read_document':
        raise HTTPException(status_code=403, detail='Operación no permitida')
    try:
        return call_tools_service({'operation': payload.operation, 'document_id': payload.document_id, 'tenant': identity})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail='Herramienta no disponible') from exc
