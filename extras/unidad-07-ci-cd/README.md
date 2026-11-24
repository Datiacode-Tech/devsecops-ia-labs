# Unidad 7 · Automatización de seguridad en CI/CD con GitHub Actions

Hasta ahora, las pruebas, Gitleaks y Trivy se ejecutaban a mano. En esta unidad se ejecutan **solos cada vez que alguien propone un cambio**. Si una comprobación falla, el cambio se marca en rojo antes de integrarse en `main`.

| N.º | Ejemplo | Workflow | Qué automatiza |
|---|---|---|---|
| 1 | Primer pipeline CI | `workflows/01-pruebas.yml` | Pruebas con pytest |
| 2 | Detectar secretos | `workflows/02-secretos.yml` | Gitleaks (Unidad 4) |
| 3 | Analizar dependencias | `workflows/03-dependencias.yml` | Trivy (Unidad 6) |
| 4 | Pipeline DevSecOps completo | `workflows/04-devsecops.yml` | Los tres controles juntos |

## Antes de empezar: dónde se ejecutan los workflows

GitHub Actions **solo** ejecuta los archivos que están en la carpeta `.github/workflows/` de un repositorio de GitHub. Los de `extras/unidad-07-ci-cd/workflows/` no se ejecutan nunca: son el material de los ejemplos. Para probarlos:

1. Crea un repositorio **tuyo** en GitHub, por ejemplo `devsecops-ia-u07`. No uses el repositorio del curso. Un repositorio privado basta para los ejemplos 1 a 3; para probar la protección de ramas del ejemplo 4, GitHub exige que el repositorio sea público o una cuenta de pago (el laboratorio solo contiene datos ficticios).
2. Sube a él tu copia del laboratorio.
3. Copia en `.github/workflows/` **solo** el workflow del ejemplo que vas a probar.

```bash
# Desde la carpeta raíz del laboratorio (la copia descargada con git clone)
git switch -c main                                   # la copia del curso no está en ninguna rama
git remote add mio git@github.com:TU_USUARIO/devsecops-ia-u07.git
git push -u mio main
```

GitHub da minutos gratuitos de Actions cada mes en las cuentas personales. Los cuatro workflows tardan pocos minutos, pero no dejes activos workflows que no uses.

**Conceptos básicos** (todos aparecen en el ejemplo 1):

| Concepto | Qué es | En el YAML |
|---|---|---|
| Workflow | Proceso automático definido en un archivo YAML | El archivo completo |
| Evento | Lo que lo pone en marcha | `on:` |
| Job | Conjunto de pasos que se ejecutan en una máquina virtual nueva | `jobs:` |
| Step | Un paso: una acción ya hecha (`uses:`) o un comando (`run:`) | `steps:` |
| Runner | Máquina virtual de GitHub que ejecuta el job | `runs-on: ubuntu-24.04` |

---

## Ejemplo 1. Crear nuestro primer pipeline CI

**Objetivo:** que las pruebas se ejecuten solas en cada cambio propuesto.

**Situación inicial:** las pruebas existen, pero solo se ejecutan si alguien se acuerda de lanzarlas. Un cambio puede llegar a `main` con pruebas rotas.

**El workflow** (`workflows/01-pruebas.yml`):

```yaml
name: "U7 · 1 · Pruebas"

on:
  push:
    branches: [main]        # al integrar cambios en main
  pull_request:             # al abrir o actualizar una Pull Request
  workflow_dispatch:        # a mano, desde la pestaña Actions

permissions:
  contents: read            # el token del workflow solo puede leer el código

jobs:
  pruebas:
    name: Pruebas con pytest
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - name: Descargar el código
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Preparar Python 3.12
        uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.12"

      - name: Instalar las dependencias
        run: python -m pip install -r requirements.txt

      - name: Ejecutar las pruebas
        run: python -m pytest -q -p no:cacheprovider -rs tests
```

**Explicación:**

- `on:` define los eventos. Con `push` solo en `main` y `pull_request` en cualquier rama, cada cambio se comprueba una vez en su Pull Request y otra al integrarse.
- `actions/checkout` descarga el código en el runner. `persist-credentials: false` evita que el token quede guardado en la copia.
- `actions/setup-python` instala Python 3.12.
- Los dos `run:` son los mismos comandos que escribirías en una terminal.
- Las acciones se fijan con el **commit completo** (el comentario indica la versión). Una etiqueta como `v7` puede moverse a otro código; un commit, no.
- `permissions: contents: read` da al workflow el mínimo permiso necesario.

