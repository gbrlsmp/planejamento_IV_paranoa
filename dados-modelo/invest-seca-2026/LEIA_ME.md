# Execução oficial — seca 2026

InVEST Urban Cooling 3.20.2: dia (factors) e noite (intensity), 450 m de resfriamento e 500 m de mistura do ar. Energia/produtividade desativadas; sem média dia/noite ou classificação de risco sanitário. Referência do ar A001 — Brasília, 153 datas pareadas; dia 24,265416609534256 °C e noite 19,714379846732786 °C. Referência operacional urbana, sem equivalência demonstrada ao ar rural.

`configuracao.json`, `estatisticas_bacia.csv`, `verificacoes_bacia.json` e `fontes_sha256.json` registram configuração, estatísticas nativas e integridade. Os scripts publicados registram a execução local. A preparação vigente e seus módulos de apoio devem ser executados a partir do repositório completo, conforme o procedimento abaixo. Ajuste a raiz da base e o caminho do executável ao ambiente; não execute produtores sobre uma entrega existente.

A nova noite ocorreu em pasta local fora do OneDrive para evitar WinError 5 na limpeza de temporários; o dia foi copiado da rodada A001 anterior após prova integral de equivalência. Os logs nativos e GeoTIFFs de 3 m permanecem na base local, em `01_Clima/06_Execucoes_InVEST/Seca_2026_A001_102_104_2026-11-16`, pastas `02_Dia_Concluido` e `03_Noite_Concluido`. Não houve alteração de políticas de segurança.

O site usa derivados médios de 20 m em EPSG:3857 e codificação UInt16; consulta de valores e cores usam a mesma codificação. A legenda distingue escala comum e contraste do cenário. A estatística da bacia vem do raster nativo, não da prévia. As cores são interpoladas da paleta existente; não representam classes de risco.

UHI superficial diurno transferido ao ar e à noite por hipótese, ETo uniforme e ausência de calibração local continuam como limitações. O diagnóstico atual publica os 46.876 fragmentos, classes térmicas relativas e polígonos de zonas relativamente quentes do InVEST. Consulte `diagnostico_fragmentos_46876.csv`, `tref_a001.json` e os manifestos em `dados-mapas/clima/diagnostico-2026` e `superficie-sazonal`. A classificação não foi calibrada e não representa risco sanitário. A rodada anterior A045 foi preservada na base local.

## Correção noturna das classes 102 e 104

A nova noite foi executada oficialmente após estender o índice de entorno às superfícies 102 e 104. A tabela auxiliar tem 18 códigos: 1020–1023, 1040–1043 e as dez linhas preservadas. O zero significa ausência de edificações no entorno e é mantido em categoria própria; as demais faixas são até 0,25, até 0,50 e acima de 0,50. Coeficientes são médias do índice disponível em cada subclasse; preenchimentos não entram na média. A mediana regional de 6,445500373840332 m é usada nas lacunas com D positivo, com flag e contagem explícitas. São 484.009 pixels (435,6081 ha). É proxy de intensidade territorial, não medição do armazenamento térmico do asfalto ou do solo.

O dia foi reaproveitado da rodada A001 anterior: a equivalência de Kc, sombra, albedo e green_area foi comprovada em todos os 225.297.940 pixels da grade. Não se alega nova execução diurna. Conferir `equivalencia_diurna_102_104.json` e a tabela de 18 classes. Os dados Landsat e as referências A001 também foram preservados.

Reprodução a partir do repositório: `python scripts/corrigir_intensidade_noturna.py` prepara uma nova pasta (ajustar PREVIOUS/RUN/SCRATCH ao ambiente). Execute somente `executar_invest.ps1 -Periodo night` nessa pasta. Depois, `scripts/finalizar_correcao_noturna.ps1 -RunRoot PASTA` copia a noite, extrai, confere e produz os derivados. O dia já existe e não deve ser novamente copiado por um finalizador antigo. A planilha pode ser atualizada com `scripts/atualizar_tabela_biofisica_102_104.mjs PASTA_CLIMA MODULOS_RUNTIME PASTA_SAIDA`, preservando a aba Diurna e as fórmulas da 103.
