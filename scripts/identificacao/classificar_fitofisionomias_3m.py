"""Reproduz as quatro etapas adotadas da proxy em uma passagem pela grade de 3 m.

Entradas locais não são versionadas. Use --base para a pasta "02 BASE DE DADOS"
e --output para um GeoTIFF novo. --stages-dir grava também etapas 01-03.
Nenhuma classificação anterior é lida: as máscaras vetoriais só entram nas
etapas explicitadas abaixo; o NDVI é a única variável espectral usada.
"""

from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr

gdal.UseExceptions()
ogr.UseExceptions()

TILE = 512
NODATA = 255
RESIDUAL_COLOR = (232, 232, 232, 255)
PROTECTED_FILTER = "AVUs = 'UC' AND Grupo = 'UC - Proteção Integral'"
COLORS = {
    3: (75, 106, 64, 255), 4: (134, 165, 143, 255),
    11: (62, 89, 114, 255), 12: (208, 165, 95, 255),
    33: (166, 206, 227, 255), 100: (43, 81, 37, 255),
    101: (196, 204, 149, 255), 102: (225, 225, 225, 255),
    103: (57, 57, 57, 255), 255: (0, 0, 0, 0),
}


def paths(base: Path) -> dict[str, Path]:
    raster = base / "02_Análises/03_Ecologia/03_Fitofisionomia/03_Raster"
    return {
        "dry": raster / "02_NDVI/ndvi_seca_2026-07-30.tif",
        "wet": raster / "02_NDVI/ndvi_chuva_2026-01-17.tif",
        "map": raster / "01_MapBiomas_10m_2025/uso_e_corbertura_mapbiomas_10m_2025_bacia_paranoa.tif",
        "roads": base / "01_Base/vetores/Vias_OSM_Bacia_Paranoa.shp",
        "water": base / "01_Base/vetores/02_Água/Massa_Dagua_Bacia_Paranoa_MERGE_IPE_DF_2023.shp",
        "buildings": base / "02_Análises/01_Riscos/04_Pressão Urbana/Construções Bacia do Paranoá.shp",
        "protected": base / "01_Base/vetores/05_AVUs/AVUs_Bacia do Paranoá_Final.shp",
        "risk": base / "02_Análises/03_Ecologia/03_Fitofisionomia/01_vetor/risco_perda_veg_nativa_Bacia_Paranoa.shp",
    }


def check_inputs(inputs: dict[str, Path]):
    for key, path in inputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"{key}: {path}")
    dry = gdal.Open(str(inputs["dry"]), gdal.GA_ReadOnly)
    wet = gdal.Open(str(inputs["wet"]), gdal.GA_ReadOnly)
    mapbiomas = gdal.Open(str(inputs["map"]), gdal.GA_ReadOnly)
    if any(ds is None for ds in (dry, wet, mapbiomas)):
        raise ValueError("Raster de entrada indisponível")
    gt, wgt = dry.GetGeoTransform(), wet.GetGeoTransform()
    if (dry.RasterCount != 1 or wet.RasterCount != 1
            or dry.GetSpatialRef().GetAuthorityCode(None) != "31983"
            or wet.GetSpatialRef().GetAuthorityCode(None) != "31983"
            or mapbiomas.RasterCount < 1
            or mapbiomas.GetSpatialRef().GetAuthorityCode(None) != "4326"
            or (gt[1], gt[2], gt[4], gt[5]) != (3, 0, 0, -3)
            or (wgt[1], wgt[2], wgt[4], wgt[5]) != (3, 0, 0, -3)):
        raise ValueError("Grade, bandas ou CRS de entrada inesperados")
    sx = round((gt[0] - wgt[0]) / 3)
    sy = round((wgt[3] - gt[3]) / 3)
    if (abs(gt[0] - wgt[0] - 3 * sx) > 1e-6
            or abs(wgt[3] - gt[3] - 3 * sy) > 1e-6
            or sx < 0 or sy < 0
            or sx + dry.RasterXSize > wet.RasterXSize
            or sy + dry.RasterYSize > wet.RasterYSize):
        raise ValueError("NDVIs não compartilham a grade de 3 m")
    for key in ("roads", "water", "buildings", "risk", "protected"):
        ds = ogr.Open(str(inputs[key]))
        expected = "4326" if key == "buildings" else "31983"
        if ds is None or ds.GetLayer(0).GetSpatialRef().GetAuthorityCode(None) != expected:
            raise ValueError(f"CRS inesperado em {key}")
        if key == "risk":
            layer = ds.GetLayer(0)
            count = 0
            for feature in layer:
                if feature.GetField("risco") == 2:
                    if not feature.GetField("legenda").startswith("Ausência de Cerrado Nativo"):
                        raise ValueError("risco=2 não corresponde à ausência de Cerrado")
                    count += 1
            if not count:
                raise ValueError("Nenhum polígono risco=2")
        if key == "protected":
            layer = ds.GetLayer(0)
            layer.SetAttributeFilter(PROTECTED_FILTER)
            if layer.GetFeatureCount() == 0:
                raise ValueError("Nenhuma UC de proteção integral")
        ds = None
    return dry, wet, mapbiomas, sx, sy


