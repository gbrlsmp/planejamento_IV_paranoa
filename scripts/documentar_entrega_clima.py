"""Índice da base organizada e conferência posterior à reorganização."""
from pathlib import Path
import json,hashlib,shutil,csv

WEB=Path(__file__).resolve().parents[1];BASE=WEB.parent/'02 BASE DE DADOS';C=BASE/'02_Análises/01_Riscos/01_Clima'
R=json.loads((WEB/'dados-modelo/atualizacao-cobertura-clima.json').read_text(encoding='utf8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

index='''# Clima — organização da base e produtos vigentes

Atualização iniciada em 15/11/2026 e concluída em 16/11/2026, horário de Brasília. Projeto Bacia do Paranoá. A identificação da IV mantém 46.876 fragmentos; o InVEST não foi executado nesta atualização.

## Onde encontrar

| Pasta | Conteúdo |
| --- | --- |
| 01_Fontes | INMET 2025/2026, Landsat, Open Buildings e vetores meteorológicos/históricos |
| 02_Metodologia_e_notas_tecnicas | Método climático consolidado e notas das alturas/preenchimento |
| 03_Tabelas/Biofisica | CSV de dez classes, CSV completo de doze classes e XLSX revisado |
| 03_Tabelas/Parametros_climaticos | Tref, contraste UHI e configuração preparada para a futura rodada |
| 03_Tabelas/Series_meteorologicas | Exploração INMET diária e séries da ETo |
| 04_Rasters | Cobertura para InVEST, ETo, ocupação horizontal, alturas e intensidade combinada |
| 05_Analises_exploratorias | QA e resultados da comparação seca/chuva INMET |
| 06_Execucoes_InVEST | Área das execuções, com subpasta Historicas para as rodadas anteriores |
| 07_Mapas_e_figuras | Figuras de consulta e prévias verificadas da tabela |
| 08_Scripts_e_verificacoes | Relatórios de QA, manifesto, mapa da reorganização e cópias dos scripts atuais |
| 09_Historico | Entregas completas das etapas anteriores, scripts antigos e umidade histórica |

## Arquivos atuais

- [Tabela biofísica completa, doze classes](03_Tabelas/Biofisica/tab_biofisica_completa_12classes.csv).
- [Planilha da tabela biofísica](03_Tabelas/Biofisica/tabela_biofisica_atual.xlsx).
- [Tabela diurna, dez classes](03_Tabelas/Biofisica/tab_biofisica_diurna_10classes.csv).
- [Cobertura auxiliar para a tabela completa](04_Rasters/Cobertura_para_InVEST/cobertura_auxiliar_1031_1033_vias104_3m.tif).
- [Classes regionais de intensidade — baixa, média, alta](04_Rasters/Cobertura_para_InVEST/classes_intensidade_regional_500m_3classes_3m.tif).
- [ETo uniforme da A001](04_Rasters/ETo/ETo_A001_media_diaria_seca_2026_uniforme_3m.tif).
- [Configuração preparada](03_Tabelas/Parametros_climaticos/CONFIGURACAO_PREPARADA.json): distâncias da nova rodada ainda a confirmar.
- [Exploração diária INMET](03_Tabelas/Series_meteorologicas/INMET_diario_seca_chuva_2025_2026.csv).
- [Método e notas](02_Metodologia_e_notas_tecnicas/METODOLOGIA_CLIMA_ATUAL.md).
- [Verificação independente](08_Scripts_e_verificacoes/Atualizacao_2026-11-15/VERIFICACAO_INDEPENDENTE.json).

A cobertura de dez classes fica em `02_Análises/03_Ecologia/03_Fitofisionomia/03_Raster/04_Vias_pavimentadas_2026-11-15/uso_cobertura_2026_vias_pavimentadas_3m.tif`, junto do buffer, máscara e relatório das vias. A tabela de áreas fica em `03_Fitofisionomia/02_Tabela/areas_uso_cobertura_vias_2026.csv`.

## Preservação e compatibilidade

As fontes grandes foram agrupadas por movimentação, sem novo download nem duplicação integral. Produtos correntes derivados possuem cópias próprias para separar metadados vigentes do histórico. As entregas antigas permanecem completas, incluindo seus manifests, arquivos intermediários e verificações originais.

Os caminhos antigos continuam acessíveis por junctions locais de compatibilidade; ficam ocultos na navegação comum. Alguns diretórios em uso foram mantidos fisicamente no local e receberam acesso a partir do grupo novo. O mapa exato está em [MAPA_REORGANIZACAO.json](08_Scripts_e_verificacoes/MAPA_REORGANIZACAO.json). Não apagar esses acessos: projetos QGIS e registros anteriores podem utilizá-los. Nenhuma sessão foi encerrada e nenhum WAL/SHM foi removido.

O inventário evita percorrer os caminhos de compatibilidade repetidamente. Os manifests históricos registram o estado de suas entregas; o manifesto desta atualização cobre os novos produtos. Documentos antigos com “proposta”, quatro subclasses ou 1034 descrevem o histórico. O estado atual tem três subclasses 1031–1033 e vias 104.

## Reprodução

Os scripts atuais versionados no repositório são a referência de reprodução. Scripts históricos preservam sua organização original e podem depender dos caminhos registrados na época. Os scripts atuais recebem pastas por argumentos ou têm entradas documentadas; não executar novamente as rotinas de produção sobre destinos já concluídos.

- `integrar_vias_pavimentadas.py`: integra somente 101/102, preserva IV/edificações/máscara e prepara tabelas/cobertura auxiliar.
- `explorar_inmet_seca_chuva.py`: série diária, pares T/UR, perfis horários, tercis e suporte dos gráficos.
- `verificar_preparacao_clima.py`: 400 verificações geométricas independentes e correspondência raster/tabela.
- `produzir_tabela_biofisica.mjs`: XLSX, cálculo dos coeficientes a partir dos componentes médios e renderizações.

Os gráficos comparam períodos observados, sem inferir normal climatológica. BI zero para superfícies não edificadas implica CC noturno inicial 1: limitação documentada. Aceite metodológico e verificações técnicas não constituem calibração local ou validação térmica.
'''
(C/'LEIA_ME.md').write_text(index,encoding='utf8')

with (C/'03_Tabelas/Biofisica/tab_biofisica_completa_12classes.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
assert len(rows)==12
for src in [WEB/'scripts/explorar_inmet_seca_chuva.py',WEB/'scripts/verificar_preparacao_clima.py',WEB/'scripts/produzir_tabela_biofisica.mjs',WEB/'scripts/organizar_base_climatica.ps1',WEB/'scripts/documentar_entrega_clima.py',WEB/'scripts/validar_atualizacao_clima.py',WEB/'scripts/identificacao/integrar_vias_pavimentadas.py']:
    shutil.copy2(src,C/'08_Scripts_e_verificacoes'/src.name)
for name in ['intensidade-500m.png','contraste-superficial.png','eto.png','ocupacao-horizontal.png','altura-regional.png']:
    shutil.copy2(WEB/'imagens/clima'/name,C/'07_Mapas_e_figuras'/name)
for p in [WEB/'docs/nota-qualidade-alturas.md',WEB/'docs/nota-preenchimento-alturas.md']:
    text=p.read_text(encoding='utf8').replace('NOTA_TECNICA_PREENCHIMENTO_RESIDUAL_ALTURAS.md','nota-preenchimento-alturas.md').replace('NOTA_TECNICA_QUALIDADE_ALTURAS_REGIONAIS.md','nota-qualidade-alturas.md');p.write_text(text,encoding='utf8')

hashes=dict(R['source_hashes_sha256'])
meteo=json.loads((WEB/'dados-mapas/clima/inmet-exploracao.json').read_text(encoding='utf8'))
hashes.update({s['path']:s['sha256'] for s in meteo['sources']})
for p,h in hashes.items():assert sha(Path(p))==h,p
mapping=json.loads((C/'08_Scripts_e_verificacoes/MAPA_REORGANIZACAO.json').read_text(encoding='utf-8-sig'))
for m in mapping:assert Path(m['original']).exists() and Path(m['atual']).exists(),m
current=[]
for group in ['02_Metodologia_e_notas_tecnicas','03_Tabelas','04_Rasters/Cobertura_para_InVEST','04_Rasters/ETo','04_Rasters/Ocupacao_horizontal','04_Rasters/Alturas','04_Rasters/Intensidade_combinada','05_Analises_exploratorias','07_Mapas_e_figuras']:
    for p in sorted((C/group).rglob('*')):
        if p.is_file():current.append({'path':str(p.relative_to(C)),'bytes':p.stat().st_size,'sha256':sha(p)})
manifest={'date':'2026-11-16','production_started':'2026-11-15','source_hashes_verified':len(hashes),'organization_paths_verified':len(mapping),'products':current,'invest_executed':False,'iv_preserved':True,'table_classes':12,'source_data_not_uploaded_to_git':True}
(C/'08_Scripts_e_verificacoes/MANIFESTO_ATUALIZACAO.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in manifest.items() if k!='products'},ensure_ascii=False))
