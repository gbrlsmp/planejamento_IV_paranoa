"""Diagnóstico por interseções exatas; execução retomável e sem alterar fontes.

Geometrias e resultados integrais em GeoPackage local. Temporários, checkpoints e
medidas de duração permanecem na pasta da execução, sob 02 BASE DE DADOS.
"""
import argparse
import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pyogrio
import pyarrow as pa
import shapely
from shapely import STRtree
from osgeo import gdal
from exactextract import exact_extract
from fitopolis_fontes import BASE, WEB, RUN, FONTES

gdal.UseExceptions()
gdal.SetCacheMax(512*1024*1024)
GPKG=RUN/'diagnostico_fitopolis.gpkg'
USO={3:'florestal',4:'savanica',11:'alagado',12:'campestre',33:'agua',100:'vegetacao_intraurbana',101:'forracao',102:'impermeavel_solo_exposto',103:'edificacoes',104:'vias'}
MOM={1:'fonte',2:'conducao',3:'acomodacao'}

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def read(key,columns=None):
    path=RUN/('fonte_'+key+'.gpkg')
    if not path.exists():
        ds=gdal.VectorTranslate(str(path),str(FONTES[key]),format='GPKG',dstSRS='EPSG:31983',layerName=key)
        ds=None
    return read_file(path,columns=columns)

def read_file(path,layer=None,columns=None):
    meta,table=pyogrio.read_arrow(path,layer=layer,columns=columns)
    column=meta['geometry_name'] or 'wkb_geometry'
    frame=table.drop([column]).to_pandas()
    frame['geometry']=shapely.from_wkb(table[column].to_numpy())
    return frame

def write_file(frame,path,layer):
    columns=frame.drop(columns='geometry')
    wkb=pa.array(shapely.to_wkb(frame.geometry.values),type=pa.binary())
    table=pa.Table.from_pandas(columns,preserve_index=False).append_column('geometry',wkb) if len(columns.columns) else pa.table({'geometry':wkb})
    pyogrio.write_arrow(table,path,layer=layer,driver='GPKG',geometry_name='geometry',geometry_type='Unknown',crs='EPSG:31983')

def extract(frame,key,ops):
    if frame.attrs['kind']=='fragmentos':return extract_fragment_parts(frame,key,ops)
    ds=gdal.OpenEx(str(GPKG),gdal.OF_VECTOR)
    layer=ds.GetLayerByName(frame.attrs['kind'])
    idcol='id_hex' if frame.attrs['kind']=='hexagonos' else 'id_frag'
    layer.SetAttributeFilter(f'{idcol} <= {int(frame[idcol].max())}')
    result=exact_extract(str(key),layer,ops,output='pandas')
    assert len(result)==len(frame)
    return result

def subdivide(geometry,max_size=300):
    stack=[geometry]
    while stack:
        g=stack.pop();xmin,ymin,xmax,ymax=g.bounds
        if max(xmax-xmin,ymax-ymin)<=max_size:
            if g.geom_type=='GeometryCollection':
                pending=list(g.geoms);polygons=[]
                while pending:
                    part=pending.pop()
                    if part.geom_type=='Polygon':polygons.append(part)
                    elif part.geom_type in ['MultiPolygon','GeometryCollection']:pending.extend(part.geoms)
                g=shapely.union_all(polygons)
            if g.area>1e-8:yield g
            continue
        if xmax-xmin>=ymax-ymin:
            cut=(xmin+xmax)/2;boxes=[shapely.box(xmin,ymin,cut,ymax),shapely.box(cut,ymin,xmax,ymax)]
        else:
            cut=(ymin+ymax)/2;boxes=[shapely.box(xmin,ymin,xmax,cut),shapely.box(xmin,cut,xmax,ymax)]
        for child in shapely.intersection(g,boxes):
            if child.area>1e-8:stack.append(child)

