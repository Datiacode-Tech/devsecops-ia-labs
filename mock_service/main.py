from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title='Proveedor LLM SIMULADO — sin modelo real')

class Inference(BaseModel):
    question: str
    context: list[str] = []

@app.post('/respond')
def respond(payload: Inference):
    # No genera texto probabilístico ni evalúa instrucciones de usuario.
    summary = ' '.join(payload.context)[:220]
    return {'answer': f'[SIMULADO] Respuesta basada en contexto: {summary or "Sin documentos recuperados"}'}
