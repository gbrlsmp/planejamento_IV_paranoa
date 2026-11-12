"""Exporta IDs dos fragmentos para recoloração web; não recalcula métricas.

Rasteriza os IDs na grade nativa e confere a área de todos os fragmentos antes
de reduzir por vizinho mais próximo para 20 m em EPSG:3857. Fontes somente leitura.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr
from PIL import Image

gdal.UseExceptions()
ogr.UseExceptions()


def export(base, output):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Usar saída nova e vazia')
    folder = base / '02_Análises/03_Ecologia'
    source = folder / '01_Fragmentação/MK_Fragmentation_Bacia_Paranoa_45m_AVU_PatchMetrics.gpkg'
    raster = folder / '03_Fitofisionomia/03_Raster/03_fitofisionomia/fitofisionomias_proxy_ndvi_3m_etapa_04.tif'
    with gdal.Open(str(raster)) as grid, ogr.Open(str(source), 0) as vectors:
        assert grid.GetSpatialRef().GetAuthorityCode(None) == '31983'
        assert grid.GetGeoTransform()[1:] == (3, 0, 8276418, 0, -3)
        layer = vectors.GetLayerByName('metricas_fragmentos')
        areas = {f['id_frag']: f['Area'] for f in layer}
        assert set(areas) == set(range(1, 46877))
        native = gdal.GetDriverByName('MEM').Create('', grid.RasterXSize, grid.RasterYSize, 1, gdal.GDT_UInt16)
        native.SetGeoTransform(grid.GetGeoTransform())
        native.SetSpatialRef(grid.GetSpatialRef())
        native.GetRasterBand(1).SetNoDataValue(0)
        layer.ResetReading()
        assert gdal.RasterizeLayer(native, [1], layer, options=['ATTRIBUTE=id_frag']) == 0
        counts = np.zeros(46877, dtype=np.int64)
        for y in range(0, grid.RasterYSize, 257):
            values = native.ReadAsArray(0, y, grid.RasterXSize, min(257, grid.RasterYSize-y))
            counts += np.bincount(values.ravel(), minlength=len(counts))
        assert all(abs(counts[i]*9 - area) < .001 for i, area in areas.items())
        web = gdal.Warp('', native, format='MEM', dstSRS='EPSG:3857', xRes=20, yRes=20,
                        srcNodata=0, dstNodata=0, resampleAlg='near', errorThreshold=0)
        ids = web.ReadAsArray()
        x, dx, _, y, _, dy = web.GetGeoTransform()
        bounds = [x, y+dy*web.RasterYSize, x+dx*web.RasterXSize, y]
        rgb = np.zeros((*ids.shape, 3), dtype=np.uint8)
        rgb[:, :, 0] = ids >> 8
        rgb[:, :, 1] = ids & 255
        output.mkdir(parents=True, exist_ok=True)
        target = output / 'fragmentos-ids.png'
        Image.fromarray(rgb).save(target, optimize=True)
        assert np.array_equal(np.asarray(Image.open(target))[:, :, 0].astype(np.uint16)*256 +
                              np.asarray(Image.open(target))[:, :, 1], ids)
        manifest = {'schema': 1, 'arquivo': target.name, 'sha256': sha256(target.read_bytes()).hexdigest(),
            'bounds': bounds, 'largura': web.RasterXSize, 'altura': web.RasterYSize,
            'resolucao_m': 20, 'crs': 'EPSG:3857', 'codificacao': 'id_frag = R * 256 + G; B = 0; fundo = 0',
            'fragmentos_fonte': len(areas), 'fragmentos_representados': int(len(np.unique(ids))-1),
            'fonte': source.name, 'camada': 'metricas_fragmentos',
            'nota': 'Representação por vizinho mais próximo; fragmentos menores podem não aparecer. Cores representam métricas do fragmento inteiro, inclusive CA; não delimitam núcleos.'}
        manifest['revisao'] = sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        (output / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.base.resolve(), args.output.resolve())
