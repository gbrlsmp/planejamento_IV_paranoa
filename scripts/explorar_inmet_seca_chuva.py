"""Caracterização exploratória INMET, 01/10/2025–30/09/2026, UTC−03.

Não recalcula ETo ou Tref. Preserva ausências e exporta dados verificáveis para
gráficos do site. Temperatura/UR: mínimo de 20 leituras válidas por dia.
Precipitação: 24 intervalos horários válidos. Sankey: pelo menos 20 pares T/UR.
"""
from pathlib import Path
from datetime import datetime,date,timedelta,timezone
from collections import defaultdict,Counter
import argparse,csv,io,json,math,hashlib,unicodedata
import numpy as np

START,END=date(2025,10,1),date(2026,9,30)
LOCAL=timezone(timedelta(hours=-3))
STATIONS={'A001':'Brasília','A045':'Águas Emendadas','A046':'Gama (Ponte Alta)','A047':'Paranoá (COOPA-DF)'}

def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn')
def val(s,lo,hi):
    try:v=float(s.replace(',','.'))
    except (ValueError,AttributeError):return None
    return v if math.isfinite(v) and lo<=v<=hi else None
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def avg(v):return round(float(np.mean(v)),4) if v else None
def dump(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf8')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--clima',type=Path,required=True);ap.add_argument('--web',type=Path,required=True);args=ap.parse_args()
    stationdata=[];sources=[];allrows=[]
    for code,name in STATIONS.items():
        days=defaultdict(lambda:defaultdict(list));hourly=defaultdict(list);seen={};dup=0;invalid=Counter();metadata={}
        for year in [2025,2026]:
            files=[p for p in (args.clima/'02_tabelas').rglob('*.CSV') if f'_{code}_' in p.name and f'01-01-{year}' in p.name]
            assert len(files)==1,(code,year,files)
            source=files[0];sources.append({'station':code,'path':str(source),'sha256':digest(source)})
            lines=source.read_bytes().decode('cp1252').splitlines();head=next(i for i,l in enumerate(lines) if l.startswith('Data;Hora'))
            for l in lines[:head]:
                if ';' in l:
                    k,v=l.split(';',1);metadata[norm(k).strip(':')]=v
            reader=csv.DictReader(io.StringIO('\n'.join(lines[head:])),delimiter=';')
            columns={norm(c):c for c in reader.fieldnames}
            def column(prefix):return next(c for n,c in columns.items() if n.startswith(prefix))
            keys={'temp':column('TEMPERATURA DO AR - BULBO'),'rh':column('UMIDADE RELATIVA DO AR,'),'rain':column('PRECIPITACAO TOTAL'),'wind':column('VENTO, VELOCIDADE HORARIA'),'rad':column('RADIACAO GLOBAL')}
            for raw in reader:
                dt=datetime.strptime(raw['Data']+' '+raw['Hora UTC'].split()[0],'%Y/%m/%d %H%M').replace(tzinfo=timezone.utc).astimezone(LOCAL)
                if not START<=dt.date()<=END and not START<=(dt-timedelta(hours=1)).date()<=END:continue
                if dt in seen:
                    assert seen[dt]==raw,'Duplicata conflitante';dup+=1;continue
                seen[dt]=raw
                values={k:val(raw[col],*(-60,60) if k=='temp' else (0,100) if k in ['rh','wind'] else (0,500) if k=='rain' else (0,10000)) for k,col in keys.items()}
                for k,v in values.items():
                    if v is None:invalid[k]+=1
                if START<=dt.date()<=END:
                    season='chuva' if dt.date()<date(2026,5,1) else 'seca';day=days[dt.date()]
                    for k in ['temp','rh','wind']:
                        if values[k] is not None:day[k].append(values[k]);hourly[(season,dt.hour,k)].append(values[k])
                    if values['temp'] is not None and values['rh'] is not None:day['pair_temp'].append(values['temp']);day['pair_rh'].append(values['rh'])
                intervalday=(dt-timedelta(hours=1)).date()
                if START<=intervalday<=END:
                    for k in ['rain','rad']:
                        if values[k] is not None:days[intervalday][k].append(values[k])
        records=[]
        for i in range((END-START).days+1):
            d=START+timedelta(days=i);v=days[d];season='chuva' if d<date(2026,5,1) else 'seca'
            row={'date':d.isoformat(),'season':season,'temp':avg(v['temp']) if len(v['temp'])>=20 else None,'rh':avg(v['rh']) if len(v['rh'])>=20 else None,'rain':round(sum(v['rain']),4) if len(v['rain'])==24 else None,'wind':avg(v['wind']) if len(v['wind'])>=20 else None,'joint_temp':avg(v['pair_temp']) if len(v['pair_temp'])>=20 else None,'joint_rh':avg(v['pair_rh']) if len(v['pair_rh'])>=20 else None,'n_temp':len(v['temp']),'n_rh':len(v['rh']),'n_rain':len(v['rain']),'n_joint':len(v['pair_temp'])}
            records.append(row);allrows.append({'station':code,**row})
        validpairs=[r for r in records if r['joint_temp'] is not None];assert validpairs
        cuts={k:[float(x) for x in np.quantile([r['joint_'+k] for r in validpairs],[1/3,2/3])] for k in ['temp','rh']}
        links=Counter()
        for row in validpairs:
            ti=int(np.searchsorted(cuts['temp'],row['joint_temp'],side='left'));ri=int(np.searchsorted(cuts['rh'],row['joint_rh'],side='left'))
            links[(row['season'],ti,ri)]+=1
        profiles=[]
        for season in ['chuva','seca']:
            for k in ['temp','rh']:
                for h in range(24):
                    values=hourly[(season,h,k)];q=[round(float(x),4) for x in np.quantile(values,[.25,.5,.75])] if values else [None]*3
                    profiles.append({'season':season,'variable':k,'hour':h,'n':len(values),'mean':avg(values),'q25':q[0],'median':q[1],'q75':q[2]})
        summary={}
        for season in ['chuva','seca']:
            s=[r for r in records if r['season']==season];summary[season]={'expected_days':len(s)}
            for k in ['temp','rh','rain','wind']:
                v=[r[k] for r in s if r[k] is not None];summary[season][k]={'n':len(v),'mean':avg(v),'median':round(float(np.median(v)),4) if v else None,'sum':round(sum(v),4) if k=='rain' and v else None}
            summary[season]['joint_days']=sum(r['joint_temp'] is not None for r in s)
        stationdata.append({'id':code,'name':name,'latitude':float(metadata['LATITUDE'].replace(',','.')),'longitude':float(metadata['LONGITUDE'].replace(',','.')),'daily':records,'profiles':profiles,'sankey_cuts':cuts,'sankey_counts':[{'season':s,'temp_bin':t,'rh_bin':r,'n':n} for (s,t,r),n in sorted(links.items())],'summary':summary,'duplicate_records':dup,'invalid_or_missing':dict(invalid)})
    result={'period':{'start':START.isoformat(),'end':END.isoformat(),'rainy':['2025-10-01','2026-04-30'],'dry':['2026-05-01','2026-09-30']},'timezone':'UTC-03:00','daily_min_readings':20,'rain_min_intervals':24,'sankey':'Dias com ≥20 pares horários T/UR; tercis conjuntos dos dois períodos por estação, limites comuns entre seca e chuva; categorias relativas, não limiares de risco. Cada ligação conta dias, não transições temporais ou causalidade.','notes':['Observações pontuais por data/hora local; precipitação da hora anterior pela data do início do intervalo.','Ausências preservadas; totais de chuva incluem somente dias com 24 intervalos válidos.','Os períodos têm 212 e 153 dias. Mostrar n e percentuais dentro do período.','Um ciclo observado não constitui normal climatológica. Esta exploração não altera os insumos ETo/Tref existentes.'],'stations':stationdata,'sources':sources}
    dump(args.web/'dados-mapas/clima/inmet-exploracao.json',result)
    output=args.clima/'03_Tabelas/Series_meteorologicas';output.mkdir(parents=True,exist_ok=True)
    with (output/'INMET_diario_seca_chuva_2025_2026.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
    report={'period':result['period'],'method':result['notes'],'sources':sources,'stations':[{k:s[k] for k in ['id','summary','sankey_cuts','duplicate_records','invalid_or_missing']} for s in stationdata]}
    dump(args.clima/'05_Analises_exploratorias/INMET_seca_chuva/RELATORIO_QA.json',report)
    print(json.dumps({s['id']:{season:s['summary'][season]['joint_days'] for season in ['chuva','seca']} for s in stationdata},ensure_ascii=False))

if __name__=='__main__':main()
