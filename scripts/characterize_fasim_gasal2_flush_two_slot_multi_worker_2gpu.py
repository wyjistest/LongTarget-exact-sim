#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

DEFAULT_BENCH_ENV = {
    "FASIM_OUTPUT_MODE": "lite",
    "FASIM_VERBOSE": "0",
    "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
    "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "256",
    "FASIM_ALIGN_GASAL2_STREAMS": "3",
    "FASIM_ALIGN_GASAL2_BATCH": "20000",
}

EXTRACTED_ENV = {
    "FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER": "1",
    "FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE": "0",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP": "0",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_VALIDATE": "0",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_SERIALIZED_CONTROL": "0",
}

TWO_SLOT_ENV = {
    "FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER": "0",
    "FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE": "0",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP": "1",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING": "1",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_VALIDATE": "0",
    "FASIM_GASAL2_FLUSH_TWO_SLOT_SERIALIZED_CONTROL": "0",
}

NUMERIC_BENCH_KEYS = (
    "fasim_gasal2_flush_two_slot_overlap_requested",
    "fasim_gasal2_flush_two_slot_overlap_active",
    "fasim_gasal2_flush_two_slot_overlap_flushes_total",
    "fasim_gasal2_flush_two_slot_overlap_flushes_gpu_submitted",
    "fasim_gasal2_flush_two_slot_overlap_flushes_finalized",
    "fasim_gasal2_flush_two_slot_overlap_flushes_committed",
    "fasim_gasal2_flush_two_slot_overlap_slot0_submit_count",
    "fasim_gasal2_flush_two_slot_overlap_slot1_submit_count",
    "fasim_gasal2_flush_two_slot_overlap_slot0_finalize_count",
    "fasim_gasal2_flush_two_slot_overlap_slot1_finalize_count",
    "fasim_gasal2_flush_two_slot_overlap_slot0_commit_count",
    "fasim_gasal2_flush_two_slot_overlap_slot1_commit_count",
    "fasim_gasal2_flush_two_slot_overlap_unsupported_flushes",
    "fasim_gasal2_flush_two_slot_overlap_legacy_fallback_flushes",
    "fasim_gasal2_flush_two_slot_overlap_state_transition_violations",
    "fasim_gasal2_flush_two_slot_overlap_order_violations",
    "fasim_gasal2_flush_two_slot_overlap_wait_for_free_slot_seconds",
    "fasim_gasal2_flush_two_slot_overlap_wait_for_finalizer_seconds",
    "fasim_gasal2_flush_two_slot_overlap_wait_for_ordered_commit_seconds",
    "fasim_gasal2_flush_two_slot_overlap_pipeline_fill_seconds",
    "fasim_gasal2_flush_two_slot_overlap_pipeline_drain_seconds",
    "fasim_gasal2_flush_two_slot_overlap_gpu_stage_seconds",
    "fasim_gasal2_flush_two_slot_overlap_cpu_finalizer_seconds",
    "fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_measurement_supported",
    "fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds",
    "fasim_gasal2_flush_two_slot_overlap_finalizer_covered_by_next_flush_seconds",
    "fasim_gasal2_flush_two_slot_overlap_producer_covered_by_finalizer_seconds",
    "fasim_gasal2_flush_two_slot_overlap_slot0_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_slot1_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_slot0_peak_live_bytes",
    "fasim_gasal2_flush_two_slot_overlap_slot1_peak_live_bytes",
    "fasim_gasal2_flush_two_slot_overlap_host_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_total_peak_live_bytes",
    "fasim_gasal2_flush_two_slot_overlap_pinned_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_device_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_allocation_failures",
    "fasim_gasal2_flush_two_slot_overlap_max_live_slots",
    "fasim_gasal2_flush_two_slot_overlap_missing_rows",
    "fasim_gasal2_flush_two_slot_overlap_extra_rows",
    "fasim_gasal2_flush_two_slot_overlap_order_mismatches",
    "fasim_gasal2_flush_two_slot_overlap_cigar_mismatches",
    "fasim_gasal2_flush_two_slot_overlap_coordinate_mismatches",
    "fasim_gasal2_flush_two_slot_overlap_counter_mismatches",
    "fasim_gasal2_flush_two_slot_overlap_archive_descriptor_mismatches",
    "fasim_gasal2_extracted_finalizer_requested",
    "fasim_gasal2_extracted_finalizer_active",
    "fasim_gasal2_extracted_finalizer_committed_flushes",
    "fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes",
    "fasim_gasal2_extracted_finalizer_legacy_fallback_flushes",
    "fasim_gasal2_extracted_finalizer_missing_rows",
    "fasim_gasal2_extracted_finalizer_extra_rows",
    "fasim_gasal2_extracted_finalizer_order_mismatches",
    "fasim_gasal2_extracted_finalizer_cigar_mismatches",
    "fasim_gasal2_extracted_finalizer_coordinate_mismatches",
    "fasim_gasal2_extracted_finalizer_counter_mismatches",
    "fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches",
    "fasim_gasal2_fallbacks",
    "fasim_gasal2_length_guard_fallbacks",
    "fasim_top5_gasal2_phase_flushes",
)

