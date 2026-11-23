# Entrega do diagnóstico territorial — Sistema Fitópolis

Issue: [#89](https://github.com/gbrlsmp/planejamento_IV_paranoa/issues/89).

## Resultado

- Apresentação, identidade e autoria atualizadas, com “Como ler o sistema” e “Próximas atualizações”.
- 1.358.654 hexágonos de 30 m entre faces; 6.856 células parciais; 46.876 fragmentos atuais, com geometrias e IDs preservados.
- Novas extrações de clima, TR5, uso e cobertura, Momentos da Água, PRE, renda contextual e edificações. Interior + entorno de 30 m para os fragmentos, limitado à bacia; ocupação dentro da própria célula para hexágonos.
- Seleção de todas, uma ou várias RAs em mapas atuais e históricos, recorte das camadas e comparação com legenda comum.
- GeoPackages científicos locais e 181 atributos numéricos em buffers Float64 independentes para a web, com carga por necessidade, cache limitado, desenho por zoom e resumos previamente calculados.
- Histórico preservado em `mapa-historico.html`. Conectividade e dinâmica do lago continuam previstas; matriz é a próxima etapa de discussão.

## Resultados científicos locais

Pasta relativa a `02 BASE DE DADOS`:

`02_Análises/04_Fitopolis/Diagnostico_2026-11-23`

| Arquivo | Finalidade |
| --- | --- |
| `hexagonos_diagnostico.gpkg` | 1.358.654 geometrias e atributos completos, camada `hexagonos` |
| `fragmentos_diagnostico.gpkg` | 46.876 fragmentos e atributos completos, camada `fragmentos` |
| `diagnostico_fitopolis.gpkg` | Geometrias de referência: hexágonos, fragmentos, bacia e RAs |
| `hexagonos_atributos.csv` / `fragmentos_atributos.csv` | Tabelas integrais com os indicadores |
| `*_intersecoes_ras.feather` | Relação de IDs com RAs e áreas efetivamente inseridas |
| `fontes_sha256.json` | Registro dos insumos e hashes |
| `validacao.json` | Verificações científicas e confronto com buffers web |
| `tempos.json`, `malha.json`, `*_subdivisao.json` | Medidas de execução e parâmetros geométricos |

Os arquivos `fonte_*`, `ensaio_*`, arquivos de partes/subdivisões e checkpoints Feather são intermediários. Não substituem os dois GeoPackages completos identificados acima. Nenhum modelo climático ou hidrológico foi executado novamente.

## Validação

A validação local verificou IDs únicos, validade e área das geometrias, igualdade de todos os fragmentos com a fonte, limites e composições dos indicadores, denominadores, ausência de dados e ausência de sobreposição material nos resumos por RA. As novas estatísticas foram confrontadas com interseções independentes de pixels em amostras; renda e edificações também foram conferidas contra os vetores originais. Os atributos de referência do GeoPackage completo foram comparados integralmente com as tabelas de processamento, e os 181 buffers web com os respectivos valores Float64 locais.

Passaram 22 testes JavaScript, o contrato do conjunto climático anterior preservado, a validação da produção climática e sua regeneração idempotente, a validação científica local e a validação dos derivados web sem GIS.

A revisão no navegador confirmou: apresentação e unidades/recortes; leitura da bacia; seleção de Plano Piloto e Vicente Pires; contagem sem duplicação na união; alternância hexágonos/fragmentos; consulta do hexágono 3024; fragmento 236 com inundação zero e média condicional não aplicável; fragmento 890 sem estimativa; pressão por edificações e resumo de 1.065 fragmentos em Vicente Pires.

A confirmação do arquivo baixado pelo botão CSV não pôde ser concluída: a automação do navegador expirou nessa ação. A geração das linhas CSV foi testada em código, incluindo zero, ausência, média não aplicável e área parcial. Os CSVs científicos completos foram gerados localmente.

## Ensaio de desempenho

Servidor local, navegador com cache aquecido, malha real de 1.358.654 hexágonos. Uma atualização do indicador térmico da bacia levou 2.211,4 ms; resumo da bacia, 0,6 ms; desenho detalhado de 2.621 células, 17,2 ms. O heap JavaScript observado após a atualização foi 271.106.550 bytes, aproximadamente 258,5 MiB. Em outra seleção, o resumo de Plano Piloto + Vicente Pires levou 189 ms.

Esses valores descrevem um ensaio local, não o tempo do primeiro download pela internet ou uma garantia em outros dispositivos. Os derivados web totalizam aproximadamente 247 MB, divididos por unidade e atributo; não são baixados todos ao abrir o mapa. A exibição panorâmica de IDs de 20 m pode omitir unidades pequenas, que continuam consultáveis pelo ID.

## Continuidade

A autora confirmou nesta tarefa a manutenção dos resultados atuais de inundação e Momentos da Água. A diferença de versão do uso do solo está documentada. Não há decisão hidrológica pendente para executar esta entrega. A parametrização futura da classe 102 continua em aberto; 100 → florestal e 101 → campestre já estão decididos para uma revisão futura.

A próxima etapa é discutir e construir a matriz: indicadores, ausências, combinações, eventuais pesos e cortes, diretrizes de conservação/recuperação/ampliação e continuidade espacial das regiões de situação. Não foram inventadas regras da matriz, nem calculados PC/dPC ou a dinâmica do lago.
