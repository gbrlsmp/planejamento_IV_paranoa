"""Calcula métricas de 45 m ou 90 m com a função oficial MK_Fragmentation.

Requer Python com GDAL, Shapely, NumPy e Matplotlib, Rscript com magrittr e a revisão
0010946ab2eef7f8d2bc4935f369869fc4c58671 de R/MK_fragmentation.R.
Código do Makurhini:
https://github.com/connectscape/Makurhini/blob/0010946ab2eef7f8d2bc4935f369869fc4c58671/R/MK_fragmentation.R

A entrada deve conter id_frag e pode preservar os indicadores de AVU.
Use uma pasta de saída existente e execute uma vez por largura de borda.
A classificação de IV é aplicada depois por classificar_elementos_iv.py.
As operações de geometria usam GEOS no Python. R calcula as métricas a
partir das áreas e dos perímetros, com os mesmos argumentos e arredondamento.
"""
import argparse
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from osgeo import gdal, ogr
import shapely
from shapely.geometry import Polygon

REVISION = '0010946ab2eef7f8d2bc4935f369869fc4c58671'
SOURCE_SHA256 = 'ed267329eedf677bfcc44bbbfe34d8590c3652ccbae260fd6eacddfe5aa865bb'
FIELDS = ('Area', 'CA', 'CAPercent', 'Perimeter', 'EdgePercent', 'PARA', 'ShapeIndex', 'FRAC')

RUN_MAKURHINI = r"""
args <- commandArgs(trailingOnly = TRUE)
geom <- read.csv(args[2])
nodes <- data.frame(id_frag = geom$id_frag)
mk <- new.env(parent = globalenv())
mk[['%>%']] <- getExportedValue("magrittr", "%>%")
mk$st_buffer <- function(x, dist) {
  stopifnot(dist == -as.numeric(args[3]), identical(x$id_frag, nodes$id_frag))
  geom$core
}
mk$st_area <- function(x, by_element = TRUE) if (is.data.frame(x)) geom$area else x
mk$st_length <- function(x) x
mk$st_boundary <- function(x) geom$perimeter
mk$unit_convert <- function(value, from, to) {
  stopifnot(identical(from, to))
  value
}
mk$formattable <- function(table, ...) table
mk$installed.packages <- function(...) matrix(character(), nrow = 0)
sys.source(args[1], envir = mk)
result <- suppressMessages(mk$MK_Fragmentation(nodes, edge_distance = as.numeric(args[3]),
  landscape_area = as.numeric(args[4]), area_unit = "m2", perimeter_unit = "m", plot = FALSE))
patches <- result[["Patch statistics shapefile"]]
names(patches)[names(patches) == "id_frag"] <- "IdTemp"
write.csv(patches, paste0(args[5], "_PatchMetrics.csv"))
write.csv(result[["Summary landscape metrics (Viewer Panel)"]],
          paste0(args[5], "_LandscapeMetrics.csv"))
"""

def polygon_parts(geometry):
    """Devolve as partes poligonais que têm área."""
    if geometry.geom_type == 'Polygon' and not geometry.is_empty:
        yield geometry
    elif geometry.geom_type in ('MultiPolygon', 'GeometryCollection'):
        for part in geometry.geoms:
            yield from polygon_parts(part)



def area_of_basin(basin):
    with gdal.VectorTranslate('', str(basin), format='MEM', dstSRS='EPSG:31983') as data:
        return sum(feature.GetGeometryRef().GetArea() for feature in data.GetLayer())


def direct_buffer(geometry, distance):
    return shapely.buffer(geometry, -distance, quad_segs=30)


def columns(lo, hi, step):
    return range(int(np.floor(lo / step)) * step, int(np.ceil(hi)), step)


def clip_rectangle(geometry, x0, y0, x1, y1):
    clipped = shapely.clip_by_rect(geometry, x0, y0, x1, y1)
    if clipped.is_valid:
        return clipped
    return geometry.intersection(shapely.box(x0, y0, x1, y1))


def buffer_tiles(geometry, distance, step=2000):
    margin = distance + 6
    left, bottom, right, top = geometry.bounds
    cores = []
    for x in columns(left, right, step):
        band = clip_rectangle(geometry, x - margin, bottom - margin, x + step + margin, top + margin)
        if band.is_empty:
            continue
        for y in columns(band.bounds[1], band.bounds[3], step):
            piece = clip_rectangle(band, x - margin, y - margin, x + step + margin, y + step + margin)
            if piece.is_empty:
                continue
            core = direct_buffer(piece, distance)
            if not core.is_empty:
                cores.extend(polygon_parts(clip_rectangle(core, x, y, x + step, y + step)))
    return shapely.union_all(cores) if cores else Polygon()


