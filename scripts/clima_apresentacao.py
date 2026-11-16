"""Produção climática em quatro etapas e diagnóstico atual, no padrão da IV."""
from html import escape
from pathlib import Path
import json
from clima_html import Elements
from metodologia_clima_conteudo import INPUTS,STEPS,NOTES,table,_render_legacy_html
from clima_widgets import explorer
TEMPLATES=Path(__file__).parent/'templates/clima'


def render_inputs():
    overview=[
        ['Meteorologia','INMET: A001, A045, A046 e A047.','Exploração seca/chuva; A001 fornece referências do ar e evapotranspiração.'],
        ['Temperatura de superfície','Landsat 8/9 Collection 2 Level-2.','Composições seca/chuva, comparação das referências e contraste UHI.'],
        ['Uso e cobertura do solo','Cobertura da pesquisa e vias pavimentadas.','Grade auxiliar de 3 m com doze classes para o InVEST.'],
        ['Morfologia construída','Implantação das edificações e Open Buildings 2023.','Ocupação, altura e intensidade em janelas de 500 × 500 m.'],
        ['Parâmetros biofísicos','Hu et al.; referências do Cerrado e decisões da pesquisa.','Kc, sombra, albedo, área verde e intensidade construída.'],
        ['Base territorial','Bacia do Paranoá e fragmentos atuais de IV.','Recorte da modelagem e unidades do diagnóstico.'],
    ]
    return '<section id="dados-entrada-clima" class="report-section"><h4>Camadas de entrada</h4><p>As fontes observadas e os produtos derivados têm funções diferentes. Cada etapa mostra o tratamento e os resultados correspondentes.</p>'+table(['Entrada','Fonte','Produto e finalidade'],overview,'Entradas da produção climática','climate-source-table')+'<details class="method-details"><summary>Consultar tratamentos e rastreabilidade das entradas</summary>'+table(['Dado de entrada','Fonte','Tratamento','Produto produzido','Finalidade na pesquisa'],INPUTS,'Da fonte ao produto climático','climate-input-table')+'</details></section>'


def render_results(results):
    h='<section id="resultados-invest" class="report-section"><h6>Resultados do InVEST na bacia</h6><p>CC representa a capacidade local de resfriamento; HM considera a influência das áreas verdes; a temperatura do ar é estimada após a mistura espacial. CC e HM são adimensionais. As duas rodadas da seca utilizam a referência A001.</p>'+result_table(results)
    h+='<p class="climate-note">Estatísticas de todos os pixels válidos dos rasters nativos de 3 m. Resultados por fragmento são apresentados no diagnóstico abaixo.</p>'+explorer('invest-producao')
    h+='<details class="method-details"><summary>Prévias dos seis mapas e dados da execução</summary><div class="method-detail-body"><div class="invest-previews">'
    for key,indicator in results['indicators'].items():
        for period,label in [('dia','Dia'),('noite','Noite')]:
            record=indicator['scenarios'][period]
            low,high=[str(v).replace('.',',') for v in indicator['range']]
            colors=','.join(indicator['colors'])
            h+=f'<figure><img src="dados-mapas/clima/urban-cooling-2026/{record["preview"]}" alt="{escape(indicator["label"])} — {label.lower()} na seca, referência A001" loading="lazy"><figcaption>{escape(indicator["label"])} · {label}.<div class="invest-legend-bar" style="background:linear-gradient(to right,{colors})"></div><div class="invest-legend-labels"><span>{low} {indicator["unit"]}</span><span>{high} {indicator["unit"]}</span></div>Escala comum aos dois cenários.</figcaption></figure>'
    return h+'</div><p><a href="dados-modelo/invest-seca-2026/estatisticas_bacia.csv">Estatísticas da bacia (CSV)</a> · <a href="dados-modelo/invest-seca-2026/configuracao.json">Configuração</a> · <a href="dados-modelo/invest-seca-2026/verificacoes_bacia.json">Conferências</a> · <a href="dados-mapas/clima/urban-cooling-2026/manifesto.json">Dados e legendas</a> · <a href="dados-modelo/invest-seca-2026/LEIA_ME.md">Reprodução</a>.</p></div></details></section>'


def result_table(results):
    rows=[]
    for period,label in [('dia','Dia'),('noite','Noite')]:
        stats={k:v['scenarios'][period]['native_stats'] for k,v in results['indicators'].items()}
        rows.append([label,f"{stats['cc']['mean']:.4f}".replace('.',','),f"{stats['hm']['mean']:.4f}".replace('.',','),f"{stats['t']['mean']:.2f} °C".replace('.',','),f"{stats['t']['min']:.2f} a {stats['t']['max']:.2f} °C".replace('.',',')])
    return table(['Cenário da seca','CC média','HM média','Temperatura média','Temperatura mínima a máxima'],rows,'Estatísticas da bacia nos rasters nativos de 3 m')


