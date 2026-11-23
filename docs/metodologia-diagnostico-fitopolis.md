# Diagnóstico territorial do Sistema Fitópolis

Referência: 23 de novembro de 2026. Gabriela Miranda Sampaio Freires, PPG FAU UnB.

## Escopo e unidades

O diagnóstico articula a infraestrutura verde existente e as necessidades do território inteiro. A base atual preserva 46.876 fragmentos, identificados por `id_frag`. A malha territorial possui 1.358.654 hexágonos, incluindo áreas sem vegetação, com 30 m entre faces opostas, lado de 17,3205080757 m e área completa de 779,422863406 m². Há 6.856 células parciais na borda da bacia.

A malha tem orientação de topo plano e origem nas coordenadas (0, 0) do EPSG:31983. As coordenadas axiais `q` e `r` e sua chave `q:r` identificam a posição estável na malha. `id_hex` é o identificador inteiro desta população de células, ordenada por q e r; a chave axial deve ser usada para compatibilidade caso o recorte seja ampliado. As geometrias de borda são intersectadas com a bacia, com área efetiva registrada. O fechamento das áreas foi verificado contra a bacia, sem preencher o exterior com células completas.

Bacia e RAs são recortes de visualização e comparação, não unidades às quais se atribui uma situação única. A seleção territorial não recalcula os indicadores integrais de hexágonos ou fragmentos. Cada unidade contribui para um resumo de RA apenas com a parcela de sua área inserida nela. Seleções múltiplas usam a união dos recortes, sem duplicar unidades nas contagens ou áreas.

## Fontes e preservação

Os processamentos e os resultados científicos ficam sob `02 BASE DE DADOS/02_Análises/04_Fitopolis/Diagnostico_2026-11-23`. São produzidos novos arquivos; as fontes e os resultados anteriores são preservados. Os GeoPackages científicos não são enviados ao GitHub.

| Tema | Fonte de referência |
| --- | --- |
| Bacia e RAs | Limites IPE-DF, 2023, em `01_Base/vetores/01_Limites` |
| Fragmentos atuais | `diagnostico_climatico_completo_46876.gpkg`, camada `diagnostico_climatico`, da execução climática vigente |
| Clima | Execução `Seca_2026_A001_102_104_2026-11-16`, InVEST Urban Cooling 3.20.2 oficial; resultados diurnos preservados e noturnos corrigidos |
| Landsat | `07_Superficie_sazonal/lst_seca_30m.tif` e `lst_chuva_30m.tif`; 13 datas secas e seis chuvosas |
| Inundação | `inundacao_profundidade_TR5_hidro.tif`, grade de 20 m; modelo existente mantido |
| Momentos da Água | `momento_dominante.tif`, grade de 5 m; modelo existente mantido |
| Uso e cobertura | `uso_cobertura_2026_vias_pavimentadas_3m.tif`, dez classes convencionais atuais |
| Renda | `Bacia_Paranoa_setores_renda_Censo2022.gpkg`, campo V06004 e situação de disponibilidade |
| Edificações | `Construções Bacia do Paranoá.shp`, 417.869 feições na auditoria de referência |
| PRE | `PRE_Bacia_Paranoa_MERGE_IPE_DF_2023.shp`, classes institucionais de `cat_pdot20` |

Os caminhos completos estão centralizados em `scripts/fitopolis_fontes.py`. Os identificadores antigos `patch_id` pertencem a outra população, de 33.454 fragmentos; não são relacionados a `id_frag` por igualdade numérica. O mapa anterior é mantido em `mapa-historico.html`, explicitamente identificado como histórico.

## Estatísticas raster e cobertura

