# Nota técnica — preenchimento residual da componente vertical

Registro em 15/11/2026, horário de Brasília. Projeto: infraestrutura verde da Bacia do Paranoá. Complemento documental à entrega 11, sem reprocessamento dos dados.

## Decisão registrada nesta retomada

Após explicação do valor de 6,45 m e do seu uso como estimativa, a pesquisadora aprovou sua manutenção: “aaa entendi, tudo bem pode manter assim”. Em seguida, solicitou registrar também esse tratamento como nota técnica: “isso tmb vai como nota”.

O preenchimento residual já existente passa a ter aceite explícito de manutenção. Esse aceite atualiza o status de proposta registrado nos documentos originais, preservados como histórico, sem transformar o valor estimado em altura observada.

## Ausência e valor utilizado

Na classe original 103 — Edificações, 5.686 pixels não possuíam nenhuma altura regional aproveitável na janela de 500 × 500 m. Na grade de 3 m, correspondem a 5,1174 ha e a 0,0624891679764005% da área edificada, aproximadamente 0,0625%.

Para completar a cobertura auxiliar, adotou-se a mediana das alturas regionais H500 nos pixels originalmente 103 com H500 disponível:

- Altura de preenchimento: 6,445500373840332 m, apresentada de forma arredondada como 6,45 m.
- Componente vertical estimada: V = 6,445500373840332 / 31,5 = 0,20461905948699466.
- Componente horizontal: D local de cada pixel, mantida sem substituição.
- Índice para classificar o pixel preenchido: I = 0,5 × D + 0,5 × V.

A mediana é calculada sobre pixels de mesma área e representa a distribuição espacial das alturas médias regionais sobre a classe 103. Não é a mediana por quantidade de prédios, nem a mediana das alturas individuais de construções (5,5 m na entrega 08). Também não é a referência de normalização de 31,5 m, cuja função é transformar H500 na escala de 0 a 1.

## Aplicação e identificação

O preenchimento foi aplicado somente à classificação e aos produtos completos propostos da entrega 11. Foram atribuídos 5.680 pixels à subclasse 1031 e 6 pixels à subclasse 1033, conforme a combinação da altura substituta com a ocupação horizontal local.

As áreas preenchidas recebem flag 9 em `qualidade_combinacao_500m_3m.tif`. Os componentes e o índice disponíveis conservam as lacunas originais onde a componente vertical está ausente; a fonte individual de alturas não foi preenchida por esse procedimento.

Os pixels preenchidos não participaram da estimação dos coeficientes representativos de building_intensity por subclasse. Esses coeficientes foram calculados somente com os pixels 103 que tinham altura regional disponível; os pixels preenchidos recebem o coeficiente da subclasse à qual foram atribuídos.

## Limitação e status dos documentos

O procedimento usa uma referência global da distribuição regional sobre edificações para completar uma ausência local. Não demonstra que a altura real nesses locais é 6,45 m e não assegura representatividade local. Sua pequena participação na área edificada não comprova, por si só, ausência de efeito espacial.

A falta de altura individual na fonte (aproximadamente 24,15% da área 103) e a falta residual de altura regional aqui preenchida (aproximadamente 0,0625%) são situações distintas. A diferença decorre do uso de informações vizinhas no cálculo regional.

Fontes locais: `RESULTADO_COMBINACAO.json`, `RELATORIO_COMBINACAO_E_TABELA.md` e `qualidade_combinacao_500m_3m.tif`. Para o suporte parcial das médias, consultar [Nota técnica — qualidade das alturas regionais](nota-qualidade-alturas.md).

As expressões “proposto” e “para revisão” dos arquivos originais descrevem o estado da produção. O registro de 15/11 trata do aceite posterior do preenchimento da 103; não representa aceite automático das demais configurações do InVEST. Sua elaboração não alterou os rasters nem executou o modelo.

## Extensão noturna às superfícies 102 e 104 — 16/11/2026

A correção solicitada estende a intensidade do entorno às classes 102 (impermeável/solo exposto) e 104 (vias pavimentadas), mantendo a 103. Nas áreas dessas duas classes com D500 positivo e H500 ausente, aplica-se a mesma mediana regional somente para classificá-las nas faixas do índice I. São 484.009 pixels, equivalentes a 435,6081 ha: 412.505 na 102 e 71.504 na 104. Todos recebem flag 9 em `qualidade_intensidade_102_104_3m.tif`.

Esses pixels não participam da estimação dos coeficientes médios de cada nova subclasse. D500 igual a zero é mantido em categoria própria, com BI zero (1020/1040), sem atribuição de uma intensidade positiva. Os componentes observados permanecem intactos. A área preenchida adicional não deve ser confundida com os 0,0625% descritos para a classe 103.

A tabela auxiliar passa a 18 códigos. A noite foi executada novamente com o InVEST oficial; o dia anterior foi preservado após prova integral de equivalência dos atributos diurnos. Consulte a [prova, contagens e coeficientes](../dados-modelo/invest-seca-2026/equivalencia_diurna_102_104.json). O preenchimento continua sendo uma estimativa, sem calibração local ou comprovação da altura real em cada pixel.
