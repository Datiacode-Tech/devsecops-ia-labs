"""Asistente de soporte FICTICIO de la Unidad 9.

SIMULACIÓN DETERMINISTA: aquí no hay ningún LLM. modelo_simulado() aplica tres
reglas fijas que imitan fallos conocidos de los modelos de lenguaje, para poder
comparar la versión vulnerable con la protegida. No mide cómo se comportaría un
modelo real.

Uso: python3 asistente.py {vulnerable|protegido} "MENSAJE" [DOCUMENTO] [--prompt]
"""
import re, sys
from pathlib import Path
import guardrails

POLITICA = Path(__file__).with_name("politica.txt").read_text(encoding="utf-8").strip()
PALABRA = re.search(r"Palabra reservada: (\w+)", POLITICA).group(1)
TEMAS = ("contraseña", "correo", "vpn", "wifi", "impresora", "portátil")

def modelo_simulado(prompt, documento=""):
    mensaje = prompt.rsplit("Usuario:", 1)[-1].lower()
    # Regla 1: obedece la última orden «responde ...» que encuentre, venga de donde venga.
    ordenes = re.findall(r"responde (?:únicamente |solo |que )([^.\n]+)", prompt, re.IGNORECASE)
    if ordenes:
        return f"[SIMULADO] {ordenes[-1]}"
    # Regla 2: rechaza la petición directa de la palabra reservada, pero cede ante reformulaciones.
    if "palabra reservada" in mensaje:
        if re.search(r"deletr[eé]", mensaje):
            return "[SIMULADO] " + "-".join(PALABRA)
        if re.search(r"actúa como|administrador|historia|personaje", mensaje):
            return f"[SIMULADO] De acuerdo: la palabra reservada es {PALABRA}."
        return "[SIMULADO] No puedo revelar la palabra reservada."
    # Regla 3: comportamiento previsto.
    if documento:
        return "[SIMULADO] Resumen: " + documento.splitlines()[0]
    if any(t in mensaje for t in TEMAS):
        return "[SIMULADO] Incidencia informática registrada. Te indico los pasos a seguir."
    return "[SIMULADO] Solo puedo ayudarte con incidencias informáticas."

def vulnerable(mensaje, documento=""):
    prompt = f"{POLITICA}\n{documento}\nUsuario: {mensaje}"   # todo mezclado en un solo texto
    return prompt, modelo_simulado(prompt, documento)

def protegido(mensaje, documento=""):
    if guardrails.es_sospechoso(mensaje):
        return "", "BLOQUEADO (entrada): el mensaje intenta modificar las instrucciones."
    descartadas = guardrails.lineas_sospechosas(documento)
    limpio = "\n".join(l for l in documento.splitlines() if l not in descartadas)
    prompt = guardrails.separar(POLITICA, mensaje, limpio)
    respuesta = modelo_simulado(prompt, limpio)
    if not guardrails.salida_valida(respuesta, PALABRA):
        respuesta = "RETENIDA (salida): la respuesta contenía la palabra reservada."
    avisos = "".join(f"AVISO (documento): línea descartada: {l}\n" for l in descartadas)
    return prompt, avisos + respuesta

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--prompt"]
    if len(args) not in (2, 3) or args[0] not in ("vulnerable", "protegido"):
        sys.exit(__doc__)
    if len(args) == 3 and not Path(args[2]).is_file():
        sys.exit(f"ERROR: no existe el documento {args[2]}")
    documento = Path(args[2]).read_text(encoding="utf-8") if len(args) == 3 else ""
    prompt, respuesta = (vulnerable if args[0] == "vulnerable" else protegido)(args[1], documento)
    if "--prompt" in sys.argv and prompt:
        print(f"--- prompt enviado al modelo simulado ---\n{prompt}\n---")
    print(respuesta)