def read_fragments(file):
    with ogr.Open(str(file)) as data:
        layer = data.GetLayer()
        if layer.GetSpatialRef().GetAuthorityCode(None) != '31983':
            raise ValueError('Fragmentos fora do CRS EPSG:31983')
        rows = [(f['id_frag'], shapely.from_wkb(bytes(f.GetGeometryRef().ExportToWkb()))) for f in layer]
    rows.sort(key=lambda row: row[0])
    if [identifier for identifier, _ in rows] != list(range(1, len(rows) + 1)):
        raise ValueError('IDs precisam ser únicos e consecutivos')
    return np.array([geometry for _, geometry in rows], dtype=object)


def compute_cores(geometries, distance):
    cores = []
    compared = 0
    tiled = 0
    for identifier, geometry in enumerate(geometries, 1):
        x0, y0, x1, y1 = geometry.bounds
        if min(x1 - x0, y1 - y0) <= 2 * distance:
            cores.append(Polygon())
            continue
        vertices = shapely.get_num_coordinates(geometry)
        if vertices < 5000:
            cores.append(direct_buffer(geometry, distance))
            continue
        print(f'{distance} m: fragmento {identifier}, {vertices:,} coordenadas', flush=True)
        core = buffer_tiles(geometry, distance)
        tiled += 1
        if vertices <= 15000 and compared < 4:
            direct = direct_buffer(geometry, distance)
            difference = direct.symmetric_difference(core).area
            if difference > 0.01:
                raise ValueError(f'Recuo em blocos divergiu no fragmento {identifier}: {difference} m²')
            compared += 1
        cores.append(core)
    if tiled and not compared:
        raise ValueError('Nenhum recuo por blocos conferido contra o recuo direto')
    if not np.all(shapely.is_valid(cores)):
        raise ValueError('Núcleo inválido')
    print(f'{distance} m: {tiled} recuos em blocos e {compared} comparações diretas', flush=True)
    return cores


def gpkg(file, prefix, patch, distance, landscape):
    with gdal.VectorTranslate(str(prefix) + '_PatchMetrics.gpkg', str(file), format='GPKG',
                              layerName='metricas_fragmentos') as data:
        layer = data.GetLayer()
        for key in FIELDS:
            layer.CreateField(ogr.FieldDefn(key, ogr.OFTReal))
        previous = layer.GetLayerDefn().GetFieldIndex('cat_iv')
        if previous >= 0:
            layer.DeleteField(previous)
        layer.SetMetadata({
            **{key: value for key, value in layer.GetMetadata().items() if key != 'CRITERIO_IV'},
            'AREA_PAISAGEM_M2': str(landscape),
            'BORDA_METROS': str(distance),
            'METODO': f'Makurhini MK_Fragmentation {REVISION}',
            'ORIGEM_FRAGMENTOS': file.name,
            'RECUO_COMPLEXOS': f'GEOS {shapely.geos_version_string}; blocos de 2000 m com margem de {distance+6} m',
        })
        data.StartTransaction()
        for feature in layer:
            for field in FIELDS:
                feature.SetField(field, patch[feature['id_frag']][field])
            layer.SetFeature(feature)
        data.CommitTransaction()


