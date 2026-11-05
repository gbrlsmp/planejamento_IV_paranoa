"""Exporta as camadas de entrada de Riscos para visualização no mapa web."""

import argparse
import json
from pathlib import Path

import numpy as np
from osgeo import gdal


def grade_vetorial(origem, config):
    dados = gdal.VectorTranslate("", origem, format="MEM", dstSRS="EPSG:3857")
    camada = dados.GetLayer(0)
    xmin, xmax, ymin, ymax = camada.GetExtent()
    passo = config.get("resolution", 50)
    grade = gdal.GetDriverByName("MEM").Create(
        "", int(np.ceil((xmax - xmin) / passo)), int(np.ceil((ymax - ymin) / passo)), 1,
        gdal.GDT_Byte,
    )
    grade.SetGeoTransform((xmin, passo, 0, ymax, 0, -passo))
    grade.SetSpatialRef(camada.GetSpatialRef())
    if config["kind"] == "income":
        limites = [0, 1212, 3636, 7272, 10908, None]
        for i, (minimo, maximo) in enumerate(zip(limites, limites[1:]), 1):
            operador = ">=" if i == 1 else ">"
            filtro = f"V06004 {operador} {minimo} AND RENDA_STATUS = 'disponivel'"
            if maximo is not None:
                filtro += f" AND V06004 <= {maximo}"
            camada.SetAttributeFilter(filtro)
            gdal.RasterizeLayer(grade, [1], camada, burn_values=[i])
    else:
        opcoes = ["ALL_TOUCHED=TRUE"] if passo == 20 else []
        gdal.RasterizeLayer(grade, [1], camada, burn_values=[1], options=opcoes)
    return grade


def preparar(entrada, config):
    gdal.UseExceptions()
    origem = gdal.OpenEx(entrada, gdal.OF_READONLY)
    if config["kind"] == "raster":
        projetado = gdal.Warp(
            "", origem, format="MEM", dstSRS="EPSG:3857", xRes=50, yRes=50,
            resampleAlg="near", outputType=gdal.GDT_Float32, dstNodata=np.nan,
        )
        dados = projetado.ReadAsArray()
        validos = np.isfinite(dados)
        classes = np.zeros(dados.shape, dtype=np.uint8)
        classes[validos] = 1 + np.searchsorted(config["bins"], dados[validos], side="left")
        grade = gdal.GetDriverByName("MEM").Create(
            "", projetado.RasterXSize, projetado.RasterYSize, 1, gdal.GDT_Byte,
        )
        grade.SetGeoTransform(projetado.GetGeoTransform())
        grade.SetSpatialRef(projetado.GetSpatialRef())
        grade.GetRasterBand(1).WriteArray(classes)
    else:
        grade = grade_vetorial(origem, config)
        classes = grade.ReadAsArray()

    codigos = np.unique(classes)
    if not any(codigo > 0 for codigo in codigos):
        raise ValueError("A camada não contém pixels de dados.")
    tabela = gdal.ColorTable()
    tabela.SetColorEntry(0, (0, 0, 0, 0))
    for codigo, _, cor in config["classes"]:
        rgb = tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))
        tabela.SetColorEntry(codigo, (*rgb, 255))
    banda = grade.GetRasterBand(1)
    banda.SetRasterColorTable(tabela)
    banda.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    x, dx, _, y, _, dy = grade.GetGeoTransform()
    limites = [x, y + dy * grade.RasterYSize, x + dx * grade.RasterXSize, y]
    return grade, limites, codigos.tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("indicador")
    parser.add_argument("entrada")
    parser.add_argument("saida", help="Caminho do PNG de saída.")
    args = parser.parse_args()
    catalogo = Path(__file__).resolve().parents[1] / "dados-mapas/contexto-riscos.json"
    config = json.loads(catalogo.read_text(encoding="utf-8"))[args.indicador]
    grade, limites, _ = preparar(args.entrada, config)
    gdal.GetDriverByName("PNG").CreateCopy(args.saida, grade, options=["ZLEVEL=9"])
    print(json.dumps(limites))


if __name__ == "__main__":
    main()
