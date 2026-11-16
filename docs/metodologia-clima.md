# Metodologia climática da Bacia do Paranoá

A pesquisa utilizou o InVEST Urban Cooling 3.20.2 na seca de 2026, com factors para o dia e intensity para a noite. Objetivo: estimar capacidade de resfriamento (CC), mitigação térmica (HM) e temperatura do ar, para posterior análise na base atual de 46.876 fragmentos. As duas execuções e a conferência técnica estão concluídas. Os mapas contínuos da bacia são apresentados na produção climática; resultados por fragmento e classificação de risco ficam para a etapa de diagnóstico.

## Dados de entrada e finalidade

| Dado de entrada | Fonte | Tratamento | Produto | Finalidade |
| --- | --- | --- | --- | --- |
| Limite da bacia e fragmentos de IV | Base territorial local atribuída ao IPE-DF (2023) e identificação da IV da pesquisa. | Compatibilização espacial; manutenção de 46.876 fragmentos, chave id_frag, e conferência da máscara de vegetação. | Área de estudo e unidades de análise. | Delimitar a aplicação e, após o modelo, relacionar as saídas à rede de IV. |
| Uso e cobertura do solo | PlanetScope de 17/01 e 30/07/2026; MapBiomas, ZEE-DF e vetores descritos na identificação. | Classificação proxy por NDVI e refinamentos territoriais em grade de 3 m, EPSG:31983; dez classes na cobertura final. | Raster de cobertura com edificações 103 e vias 104. | Localizar as superfícies às quais serão atribuídos os parâmetros biofísicos. |
| Vias pavimentadas | Camada local Vias_OSM_Bacia_Paranoa.shp, campo pavimentad. | Seleção SIM; buffer de 2,5 m por lado das linhas, rasterização pelos centros; somente pixels 101/102 recebem 104. A fonte reúne eixos e margens. | Classe 104 — Vias pavimentadas; buffer e máscara de apoio. | Distinguir o pavimento da mistura impermeável/solo exposto, preservando as classes de IV. |
| Meteorologia horária | INMET: A001 Brasília, A045 Águas Emendadas, A046 Gama e A047 Paranoá; arquivos 2025/2026. | UTC convertido para UTC−03; triagem por variável, ausência preservada. Médias, distribuições e perfis por período. Critérios específicos para exploração, Tref e ETo. | Séries e gráficos seca/chuva; dados para ETo e Tref. | Caracterizar os períodos e fornecer as observações meteorológicas usadas nas entradas do modelo. |
| Temperatura de superfície e qualidade | Landsat 8/9 Collection 2 Level-2 Surface Temperature, USGS, obtido pelo Planetary Computer. | ST_B10 com escala/offset e conversão para °C; máscaras QA_PIXEL e QA_RADSAT. Médias nas seis áreas e em 13 datas completas da seca. | Comparações superficiais, médias por data e contraste entre referências. | Apoiar a seleção da estação de referência e construir a aproximação de UHI. Não é temperatura do ar. |
| Evapotranspiração de referência — ETo | Meteorologia da A001; método FAO56 de Allen et al. (1998). | Penman–Monteith calculado por dia; vento nominal de 10 m convertido a 2 m; média de 152 dias aceitos. | ETo média de 3,948045309995122 mm/dia em raster uniforme. | Fornecer a demanda evaporativa de referência para calcular ETI com o Kc de cada cobertura. |
| Temperaturas de referência — Tref | Temperatura do ar A045; estação selecionada pelo critério superficial Landsat. | Janelas solares NOAA; mínimo de 20 leituras/dia e 80% por janela; mesmas 147 datas elegíveis para dia e noite. | Tref dia 25,155903223760365 °C; noite 17,810113695827983 °C. | Fixar a referência térmica de cada cenário do Urban Cooling. |
| Contraste UHI | Landsat: Vicente Pires e Estação Ecológica da UnB. | Diferença das médias espaciais na mesma data; média dos 13 contrastes, com pesos temporais iguais. | Parâmetro UHI de 2,8593942060678548 °C. | Fornecer a amplitude usada na conversão do índice HM em temperatura, sob as aproximações declaradas. |
| Implantação e altura das construções | Classe 103; SHP local de construções; Google Open Buildings 2.5D, ano 2023. | Altura >0 e ≤100 m, confiança de presença ≥0,50; mediana por construção na grade e amostra direta válida como alternativa; ausências preservadas. | Raster de altura individual disponível e origem/qualidade das atribuições. | Fornecer a componente vertical da morfologia construída. A temporalidade específica do SHP não foi comprovada. |
| Ocupação horizontal e altura regional | Classe 103 e alturas individuais aproveitáveis. | Janelas móveis exatas de 500 × 500 m: implantação/área terrestre e altura média ponderada pela área edificada com altura. | D500, H500 e cobertura de alturas por janela. | Descrever o entorno construído nas dimensões horizontal e vertical, com suporte espacial comum. |
| Tabela biofísica e cobertura auxiliar | Hu, Wang e Li (2023), Ribeiro e Walter (2008), manual InVEST e decisões da pesquisa. | Transferência de parâmetros e adaptações por classe; média 50/50 de D e V; três subclasses de edificações; correspondência integral dos códigos. | CSV com doze classes e cobertura auxiliar 1031–1033/104. | Traduzir a cobertura em parâmetros de resfriamento diurno e intensidade construída noturna. |

