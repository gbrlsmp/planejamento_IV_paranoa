# Leitura das métricas, da IV e das faixas cartográficas

## Fontes conceituais e escopo

Os textos foram preparados a partir de Gabriela Miranda Sampaio Freires (2026), **Sistema de Áreas Verdes Urbanas e sua Contribuição para Resiliência Climática: estudo sobre o Plano Piloto de Brasília**, projeto de dissertação de mestrado, FAU/UnB, maio de 2026, arquivo de qualificação fornecido pela autora.

Trechos consultados: seção 1.4 (PDF pp. 50–52), seção 2.3 (pp. 79–83, especialmente hubs/sites/links e Figura 41), seção 2.4.2 (pp. 91–95, Quadro 13) e seção 3.3.1 (pp. 121–122, Quadros 18/19). As páginas foram extraídas e as páginas 82, 93 e 122 também renderizadas para conferir os quadros e a leitura visual. O PDF permanece local; não foi adicionado ao Git.

A qualificação é referência conceitual, com discussão de Forman e Godron (1986), Turner e Gardner (2015), Benedict e McMahon (2002) e Sant’Anna (2020). Seus parâmetros históricos não substituem os da identificação atual da bacia. Mantêm-se 46.876 fragmentos, bordas de 45/90 m e regras da IV. As oito métricas do mapa são atributos dos fragmentos; os 13 indicadores dos CSVs `LandscapeMetrics` são resumos do conjunto.

Fórmulas/unidades conferidas no [código efetivamente adotado do MK_Fragmentation](https://github.com/connectscape/Makurhini/blob/0010946ab2eef7f8d2bc4935f369869fc4c58671/R/MK_fragmentation.R):

- PARA = Area / Perimeter (m). A leitura de perímetro/área no texto histórico não é transposta à razão inversa executada.
- ShapeIndex = Perimeter / (2 × sqrt(Area × pi)). A referência compacta é o círculo.
- FRAC = 2 × log(Perimeter) / log(Area), com os valores em m/m² da execução. Varia com o tamanho e pode superar 2 nos fragmentos pequenos; não foi truncada nem tratada como indicador isolado de qualidade ecológica.
- Edge density = soma de perímetros / soma das áreas dos fragmentos, não área total da bacia.
- Patch density = 100 × número de fragmentos / área da paisagem, nesta base em m².
- Cority é proporção da contagem com CA > 0; a linha percentual dos menores fragmentos usa área, não contagem. O limiar executado é 100 m².
- MESH = soma de Area² / área da paisagem.

No texto da IV, hubs ancoram a rede, links são conexões e sites são áreas descontínuas complementares. As cinco classes operacionais atuais são explicadas, mantendo a tabela de prioridade/regras. Sua atribuição não comprova conectividade funcional. Os números 1/2 não são apresentados como escores de qualidade.

## Imagem

`imagens/infraestrutura-verde-elementos.png` é cópia byte a byte de `Prancheta 19.png`, fornecida pela autora. Dimensões 2497 × 1401, SHA-256 `50fbe11ec2f815a89870a8b1ce20a5ac5c5f1f991fed1f2c6d4a15ccc0c93917`. Não foi redesenhada, recortada ou corrigida. Legenda e texto alternativo descrevem a função conceitual; as cores do esquema não substituem a legenda cartográfica. A figura é responsiva, limitada a 1100 px de largura, e pode ser aberta em tamanho original.

## Faixas de Perimeter, PARA e FRAC

Os quartis simples concentravam os cortes em fragmentos pequenos, que são numerosos, mas ocupam pouca área. Os limites superiores eram 18/42/114 m para Perimeter, 1/1,68/3,3462 m para PARA e 1,5948/1,7737/2 para FRAC. As grandes áreas ficavam praticamente sem diferenciação.

`preparar_faixas_metricas_web.py` usa os valores originais de todos os 46.876 fragmentos e seus pesos `Area` para encontrar quatro intervalos contíguos que minimizam a soma dos desvios quadráticos ponderados dentro das classes. É uma classificação cartográfica por variância mínima ponderada. Programação dinâmica examina todos os cortes nos valores únicos; valores iguais ficam juntos. Normalização afim dos valores reduz cancelamento numérico, preservando o problema de otimização. Em empates, vale o primeiro corte encontrado. Não há amostragem, recálculo de métricas ou alteração dos critérios da IV.

| Métrica | Limites superiores inclusivos (valor original) | Percentual da área vegetal por classe |
| --- | --- | --- |
| Perimeter | 165906; 447498; 577134 m | 23,4329; 51,2051; 4,7174; 20,6446% |
| PARA | 31,283; 80,748; 185,9684 m | 12,4584; 14,2590; 22,0775; 51,2051% |
| FRAC | 1,4086; 1,5168; 1,6924 | 55,2337; 32,0505; 12,4797; 0,2361% |

A legenda de Perimeter converte apenas a apresentação para km: 165,906 / 447,498 / 577,134 km. O popup e os CSVs continuam em metros. Classes não têm igual número de fragmentos nem igual área; um único fragmento representa 51,2051% da vegetação e não é subdividido. Os maiores perímetros ficam agora em classes distintas. Os limites comuns foram conferidos em 45/90 m, pois as três métricas e Area coincidem nos cenários.

`dados-mapas/identificacao/metricas-mapa/faixas.json` registra hashes dos dois CSVs, método, limites exatos, extremos e contagens/áreas por classe. A revisão é SHA-256 canônica do conteúdo. O navegador confere os hashes de referência contra o manifesto das métricas. A paleta de quatro verdes é preservada; Area/CA, percentuais e ShapeIndex mantêm suas faixas anteriores.

```powershell
python-qgis-ltr.bat scripts/identificacao/preparar_faixas_metricas_web.py --check
python-qgis-ltr.bat scripts/identificacao/test_faixas_metricas_web.py
```

Sem `--check`, o preparador requer um arquivo de saída ainda inexistente. O teste compara a solução com enumeração independente de todas as partições em exemplos pequenos, além de verificar repetição de valores, entrada constante, invariância afim, ordem dos dados e pesos inválidos.

## Margens e conferência visual

A identificação usa `clamp(16px, 2.5vw, 40px)` de cada lado. A antiga limitação de 864 px não retorna: mapas e tabelas aproveitam a largura interna disponível. Apenas o esquema conceitual tem largura máxima própria. O override fica no CSS exclusivo da identificação; não muda as margens de diagnóstico ou de outras páginas.

No navegador, conferir as três faixas novas, valores por clique, cenários preservados, leitura contextual da métrica, bloco de 13 indicadores, imagem/legenda e comportamento em telas estreitas. Validadores científicos e de contornos continuam conferindo os dados originais.