def extract_fragment_parts(frame,key,ops):
    """Agrega partes exatas, contornando falha nativa em polígonos gigantes.

    As geometrias originais são preservadas. Contagem fracionária, soma e
    momentos de segunda ordem recompõem as estatísticas da unidade integral.
    """
    path=RUN/'fragmentos_partes_poligonais.gpkg'
    if not path.exists():
        started=time.perf_counter();ids=[];geoms=[]
        for identifier,geometry in zip(frame.id_frag,frame.geometry):
            for part in subdivide(geometry,500):ids.append(identifier);geoms.append(part)
        areas=shapely.area(geoms);sums=np.bincount(ids,weights=areas,minlength=len(frame)+1)[1:]
        assert np.allclose(sums,frame.area_m2,atol=.01,rtol=1e-9)
        write_file(pd.DataFrame({'id_frag':ids,'geometry':geoms}),path,'partes')
        save(RUN/'fragmentos_subdivisao.json',{'fragmentos':len(frame),'partes':len(geoms),'max_extent_m':500,'simplification':False,'max_area_error_m2':float(np.max(np.abs(sums-frame.area_m2.to_numpy())))})
        clock('fragmentos_subdivisao',started)
    ds=gdal.OpenEx(str(path),gdal.OF_VECTOR);layer=ds.GetLayer(0)
    raw=exact_extract(str(key),layer,ops,include_cols=['id_frag'],output='pandas')
    index=raw.id_frag.to_numpy(dtype='int32')-1;counts=raw['count'].to_numpy();n=len(frame)
    total=np.bincount(index,weights=counts,minlength=n);out={}
    if 'frac' in ops:
        codes=sorted({float(v) for values in raw['unique'] for v in values})
        areas=np.zeros((n,len(codes)))
        for codei,code in enumerate(codes):
            a=np.fromiter((float(frac[np.flatnonzero(values==code)[0]]) if np.any(values==code) else 0. for values,frac in zip(raw['unique'],raw['frac'])),dtype='float64',count=len(raw))
            areas[:,codei]=np.bincount(index,weights=a*counts,minlength=n)
        out['unique']=[np.asarray(codes)[a>0] for a in areas]
        out['frac']=[a[a>0]/count if count>0 else np.array([]) for a,count in zip(areas,total)]
    else:
        mean=raw['mean'].to_numpy();summed=np.bincount(index,weights=np.nan_to_num(mean)*counts,minlength=n)
        aggregate=np.divide(summed,total,out=np.full(n,np.nan),where=total>0)
        out['mean']=aggregate
        if 'min' in ops:
            minima=np.full(n,np.inf);maxima=np.full(n,-np.inf)
            np.minimum.at(minima,index,np.nan_to_num(raw['min'].to_numpy(),nan=np.inf))
            np.maximum.at(maxima,index,np.nan_to_num(raw['max'].to_numpy(),nan=-np.inf))
            minima[total==0]=np.nan;maxima[total==0]=np.nan;out['min']=minima;out['max']=maxima
        if 'stdev' in ops:
            variance=raw['stdev'].to_numpy()**2
            second=np.bincount(index,weights=np.nan_to_num(variance+mean**2)*counts,minlength=n)
            moment=np.divide(second,total,out=np.full(n,np.nan),where=total>0)
            out['stdev']=np.sqrt(np.maximum(0,moment-aggregate**2))
    out['count']=total
    return pd.DataFrame({op:out[op] for op in ops})

def clock(label,started):
    duration=round(time.perf_counter()-started,3)
    print(label, duration,'s',flush=True)
    path=RUN/'tempos.json'; data=json.loads(path.read_text()) if path.exists() else {}
    data[label]=duration;save(path,data)

