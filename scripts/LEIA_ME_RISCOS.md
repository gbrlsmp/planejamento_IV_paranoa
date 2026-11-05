# Diagnóstico de riscos socioambientais

O script [01_Diagnostico_RISCOS.py](01_Diagnostico_RISCOS.py) cruza os fragmentos de vegetação com as camadas do diagnóstico. A [metodologia do relatório](../diagnostico.html#riscos) registra os critérios. A seção [Dados e método](../diagnostico.html#camadas) relaciona as entradas e seus tratamentos.

## Executar no QGIS

Use o Console Python do QGIS, com PyQGIS e os provedores de dados da instalação. Abra o editor do console e ajuste a pasta de dados e o caminho do script no trecho abaixo. A raiz de dados deve conter as pastas `01_Base` e `02_Análises`. Os caminhos relativos e os campos exigidos estão no bloco de configuração do script. Para shapefiles, mantenha os arquivos auxiliares na mesma pasta.

```python
from pathlib import Path
import os

os.environ["PARANOA_BASE_DADOS"] = r"C:/caminho/02 BASE DE DADOS"
script = Path(r"C:/caminho/planejamento_IV_paranoa/scripts/01_Diagnostico_RISCOS.py")
exec(compile(script.read_bytes(), str(script), "exec"))
```

A configuração padrão grava um GeoPackage e um JSON de parâmetros em `02_Análises/01_Riscos/05_Diagnostico`. Ajuste `PASTA_SAIDA`, `PREFIXO` ou `SUFIXO` se precisar separar novas rodadas. O script interrompe a execução se já houver um resultado com o mesmo nome. A região administrativa de maior sobreposição é gravada como atributo auxiliar. No relatório, as RAs aparecem no mapa de Identificação.

## Preparar a saída para o site

A configuração versionada gera `Diagnostico_RISCOS_v01_diagnostico.gpkg`, com uma camada de mesmo nome sem a extensão. A entrada histórica padrão do exportador usa o nome de camada `diagnostico_risco_v01`. Para exportar uma nova execução com a configuração versionada, informe a camada explicitamente e disponibilize o `ogr2ogr` do GDAL.

```sh
python scripts/exportar_mapa.py "caminho/Diagnostico_RISCOS_v01_diagnostico.gpkg" --camada Diagnostico_RISCOS_v01_diagnostico
```

O exportador prepara as geometrias e os campos usados pelo mapa em `mapa-dados.json.gz`.
