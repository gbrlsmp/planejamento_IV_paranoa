"""Exporta quatro etapas adotadas e zoom detalhado da proxy final para o site.

As cores vêm do QML informado pela pesquisadora. O mapa detalhado usa blocos
PNG reprojetados para EPSG:3857 com amostragem pelo vizinho mais próximo;
cada bloco é carregado pelo navegador somente quando entra na vista.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image, ImageDraw, ImageFont
from paletas_identificacao import RISK_COLORS, qml_colors

gdal.UseExceptions()

STAGES = {
    1: "Cortes NDVI e limpeza campestre",
    2: "Diferença sazonal: classes 101 e 102",
    3: "Sobreposições e UCs de proteção integral",
    4: "Contexto ZEE-DF e resultado final",
}
LABELS = {
    3: "Formação florestal", 4: "Formação savânica",
    11: "Campo alagado e área pantanosa", 12: "Formação campestre", 33: "Água",
    100: "Vegetação intraurbana", 101: "Forração vegetal",
    102: "Impermeável ou solo exposto", 103: "Edificações",
}
RISK = RISK_COLORS
CHUNK = 2048


def palette(qml: Path):
    colors = qml_colors(qml)
    if set(LABELS) - set(colors):
        raise ValueError("QML sem todas as nove cores esperadas")
    lut = np.zeros((256, 4), dtype=np.uint8)
    for code, hex_color in colors.items():
        lut[code, :3] = tuple(bytes.fromhex(hex_color.lstrip("#")))
        lut[code, 3] = 255
    lut[255] = 0
    return colors, lut


def save_png(values: np.ndarray, lut: np.ndarray, path: Path):
    rgba = lut[values]
    image = Image.fromarray(rgba, "RGBA")
    image.save(path, optimize=True)
    return image


def warp_vrt(source: Path, bounds=None, width=None, height=None, xres=None):
    kwargs = dict(format="VRT", dstSRS="EPSG:3857", resampleAlg="near",
                  srcNodata=255, dstNodata=255, multithread=True)
    if bounds is not None:
        kwargs.update(outputBounds=bounds, width=width, height=height)
    elif xres is not None:
        kwargs.update(xRes=xres, yRes=xres)
    vrt = gdal.Warp("", str(source), **kwargs)
    if vrt is None:
        raise ValueError(f"Não foi possível reprojetar {source}")
    return vrt


def grid_bounds(vrt):
    gt = vrt.GetGeoTransform()
    return (gt[0], gt[3] + gt[5] * vrt.RasterYSize,
            gt[0] + gt[1] * vrt.RasterXSize, gt[3])


def stats(samples: Path):
    groups = {
        "florestal": "Formação Florestal", "savanica": "Formação Savânica",
        "campestre": "Formação Campestre", "pastagem": "Pastagem (comparação)",
        "campo_alagado": "Campo alagado e área pantanosa",
    }
    report = {"grupos": [], "campestre_pastagem": [], "checagem": []}
    with np.load(samples, allow_pickle=False) as data:
        for key, name in groups.items():
            d, w = data[key + "__seca"], data[key + "__chuva"]
            delta = w - d
            q = lambda v: [round(float(n), 3) for n in np.quantile(v, [.25, .5, .75])]
            report["grupos"].append({"id": key, "nome": name, "n": len(d),
                                     "seca": q(d), "chuva": q(w),
                                     "delta": q(delta)})
        for lower, upper in ((.30, .35), (.35, .40), (.40, .45)):
            row = {"seca": [lower, upper], "classes": {}}
            for key in ("campestre", "pastagem"):
                d, w = data[key + "__seca"], data[key + "__chuva"]
                inside = w[(d >= lower) & (d < upper)]
                row["classes"][key] = {"n": len(inside),
                                       "chuva": [round(float(v), 3)
                                                 for v in np.quantile(inside, [.25, .5, .75])]}
            report["campestre_pastagem"].append(row)
        for key in ("florestal", "savanica", "campestre", "pastagem", "campo_alagado"):
            d, w = data[key + "__seca"], data[key + "__chuva"]
            x, y = data[key + "__x"], data[key + "__y"]
            test = ((np.floor(x / 4000).astype("i8") * 73856093
                     + np.floor(y / 4000).astype("i8") * 19349663) % 5) == 0
            code = np.full(len(d), 100, dtype="u1")
            code[(d >= .20) & (d < .46) & (w >= .38) & (w < .62)] = 12
            code[(d >= .48) & (d < .70) & ((d+w)/2 >= .58)] = 4
            code[d >= .70] = 3
            counts = {str(value): int(np.count_nonzero(code[test] == value))
                      for value in (3, 4, 12, 100)}
            report["checagem"].append({"id": key, "nome": groups[key],
                                       "n": int(test.sum()), "contagens": counts})
    report["nota"] = ("Amostras de mapas históricos, separadas em blocos de 4 km; "
                     "checagem exploratória, não validação independente de campo.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raster-dir", type=Path,
                        help="Pasta dos quatro rasters nomeados etapa_01 a etapa_04")
    parser.add_argument("--stages-dir", type=Path,
                        help="Rasters das etapas 01-03 criados pelo script consolidado")
    parser.add_argument("--final-raster", type=Path,
                        help="GeoTIFF final da etapa 04 criado pelo script consolidado")
    parser.add_argument("--risk", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--qml", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if args.raster_dir and not (args.stages_dir or args.final_raster):
        directory = args.raster_dir.resolve()
        sources = {i: directory / f"fitofisionomias_proxy_ndvi_3m_etapa_0{i}.tif"
                   for i in STAGES}
    elif args.stages_dir and args.final_raster and not args.raster_dir:
        directory = args.stages_dir.resolve()
        sources = {i: directory / f"fitofisionomias_proxy_ndvi_3m_etapa_0{i}.tif"
                   for i in range(1, 4)}
        sources[4] = args.final_raster.resolve()
    else:
        parser.error("Informe --raster-dir ou --stages-dir com --final-raster")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Pasta de publicação não vazia")
    output.mkdir(parents=True, exist_ok=True)
    tile_dir = output / "blocos_3m"
    tile_dir.mkdir()
    colors, lut = palette(args.qml)
    for path in (*sources.values(), args.risk, args.samples, args.qml):
        if not path.is_file():
            raise FileNotFoundError(path)

    detailed = warp_vrt(sources[4], xres=3)
    high_bounds = grid_bounds(detailed)
    cols = math.ceil((high_bounds[2]-high_bounds[0])/20)
    rows = math.ceil((high_bounds[3]-high_bounds[1])/20)
    with gdal.Open(str(sources[1])) as first:
        residual_rgba = first.GetRasterBand(1).GetRasterColorTable().GetColorEntry(100)
    first_lut = lut.copy()
    first_lut[100] = residual_rgba
    residual_color = "#" + bytes(residual_rgba[:3]).hex()
    overview_images = []
    stages = []
    overview_bounds = high_bounds
    for version, name in STAGES.items():
        vrt = warp_vrt(sources[version], overview_bounds, cols, rows)
        values = vrt.ReadAsArray().astype("u1")
        filename = f"etapa_0{version}.png"
        stage_lut = first_lut if version == 1 else lut
        overview_images.append(save_png(values, stage_lut, output / filename))
        legend = [{"code": code, "name": label, "color": colors[code]}
                  for code, label in LABELS.items() if code in values]
        if version == 1:
            for entry in legend:
                if entry["code"] == 100:
                    entry.update(name="Classe residual", color=residual_color)
        stages.append({"version": version, "name": name, "image": filename, "legend": legend})
        vrt = None

    risk_projected = output / "risco_reprojetado.incompleto.gpkg"
    projected = gdal.VectorTranslate(str(risk_projected), str(args.risk),
                                     format="GPKG", dstSRS="EPSG:3857")
    if projected is None or projected.GetLayer(0).GetFeatureCount() == 0:
        raise ValueError("Falha ao reprojetar ZEE-DF")
    projected = None
    risk_raster = gdal.GetDriverByName("MEM").Create("", cols, rows, 1, gdal.GDT_Byte)
    left, bottom, right, top = overview_bounds
    risk_raster.SetGeoTransform((left, (right-left)/cols, 0, top, 0,
                                -(top-bottom)/rows))
    risk_raster.SetProjection("EPSG:3857")
    gdal.Rasterize(risk_raster, str(risk_projected),
                   options=gdal.RasterizeOptions(attribute="risco", allTouched=True))
    risk_lut = np.zeros((256, 4), dtype="u1")
    for code, (_, color) in RISK.items():
        risk_lut[code, :3] = tuple(bytes.fromhex(color[1:]))
        risk_lut[code, 3] = 230
    save_png(risk_raster.ReadAsArray().astype("u1"), risk_lut,
             output / "contexto_zee.png")
    risk_raster = None
    risk_projected.unlink()

    # O GIF mostra a mesma área em todas as etapas; o seletor do mapa permite
    # pausar e consultar cada quadro sem depender da animação.
    frames = []
    for version, image in enumerate(overview_images, 1):
        frame = image.copy()
        frame.thumbnail((760, 760), Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (frame.width, frame.height + 44), "#ffffff")
        canvas.alpha_composite(frame, (0, 44))
        ImageDraw.Draw(canvas).text((14, 12),
                                    f"{version}. {STAGES[version]}",
                                    fill="#24382d", font=ImageFont.load_default())
        frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE,
                                     colors=64))
    frames[0].save(output / "refinamento.gif", save_all=True,
                   append_images=frames[1:], duration=1500, loop=0,
                   optimize=True, disposal=2)

    blocks = []
    width, height = detailed.RasterXSize, detailed.RasterYSize
    gt = detailed.GetGeoTransform()
    for y in range(0, height, CHUNK):
        for x in range(0, width, CHUNK):
            w, h = min(CHUNK, width-x), min(CHUNK, height-y)
            values = detailed.GetRasterBand(1).ReadAsArray(x, y, w, h).astype("u1")
            if np.all(values == 255):
                continue
            filename = f"{x}_{y}.png"
            save_png(values, lut, tile_dir / filename)
            blocks.append({"file": "blocos_3m/"+filename,
                           "bounds": [gt[0]+x*gt[1],
                                      gt[3]+(y+h)*gt[5],
                                      gt[0]+(x+w)*gt[1],
                                      gt[3]+y*gt[5]]})
    manifest = {
        "format": "EPSG:3857 image overlays",
        "overview_bounds": overview_bounds,
        "overview_resolution_m": [(right-left)/cols, (top-bottom)/rows],
        "detail_resolution_mercator_m": 3,
        "detail_native_grid_m": 3,
        "detail_min_zoom": 14,
        "stages": stages,
        "blocks": blocks,
        "context": {"image": "contexto_zee.png",
                    "legend": [{"code": k, "name": n, "color": c}
                               for k, (n, c) in RISK.items()]},
        "classes": [{"code": code, "name": name, "color": colors[code]}
                    for code, name in LABELS.items()],
        "note": ("Visão geral reamostrada para cerca de 20 m; blocos locais "
                 "reprojetados para EPSG:3857 a 3 m com vizinho mais próximo. "
                 "Áreas úmidas têm detalhe temático de 10 m da fonte."),
    }
    (output / "manifesto.json").write_text(json.dumps(manifest, ensure_ascii=False,
                                                  separators=(",", ":")), encoding="utf-8")
    (output / "exploracoes_adicionais.json").write_text(
        json.dumps(stats(args.samples), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(json.dumps({"output": str(output), "blocks": len(blocks),
                      "overview": [cols, rows], "detail": [width, height]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
