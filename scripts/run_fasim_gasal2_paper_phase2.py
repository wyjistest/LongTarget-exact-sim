#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "run_fasim_gasal2_paper_benchmarks.sh"
TOPK_INTEGRITY = ROOT / "scripts" / "check_topk_summary_digest_integrity.py"
LITE_COMPARATOR = ROOT / "scripts" / "compare_fasim_lite_topk.py"
LONG_COMPARATOR = ROOT / "scripts" / "compare_fasim_gasal2_long_query_integrated.py"
RUNTIME_EPOCH = 0
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
SEED = 20260715
COMPARATOR_VERSION = 3
PAIR_ROOT_NAME = "pairs-v3"
PHASE2_WORKLOAD_IDS = (
    "c1_h19_chr21_chr22_fast_topk",
    "c4_h19_chr21_two_slot",
    "c4_h19_chr22_two_slot",
    "c7_kcnq_max8_chr22",
)


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


def atomic_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
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
            fieldnames=fieldnames,
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


def load_rows(manifest: Path, selected_ids: list[str]) -> list[dict[str, str]]:
    rows = read_tsv(manifest)
    by_id = {row["workload_id"]: row for row in rows}
    missing = [workload_id for workload_id in selected_ids if workload_id not in by_id]
    if missing:
        raise SystemExit("unknown Phase 2 workload IDs: " + ",".join(missing))
    selected = [by_id[workload_id] for workload_id in selected_ids]
    if os.environ.get("FASIM_PAPER_HARNESS_TEST_MODE") != "1":
        unexpected = set(selected_ids) - set(PHASE2_WORKLOAD_IDS)
        if unexpected:
            raise SystemExit("non-core workload requested outside test mode: " + ",".join(sorted(unexpected)))
    return selected


def harness_plan(manifest: Path, binary: Path, workload_id: str, seed: int) -> dict[str, object]:
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
    return json.loads(result.stdout)


def build_phase2_plan(
    rows: list[dict[str, str]], manifest: Path, binary: Path, seed: int
) -> dict[str, object]:
    workloads: list[dict[str, object]] = []
    pairs: list[dict[str, object]] = []
    warmups: list[dict[str, object]] = []
    timed_run_count = 0
    for row in rows:
        plan = harness_plan(manifest, binary, row["workload_id"], seed)
        runs = plan.get("runs")
        planned_warmups = plan.get("warmups")
        if not isinstance(runs, list) or not isinstance(planned_warmups, list):
            raise SystemExit(f"invalid harness plan for {row['workload_id']}")
        grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
        for run in runs:
            pair_id = int(run["pair_id"])
            if pair_id <= 0:
                raise SystemExit(f"Phase 2 workload cannot be preflight-only: {row['workload_id']}")
            grouped[pair_id].append(run)
        if len(grouped) != int(row["required_pairs"]):
            raise SystemExit(f"pair expansion mismatch for {row['workload_id']}")
        for pair_id, pair_runs in sorted(grouped.items()):
            ordered = sorted(pair_runs, key=lambda run: int(run["order_index"]))
            if [run["mode"] for run in ordered] not in (
                ["baseline", "candidate"],
                ["candidate", "baseline"],
            ):
                raise SystemExit(f"invalid paired order for {row['workload_id']} pair {pair_id}")
            pairs.append(
                {
                    "workload_id": row["workload_id"],
                    "pair_id": pair_id,
                    "pair_order": ordered[0]["pair_order"],
                    "modes": [run["mode"] for run in ordered],
                    "run_ids": [run["run_id"] for run in ordered],
                }
            )
        warmups.extend(planned_warmups)
        timed_run_count += len(runs)
        workloads.append(
            {
                "workload_id": row["workload_id"],
                "claim_id": row["claim_id"],
                "required_pairs": int(row["required_pairs"]),
                "requires_gpu_count": int(row["requires_gpu_count"]),
                "adapter_id": row["adapter_id"],
            }
        )
    return {
        "schema_version": 1,
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "seed": seed,
        "workload_count": len(rows),
        "pair_count": len(pairs),
        "timed_run_count": timed_run_count,
        "warmup_count": len(warmups),
        "workloads": workloads,
        "warmups": warmups,
        "pairs": pairs,
    }