## Procedimentos

### 1. Caracterizar os períodos e conferir a meteorologia

A exploração compara 01/10/2025–30/04/2026 (212 dias) e 01/05–30/09/2026 (153 dias), nas quatro estações. A comparação com a chuva caracteriza os dados disponíveis; as entradas utilizadas no InVEST representam a seca de 2026.

Os horários são convertidos para UTC−03 antes de agrupar. Temperatura pontual, umidade, orvalho e vento seguem o timestamp local. Precipitação, máximas/mínimas e radiação referentes à hora anterior são atribuídas ao respectivo intervalo; o tratamento concreto depende do produto calculado.

Na exploração, médias diárias de temperatura, umidade e vento exigem pelo menos 20 leituras válidas. Chuva diária exige 24 intervalos válidos. Dispersão e Sankey exigem pelo menos 20 pares T/UR do mesmo dia, calculando as duas médias sobre as mesmas horas. Dados ausentes não são substituídos por zero.

Os boxplots resumem a distribuição entre dias; o perfil horário mostra média e quartis das leituras de cada hora. O Sankey conta dias em combinações de faixas de temperatura e umidade: os cortes são tercis dos dois períodos reunidos por estação, mantidos iguais entre os períodos daquela estação. Mostram-se contagens e percentuais dos dias pareados válidos; não são transições temporais, causalidade ou limiares de risco.

Notas relacionadas: NM 01, NM 03.

### 2. Preparar a temperatura superficial e selecionar as referências

O inventário contém 38 cenas Landsat, sendo 24 secas e 14 chuvosas; 19 têm cobertura completa no recorte considerado, das quais 13 são da seca. O filtro de nuvens de cena foi <5% na seca e <15% na chuva. A seleção térmica principal usa somente as 13 datas completas da seca, observadas de junho a setembro; não se preenche maio.

A temperatura superficial é calculada por ST_B10 × 0,00341802 + 149 − 273,15, em °C, após aplicar a máscara básica: banda válida, exclusão dos bits 0–5 de QA_PIXEL e da oclusão de relevo, bit 11 de QA_RADSAT. A água permanece incluída. ST_QA é conservada para diagnóstico, sem corte adicional de magnitude no resultado principal.

Comparam-se os entornos padronizados de 500 m das estações A001/A045/A046/A047 e as duas áreas de referência. Calcula-se primeiro a média espacial de cada área/data e depois a média das datas com pesos iguais. A045 apresentou a menor média superficial entre as quatro estações e foi selecionada para obter Tref a partir do seu registro de temperatura do ar.

O UHI adotado é a média dos contrastes emparelhados Vicente Pires menos Estação Ecológica da UnB: 2,8593942060678548 °C. Esse contraste é superficial, diurno e específico das áreas/datas observadas; sua utilização como parâmetro do modelo de ar e sua transferência para a noite são aproximações explícitas.

