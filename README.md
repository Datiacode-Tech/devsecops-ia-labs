# DevSecOps aplicado a IA · Laboratorio transversal

**Entorno docente aislado**, no apto para producción. Utiliza datos de empresas ficticias, un modelo **simulado** y un servicio HTTP didáctico de herramientas que **no implementa MCP completo**.

El proyecto evoluciona a lo largo del curso: cada unidad incorpora nuevas funcionalidades y controles de seguridad. Esta versión corresponde a los **ejemplos de la Unidad 5: Seguridad y endurecimiento de contenedores Docker** (`course_stage.json`, etapa 5).

## Objetivos de la Unidad 5

Una API autenticada y con los secretos bien gestionados puede seguir siendo vulnerable si sus contenedores se ejecutan con más privilegios de los necesarios. Esta unidad reduce lo que un atacante podría hacer si llegara a ejecutar código dentro de un contenedor.

- Auditar con herramientas nativas de Docker cómo se ejecuta cada contenedor.
- Ejecutar los servicios con un usuario sin privilegios.
- Montar el sistema de archivos del contenedor en solo lectura.
- Analizar las imágenes con Trivy e interpretar los hallazgos: un CVE no es lo mismo que un riesgo.

## Qué cambia respecto a la Unidad 4

| Control | Dónde | `api` | `mock-llm` | `tools` |
|---|---|---|---|---|
| Usuario sin privilegios (UID 10001) | `Dockerfile`, `docker/Dockerfile.mock` | Sí | Sí | Pendiente (ejercicio) |
| Sistema de archivos de solo lectura y `/tmp` en memoria (`tmpfs`) | `compose.yaml`: `read_only`, `tmpfs` | Sí | Sí | Pendiente (ejercicio) |
| Sin capacidades del kernel y sin nuevos privilegios | `compose.yaml`: `cap_drop`, `security_opt` | Sí | Sí | Pendiente (ejercicio) |
| Límites de memoria, CPU y procesos | `compose.yaml`: `mem_limit`, `memswap_limit`, `cpus`, `pids_limit` | Sí | Sí | Sí |
| Comprobación de salud | `compose.yaml`: `healthcheck` | Sí | Sí | Sí |
| Red interna sin salida a Internet | `compose.yaml`: red `backend` con `internal: true` | — | Sí | Sí |
| Análisis de imágenes | Trivy, ejecutado con Docker | — | — | — |

Los ejemplos de esta unidad tratan el usuario sin privilegios, el sistema de archivos de solo lectura y Trivy. El resto de controles de la tabla ya están aplicados en el laboratorio y comprobados por las pruebas automatizadas.

Se mantienen los controles de las unidades anteriores:

- `x-api-key` obligatoria en `POST /ask` y `POST /tools/execute`;
- validación de preguntas y de `ToolCall`;
- operaciones destructivas bloqueadas (`403`);
- `DEMO_API_KEY` solo en `.env`, registros sin credenciales y rotación de la clave;
- API publicada solo en `127.0.0.1`.

## Arquitectura

```
Equipo (127.0.0.1:8000)
        │  x-api-key
        ▼
   ┌─────────┐   red backend (interna)   ┌──────────┐
   │   api   │ ────────────────────────▶ │ mock-llm │  modelo simulado [SIMULADO]
   │ FastAPI │ ────────────────────────▶ │  tools   │  herramientas de solo lectura
   └─────────┘                           └──────────┘
   red frontend (puerto publicado)
```

| Servicio | Función | Red |
|---|---|---|
| `api` | API FastAPI: autentica, valida, recupera documentos y coordina los servicios | `frontend` (publicada en `127.0.0.1:8000`) y `backend` |
| `mock-llm` | Proveedor de lenguaje simulado: respuesta determinista marcada como `[SIMULADO]` | `backend` (interna) |
| `tools` | Servicio de herramientas de solo lectura | `backend` (interna) |

## Requisitos

