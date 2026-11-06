"""Impede publicação de revisões climáticas misturadas. Apenas biblioteca padrão."""
import gzip
import json
from pathlib import Path
from clima_comum import classify, complete, artifact_sha256

SITE = Path(__file__).resolve().parents[1]


def validate():
    catalog = json.loads((SITE / "dados-mapas/clima/catalogo.json").read_text(encoding="utf-8"))
    revision = catalog["revision"]
    assert complete(json.loads(json.dumps(catalog)))["revision"] == revision, "Catálogo alterado sem nova revisão"
    web = json.loads(gzip.decompress((SITE / "mapa-dados.json.gz").read_bytes()))
    assert web["climate_revision"] == revision
    positions = {field: index for index, field in enumerate(web["fields"])}
    assert len(web["rows"]) == len({values[positions["patch_id"]] for _, values in web["rows"]})
    context = json.loads((SITE / "dados-mapas/contexto-riscos.json").read_text(encoding="utf-8"))
    for config in catalog["indicators"].values():
        assert len(config["colors"]) == len(config["labels_numeric"]) == 5
        for scenario, record in config["scenarios"].items():
            assert len(record["source_sha256"]) == 64
            assert record["field"] not in context, "Configuração climática antiga ainda ativa"
            assert not (SITE / "dados-mapas/contexto" / (record["field"] + ".png")).exists()
            assert len(record["cuts"]) == 6 and all(a < b for a, b in zip(record["cuts"], record["cuts"][1:]))
            for file in ("continuous", "classes", "preview"):
                assert (SITE / "dados-mapas/clima" / record[file]).is_file()
            for _, values in web["rows"]:
                assert values[positions[record["class_field"]]] == classify(values[positions[record["field"]]], config, scenario), (record["field"], values[positions["patch_id"]])
    for file in ("dados-mapas/riscos-por-ra.json", "dados-mapas/metodologia-riscos.json"):
        data = json.loads((SITE / file).read_text(encoding="utf-8"))
        assert data["climate_revision"] == revision, file
    update = json.loads((SITE / "dados-mapas/clima/atualizacao.json").read_text(encoding="utf-8"))
    assert update["revision"] == revision
    assert update.get("artifacts_sha256"), "Faltam as assinaturas dos arquivos gerados"
    for file, digest in update["artifacts_sha256"].items():
        assert artifact_sha256(SITE / file) == digest, f"Arquivo alterado isoladamente: {file}"
    assert update["fragments"] == len(web["rows"])
    expected_area = sum(catalog["indicators"]["temperatura"]["scenarios"]["media"]["class_area_ha"][2:])
    assert abs(expected_area - update["zone"]["area_ha"]) < .000001
    zone = SITE / "dados-mapas/clima" / catalog["zone"]["vector"]
    assert zone.is_file()
    print(f"Clima consistente: revisão {revision}; {len(web['rows'])} fragmentos; 7 produtos principais")


if __name__ == "__main__":
    validate()
