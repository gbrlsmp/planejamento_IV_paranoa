"""Extrai CC, HM e T por id_frag atual e confere integralmente as saídas oficiais.

Estatísticas por centros de pixels de 3 m, sem classificação de risco nem média
dia/noite. A identidade espacial foi conferida na preparação e é reconferida.
"""
from pathlib import Path
from datetime import datetime
import csv
import hashlib
import json
import math
import numpy as np
from osgeo import gdal, ogr

gdal.UseExceptions()
ogr.UseExceptions()
ROOT = Path(__file__).resolve().parent
N = 46876


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def valid(array, nodata):
    return np.isfinite(array) & (array != nodata)


def crop_offset(target, source):
    t, s = target.GetGeoTransform(), source.GetGeoTransform()
    assert (t[1],t[2],t[4],t[5]) == (s[1],s[2],s[4],s[5])
    assert target.GetSpatialRef().IsSame(source.GetSpatialRef())
    fx, fy = (t[0]-s[0])/s[1], (t[3]-s[3])/s[5]
    x, y = round(fx), round(fy)
    assert abs(fx-x) < 1e-7 and abs(fy-y) < 1e-7
    assert x >= 0 and y >= 0
    assert x+target.RasterXSize <= source.RasterXSize
    assert y+target.RasterYSize <= source.RasterYSize
    return x, y


