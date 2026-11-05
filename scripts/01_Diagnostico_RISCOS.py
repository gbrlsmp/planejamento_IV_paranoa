# -*- coding: utf-8 -*-
"""
Diagnóstico por fragmento — executar no editor Python do QGIS.

Preserva identificador, atributos e geometrias originais.
Trabalha em memória e grava somente os resultados finais.
Não sobrescreve resultados existentes.
"""

from os import environ
from pathlib import Path
from datetime import datetime
from math import isfinite
import json
import re

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    NULL,
    Qgis,
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsMemoryProviderUtils,
    QgsSpatialIndex,
    QgsUnitTypes,
    QgsVectorFileWriter,
    QgsWkbTypes,
)
from qgis.analysis import QgsZonalStatistics


# ============================================================
# 1. CONFIGURAÇÃO — ENTRADAS, SAÍDA E CRITÉRIOS
# ============================================================

BASE_CONFIGURADA = environ.get("PARANOA_BASE_DADOS")
if not BASE_CONFIGURADA:
    raise RuntimeError("Defina PARANOA_BASE_DADOS com a pasta 02 BASE DE DADOS.")
BASE = Path(BASE_CONFIGURADA).expanduser()
RISCOS = BASE / "02_Análises/01_Riscos"

INVEST = RISCOS / "01_Clima/04_rasters/InVEST/v6"
INVEST_MEDIA = INVEST / "v6 - algebra"
INMET = (
    RISCOS
    / "01_Clima/04_rasters/Completo_20261103_143519_903343"
)

VETORES = {
    "fragmentos": (
        BASE
        / "02_Análises/03_Ecologia/01_Fragmentação"
        / "MK_Fragmentation_Bacia_Paranoa_45m_PatchMetrics.shp"
    ),
    "icu": (
        RISCOS / "01_Clima/01_vetores/Zona_ICU.shp"
    ),
    "edificacoes": (
        RISCOS / "04_Pressão Urbana"
        / "Construções Bacia do Paranoá.shp"
    ),
    "renda": (
        RISCOS / "02_Social/01_vetores"
        / "Bacia_Paranoa_setores_renda_Censo2022.gpkg"
    ),
    "ras": (
        BASE / "01_Base/vetores/01_Limites"
        / "RAs_Bacia_Paranoa_MERGE_IPE_DF_2023.shp"
    ),
}

# Associação adotada para os cenários:
# factors = dia; intensity = noite.
# Os nomes abaixo preservam a grafia dos arquivos existentes.
ARQUIVOS_RASTER = {
    "temp_dia": (
        INVEST / "T_air_bacia_paranoa_v6_factors.tif"
    ),
    "temp_noite": (
        INVEST / "T_air_bacia_paranoa_v6_intenssity.tif"
    ),
    "temp_media": (
        INVEST_MEDIA / "T_air_bacia_paranoa_v6_media.tif"
    ),
    "hm_dia": (
        INVEST / "hm_bacia_paranoa_v6_factors.tif"
    ),
    "hm_noite": (
        INVEST / "hm_bacia_paranoa_v6_intenssity.tif"
    ),
    "hm_media": (
        INVEST_MEDIA / "hm_bacia_paranoa_v6_media.tif"
    ),
    "umid_pct": (
        INMET / "Completo_umidade_relativa_media_pct.tif"
    ),
    "inundacao": (
        RISCOS / "03_Água/01_raster"
        / "inundacao_profundidade_TR5_hidro.tif"
    ),
}

CAMPO_ID = "patch_id"

CAMADA_RENDA = "recortado"
CAMPO_RENDA = "V06004"             # Média do responsável.
CAMPO_SETOR = "CD_SETOR"
CAMPO_STATUS_RENDA = "RENDA_STATUS"
SALARIO_MINIMO = 1212.00           # Referência nominal: 2022.

CAMPO_RA_NOME = "ra_nome"
CAMPO_RA_CODIGO = "ra_codigo"

