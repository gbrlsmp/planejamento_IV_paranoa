# Metodologia climática da Bacia do Paranoá

## Exploração INMET

Comparação de 01/10/2025–30/04/2026 (212 dias) e 01/05–30/09/2026 (153 dias), em A001, A045, A046 e A047. Não é normal climatológica. Dados horários originais, UTC convertido para UTC−03, sem imputação. Temperatura pontual, umidade e vento agrupados pelo timestamp local. Precipitação da hora anterior atribuída pela data de início do intervalo.

Médias diárias de temperatura/umidade/vento exigem ≥20 leituras válidas. Chuva diária exige 24 intervalos válidos; totais sazonais apresentados são somas dos dias completos, sem correção de lacunas. Limites operacionais de consistência: temperatura −60 a 60 °C, UR 0–100%, vento 0–100 m/s, precipitação horária 0–500 mm e radiação 0–10.000 kJ/m². A triagem não é auditoria dos sensores.

Dispersão e Sankey usam ≥20 pares T/UR no mesmo dia e médias das mesmas horas. Faixas pelos tercis da distribuição diária pareada dos dois períodos reunidos, calculadas por estação, limites idênticos entre períodos de cada estação. As categorias são relativas, não limiares de risco ou conforto. As ligações contam dias; não representam transições temporais nem causalidade. Contagens e percentuais usam os dias pareados válidos como denominador. Ciclos horários: média e quartis das leituras válidas por hora/período. Boxplots: distribuição dos dias válidos, não incerteza da média.

O script `scripts/explorar_inmet_seca_chuva.py` exporta série diária, contagens, disponibilidade, hashes das oito fontes e dados dos gráficos. A exploração não altera a ETo da A001 nem Tref da A045.

## Parâmetros e tabela

Consultar [aplicação do InVEST](../aplicacao-invest.html) e [referências](referencias-clima.md). Tabela completa de doze classes: 3/4/11/12/33/100/101/102/104/1031/1032/1033. Tabela diurna de dez classes mantém 103. Não intercambiar tabelas e coberturas.

ETo uniforme: 3,948045309995122 mm/dia, média de 152 estimativas diárias FAO56 da A001. Tref A045: 25,155903223760365 °C dia e 17,810113695827983 °C noite, 147 datas. Contraste UHI superficial diurno: 2,8593942060678548 °C em 13 cenas; transferência à noite é hipótese.

Intensidade adaptada: D = implantação 103 / área terrestre válida na janela de 500 × 500 m; H500 = altura média ponderada pela área edificada com altura disponível; V = min(H500/31,5;1); I = (D+V)/2. Faixas: baixa até 0,25; média >0,25–0,50; alta >0,50–1. Coeficientes: 0,1831179045052647; 0,3389960833545074; 0,5712112814785731. A linha 1034 é removida. Não são LCZ ou classes térmicas calibradas.

Preservação integral da implantação 103, água e máscara terrestre permite reutilizar D, H e I após inclusão das vias. O raster regional categórico foi atualizado para três níveis. Cobertura auxiliar UInt16/NoData 65535; original Byte/NoData 255.

## Notas técnicas

[Qualidade das alturas regionais](nota-qualidade-alturas.md) e [preenchimento residual](nota-preenchimento-alturas.md). Alturas parciais mantidas com indicação de suporte, sem percentual mínimo adicional. Preenchimento aceito de 6,445500373840332 m em 5,1174 ha, com D local e flag 9, excluído da estimação dos coeficientes representativos.

BI zero para superfícies não edificadas, inclusive vias, resulta em CC inicial 1 no método noturno: simplificação estrutural, sem evidência de resfriamento físico máximo. Os pesos 0,60/0,20/0,20 são os padrões diurnos do InVEST e estão aprovados.

## Estado das execuções

Não houve nova execução do InVEST. As distâncias históricas 450 m (resfriamento) e 500 m (mistura) ainda precisam de confirmação para a nova rodada. Preparação de entradas não constitui resultado de risco. A base atual tem 46.876 fragmentos; não juntar com a antiga por igualdade numérica de IDs.

Os produtos v6 e diagnósticos antigos são preservados em páginas históricas, identificadas como tais. Novos resultados serão incorporados à aba Clima após execução e verificação.
