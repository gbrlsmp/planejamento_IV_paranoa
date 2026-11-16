"""Apresentação da produção climática no padrão da Identificação da IV."""
from html import escape
from pathlib import Path
from clima_html import Elements
from metodologia_clima_conteudo import INPUTS,STEPS,NOTES,table,_render_legacy_html

TEMPLATES=Path(__file__).parent/'templates/clima'


def result_table(results):
    rows=[]
    for period,label in [('dia','Dia'),('noite','Noite')]:
        stats={k:v['scenarios'][period]['native_stats'] for k,v in results['indicators'].items()}
        rows.append([label,f"{stats['cc']['mean']:.4f}".replace('.',','),f"{stats['hm']['mean']:.4f}".replace('.',','),f"{stats['t']['mean']:.2f} °C".replace('.',','),f"{stats['t']['min']:.2f} a {stats['t']['max']:.2f} °C".replace('.',',')])
    return table(['Cenário da seca','CC média','HM média','Temperatura média','Temperatura mínima a máxima'],rows,'Estatísticas da bacia nos rasters nativos de 3 m')


def render_results(results):
    h='''<section id="resultados-invest" class="report-section"><h4>Resultados do InVEST na bacia</h4>
<p>As duas rodadas da seca de 2026 estão concluídas. CC descreve a capacidade local de resfriamento; HM inclui a influência das áreas verdes; a temperatura do ar é estimada após a mistura espacial. CC e HM são adimensionais.</p>'''+result_table(results)+'''
<p class="climate-note">As médias usam todos os pixels válidos da bacia. As cores mostram valores contínuos, sem classes de risco. Resultados relativos aos fragmentos serão apresentados na etapa de diagnóstico.</p>
<section class="invest-explorer" data-invest-explorer aria-labelledby="titulo-explorador-invest">
<h5 id="titulo-explorador-invest">Explore os mapas de dia e noite</h5>
<div class="climate-controls">
<label>Indicador<select data-invest-indicator><option value="t">Temperatura estimada do ar</option><option value="cc">Capacidade de resfriamento (CC)</option><option value="hm">Mitigação térmica (HM)</option></select></label>
<label>Cenário da seca<select data-invest-period><option value="dia">Dia</option><option value="noite">Noite</option></select></label>
<label>Escala de cores<select data-invest-scale><option value="common">Comum ao dia e à noite</option><option value="scenario">Ampliar contraste do cenário</option></select></label>
</div>
<div class="invest-actions"><label><input type="checkbox" data-invest-compare> Comparar dia e noite</label><button type="button" data-invest-fit>Enquadrar bacia</button><button type="button" data-invest-retry hidden>Tentar novamente</button></div>
<p class="climate-note" data-invest-scale-note>A escala comum permite comparar os cenários. Para explorar pequenas diferenças dentro de um cenário, escolha ampliar o contraste; confira os limites na legenda.</p>
<div class="invest-map-grid"><section><h6 data-invest-map-title>Dia</h6><div class="invest-map" data-invest-map="dia" role="region" aria-label="Mapa climático principal"></div></section><section data-invest-comparison hidden><h6>Noite</h6><div class="invest-map" data-invest-map="noite" role="region" aria-label="Mapa climático noturno para comparação"></div></section></div>
<div class="invest-legend" data-invest-legend aria-label="Legenda contínua do indicador"></div>
<p class="climate-status" data-invest-status role="status" aria-live="polite">O mapa será carregado ao chegar a esta seção.</p>
<p class="climate-note">Clique no mapa para consultar o valor da célula de visualização. A versão web agrega por média em 20 m, em projeção de visualização; os resultados originais têm grade de 3 m. Esses tamanhos de pixel não representam observação meteorológica nessa resolução.</p>
</section>
<details class="method-details"><summary>Prévias dos seis mapas e dados da execução</summary><div class="method-detail-body"><div class="invest-previews">'''
    for key,indicator in results['indicators'].items():
        for period,label in [('dia','Dia'),('noite','Noite')]:
            r=indicator['scenarios'][period]
            low,high=[str(v).replace('.',',') for v in indicator['range']]
            colors=','.join(indicator['colors'])
            h+=f'<figure><img src="dados-mapas/clima/urban-cooling-2026/{r["preview"]}" alt="{escape(indicator["label"])} na seca de 2026, {label.lower()}, na paleta do relatório" loading="lazy"><figcaption>{escape(indicator["label"])} · {label}.<div class="invest-legend-bar" style="background:linear-gradient(to right,{colors})"></div><div class="invest-legend-labels"><span>{low} {indicator["unit"]}</span><span>{high} {indicator["unit"]}</span></div>Escala comum aos dois cenários.</figcaption></figure>'
    h+='''</div><p><a href="dados-modelo/invest-seca-2026/estatisticas_bacia.csv">Estatísticas da bacia (CSV)</a> · <a href="dados-modelo/invest-seca-2026/configuracao.json">Configuração utilizada</a> · <a href="dados-modelo/invest-seca-2026/verificacoes_bacia.json">Conferências da execução</a> · <a href="dados-mapas/clima/urban-cooling-2026/manifesto.json">Dados e legendas dos mapas</a> · <a href="dados-modelo/invest-seca-2026/LEIA_ME.md">Reprodução e arquivos completos</a>.</p></div></details>
</section>'''
    return h


