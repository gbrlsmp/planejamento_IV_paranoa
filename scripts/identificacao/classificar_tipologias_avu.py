"""Delimita os fragmentos de vegetação e classifica as tipologias de AVU."""

from collections import Counter
import argparse
from io import BytesIO
import json
import os
from pathlib import Path
from uuid import uuid4

import numpy as np
from osgeo import gdal, gdal_array, ogr, osr
import shapely
from PIL import Image
from shapely import MultiPolygon, STRtree

gdal.UseExceptions()
ogr.UseExceptions()

classes = {
    3: ('pct_flor', 'Formação florestal'),
    4: ('pct_sav', 'Formação savânica'),
    11: ('pct_alag', 'Campo alagado e área pantanosa'),
    12: ('pct_camp', 'Formação campestre'),
    100: ('pct_urb', 'Vegetação intraurbana'),
}

def field(layer, name, kind, width, precision=0):
    definition = ogr.FieldDefn(name, kind)
    definition.SetWidth(width)
    if precision:
        definition.SetPrecision(precision)
    if layer.CreateField(definition) != 0:
        raise RuntimeError(f"Falha ao criar o campo {name}")

def ogr_shape(geometry):
    return shapely.from_wkb(bytes(geometry.ExportToWkb()))

def polygon_parts(geometry):
    if geometry.geom_type == 'Polygon':
        if not geometry.is_empty:
            yield geometry
    elif geometry.geom_type in ('MultiPolygon', 'GeometryCollection'):
        for part in geometry.geoms:
            yield from polygon_parts(part)

def valid_fragment(raw):
    geometry = ogr_shape(raw)
    if not geometry.is_valid:
        repaired = shapely.make_valid(geometry, method='structure', keep_collapsed=False)
        parts = list(polygon_parts(repaired))
        if not parts:
            raise ValueError('Fragmento sem geometria poligonal após reparo')
        geometry = parts[0] if len(parts) == 1 else MultiPolygon(parts)
    if geometry.geom_type not in ('Polygon', 'MultiPolygon') or not geometry.is_valid or geometry.is_empty:
        raise ValueError('Geometria poligonal inválida')
    return geometry

def reference_shapes(source_dir, filename, raster_crs, use_avus_field=False):
    shapes = []
    kinds = []
    with ogr.Open(str(source_dir / filename)) as source:
        layer = source.GetLayer()
        crs = layer.GetSpatialRef().Clone()
        crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = None
        if not crs.IsSame(raster_crs):
            transform = osr.CoordinateTransformation(crs, raster_crs)
            print(f'{filename}: reprojeção de {crs.GetAuthorityCode(None)} para 31983', flush=True)
        if use_avus_field and layer.GetLayerDefn().GetFieldIndex('AVUs') == -1:
            raise ValueError('Campo AVUs ausente na camada de áreas verdes')
        for feature in layer:
            kind = feature.GetField('AVUs') if use_avus_field else 'APP'
            if kind not in ('UC', 'Parque urbano', 'APP', 'Agrossistemas não intensivos'):
                raise ValueError(f'Categoria AVUs inesperada: {kind!r}')
            ref = feature.GetGeometryRef()
            if ref is None or ref.IsEmpty():
                raise ValueError(f'Geometria vazia em {filename}, feição {feature.GetFID()}')
            if transform is not None:
                ref = ref.Clone()
                if ref.Transform(transform) != 0:
                    raise RuntimeError(f"Falha ao reprojetar {filename}")
            geometry = ogr_shape(ref)
            if not geometry.is_valid or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
                raise ValueError(f'Geometria de referência inválida em {filename}, feição {feature.GetFID()}')
            shapes.append(geometry)
            kinds.append(kind)
    return shapes, kinds

def fill_pixels(geometry, identifier, labels, gt):
    """Preenche as células entre cruzamentos dos anéis com cada linha da grade."""
    if geometry.area == 9:
        left, _, _, top = geometry.bounds
        row = round((gt[3] - top) / 3)
        col = round((left - gt[0]) / 3)
        labels[row, col] = identifier
        return

    rings = shapely.get_rings(shapely.get_parts(geometry))
    coordinates, ring_ids = shapely.get_coordinates(rings, return_index=True)
    x = np.rint((coordinates[:, 0] - gt[0]) / 3).astype(np.int64)
    y = np.rint((gt[3] - coordinates[:, 1]) / 3).astype(np.int64)
    vertical = (x[:-1] == x[1:]) & (ring_ids[:-1] == ring_ids[1:])
    columns = x[:-1][vertical]
    starts = np.minimum(y[:-1], y[1:])[vertical]
    lengths = np.abs(np.diff(y))[vertical]
    nonzero = lengths > 0
    columns, starts, lengths = columns[nonzero], starts[nonzero], lengths[nonzero]
    interval_starts = np.cumsum(lengths) - lengths
    offsets = np.arange(int(lengths.sum())) - np.repeat(interval_starts, lengths)
    rows = np.repeat(starts, lengths) + offsets
    stride = labels.shape[1] + 1
    edges = rows * stride + np.repeat(columns, lengths)
    edges.sort()
    pairs = edges.reshape(-1, 2)
    row, start = divmod(pairs[:, 0], stride)
    end_row, stop = divmod(pairs[:, 1], stride)
    if not np.array_equal(row, end_row) or abs(int((stop - start).sum()) * 9 - geometry.area) > 0.0001:
        raise ValueError(f'Intervalos de rasterização inconsistentes no fragmento {identifier}')
    for y, x1, x2 in zip(row, start, stop):
        labels[y, x1:x2] = identifier