# Saída e identificação do teste.
PASTA_SAIDA = RISCOS / "05_Diagnostico"
PREFIXO = "Diagnostico_RISCOS"
SUFIXO = "v01"
FORMATO = "gpkg"                   # "shp" ou "gpkg".
SALVAR_PARAMETROS = True

# Aplicado EXCLUSIVAMENTE ao HM.
DISTANCIA_ENTORNO_M = 5.0

# Utilizado somente nos cálculos geométricos.
# A saída conserva o CRS original dos fragmentos.
CRS_CALCULO = "EPSG:31983"         # SIRGAS 2000 / UTM 23S.

# ICU:
# "intersecao": sim quando houver sobreposição com área.
# "contido": sim somente quando o fragmento inteiro estiver na zona.
REGRA_ICU = "intersecao"

# Inundação: classificar pela profundidade "max" ou "media".
ESTATISTICA_INUNDACAO = "max"

# Edificações: proposta inicial ajustável.
# 0%                          -> inexistente
# >0 até primeiro corte       -> baixa
# >primeiro até segundo corte -> média
# >segundo corte              -> alta
CORTES_EDIFICACAO = (100.0 / 3.0, 200.0 / 3.0)

# None: calcular mínimo e máximo entre os valores dos fragmentos.
# Para fixar uma referência entre testes, informar (mínimo, máximo).
#
# Dia, noite e média da temperatura têm limites independentes.
LIMITES_TEMPERATURA = {
    "temp_dia": None,
    "temp_noite": None,
    "temp_media": None,
}
LIMITES_UMIDADE = None
LIMITES_INUNDACAO = None


# ============================================================
# 2. FUNÇÕES
# ============================================================

PROJETO = QgsProject.instance()
CRS_METRICO = QgsCoordinateReferenceSystem(CRS_CALCULO)
ESTAT = getattr(Qgis, "ZonalStatistic", QgsZonalStatistics)

CAMPOS_TEMPERATURA = {
    "temp_dia": "td_classe",
    "temp_noite": "tn_classe",
    "temp_media": "tm_classe",
}
CAMPOS_HM = ("hm_dia", "hm_noite", "hm_media")

ROTULOS_TEMPERATURA = [
    "base", "boa", "média", "ruim", "muito ruim"
]
ROTULOS_UMIDADE = [
    "muito baixo", "médio baixo", "médio", "alto"
]
ROTULOS_INUNDACAO = [
    "muito baixa", "baixa", "média", "alta"
]


def numero(valor):
    """Mantém dados ausentes como None."""
    if valor is None or valor == NULL:
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None
    return valor if isfinite(valor) else None


def texto(valor):
    if valor is None or valor == NULL:
        return None
    return str(valor)


def carregar_vetor(caminho, nome, subcamada=None):
    uri = str(caminho)
    if subcamada:
        uri += f"|layername={subcamada}"

    camada = QgsVectorLayer(uri, nome, "ogr")
    if not camada.isValid() or not camada.crs().isValid():
        raise ValueError(f"Vetor inválido ou sem CRS: {uri}")
    if camada.geometryType() != QgsWkbTypes.PolygonGeometry:
        raise ValueError(f"A camada deve conter polígonos: {nome}")
    return camada


def geometria_metrica(feicao, transformar, origem):
    """Copia a geometria para cálculo, sem alterar o original."""
    geometria = QgsGeometry(feicao.geometry())
    if geometria.isNull() or geometria.isEmpty():
        raise ValueError(
            f"Geometria vazia em {origem}, feição {feicao.id()}."
        )

    geometria.transform(transformar)
    area = geometria.area()
    if (
        not geometria.isGeosValid()
        or not isfinite(area)
        or area <= 0
    ):
        raise ValueError(
            f"Geometria inválida em {origem}, feição {feicao.id()}. "
            "Verifique a geometria antes de executar novamente."
        )
    return geometria


