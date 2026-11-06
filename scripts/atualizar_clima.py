"""Atualiza o conjunto climático publicado. Nunca modifica os dados de pesquisa.

Requer GDAL, Shapely, NumPy e Pillow; execute com o Python do QGIS.
O GeoPackage de entrada fornece estatísticas zonais já calculadas para os mesmos
seis rasters. Novos rasters exigem novo diagnóstico, não apenas novas classes.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import runpy
import sys
import tempfile

import numpy as np
import shapely
from osgeo import gdal, ogr
from shapely.strtree import STRtree

from clima_comum import classify, complete, sha256, artifact_sha256
from exportar_mapa import preparar_dados
from exportar_riscos_por_ra import gerar
from exportar_cenarios_climaticos import save_palette

SITE = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def make_zone(source, catalog, folder):
    record = catalog["indicators"]["temperatura"]["scenarios"]["media"]
    ds = gdal.Open(str(source / record["source"]))
    mask = gdal.GetDriverByName("GTiff").Create(str(folder / "zona.tif"), ds.RasterXSize, ds.RasterYSize, 1,
                                               gdal.GDT_Byte, options=["COMPRESS=DEFLATE", "TILED=YES"])
    mask.SetGeoTransform(ds.GetGeoTransform())
    mask.SetProjection(ds.GetProjection())
    mask.GetRasterBand(1).SetNoDataValue(0)
    count = 0
    band = ds.GetRasterBand(1)
    for row in range(0, ds.RasterYSize, 256):
        height = min(256, ds.RasterYSize - row)
        values = band.ReadAsArray(0, row, ds.RasterXSize, height)
        valid = band.GetMaskBand().ReadAsArray(0, row, ds.RasterXSize, height) != 0
        warm = valid & np.isfinite(values) & (values > catalog["zone"]["threshold"])
        count += int(warm.sum())
        mask.GetRasterBand(1).WriteArray(warm.astype(np.uint8), 0, row)
    zone_path = SITE / "dados-mapas/clima/zona-icu.gpkg"
    if zone_path.exists():
        zone_path.unlink()  # Only this generated file, inside the site.
    vector = ogr.GetDriverByName("GPKG").CreateDataSource(str(zone_path))
    layer = vector.CreateLayer("zona_icu", srs=ds.GetSpatialRef(), geom_type=ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("classe", ogr.OFTInteger))
    gdal.Polygonize(mask.GetRasterBand(1), mask.GetRasterBand(1), layer, 0, [])
    polygons = [shapely.from_wkb(bytes(feature.GetGeometryRef().ExportToWkb())) for feature in layer]
    vector = None
    area = sum(p.area for p in polygons)
    pixel_area = abs(ds.GetGeoTransform()[1] * ds.GetGeoTransform()[5])
    if abs(area - count * pixel_area) > 0.01:
        raise ValueError("Área vetorizada da zona difere da máscara raster")
    # Source display: current warm/cool zones, same grid as the six climate maps.
    bounds = catalog["bounds_3857"]
    width, height = catalog["visualization"]["size"]
    projected = gdal.Warp("", ds, format="MEM", dstSRS="EPSG:3857", outputBounds=bounds,
                          width=width, height=height, resampleAlg="near", outputType=gdal.GDT_Float64, dstNodata=np.nan)
    values = projected.ReadAsArray()
    codes = np.zeros(values.shape, np.uint8)
    valid = np.isfinite(values)
    codes[valid] = 1 + (values[valid] > catalog["zone"]["threshold"]).astype(np.uint8)
    rgb = np.array([[200, 228, 218], [211, 69, 54]], np.uint8)
    save_palette(codes, rgb, SITE / "dados-mapas/contexto/icu.png")
    return polygons, {"pixels": count, "area_ha": area / 10000, "polygons": len(polygons)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--fragmentos", required=True, type=Path)
    parser.add_argument("--ras", required=True, type=Path)
    parser.add_argument("--bacia", required=True, type=Path)
    parser.add_argument("--ogr2ogr", required=True, type=Path)
    parser.add_argument("--base-riscos", required=True, type=Path)
    parser.add_argument("--proveniencia", type=Path, help="JSON de parâmetros da execução do diagnóstico")
    parser.add_argument("--migration", action="store_true", help="Primeira migração da rodada v01 auditada; não usar com novos rasters")
    args = parser.parse_args()
    gdal.UseExceptions()
    catalog_path = SITE / "dados-mapas/clima/catalogo.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    provenance = json.loads(args.proveniencia.read_text(encoding="utf-8")) if args.proveniencia else None
    if not args.migration and not provenance:
        parser.error("Informe --proveniencia do diagnóstico calculado com estes rasters")
    old_web = json.loads(gzip.decompress((SITE / "mapa-dados.json.gz").read_bytes()))
    old_index = {field: index for index, field in enumerate(old_web["fields"])}
    old_rows = {values[old_index["patch_id"]]: values for _, values in old_web["rows"]}
    old_geometry = {values[old_index["patch_id"]]: polygons for polygons, values in old_web["rows"]}
    for config in catalog["indicators"].values():
        for record in config["scenarios"].values():
            source = args.source_dir / record["source"]
            digest = sha256(source)
            if not args.migration and record.get("source_sha256") != digest:
                raise ValueError("Raster alterado: regenere o catálogo e o diagnóstico antes de publicar")
            if not args.migration and provenance.get("climate_sources", {}).get(record["field"]) != digest:
                raise ValueError("Diagnóstico e rasters têm proveniências diferentes")
            ds = gdal.Open(str(source))
            extremes = ds.GetRasterBand(1).ComputeRasterMinMax(False)
            if not np.allclose(extremes, [record["minimum"], record["maximum"]], rtol=0, atol=1e-10):
                raise ValueError("Catálogo e extremos do raster incompatíveis")
            record["source_sha256"] = digest
    complete(catalog)
    print("Fontes e cortes conferidos", flush=True)
    with tempfile.TemporaryDirectory(prefix="paranoa-clima-", dir=SITE.parent) as folder_name:
        folder = Path(folder_name).resolve()
        if folder.parent != SITE.parent.resolve():
            raise ValueError("Pasta temporária fora do diretório de trabalho")
        polygons, zone_stats = make_zone(args.source_dir, catalog, folder)
        tree = STRtree(polygons)
        print(f"Zona atualizada: {zone_stats}", flush=True)
        target = folder / "diagnostico-atual.gpkg"
        ds = gdal.VectorTranslate(str(target), str(args.fragmentos), format="GPKG")
        layer = ds.GetLayer(0)
        for config in catalog["indicators"].values():
            for record in config["scenarios"].values():
                field = record["class_field"]
                if layer.FindFieldIndex(field, True) < 0:
                    definition = ogr.FieldDefn(field, ogr.OFTString)
                    definition.SetWidth(32)
                    layer.CreateField(definition)
        changes = Counter()
        seen = set()
        ds.StartTransaction()
        for feature in layer:
            patch_id = feature["patch_id"]
            if patch_id in seen or patch_id not in old_rows:
                raise ValueError("Fragmentos incompatíveis com a publicação auditada")
            seen.add(patch_id)
            old = old_rows[patch_id]
            for config in catalog["indicators"].values():
                for scenario, record in config["scenarios"].items():
                    value = feature[record["field"]]
                    previous = old[old_index[record["field"]]]
                    if args.migration and ((value is None) != (previous is None) or (value is not None and abs(value - previous) > .00005001)):
                        raise ValueError("Migração exige as mesmas estatísticas zonais auditadas")
                    label = classify(value, config, scenario)
                    field = record["class_field"]
                    changes[field] += int(feature[field] != label)
                    if label is None:
                        feature.SetFieldNull(feature.GetFieldIndex(field))
                    else:
                        feature[field] = label
            geo = shapely.from_wkb(bytes(feature.GetGeometryRef().ExportToWkb()))
            if not geo.is_valid:
                geo = shapely.make_valid(geo)
            overlap = any(geo.intersection(polygons[int(i)]).area > 0 for i in tree.query(geo, predicate="intersects"))
            label = "sim" if overlap else "não"
            changes["icu"] += int(feature["icu"] != label)
            feature["icu"] = label
            layer.SetFeature(feature)
        if len(seen) != len(old_rows):
            raise ValueError("Quantidade de fragmentos mudou; audite a geometria antes de publicar")
        ds.CommitTransaction()
        layer_name = layer.GetName()
        layer = ds = None
        print(f"Reclassificados: {dict(changes)}", flush=True)
        web = preparar_dados(target, layer_name, args.ogr2ogr)
        id_index = web["fields"].index("patch_id")
        if any(polygons != old_geometry[values[id_index]] for polygons, values in web["rows"]):
            raise ValueError("Geometrias alteradas: faça nova auditoria antes da publicação")
        web["climate_revision"] = catalog["revision"]
        (SITE / "mapa-dados.json.gz").write_bytes(gzip.compress(json.dumps(web, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))
        print("Calculando resumo por RA…", flush=True)
        ra = gerar(str(args.ras), str(args.bacia), str(target))
        ra["climate_revision"] = catalog["revision"]
        write_json(SITE / "dados-mapas/riscos-por-ra.json", ra)
        # The diagnostic provenance is mandatory on subsequent updates.
        write_json(SITE / "dados-mapas/clima/atualizacao.json", {
            "revision": catalog["revision"], "source_diagnostic_sha256": sha256(args.fragmentos),
            "fragments": len(seen), "changes": dict(changes), "zone": zone_stats,
            "numeric_values": "preserved_from_zonal_statistics", "migration": args.migration,
        })
    write_json(catalog_path, catalog)
    context_path = SITE / "dados-mapas/contexto-riscos.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    for config in catalog["indicators"].values():
        for record in config["scenarios"].values():
            context.pop(record["field"], None)
            (SITE / "dados-mapas/contexto" / (record["field"] + ".png")).unlink(missing_ok=True)
    context["icu"].update(bounds=catalog["bounds_3857"], kind="derived", input="../clima/zona-icu.gpkg",
                          note=f"Três classes mais quentes da temperatura média; corte > {catalog['zone']['threshold']:.10f} °C. Mesma versão da metodologia e dos fragmentos.")
    write_json(context_path, context)
    sys.argv = [str(SITE / "scripts/exportar_mapas_metodologicos.py"), "--base-dir", str(args.base_riscos)]
    runpy.run_path(sys.argv[0], run_name="__main__")
    update_path = SITE / "dados-mapas/clima/atualizacao.json"
    update = json.loads(update_path.read_text(encoding="utf-8"))
    paths = [SITE / "mapa-dados.json.gz", SITE / "dados-mapas/riscos-por-ra.json",
             SITE / "dados-mapas/metodologia-riscos.json", SITE / "dados-mapas/contexto-riscos.json",
             SITE / "dados-mapas/contexto/icu.png", SITE / "dados-mapas/metodologia-riscos/icu-fragmentos-classes.png"]
    paths += list((SITE / "dados-mapas/clima").glob("*.png"))
    paths += [SITE / "dados-mapas/clima/zona-icu.gpkg", catalog_path]
    update["artifacts_sha256"] = {path.relative_to(SITE).as_posix(): artifact_sha256(path) for path in paths}
    write_json(update_path, update)
    from validar_clima import validate
    validate()


if __name__ == "__main__":
    main()
