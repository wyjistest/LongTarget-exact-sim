#!/usr/bin/env python3
import argparse
import csv
import json
import shutil
import sys
import time
from pathlib import Path

import fasim_sharded_runner as runner


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


RAW_FIELDS = [
    "workload",
    "target_record_count",
    "target_bases",
    "group_size",
    "grouped_shard_count",
    "worker_count",
    "wall_seconds",
    "runner_total_seconds",
    "single_seconds",
    "speedup_vs_group_size_1",
    "speedup_vs_single_whole_run",
    "digest_match",
    "merged_records",
    "duplicate_removed",
    "per_worker_seconds",
    "per_worker_shards",
    "per_shard_records",
    "per_shard_seconds",
    "prealign_cuda_fallbacks",
    "prealign_cuda_fallback_delta_vs_group_size_1",
    "prealign_cuda_tasks",
    "prealign_cuda_batches",
    "profile_cache_active",
    "profile_cache_calls",
    "profile_cache_hits",
    "profile_cache_misses",
    "profile_cache_hit_rate",
    "extend_seconds",
    "output_seconds",
    "imbalance_ratio",
    "report_path",
]


def _parse_csv_ints(spec: str, *, flag: str) -> list[int]:
    values: list[int] = []
    for raw in spec.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            value = int(item)
        except ValueError as exc:
            raise RuntimeError(f"invalid {flag} entry: {item}") from exc
        if value < 1:
            raise RuntimeError(f"{flag} entries must be >= 1: {item}")
        values.append(value)
    if not values:
        raise RuntimeError(f"{flag} must not be empty")
    return sorted(set(values))


def _parse_csv(spec: str | None, *, flag: str) -> list[str]:
    if spec is None or not spec.strip():
        return []
    values = [item.strip() for item in spec.split(",")]
    if any(not value for value in values):
        raise RuntimeError(f"{flag} must not include empty entries")
    return values


def _parse_workload(spec: str) -> dict[str, object]:
    parts = spec.split(":", 3)
    if len(parts) != 4:
        raise RuntimeError(
            "--workload must be NAME:TARGET_FASTA:RNA_FASTA:RULE, got: " + spec
        )
    name, target, rna, rule = parts
    if not name.strip():
        raise RuntimeError("--workload name must not be empty")
    target_path = Path(target).resolve()
    rna_path = Path(rna).resolve()
    if not target_path.exists():
        raise RuntimeError(f"missing target FASTA: {target_path}")
    if not rna_path.exists():
        raise RuntimeError(f"missing RNA FASTA: {rna_path}")
    return {
        "name": name.strip(),
        "target": str(target_path),
        "rna": str(rna_path),
        "rule": rule,
    }


def _sanitize_name(name: object) -> str:
    text = str(name)
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)
    cleaned = cleaned.strip("._-")
    return cleaned or "item"


