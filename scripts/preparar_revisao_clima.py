"""Prepara nova rodada A001, preservando a rodada e as fontes anteriores."""
from pathlib import Path
import csv, json, statistics, shutil, hashlib
from collections import defaultdict

WEB = Path(__file__).resolve().parents[1]
CLIMA = WEB.parent/'02 BASE DE DADOS/02_Análises/01_Riscos/01_Clima'
SOURCE = CLIMA/'01_Fontes/Landsat/Parametros_seca_2026-11-14'
OLD = CLIMA/'06_Execucoes_InVEST/Seca_2026_Dia_Noite_2026-11-16'
RUN = CLIMA/'06_Execucoes_InVEST/Seca_2026_A001_Dia_Noite_2026-11-16'
SCRATCH = Path(r'C:\Users\sampa\.codex\visualizations\2026\11\16\01a1e28f-51e3-7912-88b0-253b4c73ed21')/'tmp/invest-a001'

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def main():
    assert not RUN.exists(), 'Rodada existente: conferir antes de repetir a preparação.'
    RUN.mkdir(parents=True)
    with (SOURCE/'INMET_completude_diaria_janelas.csv').open(encoding='utf-8-sig',newline='') as f:
        daily=[r for r in csv.DictReader(f) if r['station']=='A001']
    sets={w:{r['data_local'] for r in daily if r[w+'_elegivel_80pct']=='1' and r['dia_atinge_20']=='1'} for w in ('dia','noite')}
    paired=sets['dia'] & sets['noite']
    grouped=defaultdict(list)
    with (SOURCE/'INMET_horario_seca_com_janelas.csv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['station']=='A001' and r['data_local'] in paired and r['temperatura_ar_C']!='':
                grouped[(r['data_local'],r['janela_solar'])].append(float(r['temperatura_ar_C']))
    means=[{'data_local':d,'janela':w,'leituras_validas':len(grouped[(d,w)]),'media_ar_C':statistics.mean(grouped[(d,w)])} for d in sorted(paired) for w in ('dia','noite')]
    tref={w:statistics.mean(r['media_ar_C'] for r in means if r['janela']==w) for w in ('dia','noite')}
    qa=json.loads((SOURCE/'INMET_QA_SOLAR.json').read_text(encoding='utf-8'))
    source=next(r for r in qa['fontes'] if r['station']=='A001')
    # O caminho registrado precede a reorganização; localizar a mesma fonte pelo nome.
    candidates=list((CLIMA/'01_Fontes').rglob(Path(source['source']).name))
    if Path(source['source']).is_file(): candidates=[Path(source['source'])]
    assert len(candidates)==1, candidates
    assert hashlib.sha256(candidates[0].read_bytes()).hexdigest()==source['sha256']
    result={'station':'A001','nome':'BRASÍLIA','periodo':['2026-05-01','2026-09-30'],'dias_pareados':len(paired),'tref':tref,'datas':sorted(paired),'datas_excluidas':sorted({r['data_local'] for r in daily}-paired),'metodo':'Média das médias diárias por janela solar, mesmas datas pareadas; >=20 leituras/dia e >=80% por janela. Sem preenchimento. Noite: antes do nascer e após o pôr do sol na mesma data civil UTC−03.','selecao':'A001 por decisão da pesquisadora em 16/11/2026; estação urbana usada como referência operacional, sem interpretação automática como rural ou mais fria.','source':dict(source,path_atual=str(candidates[0])),'hourly_table_sha256':hashlib.sha256((SOURCE/'INMET_horario_seca_com_janelas.csv').read_bytes()).hexdigest()}
    save(RUN/'TREF_A001_RESULTADOS.json',result)
    with (RUN/'Tref_A001_medias_diarias.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(means[0]));w.writeheader();w.writerows(means)
    config=json.loads((OLD/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    config.update(status='preparado_A001',invest_executed=False,reference_station='A001',reference_days=len(paired))
    config['day']['t_ref']=tref['dia'];config['night']['t_ref']=tref['noite']
    save(RUN/'configuracao_a001.json',config)
    for name in ('preparar_execucao.py','executar_invest.ps1','extrair_e_verificar.py'):
        text=(OLD/name).read_text(encoding='utf-8')
        if name=='preparar_execucao.py':text=text.replace("CONFIG = CLIMA / '03_Tabelas/Parametros_climaticos/CONFIGURACAO_PREPARADA.json'","CONFIG = ROOT / 'configuracao_a001.json'")
        (RUN/name).write_text(text,encoding='utf-8')
    shutil.copyfile(WEB/'scripts/concluir_revisao_clima.ps1',RUN/'concluir_entrega.ps1')
    # A preparação oficial cria argumentos na rodada; redirecionamento do workspace
    # ocorre em iniciar(), após a preparação e antes da execução oficial.
    save(RUN/'referencias_preservadas.json',{'previous_run':str(OLD),'scratch':str(SCRATCH),'source_files_modified':False})
    print(json.dumps(result,ensure_ascii=False))

def iniciar():
    for period in ('day','night'):
        path=RUN/f'01_Entradas/argumentos_{period}.json'
        args=json.loads(path.read_text(encoding='utf-8'))
        target=SCRATCH/period
        assert not target.exists(), 'Workspace deve ser novo.'
        args['args']['workspace_dir']=str(target)
        save(path,args)

if __name__=='__main__':
    import sys
    iniciar() if '--iniciar' in sys.argv else main()
