param([Parameter(Mandatory=$true)][string]$Clima)
$ErrorActionPreference = 'Stop'
$climaRaiz = (Resolve-Path -LiteralPath $Clima).Path.TrimEnd('\')
function DentroDaBase([string]$Caminho) {
    $absoluto = [IO.Path]::GetFullPath($Caminho)
    if (-not $absoluto.StartsWith($climaRaiz + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Destino fora de 01_Clima: $absoluto" }
    return $absoluto
}
$pastas = @('01_Fontes','02_Metodologia_e_notas_tecnicas','03_Tabelas','04_Rasters','05_Analises_exploratorias','06_Execucoes_InVEST','07_Mapas_e_figuras','08_Scripts_e_verificacoes','09_Historico')
foreach ($nome in $pastas) { New-Item -ItemType Directory -Path (DentroDaBase (Join-Path $climaRaiz $nome)) -Force | Out-Null }
$movimentos = [Collections.Generic.List[object]]::new()
$mapaAnterior = Join-Path $climaRaiz '08_Scripts_e_verificacoes\MAPA_REORGANIZACAO.json'
if (Test-Path -LiteralPath $mapaAnterior) { foreach ($m in (Get-Content -LiteralPath $mapaAnterior -Raw | ConvertFrom-Json)) { $movimentos.Add($m) } }
function Agrupar([string]$OrigemRelativa,[string]$DestinoRelativo,[bool]$OcultarCompatibilidade=$true) {
    $origem = DentroDaBase (Join-Path $climaRaiz $OrigemRelativa)
    $destino = DentroDaBase (Join-Path $climaRaiz $DestinoRelativo)
    $item = Get-Item -LiteralPath $origem -Force
    if ($item.LinkType -in @('Junction','SymbolicLink')) { return }
    if (Test-Path -LiteralPath $destino) {
        $destinoItem = Get-Item -LiteralPath $destino -Force
        if ($destinoItem.LinkType -eq 'Junction') { return }
        if (@(Get-ChildItem -LiteralPath $destino -Force).Count -eq 0) { Remove-Item -LiteralPath $destino -Force }
        else { throw "Destino de movimentação já existe: $destino" }
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $destino) -Force | Out-Null
    # Ambos os caminhos absolutos já foram verificados dentro da base autorizada.
    try { [IO.Directory]::Move($origem,$destino) }
    catch {
        # Diretórios em uso permanecem fisicamente no lugar e recebem acesso
        # pelo grupo novo, preservando as conexões existentes do QGIS.
        New-Item -ItemType Junction -Path $destino -Target $origem | Out-Null
        if ($OcultarCompatibilidade) { [IO.File]::SetAttributes($origem, ([IO.File]::GetAttributes($origem) -bor [IO.FileAttributes]::Hidden)) }
        $movimentos.Add([pscustomobject]@{original=$origem;atual=$destino;compatibilidade='junction no grupo novo; origem física preservada';oculta=$OcultarCompatibilidade})
        return
    }
    try { New-Item -ItemType Junction -Path $origem -Target $destino | Out-Null }
    catch { [IO.Directory]::Move($destino,$origem); throw }
    if ($OcultarCompatibilidade) {
        [IO.File]::SetAttributes($origem, ([IO.File]::GetAttributes($origem) -bor [IO.FileAttributes]::Hidden))
    }
    $movimentos.Add([pscustomobject]@{original=$origem;atual=$destino;compatibilidade='junction';oculta=$OcultarCompatibilidade})
}
Agrupar '01_vetores' '01_Fontes\Vetores_meteorologicos_e_historicos'
Agrupar '02_tabelas' '01_Fontes\INMET'
Agrupar '03_scripts' '09_Historico\Scripts_anteriores'
Agrupar '04_rasters\Landsat_8_9_C2_L2' '01_Fontes\Landsat'
Agrupar '04_rasters\Completo_20261103_143519_903343' '09_Historico\Umidade_2025'
Agrupar '04_rasters\InVEST' '06_Execucoes_InVEST\Historicas'
$entregas = @('05_conferencia_ETo_seca_2026-11-14','06_verificacao_final_ETo_seca_2026-11-15','07_ETo_A001_seca_2026-11-15','08_Intensidade_construtiva_OB25D_2026-11-15','09_Densidade_regional_250_500m_2026-11-15','10_Altura_regional_500m_2026-11-15','11_Intensidade_combinada_500m_2026-11-15')
foreach ($nome in $entregas) { Agrupar $nome ('09_Historico\Entregas\'+$nome) }
Agrupar '08_Intensidade_construtiva_OB25D_2026-11-15\fontes' '01_Fontes\Open_Buildings' $false
$movimentos = @($movimentos | Group-Object original | ForEach-Object { $_.Group[-1] })
$movimentos | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $climaRaiz '08_Scripts_e_verificacoes\MAPA_REORGANIZACAO.json') -Encoding utf8

function Produto([string]$OrigemRelativa,[string]$DestinoRelativo) {
    $origem = DentroDaBase (Join-Path $climaRaiz $OrigemRelativa)
    $destino = DentroDaBase (Join-Path $climaRaiz $DestinoRelativo)
    if (Test-Path -LiteralPath $destino) { return }
    New-Item -ItemType Directory -Path (Split-Path -Parent $destino) -Force | Out-Null
    Copy-Item -LiteralPath $origem -Destination $destino
}
Produto '07_ETo_A001_seca_2026-11-15\ETo_A001_media_diaria_seca_2026_uniforme_3m.tif' '04_Rasters\ETo\ETo_A001_media_diaria_seca_2026_uniforme_3m.tif'
Produto '09_Densidade_regional_250_500m_2026-11-15\densidade_edificada_500m_percentual_3m.tif' '04_Rasters\Ocupacao_horizontal\densidade_edificada_500m_percentual_3m.tif'
foreach ($nome in @('altura_media_edificada_vizinhanca_500m_3m.tif','cobertura_alturas_validas_janela_500m_percentual_3m.tif','qualidade_altura_regional_500m_3m.tif')) {
    Produto ('10_Altura_regional_500m_2026-11-15\'+$nome) ('04_Rasters\Alturas\'+$nome)
}
foreach ($nome in @('componente_horizontal_D_500m_0a1_3m.tif','componente_vertical_V_500m_0a1_disponivel_3m.tif','indice_combinado_500m_disponivel_3m.tif','qualidade_combinacao_500m_3m.tif')) {
    Produto ('11_Intensidade_combinada_500m_2026-11-15\'+$nome) ('04_Rasters\Intensidade_combinada\'+$nome)
}
Produto '11_Intensidade_combinada_500m_2026-11-15\building_intensity_combinado_500m_proposto_3m.tif' '04_Rasters\Intensidade_combinada\building_intensity_500m_3classes_3m.tif'
foreach ($nome in @('ETo_A001_serie_diaria_153datas.csv','ETo_A001_resumo_mensal.csv','A001_horario_recorte_com_proveniencia.csv')) {
    Produto ('07_ETo_A001_seca_2026-11-15\'+$nome) ('03_Tabelas\Series_meteorologicas\'+$nome)
}
foreach ($nome in @('PARAMETROS_CALCULADOS.json','TREF_RESULTADOS.json','Tref_resumo.csv','parametros_calculados.csv','contraste_superficial_por_data.csv')) {
    Produto ('01_Fontes\Landsat\Parametros_seca_2026-11-14\'+$nome) ('03_Tabelas\Parametros_climaticos\'+$nome)
}
foreach ($nome in @('contraste_superficial_seca.png','comparacao_superficial_seca.png')) {
    Produto ('01_Fontes\Landsat\Parametros_seca_2026-11-14\'+$nome) ('07_Mapas_e_figuras\Landsat\'+$nome)
}
foreach ($m in $movimentos) {
    if (-not (Test-Path -LiteralPath $m.original) -or -not (Test-Path -LiteralPath $m.atual)) { throw 'Referência de compatibilidade indisponível' }
}
Write-Output ("Reorganização concluída: {0} diretórios agrupados, com caminhos anteriores preservados por junctions." -f $movimentos.Count)
