#!/usr/bin/env python3
"""Freeze successor Phase 1 bindings, source universe, and corrected budgets."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
V1_PAPER = ROOT / "paper/biological_topk"
REPAIR_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout-repair1"
FIXED_TOTAL_STORAGE_BYTES = 64 * 1024**3
RAW_G_RESERVATION_BYTES = 1536 * 1024**2
MAX_SCHEDULED_WALL_SECONDS = 48 * 3600
MAX_GPU_HOURS = 72
BOOTSTRAP_SEED = 20260817
BOOTSTRAP_REPLICATES = 10_000
UPPER_QUANTILE = 0.95
PANEL_QUOTAS = {"short": 60, "medium": 59, "large": 59}
TECHNICAL_REPEATS = 6
PLANNED_ATTEMPTS_PER_ARM = sum(PANEL_QUOTAS.values()) + TECHNICAL_REPEATS
PREDECESSOR_BYTES = 7_142_325_727

OUTPUT_PATHS = (
    PAPER / "contract_binding.json",
    PAPER / "successor_exclusion_registry.tsv",
    PAPER / "query_source_universe.tsv.gz",
    PAPER / "target_source_universe.tsv.gz",
    PAPER / "source_universe_receipt.json",
    PAPER / "information_feasibility.json",
    PAPER / "resource_projection_model.json",
    PAPER / "resource_projection.json",
    PAPER / "resource_decision.json",
)

CONTRACT_BINDING_PATHS = (
    "docs/biological_topk/scientific_object.md",
    "docs/biological_topk/legacy_clustering_semantics.md",
    "docs/biological_topk/coordinate_mapping.md",
    "docs/biological_topk/canonicalization_spec.md",
    "docs/biological_topk/ranking_semantics.md",
    "docs/biological_topk/matching_spec.md",
    "docs/biological_topk/statistical_analysis_plan.md",
    "docs/biological_topk/source_universe_spec.md",
    "docs/biological_topk/experimental_estimand_spec.md",
    "paper/biological_topk/contract_spec.json",
    "paper/biological_topk/concordance_power_plan.json",
    "paper/biological_topk/sample_size_plan.json",
    "paper/biological_topk/joint_information_model.json",
    "paper/biological_topk/joint_information_simulation.json",
    "paper/biological_topk/experimental_power_simulation_plan.json",
    "paper/biological_topk/operating_envelope.json",
    "paper/biological_topk/legacy_clustering_fixtures.tsv",
    "paper/biological_topk/coordinate_golden_fixtures.tsv",
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/biological_topk/match_candidate_sites.py",
    "reproduce/biological_topk/compare_candidate_topk.py",
    "reproduce/biological_topk/exact_binomial_bounds.py",
    "reproduce/biological_topk/rank_diagnostics.py",
)


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


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    require(fields and all(None not in row for row in rows), f"malformed TSV: {path}")
    return fields, rows


def read_gzip_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    require(fields and all(None not in row for row in rows), f"malformed gzip TSV: {path}")
    return fields, rows


def tsv_bytes(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def gzip_bytes(payload: bytes) -> bytes:
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=stream, mtime=0) as handle:
        handle.write(payload)
    return stream.getvalue()


def directory_file_bytes(path: Path) -> int:
    require(path.is_dir() and not path.is_symlink(), f"missing or unsafe directory: {path}")
    total = 0
    for child in path.rglob("*"):
        require(not child.is_symlink(), f"resource evidence contains symlink: {child}")
        if child.is_file():
            total += child.stat().st_size
    return total


def build_contract_binding() -> dict[str, Any]:
    sample = read_json(V1_PAPER / "sample_size_plan.json")
    contract = read_json(V1_PAPER / "contract_spec.json")
    require(contract["contract_name"] == "biological_topk_candidate_site_v1", "contract name drift")
    require(sample["N_panel"] == 178 and sample["n_binary_required"] == 124, "sample-size binding drift")
    return {
        "schema_version": 1,
        "status": "exact_predecessor_contract_reused",
        "contract_name": "biological_topk_candidate_site_v1",
        "scientific_contract_changed": False,
        "comparator_changed": False,
        "threshold_changed": False,
        "rank_order_claim": "diagnostic_only",
        "score_representation": "integral_exact",
        "N_panel": 178,
        "n_binary_required": 124,
        "k_min": 122,
        "allowed_failures": 2,
        "bindings": {
            relative: sha256_file(ROOT / relative) for relative in CONTRACT_BINDING_PATHS
        },
    }


def predecessor_manifest_rows() -> list[dict[str, str]]:
    _, rows = read_tsv(V1_PAPER / "fresh_holdout_manifest.tsv")
    require(len(rows) == 178, "predecessor manifest count drift")
    require(len({row["query_sequence_sha256"] for row in rows}) == 178, "predecessor query digest uniqueness drift")
    require(len({row["target_sequence_sha256"] for row in rows}) == 178, "predecessor target digest uniqueness drift")
    return rows


def build_exclusion_registry(manifest: Sequence[Mapping[str, str]]) -> tuple[bytes, dict[str, Any]]:
    fields, old_rows = read_tsv(V1_PAPER / "fresh_input_exclusion_registry.tsv")
    new_rows: list[dict[str, str]] = []
    for row in manifest:
        new_rows.append(
            {
                "record_type": "pair",
                "query_ordinal_namespace": row["query_ordinal_namespace"],
                "query_source_ordinal": row["query_source_ordinal"],
                "target_ordinal_namespace": row["target_ordinal_namespace"],
                "target_source_ordinal": row["target_source_ordinal"],
                "query_id": row["query_transcript_id"],
                "target_id": row["target_anchor_transcript_id"],
                "query_sha256": row["query_sequence_sha256"],
                "target_sha256": row["target_sequence_sha256"],
                "query_region": f"{row['query_extracted_start0']}:{row['query_extracted_end0']}",
                "target_region": f"{row['target_region_start0']}:{row['target_region_end0']}",
                "assembly": row["assembly"],
                "coordinate_namespace": row["target_coordinate_namespace"],
                "pair_digest": row["input_pair_digest"],
                "source_receipt_path": "paper/biological_topk/fresh_holdout_manifest.tsv",
                "exclusion_reason": "predecessor_phase4_fresh_concordance_input",
            }
        )
    old_pair_digests = {row["pair_digest"] for row in old_rows if row["pair_digest"] != "NA"}
    require(not old_pair_digests & {row["pair_digest"] for row in new_rows}, "predecessor manifest already in old exclusion registry")
    payload = tsv_bytes(fields, [*old_rows, *new_rows])
    return payload, {
        "base_exclusion_count": len(old_rows),
        "predecessor_phase4_added_count": len(new_rows),
        "total_exclusion_count": len(old_rows) + len(new_rows),
        "base_registry_sha256": sha256_file(V1_PAPER / "fresh_input_exclusion_registry.tsv"),
        "predecessor_manifest_sha256": sha256_file(V1_PAPER / "fresh_holdout_manifest.tsv"),
    }


def predecessor_identity_sets(manifest: Sequence[Mapping[str, str]]) -> dict[str, set[Any]]:
    return {
        "query_digests": {row["query_sequence_sha256"] for row in manifest},
        "query_ordinals": {(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in manifest},
        "target_digests": {row["target_sequence_sha256"] for row in manifest},
        "target_ordinals": {(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in manifest},
    }


def mark_query_universe(manifest: Sequence[Mapping[str, str]]) -> tuple[bytes, dict[str, Any]]:
    fields, rows = read_gzip_tsv(V1_PAPER / "query_source_universe.tsv.gz")
    identities = predecessor_identity_sets(manifest)
    excluded = 0
    for row in rows:
        selected = (
            row["sequence_sha256"] in identities["query_digests"]
            or (row["query_ordinal_namespace"], row["source_ordinal"]) in identities["query_ordinals"]
        )
        if selected:
            reasons = set() if row["historical_exclusion_reasons"] == "NA" else set(row["historical_exclusion_reasons"].split(";"))
            reasons.add("predecessor_phase4_fresh_concordance_input")
            row["historical_exclusion_status"] = "successor_excluded"
            row["historical_exclusion_reasons"] = ";".join(sorted(reasons))
            excluded += 1
    payload = tsv_bytes(fields, rows)
    eligible = [row for row in rows if row["operating_envelope_eligible"] == "1" and row["historical_exclusion_status"] == "fresh_eligible"]
    return payload, {
        "row_count": len(rows),
        "predecessor_identity_excluded_row_count": excluded,
        "fresh_eligible_row_count": len(eligible),
        "fresh_unique_namespaced_ordinal_count": len({(row["query_ordinal_namespace"], row["source_ordinal"]) for row in eligible}),
        "fresh_unique_sequence_digest_count": len({row["sequence_sha256"] for row in eligible}),
    }


def mark_target_universe(manifest: Sequence[Mapping[str, str]]) -> tuple[bytes, dict[str, Any]]:
    fields, rows = read_gzip_tsv(V1_PAPER / "target_source_universe.tsv.gz")
    identities = predecessor_identity_sets(manifest)
    excluded = 0
    for row in rows:
        selected = (
            row["sequence_sha256"] in identities["target_digests"]
            or (row["target_ordinal_namespace"], row["source_ordinal"]) in identities["target_ordinals"]
        )
        if selected:
            reasons = set() if row["historical_exclusion_reasons"] == "NA" else set(row["historical_exclusion_reasons"].split(";"))
            reasons.add("predecessor_phase4_fresh_concordance_input")
            row["historical_exclusion_status"] = "successor_excluded"
            row["historical_exclusion_reasons"] = ";".join(sorted(reasons))
            excluded += 1
    payload = tsv_bytes(fields, rows)
    strata: dict[str, Any] = {}
    for stratum in PANEL_QUOTAS:
        selected = [
            row for row in rows
            if row["target_scale_stratum"] == stratum
            and row["operating_envelope_eligible"] == "1"
            and row["historical_exclusion_status"] == "fresh_eligible"
        ]
        strata[stratum] = {
            "fresh_eligible_row_count": len(selected),
            "fresh_unique_namespaced_ordinal_count": len({(row["target_ordinal_namespace"], row["source_ordinal"]) for row in selected}),
            "fresh_unique_sequence_digest_count": len({row["sequence_sha256"] for row in selected}),
            "required": PANEL_QUOTAS[stratum],
        }
    return payload, {
        "row_count": len(rows),
        "predecessor_identity_excluded_row_count": excluded,
        "strata": strata,
    }


def quantile_nearest_rank(values: Sequence[float | int], probability: float) -> float | int:
    require(values, "cannot take quantile of empty values")
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def attempt_observations(manifest: Sequence[Mapping[str, str]]) -> tuple[list[dict[str, Any]], int]:
    by_workload = {row["workload_id"]: row for row in manifest}
    observations: list[dict[str, Any]] = []
    attempt_bytes = 0
    for receipt_path in sorted(REPAIR_ROOT.glob("r1_*/attempt-complete.json")):
        receipt = read_json(receipt_path)
        require(receipt["status"] == "success", f"non-success predecessor repair attempt: {receipt_path}")
        workload = by_workload[receipt["workload_id"]]
        artifact_bytes = directory_file_bytes(receipt_path.parent)
        attempt_bytes += artifact_bytes
        observations.append(
            {
                "attempt_id": receipt["attempt_id"],
                "arm": receipt["arm"],
                "target_scale_stratum": workload["target_scale_stratum"],
                "query_length": int(workload["query_sequence_length"]),
                "target_length": int(workload["target_sequence_length"]),
                "wall_seconds": format(float(receipt["wall_seconds"]), ".17g"),
                "artifact_storage_bytes": artifact_bytes,
            }
        )
    require(len(observations) == 165, "predecessor repair observation count drift")
    require(Counter(row["arm"] for row in observations) == {"A": 83, "G": 82}, "predecessor repair arm count drift")
    overhead = directory_file_bytes(REPAIR_ROOT) - attempt_bytes
    require(overhead > 0, "successor resource overhead is not positive")
    return observations, overhead


def bootstrap_projection(observations: Sequence[Mapping[str, Any]], overhead: int) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    by_arm: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        grouped[(str(row["arm"]), str(row["target_scale_stratum"]))].append(row)
        by_arm[str(row["arm"])].append(row)
    for arm in ("A", "G"):
        for stratum in PANEL_QUOTAS:
            require(grouped[(arm, stratum)], f"missing resource observations: {arm}/{stratum}")

    randomizer = random.Random(BOOTSTRAP_SEED)
    storage_totals: list[int] = []
    cpu_totals: list[float] = []
    gpu_totals: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        arm_storage = {"A": 0, "G": 0}
        arm_wall = {"A": 0.0, "G": 0.0}
        for arm in ("A", "G"):
            for stratum, count in PANEL_QUOTAS.items():
                population = grouped[(arm, stratum)]
                for _ in range(count):
                    item = randomizer.choice(population)
                    arm_storage[arm] += int(item["artifact_storage_bytes"])
                    arm_wall[arm] += float(item["wall_seconds"])
            for _ in range(TECHNICAL_REPEATS):
                item = randomizer.choice(by_arm[arm])
                arm_storage[arm] += int(item["artifact_storage_bytes"])
                arm_wall[arm] += float(item["wall_seconds"])
        storage_totals.append(arm_storage["A"] + arm_storage["G"] + overhead)
        cpu_totals.append(arm_wall["A"])
        gpu_totals.append(arm_wall["G"])

    storage_point = int(round(sum(storage_totals) / len(storage_totals)))
    storage_upper = int(quantile_nearest_rank(storage_totals, UPPER_QUANTILE))
    cpu_point = sum(cpu_totals) / len(cpu_totals)
    cpu_upper = float(quantile_nearest_rank(cpu_totals, UPPER_QUANTILE))
    gpu_point = sum(gpu_totals) / len(gpu_totals)
    gpu_upper = float(quantile_nearest_rank(gpu_totals, UPPER_QUANTILE))
    actual = read_json(V1_PAPER / "fresh_holdout_actual_resources.json")
    observed_total_wall = float(actual["actual_cpu_aggregate_wall_seconds"]) + float(actual["actual_gpu_aggregate_wall_seconds"])
    scheduler_factor = float(actual["actual_scheduled_elapsed_wall_seconds"]) / (observed_total_wall / 2.0)
    scheduled_point = scheduler_factor * (cpu_point + gpu_point) / 2.0
    scheduled_upper = scheduler_factor * (cpu_upper + gpu_upper) / 2.0

    maximum = {
        arm: max(int(row["artifact_storage_bytes"]) for row in by_arm[arm])
        for arm in ("A", "G")
    }
    stress_successor = (
        PLANNED_ATTEMPTS_PER_ARM * maximum["A"]
        + PLANNED_ATTEMPTS_PER_ARM * maximum["G"]
        + overhead
    )
    total_point = PREDECESSOR_BYTES + storage_point + RAW_G_RESERVATION_BYTES
    total_upper = PREDECESSOR_BYTES + storage_upper + RAW_G_RESERVATION_BYTES
    total_stress = PREDECESSOR_BYTES + stress_successor + RAW_G_RESERVATION_BYTES
    gate_basis = max(total_upper, total_stress)
    return {
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "level": "arm_and_target_scale_stratum",
            "upper_quantile": format(UPPER_QUANTILE, ".17g"),
            "quantile_definition": "ceil(q*B)-th order statistic without interpolation",
        },
        "planned_primary_workloads": sum(PANEL_QUOTAS.values()),
        "planned_validation_instances": PLANNED_ATTEMPTS_PER_ARM,
        "planned_attempts_per_arm": PLANNED_ATTEMPTS_PER_ARM,
        "technical_repeats": TECHNICAL_REPEATS,
        "successor_fixed_overhead_bytes": overhead,
        "artifact_storage_bytes": {
            "successor_point": storage_point,
            "successor_upper_95": storage_upper,
            "successor_max_observed_per_arm_stress": stress_successor,
            "predecessor_retained": PREDECESSOR_BYTES,
            "raw_g_reservation": RAW_G_RESERVATION_BYTES,
            "total_point_with_reservation": total_point,
            "total_upper_95_with_reservation": total_upper,
            "total_max_observed_stress_with_reservation": total_stress,
            "gate_basis": gate_basis,
            "quota": FIXED_TOTAL_STORAGE_BYTES,
            "margin": FIXED_TOTAL_STORAGE_BYTES - gate_basis,
            "gate_pass": gate_basis <= FIXED_TOTAL_STORAGE_BYTES,
        },
        "cpu_aggregate_wall_seconds": {
            "point": format(cpu_point, ".17g"),
            "upper_95": format(cpu_upper, ".17g"),
        },
        "gpu_aggregate_wall_seconds": {
            "point": format(gpu_point, ".17g"),
            "upper_95": format(gpu_upper, ".17g"),
        },
        "gpu_hours": {
            "point": format(gpu_point / 3600.0, ".17g"),
            "upper_95": format(gpu_upper / 3600.0, ".17g"),
            "limit": MAX_GPU_HOURS,
            "gate_pass": gpu_upper / 3600.0 <= MAX_GPU_HOURS,
        },
        "scheduled_elapsed_wall_seconds": {
            "observed_two_worker_factor": format(scheduler_factor, ".17g"),
            "point": format(scheduled_point, ".17g"),
            "upper_95": format(scheduled_upper, ".17g"),
            "limit": MAX_SCHEDULED_WALL_SECONDS,
            "gate_pass": scheduled_upper <= MAX_SCHEDULED_WALL_SECONDS,
        },
        "max_observed_attempt_storage_bytes": maximum,
    }


def build_payloads() -> dict[Path, bytes]:
    manifest = predecessor_manifest_rows()
    exclusion_bytes, exclusion_summary = build_exclusion_registry(manifest)
    query_tsv, query_summary = mark_query_universe(manifest)
    target_tsv, target_summary = mark_target_universe(manifest)
    query_gzip = gzip_bytes(query_tsv)
    target_gzip = gzip_bytes(target_tsv)
    contract_binding = build_contract_binding()

    source_receipt = {
        "schema_version": 1,
        "status": "successor_source_universe_frozen",
        "annotation_release": "GENCODE v49",
        "assembly": "GRCh38",
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "predecessor_overlap_allowed": False,
        "exclusion_registry": {
            **exclusion_summary,
            "path": "paper/biological_topk_successor/successor_exclusion_registry.tsv",
            "sha256": sha256_bytes(exclusion_bytes),
        },
        "query_universe": {
            **query_summary,
            "path": "paper/biological_topk_successor/query_source_universe.tsv.gz",
            "uncompressed_tsv_sha256": sha256_bytes(query_tsv),
            "gzip_sha256": sha256_bytes(query_gzip),
        },
        "target_universe": {
            **target_summary,
            "path": "paper/biological_topk_successor/target_source_universe.tsv.gz",
            "uncompressed_tsv_sha256": sha256_bytes(target_tsv),
            "gzip_sha256": sha256_bytes(target_gzip),
        },
    }

    sample = read_json(V1_PAPER / "sample_size_plan.json")
    query_gate = (
        query_summary["fresh_unique_namespaced_ordinal_count"] >= sample["N_panel"]
        and query_summary["fresh_unique_sequence_digest_count"] >= sample["N_panel"]
    )
    target_gates = {
        stratum: (
            target_summary["strata"][stratum]["fresh_unique_namespaced_ordinal_count"] >= count
            and target_summary["strata"][stratum]["fresh_unique_sequence_digest_count"] >= count
        )
        for stratum, count in PANEL_QUOTAS.items()
    }
    information = {
        "schema_version": 1,
        "status": "pass" if query_gate and all(target_gates.values()) else "blocked_insufficient_source_universe",
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "contract_binding_sha256": sha256_bytes(canonical_json_bytes(contract_binding)),
        "source_universe_receipt_sha256": sha256_bytes(canonical_json_bytes(source_receipt)),
        "candidate_N_panel": sample["N_panel"],
        "n_binary_required": sample["n_binary_required"],
        "k_min": sample["k_min"],
        "allowed_failures": sample["allowed_failures"],
        "joint_information_probability_point": sample["joint_information_probability_point"],
        "joint_information_probability_lcb": sample["joint_information_probability_lcb"],
        "joint_inner_mc_precision_pass": sample["joint_inner_mc_precision_pass"],
        "source_capacity": {
            "query_gate_pass": query_gate,
            "target_gate_pass_by_stratum": target_gates,
            "query": query_summary,
            "target": target_summary,
        },
        "predecessor_overlap_count": 0,
        "all_information_gates_pass": query_gate and all(target_gates.values()) and sample["phase_1_status_recommendation"] == "pass",
    }

    observations, overhead = attempt_observations(manifest)
    projection = bootstrap_projection(observations, overhead)
    model = {
        "schema_version": 1,
        "status": "corrected_from_predecessor_observed_execution",
        "resource_values_are_performance_claims": False,
        "scientific_output_fields_read": False,
        "observation_source": "terminal_attempt_receipts_and_directory_file_bytes_only",
        "predecessor_actual_resources_sha256": sha256_file(V1_PAPER / "fresh_holdout_actual_resources.json"),
        "predecessor_manifest_sha256": sha256_file(V1_PAPER / "fresh_holdout_manifest.tsv"),
        "predecessor_run_summary_sha256": sha256_file(REPAIR_ROOT / "run-summary.json"),
        "observations": observations,
        "observation_counts": dict(sorted(Counter(f"{row['arm']}_{row['target_scale_stratum']}" for row in observations).items())),
        "projection_method": projection["bootstrap"],
    }
    model_bytes = canonical_json_bytes(model)
    projection_payload = {
        "schema_version": 1,
        "status": "pass" if (
            projection["artifact_storage_bytes"]["gate_pass"]
            and projection["gpu_hours"]["gate_pass"]
            and projection["scheduled_elapsed_wall_seconds"]["gate_pass"]
        ) else "blocked_fixed_budget",
        "resource_projection_model_sha256": sha256_bytes(model_bytes),
        "fixed_total_artifact_storage_bytes": FIXED_TOTAL_STORAGE_BYTES,
        "includes_predecessor_artifact_bytes": True,
        "quota_may_be_raised_after_phase3_projection": False,
        "projection": projection,
    }
    projection_bytes = canonical_json_bytes(projection_payload)
    decision = {
        "schema_version": 1,
        "decision": projection_payload["status"],
        "phase": 1,
        "new_prediction_run": False,
        "fresh_pair_selected": False,
        "fixed_total_artifact_storage_bytes": FIXED_TOTAL_STORAGE_BYTES,
        "resource_projection_sha256": sha256_bytes(projection_bytes),
        "resource_projection_model_sha256": sha256_bytes(model_bytes),
        "artifact_storage_gate_pass": projection["artifact_storage_bytes"]["gate_pass"],
        "gpu_hours_gate_pass": projection["gpu_hours"]["gate_pass"],
        "scheduled_wall_gate_pass": projection["scheduled_elapsed_wall_seconds"]["gate_pass"],
        "all_resource_gates_pass": projection_payload["status"] == "pass",
        "later_phase_authorized_if_state_committed": projection_payload["status"] == "pass" and information["all_information_gates_pass"],
    }

    return {
        PAPER / "contract_binding.json": canonical_json_bytes(contract_binding),
        PAPER / "successor_exclusion_registry.tsv": exclusion_bytes,
        PAPER / "query_source_universe.tsv.gz": query_gzip,
        PAPER / "target_source_universe.tsv.gz": target_gzip,
        PAPER / "source_universe_receipt.json": canonical_json_bytes(source_receipt),
        PAPER / "information_feasibility.json": canonical_json_bytes(information),
        PAPER / "resource_projection_model.json": model_bytes,
        PAPER / "resource_projection.json": projection_bytes,
        PAPER / "resource_decision.json": canonical_json_bytes(decision),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payloads = build_payloads()
    require(set(payloads) == set(OUTPUT_PATHS), "successor Phase 1 output inventory drift")
    if args.write:
        PAPER.mkdir(parents=True, exist_ok=True)
        for path, payload in payloads.items():
            path.write_bytes(payload)
        print(f"wrote {len(payloads)} successor Phase 1 artifacts")
        return 0
    mismatches = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
    require(not mismatches, f"successor Phase 1 artifacts do not reproduce: {mismatches}")
    print("successor Phase 1 artifacts reproduce byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
