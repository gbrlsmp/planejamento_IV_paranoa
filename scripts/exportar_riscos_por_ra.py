"""Resume os indicadores dos fragmentos por Região Administrativa."""

import argparse
import json
from collections import defaultdict
from math import isfinite

import shapely
from osgeo import gdal, osr
from shapely.strtree import STRtree


INDICADORES = [
    ("icu", "Ilha de calor urbano", None, "icu", "", ["não","sim"]),
    ("temp_dia", "Temperatura de dia", "temp_dia", "td_classe", "°C", ["base","boa","média","ruim","muito ruim"]),
    ("temp_noite", "Temperatura à noite", "temp_noite", "tn_classe", "°C", ["base","boa","média","ruim","muito ruim"]),
    ("temp_media", "Temperatura média", "temp_media", "tm_classe", "°C", ["base","boa","média","ruim","muito ruim"]),
    ("hm_dia", "Mitigação térmica de dia", "hm_dia", None, "", []),
    ("hm_noite", "Mitigação térmica à noite", "hm_noite", None, "", []),
    ("hm_media", "Mitigação térmica média", "hm_media", None, "", []),
    ("umid_pct", "Umidade relativa", "umid_pct", "umid_cls", "%", ["muito baixo","médio baixo","médio","alto"]),
    ("inund_max", "Profundidade máxima de inundação no fragmento · TR de 5 anos", "inund_max", "inund_cls", "", ["muito baixa","baixa","média","alta"]),
    ("inund_med", "Profundidade média de inundação no fragmento · TR de 5 anos", "inund_med", None, "", []),
    ("edif_pct", "Pressão de edificações", "edif_pct", "edif_cls", "%", ["inexistente","baixa","média","alta"]),
    ("edif", "Presença de edificações", None, "edif", "", ["não","sim"]),
    ("renda_sm", "Contexto de renda em salários mínimos", "renda_sm", "renda_cls", "SM", ["até 1 SM",">1 a 3 SM",">3 a 6 SM",">6 a 9 SM",">9 SM"]),
    ("renda_rs", "Contexto de renda em reais", "renda_rs", None, "R$", []),
]
TOLERANCIA_AREA_M2 = 0.01


def abrir(caminho, campos, reprojetar=False):
    dados = gdal.OpenEx(caminho, gdal.OF_VECTOR | gdal.OF_READONLY)
    camada = dados.GetLayer(0)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(31983)
    crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    atual = camada.GetSpatialRef()
    if atual is None:
        raise ValueError(f"Sistema de coordenadas ausente em {caminho}.")
    if not atual.IsSame(crs):
        if not reprojetar:
            raise ValueError(f"Use EPSG:31983 em {caminho}.")
        dados = gdal.VectorTranslate("", dados, format="MEM", dstSRS="EPSG:31983")
        camada = dados.GetLayer(0)
    faltantes = campos - {campo.GetName() for campo in camada.schema}
    if faltantes:
        raise ValueError(f"Campos ausentes em {caminho}: {', '.join(sorted(faltantes))}.")
    return dados, camada


def geometria(feicao):
    origem = feicao.GetGeometryRef()
    if origem is None:
        raise ValueError(f"Feição {feicao.GetFID()} sem geometria.")
    geo = shapely.from_wkb(bytes(origem.ExportToWkb()))
    if not geo.is_valid:
        geo = shapely.make_valid(geo)
    if geo.area <= 0:
        raise ValueError(f"Feição {feicao.GetFID()} sem área.")
    return geo


class Resumo:
    def __init__(self):
        self.area = 0.0
        self.soma = 0.0
        self.minimo = None
        self.maximo = None
        self.areas_classes = defaultdict(float)

    def acumular(self, valor, classe, area):
        if classe is not None:
            self.areas_classes[classe] += area
        if valor is not None:
            self.area += area
            self.soma += area * valor
            self.minimo = valor if self.minimo is None else min(self.minimo, valor)
            self.maximo = valor if self.maximo is None else max(self.maximo, valor)

    def exportar(self, numerico, classes, area):
        area_classes = sum(self.areas_classes.values())
        area_valida = self.area if numerico else area_classes
        resultado = {
            "cobertura": round(100 * area_valida / area, 4) if area else None,
        }
        if numerico:
            resultado.update(
                media=round(self.soma / self.area, 6) if self.area else None,
                minimo=round(self.minimo, 6) if self.area else None,
                maximo=round(self.maximo, 6) if self.area else None,
            )
        if classes:
            resultado["classes"] = [
                round(100 * self.areas_classes[classe] / area_classes, 4)
                if area_classes else None for classe in classes
            ]
        return resultado


