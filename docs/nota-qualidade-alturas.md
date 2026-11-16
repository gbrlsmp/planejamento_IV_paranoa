# Nota técnica — cobertura e qualidade das alturas regionais

Registro em 15/11/2026, horário de Brasília. Projeto: infraestrutura verde da Bacia do Paranoá. Complemento documental à entrega 11, sem reprocessamento dos dados.

## Encaminhamento da pesquisadora

Na revisão da qualidade das alturas disponíveis, a pesquisadora solicitou: “registra como uma nota tecninca”. Registra-se a manutenção do procedimento existente: calcular as alturas regionais com os dados aproveitáveis e documentar o suporte parcial, sem introduzir neste registro um percentual mínimo adicional de cobertura. Esse encaminhamento é uma decisão de tratamento e transparência metodológica, sem constituir validação empírica das alturas ou da previsão térmica.

## Procedimento aplicado

A altura regional H500 é a média das alturas disponíveis na vizinhança quadrada móvel de 500 × 500 m, ponderada pela área de implantação com altura aproveitável interceptada pela janela:

H500 = soma(altura × área edificada com altura disponível) / soma(área edificada com altura disponível).

A fonte é o raster de alturas individuais da entrega 08, derivado de Open Buildings 2023 e do cruzamento com o SHP de construções existente. O processamento original adotou confiança de presença ≥ 0,50 e alturas > 0 e ≤ 100 m. Esses filtros permanecem; a ausência de cobertura mínima regional não significa ausência de filtros de qualidade na fonte.

Sem edifícios na janela, o resultado regional é zero. Havendo edifícios sem nenhuma altura aproveitável, H500 permanece ausente nos produtos disponíveis. Havendo alguma altura, a média utiliza somente a parcela edificada com dados. As alturas ausentes não são tratadas como zero.

O suporte é expresso por:

Cobertura de alturas (%) = 100 × área edificada com altura disponível / área edificada total na janela.

Esse percentual mede disponibilidade de altura sobre a área edificada, e não a ocupação horizontal do terreno nem a probabilidade de acerto da estimativa.

## Diagnóstico documentado

- A fonte individual conserva aproximadamente 24,15% da área da classe 103 sem altura aproveitável.
- A regionalização permite calcular médias contextuais em quase toda a classe 103, mas não recupera as alturas individuais ausentes.
- Na entrega 11, os 9.093.491 pixels 103 com altura regional disponível recebem flag 2: média baseada em cobertura parcial de alturas na janela.
- Desses centros de pixels 103, 36,9252 ha têm médias calculadas com menos de 50% da área edificada da janela coberta por alturas. Os 50% são uma referência descritiva do diagnóstico, não um filtro aplicado ou um limiar validado.
- Outros 5.686 pixels 103, equivalentes a 5,1174 ha, não têm altura regional disponível. Seu preenchimento na cobertura completa é tratado em nota própria, com flag 9.

## Interpretação e rastreabilidade

Uma média calculável não garante representatividade de todas as construções da janela. Se as alturas ausentes tiverem características diferentes das disponíveis, a média pode apresentar viés. A proporção de dados disponíveis indica suporte; não quantifica, sozinha, o erro da altura.

Devem ser consideradas as limitações de detecção, confiança não calibrada, alinhamento espacial e a diferença temporal entre alturas de 2023 e cobertura de 2026. A regionalização e a conferência numérica não constituem validação independente das alturas ou calibração térmica do índice combinado.

O raster `qualidade_combinacao_500m_3m.tif` identifica: 0 = cobertura não 103; 1 = altura regional com cobertura de alturas de 100%; 2 = altura regional com cobertura parcial; 9 = preenchimento residual; 255 = fora da máscara. Na entrega atual, não há pixels 103 com flag 1.

A avaliação deve consultar também `cobertura_alturas_validas_janela_500m_percentual_3m.tif`, na pasta irmã `10_Altura_regional_500m_2026-11-15`.

Fontes locais: `RESULTADO_COMBINACAO.json`, `RELATORIO_COMBINACAO_E_TABELA.md` e os produtos de suporte da entrega 10. O tratamento do preenchimento está em [Nota técnica — preenchimento residual](nota-preenchimento-alturas.md).

Esta nota documenta o procedimento mantido. Não altera rasters, coeficientes, fontes ou resultados e não corresponde a uma nova execução do InVEST.
