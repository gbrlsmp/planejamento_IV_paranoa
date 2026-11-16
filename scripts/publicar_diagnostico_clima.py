"""Derivados do diagnóstico atual: fragmentos, classes relativas e zonas quentes."""
from pathlib import Path
import csv,json,gzip,math,shutil
import numpy as np
from osgeo import gdal,ogr,osr
from PIL import Image
from preparar_revisao_clima import WEB,RUN
from publicar_invest_seca_2026 import save,digest
gdal.UseExceptions();ogr.UseExceptions()
OUT=WEB/'dados-mapas/clima/diagnostico-2026'

def compressed(path,value):
    path.write_bytes(gzip.compress(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0))

def class_name(value,cuts,higher):
    if value is None:return 'Sem dados'
    index=sum(value>=cut for cut in cuts)
    return (['Ruim','Médio','Bom','Muito bom'] if higher else ['Muito bom','Bom','Médio','Ruim'])[index]

def complete_geopackage(rows,csv_path):
    source_path=RUN/'04_Extracao/clima_seca_2026_fragmentos_46876.gpkg'
    path=RUN/'04_Extracao/diagnostico_climatico_completo_46876.gpkg'
    assert not path.exists(), 'Diagnóstico completo existente: conferir antes de repetir.'
    local_csv=RUN/'04_Extracao/diagnostico_climatico_completo_46876.csv'
    shutil.copyfile(csv_path,local_csv);assert digest(local_csv)==digest(csv_path)
    ds=gdal.VectorTranslate(str(path),str(source_path),format='GPKG',layerName='diagnostico_climatico')
    layer=ds.GetLayer();definition=layer.GetLayerDefn()
    existing={definition.GetFieldDefn(i).GetName() for i in range(definition.GetFieldCount())}
    fields=[k for k in rows[1] if k not in existing and k!='center']
    for field in fields:layer.CreateField(ogr.FieldDefn(field,ogr.OFTString if field.endswith('_classe') else ogr.OFTReal))
    config=json.loads((RUN/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    lst=json.loads((WEB/'dados-mapas/clima/superficie-sazonal/manifesto.json').read_text(encoding='utf-8'))
    layer.SetMetadata({'REFERENCIA':'A001 — Brasília, 153 datas pareadas da seca de 2026','TREF_DIA_C':str(config['day']['t_ref']),'TREF_NOITE_C':str(config['night']['t_ref']),'UHI_C':str(config['uhi_max']),'CLASSES':'Térmicas relativas e exploratórias; sem limiares sanitários ou calibração local. Cada corte pertence à faixa superior de valores.','CLASSES_CC_HM':'0.25 / 0.50 / 0.75, maior melhor: Ruim / Médio / Bom / Muito bom','CLASSES_T':'(T−Tref)/UHI: 0.25 / 0.50 / 0.75, menor melhor: Muito bom / Bom / Médio / Ruim','CLASSES_LST_C':json.dumps(lst['indicators']['lst']['class_breaks']['seca'])+'; mesmos cortes seca/chuva, menor melhor','LST':'Composições diurnas 13 datas secas / 6 chuvosas; grade 30 m e térmico efetivo 100 m; extração sobre centros da geometria de 3 m sem ganho de informação térmica','GEOMETRIA':'Geometrias integrais preservadas por id_frag; nenhuma simplificação no GPKG','ORIGEM':str(RUN)})
    ds.StartTransaction()
    for feature in layer:
        row=rows[int(feature['id_frag'])]
        for field in fields:
            if row[field] is None:feature.SetFieldNull(field)
            else:feature.SetField(field,row[field])
        layer.SetFeature(feature)
    ds.CommitTransaction();ds=None
    with ogr.Open(str(source_path)) as original:
        geometries={int(f['id_frag']):bytes(f.GetGeometryRef().ExportToWkb()) for f in original.GetLayer()}
    with ogr.Open(str(path)) as check:
        assert check.GetLayer().GetFeatureCount()==len(rows)==46876
        for feature in check.GetLayer():
            ident=int(feature['id_frag']);assert bytes(feature.GetGeometryRef().ExportToWkb())==geometries[ident]
            for field in fields:assert feature[field]==rows[ident][field]
    save(RUN/'05_Verificacoes/HASHES_DIAGNOSTICO_COMPLETO.json',{'fragment_count':len(rows),'source_geometries_wkb_equal':True,'new_attributes_csv_gpkg_agree':True,'gpkg':{'path':str(path),'sha256':digest(path)},'csv':{'path':str(local_csv),'sha256':digest(local_csv)},'web_csv_copy_equal':True})

def polygons(qa):
    out=RUN/'08_Zonas_quentes';out.mkdir(exist_ok=True)
    gpkg=out/'zonas_quentes_invest.gpkg'
    assert not gpkg.exists(), 'Polígonos existentes: conferir antes de repetir.'
    target=ogr.GetDriverByName('GPKG').CreateDataSource(str(gpkg))
    result={}
    for period,short in [('day','dia'),('night','noite')]:
        ds=gdal.Open(qa['scenarios'][period]['raster_files']['t']);band=ds.GetRasterBand(1)
        stats=qa['scenarios'][period]['full_raster_stats']['t'];threshold=stats['mean']+stats['sd']
        binary=gdal.GetDriverByName('MEM').Create('',ds.RasterXSize,ds.RasterYSize,1,gdal.GDT_Byte)
        binary.SetGeoTransform(ds.GetGeoTransform());binary.SetProjection(ds.GetProjection())
        count=0
        for y in range(0,ds.RasterYSize,256):
            a=ds.ReadAsArray(0,y,ds.RasterXSize,min(256,ds.RasterYSize-y));valid=np.isfinite(a)&(a!=band.GetNoDataValue())
            mask=valid&(a>threshold);count+=int(mask.sum())
            binary.GetRasterBand(1).WriteArray(mask.astype('uint8'),0,y)
        tmp=ogr.GetDriverByName('Memory').CreateDataSource('')
        layer=tmp.CreateLayer('regions',srs=ds.GetSpatialRef(),geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn('value',ogr.OFTInteger))
        gdal.Polygonize(binary.GetRasterBand(1),binary.GetRasterBand(1),layer,0,[],callback=None)
        delivered=target.CreateLayer('zonas_'+short,srs=ds.GetSpatialRef(),geom_type=ogr.wkbMultiPolygon)
        for name,typ in [('id_zona',ogr.OFTInteger),('cenario',ogr.OFTString),('limiar_C',ogr.OFTReal),('area_ha',ogr.OFTReal)]:delivered.CreateField(ogr.FieldDefn(name,typ))
        srs=osr.SpatialReference();srs.ImportFromEPSG(4326);srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        native=ds.GetSpatialRef();native.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform=osr.CoordinateTransformation(native,srs)
        features=[];area=0.
        for f in layer:
            geom=f.GetGeometryRef()
            if geom.GetArea()<20000:continue
            assert geom.IsValid()
            identifier=len(features)+1;ha=geom.GetArea()/10000;area+=ha
            row=ogr.Feature(delivered.GetLayerDefn())
            for key,value in [('id_zona',identifier),('cenario',short),('limiar_C',threshold),('area_ha',ha)]:row.SetField(key,value)
            row.SetGeometry(ogr.ForceToMultiPolygon(geom.Clone()));delivered.CreateFeature(row)
            web=geom.SimplifyPreserveTopology(9);assert web.IsValid();web.Transform(transform)
            features.append({'type':'Feature','properties':{'id_zona':identifier,'cenario':short,'limiar_C':threshold,'area_ha':ha},'geometry':json.loads(web.ExportToJson())})
        path=OUT/f'zonas-quentes-{short}.geojson'
        save(path,{'type':'FeatureCollection','features':features})
        result[short]={'threshold_C':threshold,'mean_C':stats['mean'],'sd_C':stats['sd'],'minimum_area_ha':2,'connectivity':4,'native_selected_pixels_before_area_filter':count,'polygons':len(features),'area_ha':area,'file':path.name,'sha256':digest(path),'source_sha256':digest(Path(qa['scenarios'][period]['raster_files']['t'])),'web_simplification_m':9}
        print(json.dumps({'zones':short,**result[short]}),flush=True)
    target=None
    save(out/'criterios.json',result)
    return result

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    manifest=json.loads((WEB/'dados-mapas/clima/urban-cooling-2026/manifesto.json').read_text(encoding='utf-8'))
    lst=json.loads((WEB/'dados-mapas/clima/superficie-sazonal/manifesto.json').read_text(encoding='utf-8'))
    config=json.loads((RUN/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    qa=json.loads((RUN/'05_Verificacoes/RESULTADO_EXECUCAO_E_EXTRACAO.json').read_text(encoding='utf-8'))
    assert qa['status']=='executado_extraido_conferido'
    for key,cfg in manifest['indicators'].items():
        cfg['higher_is_better']=key!='t'
        cfg['class_breaks']={p:([config[full]['t_ref']+config['uhi_max']*v for v in (.25,.5,.75)] if key=='t' else [.25,.5,.75]) for p,full in [('dia','day'),('noite','night')]}
        cfg['class_method']='Faixas de 0,25 em CC/HM; temperatura: faixas de 0,25 no excesso (T−Tref)/UHI do respectivo cenário. Classes relativas do modelo, sem limiares de saúde ou calibração local.'
    manifest['periods']={'dia':'Dia','noite':'Noite'}
    manifest['fragment_results_published']=True
    manifest['relative_classification']=True
    # Escala comum acompanha as duas referências novas, sem recorte de valores.
    manifest.pop('revision',None)
    manifest['revision']=__import__('hashlib').sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    save(WEB/'dados-mapas/clima/urban-cooling-2026/manifesto.json',manifest)
    with (RUN/'04_Extracao/clima_seca_2026_fragmentos_46876.csv').open(encoding='utf-8-sig',newline='') as f:
        rows={int(r['id_frag']):{k:(float(v) if k not in ('classe_avu','form_pred','cat_iv') else v) for k,v in r.items()} for r in csv.DictReader(f)}
    with (RUN/'07_Superficie_sazonal/lst_fragmentos_46876.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            rows[int(r['id_frag'])].update({k:float(v) if v else None for k,v in r.items() if k.startswith('lst_')})
    for ident,r in rows.items():
        r['id_frag']=ident
        r['n_pix']=int(r['n_pix'])
        r['area_amostrada_m2']=int(r['area_amostrada_m2'])
        for key,cfg in manifest['indicators'].items():
            for p in ('dia','noite'):r[f'{key}_{p}_classe']=class_name(r[f'{key}_{p}_mean'],cfg['class_breaks'][p],cfg['higher_is_better'])
        for p in ('seca','chuva'):r[f'lst_{p}_classe']=class_name(r[f'lst_{p}_mean'],lst['indicators']['lst']['class_breaks'][p],False)
    prep=json.loads((RUN/'01_Entradas/preparacao.json').read_text(encoding='utf-8'))
    # Geometrias integrais ficam no GPKG. Contornos individuais web são simplificados
    # em 3 m e carregados por lotes; todos os IDs continuam consultáveis na tabela.
    batches={};centers={}
    with ogr.Open(prep['metric_source']) as vec:
        layer=vec.GetLayer();source=layer.GetSpatialRef()
        target=osr.SpatialReference();target.ImportFromEPSG(4326);target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);tx=osr.CoordinateTransformation(source,target)
        for f in layer:
            ident=int(f['id_frag']);geom=f.GetGeometryRef();point=geom.PointOnSurface();point.Transform(tx)
            rows[ident]['center']=[point.GetY(),point.GetX()]
            simple=geom.SimplifyPreserveTopology(3);assert simple.IsValid();simple.Transform(tx)
            batch=(ident-1)//256
            batches.setdefault(batch,[]).append({'type':'Feature','properties':{'id_frag':ident},'geometry':json.loads(simple.ExportToJson())})
    for batch,features in batches.items():compressed(OUT/f'fragmentos-{batch:03d}.geojson.gz',{'type':'FeatureCollection','features':features})
    ids=gdal.Warp('',str(RUN/'04_Extracao/id_frag_grade_3m.tif'),format='MEM',dstSRS='EPSG:3857',outputBounds=manifest['bounds'],width=manifest['size'][0],height=manifest['size'][1],resampleAlg='near',outputType=gdal.GDT_UInt32,dstNodata=0)
    a=ids.ReadAsArray();assert int(a.max())<=46876
    rgba=np.zeros((*a.shape,4),dtype='uint8');rgba[:,:,0]=(a>>16)&255;rgba[:,:,1]=(a>>8)&255;rgba[:,:,2]=a&255;rgba[:,:,3]=(a>0)*255
    Image.fromarray(rgba).save(OUT/'id-fragmentos-20m.png',optimize=True)
    ordered=[rows[i] for i in range(1,46877)]
    compressed(OUT/'fragmentos-dados.json.gz',{'schema':1,'rows':ordered})
    csv_path=WEB/'dados-modelo/invest-seca-2026/diagnostico_fragmentos_46876.csv'
    fields=[k for k in ordered[0] if k!='center']
    with csv_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(ordered)
    complete_geopackage(rows,csv_path)
    zones=polygons(qa)
    meta={'schema':1,'count':len(rows),'id_field':'id_frag','data_file':'fragmentos-dados.json.gz','data_sha256':digest(OUT/'fragmentos-dados.json.gz'),'ids_file':'id-fragmentos-20m.png','ids_sha256':digest(OUT/'id-fragmentos-20m.png'),'bounds':manifest['bounds'],'size':manifest['size'],'display_resolution_m':20,'selection':'IDs rasterizados pelo centro em 20 m para exibição. Fragmentos menores podem não aparecer; todos os 46.876 IDs são consultáveis pela tabela e busca. Contornos individuais simplificados em 3 m; geometrias integrais preservadas no GPKG local.','zones':zones,'zone_method':'Zonas relativamente quentes: T_air > média + 1 desvio padrão populacional da bacia em cada cenário, conectividade 4, área mínima 2 ha. Critério exploratório operacional, sem demonstrar ilha de calor urbano-rural observada.','relative_classes':{'cc_hm':[.25,.5,.75],'t':'(T−Tref)/UHI: 0,25 / 0,50 / 0,75; menor temperatura recebe melhor classe.','lst':'Quartis dos pixels válidos das composições seca e chuva reunidas; mesmos cortes nos dois períodos.','labels':['Ruim','Médio','Bom','Muito bom'],'meaning':'Avaliação térmica relativa dos produtos, sem risco sanitário ou limiares empíricos locais.'},'classification_counts':{field:{label:sum(r[field]==label for r in ordered) for label in ['Ruim','Médio','Bom','Muito bom','Sem dados']} for field in ordered[0] if field.endswith('_classe')}}
    save(OUT/'manifesto.json',meta)
    # Fotografia pública rastreável das referências atuais.
    tref=json.loads((RUN/'TREF_A001_RESULTADOS.json').read_text(encoding='utf-8'))
    tref['source']['file']=Path(tref['source']['path_atual']).name
    tref['source'].pop('path_atual',None);tref['source'].pop('source',None)
    daily_csv=WEB/'dados-modelo/invest-seca-2026/tref_a001_medias_diarias.csv'
    shutil.copyfile(RUN/'Tref_A001_medias_diarias.csv',daily_csv)
    tref['daily_means_file']=daily_csv.name;tref['daily_means_sha256']=digest(daily_csv)
    save(WEB/'dados-modelo/invest-seca-2026/tref_a001.json',tref)
    save(WEB/'dados-modelo/invest-seca-2026/conferencia_independente.json',json.loads((RUN/'05_Verificacoes/CONFERENCIA_A001_LANDSAT_INDEPENDENTE.json').read_text(encoding='utf-8')))
    print(json.dumps({'fragments':len(rows),'batches':len(batches),'id_cells':int((a>0).sum()),'classes':meta['classification_counts']}),flush=True)

if __name__=='__main__':main()
