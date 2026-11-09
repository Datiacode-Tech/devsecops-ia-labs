import json
from pathlib import Path

STAGE = json.loads(Path(__file__).resolve().parents[1].joinpath('course_stage.json').read_text(encoding='utf-8'))['stage']
