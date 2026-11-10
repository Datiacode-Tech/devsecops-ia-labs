#!/usr/bin/env python3
"""Demostración breve y segura de la unidad 03: autenticación y validación de la API."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000'

def clave_de_env() -> str:
    """Lee DEMO_API_KEY del entorno o de .env, sin mostrarla."""
    if os.getenv('DEMO_API_KEY'):
        return os.environ['DEMO_API_KEY']
    env = ROOT / '.env'
    if env.exists():
        for linea in env.read_text(encoding='utf-8').splitlines():
            if linea.startswith('DEMO_API_KEY='):
                return linea.split('=', 1)[1].strip()
    raise SystemExit('No se encuentra DEMO_API_KEY: crea .env a partir de .env.example')

def llamar(metodo: str, ruta: str, cuerpo: dict | None = None, clave: str | None = None) -> tuple[int, str]:
    cabeceras = {'Content-Type': 'application/json'}
    if clave is not None:
        cabeceras['x-api-key'] = clave
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    try:
        with urlopen(Request(BASE + ruta, data=datos, headers=cabeceras, method=metodo), timeout=5) as r:
            return r.status, r.read().decode()[:110]
    except HTTPError as e:
        return e.code, e.read().decode()[:110]

print('UNIDAD 03: Desarrollo seguro y protección de APIs de IA')
print('Etapa:', json.loads((ROOT / 'course_stage.json').read_text())['stage'])
clave = clave_de_env()
pregunta = {'question': '¿Cuántos días de vacaciones tengo?', 'tenant': 'empresa-a'}
casos = [
    ('1. API disponible (público)', 'GET', '/health', None, None),
    ('2. /ask sin clave', 'POST', '/ask', pregunta, None),
    ('3. /ask con clave incorrecta', 'POST', '/ask', pregunta, 'clave-incorrecta-de-prueba'),
    ('4. /ask con clave válida', 'POST', '/ask', pregunta, clave),
    ('5. Pregunta de 301 caracteres', 'POST', '/ask', {'question': 'x' * 301}, clave),
    ('6. delete_document con clave válida', 'POST', '/tools/execute', {'operation': 'delete_document', 'document_id': 'empresa-a-001'}, clave),
]
try:
    for titulo, metodo, ruta, cuerpo, k in casos:
        estado, texto = llamar(metodo, ruta, cuerpo, k)
        print(f'{titulo:40} HTTP {estado}  {texto}')
except OSError as exc:
    print('El servicio no responde. Primero: docker compose up -d --build')
    print('Detalles:', exc)
