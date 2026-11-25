"""Registra una decisión sobre una versión del modelo: cambia su estado y la anota en el historial.

Uso: python3 cambiar_estado.py VERSION NUEVO_ESTADO "MOTIVO" RESPONSABLE
Estados: registrado -> en_revision -> aprobado -> retirado (en_revision -> retirado = rechazo).
"""
import json, sys
from datetime import date
from pathlib import Path
from validar_modelo import validar

PERMITIDOS = {"registrado": ["en_revision"], "en_revision": ["aprobado", "retirado"],
              "aprobado": ["retirado"], "retirado": []}
REGISTRO, HISTORIAL = Path("registro-modelos.json"), Path("historial-estados.jsonl")

if len(sys.argv) != 5 or not sys.argv[3].strip():
    sys.exit(__doc__)
if not REGISTRO.is_file():
    sys.exit("ERROR: no hay registro-modelos.json en este directorio. Ejecuta el script desde artifacts/gobernanza.")
version, nuevo, motivo, responsable = sys.argv[1:]
registro = json.loads(REGISTRO.read_text(encoding="utf-8"))
modelo = next((m for m in registro["modelos"] if m["version"] == version), None)
if modelo is None:
    sys.exit(f"RECHAZADO: la versión {version} no está en el registro")
anterior = modelo["estado"]
if nuevo not in PERMITIDOS[anterior]:
    sys.exit(f"RECHAZADO: de '{anterior}' no se puede pasar a '{nuevo}'")
if nuevo == "aprobado" and validar(version):
    sys.exit("RECHAZADO: la versión no supera la validación técnica (python3 validar_modelo.py " + version + ")")

modelo["estado"] = nuevo
REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
cambio = {"fecha": date.today().isoformat(), "id": modelo["id"], "anterior": anterior,
          "nuevo": nuevo, "motivo": motivo, "responsable": responsable}
with HISTORIAL.open("a", encoding="utf-8") as f:
    f.write(json.dumps(cambio, ensure_ascii=False) + "\n")
print(f"{modelo['id']}: {anterior} -> {nuevo}")
