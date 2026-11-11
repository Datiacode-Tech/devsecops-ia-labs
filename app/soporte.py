"""Informe de diagnóstico para adjuntar a las incidencias de soporte.

Módulo preparado por el equipo de operaciones. Todavía no está conectado a la API:
antes de usarlo debe superar una revisión de seguridad (ejercicio de la Unidad 4).
"""
from collections.abc import Mapping

def generar_informe(entorno: Mapping[str, str], cabeceras: Mapping[str, str], error: str) -> str:
    """Construye un informe de texto con el error, el entorno del servicio y la petición que falló."""
    lineas = ['INFORME DE DIAGNOSTICO', f'Error: {error}', '', '[Entorno del servicio]']
    lineas += [f'{nombre}={valor}' for nombre, valor in sorted(entorno.items())]
    lineas += ['', '[Cabeceras de la peticion]']
    lineas += [f'{nombre}: {valor}' for nombre, valor in sorted(cabeceras.items())]
    return '\n'.join(lineas) + '\n'
