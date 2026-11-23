"""Validação independente dos dados integrais e dos derivados compactos."""
import gzip
import hashlib
import json
import math
import time
import numpy as np
import pandas as pd
import shapely
import pyogrio
from PIL import Image
from osgeo import gdal,osr
from gerar_diagnostico_fitopolis import read_file,read,save,GPKG,USO,MOM
from fitopolis_fontes import RUN,WEB,FONTES

def source_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def manual_raster(geometry,path):
    ds=gdal.Open(str(path));gt=ds.GetGeoTransform();band=ds.GetRasterBand(1);nd=band.GetNoDataValue()
    xmin,ymin,xmax,ymax=geometry.bounds
    x0=max(0,math.floor((xmin-gt[0])/gt[1]));x1=min(ds.RasterXSize,math.ceil((xmax-gt[0])/gt[1]))
    y0=max(0,math.floor((ymax-gt[3])/gt[5]));y1=min(ds.RasterYSize,math.ceil((ymin-gt[3])/gt[5]))
    if x1<=x0 or y1<=y0:return None
    data=band.ReadAsArray(x0,y0,x1-x0,y1-y0);mask=band.GetMaskBand().ReadAsArray(x0,y0,x1-x0,y1-y0)
    cols,rows=np.meshgrid(np.arange(x0,x1),np.arange(y0,y1));left=gt[0]+cols.ravel()*gt[1];top=gt[3]+rows.ravel()*gt[5]
    cells=shapely.box(left,top+gt[5],left+gt[1],top)
    areas=shapely.area(shapely.intersection(cells,geometry));values=data.ravel().astype('float64')
    valid=(areas>1e-7)&(mask.ravel()>0)&np.isfinite(values)
    if nd is not None:valid&=values!=nd
    if not valid.any():return None
    a=areas[valid];v=values[valid];mean=float(np.sum(a*v)/a.sum());positive=v>0
    return {'mean':mean,'min':float(v.min()),'max':float(v.max()),'stdev':float(np.sqrt(np.sum(a*(v-mean)**2)/a.sum())),'valid_m2':float(a.sum()),'inundada_m2':float(a[positive].sum()),'positive_mean':float(np.sum(a[positive]*v[positive])/a[positive].sum()) if positive.any() else None}