def create_raster(path: Path, template, description: str, *, residual=False):
    ds = gdal.GetDriverByName("GTiff").Create(
        str(path), template.RasterXSize, template.RasterYSize, 1,
        gdal.GDT_Byte, options=["TILED=YES", "BLOCKXSIZE=512",
                                "BLOCKYSIZE=512", "COMPRESS=DEFLATE",
                                "ZLEVEL=6", "NUM_THREADS=4"])
    ds.SetGeoTransform(template.GetGeoTransform())
    ds.SetSpatialRef(template.GetSpatialRef())
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    band.SetDescription(description)
    table = gdal.ColorTable()
    for code, rgba in COLORS.items():
        table.SetColorEntry(code, RESIDUAL_COLOR if residual and code == 100 else rgba)
    band.SetRasterColorTable(table)
    band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    return ds


def create_mask(path: Path, template):
    ds = gdal.GetDriverByName("GTiff").Create(
        str(path), template.RasterXSize, template.RasterYSize, 1,
        gdal.GDT_Byte, options=["TILED=YES", "BLOCKXSIZE=512",
                                "BLOCKYSIZE=512", "COMPRESS=DEFLATE", "ZLEVEL=1"])
    ds.SetGeoTransform(template.GetGeoTransform())
    ds.SetSpatialRef(template.GetSpatialRef())
    ds.GetRasterBand(1).Fill(0)
    return ds


def burn(mask, source: Path, code: int, where: str | None = None):
    gdal.Rasterize(mask, str(source), options=gdal.RasterizeOptions(
        burnValues=[code], allTouched=True, where=where))


def valid(values, nodata):
    result = np.isfinite(values) & (values >= -1) & (values <= 1)
    if nodata is not None:
        result &= values != nodata
    return result


def spectral(d, w, vd, vw):
    result = np.full(d.shape, NODATA, dtype=np.uint8)
    both = vd & vw
    only_d = vd & ~vw
    only_w = vw & ~vd
    result[vd | vw] = 100
    camp_max = 0.46
    sav_min = 0.48
    sav_avg = 0.58
    result[both & (d >= 0.20) & (d < camp_max)
           & (w >= 0.38) & (w < 0.62)] = 12
    result[both & (d >= sav_min) & (d < 0.70)
           & ((d + w) / 2 >= sav_avg)] = 4
    result[both & (d >= 0.70)] = 3
    result[only_d & (d >= 0.20) & (d < camp_max)] = 12
    result[only_d & (d >= sav_min) & (d < 0.70)] = 4
    result[only_d & (d >= 0.70)] = 3
    result[only_w & (w >= 0.38) & (w < 0.62)] = 12
    result[only_w & (w >= 0.65) & (w < 0.79)] = 4
    result[only_w & (w >= 0.79)] = 3
    return result