def visible_gpu_ids(required: int) -> list[str]:
    if required == 0:
        return []
    if os.environ.get("FASIM_PAPER_HARNESS_TEST_MODE") == "1":
        available = int(os.environ.get("FASIM_PAPER_TEST_GPU_COUNT", "0"))
        ids = [str(index) for index in range(available)]
    else:
        configured = os.environ.get("CUDA_VISIBLE_DEVICES")
        if configured is not None:
            ids = [value.strip() for value in configured.split(",") if value.strip() not in ("", "-1")]
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
    pair_id: int | None = None,
    warmup: bool = False,
) -> dict[str, object]:
    run_label = (
        f"{row['workload_id']} warmup {mode}"
        if warmup
        else f"{row['workload_id']} pair {pair_id} {mode}"
    )
    print(f"phase2_run_start={run_label}", file=sys.stderr, flush=True)
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
    elif pair_id is not None:
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
        message = result.stderr.strip() or result.stdout.strip() or "paper harness run failed"
        raise SystemExit(message)
    payload = json.loads(result.stdout)
    print(
        f"phase2_run_done={run_label} status={payload.get('status', 'unknown')}",
        file=sys.stderr,
        flush=True,
    )
    return payload


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
        for key, value in parse_key_values(path.read_text(encoding="utf-8", errors="replace")).items()
        if key.startswith("benchmark.")
    }


def bool_int(value: object) -> int:
    return int(value is True or str(value).lower() in {"1", "true", "yes"})


def base_result() -> dict[str, object]:
    return {
        "top5_score_equal": 0,
        "top5_stability_equal": 0,
        "top5_nt_score_equal": 0,
        "full_output_byte_equal": "NA",
        "missing_rows": "NA",
        "extra_rows": "NA",
        "fallbacks": "NA",
        "oom": "NA",
        "status": "mismatch",
        "decision": "contract_mismatch",
    }


def compare_synthetic(baseline: Path, candidate: Path, work: Path) -> dict[str, object]:
    baseline_result = baseline / "output" / "result.txt"
    candidate_result = candidate / "output" / "result.txt"
    equal = baseline_result.read_bytes() == candidate_result.read_bytes()
    result = base_result()
    result.update(
        {
            "top5_score_equal": int(equal),
            "top5_stability_equal": int(equal),
            "top5_nt_score_equal": int(equal),
            "full_output_byte_equal": int(equal),
            "missing_rows": 0 if equal else "NA",
            "extra_rows": 0 if equal else "NA",
            "fallbacks": 0,
            "oom": 0,
            "status": "clean" if equal else "mismatch",
            "decision": "synthetic_contract_clean" if equal else "synthetic_contract_mismatch",
        }
    )
    (work / "comparator.txt").write_text(f"byte_equal={str(equal).lower()}\n", encoding="utf-8")
    return result


def write_relocated_topk_report(
    report_path: Path,
    run_dir: Path,
    destination: Path,
) -> Path:
    report = load_json(report_path)
    output_dir = run_dir / "output"
    for field in (
        "topk_summary_output",
        "topk_rows_output",
        "topk_lite_output",
    ):
        recorded = report.get(field)
        if not isinstance(recorded, str) or not recorded:
            raise SystemExit(f"missing top-K artifact path field: {field}")
        published = output_dir / Path(recorded).name
        if not published.is_file():
            raise SystemExit(f"missing published top-K artifact for {field}: {published}")
        report[field] = str(published)
    atomic_json(destination, report)
    return destination


