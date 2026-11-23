"""Exporta arquivos compactos independentes, sem quantizar os resultados."""
import gzip
import hashlib
import json
import math
import shutil
import time
import numpy as np
import pandas as pd
import shapely
from PIL import Image
from osgeo import gdal,osr
from gerar_diagnostico_fitopolis import read_file, save, GPKG, USO, MOM
from fitopolis_fontes import WEB,RUN,FONTES

OUT=WEB/'dados-mapas/fitopolis-2026'

def digest(data):return hashlib.sha256(data).hexdigest()

def binary(path,array):
    a=np.asarray(array)
    data=a.tobytes(order='C');encoded=gzip.compress(data,compresslevel=6,mtime=0)
    path.write_bytes(encoded)
    return {'file':path.name,'dtype':str(a.dtype),'count':len(a),'bytes':len(encoded),'sha256':digest(encoded),'raw_sha256':digest(data)}

def jsonzip(path,data):
    path.write_bytes(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0))

def indicators():
    out={}
    def add(field,label,unit,coverage,details=(),note='',colors=None):
        out[field]={'label':label,'unit':unit,'coverage':coverage,'details':list(details),'note':note,'colors':colors or ['#fff3dd','#dfb778','#9d5e36','#522c25']}
    for prefix,label,unit in [('cc','Capacidade de resfriamento',''),('hm','Mitigação térmica',''),('t','Temperatura estimada do ar','°C')]:
        for period in ['dia','noite']:
            key=f'{prefix}_{period}'
            add(key+'_mean',label+' · '+period,unit,key+'_coverage_pct',[key+'_min',key+'_max',key+'_stdev'],
                'InVEST Urban Cooling 3.20.2, seca de 2026, referência A001. Média ponderada pela interseção exata com pixels válidos.',
                ['#e5eee7','#afcaa6','#568759','#264d3b'] if prefix!='t' else None)
    for period in ['seca','chuva']:
        key='lst_'+period
        add(key+'_mean','Temperatura de superfície · '+period,'°C',key+'_coverage_pct',[key+'_min',key+'_max',key+'_stdev'],
            'Composição Landsat diurna: 13 datas secas e 6 chuvosas. Grade de 30 m, térmico efetivo de 100 m. Não é temperatura do ar.')
    add('inundada_pct_valida','Proporção inundada · TR5','%','inundacao_coverage_pct',['inundacao_valid_m2','inundada_m2','profundidade_media_inundada_m','inundacao_max'],
        'Denominador: área válida. Resultados hidrológicos existentes, sem nova simulação. Lacunas são ausência de estimativa, não profundidade zero.',['#e8f1f6','#a4cfe2','#4c95c2','#164f77'])
    add('profundidade_media_inundada_m','Profundidade média na parcela inundada · TR5','m','inundacao_coverage_pct',['inundada_m2','inundada_pct_valida','inundacao_max'],
        'Média somente na parcela de profundidade positiva. Sem parcela inundada: média não aplicável. Sem área válida: ausência de estimativa.',['#e8f1f6','#a4cfe2','#4c95c2','#164f77'])
    add('inundacao_max','Profundidade máxima válida · TR5','m','inundacao_coverage_pct',['inundada_m2','inundada_pct_valida','profundidade_media_inundada_m'],
        'O máximo não indica a extensão inundada da unidade. Consulte também a proporção inundada.',['#e8f1f6','#a4cfe2','#4c95c2','#164f77'])
    add('edif_pct','Edificações','%',None,['edif_ocupada_m2','edif_dominio_m2'],
        'Fragmentos: interior + buffer de 30 m, limitado à bacia; a projeção das edificações é unida. Hexágonos: ocupação dentro da célula. Domínios diferentes: comparar dentro da mesma unidade de análise.')
    add('renda_sm','Renda contextual · Censo 2022','SM de 2022',None,['setor_pct_unidade','renda_reais'],
        'Rendimento médio dos responsáveis pelo domicílio com renda, no setor de maior sobreposição (V06004). SM de 2022: R$ 1.212. Não é renda per capita.',['#f1e9f7','#d4bfe5','#ae86c7','#502b77'])
    for key,classes,title in [('uso',USO,'Uso e cobertura'),('momentos',MOM,'Momentos da Água'),('pre',{0:'baixo',1:'medio',2:'alto',3:'muito_alto',4:'sobreposicao'},'PRE')]:
        for name in classes.values():
            display={'florestal':'formação florestal','savanica':'formação savânica','alagado':'campo alagado / área pantanosa','campestre':'formação campestre','agua':'água','vegetacao_intraurbana':'vegetação intraurbana','impermeavel_solo_exposto':'superfície impermeável ou solo exposto','edificacoes':'edificações','conducao':'condução','acomodacao':'acomodação','medio':'médio','sobreposicao':'sobreposição entre classes'}.get(name,name.replace('_',' '))
            add(f'{key}_pct_{name}',title+' · '+display,'%',key+'_coverage_pct',[],
                'Proporção da área integral da unidade; composição preservada. PRE: sobreposições entre classes são separadas, sem dupla contagem. Momentos da Água preserva a modelagem existente.',['#f2f4e6','#c5d2a3','#83a374','#355c43'])
    native=json.loads((WEB/'dados-mapas/clima/urban-cooling-2026/manifesto.json').read_text(encoding='utf8'))
    seasonal=json.loads((WEB/'dados-mapas/clima/superficie-sazonal/manifesto.json').read_text(encoding='utf8'))
    context=json.loads((WEB/'dados-mapas/contexto-riscos.json').read_text(encoding='utf8'))
    from identificacao.paletas_identificacao import FRAGMENT_AREA_COLORS
    for field,record in out.items():
        if field.startswith(('cc_','hm_','t_')):record['colors']=native['indicators'][field.split('_')[0]]['colors']
        elif field.startswith('lst_'):record['colors']=seasonal['indicators']['lst']['colors']
        elif field=='renda_sm':record['colors']=[v[2] for v in context['renda_sm']['classes']]
        elif field=='edif_pct':record['colors']=['#e1e1e1','#d0a55f','#b47e4f','#8d554e']
        elif field.startswith(('inund','profundidade')):record['colors']=['#acc6cb','#80b0b8','#496a6e','#3e5972']
        else:record['colors']=list(FRAGMENT_AREA_COLORS.values())
    return out

