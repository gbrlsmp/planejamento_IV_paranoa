# Identificação da vegetação na Bacia do Paranoá

Esta pasta contém a exploração inicial da identificação da vegetação com PlanetScope, MapBiomas e ZEE-DF. A metodologia está em desenvolvimento e os cortes da classificação final ainda não foram definidos.

## Entradas e subprodutos

Consultar [Camadas de entrada e origem dos subprodutos](CAMADAS_E_SUBPRODUTOS.md). O documento apresenta as fontes necessárias, suas resoluções ou escalas, o fluxo de dependências e o estado de cada resultado.

O código lê os caminhos de entrada declarados em [camadas_identificacao.json](camadas_identificacao.json). A entrada adotada é o MapBiomas local de 10 m identificado como 2025. O download online não é necessário para essa execução.

## Primeira exploração

- [Método e resultados descritivos](resultados/LEITURA.md)
- [Gráficos sazonais](resultados/comparacao_ndvi.png)
- [Registro da execução, assinaturas das fontes e estatísticas](resultados/resultados.json)
- [Código de análise](analisar_vegetacao.py)
- [Código dos gráficos](apresentar_resultados.py)

Na última alteração, foram conferidos os seis caminhos de entrada contra os arquivos utilizados na primeira execução, as referências do inventário e a ausência de ciclos nas dependências. As estatísticas dessa primeira execução não foram recalculadas.

A apresentação futura pertence a Identificação → Uso do solo e seguirá a organização de Riscos socioambientais. A documentação acompanha a proposta de atualização da página Uso do solo.

## Ambiente de execução

Usar Python com GDAL/OGR e NumPy para a análise; Matplotlib para os gráficos. No Windows, executar no ambiente Python do QGIS ou definir `QGIS_BIN` com a pasta de DLLs da instalação. O inventário JSON deve acompanhar os scripts.

Os rasters científicos e as amostras NPZ não são distribuídos neste repositório. As amostras são regeneradas pelo script antes de executar a apresentação. Usar uma pasta de saída nova para preservar a execução anterior.
