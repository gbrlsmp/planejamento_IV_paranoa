param([switch]$SomenteValidar, [ValidateSet('both','day','night')][string]$Periodo='both')
$ErrorActionPreference = 'Stop'
$investExe = 'C:\Users\sampa\AppData\Local\Programs\InVEST 3.20.2 Workbench\resources\invest\invest.exe'
$runRoot = $PSScriptRoot
$env:GDAL_CACHEMAX = '512'
$env:GDAL_NUM_THREADS = '2'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$periods = if ($Periodo -eq 'both') { @('day','night') } else { @($Periodo) }
$transcriptPath = Join-Path $runRoot ('05_Verificacoes\terminal_' + $Periodo + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.txt')
Start-Transcript -LiteralPath $transcriptPath | Out-Null
try {
    foreach ($period in $periods) {
        $argumentsPath = Join-Path $runRoot ('01_Entradas\argumentos_' + $period + '.json')
        & $investExe validate --json $argumentsPath
        if ($LASTEXITCODE -ne 0) { throw "Validação oficial falhou: $period (código $LASTEXITCODE)" }
    }
    if (-not $SomenteValidar) {
        foreach ($period in $periods) {
            $argumentsPath = Join-Path $runRoot ('01_Entradas\argumentos_' + $period + '.json')
            $startedAt = (Get-Date).ToString('o')
            & $investExe run -d $argumentsPath urban_cooling
            $modelExitCode = $LASTEXITCODE
            $status = [ordered]@{period=$period; started_at=$startedAt; finished_at=(Get-Date).ToString('o'); exit_code=$modelExitCode; official_executable=$investExe; arguments_path=$argumentsPath}
            [System.IO.File]::WriteAllText((Join-Path $runRoot ('05_Verificacoes\execucao_' + $period + '_local.json')), ($status | ConvertTo-Json), $utf8)
            if ($modelExitCode -ne 0) { throw "Execução oficial falhou: $period (código $modelExitCode)" }
        }
    }
}
finally {
    Stop-Transcript | Out-Null
}