def run(base: Path, output: Path, stages_dir: Path | None):
    inputs = paths(base)
    dry, wet, mapbiomas, sx, sy = check_inputs(inputs)
    output = output.resolve()
    report = output.with_suffix(".json")
    stage_paths = {i: stages_dir / f"fitofisionomias_proxy_ndvi_3m_etapa_0{i}.tif"
                   for i in range(1, 4)} if stages_dir else {}
    if output.suffix.lower() not in (".tif", ".tiff"):
        raise ValueError("--output precisa terminar em .tif ou .tiff")
    if any(p.exists() for p in (output, report, *stage_paths.values())):
        raise FileExistsError("Saída ou relatório já existente; use novos destinos")
    output.parent.mkdir(parents=True, exist_ok=True)
    if stages_dir:
        stages_dir.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.stem + ".incompleto.tif")
    urban_path = output.with_name("urbano.incompleto.tif")
    overlay_path = output.with_name("sobreposicoes.incompleto.tif")
    risk_path = output.with_name("ausencia_cerrado.incompleto.tif")
    protected_path = output.with_name("protecao_integral.incompleto.tif")
    projected_path = output.with_name("edificacoes.incompleto.gpkg")
    if any(p.exists() for p in (temp, urban_path, overlay_path, risk_path,
                                protected_path, projected_path)):
        raise FileExistsError("Arquivo temporário anterior ainda presente")

    projected = gdal.VectorTranslate(
        str(projected_path), str(inputs["buildings"]), format="GPKG",
        dstSRS="EPSG:31983", layerCreationOptions=["SPATIAL_INDEX=YES"])
    if projected is None or projected.GetLayer(0).GetFeatureCount() == 0:
        raise ValueError("Falha ao reprojetar edificações")
    projected = None

    urban = create_mask(urban_path, dry)
    burn(urban, inputs["roads"], 1)
    burn(urban, projected_path, 1)
    urban.FlushCache()
    overlay = create_mask(overlay_path, dry)
    for source, code in ((inputs["roads"], 1), (inputs["water"], 2),
                         (projected_path, 3)):
        burn(overlay, source, code)
    overlay.FlushCache()
    risk = create_mask(risk_path, dry)
    burn(risk, inputs["risk"], 1, where="risco = 2")
    risk.FlushCache()
    protected = create_mask(protected_path, dry)
    burn(protected, inputs["protected"], 1, where=PROTECTED_FILTER)
    protected.FlushCache()

    gt = dry.GetGeoTransform()
    map_band = gdal.Translate("", mapbiomas, format="VRT", bandList=[1])
    map_grid = gdal.Warp(
        "", map_band, format="VRT", dstSRS="EPSG:31983",
        outputBounds=(gt[0], gt[3] - dry.RasterYSize * 3,
                      gt[0] + dry.RasterXSize * 3, gt[3]),
        width=dry.RasterXSize, height=dry.RasterYSize,
        resampleAlg="near", srcNodata=0, dstNodata=0)
    if map_grid is None or any(abs(a - b) > 1e-6 for a, b in
                               zip(map_grid.GetGeoTransform(), gt)):
        raise ValueError("MapBiomas não alinhou à grade")

    final = create_raster(temp, dry, "Proxy NDVI de fitofisionomias, etapa 04")
    stages = {i: create_raster(path, dry, f"Proxy NDVI, etapa 0{i}", residual=i == 1)
              for i, path in stage_paths.items()}
    metadata = {
        "method": "NDVI seca+chuva; quatro etapas adotadas em uma passagem de 512 px",
        "grid": {"size_m": 3, "crs": "EPSG:31983", "source": "NDVI da seca"},
        "inputs": {key: str(value) for key, value in inputs.items()},
        "etapa_01": "florestal seca>=.70; sav .48<=seca<.70 e media>=.58; camp .20<=seca<.46 e .38<=chuva<.62; vias/edificações limpam campestre",
        "single_date": "seca: mesmos intervalos secos; chuva: 3>=.79, 4 [.65,.79), 12 [.38,.62); outros=100",
        "etapa_02": "100 vira 101 se |chuva-seca|/2>=.09, senão 102; seca isolada .34, chuva isolada .50",
        "etapa_03": "vias só limpam 101->102; depois MapBiomas original banda 1 classe 11; água vetorial 33; edificações 103; por fim, nas UCs de proteção integral, 101->4 e 102->12",
        "uc_filter": PROTECTED_FILTER,
        "etapa_04": "risco=2/ausência de Cerrado nativo: 3/4->100, 12->101",
        "limitations": ["proxy, não validação de campo", "duas datas não descrevem ciclo fenológico",
                        "campestre e pastagem se confundem", "101/102 não comprovam permeabilidade",
                        "área úmida mantém a resolução temática de 10 m do MapBiomas",
                        "vias lineares sem largura e UDM2 não aplicada aos mosaicos"],
    }
    final.SetMetadataItem("METHOD_JSON", json.dumps(metadata, ensure_ascii=False,
                                                    separators=(",", ":")))
    counts = {i: np.zeros(256, dtype=np.int64) for i in range(1, 5)}
    transitions = {"etapa_01_camp_to_100": 0, "etapa_03_road_101_to_102": 0,
                   "etapa_03_uc_101_to_4": 0, "etapa_03_uc_102_to_12": 0,
                   "etapa_04_forest_to_100": 0, "etapa_04_savanna_to_100": 0,
                   "etapa_04_camp_to_101": 0}
    for y in range(0, dry.RasterYSize, TILE):
        for x in range(0, dry.RasterXSize, TILE):
            width = min(TILE, dry.RasterXSize - x)
            height = min(TILE, dry.RasterYSize - y)
            d = dry.GetRasterBand(1).ReadAsArray(x, y, width, height)
            w = wet.GetRasterBand(1).ReadAsArray(x+sx, y+sy, width, height)
            vd = valid(d, dry.GetRasterBand(1).GetNoDataValue())
            vw = valid(w, wet.GetRasterBand(1).GetNoDataValue())
            first = spectral(d, w, vd, vw)
            urban_tile = urban.GetRasterBand(1).ReadAsArray(x, y, width, height) != 0
            camp = (first == 12) & urban_tile
            transitions["etapa_01_camp_to_100"] += int(camp.sum())
            first[camp] = 100

            second = first.copy()
            target = second == 100
            both = target & vd & vw
            only_d = target & vd & ~vw
            only_w = target & vw & ~vd
            if np.any(target & ~(vd | vw)):
                raise ValueError("Classe 100 sem NDVI válido")
            second[target] = 102
            second[both & (np.abs(w-d)/2 >= .09)] = 101
            second[only_d & (d >= .34)] = 101
            second[only_w & (w >= .50)] = 101

            third = second.copy()
            overlay_tile = overlay.GetRasterBand(1).ReadAsArray(x, y, width, height)
            alive = third != NODATA
            road = alive & (overlay_tile == 1) & (third == 101)
            transitions["etapa_03_road_101_to_102"] += int(road.sum())
            third[road] = 102
            wetland = map_grid.GetRasterBand(1).ReadAsArray(x, y, width, height) == 11
            third[alive & wetland] = 11
            third[alive & (overlay_tile == 2)] = 33
            third[alive & (overlay_tile == 3)] = 103
            within_uc = protected.GetRasterBand(1).ReadAsArray(x, y, width, height) != 0
            uc_savanna = within_uc & (third == 101)
            uc_grassland = within_uc & (third == 102)
            transitions["etapa_03_uc_101_to_4"] += int(uc_savanna.sum())
            transitions["etapa_03_uc_102_to_12"] += int(uc_grassland.sum())
            third[uc_savanna] = 4
            third[uc_grassland] = 12

            fourth = third.copy()
            absence = risk.GetRasterBand(1).ReadAsArray(x, y, width, height) != 0
            forest = absence & (fourth == 3)
            savanna = absence & (fourth == 4)
            grassland = absence & (fourth == 12)
            transitions["etapa_04_forest_to_100"] += int(forest.sum())
            transitions["etapa_04_savanna_to_100"] += int(savanna.sum())
            transitions["etapa_04_camp_to_101"] += int(grassland.sum())
            fourth[forest | savanna] = 100
            fourth[grassland] = 101

            for version, values in enumerate((first, second, third, fourth), 1):
                counts[version] += np.bincount(values.ravel(), minlength=256)
                ds = final if version == 4 else stages.get(version)
                if ds is not None:
                    ds.GetRasterBand(1).WriteArray(values, x, y)

    final.FlushCache()
    final = None
    for ds in stages.values():
        ds.FlushCache()
    stages.clear()
    check = gdal.Open(str(temp), gdal.GA_ReadOnly)
    if (check.RasterXSize != dry.RasterXSize
            or check.RasterYSize != dry.RasterYSize
            or check.GetGeoTransform() != dry.GetGeoTransform()
            or counts[4].sum() != dry.RasterXSize * dry.RasterYSize
            or set(np.flatnonzero(counts[4])) - set(COLORS)
            or any(value == 0 for value in transitions.values())):
        raise ValueError("Validação final falhou")
    check = None
    # Indexadores/sincronizadores do Windows podem manter o GeoTIFF recém-
    # fechado aberto por instantes. Repetir apenas a troca atômica exata.
    for attempt in range(10):
        try:
            temp.replace(output)
            break
        except PermissionError:
            if attempt == 9:
                raise
            gc.collect()
            time.sleep(.3)
    report.write_text(json.dumps({
        "metadata": metadata,
        "counts": {f"etapa_0{i}": {str(code): int(values[code])
                             for code in np.flatnonzero(values)}
                   for i, values in counts.items()},
        "transitions": transitions,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    urban = overlay = risk = protected = map_grid = None
    for path in (urban_path, overlay_path, risk_path, protected_path, projected_path):
        path.unlink()
    print(json.dumps({"output": str(output), "counts_final":
                      {str(code): int(counts[4][code])
                       for code in np.flatnonzero(counts[4])},
                      "transitions": transitions}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True,
                        help="Pasta 02 BASE DE DADOS")
    parser.add_argument("--output", type=Path, required=True,
                        help="Novo GeoTIFF da etapa 04 final")
    parser.add_argument("--stages-dir", type=Path,
                        help="Opcional: GeoTIFFs das etapas 01-03")
    args = parser.parse_args()
    run(args.base.resolve(), args.output, args.stages_dir)


if __name__ == "__main__":
    main()