def render_page(rows,inmet,figures,results):
    notes={n:(title,text) for n,title,text in NOTES}
    assignments=[['01','03'],['02','04'],[],['05'],['06','07','08','09','10','11'],['12']]
    titles=['1. Explorar a meteorologia da seca e da chuva','2. Preparar a temperatura superficial e as referências','3. Calcular a referência do ar para dia e noite','4. Calcular a evapotranspiração de referência','5. Preparar a cobertura, a morfologia e a tabela biofísica','6. Executar e conferir o InVEST Urban Cooling']
    intros=['Compare os dados das quatro estações, sua disponibilidade e as diferenças entre os períodos observados.','As cenas Landsat fundamentam a seleção da referência e o contraste superficial utilizado no modelo.','A temperatura do ar da A045 fornece uma referência para cada cenário da seca.','O cálculo diário FAO56 da A001 fornece a ETo média utilizada no modelo.','A cobertura de 3 m e os parâmetros biofísicos representam as superfícies e a morfologia construída.','Duas rodadas oficiais da seca de 2026 produzem CC, HM e temperatura, com os parâmetros confirmados.']
    bio=Elements(_render_legacy_html(rows)).fragment('tabela-biofisica-clima')
    h='''<section id="clima" aria-labelledby="titulo-clima"><h3 id="titulo-clima">Clima</h3>
<div class="climate-intro"><p>A produção climática reúne observações meteorológicas, temperatura de superfície e características da cobertura para estimar resfriamento e temperatura do ar na Bacia do Paranoá.</p><p>A exploração compara a chuva de <strong>01/10/2025–30/04/2026</strong> e a seca de <strong>01/05–30/09/2026</strong>. O InVEST representa <strong>dia e noite na seca de 2026</strong>.</p></div>
<nav class="section-nav" aria-label="Conteúdo climático"><a href="#dados-entrada-clima">Camadas de entrada</a><a href="#procedimentos-clima">Produção climática</a><a href="#inmet">Exploração INMET</a><a href="#tabela-biofisica-clima">Tabela biofísica</a><a href="#resultados-invest">Mapas do InVEST</a></nav>
<section id="metodologia-clima" class="climate-methodology" aria-label="Metodologia da análise climática">
<section id="dados-entrada-clima" class="report-section"><h4>Camadas de entrada</h4>
<p>As fontes observadas e os produtos derivados têm funções diferentes. A tabela resume sua participação; cada etapa mostra o tratamento e o resultado correspondente.</p>'''
    overview=[
        ['Meteorologia','INMET: A001, A045, A046 e A047.','Exploração seca/chuva; referências do ar e da evapotranspiração.'],
        ['Temperatura de superfície','Landsat 8/9 Collection 2 Level-2.','Comparação das áreas de referência e contraste superficial UHI.'],
        ['Uso e cobertura do solo','Cobertura da pesquisa e vias pavimentadas.','Grade auxiliar de 3 m, com doze classes para o InVEST.'],
        ['Morfologia construída','Implantação das edificações e Open Buildings 2023.','Ocupação, altura e intensidade combinada em janelas de 500 × 500 m.'],
        ['Parâmetros biofísicos','Hu et al.; referências do Cerrado e decisões da pesquisa.','Kc, sombra, albedo, área verde e intensidade construída.'],
        ['Base territorial','Limite da Bacia do Paranoá.','Recorte da modelagem; unidades da IV serão relacionadas no diagnóstico.'],
    ]
    h+=table(['Entrada','Fonte','Produto e finalidade'],overview,'Entradas da produção climática','climate-source-table')
    h+='<details class="method-details"><summary>Consultar todos os tratamentos e a rastreabilidade das entradas</summary>'+table(['Dado de entrada','Fonte','Tratamento','Produto produzido','Finalidade na pesquisa'],INPUTS,'Da fonte ao produto climático','climate-input-table')+'</details></section>'
    h+='<section id="procedimentos-clima" class="method-stage"><h4>Produção da análise climática</h4><nav class="method-stage-nav" aria-label="Etapas da produção climática">'+''.join(f'<a href="#{s["id"]}">Etapa {i+1}</a>' for i,s in enumerate(STEPS))+'</nav>'
    for i,s in enumerate(STEPS):
        h+=f'<article class="method-card" id="{s["id"]}" aria-labelledby="titulo-{s["id"]}"><h5 id="titulo-{s["id"]}">{titles[i]}</h5><p>{intros[i]}</p><details class="method-details"><summary>'+('Ver procedimento completo, gráficos e tabelas' if i==0 else 'Ver procedimento completo e produtos')+'</summary><div class="method-detail-body">'
        if i==0:h+=inmet
        if i==1:h+=figures['landsat']
        if i==2:h+=table(['Cenário','Fonte','Datas pareadas','Tref adotada'],[['Dia','A045','147','25,155903223760365 °C'],['Noite','A045','147','17,810113695827983 °C']],'Referências térmicas do ar para a seca')
        if i==3:h+=figures['eto']
        if i==4:h+='<section id="preparacao-clima"><h6>Cobertura e morfologia construída</h6>'+''.join(figures[k] for k in ('ocupacao','altura','intensidade'))+'</section>'
        h+='<h6>Dados e procedimento</h6>'+''.join('<p>'+escape(p)+'</p>' for p in s['paragraphs'])
        if i==4:h+=bio
        if i==5:h+=table(['Parâmetro','Configuração utilizada'],[['Versão','InVEST Urban Cooling 3.20.2'],['Resfriamento / mistura','450 m / 500 m'],['Dia','factors; sombra 0,60, albedo 0,20, ETI 0,20'],['Noite','intensity; CC = 1 − building_intensity'],['UHI','2,8593942060678548 °C, nos dois cenários'],['Energia / produtividade','Desativadas'],['Conferência','Grade, máscara, equações, integridade e estatísticas integrais']], 'Configuração das execuções diurna e noturna')+'<p><a href="#resultados-invest">Explorar os mapas produzidos</a> · <a href="dados-modelo/invest-seca-2026/LEIA_ME.md">Registros e reprodução da execução</a>.</p>'
        h+='<p class="climate-note">Notas relacionadas: '+' · '.join(f'<a href="#nota-clima-{n}">NM {n}</a>' for n in s['notes'])+'</p>'
        for n in assignments[i]:
            title,text=notes[n]
            h+=f'<details class="climate-procedure climate-decision" id="nota-clima-{n}"><summary>NM {n} · {escape(title)}</summary><div class="climate-procedure-body"><p>{escape(text)}</p></div></details>'
        h+='</div></details></article>\n'
    h+='</section></section>'+render_results(results)
    h+='<details class="report-section" id="notas-metodologicas-clima"><summary>Referências, notas e documentação completa</summary><p>As doze notas estão junto dos procedimentos a que se referem. Consulte também a <a href="docs/metodologia-clima.md">metodologia completa em texto</a>, as notas de <a href="docs/nota-qualidade-alturas.md">qualidade das alturas</a> e <a href="docs/nota-preenchimento-alturas.md">preenchimento residual</a> e as <a href="index.html#referencias-clima">referências utilizadas</a>.</p><p>'+ ' · '.join(f'<a href="#nota-clima-{n}">NM {n}</a>' for n,_,_ in NOTES)+'</p></details>'
    h+='<section class="report-section climate-history">'+(TEMPLATES/'historico.html').read_text(encoding='utf-8')+'</section></section>'
    return h
