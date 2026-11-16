param([Parameter(Mandatory=$true)][string]$RunRoot)
$ErrorActionPreference = 'Stop'
$deadline=(Get-Date).AddHours(4)
$statePath=Join-Path $RunRoot '05_Verificacoes\execucao_night_local.json'
while (-not (Test-Path -LiteralPath $statePath)) {
    if ((Get-Date) -gt $deadline) { throw 'Prazo de acompanhamento: verificar log noturno.' }
    Start-Sleep -Seconds 10
}
$state=Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
if ($state.exit_code -ne 0) { throw 'Execução oficial noturna falhou.' }
$arg=Get-Content -Raw -LiteralPath (Join-Path $RunRoot '01_Entradas\argumentos_night.json') | ConvertFrom-Json
$destination=Join-Path $RunRoot '03_Noite_Concluido'
if (Test-Path -LiteralPath $destination) { throw 'Destino já existe: conferir em vez de sobrescrever.' }
Copy-Item -LiteralPath $arg.args.workspace_dir -Destination $destination -Recurse
$env:PYTHONHOME='C:\Program Files\QGIS 3.44.15\apps\Python312'
$env:PATH='C:\Program Files\QGIS 3.44.15\bin;'+$env:PATH
$env:PROJ_DATA='C:\Program Files\QGIS 3.44.15\share\proj'
$env:GDAL_DATA='C:\Program Files\QGIS 3.44.15\share\gdal'
$python='C:\Program Files\QGIS 3.44.15\bin\python3.exe'
& $python -X utf8 (Join-Path $RunRoot 'extrair_e_verificar.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na extração.' }
& $python -X utf8 (Join-Path $PSScriptRoot 'verificar_correcao_noturna.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na verificação da correção.' }
& $python -X utf8 (Join-Path $PSScriptRoot 'publicar_invest_seca_2026.py') --execucao $RunRoot
if ($LASTEXITCODE -ne 0) { throw 'Falha nos derivados InVEST.' }
& $python -X utf8 (Join-Path $PSScriptRoot 'publicar_diagnostico_clima.py') --execucao $RunRoot
if ($LASTEXITCODE -ne 0) { throw 'Falha nos derivados do diagnóstico.' }
& $python -X utf8 (Join-Path $PSScriptRoot 'completar_metodologia_clima.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na geração do site.' }
& $python -X utf8 (Join-Path $PSScriptRoot 'validar_producao_clima.py') --baseline-ref 4fa1de26a88581fb289cb88d8e244e3c2a315196 --regenerar
if ($LASTEXITCODE -ne 0) { throw 'Falha na verificação do site.' }
