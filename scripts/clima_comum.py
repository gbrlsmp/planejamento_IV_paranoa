"""Contrato único das classes climáticas, compartilhado pelos exportadores."""
from bisect import bisect_left
import hashlib
import json
import math

LABELS = ["base", "boa", "média", "ruim", "muito ruim"]
FIELDS = {
    "temperatura": {"dia": ("temp_dia", "td_classe"), "noite": ("temp_noite", "tn_classe"), "media": ("temp_media", "tm_classe")},
    "hm": {"dia": ("hm_dia", "hmd_cls"), "noite": ("hm_noite", "hmn_cls"), "media": ("hm_media", "hmm_cls")},
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_sha256(path):
    # Git may convert JSON line endings on Windows checkout.
    if path.suffix == ".json":
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return sha256(path)


def classify(value, config, scenario):
    if value is None or not math.isfinite(value):
        return None
    index = bisect_left(config["scenarios"][scenario]["cuts"][1:-1], value)
    return config["labels_numeric"][index]


def complete(catalog):
    catalog["version"] = 2
    for indicator, config in catalog["indicators"].items():
        config["labels_numeric"] = LABELS if indicator == "temperatura" else LABELS[::-1]
        config["decimals"] = 1 if indicator == "temperatura" else 4
        config["unit"] = "°C" if indicator == "temperatura" else ""
        for scenario, record in config["scenarios"].items():
            record["field"], record["class_field"] = FIELDS[indicator][scenario]
    catalog["zone"] = {"indicator": "temperatura", "scenario": "media", "warmest_classes": 3,
                       "operator": ">", "threshold": catalog["indicators"]["temperatura"]["scenarios"]["media"]["cuts"][2],
                       "vector": "zona-icu.gpkg", "rule": "positive_intersection_area"}
    # Only scientific inputs and representation rules determine the revision.
    payload = {key: catalog[key] for key in ("classification", "indicators", "bounds_3857", "zone")}
    catalog["revision"] = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return catalog