As novas extrações utilizam a fração exata da área de cada pixel intersectada pela geometria, em EPSG:31983, por meio de [exactextract](https://isciences.github.io/exactextract/). A média é ponderada pelas frações de interseção; mínimo e máximo consideram pixels válidos com interseção positiva. A área válida é a soma das frações de pixels válidos multiplicada pela área do pixel. A cobertura válida é essa área dividida pela área efetiva da unidade, em porcentagem. Também se preserva o desvio padrão populacional ponderado.

Esse procedimento não substitui a resolução da fonte nem acrescenta informação observada. As extrações climáticas anteriores por centros de células permanecem preservadas nos produtos da rodada climática; o diagnóstico territorial novo tem método e saídas próprios. O modelo climático não foi executado novamente.

Os campos numéricos ausentes são nulos nos GeoPackages e NaN nos buffers web. Não são preenchidos com zero. Quando não existe área válida de um raster categórico, suas proporções também ficam ausentes; cobertura zero registra a falta de estimativa.

### Clima

São mantidos separadamente CC, HM e temperatura estimada do ar para dia e noite da seca de 2026, além da temperatura de superfície Landsat da seca e da chuva. Não há execução InVEST chuvosa nem média sintética dia/noite nesta atualização. O diagnóstico não cria limiares sanitários nem regras da matriz.

Os campos `*_mean`, `*_min`, `*_max`, `*_stdev`, `*_valid_m2` e `*_coverage_pct` registram estatísticas e cobertura de cada superfície. A interface usa escalas contínuas fixas por indicador, comuns a todos os recortes de RA e às duas unidades analíticas.

### Inundação TR5

São registrados:

- `inundacao_valid_m2`: área em que há estimativa, incluindo profundidade zero;
- `inundada_m2`: área com profundidade estritamente positiva;
- `inundada_pct_valida`: 100 × área inundada / área válida;
- `profundidade_media_inundada_m`: média ponderada somente na parcela positiva;
- `inundacao_max`: máximo da profundidade válida;
- `inundacao_coverage_pct`: cobertura válida da unidade.

Uma unidade com estimativa e nenhuma parcela positiva tem proporção inundada zero e média da parcela inundada não aplicável. Uma unidade sem estimativa tem proporção e profundidades ausentes. Os campos auxiliares `inundacao_mean`, `min` e `stdev` referem-se à parcela válida inteira, incluindo zeros; não substituem a média condicional da parcela inundada.

### Uso e cobertura, Momentos da Água e PRE

Preservam-se as proporções de todas as classes, com denominador igual à área integral efetiva da unidade. As proporções somam a cobertura válida, e não necessariamente 100%. São dez classes de uso e cobertura; fonte, condução e acomodação para Momentos da Água; baixo, médio, alto e muito alto para PRE.

No PRE, recortes da mesma classe são unidos, evitando dupla contagem. Áreas disputadas entre classes são retiradas das parcelas exclusivas e registradas em `pre_pct_sobreposicao`. A união das parcelas exclusivas com a área disputada define a cobertura válida. A ausência de PRE não significa potencial baixo. Não são recalculados os índices institucionais.

Para eficiência, polígonos muito extensos de PRE são subdivididos por interseções exatas antes do cruzamento. A soma de áreas antes e depois é conferida. Essa subdivisão não simplifica contornos nem muda a unidade de análise.

## Renda contextual

Seleciona-se o setor censitário de maior área de sobreposição com cada unidade. Em empate exato de área, o menor código de setor torna o resultado determinístico. São preservados o código, o indicador V06004, a situação de disponibilidade e `setor_pct_unidade`.

V06004 representa o rendimento médio dos responsáveis pelo domicílio com renda. A conversão em salários mínimos usa R$ 1.212, referência de 2022. Não é renda per capita, renda média domiciliar ou estimativa da população de um hexágono. Não se calcula renda populacional ponderando setores apenas por área. Valores suprimidos ou indisponíveis permanecem ausentes.

## Edificações

As projeções são unidas antes das interseções. Nos fragmentos, o domínio é o buffer positivo de 30 m da geometria integral, incluindo o interior, intersectado com a bacia. Calcula-se 100 × área da união de edificações nesse domínio / área do domínio. Nos hexágonos, o domínio é a própria célula, recortada à bacia. Os campos são `edif_ocupada_m2`, `edif_dominio_m2` e `edif_pct`.

O buffer utiliza 16 segmentos por quadrante. Geometrias extensas podem ser subdivididas por interseção exata para acelerar os cruzamentos; as parcelas são somadas novamente por ID. Nas extrações raster dos fragmentos, partes poligonais de até 500 m permitem processar as geometrias extensas de forma estável. Contagens fracionárias, somas e segundos momentos recompõem média e desvio padrão da unidade integral. Componentes lineares de área zero produzidos nos cortes não entram nas estatísticas de área.

Esses domínios têm interpretações diferentes. O filtro de RA não altera o buffer, o denominador ou o resultado de um fragmento. Não é buscado inventário de edificações fora da bacia. A janela climática de 500 × 500 m é um procedimento distinto.

## Recortes administrativos e resumos

As interseções unidade–RA registram o ID e a área efetivamente inserida em cada recorte. Antes dos resumos aditivos, verifica-se a inexistência de sobreposição material entre os recortes administrativos. Contagens de unidades na união de várias RAs usam IDs únicos.

Uma cobertura resumida dentro de uma RA é estimada multiplicando a área da interseção pela proporção válida da unidade integral. É uma agregação dos indicadores das unidades, e não uma nova extração dos pixels dentro da RA. Essa distinção permanece visível na interface. Mínimos e máximos dos resumos são os valores integrais das unidades que intersectam o recorte. A média da parcela inundada não aplicável não elimina a informação de cobertura do modelo.

## Limites hidrológicos mantidos

Por decisão expressa da autora nesta tarefa, são mantidos os resultados existentes de inundação e Momentos da Água. A cobertura utilizada nesses modelos é anterior à cobertura atual do clima; a atualização das extrações não equivale a recalcular hidrologia ou condicionantes.

A modelagem representa o escoamento que chega ao Lago Paranoá, mas não simula a variação de seu nível, a operação da barragem e os efeitos de remanso sobre os afluentes. As áreas excluídas permanecem sem estimativa de profundidade e se distinguem das áreas em que o modelo estimou ausência de inundação. A exclusão por trechos controlados pelo reservatório alcança também áreas além do espelho d’água. Há ainda células sem trecho de drenagem associado.

Na auditoria anterior, a cobertura TR5 por centros de células era aproximadamente 88,64% da bacia. Esse valor é uma referência de auditoria, não um substituto da área por interseção exata desta extração. Não se interpreta a máscara de ausência de dados como área comprovadamente inundável.

A revisão futura preservará as equivalências aprovadas 100 → parâmetros florestais e 101 → campestres. A parametrização da classe 102 continua pendente; não se importou uma hipótese 50/50. A dinâmica do lago e os cálculos de conectividade não são executados nesta entrega. A matriz é a próxima etapa e ainda requer critérios definidos com a autora.

## Formatos, precisão e interface

Os GeoPackages guardam geometrias e atributos integrais. O navegador recebe posições/IDs e atributos separados em arquivos compactos, carregados por necessidade e reutilizados por cache. Os valores numéricos são Float64 little-endian, sem quantização adicional. SHA-256, contagens e comprimentos estão no manifesto. A validação compara os buffers descomprimidos com os resultados locais.

O panorama usa uma imagem de IDs de 20 m em Web Mercator apenas para representação; unidades pequenas podem não aparecer. A consulta por ID abrange a população completa. Em zoom próximo, os hexágonos são reconstruídos de q/r no navegador, com contornos conforme a aproximação. A conversão cartográfica é conferida contra GDAL. O recorte web de bacia/RAs utiliza geometrias cartográficas; as áreas científicas vêm das interseções locais integrais. Contornos individuais dos fragmentos reutilizam os lotes atuais, simplificados em 3 m.

As cinco otimizações aprovadas são: carregamento sob demanda e cache; separação de geometria/posição e atributos; desenho adequado ao zoom; resumos previamente calculados; controle de redesenhos e divisão de tarefas extensas. A referência arquitetural é o [Vereda/Taquari](https://github.com/renatobrodrigues-cmd/riscos-sbn-taquari). A implementação desta atualização é própria; seus métodos e resultados do Paranoá não são atribuídos ao Vereda.

## Reprodução

Use o Python do QGIS 3.44.15, GDAL/OGR, NumPy, pandas, Shapely 2.1, PyArrow, Pyogrio e exactextract 0.3.0. A biblioteca exactextract está instalada de forma isolada em `02 BASE DE DADOS/05_scripts/.runtime-fitopolis`; os pacotes do QGIS não foram substituídos. A escrita/leitura vetorial usa Arrow e OGR, evitando depender da extensão PyProj bloqueada pelo ambiente.

```powershell
./scripts/fitopolis_ambiente.ps1 scripts/gerar_diagnostico_fitopolis.py --etapa tudo
./scripts/fitopolis_ambiente.ps1 scripts/exportar_diagnostico_fitopolis.py
./scripts/fitopolis_ambiente.ps1 scripts/validar_diagnostico_fitopolis.py
node --test scripts/test_fitopolis.cjs
```

As etapas guardam checkpoints locais e não executam os modelos de clima ou hidrologia. Tempos de processamento, inventário, subdivisão, geometria, exportação e validação ficam na pasta da execução. Mudanças de método ou fontes exigem uma nova pasta de execução; não reutilize checkpoints de insumos diferentes.
