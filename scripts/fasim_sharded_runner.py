#!/usr/bin/env python3
import argparse
import concurrent.futures
import dataclasses
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path


LITE_HEADER = (
    "Chr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\t"
    "StartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\t"
    "MeanStability"
)

TFOSORTED_HEADER = (
    "QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
    "StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\tStrand\t"
    "Rule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\tTFO sequence\tTTS sequence"
)

RUNNER_VERSION = "fasim_sharded_runner_manifest_v1"


@dataclasses.dataclass(frozen=True)
class FastaRecord:
    header: str
    sequence: str


@dataclasses.dataclass(frozen=True)
class Shard:
    shard_id: str
    target_name: str
    target_start: int
    target_end: int
    shard_fasta_path: Path
    estimated_length: int
    estimated_windows: None
    estimated_cells: None


@dataclasses.dataclass(frozen=True)
class RunResult:
    label: str
    cmd: list[str]
    env_overrides: dict[str, str]
    wall_seconds: float
    stdout_path: Path
    stderr_path: Path
    output_dir: Path
    output_path: Path | None
    exit_code: int


class FasimRunError(RuntimeError):
    def __init__(self, message: str, run: RunResult) -> None:
        super().__init__(message)
        self.run = run


@dataclasses.dataclass
class WorkerAssignment:
    worker_id: int
    gpu_id: str | None
    cpu_core_range: str | None
    shards: list[Shard]


@dataclasses.dataclass(frozen=True)
class ScheduledShardResult:
    shard_id: str
    output_path: Path | None
    raw_records: int
    unique_records: int
    status: str
    report: dict[str, object]


@dataclasses.dataclass(frozen=True)
class WorkerResult:
    worker_id: int
    gpu_id: str | None
    cpu_core_range: str | None
    estimated_length: int
    estimated_cells: int | None
    wall_seconds: float
    shard_results: list[ScheduledShardResult]


