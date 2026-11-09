from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx
import os
from app.security import current_identity
from app.retrieval import search_documents
from app.config import STAGE

app = FastAPI(title='Asistente documental seguro — DevSecOps IA', version='1.0')

class Question(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    tenant: str = Field(default='empresa-a', min_length=1, max_length=60)

class ToolCall(BaseModel):
    operation: str
    document_id: str

@app.get('/health')
def health():
    return {'status': 'ok', 'stage': STAGE, 'model': 'mock'}

def infer(question: str, snippets: list[str]) -> str:
    with httpx.Client(timeout=5.0) as client:
        return client.post(os.getenv('MODEL_URL', 'http://mock-llm:8100/respond'), json={'question': question, 'context': snippets}).json()['answer']

@app.post('/ask')
def ask(payload: Question):
    docs = search_documents(payload.question, payload.tenant)
    snippets = [d['text'] for d in docs]
    try:
        answer = infer(payload.question, snippets)
    except (httpx.HTTPError, KeyError) as exc:
        raise HTTPException(status_code=503, detail='Proveedor simulado no disponible') from exc
    return {'answer': answer, 'sources': [d['id'] for d in docs], 'stage': STAGE}

@app.post('/tools/execute')
def tool_call(payload: ToolCall, identity: str = Depends(current_identity)):
    # Regla permanente del laboratorio: nunca se admiten efectos destructivos reales.
    if payload.operation != 'read_document':
        raise HTTPException(status_code=403, detail='Operación no permitida')
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(os.getenv('TOOLS_URL', 'http://tools:8200/execute'), json={'operation': payload.operation, 'document_id': payload.document_id, 'tenant': identity})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail='Herramienta no disponible') from exc