def preparar_indice(camada, campos=()):
    """Indexa cópias das geometrias no CRS métrico."""
    for campo in campos:
        if campo not in camada.fields().names():
            raise ValueError(
                f"Campo ausente em {camada.name()}: {campo}"
            )

    indice = QgsSpatialIndex(
        flags=QgsSpatialIndex.FlagStoreFeatureGeometries
    )
    dados = {}
    transformar = QgsCoordinateTransform(
        camada.crs(), CRS_METRICO, PROJETO
    )
    pedido = QgsFeatureRequest().setSubsetOfAttributes(
        list(campos), camada.fields()
    )

    for feicao in camada.getFeatures(pedido):
        geometria = geometria_metrica(
            feicao, transformar, camada.name()
        )
        copia = QgsFeature()
        copia.setId(feicao.id())
        copia.setGeometry(geometria)

        if not indice.addFeature(copia):
            raise RuntimeError(
                f"Falha ao indexar {camada.name()}, "
                f"feição {feicao.id()}."
            )

        if campos:
            dados[feicao.id()] = {
                campo: feicao[campo] for campo in campos
            }

    return indice, dados


def intersecoes(geometria, indice):
    """Contato de borda, sem área, não entra no resultado."""
    for identificador in sorted(
        indice.intersects(geometria.boundingBox())
    ):
        recorte = geometria.intersection(
            indice.geometry(identificador)
        )
        if recorte.isNull() and recorte.lastError():
            raise RuntimeError(recorte.lastError())
        if not recorte.isEmpty() and recorte.area() > 0:
            yield identificador, recorte


def unir_recortes(recortes):
    uniao = QgsGeometry.unaryUnion(recortes)
    if uniao.isNull() or uniao.lastError():
        raise RuntimeError(
            f"Falha na união dos recortes: {uniao.lastError()}"
        )
    return uniao


def ilha_calor(geometria, indice):
    if REGRA_ICU == "intersecao":
        return next(intersecoes(geometria, indice), None) is not None

    recortes = [
        recorte for _, recorte in intersecoes(geometria, indice)
    ]
    if not recortes:
        return False

    restante = geometria.difference(unir_recortes(recortes))
    if restante.isNull() and restante.lastError():
        raise RuntimeError(restante.lastError())

    tolerancia = max(1e-6, geometria.area() * 1e-12)
    return restante.isEmpty() or restante.area() <= tolerancia


def percentual_ocupado(geometria, indice):
    recortes = [
        recorte for _, recorte in intersecoes(geometria, indice)
    ]
    if not recortes:
        return 0.0

    # União evita contar sobreposições mais de uma vez.
    area = unir_recortes(recortes).area()
    percentual = 100.0 * area / geometria.area()
    return min(100.0, max(0.0, percentual))


def dominante(geometria, indice, dados):
    """Escolhe o polígono com maior área de sobreposição."""
    resultado = max(
        intersecoes(geometria, indice),
        key=lambda item: item[1].area(),
        default=None,
    )
    if resultado is None:
        return None, None

    identificador, recorte = resultado
    percentual = min(
        100.0, 100.0 * recorte.area() / geometria.area()
    )
    return dados[identificador], percentual


def extrair_raster(nome, geometria, flags):
    raster, transformar = RASTERS[nome]
    copia = QgsGeometry(geometria)
    copia.transform(transformar)

    return QgsZonalStatistics.calculateStatistics(
        raster.dataProvider(),
        copia,
        abs(raster.rasterUnitsPerPixelX()),
        abs(raster.rasterUnitsPerPixelY()),
        1,
        flags,
    )


def media_raster(nome, geometria):
    resultado = extrair_raster(nome, geometria, ESTAT.Mean)
    return numero(resultado.get(ESTAT.Mean))


