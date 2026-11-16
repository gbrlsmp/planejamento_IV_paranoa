"""Compõe LST diurna seca/chuva e resume nos fragmentos atuais, sem alterar fontes."""
from pathlib import Path
import csv,json,hashlib,math
import numpy as np
from osgeo import gdal,ogr,osr
from PIL import Image
from preparar_revisao_clima import CLIMA,RUN,WEB,SOURCE
from publicar_invest_seca_2026 import palette,digest,save
from identificacao.paletas_identificacao import FRAGMENT_AREA_COLORS,ZEE_COLORS,RISK_COLORS
gdal.UseExceptions();ogr.UseExceptions()

OUT=RUN/'07_Superficie_sazonal'
LANDSAT=CLIMA/'01_Fontes/Landsat'
COLORS=[ZEE_COLORS['Lagoas de Estabilização'],ZEE_COLORS['Represas, Lagos, Lagoas e Rios'],FRAGMENT_AREA_COLORS[1],ZEE_COLORS['Formação Campestre'],RISK_COLORS[4][1],RISK_COLORS[5][1]]

def write_tif(path,array,ref,dtype=gdal.GDT_Float32,nodata=-9999):
    ds=gdal.GetDriverByName('GTiff').Create(str(path),array.shape[1],array.shape[0],1,dtype,options=['TILED=YES','COMPRESS=DEFLATE'])
    ds.SetGeoTransform(ref.GetGeoTransform());ds.SetProjection(ref.GetProjection())
    ds.GetRasterBand(1).SetNoDataValue(nodata);ds.GetRasterBand(1).WriteArray(array);ds=None

def compose():
    assert not OUT.exists(), 'Composição existente: conferir sem sobrescrever.'
    OUT.mkdir()
    coverage=gdal.Open(json.loads((RUN/'configuracao_a001.json').read_text(encoding='utf-8'))['coverage'])
    gt=coverage.GetGeoTransform()
    # Grade comum métrica de 30 m, com origem alinhada à cobertura de trabalho.
    xsize=math.ceil(coverage.RasterXSize/10);ysize=math.ceil(coverage.RasterYSize/10)
    bounds=[gt[0],gt[3]-ysize*30,gt[0]+xsize*30,gt[3]]
    mask=gdal.GetDriverByName('MEM').Create('',xsize,ysize,1,gdal.GDT_Byte)
    mask.SetProjection(coverage.GetProjection());mask.SetGeoTransform((gt[0],30,0,gt[3],0,-30))
    vec=ogr.Open(str(RUN/'01_Entradas/bacia_paranoa_31983.gpkg'))
    gdal.RasterizeLayer(mask,[1],vec.GetLayer(),burn_values=[1],options=['ALL_TOUCHED=TRUE']);basin=mask.ReadAsArray()>0
    with (LANDSAT/'inventario_cenas.csv').open(encoding='utf-8-sig',newline='') as f:
        scenes=[r for r in csv.DictReader(f) if r['cobre_DF_integral']=='1']
    meta={'source':'Landsat 8/9 Collection 2 Level-2 ST_B10','source_resolution_m':30,'effective_thermal_resolution_m':100,'periods':{},'mask':'Pixels de 30 m que intersectam a bacia (ALL_TOUCHED); ST DN 293..61440; QA_PIXEL bits 0..5 ausentes; QA_RADSAT bit 11 ausente; ST_QA válido (sem corte adicional de incerteza); água incluída.','composition':'Média por pixel das observações diurnas válidas de cada período; contagem acompanha cada pixel. Mesma grade de 30 m, reamostragem nearest para alinhar as bandas. Cenas com cobertura integral do recorte DF do inventário, mesmas 13 da seca e 6 da chuva. Não é média de todas as horas ou dias da estação.'}
    for period,label in [('seco','seca'),('chuvoso','chuva')]:
        ss=sorted([r for r in scenes if r['periodo']==period],key=lambda r:r['data_utc'])
        assert len(ss)==(13 if period=='seco' else 6)
        total=np.zeros(basin.shape,dtype='float64');count=np.zeros(basin.shape,dtype='uint8');records=[]
        for sc in ss:
            arrays={};sources={}
            for band in ('ST_B10','QA_PIXEL','QA_RADSAT','ST_QA'):
                path=next((LANDSAT/sc['pasta']).glob('*_'+band+'.TIF'))
                # Zero é valor válido nas bandas QA; usar sentinela externa ao domínio.
                ds=gdal.Warp('',str(path),format='MEM',dstSRS='EPSG:31983',outputBounds=bounds,width=xsize,height=ysize,resampleAlg='near',outputType=gdal.GDT_Int32,dstNodata=-9999)
                arrays[band]=ds.ReadAsArray();sources[path.name]=digest(path)
            st,q,rad,uq=[arrays[b] for b in ('ST_B10','QA_PIXEL','QA_RADSAT','ST_QA')]
            good=basin&(st>=293)&(st<=61440)&((q&63)==0)&((rad&(1<<11))==0)&(uq>=0)&(uq<=32767)
            temp=st.astype('float64')*.00341802+149-273.15
            total[good]+=temp[good];count[good]+=1
            records.append({'id':sc['id'],'date':sc['data_utc'][:10],'valid_pixels':int(good.sum()),'sources_sha256':sources})
        mean=np.divide(total,count,out=np.full(total.shape,-9999.),where=count>0).astype('float32')
        write_tif(OUT/f'lst_{label}_30m.tif',mean,mask)
        write_tif(OUT/f'contagem_{label}_30m.tif',np.where(basin,count,255),mask,gdal.GDT_Byte,255)
        values=mean[count>0]
        meta['periods'][label]={'scenes':records,'dates':[s['date'] for s in records],'min':float(values.min()),'max':float(values.max()),'mean':float(values.mean()),'valid_pixels':int(len(values)),'basin_pixels':int(basin.sum()),'count_min':int(count[basin].min()),'count_max':int(count.max())}
        print(json.dumps({'lst':label,'dates':len(ss),'stats':{k:v for k,v in meta['periods'][label].items() if k not in ('scenes','dates')}}),flush=True)
    save(OUT/'metadados.json',meta)

