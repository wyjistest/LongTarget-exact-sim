#!/usr/bin/env python3
"""Independently verify and freeze exact long-query hybrid checkpoint v1."""

from __future__ import annotations

import argparse
import csv
import filecmp
import hashlib
import io
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs/exact_long_query_hybrid_checkpoint_v1"
DEFAULT_MANIFEST = DOC_DIR / "checkpoint_fixtures.tsv"
EXPECTED_SOURCE_COMMIT = "61da9b6f1b3d998043d512f5703dc95671d2383e"
EXPECTED_FIXTURE_LENGTHS = {
    "linc01501_4006": 4006,
    "pcat19_8181": 8181,
    "al035530_2_12397": 12397,
}
EXPECTED_MODES = ("lite", "tfosorted")
EXPECTED_ARMS = ("baseline", "candidate")
EXPECTED_REPEATS = (1, 2, 3)
EXPECTED_TASKS = 10368
SPEEDUP_GATE = 1.5

RUN_FIELDS = (
    "fixture_id",
    "mode",
    "arm",
    "repeat",
    "wall_seconds",
    "max_rss_kb",
    "output_bytes",
    "output_sha256",
    "output_path",
)
CONSUMER_FIELDS = (
    "task_index",
    "execution_mode",
    "authority_comparison_available",
    "validation_enabled",
    "ok",
    "output_equal",
    "scoreinfo_groups",
    "attempts",
    "gpu_scored_attempts",
    "endpoint_batches",
    "cpu_oracle_attempts",
    "attempt_mismatch_rows",
    "score_mismatches",
    "query_end_mismatches",
    "ref_end_local_mismatches",
    "terminal_mismatches",
    "control_selected_attempts",
    "cpu_control_selected_attempts",
    "consumer_selection_equal",
    "cpu_reference_align_attempts",
    "consumer_attempt_prefix_equal",
    "cpu_continuation_requested",
    "cpu_continuation_active",
    "cpu_continuation_calls",
    "cpu_continuation_failures",
    "replay_attempts",
    "cpu_align_attempts",
    "threshold_groups",
    "best_fallback_groups",
    "last_groups",
    "empty_groups",
    "score_seconds",
    "gpu_kernel_seconds",
    "h2d_seconds",
    "d2h_seconds",
    "cpu_oracle_seconds",
    "select_seconds",
    "traceback_seconds",
    "convert_seconds",
    "total_seconds",
    "missing_rows",
    "extra_rows",
    "first_attempt_mismatch",
    "first_consumer_mismatch",
    "error",
)
CONSUMER_TOTAL_FIELDS = (
    "scoreinfo_groups",
    "attempts",
    "gpu_scored_attempts",
    "endpoint_batches",
    "cpu_oracle_attempts",
    "attempt_mismatch_rows",
    "score_mismatches",
    "query_end_mismatches",
    "ref_end_local_mismatches",
    "terminal_mismatches",
    "control_selected_attempts",
    "cpu_control_selected_attempts",
    "cpu_reference_align_attempts",
    "cpu_continuation_calls",
    "cpu_continuation_failures",
    "replay_attempts",
    "cpu_align_attempts",
    "threshold_groups",
    "best_fallback_groups",
    "last_groups",
    "empty_groups",
    "missing_rows",
    "extra_rows",
)
CONSUMER_TIMING_FIELDS = (
    "score_seconds",
    "gpu_kernel_seconds",
    "h2d_seconds",
    "d2h_seconds",
    "cpu_oracle_seconds",
    "select_seconds",
    "traceback_seconds",
    "convert_seconds",
    "total_seconds",
)
RECEIPT_CONSUMER_FIELDS = (
    "scoreinfo_groups",
    "attempts",
    "gpu_scored_attempts",
    "cpu_oracle_attempts",
    "cpu_reference_align_attempts",
    "control_selected_attempts",
    "cpu_continuation_calls",
    "cpu_continuation_failures",
    "cpu_align_attempts",
    "score_seconds",
    "gpu_kernel_seconds",
    "h2d_seconds",
    "d2h_seconds",
    "select_seconds",
    "traceback_seconds",
    "convert_seconds",
    "total_seconds",
)
FALLBACK_METRICS = (
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks",
    "benchmark.fasim_gasal2_fallbacks",
)
FORWARD_PREFIX = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_"


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def read_tsv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None, f"missing TSV header: {path}")
    require(
        all(None not in row and all(value is not None for value in row.values()) for row in rows),
        f"malformed TSV: {path}",
    )
    return tuple(reader.fieldnames), rows


