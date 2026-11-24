# Unidad 6 · Seguridad de la cadena de suministro de software y modelos

Cuatro ejemplos cortos. Tu código puede ser correcto y, aun así, la aplicación puede ser vulnerable por lo que **no has escrito tú**: bibliotecas de terceros, paquetes descargados y modelos de IA. Estos ejemplos enseñan a responder a tres preguntas:

- ¿Qué componentes de terceros usa la aplicación y en qué versión? (inventario, SBOM)
- ¿Alguno tiene vulnerabilidades conocidas? (análisis de dependencias)
- ¿El archivo que he descargado es exactamente el que publicó su autor? (integridad con SHA-256)

| N.º | Ejemplo | Herramienta |
|---|---|---|
| 1 | Detectar vulnerabilidades en dependencias Python | Trivy |
| 2 | Generar un SBOM | Trivy y `jq` |
| 3 | Comprobar la integridad de un paquete | `sha256sum` |
| 4 | Comprobar la integridad de un modelo de IA | `sha256sum` |

Nada de esta carpeta se instala en la aplicación. `dependencias/versiones-antiguas.txt` contiene versiones antiguas con vulnerabilidades publicadas: **solo se analiza, nunca se instala**. No se llama `requirements.txt` a propósito: así no lo confunden con las dependencias del proyecto ni las personas ni las herramientas que buscan archivos con ese nombre.

## Preparación

Los comandos están pensados para **WSL / Linux** y se ejecutan desde la **carpeta raíz del laboratorio** (donde está `compose.yaml`).

- Docker en marcha y la imagen de la API construida (`docker compose up -d --build`, como en la Unidad 5).
- Conexión a Internet: Trivy descarga su base de datos de vulnerabilidades la primera vez.
- `jq` para consultar el SBOM (ejemplo 2). Si no lo tienes: `sudo apt install jq`. También se indica una alternativa sin `jq`.

Trivy se ejecuta con Docker, en la misma versión fijada por número y por digest que en la Unidad 5:

```bash
TRIVY=aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
mkdir -p artifacts
```

`artifacts/` está excluida de Git y de las imágenes: todo lo que generan los ejemplos va ahí.

---

## Ejemplo 1. Detectar vulnerabilidades en dependencias Python

**Objetivo:** comprobar si las bibliotecas de terceros de la aplicación tienen vulnerabilidades conocidas.

**Situación inicial:** la API usa FastAPI, uvicorn, httpx y pytest. Esas bibliotecas, a su vez, instalan otras (dependencias transitivas). Un fallo en cualquiera de ellas afecta a la aplicación aunque nuestro código sea correcto.

**Pasos:**

```bash
# 1. Qué declara el proyecto
cat requirements.txt

# 2. Analizar las dependencias declaradas
docker run --rm -v ./requirements.txt:/src/requirements.txt:ro -v trivy-cache:/root/.cache $TRIVY fs --quiet --scanners vuln /src

# 3. Versiones realmente instaladas en la imagen de la API
docker run --rm devsecops-ia-lab/api:local pip freeze > artifacts/requirements-instalados.txt
cat artifacts/requirements-instalados.txt

# 4. Analizar las versiones instaladas
docker run --rm -v ./artifacts/requirements-instalados.txt:/src/requirements.txt:ro -v trivy-cache:/root/.cache $TRIVY fs --quiet --scanners vuln /src

# 5. Analizar el archivo de demostración (versiones antiguas)
docker run --rm -v ./extras/unidad-06-cadena-suministro/dependencias/versiones-antiguas.txt:/src/requirements.txt:ro -v trivy-cache:/root/.cache $TRIVY fs --quiet --scanners vuln /src

# 6. Solo las vulnerabilidades graves
docker run --rm -v ./extras/unidad-06-cadena-suministro/dependencias/versiones-antiguas.txt:/src/requirements.txt:ro -v trivy-cache:/root/.cache $TRIVY fs --quiet --scanners vuln --severity HIGH,CRITICAL /src
```

**Explicación:**

1. `requirements.txt` declara **rangos** (`fastapi>=0.115,<1.0`), no versiones exactas.
2. `trivy fs` analiza una carpeta. Trivy reconoce el archivo por su nombre, `requirements.txt`, así que se monta con ese nombre. `--scanners vuln` limita el análisis a vulnerabilidades y `--quiet` oculta la barra de descarga.
3. `pip freeze` lista lo que **realmente** se instaló en la imagen, con versión exacta e incluidas las dependencias transitivas. Es posible que veas un aviso sobre la caché de `pip`: no afecta al resultado.
4. Se repite el análisis con las versiones exactas.
5. y 6. El archivo de demostración fija tres versiones antiguas (`requests 2.19.1`, `PyYAML 5.3` y `Jinja2 2.10`) para ver cómo es un informe con hallazgos. Se monta en el contenedor con el nombre `requirements.txt`, igual que en el paso 4, para que Trivy lo reconozca.

