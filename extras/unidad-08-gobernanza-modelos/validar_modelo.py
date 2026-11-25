"""Validación técnica de un modelo registrado: integridad y estructura.

Uso: python3 validar_modelo.py VERSION    (desde la carpeta que contiene registro-modelos.json)
Código de salida: 0 si supera todas las comprobaciones, 1 si alguna falla.
No evalúa si el modelo acierta ni lo aprueba: eso es otra decisión.
"""
import hashlib, json, sys
from pathlib import Path

CAMPOS = ["nombre", "version", "entradas", "pesos", "sesgo", "umbral_urgente", "etiquetas"]

def validar(version, registro="registro-modelos.json"):
    entrada = next((m for m in json.loads(Path(registro).read_text(encoding="utf-8"))["modelos"]
                    if m["version"] == version), None)
    if entrada is None:
        return [f"la versión {version} no está en el registro"]
    ruta = Path(entrada["artefacto"])
    if not ruta.is_file():
        return [f"no existe el archivo {ruta}"]
    errores = []
    if hashlib.sha256(ruta.read_bytes()).hexdigest() != entrada["sha256"]:
        errores.append("integridad: el hash SHA-256 no coincide con el registro")
    try:
        modelo = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return errores + [f"estructura: el archivo no es un JSON válido ({e})"]
    faltan = [c for c in CAMPOS if c not in modelo]
    if faltan:
        return errores + [f"estructura: faltan campos obligatorios: {', '.join(faltan)}"]
    if not isinstance(modelo["entradas"], list):
        return errores + ["estructura: entradas debe ser una lista"]
    es_numero = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    pesos = modelo["pesos"] if isinstance(modelo["pesos"], list) else [None]
    mal = [c for c in ("umbral_urgente", "sesgo") if not es_numero(modelo[c])]
    mal += ["pesos"] if not all(es_numero(p) for p in pesos) else []
    if mal:
        return errores + [f"tipo: deben ser números (no texto ni otro tipo): {', '.join(mal)}"]
    if modelo["version"] != version:
        errores.append(f"estructura: el archivo dice versión {modelo['version']} y el registro {version}")
    if not 0 <= modelo["umbral_urgente"] <= 1:
        errores.append(f"rango: umbral_urgente={modelo['umbral_urgente']} fuera de [0, 1]")
    if len(modelo["pesos"]) != len(modelo["entradas"]) or any(not -5 <= p <= 5 for p in modelo["pesos"]):
        errores.append("rango: debe haber un peso por entrada y cada peso entre -5 y 5")
    return errores

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if not Path("registro-modelos.json").is_file():
        sys.exit("ERROR: no hay registro-modelos.json en este directorio. Ejecuta el script desde artifacts/gobernanza.")
    fallos = validar(sys.argv[1])
    for f in fallos:
        print("FALLO", f)
    print(f"Versión {sys.argv[1]}:", "NO SUPERA la validación técnica" if fallos else "supera la validación técnica")
    sys.exit(1 if fallos else 0)
