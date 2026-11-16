param([Parameter(Mandatory=$true)][string]$RunRoot)
$ErrorActionPreference = 'Stop'
$scriptsRoot = $PSScriptRoot
$deadline = (Get-Date).AddHours(4)
do {
    $done = 0
    foreach ($period in @('day','night')) {
        $path = Join-Path $RunRoot "05_Verificacoes\execucao_${period}_local.json"
        if (Test-Path -LiteralPath $path) {
            $state = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
            if ($state.exit_code -ne 0) { throw "Rodada falhou: $period" }
            $done += 1
        }
    }
    if ((Get-Date) -gt $deadline) { throw 'Tempo de acompanhamento esgotado; verificar processos/logs.' }
    if ($done -ne 2) { Start-Sleep -Seconds 10 }
} until ($done -eq 2)
& (Join-Path $scriptsRoot 'concluir_revisao_clima.ps1') -RunRoot $RunRoot
if (-not $?) { throw 'Falha ao concluir a extração' }
$python = 'C:\Program Files\QGIS 3.44.15\bin\python3.exe'
& $python -X utf8 (Join-Path $scriptsRoot 'verificar_revisao_clima.py') --modelo
if ($LASTEXITCODE -ne 0) { throw 'Falha na conferência independente' }
& $python -X utf8 (Join-Path $scriptsRoot 'publicar_invest_seca_2026.py') --execucao $RunRoot
if ($LASTEXITCODE -ne 0) { throw 'Falha nos derivados InVEST' }
& $python -X utf8 (Join-Path $scriptsRoot 'publicar_diagnostico_clima.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha no diagnóstico' }
& $python -X utf8 (Join-Path $scriptsRoot 'completar_metodologia_clima.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha na geração da página' }
& $python -X utf8 (Join-Path $scriptsRoot 'validar_producao_clima.py') --baseline-ref e247b32479f96f1779b575b8766dd78fafc68be5 --regenerar
if ($LASTEXITCODE -ne 0) { throw 'Falha na validação da página/derivados' }
& $python -X utf8 (Join-Path $scriptsRoot 'registrar_revisao_clima.py')
if ($LASTEXITCODE -ne 0) { throw 'Falha no registro local da rodada vigente' }