**Resultado esperado:**

- Paso 2: Trivy no analiza nada: la tabla muestra `-` y la leyenda `'-': Not scanned`. Con rangos no sabe qué versión se instalará, así que no puede compararla con su base de datos. Sin `--quiet`, Trivy lo explica con el aviso `Supported files for scanner(s) not found`.
- Paso 3: unas 22 bibliotecas, aunque `requirements.txt` solo nombra 4.
- Paso 4: `requirements.txt │ pip │ 0`. Cero vulnerabilidades **conocidas** en las versiones instaladas en el momento del análisis.
- Paso 5: una tabla con 13 vulnerabilidades (2 críticas, 2 altas y 9 medias). Cada fila indica:

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `Library` | Paquete afectado | `PyYAML` |
| `Vulnerability` | Identificador público de la vulnerabilidad | `CVE-2020-14343` |
| `Severity` | Gravedad | `CRITICAL` |
| `Installed Version` | Versión que usamos | `5.3` |
| `Fixed Version` | Primera versión que la corrige | `5.4` |

- Paso 6: solo 4 filas: las dos críticas de PyYAML y una alta de Jinja2 y otra de requests.

Las cifras dependen de la base de datos de Trivy y pueden aumentar con el tiempo, porque cada día se publican vulnerabilidades nuevas. Las versiones corregidas no cambian.

**Cómo actuar ante los resultados:**

1. Empieza por `CRITICAL` y `HIGH`.
2. Comprueba si existe `Fixed Version`: casi siempre basta con actualizar a esa versión o a una posterior.
3. Valora si el código vulnerable se usa realmente en la aplicación. Un hallazgo es información; el riesgo depende del uso.
4. Actualiza, reconstruye y vuelve a analizar. Las pruebas automatizadas comprueban que la actualización no rompe nada.

**Conclusión:** las dependencias se analizan con versiones exactas. Un análisis sobre rangos no detecta nada y puede dar una falsa sensación de seguridad.

**Pequeño ejercicio:** copia el archivo de demostración como `artifacts/versiones-corregidas.txt`, cambia `PyYAML==5.3` por la versión que indica Trivy en `Fixed Version` y vuelve a analizarlo, montándolo como en el paso 5. ¿Cuántas vulnerabilidades críticas quedan?

---

## Ejemplo 2. Generar un SBOM

**Objetivo:** obtener un inventario de los componentes de terceros de la aplicación en un formato estándar.

**Situación inicial:** se publica una vulnerabilidad grave en una biblioteca. La primera pregunta es: «¿la usamos?, ¿en qué versión?». Sin inventario, hay que revisar proyecto por proyecto.

Un **SBOM** (*Software Bill of Materials*) es la lista de ingredientes de un software: cada componente con su versión y un identificador estándar. **CycloneDX** es uno de los formatos más usados.

**Pasos** (reutilizan `artifacts/requirements-instalados.txt` del ejemplo 1):

```bash
# 1. Generar el SBOM en formato CycloneDX
docker run --rm -v ./artifacts/requirements-instalados.txt:/src/requirements.txt:ro -v trivy-cache:/root/.cache $TRIVY fs --quiet --format cyclonedx /src > artifacts/sbom-api.cdx.json

# 2. Listar los componentes
jq -r '.components[] | select(.type == "library") | "\(.name) \(.version)"' artifacts/sbom-api.cdx.json

# 3. Buscar un componente concreto
jq -r '.components[] | select(.name == "starlette") | .purl' artifacts/sbom-api.cdx.json

# Alternativa sin jq
grep -o '"purl": "[^"]*"' artifacts/sbom-api.cdx.json

# 4. Analizar el SBOM en busca de vulnerabilidades
docker run --rm -v ./artifacts:/artifacts:ro -v trivy-cache:/root/.cache $TRIVY sbom --quiet /artifacts/sbom-api.cdx.json
```

**Explicación:**

