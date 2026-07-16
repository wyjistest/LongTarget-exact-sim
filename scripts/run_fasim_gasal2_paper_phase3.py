#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/run_fasim_gasal2_paper_benchmarks.sh"
CONTRACT_COMPARATOR = ROOT / "scripts/compare_fasim_segmented_contract.py"
RUNTIME_EPOCH = 0
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
SEED = 20260715
COMPARATOR_VERSION = 1
PAIR_ROOT_NAME = "pairs-v1"
SUPPORTED_ROLES = {"generalization_core", "breadth"}
EXPECTED_SUPPORTED_IDS = {f"g{index:02d}_" for index in range(1, 14)}
EXPECTED_GUARD_IDS = {
    "n01_malat1_full_guard",
    "n02_neat1_full_guard",
    "n03_kcnq1ot1_full_guard",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return list(reader)


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid JSON artifact: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON artifact must be an object: {path}")
    return payload


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
    return values


def benchmark_metrics(path: Path) -> dict[str, str]:
    return {
        key.removeprefix("benchmark."): value
        for key, value in parse_key_values(
            path.read_text(encoding="utf-8", errors="replace")
        ).items()
        if key.startswith("benchmark.")
    }


def metric_int(metrics: dict[str, str], key: str) -> int:
    try:
        return int(float(metrics.get(key, "0") or "0"))
    except ValueError as exc:
        raise SystemExit(f"invalid benchmark counter {key}") from exc


def load_phase3_rows(manifest: Path) -> list[dict[str, str]]:
    rows = [
        row
        for row in read_tsv(manifest)
        if row["role"] in SUPPORTED_ROLES or row["role"] == "negative_control"
    ]
    supported = [row for row in rows if row["role"] in SUPPORTED_ROLES]
    guards = [row for row in rows if row["role"] == "negative_control"]
    if len(supported) != 13 or len(guards) != 3:
        raise SystemExit("frozen Phase 3 workload count drifted")
    if not all(
        any(row["workload_id"].startswith(prefix) for prefix in EXPECTED_SUPPORTED_IDS)
        for row in supported
    ):
        raise SystemExit("frozen supported workload IDs drifted")
    if {row["workload_id"] for row in guards} != EXPECTED_GUARD_IDS:
        raise SystemExit("frozen guard workload IDs drifted")
    if any(
        row["adapter_id"] != "direct_tfo_contract"
        or row["preset_id"] != "gasal2_short_topk_v1"
        or row["output_contract"] != "fast_topk_score_stability_nt"
        for row in supported
    ):
        raise SystemExit("Phase 3 supported rows do not use one frozen preset/contract")
    if any(
        row["adapter_id"] != "preflight_guard"
        or row["output_contract"] != "preflight_guard_only"
        or row["required_pairs"] != "0"
        for row in guards
    ):
        raise SystemExit("Phase 3 guard rows drifted")
    return rows


def harness_plan(
    manifest: Path, binary: Path, workload_id: str, seed: int
) -> dict[str, object]:
    result = subprocess.run(
        [
            "bash",
            str(HARNESS),
            "--dry-run",
            "--manifest",
            str(manifest),
            "--binary",
            str(binary),
            "--workload-id",
            workload_id,
            "--seed",
            str(seed),
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or "paper harness dry-run failed")
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise SystemExit("paper harness dry-run did not return an object")
    return payload


def build_phase3_plan(
    rows: list[dict[str, str]], manifest: Path, binary: Path, seed: int
) -> dict[str, object]:
    supported = [row for row in rows if row["role"] in SUPPORTED_ROLES]
    guards = [row for row in rows if row["role"] == "negative_control"]
    pairs: list[dict[str, object]] = []
    warmups: list[dict[str, object]] = []
    preflights: list[dict[str, object]] = []
    timed_run_count = 0
    for row in rows:
        plan = harness_plan(manifest, binary, row["workload_id"], seed)
        runs = plan.get("runs")
        planned_warmups = plan.get("warmups")
        if not isinstance(runs, list) or not isinstance(planned_warmups, list):
            raise SystemExit(f"invalid harness plan for {row['workload_id']}")
        if row["role"] == "negative_control":
            if len(runs) != 1 or runs[0].get("mode") != "preflight" or planned_warmups:
                raise SystemExit(f"invalid preflight plan for {row['workload_id']}")
            preflights.extend(runs)
            continue
        grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
        for run in runs:
            grouped[int(run["pair_id"])].append(run)
        if len(grouped) != int(row["required_pairs"]):
            raise SystemExit(f"pair expansion mismatch for {row['workload_id']}")
        for pair_id, pair_runs in sorted(grouped.items()):
            ordered = sorted(pair_runs, key=lambda run: int(run["order_index"]))
            modes = [str(run["mode"]) for run in ordered]
            if modes not in (["baseline", "candidate"], ["candidate", "baseline"]):
                raise SystemExit(f"invalid paired order for {row['workload_id']} pair {pair_id}")
            pairs.append(
                {
                    "workload_id": row["workload_id"],
                    "pair_id": pair_id,
                    "pair_order": ordered[0]["pair_order"],
                    "modes": modes,
                    "run_ids": [run["run_id"] for run in ordered],
                }
            )
        warmups.extend(planned_warmups)
        timed_run_count += len(runs)
    return {
        "schema_version": 1,
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "seed": seed,
        "supported_workload_count": len(supported),
        "guard_workload_count": len(guards),
        "pair_count": len(pairs),
        "timed_run_count": timed_run_count,
        "warmup_count": len(warmups),
        "preflight_count": len(preflights),
        "warmups": warmups,
        "preflights": preflights,
        "pairs": pairs,
    }


def visible_gpu_ids(required: int) -> list[str]:
    if required == 0:
        return []
    configured = os.environ.get("CUDA_VISIBLE_DEVICES")
    if configured is not None:
        ids = [value.strip() for value in configured.split(",") if value.strip() not in {"", "-1"}]
    else:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader,nounits"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ids = [line.strip() for line in result.stdout.splitlines() if line.strip()] if result.returncode == 0 else []
    if len(ids) < required:
        raise SystemExit(
            f"blocked_reason=insufficient_visible_gpus required={required} available={len(ids)}"
        )
    return ids[:required]


def invoke_harness(
    manifest: Path,
    binary: Path,
    artifact_root: Path,
    row: dict[str, str],
    mode: str,
    seed: int,
    resume: bool,
    *,
    pair_id: int | None = None,
    warmup: bool = False,
) -> dict[str, object]:
    label = (
        f"{row['workload_id']} warmup {mode}"
        if warmup
        else f"{row['workload_id']} {'preflight' if mode == 'preflight' else f'pair {pair_id} {mode}'}"
    )
    print(f"phase3_run_start={label}", file=sys.stderr, flush=True)
    command = [
        "bash",
        str(HARNESS),
        "--manifest",
        str(manifest),
        "--binary",
        str(binary),
        "--artifact-root",
        str(artifact_root),
        "--workload-id",
        row["workload_id"],
        "--mode",
        mode,
        "--seed",
        str(seed),
    ]
    if warmup:
        command.append("--warmup")
    elif mode != "preflight" and pair_id is not None:
        command.extend(["--pair-id", str(pair_id)])
    if resume:
        command.append("--resume")
    environment = os.environ.copy()
    gpu_ids = visible_gpu_ids(int(row["requires_gpu_count"]))
    if gpu_ids:
        environment["CUDA_VISIBLE_DEVICES"] = ",".join(gpu_ids)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "paper harness run failed")
    payload = json.loads(result.stdout)
    print(
        f"phase3_run_done={label} status={payload.get('status', 'unknown')}",
        file=sys.stderr,
        flush=True,
    )
    return payload


def find_tfosorted(run_dir: Path) -> Path:
    matches = sorted((run_dir / "output").glob("*-TFOsorted"))
    if len(matches) != 1:
        raise SystemExit(f"expected one TFOsorted in {run_dir}, found {len(matches)}")
    return matches[0]


def compare_supported_pair(
    baseline: Path, candidate: Path, work: Path
) -> dict[str, object]:
    details = work / "top5-details.tsv"
    command = [
        sys.executable,
        str(CONTRACT_COMPARATOR),
        "--baseline",
        str(find_tfosorted(baseline)),
        "--candidate",
        str(find_tfosorted(candidate)),
        "--k",
        "5",
        "--details",
        str(details),
    ]
    comparison = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (work / "comparator.stdout.log").write_text(comparison.stdout, encoding="utf-8")
    (work / "comparator.stderr.log").write_text(comparison.stderr, encoding="utf-8")
    if comparison.returncode not in {0, 1} or not details.is_file():
        raise SystemExit(
            comparison.stderr.strip() or "generalization comparator did not produce details"
        )
    values = parse_key_values(comparison.stdout)
    required = {
        "full_missing_rows",
        "full_extra_rows",
        "raw_score_top5_equal",
        "raw_stability_top5_equal",
        "raw_nt_top5_equal",
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "all_three_top5_equal",
        "boundary_ties_equal",
        "baseline_boundary_tie_groups",
        "candidate_boundary_tie_groups",
        "representative_conflict_clusters",
        "candidate_representative_conflict_clusters",
    }
    missing = sorted(required - set(values))
    if missing:
        raise SystemExit("generalization comparator missing fields: " + ",".join(missing))
    metrics = benchmark_metrics(candidate / "stderr.log")
    requested = metric_int(metrics, "fasim_top5_gasal2_gpu_scoreinfo_requested")
    active = metric_int(metrics, "fasim_top5_gasal2_gpu_scoreinfo_active")
    runtime_fallbacks = metric_int(metrics, "fasim_gasal2_fallbacks")
    length_guards = metric_int(metrics, "fasim_gasal2_length_guard_fallbacks")
    batch_fallbacks = metric_int(
        metrics, "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches"
    )
    overflow = metric_int(
        metrics, "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches"
    )
    fallbacks = runtime_fallbacks + length_guards + batch_fallbacks
    active_path = requested == 1 and active == 1
    all_three = values["all_three_top5_equal"] == "1"
    boundary_ties = values["boundary_ties_equal"] == "1"
    if fallbacks or overflow or not active_path:
        status = "fallback"
        decision = "generalization_runtime_fallback"
    elif not all_three or not boundary_ties:
        status = "mismatch"
        decision = "generalization_clustered_contract_mismatch"
    else:
        status = "clean"
        decision = "generalization_clustered_contract_clean"
    return {
        "raw_score_top5_equal": int(values["raw_score_top5_equal"]),
        "raw_stability_top5_equal": int(values["raw_stability_top5_equal"]),
        "raw_nt_top5_equal": int(values["raw_nt_top5_equal"]),
        "clustered_score_top5_equal": int(values["clustered_score_top5_equal"]),
        "clustered_stability_top5_equal": int(values["clustered_stability_top5_equal"]),
        "clustered_nt_top5_equal": int(values["clustered_nt_top5_equal"]),
        "all_three_top5_equal": int(all_three),
        "boundary_ties_equal": int(boundary_ties),
        "baseline_boundary_tie_groups": int(values["baseline_boundary_tie_groups"]),
        "candidate_boundary_tie_groups": int(values["candidate_boundary_tie_groups"]),
        "baseline_representative_conflict_clusters": int(
            values["representative_conflict_clusters"]
        ),
        "candidate_representative_conflict_clusters": int(
            values["candidate_representative_conflict_clusters"]
        ),
        "full_missing_rows": int(values["full_missing_rows"]),
        "full_extra_rows": int(values["full_extra_rows"]),
        "candidate_active_path": int(active_path),
        "gasal2_requests": metric_int(metrics, "fasim_gasal2_requests"),
        "traceback_requests": metric_int(metrics, "fasim_gasal2_traceback_requests"),
        "fallbacks": fallbacks,
        "length_guard_fallbacks": length_guards,
        "runtime_batch_fallbacks": batch_fallbacks,
        "overflow_fallbacks": overflow,
        "oom": 0,
        "status": status,
        "decision": decision,
        "details_path": str(details),
    }


def pair_id_text(workload_id: str, pair_id: int) -> str:
    return f"{workload_id}__pair{pair_id:02d}__{RUNTIME_EPOCH}"


def publish_pair(
    row: dict[str, str],
    pair: dict[str, object],
    artifact_root: Path,
    resume: bool,
) -> str:
    workload_id = row["workload_id"]
    pair_id = int(pair["pair_id"])
    baseline = artifact_root / f"{workload_id}__pair{pair_id:02d}__baseline__{RUNTIME_EPOCH}"
    candidate = artifact_root / f"{workload_id}__pair{pair_id:02d}__candidate__{RUNTIME_EPOCH}"
    component_paths = {
        "baseline": baseline / "run-complete.json",
        "candidate": candidate / "run-complete.json",
    }
    for mode, path in component_paths.items():
        if not path.is_file():
            raise SystemExit(f"missing {mode} component receipt for {workload_id} pair {pair_id}")
    component_digests = {mode: sha256(path) for mode, path in component_paths.items()}
    config: dict[str, object] = {
        "schema_version": 1,
        "pair_id_text": pair_id_text(workload_id, pair_id),
        "workload_id": workload_id,
        "claim_id": row["claim_id"],
        "role": row["role"],
        "query_id": row["query_id"],
        "query_length_nt": int(row["query_length_nt"]),
        "fragment_position": row["fragment_position"],
        "target_id": row["target_id"],
        "target_region": row["target_region"],
        "preset_id": row["preset_id"],
        "pair_id": pair_id,
        "pair_order": pair["pair_order"],
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "output_contract": row["output_contract"],
        "comparator_version": COMPARATOR_VERSION,
        "baseline_run_id": baseline.name,
        "candidate_run_id": candidate.name,
        "baseline_receipt_sha256": component_digests["baseline"],
        "candidate_receipt_sha256": component_digests["candidate"],
    }
    config["config_digest_sha256"] = canonical_digest(config)
    destination = artifact_root / PAIR_ROOT_NAME / pair_id_text(workload_id, pair_id)
    complete_path = destination / "pair-complete.json"
    if destination.exists():
        if not complete_path.is_file():
            raise SystemExit(f"incomplete pair receipt: {destination}")
        existing_config = load_json(destination / "pair-config.json")
        complete = load_json(complete_path)
        if existing_config.get("config_digest_sha256") != config["config_digest_sha256"]:
            raise SystemExit(f"pair config digest mismatch: {destination}")
        summary_path = destination / "pair-summary.json"
        if complete.get("summary_sha256") != sha256(summary_path):
            raise SystemExit(f"pair summary digest mismatch: {destination}")
        if not resume:
            raise SystemExit(f"duplicate pair ID: {destination.name}")
        return "reused"

    temporary = artifact_root / PAIR_ROOT_NAME / f".{destination.name}.partial.{os.getpid()}"
    temporary.mkdir(parents=True)
    atomic_json(temporary / "pair-config.json", config)
    try:
        comparison = compare_supported_pair(baseline, candidate, temporary)
    except BaseException as exc:
        atomic_json(
            temporary / "pair-failure.json",
            {
                "schema_version": 1,
                "status": "technical_failure",
                "reason": "pair_comparator_failure",
                "exception_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        failed = destination.with_name(f"{destination.name}.failed.{time.time_ns()}")
        os.replace(temporary, failed)
        raise
    baseline_summary = load_json(baseline / "summary.json")
    candidate_summary = load_json(candidate / "summary.json")
    baseline_wall = float(baseline_summary["wall_seconds"])
    candidate_wall = float(candidate_summary["wall_seconds"])
    summary: dict[str, object] = {
        **config,
        **comparison,
        "baseline_wall_seconds": baseline_wall,
        "candidate_wall_seconds": candidate_wall,
        "paired_speedup": baseline_wall / candidate_wall if candidate_wall else "NA",
        "baseline_max_rss_kb": baseline_summary.get("max_rss_kb", "NA"),
        "candidate_max_rss_kb": candidate_summary.get("max_rss_kb", "NA"),
        "baseline_gpu_memory_peak_mib": baseline_summary.get("gpu_memory_peak_mib", "NA"),
        "candidate_gpu_memory_peak_mib": candidate_summary.get("gpu_memory_peak_mib", "NA"),
    }
    atomic_json(temporary / "pair-summary.json", summary)
    atomic_json(
        temporary / "pair-complete.json",
        {
            "schema_version": 1,
            "status": "complete",
            "pair_id_text": destination.name,
            "config_digest_sha256": config["config_digest_sha256"],
            "summary_sha256": sha256(temporary / "pair-summary.json"),
        },
    )
    os.replace(temporary, destination)
    return "completed"


RUN_FIELDS = [
    "run_id",
    "workload_id",
    "role",
    "query_id",
    "query_length_nt",
    "fragment_position",
    "target_id",
    "target_region",
    "pair_id",
    "mode",
    "warmup",
    "status",
    "runtime_epoch",
    "config_digest_sha256",
    "wall_seconds",
    "max_rss_kb",
    "gpu_memory_peak_mib",
    "gpu_temperature_peak_c",
    "gpu_power_peak_w",
    "receipt_path",
]
PAIR_FIELDS = [
    "pair_id_text",
    "workload_id",
    "claim_id",
    "role",
    "query_id",
    "query_length_nt",
    "fragment_position",
    "target_id",
    "target_region",
    "preset_id",
    "pair_id",
    "pair_order",
    "runtime_epoch",
    "runtime_commit",
    "comparator_version",
    "output_contract",
    "baseline_wall_seconds",
    "candidate_wall_seconds",
    "paired_speedup",
    "baseline_max_rss_kb",
    "candidate_max_rss_kb",
    "baseline_gpu_memory_peak_mib",
    "candidate_gpu_memory_peak_mib",
    "raw_score_top5_equal",
    "raw_stability_top5_equal",
    "raw_nt_top5_equal",
    "clustered_score_top5_equal",
    "clustered_stability_top5_equal",
    "clustered_nt_top5_equal",
    "all_three_top5_equal",
    "boundary_ties_equal",
    "baseline_boundary_tie_groups",
    "candidate_boundary_tie_groups",
    "baseline_representative_conflict_clusters",
    "candidate_representative_conflict_clusters",
    "full_missing_rows",
    "full_extra_rows",
    "candidate_active_path",
    "gasal2_requests",
    "traceback_requests",
    "fallbacks",
    "length_guard_fallbacks",
    "runtime_batch_fallbacks",
    "overflow_fallbacks",
    "oom",
    "status",
    "decision",
    "details_path",
    "pair_summary_path",
]
GUARD_FIELDS = [
    "run_id",
    "workload_id",
    "query_id",
    "query_length_nt",
    "target_id",
    "supported",
    "reason",
    "gpu_fast_path_executed",
    "status",
    "receipt_path",
]
FAILURE_FIELDS = ["artifact_path", "run_id", "status", "reason", "returncode", "timed_out"]
ARTIFACT_FIELDS = ["artifact_path", "size_bytes", "sha256"]


def rebuild_tables(artifact_root: Path) -> None:
    artifact_root.mkdir(parents=True, exist_ok=True)
    run_rows: list[dict[str, object]] = []
    guard_rows: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    for path in sorted(artifact_root.iterdir()):
        if (
            not path.is_dir()
            or path.name == "pairs"
            or path.name.startswith("pairs-v")
            or path.name.startswith(".")
        ):
            continue
        config_path = path / "run-config.json"
        if not config_path.is_file():
            failure_rows.append(
                {
                    "artifact_path": str(path),
                    "run_id": path.name,
                    "status": "incomplete",
                    "reason": "missing_run_config",
                    "returncode": "NA",
                    "timed_out": "NA",
                }
            )
            continue
        config = load_json(config_path)
        summary_path = path / "summary.json"
        complete_path = path / "run-complete.json"
        if complete_path.is_file() and summary_path.is_file():
            summary = load_json(summary_path)
            manifest_row = config.get("manifest_row", {})
            if not isinstance(manifest_row, dict):
                raise SystemExit(f"invalid manifest row in {config_path}")
            run_rows.append(
                {
                    "run_id": config.get("run_id", path.name),
                    "workload_id": config.get("workload_id", "NA"),
                    "role": manifest_row.get("role", "NA"),
                    "query_id": manifest_row.get("query_id", "NA"),
                    "query_length_nt": manifest_row.get("query_length_nt", "NA"),
                    "fragment_position": manifest_row.get("fragment_position", "NA"),
                    "target_id": manifest_row.get("target_id", "NA"),
                    "target_region": manifest_row.get("target_region", "NA"),
                    "pair_id": config.get("pair_id", "NA"),
                    "mode": config.get("mode", "NA"),
                    "warmup": int(bool(config.get("warmup"))),
                    "status": "complete",
                    "runtime_epoch": config.get("runtime_epoch", "NA"),
                    "config_digest_sha256": config.get("config_digest_sha256", "NA"),
                    "wall_seconds": summary.get("wall_seconds", "NA"),
                    "max_rss_kb": summary.get("max_rss_kb", "NA"),
                    "gpu_memory_peak_mib": summary.get("gpu_memory_peak_mib", "NA"),
                    "gpu_temperature_peak_c": summary.get("gpu_temperature_peak_c", "NA"),
                    "gpu_power_peak_w": summary.get("gpu_power_peak_w", "NA"),
                    "receipt_path": str(complete_path),
                }
            )
            if config.get("mode") == "preflight":
                correctness = load_json(path / "correctness.json")
                guard_rows.append(
                    {
                        "run_id": config.get("run_id", path.name),
                        "workload_id": config.get("workload_id", "NA"),
                        "query_id": manifest_row.get("query_id", "NA"),
                        "query_length_nt": manifest_row.get("query_length_nt", "NA"),
                        "target_id": manifest_row.get("target_id", "NA"),
                        "supported": int(bool(correctness.get("supported"))),
                        "reason": correctness.get("reason", "NA"),
                        "gpu_fast_path_executed": 0,
                        "status": correctness.get("status", "NA"),
                        "receipt_path": str(complete_path),
                    }
                )
        else:
            execution = load_json(path / "execution.json") if (path / "execution.json").is_file() else {}
            correctness = load_json(path / "correctness.json") if (path / "correctness.json").is_file() else {}
            failure_rows.append(
                {
                    "artifact_path": str(path),
                    "run_id": config.get("run_id", path.name),
                    "status": correctness.get("status", "failed"),
                    "reason": correctness.get("reason", "incomplete_receipt"),
                    "returncode": execution.get("returncode", "NA"),
                    "timed_out": execution.get("timed_out", "NA"),
                }
            )
    pair_rows: list[dict[str, object]] = []
    pairs_root = artifact_root / PAIR_ROOT_NAME
    if pairs_root.is_dir():
        for path in sorted(pairs_root.iterdir()):
            summary_path = path / "pair-summary.json"
            if path.is_dir() and summary_path.is_file() and (path / "pair-complete.json").is_file():
                summary = load_json(summary_path)
                summary["pair_summary_path"] = str(summary_path)
                summary["details_path"] = str(path / "top5-details.tsv")
                pair_rows.append(summary)
            elif path.is_dir() and ".failed." in path.name:
                config = load_json(path / "pair-config.json") if (path / "pair-config.json").is_file() else {}
                failure = load_json(path / "pair-failure.json") if (path / "pair-failure.json").is_file() else {}
                failure_rows.append(
                    {
                        "artifact_path": str(path),
                        "run_id": config.get("pair_id_text", path.name),
                        "status": failure.get("status", "technical_failure"),
                        "reason": failure.get("reason", "pair_comparator_failure"),
                        "returncode": "NA",
                        "timed_out": "NA",
                    }
                )
    atomic_tsv(artifact_root / "phase3-runs.tsv", RUN_FIELDS, run_rows)
    atomic_tsv(artifact_root / "phase3-pairs.tsv", PAIR_FIELDS, pair_rows)
    atomic_tsv(artifact_root / "phase3-guards.tsv", GUARD_FIELDS, guard_rows)
    atomic_tsv(artifact_root / "phase3-failures.tsv", FAILURE_FIELDS, failure_rows)
    artifact_rows: list[dict[str, object]] = []
    manifest_path = artifact_root / "phase3-artifacts.tsv"
    for path in sorted(artifact_root.rglob("*")):
        if path.is_file() and path != manifest_path:
            artifact_rows.append(
                {
                    "artifact_path": str(path.relative_to(artifact_root)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    atomic_tsv(manifest_path, ARTIFACT_FIELDS, artifact_rows)


def execute(
    rows: list[dict[str, str]],
    plan: dict[str, object],
    manifest: Path,
    binary: Path,
    artifact_root: Path,
    seed: int,
    resume: bool,
) -> tuple[int, int]:
    by_id = {row["workload_id"]: row for row in rows}
    pairs_by_workload: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pair in plan["pairs"]:  # type: ignore[index]
        pairs_by_workload[str(pair["workload_id"])].append(pair)
    completed = 0
    reused = 0
    try:
        for preflight in plan["preflights"]:  # type: ignore[index]
            row = by_id[str(preflight["workload_id"])]
            invoke_harness(
                manifest,
                binary,
                artifact_root,
                row,
                "preflight",
                seed,
                resume,
            )
        for row in rows:
            if row["role"] not in SUPPORTED_ROLES:
                continue
            for mode in ("baseline", "candidate"):
                invoke_harness(
                    manifest,
                    binary,
                    artifact_root,
                    row,
                    mode,
                    seed,
                    resume,
                    warmup=True,
                )
            for pair in sorted(
                pairs_by_workload[row["workload_id"]], key=lambda item: int(item["pair_id"])
            ):
                for mode in pair["modes"]:
                    invoke_harness(
                        manifest,
                        binary,
                        artifact_root,
                        row,
                        str(mode),
                        seed,
                        resume,
                        pair_id=int(pair["pair_id"]),
                    )
                print(
                    f"phase3_compare_start={row['workload_id']} pair {pair['pair_id']}",
                    file=sys.stderr,
                    flush=True,
                )
                status = publish_pair(row, pair, artifact_root, resume)
                print(
                    f"phase3_compare_done={row['workload_id']} pair {pair['pair_id']} status={status}",
                    file=sys.stderr,
                    flush=True,
                )
                if status == "completed":
                    completed += 1
                else:
                    reused += 1
    finally:
        rebuild_tables(artifact_root)
    return completed, reused


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "paper/workload_manifest.tsv")
    parser.add_argument("--binary", type=Path, default=ROOT / ".tmp/fasim_longtarget_gasal2_direct")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization",
    )
    parser.add_argument("--workload-id", action="append")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not args.binary.is_file():
        raise SystemExit(f"missing paper benchmark binary: {args.binary}")
    rows = load_phase3_rows(args.manifest)
    if args.workload_id:
        selected = set(args.workload_id)
        unknown = selected - {row["workload_id"] for row in rows}
        if unknown:
            raise SystemExit("unknown Phase 3 workload IDs: " + ",".join(sorted(unknown)))
        rows = [row for row in rows if row["workload_id"] in selected]
    plan = build_phase3_plan(rows, args.manifest, args.binary, args.seed)
    if args.dry_run:
        json.dump(plan, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    completed, reused = execute(
        rows,
        plan,
        args.manifest,
        args.binary,
        args.artifact_root,
        args.seed,
        args.resume,
    )
    print(f"completed_pairs={completed}")
    print(f"reused_pairs={reused}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
