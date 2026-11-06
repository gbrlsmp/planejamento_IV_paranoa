"""Exporta comparativos e mapas de temperatura/HM sem modificar os rasters v6.

Requer GDAL, NumPy e Pillow (disponíveis no Python do QGIS).
python scripts/exportar_cenarios_climaticos.py --source-dir CAMINHO/InVEST/v6
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from osgeo import gdal
from PIL import Image
from clima_comum import complete, sha256


SOURCES = {
    "temperatura": {
        "dia": "T_air_bacia_paranoa_v6_factors.tif",
        "noite": "T_air_bacia_paranoa_v6_intenssity.tif",
        "media": "v6 - algebra/T_air_bacia_paranoa_v6_media.tif",
    },
    "hm": {
        "dia": "hm_bacia_paranoa_v6_factors.tif",
        "noite": "hm_bacia_paranoa_v6_intenssity.tif",
        "media": "v6 - algebra/hm_bacia_paranoa_v6_media.tif",
    },
}
COLORS = {
    "temperatura": ["#365b95", "#83bdc1", "#f4e7a0", "#ef9653", "#a52d3e"],
    "hm": ["#f4deb5", "#c0d6b6", "#70b7a3", "#328777", "#145342"],
}


def ramp(colors):
    stops = np.array([[int(color[i:i + 2], 16) for i in (1, 3, 5)] for color in colors])
    return np.rint(np.column_stack([
        np.interp(np.linspace(0, 4, 255), np.arange(5), stops[:, channel])
        for channel in range(3)
    ])).astype(np.uint8)


def valid_values(dataset, y, rows):
    band = dataset.GetRasterBand(1)
    values = band.ReadAsArray(0, y, dataset.RasterXSize, rows).astype(np.float64)
    valid = np.isfinite(values) & (band.GetMaskBand().ReadAsArray(0, y, dataset.RasterXSize, rows) != 0)
    return values, valid


def statistics(datasets):
    """Lê todas as células originais; comparações usam a mesma máscara válida."""
    reference = next(iter(datasets.values()))
    transform = reference.GetGeoTransform()
    cell_area = abs(transform[1] * transform[5] - transform[2] * transform[4])
    records = {}
    for key, dataset in datasets.items():
        if (dataset.RasterXSize, dataset.RasterYSize, dataset.GetGeoTransform(), dataset.GetProjection()) != (
            reference.RasterXSize, reference.RasterYSize, transform, reference.GetProjection()
        ):
            raise ValueError("As seis camadas precisam compartilhar a grade original.")
        low, high = dataset.GetRasterBand(1).ComputeRasterMinMax(False)
        if not (math.isfinite(low) and math.isfinite(high) and high > low):
            raise ValueError(f"Camada sem amplitude válida para cinco intervalos: {key}")
        records[key] = {
            "minimum": low, "maximum": high,
            "cuts": np.linspace(low, high, 6).tolist(),
            "valid_pixels": 0, "sum": 0.0, "common_sum": 0.0,
            "class_counts": np.zeros(5, dtype=np.int64),
        }
    common_count = 0
    differences = {name: {"sum": 0.0, "minimum": math.inf, "maximum": -math.inf}
                   for name in ("temperatura_dia_menos_noite", "hm_noite_menos_dia")}
    residuals = {name: 0.0 for name in SOURCES}
    for y in range(0, reference.RasterYSize, 256):
        rows = min(256, reference.RasterYSize - y)
        chunk = {key: valid_values(dataset, y, rows) for key, dataset in datasets.items()}
        common = np.logical_and.reduce([valid for _, valid in chunk.values()])
        common_count += int(common.sum())
        for key, (values, valid) in chunk.items():
            record = records[key]
            selected = values[valid]
            record["valid_pixels"] += len(selected)
            record["sum"] += float(selected.sum(dtype=np.float64))
            record["common_sum"] += float(values[common].sum(dtype=np.float64))
            record["class_counts"] += np.bincount(
                np.searchsorted(record["cuts"][1:-1], selected, side="left"), minlength=5,
            )
        if not common.any():
            continue
        for indicator in SOURCES:
            day, night, mean = [chunk[(indicator, scenario)][0][common] for scenario in ("dia", "noite", "media")]
            difference = day - night if indicator == "temperatura" else night - day
            record = differences["temperatura_dia_menos_noite" if indicator == "temperatura" else "hm_noite_menos_dia"]
            record["sum"] += float(difference.sum(dtype=np.float64))
            record["minimum"] = min(record["minimum"], float(difference.min()))
            record["maximum"] = max(record["maximum"], float(difference.max()))
            residuals[indicator] = max(residuals[indicator], float(np.abs(mean - (day + night) / 2).max()))
    if not common_count:
        raise ValueError("Não há células válidas comuns às seis camadas.")
    if residuals["temperatura"] > 2e-6 or residuals["hm"] > 1e-7:
        raise ValueError("As camadas médias não correspondem a (dia + noite) / 2 na tolerância de ponto flutuante.")
    for record in records.values():
        record["mean"] = record.pop("sum") / record["valid_pixels"]
        record["common_mean"] = record.pop("common_sum") / common_count
        record["class_percent"] = (100 * record["class_counts"] / record["valid_pixels"]).tolist()
        record["class_area_ha"] = (cell_area / 10000 * record["class_counts"]).tolist()
        record["class_counts"] = record["class_counts"].tolist()
    for record in differences.values():
        record["mean"] = record.pop("sum") / common_count
    return records, {
        "common_valid_pixels": common_count,
        "common_area_ha": common_count * cell_area / 10000,
        "differences": differences, "maximum_absolute_mean_residual": residuals,
    }


def save_palette(indices, colors, path):
    image = Image.fromarray(indices).convert("P")
    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[1:len(colors) + 1] = colors
    image.putpalette(palette.ravel().tolist())
    image.save(path, transparency=0, optimize=True)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "dados-mapas/clima")
    parser.add_argument("--resolution", type=float, default=20, help="Passo de visualização em EPSG:3857; não altera as estatísticas.")
    args = parser.parse_args()
    if args.resolution <= 0:
        parser.error("--resolution precisa ser positiva")
    gdal.UseExceptions()
    datasets = {(indicator, scenario): gdal.Open(str(args.source_dir / filename), gdal.GA_ReadOnly)
                for indicator, scenarios in SOURCES.items() for scenario, filename in scenarios.items()}
    records, comparison = statistics(datasets)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    catalog = {
        "version": 1, "source_resolution_m": 3,
        "visualization": {"crs": "EPSG:3857", "resolution": args.resolution, "resampling": "nearest", "continuous_colors": 255},
        "classification": {"intervals": 5, "method": "equal_interval", "boundary": "lower_numeric_interval", "rounding": "display_only"},
        "comparison": comparison, "indicators": {},
    }
    grid = None
    for indicator, scenarios in SOURCES.items():
        low = min(records[(indicator, scenario)]["minimum"] for scenario in scenarios)
        high = max(records[(indicator, scenario)]["maximum"] for scenario in scenarios)
        config = {"range": [low, high], "colors": COLORS[indicator], "scenarios": {}}
        catalog["indicators"][indicator] = config
        for scenario, filename in scenarios.items():
            dataset = datasets[(indicator, scenario)]
            projected = gdal.Warp("", dataset, format="MEM", dstSRS="EPSG:3857",
                                  xRes=args.resolution, yRes=args.resolution, resampleAlg="near",
                                  outputType=gdal.GDT_Float64, dstNodata=np.nan)
            values = projected.ReadAsArray()
            valid = np.isfinite(values)
            x, dx, _, y, _, dy = projected.GetGeoTransform()
            current_grid = [x, y + dy * projected.RasterYSize, x + dx * projected.RasterXSize, y]
            if grid is not None and grid != current_grid:
                raise ValueError("Extensões de visualização diferentes")
            grid = current_grid
            record = records[(indicator, scenario)]
            record["source"] = filename
            record["source_sha256"] = sha256(args.source_dir / filename)
            record["continuous"] = f"{indicator}-{scenario}-continuo.png"
            record["classes"] = f"{indicator}-{scenario}-classes.png"
            record["preview"] = f"{indicator}-{scenario}-previa.png"
            config["scenarios"][scenario] = record
            indices = np.zeros(values.shape, dtype=np.uint8)
            indices[valid] = 1 + np.rint(254 * np.clip((values[valid] - low) / (high - low), 0, 1)).astype(np.uint8)
            image = save_palette(indices, ramp(COLORS[indicator]), args.out_dir / record["continuous"])
            image.thumbnail((560, 560), Image.Resampling.NEAREST)
            image.save(args.out_dir / record["preview"], transparency=0, optimize=True)
            indices[valid] = 1 + np.searchsorted(record["cuts"][1:-1], values[valid], side="left").astype(np.uint8)
            colors = np.array([[int(color[i:i + 2], 16) for i in (1, 3, 5)] for color in COLORS[indicator]], dtype=np.uint8)
            save_palette(indices, colors, args.out_dir / record["classes"])
            catalog["visualization"]["size"] = [projected.RasterXSize, projected.RasterYSize]
            projected = None
            print(f"Exportado: {indicator}/{scenario}", flush=True)
    catalog["bounds_3857"] = grid
    complete(catalog)
    (args.out_dir / "catalogo.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
