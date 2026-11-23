param([Parameter(Mandatory=$true)][string]$Script, [Parameter(ValueFromRemainingArguments=$true)][string[]]$Argumentos)
$ErrorActionPreference = 'Stop'
$env:PYTHONHOME = 'C:\Program Files\QGIS 3.44.15\apps\Python312'
$env:PATH = 'C:\Program Files\QGIS 3.44.15\bin;' + $env:PATH
$env:PROJ_DATA = 'C:\Program Files\QGIS 3.44.15\share\proj'
$env:GDAL_DATA = 'C:\Program Files\QGIS 3.44.15\apps\gdal\share\gdal'
$env:PYTHONPATH = 'C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS\05_scripts\.runtime-fitopolis'
$env:PARANOA_BASE_DADOS = 'C:\Users\sampa\OneDrive - unb.br\02 BASE DE DADOS'
& 'C:\Program Files\QGIS 3.44.15\bin\python3.exe' -u $Script @Argumentos
exit $LASTEXITCODE
