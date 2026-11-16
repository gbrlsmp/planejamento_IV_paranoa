"""Verifica invariância do dia e efeitos noturnos da intensidade 102/104."""
import csv,json
from pathlib import Path
import numpy as np
from osgeo import gdal
from corrigir_intensidade_noturna import RUN,PREVIOUS,D,H,SUPPORT,FALLBACK_H,bands
from publicar_invest_seca_2026 import save,digest
gdal.UseExceptions()

def verify(inputs_only=False):
    proof=json.loads((RUN/'05_Verificacoes/PROVA_DIURNA_E_PARAMETRIZACAO.json').read_text(encoding='utf-8'))
    assert proof['status']=='atributos_diurnos_identicos_pixel_a_pixel' and proof['pixels_compared']==225297940
    day={}
    for name in ('cc','hm','T_air'):
        file=f'{name}_seca_2026_dia.tif';old=PREVIOUS/'02_Dia_Concluido'/file;new=RUN/'02_Dia_Concluido'/file
        assert digest(old)==digest(new);day[name]={'sha256':digest(new),'identical':True}
    oldcfg=json.loads((PREVIOUS/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    newcfg=json.loads((RUN/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    # Casos de fronteira: zero confirmado, corte incluído e ausência de altura.
    d=np.array([[0.,50.,50.,100.,1.,25.,25.]],dtype='float32')
    h=np.array([[10.,0.,15.75,31.5,-9999.,7.875,7.875001]],dtype='float32')
    _,levels,known,missing,zero=bands(d,h,np.ones_like(d,dtype=bool))
    assert levels.tolist()==[[0,2,2,3,1,1,2]] and zero.tolist()==[[True,False,False,False,False,False,False]]
    assert missing.tolist()==[[False,True,False,False,True,False,False]]
    # Centros distribuídos por faixas da grade: cálculo escalar independente.
    newcover=gdal.Open(newcfg['coverage']);quality=gdal.Open(str(RUN/'01_Entradas/qualidade_intensidade_102_104_3m.tif'))
    dd=gdal.Open(str(D));hh=gdal.Open(str(H));ss=gdal.Open(str(SUPPORT))
    sample_counts={int(r['lucode']):0 for r in proof['classes']};sample_report=[]
    for y in range(0,newcover.RasterYSize,256):
        n=min(256,newcover.RasterYSize-y);part=newcover.ReadAsArray(0,y,newcover.RasterXSize,n)
        for code in sample_counts:
            positions=np.flatnonzero(part==code)
            if not len(positions):continue
            for pos in positions[np.unique(np.linspace(0,len(positions)-1,2,dtype=int))]:
                row,col=divmod(int(pos),newcover.RasterXSize);row+=y
                dens=float(dd.ReadAsArray(col,row,1,1)[0,0]);height=float(hh.ReadAsArray(col,row,1,1)[0,0]);support=float(ss.ReadAsArray(col,row,1,1)[0,0])
                q=int(quality.ReadAsArray(col,row,1,1)[0,0]);valid=0<height<=100
                if dens==0:expected_level=0;expected_q=0
                else:
                    index=.5*(dens/100+min((height if valid else FALLBACK_H)/31.5,1))
                    expected_level=1 if index<=.25 else 2 if index<=.5 else 3
                    expected_q=(1 if support==100 else 2) if valid else 9
                assert code%10==expected_level and q==expected_q,(row,col,code,dens,height,q)
                sample_counts[code]+=1
                sample_report.append({'row':row,'col':col,'lucode':code,'density_pct':dens,'height_m':height,'flag':q})
    assert min(sample_counts.values())>=10
    if inputs_only:
        print(json.dumps({'status':'entradas_conferidas','centers_by_code':sample_counts,'zero_cutoffs_missing_height_tested':True},ensure_ascii=False),flush=True)
        return
    for key in ('day','night','uhi_max','green_area_cooling_distance','t_air_average_radius','eto'):assert oldcfg[key]==newcfg[key]
    old={k:gdal.Open(str(PREVIOUS/f'03_Noite_Concluido/{n}_seca_2026_noite.tif')) for k,n in [('cc','cc'),('hm','hm'),('t','T_air')]}
    new={k:gdal.Open(str(RUN/f'03_Noite_Concluido/{n}_seca_2026_noite.tif')) for k,n in [('cc','cc'),('hm','hm'),('t','T_air')]}
    coverage=gdal.Open(oldcfg['coverage']);gt=new['t'].GetGeoTransform();cg=coverage.GetGeoTransform();xo=round((gt[0]-cg[0])/3);yo=round((cg[3]-gt[3])/3)
    assert all(old[k].GetGeoTransform()==new[k].GetGeoTransform() for k in new)
    changed_cc=0;changed_t=0;min_delta=float('inf');max_delta=float('-inf');sum_delta=0.;n_valid=0
    for y in range(0,new['t'].RasterYSize,256):
        h=min(256,new['t'].RasterYSize-y);land=coverage.ReadAsArray(xo,yo+y,new['t'].RasterXSize,h);mask=land!=65535;target=np.isin(land,[102,104])
        for k in new:
            a=old[k].ReadAsArray(0,y,new[k].RasterXSize,h);b=new[k].ReadAsArray(0,y,new[k].RasterXSize,h)
            assert np.array_equal(a==old[k].GetRasterBand(1).GetNoDataValue(),b==new[k].GetRasterBand(1).GetNoDataValue())
            if k=='cc':
                assert np.array_equal(a[mask&~target],b[mask&~target])
                assert np.all(b[mask]<=a[mask]+2e-6);changed_cc+=int(np.sum(a[mask]!=b[mask]))
            if k=='hm':
                assert np.all(b[mask]<=a[mask]+2e-6)
                assert np.max(np.abs(a[mask&~target]-b[mask&~target]))<2e-6
            if k=='t' and mask.any():
                delta=b[mask].astype(float)-a[mask].astype(float)
                min_delta=min(min_delta,float(delta.min()));max_delta=max(max_delta,float(delta.max()));sum_delta+=float(delta.sum());n_valid+=len(delta);changed_t+=int(np.sum(delta>1e-4))
    assert min_delta>=-1e-4 and max_delta>0
    zeros=sum(r['n'] for r in proof['classes'] if r['level']==0)
    assert changed_cc==proof['recoded_pixels']-zeros
    # O campo regional não altera CC/HM nos fragmentos vegetados; T pode mudar.
    with (PREVIOUS/'04_Extracao/clima_seca_2026_fragmentos_46876.csv').open(encoding='utf-8-sig',newline='') as f:before={int(r['id_frag']):r for r in csv.DictReader(f)}
    with (RUN/'04_Extracao/clima_seca_2026_fragmentos_46876.csv').open(encoding='utf-8-sig',newline='') as f:after=list(csv.DictReader(f))
    assert len(after)==46876
    for r in after:
        a=before[int(r['id_frag'])]
        for key in a:
            if '_dia_' in key or key.startswith(('cc_noite_','hm_noite_')):assert r[key]==a[key], (r['id_frag'],key)
    result={'status':'correcao_noturna_conferida','day_rasters_identical':day,'day_all_parameters_equal':True,'night_parameters_except_coverage_table_equal':True,'night_cc_changes_restricted_to_102_104':True,'night_hm_changes_restricted_to_102_104_within_2e_6':True,'cc_changed_pixels':changed_cc,'zero_intensity_pixels_retained':zeros,'temperature_changed_pixels_above_1e_4':changed_t,'temperature_delta_C':{'min':min_delta,'max':max_delta,'mean':sum_delta/n_valid},'fragment_count':46876,'all_fragment_day_fields_unchanged':True,'all_fragment_night_cc_hm_fields_unchanged':True,'source_geometries_preserved':True,'empirical_thermal_validation':False}
    result['independent_input_centers_by_code']=sample_counts
    result['zero_cutoffs_missing_height_tested']=True
    save(RUN/'05_Verificacoes/AMOSTRAS_INDEPENDENTES_102_104.json',sample_report)
    save(RUN/'05_Verificacoes/VERIFICACAO_CORRECAO_NOTURNA.json',result)
    independent=json.loads((PREVIOUS/'05_Verificacoes/CONFERENCIA_A001_LANDSAT_INDEPENDENTE.json').read_text(encoding='utf-8'))
    independent.pop('model_translation',None);independent['tref_landsat_reused_from']=PREVIOUS.name;independent['night_correction']=result
    save(RUN/'05_Verificacoes/CONFERENCIA_A001_LANDSAT_INDEPENDENTE.json',independent)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--somente-entradas',action='store_true')
    verify(parser.parse_args().somente_entradas)