def compare_formal_topk(baseline: Path, candidate: Path, work: Path) -> dict[str, object]:
    baseline_report_path = baseline / "output" / "report.json"
    candidate_report_path = candidate / "output" / "report.json"
    baseline_integrity_report = write_relocated_topk_report(
        baseline_report_path,
        baseline,
        work / "baseline-report-relocated.json",
    )
    candidate_integrity_report = write_relocated_topk_report(
        candidate_report_path,
        candidate,
        work / "candidate-report-relocated.json",
    )
    command = [
        sys.executable,
        str(TOPK_INTEGRITY),
        "--report",
        str(candidate_integrity_report),
        "--same-payload-as",
        str(baseline_integrity_report),
    ]
    check = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (work / "comparator.stdout.log").write_text(check.stdout, encoding="utf-8")
    (work / "comparator.stderr.log").write_text(check.stderr, encoding="utf-8")
    baseline_report = load_json(baseline_report_path)
    candidate_report = load_json(candidate_report_path)
    baseline_modes = baseline_report.get("topk_summary", {}).get("modes", {})
    candidate_modes = candidate_report.get("topk_summary", {}).get("modes", {})
    score = candidate_modes.get("score") == baseline_modes.get("score")
    stability = candidate_modes.get("stability") == baseline_modes.get("stability")
    nt_score = candidate_modes.get("nt_score") == baseline_modes.get("nt_score")
    sums = candidate_report.get("fasim_benchmark_sums", {})
    shard_count = int(candidate_report.get("shard_count", 0) or 0)
    requested = int(sums.get("fasim_top5_gasal2_gpu_scoreinfo_requested", 0) or 0)
    active = int(sums.get("fasim_top5_gasal2_gpu_scoreinfo_active", 0) or 0)
    fallbacks = int(sums.get("fasim_gasal2_fallbacks", 0) or 0)
    length_guards = int(sums.get("fasim_gasal2_length_guard_fallbacks", 0) or 0)
    overflow = int(sums.get("fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches", 0) or 0)
    fallback_batches = int(sums.get("fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches", 0) or 0)
    active_path = shard_count == 2 and requested == shard_count and active == shard_count
    clean = (
        check.returncode == 0
        and score
        and stability
        and nt_score
        and active_path
        and fallbacks == 0
        and length_guards == 0
        and overflow == 0
        and fallback_batches == 0
        and candidate_report.get("worker_count") == 2
        and candidate_report.get("gpu_ids") == ["0", "1"]
    )
    result = base_result()
    result.update(
        {
            "top5_score_equal": int(score),
            "top5_stability_equal": int(stability),
            "top5_nt_score_equal": int(nt_score),
            "fallbacks": fallbacks + length_guards + fallback_batches,
            "oom": 0,
            "status": "clean" if clean else "mismatch",
            "decision": "formal_topk_contract_clean" if clean else "formal_topk_contract_mismatch",
            "candidate_active_path": int(active_path),
            "candidate_overflow_batches": overflow,
            "candidate_worker_count": candidate_report.get("worker_count", "NA"),
            "candidate_gpu_ids": ",".join(candidate_report.get("gpu_ids", [])),
        }
    )
    return result


def find_one_lite(run_dir: Path) -> Path:
    matches = sorted((run_dir / "output").glob("*-TFOsorted.lite"))
    if len(matches) != 1:
        raise SystemExit(f"expected one lite output in {run_dir}, found {len(matches)}")
    return matches[0]


def metric_int(metrics: dict[str, str], key: str) -> int:
    try:
        return int(float(metrics.get(key, "0") or "0"))
    except ValueError as exc:
        raise SystemExit(f"invalid benchmark counter {key}") from exc


def metric_float(metrics: dict[str, str], key: str) -> float:
    try:
        return float(metrics.get(key, "0") or "0")
    except ValueError as exc:
        raise SystemExit(f"invalid benchmark value {key}") from exc


