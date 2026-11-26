# Unidad 10 · Seguridad en RAG, agentes y MCP

Proteger el modelo no basta. Un asistente con recuperación de documentos (RAG) y herramientas también necesita proteger qué documentos recupera, que esos documentos no hayan sido alterados y qué acciones puede ejecutar. Cuatro ejemplos encadenados:

```
Proteger los documentos recuperados → Proteger su integridad → Autorizar las acciones del agente → Proteger las herramientas MCP
```

| N.º | Ejemplo | Qué se protege | Archivos |
|---|---|---|---|
| 1 | Aislamiento entre empresas en RAG | Seguridad de la recuperación | `rag.py`, `sesiones.json` |
| 2 | Envenenamiento del contexto RAG | Integridad de los documentos | `rag.py`, `huellas-documentos.json`, `consultar_api.py` |
| 3 | Seguridad en herramientas de agentes | Autorización de herramientas | API del laboratorio (`/tools/execute`) |
| 4 | Seguridad en servidores MCP | Controles de herramientas expuestas | `servidor_mcp_simulado.py`, `catalogo-herramientas.json` |

## Qué es real y qué es simulado

En esta unidad aparecen tres tipos de resultado. Conviene no mezclarlos:

| Tipo | Dónde | Qué demuestra |
|---|---|---|
| **Vulnerabilidades observadas en la API real** | `curl` contra `/ask` y `/tools/execute`, la llamada directa al servicio `tools` y `consultar_api.py` (ejecuta el código real de `/ask`) | Lo que hace hoy el laboratorio: `/ask` mezcla empresas (ejemplo 1), un documento alterado llega a la respuesta (ejemplo 2) y `read_document` acepta documentos de otra empresa (ejemplo 3, caso C3). **Siguen presentes**: la API no se modifica en esta unidad |
| **Controles demostrados fuera de la aplicación** | `rag.py`, modo `protegido`: filtro por la empresa de la sesión y huellas SHA-256 | Cómo debería recuperar documentos el servidor. Son controles reales en Python, pero **no están integrados en la API** |
| **Comportamiento simulado de un servidor MCP** | `servidor_mcp_simulado.py` y `catalogo-herramientas.json` | Las comprobaciones que debe hacer un servidor MCP (permiso, argumentos, recurso). **No es un servidor MCP** ni implementa el protocolo, y `delete_document` no borra nada |

Las identidades `ana` (empresa-a) y `bruno` (empresa-b) de `sesiones.json` son **ficticias**: representan a dos usuarias que el servidor ya hubiera autenticado. La API real no tiene esta información: atribuye todas las peticiones a `empresa-a`.

Recuerda que `mock-llm` no es un modelo: devuelve el texto de los documentos recuperados (Unidad 9). Cuando un dato aparece en su respuesta, lo que se demuestra es que ese dato **llegó al modelo**, no que un modelo lo haya «creído».

## Preparación

Comandos para **WSL / Linux** desde la **carpeta raíz del laboratorio** (donde está `compose.yaml`). Hacen falta Python 3, `jq`, Docker, los servicios en marcha (`docker compose up -d --build`) y `.env` con la clave, como en unidades anteriores.

Copia de trabajo en `artifacts/`, excluida de Git:

```bash
mkdir -p artifacts
cp -r extras/unidad-10-seguridad-rag-agentes-mcp artifacts/rag-mcp
cd artifacts/rag-mcp
CLAVE=$(sed -n 's/^DEMO_API_KEY=//p' ../../.env | tr -d '\r')
```

**Los comandos se ejecutan desde `artifacts/rag-mcp`**, salvo los que empiezan por `cd ../..`, que necesitan la carpeta raíz para usar `docker compose`. Los scripts leen los documentos reales del laboratorio (`data/documents.json`) y nunca los modifican.

`CLAVE` es una variable de la terminal, no exportada; si abres otra terminal, repite la última línea.

---

## Ejemplo 1. Aislamiento de información entre empresas en RAG

**Objetivo:** comprobar si la recuperación puede entregar al modelo documentos de otra empresa, y dónde debe aplicarse el control.

**Situación inicial:** el laboratorio tiene documentos de `empresa-a` y `empresa-b` (`data/documents.json`, campo `tenant`). Una persona de `empresa-a` no debería recuperar documentos de `empresa-b`.

**Explicación:** antes de arreglar nada, hay que saber cómo funciona hoy la API:

| Pregunta | Respuesta en el código real |
|---|---|
| ¿Cómo se identifica la empresa del usuario? | La API key se comprueba en `app/security.py`, que atribuye **todas** las peticiones a una única identidad ficticia, `empresa-a` |
| ¿Cómo se recuperan los documentos? | `app/retrieval.py` cuenta las palabras en común con la pregunta y devuelve los 2 mejores |
| ¿Qué metadatos de empresa existen? | Cada documento tiene `tenant`; la petición puede traer un campo `tenant` |
| ¿Se filtra por empresa? | **No.** `search_documents` recibe el `tenant` pero no lo usa |

El filtro debe aplicarse en la recuperación, **antes** de entregar los documentos al modelo, y con la empresa que decide el servidor a partir de la identidad autenticada, no con la que escribe el cliente.

`rag.py` repite exactamente la búsqueda de `app/retrieval.py` (una prueba lo comprueba) en tres modos:

| Modo | Filtro de empresa |
|---|---|
| `vulnerable` | Ninguno, como `/ask` hoy |
| `tenant-cliente` | La empresa que declara el cliente con `--tenant` |
| `protegido` | La empresa de la sesión, según `sesiones.json` (lado servidor); `--tenant` se ignora |

**Pasos:**

```bash
# 1. Comportamiento real de /ask: el cliente declara empresa-a
curl -s -w '\n' -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" \
  -d '{"question":"¿Cuál es el presupuesto de la política financiera?","tenant":"empresa-a"}'

# 2. Las tres variantes de recuperación con la misma pregunta
python3 rag.py vulnerable "¿Cuál es el presupuesto de la política financiera?"
python3 rag.py tenant-cliente "¿Cuál es el presupuesto de la política financiera?" --tenant empresa-a
python3 rag.py protegido "¿Cuál es el presupuesto de la política financiera?" --sesion ana
```

**Resultado esperado:**

Paso 1 (API real):

```
{"answer":"[SIMULADO] Respuesta basada en contexto: Política financiera confidencial empresa-b: presupuesto 1000 unidades ficticias. ...","sources":["empresa-b-001","empresa-a-002"],"stage":10}
```

Paso 2:

```
Documentos entregados al modelo: empresa-b-001, empresa-a-002
  [empresa-b-001] Política financiera confidencial empresa-b: presupuesto 1000 unidades ficticias.
  ...
Documentos entregados al modelo: empresa-a-002, empresa-a-001
  ...
Sesión ana: empresa empresa-a (según el servidor)
Documentos entregados al modelo: empresa-a-002, empresa-a-001
  ...
```

**Interpretación:** el fallo de aislamiento **existe en la API real**: con una clave de `empresa-a`, el documento confidencial de `empresa-b` llega al modelo y a la respuesta. El modo `vulnerable` de `rag.py` reproduce exactamente los mismos documentos. Los dos modos con filtro devuelven solo documentos de `empresa-a`, pero por razones distintas, que el ejercicio pone a prueba.

Ocultar el nombre de `empresa-b` en la respuesta final no arreglaría nada: el documento ya habría llegado al modelo, que podría usarlo o repetirlo de otra forma. El control va en la recuperación.

**Conclusión:** el aislamiento entre empresas se aplica al recuperar los documentos, con una identidad que el cliente no puede cambiar.

**Pequeño ejercicio:** intenta recuperar el documento de `empresa-b` siendo `ana`: repite la petición del paso 1 con `"tenant":"empresa-b"` y prueba `tenant-cliente` y `protegido` con `--tenant empresa-b`. ¿Qué modo se deja engañar y por qué?

---

## Ejemplo 2. Envenenamiento del contexto RAG

**Objetivo:** ver cómo un documento alterado cambia la información que llega a la respuesta, y cómo detectarlo.

**Situación inicial:** el manual de vacaciones (`empresa-a-001`) dice que las solicitudes se registran «con quince días de antelación». Un atacante con acceso a la colección de documentos cambia el dato por «dos días». No añade ninguna instrucción: solo cambia un dato.

**Explicación:** en la Unidad 9 el ataque eran instrucciones dirigidas al modelo. Aquí el ataque son **los datos**: el modelo puede funcionar exactamente como está previsto y aun así dar una respuesta incorrecta, porque la fuente es incorrecta.

La defensa más sencilla es la de la Unidad 6 y la Unidad 8: una **huella SHA-256** de cada documento guardada en un registro de confianza (`huellas-documentos.json`). El modo `protegido` descarta cualquier documento cuya huella no coincida antes de entregarlo al modelo.

