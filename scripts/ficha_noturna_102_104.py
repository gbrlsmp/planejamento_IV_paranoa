"""Atualiza a ficha de aplicação com a mesma tabela vigente da metodologia."""
from clima_html import Elements
from metodologia_clima_conteudo import table

def replace_element(page,element,text):
    return page[:element['start']]+text+page[element['end']:]

def update(page,rows):
    page=page.replace('tab_biofisica_completa_12classes.csv','tab_biofisica_completa_18classes.csv')
    doc=Elements(page);section=doc.by_id('entradas')
    first=min((e for e in doc.elements if e['tag']=='p' and section['start']<e['start']<e['end']<section['end']),key=lambda e:e['start'])
    page=replace_element(page,first,'<p>A cobertura convencional mantém dez classes. A auxiliar de 18 códigos usa 1031–1033 nas edificações, 1020–1023 em impermeável/solo exposto e 1040–1043 nas vias, preservando as demais classes. Grade de 3 m, EPSG:31983, UInt16 e NoData 65535. As subclasses novas mantêm Kc, sombra, albedo e green_area de suas classes de origem; a alteração científica afeta a noite. O resultado diurno A001 foi reaproveitado após prova integral de equivalência desses atributos.</p>')
    doc=Elements(page);section=doc.by_id('tabela-biofisica')
    element=min((e for e in doc.elements if e['tag']=='div' and e['attrs'].get('class')=='table-scroll' and section['start']<e['start']<e['end']<section['end']),key=lambda e:e['start'])
    values=[[r['lucode'],r['classe']]+[r[k].replace('.',',') for k in ('kc','green_area','shade','albedo','building_intensity')] for r in rows]
    page=replace_element(page,element,table(['Código','Classe','Kc','green_area','shade','Albedo','building_intensity'],values,'Parâmetros adotados — 18 classes'))
    values=[]
    for r in rows:
        code=int(r['lucode'])
        if code//10 not in (102,104):continue
        level=code%10
        interval=['D500 = 0','0 < I ≤ 0,25','0,25 < I ≤ 0,50','I > 0,50'][level]
        values.append([r['lucode'],r['classe'],interval,r['building_intensity'].replace('.',',')])
    extra='<section id="intensidade-102-104"><h4>Intensidade do entorno em vias e na classe 102</h4><p>O mesmo índice regional I de ocupação e altura é atribuído às classes 102 e 104. As vias não entram no numerador de ocupação edificada. D500 zero conserva intensidade zero em categoria própria; as outras três faixas mantêm os cortes da 103. O coeficiente de cada nova subclasse é a média do índice com suporte disponível nessa subclasse.</p>'+table(['Código','Superfície e intensidade','Faixa','Coeficiente noturno'],values,'Intensidade regional nas superfícies 102 e 104')+'<p>Em 484.009 pixels de 102/104 com D positivo e altura regional ausente, a classificação usa a mediana de 6,445500373840332 m, mantendo a flag de preenchimento. São 435,6081 ha. Esses pixels não entram na estimação dos coeficientes médios. Não são alturas observadas.</p><p>CC noturna = 1 − intensidade. Um valor alto em uma construção ou pavimento não demonstra produção ativa de resfriamento; HM também pode representar benefício recebido da vegetação próxima. Este índice não mede a capacidade térmica dos materiais.</p><p><a href="dados-modelo/invest-seca-2026/equivalencia_diurna_102_104.json">Conferir fontes, coeficientes, lacunas e equivalência diurna</a>.</p></section>'
    doc=Elements(page)
    try:element=doc.by_id('intensidade-102-104')
    except ValueError:
        section=doc.by_id('intensidade');end=page.rfind('</section>',section['start'],section['end']);page=page[:end]+extra+page[end:]
    else:page=replace_element(page,element,extra)
    return page