def render_page(rows,inmet,figures,results):
    from clima_widgets import surface_products,diagnosis
    # Reaproveita as tabelas de entradas e de parâmetros sem duplicar conteúdo.
    inputs=render_inputs()
    bio=Elements(_render_legacy_html(rows)).fragment('tabela-biofisica-clima')
    config=json.loads((Path(__file__).resolve().parents[1]/'dados-modelo/invest-seca-2026/configuracao.json').read_text(encoding='utf-8'))
    notes={n:(title,text) for n,title,text in NOTES}
    groups=[
        ('clima-metodo-inmet','1. Explorar a meteorologia e calcular a ETo',[0,3],['01','03','05'],'Compare seca e chuva nas quatro estações e consulte o cálculo da evapotranspiração de referência da A001.'),
        ('clima-metodo-landsat','2. Preparar a temperatura de superfície e as referências do ar',[1,2],['02','04'],'Compare as composições Landsat de seca e chuva e conheça as referências diurna e noturna do ar da A001.'),
        ('clima-metodo-morfologia','3. Preparar a cobertura e os parâmetros biofísicos',[4],['06','07','08','09','10','11'],'A cobertura de 3 m e a morfologia construída fornecem os atributos das doze classes do InVEST.'),
        ('clima-metodo-modelo','4. Aplicar o InVEST e conferir os resultados',[5],['12'],'As rodadas oficiais de dia e noite na seca produzem capacidade de resfriamento, mitigação e temperatura estimada do ar.'),
    ]
    h='''<section id="clima" aria-labelledby="titulo-clima"><h3 id="titulo-clima">Clima</h3>
<div class="climate-intro"><p>A produção climática combina meteorologia, temperatura de superfície e cobertura do solo para estimar o resfriamento na Bacia do Paranoá. O diagnóstico relaciona esses produtos aos fragmentos da infraestrutura verde.</p><p>A exploração e os mapas Landsat comparam a chuva de <strong>01/10/2025–30/04/2026</strong> e a seca de <strong>01/05–30/09/2026</strong>. O InVEST representa <strong>dia e noite na seca de 2026</strong>, com referências do ar da <strong>A001 — Brasília</strong>.</p></div>
<nav class="section-nav" aria-label="Conteúdo climático"><a href="#dados-entrada-clima">Camadas de entrada</a><a href="#clima-metodo-inmet">Meteorologia e ETo</a><a href="#clima-metodo-landsat">Referências térmicas</a><a href="#clima-metodo-morfologia">Cobertura e parâmetros</a><a href="#clima-metodo-modelo">InVEST e resultados</a><a href="#diagnostico-clima-atual">Diagnóstico dos fragmentos</a></nav>
<section id="metodologia-clima" class="climate-methodology" aria-label="Metodologia da análise climática">'''+inputs
    h+='<section id="procedimentos-clima" class="method-stage"><h4>Produção da análise climática</h4><nav class="method-stage-nav" aria-label="Etapas da produção climática">'+''.join(f'<a href="#{g[0]}">Etapa {i+1}</a>' for i,g in enumerate(groups))+'</nav>'
    for identifier,title,steps,assigned,intro in groups:
        h+=f'<article class="method-card" id="{identifier}" aria-labelledby="titulo-{identifier}"><h5 id="titulo-{identifier}">{title}</h5><p>{intro}</p><details class="method-details"><summary>Ver procedimento completo, dados e produtos</summary><div class="method-detail-body">'
        for step in steps:
            s=STEPS[step]
            subid=f' id="{s["id"]}"' if s['id']!=identifier else ''
            h+=f'<section{subid}><h6>'+escape(s['title'].split('. ',1)[1])+'</h6>'
            if step==0:h+=inmet
            if step==1:h+=surface_products()+figures['landsat']
            if step==2:h+=table(['Cenário','Fonte','Datas pareadas','Tref adotada'],[[label,'A001 — Brasília',str(config['reference_days']),f"{config[key]['t_ref']:.4f} °C".replace('.',',')] for key,label in [('day','Dia'),('night','Noite')]],'Referências do ar na seca — média das médias diárias por janela')+'<p><a href="dados-modelo/invest-seca-2026/tref_a001.json">Datas, critérios e fonte INMET</a> · <a href="dados-modelo/invest-seca-2026/tref_a001_medias_diarias.csv">Médias diurnas e noturnas por data (CSV)</a>.</p>'
            if step==3:h+=figures['eto']
            if step==4:h+='<section id="preparacao-clima">'+''.join(figures[k] for k in ('ocupacao','altura','intensidade'))+'</section>'
            h+=''.join('<p>'+escape(p)+'</p>' for p in s['paragraphs'])
            if step==4:h+=bio
            if step==5:
                h+=table(['Parâmetro','Configuração utilizada'],[['Versão','InVEST Urban Cooling 3.20.2'],['Referência do ar','A001 — Brasília; 153 datas pareadas da seca'],['Resfriamento / mistura','450 m / 500 m'],['Dia','factors; sombra 0,60, albedo 0,20, ETI 0,20'],['Noite','intensity; CC = 1 − building_intensity'],['UHI','2,8593942060678548 °C nos dois cenários'],['Energia / produtividade','Desativadas'],['Conferência','Máscara, grade, equações, integridade e estatísticas nativas']], 'Configuração das rodadas atuais')+render_results(results)
            h+='</section>'
        for n in assigned:
            nt,text=notes[n]
            h+=f'<details class="climate-procedure climate-decision" id="nota-clima-{n}"><summary>NM {n} · {escape(nt)}</summary><div class="climate-procedure-body"><p>{escape(text)}</p></div></details>'
        h+='</div></details></article>'
    h+='</section></section>'+diagnosis()
    h+='<details class="report-section" id="notas-metodologicas-clima"><summary>Referências, notas e documentação completa</summary><p>As doze notas acompanham as etapas correspondentes. Consulte a <a href="docs/metodologia-clima.md">metodologia completa</a>, as notas de <a href="docs/nota-qualidade-alturas.md">qualidade das alturas</a> e <a href="docs/nota-preenchimento-alturas.md">preenchimento residual</a> e as <a href="index.html#referencias-clima">referências utilizadas</a>.</p><p>'+' · '.join(f'<a href="#nota-clima-{n}">NM {n}</a>' for n,_,_ in NOTES)+'</p></details>'
    return h+'<section class="report-section climate-history">'+(TEMPLATES/'historico.html').read_text(encoding='utf-8')+'</section></section>'