**Pasos:**

```bash
# 1. Copia manipulada de la colección (los documentos originales no se tocan)
cp ../../data/documents.json documentos.json
sed -i 's/con quince días de antelación/con dos días de antelación/' documentos.json

# 2. Recuperación con la colección original y con la manipulada
python3 rag.py vulnerable "¿Con cuántos días de antelación se registran las solicitudes de vacaciones?"
python3 rag.py vulnerable "¿Con cuántos días de antelación se registran las solicitudes de vacaciones?" --documentos documentos.json

# 3. El /ask REAL con la colección manipulada (montada en lugar de la original solo para esta ejecución)
cd ../..
docker compose run --rm --no-deps -T \
  -v ./artifacts/rag-mcp/documentos.json:/code/data/documents.json:ro \
  -v ./artifacts/rag-mcp/consultar_api.py:/code/consultar_api.py:ro \
  api python consultar_api.py "¿Con cuántos días de antelación se registran las solicitudes de vacaciones?"
cd artifacts/rag-mcp

# 4. Comprobar la huella del documento
jq -j '.[] | select(.id == "empresa-a-001") | .text' documentos.json | sha256sum
jq -r '."empresa-a-001"' huellas-documentos.json

# 5. Recuperación protegida con la colección manipulada
python3 rag.py protegido "¿Con cuántos días de antelación se registran las solicitudes de vacaciones?" --documentos documentos.json
```

**Resultado esperado:**

Paso 2: el mismo documento, primero con «quince días» y después con «dos días».

Paso 3 (API real, además de una línea `Container … Created` de Docker):

```
{'answer': '[SIMULADO] Respuesta basada en contexto: Manual de vacaciones: las solicitudes se registran con dos días de antelación. ...', 'sources': ['empresa-a-001', 'empresa-a-002'], 'stage': 10}
```

Paso 4: dos huellas distintas (`d0101f64…` frente a `c1895c41…`).

Paso 5:

```
Sesión ana: empresa empresa-a (según el servidor)
AVISO: empresa-a-001 descartado: su huella no coincide con el registro
Documentos entregados al modelo: empresa-a-002
  ...
```

**Interpretación:** el dato manipulado llega a la respuesta del `/ask` real: `mock-llm` repite lo que recibe, y un LLM real lo usaría como fuente fiable. Nadie ha atacado al modelo. La huella detecta la alteración y el documento se descarta, con un aviso que permite investigar. Descartarlo deja la pregunta sin la información correcta: es preferible a dar un dato falso, pero obliga a restaurar el original.

La huella solo protege si el registro está en un lugar que el atacante no puede modificar, y solo sirve para documentos que no cambian a menudo. Para fuentes que se actualizan constantemente se usan controles de procedencia: quién puede publicar documentos en la colección y con qué revisión.

**Conclusión:** un sistema RAG es tan fiable como sus fuentes. La integridad y la procedencia de los documentos se comprueban antes de que entren en el contexto.

**Pequeño ejercicio:** en tu copia `documentos.json`, cambia otro dato (por ejemplo, el presupuesto de `empresa-b-001`), comprueba con el modo `protegido` y la sesión que corresponda que se detecta la alteración y restaura después la versión original.

---

## Ejemplo 3. Seguridad en herramientas de agentes

**Objetivo:** comprobar que el servidor, y no el modelo, decide qué herramientas se ejecutan y con qué argumentos.

**Situación inicial:** un agente traduce la petición del usuario en una llamada a una herramienta. En el laboratorio, la API la recibe en `/tools/execute` y la reenvía al servicio interno `tools`.

**Explicación:** controles que ya tiene el laboratorio (todo en el código real):

| Control | Dónde | Qué hace |
|---|---|---|
| Autenticación | `app/security.py` | Sin una API key válida, 401 |
| Lista de herramientas permitidas | `app/main.py`, `tool_call` | Solo `read_document`; cualquier otra operación, 403 |
| Validación de argumentos | `app/main.py`, `ToolCall` | `document_id` con el formato `empresa-<nombre>-<tres dígitos>`; si no, 422 |
| Identidad del servidor | `app/main.py` | El `tenant` que se envía al servicio `tools` es el de la identidad, no el que escribe el cliente |
| Segunda comprobación | `tools_service/main.py` | El servicio `tools` también rechaza lo que no sea lectura |

Ningún control depende del prompt: aunque el modelo pidiera borrar un documento, la API lo rechazaría.

