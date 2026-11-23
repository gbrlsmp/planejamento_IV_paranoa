"""Extrai os derivados públicos de uma cópia HTML validada do piloto Fitópolis."""
import argparse
import base64
import gzip
import json
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "dados-mapas/matriz-situacoes"


def exportar(html, destino):
    prefix = '<script id="dados" type="application/json">'
    fonte = html.read_text(encoding="utf-8")
    inicio = fonte.index(prefix) + len(prefix)
    dados = json.loads(fonte[inicio:fonte.index("</script>", inicio)])
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ("fragmentos", "avus"):
        payload = json.dumps(dados.pop(nome), ensure_ascii=False, separators=(",", ":")).encode()
        (destino / f"{nome}.json.gz").write_bytes(gzip.compress(payload, mtime=0))
    for nome in list(dados):
        if isinstance(dados[nome], str):
            payload = base64.b64decode(dados.pop(nome), validate=True)
            if not payload.startswith(b"\x1f\x8b"):
                raise ValueError(f"{nome}: esperado vetor gzip")
            (destino / f"{nome}.bin.gz").write_bytes(payload)
    for ra, imagem in dados["panos"].items():
        prefix = "data:image/png;base64,"
        if not imagem.startswith(prefix):
            raise ValueError("Panorama inválido")
        nome = f"panorama-{ra}.png"
        (destino / nome).write_bytes(base64.b64decode(imagem[len(prefix):], validate=True))
        dados["panos"][ra] = nome
    (destino / "catalogo.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="Explorar_piloto.html produzido pela matriz local")
    parser.add_argument("--destino", type=Path, default=OUT)
    args = parser.parse_args()
    exportar(args.html, args.destino)
