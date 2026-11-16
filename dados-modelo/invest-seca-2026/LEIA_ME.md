# Execução oficial — seca 2026

InVEST Urban Cooling 3.20.2: dia (factors) e noite (intensity), 450 m de resfriamento e 500 m de mistura do ar. Energia/produtividade desativadas; sem média dia/noite ou classificação de risco.

`configuracao.json`, `estatisticas_bacia.csv`, `verificacoes_bacia.json` e `fontes_sha256.json` registram configuração, estatísticas nativas e integridade. Os scripts são cópias da execução local e documentam a reprodução: devem ser colocados na pasta da rodada com `01_Entradas/argumentos_day.json` e `argumentos_night.json`, gerados por `preparar_execucao.py`. Ajuste a raiz da base e o caminho do executável ao ambiente; não execute produtores sobre uma entrega existente.

As rodadas completas ocorreram em pasta local fora do OneDrive, após um teste integral em recorte, para evitar WinError 5 na limpeza de temporários. Os logs nativos e GeoTIFFs de 3 m permanecem na base local, em `01_Clima/06_Execucoes_InVEST/Seca_2026_Dia_Noite_2026-11-16`, pastas `02_Dia_Concluido` e `03_Noite_Concluido`. Não houve alteração de políticas de segurança.

O site usa derivados médios de 20 m em EPSG:3857 e codificação UInt16; consulta de valores e cores usam a mesma codificação. A legenda distingue escala comum e contraste do cenário. A estatística da bacia vem do raster nativo, não da prévia. As cores são interpoladas da paleta existente; não representam classes de risco.

UHI superficial diurno transferido ao ar e à noite por hipótese, ETo uniforme e ausência de calibração local continuam como limitações. Resultados por fragmento ficam para o diagnóstico e não integram estes arquivos de publicação.
