"""Registra a correção 102/104 conferida, preservando os registros anteriores."""
import argparse,json,shutil
from pathlib import Path
from datetime import datetime
from corrigir_intensidade_noturna import RUN,PREVIOUS,CLIMA,WEB
from publicar_invest_seca_2026 import save,digest


def register(workbook):
    qa=json.loads((RUN/'05_Verificacoes/RESULTADO_EXECUCAO_E_EXTRACAO.json').read_text(encoding='utf-8'))
    audit=json.loads((RUN/'05_Verificacoes/VERIFICACAO_CORRECAO_NOTURNA.json').read_text(encoding='utf-8'))
    assert qa['status']=='executado_extraido_conferido' and audit['status']=='correcao_noturna_conferida'
    config=json.loads((RUN/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    backup=RUN/'09_Registros_vigentes_anteriores';backup.mkdir(exist_ok=True)
    params=CLIMA/'03_Tabelas/Parametros_climaticos';bio=CLIMA/'03_Tabelas/Biofisica'
    for path in [params/'CONFIGURACAO_PREPARADA.json',params/'PARAMETROS_CALCULADOS.json',bio/'tabela_biofisica_atual.xlsx',CLIMA/'LEIA_ME.md']:
        if not (backup/path.name).exists():shutil.copyfile(path,backup/path.name)
    assert workbook.is_file() and workbook.suffix=='.xlsx'
    shutil.copyfile(workbook,bio/'tabela_biofisica_atual.xlsx')
    shutil.copyfile(config['biophysical_table'],bio/'tab_biofisica_completa_18classes.csv')
    for source,target in [('nota-preenchimento-alturas.md','NOTA_TECNICA_PREENCHIMENTO_RESIDUAL_ALTURAS.md'),('nota-qualidade-alturas.md','NOTA_TECNICA_QUALIDADE_ALTURAS_REGIONAIS.md')]:
        destination=CLIMA/'02_Metodologia_e_notas_tecnicas'/target
        if not (backup/target).exists():shutil.copyfile(destination,backup/target)
        shutil.copyfile(WEB/'docs'/source,destination)
    assert digest(bio/'tab_biofisica_completa_18classes.csv')==digest(Path(config['biophysical_table']))
    config.update(status='correcao_noturna_102_104_executada_extraida_conferida',invest_executed=True,last_completed_run=str(RUN),last_completed_at=datetime.now().astimezone().isoformat(),fragment_count=46876,day_reused=True,new_day_execution=False,climate_risk_classification_pending=True,relative_thermal_classification_produced=True,site_change_status='branch_para_PR_sem_merge')
    save(params/'CONFIGURACAO_PREPARADA.json',config)
    previous=json.loads((backup/'PARAMETROS_CALCULADOS.json').read_text(encoding='utf-8'))
    previous.update(last_completed_run=str(RUN),escopo='Noite oficial refeita com intensidade 102/104; dia A001 anterior reaproveitado após prova integral de equivalência. Publicação proposta em PR, sem merge automático.')
    save(params/'PARAMETROS_CALCULADOS.json',previous)
    table=['| Cenário | Mínimo °C | Máximo °C | Média °C |','| --- | ---: | ---: | ---: |']
    for p,label in [('day','Dia preservado'),('night','Noite corrigida')]:
        s=qa['scenarios'][p]['full_raster_stats']['t'];table.append(f'| {label} | {s["min"]:.6f} | {s["max"]:.6f} | {s["mean"]:.6f} |')
    text='\n'.join([
        '# Resultados vigentes — correção noturna 102/104','',
        'InVEST Urban Cooling 3.20.2 oficial por script, seca de 2026. A noite recebeu a intensidade regional nas classes 102 e 104; edificações 1031–1033 preservadas. A tabela auxiliar tem 18 códigos. O dia A001 anterior foi reaproveitado, sem nova execução, após comprovar Kc, sombra, albedo e green_area idênticos em todos os 225.297.940 pixels da grade. Os três rasters diurnos e os seis arquivos de mapas diurnos mantêm os hashes anteriores.','',
        'Referência A001 em 153 datas: dia 24,265416609534256 °C e noite 19,714379846732786 °C. UHI 2,8593942060678548 °C, distâncias 450/500 m e ETo preservados. Sem energia, produtividade ou média dia/noite.','',
        *table,'',
        'D500 zero conserva BI zero em 1020/1040. As faixas positivas usam os cortes da 103 e a média disponível de I por superfície/faixa. Os 484.009 pixels com D positivo e altura ausente (435,6081 ha) usam H mediana 6,445500373840332 m para classificar, com flag 9, e não entram na estimação das médias.','',
        'CC noturna = 1 − BI. A intensidade é uma proxy territorial de ocupação/altura; CC positivo em pavimento ou edifício não prova resfriamento ativo. HM pode representar influência recebida da vegetação. Permanecem as limitações de UHI superficial transferido ao ar/à noite, referência urbana A001, ETo uniforme e ausência de calibração térmica empírica.','',
        '## Arquivos','',
        '- `01_Entradas`: tabela e cobertura de 18 códigos, parâmetros imutáveis e raster de qualidade 102/104.',
        '- `02_Dia_Concluido`: cópia das saídas oficiais diurnas anteriores. `03_Noite_Concluido`: nova noite oficial e log nativo.',
        '- `04_Extracao`: CSV/GPKG dos 46.876 fragmentos e diagnóstico completo com LST/classificações; geometrias integrais preservadas.',
        '- `05_Verificacoes`: prova diurna integral, comparação noturna, amostras independentes, hashes e equações do modelo.',
        '- `07_Superficie_sazonal`: composições anteriores preservadas (13 datas secas, 6 chuvosas).',
        '- `08_Zonas_quentes`: polígonos T_air > média + 1 DP por cenário; conectividade 4, área mínima 2 ha.',
        '- `09_Registros_vigentes_anteriores`: cópias dos registros e da planilha anteriores.','',
        'Reprodução: executar `scripts/corrigir_intensidade_noturna.py` a partir do repositório, ajustando os caminhos PREVIOUS/RUN/SCRATCH em um ambiente novo. O produtor recusa sobrescrever a rodada. Executar somente `executar_invest.ps1 -Periodo night` da pasta da rodada e concluir com `scripts/finalizar_correcao_noturna.ps1 -RunRoot PASTA`. A planilha é atualizada por `scripts/atualizar_tabela_biofisica_102_104.mjs` com o runtime de planilhas.','',
        f'Rodada anterior integralmente preservada: `{PREVIOUS.name}`. Fontes INMET/Landsat, ocupação/altura e geometrias não são alteradas.','',
        'Site: branch para PR de aprovação, sem merge ou publicação automática. As classes Ruim/Médio/Bom/Muito bom e as zonas quentes são relativas e exploratórias, sem limiares sanitários ou demonstração de ilha de calor urbano-rural observada.',''])
    (RUN/'LEIA_ME_RESULTADOS.md').write_text(text,encoding='utf-8')
    original_readme=(backup/'LEIA_ME.md').read_text(encoding='utf-8')
    compatibility=original_readme.split('## Preservação e compatibilidade',1)[-1].split('O inventário evita',1)[0]
    (CLIMA/'LEIA_ME.md').write_text(text+'\nMétodo vigente: `02_Metodologia_e_notas_tecnicas/METODOLOGIA_CLIMA_ATUAL.md`. Tabela corrente: `03_Tabelas/Biofisica/tab_biofisica_completa_18classes.csv`; a tabela de 12 classes permanece histórica. A configuração corrente aponta para a cobertura auxiliar dentro da nova rodada.\n\n## Preservação e compatibilidade\n'+compatibility,encoding='utf-8')
    save(RUN/'05_Verificacoes/REGISTRO_VIGENTE.json',{'status':'registrado_sem_merge','run':str(RUN),'previous_run':str(PREVIOUS),'workbook_sha256':digest(workbook),'biophysical_csv_sha256':digest(bio/'tab_biofisica_completa_18classes.csv')})
    print('Correção noturna registrada; dia, fontes e rodada anterior preservados. Git aguarda aprovação em PR.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--planilha',type=Path,required=True)
    register(parser.parse_args().planilha.resolve())
