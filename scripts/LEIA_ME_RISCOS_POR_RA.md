# Riscos por Região Administrativa

A [tabela por RA](../mapa-riscos.html#riscos-por-ra) resume os resultados da rodada v01 do diagnóstico por fragmento.

| Entrada | Uso |
| --- | --- |
| `regioes_administrativas.shp` | Geometrias completas, códigos e nomes das RAs. |
| `Bacia_Paranoa_MERGE_IPE_DF_2023.shp` | Limite da bacia usado para recortar as RAs. |
| `Diagnostico_RISCO_v01.gpkg` | Geometrias e indicadores calculados por fragmento. |

O cruzamento é feito em SIRGAS 2000 / UTM 23S (EPSG:31983). O limite da bacia é reprojetado quando necessário. A tabela inclui as RAs com interseção de área superior a 0,01 m² com a bacia. Na coluna **RA inteiramente dentro da bacia**, a resposta é **Sim** quando o limite da bacia cobre a RA completa, com tolerância de 0,01 m² para resíduos numéricos. A coluna usa apenas **Sim** ou **Não**.

Um fragmento pode interceptar mais de uma RA. Cada interseção contribui com sua área para a respectiva RA. A média de um indicador numérico é ponderada por essa área, usando apenas fragmentos com valor válido. Mínimo e máximo referem-se aos valores originais desses fragmentos. As porcentagens por classe usam como denominador a área classificada. A coluna **Área com dado válido (%)** usa como denominador toda a área dos fragmentos dentro da RA. As medidas da renda descrevem o indicador atribuído aos fragmentos e sua distribuição espacial.

## Atualizar o resultado

Execute com o Python do QGIS e as bibliotecas GDAL e Shapely 2. Mantenha os arquivos auxiliares dos shapefiles na mesma pasta. O comando escreve JSON na saída padrão.

```sh
python scripts/exportar_riscos_por_ra.py --ras "caminho/regioes_administrativas.shp" --bacia "caminho/Bacia_Paranoa_MERGE_IPE_DF_2023.shp" --fragmentos "caminho/Diagnostico_RISCO_v01.gpkg"
```

Salve a saída em UTF-8 como `dados-mapas/riscos-por-ra.json` para atualizar a tabela no site.
