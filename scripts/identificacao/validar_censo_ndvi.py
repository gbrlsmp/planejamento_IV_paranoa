"""Confere fontes, censo, cortes e publicação; --recontar-dir faz outra passagem integral."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import shapely
from osgeo import gdal
from PIL import Image

from calcular_censo_ndvi import (SEASONS, BINS, aligned_sources, check_counts,
    check_adopted, code_fingerprint, public_record, geometries)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def recount(local, sources, offsets, directory):
    """Método separado: Welford combinado e bincount, em faixas de 257 linhas."""
    masks = {key: gdal.Open(str(directory / (key + '.tif')), gdal.GA_ReadOnly) for key in local['grupos']}
    checks = {key: {'n': 0, 'means': np.zeros(3), 'm2': np.zeros(3),
                    'joint': np.zeros(6400, dtype=np.int64)} for key in masks}
    width, height = sources['seca'].RasterXSize, sources['seca'].RasterYSize
    for y in range(0, height, 257):
        h = min(257, height-y)
        values = [sources[s].ReadAsArray(offsets[s][0], y+offsets[s][1], width, h) for s in SEASONS]
        good = np.ones((h, width), dtype=bool)
        for s, a in zip(SEASONS, values):
            good &= np.isfinite(a) & (a >= -1) & (a <= 1) & (a != sources[s].GetRasterBand(1).GetNoDataValue())
        for key, mask in masks.items():
            chosen = (mask.ReadAsArray(0, y, width, h) != 0) & good
            n = int(chosen.sum())
            if not n:
                continue
            data = [a[chosen] for a in values]
            means, m2 = [], []
            for a in data:
                a = a.astype(np.float64)
                mean = a.mean()
                means.append(mean)
                m2.append(np.sum((a-mean)**2))
            means, m2 = np.array(means), np.array(m2)
            state = checks[key]
            old_n = state['n']
            total = old_n+n
            delta = means-state['means']
            state['m2'] += m2 + delta*delta*old_n*n/total
            state['means'] += delta*n/total
            state['n'] = total
            indices = [np.minimum(np.searchsorted(BINS, a, side='right')-1, 79) for a in data[:2]]
            state['joint'] += np.bincount(indices[0]*80+indices[1], minlength=6400)
    for key, state in checks.items():
        expected = local['grupos'][key]
        require(state['n'] == expected['n_pares_validos'], 'Recontagem n: ' + key)
        require(np.array_equal(state['joint'].reshape(80, 80), expected['densidade_conjunta']), 'Recontagem conjunta: ' + key)
        for i, season in enumerate(SEASONS):
            actual = expected['estatisticas'][season]
            require(abs(state['means'][i]-actual['media']) < 1e-12, 'Recontagem média: ' + key)
            require(abs(np.sqrt(state['m2'][i]/state['n'])-actual['desvio_padrao']) < 1e-12, 'Recontagem desvio: ' + key)
    print('OK: recontagem integral independente em 257 linhas, Welford e bincount; todos os pixels, estatísticas e células conjuntas coincidem.')


def validate(base, references, tables, figures, web, recount_dir=None, local_path=None):
    local_path = local_path or tables / 'censo_ndvi.json'
    local = json.loads(local_path.read_text(encoding='utf-8'))
    public = json.loads((web / 'exploracao.json').read_text(encoding='utf-8'))
    maps = json.loads((web / 'referencias.json').read_text(encoding='utf-8'))
    require(public_record(local) == public, 'Publicação difere do censo local')
    require(public['revisao'] == maps['revisao'], 'Revisões incompatíveis')
    payload = {k: v for k, v in public.items() if k not in ('gerado_utc', 'revisao')}
    require(sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:16] == public['revisao'], 'Revisão não reproduzível')
    require('amostragem' not in public and public['censo']['resolucao_m'] == 3, 'Censo não adotado')
    for record in public['codigo']:
        require(code_fingerprint(Path(__file__).with_name(record['arquivo'])) == record, 'Código do censo alterado')
    original_base = Path(local['fontes']['bacia'][0]['arquivo']).parents[3]
    def actual_path(item):
        return base / Path(item['arquivo']).relative_to(original_base)
    for items in local['fontes'].values():
        for item in items:
            path = actual_path(item)
            require(path.stat().st_size == item['bytes'], 'Tamanho da fonte alterado: ' + path.name)
            digest = sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(8*1024*1024), b''):
                    digest.update(block)
            require(digest.hexdigest() == item['sha256'], 'Fonte alterada: ' + path.name)
    historical = json.loads((tables / 'exploracao_ndvi.json').read_text(encoding='utf-8'))
    for new, old in [('seca', 'ndvi_seca'), ('chuva', 'ndvi_chuva'), ('mapbiomas_vetor', 'mapbiomas_vetor'), ('bacia', 'bacia')]:
        require([r['sha256'] for r in local['fontes'][new]] == [r['sha256'] for r in historical['fontes'][old]], 'Fonte histórica alterada: ' + new)
    require([r['sha256'] for r in local['fontes']['referencias']] == [r['sha256'] for r in historical['produtos_locais']['referencias']], 'Referências científicas alteradas')
    check_counts(public['grupos'])
    require(check_adopted(public['grupos']) == public['conferencia_cortes'], 'Conferência dos cortes alterada')
    paths = {s: actual_path(local['fontes'][s][0]) for s in SEASONS}
    sources, offsets = aligned_sources(paths)
    shapes, _, _ = geometries(base, references)
    gt = sources['seca'].GetGeoTransform()
    checks = 0
    for key, points in local['auditoria_pontos'].items():
        xs = [gt[0]+(p['col']+.5)*3 for p in points]
        ys = [gt[3]-(p['row']+.5)*3 for p in points]
        require(np.all(shapely.covers(shapes[key], shapely.points(xs, ys))), 'Centro fora da referência: ' + key)
        for point in points:
            for s in SEASONS:
                value = sources[s].ReadAsArray(point['col']+offsets[s][0], point['row']+offsets[s][1], 1, 1)[0, 0]
                require(value == point[s], 'Leitura direta de NDVI divergente')
                checks += 1
    for name, layer in maps['camadas'].items():
        path = web / (name + '.png')
        # No estágio, as imagens permanecem na publicação corrente.
        if not path.exists():
            path = Path(__file__).resolve().parents[2] / 'dados-mapas/identificacao' / path.name
        image = Image.open(path)
        palette = image.getpalette()
        require(list(image.size) == maps['dimensoes'], 'Dimensões PNG incorretas')
        require(set(np.unique(np.asarray(image))).issubset({0, *[e['codigo'] for e in layer['legenda']]}), 'Classe PNG fora da legenda')
        for entry in layer['legenda']:
            require('#' + bytes(palette[entry['codigo']*3:entry['codigo']*3+3]).hex() == entry['cor'], 'Paleta divergente')
            if entry['nome'] in ('Pastagem', 'Pecuária'):
                require(entry['cor'] == '#915558', 'Cor de pastagem divergente')
    if figures:
        for name in ('exploracao.json', 'referencias.json', 'mapbiomas.png', 'zee.png', 'intersecao.png'):
            require((figures / name).read_bytes() == (web / name).read_bytes(), 'Cópia local/web divergente: ' + name)
    if recount_dir:
        recount(local, sources, offsets, recount_dir)
    print(f'OK: fontes e amostras históricas preservadas; censo, histogramas, densidades, parâmetros dos cortes e paletas coerentes; {checks} leituras diretas de NDVI. Revisão {public["revisao"]}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('base', 'referencias', 'tabelas', 'publicacao'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--figuras', type=Path)
    parser.add_argument('--local', type=Path)
    parser.add_argument('--recontar-dir', type=Path)
    args = parser.parse_args()
    validate(args.base, args.referencias, args.tabelas, args.figuras, args.publicacao, args.recontar_dir, args.local)
