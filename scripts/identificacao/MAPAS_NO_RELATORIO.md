# Mapas nas seções de identificação

As seções Métricas de forma, Tipologias de AVU e Elementos da IV apresentam seus próprios mapas depois das tabelas. A navegação principal permanece na página de identificação. Cada mapa mantém seu enquadramento e suas camadas ao alternar entre as seções.

`identificacao-mapas.js` usa os PNGs e o catálogo já publicados para tipologias e IV (aproximadamente 20 m), sem recalcular a classificação ou os indicadores. A legenda e a consulta desses dois temas vêm de `dados-mapas/catalogo.json`.

O mapa de métricas permite selecionar Area, CA, CAPercent, Perimeter, EdgePercent, PARA, ShapeIndex e FRAC. `identificacao-metricas-dados.js` carrega uma única vez os mesmos CSVs originais usados na consulta por ID. `identificacao-metricas-mapa.js` associa cada ID aos valores, colore o mapa e atualiza legenda, unidades e popup com ID/valor. CA, CAPercent e EdgePercent permitem escolher 45/90 m; o controle fica desativado nas métricas iguais entre cenários. Nenhuma métrica ou geometria científica é recalculada.

Área total e área de núcleo usam os limites de 1, 10 e 100 ha; percentuais usam 25, 50 e 75%. Zero tem classe cinza própria nas três métricas dependentes da borda. As demais métricas usam quartis da população completa de 46.876 fragmentos (limites inclusivos superiores, postos ceil(q*N), limites repetidos removidos). As faixas servem apenas à visualização e não alteram os critérios da IV. PARA mantém a razão Area / Perimeter efetivamente executada. O popup apresenta valores originais em m²/m/% conforme a métrica, com quatro casas.

`dados-mapas/identificacao/metricas-mapa/fragmentos-ids.png` codifica `id_frag = R*256+G`, fundo zero e B zero. O exportador rasteriza os IDs na grade nativa de 3 m, confere a área de todos os 46.876 fragmentos e reprojeta por vizinho mais próximo, sem aproximação do transformador, para 20 m em EPSG:3857. O navegador apenas recolore essa representação. Fragmentos menores podem não aparecer na escala web; a consulta por ID continua abrangendo todos. As cores de CA representam um atributo do fragmento inteiro e **não delimitam espacialmente os núcleos**. O PNG antigo `dados-mapas/metricas.png` permanece disponível para o atlas geral.

## Contornos de AVU e APP

O mapa de tipologias distingue o preenchimento dos fragmentos classificados dos contornos dos polígonos de referência. As categorias podem ser ativadas individualmente. UCs, parques e agrossistemas aparecem inicialmente; APPs são carregadas quando selecionadas. O clique no contorno mostra categoria, nome quando disponível, arquivo e ID da feição original.

As fontes são as mesmas da classificação das tipologias:

| Fonte em `01_Base/vetores/05_AVUs` | Feições | CRS original |
| --- | ---: | --- |
| `AVUs_Bacia do Paranoá_Final.shp` | 290 | EPSG:31983 |
| `APP_Nascente_Bacia Paranoa.shp` | 488 | EPSG:3857 |
| `APP_Buffer_hid_Bacia_Paranoa.shp` | 1.438 | EPSG:31983 |

As 290 AVUs são distribuídas em proteção integral (16), uso sustentável (32), parques urbanos (21) e agrossistemas não intensivos (221). Os arquivos são abertos somente para leitura. A exportação preserva todas as feições, partes, anéis e vértices, sem simplificação ou recorte adicional. As coordenadas são reprojetadas para EPSG:4326 e serializadas com precisão de dez casas decimais. A validação mede o erro após a reprojeção inversa para EPSG:31983; o limite é 2 mm e o maior erro desta entrega foi 0,000129 m.

Agrossistemas não intensivos, APPs de nascentes e APPs de hidrografia usam contornos contínuos no mapa e nas amostras da legenda. Cores e geometrias foram preservadas. O traço de UC de uso sustentável continua distinguindo essa categoria.

Os GeoJSONs comprimidos e seu manifesto ficam em `dados-mapas/identificacao/limites-avu/`. O manifesto registra contagens, SHA-256 dos arquivos publicados, das fontes e do exportador. Somente categoria, nome, fonte e ID são incluídos nos atributos web. Os limites originais podem ultrapassar os fragmentos classificados: o contorno não altera a regra de atribuição ao fragmento inteiro.

A APP hidrográfica dissolvida empregada na classificação dos elementos da IV continua sendo uma entrada específica desse procedimento. Os contornos de APP do mapa de tipologias correspondem às duas fontes históricas da classificação de AVU listadas acima.

## Reprodução e conferência

No Python do QGIS, execute com `--base` apontando para a raiz local `02 BASE DE DADOS` e `--output` para uma pasta nova e vazia:

```powershell
python-qgis-ltr.bat scripts/identificacao/exportar_limites_avu_web.py --base "CAMINHO/02 BASE DE DADOS" --output "CAMINHO/saida-nova"
python-qgis-ltr.bat scripts/identificacao/validar_limites_avu_web.py --base "CAMINHO/02 BASE DE DADOS" --output "CAMINHO/saida-nova"
python-qgis-ltr.bat scripts/identificacao/exportar_ids_metricas_web.py --base "CAMINHO/02 BASE DE DADOS" --output "CAMINHO/saida-ids-nova"
python-qgis-ltr.bat scripts/identificacao/validar_ids_metricas_web.py --base "CAMINHO/02 BASE DE DADOS"
```

A conferência compara todos os polígonos web com suas feições de origem, verifica atributos, tipo geométrico, validade, sequência de coordenadas e hashes. O validador geral `validar_identificacao.py` continua conferindo os produtos científicos e a estrutura HTML. No navegador, verifique a posição após a tabela, as três legendas, a consulta por clique, os controles independentes, as seis opções de contorno e o retorno entre abas sem sair de `identificacao.html`.
