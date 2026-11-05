# Diagnóstico da Bacia do Paranoá

Relatório metodológico da Bacia do Paranoá, no Distrito Federal. O projeto busca definir estratégias para qualificar a conectividade ecológica e a prestação de serviços ecossistêmicos de regulação. O site reúne a identificação da Rede de Infraestrutura Verde e o diagnóstico de riscos socioambientais, condicionantes e ecologia.

[Ler o relatório](https://gbrlsmp.github.io/planejamento_IV_paranoa/) · [Abrir o mapa interativo](https://gbrlsmp.github.io/planejamento_IV_paranoa/mapa-riscos.html)

## Como usar o mapa

O mapa abre com o limite da bacia e as massas d’água. Selecione um indicador para colorir os fragmentos e clique em um deles para consultar seus valores. O mapa das regiões administrativas fica na aba de identificação da rede. O fundo de satélite do Google é opcional e depende da configuração descrita abaixo.

## O que há no repositório

| Caminho | Conteúdo |
| --- | --- |
| [`index.html`](index.html) | Sumário do relatório, objetivo, metodologia geral, matriz de decisão e referências. |
| [`identificacao.html`](identificacao.html) | Mapa da bacia e das RAs, leitura da rede, uso do solo, tipologias de AVU e IV e métricas de forma. |
| [`docs/referencias-parte-iv.md`](docs/referencias-parte-iv.md) | Referências, páginas da tese e relação com o conteúdo da Parte IV. |
| [`diagnostico.html`](diagnostico.html) | Metodologia e indicadores de riscos socioambientais, com acesso a Condicionantes e Ecologia. |
| [`mapa-riscos.html`](mapa-riscos.html) | Interface do mapa, com estilos e scripts próprios e Leaflet 1.9.4 em [`vendor/leaflet`](vendor/leaflet). |
| [`mapa-base.json.gz`](mapa-base.json.gz) | Limite da bacia, massas d’água e regiões administrativas a partir da base do IPE-DF (2023), em WGS 84. |
| [`mapa-dados.json.gz`](mapa-dados.json.gz) | Geometrias e indicadores dos fragmentos da rodada v01, preparados para visualização. |
| [`scripts/01_Diagnostico_RISCOS.py`](scripts/01_Diagnostico_RISCOS.py) | Cálculo dos indicadores de riscos por fragmento em PyQGIS. |
| [`scripts/condicionantes/`](scripts/condicionantes/) | Código de Momentos da Água e do resumo de Potencial de Recuperação Ecológica. |
| [`scripts/exportar_mapa.py`](scripts/exportar_mapa.py) | Exportador que prepara a camada final do diagnóstico para o navegador. |

## Como rodar localmente

Clone o repositório e inicie um servidor HTTP com Python 3.

```sh
git clone https://github.com/gbrlsmp/planejamento_IV_paranoa.git
cd planejamento_IV_paranoa
python -m http.server 8000
```

Abra o [mapa local](http://localhost:8000/mapa-riscos.html). Os arquivos de dados publicados já permitem explorar o mapa. O GitHub Pages publica os arquivos estáticos na raiz da branch `main`.

## Como reproduzir as análises

- **Riscos socioambientais**. [Executar o diagnóstico por fragmento no QGIS](scripts/LEIA_ME_RISCOS.md).
- **Condicionantes**. [Executar Momentos da Água e resumir o Potencial de Recuperação Ecológica](scripts/condicionantes/LEIA_ME_MOMENTOS_AGUA.md).

Os guias registram as entradas e os parâmetros. As camadas de origem são necessárias para uma nova execução.

## Como atualizar os indicadores no mapa

O exportador parte do GeoPackage final do diagnóstico e requer Python 3 e o `ogr2ogr` do GDAL, disponível no QGIS. Ele mantém os atributos usados pelo mapa, simplifica as geometrias em três unidades do sistema de coordenadas de entrada e as reprojeta para WGS 84.

```sh
python scripts/exportar_mapa.py "caminho-do-diagnostico.gpkg"
```

A camada de entrada padrão é `diagnostico_risco_v01`. Use `--camada` para indicar outro nome e `--ogr2ogr` para informar o caminho do executável se ele estiver fora do `PATH`. O arquivo de saída padrão é `mapa-dados.json.gz`.

### Satélite do Google

Ative a Maps JavaScript API em um projeto do Google Cloud com faturamento habilitado. Crie uma chave de navegador restrita a essa API e à origem `https://gbrlsmp.github.io`. [Configuração de chaves do Google Maps](https://developers.google.com/maps/documentation/javascript/get-api-key?hl=pt-br)

Preencha o atributo `content` de `<meta name="google-maps-key">` em [`mapa-riscos.html`](mapa-riscos.html). Essa chave de navegador fica visível no HTML publicado. A API só é carregada quando alguém ativa a opção de satélite.

## Como contribuir

Cada alteração começa com uma issue e passa por uma branch de trabalho e um pull request. Consulte o [guia de contribuição](CONTRIBUTING.md) para os tipos de branch, o padrão de nomes e o modelo de PR. As contribuições seguem o [código de conduta](CODE_OF_CONDUCT.md).

## Licença

O código original do projeto é licenciado sob a [GNU General Public License, versão 3](LICENSE) (`GPL-3.0-only`). O Leaflet mantém sua [licença BSD de duas cláusulas](vendor/leaflet/LICENSE). Para reutilizar os dados geográficos, consulte os termos das respectivas fontes. As imagens de satélite seguem os [termos do Google Maps](https://www.google.com/intl/pt-BR/help/terms_maps/).
