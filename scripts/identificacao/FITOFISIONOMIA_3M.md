# Proxy de fitofisionomias em 3 m — Bacia do Paranoá

## Resultado e alcance

`classificar_fitofisionomias_3m.py` produz **quatro etapas adotadas em uma passagem** pela grade do NDVI PlanetScope da seca (EPSG:31983, células de 3 × 3 m). Todos os pixels com pelo menos uma data válida são classificados; sem observação válida, permanecem NoData 255. A localização urbana não exclui um pixel da análise espectral. Os quatro GeoTIFFs locais são identificados de `fitofisionomias_proxy_ndvi_3m_etapa_01.tif` a `fitofisionomias_proxy_ndvi_3m_etapa_04.tif`.

Formação florestal (3), formação savânica (4) e formação campestre (12) são **proxies espectrais**, sem comprovação botânica ou de origem nativa. As referências para explorar os cortes vêm da interseção MapBiomas × ZEE-DF; pastagem (15) é grupo de comparação. A checagem por blocos espaciais usa rótulos dessas bases históricas, sem validação de campo independente.

## Etapas adotadas

| Etapa e raster | Operação |
| --- | --- |
| 1 · raster 01 | Aplicar ao NDVI médio os cortes históricos da tabela abaixo. Formação campestre (12) sobre vias OSM ou edificações Open Buildings passa a classe residual (100). |
| 2 · raster 02 | Na classe residual (100), `abs(chuva-seca)/2 ≥ 0,09` produz forração vegetal (101); abaixo desse limite, impermeável ou solo exposto (102). Se apenas a seca for válida, seca ≥ 0,34 produz forração vegetal (101); se apenas a chuva for válida, chuva ≥ 0,50. Os demais casos ficam em impermeável ou solo exposto (102). |
| 3 · raster 03 | Forração vegetal (101) sobre vias passa a impermeável ou solo exposto (102). Sobrepor campo alagado e área pantanosa (11) da banda original do MapBiomas e edificações (103) do Google Open Buildings fora da máscara de água. A água (33) do vetor SEDUH/Geoportal prevalece sobre as demais classes, preservando formação florestal (3) e formação savânica (4). Ao final, nas UCs de proteção integral, forração vegetal (101) passa a formação savânica (4) e impermeável ou solo exposto (102) passa a formação campestre (12). Vias servem à limpeza. |
| 4 · raster 04, final | Na categoria `risco=2`, “Ausência de Cerrado Nativo” do ZEE-DF, formação florestal (3) e formação savânica (4) passam a vegetação intraurbana (100), e formação campestre (12) a forração vegetal (101). As demais classes permanecem. |

Com as duas datas válidas, a etapa 01 usa a média aritmética por pixel. Com uma única data válida, usa o NDVI disponível. Tanto os valores como os limites são comparados em float32. Sem data válida, o pixel é NoData (255). A classe residual (100) recebe os pixels válidos abaixo do menor corte.

| Classe | Intervalo do NDVI | Fórmula do limite inferior |
| --- | --- | --- |
| Formação campestre (12) | 0,5582746239843752 ≤ NDVI < 0,6263072517078357 | Média + desvio padrão |
| Formação savânica (4) | 0,6263072517078357 ≤ NDVI < 0,7354611318541137 | Média |
| Formação florestal (3) | NDVI ≥ 0,7354611318541137 | Média − desvio padrão |

As três estatísticas vêm dos arquivos `form_campestre_estatisticas_ndvi.csv`, `form_savanica_estatisticas_ndvi.csv` e `form_florestal_estatisticas_ndvi.csv` em `02_Tabela`. A média e o desvio da vegetação nativa agregada não entram nos três cortes. A aplicação dos cortes ao NDVI médio histórico reproduziu integralmente os 57.826.223 pixels classificados do intermediário `veg_cerrado_3m_classificado_corrigido.tif`. Entre as entradas atuais com as duas datas válidas, 117.363.808 pixels coincidiram com o NDVI médio histórico. O raster histórico de uso do solo `uso_cobertura_final_v01.tif` combina outras fontes, e a reprodução do intermediário de NDVI não estabelece toda a linhagem desse raster.

A ordem completa de atribuições está no código e no relatório JSON gerado. Vetores são rasterizados com `ALL_TOUCHED=TRUE`. A classe do MapBiomas é transferida por vizinho mais próximo.

## Entradas e proveniência das cores

