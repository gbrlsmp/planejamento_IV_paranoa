# Atualizar os dados vigentes

O sistema apresenta somente a revisão atual. Versões anteriores ficam no histórico do Git, sem seletores ou cópias antigas nas telas.

## Conjunto climático

Há **3 indicadores e 7 produtos principais**: uma zona de ilha de calor, três temperaturas e três HM. Dia (`factors`), noite (`intensity`) e média são cenários diferentes. PNGs de classes, degradês, prévias e estatísticas por fragmento são representações desses produtos.

`dados-mapas/clima/catalogo.json` é a referência única de fontes, cortes, cores, escala, precisão e campos. Cada fonte tem SHA-256. A revisão é derivada desse contrato e acompanha o diagnóstico web, o resumo por RA e os mapas metodológicos. A navegação verifica as revisões; requisições revalidam o cache e as imagens usam a revisão na URL.

## Fluxo de atualização

Execute com o Python do QGIS, com GDAL, NumPy, Pillow e Shapely 2. As entradas de pesquisa são somente leitura. Faça as alterações em uma branch e publique o conjunto completo após a validação.

1. Se os seis rasters mudarem, regenere o catálogo e as imagens com `exportar_cenarios_climaticos.py --source-dir "caminho/InVEST/v6"`. Essa etapa verifica alinhamento e a média dos cenários, calcula os cortes na resolução original e registra os hashes.
2. Calcule o diagnóstico com `01_Diagnostico_RISCOS.py` conforme seu [guia](../scripts/LEIA_ME_RISCOS.md). Preserve o JSON de parâmetros: ele associa as estatísticas zonais aos hashes dos rasters. Para mudar apenas as classes, use o diagnóstico vigente dos mesmos rasters e seu registro de proveniência.
3. Execute a atualização conjunta, informando as RAs completas, o limite da bacia e o diagnóstico. Não use a camada de RAs já recortada para decidir se uma RA está inteiramente na bacia.

```sh
python scripts/atualizar_clima.py --source-dir "caminho/InVEST/v6" --fragmentos "caminho/diagnostico.gpkg" --proveniencia "caminho/parametros.json" --ras "caminho/regioes_administrativas.shp" --bacia "caminho/Bacia_Paranoa_MERGE_IPE_DF_2023.shp" --ogr2ogr "caminho/ogr2ogr.exe" --base-riscos "caminho/01_Riscos"
python scripts/validar_clima.py
```

O atualizador cria um GeoPackage temporário com as geometrias completas. Preserva os valores zonais; aplica os cortes vigentes à temperatura e ao HM; regenera a zona na resolução original e suas interseções; exporta o mapa, o resumo por RA e as imagens metodológicas. Os arquivos ativos usam nomes estáveis e são substituídos. A validação impede misturar arquivos de revisões distintas. Se uma execução falhar, corrija e execute novamente antes de fazer o commit; não publique uma atualização parcial.

A rotina admite a mesma população de fragmentos da publicação. Alterações de geometria ou quantidade exigem nova auditoria antes da atualização. O diagnóstico deve corresponder aos rasters atuais; não se pode reutilizar estatísticas zonais antigas após mudar as fontes.

`--migration` é reservado à migração inicial da rodada histórica v01: confere todos os valores dos seis campos, por `patch_id`, contra o diagnóstico publicado, com tolerância de 0,00005001 por causa do antigo arredondamento de armazenamento. O arquivo `atualizacao.json` documenta essa migração, sem substituir as fontes da pesquisa.

## Diferenças legítimas de representação

O mapa de entrada mostra variação espacial do raster; no fragmento há uma única estatística: temperatura média no interior e HM médio no anel externo de 5 m. Uma cor única no fragmento não preserva cada célula do raster. Ambos usam os mesmos cortes e cores. A comparação absoluta entre dia, noite e média deve usar o degradê de escala comum; as cinco classes são relativas aos extremos de cada cenário.

Na zona de calor, as três classes mais quentes da temperatura média definem a máscara. Um fragmento recebe ocorrência se qualquer parte tiver sobreposição de área positiva, mesmo que sua temperatura média esteja em outra classe.

## Verificação da publicação

A ação `Validar conjunto climático` executa `validar_clima.py` em pushes e PRs. Ela verifica revisão, cortes, classes de todos os fragmentos, presença dos arquivos e remoção das configurações e imagens climáticas obsoletas. Confira também no navegador os seis cenários, as duas representações, a zona de calor e a tabela por RA. A publicação no Pages ocorre quando o PR é integrado à `main`.
