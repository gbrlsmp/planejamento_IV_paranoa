"""Integra o diagnóstico atual; os mapas históricos ficam identificados à parte."""
from pathlib import Path
import re
WEB=Path(__file__).resolve().parents[1]

def assets(s,viewer=False):
    if 'vendor/leaflet/leaflet.js' not in s:
        s=s.replace('</head>','<link rel="stylesheet" href="vendor/leaflet/leaflet.css"><script defer src="vendor/leaflet/leaflet.js"></script><script defer src="mapa-base.js?v=fitopolis-2026"></script>\n</head>')
    if 'fitopolis-territorio.js' not in s:
        s=re.sub(r'(<script[^>]+src="mapa-base\.js[^"\s]*"[^>]*></script>)',r'\1<script defer src="fitopolis-territorio.js?v=1"></script><link rel="stylesheet" href="fitopolis.css?v=1">',s,count=1)
    if viewer and 'diagnostico-territorial.js' not in s:
        s=s.replace('</head>','<script defer src="fitopolis-dados.js?v=1"></script><script defer src="mapa-camadas.js"></script><script defer src="diagnostico-territorial.js?v=3"></script>\n</head>')
    return s

def widget(field):
    return f'<section class="climate-explorer" data-fitopolis data-indicator="{field}"><p>Carregando a leitura territorial…</p></section>'

def main():
    p=WEB/'mapa.html';old=p.read_text(encoding='utf8')
    historic=old.replace('<h2 id="titulo-atlas">Mapa interativo geral</h2>','<h2 id="titulo-atlas">Mapa histórico · diagnóstico anterior</h2><p class="note">Esta página preserva os indicadores e os 33.454 fragmentos da base histórica. <a href="mapa.html">Consultar o diagnóstico atual do Sistema Fitópolis</a>.</p>')
    historic=historic.replace('      <label class="map-toggle">\n        <input id="mostrar-ras" type="checkbox" checked disabled>\n        Mostrar regiões administrativas (RAs)\n      </label>','      <input id="mostrar-ras" type="checkbox" checked hidden disabled>')
    if not (WEB/'mapa-historico.html').exists():(WEB/'mapa-historico.html').write_text(assets(historic),encoding='utf8')
    header=re.search(r'<header.*?</header>',old,re.S).group()
    page='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Mapa territorial | Sistema Fitópolis</title><link rel="stylesheet" href="style.css?v=fitopolis-2026"><link rel="stylesheet" href="mapa-riscos.css?v=5"><script defer src="mapa-satelite.js?v=2"></script></head><body>'''+header+'''<main class="container map-container"><h2>Diagnóstico territorial</h2><p>Examine as condições da bacia inteira e a infraestrutura verde existente. Escolha hexágonos ou fragmentos, selecione o indicador e use o controle territorial do mapa para comparar uma ou várias RAs.</p><section data-fitopolis></section><section id="comparacao-ras" class="report-section"><h3>Comparar regiões administrativas</h3><p>Selecione as RAs no controle do mapa. As unidades mantêm seus valores integrais; os resumos consideram somente a área inserida na união dos recortes. A comparação preserva as diferenças internas de cada RA, com a mesma legenda. Baixe o CSV da seleção para examinar os valores.</p></section><section class="report-section"><h3>Camadas de origem e identificação</h3><p>O controle “Camada de origem / identificação” permite sobrepor uso e cobertura, Momentos da Água, PRE e elementos da infraestrutura verde. As fontes climáticas estão disponíveis nos <a href="diagnostico.html#producao-indicadores">mapas de produção e diagnóstico</a>. <a href="mapa-historico.html">Consultar mapas e resumos históricos</a>.</p><p><label><input id="mostrar-satelite" type="checkbox" disabled> Mostrar satélite (Sentinel-2)</label></p><p id="satelite-status" role="status"></p><details><summary>Termos da camada de satélite</summary><p>Sentinel-2 cloudless 2025, EOX::Maps, com dados Copernicus Sentinel modificados (2025), sob CC BY-NC-SA 4.0, uso não comercial. Ao ativar, o navegador solicita imagens à EOX. <a href="https://cloudless.eox.at/products/viewing">Condições de uso</a> · <a href="https://eox.at/privacy-policy/">Privacidade</a>.</p></details></section><p><a href="docs/metodologia-diagnostico-fitopolis.md">Métodos, fontes, denominadores e limitações</a></p><p class="note">Gabriela Miranda Sampaio Freires, PPG FAU UnB, 2026. Sistema Fitópolis.</p></main></body></html>'''
    p.write_text(assets(page,True),encoding='utf8')
    for name in ['diagnostico.html','condicionantes.html']:
        p=WEB/name;s=p.read_text(encoding='utf8')
        if name=='diagnostico.html':
            aliases={'inund_max':'inundada_pct_valida','edif_pct':'edif_pct','renda_sm':'renda_sm'}
            pattern=r'<section class="climate-explorer risk-explorer" data-risk-map="(inund_max|edif_pct|renda_sm)".*?</section>'
            s=re.sub(pattern,lambda m:widget(aliases[m.group(1)]),s,flags=re.S)
            # Climate sources remain available; this adds exact current summaries on both units.
            if 'data-indicator="t_dia_mean"' not in s:s=s.replace('<h4 id="titulo-resultados-invest">Resultados do InVEST</h4>','<h4 id="titulo-resultados-invest">Resultados do InVEST</h4><details><summary>Diagnóstico territorial: hexágonos e fragmentos</summary>'+widget('t_dia_mean')+'</details>')
            # Some headings use the section ID without a title ID.
            if 'data-indicator="t_dia_mean"' not in s:
                s=s.replace('<section id="resultados-invest" class="report-section">','<section id="resultados-invest" class="report-section"><details><summary>Diagnóstico territorial: hexágonos e fragmentos</summary>'+widget('t_dia_mean')+'</details>',1)
        else:
            s=s.replace('O cruzamento registra as proporções e as classes predominantes por fragmento.','O cruzamento registra a composição das classes nos hexágonos territoriais e nos fragmentos atuais, com cobertura válida e sobreposições explicitadas. A modelagem de Momentos da Água existente foi mantida, sem nova execução.')
            if 'data-indicator="momentos_pct_fonte"' not in s:s=s.replace('<h3 id="condicionantes">Condicionantes</h3>','<h3 id="condicionantes">Condicionantes</h3><details><summary>Explorar hexágonos e fragmentos</summary>'+widget('momentos_pct_fonte')+'</details>')
        p.write_text(assets(s,True),encoding='utf8')
    for p in WEB.glob('*.html'):
        s=p.read_text(encoding='utf8')
        if 'mapa-base.js' in s:
            s=assets(s)
            s=s.replace('mapa-base.js?v=3','mapa-base.js?v=fitopolis-2026')
            p.write_text(s,encoding='utf8')
    p=WEB/'index.html';s=p.read_text(encoding='utf8').replace('mapa.html#riscos-por-ra','mapa.html#comparacao-ras');p.write_text(s,encoding='utf8')

if __name__=='__main__':main()
