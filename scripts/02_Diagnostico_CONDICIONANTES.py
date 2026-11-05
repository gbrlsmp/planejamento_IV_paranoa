"""Resume Momentos da Água e Potencial de Recuperação Ecológica por fragmento."""

import argparse
import csv
import math
import sys

import numpy as np
import shapely
from osgeo import gdal, osr
from shapely.strtree import STRtree


MOMENTOS = {1: "fonte", 2: "conducao", 3: "acomodacao"}
CLASSES_PRE = {
    "MUITO ALTO": "muito_alto",
    "ALTO": "alto",
    "MÉDIO": "medio",
    "BAIXO": "baixo",
}
SUFIXO_PRE = " POTENCIAL DE RECUPERAÇÃO ECOLÓGICA"
BLOCO = 256


def verificar_crs(crs, nome):
    esperado = osr.SpatialReference()
    esperado.ImportFromEPSG(31983)
    esperado.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if crs is None or not crs.IsSame(esperado):
        raise ValueError(f"{nome} deve estar em SIRGAS 2000 / UTM 23S (EPSG:31983).")


def abrir_vetor(caminho, campo):
    dados = gdal.OpenEx(caminho, gdal.OF_VECTOR | gdal.OF_READONLY)
    camada = dados.GetLayer(0)
    verificar_crs(camada.GetSpatialRef(), caminho)
    if camada.GetLayerDefn().GetFieldIndex(campo) < 0:
        raise ValueError(f"Campo {campo} ausente em {caminho}.")
    return dados, camada


def geometria(feicao):
    original = feicao.GetGeometryRef()
    if original is None:
        raise ValueError(f"Geometria ausente na feição {feicao.GetFID()}.")
    poligono = shapely.from_wkb(bytes(original.ExportToWkb()))
    if not poligono.is_valid:
        poligono = shapely.make_valid(poligono)
    return poligono


def indexar_pre(camada, campo):
    geometrias, classes = [], []
    for feicao in camada:
        rotulo = str(feicao.GetField(campo)).strip().upper().removesuffix(SUFIXO_PRE)
        if rotulo not in CLASSES_PRE:
            raise ValueError(f"Classe de PRE desconhecida na feição {feicao.GetFID()}: {rotulo}")
        poligono = geometria(feicao)
        if poligono.area <= 0:
            raise ValueError(f"Polígono de PRE sem área na feição {feicao.GetFID()}.")
        geometrias.append(poligono)
        classes.append(CLASSES_PRE[rotulo])
    return STRtree(geometrias), np.array(classes)


def areas_pre(fragmento, indice, classes, tolerancia):
    candidatos = indice.query(fragmento, predicate="intersects")
    recortes = shapely.intersection(fragmento, indice.geometries[candidatos])
    classes_recortes = classes[candidatos]
    unioes = {
        classe: shapely.union_all(recortes[classes_recortes == classe])
        for classe in CLASSES_PRE.values()
    }
    areas = {classe: poligono.area for classe, poligono in unioes.items()}
    cobertura = shapely.union_all(list(unioes.values())).area
    sobreposicao = 0.0
    if sum(areas.values()) > cobertura + tolerancia:
        # A área disputada fica separada para não contar duas classes no mesmo local.
        areas = {
            classe: poligono.difference(
                shapely.union_all([outro for nome, outro in unioes.items() if nome != classe])
            ).area
            for classe, poligono in unioes.items()
        }
        sobreposicao = max(0.0, cobertura - sum(areas.values()))
    return areas, cobertura, sobreposicao


