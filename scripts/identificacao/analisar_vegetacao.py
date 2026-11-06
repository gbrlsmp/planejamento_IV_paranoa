"""Exploração reproduzível de NDVI sazonal; não produz classificação final.

Usa cópias LOCAIS das referências, sem alterar qualquer fonte. A amostra
sistemática seleciona pixels originais PlanetScope: espaçamento de 30 m por
padrão, não média nem interpolação do NDVI. Os centros amostrais são os mesmos
nas duas datas. Ausência de máscara UDM2 limita a interpretação.
Executar com Python/GDAL do QGIS; gráficos podem ser gerados separadamente.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone

_dll = os.add_dll_directory(os.environ["QGIS_BIN"]) if os.name == "nt" and os.environ.get("QGIS_BIN") else None
from osgeo import gdal, ogr, osr
import numpy as np

gdal.UseExceptions()
ogr.UseExceptions()
gdal.SetCacheMax(256 * 1024 * 1024)


def fingerprint(path):
    paths = sorted(path.parent.glob(path.stem + '.*')) if path.suffix == '.shp' else [path]
    items = []
    for p in paths:
        if p.suffix not in {'.shp', '.shx', '.dbf', '.prj', '.cpg'} and path.suffix == '.shp':
            continue
        h = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
                h.update(block)
        items.append({'arquivo': str(p), 'bytes': p.stat().st_size, 'sha256': h.hexdigest()})
    return items


def stats(values):
    values = values[np.isfinite(values)]
    if not len(values):
        return {'n': 0}
    qs = np.quantile(values, [0, .05, .25, .5, .75, .95, 1])
    return dict(n=int(len(values)), media=float(np.mean(values, dtype=np.float64)),
                desvio_padrao_populacional=float(np.std(values, dtype=np.float64)),
                **dict(zip(['minimo', 'p05', 'p25', 'mediana', 'p75', 'p95', 'maximo'], map(float, qs))))


def carregar_entradas(base, inventario):
    """Resolve as entradas declaradas no inventário legível da metodologia."""
    catalogo = json.loads(inventario.read_text(encoding='utf-8'))
    entradas = {}
    for camada in catalogo['camadas']:
        chave = camada.get('chave_execucao')
        if chave:
            if chave in entradas:
                raise ValueError(f'Chave de entrada duplicada: {chave}')
            entradas[chave] = base / camada['caminho_relativo']
    if set(entradas) != {'chuva', 'seca', 'mapbiomas', 'zee', 'risco', 'bacia'}:
        raise ValueError('O inventário deve identificar as seis entradas da exploração')
    return entradas, catalogo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stride', type=int, default=10)
    parser.add_argument('--camadas', type=Path, default=Path(__file__).with_name('camadas_identificacao.json'),
                        help='Inventário das entradas e dependências dos subprodutos')
    parser.add_argument('--mapbiomas', type=Path, help='Novo recorte oficial; substitui somente a entrada desta execução')
    args = parser.parse_args()
    if args.stride < 1:
        parser.error('--stride deve ser positivo')
    args.out.mkdir(parents=True, exist_ok=True)
    base = args.base
    paths, catalogo = carregar_entradas(base, args.camadas)
    if args.mapbiomas:
        paths['mapbiomas'] = args.mapbiomas
    if any(not p.is_file() for p in paths.values()):
        raise FileNotFoundError([str(p) for p in paths.values() if not p.is_file()])
    ds = {k: gdal.Open(str(paths[k]), gdal.GA_ReadOnly) for k in ['chuva', 'seca']}
    transforms = [d.GetGeoTransform() for d in ds.values()]
    for d, gt in zip(ds.values(), transforms):
        if d.GetSpatialRef().GetAuthorityCode(None) != '31983' or not np.allclose([gt[1], gt[2], gt[4], gt[5]], [3, 0, 0, -3]):
            raise ValueError('Esperadas imagens norte-acima de 3 m em EPSG:31983')
        if d.RasterCount != 8 or d.GetRasterBand(6).GetDescription() != 'Red' or d.GetRasterBand(8).GetDescription() != 'NIR':
            raise ValueError('Conferir bandas: são esperadas Red=6 e NIR=8 identificadas nos cabeçalhos')
    delta_origin = np.array([transforms[0][0] - transforms[1][0], transforms[0][3] - transforms[1][3]]) / 3
    if not np.allclose(delta_origin, np.round(delta_origin)):
        raise ValueError('Grades originais não estão alinhadas; não reamostrar silenciosamente')
    left = max(gt[0] for gt in transforms)
    top = min(gt[3] for gt in transforms)
    right = min(d.GetGeoTransform()[0] + d.RasterXSize * 3 for d in ds.values())
    bottom = max(d.GetGeoTransform()[3] - d.RasterYSize * 3 for d in ds.values())
    ncols, nrows = round((right-left)/3), round((top-bottom)/3)
    offset = args.stride // 2
    nx, ny = len(range(offset, ncols, args.stride)), len(range(offset, nrows, args.stride))
    if min(nx, ny) <= 0:
        raise ValueError('Sem extensão comum amostrável')
    spacing = args.stride * 3
    x0 = left + (offset + .5) * 3 - spacing / 2
    y0 = top - (offset + .5) * 3 + spacing / 2
    bounds = [x0, y0 - ny * spacing, x0 + nx * spacing, y0]
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(31983)
    sample_gt = (x0, spacing, 0., y0, 0., -spacing)

    def grid():
        mem = gdal.GetDriverByName('MEM').Create('', nx, ny, 1, gdal.GDT_Byte)
        mem.SetProjection(srs.ExportToWkt())
        mem.SetGeoTransform(sample_gt)
        mem.GetRasterBand(1).Fill(0)
        return mem

    def burn(path, where=None, value=1, attribute=None):
        vector = ogr.Open(str(path), 0)
        layer = vector.GetLayer()
        if where:
            layer.SetAttributeFilter(where)
        if not layer.GetSpatialRef().IsSame(srs):
            source_srs = layer.GetSpatialRef().Clone()
            source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            target_srs = srs.Clone()
            target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            transform = osr.CoordinateTransformation(source_srs, target_srs)
            projected = ogr.GetDriverByName('MEM').CreateDataSource('')
            target_layer = projected.CreateLayer('projected', srs=target_srs, geom_type=layer.GetGeomType())
            for field in layer.schema:
                target_layer.CreateField(field)
            for feature in layer:
                geometry = feature.GetGeometryRef().Clone()
                geometry.Transform(transform)
                target_feature = ogr.Feature(target_layer.GetLayerDefn())
                target_feature.SetFrom(feature)
                target_feature.SetGeometry(geometry)
                target_layer.CreateFeature(target_feature)
            layer = target_layer
        mem = grid()
        options = ['ATTRIBUTE=' + attribute] if attribute else []
        gdal.RasterizeLayer(mem, [1], layer, burn_values=[value], options=options)
        return mem.ReadAsArray()

    basin = burn(paths['bacia']) == 1
    print('Grade amostral', nx, ny, 'pontos na bacia', int(basin.sum()), flush=True)
    ndvi = {}
    for season, d in ds.items():
        print('Lendo bandas', season, flush=True)
        vrt = gdal.Translate('', d, format='VRT', bandList=[6, 8])
        mem = gdal.Warp('', vrt, format='MEM', dstSRS='EPSG:31983', outputBounds=bounds,
                        width=nx, height=ny, resampleAlg='near', dstNodata=0, overviewLevel='NONE')
        red, nir = mem.ReadAsArray().astype(np.float32)
        # Confirm that sampled values are actual original pixels, not averages.
        for row, col in [(0, 0), (ny//2, nx//2), (ny-1, nx-1)]:
            x = x0 + (col+.5)*spacing
            y = y0 - (row+.5)*spacing
            gt = d.GetGeoTransform()
            source_col, source_row = round((x-gt[0])/3-.5), round((gt[3]-y)/3-.5)
            source_red = d.GetRasterBand(6).ReadAsArray(source_col, source_row, 1, 1)[0, 0]
            source_nir = d.GetRasterBand(8).ReadAsArray(source_col, source_row, 1, 1)[0, 0]
            if red[row, col] != source_red or nir[row, col] != source_nir:
                raise ValueError('Reamostragem nao preservou os pixels originais esperados')
        valid = basin & np.isfinite(red) & np.isfinite(nir) & (red != 0) & (nir != 0) & ((red+nir) != 0)
        result = np.full(red.shape, np.nan, dtype=np.float32)
        np.divide(nir-red, nir+red, out=result, where=valid)
        valid &= (result >= -1) & (result <= 1)
        result[~valid] = np.nan
        ndvi[season] = result
    mb_ds = gdal.Warp('', str(paths['mapbiomas']), format='MEM', dstSRS='EPSG:31983',
                      outputBounds=bounds, width=nx, height=ny, resampleAlg='near', dstNodata=0, overviewLevel='NONE')
    if mb_ds.RasterCount not in (1, 2):
        raise ValueError('Verificar estrutura do MapBiomas: esperada uma banda de classes e alfa opcional')
    mb = mb_ds.GetRasterBand(1).ReadAsArray()
    if mb_ds.RasterCount == 2:
        if mb_ds.GetRasterBand(2).GetColorInterpretation() != gdal.GCI_AlphaBand:
            raise ValueError('A segunda banda do MapBiomas deve ser alfa, não outro ano')
        mb[mb_ds.GetRasterBand(2).ReadAsArray() == 0] = 0
    risk = burn(paths['risco'], attribute='risco')
    definitions = [('campestre', 12, 'Formação Campestre'), ('savanica', 4, 'Formação Savânica'),
                   ('florestal', 3, 'Formação Florestal')]
    ref_masks = {}
    zee = np.zeros((ny, nx), np.uint8)
    hits = np.zeros((ny, nx), np.uint8)
    for idx, (name, code, label) in enumerate(definitions, 1):
        selected = burn(paths['zee'], where=f"classe = '{label}' AND simplifica = 'Vegetação nativa remanescente'") == 1
        hits += selected
        zee[selected] = idx
        ref_masks[name] = selected & (mb == code) & basin
    conflicts = hits > 1
    common = basin & np.isfinite(ndvi['seca']) & np.isfinite(ndvi['chuva'])
    variables = {'seca': ndvi['seca'], 'chuva': ndvi['chuva'],
                 'media_sazonal': (ndvi['seca']+ndvi['chuva'])/2,
                 'diferenca_chuva_menos_seca': ndvi['chuva']-ndvi['seca']}
    groups = {name: mask & ~conflicts for name, mask in ref_masks.items()}
    groups['pastagem_mapbiomas_comparacao'] = (mb == 15) & basin
    groups['ausencia_remanescente_zee_comparacao'] = (risk == 2) & basin
    summary, rows, samples = {}, [], {}
    for name, mask in groups.items():
        paired = mask & common
        summary[name] = {'n_referencia': int(mask.sum()), 'n_pares_validos': int(paired.sum()),
                         'n_sem_par_valido': int((mask & ~common).sum()),
                         'estatisticas_pareadas': {v: stats(a[paired]) for v, a in variables.items()},
                         'n_por_situacao_risco': {str(k): int((paired & (risk == k)).sum()) for k in [0, 2, 3, 4, 5]}}
        for variable, a in variables.items():
            samples[name+'__'+variable] = a[paired]
            rows.append({'grupo': name, 'variavel': variable, **stats(a[paired])})
    overlaps = []
    names = list(ref_masks)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            item = {'formacao_a': a, 'formacao_b': b}
            for var in ['seca', 'chuva', 'media_sazonal']:
                ha = np.histogram(samples[a+'__'+var], bins=80, range=(-1, 1))[0].astype(float)
                hb = np.histogram(samples[b+'__'+var], bins=80, range=(-1, 1))[0].astype(float)
                item[var] = float(np.minimum(ha/ha.sum(), hb/hb.sum()).sum()) if ha.sum() and hb.sum() else None
            ha = np.histogram2d(samples[a+'__seca'], samples[a+'__chuva'], bins=40, range=[[-1, 1], [-1, 1]])[0]
            hb = np.histogram2d(samples[b+'__seca'], samples[b+'__chuva'], bins=40, range=[[-1, 1], [-1, 1]])[0]
            item['duas_datas_histograma_2d'] = float(np.minimum(ha/ha.sum(), hb/hb.sum()).sum()) if ha.sum() and hb.sum() else None
            overlaps.append(item)
    # Cross-tab preserves disagreements instead of silently deleting them.
    cross = []
    for idx, (name, _, _) in enumerate(definitions, 1):
        for code in np.unique(mb[basin]):
            n = int((basin & (zee == idx) & (mb == code) & ~conflicts).sum())
            if n:
                cross.append({'zee': name, 'codigo_mapbiomas': int(code), 'n_pontos': n})
    report = {
        'gerado_utc': datetime.now(timezone.utc).isoformat(),
        'estado': 'exploracao_preliminar_sem_classificacao_final',
        'fontes': 'copias_locais; nao houve download novo; colecao MapBiomas nao comprovada pelo cabecalho',
        'datas_planetscope': {c['chave_execucao']: c.get('data') for c in catalogo['camadas']
                             if c.get('chave_execucao') in ('chuva', 'seca')},
        'inventario_metodologico': {'arquivo': str(args.camadas), 'assinatura': fingerprint(args.camadas),
            'produtos_e_dependencias': catalogo['produtos'],
            'nota': 'Estados do inventário descrevem o desenvolvimento da metodologia; a execução atual é amostral.'},
        'amostragem': {'tipo': 'sistematica_em_centros_de_pixels_originais', 'stride_pixels': args.stride,
            'espacamento_m': spacing, 'resolucao_origem_m': 3, 'geotransform_grade_amostral': sample_gt,
            'n_pontos_bacia': int(basin.sum()), 'n_pares_validos': int(common.sum()),
            'n_conflitos_classes_zee': int((conflicts & basin).sum()), 'offset_pixels': offset},
        'metodo': {'ndvi': '(banda8_NIR-banda6_Red)/(banda8_NIR+banda6_Red)',
            'invalidos': 'fora_bacia, nodata_zero_em_qualquer_banda, nao_finito, denominador_zero, NDVI_fora_de_menos1_a1',
            'comparacoes': 'mesmos_pontos_validos_nas_duas_datas',
            'referencias': 'classe_igual_entre_MapBiomas_e_ZEE_e_simplifica_vegetacao_nativa_remanescente',
            'interseccao': 'concordancia_espacial_nos_centros_amostrais; nao_e_vetorizacao_de_interseccao_integral',
            'risco': 'codigo2=ausencia_de_Cerrado_nativo; 0=sem_cobertura; 3/4/5=niveis_de_risco',
            'sobreposicao': 'soma_minima_de_histogramas_normalizados;0=sem_sobreposicao;1=total;descritivo_nao_acuracia'},
        'limitacoes': ['UDM2 nao aplicado nos mosaicos segundo relatorios; mascaras separadas nao encontradas',
            'Sem validacao independente nem controle de nuvens/sombras por UDM2',
            'Pontos vizinhos nao independentes; nao foram calculados p-valores ou intervalos inferenciais',
            'Referencias historicas e de escalas distintas; grade de saida 3m nao implica acuracia tematica 3m',
            'NDVI calculado na amostra, nao foram produzidos rasters integrais novos',
            'Grupo de ausencia no ZEE inclui coberturas diversas e nao equivale a vegetacao nao nativa',
            'Nenhuma regra de inclusao em infraestrutura verde foi aplicada'],
        'grupos': summary, 'sobreposicoes_descritivas': overlaps, 'cruzamento_zee_mapbiomas': cross,
    }
    print('Calculando assinaturas das fontes', flush=True)
    report['arquivos_entrada'] = {name: fingerprint(path) for name, path in paths.items()}
    (args.out/'resultados.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (args.out/'estatisticas.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
    np.savez_compressed(args.out/'amostras.npz', **samples)
    print(json.dumps({'amostras_por_grupo': {k: v['n_pares_validos'] for k, v in summary.items()}, 'sobreposicoes': overlaps}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