def _num(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return default


def _int(value: object, default: int = 0) -> int:
    return int(_num(value, float(default)))


def _safe_ratio(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _format_seconds_list(values: list[object]) -> str:
    return ",".join(f"{_num(value):.6f}" for value in values)


def _format_int_list(values: list[object]) -> str:
    return ",".join(str(_int(value)) for value in values)


def _records_bases(records: list[runner.FastaRecord]) -> int:
    return sum(len(record.sequence) for record in records)


def read_fasta(path: Path) -> list[runner.FastaRecord]:
    return runner._read_fasta(path)


def write_grouped_fasta(
    *,
    records: list[runner.FastaRecord],
    group_size: int,
    output_dir: Path,
    workload_name: str,
) -> tuple[Path, dict[str, object]]:
    if group_size < 1:
        raise RuntimeError("group_size must be >= 1")
    if not records:
        raise RuntimeError("cannot group an empty FASTA")

    output_dir.mkdir(parents=True, exist_ok=True)
    grouped_target_path = output_dir / (
        f"{_sanitize_name(workload_name)}.group_size_{group_size}.fa"
    )
    shard_dir = output_dir / "shards"
    shard_dir.mkdir(parents=True, exist_ok=True)

    groups: list[dict[str, object]] = []
    with grouped_target_path.open("w", encoding="utf-8") as combined:
        for group_idx, start in enumerate(range(0, len(records), group_size)):
            members = records[start : start + group_size]
            group_id = f"group_{group_idx:04d}"
            group_path = shard_dir / f"{group_id}.fa"
            with group_path.open("w", encoding="utf-8") as group_file:
                for record in members:
                    entry = f"{record.header}\n{runner._wrap_sequence(record.sequence)}\n"
                    group_file.write(entry)
                    combined.write(entry)
            groups.append(
                {
                    "group_id": group_id,
                    "group_fasta_path": str(group_path),
                    "member_indices": list(range(start, start + len(members))),
                    "record_count": len(members),
                    "record_headers": [record.header for record in members],
                    "sequence_bases": _records_bases(members),
                    "group_fasta_digest": runner._sha256_file(group_path),
                }
            )

    group_plan = {
        "schema_version": 1,
        "mode": "fasim_shard_coalescing_group_plan",
        "workload": workload_name,
        "group_size": group_size,
        "target_record_count": len(records),
        "target_bases": _records_bases(records),
        "grouped_shard_count": len(groups),
        "grouped_target_path": str(grouped_target_path),
        "grouped_target_digest": runner._sha256_file(grouped_target_path),
        "groups": groups,
    }
    _write_json(output_dir / "group_plan.json", group_plan)
    return grouped_target_path, group_plan


def _group_plan_to_shards(group_plan: dict[str, object]) -> list[runner.Shard]:
    shards: list[runner.Shard] = []
    groups = group_plan.get("groups")
    if not isinstance(groups, list):
        raise RuntimeError("group plan has no groups")
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group["group_id"])
        group_path = Path(str(group["group_fasta_path"]))
        shards.append(
            runner.Shard(
                shard_id=group_id,
                target_name=group_id,
                target_start=1,
                target_end=_int(group.get("sequence_bases")),
                shard_fasta_path=group_path,
                estimated_length=_int(group.get("sequence_bases")),
                estimated_windows=None,
                estimated_cells=None,
            )
        )
    return shards


def _aggregate_worker_telemetry(run: dict[str, object]) -> dict[str, object]:
    telemetry = run.get("sharded_telemetry")
    if isinstance(telemetry, dict):
        return telemetry
    per_worker = run.get("per_worker")
    if not isinstance(per_worker, list):
        return {}
    return runner._sum_fasim_telemetry(
        [
            worker.get("telemetry")
            for worker in per_worker
            if isinstance(worker, dict) and isinstance(worker.get("telemetry"), dict)
        ]
    )


def _imbalance_ratio(per_worker_seconds: list[object]) -> float:
    active = [_num(value) for value in per_worker_seconds if _num(value) > 0.0]
    if not active:
        return 0.0
    return max(active) / (sum(active) / len(active))


def _worker_wall(per_worker: list[dict[str, object]]) -> float:
    return max((_num(worker.get("wall_seconds")) for worker in per_worker), default=0.0)


def _run_single_reference(
    *,
    workload: dict[str, object],
    args: argparse.Namespace,
    env_overrides: dict[str, str],
    gpu_ids: list[str],
    work_dir: Path,
) -> tuple[runner.CanonicalOutput, dict[str, object]]:
    single_env = dict(env_overrides)
    if gpu_ids:
        single_env["CUDA_VISIBLE_DEVICES"] = gpu_ids[0]
        single_env["FASIM_CUDA_DEVICE"] = "0"
        single_env.pop("FASIM_CUDA_DEVICES", None)

    run = runner._run_fasim(
        label="single_reference",
        fasim_bin=args.fasim_bin,
        target=Path(str(workload["target"])),
        rna=Path(str(workload["rna"])),
        rule=str(workload["rule"]),
        output_mode=args.output_mode,
        output_dir=work_dir / "single_reference_output",
        log_dir=work_dir / "logs",
        env_overrides=single_env,
        fasim_args=args.fasim_arg,
    )
    if run.output_path is None:
        raise RuntimeError("single reference completed without output")
    canonical = runner._canonicalize_file(run.output_path, args.output_mode)
    return canonical, runner._run_to_json(run)


def _run_grouped_worker_count(
    *,
    workload: dict[str, object],
    group_plan: dict[str, object],
    worker_count: int,
    args: argparse.Namespace,
    env_overrides: dict[str, str],
    gpu_ids: list[str],
    explicit_cpu_core_ranges: list[str],
    single_reference: runner.CanonicalOutput,
    single_run_json: dict[str, object],
    run_dir: Path,
) -> dict[str, object]:
    shards = _group_plan_to_shards(group_plan)
    cpu_core_ranges = runner._resolve_cpu_core_ranges(
        explicit_cpu_core_ranges=explicit_cpu_core_ranges[:worker_count],
        auto_cpu_core_ranges=bool(args.auto_cpu_core_ranges),
        cpu_pool=args.cpu_pool,
        cpu_cores_per_worker=args.cpu_cores_per_worker,
        worker_count=worker_count,
    )
    assignments = runner._assign_shards_to_workers(
        shards,
        worker_count=worker_count,
        gpu_ids=gpu_ids,
        cpu_core_ranges=cpu_core_ranges,
    )

    run_config_digest = runner._json_digest(
        {
            "mode": "fasim_shard_coalescing_characterization",
            "workload": workload,
            "group_plan_digest": runner._json_digest(group_plan),
            "worker_count": worker_count,
            "gpu_ids": gpu_ids,
            "cpu_core_ranges": cpu_core_ranges,
            "env_overrides": env_overrides,
            "output_mode": args.output_mode,
            "fasim_args": args.fasim_arg,
        }
    )

    start = time.perf_counter()
    worker_results = runner._run_scheduled_shards(
        assignments=assignments,
        fasim_bin=args.fasim_bin,
        rna=Path(str(workload["rna"])),
        rule=str(workload["rule"]),
        output_mode=args.output_mode,
        work_dir=run_dir,
        env_overrides=env_overrides,
        fasim_args=args.fasim_arg,
        resume_entries={},
        run_config_digest=run_config_digest,
        manifest=None,
        resume=False,
        keep_going=False,
    )
    runner_total_seconds = time.perf_counter() - start

    shard_order = {shard.shard_id: idx for idx, shard in enumerate(shards)}
    scheduled_results = [
        shard_result
        for worker_result in worker_results
        for shard_result in worker_result.shard_results
    ]
    scheduled_results.sort(key=lambda result: shard_order[result.shard_id])

    per_shard: list[dict[str, object]] = []
    shard_output_paths: list[Path] = []
    sharded_raw_records = 0
    sharded_unique_records = 0
    for shard_result in scheduled_results:
        per_shard.append(shard_result.report)
        if shard_result.output_path is not None:
            shard_output_paths.append(shard_result.output_path)
        sharded_raw_records += shard_result.raw_records
        sharded_unique_records += shard_result.unique_records

    merged_output_path = run_dir / "merged" / (
        "merged-TFOsorted.lite" if args.output_mode == "lite" else "merged-TFOsorted"
    )
    merged = runner._merge_outputs(shard_output_paths, args.output_mode, merged_output_path)
    per_worker = [
        {
            "worker_id": result.worker_id,
            "gpu_id": result.gpu_id,
            "cpu_core_range": result.cpu_core_range,
            "shard_ids": [shard_result.shard_id for shard_result in result.shard_results],
            "estimated_length": result.estimated_length,
            "estimated_cells": result.estimated_cells,
            "wall_seconds": result.wall_seconds,
            "records": sum(
                shard_result.unique_records
                for shard_result in result.shard_results
                if shard_result.status != "failed"
            ),
            "raw_records": sum(
                shard_result.raw_records
                for shard_result in result.shard_results
                if shard_result.status != "failed"
            ),
            "telemetry": runner._worker_telemetry_from_shards(
                [shard_result.report for shard_result in result.shard_results]
            ),
        }
        for result in worker_results
    ]
    sharded_telemetry = runner._sum_fasim_telemetry(
        [
            telemetry
            for shard_report in per_shard
            for run in [shard_report.get("run")]
            if isinstance(run, dict)
            for telemetry in [run.get("telemetry")]
            if isinstance(telemetry, dict)
        ]
    )
    report = {
        "schema_version": 1,
        "mode": "fasim_shard_coalescing_grouped_run",
        "run_status": "completed",
        "run_config_digest": run_config_digest,
        "target": workload["target"],
        "rna": workload["rna"],
        "rule": workload["rule"],
        "output_mode": args.output_mode,
        "env_overrides": env_overrides,
        "worker_count": worker_count,
        "gpu_ids": gpu_ids,
        "gpu_sharing_mode": runner._gpu_sharing_mode(
            worker_count=worker_count,
            gpu_ids=gpu_ids,
        ),
        "cpu_core_ranges": cpu_core_ranges,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "group_plan": group_plan,
        "group_plan_digest": runner._json_digest(group_plan),
        "shard_count": len(shards),
        "per_worker": per_worker,
        "per_shard": per_shard,
        "sharded_telemetry": sharded_telemetry,
        "sharded_records": sharded_raw_records,
        "sharded_unique_records": sharded_unique_records,
        "merged_records": len(merged.rows),
        "merged_raw_records": merged.raw_records,
        "merged_digest": merged.digest,
        "merged_output": str(merged_output_path),
        "duplicate_records_removed": sharded_raw_records - len(merged.rows),
        "single_records": len(single_reference.rows),
        "single_raw_records": single_reference.raw_records,
        "single_digest": single_reference.digest,
        "single_vs_sharded_digest_match": merged.digest == single_reference.digest,
        "single_run": single_run_json,
        "runner_total_seconds": runner_total_seconds,
    }
    _write_json(run_dir / "report.json", report)
    return report


def row_from_scaling_report(
    *,
    report_path: Path,
    workload_name: str,
    target_record_count: int,
    group_size: int,
    grouped_shard_count: int,
    worker_count: int,
    baseline_by_worker: dict[int, dict[str, object]],
) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("mode") == "fasim_shard_coalescing_grouped_run":
        run = report
    else:
        runs = report.get("runs")
        if not isinstance(runs, list):
            raise RuntimeError(f"report has no runs: {report_path}")
        matching = [
            item
            for item in runs
            if isinstance(item, dict) and _int(item.get("worker_count")) == worker_count
        ]
        if not matching:
            raise RuntimeError(f"report has no worker_count={worker_count}: {report_path}")
        run = matching[0]

    telemetry = _aggregate_worker_telemetry(run)
    single_run = run.get("single_run")
    single_seconds = (
        _num(single_run.get("wall_seconds"))
        if isinstance(single_run, dict)
        else _num(report.get("baseline", {}).get("single_seconds"))
        if isinstance(report.get("baseline"), dict)
        else 0.0
    )
    per_worker_seconds = run.get("per_worker_seconds")
    if not isinstance(per_worker_seconds, list):
        per_worker = run.get("per_worker")
        per_worker_seconds = (
            [worker.get("wall_seconds") for worker in per_worker if isinstance(worker, dict)]
            if isinstance(per_worker, list)
            else []
        )
    per_worker_shards: list[object] = []
    per_worker = run.get("per_worker")
    if isinstance(per_worker, list):
        per_worker_shards = [
            len(worker.get("shard_ids", [])) if isinstance(worker, dict) else 0
            for worker in per_worker
        ]

    per_shard_records = run.get("per_shard_records")
    if not isinstance(per_shard_records, list):
        per_shard = run.get("per_shard")
        per_shard_records = (
            [shard.get("records") for shard in per_shard if isinstance(shard, dict)]
            if isinstance(per_shard, list)
            else []
        )
    per_shard_seconds = run.get("per_shard_seconds")
    if not isinstance(per_shard_seconds, list):
        per_shard = run.get("per_shard")
        per_shard_seconds = (
            [
                shard.get("run", {}).get("wall_seconds")
                for shard in per_shard
                if isinstance(shard, dict)
            ]
            if isinstance(per_shard, list)
            else []
        )

    wall_seconds = _num(run.get("wall_seconds"))
    if wall_seconds == 0.0 and isinstance(per_worker_seconds, list):
        wall_seconds = max((_num(value) for value in per_worker_seconds), default=0.0)
    fallback_value = _int(
        run.get("fallbacks", telemetry.get("fasim_prealign_cuda_fallbacks"))
    )
    baseline = baseline_by_worker.get(worker_count, {})
    baseline_wall = _num(baseline.get("wall_seconds"))
    baseline_fallbacks = _int(baseline.get("fallbacks"))
    profile_calls = _int(telemetry.get("fasim_align_profile_cache_calls"))
    profile_hits = _int(telemetry.get("fasim_align_profile_cache_hits"))

    target_bases = _int(
        run.get(
            "target_bases",
            report.get("group_plan", {}).get("target_bases")
            if isinstance(report.get("group_plan"), dict)
            else 0,
        )
    )

    return {
        "workload": workload_name,
        "target_record_count": target_record_count,
        "target_bases": target_bases,
        "group_size": group_size,
        "grouped_shard_count": grouped_shard_count,
        "worker_count": worker_count,
        "wall_seconds": wall_seconds,
        "runner_total_seconds": _num(run.get("runner_total_seconds")),
        "single_seconds": single_seconds,
        "speedup_vs_group_size_1": _safe_ratio(baseline_wall, wall_seconds),
        "speedup_vs_single_whole_run": _safe_ratio(single_seconds, wall_seconds),
        "digest_match": int(bool(run.get("single_vs_sharded_digest_match"))),
        "merged_records": _int(run.get("merged_records")),
        "duplicate_removed": _int(run.get("duplicate_records_removed")),
        "per_worker_seconds": per_worker_seconds,
        "per_worker_shards": per_worker_shards,
        "per_shard_records": per_shard_records,
        "per_shard_seconds": per_shard_seconds,
        "prealign_cuda_fallbacks": fallback_value,
        "prealign_cuda_fallback_delta_vs_group_size_1": fallback_value
        - baseline_fallbacks,
        "prealign_cuda_tasks": _int(telemetry.get("fasim_prealign_cuda_tasks")),
        "prealign_cuda_batches": _int(telemetry.get("fasim_prealign_cuda_batches")),
        "profile_cache_active": _int(
            telemetry.get("fasim_align_profile_cache_active")
        ),
        "profile_cache_calls": profile_calls,
        "profile_cache_hits": profile_hits,
        "profile_cache_misses": _int(telemetry.get("fasim_align_profile_cache_misses")),
        "profile_cache_hit_rate": _safe_ratio(float(profile_hits), float(profile_calls)),
        "extend_seconds": _num(telemetry.get("fasim_extend_seconds")),
        "output_seconds": _num(telemetry.get("fasim_output_seconds")),
        "imbalance_ratio": _imbalance_ratio(per_worker_seconds),
        "report_path": str(report_path),
    }


def _tsv_row(row: dict[str, object]) -> dict[str, object]:
    converted = dict(row)
    converted["per_worker_seconds"] = _format_seconds_list(
        list(converted.get("per_worker_seconds", []))
    )
    converted["per_worker_shards"] = _format_int_list(
        list(converted.get("per_worker_shards", []))
    )
    converted["per_shard_records"] = _format_int_list(
        list(converted.get("per_shard_records", []))
    )
    converted["per_shard_seconds"] = _format_seconds_list(
        list(converted.get("per_shard_seconds", []))
    )
    return converted


def _default_env(args: argparse.Namespace) -> dict[str, str]:
    env = {
        "FASIM_ENABLE_PREALIGN_CUDA": "1",
        "FASIM_EXTEND_THREADS": str(args.extend_threads),
        "FASIM_ALIGN_PROFILE_CACHE": "1",
        "FASIM_VERBOSE": "0",
    }
    for item in args.env:
        if "=" not in item:
            raise RuntimeError(f"--env must be KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise RuntimeError(f"--env has empty key: {item}")
        env[key] = value
    return env


def _characterize_workload(
    *,
    workload: dict[str, object],
    args: argparse.Namespace,
    group_sizes: list[int],
    worker_counts: list[int],
    gpu_ids: list[str],
    explicit_cpu_core_ranges: list[str],
    env_overrides: dict[str, str],
    work_dir: Path,
) -> dict[str, object]:
    workload_name = str(workload["name"])
    workload_dir = work_dir / _sanitize_name(workload_name)
    records = read_fasta(Path(str(workload["target"])))
    target_record_count = len(records)
    target_bases = _records_bases(records)

    single_reference, single_run_json = _run_single_reference(
        workload=workload,
        args=args,
        env_overrides=env_overrides,
        gpu_ids=gpu_ids,
        work_dir=workload_dir,
    )

    group_reports: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    baseline_by_worker: dict[int, dict[str, object]] = {}

    for group_size in group_sizes:
        group_dir = workload_dir / f"group_size_{group_size}" / "inputs"
        _, group_plan = write_grouped_fasta(
            records=records,
            group_size=group_size,
            output_dir=group_dir,
            workload_name=workload_name,
        )
        group_report = {
            "schema_version": 1,
            "mode": "fasim_shard_coalescing_group_size",
            "workload": workload_name,
            "target": workload["target"],
            "rna": workload["rna"],
            "rule": workload["rule"],
            "target_record_count": target_record_count,
            "target_bases": target_bases,
            "group_plan": group_plan,
            "baseline": {
                "single_seconds": _num(single_run_json.get("wall_seconds")),
                "merged_digest": single_reference.digest,
                "merged_records": len(single_reference.rows),
            },
            "runs": [],
        }
        group_report_path = workload_dir / f"group_size_{group_size}" / "report.json"

        for worker_count in worker_counts:
            run_dir = (
                workload_dir
                / f"group_size_{group_size}"
                / f"workers_{worker_count}"
            )
            if run_dir.exists():
                shutil.rmtree(run_dir)
            run_report = _run_grouped_worker_count(
                workload=workload,
                group_plan=group_plan,
                worker_count=worker_count,
                args=args,
                env_overrides=env_overrides,
                gpu_ids=gpu_ids,
                explicit_cpu_core_ranges=explicit_cpu_core_ranges,
                single_reference=single_reference,
                single_run_json=single_run_json,
                run_dir=run_dir,
            )
            run_report_path = run_dir / "report.json"
            group_report["runs"].append(run_report)
            if group_size == 1:
                telemetry = _aggregate_worker_telemetry(run_report)
                baseline_by_worker[worker_count] = {
                    "wall_seconds": _worker_wall(
                        [
                            worker
                            for worker in run_report.get("per_worker", [])
                            if isinstance(worker, dict)
                        ]
                    ),
                    "fallbacks": _int(telemetry.get("fasim_prealign_cuda_fallbacks")),
                }
            row = row_from_scaling_report(
                report_path=run_report_path,
                workload_name=workload_name,
                target_record_count=target_record_count,
                group_size=group_size,
                grouped_shard_count=_int(group_plan.get("grouped_shard_count")),
                worker_count=worker_count,
                baseline_by_worker=baseline_by_worker,
            )
            row["target_bases"] = target_bases
            rows.append(row)

        group_report["summary"] = {
            "all_digest_match": all(
                bool(run.get("single_vs_sharded_digest_match"))
                for run in group_report["runs"]
                if isinstance(run, dict)
            )
        }
        _write_json(group_report_path, group_report)
        group_reports.append(group_report)

    return {
        "name": workload_name,
        "target": workload["target"],
        "rna": workload["rna"],
        "rule": workload["rule"],
        "target_record_count": target_record_count,
        "target_bases": target_bases,
        "single_reference": {
            "records": len(single_reference.rows),
            "raw_records": single_reference.raw_records,
            "digest": single_reference.digest,
            "run": single_run_json,
        },
        "group_reports": group_reports,
        "rows": rows,
        "all_digest_match": all(bool(row["digest_match"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Characterize grouping tiny Fasim target FASTA records into larger "
            "worker shards while preserving merged output equivalence."
        )
    )
    parser.add_argument(
        "--workload",
        action="append",
        required=True,
        metavar="NAME:TARGET_FASTA:RNA_FASTA:RULE",
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument(
        "--output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
    )
    parser.add_argument("--group-sizes", default="1,4,8,16,32")
    parser.add_argument("--workers", default="1,2,4")
    parser.add_argument("--gpu-ids", default=None)
    parser.add_argument("--cpu-core-ranges", default=None)
    parser.add_argument("--cpu-pool", default=None)
    parser.add_argument("--cpu-cores-per-worker", type=int, default=None)
    parser.add_argument("--auto-cpu-core-ranges", action="store_true")
    parser.add_argument("--extend-threads", type=int, default=6)
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="environment override applied after the current-base defaults",
    )
    parser.add_argument(
        "--fasim-arg",
        action="append",
        default=[],
        help="extra single argument appended to each Fasim invocation",
    )
    args = parser.parse_args()

    args.fasim_bin = args.fasim_bin.resolve()
    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")
    workloads = [_parse_workload(spec) for spec in args.workload]
    group_sizes = _parse_csv_ints(args.group_sizes, flag="--group-sizes")
    if 1 not in group_sizes:
        raise RuntimeError("--group-sizes must include 1 for the baseline")
    worker_counts = _parse_csv_ints(args.workers, flag="--workers")
    gpu_ids = _parse_csv(args.gpu_ids, flag="--gpu-ids")
    explicit_cpu_core_ranges = _parse_csv(
        args.cpu_core_ranges,
        flag="--cpu-core-ranges",
    )
    if explicit_cpu_core_ranges and len(explicit_cpu_core_ranges) < max(worker_counts):
        raise RuntimeError(
            "--cpu-core-ranges must include at least as many ranges as the largest worker count"
        )
    if args.auto_cpu_core_ranges and not args.cpu_pool:
        raise RuntimeError("--auto-cpu-core-ranges requires --cpu-pool")
    if args.auto_cpu_core_ranges and args.cpu_cores_per_worker is None:
        raise RuntimeError("--auto-cpu-core-ranges requires --cpu-cores-per-worker")

    env_overrides = _default_env(args)
    work_dir = args.work_dir.resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    workload_reports = []
    rows: list[dict[str, object]] = []
    for workload in workloads:
        report = _characterize_workload(
            workload=workload,
            args=args,
            group_sizes=group_sizes,
            worker_counts=worker_counts,
            gpu_ids=gpu_ids,
            explicit_cpu_core_ranges=explicit_cpu_core_ranges,
            env_overrides=env_overrides,
            work_dir=work_dir,
        )
        workload_reports.append(report)
        rows.extend(report["rows"])

    output = {
        "schema_version": 1,
        "mode": "fasim_shard_coalescing_characterization",
        "output_mode": args.output_mode,
        "group_sizes": group_sizes,
        "worker_counts": worker_counts,
        "gpu_ids": gpu_ids,
        "cpu_core_ranges": explicit_cpu_core_ranges,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "env_overrides": env_overrides,
        "workloads": workload_reports,
        "rows": rows,
        "summary": {
            "workloads": len(workload_reports),
            "rows": len(rows),
            "all_digest_match": all(bool(row["digest_match"]) for row in rows),
        },
    }
    _write_json(work_dir / "report.json", output)
    _write_tsv(work_dir / "raw.tsv", [_tsv_row(row) for row in rows], RAW_FIELDS)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
