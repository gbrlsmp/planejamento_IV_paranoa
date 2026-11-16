"""Publica a metodologia consolidada sem recalcular rasters ou modelos."""
from pathlib import Path
import csv,re
from metodologia_clima_conteudo import render_html,render_markdown

START='<!-- inicio-metodologia-clima -->'
END='<!-- fim-metodologia-clima -->'

def update(web=None):
    web=Path(web) if web else Path(__file__).resolve().parents[1]
    with (web/'dados-modelo/tab_biofisica_completa_12classes.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==12 and len({r['lucode'] for r in rows})==12
    p=web/'diagnostico.html';page=p.read_text(encoding='utf8')
    page=re.sub(r'\s*'+re.escape(START)+'.*?'+re.escape(END)+r'\s*','',page,flags=re.S)
    marker='<section id="inmet"'
    assert page.count(marker)==1
    page=re.sub(r'\s*(?='+re.escape(marker)+')','',page)
    page=page.replace(marker,'\n'+START+'\n'+render_html(rows)+'\n'+END+'\n'+marker,1)
    nav='<a href="#metodologia-clima">Metodologia e InVEST</a><a href="#dados-entrada-clima">Dados de entrada</a><a href="#tabela-biofisica-clima">Tabela biofísica</a><a href="#notas-metodologicas-clima">Notas metodológicas</a><a href="#inmet">Explorar INMET</a><a href="#preparacao-clima">Produtos preparados</a><a href="#resultados-invest">Resultados do InVEST</a>'
    page,n=re.subn(r'(<nav class="section-nav" aria-label="Conteúdo climático">).*?(</nav>)',lambda m:m[1]+nav+m[2],page,flags=re.S);assert n==1
    page=page.replace('clima-exploracao.css?v=1','clima-exploracao.css?v=2').replace('subabas.js?v=1','subabas.js?v=2')
    p.write_text(page,encoding='utf8')
    markdown=render_markdown(rows);(web/'docs/metodologia-clima.md').write_text(markdown,encoding='utf8')
    p=web/'aplicacao-invest.html';page=p.read_text(encoding='utf8')
    link='<p><a href="diagnostico.html#metodologia-clima">Consultar metodologia completa: dados de entrada, tratamentos, finalidade e notas das decisões</a>.</p>'
    if link not in page:page=page.replace('<nav class="section-nav"',link+'<nav class="section-nav"',1)
    page=page.replace('clima-exploracao.css?v=1','clima-exploracao.css?v=2')
    p.write_text(page,encoding='utf8')
    local=web.parent/'02 BASE DE DADOS/02_Análises/01_Riscos/01_Clima/02_Metodologia_e_notas_tecnicas'
    if local.is_dir():(local/'METODOLOGIA_CLIMA_ATUAL.md').write_text(markdown,encoding='utf8')
    print('Metodologia: 11 entradas, 6 procedimentos, tabela de 12 classes, 12 notas metodológicas.')

if __name__=='__main__':update()
