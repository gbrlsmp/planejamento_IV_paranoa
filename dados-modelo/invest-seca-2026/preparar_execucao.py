"""Prepara a rodada autorizada, sem alterar as fontes e sem recalcular insumos."""
from pathlib import Path
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import hashlib
import json
import math
import numpy as np
from osgeo import gdal, ogr

gdal.UseExceptions()
ogr.UseExceptions()
ROOT = Path(__file__).resolve().parent
CLIMA = ROOT.parent.parent
BASE = CLIMA.parents[2]
CONFIG = CLIMA / '03_Tabelas/Parametros_climaticos/CONFIGURACAO_PREPARADA.json'
FRAG = BASE / '02_Análises/03_Ecologia/01_Fragmentação'
FRAGMENTOS = FRAG / 'fragmentos_vegetacao.gpkg'
METRICAS = FRAG / 'MK_Fragmentation_Bacia_Paranoa_45m_AVU_PatchMetrics.gpkg'
BACIA = BASE / '01_Base/vetores/01_Limites/Bacia_Paranoa_MERGE_IPE_DF_2023.shp'


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    for name in ('01_Entradas', '02_Dia', '03_Noite', '04_Extracao', '05_Verificacoes'):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    if (ROOT / '01_Entradas/preparacao.json').exists():
        raise RuntimeError('Preparação já registrada: conferir em vez de sobrescrever.')
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    assert config['green_area_cooling_distance'] == 450
    assert config['t_air_average_radius'] == 500
    coverage = gdal.Open(config['coverage'])
    eto = gdal.Open(config['eto'])
    assert coverage.GetGeoTransform() == eto.GetGeoTransform()
    assert coverage.GetProjection() == eto.GetProjection()
    assert (coverage.RasterXSize, coverage.RasterYSize) == (eto.RasterXSize, eto.RasterYSize)
    assert coverage.GetSpatialRef().GetAuthorityCode(None) == '31983'
    assert coverage.GetGeoTransform()[1:3] == (3.0, 0.0)
    with open(config['biophysical_table'], encoding='utf-8-sig', newline='') as stream:
        table = list(csv.DictReader(stream))
    codes = {int(r['lucode']) for r in table}
    assert len(codes) == len(table) == 12
    counts = Counter()
    valid_count = 0
    eto_min, eto_max = math.inf, -math.inf
    for y in range(0, coverage.RasterYSize, 256):
        rows = min(256, coverage.RasterYSize-y)
        land = coverage.ReadAsArray(0, y, coverage.RasterXSize, rows)
        evap = eto.ReadAsArray(0, y, eto.RasterXSize, rows)
        valid = land != coverage.GetRasterBand(1).GetNoDataValue()
        assert np.array_equal(valid, evap != eto.GetRasterBand(1).GetNoDataValue())
        u, n = np.unique(land[valid], return_counts=True)
        counts.update(dict(zip(map(int,u), map(int,n))))
        if valid.any():
            assert np.isfinite(evap[valid]).all()
            eto_min = min(eto_min, float(evap[valid].min()))
            eto_max = max(eto_max, float(evap[valid].max()))
            valid_count += int(valid.sum())
    assert set(counts) <= codes
    assert eto_min > 0 and eto_min == eto_max
    aoi_path = ROOT / '01_Entradas/bacia_paranoa_31983.gpkg'
    aoi = gdal.VectorTranslate(str(aoi_path), str(BACIA), format='GPKG', dstSRS='EPSG:31983', layerName='bacia_paranoa')
    aoi = None
    with ogr.Open(str(FRAGMENTOS)) as source, ogr.Open(str(METRICAS)) as metric:
        layer = source.GetLayer()
        met_layer = metric.GetLayer()
        assert layer.GetFeatureCount() == met_layer.GetFeatureCount() == 46876
        records = {int(f['id_frag']): (f.GetGeometryRef().GetArea(), bytes(f.GetGeometryRef().ExportToWkb())) for f in layer}
        assert sorted(records) == list(range(1, 46877))
        for feature in met_layer:
            identifier = int(feature['id_frag'])
            area, wkb = records[identifier]
            assert abs(area - float(feature['Area'])) < 0.001
            assert wkb == bytes(feature.GetGeometryRef().ExportToWkb())
        layer.ResetReading()
        id_path = ROOT / '04_Extracao/id_frag_grade_3m.tif'
        ids = gdal.GetDriverByName('GTiff').Create(str(id_path), coverage.RasterXSize, coverage.RasterYSize, 1, gdal.GDT_UInt32, options=['TILED=YES','COMPRESS=DEFLATE','BIGTIFF=IF_SAFER'])
        ids.SetGeoTransform(coverage.GetGeoTransform())
        ids.SetProjection(coverage.GetProjection())
        ids.GetRasterBand(1).SetNoDataValue(0)
        ids.GetRasterBand(1).Fill(0)
        gdal.RasterizeLayer(ids, [1], layer, options=['ATTRIBUTE=id_frag','ALL_TOUCHED=FALSE'])
        ids.FlushCache()
        pixels = np.zeros(46877, dtype=np.int64)
        for y in range(0, coverage.RasterYSize, 256):
            rows = min(256, coverage.RasterYSize-y)
            labels = ids.ReadAsArray(0, y, coverage.RasterXSize, rows)
            land = coverage.ReadAsArray(0, y, coverage.RasterXSize, rows)
            assert np.array_equal(labels > 0, np.isin(land, [3,4,11,12,100]))
            pixels += np.bincount(labels.ravel(), minlength=46877)
        for identifier,(area,_) in records.items():
            assert pixels[identifier] > 0
            assert abs(pixels[identifier] * 9 - area) < 0.001
        ids = None
    write_json(ROOT/'01_Entradas/configuracao_confirmada.json', config)
    common = dict(lulc_raster_path=config['coverage'], ref_eto_raster_path=config['eto'], aoi_vector_path=str(aoi_path), biophysical_table_path=config['biophysical_table'], green_area_cooling_distance=450, t_air_average_radius=500, uhi_max=config['uhi_max'], do_energy_valuation=False, do_productivity_valuation=False, n_workers=-1)
    for period, folder in [('day','02_Dia'),('night','03_Noite')]:
        args = dict(common, workspace_dir=str(ROOT/folder), results_suffix='seca_2026_'+('dia' if period=='day' else 'noite'), t_ref=config[period]['t_ref'], cc_method=config[period]['cc_method'])
        if period == 'day':
            args.update(cc_weight_shade=0.6, cc_weight_albedo=0.2, cc_weight_eti=0.2)
        write_json(ROOT/f'01_Entradas/argumentos_{period}.json', dict(args=args, invest_version='3.20.2', model_name='natcap.invest.urban_cooling_model.urban_cooling_model'))
    files = [Path(config[k]) for k in ('coverage','eto','biophysical_table')]+[CONFIG, FRAGMENTOS, METRICAS, aoi_path]
    files += [BACIA.with_suffix(s) for s in ('.shp','.shx','.dbf','.prj')]
    manifest = dict(date=datetime.now().astimezone().isoformat(), model_version='3.20.2', input_files={str(p):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files}, fragment_source=str(FRAGMENTOS), metric_source=str(METRICAS), fragment_count=46876, fragment_ids='id_frag 1..46876', geometry_comparison='WKB igual entre fragmentos e métricas atuais, por id_frag', spatial_check='Rasterização por centro em grade original: igualdade pixel a pixel com IV 3/4/11/12/100 e área por fragmento igual a contagem × 9 m²', pixels_by_code=dict(counts), total_valid_pixels=valid_count, vegetation_pixels=int(pixels[1:].sum()), uniform_eto_range=[eto_min,eto_max], grid={'size':[coverage.RasterXSize,coverage.RasterYSize],'geotransform':coverage.GetGeoTransform(),'epsg':31983}, source_files_modified=False, climate_risk_classification=False)
    write_json(ROOT/'01_Entradas/preparacao.json', manifest)
    print(json.dumps({'prepared':True,'valid_pixels':valid_count,'vegetation_pixels':int(pixels[1:].sum()),'fragments':46876,'eto':eto_min}))


if __name__ == '__main__':
    main()
