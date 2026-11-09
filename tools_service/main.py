from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title='Servicio de herramientas DIDÁCTICO (no es MCP completo)')

class Operation(BaseModel):
    operation: str
    document_id: str
    tenant: str

@app.post('/execute')
def execute(op: Operation):
    if op.operation != 'read_document':
        raise HTTPException(status_code=403, detail='Solo lectura permitida')
    return {'operation': op.operation, 'document_id': op.document_id, 'status': 'read-only'}
