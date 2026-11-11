# Uso do solo e identificação da infraestrutura verde — método vigente

Método adotado em **11/11/2026**, chamado v2 nos testes dessa data. Ele substitui a rodada histórica v3. Os quatro rasters correntes perderam o sufixo `_v2`; as cópias correntes anteriores foram retiradas. Entradas originais e materiais históricos de outras análises foram preservados.

## Entradas e grade

- PlanetScope de chuva em 17/01/2026 e seca em 30/07/2026; NDVI = (banda 8 − banda 6) / (banda 8 + banda 6).
- Grade da seca: EPSG:31983, 3 × 3 m, 14.644 × 15.385 células; geotransformação `(166599, 3, 0, 8276418, 0, -3)`.
- NDVIs Float32, NoData −9999; classificação Byte, NoData 255.
- Referências atuais: `referencias_mapbiomas_zee_sistema.gpkg`, camada `referencias_equivalentes`, códigos 12, 4 e 3. Centros de pixel, todos os valores válidos, sem amostragem.
- Vias OSM sem filtro de pavimentação ou buffer; Google Open Buildings; água SEDUH/Geoportal; UCs de proteção integral; MapBiomas local identificado como 2025 e 10 m; ZEE-DF de risco de perda da vegetação nativa. Coleção MapBiomas e certas datas das fontes continuam sem comprovação documental.

O raster `ndvi_media_seca_chuva_2026.tif`, na pasta `02_NDVI`, exige as duas datas válidas. O classificador usa a média aritmética com duas observações válidas e o valor disponível com uma única data; sem observação válida, mantém NoData. Um valor válido é finito, entre −1 e 1 e diferente de NoData. A média temporal é calculada em Float32. Os quatro rasters classificados têm 117.365.300 pixels válidos, 1.492 a mais que o raster médio estrito.

## Quatro etapas adotadas

### 01 — classificação espectral e limpeza campestre

As estatísticas são **espaciais**, calculadas no raster médio dentro de cada interseção atual. O desvio é populacional (`ddof=0`); acumuladores Float64 sobre o raster Float32. Não é desvio temporal por pixel nem erro padrão da média.

| Formação | Pixels válidos | Média | Desvio padrão | Corte inferior | Fórmula |
| --- | ---: | ---: | ---: | ---: | --- |
| Campestre (12) | 4.373.980 | 0,4567 | 0,0618 | 0,5185 | média + desvio |
| Savânica (4) | 26.341.685 | 0,6419 | 0,0587 | 0,6419 | média |
| Florestal (3) | 5.626.327 | 0,7877 | 0,0522 | 0,7355 | média − desvio |

Parâmetros completos: campestre `0.5185165309558434`, savânica `0.6418583869084876`, florestal `0.7354611318541107`. Valores e limites são comparados em Float32; quatro casas decimais são somente apresentação.

Cada limite é inclusivo no início da classe. Campestre termina abaixo do limite savânico e savânica abaixo do florestal. NDVI válido abaixo do limite campestre recebe residual 100. Depois, somente campestre sobre vias ou edificações passa a residual. A residual 100 é cinza; não confundir com vegetação intraurbana 100 final.

As estatísticas anteriores divergiam porque usavam outras áreas de referência campestre e savânica. A referência florestal praticamente coincide. Isso explica os cortes diferentes, mas não reconstrói toda a composição do raster histórico `uso_cobertura_final_v01.tif`.

### 02 — nível de NDVI na residual

Somente a residual 100 é alterada: NDVI efetivo **≤ 0,3555 → 102**, impermeável ou solo exposto; **> 0,3555 → 101**, forração vegetal. Preservar formações e NoData.

A média sobre vias foi `0.355499212570903`; sobre edificações, `0.25223246599129945`. A pesquisa escolheu o limite **literal 0.3555**, com conversão Float32 na comparação. O primeiro teste com média entre grupos `0.3038658392811012` foi superado. A regra sazonal anterior de 0,09 e os limites auxiliares 0,34/0,50 não integram o método vigente. Com uma única data válida, aplica-se o mesmo 0,3555 ao NDVI disponível.

### 03 — sobreposições e UCs, nesta ordem

