"""Exporta os polígonos de referência de AVU/APP para consulta web, sem simplificar.

Fontes abertas apenas em leitura. Não classifica fragmentos nem altera vetores.
Mantém uma feição por polígono original, com seus anéis e partes; reprojeta para
EPSG:4326 e registra coordenadas em dez casas decimais. Recusa saída não vazia.
"""
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path

from osgeo import ogr, osr
import shapely

from preparar_referencias_ndvi import fingerprint, spatial_ref
from paletas_identificacao import AVU_COLORS

ogr.UseExceptions()
SOURCES = [
    'AVUs_Bacia do Paranoá_Final.shp',
    'APP_Nascente_Bacia Paranoa.shp',
    'APP_Buffer_hid_Bacia_Paranoa.shp',
]
GROUPS = {
    'uc_pi': {'nome': 'UC — Proteção Integral', 'categoria': 'UC - Proteção Integral', 'cor': AVU_COLORS['UC'], 'tracejado': '', 'visivel': True},
    'uc_us': {'nome': 'UC — Uso Sustentável', 'categoria': 'UC - Uso Sustentável', 'cor': AVU_COLORS['UC'], 'tracejado': '6 3', 'visivel': True},
    'parques': {'nome': 'Parques urbanos', 'categoria': 'Parque urbano', 'cor': AVU_COLORS['Parque urbano'], 'tracejado': '', 'visivel': True},
    'agro': {'nome': 'Agrossistemas não intensivos', 'categoria': 'Agrossistemas não intensivos', 'cor': AVU_COLORS['Agrossistemas não intensivos'], 'tracejado': '', 'visivel': True},
    'app_nascentes': {'nome': 'APPs de nascentes', 'categoria': 'APP de nascente', 'cor': AVU_COLORS['APP'], 'tracejado': '', 'visivel': False},
    'app_hidrografia': {'nome': 'APPs de hidrografia', 'categoria': 'APP de hidrografia', 'cor': AVU_COLORS['APP'], 'tracejado': '', 'visivel': False},
}


def records(base):
    folder = base / '01_Base/vetores/05_AVUs'
    result = {key: [] for key in GROUPS}
    counts = {}
    for index, filename in enumerate(SOURCES):
        path = folder / filename
        source = ogr.Open(str(path), 0)
        layer = source.GetLayer()
        srs = layer.GetSpatialRef().Clone()
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(srs, spatial_ref(31983))
        counts[filename] = layer.GetFeatureCount()
        for feature in layer:
            if index == 0:
                category = feature.GetField('AVUs')
                if category == 'UC':
                    category = feature.GetField('Grupo')
                key = next((key for key, info in GROUPS.items() if info['categoria'] == category), None)
                if key is None:
                    raise ValueError('Categoria AVU não prevista: ' + str(category))
                name = feature.GetField('Nome') or ''
            else:
                key = 'app_nascentes' if index == 1 else 'app_hidrografia'
                name = (feature.GetField('rio_nome') or '') if index == 2 else ''
            geometry = feature.GetGeometryRef().Clone()
            if geometry.Transform(transform) != 0:
                raise ValueError('Falha na reprojeção: ' + filename)
            shape = shapely.from_wkb(bytes(geometry.ExportToWkb()))
            if shape.is_empty or not shape.is_valid or shape.geom_type not in ('Polygon', 'MultiPolygon'):
                raise ValueError('Polígono de referência inválido: ' + filename)
            properties = {'id_origem': feature.GetFID(), 'categoria': GROUPS[key]['categoria'],
                          'nome': str(name), 'fonte': filename}
            result[key].append((properties, geometry))
    return result, counts


def export(base, output):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Usar saída nova e vazia')
    output.mkdir(parents=True, exist_ok=True)
    grouped, source_counts = records(base)
    transform = osr.CoordinateTransformation(spatial_ref(31983), spatial_ref(4326))
    layers = []
    for key, group in grouped.items():
        features = []
        for properties, native in group:
            geometry = native.Clone()
            if geometry.Transform(transform) != 0:
                raise ValueError('Falha na reprojeção para consulta web')
            features.append({'type': 'Feature', 'properties': properties,
                'geometry': json.loads(geometry.ExportToJson(options=['COORDINATE_PRECISION=10']))})
        payload = json.dumps({'type': 'FeatureCollection', 'features': features},
                             ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        compressed = gzip.compress(payload, compresslevel=9, mtime=0)
        filename = key + '.geojson.gz'
        (output / filename).write_bytes(compressed)
        layers.append({'id': key, **GROUPS[key], 'arquivo': filename, 'feicoes': len(features),
                       'sha256': sha256(compressed).hexdigest(), 'bytes': len(compressed)})
    manifest = {'schema': 1, 'crs_web': 'EPSG:4326', 'crs_conferencia': 'EPSG:31983',
        'simplificacao_m': 0, 'recorte_adicional': False, 'casas_coordenadas': 10,
        'nota': 'Polígonos das fontes originais de AVU/APP, sem simplificação nem recorte adicional; não representam os fragmentos classificados.',
        'contagens_fontes': source_counts, 'camadas': layers,
        'fontes': {filename: [{**r, 'arquivo': Path(r['arquivo']).name} for r in
            fingerprint(base / '01_Base/vetores/05_AVUs' / filename)] for filename in SOURCES},
        'codigo_sha256_utf8_lf': sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest()}
    manifest['revisao'] = sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
    (output / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'revisao': manifest['revisao'], 'camadas': {x['id']: x['feicoes'] for x in layers},
        'bytes_gzip': sum(x['bytes'] for x in layers)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    export(args.base.resolve(), args.output.resolve())
