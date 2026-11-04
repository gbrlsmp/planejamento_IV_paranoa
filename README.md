# planejamento_IV_paranoa

Relatório metodológico da Bacia do Paranoá. O site publica arquivos estáticos na raiz da branch `main`.

O diagnóstico é calculado em PyQGIS. O exportador abaixo prepara a camada final para visualização no navegador, preservando os indicadores e simplificando as geometrias em três metros. A execução requer Python 3 e o `ogr2ogr` do GDAL, disponível no QGIS.

```text
python scripts/exportar_mapa.py "caminho-do-diagnostico.gpkg"
```

Use `--camada` se o nome da camada for diferente de `diagnostico_risco_v01`. Fora do terminal do QGIS, informe o executável com `--ogr2ogr`. O arquivo gerado é `mapa-dados.json.gz`.

Para visualizar o site localmente, execute `python -m http.server` na pasta do site e abra o endereço local do servidor no navegador.

O mapa usa Leaflet 1.9.4 em `vendor/leaflet`. A licença acompanha os arquivos da biblioteca. A base cartográfica tem atribuição ao OpenStreetMap no mapa.
