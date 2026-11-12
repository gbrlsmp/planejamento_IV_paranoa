# Mapas nas seções de identificação

As seções Métricas de forma, Tipologias de AVU e Elementos da IV apresentam seus próprios mapas depois das tabelas. A navegação principal permanece na página de identificação. Cada mapa mantém seu enquadramento e suas camadas ao alternar entre as seções.

`identificacao-mapas.js` usa os PNGs e o catálogo já publicados, sem recalcular a classificação ou os indicadores. A legenda e a consulta por clique vêm de `dados-mapas/catalogo.json`. A área total dos fragmentos é representada em aproximadamente 50 m; as tipologias e os elementos da IV, em aproximadamente 20 m. O mapa de área total não representa os núcleos dos cenários de 45 m e 90 m.

## Contornos de AVU e APP

O mapa de tipologias distingue o preenchimento dos fragmentos classificados dos contornos dos polígonos de referência. As categorias podem ser ativadas individualmente. UCs, parques e agrossistemas aparecem inicialmente; APPs são carregadas quando selecionadas. O clique no contorno mostra categoria, nome quando disponível, arquivo e ID da feição original.

As fontes são as mesmas da classificação das tipologias:

| Fonte em `01_Base/vetores/05_AVUs` | Feições | CRS original |
| --- | ---: | --- |
| `AVUs_Bacia do Paranoá_Final.shp` | 290 | EPSG:31983 |
| `APP_Nascente_Bacia Paranoa.shp` | 488 | EPSG:3857 |
| `APP_Buffer_hid_Bacia_Paranoa.shp` | 1.438 | EPSG:31983 |

As 290 AVUs são distribuídas em proteção integral (16), uso sustentável (32), parques urbanos (21) e agrossistemas não intensivos (221). Os arquivos são abertos somente para leitura. A exportação preserva todas as feições, partes, anéis e vértices, sem simplificação ou recorte adicional. As coordenadas são reprojetadas para EPSG:4326 e serializadas com precisão de dez casas decimais. A validação mede o erro após a reprojeção inversa para EPSG:31983; o limite é 2 mm e o maior erro desta entrega foi 0,000129 m.

Os GeoJSONs comprimidos e seu manifesto ficam em `dados-mapas/identificacao/limites-avu/`. O manifesto registra contagens, SHA-256 dos arquivos publicados, das fontes e do exportador. Somente categoria, nome, fonte e ID são incluídos nos atributos web. Os limites originais podem ultrapassar os fragmentos classificados: o contorno não altera a regra de atribuição ao fragmento inteiro.

A APP hidrográfica dissolvida empregada na classificação dos elementos da IV continua sendo uma entrada específica desse procedimento. Os contornos de APP do mapa de tipologias correspondem às duas fontes históricas da classificação de AVU listadas acima.

## Reprodução e conferência

No Python do QGIS, execute com `--base` apontando para a raiz local `02 BASE DE DADOS` e `--output` para uma pasta nova e vazia:

```powershell
python-qgis-ltr.bat scripts/identificacao/exportar_limites_avu_web.py --base "CAMINHO/02 BASE DE DADOS" --output "CAMINHO/saida-nova"
python-qgis-ltr.bat scripts/identificacao/validar_limites_avu_web.py --base "CAMINHO/02 BASE DE DADOS" --output "CAMINHO/saida-nova"
```

A conferência compara todos os polígonos web com suas feições de origem, verifica atributos, tipo geométrico, validade, sequência de coordenadas e hashes. O validador geral `validar_identificacao.py` continua conferindo os produtos científicos e a estrutura HTML. No navegador, verifique a posição após a tabela, as três legendas, a consulta por clique, os controles independentes, as seis opções de contorno e o retorno entre abas sem sair de `identificacao.html`.