**Pasos:**

```bash
# Caso A. Operación permitida
curl -s -w '  [HTTP %{http_code}]\n' -X POST http://127.0.0.1:8000/tools/execute -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" \
  -d '{"operation":"read_document","document_id":"empresa-a-001"}'

# Caso B. Operación no autorizada
curl -s -w '  [HTTP %{http_code}]\n' -X POST http://127.0.0.1:8000/tools/execute -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" \
  -d '{"operation":"delete_document","document_id":"empresa-a-001"}'

# Caso C1. Argumento con un formato no válido (intento de ruta)
curl -s -w '  [HTTP %{http_code}]\n' -X POST http://127.0.0.1:8000/tools/execute -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" \
  -d '{"operation":"read_document","document_id":"../../etc/passwd"}'

# Caso C2. Intento de cambiar la empresa desde el cuerpo
curl -s -w '  [HTTP %{http_code}]\n' -X POST http://127.0.0.1:8000/tools/execute -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" \
  -d '{"operation":"read_document","document_id":"empresa-a-001","tenant":"empresa-b"}'

# Caso C3. Documento de otra empresa con un formato válido
curl -s -w '  [HTTP %{http_code}]\n' -X POST http://127.0.0.1:8000/tools/execute -H 'Content-Type: application/json' -H "x-api-key: $CLAVE" \
  -d '{"operation":"read_document","document_id":"empresa-b-001"}'

# Segunda capa: el servicio tools, llamado directamente desde dentro de la red interna
cd ../..
docker compose exec -T api python -c "import httpx; r = httpx.post('http://tools:8200/execute', json={'operation': 'delete_document', 'document_id': 'empresa-a-001', 'tenant': 'empresa-a'}); print(r.status_code, r.json())"
cd artifacts/rag-mcp
```

**Resultado esperado** (todo de la API real):

```
{"operation":"read_document","document_id":"empresa-a-001","status":"read-only"}  [HTTP 200]
{"detail":"Operación no permitida"}  [HTTP 403]
{"detail":[{"type":"string_pattern_mismatch",...,"input":"../../etc/passwd",...}]}  [HTTP 422]
{"operation":"read_document","document_id":"empresa-a-001","status":"read-only"}  [HTTP 200]
{"operation":"read_document","document_id":"empresa-b-001","status":"read-only"}  [HTTP 200]
403 {'detail': 'Solo lectura permitida'}
```

**Interpretación:**

- A: la operación de consulta está en la lista y sus argumentos son válidos.
- B: `delete_document` no está en la lista; la API responde 403 y el servicio `tools` tampoco lo aceptaría (segunda capa, **mínimo privilegio**: el servicio solo sabe leer).
- C1: la validación del formato impide argumentos fuera del patrón.
- C2: el campo `tenant` del cuerpo se ignora; el servidor usa su identidad.
- C3: **fallo real.** El formato es válido y la operación está permitida, pero nadie comprueba que `empresa-b-001` pertenezca a la empresa de quien lo pide. En el laboratorio el servicio `tools` no devuelve el contenido (solo confirma la lectura), pero en un sistema real sería un acceso indebido. Falta la **autorización por recurso**, que el ejemplo 4 muestra.

**Conclusión:** que el modelo proponga una acción no significa que el servidor deba ejecutarla. La lista de herramientas, la validación de argumentos y la identidad del servidor se imponen en el código; y además hay que comprobar el permiso sobre cada recurso concreto.

**Pequeño ejercicio:** ejecuta una operación permitida y otra rechazada (distintas de las del ejemplo) y explica qué control interviene en cada caso y en qué archivo está.

---

## Ejemplo 4. Seguridad en servidores MCP

**Objetivo:** entender que publicar una herramienta en un servidor MCP no equivale a autorizar su ejecución.

**Situación inicial:** con **Model Context Protocol (MCP)**, un cliente de IA pregunta a un servidor qué herramientas ofrece (descubrimiento), recibe su nombre, descripción y argumentos, y pide ejecutarlas. Si el servidor ejecuta todo lo que se le pide, el riesgo es el del ejemplo 3, multiplicado por cada cliente que se conecte.

**Explicación:** `servidor_mcp_simulado.py` es una **simulación de los controles de seguridad de un servidor MCP**. **No es un servidor MCP** ni es compatible con el protocolo (no hay JSON-RPC, transporte ni sesiones); solo reproduce las comprobaciones que un servidor real debe hacer, en este orden:

