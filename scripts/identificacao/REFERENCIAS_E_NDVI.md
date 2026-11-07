# Referências MapBiomas–ZEE e exploração dos dois NDVIs

## Escopo e ordem das etapas

1. Referências: interseções vetoriais entre classes equivalentes do MapBiomas e do ZEE de cobertura vegetal.
2. NDVI e exploração: distribuições por grupo, separadas para seca e chuva, e gráfico NDVI seca × chuva.
3. Classificação e refinamento: etapa posterior, ainda sem regras finais ou avaliação independente.
4. Contexto dos remanescentes: cruzamento posterior com o outro produto do ZEE, de risco de perda de vegetação nativa.

Não foram definidos cortes de NDVI, modelos de classificação ou regras finais da rede. A pastagem participa somente como comparação e fica fora da rede de IV. Não se calculam médias ou diferenças entre datas como produtos desta exploração.

## Entradas e correspondência das legendas

O novo processamento lê o **vetor MapBiomas** indicado pela pesquisadora. A classe é o campo `cod_sub`, e não `classe`, que contém códigos compostos como 1003 e 2011. O raster local é usado para conferir a correspondência com a exploração histórica. A coleção permanece não comprovada; ano 2025 e resolução nominal de 10 m correspondem à identificação da pesquisadora.

| Grupo | MapBiomas, cod_sub | ZEE, classe |
| --- | --- | --- |
| Campestre | 12 | Formação Campestre |
| Savânica | 4 | Formação Savânica |
| Florestal | 3 | Formação Florestal |
| Campo alagado e área pantanosa | 11 | Áreas úmidas: Parque Cerrado (ou Murundum), Palmeirais e Veredas |
| Pastagem, comparação | 15 | Sem cruzamento de equivalência; referência apenas do MapBiomas |

As quatro referências usam também `simplifica = Vegetação nativa remanescente` no ZEE. Seus subgrupos originais permanecem incluídos, entre eles formações degradadas e “Campo de origem antrópica”. Isso precisa ser considerado na interpretação; concordância entre mapas não comprova composição florística ou conservação.

A correspondência de áreas úmidas foi confirmada pela pesquisadora como **operacional**, com ressalva explícita: as definições das fontes não são idênticas. O ZEE inclui murundus, palmeirais e veredas; não se afirma equivalência ecológica exata de toda a categoria à classe 11.

Os NDVIs são os novos arquivos `ndvi_chuva_2026-01-17.tif` e `ndvi_seca_2026-07-30.tif`, descritos em [NDVI_GERACAO.md](NDVI_GERACAO.md). O processamento não reutiliza os rasters antigos nem recalcula o índice nas imagens originais. O limite da bacia define o recorte comum.

## Procedimento

### Referências e áreas

1. Conferir o MapBiomas: rasterizar `cod_sub` do vetor na grade original do raster e comparar códigos e cobertura alfa, sem reamostrar a cópia raster.
2. Reprojetar as geometrias para EPSG:31983 com ordem tradicional de eixos e recortar ao limite da bacia.
3. Unir as geometrias de cada classe em cada fonte, para não somar duas vezes sobreposições internas da mesma classe.
4. Intersectar somente os pares correspondentes. A execução recusa sobreposições positivas entre referências de grupos diferentes, em vez de decidir silenciosamente seu tratamento.
5. Registrar as áreas integrais do MapBiomas, do ZEE e da interseção, em hectares. São áreas vetoriais, não contagens de pontos ou medidas de acurácia.
6. Salvar o GeoPackage e reabri-lo como entrada da amostragem seguinte. Nenhuma interseção anterior é reutilizada.

Geometrias inválidas são reparadas com `make_valid`, retendo componentes poligonais e registrando as áreas antes/depois. Nesta execução **nenhuma geometria precisou de reparo**. Esse tratamento técnico não valida a cartografia.

### Amostragem e gráficos

