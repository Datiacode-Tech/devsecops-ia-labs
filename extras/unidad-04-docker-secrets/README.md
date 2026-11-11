# Ejemplo 4 · Docker Compose Secrets frente a variables de entorno

Ejemplo práctico de la Unidad 4, **independiente del laboratorio principal**: no usa `.env` ni modifica la API, el `compose.yaml` ni los Dockerfiles del laboratorio. Arranca una API FastAPI mínima con la misma idea de autenticación (cabecera `x-api-key`, comparación en tiempo constante, `401` único) que lee su clave de un **secreto de Docker Compose** montado en `/run/secrets/demo_api_key`.

| Servicio | Puerto | Origen de la clave |
|---|---|---|
| `api-secreto` | `127.0.0.1:8007` | Fichero montado en `/run/secrets/demo_api_key` (opción B) |
| `api-entorno` (perfil `comparar`) | `127.0.0.1:8008` | Variable de entorno `DEMO_API_KEY` (opción A, solo para comparar) |

Proyecto Docker Compose: `devsecops-ia-u04-secretos`. No interfiere con los servicios del laboratorio principal.

## 1. Generar el secreto sin mostrarlo

WSL / Linux:

```bash
mkdir -p secrets
( umask 077
  CLAVE=$(docker run --rm python:3.12.16-slim python -c "import secrets; print(secrets.token_urlsafe(24), end='')")
  printf '%s' "$CLAVE" > secrets/demo_api_key.txt
  printf 'DEMO_API_KEY=%s\n' "$CLAVE" > secrets/demo.env )
chmod 600 secrets/demo_api_key.txt secrets/demo.env
ls -l secrets
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force secrets | Out-Null
$clave = docker run --rm python:3.12.16-slim python -c "import secrets; print(secrets.token_urlsafe(24), end='')"
$dir = Join-Path (Get-Location).ProviderPath 'secrets'
[IO.File]::WriteAllText((Join-Path $dir 'demo_api_key.txt'), $clave)
[IO.File]::WriteAllText((Join-Path $dir 'demo.env'), "DEMO_API_KEY=$clave`n")
Remove-Variable clave
foreach ($f in 'demo_api_key.txt', 'demo.env') { icacls (Join-Path $dir $f) /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null }
```

Si la carpeta del laboratorio está dentro de WSL (`\\wsl.localhost\...`), `icacls` responde «Función incorrecta» y no cambia los permisos: en ese caso restríngelos desde WSL con `chmod 600 secrets/demo_api_key.txt secrets/demo.env`.

`secrets/demo.env` contiene la misma clave en formato de variable de entorno y solo se usa para la comparación. La carpeta `secrets/` está excluida de Git (`.gitignore`) y de la imagen (`.dockerignore`).

## 2. Arrancar

```bash
docker compose -f compose.secrets-demo.yaml config --quiet
docker compose -f compose.secrets-demo.yaml up -d --build api-secreto
docker compose -f compose.secrets-demo.yaml ps
```

Para comparar con la variable de entorno:

```bash
docker compose -f compose.secrets-demo.yaml --profile comparar up -d api-entorno
```

## 3. Verificar

Comprobación completa, sin mostrar la clave (arranca, comprueba y elimina el proyecto del ejemplo):

```bash
bash scripts/verificar.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verificar.ps1
```

Solo las pruebas, dentro del contenedor `api-secreto`:

```bash
docker compose -f compose.secrets-demo.yaml run --rm --no-deps -v ./tests:/demo/tests:ro api-secreto python -m pytest -q -p no:cacheprovider /demo/tests
```

Resultado esperado: `5 passed` (puede aparecer `1 warning`).

## 4. Limpieza

```bash
docker compose -f compose.secrets-demo.yaml --profile comparar down --rmi all
rm -f secrets/demo_api_key.txt secrets/demo.env
```

```powershell
docker compose -f compose.secrets-demo.yaml --profile comparar down --rmi all
Remove-Item secrets\demo_api_key.txt, secrets\demo.env
```

`--rmi all` elimina solo la imagen de este ejemplo (`devsecops-ia-u04-secretos:local`). No afecta al `.env` ni a los contenedores del laboratorio principal.

## Advertencias

- `docker compose config` **sin** `--quiet` y con `--profile comparar` muestra el valor de la clave del servicio `api-entorno`.
- Docker Compose no cifra `secrets/demo_api_key.txt`: lo monta en el contenedor en solo lectura. Su protección depende de los permisos del fichero y del acceso al equipo.
