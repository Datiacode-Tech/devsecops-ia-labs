# DevSecOps aplicado a IA · Laboratorio transversal

**Entorno docente aislado**, no apto para producción. Utiliza datos de empresas ficticias, un modelo **simulado** y un servicio HTTP didáctico de herramientas que **no implementa MCP completo**.

El proyecto evoluciona a lo largo del curso: cada unidad incorpora nuevas funcionalidades y controles de seguridad. Esta versión corresponde a los **ejemplos de la Unidad 4: Gestión segura de secretos y credenciales** (`course_stage.json`, etapa 4).

## Objetivos de la Unidad 4

- Tratar la API key del laboratorio como un **secreto** durante todo su ciclo de vida: generación, almacenamiento, uso, registro y rotación.
- Mantener las credenciales fuera del código, de Git y de la imagen Docker.
- Impedir que la API arranque con claves ausentes, cortas o de ejemplo.
- Evitar que las credenciales aparezcan en los registros.
- Rotar una clave comprometida y comprobar que la antigua deja de funcionar.
- Conocer las limitaciones de las variables de entorno y una alternativa: Docker Compose Secrets.

La técnica que se repite en todos los ejemplos es **comprobar sin mostrar**: se cuenta cuántas veces aparece la clave en un lugar, nunca se imprime.

## Qué cambia respecto a la Unidad 3

| Control | Implementación |
|---|---|
| Rechazo de claves inseguras | La API no arranca si la clave falta, tiene menos de 16 caracteres, contiene valores de ejemplo conocidos (`cambia-esta-clave`, `curso-demo-key`, `password`…) o tiene menos de 8 caracteres distintos (`app/config.py`). El error indica el motivo, nunca el valor |
| Registros sin credenciales | Los rechazos se registran con el motivo (`credencial ausente` o `credencial incorrecta`), sin el valor. Un filtro (`app/log_redaction.py`) sustituye por `[REDACTADO]` la clave configurada y cualquier `x-api-key`, `DEMO_API_KEY` o `authorization` con valor, en los registros de la API y de uvicorn |
| Rotación de la clave | Nueva clave en `.env` y recreación solo del servicio `api` |
| Docker Compose Secrets | Ejemplo independiente en `extras/unidad-04-docker-secrets/` |
| Pruebas | `tests/test_secrets.py`: configuración, respuestas, registros y rotación |

Se mantienen los controles de las unidades anteriores:

- `x-api-key` obligatoria en `POST /ask` y `POST /tools/execute`; `GET /health` es público;
- preguntas de 1 a 300 caracteres;
- validación de `ToolCall`: `operation` de 1 a 40 caracteres y `document_id` con el formato `empresa-<nombre>-<tres dígitos>` y 60 caracteres como máximo (`422` si no se cumple);
- operaciones destructivas bloqueadas (`403`);
- API publicada solo en `127.0.0.1`.

## Arquitectura

```
Equipo (127.0.0.1:8000)
        │  x-api-key
        ▼
   ┌─────────┐   red privada de Docker   ┌──────────┐
   │   api   │ ────────────────────────▶ │ mock-llm │  modelo simulado [SIMULADO]
   │ FastAPI │ ────────────────────────▶ │  tools   │  herramientas de solo lectura
   └─────────┘                           └──────────┘
       ▲
   DEMO_API_KEY desde .env (solo api la recibe)
```

| Servicio | Función | ¿Recibe la clave? |
|---|---|---|
| `api` | API FastAPI: autentica, valida, recupera documentos y coordina los servicios | Sí, como variable de entorno |
| `mock-llm` | Proveedor de lenguaje simulado: respuesta determinista marcada como `[SIMULADO]` | No |
| `tools` | Servicio de herramientas de solo lectura | No |

## Requisitos

- **Docker**: Docker Desktop en Windows (con el motor WSL 2) o Docker Engine con el complemento Compose v2 en Linux / WSL. El ejemplo 4 necesita Docker Compose 2.24 o posterior.
- **Git**.
- **Navegador web** para Swagger.
- Puertos libres en el propio equipo: `8000` (laboratorio) y `8007` y `8008` (ejemplo 4).
- No hace falta Python: las claves se generan y las pruebas se ejecutan dentro de contenedores.

```bash
git --version
docker --version
docker compose version
```

## Preparación

### 1. Descargar la versión de la Unidad 4