def gerar(ra_path, bacia_path, frag_path):
    gdal.UseExceptions()
    dados_ra, camada_ra = abrir(ra_path, {"ra_cira", "ra_nome"})
    dados_bacia, camada_bacia = abrir(bacia_path, set(), reprojetar=True)
    bacia = shapely.union_all([geometria(feicao) for feicao in camada_bacia])
    if bacia.is_empty:
        raise ValueError("A camada da bacia está vazia.")
    shapely.prepare(bacia)
    campos = {campo for _, _, valor, classe, _, _ in INDICADORES for campo in (valor, classe) if campo}
    dados_frag, fragmentos = abrir(frag_path, campos | {"patch_id"})
    registros, poligonos = [], []
    codigos = set()
    for feicao in camada_ra:
        codigo, nome = feicao["ra_cira"], feicao["ra_nome"]
        if codigo is None or codigo in codigos or not nome:
            raise ValueError(f"Identificador ou nome inválido na feição {feicao.GetFID()}.")
        codigos.add(codigo)
        original = geometria(feicao)
        poligono = bacia.intersection(original)
        if poligono.area <= TOLERANCIA_AREA_M2:
            continue
        inteira = bacia.covers(original) or original.difference(bacia).area <= TOLERANCIA_AREA_M2
        registros.append({
            "codigo": codigo,
            "nome": nome,
            "inteira": inteira,
            "area": 0.0,
            "fragmentos": 0,
            "resumos": [Resumo() for _ in INDICADORES],
        })
        poligonos.append(poligono)
        shapely.prepare(poligono)
    if not registros:
        raise ValueError("A camada de RAs está vazia.")

    indice = STRtree(poligonos)
    vistos = set()
    for feicao in fragmentos:
        patch_id = feicao["patch_id"]
        if patch_id is None or patch_id in vistos:
            raise ValueError(f"Identificador ausente ou duplicado na feição {feicao.GetFID()}.")
        vistos.add(patch_id)
        geo = geometria(feicao)
        valores = []
        for _, _, campo, cat, _, classes in INDICADORES:
            valor = feicao[campo] if campo else None
            if valor is not None and not isfinite(valor):
                valor = None
            classe = feicao[cat] if cat else None
            if classe not in classes:
                classe = None
            valores.append((valor, classe))
        for pos in indice.query(geo, predicate="intersects"):
            poligono = poligonos[pos]
            area = geo.area if poligono.covers(geo) else poligono.intersection(geo).area
            if not area:
                continue
            reg = registros[pos]
            reg["area"] += area
            reg["fragmentos"] += 1
            for resumo, (valor, classe) in zip(reg["resumos"], valores):
                resumo.acumular(valor, classe, area)
    if not vistos:
        raise ValueError("A camada de fragmentos está vazia.")

    return {
        "indicadores": [
            {"id": id_, "titulo": titulo, "numerico": campo is not None, "unidade": unidade, "classes": classes}
            for id_, titulo, campo, _, unidade, classes in INDICADORES
        ],
        "regioes": [
            {
                "codigo": reg["codigo"], "nome": reg["nome"], "inteira": reg["inteira"],
                "area_ha": round(reg["area"] / 10_000, 6), "fragmentos": reg["fragmentos"],
                "indicadores": [
                    resumo.exportar(campo is not None, classes, reg["area"])
                    for resumo, (_, _, campo, _, _, classes) in zip(reg["resumos"], INDICADORES)
                ],
            }
            for reg in sorted(registros, key=lambda r: r["nome"])
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ras", required=True, help="Camada com as geometrias completas das RAs.")
    parser.add_argument("--bacia", required=True, help="Limite da Bacia do Paranoá.")
    parser.add_argument("--fragmentos", required=True, help="GeoPackage do diagnóstico de Riscos.")
    args = parser.parse_args()
    print(json.dumps(gerar(args.ras, args.bacia, args.fragmentos), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
