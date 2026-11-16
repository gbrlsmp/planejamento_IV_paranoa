"""Derivados leves das saídas oficiais; não roda InVEST nem publica fragmentos.

Uso no Python do QGIS: --execucao PASTA_DA_RODADA. Fontes somente leitura.
Web: média espacial em grade de 20 m EPSG:3857, seguida de codificação UInt16.
Estatísticas da bacia são copiadas da conferência integral dos rasters nativos.
"""
from pathlib import Path
import argparse,csv,hashlib,json,shutil
import numpy as np
from osgeo import gdal
from PIL import Image
from identificacao.paletas_identificacao import FRAGMENT_AREA_COLORS, ZEE_COLORS, RISK_COLORS

gdal.UseExceptions()
WEB=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def palette(colors):
    anchors=np.array([[int(c[i:i+2],16) for i in (1,3,5)] for c in colors])
    pos=np.linspace(0,len(colors)-1,65535)
    lo=np.minimum(np.floor(pos).astype(int),len(colors)-2)
    return np.floor(anchors[lo]*(1-(pos-lo))[:,None]+anchors[lo+1]*(pos-lo)[:,None]+.5).astype('uint8')


def publish(run):
    qa=json.loads((run/'05_Verificacoes/RESULTADO_EXECUCAO_E_EXTRACAO.json').read_text(encoding='utf-8'))
    assert qa['status']=='executado_extraido_conferido'
    config=json.loads((run/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    out=WEB/'dados-mapas/clima/urban-cooling-2026';out.mkdir(parents=True,exist_ok=True)
    archive=WEB/'dados-modelo/invest-seca-2026';archive.mkdir(parents=True,exist_ok=True)
    greens=list(FRAGMENT_AREA_COLORS.values())
    warm=[ZEE_COLORS['Lagoas de Estabilização'],ZEE_COLORS['Represas, Lagos, Lagoas e Rios'],FRAGMENT_AREA_COLORS[1],ZEE_COLORS['Formação Campestre'],RISK_COLORS[4][1],RISK_COLORS[5][1]]
    meta={'schema':1,'invest_version':'3.20.2','period':'Seca de 2026','source_resolution_m':3,'web_resolution_m':20,'web_crs':'EPSG:3857','web_resampling':'average','encoding':{'type':'uint16_rg','nodata':0,'minimum_code':1,'maximum_code':65535,'formula':'value = low + (R*256+G-1)/65534*(high-low)'},'palette_source':'scripts/identificacao/paletas_identificacao.py; cores existentes da identificação e do relatório','fragment_results_published':False,'risk_classification':False,'indicators':{}}
    summary=[];bounds=None
    import math
    t_limits=[math.floor(min(qa['scenarios'][p]['full_raster_stats']['t']['min'] for p in ('day','night'))),math.ceil(max(qa['scenarios'][p]['full_raster_stats']['t']['max'] for p in ('day','night')))]
    for key,label,unit,colors,limits in [('cc','Capacidade de resfriamento (CC)','',greens,[0,1]),('hm','Mitigação térmica (HM)','',greens,[0,1]),('t','Temperatura estimada do ar','°C',warm,t_limits)]:
        indicator={'label':label,'unit':unit,'colors':colors,'range':limits,'scenarios':{}}
        lut=palette(colors)
        for period,short in [('day','dia'),('night','noite')]:
            status=json.loads((run/f'05_Verificacoes/execucao_{period}_local.json').read_text(encoding='utf-8'))
            assert status['exit_code']==0
            source=Path(qa['scenarios'][period]['raster_files'][key])
            hashes=json.loads((run/'05_Verificacoes/HASHES_PRODUTOS.json').read_text(encoding='utf-8'))
            recorded=next(v['sha256'] for k,v in hashes.items() if k.replace('\\','/')==source.relative_to(run).as_posix())
            assert digest(source)==recorded
            ds=gdal.Warp('',str(source),format='MEM',dstSRS='EPSG:3857',xRes=20,yRes=20,outputBounds=bounds,resampleAlg='average',outputType=gdal.GDT_Float32,dstNodata=-9999,multithread=False)
            gt=ds.GetGeoTransform();array=ds.ReadAsArray();valid=np.isfinite(array)&(array!=-9999)
            actual_bounds=[gt[0],gt[3]+gt[5]*ds.RasterYSize,gt[0]+gt[1]*ds.RasterXSize,gt[3]]
            if bounds is None:bounds=actual_bounds
            assert bounds==actual_bounds
            low,high=limits
            assert float(array[valid].min())>=low-1e-4 and float(array[valid].max())<=high+1e-4
            q=np.zeros(array.shape,dtype='uint16')
            q[valid]=np.floor(np.clip((array[valid].astype(float)-low)/(high-low),0,1)*65534+.5).astype('uint16')+1
            encoded=np.zeros((*array.shape,4),dtype='uint8')
            encoded[:,:,0]=q>>8;encoded[:,:,1]=q&255;encoded[:,:,3]=valid*255
            filename=f'{key}-{short}-valores.png';Image.fromarray(encoded).save(out/filename,optimize=True)
            check=np.asarray(Image.open(out/filename))
            assert np.array_equal(check[:,:,0].astype('uint16')*256+check[:,:,1],q)
            decoded=low+(q[valid].astype(float)-1)/65534*(high-low)
            error=float(np.max(np.abs(decoded-array[valid])))
            assert error<=(high-low)/65534/2+1e-6
            rgba=np.zeros_like(encoded);rgba[valid,:3]=lut[q[valid].astype(int)-1];rgba[:,:,3]=valid*255
            preview=Image.fromarray(rgba);preview.thumbnail((850,900),Image.Resampling.NEAREST)
            preview_name=f'{key}-{short}-previa.png';preview.save(out/preview_name,optimize=True)
            stats=qa['scenarios'][period]['full_raster_stats'][key]
            indicator['scenarios'][short]={'file':filename,'preview':preview_name,'sha256':digest(out/filename),'preview_sha256':digest(out/preview_name),'source_file':source.name,'source_sha256':recorded,'native_stats':stats,'quantization_max_absolute_error':error,'web_valid_cells':int(valid.sum())}
            summary.append({'indicador':key,'cenario':short,'unidade':unit,'pixels_nativos_validos':stats['n'],'area_valida_ha':stats['n']*.0009,'media':stats['mean'],'minimo':stats['min'],'maximo':stats['max'],'desvio_padrao':stats['sd']})
            print(json.dumps({'published':key,'scenario':short,'size':[ds.RasterXSize,ds.RasterYSize],'quantization_error':error}),flush=True)
        meta['indicators'][key]=indicator
    meta.update(bounds=bounds,size=[ds.RasterXSize,ds.RasterYSize])
    meta['revision']=hashlib.sha256(json.dumps(meta,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    save(out/'manifesto.json',meta)
    with (archive/'estatisticas_bacia.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    config=json.loads((run/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    inputs=json.loads((run/'01_Entradas/preparacao.json').read_text(encoding='utf-8'))
    clean_config={k:config[k] for k in ('invest_version','day','night','uhi_max','green_area_cooling_distance','t_air_average_radius')}
    clean_config.update(invest_executed=True,do_energy_valuation=False,do_productivity_valuation=False,source_resolution_m=3,reference_station=config['reference_station'],reference_days=config['reference_days'])
    save(archive/'configuracao.json',clean_config)
    save(archive/'verificacoes_bacia.json',{'status':qa['status'],'scenarios':{p:{k:v for k,v in qa['scenarios'][p].items() if k!='raster_files'} for p in ('day','night')},'source_geometries_preserved':qa['source_geometries_preserved'],'input_hashes_unchanged':qa['input_hashes_unchanged'],'native_copy_hash_checks':len(qa['native_to_delivered_copy_checks']),'empirical_thermal_validation':False,'fragment_results':'Reservados à etapa de diagnóstico; não publicados aqui.'})
    save(archive/'fontes_sha256.json',{'inputs':{Path(k).name:v for k,v in inputs['input_files'].items() if not k.endswith('CONFIGURACAO_PREPARADA.json')},'rasters':{i:{p:{k:r[k] for k in ('source_file','source_sha256')} for p,r in cfg['scenarios'].items()} for i,cfg in meta['indicators'].items()}})
    for name in ('preparar_execucao.py','executar_invest.ps1','concluir_entrega.ps1','extrair_e_verificar.py'):
        shutil.copyfile(run/name,archive/name)
    (archive/'LEIA_ME.md').write_text('''# Execução oficial — seca 2026

InVEST Urban Cooling 3.20.2: dia (factors) e noite (intensity), 450 m de resfriamento e 500 m de mistura do ar. Energia/produtividade desativadas; sem média dia/noite ou classificação de risco.

`configuracao.json`, `estatisticas_bacia.csv`, `verificacoes_bacia.json` e `fontes_sha256.json` registram configuração, estatísticas nativas e integridade. Os scripts são cópias da execução local e documentam a reprodução: devem ser colocados na pasta da rodada com `01_Entradas/argumentos_day.json` e `argumentos_night.json`, gerados por `preparar_execucao.py`. Ajuste a raiz da base e o caminho do executável ao ambiente; não execute produtores sobre uma entrega existente.

As rodadas completas ocorreram em pasta local fora do OneDrive, após um teste integral em recorte, para evitar WinError 5 na limpeza de temporários. Os logs nativos e GeoTIFFs de 3 m permanecem na base local, em `01_Clima/06_Execucoes_InVEST/Seca_2026_Dia_Noite_2026-11-16`, pastas `02_Dia_Concluido` e `03_Noite_Concluido`. Não houve alteração de políticas de segurança.

O site usa derivados médios de 20 m em EPSG:3857 e codificação UInt16; consulta de valores e cores usam a mesma codificação. A legenda distingue escala comum e contraste do cenário. A estatística da bacia vem do raster nativo, não da prévia. As cores são interpoladas da paleta existente; não representam classes de risco.

UHI superficial diurno transferido ao ar e à noite por hipótese, ETo uniforme e ausência de calibração local continuam como limitações. Resultados por fragmento ficam para o diagnóstico e não integram estes arquivos de publicação.
''',encoding='utf-8')
    readme=archive/'LEIA_ME.md'
    text=readme.read_text(encoding='utf-8').replace('Seca_2026_Dia_Noite_2026-11-16','Seca_2026_A001_Dia_Noite_2026-11-16')
    text=text.replace('sem média dia/noite ou classificação de risco.', 'sem média dia/noite ou classificação de risco sanitário. Referência do ar A001 — Brasília, 153 datas pareadas; dia 24,265416609534256 °C e noite 19,714379846732786 °C. Referência operacional urbana, sem equivalência demonstrada ao ar rural.')
    text=text.replace('Resultados por fragmento ficam para o diagnóstico e não integram estes arquivos de publicação.', 'O diagnóstico atual publica os 46.876 fragmentos, classes térmicas relativas e polígonos de zonas relativamente quentes do InVEST. Consulte `diagnostico_fragmentos_46876.csv`, `tref_a001.json` e os manifestos em `dados-mapas/clima/diagnostico-2026` e `superficie-sazonal`. A classificação não foi calibrada e não representa risco sanitário. A rodada anterior A045 foi preservada na base local.')
    text+='\n\nPreparação atual: `scripts/preparar_revisao_clima.py` calcula as referências e gera uma nova pasta, recusando sobrescrever entregas. Após preparar entradas com o Python do QGIS, `--iniciar` define workspaces locais novos; `executar_invest.ps1` chama o InVEST oficial. Para concluir a cópia e extração use `scripts/concluir_revisao_clima.ps1 -RunRoot PASTA`. Os produtores `produzir_superficie_sazonal.py` e `publicar_diagnostico_clima.py` registram as composições, classes e polígonos. Ajuste os caminhos de ROOT/SCRATCH ao ambiente. Nenhuma execução modifica as fontes Landsat/INMET ou as geometrias originais.\n'
    readme.write_text(text,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execucao',type=Path,required=True)
    publish(parser.parse_args().execucao.resolve())