@dataclasses.dataclass(frozen=True)
class CanonicalOutput:
    header: str
    rows: list[str]
    raw_records: int
    digest: str
    content: str


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_text(encoded)


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)
    try:
        dir_fd = os.open(str(path.parent), os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _git_commit() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _read_fasta(path: Path) -> list[FastaRecord]:
    records: list[FastaRecord] = []
    header: str | None = None
    seq_parts: list[str] = []

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append(FastaRecord(header, "".join(seq_parts)))
                header = line
                seq_parts = []
            else:
                seq_parts.append(line)

    if header is not None:
        records.append(FastaRecord(header, "".join(seq_parts)))

    return [r for r in records if r.sequence]


def _parse_target_header(record: FastaRecord) -> tuple[str, int, int]:
    if not record.header.startswith(">"):
        return record.header.strip() or "unknown", 1, len(record.sequence)

    body = record.header[1:].strip()
    parts = body.split("|")
    target_name = parts[1].strip() if len(parts) >= 2 and parts[1].strip() else body
    start = 1
    end = len(record.sequence)

    if len(parts) >= 3:
        coord_text = parts[2].strip()
        match = re.match(r"^(-?\d+)(?:-(-?\d+))?", coord_text)
        if match:
            start = int(match.group(1))
            if match.group(2) is not None:
                end = int(match.group(2))
            else:
                end = start + len(record.sequence) - 1
        else:
            end = start + len(record.sequence) - 1

    return target_name, start, end


def _sanitize_for_path(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "target"


def _wrap_sequence(sequence: str, width: int = 80) -> str:
    return "\n".join(sequence[i : i + width] for i in range(0, len(sequence), width))


def _write_shard_fastas(records: list[FastaRecord], shard_dir: Path) -> list[Shard]:
    shard_dir.mkdir(parents=True, exist_ok=True)
    shards: list[Shard] = []

    for idx, record in enumerate(records):
        target_name, start, end = _parse_target_header(record)
        shard_id = f"shard_{idx:04d}_{_sanitize_for_path(target_name)}"
        shard_path = shard_dir / f"{shard_id}.fa"
        shard_path.write_text(
            f"{record.header}\n{_wrap_sequence(record.sequence)}\n",
            encoding="utf-8",
        )
        shards.append(
            Shard(
                shard_id=shard_id,
                target_name=target_name,
                target_start=start,
                target_end=end,
                shard_fasta_path=shard_path,
                estimated_length=len(record.sequence),
                estimated_windows=None,
                estimated_cells=None,
            )
        )

    return shards


def _parse_env_overrides(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--env must be KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"--env has empty key: {item}")
        env[key] = value
    return env


def _parse_csv_list(value: str | None, *, name: str) -> list[str]:
    if value is None or not value.strip():
        return []
    items = [item.strip() for item in value.split(",")]
    if any(not item for item in items):
        raise ValueError(f"{name} must be a comma-separated list without empty items")
    return items


def _parse_cpu_pool(value: str) -> list[int]:
    cores: list[int] = []
    seen: set[int] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            raise ValueError("--cpu-pool must not include empty entries")
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                raise ValueError(f"invalid --cpu-pool range: {item}")
            values = range(start, end + 1)
        else:
            values = [int(item)]
        for core in values:
            if core < 0:
                raise ValueError("--cpu-pool cores must be >= 0")
            if core not in seen:
                cores.append(core)
                seen.add(core)
    if not cores:
        raise ValueError("--cpu-pool must not be empty")
    return cores


def _format_cpu_range(cores: list[int]) -> str:
    if not cores:
        raise ValueError("empty CPU core range")
    ranges: list[str] = []
    start = cores[0]
    prev = cores[0]
    for core in cores[1:]:
        if core == prev + 1:
            prev = core
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = core
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(ranges)


def _resolve_cpu_core_ranges(
    *,
    explicit_cpu_core_ranges: list[str],
    auto_cpu_core_ranges: bool,
    cpu_pool: str | None,
    cpu_cores_per_worker: int | None,
    worker_count: int,
) -> list[str]:
    if explicit_cpu_core_ranges and auto_cpu_core_ranges:
        raise ValueError("--cpu-core-ranges and --auto-cpu-core-ranges cannot be used together")
    if not auto_cpu_core_ranges:
        return explicit_cpu_core_ranges
    if not cpu_pool:
        raise ValueError("--auto-cpu-core-ranges requires --cpu-pool")
    if cpu_cores_per_worker is None:
        raise ValueError("--auto-cpu-core-ranges requires --cpu-cores-per-worker")
    if cpu_cores_per_worker < 1:
        raise ValueError("--cpu-cores-per-worker must be >= 1")
    cores = _parse_cpu_pool(cpu_pool)
    required = worker_count * cpu_cores_per_worker
    if len(cores) < required:
        raise ValueError(
            f"insufficient --cpu-pool cores: need {required}, have {len(cores)}"
        )
    ranges: list[str] = []
    for idx in range(worker_count):
        start = idx * cpu_cores_per_worker
        end = start + cpu_cores_per_worker
        ranges.append(_format_cpu_range(cores[start:end]))
    return ranges


def _shard_work(shard: Shard) -> int:
    return int(shard.estimated_cells or shard.estimated_length)


def _sum_estimated_cells(shards: list[Shard]) -> int | None:
    if any(shard.estimated_cells is None for shard in shards):
        return None
    return sum(int(shard.estimated_cells or 0) for shard in shards)


def _assign_shards_to_workers(
    shards: list[Shard],
    *,
    worker_count: int,
    gpu_ids: list[str],
    cpu_core_ranges: list[str],
) -> list[WorkerAssignment]:
    if worker_count < 1:
        raise ValueError("--workers must be >= 1")
    if cpu_core_ranges and len(cpu_core_ranges) != worker_count:
        raise ValueError("--cpu-core-ranges must have one range per worker")

    assignments = [
        WorkerAssignment(
            worker_id=idx,
            gpu_id=gpu_ids[idx % len(gpu_ids)] if gpu_ids else None,
            cpu_core_range=cpu_core_ranges[idx] if cpu_core_ranges else None,
            shards=[],
        )
        for idx in range(worker_count)
    ]
    loads = [0 for _ in range(worker_count)]

    for shard in sorted(shards, key=lambda s: (-_shard_work(s), s.shard_id)):
        worker_idx = min(range(worker_count), key=lambda idx: (loads[idx], idx))
        assignments[worker_idx].shards.append(shard)
        loads[worker_idx] += _shard_work(shard)

    for assignment in assignments:
        assignment.shards.sort(key=lambda shard: shard.shard_id)

    return assignments


def _resolve_worker_count(
    *,
    workers: int | None,
    workers_per_gpu: int | None,
    gpu_ids: list[str],
) -> tuple[int, bool]:
    if workers is not None and workers_per_gpu is not None:
        raise ValueError("--workers and --workers-per-gpu cannot be used together")
    if workers_per_gpu is not None:
        if workers_per_gpu < 1:
            raise ValueError("--workers-per-gpu must be >= 1")
        if not gpu_ids:
            raise ValueError("--workers-per-gpu requires --gpu-ids")
        return len(gpu_ids) * workers_per_gpu, True
    if workers is None:
        return 1, False
    return workers, False


def _gpu_sharing_mode(*, worker_count: int, gpu_ids: list[str]) -> str | None:
    if not gpu_ids:
        return None
    return "shared" if worker_count > len(gpu_ids) else "exclusive"


class RunManifest:
    def __init__(self, path: Path, payload: dict[str, object]) -> None:
        self.path = path
        self.payload = payload
        self._lock = threading.Lock()

    @classmethod
    def create(
        cls,
        *,
        path: Path,
        args: argparse.Namespace,
        target: Path,
        target_digest: str,
        rna: Path,
        rna_digest: str,
        shards: list[Shard],
        shard_plan_digest: str,
        worker_count: int,
        workers_derived_from_gpu_ids: bool,
        gpu_ids: list[str],
        cpu_core_ranges: list[str],
        env_overrides: dict[str, str],
        run_config_digest: str,
        git_commit: str | None,
    ) -> "RunManifest":
        now = _utc_now()
        payload: dict[str, object] = {
            "schema_version": 1,
            "run_id": str(uuid.uuid4()),
            "run_status": "running",
            "created_at": now,
            "updated_at": now,
            "git_commit": git_commit,
            "runner_version": RUNNER_VERSION,
            "command_line": sys.argv,
            "run_config_digest": run_config_digest,
            "target_fasta": str(target),
            "target_fasta_digest": target_digest,
            "rna_fasta": str(rna),
            "rna_fasta_digest": rna_digest,
            "shard_plan_digest": shard_plan_digest,
            "shard_count": len(shards),
            "worker_count": worker_count,
            "gpu_ids": gpu_ids,
            "workers_per_gpu": args.workers_per_gpu,
            "workers_derived_from_gpu_ids": workers_derived_from_gpu_ids,
            "gpu_sharing_mode": _gpu_sharing_mode(
                worker_count=worker_count,
                gpu_ids=gpu_ids,
            ),
            "cpu_core_ranges": cpu_core_ranges,
            "cpu_pool": args.cpu_pool,
            "cpu_cores_per_worker": args.cpu_cores_per_worker,
            "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
            "taskset_enabled": bool(cpu_core_ranges),
            "env_snapshot": env_overrides,
            "output_mode": args.output_mode,
            "rule": str(args.rule),
            "per_shard": [
                {
                    **_shard_to_json(shard),
                    "run_config_digest": run_config_digest,
                    "shard_input_digest": _sha256_file(shard.shard_fasta_path),
                    "status": "planned",
                    "start_time": None,
                    "end_time": None,
                    "wall_seconds": None,
                    "output_path": None,
                    "output_digest": None,
                    "records": None,
                    "stdout_path": None,
                    "stderr_path": None,
                    "exit_code": None,
                    "env_overrides": None,
                    "skipped_by_resume": False,
                }
                for shard in shards
            ],
            "merged_records": None,
            "duplicate_removed": None,
            "merged_digest": None,
            "partial_merged_digest": None,
            "failed_shards": [],
            "resumed_shards": [],
        }
        manifest = cls(path, payload)
        manifest.write()
        return manifest

    @classmethod
    def load(cls, path: Path) -> "RunManifest":
        return cls(path, json.loads(path.read_text(encoding="utf-8")))

    def write(self) -> None:
        with self._lock:
            self._write_locked()

    def _write_locked(self) -> None:
        self.payload["updated_at"] = _utc_now()
        _atomic_write_json(self.path, self.payload)

    def shard_entry(self, shard_id: str) -> dict[str, object]:
        for entry in self.payload.get("per_shard", []):
            if isinstance(entry, dict) and entry.get("shard_id") == shard_id:
                return entry
        raise KeyError(f"manifest missing shard: {shard_id}")

    def mark_running(
        self,
        shard: Shard,
        *,
        run: RunResult | None = None,
        worker_id: int | None = None,
        gpu_id: str | None = None,
        cpu_core_range: str | None = None,
    ) -> None:
        with self._lock:
            entry = self.shard_entry(shard.shard_id)
            entry.update(
                {
                    "status": "running",
                    "start_time": _utc_now(),
                    "end_time": None,
                    "wall_seconds": None,
                    "worker_id": worker_id,
                    "gpu_id": gpu_id,
                    "cpu_core_range": cpu_core_range,
                    "output_path": str(run.output_path) if run and run.output_path else None,
                    "stdout_path": str(run.stdout_path) if run else None,
                    "stderr_path": str(run.stderr_path) if run else None,
                    "exit_code": None,
                    "skipped_by_resume": False,
                }
            )
            self._write_locked()

    def mark_completed(
        self,
        shard: Shard,
        *,
        run: RunResult,
        canonical: CanonicalOutput,
        worker_id: int,
        gpu_id: str | None,
        cpu_core_range: str | None,
        skipped_by_resume: bool = False,
    ) -> None:
        if run.output_path is None:
            raise RuntimeError(f"cannot complete {shard.shard_id} without output")
        with self._lock:
            entry = self.shard_entry(shard.shard_id)
            entry.update(
                {
                    "status": "skipped_by_resume" if skipped_by_resume else "completed",
                    "end_time": _utc_now(),
                    "wall_seconds": run.wall_seconds,
                    "worker_id": worker_id,
                    "gpu_id": gpu_id,
                    "cpu_core_range": cpu_core_range,
                    "output_path": str(run.output_path),
                    "output_digest": canonical.digest,
                    "records": len(canonical.rows),
                    "raw_records": canonical.raw_records,
                    "stdout_path": str(run.stdout_path),
                    "stderr_path": str(run.stderr_path),
                    "exit_code": run.exit_code,
                    "env_overrides": run.env_overrides,
                    "skipped_by_resume": skipped_by_resume,
                }
            )
            self._write_locked()

    def mark_failed(
        self,
        shard: Shard,
        *,
        run: RunResult | None,
        worker_id: int,
        gpu_id: str | None,
        cpu_core_range: str | None,
    ) -> None:
        with self._lock:
            entry = self.shard_entry(shard.shard_id)
            entry.update(
                {
                    "status": "failed",
                    "end_time": _utc_now(),
                    "wall_seconds": run.wall_seconds if run else None,
                    "worker_id": worker_id,
                    "gpu_id": gpu_id,
                    "cpu_core_range": cpu_core_range,
                    "output_path": str(run.output_path) if run and run.output_path else None,
                    "stdout_path": str(run.stdout_path) if run else None,
                    "stderr_path": str(run.stderr_path) if run else None,
                    "exit_code": run.exit_code if run else 1,
                    "env_overrides": run.env_overrides if run else None,
                    "skipped_by_resume": False,
                }
            )
            failed = list(self.payload.get("failed_shards", []))
            if shard.shard_id not in failed:
                failed.append(shard.shard_id)
            self.payload["failed_shards"] = failed
            self._write_locked()

    def finalize(
        self,
        *,
        run_status: str,
        merged_records: int | None,
        duplicate_removed: int | None,
        merged_digest: str | None,
        partial_merged_digest: str | None,
        failed_shards: list[str],
        resumed_shards: list[str],
    ) -> None:
        with self._lock:
            self.payload.update(
                {
                    "run_status": run_status,
                    "merged_records": merged_records,
                    "duplicate_removed": duplicate_removed,
                    "merged_digest": merged_digest,
                    "partial_merged_digest": partial_merged_digest,
                    "failed_shards": failed_shards,
                    "resumed_shards": resumed_shards,
                }
            )
            self._write_locked()


def _manifest_by_shard(manifest: RunManifest | None) -> dict[str, dict[str, object]]:
    if manifest is None:
        return {}
    return {
        str(entry["shard_id"]): entry
        for entry in manifest.payload.get("per_shard", [])
        if isinstance(entry, dict) and entry.get("shard_id")
    }


def _resume_entry_valid(
    *,
    entry: dict[str, object] | None,
    shard: Shard,
    output_mode: str,
    run_config_digest: str,
) -> tuple[bool, CanonicalOutput | None, Path | None]:
    if not entry:
        return False, None, None
    if entry.get("status") not in {"completed", "skipped_by_resume"}:
        return False, None, None
    if entry.get("run_config_digest") != run_config_digest:
        return False, None, None
    if entry.get("shard_input_digest") != _sha256_file(shard.shard_fasta_path):
        return False, None, None
    output_text = entry.get("output_path")
    digest_text = entry.get("output_digest")
    if not output_text or not digest_text:
        return False, None, None
    output_path = Path(str(output_text))
    if not output_path.exists():
        return False, None, None
    canonical = _canonicalize_file(output_path, output_mode)
    if canonical.digest != digest_text:
        return False, None, None
    return True, canonical, output_path


def _build_run_config_digest(
    *,
    args: argparse.Namespace,
    target: Path,
    target_digest: str,
    rna: Path,
    rna_digest: str,
    fasim_bin: Path,
    env_overrides: dict[str, str],
    worker_count: int,
    workers_derived_from_gpu_ids: bool,
    gpu_ids: list[str],
    cpu_core_ranges: list[str],
    shard_plan: list[dict[str, object]],
    shard_plan_digest: str,
    git_commit: str | None,
) -> str:
    payload = {
        "runner_version": RUNNER_VERSION,
        "git_commit": git_commit,
        "fasim_bin": str(fasim_bin),
        "target": str(target),
        "target_digest": target_digest,
        "rna": str(rna),
        "rna_digest": rna_digest,
        "rule": str(args.rule),
        "output_mode": args.output_mode,
        "validate_single": bool(args.validate_single),
        "env_overrides": env_overrides,
        "fasim_args": args.fasim_arg,
        "worker_count": worker_count,
        "workers_per_gpu": args.workers_per_gpu,
        "workers_derived_from_gpu_ids": workers_derived_from_gpu_ids,
        "gpu_ids": gpu_ids,
        "cpu_core_ranges": cpu_core_ranges,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "taskset_enabled": bool(cpu_core_ranges),
        "shard_plan": shard_plan,
        "shard_plan_digest": shard_plan_digest,
        "merge_config": {
            "canonical_sort": True,
            "exact_dedup": True,
            "output_mode": args.output_mode,
        },
    }
    return _json_digest(payload)


def _build_fasim_cmd(
    *,
    fasim_bin: Path,
    target: Path,
    rna: Path,
    rule: str,
    output_dir: Path,
    fasim_args: list[str],
    cpu_core_range: str | None = None,
) -> list[str]:
    cmd = [
        str(fasim_bin),
        "-f1",
        str(target),
        "-f2",
        str(rna),
        "-r",
        str(rule),
        "-O",
        str(output_dir),
    ]
    cmd.extend(fasim_args)
    if cpu_core_range:
        if shutil.which("taskset") is None:
            raise RuntimeError("--cpu-core-ranges requires taskset on PATH")
        cmd = ["taskset", "-c", cpu_core_range, *cmd]
    return cmd


def _run_fasim(
    *,
    label: str,
    fasim_bin: Path,
    target: Path,
    rna: Path,
    rule: str,
    output_mode: str,
    output_dir: Path,
    log_dir: Path,
    env_overrides: dict[str, str],
    fasim_args: list[str],
    cpu_core_range: str | None = None,
) -> RunResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    cmd = _build_fasim_cmd(
        fasim_bin=fasim_bin,
        target=target,
        rna=rna,
        rule=rule,
        output_dir=output_dir,
        fasim_args=fasim_args,
        cpu_core_range=cpu_core_range,
    )

    env = os.environ.copy()
    if "CUDA_VISIBLE_DEVICES" in env_overrides and "FASIM_CUDA_DEVICES" not in env_overrides:
        env.pop("FASIM_CUDA_DEVICES", None)
    env.update(env_overrides)
    env["FASIM_OUTPUT_MODE"] = output_mode
    env.setdefault("FASIM_VERBOSE", "0")

    stdout_path = log_dir / f"{label}.stdout.log"
    stderr_path = log_dir / f"{label}.stderr.log"

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    t1 = time.perf_counter()

    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    output_path = _find_output_file(output_dir, output_mode) if proc.returncode == 0 else None
    run = RunResult(
        label=label,
        cmd=cmd,
        env_overrides=env_overrides,
        wall_seconds=t1 - t0,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        output_dir=output_dir,
        output_path=output_path,
        exit_code=proc.returncode,
    )

    if proc.returncode != 0:
        raise FasimRunError(
            f"{label} failed with exit {proc.returncode}; see {stderr_path}",
            run,
        )
    return run


def _run_worker(
    *,
    assignment: WorkerAssignment,
    fasim_bin: Path,
    rna: Path,
    rule: str,
    output_mode: str,
    work_dir: Path,
    env_overrides: dict[str, str],
    fasim_args: list[str],
    resume_entries: dict[str, dict[str, object]],
    run_config_digest: str,
    manifest: RunManifest | None = None,
    resume: bool = False,
    keep_going: bool = False,
) -> WorkerResult:
    worker_env = dict(env_overrides)
    if assignment.gpu_id is not None:
        worker_env["CUDA_VISIBLE_DEVICES"] = assignment.gpu_id
        worker_env["FASIM_CUDA_DEVICE"] = "0"
        worker_env.pop("FASIM_CUDA_DEVICES", None)

    shard_results: list[ScheduledShardResult] = []
    t0 = time.perf_counter()
    for shard in assignment.shards:
        if resume:
            valid, canonical, output_path = _resume_entry_valid(
                entry=resume_entries.get(shard.shard_id),
                shard=shard,
                output_mode=output_mode,
                run_config_digest=run_config_digest,
            )
            if valid and canonical is not None and output_path is not None:
                pseudo_run = RunResult(
                    label=shard.shard_id,
                    cmd=[],
                    env_overrides=worker_env,
                    wall_seconds=0.0,
                    stdout_path=Path(str(resume_entries[shard.shard_id].get("stdout_path") or "")),
                    stderr_path=Path(str(resume_entries[shard.shard_id].get("stderr_path") or "")),
                    output_dir=output_path.parent,
                    output_path=output_path,
                    exit_code=0,
                )
                if manifest is not None:
                    manifest.mark_completed(
                        shard,
                        run=pseudo_run,
                        canonical=canonical,
                        worker_id=assignment.worker_id,
                        gpu_id=assignment.gpu_id,
                        cpu_core_range=assignment.cpu_core_range,
                        skipped_by_resume=True,
                    )
                shard_results.append(
                    ScheduledShardResult(
                        shard_id=shard.shard_id,
                        output_path=output_path,
                        raw_records=canonical.raw_records,
                        unique_records=len(canonical.rows),
                        status="skipped_by_resume",
                        report={
                            **_shard_to_json(shard),
                            "worker_id": assignment.worker_id,
                            "gpu_id": assignment.gpu_id,
                            "cpu_core_range": assignment.cpu_core_range,
                            "records": len(canonical.rows),
                            "raw_records": canonical.raw_records,
                            "digest": canonical.digest,
                            "status": "skipped_by_resume",
                            "skipped_by_resume": True,
                            "run": _run_to_json(pseudo_run),
                        },
                    )
                )
                continue

        output_dir = work_dir / "shard_outputs" / shard.shard_id
        if manifest is not None:
            manifest.mark_running(
                shard,
                worker_id=assignment.worker_id,
                gpu_id=assignment.gpu_id,
                cpu_core_range=assignment.cpu_core_range,
            )
        try:
            run = _run_fasim(
                label=shard.shard_id,
                fasim_bin=fasim_bin,
                target=shard.shard_fasta_path,
                rna=rna,
                rule=rule,
                output_mode=output_mode,
                output_dir=output_dir,
                log_dir=work_dir / "logs",
                env_overrides=worker_env,
                fasim_args=fasim_args,
                cpu_core_range=assignment.cpu_core_range,
            )
            if run.output_path is None:
                raise RuntimeError(f"{shard.shard_id} completed without output path")
            canonical = _canonicalize_file(run.output_path, output_mode)
            if manifest is not None:
                manifest.mark_completed(
                    shard,
                    run=run,
                    canonical=canonical,
                    worker_id=assignment.worker_id,
                    gpu_id=assignment.gpu_id,
                    cpu_core_range=assignment.cpu_core_range,
                )
        except FasimRunError as e:
            if manifest is not None:
                manifest.mark_failed(
                    shard,
                    run=e.run,
                    worker_id=assignment.worker_id,
                    gpu_id=assignment.gpu_id,
                    cpu_core_range=assignment.cpu_core_range,
                )
            if not keep_going:
                raise
            shard_results.append(
                ScheduledShardResult(
                    shard_id=shard.shard_id,
                    output_path=None,
                    raw_records=0,
                    unique_records=0,
                    status="failed",
                    report={
                        **_shard_to_json(shard),
                        "worker_id": assignment.worker_id,
                        "gpu_id": assignment.gpu_id,
                        "cpu_core_range": assignment.cpu_core_range,
                        "records": None,
                        "raw_records": None,
                        "digest": None,
                        "status": "failed",
                        "skipped_by_resume": False,
                        "run": _run_to_json(e.run),
                    },
                )
            )
            continue
        shard_results.append(
            ScheduledShardResult(
                shard_id=shard.shard_id,
                output_path=run.output_path,
                raw_records=canonical.raw_records,
                unique_records=len(canonical.rows),
                status="completed",
                report={
                    **_shard_to_json(shard),
                    "worker_id": assignment.worker_id,
                    "gpu_id": assignment.gpu_id,
                    "cpu_core_range": assignment.cpu_core_range,
                    "records": len(canonical.rows),
                    "raw_records": canonical.raw_records,
                    "digest": canonical.digest,
                    "status": "completed",
                    "skipped_by_resume": False,
                    "run": _run_to_json(run),
                },
            )
        )
    t1 = time.perf_counter()

    return WorkerResult(
        worker_id=assignment.worker_id,
        gpu_id=assignment.gpu_id,
        cpu_core_range=assignment.cpu_core_range,
        estimated_length=sum(shard.estimated_length for shard in assignment.shards),
        estimated_cells=_sum_estimated_cells(assignment.shards),
        wall_seconds=t1 - t0,
        shard_results=shard_results,
    )


def _run_scheduled_shards(
    *,
    assignments: list[WorkerAssignment],
    fasim_bin: Path,
    rna: Path,
    rule: str,
    output_mode: str,
    work_dir: Path,
    env_overrides: dict[str, str],
    fasim_args: list[str],
    resume_entries: dict[str, dict[str, object]],
    run_config_digest: str,
    manifest: RunManifest | None = None,
    resume: bool = False,
    keep_going: bool = False,
) -> list[WorkerResult]:
    if len(assignments) == 1:
        return [
            _run_worker(
                assignment=assignments[0],
                fasim_bin=fasim_bin,
                rna=rna,
                rule=rule,
                output_mode=output_mode,
                work_dir=work_dir,
                env_overrides=env_overrides,
                fasim_args=fasim_args,
                resume_entries=resume_entries,
                run_config_digest=run_config_digest,
                manifest=manifest,
                resume=resume,
                keep_going=keep_going,
            )
        ]

    results: list[WorkerResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(assignments)) as executor:
        futures = [
            executor.submit(
                _run_worker,
                assignment=assignment,
                fasim_bin=fasim_bin,
                rna=rna,
                rule=rule,
                output_mode=output_mode,
                work_dir=work_dir,
                env_overrides=env_overrides,
                fasim_args=fasim_args,
                resume_entries=resume_entries,
                run_config_digest=run_config_digest,
                manifest=manifest,
                resume=resume,
                keep_going=keep_going,
            )
            for assignment in assignments
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return sorted(results, key=lambda result: result.worker_id)


def _find_output_file(output_dir: Path, output_mode: str) -> Path:
    if output_mode == "lite":
        files = sorted(output_dir.glob("*-TFOsorted.lite"))
    else:
        files = [
            p
            for p in sorted(output_dir.glob("*-TFOsorted"))
            if not p.name.endswith(".lite")
        ]

    if len(files) != 1:
        names = ", ".join(p.name for p in files) or "<none>"
        raise RuntimeError(
            f"expected exactly one {output_mode} output in {output_dir}, found: {names}"
        )
    return files[0]


def _default_header(output_mode: str) -> str:
    return LITE_HEADER if output_mode == "lite" else TFOSORTED_HEADER


def _convert_sort_value(value: str) -> tuple[int, object]:
    if re.match(r"^-?\d+$", value):
        return (0, int(value))
    try:
        return (1, float(value))
    except ValueError:
        return (2, value)


def _row_sort_key(header: str, row: str) -> tuple:
    cols = header.split("\t")
    idx = {name: i for i, name in enumerate(cols)}
    parts = row.split("\t")
    preferred = [
        "Chr",
        "StartInGenome",
        "EndInGenome",
        "Strand",
        "Rule",
        "QueryStart",
        "QueryEnd",
        "StartInSeq",
        "EndInSeq",
        "Direction",
        "Score",
        "Nt(bp)",
        "MeanIdentity(%)",
        "MeanStability",
        "Class",
        "MidPoint",
        "Center",
        "TFO sequence",
        "TTS sequence",
    ]
    key: list[object] = []
    for name in preferred:
        pos = idx.get(name)
        if pos is not None and pos < len(parts):
            key.append((name, _convert_sort_value(parts[pos])))
    key.append(("row", row))
    return tuple(key)


def _canonical_from_rows(header: str, rows: list[str]) -> CanonicalOutput:
    unique_rows = sorted(set(rows), key=lambda row: _row_sort_key(header, row))
    content = header + "\n"
    if unique_rows:
        content += "\n".join(unique_rows) + "\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return CanonicalOutput(
        header=header,
        rows=unique_rows,
        raw_records=len(rows),
        digest=digest,
        content=content,
    )


def _canonicalize_file(path: Path, output_mode: str) -> CanonicalOutput:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return _canonical_from_rows(_default_header(output_mode), [])
    header = lines[0].rstrip("\r\n")
    rows = [line.rstrip("\r\n") for line in lines[1:] if line.strip()]
    return _canonical_from_rows(header, rows)


def _merge_outputs(paths: list[Path], output_mode: str, output_path: Path) -> CanonicalOutput:
    header: str | None = None
    rows: list[str] = []

    for path in paths:
        canonical = _canonicalize_file(path, output_mode)
        if header is None:
            header = canonical.header
        elif canonical.header != header:
            raise RuntimeError(f"output header mismatch in {path}")
        rows.extend(canonical.rows)

    merged = _canonical_from_rows(header or _default_header(output_mode), rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(merged.content, encoding="utf-8")
    return merged


def _shard_to_json(shard: Shard) -> dict[str, object]:
    return {
        "shard_id": shard.shard_id,
        "target_name": shard.target_name,
        "target_start": shard.target_start,
        "target_end": shard.target_end,
        "shard_fasta_path": str(shard.shard_fasta_path),
        "estimated_length": shard.estimated_length,
        "estimated_windows": shard.estimated_windows,
        "estimated_cells": shard.estimated_cells,
    }


def _run_to_json(run: RunResult) -> dict[str, object]:
    return {
        "label": run.label,
        "cmd": run.cmd,
        "env_overrides": run.env_overrides,
        "wall_seconds": run.wall_seconds,
        "stdout_path": str(run.stdout_path),
        "stderr_path": str(run.stderr_path),
        "output_dir": str(run.output_dir),
        "output_path": str(run.output_path) if run.output_path else None,
        "exit_code": run.exit_code,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Fasim once per target FASTA contig and deterministically merge "
            "record output. Shards remain contig-level; workers are independent "
            "Fasim subprocesses."
        )
    )
    parser.add_argument("--fasim-bin", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--rna", required=True, type=Path)
    parser.add_argument("--rule", default="0")
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument(
        "--output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
        help="Fasim record schema to merge deterministically.",
    )
    parser.add_argument(
        "--validate-single",
        action="store_true",
        help="Also run the original multi-contig target and compare canonical digest.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment override passed to every Fasim worker. Repeatable.",
    )
    parser.add_argument(
        "--fasim-arg",
        action="append",
        default=[],
        help="Extra single argument appended to each Fasim invocation. Repeatable.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of process-level shard workers to run in parallel.",
    )
    parser.add_argument(
        "--workers-per-gpu",
        type=int,
        default=None,
        help=(
            "Derive worker count as len(--gpu-ids) * N. This is mutually "
            "exclusive with --workers and does not change the default policy."
        ),
    )
    parser.add_argument(
        "--gpu-ids",
        default=None,
        help="Comma-separated CUDA_VISIBLE_DEVICES values assigned to workers.",
    )
    parser.add_argument(
        "--cpu-core-ranges",
        default=None,
        help="Comma-separated taskset CPU ranges, one per worker.",
    )
    parser.add_argument(
        "--cpu-pool",
        default=None,
        help="CPU core pool used with --auto-cpu-core-ranges, e.g. 0-23.",
    )
    parser.add_argument(
        "--cpu-cores-per-worker",
        type=int,
        default=None,
        help="Number of CPU cores assigned to each worker in auto CPU binding mode.",
    )
    parser.add_argument(
        "--auto-cpu-core-ranges",
        action="store_true",
        help="Derive one taskset CPU range per worker from --cpu-pool.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to run_manifest.json for resumable audited sharded runs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse manifest-compatible completed shard outputs.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Clear the work directory and rerun all shards.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first failed shard. This is the default.",
    )
    group.add_argument(
        "--keep-going",
        action="store_true",
        help="Record failed shards and continue other workers; final run is incomplete.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    fasim_bin = args.fasim_bin.resolve()
    target = args.target.resolve()
    rna = args.rna.resolve()
    work_dir = args.work_dir.resolve()
    manifest_path = args.manifest.resolve() if args.manifest else work_dir / "run_manifest.json"
    manifest_enabled = args.manifest is not None

    if not fasim_bin.exists():
        raise RuntimeError(f"missing Fasim binary: {fasim_bin}")
    if not target.exists():
        raise RuntimeError(f"missing target FASTA: {target}")
    if not rna.exists():
        raise RuntimeError(f"missing RNA FASTA: {rna}")
    if args.resume and args.force:
        raise RuntimeError("--resume and --force cannot be used together")
    if args.keep_going and args.validate_single:
        raise RuntimeError("--keep-going cannot be combined with --validate-single")

    if manifest_enabled and work_dir.exists() and manifest_path.exists() and not args.resume and not args.force:
        raise RuntimeError(
            "existing manifest/work-dir found; use --resume or --force to continue safely"
        )
    if args.force and work_dir.exists():
        shutil.rmtree(work_dir)
    elif not manifest_enabled and work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "shards").mkdir(parents=True, exist_ok=True)
    (work_dir / "logs").mkdir(parents=True, exist_ok=True)

    records = _read_fasta(target)
    if not records:
        raise RuntimeError(f"no FASTA records found in {target}")

    env_overrides = _parse_env_overrides(args.env)
    gpu_ids = _parse_csv_list(args.gpu_ids, name="--gpu-ids")
    explicit_cpu_core_ranges = _parse_csv_list(
        args.cpu_core_ranges,
        name="--cpu-core-ranges",
    )
    worker_count, workers_derived_from_gpu_ids = _resolve_worker_count(
        workers=args.workers,
        workers_per_gpu=args.workers_per_gpu,
        gpu_ids=gpu_ids,
    )
    cpu_core_ranges = _resolve_cpu_core_ranges(
        explicit_cpu_core_ranges=explicit_cpu_core_ranges,
        auto_cpu_core_ranges=bool(args.auto_cpu_core_ranges),
        cpu_pool=args.cpu_pool,
        cpu_cores_per_worker=args.cpu_cores_per_worker,
        worker_count=worker_count,
    )
    shards = _write_shard_fastas(records, work_dir / "shards")
    shard_plan = [_shard_to_json(shard) for shard in shards]
    shard_plan_digest = _json_digest(shard_plan)
    target_digest = _sha256_file(target)
    rna_digest = _sha256_file(rna)
    git_commit = _git_commit()
    run_config_digest = _build_run_config_digest(
        args=args,
        target=target,
        target_digest=target_digest,
        rna=rna,
        rna_digest=rna_digest,
        fasim_bin=fasim_bin,
        env_overrides=env_overrides,
        worker_count=worker_count,
        workers_derived_from_gpu_ids=workers_derived_from_gpu_ids,
        gpu_ids=gpu_ids,
        cpu_core_ranges=cpu_core_ranges,
        shard_plan=shard_plan,
        shard_plan_digest=shard_plan_digest,
        git_commit=git_commit,
    )
    assignments = _assign_shards_to_workers(
        shards,
        worker_count=worker_count,
        gpu_ids=gpu_ids,
        cpu_core_ranges=cpu_core_ranges,
    )
    shard_plan_path = work_dir / "shard_plan.json"
    shard_plan_path.write_text(
        json.dumps(shard_plan, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest: RunManifest | None = None
    if manifest_enabled:
        if args.resume:
            if not manifest_path.exists():
                raise RuntimeError(f"--resume requires existing manifest: {manifest_path}")
            old_manifest = RunManifest.load(manifest_path)
            if old_manifest.payload.get("run_config_digest") != run_config_digest:
                _eprint("resume manifest run_config_digest differs; incompatible shards will rerun")
            old_by_shard = _manifest_by_shard(old_manifest)
        else:
            old_by_shard = {}
        manifest = RunManifest.create(
            path=manifest_path,
            args=args,
            target=target,
            target_digest=target_digest,
            rna=rna,
            rna_digest=rna_digest,
            shards=shards,
            shard_plan_digest=shard_plan_digest,
            worker_count=worker_count,
            workers_derived_from_gpu_ids=workers_derived_from_gpu_ids,
            gpu_ids=gpu_ids,
            cpu_core_ranges=cpu_core_ranges,
            env_overrides=env_overrides,
            run_config_digest=run_config_digest,
            git_commit=git_commit,
        )
        for entry in manifest.payload.get("per_shard", []):
            if isinstance(entry, dict):
                entry["run_config_digest"] = run_config_digest
        manifest.write()
        resume_entries = old_by_shard if args.resume else {}
    else:
        resume_entries = {}

    per_shard: list[dict[str, object]] = []
    shard_output_paths: list[Path] = []
    sharded_raw_records = 0
    sharded_unique_records = 0
    worker_results = _run_scheduled_shards(
        assignments=assignments,
        fasim_bin=fasim_bin,
        rna=rna,
        rule=str(args.rule),
        output_mode=args.output_mode,
        work_dir=work_dir,
        env_overrides=env_overrides,
        fasim_args=args.fasim_arg,
        resume_entries=resume_entries,
        run_config_digest=run_config_digest,
        manifest=manifest,
        resume=args.resume,
        keep_going=args.keep_going,
    )

    shard_order = {shard.shard_id: idx for idx, shard in enumerate(shards)}
    scheduled_results = [
        shard_result
        for worker_result in worker_results
        for shard_result in worker_result.shard_results
    ]
    scheduled_results.sort(key=lambda result: shard_order[result.shard_id])

    for shard_result in scheduled_results:
        if shard_result.status == "failed":
            per_shard.append(shard_result.report)
            continue
        sharded_raw_records += shard_result.raw_records
        sharded_unique_records += shard_result.unique_records
        if shard_result.output_path is not None:
            shard_output_paths.append(shard_result.output_path)
        per_shard.append(shard_result.report)

    failed_shards = [
        shard_result.shard_id
        for shard_result in scheduled_results
        if shard_result.status == "failed"
    ]
    resumed_shards = [
        shard_result.shard_id
        for shard_result in scheduled_results
        if shard_result.status == "skipped_by_resume"
    ]

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
                shard_result.unique_records for shard_result in result.shard_results
                if shard_result.status != "failed"
            ),
            "raw_records": sum(
                shard_result.raw_records for shard_result in result.shard_results
                if shard_result.status != "failed"
            ),
        }
        for result in worker_results
    ]

    merged_name = "merged-TFOsorted.lite" if args.output_mode == "lite" else "merged-TFOsorted"
    complete_run = not failed_shards
    merged_output_path = work_dir / "merged" / merged_name
    partial_merged_output_path = work_dir / "merged" / ("partial-" + merged_name)
    if complete_run:
        merged = _merge_outputs(shard_output_paths, args.output_mode, merged_output_path)
        partial_merged = None
    else:
        merged = None
        partial_merged = _merge_outputs(
            shard_output_paths,
            args.output_mode,
            partial_merged_output_path,
        )

    single_digest = None
    single_records = None
    single_raw_records = None
    single_run_json = None
    digest_match = None
    single_output_path = None
    if args.validate_single and complete_run:
        single_run = _run_fasim(
            label="single",
            fasim_bin=fasim_bin,
            target=target,
            rna=rna,
            rule=str(args.rule),
            output_mode=args.output_mode,
            output_dir=work_dir / "single_output",
            log_dir=work_dir / "logs",
            env_overrides=env_overrides,
            fasim_args=args.fasim_arg,
        )
        single = _canonicalize_file(single_run.output_path, args.output_mode)
        single_digest = single.digest
        single_records = len(single.rows)
        single_raw_records = single.raw_records
        single_run_json = _run_to_json(single_run)
        single_output_path = str(single_run.output_path)
        digest_match = single.digest == merged.digest

    merged_records = len(merged.rows) if merged is not None else None
    merged_raw_records = merged.raw_records if merged is not None else None
    merged_digest = merged.digest if merged is not None else None
    partial_merged_digest = partial_merged.digest if partial_merged is not None else None
    duplicate_records_removed = (
        sharded_raw_records - len(merged.rows)
        if merged is not None
        else None
    )
    run_status = "completed" if complete_run else "incomplete"
    if manifest is not None:
        manifest.finalize(
            run_status=run_status,
            merged_records=merged_records,
            duplicate_removed=duplicate_records_removed,
            merged_digest=merged_digest,
            partial_merged_digest=partial_merged_digest,
            failed_shards=failed_shards,
            resumed_shards=resumed_shards,
        )

    report = {
        "schema_version": 1,
        "mode": "contig_shards",
        "run_status": run_status,
        "run_id": manifest.payload.get("run_id") if manifest else None,
        "manifest": str(manifest_path) if manifest_enabled else None,
        "run_config_digest": run_config_digest,
        "git_commit": git_commit,
        "runner_version": RUNNER_VERSION,
        "target": str(target),
        "target_fasta_digest": target_digest,
        "rna": str(rna),
        "rna_fasta_digest": rna_digest,
        "rule": str(args.rule),
        "output_mode": args.output_mode,
        "env_overrides": env_overrides,
        "worker_count": worker_count,
        "gpu_ids": gpu_ids,
        "workers_per_gpu": args.workers_per_gpu,
        "workers_derived_from_gpu_ids": workers_derived_from_gpu_ids,
        "gpu_sharing_mode": _gpu_sharing_mode(
            worker_count=worker_count,
            gpu_ids=gpu_ids,
        ),
        "cpu_core_ranges": cpu_core_ranges,
        "cpu_pool": args.cpu_pool,
        "cpu_cores_per_worker": args.cpu_cores_per_worker,
        "auto_cpu_core_ranges": bool(args.auto_cpu_core_ranges),
        "taskset_enabled": bool(cpu_core_ranges),
        "shard_plan": str(shard_plan_path),
        "shard_plan_digest": shard_plan_digest,
        "shard_count": len(shards),
        "shard_ids": [shard.shard_id for shard in shards],
        "per_worker": per_worker,
        "per_shard": per_shard,
        "sharded_records": sharded_raw_records,
        "sharded_unique_records": sharded_unique_records,
        "merged_records": merged_records,
        "merged_raw_records": merged_raw_records,
        "merged_digest": merged_digest,
        "merged_output": str(merged_output_path) if merged is not None else None,
        "partial_merged_digest": partial_merged_digest,
        "partial_merged_output": (
            str(partial_merged_output_path) if partial_merged is not None else None
        ),
        "duplicate_records_removed": duplicate_records_removed,
        "failed_shards": failed_shards,
        "resumed_shards": resumed_shards,
        "single_records": single_records,
        "single_raw_records": single_raw_records,
        "single_digest": single_digest,
        "single_output": single_output_path,
        "single_run": single_run_json,
        "single_vs_sharded_digest_match": digest_match,
    }

    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failed_shards:
        raise RuntimeError(f"sharded run incomplete; failed shards: {','.join(failed_shards)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _eprint(f"error: {exc}")
        raise SystemExit(1)