def compare_two_slot(baseline: Path, candidate: Path, work: Path) -> dict[str, object]:
    command = [
        sys.executable,
        str(LITE_COMPARATOR),
        "--baseline",
        str(find_one_lite(baseline)),
        "--candidate",
        str(find_one_lite(candidate)),
        "--k",
        "5",
    ]
    compare = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (work / "comparator.stdout.log").write_text(compare.stdout, encoding="utf-8")
    (work / "comparator.stderr.log").write_text(compare.stderr, encoding="utf-8")
    values = parse_key_values(compare.stdout)
    metrics = benchmark_metrics(candidate / "stderr.log")
    prefix = "fasim_gasal2_flush_two_slot_overlap_"
    submitted = metric_int(metrics, prefix + "flushes_gpu_submitted")
    finalized = metric_int(metrics, prefix + "flushes_finalized")
    committed = metric_int(metrics, prefix + "flushes_committed")
    fallbacks = metric_int(metrics, "fasim_gasal2_fallbacks") + metric_int(
        metrics, prefix + "legacy_fallback_flushes"
    )
    violations = (
        metric_int(metrics, prefix + "state_transition_violations")
        + metric_int(metrics, prefix + "order_violations")
        + metric_int(metrics, prefix + "allocation_failures")
    )
    lifecycle_clean = submitted > 0 and submitted == finalized == committed
    slot_rotation_clean = (
        metric_int(metrics, prefix + "slot0_submit_count") > 0
        and metric_int(metrics, prefix + "slot1_submit_count") > 0
    )
    active_clean = (
        metric_int(metrics, prefix + "requested") == 1
        and metric_int(metrics, prefix + "active") == 1
        and metrics.get(prefix + "decision") == "two_slot_active_clean_no_fallback"
    )
    host_overlap = metric_float(metrics, prefix + "host_scheduling_overlap_seconds")
    score = values.get("top5_score_equal") == "true"
    stability = values.get("top5_stability_equal") == "true"
    nt_score = values.get("top5_nt_score_equal") == "true"
    clean = (
        compare.returncode == 0
        and score
        and stability
        and nt_score
        and lifecycle_clean
        and slot_rotation_clean
        and active_clean
        and host_overlap > 0
        and fallbacks == 0
        and violations == 0
    )
    result = base_result()
    result.update(
        {
            "top5_score_equal": int(score),
            "top5_stability_equal": int(stability),
            "top5_nt_score_equal": int(nt_score),
            "missing_rows": values.get("missing_rows", "NA"),
            "extra_rows": values.get("extra_rows", "NA"),
            "fallbacks": fallbacks,
            "oom": 0,
            "status": "clean" if clean else "mismatch",
            "decision": "two_slot_contract_clean" if clean else "two_slot_contract_mismatch",
            "candidate_lifecycle_count": submitted,
            "candidate_max_live_slots": metric_int(metrics, prefix + "max_live_slots"),
            "candidate_slot_rotation_clean": int(slot_rotation_clean),
            "candidate_host_overlap_seconds": host_overlap,
            "candidate_state_order_allocation_violations": violations,
        }
    )
    return result


def compare_segmented_max8(baseline: Path, candidate: Path, work: Path) -> dict[str, object]:
    pair_tsv = work / "pair.tsv"
    command = [
        sys.executable,
        str(LONG_COMPARATOR),
        "--workload",
        "max8",
        "--repeat",
        "1",
        "--baseline-root",
        str(baseline / "output"),
        "--candidate-root",
        str(candidate / "output"),
        "--work-dir",
        str(work / "contracts"),
        "--output",
        str(pair_tsv),
        "--allow-relocated-input-paths",
    ]
    compare = subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (work / "comparator.stdout.log").write_text(compare.stdout, encoding="utf-8")
    (work / "comparator.stderr.log").write_text(compare.stderr, encoding="utf-8")
    if not pair_tsv.is_file():
        raise SystemExit(f"segmented max8 comparator did not produce {pair_tsv}")
    rows = read_tsv(pair_tsv)
    if len(rows) != 1:
        raise SystemExit("segmented max8 comparator must produce one pair row")
    row = rows[0]
    score = row["top5_score_equal"] == "1"
    stability = row["top5_stability_equal"] == "1"
    nt_score = row["top5_nt_score_equal"] == "1"
    fallbacks = int(row["fallbacks"])
    oom = int(row["oom"])
    clean = (
        compare.returncode == 0
        and row["decision"] == "paired_integrated_contract_clean"
        and row["exact_work_equal"] == "1"
        and row["full_output_byte_equal"] == "1"
        and row["missing_rows"] == "0"
        and row["extra_rows"] == "0"
        and score
        and stability
        and nt_score
        and row["offline_clustered_top5_equal"] == "1"
        and row["archive_restore_clean"] == "1"
        and fallbacks == 0
        and oom == 0
    )
    result = base_result()
    result.update(
        {
            "top5_score_equal": int(score),
            "top5_stability_equal": int(stability),
            "top5_nt_score_equal": int(nt_score),
            "full_output_byte_equal": row["full_output_byte_equal"],
            "missing_rows": row["missing_rows"],
            "extra_rows": row["extra_rows"],
            "fallbacks": fallbacks,
            "oom": oom,
            "status": "clean" if clean else "mismatch",
            "decision": row["decision"],
            "archive_restore_clean": row["archive_restore_clean"],
            "exact_work_equal": row["exact_work_equal"],
        }
    )
    return result