def extract():
    ids=gdal.Open(str(RUN/'04_Extracao/id_frag_grade_3m.tif'));gt=ids.GetGeoTransform()
    results={};N=46876
    for period in ('seca','chuva'):
        raster=gdal.Open(str(OUT/f'lst_{period}_30m.tif'))
        accum={k:np.zeros(N+1,dtype='int64' if k=='n' else 'float64') for k in ('n','sum','sum2')}
        accum['min']=np.full(N+1,np.inf);accum['max']=np.full(N+1,-np.inf)
        for y in range(0,ids.RasterYSize,256):
            h=min(256,ids.RasterYSize-y);labels=ids.ReadAsArray(0,y,ids.RasterXSize,h)
            bound=[gt[0],gt[3]-(y+h)*3,gt[0]+ids.RasterXSize*3,gt[3]-y*3]
            ds=gdal.Warp('',raster,format='MEM',dstSRS='EPSG:31983',outputBounds=bound,width=ids.RasterXSize,height=h,resampleAlg='near',dstNodata=-9999)
            a=ds.ReadAsArray();valid=(labels>0)&np.isfinite(a)&(a!=-9999);lab=labels[valid];v=a[valid].astype(float)
            accum['n']+=np.bincount(lab,minlength=N+1);accum['sum']+=np.bincount(lab,weights=v,minlength=N+1);accum['sum2']+=np.bincount(lab,weights=v*v,minlength=N+1)
            np.minimum.at(accum['min'],lab,v);np.maximum.at(accum['max'],lab,v)
        mean=np.divide(accum['sum'],accum['n'],out=np.full(N+1,np.nan),where=accum['n']>0)
        sd=np.sqrt(np.maximum(np.divide(accum['sum2'],accum['n'],out=np.full(N+1,np.nan),where=accum['n']>0)-mean**2,0))
        results[period]=dict(accum,mean=mean,sd=sd)
    rows=[]
    with (RUN/'01_Entradas/preparacao.json').open(encoding='utf-8') as f:manifest=json.load(f)
    with ogr.Open(manifest['metric_source']) as vec:
        for feature in vec.GetLayer():
            ident=int(feature['id_frag']);row={'id_frag':ident,'area_m2':float(feature['Area'])}
            for period in results:
                a=results[period];row[f'lst_{period}_coverage_pct']=100*int(a['n'][ident])*9/row['area_m2']
                for stat in ('mean','min','max','sd'):
                    value=float(a[stat][ident]);row[f'lst_{period}_{stat}']=value if np.isfinite(value) else None
            rows.append(row)
    assert len(rows)==N
    with (OUT/'lst_fragmentos_46876.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(sorted(rows,key=lambda r:r['id_frag']))
    print(json.dumps({'lst_fragments':N,'missing_by_period':{p:int(np.sum(results[p]['n'][1:]==0)) for p in results}}),flush=True)

def publish():
    out=WEB/'dados-mapas/clima/superficie-sazonal';out.mkdir(exist_ok=True,parents=True)
    source_meta=json.loads((OUT/'metadados.json').read_text(encoding='utf-8'))
    rasters={p:gdal.Open(str(OUT/f'lst_{p}_30m.tif')) for p in ('seca','chuva')}
    pool=np.concatenate([a[a!=-9999] for a in [r.ReadAsArray() for r in rasters.values()]])
    cuts=[float(v) for v in np.quantile(pool,[.25,.5,.75])]
    limits=[math.floor(float(pool.min())),math.ceil(float(pool.max()))]
    config={'label':'Temperatura de superfície Landsat','unit':'°C','colors':COLORS,'range':limits,'higher_is_better':False,'class_breaks':{'seca':cuts,'chuva':cuts},'class_method':'Quartis dos pixels válidos das duas composições reunidas; mesmos cortes para seca e chuva. Qualidade térmica relativa, sem limiares de saúde.','scenarios':{}}
    meta={'schema':2,'periods':{'seca':'Seca','chuva':'Chuva'},'source_resolution_m':30,'effective_thermal_resolution_m':100,'web_resolution_m':30,'web_crs':'EPSG:3857','web_resampling':'average','indicators':{'lst':config},'composition':source_meta}
    bounds=None
    for period,raster in rasters.items():
        ds=gdal.Warp('',raster,format='MEM',dstSRS='EPSG:3857',xRes=30,yRes=30,outputBounds=bounds,resampleAlg='average',dstNodata=-9999)
        gt=ds.GetGeoTransform();a=ds.ReadAsArray();valid=np.isfinite(a)&(a!=-9999)
        box=[gt[0],gt[3]+gt[5]*ds.RasterYSize,gt[0]+gt[1]*ds.RasterXSize,gt[3]]
        if bounds is None:bounds=box
        assert bounds==box
        q=np.zeros(a.shape,dtype='uint16');q[valid]=np.floor(np.clip((a[valid].astype(float)-limits[0])/(limits[1]-limits[0]),0,1)*65534+.5).astype('uint16')+1
        rgba=np.zeros((*q.shape,4),dtype='uint8');rgba[:,:,0]=q>>8;rgba[:,:,1]=q&255;rgba[:,:,3]=valid*255
        name=f'lst-{period}-valores.png';Image.fromarray(rgba).save(out/name,optimize=True)
        count=gdal.Warp('',str(OUT/f'contagem_{period}_30m.tif'),format='MEM',dstSRS='EPSG:3857',outputBounds=bounds,width=ds.RasterXSize,height=ds.RasterYSize,resampleAlg='near',dstNodata=255).ReadAsArray()
        cname=f'contagem-{period}.png';Image.fromarray(count).save(out/cname,optimize=True)
        preview=np.zeros_like(rgba);preview[valid,:3]=palette(COLORS)[q[valid].astype(int)-1];preview[:,:,3]=valid*255
        im=Image.fromarray(preview);im.thumbnail((850,900));pname=f'lst-{period}-previa.png';im.save(out/pname,optimize=True)
        stats=source_meta['periods'][period]
        config['scenarios'][period]={'file':name,'sha256':digest(out/name),'preview':pname,'count_file':cname,'count_sha256':digest(out/cname),'count_max':len(stats['dates']),'native_stats':{'n':stats['valid_pixels'],'mean':stats['mean'],'min':stats['min'],'max':stats['max']},'source_file':f'lst_{period}_30m.tif','source_sha256':digest(OUT/f'lst_{period}_30m.tif')}
    meta.update(bounds=bounds,size=[ds.RasterXSize,ds.RasterYSize])
    references=[]
    with ogr.Open(str(LANDSAT/'QA_local_2026-11-14/areas_QA_500m_e_referencias.gpkg')) as vector:
        layer=vector.GetLayer();src=layer.GetSpatialRef();src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dst=osr.SpatialReference();dst.ImportFromEPSG(4326);dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        tx=osr.CoordinateTransformation(src,dst)
        for f in layer:
            geom=f.GetGeometryRef().SimplifyPreserveTopology(9);geom.Transform(tx)
            references.append({'type':'Feature','properties':{'area_id':f['area_id'],'nome':f['nome'],'tipo':f['tipo']},'geometry':json.loads(geom.ExportToJson())})
    save(out/'referencias.geojson',{'type':'FeatureCollection','features':references})
    meta['reference_areas_file']='referencias.geojson'
    meta['reference_areas_sha256']=digest(out/'referencias.geojson')
    save(out/'manifesto.json',meta)
    save(WEB/'dados-modelo/invest-seca-2026/superficie_sazonal.json',source_meta)

if __name__=='__main__':
    import sys
    if '--publicar' in sys.argv:publish()
    else:compose();extract();publish()
