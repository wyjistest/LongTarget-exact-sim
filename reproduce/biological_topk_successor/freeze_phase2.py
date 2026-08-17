#!/usr/bin/env python3
"""Freeze the unchanged comparator regression in the successor epoch."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reproduce.biological_topk import build_phase2_regression as v1_builder  # noqa: E402


PAPER = ROOT / "paper/biological_topk_successor"
V1_PAPER = ROOT / "paper/biological_topk"
PHASE1_COMMIT = "c68891dab08a777e54c9e301e8dd3515a11bcc31"
PREDECESSOR_PHASE2_COMMIT = "4d89d1cd989f50a42e7e3af56333c39219ba1803"
REGRESSION_NAMES = (
    "phase2_known_cases.json",
    "phase2_regression_details.tsv",
    "phase2_regression_manifest.tsv",
    "phase2_regression_receipt.json",
    "phase2_regression_results.tsv",
)
FREEZE_PATH = PAPER / "phase2_comparator_freeze.json"
OUTPUT_PATHS = tuple(PAPER / name for name in REGRESSION_NAMES) + (FREEZE_PATH,)


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def build_payloads() -> dict[Path, bytes]:
    generated, receipt = v1_builder.build_regression_payloads()
    by_name = {path.name: payload for path, payload in generated.items()}
    require(set(by_name) == set(REGRESSION_NAMES), "historical regression output inventory drift")
    payloads = {PAPER / name: by_name[name] for name in REGRESSION_NAMES}

    predecessor_hashes = {
        f"paper/biological_topk/{name}": sha256_file(V1_PAPER / name)
        for name in REGRESSION_NAMES
    }
    require(
        all(sha256_bytes(by_name[name]) == predecessor_hashes[f"paper/biological_topk/{name}"] for name in REGRESSION_NAMES),
        "successor regression does not preserve predecessor bytes",
    )
    components = {
        relative: sha256_file(ROOT / relative)
        for relative in v1_builder.COMPONENT_PATHS
    }
    freeze = {
        "schema_version": 1,
        "phase": 2,
        "status": "pass",
        "contract_name": "biological_topk_candidate_site_v1",
        "source_commit": PHASE1_COMMIT,
        "source_commit_role": "successor_phase_2_parent_and_frozen_contract_commit",
        "predecessor_phase2_commit": PREDECESSOR_PHASE2_COMMIT,
        "historical_regression_rerun": True,
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "scientific_contract_changed": False,
        "comparator_changed": False,
        "prior_mismatch_and_no_go_preserved": True,
        "regression_artifacts_byte_identical_to_predecessor": True,
        "python_version": platform.python_version(),
        "contract_binding_sha256": sha256_file(PAPER / "contract_binding.json"),
        "contract_spec_sha256": sha256_file(V1_PAPER / "contract_spec.json"),
        "contract_module_sha256": sha256_file(ROOT / "reproduce/biological_topk/contract.py"),
        "coordinate_mapping_sha256": sha256_file(ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"),
        "comparator_sha256": components["reproduce/biological_topk/compare_candidate_topk.py"],
        "component_sha256": components,
        "comparison_count": receipt["comparison_count"],
        "ranking_result_count": receipt["ranking_result_count"],
        "detail_count": receipt["detail_count"],
        "strict_row_mismatch_result_count": receipt["strict_row_mismatch_result_count"],
        "classification_counts": receipt["classification_counts"],
        "successor_regression_sha256": {
            f"paper/biological_topk_successor/{name}": sha256_bytes(by_name[name])
            for name in REGRESSION_NAMES
        },
        "predecessor_regression_sha256": predecessor_hashes,
        "default_fail_closed": True,
        "independent_validation_claim": False,
    }
    payloads[FREEZE_PATH] = canonical_json_bytes(freeze)
    require(set(payloads) == set(OUTPUT_PATHS), "successor Phase 2 output inventory drift")
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payloads = build_payloads()
    if args.write:
        PAPER.mkdir(parents=True, exist_ok=True)
        for path, payload in payloads.items():
            path.write_bytes(payload)
        print(f"wrote {len(payloads)} successor Phase 2 regression artifacts")
        return 0
    stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
    require(not stale, f"successor Phase 2 regression artifacts do not reproduce: {stale}")
    print("successor Phase 2 regression artifacts reproduce byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