- **Docker**: Docker Desktop en Windows (con el motor WSL 2) o Docker Engine 25 o posterior con el complemento Compose v2 en Linux / WSL. Los `healthcheck` usan `start_interval`.
- **Git**.
- **Navegador web** para Swagger.
- Puerto `8000` libre en el propio equipo.
- Conexión a Internet para el ejemplo 4 (Trivy descarga su base de datos de vulnerabilidades).
- No hace falta Python: las claves se generan y las pruebas se ejecutan dentro de contenedores.

```bash
git --version
docker --version
docker compose version
```

## Preparación

### 1. Descargar la versión de la Unidad 5

El mismo comando sirve en WSL / Linux y en PowerShell:

```bash
git clone --branch unidad-05-ejemplos https://github.com/Datiacode-Tech/devsecops-ia-labs.git devsecops-ia-unidad-05
cd devsecops-ia-unidad-05
```

Git avisa de que la copia está en estado *detached HEAD*: es lo normal al descargar una etiqueta.

Si continúas en la carpeta de la Unidad 4, detén antes sus servicios (`docker compose down`) y cambia de versión. Tu `.env` se conserva:

```bash
git fetch --tags
git checkout unidad-05-ejemplos
```

### 2. Crear `.env` con una clave generada

Si ya tienes `.env` de la Unidad 4, sáltate este paso.

WSL / Linux:

```bash
cp .env.example .env
CLAVE=$(docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))")
sed -i "s|^DEMO_API_KEY=.*|DEMO_API_KEY=${CLAVE}|" .env
unset CLAVE
chmod 600 .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
$clave = docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(24))"
(Get-Content .env) -replace '^DEMO_API_KEY=.*', "DEMO_API_KEY=$clave" | Set-Content -Encoding ascii .env
Remove-Variable clave
```

**No exportes `DEMO_API_KEY` en la terminal**: Docker Compose daría prioridad a ese valor sobre `.env`. Si la tienes definida, elimínala con `unset DEMO_API_KEY` (WSL / Linux) o `Remove-Item Env:DEMO_API_KEY -ErrorAction SilentlyContinue` (PowerShell).

### 3. Arrancar Docker Compose

Igual en WSL / Linux y en PowerShell:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

- `docker compose up` espera a que `mock-llm` y `tools` estén sanos antes de arrancar `api`. En unos segundos, los tres servicios deben aparecer como `(healthy)`.
- **No ejecutes `docker compose config` sin `--quiet`** si vas a compartir la salida: muestra el valor de la clave.

Swagger: http://127.0.0.1:8000/docs. Pulsa **Authorize** y pega la clave (está en `.env`).

### 4. Comprobar que la API responde

Lee la clave de `.env` en una variable **de la terminal, no exportada**:

```bash
CLAVE=$(sed -n 's/^DEMO_API_KEY=//p' .env | tr -d '\r')                                      # WSL / Linux
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" -d '{"question":"vacaciones"}'  # 200
```

```powershell
$clave = (Select-String -Path .env -Pattern '^DEMO_API_KEY=(.+)$').Matches[0].Groups[1].Value   # PowerShell
(Invoke-WebRequest -UseBasicParsing -Method Post -Uri http://127.0.0.1:8000/ask -Headers @{ 'x-api-key' = $clave } `
    -ContentType 'application/json' -Body '{"question":"vacaciones"}').StatusCode                # 200
```

El endurecimiento de los contenedores no cambia el funcionamiento de la API.

## Ejemplos

| N.º | Ejemplo | Archivos que intervienen |
|---|---|---|
| 1 | Auditoría de los contenedores | `compose.yaml`, `Dockerfile`, `docker/Dockerfile.mock`, `docker/Dockerfile.tools` |
| 2 | Ejecutar contenedores sin root | `Dockerfile`, `docker/Dockerfile.mock`, `scripts/demo_unidad_05_contenedor.py` |
| 3 | Sistema de archivos de solo lectura | `compose.yaml` (`read_only`, `tmpfs`) |
| 4 | Análisis de imágenes con Trivy | Imágenes del laboratorio, `Dockerfile`, `docker/`, `artifacts/` |

Las plantillas de `docker inspect` usan acentos graves (`` `Tmpfs` ``) en lugar de comillas dobles: Windows PowerShell 5.1 elimina las comillas dobles de los argumentos que pasa a otros programas. Así, los mismos comandos funcionan en WSL / Linux y en PowerShell.

### Ejemplo 1. Auditoría de los contenedores

**Objetivo:** analizar cómo se ejecutan `api`, `mock-llm` y `tools` y distinguir riesgos reales de características del entorno.

Igual en WSL / Linux y en PowerShell:

```bash
# 1. Servicios, estado y puertos
docker compose ps

