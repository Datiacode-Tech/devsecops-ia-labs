"""utilidades_texto 1.0.0 · paquete ficticio de la Unidad 6 (cadena de suministro).

Representa un componente de terceros descargado de Internet. Solo se usa para calcular
y comprobar su hash SHA-256: no hace falta ejecutarlo.
"""


def normalizar(texto: str) -> str:
    """Quita espacios sobrantes y pasa el texto a minúsculas."""
    return " ".join(texto.split()).lower()


def contar_palabras(texto: str) -> int:
    """Cuenta las palabras de un texto."""
    return len(texto.split())
