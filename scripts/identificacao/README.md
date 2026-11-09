# Identificação da vegetação na Bacia do Paranoá

Esta pasta contém os procedimentos de identificação da vegetação com PlanetScope, MapBiomas e ZEE-DF e o registro da exploração inicial. A proxy de fitofisionomias em 3 m está documentada em [FITOFISIONOMIA_3M.md](FITOFISIONOMIA_3M.md). Ela é um resultado exploratório, sujeito a validação independente.

## Entradas e subprodutos

Consultar [Camadas de entrada e origem dos subprodutos](CAMADAS_E_SUBPRODUTOS.md). O documento apresenta as fontes necessárias, suas resoluções ou escalas, o fluxo de dependências e o estado de cada resultado.

O código lê os caminhos de entrada declarados em [camadas_identificacao.json](camadas_identificacao.json). A entrada adotada é o MapBiomas local de 10 m identificado como 2025. O download online não é necessário para essa execução.

## Referências e análise exploratória

Consultar [Referências e NDVI — método, produtos e reprodução](REFERENCIAS_E_NDVI.md). O programa `preparar_referencias_ndvi.py` produz interseções vetoriais entre quatro pares de classes correspondentes, lê os dois novos NDVIs integrais e prepara distribuições por data e o gráfico seca × chuva. Pastagem participa somente como comparação. A correspondência de áreas úmidas é operacional, com definições distintas explicitadas.

As versões leves são guardadas em `04_figuras`, destino confirmado pela pesquisadora, e copiadas para `dados-mapas/identificacao/` para o site. O GeoPackage e as amostras completas permanecem locais. A etapa seguinte usa os dois novos NDVIs para aplicar os cortes documentados em `FITOFISIONOMIA_3M.md`.

## Classificação proxy e publicação

`classificar_fitofisionomias_3m.py` aplica as quatro etapas adotadas em uma passagem pelos NDVIs, sem ler classificações anteriores. `exportar_fitofisionomias_web.py` prepara quatro vistas leves, o GIF, o mapa de risco do ZEE-DF, os blocos detalhados e as tabelas adicionais. `atualizar_paletas_referencias.py` aplica os QML às imagens de referência já calculadas. Entradas locais e GeoTIFFs integrais ficam fora do repositório; a página publica apenas arquivos de consulta. Consulte [o método e a reprodução](FITOFISIONOMIA_3M.md).

## Primeira exploração — registro histórico

- [Método e resultados descritivos](resultados/LEITURA.md)
- [Gráficos sazonais](resultados/comparacao_ndvi.png)
- [Registro da execução, assinaturas das fontes e estatísticas](resultados/resultados.json)
- [Código de análise](analisar_vegetacao.py)
- [Código dos gráficos](apresentar_resultados.py)

O inventário descreve agora os caminhos atuais. O JSON da primeira execução preserva os caminhos e resultados históricos; suas estatísticas não foram reescritas como se pertencessem à nova execução.

A apresentação pertence a Identificação → Uso do solo, com referências na etapa 1 e NDVI/análise exploratória na etapa 2. A documentação acompanha a proposta de atualização da página Uso do solo.

## Ambiente de execução

Usar Python com GDAL/OGR, NumPy, Shapely 2 e Pillow no novo processamento. Os dois gráficos atuais são desenhados pelo navegador a partir do JSON. Matplotlib é usado somente pelo apresentador da exploração histórica. No Windows, executar no ambiente Python do QGIS ou definir `QGIS_BIN` com a pasta de DLLs da instalação. O inventário JSON deve acompanhar os scripts.

Os rasters científicos e as amostras NPZ não são distribuídos neste repositório. As amostras são regeneradas pelo script antes de executar a apresentação. Usar uma pasta de saída nova para preservar a execução anterior.
