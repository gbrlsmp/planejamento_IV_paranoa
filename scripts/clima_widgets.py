"""Componentes climáticos compartilhados de produção e diagnóstico."""
from html import escape
from pathlib import Path
import json

WEB=Path(__file__).resolve().parents[1]

def explorer(identifier,lst=False,diagnostic=False):
    folder='superficie-sazonal' if lst else 'urban-cooling-2026'
    name='Temperatura de superfície: seca e chuva' if lst else 'InVEST: dia e noite na seca'
    periods=[('seca','Seca'),('chuva','Chuva')] if lst else [('dia','Dia'),('noite','Noite')]
    indicators=[('lst','Temperatura de superfície')] if lst else [('t','Temperatura estimada do ar'),('cc','Capacidade de resfriamento (CC)'),('hm','Mitigação térmica (HM)')]
    heading='h5' if diagnostic else 'h6'
    h=f'<section class="invest-explorer" data-invest-explorer data-explorer-id="{identifier}" data-folder="dados-mapas/clima/{folder}/" aria-labelledby="titulo-{identifier}"><{heading} id="titulo-{identifier}">{name}</{heading}><div class="climate-controls">'
    if diagnostic:h+='<label>Visualização<select data-invest-view><option value="fragments">Resultado por fragmento</option><option value="source">'+('Composição de superfície' if lst else 'Superfície do InVEST')+'</option></select></label>'
    h+='<label>Indicador<select data-invest-indicator>'+''.join(f'<option value="{key}">{label}</option>' for key,label in indicators)+'</select></label>'
    h+='<label>'+('Período' if lst else 'Cenário da seca')+'<select data-invest-period>'+''.join(f'<option value="{key}">{label}</option>' for key,label in periods)+'</select></label>'
    h+='<label>Representação<select data-invest-mode><option value="continuous">Degradê contínuo</option><option value="classes">Faixas cartográficas</option></select></label>'
    h+='<label>Escala de cores<select data-invest-scale><option value="common">Comum aos dois '+('períodos' if lst else 'cenários')+'</option><option value="scenario">Ampliar contraste do cenário</option></select></label></div>'
    h+='<div class="invest-actions"><label><input type="checkbox" data-invest-compare> Comparar '+('seca e chuva' if lst else 'dia e noite')+'</label>'
    if not lst:h+='<label><input type="checkbox" data-invest-zones> Demarcar zonas relativamente quentes</label>'
    if lst:h+='<label><input type="checkbox" data-invest-references> Mostrar entornos das estações e áreas de referência</label>'
    h+='<button type="button" data-invest-fit>Enquadrar bacia</button><button type="button" data-invest-retry hidden>Tentar novamente</button></div>'
    h+='<p class="climate-note">'+('Landsat observa temperatura de superfície nas passagens diurnas. A comparação usa os mesmos cortes e escala nos dois períodos; consulte a contagem de observações ao clicar.' if lst else 'As cores e os valores representam estimativas do modelo. As faixas avaliam desempenho térmico relativo, sem limiares de risco à saúde.')+'</p>'
    h+=f'<div class="invest-map-layout"><div class="invest-map-grid"><section><h6 data-invest-map-title>{periods[0][1]}</h6><div class="invest-map" data-invest-map="{periods[0][0]}" role="region" aria-label="{name}: mapa principal"></div></section><section data-invest-comparison hidden><h6>{periods[1][1]}</h6><div class="invest-map" data-invest-map="{periods[1][0]}" role="region" aria-label="{name}: comparação"></div></section></div>'
    h+='<aside class="invest-legend" data-invest-legend aria-label="Legenda do indicador"></aside></div><p class="climate-status" data-invest-status role="status" aria-live="polite">O mapa será carregado ao abrir esta seção.</p>'
    if diagnostic:h+='<p class="climate-note">As cores mostram a média de cada fragmento, com consulta de mínimo, máximo, desvio padrão e cobertura válida. A visualização de 20 m pode omitir fragmentos pequenos; a busca e o CSV abrangem todos os 46.876 IDs.</p>'
    h+='<p class="climate-note">Use + e − para aproximar e arraste para navegar. Trocar indicador, cenário ou representação mantém a posição e o zoom. '+('Grade Landsat de 30 m, com resolução térmica efetiva de 100 m; ampliar não acrescenta detalhe observado.' if lst else 'Superfície web por média em 20 m; resultados originais em grade de 3 m, sem observação meteorológica nessa resolução.')+'</p></section>'
    return h

def surface_products():
    p=WEB/'dados-mapas/clima/superficie-sazonal/manifesto.json'
    meta=json.loads(p.read_text(encoding='utf-8'));c=meta['composition']
    h=explorer('superficie-producao',lst=True)
    h+='<p>Composições diurnas: <strong>13 datas na seca</strong> (junho–setembro/2026) e <strong>6 datas na chuva</strong> (outubro/2025–abril/2026). Cada pixel usa apenas suas observações válidas, sem preenchimento. A amostragem não representa todas as horas ou dias dos períodos; maio não tem cena completa na seleção da seca.</p>'
    h+='<p>A composição considera os pixels de 30 m que intersectam a bacia. O tratamento de qualidade exclui ausência, nuvens, sombras, cirros e oclusão do relevo; água permanece incluída. As datas e contagens espaciais podem diferir entre períodos. Uma média maior na composição da chuva não demonstra que toda a estação chuvosa foi mais quente.</p>'
    for period,label in [('seca','Seca'),('chuva','Chuva')]:
        r=c['periods'][period]
        h+=f'<p><strong>{label}:</strong> {r["count_min"]} a {r["count_max"]} observações válidas por pixel. Datas: '+', '.join(r['dates'])+'.</p>'
    h+='<p><a href="dados-modelo/invest-seca-2026/superficie_sazonal.json">Datas, máscaras e hashes das composições</a> · <a href="dados-mapas/clima/superficie-sazonal/manifesto.json">Escalas, cortes e dados de visualização</a>.</p>'
    return h