# 2. Usuario, privilegios y sistema de archivos
docker inspect --format '{{.Name}} usuario={{.Config.User}} privilegiado={{.HostConfig.Privileged}} solo_lectura={{.HostConfig.ReadonlyRootfs}} tmpfs={{with index .HostConfig `Tmpfs`}}{{json .}}{{else}}ninguno{{end}}' $(docker compose ps -q)

# 3. Capacidades y opciones de seguridad
docker inspect --format '{{.Name}} cap_drop={{.HostConfig.CapDrop}} cap_add={{.HostConfig.CapAdd}} security_opt={{.HostConfig.SecurityOpt}}' $(docker compose ps -q)

# 4. Puertos, montajes y redes
docker inspect --format '{{.Name}} puertos={{json .HostConfig.PortBindings}} montajes={{len .Mounts}} redes={{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' $(docker compose ps -q)

# 5. Desde dentro: usuario del proceso
docker compose exec api id
docker compose exec tools id

# 6. Nombres (no valores) de las variables de entorno de la API
docker compose exec api python -c "import os; print(sorted(os.environ))"
```

Resultado esperado (resumido):

```
…-api-1      usuario=10001:10001 privilegiado=false solo_lectura=true  tmpfs={"/tmp":"rw,noexec,nosuid,nodev,size=16m"}
…-mock-llm-1 usuario=10001:10001 privilegiado=false solo_lectura=true  tmpfs={"/tmp":"rw,noexec,nosuid,nodev,size=16m"}
…-tools-1    usuario=            privilegiado=false solo_lectura=false tmpfs=ninguno
```

| Observación | ¿Riesgo? | Motivo |
|---|---|---|
| `usuario=` vacío (root) en `tools` | Sí | Un fallo de la aplicación daría control como root dentro del contenedor |
| `solo_lectura=false` en `tools` | Sí | Se podría modificar el código o dejar herramientas |
| `cap_drop=[]` en `tools` | Sí | Conserva las 14 capacidades que Docker concede por defecto |
| `privilegiado=false` en los tres | No | Correcto: `privileged: true` daría acceso casi total al equipo |
| `montajes=0` | No | Sin volúmenes ni socket de Docker montados |
| Puerto solo en `127.0.0.1` | No | Solo accesible desde el propio equipo |
| `DEMO_API_KEY` entre las variables | Conocido | Necesaria para la API; registrado como R-10 |

`usuario=` vacío significa el usuario por defecto de la imagen, que en `python:3.12-slim` es root. **Nunca uses `docker inspect` sin `--format`**: incluye las variables de entorno con el valor de `DEMO_API_KEY`.

### Ejemplo 2. Ejecutar contenedores sin root

**Objetivo:** entender por qué una aplicación no debe ejecutarse como root dentro de un contenedor y cómo se aplica un usuario sin privilegios.

Los contenedores comparten el kernel del equipo. Si una vulnerabilidad o una mala configuración permite escapar del contenedor, el atacante sale con el usuario del proceso. Además, root dentro del contenedor puede modificar el código y leer cualquier fichero de la imagen.

`Dockerfile` (y `docker/Dockerfile.mock` con el mismo patrón):

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
# Usuario de sistema sin privilegios, sin contraseña, sin directorio personal y sin shell de acceso.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app
COPY app app
COPY data data
COPY course_stage.json .
USER 10001:10001
```

- `pip install` va **antes** de `USER`: instalar en `/usr/local` requiere root.
- El código se copia **sin** `--chown`: pertenece a root, así que el usuario `app` puede leerlo pero no modificarlo.
- UID numérico alto (10001): no coincide con usuarios habituales del equipo y se comprueba sin consultar `/etc/passwd`.

