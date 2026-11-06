# Obtenção do MapBiomas pelo código

## Entrada adotada para o trabalho

Por decisão da autora, o fluxo atual usa a cópia local do MapBiomas de 10 m identificada como 2025. A obtenção online não é requisito para executar a análise. A coleção da cópia local continua sem comprovação nos metadados consultados.

As entradas e suas relações estão documentadas em `CAMADAS_E_SUBPRODUTOS.md` e `camadas_identificacao.json`. A rotina de download abaixo permanece como alternativa, sem substituir a entrada local adotada.

## Alternativa de obtenção online

O módulo `baixar_mapbiomas.py` consulta o endereço oficial da Coleção 4 do produto Cobertura 10 m, com ano configurável entre 2017 e 2025. O padrão é 2025, último ano informado na página oficial consultada em 6 de novembro de 2026.

O módulo prevê leitura remota parcial com GDAL, recorte pela bacia na grade nativa, preservação dos códigos por vizinho mais próximo, metadados explícitos e manifesto com data, identificação do objeto remoto e SHA-256 do recorte. Não sobrescreve arquivos existentes.

## Situação verificada

O endereço indicado na página oficial respondeu HTTP 403 (acesso anônimo negado) tanto para HEAD quanto para GET parcial. Portanto, **nenhum novo raster oficial foi baixado e o fluxo completo de obtenção ainda não foi validado**. O código foi conferido quanto à sintaxe. O tratamento de erro impede substituir silenciosamente o ano ou a coleção.

O toolkit oficial no Google Earth Engine é outra via indicada pelo MapBiomas, mas exige login. Não há autenticação Earth Engine configurada neste ambiente. A coleção e o ano devem ser mantidos explícitos na exportação.

## Reprodução quando o endereço estiver acessível

Com Python/GDAL do QGIS:

```powershell
python baixar_mapbiomas.py --bacia "CAMINHO_LIMITE.shp" --out "NOVA_PASTA_FONTES" --ano 2025
python analisar_vegetacao.py --base "PASTA_BASE_DADOS" --mapbiomas "NOVO_RECORTE.tif" --out "NOVA_PASTA_RESULTADOS"
```

O argumento `--mapbiomas` permite usar o novo recorte, inclusive exportado pelo toolkit oficial, sem mudar a cópia antiga. A análise aceita uma banda de classes e, opcionalmente, uma banda alfa.

A primeira análise estatística entregue continua baseada na cópia local antiga; não foi recalculada nem atribuída à Coleção 4 por suposição.

Fonte: https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-10m/cobertura/

Toolkit: https://brasil.mapbiomas.org/downloads/baixe-mapas-recortados-geotiff-via-google-earth-engine/