El mismo comando sirve en WSL / Linux y en PowerShell:

```bash
git clone --branch unidad-04-ejemplos https://github.com/Datiacode-Tech/devsecops-ia-labs.git devsecops-ia-unidad-04
cd devsecops-ia-unidad-04
```

Git avisa de que la copia está en estado *detached HEAD*: es lo normal al descargar una etiqueta.

### 2. Crear `.env` con una clave generada

La clave se genera con `secrets.token_urlsafe` **dentro de un contenedor** y se escribe en `.env` sin mostrarla en pantalla.

WSL / Linux:

```bash
cp .env.example .env
CLAVE=$(docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))")
sed -i "s|^DEMO_API_KEY=.*|DEMO_API_KEY=${CLAVE}|" .env
unset CLAVE
chmod 600 .env        # solo tu usuario puede leer el fichero
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
$clave = docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))"
(Get-Content .env) -replace '^DEMO_API_KEY=.*', "DEMO_API_KEY=$clave" | Set-Content -Encoding ascii .env
Remove-Variable clave
```

**No exportes `DEMO_API_KEY` en la terminal.** Docker Compose da prioridad a una variable de la sesión sobre `.env`, incluso si está vacía: al rotar la clave, el contenedor seguiría recibiendo el valor antiguo. Si en la Unidad 3 la cargaste en la sesión, elimínala:

```bash
unset DEMO_API_KEY                                          # WSL / Linux
```

```powershell
Remove-Item Env:DEMO_API_KEY -ErrorAction SilentlyContinue  # PowerShell
```

### 3. Arrancar Docker Compose

Igual en WSL / Linux y en PowerShell:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

- `docker compose config --quiet` no muestra nada si la configuración es correcta. **Sin `--quiet` muestra el valor de la clave**: no compartas esa salida.
- `docker compose ps` debe mostrar `api`, `mock-llm` y `tools` en estado `running`.
- Si `api` termina (`Exited (1)`), `docker compose logs api` explica el motivo sin mostrar ningún valor.

Swagger: http://127.0.0.1:8000/docs. Pulsa **Authorize**, pega la clave (está en `.env`) y prueba los endpoints protegidos.

### 4. Leer la clave en una variable no exportada

Para usar la clave en las peticiones se lee de `.env` a una variable **de la terminal, no exportada**: Docker Compose no la ve.

```bash
CLAVE=$(sed -n 's/^DEMO_API_KEY=//p' .env | tr -d '\r')                                      # WSL / Linux
```

```powershell
$clave = (Select-String -Path .env -Pattern '^DEMO_API_KEY=(.+)$').Matches[0].Groups[1].Value   # PowerShell
```

En PowerShell, `Invoke-WebRequest` lanza una excepción con los códigos 4xx. Esta función muestra siempre el código y el cuerpo; pégala una vez en la sesión:

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
```

Si los acentos se ven mal en la consola de PowerShell, ejecuta antes `[Console]::OutputEncoding = [Text.Encoding]::UTF8`.

## Ejemplos

| N.º | Ejemplo | Archivos que intervienen |
|---|---|---|
| 1 | Protección de credenciales | `.env`, `.env.example`, `.gitignore`, `.dockerignore`, `compose.yaml`, `app/config.py` |
| 2 | Protección de logs | `app/log_redaction.py`, `app/security.py`, `app/main.py`, `scripts/demo_unidad_04_logs.py` |
| 3 | Rotación de API keys | `.env`, `compose.yaml`, `app/config.py`, `app/security.py` |
| 4 | Docker Compose Secrets | `extras/unidad-04-docker-secrets/` (`compose.secrets-demo.yaml`, `app/main.py`, `scripts/verificar.*`, `tests/test_secreto.py`) |

### Ejemplo 1. Protección de credenciales

**Objetivo:** comprobar que la clave solo llega por configuración, que no está en Git ni en la imagen, y que la API se niega a arrancar con valores inseguros.

Igual en WSL / Linux y en PowerShell:

```bash
# 1. El código solo referencia la variable por su nombre
git grep -n -e DEMO_API_KEY -- app compose.yaml

# 2. .env está excluido de Git
git check-ignore -v .env
git ls-files .env

# 3. .env está excluido de la imagen Docker
git grep -n -e '^.env' -- .dockerignore
docker compose run --rm --no-deps api ls -a /code