def compare_pair(row: dict[str, str], baseline: Path, candidate: Path, work: Path) -> dict[str, object]:
    adapter = row["adapter_id"]
    if adapter == "synthetic_test":
        return compare_synthetic(baseline, candidate, work)
    if adapter == "formal_topk_sharded":
        return compare_formal_topk(baseline, candidate, work)
    if adapter == "direct_two_slot":
        return compare_two_slot(baseline, candidate, work)
    if adapter == "segmented_max8":
        return compare_segmented_max8(baseline, candidate, work)
    raise SystemExit(f"unsupported Phase 2 pair comparator for adapter {adapter}")


def pair_id_text(workload_id: str, pair_id: int) -> str:
    return f"{workload_id}__pair{pair_id:02d}__{RUNTIME_EPOCH}"


def publish_pair(
    row: dict[str, str], pair: dict[str, object], artifact_root: Path, resume: bool
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
        "pair_id": pair_id,
        "pair_order": pair["pair_order"],
        "runtime_epoch": RUNTIME_EPOCH,
        "runtime_commit": RUNTIME_COMMIT,
        "output_contract": row["output_contract"],
        "adapter_id": row["adapter_id"],
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
        complete = load_json(complete_path)
        existing_config = load_json(destination / "pair-config.json")
        if (
            existing_config.get("baseline_receipt_sha256") != component_digests["baseline"]
            or existing_config.get("candidate_receipt_sha256") != component_digests["candidate"]
        ):
            raise SystemExit(f"pair component receipt digest mismatch: {destination}")
        if existing_config.get("config_digest_sha256") != config["config_digest_sha256"]:
            raise SystemExit(f"pair config digest mismatch: {destination}")
        if not resume:
            raise SystemExit(f"duplicate pair ID: {destination.name}")
        summary_path = destination / "pair-summary.json"
        if complete.get("summary_sha256") != sha256(summary_path):
            raise SystemExit(f"pair summary digest mismatch: {destination}")
        return "reused"

    temporary = artifact_root / PAIR_ROOT_NAME / f".{destination.name}.partial.{os.getpid()}"
    if temporary.exists():
        raise SystemExit(f"pair temporary path already exists: {temporary}")
    temporary.mkdir(parents=True)
    atomic_json(temporary / "pair-config.json", config)
    try:
        comparison = compare_pair(row, baseline, candidate, temporary)
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
        "schema_version": 1,
        **config,
        **comparison,
        "baseline_wall_seconds": baseline_wall,
        "candidate_wall_seconds": candidate_wall,
        "paired_speedup": baseline_wall / candidate_wall if candidate_wall else "NA",
        "baseline_max_rss_kb": baseline_summary.get("max_rss_kb", "NA"),
        "candidate_max_rss_kb": candidate_summary.get("max_rss_kb", "NA"),
        "baseline_gpu_memory_peak_mib": baseline_summary.get("gpu_memory_peak_mib", "NA"),
        "candidate_gpu_memory_peak_mib": candidate_summary.get("gpu_memory_peak_mib", "NA"),
        "baseline_gpu_temperature_peak_c": baseline_summary.get("gpu_temperature_peak_c", "NA"),
        "candidate_gpu_temperature_peak_c": candidate_summary.get("gpu_temperature_peak_c", "NA"),
        "baseline_gpu_power_peak_w": baseline_summary.get("gpu_power_peak_w", "NA"),
        "candidate_gpu_power_peak_w": candidate_summary.get("gpu_power_peak_w", "NA"),
    }
    atomic_json(temporary / "pair-summary.json", summary)
    complete = {
        "schema_version": 1,
        "status": "complete",
        "pair_id_text": destination.name,
        "config_digest_sha256": config["config_digest_sha256"],
        "summary_sha256": sha256(temporary / "pair-summary.json"),
    }
    atomic_json(temporary / "pair-complete.json", complete)
    os.replace(temporary, destination)
    return "completed"