def id_image(kind):
    directory=OUT/kind;path=directory/'ids-20m.png'
    if path.exists():return json.loads((directory/'imagem.json').read_text())
    ds=gdal.OpenEx(str(GPKG),gdal.OF_VECTOR);feature=ds.GetLayerByName('bacia').GetNextFeature();basin=feature.GetGeometryRef().Clone()
    # Keep parent feature alive through Clone (OGR geometries are borrowed).
    source=osr.SpatialReference();source.ImportFromEPSG(31983);source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dest=osr.SpatialReference();dest.ImportFromEPSG(3857);dest.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    basin.Transform(osr.CoordinateTransformation(source,dest));xmin,xmax,ymin,ymax=basin.GetEnvelope()
    xmin=math.floor(xmin/20)*20;ymax=math.ceil(ymax/20)*20
    w=math.ceil((xmax-xmin)/20);h=math.ceil((ymax-ymin)/20)
    mem=gdal.GetDriverByName('MEM').Create('',w,h,1,gdal.GDT_UInt32)
    mem.SetProjection(dest.ExportToWkt());mem.SetGeoTransform([xmin,20,0,ymax,0,-20])
    field='id_hex' if kind=='hexagonos' else 'id_frag'
    gdal.RasterizeLayer(mem,[1],ds.GetLayerByName(kind),options=['ATTRIBUTE='+field])
    a=mem.ReadAsArray();rgb=np.stack([(a>>16)&255,(a>>8)&255,a&255],axis=-1).astype('uint8')
    Image.fromarray(rgb).save(path,optimize=True)
    info={'file':path.name,'bounds':[xmin,ymax-h*20,xmin+w*20,ymax],'size':[w,h],'resolution_3857_m':20,'sha256':digest(path.read_bytes()),'present_ids':int(len(np.unique(a))-1)}
    save(directory/'imagem.json',info);return info

