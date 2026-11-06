# Mapas nos procedimentos dos indicadores de Riscos

Ilha de calor, umidade relativa, inundação, pressão de edificações e contexto de renda têm um mapa dentro de seu procedimento expansível, sem painel comparativo. Temperatura e HM conservam o comparativo de três cenários já documentado.

## Leituras e representação

Cada mapa oferece **Camada de entrada** e **Resultado por fragmento**. Essa escolha distingue a base que entra no cálculo da unidade de análise do diagnóstico.

- Na entrada de ilha de calor, exibe-se a zona já usada no diagnóstico. O limite ainda não foi regenerado com os novos cortes de temperatura.
- Na entrada de edificações, cada ocorrência é uma feição mapeada; não há porcentagem de ocupação nem degradê numérico nessa vista. O percentual está no resultado por fragmento.
- Umidade, profundidade de inundação e renda têm degradê e faixas cartográficas na entrada. As faixas são as já utilizadas no catálogo de contexto, sem alteração de seus cortes.
- Nos resultados numéricos por fragmento, há degradê e **classes já gravadas** no diagnóstico v01. A exportação não calcula novos intervalos ou modifica as classes.
- Ilha de calor por fragmento permanece categórica: sim ou não, sem degradê.
- Cinza identifica fragmentos sem dado válido. Fora dos fragmentos, a imagem é transparente. Na entrada, a transparência corresponde à ausência de cobertura/dado da imagem; não é convertida em zero.

As faixas cartográficas da entrada não devem ser confundidas com as classes do diagnóstico. Por exemplo, a entrada de umidade usa cinco faixas cartográficas em porcentagem; a classificação por fragmento tem quatro classes. Na inundação, a entrada mostra profundidade na célula, e o diagnóstico classifica o máximo dentro do fragmento. Renda usa a referência de R$ 1.212 por salário mínimo de 2022.

## Dados e exportação

- Resultados e geometrias: `mapa-dados.json.gz`, os mesmos utilizados pelo mapa geral. As geometrias publicadas já foram simplificadas e codificadas em WGS 84.
- Entradas em classes: imagens de `dados-mapas/contexto`, com limites e legendas do catálogo `contexto-riscos.json`.
- Entradas em degradê: rasters de umidade e inundação reamostrados por vizinho mais próximo; renda rasterizada do campo `V06004` dos setores com `RENDA_STATUS = disponivel`, dividida por 1.212.
- Resultados: geometrias reprojetadas para EPSG:3857 e rasterizadas pelo centro da célula. Valores e códigos de classe vêm diretamente dos atributos publicados. A última feição prevalece em eventual sobreposição geométrica.
- As novas imagens usam passo de 20 m em EPSG:3857, cerca de 17 m no terreno neste recorte. Não substituem geometrias e valores originais; fragmentos pequenos podem não ocupar um centro de célula. O mapa geral permite consultar os polígonos.
- O degradê usa 254 cores; o índice 0 é transparente e 255 reserva cinza para dados ausentes por fragmento. A quantização é gráfica e não altera os valores usados no diagnóstico.

O catálogo `dados-mapas/metodologia-riscos.json` registra imagens, limites, escalas, classes e contagens dos atributos por indicador. A contagem representa os fragmentos publicados, não a área das células da imagem.

Reprodução em Python com GDAL, NumPy e Pillow, a partir da pasta local de Riscos:

```sh
python scripts/exportar_mapas_metodologicos.py --base-dir "caminho/01_Riscos"
```

O exportador abre as fontes em modo de leitura e grava apenas as imagens e o catálogo do site. `--resolution` modifica o passo de visualização, não os resultados científicos.

## Carregamento e navegação

Os mapas são inicializados ao chegar à seção aberta. Cada camada é carregada quando selecionada. Zoom, enquadramento e navegação por teclado são locais a cada mapa, e as trocas de visualização preservam a posição. Falhas de carregamento oferecem nova tentativa.

A navegação de Riscos foi centralizada em `mapa.html`. O antigo endereço `mapa-riscos.html` redireciona ao mapa geral preservando busca e âncora. A tabela por RA também está no mapa geral e acompanha o indicador selecionado. Nos recortes temáticos de outros tópicos, ela fica oculta.

Links dos quadros podem pré-selecionar o indicador no mapa geral com `?indicador=umid_pct&visualizacao=fragmentos` ou `visualizacao=contexto`.
