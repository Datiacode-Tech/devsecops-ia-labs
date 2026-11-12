FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Usuario de sistema sin privilegios, sin contraseña, sin directorio personal y sin shell de acceso.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app
# El código pertenece a root y el usuario app solo puede leerlo: aunque la aplicación se vea
# comprometida, no puede modificar su propio código.
COPY app app
COPY data data
COPY course_stage.json .
# A partir de aquí todo se ejecuta como app. Se indica el UID numérico para que pueda
# comprobarse sin consultar /etc/passwd.
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
