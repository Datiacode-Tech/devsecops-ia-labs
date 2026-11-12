"""Unidad 5: los límites de recursos protegen el equipo (ejemplo 6).

Todo está acotado aunque el contenedor no tuviera límites: como máximo 150 hilos en reposo
y 384 MiB de memoria. Se ejecuta en un contenedor efímero; si el núcleo lo detiene por
exceder la memoria, solo termina ese contenedor (código de salida 137).

Uso (desde la carpeta del proyecto, igual en WSL/Linux y PowerShell):
    docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro SERVICIO python -m scripts.demo_unidad_05_limites
"""
import threading
import time
from pathlib import Path

MAX_HILOS = 150
BLOQUE_MIB = 16
MAX_MIB = 384

def leer(nombre: str) -> str:
    fichero = Path('/sys/fs/cgroup') / nombre
    return fichero.read_text().strip() if fichero.exists() else 'no disponible'

print('1. Límites vistos desde dentro (cgroup v2)')
memoria = leer('memory.max')
print(f'    memory.max  {memoria}' + (f'  ({int(memoria) // 2**20} MiB)' if memoria.isdigit() else ''))
print(f'    cpu.max     {leer("cpu.max")}   (cuota y periodo en microsegundos)')
print(f'    pids.max    {leer("pids.max")}')

print(f'2. Crear hasta {MAX_HILOS} hilos en reposo')
parar = threading.Event()
hilos = []
try:
    for _ in range(MAX_HILOS):
        hilo = threading.Thread(target=parar.wait, daemon=True)
        hilo.start()
        hilos.append(hilo)
    print(f'    creados {len(hilos)}: el límite de procesos no se ha alcanzado')
except RuntimeError as e:
    print(f'    creados {len(hilos)}; el siguiente falla: {e}')
parar.set()
for hilo in hilos:
    hilo.join()

print(f'3. Reservar memoria en bloques de {BLOQUE_MIB} MiB, hasta {MAX_MIB} MiB')
bloques = []
for total in range(BLOQUE_MIB, MAX_MIB + 1, BLOQUE_MIB):
    bloques.append(bytearray(BLOQUE_MIB * 2**20))   # bytearray escribe ceros: la memoria se usa de verdad
    print(f'    reservados {total} MiB', flush=True)
    time.sleep(0.05)
print('    reservada toda la memoria: el límite de memoria no se ha alcanzado')
