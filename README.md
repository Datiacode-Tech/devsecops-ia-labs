# DevSecOps aplicado a IA · Laboratorio transversal

**Entorno docente aislado**, no apto para producción. Utiliza datos de empresas ficticias, un modelo **simulado** y un servicio HTTP didáctico de herramientas que **no implementa MCP completo**.

El proyecto evoluciona a lo largo del curso: cada unidad incorpora nuevas funcionalidades y controles de seguridad. Esta versión corresponde a los **ejemplos guiados de la Unidad 3: Desarrollo seguro y protección de APIs de IA** (`course_stage.json`, etapa 3).

## Objetivos de la Unidad 3

- Proteger los endpoints de la API con una clave enviada en la cabecera `x-api-key`.
- Mantener la clave fuera del código: se genera en el propio equipo y se guarda en `.env`, que no se sube a Git.
- Validar las preguntas antes de que lleguen al modelo: ni vacías ni de más de 300 caracteres.
- Distinguir **autenticación** (quién llama) de **autorización** (qué puede hacer y a qué datos accede).
- Obtener evidencia de cada control con pruebas automatizadas y relacionarla con el registro de riesgos.

## Qué cambia respecto a la Unidad 2

En la Unidad 2 cualquiera que llegara a la API podía consultarla sin credencial (riesgo R-01). En esta versión:

| Control | Implementación |
|---|---|
| Autenticación por API key | Cabecera `x-api-key`, comprobada por una dependencia reutilizable (`require_api_key` en `app/security.py`) con el esquema `APIKeyHeader` de FastAPI |
| Endpoints protegidos | `POST /ask` y `POST /tools/execute`. `GET /health` sigue siendo público |
| Comparación segura | `hmac.compare_digest`: tarda lo mismo acierte o falle, para que el tiempo de respuesta no revele cuántos caracteres coinciden |
| Respuesta 401 única | El mismo mensaje sin clave y con clave incorrecta. La respuesta nunca contiene la clave |
| Clave fuera del código | Variable `DEMO_API_KEY` leída de `.env` por Docker Compose, sin valor por defecto. La API no arranca si falta, mantiene el valor de ejemplo o tiene menos de 16 caracteres |
| Validación de preguntas | Pydantic (`StringConstraints`): entre 1 y 300 caracteres, sin contar los espacios iniciales y finales. Fuera de ese rango, `422` |

Se mantienen las medidas anteriores: API publicada solo en `127.0.0.1`, validación estructural de las peticiones y bloqueo de operaciones destructivas (`403` para cualquier operación distinta de `read_document`).

## Arquitectura

```
Equipo (127.0.0.1:8000)
        │  x-api-key
        ▼
   ┌─────────┐   red privada de Docker   ┌──────────┐
   │   api   │ ────────────────────────▶ │ mock-llm │  modelo simulado [SIMULADO]
   │ FastAPI │ ────────────────────────▶ │  tools   │  herramientas de solo lectura
   └─────────┘                           └──────────┘
```

| Servicio | Función |
|---|---|
| `api` | API FastAPI: autentica, valida, recupera documentos y coordina los servicios |
| `mock-llm` | Proveedor de lenguaje simulado: devuelve una respuesta determinista marcada como `[SIMULADO]` |
| `tools` | Servicio de herramientas de solo lectura |

Solo `api` publica un puerto, y solo en el propio equipo. `mock-llm` y `tools` no son accesibles desde fuera de Docker.

## Requisitos

- **Docker**: Docker Desktop en Windows (con el motor WSL 2) o Docker Engine con el complemento Compose v2 en Linux / WSL.
- **Git**.
- **Navegador web** para Swagger.
- Puerto `8000` libre en el propio equipo.
- No hace falta Python: la clave se genera y las pruebas se ejecutan dentro de contenedores.

Comprobar las herramientas (igual en WSL / Linux y en PowerShell):

```bash
git --version
docker --version
docker compose version
```

## Preparación

### 1. Descargar la versión de la Unidad 3

El mismo comando sirve en WSL / Linux y en PowerShell:

```bash
git clone --branch unidad-03-ejemplos https://github.com/Datiacode-Tech/devsecops-ia-labs.git devsecops-ia-unidad-03
cd devsecops-ia-unidad-03
```

Git avisa de que la copia está en estado *detached HEAD*: es lo normal al descargar una etiqueta.

### 2. Crear `.env` con una clave generada

La clave se genera con el generador criptográfico de Python (`secrets.token_urlsafe`) **dentro de un contenedor** y se escribe directamente en `.env`, sin mostrarla en pantalla ni escribirla en el código. `.env` está excluido de Git (`.gitignore`) y de la imagen Docker (`.dockerignore`).

WSL / Linux:

```bash
cp .env.example .env
CLAVE=$(docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))")
sed -i "s|^DEMO_API_KEY=.*|DEMO_API_KEY=${CLAVE}|" .env
unset CLAVE
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
$clave = docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))"
(Get-Content .env) -replace '^DEMO_API_KEY=.*', "DEMO_API_KEY=$clave" | Set-Content -Encoding ascii .env
Remove-Variable clave
```

- La primera vez Docker descarga la imagen `python:3.12-slim` (mensaje «Unable to find image… Pulling»): es normal.
- La clave generada tiene 32 caracteres y queda solo en `.env`.
- `.env.example` no lleva tildes a propósito: Windows PowerShell 5.1 reescribe el fichero y los caracteres no ASCII podrían alterarse.

### 3. Validar la configuración y arrancar

Igual en WSL / Linux y en PowerShell:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

- `docker compose config --quiet` no muestra nada si la configuración es correcta. Sin `.env` muestra: `required variable DEMO_API_KEY is missing a value`.
- **No ejecutes `docker compose config` sin `--quiet`** si vas a compartir la salida: muestra el valor de la clave.
- `docker compose ps` debe mostrar `api`, `mock-llm` y `tools` en estado `running`. La primera construcción tarda unos minutos.
- Si `.env` mantiene el valor de ejemplo, `api` termina (`Exited (1)`) y `docker compose logs api` explica el motivo sin mostrar ningún valor.

### 4. Abrir Swagger

Abre http://127.0.0.1:8000/docs en el navegador. Los endpoints protegidos muestran un candado. Pulsa **Authorize**, pega la clave (cópiala de `.env`) y confirma. Después usa **Try it out** en cada endpoint.

### 5. Cargar la clave en la terminal sin mostrarla

WSL / Linux:

```bash
set -a; . ./.env; set +a
```

Windows PowerShell:

```powershell
$env:DEMO_API_KEY = (Select-String -Path .env -Pattern '^DEMO_API_KEY=(.+)$').Matches[0].Groups[1].Value
```

### 6. Función auxiliar de PowerShell

`Invoke-WebRequest` lanza una excepción con los códigos 4xx. Esta función muestra siempre el código HTTP y el cuerpo de la respuesta. Pégala una vez en la sesión de PowerShell:

```powershell
function Invoke-Lab {
    param([string]$Metodo, [string]$Ruta, $Cuerpo = $null, [string]$Clave = '')
    $cabeceras = @{}
    if ($Clave) { $cabeceras['x-api-key'] = $Clave }
    $p = @{ Uri = "http://127.0.0.1:8000$Ruta"; Method = $Metodo; Headers = $cabeceras; UseBasicParsing = $true }
    if ($null -ne $Cuerpo) {
        $p.ContentType = 'application/json; charset=utf-8'
        $p.Body = [Text.Encoding]::UTF8.GetBytes(($Cuerpo | ConvertTo-Json -Compress))
    }
    try {
        $r = Invoke-WebRequest @p
        "HTTP $($r.StatusCode) $([Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()))"
    } catch {
        "HTTP $([int]$_.Exception.Response.StatusCode) $($_.ErrorDetails.Message)"
    }
}

$pregunta = @{ question = '¿Cuántos días de vacaciones tengo?'; tenant = 'empresa-a' }
```

Si los acentos se ven mal en la consola de PowerShell, ejecuta antes `[Console]::OutputEncoding = [Text.Encoding]::UTF8`.