Notas relacionadas: NM 02, NM 04.

### 3. Calcular a referência do ar para dia e noite

As janelas são delimitadas por nascer e pôr do sol teóricos, calculados pelas equações NOAA. Dia inclui o nascer e exclui o pôr; noite reúne os horários anteriores ao nascer e posteriores ao pôr na mesma data civil local. Não se trata de uma noite contínua atravessando duas datas.

O critério exige ≥20 leituras válidas no dia e ≥80% das leituras esperadas em cada janela, com o mínimo arredondado para cima. A média principal usa as mesmas 147 datas com ambas as janelas elegíveis. Nesse conjunto específico, as janelas também são completas.

Calcula-se a média de cada janela em cada dia; depois, a média das médias diárias com pesos iguais. Obtêm-se 25,155903223760365 °C para o dia e 17,810113695827983 °C para a noite. A045 é fonte de Tref; A001 é fonte de ETo.

Notas relacionadas: NM 03, NM 04.

### 4. Calcular a ETo diária e produzir o raster de referência

Aplica-se FAO Penman–Monteith diário à A001, antes de qualquer média sazonal. Tmax é a maior máxima horária do dia; Tmin, a menor mínima horária; T = (Tmax + Tmin)/2. Cada leitura de ponto de orvalho é convertida em pressão de vapor antes de calcular a pressão média diária. A pressão atmosférica é estimada pela altitude.

A média escalar de vento na altura nominal de 10 m é convertida para 2 m pelo perfil FAO56. Radiação global observada é convertida de kJ/m² para MJ/m² e usada no saldo de radiação; G = 0 na escala diária. Kc não participa da estimativa meteorológica da ETo: será aplicado separadamente no Urban Cooling.

Equação diária: ETo = [0,408 Δ (Rn − G) + γ (900/(T + 273)) u₂ (es − ea)] / [Δ + γ (1 + 0,34 u₂)]. T é temperatura em °C; Rn e G, energia em MJ/m²/dia; u₂, vento a 2 m em m/s; es e ea, pressões de vapor em kPa; Δ, inclinação da curva de pressão de saturação; γ, constante psicrométrica.

Para a altura nominal de 10 m, u₂ = 0,7479510751679441 × u₁₀. A pressão de vapor de cada leitura de orvalho Td é ea = 0,6108 × exp[17,27 Td/(Td + 237,3)], em kPa; calcula-se depois a média dessas pressões. Latitude, dia do ano e altitude entram nos cálculos de radiação extraterrestre/céu claro e saldo radiativo. Os intermediários diários são preservados na série da ETo.

A execução exige 24 valores válidos das variáveis essenciais e nenhuma lacuna de radiação em intervalo inteiramente diurno. Exclui-se 21/09/2026 por ausência de uma máxima horária. Em 58 dos 152 dias utilizados, pequenas ausências nas bordas solares totalizam 63 intervalos: a soma observada é uma aproximação identificada, sem preenchimento nem afirmação de energia ausente igual a zero.

A média aritmética das 152 estimativas diárias é 3,948045309995122 mm/dia. É uma média diária, não acumulado da seca. A fonte única A001 e a representação uniforme são escolhas da pesquisa. O raster coincide com a grade/máscara da cobertura; os 3 m representam alinhamento cartográfico.

Notas relacionadas: NM 03, NM 05.

### 5. Representar ocupação horizontal e altura em 500 m

A ocupação horizontal D é a área da implantação 103 dividida pela área terrestre válida na janela quadrada móvel de 500 × 500 m. Água e fora da máscara são excluídos do denominador; vias 104 e demais classes terrestres entram no denominador. Vias não são somadas à implantação de edifícios.

A altura H500 é Σ(altura disponível × área edificada interceptada) / Σ(área edificada com altura disponível interceptada). É média em metros, ponderada pela implantação; não é volume construído dividido pela área total do terreno. Janelas parciais e cobertura das alturas são identificadas. A integração considera a janela exata de 500 m sobre a grade de 3 m, com pesos fracionários nas bordas.

