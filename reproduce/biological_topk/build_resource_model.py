#!/usr/bin/env python3
"""Fit and freeze the input-only Phase 1 resource projection model."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
MODEL_PATH = PAPER / "resource_projection_model.json"
RECEIPT_PATH = PAPER / "resource_projection_model_receipt.json"
BUDGET_PATH = PAPER / "fresh_budget_projection_plan.json"
OWNER_QUOTA_PATH = PAPER / "owner_storage_quota_approval.json"
SOURCE_BUILDER_PATH = ROOT / "reproduce/biological_topk/build_source_universe.py"
QUERY_UNIVERSE_PATH = PAPER / "query_source_universe.tsv.gz"
TARGET_UNIVERSE_PATH = PAPER / "target_source_universe.tsv.gz"

BOOTSTRAP_SEED = 20260810
BOOTSTRAP_REPLICATES = 10000
RIDGE_LAMBDA = 0.01
UPPER_QUANTILE = 0.95
SCHEDULER_WORKERS = 2
SCHEDULER_INEFFICIENCY = 1.10
QUOTAS = {"short": 60, "medium": 59, "large": 59}
MAX_FORMAL_SCHEDULED_WALL_SECONDS = 172800
MAX_GPU_HOURS = 72
MAX_ARTIFACT_STORAGE_BYTES = 8589934592

FEATURE_NAMES = (
    "intercept",
    "log1p_query_length",
    "log1p_target_length",
    "log1p_query_times_target",
    "query_complexity_proxy",
    "target_complexity_proxy",
    "stratum_medium",
    "stratum_large",
    "config_paper_direct_v1",
    "config_paper_sharded_v1",
)
RESPONSES = ("cpu_wall_seconds", "gpu_wall_seconds", "artifact_storage_bytes")


def load_source_builder():
    spec = importlib.util.spec_from_file_location("biological_topk_resource_source", SOURCE_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SOURCE_BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii")


def validate_owner_quota() -> dict[str, Any]:
    approval = json.loads(OWNER_QUOTA_PATH.read_text(encoding="ascii"))
    expected = {
        "approved_by": "repository_owner_via_active_codex_thread",
        "approved_on": "2026-07-30",
        "approval_message": "\u6279\u51c6",
        "approval_scope": "max_artifact_storage_bytes_and_phase_1_commit_replacement",
        "max_artifact_storage_bytes": MAX_ARTIFACT_STORAGE_BYTES,
        "quota_unit": "bytes",
        "quota_may_be_raised_after_manifest_projection": False,
        "phase_1_commit_replacement_authorized": True,
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            raise ValueError(f"owner storage approval drift: {key}")
    if approval.get("schema_version") != 1:
        raise ValueError("owner storage approval schema drift")
    return approval


def fasta_sequence(path: Path) -> str:
    return "".join(
        line.strip().upper()
        for line in path.read_text(encoding="ascii").splitlines()
        if line and not line.startswith(">")
    )


def directory_bytes(path: Path) -> int:
    if not path.is_dir():
        raise ValueError(f"missing artifact directory: {path}")
    total = 0
    for child in path.rglob("*"):
        if child.is_symlink():
            raise ValueError(f"resource evidence contains symlink: {child}")
        if child.is_file():
            total += child.stat().st_size
    return total


def complexity(source_builder: Any, sequence: str) -> float:
    return float(source_builder.sampled_distinct_4mer_fraction(sequence))


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_gzip_tsv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def observation(
    *,
    observation_id: str,
    stratum: str,
    configuration: str,
    query_length: int,
    target_length: int,
    query_complexity: float,
    target_complexity: float,
    cpu_wall: float,
    gpu_wall: float,
    storage_bytes: int,
    source_paths: Iterable[Path],
) -> dict[str, Any]:
    if stratum not in QUOTAS or configuration not in {
        "canonical_hybrid_v2",
        "paper_direct_v1",
        "paper_sharded_v1",
    }:
        raise ValueError("invalid resource observation class")
    paths = tuple(source_paths)
    return {
        "observation_id": observation_id,
        "target_scale_stratum": stratum,
        "execution_configuration": configuration,
        "query_length": query_length,
        "target_length": target_length,
        "query_length_times_target_length": query_length * target_length,
        "query_complexity_proxy": format(query_complexity, ".17g"),
        "target_complexity_proxy": format(target_complexity, ".17g"),
        "cpu_wall_seconds": format(cpu_wall, ".17g"),
        "gpu_wall_seconds": format(gpu_wall, ".17g"),
        "artifact_storage_bytes": storage_bytes,
        "source_paths": [path.relative_to(ROOT).as_posix() for path in paths],
        "source_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths if path.is_file()},
    }


def build_observations(source_builder: Any) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    holdout_results_path = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_results.tsv"
    holdout_workloads_path = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_workloads.tsv"
    result_rows = read_tsv(holdout_results_path)
    workload_rows = {row["workload_id"]: row for row in read_tsv(holdout_workloads_path)}
    artifact_root = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout"
    sequence_cache: dict[Path, tuple[int, float]] = {}

    def sequence_metrics(path: Path) -> tuple[int, float]:
        metrics = sequence_cache.get(path)
        if metrics is None:
            sequence = fasta_sequence(path)
            metrics = (len(sequence), complexity(source_builder, sequence))
            sequence_cache[path] = metrics
        return metrics

    for result in result_rows:
        if result["repeat_id"] != "0":
            continue
        workload = workload_rows[result["workload_id"]]
        query_path = ROOT / workload["query_path"]
        target_path = ROOT / workload["target_path"]
        query_length, query_complexity = sequence_metrics(query_path)
        target_length, target_complexity = sequence_metrics(target_path)
        authority_dir = artifact_root / result["authority_attempt_id"]
        hybrid_dir = artifact_root / result["hybrid_attempt_id"]
        observations.append(
            observation(
                observation_id=f"short_{result['workload_id']}",
                stratum="short",
                configuration="canonical_hybrid_v2",
                query_length=query_length,
                target_length=target_length,
                query_complexity=query_complexity,
                target_complexity=target_complexity,
                cpu_wall=float(result["authority_wall_seconds"]),
                gpu_wall=float(result["hybrid_wall_seconds"]),
                storage_bytes=directory_bytes(authority_dir) + directory_bytes(hybrid_dir),
                source_paths=(
                    holdout_results_path,
                    holdout_workloads_path,
                    authority_dir / "attempt-complete.json",
                    hybrid_dir / "attempt-complete.json",
                    query_path,
                    target_path,
                ),
            )
        )

    generalization_pairs_path = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization/phase3-pairs.tsv"
    for pair in read_tsv(generalization_pairs_path):
        if pair["pair_id"] != "1":
            continue
        workload_id = pair["workload_id"]
        base = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization"
        authority_dir = base / f"{workload_id}__pair01__baseline__0"
        candidate_dir = base / f"{workload_id}__pair01__candidate__0"
        query_path = authority_dir / "inputs/query.fa"
        target_path = authority_dir / "inputs/target.fa"
        query_length, query_complexity = sequence_metrics(query_path)
        target_length, target_complexity = sequence_metrics(target_path)
        observations.append(
            observation(
                observation_id=f"medium_{workload_id}",
                stratum="medium",
                configuration="paper_direct_v1",
                query_length=query_length,
                target_length=target_length,
                query_complexity=query_complexity,
                target_complexity=target_complexity,
                cpu_wall=float(pair["baseline_wall_seconds"]),
                gpu_wall=float(pair["candidate_wall_seconds"]),
                storage_bytes=directory_bytes(authority_dir) + directory_bytes(candidate_dir),
                source_paths=(
                    generalization_pairs_path,
                    authority_dir / "run-complete.json",
                    candidate_dir / "run-complete.json",
                    query_path,
                    target_path,
                ),
            )
        )

    pair_summary = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core/pairs-v3/c1_h19_chr21_chr22_fast_topk__pair01__0/pair-summary.json"
    if not pair_summary.is_file():
        pair_summary = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core/c1_h19_chr21_chr22_fast_topk__pair01__0/pair-summary.json"
    summary = json.loads(pair_summary.read_text(encoding="utf-8"))
    large_root = ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core"
    authority_dir = large_root / "c1_h19_chr21_chr22_fast_topk__pair01__baseline__0"
    candidate_dir = large_root / "c1_h19_chr21_chr22_fast_topk__pair01__candidate__0"
    query_path = authority_dir / "inputs/query.fa"
    query_length, query_complexity = sequence_metrics(query_path)
    target_paths = sorted((authority_dir / "output/shards").glob("*.fa"))
    if len(target_paths) != 2:
        raise ValueError("large resource observation requires two chromosome shards")
    target_sequences = [fasta_sequence(path) for path in target_paths]
    target_sequence = "".join(target_sequences)
    observations.append(
        observation(
            observation_id="large_c1_h19_chr21_chr22",
            stratum="large",
            configuration="paper_sharded_v1",
            query_length=query_length,
            target_length=len(target_sequence),
            query_complexity=query_complexity,
            target_complexity=complexity(source_builder, target_sequence),
            cpu_wall=float(summary["baseline_wall_seconds"]),
            gpu_wall=float(summary["candidate_wall_seconds"]),
            storage_bytes=directory_bytes(authority_dir) + directory_bytes(candidate_dir),
            source_paths=(pair_summary, authority_dir / "run-complete.json", candidate_dir / "run-complete.json", query_path, *target_paths),
        )
    )
    expected = Counter({"short": 48, "medium": 13, "large": 1})
    actual = Counter(row["target_scale_stratum"] for row in observations)
    if actual != expected:
        raise ValueError(f"resource observation strata drift: {actual}")
    return observations


def feature_vector(row: dict[str, Any]) -> np.ndarray:
    query_length = float(row["query_length"])
    target_length = float(row["target_length"])
    stratum = row["target_scale_stratum"]
    configuration = row["execution_configuration"]
    return np.asarray(
        [
            1.0,
            math.log1p(query_length),
            math.log1p(target_length),
            math.log1p(query_length * target_length),
            float(row["query_complexity_proxy"]),
            float(row["target_complexity_proxy"]),
            float(stratum == "medium"),
            float(stratum == "large"),
            float(configuration == "paper_direct_v1"),
            float(configuration == "paper_sharded_v1"),
        ],
        dtype=np.float64,
    )


def fit_coefficients(rows: list[dict[str, Any]], response: str) -> np.ndarray:
    matrix = np.vstack([feature_vector(row) for row in rows])
    values = np.log1p(np.asarray([float(row[response]) for row in rows], dtype=np.float64))
    penalty = np.eye(matrix.shape[1], dtype=np.float64) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    return np.linalg.solve(matrix.T @ matrix + penalty, matrix.T @ values)


def predict(coefficients: np.ndarray, row: dict[str, Any]) -> float:
    return max(0.0, math.expm1(float(feature_vector(row) @ coefficients)))


def residuals_by_stratum(
    rows: list[dict[str, Any]], coefficients: np.ndarray, response: str
) -> dict[str, list[float]]:
    result: dict[str, list[float]] = {stratum: [] for stratum in QUOTAS}
    for row in rows:
        residual = math.log1p(float(row[response])) - math.log1p(predict(coefficients, row))
        result[row["target_scale_stratum"]].append(residual)
    return result


def nearest_rank(values: Iterable[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(quantile * len(ordered)) - 1]


def projection_scenarios() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, tuple[float, float]]]]:
    queries = [row for row in read_gzip_tsv(QUERY_UNIVERSE_PATH) if row["historical_exclusion_status"] == "fresh_eligible"]
    targets = [row for row in read_gzip_tsv(TARGET_UNIVERSE_PATH) if row["historical_exclusion_status"] == "fresh_eligible"]
    query_lengths = sorted(int(row["sequence_length"]) for row in queries)
    query_complexities = sorted(float(row["sampled_distinct_4mer_fraction"]) for row in queries)
    query_point_length = query_lengths[len(query_lengths) // 2]
    query_point_complexity = query_complexities[len(query_complexities) // 2]
    query_bounds = (min(query_complexities), max(query_complexities))
    point: dict[str, dict[str, Any]] = {}
    bounds: dict[str, dict[str, tuple[float, float]]] = {}
    for stratum in QUOTAS:
        stratum_targets = [row for row in targets if row["target_scale_stratum"] == stratum]
        target_complexities = sorted(float(row["sampled_distinct_4mer_fraction"]) for row in stratum_targets)
        target_lengths = {int(row["sequence_length"]) for row in stratum_targets}
        if len(target_lengths) != 1:
            raise ValueError(f"target length drift in {stratum}")
        target_length = next(iter(target_lengths))
        point[stratum] = {
            "target_scale_stratum": stratum,
            "execution_configuration": "canonical_hybrid_v2",
            "query_length": query_point_length,
            "target_length": target_length,
            "query_complexity_proxy": query_point_complexity,
            "target_complexity_proxy": target_complexities[len(target_complexities) // 2],
        }
        bounds[stratum] = {
            "query_complexity_proxy": query_bounds,
            "target_complexity_proxy": (min(target_complexities), max(target_complexities)),
            "query_length": (float(min(query_lengths)), float(max(query_lengths))),
            "target_length": (float(target_length), float(target_length)),
        }
    return point, bounds


def maximum_prediction_scenario(
    coefficients: np.ndarray,
    stratum: str,
    bounds: dict[str, dict[str, tuple[float, float]]],
) -> dict[str, Any]:
    values = bounds[stratum]
    query_complexity = values["query_complexity_proxy"][1 if coefficients[4] >= 0 else 0]
    target_complexity = values["target_complexity_proxy"][1 if coefficients[5] >= 0 else 0]
    return {
        "target_scale_stratum": stratum,
        "execution_configuration": "canonical_hybrid_v2",
        "query_length": int(values["query_length"][1]),
        "target_length": int(values["target_length"][1]),
        "query_complexity_proxy": query_complexity,
        "target_complexity_proxy": target_complexity,
    }


def stratified_bootstrap(rows: list[dict[str, Any]], rng: np.random.Generator) -> list[dict[str, Any]]:
    sampled: list[dict[str, Any]] = []
    for stratum in ("short", "medium", "large"):
        candidates = [row for row in rows if row["target_scale_stratum"] == stratum]
        indexes = rng.integers(0, len(candidates), size=len(candidates))
        sampled.extend(candidates[int(index)] for index in indexes)
    return sampled


def build() -> dict[Path, bytes]:
    owner_approval = validate_owner_quota()
    source_builder = load_source_builder()
    observations = build_observations(source_builder)
    point_scenarios, scenario_bounds = projection_scenarios()
    point_coefficients = {
        response: fit_coefficients(observations, response) for response in RESPONSES
    }
    point_projection = {
        response: sum(
            QUOTAS[stratum] * predict(point_coefficients[response], point_scenarios[stratum])
            for stratum in QUOTAS
        )
        for response in RESPONSES
    }

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    bootstrap_aggregates = {response: [] for response in RESPONSES}
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = stratified_bootstrap(observations, rng)
        for response in RESPONSES:
            coefficients = fit_coefficients(sampled, response)
            residuals = residuals_by_stratum(sampled, coefficients, response)
            aggregate = 0.0
            for stratum, quota in QUOTAS.items():
                scenario = maximum_prediction_scenario(coefficients, stratum, scenario_bounds)
                base_log = math.log1p(predict(coefficients, scenario))
                positive_residual = max(0.0, nearest_rank(residuals[stratum], 0.95))
                aggregate += quota * math.expm1(base_log + positive_residual)
            bootstrap_aggregates[response].append(aggregate)

    upper = {
        response: nearest_rank(values, UPPER_QUANTILE)
        for response, values in bootstrap_aggregates.items()
    }
    scheduled_point = (
        point_projection["cpu_wall_seconds"] + point_projection["gpu_wall_seconds"]
    ) / SCHEDULER_WORKERS * SCHEDULER_INEFFICIENCY
    scheduled_upper_samples = [
        (cpu + gpu) / SCHEDULER_WORKERS * SCHEDULER_INEFFICIENCY
        for cpu, gpu in zip(
            bootstrap_aggregates["cpu_wall_seconds"],
            bootstrap_aggregates["gpu_wall_seconds"],
        )
    ]
    scheduled_upper = nearest_rank(scheduled_upper_samples, UPPER_QUANTILE)
    gpu_hours_point = point_projection["gpu_wall_seconds"] / 3600
    gpu_hours_upper = upper["gpu_wall_seconds"] / 3600

    model = {
        "schema_version": 1,
        "model_family": "ridge_log_response_with_stratified_workload_bootstrap",
        "input_features": list(FEATURE_NAMES[1:]),
        "responses": list(RESPONSES),
        "feature_transform": "log1p lengths and length product; raw static complexity proxies; one-hot strata/configuration",
        "ridge_lambda": format(RIDGE_LAMBDA, ".17g"),
        "historical_observations": observations,
        "observation_count_by_stratum": dict(sorted(Counter(row["target_scale_stratum"] for row in observations).items())),
        "execution_configurations": sorted({row["execution_configuration"] for row in observations}),
        "fixed_projection_configuration": "canonical_hybrid_v2",
        "point_coefficients": {
            response: {
                feature: format(float(value), ".17g")
                for feature, value in zip(FEATURE_NAMES, point_coefficients[response])
            }
            for response in RESPONSES
        },
        "bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "replicates": BOOTSTRAP_REPLICATES,
            "level": "workload_stratified_by_target_scale",
            "residual_treatment": "within-bootstrap stratum-specific nonnegative 95th nearest-rank log residual added per projected workload",
            "upper_bound_quantile": format(UPPER_QUANTILE, ".17g"),
            "quantile_definition": "ceil(q*B)-th order statistic without interpolation",
        },
        "scheduler_simulation": {
            "logical_workers": SCHEDULER_WORKERS,
            "worker_assignment": "balanced_static_two_worker_projection",
            "cpu_then_gpu_per_workload": True,
            "inefficiency_factor": format(SCHEDULER_INEFFICIENCY, ".17g"),
            "formula": "(aggregate_cpu_seconds+aggregate_gpu_seconds)/2*1.10",
        },
        "projection_input_scenarios": point_scenarios,
        "projection_input_bounds": scenario_bounds,
        "stratum_quotas": QUOTAS,
        "projection": {
            "projected_cpu_aggregate_wall_seconds_point": format(point_projection["cpu_wall_seconds"], ".17g"),
            "projected_cpu_aggregate_wall_seconds_upper_95": format(upper["cpu_wall_seconds"], ".17g"),
            "projected_gpu_aggregate_wall_seconds_point": format(point_projection["gpu_wall_seconds"], ".17g"),
            "projected_gpu_aggregate_wall_seconds_upper_95": format(upper["gpu_wall_seconds"], ".17g"),
            "projected_gpu_hours_point": format(gpu_hours_point, ".17g"),
            "projected_gpu_hours_upper_95": format(gpu_hours_upper, ".17g"),
            "projected_scheduled_elapsed_wall_seconds_point": format(scheduled_point, ".17g"),
            "projected_scheduled_elapsed_wall_seconds_upper_95": format(scheduled_upper, ".17g"),
            "projected_artifact_storage_bytes_point": str(math.ceil(point_projection["artifact_storage_bytes"])),
            "projected_artifact_storage_bytes_upper_95": str(math.ceil(upper["artifact_storage_bytes"])),
        },
        "limitations": [
            "only one chromosome-scale CPU-authority/GPU-candidate timing observation is available",
            "target-scale and historical execution-configuration effects are partially aliased",
            "Phase 3 must recompute a manifest-specific projection without changing this model",
            "resource projections are planning controls and not performance claims",
        ],
    }
    model_bytes = canonical_json_bytes(model)
    elapsed_pass = scheduled_upper <= MAX_FORMAL_SCHEDULED_WALL_SECONDS
    gpu_pass = gpu_hours_upper <= MAX_GPU_HOURS
    storage_pass = math.ceil(upper["artifact_storage_bytes"]) <= MAX_ARTIFACT_STORAGE_BYTES
    budget = {
        "schema_version": 1,
        "status": "frozen",
        "model_path": MODEL_PATH.relative_to(ROOT).as_posix(),
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "N_panel": sum(QUOTAS.values()),
        "stratum_quotas": QUOTAS,
        "max_formal_scheduled_wall_seconds": MAX_FORMAL_SCHEDULED_WALL_SECONDS,
        "max_gpu_hours": MAX_GPU_HOURS,
        "max_artifact_storage_bytes": MAX_ARTIFACT_STORAGE_BYTES,
        "storage_quota_source": OWNER_QUOTA_PATH.relative_to(ROOT).as_posix(),
        "storage_quota_source_sha256": sha256_file(OWNER_QUOTA_PATH),
        "projected_scheduled_elapsed_wall_seconds_upper_95": model["projection"]["projected_scheduled_elapsed_wall_seconds_upper_95"],
        "projected_gpu_hours_upper_95": model["projection"]["projected_gpu_hours_upper_95"],
        "projected_artifact_storage_bytes_upper_95": model["projection"]["projected_artifact_storage_bytes_upper_95"],
        "scheduled_wall_gate_pass": elapsed_pass,
        "gpu_hours_gate_pass": gpu_pass,
        "artifact_storage_gate_pass": storage_pass,
        "fixed_budget_gate_pass": elapsed_pass and gpu_pass and storage_pass,
        "owner_quota_may_be_raised_after_manifest_projection": False,
        "fresh_pair_selected": False,
        "new_prediction_run": False,
    }
    input_paths = (
        ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_results.tsv",
        ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_workloads.tsv",
        ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization/phase3-pairs.tsv",
        QUERY_UNIVERSE_PATH,
        TARGET_UNIVERSE_PATH,
        OWNER_QUOTA_PATH,
    )
    receipt = {
        "schema_version": 1,
        "model_path": MODEL_PATH.relative_to(ROOT).as_posix(),
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "model_size_bytes": len(model_bytes),
        "builder_path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "source_builder_path": SOURCE_BUILDER_PATH.relative_to(ROOT).as_posix(),
        "source_builder_sha256": sha256_file(SOURCE_BUILDER_PATH),
        "input_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in input_paths},
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "owner_storage_quota": {
            "approval_path": OWNER_QUOTA_PATH.relative_to(ROOT).as_posix(),
            "approval_sha256": sha256_file(OWNER_QUOTA_PATH),
            "max_artifact_storage_bytes": owner_approval["max_artifact_storage_bytes"],
        },
        "fresh_pair_selected": False,
        "new_prediction_run": False,
    }
    return {
        MODEL_PATH: model_bytes,
        RECEIPT_PATH: canonical_json_bytes(receipt),
        BUDGET_PATH: canonical_json_bytes(budget),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    if args.check:
        mismatches = [path for path, payload in outputs.items() if not path.is_file() or path.read_bytes() != payload]
        if mismatches:
            for path in mismatches:
                print(f"resource model artifact drift: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("biological Top-K resource artifacts reproduce byte-for-byte")
        return 0
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(outputs)} Phase 1 resource artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