**Pasos:**

```bash
mkdir -p .github/workflows
cp extras/unidad-07-ci-cd/workflows/01-pruebas.yml .github/workflows/
git add .github/workflows/01-pruebas.yml
git commit -m "CI: pruebas automáticas"
git push
```

En GitHub: pestaña **Actions** › workflow **U7 · 1 · Pruebas** › la ejecución › job **Pruebas con pytest**. Cada step se puede desplegar para ver su log.

**Resultado esperado:** marca verde y, en el step «Ejecutar las pruebas», `48 passed, 11 skipped`.

**Interpretación:** las 11 pruebas omitidas (`SKIPPED … solo tiene sentido dentro de un contenedor Docker` o `… requiere la red interna de Docker`) comprueban el endurecimiento de los contenedores y la red interna de la Unidad 5. En el runner no hay contenedores del laboratorio, así que se omiten a propósito. La batería completa (59) se ejecuta en local con Docker Compose, como en las unidades anteriores.

**Conclusión:** con un archivo de 30 líneas, ningún cambio llega a `main` sin pasar las pruebas.

**Errores habituales:**

- Dejar el workflow fuera de `.github/workflows/`: GitHub no lo ve.
- Sangría incorrecta en el YAML: el workflow no arranca y GitHub muestra el error en la pestaña Actions.
- Confundir «omitida» con «fallida»: una prueba omitida no cuenta como error.

**Pequeño ejercicio:** introduce de forma controlada una prueba que falle, comprueba cómo lo muestra GitHub Actions y deja el proyecto como estaba.

---

## Ejemplo 2. Detectar secretos automáticamente

**Objetivo:** que Gitleaks revise cada cambio en busca de credenciales.

**Situación inicial:** en la Unidad 4 ejecutabas Gitleaks a mano. Si alguien olvida hacerlo, una clave puede llegar al repositorio, y una vez subida queda en el historial aunque se borre después.

**El workflow** (`workflows/02-secretos.yml`, lo esencial):

```yaml
env:
  GITLEAKS: ghcr.io/gitleaks/gitleaks:v8.28.0@sha256:cdbb7c955abce02001a9f6c9f602fb195b7fadc1e812065883f695d1eeaba854

jobs:
  secretos:
    name: Secretos con Gitleaks
    runs-on: ubuntu-24.04
    steps:
      - name: Descargar el código con todo el historial
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Buscar secretos en todo el historial
        run: docker run --rm -v "$PWD:/repo:ro" "$GITLEAKS" git /repo --redact --no-banner -v
```

**Explicación:**

- `fetch-depth: 0` descarga todo el historial **de todas las ramas** del repositorio. Sin él, Gitleaks solo vería el último commit. Por eso, un secreto en cualquier rama hace fallar el análisis en todas, hasta que se elimine del historial de esa rama o se borre la rama.
- Se usa la **misma imagen de Gitleaks de la Unidad 4**, fijada por versión y por digest, ejecutada con Docker (los runners de GitHub lo traen instalado). El código se monta en solo lectura (`:ro`).
- `gitleaks git` analiza todos los commits; `--redact` oculta el valor del secreto en el log.
- Si encuentra un secreto, Gitleaks termina con código 1 y **el job falla**.
- Se usa la herramienta de línea de comandos y no la acción `gitleaks-action` porque esta exige una licencia en los repositorios de organizaciones y pide permisos de escritura para comentar en las Pull Requests.

**Pasos:** igual que en el ejemplo 1, copiando `02-secretos.yml`.

**Resultado esperado:** marca verde y, en el log, `commits scanned` y `no leaks found`.

**Si encuentra un secreto:** el log muestra la regla, el archivo, la línea y el commit, nunca el valor:

```
RuleID:      generic-api-key
File:        config-prueba.env
Line:        2
Commit:      30975cc…
WRN leaks found: 1
```

Qué hacer:

1. Considerar la credencial comprometida y **rotarla** en el servicio al que da acceso (Unidad 4).
2. Quitarla del código y del historial.
3. Si es un falso positivo, documentarlo (por ejemplo, con un comentario `gitleaks:allow` en esa línea).

