# Conferência da aplicação do Urban Cooling

## Fontes consultadas

- Logs e metadados locais das saídas v6, de 28 de outubro de 2026, incluindo `T_air`, `hm`, `cc`, `ref_eto`, `eti` e coeficientes reclassificados.
- Print dos parâmetros fornecido pela autora: 22,09 °C, 10,71 °C, 500 m e 450 m, coincidentes com os argumentos registrados.
- [Código oficial da versão 3.20.2](https://github.com/natcap/invest/blob/3.20.2/src/natcap/invest/urban_cooling_model/urban_cooling_model.py).
- [Manual oficial Urban Cooling](https://storage.googleapis.com/releases.naturalcapitalproject.org/invest-userguide/latest/en/urban_cooling_model.html).
- [Tabela biofísica v5](../dados-modelo/tab_biofisica_InVEST_v5.csv), [tabela diária INMET](../dados-modelo/INMET_diario_2025_ago_set.csv) e [ETo média por estação](../dados-modelo/INMET_2025_ago_set_ETo_medio.csv), da base local de pesquisa. As cópias publicadas preservam os valores.
- Script local `ETo.py` e metadados dos rasters do processamento `Completo_20261103_143519_903343`.

## Etapas e parâmetros confirmados

1. Cobertura e ETo são alinhadas; a versão usa moda para a cobertura e spline cúbica para ETo.
2. Em factors, ETI = Kc × ETo / máximo da ETo alinhada. Com pesos vazios, CC = 0,6 × sombra + 0,2 × albedo + 0,2 × ETI. A função normaliza os pesos pela soma.
3. Em intensity, CC = 1 − intensidade construtiva. ETo participa do alinhamento e da cobertura válida, mas não dessa expressão de CC.
4. HM combina CC local e a influência das células verdes. A distância de resfriamento configurada é 450 m. A regra interna usa a soma de área verde na vizinhança, com limiar de 20.000 m², e mantém o maior efeito elegível. Não é um teste de área individual ou conectividade de cada fragmento do diagnóstico.
5. Antes da mistura, T = 22,09 + (1 − HM) × 10,71. A distância de mistura configurada é 500 m e só atua na etapa de temperatura. Esses dois valores térmicos e a mistura do ar não alteram diretamente HM.
6. As influências espaciais são convoluções exponenciais, não buffers rígidos: a implementação converte as distâncias em células e constrói kernels truncados em cinco vezes a escala de decaimento.
7. As médias entre dia e noite foram preparadas após o modelo, separadamente para temperatura e HM; a igualdade foi verificada nas camadas originais. Não são médias observadas de 24 horas.
8. O diagnóstico calcula temperatura no interior do fragmento e HM na faixa externa de 5 m. Esse anel é independente das distâncias de 450 m e 500 m do modelo.

As etapas visíveis nas caixas foram ajustadas para separar a modelagem, a média entre cenários e o cálculo posterior por fragmento. A zona de calor é derivada da temperatura média; a atualização do polígono com os novos cortes permanece pendente.

## Conferência da tabela com os intermediários

A tabela v5 contém 16 códigos únicos: 3, 4, 9, 11, 12, 15, 19, 21, 24, 25, 33, 100, 241, 242, 243 e 244. Todos foram encontrados na grade alinhada com CC válido.

Foi selecionada uma célula válida de cada código e comparada aos rasters reclassificados de Kc, área verde, sombra, albedo e intensidade construtiva. Também foram verificadas ETI e CC pelos cálculos acima, com máximo da ETo alinhada de 6,649216651916504. Não foram encontradas diferenças acima da tolerância absoluta de 0,000001.

A conferência é por amostra de códigos e de associação dos coeficientes, não uma validação integral da superfície nem uma calibração climática. Células NoData de CC/ETo foram excluídas da seleção.

## Proveniência da ETo e da umidade

As tabelas históricas de ETo contêm 305 registros diários de cinco estações, com 61 dias por estação em agosto–setembro de 2025. O log v6 identifica `ETo_2025_ago_set_bacia_paranoa_3m.tif` como entrada. O arquivo alinhado retido no diretório intermediário foi localizado. A memória de cálculo e interpolação do arquivo anterior ao alinhamento ainda precisa ser recuperada para reprodução integral.

O script disponível atualmente descreve Penman–Monteith FAO-56, ajuste de vento a 2 m, radiação de onda longa, pressão pela altitude, fluxo de calor no solo diário nulo, umidade relativa média e IDW de potência 2. Isso não basta para afirmar que essa versão do script gerou a entrada de outubro.

Os metadados dos rasters climáticos de 3 de novembro registram **57 dias válidos comuns**, as cinco estações, grade de 3 m e IDW de potência 2. A umidade usada no diagnóstico vem desse processamento. A ETo desse processamento posterior não foi atribuída retroativamente à rodada v6.

## Origem dos valores térmicos: hipótese

A autora confirmou os valores configurados, mas não recuperou a memória de sua escolha. A especificação da versão 3.20.2 exige temperatura de referência e efeito de ilha de calor fornecidos pelo usuário; não tem padrões numéricos automáticos para esses dois campos.

Na tabela diária INMET, a média do campo `temp_media` de A047 (Paranoá/COOPA-DF) nos 61 dias é 22,09221608458066 °C. A máxima do campo `temp_max` de A001 (Brasília) no período é 32,8 °C. O arredondamento da primeira dá 22,09 °C e a diferença 32,8 − 22,09 dá 10,71 °C.

Essa correspondência sustenta uma hipótese de origem nos dados do INMET. Não comprova a escolha original de estações, o uso como referência rural nem a adequação de comparar média do período com máxima observada. A interface mantém essa origem como **a confirmar**, sem apresentar o cálculo como calibração validada.
