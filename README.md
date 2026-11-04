# Diagnóstico da Bacia do Paranoá

Relatório metodológico e mapa interativo do diagnóstico de riscos ambientais por fragmento de vegetação na Bacia do Paranoá, no Distrito Federal. O projeto reúne indicadores de calor, umidade, inundação e ocupação por edificações, com renda e região administrativa como informações de contexto.

[Ler o relatório](https://gbrlsmp.github.io/planejamento_IV_paranoa/) · [Abrir o mapa interativo](https://gbrlsmp.github.io/planejamento_IV_paranoa/mapa-riscos.html)

## Como usar o mapa

O mapa abre com o limite da bacia e as massas d’água. Selecione um indicador para colorir os fragmentos e clique em um deles para consultar seus valores. As regiões administrativas podem ser ativadas separadamente. O fundo de satélite do Google é opcional e depende da configuração descrita abaixo.

## O que há no repositório

| Caminho | Conteúdo |
| --- | --- |
| [`index.html`](index.html) | Metodologia, indicadores, critérios de classificação e camadas de entrada do diagnóstico de riscos. |
| [`mapa-riscos.html`](mapa-riscos.html) | Interface do mapa, com estilos e scripts próprios e Leaflet 1.9.4 em [`vendor/leaflet`](vendor/leaflet). |
| [`mapa-base.json.gz`](mapa-base.json.gz) | Limite da bacia, massas d’água e regiões administrativas a partir da base do IPE-DF (2023), em WGS 84. |
| [`mapa-dados.json.gz`](mapa-dados.json.gz) | Geometrias e indicadores dos fragmentos da rodada v01, preparados para visualização. |
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

O diagnóstico é calculado em PyQGIS. O exportador parte do GeoPackage final do diagnóstico e requer Python 3 e o `ogr2ogr` do GDAL, disponível no QGIS. Ele mantém os atributos usados pelo mapa, simplifica as geometrias em três unidades do sistema de coordenadas de entrada e as reprojeta para WGS 84.

```sh
python scripts/exportar_mapa.py "caminho-do-diagnostico.gpkg"
```

A camada de entrada padrão é `diagnostico_risco_v01`. Use `--camada` para indicar outro nome e `--ogr2ogr` para informar o caminho do executável se ele estiver fora do `PATH`. O arquivo de saída padrão é `mapa-dados.json.gz`.

### Satélite do Google

Ative a Maps JavaScript API em um projeto do Google Cloud com faturamento habilitado. Crie uma chave de navegador restrita a essa API e à origem `https://gbrlsmp.github.io`. [Configuração de chaves do Google Maps](https://developers.google.com/maps/documentation/javascript/get-api-key?hl=pt-br)

Preencha o atributo `content` de `<meta name="google-maps-key">` em [`mapa-riscos.html`](mapa-riscos.html). Essa chave de navegador fica visível no HTML publicado. A API só é carregada quando alguém ativa a opção de satélite.

## Como contribuir

Use as [issues](https://github.com/gbrlsmp/planejamento_IV_paranoa/issues) para relatar problemas ou sugerir melhorias. Em alterações de metodologia, indique as camadas, os critérios e os campos afetados. Em alterações no mapa, descreva como testar a mudança e informe a origem de novos dados. As contribuições seguem o [código de conduta](CODE_OF_CONDUCT.md).

## Licença

O código original do projeto é licenciado sob a [GNU General Public License, versão 3](LICENSE) (`GPL-3.0-only`). O Leaflet mantém sua [licença BSD de duas cláusulas](vendor/leaflet/LICENSE). Para reutilizar os dados geográficos, consulte os termos das respectivas fontes. As imagens de satélite seguem os [termos do Google Maps](https://www.google.com/intl/pt-BR/help/terms_maps/).
