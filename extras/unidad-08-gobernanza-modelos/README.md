# Unidad 8 · Gobernanza, protección y ciclo de vida de modelos de IA

Cuatro ejemplos cortos sobre un mismo proceso. Un modelo de IA no debería usarse sin saber qué modelo es, de dónde procede, qué versión es, quién responde de él, qué comprobaciones ha superado y si alguien ha decidido aprobarlo. Y la organización debe poder detectar un cambio no autorizado y retirar una versión problemática.

```
Modelo recibido → Registro → Versionado → Validación → Aprobación → Seguimiento → Retirada
```

| N.º | Ejemplo | Herramientas |
|---|---|---|
| 1 | Registrar un modelo de IA | `cat`, `jq`, `sha256sum` |
| 2 | Versionar y controlar cambios | `git diff`, `sha256sum` |
| 3 | Validar un modelo antes de aprobarlo | `validar_modelo.py` |
| 4 | Aprobar, rechazar y retirar modelos | `cambiar_estado.py`, `jq` |

Todo se demuestra con unos pocos archivos JSON y dos scripts cortos de Python estándar. Es la idea que hay detrás de las plataformas de registro de modelos, sin instalar ninguna.

## Preparación

Los comandos están pensados para **WSL / Linux** y se ejecutan desde la **carpeta raíz del laboratorio** (donde está `compose.yaml`). Se necesitan `jq` (`sudo apt install jq`, como en la Unidad 6) y Python 3 (`python3 --version`; Ubuntu lo incluye). No hace falta Docker ni Internet.

Se trabaja sobre una copia en `artifacts/`, excluida de Git. Los archivos originales no se modifican:

```bash
mkdir -p artifacts
cp -r extras/unidad-08-gobernanza-modelos artifacts/gobernanza
cd artifacts/gobernanza
```

**Todos los comandos y los dos scripts se ejecutan desde `artifacts/gobernanza`**, la carpeta que contiene `registro-modelos.json`: los scripts buscan el registro, el historial y los modelos en el directorio actual. Si `pwd` no termina en `artifacts/gobernanza`, vuelve a ella antes de seguir. Para empezar de cero en cualquier momento:

```bash
cd ../.. && rm -rf artifacts/gobernanza && cp -r extras/unidad-08-gobernanza-modelos artifacts/gobernanza && cd artifacts/gobernanza
```

Archivos de la carpeta:

| Archivo | Contenido |
|---|---|
| `modelos/clasificador-incidencias-v1.0.0.json` | Modelo ficticio de la Unidad 6 (el mismo archivo, con el mismo hash) |
| `modelos/clasificador-incidencias-v1.1.0.json` | Nueva versión del modelo |
| `registro-modelos.json` | Registro de modelos: una entrada por versión |
| `historial-estados.jsonl` | Historial de decisiones: una línea JSON por cambio de estado |
| `validar_modelo.py` | Validación técnica de una versión (ejemplo 3) |
| `cambiar_estado.py` | Registro de una decisión de estado (ejemplo 4) |

El modelo es **ficticio**: un archivo JSON con unos pesos y un umbral que deciden si una incidencia de soporte es urgente. Los responsables (`equipo-plataforma-ia`, `comite-modelos`) son roles inventados.

---

## Ejemplo 1. Registrar un modelo de IA

**Objetivo:** identificar un modelo de forma inequívoca antes de usarlo.

**Situación inicial:** en la Unidad 6 comprobamos la integridad de `clasificador-incidencias-v1.json`. Sabemos que el archivo no ha cambiado, pero el archivo no dice quién responde de él, para qué se puede usar ni si alguien ha autorizado su uso.

**Explicación:** un **registro de modelos** es un inventario con una entrada por versión. Cada entrada responde a las preguntas que haría un auditor: qué es (`id`, `nombre`, `version`, `descripcion`), de dónde viene (`origen`), quién responde (`responsable`), dónde está y cómo se comprueba (`artefacto`, `sha256`), para qué se usa (`uso_previsto`) y en qué situación está (`estado`, `fecha_registro`).

