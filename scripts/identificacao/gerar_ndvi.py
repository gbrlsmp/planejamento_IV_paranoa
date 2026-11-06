"""Generate new basin-clipped PlanetScope NDVI rasters; never overwrite inputs."""
import argparse
import os
from pathlib import Path

if os.name == 'nt' and os.environ.get('QGIS_BIN'):
    _dll = os.add_dll_directory(os.environ['QGIS_BIN'])
import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()
NODATA = -9999.0


def ndvi(red, nir, mask):
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)
    total = red + nir
    valid = mask & (red != 0) & (nir != 0) & np.isfinite(total) & (total != 0)
    out = np.full(red.shape, NODATA, np.float32)
    np.divide(nir - red, total, out=out, where=valid)
    out[(out < -1) | (out > 1) | ~np.isfinite(out)] = NODATA
    return out


def run(source, basin, dest):
    if dest.exists():
        raise FileExistsError(f'Recusa sobrescrever {dest}')
    image = gdal.Open(str(source))
    if image.RasterCount != 8 or [image.GetRasterBand(i).GetDescription() for i in (6, 8)] != ['Red', 'NIR']:
        raise ValueError('Confirmar bandas: esperadas Red=6, NIR=8')
    gt = image.GetGeoTransform()
    if not np.allclose([gt[1], gt[2], gt[4], gt[5]], [3, 0, 0, -3]):
        raise ValueError('Imagem não está em grade de 3 m esperada')
    src = ogr.Open(str(basin))
    layer = src.GetLayer()
    original_srs = layer.GetSpatialRef().Clone()
    target_srs = image.GetSpatialRef().Clone()
    original_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(original_srs, target_srs)
    vectors = ogr.GetDriverByName('Memory').CreateDataSource('')
    projected = vectors.CreateLayer('bacia', srs=target_srs, geom_type=ogr.wkbMultiPolygon)
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        geom.Transform(transform)
        f = ogr.Feature(projected.GetLayerDefn())
        f.SetGeometry(geom)
        projected.CreateFeature(f)
    mask = gdal.GetDriverByName('MEM').Create('', image.RasterXSize, image.RasterYSize, 1, gdal.GDT_Byte)
    mask.SetGeoTransform(gt)
    mask.SetProjection(image.GetProjection())
    gdal.RasterizeLayer(mask, [1], projected, burn_values=[1])
    output = gdal.GetDriverByName('GTiff').Create(str(dest), image.RasterXSize, image.RasterYSize, 1, gdal.GDT_Float32,
        options=['TILED=YES', 'COMPRESS=DEFLATE', 'PREDICTOR=3', 'BIGTIFF=IF_SAFER'])
    output.SetGeoTransform(gt)
    output.SetProjection(image.GetProjection())
    output.SetMetadata({'source': source.name, 'formula': '(NIR-Red)/(NIR+Red)', 'bands': 'Red=6; NIR=8',
                        'quality_note': 'UDM2 nao aplicado conforme relatorio do mosaico'})
    output.GetRasterBand(1).SetNoDataValue(NODATA)
    output.GetRasterBand(1).SetDescription('NDVI')
    count = 0
    for y in range(0, image.RasterYSize, 512):
        h = min(512, image.RasterYSize-y)
        for x in range(0, image.RasterXSize, 512):
            w = min(512, image.RasterXSize-x)
            values = ndvi(image.GetRasterBand(6).ReadAsArray(x,y,w,h), image.GetRasterBand(8).ReadAsArray(x,y,w,h), mask.ReadAsArray(x,y,w,h) != 0)
            count += int((values != NODATA).sum())
            output.GetRasterBand(1).WriteArray(values, x, y)
        print(f'{source.name}: {y+h}/{image.RasterYSize}', flush=True)
    output.FlushCache()
    output = None
    print(f'{dest}: {count} pixels válidos', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--chuva', type=Path, required=True)
    p.add_argument('--seca', type=Path, required=True)
    p.add_argument('--bacia', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if not args.out.is_dir():
        raise FileNotFoundError('A pasta de saída aprovada precisa existir')
    targets = [args.out/'ndvi_chuva_2026-01-17.tif', args.out/'ndvi_seca_2026-07-30.tif']
    if any(p.exists() for p in targets):
        raise FileExistsError('Uma saída já existe; não será sobrescrita')
    for src, target in zip((args.chuva, args.seca), targets):
        run(src, args.bacia, target)
