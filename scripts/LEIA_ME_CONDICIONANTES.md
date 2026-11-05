# Condicionantes por fragmento

O [script](02_Diagnostico_CONDICIONANTES.py) cruza os fragmentos com o raster de Momentos da Água e a camada vetorial de Potencial de Recuperação Ecológica (PRE). O CSV tem uma linha por fragmento, com as proporções de cada classe e a classe predominante em cada camada.

## Entradas

| Entrada | Camada usada no estudo | O que entra no cálculo |
| --- | --- | --- |
| Fragmentos | `MK_Fragmentation_Bacia_Paranoa_45m_PatchMetrics.shp` | Geometria e identificador `patch_id`. |
| Momentos da Água | `momento_dominante.tif`, versão 1.1.1 registrada na proveniência da análise do Paranoá. | Raster de 5 m. Os códigos 1, 2 e 3 são fonte, condução e acomodação, respectivamente. A máscara da banda informa as células sem dados. |
| Potencial de Recuperação Ecológica | `PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp`, camada da SEDUH-DF recortada à bacia. | O campo `cat_pdot20` registra muito alto, alto, médio e baixo. |

A leitura em fonte, condução e acomodação vem de Sandre et al. (2025) e foi aplicada por Renato Bezerra Rodrigues (2026) ao Córrego Taquari. O cruzamento usa os momentos que já constam no raster do Paranoá. [Sandre et al. (2025)](https://publicacoes.amigosdanatureza.org.br/index.php/rlaac_sustentabilidade/pt_BR/article/view/6127) · [Método no Taquari](https://renatobrodrigues-cmd.github.io/riscos-sbn-taquari/#mom-met)

Nas pp. 171–173, Amaral (2023) seleciona as classes 6 e 7 de umidade topográfica (TWI) e a classe 5 de fluxo de carbono (CO₂flux). Ele combina essas seleções em uma máscara e recorta o raster de fluxo de carbono. No Quadro 4, fluxo alto corresponde à integridade dos processos ecológicos de suporte (PES), fluxo médio à adaptação, fluxo baixo à transformabilidade 1 e fluxo muito baixo ou ausente à transformabilidade 2. [Tese de Amaral (2023)](https://repositorio.unb.br/handle/10482/45979)

A minuta preliminar do PDOT apresenta as categorias da tese. O Mapa 7 publicado e o campo `cat_pdot20` usam a escala de muito alto a baixo. O campo contém a classe final de potencial. A correspondência entre as duas legendas depende de metadados da camada ou da comparação das bases originais. O CSV preserva os rótulos do shapefile. [Minuta preliminar do PDOT, Mapa 8](https://sistemas.df.gov.br/PDOTSEDUH/Minuta%20Preliminar%20de%20Lei%20Complementar%20PDOT.pdf?DjwawQ6o_rZctCR1PLeEiQ=) · [Mapa 7 publicado](https://www.cl.df.gov.br/documents/5744638/35297378/DCL%2Bn%C2%BA%2B039%2C%2B2%2Bde%2Bmar%C3%A7o%2Bde%2B2026%2B-%2BSuplemento.pdf/d3817c42-f581-436c-f2b9-48c965c52d7f?t=1772223936113)

## Como o script calcula

- **Momentos da Água.** Calcula a área da interseção com as células de cada momento. Uma célula que cruza a borda contribui apenas com a parcela dentro do fragmento. Nesta versão, o grau de definição fica fora do resumo.
- **PRE.** Calcula a área da interseção com os polígonos e une os recortes da mesma classe. As áreas em que classes diferentes se sobrepõem ficam registradas à parte como `pre_pct_sobreposicao`.
- **Proporções.** Usa a área total do fragmento como denominador em ambas as camadas. As áreas sem cobertura classificada aparecem em `mom_pct_sem_dados` e `pre_pct_sem_dados`.
- **Predominância.** É a classe com a maior área identificável. A classe fica vazia em caso de empate, ausência de dados ou ausência de área exclusiva. O campo de situação indica o motivo. Leia a predominância junto dos percentuais, pois ela também pode ocorrer quando só uma pequena parte do fragmento tem dados.

## Executar

Use o Python do QGIS com GDAL, NumPy e Shapely 2. As três entradas devem estar em SIRGAS 2000 / UTM 23S (EPSG:31983). Mantenha os arquivos auxiliares dos shapefiles na mesma pasta.

```sh
python scripts/02_Diagnostico_CONDICIONANTES.py --fragmentos "caminho/fragmentos.shp" --momentos "caminho/momento_dominante.tif" --pre "caminho/potencial_recuperacao.shp"
```

O CSV separado por ponto e vírgula é enviado à saída padrão. Os campos `mom_predominante` e `pre_predominante` identificam a classe de maior área e `patch_id` permite vincular o CSV aos fragmentos no QGIS.