Igual en WSL / Linux y en PowerShell:

```bash
docker compose exec api id
docker compose exec mock-llm id
docker compose exec tools id
docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro api python -m scripts.demo_unidad_05_contenedor
docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro tools python -m scripts.demo_unidad_05_contenedor
```

Resultados esperados:

- `id`: `uid=10001(app)` en `api` y `mock-llm`; `uid=0(root)` en `tools`.
- La demostración se ejecuta en un contenedor efímero con la configuración de cada servicio y muestra la identidad, las capacidades, los montajes y varios intentos, sin mostrar variables de entorno:

| Intento | `api` | `tools` |
|---|---|---|
| Modificar el código de la aplicación | denegado (`EACCES`) | PERMITIDO |
| Crear un fichero en `/code` o en `/etc` | denegado (`EROFS`) | PERMITIDO |
| Crear un fichero en `/tmp` | PERMITIDO | PERMITIDO |
| Cambiar el propietario de un fichero | denegado (`EPERM`) | PERMITIDO |
| Abrir un socket de red crudo | denegado (`EPERM`) | PERMITIDO |

En `api`, modificar el código falla por falta de permiso (`EACCES`) **antes** de llegar a la protección de solo lectura (`EROFS`): son dos capas independientes. Si cambias un Dockerfile, reconstruye con `docker compose up -d --build`.

### Ejemplo 3. Sistema de archivos de solo lectura

**Objetivo:** impedir que un proceso comprometido modifique el contenedor y dar a la aplicación un espacio temporal controlado.

`compose.yaml` (servicio `api`; `mock-llm` es igual):

```yaml
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,nodev,size=16m
```

- `read_only: true` monta la raíz del contenedor en solo lectura: cualquier escritura recibe `EROFS` (*Read-only file system*), incluso como root.
- `tmpfs` monta `/tmp` en memoria: se puede escribir, desaparece al detener el contenedor y `size=16m` lo acota.
- `noexec` impide ejecutar programas desde `/tmp`, el lugar habitual donde un atacante deja una herramienta descargada. `nosuid` ignora los bits `setuid` y `nodev` impide usar ficheros de dispositivo.

Igual en WSL / Linux y en PowerShell:

```bash
docker compose exec api python -c "open('/code/prueba.txt', 'w')"
docker compose exec tools python -c "open('/code/prueba.txt', 'w'); print('escrito')"
docker compose exec tools rm /code/prueba.txt
```

Resultado esperado: en `api`, `OSError: [Errno 30] Read-only file system: '/code/prueba.txt'`; en `tools`, `escrito`. Los tres servicios siguen funcionando con normalidad.

`read_only` sin `tmpfs` es un error habitual: el servicio puede arrancar y aparecer `healthy`, pero falla cualquier código que necesite un directorio temporal.

### Ejemplo 4. Análisis de imágenes con Trivy

**Objetivo:** analizar las imágenes del laboratorio, filtrar e interpretar los hallazgos y distinguir hallazgo de riesgo.

Se necesita el laboratorio construido (`docker compose up -d --build`): las imágenes tienen nombres fijos (`devsecops-ia-lab/api:local`) gracias a `image:` en `compose.yaml`.

Trivy se ejecuta con Docker, en una versión fijada por número y por digest. Las etiquetas de Docker no son inmutables, y una herramienta de seguridad también puede ser un vector de ataque: por eso no se usa `latest`.

Las imágenes se exportan a un fichero con `docker save` en lugar de montar el socket de Docker (`/var/run/docker.sock`) en el contenedor de Trivy: quien accede a ese socket controla Docker y, en la práctica, el equipo. La carpeta `artifacts/` está excluida de Git y de las imágenes.

WSL / Linux:

```bash
TRIVY=aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
mkdir -p artifacts
```

Windows PowerShell:

```powershell
$TRIVY = 'aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c'
New-Item -ItemType Directory -Force artifacts | Out-Null
```

A partir de aquí, los comandos son iguales en ambos sistemas:

```bash
# 1. Exportar la imagen
docker save -o artifacts/api.tar devsecops-ia-lab/api:local

# 2. Vulnerabilidades HIGH y CRITICAL
docker run --rm -v ./artifacts:/artifacts:ro -v trivy-cache:/root/.cache $TRIVY image --input /artifacts/api.tar --scanners vuln --severity HIGH,CRITICAL --table-mode detailed

# 3. Solo las que tienen corrección disponible
docker run --rm -v ./artifacts:/artifacts:ro -v trivy-cache:/root/.cache $TRIVY image --input /artifacts/api.tar --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --table-mode detailed

# 4. Configuración de los Dockerfiles
docker run --rm -v ./Dockerfile:/work/Dockerfile:ro -v ./docker:/work/docker:ro -v trivy-cache:/root/.cache $TRIVY config /work --table-mode detailed
```

- La primera ejecución descarga la base de datos de vulnerabilidades; el volumen `trivy-cache` la conserva.
- `--ignore-unfixed` oculta lo que todavía no tiene versión corregida: es lo que se puede corregir hoy.
- `config` revisa los Dockerfiles (no analiza `compose.yaml`).

**Resultados orientativos.** Las cifras cambian a diario porque la base de datos se actualiza. En una ejecución de referencia:

- los paquetes del sistema de la imagen base tenían decenas de hallazgos HIGH sin corrección publicada (estado `affected`) y solo unos pocos con corrección;
- las dependencias de la aplicación (FastAPI, uvicorn, httpx, pydantic…) no tenían hallazgos;
- `config` solo señalaba la falta de `HEALTHCHECK` en los Dockerfiles y, en `docker/Dockerfile.tools`, la falta de un usuario no root.

**Interpretación:**

- **CVE, severidad y riesgo.** El CVE identifica una vulnerabilidad conocida y la severidad estima su gravedad en general. El riesgo real depende del contexto: si el componente se usa, si es alcanzable y con qué privilegios se ejecuta.
- **Riesgo bajo pese a HIGH.** Varios hallazgos afectan a utilidades de administración como `mount`. La aplicación no las ejecuta, el proceso no es root (ejemplo 2), el contenedor no tiene capacidades del kernel y `no-new-privileges` impide que un binario `setuid` como `mount` otorgue privilegios. El endurecimiento reduce el riesgo de muchos hallazgos de la imagen.
- **Sin corrección disponible (`affected`).** No hay versión que instalar: se acepta y documenta el riesgo, se elimina el paquete si no se necesita o se cambia a una imagen base más pequeña.
- **Falsos positivos.** La falta de `HEALTHCHECK` en el Dockerfile no es un problema aquí: la comprobación de salud está en `compose.yaml`. `Dockerfile.tools` sin usuario no root sí es real: es el punto de partida del ejercicio.
- **Cero hallazgos no significa imagen segura**: solo que no hay vulnerabilidades **conocidas** en los paquetes que Trivy identifica. No cubre el código propio ni la configuración de ejecución.

Riesgo relacionado: R-16 (en seguimiento).

Limpieza del ejemplo: borra `artifacts/` y, si quieres liberar espacio, `docker volume rm trivy-cache`.

## Pruebas

Batería completa, dentro de un contenedor de la API (arranca antes `mock-llm` y `tools`). El mismo comando en WSL / Linux y en PowerShell:

```bash
docker compose run --rm -v ./tests:/code/tests:ro -v ./security:/code/security:ro -e PYTHONDONTWRITEBYTECODE=1 api python -m pytest -q -p no:cacheprovider /code/tests
```

Resultado esperado: `59 passed` (puede aparecer `1 warning`). Requiere `.env` configurado.

| Fichero | Qué comprueba |
|---|---|
| `tests/test_container_hardening.py` | Usuario, solo lectura, `/tmp`, capacidades, `no-new-privileges` y límites, comprobados **desde dentro** del contenedor (Unidad 5) |
| `tests/test_internal_services.py` | La API llega a `mock-llm` y `tools` por la red interna y responde de extremo a extremo (Unidad 5) |
| `tests/test_secrets.py` | Configuración de la clave, respuestas, registros y rotación (Unidad 4) |
| `tests/test_api.py`, `tests/test_tools_validation.py` | Autenticación, validación de preguntas y de `ToolCall`, operaciones bloqueadas (Unidad 3) |
| `tests/test_local_logic.py`, `tests/test_risk_register.py`, `tests/test_soporte.py` | Datos, etapa, registro de riesgos e informe de soporte |