1. `--format cyclonedx` hace que Trivy genere un SBOM en lugar de un informe. La salida se redirige con `>` a un archivo del equipo; así el archivo pertenece a tu usuario y no a root.
2. `jq` recorre la lista `components` y muestra nombre y versión de cada biblioteca.
3. `purl` (*package URL*) es el identificador estándar de un paquete: `pkg:pypi/starlette@1.10.0` significa «paquete de PyPI llamado starlette, versión 1.10.0».
4. `trivy sbom` analiza el inventario sin volver a abrir la imagen ni el proyecto.

**Resultado esperado:**

- Paso 1: `artifacts/sbom-api.cdx.json`, de unos 10 KB.
- Paso 2: las mismas 22 bibliotecas que `pip freeze`, por ejemplo `fastapi 0.162.2` y `starlette 1.10.0`.
- Paso 3: `pkg:pypi/starlette@1.10.0`.
- Paso 4: `requirements.txt │ pip │ 0`.

Las versiones son las de la imagen construida; pueden variar si la reconstruyes otro día, porque `requirements.txt` declara rangos.

**Para qué sirve ante una nueva vulnerabilidad:** si mañana se publica un fallo en `starlette`, basta con buscarlo en los SBOM guardados (paso 3) o volver a analizarlos (paso 4) para saber qué aplicaciones y versiones están afectadas, sin reconstruir nada.

**Conclusión:** un SBOM convierte «¿estamos afectados?» en una búsqueda de segundos. Se genera en cada versión que se entrega y se guarda junto a ella.

**Pequeño ejercicio:** genera el SBOM del archivo de demostración (`extras/unidad-06-cadena-suministro/dependencias/versiones-antiguas.txt`), guárdalo como `artifacts/sbom-demo.cdx.json` y analízalo con `trivy sbom` mostrando solo `HIGH` y `CRITICAL`. ¿Qué componente actualizarías primero?

---

## Ejemplo 3. Comprobar la integridad de un paquete

**Objetivo:** comprobar con un hash que un archivo descargado no ha sido modificado.

**Situación inicial:** descargas `utilidades_texto-1.0.0.py`, un paquete de terceros (ficticio). Su autor publica también el archivo `SHA256SUMS` con el hash esperado. Si alguien modifica el paquete por el camino o en el servidor de descarga, el contenido cambia, aunque el nombre siga siendo el mismo.

Un **hash SHA-256** es una huella de 64 caracteres hexadecimales calculada a partir del contenido. Cambiar un solo carácter del archivo produce una huella completamente distinta.

**Pasos:**

```bash
# 1. Copia de trabajo (no se modifican los originales)
mkdir -p artifacts/descargas
cp extras/unidad-06-cadena-suministro/descargas/* artifacts/descargas/
cd artifacts/descargas

# 2. Hash publicado por el autor
cat SHA256SUMS

# 3. Hash del archivo descargado
sha256sum utilidades_texto-1.0.0.py

# 4. Comprobación automática
sha256sum -c SHA256SUMS

# 5. Simular una manipulación: un cambio mínimo en el código
sed -i 's/return len(texto.split())/return len(texto.split()) + 1/' utilidades_texto-1.0.0.py

# 6. Repetir la comprobación
sha256sum -c SHA256SUMS

cd ../..
```

**Explicación:**

- `sha256sum archivo` calcula el hash.
- `sha256sum -c SHA256SUMS` lee los hashes esperados y compara cada archivo de la lista con su valor.
- `sed -i` cambia una sola línea: añade `+ 1` al resultado de una función. Es el tipo de cambio pequeño que pasaría desapercibido en una revisión rápida.

**Resultado esperado:**

```
809f9977cd17891c220de6539e3255a1a21af50301bc368ca87af28e0ae5d745  utilidades_texto-1.0.0.py
utilidades_texto-1.0.0.py: OK
```

Después de la modificación:

```
utilidades_texto-1.0.0.py: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

**Relación con pip:** pip puede exigir el hash de cada paquete. En el archivo de requisitos se escribe junto a la versión (`paquete==1.0.0 --hash=sha256:…`) y se instala con `pip install --require-hashes -r requirements.txt`. Si un paquete descargado no coincide, pip se niega a instalarlo. Para ver el formato que usa pip con nuestro archivo de ejemplo:

```bash
docker run --rm -v ./extras/unidad-06-cadena-suministro/descargas:/d:ro devsecops-ia-lab/api:local pip hash /d/utilidades_texto-1.0.0.py
```

El resultado, `--hash=sha256:809f9977…d745`, es el mismo valor que calcula `sha256sum`.

**Conclusión:** el hash detecta cualquier cambio respecto a un valor de referencia. Comprobarlo antes de usar un archivo es una medida sencilla y automatizable.

**Pequeño ejercicio:** `sha256sum -c` termina con un código de salida, que se consulta con `echo $?`. Comprueba qué código devuelve con el archivo modificado y cuál después de restaurar el original. ¿Por qué ese código es útil en un pipeline?

---

## Ejemplo 4. Comprobar la integridad de un modelo de IA

**Objetivo:** aplicar la misma comprobación a un artefacto de modelo, que también es una pieza de la cadena de suministro.

**Situación inicial:** la aplicación carga `clasificador-incidencias-v1.json`, un modelo **ficticio** que decide si una incidencia es urgente a partir de unos pesos y un umbral. El proveedor publica su hash:

```
e6b4ab0f6f5fb20216e3f3377d975840d1b9e6bdcacae52ea3d84398eb709b94
```

Un atacante no necesita romper el código: le basta con cambiar un número del modelo para que la aplicación tome decisiones distintas.

**Pasos:**

```bash
# 1. Copia de trabajo
mkdir -p artifacts/modelos
cp extras/unidad-06-cadena-suministro/modelos/* artifacts/modelos/
cd artifacts/modelos

# 2. Comprobar el modelo recibido
sha256sum -c SHA256SUMS

# 3. Simular una manipulación: subir el umbral para que casi nada se considere urgente
sed -i 's/"umbral_urgente": 0.50/"umbral_urgente": 0.95/' clasificador-incidencias-v1.json

# 4. Segunda verificación
sha256sum -c SHA256SUMS

cd ../..
```

**Explicación:** los comandos son los mismos que en el ejemplo 3. El cambio del paso 3 no rompe nada: el archivo sigue siendo un JSON válido y la aplicación lo cargaría sin errores, pero dejaría de marcar como urgentes casi todas las incidencias.

**Resultado esperado:** `clasificador-incidencias-v1.json: OK` en el paso 2, y `FAILED` con el aviso `1 computed checksum did NOT match` en el paso 4.

**Diferencias entre verificar un paquete y verificar un modelo:**

| | Paquete de software | Artefacto de modelo |
|---|---|---|
| Qué contiene | Código que se lee y se revisa | Números (pesos) que no se pueden revisar a simple vista |
| Cómo se nota una manipulación | En el código, revisando los cambios | En el comportamiento, a veces solo en casos concretos |
| Tamaño habitual | De kilobytes a pocos megabytes | De megabytes a varios gigabytes |
| Riesgo al cargarlo | Ejecuta código al importarlo | Algunos formatos (por ejemplo, los basados en `pickle`) ejecutan código al cargarse; otros, como `safetensors`, solo contienen datos |

Por eso el hash se comprueba **antes** de cargar el modelo, no después.

**Lo que el hash no garantiza:** el hash demuestra que el archivo es idéntico al de referencia. No demuestra que el modelo sea seguro, que no tenga sesgos ni que el proveedor sea fiable. Y solo sirve si el valor de referencia viene de una fuente de confianza: si un atacante puede cambiar a la vez el modelo y el archivo `SHA256SUMS`, la comprobación pasará.

**Conclusión:** los modelos se tratan como cualquier otra dependencia: versión concreta, origen conocido y hash comprobado antes de usarlos.

**Pequeño ejercicio:** simula un atacante que, además de modificar el modelo, regenera `SHA256SUMS` con `sha256sum clasificador-incidencias-v1.json > SHA256SUMS`. ¿Qué dice ahora `sha256sum -c SHA256SUMS`? ¿Cómo detectarías la manipulación?

---

## Limpieza

```bash
rm -rf artifacts/descargas artifacts/modelos artifacts/versiones-corregidas.txt artifacts/requirements-instalados.txt artifacts/sbom-*.cdx.json
```

Para liberar espacio también puedes borrar la base de datos de Trivy: `docker volume rm trivy-cache`.

## Archivos de esta carpeta

| Archivo | Uso |
|---|---|
| `dependencias/versiones-antiguas.txt` | Versiones antiguas con vulnerabilidades publicadas (ejemplos 1 y 2). Solo se analiza |
| `descargas/utilidades_texto-1.0.0.py` y `descargas/SHA256SUMS` | Paquete ficticio y su hash (ejemplo 3) |
| `modelos/clasificador-incidencias-v1.json` y `modelos/SHA256SUMS` | Modelo ficticio y su hash (ejemplo 4) |
| `.gitattributes` | Evita que Git cambie los finales de línea de los archivos con hash; si los cambiara, la comprobación fallaría |
