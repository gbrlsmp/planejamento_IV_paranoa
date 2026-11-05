"""Resume a camada de potencial de recuperação ecológica em CSV."""

import argparse
import csv
import sys
from collections import defaultdict

from osgeo import gdal, osr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("camada", help="Shapefile de PRE recortado à bacia, em EPSG:31983.")
    args = parser.parse_args()

    gdal.UseExceptions()
    dataset = gdal.OpenEx(args.camada, gdal.OF_VECTOR | gdal.OF_READONLY)
    layer = dataset.GetLayer(0)
    esperado = osr.SpatialReference()
    esperado.ImportFromEPSG(31983)
    crs = layer.GetSpatialRef()
    if crs is None or not crs.IsSame(esperado):
        parser.error("A camada deve estar em SIRGAS 2000 / UTM 23S (EPSG:31983).")
    if layer.GetLayerDefn().GetFieldIndex("cat_pdot20") == -1:
        parser.error("A camada deve ter o campo cat_pdot20.")

    totais = defaultdict(lambda: [0, 0.0])
    for feicao in layer:
        classe = feicao.GetField("cat_pdot20")
        geometria = feicao.GetGeometryRef()
        if not classe or geometria is None or geometria.IsEmpty():
            parser.error(f"Classe ou geometria ausente na feição {feicao.GetFID()}.")
        total = totais[classe]
        total[0] += 1
        total[1] += geometria.GetArea() / 10_000

    saida = csv.writer(sys.stdout, delimiter=";", lineterminator="\n")
    saida.writerow(["cat_pdot20", "poligonos", "area_ha"])
    for classe, (poligonos, area_ha) in sorted(totais.items()):
        saida.writerow([classe, poligonos, f"{area_ha:.6f}"])


if __name__ == "__main__":
    main()
