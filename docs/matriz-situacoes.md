# Matriz de situações do Fitópolis

O [piloto](../matriz.html) compara as porções do Plano Piloto e de Vicente Pires na Bacia do Paranoá. O total do Plano Piloto inclui as colunas dentro e fora do Parque Nacional. As famílias são propostas para discussão e admitem sobreposição.

| Família | Critério do piloto |
|---|---|
| Formações nativas abaixo dos cortes de calor | Cobertura predominante florestal, savânica, campestre ou de campo alagado e temperatura abaixo dos dois cortes. |
| Calor diurno e noturno em terra | Cobertura terrestre identificada ou mosaico e temperatura acima do corte nos dois períodos. |
| Calor em um único período em terra | Mesmas coberturas e temperatura acima do corte apenas de dia ou à noite. |
| Inundação em cobertura vegetada | Predomínio de uma formação nativa, vegetação intraurbana ou forração, com alguma parcela do hexágono positiva no TR5. |
| Inundação com edificações expostas | Interseção com área positiva entre a projeção edificada e pixels positivos do TR5 no recorte. |

Os cortes do ar correspondem à média da bacia mais um desvio-padrão por período da seca. A temperatura relativa, o CC e o HM permanecem consultáveis separadamente. A cobertura predominante ocupa mais de 50% da unidade. A tabela mostra hectares de território e percentual da área total do recorte. Para edificações, a ficha informa também a área efetivamente exposta. Em Vicente Pires, são 84,49 ha de células e 10,49 ha de projeções expostas. Cobertura parcial e ausência de estimativa permanecem explícitas.

A geometria de cada fragmento ou AVU é intersectada com o hexágono e o recorte. Uma célula pode conter vários fragmentos e uma AVU pode abranger várias situações. O panorama rasterizado serve para navegação. A tabela de combinações usa as áreas geométricas e distingue a estabilidade da combinação original da pertinência a uma família.

## Dados de distribuição

Os arquivos em `dados-mapas/matriz-situacoes/` são os derivados do piloto validado em 23 de novembro de 2026. O catálogo descreve famílias por índice, totais, exemplos, grupos, recortes e sensibilidade. Os vetores binários preservam os valores do piloto, incluindo dados ausentes. Os dois PNGs codificam identificadores para a consulta cartográfica. As geometrias científicas e a base relacional são mantidas na base local.

Para reexportar os dados de uma cópia validada, execute `python scripts/exportar_dados_matriz.py CAMINHO/Explorar_piloto.html`. Para testar a navegação, sirva a raiz do repositório por HTTP, abra `matriz.html` e selecione uma família e um recorte. Em **Ver combinações e critérios**, consulte as 128 combinações e as áreas que contribuem para a família selecionada.
