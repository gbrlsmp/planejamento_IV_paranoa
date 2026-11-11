"""Interseções entre classes equivalentes e exploração pareada dos NDVIs novos.

Não classifica a bacia nem define cortes. Fontes são abertas em leitura; todas
as saídas são explícitas e a execução recusa sobrescrever arquivos existentes.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

_dll = os.add_dll_directory(os.environ['QGIS_BIN']) if os.name == 'nt' and os.environ.get('QGIS_BIN') else None
import numpy as np
import shapely
from PIL import Image
from osgeo import gdal, ogr, osr
from paletas_identificacao import ZEE_COLORS, qml_colors

gdal.UseExceptions()
ogr.UseExceptions()
gdal.SetCacheMax(256 * 1024 * 1024)

WETLAND = 'Áreas úmidas: Parque Cerrado (ou Murundum), Palmeirais e Veredas'
GROUPS = [
    ('campestre', 'Formação campestre', 12, 'Formação Campestre', '#d0a55f'),
    ('savanica', 'Formação savânica', 4, 'Formação Savânica', '#86a58f'),
    ('florestal', 'Formação florestal', 3, 'Formação Florestal', '#4b6a40'),
    ('campo_alagado', 'Campo alagado e área pantanosa', 11, WETLAND, '#496a6e'),
]
MB = {
    3: ('Formação florestal', '#4b6a40'), 4: ('Formação savânica', '#86a58f'),
    9: ('Silvicultura', '#d5d69e'), 11: ('Campo alagado e área pantanosa', '#496a6e'),
    12: ('Formação campestre', '#d0a55f'), 15: ('Pastagem', '#915558'),
    19: ('Lavoura temporária', '#64ef74'), 21: ('Mosaico de usos', '#b6b787'),
    24: ('Área urbanizada', '#e2e2e2'), 25: ('Outras áreas não vegetadas', '#eeeeee'),
    33: ('Rio, lago e oceano', '#acc6cb'), 36: ('Lavoura perene', '#c0a77a'),
}


def fingerprint(path):
    paths = [path]
    if path.suffix.lower() == '.shp':
        paths = [path.with_suffix(ext) for ext in ('.shp', '.shx', '.dbf', '.prj', '.cpg') if path.with_suffix(ext).exists()]
    result = []
    for item in paths:
        h = hashlib.sha256()
        with item.open('rb') as source:
            for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                h.update(block)
        result.append({'arquivo': str(item), 'bytes': item.stat().st_size, 'sha256': h.hexdigest()})
    return result


def spatial_ref(code):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(code)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


def polygonal(geometry):
    if geometry.is_empty:
        return shapely.MultiPolygon()
    if geometry.geom_type in ('Polygon', 'MultiPolygon'):
        return geometry
    return shapely.union_all([polygonal(g) for g in geometry.geoms])


def read_vectors(path, target):
    ds = ogr.Open(str(path), 0)
    layer = ds.GetLayer()
    srs = layer.GetSpatialRef().Clone()
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(srs, target)
    records, repairs = [], []
    for feature in layer:
        geometry = feature.GetGeometryRef().Clone()
        geometry.Transform(transform)
        shape = shapely.from_wkb(bytes(geometry.ExportToWkb()))
        if not shape.is_valid:
            old_area = shape.area
            shape = polygonal(shapely.make_valid(shape))
            repairs.append({'fid': feature.GetFID(), 'area_antes_m2': old_area, 'area_depois_m2': shape.area})
        records.append({'geometry': shape, **feature.items()})
    return records, repairs


def burn(records, srs, gt, width, height):
    vectors = ogr.GetDriverByName('Memory').CreateDataSource('')
    layer = vectors.CreateLayer('classes', srs=srs)
    layer.CreateField(ogr.FieldDefn('code', ogr.OFTInteger))
    for code, shape in records:
        if shape.is_empty:
            continue
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('code', int(code))
        feature.SetGeometry(ogr.CreateGeometryFromWkb(shape.wkb))
        layer.CreateFeature(feature)
    grid = gdal.GetDriverByName('MEM').Create('', width, height, 1, gdal.GDT_Byte)
    grid.SetProjection(srs.ExportToWkt())
    grid.SetGeoTransform(gt)
    grid.GetRasterBand(1).Fill(0)
    gdal.RasterizeLayer(grid, [1], layer, options=['ATTRIBUTE=code'])
    return grid.ReadAsArray()


def audit_mapbiomas(vector_path, raster_path):
    raster = gdal.Open(str(raster_path), gdal.GA_ReadOnly)
    if raster.RasterCount != 2 or raster.GetRasterBand(2).GetColorInterpretation() != gdal.GCI_AlphaBand:
        raise ValueError('Conferir estrutura do raster MapBiomas: classes e alfa esperados')
    memory = gdal.GetDriverByName('MEM').Create('', raster.RasterXSize, raster.RasterYSize, 1, gdal.GDT_Byte)
    memory.SetGeoTransform(raster.GetGeoTransform())
    memory.SetProjection(raster.GetProjection())
    vectors = ogr.Open(str(vector_path), 0)
    gdal.RasterizeLayer(memory, [1], vectors.GetLayer(), options=['ATTRIBUTE=cod_sub'])
    v = memory.ReadAsArray()
    r = raster.GetRasterBand(1).ReadAsArray()
    valid = raster.GetRasterBand(2).ReadAsArray() > 0
    common = valid & (v > 0)
    return {'criterio': 'cod_sub vetorial rasterizado nos centros da grade original, sem reamostrar o raster',
            'comparados': int(common.sum()), 'divergentes': int(((v != r) & common).sum()),
            'raster_sem_vetor': int((valid & (v == 0)).sum()),
            'vetor_fora_raster': int(((v > 0) & ~valid).sum())}


def save_references(path, refs, srs):
    ds = ogr.GetDriverByName('GPKG').CreateDataSource(str(path))
    layer = ds.CreateLayer('referencias_equivalentes', srs=srs, geom_type=ogr.wkbMultiPolygon)
    for name, kind in [('grupo', ogr.OFTString), ('nome', ogr.OFTString), ('mb_codigo', ogr.OFTInteger),
                       ('zee_classe', ogr.OFTString), ('area_ha', ogr.OFTReal)]:
        layer.CreateField(ogr.FieldDefn(name, kind))
    for group, label, code, zee_class, _, shape in refs:
        feature = ogr.Feature(layer.GetLayerDefn())
        for field, value in [('grupo', group), ('nome', label), ('mb_codigo', code),
                             ('zee_classe', zee_class), ('area_ha', shape.area / 10000)]:
            feature.SetField(field, value)
        feature.SetGeometry(ogr.ForceToMultiPolygon(ogr.CreateGeometryFromWkb(shape.wkb)))
        layer.CreateFeature(feature)
    ds = None


def sample_ndvi(rain_path, dry_path, ref_path, pasture, basin, srs, spacing):
    sources = {'chuva': gdal.Open(str(rain_path)), 'seca': gdal.Open(str(dry_path))}
    transforms = [d.GetGeoTransform() for d in sources.values()]
    for d, gt in zip(sources.values(), transforms):
        if d.RasterCount != 1 or d.GetSpatialRef().GetAuthorityCode(None) != '31983' or not np.allclose(gt[1:3] + gt[4:6], (3, 0, 0, -3)):
            raise ValueError('Esperados novos NDVIs de uma banda, EPSG:31983, pixels de 3 m')
    origins = (np.array(transforms[0])[[0, 3]] - np.array(transforms[1])[[0, 3]]) / 3
    if not np.allclose(origins, np.round(origins), rtol=0, atol=1e-6):
        raise ValueError('Grades dos NDVIs não alinhadas')
    left = max(gt[0] for gt in transforms)
    top = min(gt[3] for gt in transforms)
    right = min(d.GetGeoTransform()[0] + d.RasterXSize * 3 for d in sources.values())
    bottom = max(d.GetGeoTransform()[3] - d.RasterYSize * 3 for d in sources.values())
    stride = spacing // 3
    offset = stride // 2
    cols = np.arange(offset, round((right - left) / 3), stride)
    rows = np.arange(offset, round((top - bottom) / 3), stride)
    if not len(cols) or not len(rows):
        raise ValueError('Sem área comum amostrável')
    gt = (left + (offset + .5) * 3 - spacing / 2, spacing, 0,
          top - (offset + .5) * 3 + spacing / 2, 0, -spacing)
    w, h = len(cols), len(rows)
    bounds = (gt[0], gt[3] - h * spacing, gt[0] + w * spacing, gt[3])
    values = {}
    for key, source in sources.items():
        warped = gdal.Warp('', source, format='MEM', dstSRS=srs, outputBounds=bounds,
                           width=w, height=h, resampleAlg='near', dstNodata=-9999, overviewLevel='NONE')
        values[key] = warped.ReadAsArray()
        for row, col in [(0, 0), (h // 2, w // 2), (h - 1, w - 1)]:
            original_gt = source.GetGeoTransform()
            x, y = gt[0] + (col + .5) * spacing, gt[3] - (row + .5) * spacing
            c, r = round((x - original_gt[0]) / 3 - .5), round((original_gt[3] - y) / 3 - .5)
            if values[key][row, col] != source.ReadAsArray(c, r, 1, 1)[0, 0]:
                raise ValueError('Amostra não corresponde ao pixel original')
    basin_mask = burn([(1, basin)], srs, gt, w, h) == 1
    paired = basin_mask.copy()
    for a in values.values():
        paired &= np.isfinite(a) & (a >= -1) & (a <= 1)
    # Consumir o GeoPackage produzido nesta execução, não as interseções antigas.
    saved, _ = read_vectors(ref_path, srs)
    masks = {r['grupo']: burn([(1, r['geometry'])], srs, gt, w, h) == 1 for r in saved}
    hits = np.sum(list(masks.values()), axis=0)
    conflict = hits > 1
    masks = {name: mask & ~conflict for name, mask in masks.items()}
    masks['pastagem'] = burn([(1, pasture)], srs, gt, w, h) == 1
    # Pastagem é comparação MapBiomas; não depende de equivalência ZEE.
    samples, report = {}, {}
    bins = np.linspace(-1, 1, 81)
    rng = np.random.default_rng(20261106)
    for name, mask in masks.items():
        selected = mask & paired
        rr, cc = np.where(selected)
        seca, chuva = values['seca'][selected], values['chuva'][selected]
        samples[name + '__seca'] = seca
        samples[name + '__chuva'] = chuva
        samples[name + '__x'] = gt[0] + (cc + .5) * spacing
        samples[name + '__y'] = gt[3] - (rr + .5) * spacing
        index = np.sort(rng.choice(len(seca), min(2500, len(seca)), replace=False))
        report[name] = {'n_referencia': int(mask.sum()), 'n_pares_validos': len(seca),
                        'n_sem_par_valido': int((mask & ~paired).sum()),
                        'estatisticas': {key: {'media': float(np.mean(a[selected], dtype=np.float64)),
                                              'desvio_padrao': float(np.std(a[selected], dtype=np.float64, ddof=0))}
                                         for key, a in values.items()},
                        'histogramas': {key: np.histogram(a[selected], bins=bins)[0].tolist() for key, a in values.items()},
                        'pontos_grafico': np.round(np.column_stack((seca[index], chuva[index])), 5).tolist()}
    return samples, report, {'tipo': 'sistematica_em_centros_de_pixels_originais', 'espacamento_m': spacing,
                             'grade_amostral': gt, 'n_conflitos_excluidos': int((conflict & basin_mask).sum()),
                             'n_pares_validos_bacia': int(paired.sum()), 'bins': bins.tolist(),
                             'semente_grafico': 20261106, 'maximo_pontos_grafico_por_grupo': 2500}


def map_images(out, basin, mb_records, zee_records, refs, srs, step, final_colors):
    # Recorte de apresentação: áreas úmidas continuam nas fontes e no raster final.
    mb_records = [r for r in mb_records if r['cod_sub'] != 11]
    zee_records = [r for r in zee_records if r['classe'] != WETLAND]
    refs = [r for r in refs if r[2] != 11]
    web = spatial_ref(3857)
    transform = osr.CoordinateTransformation(srs, web)

    def project(shape):
        geometry = ogr.CreateGeometryFromWkb(shape.wkb)
        geometry.Transform(transform)
        return shapely.from_wkb(bytes(geometry.ExportToWkb()))

    bounds = project(basin).bounds
    left, bottom = math.floor(bounds[0] / step) * step, math.floor(bounds[1] / step) * step
    right, top = math.ceil(bounds[2] / step) * step, math.ceil(bounds[3] / step) * step
    w, h = round((right - left) / step), round((top - bottom) / step)
    gt = (left, step, 0, top, 0, -step)
    zee_labels = sorted({r['classe'] for r in zee_records})
    zee_ids = {label: i + 1 for i, label in enumerate(zee_labels)}
    if set(zee_labels) - set(ZEE_COLORS):
        raise ValueError('Categoria ZEE sem cor definida: ' + str(set(zee_labels) - set(ZEE_COLORS)))
    zee_legend = [{'codigo': zee_ids[label], 'nome': label,
                   'cor': ZEE_COLORS[label]} for label in zee_labels]
    definitions = {
        'mapbiomas': ([(int(r['cod_sub']), r['geometry']) for r in mb_records],
                      [{'codigo': code, 'nome': label, 'cor': color} for code, (label, color) in MB.items() if code != 11]),
        'zee': ([(zee_ids[r['classe']], r['geometry']) for r in zee_records], zee_legend),
        'intersecao': ([(i + 1, ref[-1]) for i, ref in enumerate(refs)],
                       [{'codigo': i + 1, 'nome': ref[1], 'cor': final_colors[ref[2]]}
                        for i, ref in enumerate(refs)]),
    }
    result = {}
    for name, (records, legend) in definitions.items():
        grid = burn([(code, project(geom)) for code, geom in records], web, gt, w, h)
        palette = [0] * 768
        for entry in legend:
            rgb = bytes.fromhex(entry['cor'][1:])
            palette[entry['codigo'] * 3:entry['codigo'] * 3 + 3] = rgb
        picture = Image.fromarray(grid).convert('P')
        picture.putpalette(palette)
        picture.save(out / (name + '.png'), transparency=0, optimize=True)
        # Preservar códigos em PNG, inclusive após a conversão para imagem paletizada.
        if not np.array_equal(np.asarray(Image.open(out / (name + '.png'))), grid):
            raise ValueError('PNG alterou códigos de classe')
        result[name] = {'imagem': 'dados-mapas/identificacao/' + name + '.png', 'legenda': legend}
    return {'bounds_3857': [left, bottom, right, top], 'passo_web_m': step, 'dimensoes': [w, h], 'camadas': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--referencias', type=Path, required=True, help='GeoPackage de saída aprovado')
    parser.add_argument('--tabelas', type=Path, required=True, help='Pasta aprovada para CSV, NPZ e JSON')
    parser.add_argument('--web', type=Path, required=True, help='Pasta dados-mapas/identificacao no checkout')
    parser.add_argument('--incluir-areas-umidas', action='store_true', help='Correspondência operacional previamente confirmada')
    parser.add_argument('--espacamento', type=int, default=30)
    parser.add_argument('--passo-web', type=int, default=20)
    args = parser.parse_args()
    if args.espacamento < 3 or args.espacamento % 3 or args.passo_web < 1:
        parser.error('Espaçamento positivo múltiplo de 3 m e passo web positivo exigidos')
    targets = [args.referencias] + [args.tabelas / f for f in ('areas_referencias.csv', 'amostras_ndvi_pareadas.npz', 'exploracao_ndvi.json')]
    targets += [args.web / f for f in ('mapbiomas.png', 'zee.png', 'intersecao.png', 'referencias.json', 'exploracao.json')]
    if any(p.exists() for p in targets):
        raise FileExistsError('Recusa sobrescrever saídas: ' + str([str(p) for p in targets if p.exists()]))
    fit = args.base / '02_Análises/03_Ecologia/03_Fitofisionomia'
    styles = fit / '03_Raster/03_fitofisionomia'
    mb_qml = qml_colors(styles / 'uso do solo mapbiomas.qml')
    final_qml = qml_colors(styles / 'uso do solo.qml')
    if any(mb_qml.get(code) != color for code, (_, color) in MB.items() if code not in (15, 36)):
        raise ValueError('Cores MapBiomas no código divergem do QML indicado')
    if set(code for _, _, code, _, _ in GROUPS) - set(final_qml):
        raise ValueError('QML final sem cor de alguma referência')
    paths = {
        'mapbiomas_vetor': fit / '01_vetor/02_MapBiomas_10m_2025/uso_cobertura_MapBiomas_Bacia_Paranoa.shp',
        'mapbiomas_raster_conferencia': fit / '03_Raster/01_MapBiomas_10m_2025/uso_e_corbertura_mapbiomas_10m_2025_bacia_paranoa.tif',
        'zee': fit / '01_vetor/01_ZEE/cobertura_vegetal_zee_Bacia_Paranoa.shp',
        'bacia': args.base / '01_Base/vetores/01_Limites/Bacia_Paranoa_MERGE_IPE_DF_2023.shp',
        'ndvi_chuva': fit / '03_Raster/02_NDVI/ndvi_chuva_2026-01-17.tif',
        'ndvi_seca': fit / '03_Raster/02_NDVI/ndvi_seca_2026-07-30.tif',
    }
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    print('Conferindo correspondência vetor/raster MapBiomas', flush=True)
    audit = audit_mapbiomas(paths['mapbiomas_vetor'], paths['mapbiomas_raster_conferencia'])
    if any(audit[k] for k in ('divergentes', 'raster_sem_vetor', 'vetor_fora_raster')):
        raise ValueError('MapBiomas vetorial e raster divergem; avaliar antes de executar: ' + json.dumps(audit))
    srs = spatial_ref(31983)
    basin_records, basin_repairs = read_vectors(paths['bacia'], srs)
    basin = shapely.union_all([r['geometry'] for r in basin_records])
    mb_records, mb_repairs = read_vectors(paths['mapbiomas_vetor'], srs)
    zee_records, zee_repairs = read_vectors(paths['zee'], srs)
    for records in (mb_records, zee_records):
        for r in records:
            r['geometry'] = polygonal(r['geometry'].intersection(basin))
    definitions = GROUPS if args.incluir_areas_umidas else GROUPS[:3]
    refs, areas = [], []
    for name, label, code, zee_class, color in definitions:
        print('Interseção:', label, flush=True)
        mb = shapely.union_all([r['geometry'] for r in mb_records if r['cod_sub'] == code])
        zee = shapely.union_all([r['geometry'] for r in zee_records
                                if r['classe'] == zee_class and r['simplifica'] == 'Vegetação nativa remanescente'])
        if zee.is_empty:
            raise ValueError('Classe ZEE esperada não encontrada: ' + zee_class)
        intersection = polygonal(mb.intersection(zee))
        refs.append((name, label, code, zee_class, color, intersection))
        areas.append({'grupo': name, 'nome': label, 'mapbiomas_codigo': code, 'zee_classe': zee_class,
                      'mapbiomas_ha': mb.area / 10000, 'zee_ha': zee.area / 10000,
                      'intersecao_ha': intersection.area / 10000,
                      'correspondencia': 'operacional_definicoes_distintas' if code == 11 else 'classes_equivalentes'})
    for i, a in enumerate(refs):
        if not a[-1].is_valid or a[-1].difference(basin).area > .01:
            raise ValueError('Referência inválida ou fora da bacia')
        for b in refs[i + 1:]:
            if a[-1].intersection(b[-1]).area > .01:
                raise ValueError('Sobreposição entre referências de grupos diferentes; discutir tratamento')
    for folder in (args.referencias.parent, args.tabelas, args.web):
        folder.mkdir(parents=True, exist_ok=True)
    save_references(args.referencias, refs, srs)
    pasture = shapely.union_all([r['geometry'] for r in mb_records if r['cod_sub'] == 15])
    print('Amostrando NDVIs novos nos mesmos locais', flush=True)
    samples, groups, sampling = sample_ndvi(paths['ndvi_chuva'], paths['ndvi_seca'], args.referencias, pasture, basin, srs, args.espacamento)
    np.savez_compressed(args.tabelas / 'amostras_ndvi_pareadas.npz', **samples)
    with (args.tabelas / 'areas_referencias.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(areas[0]), delimiter=';')
        writer.writeheader()
        writer.writerows(areas)
    print('Preparando mapas leves', flush=True)
    maps = map_images(args.web, basin, mb_records, zee_records, refs, srs,
                      args.passo_web, final_qml)
    labels = {r[0]: {'nome': r[1], 'cor': r[4], 'referencia': 'intersecao_equivalente'} for r in definitions}
    labels['pastagem'] = {'nome': 'Pastagem (comparação)', 'cor': MB[15][1], 'referencia': 'somente_MapBiomas_fora_da_rede_IV'}
    print('Registrando proveniência', flush=True)
    report = {'versao': 2, 'gerado_utc': datetime.now(timezone.utc).isoformat(),
              'estado': 'exploracao_sem_cortes_sem_validacao_independente', 'areas': areas,
              'datas': {'chuva': '2026-01-17', 'seca': '2026-07-30'},
              'grupos': {name: {**labels[name], **v} for name, v in groups.items()}, 'amostragem': sampling,
              'auditoria_mapbiomas': audit,
              'reparos_geometricos': {'bacia': basin_repairs, 'mapbiomas': mb_repairs, 'zee': zee_repairs},
              'metodo': {'areas': 'uniao por classe e intersecao vetorial integral em EPSG:31983, recortada a bacia',
                         'ndvi': 'amostra sistematica pareada; media e desvio populacional espacial por grupo e data; cortes usam censo separado no NDVI medio',
                         'histogramas': '80 intervalos iguais entre -1 e 1; normalizados pelo total valido de cada grupo e data',
                         'grafico_duas_datas': 'subamostra aleatoria sem reposicao de ate 2500 pares por grupo; semente fixa; sem ajuste de fronteiras',
                         'mapas': 'rasterizacao vetorial por centro de pixel em EPSG:3857; representacao reduzida para a web'},
              'limitacoes': ['Colecao MapBiomas nao comprovada; 2025 e 10 m conforme identificacao da pesquisadora',
                             'Data e escala do ZEE ainda precisam de comprovacao',
                             'Correspondencia de areas umidas operacional; definicoes das fontes distintas' if args.incluir_areas_umidas else 'Areas umidas pendentes de correspondencia',
                             'UDM2 nao aplicada nos mosaicos; nuvens e sombras podem afetar os NDVIs',
                             'Referencias de mapas historicos nao sao verdade de campo nem validacao independente',
                             'Campo de origem antropica e formacoes degradadas permanecem nos agrupamentos classe/simplifica originais do ZEE',
                             'Pontos proximos podem ser dependentes; nao ha inferencia estatistica ou acuracia calculada',
                             'Duas datas nao descrevem ciclo fenologico completo',
                             'Passo cartografico web nao e resolucao cientifica; feicoes estreitas podem desaparecer na representacao'],
              'fontes': {key: fingerprint(path) for key, path in paths.items()},
              'ambiente': {'gdal': gdal.VersionInfo('--version'), 'numpy': np.__version__, 'shapely': shapely.__version__},
              'codigo': fingerprint(Path(__file__)),
              'produtos_locais': {'referencias': fingerprint(args.referencias),
                                  'amostras': fingerprint(args.tabelas / 'amostras_ndvi_pareadas.npz'),
                                  'areas': fingerprint(args.tabelas / 'areas_referencias.csv')}}
    full = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    (args.tabelas / 'exploracao_ndvi.json').write_text(full, encoding='utf-8')
    # O manifesto público omite caminhos pessoais; as assinaturas continuam disponíveis.
    public = json.loads(full)
    for items in [*public['fontes'].values(), public['codigo'], *public['produtos_locais'].values()]:
        for item in items:
            item['arquivo'] = Path(item['arquivo']).name
    revision = hashlib.sha256(full.encode('utf-8')).hexdigest()[:16]
    public['revisao'] = revision
    maps.update({'revisao': revision, 'areas': [a for a in areas if a['mapbiomas_codigo'] != 11], 'inclui_areas_umidas': False,
                 'nota_areas_umidas': 'Correspondência operacional: classe 11 do MapBiomas ∩ áreas úmidas do ZEE; as definições não são idênticas.'})
    (args.web / 'referencias.json').write_text(json.dumps(maps, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.web / 'exploracao.json').write_text(json.dumps(public, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(json.dumps({'revisao': revision, 'areas': areas, 'pares_por_grupo': {k: v['n_pares_validos'] for k, v in groups.items()}}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
