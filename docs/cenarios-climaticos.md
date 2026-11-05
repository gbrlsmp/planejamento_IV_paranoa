# Comparação de cenários climáticos

A metodologia de Riscos apresenta comparativos e mapas das camadas integrais de temperatura do ar e HM da rodada InVEST Urban Cooling v6. Esses mapas mostram as entradas do diagnóstico, antes das estatísticas por fragmento.

## Cenários e média

- **Dia**: saída do método `factors`.
- **Noite**: saída do método `intensity`; os arquivos originais preservam a grafia `intenssity`.
- **Média**: `(dia + noite) / 2`, calculada célula a célula, separadamente para temperatura e HM.

A média foi verificada nas seis camadas originais: a maior diferença absoluta para essa expressão foi 0,000000954 °C em temperatura e 0,000000030 em HM, compatível com arredondamento de ponto flutuante. A média entre dois cenários modelados não corresponde a uma média observada de 24 horas.

O HM é um índice de mitigação; não é temperatura nem porcentagem de redução do calor. O HM local combina capacidade de resfriamento e influência de áreas verdes próximas. O diagnóstico consulta HM em faixa externa de 5 m do fragmento; a modelagem usa distância de resfriamento de 450 m. Essas duas distâncias têm funções diferentes.

## Duas formas de representar

**Degradê contínuo:** mínimo e máximo comuns aos três cenários de cada indicador. A mesma cor representa o mesmo valor, permitindo a comparação direta. Os mapas pequenos do comparativo também usam essa escala, a mesma extensão e a mesma orientação.

**Cinco classes:** intervalos de igual amplitude calculados separadamente para cada raster integral: `corte_i = mínimo + i × (máximo − mínimo) / 5`. A largura numérica é igual dentro de um cenário, mas a área de cada classe pode ser diferente. Os cortes entre cenários também podem ser diferentes; comparar somente o nome ou a cor da classe não equivale a comparar o mesmo valor absoluto.

Temperatura: **base, boa, média, ruim e muito ruim**, da menor para a maior temperatura. Base é a faixa mais fria observada naquele cenário, não a temperatura de referência de entrada do InVEST nem um ideal de conforto térmico.

HM: **base, boa, média, ruim e muito ruim**, da maior para a menor mitigação. Os nomes descrevem posições relativas neste estudo; não designam diretamente refúgios climáticos ou ilhas de calor. Essas interpretações dependem dos demais critérios da matriz.

O mínimo é incluído na primeira faixa numérica. Cada corte interno pertence à faixa numérica inferior: `[mínimo, corte1]`, `(corte1, corte2]`, etc. O arredondamento ocorre apenas na apresentação (uma casa decimal em temperatura, quatro em HM). A classificação usa os cortes originais de dupla precisão. As faixas da legenda podem apresentar o mesmo valor arredondado na transição; isso não produz sobreposição nos cálculos. Os cortes completos estão no [catálogo](../dados-mapas/clima/catalogo.json).

## Faixas e área válida

As porcentagens seguintes foram calculadas lendo **todas** as células válidas dos rasters originais de 3 m, sem amostragem. Na noite, a extensão válida é ligeiramente maior: 105.639,3 ha, contra 105.615,5 ha em dia e média. Cada porcentagem usa a área válida do seu próprio raster.

### Temperatura do ar · dia

Fonte: `T_air_bacia_paranoa_v6_factors.tif`.

| Classe | Faixa exibida °C | Área válida |
| --- | --- | --- |
| Base | 25,0 a 26,3 | 37,9% |
| Boa | 26,3 a 27,7 | 20,0% |
| Média | 27,7 a 29,1 | 16,1% |
| Ruim | 29,1 a 30,5 | 19,4% |
| Muito ruim | 30,5 a 31,8 | 6,7% |

### Temperatura do ar · noite

Fonte: `T_air_bacia_paranoa_v6_intenssity.tif`.

| Classe | Faixa exibida °C | Área válida |
| --- | --- | --- |
| Base | 22,1 a 23,0 | 75,7% |
| Boa | 23,0 a 24,0 | 15,1% |
| Média | 24,0 a 24,9 | 5,6% |
| Ruim | 24,9 a 25,9 | 2,5% |
| Muito ruim | 25,9 a 26,8 | 1,0% |

### Temperatura do ar · média

Fonte: `v6 - algebra/T_air_bacia_paranoa_v6_media.tif`.

| Classe | Faixa exibida °C | Área válida |
| --- | --- | --- |
| Base | 23,5 a 24,7 | 46,8% |
| Boa | 24,7 a 25,8 | 22,8% |
| Média | 25,8 a 26,9 | 19,3% |
| Ruim | 26,9 a 28,0 | 9,0% |
| Muito ruim | 28,0 a 29,1 | 2,2% |

### Mitigação térmica — HM · dia

Fonte: `hm_bacia_paranoa_v6_factors.tif`.

| Classe | Faixa exibida | Área válida |
| --- | --- | --- |
| Base | 0,6538 a 0,7972 | 19,4% |
| Boa | 0,5104 a 0,6538 | 35,7% |
| Média | 0,3669 a 0,5104 | 10,8% |
| Ruim | 0,2235 a 0,3669 | 14,1% |
| Muito ruim | 0,0801 a 0,2235 | 20,1% |

