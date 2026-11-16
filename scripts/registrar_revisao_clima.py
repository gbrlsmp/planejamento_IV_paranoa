"""Registra a rodada A001 conferida como vigente; não altera o site remoto."""
import json,shutil
from datetime import datetime
from preparar_revisao_clima import CLIMA,RUN,WEB
from publicar_invest_seca_2026 import save

def main():
    qa=json.loads((RUN/'05_Verificacoes/RESULTADO_EXECUCAO_E_EXTRACAO.json').read_text(encoding='utf-8'))
    assert qa['status']=='executado_extraido_conferido'
    independent=json.loads((RUN/'05_Verificacoes/CONFERENCIA_A001_LANDSAT_INDEPENDENTE.json').read_text(encoding='utf-8'))
    assert 'model_translation' in independent
    tref=json.loads((RUN/'TREF_A001_RESULTADOS.json').read_text(encoding='utf-8'))
    config=json.loads((RUN/'01_Entradas/configuracao_confirmada.json').read_text(encoding='utf-8'))
    current=CLIMA/'03_Tabelas/Parametros_climaticos'
    backup=RUN/'09_Registros_vigentes_anteriores';backup.mkdir(exist_ok=True)
    for name in ('CONFIGURACAO_PREPARADA.json','TREF_RESULTADOS.json','PARAMETROS_CALCULADOS.json'):
        if not (backup/name).exists():shutil.copyfile(current/name,backup/name)
    config.update(status='modelo_A001_dia_noite_seca_executado_extraido_conferido',invest_executed=True,last_completed_run=str(RUN),last_completed_at=datetime.now().astimezone().isoformat(),fragment_count=46876,climate_risk_classification_pending=True,relative_thermal_classification_produced=True,site_change_status='branch_para_PR_sem_merge')
    save(current/'CONFIGURACAO_PREPARADA.json',config)
    reference=dict(tref)
    reference['resumos']=[{'station':'A001','janela':period,'dias_pareados':153,'Tref_media_das_medias_diarias_C':tref['tref'][period]} for period in ('dia','noite')]
    save(current/'TREF_RESULTADOS.json',reference)
    old=json.loads((backup/'PARAMETROS_CALCULADOS.json').read_text(encoding='utf-8'))
    old.update(Tref_dia_C=tref['tref']['dia'],Tref_noite_C=tref['tref']['noite'],estacao_INMET='A001',metodo_INMET=tref['metodo'],escopo='Referências A001 utilizadas em duas rodadas oficiais concluídas e conferidas; publicação proposta em PR, sem merge automático.')
    save(current/'PARAMETROS_CALCULADOS.json',old)
    lines=['# Resultados vigentes — A001, seca de 2026','',
        'InVEST Urban Cooling 3.20.2 oficial por script. Referência operacional urbana A001 — Brasília, 153 datas pareadas de 01/05 a 30/09/2026. Distâncias 450/500 m; UHI 2,8593942060678548 °C; demais entradas preservadas. Energia/produtividade desativadas. Nenhuma média dia/noite.',
        '',f'Tref dia: {config["day"]["t_ref"]} °C. Tref noite: {config["night"]["t_ref"]} °C.','',
        '| Cenário | Mínimo °C | Máximo °C | Média °C |','| --- | ---: | ---: | ---: |']
    for period,label in [('day','Dia'),('night','Noite')]:
        s=qa['scenarios'][period]['full_raster_stats']['t'];lines.append(f'| {label} | {s["min"]:.6f} | {s["max"]:.6f} | {s["mean"]:.6f} |')
    lines+=['','## Arquivos','',
        '- `01_Entradas`: configuração imutável, argumentos oficiais e hashes das fontes.',
        '- `02_Dia_Concluido` / `03_Noite_Concluido`: saídas oficiais, relatórios e logs.',
        '- `04_Extracao`: CSV e GPKG com os 46.876 fragmentos, geometrias preservadas, média/mínimo/máximo/desvio padrão de CC/HM/T em cada cenário. `diagnostico_climatico_completo_46876.gpkg` acrescenta LST seca/chuva, cobertura válida e todas as classes relativas, conferidas contra o CSV completo.',
        '- `05_Verificacoes`: comparação integral, 32 conferências espaciais independentes dos fragmentos, fonte INMET bruta, 128 verificações Landsat nativas e comparação com a rodada A045.',
        '- `07_Superficie_sazonal`: composições Landsat seca/chuva, contagens, fontes e extração por fragmento.',
        '- `08_Zonas_quentes`: polígonos nativos em GPKG e critérios (média + um desvio padrão; conectividade 4; área mínima 2 ha).',
        '- `09_Registros_vigentes_anteriores`: fotografia dos registros derivados antes de atualizar a referência.',
        '', 'As classes Ruim/Médio/Bom/Muito bom são relativas e exploratórias, sem risco sanitário ou calibração local. O CSV web reúne as estatísticas e classes. Os manifestos públicos registram cortes, polígonos e simplificação dos contornos. A imagem de IDs de 20 m pode omitir fragmentos pequenos; todos são consultáveis pela tabela.',
        '', 'A rodada A045 foi preservada integralmente na pasta anterior. A tentativa inicial `07_Tentativa_QA_zero_descartada` não integra a entrega: o produtor foi corrigido para preservar zero válido nas bandas QA e cobrir a interseção dos pixels de 30 m com a bacia. A composição final foi conferida diretamente nas bandas nativas.',
        '', 'A troca de Tref desloca a temperatura absoluta, mantendo CC/HM e aproximadamente a amplitude espacial. UHI superficial diurno aplicado ao ar e à noite, referência urbana A001, ETo uniforme e ausência de calibração permanecem limitações explícitas.',
        '', 'As alterações do site serão entregues em PR para aprovação da pesquisadora, sem merge ou publicação automática.']
    (RUN/'LEIA_ME_RESULTADOS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Rodada A001 vigente registrada; rodada A045 e fontes preservadas. Site remoto não alterado.')

if __name__=='__main__':main()