**Pasos:**

```bash
# 1. Ver el registro completo
cat registro-modelos.json

# 2. Una entrada concreta
jq '.modelos[] | select(.version == "1.0.0")' registro-modelos.json

# 3. Resumen: identificador, estado y responsable
jq -r '.modelos[] | [.id, .estado, .responsable] | @tsv' registro-modelos.json

# 4. Comprobar que el artefacto es el registrado
jq -r '.modelos[] | select(.version == "1.0.0") | .sha256' registro-modelos.json
sha256sum modelos/clasificador-incidencias-v1.0.0.json
```

**Resultado esperado** (paso 3 y paso 4):

```
clasificador-incidencias@1.0.0	aprobado	equipo-plataforma-ia
clasificador-incidencias@1.1.0	registrado	equipo-plataforma-ia

e6b4ab0f6f5fb20216e3f3377d975840d1b9e6bdcacae52ea3d84398eb709b94
e6b4ab0f6f5fb20216e3f3377d975840d1b9e6bdcacae52ea3d84398eb709b94  modelos/clasificador-incidencias-v1.0.0.json
```

**Interpretación:** los dos hashes coinciden: el archivo es el que se registró. Es el mismo valor que en la Unidad 6, porque es el mismo artefacto. La versión 1.0.0 está aprobada; la 1.1.0 está registrada, pero nadie ha decidido todavía que pueda usarse.

**Conclusión:** el registro convierte un archivo en un activo identificado: versión, origen, responsable, uso previsto y huella de integridad en un único lugar.

**Pequeño ejercicio:** registra una versión ficticia `1.2.0`. Crea su artefacto copiando el de la 1.1.0 y cambiando solo su campo `version`. Añade su entrada al registro modificando únicamente los metadatos necesarios. ¿Qué campos has tenido que cambiar y cuáles se mantienen?

---

## Ejemplo 2. Versionar y controlar cambios en un modelo

**Objetivo:** identificar cada versión de un modelo y saber qué cambia entre ellas.

**Situación inicial:** el proveedor entrega la versión 1.1.0 del clasificador. Queremos conservar la 1.0.0, que está en uso, y saber exactamente qué ha cambiado.

**Explicación:** cada versión es un archivo distinto, con su propio nombre y su propio hash. Nunca se reemplaza un archivo por otro con el mismo nombre: se perdería la versión anterior y el hash registrado dejaría de coincidir.

**Pasos:**

```bash
# 1. Un archivo por versión
ls modelos

# 2. Qué ha cambiado entre las dos versiones
git diff --no-index modelos/clasificador-incidencias-v1.0.0.json modelos/clasificador-incidencias-v1.1.0.json

# 3. Comprobar a la vez la integridad de todas las versiones registradas
jq -r '.modelos[] | "\(.sha256)  \(.artefacto)"' registro-modelos.json | sha256sum -c -

# 4. Simular un error: sobrescribir la versión 1.0.0 con la nueva
cp modelos/clasificador-incidencias-v1.1.0.json modelos/clasificador-incidencias-v1.0.0.json
jq -r '.modelos[] | "\(.sha256)  \(.artefacto)"' registro-modelos.json | sha256sum -c -

# 5. Recuperar la versión original desde el repositorio
cp ../../extras/unidad-08-gobernanza-modelos/modelos/clasificador-incidencias-v1.0.0.json modelos/
jq -r '.modelos[] | "\(.sha256)  \(.artefacto)"' registro-modelos.json | sha256sum -c -
```

`git diff --no-index` compara dos archivos aunque no estén en un repositorio. En el paso 3, `jq` genera la lista de hashes esperados a partir del registro y `sha256sum -c -` la comprueba.

**Resultado esperado:**

Paso 2: solo cambian dos líneas.