def parse_key_values(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            continue
        require(key not in result, f"duplicate metric {key}: {path}")
        result[key] = value
    return result


def require_float_equal(actual: object, expected: object, label: str) -> None:
    require(
        math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-9),
        f"{label}: {actual} != {expected}",
    )


def verify_consumer(path: Path, expected_tasks: int = EXPECTED_TASKS) -> dict[str, int | float]:
    fields, rows = read_tsv(path)
    require(fields == CONSUMER_FIELDS, f"consumer schema mismatch: {path}")
    require(len(rows) == expected_tasks, f"consumer task count mismatch: {path}")
    totals: dict[str, int | float] = {key: 0 for key in CONSUMER_TOTAL_FIELDS}
    totals.update({key: 0.0 for key in CONSUMER_TIMING_FIELDS})

    zero_fields = (
        "cpu_oracle_attempts",
        "attempt_mismatch_rows",
        "score_mismatches",
        "query_end_mismatches",
        "ref_end_local_mismatches",
        "terminal_mismatches",
        "cpu_control_selected_attempts",
        "cpu_reference_align_attempts",
        "cpu_continuation_failures",
        "missing_rows",
        "extra_rows",
    )
    for index, row in enumerate(rows):
        label = f"{path}: task {index}"
        require(int(row["task_index"]) == index, f"non-contiguous task index: {label}")
        require(row["execution_mode"] == "replacement_prototype", f"wrong execution mode: {label}")
        require(row["authority_comparison_available"] == "0", f"CPU authority enabled: {label}")
        require(row["validation_enabled"] == "0", f"all-attempt validation enabled: {label}")
        require(row["ok"] == "1" and row["output_equal"] == "-1", f"task failed: {label}")
        require(
            row["first_attempt_mismatch"] == row["first_consumer_mismatch"] == row["error"] == "none",
            f"consumer mismatch/error: {label}",
        )
        require(all(int(row[key]) == 0 for key in zero_fields), f"nonzero failure counter: {label}")

        groups = int(row["scoreinfo_groups"])
        attempts = int(row["attempts"])
        selected = int(row["control_selected_attempts"])
        require(attempts == 4 * groups, f"four-round attempt coverage mismatch: {label}")
        require(attempts == int(row["gpu_scored_attempts"]), f"GPU attempt coverage mismatch: {label}")
        require(
            groups
            == int(row["threshold_groups"])
            + int(row["best_fallback_groups"])
            + int(row["last_groups"])
            + int(row["empty_groups"]),
            f"group outcome partition mismatch: {label}",
        )
        require(
            selected
            == int(row["threshold_groups"])
            + int(row["best_fallback_groups"])
            + int(row["last_groups"]),
            f"selected outcome partition mismatch: {label}",
        )
        require(
            selected == int(row["cpu_continuation_calls"]) == int(row["cpu_align_attempts"]),
            f"selected CPU continuation accounting mismatch: {label}",
        )
        active = 1 if groups else 0
        require(int(row["consumer_selection_equal"]) == active, f"consumer selection activity mismatch: {label}")
        require(int(row["consumer_attempt_prefix_equal"]) == active, f"attempt prefix activity mismatch: {label}")
        require(int(row["endpoint_batches"]) == active, f"endpoint batch activity mismatch: {label}")
        require(int(row["cpu_continuation_requested"]) == active, f"continuation request mismatch: {label}")
        require(int(row["cpu_continuation_active"]) == active, f"continuation activity mismatch: {label}")
        require(float(row["cpu_oracle_seconds"]) == 0.0, f"CPU oracle timing is nonzero: {label}")
        require(all(float(row[key]) >= 0.0 for key in CONSUMER_TIMING_FIELDS), f"negative timing: {label}")

        for key in CONSUMER_TOTAL_FIELDS:
            totals[key] = int(totals[key]) + int(row[key])
        for key in CONSUMER_TIMING_FIELDS:
            totals[key] = float(totals[key]) + float(row[key])
    totals["task_rows"] = len(rows)
    return totals


