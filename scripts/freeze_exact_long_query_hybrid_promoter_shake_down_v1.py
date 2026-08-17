#!/usr/bin/env python3
"""Freeze the passed real-promoter shake-down and authorize the formal panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs/exact_long_query_hybrid_promoter_panel_v1"
RUN_ROOT = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_promoter_panel_v1"
)
SHAKE_ROOT = RUN_ROOT / "shake_down_v1"
HARNESS_COMMIT = "8feae7e317e5d5c6ee7707d9858faab766d1949f"
EXPECTED_QUERY_IDS = (
    "ENSG00000286042",
    "ENSG00000215068",
    "ENSG00000246090",
    "ENSG00000269086",
    "ENSG00000254319",
    "ENSG00000241316",
)


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, object]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_matrix() -> list[dict[str, str]]:
    path = DOC_ROOT / "execution_matrix.tsv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None and all(None not in row for row in rows), "malformed execution matrix")
    return rows


def verify_file(path: Path, expected_sha256: str, expected_bytes: int | None = None) -> None:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe artifact: {path}")
    if expected_bytes is not None:
        require(path.stat().st_size == expected_bytes, f"artifact size mismatch: {path}")
    require(sha256_file(path) == expected_sha256, f"artifact digest mismatch: {path}")


def verify_case(case_root: Path, arm: str) -> dict[str, object]:
    receipt_path = case_root / "receipt.json"
    receipt = load_json(receipt_path)
    require(
        receipt.get("status") == "complete"
        and receipt.get("technical_contract_pass") is True
        and receipt.get("arm") == arm,
        f"{arm} case did not complete",
    )
    artifacts = receipt.get("artifacts")
    require(isinstance(artifacts, list) and len(artifacts) == 1, f"{arm} artifact inventory mismatch")
    artifact = artifacts[0]
    require(isinstance(artifact, dict), f"{arm} artifact metadata malformed")
    verify_file(Path(str(artifact["path"])), str(artifact["sha256"]), int(artifact["bytes"]))
    if arm == "candidate":
        consumer = receipt.get("consumer")
        forward = receipt.get("forward")
        require(isinstance(consumer, dict) and isinstance(forward, dict), "candidate accounting missing")
        require(
            int(forward["tasks"]) == int(forward["gpu_tasks"]) == 48432,
            "candidate forward task coverage mismatch",
        )
        require(
            int(consumer["attempts"]) == int(consumer["gpu_scored_attempts"]) == 4345980,
            "candidate endpoint attempt coverage mismatch",
        )
        require(
            int(consumer["cpu_oracle_attempts"]) == 0
            and int(consumer["cpu_reference_align_attempts"]) == 0
            and int(consumer["cpu_continuation_failures"]) == 0,
            "candidate CPU oracle/failure gate failed",
        )
    return receipt


def verify_pair() -> dict[str, object]:
    path = SHAKE_ROOT / "pair/pair-receipt.json"
    receipt = load_json(path)
    require(receipt.get("status") == "pair_gate_pass", "paired shake-down did not pass")
    gates = receipt.get("gates")
    require(isinstance(gates, dict) and gates and all(value is True for value in gates.values()), "paired gate is incomplete")
    require(
        receipt.get("raw_tfosorted", {}).get("sha256")
        == "2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075",
        "raw TFOsorted identity drift",
    )
    decode = receipt.get("decode")
    affinity = receipt.get("dbd_dbs_affinity_threshold_zero")
    sites = receipt.get("biological_topk_candidate_site_v1")
    require(isinstance(decode, dict) and isinstance(affinity, dict) and isinstance(sites, dict), "paired downstream evidence missing")
    baseline_decode = decode["baseline_summary"]
    candidate_decode = decode["candidate_summary"]
    require(isinstance(baseline_decode, dict) and isinstance(candidate_decode, dict), "decode summaries malformed")
    count_fields = (
        "raw_source_rows",
        "decoded_unique_source_hits",
        "exact_duplicate_rows_removed",
        "retained_source_hits",
        "mapped_promoter_associations",
        "rejected_source_hits",
        "rejection_reason_counts",
    )
    require(
        all(baseline_decode[field] == candidate_decode[field] for field in count_fields),
        "paired decode counts differ",
    )
    expected_decode = {
        "raw_source_rows": 44753,
        "decoded_unique_source_hits": 44477,
        "exact_duplicate_rows_removed": 276,
        "retained_source_hits": 44209,
        "mapped_promoter_associations": 63368,
        "rejected_source_hits": 268,
        "rejection_reason_counts": {"cross_component_boundary": 268},
    }
    require(all(baseline_decode[key] == value for key, value in expected_decode.items()), "frozen decode result drift")
    for metadata in decode["exact_artifacts"].values():
        require(isinstance(metadata, dict) and metadata.get("status") == "byte_identical", "decode artifact mismatch")
    for metadata in affinity["exact_artifacts"].values():
        require(isinstance(metadata, dict) and metadata.get("status") == "byte_identical", "affinity artifact mismatch")
    require(
        affinity["baseline"]["counts"] == affinity["candidate"]["counts"]
        == {
            "dbs_peaks_below_affinity_threshold": 0,
            "dbs_peaks_total": 8639,
            "lncrna_promoter_pairs": 1395,
            "lncrna_target_gene_pairs": 1395,
            "rejected_source_hits": 268,
            "strong_dbs": 8639,
        },
        "frozen affinity counts drift",
    )
    require(
        sites["baseline"]["row_count"] == sites["candidate"]["row_count"] == 15
        and sites["exact_artifact"]["status"] == "byte_identical",
        "candidate-site equality drift",
    )
    return receipt


def freshness_audit() -> dict[str, object]:
    root = Path("/data/wenyujianData/linjieData/longtarget_runs")
    matches: dict[str, list[str]] = {}
    for gene_id in EXPECTED_QUERY_IDS:
        values = sorted(root.glob(f"human_genes20cells_ge2048_*/raw_jobs/{gene_id}"))
        matches[gene_id] = [str(path) for path in values]
    require(all(not values for values in matches.values()), "fresh query acquired an external production-target job")
    return {
        "status": "pass",
        "query_count": len(EXPECTED_QUERY_IDS),
        "external_production_target_matches": matches,
    }


def build_artifacts(authorized_utc: str) -> dict[str, bytes]:
    matrix = read_matrix()
    formal = [row for row in matrix if row["stage"] == "fresh_full_promoter_panel"]
    require(len(formal) == 36, "formal execution row count drift")
    require({row["gene_id"] for row in formal} == set(EXPECTED_QUERY_IDS), "formal query set drift")
    require(
        all(row["authorization"] == "pending_shake_down_gate" for row in formal),
        "preexecution matrix authorization state drift",
    )
    baseline = verify_case(SHAKE_ROOT / "baseline_1", "baseline")
    candidate = verify_case(SHAKE_ROOT / "candidate_1", "candidate")
    require(baseline["workload_id"] == candidate["workload_id"], "shake case identity mismatch")
    pair = verify_pair()
    fresh = freshness_audit()
    pair_path = SHAKE_ROOT / "pair/pair-receipt.json"
    decision = {
        "schema_version": "exact_long_query_hybrid_promoter_shake_down_decision_v1",
        "status": "pass",
        "authorized_utc": authorized_utc,
        "harness_commit": HARNESS_COMMIT,
        "workload_id": baseline["workload_id"],
        "source_receipts": {
            "baseline": {
                "path": str((SHAKE_ROOT / "baseline_1/receipt.json").resolve()),
                "sha256": sha256_file(SHAKE_ROOT / "baseline_1/receipt.json"),
            },
            "candidate": {
                "path": str((SHAKE_ROOT / "candidate_1/receipt.json").resolve()),
                "sha256": sha256_file(SHAKE_ROOT / "candidate_1/receipt.json"),
            },
            "pair": {"path": str(pair_path.resolve()), "sha256": sha256_file(pair_path)},
        },
        "runtime": {
            "binary_sha256": baseline["binary"]["sha256"],
            "raw_tfosorted_sha256": pair["raw_tfosorted"]["sha256"],
            "baseline_wall_seconds_diagnostic_only": baseline["wall_seconds"],
            "candidate_wall_seconds_diagnostic_only": candidate["wall_seconds"],
            "diagnostic_speedup": float(baseline["wall_seconds"]) / float(candidate["wall_seconds"]),
            "performance_formal": False,
            "reason": "unrelated OpenMP production worker was active",
        },
        "evidence": {
            "raw_tfosorted_byte_identical": True,
            "forward_gpu_tasks": candidate["forward"]["gpu_tasks"],
            "gpu_endpoint_attempts": candidate["consumer"]["gpu_scored_attempts"],
            "cpu_all_attempt_oracle": candidate["consumer"]["cpu_oracle_attempts"],
            "cpu_reference_align_attempts": candidate["consumer"]["cpu_reference_align_attempts"],
            "selected_continuation_failures": candidate["consumer"]["cpu_continuation_failures"],
            "decoded_unique_source_hits": pair["decode"]["baseline_summary"]["decoded_unique_source_hits"],
            "rejected_source_hits": pair["decode"]["baseline_summary"]["rejected_source_hits"],
            "rejection_reason_counts": pair["decode"]["baseline_summary"]["rejection_reason_counts"],
            "mapped_promoter_associations": pair["decode"]["baseline_summary"]["mapped_promoter_associations"],
            "dbs_peaks_threshold_zero": pair["dbd_dbs_affinity_threshold_zero"]["baseline"]["counts"]["dbs_peaks_total"],
            "promoter_affinity_pairs": pair["dbd_dbs_affinity_threshold_zero"]["baseline"]["counts"]["lncrna_promoter_pairs"],
            "candidate_site_rows": pair["biological_topk_candidate_site_v1"]["baseline"]["row_count"],
            "all_pair_gates": pair["gates"],
        },
        "freshness_audit": fresh,
        "decision": "authorize_fresh_full_promoter_panel_execution",
        "production_authorized": False,
        "bioinformatics_v2_state_modified": False,
    }
    addendum = {
        "schema_version": "exact_long_query_hybrid_promoter_formal_execution_addendum_v1",
        "status": "formal_execution_authorized",
        "authorized_utc": authorized_utc,
        "harness_commit": HARNESS_COMMIT,
        "shake_down_decision_sha256": hashlib.sha256(json_bytes(decision)).hexdigest(),
        "execution_matrix_sha256": sha256_file(DOC_ROOT / "execution_matrix.tsv"),
        "fresh_queries_sha256": sha256_file(DOC_ROOT / "fresh_queries.tsv"),
        "formal_panel_authorized": True,
        "formal_run_count": 36,
        "query_ids": list(EXPECTED_QUERY_IDS),
        "target_artifact_id": "logical_full_concat",
        "target_length_bp": 164917643,
        "required_runtime_conditions": {
            "case_runner_must_recheck_query_freshness": True,
            "complete_tfosorted_only": True,
            "cpu_hybrid_pairing": True,
            "repeats_per_arm": 3,
            "affinity_threshold": 0,
            "fail_closed_on_any_gpu_or_mapping_counter": True,
        },
        "performance_note": "shake-down timing was diagnostic only; formal performance requires separately controlled paired timing",
        "production_authorized": False,
        "gpu_only_claim": False,
        "bioinformatics_v2_state_modified": False,
    }
    artifacts = {
        "shake_down_decision.json": json_bytes(decision),
        "formal_execution_addendum.json": json_bytes(addendum),
    }
    artifacts["post_shake_checksums.sha256"] = "".join(
        f"{hashlib.sha256(value).hexdigest()}  docs/exact_long_query_hybrid_promoter_panel_v1/{name}\n"
        for name, value in sorted(artifacts.items())
    ).encode("ascii")
    return artifacts


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--write", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    addendum_path = DOC_ROOT / "formal_execution_addendum.json"
    if args.write:
        require(not addendum_path.exists(), "formal execution addendum already exists")
        authorized_utc = datetime.now(timezone.utc).isoformat()
    else:
        authorized_utc = str(load_json(addendum_path)["authorized_utc"])
    artifacts = build_artifacts(authorized_utc)
    for name, value in artifacts.items():
        path = DOC_ROOT / name
        if args.write:
            atomic_bytes(path, value)
        else:
            require(path.is_file() and path.read_bytes() == value, f"post-shake artifact drift: {path}")
    print(json.dumps({
        "status": "formal_execution_authorized",
        "formal_panel_authorized": True,
        "formal_run_count": 36,
        "query_ids": list(EXPECTED_QUERY_IDS),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(2)
