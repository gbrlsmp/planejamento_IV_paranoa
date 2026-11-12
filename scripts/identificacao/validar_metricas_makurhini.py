"""Confere cópias web do Makurhini contra os CSVs originais e GeoPackages."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from publicar_metricas_makurhini import INDICATORS, MAKURHINI_URL


def validate(base):
    repo = Path(__file__).resolve().parents[2]
    folder = base/'02_Análises/03_Ecologia/01_Fragmentação'
    output = repo/'dados-mapas/identificacao/metricas'
    manifest = json.loads((output/'manifesto.json').read_text(encoding='utf-8'))
    payload = {k: v for k, v in manifest.items() if k != 'revisao'}
    assert sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:16] == manifest['revisao']
    assert manifest['fonte_makurhini'] == MAKURHINI_URL
    assert [c['borda_m'] for c in manifest['cenarios']] == [45, 90]
    assert manifest['indicadores'] == [{'campo': f, 'nome': n, 'unidade': u} for f, n, u in INDICATORS]
    fields = [field for field, _, _ in INDICATORS]
    for scenario in manifest['cenarios']:
        distance = scenario['borda_m']
        for key in ('fragmentos', 'paisagem'):
            info = scenario[key]
            content = (output/info['arquivo']).read_bytes()
            assert content == (folder/info['arquivo']).read_bytes()
            assert len(content) == info['bytes'] and sha256(content).hexdigest() == info['sha256']
            rows = list(csv.DictReader(content.decode('utf-8-sig').splitlines()))
            assert len(rows) == info['registros']
            if key == 'fragmentos':
                assert [int(row['IdTemp']) for row in rows] == list(range(1, manifest['fragmentos']+1))
                path = folder/f'MK_Fragmentation_Bacia_Paranoa_{distance}m_AVU_PatchMetrics.gpkg'
                with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                    originals = dict((row[0], row[1:]) for row in db.execute(
                        'SELECT id_frag,'+','.join(fields)+' FROM metricas_fragmentos'))
                assert len(originals) == len(rows)
                assert all(tuple(float(row[field]) for field in fields) == originals[int(row['IdTemp'])] for row in rows)
            else:
                assert len(rows) == 13
                values = {row['Metric']: float(row['Value']) for row in rows}
                assert values['Number of patches'] == manifest['fragmentos'] == 46876
                assert values['Patch area (m2)'] == 554756895
    print('OK: quatro CSVs idênticos às fontes, 93.752 registros e oito campos iguais aos GeoPackages; resumos da paisagem e manifesto conferidos.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    validate(parser.parse_args().base.resolve())
