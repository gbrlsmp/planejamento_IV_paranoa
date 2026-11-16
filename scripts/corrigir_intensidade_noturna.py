"""Intensidade regional em 102/104; prova diurna integral e nova execução noturna."""
from pathlib import Path
from collections import Counter
import csv,json,shutil,hashlib
import numpy as np
from osgeo import gdal
from publicar_invest_seca_2026 import save,digest
from preparar_revisao_clima import WEB,CLIMA,RUN as PREVIOUS
gdal.UseExceptions()

RUN=CLIMA/'06_Execucoes_InVEST/Seca_2026_A001_102_104_2026-11-16'
SCRATCH=Path(r'C:\Users\sampa\.codex\visualizations\2026\11\16\01a1e28f-51e3-7912-88b0-253b4c73ed21')/'tmp/invest-a001-102-104/night'
D=CLIMA/'04_Rasters/Ocupacao_horizontal/densidade_edificada_500m_percentual_3m.tif'
H=CLIMA/'04_Rasters/Alturas/altura_media_edificada_vizinhanca_500m_3m.tif'
SUPPORT=CLIMA/'04_Rasters/Alturas/cobertura_alturas_validas_janela_500m_percentual_3m.tif'
FALLBACK_H=6.445500373840332

def bands(d,h,mask):
    assert np.all(np.isfinite(d[mask])&(d[mask]>=0)&(d[mask]<=100))
    zero=mask&(d==0)
    known=mask&(d>0)&(h>0)&(h<=100)
    missing=mask&~zero&~known
    index=np.zeros(d.shape,dtype='float64')
    index[known]=.5*(d[known].astype(float)/100+np.minimum(h[known].astype(float)/31.5,1))
    index[missing]=.5*(d[missing].astype(float)/100+min(FALLBACK_H/31.5,1))
    level=np.zeros(d.shape,dtype='uint8')
    positive=known|missing
    level[positive]=1+(index[positive]>.25).astype('uint8')+(index[positive]>.5).astype('uint8')
    return index,level,known,missing,zero

def create(path,ref,kind,nodata):
    ds=gdal.GetDriverByName('GTiff').Create(str(path),ref.RasterXSize,ref.RasterYSize,1,kind,options=['TILED=YES','COMPRESS=DEFLATE','BIGTIFF=IF_SAFER'])
    ds.SetGeoTransform(ref.GetGeoTransform());ds.SetProjection(ref.GetProjection());ds.GetRasterBand(1).SetNoDataValue(nodata)
    return ds