def verify_candidate_metrics(
    path: Path, consumer: Mapping[str, int | float]
) -> dict[str, float]:
    metrics = parse_key_values(path)
    for key in FALLBACK_METRICS:
        require(metrics.get(key) == "0", f"fallback metric is missing or nonzero: {key}: {path}")
    required_exact = {
        FORWARD_PREFIX + "requested": 1,
        FORWARD_PREFIX + "active": 1,
        FORWARD_PREFIX + "tasks": EXPECTED_TASKS,
        FORWARD_PREFIX + "gpu_tasks": EXPECTED_TASKS,
        FORWARD_PREFIX + "cpu_scoreinfo_groups": 0,
        FORWARD_PREFIX + "scoreinfo_mismatches": 0,
        FORWARD_PREFIX + "candidate_missing": 0,
        FORWARD_PREFIX + "candidate_extra": 0,
        FORWARD_PREFIX + "cpu_prealign_seconds": 0,
        FORWARD_PREFIX + "realpath_requested": 1,
        FORWARD_PREFIX + "realpath_trust": 1,
        FORWARD_PREFIX + "realpath_used": EXPECTED_TASKS,
        FORWARD_PREFIX + "realpath_fallbacks": 0,
        FORWARD_PREFIX + "realpath_extend_calls": EXPECTED_TASKS,
        FORWARD_PREFIX + "realpath_extend_scoreinfo_groups": int(consumer["scoreinfo_groups"]),
        FORWARD_PREFIX + "realpath_extend_align_attempts": int(consumer["control_selected_attempts"]),
    }
    for key, expected in required_exact.items():
        require(key in metrics, f"missing candidate metric: {key}: {path}")
        require_float_equal(metrics[key], expected, f"candidate metric {key}")
    timing_keys = {
        "forward_total_seconds": FORWARD_PREFIX + "total_seconds",
        "forward_kernel_seconds": FORWARD_PREFIX + "kernel_seconds",
        "forward_h2d_seconds": FORWARD_PREFIX + "h2d_seconds",
        "forward_d2h_seconds": FORWARD_PREFIX + "d2h_seconds",
        "forward_minscore_seconds": FORWARD_PREFIX + "gpu_minscore_wall_seconds",
    }
    timings: dict[str, float] = {}
    for output_key, metric_key in timing_keys.items():
        require(metric_key in metrics, f"missing stage timing metric: {metric_key}: {path}")
        timings[output_key] = float(metrics[metric_key])
        require(timings[output_key] >= 0.0, f"negative stage timing: {metric_key}: {path}")
    return timings


def manifest_digest(paths: Iterable[Path], base: Path) -> tuple[int, int, str]:
    rows = []
    total_bytes = 0
    for path in sorted(paths, key=lambda value: value.relative_to(base).as_posix()):
        relative = path.relative_to(base).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        rows.append(f"{digest}\t{size}\t{relative}\n")
        total_bytes += size
    return len(rows), total_bytes, sha256_bytes("".join(rows).encode("utf-8"))


