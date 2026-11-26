"""SIMULACIÓN de los controles de seguridad de un servidor MCP.

No implementa el protocolo MCP (sin JSON-RPC, transporte ni sesiones): solo muestra
qué debe comprobar el servidor antes de ejecutar una herramienta.

Uso: python3 servidor_mcp_simulado.py listar
     python3 servidor_mcp_simulado.py ejecutar SESION HERRAMIENTA 'ARGUMENTOS_JSON'
"""
import json, re, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LAB = AQUI.parents[1]
CATALOGO = json.loads((AQUI / "catalogo-herramientas.json").read_text(encoding="utf-8"))["herramientas"]
SESIONES = json.loads((AQUI / "sesiones.json").read_text(encoding="utf-8"))
if not (LAB / "data" / "documents.json").is_file():
    sys.exit("ERROR: no se encuentra data/documents.json. Copia la carpeta en artifacts/ de la raíz del laboratorio y ejecuta el script desde allí.")
DOCUMENTOS = {d["id"]: d for d in json.loads((LAB / "data" / "documents.json").read_text(encoding="utf-8"))}

def ejecutar(sesion, nombre, argumentos):
    herramienta = next((h for h in CATALOGO if h["nombre"] == nombre), None)
    if herramienta is None:
        return False, f"la herramienta {nombre} no existe"
    if sesion not in SESIONES:
        return False, "sesión no reconocida"
    if nombre not in SESIONES[sesion]["herramientas"]:                       # 1. permiso
        return False, f"la sesión {sesion} no tiene permiso para {nombre}"
    esperados = herramienta["argumentos"]
    if not isinstance(argumentos, dict) or set(argumentos) != set(esperados):  # 2. argumentos
        return False, f"argumentos esperados: {', '.join(esperados)}"
    for clave, patron in esperados.items():
        if not isinstance(argumentos[clave], str) or not re.fullmatch(patron, argumentos[clave]):
            return False, f"el argumento {clave} no tiene un formato válido"
    documento = DOCUMENTOS.get(argumentos["document_id"])
    if documento is None or documento["tenant"] != SESIONES[sesion]["tenant"]:  # 3. recurso
        return False, "documento inexistente o de otra empresa"
    if nombre == "read_document":
        return True, documento["text"]
    return True, f"[SIMULADO] {nombre} autorizado; en este laboratorio no se modifica nada"

if __name__ == "__main__":
    if sys.argv[1:] == ["listar"]:
        for h in CATALOGO:
            print(f"{h['nombre']}: {h['descripcion']} Argumentos: {', '.join(h['argumentos'])}")
        sys.exit(0)
    if len(sys.argv) != 5 or sys.argv[1] != "ejecutar":
        sys.exit(__doc__)
    try:
        argumentos = json.loads(sys.argv[4])
    except json.JSONDecodeError:
        sys.exit("RECHAZADO: los argumentos no son JSON válido")
    permitido, resultado = ejecutar(sys.argv[2], sys.argv[3], argumentos)
    print(("PERMITIDO: " if permitido else "RECHAZADO: ") + resultado)
    sys.exit(0 if permitido else 1)
