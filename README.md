# Diagnóstico da Bacia do Paranoá

Relatório metodológico da Bacia do Paranoá, no Distrito Federal. O projeto busca definir estratégias para qualificar a conectividade ecológica e a prestação de serviços ecossistêmicos de regulação. O site reúne a identificação da Rede de Infraestrutura Verde e o diagnóstico de riscos socioambientais, condicionantes e ecologia.

[Ler o relatório](https://gbrlsmp.github.io/planejamento_IV_paranoa/) · [Abrir o mapa interativo](https://gbrlsmp.github.io/planejamento_IV_paranoa/mapa-riscos.html)

## Como consultar a metodologia

As páginas de Riscos e Condicionantes apresentam **Produção das camadas** (resumo, sequência de etapas e procedimento expansível) e **Aplicação no diagnóstico** (cruzamento com os fragmentos e classificação). [Parâmetros, fontes e limites documentados](docs/metodologia-camadas.md).

## Como usar o mapa

Nos indicadores de Riscos, use **Visualização** para alternar entre os resultados por fragmento e o contexto da camada de entrada.

A seção [Riscos por RA](mapa-riscos.html#riscos-por-ra), na mesma página do mapa dos indicadores, reúne os indicadores dos fragmentos em cada Região Administrativa que intercepta a bacia.

O [mapa interativo geral](https://gbrlsmp.github.io/planejamento_IV_paranoa/mapa.html) permite combinar camadas temáticas, limites das RAs e indicadores de Riscos. Os tópicos do relatório também têm vistas de Metodologia e Mapa. [Dados e exportação das camadas](docs/mapas-tematicos.md).

O mapa abre com o limite da bacia e as massas d’água. Selecione um indicador para colorir os fragmentos e clique em um deles para consultar seus valores. Os limites e os códigos das regiões administrativas aparecem no mapa, com legenda de nomes e números. O fundo de satélite Sentinel-2 é opcional e funciona sem chave de API.

## O que há no repositório

| Caminho | Conteúdo |
| --- | --- |
| [`index.html`](index.html) | Sumário do relatório, objetivo, metodologia geral e referências. |
| [`identificacao.html`](identificacao.html) | Uso do solo, tipologias de AVU e IV e métricas de forma. |
| [`docs/referencias-parte-iv.md`](docs/referencias-parte-iv.md) | Referências, páginas da tese e relação com o conteúdo da Parte IV. |
| [`estrategias.html`](estrategias.html) | Matriz de decisão, matriz de resolução de problemas e estratégias. |
| [`diagnostico.html`](diagnostico.html) | Metodologia e indicadores de riscos socioambientais, com acesso a Condicionantes e Ecologia. |
| [`mapa-riscos.html`](mapa-riscos.html) | Interface do mapa, com estilos e scripts próprios e Leaflet 1.9.4 em [`vendor/leaflet`](vendor/leaflet). |
| [`mapa-base.json.gz`](mapa-base.json.gz) | Limite da bacia, massas d’água e regiões administrativas a partir da base do IPE-DF (2023), em WGS 84. |
| [`mapa-dados.json.gz`](mapa-dados.json.gz) | Geometrias e indicadores dos fragmentos da rodada v01, preparados para visualização. |
| [`scripts/01_Diagnostico_RISCOS.py`](scripts/01_Diagnostico_RISCOS.py) | Cálculo dos indicadores de riscos por fragmento em PyQGIS. |
| [`scripts/02_Diagnostico_CONDICIONANTES.py`](scripts/02_Diagnostico_CONDICIONANTES.py) | Proporções e classes predominantes de Momentos da Água e PRE por fragmento. [Guia de execução](scripts/LEIA_ME_CONDICIONANTES.md). |
| [`scripts/exportar_mapa.py`](scripts/exportar_mapa.py) | Exportador que prepara a camada final do diagnóstico para o navegador. |

## Como rodar localmente

Clone o repositório e inicie um servidor HTTP com Python 3.

```sh
git clone https://github.com/gbrlsmp/planejamento_IV_paranoa.git
cd planejamento_IV_paranoa
python -m http.server 8000
```

Abra o [mapa local](http://localhost:8000/mapa-riscos.html). Os arquivos de dados publicados já permitem explorar o mapa. O GitHub Pages publica os arquivos estáticos na raiz da branch `main`.

## Como atualizar os indicadores

Para calcular o diagnóstico por fragmento no QGIS, consulte o [guia de execução do script de Riscos](scripts/LEIA_ME_RISCOS.md).

O exportador parte do GeoPackage final do diagnóstico e requer Python 3 e o `ogr2ogr` do GDAL, disponível no QGIS. Ele mantém os atributos usados pelo mapa, simplifica as geometrias em três unidades do sistema de coordenadas de entrada e as reprojeta para WGS 84.

```sh
python scripts/exportar_mapa.py "caminho-do-diagnostico.gpkg"
```

A camada de entrada padrão é `diagnostico_risco_v01`. Use `--camada` para indicar outro nome e `--ogr2ogr` para informar o caminho do executável se ele estiver fora do `PATH`. O arquivo de saída padrão é `mapa-dados.json.gz`.

### Satélite gratuito

Ative **Mostrar satélite (Sentinel-2)** no mapa geral ou no mapa dos indicadores. A camada usa o mosaico Sentinel-2 cloudless 2025 da [EOX::Maps](https://maps.eox.at), com resolução de 10 m e dados Copernicus Sentinel modificados (2025). Não exige chave de API, cadastro ou faturamento.

O serviço é gratuito para este uso acadêmico e não comercial, sob [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Os créditos permanecem visíveis no mapa. O provedor aplica limites de acesso e não garante disponibilidade; falhas de carregamento são informadas na interface. Ampliar além do zoom nativo 14 mantém a imagem, sem acrescentar detalhes. [Condições da EOX](https://cloudless.eox.at/products/viewing).

## Como contribuir

Cada alteração começa com uma issue e passa por uma branch de trabalho e um pull request. Consulte o [guia de contribuição](CONTRIBUTING.md) para os tipos de branch, o padrão de nomes e o modelo de PR. As contribuições seguem o [código de conduta](CODE_OF_CONDUCT.md).

## Licença

O código original do projeto é licenciado sob a [GNU General Public License, versão 3](LICENSE) (`GPL-3.0-only`). O Leaflet mantém sua [licença BSD de duas cláusulas](vendor/leaflet/LICENSE). Para reutilizar os dados geográficos, consulte os termos das respectivas fontes. As imagens de satélite Sentinel-2 cloudless 2025 seguem a licença [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), distinta da licença do código.
