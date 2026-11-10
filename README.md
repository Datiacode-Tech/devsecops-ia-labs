# DevSecOps aplicado a IA · Laboratorio transversal

**Entorno docente aislado**, no apto para producción. Utiliza datos de empresas ficticias, un modelo **simulado** y un servicio HTTP didáctico de herramientas que **no implementa MCP completo**.

El proyecto evoluciona a lo largo del curso: cada unidad incorpora nuevas funcionalidades y controles de seguridad. Esta versión corresponde a la **Unidad 2: Amenazas y riesgos en sistemas de IA** (`course_stage.json`, etapa 2).

| Servicio | Función |
|---|---|
| `api` | API FastAPI: recibe las consultas, recupera documentos y coordina los servicios |
| `mock-llm` | Proveedor de lenguaje simulado: devuelve una respuesta determinista marcada como `[SIMULADO]` |
| `tools` | Servicio de herramientas de solo lectura |

## Objetivos de la Unidad 2

- Identificar amenazas reales sobre una aplicación de IA con recuperación de documentos (RAG) y herramientas.
- Observar en el laboratorio tres problemas de seguridad que **se mantienen a propósito**: la API no exige credencial, la recuperación devuelve documentos de otra empresa y un documento contiene instrucciones maliciosas (inyección indirecta de instrucciones).
- Comprobar un control que sí funciona: las operaciones destructivas están bloqueadas.
- Leer y ampliar el registro de riesgos `security/risk_register.csv`, relacionando cada riesgo con su control y su evidencia.

Las vulnerabilidades se corrigen en unidades posteriores. En esta unidad se analizan y se documentan.

## Requisitos

- **Docker**: Docker Desktop en Windows (con el motor WSL 2) o Docker Engine con el complemento Compose v2 en Linux / WSL.
- **Git**.
- **Navegador web** para Swagger.
- Puerto `8000` libre en el propio equipo.
- No hace falta Python: todo se ejecuta en contenedores.

Comprobar las herramientas (igual en WSL / Linux y en PowerShell):

```bash
git --version
docker --version
docker compose version
```

## Descargar la Unidad 2

El mismo comando sirve en WSL / Linux y en PowerShell:

```bash
git clone --branch unidad-02 https://github.com/Datiacode-Tech/devsecops-ia-labs.git devsecops-ia-unidad-02
cd devsecops-ia-unidad-02
```

Git avisa de que la copia está en estado *detached HEAD*: es lo normal al descargar una etiqueta.

## Arrancar el laboratorio

Desde la carpeta del proyecto (igual en WSL / Linux y en PowerShell):

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

`docker compose ps` debe mostrar los tres servicios (`api`, `mock-llm` y `tools`) en estado `running`. La primera construcción tarda unos minutos.

## Swagger

Abre http://127.0.0.1:8000/docs en el navegador. Desde ahí se pueden probar `GET /health`, `POST /ask` y `POST /tools/execute` con **Try it out**. En esta unidad no hace falta ninguna credencial.

## Consultar la API desde la terminal

WSL / Linux:

```bash
# Estado del servicio: HTTP 200 y "stage": 2
curl -s -w ' HTTP %{http_code}\n' http://127.0.0.1:8000/health

# Consulta sin ninguna credencial: HTTP 200
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"¿Cuántos días de vacaciones tengo?","tenant":"empresa-a"}'

# Consulta como empresa-a sobre el presupuesto: observa las fuentes devueltas
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"presupuesto","tenant":"empresa-a"}'

# Operación destructiva: HTTP 403
curl -s -w ' HTTP %{http_code}\n' -X POST http://127.0.0.1:8000/tools/execute \
  -H 'Content-Type: application/json' \
  -d '{"operation":"delete_document","document_id":"empresa-a-001"}'
```

Windows PowerShell. `Invoke-WebRequest` lanza una excepción con los códigos 4xx; esta función muestra el código y el cuerpo en todos los casos:

```powershell
function Invoke-Lab {
    param([string]$Metodo, [string]$Ruta, $Cuerpo = $null)
    $p = @{ Uri = "http://127.0.0.1:8000$Ruta"; Method = $Metodo; UseBasicParsing = $true }
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

Invoke-Lab GET /health                                                                          # 200, "stage":2
Invoke-Lab POST /ask @{ question = '¿Cuántos días de vacaciones tengo?'; tenant = 'empresa-a' }  # 200
Invoke-Lab POST /ask @{ question = 'presupuesto'; tenant = 'empresa-a' }                         # observa las fuentes
Invoke-Lab POST /tools/execute @{ operation = 'delete_document'; document_id = 'empresa-a-001' } # 403
```

