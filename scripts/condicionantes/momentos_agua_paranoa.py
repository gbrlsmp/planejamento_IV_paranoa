# -*- coding: utf-8 -*-
"""Momentos da agua / Paranoa. Executar conforme LEIA_ME_MOMENTOS_AGUA.md.

Um arquivo: pre-processamento, GRASS, textura, estimativas hidrologicas,
HAND, FAHP, mapas e diagnosticos. Os resultados sao exploratorios, sem calibracao
hidrologica. O Lago Paranoa NAO recebe uma curva de operacao inventada.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata

VERSION = "1.1.1"
# A 1.1.1 altera somente a janela hidrologica e o aviso de termino.
# Esta assinatura permite reaproveitar com seguranca as etapas anteriores.
PRE_HYDRO_CACHE = (
    "1.1.0",
    "53c4a42f19b6518f48f1a738ca2296c3fde70c281ae1e8d1c017d0055c319b77",
)
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent
NODATA = -9999.0
CRITERIA = ["decl", "flux", "alt", "solo", "infil", "lencol", "inund", "dren", "uso"]
NOTAS = [8, 8, 7, 5, 6, 6, 7, 4, 5]
DEFAULT = {
    "versao": VERSION,
    "pasta": str(ROOT),
    "epsg": 31983,
    "resolucao_mde_m": 2.0,
    "resolucao_momentos_m": 5.0,
    "resolucao_hidrologia_m": 20.0,
    "tile_mde_pixels": 2048,
    "margem_interpolacao_m": 500.0,
    "simplificar_curvas_m": 0.75,
    "distancia_maxima_fallback_mde_m": 150.0,
    "rebaixamento_vias_m": 0.30,
    "buffer_vias_m": 5.25,
    "limiar_drenagem_km2": 0.25,
    "massa_agua_grande_km2": 0.5,
    "manning_canal": 0.045,
    "raio_hidraulico_referencia_tc_m": 0.5,
    "altura_escoamento_lamina_tc_m": 0.02,
    "manning_limites_velocidade_ms": [0.05, 5.0],
    "passo_hidrograma_min": 5.0,
    "duracoes_chuva_min": [60, 180, 360, 720, 1440],
    "tempos_retorno": [5, 10, 20, 50, 100, 200, 500],
    "idf": {"K": 816.70, "a": 0.081, "b": 8.990, "c": 0.704},
    "abstracao_inicial_fracao_S": 0.2,
    "limite_altura_curva_chave_m": 50.0,
    "passo_altura_curva_chave_m": 0.25,
    "memoria_grass_mb": 2048,
    "qgis_root": r"C:\Program Files\QGIS 3.44.15",
    "preferir_pocos_monitoramento": True,
    "minimo_pocos_ajuste": 8,
    "perturbacoes_pesos": 500,
    "amostras_sensibilidade": 10000,
    "semente": 42,
    "salvar_pertinencias_criterios": True,
    "limpar_intermediarios_ao_concluir": True,
    "piloto_bbox_utm": [181000.0, 8244000.0, 183000.0, 8246000.0],
    "arquivos": {
        "bacia": "bacia_paranoa_merge_ipe_df_2023.gpkg",
        "curvas": "CURVA_DE_NIVEL_COMPLETA_Bacia_Paranoa.gpkg",
        "uso": "uso_cobertura_final_v01.tif",
        "edificacoes": "Construções Bacia do Paranoá.shp",
        "vias": "Vias_OSM_Bacia_Paranoa.shp",
        "ibge": "Pedo_IBGE_Bacia_Paranoa.shp",
        "ibram": "classes_de_solos_CORRIGIDA.shp",
        "pocos": "POCOS_SIAGAS_Bacia_Paranoa.gpkg",
    },
    "campos": {
        "cota": "cota",
        "ibge": "legenda",
        "ibram": "classe_n2",
        "pavimentacao": "pavimentad",
        "ne": "ne",
        "id_poco": "idt_ponto",
    },
    "codigos_urbanos": [24, 241, 242, 243, 244],
    "notas_fahp": NOTAS,
    "observacao": "Hidrologia/HAND na grade configurada (padrao 20 m); mapas finais 5 m nao criam detalhe hidrologico de 5 m. Parametros iniciais sem calibracao.",
}
# Solo: fator Ksat, grupo hidrologico de trabalho (0=A ... 3=D).
# Estes grupos sao HIPOTESES por classe, nao um levantamento NRCS de campo.
SOILS = {
    0: (0.0, 3),
    1: (1.0, 1),
    2: (0.45, 3),
    3: (0.55, 2),
    4: (0.35, 3),
    5: (0.15, 3),
    6: (0.65, 2),
    7: (0.45, 2),
    8: (0.8, 1),
    9: (1.0, 0),
    10: (0.5, 2),
}
SOIL_NAMES = {
    0: "Agua",
    1: "Latossolo",
    2: "Plintossolo",
    3: "Argissolo",
    4: "Neossolo litolico",
    5: "Gleissolo/hidromorfico",
    6: "Neossolo fluvico",
    7: "Cambissolo",
    8: "Nitossolo",
    9: "Neossolo quartzarenico",
    10: "Espodossolo",
    250: "Urbano sem complemento",
    254: "Solo nao reconhecido",
}
# CN II de trabalho; familias de coberturas inspiradas em NRCS TR-55. E preciso
# revisar para calibracao local. Nao equivalem aos coeficientes C nem a Manning.
CN = {
    3: [30, 55, 70, 77],
    4: [39, 61, 74, 80],
    9: [36, 60, 73, 79],
    11: [85, 90, 94, 95],
    12: [39, 61, 74, 80],
    15: [49, 69, 79, 84],
    19: [67, 78, 85, 89],
    21: [61, 75, 83, 87],
    24: [77, 85, 90, 92],
    25: [77, 86, 91, 94],
    33: [98] * 4,
    100: [49, 69, 79, 84],
}
ROUGHNESS = {
    3: 0.25,
    4: 0.20,
    9: 0.20,
    11: 0.15,
    12: 0.12,
    15: 0.10,
    19: 0.08,
    21: 0.08,
    24: 0.06,
    25: 0.035,
    33: 0.045,
    100: 0.12,
}
CBASE = {
    3: 0.15,
    4: 0.20,
    9: 0.20,
    11: 0.60,
    12: 0.20,
    15: 0.30,
    19: 0.40,
    21: 0.40,
    24: 0.60,
    25: 0.55,
    33: 1.0,
    100: 0.30,
}
IMPBASE = {
    3: 0.0,
    4: 0.0,
    9: 0.0,
    11: 0.0,
    12: 0.0,
    15: 0.0,
    19: 0.0,
    21: 0.10,
    24: 0.40,
    25: 0.05,
    33: 0.0,
    100: 0.0,
}


def norm(s):
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", str(s or "").upper())
        if not unicodedata.combining(c)
    )


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def config(root=ROOT):
    p = Path(root) / "parametros_momentos_agua.json"
    if not p.exists():
        save_json(p, DEFAULT)
    c = json.loads(p.read_text(encoding="utf-8"))
    return c


def deps():
    global np, gdal, ogr, osr, ndimage, spatial, optimize, signal, stats
    import numpy as np
    from osgeo import gdal, ogr, osr
    from scipy import ndimage, spatial, optimize, signal, stats

    gdal.UseExceptions()
    ogr.UseExceptions()
    gdal.SetConfigOption("GDAL_NUM_THREADS", "2")
    gdal.SetConfigOption("GDAL_HTTP_MAX_RETRY", "3")
    gdal.SetConfigOption("GDAL_HTTP_RETRY_DELAY", "2")
    gdal.SetConfigOption("GDAL_HTTP_TIMEOUT", "60")
    gdal.SetCacheMax(512 * 1024**2)


def srs(epsg):
    s = osr.SpatialReference()
    s.ImportFromEPSG(int(epsg))
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return s


def output_directory(c, piloto=False):
    return Path(c["pasta"]) / ("TESTE_PILOTO" if piloto else "RESULTADOS_MOMENTOS_AGUA")


def execution_key(c, piloto, *, version=VERSION, code_hash=None):
    """Invalidate calculated data whenever code, parameters or inputs change."""
    signatures = {}
    for name, filename in c["arquivos"].items():
        source = Path(c["pasta"]) / filename
        files = [source]
        if source.suffix.lower() == ".shp":
            files = [
                source.with_suffix(ext)
                for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".cst")
                if source.with_suffix(ext).exists()
            ]
        signatures[name] = [[str(f), f.stat().st_size, f.stat().st_mtime_ns] for f in files]
    code_hash = code_hash or hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    payload = json.dumps([version, code_hash, c, signatures, piloto], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def create_geotiff(path, width, height, transform, projection, dtype, nodata):
    """One place for the storage format and georeferencing of derived rasters."""
    predictor = "3" if dtype in (gdal.GDT_Float32, gdal.GDT_Float64) else "2"
    dataset = gdal.GetDriverByName("GTiff").Create(
        str(path),
        width,
        height,
        1,
        dtype,
        options=["TILED=YES", "COMPRESS=DEFLATE", f"PREDICTOR={predictor}", "BIGTIFF=IF_SAFER"],
    )
    dataset.SetProjection(projection)
    dataset.SetGeoTransform(transform)
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(nodata)
    band.Fill(nodata)
    return dataset


def close_datasets(*datasets):
    """Close handles before recording a successful checkpoint or deleting files."""
    for dataset in datasets:
        if dataset is not None:
            dataset.Close()


def completed_run(out, key):
    """Completed products can be reused even after temporary files are removed."""
    try:
        report = json.loads((out / "proveniencia_e_limites.json").read_text(encoding="utf-8"))
        products = report["produtos"]
        return (
            (out / "CONCLUIDO.txt").exists()
            and report["chave_execucao"] == key
            and bool(products)
            and all(
                (out / name).is_file() and (out / name).stat().st_size == size
                for name, size in products
            )
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def basin_tile_mask(geom, bx, by, width, height, res, epsg):
    """Pixels com centro dentro da bacia; blocos exteriores nao exigem cotas."""
    ring = ogr.CreateGeometryFromWkt(
        f"POLYGON(({bx} {by},{bx+width*res} {by},{bx+width*res} {by-height*res},{bx} {by-height*res},{bx} {by}))"
    )
    if not geom.Intersects(ring):
        return np.zeros((height, width), dtype=bool)
    if geom.Contains(ring):
        return np.ones((height, width), dtype=bool)
    vector = (ogr.GetDriverByName("MEM") or ogr.GetDriverByName("Memory")).CreateDataSource("")
    layer = vector.CreateLayer("bacia", srs(epsg), ogr.wkbUnknown)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(geom)
    layer.CreateFeature(feature)
    raster = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    raster.SetProjection(srs(epsg).ExportToWkt())
    raster.SetGeoTransform((bx, res, 0, by, 0, -res))
    raster.GetRasterBand(1).Fill(0)
    gdal.RasterizeLayer(raster, [1], layer, burn_values=[1])
    result = raster.ReadAsArray() > 0
    raster = None
    vector = None
    return result


def tin_tile(points, zs, mask, bx, by, res, max_distance, label):
    """TIN somente onde existe bacia; nao inventar cotas em lacunas internas."""
    a = np.full(mask.shape, NODATA, dtype="float32")
    if not mask.any():
        return a
    pts = np.asarray(points, dtype="float64")
    values = np.asarray(zs, dtype="float64")
    if len(pts) < 3:
        raise ValueError(
            f"Topografia insuficiente dentro da bacia no bloco {label}; nao sera inventado relevo."
        )
    pts, inverse = np.unique(pts, axis=0, return_inverse=True)
    values = np.bincount(inverse, weights=values) / np.bincount(inverse)
    if len(pts) < 3 or np.linalg.matrix_rank(pts - pts[0]) < 2:
        raise ValueError(
            f"Curvas sem pontos unicos nao colineares suficientes no bloco {label}, dentro da bacia."
        )
    from scipy.interpolate import LinearNDInterpolator

    interp = LinearNDInterpolator(spatial.Delaunay(pts), values, fill_value=np.nan)
    tree = spatial.cKDTree(pts)
    height, width = mask.shape
    for row in range(0, height, 128):
        nr = min(128, height - row)
        inside = mask[row : row + nr]
        if not inside.any():
            continue
        gx, gy = np.meshgrid(
            bx + (np.arange(width) + 0.5) * res, by - (np.arange(row, row + nr) + 0.5) * res
        )
        q = np.column_stack((gx[inside], gy[inside]))
        vv = np.asarray(interp(q))
        bad = ~np.isfinite(vv)
        if bad.any():
            dist, ix = tree.query(q[bad])
            vv[bad] = np.where(dist <= max_distance, values[ix], NODATA)
        a[row : row + nr][inside] = vv
    return a


class Pipeline:
    def __init__(self, c, piloto=False, reuse_completed=False):
        self.c = c
        self.root = Path(c["pasta"])
        self.out = output_directory(c, piloto)
        self.out.mkdir(exist_ok=True)
        self.tmp = self.out / "intermediarios"
        self.piloto = piloto
        self.warnings = []
        self.logfile = self.out / "execucao.log"
        self.key = execution_key(c, piloto)
        self.pre_hydro_key = execution_key(
            c, piloto, version=PRE_HYDRO_CACHE[0], code_hash=PRE_HYDRO_CACHE[1]
        )
        self.log(
            "Inicio; "
            + (
                "PILOTO: contribuicoes truncadas, NAO utilizar para conclusoes."
                if piloto
                else "bacia completa"
            )
        )
        self.reused = reuse_completed and completed_run(self.out, self.key)
        if self.reused:
            self.log("Resultados completos ja verificados; reutilizando produtos finais.")
            return
        self.tmp.mkdir(exist_ok=True)
        ds = ogr.Open(str(self.root / c["arquivos"]["bacia"]))
        l = ds.GetLayer(0)
        ss = l.GetSpatialRef().Clone()
        ss.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        transform = osr.CoordinateTransformation(ss, srs(c["epsg"]))
        geom = None
        for f in l:
            g = f.GetGeometryRef().Clone()
            g.Transform(transform)
            if not g.IsValid():
                g = g.MakeValid()
            geom = g if geom is None else geom.Union(g)
        if piloto:
            x0, y0, x1, y1 = c["piloto_bbox_utm"]
            box = ogr.CreateGeometryFromWkt(
                f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"
            )
            geom = geom.Intersection(box)
            if geom.IsEmpty():
                raise ValueError("Recorte piloto fora da bacia; alterar piloto_bbox_utm.")
        self.geom = geom
        self.area = geom.GetArea()
        env = geom.GetEnvelope()
        r = c["resolucao_hidrologia_m"]
        for name in ["resolucao_mde_m", "resolucao_momentos_m"]:
            v = c[name]
            if r < v or abs(r / v - round(r / v)) > 1e-7:
                raise ValueError(
                    "Grade hidrologica deve ser multipla inteira das grades MDE e momentos."
                )
        self.bbox = (
            math.floor(env[0] / r) * r,
            math.floor(env[2] / r) * r,
            math.ceil(env[1] / r) * r,
            math.ceil(env[3] / r) * r,
        )
        self.bacia = self.tmp / "bacia_trabalho.gpkg"
        if not self.done("00_bacia", [self.bacia]):
            if self.bacia.exists():
                self.bacia.unlink()
            d = ogr.GetDriverByName("GPKG").CreateDataSource(str(self.bacia))
            lay = d.CreateLayer("bacia", srs(c["epsg"]), ogr.wkbMultiPolygon)
            ft = ogr.Feature(lay.GetLayerDefn())
            ft.SetGeometry(ogr.ForceToMultiPolygon(geom.Clone()))
            lay.CreateFeature(ft)
            d = None
            self.mark("00_bacia", [self.bacia])

    def log(self, msg):
        line = time.strftime("%H:%M:%S") + " | " + str(msg)
        print(line, flush=True)
        with self.logfile.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)
        self.log("ATENCAO: " + msg)

    def done(self, stage, paths):
        marker = self.tmp / (stage + ".json")
        if marker.exists() and all(Path(p).exists() for p in paths):
            try:
                saved_key = json.loads(marker.read_text(encoding="utf-8"))["key"]
                compatible_stage = stage in {
                    "00_bacia", "01_terreno", "02_superficies", "03_grass", "04_rede", "05_textura"
                } or stage.startswith(("mask_", "v_"))
                if saved_key == self.key:
                    self.log("Retomada: " + stage)
                    return True
                if compatible_stage and saved_key == self.pre_hydro_key:
                    self.mark(stage, paths)
                    self.log("Retomada compativel da v1.1.0: " + stage)
                    return True
            except (ValueError, KeyError):
                pass
        # A checkpoint must not survive an incomplete attempt to rebuild it.
        marker.unlink(missing_ok=True)
        return False

    def mark(self, stage, paths):
        save_json(self.tmp / (stage + ".json"), {"key": self.key, "files": [str(p) for p in paths]})

    def cleanup(self):
        """Apaga apenas os temporarios deste processamento, apos sucesso."""
        target = self.tmp.resolve()
        expected = self.out.resolve() / "intermediarios"
        if (
            self.out.resolve() != self.root.resolve() / self.out.name
            or self.out.is_symlink()
            or self.out.is_junction()
            or target != expected
            or self.tmp.is_symlink()
            or self.tmp.is_junction()
        ):
            raise RuntimeError(
                "Pasta de intermediarios fora do destino esperado; limpeza cancelada."
            )
        if target.is_dir():
            def remove_readonly(function, path, error):
                candidate = Path(path).resolve()
                if candidate != target and not candidate.is_relative_to(target):
                    raise RuntimeError("Alvo de limpeza fora da pasta de intermediarios.")
                attributes = os.stat(path, follow_symlinks=False)
                if not isinstance(error, PermissionError) or not (
                    getattr(attributes, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_READONLY
                ):
                    raise error
                # OneDrive pode marcar nossas pastas temporarias como somente leitura.
                os.chmod(path, stat.S_IWRITE)
                function(path)

            shutil.rmtree(target, onexc=remove_readonly)
            self.log("Intermediarios removidos; produtos finais e entradas preservados.")

    def create(self, path, res, dtype=None, nodata=NODATA):
        x0, y0, x1, y1 = self.bbox
        w = round((x1 - x0) / res)
        h = round((y1 - y0) / res)
        dtype = gdal.GDT_Float32 if dtype is None else dtype
        return create_geotiff(
            path, w, h, (x0, res, 0, y1, 0, -res), srs(self.c["epsg"]).ExportToWkt(), dtype, nodata
        )

    def write(self, path, a, res, dtype=None, nodata=NODATA):
        with self.create(path, res, dtype, nodata) as ds:
            ds.GetRasterBand(1).WriteArray(a)

    def warp(self, src, dst, res, method="bilinear", dtype=None, nodata=NODATA):
        kwargs = dict(
            format="GTiff",
            dstSRS=f"EPSG:{self.c['epsg']}",
            outputBounds=self.bbox,
            xRes=res,
            yRes=res,
            resampleAlg=method,
            dstNodata=nodata,
            multithread=True,
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"],
        )
        if dtype is not None:
            kwargs["outputType"] = dtype
        d = gdal.Warp(str(dst), str(src), **kwargs)
        d = None

    def mask(self, res):
        name = self.tmp / f"mascara_{res:g}m.tif"
        if not self.done("mask_" + str(res), [name]):
            d = self.create(name, res, gdal.GDT_Byte, 0)
            v = ogr.Open(str(self.bacia))
            gdal.RasterizeLayer(d, [1], v.GetLayer(0), burn_values=[1])
            d = None
            v = None
            self.mark("mask_" + str(res), [name])
        return name

    def vector(self, key):
        out = self.tmp / (key + "_utm.gpkg")
        if not self.done("v_" + key, [out]):
            if out.exists():
                out.unlink()
            x0, y0, x1, y1 = self.bbox
            src = gdal.OpenEx(
                str(self.root / self.c["arquivos"][key]),
                gdal.OF_VECTOR,
                open_options=["ENCODING=ISO-8859-1"] if key == "ibram" else [],
            )
            opts = [
                "-f",
                "GPKG",
                "-t_srs",
                f"EPSG:{self.c['epsg']}",
                "-spat",
                str(x0),
                str(y0),
                str(x1),
                str(y1),
                "-spat_srs",
                f"EPSG:{self.c['epsg']}",
                "-nln",
                key,
            ]
            if key in ["edificacoes", "ibge", "ibram"]:
                opts += ["-nlt", "PROMOTE_TO_MULTI"]
            d = gdal.VectorTranslate(str(out), src, options=opts)
            d = None
            src = None
            self.mark("v_" + key, [out])
        return out

    def terrain(self):
        c = self.c
        final = self.out / "mde_2m.tif"
        model = self.out / "mde_momentos.tif"
        if self.done("01_terreno", [final, model]):
            return
        self.log("Interpolacao TIN por blocos; mantendo fontes topograficas originais.")
        res = c["resolucao_mde_m"]
        x0, y0, x1, y1 = self.bbox
        width = round((x1 - x0) / res)
        height = round((y1 - y0) / res)
        tiles = self.tmp / "tiles_mde"
        tiles.mkdir(exist_ok=True)
        dim = int(c["tile_mde_pixels"])
        paths = []
        src = ogr.Open(str(self.root / c["arquivos"]["curvas"]))
        layer = src.GetLayerByName("curvas_completas") or src.GetLayer(0)
        target = srs(c["epsg"])
        ss = layer.GetSpatialRef().Clone()
        ss.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        if not ss.IsSame(target):
            raise ValueError(
                "Curvas precisam estar no CRS metrico configurado; reprojetar fonte derivada antes desta etapa."
            )
        margin = c["margem_interpolacao_m"]
        count = 0
        total = math.ceil(width / dim) * math.ceil(height / dim)
        for yy in range(0, height, dim):
            for xx in range(0, width, dim):
                count += 1
                tw = min(dim, width - xx)
                th = min(dim, height - yy)
                bx = x0 + xx * res
                by = y1 - yy * res
                path = tiles / f"tin_{yy}_{xx}.tif"
                paths.append(str(path))
                mark = path.with_suffix(".ok.json")
                if (
                    path.exists()
                    and mark.exists()
                    and json.loads(mark.read_text()).get("key") == self.key
                ):
                    continue
                mark.unlink(missing_ok=True)
                self.log(f"TIN bloco {count}/{total} iniciando ({xx},{yy}).")
                inside = basin_tile_mask(self.geom, bx, by, tw, th, res, c["epsg"])
                env = (bx - margin, by - th * res - margin, bx + tw * res + margin, by + margin)
                clip = ogr.CreateGeometryFromWkt(
                    f"POLYGON(({env[0]} {env[1]},{env[2]} {env[1]},{env[2]} {env[3]},{env[0]} {env[3]},{env[0]} {env[1]}))"
                )
                layer.SetSpatialFilterRect(*env)
                points = []
                zs = []
                for feat in (layer if inside.any() else []):
                    z = feat.GetField(c["campos"]["cota"])
                    if z is None or not math.isfinite(z):
                        continue
                    g = feat.GetGeometryRef().Intersection(clip).Simplify(c["simplificar_curvas_m"])

                    def collect(gg):
                        if gg is None or gg.IsEmpty():
                            return
                        if gg.GetGeometryCount():
                            for j in range(gg.GetGeometryCount()):
                                collect(gg.GetGeometryRef(j))
                        else:
                            for p in gg.GetPoints():
                                points.append(p[:2])
                                zs.append(float(z))

                    collect(g)
                a = tin_tile(
                    points,
                    zs,
                    inside,
                    bx,
                    by,
                    res,
                    c["distancia_maxima_fallback_mde_m"],
                    f"{xx},{yy}",
                )
                with create_geotiff(
                    path,
                    tw,
                    th,
                    (bx, res, 0, by, 0, -res),
                    target.ExportToWkt(),
                    gdal.GDT_Float32,
                    NODATA,
                ) as d:
                    d.GetRasterBand(1).WriteArray(a)
                save_json(mark, {"key": self.key, "fora_da_bacia": bool(not inside.any())})
                self.log(
                    f"TIN bloco {count}/{total}: "
                    + (
                        f"{len(points)} vertices; concluido."
                        if inside.any()
                        else "fora da bacia; mantido NoData."
                    )
                )
        vrt = self.tmp / "mosaico_mde.vrt"
        d = gdal.BuildVRT(str(vrt), paths)
        d = None
        d = gdal.Translate(
            str(final),
            str(vrt),
            format="GTiff",
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3", "BIGTIFF=YES"],
        )
        d = None
        self.warp(final, model, c["resolucao_momentos_m"], "average")
        self.mark("01_terreno", [final, model])

    def surfaces(self):
        c = self.c
        res = c["resolucao_momentos_m"]
        outputs = [
            self.out / n
            for n in [
                "uso_classes.tif",
                "edificacoes.tif",
                "vias_tipo.tif",
                "solo_integrado.tif",
                "solo_fonte.tif",
                "impermeabilizacao.tif",
                "rugosidade.tif",
                "cn_ii.tif",
                "coeficiente_c_referencia.tif",
                "mde_condicionado.tif",
            ]
        ]
        if self.done("02_superficies", [*outputs, self.out / "pedologia_integrada.gpkg"]):
            return
        self.log("Reprojetando vetores e combinando cobertura, telhados, vias e pedologia.")
        self.warp(self.root / c["arquivos"]["uso"], outputs[0], res, "near", gdal.GDT_Byte, 255)
        edif = self.vector("edificacoes")
        vias = self.vector("vias")
        ibge = self.vector("ibge")
        ibram = self.vector("ibram")
        d = self.create(outputs[1], res, gdal.GDT_Byte, 0)
        v = ogr.Open(str(edif))
        gdal.RasterizeLayer(d, [1], v.GetLayer(0), burn_values=[1])
        d = None
        v = None
        # Cada via recebe o buffer aprovado; NAO e SIM permanecem diferentes.
        d = self.create(outputs[2], res, gdal.GDT_Byte, 0)
        v = ogr.Open(str(vias))
        l = v.GetLayer(0)
        for value, burn in [("NAO", 1), ("SIM", 2)]:
            l.SetAttributeFilter(f"{c['campos']['pavimentacao']} = '{value}'")
            mem = ogr.GetDriverByName("Memory").CreateDataSource("")
            ml = mem.CreateLayer("vias", srs(c["epsg"]), ogr.wkbPolygon)
            for f in l:
                g = f.GetGeometryRef().Buffer(c["buffer_vias_m"], 4)
                ft = ogr.Feature(ml.GetLayerDefn())
                ft.SetGeometry(g)
                ml.CreateFeature(ft)
            gdal.RasterizeLayer(d, [1], ml, burn_values=[burn])
            mem = None
        d = None
        v = None
        ped = self.out / "pedologia_integrada.gpkg"
        if ped.exists():
            ped.unlink()
        d = ogr.GetDriverByName("GPKG").CreateDataSource(str(ped))
        pl = d.CreateLayer("pedologia", srs(c["epsg"]), ogr.wkbMultiPolygon)
        for name, kind in [
            ("solo_code", ogr.OFTInteger),
            ("fonte_id", ogr.OFTInteger),
            ("classe_original", ogr.OFTString),
        ]:
            pl.CreateField(ogr.FieldDefn(name, kind))

        def code(label):
            t = norm(label)
            if "URBANA" in t:
                return 250
            if "AGUA" in t:
                return 0
            for token, n in [
                ("LATOSSOLO", 1),
                ("PLINTOSSOLO", 2),
                ("ARGISSOLO", 3),
                ("LITOLICO", 4),
                ("GLEISSOLO", 5),
                ("HIDROMORF", 5),
                ("FLUVICO", 6),
                ("CAMBISSOLO", 7),
                ("NITOSSOLO", 8),
                ("QUARTZAREN", 9),
                ("ESPODOSSOLO", 10),
            ]:
                if token in t:
                    return n
            return 254

        def add(g, cl, origin):
            if g is None or g.IsEmpty():
                return
            if not g.IsValid():
                g = g.MakeValid()
            if g.GetDimension() != 2:
                return
            ft = ogr.Feature(pl.GetLayerDefn())
            ft.SetField("solo_code", code(cl))
            ft.SetField("fonte_id", origin)
            ft.SetField("classe_original", str(cl or ""))
            ft.SetGeometry(ogr.ForceToMultiPolygon(g))
            pl.CreateFeature(ft)

        v = ogr.Open(str(ibge))
        urban = None
        for f in v.GetLayer(0):
            label = f.GetField(c["campos"]["ibge"])
            g = f.GetGeometryRef().Intersection(self.geom)
            if code(label) == 250:
                urban = g.Clone() if urban is None else urban.Union(g)
            add(g, label, 1)
        v = None
        d.SyncToDisk()
        # Guardar primeiro a camada IBGE; depois sobrescrever somente a mascara urbana.
        soil = self.create(outputs[3], res, gdal.GDT_Byte, 255)
        origin = self.create(outputs[4], res, gdal.GDT_Byte, 0)
        gdal.RasterizeLayer(soil, [1], pl, options=["ATTRIBUTE=solo_code"])
        gdal.RasterizeLayer(origin, [1], pl, options=["ATTRIBUTE=fonte_id"])
        if urban is not None:
            v = ogr.Open(str(ibram))
            ll = v.GetLayer(0)
            ll.SetSpatialFilter(urban)
            covered = None
            for f in ll:
                clipped = f.GetGeometryRef().Intersection(urban)
                add(clipped, f.GetField(c["campos"]["ibram"]), 2)
                if not clipped.IsEmpty():
                    covered = clipped.Clone() if covered is None else covered.Union(clipped)
            pl.SetAttributeFilter("fonte_id = 2")
            gdal.RasterizeLayer(soil, [1], pl, options=["ATTRIBUTE=solo_code"])
            gdal.RasterizeLayer(origin, [1], pl, options=["ATTRIBUTE=fonte_id"])
            pl.SetAttributeFilter(None)
            v = None
            # A camada vetorial tambem deve conter a substituicao, sem manter
            # o poligono urbano IBGE inteiro sobreposto ao complemento IBRAM.
            pl.SetAttributeFilter("solo_code = 250 AND fonte_id = 1")
            urban_ids = [f.GetFID() for f in pl]
            pl.SetAttributeFilter(None)
            for fid in urban_ids:
                pl.DeleteFeature(fid)
            if covered is not None:
                add(urban.Difference(covered), "Area Urbana", 1)
            else:
                add(urban, "Area Urbana", 1)
        soil = None
        origin = None
        d = None
        inputs = [gdal.Open(str(p)) for p in outputs[:4]]
        terrain = gdal.Open(str(self.out / "mde_momentos.tif"))
        mask = gdal.Open(str(self.mask(res)))
        writers = [self.create(p, res) for p in outputs[5:]]
        for y in range(0, terrain.RasterYSize, 256):
            n = min(256, terrain.RasterYSize - y)
            arrays = [dd.ReadAsArray(0, y, terrain.RasterXSize, n) for dd in inputs]
            lc, bld, road, sc = arrays
            valid = (mask.ReadAsArray(0, y, terrain.RasterXSize, n) > 0) & (lc != 255)
            imp = np.full(lc.shape, np.nan, dtype="float32")
            rough = imp.copy()
            cn = imp.copy()
            cb = imp.copy()
            hsg = np.full(lc.shape, -1, dtype="int8")
            for k, (_, group) in SOILS.items():
                hsg[sc == k] = group
            for k in [*CN, 241, 242, 243, 244]:
                base = 24 if k in c["codigos_urbanos"] else k
                take = lc == k
                imp[take] = IMPBASE[base]
                rough[take] = ROUGHNESS[base]
                cb[take] = CBASE[base]
                for group in range(4):
                    cn[take & (hsg == group)] = CN[base][group]
            take = road == 1
            imp[take] = 0.10
            rough[take] = 0.035
            cb[take] = 0.45
            cn[take] = 89
            take = (road == 2) | (bld > 0)
            imp[take] = 1
            rough[take] = 0.015
            cb[take] = 0.90
            cn[take] = 98
            water = lc == 33
            imp[water] = 0
            rough[water] = 0.045
            cb[water] = 1
            cn[water] = 98
            z = terrain.ReadAsArray(0, y, terrain.RasterXSize, n)
            condition = z.copy()
            condition[(road > 0) & ~water] -= c["rebaixamento_vias_m"]
            for wr, a in zip(writers, [imp, rough, cn, cb, condition]):
                a = np.where(valid & np.isfinite(a) & (z != NODATA), a, NODATA).astype("float32")
                wr.GetRasterBand(1).WriteArray(a, 0, y)
        close_datasets(*writers, *inputs, terrain, mask)
        writers.clear()
        inputs.clear()
        terrain = None
        mask = None
        self.mark("02_superficies", [*outputs, self.out / "pedologia_integrada.gpkg"])

    def grass(self):
        c = self.c
        res = c["resolucao_hidrologia_m"]
        names = [
            "hidro_dem",
            "hidro_direcao",
            "hidro_acumulacao",
            "hidro_trechos",
            "hidro_bacias",
            "hidro_twi",
        ]
        outputs = [self.out / (n + ".tif") for n in names]
        if self.done("03_grass", outputs):
            return
        dem = self.tmp / "dem_entrada_grass.tif"
        self.warp(self.out / "mde_condicionado.tif", dem, res, "average")
        qr = Path(c["qgis_root"])
        grasses = sorted((qr / "apps" / "grass").glob("grass*"))
        if not grasses:
            raise RuntimeError("GRASS nao encontrado no QGIS configurado.")
        gb = grasses[-1]
        env = os.environ.copy()
        env.update(
            GISBASE=str(gb),
            GRASS_PYDIR=str(gb / "etc" / "python"),
            GRASS_PYTHON=sys.executable,
            GRASS_COMPATIBILITY_TEST="0",
            GRASS_PROJSHARE=str(qr / "share" / "proj"),
        )
        env["PYTHONPATH"] = str(gb / "etc" / "python") + os.pathsep + env.get("PYTHONPATH", "")
        env["PATH"] = str(gb / "bin") + os.pathsep + str(gb / "lib") + os.pathsep + env["PATH"]
        env["TMP"] = str(self.tmp)
        env["TEMP"] = str(self.tmp)
        env["GRASS_VERBOSE"] = "0"
        job = self.tmp / "grass_job.json"
        save_json(
            job,
            {
                "dem": str(dem),
                "out": str(self.out),
                "res": res,
                "threshold": max(2, round(c["limiar_drenagem_km2"] * 1e6 / res**2)),
                "memory": c["memoria_grass_mb"],
            },
        )
        launcher = gb / "etc" / (gb.name + ".py")
        command = [
            sys.executable,
            str(launcher),
            "--tmp-project",
            str(dem),
            "--exec",
            sys.executable,
            str(SCRIPT),
            "--grass-worker",
            str(job),
        ]
        self.log("GRASS: condicionamento e drenagem D8.")
        run_command(command, env, self.log)
        self.mark("03_grass", outputs)


def run_command(command, env, log):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    ) as p:
        for line in p.stdout:
            if line.strip():
                log(line.strip())
        if p.wait() != 0:
            raise RuntimeError("Falha no processo externo; consultar execucao.log.")


def grass_worker(path):
    import grass.script as gs

    j = json.loads(Path(path).read_text(encoding="utf-8"))
    out = Path(j["out"])
    gs.run_command("r.in.gdal", input=j["dem"], output="z", overwrite=True)
    gs.run_command("g.region", raster="z")
    gs.run_command(
        "r.fill.dir", input="z", output="zfill", direction="filldir", areas="sinks", overwrite=True
    )
    gs.run_command(
        "r.watershed",
        flags="s",
        elevation="zfill",
        threshold=j["threshold"],
        memory=j["memory"],
        accumulation="acc",
        drainage="dir",
        stream="streams",
        basin="basins",
        tci="twi",
        overwrite=True,
    )
    for source, name, typ in [
        ("zfill", "hidro_dem", "Float32"),
        ("dir", "hidro_direcao", "Int16"),
        ("acc", "hidro_acumulacao", "Float64"),
        ("streams", "hidro_trechos", "Int32"),
        ("basins", "hidro_bacias", "Int32"),
        ("twi", "hidro_twi", "Float64"),
    ]:
        gs.run_command(
            "r.out.gdal",
            flags="c",
            input=source,
            output=str(out / (name + ".tif")),
            format="GTiff",
            type=typ,
            nodata=-9999,
            createopt="TILED=YES,COMPRESS=DEFLATE,BIGTIFF=IF_SAFER",
            overwrite=True,
        )


def downstream_graph(direction, valid):
    h, w = direction.shape
    n = h * w
    dr = np.array([0, -1, -1, -1, 0, 1, 1, 1, 0])
    dc = np.array([0, 1, 0, -1, -1, -1, 0, 1, 1])
    codes = direction.ravel().astype("int16")
    ix = np.arange(n, dtype="int32")
    rr = ix // w
    cc = ix % w
    safe = np.clip(codes, 0, 8)
    rn = rr + dr[safe]
    cn = cc + dc[safe]
    target = rn * w + cn
    ok = valid.ravel() & (codes > 0) & (codes <= 8) & (rn >= 0) & (rn < h) & (cn >= 0) & (cn < w)
    ok &= valid.ravel()[np.clip(target, 0, n - 1)]
    down = np.where(ok, target, -1).astype("int32")
    indeg = np.bincount(down[down >= 0], minlength=n).astype("int16")
    frontier = np.flatnonzero(valid.ravel() & (indeg == 0)).astype("int32")
    parts = []
    while frontier.size:
        parts.append(frontier)
        dest = down[frontier]
        dest = dest[dest >= 0]
        np.add.at(indeg, dest, -1)
        unique = np.unique(dest)
        frontier = unique[indeg[unique] == 0]
    order = np.concatenate(parts) if parts else np.array([], dtype="int32")
    if order.size != np.count_nonzero(valid):
        raise RuntimeError("Ciclo ou direcao inconsistente na grade D8.")
    return down, order


def reverse_trace(down, order, seed, dem, velocity, res, shape):
    n = len(down)
    w = shape[1]
    catch = seed.ravel().astype("int32").copy()
    bed = np.full(n, np.nan, dtype="float32")
    travel = np.zeros(n, dtype="float32")
    selected = catch > 0
    bed[selected] = dem.ravel()[selected]
    # Uma passagem inversa pela ordem topologica, em blocos de niveis, mantem
    # dependencia jusante -> montante sem resolver proximidade euclidiana.
    # A ordem e percorrida explicitamente: esta e uma etapa custosa na bacia toda.
    for i in order[::-1]:
        if catch[i] > 0:
            continue
        j = down[i]
        if j < 0 or catch[j] == 0:
            continue
        catch[i] = catch[j]
        bed[i] = bed[j]
        diagonal = abs(int(i) // w - int(j) // w) + abs(int(i) % w - int(j) % w) == 2
        travel[i] = travel[j] + res * (math.sqrt(2) if diagonal else 1) / max(
            float(velocity.ravel()[i]), 0.05
        )
    return catch.reshape(shape), bed.reshape(shape), travel.reshape(shape)


def ramp(x, a, b):
    return np.clip((x - a) / (b - a), 0, 1)


def tri(x, a, b, c):
    return np.minimum(ramp(x, a, b), 1 - ramp(x, b, c))


def fahp(notas):
    n = len(notas)
    scores = np.asarray(notas, dtype=float)
    diff = scores[:, None] - scores[None, :]
    central = np.empty_like(diff)
    positive = diff >= 0
    central[positive] = diff[positive] + 1
    central[~positive] = 1 / (1 - diff[~positive])
    tf = np.zeros((n, n, 3))
    for i in range(n):
        for j in range(n):
            v = central[i, j]
            if v == 1:
                tf[i, j] = [1, 1, 1]
            elif v > 1:
                tf[i, j] = [max(1, v - 1), v, min(9, v + 1)]
            else:
                a = 1 / v
                tf[i, j] = [1 / min(9, a + 1), 1 / a, 1 / max(1, a - 1)]
    r = np.exp(np.mean(np.log(tf), axis=1))
    tot = r.sum(axis=0)
    fuzzy = r / tot[::-1]
    weights = fuzzy.mean(axis=1)
    weights /= weights.sum()
    lam = np.max(np.linalg.eigvals(central).real)
    ri = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}[n]
    cr = 0 if ri == 0 else (lam - n) / (n - 1) / ri
    return weights, central, fuzzy, float(cr)


def idf(c, tr, t):
    p = c["idf"]
    return p["K"] * tr ** p["a"] / (np.asarray(t) + p["b"]) ** p["c"]


def storm(c, tr, duration):
    dt = c["passo_hidrograma_min"]
    n = math.ceil(duration / dt)
    t = np.arange(1, n + 1) * dt
    total = idf(c, tr, t) * t / 60
    increments = np.diff(np.r_[0, total])
    if np.any(increments < 0):
        raise ValueError("IDF produziu incrementos negativos.")
    ordered = np.sort(increments)[::-1]
    out = np.zeros(n)
    mid = (n - 1) // 2
    positions = [mid]
    for step in range(1, n + 1):
        if mid + step < n:
            positions.append(mid + step)
        if mid - step >= 0:
            positions.append(mid - step)
    out[np.asarray(positions[:n])] = ordered
    return out


def scs_excess(rain, cn, ia_fraction=0.2):
    retention = 25400 / np.clip(cn, 30, 98) - 254
    cum = np.cumsum(rain)
    p = np.maximum(cum - ia_fraction * retention, 0)
    excess = p * p / (p + retention)
    return np.maximum(np.diff(np.r_[0, excess]), 0)


def triangular_kernel(tc_seconds, dt):
    peak = dt / 2 + 0.6 * max(tc_seconds, dt)
    base = 2.67 * peak
    n = max(1, math.ceil(base / dt))
    t = np.arange(n + 1) * dt
    f = np.where(
        t <= peak,
        t * t / (base * peak),
        1 - (base - np.minimum(t, base)) ** 2 / (base * (base - peak)),
    )
    f = np.clip(f, 0, 1)
    k = np.diff(f)
    return k / k.sum()


def route_linear(q, k_seconds, dt, delay_seconds=0):
    if k_seconds <= 0:
        out = q.copy()
        storage = 0.0
    else:
        a = math.exp(-dt / k_seconds)
        end = signal.lfilter([1 - a], [1, -a], q)
        prev = np.r_[0, end[:-1]]
        out = q + (prev - q) * (1 - a) * k_seconds / dt
        storage = float(k_seconds * end[-1])
    delay = max(0, float(delay_seconds) / dt)
    whole = int(delay)
    fraction = delay - whole
    shifted = np.zeros_like(out)
    if whole < len(out):
        shifted[whole:] += (1 - fraction) * out[: len(out) - whole]
    if whole + 1 < len(out):
        shifted[whole + 1 :] += fraction * out[: len(out) - whole - 1]
    queued = max(0, float((out.sum() - shifted.sum()) * dt))
    return shifted, storage + queued


def reach_order(parent):
    n = len(parent)
    indeg = np.bincount(parent[parent > 0], minlength=n).astype(int)
    front = list(np.flatnonzero((indeg == 0) & (np.arange(n) > 0)))
    order = []
    while front:
        i = front.pop()
        order.append(i)
        p = int(parent[i])
        if p > 0:
            indeg[p] -= 1
            if indeg[p] == 0:
                front.append(p)
    if len(order) != n - 1:
        raise ValueError("Ciclo na rede de trechos.")
    return order


def read_grid(path):
    d = gdal.Open(str(path))
    a = d.ReadAsArray()
    d = None
    return a


def network(p):
    c = p.c
    r = c["resolucao_hidrologia_m"]
    cache = p.tmp / "rede_calculo.npz"
    products = [
        cache,
        *[
            p.out / (name + ".tif")
            for name in [
                "hand_hidro",
                "referencia_canal_hidro",
                "contribuicao_trecho_hidro",
                "distancia_drenagem_hidro",
                "velocidade_proxy_hidro",
                "controle_reservatorio_hidro",
            ]
        ],
    ]
    if p.done("04_rede", products):
        with np.load(cache) as saved:
            return {k: saved[k] for k in saved.files}
    p.log("Construindo grafo D8, HAND por caminho de fluxo e rede de contribuicoes.")
    paths = {}
    for name, method in [
        ("uso_classes", "near"),
        ("cn_ii", "average"),
        ("rugosidade", "average"),
        ("mde_momentos", "average"),
    ]:
        dest = p.tmp / (name + "_hidro.tif")
        p.warp(
            p.out / (name + ".tif"),
            dest,
            r,
            method,
            nodata=255 if name == "uso_classes" else NODATA,
        )
        paths[name] = dest
    dem = read_grid(paths["mde_momentos"])
    direction = read_grid(p.out / "hidro_direcao.tif")
    acc = np.abs(read_grid(p.out / "hidro_acumulacao.tif"))
    raw = read_grid(p.out / "hidro_trechos.tif")
    valid = (read_grid(p.mask(r)) > 0) & (dem != NODATA) & np.isfinite(dem)
    lc = read_grid(paths["uso_classes"])
    rough = read_grid(paths["rugosidade"])
    raw = np.where((raw > 0) & valid, raw, 0).astype("int32")
    water_labels, _ = ndimage.label((lc == 33) & valid)
    counts = np.bincount(water_labels.ravel())
    large = np.flatnonzero(counts * r * r >= c["massa_agua_grande_km2"] * 1e6)
    large = large[large > 0]
    lake = np.isin(water_labels, large)
    seed = raw.copy()
    maximum = int(seed.max())
    for k, label in enumerate(large, 1):
        seed[water_labels == label] = maximum + k
    # Cada componente grande de agua e terminal hidrologico, sem operacao presumida.
    original = np.unique(seed[seed > 0])
    if not len(original):
        raise RuntimeError(
            "Nenhum canal extraido; conferir terreno/limiar ou ampliar recorte piloto."
        )
    seed = np.where(seed > 0, np.searchsorted(original, seed) + 1, 0).astype("int32")
    n = len(original) + 1
    lake_reach = np.r_[False, original > maximum]
    filled = np.where(valid, dem, 0)
    # Preencher somente vizinhos usados na derivada; celulas invalidas continuam mascaradas.
    if (~valid).any():
        ix = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
        filled = dem[tuple(ix)]
    sy, sx = np.gradient(filled, r)
    slope = np.hypot(sx, sy)
    slope = np.maximum(slope, 1e-5)
    v = np.clip(
        (c["altura_escoamento_lamina_tc_m"] ** (2 / 3) / np.maximum(rough, 0.015)) * np.sqrt(slope),
        *c["manning_limites_velocidade_ms"],
    )
    down, order = downstream_graph(direction, valid)
    catch, bed, travel = reverse_trace(down, order, seed, dem, v, r, dem.shape)
    hand = np.maximum(dem - bed, 0)
    hand[~valid | ~np.isfinite(bed)] = np.nan
    channel = (seed > 0) & ~lake
    distance = ndimage.distance_transform_edt(~channel, sampling=r).astype("float32")
    area = np.bincount(catch.ravel(), weights=valid.ravel() * r * r, minlength=n)
    cn = read_grid(paths["cn_ii"])
    cn_good = valid & (cn != NODATA) & np.isfinite(cn) & (catch > 0)
    cn_count = np.bincount(catch[cn_good], minlength=n)
    cnmean = np.divide(
        np.bincount(catch[cn_good], weights=cn[cn_good], minlength=n),
        cn_count,
        out=np.full(n, np.nan),
        where=cn_count > 0,
    )
    tc = np.zeros(n)
    np.maximum.at(tc, catch[valid], travel[valid])
    tc = np.maximum(tc, c["passo_hidrograma_min"] * 60)
    parent = np.zeros(n, dtype="int32")
    raw_parent = parent.copy()
    length = np.zeros(n)
    reach_slope = np.zeros(n)
    flatseed = seed.ravel()
    flatacc = acc.ravel()
    flatdem = dem.ravel()
    for rid in range(1, n):
        cells = np.flatnonzero(flatseed == rid)
        best = cells[np.argmax(flatacc[cells])]
        length[rid] = max(r, len(cells) * r)
        reach_slope[rid] = max(
            0.0001, (float(np.max(flatdem[cells])) - float(np.min(flatdem[cells]))) / length[rid]
        )
        j = int(down[best])
        seen = 0
        while j >= 0 and (flatseed[j] == 0 or flatseed[j] == rid) and seen < len(order):
            j = int(down[j])
            seen += 1
        if j >= 0:
            raw_parent[rid] = int(flatseed[j])
        parent[rid] = 0 if lake_reach[rid] else raw_parent[rid]
    topo = np.asarray(reach_order(parent), dtype="int32")
    controlled = np.zeros(n, dtype=bool)
    controlled[lake_reach] = True
    for rid in np.flatnonzero(lake_reach):
        j = int(raw_parent[rid])
        seen = set()
        while j > 0 and j not in seen:
            controlled[j] = True
            seen.add(j)
            j = int(raw_parent[j])
    control = controlled[catch] | lake
    # Curvas HAND-SRC: distribuicao de alturas de cada area local de trecho.
    step = c["passo_altura_curva_chave_m"]
    nb = math.ceil(c["limite_altura_curva_chave_m"] / step) + 1
    take = valid & (catch > 0) & np.isfinite(hand) & (hand < nb * step)
    bins = np.floor(np.clip(hand[take] / step, 0, nb - 1)).astype("int32")
    group = catch[take] * nb + bins
    hist = np.bincount(group, minlength=n * nb).reshape(n, nb).astype("float64")
    sums = np.bincount(group, weights=hand[take], minlength=n * nb).reshape(n, nb)
    levels = np.arange(nb) * step
    countcum = np.cumsum(hist, axis=1)
    sumcum = np.cumsum(sums, axis=1)
    crossarea = (
        np.maximum(levels[None, :] * countcum - sumcum, 0) * r * r / np.maximum(length[:, None], r)
    )
    topwidth = countcum * r * r / np.maximum(length[:, None], r)
    perimeter = topwidth + 2 * levels[None, :]
    radius = np.divide(crossarea, perimeter, out=np.zeros_like(crossarea), where=perimeter > 0)
    rating = (crossarea * radius ** (2 / 3) * np.sqrt(reach_slope[:, None])) / c["manning_canal"]
    rating = np.maximum.accumulate(rating, axis=1)
    velocity_channel = np.clip(
        c["raio_hidraulico_referencia_tc_m"] ** (2 / 3) / c["manning_canal"] * np.sqrt(reach_slope),
        0.1,
        5.0,
    )
    route_k = np.maximum(length / velocity_channel, 60.0)
    for name, a in [
        ("hand_hidro", hand),
        ("referencia_canal_hidro", bed),
        ("distancia_drenagem_hidro", distance),
        ("velocidade_proxy_hidro", v),
    ]:
        p.write(
            p.out / (name + ".tif"),
            np.where(valid & np.isfinite(a), a, NODATA).astype("float32"),
            r,
        )
    p.write(
        p.out / "contribuicao_trecho_hidro.tif", np.where(valid, catch, 0), r, gdal.GDT_Int32, 0
    )
    p.write(
        p.out / "controle_reservatorio_hidro.tif",
        np.where(valid, control, 255).astype("uint8"),
        r,
        gdal.GDT_Byte,
        255,
    )
    data = dict(
        catch=catch,
        hand=hand,
        valid=valid,
        lake=lake,
        parent=parent,
        controlled=controlled,
        lake_reach=lake_reach,
        topo=topo,
        area=area,
        cn=cnmean,
        tc=tc,
        length=length,
        slope=reach_slope,
        route_k=route_k,
        levels=levels,
        rating=rating,
    )
    np.savez(cache, **data)
    p.mark("04_rede", products)
    p.warn(
        "Operacao de reservatorios e remanso nao simulados: margens ligadas diretamente a grandes massas de agua e trechos controlados a jusante ficam sem nivel de cheia calculado."
    )
    return data


def texture(p):
    outputs = [p.out / "areia_0_30_percent.tif", p.out / "argila_0_30_percent.tif"]
    if p.done("05_textura", outputs):
        return
    p.log("Obtendo recortes SoilGrids 250 m; sem substituir falhas por valores inventados.")
    local = p.root / "soilgrids"
    for prop, output in zip(["sand", "clay"], outputs):
        rasters = []
        for depth in ["0-5", "5-15", "15-30"]:
            base = f"{prop}_{depth}cm_mean"
            native = local / (base + ".tif")
            if not native.exists():
                source = (
                    "/vsicurl/https://files.isric.org/soilgrids/latest/data/"
                    + prop
                    + "/"
                    + base
                    + ".vrt"
                )
                stage = p.tmp / (base + "_250m.tif")
                # Cache de aquisicao independe da revisao do codigo: conferir
                # grade, cobertura e valores evita baixar novamente em testes.
                usable = False
                if stage.exists():
                    try:
                        cached = gdal.Open(str(stage))
                        gt = cached.GetGeoTransform()
                        aa = cached.ReadAsArray()
                        usable = (
                            abs(gt[0] - p.bbox[0]) < 0.01
                            and abs(gt[3] - p.bbox[3]) < 0.01
                            and abs(gt[1] - 250) < 0.01
                            and abs(gt[5] + 250) < 0.01
                            and cached.RasterXSize == round((p.bbox[2] - p.bbox[0]) / 250)
                            and cached.RasterYSize == round((p.bbox[3] - p.bbox[1]) / 250)
                            and np.any(np.isfinite(aa) & (aa >= 0) & (aa <= 1000))
                        )
                        cached = None
                    except RuntimeError:
                        pass
                if not usable:
                    p.warp(source, stage, 250, "bilinear")
            else:
                stage = native
            warped = p.tmp / (base + "_modelo.tif")
            p.warp(stage, warped, p.c["resolucao_momentos_m"], "bilinear")
            rasters.append(gdal.Open(str(warped)))
        out = p.create(output, p.c["resolucao_momentos_m"])
        for y in range(0, out.RasterYSize, 256):
            n = min(256, out.RasterYSize - y)
            a = np.stack([d.ReadAsArray(0, y, out.RasterXSize, n) for d in rasters])
            valid = np.all(np.isfinite(a) & (a >= 0) & (a <= 1000), axis=0)
            mean = (a[0] * 5 + a[1] * 10 + a[2] * 15) / 300  # g/kg -> %, profundidade ponderada
            out.GetRasterBand(1).WriteArray(np.where(valid, mean, NODATA).astype("float32"), 0, y)
        close_datasets(out, *rasters)
        out = None
        rasters.clear()
    p.mark("05_textura", outputs)


def hydrograph_steps(c, d):
    """Janela causal: so canais propagam vazao; lagos sao terminais."""
    path_k = np.zeros(len(d["parent"]))
    for rid in d["topo"][::-1]:
        routing_time = 0.0 if d["lake_reach"][rid] else d["route_k"][rid]
        path_k[rid] = routing_time + path_k[d["parent"][rid]]
    tail = max(float(path_k.max()) * 12, float(d["tc"].max()) * 3, 24 * 3600.0)
    dt = c["passo_hidrograma_min"] * 60
    nt = math.ceil((max(c["duracoes_chuva_min"]) * 60 + tail) / dt) + 2
    if nt > 10000:
        raise RuntimeError(
            "Tempo de percurso excessivo nos canais; revisar caminhos, declividades e parametros de velocidade antes da simulacao."
        )
    return nt


def hydrographs(p, d):
    products = [p.out / f"inundacao_profundidade_TR{tr}_hidro.tif" for tr in p.c["tempos_retorno"]]
    products += [
        p.out / "frequencia_menor_TR_hidro.tif",
        p.out / "hidrologia_trechos.csv",
        p.out / "balanco_hidrologico.json",
    ]
    if p.done("06_hidrologia", products):
        return
    c = p.c
    n = len(d["parent"])
    dt = c["passo_hidrograma_min"] * 60
    all_rows = []
    balances = []
    if np.any((d["area"][1:] > 0) & ~np.isfinite(d["cn"][1:])):
        raise RuntimeError("Area contribuinte sem CN: conferir lacunas pedologicas/cobertura.")
    nt = hydrograph_steps(c, d)
    p.log(f"Janela hidrologica: {nt} passos de {dt/60:g} min ({nt*dt/3600:.1f} h).")
    frequency = np.zeros(d["catch"].shape, dtype="int16")
    frequency[~d["valid"] | (d["catch"] == 0)] = -9999
    frequency[d["controlled"][d["catch"]]] = -9999
    for tr in c["tempos_retorno"]:
        p.log(f"Hidrogramas TR {tr}: {n-1} unidades; {len(c['duracoes_chuva_min'])} duracoes.")
        peak = np.zeros(n)
        critical = np.zeros(n, dtype="int32")
        for duration in c["duracoes_chuva_min"]:
            rain = storm(c, tr, duration)
            incoming = np.zeros((n, nt), dtype="float64")
            initial_volume = 0.0
            storage = 0.0
            terminal = 0.0
            for rid in d["topo"]:
                excess = scs_excess(rain, d["cn"][rid], c["abstracao_inicial_fracao_S"])
                source = excess * d["area"][rid] / 1000 / dt
                initial_volume += float(source.sum() * dt)
                local = signal.fftconvolve(source, triangular_kernel(d["tc"][rid], dt))
                if len(local) > nt:
                    raise RuntimeError("Janela de hidrograma insuficiente.")
                incoming[rid, : len(local)] += local
                if d["lake_reach"][rid]:
                    terminal += float(incoming[rid].sum() * dt)
                    q = incoming[rid]
                else:
                    q, stored = route_linear(
                        incoming[rid], d["route_k"][rid] * 0.5, dt, d["route_k"][rid] * 0.5
                    )
                    storage += stored
                    parent = int(d["parent"][rid])
                    if parent:
                        incoming[parent] += q
                    else:
                        terminal += float(q.sum() * dt)
                value = max(0, float(q.max()))
                if value > peak[rid]:
                    peak[rid] = value
                    critical[rid] = duration
            error = abs(initial_volume - terminal - storage) / max(initial_volume, 1.0)
            balances.append(
                {
                    "TR": tr,
                    "duracao_min": duration,
                    "volume_excesso_m3": initial_volume,
                    "volume_saidas_e_entrada_lagos_m3": terminal,
                    "armazenado_ou_em_transito_final_m3": storage,
                    "erro_relativo": error,
                    "passos_janela": nt,
                }
            )
            if error > 1e-5:
                raise RuntimeError(f"Balanco de massa inconsistente: {error:.2%}")
            del incoming
        stages = np.full(n, np.nan)
        flags = [""] * n
        for rid in range(1, n):
            if d["controlled"][rid]:
                flags[rid] = "RESERVATORIO_SEM_OPERACAO_OU_JUSANTE_CONTROLADA"
                continue
            rating = d["rating"][rid]
            if rating[-1] <= 0 or peak[rid] > rating[-1]:
                flags[rid] = "FORA_DA_CURVA_CHAVE"
                continue
            stages[rid] = 0.0 if peak[rid] <= 0 else np.interp(peak[rid], rating, d["levels"])
        z = stages[d["catch"]]
        depth = np.maximum(z - d["hand"], 0)
        good = d["valid"] & np.isfinite(depth) & (d["catch"] > 0)
        output = np.where(good, depth, NODATA).astype("float32")
        p.write(
            p.out / f"inundacao_profundidade_TR{tr}_hidro.tif", output, c["resolucao_hidrologia_m"]
        )
        wet = good & (depth > 0.05) & (frequency == 0)
        frequency[wet] = tr
        frequency[(~good) & (frequency == 0)] = -9999
        for rid in range(1, n):
            all_rows.append(
                [
                    tr,
                    rid,
                    int(d["parent"][rid]),
                    float(d["area"][rid] / 1e6),
                    float(d["cn"][rid]),
                    float(d["tc"][rid] / 60),
                    float(peak[rid]),
                    int(critical[rid]),
                    float(stages[rid]) if np.isfinite(stages[rid]) else "",
                    flags[rid],
                ]
            )
    p.write(
        p.out / "frequencia_menor_TR_hidro.tif",
        frequency,
        c["resolucao_hidrologia_m"],
        gdal.GDT_Int16,
        -9999,
    )
    write_csv(
        p.out / "hidrologia_trechos.csv",
        [
            "TR",
            "trecho",
            "jusante",
            "area_local_km2",
            "CN_II",
            "tc_local_min",
            "Q_pico_m3s",
            "duracao_critica_min",
            "altura_sobre_canal_m",
            "limitacao",
        ],
        all_rows,
    )
    save_json(p.out / "balanco_hidrologico.json", balances)
    p.mark("06_hidrologia", products)


def write_csv(path, header, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


def estimate_groundwater(p):
    dest = p.out / "lencol_estimado.tif"
    report = p.out / "ajuste_lencol.json"
    handpath = p.out / "hand_referenciado_5m.tif"
    if p.done("07_lencol", [dest, report, handpath]):
        return json.loads(report.read_text(encoding="utf-8"))
    c = p.c
    res = c["resolucao_momentos_m"]
    # O terreno fino e a referencia de canal do caminho hidrologico grosso.
    bedpath = p.tmp / "referencia_canal_modelo.tif"
    p.warp(p.out / "referencia_canal_hidro.tif", bedpath, res, "near")
    z = gdal.Open(str(p.out / "mde_momentos.tif"))
    b = gdal.Open(str(bedpath))
    h = p.create(handpath, res)
    for y in range(0, z.RasterYSize, 256):
        nr = min(256, z.RasterYSize - y)
        aa = z.ReadAsArray(0, y, z.RasterXSize, nr)
        bb = b.ReadAsArray(0, y, z.RasterXSize, nr)
        v = (aa != NODATA) & (bb != NODATA) & np.isfinite(aa) & np.isfinite(bb)
        h.GetRasterBand(1).WriteArray(
            np.where(v, np.maximum(aa - bb, 0), NODATA).astype("float32"), 0, y
        )
    h = None
    z = None
    b = None
    points = ogr.Open(str(p.vector("pocos")))
    layer = points.GetLayer(0)
    ds = gdal.Open(str(handpath))
    gt = ds.GetGeoTransform()
    obs = []
    for f in layer:
        g = f.GetGeometryRef()
        ne = f.GetField(c["campos"]["ne"])
        if g.GetGeometryType() in [ogr.wkbMultiPoint, ogr.wkbMultiPoint25D]:
            g = g.GetGeometryRef(0)
        if ne is None or ne <= 0 or not g.Within(p.geom):
            continue
        col = int((g.GetX() - gt[0]) / gt[1])
        row = int((g.GetY() - gt[3]) / gt[5])
        if not (0 <= col < ds.RasterXSize and 0 <= row < ds.RasterYSize):
            continue
        value = float(ds.ReadAsArray(col, row, 1, 1)[0, 0])
        if not np.isfinite(value) or value == NODATA or value < 0.2:
            continue
        nd = f.GetField("nd") if f.GetFieldIndex("nd") >= 0 else None
        obs.append(
            {
                "id": str(int(f.GetField(c["campos"]["id_poco"]))),
                "hand": value,
                "ne": float(ne),
                "monitoramento": "MONITOR" in norm(f.GetField("natureza_ponto")),
                "inconsistencia_nd_ne": bool(nd is not None and nd > 0 and nd < ne),
            }
        )
    monitored = [o for o in obs if o["monitoramento"] and not o["inconsistencia_nd_ne"]]
    selected = (
        monitored
        if c["preferir_pocos_monitoramento"]
        else [o for o in obs if not o["inconsistencia_nd_ne"]]
    )
    info = {
        "modelo": "NE=0.5+b*HAND; regressao robusta; exploratorio",
        "pocos_disponiveis": len(obs),
        "monitoramento_disponiveis": len(monitored),
        "n_ajuste": len(selected),
        "aquifero_e_data_nao_verificados": True,
        "ajuste_aceito": False,
        "b": None,
        "rmse_m": None,
        "rho": None,
    }
    if len(selected) >= c["minimo_pocos_ajuste"]:
        x = np.array([o["hand"] for o in selected])
        yy = np.array([o["ne"] for o in selected])
        fit = optimize.least_squares(
            lambda bb: 0.5 + bb[0] * x - yy, [0.5], bounds=(0, 10), loss="soft_l1", f_scale=5
        )
        beta = float(fit.x[0])
        rho = float(stats.spearmanr(x, yy).statistic) if np.std(x) > 0 and np.std(yy) > 0 else 0.0
        info.update(
            b=beta,
            rmse_m=float(np.sqrt(np.mean((0.5 + beta * x - yy) ** 2))),
            rho=rho,
            ajuste_aceito=bool(beta > 1e-6 and rho >= 0.2 and np.std(x) > 1),
        )
    if not info["ajuste_aceito"]:
        p.warn(
            "Os pocos selecionados nao sustentaram o ajuste local do lencol; criterio ficara sem estimativa nas areas terrestres, com renormalizacao explicita dos pesos."
        )
    source = gdal.Open(str(handpath))
    soil = gdal.Open(str(p.out / "solo_integrado.tif"))
    lc = gdal.Open(str(p.out / "uso_classes.tif"))
    out = p.create(dest, res)
    for y in range(0, source.RasterYSize, 256):
        nr = min(256, source.RasterYSize - y)
        aa = source.ReadAsArray(0, y, source.RasterXSize, nr)
        sc = soil.ReadAsArray(0, y, source.RasterXSize, nr)
        land = lc.ReadAsArray(0, y, source.RasterXSize, nr)
        result = np.full(aa.shape, NODATA, dtype="float32")
        if info["ajuste_aceito"]:
            good = np.isfinite(aa) & (aa != NODATA)
            result[good] = 0.5 + info["b"] * aa[good]
            # Restricao paisagistica e hipotese, preservada como tal no relatorio.
            wet = good & ((sc == 5) | (land == 11))
            result[wet] = np.minimum(result[wet], 1.0)
        result[land == 33] = 0
        out.GetRasterBand(1).WriteArray(result, 0, y)
    out = None
    source = None
    soil = None
    lc = None
    ds = None
    points = None
    selected_ids = {o["id"] for o in selected}
    write_csv(
        p.out / "pocos_ajuste.csv",
        ["id", "HAND_m", "NE_m", "monitoramento", "nd_menor_ne_revisar", "selecionado_ajuste"],
        [
            [
                o["id"],
                o["hand"],
                o["ne"],
                o["monitoramento"],
                o["inconsistencia_nd_ne"],
                o["id"] in selected_ids,
            ]
            for o in obs
        ],
    )
    save_json(report, info)
    p.mark("07_lencol", [dest, report, handpath])
    return info


def memberships(v):
    """Regras OPERACIONAIS desta adaptacao; nao apresentadas como codigo do autor.

    Todas as rampas abaixo ficam documentadas em regras_pertinencia.txt.
    Nove triplas independentes: fonte, conducao, acomodacao.
    """
    slope = v["decl"]
    alt = v["alt"]
    soil = v["solo"]
    inf = v["infil"]
    water = v["uso"] == 33
    hand = v["hand"]
    ne = v["lencol"]
    dist = v["dren"]
    vel = v["flux"]
    area = v["area"]
    imp = v["imp"]
    lc = v["uso"]
    out = []
    out.append(np.stack([1 - ramp(slope, 4, 12), ramp(slope, 4, 12), 1 - ramp(slope, 1, 4)]))
    vel_log = np.log10(np.maximum(vel, 1e-5))
    mu = np.stack(
        [
            1 - ramp(area, 0.005, 0.08),
            ramp(vel_log, -1, 0.4) * ramp(area, 0.005, 0.15),
            ramp(area, 0.01, 0.2) * (1 - ramp(vel, 0.1, 0.8)) * (1 - ramp(hand, 2, 4)),
        ]
    )
    mu[:, water] = np.nan
    out.append(mu)
    out.append(
        np.stack([ramp(alt, 0.45, 0.75), tri(alt, 0.15, 0.5, 0.85), 1 - ramp(alt, 0.2, 0.5)])
    )
    table = {
        0: [0, 0, 1],
        1: [1, 0.2, 0.1],
        2: [0.2, 0.9, 0.3],
        3: [0.35, 0.85, 0.25],
        4: [0.2, 1, 0.15],
        5: [0.1, 0.2, 1],
        6: [0.2, 0.4, 0.9],
        7: [0.4, 0.8, 0.2],
        8: [0.8, 0.4, 0.15],
        9: [1, 0.25, 0.1],
        10: [0.4, 0.5, 0.7],
    }
    mu = np.full((3, *soil.shape), np.nan, dtype="float32")
    for code, values in table.items():
        for j in range(3):
            mu[j][soil == code] = values[j]
    out.append(mu)
    shallow = np.where(np.isfinite(ne), 1 - ramp(ne, 1, 4), 1 - ramp(hand, 1, 4))
    out.append(
        np.stack([ramp(inf, 10, 30), 1 - ramp(inf, 3, 20), (1 - ramp(inf, 3, 15)) * shallow])
    )
    out.append(np.stack([ramp(ne, 3, 10), tri(ne, 0.5, 4, 12), 1 - ramp(ne, 1, 3)]))
    freq = v["inund"]
    present = freq > 0
    mu = np.stack(
        [
            np.where(present, 0.0, 1.0),
            np.where(present, 0.1, 0.25),
            np.where(
                (freq > 0) & (freq <= 20),
                1.0,
                np.where((freq > 20) & (freq <= 100), 0.8, np.where(freq > 100, 0.5, 0.0)),
            ),
        ]
    )
    mu[:, ~np.isfinite(freq)] = np.nan
    out.append(mu)
    mu = np.stack([ramp(dist, 150, 400), tri(dist, 0, 120, 450), 1 - ramp(dist, 30, 120)])
    mu[:, water] = np.array([0, 0, 1])[:, None]
    out.append(mu)
    veg = np.isin(lc, [3, 4, 9, 11, 12, 15, 19, 21, 100])
    mu = np.stack(
        [(1 - imp) * np.where(veg, 1.0, 0.5), imp, np.where((lc == 11) | water, 1.0, 0.0)]
    )
    mu[:, water] = np.array([0, 0, 1])[:, None]
    out.append(mu)
    return np.clip(np.stack(out).astype("float32"), 0, 1)


def aggregate_mu(mu, weights):
    available = np.all(np.isfinite(mu), axis=1)
    numerator = np.sum(
        np.nan_to_num(mu, nan=0)
        * available[:, None, ...]
        * weights[:, None, *([None] * (mu.ndim - 2))],
        axis=0,
    )
    denominator = np.sum(available * weights[:, *([None] * (mu.ndim - 2))], axis=0)
    scores = np.divide(
        numerator,
        denominator[None, ...],
        out=np.full_like(numerator, np.nan),
        where=denominator[None, ...] > 0,
    )
    return scores, available.sum(axis=0)


def classify(p, lencol_info):
    c = p.c
    res = c["resolucao_momentos_m"]
    mainnames = [
        "momento_dominante",
        "grau_definicao",
        "margem_pertinencia",
        "numero_criterios",
        "fonte_impermeabilizada",
        "transicoes",
        "pertinencia_fonte",
        "pertinencia_conducao",
        "pertinencia_acomodacao",
    ]
    outputs = [p.out / (n + ".tif") for n in mainnames]
    if p.done(
        "08_momentos", outputs + [p.out / "sensibilidade.json", p.out / "areas_momentos.csv"]
    ):
        return
    p.log("Preparando criterios e combinacao FAHP por blocos.")
    for name, method in [
        ("distancia_drenagem_hidro", "bilinear"),
        ("velocidade_proxy_hidro", "bilinear"),
        ("hidro_acumulacao", "bilinear"),
        ("frequencia_menor_TR_hidro", "near"),
    ]:
        p.warp(p.out / (name + ".tif"), p.tmp / (name + "_modelo.tif"), res, method)
    for tr in c["tempos_retorno"]:
        p.warp(
            p.out / f"inundacao_profundidade_TR{tr}_hidro.tif",
            p.out / f"inundacao_profundidade_TR{tr}_visualizacao.tif",
            res,
            "near",
        )
    slopepath = p.out / "declividade_percent.tif"
    s = gdal.DEMProcessing(
        str(slopepath),
        str(p.out / "mde_momentos.tif"),
        "slope",
        slopeFormat="percent",
        computeEdges=True,
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"],
    )
    s = None
    paths = {
        "z": p.out / "mde_momentos.tif",
        "decl": slopepath,
        "solo": p.out / "solo_integrado.tif",
        "uso": p.out / "uso_classes.tif",
        "sand": p.out / "areia_0_30_percent.tif",
        "clay": p.out / "argila_0_30_percent.tif",
        "imp": p.out / "impermeabilizacao.tif",
        "hand": p.out / "hand_referenciado_5m.tif",
        "lencol": p.out / "lencol_estimado.tif",
        "dren": p.tmp / "distancia_drenagem_hidro_modelo.tif",
        "flux": p.tmp / "velocidade_proxy_hidro_modelo.tif",
        "area": p.tmp / "hidro_acumulacao_modelo.tif",
        "inund": p.tmp / "frequencia_menor_TR_hidro_modelo.tif",
    }
    readers = {k: gdal.Open(str(v)) for k, v in paths.items()}
    mask = gdal.Open(str(p.mask(res)))
    reference = readers["z"]
    width = reference.RasterXSize
    height = reference.RasterYSize
    hist = np.zeros(20000, dtype="int64")
    zmin = math.inf
    zmax = -math.inf
    for y in range(0, height, 256):
        nr = min(256, height - y)
        a = reference.ReadAsArray(0, y, width, nr)
        valid = (a != NODATA) & np.isfinite(a) & (mask.ReadAsArray(0, y, width, nr) > 0)
        if valid.any():
            zmin = min(zmin, float(a[valid].min()))
            zmax = max(zmax, float(a[valid].max()))
            hist += np.bincount(
                np.clip(np.rint(a[valid] * 10).astype(int), 0, 19999), minlength=20000
            )
    if not hist.sum():
        raise RuntimeError("MDE sem cobertura no recorte.")
    cdf = np.cumsum(hist) / hist.sum()
    weights, matrix, tfn, cr = fahp(c["notas_fahp"])
    if cr > 0.1:
        raise RuntimeError("Matriz FAHP inconsistente (CR>0.10).")
    save_json(
        p.out / "pesos_fahp.json",
        {
            "criterios": CRITERIA,
            "notas": c["notas_fahp"],
            "pesos": weights.tolist(),
            "matriz": matrix.tolist(),
            "pesos_fuzzy": tfn.tolist(),
            "CR": cr,
            "origem": "julgamentos da implementacao de Rodrigues; recalculados sem arredondamento",
        },
    )
    writers = []
    for k, path in enumerate(outputs):
        byte = k in [0, 1, 3, 4, 5]
        writers.append(
            p.create(
                path, res, gdal.GDT_Byte if byte else gdal.GDT_Float32, 255 if byte else NODATA
            )
        )
    capacity = p.create(p.out / "infiltracao_efetiva_mmh.tif", res)
    ksoil = p.create(p.out / "ksat_estimado_mmh.tif", res)
    altout = p.create(p.out / "posicao_altimetrica_percentil.tif", res)
    fuzzy_writers = {}
    if c["salvar_pertinencias_criterios"]:
        directory = p.out / "pertinencias_criterios"
        directory.mkdir(exist_ok=True)
        for crit in CRITERIA:
            for moment in ["fonte", "conducao", "acomodacao"]:
                fuzzy_writers[(crit, moment)] = p.create(directory / f"{crit}_{moment}.tif", res)
    areas = np.zeros((3, 3), dtype="int64")
    sample = []
    sample_xy = []
    stride = max(1, math.ceil(math.sqrt(p.area / res**2 / c["amostras_sensibilidade"])))
    for y in range(0, height, 128):
        nr = min(128, height - y)
        v = {key: d.ReadAsArray(0, y, width, nr).astype("float32") for key, d in readers.items()}
        for key in v:
            v[key][v[key] == NODATA] = np.nan
        v["alt"] = np.interp(v["z"], np.arange(len(cdf)) / 10, cdf).astype("float32")
        v["alt"][~np.isfinite(v["z"])] = np.nan
        v["area"] *= c["resolucao_hidrologia_m"] ** 2 / 1e6
        sand = v["sand"]
        clay = v["clay"]
        factor = np.full(sand.shape, np.nan, dtype="float32")
        for code, (fac, _) in SOILS.items():
            factor[v["solo"] == code] = fac
        ks = 25.4 * 10 ** (-0.6 + 0.0126 * sand - 0.0064 * clay) * factor
        inf = ks * (1 - np.clip(v["imp"], 0, 1))
        water = v["uso"] == 33
        ks[water] = 0
        inf[water] = 0
        v["infil"] = inf
        mu = memberships(v)
        scores, ncriteria = aggregate_mu(mu, weights)
        valid = (
            (mask.ReadAsArray(0, y, width, nr) > 0)
            & np.isfinite(v["z"])
            & (v["uso"] != 255)
            & (ncriteria >= 6)
            & np.all(np.isfinite(scores), axis=0)
        )
        moment = np.argmax(np.nan_to_num(scores, nan=-1), axis=0) + 1
        rank = np.argsort(np.nan_to_num(scores, nan=-1), axis=0)
        ordered = np.sort(scores, axis=0)
        margin = ordered[-1] - ordered[-2]
        grade = np.where(margin >= 0.15, 1, np.where(margin >= 0.05, 2, 3))
        transition = np.where(
            margin < 0.05,
            (np.minimum(rank[-1], rank[-2]) + 1) * 10 + np.maximum(rank[-1], rank[-2]) + 1,
            0,
        )
        vals = [
            moment,
            grade,
            margin,
            ncriteria,
            ((moment == 1) & (v["imp"] >= 0.6)).astype(int),
            transition,
            *scores,
        ]
        for k, (writer, a) in enumerate(zip(writers, vals)):
            byte = k in [0, 1, 3, 4, 5]
            writer.GetRasterBand(1).WriteArray(
                np.where(valid, a, 255 if byte else NODATA).astype("uint8" if byte else "float32"),
                0,
                y,
            )
        for writer, a in [(capacity, inf), (ksoil, ks), (altout, v["alt"])]:
            writer.GetRasterBand(1).WriteArray(
                np.where(valid & np.isfinite(a), a, NODATA).astype("float32"), 0, y
            )
        for i, crit in enumerate(CRITERIA):
            for j, m in enumerate(["fonte", "conducao", "acomodacao"]):
                if fuzzy_writers:
                    fuzzy_writers[(crit, m)].GetRasterBand(1).WriteArray(
                        np.where(valid & np.isfinite(mu[i, j]), mu[i, j], NODATA).astype("float32"),
                        0,
                        y,
                    )
        for m in range(1, 4):
            for g in range(1, 4):
                areas[m - 1, g - 1] += np.count_nonzero(valid & (moment == m) & (grade == g))
        rr, cc = np.indices(valid.shape)
        take = valid & (((rr + y) % stride) == stride // 2) & ((cc % stride) == stride // 2)
        if take.any():
            sample.append(mu[:, :, take])
            sample_xy.extend(
                zip(
                    (p.bbox[0] + (cc[take] + 0.5) * res).tolist(),
                    (p.bbox[3] - (rr[take] + y + 0.5) * res).tolist(),
                )
            )
    close_datasets(
        *writers, *fuzzy_writers.values(), capacity, ksoil, altout, *readers.values(), mask
    )
    writers.clear()
    fuzzy_writers.clear()
    capacity = None
    ksoil = None
    altout = None
    readers.clear()
    reference = None
    mask = None
    labels = ["Fonte", "Conducao", "Acomodacao"]
    grades = ["Forte", "Moderado", "Transicao"]
    write_csv(
        p.out / "areas_momentos.csv",
        ["momento", "grau", "pixels", "area_ha"],
        [
            [labels[m], grades[g], int(areas[m, g]), float(areas[m, g] * res**2 / 10000)]
            for m in range(3)
            for g in range(3)
        ],
    )
    if not sample:
        raise RuntimeError(
            "Nenhuma amostra valida para sensibilidade; revisar cobertura e criterios."
        )
    sample = np.concatenate(sample, axis=2)
    save_sensitivity(p, sample, weights, sample_xy)
    write_parameter_tables(p)
    rules = (
        "Funcoes operacionais desta adaptacao, explicitadas em memberships() no script.\n"
        + __import__("inspect").getsource(memberships)
    )
    (p.out / "regras_pertinencia.txt").write_text(rules, encoding="utf-8")
    save_json(
        p.out / "diagnostico_modelo.json",
        {
            "pixels_classificados": int(areas.sum()),
            "area_classificada_km2": float(areas.sum() * res**2 / 1e6),
            "area_vetorial_km2": p.area / 1e6,
            "intervalo_cotas": [zmin, zmax],
            "grade_hidro_m": c["resolucao_hidrologia_m"],
            "grade_momentos_m": res,
            "lencol": lencol_info,
            "operacao_reservatorio_simulada": False,
            "validacao_independente": False,
            "piloto": p.piloto,
        },
    )
    p.mark("08_momentos", outputs + [p.out / "sensibilidade.json", p.out / "areas_momentos.csv"])


def save_sensitivity(p, mu, weights, xy):
    baseline, _ = aggregate_mu(mu, weights)
    base = np.argmax(baseline, axis=0)
    rng = np.random.default_rng(p.c["semente"])
    stable = np.zeros(len(base))
    agreements = []
    for _ in range(p.c["perturbacoes_pesos"]):
        w = weights * rng.uniform(0.5, 1.5, len(weights))
        w /= w.sum()
        s, _ = aggregate_mu(mu, w)
        same = np.argmax(s, axis=0) == base
        stable += same
        agreements.append(float(same.mean()))
    loo = {}
    for i, crit in enumerate(CRITERIA):
        w = weights.copy()
        w[i] = 0
        w /= w.sum()
        s, _ = aggregate_mu(mu, w)
        loo[crit] = float(np.mean(np.argmax(s, axis=0) == base))
    stable /= p.c["perturbacoes_pesos"]
    save_json(
        p.out / "sensibilidade.json",
        {
            "amostras": len(base),
            "sorteios": p.c["perturbacoes_pesos"],
            "perturbacao_relativa": [-0.5, 0.5],
            "semente": p.c["semente"],
            "concordancia_media": float(np.mean(agreements)),
            "fracao_amostras_estaveis_acima_90pct": float(np.mean(stable > 0.9)),
            "retirada_de_criterio": loo,
            "observacao": "Robustez aos pesos; nao e validacao fisica independente.",
        },
    )
    write_csv(
        p.out / "sensibilidade_amostras.csv",
        ["x_utm", "y_utm", "momento", "estabilidade"],
        [[x, y, int(base[i] + 1), float(stable[i])] for i, (x, y) in enumerate(xy)],
    )


def write_parameter_tables(p):
    rows = []
    for code in [*CN, 241, 242, 243, 244]:
        k = 24 if code in [241, 242, 243, 244] else code
        rows.append([code, *CN[k], IMPBASE[k], ROUGHNESS[k], CBASE[k]])
    write_csv(
        p.out / "parametros_superficies.csv",
        [
            "classe",
            "CN_A",
            "CN_B",
            "CN_C",
            "CN_D",
            "fracao_impermeavel_fundo",
            "Manning_n",
            "C_referencia",
        ],
        rows,
    )
    write_csv(
        p.out / "parametros_solos.csv",
        ["grupo", "nome", "fator_Ksat", "grupo_hidrologico_hipotese"],
        [[k, SOIL_NAMES[k], factor, "ABCD"[hsg]] for k, (factor, hsg) in SOILS.items()],
    )


def final_report(p):
    info = {
        "versao_script": VERSION,
        "parametros": p.c,
        "piloto": p.piloto,
        "avisos": p.warnings,
        "limites": [
            "modelo exploratorio sem calibracao de vazoes ou observacoes independentes de inundacao",
            "CN e grupos hidrologicos sao hipoteses de trabalho",
            "chuva IDF pontual aplicada uniformemente sem fator de reducao areal",
            "envoltoria de maximos de duracoes diferentes por trecho nao representa uma cheia unica simultanea",
            "HAND-SRC nao representa pontes, bueiros, batimetria ou remanso",
            "operacao do Lago Paranoa nao foi simulada; zonas controladas sao sinalizadas como desconhecidas",
            "resultado 5 m nao implica informacao hidrologica 5 m quando grade hidrologica configurada e mais grossa",
            "tempos de retorno de chuva nao garantem a mesma frequencia da cheia",
            "500 perturbacoes dos pesos nao abrangem toda incerteza hidrologica",
        ],
    }
    info["chave_execucao"] = p.key
    info["produtos"] = [
        [str(path.relative_to(p.out)), path.stat().st_size]
        for path in sorted(p.out.rglob("*"))
        if path.is_file()
        and not path.is_relative_to(p.tmp)
        and path.name not in {"execucao.log", "CONCLUIDO.txt", "proveniencia_e_limites.json"}
    ]
    info["intermediarios_removidos"] = not p.tmp.exists()
    save_json(p.out / "proveniencia_e_limites.json", info)
    (p.out / "CONCLUIDO.txt").write_text(
        "Fluxo concluido. Ler diagnostico_modelo.json, proveniencia_e_limites.json e hidrologia_trechos.csv.\n"
        + ("TESTE PILOTO SEM VALIDADE PARA A BACIA INTEIRA.\n" if p.piloto else ""),
        encoding="utf-8",
    )
    if p.c.get("limpar_intermediarios_ao_concluir", True):
        try:
            p.cleanup()
        except (OSError, RuntimeError) as error:
            p.warn(f"Produtos concluidos; limpeza de intermediarios pendente: {error}")
        info["intermediarios_removidos"] = not p.tmp.exists()
        save_json(p.out / "proveniencia_e_limites.json", info)
    p.log("CONCLUIDO: " + str(p.out))


def selftest(root):
    deps()
    checks = []

    def check(name, ok):
        if not bool(ok):
            raise AssertionError(name)
        checks.append(name)

    triangle = ogr.CreateGeometryFromWkt("POLYGON((0 0,10 0,0 10,0 0))")
    inside = basin_tile_mask(triangle, 0, 10, 10, 10, 1, 31983)
    outside = basin_tile_mask(triangle, 20, 30, 10, 10, 1, 31983)
    empty = tin_tile([], [], outside, 20, 30, 1, 150, "teste_exterior")
    check(
        "Bloco exterior sem curvas permanece NoData", not outside.any() and np.all(empty == NODATA)
    )
    values = tin_tile(
        [[0, 0], [10, 0], [0, 10]], [100, 110, 110], inside, 0, 10, 1, 150, "teste_parcial"
    )
    gy, gx = np.indices((10, 10))
    expected = 100 + (gx + 0.5) + (10 - gy - 0.5)
    check(
        "TIN parcial preserva o plano somente na bacia",
        inside.any()
        and not inside.all()
        and np.allclose(values[inside], expected[inside])
        and np.all(values[~inside] == NODATA),
    )
    for points, name in [
        ([[1, 1], [1, 1], [1, 1]], "duplicados"),
        ([[1, 1], [2, 2], [3, 3]], "colineares"),
    ]:
        rejected = False
        try:
            tin_tile(
                points, [100, 100, 100], np.ones((4, 4), dtype=bool), 0, 4, 1, 150, "teste_" + name
            )
        except ValueError:
            rejected = True
        check("TIN rejeita pontos " + name + " dentro da bacia", rejected)
    w, m, tf, cr = fahp(NOTAS)
    check(
        "FAHP normalizado e consistente",
        abs(w.sum() - 1) < 1e-12 and cr < 0.1 and np.allclose(m * m.T, 1),
    )
    check("FAHP simetria dos julgamentos iguais", abs(w[0] - w[1]) < 1e-12)
    for tr in [5, 100, 500]:
        rain = storm(DEFAULT, tr, 180)
        check(
            f"Chuva TR{tr} conserva lamina IDF",
            abs(rain.sum() - float(idf(DEFAULT, tr, 180)) * 3) < 1e-9,
        )
        ex = scs_excess(rain, 75)
        check(f"Excesso limitado a chuva TR{tr}", np.all(ex >= 0) and ex.sum() <= rain.sum())
    q = np.zeros(600)
    q[5:15] = 10
    out, stored = route_linear(q, 1800, 300, 750)
    check("Propagacao conserva volume", abs(q.sum() * 300 - out.sum() * 300 - stored) < 1e-7)
    check("Propagacao atrasa e amortece pico", np.argmax(out) > 5 and out.max() < 10)
    k = triangular_kernel(1800, 300)
    check("Hidrograma unitario normalizado", abs(k.sum() - 1) < 1e-12 and np.all(k >= 0))
    # Rede Y: dois tributarios entram em um terceiro; nao somar somente os picos.
    par = np.array([0, 3, 3, 0])
    order = reach_order(par)
    check(
        "Ordem causal da rede", order.index(3) > order.index(1) and order.index(3) > order.index(2)
    )
    direction = np.array([[8, 6, 6], [8, 8, 6], [8, 8, -6]], dtype="int16")
    valid = np.ones((3, 3), bool)
    down, order = downstream_graph(direction, valid)
    seed = np.zeros((3, 3), dtype="int32")
    seed[2, 2] = 1
    dem = np.array([[9, 8, 7], [8, 6, 4], [7, 4, 1]], dtype="float32")
    catch, bed, travel = reverse_trace(down, order, seed, dem, np.ones((3, 3)), 10, dem.shape)
    check(
        "HAND segue drenagem e nao vizinho euclidiano",
        np.all(catch == 1) and np.all(bed == 1) and travel[0, 0] > travel[2, 1],
    )
    mu = np.ones((9, 3, 4), dtype="float32") * 0.5
    mu[0, :, 0] = np.nan
    scores, count = aggregate_mu(mu, w)
    check("NoData renormaliza pesos sem virar zero", np.allclose(scores, 0.5) and count[0] == 8)
    mu[1, 0, 0] = np.nan
    scores, count = aggregate_mu(mu, w)
    check(
        "Criterio parcialmente ausente e excluido inteiro",
        np.allclose(scores, 0.5) and count[0] == 7,
    )

    # Integracao pequena com duas contribuicoes entrando em um reservatorio.
    # O caso sintetico usa uma pasta temporaria descartada ao fim do teste.
    class Synthetic:
        def __init__(self, directory):
            self.c = json.loads(json.dumps(DEFAULT))
            self.c["tempos_retorno"] = [5, 100]
            self.c["duracoes_chuva_min"] = [60, 180]
            self.out = Path(directory)
            self.arrays = {}

        def done(self, *args):
            return False

        def mark(self, *args):
            pass

        def log(self, *args):
            pass

        def write(self, path, array, *args):
            self.arrays[Path(path).name] = array.copy()

    with tempfile.TemporaryDirectory(prefix=".autoteste_", dir=Path(root).resolve()) as directory:
        fake = Synthetic(directory)
        par = np.array([0, 3, 3, 0])
        levels = np.arange(0, 51, dtype=float)
        synthetic = dict(
            parent=par,
            topo=reach_order(par),
            area=np.array([0, 400, 400, 800.0]),
            cn=np.array([np.nan, 75, 75, 98]),
            tc=np.array([300, 600, 600, 300.0]),
            route_k=np.array([60, 600, 600, 60.0]),
            catch=np.array([[1, 2], [3, 3]]),
            valid=np.ones((2, 2), bool),
            hand=np.zeros((2, 2)),
            controlled=np.array([False, False, False, True]),
            lake_reach=np.array([False, False, False, True]),
            levels=levels,
            rating=np.tile(levels * 1000, (4, 1)),
        )
        ordinary_steps = hydrograph_steps(fake.c, synthetic)
        synthetic["route_k"][-1] = 200 * 86400.0
        check(
            "Tempo ficticio de lago terminal nao aumenta a janela",
            hydrograph_steps(fake.c, synthetic) == ordinary_steps,
        )
        hydrographs(fake, synthetic)
        balances = json.loads((fake.out / "balanco_hidrologico.json").read_text())
        check(
            "Rede com reservatorio conserva volume",
            max(b["erro_relativo"] for b in balances) < 1e-10,
        )
        check(
            "Reservatorio nao recebe nivel de cheia inventado",
            np.all(fake.arrays["inundacao_profundidade_TR100_hidro.tif"][1, :] == NODATA),
        )
    target = Path(root) / "AUTOTESTES_MOMENTOS_AGUA.json"
    save_json(
        target,
        {"versao": VERSION, "testes_aprovados": checks, "calibracao_ou_validacao_campo": False},
    )
    print(
        json.dumps({"aprovados": len(checks), "arquivo": str(target)}, ensure_ascii=False),
        flush=True,
    )


def run(c, piloto=False, ate="completo"):
    deps()
    p = Pipeline(c, piloto, reuse_completed=ate == "completo")
    if p.reused:
        return p
    (p.out / "CONCLUIDO.txt").unlink(missing_ok=True)
    p.terrain()
    if ate == "terreno":
        return p
    p.surfaces()
    if ate == "superficies":
        return p
    p.grass()
    if ate == "grass":
        return p
    data = network(p)
    if ate == "rede":
        return p
    texture(p)
    if ate == "textura":
        return p
    hydrographs(p, data)
    del data
    info = estimate_groundwater(p)
    classify(p, info)
    final_report(p)
    return p


def write_task_result(statusfile, result=None, exception=None, output=None):
    """Grava o encerramento mesmo se o callback da interface estiver pendente."""
    code = result.get("codigo") if isinstance(result, dict) else None
    failed = exception is not None or code != 0
    detail = str(exception) if exception else (
        "\n".join(result.get("ultimas_mensagens", []))
        if isinstance(result, dict) else "Tarefa encerrada sem resultado."
    )
    state = {
        "estado": "falhou" if failed else "concluido",
        "versao": VERSION,
        "codigo": code,
        "atualizado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if failed:
        state["detalhe"] = detail
    elif output is not None:
        state["resultados"] = str(output)
    save_json(statusfile, state)
    return state


def start_qgis():
    from qgis.core import QgsApplication, QgsTask, QgsMessageLog, Qgis
    from qgis.utils import iface

    c = config(ROOT)
    python = Path(c["qgis_root"]) / "bin" / "python3.exe"
    if not python.exists():
        raise RuntimeError("Executavel Python do QGIS nao encontrado; ajustar qgis_root no JSON.")
    logfile = ROOT / "ULTIMA_EXECUCAO_QGIS.log"
    statusfile = ROOT / "STATUS_EXECUCAO_QGIS.json"
    save_json(statusfile, {"estado": "iniciando", "versao": VERSION, "log": str(logfile)})
    QgsMessageLog.logMessage(
        "Iniciando. Acompanhe o painel Mensagens / Momentos da agua e o arquivo ULTIMA_EXECUCAO_QGIS.log.",
        "Momentos da agua",
        Qgis.Info,
    )

    def backend_worker(task):
        # Nao usar objetos de camada/projeto do QGIS na thread de trabalho.
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        task.setProgress(1)
        last_update = 0.0
        progress = 1.0
        tail = []
        with logfile.open("w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [str(python), str(SCRIPT), "--run"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            )
            for line in proc.stdout:
                log.write(line)
                log.flush()
                QgsMessageLog.logMessage(line.rstrip(), "Momentos da agua", Qgis.Info)
                tail.append(line.rstrip())
                tail = tail[-12:]
                hit = re.search(r"TIN bloco (\d+)/(\d+)", line)
                if hit:
                    progress = 2 + 28 * int(hit[1]) / int(hit[2])
                for text, value in [
                    ("Reprojetando vetores", 32),
                    ("GRASS:", 42),
                    ("Construindo grafo", 48),
                    ("Obtendo recortes SoilGrids", 53),
                    ("Hidrogramas TR", 65),
                    ("Preparando criterios", 85),
                ]:
                    if text in line:
                        progress = max(progress, value)
                task.setProgress(progress)
                if time.monotonic() - last_update > 5:
                    save_json(
                        statusfile,
                        {
                            "estado": "processando",
                            "versao": VERSION,
                            "pid": proc.pid,
                            "progresso_aproximado_pct": round(progress, 1),
                            "ultima_mensagem": line.rstrip(),
                            "atualizado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "log": str(logfile),
                        },
                    )
                    last_update = time.monotonic()
            return {"codigo": proc.wait(), "ultimas_mensagens": tail}

    def worker(task):
        try:
            result = backend_worker(task)
        except Exception as error:
            write_task_result(statusfile, exception=error)
            raise
        write_task_result(
            statusfile, result, output=Path(c["pasta"]) / "RESULTADOS_MOMENTOS_AGUA"
        )
        return result

    def finished(exception, result=None):
        # QgsTaskWrapper so encaminha valores truthy. Um codigo inteiro 0
        # era descartado pelo wrapper e acabava interpretado como falha.
        state = write_task_result(
            statusfile, result, exception, Path(c["pasta"]) / "RESULTADOS_MOMENTOS_AGUA"
        )
        if state["estado"] == "falhou":
            detail = state["detalhe"]
            QgsMessageLog.logMessage(
                "Falha: " + detail + ". Consultar " + str(logfile),
                "Momentos da agua",
                Qgis.Critical,
            )
            print("FALHOU: a tarefa foi interrompida.\n" + detail + "\nLog: " + str(logfile))
            iface.messageBar().pushCritical(
                "Momentos da agua",
                "Execucao interrompida. O erro foi escrito na Console Python e no log.",
            )
            return
        out = Path(c["pasta"]) / "RESULTADOS_MOMENTOS_AGUA"
        print("CONCLUIDO. Resultados em: " + str(out))
        from qgis.core import QgsRasterLayer, QgsProject, QgsPalettedRasterRenderer
        palette = {
            1: ("Fonte", "#41ab5d"),
            2: ("Conducao", "#bf812d"),
            3: ("Acomodacao", "#2171b5"),
        }
        for filename, title in [
            ("momento_dominante.tif", "Momentos da agua - estimativa"),
            ("grau_definicao.tif", "Grau de definicao"),
            ("inundacao_profundidade_TR100_visualizacao.tif", "Profundidade TR100 - estimativa"),
            ("controle_reservatorio_hidro.tif", "Zonas sem simulacao de operacao de reservatorio"),
        ]:
            layer = QgsRasterLayer(str(out / filename), title)
            if not layer.isValid():
                continue
            if filename == "momento_dominante.tif":
                from qgis.PyQt.QtGui import QColor

                classes = [
                    QgsPalettedRasterRenderer.Class(k, QColor(color), label)
                    for k, (label, color) in palette.items()
                ]
                layer.setRenderer(QgsPalettedRasterRenderer(layer.dataProvider(), 1, classes))
            QgsProject.instance().addMapLayer(layer)
        iface.messageBar().pushSuccess(
            "Momentos da agua", "Concluido. Leia os diagnosticos na pasta de resultados."
        )

    task = QgsTask.fromFunction("Momentos da agua - Paranoa", worker, on_finished=finished)
    QgsApplication.taskManager().addTask(task)
    print(
        "Tarefa iniciada (v"
        + VERSION
        + "). Acompanhe Exibir > Paineis > Mensagens de log, aba Momentos da agua.\nStatus: "
        + str(statusfile)
        + "\nA Console mostrara CONCLUIDO ou FALHOU ao terminar."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--piloto", action="store_true")
    parser.add_argument("--autoteste", action="store_true")
    parser.add_argument("--grass-worker")
    parser.add_argument(
        "--ate",
        default="completo",
        choices=["terreno", "superficies", "grass", "rede", "textura", "completo"],
    )
    args = parser.parse_args()
    if args.grass_worker:
        grass_worker(args.grass_worker)
        return
    if args.autoteste:
        selftest(ROOT)
        return
    try:
        c = config()
        run(c, args.piloto, args.ate)
    except Exception:
        traceback.print_exc()
        print(
            "FALHA. Resultados incompletos nao devem ser usados; etapas anteriores podem ser retomadas.",
            flush=True,
        )
        raise SystemExit(1)


if __name__ == "__qgis_agua__":
    start_qgis()
elif __name__ == "__main__":
    main()