1. La herramienta existe en el catálogo (`catalogo-herramientas.json`).
2. La sesión tiene permiso para esa herramienta (`sesiones.json`, lado servidor).
3. Los argumentos son exactamente los esperados y tienen el formato correcto.
4. El recurso pertenece a la empresa de la sesión (la autorización por recurso que faltaba en el caso C3).

Las dos herramientas son ficticias: `read_document` lee un documento real del laboratorio; `delete_document` aparece en el catálogo, pero ninguna sesión tiene permiso, y aunque lo tuviera no borraría nada.

Los mensajes de rechazo por recurso no distinguen entre «no existe» y «es de otra empresa», para no revelar qué documentos existen.

**Pasos:**

```bash
# 1. Descubrimiento: catálogo de herramientas
python3 servidor_mcp_simulado.py listar

# 2. Ejecución permitida
python3 servidor_mcp_simulado.py ejecutar ana read_document '{"document_id": "empresa-a-001"}'

# 3. Herramienta publicada pero no autorizada
python3 servidor_mcp_simulado.py ejecutar ana delete_document '{"document_id": "empresa-a-001"}'

# 4. Argumentos incorrectos: formato y campos de más
python3 servidor_mcp_simulado.py ejecutar ana read_document '{"document_id": "../../etc/passwd"}'
python3 servidor_mcp_simulado.py ejecutar ana read_document '{"document_id": "empresa-a-001", "tenant": "empresa-b"}'

# 5. Recurso de otra empresa (el caso C3 del ejemplo 3)
python3 servidor_mcp_simulado.py ejecutar ana read_document '{"document_id": "empresa-b-001"}'
echo "Código de salida: $?"

# 6. Pruebas automatizadas de los ejemplos 1, 2 y 4
docker run --rm -v "$PWD:/code/artifacts/rag-mcp:ro" -w /code/artifacts/rag-mcp -e PYTHONDONTWRITEBYTECODE=1 \
  devsecops-ia-lab/api:local python -m pytest -q -p no:cacheprovider test_unidad10.py
```

**Resultado esperado:**

```
read_document: Lee un documento de la empresa del usuario. Argumentos: document_id
delete_document: Borra un documento. Ficticia: en este laboratorio no borra nada. Argumentos: document_id
PERMITIDO: Manual de vacaciones: las solicitudes se registran con quince días de antelación.
RECHAZADO: la sesión ana no tiene permiso para delete_document
RECHAZADO: el argumento document_id no tiene un formato válido
RECHAZADO: argumentos esperados: document_id
RECHAZADO: documento inexistente o de otra empresa
Código de salida: 1
.......................                                                  [100%]
23 passed
```

**Interpretación:** `delete_document` se ve en el catálogo, pero no se puede ejecutar: descubrir no es autorizar. El campo `tenant` añadido se rechaza en lugar de ignorarse: en MCP los argumentos los genera un modelo, y un argumento inesperado es motivo de sospecha. La comprobación del recurso cierra el hueco del caso C3. Cada rechazo termina con código 1.

Las descripciones del catálogo también son texto que el cliente entrega al modelo: un servidor MCP no confiable podría incluir en ellas instrucciones (la inyección indirecta de la Unidad 9). Solo deben conectarse servidores MCP de confianza.

**Conclusión:** un servidor MCP debe autorizar en el servidor cada herramienta, cada argumento y cada recurso, con una identidad de confianza. Publicar una herramienta no significa autorizar su ejecución.

**Pequeño ejercicio:** añade una solicitud con argumentos incorrectos o con un documento que la sesión no puede leer, y comprueba qué control la rechaza.

---

## Resumen

| Riesgo | En la API del laboratorio | Control demostrado |
|---|---|---|
| Documentos de otra empresa en el contexto | Ocurre (`/ask`) | Filtro por la empresa de la sesión, antes del modelo |
| Documento manipulado | Llega a la respuesta | Huella SHA-256 frente a un registro de confianza |
| Operación no permitida | Rechazada (403) | Lista de herramientas en el servidor |
| Argumentos manipulados | Rechazados por formato (422) | Validación de argumentos |
| Recurso de otra empresa en una herramienta | Aceptado (200) | Autorización por recurso (servidor MCP simulado) |

Los controles de `rag.py` y del servidor MCP simulado **no están integrados en la API**: los fallos de `/ask` y del caso C3 siguen presentes en el laboratorio.

## Limpieza

```bash
cd ../..
rm -rf artifacts/rag-mcp
```