def raster_summary(raster, labels, fragment_count):
    counts = np.zeros((len(classes), fragment_count + 1), dtype=np.int64)
    width = raster.RasterXSize
    height = raster.RasterYSize
    raster_band = raster.GetRasterBand(1)
    id_band = labels.GetRasterBand(1)

    def verify_adjacent(a, b):
        if np.any((a > 0) & (b > 0) & (a != b)):
            raise ValueError('Pixels válidos vizinhos receberam IDs diferentes')

    for y in range(0, height, 512):
        rows = min(512, height - y)
        ids = id_band.ReadAsArray(0, y, width, min(rows + 1, height - y))
        core = ids[:rows]
        if core.min() < 0 or core.max() > fragment_count:
            raise ValueError('ID fora do intervalo de fragmentos')
        values = raster_band.ReadAsArray(0, y, width, rows)
        valid = np.isin(values, list(classes))
        if not np.array_equal(core > 0, valid):
            raise ValueError(f'Máscara vetorizada diverge do raster de origem na linha {y}')
        verify_adjacent(core[:, :-1], core[:, 1:])
        verify_adjacent(ids[:-1], ids[1:])
        verify_adjacent(ids[:-1, :-1], ids[1:, 1:])
        verify_adjacent(ids[:-1, 1:], ids[1:, :-1])
        for index, code in enumerate(classes):
            counts[index] += np.bincount(core[values == code], minlength=fragment_count + 1)
    return counts

def overlaps_area(geometry, index):
    # Dimensão 2 na interseção dos interiores exige sobreposição de área.
    return any(shapely.relate_pattern(geometry, index.geometries[i], '2********')
               for i in index.query(geometry))


def classify(geometry, uc_index, park_index, app_index):
    if overlaps_area(geometry, uc_index):
        return 'UC'
    park = overlaps_area(geometry, park_index)
    app = overlaps_area(geometry, app_index)
    if park:
        return 'Parque + APP' if app else 'Parque urbano'
    return 'APP' if app else 'Sem AVU'


MAP_CLASSES = {
    'UC': (1, '#23734d'),
    'Parque urbano': (2, '#78ad69'),
    'Parque + APP': (3, '#89739c'),
    'APP': (4, '#c4b53d'),
    'Sem AVU': (5, '#6b7270'),
}

def export_map(raster, gt, fragment_ids, map_codes):
    thematic = gdal_array.OpenArray(map_codes[fragment_ids])
    thematic.SetGeoTransform(gt)
    thematic.SetSpatialRef(raster.GetSpatialRef())
    overview = gdal.Warp('', thematic, format='MEM', dstSRS='EPSG:3857',
                         xRes=20, yRes=20, srcNodata=0, dstNodata=0,
                         resampleAlg='near')
    x, dx, _, y, _, dy = overview.GetGeoTransform()
    palette = [0] * (256 * 3)
    for code, color in MAP_CLASSES.values():
        palette[code * 3:code * 3 + 3] = bytes.fromhex(color[1:])
    image = Image.fromarray(overview.ReadAsArray())
    image.putpalette(palette)
    buffer = BytesIO()
    image.save(buffer, format='PNG', transparency=0, optimize=True)
    bounds = [x, y + dy * overview.RasterYSize, x + dx * overview.RasterXSize, y]
    return bounds, buffer


