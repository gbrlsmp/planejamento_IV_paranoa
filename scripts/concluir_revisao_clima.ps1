param([Parameter(Mandatory=$true)][string]$RunRoot)
$ErrorActionPreference = 'Stop'
$runRootAbsolute = [IO.Path]::GetFullPath($RunRoot)
foreach ($period in @('day','night')) {
    $state = Get-Content -Raw -LiteralPath (Join-Path $runRootAbsolute "05_Verificacoes\execucao_${period}_local.json") | ConvertFrom-Json
    if ($state.exit_code -ne 0) { throw "Execução oficial sem êxito: $period" }
    $record = Get-Content -Raw -LiteralPath (Join-Path $runRootAbsolute "01_Entradas\argumentos_${period}.json") | ConvertFrom-Json
    $folder = if ($period -eq 'day') { '02_Dia_Concluido' } else { '03_Noite_Concluido' }
    $destination = Join-Path $runRootAbsolute $folder
    if (Test-Path -LiteralPath $destination) { throw "Destino existente; conferir em vez de sobrescrever: $destination" }
    Copy-Item -LiteralPath $record.args.workspace_dir -Destination $destination -Recurse
}
$env:PYTHONHOME = 'C:\Program Files\QGIS 3.44.15\apps\Python312'
$env:PATH = 'C:\Program Files\QGIS 3.44.15\bin;' + $env:PATH
$env:PROJ_DATA = 'C:\Program Files\QGIS 3.44.15\share\proj'
$env:GDAL_DATA = 'C:\Program Files\QGIS 3.44.15\share\gdal'
$env:GDAL_CACHEMAX = '512'
& 'C:\Program Files\QGIS 3.44.15\bin\python3.exe' -X utf8 (Join-Path $runRootAbsolute 'extrair_e_verificar.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na extração ou conferência' }
