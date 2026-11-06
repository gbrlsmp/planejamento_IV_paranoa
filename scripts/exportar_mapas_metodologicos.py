"""Exporta imagens dos demais indicadores de Riscos para os quadros metodológicos.

Usa as classes já publicadas em mapa-dados.json.gz, sem reclassificar resultados.
Requer GDAL, NumPy e Pillow. As fontes são abertas em modo de leitura.
"""
import argparse
import gzip
import json
import math
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image


SITE = Path(__file__).resolve().parents[1]
MISSING = "#a9afb4"
CONFIG = {
    "icu": ("Ilha de calor urbano", None, "icu", "", ["não", "sim"], ["#c8e4da", "#d34536"]),
    "umid_pct": ("Umidade relativa", "umid_pct", "umid_cls", "%", ["muito baixo", "médio baixo", "médio", "alto"], ["#d8eaf7", "#8cc4e5", "#3b8abe", "#155687"]),
    "inund_max": ("Profundidade máxima de inundação · TR5", "inund_max", "inund_cls", "m", ["muito baixa", "baixa", "média", "alta"], ["#d8eaf7", "#8cc4e5", "#3b8abe", "#155687"]),
    "edif_pct": ("Pressão de edificações", "edif_pct", "edif_cls", "%", ["inexistente", "baixa", "média", "alta"], ["#dfe5e1", "#f7d497", "#ed9452", "#aa3e31"]),
    "renda_sm": ("Contexto de renda", "renda_sm", "renda_cls", "SM", ["até 1 SM", ">1 a 3 SM", ">3 a 6 SM", ">6 a 9 SM", ">9 SM"], ["#f1e9f7", "#d4bfe5", "#ae86c7", "#8151a4", "#502b77"]),
}


def decode(encoded):
    points, xy, cursor = [], [0, 0], 0
    while cursor < len(encoded):
        for axis in range(2):
            value = shift = 0
            while True:
                if cursor >= len(encoded) or shift > 30:
                    raise ValueError("Geometria publicada inválida")
                unit = ord(encoded[cursor]) - 63
                cursor += 1
                value |= (unit & 31) << shift
                shift += 5
                if unit < 32:
                    break
            xy[axis] += -(value >> 1) - 1 if value & 1 else value >> 1
        points.append([xy[0] / 100000, xy[1] / 100000])
    if points and points[-1] != points[0]:
        points.append(points[0])
    return points


def grid(layer, step):
    left, right, bottom, top = layer.GetExtent()
    width, height = math.ceil((right - left) / step), math.ceil((top - bottom) / step)
    ds = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Float64)
    ds.SetGeoTransform((left, step, 0, top, 0, -step))
    ds.SetSpatialRef(layer.GetSpatialRef())
    ds.GetRasterBand(1).Fill(float("nan"))
    return ds


def bounds(ds):
    x, dx, _, y, _, dy = ds.GetGeoTransform()
    return [x, y + dy * ds.RasterYSize, x + dx * ds.RasterXSize, y]


def palette_image(indices, colors, path):
    image = Image.fromarray(indices).convert("P")
    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[1:len(colors) + 1] = colors
    palette[255] = [int(MISSING[i:i + 2], 16) for i in (1, 3, 5)]
    image.putpalette(palette.ravel().tolist())
    image.save(path, transparency=0, optimize=True)


def ramp(colors):
    rgb = np.array([[int(color[i:i + 2], 16) for i in (1, 3, 5)] for color in colors])
    return np.rint(np.column_stack([
        np.interp(np.linspace(0, len(colors) - 1, 254), np.arange(len(colors)), rgb[:, i])
        for i in range(3)
    ])).astype(np.uint8)