**Por qué nunca se suben credenciales reales**, ni siquiera a una rama de prueba: en cuanto llegan a GitHub, cualquiera con acceso al repositorio (o todo el mundo, si es público) puede copiarlas, y borrar el archivo después no las quita del historial.

**Conclusión:** la detección de secretos deja de depender de la memoria de cada persona: cada cambio se revisa.

**Errores habituales:**

- Olvidar `fetch-depth: 0`: solo se analiza el último commit.
- Probar el pipeline subiendo una clave real «para ver si la detecta».
- Ignorar el aviso porque «es solo una rama»: la rama ya está en GitHub, y además hace fallar el análisis de las demás.
- Borrar el archivo en un commit nuevo y esperar que el análisis pase: el secreto sigue en el historial y el job sigue fallando.

**Pequeño ejercicio:** comprueba que el análisis detecta una credencial ficticia controlada y que, después de eliminarla, vuelve a pasar. Hazlo en tu equipo, sin subir nada a GitHub.

---

## Ejemplo 3. Analizar dependencias con Trivy

**Objetivo:** automatizar el análisis de vulnerabilidades de las dependencias Python de la Unidad 6.

**Situación inicial:** en la Unidad 6 analizaste las dependencias a mano. Cada día se publican vulnerabilidades nuevas: una dependencia limpia hoy puede no estarlo dentro de un mes.

**El workflow** (`workflows/03-dependencias.yml`). Empieza igual que el del ejemplo 1 (descargar el código, preparar Python 3.12 e instalar las dependencias), define la imagen de Trivy en `env:` y añade dos steps:

```yaml
env:
  TRIVY: aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
```

```yaml
      - name: Inventario con versiones exactas
        run: |
          mkdir -p artifacts
          python -m pip freeze > artifacts/requirements-instalados.txt
          cat artifacts/requirements-instalados.txt

      - name: Analizar vulnerabilidades HIGH y CRITICAL
        run: >-
          docker run --rm
          -v "$PWD/artifacts/requirements-instalados.txt:/src/requirements.txt:ro"
          "$TRIVY" fs --quiet --scanners vuln --severity HIGH,CRITICAL --exit-code 1 /src
```

**Explicación:**

- `pip freeze` crea el inventario con las versiones **realmente instaladas** en el runner, incluidas las dependencias transitivas.
- Se analiza ese inventario, no `requirements.txt`. Como viste en la Unidad 6, sobre rangos (`fastapi>=0.115,<1.0`) Trivy no analiza nada. En un pipeline es todavía más peligroso: **el job terminaría en verde sin haber comprobado nada**.
- `--severity HIGH,CRITICAL` limita el análisis a las vulnerabilidades graves.
- `--exit-code 1` es lo que convierte un hallazgo en un fallo del job. Sin esa opción, Trivy informaría de las vulnerabilidades, pero el job terminaría en verde.
- Se usa la misma versión de Trivy de las unidades 5 y 6, fijada por digest.

**Pasos:** igual que en el ejemplo 1, copiando `03-dependencias.yml`.

**Resultado esperado:** marca verde. En el log, el inventario (unas 22 bibliotecas) y la tabla de Trivy con `requirements.txt │ pip │ 0`.

**Interpretación:** las versiones exactas pueden cambiar de una ejecución a otra, porque `pip` instala la versión más reciente que permiten los rangos. Por eso el inventario se genera en cada ejecución y aparece en el log. Si un día Trivy encuentra una vulnerabilidad grave, el job fallará aunque nadie haya tocado el código: es una vulnerabilidad nueva en una dependencia.

**Conclusión:** el análisis de dependencias se repite solo en cada cambio y avisa en cuanto aparece una vulnerabilidad grave.

**Errores habituales:**

- Analizar `requirements.txt` con rangos: no detecta nada y el job pasa.
- Olvidar `--exit-code 1`: los hallazgos aparecen en el log, pero el job sigue en verde.
- Añadir las versiones del archivo de demostración de la Unidad 6 a `requirements.txt` para «probar» el pipeline: se instalarían en la aplicación.

**Pequeño ejercicio:** ejecuta en tu equipo el mismo análisis que hace el pipeline sobre el archivo de demostración de la Unidad 6 (`extras/unidad-06-cadena-suministro/dependencias/versiones-antiguas.txt`) y comprueba qué código de salida devuelve. ¿Qué haría GitHub Actions con ese resultado?