```
-  "version": "1.0.0",
+  "version": "1.1.0",
...
-  "umbral_urgente": 0.50,
+  "umbral_urgente": 0.40,
```

Pasos 3 y 5:

```
modelos/clasificador-incidencias-v1.0.0.json: OK
modelos/clasificador-incidencias-v1.1.0.json: OK
```

Paso 4:

```
modelos/clasificador-incidencias-v1.0.0.json: FAILED
modelos/clasificador-incidencias-v1.1.0.json: OK
sha256sum: WARNING: 1 computed checksum did NOT match
```

**Interpretación:** la versión 1.1.0 baja el umbral a partir del cual una incidencia se considera urgente. El código de la aplicación no cambia, pero su comportamiento sí. No sabemos si es una mejora: eso solo lo diría una evaluación con datos representativos. Lo que sí sabemos es qué ha cambiado y en qué archivo. Al sobrescribir la 1.0.0, el registro detecta que el archivo ya no es el aprobado. Si no tuviéramos el original en Git, no podríamos volver a la versión en uso.

**Conclusión:** versiones en archivos separados, un hash por versión y el historial de Git permiten saber qué cambió, cuándo, y volver atrás.

**Pequeño ejercicio:** identifica qué parámetro del modelo cambia entre la 1.0.0 y la 1.1.0 (sin contar `version`) y explica en dos o tres frases por qué ese cambio debería quedar registrado aunque no se haya tocado el código.

---

## Ejemplo 3. Validar un modelo antes de aprobarlo

**Objetivo:** comprobar que una versión cumple unas condiciones mínimas antes de autorizar su uso.

**Situación inicial:** la versión 1.1.0 está registrada, pero todavía no está aprobada. Antes de decidir nada hay que comprobarla.

**Explicación:** `validar_modelo.py` (unas 50 líneas, solo biblioteca estándar) busca la versión en el registro y comprueba:

| Tipo | Comprobación |
|---|---|
| Integridad | El archivo existe y su SHA-256 coincide con el registro |
| Estructura | Es JSON válido, tiene los campos obligatorios y su `version` coincide con el registro |
| Tipos | `umbral_urgente`, `sesgo` y los pesos son números, no texto |
| Rangos | `umbral_urgente` entre 0 y 1; un peso por entrada y cada peso entre -5 y 5 |

Termina con código de salida **0** si todo es correcto y **1** si algo falla, por lo que puede usarse en un pipeline como los de la Unidad 7.

Conviene separar tres cosas que se confunden a menudo:

| Qué | Pregunta que responde | En este ejemplo |
|---|---|---|
| Validación técnica | ¿Es el archivo registrado y tiene la forma esperada? | Sí: `validar_modelo.py` |
| Evaluación funcional | ¿Cómo se comporta con datos representativos (aciertos, errores, sesgos)? | No |
| Aprobación | ¿Decide la organización que puede usarse para el uso previsto? | No: es una decisión de una persona (ejemplo 4) |

Superar la validación técnica no demuestra que el modelo sea preciso, justo, seguro ni adecuado para producción, y no equivale a una aprobación. Demuestra que es el archivo esperado y que tiene una forma correcta.

**Pasos:**

```bash
# 1. Validar la versión pendiente
python3 validar_modelo.py 1.1.0
echo "Código de salida: $?"

# 2. Una versión que no está en el registro
python3 validar_modelo.py 2.0.0
echo "Código de salida: $?"

# 3. Simular un dato incorrecto: umbral fuera de rango
sed -i 's/"umbral_urgente": 0.40/"umbral_urgente": 1.40/' modelos/clasificador-incidencias-v1.1.0.json
python3 validar_modelo.py 1.1.0
echo "Código de salida: $?"

# 4. Restaurar el archivo
cp ../../extras/unidad-08-gobernanza-modelos/modelos/clasificador-incidencias-v1.1.0.json modelos/
```

**Resultado esperado:**

