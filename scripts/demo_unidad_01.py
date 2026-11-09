#!/usr/bin/env python3
"""Demostración breve y segura de la unidad 01."""
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
print('UNIDAD 01: Fundamentos de DevSecOps, MLOps y LLMOps')
print('Objetivo: inspecciona la respuesta health y la documentación OpenAPI.')
print('Etapa:', json.loads((ROOT / 'course_stage.json').read_text())['stage'])
try:
    with urlopen('http://127.0.0.1:8000/health', timeout=3) as response:
        print('Salud de API:', json.loads(response.read()))
except Exception as exc:
    print('El servicio no responde. Primero: docker compose up -d --build')
    print('Detalles:', str(exc))

file = ROOT / 'compose.yaml'
print('Archivo foco:', file.relative_to(ROOT))
print('Extracto (primeros 650 caracteres):')
print(file.read_text(encoding='utf-8')[:650])
