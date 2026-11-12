"""Confere polígonos web contra cada feição original, em coordenadas métricas."""
import argparse
from hashlib import sha256
import gzip
import json
from pathlib import Path

import numpy as np
from osgeo import ogr, osr
import shapely

from exportar_limites_avu_web import records, SOURCES
from preparar_referencias_ndvi import fingerprint, spatial_ref


def structure(geometry):
    if geometry.geom_type == 'Polygon':
        return ('Polygon', len(geometry.exterior.coords), tuple(len(r.coords) for r in geometry.interiors))
    return ('MultiPolygon', tuple(structure(part) for part in geometry.geoms))


def validate(base, output):
    manifest = json.loads((output / 'manifesto.json').read_text(encoding='utf-8'))
    expected, counts = records(base)
    assert manifest['contagens_fontes'] == counts
    assert [layer['id'] for layer in manifest['camadas']] == list(expected)
    payload = {k: v for k, v in manifest.items() if k != 'revisao'}
    assert sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16] == manifest['revisao']
    code = Path(__file__).with_name('exportar_limites_avu_web.py')
    assert sha256(code.read_text(encoding='utf-8').encode('utf-8')).hexdigest() == manifest['codigo_sha256_utf8_lf']
    for filename in SOURCES:
        actual = [{**r, 'arquivo': Path(r['arquivo']).name} for r in fingerprint(base / '01_Base/vetores/05_AVUs' / filename)]
        assert actual == manifest['fontes'][filename], filename
    transform = osr.CoordinateTransformation(spatial_ref(4326), spatial_ref(31983))
    total, max_error = 0, 0.
    for layer in manifest['camadas']:
        content = (output / layer['arquivo']).read_bytes()
        assert sha256(content).hexdigest() == layer['sha256'] and len(content) == layer['bytes']
        features = json.loads(gzip.decompress(content))['features']
        assert len(features) == len(expected[layer['id']]) == layer['feicoes']
        for feature, (properties, native) in zip(features, expected[layer['id']]):
            assert feature['properties'] == properties
            geometry = ogr.CreateGeometryFromJson(json.dumps(feature['geometry']))
            assert geometry.Transform(transform) == 0
            actual = shapely.from_wkb(bytes(geometry.ExportToWkb()))
            original = shapely.from_wkb(bytes(native.ExportToWkb()))
            assert actual.is_valid and actual.geom_type == original.geom_type
            assert structure(actual) == structure(original), 'Mudança de partes ou anéis'
            a, b = shapely.get_coordinates(actual), shapely.get_coordinates(original)
            assert a.shape == b.shape, 'Mudança de vértices ou partes'
            error = float(np.max(np.linalg.norm(a-b, axis=1)))
            assert error < .002, 'Deslocamento acima de 2 mm'
            max_error = max(max_error, error)
            total += 1
    assert manifest['simplificacao_m'] == 0 and not manifest['recorte_adicional']
    assert manifest['casas_coordenadas'] == 10 and total == sum(counts.values())
    print(f'OK: {total} feições, atributos selecionados, anéis/vértices e fontes preservados; erro máximo de reprojeção/arredondamento {max_error:.6f} m; revisão {manifest["revisao"]}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    validate(args.base.resolve(), args.output.resolve())