def classe_edificacao(percentual):
    if percentual == 0:
        return "inexistente"
    if percentual <= CORTES_EDIFICACAO[0]:
        return "baixa"
    if percentual <= CORTES_EDIFICACAO[1]:
        return "média"
    return "alta"


def classificar_renda(valor):
    if valor is None:
        return None, "sem dados"

    salarios = valor / SALARIO_MINIMO
    for teto, classe in (
        (1, "até 1 SM"),
        (3, ">1 a 3 SM"),
        (6, ">3 a 6 SM"),
        (9, ">6 a 9 SM"),
    ):
        if salarios <= teto:
            return salarios, classe
    return salarios, ">9 SM"


def criar_limites(camada, campos, quantidade, fixos=None):
    if fixos is not None:
        minimo, maximo = map(float, fixos)
        if (
            not all(map(isfinite, (minimo, maximo)))
            or minimo >= maximo
        ):
            raise ValueError(f"Limites fixos inválidos: {campos}")
    else:
        valores = (
            numero(feicao[campo])
            for feicao in camada.getFeatures()
            for campo in campos
        )
        valores = [
            valor for valor in valores if valor is not None
        ]
        if not valores:
            return None
        minimo, maximo = min(valores), max(valores)

    passo = (maximo - minimo) / quantidade
    limites = [
        minimo + passo * i for i in range(quantidade + 1)
    ]
    limites[-1] = maximo
    return limites


def classe_intervalo(valor, limites, rotulos):
    """Intervalos [a, b); o máximo pertence à última classe."""
    valor = numero(valor)
    if valor is None or limites is None:
        return "sem dados"
    if limites[0] == limites[-1]:
        return "sem variação"
    if valor < limites[0] or valor > limites[-1]:
        return "fora da faixa"

    for i, superior in enumerate(limites[1:]):
        if valor < superior:
            return rotulos[i]
    return rotulos[-1]


def adicionar_lote(provedor, lote):
    if lote:
        sucesso, _ = provedor.addFeatures(lote)
        if not sucesso:
            raise RuntimeError(
                "Falha ao adicionar resultados em memória."
            )
        lote.clear()


# ============================================================
# 3. VALIDAÇÃO E LEITURA
# ============================================================

for caminho in [
    *VETORES.values(),
    *ARQUIVOS_RASTER.values(),
]:
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}"
        )

if (
    not CRS_METRICO.isValid()
    or CRS_METRICO.mapUnits() != QgsUnitTypes.DistanceMeters
):
    raise ValueError("O CRS de cálculo deve ser válido e usar metros.")
if (
    not isfinite(DISTANCIA_ENTORNO_M)
    or DISTANCIA_ENTORNO_M <= 0
):
    raise ValueError("A distância do entorno deve ser positiva.")
if not isfinite(SALARIO_MINIMO) or SALARIO_MINIMO <= 0:
    raise ValueError("Salário mínimo inválido.")
if not (
    0 < CORTES_EDIFICACAO[0] < CORTES_EDIFICACAO[1] < 100
):
    raise ValueError("Cortes de edificações inválidos.")
if REGRA_ICU not in ("intersecao", "contido"):
    raise ValueError("REGRA_ICU deve ser 'intersecao' ou 'contido'.")
if ESTATISTICA_INUNDACAO not in ("max", "media"):
    raise ValueError("Use 'max' ou 'media' para a inundação.")
if FORMATO not in ("shp", "gpkg"):
    raise ValueError("FORMATO deve ser 'shp' ou 'gpkg'.")

if not re.fullmatch(r"[A-Za-z0-9_-]+", PREFIXO):
    raise ValueError(
        "Prefixo: use letras sem acento, números, '_' ou '-'."
    )
if SUFIXO and not re.fullmatch(r"[A-Za-z0-9_-]+", SUFIXO):
    raise ValueError("Sufixo inválido.")

TESTE = "_".join(
    parte for parte in (PREFIXO, SUFIXO) if parte
)
if len(TESTE) > 64:
    raise ValueError(
        "Prefixo e sufixo, juntos, devem ter até 64 caracteres."
    )

