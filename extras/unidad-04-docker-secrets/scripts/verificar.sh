#!/usr/bin/env bash
# Ejemplo 4 (Unidad 4): verificación completa desde el equipo, sin mostrar la clave.
# Uso, desde extras/unidad-04-docker-secrets:  bash scripts/verificar.sh
# Requiere secrets/demo_api_key.txt y secrets/demo.env (paso 1 del README).
# Arranca el proyecto devsecops-ia-u04-secretos, lo comprueba y lo elimina al terminar.
set -uo pipefail
cd "$(dirname "$0")/.."
DC=(docker compose -f compose.secrets-demo.yaml --profile comparar)
FALLOS=0
ok()    { echo "  OK    $*"; }
error() { echo "  FALLO $*"; FALLOS=$((FALLOS + 1)); }
comprobar() { local desc=$1; shift; if "$@"; then ok "$desc"; else error "$desc"; fi; }
codigo() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

[ -s secrets/demo_api_key.txt ] && [ -s secrets/demo.env ] || { echo "Faltan los ficheros de secrets/: sigue el paso 1 del README."; exit 2; }
CLAVE=$(cat secrets/demo_api_key.txt)   # solo en memoria; nunca se imprime

echo "== 1. Fichero de origen"
comprobar "permisos 600 en secrets/demo_api_key.txt ($(stat -c %a secrets/demo_api_key.txt))" [ "$(stat -c %a secrets/demo_api_key.txt)" = 600 ]
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  comprobar "secrets/ excluido de Git" git check-ignore -q secrets/demo_api_key.txt
fi

echo "== 2. Arranque independiente"
comprobar "configuración válida" "${DC[@]}" config --quiet
"${DC[@]}" up -d --build >/dev/null 2>&1 || error "docker compose up"
for _ in $(seq 30); do curl -sf http://127.0.0.1:8007/health >/dev/null && curl -sf http://127.0.0.1:8008/health >/dev/null && break; sleep 1; done
echo "  api-secreto: $(curl -s http://127.0.0.1:8007/health)"
echo "  api-entorno: $(curl -s http://127.0.0.1:8008/health)"

echo "== 3. Secreto dentro del contenedor (sin mostrar su contenido)"
echo "  $("${DC[@]}" exec -T api-secreto stat -c '%A %u:%g %n' /run/secrets/demo_api_key)"
comprobar "el proceso puede leer /run/secrets/demo_api_key" "${DC[@]}" exec -T api-secreto test -r /run/secrets/demo_api_key

echo "== 4. Variables de entorno y metadatos (docker inspect)"
SEC=$("${DC[@]}" ps -q api-secreto); ENT=$("${DC[@]}" ps -q api-entorno)
echo "  nombres de variables en api-secreto: $(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SEC" | cut -d= -f1 | paste -sd' ')"
echo "  nombres de variables en api-entorno: $(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$ENT" | cut -d= -f1 | paste -sd' ')"
echo "  montajes de api-secreto: $(docker inspect -f '{{range .Mounts}}{{.Type}} {{.Destination}} rw={{.RW}}{{end}}' "$SEC")"
N_SEC=$(docker inspect "$SEC" | grep -cF -- "$CLAVE"); N_ENT=$(docker inspect "$ENT" | grep -cF -- "$CLAVE")
comprobar "api-secreto: DEMO_API_KEY no es variable de entorno" sh -c "! docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' $SEC | grep -q '^DEMO_API_KEY='"
comprobar "api-secreto: el valor no aparece en docker inspect (coincidencias: $N_SEC)" [ "$N_SEC" -eq 0 ]
comprobar "api-entorno (comparación): el valor SÍ aparece en docker inspect (coincidencias: $N_ENT)" [ "$N_ENT" -ge 1 ]
N_P1=$("${DC[@]}" exec -T api-secreto cat /proc/1/environ | tr '\0' '\n' | grep -cF -- "$CLAVE")
comprobar "api-secreto: el valor no está en el entorno del proceso principal (coincidencias: $N_P1)" [ "$N_P1" -eq 0 ]

echo "== 5. Autenticación en api-secreto (127.0.0.1:8007)"
R1=$(codigo http://127.0.0.1:8007/protegido)
R2=$(codigo -H 'x-api-key: clave-incorrecta-de-prueba' http://127.0.0.1:8007/protegido)
R3=$(codigo -H "x-api-key: $CLAVE" http://127.0.0.1:8007/protegido)
comprobar "sin clave $R1 · incorrecta $R2 · correcta $R3 (esperado 401 401 200)" [ "$R1 $R2 $R3" = "401 401 200" ]

echo "== 6. Pruebas automatizadas dentro del contenedor"
RES=$("${DC[@]}" run --rm --no-deps -v ./tests:/demo/tests:ro api-secreto python -m pytest -q -p no:cacheprovider /demo/tests 2>&1 | tail -1)
comprobar "pytest: $RES" grep -qE '^5 passed' <<<"$RES"

echo "== 7. Registros"
N_LOG=$("${DC[@]}" logs 2>&1 | grep -cF -- "$CLAVE")
comprobar "la clave no aparece en los registros (coincidencias: $N_LOG)" [ "$N_LOG" -eq 0 ]

echo "== 8. Detención independiente"
"${DC[@]}" down --remove-orphans >/dev/null 2>&1
RESTO=$(docker ps -a -q --filter label=com.docker.compose.project=devsecops-ia-u04-secretos; docker network ls -q --filter label=com.docker.compose.project=devsecops-ia-u04-secretos)
comprobar "no quedan contenedores ni redes del ejemplo" [ -z "$RESTO" ]
unset CLAVE

echo; [ "$FALLOS" -eq 0 ] && echo "RESULTADO: todas las comprobaciones superadas" || echo "RESULTADO: $FALLOS comprobaciones fallidas"
exit "$FALLOS"