Normaliza-se V = mínimo(H500 / 31,5; 1), e combina-se I = 0,5 × D + 0,5 × V. A referência de 31,5 m é o P99 das medianas individuais de alturas. Pesos iguais permitem compensação: ocupação 0,40 com V 0,20 e ocupação 0,20 com V 0,40 produzem I 0,30.

As subclasses aplicam-se somente à implantação original 103: baixa até 0,25; média >0,25–0,50; alta >0,50–1. As faixas têm amplitudes diferentes. Cada subclasse recebe a média de I dos seus pixels com altura regional disponível: 0,1831179045052647; 0,3389960833545074; 0,5712112814785731. Não se faz média dos rótulos das classificações horizontal e vertical.

Notas relacionadas: NM 08, NM 09, NM 10, NM 11.

### 6. Executar e conferir o InVEST Urban Cooling

Foi utilizado o InVEST Urban Cooling 3.20.2, por script, com uma execução diurna pelo método factors e outra noturna pelo método intensity, ambas representativas da seca de 2026. O manual de referência consultado é o 3.20.0. O objetivo é estimar capacidade de resfriamento, mitigação térmica e temperatura do ar para apoiar o diagnóstico da IV na seca.

A cobertura auxiliar é associada à tabela pelo lucode. No dia: ETI = Kc × ETo / máximo(ETo); CC = 0,60 × shade + 0,20 × albedo + 0,20 × ETI. São mantidos os pesos padrão do modelo. Como a ETo adotada é uniforme e positiva, ETI = Kc nesta configuração.

Na noite: CC = 1 − building_intensity. O índice combinado da pesquisa é usado como adaptação desse parâmetro. O mecanismo adicional de áreas verdes utiliza green_area; o modelo considera a soma de área verde na vizinhança, com limiar interno de 2 ha, sem exigir que ela corresponda a um único fragmento contíguo. A influência verde pode elevar o índice de mitigação HM em relação à capacidade local.

Antes da mistura espacial, T_ar = Tref + (1 − HM) × UHI. A etapa de mistura gera a estimativa final de temperatura do ar. As distâncias de resfriamento e mistura são parâmetros diferentes da janela morfológica de 500 m; foram confirmados e utilizados 450 m para resfriamento e 500 m para mistura do ar, alinhados às recomendações iniciais do manual, sem calibração local.

Foram produzidos e conferidos CC e HM, adimensionais, e temperatura do ar em °C. As avaliações opcionais de energia e produtividade foram desativadas. Nesta apresentação são mostradas as superfícies contínuas da bacia; resultados por fragmento e classificação de risco pertencem à etapa de diagnóstico. O Urban Cooling não gera diretamente um mapa de umidade do ar. Não foi calculada média dia/noite. As duas execuções concluíram com código 0; a conferência leu integralmente as saídas, verificando grade, máscara, equações e integridade das cópias. Não houve calibração ou validação térmica empírica.

Notas relacionadas: NM 06, NM 07, NM 11, NM 12.

## Tabela biofísica

| Campo | Significado | Uso no modelo |
| --- | --- | --- |
| lucode / classe | Código inteiro único e nome da cobertura. | Relacionam cada pixel à linha correta da tabela; a auxiliar tem doze códigos válidos. |
| kc | Coeficiente adimensional da cobertura. | Multiplica ETo no cálculo de ETI diurno; pode superar 1 e não é medida de umidade ou de ET real. |
| shade | Fração de cobertura de copa de árvores com altura ≥2 m, entre 0 e 1. | Representa sombra arbórea no cálculo diurno; não inclui automaticamente sombra projetada por edifícios. |
| albedo | Fração da radiação solar refletida, entre 0 e 1. | Representa reflexão da superfície no componente diurno. |
| green_area | Indicador binário: 0 ou 1. | Define participação no mecanismo adicional de grandes áreas verdes; não decide a inclusão de uma classe nos fragmentos de IV. |
| building_intensity | Parâmetro noturno normalizado; nesta pesquisa, proxy composto de D e V. | Define CC noturna. A média D/V é adaptação e não mede a razão literal área de pavimentos/implantação do manual. |

