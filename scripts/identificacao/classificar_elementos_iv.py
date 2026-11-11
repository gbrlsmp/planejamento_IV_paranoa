"""Reproduz a classificação adotada dos elementos de IV e exporta o mapa.

Execute com o Python do QGIS. --apply atualiza cat_iv e a descrição do método
nos GeoPackages informados. As demais colunas são conferidas antes e depois.
"""
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import pickle
import re
import sqlite3

import numpy as np
from osgeo import gdal, ogr
import shapely
from shapely import STRtree

from classificar_tipologias_avu import export_map, fill_pixels, ogr_shape
from paletas_identificacao import qml_colors

gdal.UseExceptions()
ogr.UseExceptions()

# As cores vêm das classes 3, 4, 11, 12 e 101 do QML de uso do solo.
PALETTE_CODES = {'Hub 1': 3, 'Hub 2': 4, 'Link': 11, 'Site 1': 12, 'Site 2': 101}
METHOD = (
    'Classificação IV por prioridade. Hub 1: exclusivamente os dois maiores fragmentos '
    'pela área total entre os que se sobrepõem a UC de proteção integral. Hub 2: parques '
    'urbanos sem APP ainda sem classe e fragmentos que seriam Link com ShapeIndex superior a 25. '
    'Link: fragmentos com APP ainda sem classe. Site 1: Agrossistemas não intensivos '
    'ainda sem classe. Site 2: demais. Para IV, APP corresponde exclusivamente a sobreposição '
    'de área positiva com a camada dissolvido de APP_Buffer_hid_Bacia_Paranoa_disso.gpkg '
    '(EPSG:31983).'
)


def connection(path, mode='ro'):
    return closing(sqlite3.connect(path.resolve().as_uri() + '?mode=' + mode, uri=True, timeout=15))


def signature(db, schema):
    fields = [r[1] for r in db.execute(f'PRAGMA {schema}.table_info(metricas_fragmentos)') if r[1] != 'cat_iv']
    columns = ','.join('"' + name.replace('"', '""') + '"' for name in fields)
    digest = sha256()
    for row in db.execute(f'SELECT {columns} FROM {schema}.metricas_fragmentos ORDER BY id_frag'):
        digest.update(pickle.dumps(row))
    return digest.hexdigest()


def read_metrics(path):
    with ogr.Open(str(path)) as ds:
        layer = ds.GetLayerByName('metricas_fragmentos')
        if layer is None or layer.GetSpatialRef().GetAuthorityCode(None) != '31983':
            raise ValueError('Informe a camada metricas_fragmentos em EPSG:31983')
        records = {}
        for feature in layer:
            identifier = feature['id_frag']
            if identifier is None or identifier in records:
                raise ValueError('ID ausente ou duplicado')
            records[identifier] = {
                'area': feature['Area'], 'shape': feature['ShapeIndex'],
                'integral': bool(feature['avu_uc_pi']), 'park': bool(feature['avu_parque']),
                'agro': bool(feature['avu_agro']), 'geometry': ogr_shape(feature.GetGeometryRef()),
            }
        layer = None
    if len(records) < 2 or any(not np.isfinite(r['shape']) or r['area'] <= 0 for r in records.values()):
        raise ValueError('Métricas incompletas')
    return records


def classify(records, app_path):
    with ogr.Open(str(app_path)) as ds:
        layer = ds.GetLayerByName('dissolvido')
        if layer is None or layer.GetSpatialRef().GetAuthorityCode(None) != '31983':
            raise ValueError('A APP deve ter a camada dissolvido em EPSG:31983')
        shapes = [ogr_shape(feature.GetGeometryRef()) for feature in layer]
        layer = None
    if not shapes or not all(g.is_valid and not g.is_empty for g in shapes):
        raise ValueError('Geometria de APP inválida')
    parts = shapely.get_parts(shapes)
    tree = STRtree(parts)
    eligible = sorted((i for i in records if records[i]['integral']), key=lambda i: (-records[i]['area'], i))
    if len(eligible) < 2 or (len(eligible) > 2 and records[eligible[1]]['area'] == records[eligible[2]]['area']):
        raise ValueError('Os dois maiores fragmentos elegíveis precisam estar definidos sem empate')
    hubs = set(eligible[:2])
    classes = {}
    for identifier, record in records.items():
        geometry = record['geometry']
        app = any(shapely.relate_pattern(geometry, parts[i], '2********') for i in tree.query(geometry))
        if identifier in hubs:
            label = 'Hub 1'
        elif record['park'] and not app:
            label = 'Hub 2'
        elif app:
            label = 'Hub 2' if record['shape'] > 25 else 'Link'
        else:
            label = 'Site 1' if record['agro'] else 'Site 2'
        classes[identifier] = label
    if sum(label == 'Hub 1' for label in classes.values()) != 2:
        raise ValueError('Hub 1 deve conter exatamente dois fragmentos')
    return classes