Si los acentos se ven mal en la consola de PowerShell, ejecuta antes `[Console]::OutputEncoding = [Text.Encoding]::UTF8`.

Opcional, si el equipo tiene Python 3: `python scripts/demo_unidad_02.py` muestra el estado de la API y un extracto del registro de riesgos.

## Qué hay que observar

Los documentos ficticios están en `data/documents.json`: dos de `empresa-a` y uno de `empresa-b`.

| Observación | Cómo se ve en el laboratorio |
|---|---|
| Acceso sin credencial | `POST /ask` responde HTTP 200 sin ninguna credencial. Cualquiera que llegue a la API puede consultarla |
| Acceso a documentos de otra empresa | Al preguntar `presupuesto` como `empresa-a`, `sources` incluye `empresa-b-001`. El campo `tenant` se recibe, pero no se usa para filtrar. La herramienta `read_document` también lee `empresa-b-001` |
| Inyección indirecta de instrucciones | El documento `empresa-a-002` contiene, dentro de una política de gastos, una instrucción maliciosa ficticia. Al preguntar por vacaciones o por gastos, ese texto llega al modelo como contexto y aparece en la respuesta. El modelo simulado no la ejecuta; un modelo real podría intentar seguirla |
| Operación destructiva bloqueada | `delete_document` devuelve HTTP 403: la API solo admite `read_document` (allowlist) |

## Registro de riesgos y ejercicio

`security/risk_register.csv` tiene ocho columnas:

```
id,activo,amenaza,impacto,probabilidad,control,evidencia,estado
```

Contiene los riesgos de partida:

| Riesgo | Estado |
|---|---|
| R-01 Acceso sin credencial | En seguimiento: el control previsto todavía no existe |
| R-02 Acceso a documentos de otra empresa (tenant ajeno) | En seguimiento |
| R-03 Operación no autorizada | Mitigado: allowlist de operaciones, con la evidencia `test_mutation_is_denied` |

El ejercicio de la unidad consiste en **añadir a este fichero dos filas nuevas**, con los identificadores que indica el enunciado, para riesgos que hayas observado y que todavía no figuren en el registro. Reglas que comprueban las pruebas:

- Las ocho columnas en el mismo orden, separadas por comas y sin campos vacíos. No uses comas dentro de un campo.
- Identificador con el formato `R-NN` y sin repetir.
- La evidencia es el nombre de una prueba que existe en `tests/` o una prueba prevista marcada como pendiente (`pendiente_...` o `..._pendiente`).
- Un riesgo con evidencia pendiente **no puede** tener el estado `Mitigado`: documentar un control no significa haberlo implementado.

Edita el fichero con un editor de texto (VS Code, Bloc de notas…) y guárdalo en UTF-8 **sin BOM**. Excel puede cambiar los separadores o la codificación y romper el formato. Después ejecuta las pruebas: deben seguir pasando las 9.

## Pruebas

Dentro del contenedor de la API, montando las pruebas y el registro de riesgos. El mismo comando sirve en WSL / Linux y en PowerShell:

```bash
docker compose run --rm -v ./tests:/code/tests:ro -v ./security:/code/security:ro -e PYTHONDONTWRITEBYTECODE=1 api python -m pytest -q -p no:cacheprovider /code/tests
```

Resultado esperado: `9 passed` (puede aparecer `1 warning`). Las pruebas leen tu copia de `security/risk_register.csv`, así que también validan las filas que añadas.

Opcional, sin contenedores y con Python 3 en el equipo:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## Registros

```bash
docker compose logs --tail=30 api      # últimas líneas de la API
docker compose logs -f api             # en directo; Ctrl+C para salir
```

## Detener el laboratorio

```bash
docker compose down
```

Detiene y elimina los contenedores y la red del laboratorio. Las imágenes se conservan, así que el siguiente arranque es más rápido.

## Reglas del laboratorio

- La API solo se publica en `127.0.0.1`; `mock-llm` y `tools` permanecen en la red privada de Docker.
- El servicio de herramientas nunca ejecuta operaciones destructivas.
- No despliegues este laboratorio en un servidor accesible desde Internet.
- Nunca introduzcas credenciales ni datos reales.
