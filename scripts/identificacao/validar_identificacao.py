from pathlib import Path
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter
import json,sqlite3,csv
from PIL import Image,ImageSequence
from osgeo import gdal
import numpy as np

gdal.UseExceptions()
import argparse
parser=argparse.ArgumentParser(description='Confere os produtos locais e a publicação da identificação adotada.')
parser.add_argument('--base',type=Path,required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[2]
base=args.base.resolve(); frag=base/'02_Análises/03_Ecologia/01_Fragmentação'; fit=base/'02_Análises/03_Ecologia/03_Fitofisionomia'
d=json.loads((repo/'dados-mapas/identificacao/resultados_identificacao.json').read_text(encoding='utf-8'))
for entry in d['rasters']:
    path=fit/'03_Raster/03_fitofisionomia'/entry['file']
    assert sha256(path.read_bytes()).hexdigest()==entry['sha256']
assert not list((fit/'03_Raster/03_fitofisionomia').glob('*_v2.tif'))
labels=[]
for distance in (45,90):
    path=frag/f'MK_Fragmentation_Bacia_Paranoa_{distance}m_AVU_PatchMetrics.gpkg'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        actual=dict(db.execute('SELECT cat_iv,COUNT(*) FROM metricas_fragmentos GROUP BY cat_iv'))
        assert actual==d['iv']['counts']
        labels.append(db.execute('SELECT id_frag,cat_iv FROM metricas_fragmentos ORDER BY id_frag').fetchall())
        count,area,core=db.execute('SELECT COUNT(*),SUM(Area),SUM(CA) FROM metricas_fragmentos').fetchone()
        assert count==d['fragmentos']['fragments']
        assert abs(area/10000-d['fragmentos']['vegetation_area_ha'])<1e-7
        assert abs(core-d['metricas'][str(distance)]['nucleo_m2'])<.001
        records={r[0]:r[1:] for r in db.execute('SELECT id_frag,Area,CA,CAPercent,Perimeter,EdgePercent,PARA,ShapeIndex,FRAC FROM metricas_fragmentos')}
        with (frag/f'MK_Fragmentation_Bacia_Paranoa_{distance}m_AVU_PatchMetrics.csv').open(encoding='utf-8',newline='') as f:
            for row in csv.DictReader(f):
                assert np.array_equal(records[int(row['IdTemp'])],[float(row[k]) for k in ['Area','CA','CAPercent','Perimeter','EdgePercent','PARA','ShapeIndex','FRAC']])
assert labels[0]==labels[1]
with sqlite3.connect((frag/'fragmentos_vegetacao.gpkg').as_uri()+'?mode=ro',uri=True) as db:
    assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    assert dict(db.execute('SELECT classe_avu,COUNT(*) FROM fragmentos_vegetacao GROUP BY classe_avu'))==d['fragmentos']['avus']

assets=repo/'dados-mapas/identificacao/fitofisionomia'
manifest=json.loads((assets/'manifesto.json').read_text(encoding='utf-8'))
assert len(manifest['blocks'])==46
assert all((assets/b['file']).is_file() for b in manifest['blocks'])
assert (repo/'dados-mapas/uso.png').read_bytes()==(assets/'etapa_04.png').read_bytes()
with Image.open(assets/'refinamento.gif') as gif:
    assert gif.n_frames==4
    assert all(frame.info['duration']==1500 for frame in ImageSequence.Iterator(gif))
catalog=json.loads((repo/'dados-mapas/catalogo.json').read_text(encoding='utf-8'))
for key in ['uso','iv','metricas','tipologias']:
    assert catalog[key]['revision']==sha256((repo/f'dados-mapas/{key}.png').read_bytes()).hexdigest()[:16]
assert catalog['uso']['bounds']==manifest['overview_bounds']
assert catalog['iv']['classes']==d['iv']['map']['classes']

class Page(HTMLParser):
    def __init__(self): super().__init__(); self.ids=[]; self.links=[]; self.tables=[]; self.stack=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        for a in ['href','src']:
            if a in attrs:self.links.append(attrs[a])
        if tag=='tbody':self.tables.append(0)
        if tag=='p' and self.tables:raise AssertionError('Parágrafo dentro de tbody')
    def handle_endtag(self,tag):
        if tag=='tbody':self.tables.pop()
for name in ['identificacao.html','index.html','mapa.html']:
    page=Page(); page.feed((repo/name).read_text(encoding='utf-8'))
    assert len(page.ids)==len(set(page.ids)),name+' contém IDs duplicados'
    for link in page.links:
        url=urlsplit(link)
        if url.scheme or link.startswith('//') or not url.path:continue
        target=repo/unquote(url.path)
        assert target.exists(),str(target)
    if name=='identificacao.html':
        text=(repo/name).read_text(encoding='utf-8')
        format_pt=lambda v, digits=4: f'{v:,.{digits}f}'.replace(',','|').replace('.',',').replace('|','.')
        for value in [format_pt(d['fragmentos']['fragments'],0),format_pt(d['fragmentos']['vegetation_area_ha']),format_pt(d['metricas']['45']['nucleo_ha']),format_pt(d['metricas']['90']['nucleo_ha']),format_pt(d['iv']['area_ha']['Hub 1']),format_pt(d['limite_residual'])]:
            assert value in text,value
        assert 'data-ndvi-sankey' in text
        assert 'data-reference-opacity' not in text
        for removed in ['data-ndvi-stat-scatter', 'data-extra-camp-past', 'data-extra-check']:
            assert removed not in text, removed
        assert 'quatro rasters novos de 3 m' not in text
print('OK: rasters promovidos, GeoPackages, CSVs, áreas, IV 45/90 m, 46 blocos, GIF, catálogos, números, estrutura HTML e arquivos vinculados.')