### Mitigação térmica — HM · noite

Fonte: `hm_bacia_paranoa_v6_intenssity.tif`.

| Classe | Faixa exibida | Área válida |
| --- | --- | --- |
| Base | 0,8946 a 1,0000 | 78,5% |
| Boa | 0,7891 a 0,8946 | 10,7% |
| Média | 0,6837 a 0,7891 | 8,1% |
| Ruim | 0,5782 a 0,6837 | 0,0% |
| Muito ruim | 0,4728 a 0,5782 | 2,7% |

### Mitigação térmica — HM · média

Fonte: `v6 - algebra/hm_bacia_paranoa_v6_media.tif`.

| Classe | Faixa exibida | Área válida |
| --- | --- | --- |
| Base | 0,7742 a 0,8986 | 53,7% |
| Boa | 0,6497 a 0,7742 | 15,0% |
| Média | 0,5253 a 0,6497 | 15,3% |
| Ruim | 0,4009 a 0,5253 | 10,8% |
| Muito ruim | 0,2764 a 0,4009 | 5,2% |

A faixa **ruim** de HM à noite não contém células nos rasters originais. A classe é mantida com 0%, preservando os intervalos iguais em vez de inventar ocorrências ou redistribuir os cortes.

## Comparação na mesma área

As médias espaciais do comparativo usam a interseção das máscaras válidas dos **seis** rasters: 117.350.582 células, ou 105.615,5238 ha. Excluem-se NoData, NaN e valores não finitos. Assim, a diferença entre os cenários não decorre de comparar extensões diferentes.

| Cenário | Temperatura média espacial | HM médio espacial |
| --- | --- | --- |
| Dia | 27,6 °C | 0,4858 |
| Noite | 22,7 °C | 0,9439 |
| Média | 25,1 °C | 0,7148 |

A diferença célula a célula dia − noite tem média de 4,9 °C (amplitude de 2,8 a 8,2 °C). A diferença HM noite − dia tem média de 0,4581 (amplitude de 0,1503 a 0,8574). São contrastes entre cenários modelados, não medições do ciclo diário. O [catálogo](../dados-mapas/clima/catalogo.json) conserva os valores completos, contagens e áreas por classe.

## Visualização e exportação

A exportação cria imagens PNG estáticas georreferenciadas por seus limites, adequadas ao GitHub Pages e carregadas sob demanda pelo Leaflet 1.9.4 já distribuído no repositório. Não exige serviço pago, chave ou execução dos modelos pelo navegador.

- Fontes: os seis rasters da rodada v6, em grade de 3 m, com a média na subpasta `v6 - algebra`.
- Estatísticas e cortes: calculados na grade original integral, excluindo as máscaras inválidas.
- Visualização: reprojeção para EPSG:3857 em passo de 20 m (cerca de 17 m no terreno neste recorte), por vizinho mais próximo. Não usa médias espaciais para criar valores de visualização.
- Classes: classificadas a partir do valor reamostrado e dos cortes integrais, com precisão interna preservada; cinco cores discretas.
- Degradê: 255 cores interpoladas na mesma faixa numérica para os três cenários de cada indicador. Essa quantização é apenas gráfica; não altera os valores ou estatísticas.
- Transparência: índice 0 do PNG reservado a NoData. Células sem dados não são representadas como valor zero do indicador.
- Prévias: imagens reduzidas para o quadro comparativo, com extensão idêntica aos mapas.
- Zoom: permite explorar a visualização; não recupera detalhes de 3 m removidos pela redução de resolução.

O seletor troca a camada mantendo posição e zoom. A troca entre degradê e classes também atualiza a legenda. Há estado de carregamento, recuperação de falhas, navegação por teclado e ajuste de tamanho para celular. Apenas os mapas próximos da área visível são inicializados; cada imagem é buscada quando selecionada.

Para reproduzir, use um ambiente Python com GDAL, NumPy e Pillow (por exemplo, o Python do QGIS):

```sh
python scripts/exportar_cenarios_climaticos.py --source-dir "caminho/InVEST/v6"
```

A saída padrão é `dados-mapas/clima`. Use `--out-dir` para outro diretório e `--resolution` para outro passo de visualização em EPSG:3857. As grades originais precisam estar alinhadas. As entradas são abertas em modo de leitura; não são regravadas.

## Relação com o diagnóstico publicado

Esta entrega adiciona a exploração das **camadas de entrada** à metodologia. Não recalcula resultados por fragmento, tabela por RA ou polígonos de `Zona_ICU.shp`. As classes de temperatura do diagnóstico publicado foram obtidas a partir dos valores por fragmento, e HM permanece numérico nessa saída. Os cinco intervalos dos rasters aqui apresentados não são silenciosamente aplicados a esses resultados anteriores.

A decisão de estudo para a próxima atualização da zona de ilha de calor é reunir as três classes mais quentes da **temperatura média**. Regenerar esse limite e recalcular suas interseções com os fragmentos é uma etapa posterior; a visualização desta entrega não altera aquela camada.
