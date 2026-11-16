"""Gera a produção climática integrada, sem recalcular o modelo ou outros painéis."""
from pathlib import Path
import csv,json,re
from clima_html import Elements
from metodologia_clima_conteudo import render_html,render_markdown


def update(web=None):
    web=Path(web) if web else Path(__file__).resolve().parents[1]
    template=web/'scripts/templates/clima'
    with (web/'dados-modelo/tab_biofisica_completa_12classes.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==len({r['lucode'] for r in rows})==12
    results=json.loads((web/'dados-mapas/clima/urban-cooling-2026/manifesto.json').read_text(encoding='utf-8'))
    p=web/'diagnostico.html';page=p.read_text(encoding='utf-8');doc=Elements(page)
    untouched={k:doc.fragment(k) for k in ('agua','sociedade')}
    area=doc.by_id('clima')
    content=render_html(rows,(template/'inmet.html').read_text(encoding='utf-8'),json.loads((template/'preparacao.json').read_text(encoding='utf-8')),results)
    page=page[:area['start']]+content+page[area['end']:]
    for file,version in [('clima-exploracao.css',3),('clima-exploracao.js',2),('subabas.js',3)]:
        page=re.sub(re.escape(file)+r'\?v=[^"\s]+',file+f'?v={version}',page)
    if 'invest-raster.js' not in page and 'invest-producao.js' in page:
        page=page.replace('<script src="invest-producao.js', '<script src="invest-raster.js?v=1" defer></script><script src="invest-producao.js',1)
    if 'invest-producao.js' not in page:
        page=page.replace('</head>','<script src="invest-raster.js?v=1" defer></script><script src="invest-producao.js?v=1" defer></script>\n</head>',1)
    for key,value in untouched.items():assert Elements(page).fragment(key)==value, key+' foi alterado'
    p.write_text(page,encoding='utf-8')
    markdown=render_markdown(rows)
    markdown+='\n## Resultados contínuos da bacia\n\nAs duas rodadas oficiais estão concluídas, com 450 m de resfriamento e 500 m de mistura do ar, sem avaliações de energia/produtividade e sem média dia/noite. [Mapas contínuos e estatísticas](../diagnostico.html#resultados-invest), [configuração](../dados-modelo/invest-seca-2026/configuracao.json), [conferências](../dados-modelo/invest-seca-2026/verificacoes_bacia.json) e [registros da execução](../dados-modelo/invest-seca-2026/LEIA_ME.md). Resultados por fragmento e classificação de risco pertencem à etapa de diagnóstico e não são apresentados nesta produção.\n\nA versão web agrega por média em 20 m, EPSG:3857, com codificação UInt16 para consulta. As cores são interpoladas da paleta existente. A escala comum permite comparar cenários; ampliar o contraste usa os limites do cenário e é desativado na comparação lado a lado. As estatísticas tabulares vêm da conferência integral dos rasters nativos de 3 m. A escala de cores não define risco.\n'
    (web/'docs/metodologia-clima.md').write_text(markdown,encoding='utf-8')
    local=web.parent/'02 BASE DE DADOS/02_Análises/01_Riscos/01_Clima/02_Metodologia_e_notas_tecnicas'
    if local.is_dir():(local/'METODOLOGIA_CLIMA_ATUAL.md').write_text(markdown,encoding='utf-8')
    p=web/'aplicacao-invest.html';page=p.read_text(encoding='utf-8')
    page=page.replace('A cobertura e a tabela estão preparadas; as novas execuções de dia e noite ainda não foram realizadas.','As execuções diurna e noturna da seca de 2026 estão concluídas e conferidas, com 450 m de resfriamento e 500 m de mistura do ar. As superfícies contínuas são apresentadas na produção climática; resultados por fragmento ficam para o diagnóstico.')
    page=page.replace('450 m na rodada histórica','450 m').replace('500 m na rodada histórica','500 m').replace('Valor da nova execução ainda a confirmar','Confirmado e utilizado nas duas execuções da seca de 2026')
    page=page.replace('<h3>Entradas preparadas</h3>','<h3>Entradas utilizadas</h3>')
    if 'id="execucao-seca-2026"' not in page:
        record='<section class="report-section" id="execucao-seca-2026"><h3>Execuções concluídas da seca de 2026</h3><p>InVEST 3.20.2 por script: dia (factors) e noite (intensity), com energia e produtividade desativadas. Foram conferidos máscara, grade, equações e integridade das saídas. Não houve calibração térmica local.</p><p><a href="diagnostico.html#resultados-invest">Explorar CC, HM e temperatura na bacia</a> · <a href="dados-modelo/invest-seca-2026/estatisticas_bacia.csv">Estatísticas nativas da bacia (CSV)</a> · <a href="dados-modelo/invest-seca-2026/LEIA_ME.md">Registros e reprodução</a>.</p></section>'
        page=page.replace('<details class="report-section">',record+'<details class="report-section">',1)
    page=re.sub(r'clima-exploracao.css\?v=\d+','clima-exploracao.css?v=3',page)
    p.write_text(page,encoding='utf-8')
    print('Produção climática: seis cartões, INMET na etapa 1, doze notas contextualizadas e seis mapas atuais. Água/Sociedade preservadas.')


if __name__=='__main__':update()