```
Versión 1.1.0: supera la validación técnica
Código de salida: 0

FALLO la versión 2.0.0 no está en el registro
Versión 2.0.0: NO SUPERA la validación técnica
Código de salida: 1

FALLO integridad: el hash SHA-256 no coincide con el registro
FALLO rango: umbral_urgente=1.4 fuera de [0, 1]
Versión 1.1.0: NO SUPERA la validación técnica
Código de salida: 1
```

**Interpretación:** el cambio del paso 3 lo detectan dos comprobaciones distintas. El hash detecta que el archivo no es el registrado; el rango detecta que el valor no tiene sentido. Son complementarias: un proveedor podría entregar un archivo con un valor absurdo y su hash correcto, y un atacante podría cambiar un valor dentro del rango.

**Conclusión:** antes de aprobar un modelo se comprueba automáticamente que es el archivo registrado y que su contenido tiene la forma esperada. Es una condición necesaria, no suficiente.

**Pequeño ejercicio:** cambia un parámetro del modelo 1.1.0 (por ejemplo, `umbral_urgente` a `0.95`, como el atacante de la Unidad 6) y vuelve a validarlo. ¿Qué comprobaciones fallan y cuáles no? ¿Qué pasaría si la validación no comprobara el hash? Restaura el archivo al terminar.

---

## Ejemplo 4. Aprobar, rechazar y retirar modelos

**Objetivo:** controlar qué versiones pueden usarse en cada momento y dejar constancia de cada decisión.

**Situación inicial:** la versión 1.0.0 está aprobada y en uso. La 1.1.0 está registrada y pendiente.

**Explicación:** cada versión tiene un estado:

| Estado | Significado | Puede usarse |
|---|---|---|
| `registrado` | Se conoce el modelo, su origen, su responsable y su hash | No |
| `en_revision` | Se están haciendo las comprobaciones técnicas y la evaluación | No |
| `aprobado` | Una persona responsable ha decidido que puede usarse para el uso previsto | Sí |
| `retirado` | No puede usarse: se ha rechazado en la revisión o se ha detectado un problema | No |

Los cambios permitidos son: `registrado → en_revision → aprobado → retirado`, y `en_revision → retirado` cuando la revisión rechaza la versión. Un modelo retirado no vuelve a aprobarse: si se corrige, se registra una versión nueva.

**Rechazo:** para no añadir más estados, una versión rechazada en la revisión pasa a `retirado` y el motivo lo dice expresamente (por ejemplo, «Rechazada en revisión: el hash no coincide»). Es una simplificación didáctica: en un sistema real conviene distinguir `rechazado` (nunca llegó a usarse) de `retirado` (se usó y se dejó de usar), porque las consecuencias son distintas; una retirada obliga, por ejemplo, a revisar las decisiones tomadas mientras estuvo en uso.

`cambiar_estado.py` registra una decisión: cambia el estado en el registro y añade una línea al historial con la versión, el estado anterior, el nuevo, el motivo, la fecha y el responsable. Para aprobar, exige que la versión supere la validación técnica, pero **la aprobación no es automática**: alguien tiene que pedirla, con un motivo y su nombre. Superar las pruebas es un requisito para aprobar, no una aprobación.

**Pasos:**

```bash
# 1. Estado actual
jq -r '.modelos[] | "\(.version)  \(.estado)"' registro-modelos.json

# 2. Intentar aprobar sin revisión
python3 cambiar_estado.py 1.1.0 aprobado "Atajo sin revisión" equipo-plataforma-ia

# 3. Pasar a revisión y comprobar
python3 cambiar_estado.py 1.1.0 en_revision "Solicitud de uso en la cola de soporte" equipo-plataforma-ia
python3 validar_modelo.py 1.1.0

# 4. Decisión de aprobación
python3 cambiar_estado.py 1.1.0 aprobado "Validación técnica superada y uso aceptado por el área de soporte" comite-modelos

# 5. Problema detectado en el seguimiento: retirada
python3 cambiar_estado.py 1.1.0 retirado "Problema simulado: demasiadas incidencias normales marcadas como urgentes" comite-modelos

# 6. Qué versión sigue disponible
jq -r '.modelos[] | select(.estado == "aprobado") | .id' registro-modelos.json

# 7. Trazabilidad de la versión 1.1.0
jq -c 'select(.id == "clasificador-incidencias@1.1.0")' historial-estados.jsonl
```