STRING_BENCH_KEYS = (
    "fasim_gasal2_flush_two_slot_overlap_decision",
    "fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds",
    "fasim_gasal2_flush_two_slot_overlap_overlap_fraction",
    "fasim_gasal2_extracted_finalizer_decision",
)

MAX_BENCH_KEYS = {
    "fasim_gasal2_flush_two_slot_overlap_slot0_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_slot1_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_slot0_peak_live_bytes",
    "fasim_gasal2_flush_two_slot_overlap_slot1_peak_live_bytes",
    "fasim_gasal2_flush_two_slot_overlap_host_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_total_peak_live_bytes",
    "fasim_gasal2_flush_two_slot_overlap_pinned_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_device_peak_bytes",
    "fasim_gasal2_flush_two_slot_overlap_max_live_slots",
}


class ResourceSampler:
    def __init__(self, root_pid: int, interval: float) -> None:
        self.root_pid = root_pid
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.samples: list[dict[str, object]] = []
        self.peak_rss_kb = 0
        self.peak_gpu_used_mb = 0
        self.nvidia_smi_available = shutil.which("nvidia-smi") is not None

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=max(2.0, self.interval * 4.0))

    def _run(self) -> None:
        while not self.stop_event.is_set():
            timestamp = time.time()
            rss_kb = self._rss_tree_kb(self.root_pid)
            gpu_used_mb = self._gpu_compute_memory_mb()
            self.peak_rss_kb = max(self.peak_rss_kb, rss_kb)
            self.peak_gpu_used_mb = max(self.peak_gpu_used_mb, gpu_used_mb)
            self.samples.append(
                {
                    "timestamp": timestamp,
                    "rss_tree_kb": rss_kb,
                    "gpu_compute_used_mb": gpu_used_mb,
                }
            )
            self.stop_event.wait(self.interval)

    @staticmethod
    def _children_of(pid: int) -> list[int]:
        proc = subprocess.run(
            ["pgrep", "-P", str(pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        children: list[int] = []
        for line in proc.stdout.splitlines():
            try:
                children.append(int(line.strip()))
            except ValueError:
                pass
        return children

    @classmethod
    def _descendants(cls, root_pid: int) -> list[int]:
        pending = [root_pid]
        seen: set[int] = set()
        while pending:
            pid = pending.pop()
            if pid in seen:
                continue
            seen.add(pid)
            pending.extend(cls._children_of(pid))
        return sorted(seen)

    @classmethod
    def _rss_tree_kb(cls, root_pid: int) -> int:
        total = 0
        for pid in cls._descendants(root_pid):
            status = Path("/proc") / str(pid) / "status"
            try:
                for line in status.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            total += int(parts[1])
                        break
            except OSError:
                continue
        return total

    def _gpu_compute_memory_mb(self) -> int:
        if not self.nvidia_smi_available:
            return 0
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=used_memory",
                "--format=csv,noheader,nounits",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return 0
        total = 0
        for line in proc.stdout.splitlines():
            try:
                total += int(line.strip())
            except ValueError:
                continue
        return total


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_csv_ints(spec: str, *, flag: str) -> list[int]:
    values: list[int] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value < 1:
            raise RuntimeError(f"{flag} entries must be >= 1")
        values.append(value)
    if not values:
        raise RuntimeError(f"{flag} must not be empty")
    return sorted(set(values))


def _parse_csv(spec: str) -> list[str]:
    return [item.strip() for item in spec.split(",") if item.strip()]


def _read_fasta_records(path: Path) -> list[tuple[str, list[str]]]:
    records: list[tuple[str, list[str]]] = []
    header: str | None = None
    seq: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith(">"):
                if header is not None:
                    records.append((header, seq))
                header = line.rstrip("\n")
                seq = []
            else:
                seq.append(line.rstrip("\n"))
    if header is not None:
        records.append((header, seq))
    return records


def _write_subset_input(
    *,
    output: Path,
    source_primary: Path,
    fallback_shard_dir: Path,
    contigs: list[str],
    limit_bases_per_contig: int | None = None,
) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    wanted = set(contigs)
    selected: list[tuple[str, list[str]]] = []
    source = None
    if source_primary.exists():
        source = source_primary
        by_name: dict[str, tuple[str, list[str]]] = {}
        for header, seq in _read_fasta_records(source_primary):
            name = header[1:].split()[0].split("|")[-1] if header.startswith(">") else header
            by_name[name] = (header, seq)
        selected = [by_name[name] for name in contigs if name in by_name]
    if len(selected) != len(contigs):
        selected = []
        source = fallback_shard_dir
        for name in contigs:
            shard = fallback_shard_dir / f"{name}.fa"
            if not shard.exists():
                raise RuntimeError(f"missing fallback shard for {name}: {shard}")
            records = _read_fasta_records(shard)
            if len(records) != 1:
                raise RuntimeError(f"expected one FASTA record in {shard}")
            selected.extend(records)
    total_bases = 0
    with output.open("w", encoding="utf-8") as handle:
        for header, seq in selected:
            if limit_bases_per_contig is not None:
                joined = "".join(seq)[:limit_bases_per_contig]
                seq = [joined[idx : idx + 60] for idx in range(0, len(joined), 60)]
            total_bases += sum(len(line.strip()) for line in seq)
            handle.write(header + "\n")
            for line in seq:
                handle.write(line + "\n")
    names = [header[1:].split()[0].split("|")[-1] for header, _ in selected]
    if set(names) != wanted:
        raise RuntimeError(f"subset input mismatch: wanted={contigs} got={names}")
    return {
        "path": str(output),
        "source": str(source),
        "contigs": names,
        "records": len(selected),
        "bases": total_bases,
        "limit_bases_per_contig": limit_bases_per_contig,
        "bytes": output.stat().st_size,
        "sha256": _sha256_file(output),
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _metric(report: dict[str, object], key: str, default: object = 0) -> object:
    sums = report.get("fasim_benchmark_sums")
    if not isinstance(sums, dict):
        return default
    return sums.get(key, default)


def _parse_benchmark_log(path: Path) -> dict[str, object]:
    benchmarks: dict[str, object] = {}
    if not path.exists():
        return benchmarks
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("benchmark."):
            continue
        item = line[len("benchmark.") :]
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        try:
            number = float(value) if "." in value or "e" in value.lower() else int(value)
        except ValueError:
            benchmarks[key] = value
        else:
            benchmarks[key] = number
    return benchmarks


def _aggregate_shard_benchmarks(report: dict[str, object]) -> dict[str, object]:
    aggregate: dict[str, object] = {}
    for shard in report.get("per_shard", []):
        if not isinstance(shard, dict) or shard.get("status") == "failed":
            continue
        run = shard.get("run")
        if not isinstance(run, dict):
            continue
        stderr = run.get("stderr_path")
        if not isinstance(stderr, str):
            continue
        values = _parse_benchmark_log(Path(stderr))
        for key, value in values.items():
            if isinstance(value, (int, float)):
                if key in MAX_BENCH_KEYS:
                    previous = aggregate.get(key, 0)
                    aggregate[key] = max(float(previous), float(value))
                else:
                    previous = aggregate.get(key, 0)
                    if isinstance(previous, (int, float)):
                        aggregate[key] = previous + value
                    else:
                        aggregate[key] = value
            elif key not in aggregate or aggregate[key] in ("", "none"):
                aggregate[key] = value
    return aggregate


def _metric_float(report: dict[str, object], key: str) -> float:
    value = _metric(report, key, 0)
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _metric_int(report: dict[str, object], key: str) -> int:
    return int(round(_metric_float(report, key)))


def _summarize_gpu_assignment(report: dict[str, object]) -> str:
    per_worker = report.get("per_worker")
    if not isinstance(per_worker, list):
        return ""
    pairs = []
    for worker in per_worker:
        if isinstance(worker, dict):
            pairs.append(f"{worker.get('worker_id')}:{worker.get('gpu_id')}")
    return ",".join(pairs)


def _topk_compare(baseline: Path, candidate: Path, output: Path) -> dict[str, str]:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "compare_fasim_lite_topk.py"),
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--k",
            "5",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    output.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    values: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    values["status"] = "clean" if proc.returncode == 0 else "mismatch"
    return values


def _run_sharded_case(
    *,
    args: argparse.Namespace,
    mode: str,
    worker_count: int,
    repeat: int,
    work_dir: Path,
    env_items: list[str],
) -> tuple[dict[str, object], dict[str, object]]:
    case_dir = work_dir / mode / f"workers_{worker_count}" / f"run_{repeat}"
    case_dir.mkdir(parents=True, exist_ok=True)
    report_path = case_dir / "report.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "fasim_sharded_runner.py"),
        "--fasim-bin",
        str(args.fasim_bin),
        "--target",
        str(args.target),
        "--rna",
        str(args.rna),
        "--rule",
        str(args.rule),
        "--work-dir",
        str(case_dir),
        "--output-mode",
        "lite",
        "--workers",
        str(worker_count),
        "--gpu-ids",
        args.gpu_ids,
        "--auto-cpu-core-ranges",
        "--cpu-pool",
        args.cpu_pool,
        "--cpu-cores-per-worker",
        str(args.cpu_cores_per_worker),
    ]
    if args.manifest:
        cmd.append("--manifest")
    for item in env_items:
        cmd.extend(["--env", item])

    stdout_path = case_dir / "matrix_stdout.log"
    stderr_path = case_dir / "matrix_stderr.log"
    env = os.environ.copy()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    sampler = ResourceSampler(proc.pid, args.resource_sample_interval)
    sampler.start()
    t0 = time.perf_counter()
    stdout, stderr = proc.communicate()
    t1 = time.perf_counter()
    sampler.stop()
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    _write_json(case_dir / "resource_samples.json", sampler.samples)
    resources = {
        "resource_samples_path": str(case_dir / "resource_samples.json"),
        "resource_sample_interval": args.resource_sample_interval,
        "peak_rss_tree_kb": sampler.peak_rss_kb,
        "peak_gpu_compute_used_mb": sampler.peak_gpu_used_mb,
        "nvidia_smi_available": sampler.nvidia_smi_available,
    }
    if proc.returncode != 0:
        resources["exit_code"] = proc.returncode
        resources["stdout_path"] = str(stdout_path)
        resources["stderr_path"] = str(stderr_path)
        resources["error"] = (
            f"{mode} workers={worker_count} repeat={repeat} failed with "
            f"exit {proc.returncode}; see {stderr_path}"
        )
        return {}, resources
    if not report_path.exists():
        raise RuntimeError(f"missing sharded report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["matrix_runner_wall_seconds"] = t1 - t0
    return report, resources


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Characterize default-off GASAL2 two-slot overlap under 2-GPU multi-worker sharding."
    )
    parser.add_argument("--fasim-bin", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--rna", type=Path, default=ROOT / "H19.fa")
    parser.add_argument("--rule", default="0")
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument(
        "--contigs",
        default="chr17,chr18,chr19,chr20,chr21,chr22",
        help="contigs used when --target is omitted",
    )
    parser.add_argument(
        "--source-primary",
        type=Path,
        default=ROOT / ".tmp" / "fasim_hg38_genome_sharded_worker_matrix" / "inputs" / "hg38_primary_chromosomes.fa",
    )
    parser.add_argument(
        "--fallback-shard-dir",
        type=Path,
        default=ROOT / ".tmp" / "gasal2_hg38_archive_first_rule0_run" / "shards",
    )
    parser.add_argument("--workers", default="1,2,4,6")
    parser.add_argument("--gpu-ids", default="0,1")
    parser.add_argument("--cpu-pool", default="0-17")
    parser.add_argument("--cpu-cores-per-worker", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--resource-sample-interval", type=float, default=1.0)
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="record failed worker-count configurations and continue",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="use chr21,chr22 and workers 1,2 unless explicitly overridden",
    )
    parser.add_argument(
        "--smoke-bases-per-contig",
        type=int,
        default=2_000_000,
        help="truncate each smoke contig to this many bases",
    )
    parser.add_argument(
        "--limit-bases-per-contig",
        type=int,
        default=8_000_000,
        help="truncate generated non-smoke contigs to this many bases; set 0 for full contigs",
    )
    args = parser.parse_args()

    args.fasim_bin = args.fasim_bin.resolve()
    args.rna = args.rna.resolve()
    work_dir = args.work_dir.resolve()
    if not args.fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {args.fasim_bin}")
    if not args.rna.exists():
        raise RuntimeError(f"missing RNA FASTA: {args.rna}")
    if args.repeats < 1:
        raise RuntimeError("--repeats must be >= 1")

    worker_counts = _parse_csv_ints("1,2" if args.smoke and args.workers == "1,2,4,6" else args.workers, flag="--workers")
    if 1 not in worker_counts:
        raise RuntimeError("--workers must include 1")
    gpu_ids = _parse_csv(args.gpu_ids)
    if len(gpu_ids) < 2:
        raise RuntimeError("--gpu-ids must include at least two GPUs for this characterization")

    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    if args.target is None:
        contig_spec = "chr21,chr22" if args.smoke and args.contigs == "chr17,chr18,chr19,chr20,chr21,chr22" else args.contigs
        contigs = _parse_csv(contig_spec)
        target = work_dir / "inputs" / ("smoke_multi_worker.fa" if args.smoke else "chr17_chr22_scoped.fa")
        if args.smoke:
            limit_bases = args.smoke_bases_per_contig
        else:
            limit_bases = args.limit_bases_per_contig if args.limit_bases_per_contig > 0 else None
        input_info = _write_subset_input(
            output=target,
            source_primary=args.source_primary.resolve(),
            fallback_shard_dir=args.fallback_shard_dir.resolve(),
            contigs=contigs,
            limit_bases_per_contig=limit_bases,
        )
    else:
        target = args.target.resolve()
        if not target.exists():
            raise RuntimeError(f"missing target FASTA: {target}")
        input_info = {
            "path": str(target),
            "source": "explicit",
            "contigs": [],
            "records": sum(1 for line in target.open(errors="replace") if line.startswith(">")),
            "bytes": target.stat().st_size,
            "sha256": _sha256_file(target),
        }
    args.target = target

    common_env = dict(DEFAULT_BENCH_ENV)
    modes = {
        "extracted": EXTRACTED_ENV,
        "two_slot": TWO_SLOT_ENV,
    }

    runs: list[dict[str, object]] = []
    failed_runs: list[dict[str, object]] = []
    reports: dict[tuple[str, int, int], dict[str, object]] = {}
    resources_by_run: dict[tuple[str, int, int], dict[str, object]] = {}

    for repeat in range(1, args.repeats + 1):
        for worker_count in worker_counts:
            for mode in ("extracted", "two_slot"):
                env_values = {**common_env, **modes[mode]}
                env_items = [f"{key}={value}" for key, value in sorted(env_values.items())]
                report, resources = _run_sharded_case(
                    args=args,
                    mode=mode,
                    worker_count=worker_count,
                    repeat=repeat,
                    work_dir=work_dir,
                    env_items=env_items,
                )
                if not report:
                    failure = {
                        "schema_version": 1,
                        "mode": mode,
                        "worker_count": worker_count,
                        "repeat": repeat,
                        "exit_code": resources.get("exit_code"),
                        "error": resources.get("error"),
                        "stdout_path": resources.get("stdout_path"),
                        "stderr_path": resources.get("stderr_path"),
                        "resource_peak_rss_tree_kb": resources.get("peak_rss_tree_kb", 0),
                        "resource_peak_gpu_compute_used_mb": resources.get("peak_gpu_compute_used_mb", 0),
                    }
                    failed_runs.append(failure)
                    print(
                        f"failed mode={mode} workers={worker_count} repeat={repeat}: "
                        f"{failure['error']}",
                        flush=True,
                    )
                    if not args.keep_going:
                        raise RuntimeError(str(failure["error"]))
                    continue
                reports[(mode, worker_count, repeat)] = report
                resources_by_run[(mode, worker_count, repeat)] = resources
                merged_output = report.get("merged_output")
                if not isinstance(merged_output, str):
                    raise RuntimeError(f"{mode} workers={worker_count} repeat={repeat}: missing merged_output")
                merged_path = Path(merged_output)
                bench = _aggregate_shard_benchmarks(report)
                row = {
                    "schema_version": 1,
                    "mode": mode,
                    "worker_count": worker_count,
                    "repeat": repeat,
                    "run_status": report.get("run_status"),
                    "gpu_ids": ",".join(str(x) for x in report.get("gpu_ids", [])),
                    "gpu_sharing_mode": report.get("gpu_sharing_mode"),
                    "worker_gpu_assignment": _summarize_gpu_assignment(report),
                    "shard_count": report.get("shard_count"),
                    "failed_shards": len(report.get("failed_shards", []) or []),
                    "resumed_shards": len(report.get("resumed_shards", []) or []),
                    "wall_seconds": max(
                        float(worker.get("wall_seconds", 0.0))
                        for worker in report.get("per_worker", [])
                        if isinstance(worker, dict)
                    ),
                    "runner_wall_seconds": report.get("matrix_runner_wall_seconds"),
                    "worker_seconds_sum": sum(
                        float(worker.get("wall_seconds", 0.0))
                        for worker in report.get("per_worker", [])
                        if isinstance(worker, dict)
                    ),
                    "per_worker_wall_seconds": ",".join(
                        f"{float(worker.get('wall_seconds', 0.0)):.6f}"
                        for worker in report.get("per_worker", [])
                        if isinstance(worker, dict)
                    ),
                    "merged_records": report.get("merged_records"),
                    "merged_raw_records": report.get("merged_raw_records"),
                    "merged_digest": report.get("merged_digest"),
                    "merged_output": str(merged_path),
                    "topk_summary_digest": report.get("topk_summary_digest"),
                    "topk_rows_digest": report.get("topk_rows_digest"),
                    "topk_lite_digest": report.get("topk_lite_digest"),
                    "duplicate_records_removed": report.get("duplicate_records_removed"),
                    "resource_peak_rss_tree_kb": resources["peak_rss_tree_kb"],
                    "resource_peak_gpu_compute_used_mb": resources["peak_gpu_compute_used_mb"],
                    "nvidia_smi_available": resources["nvidia_smi_available"],
                    "report_path": str(work_dir / mode / f"workers_{worker_count}" / f"run_{repeat}" / "report.json"),
                }
                for key in NUMERIC_BENCH_KEYS:
                    row[key] = bench.get(key, 0)
                for key in STRING_BENCH_KEYS:
                    row[key] = bench.get(key, "none")
                runs.append(row)
                print(
                    f"completed mode={mode} workers={worker_count} repeat={repeat} "
                    f"wall={row['wall_seconds']:.3f}s digest={row['merged_digest']}",
                    flush=True,
                )

    topk_rows: list[dict[str, object]] = []
    for worker_count in worker_counts:
        for repeat in range(1, args.repeats + 1):
            if ("extracted", worker_count, repeat) not in reports or (
                "two_slot",
                worker_count,
                repeat,
            ) not in reports:
                continue
            baseline = reports[("extracted", worker_count, repeat)]
            candidate = reports[("two_slot", worker_count, repeat)]
            baseline_path = Path(str(baseline["merged_output"]))
            candidate_path = Path(str(candidate["merged_output"]))
            out = work_dir / "topk_compare" / f"workers_{worker_count}_run_{repeat}.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            compare = _topk_compare(baseline_path, candidate_path, out)
            topk_rows.append(
                {
                    "schema_version": 1,
                    "worker_count": worker_count,
                    "repeat": repeat,
                    "baseline": str(baseline_path),
                    "candidate": str(candidate_path),
                    "merged_digest_equal": str(baseline.get("merged_digest") == candidate.get("merged_digest")).lower(),
                    "top5_score_equal": compare.get("top5_score_equal", "false"),
                    "top5_stability_equal": compare.get("top5_stability_equal", "false"),
                    "top5_nt_score_equal": compare.get("top5_nt_score_equal", "false"),
                    "missing_rows": compare.get("missing_rows", "0"),
                    "extra_rows": compare.get("extra_rows", "0"),
                    "baseline_unique_rows": compare.get("baseline_unique_rows", "0"),
                    "candidate_unique_rows": compare.get("candidate_unique_rows", "0"),
                    "status": compare["status"],
                    "compare_path": str(out),
                }
            )

    determinism_rows: list[dict[str, object]] = []
    for mode in ("extracted", "two_slot"):
        for worker_count in worker_counts:
            if any((mode, worker_count, repeat) not in reports for repeat in range(1, args.repeats + 1)):
                continue
            paths = [
                str(reports[(mode, worker_count, repeat)]["merged_output"])
                for repeat in range(1, args.repeats + 1)
            ]
            label = f"{mode}_workers_{worker_count}"
            summary = work_dir / "determinism" / f"{label}.summary.txt"
            pairs = work_dir / "determinism" / f"{label}.pairs.tsv"
            summary.parent.mkdir(parents=True, exist_ok=True)
            if len(paths) >= 2:
                cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "compare_fasim_full_run_determinism.py"),
                    *(arg for path in paths for arg in ("--run", path)),
                    "--k",
                    "5",
                    "--output-summary",
                    str(summary),
                    "--output-pairs",
                    str(pairs),
                ]
                subprocess.run(cmd, check=True)
            else:
                summary.write_text(
                    "\n".join(
                        [
                            "runs=1",
                            "schema=lite",
                            "k=5",
                            "byte_stable=true",
                            "set_stable=true",
                            "multiset_stable=true",
                            "top5_score_stable=true",
                            "top5_stability_stable=true",
                            "top5_nt_score_stable=true",
                            "max_pair_set_missing=0",
                            "max_pair_set_extra=0",
                            "max_pair_multiset_missing=0",
                            "max_pair_multiset_extra=0",
                            "classification=single_run_no_pairwise_variability",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                pairs.write_text("", encoding="utf-8")
            values: dict[str, str] = {}
            for line in summary.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
            determinism_rows.append(
                {
                    "schema_version": 1,
                    "mode": mode,
                    "worker_count": worker_count,
                    "summary_path": str(summary),
                    "pairs_path": str(pairs),
                    **values,
                }
            )

    run_columns = list(runs[0].keys()) if runs else []
    with (work_dir / "runs.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=run_columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(runs)

    topk_columns = list(topk_rows[0].keys()) if topk_rows else []
    with (work_dir / "topk_compare.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=topk_columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(topk_rows)

    det_columns = sorted({key for row in determinism_rows for key in row})
    with (work_dir / "determinism.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=det_columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(determinism_rows)

    failed_columns = list(failed_runs[0].keys()) if failed_runs else [
        "schema_version",
        "mode",
        "worker_count",
        "repeat",
        "exit_code",
        "error",
        "stdout_path",
        "stderr_path",
        "resource_peak_rss_tree_kb",
        "resource_peak_gpu_compute_used_mb",
    ]
    with (work_dir / "failed_runs.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=failed_columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(failed_runs)

    summary: dict[str, object] = {
        "schema_version": 1,
        "mode": "fasim_gasal2_flush_two_slot_multi_worker_2gpu",
        "scope": "normal-triplex lite",
        "default_policy": "default_off",
        "runtime_device_overlap_supported": False,
        "host_scheduling_overlap_available": True,
        "target": input_info,
        "rna": str(args.rna),
        "rule": str(args.rule),
        "worker_counts": worker_counts,
        "gpu_ids": gpu_ids,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "repeats": args.repeats,
        "smoke": bool(args.smoke),
        "failed_runs": len(failed_runs),
    }
    strong_go_counts = 0
    scoped_go_counts = 0
    for worker_count in worker_counts:
        extracted_rows = [
            row for row in runs
            if row["mode"] == "extracted" and row["worker_count"] == worker_count
        ]
        two_slot_rows = [
            row for row in runs
            if row["mode"] == "two_slot" and row["worker_count"] == worker_count
        ]
        topk_for_worker = [
            row for row in topk_rows
            if row["worker_count"] == worker_count
        ]
        extracted_wall = _median([float(row["wall_seconds"]) for row in extracted_rows])
        two_slot_wall = _median([float(row["wall_seconds"]) for row in two_slot_rows])
        improvement = ((extracted_wall - two_slot_wall) / extracted_wall) if extracted_wall else 0.0
        if worker_count > 1 and improvement >= 0.05:
            strong_go_counts += 1
        if improvement >= 0.05:
            scoped_go_counts += 1
        prefix = f"workers_{worker_count}"
        summary[f"{prefix}_extracted_wall_median_seconds"] = extracted_wall
        summary[f"{prefix}_two_slot_wall_median_seconds"] = two_slot_wall
        summary[f"{prefix}_two_slot_wall_saving_seconds_vs_extracted"] = extracted_wall - two_slot_wall
        summary[f"{prefix}_two_slot_wall_improvement_fraction_vs_extracted"] = improvement
        summary[f"{prefix}_two_slot_host_scheduling_overlap_seconds_median"] = _median(
            [
                float(row["fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds"])
                for row in two_slot_rows
            ]
        )
        summary[f"{prefix}_two_slot_peak_rss_tree_kb_median"] = _median(
            [float(row["resource_peak_rss_tree_kb"]) for row in two_slot_rows]
        )
        summary[f"{prefix}_two_slot_peak_gpu_compute_used_mb_median"] = _median(
            [float(row["resource_peak_gpu_compute_used_mb"]) for row in two_slot_rows]
        )
        summary[f"{prefix}_top5_clean"] = bool(topk_for_worker) and all(
            row["top5_score_equal"] == "true"
            and row["top5_stability_equal"] == "true"
            and row["top5_nt_score_equal"] == "true"
            for row in topk_for_worker
        )
        summary[f"{prefix}_cross_mode_merged_digest_equal"] = bool(topk_for_worker) and all(
            row["merged_digest_equal"] == "true"
            for row in topk_for_worker
        )
        summary[f"{prefix}_cross_mode_missing_rows_max"] = max(
            [int(row["missing_rows"]) for row in topk_for_worker] or [0]
        )
        summary[f"{prefix}_cross_mode_extra_rows_max"] = max(
            [int(row["extra_rows"]) for row in topk_for_worker] or [0]
        )
    summary["strong_go_multi_worker_configs"] = strong_go_counts
    summary["scoped_go_configs"] = scoped_go_counts
    summary["decision"] = "multi_worker_2gpu_recorded"
    _write_json(work_dir / "summary.json", summary)
    (work_dir / "summary.txt").write_text(
        "\n".join(f"{key}={value}" for key, value in summary.items()) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