1. Verificar NDVIs de uma banda, 3 m, EPSG:31983 e origens alinhadas em múltiplos inteiros de 3 m. Usar a extensão comum.
2. Selecionar centros de pixels originais com espaçamento sistemático de 30 m e origem documentada no JSON. O espaçamento não é resolução de um novo raster. Não há interpolação nem média dos NDVIs.
3. Manter os mesmos locais e apenas pares finitos entre -1 e 1 nas duas datas, dentro da bacia e de cada referência. Pastagem usa a classe 15 do vetor MapBiomas, sem exigir equivalência com o ZEE.
4. Calcular histogramas com **80 intervalos iguais entre -1 e 1**, largura 0,025. Cada distribuição é normalizada pelo total de pares do próprio grupo, somando 100%. Essa largura é um parâmetro gráfico, não corte de classe. Os dois gráficos de distribuição compartilham os eixos e a escala vertical.
5. No gráfico seca × chuva, mostrar até 2.500 pares sorteados sem reposição por grupo, semente 20261106. As coordenadas de NDVI são arredondadas a cinco casas somente na representação pública. A quantidade desenhada não indica área relativa. O NPZ local preserva todos os valores amostrados e suas coordenadas espaciais.
6. Oferecer seleção dos grupos nos gráficos. A diagonal indica igualdade entre datas; não define classes. Não há inferência, testes de significância, intervalos de confiança ou estimativa de acurácia.
7. No diagrama de Sankey, somar os intervalos dos histogramas publicados em sete faixas, com limites −1, 0,20, 0,35, 0,45, 0,55, 0,65, 0,75 e 1. Cada faixa inclui o limite inferior e a última inclui também o limite superior. As duas datas usam as mesmas faixas, com intervalos mais estreitos onde se concentram os valores amostrados. As fitas mostram a porcentagem de cada grupo em cada faixa, com 100% por grupo e por data. A tabela do diagrama apresenta os percentuais e as contagens originais de pontos. O diagrama descreve as distribuições por data. O pareamento entre pontos é mostrado no gráfico seca × chuva.

### Mapa no site

As três camadas mostram as classes originais do MapBiomas, as classes do ZEE e as quatro interseções correspondentes. As fontes originais são preservadas; não se substitui o ZEE de cobertura pelo de risco.

Para manter o site leve, os vetores são rasterizados por centro de célula em EPSG:3857, com passo cartográfico de **20 m** e a mesma extensão nas três imagens PNG. São representações reduzidas, não novas bases de 20 m. Feições estreitas podem desaparecer. O mapa mantém o enquadramento ao trocar camada e permite ajustar opacidade, consultar a classe representada e reenquadrar a bacia. As áreas da tabela não são calculadas nesses PNGs.

## Produtos locais e publicação

Destinos confirmados pela pesquisadora sob `02 BASE DE DADOS/02_Análises/03_Ecologia/03_Fitofisionomia/`:

- `01_vetor/03_Intersec_ZEE_MapBiomas/referencias_mapbiomas_zee_sistema.gpkg`, camada `referencias_equivalentes`, EPSG:31983, quatro registros multipoligonais.
- `02_Tabela/Exploracao_NDVI_sistema/areas_referencias.csv`.
- `02_Tabela/Exploracao_NDVI_sistema/amostras_ndvi_pareadas.npz`.
- `02_Tabela/Exploracao_NDVI_sistema/exploracao_ndvi.json`, registro integral com caminhos, parâmetros, versões e assinaturas.
- **`04_figuras/`**, destino corrigido pela pesquisadora para as versões leves: `mapbiomas.png`, `zee.png`, `intersecao.png`, `referencias.json` e `exploracao.json`.

O site distribui cópias dos cinco arquivos leves em `dados-mapas/identificacao/`. Não é suficiente apontar o HTML a uma pasta pessoal do computador. As cópias de publicação devem ser byte a byte idênticas às versões locais; rasters completos, GeoPackage e NPZ permanecem fora do Git. O JSON público omite os caminhos pessoais, mantendo nomes e hashes. A revisão comum dos dois JSON é conferida pelo navegador para recusar execuções incompatíveis.

## Reprodução

Preparar Python com GDAL/OGR, NumPy, Shapely 2 e Pillow; nesta execução foi usado Python 3.12 do QGIS 3.44.15. No Windows, definir `QGIS_BIN` para a pasta de DLLs do QGIS. As versões efetivas estão no JSON da execução. O script abre as entradas em leitura e recusa sobrescrever suas nove saídas previstas. Usar novos destinos confirmados em uma nova execução; não remover produtos científicos anteriores automaticamente.