def aggregate(period, folder, config, ids, coverage, table):
    short = 'dia' if period == 'day' else 'noite'
    suffix = 'seca_2026_'+short
    paths = {key:ROOT/folder/f'{prefix}_{suffix}.tif' for key,prefix in [('cc','cc'),('hm','hm'),('t','T_air')]}
    rasters = {key:gdal.Open(str(path)) for key,path in paths.items()}
    ds = rasters['t']
    for raster in rasters.values():
        assert raster.GetGeoTransform() == ds.GetGeoTransform()
        assert raster.GetProjection() == ds.GetProjection()
        assert (raster.RasterXSize,raster.RasterYSize) == (ds.RasterXSize,ds.RasterYSize)
    xoff, yoff = crop_offset(ds, ids)
    assert crop_offset(ds,coverage) == (xoff,yoff)
    t_nomix = gdal.Open(str(ROOT/folder/f'intermediate/T_air_nomix_{suffix}.tif'))
    assert t_nomix.GetGeoTransform() == ds.GetGeoTransform()
    accum = {key:{'n':np.zeros(N+1,dtype=np.int64), 'sum':np.zeros(N+1), 'sum2':np.zeros(N+1), 'min':np.full(N+1,np.inf), 'max':np.full(N+1,-np.inf)} for key in paths}
    global_stats = {key:{'n':0,'sum':0.,'sum2':0.,'min':math.inf,'max':-math.inf} for key in paths}
    max_cc_error = max_t_formula_error = 0.
    lut = np.zeros(65536,dtype=np.float64)
    for row in table:
        if period == 'day':
            value = .6*float(row['shade'])+.2*float(row['albedo'])+.2*float(row['kc'])
        else:
            value = 1-float(row['building_intensity'])
        lut[int(row['lucode'])] = value
    for y in range(0,ds.RasterYSize,256):
        rows = min(256,ds.RasterYSize-y)
        label = ids.ReadAsArray(xoff,yoff+y,ds.RasterXSize,rows)
        land = coverage.ReadAsArray(xoff,yoff+y,ds.RasterXSize,rows)
        arrays = {key:r.ReadAsArray(0,y,ds.RasterXSize,rows) for key,r in rasters.items()}
        masks = {key:valid(a,rasters[key].GetRasterBand(1).GetNoDataValue()) for key,a in arrays.items()}
        mask = land != coverage.GetRasterBand(1).GetNoDataValue()
        for m in masks.values():
            assert np.array_equal(mask,m), (short,y,'máscara divergente')
        assert np.all(mask[label>0])
        if not mask.any():
            continue
        max_cc_error = max(max_cc_error,float(np.max(np.abs(arrays['cc'][mask].astype(float)-lut[land[mask]]))))
        assert np.min(arrays['hm'][mask]-arrays['cc'][mask]) >= -2e-6
        assert np.min(arrays['hm'][mask]) >= -2e-6
        assert np.max(arrays['hm'][mask]) <= 1+2e-6
        nomix = t_nomix.ReadAsArray(0,y,ds.RasterXSize,rows)
        assert np.array_equal(valid(nomix,t_nomix.GetRasterBand(1).GetNoDataValue()),mask)
        predicted = config[period]['t_ref']+(1-arrays['hm'][mask].astype(float))*config['uhi_max']
        max_t_formula_error = max(max_t_formula_error,float(np.max(np.abs(nomix[mask].astype(float)-predicted))))
        assert np.min(arrays['t'][mask]) >= config[period]['t_ref']-1e-4
        assert np.max(arrays['t'][mask]) <= config[period]['t_ref']+config['uhi_max']+1e-4
        fragment_mask = label > 0
        labs = label[fragment_mask]
        for key,array in arrays.items():
            values = array[mask].astype(np.float64)
            glob = global_stats[key]
            glob['n'] += values.size
            glob['sum'] += float(values.sum())
            glob['sum2'] += float(np.dot(values,values))
            glob['min'] = min(glob['min'],float(values.min()))
            glob['max'] = max(glob['max'],float(values.max()))
            vals = array[fragment_mask].astype(np.float64)
            record = accum[key]
            record['n'] += np.bincount(labs,minlength=N+1)
            record['sum'] += np.bincount(labs,weights=vals,minlength=N+1)
            record['sum2'] += np.bincount(labs,weights=vals*vals,minlength=N+1)
            np.minimum.at(record['min'],labs,vals)
            np.maximum.at(record['max'],labs,vals)
    assert max_cc_error < 2e-6, max_cc_error
    assert max_t_formula_error < 1e-4, max_t_formula_error
    for key,record in accum.items():
        assert np.all(record['n'][1:]>0)
        record['mean'] = np.divide(record['sum'],record['n'],out=np.zeros(N+1),where=record['n']>0)
        var = np.divide(record['sum2'],record['n'],out=np.zeros(N+1),where=record['n']>0)-record['mean']**2
        record['sd'] = np.sqrt(np.maximum(var,0))
        g = global_stats[key]
        g['mean'] = g['sum']/g['n']
        g['sd'] = math.sqrt(max(g['sum2']/g['n']-g['mean']**2,0))
    for key in accum:
        assert np.array_equal(accum['t']['n'],accum[key]['n'])
    qa = dict(period=period, raster_files={k:str(p) for k,p in paths.items()}, grid={'size':[ds.RasterXSize,ds.RasterYSize],'geotransform':ds.GetGeoTransform(),'epsg':31983}, full_raster_stats=global_stats, max_cc_formula_absolute_error=max_cc_error, max_temperature_nomix_formula_absolute_error=max_t_formula_error, masks_match_input=True, hm_at_least_cc=True, t_in_reference_uhi_bounds_within_tolerance=True, temperature_bounds_tolerance_C=1e-4, temperature_below_reference_max_C=max(0.,config[period]['t_ref']-global_stats['t']['min']), temperature_above_reference_plus_uhi_max_C=max(0.,global_stats['t']['max']-config[period]['t_ref']-config['uhi_max']), all_fragments_have_data=True)
    print(json.dumps({'period':period,'verified':True,'t_range':[global_stats['t']['min'],global_stats['t']['max']],'t_mean':global_stats['t']['mean']}),flush=True)
    return accum,qa,rasters


