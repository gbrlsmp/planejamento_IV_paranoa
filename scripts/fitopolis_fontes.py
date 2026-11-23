"""Fontes aprovadas. Nenhum caminho aponta para modelos climáticos históricos."""
import os
from pathlib import Path

BASE = Path(os.environ['PARANOA_BASE_DADOS'])
WEB = Path(__file__).resolve().parents[1]
RUN = BASE/'02_Análises/04_Fitopolis/Diagnostico_2026-11-23'
CLIMA = BASE/'02_Análises/01_Riscos/01_Clima/06_Execucoes_InVEST/Seca_2026_A001_102_104_2026-11-16'
LIMITES = BASE/'01_Base/vetores/01_Limites'
FONTES = {
    'bacia': LIMITES/'Bacia_Paranoa_MERGE_IPE_DF_2023.shp',
    'ras': LIMITES/'RAs_Bacia_Paranoa_MERGE_IPE_DF_2023.shp',
    'fragmentos': CLIMA/'04_Extracao/diagnostico_climatico_completo_46876.gpkg',
    'renda': BASE/'02_Análises/01_Riscos/02_Social/01_vetores/Bacia_Paranoa_setores_renda_Censo2022.gpkg',
    'edificacoes': BASE/'02_Análises/01_Riscos/04_Pressão Urbana/Construções Bacia do Paranoá.shp',
    'pre': BASE/'02_Análises/02_Condicionantes/02_Potencial de Recuperação Ecológica/PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp',
    'momentos': BASE/'02_Análises/02_Condicionantes/01_Momento Água/02_raster/momento_dominante.tif',
    'inundacao': BASE/'02_Análises/01_Riscos/03_Água/01_raster/inundacao_profundidade_TR5_hidro.tif',
    'uso': BASE/'02_Análises/03_Ecologia/03_Fitofisionomia/03_Raster/04_Vias_pavimentadas_2026-11-15/uso_cobertura_2026_vias_pavimentadas_3m.tif',
    'lst_seca': CLIMA/'07_Superficie_sazonal/lst_seca_30m.tif',
    'lst_chuva': CLIMA/'07_Superficie_sazonal/lst_chuva_30m.tif',
}
for periodo, pasta in [('dia','02_Dia_Concluido'),('noite','03_Noite_Concluido')]:
    for indicador, arquivo in [('cc','cc'),('hm','hm'),('t','T_air')]:
        FONTES[f'{indicador}_{periodo}'] = CLIMA/pasta/f'{arquivo}_seca_2026_{periodo}.tif'

if __name__ == '__main__':
    import json
    from osgeo import gdal
    gdal.UseExceptions()
    RUN.mkdir(parents=True, exist_ok=True)
    report = {}
    for key, path in FONTES.items():
        ds = gdal.OpenEx(str(path))
        if ds.RasterCount:
            report[key] = {'path':str(path), 'size':[ds.RasterXSize,ds.RasterYSize], 'crs':ds.GetSpatialRef().GetAuthorityCode(None)}
        else:
            layer=ds.GetLayer(0)
            report[key]={'path':str(path),'count':layer.GetFeatureCount(),'fields':[f.GetName() for f in layer.schema], 'crs':layer.GetSpatialRef().GetAuthorityCode(None)}
        print(key, report[key], flush=True)
    qa=json.loads((WEB/'dados-modelo/invest-seca-2026/verificacoes_bacia.json').read_text(encoding='utf8'))
    for period, info in qa['scenarios'].items():
        print(period, info.get('raster_files'),flush=True)
    (RUN/'inventario.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