NOME_SAIDA = f"{TESTE}_diagnostico"
ARQUIVO_SAIDA = PASTA_SAIDA / f"{NOME_SAIDA}.{FORMATO}"
ARQUIVO_PARAMETROS = (
    PASTA_SAIDA / f"{NOME_SAIDA}_parametros.json"
)

if (
    any(PASTA_SAIDA.glob(f"{NOME_SAIDA}.*"))
    or ARQUIVO_PARAMETROS.exists()
):
    raise FileExistsError(
        "Já existe um resultado com este nome. "
        "Troque o prefixo ou o sufixo."
    )

fragmentos = carregar_vetor(
    VETORES["fragmentos"], "fragmentos"
)
if CAMPO_ID not in fragmentos.fields().names():
    raise ValueError(f"Identificador ausente: {CAMPO_ID}")
if fragmentos.featureCount() == 0:
    raise ValueError("A camada de fragmentos está vazia.")

icu = carregar_vetor(VETORES["icu"], "zona_icu")
edificacoes = carregar_vetor(
    VETORES["edificacoes"], "edificacoes"
)
renda = carregar_vetor(
    VETORES["renda"], "renda", CAMADA_RENDA
)
ras = carregar_vetor(VETORES["ras"], "regioes_administrativas")

RASTERS = {}
for nome, caminho in ARQUIVOS_RASTER.items():
    raster = QgsRasterLayer(str(caminho), nome)
    if (
        not raster.isValid()
        or not raster.crs().isValid()
        or raster.bandCount() < 1
    ):
        raise ValueError(
            f"Raster inválido ou sem CRS: {caminho}"
        )

    RASTERS[nome] = (
        raster,
        QgsCoordinateTransform(
            CRS_METRICO, raster.crs(), PROJETO
        ),
    )

for nome in CAMPOS_HM:
    raster = RASTERS[nome][0]
    if raster.crs().mapUnits() == QgsUnitTypes.DistanceMeters:
        pixel = max(
            abs(raster.rasterUnitsPerPixelX()),
            abs(raster.rasterUnitsPerPixelY()),
        )
        if pixel > DISTANCIA_ENTORNO_M:
            print(
                f"ATENÇÃO: o pixel de {nome} é maior que "
                "a largura do entorno. A resolução original "
                "será preservada."
            )
    else:
        print(
            f"Confira a resolução espacial de {nome} "
            "em relação à largura do entorno."
        )

print("Preparando índices espaciais em memória...")

indice_icu, _ = preparar_indice(icu)
indice_edificacoes, _ = preparar_indice(edificacoes)
indice_renda, dados_renda = preparar_indice(
    renda,
    (CAMPO_SETOR, CAMPO_RENDA, CAMPO_STATUS_RENDA),
)
indice_ra, dados_ra = preparar_indice(
    ras,
    (CAMPO_RA_NOME, CAMPO_RA_CODIGO),
)


# ============================================================
# 4. CAMPOS DE SAÍDA
# ============================================================

# Nomes de até dez caracteres para compatibilidade com shapefile.
textos = {
    "teste": 64,
    "icu": 8,
    "ra_nome": 100,
    "ra_codigo": 20,
    "td_classe": 32,
    "tn_classe": 32,
    "tm_classe": 32,
    "umid_cls": 32,
    "inund_cls": 32,
    "edif": 8,
    "edif_cls": 32,
    "setor": 20,
    "renda_cls": 32,
    "renda_st": 40,
}
numericos = (
    "ra_pct",
    "temp_dia", "temp_noite", "temp_media",
    "umid_pct",
    "hm_dia", "hm_noite", "hm_media",
    "inund_med", "inund_max",
    "edif_pct",
    "setor_pct", "renda_rs", "renda_sm",
)

