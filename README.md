# DevSecOps aplicado a IA · Laboratorio transversal

**Entorno docente aislado**, no apto para producción. Utiliza datos de empresas ficticias, un modelo **simulado** y un servicio HTTP didáctico de herramientas que **no implementa MCP completo**.

El proyecto evoluciona a lo largo del curso: cada unidad incorpora nuevas funcionalidades y controles de seguridad. Esta versión corresponde a la **Unidad 1** (`course_stage.json`): arquitectura básica con tres servicios.

| Servicio | Función |
|---|---|
| `api` | API FastAPI: recibe las consultas, recupera documentos y coordina los servicios |
| `mock-llm` | Proveedor de lenguaje simulado: devuelve una respuesta determinista marcada como `[SIMULADO]` |
| `tools` | Servicio de herramientas de solo lectura |

## Arranque

```bash
docker compose config
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

Swagger: http://127.0.0.1:8000/docs

```bash
curl -s -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"política de vacaciones","tenant":"empresa-a"}'
```

## Pruebas

Sin contenedores:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

Dentro del contenedor de la API, montando la carpeta de pruebas:

```bash
docker compose run --rm -v "$PWD/tests:/code/tests" api python -m pytest -q
```

## Registros y limpieza

```bash
docker compose logs --tail=30 api
docker compose down
```

## Reglas del laboratorio

- La API solo se publica en `127.0.0.1`; `mock-llm` y `tools` permanecen en la red privada de Docker.
- El servicio de herramientas nunca ejecuta operaciones destructivas.
- No despliegues este laboratorio en un servidor accesible desde Internet.
- Nunca introduzcas credenciales ni datos reales.
