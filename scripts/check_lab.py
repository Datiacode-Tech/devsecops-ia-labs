import json, urllib.request
from pathlib import Path
cfg=json.loads(Path('course_stage.json').read_text())
print(f"Curso activo: unidad {cfg['stage']}")
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3) as r:
        result=json.load(r)
        print('API:',result)
        assert result['stage']==cfg['stage']
except Exception as e:
    raise SystemExit(f'API no disponible: {e}. Usa docker compose up -d --build')
