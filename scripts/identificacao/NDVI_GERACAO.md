# NDVI da seca e da chuva — geração e resultados

Os dois rasters são calculados a partir dos mosaicos PlanetScope, separadamente, e recortados à Bacia do Paranoá. São produtos novos do sistema, não os rasters NDVI anteriores. O cálculo usa `(NIR − vermelho) / (NIR + vermelho)`, bandas 8 e 6, e mantém cada imagem na sua grade original de 3 m, SIRGAS 2000 / UTM 23S (EPSG:31983). Células fora da bacia, com banda igual a zero, denominador zero ou resultado inválido recebem NoData (-9999). O recorte utiliza o centro do pixel. O mosaico de cada data tem extensão e origem próprias, alinhadas em múltiplos de 3 m; comparações por pixel devem alinhar suas regiões comuns.

## Entradas

- Mosaico PlanetScope de 17/01/2026, oito bandas, com Red e NIR nas bandas 6 e 8.
- Mosaico PlanetScope de 30/07/2026, mesmas bandas.
- Limite da Bacia do Paranoá, vetor IPE-DF 2023, com todos os arquivos auxiliares do shapefile.
- As máscaras UDM2 não foram aplicadas aos mosaicos segundo seus relatórios e não foram fornecidas a esta execução; nuvens e sombras podem afetar os resultados.

## Reprodução

Preparar Python com GDAL/OGR e NumPy compatíveis (por exemplo, o ambiente Python do QGIS). No Windows, se necessário, definir `QGIS_BIN` para a pasta `bin` da instalação do QGIS. Criar previamente uma pasta de saída vazia e executar a partir da raiz do repositório, substituindo os caminhos pelos arquivos locais:

```powershell
python scripts/identificacao/gerar_ndvi.py --chuva "CAMINHO_DA_IMAGEM_CHUVA.tif" --seca "CAMINHO_DA_IMAGEM_SECA.tif" --bacia "CAMINHO_DO_LIMITE.shp" --out "PASTA_DE_SAIDA_EXISTENTE"
```

O programa recusa sobrescrever as saídas com os mesmos nomes. A pasta deve ser confirmada com a pesquisadora antes de salvar novos produtos. Registrar a versão das bibliotecas e os arquivos de entrada usados em cada reprodução. O MapBiomas não é entrada do cálculo de NDVI.

## Execução de 06/11/2026

Resultados locais em `02 BASE DE DADOS/02_Análises/03_Ecologia/03_Fitofisionomia/03_Raster/02_NDVI/`. Médias sobre todos os pixels válidos dentro da bacia, não por fitofisionomia; os conjuntos de pixels válidos diferem entre datas.

| Período | Arquivo | Pixels válidos | NDVI mínimo | NDVI médio | NDVI máximo | Tamanho |
|---|---|---:|---:|---:|---:|---:|
| Chuva, 17/01/2026 | ndvi_chuva_2026-01-17.tif | 117.363.808 | -0,831000 | 0,575854 | 0,999238 | 338.315.577 bytes |
| Seca, 30/07/2026 | ndvi_seca_2026-07-30.tif | 117.365.300 | -0,856886 | 0,452610 | 0,999598 | 351.837.281 bytes |

SHA-256 dos arquivos: chuva `e31b4cfbd3bff7d72f6b1c88614d0744c6f6c092a546936fb3a79ae4b006a1f2`; seca `72763fa471cc847aa2171ae6bfa373675594e4abbfe247b80371e4f4a30ae88d`.

Os metadados, o intervalo e os valores dos rasters foram conferidos; 80 pixels válidos distribuídos por blocos em cada arquivo foram comparados diretamente às bandas das imagens, com tolerância de 0,000001. Os rasters foram gerados localmente e não acompanham o repositório por ultrapassarem o limite de arquivo do GitHub. A exploração amostral por formação anterior continua identificada como tal; não foi recalculada a partir destes rasters. O mapa interativo dos novos produtos permanece pendente.
