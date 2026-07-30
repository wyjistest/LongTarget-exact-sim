#!/usr/bin/env python3
"""Freeze the input-only successor Phase 3 concordance panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reproduce.biological_topk import freeze_fresh_holdout as _IMPL  # noqa: E402


PAPER = ROOT / "paper/biological_topk_successor"
PHASE2_COMMIT = "a48bcf814d4d055320ee1ab437666bde9d03d390"
PREDECESSOR_BYTES = 7_142_325_727
FIXED_TOTAL_STORAGE_BYTES = 64 * 1024**3
RAW_G_RESERVATION_BYTES = 1536 * 1024**2
SUCCESSOR_TRACKED_RESERVATION_BYTES = 256 * 1024**2
BOOTSTRAP_SEED = 20260818
BOOTSTRAP_REPLICATES = 10_000
NEAREST_OBSERVATIONS = 7

QUERY_UNIVERSE_PATH = PAPER / "query_source_universe.tsv.gz"
TARGET_UNIVERSE_PATH = PAPER / "target_source_universe.tsv.gz"
EXCLUSION_PATH = PAPER / "successor_exclusion_registry.tsv"
COMPARATOR_FREEZE_PATH = PAPER / "phase2_comparator_freeze.json"
RESOURCE_MODEL_PATH = PAPER / "resource_projection_model.json"
RESOURCE_PLAN_PATH = PAPER / "resource_projection.json"
OWNER_QUOTA_PATH = PAPER / "owner_successor_authorization.json"
RUNNER_PATH = ROOT / "reproduce/biological_topk_successor/run_phase4.py"
ANALYZER_PATH = ROOT / "reproduce/biological_topk_successor/analyze_phase4.py"
PLAN_PATH = PAPER / "fresh_holdout_plan.json"
MANIFEST_PATH = PAPER / "fresh_holdout_manifest.tsv"
ATTEMPT_PLAN_PATH = PAPER / "fresh_holdout_attempt_plan.tsv"
MANIFEST_CHECKSUM_PATH = PAPER / "fresh_holdout_manifest.sha256"
RESOURCE_PROJECTION_PATH = PAPER / "fresh_holdout_resource_projection.json"
RESOURCE_DECISION_PATH = PAPER / "fresh_holdout_resource_decision.json"
SELECTION_SEED = "biological_topk_successor_phase3_panel_v2_20260818"
RESOURCE_MODEL_SHA256 = "1a358de7383b1a6d2e046ef2fa8e4fa0e3fd8d026849e191a8955321fea6f504"


_ORIGINAL_BUILD_MANIFEST = _IMPL.build_manifest
_ORIGINAL_BUILD_ATTEMPT_PLAN = _IMPL.build_attempt_plan
_ORIGINAL_BUILD = _IMPL.build


def _configure() -> None:
    replacements = {
        "PAPER": PAPER,
        "QUERY_UNIVERSE_PATH": QUERY_UNIVERSE_PATH,
        "TARGET_UNIVERSE_PATH": TARGET_UNIVERSE_PATH,
        "EXCLUSION_PATH": EXCLUSION_PATH,
        "COMPARATOR_FREEZE_PATH": COMPARATOR_FREEZE_PATH,
        "RESOURCE_MODEL_PATH": RESOURCE_MODEL_PATH,
        "RESOURCE_PLAN_PATH": RESOURCE_PLAN_PATH,
        "OWNER_QUOTA_PATH": OWNER_QUOTA_PATH,
        "RUNNER_PATH": RUNNER_PATH,
        "ANALYZER_PATH": ANALYZER_PATH,
        "PLAN_PATH": PLAN_PATH,
        "MANIFEST_PATH": MANIFEST_PATH,
        "ATTEMPT_PLAN_PATH": ATTEMPT_PLAN_PATH,
        "MANIFEST_CHECKSUM_PATH": MANIFEST_CHECKSUM_PATH,
        "RESOURCE_PROJECTION_PATH": RESOURCE_PROJECTION_PATH,
        "RESOURCE_DECISION_PATH": RESOURCE_DECISION_PATH,
        "SELECTION_SEED": SELECTION_SEED,
        "RESOURCE_MODEL_SHA256": RESOURCE_MODEL_SHA256,
        "MAX_STORAGE_BYTES": FIXED_TOTAL_STORAGE_BYTES,
    }
    for name, value in replacements.items():
        setattr(_IMPL, name, value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tracked_successor_bytes_at_phase2() -> int:
    completed = subprocess.run(
        ("git", "ls-tree", "-r", "-l", PHASE2_COMMIT),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _IMPL.require(completed.returncode == 0, completed.stderr.strip() or "cannot inventory Phase 2 tree")
    total = 0
    for line in completed.stdout.splitlines():
        metadata, relative = line.split("\t", 1)
        size = metadata.split()[3]
        included = (
            relative == "goal-biological-topk-successor.md"
            or relative == "schemas/biological_topk_successor_program_state.schema.json"
            or relative.startswith("paper/biological_topk_successor/")
            or relative.startswith("reproduce/biological_topk_successor/")
            or relative.startswith("tests/biological_topk_successor/")
            or relative.startswith("scripts/check_biological_topk_successor_")
        )
        if included:
            _IMPL.require(size != "-", f"non-blob in successor tracked inventory: {relative}")
            total += int(size)
    _IMPL.require(total > 0, "empty successor tracked inventory")
    return total


def build_manifest(
    queries: Mapping[str, list[dict[str, Any]]],
    targets: Mapping[str, list[dict[str, Any]]],
    indexes: Mapping[str, set[Any]],
) -> list[dict[str, Any]]:
    rows = _ORIGINAL_BUILD_MANIFEST(queries, targets, indexes)
    for index, row in enumerate(rows, 1):
        row["workload_id"] = f"bts3_w{index:03d}"
    _IMPL.validate_manifest(rows, indexes)
    return rows


def build_attempt_plan(manifest: Sequence[Mapping[str, Any]], manifest_sha256: str) -> list[dict[str, Any]]:
    rows = _ORIGINAL_BUILD_ATTEMPT_PLAN(manifest, manifest_sha256)
    for row in rows:
        row["artifact_root"] = (
            ".paper-artifacts/biological-topk-successor/fresh-holdout/"
            f"{row['validation_instance_id']}_{row['arm'].lower()}"
        )
    return rows


def _manifest_instances(manifest: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in manifest:
        rows.extend([row] * (1 + int(row["technical_repeat_count"])))
    _IMPL.require(len(rows) == 184, "successor manifest resource instance count drift")
    return rows


def _nearest(
    observations: Sequence[Mapping[str, Any]],
    arm: str,
    workload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    candidates = [
        row
        for row in observations
        if row["arm"] == arm and row["target_scale_stratum"] == workload["target_scale_stratum"]
    ]
    query = math.log1p(int(workload["query_sequence_length"]))
    target = math.log1p(int(workload["target_sequence_length"]))
    ordered = sorted(
        candidates,
        key=lambda row: (
            abs(math.log1p(int(row["query_length"])) - query)
            + abs(math.log1p(int(row["target_length"])) - target),
            row["attempt_id"],
        ),
    )
    _IMPL.require(ordered, f"missing successor resource matches: {arm}/{workload['target_scale_stratum']}")
    return ordered[: min(NEAREST_OBSERVATIONS, len(ordered))]


def _nearest_rank(values: Sequence[float | int], probability: float) -> float | int:
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def resource_projection(manifest: Sequence[Mapping[str, Any]], manifest_sha256: str) -> dict[str, Any]:
    _IMPL.require(sha256_file(RESOURCE_MODEL_PATH) == RESOURCE_MODEL_SHA256, "successor Phase 1 resource model drift")
    model = _IMPL.load_json(RESOURCE_MODEL_PATH)
    observations = model["observations"]
    _IMPL.require(len(observations) == 165 and model["scientific_output_fields_read"] is False, "successor resource observations drift")
    instances = _manifest_instances(manifest)
    matches = {
        (index, arm): _nearest(observations, arm, row)
        for index, row in enumerate(instances)
        for arm in ("A", "G")
    }
    overhead = int(_IMPL.load_json(RESOURCE_PLAN_PATH)["projection"]["successor_fixed_overhead_bytes"])
    scheduler_factor = float(
        _IMPL.load_json(RESOURCE_PLAN_PATH)["projection"]["scheduled_elapsed_wall_seconds"]["observed_two_worker_factor"]
    )
    randomizer = random.Random(BOOTSTRAP_SEED)
    storage_samples: list[int] = []
    cpu_samples: list[float] = []
    gpu_samples: list[float] = []
    scheduled_samples: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        storage = overhead
        cpu = 0.0
        gpu = 0.0
        for index in range(len(instances)):
            authority = randomizer.choice(matches[(index, "A")])
            candidate = randomizer.choice(matches[(index, "G")])
            storage += int(authority["artifact_storage_bytes"]) + int(candidate["artifact_storage_bytes"])
            cpu += float(authority["wall_seconds"])
            gpu += float(candidate["wall_seconds"])
        storage_samples.append(storage)
        cpu_samples.append(cpu)
        gpu_samples.append(gpu)
        scheduled_samples.append(scheduler_factor * (cpu + gpu) / 2.0)

    storage_point = int(round(sum(storage_samples) / len(storage_samples)))
    storage_upper = int(_nearest_rank(storage_samples, 0.95))
    cpu_point = sum(cpu_samples) / len(cpu_samples)
    gpu_point = sum(gpu_samples) / len(gpu_samples)
    scheduled_point = sum(scheduled_samples) / len(scheduled_samples)
    cpu_upper = float(_nearest_rank(cpu_samples, 0.95))
    gpu_upper = float(_nearest_rank(gpu_samples, 0.95))
    scheduled_upper = float(_nearest_rank(scheduled_samples, 0.95))
    maximum = {
        arm: max(int(row["artifact_storage_bytes"]) for row in observations if row["arm"] == arm)
        for arm in ("A", "G")
    }
    runtime_stress = 184 * maximum["A"] + 184 * maximum["G"] + overhead
    tracked_phase2 = tracked_successor_bytes_at_phase2()
    fixed_nonruntime = (
        PREDECESSOR_BYTES
        + tracked_phase2
        + SUCCESSOR_TRACKED_RESERVATION_BYTES
        + RAW_G_RESERVATION_BYTES
    )
    total_point = fixed_nonruntime + storage_point
    total_upper = fixed_nonruntime + storage_upper
    total_stress = fixed_nonruntime + runtime_stress
    gate_basis = max(total_upper, total_stress)
    return {
        "schema_version": 1,
        "status": "manifest_specific_projection_frozen",
        "evidence_role": "resource_planning_control",
        "performance_claim": False,
        "manifest_path": MANIFEST_PATH.relative_to(ROOT).as_posix(),
        "manifest_sha256": manifest_sha256,
        "resource_model_path": RESOURCE_MODEL_PATH.relative_to(ROOT).as_posix(),
        "resource_model_sha256": RESOURCE_MODEL_SHA256,
        "model_unchanged_from_phase_1": True,
        "observation_source": model["observation_source"],
        "scientific_output_fields_read": False,
        "matching_method": "seven_nearest_within_arm_and_target_scale_on_log_query_target_lengths",
        "primary_workload_count": 178,
        "technical_repeat_instance_count": 6,
        "projected_validation_instance_count": 184,
        "projected_attempt_count": 368,
        "technical_repeats_included": True,
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "upper_quantile": "0.95",
            "quantile_definition": "ceil(q*B)-th order statistic without interpolation",
        },
        "projection": {
            "projected_cpu_aggregate_wall_seconds_point": format(cpu_point, ".17g"),
            "projected_cpu_aggregate_wall_seconds_upper_95": format(cpu_upper, ".17g"),
            "projected_gpu_aggregate_wall_seconds_point": format(gpu_point, ".17g"),
            "projected_gpu_aggregate_wall_seconds_upper_95": format(gpu_upper, ".17g"),
            "projected_gpu_hours_point": format(gpu_point / 3600.0, ".17g"),
            "projected_gpu_hours_upper_95": format(gpu_upper / 3600.0, ".17g"),
            "projected_scheduled_elapsed_wall_seconds_point": format(scheduled_point, ".17g"),
            "projected_scheduled_elapsed_wall_seconds_upper_95": format(scheduled_upper, ".17g"),
            "successor_runtime_storage_bytes_point": storage_point,
            "successor_runtime_storage_bytes_upper_95": storage_upper,
            "successor_runtime_storage_bytes_max_observed_stress": runtime_stress,
            "predecessor_retained_bytes": PREDECESSOR_BYTES,
            "successor_tracked_bytes_through_phase2": tracked_phase2,
            "successor_phase3_phase4_tracked_reservation_bytes": SUCCESSOR_TRACKED_RESERVATION_BYTES,
            "raw_g_telemetry_reservation_bytes": RAW_G_RESERVATION_BYTES,
            "total_artifact_storage_bytes_point_with_reservations": total_point,
            "total_artifact_storage_bytes_upper_95_with_reservations": total_upper,
            "total_artifact_storage_bytes_max_observed_stress_with_reservations": total_stress,
            "total_artifact_storage_gate_basis_bytes": gate_basis,
            "fixed_total_artifact_storage_bytes": FIXED_TOTAL_STORAGE_BYTES,
            "artifact_storage_margin_bytes": FIXED_TOTAL_STORAGE_BYTES - gate_basis,
        },
    }


def resource_decision(projection: Mapping[str, Any], manifest_sha256: str) -> dict[str, Any]:
    values = projection["projection"]
    elapsed_pass = float(values["projected_scheduled_elapsed_wall_seconds_upper_95"]) <= _IMPL.MAX_ELAPSED_SECONDS
    gpu_pass = float(values["projected_gpu_hours_upper_95"]) <= _IMPL.MAX_GPU_HOURS
    storage_pass = int(values["total_artifact_storage_gate_basis_bytes"]) <= FIXED_TOTAL_STORAGE_BYTES
    return {
        "schema_version": 1,
        "phase": 3,
        "status": "pass" if elapsed_pass and gpu_pass and storage_pass else "blocked_fixed_budget",
        "manifest_sha256": manifest_sha256,
        "resource_projection_path": RESOURCE_PROJECTION_PATH.relative_to(ROOT).as_posix(),
        "resource_projection_sha256": _IMPL.canonical_digest(projection),
        "resource_model_sha256": RESOURCE_MODEL_SHA256,
        "max_formal_scheduled_wall_seconds": _IMPL.MAX_ELAPSED_SECONDS,
        "max_gpu_hours": _IMPL.MAX_GPU_HOURS,
        "fixed_total_artifact_storage_bytes": FIXED_TOTAL_STORAGE_BYTES,
        "includes_predecessor_artifact_bytes": True,
        "includes_successor_tracked_reservation": True,
        "includes_raw_g_telemetry_reservation": True,
        "projected_scheduled_elapsed_wall_seconds_upper_95": values["projected_scheduled_elapsed_wall_seconds_upper_95"],
        "projected_gpu_hours_upper_95": values["projected_gpu_hours_upper_95"],
        "total_artifact_storage_gate_basis_bytes": values["total_artifact_storage_gate_basis_bytes"],
        "scheduled_elapsed_gate_pass": elapsed_pass,
        "gpu_hours_gate_pass": gpu_pass,
        "artifact_storage_gate_pass": storage_pass,
        "fixed_budget_gate_pass": elapsed_pass and gpu_pass and storage_pass,
        "owner_quota_may_be_raised_after_manifest_projection": False,
        "phase_4_execution_authorized": elapsed_pass and gpu_pass and storage_pass,
    }


def build() -> dict[Path, bytes]:
    payloads = _ORIGINAL_BUILD()
    plan = json.loads(payloads[PLAN_PATH].decode("ascii"))
    plan["epoch_id"] = "biological_topk_successor_v2"
    plan["phase_2_parent_commit"] = PHASE2_COMMIT
    plan["exact_analysis_command"] = [
        "python3",
        "reproduce/biological_topk_successor/analyze_phase4.py",
        "--analyze",
        "--artifact-root",
        ".paper-artifacts/biological-topk-successor/fresh-holdout",
    ]
    plan["predecessor_phase4_input_overlap_count"] = 0
    plan["fixed_total_artifact_storage_bytes"] = FIXED_TOTAL_STORAGE_BYTES
    plan["fixed_quota_includes_predecessor_evidence"] = True
    plan["raw_telemetry_policy"] = "validate_then_deterministic_lossless_gzip_before_next_attempt"
    payloads[PLAN_PATH] = _IMPL.canonical_json_bytes(plan)
    return payloads


_configure()
_IMPL.build_manifest = build_manifest
_IMPL.build_attempt_plan = build_attempt_plan
_IMPL.resource_projection = resource_projection
_IMPL.resource_decision = resource_decision
_IMPL.build = build

for _name in _IMPL.__all__:
    globals()[_name] = getattr(_IMPL, _name)
globals().update(
    {
        "build": build,
        "build_manifest": build_manifest,
        "build_attempt_plan": build_attempt_plan,
        "resource_projection": resource_projection,
        "resource_decision": resource_decision,
        "PHASE2_COMMIT": PHASE2_COMMIT,
        "FIXED_TOTAL_STORAGE_BYTES": FIXED_TOTAL_STORAGE_BYTES,
        "RAW_G_RESERVATION_BYTES": RAW_G_RESERVATION_BYTES,
        "SUCCESSOR_TRACKED_RESERVATION_BYTES": SUCCESSOR_TRACKED_RESERVATION_BYTES,
    }
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payloads = build()
        if args.write:
            for path, payload in payloads.items():
                _IMPL.atomic_write(path, payload)
            print(f"wrote {len(payloads)} successor Phase 3 holdout artifacts")
            return 0
        stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
        _IMPL.require(not stale, f"successor Phase 3 holdout artifacts do not reproduce: {stale}")
        print("successor Phase 3 holdout artifacts reproduce byte-for-byte")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, _IMPL.FreezeError) as error:
        print(f"successor Phase 3 freeze failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
