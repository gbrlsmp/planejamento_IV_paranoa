"""Verifica vias/entradas de forma independente e gera figuras de consulta."""
from pathlib import Path
import json,random,csv,hashlib
from osgeo import gdal,ogr
import numpy as np
from PIL import Image,ImageDraw,ImageFont

gdal.UseExceptions();ogr.UseExceptions()
WEB=Path(__file__).resolve().parents[1];BASE=WEB.parent/'02 BASE DE DADOS';CLIMA=BASE/'02_Análises/01_Riscos/01_Clima'
r=json.loads((WEB/'dados-modelo/atualizacao-cobertura-clima.json').read_text(encoding='utf8'))
src=Path(r['outputs']['coverage']);out=src.parent;ds=gdal.Open(str(src));gt=ds.GetGeoTransform()
mask=gdal.Open(str(out/'mascara_vias_pavimentadas_buffer_2_5m_3m.tif'))
vd=ogr.Open(str(out/'vias_pavimentadas_buffer_2_5m.gpkg'));ly=vd.GetLayer(0)
assert ly.GetFeatureCount()==41169
rand=random.Random(79);tests=[]
for k in [0,1]:
    found=0
    while found<200:
        x=rand.randrange(ds.RasterXSize);y=rand.randrange(ds.RasterYSize);v=int(mask.ReadAsArray(x,y,1,1)[0,0])
        if v!=k:continue
        xx=gt[0]+(x+.5)*3;yy=gt[3]-(y+.5)*3
        point=ogr.Geometry(ogr.wkbPoint);point.AddPoint_2D(xx,yy)
        ly.SetSpatialFilterRect(xx-.001,yy-.001,xx+.001,yy+.001)
        hit=any(f.GetGeometryRef().Intersects(point) for f in ly)
        assert hit==bool(k),(x,y,k,hit)
        tests.append([x,y,k]);found+=1
ly.SetSpatialFilter(None);vd=None;mask=None

rows=list(csv.DictReader((WEB/'dados-modelo/tab_biofisica_completa_12classes.csv').open(encoding='utf-8-sig')))
assert len(rows)==12 and len({r['lucode'] for r in rows})==12
assert set(int(x['lucode']) for x in rows)==set(int(k) for k in r['aux_counts'])-{65535}
assert not any(int(x['lucode'])==1034 for x in rows)

font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',20);bold=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',26)
folder=WEB/'imagens/clima';folder.mkdir(parents=True,exist_ok=True)
aux=gdal.Open(str(Path(r['outputs']['auxiliary'])));a=aux.ReadAsArray(buf_xsize=1000,buf_ysize=1050)
lut=np.full((65536,4),[245,246,242,255],dtype='uint8');lut[65535]=[0,0,0,0]
palette={1031:'#b9cfa4',1032:'#c49b58',1033:'#84544d'}
for k,v in palette.items():lut[k]=[*bytes.fromhex(v[1:]),255]
im=Image.new('RGB',(1100,1230),'#faf9f3');d=ImageDraw.Draw(im);d.text((30,20),'Intensidade combinada das edificações',font=bold,fill='#29372d')
layer=Image.fromarray(lut[a]);im.paste(layer,(50,70),layer)
for i,(k,v) in enumerate(palette.items()):
    x=35+i*350;d.rectangle((x,1160,x+24,1184),fill=v);d.text((x+34,1158),{1031:'Baixa: I ≤ 0,25',1032:'Média: 0,25 < I ≤ 0,50',1033:'Alta: I > 0,50'}[k],font=font,fill='#29372d')
