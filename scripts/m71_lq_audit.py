#!/usr/bin/env python3
"""Audit M7.1-LQ saved Node1 evidence without declaring formal equivalence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

VARIANTS = ("programmable", "fixed", "rom")
FIELDS = {
    "rtl_sha256": "msif_{variant}.sv",
    "mapped_verilog_sha256": "m71_lq/msif_{variant}_mapped.v",
    "mapped_json_sha256": "m71_lq/msif_{variant}_mapped.json",
    "cell_inventory_sha256": "m71_lq/msif_{variant}_inventory.json",
    "mapping_log_sha256": "m71_lq/msif_{variant}_map.log",
    "simulation_log_sha256": "m71_lq/msif_{variant}_simulate.log",
    "actual_cell_models_sha256": "m71_lq/msif_{variant}_functional_models.v",
}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(build: Path) -> dict:
    out = build / "m71_lq"
    evidence = json.loads((out / "evidence.json").read_text())
    if evidence.get("schema") != "msif-m71-lq-v1":
        raise ValueError("wrong evidence schema")
    if evidence.get("qualification") != "bounded-mapped-gate-level-validation":
        raise ValueError("wrong qualification boundary")
    for key in ("release_approval", "full_formal_equivalence", "physical_ppa"):
        if evidence.get(key) != "NOT_VERIFIED":
            raise ValueError("misleading or unexpected approval assertion: " + key)
    for field, name in (("liberty_sha256", None), ("model_sha256", "model.json"),
                        ("manifest_sha256", "manifest.json")):
        value = evidence.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("invalid digest field: " + field)
        if name and digest(build / name) != value:
            raise ValueError("digest mismatch: " + name)
    variants = evidence.get("architectures", {})
    if set(variants) != set(VARIANTS):
        raise ValueError("missing or unexpected architectures")
    for variant in VARIANTS:
        item = variants[variant]
        inv = json.loads((out / f"msif_{variant}_inventory.json").read_text())
        provenance = json.loads((out / f"msif_{variant}_functional_models.provenance.json").read_text())
        if inv.get("check") != "PASS" or inv.get("unknown_cells") != []:
            raise ValueError("cell inventory rejected: " + variant)
        if inv.get("total_cells") != item.get("mapped_cell_count"):
            raise ValueError("cell inventory count mismatch: " + variant)
        if provenance.get("model_sha256") != item.get("actual_cell_models_sha256"):
            raise ValueError("model provenance digest mismatch: " + variant)
        if item.get("inventory") != "PASS" or item.get("gate_level_regression") != "PASS":
            raise ValueError("missing verification PASS: " + variant)
        count = item.get("gate_level_vectors")
        if type(count) is not int or count < 5:
            raise ValueError("insufficient vectors: " + variant)
        for key, template in FIELDS.items():
            path = build / template.format(variant=variant)
            if not path.is_file() or digest(path) != item.get(key):
                raise ValueError(f"digest mismatch/missing file: {variant}/{key}")
        sim_text = (out / f"msif_{variant}_simulate.log").read_text()
        if f"PASS {variant} {count} vectors" not in sim_text:
            raise ValueError("missing simulator PASS marker: " + variant)
        if "FATAL:" in sim_text or "ERROR:" in sim_text:
            raise ValueError("simulator error marker: " + variant)
    return {"result": "PASS", "qualification": "bounded-gate-level-only",
            "architectures": list(VARIANTS), "vectors_per_architecture": [variants[v]["gate_level_vectors"] for v in VARIANTS],
            "full_formal_equivalence": "NOT_VERIFIED", "physical_ppa": "NOT_VERIFIED", "release_approval": "NOT_VERIFIED"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=Path("build/m71_liberty"))
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.build), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as err:
        parser.exit(1, f"BLOCKED M7.1-LQ audit: {err}\n")

if __name__ == "__main__":
    main()
