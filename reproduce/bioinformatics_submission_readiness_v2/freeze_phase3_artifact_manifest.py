#!/usr/bin/env python3
"""Inventory every Phase 3 input-only artifact under the fixed v2 quota."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V2_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2"
PHASE3_ROOT = V2_ROOT / "phase3"
OUTPUT = ROOT / "paper/bioinformatics_submission_readiness_v2/phase_3_artifact_manifest.json"
QUOTA = 68_719_476_736


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def role(relative: Path) -> str:
    value = relative.as_posix()
    if value == "phase3/input-generation-receipt.json":
        return "input_only_generation_receipt"
    if value == "phase3/external-input-generation-receipt.json":
        return "external_input_only_generation_receipt"
    if "/frozen-inputs/" in f"/{value}" and value.endswith("/query.fa"):
        return "frozen_formal_query"
    if "/frozen-inputs/" in f"/{value}" and value.endswith("/target.fa"):
        return "frozen_formal_target"
    if "/external-frozen-inputs/" in f"/{value}" and value.endswith("/target-regions.fa"):
        return "frozen_label_blind_external_target"
    raise ValueError(f"unclassified Phase 3 artifact: {value}")


def main() -> int:
    if OUTPUT.exists():
        print(f"Phase 3 artifact manifest already exists: {OUTPUT}", file=sys.stderr)
        return 1
    artifacts = []
    for path in sorted(PHASE3_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(V2_ROOT)
        artifacts.append(
            {
                "relative_path": relative.as_posix(),
                "role": role(relative),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    total = sum(path.stat().st_size for path in V2_ROOT.rglob("*") if path.is_file())
    value = {
        "schema_version": 1,
        "phase": 3,
        "formal_claim_evidence": False,
        "prediction_executed": False,
        "artifacts": artifacts,
        "phase3_artifact_count": len(artifacts),
        "bytes_at_phase3_freeze": total,
        "quota_bytes": QUOTA,
    }
    if not artifacts or total > QUOTA:
        print("Phase 3 artifact inventory is empty or over quota", file=sys.stderr)
        return 1
    OUTPUT.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact_count": len(artifacts), "bytes_at_phase3_freeze": total}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