class RasterMomentos:
    def __init__(self, caminho):
        self.dados = gdal.OpenEx(caminho, gdal.OF_RASTER | gdal.OF_READONLY)
        verificar_crs(self.dados.GetSpatialRef(), caminho)
        self.x, self.dx, rx, self.y, ry, dy = self.dados.GetGeoTransform()
        if self.dx <= 0 or dy >= 0 or rx or ry or self.dados.RasterCount != 1:
            raise ValueError("Use um raster de Momentos com uma banda e grade alinhada ao norte.")
        self.dy = -dy
        self.banda = self.dados.GetRasterBand(1)
        self.mascara = self.banda.GetMaskBand()

    def areas(self, fragmento):
        xmin, ymin, xmax, ymax = fragmento.bounds
        col0 = max(0, math.floor((xmin - self.x) / self.dx))
        col1 = min(self.dados.RasterXSize, math.ceil((xmax - self.x) / self.dx))
        lin0 = max(0, math.floor((self.y - ymax) / self.dy))
        lin1 = min(self.dados.RasterYSize, math.ceil((self.y - ymin) / self.dy))
        totais = np.zeros(4)
        shapely.prepare(fragmento)
        for linha in range(lin0, lin1, BLOCO):
            for coluna in range(col0, col1, BLOCO):
                largura = min(BLOCO, col1 - coluna)
                altura = min(BLOCO, lin1 - linha)
                argumentos = coluna, linha, largura, altura
                dados = self.banda.ReadAsArray(*argumentos)
                validos = self.mascara.ReadAsArray(*argumentos) != 0
                if np.any(validos & ~np.isin(dados, list(MOMENTOS))):
                    raise ValueError("Raster de Momentos contém código válido diferente de 1, 2 ou 3.")
                valores = np.where(validos, dados, 0).astype(np.uint8)

                # Une células contíguas de mesmo código em faixas de uma linha.
                limites = np.pad(valores, ((0, 0), (1, 1)))
                mudou = limites[:, :-1] != limites[:, 1:]
                linhas, inicios = np.nonzero(mudou[:, :-1] & (valores != 0))
                _, fins = np.nonzero(mudou[:, 1:] & (valores != 0))
                x0 = self.x + (coluna + inicios) * self.dx
                x1 = self.x + (coluna + fins + 1) * self.dx
                y1 = self.y - (linha + linhas) * self.dy
                faixas = shapely.box(x0, y1 - self.dy, x1, y1)
                toca = shapely.intersects(fragmento, faixas)
                faixas = faixas[toca]
                dentro = shapely.covers(fragmento, faixas)
                areas = shapely.area(faixas)
                areas[~dentro] = shapely.area(shapely.intersection(fragmento, faixas[~dentro]))
                codigos = valores[linhas, inicios][toca]
                totais += np.bincount(codigos, weights=areas, minlength=4)
        return {classe: totais[codigo] for codigo, classe in MOMENTOS.items()}


def resumo(prefixo, areas, area_total, cobertura, tolerancia):
    def percentual(area):
        return round(100 * max(0.0, area) / area_total, 6)

    maior = max(areas.values())
    empatadas = [classe for classe, area in areas.items() if maior - area <= tolerancia]
    if maior <= tolerancia:
        predominante = ""
        situacao = "sem_dados" if cobertura <= tolerancia else "sem_classe_exclusiva"
    elif len(empatadas) > 1:
        predominante, situacao = "", "empate"
    else:
        predominante, situacao = empatadas[0], "definida"

    return {
        **{f"{prefixo}_pct_{classe}": percentual(area) for classe, area in areas.items()},
        f"{prefixo}_pct_sem_dados": percentual(area_total - cobertura),
        f"{prefixo}_predominante": predominante,
        f"{prefixo}_situacao": situacao,
    }


def cruzar(fragmentos, campo_id, momentos, indice_pre, classes_pre):
    vistos = set()
    for feicao in fragmentos:
        identificador = feicao.GetField(campo_id)
        if identificador is None or identificador == "" or identificador in vistos:
            raise ValueError(f"Identificador ausente ou duplicado na feição {feicao.GetFID()}.")
        vistos.add(identificador)
        fragmento = geometria(feicao)
        area = fragmento.area
        if area <= 0:
            raise ValueError(f"Fragmento {identificador} sem área.")
        tolerancia = max(1e-6, area * 1e-10)
        agua = momentos.areas(fragmento)
        pre, cobertura_pre, sobreposicao = areas_pre(fragmento, indice_pre, classes_pre, tolerancia)
        yield {
            "patch_id": identificador,
            "area_fragmento_m2": round(area, 6),
            **resumo("mom", agua, area, sum(agua.values()), tolerancia),
            **resumo("pre", pre, area, cobertura_pre, tolerancia),
            "pre_pct_sobreposicao": round(100 * sobreposicao / area, 6),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fragmentos", required=True, help="Camada vetorial de fragmentos.")
    parser.add_argument("--momentos", required=True, help="Raster momento_dominante.tif.")
    parser.add_argument("--pre", required=True, help="Camada vetorial de PRE.")
    parser.add_argument("--campo-id", default="patch_id")
    parser.add_argument("--campo-pre", default="cat_pdot20")
    args = parser.parse_args()

    gdal.UseExceptions()
    try:
        dados_fragmentos, fragmentos = abrir_vetor(args.fragmentos, args.campo_id)
        dados_pre, camada_pre = abrir_vetor(args.pre, args.campo_pre)
        indice, classes = indexar_pre(camada_pre, args.campo_pre)
        momentos = RasterMomentos(args.momentos)
        linhas = list(cruzar(fragmentos, args.campo_id, momentos, indice, classes))
        if not linhas:
            raise ValueError("A camada de fragmentos está vazia.")
    except (RuntimeError, ValueError, shapely.errors.GEOSException) as erro:
        parser.exit(1, f"Erro: {erro}\n")

    saida = csv.DictWriter(sys.stdout, fieldnames=linhas[0].keys(), delimiter=";", lineterminator="\n")
    saida.writeheader()
    saida.writerows(linhas)


if __name__ == "__main__":
    main()