## Ejemplos guiados

Resumen de los resultados esperados:

| Situación | HTTP |
|---|---|
| `GET /health` sin clave | 200 |
| `POST /ask` sin clave | 401 |
| `POST /ask` con clave incorrecta | 401 |
| `POST /ask` con clave correcta y pregunta válida | 200 |
| Pregunta vacía o de más de 300 caracteres, con clave correcta | 422 |
| `delete_document` con clave correcta | 403 |

### Ejemplo 1. Comprobar que la API funciona

- **Objetivo:** confirmar que el servicio responde y que es la versión de la Unidad 3.
- **Control:** `/health` es público a propósito, para la monitorización, y no expone datos.

```bash
curl -s -w ' HTTP %{http_code}\n' http://127.0.0.1:8000/health
```

```powershell
Invoke-Lab GET /health
```

- **Resultado esperado:** `HTTP 200` y `{"status":"ok","stage":3,"model":"mock"}`.
- **Qué demuestra:** la API está en marcha sin pedir clave; `stage: 3` identifica la unidad.

### Ejemplo 2. Consulta sin autenticación

- **Objetivo:** comprobar que `/ask` ya no admite peticiones anónimas (en la Unidad 2 devolvía 200).
- **Control:** la dependencia `require_api_key`.

```bash
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿Cuántos días de vacaciones tengo?","tenant":"empresa-a"}'
```

```powershell
Invoke-Lab POST /ask $pregunta
```

- **Resultado esperado:** `HTTP 401` y `{"detail":"Credencial ausente o incorrecta"}`.
- **Qué demuestra:** sin credencial, la petición no llega a la recuperación de documentos ni al modelo. R-01 deja de ser explotable.

### Ejemplo 3. Clave incorrecta

- **Objetivo:** comprobar que una clave inventada se rechaza igual que la ausencia de clave.
- **Control:** comparación en tiempo constante y mensaje único.

```bash
INCORRECTA=clave-incorrecta-de-prueba
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $INCORRECTA" \
  -d '{"question":"¿Cuántos días de vacaciones tengo?","tenant":"empresa-a"}'
```

```powershell
Invoke-Lab POST /ask $pregunta 'clave-incorrecta-de-prueba'
```

- **Resultado esperado:** `HTTP 401` y el mismo mensaje del ejemplo 2.
- **Qué demuestra:** el mensaje no permite distinguir «falta la clave» de «la clave está mal», así que no da pistas a quien intenta adivinarla. La respuesta nunca contiene la clave.

### Ejemplo 4. Consulta con clave válida (terminal y Swagger)

- **Objetivo:** comprobar que una petición autenticada funciona igual que antes.
- **Control:** la dependencia deja pasar la petición cuando la clave coincide.

```bash
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d '{"question":"¿Cuántos días de vacaciones tengo?","tenant":"empresa-a"}'
```

```powershell
Invoke-Lab POST /ask $pregunta $env:DEMO_API_KEY
```

- **Resultado esperado:** `HTTP 200`. `answer` empieza por `[SIMULADO]`, `sources` contiene `empresa-a-001` y `empresa-a-002`, y `stage` vale 3.
- **En Swagger:** **Authorize** con la clave, después `POST /ask` → **Try it out** → **Execute**. Sin autorizar, Swagger obtiene el mismo 401 del ejemplo 2.
- **Qué demuestra:** la autenticación no cambia el comportamiento para quien tiene la clave. Observa que el texto del documento `empresa-a-002` sigue llegando a la respuesta: autenticar la petición no filtra el contexto que recibe el modelo.

### Ejemplo 5. Pregunta que supera el límite

- **Objetivo:** comprobar el límite de 300 caracteres y el rechazo de preguntas vacías.
- **Control:** `StringConstraints` de Pydantic en el modelo `Question` (`QUESTION_MAX_LENGTH = 300`).

WSL / Linux:

