import json
from pathlib import Path

def documents():
    return json.loads(Path(__file__).resolve().parents[1].joinpath('data/documents.json').read_text(encoding='utf-8'))

def search_documents(question: str, tenant: str):
    words = set(w.strip('.,:;!?').lower() for w in question.split() if len(w) > 3)
    rows = documents()
    ranked = sorted(rows, key=lambda d: len(words.intersection(set(d['text'].lower().split()))), reverse=True)
    return ranked[:2]
