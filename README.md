# planejamento_IV_paranoa

Relatório metodológico da Bacia do Paranoá. O site publica arquivos estáticos na raiz da branch `main`.

O diagnóstico é calculado em PyQGIS. O exportador abaixo prepara a camada final para visualização no navegador, preservando os indicadores e simplificando as geometrias em três metros. A execução requer Python 3 e o `ogr2ogr` do GDAL, disponível no QGIS.

```text
python scripts/exportar_mapa.py "caminho-do-diagnostico.gpkg"
```

Use `--camada` se o nome da camada for diferente de `diagnostico_risco_v01`. Fora do terminal do QGIS, informe o executável com `--ogr2ogr`. O arquivo gerado é `mapa-dados.json.gz`.

Para visualizar o site localmente, execute `python -m http.server` na pasta do site e abra o endereço local do servidor no navegador.

O mapa usa Leaflet 1.9.4 em `vendor/leaflet`. A licença acompanha os arquivos da biblioteca. A base do IPE-DF (2023) está em `mapa-base.json.gz` e contém o limite da bacia, as massas d’água e as regiões administrativas, em WGS 84.

## Satélite do Google

Ative a [Maps JavaScript API](https://developers.google.com/maps/documentation/javascript/get-api-key?hl=pt-br) em um projeto do Google Cloud com faturamento habilitado. Crie uma chave de navegador, restrinja seu uso à Maps JavaScript API e autorize a origem `https://gbrlsmp.github.io` na restrição por sites. A API recebe apenas a origem nas solicitações entre domínios.

Coloque a chave restrita no atributo `content` de `<meta name="google-maps-key">` em `mapa-riscos.html`. A chave de navegador ficará visível no HTML publicado. O mapa abre com a base cartográfica do IPE-DF e só carrega a API quando a opção de satélite é marcada.
