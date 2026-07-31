#!/usr/bin/env python3
"""Bind every file that may affect formal Phase 4 execution or analysis."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "paper/bioinformatics_submission_readiness_v2/phase_3_execution_binding.json"
PATHS = (
    ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86",
    "paper/bioinformatics_submission_readiness_v2/phase_2_runtime_identity.json",
    "paper/bioinformatics_submission_readiness_v2/phase_3_artifact_manifest.json",
    "paper/bioinformatics_submission_readiness_v2/phase_3_attempt_manifest.tsv",
    "paper/bioinformatics_submission_readiness_v2/phase_3_exclusion_digest_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_3_hardware_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_3_input_manifest.tsv",
    "paper/bioinformatics_submission_readiness_v2/phase_3_performance_plan.json",
    "paper/biological_topk/contract_spec.json",
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/compare_candidate_topk.py",
    "reproduce/biological_topk/contract.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/bioinformatics_submission_readiness_v2/analyze_phase4.py",
    "reproduce/bioinformatics_submission_readiness_v2/capacity.py",
    "reproduce/bioinformatics_submission_readiness_v2/cpu_reference_screen.py",
    "reproduce/bioinformatics_submission_readiness_v2/run_phase4.py",
    "schemas/gasal2_candidate_sites_tsv_v1.schema.json",
    "schemas/gasal2_gpu_screen_run_report_v1.schema.json",
    "scripts/fasim_tfo_archive.py",
    "scripts/gasal2_candidate_sites.py",
    "scripts/gasal2_gpu_screen.py",
    "scripts/gasal2_longtarget.py"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        print(f"Phase 3 execution binding already exists: {OUTPUT}", file=sys.stderr)
        return 1
    files = {}
    for relative in PATHS:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            print(f"missing or unsafe execution file: {relative}", file=sys.stderr)
            return 1
        files[relative] = sha256(path)
    value = {
        "schema_version": 1,
        "phase": 3,
        "prediction_executed_before_binding": False,
        "software_epoch": "submission_rc_v2_2",
        "container_image_digest": "sha256:f04340aa1b77092c25eee50c84144adb08e6f1b48a34580f6f9c33aff3163ca7",
        "candidate_binary_sha256": "ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9",
        "authority_binary_sha256": "75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e",
        "execution_file_sha256": files,
    }
    OUTPUT.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"bound_file_count": len(files)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
