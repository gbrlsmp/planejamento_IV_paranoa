"""Audita IDs web por coordenadas e geometrias originais, sem gravar nas fontes."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from contextlib import closing

import numpy as np
from osgeo import gdal, ogr, osr
from PIL import Image
import shapely

gdal.UseExceptions()
ogr.UseExceptions()


def validate(base, output):
    manifest = json.loads((output/'manifesto.json').read_text(encoding='utf-8'))
    payload = {k: v for k, v in manifest.items() if k != 'revisao'}
    assert sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16] == manifest['revisao']
    path = output/manifest['arquivo']
    assert sha256(path.read_bytes()).hexdigest() == manifest['sha256']
    rgb = np.asarray(Image.open(path))
    assert rgb.shape == (manifest['altura'], manifest['largura'], 3)
    assert np.all(rgb[:, :, 2] == 0)
    ids = rgb[:, :, 0].astype(np.uint16)*256 + rgb[:, :, 1]
    assert ids.max() <= manifest['fragmentos_fonte'] == 46876
    assert len(np.unique(ids))-1 == manifest['fragmentos_representados']
    folder = base/'02_Análises/03_Ecologia'
    source = folder/('01_Fragmentação/'+manifest['fonte'])
    scenario_signatures = []
    for distance in [45, 90]:
        path = folder/f'01_Fragmentação/MK_Fragmentation_Bacia_Paranoa_{distance}m_AVU_PatchMetrics.gpkg'
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            digest = sha256()
            geometry_column = db.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name='metricas_fragmentos'").fetchone()[0]
            for identifier, geometry in db.execute(f'SELECT id_frag,"{geometry_column}" FROM metricas_fragmentos ORDER BY id_frag'):
                digest.update(int(identifier).to_bytes(4, 'little'))
                digest.update(geometry)
            scenario_signatures.append(digest.hexdigest())
    assert scenario_signatures[0] == scenario_signatures[1], 'Geometrias ou IDs diferem entre cenários'
    geometries, identifiers = [], []
    with ogr.Open(str(source), 0) as ds:
        for feature in ds.GetLayerByName('metricas_fragmentos'):
            identifiers.append(feature['id_frag'])
            geometries.append(shapely.from_wkb(bytes(feature.GetGeometryRef().ExportToWkb())))
    tree = shapely.STRtree(geometries)
    identifiers = np.asarray(identifiers)
    sr = []
    for code in [3857, 31983]:
        item = osr.SpatialReference()
        item.ImportFromEPSG(code)
        item.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        sr.append(item)
    transform = osr.CoordinateTransformation(*sr)
    # Amostra espacial uniforme mais um pixel de cada ID representado, para
    # conferir pequenos fragmentos e não apenas a área dos grandes hubs.
    _, first = np.unique(ids, return_index=True)
    positions = np.unique(np.concatenate([first, np.arange(0, ids.size, 997)]))
    rows, cols = np.divmod(positions, manifest['largura'])
    west, south, east, north = manifest['bounds']
    coords = transform.TransformPoints(np.column_stack([
        west+(cols+.5)*20, north-(rows+.5)*20]).tolist())
    raster = folder/'03_Fitofisionomia/03_Raster/03_fitofisionomia/fitofisionomias_proxy_ndvi_3m_etapa_04.tif'
    with gdal.Open(str(raster)) as ds:
        gt = ds.GetGeoTransform()
    # Vizinho mais próximo consulta o centro da célula nativa de 3 m.
    x = gt[0]+(np.floor((np.asarray(coords)[:, 0]-gt[0])/3)+.5)*3
    y = gt[3]-(np.floor((gt[3]-np.asarray(coords)[:, 1])/3)+.5)*3
    points = shapely.points(x, y)
    pairs = tree.query(points, predicate='intersects')
    actual = np.zeros(len(points), dtype=np.uint16)
    assert len(np.unique(pairs[0])) == len(pairs[0]), 'Sobreposição de fragmentos'
    actual[pairs[0]] = identifiers[pairs[1]]
    assert np.array_equal(actual, ids.ravel()[positions]), 'ID espacial divergente'
    print(f'OK: hash, codificação e {len(points)} consultas espaciais independentes; todos os {manifest["fragmentos_representados"]} IDs representados incluídos.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2]/'dados-mapas/identificacao/metricas-mapa')
    args = parser.parse_args()
    validate(args.base.resolve(), args.output.resolve())
