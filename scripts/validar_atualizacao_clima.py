"""Confere publicação, dados meteorológicos, áreas e XLSX da atualização climática."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter
import bisect,csv,json,math
import pandas as pd
from openpyxl import load_workbook

WEB=Path(__file__).resolve().parents[1];C=WEB.parent/'02 BASE DE DADOS/02_Análises/01_Riscos/01_Clima'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        for key in ['href','src']:
            if key in a:self.links.append(a[key])
pages={}
def parse(path):
    if path not in pages:
        d=Page();d.feed(path.read_text(encoding='utf8'));pages[path]=d
    return pages[path]
errors=[];links=0
for name in ['diagnostico.html','aplicacao-invest.html','identificacao.html','index.html']:
    p=WEB/name;d=parse(p);assert len(d.ids)==len(set(d.ids)),name
    for link in d.links:
        u=urlsplit(link)
        if u.scheme or link.startswith('//'):continue
        target=p.parent/unquote(u.path) if u.path else p;links+=1
        if not target.exists():errors.append([name,link,'arquivo ausente']);continue
        if u.fragment and target.suffix=='.html' and unquote(u.fragment) not in parse(target).ids:errors.append([name,link,'âncora ausente'])
assert not errors,errors
data=json.loads((WEB/'dados-mapas/clima/inmet-exploracao.json').read_text(encoding='utf8'))
spotchecks=[]
for s in data['stations']:
    assert len(s['daily'])==365 and len({r['date'] for r in s['daily']})==365
    for season,expected in [('chuva',212),('seca',153)]:
        rec=[r for r in s['daily'] if r['season']==season];assert len(rec)==expected
        paired=[r for r in rec if r['joint_temp'] is not None]
        bins=Counter((bisect.bisect_left(s['sankey_cuts']['temp'],r['joint_temp']),bisect.bisect_left(s['sankey_cuts']['rh'],r['joint_rh'])) for r in paired)
        actual=Counter({(r['temp_bin'],r['rh_bin']):r['n'] for r in s['sankey_counts'] if r['season']==season})
        assert bins==actual and sum(actual.values())==s['summary'][season]['joint_days']
        for r in rec:
            assert (r['temp'] is not None)==(r['n_temp']>=20)
            assert (r['rh'] is not None)==(r['n_rh']>=20)
            assert (r['rain'] is not None)==(r['n_rain']==24)
    # Releitura independente com pandas de um dia por ano/estação.
    for year,day in [(2025,'2025-10-15'),(2026,'2026-06-15')]:
        source=next(x for x in data['sources'] if x['station']==s['id'] and f'01-01-{year}' in x['path'])
        frame=pd.read_csv(source['path'],sep=';',skiprows=8,encoding='cp1252',decimal=',',na_values=[-9999])
        utc=pd.to_datetime(frame.iloc[:,0]+' '+frame.iloc[:,1].str.replace(' UTC',''),format='%Y/%m/%d %H%M',utc=True)
        local=utc.dt.tz_convert('America/Sao_Paulo');part=frame[local.dt.strftime('%Y-%m-%d')==day]
        values=pd.to_numeric(part.iloc[:,7],errors='coerce');values=values[values.between(-60,60)]
        found=next(r for r in s['daily'] if r['date']==day)
        assert len(values)==found['n_temp']
        if len(values)>=20:assert abs(float(values.mean())-found['temp'])<=.000050001
        spotchecks.append([s['id'],day,len(values)])

r=json.loads((WEB/'dados-modelo/atualizacao-cobertura-clima.json').read_text(encoding='utf8'))
areas=list(csv.DictReader((WEB/'dados-modelo/areas_uso_cobertura_vias_2026.csv').open(encoding='utf-8-sig')))
assert len(areas)==10 and abs(sum(float(x['area_ha']) for x in areas)-105628.77)<1e-7
for row in areas:assert int(row['pixels'])==r['counts'][row['lucode']] and abs(float(row['area_ha'])-int(row['pixels'])*.0009)<1e-8
rows=list(csv.DictReader((WEB/'dados-modelo/tab_biofisica_completa_12classes.csv').open(encoding='utf-8-sig')))
codes={int(x['lucode']) for x in rows};assert len(rows)==12 and codes=={int(x) for x in r['aux_counts']}-{65535}
assert abs(float(next(x for x in rows if x['lucode']=='102')['kc'])-(.327539+.613452)/2)<1e-12
assert abs(float(next(x for x in rows if x['lucode']=='102')['albedo'])-(.208190+.231966)/2)<1e-12
assert float(next(x for x in rows if x['lucode']=='104')['building_intensity'])==0
book=load_workbook(C/'03_Tabelas/Biofisica/tabela_biofisica_atual.xlsx',data_only=True)
actual=list(book['Completa'].iter_rows(min_row=6,max_row=17,min_col=1,max_col=7,values_only=True))
for a,e in zip(actual,rows):
    assert a[0]==e['classe'] and a[1]==int(e['lucode'])
    for i,key in enumerate(['kc','green_area','shade','albedo','building_intensity'],2):assert abs(a[i]-float(e[key]))<1e-12
assert all('SSEBop' not in (WEB/'docs/referencias-clima.md').read_text(encoding='utf8') for _ in [0])
out={'html_pages':4,'local_links_and_anchors_verified':links,'stations':4,'daily_records':1460,'independent_hourly_source_spotchecks':spotchecks,'sankey_counts_verified':True,'table_rows':12,'land_cover_classes':10,'xlsx_cached_values_match_csv':True,'iv_preserved':r['iv_preserved'],'invest_executed':False}
(C/'08_Scripts_e_verificacoes/VALIDACAO_PUBLICACAO.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False))