# 4. La API no arranca sin clave, con valores de ejemplo o con una clave corta
docker compose run --rm --no-deps -e DEMO_API_KEY= api python -c "import app.config"
docker compose run --rm --no-deps -e DEMO_API_KEY=curso-demo-key-local api python -c "import app.config"
docker compose --env-file .env.example run --rm --no-deps api python -c "import app.config"
docker compose run --rm --no-deps -e DEMO_API_KEY=corta api python -c "import app.config"

# 5. Con la clave de .env, la configuración es válida
docker compose run --rm --no-deps api python -c "import app.config; print('configuracion valida')"
```

Resultados esperados:

- `git check-ignore -v .env` muestra la regla que lo excluye (`.gitignore:1:.env`) y `git ls-files .env` no devuelve nada.
- `ls -a /code` lista el contenido de la imagen (`app`, `data`, `course_stage.json`…) y no aparece `.env`: `.dockerignore` lo excluye del contexto de construcción.
- Cada arranque del paso 4 termina con un `RuntimeError` cuya última línea indica el motivo: `ausente`, `valor de ejemplo o inseguro` (las dos siguientes) y `longitud insuficiente`. El valor recibido no aparece nunca.
- El paso 5 muestra `configuracion valida`.

Dónde está la clave, contando apariciones sin mostrarla (con la clave leída como en el apartado 4 de la preparación):

```bash
git grep -F -l -e "$CLAVE" | wc -l                                   # ficheros versionados: 0
git log --all -p | grep -c -F -e "$CLAVE"                            # historial Git: 0
docker inspect $(docker compose ps -q api) | grep -c -F -e "$CLAVE"  # metadatos del contenedor: 1
```

```powershell
(git grep -F -l -e $clave | Measure-Object).Count
(git log --all -p | Select-String -SimpleMatch $clave | Measure-Object).Count
(docker inspect (docker compose ps -q api) | Select-String -SimpleMatch $clave | Measure-Object).Count
```

El último vale 1: una variable de entorno queda en claro en los metadatos del contenedor. Es la limitación que aborda el ejemplo 4.

`-e DEMO_API_KEY=…` en la línea de comandos solo es aceptable con valores de prueba que no funcionan, como aquí: un valor real quedaría en el historial de la terminal.

### Ejemplo 2. Protección de logs

**Objetivo:** ver la diferencia entre un registro inseguro y uno seguro, y comprobar que la API no registra credenciales.

Demostración con una clave ficticia: registro mal diseñado, el mismo registro con el filtro de redacción y el diseño correcto (igual en WSL / Linux y en PowerShell):

```bash
docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro api python -m scripts.demo_unidad_04_logs
```

En la API real, una petición con una clave incorrecta deja el motivo en el registro, sin el valor.

WSL / Linux:

```bash
INCORRECTA=clave-incorrecta-de-prueba-$RANDOM
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $INCORRECTA" -d '{"question":"vacaciones"}'   # 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" -d '{"question":"vacaciones"}'        # 200
docker compose logs api | grep 'rechazada'
docker compose logs api | grep -c -F -e "$INCORRECTA"     # 0
docker compose logs api | grep -c -F -e "$CLAVE"          # 0
unset INCORRECTA
```

Windows PowerShell (con `Invoke-Lab`):

```powershell
$incorrecta = "clave-incorrecta-de-prueba-$(Get-Random)"
Invoke-Lab POST /ask @{ question = 'vacaciones' } $incorrecta     # 401
Invoke-Lab POST /ask @{ question = 'vacaciones' } $clave          # 200
docker compose logs api | Select-String 'rechazada'
(docker compose logs api | Select-String -SimpleMatch $incorrecta | Measure-Object).Count   # 0
(docker compose logs api | Select-String -SimpleMatch $clave | Measure-Object).Count        # 0
Remove-Variable incorrecta
```

Resultado esperado: `Autenticación rechazada: credencial incorrecta` en el registro y 0 apariciones de ambas claves. Las pruebas `test_logs_redact_api_key` y `test_auth_failures_are_logged_without_credentials` lo comprueban de forma automática.

### Ejemplo 3. Rotación de API keys

**Objetivo:** sustituir una clave que ha podido quedar expuesta y comprobar que la antigua deja de funcionar. Solo se recrea el servicio `api`, que es el único que usa la clave.

WSL / Linux:

```bash
unset DEMO_API_KEY                                   # imprescindible: si no, Compose usaría el valor de la sesión
ANTIGUA=$(sed -n 's/^DEMO_API_KEY=//p' .env | tr -d '\r')
NUEVA=$(docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))")
sed -i "s|^DEMO_API_KEY=.*|DEMO_API_KEY=${NUEVA}|" .env
docker compose up -d --no-deps api                   # debe mostrar «Recreated»
until curl -sf http://127.0.0.1:8000/health >/dev/null; do sleep 1; done
for K in "$ANTIGUA" "$NUEVA"; do
  curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/ask \
    -H 'Content-Type: application/json' -H "x-api-key: $K" -d '{"question":"vacaciones"}'
