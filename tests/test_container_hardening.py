"""Unidad 5: endurecimiento del contenedor en el que se ejecutan estas pruebas.

Comprueban la configuración efectiva vista desde dentro (usuario, montajes, capacidades,
no-new-privileges y cgroups), no lo que dice un fichero. `docker compose run` crea el
contenedor con la configuración del servicio, así que el mismo fichero sirve para
cualquiera de los tres servicios (desde la carpeta del proyecto):

    docker compose run --rm --no-deps -v ./tests:/code/tests:ro SERVICIO python -m pytest -q -p no:cacheprovider /code/tests/test_container_hardening.py

Fuera de un contenedor (por ejemplo, con Python en el equipo) se omiten.
"""
import errno
import os
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(not Path('/.dockerenv').exists(), reason='solo tiene sentido dentro de un contenedor Docker')

CGROUP = Path('/sys/fs/cgroup')
# Límites máximos aceptados en el laboratorio: lo que se comprueba es que existe un límite razonable.
MEMORIA_MAXIMA = 512 * 1024 * 1024
PROCESOS_MAXIMOS = 256

def estado_proceso() -> dict[str, str]:
    lineas = Path('/proc/self/status').read_text().splitlines()
    return dict(linea.split(':', 1) for linea in lineas if ':' in linea)

def montaje(punto: str) -> tuple[str, set[str]] | None:
    """Tipo y opciones del montaje visible en `punto` (el último montado prevalece)."""
    encontrado = None
    for linea in Path('/proc/self/mounts').read_text().splitlines():
        _, destino, tipo, opciones, *_ = linea.split()
        if destino == punto:
            encontrado = (tipo, set(opciones.split(',')))
    return encontrado

def cgroup(*rutas: str) -> str:
    """Primer fichero existente: cgroup v2 (Docker actual) o cgroup v1."""
    for ruta in rutas:
        fichero = CGROUP / ruta
        if fichero.exists():
            return fichero.read_text().strip()
    pytest.fail(f'no se encuentra ninguno de {rutas} en {CGROUP}')

# --- Usuario (ejemplo 2) ---

def test_process_runs_as_non_root():
    assert os.geteuid() != 0, 'el proceso se ejecuta como root (UID 0)'
    assert os.getegid() != 0, 'el proceso pertenece al grupo root (GID 0)'
    assert 0 not in os.getgroups(), 'el proceso tiene root como grupo suplementario'

# --- Sistema de archivos (ejemplo 3) ---

def test_root_filesystem_is_read_only():
    raiz = montaje('/')
    assert raiz is not None and 'ro' in raiz[1], 'el sistema de archivos raíz admite escritura'
    with pytest.raises(OSError) as error:
        Path('/code/escritura-de-prueba').write_text('no debería poder escribirse')
    assert error.value.errno in (errno.EROFS, errno.EACCES)

def test_tmp_is_writable_tmpfs():
    tmp = montaje('/tmp')
    assert tmp is not None, '/tmp no es un montaje propio: falta tmpfs'
    tipo, opciones = tmp
    assert tipo == 'tmpfs'
    assert {'noexec', 'nosuid', 'nodev'} <= opciones
    fichero = Path('/tmp') / f'prueba-{os.getpid()}'
    fichero.write_text('ok')
    assert fichero.read_text() == 'ok'
    fichero.unlink()

# --- Privilegios (ejemplo 4) ---

def test_capabilities_are_dropped():
    estado = estado_proceso()
    # CapBnd es el límite máximo que el proceso podría llegar a obtener: con cap_drop ALL es 0.
    for campo in ('CapEff', 'CapPrm', 'CapBnd'):
        assert int(estado[campo], 16) == 0, f'{campo} = {estado[campo].strip()}'

def test_no_new_privileges_is_enabled():
    assert estado_proceso()['NoNewPrivs'].strip() == '1'

# --- Recursos (ejemplo 6) ---

def test_memory_limit_is_set():
    valor = cgroup('memory.max', 'memory/memory.limit_in_bytes')
    assert valor != 'max' and int(valor) <= MEMORIA_MAXIMA, f'memoria sin límite razonable: {valor}'
    # Sin memswap_limit, Docker permite usar en swap otro tanto como mem_limit.
    swap = CGROUP / 'memory.swap.max'
    if swap.exists():
        assert swap.read_text().strip() == '0', f'el contenedor puede usar swap: {swap.read_text().strip()}'

def test_cpu_limit_is_set():
    if (CGROUP / 'cpu.max').exists():
        cuota = (CGROUP / 'cpu.max').read_text().split()[0]
        assert cuota != 'max', 'CPU sin límite'
    else:
        assert int(cgroup('cpu/cpu.cfs_quota_us')) > 0, 'CPU sin límite'

def test_pids_limit_is_set():
    valor = cgroup('pids.max', 'pids/pids.max')
    assert valor != 'max' and int(valor) <= PROCESOS_MAXIMOS, f'procesos sin límite razonable: {valor}'