novos_campos = [
    QgsField(nome, QVariant.String, "", tamanho)
    for nome, tamanho in textos.items()
]
novos_campos += [
    QgsField(nome, QVariant.Double, "", 24, 10)
    for nome in numericos
]

originais = {
    nome.lower() for nome in fragmentos.fields().names()
}
conflitos = [
    campo.name()
    for campo in novos_campos
    if campo.name().lower() in originais
]
if conflitos:
    raise ValueError(
        f"Campos já existentes na entrada: {conflitos}"
    )

campos = QgsFields(fragmentos.fields())
for campo in novos_campos:
    campos.append(campo)

saida = QgsMemoryProviderUtils.createMemoryLayer(
    NOME_SAIDA,
    campos,
    fragmentos.wkbType(),
    fragmentos.crs(),
)
if not saida.isValid():
    raise RuntimeError("Falha ao criar a camada em memória.")

provedor = saida.dataProvider()
transformar_fragmentos = QgsCoordinateTransform(
    fragmentos.crs(), CRS_METRICO, PROJETO
)


# ============================================================
# 5. CÁLCULO POR FRAGMENTO
# ============================================================

ids_vistos = set()
lote = []
processados = 0

for feicao in fragmentos.getFeatures():
    identificador = feicao[CAMPO_ID]
    if identificador is None or identificador == NULL:
        raise ValueError("Há fragmento sem identificador.")
    if identificador in ids_vistos:
        raise ValueError(
            f"Identificador repetido: {identificador}. "
            "É necessário um identificador único por fragmento."
        )
    ids_vistos.add(identificador)

    geometria = geometria_metrica(
        feicao,
        transformar_fragmentos,
        f"fragmento {identificador}",
    )

    valores = {"teste": TESTE}

    # Temperatura: somente no interior do fragmento.
    # A média usa o raster médio existente, sem recalculá-lo.
    for campo in CAMPOS_TEMPERATURA:
        valores[campo] = media_raster(campo, geometria)

    # Umidade: somente o raster pronto derivado do INMET.
    umidade = media_raster("umid_pct", geometria)
    if umidade is not None and not 0 <= umidade <= 100:
        raise ValueError(
            f"Umidade fora de 0–100% no fragmento {identificador}."
        )
    valores["umid_pct"] = umidade

    # Inundação: média e máximo dentro do fragmento.
    inundacao = extrair_raster(
        "inundacao", geometria, ESTAT.Mean | ESTAT.Max
    )
    valores["inund_med"] = numero(
        inundacao.get(ESTAT.Mean)
    )
    valores["inund_max"] = numero(
        inundacao.get(ESTAT.Max)
    )
    if (
        valores["inund_max"] is not None
        and valores["inund_max"] < 0
    ):
        raise ValueError(
            f"Profundidade negativa no fragmento {identificador}."
        )

    # EXCLUSIVAMENTE o HM usa a faixa externa.
    entorno = geometria.buffer(
        DISTANCIA_ENTORNO_M, 8
    ).difference(geometria)

    if (
        entorno.isNull()
        or entorno.isEmpty()
        or not entorno.isGeosValid()
    ):
        raise ValueError(
            f"Entorno inválido no fragmento {identificador}."
        )

    for campo in CAMPOS_HM:
        valor = media_raster(campo, entorno)
        if valor is not None and not -1e-6 <= valor <= 1 + 1e-6:
            raise ValueError(
                f"{campo} fora de 0–1 no fragmento {identificador}."
            )
        valores[campo] = valor

    # ICU: apenas sim/não.
    valores["icu"] = (
        "sim" if ilha_calor(geometria, indice_icu) else "não"
    )

    # Edificações: ocupação no interior, sem dupla contagem.
    ocupacao = percentual_ocupado(
        geometria, indice_edificacoes
    )
    valores.update({
        "edif": "sim" if ocupacao > 0 else "não",
        "edif_pct": ocupacao,
        "edif_cls": classe_edificacao(ocupacao),
    })

    # Região administrativa de maior sobreposição.
    ra, ra_pct = dominante(geometria, indice_ra, dados_ra)
    valores.update({
        "ra_nome": (
            texto(ra[CAMPO_RA_NOME]) if ra else None
        ),
        "ra_codigo": (
            texto(ra[CAMPO_RA_CODIGO]) if ra else None
        ),
        "ra_pct": ra_pct,
    })

    # Renda do setor censitário de maior sobreposição.
    # Um setor com dado suprimido não é substituído por outro.
    setor, setor_pct = dominante(
        geometria, indice_renda, dados_renda
    )
    renda_rs = (
        numero(setor[CAMPO_RENDA]) if setor else None
    )
    renda_status = (
        texto(setor[CAMPO_STATUS_RENDA])
        if setor else "sem setor"
    )

    if renda_rs is not None and renda_rs < 0:
        renda_rs = None
        renda_status = "valor inválido"

    renda_sm, renda_classe = classificar_renda(renda_rs)
    valores.update({
        "setor": (
            texto(setor[CAMPO_SETOR]) if setor else None
        ),
        "setor_pct": setor_pct,
        "renda_rs": renda_rs,
        "renda_sm": renda_sm,
        "renda_cls": renda_classe,
        "renda_st": renda_status,
    })

    resultado = QgsFeature(saida.fields())
    resultado.setGeometry(feicao.geometry())
    resultado.setAttributes(
        feicao.attributes()
        + [
            valores.get(campo.name())
            for campo in novos_campos
        ]
    )
    lote.append(resultado)
    processados += 1

    if len(lote) >= 500:
        adicionar_lote(provedor, lote)
        print(f"{processados} fragmentos processados.")

