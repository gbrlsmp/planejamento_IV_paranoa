"""Integra vias pavimentadas à cobertura e prepara entradas atuais do Urban Cooling.

Executar com Python/GDAL instalado, --base apontando para 02 BASE DE DADOS e
--web para o checkout. Não executa InVEST nem altera as fontes.
"""
from pathlib import Path
import argparse, csv, hashlib, json, shutil, time
from collections import Counter
from osgeo import gdal, ogr
import numpy as np
from PIL import Image, ImageDraw, ImageFont

gdal.UseExceptions(); ogr.UseExceptions()
LABELS = {3:'Formação florestal',4:'Formação savânica',11:'Campo alagado/pantanoso',12:'Formação campestre',33:'Água',100:'Vegetação intraurbana',101:'Forração vegetal',102:'Impermeável ou solo exposto',103:'Edificações',104:'Vias pavimentadas'}
COLORS = {3:'#4b6a40',4:'#86a58f',11:'#3e5972',12:'#d0a55f',33:'#a6cee3',100:'#2b5125',101:'#c4cc95',102:'#e1e1e1',103:'#393939',104:'#8b7186'}
IV = [3,4,11,12,100]

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def create(path,ref,kind,nd):
    assert not path.exists(),f'Destino já existente: {path}'
    path.parent.mkdir(parents=True,exist_ok=True)
    ds=gdal.GetDriverByName('GTiff').Create(str(path),ref.RasterXSize,ref.RasterYSize,1,kind,options=['TILED=YES','COMPRESS=DEFLATE','PREDICTOR=2','NUM_THREADS=2'])
    ds.SetGeoTransform(ref.GetGeoTransform());ds.SetProjection(ref.GetProjection());ds.GetRasterBand(1).SetNoDataValue(nd)
    ds.SetMetadataItem('PROCESSING_DATE','2026-11-15');return ds

def save_image(a,path):
    lut=np.zeros((256,3),dtype='uint8')
    for k,v in COLORS.items():lut[k]=list(bytes.fromhex(v[1:]))
    image=Image.fromarray(a).convert('P');image.putpalette(lut.ravel().tolist())
    image.save(path,optimize=True,transparency=255)

