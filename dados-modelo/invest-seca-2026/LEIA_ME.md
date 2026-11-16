# Execução oficial — seca 2026

InVEST Urban Cooling 3.20.2: dia (factors) e noite (intensity), 450 m de resfriamento e 500 m de mistura do ar. Energia/produtividade desativadas; sem média dia/noite ou classificação de risco sanitário. Referência do ar A001 — Brasília, 153 datas pareadas; dia 24,265416609534256 °C e noite 19,714379846732786 °C. Referência operacional urbana, sem equivalência demonstrada ao ar rural.

`configuracao.json`, `estatisticas_bacia.csv`, `verificacoes_bacia.json` e `fontes_sha256.json` registram configuração, estatísticas nativas e integridade. Os scripts são cópias da execução local e documentam a reprodução: devem ser colocados na pasta da rodada com `01_Entradas/argumentos_day.json` e `argumentos_night.json`, gerados por `preparar_execucao.py`. Ajuste a raiz da base e o caminho do executável ao ambiente; não execute produtores sobre uma entrega existente.

As rodadas completas ocorreram em pasta local fora do OneDrive, após um teste integral em recorte, para evitar WinError 5 na limpeza de temporários. Os logs nativos e GeoTIFFs de 3 m permanecem na base local, em `01_Clima/06_Execucoes_InVEST/Seca_2026_A001_Dia_Noite_2026-11-16`, pastas `02_Dia_Concluido` e `03_Noite_Concluido`. Não houve alteração de políticas de segurança.

O site usa derivados médios de 20 m em EPSG:3857 e codificação UInt16; consulta de valores e cores usam a mesma codificação. A legenda distingue escala comum e contraste do cenário. A estatística da bacia vem do raster nativo, não da prévia. As cores são interpoladas da paleta existente; não representam classes de risco.

UHI superficial diurno transferido ao ar e à noite por hipótese, ETo uniforme e ausência de calibração local continuam como limitações. O diagnóstico atual publica os 46.876 fragmentos, classes térmicas relativas e polígonos de zonas relativamente quentes do InVEST. Consulte `diagnostico_fragmentos_46876.csv`, `tref_a001.json` e os manifestos em `dados-mapas/clima/diagnostico-2026` e `superficie-sazonal`. A classificação não foi calibrada e não representa risco sanitário. A rodada anterior A045 foi preservada na base local.


Preparação atual: `scripts/preparar_revisao_clima.py` calcula as referências e gera uma nova pasta, recusando sobrescrever entregas. Após preparar entradas com o Python do QGIS, `--iniciar` define workspaces locais novos; `executar_invest.ps1` chama o InVEST oficial. Para concluir a cópia e extração use `scripts/concluir_revisao_clima.ps1 -RunRoot PASTA`. Os produtores `produzir_superficie_sazonal.py` e `publicar_diagnostico_clima.py` registram as composições, classes e polígonos. Ajuste os caminhos de ROOT/SCRATCH ao ambiente. Nenhuma execução modifica as fontes Landsat/INMET ou as geometrias originais.
