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

A [seção Por RA, no mapa interativo geral](../mapa.html#riscos-por-ra) resume todos os indicadores de Riscos por Região Administrativa. A tabela usa o recorte da RA pela bacia e informa se a RA completa está dentro dela. [Método de agregação e fontes](../scripts/LEIA_ME_RISCOS_POR_RA.md).

## Contexto geral de Riscos

O controle **Visualização** alterna entre **Nos fragmentos** e **Contexto geral**. A primeira vista mostra os valores do diagnóstico, incluindo as classes atribuídas aos fragmentos. A segunda usa os arquivos de entrada listados na [metodologia de Riscos](../diagnostico.html#camadas).

- Temperatura, mitigação térmica, umidade e inundação são apresentadas nas faixas cartográficas do catálogo, em uma grade de 50 m em Web Mercator com reamostragem por vizinho mais próximo. As faixas de temperatura, HM e umidade são constantes por tipo de dado para facilitar a comparação entre cenários.
- A zona de ilha de calor é rasterizada em uma grade de 50 m. As edificações são representadas em 20 m, considerando as células tocadas pelas geometrias para manter pequenas feições visíveis. A área colorida no mapa serve à visualização.
- O contexto da renda usa o campo `V06004` dos setores censitários com dado disponível, em faixas de salários mínimos pela referência de R$ 1.212 da rodada de 2022.

As definições e os limites das imagens estão em `dados-mapas/contexto-riscos.json`. Para reexportar uma imagem com o Python do QGIS, use GDAL e NumPy.

```sh
python scripts/exportar_contexto_riscos.py temp_dia "caminho/T_air_bacia_paranoa_v6_factors.tif" dados-mapas/contexto/temp_dia.png
```

O comando imprime a extensão projetada da imagem, na ordem oeste, sul, leste e norte. Registre-a em `bounds` na entrada do indicador.
