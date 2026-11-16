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

As expressões “proposto” e “para revisão” dos arquivos originais descrevem o estado da produção. Esta nota registra especificamente o aceite posterior do preenchimento; não representa aceite automático das demais configurações do InVEST. Não houve alteração dos rasters ou nova execução do modelo para elaborar esta nota.