A tabela é fundamentada em Hu, Wang e Li (2023), Tabela 1; a discussão de cobertura arbórea em Ribeiro e Walter (2008), e o apoio metodológico de dossel/sombra em Borges (2026). Stewart e Oke (2012) apoiam a discussão morfológica, sem prescrever nossa janela. Consultar [referências e papel de cada fonte](referencias-clima.md).

| lucode | classe | kc | green_area | shade | albedo | building_intensity |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | Formação florestal | 1.003927 | 1 | 0.95 | 0.14011 | 0 |
| 4 | Formação savânica — cerrado denso/típico | 0.967735 | 1 | 0.5 | 0.166499 | 0 |
| 11 | Campo alagado/pantanoso | 1.1 | 1 | 0.15 | 0.141964 | 0 |
| 12 | Formação campestre | 0.931543 | 1 | 0.05 | 0.192888 | 0 |
| 33 | Água | 1 | 0 | 0 | 0.056354 | 0 |
| 100 | Vegetação intraurbana | 1.003927 | 1 | 0.9 | 0.14011 | 0 |
| 101 | Forração vegetal | 0.931543 | 1 | 0.05 | 0.192888 | 0 |
| 102 | Impermeável ou solo exposto | 0.4704955 | 0 | 0 | 0.220078 | 0 |
| 104 | Vias pavimentadas | 0.327539 | 0 | 0 | 0.20819 | 0 |
| 1031 | Edificações — baixa | 0.327539 | 0 | 0 | 0.20819 | 0.1831179045052647 |
| 1032 | Edificações — média | 0.327539 | 0 | 0 | 0.20819 | 0.3389960833545074 |
| 1033 | Edificações — alta | 0.327539 | 0 | 0 | 0.20819 | 0.5712112814785731 |

### Justificativas por classe

| Classe | Referência e adaptação |
| --- | --- |
| 3 — Formação florestal | Kc/albedo de tree cover de Hu. Shade 0,95 é hipótese de cobertura arbórea, discutida com Ribeiro e Walter; não é média local medida de todas as formações. |
| 4 — Formação savânica | Representação de cerrado denso/típico. Kc e albedo = 50% árvores + 50% herbáceas de Hu: 0,967735 e 0,166499. Shade 0,50. A coincidência do Kc com shrubland não torna o albedo original de arbustos o adotado. |
| 11 — Campo alagado/pantanoso | Kc 1,10 e albedo 0,141964 de herbaceous wetland. Shade 0,15 admite participação arbórea. Green_area 1; disponibilidade hídrica durante toda a seca não foi comprovada localmente. |
| 12 — Formação campestre | Kc/albedo de grassland e shade 0,05 como hipótese de pequena participação de copas. |
| 33 — Água | Kc 1 e albedo 0,056354 de permanent water bodies. Shade 0 e green_area 0 por decisão da pesquisa. O Kc mantém a contribuição local diurna de evaporação no modelo. |
| 100 — Vegetação intraurbana | Kc/albedo de tree cover. Shade 0,90 mantido por decisão expressa; não é reponderado pela origem florestal/savânica da classe. |
| 101 — Forração vegetal | Kc/albedo herbáceos e shade 0,05 por analogia operacional com campestre, admitindo algumas copas. Green_area 1 no modelo não inclui a classe na fragmentação da IV. |
| 102 — Impermeável ou solo exposto | Mistura sintética 50/50 de built-up e bare/sparse: Kc = (0,327539 + 0,613452)/2 = 0,4704955; albedo = (0,208190 + 0,231966)/2 = 0,220078. Não são proporções locais medidas. |
| 104 — Vias pavimentadas | Kc 0,327539 e albedo 0,208190 de built-up; shade, green_area e building_intensity iguais a zero. Built-up é referência urbanizada ampla, não medição exclusiva de asfalto. Retirar vias da 102 não torna o remanescente exclusivamente solo exposto. |
| 1031 / 1032 / 1033 — Edificações | Repetem Kc 0,327539, albedo 0,208190, shade 0 e green_area 0 de built-up. Diferem no coeficiente noturno, calculado como média do índice combinado em cada grupo. Baixa/média/alta são níveis desta classificação, sem equivaler a LCZ ou limiares térmicos calibrados. |

## Decisões metodológicas e limitações