```bash
LARGA=$(printf 'x%.0s' $(seq 301))
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d "{\"question\":\"$LARGA\"}"

JUSTA=$(printf 'x%.0s' $(seq 300))
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d "{\"question\":\"$JUSTA\"}"

curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d '{"question":""}'

curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d "{\"question\":\"$LARGA\"}"
```

Windows PowerShell:

```powershell
Invoke-Lab POST /ask @{ question = ('x' * 301) } $env:DEMO_API_KEY
Invoke-Lab POST /ask @{ question = ('x' * 300) } $env:DEMO_API_KEY
Invoke-Lab POST /ask @{ question = '' } $env:DEMO_API_KEY
Invoke-Lab POST /ask @{ question = ('x' * 301) }
```

| Pregunta | Resultado esperado |
|---|---|
| 301 caracteres, con clave | `HTTP 422`, `"type":"string_too_long"` |
| 300 caracteres, con clave | `HTTP 200` |
| Vacía, con clave | `HTTP 422`, `"type":"string_too_short"` |
| 301 caracteres, **sin** clave | `HTTP 401` |

- **Qué demuestra:** la validación rechaza la entrada antes de que llegue al modelo, lo que reduce el abuso con entradas largas.
- **Orden de las comprobaciones:** con un cuerpo JSON bien formado se comprueba primero la clave, así que una petición sin clave recibe `401` aunque la pregunta sea demasiado larga. Un cuerpo que no es JSON válido recibe `422` antes de comprobar la clave, porque FastAPI lo analiza primero.
- La respuesta `422` de FastAPI repite el texto enviado en el campo `input`.

### Ejemplo 6. Operación destructiva con clave válida

- **Objetivo:** comprobar que autenticarse no da permiso para todo.
- **Control:** lista de operaciones permitidas en `/tools/execute` (desde la Unidad 1), ahora detrás de la autenticación.

```bash
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/tools/execute \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d '{"operation":"delete_document","document_id":"empresa-a-001"}'

curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/tools/execute \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d '{"operation":"read_document","document_id":"empresa-a-001"}'

curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/tools/execute \
  -H 'Content-Type: application/json' \
  -d '{"operation":"read_document","document_id":"empresa-a-001"}'
```

```powershell
Invoke-Lab POST /tools/execute @{ operation = 'delete_document'; document_id = 'empresa-a-001' } $env:DEMO_API_KEY
Invoke-Lab POST /tools/execute @{ operation = 'read_document'; document_id = 'empresa-a-001' } $env:DEMO_API_KEY
Invoke-Lab POST /tools/execute @{ operation = 'read_document'; document_id = 'empresa-a-001' }
```

| Variante | Resultado esperado |
|---|---|
| `delete_document`, con clave | `HTTP 403` y `{"detail":"Operación no permitida"}` |
| `read_document`, con clave | `HTTP 200` y `"status":"read-only"` |
| `read_document`, sin clave | `HTTP 401` |

- **Qué demuestra:** `401` significa «no sé quién eres»; `403`, «sé quién eres, pero esto no está permitido». La autenticación se suma a la lista de operaciones permitidas; no la sustituye.

### Ejemplo 7. Pruebas automatizadas

- **Objetivo:** obtener evidencia automatizada de todos los controles.
- **Cómo:** pytest dentro del contenedor de la API, con `tests/` y `security/` montados en solo lectura. Requiere `.env` configurado.

WSL / Linux:

```bash
docker compose run --rm \
  -v ./tests:/code/tests:ro \
  -v ./security:/code/security:ro \
  -e PYTHONDONTWRITEBYTECODE=1 \
  api python -m pytest -q -p no:cacheprovider /code/tests
```

Windows PowerShell (en una sola línea):

```powershell
docker compose run --rm -v ./tests:/code/tests:ro -v ./security:/code/security:ro -e PYTHONDONTWRITEBYTECODE=1 api python -m pytest -q -p no:cacheprovider /code/tests
```

- **Resultado esperado:** `22 passed` (puede aparecer `1 warning`, una deprecación de Starlette ajena al laboratorio).
- **Qué demuestra:** cada control tiene al menos una prueba. `test_ask_requires_api_key` es la evidencia de R-01 en el registro de riesgos.