def main():
    started=time.perf_counter();report={'status':'ok','units':{},'manual_checks':[],'web_arrays':0}
    OUT=WEB/'dados-mapas/fitopolis-2026';manifest=json.loads((OUT/'manifesto.json').read_text(encoding='utf8'))
    for kind,n in [('hexagonos',1358654),('fragmentos',46876)]:
        frame=pd.read_feather(RUN/f'{kind}_atributos.feather');idcol='id_hex' if kind=='hexagonos' else 'id_frag'
        assert len(frame)==n and np.array_equal(frame[idcol],np.arange(1,n+1))
        geo=read_file(GPKG,layer=kind,columns=[idcol])
        areas=shapely.area(geo.geometry.values)
        assert np.allclose(areas,frame.area_m2,atol=.0001,rtol=1e-10)
        assert shapely.is_valid(geo.geometry.values).all()
        if kind=='fragmentos':
            source=read('fragmentos',['id_frag']).sort_values('id_frag').reset_index(drop=True)
            assert np.array_equal(shapely.to_wkb(source.geometry.values),shapely.to_wkb(geo.geometry.values))
        # Independent vector checks: original source polygons, no subdivision.
        sectors=read('renda',['CD_SETOR','V06004']).sort_values('CD_SETOR').reset_index(drop=True)
        sector_tree=shapely.STRtree(sectors.geometry.values)
        buildings=read('edificacoes',[]);building_tree=shapely.STRtree(buildings.geometry.values)
        basin=read_file(GPKG,layer='bacia').geometry.iloc[0]
        small=np.flatnonzero((areas>20)&(areas<1500))[:4]
        for idx in small:
            unit=geo.geometry.iloc[idx]
            candidates=sector_tree.query(unit,predicate='intersects')
            if len(candidates):
                overlap=shapely.area(shapely.intersection(unit,sectors.geometry.values[candidates]));order=np.lexsort((candidates,-overlap));best=candidates[order[0]]
                if overlap[order[0]]>1e-8:
                    assert str(frame.loc[idx,'setor_codigo'])==str(sectors.loc[best,'CD_SETOR'])
                    assert np.isclose(frame.loc[idx,'setor_pct_unidade'],100*overlap[order[0]]/areas[idx],atol=1e-6)
            domain=unit if kind=='hexagonos' else shapely.intersection(shapely.buffer(unit,30,quad_segs=16),basin)
            candidates=building_tree.query(domain,predicate='intersects')
            occupied=shapely.union_all(shapely.intersection(domain,buildings.geometry.values[candidates])).area
            assert np.isclose(frame.loc[idx,'edif_ocupada_m2'],occupied,atol=.001,rtol=1e-8)
            assert np.isclose(frame.loc[idx,'edif_dominio_m2'],domain.area,atol=.001,rtol=1e-8)
        del sectors,sector_tree,buildings,building_tree
        for group in ['cc_dia','hm_dia','t_dia','cc_noite','hm_noite','t_noite','lst_seca','lst_chuva','inundacao','uso','momentos','pre']:
            cover=frame[group+'_coverage_pct'].to_numpy()
            assert np.nanmin(cover)>=-1e-6 and np.nanmax(cover)<=100.0001
        for group in ['uso','momentos','pre']:
            columns=[c for c in frame if c.startswith(group+'_pct_')]
            total=frame[columns].sum(axis=1).to_numpy()
            assert np.allclose(total,frame[group+'_coverage_pct'],atol=1e-4)
            no=frame[group+'_coverage_pct']==0
            assert frame.loc[no,columns].isna().all().all()
        assert np.all(frame.edif_ocupada_m2<=frame.edif_dominio_m2+.001)
        assert np.all(frame.inundada_m2<=frame.inundacao_valid_m2+.001)
        no_valid=frame.inundacao_valid_m2==0;no_flood=(frame.inundada_m2==0)&~no_valid
        assert frame.loc[no_valid,'inundada_pct_valida'].isna().all()
        assert (frame.loc[no_flood,'inundada_pct_valida']==0).all()
        assert frame.loc[frame.inundada_m2==0,'profundidade_media_inundada_m'].isna().all()
        pairs=pd.read_feather(RUN/f'{kind}_intersecoes_ras.feather')
        summed=np.bincount(pairs.indice,weights=pairs.area_m2,minlength=n)
        assert np.max(summed-areas)<.05
        # Independent exact intersections of native raster pixels in small units.
        rng=np.random.default_rng(20261123);candidates=np.flatnonzero((areas>20)&(areas<1500))
        sample=rng.choice(candidates,size=min(6,len(candidates)),replace=False)
        if kind=='hexagonos':sample=np.r_[sample,np.flatnonzero(frame.parcial.to_numpy())[:2]]
        for idx in sample:
            for key in ['t_dia','t_noite','lst_seca','inundacao']:
                expected=manual_raster(geo.geometry.iloc[idx],FONTES[key])
                if expected is None:
                    assert frame.loc[idx,key+'_valid_m2']<.001
                    continue
                for statistic in ['mean','min','max','stdev','valid_m2']:
                    actual=frame.loc[idx,key+'_'+statistic];assert np.isclose(actual,expected[statistic],atol=2e-5,rtol=1e-7),(kind,int(idx),key,statistic,actual,expected[statistic])
                if key=='inundacao':assert np.isclose(frame.loc[idx,'inundada_m2'],expected['inundada_m2'],atol=.001)
                report['manual_checks'].append({'kind':kind,'id':int(idx+1),'raster':key})
        info=manifest['units'][kind]
        for column,record in info['arrays'].items():
            encoded=(OUT/kind/record['file']).read_bytes();assert hashlib.sha256(encoded).hexdigest()==record['sha256']
            decoded=gzip.decompress(encoded);assert hashlib.sha256(decoded).hexdigest()==record['raw_sha256']
            actual=np.frombuffer(decoded,dtype='<f8');assert np.array_equal(actual,frame[column].to_numpy(dtype='float64'),equal_nan=True),column
            report['web_arrays']+=1
        report['units'][kind]={'count':n,'area_m2':float(areas.sum()),'unique_ids':True,'valid_geometries':True,'missing_flood_estimate':int(no_valid.sum()),'valid_without_flood':int(no_flood.sum()),'max_ra_area_excess_m2':float(np.max(summed-areas)),'complete_gpkg':str(RUN/f'{kind}_diagnostico.gpkg')}
        # Confirm that complete output also has exactly the original geometry.
        ds=gdal.OpenEx(str(RUN/f'{kind}_diagnostico.gpkg'),gdal.OF_VECTOR);layer=ds.GetLayer(0);assert layer.GetFeatureCount()==n
        for idx in sample:
            layer.SetAttributeFilter(f'{idcol} = {int(idx+1)}');feature=layer.GetNextFeature()
            assert shapely.equals_exact(shapely.from_wkb(bytes(feature.GetGeometryRef().ExportToWkb())),geo.geometry.iloc[idx],0)
        ds=None
        fields=[idcol,'t_dia_mean','inundada_pct_valida','edif_pct','renda_sm','pre_pct_alto']
        _,attributes=pyogrio.read_arrow(RUN/f'{kind}_diagnostico.gpkg',layer=kind,columns=fields,read_geometry=False)
        delivered=attributes.to_pandas()
        for field in fields:assert np.array_equal(delivered[field].to_numpy(dtype='float64'),frame[field].to_numpy(dtype='float64'),equal_nan=True)
        report['units'][kind]['complete_gpkg_attribute_alignment']=True
        report['units'][kind]['independent_vector_samples']=len(small)
        del geo,frame
    # Fixture independently computed by GDAL for browser projection tests.
    s=osr.SpatialReference();s.ImportFromEPSG(4326);s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    t=osr.SpatialReference();t.ImportFromEPSG(31983);t.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct=osr.CoordinateTransformation(s,t)
    points=[[-48.2,-15.6],[-47.9,-15.8],[-47.7,-16.0],[-48.0,-15.9]]
    save(OUT/'projecao-verificada.json',[{'lonlat':p,'utm':list(ct.TransformPoint(*p)[:2])} for p in points])
    provenance={}
    for key,path in FONTES.items():
        provenance[key]={'path':str(path.relative_to(RUN.parents[2])) if path.is_relative_to(RUN.parents[2]) else str(path),'size':path.stat().st_size,'sha256':source_hash(path)}
    save(RUN/'fontes_sha256.json',provenance)
    report['elapsed_s']=time.perf_counter()-started
    save(RUN/'validacao.json',report);save(OUT/'validacao.json',{k:v for k,v in report.items() if k!='units'}|{'units':{k:{a:b for a,b in v.items() if a!='complete_gpkg'} for k,v in report['units'].items()}})
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