def diagnosis():
    h='''<section class="report-section" id="diagnostico-clima-atual"><h4>Diagnóstico climático dos fragmentos</h4>
<p>Os 46.876 fragmentos atuais são relacionados às saídas diurna e noturna do InVEST e às composições Landsat de seca e chuva. As médias, mínimos, máximos, desvios padrão populacionais e percentuais válidos são calculados na geometria integral, por id_frag.</p>
<details class="method-details" id="criterios-diagnostico-clima"><summary>Critérios das classes e das zonas de calor</summary><div class="method-detail-body">
<p>Ruim, Médio, Bom e Muito bom descrevem desempenho térmico relativo dos produtos. Os critérios são operacionais e exploratórios; não são limiares sanitários ou classes calibradas com observações locais. A classificação usa a precisão integral; valores e cortes exibidos são arredondados. Consulte o CSV e os metadados para os números completos.</p>
<ul><li><strong>CC e HM:</strong> cortes em 0,25, 0,50 e 0,75; valores maiores recebem melhor classe.</li>
<li><strong>Temperatura do ar:</strong> calcula-se (T − Tref)/UHI separadamente no dia e na noite, com cortes em 0,25, 0,50 e 0,75. Valores menores recebem melhor classe. Os cortes em °C aparecem na legenda de cada cenário; não se comparam temperaturas absolutas usando cortes distintos.</li>
<li><strong>Temperatura de superfície:</strong> cortes nos quartis dos pixels válidos das duas composições reunidas, mantidos iguais na seca e na chuva. Menor temperatura recebe melhor classe. A classificação de cada fragmento usa sua média e esses mesmos cortes.</li>
<li><strong>Limites de classe:</strong> cada corte pertence à faixa de valores superiores. Empates permanecem na mesma faixa; não são forçadas quatro classes ocupadas. CC/HM noturnos da vegetação podem se concentrar em Muito bom por building_intensity igual a zero.</li>
<li><strong>Zonas relativamente quentes:</strong> exclusivamente T_air do InVEST acima da média da bacia mais um desvio padrão populacional, em cada cenário. Polígonos conectados por lados, com área mínima de 2 ha, delimitados na grade nativa de 3 m. O contorno web é simplificado em 9 m. Esses polígonos não demonstram ilha de calor urbano-rural observada nem persistência entre datas.</li></ul>
<p>A extração Landsat usa os valores dos pixels de 30 m sobre os centros da grade dos fragmentos de 3 m, sem acrescentar informação térmica. O percentual válido acompanha os resultados; ausências permanecem sem dados.</p>
<p>As classes do ar usam a escala definida por Tref e UHI; as zonas destacam temperaturas altas em relação à própria bacia. Uma zona relativamente quente pode coincidir com a classe Muito bom. O mapa não força quatro classes ocupadas para ampliar diferenças pequenas.</p>
<p><a href="dados-mapas/clima/diagnostico-2026/manifesto.json">Critérios, contagens de classes e limiares efetivos</a> · <a href="dados-mapas/clima/diagnostico-2026/zonas-quentes-dia.geojson" download>Polígonos diurnos (GeoJSON)</a> · <a href="dados-mapas/clima/diagnostico-2026/zonas-quentes-noite.geojson" download>Polígonos noturnos (GeoJSON)</a>.</p></div></details>'''
    h+=explorer('invest-diagnostico',diagnostic=True)
    h+='<details class="method-details"><summary>Comparar temperatura de superfície por fragmento: seca e chuva</summary><div class="method-detail-body">'+explorer('superficie-diagnostico',lst=True,diagnostic=True)+'</div></details>'
    h+='''<details class="method-details" id="tabela-fragmentos-clima"><summary>Consultar e baixar os 46.876 fragmentos</summary><div class="method-detail-body" data-fragment-table>
<label class="climate-fragment-search">Buscar ID, elemento da IV ou AVU<input type="search" data-fragment-search placeholder="Ex.: 125, florestal ou parque" aria-label="Buscar fragmentos climáticos"></label>
<label class="climate-fragment-search">Localizar o ID no mapa<select data-fragment-target><option value="invest-diagnostico">InVEST: dia e noite na seca</option><option value="superficie-diagnostico">Temperatura de superfície: seca e chuva</option></select></label>
<p class="climate-note">Temperaturas em °C; CC e HM adimensionais; área em hectares. Cada linha representa um fragmento atual. O ID localiza seu contorno no mapa do diagnóstico.</p>
<div class="table-scroll" tabindex="0" role="region" aria-label="Resultados climáticos dos fragmentos"><table class="indicator-table"><thead><tr><th>ID</th><th>Elemento da IV</th><th>Área (ha)</th><th>CC dia</th><th>HM dia</th><th>T dia (°C)</th><th>Classe dia</th><th>T noite (°C)</th><th>Classe noite</th><th>Superfície seca (°C)</th><th>Superfície chuva (°C)</th></tr></thead><tbody></tbody></table></div>
<p data-fragment-table-status role="status" aria-live="polite">Abra esta seção para carregar a consulta.</p><div class="invest-actions"><button type="button" data-fragment-previous disabled>Anterior</button><button type="button" data-fragment-next disabled>Próxima</button><a href="dados-modelo/invest-seca-2026/diagnostico_fragmentos_46876.csv" download>Baixar todos os resultados (CSV)</a></div></div></details></section>'''
    return h
