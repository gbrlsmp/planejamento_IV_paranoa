# Produção do indicador e aplicação no diagnóstico

Riscos, Condicionantes e Ecologia começam pela explicação breve e pela tabela de indicadores e critérios. Depois apresentam Produção do indicador e Aplicação no diagnóstico. Em temperatura e HM, o comparativo fixo e o mapa interativo ficam dentro do procedimento expansível da respectiva caixa. As lacunas científicas de Ecologia continuam explícitas. Os modelos não são executados pelo site.

## Clima

As descrições de temperatura e HM foram conferidas nos metadados das saídas v6 e nos registros do InVEST Urban Cooling 3.20.2, de 28 de outubro de 2026.

| Parâmetro | Valor registrado |
| --- | --- |
| Método do cenário de dia | factors |
| Método do cenário de noite | intensity (o nome de saída preserva a grafia intenssity) |
| Temperatura de referência | 22,09 °C |
| Magnitude máxima de ilha de calor | 10,71 °C |
| Distância de resfriamento de áreas verdes | 450 m |
| Raio de mistura do ar | 500 m |
| Valoração de energia e produtividade | Desativadas |
| Grade das saídas térmicas conferidas | 3 m |

Entradas identificadas: uso_cobertura_final_v01.tif, tab_biofisica_InVEST_v5.csv, ETo_2025_ago_set_bacia_paranoa_3m.tif e limite da bacia. Os metadados T_air_bacia_paranoa_v6_factors.tif.yml e T_air_bacia_paranoa_v6_intenssity.tif.yml registram a linhagem das saídas. Os registros da rodada integram a base de pesquisa local; esses arquivos não são distribuídos por este repositório.

Para reproduzir a modelagem, reunir as entradas originais, a tabela biofísica e os parâmetros acima. Consultar o [manual oficial do InVEST Urban Cooling](https://storage.googleapis.com/releases.naturalcapitalproject.org/invest-userguide/latest/en/urban_cooling_model.html). Os argumentos de pesos de factors estão vazios. Foi conferido no código oficial da versão 3.20.2 que isso ativa os padrões 0,6 para sombra, 0,2 para albedo e 0,2 para ETI; os pesos são normalizados pela soma. A [aplicação local do modelo](../aplicacao-invest.html) documenta entradas, tabelas e dependências. O [registro de conferência](conferencia-invest.md) distingue a ETo da rodada v6 do processamento posterior.

O [script de riscos](../scripts/01_Diagnostico_RISCOS.py) recebe as saídas prontas: temperatura é consultada no interior do fragmento; HM, em faixa externa de 5 m. As camadas médias de temperatura e HM correspondem a `(dia + noite) / 2`, célula a célula. Essa expressão foi conferida nas seis camadas originais, com diferenças residuais compatíveis com ponto flutuante. Não é uma média observada de 24 horas. Os [comparativos e mapas de cenários](cenarios-climaticos.md) distinguem a escala contínua comum das cinco classes de cada raster.

A entrada Zona_ICU.shp é um subproduto da temperatura média do ar do InVEST, conforme origem esclarecida pela autora. O critério do estudo reúne as três classes mais quentes da temperatura média (média, ruim e muito ruim). O diagnóstico recebe o polígono pronto e registra interseção com área positiva. Sua atualização com os novos cortes integrais, e o recálculo das interseções, permanecem uma etapa posterior aos mapas exploratórios desta entrega.

## Água

Fontes locais conferidas: proveniencia_e_limites.json (versão de execução 1.1.1), pesos_fahp.json, regras_pertinencia.txt e o gerador momentos_agua_paranoa-Nightcity.py, versão 1.1.1. Os nomes identificam os registros da base de pesquisa; o gerador e suas entradas não integram este repositório.

| Configuração | Valor registrado |
| --- | --- |
| Sistema de coordenadas | SIRGAS 2000 / UTM 23S, EPSG:31983 |
| Terreno inicial | 2 m |
| Grade de Momentos da Água | 5 m |
| Grade hidrológica | 20 m |
| Limiar de drenagem | 0,25 km² |
| Durações de chuva | 60, 180, 360, 720 e 1.440 min |
| Tempos de retorno simulados | 5, 10, 20, 50, 100, 200 e 500 anos |
| Passo dos hidrogramas | 5 min |
| Coeficientes IDF | K = 816,7; a = 0,081; b = 8,99; c = 0,704 |
| Fração de abstração inicial | 0,2 de S |
| Manning do canal | 0,045 |

A geração da inundação utiliza excesso de chuva SCS-CN, hidrogramas, propagação na rede e curvas de vazão e nível com HAND. Por trecho é selecionado o maior pico entre durações. O diagnóstico recebe inundacao_profundidade_TR5_hidro.tif, em vez do raster de visualização.

A classificação de momentos combina nove critérios: declividade, fluxo, posição altimétrica, solos, infiltração, lençol freático, inundação, distância da drenagem e uso do solo. Os pesos registrados, nessa ordem, são 0,2119868248; 0,2119868248; 0,1375768726; 0,0504663705; 0,0834942838; 0,0834942838; 0,1375768726; 0,0329512966; 0,0504663705. A disponibilidade dos critérios altera a ponderação efetiva.

A execução informa ausência de ajuste local suficiente para lençol freático em áreas terrestres, com renormalização explícita dos pesos. O momento dominante corresponde à maior pontuação. A diferença entre as duas maiores define forte (≥ 0,15), moderado (≥ 0,05 e < 0,15) ou transição (< 0,05).

A proveniência registra modelo exploratório sem calibração de vazões nem observações independentes de inundação. Chuva pontual é aplicada uniformemente; não há simulação da operação do lago, pontes, bueiros, batimetria ou remanso. Reamostragem para 5 m não cria resolução hidrológica de 5 m. O tempo de retorno da chuva não assegura igual frequência da cheia.

O [guia de Condicionantes](../scripts/LEIA_ME_CONDICIONANTES.md) documenta o cruzamento do raster final com os fragmentos. Esse cruzamento não refaz o modelo de produção.

## Potencial de recuperação ecológica

O método de Rubens do Amaral foi conferido nas pp. 171–173 e no Quadro 4 da [tese de 2023](https://repositorio.unb.br/handle/10482/45979). A descrição na interface é uma síntese; os procedimentos e a discussão completos devem ser consultados na fonte.

A aplicação atual recebe PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp da SEDUH-DF, com classes registradas em cat_pdot20. O diagnóstico não recalcula TWI ou CO₂flux. A equivalência entre as categorias de demanda da tese e a legenda de potencial da camada depende de metadados ou comparação das bases, e não foi presumida.

## Escopo desta documentação

Os comparativos e as imagens de visualização acrescentam uma exploração das camadas climáticas de entrada, sem alterar rasters originais, scripts de diagnóstico ou os resultados publicados por fragmento. Para reproduzir a produção, ainda é necessário reunir os geradores, as entradas e os registros originais da pesquisa. Para reproduzir o cruzamento com os fragmentos, seguir os guias de Riscos e Condicionantes do repositório.
