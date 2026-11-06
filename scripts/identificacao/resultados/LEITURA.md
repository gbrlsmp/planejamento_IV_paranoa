# Exploração inicial da identificação da vegetação

Esta análise compara o NDVI de janeiro e julho de 2026 em áreas onde as cópias locais do MapBiomas e do ZEE concordam nas formações campestre, savânica e florestal. Não estabelece cortes finais e não aplica critérios de inclusão na rede de infraestrutura verde.

## Resultados descritivos

| Formação | Pares válidos | Média seca | Média chuva | Média das datas | DP da média das datas |
| --- | ---: | ---: | ---: | ---: | ---: |
| Campestre | 43.775 | 0,362 | 0,551 | 0,457 | 0,062 |
| Savânica | 263.430 | 0,563 | 0,720 | 0,642 | 0,059 |
| Florestal | 56.405 | 0,761 | 0,814 | 0,788 | 0,052 |

Médias e desvios descrevem as amostras de referência. Não são limites de classificação. Os grupos têm tamanhos distintos, e os pontos não representam observações independentes.

## Como a análise foi feita

1. Conferência de projeção, resolução, bandas e alinhamento das duas imagens.
2. Seleção sistemática dos centros de pixels originais, com espaçamento de 30 m. Isso reduz a leitura para exploração; não muda a resolução das imagens de origem.
3. Cálculo de NDVI a partir das bandas Red e NIR originais, desativando o uso automático de pirâmides de visualização. Pontos verificados diretamente nas fontes.
4. Consulta das classes do MapBiomas por vizinho mais próximo e das classes do ZEE nos mesmos centros. A concordância é feita nos pontos amostrais, sem gerar uma nova interseção vetorial integral.
5. Comparação pareada: apenas pontos válidos nas duas datas para cada grupo.
6. Resumos, distribuições e sobreposições descritivas. Pastagem e ausência de remanescentes são mantidas como grupos de comparação, sem excluir dados.

## Limitações

- UDM2 nao aplicado nos mosaicos segundo relatorios; mascaras separadas nao encontradas.
- Sem validacao independente nem controle de nuvens/sombras por UDM2.
- Pontos vizinhos nao independentes; nao foram calculados p-valores ou intervalos inferenciais.
- Referencias historicas e de escalas distintas; grade de saida 3m nao implica acuracia tematica 3m.
- NDVI calculado na amostra, nao foram produzidos rasters integrais novos.
- Grupo de ausencia no ZEE inclui coberturas diversas e nao equivale a vegetacao nao nativa.
- Nenhuma regra de inclusao em infraestrutura verde foi aplicada.

As fontes desta primeira exploração são cópias locais. Nenhum novo download do SISDIA ou do MapBiomas foi realizado. O ano está identificado no nome do arquivo local do MapBiomas, mas sua coleção não é comprovada pelos metadados do raster.

## Apresentação futura no site

Destino definido pela autora: Identificação → Uso do solo. Seguir a organização de Riscos socioambientais: introdução, tabela geral antes dos quadros, produção do indicador, procedimento completo em expansor fechado por padrão e mapas carregados sob demanda. Distinguir produção da cobertura vegetal da aplicação posterior ao diagnóstico e à rede de infraestrutura verde. O site não foi alterado.

## Arquivos

- `resultados.json`: método, limitações, resumos, cruzamentos e SHA-256 das fontes.
- `estatisticas.csv`: valores descritivos de todos os grupos.
- `amostras.npz`: valores pareados por grupo e variável.
- `comparacao_ndvi.png`: distribuições e relação entre as duas datas.

Para reproduzir, executar `analisar_vegetacao.py --base PASTA_DADOS --out PASTA_SAIDA` com Python/GDAL do QGIS, depois `apresentar_resultados.py PASTA_SAIDA` com Python, NumPy e Matplotlib. Os scripts ficam na pasta imediatamente acima dos resultados.
