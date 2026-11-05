# Condicionantes

## Momentos da Água

O script [momentos_agua_paranoa.py](momentos_agua_paranoa.py) é a versão 1.1.1 registrada na proveniência de `areas_momentos.csv`. Ele reúne terreno, solos, superfícies e variáveis hidrológicas para estimar os momentos de fonte, condução e acomodação. A classificação e o grau de definição são exploratórios. A saída inclui diagnósticos e limites da análise.

### Ambiente e configuração

Use o Python da instalação do QGIS para Windows, com GDAL/OGR, GRASS GIS, NumPy e SciPy. A configuração da rodada usa QGIS 3.44.15. Execute os comandos abaixo na pasta deste guia, em um terminal com o ambiente Python do QGIS.

```sh
python -c "import runpy; runpy.run_path('momentos_agua_paranoa.py')['config']()"
```

O comando cria `parametros_momentos_agua.json` na pasta do script se o arquivo ainda estiver ausente. Ajuste `pasta` para uma área de trabalho com as entradas padronizadas e `qgis_root` para a instalação do QGIS. A rodada publicada usou os parâmetros analíticos padrão. Os caminhos e nomes de entradas são configuráveis em `arquivos`. A chave `versao` no JSON identifica a configuração. O próprio script informa sua versão em `proveniencia_e_limites.json`.

| Entrada padrão | Uso |
| --- | --- |
| `bacia_paranoa_merge_ipe_df_2023.gpkg` | Recorte da Bacia do Paranoá. |
| `CURVA_DE_NIVEL_COMPLETA_Bacia_Paranoa.gpkg` | Geração do modelo de elevação. |
| `uso_cobertura_final_v01.tif` | Classes de uso e cobertura do solo. |
| `Construções Bacia do Paranoá.shp` | Superfícies edificadas. |
| `Vias_OSM_Bacia_Paranoa.shp` | Tipos de vias e condicionamento do terreno. |
| `Pedo_IBGE_Bacia_Paranoa.shp` e `classes_de_solos_CORRIGIDA.shp` | Integração pedológica. |
| `POCOS_SIAGAS_Bacia_Paranoa.gpkg` | Dados de poços para avaliar o ajuste da estimativa do lençol. |

A etapa de textura usa rasters do SoilGrids via GDAL. Mantenha junto aos shapefiles seus arquivos auxiliares.

### Execução

```sh
python momentos_agua_paranoa.py --piloto
python momentos_agua_paranoa.py --run
```

O piloto trabalha em uma área de teste e grava em `TESTE_PILOTO`. A rodada completa grava em `RESULTADOS_MOMENTOS_AGUA`, dentro da pasta de trabalho. Use uma pasta de trabalho separada para cada cenário que queira preservar. Ao concluir, confira `CONCLUIDO.txt`, `areas_momentos.csv`, `diagnostico_modelo.json` e `proveniencia_e_limites.json`. A tabela do relatório usa `area_ha`, por momento e grau de definição.

## Potencial de Recuperação Ecológica

O relatório parte da camada pronta `PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp`. O código [resumir_pre.py](resumir_pre.py) usa GDAL/OGR para contar as feições por `cat_pdot20` e somar as áreas geométricas em hectares, em SIRGAS 2000 / UTM 23S (EPSG:31983). A origem primária da classificação da camada ainda precisa ser documentada.

```sh
python resumir_pre.py "caminho/PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp"
```

O CSV sai no terminal. A área é a soma das feições da classe, e a tabela do site apresenta os valores arredondados a duas casas decimais.