def tsv_bytes(fields: tuple[str, ...], rows: Iterable[Mapping[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, delimiter="\t", fieldnames=fields, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def verify_and_derive(run_root: Path, manifest_path: Path) -> dict[str, bytes]:
    run_root = run_root.resolve()
    require(run_root.is_dir(), f"missing formal run root: {run_root}")
    checkpoint_path = run_root / "checkpoint_receipt.json"
    preflight_path = run_root / "preflight.json"
    runs_path = run_root / "runs.tsv"
    checkpoint = load_json(checkpoint_path)
    preflight = load_json(preflight_path)
    run_fields, raw_runs = read_tsv(runs_path)
    manifest_fields, manifest_rows = read_tsv(manifest_path)
    require(run_fields == RUN_FIELDS, "runs.tsv schema mismatch")
    require(len(raw_runs) == 36, "formal run count must be 36")
    require(len(manifest_rows) == 3, "fixture manifest must contain three discrete fixtures")
    manifest = {row["fixture_id"]: row for row in manifest_rows}
    require(
        {key: int(row["query_length_nt"]) for key, row in manifest.items()}
        == EXPECTED_FIXTURE_LENGTHS,
        "fixture identities or discrete lengths changed",
    )

    require(checkpoint.get("schema_version") == "exact_long_query_hybrid_checkpoint_v1", "checkpoint schema mismatch")
    require(checkpoint.get("status") == "checkpoint_gate_pass", "checkpoint did not pass")
    require(checkpoint.get("run_count") == 36 and checkpoint.get("repeats") == 3, "checkpoint run matrix mismatch")
    require_float_equal(checkpoint.get("speedup_gate"), SPEEDUP_GATE, "speedup gate")
    require(checkpoint.get("gpu_only_traceback") is False, "checkpoint mislabels GPU traceback")
    require(checkpoint.get("validated_continuous_range") is False, "continuous range was overclaimed")
    require(checkpoint.get("production_target_scientific_contract_validated") is False, "production target was overclaimed")
    require(checkpoint.get("production_authorized") is False, "production was unexpectedly authorized")
    require(checkpoint.get("bioinformatics_v2_state_modified") is False, "Bioinformatics v2 was modified")
    source_identity = checkpoint["source_identity"]
    build_source = checkpoint["build_source"]
    require(source_identity["benchmark_source_commit"] == EXPECTED_SOURCE_COMMIT, "benchmark source mismatch")
    require(source_identity["runtime_path_diff_empty"] is True, "runtime path diff was not empty")
    require(build_source["source_commit"] == EXPECTED_SOURCE_COMMIT, "build source mismatch")
    require(build_source["source_status_before"] == build_source["source_status_after"] == "", "build source was dirty")
    require(build_source["source_diff_sha256"] == hashlib.sha256(b"").hexdigest(), "build source diff was not empty")
    require(checkpoint["binary_sha256"] == preflight["binary_sha256"] == build_source["binary_sha256"], "binary identity mismatch")
    binary = Path(str(build_source["binary"]))
    require(binary.is_file() and sha256_file(binary) == checkpoint["binary_sha256"], "formal binary digest mismatch")

    expected_matrix = {
        (fixture, mode, arm, repeat)
        for fixture in EXPECTED_FIXTURE_LENGTHS
        for mode in EXPECTED_MODES
        for arm in EXPECTED_ARMS
        for repeat in EXPECTED_REPEATS
    }
    observed_matrix: set[tuple[str, str, str, int]] = set()
    verified: dict[tuple[str, str, str, int], dict[str, object]] = {}
    output_paths: list[Path] = []
    run_receipt_paths: list[Path] = []
    consumer_paths: list[Path] = []

    for raw in raw_runs:
        key = (raw["fixture_id"], raw["mode"], raw["arm"], int(raw["repeat"]))
        require(key in expected_matrix and key not in observed_matrix, f"invalid or duplicate run: {key}")
        observed_matrix.add(key)
        fixture_id, mode, arm, repeat = key
        directory = run_root / fixture_id / mode / f"{arm}_{repeat}"
        receipt_path = directory / "run_receipt.json"
        invocation_path = directory / "invocation.json"
        timing_path = directory / "time.txt"
        stderr_path = directory / "stderr.log"
        require(all(path.is_file() for path in (receipt_path, invocation_path, timing_path, stderr_path)), f"missing run artifact: {key}")
        receipt = load_json(receipt_path)
        invocation = load_json(invocation_path)
        timing = parse_key_values(timing_path)
        require(receipt["fixture_id"] == fixture_id and receipt["mode"] == mode, f"run receipt identity mismatch: {key}")
        require(receipt["arm"] == arm and int(receipt["repeat"]) == repeat, f"run receipt arm/repeat mismatch: {key}")
        require(timing.get("exit_status") == "0", f"nonzero timing receipt: {key}")
        for field in ("wall_seconds", "max_rss_kb", "output_bytes", "output_sha256", "output_path"):
            expected = raw[field]
            actual = receipt[field]
            if field == "wall_seconds":
                require_float_equal(actual, expected, f"runs/run receipt {field}: {key}")
            elif field in ("max_rss_kb", "output_bytes"):
                require(int(actual) == int(expected), f"runs/run receipt {field}: {key}")
            else:
                require(str(actual) == expected, f"runs/run receipt {field}: {key}")
        require_float_equal(timing["wall_seconds"], receipt["wall_seconds"], f"time/run receipt wall: {key}")
        require(int(timing["max_rss_kb"]) == int(receipt["max_rss_kb"]), f"time/run receipt RSS: {key}")

        output = Path(str(receipt["output_path"])).resolve()
        require(output.is_relative_to(run_root) and output.parent == directory, f"output escaped run root: {key}")
        require(output.is_file(), f"missing output: {key}")
        require(output.stat().st_size == int(receipt["output_bytes"]), f"output size mismatch: {key}")
        require(sha256_file(output) == receipt["output_sha256"], f"output digest mismatch: {key}")
        expected_suffix = "-TFOsorted.lite" if mode == "lite" else "-TFOsorted"
        require(output.name.endswith(expected_suffix), f"output mode suffix mismatch: {key}")
        output_paths.append(output)
        run_receipt_paths.append(receipt_path)

        environment = invocation["environment"]
        require(environment["FASIM_OUTPUT_MODE"] == mode and environment["OMP_NUM_THREADS"] == "1", f"invocation mode/thread mismatch: {key}")
        if arm == "baseline":
            require(environment["FASIM_ALIGN_GASAL2"] == environment["FASIM_ENABLE_PREALIGN_CUDA"] == "0", f"baseline GPU flags active: {key}")
            require("consumer" not in receipt, f"baseline contains consumer report: {key}")
        else:
            consumer_path = directory / "consumer.tsv"
            consumer = verify_consumer(consumer_path)
            consumer_paths.append(consumer_path)
            require(environment["FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE"] == "1", f"replacement prototype inactive: {key}")
            require(environment["FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION"] == "1", f"CPU continuation inactive: {key}")
            require(environment["FASIM_ALIGN_GASAL2_MAX_QUERY_LEN"] == "2812", f"legacy guard contract changed: {key}")
            require(int(receipt["consumer"]["task_rows"]) == EXPECTED_TASKS, f"receipt consumer task count mismatch: {key}")
            for field in RECEIPT_CONSUMER_FIELDS:
                if field in CONSUMER_TIMING_FIELDS:
                    require_float_equal(receipt["consumer"][field], consumer[field], f"consumer receipt {field}: {key}")
                else:
                    require(int(receipt["consumer"][field]) == int(consumer[field]), f"consumer receipt {field}: {key}")
            forward = verify_candidate_metrics(stderr_path, consumer)
            receipt["verified_consumer"] = consumer
            receipt["verified_forward"] = forward
        verified[key] = receipt
    require(observed_matrix == expected_matrix, "formal run matrix is incomplete")

    result_fields = (
        "fixture_id", "evidence_role", "gene_id", "gene_symbol", "query_length_nt", "mode", "repeats",
        "output_bytes", "output_sha256", "byte_equal", "deterministic", "median_baseline_wall_seconds",
        "median_candidate_wall_seconds", "median_paired_speedup", "speedup_gate_pass", "task_rows_per_candidate_run",
        "scoreinfo_groups_per_candidate_run", "attempts_per_candidate_run", "gpu_scored_attempts_per_candidate_run",
        "selected_attempts_per_candidate_run", "selected_cpu_continuation_calls_per_candidate_run",
        "all_attempt_cpu_oracle_attempts_per_candidate_run", "full_cpu_consumer_replay_attempts_per_candidate_run",
        "continuation_failures_per_candidate_run", "fallbacks_per_candidate_run",
    )
    result_rows: list[dict[str, object]] = []
    timing_fields = (
        "fixture_id", "mode", "repeat", "wall_seconds", "forward_total_seconds", "forward_kernel_seconds",
        "forward_h2d_seconds", "forward_d2h_seconds", "forward_minscore_seconds", "attempt_score_seconds",
        "attempt_gpu_kernel_seconds", "attempt_h2d_seconds", "attempt_d2h_seconds", "host_select_seconds",
        "selected_cpu_traceback_seconds", "conversion_seconds", "consumer_total_seconds", "unprofiled_wall_seconds",
    )
    timing_rows: list[dict[str, object]] = []
    derived_fixture_results: list[dict[str, object]] = []

    receipt_fixture_map = {row["fixture_id"]: row for row in checkpoint["fixtures"]}
    for fixture_id, query_length in EXPECTED_FIXTURE_LENGTHS.items():
        fixture = manifest[fixture_id]
        derived_modes = []
        for mode in EXPECTED_MODES:
            baselines = [verified[(fixture_id, mode, "baseline", repeat)] for repeat in EXPECTED_REPEATS]
            candidates = [verified[(fixture_id, mode, "candidate", repeat)] for repeat in EXPECTED_REPEATS]
            baseline_paths = [Path(str(row["output_path"])) for row in baselines]
            candidate_paths = [Path(str(row["output_path"])) for row in candidates]
            for baseline, candidate in zip(baseline_paths, candidate_paths):
                require(filecmp.cmp(baseline, candidate, shallow=False), f"paired output bytes differ: {fixture_id} {mode}")
            digests = {str(row["output_sha256"]) for row in baselines + candidates}
            sizes = {int(row["output_bytes"]) for row in baselines + candidates}
            require(len(digests) == len(sizes) == 1, f"nondeterministic output: {fixture_id} {mode}")
            output_digest = next(iter(digests))
            expected_digest = fixture["expected_lite_sha256" if mode == "lite" else "expected_tfosorted_sha256"]
            require(expected_digest != "pending_clean_checkpoint", f"unfrozen output digest remains: {fixture_id} {mode}")
            require(output_digest == expected_digest, f"manifest output digest mismatch: {fixture_id} {mode}")
            paired_speedups = [float(base["wall_seconds"]) / float(candidate["wall_seconds"]) for base, candidate in zip(baselines, candidates)]
            median_speedup = statistics.median(paired_speedups)
            require(median_speedup >= SPEEDUP_GATE, f"speedup gate failed: {fixture_id} {mode}")

            stable_consumer_fields = (
                "task_rows", "scoreinfo_groups", "attempts", "gpu_scored_attempts", "control_selected_attempts",
                "cpu_continuation_calls", "cpu_oracle_attempts", "cpu_reference_align_attempts", "cpu_continuation_failures",
            )
            for field in stable_consumer_fields:
                require(len({int(row["verified_consumer"][field]) for row in candidates}) == 1, f"consumer count drift: {fixture_id} {mode} {field}")
            consumer = candidates[0]["verified_consumer"]
            result_rows.append({
                "fixture_id": fixture_id,
                "evidence_role": fixture["evidence_role"],
                "gene_id": fixture["gene_id"],
                "gene_symbol": fixture["gene_symbol"],
                "query_length_nt": query_length,
                "mode": mode,
                "repeats": 3,
                "output_bytes": next(iter(sizes)),
                "output_sha256": output_digest,
                "byte_equal": 1,
                "deterministic": 1,
                "median_baseline_wall_seconds": f"{statistics.median(float(row['wall_seconds']) for row in baselines):.6f}",
                "median_candidate_wall_seconds": f"{statistics.median(float(row['wall_seconds']) for row in candidates):.6f}",
                "median_paired_speedup": f"{median_speedup:.9f}",
                "speedup_gate_pass": 1,
                "task_rows_per_candidate_run": consumer["task_rows"],
                "scoreinfo_groups_per_candidate_run": consumer["scoreinfo_groups"],
                "attempts_per_candidate_run": consumer["attempts"],
                "gpu_scored_attempts_per_candidate_run": consumer["gpu_scored_attempts"],
                "selected_attempts_per_candidate_run": consumer["control_selected_attempts"],
                "selected_cpu_continuation_calls_per_candidate_run": consumer["cpu_continuation_calls"],
                "all_attempt_cpu_oracle_attempts_per_candidate_run": consumer["cpu_oracle_attempts"],
                "full_cpu_consumer_replay_attempts_per_candidate_run": consumer["cpu_reference_align_attempts"],
                "continuation_failures_per_candidate_run": consumer["cpu_continuation_failures"],
                "fallbacks_per_candidate_run": 0,
            })
            for repeat, candidate in zip(EXPECTED_REPEATS, candidates):
                consumer_values = candidate["verified_consumer"]
                forward_values = candidate["verified_forward"]
                residual = float(candidate["wall_seconds"]) - float(forward_values["forward_total_seconds"]) - float(consumer_values["total_seconds"])
                require(residual >= 0.0, f"profiled time exceeds wall time: {fixture_id} {mode} repeat {repeat}")
                timing_rows.append({
                    "fixture_id": fixture_id,
                    "mode": mode,
                    "repeat": repeat,
                    "wall_seconds": f"{float(candidate['wall_seconds']):.6f}",
                    **{key: f"{float(value):.9f}" for key, value in forward_values.items()},
                    "attempt_score_seconds": f"{float(consumer_values['score_seconds']):.9f}",
                    "attempt_gpu_kernel_seconds": f"{float(consumer_values['gpu_kernel_seconds']):.9f}",
                    "attempt_h2d_seconds": f"{float(consumer_values['h2d_seconds']):.9f}",
                    "attempt_d2h_seconds": f"{float(consumer_values['d2h_seconds']):.9f}",
                    "host_select_seconds": f"{float(consumer_values['select_seconds']):.9f}",
                    "selected_cpu_traceback_seconds": f"{float(consumer_values['traceback_seconds']):.9f}",
                    "conversion_seconds": f"{float(consumer_values['convert_seconds']):.9f}",
                    "consumer_total_seconds": f"{float(consumer_values['total_seconds']):.9f}",
                    "unprofiled_wall_seconds": f"{residual:.9f}",
                })
            derived_modes.append({
                "mode": mode,
                "output_sha256": output_digest,
                "paired_speedups": paired_speedups,
                "median_paired_speedup": median_speedup,
            })
        derived_fixture_results.append({
            "fixture_id": fixture_id,
            "gene_id": fixture["gene_id"],
            "gene_symbol": fixture["gene_symbol"],
            "query_length_nt": query_length,
            "required_dynamic_smem_bytes": 3 * math.ceil(query_length / 32) * 32 * 2,
            "resource_fit": True,
            "modes": derived_modes,
        })

    for derived in derived_fixture_results:
        recorded = receipt_fixture_map[derived["fixture_id"]]
        require(recorded["gene_id"] == derived["gene_id"] and recorded["query_length_nt"] == derived["query_length_nt"], "checkpoint fixture metadata mismatch")
        require(recorded["required_dynamic_smem_bytes"] == derived["required_dynamic_smem_bytes"], "shared-memory receipt mismatch")
        recorded_modes = {row["mode"]: row for row in recorded["modes"]}
        for mode in derived["modes"]:
            recorded_mode = recorded_modes[mode["mode"]]
            require(recorded_mode["output_sha256"] == mode["output_sha256"], "checkpoint output summary mismatch")
            require(recorded_mode["deterministic"] is True and recorded_mode["byte_equal"] is True, "checkpoint exactness summary mismatch")
            require_float_equal(recorded_mode["median_paired_speedup"], mode["median_paired_speedup"], "checkpoint median speedup")
            require(len(recorded_mode["paired_speedups"]) == 3, "checkpoint paired speedup count mismatch")
            for actual, expected in zip(recorded_mode["paired_speedups"], mode["paired_speedups"]):
                require_float_equal(actual, expected, "checkpoint paired speedup")

    environment = checkpoint["environment"]
    cuda = environment["cuda_attributes"]
    scoring = environment["scoring_contract"]
    optin_limit = int(cuda["optin_shared_memory_per_block_bytes"])
    resource_ceiling = (optin_limit // (3 * 32 * 2)) * 32
    operating_envelope = {
        "schema_version": "exact_long_query_hybrid_operating_envelope_v1",
        "status": "observed_on_three_discrete_fixtures_only",
        "benchmark_source_commit": EXPECTED_SOURCE_COMMIT,
        "binary_sha256": checkpoint["binary_sha256"],
        "hardware": {
            "hostname": environment["hostname"],
            "cpu_model": environment["cpu_model"],
            "gpu_inventory": environment["nvidia_smi"],
            "benchmark_device_index": cuda["device_index"],
            "default_shared_memory_per_block_bytes": cuda["default_shared_memory_per_block_bytes"],
            "optin_shared_memory_per_block_bytes": optin_limit,
        },
        "resource_model": {
            "required_dynamic_smem_formula": "3 * ceil(query_length_nt / 32) * 32 * sizeof(int16_t)",
            "resource_only_query_length_ceiling_nt": resource_ceiling,
            "resource_only_ceiling_is_scientifically_validated": False,
            "resource_fit_does_not_imply_scientific_support": True,
        },
        "scoring_contract": scoring,
        "numeric_safety": {
            "state_storage": "int16_t",
            "int16_max": 32767,
            "conservative_condition": "5 * min(query_length_nt, target_subview_length_nt) <= INT16_MAX",
            "runtime_range_guard_implemented": False,
            "boundary_fixtures_validated": False,
        },
        "validated_query_lengths_nt": list(EXPECTED_FIXTURE_LENGTHS.values()),
        "validated_continuous_range": False,
        "fixture_observations": [
            {
                "fixture_id": row["fixture_id"],
                "query_length_nt": row["query_length_nt"],
                "required_dynamic_smem_bytes": row["required_dynamic_smem_bytes"],
                "resource_fit": True,
                "full_output_byte_equal": True,
            }
            for row in derived_fixture_results
        ],
        "target_contract": {
            "executed_target_role": "development_contiguous_chr22_slice",
            "executed_target_sha256": manifest_rows[0]["target_sha256"],
            "production_promoter_identity_gate": checkpoint["promoter_identity_gate"]["status"],
            "production_promoter_scientific_contract_validated": False,
        },
        "unsupported_configuration_fail_closed_guards_implemented": False,
    }

    all_artifacts = [path for path in run_root.rglob("*") if path.is_file()]
    artifact_count, artifact_bytes, artifact_digest = manifest_digest(all_artifacts, run_root)
    run_receipt_count, run_receipt_bytes, run_receipt_digest = manifest_digest(run_receipt_paths, run_root)
    consumer_count, consumer_bytes, consumer_digest = manifest_digest(consumer_paths, run_root)
    output_count, output_bytes_total, output_digest = manifest_digest(output_paths, run_root)
    min_speedup = min(float(row["median_paired_speedup"]) for row in result_rows)
    decision = {
        "schema_version": "exact_long_query_hybrid_checkpoint_decision_v1",
        "status": "checkpoint_gate_pass",
        "decision": "retain_as_exact_hybrid_engineering_candidate",
        "implementation": checkpoint["implementation"],
        "evidence": {
            "formal_run_root": str(run_root),
            "completed_utc": checkpoint["completed_utc"],
            "benchmark_source_commit": EXPECTED_SOURCE_COMMIT,
            "checkpoint_harness_commit_at_execution": source_identity["checkpoint_harness_commit"],
            "binary_sha256": checkpoint["binary_sha256"],
            "checkpoint_receipt_sha256": sha256_file(checkpoint_path),
            "preflight_sha256": sha256_file(preflight_path),
            "runs_tsv_sha256": sha256_file(runs_path),
            "formal_artifact_manifest": {
                "algorithm": "sha256 of sorted '<sha256>\\t<size>\\t<relative_path>\\n' rows",
                "file_count": artifact_count,
                "total_bytes": artifact_bytes,
                "sha256": artifact_digest,
            },
            "run_receipts": {"count": run_receipt_count, "total_bytes": run_receipt_bytes, "manifest_sha256": run_receipt_digest},
            "consumer_reports": {"count": consumer_count, "total_bytes": consumer_bytes, "manifest_sha256": consumer_digest},
            "output_artifacts": {"count": output_count, "total_bytes": output_bytes_total, "manifest_sha256": output_digest},
        },
        "gates": {
            "clean_source_and_binary_identity": "pass",
            "run_matrix_36_of_36": "pass",
            "full_and_lite_output_byte_equality": "pass",
            "three_repeat_output_determinism": "pass",
            "all_attempt_gpu_coverage": "pass",
            "all_attempt_cpu_oracle_zero": "pass",
            "full_cpu_consumer_replay_zero": "pass",
            "selected_cpu_continuation_failures_zero": "pass",
            "fallbacks_zero": "pass",
            "median_paired_speedup_at_least_1_5x": "pass",
            "minimum_fixture_mode_median_paired_speedup": min_speedup,
            "production_promoter_identity": checkpoint["promoter_identity_gate"]["status"],
            "production_promoter_scientific_contract": "not_executed",
            "continuous_query_length_range": "not_validated",
            "runtime_parameter_and_int16_guards": "not_implemented",
        },
        "authorization": {
            "long_query_hybrid": "engineering_candidate",
            "next_engineering_stage": "fresh_real_promoter_validation_panel",
            "execution_mode_product_release": False,
            "production_authorized": False,
            "gpu_only_or_full_gpu_claim": False,
            "bioinformatics_v2_state_modified": False,
        },
        "claim_boundary": [
            "exactness passed on three discrete query fixtures and one development target slice",
            "the 4-12 kb continuous range is not validated",
            "the production promoter scientific and coordinate-restoration contract is not validated",
            "selected attempts still use CPU canonical reverse-start and CIGAR continuation",
        ],
    }

    return {
        "checkpoint_results.tsv": tsv_bytes(result_fields, result_rows),
        "stage_timing.tsv": tsv_bytes(timing_fields, timing_rows),
        "operating_envelope.json": json_bytes(operating_envelope),
        "decision.json": json_bytes(decision),
    }


def checksum_bytes(artifacts: Mapping[str, bytes], output_dir: Path) -> bytes:
    rows = []
    for name in sorted(artifacts):
        rows.append(f"{sha256_bytes(artifacts[name])}  docs/exact_long_query_hybrid_checkpoint_v1/{name}\n")
    for name in (
        "checkpoint_fixtures.tsv",
        "preexecution_input_repair_v1.json",
        "production_promoter_contract.json",
    ):
        path = output_dir / name
        rows.append(f"{sha256_file(path)}  docs/exact_long_query_hybrid_checkpoint_v1/{name}\n")
    return "".join(sorted(rows)).encode("utf-8")


def materialize(artifacts: Mapping[str, bytes], output_dir: Path, write: bool) -> None:
    expected = dict(artifacts)
    expected["checksums.sha256"] = checksum_bytes(artifacts, output_dir)
    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, value in expected.items():
            (output_dir / name).write_bytes(value)
        return
    for name, value in expected.items():
        path = output_dir / name
        require(path.is_file(), f"missing frozen artifact: {path}")
        require(path.read_bytes() == value, f"frozen artifact drift: {path}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--run-root", type=Path, required=True)
    result.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    result.add_argument("--output-dir", type=Path, default=DOC_DIR)
    result.add_argument("--write", action="store_true", help="write verified derived artifacts; otherwise check them")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        artifacts = verify_and_derive(args.run_root, args.manifest)
        materialize(artifacts, args.output_dir, args.write)
        decision = json.loads(artifacts["decision.json"])
        print(json.dumps({
            "status": decision["status"],
            "formal_artifact_files": decision["evidence"]["formal_artifact_manifest"]["file_count"],
            "formal_artifact_manifest_sha256": decision["evidence"]["formal_artifact_manifest"]["sha256"],
            "write": args.write,
        }, indent=2, sort_keys=True))
        return 0
    except (FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