- NDVI PlanetScope de chuva (17/01/2026) e seca (30/07/2026): variáveis espectrais e grade de 3 m.
- MapBiomas local identificado como 2025, 10 m: referências cartográficas e campo alagado e área pantanosa (11).
- `01_Base/vetores/05_AVUs/AVUs_Bacia do Paranoá_Final.shp`: vetor local de Áreas Verdes Urbanas. O filtro `AVUs = 'UC' AND Grupo = 'UC - Proteção Integral'` selecionou 16 feições para a etapa 3.
- ZEE-DF: cobertura vegetal para referências e risco de perda de vegetação nativa para a etapa 4.
- Google [Open Buildings](https://sites.research.google/gr/open-buildings/): edificações; OpenStreetMap: vias; SEDUH via Geoportal: massas d'água. Os arquivos vetoriais locais estão listados no script.
- `uso do solo.qml`: cores do raster final e das interseções. A classe residual (100) da etapa 1 usa cinza claro `#e8e8e8` no GeoTIFF, no mapa e na legenda. `uso do solo mapbiomas.qml`: cores do mapa MapBiomas e dos gráficos NDVI. `paletas_identificacao.py`: paletas derivadas para cobertura vegetal e risco do ZEE-DF. O QML MapBiomas não possui cor para lavoura perene (36); a visualização usa `#c0a77a` como cor complementar documentada.

## Reproduzir localmente

Requer Python com GDAL/OGR, NumPy e Pillow, como o ambiente Python do QGIS. As entradas ficam fora do Git em `02 BASE DE DADOS`. O script verifica arquivos, CRS, resolução e alinhamento e recusa sobrescrever uma saída existente.

```powershell
python scripts/identificacao/classificar_fitofisionomias_3m.py `
  --base "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS" `
  --output "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\02_Análises\03_Ecologia\03_Fitofisionomia\03_Raster\03_fitofisionomia\fitofisionomias_proxy_ndvi_3m_etapa_04.tif" `
  --stages-dir "C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\02_Análises\03_Ecologia\03_Fitofisionomia\03_Raster\03_fitofisionomia"
```

`--stages-dir` é opcional; com ele, também são gravadas as etapas 01–03. O script nunca lê classificações anteriores. Para republicar o site, `exportar_fitofisionomias_web.py` aceita `--stages-dir` e `--final-raster` da reprodução ou `--raster-dir` com os quatro arquivos locais nomeados `etapa_01` a `etapa_04`. Também recebe `--risk`, `--samples`, `--qml` e `--output-dir` vazio. `atualizar_paletas_referencias.py` recolore os PNG paletizados de MapBiomas, ZEE-DF e interseções sem recalcular amostras ou geometrias.

O exportador cria quatro vistas gerais de aproximadamente 20 m, um GIF de quatro quadros, o mapa de risco do ZEE-DF e blocos PNG de 3 m em EPSG:3857 que o navegador carrega apenas em zoom próximo. Os GeoTIFFs integrais não são distribuídos pelo Git.

## Conferência

Os quatro rasters foram reproduzidos das entradas brutas e comparados com os GeoTIFFs da rodada adotada em todos os pixels. Os valores, a grade, o CRS, o NoData e a paleta coincidiram.

O raster 04 tem **117.365.300 pixels classificados** e 107.932.640 NoData. As áreas são calculadas na grade nativa com 9 m² por pixel e excluem NoData. A visão geral do site é reamostrada para visualização.

| Classe | Pixels | Área (ha) |
| --- | ---: | ---: |
| Formação florestal (3) | 7.386.448 | 6.647,80 |
| Formação savânica (4) | 26.692.251 | 24.023,03 |
| Campo alagado e área pantanosa (11) | 1.701.771 | 1.531,59 |
| Formação campestre (12) | 17.236.857 | 15.513,17 |
| Água (33) | 5.195.517 | 4.675,97 |
| Vegetação intraurbana (100) | 7.706.966 | 6.936,27 |
| Forração vegetal (101) | 16.903.382 | 15.213,04 |
| Impermeável ou solo exposto (102) | 25.443.004 | 22.898,70 |
| Edificações (103) | 9.099.104 | 8.189,19 |

## Limitações

- Formação campestre (12) e pastagem (15) se misturam em NDVI. O corte não estabelece origem nativa nem composição florística.
- Duas datas não descrevem o ciclo fenológico completo. UDM2 não foi aplicada aos mosaicos; nuvens e sombras podem afetar pixels.
- Células de 3 m não equivalem a acurácia temática de 3 m. Campo alagado e área pantanosa (11) herda limites da fonte MapBiomas de 10 m.
- Forração vegetal (101) indica condições mais compatíveis com forração vegetal ou trechos de formações vegetais fora dos limiares de NDVI. Impermeável ou solo exposto (102) indica condições mais compatíveis com superfícies impermeabilizadas ou solo exposto. As duas classes são aproximações e podem divergir da cobertura real do terreno.
- Vias são linhas sem largura uniforme. Os vetores de edificações e água e o ZEE-DF têm incertezas próprias de data e posição.
- A imagem de satélite opcional do site é Sentinel-2 cloudless 2025 de 10 m, usada apenas para orientação visual; não é a imagem PlanetScope classificada.


## Histórico dos cortes de NDVI

| Rodada | Método e limiares |
| --- | --- |
| Inicial (v1) | Com duas datas válidas, formação florestal (3) se seca ≥ 0,70. Formação savânica (4) se 0,48 ≤ seca < 0,70 e média ≥ 0,58. Formação campestre (12) se 0,20 ≤ seca < 0,46 e 0,38 ≤ chuva < 0,62. Em data única, seca usa os mesmos intervalos secos e chuva usa 0,38–<0,62, 0,65–<0,79 e ≥ 0,79 para campestre, savânica e florestal, respectivamente. |
| v2 final | Desvio padrão amostral dos valores válidos de seca e chuva reunidos em cada interseção. Limites inferiores 0,5765370662151971 para formação campestre (12), 0,6418580985614883 para formação savânica (4) e 0,7282830052276217 para formação florestal (3). Florestal usa a mediana dos valores reunidos (0,7969018816947937) menos o desvio padrão (0,06861887646717196). |
| Primeiro teste v3 | Desvio padrão amostral calculado sobre a média seca–chuva de cada pixel das interseções. Limites inferiores 0,5185165380148051 para formação campestre (12), 0,6418583869093903 para formação savânica (4) e 0,7354611272062169 para formação florestal (3). |
| v3 adotada | Recuperação dos cortes históricos da etapa de NDVI médio. Aplicam-se os limiares e regras da tabela em Etapas adotadas. Esta é a base dos arquivos atuais sem sufixo de versão. |


## Fragmentos, métricas e tipologias de AVU

O raster 04 fornece a máscara das classes 3, 4, 11, 12 e 100. Pixels unidos por lado ou vértice recebem um único ID, ainda que de formações diferentes. Os cinco percentuais usam a contagem de pixels e a formação predominante recebe o maior percentual ou Empate. A conferência rasterizou as geometrias de volta à grade e confirmou a máscara, as áreas, os percentuais e a vizinhança.

Para a AVU, o cruzamento exige sobreposição de área positiva e vale para o fragmento inteiro. A categoria Aviso reúne sobreposições com duas ou mais categorias entre UC, parque urbano e Agrossistemas não intensivos. APP é usada na ausência dessas três categorias. O GeoPackage preserva os indicadores de sobreposição usados na classificação.

As duas bordas usam os mesmos fragmentos. O recuo usa GEOS 3.14.1, com 30 segmentos por quadrante. Os fragmentos com pelo menos 5.000 coordenadas foram divididos em blocos centrais de 2.000 m com margem de 6 m além da borda solicitada. As métricas por fragmento e por paisagem são calculadas no R 4.5.3 pela função oficial MK_Fragmentation da revisão [0010946](https://github.com/connectscape/Makurhini/blob/0010946ab2eef7f8d2bc4935f369869fc4c58671/R/MK_fragmentation.R). A função recebe as áreas e os perímetros já calculados, em metros quadrados e metros. A área da paisagem vem do limite da bacia reprojetado para EPSG:31983. Os gráficos usam os mesmos núcleos e métricas dos GeoPackages e CSVs.

O script local `calcular_metricas_fragmentacao.py` fica na pasta `01_Fragmentação`, junto dos produtos, com uma cópia correspondente [versionada neste diretório](calcular_metricas_fragmentacao.py). Execute com o Python do QGIS com Shapely e Matplotlib e o R com magrittr. Informe o GeoPackage de fragmentos, o limite da bacia, a fonte da revisão citada do Makurhini, o executável Rscript e uma pasta de saída existente sem resultados prévios para a borda escolhida. Execute com `--borda 45` e depois com `--borda 90`. Use `--help` para ver os argumentos. O cálculo das métricas preserva a AVU e não atribui `cat_iv`; aplique depois o classificador de IV abaixo.

## Elementos da infraestrutura verde

O programa [classificar_elementos_iv.py](classificar_elementos_iv.py) aplica a classificação aprovada em 10/11/2026. Usa a camada `metricas_fragmentos`, os indicadores `avu_uc_pi`, `avu_parque` e `avu_agro`, a área total `Area` e o índice `ShapeIndex`. Os dois cenários têm os mesmos 50.047 fragmentos e 54.651,8637 ha. As geometrias e os atributos usados na IV são comparados por ID antes de compartilhar a classificação; as métricas de núcleo diferem com a borda.

Para a IV, a única APP é a camada `dissolvido` de `01_Base/vetores/05_AVUs/APP_Buffer_hid_Bacia_Paranoa_disso.gpkg`, em EPSG:31983. Exige-se interseção de área positiva. O campo histórico `avu_app`, usado na classificação de AVU com outras fontes, não é usado para decidir a IV.

Aplica-se a primeira regra atendida pelo fragmento inteiro:

1. **Hub 1:** exclusivamente os dois maiores fragmentos, pela área total, entre aqueles com sobreposição a UC de proteção integral. IDs atuais: 17964 e 50034.
2. **Hub 2:** parques urbanos sem sobreposição à APP indicada, ainda sem classe.
3. **Link:** fragmentos com APP ainda sem classe. Se `ShapeIndex > 25`, recebem **Hub 2**. O limite é estrito: 25 permanece Link.
4. **Site 1:** Agrossistemas não intensivos ainda sem classe.
5. **Site 2:** todos os demais.

O ensaio anterior de herança de Hub por proximidade de 300 m foi retirado da classificação adotada. Hub 1 permanece limitado aos dois fragmentos definidos. O fragmento 27675 é o único candidato a Link com `ShapeIndex > 25` nesta base (35,4834) e passa a Hub 2.

| Classe | Fragmentos, 45 m e 90 m | Área (ha) | Cor do uso do solo reutilizada |
| --- | ---: | ---: | --- |
| Hub 1 | 2 | 39.561,0381 | Formação florestal (3), `#4b6a40` |
| Hub 2 | 933 | 2.550,9132 | Formação savânica (4), `#86a58f` |
| Link | 1.185 | 5.381,4780 | Campo alagado e área pantanosa (11), `#3e5972` |
| Site 1 | 751 | 280,4067 | Formação campestre (12), `#d0a55f` |
| Site 2 | 47.176 | 6.878,0277 | Forração vegetal (101), `#c4cc95` |
| **Total** | **50.047** | **54.651,8637** | |

A paleta vem de `uso do solo.qml`. Reutilizar suas cores não estabelece equivalência temática entre classes de cobertura e funções da IV. O mapa interativo consulta a classe da imagem de visualização, reamostrada com vizinho mais próximo para aproximadamente 20 m em EPSG:3857. Ele representa ambos os cenários, que possuem a mesma IV. As áreas da tabela vêm da geometria integral de 3 m, e não da imagem web.

Exemplo de aplicação aos dois GeoPackages existentes, executado da raiz do repositório no PowerShell:

```powershell
$baseDados = 'C:/Users/sampa/OneDrive - unb.br/02 BASE DE DADOS'
$fragmentacao = "$baseDados/02_Análises/03_Ecologia/01_Fragmentação"
$fitofisionomia = "$baseDados/02_Análises/03_Ecologia/03_Fitofisionomia"
& 'C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat' scripts/identificacao/classificar_elementos_iv.py `
  --metrics "$fragmentacao/MK_Fragmentation_Bacia_Paranoa_45m_AVU_PatchMetrics.gpkg" "$fragmentacao/MK_Fragmentation_Bacia_Paranoa_90m_AVU_PatchMetrics.gpkg" `
  --app "$baseDados/01_Base/vetores/05_AVUs/APP_Buffer_hid_Bacia_Paranoa_disso.gpkg" `
  --apply
```

Sem `--apply`, o script apenas calcula e informa as contagens e áreas. Para exportar o mapa, acrescente `--raster` com a etapa 04, `--qml` com a paleta de uso do solo e `--map-output` com um destino PNG inexistente. O JSON impresso informa os limites e a legenda que correspondem à imagem. Na publicação, copie a imagem para `dados-mapas/iv.png` e sincronize a entrada `iv` de `dados-mapas/catalogo.json`. O script verifica as áreas rasterizadas por classe e, na gravação de `cat_iv`, confere que as demais colunas e geometrias permaneceram iguais.

## Correspondência dos produtos publicados

Alterações nos dados da identificação devem atualizar conjuntamente os scripts, este método, os valores e legendas de `identificacao.html`, as imagens e catálogos de `dados-mapas`, os mapas interativos e os links da árvore em `index.html`. Os GeoTIFFs e GeoPackages científicos integrais permanecem nas pastas de dados locais; o Git distribui o código, os métodos e as representações para consulta.

`exportar_fitofisionomias_web.py` regenera, a partir das quatro etapas atuais, os quatro PNGs, o GIF com quatro quadros de 1,5 s e os blocos de detalhe de 3 m, além do manifesto e das análises adicionais. O manifesto inclui uma revisão calculada das imagens para evitar que o navegador reaproveite imagens de uma execução anterior. `dados-mapas/uso.png` corresponde ao PNG da etapa 04, com os mesmos limites e classes no catálogo do mapa geral. A nota de revisão do uso do solo permanece visível na página: atualizar suas representações não resolve a diferença metodológica ainda pendente em relação ao uso do solo histórico.