def geometry():
    if GPKG.exists(): return
    started=time.perf_counter()
    basin=shapely.union_all(read('bacia').geometry.values)
    assert basin.is_valid
    xmin,ymin,xmax,ymax=basin.bounds
    side=30/math.sqrt(3); step=1.5*side
    pieces=[]
    # Flat-top hexagons anchored at the origin of EPSG:31983. q:r is stable.
    for q in range(math.floor((xmin-side)/step), math.ceil((xmax+side)/step)+1):
        rs=np.arange(math.floor((ymin-30)/30-q/2),math.ceil((ymax+30)/30-q/2)+1,dtype=np.int32)
        xy=np.column_stack([np.full(len(rs),q*step),30*(rs+q/2)])
        angles=np.arange(6)*math.pi/3
        vertices=xy[:,None,:]+side*np.column_stack([np.cos(angles),np.sin(angles)])[None,:,:]
        polygons=shapely.polygons(vertices)
        mask=shapely.intersects(polygons,basin)
        rs=rs[mask]; polygons=polygons[mask]
        inside=shapely.covers(basin,polygons)
        polygons[~inside]=shapely.intersection(polygons[~inside],basin)
        areas=shapely.area(polygons);keep=areas>1e-8
        if not keep.any():continue
        pieces.append(pd.DataFrame({'q':np.full(keep.sum(),q,dtype=np.int32),'r':rs[keep], 'area_m2':areas[keep], 'parcial':(~inside[keep]).astype(np.int8),'geometry':polygons[keep]}))
    frame=pd.concat(pieces,ignore_index=True)
    frame.insert(0,'id_hex',np.arange(1,len(frame)+1,dtype=np.int32))
    frame.insert(1,'chave_hex',frame.q.astype(str)+':'+frame.r.astype(str))
    assert frame.chave_hex.is_unique
    error=abs(frame.area_m2.sum()-basin.area)
    assert error<max(.1,basin.area*1e-9),error
    write_file(frame,GPKG,'hexagonos')
    frag=read('fragmentos',['id_frag','cat_iv','classe_avu','form_pred'])
    assert len(frag)==46876 and frag.id_frag.is_unique
    frag=frag.sort_values('id_frag').reset_index(drop=True)
    frag['area_m2']=shapely.area(frag.geometry.values)
    write_file(frag,GPKG,'fragmentos')
    ras=read('ras',['ra_cira','ra_nome']);ras.geometry=shapely.intersection(ras.geometry.values,basin)
    write_file(ras,GPKG,'ras')
    write_file(pd.DataFrame({'nome':['Bacia do Paranoá'],'geometry':[basin]}),GPKG,'bacia')
    save(RUN/'malha.json',{'hexagonos':len(frame),'fragmentos':len(frag),'crs':'EPSG:31983','entre_faces_m':30,'lado_m':side,'area_completa_m2':side*30*1.5,'origem':[0,0],'orientacao':'flat-top','chave_estavel':'q:r','celulas_parciais':int(frame.parcial.sum()),'area_bacia_m2':basin.area,'erro_fechamento_m2':error})
    clock('geometrias',started)

def cache_table(name,producer,discard=False):
    path=RUN/(name+'.feather')
    if path.exists(): return None if discard else pd.read_feather(path)
    started=time.perf_counter(); data=producer();data.to_feather(path);clock(name,started);return None if discard else data

def numeric(frame,key):
    ds=gdal.Open(str(FONTES[key]));gt=ds.GetGeoTransform();pixel=abs(gt[1]*gt[5]);ds=None
    out=extract(frame,FONTES[key],['mean','min','max','stdev','count'])
    out.columns=[f'{key}_{x}' for x in out.columns]
    out[f'{key}_valid_m2']=out.pop(f'{key}_count')*pixel
    out[f'{key}_coverage_pct']=100*out[f'{key}_valid_m2']/frame.area_m2.to_numpy()
    return out

def categorical(frame,key,classes):
    ds=gdal.Open(str(FONTES[key]));gt=ds.GetGeoTransform();pixel=abs(gt[1]*gt[5]);ds=None
    raw=extract(frame,FONTES[key],['unique','frac','count'])
    counts=raw['count'].to_numpy()*pixel
    result={f'{key}_valid_m2':counts,f'{key}_coverage_pct':100*counts/frame.area_m2.to_numpy()}
    for code,label in classes.items():
        values=np.fromiter((float(f[np.flatnonzero(u==code)[0]]) if np.any(u==code) else 0. for u,f in zip(raw['unique'],raw['frac'])),dtype='float64',count=len(frame))
        result[f'{key}_pct_{label}']=100*values*counts/frame.area_m2.to_numpy()
    unknown=np.zeros(len(frame))
    for values in (result[f'{key}_pct_{label}'] for label in classes.values()):unknown+=values
    assert np.max(np.abs(unknown-result[f'{key}_coverage_pct']))<1e-4,'Classe não reconhecida'
    for label in classes.values():result[f'{key}_pct_{label}'][counts==0]=np.nan
    return pd.DataFrame(result)

