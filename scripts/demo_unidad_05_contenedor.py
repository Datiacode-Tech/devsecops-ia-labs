"""Unidad 5: qué puede hacer un proceso dentro de su contenedor (ejemplos 2, 3 y 4).

Se ejecuta en un contenedor efímero creado con la configuración del servicio indicado, por
lo que no afecta a los contenedores en marcha. No muestra variables de entorno ni secretos.

Uso (desde la carpeta del proyecto, igual en WSL/Linux y PowerShell):
    docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro SERVICIO python -m scripts.demo_unidad_05_contenedor
"""
import errno
import os
import socket
from pathlib import Path

# Nombres de las capacidades de Linux por número de bit (include/uapi/linux/capability.h).
CAPACIDADES = [
    'CHOWN', 'DAC_OVERRIDE', 'DAC_READ_SEARCH', 'FOWNER', 'FSETID', 'KILL', 'SETGID', 'SETUID',
    'SETPCAP', 'LINUX_IMMUTABLE', 'NET_BIND_SERVICE', 'NET_BROADCAST', 'NET_ADMIN', 'NET_RAW',
    'IPC_LOCK', 'IPC_OWNER', 'SYS_MODULE', 'SYS_RAWIO', 'SYS_CHROOT', 'SYS_PTRACE', 'SYS_PACCT',
    'SYS_ADMIN', 'SYS_BOOT', 'SYS_NICE', 'SYS_RESOURCE', 'SYS_TIME', 'SYS_TTY_CONFIG', 'MKNOD',
    'LEASE', 'AUDIT_WRITE', 'AUDIT_CONTROL', 'SETFCAP', 'MAC_OVERRIDE', 'MAC_ADMIN', 'SYSLOG',
    'WAKE_ALARM', 'BLOCK_SUSPEND', 'AUDIT_READ', 'PERFMON', 'BPF', 'CHECKPOINT_RESTORE',
]

def estado() -> dict[str, str]:
    return {k: v.strip() for k, v in (l.split(':', 1) for l in Path('/proc/self/status').read_text().splitlines() if ':' in l)}

def capacidades(mascara: str) -> str:
    valor = int(mascara, 16)
    nombres = [n for i, n in enumerate(CAPACIDADES) if valor >> i & 1]
    return f'{len(nombres)}: {", ".join(nombres)}' if nombres else '0 (ninguna)'

def intento(descripcion: str, accion) -> None:
    try:
        accion()
        resultado = 'PERMITIDO'
    except OSError as e:
        resultado = f'denegado ({errno.errorcode.get(e.errno, e.errno)}: {e.strerror})'
    print(f'    {descripcion:<52} {resultado}')

def escribir(ruta: str):
    def accion():
        Path(ruta).write_text('prueba')
        Path(ruta).unlink()
    return accion

def modificar_codigo():
    # Abre en modo «añadir» sin escribir nada: basta para comprobar el permiso.
    objetivo = next(p for p in Path('/code').glob('*/main.py'))
    with objetivo.open('a'):
        pass

def cambiar_propietario():
    ruta = Path('/tmp/propietario')
    ruta.write_text('x')
    try:
        os.chown(ruta, 12345, 12345)        # requiere CAP_CHOWN
    finally:
        ruta.unlink()

def socket_crudo():
    socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP).close()   # requiere CAP_NET_RAW

def montaje(punto: str) -> str:
    encontrado = 'sin montaje propio'
    for linea in Path('/proc/self/mounts').read_text().splitlines():
        _, destino, tipo, opciones, *_ = linea.split()
        if destino == punto:
            # Se omiten las rutas internas de overlayfs (lowerdir, upperdir, workdir).
            utiles = [o for o in opciones.split(',') if not o.endswith('dir') and 'dir=' not in o and o != 'relatime']
            encontrado = f'{tipo} ({",".join(utiles)})'
    return encontrado

s = estado()
print('1. Identidad del proceso')
print(f'    UID {os.geteuid()}  GID {os.getegid()}  grupos {os.getgroups()}')
print('2. Capacidades del kernel')
print(f'    efectivas (CapEff):      {capacidades(s["CapEff"])}')
print(f'    límite máximo (CapBnd):  {capacidades(s["CapBnd"])}')
print(f'    no-new-privileges:       {"activado" if s["NoNewPrivs"] == "1" else "desactivado"}')
print('3. Sistema de archivos')
print(f'    /     {montaje("/")}')
print(f'    /tmp  {montaje("/tmp")}')
print('4. Intentos')
intento('modificar el código de la aplicación', modificar_codigo)
intento('crear un fichero en /code', escribir('/code/nuevo.txt'))
intento('crear un fichero en /etc', escribir('/etc/prueba'))
intento('crear un fichero en /tmp', escribir(f'/tmp/prueba-{os.getpid()}'))
intento('cambiar el propietario de un fichero (CAP_CHOWN)', cambiar_propietario)
intento('abrir un socket de red crudo (CAP_NET_RAW)', socket_crudo)
