"""Recolore mapas de referência já calculados, sem refazer vetores ou NDVI."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from paletas_identificacao import ZEE_COLORS, qml_colors


def recolor(path: Path, legend):
    image = Image.open(path)
    if image.mode != "P":
        raise ValueError(f"Imagem de classes não paletizada: {path}")
    original = np.asarray(image).copy()
    palette = [0] * 768
    for item in legend:
        rgb = bytes.fromhex(item["cor"].lstrip("#"))
        palette[item["codigo"] * 3:item["codigo"] * 3 + 3] = rgb
    image.putpalette(palette)
    image.save(path, transparency=0, optimize=True)
    if not np.array_equal(np.asarray(Image.open(path)), original):
        raise ValueError(f"Código alterado ao recolorir {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", type=Path, required=True,
                        help="Pasta dados-mapas/identificacao no checkout")
    parser.add_argument("--mapbiomas-qml", type=Path, required=True)
    parser.add_argument("--final-qml", type=Path, required=True)
    args = parser.parse_args()
    mb_colors = qml_colors(args.mapbiomas_qml)
    final_colors = qml_colors(args.final_qml)
    refs_path, ndvi_path = args.web / "referencias.json", args.web / "exploracao.json"
    refs = json.loads(refs_path.read_text(encoding="utf-8"))
    ndvi = json.loads(ndvi_path.read_text(encoding="utf-8"))
    if refs["revisao"] != ndvi["revisao"]:
        raise ValueError("Referências e exploração de execuções diferentes")
    for item in refs["camadas"]["mapbiomas"]["legenda"]:
        item["cor"] = mb_colors.get(item["codigo"], "#c0a77a")
    for item in refs["camadas"]["zee"]["legenda"]:
        item["cor"] = ZEE_COLORS[item["nome"]]
    for item in refs["camadas"]["intersecao"]["legenda"]:
        group = next(x for x in ndvi["areas"] if x["nome"] == item["nome"])
        item["cor"] = final_colors[group["mapbiomas_codigo"]]
    for layer in ("mapbiomas", "zee", "intersecao"):
        recolor(args.web / f"{layer}.png", refs["camadas"][layer]["legenda"])
    for group in ndvi["grupos"].values():
        if group["nome"].startswith("Pastagem"):
            group["cor"] = mb_colors[15]
        else:
            match = next(x for x in ndvi["areas"] if x["nome"] == group["nome"])
            group["cor"] = mb_colors[match["mapbiomas_codigo"]]
    presentation = {
        "mapbiomas": args.mapbiomas_qml.name,
        "intersecao": args.final_qml.name,
        "zee": "paletas_identificacao.py, inspirada no QML MapBiomas",
        "nota": "O QML MapBiomas não inclui o código 36; lavoura perene usa #c0a77a.",
    }
    revision = hashlib.sha256((refs["revisao"] + json.dumps(presentation, sort_keys=True)
                               + json.dumps(refs["camadas"], sort_keys=True)).encode()).hexdigest()[:16]
    refs["revisao"] = ndvi["revisao"] = revision
    refs["apresentacao_cores"] = ndvi["apresentacao_cores"] = presentation
    refs_path.write_text(json.dumps(refs, ensure_ascii=False, indent=2), encoding="utf-8")
    ndvi_path.write_text(json.dumps(ndvi, ensure_ascii=False, separators=(",", ":")),
                         encoding="utf-8")
    print(json.dumps({"revisao": revision, "camadas": list(refs["camadas"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