RUN_FIELDS = [
    "run_id",
    "workload_id",
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
    "baseline_gpu_temperature_peak_c",
    "candidate_gpu_temperature_peak_c",
    "baseline_gpu_power_peak_w",
    "candidate_gpu_power_peak_w",
    "candidate_active_path",
    "candidate_overflow_batches",
    "candidate_worker_count",
    "candidate_gpu_ids",
    "candidate_lifecycle_count",
    "candidate_max_live_slots",
    "candidate_slot_rotation_clean",
    "candidate_host_overlap_seconds",
    "candidate_state_order_allocation_violations",
    "archive_restore_clean",
    "exact_work_equal",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "full_output_byte_equal",
    "missing_rows",
    "extra_rows",
    "fallbacks",
    "oom",
    "status",
    "decision",
    "pair_summary_path",
]
FAILURE_FIELDS = ["artifact_path", "run_id", "status", "reason", "returncode", "timed_out"]
ARTIFACT_FIELDS = ["artifact_path", "size_bytes", "sha256"]


def rebuild_tables(artifact_root: Path) -> None:
    artifact_root.mkdir(parents=True, exist_ok=True)
    run_rows: list[dict[str, object]] = []
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
        complete = path / "run-complete.json"
        summary_path = path / "summary.json"
        if complete.is_file() and summary_path.is_file():
            summary = load_json(summary_path)
            run_rows.append(
                {
                    "run_id": config.get("run_id", path.name),
                    "workload_id": config.get("workload_id", "NA"),
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
                    "receipt_path": str(complete),
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
                pair_rows.append(summary)
    historical_pair_roots = sorted(
        path
        for path in artifact_root.iterdir()
        if path.is_dir() and (path.name == "pairs" or path.name.startswith("pairs-v"))
    )
    for historical_root in historical_pair_roots:
        for path in sorted(historical_root.iterdir()):
            if not path.is_dir():
                continue
            if historical_root != pairs_root:
                summary_path = path / "pair-summary.json"
                complete_path = path / "pair-complete.json"
                if summary_path.is_file() and complete_path.is_file():
                    historical_summary = load_json(summary_path)
                    if historical_summary.get("status") != "clean":
                        failure_rows.append(
                            {
                                "artifact_path": str(path),
                                "run_id": historical_summary.get("pair_id_text", path.name),
                                "status": historical_summary.get("status", "mismatch"),
                                "reason": "superseded_derived_pair",
                                "returncode": "NA",
                                "timed_out": "NA",
                            }
                        )
            if ".failed." in path.name:
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
    atomic_tsv(artifact_root / "phase2-runs.tsv", RUN_FIELDS, run_rows)
    atomic_tsv(artifact_root / "phase2-pairs.tsv", PAIR_FIELDS, pair_rows)
    atomic_tsv(artifact_root / "phase2-failures.tsv", FAILURE_FIELDS, failure_rows)

    artifact_rows: list[dict[str, object]] = []
    manifest_path = artifact_root / "phase2-artifacts.tsv"
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
    completed_pairs = 0
    reused_pairs = 0
    pairs_by_workload: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pair in plan["pairs"]:  # type: ignore[index]
        pairs_by_workload[str(pair["workload_id"])].append(pair)
    try:
        for row in rows:
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
            for pair in sorted(pairs_by_workload[row["workload_id"]], key=lambda item: int(item["pair_id"])):
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
                    f"phase2_compare_start={row['workload_id']} pair {pair['pair_id']}",
                    file=sys.stderr,
                    flush=True,
                )
                status = publish_pair(row, pair, artifact_root, resume)
                print(
                    f"phase2_compare_done={row['workload_id']} pair {pair['pair_id']} status={status}",
                    file=sys.stderr,
                    flush=True,
                )
                if status == "completed":
                    completed_pairs += 1
                else:
                    reused_pairs += 1
    finally:
        rebuild_tables(artifact_root)
    return completed_pairs, reused_pairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "paper/workload_manifest.tsv")
    parser.add_argument("--binary", type=Path, default=ROOT / ".tmp/fasim_longtarget_gasal2_direct")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core",
    )
    parser.add_argument("--workload-id", action="append")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if not args.binary.is_file():
        raise SystemExit(f"missing paper benchmark binary: {args.binary}")
    selected_ids = args.workload_id or list(PHASE2_WORKLOAD_IDS)
    rows = load_rows(args.manifest, selected_ids)
    plan = build_phase2_plan(rows, args.manifest, args.binary, args.seed)
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
