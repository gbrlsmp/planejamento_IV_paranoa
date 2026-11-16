$ErrorActionPreference = 'Stop'
$runRoot = $PSScriptRoot
do {
    $completeCount = 0
    foreach ($period in @('day','night')) {
        $statusPath = Join-Path $runRoot ('05_Verificacoes\execucao_' + $period + '_local.json')
        if (Test-Path -LiteralPath $statusPath) {
            $state = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
            if ($state.exit_code -ne 0) { throw "Execução falhou: $period" }
            $completeCount += 1
        }
    }
    if ($completeCount -ne 2) {
        if (-not (Get-Process -Name invest -ErrorAction SilentlyContinue)) { throw 'Sem processos InVEST e sem duas conclusões bem-sucedidas' }
        Start-Sleep -Seconds 10
    }
} until ($completeCount -eq 2)
foreach ($period in @('day','night')) {
    $argumentPath = Join-Path $runRoot ('01_Entradas\argumentos_' + $period + '.json')
    $argumentRecord = Get-Content -LiteralPath $argumentPath -Raw | ConvertFrom-Json
    $sourceWorkspace = $argumentRecord.args.workspace_dir
    $destinationName = if ($period -eq 'day') { '02_Dia_Concluido' } else { '03_Noite_Concluido' }
    $destinationWorkspace = Join-Path $runRoot $destinationName
    if (Test-Path -LiteralPath $destinationWorkspace) { throw "Destino já existe; conferir antes de copiar: $destinationWorkspace" }
    Copy-Item -LiteralPath $sourceWorkspace -Destination $destinationWorkspace -Recurse
}
$env:PYTHONHOME = 'C:\Program Files\QGIS 3.44.15\apps\Python312'
$env:PATH = 'C:\Program Files\QGIS 3.44.15\bin;' + $env:PATH
$env:PROJ_DATA = 'C:\Program Files\QGIS 3.44.15\share\proj'
$env:GDAL_DATA = 'C:\Program Files\QGIS 3.44.15\share\gdal'
$env:GDAL_CACHEMAX = '512'
$qgisPython = 'C:\Program Files\QGIS 3.44.15\bin\python3.exe'
& $qgisPython -X utf8 (Join-Path $runRoot 'extrair_e_verificar.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na extração/verificação; consultar mensagem acima' }
& $qgisPython -X utf8 (Join-Path $runRoot 'documentar_resultados.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na documentação/prévia; consultar mensagem acima' }
