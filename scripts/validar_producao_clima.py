"""Confere estrutura, fontes, paleta, derivados e limites de publicação atuais."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import argparse,hashlib,json,subprocess
from PIL import Image,ImageChops
from clima_html import Elements
from metodologia_clima_conteudo import NOTES
from identificacao.paletas_identificacao import FRAGMENT_AREA_COLORS,ZEE_COLORS,RISK_COLORS

WEB=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n') if path.suffix in ('.html','.md') else path.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self,text):
        super().__init__();self.ids=[];self.links=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        self.links += [attrs[k] for k in ('href','src') if k in attrs]


def validate(baseline=None,regenerate=False):
    page=(WEB/'diagnostico.html').read_text(encoding='utf-8');tree=Elements(page);climate=tree.fragment('clima')
    first=tree.by_id('clima-metodo-inmet');explorer=tree.by_id('inmet')
    assert first['start']<explorer['start']<explorer['end']<first['end']
    assert 'data-risk-map' not in climate and 'data-ident-map-theme' not in climate
    assert 'fragmentos-ids' not in climate and 'clima_seca_2026_fragmentos_46876' not in climate
    assert 'Execuções da cobertura atual ainda não realizadas' not in climate
    assert 'a confirmar' not in climate and 'etapa a executar' not in climate
    for note,_,_ in NOTES:assert tree.by_id('nota-clima-'+note)
    assert len([e for e in tree.elements if e['tag']=='article' and e['attrs'].get('class')=='method-card' and first['start']<=e['start']<tree.by_id('resultados-invest')['start']])==6
    assert page.index('invest-raster.js')<page.index('invest-producao.js')
    untouched={}
    if baseline:
        base=subprocess.run(['git','show',baseline+':diagnostico.html'],cwd=WEB,check=True,capture_output=True).stdout.decode('utf-8')
        for key in ('agua','sociedade'):
            assert Elements(base).fragment(key)==tree.fragment(key),key+' alterado'
            untouched[key]=hashlib.sha256(tree.fragment(key).encode()).hexdigest()
    parsed={};count=0
    for name in ('diagnostico.html','aplicacao-invest.html','identificacao.html','index.html'):
        path=WEB/name;text=path.read_text(encoding='utf-8');parsed[path]=Links(text)
        assert len(parsed[path].ids)==len(set(parsed[path].ids)),name
        Elements(text)
    for path,doc in list(parsed.items()):
        for link in doc.links:
            u=urlsplit(link)
            if u.scheme or link.startswith('//'):continue
            target=path.parent/unquote(u.path) if u.path else path;count+=1
            assert target.is_file(),(path.name,link)
            if u.fragment and target.suffix=='.html':
                if target not in parsed:parsed[target]=Links(target.read_text(encoding='utf-8'))
                assert unquote(u.fragment) in parsed[target].ids,(path.name,link)
    out=WEB/'dados-mapas/clima/urban-cooling-2026'
    m=json.loads((out/'manifesto.json').read_text(encoding='utf-8'))
    revision=m.pop('revision')
    assert hashlib.sha256(json.dumps(m,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]==revision
    assert m['fragment_results_published'] is False and m['risk_classification'] is False
    assert m['web_resampling']=='average' and m['source_resolution_m']==3 and m['web_resolution_m']==20
    allowed=set(FRAGMENT_AREA_COLORS.values())|set(ZEE_COLORS.values())|{r[1] for r in RISK_COLORS.values()}
    files=[]
    for key,indicator in m['indicators'].items():
        assert set(indicator['colors'])<=allowed
        assert set(indicator['scenarios'])=={'dia','noite'}
        for period,record in indicator['scenarios'].items():
            path=out/record['file'];assert sha(path)==record['sha256']
            with Image.open(path) as image:
                assert image.mode=='RGBA' and list(image.size)==m['size']
                r,g,b,a=image.split();assert b.getextrema()==(0,0)
                zero=ImageChops.multiply(r.point(lambda x:255 if x==0 else 0),g.point(lambda x:255 if x==0 else 0))
                assert ImageChops.difference(a,ImageChops.invert(zero)).getbbox() is None
            assert sha(out/record['preview'])==record['preview_sha256']
            assert len(record['source_sha256'])==64
            assert record['native_stats']['n']==117365300
            assert record['quantization_max_absolute_error']<=(indicator['range'][1]-indicator['range'][0])/65534/2+1e-6
            files.append(path.name)
    config=json.loads((WEB/'dados-modelo/invest-seca-2026/configuracao.json').read_text(encoding='utf-8'))
    assert config['invest_executed'] and config['green_area_cooling_distance']==450 and config['t_air_average_radius']==500
    assert not config['do_energy_valuation'] and not config['do_productivity_valuation']
    assert all(p.suffix not in ('.tif','.gpkg') for p in out.iterdir())
    if regenerate:
        from completar_metodologia_clima import update
        paths=[WEB/n for n in ('diagnostico.html','aplicacao-invest.html','docs/metodologia-clima.md')]
        before={p:sha(p) for p in paths};update(WEB)
        assert {p:sha(p) for p in paths}==before,'Gerador não idempotente'
    result={'status':'ok','six_current_rasters':files,'palette':'existente','links_and_anchors':count,'inmet_inside_step_1':True,'all_twelve_notes_present':True,'fragment_results_published':False,'unchanged_panels_sha256':untouched,'generator_idempotent':regenerate,'browser_visual_review':'Não realizada: acesso ao navegador recusado nesta sessão.'}
    print(json.dumps(result,ensure_ascii=False))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-ref');p.add_argument('--regenerar',action='store_true')
    args=p.parse_args();validate(args.baseline_ref,args.regenerar)
