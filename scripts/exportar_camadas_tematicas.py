"""Gera uma camada temática PNG para o mapa, com limites em Web Mercator."""

import argparse
import json
from pathlib import Path

import numpy as np
from osgeo import gdal, osr


RESOLUCAO = 50
CAMPOS = {"uso": "classe", "metricas": "Area", "pre": "cat_pdot20"}
ROTULOS_PRE = ("BAIXO", "MÉDIO", "ALTO", "MUITO ALTO")


def srs(codigo):
    ref = osr.SpatialReference()
    ref.ImportFromEPSG(codigo)
    ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return ref


def rasterizar(tema, dados, classes):
    camada = dados.GetLayer(0)
    crs = camada.GetSpatialRef()
    if crs is None:
        raise ValueError("A camada vetorial precisa ter um sistema de coordenadas definido.")
    if not crs.IsSame(srs(31983)):
        dados = gdal.VectorTranslate("", dados, format="Memory", dstSRS="EPSG:31983")
        camada = dados.GetLayer(0)
    xmin, xmax, ymin, ymax = camada.GetExtent()
    passo = RESOLUCAO
    grade = gdal.GetDriverByName("MEM").Create(
        "", int(np.ceil((xmax - xmin) / passo)), int(np.ceil((ymax - ymin) / passo)), 1,
        gdal.GDT_Byte,
    )
    grade.SetGeoTransform((xmin, passo, 0, ymax, 0, -passo))
    grade.SetSpatialRef(srs(31983))
    grade.GetRasterBand(1).SetNoDataValue(0)
    campo = CAMPOS[tema]
    if tema == "uso":
        filtros = [(codigo, f'"{campo}" % 100 = {codigo}') for codigo, _, _ in classes]
    elif tema == "pre":
        filtros = [
            (codigo, f'"{campo}" = \'{rotulo} POTENCIAL DE RECUPERAÇÃO ECOLÓGICA\'')
            for codigo, rotulo in enumerate(ROTULOS_PRE, 1)
        ]
    else:
        filtros = [
            (1, f'"{campo}" <= 10000'),
            (2, f'"{campo}" > 10000 AND "{campo}" <= 100000'),
            (3, f'"{campo}" > 100000 AND "{campo}" <= 1000000'),
            (4, f'"{campo}" > 1000000'),
        ]
    for codigo, filtro in filtros:
        camada.SetAttributeFilter(filtro)
        if not camada.GetFeatureCount():
            raise ValueError(f"Classe {codigo} sem feições. Verifique a camada de {tema}.")
        gdal.RasterizeLayer(grade, [1], camada, burn_values=[codigo])
    return grade


def preparar(tema, entrada, classes):
    gdal.UseExceptions()
    dados = gdal.OpenEx(entrada)
    origem = dados if tema == "momentos" else rasterizar(tema, dados, classes)
    destino = gdal.Warp(
        "", origem, format="MEM", dstSRS=srs(3857).ExportToWkt(),
        xRes=RESOLUCAO, yRes=RESOLUCAO, resampleAlg="near", dstNodata=0,
    )
    banda = destino.GetRasterBand(1)
    contagens = np.bincount(banda.ReadAsArray().ravel())
    tabela = gdal.ColorTable()
    tabela.SetColorEntry(0, (0, 0, 0, 0))
    for codigo, _, cor in classes:
        if codigo >= len(contagens) or not contagens[codigo]:
            raise ValueError(f"Classe {codigo} ausente após a rasterização de {tema}.")
        canais = tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))
        tabela.SetColorEntry(codigo, (*canais, 255))
    banda.SetRasterColorTable(tabela)
    banda.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    x, dx, _, y, _, dy = destino.GetGeoTransform()
    limites = [x, y + dy * destino.RasterYSize, x + dx * destino.RasterXSize, y]
    return destino, limites


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tema", choices=("uso", "metricas", "momentos", "pre"))
    parser.add_argument("entrada")
    parser.add_argument("saida", help="Caminho do PNG de saída.")
    args = parser.parse_args()
    catalogo = Path(__file__).resolve().parents[1] / "dados-mapas" / "catalogo.json"
    classes = json.loads(catalogo.read_text(encoding="utf-8"))[args.tema]["classes"]
    destino, limites = preparar(args.tema, args.entrada, classes)
    gdal.GetDriverByName("PNG").CreateCopy(args.saida, destino, options=["ZLEVEL=9", "WORLDFILE=NO"])
    print(json.dumps(limites))


if __name__ == "__main__":
    main()
