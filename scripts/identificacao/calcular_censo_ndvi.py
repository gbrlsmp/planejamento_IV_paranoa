"""Censo pareado em 3 m das referências existentes, sem alterar cortes ou rasters.

Lê seca, chuva e média estrita na grade nativa; rasteriza cada referência por
centro de pixel. As máscaras são independentes, sem excluir pixels de uma
formação por prioridade de outra. Só grava em uma pasta de saída nova.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import shapely
from osgeo import gdal, ogr, osr

from classificar_fitofisionomias_3m import CORTES, valid
from preparar_referencias_ndvi import fingerprint, read_vectors, spatial_ref

gdal.UseExceptions()
ogr.UseExceptions()
gdal.SetCacheMax(256 * 1024 * 1024)
BINS = np.linspace(-1, 1, 81)
SEASONS = ('seca', 'chuva', 'media')
CODES = {'campestre': 12, 'savanica': 4, 'florestal': 3, 'campo_alagado': 11, 'pastagem': 15}
# Censo aprovado das interseções atuais, registrado no método de 11/11/2026.
ADOPTED = {
    'campestre': (4373980, 0.45674290037262527, 0.06177363058321809),
    'savanica': (26341685, 0.6418583869084876, 0.05870349848932762),
    'florestal': (5626327, 0.7876708356940665, 0.05220970383995581),
}


def code_fingerprint(path):
    return {'arquivo': path.name, 'sha256_utf8_lf': sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()}


def geometries(base, references):
    srs = spatial_ref(31983)
    saved, _ = read_vectors(references, srs)
    shapes = {r['grupo']: r['geometry'] for r in saved}
    basin_path = base / '01_Base/vetores/01_Limites/Bacia_Paranoa_MERGE_IPE_DF_2023.shp'
    basin = shapely.union_all([r['geometry'] for r in read_vectors(basin_path, srs)[0]])
    mb_path = base / '02_Análises/03_Ecologia/03_Fitofisionomia/01_vetor/02_MapBiomas_10m_2025/uso_cobertura_MapBiomas_Bacia_Paranoa.shp'
    source = ogr.Open(str(mb_path), 0)
    layer = source.GetLayer()
    layer.SetAttributeFilter('cod_sub = 15')
    original_srs = layer.GetSpatialRef().Clone()
    original_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(original_srs, srs)
    pasture = []
    for feature in layer:
        geometry = feature.GetGeometryRef().Clone()
        geometry.Transform(transform)
        pasture.append(shapely.from_wkb(bytes(geometry.ExportToWkb())))
    shapes['pastagem'] = shapely.union_all(pasture).intersection(basin)
    if set(shapes) != set(CODES) or any(not g.is_valid or g.is_empty for g in shapes.values()):
        raise ValueError('Referências ausentes, vazias ou inválidas')
    return shapes, basin_path, mb_path


def rasterize_mask(path, shape, template):
    vectors = ogr.GetDriverByName('Memory').CreateDataSource('')
    layer = vectors.CreateLayer('referencia', srs=template.GetSpatialRef())
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(ogr.CreateGeometryFromWkb(shape.wkb))
    layer.CreateFeature(feature)
    mask = gdal.GetDriverByName('GTiff').Create(str(path), template.RasterXSize, template.RasterYSize, 1,
        gdal.GDT_Byte, options=['TILED=YES', 'COMPRESS=DEFLATE', 'ZLEVEL=1', 'BIGTIFF=IF_SAFER'])
    mask.SetGeoTransform(template.GetGeoTransform())
    mask.SetProjection(template.GetProjection())
    mask.GetRasterBand(1).Fill(0)
    gdal.RasterizeLayer(mask, [1], layer, burn_values=[1])
    mask = None
    return gdal.Open(str(path), gdal.GA_ReadOnly)


def aligned_sources(paths):
    sources = {k: gdal.Open(str(p), gdal.GA_ReadOnly) for k, p in paths.items()}
    dry = sources['seca']
    gt = dry.GetGeoTransform()
    offsets = {}
    for key, source in sources.items():
        other = source.GetGeoTransform()
        if source.RasterCount != 1 or source.GetSpatialRef().GetAuthorityCode(None) != '31983' or other[1:3] + other[4:6] != (3, 0, 0, -3):
            raise ValueError('Esperados NDVIs nativos de 3 m em EPSG:31983')
        x, y = (gt[0] - other[0]) / 3, (other[3] - gt[3]) / 3
        if abs(x-round(x)) > 1e-8 or abs(y-round(y)) > 1e-8 or x < 0 or y < 0:
            raise ValueError('Grades não alinhadas por deslocamento inteiro')
        x, y = round(x), round(y)
        if x + dry.RasterXSize > source.RasterXSize or y + dry.RasterYSize > source.RasterYSize:
            raise ValueError('Fonte não cobre a grade da seca')
        offsets[key] = (x, y)
    return sources, offsets


def summarize(sources, offsets, masks, rows=512):
    dry = sources['seca']
    groups = {key: {'n_referencia': 0, 'n_pares_validos': 0,
        'momentos': {s: {'soma': 0., 'soma_quadrados': 0.} for s in SEASONS},
        'histogramas': {s: np.zeros(80, dtype=np.int64) for s in ('seca', 'chuva')},
        'densidade_conjunta': np.zeros((80, 80), dtype=np.int64)} for key in masks}
    audits = {key: [] for key in masks}
    paired_count = 0
    for y in range(0, dry.RasterYSize, rows):
        h = min(rows, dry.RasterYSize-y)
        arrays = {s: source.ReadAsArray(offsets[s][0], y+offsets[s][1], dry.RasterXSize, h)
                  for s, source in sources.items()}
        flags = {s: valid(a, sources[s].GetRasterBand(1).GetNoDataValue()) for s, a in arrays.items()}
        paired = flags['seca'] & flags['chuva']
        if not np.array_equal(paired, flags['media']):
            raise ValueError('Validade do raster médio estrito difere das duas datas válidas')
        mean = (arrays['seca'][paired].astype(np.float32) + arrays['chuva'][paired].astype(np.float32)) / np.float32(2)
        if not np.array_equal(mean, arrays['media'][paired]):
            raise ValueError('Raster médio difere da média Float32 das duas datas')
        paired_count += int(paired.sum())
        for key, mask in masks.items():
            inside = mask.ReadAsArray(0, y, dry.RasterXSize, h) != 0
            chosen = inside & paired
            group = groups[key]
            group['n_referencia'] += int(inside.sum())
            n = int(chosen.sum())
            group['n_pares_validos'] += n
            if not n:
                continue
            values = {s: a[chosen] for s, a in arrays.items()}
            for season, a in values.items():
                numbers = a.astype(np.float64)
                group['momentos'][season]['soma'] += float(numbers.sum())
                group['momentos'][season]['soma_quadrados'] += float(np.dot(numbers, numbers))
                if season != 'media':
                    group['histogramas'][season] += np.histogram(a, bins=BINS)[0]
            joint = np.histogram2d(values['seca'], values['chuva'], bins=(BINS, BINS))[0].astype(np.int64)
            group['densidade_conjunta'] += joint
            indexes = np.flatnonzero(chosen)
            for index in indexes[np.linspace(0, len(indexes)-1, min(5, len(indexes)), dtype=int)]:
                row, col = divmod(int(index), dry.RasterXSize)
                audits[key].append({'col': col, 'row': y+row, **{s: float(a[row, col]) for s, a in arrays.items()}})
        print(f'Censo: {min(y+h, dry.RasterYSize)}/{dry.RasterYSize} linhas', flush=True)
    for group in groups.values():
        n = group['n_pares_validos']
        if not n:
            raise ValueError('Grupo sem pixels válidos')
        group['n_sem_par_valido'] = group['n_referencia'] - n
        group['estatisticas'] = {}
        for season, moments in group['momentos'].items():
            mean = moments['soma'] / n
            variance = max(0., moments['soma_quadrados'] / n - mean * mean)
            group['estatisticas'][season] = {'media': mean, 'desvio_padrao': float(np.sqrt(variance))}
        group['histogramas'] = {s: a.tolist() for s, a in group['histogramas'].items()}
        group['densidade_conjunta'] = group['densidade_conjunta'].tolist()
    return groups, audits, paired_count


def check_counts(groups):
    for key, group in groups.items():
        joint = np.array(group['densidade_conjunta'], dtype=np.int64)
        n = group['n_pares_validos']
        if joint.shape != (80, 80) or joint.sum() != n:
            raise ValueError('Total conjunto inconsistente: ' + key)
        for season, axis in [('seca', 1), ('chuva', 0)]:
            if not np.array_equal(joint.sum(axis=axis), group['histogramas'][season]):
                raise ValueError('Marginal difere do histograma: ' + key)


def check_adopted(groups):
    result = {}
    for key, (n, mean, std) in ADOPTED.items():
        group = groups[key]
        actual = group['estatisticas']['media']
        if group['n_pares_validos'] != n or abs(actual['media']-mean) > 1e-12 or abs(actual['desvio_padrao']-std) > 1e-12:
            raise ValueError('Censo não reproduz a referência adotada: ' + key + ' ' + str(actual))
        limit = actual['media'] + actual['desvio_padrao'] if key == 'campestre' else actual['media']
        if key == 'florestal':
            limit -= actual['desvio_padrao']
        adopted = CORTES[CODES[key]]
        if abs(limit-adopted) > 1e-12 or np.float32(limit) != np.float32(adopted):
            raise ValueError('Limite censitário diverge do corte adotado: ' + key)
        result[key] = {'n': n, 'media_adotada': mean, 'desvio_adotado': std,
                       'limite_reproduzido': limit, 'limite_adotado': adopted,
                       'diferenca_limite': limit-adopted, 'mesmo_float32': True}
    return result


def public_record(local):
    public = deepcopy(local)
    public.pop('auditoria_pontos')
    for items in public['fontes'].values():
        for item in items:
            item['arquivo'] = Path(item['arquivo']).name
    return public


def run(base, web, output):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Saída deve ser uma pasta nova e vazia')
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'mascaras_temporarias'
    work.mkdir()
    fit = base / '02_Análises/03_Ecologia/03_Fitofisionomia'
    reference = fit / '01_vetor/03_Intersec_ZEE_MapBiomas/referencias_mapbiomas_zee_sistema.gpkg'
    tables = fit / '02_Tabela/Exploracao_NDVI_sistema'
    historical = json.loads((tables / 'exploracao_ndvi.json').read_text(encoding='utf-8'))
    old = json.loads((web / 'exploracao.json').read_text(encoding='utf-8'))
    maps = json.loads((web / 'referencias.json').read_text(encoding='utf-8'))
    paths = {s: fit / ('03_Raster/02_NDVI/' + filename) for s, filename in [
        ('seca', 'ndvi_seca_2026-07-30.tif'), ('chuva', 'ndvi_chuva_2026-01-17.tif'),
        ('media', 'ndvi_media_seca_chuva_2026.tif')]}
    sources, offsets = aligned_sources(paths)
    shapes, basin, mb = geometries(base, reference)
    masks = {}
    for key, shape in shapes.items():
        print('Máscara nativa por centro:', key, flush=True)
        masks[key] = rasterize_mask(work / (key + '.tif'), shape, sources['seca'])
    groups, audits, n_paired = summarize(sources, offsets, masks)
    check_counts(groups)
    comparison = check_adopted(groups)
    labels = {key: {'nome': group['nome'], 'cor': group['cor'], 'referencia': group['referencia'],
                    'mapbiomas_codigo': CODES[key]} for key, group in old['grupos'].items()}
    source_paths = {**paths, 'referencias': reference, 'mapbiomas_vetor': mb, 'bacia': basin,
                    'registro_amostral_historico': tables / 'exploracao_ndvi.json',
                    'amostras_historicas': tables / 'amostras_ndvi_pareadas.npz'}
    report = {'schema': 3, 'gerado_utc': datetime.now(timezone.utc).isoformat(),
        'estado': 'censo_pareado_grade_nativa_sem_alteracao_dos_cortes',
        'datas': old['datas'], 'areas': historical['areas'],
        'grupos': {key: {**labels[key], **groups[key]} for key in old['grupos']},
        'censo': {'tipo': 'todos_os_centros_validos_da_grade_nativa', 'resolucao_m': 3,
            'grade': sources['seca'].GetGeoTransform(),
            'dimensoes': [sources['seca'].RasterXSize, sources['seca'].RasterYSize],
            'deslocamentos_leitura': offsets, 'n_pares_validos_bacia': n_paired,
            'bins': BINS.tolist(), 'mascaras_independentes': True,
            'validade': 'Duas datas finitas em [-1,1], diferentes de NoData; raster médio estrito válido nos mesmos pixels.',
            'selecao_espacial': 'Centro de cada pixel nativo dentro da referência; sem ALL_TOUCHED e sem reamostragem.'},
        'metodo': {'estatisticas': 'Média e desvio padrão populacional espacial de todos os pixels válidos de cada referência; acumuladores Float64; seca e chuva separadas.',
            'media_temporal': 'Raster médio estrito Float32; censo reproduz os parâmetros adotados para os cortes.',
            'histogramas': '80 intervalos iguais entre -1 e 1; todos os pixels válidos, normalizados por grupo e data.',
            'dispersao': 'Frequências bidimensionais em células de NDVI 0,025 × 0,025; todos os pares válidos, sem sorteio.',
            'sankey': 'Agregação dos histogramas censitários nas mesmas faixas nas duas datas; 100% por grupo e época; distribuições marginais.'},
        'conferencia_cortes': comparison, 'auditoria_pontos': audits,
        'fontes': {key: fingerprint(path) for key, path in source_paths.items()},
        'codigo': [code_fingerprint(Path(__file__)), code_fingerprint(Path(__file__).with_name('classificar_fitofisionomias_3m.py'))],
        'limitacoes': historical['limitacoes'],
        'ambiente': {'gdal': gdal.VersionInfo('--version'), 'numpy': np.__version__, 'shapely': shapely.__version__}}
    public = public_record(report)
    revision_input = {k: v for k, v in public.items() if k != 'gerado_utc'}
    revision = sha256(json.dumps(revision_input, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    report['revisao'] = public['revisao'] = maps['revisao'] = revision
    for filename, record in [('censo_ndvi.json', report), ('exploracao.json', public), ('referencias.json', maps)]:
        (output / filename).write_text(json.dumps(record, ensure_ascii=False, allow_nan=False,
            **({'indent': 2} if filename == 'referencias.json' else {'separators': (',', ':')})), encoding='utf-8')
    print(json.dumps({'revisao': revision, 'pares': {k: g['n_pares_validos'] for k, g in groups.items()}, 'conferencia_cortes': comparison}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--web', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.base.resolve(), args.web.resolve(), args.output.resolve())