def continuous(values, valid, extent, colors, path, missing=None):
    if not valid.any():
        raise ValueError(f"Sem valores numéricos válidos: {path.name}")
    low, high = extent
    if not high > low:
        raise ValueError(f"Sem amplitude numérica: {path.name}")
    indices = np.zeros(values.shape, dtype=np.uint8)
    indices[valid] = 1 + np.rint(253 * np.clip((values[valid] - low) / (high - low), 0, 1)).astype(np.uint8)
    if missing is not None:
        indices[missing] = 255
    palette_image(indices, ramp(colors), path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, required=True, help="Pasta local 01_Riscos")
    parser.add_argument("--resolution", type=float, default=20, help="Passo de visualização em EPSG:3857")
    args = parser.parse_args()
    if not args.resolution > 0:
        parser.error("A resolução precisa ser positiva")
    gdal.UseExceptions()
    out = SITE / "dados-mapas/metodologia-riscos"
    out.mkdir(exist_ok=True)
    published = json.loads(gzip.decompress((SITE / "mapa-dados.json.gz").read_bytes()))
    catalog = json.loads((SITE / "dados-mapas/contexto-riscos.json").read_text(encoding="utf-8"))
    positions = {name: index for index, name in enumerate(published["fields"])}
    features = []
    counts = {key: {} for key in CONFIG}
    for polygons, values in published["rows"]:
        props = {}
        for key, (_, field, category, _, labels, _) in CONFIG.items():
            label = values[positions[category]]
            counts[key][label] = counts[key].get(label, 0) + 1
            if label not in labels and label not in (None, "sem dados"):
                raise ValueError(f"Classe publicada inesperada: {key}/{label}")
            props["c_" + key] = labels.index(label) + 1 if label in labels else 255
            if field:
                value = values[positions[field]]
                props["v_" + key] = value if isinstance(value, (int, float)) and math.isfinite(value) else -999999
        features.append({"type": "Feature", "properties": props, "geometry": {
            "type": "MultiPolygon", "coordinates": [[decode(ring) for ring in polygon] for polygon in polygons],
        }})
    dataset = gdal.VectorTranslate("", json.dumps({"type": "FeatureCollection", "features": features}), format="MEM", dstSRS="EPSG:3857")
    layer = dataset.GetLayer(0)
    target = grid(layer, args.resolution)
    result = {"resolution_3857": args.resolution, "resampling": "nearest_or_cell_center", "indicators": {}}
    for key, (title, field, category, unit, labels, colors) in CONFIG.items():
        config = {"title": title, "unit": unit, "colors": colors, "counts": counts[key]}
        result["indicators"][key] = config
        src = catalog[key]
        config["source"] = {"title": src["title"], "note": src["note"], "classes": {
            "image": "dados-mapas/contexto/" + key + ".png", "bounds": src["bounds"], "entries": src["classes"],
        }}
        target.GetRasterBand(1).Fill(0)
        gdal.RasterizeLayer(target, [1], layer, options=["ATTRIBUTE=c_" + key])
        codes = target.ReadAsArray().astype(np.uint8)
        file = key + "-fragmentos-classes.png"
        palette_image(codes, np.array([[int(color[i:i + 2], 16) for i in (1, 3, 5)] for color in colors]), out / file)
        entries = [[i + 1, label, color] for i, (label, color) in enumerate(zip(labels, colors))] + [[255, "Sem dados", MISSING]]
        config["fragments"] = {"title": title + (" (" + unit + ")" if unit else ""),
            "note": "Classes registradas no diagnóstico publicado por fragmento, rodada v01.",
            "classes": {"image": "dados-mapas/metodologia-riscos/" + file, "bounds": bounds(target), "entries": entries}}
        if field:
            target.GetRasterBand(1).Fill(float("nan"))
            gdal.RasterizeLayer(target, [1], layer, options=["ATTRIBUTE=v_" + key])
            values = target.ReadAsArray()
            valid = (codes > 0) & np.isfinite(values) & (values != -999999)
            file = key + "-fragmentos-continuo.png"
            extent = published["ranges"][field]
            continuous(values, valid, extent, colors, out / file, (codes > 0) & ~valid)
            config["fragments"]["continuous"] = {"image": "dados-mapas/metodologia-riscos/" + file, "bounds": bounds(target), "range": extent}
        if src["kind"] in ("raster", "income"):
            path = args.base_dir / src["input"]
            if src["kind"] == "raster":
                original = gdal.Open(str(path), gdal.GA_ReadOnly)
                extent = original.GetRasterBand(1).ComputeRasterMinMax(False)
                projected = gdal.Warp("", original, format="MEM", dstSRS="EPSG:3857", xRes=args.resolution,
                                      yRes=args.resolution, resampleAlg="near", outputType=gdal.GDT_Float64, dstNodata=float("nan"))
                values = projected.ReadAsArray()
            else:
                projected_vector = gdal.VectorTranslate("", str(path), format="MEM", dstSRS="EPSG:3857")
                income = projected_vector.GetLayer(0)
                income.SetAttributeFilter("RENDA_STATUS = 'disponivel' AND V06004 >= 0")
                projected = grid(income, args.resolution)
                gdal.RasterizeLayer(projected, [1], income, options=["ATTRIBUTE=V06004"])
                values = projected.ReadAsArray() / 1212
                extent = [float(values[np.isfinite(values)].min()), float(values[np.isfinite(values)].max())]
            file = key + "-entrada-continuo.png"
            continuous(values, np.isfinite(values), extent, colors, out / file)
            config["source"]["continuous"] = {"image": "dados-mapas/metodologia-riscos/" + file, "bounds": bounds(projected), "range": list(extent)}
        print(f"Exportado: {key}", flush=True)
    (SITE / "dados-mapas/metodologia-riscos.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