adicionar_lote(provedor, lote)
saida.updateExtents()

if saida.featureCount() != processados:
    raise RuntimeError(
        "A quantidade de resultados ficou inconsistente."
    )


# ============================================================
# 6. CLASSIFICAÇÕES POR INTERVALOS IGUAIS
# ============================================================

# Temperatura: limites independentes por cenário.
limites_temperatura = {
    origem: criar_limites(
        saida,
        [origem],
        len(ROTULOS_TEMPERATURA),
        LIMITES_TEMPERATURA[origem],
    )
    for origem in CAMPOS_TEMPERATURA
}

limites_umidade = criar_limites(
    saida,
    ["umid_pct"],
    len(ROTULOS_UMIDADE),
    LIMITES_UMIDADE,
)

campo_inundacao = (
    "inund_max"
    if ESTATISTICA_INUNDACAO == "max"
    else "inund_med"
)
limites_inundacao = criar_limites(
    saida,
    [campo_inundacao],
    len(ROTULOS_INUNDACAO),
    LIMITES_INUNDACAO,
)

classificacoes = {
    destino: (
        origem,
        limites_temperatura[origem],
        ROTULOS_TEMPERATURA,
    )
    for origem, destino in CAMPOS_TEMPERATURA.items()
}
classificacoes.update({
    "umid_cls": (
        "umid_pct",
        limites_umidade,
        ROTULOS_UMIDADE,
    ),
    "inund_cls": (
        campo_inundacao,
        limites_inundacao,
        ROTULOS_INUNDACAO,
    ),
})

alteracoes = {}
for feicao in saida.getFeatures():
    alteracoes[feicao.id()] = {
        saida.fields().indexFromName(destino): classe_intervalo(
            feicao[origem], limites, rotulos
        )
        for destino, (origem, limites, rotulos)
        in classificacoes.items()
    }

    if len(alteracoes) >= 500:
        if not provedor.changeAttributeValues(alteracoes):
            raise RuntimeError(
                "Falha ao atualizar as classificações."
            )
        alteracoes.clear()

if alteracoes and not provedor.changeAttributeValues(alteracoes):
    raise RuntimeError(
        "Falha ao finalizar as classificações."
    )

