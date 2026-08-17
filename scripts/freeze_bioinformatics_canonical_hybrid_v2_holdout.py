#!/usr/bin/env python3
"""Freeze the input-only canonical-hybrid-v2 fresh correctness holdout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "reproduce/bioinformatics/run_canonical_hybrid_v2.py"
RUNTIME_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_runtime.json"
APPLICATION_MANIFEST_PATH = ROOT / "paper/bioinformatics/application_manifest.tsv"
APPLICATION_MANIFEST_CHECKSUM_PATH = ROOT / "paper/bioinformatics/application_manifest.sha256"
APPLICATION_PROTOCOL_PATH = ROOT / "paper/bioinformatics/application_protocol.md"
SELECTION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_selection.json"
WORKLOAD_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_workloads.tsv"
PLAN_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_plan.tsv"
PLAN_CHECKSUM_PATH = PLAN_PATH.with_suffix(".sha256")
RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_plan_receipt.json"
FREEZE_CHECKSUM_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_freeze.sha256"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout"
SELECTION_SEED = "canonical-hybrid-v2-fresh-holdout-ordinal-v1-20260727"
QUERY_STRATA = ("short_500_800", "medium_801_1600", "long_1601_2812")
TARGET_CHROMOSOMES = ("chr21", "chr22")
QUERY_COUNT_PER_STRATUM = 4
TARGET_COUNT_PER_CHROMOSOME = 2
PRIOR_PILOT_QUERY_PREFIX_COUNT = 1
PRIOR_PILOT_TARGET_PREFIX_COUNT = 1
WORKLOAD_FIELDS = (
    "workload_id",
    "query_source_ordinal",
    "query_id",
    "query_length",
    "query_stratum",
    "query_selection_hash",
    "target_source_ordinal",
    "target_id",
    "target_chromosome",
    "target_selection_hash",
    "query_path",
    "target_path",
    "repeat_count",
    "repeat_subset",
    "status",
)


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fieldnames: Sequence[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="raise"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_new(path: Path, payload: bytes) -> None:
    require(not path.exists(), f"refusing to replace frozen holdout artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_clean_checkout() -> str:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all", "--ignored=no")
    require(not status, f"holdout freeze requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def load_runner():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_holdout_freeze_runner", RUNNER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical hybrid runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_application_manifest() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    require(APPLICATION_MANIFEST_PATH.is_file() and not APPLICATION_MANIFEST_PATH.is_symlink(), "unsafe application manifest")
    checksum = APPLICATION_MANIFEST_CHECKSUM_PATH.read_text(encoding="ascii").strip().split()
    require(
        len(checksum) == 2
        and checksum[1] == APPLICATION_MANIFEST_PATH.name
        and checksum[0] == sha256_file(APPLICATION_MANIFEST_PATH),
        "application manifest checksum drift",
    )
    with APPLICATION_MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    require(len(rows) == 718, "application manifest record count drift")
    queries: list[dict[str, object]] = []
    targets: list[dict[str, object]] = []
    for row in rows:
        require(row["status"] == "preregistered_not_run" and row["split"] == "application", "application state drift")
        if row["record_role"] == "query":
            queries.append({**row, "source_ordinal": len(queries) + 1})
        elif row["record_role"] == "target":
            targets.append({**row, "source_ordinal": len(targets) + 1})
        else:
            raise FreezeError(f"unknown application role: {row['record_role']}")
    require(len(queries) == 50 and len(targets) == 668, "application input count drift")
    return queries, targets


def query_stratum(length: int) -> str:
    if 500 <= length <= 800:
        return QUERY_STRATA[0]
    if 801 <= length <= 1600:
        return QUERY_STRATA[1]
    if 1601 <= length <= 2812:
        return QUERY_STRATA[2]
    raise FreezeError(f"query length outside frozen strata: {length}")


def ordinal_selection_hash(kind: str, group: str, source_ordinal: int) -> str:
    payload = f"{SELECTION_SEED}|{kind}|{group}|source-ordinal-{source_ordinal}".encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def select_inputs(
    queries: list[dict[str, object]], targets: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    selected_queries: list[dict[str, object]] = []
    for stratum in QUERY_STRATA:
        candidates = []
        for row in queries:
            ordinal = int(row["source_ordinal"])
            length = int(row["sequence_length"])
            if ordinal <= PRIOR_PILOT_QUERY_PREFIX_COUNT or query_stratum(length) != stratum:
                continue
            candidates.append(
                {
                    **row,
                    "query_stratum": stratum,
                    "selection_hash": ordinal_selection_hash("query", stratum, ordinal),
                }
            )
        candidates.sort(key=lambda row: (str(row["selection_hash"]), int(row["source_ordinal"])))
        require(len(candidates) >= QUERY_COUNT_PER_STRATUM, f"insufficient query candidates in {stratum}")
        selected_queries.extend(candidates[:QUERY_COUNT_PER_STRATUM])

    selected_targets: list[dict[str, object]] = []
    for chromosome in TARGET_CHROMOSOMES:
        candidates = []
        for row in targets:
            ordinal = int(row["source_ordinal"])
            if ordinal <= PRIOR_PILOT_TARGET_PREFIX_COUNT or row["chromosome"] != chromosome:
                continue
            candidates.append(
                {
                    **row,
                    "selection_hash": ordinal_selection_hash("target", chromosome, ordinal),
                }
            )
        candidates.sort(key=lambda row: (str(row["selection_hash"]), int(row["source_ordinal"])))
        require(len(candidates) >= TARGET_COUNT_PER_CHROMOSOME, f"insufficient targets on {chromosome}")
        selected_targets.extend(candidates[:TARGET_COUNT_PER_CHROMOSOME])

    require(len(selected_queries) == 12 and len(selected_targets) == 4, "fresh holdout input count drift")
    return selected_queries, selected_targets


def verify_selected_files(rows: list[dict[str, object]]) -> None:
    for row in rows:
        path = (ROOT / str(row["path"])).resolve()
        require(ROOT in path.parents and path.is_file() and not path.is_symlink(), f"unsafe selected input: {path}")
        require(sha256_file(path) == row["file_sha256"], f"selected input digest drift: {path}")


def build_payloads(freeze_commit: str, created_utc: str) -> dict[Path, bytes]:
    runner = load_runner()
    runtime = runner.read_runtime_receipt()
    require(runtime.get("runtime_revision") == 2, "fresh holdout requires runner revision 2")
    require(runtime.get("scientific_runtime_changed") is False, "runner-only runtime boundary drift")
    require(runtime.get("runner_change_scope") == "comparator_bytecode_isolation_and_snapshot_integrity_only", "runner scope drift")
    queries, targets = read_application_manifest()
    selected_queries, selected_targets = select_inputs(queries, targets)
    verify_selected_files(selected_queries + selected_targets)

    repeated_query_ordinals = {
        int(next(row["source_ordinal"] for row in selected_queries if row["query_stratum"] == stratum))
        for stratum in QUERY_STRATA
    }
    repeated_target_ordinals = {
        int(next(row["source_ordinal"] for row in selected_targets if row["chromosome"] == chromosome))
        for chromosome in TARGET_CHROMOSOMES
    }
    workload_rows: list[dict[str, object]] = []
    workloads: list[dict[str, object]] = []
    for query in selected_queries:
        for target in selected_targets:
            repeat_subset = (
                int(query["source_ordinal"]) in repeated_query_ordinals
                and int(target["source_ordinal"]) in repeated_target_ordinals
            )
            workload_id = f"vh{len(workloads) + 1:03d}"
            workload = {
                "workload_id": workload_id,
                "query": query,
                "target": target,
                "repeat_subset": repeat_subset,
            }
            workloads.append(workload)
            workload_rows.append(
                {
                    "workload_id": workload_id,
                    "query_source_ordinal": query["source_ordinal"],
                    "query_id": query["record_id"],
                    "query_length": query["sequence_length"],
                    "query_stratum": query["query_stratum"],
                    "query_selection_hash": query["selection_hash"],
                    "target_source_ordinal": target["source_ordinal"],
                    "target_id": target["record_id"],
                    "target_chromosome": target["chromosome"],
                    "target_selection_hash": target["selection_hash"],
                    "query_path": query["path"],
                    "target_path": target["path"],
                    "repeat_count": 3 if repeat_subset else 1,
                    "repeat_subset": int(repeat_subset),
                    "status": "preregistered_not_run",
                }
            )
    require(len(workloads) == 48 and sum(row["repeat_subset"] for row in workload_rows) == 6, "workload shape drift")
    workload_payload = tsv_bytes(WORKLOAD_FIELDS, workload_rows)

    runtime_sha256 = sha256_file(RUNTIME_PATH)
    plan_rows: list[dict[str, object]] = []
    validation_index = 0
    for workload in workloads:
        repeat_ids = range(3) if workload["repeat_subset"] else range(1)
        for repeat_id in repeat_ids:
            validation_index += 1
            validation_id = f"{workload['workload_id']}__repeat{repeat_id:02d}"
            authority_attempt = f"v2hold_{validation_id}_a"
            hybrid_attempt = f"v2hold_{validation_id}_h"
            common = {
                "stage": "fresh-holdout",
                "validation_id": validation_id,
                "repeat_id": str(repeat_id),
                "query_id": workload["query"]["record_id"],
                "target_id": workload["target"]["record_id"],
                "query_path": workload["query"]["path"],
                "target_path": workload["target"]["path"],
                "query_sha256": workload["query"]["file_sha256"],
                "target_sha256": workload["target"]["file_sha256"],
                "runtime_commit": runtime["runtime_commit"],
                "hybrid_binary_sha256": runtime["hybrid_binary_sha256"],
                "authority_binary_sha256": runtime["authority_binary_sha256"],
                "runner_commit": runtime["runner_commit"],
                "runner_sha256": runtime["runner_sha256"],
                "runtime_receipt_sha256": runtime_sha256,
                "backend_timeout_seconds": "3600",
                "contract": "all-ranked-top5-canonical-row-v2",
                "claim_role": "fresh_correctness_promotion",
                "promotion_eligible": "1",
                "formal_source_data": "1",
                "retry_policy": "none",
                "status": "preregistered_not_run",
            }
            plan_rows.append(
                {
                    **common,
                    "attempt_id": authority_attempt,
                    "arm": "A",
                    "order": str(len(plan_rows) + 1),
                    "authority_reference_kind": "none",
                    "authority_reference": "NA",
                    "authority_reference_sha256": "NA",
                    "gpu_physical_index": "NA",
                    "expected_artifact_root": f"fresh-holdout/{authority_attempt}",
                }
            )
            plan_rows.append(
                {
                    **common,
                    "attempt_id": hybrid_attempt,
                    "arm": "H",
                    "order": str(len(plan_rows) + 1),
                    "authority_reference_kind": "stage_attempt",
                    "authority_reference": authority_attempt,
                    "authority_reference_sha256": "derived_from_completed_stage_A_attempt",
                    "gpu_physical_index": str((validation_index - 1) % 2),
                    "expected_artifact_root": f"fresh-holdout/{hybrid_attempt}",
                }
            )
    require(validation_index == 60 and len(plan_rows) == 120, "holdout attempt count drift")
    plan_payload = tsv_bytes(runner.PLAN_FIELDS, plan_rows)

    selection = {
        "schema_version": 1,
        "stage": "fresh-holdout",
        "selection_seed": SELECTION_SEED,
        "source_application_manifest_sha256": sha256_file(APPLICATION_MANIFEST_PATH),
        "source_application_protocol_sha256": sha256_file(APPLICATION_PROTOCOL_PATH),
        "selection_key_definition": "SHA256(seed|kind|coverage_group|source-ordinal-N)",
        "selection_key_uses_only": ["frozen role-local source ordinal", "query length stratum", "target chromosome coverage group"],
        "selection_key_prohibited_inputs": [
            "query or gene name",
            "target or gene name",
            "sequence or file digest",
            "observed output",
            "runtime",
            "mismatch",
            "fallback",
            "blacklist",
            "allowlist",
        ],
        "prohibited_selection_input_used": False,
        "prior_pilot_outcomes_read": False,
        "prior_v1_pilot_exclusion": {
            "basis": "the first role-local query and target ordinal prefixes were prospectively assigned to the frozen v1 pilot before v2 design",
            "query_source_ordinal_prefix_count": PRIOR_PILOT_QUERY_PREFIX_COUNT,
            "target_source_ordinal_prefix_count": PRIOR_PILOT_TARGET_PREFIX_COUNT,
            "identity_list_used": False,
        },
        "query_design": {"strata": list(QUERY_STRATA), "selected_per_stratum": 4, "selected_total": 12},
        "target_design": {"chromosomes": list(TARGET_CHROMOSOMES), "selected_per_chromosome": 2, "selected_total": 4},
        "selected_queries": [
            {
                "source_ordinal": row["source_ordinal"],
                "record_id": row["record_id"],
                "sequence_length": int(row["sequence_length"]),
                "stratum": row["query_stratum"],
                "ordinal_selection_hash": row["selection_hash"],
            }
            for row in selected_queries
        ],
        "selected_targets": [
            {
                "source_ordinal": row["source_ordinal"],
                "record_id": row["record_id"],
                "chromosome": row["chromosome"],
                "ordinal_selection_hash": row["selection_hash"],
            }
            for row in selected_targets
        ],
        "matrix": {
            "base_workloads": 48,
            "repeat_subset_workloads": 6,
            "repeats_per_subset_workload": 3,
            "validation_instances": 60,
            "arms_per_validation": ["A", "H"],
            "attempts": 120,
        },
        "claim_role": "fresh_correctness_promotion",
        "performance_claim_role": "none",
        "retry_policy": "none",
        "status": "preregistered_not_run",
    }
    selection_payload = json_bytes(selection)
    plan_sha256 = sha256_bytes(plan_payload)
    receipt = {
        "schema_version": 1,
        "stage": "fresh-holdout",
        "status": "preregistered_not_run",
        "freeze_commit": freeze_commit,
        "created_utc": created_utc,
        "selection_seed": SELECTION_SEED,
        "selection_sha256": sha256_bytes(selection_payload),
        "workload_manifest_sha256": sha256_bytes(workload_payload),
        "plan_sha256": plan_sha256,
        "source_application_manifest_sha256": sha256_file(APPLICATION_MANIFEST_PATH),
        "runtime_receipt_sha256": runtime_sha256,
        "runtime_epoch": runtime["runtime_epoch"],
        "runtime_revision": runtime["runtime_revision"],
        "runtime_commit": runtime["runtime_commit"],
        "runner_commit": runtime["runner_commit"],
        "runner_sha256": runtime["runner_sha256"],
        "scientific_runtime_changed_from_regression": runtime["scientific_runtime_changed"],
        "workload_count": 48,
        "repeat_subset_workload_count": 6,
        "validation_count": 60,
        "attempt_count": 120,
        "arm_counts": {"A": 60, "H": 60},
        "gpu_assignment": "validation_index_zero_based_modulo_2",
        "gpu_counts": {"0": 30, "1": 30},
        "execution_order": "A_then_H_per_validation",
        "backend_timeout_seconds": 3600,
        "retry_policy": "none",
        "replacement_retry_allowed": False,
        "formal_source_data": True,
        "promotion_eligible": True,
        "promotion_contract": "all-ranked-top5-canonical-row-v2",
        "promotion_requirement": "zero declared-contract mismatch and zero technical failure across all 60 validation instances",
        "regression_evidence_used_for_promotion": False,
        "performance_promotion_assessed": False,
        "b3_speedup_threshold": 10.0,
        "b3_speedup_threshold_changed": False,
        "complete_cpu_authority_inside_hybrid": False,
        "prior_pilot_outcomes_read_for_selection": False,
        "command_templates": {
            "runner": "python3 reproduce/bioinformatics/run_canonical_hybrid_v2.py --stage fresh-holdout --execute",
            "authority": "{authority_binary} -f1 {target_snapshot} -f2 {query_snapshot} -r 0 -O {output_root}",
            "hybrid": "{hybrid_binary} -f1 {target_snapshot} -f2 {query_snapshot} -r 0 -O {output_root}",
            "comparator": "{python} -B {comparator} --baseline {authority_output} --candidate {hybrid_output} --k 5 --cluster-distance 15 --cluster-length 50 --details {details}",
        },
        "expected_artifact_root": ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout",
        "execution_started": False,
    }
    receipt_payload = json_bytes(receipt)
    plan_checksum_payload = f"{plan_sha256}  {PLAN_PATH.name}\n".encode("ascii")
    freeze_checksum_payload = (
        f"{sha256_bytes(selection_payload)}  {SELECTION_PATH.name}\n"
        f"{sha256_bytes(workload_payload)}  {WORKLOAD_PATH.name}\n"
        f"{plan_sha256}  {PLAN_PATH.name}\n"
        f"{sha256_bytes(receipt_payload)}  {RECEIPT_PATH.name}\n"
    ).encode("ascii")
    return {
        SELECTION_PATH: selection_payload,
        WORKLOAD_PATH: workload_payload,
        PLAN_PATH: plan_payload,
        PLAN_CHECKSUM_PATH: plan_checksum_payload,
        RECEIPT_PATH: receipt_payload,
        FREEZE_CHECKSUM_PATH: freeze_checksum_payload,
    }


def write_payloads(payloads: dict[Path, bytes]) -> None:
    require(not ARTIFACT_ROOT.exists(), "fresh holdout execution artifact root already exists")
    for path, payload in payloads.items():
        atomic_new(path, payload)


def check_payloads() -> dict[str, object]:
    require(RECEIPT_PATH.is_file() and not RECEIPT_PATH.is_symlink(), "holdout plan receipt is missing")
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    freeze_commit = str(receipt["freeze_commit"])
    require(git_output("merge-base", "--is-ancestor", freeze_commit, "HEAD") == "", "holdout freeze commit is not an ancestor")
    frozen_builder = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{freeze_commit}:{Path(__file__).resolve().relative_to(ROOT).as_posix()}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(frozen_builder.returncode == 0, "holdout freeze builder is not committed at freeze identity")
    require(sha256_bytes(frozen_builder.stdout) == sha256_file(Path(__file__).resolve()), "holdout freeze builder drift")
    expected = build_payloads(freeze_commit, str(receipt["created_utc"]))
    for path, payload in expected.items():
        require(path.is_file() and not path.is_symlink(), f"missing holdout freeze artifact: {path}")
        require(path.read_bytes() == payload, f"holdout freeze artifact drift: {path}")
    require(not ARTIFACT_ROOT.exists(), "fresh holdout execution already started")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.write:
            freeze_commit = require_clean_checkout()
            created_utc = datetime.now(timezone.utc).isoformat()
            payloads = build_payloads(freeze_commit, created_utc)
            write_payloads(payloads)
            result = json.loads(payloads[RECEIPT_PATH].decode("utf-8"))
        elif args.check:
            result = check_payloads()
        else:
            payloads = build_payloads(git_output("rev-parse", "HEAD"), "PREVIEW")
            result = json.loads(payloads[RECEIPT_PATH].decode("utf-8"))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"canonical-hybrid-v2 fresh holdout freeze failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
