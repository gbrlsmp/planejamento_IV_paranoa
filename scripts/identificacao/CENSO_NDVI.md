# Censo exploratório do NDVI na grade nativa

As estatísticas exploratórias usam todos os pixels válidos de 3 m das referências existentes. A seca e a chuva são analisadas separadamente; os cortes permanecem calculados sobre o NDVI médio por pixel. O método de classificação, os quatro rasters e os derivados da IV permanecem preservados.

## População e cálculo

`calcular_censo_ndvi.py` lê os rasters existentes de seca, chuva e média estrita, em EPSG:31983. Usa a grade da seca e deslocamentos inteiros entre origens; não reprojeta nem reamostra NDVI. Cada referência do GeoPackage é rasterizada por centro de pixel, sem `ALL_TOUCHED`. As máscaras são independentes: um pixel não é excluído de uma formação pela prioridade de outra.

As três formações usam as mesmas interseções MapBiomas–ZEE dos cortes. Pastagem usa MapBiomas 15 recortado à bacia. Áreas úmidas mantêm a interseção operacional existente; as definições das fontes não são idênticas. Entram apenas pixels finitos em [-1, 1], diferentes de NoData e válidos nas duas datas. A validade do raster médio estrito é conferida contra esse pareamento em toda a grade.

| Grupo | Pixels válidos pareados |
| --- | ---: |
| Formação campestre | 4.373.980 |
| Formação savânica | 26.341.685 |
| Formação florestal | 5.626.327 |
| Campo alagado e área pantanosa | 273.761 |
| Pastagem | 8.393.078 |

O gerador lê faixas de 512 linhas por toda a largura. Calcula somas e somas de quadrados com acumuladores Float64 e desvio padrão populacional espacial por grupo e época. Não há seleção a cada 30 m nem sorteio. O raster médio é comparado pixel a pixel com a média Float32 das datas válidas.

O censo do NDVI médio reproduz as contagens e estatísticas adotadas para campestre, savânica e florestal. A conferência exige tolerância de 1e-12 em Float64 e igualdade dos limites convertidos para Float32. As diferenças residuais máximas dos limites nesta execução são da ordem de 2,5e-14, decorrentes da acumulação numérica. Os parâmetros de classificação não são substituídos por esses valores recalculados.

## Representação

- Histogramas: 80 intervalos entre -1 e 1, largura 0,025; todos os pixels, com normalização por grupo/data. Seca e chuva compartilham escalas.
- Tabela única e barras: médias e desvios populacionais por época, com quatro casas decimais apenas na apresentação.
- Sankey: agrega os histogramas nas mesmas faixas nas duas datas; 100% por grupo e época. Pastagem fica no topo. As fitas representam distribuições marginais, sem trajetórias individuais entre datas.
- Distribuição conjunta seca × chuva: matriz de 80 × 80 células de NDVI, 0,025 × 0,025. Todos os pares entram nas contagens, sem subamostragem. As marginais coincidem com os histogramas completos. A intensidade de cor é relativa à célula mais frequente do próprio grupo; não mede a proporção de área do grupo na bacia.

O bloco de quartis sazonais não é apresentado. Cores, mapa de referências e fonte científica das geometrias permanecem preservados; pastagem usa #915558.

## Produtos e reprodução

Registro local: `02_Tabela/Exploracao_NDVI_sistema/censo_ndvi.json`, sob a pasta da fitofisionomia. Publicação: `dados-mapas/identificacao/exploracao.json`, sem caminhos pessoais e sem os pontos espaciais de auditoria. As cinco cópias leves em `04_figuras` continuam sincronizadas. O NPZ e `exploracao_ndvi.json` amostrais permanecem como registros históricos e não alimentam os gráficos correntes. `atualizar_apresentacao_ndvi.py` recusa substituir o censo pela amostra histórica.

Usar Python/GDAL/NumPy/Shapely do ambiente científico e uma saída temporária nova:

```powershell
python scripts/identificacao/calcular_censo_ndvi.py --base "BASE" --web "dados-mapas/identificacao" --output "SAIDA_NOVA"
python scripts/identificacao/validar_censo_ndvi.py --base "BASE" --referencias "REFERENCIAS.gpkg" --tabelas "TABELAS" --publicacao "SAIDA_NOVA" --local "SAIDA_NOVA/censo_ndvi.json" --recontar-dir "SAIDA_NOVA/mascaras_temporarias"
```

Validar antes de promover os três JSON aos destinos correntes. As máscaras pertencem apenas à área temporária e não são produtos científicos permanentes. Fontes e código têm assinaturas registradas; os hashes de código normalizam quebras de linha para UTF-8/LF.

## Validação

`test_censo_ndvi.py` usa uma grade analítica para verificar centros, máscaras sobrepostas independentes, deslocamentos inteiros, NoData, extremos -1/1 e invariância ao tamanho da faixa.

`validar_censo_ndvi.py` confere fontes e históricos, proveniência, reprodução dos cortes, contagens, marginais, paletas e cópias locais/web. Nesta execução, conferiu 2.145 leituras diretas aos rasters e os centros nas geometrias. A opção `--recontar-dir` executa outra passagem integral em faixas de 257 linhas, com momentos centrais combinados por Welford e histogramas por `bincount`, independentemente dos acumuladores e do `histogram2d` do gerador. A recontagem reproduziu todas as estatísticas e células conjuntas.

Essas verificações demonstram coerência computacional. Não constituem validação temática de campo, prova de origem nativa, de conservação ou de limiares ótimos. Duas datas não caracterizam todo o ciclo fenológico; as demais limitações das fontes continuam válidas.