def flooding(frame):
    path=RUN/'profundidade_positiva.tif'
    if not path.exists():
        src=gdal.Open(str(FONTES['inundacao']));a=src.ReadAsArray();nd=src.GetRasterBand(1).GetNoDataValue()
        valid=np.isfinite(a)&(a!=nd)&(a>0);a[~valid]=-9999
        dst=gdal.GetDriverByName('GTiff').Create(str(path),src.RasterXSize,src.RasterYSize,1,gdal.GDT_Float32,options=['COMPRESS=DEFLATE','TILED=YES'])
        dst.SetGeoTransform(src.GetGeoTransform());dst.SetProjection(src.GetProjection());dst.GetRasterBand(1).SetNoDataValue(-9999);dst.GetRasterBand(1).WriteArray(a);dst=None
    out=numeric(frame,'inundacao')
    positive=extract(frame,path,['mean','count'])
    ds=gdal.Open(str(path));gt=ds.GetGeoTransform();ds=None
    out['inundada_m2']=positive['count'].to_numpy()*abs(gt[1]*gt[5])
    out['inundada_pct_valida']=np.divide(100*out.inundada_m2,out.inundacao_valid_m2,out=np.full(len(frame),np.nan),where=out.inundacao_valid_m2>0)
    out['profundidade_media_inundada_m']=positive['mean'].to_numpy()
    return out

def split_parts(geoms):
    return shapely.get_parts(geoms)

def analysis_units(units):
    bounds=shapely.bounds(units)
    large=np.maximum(bounds[:,2]-bounds[:,0],bounds[:,3]-bounds[:,1])>1000
    if not large.any():return units,np.arange(len(units))
    parts=[];owners=[]
    for i,g in enumerate(units):
        for piece in subdivide(g,500) if large[i] else [g]:parts.append(piece);owners.append(i)
    return np.asarray(parts,dtype='object'),np.asarray(owners,dtype='int32')

def area_pairs(units,geometries):
    tree=STRtree(geometries)
    parts,owners=analysis_units(units)
    for start in range(0,len(parts),5000):
        batch=parts[start:start+5000];shapely.prepare(batch)
        i,j=tree.query(batch,predicate='intersects')
        inside=shapely.covers(batch[i],geometries[j]);areas=shapely.area(geometries[j])
        areas[~inside]=shapely.area(shapely.intersection(batch[i[~inside]],geometries[j[~inside]]))
        good=areas>1e-8
        yield owners[start+i[good]],j[good],areas[good]

def buildings(frame,kind):
    path=RUN/'edificacoes_uniao.gpkg'
    if not path.exists():
        a=read('edificacoes',[]).geometry.values
        merged=shapely.disjoint_subset_union_all(a)
        write_file(pd.DataFrame({'geometry':split_parts([merged])}),path,'edificacoes')
    geoms=read_file(path).geometry.values
    units=frame.geometry.values
    if kind=='fragmentos':
        basin=read_file(GPKG,layer='bacia').geometry.iloc[0]
        units=shapely.intersection(shapely.buffer(units,30,quad_segs=16),basin)
    denominator=shapely.area(units);areas=np.zeros(len(frame))
    for i,j,a in area_pairs(units,geoms):np.add.at(areas,i,a)
    assert np.all(areas<=denominator+1e-4)
    return pd.DataFrame({'edif_ocupada_m2':areas,'edif_dominio_m2':denominator,'edif_pct':100*areas/denominator})