done                                                 # 401 con la antigua, 200 con la nueva
CLAVE=$NUEVA
unset ANTIGUA NUEVA K
```

Windows PowerShell (con `Invoke-Lab`):

```powershell
Remove-Item Env:DEMO_API_KEY -ErrorAction SilentlyContinue
$antigua = (Select-String -Path .env -Pattern '^DEMO_API_KEY=(.+)$').Matches[0].Groups[1].Value
$nueva = docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))"
(Get-Content .env) -replace '^DEMO_API_KEY=.*', "DEMO_API_KEY=$nueva" | Set-Content -Encoding ascii .env
docker compose up -d --no-deps api
do { Start-Sleep 1; try { $ok = (Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing).StatusCode -eq 200 } catch { $ok = $false } } until ($ok)
Invoke-Lab POST /ask @{ question = 'vacaciones' } $antigua        # 401
Invoke-Lab POST /ask @{ question = 'vacaciones' } $nueva          # 200
$clave = $nueva
Remove-Variable antigua, nueva
```

- Si `docker compose up` muestra `Running` en lugar de `Recreated`, la clave nueva no ha llegado al contenedor (normalmente porque `DEMO_API_KEY` sigue definida en la sesión).
- `docker compose restart api` **no sirve**: reinicia el contenedor con la configuración antigua.
- Durante la recreación la API deja de responder unos segundos. En producción se evita con un periodo en el que se aceptan ambas claves, despliegues escalonados y la revocación posterior de la antigua.
- Recuerda actualizar la clave en Swagger (**Authorize**).

### Ejemplo 4. Docker Compose Secrets

**Objetivo:** entregar la credencial como un **fichero** montado en `/run/secrets/` en lugar de como variable de entorno, y comparar ambas opciones.

Es una demostración **independiente de la API principal**: tiene su propio `compose.secrets-demo.yaml`, su propia API mínima y su propio proyecto de Docker Compose (`devsecops-ia-u04-secretos`). No usa `.env` ni modifica el laboratorio, que puede seguir en marcha.

| Servicio | Puerto | Origen de la clave |
|---|---|---|
| `api-secreto` | `127.0.0.1:8007` | Fichero montado en `/run/secrets/demo_api_key` |
| `api-entorno` (perfil `comparar`) | `127.0.0.1:8008` | Variable de entorno `DEMO_API_KEY`, solo para comparar |

**1. Generar el secreto sin mostrarlo.** Desde la carpeta del ejemplo:

```bash
cd extras/unidad-04-docker-secrets
```

WSL / Linux:

```bash
mkdir -p secrets
( umask 077
  CLAVE=$(docker run --rm python:3.12.16-slim python -c "import secrets; print(secrets.token_urlsafe(24), end='')")
  printf '%s' "$CLAVE" > secrets/demo_api_key.txt
  printf 'DEMO_API_KEY=%s\n' "$CLAVE" > secrets/demo.env )
