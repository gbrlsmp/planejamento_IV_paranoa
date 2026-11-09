# Proxy de fitofisionomias em 3 m — Bacia do Paranoá

## Resultado e alcance

`classificar_fitofisionomias_3m.py` reproduz em **uma passagem** as cinco versões do raster até a v05. A grade é a do NDVI PlanetScope da seca, em EPSG:31983 e células de 3 × 3 m. Todos os pixels com pelo menos uma data de NDVI válida são classificados; os sem observação válida permanecem NoData 255. A posição urbana não exclui o pixel da classificação espectral.

Os rótulos 3 (florestal), 4 (savânica) e 12 (campestre) são **proxies espectrais**, não identificação botânica ou comprovação de vegetação nativa. As referências para explorar cortes vêm da interseção cartográfica MapBiomas × ZEE-DF; pastagem do MapBiomas é grupo de comparação. A escolha dos limites é exploratória, e a checagem por blocos espaciais usa as mesmas bases históricas, sem validação de campo independente.

## Regras, na ordem aplicada

| Versão | Operação |
| --- | --- |
| v01 | Florestal 3: seca ≥ 0,70. Savânica 4: 0,45 ≤ seca < 0,70 e média das datas ≥ 0,55. Campestre 12: 0,20 ≤ seca < 0,45 e 0,38 ≤ chuva < 0,62. Demais pares válidos: 100. |
| v02 | Savânica: seca ≥ 0,48 e média ≥ 0,58. Campestre: seca < 0,46. Campestre sobre vias ou edificações passa a 100. |
| v03 | O residual 100 passa a 101 quando `abs(chuva-seca)/2 ≥ 0,09`; caso contrário passa a 102. Para pixel válido apenas na seca, usar seca ≥ 0,34 para 101; apenas na chuva, chuva ≥ 0,50. |
| v04 | 101 sobre vias passa a 102. Depois sobrepor a classe 11 da banda original do MapBiomas, água vetorial 33 e edificações 103. Edificações têm prioridade sobre todas as classes. Vias servem apenas à limpeza. |
| v05 | Na categoria `risco=2`, “Ausência de Cerrado Nativo” do vetor ZEE-DF, 3 e 4 passam a vegetação intraurbana 100 e 12 passa a 101. |

O script também admite observação válida em apenas uma data: na seca usa os intervalos secos; apenas na chuva, 12 para 0,38–<0,62, 4 para 0,65–<0,79 e 3 para ≥0,79. Sobreposições vetoriais usam `ALL_TOUCHED=TRUE`; MapBiomas é transferido por vizinho mais próximo. A prioridade completa está expressa na ordem de atribuições do código e no JSON de relatório gerado junto com o raster.

## Reproduzir localmente

Requer Python com GDAL/OGR e NumPy, por exemplo o Python do QGIS no Windows. As entradas ficam fora do Git em `02 BASE DE DADOS`. O script verifica arquivos, CRS, resolução e alinhamento antes de começar; recusa sobrescrever saída existente.

```powershell
python scripts/identificacao/classificar_fitofisionomias_3m.py `
  --base "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS" `
  --output "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\02_Análises\03_Ecologia\03_Fitofisionomia\03_Raster\03_fitofisionomia\reproducao_v05.tif" `
  --stages-dir "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\02_Análises\03_Ecologia\03_Fitofisionomia\03_Raster\03_fitofisionomia\etapas_reproduzidas"
```

`--stages-dir` é opcional; sem ele, o processamento grava só v05 e seu relatório JSON. A saída nova não depende dos rasters classificados anteriores. Para republicar as visualizações da página, executar `exportar_fitofisionomias_web.py` com `--stages-dir` e `--final-raster` da reprodução acima, `--risk` apontando ao vetor ZEE-DF, `--samples` ao NPZ de amostras pareadas, `--qml` à simbologia `uso do solo.qml` e `--output-dir` a uma pasta vazia. Como alternativa, `--raster-dir` aceita a pasta que contém os cinco GeoTIFFs históricos. O exportador prepara cinco vistas de cerca de 20 m, um GIF, um mapa de contexto e blocos PNG de 3 m em EPSG:3857 para consulta por zoom. Os GeoTIFFs grandes não são publicados no Git.

## Conferência da reprodução

Em 08/11/2026, os cinco GeoTIFFs gerados pelo script consolidado foram comparados, pixel por pixel, aos arquivos locais v01–v05: **zero pixels diferentes em cada versão**. A v05 tem 117.365.300 pixels classificados e 107.932.640 NoData. Contagens de classes: 3 = 7.032.809; 4 = 30.787.965; 11 = 1.701.771; 12 = 7.185.341; 33 = 5.255.694; 100 = 10.060.941; 101 = 25.367.542; 102 = 20.869.555; 103 = 9.103.682. Os dois rasters de entrada têm células de 3 m, e a saída preserva esse tamanho e alinhamento. A visão geral do site reduz a resolução somente para visualização.

## Limitações

- Campestre e pastagem se misturam em NDVI. O corte não estabelece naturalidade nem composição florística.
- Duas datas não descrevem o ciclo fenológico completo. UDM2 não foi aplicada aos mosaicos; nuvens e sombras podem afetar pixels.
- O tamanho de célula de 3 m não equivale a acurácia temática de 3 m. A classe 11 herda limites da fonte MapBiomas de 10 m.
- 101 e 102 descrevem uma separação exploratória por NDVI, sem comprovar permeabilidade ou material de superfície.
- Vias são geometrias lineares sem largura uniforme. Edificações, água e contexto ZEE-DF têm incertezas próprias de data e posição.
- O mapa de satélite opcional do site usa Sentinel-2 cloudless 2025 de 10 m para orientação visual; não é a imagem PlanetScope classificada.
