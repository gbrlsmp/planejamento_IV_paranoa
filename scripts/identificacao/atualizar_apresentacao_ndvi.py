"""Atualiza a apresentação das referências existentes sem refazer geometrias.

Estatísticas exploratórias usam todos os pares da amostra sistemática de 30 m.
Os cortes da classificação usam o censo independente do NDVI médio a 3 m.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image


def update(web, samples):
    exploration = json.loads((web / 'exploracao.json').read_text(encoding='utf-8'))
    if 'censo' in exploration:
        raise ValueError('A apresentação usa censo. Use calcular_censo_ndvi.py em saída nova; não substituir pelo registro amostral histórico.')
    references = json.loads((web / 'referencias.json').read_text(encoding='utf-8'))
    with np.load(samples, allow_pickle=False) as data:
        for key, group in exploration['grupos'].items():
            group['estatisticas'] = {}
            for season in ('seca', 'chuva'):
                values = data[key + '__' + season]
                if len(values) != group['n_pares_validos']:
                    raise ValueError('Amostras e manifesto divergem: ' + key)
                group['estatisticas'][season] = {
                    'media': float(np.mean(values, dtype=np.float64)),
                    'desvio_padrao': float(np.std(values, dtype=np.float64, ddof=0)),
                }
        exploration['grupos']['pastagem']['cor'] = '#915558'
    exploration['metodo']['estatisticas'] = (
        'Média e desvio padrão populacional espacial dos pares da amostra sistemática, '
        'por grupo e data, apresentados nas distribuições e no resumo média ± desvio. '
        'Não é desvio temporal por pixel, erro padrão ou censo dos cortes.'
    )
    exploration['metodo']['sankey'] = (
        'Histogramas agregados nas faixas [-1, 0.2, 0.35, 0.45, 0.55, 0.65, 0.75, 1]; '
        '100% dos pares por grupo e data; distribuições marginais, sem trajetórias individuais.'
    )
    exploration['apresentacao_atualizada'] = {
        'registro_cientifico_sha256': sha256((samples.parent / 'exploracao_ndvi.json').read_bytes()).hexdigest(),
        'amostras_sha256': sha256(samples.read_bytes()).hexdigest(),
        'codigo_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    references['areas'] = [a for a in references['areas'] if a['mapbiomas_codigo'] != 11]
    references['inclui_areas_umidas'] = False
    references['nota_apresentacao'] = (
        'Áreas úmidas omitidas somente desta tabela e das vistas de referência; '
        'fontes, amostras exploratórias e classe 11 do uso do solo preservadas.'
    )
    for key, layer in references['camadas'].items():
        path = web / Path(layer['imagem']).name
        image = Image.open(path)
        if image.mode != 'P':
            raise ValueError('Esperado PNG paletizado: ' + str(path))
        values = np.array(image)
        palette = image.getpalette()
        legend = []
        for entry in layer['legenda']:
            if 'alagado' in entry['nome'].lower() or entry['nome'].startswith('Áreas úmidas'):
                values[values == entry['codigo']] = 0
                continue
            if ((key == 'mapbiomas' and entry['codigo'] == 15)
                    or (key == 'zee' and entry['nome'] == 'Pecuária')):
                entry['cor'] = '#915558'
            palette[entry['codigo'] * 3:entry['codigo'] * 3 + 3] = bytes.fromhex(entry['cor'][1:])
            legend.append(entry)
        result = Image.fromarray(values)
        result.putpalette(palette)
        result.save(path, transparency=0, optimize=True)
        layer['legenda'] = legend
    # A mesma entrada e o mesmo código devem produzir a mesma revisão.
    revision_payload = {key: value for key, value in exploration.items() if key != 'revisao'}
    digest = sha256(json.dumps(revision_payload, sort_keys=True, ensure_ascii=False).encode('utf-8'))
    for key in sorted(references['camadas']):
        digest.update((web / Path(references['camadas'][key]['imagem']).name).read_bytes())
    revision = digest.hexdigest()[:16]
    exploration['revisao'] = references['revisao'] = revision
    for name, payload in [('referencias.json', references), ('exploracao.json', exploration)]:
        options = {'indent': 2} if name == 'referencias.json' else {'separators': (',', ':')}
        (web / name).write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, **options), encoding='utf-8')
    print(json.dumps({'revision': revision, 'groups': {k: v['estatisticas'] for k, v in exploration['grupos'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web', type=Path, required=True)
    parser.add_argument('--samples', type=Path, required=True)
    args = parser.parse_args()
    update(args.web, args.samples)
