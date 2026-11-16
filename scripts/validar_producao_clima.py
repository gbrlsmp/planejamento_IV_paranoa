"""Confere estrutura, fontes, paleta, derivados e limites de publicação atuais."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import argparse,hashlib,json,subprocess,gzip,csv,math,statistics
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
    assert 'A045: fonte de Tref' not in climate and 'A001: fonte de Tref e ETo' in climate
    for note,_,_ in NOTES:assert tree.by_id('nota-clima-'+note)
    assert len([e for e in tree.elements if e['tag']=='article' and e['attrs'].get('class')=='method-card' and first['start']<=e['start']<tree.by_id('resultados-invest')['start']])==4
    assert tree.by_id('diagnostico-clima-atual')['start']>=tree.by_id('metodologia-clima')['end']
    assert len([e for e in tree.elements if 'data-invest-explorer' in e['attrs']])==4
    assert len([e for e in tree.elements if 'data-invest-view' in e['attrs']])==2
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
    assert m['fragment_results_published'] is True and m['risk_classification'] is False and m['relative_classification'] is True
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
    assert config['reference_station']=='A001' and config['reference_days']==153
    assert config['day']['t_ref']==24.265416609534256 and config['night']['t_ref']==19.714379846732786
    assert config['auxiliary_class_count']==18 and config['day_reused'] is True
    model=WEB/'dados-modelo'
    with (model/'tab_biofisica_completa_18classes.csv').open(encoding='utf-8-sig',newline='') as stream:
        bio={int(r['lucode']):r for r in csv.DictReader(stream)}
    with (model/'tab_biofisica_completa_12classes.csv').open(encoding='utf-8-sig',newline='') as stream:
        oldbio={int(r['lucode']):r for r in csv.DictReader(stream)}
    assert set(bio)==(set(oldbio)-{102,104})|set(range(1020,1024))|set(range(1040,1044))
    assert all(bio[k]==row for k,row in oldbio.items() if k not in (102,104))
    proof=json.loads((model/'invest-seca-2026'/config['day_reuse_proof']).read_text(encoding='utf-8'))
    assert proof['status']=='atributos_diurnos_identicos_pixel_a_pixel'
    assert proof['pixels_compared']==225297940 and proof['recoded_pixels']==15116363
    assert proof['class_count']==18 and proof['only_classes_recoded']==[102,104]
    assert proof['fields_equal']==['kc','shade','albedo','green_area'] and proof['other_codes_unchanged']
    assert proof['fallback_pixels']==484009
    assert sum(r['n'] for r in proof['classes'] if r['level']==0)==667654
    for row in proof['classes']:
        k=row['lucode'];base=row['base'];level=row['level'];bi=float(bio[k]['building_intensity'])
        assert k==base*10+level and row['known_n']+row['fallback_n']==row['n']
        assert bi==row['building_intensity']==row['sum']/row['known_n']
        assert (bi==0 if level==0 else (level-1)*.25<bi<=(.25 if level==1 else .5 if level==2 else 1))
        for field in proof['fields_equal']:assert bio[k][field]==oldbio[base][field]
    sources=json.loads((model/'invest-seca-2026/fontes_sha256.json').read_text(encoding='utf-8'))
    assert sources['inputs']['tab_biofisica_102_104_regional.csv']['sha256']==sha(model/'tab_biofisica_completa_18classes.csv')
    night_audit=json.loads((model/'invest-seca-2026/conferencia_independente.json').read_text(encoding='utf-8'))['night_correction']
    assert night_audit['status']=='correcao_noturna_conferida' and night_audit['cc_changed_pixels']==14448709
    assert night_audit['zero_intensity_pixels_retained']==667654 and night_audit['temperature_delta_C']['min']>=-1e-4
    assert night_audit['temperature_delta_C']['max']>0 and night_audit['zero_cutoffs_missing_height_tested']
    assert min(night_audit['independent_input_centers_by_code'].values())>=10
    assert night_audit['all_fragment_day_fields_unchanged'] and night_audit['all_fragment_night_cc_hm_fields_unchanged']
    assert len(proof['day_web_files_identical'])==6
    for file,value in proof['day_web_files_identical'].items():assert sha(out/file)==value
    for key,record in proof['day_rasters_identical'].items():
        assert record['identical'] and m['indicators'][{'T_air':'t'}.get(key,key)]['scenarios']['dia']['source_sha256']==record['sha256']
    if baseline:
        oldmanifest=json.loads(subprocess.run(['git','show',baseline+':dados-mapas/clima/urban-cooling-2026/manifesto.json'],cwd=WEB,check=True,capture_output=True).stdout)
        for key,ind in m['indicators'].items():
            assert ind['scenarios']['dia']==oldmanifest['indicators'][key]['scenarios']['dia']
    ficha=(WEB/'aplicacao-invest.html').read_text(encoding='utf-8')
    assert 'intensidade-102-104' in ficha and 'tab_biofisica_completa_18classes.csv' in ficha
    tref=json.loads((WEB/'dados-modelo/invest-seca-2026/tref_a001.json').read_text(encoding='utf-8'))
    daily_path=WEB/'dados-modelo/invest-seca-2026'/tref['daily_means_file'];assert sha(daily_path)==tref['daily_means_sha256']
    with daily_path.open(encoding='utf-8-sig',newline='') as f:daily=list(csv.DictReader(f))
    for p,key in [('dia','day'),('noite','night')]:
        rr=[r for r in daily if r['janela']==p]
        assert sorted(r['data_local'] for r in rr)==tref['datas'] and len(rr)==153
        assert abs(statistics.mean(float(r['media_ar_C']) for r in rr)-config[key]['t_ref'])<1e-12
    assert all(ind['class_breaks']['dia']==[.25,.5,.75] for key,ind in m['indicators'].items() if key!='t')
    for p,key in [('dia','day'),('noite','night')]:
        assert m['indicators']['t']['class_breaks'][p]==[config[key]['t_ref']+config['uhi_max']*v for v in (.25,.5,.75)]
    assert all(p.suffix not in ('.tif','.gpkg') for p in out.iterdir())
    seasonal=WEB/'dados-mapas/clima/superficie-sazonal'
    lst=json.loads((seasonal/'manifesto.json').read_text(encoding='utf-8'))
    assert lst['source_resolution_m']==30 and lst['effective_thermal_resolution_m']==100
    lc=lst['indicators']['lst'];assert lc['class_breaks']['seca']==lc['class_breaks']['chuva']
    assert set(lc['colors'])<=allowed
    for p,n in [('seca',13),('chuva',6)]:
        r=lc['scenarios'][p];assert len(lst['composition']['periods'][p]['dates'])==n
        assert sha(seasonal/r['file'])==r['sha256'] and sha(seasonal/r['count_file'])==r['count_sha256']
        with Image.open(seasonal/r['count_file']) as image:
            assert set(image.getdata())<=set(range(n+1))|{255}
        with Image.open(seasonal/r['file']) as image:
            assert image.mode=='RGBA' and list(image.size)==lst['size']
    diagnostic=WEB/'dados-mapas/clima/diagnostico-2026'
    dm=json.loads((diagnostic/'manifesto.json').read_text(encoding='utf-8'))
    assert dm['count']==46876 and sha(diagnostic/dm['data_file'])==dm['data_sha256']
    data=json.loads(gzip.decompress((diagnostic/dm['data_file']).read_bytes()))['rows']
    assert [r['id_frag'] for r in data]==list(range(1,46877))
    counts={}
    for r in data:
        assert len(r['center'])==2 and -90<=r['center'][0]<=90 and -180<=r['center'][1]<=180
        for key,ind in list(m['indicators'].items())+list(lst['indicators'].items()):
            for p in ind['scenarios']:
                value=r[f'{key}_{p}_mean'];actual=r[f'{key}_{p}_classe']
                index=sum(value>=v for v in ind['class_breaks'][p]) if value is not None else None
                labels=['Ruim','Médio','Bom','Muito bom'] if ind['higher_is_better'] else ['Muito bom','Bom','Médio','Ruim']
                assert actual==(labels[index] if index is not None else 'Sem dados')
                field=f'{key}_{p}_classe';counts.setdefault(field,dict.fromkeys(['Ruim','Médio','Bom','Muito bom','Sem dados'],0))[actual]+=1
        assert abs(r['cobertura_percentual']-100)<1e-8
        for p in ('seca','chuva'):assert 0<=r[f'lst_{p}_coverage_pct']<=100+1e-8
    assert counts==dm['classification_counts']
    with (WEB/'dados-modelo/invest-seca-2026/diagnostico_fragmentos_46876.csv').open(encoding='utf-8-sig',newline='') as stream:
        records=list(csv.DictReader(stream));assert len(records)==len(data)
        for record,row in zip(records,data):
            for key,value in record.items():
                assert (value=='' and row[key] is None) or value==str(row[key]) or (isinstance(row[key],(int,float)) and float(value)==row[key]), (row['id_frag'],key)
    ids=[]
    for file in sorted(diagnostic.glob('fragmentos-*.geojson.gz')):
        features=json.loads(gzip.decompress(file.read_bytes()))['features']
        ids.extend(f['properties']['id_frag'] for f in features)
    assert sorted(ids)==list(range(1,46877))
    assert sha(diagnostic/dm['ids_file'])==dm['ids_sha256']
    assert dm['bounds']==m['bounds'] and dm['size']==m['size'] and dm['display_resolution_m']==20
    with Image.open(diagnostic/dm['ids_file']) as image:
        assert image.mode=='RGBA' and list(image.size)==dm['size']
        pixels=image.tobytes()
        for red,green,blue,alpha in zip(pixels[0::4],pixels[1::4],pixels[2::4],pixels[3::4]):
            identifier=red*65536+green*256+blue
            assert 0<=identifier<=46876 and alpha==(255 if identifier else 0)
    for p in ('dia','noite'):
        z=dm['zones'][p];assert abs(z['threshold_C']-z['mean_C']-z['sd_C'])<1e-12
        assert z['minimum_area_ha']==2 and z['connectivity']==4
        assert sha(diagnostic/z['file'])==z['sha256']
        zones=json.loads((diagnostic/z['file']).read_text(encoding='utf-8'))['features']
        assert len(zones)==z['polygons']
        assert all(f['properties']['area_ha']>=2 and f['properties']['limiar_C']==z['threshold_C'] for f in zones)
        assert abs(sum(f['properties']['area_ha'] for f in zones)-z['area_ha'])<1e-6
    if regenerate:
        from completar_metodologia_clima import update
        paths=[WEB/n for n in ('diagnostico.html','aplicacao-invest.html','docs/metodologia-clima.md')]
        before={p:sha(p) for p in paths};update(WEB)
        assert {p:sha(p) for p in paths}==before,'Gerador não idempotente'
    result={'status':'ok','six_current_rasters':files,'landsat_seasonal_rasters':2,'current_fragments':len(data),'four_method_steps':True,'relative_classes_recomputed':True,'zones_checked':True,'palette':'existente','links_and_anchors':count,'inmet_inside_step_1':True,'all_twelve_notes_present':True,'fragment_results_published':True,'unchanged_panels_sha256':untouched,'generator_idempotent':regenerate,'browser_visual_review':'Não realizada: acesso ao navegador recusado nesta sessão.'}
    print(json.dumps(result,ensure_ascii=False))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-ref');p.add_argument('--regenerar',action='store_true')
    args=p.parse_args();validate(args.baseline_ref,args.regenerar)