def main():
    started=time.perf_counter();OUT.mkdir(exist_ok=True,parents=True)
    config=indicators();tables={kind:pd.read_feather(RUN/(kind+'_atributos.feather')) for kind in ['hexagonos','fragmentos']}
    for field,record in config.items():
        values=np.concatenate([tables[k][field].to_numpy(dtype='float64') for k in tables])
        valid=values[np.isfinite(values)]
        if field.endswith('_pct_valida') or '_pct_' in field or field=='edif_pct':limits=[0.,100.]
        elif field.startswith(('cc_','hm_')):limits=[0.,1.]
        else:limits=[float(valid.min()),float(valid.max())] if len(valid) else [0.,1.]
        record['range']=limits
    manifest={'schema':1,'date':'2026-11-23','title':'Sistema Fitópolis','method':'interseções exatas raster/polígono, estatísticas ponderadas pela fração coberta; vetores por união/interseção em EPSG:31983','indicators':config,'units':{},'hydrology':'Resultados existentes mantidos; uso do solo histórico; Lago Paranoá sem operação, dinâmica de nível ou remanso.','display':'IDs de 20 m no panorama podem omitir unidades pequenas. Hexágonos detalhados reconstruídos das coordenadas axiais; bordas recortadas cartograficamente. Fragmentos têm contornos de consulta simplificados em 3 m; GPKGs preservam geometria integral.','summary_method':'Área inserida no recorte e médias dos indicadores integrais ponderadas pela parcela de área válida proporcional. Não são novas extrações de raster dentro das RAs. RAs verificadas sem sobreposição material.'}
    for kind,frame in tables.items():
        directory=OUT/kind;directory.mkdir(exist_ok=True)
        arrays={}
        numeric=[c for c in frame if pd.api.types.is_numeric_dtype(frame[c])]
        for column in numeric:
            arrays[column]=binary(directory/(column+'.f64.gz'),frame[column].to_numpy(dtype='<f8'))
        info={'count':len(frame),'id_field':'id_hex' if kind=='hexagonos' else 'id_frag','arrays':arrays,'image':id_image(kind)}
        if kind=='hexagonos':
            info['axial']=binary(directory/'axiais.i32.gz',frame[['q','r']].to_numpy(dtype='<i4').reshape(-1))
            jsonzip(directory/'renda-contexto.json.gz',{'setor_codigo':frame.setor_codigo.where(frame.setor_codigo.notna(),None).tolist(),'renda_status':frame.renda_status.tolist()})
            centers_native=np.column_stack([frame.q.to_numpy()*1.5*30/math.sqrt(3),30*(frame.r.to_numpy()+frame.q.to_numpy()/2)])
        else:
            source=read_file(GPKG,layer='fragmentos')
            pts=shapely.point_on_surface(source.geometry.values)
            s=osr.SpatialReference();s.ImportFromEPSG(31983);s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            t=osr.SpatialReference();t.ImportFromEPSG(3857);t.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            xy=shapely.get_coordinates(pts);ct=osr.CoordinateTransformation(s,t)
            centers_native=xy
            positions=np.asarray(ct.TransformPoints(xy.tolist()))[:,:2]
            info['centers']=binary(directory/'centros.f64.gz',positions.astype('<f8').reshape(-1))
            jsonzip(directory/'contexto.json.gz',frame[['id_frag','cat_iv','classe_avu','form_pred','setor_codigo','renda_status']].where(pd.notna(frame),None).to_dict('records'))
            info['context']='contexto.json.gz'
        pairs=pd.read_feather(RUN/(kind+'_intersecoes_ras.feather'))
        administrative=read_file(GPKG,layer='ras')
        geographic=osr.SpatialReference();geographic.ImportFromEPSG(4326);geographic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        native=osr.SpatialReference();native.ImportFromEPSG(31983);native.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        to_geo=osr.CoordinateTransformation(native,geographic)
        summaries={};ras={}
        for ra,group in pairs.groupby('ra'):
            indices=group.indice.to_numpy(dtype='int32');areas=group.area_m2.to_numpy()
            path=directory/f'ra-{int(ra)}.json.gz'
            region=administrative.loc[administrative.ra_cira==ra,'geometry'].iloc[0]
            outside=indices[~shapely.covers(region,shapely.points(centers_native[indices]))]
            anchors={}
            if len(outside):
                if kind=='fragmentos':geometries=source.geometry.values[outside]
                else:
                    angles=np.arange(6)*math.pi/3
                    geometries=shapely.polygons(centers_native[outside,None,:]+30/math.sqrt(3)*np.column_stack([np.cos(angles),np.sin(angles)])[None,:,:])
                points=shapely.get_coordinates(shapely.point_on_surface(shapely.intersection(geometries,region)))
                transformed=to_geo.TransformPoints(points.tolist())
                anchors={str(int(index)):[p[1],p[0]] for index,p in zip(outside,transformed)}
            jsonzip(path,{'indices':indices.tolist(),'areas':areas.tolist(),'anchors':anchors});ras[str(int(ra))]={'file':path.name,'area_m2':float(areas.sum()),'units':len(indices)}
        for field,c in config.items():
            v=frame[field].to_numpy(dtype='float64')
            cover=frame[c['coverage']].to_numpy(dtype='float64')/100 if c['coverage'] else np.isfinite(v).astype('float64')
            per={}
            groups=[('bacia',np.arange(len(frame)),frame.area_m2.to_numpy())]+[(str(int(ra)),g.indice.to_numpy(),g.area_m2.to_numpy()) for ra,g in pairs.groupby('ra')]
            for ra,idx,area in groups:
                weights=area*cover[idx];valid=np.isfinite(v[idx]);valid_area=float(weights[valid].sum())
                per[ra]={'area_m2':float(area.sum()),'coverage_m2':float(weights.sum()),'valid_m2':valid_area,'weighted_sum':float(np.sum(v[idx][valid]*weights[valid])),'min':float(v[idx][valid].min()) if valid.any() else None,'max':float(v[idx][valid].max()) if valid.any() else None}
            summaries[field]=per
        jsonzip(directory/'resumos.json.gz',summaries);info['summaries']='resumos.json.gz';info['ras']=ras
        manifest['units'][kind]=info
    save(OUT/'manifesto.json',manifest)
    save(RUN/'exportacao_web.json',{'elapsed_s':time.perf_counter()-started,'files':len(list(OUT.rglob('*.*'))),'bytes':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),'float_precision':'Float64 little-endian sem quantização; NaN indica valor ausente','geometry_precision':'GeoPackage integral; desenho cartográfico separado'})
    shutil.copyfile(RUN/'malha.json',OUT/'malha.json')
    print('exportacao concluida',time.perf_counter()-started,flush=True)

if __name__=='__main__':main()
