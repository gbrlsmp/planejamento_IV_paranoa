# Proxy de fitofisionomias em 3 m — Bacia do Paranoá

## Resultado e alcance

`classificar_fitofisionomias_3m.py` produz **quatro etapas adotadas em uma passagem** pela grade do NDVI PlanetScope da seca (EPSG:31983, células de 3 × 3 m). Todos os pixels com pelo menos uma data válida são classificados; sem observação válida, permanecem NoData 255. A localização urbana não exclui um pixel da análise espectral. O produto local já calculado da etapa 04 conserva, por compatibilidade com projetos QGIS, o nome `fitofisionomias_proxy_ndvi_3m_v05.tif`; os nomes das quatro etapas no método e no site não incluem os testes descartados.

Formação florestal (3), formação savânica (4) e formação campestre (12) são **proxies espectrais**, sem comprovação botânica ou de origem nativa. As referências para explorar os cortes vêm da interseção MapBiomas × ZEE-DF; pastagem (15) é grupo de comparação. A checagem por blocos espaciais usa rótulos dessas bases históricas, sem validação de campo independente.

## Etapas adotadas

| Etapa e raster | Operação |
| --- | --- |
| 1 · raster 01 | Formação florestal (3): NDVI seca ≥ 0,70. Formação savânica (4): 0,48 ≤ seca < 0,70 e média das duas datas ≥ 0,58. Formação campestre (12): 0,20 ≤ seca < 0,46 e 0,38 ≤ chuva < 0,62. Demais pixels válidos: classe residual (100). Formação campestre (12) sobre vias OSM ou edificações Open Buildings passa a classe residual (100). |
| 2 · raster 02 | Na classe residual (100), `abs(chuva-seca)/2 ≥ 0,09` produz forração vegetal (101); abaixo desse limite, impermeável ou solo exposto (102). Se apenas a seca for válida, seca ≥ 0,34 produz forração vegetal (101); se apenas a chuva for válida, chuva ≥ 0,50. Os demais casos ficam em impermeável ou solo exposto (102). |
| 3 · raster 03 | Forração vegetal (101) sobre vias passa a impermeável ou solo exposto (102). Sobrepor, nessa ordem, campo alagado e área pantanosa (11) da banda original do MapBiomas, água (33) do vetor SEDUH/Geoportal e edificações (103) do Google Open Buildings. As edificações têm a última prioridade em todos os pixels classificados. Vias não se tornam classe. |
| 4 · raster 04, final | Na categoria `risco=2`, “Ausência de Cerrado Nativo” do ZEE-DF, formação florestal (3) e formação savânica (4) passam a vegetação intraurbana (100), e formação campestre (12) a forração vegetal (101). As demais classes permanecem. |

Na etapa 1, quando só a seca é válida, são usados os mesmos intervalos secos. Se só a chuva é válida: formação campestre (12) em 0,38–<0,62; formação savânica (4) em 0,65–<0,79; formação florestal (3) em ≥ 0,79. A ordem completa de atribuições está no código e no relatório JSON gerado. Vetores são rasterizados com `ALL_TOUCHED=TRUE`; a classe do MapBiomas é transferida por vizinho mais próximo.

## Entradas e proveniência das cores

- NDVI PlanetScope de chuva (17/01/2026) e seca (30/07/2026): variáveis espectrais e grade de 3 m.
- MapBiomas local identificado como 2025, 10 m: referências cartográficas e campo alagado e área pantanosa (11).
- ZEE-DF: cobertura vegetal para referências e risco de perda de vegetação nativa para a etapa 4.
- Google [Open Buildings](https://sites.research.google/gr/open-buildings/): edificações; OpenStreetMap: vias; SEDUH via Geoportal: massas d'água. Os arquivos vetoriais locais estão listados no script.
- `uso do solo.qml`: cores do raster final e das interseções. `uso do solo mapbiomas.qml`: cores do mapa MapBiomas e dos gráficos NDVI. `paletas_identificacao.py`: paletas derivadas para cobertura vegetal e risco do ZEE-DF. O QML MapBiomas não possui cor para lavoura perene (36); a visualização usa `#c0a77a` como cor complementar documentada.

## Reproduzir localmente

Requer Python com GDAL/OGR, NumPy e Pillow, como o ambiente Python do QGIS. As entradas ficam fora do Git em `02 BASE DE DADOS`. O script verifica arquivos, CRS, resolução e alinhamento e recusa sobrescrever uma saída existente.

```powershell
python scripts/identificacao/classificar_fitofisionomias_3m.py `
  --base "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS" `
  --output "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\02_Análises\03_Ecologia\03_Fitofisionomia\03_Raster\03_fitofisionomia\reproducao_etapa_04.tif" `
  --stages-dir "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\02_Análises\03_Ecologia\03_Fitofisionomia\03_Raster\03_fitofisionomia\etapas_reproduzidas"
```

`--stages-dir` é opcional; com ele, também são gravadas as etapas 01–03. O script nunca lê classificações anteriores. Para republicar o site, `exportar_fitofisionomias_web.py` aceita `--stages-dir` e `--final-raster` da reprodução ou `--raster-dir` com os quatro arquivos locais anteriormente chamados v02–v05. Também recebe `--risk`, `--samples`, `--qml` e `--output-dir` vazio. `atualizar_paletas_referencias.py` recolore os PNG paletizados de MapBiomas, ZEE-DF e interseções sem recalcular amostras ou geometrias.

O exportador cria quatro vistas gerais de aproximadamente 20 m, um GIF de quatro quadros, o mapa de risco do ZEE-DF e blocos PNG de 3 m em EPSG:3857 que o navegador carrega apenas em zoom próximo. Os GeoTIFFs integrais não são distribuídos pelo Git.

## Conferência

As quatro saídas adotadas devem ser comparadas pixel a pixel, respectivamente, aos arquivos locais anteriormente chamados v02, v03, v04 e v05. A etapa final tem 117.365.300 pixels classificados e 107.932.640 NoData. Contagens: formação florestal (3) = 7.032.809; formação savânica (4) = 30.787.965; campo alagado e área pantanosa (11) = 1.701.771; formação campestre (12) = 7.185.341; água (33) = 5.255.694; vegetação intraurbana (100) = 10.060.941; forração vegetal (101) = 25.367.542; impermeável ou solo exposto (102) = 20.869.555; edificações (103) = 9.103.682. A visão geral do site é reduzida somente para visualização.

## Limitações

- Formação campestre (12) e pastagem (15) se misturam em NDVI. O corte não estabelece origem nativa nem composição florística.
- Duas datas não descrevem o ciclo fenológico completo. UDM2 não foi aplicada aos mosaicos; nuvens e sombras podem afetar pixels.
- Células de 3 m não equivalem a acurácia temática de 3 m. Campo alagado e área pantanosa (11) herda limites da fonte MapBiomas de 10 m.
- Forração vegetal (101) e impermeável ou solo exposto (102) são inferências exploratórias; o NDVI não comprova permeabilidade nem material de superfície.
- Vias são linhas sem largura uniforme. Os vetores de edificações e água e o ZEE-DF têm incertezas próprias de data e posição.
- A imagem de satélite opcional do site é Sentinel-2 cloudless 2025 de 10 m, usada apenas para orientação visual; não é a imagem PlanetScope classificada.