def update_metrics(paths, classes, initial_signatures):
    def reject_geometry_write(value):
        raise RuntimeError('A atualização de IV não pode modificar a geometria')

    with connection(paths[0], 'rw') as db, db:
        schemas = ['main']
        for index, path in enumerate(paths[1:], 1):
            schema = f'cenario{index}'
            db.execute(f'ATTACH DATABASE ? AS {schema}', (path.resolve().as_uri() + '?mode=rw',))
            schemas.append(schema)
        for name in ('ST_IsEmpty', 'ST_MinX', 'ST_MaxX', 'ST_MinY', 'ST_MaxY'):
            db.create_function(name, 1, reject_geometry_write)
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TEMP TABLE nova_iv (id_frag INTEGER PRIMARY KEY, classe TEXT NOT NULL)')
        db.executemany('INSERT INTO nova_iv VALUES (?,?)', classes.items())
        for schema, path in zip(schemas, paths, strict=True):
            if signature(db, schema) != initial_signatures[path]:
                raise RuntimeError('O GeoPackage mudou durante a classificação')
            fields = {r[1] for r in db.execute(f'PRAGMA {schema}.table_info(metricas_fragmentos)')}
            if 'cat_iv' not in fields:
                db.execute(f'ALTER TABLE {schema}.metricas_fragmentos ADD COLUMN cat_iv TEXT')
            ids = {r[0] for r in db.execute(f'SELECT id_frag FROM {schema}.metricas_fragmentos')}
            if ids != classes.keys():
                raise ValueError('Os cenários devem conter os mesmos IDs')
            db.execute(f'UPDATE {schema}.metricas_fragmentos AS f SET cat_iv=n.classe '
                       'FROM temp.nova_iv AS n WHERE f.id_frag=n.id_frag')
            mdid, xml = db.execute(f'SELECT md.id,md.metadata FROM {schema}.gpkg_metadata md '
                                  f'JOIN {schema}.gpkg_metadata_reference ref ON ref.md_file_id=md.id '
                                  "WHERE ref.table_name='metricas_fragmentos' AND ref.reference_scope='table'").fetchone()
            xml, count = re.subn(r'(<MDI key="CRITERIO_IV">)[^<]*(</MDI>)',
                                lambda m: m[1] + METHOD + m[2], xml)
            if count == 0:
                xml = xml.replace('</Metadata>', f'  <MDI key="CRITERIO_IV">{METHOD}</MDI>\n  </Metadata>', 1)
            db.execute(f'UPDATE {schema}.gpkg_metadata SET metadata=? WHERE id=?', (xml, mdid))
            timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            db.execute(f'UPDATE {schema}.gpkg_contents SET last_change=? WHERE table_name=?',
                       (timestamp, 'metricas_fragmentos'))
            if signature(db, schema) != initial_signatures[path]:
                raise RuntimeError('A atualização modificou campos além de cat_iv')
    for path in paths:
        with connection(path) as db:
            actual = dict(db.execute('SELECT id_frag,cat_iv FROM metricas_fragmentos'))
            if actual != classes:
                raise RuntimeError('Falha na conferência após a gravação')


def render_map(records, classes, raster_path, qml, destination):
    palette = qml_colors(qml)
    legend = {label: (index, palette[code]) for index, (label, code) in enumerate(PALETTE_CODES.items(), 1)}
    with gdal.Open(str(raster_path)) as raster:
        if raster.GetSpatialRef().GetAuthorityCode(None) != '31983':
            raise ValueError('Raster fora de EPSG:31983')
        gt = raster.GetGeoTransform()
        if (gt[1], gt[2], gt[4], gt[5]) != (3, 0, 0, -3):
            raise ValueError('O mapa requer a grade nativa de 3 m')
        codes = np.zeros((raster.RasterYSize, raster.RasterXSize), dtype=np.uint8)
        expected = np.zeros(256, dtype=np.float64)
        for identifier, record in records.items():
            code = legend[classes[identifier]][0]
            fill_pixels(record['geometry'], code, codes, gt)
            expected[code] += record['area']
        actual = np.bincount(codes.ravel(), minlength=256) * 9
        if not np.allclose(actual[1:], expected[1:], rtol=0, atol=.001):
            raise ValueError('A representação dos fragmentos divergiu das áreas nativas')
        bounds, buffer = export_map(raster, gt, codes, np.arange(256, dtype=np.uint8), legend)
    with destination.open('xb') as handle:
        handle.write(buffer.getbuffer())
    return {'title': 'Elementos da infraestrutura verde', 'bounds': bounds,
            'classes': [[code, label, color] for label, (code, color) in legend.items()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', nargs='+', type=Path, required=True)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Gravar a classificação nos GeoPackages')
    parser.add_argument('--raster', type=Path)
    parser.add_argument('--qml', type=Path)
    parser.add_argument('--map-output', type=Path)
    args = parser.parse_args()
    paths = [path.resolve() for path in args.metrics]
    if len(set(paths)) != len(paths):
        parser.error('GeoPackage repetido')
    if args.map_output and (not args.raster or not args.qml):
        parser.error('--map-output requer --raster e --qml')
    snapshots = {}
    for path in paths:
        with connection(path) as db:
            snapshots[path] = signature(db, 'main')
    records = read_metrics(paths[0])
    # CA, CAPercent e borda mudam entre cenários. A classificação usa os
    # atributos e as geometrias comuns, conferidos por ID.
    for path in paths[1:]:
        other = read_metrics(path)
        if records.keys() != other.keys() or any(
            records[i] != other[i] for i in records
        ):
            raise ValueError('A delimitação ou os atributos usados na IV diferem entre cenários')
    classes = classify(records, args.app)
    if args.apply:
        update_metrics(paths, classes, snapshots)
    counts = Counter(classes.values())
    areas = Counter()
    for identifier, record in records.items():
        areas[classes[identifier]] += record['area'] / 10000
    report = {'fragments': len(records), 'counts': dict(counts), 'area_ha': dict(areas)}
    if args.map_output:
        report['map'] = render_map(records, classes, args.raster, args.qml, args.map_output)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
