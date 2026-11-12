# Consulta das métricas e paletas do relatório

## Resultados do Makurhini

A seção Métricas de forma oferece uma consulta por ID, com os oito campos e os dois cenários lado a lado, e quatro downloads: métricas dos fragmentos e da paisagem, nas bordas de 45 m e 90 m. Os CSVs publicados são cópias byte a byte dos produtos locais adotados, com o prefixo `MK_Fragmentation_Bacia_Paranoa_{45|90}m_AVU`. Os arquivos antigos de 45 m sem `_AVU` não são usados.

Origem: `02_Análises/03_Ecologia/01_Fragmentação`, sob a base local. Há 46.876 fragmentos por cenário e 13 indicadores por tabela da paisagem. O campo `IdTemp` corresponde a `id_frag` nos GeoPackages. A primeira coluna sem nome dos CSVs é o índice de linha gerado pelo R; a consulta usa `IdTemp`.

| Campo | Apresentação | Unidade nesta execução |
| --- | --- | --- |
| Area | Área total | m² |
| CA | Área de núcleo | m² |
| CAPercent | Percentual de núcleo | % |
| Perimeter | Perímetro | m |
| EdgePercent | Percentual de borda | % |
| PARA | Área / perímetro | m |
| ShapeIndex | Índice de forma | adimensional |
| FRAC | Dimensão fractal | adimensional |

Os cálculos existentes usam a [revisão fixa do MK_Fragmentation](https://github.com/connectscape/Makurhini/blob/0010946ab2eef7f8d2bc4935f369869fc4c58671/R/MK_fragmentation.R), com áreas/perímetros/núcleos fornecidos por GEOS/Python ao R, `area_unit="m2"` e `perimeter_unit="m"`. **A instrução executada para PARA é `Area / Perimeter`**, embora o comentário dessa revisão descreva perímetro/área. A apresentação identifica a fórmula efetivamente usada e preserva os números originais. Não foi corrigida ou recalculada a métrica.

As tabelas da paisagem conservam os nomes e valores originais. A interpretação do limiar de tamanho merece distinguir a documentação da implementação dessa revisão: o padrão `min_node_area=100` é comparado diretamente com `Area`, portanto, com estes argumentos, o corte executado é 100 m²; a linha rotulada como percentual de fragmentos menores usa a soma de suas áreas, não a proporção da contagem. A densidade de fragmentos conserva o fator 100 da fórmula do pacote. Esses resultados não foram redefinidos para disponibilizar os arquivos.

A consulta carrega os dois CSVs de fragmentos somente ao enviar o formulário, mantém os dados na memória da página e exibe quatro casas decimais. Não altera as fontes nem os rasters. Os downloads funcionam independentemente da consulta. `.gitattributes` desativa a normalização de texto apenas nesses CSVs para preservar os bytes e as assinaturas entre Windows e Linux.

Reprodução no Python científico:

```powershell
python scripts/identificacao/publicar_metricas_makurhini.py --base "CAMINHO/02 BASE DE DADOS" --output "PASTA_NOVA_E_VAZIA"
python scripts/identificacao/validar_metricas_makurhini.py --base "CAMINHO/02 BASE DE DADOS"
```

O validador compara as cópias web com os originais, todos os IDs/campos dos dois GeoPackages, contagens, somas principais e hashes do manifesto. Não executa R novamente.

## Padronização das cores

Uso do solo, MapBiomas, ZEE, referências e IV conservam suas simbologias prescritas. Pastagem permanece `#915558`. Os mapas de área, de tipologias e os contornos de AVU usam as cores da paleta final existente, reunidas em `paletas_identificacao.py`. Os temas conservam seus próprios significados e suas legendas.

| Tema | Classes na ordem da legenda | Cores |
| --- | --- | --- |
| Área total | até 1; >1–10; >10–100; >100 ha | `#c4cc95`, `#86a58f`, `#4b6a40`, `#2b5125` |
| AVU | UC; Parque; Agro; APP; Sem AVU; Aviso | `#4b6a40`, `#86a58f`, `#d0a55f`, `#3e5972`, `#e1e1e1`, `#c4cc95` |

Contornos de UC, parque, agro e APP seguem as cores das categorias correspondentes. Proteção integral e uso sustentável distinguem-se pelo traço contínuo/tracejado; as duas APPs usam padrões de traço diferentes. A cor não altera sobreposições, critérios ou a atribuição ao fragmento inteiro.

`padronizar_paletas_relatorio.py` muda somente as paletas dos dois PNGs e metadados correspondentes. Confere igualdade exata dos códigos antes/depois, preserva transparência e limites, atualiza revisões do catálogo e cores do manifesto vetorial. Não modifica os GeoJSONs ou fontes científicas. `paleta-relatorio.json` registra os hashes dos planos de códigos sem a paleta para conferência futura. Geradores de tipologias e contornos usam as mesmas constantes para reproduzir a apresentação.

## Regras na tabela de IV

A tabela contém prioridade, elemento, regra, número de fragmentos e área. A lista anterior foi transferida integralmente para as células, preservando a sequência Hub 1 → Hub 2 → Link → Site 1 → Site 2, os IDs 17217/46862 e o corte estrito `ShapeIndex > 25`. O texto sobre a APP hidrográfica dissolvida e o resultado do ID 25996 foi preservado.