def main():
    manifest = json.loads((ROOT/'01_Entradas/preparacao.json').read_text(encoding='utf-8'))
    config = json.loads((ROOT/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    for name,record in manifest['input_files'].items():
        if Path(name).name == 'CONFIGURACAO_PREPARADA.json':
            # O registro compartilhado muda de estado após a conclusão; a
            # fotografia usada nesta rodada permanece imutável em 01_Entradas.
            current = json.loads(Path(name).read_text(encoding='utf-8'))
            for key in ('coverage','biophysical_table','eto','day','night','uhi_max','green_area_cooling_distance','t_air_average_radius'):
                assert current[key] == config[key], 'Parâmetro científico alterado: '+key
        else:
            assert sha(Path(name)) == record['sha256'], 'Fonte alterada: '+name
    for period in ('day','night'):
        assert json.loads((ROOT/f'05_Verificacoes/execucao_{period}_local.json').read_text(encoding='utf-8'))['exit_code'] == 0
    with open(config['biophysical_table'],encoding='utf-8-sig',newline='') as stream:
        table = list(csv.DictReader(stream))
    ids = gdal.Open(str(ROOT/'04_Extracao/id_frag_grade_3m.tif'))
    coverage = gdal.Open(config['coverage'])
    records = {}
    geoms = {}
    with ogr.Open(manifest['metric_source']) as vector:
        for feature in vector.GetLayer():
            identifier = int(feature['id_frag'])
            records[identifier] = {key:feature[key] for key in ['id_frag','classe_avu','form_pred','cat_iv','Area']}
            geoms[identifier] = feature.GetGeometryRef().Clone()
    all_results,qa,rasters = {},{},{}
    copy_checks = []
    for period,folder in [('day','02_Dia_Concluido'),('night','03_Noite_Concluido')]:
        native = Path(json.loads((ROOT/f'01_Entradas/argumentos_{period}.json').read_text(encoding='utf-8'))['args']['workspace_dir'])
        for native_path in native.rglob('*'):
            if native_path.is_file() and native_path.suffix.lower() in ('.tif','.html','.json','.shp','.dbf','.shx','.prj'):
                copy_path = ROOT/folder/native_path.relative_to(native)
                native_hash = sha(native_path)
                assert sha(copy_path) == native_hash, 'Cópia divergente: '+str(copy_path)
                copy_checks.append({'period':period,'file':str(native_path.relative_to(native)),'sha256':native_hash,'copy_equal':True})
        all_results[period],qa[period],rasters[period] = aggregate(period,folder,config,ids,coverage,table)
        assert qa[period]['full_raster_stats']['t']['n'] == manifest['total_valid_pixels']
        for identifier,record in records.items():
            assert abs(all_results[period]['t']['n'][identifier]*9-record['Area']) < .001
    assert np.array_equal(all_results['day']['t']['n'],all_results['night']['t']['n'])
    sample_ids = [int(x) for x in np.random.default_rng(20261116).choice(np.arange(1,N+1),size=16,replace=False)]
    spotchecks = []
    for identifier in sample_ids:
        geom = geoms[identifier]
        for period in ('day','night'):
            ds = rasters[period]['t']
            gt = ds.GetGeoTransform()
            xmin,xmax,ymin,ymax = geom.GetEnvelope()
            x0,y0 = max(0,int(math.floor((xmin-gt[0])/3))),max(0,int(math.floor((gt[3]-ymax)/3)))
            x1,y1 = min(ds.RasterXSize,int(math.ceil((xmax-gt[0])/3))),min(ds.RasterYSize,int(math.ceil((gt[3]-ymin)/3)))
            memvec = ogr.GetDriverByName('Memory').CreateDataSource('')
            layer = memvec.CreateLayer('patch',srs=ds.GetSpatialRef(),geom_type=ogr.wkbMultiPolygon)
            feat = ogr.Feature(layer.GetLayerDefn()); feat.SetGeometry(geom); layer.CreateFeature(feat)
            mem = gdal.GetDriverByName('MEM').Create('',x1-x0,y1-y0,1,gdal.GDT_Byte)
            mem.SetGeoTransform((gt[0]+x0*3,3,0,gt[3]-y0*3,0,-3)); mem.SetProjection(ds.GetProjection())
            mem.GetRasterBand(1).Fill(0)
            gdal.RasterizeLayer(mem,[1],layer,burn_values=[1],options=['ALL_TOUCHED=FALSE'])
            mask = mem.ReadAsArray()>0
            assert int(mask.sum()) == all_results[period]['t']['n'][identifier]
            for key,raster in rasters[period].items():
                values = raster.ReadAsArray(x0,y0,x1-x0,y1-y0)[mask].astype(float)
                expected = all_results[period][key]
                assert abs(float(values.mean())-expected['mean'][identifier]) < 1e-8
                assert float(values.min()) == expected['min'][identifier]
                assert float(values.max()) == expected['max'][identifier]
            spotchecks.append({'id_frag':identifier,'period':period,'pixels':int(mask.sum()),'geometry_rasterized_independently':True,'three_indicators_agree':True})
    fields = ['id_frag','classe_avu','form_pred','cat_iv','area_m2','n_pix','area_amostrada_m2','cobertura_percentual']
    for period in ('dia','noite'):
        fields += [f'{key}_{period}_{stat}' for key in ('cc','hm','t') for stat in ('mean','min','max','sd')]
    output_rows = []
    for identifier in sorted(records):
        source = records[identifier]
        row = {key:source[key] for key in ['id_frag','classe_avu','form_pred','cat_iv']}
        n = int(all_results['day']['t']['n'][identifier])
        row.update(area_m2=source['Area'],n_pix=n,area_amostrada_m2=n*9,cobertura_percentual=100.*n*9/source['Area'])
        for period,short in [('day','dia'),('night','noite')]:
            for key in ('cc','hm','t'):
                for stat in ('mean','min','max','sd'):
                    row[f'{key}_{short}_{stat}'] = float(all_results[period][key][stat][identifier])
        output_rows.append(row)
    csv_path = ROOT/'04_Extracao/clima_seca_2026_fragmentos_46876.csv'
    with csv_path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(output_rows)
    gpkg_path = ROOT/'04_Extracao/clima_seca_2026_fragmentos_46876.gpkg'
    assert not gpkg_path.exists(), 'Não sobrescrever extração existente'
    gpkg = gdal.VectorTranslate(str(gpkg_path),manifest['metric_source'],format='GPKG',layerName='clima_fragmentos')
    layer = gpkg.GetLayer()
    new_fields = [field for field in fields if field not in records[1]]
    for field in new_fields:
        layer.CreateField(ogr.FieldDefn(field,ogr.OFTInteger64 if field=='n_pix' else ogr.OFTReal))
    layer.SetMetadata({'METODO':'Estatísticas por centro de pixels de 3 m das saídas oficiais InVEST 3.20.2; sd populacional','PERIODO':'Seca 2026: cenários dia e noite separados','CHAVE':'id_frag atual, 46876 fragmentos; igualdade geométrica e de área conferida','RISCO':'Sem classificação de risco; sem média dia/noite','CC_HM_UNIDADE':'Adimensional','TEMPERATURA_UNIDADE':'graus Celsius','LIMITACOES':'UHI superficial diurna transferida para ar e noite por hipótese; parâmetros sem calibração local','ORIGEM_EXECUCAO':str(ROOT)})
    gpkg.StartTransaction()
    for feature in layer:
        row = output_rows[int(feature['id_frag'])-1]
        for field in new_fields:
            feature.SetField(field,row[field])
        layer.SetFeature(feature)
    gpkg.CommitTransaction(); gpkg = None
    with csv_path.open(encoding='utf-8-sig',newline='') as stream:
        csv_rows = {int(row['id_frag']):row for row in csv.DictReader(stream)}
    with ogr.Open(str(gpkg_path)) as reread:
        assert reread.GetLayer().GetFeatureCount() == len(csv_rows) == N
        for feature in reread.GetLayer():
            identifier = int(feature['id_frag'])
            assert bytes(feature.GetGeometryRef().ExportToWkb()) == bytes(geoms[identifier].ExportToWkb())
            for field in new_fields:
                assert feature[field] == float(csv_rows[identifier][field])
    result = {'status':'executado_extraido_conferido','finished_at':datetime.now().astimezone().isoformat(),'invest_version':'3.20.2','fragment_count':N,'id_field':'id_frag','extraction_method':'Centros de pixels de 3 m; média, mínimo, máximo e desvio padrão populacional por fragmento','fragment_pixel_coverage_percent':[min(r['cobertura_percentual'] for r in output_rows),max(r['cobertura_percentual'] for r in output_rows)],'scenarios':qa,'independent_spotchecks':spotchecks,'native_to_delivered_copy_checks':copy_checks,'csv_gpkg_full_comparison':True,'input_hashes_unchanged':True,'source_geometries_preserved':True,'risk_classification_performed':False,'day_night_average_performed':False,'empirical_thermal_validation':False,'outputs':{'csv':str(csv_path),'gpkg':str(gpkg_path)}}
    write_json(ROOT/'05_Verificacoes/RESULTADO_EXECUCAO_E_EXTRACAO.json',result)
    output_hashes = {}
    for folder in ('02_Dia_Concluido','03_Noite_Concluido','04_Extracao'):
        for path in (ROOT/folder).iterdir():
            if path.is_file() and path.suffix.lower() in ('.tif','.gpkg','.csv','.json','.html'):
                output_hashes[str(path.relative_to(ROOT))] = {'bytes':path.stat().st_size,'sha256':sha(path)}
    write_json(ROOT/'05_Verificacoes/HASHES_PRODUTOS.json',output_hashes)
    print(json.dumps({'complete':True,'fragments':N,'csv':str(csv_path),'gpkg':str(gpkg_path)}),flush=True)


if __name__ == '__main__':
    main()