**Resultado esperado:**

```
1.0.0  aprobado
1.1.0  registrado

RECHAZADO: de 'registrado' no se puede pasar a 'aprobado'

clasificador-incidencias@1.1.0: registrado -> en_revision
Versión 1.1.0: supera la validación técnica

clasificador-incidencias@1.1.0: en_revision -> aprobado

clasificador-incidencias@1.1.0: aprobado -> retirado

clasificador-incidencias@1.0.0
```

El paso 7 muestra cuatro líneas: el registro inicial y las tres decisiones, cada una con su motivo y su responsable. **Fechas:** las líneas que ya traía el historial tienen fechas ficticias fijas (noviembre de 2026); las que añade `cambiar_estado.py` llevan la fecha del momento de ejecución, tomada del reloj de tu equipo. Por eso tus fechas no coincidirán con las de esta guía.

**Interpretación:** el paso 2 se rechaza porque una versión no se aprueba sin pasar por revisión. Después de la retirada, la única versión aprobada es la 1.0.0: es la que puede seguir usándose. Ojo: el registro dice qué versión *puede* usarse, pero la API del laboratorio todavía no lo consulta, así que nada impide técnicamente cargar la 1.1.0. El historial explica por qué la 1.1.0 llegó a aprobarse y por qué se retiró. Con `cd ../.. && git diff --no-index extras/unidad-08-gobernanza-modelos/registro-modelos.json artifacts/gobernanza/registro-modelos.json` se ve que el registro solo ha cambiado en el campo `estado`.

**Conclusión:** el estado indica qué versiones pueden usarse; el historial explica quién decidió cada cambio y por qué. En un proyecto real, el registro y el historial se guardan en Git y cada cambio pasa por una Pull Request revisada, con lo que la decisión queda también firmada por su autor.

**Pequeño ejercicio:** simula la retirada de la versión 1.0.0 por un problema detectado en el seguimiento. Comprueba que el historial recoge la decisión y su motivo, y consulta qué versiones quedan aprobadas. ¿Qué debería hacer la aplicación si no queda ninguna?

---

## Lo que estos ejemplos no cubren

- **Aplicación automática de los estados:** la API FastAPI del laboratorio no consulta este registro. Que una versión esté `retirado` no impide hoy que alguien la cargue; el registro documenta y controla la decisión, pero hacerla cumplir exige que la aplicación (o el pipeline de despliegue) compruebe el estado y el hash antes de usar un modelo.
- **Aprobación empresarial:** los scripts registran quién decide y por qué, pero no sustituyen el proceso de la organización (revisión por otras personas, criterios de negocio, legales y de riesgo).

- **Evaluación funcional:** medir aciertos, errores y sesgos con datos representativos. Es lo que justificaría que una versión es mejor que otra.
- **Firmas digitales:** el hash comprueba que el archivo coincide con el registro, pero no quién lo publicó. Herramientas como Sigstore permiten firmar artefactos y verificar su autor.
- **Plataformas de registro de modelos:** gestionan lo mismo que estos archivos (versiones, estados, responsables, trazabilidad) a gran escala.

Un hash demuestra que el archivo coincide con el valor esperado. No demuestra que el modelo sea seguro ni que su proveedor sea legítimo. Y solo protege si el registro está en un lugar de confianza: quien pueda modificar a la vez el modelo y el registro podrá hacer pasar cualquier archivo.

## Limpieza

```bash
cd ../..
rm -rf artifacts/gobernanza
```