### NM 01 — Recorte temporal e comparação seca/chuva

A seca representa maio–setembro/2026; a chuva exploratória, outubro/2025–abril/2026. São períodos observados de um ciclo, com 153 e 212 dias. Apresentar disponibilidade e denominadores; não interpretar a comparação como normal climatológica ou usar contagens brutas como se os períodos tivessem a mesma duração.

### NM 02 — Superfície, ar e contraste UHI

Landsat mede superfície, enquanto Tref vem do ar. O contraste entre duas áreas nas passagens diurnas não demonstra o máximo espacial de ilha de calor da bacia. Usá-lo na temperatura do ar e transferi-lo à noite são duas aproximações, sem observação noturna Landsat independente. O QA local em seis áreas não é auditoria térmica integral da bacia. O térmico nativo é de 100 m, distribuído a 30 m; alinhamento não cria informação térmica de 3 m.

### NM 03 — Critérios de completude específicos

Exploração: ≥20 leituras por dia e 24 intervalos para chuva; Sankey/dispersão: ≥20 pares T/UR. Tref: ≥20 temperaturas/dia e ≥80% em cada janela solar, com 147 datas pareadas efetivas. ETo: 24 valores das variáveis essenciais e tratamento da radiação descrito no procedimento. Não transportar um único critério para todos os produtos; ausências permanecem identificadas.

### NM 04 — Escolha e representatividade da A045

A045 foi selecionada pela menor média superficial do entorno comparativo; isso não prova que registre o ar mais frio de toda a região. A estação fica fora da bacia. O entorno de 500 m é recorte de comparação e não raio demonstrado de representatividade meteorológica. A seleção utiliza 13 datas Landsat de junho–setembro; Tref abrange datas elegíveis de maio–setembro, com compatibilidade sazonal e sem simultaneidade integral.

### NM 05 — Fonte única e uniformidade da ETo

A001 e raster uniforme são escolhas metodológicas aceitas. Não foi modelado um gradiente espacial meteorológico de ETo na bacia; grade de 3 m é cartográfica. O valor uniforme cancela em ETI = Kc × ETo / máximo(ETo), resultando em ETI = Kc. A uniformidade não comprova homogeneidade real do clima. A altura do vento de 10 m é nominal da rede, sem conferência da ficha individual de instalação/calibração em 2026.

### NM 06 — Transferência dos parâmetros e disponibilidade de água

Kc e albedo de Hu foram aplicados em Wuhan; sua transferência e as misturas sintéticas não constituem calibração local do Cerrado. ETI representa evapotranspiração potencial sob a disponibilidade hídrica assumida; não mede ET real nem comprova água disponível durante toda a seca. Os pesos 0,60/0,20/0,20 são os padrões diurnos aceitos, e não porcentagens de resfriamento observadas na bacia.

### NM 07 — Sombra, área verde e água

Shade representa copa arbórea, sem equivaler a toda vegetação ou à sombra dos prédios. Os valores são hipóteses e decisões apoiadas na discussão das formações. Green_area é uma regra do Urban Cooling: forração 101 recebe 1, mas continua fora da fragmentação da IV; água recebe 0, mantendo Kc 1 e sua contribuição local diurna. BI zero em água, solo, vias e vegetação produz CC noturna inicial 1: simplificação estrutural, sem demonstrar resfriamento físico máximo ou comportamento idêntico dessas superfícies.

### NM 08 — Representação das vias e da classe 102

A faixa de 2,5 m por lado é uma hipótese uniforme aplicada a linhas de eixos e margens; não mede a largura real ou o material de cada pista. Só 101/102 foram recodificadas para 104, com IV, edificações, água e NoData preservados. Os parâmetros integrais de built-up foram aceitos para 104; a 102 remanescente mantém a mistura 50/50, pois ainda pode conter outras superfícies impermeáveis. Essas proporções não foram medidas.

### NM 09 — Alturas e diferença temporal

Open Buildings 2023 é combinado com cobertura 2026 e SHP de temporalidade específica não comprovada. A distribuição de 0,5 m tem resolução efetiva aproximada de 4 m e foi alinhada a 3 m. Confiança de presença não é probabilidade calibrada; ≥0,50 é filtro operacional. Deslocamentos, pequenas construções e lacunas afetam as estimativas. Não se atribui à bacia a acurácia anunciada na avaliação original do conjunto.

