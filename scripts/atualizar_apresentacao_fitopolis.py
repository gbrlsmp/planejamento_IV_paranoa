"""Atualiza a apresentação e as regras aprovadas, sem regenerar páginas climáticas."""
from pathlib import Path
import re

WEB=Path(__file__).resolve().parents[1]

def main():
    for name in ['index.html','identificacao.html','diagnostico.html','condicionantes.html','ecologia.html','estrategias.html','mapa.html','aplicacao-invest.html']:
        p=WEB/name;s=p.read_text(encoding='utf8')
        s=s.replace('aria-label="Bacia do Paranoá, sumário do relatório">Bacia do Paranoá</a>','aria-label="Sistema Fitópolis, sumário">Sistema Fitópolis</a>')
        s=s.replace('Relatório metodológico</p>','Bacia do Paranoá · Distrito Federal</p>')
        s=s.replace('| Diagnóstico da Bacia do Paranoá</title>','| Sistema Fitópolis</title>').replace('| Bacia do Paranoá</title>','| Sistema Fitópolis</title>')
        if name=='index.html':
            s=s.replace('Apresentação do Sistema de Infraestrutura Verde da Bacia do Paranoá.','Sistema Fitópolis: infraestrutura verde, diagnóstico territorial e estratégias para a Bacia do Paranoá.')
            s=s.replace('<h2>O Sistema</h2>','<h2>Sistema Fitópolis</h2>',1)
            s=s.replace('O Sistema de Infraestrutura Verde da Bacia do Paranoá reúne áreas que contribuem ou podem contribuir para a conectividade ecológica e a prestação de serviços ecossistêmicos de regulação.','O Sistema Fitópolis reúne a identificação da infraestrutura verde e o diagnóstico territorial da Bacia do Paranoá, no Distrito Federal. Sua leitura articula a vegetação existente e as necessidades das áreas com pouca ou nenhuma vegetação, apoiando estratégias de conservação, recuperação e ampliação da rede.')
            s=s.replace('para cada fragmento de vegetação, informações sobre riscos socioambientais, condicionantes e ecologia.','nos hexágonos territoriais e nos fragmentos de vegetação, informações sobre condições térmicas, inundação, ocupação, contexto social e condicionantes. A matriz será a próxima etapa de integração para orientar as intervenções.')
            for anchor,title in [('como-ler','Como ler o sistema'),('proximas-atualizacoes','Próximas atualizações')]:
                if f'href="#{anchor}"' in s:continue
                s=s.replace('            <li><a href="#referencias">Referências</a></li>',f'            <li><a href="#{anchor}">{title}</a></li>\n            <li><a href="#referencias">Referências</a></li>',1)
                s=s.replace('      <a href="#referencias">Referências</a>',f'      <a href="#{anchor}">{title}</a>\n      <a href="#referencias">Referências</a>',1)
            sections='''
    <section id="como-ler" class="report-section" aria-labelledby="titulo-como-ler">
      <h3 id="titulo-como-ler">Como ler o sistema</h3>
      <p>O percurso reúne identificação da infraestrutura verde, diagnóstico, matriz e intervenções. A identificação reconhece a vegetação, suas fitofisionomias, estrutura e elementos da rede. O diagnóstico examina as condições e os processos do território; a matriz integrará suas combinações para orientar conservação, recuperação e ampliação.</p>
      <h4>Unidades de análise</h4>
      <p>Os <strong>hexágonos de 30 m entre faces opostas</strong> cobrem a bacia inteira, incluindo lugares sem vegetação. Os <strong>46.876 fragmentos</strong> preservam a individualidade da infraestrutura verde existente. As duas leituras se complementam: uma revela necessidades territoriais e a outra permite examinar a participação dos fragmentos.</p>
      <h4>Recortes de visualização e comparação</h4>
      <p>A bacia e as regiões administrativas (RAs) permitem visualizar e comparar essas mesmas unidades. Selecione uma RA, várias RAs ou a bacia inteira nos mapas. O filtro mantém os indicadores integrais das unidades e considera apenas a área inserida no recorte nos resumos; uma RA não recebe uma situação única que apague sua diversidade interna.</p>
      <h4>Valores, cobertura e limites</h4>
      <p>Consulte o valor, o denominador e a cobertura válida de cada indicador. Zero e ausência de estimativa são situações diferentes. Temperatura estimada do ar, temperatura de superfície Landsat, capacidade de resfriamento e mitigação térmica têm significados próprios. Renda é contexto do setor censitário de maior sobreposição, não renda per capita da unidade.</p>
      <p><a href="mapa.html">Explorar o diagnóstico territorial</a> · <a href="docs/metodologia-diagnostico-fitopolis.md">Métodos e limites do diagnóstico</a>.</p>
    </section>
    <section id="proximas-atualizacoes" class="report-section" aria-labelledby="titulo-proximas-atualizacoes">
      <h3 id="titulo-proximas-atualizacoes">Próximas atualizações</h3>
      <p>A identificação da rede, os resultados climáticos atuais e o diagnóstico territorial estão disponíveis. Os indicadores podem ser consultados nos hexágonos e nos fragmentos, com seleção de RAs e registro de cobertura e lacunas.</p>
      <p><strong>Matriz de situações e intervenções — próxima etapa:</strong> integrar os indicadores para reconhecer combinações de problemas e oportunidades e orientar conservação, recuperação e ampliação. Seus critérios, eventuais pesos, cortes e regiões de situação serão definidos na etapa específica; ainda não há resultados de matriz disponíveis.</p>
      <p><strong>Conectividade ecológica — atualização em breve:</strong> avaliar a rede e a contribuição dos fragmentos com cenários de deslocamento, probabilidade de conectividade (PC) e contribuição individual (dPC). Cenários previstos não representam deslocamentos observados nem resultados já calculados.</p>
      <p><strong>Aprimoramento hidrológico — desenvolvimento futuro:</strong> revisar parâmetros de uso e cobertura e incorporar a dinâmica do Lago Paranoá, a operação da barragem e o remanso. Nesta etapa, são mantidos os resultados existentes de inundação e Momentos da Água, com suas versões e limitações documentadas.</p>
      <p>As funcionalidades previstas serão identificadas como disponíveis após implementação e verificação, sem datas de entrega ainda definidas.</p>
    </section>
'''
            if 'id="como-ler"' not in s:s=s.replace('    <section id="referencias"',sections+'\n    <section id="referencias"',1)
            if 'Gabriela Miranda Sampaio Freires, PPG FAU UnB, 2026. Sistema Fitópolis.' not in s:s=s.replace('  </main>','    <p class="note">Gabriela Miranda Sampaio Freires, PPG FAU UnB, 2026. Sistema Fitópolis.</p>\n  </main>',1)
        elif name=='diagnostico.html':
            s=s.replace('O indicador e as extrações apresentados nesta seção pertencem ao diagnóstico anterior. Sua atualização na base atual de 46.876 fragmentos exige revisão das entradas hidrológicas e novos cruzamentos.','São mantidos o cenário hidrológico TR5 e sua cobertura de uso do solo original. As novas extrações usam os 46.876 fragmentos atuais e os hexágonos de 30 m, sem nova simulação hidrológica. As lacunas permanecem sem estimativa.')
            s=s.replace('As extrações disponíveis pertencem ao diagnóstico anterior. A atualização exige cruzar as bases com os fragmentos atuais; identificadores antigos e atuais não são equivalentes.','A leitura atual utiliza os 46.876 fragmentos, identificados por id_frag, e os hexágonos de 30 m. Os identificadores da base histórica não são equivalentes.')
            s=s.replace('Expressa quanto da área do fragmento é ocupado por polígonos de edificações.','Expressa a proporção ocupada pela união das projeções de edificações no fragmento e em seu entorno de 30 m, incluindo o interior e limitada à bacia. Nos hexágonos, mede a ocupação dentro da própria célula.')
            s=s.replace('Recortar edificações no fragmento','Recortar no fragmento + entorno de 30 m, limitado à bacia')
            s=s.replace('Calcula-se 100 × área ocupada / área do fragmento.','Calcula-se 100 × área ocupada / área do domínio: buffer positivo de 30 m do fragmento, incluindo seu interior, intersectado com a bacia. As edificações são unidas para evitar dupla contagem. O filtro de RA não altera esse domínio.')
            s=s.replace('O sistema registra a profundidade média e máxima em cada fragmento e classifica pelo máximo.','O diagnóstico registra área válida, área com profundidade positiva, proporção inundada da área válida, profundidade média na parcela inundada e profundidade máxima. Quando não há parcela inundada, sua profundidade média permanece sem valor; isso é diferente de não haver estimativa.')
            lake='<p>A modelagem representa o escoamento que chega ao Lago Paranoá, mas não simula a variação de seu nível, a operação da barragem e os efeitos de remanso sobre os afluentes. As áreas excluídas permanecem sem estimativa de profundidade e se distinguem das áreas em que o modelo estimou ausência de inundação. A exclusão alcança áreas associadas aos trechos controlados pelo reservatório, além do espelho d’água; também há células sem trecho de drenagem associado.</p>'
            s=s.replace('<h5>Limites</h5><p>A execução não foi calibrada', '<h5>Limites</h5>'+lake+'<p>A execução não foi calibrada',1)
        elif name=='ecologia.html' and 'Atualização em breve.' not in s:
            s=s.replace('<h3 id="ecologia">Ecologia</h3>','<h3 id="ecologia">Ecologia</h3><p class="climate-status-note"><strong>Atualização em breve.</strong> Os cálculos de conectividade não são atualizados nesta etapa. A análise futura avaliará a rede por PC e a contribuição dos fragmentos por dPC, com cenários de 300 m e 1.750 m. Referências de dispersão, habitat e barreiras serão conferidas antes da execução.</p>')
        elif name=='estrategias.html':
            s=s.replace('para agrupar fragmentos em situações semelhantes','para reconhecer combinações nos hexágonos territoriais e nos fragmentos')
            s=s.replace('As propostas serão registradas por situação diagnosticada, com foco em reconectar a rede e mitigar riscos socioambientais.','As propostas serão registradas por situação diagnosticada, orientando conservação, recuperação e ampliação da infraestrutura verde. Critérios de agrupamento e continuidade espacial ainda serão definidos.')
        p.write_text(s,encoding='utf8')

if __name__=='__main__':main()