| Fichero | Qué comprueba |
|---|---|
| `tests/test_api.py` | `/health` público; `401` sin clave o con clave incorrecta en `/ask` y `/tools/execute`; `200` con clave válida; `403` en `delete_document`; `401` antes que `422`; preguntas vacías, en blanco, de 300 y de 301 caracteres; R-02 sigue abierto |
| `tests/test_local_logic.py` | Coherencia de los documentos, etapa 3 y rechazo al arrancar de una clave ausente, vacía, de ejemplo o demasiado corta |
| `tests/test_risk_register.py` | Estructura del registro y evidencias existentes o pendientes |
| `tests/conftest.py` | Clave de las pruebas: la de `.env` dentro del contenedor, o una temporal si se ejecutan fuera |

Opcional, sin contenedores y con Python 3 en el equipo (las pruebas generan una clave temporal si no existe `DEMO_API_KEY`):

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

### Ejemplo 8. Registros y riesgos pendientes

- **Objetivo:** revisar qué queda registrado y qué riesgos siguen abiertos.

```bash
docker compose logs --tail=30 api
```

- **Resultado esperado:** líneas con `401 Unauthorized`, `200 OK`, `422 Unprocessable Entity` y `403 Forbidden`. La clave no aparece en los registros.

Riesgo que sigue abierto (R-02, acceso a documentos de otra empresa):

```bash
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $DEMO_API_KEY" \
  -d '{"question":"presupuesto","tenant":"empresa-a"}'
```

```powershell
Invoke-Lab POST /ask @{ question = 'presupuesto'; tenant = 'empresa-a' } $env:DEMO_API_KEY
```

- **Resultado esperado:** `HTTP 200` y `sources` incluye `empresa-b-001`.
- **Qué demuestra:** con una clave válida, `empresa-a` sigue obteniendo un documento confidencial de `empresa-b`. La clave autentica, pero no autoriza por tenant: todas las peticiones válidas se atribuyen a la misma identidad y el campo `tenant` no se usa para filtrar. **Autenticación no es autorización.** Este riesgo se trata en la Unidad 10.

Opcional, si el equipo tiene Python 3: `python scripts/demo_unidad_03.py` ejecuta la secuencia de comprobaciones de los ejemplos 1 a 6.

## Registro de riesgos

`security/risk_register.csv` relaciona cada riesgo con su control y su evidencia. Una evidencia `test_*` es una prueba que existe en `tests/`; una evidencia pendiente (`pendiente_*` o `*_pendiente`) es una prueba prevista que todavía no existe, y ese riesgo no puede figurar como `Mitigado`.

| Riesgo | Estado en la Unidad 3 |
|---|---|
| R-01 Acceso sin credencial | Mitigado: `/ask` y `/tools/execute` exigen la clave (`test_ask_requires_api_key`) |
| R-02 Acceso a tenant ajeno | En seguimiento (Unidad 10): la clave autentica, pero no limita los documentos al tenant |
| R-03 Acción no autorizada | Mitigado: lista de operaciones permitidas (`test_mutation_is_denied`) |

Limitaciones que siguen abiertas en esta versión:

- Una única clave compartida, sin identidad por usuario ni por tenant.
- Sin rotación ni caducidad de la clave.
- Clave guardada en un fichero local.
- Sin límite de peticiones.
- HTTP sin cifrar, aunque solo en el propio equipo.
- El contenido no fiable de los documentos sigue llegando al modelo.

La gestión de secretos se trata en la Unidad 4.

## Detener el laboratorio

```bash
docker compose down
```

Detiene y elimina los contenedores y la red del laboratorio. Las imágenes y `.env` se conservan, así que el siguiente arranque es más rápido.

## Reglas del laboratorio

- La API solo se publica en `127.0.0.1`; `mock-llm` y `tools` permanecen en la red privada de Docker.
- El servicio de herramientas nunca ejecuta operaciones destructivas.
- No subas `.env` a Git ni compartas la clave.
- No despliegues este laboratorio en un servidor accesible desde Internet.
- Nunca introduzcas credenciales ni datos reales.