chmod 600 secrets/demo_api_key.txt secrets/demo.env
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force secrets | Out-Null
$c = docker run --rm python:3.12.16-slim python -c "import secrets; print(secrets.token_urlsafe(24), end='')"
$dir = Join-Path (Get-Location).ProviderPath 'secrets'
[IO.File]::WriteAllText((Join-Path $dir 'demo_api_key.txt'), $c)
[IO.File]::WriteAllText((Join-Path $dir 'demo.env'), "DEMO_API_KEY=$c`n")
Remove-Variable c
foreach ($f in 'demo_api_key.txt', 'demo.env') { icacls (Join-Path $dir $f) /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null }
```

Si la carpeta del laboratorio está dentro de WSL (`\\wsl.localhost\...`), `icacls` responde «Función incorrecta» y no cambia los permisos: en ese caso restríngelos desde WSL con `chmod 600 secrets/demo_api_key.txt secrets/demo.env`.

`secrets/` está excluida de Git y de la imagen. `secrets/demo.env` contiene la misma clave como variable de entorno y solo se usa para la comparación.

**2. Arrancar los dos servicios** (igual en WSL / Linux y en PowerShell):

```bash
docker compose -f compose.secrets-demo.yaml config --quiet
docker compose -f compose.secrets-demo.yaml up -d --build api-secreto
docker compose -f compose.secrets-demo.yaml --profile comparar up -d api-entorno
```

**3. Lectura desde `/run/secrets/`** (se muestran los permisos y la longitud, nunca el contenido):

```bash
docker compose -f compose.secrets-demo.yaml exec api-secreto stat -c '%A %n' /run/secrets/demo_api_key
docker compose -f compose.secrets-demo.yaml exec api-secreto python -c "from pathlib import Path; print(len(Path('/run/secrets/demo_api_key').read_text().strip()), 'caracteres')"
docker compose -f compose.secrets-demo.yaml logs api-secreto
```

El registro muestra `Clave cargada desde: secreto`. `http://127.0.0.1:8007/health` devuelve `"origen_clave":"secreto"` y `http://127.0.0.1:8008/health`, `"origen_clave":"entorno"`.

**4. Diferencia respecto a una variable de entorno** (igual en WSL / Linux y en PowerShell):

```bash
docker compose -f compose.secrets-demo.yaml exec api-secreto python -c "import os; print('DEMO_API_KEY' in os.environ)"
docker compose -f compose.secrets-demo.yaml --profile comparar exec api-entorno python -c "import os; print('DEMO_API_KEY' in os.environ)"
```

Apariciones del valor en `docker inspect`, sin mostrarlo.

WSL / Linux:

```bash
SEC=$(docker compose -f compose.secrets-demo.yaml ps -q api-secreto)
ENT=$(docker compose -f compose.secrets-demo.yaml --profile comparar ps -q api-entorno)
docker inspect $SEC | grep -cF -- "$(cat secrets/demo_api_key.txt)"     # 0
docker inspect $ENT | grep -cF -- "$(cat secrets/demo_api_key.txt)"     # 1
```

Windows PowerShell:

```powershell
$sec = docker compose -f compose.secrets-demo.yaml ps -q api-secreto
$ent = docker compose -f compose.secrets-demo.yaml --profile comparar ps -q api-entorno
$valor = [IO.File]::ReadAllText((Join-Path (Get-Location).ProviderPath 'secrets\demo_api_key.txt')).Trim()
@(docker inspect $sec | Select-String -SimpleMatch $valor).Count     # 0
@(docker inspect $ent | Select-String -SimpleMatch $valor).Count     # 1
Remove-Variable valor
```

| Comprobación | `api-secreto` (fichero) | `api-entorno` (variable) |
|---|---|---|
| `'DEMO_API_KEY' in os.environ` | `False` | `True` |
| Apariciones del valor en `docker inspect` | 0 | 1 |
| `docker compose config` sin `--quiet` | Solo la ruta del fichero | Muestra el valor |
| Montaje | `/run/secrets/demo_api_key`, solo lectura | — |

**5. Verificación completa y pruebas.** El script arranca la demostración, comprueba permisos, montajes, entorno, `docker inspect`, la autenticación (401 sin clave, 401 con clave incorrecta, 200 con la correcta), las pruebas y los registros, y la detiene. Termina con código 0 si todo es correcto:

```bash
bash scripts/verificar.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verificar.ps1
```

Solo las pruebas, dentro del contenedor (resultado esperado: `5 passed`):

```bash
docker compose -f compose.secrets-demo.yaml run --rm --no-deps -v ./tests:/demo/tests:ro api-secreto python -m pytest -q -p no:cacheprovider /demo/tests
```

**6. Detener y limpiar:**

```bash
docker compose -f compose.secrets-demo.yaml --profile comparar down --rmi all
rm -f secrets/demo_api_key.txt secrets/demo.env          # WSL / Linux
cd ../..
```

```powershell
docker compose -f compose.secrets-demo.yaml --profile comparar down --rmi all
Remove-Item secrets\demo_api_key.txt, secrets\demo.env   # PowerShell
Set-Location ..\..
```