def income(frame):
    sectors=read('renda',['CD_SETOR','V06004','RENDA_STATUS']).sort_values('CD_SETOR').reset_index(drop=True)
    geom=sectors.geometry.values
    best=np.full(len(frame),-1,dtype=np.int32);overlap=np.zeros(len(frame))
    batches=area_pairs(frame.geometry.values,geom)
    if frame.attrs.get('kind')=='fragmentos':
        combined=pd.concat([pd.DataFrame({'i':i,'j':j,'area':areas}) for i,j,areas in batches],ignore_index=True).groupby(['i','j'],as_index=False).area.sum()
        batches=[(combined.i.to_numpy(),combined.j.to_numpy(),combined.area.to_numpy())]
    for i,j,areas in batches:
        # Stable tie: smallest sector code, independent of spatial-index order.
        order=np.lexsort((j,-areas,i));i=i[order];j=j[order];areas=areas[order]
        first=np.r_[True,i[1:]!=i[:-1]];i=i[first];best[i]=j[first];overlap[i]=areas[first]
    data=pd.DataFrame({'setor_codigo':pd.Series([None]*len(frame),dtype='object'),'renda_reais':np.nan,'renda_sm':np.nan,'renda_status':pd.Series(['sem_setor']*len(frame),dtype='object'),'setor_pct_unidade':100*overlap/frame.area_m2.to_numpy()})
    yes=best>=0;s=sectors.iloc[best[yes]]
    values=pd.to_numeric(s.V06004,errors='coerce').to_numpy(copy=True)
    data.loc[yes,'setor_codigo']=s.CD_SETOR.astype(str).to_numpy()
    data.loc[yes,'renda_status']=s.RENDA_STATUS.astype(str).to_numpy()
    values[values<0]=np.nan
    data.loc[yes,'renda_reais']=values;data.loc[yes,'renda_sm']=values/1212
    return data

def pre(frame):
    """Uniões locais evitam dissolver contornos adjacentes de toda a bacia.

    A união ocorre depois da interseção com cada unidade: mesma precisão,
    geometrias pequenas e preservação explícita das disputas entre classes.
    """
    path=RUN/'pre_subdividido.gpkg'
    if not path.exists():
        source=read('pre',['cat_pdot20']);text=source.cat_pdot20.str.upper()
        raw_codes=np.where(text.str.startswith('MUITO ALTO'),3,np.where(text.str.startswith('ALTO'),2,np.where(text.str.startswith(('MÉDIO','MEDIO')),1,np.where(text.str.startswith('BAIXO'),0,-1))))
        assert (raw_codes>=0).all()
        original_area=float(shapely.area(source.geometry.values).sum());parts=[];classes=[]
        # Exact recursive clipping prevents a 462k-vertex polygon from being
        # intersected in full for every 30 m cell. No simplification is used.
        stack=list(zip(source.geometry.values,raw_codes))
        while stack:
            g,code=stack.pop();xmin,ymin,xmax,ymax=g.bounds
            if max(xmax-xmin,ymax-ymin)<=300:
                parts.append(g);classes.append(code);continue
            if xmax-xmin>=ymax-ymin:
                cut=(xmin+xmax)/2;boxes=[shapely.box(xmin,ymin,cut,ymax),shapely.box(cut,ymin,xmax,ymax)]
            else:
                cut=(ymin+ymax)/2;boxes=[shapely.box(xmin,ymin,xmax,cut),shapely.box(xmin,cut,xmax,ymax)]
            clipped=shapely.intersection(g,boxes)
            for child in clipped:
                if child.area>1e-8:stack.append((child,code))
        assert abs(sum(p.area for p in parts)-original_area)<max(.01,original_area*1e-9)
        write_file(pd.DataFrame({'classe':classes,'geometry':parts}),path,'pre_subdividido')
        save(RUN/'pre_subdivisao.json',{'source_features':len(source),'parts':len(parts),'max_extent_m':300,'simplification':False,'source_sum_area_m2':original_area,'parts_sum_area_m2':sum(p.area for p in parts)})
    source=read_file(path);codes=source.classe.to_numpy()
    geometries=source.geometry.values;tree=STRtree(geometries);totals=np.zeros((len(frame),5))
    units,owners=analysis_units(frame.geometry.values)
    for start in range(0,len(units),5000):
        batch=units[start:start+5000];i,j=tree.query(batch,predicate='intersects')
        clips=shapely.intersection(batch[i],geometries[j]);areas=shapely.area(clips)
        good=areas>1e-8;i=i[good];j=j[good];clips=clips[good];areas=areas[good]
        order=np.argsort(i,kind='stable');i=i[order];j=j[order];clips=clips[order];areas=areas[order]
        limits=np.r_[0,np.flatnonzero(i[1:]!=i[:-1])+1,len(i)]
        for lo,hi in zip(limits[:-1],limits[1:]):
            if lo==hi:continue
            idx=owners[start+i[lo]]
            if hi-lo==1:totals[idx,codes[j[lo]]]+=areas[lo];continue
            cls=codes[j[lo:hi]];parts=clips[lo:hi]
            if np.all(cls==cls[0]):
                totals[idx,cls[0]]+=shapely.union_all(parts).area
                continue
            unions=[shapely.union_all(parts[cls==c]) for c in range(4)]
            area=np.asarray([p.area for p in unions]);coverage=shapely.union_all(unions).area
            if area.sum()>coverage+max(1e-6,frame.area_m2.iloc[idx]*1e-10):
                area=np.asarray([p.difference(shapely.union_all([g for k,g in enumerate(unions) if k!=c])).area for c,p in enumerate(unions)])
            totals[idx,:4]+=area;totals[idx,4]+=max(0,coverage-area.sum())
        if start%100000==0:print('PRE',start,'/',len(frame),flush=True)
    labels=['baixo','medio','alto','muito_alto','sobreposicao']
    valid=totals.sum(axis=1);out={f'pre_pct_{label}':100*totals[:,c]/frame.area_m2.to_numpy() for c,label in enumerate(labels)}
    out['pre_valid_m2']=valid;out['pre_coverage_pct']=100*valid/frame.area_m2.to_numpy()
    for label in labels:out[f'pre_pct_{label}'][valid==0]=np.nan
    assert np.max(out['pre_coverage_pct'])<100.0001
    return pd.DataFrame(out)

