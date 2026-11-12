"""Conferir geometrias, amostras, histogramas, proveniência e cópias web.

Validação de coerência computacional; não é validação temática independente.
Não cria nem altera arquivos de dados.
"""
import argparse
import hashlib
import json
from pathlib import Path

from preparar_referencias_ndvi import fingerprint, read_vectors, spatial_ref, GROUPS, polygonal
import numpy as np
import shapely
from osgeo import gdal
from PIL import Image


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--referencias', type=Path, required=True)
    parser.add_argument('--tabelas', type=Path, required=True)
    parser.add_argument('--figuras', type=Path, required=True)
    parser.add_argument('--publicacao', type=Path, required=True)
    args = parser.parse_args()
    local_text = (args.tabelas / 'exploracao_ndvi.json').read_text(encoding='utf-8')
    local = json.loads(local_text)
    public = json.loads((args.publicacao / 'exploracao.json').read_text(encoding='utf-8'))
    maps = json.loads((args.publicacao / 'referencias.json').read_text(encoding='utf-8'))
    original_base = Path(local['fontes']['bacia'][0]['arquivo']).parents[3]

    def source_path(item):
        return args.base / Path(item['arquivo']).relative_to(original_base)

    revision = hashlib.sha256(local_text.encode('utf-8')).hexdigest()[:16]
    presentation = public.get('apresentacao_atualizada')
    require(public['revisao'] == maps['revisao'], 'Revisões incompatíveis')
    if presentation:
        require(presentation['registro_cientifico_sha256'] == hashlib.sha256((args.tabelas / 'exploracao_ndvi.json').read_bytes()).hexdigest(), 'Registro científico alterado')
        require(presentation['amostras_sha256'] == hashlib.sha256((args.tabelas / 'amostras_ndvi_pareadas.npz').read_bytes()).hexdigest(), 'Amostras alteradas')
        require(presentation['codigo_sha256'] == hashlib.sha256(Path(__file__).with_name('atualizar_apresentacao_ndvi.py').read_bytes()).hexdigest(), 'Código de apresentação alterado')
    else:
        require(revision == public['revisao'], 'Revisão científica incompatível')
    for name in ('exploracao.json', 'referencias.json', 'mapbiomas.png', 'zee.png', 'intersecao.png'):
        require((args.figuras / name).read_bytes() == (args.publicacao / name).read_bytes(), 'Cópia de publicação diferente: ' + name)
    for source, items in local['fontes'].items():
        for item in items:
            path = source_path(item)
            require(path.is_file(), 'Fonte indisponível: ' + str(path))
            # Para auxiliares de shapefile, conferir exatamente os bytes deste item.
            h = hashlib.sha256()
            with path.open('rb') as f:
                for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(block)
            require(h.hexdigest() == item['sha256'], 'Fonte alterada: ' + source + '/' + path.name)
    if not presentation:
        require(fingerprint(Path(__file__).with_name('preparar_referencias_ndvi.py'))[0]['sha256'] == local['codigo'][0]['sha256'], 'Código difere da versão executada')
    else:
        require([item['sha256'] for item in public['codigo']] == [item['sha256'] for item in local['codigo']], 'Proveniência do gerador científico modificada')
    require(local['auditoria_mapbiomas']['divergentes'] == 0, 'Auditoria vetorial/raster com divergências')
    srs = spatial_ref(31983)
    saved, _ = read_vectors(args.referencias, srs)
    basin_records, _ = read_vectors(source_path(local['fontes']['bacia'][0]), srs)
    basin = shapely.union_all([r['geometry'] for r in basin_records])
    mb, _ = read_vectors(source_path(local['fontes']['mapbiomas_vetor'][0]), srs)
    zee, _ = read_vectors(source_path(local['fontes']['zee'][0]), srs)
    for ref in saved:
        definition = next(g for g in GROUPS if g[0] == ref['grupo'])
        m = shapely.union_all([r['geometry'] for r in mb if r['cod_sub'] == definition[2]]).intersection(basin)
        z = shapely.union_all([r['geometry'] for r in zee if r['classe'] == definition[3]
                              and r['simplifica'] == 'Vegetação nativa remanescente']).intersection(basin)
        expected = polygonal(m.intersection(z))
        geom = ref['geometry']
        require(geom.is_valid, 'Referência inválida: ' + ref['grupo'])
        require(expected.symmetric_difference(geom).area < .01, 'Interseção salva difere do cruzamento das entradas')
        area = next(a for a in local['areas'] if a['grupo'] == ref['grupo'])
        require(abs(geom.area / 10000 - area['intersecao_ha']) < 1e-8, 'Área vetorial difere da tabela')
        shown = next((a for a in maps['areas'] if a['grupo'] == ref['grupo']), None)
        if shown is not None:
            require(shown == area, 'Tabela publicada difere do registro científico')
    samples = np.load(args.tabelas / 'amostras_ndvi_pareadas.npz', allow_pickle=False)
    rng = np.random.default_rng(local['amostragem']['semente_grafico'])
    sources = {season: gdal.Open(str(source_path(local['fontes']['ndvi_' + season][0]))) for season in ('seca', 'chuva')}
    checks = 0
    for name, group in public['grupos'].items():
        dry = samples[name + '__seca']
        rain = samples[name + '__chuva']
        xs = samples[name + '__x']
        ys = samples[name + '__y']
        n = group['n_pares_validos']
        require(len(dry) == len(rain) == len(xs) == len(ys) == n, 'Pareamento inconsistente')
        require(np.all(np.isfinite(dry) & np.isfinite(rain) & (dry >= -1) & (dry <= 1) & (rain >= -1) & (rain <= 1)), 'NDVI inválido na amostra')
        if name == 'pastagem':
            geom = shapely.union_all([r['geometry'] for r in mb if r['cod_sub'] == 15]).intersection(basin)
        else:
            geom = next(r['geometry'] for r in saved if r['grupo'] == name)
        shapely.prepare(geom)
        require(np.all(shapely.intersects_xy(geom, xs, ys)), 'Ponto fora da referência: ' + name)
        for season, values in [('seca', dry), ('chuva', rain)]:
            hist = np.histogram(values, bins=local['amostragem']['bins'])[0]
            require(hist.tolist() == group['histogramas'][season] and hist.sum() == n, 'Histograma inconsistente')
            if presentation:
                stats = group['estatisticas'][season]
                require(abs(stats['media'] - float(np.mean(values, dtype=np.float64))) < 1e-14, 'Média inconsistente')
                require(abs(stats['desvio_padrao'] - float(np.std(values, dtype=np.float64, ddof=0))) < 1e-14, 'Desvio populacional inconsistente')
            source = sources[season]
            gt = source.GetGeoTransform()
            for i in np.linspace(0, n - 1, min(n, 100), dtype=int):
                col = round((xs[i] - gt[0]) / 3 - .5)
                row = round((gt[3] - ys[i]) / 3 - .5)
                require(source.ReadAsArray(col, row, 1, 1)[0, 0] == values[i], 'Valor amostrado difere do NDVI original')
                checks += 1
        index = np.sort(rng.choice(n, min(2500, n), replace=False))
        expected = np.round(np.column_stack((dry[index], rain[index])), 5)
        require(np.allclose(expected, group['pontos_grafico'], rtol=0, atol=1e-7), 'Subamostra gráfica não reproduzível')
    for name, layer in maps['camadas'].items():
        pic = Image.open(args.publicacao / (name + '.png'))
        a = np.asarray(pic)
        require(list(pic.size) == maps['dimensoes'], 'Dimensões PNG inconsistentes')
        require(set(np.unique(a)).issubset({0, *[e['codigo'] for e in layer['legenda']]}), 'Código PNG fora da legenda')
        colors = [e['cor'] for e in layer['legenda']]
        require(len(colors) == len(set(colors)), 'Cores repetidas impedem consulta unívoca no mapa')
        palette = pic.getpalette()
        for entry in layer['legenda']:
            actual = bytes(palette[entry['codigo'] * 3:entry['codigo'] * 3 + 3]).hex()
            require('#' + actual == entry['cor'], 'Paleta PNG diverge da legenda: ' + name)
            if entry['nome'] in ('Pastagem', 'Pecuária'):
                require(entry['cor'] == '#915558', 'Cor de pastagem incorreta: ' + name)
    if presentation:
        require({a['mapbiomas_codigo'] for a in maps['areas']} == {3, 4, 12}, 'Tabela de referência incorreta')
        require(public['grupos']['pastagem']['cor'] == '#915558', 'Cor de pastagem incorreta')
        require(all(not ('alagado' in e['nome'].lower() or e['nome'].startswith('Áreas úmidas')) for layer in maps['camadas'].values() for e in layer['legenda']), 'Área úmida na legenda de referência')
    print(f'OK: interseções integrais, áreas, todos os pontos nas referências, histogramas completos, {checks} consultas diretas aos NDVIs, subamostras reproduzíveis, fontes preservadas e cinco cópias web idênticas.')
    print('Revisão: ' + public['revisao'] + '. Coerência computacional conferida; sem validação temática independente.')


if __name__ == '__main__':
    main()