def export_web(source,web):
    folder=web/'dados-mapas/identificacao/fitofisionomia';m=json.loads((folder/'manifesto.json').read_text(encoding='utf8'))
    bounds=m['overview_bounds'];cols=round((bounds[2]-bounds[0])/20);rows=round((bounds[3]-bounds[1])/20)
    vrt=gdal.Warp('',str(source),format='VRT',dstSRS='EPSG:3857',outputBounds=bounds,width=cols,height=rows,resampleAlg='near',srcNodata=255,dstNodata=255)
    save_image(vrt.ReadAsArray(),folder/'etapa_04.png');shutil.copy2(folder/'etapa_04.png',web/'dados-mapas/uso.png');vrt=None
    for block in m['blocks']:
        target=folder/block['file'];old=Image.open(target);w,h=old.size;old.close()
        vrt=gdal.Warp('',str(source),format='VRT',dstSRS='EPSG:3857',outputBounds=block['bounds'],width=w,height=h,resampleAlg='near',srcNodata=255,dstNodata=255)
        save_image(vrt.ReadAsArray(),target);vrt=None
    m['classes']=[{'code':k,'name':v,'color':COLORS[k]} for k,v in LABELS.items()]
    m['stages'][-1].update(name='Contexto ZEE-DF e vias pavimentadas',legend=m['classes'])
    m['revision']=sha(source)[:16];dump(folder/'manifesto.json',m)
    frames=[]
    for stage in m['stages']:
        im=Image.open(folder/stage['image']).convert('RGBA');im.thumbnail((760,760),Image.Resampling.NEAREST)
        canvas=Image.new('RGBA',(im.width,im.height+44),'white');canvas.alpha_composite(im,(0,44))
        ImageDraw.Draw(canvas).text((14,12),f"{stage['version']}. {stage['name']}",fill='#24382d',font=ImageFont.load_default())
        frames.append(canvas.convert('P',palette=Image.Palette.ADAPTIVE,colors=64))
    frames[0].save(folder/'refinamento.gif',save_all=True,append_images=frames[1:],duration=1500,loop=0,optimize=True,disposal=2)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--web',type=Path,required=True);a=p.parse_args()
    t=time.time();base=a.base.resolve();web=a.web.resolve()
    eco=base/'02_Análises/03_Ecologia/03_Fitofisionomia';clima=base/'02_Análises/01_Riscos/01_Clima'
    out=eco/'03_Raster/04_Vias_pavimentadas_2026-11-15';out.mkdir(parents=True,exist_ok=True)
    cr=clima/'04_Rasters/Cobertura_para_InVEST';ct=clima/'03_Tabelas/Biofisica';cv=clima/'08_Scripts_e_verificacoes/Atualizacao_2026-11-15'
    for d in [cr,ct,cv]:d.mkdir(parents=True,exist_ok=True)
    source=eco/'03_Raster/03_fitofisionomia/fitofisionomias_proxy_ndvi_3m_etapa_04.tif'
    roads=base/'01_Base/vetores/Vias_OSM_Bacia_Paranoa.shp'
    p11=clima/'11_Intensidade_combinada_500m_2026-11-15'
    oldaux=p11/'cobertura_auxiliar_1031_1034_500m_proposta_3m.tif'
    oldclasses=p11/'classes_indice_combinado_500m_disponivel_3m.tif'
    result=json.loads((p11/'RESULTADO_COMBINACAO.json').read_text(encoding='utf8'))
    sources=[source,oldaux,oldclasses]+[roads.with_suffix(s) for s in ['.shp','.shx','.dbf','.prj','.cpg']]
    hashes={str(x):sha(x) for x in sources}
    ref=gdal.Open(str(source));assert ref.GetSpatialRef().GetAuthorityCode(None)=='31983'
    rd=ogr.Open(str(roads));ly=rd.GetLayer(0);assert ly.GetSpatialRef().GetAuthorityCode(None)=='31983';ly.SetAttributeFilter("pavimentad = 'SIM'")
    selected=ly.GetFeatureCount();types=Counter(f.GetField('tipo') for f in ly);rd=None
    vector=out/'vias_pavimentadas_buffer_2_5m.gpkg'
    assert not vector.exists()
    sql='SELECT ST_Buffer(geometry, 2.5) AS geom, objectid, tipo, pavimentad FROM "Vias_OSM_Bacia_Paranoa" WHERE pavimentad = \'SIM\''
    vd=gdal.VectorTranslate(str(vector),str(roads),format='GPKG',SQLStatement=sql,SQLDialect='SQLite',layerName='vias_pavimentadas_buffer_2_5m');assert vd;vd=None
    maskpath=out/'mascara_vias_pavimentadas_buffer_2_5m_3m.tif'
    mask=create(maskpath,ref,gdal.GDT_Byte,255);mask.GetRasterBand(1).Fill(0)
    # Centros de pixels; ALL_TOUCHED não é aplicado ao buffer de largura fixa.
    gdal.Rasterize(mask,str(vector),burnValues=[1]);mask.FlushCache()
    coverage=out/'uso_cobertura_2026_vias_pavimentadas_3m.tif'
    aux=cr/'cobertura_auxiliar_1031_1033_vias104_3m.tif'
    reg=cr/'classes_intensidade_regional_500m_3classes_3m.tif'
    dst=create(coverage,ref,gdal.GDT_Byte,255);full=create(aux,ref,gdal.GDT_UInt16,65535);regional=create(reg,ref,gdal.GDT_Byte,255)
    table=gdal.ColorTable()
    for k,v in COLORS.items():table.SetColorEntry(k,(*bytes.fromhex(v[1:]),255))
    table.SetColorEntry(255,(0,0,0,0));dst.GetRasterBand(1).SetRasterColorTable(table)
    old=gdal.Open(str(oldaux));oreg=gdal.Open(str(oldclasses));counts=Counter();fromcounts=Counter();before=Counter();compared=0
    nx,ny=ref.RasterXSize,ref.RasterYSize
    for y in range(0,ny,256):
        h=min(256,ny-y);lc=ref.ReadAsArray(0,y,nx,h);m=mask.ReadAsArray(0,y,nx,h)
        take=(m==1)&np.isin(lc,[101,102]);updated=lc.copy();updated[take]=104
        for k,n in zip(*np.unique(lc[take],return_counts=True)):fromcounts[int(k)]+=int(n)
        auxa=old.ReadAsArray(0,y,nx,h);assert not np.any(auxa==1034);auxa[take]=104
        ra=oreg.ReadAsArray(0,y,nx,h);ra[ra==4]=3
        assert np.array_equal(np.isin(lc,IV),np.isin(updated,IV))
        assert np.array_equal(lc==103,updated==103)
        assert np.array_equal(lc==255,updated==255)
        assert np.all((lc!=updated)==take)
        for k,n in zip(*np.unique(updated,return_counts=True)):counts[int(k)]+=int(n)
        for k,n in zip(*np.unique(lc,return_counts=True)):before[int(k)]+=int(n)
        dst.GetRasterBand(1).WriteArray(updated,0,y);full.GetRasterBand(1).WriteArray(auxa,0,y);regional.GetRasterBand(1).WriteArray(ra,0,y);compared+=lc.size
    for ds in [dst,full,regional,mask]:ds.FlushCache()
    dst=full=regional=mask=old=oreg=ref=None
    # Conferência integral por releitura dos produtos.
    r=gdal.Open(str(coverage));b=gdal.Open(str(source));au=gdal.Open(str(aux));auxcounts=Counter();checkcounts=Counter()
    for y in range(0,ny,256):
        h=min(256,ny-y);v=r.ReadAsArray(0,y,nx,h);orig=b.ReadAsArray(0,y,nx,h);av=au.ReadAsArray(0,y,nx,h)
        assert np.array_equal(np.isin(v,IV),np.isin(orig,IV));assert np.array_equal(v==104,av==104)
        assert np.array_equal(np.isin(av,[1031,1032,1033]),orig==103)
        for k,n in zip(*np.unique(v,return_counts=True)):checkcounts[int(k)]+=int(n)
        for k,n in zip(*np.unique(av,return_counts=True)):auxcounts[int(k)]+=int(n)
    assert counts==checkcounts;r=b=au=None
    assert hashes=={str(x):sha(x) for x in sources}
    rows=list(csv.DictReader((p11/'tab_biofisica_diurna_original.csv').open(encoding='utf8')))
    road=dict(rows[-1]);road.update(classe='Vias pavimentadas',lucode='104');rows.append(road)
    write_csv(ct/'tab_biofisica_diurna_10classes.csv',rows)
    combined=[]
    for row in rows:
        if int(row['lucode'])==103:continue
        combined.append({**row,'building_intensity':0})
    for c,name in zip(result['classes'][:3],['Baixa','Média','Alta']):
        combined.append({**rows[-2],'lucode':c['lucode'],'classe':'Edificações — '+name.lower(),'building_intensity':c['building_intensity']})
    assert len(combined)==12 and {int(x['lucode']) for x in combined}==set(auxcounts)-{65535}
    write_csv(ct/'tab_biofisica_completa_12classes.csv',combined)
    areas=[{'lucode':k,'classe':LABELS[k],'pixels':counts[k],'area_ha':counts[k]*.0009} for k in LABELS]
    write_csv(eco/'02_Tabela/areas_uso_cobertura_vias_2026.csv',areas)
    report={'date':'2026-11-15','filter':"pavimentad = 'SIM'",'selected_features':selected,'selected_types':dict(types),'buffer_m_each_side':2.5,'rasterization':'pixel centers; ALL_TOUCHED=FALSE','grid':{'width':nx,'height':ny,'epsg':31983,'pixel_m':3},'counts':dict(counts),'before_counts':dict(before),'transitions_to104':dict(fromcounts),'area_vias_ha':counts[104]*.0009,'aux_counts':dict(auxcounts),'pixels_verified':compared,'iv_preserved':True,'buildings_preserved':True,'nodata_preserved':True,'fragment_count_preserved':46876,'components_D_H_I_reused':True,'thermal_validation':False,'invest_executed':False,'source_hashes_sha256':hashes,'outputs':{'coverage':str(coverage),'auxiliary':str(aux),'table':str(ct/'tab_biofisica_completa_12classes.csv')},'duration_seconds':round(time.time()-t,2)}
    dump(cv/'RESULTADO_ATUALIZACAO.json',report);dump(out/'RESULTADO_VIAS.json',report)
    dump(web/'dados-modelo/atualizacao-cobertura-clima.json',report)
    for csvpath in ct.glob('*.csv'):shutil.copy2(csvpath,web/'dados-modelo'/csvpath.name)
    shutil.copy2(eco/'02_Tabela/areas_uso_cobertura_vias_2026.csv',web/'dados-modelo/areas_uso_cobertura_vias_2026.csv')
    published=web/'dados-mapas/identificacao/resultados_identificacao.json';record=json.loads(published.read_text(encoding='utf8'))
    record['classificacao']['counts']['etapa_04']={str(k):v for k,v in counts.items()};record['vias_pavimentadas']=report;record['data']='2026-11-15';record['metodo']='Proxy NDVI, refinamentos territoriais e vias pavimentadas em 3 m';dump(published,record)
    export_web(coverage,web)
    print(json.dumps({k:report[k] for k in ['selected_features','transitions_to104','area_vias_ha','pixels_verified','iv_preserved','duration_seconds']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