Las pruebas de endurecimiento se pueden ejecutar en cada servicio. WSL / Linux:

```bash
for s in api mock-llm tools; do echo "== $s"; docker compose run --rm --no-deps -v ./tests:/code/tests:ro $s python -m pytest -q -p no:cacheprovider /code/tests/test_container_hardening.py; done
```

PowerShell:

```powershell
foreach ($s in 'api', 'mock-llm', 'tools') { "== $s"; docker compose run --rm --no-deps -v ./tests:/code/tests:ro $s python -m pytest -q -p no:cacheprovider /code/tests/test_container_hardening.py }
```

`api` y `mock-llm` superan las 8. En `tools` fallan 5 (usuario, solo lectura, `/tmp`, capacidades y `no-new-privileges`) y pasan las 3 de límites: es el punto de partida del ejercicio de la unidad.

## Registro de riesgos

`security/risk_register.csv` relaciona cada riesgo con su control y su evidencia. Una evidencia `test_*` es una prueba que existe en `tests/`; una evidencia pendiente (`pendiente_*`) no permite marcar el riesgo como `Mitigado`.

| Riesgo | Estado en la Unidad 5 |
|---|---|
| R-01, R-03, R-04, R-07, R-08, R-09 | Mitigados (unidades 3 y 4) |
| R-02 Acceso a tenant ajeno | En seguimiento (Unidad 10) |
| R-10 Secreto legible en el equipo y en los metadatos del contenedor | En seguimiento |
| R-12 Proceso como root en `api` y `mock-llm` | Mitigado: `test_process_runs_as_non_root` |
| R-13 Escritura en el sistema de archivos de `api` y `mock-llm` | Mitigado: `test_root_filesystem_is_read_only` |
| R-14 Capacidades y escalada de privilegios en `api` y `mock-llm` | Mitigado: `test_capabilities_are_dropped` |
| R-15 Agotamiento de recursos del equipo | Mitigado: `test_memory_limit_is_set` |
| R-16 Vulnerabilidades conocidas en la imagen base | En seguimiento: análisis manual con Trivy |

## Otros archivos

Se conservan como material de unidades anteriores o complementario:

- `scripts/demo_unidad_05_limites.py`: demostración de los límites de memoria y procesos (`docker compose run --rm --no-deps -T -v ./scripts:/code/scripts:ro mock-llm python -m scripts.demo_unidad_05_limites`).
- `extras/unidad-04-docker-secrets/`: ejemplo de Docker Compose Secrets de la Unidad 4, independiente del laboratorio.
- `scripts/demo_unidad_04_logs.py`, `scripts/demo_unidad_04_gitleaks.sh`, `app/soporte.py` y `scripts/incidencia_unidad_04.py`: material de la Unidad 4.
- `scripts/demo_unidad_01.py` a `scripts/demo_unidad_03.py` y `scripts/check_lab.py`: demostraciones de unidades anteriores.

## Detener los servicios

```bash
docker compose logs --tail=30 api
docker compose down                  # detiene y elimina los contenedores y las redes
docker compose down --rmi all        # además, elimina las imágenes devsecops-ia-lab/*
```

Al terminar, borra la variable de la terminal: `unset CLAVE` (WSL / Linux) o `Remove-Variable clave` (PowerShell). `.env` se conserva para la siguiente unidad.

## Reglas del laboratorio

- La API solo se publica en `127.0.0.1`; `mock-llm` y `tools` permanecen en la red interna de Docker.
- El servicio de herramientas nunca ejecuta operaciones destructivas.
- Ningún contenedor monta el socket de Docker ni se ejecuta con `privileged`.
- No despliegues este laboratorio en un servidor accesible desde Internet.
- Nunca introduzcas credenciales ni datos reales.