def prepare():
    assert not RUN.exists(), 'Preservar rodada existente.'
    for folder in ('01_Entradas','04_Extracao','05_Verificacoes'): (RUN/folder).mkdir(parents=True,exist_ok=True)
    old=json.loads((PREVIOUS/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    ref=gdal.Open(old['coverage']);dd=gdal.Open(str(D));hh=gdal.Open(str(H));support=gdal.Open(str(SUPPORT))
    for ds in (dd,hh,support):
        assert ds.GetGeoTransform()==ref.GetGeoTransform() and ds.GetProjection()==ref.GetProjection()
        assert (ds.RasterXSize,ds.RasterYSize)==(ref.RasterXSize,ref.RasterYSize)
    with Path(old['biophysical_table']).open(encoding='utf-8-sig',newline='') as f:original=list(csv.DictReader(f))
    table={int(r['lucode']):r for r in original}
    inputs=[Path(old[k]) for k in ('coverage','biophysical_table','eto')]+[D,H,SUPPORT]
    hashes={str(p):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in inputs}
    totals={(base,level):{'n':0,'known_n':0,'sum':0.,'fallback_n':0} for base in (102,104) for level in range(4)}
    for y in range(0,ref.RasterYSize,256):
        n=min(256,ref.RasterYSize-y);lc=ref.ReadAsArray(0,y,ref.RasterXSize,n);d=dd.ReadAsArray(0,y,ref.RasterXSize,n);h=hh.ReadAsArray(0,y,ref.RasterXSize,n)
        index,level,known,missing,zero=bands(d,h,np.isin(lc,[102,104]))
        for base in (102,104):
            for k in range(4):
                take=(lc==base)&(level==k);available=take&(known|zero);r=totals[(base,k)]
                r['n']+=int(take.sum());r['known_n']+=int(available.sum());r['sum']+=float(index[available].sum());r['fallback_n']+=int((take&missing).sum())
    rows=[dict(r) for r in original if int(r['lucode']) not in (102,104)]
    coefficients={};summary=[]
    labels=['Sem edificações no entorno','Baixa','Média','Alta']
    for (base,k),r in totals.items():
        if not r['n']:continue
        assert r['known_n']>0, 'Faixa sem observações válidas: revisar antes de imputar coeficiente.'
        coefficient=0. if k==0 else r['sum']/r['known_n'];code=base*10+k
        coefficients[code]=coefficient
        row=dict(table[base]);row.update(lucode=str(code),classe=table[base]['classe']+' — '+labels[k].lower(),building_intensity=str(coefficient));rows.append(row)
        summary.append(dict(base=base,level=k,lucode=code,building_intensity=coefficient,**r))
    rows.sort(key=lambda r:int(r['lucode']))
    csv_path=RUN/'01_Entradas/tab_biofisica_102_104_regional.csv'
    with csv_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(original[0]));w.writeheader();w.writerows(rows)
    coverage=RUN/'01_Entradas/cobertura_auxiliar_102_103_104_regional_3m.tif'
    dst=create(coverage,ref,gdal.GDT_UInt16,65535)
    quality=create(RUN/'01_Entradas/qualidade_intensidade_102_104_3m.tif',ref,gdal.GDT_Byte,255)
    newtable={int(r['lucode']):r for r in rows};counts=Counter();changed=0;fallback=0
    for y in range(0,ref.RasterYSize,256):
        n=min(256,ref.RasterYSize-y);lc=ref.ReadAsArray(0,y,ref.RasterXSize,n);d=dd.ReadAsArray(0,y,ref.RasterXSize,n);h=hh.ReadAsArray(0,y,ref.RasterXSize,n);sup=support.ReadAsArray(0,y,ref.RasterXSize,n)
        target=np.isin(lc,[102,104]);index,level,known,missing,zero=bands(d,h,target)
        out=lc.copy();out[target]=lc[target]*10+level[target]
        assert np.array_equal(out[~target],lc[~target])
        for field in ('kc','shade','albedo','green_area'):
            old_lut=np.zeros(65536);new_lut=np.zeros(65536)
            for code,row in table.items():old_lut[code]=float(row[field])
            for code,row in newtable.items():new_lut[code]=float(row[field])
            assert np.array_equal(old_lut[lc],new_lut[out]), ('Atributo diurno alterado',field,y)
        dst.GetRasterBand(1).WriteArray(out,0,y)
        qa=np.zeros(lc.shape,dtype='uint8');qa[lc==65535]=255;qa[known&(sup==100)]=1;qa[known&(sup<100)]=2;qa[missing]=9
        quality.GetRasterBand(1).WriteArray(qa,0,y)
        u,nn=np.unique(out,return_counts=True);counts.update(dict(zip(map(int,u),map(int,nn))))
        changed+=int(target.sum());fallback+=int(missing.sum())
    dst=quality=None
    assert all(digest(Path(p))==r['sha256'] for p,r in hashes.items())
    proof={'status':'atributos_diurnos_identicos_pixel_a_pixel','previous_run':str(PREVIOUS),'pixels_compared':ref.RasterXSize*ref.RasterYSize,'recoded_pixels':changed,'only_classes_recoded':[102,104],'fields_equal':['kc','shade','albedo','green_area'],'other_codes_unchanged':True,'same_grid_mask_eto_weights_tref_uhi_distances':True,'day_reuse':'Saídas oficiais diurnas anteriores reaproveitadas após prova integral de equivalência dos atributos; nenhuma nova execução diurna é alegada.','zero_intensity':'D500 igual a zero conserva BI=0 em subclasse própria; não recebe a média positiva da faixa baixa.','coefficients':'Mesmos cortes <=0.25 / <=0.50 / >0.50 da 103. Média de I entre pixels com suporte disponível de cada nova subclasse; lacunas preenchidas não entram na estimação.','fallback_height_m':FALLBACK_H,'fallback_pixels':fallback,'classes':summary,'source_hashes':hashes,'class_count':len(rows),'counts':dict(counts),'physical_limit':'Intensidade construída de entorno, não armazenamento de calor medido do pavimento/solo.'}
    save(RUN/'05_Verificacoes/PROVA_DIURNA_E_PARAMETRIZACAO.json',proof)
    config=dict(old);config.update(coverage=str(coverage),biophysical_table=str(csv_path),status='correcao_noturna_102_104_preparada',invest_executed=False,auxiliary_class_count=len(rows),night_revision='Intensidade regional nas classes 102 e 104; 103 preservada',day_reused_from=str(PREVIOUS),preparation_script='scripts/corrigir_intensidade_noturna.py')
    save(RUN/'01_Entradas/configuracao_confirmada.json',config)
    shutil.copyfile(PREVIOUS/'01_Entradas/bacia_paranoa_31983.gpkg',RUN/'01_Entradas/bacia_paranoa_31983.gpkg')
    shutil.copyfile(PREVIOUS/'04_Extracao/id_frag_grade_3m.tif',RUN/'04_Extracao/id_frag_grade_3m.tif')
    prep=json.loads((PREVIOUS/'01_Entradas/preparacao.json').read_text(encoding='utf-8'))
    prep['input_files']={p:r for p,r in prep['input_files'].items() if p not in (old['coverage'],old['biophysical_table']) and not p.endswith('configuracao_a001.json')}
    for p in [coverage,csv_path,RUN/'01_Entradas/configuracao_confirmada.json',RUN/'01_Entradas/bacia_paranoa_31983.gpkg',D,H,SUPPORT]:prep['input_files'][str(p)]={'bytes':p.stat().st_size,'sha256':digest(p)}
    prep.update(pixels_by_code=dict(counts),day_reuse_proof=str(RUN/'05_Verificacoes/PROVA_DIURNA_E_PARAMETRIZACAO.json'))
    save(RUN/'01_Entradas/preparacao.json',prep)
    for filename in ('TREF_A001_RESULTADOS.json','Tref_A001_medias_diarias.csv'):
        shutil.copyfile(PREVIOUS/filename,RUN/filename)
    shutil.copytree(PREVIOUS/'07_Superficie_sazonal',RUN/'07_Superficie_sazonal')
    shutil.copytree(PREVIOUS/'02_Dia_Concluido',RUN/'02_Dia_Concluido')
    day=json.loads((PREVIOUS/'01_Entradas/argumentos_day.json').read_text(encoding='utf-8'));day['args']['workspace_dir']=str(PREVIOUS/'02_Dia_Concluido');day['reuse_proof']=str(RUN/'05_Verificacoes/PROVA_DIURNA_E_PARAMETRIZACAO.json')
    save(RUN/'01_Entradas/argumentos_day.json',day)
    status=json.loads((PREVIOUS/'05_Verificacoes/execucao_day_local.json').read_text(encoding='utf-8'));status.update(reused=True,previous_run=str(PREVIOUS),new_day_execution=False)
    save(RUN/'05_Verificacoes/execucao_day_local.json',status)
    night=json.loads((PREVIOUS/'01_Entradas/argumentos_night.json').read_text(encoding='utf-8'))
    night['args'].update(lulc_raster_path=str(coverage),biophysical_table_path=str(csv_path),aoi_vector_path=str(RUN/'01_Entradas/bacia_paranoa_31983.gpkg'),workspace_dir=str(SCRATCH))
    assert not SCRATCH.exists();save(RUN/'01_Entradas/argumentos_night.json',night)
    for filename in ('executar_invest.ps1','extrair_e_verificar.py','concluir_entrega.ps1'):
        shutil.copyfile(PREVIOUS/filename,RUN/filename)
    shutil.copyfile(Path(__file__),RUN/'preparar_execucao.py')
    print(json.dumps({'prepared':True,'classes':len(rows),'changed_pixels':changed,'fallback_pixels':fallback,'coefficients':summary},ensure_ascii=False),flush=True)

if __name__=='__main__':prepare()
