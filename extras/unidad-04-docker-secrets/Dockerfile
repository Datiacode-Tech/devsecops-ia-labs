# Ejemplo 4 (Unidad 4): API mínima que lee su clave de un secreto de Docker Compose.
# Imagen base fijada por versión y digest.
FROM python:3.12.16-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /demo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Solo se copia el código: el secreto nunca forma parte de la imagen (ver .dockerignore).
COPY app app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