```powershell
python scripts/identificacao/preparar_referencias_ndvi.py --base "CAMINHO/02 BASE DE DADOS" --referencias "DESTINO_APROVADO/referencias_mapbiomas_zee_sistema.gpkg" --tabelas "PASTA_APROVADA_DE_TABELAS" --web "PASTA_APROVADA_04_figuras" --incluir-areas-umidas
```

`--incluir-areas-umidas` registra a adoção da correspondência operacional confirmada. `--espacamento` permite outro múltiplo positivo de 3 m (padrão 30); `--passo-web` define apenas o passo cartográfico (padrão 20). Alterá-los muda a execução e exige documentar os novos parâmetros. Copiar depois os cinco arquivos leves para `dados-mapas/identificacao/` do checkout para preparar a publicação.

```powershell
python scripts/identificacao/validar_referencias_ndvi.py --base "CAMINHO/02 BASE DE DADOS" --referencias "DESTINO_APROVADO/referencias_mapbiomas_zee_sistema.gpkg" --tabelas "PASTA_APROVADA_DE_TABELAS" --figuras "PASTA_APROVADA_04_figuras" --publicacao "dados-mapas/identificacao"
```

## Execução registrada

Revisão `998dd55a72b7567e`. A conferência vetor/raster comparou **11.021.899 células**, sem divergências de códigos ou cobertura. Esse resultado comprova a correspondência dessas duas cópias locais, não a coleção ou a acurácia do MapBiomas.

| Grupo | MapBiomas (ha) | ZEE (ha) | Interseção (ha) | Pares NDVI válidos, amostra |
| --- | ---: | ---: | ---: | ---: |
| Campestre | 5.436,74 | 20.316,70 | 3.936,28 | 43.788 |
| Savânica | 38.846,22 | 28.437,79 | 23.707,03 | 263.413 |
| Florestal | 10.867,98 | 6.184,56 | 5.063,39 | 56.402 |
| Campo alagado e área pantanosa | 1.574,15 | 1.454,81 | 246,40 | 2.741 |
| Pastagem, comparação | — | — | — | 83.909 |

As contagens são informação técnica, não a síntese exibida nas tabelas principais do site. As pequenas diferenças frente à exploração anterior decorrem da nova seleção espacial por vetor/interseção e da leitura dos novos NDVIs. A tabela antiga “Áreas por classe na base publicada” continua identificada como base anterior e não foi substituída por uma nova classificação.

## Limitações e referências científicas

UDM2 não foi aplicada aos mosaicos, conforme seus relatórios; nuvens/sombras podem afetar os resultados. Data e escala do ZEE e coleção do MapBiomas ainda precisam de comprovação. As referências vêm de mapas históricos de escalas e definições distintas. Duas datas não caracterizam um ciclo fenológico. Pontos próximos podem ser dependentes e não constituem observações independentes para inferência. A exploração informa uma futura discussão de cortes; não garante que limiares simples de NDVI sejam suficientes.

1. **Liesenberg, V.; Ponzoni, F. J.; Galvão, L. S. (2007).** Análise da dinâmica sazonal e separabilidade espectral de algumas fitofisionomias do cerrado com índices de vegetação dos sensores MODIS/TERRA e AQUA. Revista Árvore, 31(2). [DOI](https://doi.org/10.1590/S0100-67622007000200012). O estudo encontrou discriminação dependente da estação, com melhor separabilidade na seca naquele contexto. Apoia comparar datas; seus resultados MODIS não fornecem cortes diretamente aplicáveis ao PlanetScope. Página com texto integral consultada na discussão, sem reprodução da análise.
2. **Haddad, I. et al. (2022).** On the combined use of phenological metrics derived from different PlanetScope vegetation indices for classifying savannas in Brazil. Remote Sensing Applications: Society and Environment, 26, 100764. [DOI](https://doi.org/10.1016/j.rsase.2022.100764). Avaliou 70 imagens PlanetScope e métricas temporais em Águas Emendadas. Motiva investigar informação complementar entre datas, mas não autoriza reproduzir métricas de ciclo completo com duas imagens. Resumo e metadados consultados; não foi feita leitura integral do artigo.

As duas referências foram guardadas a pedido da pesquisadora e agora também acompanham o procedimento no repositório. Nenhum resultado desses trabalhos é apresentado como validação da classificação local.
