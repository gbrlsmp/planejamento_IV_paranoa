"""Contrato dos derivados web; executável no CI sem GIS nem bases locais."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'dados-mapas/fitopolis-2026'

def main():
    m=json.loads((ROOT/'manifesto.json').read_text(encoding='utf8'))
    checked=0
    for kind,count in [('hexagonos',1358654),('fragmentos',46876)]:
        info=m['units'][kind];assert info['count']==count
        for name,record in info['arrays'].items():
            data=(ROOT/kind/record['file']).read_bytes()
            assert len(data)==record['bytes']
            assert hashlib.sha256(data).hexdigest()==record['sha256']
            raw=gzip.decompress(data)
            assert len(raw)==8*count and record['dtype']=='float64'
            assert hashlib.sha256(raw).hexdigest()==record['raw_sha256']
            checked+=1
        for field,c in m['indicators'].items():
            assert field in info['arrays']
            assert c['coverage'] is None or c['coverage'] in info['arrays']
            assert all(f in info['arrays'] for f in c['details'])
            assert len(c['range'])==2 and c['range'][1]>=c['range'][0]
        if kind=='hexagonos':
            record=info['axial'];raw=gzip.decompress((ROOT/kind/record['file']).read_bytes());assert len(raw)==count*8
        image=info['image'];assert hashlib.sha256((ROOT/kind/image['file']).read_bytes()).hexdigest()==image['sha256']
        summaries=json.loads(gzip.decompress((ROOT/kind/info['summaries']).read_bytes()))
        for field in m['indicators']:
            for ra,summary in summaries[field].items():
                assert summary['area_m2']>=0 and summary['valid_m2']>=0
                tolerance=max(.1,summary['area_m2']*1e-8)
                assert summary['coverage_m2']<=summary['area_m2']+tolerance
                assert summary['valid_m2']<=summary['coverage_m2']+tolerance
        for ra,record in info['ras'].items():
            row=json.loads(gzip.decompress((ROOT/kind/record['file']).read_bytes()))
            assert len(row['indices'])==record['units']==len(row['areas'])
            assert len(row['indices'])==len(set(row['indices']))
            assert all(0<=v<count for v in row['indices']) and all(a>0 for a in row['areas'])
            assert abs(sum(row['areas'])-record['area_m2'])<.1
    validation=json.loads((ROOT/'validacao.json').read_text(encoding='utf8'))
    assert validation['status']=='ok' and validation['manual_checks']
    print(f'Fitópolis: {checked} atributos compactos íntegros; duas unidades; resumos e recortes coerentes.')

if __name__=='__main__':main()
