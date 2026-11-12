"""Copia as quatro tabelas adotadas do Makurhini, sem recalcular ou reformatar."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

INDICATORS = [
    ('Area', 'Área total', 'm²'), ('CA', 'Área de núcleo', 'm²'),
    ('CAPercent', 'Percentual de núcleo', '%'), ('Perimeter', 'Perímetro', 'm'),
    ('EdgePercent', 'Percentual de borda', '%'), ('PARA', 'Razão área/perímetro nesta execução', 'm'),
    ('ShapeIndex', 'Índice de forma', 'adimensional'), ('FRAC', 'Dimensão fractal', 'adimensional'),
]
MAKURHINI_URL = 'https://github.com/connectscape/Makurhini/blob/0010946ab2eef7f8d2bc4935f369869fc4c58671/R/MK_fragmentation.R'


def publish(base, output):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Usar uma saída nova e vazia')
    folder = base / '02_Análises/03_Ecologia/01_Fragmentação'
    output.mkdir(parents=True, exist_ok=True)
    scenarios = []
    for distance in (45, 90):
        scenario = {'borda_m': distance}
        for key, suffix in [('fragmentos', 'PatchMetrics'), ('paisagem', 'LandscapeMetrics')]:
            filename = f'MK_Fragmentation_Bacia_Paranoa_{distance}m_AVU_{suffix}.csv'
            payload = (folder / filename).read_bytes()
            rows = list(csv.DictReader(payload.decode('utf-8-sig').splitlines()))
            if key == 'fragmentos':
                assert [int(row['IdTemp']) for row in rows] == list(range(1, 46877))
                assert all(field in rows[0] for field, _, _ in INDICATORS)
            else:
                assert len(rows) == 13 and rows[0]['Metric'] == 'Patch area (m2)'
            (output / filename).write_bytes(payload)
            scenario[key] = {'arquivo': filename, 'sha256': sha256(payload).hexdigest(),
                             'bytes': len(payload), 'registros': len(rows)}
        scenarios.append(scenario)
    manifest = {'schema': 1, 'fragmentos': 46876, 'fonte_makurhini': MAKURHINI_URL,
        'geracao': 'GEOS/Python para geometrias; MK_Fragmentation no R para métricas, com area_unit=m2 e perimeter_unit=m.',
        'id': 'IdTemp dos CSVs corresponde ao id_frag dos GeoPackages adotados.',
        'indicadores': [{'campo': f, 'nome': n, 'unidade': u} for f, n, u in INDICATORS],
        'nota_para': 'A revisão executada calcula PARA = Area / Perimeter, embora o comentário da função descreva a razão inversa. Os valores originais foram preservados.',
        'cenarios': scenarios}
    manifest['revisao'] = sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16]
    (output/'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('OK: quatro CSVs originais, 46.876 registros por cenário e 13 indicadores da paisagem; revisão '+manifest['revisao'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(args.base.resolve(), args.output.resolve())
