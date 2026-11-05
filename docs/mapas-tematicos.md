# Mapas temáticos

O mapa geral combina as camadas do catálogo com o limite da bacia, as massas d’água, as RAs e os indicadores de Riscos. Cada tema do relatório tem links para sua metodologia e para a vista de mapa.

| Tema | Dado de origem | Leitura no mapa |
| --- | --- | --- |
| Uso e cobertura do solo | `uso_cobertura_MapBiomas_Bacia_Paranoa.shp`, MapBiomas 10 m | Classes do relatório. Os dois últimos dígitos do campo `classe` identificam o código de uso. |
| Métricas de forma | `MK_Fragmentation_Bacia_Paranoa_45m_PatchMetrics.shp` | Área do fragmento em faixas cartográficas de 1, 10 e 100 ha, calculadas com o campo `Area` em m². |
| Momentos da Água | `momento_dominante.tif`, análise do Paranoá | Fonte, condução e acomodação. |
| Potencial de recuperação ecológica | `PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp`, SEDUH-DF | Classes do campo `cat_pdot20`. |

Os vetores são rasterizados pelo centro da célula. As quatro imagens são publicadas em uma grade de 50 m em Web Mercator (EPSG:3857), com reamostragem pelo vizinho mais próximo. Elas servem à leitura cartográfica. Para cálculos de área e cruzamentos por fragmento, use as camadas originais. Cada imagem tem sua extensão em metros projetados e sua legenda em `dados-mapas/catalogo.json`.

## Atualizar uma camada

Execute com o Python do QGIS, com GDAL e NumPy. Os temas disponíveis são `uso`, `metricas`, `momentos` e `pre`.

```sh
python scripts/exportar_camadas_tematicas.py momentos "caminho/momento_dominante.tif" dados-mapas/momentos.png
```

Copie para `bounds` no catálogo os limites projetados que o comando imprime, na ordem oeste, sul, leste e norte. Use os mesmos nomes de tema para o PNG e para a entrada no catálogo.

## Riscos por Região Administrativa

A [vista Por RA](../riscos-por-ra.html) resume todos os indicadores de Riscos por Região Administrativa. A tabela usa o recorte da RA pela bacia e informa se a RA completa está dentro dela. [Método de agregação e fontes](../scripts/LEIA_ME_RISCOS_POR_RA.md).
