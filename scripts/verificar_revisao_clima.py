"""Conferência independente das referências A001 e composições sazonais locais."""
import csv,json,statistics,math
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import defaultdict
import numpy as np
from osgeo import gdal,ogr,osr
from preparar_revisao_clima import RUN,SOURCE,CLIMA,OLD
from publicar_invest_seca_2026 import save,digest
gdal.UseExceptions();ogr.UseExceptions()

def tref():
    result=json.loads((RUN/'TREF_A001_RESULTADOS.json').read_text(encoding='utf-8'))
    raw=Path(result['source']['path_atual'])
    assert digest(raw)==result['source']['sha256']
    with (SOURCE/'INMET_completude_diaria_janelas.csv').open(encoding='utf-8-sig',newline='') as f:
        daily={r['data_local']:r for r in csv.DictReader(f) if r['station']=='A001'}
    windows=defaultdict(list);count=defaultdict(int)
    with raw.open(encoding='latin-1',newline='') as f:
        for _ in range(9):next(f)
        for row in csv.reader(f,delimiter=';'):
            t=datetime.strptime(row[0]+' '+row[1][:4],'%Y/%m/%d %H%M').replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-3)))
            day=t.date().isoformat()
            if day not in daily:continue
            value=float(row[7].replace(',','.')) if row[7] else math.nan
            if not math.isfinite(value) or not -60<=value<=60:continue
            rise=datetime.fromisoformat(daily[day]['nascer_sol_local']);setting=datetime.fromisoformat(daily[day]['por_sol_local'])
            label='dia' if rise<=t<setting else 'noite';windows[(day,label)].append(value);count[day]+=1
    eligible=[]
    for d,r in daily.items():
        if count[d]>=20 and all(len(windows[(d,w)])>=math.ceil(.8*int(r[w+'_horas_esperadas'])) for w in ('dia','noite')):eligible.append(d)
    assert sorted(eligible)==result['datas'] and len(eligible)==153
    independent={w:statistics.mean(statistics.mean(windows[(d,w)]) for d in eligible) for w in ('dia','noite')}
    assert all(abs(independent[w]-result['tref'][w])<1e-12 for w in independent)
    return {'raw_csv_independent_read':True,'utc_to_local_and_solar_windows':True,'paired_dates':153,'tref':independent,'source_sha256':digest(raw)}

def surfaces():
    out=RUN/'07_Superficie_sazonal'
    meta=json.loads((out/'metadados.json').read_text(encoding='utf-8'))
    with (CLIMA/'01_Fontes/Landsat/inventario_cenas.csv').open(encoding='utf-8-sig',newline='') as f:scenes={r['id']:r for r in csv.DictReader(f)}
    checks=[]
    for period in ('seca','chuva'):
        ds=gdal.Open(str(out/f'lst_{period}_30m.tif'));a=ds.ReadAsArray();valid=np.argwhere(a!=-9999)
        choices=valid[np.random.default_rng(85).choice(len(valid),64,replace=False)]
        gt=ds.GetGeoTransform();source=ds.GetSpatialRef();source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        values=[[] for _ in choices]
        for record in meta['periods'][period]['scenes']:
            sc=scenes[record['id']];bands={b:gdal.Open(str(next((CLIMA/'01_Fontes/Landsat'/sc['pasta']).glob('*_'+b+'.TIF')))) for b in ('ST_B10','QA_PIXEL','QA_RADSAT','ST_QA')}
            target=bands['ST_B10'].GetSpatialRef();target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);tx=osr.CoordinateTransformation(source,target)
            inv=gdal.InvGeoTransform(bands['ST_B10'].GetGeoTransform())
            for i,(y,x) in enumerate(choices):
                xx,yy=gdal.ApplyGeoTransform(gt,float(x)+.5,float(y)+.5);xx,yy,_=tx.TransformPoint(xx,yy)
                px,py=gdal.ApplyGeoTransform(inv,xx,yy);px,py=math.floor(px),math.floor(py)
                if not (0<=px<bands['ST_B10'].RasterXSize and 0<=py<bands['ST_B10'].RasterYSize):continue
                st,q,rad,uq=[int(bands[b].ReadAsArray(px,py,1,1)[0,0]) for b in ('ST_B10','QA_PIXEL','QA_RADSAT','ST_QA')]
                if 293<=st<=61440 and not(q&63) and not(rad&(1<<11)) and 0<=uq<=32767:values[i].append(st*.00341802+149-273.15)
        counts=gdal.Open(str(out/f'contagem_{period}_30m.tif')).ReadAsArray();errors=[]
        for (y,x),vv in zip(choices,values):
            assert len(vv)==int(counts[y,x]) and len(vv)>0
            error=abs(statistics.mean(vv)-float(a[y,x]));assert error<5e-5;errors.append(error)
        checks.append({'period':period,'independent_native_pixel_checks':len(choices),'count_agrees':True,'maximum_mean_error_C':max(errors),'source_band_sampling':'Transformação independente dos centros para a grade nativa; leitura direta de ST e flags, sem gdal.Warp.'})
    return checks

def model_translation():
    old=json.loads((OLD/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    new=json.loads((RUN/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    result={}
    for period,folder,label in [('day','02_Dia_Concluido','dia'),('night','03_Noite_Concluido','noite')]:
        hashes={}
        for key in ('cc','hm'):
            filename=f'{key}_seca_2026_{label}.tif'
            hashes[key]=digest(OLD/folder/filename)==digest(RUN/folder/filename)
            assert hashes[key], key+' mudou apesar de Tref ser a única alteração científica'
        previous=gdal.Open(str(OLD/folder/f'T_air_seca_2026_{label}.tif'))
        current=gdal.Open(str(RUN/folder/f'T_air_seca_2026_{label}.tif'))
        assert previous.GetGeoTransform()==current.GetGeoTransform()
        delta=new[period]['t_ref']-old[period]['t_ref'];maximum=0.
        for y in range(0,current.RasterYSize,256):
            h=min(256,current.RasterYSize-y);a=previous.ReadAsArray(0,y,current.RasterXSize,h);b=current.ReadAsArray(0,y,current.RasterXSize,h)
            mask=a!=previous.GetRasterBand(1).GetNoDataValue();assert np.array_equal(mask,b!=current.GetRasterBand(1).GetNoDataValue())
            if mask.any():maximum=max(maximum,float(np.max(np.abs(b[mask].astype(float)-a[mask].astype(float)-delta))))
        assert maximum<1e-4, maximum
        result[period]={'cc_hm_hashes_equal_previous_run':hashes,'reference_shift_C':delta,'maximum_translation_error_C':maximum,'interpretation':'Trocar apenas Tref desloca a temperatura absoluta; preserva CC/HM e aproximadamente a amplitude espacial. Não aumenta o contraste do modelo.'}
    return result

if __name__=='__main__':
    result={'tref':tref(),'landsat':surfaces(),'source_files_modified':False}
    import sys
    if '--modelo' in sys.argv:result['model_translation']=model_translation()
    save(RUN/'05_Verificacoes/CONFERENCIA_A001_LANDSAT_INDEPENDENTE.json',result)
    print(json.dumps(result,ensure_ascii=False))