---

## Ejemplo 4. Crear un pipeline DevSecOps completo

**Objetivo:** reunir los tres controles en un solo workflow e interpretar su resultado.

**Situación inicial:** tres workflows separados funcionan, pero lo habitual es un único workflow con un job por control.

**El workflow** (`workflows/04-devsecops.yml`) tiene tres jobs, `pruebas`, `secretos` y `dependencias`, con los mismos pasos de los ejemplos 1 a 3. Los tres se ejecutan **en paralelo** y de forma independiente.

**Pasos:**

```bash
git rm .github/workflows/0[1-3]-*.yml               # evita ejecutar dos veces cada control
cp extras/unidad-07-ci-cd/workflows/04-devsecops.yml .github/workflows/
git add .github/workflows/
git commit -m "CI: pipeline DevSecOps"
git push
```

Si no habías copiado los workflows anteriores, omite el `git rm`.

**Resultado esperado:** en la ejecución de **U7 · 4 · DevSecOps**, tres jobs en verde: **Pruebas con pytest**, **Secretos con Gitleaks** y **Dependencias con Trivy**.

**Interpretación:**

- **Job correcto (verde):** todos sus steps terminaron con código 0.
- **Job fallido (rojo):** un step terminó con un código distinto de 0. Los steps siguientes de ese job no se ejecutan; los otros jobs siguen, porque son independientes.
- **Workflow:** solo está en verde si **todos** sus jobs lo están. Un único control fallido pone el workflow en rojo.
- **Logs:** en la página de la ejecución, cada job aparece a la izquierda; al pulsarlo se ven sus steps y, al desplegar un step, su salida. El step que falló aparece marcado con una cruz.
- **Pull Requests:** el resultado de cada job aparece en la Pull Request como una comprobación. Con la **protección de ramas** (Settings › Branches) se pueden exigir esos jobs para poder integrar en `main`: con uno en rojo, GitHub no permite fusionar. En los repositorios privados de cuentas y organizaciones gratuitas, GitHub no permite crear reglas de protección; las comprobaciones se ven igualmente en la Pull Request.

**Por qué no se ignoran los errores de seguridad:** un pipeline que falla «siempre» acaba ignorándose, y entonces deja de proteger. Si un hallazgo es un falso positivo, se documenta y se excluye de forma explícita; si es real, se corrige. Nunca se desactiva el control para que el workflow salga en verde.

**Conclusión:** el pipeline aplica en cada cambio las tres comprobaciones de las unidades anteriores, y la protección de ramas impide integrar código que no las supera.

**Errores habituales:**

- Dejar activos los workflows 1 a 3 junto al 4: cada control se ejecuta dos veces y cada comprobación aparece repetida en la Pull Request.
- Interpretar un workflow en rojo como «todo está mal»: hay que abrir el job que falló.
- Desactivar o borrar un job para poder fusionar una Pull Request.

**Pequeño ejercicio:** provoca un fallo controlado en una rama, abre una Pull Request, identifica qué comprobación lo detecta, corrígelo y comprueba que el pipeline vuelve a pasar.

---

## Seguridad de los propios workflows

- **Permisos mínimos:** `permissions: contents: read`. Ninguno de los workflows necesita escribir en el repositorio.
- **Acciones fijadas** a un commit completo; herramientas (Gitleaks y Trivy) fijadas por versión y por digest.
- **Sin secretos:** los workflows no usan ningún secreto. Si algún día lo necesitas, se guarda en Settings › Secrets y nunca se imprime en el log.
- **Sin `pull_request_target`:** ese evento ejecuta el workflow con permisos del repositorio de destino, peligroso con código de una Pull Request no revisada. Se usa `pull_request`.
- **Sin scripts descargados** con `curl … | sh` y sin despliegues ni publicación de artefactos.
- `timeout-minutes` evita que un job bloqueado consuma minutos indefinidamente.

## Archivos de esta carpeta

| Archivo | Uso |
|---|---|
| `workflows/01-pruebas.yml` | Ejemplo 1: pruebas con pytest |
| `workflows/02-secretos.yml` | Ejemplo 2: Gitleaks sobre todo el historial |
| `workflows/03-dependencias.yml` | Ejemplo 3: inventario con `pip freeze` y Trivy |
| `workflows/04-devsecops.yml` | Ejemplo 4: los tres controles como jobs paralelos |