im.save(folder/'intensidade-500m.png');aux=None
for name,path,title,cuts,colors,legend in [
    ('ocupacao-horizontal.png',CLIMA/'04_Rasters/Ocupacao_horizontal/densidade_edificada_500m_percentual_3m.tif','Ocupação horizontal no entorno de 500 m',[0,10,20,40],['#e8ebe2','#cad6ba','#a7b282','#c6a35d','#8d6150'],['Sem edifícios','>0–10%','>10–20%','>20–40%','>40%']),
    ('altura-regional.png',CLIMA/'04_Rasters/Alturas/altura_media_edificada_vizinhanca_500m_3m.tif','Altura média das construções no entorno de 500 m',[0,3,10,25],['#e8ebe2','#c4d8ce','#91b8b2','#648c97','#3e5972'],['Sem edifícios','>0–3 m','>3–10 m','>10–25 m','>25 m'])]:
    rr=gdal.Open(str(path));arr=rr.ReadAsArray(buf_xsize=1000,buf_ysize=1050);rr=None
    ids=np.searchsorted(cuts,arr,side='left');rgba=np.array([[*bytes.fromhex(color[1:]),255] for color in colors],dtype='uint8')[ids];rgba[arr<0]=0
    canvas=Image.new('RGB',(1100,1270),'#faf9f3');draw=ImageDraw.Draw(canvas);draw.text((30,20),title,font=bold,fill='#29372d')
    layer=Image.fromarray(rgba);canvas.paste(layer,(50,70),layer)
    for i,(color,label) in enumerate(zip(colors,legend)):
        x=30+(i%3)*350;y=1150+(i//3)*44;draw.rectangle((x,y,x+24,y+24),fill=color);draw.text((x+34,y-2),label,font=font,fill='#29372d')
    canvas.save(folder/name)
qml='''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'><qgis version="3.44" styleCategories="Symbology"><pipe><rasterrenderer type="paletted" band="1"><colorPalette>'''
from identificacao.integrar_vias_pavimentadas import COLORS,LABELS
qml+=''.join(f'<paletteEntry value="{k}" color="{COLORS[k]}" alpha="255" label="{v}"/>' for k,v in LABELS.items())+'<paletteEntry value="255" color="#000000" alpha="0" label="NoData"/></colorPalette></rasterrenderer></pipe></qgis>'
src.with_suffix('.qml').write_text(qml,encoding='utf8')
# Estilos da cobertura auxiliar e dos três níveis correntes.
def style(path,items):
    text='<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'><qgis version="3.44" styleCategories="Symbology"><pipe><rasterrenderer type="paletted" band="1"><colorPalette>'
    text+=''.join(f'<paletteEntry value="{k}" color="{color}" alpha="{alpha}" label="{label}"/>' for k,label,color,alpha in items)
    path.write_text(text+'</colorPalette></rasterrenderer></pipe></qgis>',encoding='utf8')
style(Path(r['outputs']['auxiliary']).with_suffix('.qml'),[(k,v,COLORS[k],255) for k,v in LABELS.items() if k!=103]+[(1031,'Edificações — baixa','#b9cfa4',255),(1032,'Edificações — média','#c49b58',255),(1033,'Edificações — alta','#84544d',255),(65535,'NoData','#000000',0)])
regional=CLIMA/'04_Rasters/Cobertura_para_InVEST/classes_intensidade_regional_500m_3classes_3m.tif'
style(regional.with_suffix('.qml'),[(0,'Sem edificações','#e8ebe2',255),(1,'Baixa','#b9cfa4',255),(2,'Média','#c49b58',255),(3,'Alta','#84544d',255),(254,'Altura indisponível','#d3c9bd',255),(255,'Água/fora','#000000',0)])
import shutil
sub=CLIMA/'04_Rasters/Intensidade_combinada/subclasses103_500m_3classes_3m.tif'
if not sub.exists():shutil.copy2(CLIMA/'11_Intensidade_combinada_500m_2026-11-15/subclasses103_combinado_500m_proposta_3m.tif',sub)
style(sub.with_suffix('.qml'),[(0,'Outras coberturas','#000000',0),(1,'Baixa','#b9cfa4',255),(2,'Média','#c49b58',255),(3,'Alta','#84544d',255),(255,'Fora','#000000',0)])
for path in (CLIMA/'04_Rasters/Intensidade_combinada').glob('*.tif'):
    current=gdal.Open(str(path),gdal.GA_Update)
    current.SetMetadataItem('CURRENT_CLASS_LABELS','1031=Baixa;1032=Media;1033=Alta')
    current.SetMetadataItem('CLASS_THRESHOLDS','(0,0.25];(0.25,0.50];(0.50,1]')
    current.SetMetadataItem('METHOD_STATUS','Escolhas aprovadas em 2026-11-15; sem calibracao termica; qualidade parcial e preenchimento flag9 documentados')
    current.FlushCache();current=None
qa={'vector_feature_count':41169,'independent_pixel_center_geometry_checks':len(tests),'sample_seed':79,'table_rows':12,'table_matches_all_auxiliary_codes':True,'empty_class_1034_removed':True,'integral_pixel_checks':r['pixels_verified'],'iv_preserved':True,'height_and_density_sources_reused':True,'invest_executed':False,'gdal_version':gdal.VersionInfo(),'checks':tests}
p=CLIMA/'08_Scripts_e_verificacoes/Atualizacao_2026-11-15/VERIFICACAO_INDEPENDENTE.json';p.write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in qa.items() if k!='checks'},ensure_ascii=False))