def ra_intersections(frame,kind):
    path=RUN/f'{kind}_intersecoes_ras.feather'
    if path.exists():return
    started=time.perf_counter();ras=read_file(GPKG,layer='ras');parts=[];geoms=[];codes=[]
    for code,geometry in zip(ras.ra_cira,ras.geometry):
        for piece in subdivide(geometry,1000):geoms.append(piece);codes.append(code)
    geoms=np.asarray(geoms,dtype='object');codes=np.asarray(codes,dtype='int16')
    for i,j,a in area_pairs(frame.geometry.values,geoms):
        parts.append(pd.DataFrame({'indice':i.astype('int32'),'ra':codes[j],'area_m2':a}))
    out=pd.concat(parts,ignore_index=True).groupby(['indice','ra'],as_index=False,sort=True).area_m2.sum()
    assert out.groupby('indice').area_m2.sum().max()>0
    areas=out.groupby('indice').area_m2.sum().reindex(range(len(frame)),fill_value=0).to_numpy()
    assert np.max(areas-frame.area_m2.to_numpy())<.05,'RAs sobrepostas: não publicar resumos aditivos'
    out.to_feather(path)
    clock(kind+'_intersecoes_ras',started)

def results(kind,limit=0,only_rasters=False,only_vectors=False):
    idcol='id_hex' if kind=='hexagonos' else 'id_frag'
    frame=read_file(GPKG,layer=kind)
    frame=frame.sort_values(idcol).reset_index(drop=True)
    if limit:frame=frame.iloc[:limit].copy()
    frame.attrs['kind']=kind
    prefix=(kind if not limit else f'ensaio_{kind}_{limit}')
    outputs=[]
    def cached(name,producer):return cache_table(name,producer,discard=only_rasters or only_vectors)
    if not only_vectors:
        for key in ['cc_dia','hm_dia','t_dia','cc_noite','hm_noite','t_noite','lst_seca','lst_chuva']:
            outputs.append(cached(prefix+'_'+key,lambda key=key:numeric(frame,key)))
        outputs.append(cached(prefix+'_inundacao',lambda:flooding(frame)))
        outputs.append(cached(prefix+'_uso',lambda:categorical(frame,'uso',USO)))
        outputs.append(cached(prefix+'_momentos',lambda:categorical(frame,'momentos',MOM)))
    if only_rasters:return
    outputs.append(cached(prefix+'_edificacoes',lambda:buildings(frame,kind)))
    outputs.append(cached(prefix+'_renda',lambda:income(frame)))
    outputs.append(cached(prefix+'_pre',lambda:pre(frame)))
    if only_vectors:
        ra_intersections(frame,kind)
        return
    out=pd.concat([pd.DataFrame(frame.drop(columns='geometry'))]+outputs,axis=1)
    for category in ['uso','momentos','pre']:
        for column in out:
            if column.startswith(category+'_pct_'):out.loc[out[category+'_coverage_pct']==0,column]=np.nan
    assert out[idcol].is_unique
    for c in out:
        if c.endswith('coverage_pct'):
            assert out[c].min()>=-1e-6 and out[c].max()<=100.0001,(kind,c,out[c].max())
    out.to_feather(RUN/(prefix+'_atributos.feather'))
    out.to_csv(RUN/(prefix+'_atributos.csv'),index=False,encoding='utf-8-sig')
    if not limit:
        ra_intersections(frame,kind)
        # New complete output layer; source geometry is copied unchanged.
        path=RUN/(kind+'_diagnostico.gpkg')
        if not path.exists():
            delivered=out.copy();delivered['geometry']=frame.geometry
            write_file(delivered,path,kind)
    print(prefix,'concluido',len(out),flush=True)

