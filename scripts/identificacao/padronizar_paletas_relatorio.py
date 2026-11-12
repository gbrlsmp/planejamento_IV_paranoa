"""Alinha área/tipologias/contornos à paleta vigente, preservando os códigos."""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from PIL import Image
from paletas_identificacao import AVU_COLORS, FRAGMENT_AREA_COLORS
from exportar_limites_avu_web import GROUPS


def main():
    repo = Path(__file__).resolve().parents[2]
    catalog_path = repo / 'dados-mapas/catalogo.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    report_path = repo / 'dados-mapas/identificacao/resultados_identificacao.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    records = {}
    for theme in ('metricas', 'tipologias'):
        info = catalog[theme]
        for entry in info['classes']:
            entry[2] = FRAGMENT_AREA_COLORS[entry[0]] if theme == 'metricas' else AVU_COLORS[entry[1]]
        path = repo / f'dados-mapas/{theme}.png'
        with Image.open(path) as image:
            assert image.mode == 'P' and image.info['transparency'] == 0
            original = np.asarray(image).copy()
            palette = [0] * 768
            for code, _, color in info['classes']:
                palette[code*3:code*3+3] = bytes.fromhex(color[1:])
            image.putpalette(palette)
            image.save(path, transparency=0, optimize=True)
        with Image.open(path) as image:
            assert np.array_equal(original, np.asarray(image))
            assert image.info['transparency'] == 0
        info['revision'] = sha256(path.read_bytes()).hexdigest()[:16]
        records[theme] = {'dimensoes': list(original.shape[::-1]),
            'codigos_sha256': sha256(original.tobytes()).hexdigest(),
            'classes': info['classes'], 'bounds': info['bounds'], 'revision': info['revision']}
    report['fragmentos']['map']['classes'] = catalog['tipologias']['classes']
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    manifest_path = repo / 'dados-mapas/identificacao/limites-avu/manifesto.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for layer in manifest['camadas']:
        layer['cor'] = GROUPS[layer['id']]['cor']
    exporter = Path(__file__).with_name('exportar_limites_avu_web.py')
    manifest['codigo_sha256_utf8_lf'] = sha256(exporter.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    manifest.pop('revisao')
    manifest['revisao'] = sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    record = {'origem': 'Paleta final do uso do solo já adotada; paletas_identificacao.py',
        'tratamento': 'Somente cores; códigos, transparência, extensões e geometrias preservados.', 'mapas': records}
    (repo / 'dados-mapas/identificacao/paleta-relatorio.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('OK: área, tipologias e contornos harmonizados; códigos e geometrias preservados.')


if __name__ == '__main__':
    main()