1. Forração 101 sobre vias passa para 102.
2. Classe 11 da primeira banda original do MapBiomas sobrepõe pixels válidos.
3. Água atribui 33, preservando as classes atuais 3 e 4.
4. Edificações atribuem 103 a todos os pixels válidos sob a máscara, inclusive sobre água e savânica, preservando somente a classe atual 3.
5. Em UCs de proteção integral, os pixels restantes 101 → 4 e 102 → 12.

Máscaras de vias, água e edificações são independentes. Vetores usam `ALL_TOUCHED=TRUE`; edificações são reprojetadas de EPSG:4326 para 31983. Filtro literal: `AVUs = 'UC' AND Grupo = 'UC - Proteção Integral'`. A exceção florestal vale no momento de aplicar edificações: áreas úmidas já foram aplicadas e o refinamento ZEE ainda ocorrerá.

A classe MapBiomas é transferida por vizinho mais próximo usando uma VRT GDAL, transformação aproximada padrão de 0,125 pixel, lida em faixas de **512 linhas por toda a largura**. Na reprodução desta rodada, ler a VRT em quadrados alterava pixels de borda; a leitura em faixas reproduziu integralmente os testes aprovados. O ambiente conferido consta no JSON de resultados.

### 04 — contexto ZEE-DF

Somente em `risco = 2`, legenda “Ausência de Cerrado Nativo”: 3/4 → vegetação intraurbana 100; 12 → forração 101. As demais classes, inclusive edificações 103, permanecem.

## Uso do solo final

| Classe | Pixels | Área (ha) |
| --- | ---: | ---: |
| Formação florestal (3) | 7.387.713 | 6.648,9417 |
| Formação savânica (4) | 22.256.030 | 20.030,4270 |
| Campo alagado e área pantanosa (11) | 1.701.852 | 1.531,6668 |
| Formação campestre (12) | 23.465.123 | 21.118,6107 |
| Água (33) | 5.194.968 | 4.675,4712 |
| Vegetação intraurbana (100) | 6.828.937 | 6.146,0433 |
| Forração vegetal (101) | 26.659.570 | 23.993,6130 |
| Impermeável ou solo exposto (102) | 14.771.930 | 13.294,7370 |
| Edificações (103) | 9.099.177 | 8.189,2593 |

Áreas = células × 9 m² / 10.000. NoData: 107.932.640 células, fora da soma.

## Fragmentos, métricas e tipologias de AVU

As classes **3, 4, 11, 12 e 100** formam a máscara de vegetação. Forração 101 fica fora. Vizinhança de oito pixels une lado ou vértice, inclusive entre classes diferentes. Novas geometrias e IDs foram gerados, sem transferir atributos por identidade de IDs antigos.

Resultado: **46.876 fragmentos**, **55.475,6895 ha**, 4 empates de predominância. Percentuais por classe usam contagem nativa de pixels; o maior define predominância, e empate recebe Empate. Máscara, áreas, composição e vizinhança foram conferidas pela rasterização de volta à grade.

A classificação AVU exige sobreposição de área positiva do fragmento inteiro. Duas ou mais categorias entre UC/parque/agrossistemas recebem Aviso; uma recebe seu rótulo; na ausência delas, APP; restantes Sem AVU. Os campos `avu_uc_pi`, `avu_uc_us`, `avu_agro`, `avu_parque` e `avu_app` permanecem disponíveis. A AVU usa as APPs históricas de nascente e hidrografia.

| AVU | Fragmentos | Área (ha) |
| --- | ---: | ---: |
| UC | 4.495 | 2.611,9062 |
| Parque urbano | 845 | 91,5543 |
| Agrossistemas não intensivos | 569 | 979,8399 |
| APP | 981 | 857,2473 |
| Aviso | 176 | 44.403,7761 |
| Sem AVU | 39.810 | 6.531,3657 |

