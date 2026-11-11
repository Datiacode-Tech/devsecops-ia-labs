#!/bin/sh
# Ejemplo 3 de la Unidad 4: Gitleaks sobre un repositorio Git de prácticas.
#
# Se ejecuta DENTRO del contenedor de Gitleaks. El repositorio de prácticas se crea en el /tmp
# del contenedor, con una credencial ficticia generada al vuelo, y desaparece al terminar
# (docker run --rm). No toca el proyecto ni su historial.
#
# Uso (desde la carpeta del proyecto, igual en WSL/Linux y PowerShell):
#   docker run --rm -v ./scripts:/scripts:ro --entrypoint sh ghcr.io/gitleaks/gitleaks:v8.28.0 /scripts/demo_unidad_04_gitleaks.sh
set -eu

escanear() {
  # $1 = dir | git. Sin valores: --redact oculta el secreto y solo se muestran los campos útiles.
  gitleaks "$1" . --redact --no-banner --no-color -v 2>&1 \
    | grep -E '^(RuleID|File|Line|Commit):|leaks found|no leaks' | sed 's/^/    /' || true
}

LAB=$(mktemp -d)
cd "$LAB"
git init -q
git config user.name 'Laboratorio U4'
git config user.email 'laboratorio@example.invalid'

echo '== Paso 1. Un compañero sube la configuración y unas notas'
CLAVE_FICTICIA=$(head -c 24 /dev/urandom | base64 | tr '+/' '-_')
printf 'MODEL_URL=http://mock-llm:8100/respond\nDEMO_API_KEY=%s\n' "$CLAVE_FICTICIA" > config.env
unset CLAVE_FICTICIA
# La línea curl se compone al ejecutar para que este script no sea, él mismo, un hallazgo.
printf '# Notas de pruebas\nComprobar que una clave incorrecta devuelve 401:\ncurl -H "%s: %s" http://127.0.0.1:8000/ask\n' \
  'x-api-key' 'clave-incorrecta-de-prueba' > notas.md
git add config.env notas.md
git commit -qm 'Configuración y notas de pruebas'
echo "    commit $(git rev-parse --short HEAD): config.env (credencial ficticia) y notas.md"

echo
echo '== Paso 2. gitleaks dir: analiza los archivos tal como están ahora'
escanear dir

echo
echo '== Paso 3. Corrección ingenua: borrar config.env en un commit nuevo'
git rm -q config.env
printf 'config.env\n' > .gitignore
git add .gitignore
git commit -qm 'Elimina config.env y lo excluye'
echo "    commit $(git rev-parse --short HEAD): config.env eliminado"
echo '    gitleaks dir (archivos actuales):'
escanear dir
echo '    gitleaks git (todo el historial):'
escanear git

echo
echo '== Paso 4. Falso positivo documentado: notas.md usa una clave de prueba que no funciona'
sed -i 's|/ask$|/ask  # gitleaks:allow (valor de prueba, no es una credencial)|' notas.md
git commit -qam 'Marca el valor de prueba como falso positivo'
echo '    gitleaks dir tras añadir el comentario gitleaks:allow:'
escanear dir
echo '    gitleaks git: el commit antiguo de notas.md sigue sin el comentario:'
escanear git

echo
echo '== Paso 5. Ignorar solo el falso positivo histórico por su huella (.gitleaksignore)'
gitleaks git . --redact --no-banner --no-color -v 2>/dev/null \
  | sed -n 's/^Fingerprint: *\(.*:notas\.md:.*\)$/\1/p' > .gitleaksignore
echo "    .gitleaksignore: $(cat .gitleaksignore)"
escanear git
echo '    Lo que queda es un verdadero positivo: la credencial sigue en el historial y hay que rotarla.'

echo
echo '== Limpieza'
cd /
rm -rf "$LAB"
echo "    repositorio de prácticas eliminado ($LAB)"
