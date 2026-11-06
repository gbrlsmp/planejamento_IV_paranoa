#!/usr/bin/env python3
"""Gera o arquivo compacto do mapa a partir da camada final do diagnóstico."""

import argparse
import gzip
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


CAMPOS = (
    "patch_id", "ra_nome", "icu",
    "temp_dia", "td_classe", "temp_noite", "tn_classe", "temp_media", "tm_classe",
    "hm_dia", "hmd_cls", "hm_noite", "hmn_cls", "hm_media", "hmm_cls", "umid_pct", "umid_cls",
    "inund_med", "inund_max", "inund_cls",
    "edif", "edif_pct", "edif_cls", "renda_sm", "renda_cls",
)
RAIZ_SITE = Path(__file__).resolve().parents[1]


def ambiente_gdal(ogr2ogr):
    ambiente = os.environ.copy()
    # Em instalações do QGIS para Windows, os dados ficam ao lado de bin.
    raiz = ogr2ogr.resolve().parent.parent
    proj = raiz / "share" / "proj"
    gdal = raiz / "apps" / "gdal" / "share" / "gdal"
    if (proj / "proj.db").is_file():
        ambiente.setdefault("PROJ_DATA", str(proj))
    if gdal.is_dir():
        ambiente.setdefault("GDAL_DATA", str(gdal))
    return ambiente


def codificar_anel(anel):
    """Codifica deltas de longitude e latitude com cinco casas decimais."""
    partes = []
    anterior = (0, 0)
    for longitude, latitude in anel:
        atual = tuple(math.floor(valor * 100_000 + 0.5) for valor in (longitude, latitude))
        for novo, velho in zip(atual, anterior):
            delta = novo - velho
            valor = -2 * delta - 1 if delta < 0 else 2 * delta
            while valor >= 32:
                partes.append(chr((32 | (valor & 31)) + 63))
                valor >>= 5
            partes.append(chr(valor + 63))
        anterior = atual
    return "".join(partes)


def preparar_dados(entrada, camada, ogr2ogr):
    argumentos = [
        str(ogr2ogr), "-q", "-f", "GeoJSONSeq",
        "-t_srs", "EPSG:4326", "-simplify", "3",
        "-lco", "COORDINATE_PRECISION=5",
        "-select", ",".join(CAMPOS), "/vsistdout/", str(entrada), camada,
    ]
    resultado = subprocess.run(
        argumentos, check=True, capture_output=True, encoding="utf-8",
        env=ambiente_gdal(ogr2ogr),
    )
    rows, ranges, classes = [], {}, {}
    ids = set()
    for linha in resultado.stdout.splitlines():
        if not linha.strip():
            continue
        feicao = json.loads(linha)
        geometria = feicao.get("geometry") or {}
        tipo = geometria.get("type")
        coordenadas = geometria.get("coordinates")
        if tipo not in ("Polygon", "MultiPolygon") or not coordenadas:
            raise ValueError("A camada contém uma geometria sem polígono.")
        poligonos = [coordenadas] if tipo == "Polygon" else coordenadas
        atributos = feicao["properties"]
        identificador = atributos.get("patch_id")
        if identificador is None or identificador in ids:
            raise ValueError("Cada fragmento precisa de um patch_id único.")
        ids.add(identificador)
        valores = []
        for campo in CAMPOS:
            valor = atributos.get(campo)
            if isinstance(valor, (int, float)):
                if not math.isfinite(valor):
                    valor = None
                else:
                    minimo, maximo = ranges.get(campo, (valor, valor))
                    ranges[campo] = [min(minimo, valor), max(maximo, valor)]
            elif isinstance(valor, str):
                classes.setdefault(campo, set()).add(valor)
            valores.append(valor)
        rows.append([[list(map(codificar_anel, poligono)) for poligono in poligonos], valores])
    if not rows:
        raise ValueError("A camada não contém fragmentos.")
    return {
        "fields": CAMPOS, "rows": rows, "ranges": ranges,
        "classes": {campo: sorted(valores) for campo, valores in classes.items()},
        "encoding": "polyline-xy-5",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", type=Path, help="GeoPackage final do diagnóstico")
    parser.add_argument("--camada", default="diagnostico_risco_v01")
    parser.add_argument("--ogr2ogr", type=Path, default=shutil.which("ogr2ogr"))
    parser.add_argument("--saida", type=Path, default=RAIZ_SITE / "mapa-dados.json.gz")
    args = parser.parse_args()
    if not args.entrada.is_file():
        parser.error("Informe o GeoPackage final do diagnóstico.")
    if not args.ogr2ogr or not args.ogr2ogr.is_file():
        parser.error("Use o terminal do QGIS ou informe o caminho de ogr2ogr com --ogr2ogr.")
    if args.entrada.resolve() == args.saida.resolve():
        parser.error("Escolha um arquivo de saída diferente do GeoPackage.")
    try:
        dados = preparar_dados(args.entrada, args.camada, args.ogr2ogr)
    except subprocess.CalledProcessError as erro:
        parser.exit(1, erro.stderr or "Falha ao exportar a camada com GDAL.\n")
    except ValueError as erro:
        parser.exit(1, f"{erro}\n")

    conteudo = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.saida.parent, delete=False) as arquivo:
        temporario = Path(arquivo.name)
    try:
        temporario.write_bytes(gzip.compress(conteudo, compresslevel=9, mtime=0))
        temporario.replace(args.saida)
    finally:
        temporario.unlink(missing_ok=True)
    print(f"{len(dados['rows'])} fragmentos exportados para {args.saida}")


if __name__ == "__main__":
    main()