def plot_results(geometries, cores, patch, prefix, distance):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Patch, PathPatch
    from matplotlib.path import Path as PlotPath

    def geometry_patches(items):
        for shape in items:
            for poly in polygon_parts(shapely.orient_polygons(shape)):
                rings = [poly.exterior, *poly.interiors]
                paths = [PlotPath(np.asarray(r.coords), closed=True) for r in rings]
                yield PathPatch(PlotPath.make_compound_path(*paths))

    figure, ax = plt.subplots(figsize=(15, 11), layout='constrained')
    for items, color in ((geometries, '#c84a38'), (cores, '#1a9641')):
        ax.add_collection(PatchCollection(list(geometry_patches(items)), facecolor=color, edgecolor='none'))
    ax.autoscale_view()
    ax.set_aspect('equal')
    ax.set_axis_off()
    ax.set_title(f'Núcleo e borda · {distance} m')
    ax.legend(handles=[Patch(color='#1a9641', label='Núcleo'), Patch(color='#c84a38', label='Borda')])
    figure.savefig(str(prefix) + '_CoreEdge.tif', dpi=240, pil_kwargs={'compression': 'tiff_lzw'})
    plt.close(figure)

    figure, axes = plt.subplots(2, 2, figsize=(15, 11), layout='constrained')
    for ax, key, title, units in zip(axes.flat, ('Area', 'Perimeter', 'ShapeIndex', 'CA'),
        ('Área do fragmento', 'Perímetro', 'Índice de forma', 'Área de núcleo'),
        ('log10(m²)', 'log10(m)', 'Índice', 'log10(m²); zero para núcleo vazio')):
        values = np.array([row[key] for row in patch.values()])
        if key != 'ShapeIndex':
            positive = values > 0
            values[positive] = np.log10(values[positive])
        ax.hist(values, bins=10, color='#529580', edgecolor='white')
        ax.set(title=title, xlabel=units, ylabel='Frequência')
    figure.savefig(str(prefix) + '_fragStats.tif', dpi=240, pil_kwargs={'compression': 'tiff_lzw'})
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('fragmentos', 'bacia', 'makurhini', 'rscript', 'saida'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--borda', type=int, choices=(45, 90), required=True)
    parser.add_argument('--r-dll-dir', type=Path, help='Pasta Library/bin se R vier de um ambiente conda no Windows')
    args = parser.parse_args()
    official = args.makurhini.read_text(encoding='utf-8-sig').strip()
    if sha256(official.encode('utf-8')).hexdigest() != SOURCE_SHA256:
        parser.error(f'Informe o arquivo MK_fragmentation.R da revisão {REVISION}')
    env = os.environ.copy()
    if args.r_dll_dir is not None:
        env['PATH'] = str(args.r_dll_dir.resolve()) + os.pathsep + env.get('PATH', '')
    prefix = args.saida.resolve() / f'MK_Fragmentation_Bacia_Paranoa_{args.borda}m_AVU'
    if list(prefix.parent.glob(prefix.name + '_*')):
        raise FileExistsError(prefix)
    gdal.UseExceptions()
    ogr.UseExceptions()
    geometries = read_fragments(args.fragmentos)
    landscape = area_of_basin(args.bacia)
    if not len(geometries) or not np.isfinite(landscape) or landscape <= 0:
        raise ValueError('Área da paisagem ou base de fragmentos inválida')
    cores = compute_cores(geometries, args.borda)
    areas = shapely.area(geometries)
    core_areas = shapely.area(cores)
    if not np.all((0 <= core_areas) & (core_areas <= areas)):
        raise ValueError('Área de núcleo inválida')
    with tempfile.TemporaryDirectory(dir=prefix.parent) as folder:
        inputs = Path(folder) / 'areas.csv'
        runner = Path(folder) / 'executar_makurhini.R'
        runner.write_text(RUN_MAKURHINI, encoding='utf-8')
        with inputs.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(('id_frag', 'area', 'core', 'perimeter'))
            writer.writerows(zip(range(1, len(geometries) + 1), areas, core_areas, shapely.length(geometries)))
        subprocess.run([str(args.rscript), '--vanilla', str(runner), str(args.makurhini),
                        str(inputs), str(args.borda), str(landscape), str(prefix)], check=True, env=env)
    with Path(str(prefix) + '_PatchMetrics.csv').open(encoding='utf-8', newline='') as handle:
        patch = {int(row['IdTemp']): {name: float(row[name]) for name in FIELDS} for row in csv.DictReader(handle)}
    assert len(patch) == len(geometries) and all(key in patch for key in range(1, len(geometries) + 1))
    assert np.allclose([row['CA'] for row in patch.values()], core_areas, rtol=0, atol=.000051)
    gpkg(args.fragmentos, prefix, patch, args.borda, landscape)
    plot_results(geometries, cores, patch, prefix, args.borda)
    print(json.dumps({'borda': args.borda, 'area_paisagem_m2': landscape,
                      'nucleo_m2': sum(row['CA'] for row in patch.values()),
                      'fragmentos_com_nucleo': sum(row['CA'] > 0 for row in patch.values()),
                      'geos': shapely.geos_version_string}), flush=True)


if __name__ == '__main__':
    main()


