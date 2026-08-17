#!/usr/bin/env python3
"""Freeze the input-only canonical-hybrid-v2 A/H performance pilot."""

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
CORRECTNESS_SELECTION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_selection.json"
CORRECTNESS_PLAN_RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_plan_receipt.json"
SELECTION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_selection.json"
WORKLOAD_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_workloads.tsv"
PLAN_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_plan.tsv"
PLAN_CHECKSUM_PATH = PLAN_PATH.with_suffix(".sha256")
RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_plan_receipt.json"
FREEZE_CHECKSUM_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_freeze.sha256"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/performance-pilot"
SELECTION_SEED = "canonical-hybrid-v2-performance-pilot-ordinal-v1-20260727"
QUERY_STRATA = ("short_500_800", "medium_801_1600", "long_1601_2812")
TARGET_CHROMOSOMES = ("chr21", "chr22")
PRIOR_V1_PILOT_PREFIX_COUNT = 1
REPEATS_PER_WORKLOAD = 3
SPEEDUP_THRESHOLD = 10.0
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
    require(not path.exists(), f"refusing to replace frozen performance artifact: {path}")
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
    require(not status, f"performance freeze requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def load_runner():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_performance_freeze_runner", RUNNER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical hybrid runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_application_manifest() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    checksum = APPLICATION_MANIFEST_CHECKSUM_PATH.read_text(encoding="ascii").strip().split()
    require(
        len(checksum) == 2
        and checksum[1] == APPLICATION_MANIFEST_PATH.name
        and checksum[0] == sha256_file(APPLICATION_MANIFEST_PATH),
        "application manifest checksum drift",
    )
    with APPLICATION_MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
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


def correctness_used_ordinals() -> tuple[set[int], set[int]]:
    correctness = json.loads(CORRECTNESS_SELECTION_PATH.read_text(encoding="utf-8"))
    plan_receipt = json.loads(CORRECTNESS_PLAN_RECEIPT_PATH.read_text(encoding="utf-8"))
    require(plan_receipt["selection_sha256"] == sha256_file(CORRECTNESS_SELECTION_PATH), "correctness selection identity drift")
    require(correctness["prior_pilot_outcomes_read"] is False, "correctness selection boundary drift")
    return (
        {int(row["source_ordinal"]) for row in correctness["selected_queries"]},
        {int(row["source_ordinal"]) for row in correctness["selected_targets"]},
    )


def select_inputs(
    queries: list[dict[str, object]],
    targets: list[dict[str, object]],
    used_query_ordinals: set[int],
    used_target_ordinals: set[int],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    selected_queries: list[dict[str, object]] = []
    for stratum in QUERY_STRATA:
        candidates = []
        for row in queries:
            ordinal = int(row["source_ordinal"])
            length = int(row["sequence_length"])
            if (
                ordinal <= PRIOR_V1_PILOT_PREFIX_COUNT
                or ordinal in used_query_ordinals
                or query_stratum(length) != stratum
            ):
                continue
            candidates.append(
                {
                    **row,
                    "query_stratum": stratum,
                    "selection_hash": ordinal_selection_hash("query", stratum, ordinal),
                }
            )
        candidates.sort(key=lambda row: (str(row["selection_hash"]), int(row["source_ordinal"])))
        require(candidates, f"no unused performance query in {stratum}")
        selected_queries.append(candidates[0])

    selected_targets: list[dict[str, object]] = []
    for chromosome in TARGET_CHROMOSOMES:
        candidates = []
        for row in targets:
            ordinal = int(row["source_ordinal"])
            if (
                ordinal <= PRIOR_V1_PILOT_PREFIX_COUNT
                or ordinal in used_target_ordinals
                or row["chromosome"] != chromosome
            ):
                continue
            candidates.append(
                {
                    **row,
                    "selection_hash": ordinal_selection_hash("target", chromosome, ordinal),
                }
            )
        candidates.sort(key=lambda row: (str(row["selection_hash"]), int(row["source_ordinal"])))
        require(candidates, f"no unused performance target on {chromosome}")
        selected_targets.append(candidates[0])
    return selected_queries, selected_targets


def verify_selected_files(rows: list[dict[str, object]]) -> None:
    for row in rows:
        path = (ROOT / str(row["path"])).resolve()
        require(ROOT in path.parents and path.is_file() and not path.is_symlink(), f"unsafe selected input: {path}")
        require(sha256_file(path) == row["file_sha256"], f"selected input digest drift: {path}")


def build_payloads(freeze_commit: str, created_utc: str) -> dict[Path, bytes]:
    runner = load_runner()
    runtime = runner.read_runtime_receipt()
    require(runtime.get("runtime_revision") == 2 and runtime.get("scientific_runtime_changed") is False, "runtime boundary drift")
    queries, targets = read_application_manifest()
    used_query_ordinals, used_target_ordinals = correctness_used_ordinals()
    selected_queries, selected_targets = select_inputs(
        queries, targets, used_query_ordinals, used_target_ordinals
    )
    verify_selected_files(selected_queries + selected_targets)
    require(
        not ({int(row["source_ordinal"]) for row in selected_queries} & used_query_ordinals)
        and not ({int(row["source_ordinal"]) for row in selected_targets} & used_target_ordinals),
        "performance input overlaps correctness input",
    )

    workloads: list[dict[str, object]] = []
    workload_rows: list[dict[str, object]] = []
    for query in selected_queries:
        for target in selected_targets:
            workload_id = f"vp{len(workloads) + 1:03d}"
            workloads.append({"workload_id": workload_id, "query": query, "target": target})
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
                    "repeat_count": REPEATS_PER_WORKLOAD,
                    "status": "preregistered_not_run",
                }
            )
    require(len(workloads) == 6, "performance workload count drift")
    workload_payload = tsv_bytes(WORKLOAD_FIELDS, workload_rows)

    runtime_sha256 = sha256_file(RUNTIME_PATH)
    plan_rows: list[dict[str, object]] = []
    validation_index = 0
    for workload in workloads:
        for repeat_id in range(REPEATS_PER_WORKLOAD):
            validation_index += 1
            validation_id = f"{workload['workload_id']}__repeat{repeat_id:02d}"
            authority_attempt = f"v2perf_{validation_id}_a"
            hybrid_attempt = f"v2perf_{validation_id}_h"
            common = {
                "stage": "performance-pilot",
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
                "claim_role": "fixed_performance_promotion",
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
                    "expected_artifact_root": f"performance-pilot/{authority_attempt}",
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
                    "expected_artifact_root": f"performance-pilot/{hybrid_attempt}",
                }
            )
    require(validation_index == 18 and len(plan_rows) == 36, "performance attempt count drift")
    plan_payload = tsv_bytes(runner.PLAN_FIELDS, plan_rows)

    selection = {
        "schema_version": 1,
        "stage": "performance-pilot",
        "selection_seed": SELECTION_SEED,
        "source_application_manifest_sha256": sha256_file(APPLICATION_MANIFEST_PATH),
        "source_correctness_selection_sha256": sha256_file(CORRECTNESS_SELECTION_PATH),
        "correctness_results_or_timings_read": False,
        "selection_key_definition": "SHA256(seed|kind|coverage_group|source-ordinal-N)",
        "selection_key_uses_only": ["frozen role-local source ordinal", "query length stratum", "target chromosome coverage group"],
        "selection_key_prohibited_inputs": [
            "query or gene name",
            "target or gene name",
            "sequence or file digest",
            "correctness output or timing",
            "runtime",
            "mismatch",
            "fallback",
            "result-based blacklist",
            "result-based allowlist",
        ],
        "prohibited_selection_input_used": False,
        "input_partition_rule": "exclude the frozen v1 pilot ordinal prefix and all ordinals already allocated to the fresh correctness split, independent of their outcomes",
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
            "workloads": 6,
            "repeats_per_workload": REPEATS_PER_WORKLOAD,
            "validation_instances": 18,
            "arms_per_validation": ["A", "H"],
            "attempts": 36,
        },
        "status": "preregistered_not_run",
    }
    selection_payload = json_bytes(selection)
    plan_sha256 = sha256_bytes(plan_payload)
    receipt = {
        "schema_version": 1,
        "stage": "performance-pilot",
        "status": "preregistered_not_run",
        "freeze_commit": freeze_commit,
        "created_utc": created_utc,
        "selection_seed": SELECTION_SEED,
        "selection_sha256": sha256_bytes(selection_payload),
        "workload_manifest_sha256": sha256_bytes(workload_payload),
        "plan_sha256": plan_sha256,
        "source_application_manifest_sha256": sha256_file(APPLICATION_MANIFEST_PATH),
        "source_correctness_selection_sha256": sha256_file(CORRECTNESS_SELECTION_PATH),
        "correctness_results_or_timings_read_for_selection": False,
        "runtime_receipt_sha256": runtime_sha256,
        "runtime_epoch": runtime["runtime_epoch"],
        "runtime_revision": runtime["runtime_revision"],
        "runtime_commit": runtime["runtime_commit"],
        "runner_commit": runtime["runner_commit"],
        "runner_sha256": runtime["runner_sha256"],
        "workload_count": 6,
        "validation_count": 18,
        "attempt_count": 36,
        "arm_counts": {"A": 18, "H": 18},
        "repeats_per_workload": REPEATS_PER_WORKLOAD,
        "execution_order": "A_then_H_per_validation",
        "gpu_assignment": "validation_index_zero_based_modulo_2",
        "gpu_counts": {"0": 9, "1": 9},
        "backend_timeout_seconds": 3600,
        "retry_policy": "none",
        "replacement_retry_allowed": False,
        "formal_source_data": True,
        "promotion_eligible": True,
        "correctness_requirement": "zero declared-contract mismatch and zero technical failure across all 18 validation instances",
        "primary_performance_metric": "sum(authority isolated wall seconds) / sum(hybrid isolated wall seconds)",
        "secondary_performance_metric": "projected fixed-two-worker authority makespan / projected fixed-two-worker hybrid makespan",
        "performance_gate_rule": "both primary and secondary speedups must be >=10.0 with correctness clean",
        "performance_speedup_threshold": SPEEDUP_THRESHOLD,
        "performance_speedup_threshold_changed": False,
        "lower_substitute_threshold_allowed": False,
        "complete_cpu_authority_inside_hybrid": False,
        "candidate_v1_or_sequential_verified_timing_allowed": False,
        "expected_artifact_root": ".paper-artifacts/bioinformatics-canonical-hybrid-v2/performance-pilot",
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
    require(not ARTIFACT_ROOT.exists(), "performance execution artifact root already exists")
    for path, payload in payloads.items():
        atomic_new(path, payload)


def check_payloads() -> dict[str, object]:
    require(RECEIPT_PATH.is_file() and not RECEIPT_PATH.is_symlink(), "performance plan receipt is missing")
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    freeze_commit = str(receipt["freeze_commit"])
    require(git_output("merge-base", "--is-ancestor", freeze_commit, "HEAD") == "", "performance freeze commit is not an ancestor")
    frozen_builder = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{freeze_commit}:{Path(__file__).resolve().relative_to(ROOT).as_posix()}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(frozen_builder.returncode == 0, "performance builder is not committed at freeze identity")
    require(sha256_bytes(frozen_builder.stdout) == sha256_file(Path(__file__).resolve()), "performance builder drift")
    expected = build_payloads(freeze_commit, str(receipt["created_utc"]))
    for path, payload in expected.items():
        require(path.is_file() and not path.is_symlink(), f"missing performance freeze artifact: {path}")
        require(path.read_bytes() == payload, f"performance freeze artifact drift: {path}")
    require(not ARTIFACT_ROOT.exists(), "performance execution already started")
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
        print(f"canonical-hybrid-v2 performance freeze failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