As métricas usam R 4.5.3, magrittr e a função oficial `MK_Fragmentation`, revisão [0010946](https://github.com/connectscape/Makurhini/blob/0010946ab2eef7f8d2bc4935f369869fc4c58671/R/MK_fragmentation.R), SHA-256 normalizado `ed267329eedf677bfcc44bbbfe34d8590c3652ccbae260fd6eacddfe5aa865bb`. Python/GEOS 3.14.1 calcula geometrias; R recebe áreas/perímetros/núcleos por adaptadores e calcula as métricas oficiais e arredondamentos. Não se trata de geometria integralmente executada no pacote sf.

Buffer negativo com 30 segmentos por quadrante. Geometrias com pelo menos 5.000 coordenadas são tratadas em blocos centrais de 2.000 m, margem de borda + 6 m; foram 25 recuos por blocos e quatro comparações com recuo direto em cada cenário. Núcleos válidos, dentro das áreas originais, e núcleo de 90 m ≤ 45 m por fragmento.

| Borda | Núcleo (ha) | Núcleo (% da vegetação) | Fragmentos com núcleo |
| --- | ---: | ---: | ---: |
| 45 m | 41.031,0730 | 73,9623 | 347 |
| 90 m | 36.399,9060 | 65,6142 | 125 |

Área da paisagem: 1.056.287.128,2928 m². MESH: 89.611.444,5657 m² em ambos. Os campos são `Area`, `CA`, `CAPercent`, `Perimeter`, `EdgePercent`, `PARA`, `ShapeIndex`, `FRAC`. Nesta revisão oficial, PARA é área/perímetro; Cority é proporção de fragmentos com núcleo positivo. `min_node_area` permanece no padrão 100, sem excluir fragmentos pequenos da base.

## Elementos da infraestrutura verde

Regras preservadas, aplicadas aos novos fragmentos inteiros por prioridade:

1. **Hub 1:** somente os dois maiores pela área total dentre os que sobrepõem UC de proteção integral. IDs atuais: 17217 e 46862.
2. **Hub 2:** parques urbanos sem APP ainda sem classe.
3. **Link:** APP ainda sem classe; candidatos com **ShapeIndex > 25** recebem Hub 2. Exatamente 25 continua Link.
4. **Site 1:** agrossistemas não intensivos ainda sem classe.
5. **Site 2:** demais.

APP exclusiva da IV: `APP_Buffer_hid_Bacia_Paranoa_disso.gpkg`, camada `dissolvido`, com área positiva de sobreposição. O indicador AVU `avu_app` não decide IV. Não há herança por proximidade de 300 m.

| IV | Fragmentos | Área (ha) |
| --- | ---: | ---: |
| Hub 1 | 2 | 39.859,1361 |
| Hub 2 | 834 | 2.697,3756 |
| Link | 1.179 | 5.370,8076 |
| Site 1 | 714 | 272,7288 |
| Site 2 | 44.147 | 7.275,6414 |

O candidato ID 25996, ShapeIndex 31,8252, recebe Hub 2 por forma. Os cenários têm as mesmas geometrias, indicadores, área e ShapeIndex, conferidos por ID; somente métricas ligadas à borda diferem. Os dois cenários receberam e releram os mesmos rótulos de IV.

## Reprodução, arquivos e publicação

- `classificar_fitofisionomias_3m.py --base BASE --output NOVO_RASTER04 --stages-dir PASTA_VAZIA`: reproduz as quatro etapas das fontes, sem ler classificações anteriores. Parâmetros completos no código e relatório JSON. O destino deve ser novo.
- `classificar_tipologias_avu.py --base BASE --raster RASTER04 --output NOVO_GPKG --map-output NOVO_PNG`: delimita, cruza AVU e valida composição/vizinhança.
- `calcular_metricas_fragmentacao.py`: executar por borda 45 e 90; informar `--fragmentos`, `--bacia`, `--makurhini`, `--rscript`, `--saida` existente e `--borda`. Para R conda no Windows, pode ser necessário `--r-dll-dir`. A cópia local fica junto dos dados de fragmentação.
- `classificar_elementos_iv.py --metrics GPKG45 GPKG90 --app APP_DISSOLVIDA --apply`: compara cenários e grava `cat_iv`, preservando outras colunas. Sem `--apply`, apenas confere. `--raster`, `--qml`, `--map-output` exportam mapa e conferem as áreas nativas.
- `exportar_fitofisionomias_web.py`: recebe quatro rasters correntes, risco, NPZ de amostras e QML; gera quatro vistas, GIF com quatro quadros de 1,5 s, 46 blocos e manifesto com revisão de cache. `dados-mapas/uso.png` é idêntico à vista da etapa 04.
- `atualizar_apresentacao_ndvi.py --web PASTA_WEB --samples NPZ`: atualiza resumos por grupo/data e as vistas de referência existentes. A tabela e essas vistas omitem áreas úmidas; os dados científicos, o grupo exploratório e a classe 11 final permanecem. Pastagem usa `#915558`.

Os resumos gráficos usam a amostra sistemática pareada de 30 m, com médias/desvios espaciais por grupo e data. O gráfico média × desvio tem dois pontos por grupo, um por data. As barras são média ± desvio populacional, não intervalo de confiança. O gráfico seca × chuva mantém até 2.500 pares por grupo, com semente fixa. Nenhum raster de desvio foi criado.

`validar_identificacao.py --base BASE` confere os produtos correntes, CSVs/GeoPackages, áreas, IV, hashes dos rasters, GIF, blocos, catálogo e correspondências HTML. `validar_referencias_ndvi.py` confere as fontes, referências e amostras exploratórias.

GeoTIFFs e GeoPackages integrais permanecem locais. O Git distribui scripts, métodos, tabelas e imagens de consulta. O [JSON desta execução](../../dados-mapas/identificacao/resultados_identificacao.json) registra contagens, áreas, hashes dos rasters, parâmetros e ambiente. `METHOD_JSON` dos rasters preserva a proveniência dos testes que foram promovidos, inclusive seus nomes históricos.

Os GeoPackages correntes foram atualizados por transação no mesmo arquivo, para preservar as conexões do QGIS; atributos e geometrias foram relidos e comparados às saídas novas. Não foram encerradas sessões nem removidos WAL/SHM. Diagnóstico, riscos, zonas A/B/C e análises de conectividade não foram recalculados. A entrega segue por PR; integração à main depende da revisão da pesquisadora.

## Limitações

NDVI e regras média ± desvio são proxies empíricas, sem comprovação de origem nativa, composição botânica ou limiares ótimos. Duas datas não descrevem o ciclo fenológico completo. UDM2 não foi aplicada. Vias lineares sem largura/filtro de pavimentação e edificações sem erosão podem incluir pixels mistos, vegetação e sombras. Classe 102 reúne impermeabilização e solo exposto; 101 não é tipologia botânica validada. A classe 11 conserva o detalhe temático de 10 m. Referências cartográficas históricas não são validação independente. Vistas web reamostradas não substituem dados nativos para medir área.

## Histórico dos cortes de NDVI

| Rodada | Método e limiares |
| --- | --- |
| Inicial (v1) | Com duas datas válidas, formação florestal (3) se seca ≥ 0,70. Formação savânica (4) se 0,48 ≤ seca < 0,70 e média ≥ 0,58. Formação campestre (12) se 0,20 ≤ seca < 0,46 e 0,38 ≤ chuva < 0,62. Em data única, seca usa os mesmos intervalos secos e chuva usa 0,38–<0,62, 0,65–<0,79 e ≥ 0,79 para campestre, savânica e florestal, respectivamente. |
| v2 histórica (superada) | Desvio padrão amostral dos valores válidos de seca e chuva reunidos em cada interseção. Limites inferiores 0,5765370662151971 para formação campestre (12), 0,6418580985614883 para formação savânica (4) e 0,7282830052276217 para formação florestal (3). Florestal usa a mediana dos valores reunidos (0,7969018816947937) menos o desvio padrão (0,06861887646717196). |
| Primeiro teste v3 | Desvio padrão amostral calculado sobre a média seca–chuva de cada pixel das interseções. Limites inferiores 0,5185165380148051 para formação campestre (12), 0,6418583869093903 para formação savânica (4) e 0,7354611272062169 para formação florestal (3). |
| v3 histórica (superada) | Recuperação dos cortes históricos da etapa de NDVI médio. Era a base anterior sem sufixo; substituída pelo método adotado em 11/11/2026. |
| v2 de 11/11/2026 (vigente) | Referências atuais, desvio populacional espacial, cortes completos registrados acima; residual literal 0,3555; edificações depois da água, preservando classe atual 3. |