**Limitaciones:** Docker Compose **no cifra** el secreto: monta el fichero del equipo en solo lectura. El fichero de origen sigue en claro en el disco, y quien tenga acceso a Docker puede leerlo dentro del contenedor. El cifrado y la distribución controlada de secretos corresponden a Docker Swarm, Kubernetes o un gestor de secretos (HashiCorp Vault o los servicios de los proveedores cloud). Más detalle en `extras/unidad-04-docker-secrets/README.md`.

## Pruebas

Dentro del contenedor de la API, montando las pruebas y el registro de riesgos. El mismo comando sirve en WSL / Linux y en PowerShell:

```bash
docker compose run --rm -v ./tests:/code/tests:ro -v ./security:/code/security:ro -e PYTHONDONTWRITEBYTECODE=1 api python -m pytest -q -p no:cacheprovider /code/tests
```

Resultado esperado: `48 passed` (puede aparecer `1 warning`). Requiere `.env` configurado.

| Fichero | Qué comprueba |
|---|---|
| `tests/test_api.py` | Autenticación, validación de preguntas, operaciones bloqueadas |
| `tests/test_tools_validation.py` | Validación de `operation` y `document_id` en `/tools/execute` |
| `tests/test_secrets.py` | Configuración de la clave, respuestas, registros y rotación (Unidad 4) |
| `tests/test_local_logic.py`, `tests/test_risk_register.py`, `tests/test_soporte.py` | Datos, etapa, registro de riesgos e informe de soporte |

## Registro de riesgos

`security/risk_register.csv` relaciona cada riesgo con su control y su evidencia. Una evidencia `test_*` es una prueba que existe en `tests/`; una evidencia pendiente (`pendiente_*`) es una prueba prevista que todavía no existe, y ese riesgo no puede figurar como `Mitigado`.

| Riesgo | Estado en la Unidad 4 |
|---|---|
| R-01 Acceso sin credencial | Mitigado: `test_ask_requires_api_key` |
| R-02 Acceso a tenant ajeno | En seguimiento (Unidad 10) |
| R-03 Acción no autorizada | Mitigado: `test_mutation_is_denied` |
| R-04 Credencial en el código o en el historial | Mitigado: `test_api_key_not_hardcoded_in_source` |
| R-07 Entrada no validada en herramientas | Mitigado: `test_tool_document_id_invalid_format` |
| R-08 Credencial en los registros | Mitigado: `test_logs_redact_api_key` |
| R-09 Clave comprometida que sigue siendo válida | Mitigado con rotación manual: `test_rotation_rejects_old_key_and_accepts_new` |
| R-10 Secreto legible en el equipo y en los metadatos del contenedor | En seguimiento: requiere un gestor de secretos |

Limitaciones que siguen abiertas: una única clave compartida, sin identidad por usuario ni por tenant, sin caducidad, rotación manual con interrupción y sin análisis automático de secretos en cada cambio (Unidad 7).

## Otros archivos

Se conservan como material complementario y no forman parte de los cuatro ejemplos:

- `scripts/demo_unidad_04_gitleaks.sh`: detección de credenciales con Gitleaks en un repositorio de prácticas (`docker run --rm -v ./scripts:/scripts:ro --entrypoint sh ghcr.io/gitleaks/gitleaks:v8.28.0 /scripts/demo_unidad_04_gitleaks.sh`).
- `app/soporte.py` y `scripts/incidencia_unidad_04.py`: punto de partida del ejercicio de la unidad.
- `scripts/demo_unidad_01.py`, `scripts/demo_unidad_02.py`, `scripts/demo_unidad_03.py` y `scripts/check_lab.py`: demostraciones de unidades anteriores.

## Detener los servicios

```bash
docker compose logs --tail=30 api
docker compose down
```

Al terminar, borra la variable de la terminal: `unset CLAVE` (WSL / Linux) o `Remove-Variable clave` (PowerShell). `.env` se conserva para la siguiente unidad.

## Reglas del laboratorio

- La API solo se publica en `127.0.0.1`; `mock-llm` y `tools` permanecen en la red privada de Docker.
- El servicio de herramientas nunca ejecuta operaciones destructivas.
- No despliegues este laboratorio en un servidor accesible desde Internet.
- Nunca introduzcas credenciales ni datos reales. Las credenciales de los ejemplos son ficticias o se generan al ejecutarlos.
