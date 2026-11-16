"""Gera a produção climática integrada, sem recalcular o modelo ou outros painéis."""
from pathlib import Path
import csv,json,re
from clima_html import Elements
from metodologia_clima_conteudo import render_html,render_markdown


def update(web=None):
    web=Path(web) if web else Path(__file__).resolve().parents[1]
    template=web/'scripts/templates/clima'
    with (web/'dados-modelo/tab_biofisica_completa_18classes.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==len({r['lucode'] for r in rows})==18
    results=json.loads((web/'dados-mapas/clima/urban-cooling-2026/manifesto.json').read_text(encoding='utf-8'))
    p=web/'diagnostico.html';page=p.read_text(encoding='utf-8');doc=Elements(page)
    untouched={k:doc.fragment(k) for k in ('agua','sociedade')}
    area=doc.by_id('clima')
    content=render_html(rows,(template/'inmet.html').read_text(encoding='utf-8'),json.loads((template/'preparacao.json').read_text(encoding='utf-8')),results)
    page=page[:area['start']]+content+page[area['end']:]
    for file,version in [('clima-exploracao.css',4),('clima-exploracao.js',2),('subabas.js',3),('invest-raster.js',2),('invest-producao.js',3)]:
        page=re.sub(re.escape(file)+r'\?v=[^"\s]+',file+f'?v={version}',page)
    if 'invest-raster.js' not in page and 'invest-producao.js' in page:
        page=page.replace('<script src="invest-producao.js', '<script src="invest-raster.js?v=1" defer></script><script src="invest-producao.js',1)
    if 'invest-producao.js' not in page:
        page=page.replace('</head>','<script src="invest-raster.js?v=1" defer></script><script src="invest-producao.js?v=1" defer></script>\n</head>',1)
    if 'clima-fragmentos.js' not in page:
        page=page.replace('<script src="invest-producao.js', '<script src="clima-fragmentos.js?v=1" defer></script><script src="invest-producao.js',1)
    for key,value in untouched.items():assert Elements(page).fragment(key)==value, key+' foi alterado'
    p.write_text(page,encoding='utf-8')
    markdown=render_markdown(rows)
    markdown+='\n## Resultados contínuos da bacia\n\nAs duas rodadas oficiais estão concluídas, com 450 m de resfriamento e 500 m de mistura do ar, sem avaliações de energia/produtividade e sem média dia/noite. [Mapas contínuos e estatísticas](../diagnostico.html#resultados-invest), [configuração](../dados-modelo/invest-seca-2026/configuracao.json), [conferências](../dados-modelo/invest-seca-2026/verificacoes_bacia.json) e [registros da execução](../dados-modelo/invest-seca-2026/LEIA_ME.md). Resultados por fragmento e classificação de risco pertencem à etapa de diagnóstico e não são apresentados nesta produção.\n\nA versão web agrega por média em 20 m, EPSG:3857, com codificação UInt16 para consulta. As cores são interpoladas da paleta existente. A escala comum permite comparar cenários; ampliar o contraste usa os limites do cenário e é desativado na comparação lado a lado. As estatísticas tabulares vêm da conferência integral dos rasters nativos de 3 m. A escala de cores não define risco.\n'
    markdown=markdown.replace('Resultados por fragmento e classificação de risco pertencem à etapa de diagnóstico e não são apresentados nesta produção.', 'Os resultados por fragmento e as classes térmicas relativas são apresentados na seção de diagnóstico atual; não constituem classificação de risco sanitário.')
    markdown+='\n## Comparação Landsat seca/chuva e diagnóstico atual\n\nComposições diurnas de 13 datas da seca e 6 da chuva, com média por pixel disponível, sem preenchimento, máscara QA básica e contagem de observações. Grade de 30 m (térmico efetivo de 100 m), pixels que intersectam a bacia. As datas não representam todas as horas ou dias dos períodos. A extração nos fragmentos usa os valores desses pixels sobre os centros da grade geométrica de 3 m, sem criar informação térmica. O percentual válido é informado.\n\nClasses relativas Ruim, Médio, Bom e Muito bom: CC/HM com cortes 0,25/0,50/0,75, maiores valores melhores; temperatura do ar pelo excesso normalizado (T−Tref)/UHI, cortes 0,25/0,50/0,75, menores valores melhores; LST pelos quartis dos pixels válidos das duas composições reunidas, mesmos cortes na seca e chuva. Cada corte pertence à faixa superior de valores. Empates não são separados e não se forçam classes ocupadas. Não são limiares de saúde ou calibração local.\n\nZonas relativamente quentes: exclusivamente saídas T_air do InVEST acima da média da bacia mais um desvio padrão populacional em cada cenário, conectividade 4 e área mínima de 2 ha na grade nativa de 3 m. Contornos web simplificados em 9 m; GPKG local preserva os polígonos nativos. Critério operacional exploratório; não demonstra ilha de calor urbano-rural observada ou persistência entre datas.\n\nO [diagnóstico dos fragmentos](../diagnostico.html#diagnostico-clima-atual) permite consultar os 46.876 IDs, mapas, classes e estatísticas. A imagem de IDs de 20 m pode omitir fragmentos pequenos; tabela e busca cobrem todos. Contornos individuais web são simplificados em 3 m; geometrias integrais permanecem nos GPKGs locais. [CSV completo](../dados-modelo/invest-seca-2026/diagnostico_fragmentos_46876.csv), [critérios e limiares](../dados-mapas/clima/diagnostico-2026/manifesto.json), [Tref A001](../dados-modelo/invest-seca-2026/tref_a001.json) e [Landsat](../dados-modelo/invest-seca-2026/superficie_sazonal.json).\n'
    markdown+='\n## Revisão noturna das superfícies 102 e 104\n\nA intensidade regional passa a 1020–1023 e 1040–1043. D500 zero mantém BI zero em subclasse própria. Os coeficientes positivos são médias do índice com suporte disponível em cada nova subclasse, com os cortes da 103. A tabela atual tem 18 códigos. Os 484.009 pixels com D positivo e altura ausente usam a mediana regional somente para a classificação, com flag 9, sem participar da estimação das médias. O índice representa o entorno construído, não o armazenamento térmico medido dos materiais.\n\nA noite foi executada novamente com o InVEST oficial. O dia A001 anterior foi reaproveitado: Kc, sombra, albedo e green_area são idênticos em todos os 225.297.940 pixels da grade. Os três rasters nativos e os seis arquivos de mapas diurnos mantêm seus hashes. Não se alega nova execução diurna. [Prova integral, coeficientes e lacunas](../dados-modelo/invest-seca-2026/equivalencia_diurna_102_104.json).\n'
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
    page=re.sub(r'clima-exploracao.css\?v=\d+','clima-exploracao.css?v=4',page)
    p.write_text(page,encoding='utf-8')
    page=page.replace('25,155903223760365','24,265416609534256').replace('17,810113695827983','19,714379846732786')
    page=page.replace('25,1559','24,2654').replace('17,8101','19,7144')
    page=page.replace('147 datas','153 datas').replace('147 dias','153 dias')
    page=page.replace('A045 — Águas Emendadas','A001 — Brasília').replace('A045 fornece Tref','A001 fornece Tref')
    page=page.replace('Temperatura do ar A045','Temperatura do ar A001 — Brasília').replace('Mesmas datas da A045','Mesmas 153 datas da A001')
    page=page.replace('A seleção da A045 utilizou a comparação superficial dos entornos das estações, mas Tref foi calculada com temperatura do ar.', 'A referência atual utiliza médias diurna e noturna do ar da A001 — Brasília em 153 datas pareadas da seca. É uma referência operacional urbana, sem equivalência demonstrada ao ar rural. A comparação superficial das estações permanece como exploração independente.')
    from ficha_noturna_102_104 import update as update_night_sheet
    page=update_night_sheet(page,rows)
    p.write_text(page,encoding='utf-8')
    print('Clima: quatro etapas, A001, comparação Landsat e diagnóstico atual; Água/Sociedade preservadas.')


if __name__=='__main__':update()
