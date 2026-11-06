"""Obtém recorte novo do MapBiomas 10 m Coleção 4 pela fonte pública oficial.

Requer Python/GDAL (por exemplo, QGIS). Não usa Earth Engine nem credenciais.
Preserva grade e códigos nativos; recorta pela bacia; nunca sobrescreve fontes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

_dll = os.add_dll_directory(os.environ["QGIS_BIN"]) if os.name == "nt" and os.environ.get("QGIS_BIN") else None
from osgeo import gdal, ogr, osr
import numpy as np
gdal.UseExceptions()
ogr.UseExceptions()

SOURCE_PAGE = 'https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/cobertura-10m/cobertura/'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bacia', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--ano', type=int, choices=range(2017, 2026), default=2025)
    args = p.parse_args()
    if not args.bacia.is_file():
        p.error('Limite da bacia não encontrado')
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f'mapbiomas_col4_10m_{args.ano}_bacia_paranoa'
    output, manifest = args.out/(stem+'.tif'), args.out/(stem+'.json')
    partial = args.out/(stem+'.part.tif')
    if any(f.exists() for f in [output, manifest, partial]):
        p.error('Já existe uma saída com esse nome; informe outra pasta para uma nova obtenção')
    url = ('https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/lulc_10m/'
           f'collection4/coverage/brazil_coverage/brazil_coverage-col4_10m_{args.ano}.tif')
    gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
    gdal.SetConfigOption('GDAL_HTTP_TIMEOUT', '60')
    gdal.SetConfigOption('GDAL_HTTP_MAX_RETRY', '2')
    gdal.SetConfigOption('CPL_VSIL_CURL_ALLOWED_EXTENSIONS', '.tif')
    # Record object identity as well as acquisition time, since a URL may change.
    try:
        with urlopen(Request(url, method='HEAD'), timeout=60) as response:
            headers = {key: response.headers.get(key) for key in
                       ['ETag', 'Last-Modified', 'Content-Length', 'x-goog-generation', 'x-goog-hash']}
    except HTTPError as error:
        if error.code == 403:
            raise RuntimeError('A fonte oficial negou acesso anônimo (HTTP 403). Nenhum dado foi baixado. '
                'Use uma exportação autenticada pelo toolkit oficial do Google Earth Engine ou aguarde '
                'a disponibilização pública do endereço. Não substituir silenciosamente coleção ou ano.') from None
        raise
    print('Abrindo fonte oficial; leitura remota apenas das regiões necessárias', flush=True)
    src = gdal.Open('/vsicurl/'+url, gdal.GA_ReadOnly)
    if src.RasterCount != 1:
        raise ValueError('Fonte oficial deveria ter uma banda de classes')
    gt = src.GetGeoTransform()
    if gt[2] != 0 or gt[4] != 0 or gt[1] <= 0 or gt[5] >= 0:
        raise ValueError('Grade não suportada: verificar orientação do raster')
    vector = ogr.Open(str(args.bacia), 0)
    layer = vector.GetLayer()
    if layer.GetFeatureCount() == 0:
        raise ValueError('Limite vazio')
    native = src.GetSpatialRef().Clone()
    native.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    local = layer.GetSpatialRef().Clone()
    local.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(local, native)
    boxes = []
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        geom.Transform(transform)
        boxes.append(geom.GetEnvelope())
    xmin, xmax = min(e[0] for e in boxes), max(e[1] for e in boxes)
    ymin, ymax = min(e[2] for e in boxes), max(e[3] for e in boxes)
    col0, col1 = math.floor((xmin-gt[0])/gt[1]), math.ceil((xmax-gt[0])/gt[1])
    row0, row1 = math.floor((gt[3]-ymax)/-gt[5]), math.ceil((gt[3]-ymin)/-gt[5])
    if min(col0, row0) < 0 or col1 > src.RasterXSize or row1 > src.RasterYSize:
        raise ValueError('Bacia fora da extensão da fonte')
    bounds = [gt[0]+col0*gt[1], gt[3]+row1*gt[5], gt[0]+col1*gt[1], gt[3]+row0*gt[5]]
    print(f'Recortando {col1-col0} × {row1-row0} células na grade nativa', flush=True)
    result = gdal.Warp(str(partial), src, format='GTiff', dstSRS=native.ExportToWkt(),
        outputBounds=bounds, width=col1-col0, height=row1-row0,
        cutlineDSName=str(args.bacia), resampleAlg='near', overviewLevel='NONE',
        dstNodata=0, outputType=gdal.GDT_Byte,
        creationOptions=['COMPRESS=DEFLATE', 'TILED=YES', 'NUM_THREADS=2'])
    result.SetMetadata({'FONTE': 'MapBiomas', 'PRODUTO': 'Cobertura 10m',
        'COLECAO': '4', 'ANO': str(args.ano), 'SOURCE_URL': url,
        'PROCESSAMENTO': 'recorte na grade nativa; vizinho mais proximo; sem piramides'})
    result.GetRasterBand(1).SetDescription('classification_'+str(args.ano))
    result.FlushCache()
    values, counts = np.unique(result.ReadAsArray(), return_counts=True)
    if len(values) == 1 and values[0] == 0:
        raise ValueError('Recorte sem células classificadas')
    metadata = {'fonte': 'MapBiomas', 'produto': 'Cobertura 10m', 'colecao': 4, 'ano': args.ano,
        'pagina_oficial': SOURCE_PAGE, 'url': url, 'objeto_remoto': headers,
        'obtido_utc': datetime.now(timezone.utc).isoformat(), 'gdal': gdal.VersionInfo('--version'),
        'crs_nativo': src.GetProjection(), 'geotransform_fonte': gt,
        'geotransform_saida': result.GetGeoTransform(), 'dimensoes': [result.RasterXSize, result.RasterYSize],
        'tratamento': 'recorte pela bacia na grade nativa; vizinho mais proximo; sem uso de overviews; nodata=0',
        'contagens_codigos': {str(int(v)): int(c) for v, c in zip(values, counts)},
        'resolucao_nominal_produto_m': 10,
        'observacao': 'Grade geográfica nativa pode estar em graus; este dado não foi transformado em 3 m.',
        'limite': {'arquivo': str(args.bacia), 'sha256': sha256(args.bacia)}, 'arquivo': str(output)}
    result = None
    metadata['sha256_recorte'] = sha256(partial)
    partial.rename(output)
    manifest.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'arquivo': str(output), 'manifesto': str(manifest),
                      'contagens': metadata['contagens_codigos']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