### NM 10 — Índice composto, referência vertical e três níveis

A média 50/50 de ocupação e altura normalizada é adaptação, sem medição de área real dos pavimentos. A referência 31,5 m é P99 de alturas medianas individuais, não máximo do conjunto nem P99 das médias regionais; a saturação em V 1 elimina diferenças acima dela. A média permite compensação entre ocupação e altura. Os cortes 0,25/0,50 definem três faixas de amplitudes diferentes; o grupo alto é relativo à classificação adotada. Não são cortes oficiais do InVEST nem classes físicas calibradas.

### NM 11 — Suporte parcial e preenchimento residual

A média regional usa somente alturas aproveitáveis, sem mínimo adicional de cobertura. Na fonte individual, cerca de 24,15% da área 103 permanece sem altura; regionalizar não recupera essas alturas. Há 36,9252 ha de centros 103 com menos de 50% de cobertura das alturas na janela. Os 9.093.491 pixels 103 com média regional têm suporte parcial, flag 2. Outros 5.686 pixels, 5,1174 ha ou 0,06248917% da área edificada, usam a mediana regional de 6,445500373840332 m, mantendo D local e flag 9. Esse preenchimento foi aceito e não participou da estimação dos coeficientes representativos. Não é altura medida; os componentes disponíveis conservam as lacunas.

### NM 12 — Escalas, estado da execução e interpretação

Pixel de 3 m, janela morfológica de 500 × 500 m, entorno comparativo das estações e distâncias climáticas são suportes distintos. As distâncias 450/500 m foram confirmadas e utilizadas nas execuções diurna e noturna da seca de 2026. As saídas contínuas foram produzidas e conferidas; a apresentação dos resultados por fragmento e a classificação de risco ficam para o diagnóstico. Conferência técnica e aceite metodológico não constituem validação térmica. Critérios de risco serão revistos conforme as novas saídas; IDs antigos não devem ser associados aos atuais por igualdade numérica.

## Exploração INMET

Os gráficos e os critérios de agregação estão detalhados na primeira etapa. A triagem de consistência usa temperatura −60–60 °C, UR 0–100%, vento 0–100 m/s, precipitação horária 0–500 mm e radiação 0–10.000 kJ/m², preservando ausências. Não é auditoria dos sensores. A série diária contém contagens e disponibilidade; as fontes horárias são preservadas.

## Rastreabilidade e aplicação

[Metodologia na aba Clima](../diagnostico.html#metodologia-clima), [aplicação do InVEST](../aplicacao-invest.html), [qualidade das alturas](nota-qualidade-alturas.md), [preenchimento residual](nota-preenchimento-alturas.md). Tabela completa de doze classes e tabela diurna de dez classes correspondem a coberturas diferentes. Não intercambiar. As camadas integrais ficam na base local organizada. Scripts, parâmetros e verificações das execuções oficiais acompanham a publicação; esta organização do site não recalcula o modelo.

## Resultados contínuos da bacia

As duas rodadas oficiais estão concluídas, com 450 m de resfriamento e 500 m de mistura do ar, sem avaliações de energia/produtividade e sem média dia/noite. [Mapas contínuos e estatísticas](../diagnostico.html#resultados-invest), [configuração](../dados-modelo/invest-seca-2026/configuracao.json), [conferências](../dados-modelo/invest-seca-2026/verificacoes_bacia.json) e [registros da execução](../dados-modelo/invest-seca-2026/LEIA_ME.md). Resultados por fragmento e classificação de risco pertencem à etapa de diagnóstico e não são apresentados nesta produção.

A versão web agrega por média em 20 m, EPSG:3857, com codificação UInt16 para consulta. As cores são interpoladas da paleta existente. A escala comum permite comparar cenários; ampliar o contraste usa os limites do cenário e é desativado na comparação lado a lado. As estatísticas tabulares vêm da conferência integral dos rasters nativos de 3 m. A escala de cores não define risco.