def consolidate(kind):
    """Consolidação em lotes para não reter geometrias e centenas de atributos."""
    import gc
    if (RUN/f'{kind}_consolidado.json').exists():return
    started=time.perf_counter()
    _,table=pyogrio.read_arrow(GPKG,layer=kind,read_geometry=False)
    parts=[table.to_pandas()];del table
    for suffix in ['cc_dia','hm_dia','t_dia','cc_noite','hm_noite','t_noite','lst_seca','lst_chuva','inundacao','uso','momentos','edificacoes','renda','pre']:
        parts.append(pd.read_feather(RUN/f'{kind}_{suffix}.feather'))
    out=pd.concat(parts,axis=1,copy=False);del parts;gc.collect()
    for category in ['uso','momentos','pre']:
        for c in out:
            if c.startswith(category+'_pct_'):out.loc[out[category+'_coverage_pct']==0,c]=np.nan
    for c in out:
        if c.endswith('coverage_pct'):assert out[c].min()>=-1e-6 and out[c].max()<=100.0001,(kind,c,out[c].max())
    out.to_feather(RUN/f'{kind}_atributos.feather')
    out.to_csv(RUN/f'{kind}_atributos.csv',index=False,encoding='utf-8-sig',chunksize=5000)
    path=RUN/f'{kind}_diagnostico.gpkg'
    written=0
    if path.exists():
        ds=gdal.OpenEx(str(path),gdal.OF_VECTOR);written=ds.GetLayer(0).GetFeatureCount();ds=None
    for start in range(written,len(out),25000):
        meta,source=pyogrio.read_arrow(GPKG,layer=kind,columns=[],skip_features=start,max_features=min(25000,len(out)-start))
        field=meta['geometry_name'] or 'wkb_geometry'
        attributes=pa.Table.from_pandas(out.iloc[start:start+len(source)],preserve_index=False).append_column('geometry',source[field])
        pyogrio.write_arrow(attributes,path,layer=kind,driver='GPKG',geometry_name='geometry',geometry_type='Unknown',crs='EPSG:31983',append=start>0)
        if start%250000==0:print('GPKG',kind,start,flush=True)
    save(RUN/f'{kind}_consolidado.json',{'count':len(out),'columns':list(out),'geometry_unchanged':True})
    clock(kind+'_consolidacao',started)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--etapa',choices=['geometrias','ensaio','rasters','vetores','consolidar','hexagonos','fragmentos','tudo'],default='tudo')
    p.add_argument('--unidade',choices=['ambas','hexagonos','fragmentos'],default='ambas',help='Recorte da etapa consolidar.')
    args=p.parse_args();RUN.mkdir(parents=True,exist_ok=True)
    geometry()
    if args.etapa=='ensaio':results('hexagonos',10000)
    elif args.etapa=='rasters':
        results('hexagonos',only_rasters=True);results('fragmentos',only_rasters=True)
    elif args.etapa=='vetores':
        results('hexagonos',only_vectors=True);results('fragmentos',only_vectors=True)
    elif args.etapa=='consolidar':
        for kind in (['hexagonos','fragmentos'] if args.unidade=='ambas' else [args.unidade]):consolidate(kind)
    elif args.etapa in ['hexagonos','fragmentos']:
        results(args.etapa,only_rasters=True);results(args.etapa,only_vectors=True);consolidate(args.etapa)
    elif args.etapa=='tudo':
        for kind in ['hexagonos','fragmentos']:
            results(kind,only_rasters=True);results(kind,only_vectors=True);consolidate(kind)

if __name__=='__main__':main()