# ============================================================
# 7. GRAVAÇÃO DOS RESULTADOS FINAIS
# ============================================================

# A criação de arquivos começa somente aqui.
PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

opcoes = QgsVectorFileWriter.SaveVectorOptions()
opcoes.driverName = (
    "ESRI Shapefile" if FORMATO == "shp" else "GPKG"
)
opcoes.fileEncoding = "UTF-8"
opcoes.layerName = NOME_SAIDA

erro = QgsVectorFileWriter.writeAsVectorFormatV3(
    saida,
    str(ARQUIVO_SAIDA),
    PROJETO.transformContext(),
    opcoes,
)
if erro[0] != QgsVectorFileWriter.NoError:
    raise RuntimeError(f"Falha ao gravar a saída: {erro}")

verificacao = QgsVectorLayer(
    str(ARQUIVO_SAIDA), NOME_SAIDA, "ogr"
)
campos_esperados = {
    CAMPO_ID, *[campo.name() for campo in novos_campos]
}
if (
    not verificacao.isValid()
    or verificacao.featureCount() != processados
    or not campos_esperados.issubset(
        verificacao.fields().names()
    )
):
    raise RuntimeError(
        "A conferência da camada gravada falhou."
    )

if SALVAR_PARAMETROS:
    registro = {
        "teste": TESTE,
        "data_execucao": datetime.now().astimezone().isoformat(),
        "qgis": Qgis.QGIS_VERSION,
        "quantidade_fragmentos": processados,
        "campo_id": CAMPO_ID,
        "vetores": {
            nome: str(caminho)
            for nome, caminho in VETORES.items()
        },
        "rasters": {
            nome: str(caminho)
            for nome, caminho in ARQUIVOS_RASTER.items()
        },
        "saida": str(ARQUIVO_SAIDA),
        "crs_calculo": CRS_CALCULO,
        "icu": {
            "regra": REGRA_ICU,
            "saida": "somente sim ou não",
        },
       "temperatura": {
    "estatistica": "média no interior do fragmento",
    "cortes_compartilhados": False,
    "limites_por_cenario": limites_temperatura,
    "rotulos": ROTULOS_TEMPERATURA,
        },
        "hm": {
            "estatistica": "média na faixa externa",
            "distancia_m": DISTANCIA_ENTORNO_M,
            "interior_do_fragmento": "excluído",
            "classificacao": "não definida; manter valores",
        },
        "umidade": {
            "fonte": "raster pronto derivado do INMET",
            "limites": limites_umidade,
            "rotulos": ROTULOS_UMIDADE,
        },
        "inundacao": {
            "tempo_retorno_anos": 5,
            "estatistica": ESTATISTICA_INUNDACAO,
            "limites": limites_inundacao,
            "rotulos": ROTULOS_INUNDACAO,
        },
        "edificacoes": {
            "cortes_percentuais": list(CORTES_EDIFICACAO),
            "sobreposicoes": "contadas uma única vez",
        },
        "ra": {
            "metodo": "maior área de sobreposição",
            "campo_nome": CAMPO_RA_NOME,
            "campo_codigo": CAMPO_RA_CODIGO,
        },
        "renda": {
            "camada": CAMADA_RENDA,
            "campo": CAMPO_RENDA,
            "metodo": "setor de maior área de sobreposição",
            "indicador": "renda do responsável como proxy",
            "salario_minimo_reais": SALARIO_MINIMO,
            "ano_referencia": 2022,
        },
        "sem_dados": "NULL numérico; não convertido em zero",
    }

    with ARQUIVO_PARAMETROS.open("x", encoding="utf-8") as arquivo:
        json.dump(
            registro, arquivo, ensure_ascii=False, indent=2
        )

PROJETO.addMapLayer(verificacao)
print(f"Concluído: {processados} fragmentos.")
print(f"Saída: {ARQUIVO_SAIDA}")
