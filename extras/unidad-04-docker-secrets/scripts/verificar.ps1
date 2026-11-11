# Ejemplo 4 (Unidad 4): verificación completa desde el equipo, sin mostrar la clave.
# Uso (Windows PowerShell 5.1), desde extras\unidad-04-docker-secrets:
#   powershell -ExecutionPolicy Bypass -File scripts\verificar.ps1
# Fichero guardado en UTF-8 con BOM para que Windows PowerShell 5.1 lea bien las tildes.
# Requiere secrets\demo_api_key.txt y secrets\demo.env (paso 1 del README).
# Arranca el proyecto devsecops-ia-u04-secretos, lo comprueba y lo elimina al terminar.
Set-Location (Split-Path -Parent $PSScriptRoot)
$compose = @('compose', '-f', 'compose.secrets-demo.yaml', '--profile', 'comparar')
$script:fallos = 0
function Ok($texto)    { Write-Output "  OK    $texto" }
function Fallo($texto) { Write-Output "  FALLO $texto"; $script:fallos++ }
function Comprobar($texto, [bool]$condicion) { if ($condicion) { Ok $texto } else { Fallo $texto } }
function Codigo([string]$url, [string]$clave = '') {
    $cab = @{}; if ($clave) { $cab['x-api-key'] = $clave }
    try { [int](Invoke-WebRequest -Uri $url -Headers $cab -UseBasicParsing).StatusCode }
    catch { [int]$_.Exception.Response.StatusCode }
}
function Contar([string[]]$lineas, [string]$texto) { @($lineas | Select-String -SimpleMatch -Pattern $texto).Count }

$base = (Get-Location).ProviderPath
$rutaClave = Join-Path $base 'secrets\demo_api_key.txt'
if (-not ((Test-Path $rutaClave) -and (Test-Path (Join-Path $base 'secrets\demo.env')))) {
    Write-Output 'Faltan los ficheros de secrets\: sigue el paso 1 del README.'; exit 2
}
$clave = [IO.File]::ReadAllText($rutaClave).Trim()   # solo en memoria; nunca se imprime

Write-Output '== 1. Fichero de origen'
try {
    $identidades = (Get-Acl $rutaClave -ErrorAction Stop).Access | ForEach-Object { "$($_.IdentityReference.Value) ($($_.FileSystemRights))" }
    Write-Output "  permisos de secrets\demo_api_key.txt: $($identidades -join '; ')"
} catch {
    Write-Output '  permisos: no disponibles desde Windows en esta ruta (carpeta de WSL); revisar con: wsl stat -c %a secrets/demo_api_key.txt'
}
git check-ignore -q secrets/demo_api_key.txt 2>$null
if ($LASTEXITCODE -le 1) { Comprobar 'secrets\ excluido de Git' ($LASTEXITCODE -eq 0) }

Write-Output '== 2. Arranque independiente'
docker @compose config --quiet; Comprobar 'configuración válida' ($LASTEXITCODE -eq 0)
docker @compose up -d --build 2>&1 | Out-Null
foreach ($i in 1..30) { if ((Codigo 'http://127.0.0.1:8007/health') -eq 200 -and (Codigo 'http://127.0.0.1:8008/health') -eq 200) { break }; Start-Sleep 1 }
Write-Output "  api-secreto: $((Invoke-WebRequest http://127.0.0.1:8007/health -UseBasicParsing).Content)"
Write-Output "  api-entorno: $((Invoke-WebRequest http://127.0.0.1:8008/health -UseBasicParsing).Content)"

Write-Output '== 3. Secreto dentro del contenedor (sin mostrar su contenido)'
Write-Output "  $(docker @compose exec -T api-secreto stat -c '%A %u:%g %n' /run/secrets/demo_api_key)"
docker @compose exec -T api-secreto test -r /run/secrets/demo_api_key
Comprobar 'el proceso puede leer /run/secrets/demo_api_key' ($LASTEXITCODE -eq 0)

Write-Output '== 4. Variables de entorno y metadatos (docker inspect)'
$sec = docker @compose ps -q api-secreto; $ent = docker @compose ps -q api-entorno
$envSec = docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' $sec | Where-Object { $_ }
$envEnt = docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' $ent | Where-Object { $_ }
Write-Output "  nombres de variables en api-secreto: $(($envSec | ForEach-Object { ($_ -split '=')[0] }) -join ' ')"
Write-Output "  nombres de variables en api-entorno: $(($envEnt | ForEach-Object { ($_ -split '=')[0] }) -join ' ')"
Write-Output "  montajes de api-secreto: $(docker inspect -f '{{range .Mounts}}{{.Type}} {{.Destination}} rw={{.RW}}{{end}}' $sec)"
$nSec = Contar (docker inspect $sec) $clave; $nEnt = Contar (docker inspect $ent) $clave
$nP1 = Contar ((docker @compose exec -T api-secreto cat /proc/1/environ) -split [char]0) $clave
Comprobar 'api-secreto: DEMO_API_KEY no es variable de entorno' (-not ($envSec | Where-Object { $_ -like 'DEMO_API_KEY=*' }))
Comprobar "api-secreto: el valor no aparece en docker inspect (coincidencias: $nSec)" ($nSec -eq 0)
Comprobar "api-entorno (comparación): el valor SÍ aparece en docker inspect (coincidencias: $nEnt)" ($nEnt -ge 1)
Comprobar "api-secreto: el valor no está en el entorno del proceso principal (coincidencias: $nP1)" ($nP1 -eq 0)

Write-Output '== 5. Autenticación en api-secreto (127.0.0.1:8007)'
$r1 = Codigo 'http://127.0.0.1:8007/protegido'
$r2 = Codigo 'http://127.0.0.1:8007/protegido' 'clave-incorrecta-de-prueba'
$r3 = Codigo 'http://127.0.0.1:8007/protegido' $clave
Comprobar "sin clave $r1 · incorrecta $r2 · correcta $r3 (esperado 401 401 200)" ("$r1 $r2 $r3" -eq '401 401 200')

Write-Output '== 6. Pruebas automatizadas dentro del contenedor'
$res = docker @compose run --rm --no-deps -v ./tests:/demo/tests:ro api-secreto python -m pytest -q -p no:cacheprovider /demo/tests 2>&1 | Select-Object -Last 1
Comprobar "pytest: $res" ("$res" -match '^5 passed')

Write-Output '== 7. Registros'
$nLog = Contar (docker @compose logs 2>&1 | ForEach-Object { "$_" }) $clave
Comprobar "la clave no aparece en los registros (coincidencias: $nLog)" ($nLog -eq 0)

Write-Output '== 8. Detención independiente'
docker @compose down --remove-orphans 2>&1 | Out-Null
$resto = @(docker ps -a -q --filter label=com.docker.compose.project=devsecops-ia-u04-secretos) + @(docker network ls -q --filter label=com.docker.compose.project=devsecops-ia-u04-secretos) | Where-Object { $_ }
Comprobar 'no quedan contenedores ni redes del ejemplo' (@($resto).Count -eq 0)
Remove-Variable clave

Write-Output ''
if ($script:fallos -eq 0) { Write-Output 'RESULTADO: todas las comprobaciones superadas' } else { Write-Output "RESULTADO: $($script:fallos) comprobaciones fallidas" }
exit $script:fallos