def run(base, staged):
    theme = base / '02_Análises/03_Ecologia/03_Fitofisionomia'
    raster_path = theme / '03_Raster/03_fitofisionomia/fitofisionomias_proxy_ndvi_3m_etapa_04.tif'
    source_dir = base / '01_Base/vetores/05_AVUs'
    with gdal.Open(str(raster_path)) as raster:
        raster_crs = raster.GetSpatialRef()
        raster_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        gt = raster.GetGeoTransform()
        assert raster_crs.GetAuthorityCode(None) == '31983'
        assert (gt[1], gt[2], gt[4], gt[5]) == (3, 0, 0, -3)
        assert raster.GetRasterBand(1).GetNoDataValue() == 255

        avu_shapes, avu_types = reference_shapes(source_dir, 'AVUs_Bacia do Paranoá_Final.shp', raster_crs, True)
        nascentes, _ = reference_shapes(source_dir, 'APP_Nascente_Bacia Paranoa.shp', raster_crs)
        hidro, _ = reference_shapes(source_dir, 'APP_Buffer_hid_Bacia_Paranoa.shp', raster_crs)
        uc_index = STRtree([shape for shape, kind in zip(avu_shapes, avu_types) if kind == 'UC'])
        park_index = STRtree([shape for shape, kind in zip(avu_shapes, avu_types) if kind == 'Parque urbano'])
        app_index = STRtree(nascentes + hidro)
        print(f'Limites lidos: {dict(Counter(avu_types))}; APP nascentes={len(nascentes)}, APP hidrografia={len(hidro)}', flush=True)

        raster_classes = raster.ReadAsArray()
        source_counts = [int(np.count_nonzero(raster_classes == code)) for code in classes]
        valid = np.isin(raster_classes, list(classes)).astype(np.uint8)
        raster_classes = None
        binary = gdal_array.OpenArray(valid)
        binary.SetGeoTransform(gt)
        binary.SetSpatialRef(raster_crs)
        raw = ogr.GetDriverByName('MEM').CreateDataSource('raw')
        raw_layer = raw.CreateLayer('components', srs=raster_crs, geom_type=ogr.wkbPolygon)
        print('Vetorizando a máscara de vegetação com oito vizinhos...', flush=True)
        binary_band = binary.GetRasterBand(1)
        if gdal.Polygonize(binary_band, binary_band, raw_layer, -1, options=['8CONNECTED=8']) != 0:
            raise RuntimeError('Falha na vetorização da máscara')
        fragment_count = raw_layer.GetFeatureCount()
        if fragment_count < 1:
            raise ValueError('Nenhum fragmento encontrado no raster')
        print(f'{fragment_count:,} fragmentos encontrados. Preparando geometrias e atributos...', flush=True)
        binary_band = binary = valid = None

        shapes = ogr.GetDriverByName('MEM').CreateDataSource('valid')
        shape_layer = shapes.CreateLayer('valid', srs=raster_crs, geom_type=ogr.wkbMultiPolygon)
        field(shape_layer, 'id_frag', ogr.OFTInteger, 9)
        field(shape_layer, 'classe_avu', ogr.OFTString, 16)
        areas = np.zeros(fragment_count + 1, dtype=np.float64)
        id_grid = np.zeros((raster.RasterYSize, raster.RasterXSize), dtype=np.int32)
        avu_counts = Counter()
        map_codes = np.zeros(fragment_count + 1, dtype=np.uint8)
        for identifier, raw_feature in enumerate(raw_layer, start=1):
            polygon = valid_fragment(raw_feature.GetGeometryRef())
            areas[identifier] = polygon.area
            fill_pixels(polygon, identifier, id_grid, gt)
            avu = classify(polygon, uc_index, park_index, app_index)
            feature = ogr.Feature(shape_layer.GetLayerDefn())
            feature.SetField('id_frag', identifier)
            feature.SetField('classe_avu', avu)
            feature.SetGeometry(ogr.CreateGeometryFromWkb(polygon.wkb))
            if shape_layer.CreateFeature(feature) != 0:
                raise RuntimeError(f'Falha ao preparar o fragmento {identifier}')
            avu_counts[avu] += 1
            map_codes[identifier] = MAP_CLASSES[avu][0]
            if identifier % 20000 == 0:
                print(f'{identifier:,}/{fragment_count:,} geometrias classificadas', flush=True)
        raw_feature = raw_layer = raw = None
        print(f'AVU: {dict(avu_counts)}. Conferindo a correspondência com a grade original...', flush=True)

        labels = gdal_array.OpenArray(id_grid)
        counts = raster_summary(raster, labels, fragment_count)
        labels = None
        pixels = counts.sum(axis=0)
        assert np.all(pixels[1:] > 0)
        assert np.allclose(pixels[1:] * 9, areas[1:], rtol=0, atol=0.0001)
        assert counts.sum(axis=1).tolist() == source_counts
        print('Grade, vizinhanca e area conferidas. Gravando atributos no GeoPackage...', flush=True)

        bounds, png = export_map(raster, gt, id_grid, map_codes)
        id_grid = None

        with ogr.GetDriverByName('GPKG').CreateDataSource(str(staged)) as dataset:
            out = dataset.CreateLayer('fragmentos_vegetacao_avu', srs=raster_crs,
                                      geom_type=ogr.wkbMultiPolygon,
                                      options=['SPATIAL_INDEX=YES'])
            if dataset.StartTransaction() != 0:
                raise RuntimeError('Falha ao iniciar a gravação do GeoPackage')
            field(out, 'id_frag', ogr.OFTInteger, 9)
            field(out, 'classe_avu', ogr.OFTString, 16)
            field(out, 'form_pred', ogr.OFTString, 45)
            for name, _ in classes.values():
                field(out, name, ogr.OFTReal, 12, 6)

            ties = 0
            shape_layer.ResetReading()
            for source_feature in shape_layer:
                identifier = source_feature.GetField('id_frag')
                avu = source_feature.GetField('classe_avu')
                class_counts = counts[:, identifier]
                predominant = np.flatnonzero(class_counts == class_counts.max())
                if predominant.size == 1:
                    formation = list(classes.values())[int(predominant[0])][1]
                else:
                    ties += 1
                    formation = 'Empate'
                record = ogr.Feature(out.GetLayerDefn())
                record.SetField('id_frag', identifier)
                record.SetField('classe_avu', avu)
                record.SetField('form_pred', formation)
                for (name, _), number in zip(classes.values(), class_counts):
                    record.SetField(name, round(100 * int(number) / int(pixels[identifier]), 6))
                record.SetGeometry(ogr.ForceToMultiPolygon(source_feature.GetGeometryRef().Clone()))
                if out.CreateFeature(record) != 0:
                    raise RuntimeError(f'Falha ao escrever o fragmento {identifier}')
            if dataset.CommitTransaction() != 0:
                raise RuntimeError('Falha ao concluir a gravação do GeoPackage')
            out = None

    shape_layer = shapes = None
    with ogr.Open(str(staged)) as dataset:
        layer = dataset.GetLayer()
        assert layer.GetFeatureCount() == fragment_count
        assert layer.GetSpatialRef().IsSame(raster_crs)
        definition = layer.GetLayerDefn()
        field_names = [definition.GetFieldDefn(i).GetName() for i in range(definition.GetFieldCount())]
        expected_fields = ['id_frag', 'classe_avu', 'form_pred', *(name for name, _ in classes.values())]
        assert field_names == expected_fields
        for identifier, feature in enumerate(layer, start=1):
            assert MAP_CLASSES[feature.GetField('classe_avu')][0] == map_codes[identifier]
            assert feature.GetField('id_frag') == identifier
            percentages = [feature.GetField(name) for name, _ in classes.values()]
            assert abs(sum(percentages) - 100) <= 0.0000026
            assert all(abs(observed - 100 * int(expected) / int(pixels[identifier])) <= 0.00000051
                       for observed, expected in zip(percentages, counts[:, identifier]))
            assert abs(feature.GetGeometryRef().GetArea() - areas[identifier]) <= 0.0001
            expected_predominant = np.flatnonzero(counts[:, identifier] == counts[:, identifier].max())
            assert feature.GetField('form_pred') == (list(classes.values())[int(expected_predominant[0])][1] if expected_predominant.size == 1 else 'Empate')
        layer = None
    area_by_avu = {avu: int(pixels[map_codes == spec[0]].sum()) * 9 / 10000
                   for avu, spec in MAP_CLASSES.items()}

    return png, {
        'fragments': fragment_count,
        'avus': dict(avu_counts),
        'area_ha_by_avu': area_by_avu,
        'source_pixel_counts': dict(zip(classes, source_counts)),
        'map': {'title': 'Classes de AVU dos fragmentos',
                'classes': [[code, avu, color]
                            for avu, (code, color) in MAP_CLASSES.items()],
                'bounds': bounds},
        'ties': ties,
        'vegetation_pixels': int(pixels.sum()),
        'vegetation_area_ha': float(pixels.sum() * 9 / 10000),
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--map-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != '.gpkg' or args.map_output.suffix.lower() != '.png':
        parser.error('--output requer .gpkg e --map-output requer .png')
    destination = args.output.resolve()
    map_output = args.map_output.resolve()
    for path in (destination, map_output):
        if path.exists():
            raise FileExistsError(path)
    staged = destination.with_name(f'.{destination.stem}-{uuid4().hex}.gpkg')
    try:
        png, report = run(args.base.resolve(), staged)
        if destination.exists():
            raise FileExistsError(destination)
        os.replace(staged, destination)
        with map_output.open('xb') as handle:
            handle.write(png.getbuffer())
        print(json.dumps(report, ensure_ascii=True), flush=True)
    finally:
        staged.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
