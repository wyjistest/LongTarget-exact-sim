#!/usr/bin/env python3
import argparse
import concurrent.futures
import dataclasses
import datetime
import heapq
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
from collections.abc import Iterable
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
CANONICAL_SORT_COLUMNS = (
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
)
TOPK_MODES = ("score", "stability", "nt_score")
TOPK_ROW_KEY_COLUMNS = (
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
)
GASAL2_DEFAULT_MAX_QUERY_LEN = 2812
GASAL2_COLUMN_PRUNED_PRESET_MAX_BATCH = 30000
GASAL2_COLUMN_PRUNED_PRESET_MAX_STREAMS = 16
GASAL2_COLUMN_PRUNED_PRESET_PRUNE_MAX_PER_TASK = 64
LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_CONTRACT = (
    "long_query_streaming_scoreinfo_gpu_trust_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_GROUP32_CONTRACT = (
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_GROUP32_PROFILE = (
    "malat1_like_group32_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_TRUST_CONTRACT = (
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_TRUST_GROUP32_CONTRACT = (
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_TRUST_GROUP32_PROFILE = (
    "malat1_like_two_contract_group32_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_RUNTIME_CONTRACT = (
    "long_query_streaming_scoreinfo_gpu_two_contract_runtime_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_RUNTIME_GROUP32_CONTRACT = (
    "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_RUNTIME_GROUP32_PROFILE = (
    "malat1_like_two_contract_runtime_group32_experimental_v1"
)
LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_DECISION = "experimental_external_digest_gate"


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
    group_member_count: int = 1
    group_member_headers: tuple[str, ...] = ()
    group_member_names: tuple[str, ...] = ()
    group_member_ranges: tuple[str, ...] = ()
    group_member_input_digests: tuple[str, ...] = ()


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
    canonical: "CanonicalOutput | None"
    raw_output: "RawOutput | None"
    canonicalize_seconds: float
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
    canonicalize_seconds: float
    shard_results: list[ScheduledShardResult]


@dataclasses.dataclass(frozen=True)
class CanonicalOutput:
    header: str
    rows: list[str]
    raw_records: int
    digest: str
    content: str


@dataclasses.dataclass(frozen=True)
class RawOutput:
    header: str
    rows: list[str]
    raw_records: int
    digest: str


@dataclasses.dataclass(frozen=True)
class CanonicalSortContext:
    positions: tuple[tuple[str, int], ...]


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


def _benchmark_number(payload: dict[str, object], key: str) -> float:
    value = payload.get(key, 0)
    return float(value)


def _result_contract(args: argparse.Namespace) -> str:
    if getattr(
        args, "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32", False
    ):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_RUNTIME_GROUP32_CONTRACT
    if getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_runtime", False):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_RUNTIME_CONTRACT
    if getattr(
        args, "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32", False
    ):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_TRUST_GROUP32_CONTRACT
    if getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_trust", False):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_TRUST_CONTRACT
    if getattr(args, "long_query_streaming_scoreinfo_gpu_trust_group32", False):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_GROUP32_CONTRACT
    if args.long_query_streaming_scoreinfo_gpu_trust:
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_CONTRACT
    if args.gasal2_top5_column_pruned_scoreinfo:
        return "gasal2_top5_column_pruned_scoreinfo_artifact_v1"
    if args.gasal2_top5_scoreinfo_prune_max_per_task is not None:
        return "gasal2_top5_scoreinfo_artifact_v1"
    if args.topk_summary_only:
        return "topk_summary_artifact_v1"
    return "merged_output_v1"


def _long_query_streaming_scoreinfo_gpu_profile(args: argparse.Namespace) -> str | None:
    if getattr(args, "long_query_streaming_scoreinfo_gpu_trust_group32", False):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_GROUP32_PROFILE
    if getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32", False):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_TRUST_GROUP32_PROFILE
    if getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32", False):
        return LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_RUNTIME_GROUP32_PROFILE
    return None


def _long_query_streaming_scoreinfo_gpu_uses_external_digest_gate(
    args: argparse.Namespace,
) -> bool:
    return (
        getattr(args, "long_query_streaming_scoreinfo_gpu_trust", False)
        or getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_trust", False)
        or getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32", False)
        or getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_runtime", False)
        or getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32", False)
    )


def _gasal2_top5_activation_error(
    args: argparse.Namespace,
    benchmark_sums: dict[str, object],
    benchmark_shards: int,
    shard_count: int,
) -> str | None:
    if not args.gasal2_top5_column_pruned_scoreinfo:
        return None
    if benchmark_shards != shard_count:
        return (
            "--gasal2-top5-column-pruned-scoreinfo requires active "
            f"GASAL2/exact-scoreInfo GPU shards; benchmark_shards={benchmark_shards} "
            f"shard_count={shard_count}"
        )

    required_per_shard = (
        "fasim_top5_gasal2_gpu_scoreinfo_requested",
        "fasim_top5_gasal2_gpu_scoreinfo_active",
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled",
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled",
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled",
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled",
    )
    for key in required_per_shard:
        if _benchmark_number(benchmark_sums, key) != float(shard_count):
            return (
                "--gasal2-top5-column-pruned-scoreinfo requires active "
                f"GASAL2/exact-scoreInfo GPU shards; {key}="
                f"{benchmark_sums.get(key, 0)} shard_count={shard_count}"
            )

    required_positive = (
        "fasim_gasal2_requests",
        "fasim_gasal2_score_requests",
        "fasim_gasal2_traceback_requests",
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks",
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows",
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank",
    )
    for key in required_positive:
        if _benchmark_number(benchmark_sums, key) <= 0.0:
            return (
                "--gasal2-top5-column-pruned-scoreinfo requires active "
                f"GASAL2/exact-scoreInfo GPU shards; {key}={benchmark_sums.get(key, 0)}"
            )

    required_zero = (
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
        "fasim_gasal2_fallbacks",
        "fasim_gasal2_length_guard_fallbacks",
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows",
    )
    for key in required_zero:
        if _benchmark_number(benchmark_sums, key) != 0.0:
            return (
                "--gasal2-top5-column-pruned-scoreinfo requires active "
                f"GASAL2/exact-scoreInfo GPU shards without fallback; "
                f"{key}={benchmark_sums.get(key, 0)}"
            )
    return None


def _gasal2_top5_activation_report_fields(
    args: argparse.Namespace,
    benchmark_sums: dict[str, object],
    benchmark_shards: int,
    shard_count: int,
) -> dict[str, object]:
    if not args.gasal2_top5_column_pruned_scoreinfo:
        return {
            "gasal2_top5_activation_verified": None,
            "gasal2_top5_activation_error": None,
        }
    error = _gasal2_top5_activation_error(
        args,
        benchmark_sums,
        benchmark_shards,
        shard_count,
    )
    return {
        "gasal2_top5_activation_verified": error is None,
        "gasal2_top5_activation_error": error,
    }


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


def _record_input_digest(record: FastaRecord) -> str:
    return _sha256_text(f"{record.header}\n{record.sequence}\n")


def _write_shard_fastas(
    records: list[FastaRecord],
    shard_dir: Path,
    *,
    group_target_records: int | None = None,
) -> list[Shard]:
    shard_dir.mkdir(parents=True, exist_ok=True)
    shards: list[Shard] = []

    group_size = group_target_records or 1
    if group_size < 1:
        raise ValueError("group_target_records must be >= 1")

    for idx in range(0, len(records), group_size):
        group_records = records[idx : idx + group_size]
        group_index = len(shards)
        member_meta = [
            (*_parse_target_header(record), record)
            for record in group_records
        ]
        if len(group_records) == 1:
            target_name, start, end, _record = member_meta[0]
            shard_id = f"shard_{group_index:04d}_{_sanitize_for_path(target_name)}"
            shard_target_name = target_name
            shard_target_start = start
            shard_target_end = end
        else:
            target_name = f"group_{group_index:04d}"
            shard_id = f"shard_{group_index:04d}_{target_name}"
            shard_target_name = target_name
            shard_target_start = 0
            shard_target_end = 0
        shard_path = shard_dir / f"{shard_id}.fa"
        shard_text = "".join(
            f"{record.header}\n{_wrap_sequence(record.sequence)}\n"
            for _, _, _, record in member_meta
        )
        shard_path.write_text(shard_text, encoding="utf-8")
        shards.append(
            Shard(
                shard_id=shard_id,
                target_name=shard_target_name,
                target_start=shard_target_start,
                target_end=shard_target_end,
                shard_fasta_path=shard_path,
                estimated_length=sum(len(record.sequence) for _, _, _, record in member_meta),
                estimated_windows=None,
                estimated_cells=None,
                group_member_count=len(group_records),
                group_member_headers=tuple(record.header for _, _, _, record in member_meta),
                group_member_names=tuple(name for name, _, _, _ in member_meta),
                group_member_ranges=tuple(
                    f"{start}-{end}" for _, start, end, _ in member_meta
                ),
                group_member_input_digests=tuple(
                    _record_input_digest(record) for _, _, _, record in member_meta
                ),
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


GASAL2_COLUMN_PRUNED_PRESET_ALLOWED_ENV = frozenset(
    {
        "FASIM_ALIGN_GASAL2_BATCH",
        "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN",
        "FASIM_ALIGN_GASAL2_STREAMS",
        "FASIM_TOP5_GASAL2_SCOREINFO_EMIT_RANK_OBSERVE",
        "FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE",
        "FASIM_VERBOSE",
    }
)


def _reject_unknown_gasal2_column_pruned_preset_env(
    args: argparse.Namespace,
    env_overrides: dict[str, str],
) -> None:
    if not args.gasal2_top5_column_pruned_scoreinfo:
        return
    unknown = sorted(
        key
        for key in env_overrides
        if key not in GASAL2_COLUMN_PRUNED_PRESET_ALLOWED_ENV
    )
    if unknown:
        raise RuntimeError(
            "--gasal2-top5-column-pruned-scoreinfo cannot be combined "
            "with --env for: " + ", ".join(unknown)
        )


def _fasim_binary_has_gasal2_support(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"failed to inspect Fasim binary {path}: {exc}") from exc
    return b"benchmark.fasim_gasal2_built=1" in data


def _requires_gasal2_enabled_binary(args: argparse.Namespace) -> bool:
    return (
        args.gasal2_top5_scoreinfo_prune_max_per_task is not None
        or args.gasal2_single_pass_topn
        or args.long_query_streaming_scoreinfo_gpu_trust
        or getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_trust", False)
        or getattr(args, "long_query_streaming_scoreinfo_gpu_two_contract_runtime", False)
    )


def _rna_query_length(records: list[FastaRecord]) -> int:
    return sum(len(record.sequence) for record in records)


def _gasal2_runner_max_query_len(env_overrides: dict[str, str]) -> int:
    value = env_overrides.get("FASIM_ALIGN_GASAL2_MAX_QUERY_LEN")
    if value is None or value.strip() == "":
        return GASAL2_DEFAULT_MAX_QUERY_LEN
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(
            "--env FASIM_ALIGN_GASAL2_MAX_QUERY_LEN must be an integer"
        ) from exc
    return parsed


def _gasal2_runner_batch(env_overrides: dict[str, str]) -> int | None:
    value = env_overrides.get("FASIM_ALIGN_GASAL2_BATCH")
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError("--env FASIM_ALIGN_GASAL2_BATCH must be an integer") from exc


def _gasal2_runner_streams(env_overrides: dict[str, str]) -> int | None:
    value = env_overrides.get("FASIM_ALIGN_GASAL2_STREAMS")
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError("--env FASIM_ALIGN_GASAL2_STREAMS must be an integer") from exc


def _gasal2_top5_query_preflight_error(
    args: argparse.Namespace,
    env_overrides: dict[str, str],
    rna_records: list[FastaRecord],
) -> str | None:
    if not args.gasal2_top5_column_pruned_scoreinfo:
        return None
    try:
        batch = _gasal2_runner_batch(env_overrides)
    except RuntimeError as exc:
        return str(exc)
    if batch is not None:
        if batch <= 0:
            return (
                "--gasal2-top5-column-pruned-scoreinfo requires positive "
                "FASIM_ALIGN_GASAL2_BATCH"
            )
        if batch > GASAL2_COLUMN_PRUNED_PRESET_MAX_BATCH:
            return (
                "--gasal2-top5-column-pruned-scoreinfo cannot override "
                "FASIM_ALIGN_GASAL2_BATCH above verified limit "
                f"{GASAL2_COLUMN_PRUNED_PRESET_MAX_BATCH}"
            )
    try:
        streams = _gasal2_runner_streams(env_overrides)
    except RuntimeError as exc:
        return str(exc)
    if streams is not None and streams <= 0:
        return (
            "--gasal2-top5-column-pruned-scoreinfo requires positive "
            "FASIM_ALIGN_GASAL2_STREAMS"
        )
    if streams is not None and streams > GASAL2_COLUMN_PRUNED_PRESET_MAX_STREAMS:
        return (
            "--gasal2-top5-column-pruned-scoreinfo cannot override "
            "FASIM_ALIGN_GASAL2_STREAMS above GASAL2 bridge limit "
            f"{GASAL2_COLUMN_PRUNED_PRESET_MAX_STREAMS}"
        )
    try:
        max_query_len = _gasal2_runner_max_query_len(env_overrides)
    except RuntimeError as exc:
        return str(exc)
    query_len = _rna_query_length(rna_records)
    if max_query_len <= 0:
        return (
            "--gasal2-top5-column-pruned-scoreinfo requires positive "
            "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN"
        )
    if max_query_len > GASAL2_DEFAULT_MAX_QUERY_LEN:
        return (
            "--gasal2-top5-column-pruned-scoreinfo cannot override "
            "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN above verified limit "
            f"{GASAL2_DEFAULT_MAX_QUERY_LEN}"
        )
    if max_query_len > 0 and query_len > max_query_len:
        return (
            "--gasal2-top5-column-pruned-scoreinfo requires active "
            "GASAL2/exact-scoreInfo GPU shards; query length "
            f"{query_len} exceeds FASIM_ALIGN_GASAL2_MAX_QUERY_LEN={max_query_len}"
        )
    return None


def _gasal2_top5_query_preflight_report_fields(
    args: argparse.Namespace,
    env_overrides: dict[str, str],
    rna_records: list[FastaRecord],
) -> dict[str, object]:
    if not args.gasal2_top5_column_pruned_scoreinfo:
        return {
            "gasal2_top5_query_preflight_supported": None,
            "gasal2_top5_query_preflight_error": None,
            "gasal2_top5_query_preflight_query_len": None,
            "gasal2_top5_query_preflight_max_query_len": None,
        }

    query_len = _rna_query_length(rna_records)
    try:
        max_query_len: int | None = _gasal2_runner_max_query_len(env_overrides)
    except RuntimeError as exc:
        return {
            "gasal2_top5_query_preflight_supported": False,
            "gasal2_top5_query_preflight_error": str(exc),
            "gasal2_top5_query_preflight_query_len": query_len,
            "gasal2_top5_query_preflight_max_query_len": None,
        }

    error = _gasal2_top5_query_preflight_error(args, env_overrides, rna_records)
    return {
        "gasal2_top5_query_preflight_supported": error is None,
        "gasal2_top5_query_preflight_error": error,
        "gasal2_top5_query_preflight_query_len": query_len,
        "gasal2_top5_query_preflight_max_query_len": max_query_len,
    }


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
            "result_contract": _result_contract(args),
            "target_fasta": str(target),
            "target_fasta_digest": target_digest,
            "target_record_count": sum(shard.group_member_count for shard in shards),
            "group_target_records": args.group_target_records,
            "grouped_shard_count": len(shards),
            "long_query_streaming_scoreinfo_gpu_trust": bool(
                args.long_query_streaming_scoreinfo_gpu_trust
            ),
            "long_query_streaming_scoreinfo_gpu_trust_group32": bool(
                args.long_query_streaming_scoreinfo_gpu_trust_group32
            ),
            "long_query_streaming_scoreinfo_gpu_two_contract_trust": bool(
                args.long_query_streaming_scoreinfo_gpu_two_contract_trust
            ),
            "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32": bool(
                args.long_query_streaming_scoreinfo_gpu_two_contract_trust_group32
            ),
            "long_query_streaming_scoreinfo_gpu_two_contract_runtime": bool(
                args.long_query_streaming_scoreinfo_gpu_two_contract_runtime
            ),
            "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32": bool(
                args.long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32
            ),
            "long_query_streaming_scoreinfo_gpu_trust_profile": (
                _long_query_streaming_scoreinfo_gpu_profile(args)
            ),
            "long_query_streaming_scoreinfo_gpu_trust_decision": (
                LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_DECISION
                if _long_query_streaming_scoreinfo_gpu_uses_external_digest_gate(args)
                else None
            ),
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
                    "raw_records": None,
                    "raw_topk_only": False,
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
            "topk_summary_output": None,
            "topk_summary_digest": None,
            "topk_summary_payload_digest": None,
            "topk_rows_output": None,
            "topk_rows_digest": None,
            "topk_rows_payload_digest": None,
            "topk_lite_output": None,
            "topk_lite_digest": None,
            "topk_lite_records": None,
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
        self.write()

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
                "raw_topk_only": False,
                "stdout_path": str(run.stdout_path),
                "stderr_path": str(run.stderr_path),
                "exit_code": run.exit_code,
                "env_overrides": run.env_overrides,
                "skipped_by_resume": skipped_by_resume,
            }
        )
        self.write()

    def mark_completed_raw(
        self,
        shard: Shard,
        *,
        run: RunResult,
        raw_output: RawOutput,
        worker_id: int,
        gpu_id: str | None,
        cpu_core_range: str | None,
        skipped_by_resume: bool = False,
    ) -> None:
        if run.output_path is None:
            raise RuntimeError(f"cannot complete {shard.shard_id} without output")
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
                "output_digest": raw_output.digest,
                "records": len(set(raw_output.rows)),
                "raw_records": raw_output.raw_records,
                "raw_topk_only": True,
                "stdout_path": str(run.stdout_path),
                "stderr_path": str(run.stderr_path),
                "exit_code": run.exit_code,
                "env_overrides": run.env_overrides,
                "skipped_by_resume": skipped_by_resume,
            }
        )
        self.write()

    def mark_failed(
        self,
        shard: Shard,
        *,
        run: RunResult | None,
        worker_id: int,
        gpu_id: str | None,
        cpu_core_range: str | None,
    ) -> None:
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
        self.write()

    def finalize(
        self,
        *,
        run_status: str,
        merged_records: int | None,
        duplicate_removed: int | None,
        merged_digest: str | None,
        partial_merged_digest: str | None,
        topk_summary_output: str | None,
        topk_summary_digest: str | None,
        topk_summary_payload_digest: str | None,
        topk_rows_output: str | None,
        topk_rows_digest: str | None,
        topk_rows_payload_digest: str | None,
        topk_lite_output: str | None,
        topk_lite_digest: str | None,
        topk_lite_records: int | None,
        gasal2_top5_activation_verified: bool | None,
        gasal2_top5_activation_error: str | None,
        gasal2_top5_query_preflight_supported: bool | None,
        gasal2_top5_query_preflight_error: str | None,
        gasal2_top5_query_preflight_query_len: int | None,
        gasal2_top5_query_preflight_max_query_len: int | None,
        failed_shards: list[str],
        resumed_shards: list[str],
    ) -> None:
        self.payload.update(
            {
                "run_status": run_status,
                "merged_records": merged_records,
                "duplicate_removed": duplicate_removed,
                "merged_digest": merged_digest,
                "partial_merged_digest": partial_merged_digest,
                "topk_summary_output": topk_summary_output,
                "topk_summary_digest": topk_summary_digest,
                "topk_summary_payload_digest": topk_summary_payload_digest,
                "topk_rows_output": topk_rows_output,
                "topk_rows_digest": topk_rows_digest,
                "topk_rows_payload_digest": topk_rows_payload_digest,
                "topk_lite_output": topk_lite_output,
                "topk_lite_digest": topk_lite_digest,
                "topk_lite_records": topk_lite_records,
                "gasal2_top5_activation_verified": gasal2_top5_activation_verified,
                "gasal2_top5_activation_error": gasal2_top5_activation_error,
                "gasal2_top5_query_preflight_supported": gasal2_top5_query_preflight_supported,
                "gasal2_top5_query_preflight_error": gasal2_top5_query_preflight_error,
                "gasal2_top5_query_preflight_query_len": gasal2_top5_query_preflight_query_len,
                "gasal2_top5_query_preflight_max_query_len": gasal2_top5_query_preflight_max_query_len,
                "failed_shards": failed_shards,
                "resumed_shards": resumed_shards,
            }
        )
        self.write()


def _manifest_by_shard(manifest: RunManifest | None) -> dict[str, dict[str, object]]:
    if manifest is None:
        return {}
    return {
        str(entry["shard_id"]): entry
        for entry in manifest.payload.get("per_shard", [])
        if isinstance(entry, dict) and entry.get("shard_id")
    }


def _manifest_has_verified_gasal2_top5_activation(manifest: RunManifest) -> bool:
    query_len = manifest.payload.get("gasal2_top5_query_preflight_query_len")
    max_query_len = manifest.payload.get("gasal2_top5_query_preflight_max_query_len")
    return (
        manifest.payload.get("gasal2_top5_activation_verified") is True
        and manifest.payload.get("gasal2_top5_activation_error") is None
        and manifest.payload.get("gasal2_top5_query_preflight_supported") is True
        and manifest.payload.get("gasal2_top5_query_preflight_error") is None
        and isinstance(query_len, int)
        and query_len >= 0
        and isinstance(max_query_len, int)
        and max_query_len > 0
        and max_query_len <= GASAL2_DEFAULT_MAX_QUERY_LEN
        and query_len <= max_query_len
    )


def _resume_entries_for_manifest(
    manifest: RunManifest | None,
    args: argparse.Namespace,
    run_config_digest: str,
) -> dict[str, dict[str, object]]:
    if manifest is None:
        return {}
    if manifest.payload.get("run_config_digest") != run_config_digest:
        return {}
    if (
        args.gasal2_top5_column_pruned_scoreinfo
        and not _manifest_has_verified_gasal2_top5_activation(manifest)
    ):
        return {}
    return _manifest_by_shard(manifest)


def _resume_entry_valid(
    *,
    entry: dict[str, object] | None,
    shard: Shard,
    output_mode: str,
    run_config_digest: str,
) -> tuple[bool, CanonicalOutput | None, RawOutput | None, Path | None]:
    if not entry:
        return False, None, None, None
    if entry.get("status") not in {"completed", "skipped_by_resume"}:
        return False, None, None, None
    if entry.get("run_config_digest") != run_config_digest:
        return False, None, None, None
    if entry.get("shard_input_digest") != _sha256_file(shard.shard_fasta_path):
        return False, None, None, None
    output_text = entry.get("output_path")
    digest_text = entry.get("output_digest")
    if not output_text or not digest_text:
        return False, None, None, None
    output_path = Path(str(output_text))
    if not output_path.exists():
        return False, None, None, None
    if bool(entry.get("raw_topk_only")):
        if _sha256_file(output_path) != digest_text:
            return False, None, None, None
        raw_output = _read_raw_output(output_path, output_mode)
        return True, None, raw_output, output_path
    canonical = _canonicalize_file(output_path, output_mode)
    if canonical.digest != digest_text:
        return False, None, None, None
    return True, canonical, None, output_path


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
        "topk_summary": args.topk_summary,
        "topk_summary_only": bool(args.topk_summary_only),
        "shard_output_topk_lite": args.shard_output_topk_lite,
        "group_target_records": args.group_target_records,
        "long_query_streaming_scoreinfo_gpu_trust": bool(
            args.long_query_streaming_scoreinfo_gpu_trust
        ),
        "long_query_streaming_scoreinfo_gpu_trust_group32": bool(
            args.long_query_streaming_scoreinfo_gpu_trust_group32
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_trust": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_trust
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_trust_group32
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_runtime": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_runtime
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32
        ),
        "long_query_streaming_scoreinfo_gpu_trust_profile": (
            _long_query_streaming_scoreinfo_gpu_profile(args)
        ),
        "gasal2_top5_column_pruned_scoreinfo": bool(
            args.gasal2_top5_column_pruned_scoreinfo
        ),
        "gasal2_top5_scoreinfo_prune_max_per_task": (
            args.gasal2_top5_scoreinfo_prune_max_per_task
        ),
        "exact_scoreinfo_gpu_max_per_task": args.exact_scoreinfo_gpu_max_per_task,
        "exact_scoreinfo_gpu_pruned_output": bool(args.exact_scoreinfo_gpu_pruned_output),
        "exact_scoreinfo_gpu_column_pruned_output": bool(
            args.exact_scoreinfo_gpu_column_pruned_output
        ),
        "gasal2_single_pass_topn": bool(args.gasal2_single_pass_topn),
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
    raw_topk_only: bool = False,
) -> WorkerResult:
    worker_env = dict(env_overrides)
    if assignment.gpu_id is not None:
        worker_env["CUDA_VISIBLE_DEVICES"] = assignment.gpu_id
        worker_env["FASIM_CUDA_DEVICE"] = "0"
        worker_env.pop("FASIM_CUDA_DEVICES", None)

    shard_results: list[ScheduledShardResult] = []
    canonicalize_seconds = 0.0
    t0 = time.perf_counter()
    for shard in assignment.shards:
        if resume:
            valid, canonical, raw_output, output_path = _resume_entry_valid(
                entry=resume_entries.get(shard.shard_id),
                shard=shard,
                output_mode=output_mode,
                run_config_digest=run_config_digest,
            )
            if valid and output_path is not None and (canonical is not None or raw_output is not None):
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
                    if canonical is not None:
                        manifest.mark_completed(
                            shard,
                            run=pseudo_run,
                            canonical=canonical,
                            worker_id=assignment.worker_id,
                            gpu_id=assignment.gpu_id,
                            cpu_core_range=assignment.cpu_core_range,
                            skipped_by_resume=True,
                        )
                    elif raw_output is not None:
                        manifest.mark_completed_raw(
                            shard,
                            run=pseudo_run,
                            raw_output=raw_output,
                            worker_id=assignment.worker_id,
                            gpu_id=assignment.gpu_id,
                            cpu_core_range=assignment.cpu_core_range,
                            skipped_by_resume=True,
                        )
                if canonical is not None:
                    records = len(canonical.rows)
                    raw_records = canonical.raw_records
                    digest = canonical.digest
                elif raw_output is not None:
                    records = len(set(raw_output.rows))
                    raw_records = raw_output.raw_records
                    digest = raw_output.digest
                else:
                    records = 0
                    raw_records = 0
                    digest = None
                shard_results.append(
                    ScheduledShardResult(
                        shard_id=shard.shard_id,
                        output_path=output_path,
                        canonical=canonical,
                        raw_output=raw_output,
                        canonicalize_seconds=0.0,
                        raw_records=raw_records,
                        unique_records=records,
                        status="skipped_by_resume",
                        report={
                            **_shard_to_json(shard),
                            "worker_id": assignment.worker_id,
                            "gpu_id": assignment.gpu_id,
                            "cpu_core_range": assignment.cpu_core_range,
                            "records": records,
                            "raw_records": raw_records,
                            "digest": digest,
                            "raw_topk_only": raw_output is not None,
                            "status": "skipped_by_resume",
                            "skipped_by_resume": True,
                            "canonicalize_seconds": 0.0,
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
            canonicalize_start = time.perf_counter()
            if raw_topk_only:
                raw_output = _read_raw_output(run.output_path, output_mode)
                canonical = None
                raw_records = raw_output.raw_records
                unique_records = len(set(raw_output.rows))
                digest = raw_output.digest
            else:
                raw_output = None
                canonical = _canonicalize_file(run.output_path, output_mode)
                raw_records = canonical.raw_records
                unique_records = len(canonical.rows)
                digest = canonical.digest
            canonicalize_elapsed = time.perf_counter() - canonicalize_start
            canonicalize_seconds += canonicalize_elapsed
            if manifest is not None and canonical is not None:
                manifest.mark_completed(
                    shard,
                    run=run,
                    canonical=canonical,
                    worker_id=assignment.worker_id,
                    gpu_id=assignment.gpu_id,
                    cpu_core_range=assignment.cpu_core_range,
                )
            elif manifest is not None and raw_output is not None:
                manifest.mark_completed_raw(
                    shard,
                    run=run,
                    raw_output=raw_output,
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
                    canonical=None,
                    raw_output=None,
                    canonicalize_seconds=0.0,
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
                canonical=canonical,
                raw_output=raw_output,
                canonicalize_seconds=canonicalize_elapsed,
                raw_records=raw_records,
                unique_records=unique_records,
                status="completed",
                report={
                    **_shard_to_json(shard),
                    "worker_id": assignment.worker_id,
                    "gpu_id": assignment.gpu_id,
                    "cpu_core_range": assignment.cpu_core_range,
                    "records": unique_records,
                    "raw_records": raw_records,
                    "digest": digest,
                    "raw_topk_only": raw_output is not None,
                    "status": "completed",
                    "skipped_by_resume": False,
                    "canonicalize_seconds": canonicalize_elapsed,
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
        canonicalize_seconds=canonicalize_seconds,
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
    raw_topk_only: bool = False,
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
                raw_topk_only=raw_topk_only,
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
                raw_topk_only=raw_topk_only,
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


def _is_integer_sort_value(value: str) -> bool:
    if not value:
        return False
    if value[0] == "-":
        return len(value) > 1 and value[1:].isdigit()
    return value.isdigit()


def _convert_sort_value(value: str) -> tuple[int, object]:
    if _is_integer_sort_value(value):
        return (0, int(value))
    try:
        return (1, float(value))
    except ValueError:
        return (2, value)


def _canonical_sort_context(header: str) -> CanonicalSortContext:
    cols = header.split("\t")
    idx = {name: i for i, name in enumerate(cols)}
    positions = tuple(
        (name, idx[name])
        for name in CANONICAL_SORT_COLUMNS
        if name in idx
    )
    return CanonicalSortContext(positions=positions)


def _row_sort_key(context: CanonicalSortContext, row: str) -> tuple:
    parts = row.split("\t")
    key: list[object] = []
    for name, pos in context.positions:
        if pos < len(parts):
            key.append((name, _convert_sort_value(parts[pos])))
    key.append(("row", row))
    return tuple(key)


def _row_field(parts: list[str], positions: dict[str, int], key: str) -> str:
    pos = positions.get(key)
    if pos is None or pos >= len(parts):
        return ""
    return parts[pos]


def _row_float(parts: list[str], positions: dict[str, int], key: str) -> float:
    value = _row_field(parts, positions, key)
    if value == "":
        return float("-inf")
    return float(value)


def _topk_rank_key(parts: list[str], positions: dict[str, int], mode: str) -> tuple[float, ...]:
    if mode == "score":
        return (
            _row_float(parts, positions, "Score"),
            _row_float(parts, positions, "Nt(bp)"),
            _row_float(parts, positions, "MeanStability"),
        )
    if mode == "stability":
        return (
            _row_float(parts, positions, "MeanStability"),
            _row_float(parts, positions, "Nt(bp)"),
            _row_float(parts, positions, "Score"),
        )
    if mode == "nt_score":
        return (
            _row_float(parts, positions, "Nt(bp)"),
            _row_float(parts, positions, "Score"),
            _row_float(parts, positions, "MeanStability"),
        )
    raise ValueError(f"unknown top-k mode: {mode}")


def _topk_row_key(parts: list[str], positions: dict[str, int]) -> str:
    return "\t".join(_row_field(parts, positions, column) for column in TOPK_ROW_KEY_COLUMNS)


def _topk_digest(keys: list[str]) -> str:
    return hashlib.sha256(("\n".join(keys) + "\n").encode()).hexdigest()


def _topk_push(
    heap: list[tuple[tuple[float, ...], str, str]],
    item: tuple[tuple[float, ...], str, str],
    k: int,
) -> None:
    if len(heap) < k:
        heapq.heappush(heap, item)
    elif item > heap[0]:
        heapq.heapreplace(heap, item)


def _topk_summary_from_unique_rows(header: str, rows: Iterable[str], k: int) -> dict[str, object]:
    positions = {name: i for i, name in enumerate(header.split("\t"))}
    heaps: dict[str, list[tuple[tuple[float, ...], str, str]]] = {
        mode: [] for mode in TOPK_MODES
    }
    rows_considered = 0
    for row in rows:
        parts = row.split("\t")
        row_key = _topk_row_key(parts, positions)
        for mode in TOPK_MODES:
            _topk_push(heaps[mode], (_topk_rank_key(parts, positions, mode), row_key, row), k)
        rows_considered += 1
    summary: dict[str, object] = {
        "k": k,
        "header": header,
        "rows_considered": rows_considered,
        "modes": {},
    }
    modes = summary["modes"]
    assert isinstance(modes, dict)
    for mode in TOPK_MODES:
        top_items = [
            item
            for item in sorted(heaps[mode], key=lambda item: (item[0], item[1]), reverse=True)
        ]
        keys = [item[1] for item in top_items]
        full_rows = [item[2] for item in top_items]
        modes[mode] = {
            "digest": _topk_digest(keys),
            "keys": keys,
            "rows": full_rows,
        }
    return summary


def _topk_summary_from_deduped_rows(header: str, rows: Iterable[str], k: int) -> dict[str, object]:
    seen: set[str] = set()
    positions = {name: i for i, name in enumerate(header.split("\t"))}
    heaps: dict[str, list[tuple[tuple[float, ...], str, str]]] = {
        mode: [] for mode in TOPK_MODES
    }
    for row in rows:
        if row in seen:
            continue
        seen.add(row)
        parts = row.split("\t")
        row_key = _topk_row_key(parts, positions)
        for mode in TOPK_MODES:
            _topk_push(heaps[mode], (_topk_rank_key(parts, positions, mode), row_key, row), k)
    summary: dict[str, object] = {
        "k": k,
        "header": header,
        "rows_considered": len(seen),
        "modes": {},
    }
    modes = summary["modes"]
    assert isinstance(modes, dict)
    for mode in TOPK_MODES:
        top_items = [
            item
            for item in sorted(heaps[mode], key=lambda item: (item[0], item[1]), reverse=True)
        ]
        keys = [item[1] for item in top_items]
        full_rows = [item[2] for item in top_items]
        modes[mode] = {
            "digest": _topk_digest(keys),
            "keys": keys,
            "rows": full_rows,
        }
    return summary


def _topk_rows(rows: list[list[str]], positions: dict[str, int], mode: str, k: int) -> list[list[str]]:
    heap: list[tuple[tuple[float, ...], str, int, list[str]]] = []
    for ordinal, row in enumerate(rows):
        row_key = _topk_row_key(row, positions)
        item = (_topk_rank_key(row, positions, mode), row_key, ordinal, row)
        if len(heap) < k:
            heapq.heappush(heap, item)
        elif item[:2] > heap[0][:2]:
            heapq.heapreplace(heap, item)
    return [
        item[3]
        for item in sorted(
            heap,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
    ]


def _topk_summary(canonical: CanonicalOutput | None, k: int | None) -> dict[str, object] | None:
    if k is None:
        return None
    if k < 1:
        raise ValueError("--topk-summary must be >= 1")
    if canonical is None:
        return None
    return _topk_summary_from_unique_rows(canonical.header, canonical.rows, k)


def _topk_summary_from_canonicals(
    canonicals: list[CanonicalOutput], k: int | None
) -> dict[str, object] | None:
    if k is None:
        return None
    if k < 1:
        raise ValueError("--topk-summary must be >= 1")
    header: str | None = None
    rows: list[str] = []
    for canonical in canonicals:
        if header is None:
            header = canonical.header
        elif canonical.header != header:
            raise RuntimeError("output header mismatch in shard output")
        rows.extend(canonical.rows)
    return _topk_summary_from_deduped_rows(header or LITE_HEADER, rows, k)


def _topk_summary_from_raw_outputs(
    raw_outputs: list[RawOutput], k: int | None
) -> dict[str, object] | None:
    if k is None:
        return None
    if k < 1:
        raise ValueError("--topk-summary must be >= 1")
    header: str | None = None
    rows: list[str] = []
    for raw_output in raw_outputs:
        if header is None:
            header = raw_output.header
        elif raw_output.header != header:
            raise RuntimeError("output header mismatch in shard output")
        rows.extend(raw_output.rows)
    return _topk_summary_from_deduped_rows(header or LITE_HEADER, rows, k)


def _topk_summary_from_outputs(
    canonicals: list[CanonicalOutput],
    raw_outputs: list[RawOutput],
    k: int | None,
) -> dict[str, object] | None:
    if k is None:
        return None
    if k < 1:
        raise ValueError("--topk-summary must be >= 1")
    header: str | None = None
    rows: list[str] = []
    for canonical in canonicals:
        if header is None:
            header = canonical.header
        elif canonical.header != header:
            raise RuntimeError("output header mismatch in shard output")
        rows.extend(canonical.rows)
    for raw_output in raw_outputs:
        if header is None:
            header = raw_output.header
        elif raw_output.header != header:
            raise RuntimeError("output header mismatch in shard output")
        rows.extend(raw_output.rows)
    return _topk_summary_from_deduped_rows(header or LITE_HEADER, rows, k)


def _topk_summary_payload_content(summary: dict[str, object]) -> str:
    lines = ["mode\trank\t" + "\t".join(TOPK_ROW_KEY_COLUMNS)]
    modes = summary.get("modes")
    if not isinstance(modes, dict):
        raise RuntimeError("topk_summary missing modes")
    for mode in TOPK_MODES:
        payload = modes.get(mode)
        if not isinstance(payload, dict):
            raise RuntimeError(f"topk_summary missing mode: {mode}")
        keys = payload.get("keys")
        if not isinstance(keys, list):
            raise RuntimeError(f"topk_summary mode missing keys: {mode}")
        for rank, key in enumerate(keys, start=1):
            if not isinstance(key, str):
                raise RuntimeError(f"topk_summary key is not text: {mode} rank {rank}")
            lines.append(f"{mode}\t{rank}\t{key}")
    return "\n".join(lines) + "\n"


def _topk_rows_payload_content(summary: dict[str, object]) -> str:
    header = summary.get("header")
    if not isinstance(header, str) or not header:
        raise RuntimeError("topk_summary missing header")
    lines = ["mode\trank\t" + header]
    modes = summary.get("modes")
    if not isinstance(modes, dict):
        raise RuntimeError("topk_summary missing modes")
    for mode in TOPK_MODES:
        payload = modes.get(mode)
        if not isinstance(payload, dict):
            raise RuntimeError(f"topk_summary missing mode: {mode}")
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(f"topk_summary mode missing rows: {mode}")
        for rank, row in enumerate(rows, start=1):
            if not isinstance(row, str):
                raise RuntimeError(f"topk_summary row is not text: {mode} rank {rank}")
            lines.append(f"{mode}\t{rank}\t{row}")
    return "\n".join(lines) + "\n"


def _write_topk_summary_artifact(
    summary: dict[str, object] | None,
    path: Path,
    result_contract: str,
) -> tuple[str, str, str] | tuple[None, None, None]:
    if summary is None:
        return None, None, None
    payload_content = _topk_summary_payload_content(summary)
    content = f"# result_contract={result_contract}\n" + payload_content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path), _sha256_text(content), _sha256_text(payload_content)


def _write_topk_rows_artifact(
    summary: dict[str, object] | None,
    path: Path,
    result_contract: str,
) -> tuple[str, str, str] | tuple[None, None, None]:
    if summary is None:
        return None, None, None
    payload_content = _topk_rows_payload_content(summary)
    content = f"# result_contract={result_contract}\n" + payload_content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path), _sha256_text(content), _sha256_text(payload_content)


def _topk_lite_output(summary: dict[str, object] | None) -> CanonicalOutput | None:
    if summary is None:
        return None
    header = summary.get("header")
    if not isinstance(header, str) or not header:
        raise RuntimeError("topk_summary missing header")
    modes = summary.get("modes")
    if not isinstance(modes, dict):
        raise RuntimeError("topk_summary missing modes")
    rows: list[str] = []
    for mode in TOPK_MODES:
        payload = modes.get(mode)
        if not isinstance(payload, dict):
            raise RuntimeError(f"topk_summary missing mode: {mode}")
        mode_rows = payload.get("rows")
        if not isinstance(mode_rows, list):
            raise RuntimeError(f"topk_summary mode missing rows: {mode}")
        for row in mode_rows:
            if not isinstance(row, str):
                raise RuntimeError(f"topk_summary row is not text: {mode}")
            rows.append(row)
    return _canonical_from_rows(header, rows)


def _write_topk_lite_artifact(
    summary: dict[str, object] | None,
    path: Path,
) -> tuple[str, str, int] | tuple[None, None, None]:
    topk_lite = _topk_lite_output(summary)
    if topk_lite is None:
        return None, None, None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(topk_lite.content, encoding="utf-8")
    return str(path), topk_lite.digest, len(topk_lite.rows)


def _canonical_from_rows(header: str, rows: list[str]) -> CanonicalOutput:
    context = _canonical_sort_context(header)
    unique_rows = sorted(set(rows), key=lambda row: _row_sort_key(context, row))
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


def _read_raw_output(path: Path, output_mode: str) -> RawOutput:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return RawOutput(
            header=_default_header(output_mode),
            rows=[],
            raw_records=0,
            digest=_sha256_file(path),
        )
    header = lines[0].rstrip("\r\n")
    rows = [line.rstrip("\r\n") for line in lines[1:] if line.strip()]
    return RawOutput(
        header=header,
        rows=rows,
        raw_records=len(rows),
        digest=_sha256_file(path),
    )


def _merge_canonical_outputs(
    canonicals: list[CanonicalOutput], output_mode: str, output_path: Path
) -> CanonicalOutput:
    header: str | None = None
    rows: list[str] = []

    for canonical in canonicals:
        if header is None:
            header = canonical.header
        elif canonical.header != header:
            raise RuntimeError("output header mismatch in shard output")
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
        "group_member_count": shard.group_member_count,
        "group_member_headers": list(shard.group_member_headers),
        "group_member_names": list(shard.group_member_names),
        "group_member_ranges": list(shard.group_member_ranges),
        "group_member_input_digests": list(shard.group_member_input_digests),
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


def _parse_fasim_benchmarks(stderr_path: Path | None) -> dict[str, object]:
    if stderr_path is None or not stderr_path.exists():
        return {}
    benchmarks: dict[str, object] = {}
    for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("benchmark."):
            continue
        key_value = line[len("benchmark.") :]
        if "=" not in key_value:
            continue
        key, value = key_value.split("=", 1)
        try:
            number = float(value) if "." in value or "e" in value.lower() else int(value)
        except ValueError:
            benchmarks[key] = value
        else:
            benchmarks[key] = number
    return benchmarks


def _sum_fasim_benchmarks(per_shard: list[dict[str, object]]) -> tuple[dict[str, object], int]:
    sums: dict[str, object] = {}
    shard_count = 0
    for shard in per_shard:
        if shard.get("status") == "failed":
            continue
        run = shard.get("run")
        if not isinstance(run, dict):
            continue
        stderr_path_value = run.get("stderr_path")
        if not isinstance(stderr_path_value, str) or not stderr_path_value:
            continue
        benchmarks = _parse_fasim_benchmarks(Path(stderr_path_value))
        if not benchmarks:
            continue
        shard_count += 1
        for key, value in benchmarks.items():
            if isinstance(value, (int, float)):
                previous = sums.get(key, 0)
                if isinstance(previous, (int, float)):
                    sums[key] = previous + value
                else:
                    sums[key] = value
            elif key not in sums or sums[key] in ("", "none"):
                sums[key] = value
    return sums, shard_count


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
        "--topk-summary",
        type=int,
        default=None,
        metavar="K",
        help=(
            "Add report-only top-K summaries for score, stability, and nt_score "
            "rankings. Does not change merged output or defaults."
        ),
    )
    parser.add_argument(
        "--topk-summary-only",
        action="store_true",
        help=(
            "Skip full merged output materialization and report only top-K "
            "summaries. Requires --topk-summary and is incompatible with "
            "--validate-single."
        ),
    )
    parser.add_argument(
        "--shard-output-topk-lite",
        type=int,
        default=None,
        metavar="K",
        help=(
            "Ask each Fasim shard to write only its in-process top-K lite "
            "artifact via FASIM_OUTPUT_TOPK_LITE. Requires --output-mode lite, "
            "--topk-summary-only, and the same K as --topk-summary."
        ),
    )
    parser.add_argument(
        "--group-target-records",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Default-off complete-record shard grouping. Groups up to N target "
            "FASTA records into one worker shard FASTA without splitting records "
            "or rewriting original FASTA headers."
        ),
    )
    parser.add_argument(
        "--gasal2-top5-column-pruned-scoreinfo",
        action="store_true",
        help=(
            "Default-off top5-only GASAL2 scoreInfo/preAlign preset. Sets the "
            "current column-pruned one-DP scoreInfo artifact path with "
            "--gasal2-top5-scoreinfo-prune-max-per-task 64, "
            "--exact-scoreinfo-gpu-max-per-task 512, "
            "--exact-scoreinfo-gpu-pruned-output, and "
            "--exact-scoreinfo-gpu-column-pruned-output, and "
            "topK-lite scoreInfo rank telemetry plus topK artifact output "
            "with --topk-summary 5, "
            "--topk-summary-only, and --shard-output-topk-lite 5. "
            "Requires --output-mode lite."
        ),
    )
    parser.add_argument(
        "--gasal2-top5-scoreinfo-prune-max-per-task",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Default-off top5 compute-prune preset for GASAL2 scoreInfo/preAlign "
            "runs. Sets FASIM_TOP5_GASAL2_GPU_SCOREINFO=1, phase timing, "
            "staged-first pruning, and FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=N. "
            "Requires --output-mode lite, --topk-summary 5, and --topk-summary-only."
        ),
    )
    parser.add_argument(
        "--exact-scoreinfo-gpu-max-per-task",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Default-off exact scoreInfo GPU compact-buffer capacity for top5 "
            "GASAL2 scoreInfo/preAlign runs. Sets FASIM_EXACT_COLUMN_SCOREINFO_GPU=1 "
            "and FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=N. Requires "
            "--gasal2-top5-scoreinfo-prune-max-per-task."
        ),
    )
    parser.add_argument(
        "--exact-scoreinfo-gpu-pruned-output",
        action="store_true",
        help=(
            "Default-off exact scoreInfo GPU pruned compact output for top5 "
            "GASAL2 scoreInfo/preAlign runs. Sets "
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 and requires "
            "--exact-scoreinfo-gpu-max-per-task plus "
            "--gasal2-top5-scoreinfo-prune-max-per-task."
        ),
    )
    parser.add_argument(
        "--exact-scoreinfo-gpu-column-pruned-output",
        action="store_true",
        help=(
            "Default-off diagnostic one-DP exact-column top5 path. Sets "
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1 and "
            "requires --exact-scoreinfo-gpu-pruned-output."
        ),
    )
    parser.add_argument(
        "--gasal2-single-pass-topn",
        action="store_true",
        help=(
            "Default-off top5 diagnostic path that forces the existing CUDA "
            "topN column-maxima pass to feed GASAL2 directly. Sets "
            "FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1 and requires "
            "--gasal2-top5-scoreinfo-prune-max-per-task."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-trust",
        action="store_true",
        help=(
            "Default-off experimental long-query streaming scoreInfo trust "
            "preset. Sets the MALAT1-validated GPU scoreInfo/minScore trust "
            "stack and feeds GPU scoreInfo into CPU extend/output without GPU "
            "endpoint, CIGAR, or traceback authority. Correctness requires an "
            "external baseline/candidate digest gate; this is not a broad "
            "scoreInfo/preAlign replacement."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-trust-group32",
        action="store_true",
        help=(
            "Default-off MALAT1-like grouped trust preset. Equivalent to "
            "--long-query-streaming-scoreinfo-gpu-trust with "
            "--group-target-records 32, records the "
            "malat1_like_group32_experimental_v1 profile, and still requires "
            "an external digest gate."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
        action="store_true",
        help=(
            "Default-off experimental two-contract long-query scoreInfo trust "
            "preset. Sets FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1 "
            "and FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1, "
            "uses hot GPU minScore for the legacy calc-score contract, feeds "
            "GPU scoreInfo into CPU extend/output, and still requires an "
            "external baseline/candidate digest gate."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
        action="store_true",
        help=(
            "Default-off MALAT1-like grouped two-contract trust preset. "
            "Equivalent to --long-query-streaming-scoreinfo-gpu-two-contract-trust "
            "with --group-target-records 32, records the "
            "malat1_like_two_contract_group32_experimental_v1 profile, and still "
            "requires an external digest gate."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-two-contract-runtime",
        action="store_true",
        help=(
            "Default-off experimental no-probe two-contract long-query "
            "scoreInfo runtime preset. It sets the two-contract bridge trust "
            "stack and hot GPU minScore without enabling replay/attempt "
            "diagnostic probes. Correctness still requires an external "
            "baseline/candidate digest gate."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
        action="store_true",
        help=(
            "Default-off MALAT1-like grouped no-probe two-contract runtime "
            "preset. Equivalent to --long-query-streaming-scoreinfo-gpu-two-contract-runtime "
            "with --group-target-records 32, records the "
            "malat1_like_two_contract_runtime_group32_experimental_v1 profile, "
            "and still requires an external digest gate."
        ),
    )
    parser.add_argument(
        "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Task cap per flush for the long-query streaming scoreInfo "
            "flush-level replay diagnostics. The trust preset default is 1; "
            "0 means all tasks in each flush. Larger values only expand "
            "diagnostic replay coverage and do not give GPU endpoint/CIGAR/"
            "output authority."
        ),
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
    if args.long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32:
        args.long_query_streaming_scoreinfo_gpu_two_contract_runtime = True
        if args.group_target_records is None:
            args.group_target_records = 32
        elif args.group_target_records != 32:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32 uses --group-target-records 32"
            )

    if args.long_query_streaming_scoreinfo_gpu_two_contract_trust_group32:
        args.long_query_streaming_scoreinfo_gpu_two_contract_trust = True
        if args.group_target_records is None:
            args.group_target_records = 32
        elif args.group_target_records != 32:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32 uses --group-target-records 32"
            )

    if args.long_query_streaming_scoreinfo_gpu_trust_group32:
        args.long_query_streaming_scoreinfo_gpu_trust = True
        if args.group_target_records is None:
            args.group_target_records = 32
        elif args.group_target_records != 32:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-trust-group32 uses --group-target-records 32"
            )

    if args.long_query_streaming_scoreinfo_gpu_trust:
        if args.gasal2_top5_column_pruned_scoreinfo:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --gasal2-top5-column-pruned-scoreinfo"
            )
        if args.validate_single:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --validate-single"
            )
        if args.keep_going:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --keep-going"
            )
        if args.fasim_arg:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --fasim-arg"
            )
    if args.long_query_streaming_scoreinfo_gpu_two_contract_trust:
        if args.long_query_streaming_scoreinfo_gpu_trust:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --long-query-streaming-scoreinfo-gpu-trust"
            )
        if args.long_query_streaming_scoreinfo_gpu_two_contract_runtime:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --long-query-streaming-scoreinfo-gpu-two-contract-runtime"
            )
        if args.gasal2_top5_column_pruned_scoreinfo:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --gasal2-top5-column-pruned-scoreinfo"
            )
        if args.validate_single:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --validate-single"
            )
        if args.keep_going:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --keep-going"
            )
        if args.fasim_arg:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --fasim-arg"
            )
    if args.long_query_streaming_scoreinfo_gpu_two_contract_runtime:
        if args.long_query_streaming_scoreinfo_gpu_trust:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --long-query-streaming-scoreinfo-gpu-trust"
            )
        if args.long_query_streaming_scoreinfo_gpu_two_contract_trust:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --long-query-streaming-scoreinfo-gpu-two-contract-trust"
            )
        if args.gasal2_top5_column_pruned_scoreinfo:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --gasal2-top5-column-pruned-scoreinfo"
            )
        if args.validate_single:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --validate-single"
            )
        if args.keep_going:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --keep-going"
            )
        if args.fasim_arg:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --fasim-arg"
            )

    if args.gasal2_top5_column_pruned_scoreinfo:
        if args.output_mode != "lite":
            raise RuntimeError("--gasal2-top5-column-pruned-scoreinfo requires --output-mode lite")
        if args.validate_single:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo cannot be combined with --validate-single"
            )
        if args.keep_going:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo cannot be combined with --keep-going"
            )
        if args.fasim_arg:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo cannot be combined with --fasim-arg"
            )
        if args.gasal2_single_pass_topn:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo cannot be combined "
                "with --gasal2-single-pass-topn"
            )
        if args.topk_summary is None:
            args.topk_summary = 5
        elif args.topk_summary != 5:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo uses --topk-summary 5"
            )
        args.topk_summary_only = True
        if args.gasal2_top5_scoreinfo_prune_max_per_task is None:
            args.gasal2_top5_scoreinfo_prune_max_per_task = (
                GASAL2_COLUMN_PRUNED_PRESET_PRUNE_MAX_PER_TASK
            )
        elif (
            args.gasal2_top5_scoreinfo_prune_max_per_task
            != GASAL2_COLUMN_PRUNED_PRESET_PRUNE_MAX_PER_TASK
        ):
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo uses "
                "--gasal2-top5-scoreinfo-prune-max-per-task "
                f"{GASAL2_COLUMN_PRUNED_PRESET_PRUNE_MAX_PER_TASK}"
            )
        if args.exact_scoreinfo_gpu_max_per_task is None:
            args.exact_scoreinfo_gpu_max_per_task = 512
        elif args.exact_scoreinfo_gpu_max_per_task != 512:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo uses "
                "--exact-scoreinfo-gpu-max-per-task 512"
            )
        if not args.exact_scoreinfo_gpu_pruned_output:
            args.exact_scoreinfo_gpu_pruned_output = True
        if not args.exact_scoreinfo_gpu_column_pruned_output:
            args.exact_scoreinfo_gpu_column_pruned_output = True
        if args.shard_output_topk_lite is None:
            args.shard_output_topk_lite = 5
        elif args.shard_output_topk_lite != 5:
            raise RuntimeError(
                "--gasal2-top5-column-pruned-scoreinfo requires "
                "--shard-output-topk-lite 5"
            )

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
    if args.topk_summary is not None and args.topk_summary < 1:
        raise RuntimeError("--topk-summary must be >= 1")
    if args.topk_summary_only and args.topk_summary is None:
        raise RuntimeError("--topk-summary-only requires --topk-summary")
    if args.topk_summary_only and args.validate_single:
        raise RuntimeError("--topk-summary-only cannot be combined with --validate-single")
    if args.group_target_records is not None and args.group_target_records < 1:
        raise RuntimeError("--group-target-records must be >= 1")
    if args.shard_output_topk_lite is not None:
        if args.shard_output_topk_lite < 1:
            raise RuntimeError("--shard-output-topk-lite must be >= 1")
        if args.output_mode != "lite":
            raise RuntimeError("--shard-output-topk-lite requires --output-mode lite")
        if not args.topk_summary_only:
            raise RuntimeError("--shard-output-topk-lite requires --topk-summary-only")
        if args.topk_summary != args.shard_output_topk_lite:
            raise RuntimeError("--shard-output-topk-lite must match --topk-summary")
    if args.gasal2_top5_scoreinfo_prune_max_per_task is not None:
        if args.gasal2_top5_scoreinfo_prune_max_per_task < 1:
            raise RuntimeError("--gasal2-top5-scoreinfo-prune-max-per-task must be >= 1")
        if args.output_mode != "lite":
            raise RuntimeError("--gasal2-top5-scoreinfo-prune-max-per-task requires --output-mode lite")
        if not args.topk_summary_only:
            raise RuntimeError("--gasal2-top5-scoreinfo-prune-max-per-task requires --topk-summary-only")
        if args.topk_summary != 5:
            raise RuntimeError("--gasal2-top5-scoreinfo-prune-max-per-task requires --topk-summary 5")
    if args.gasal2_top5_column_pruned_scoreinfo:
        if args.output_mode != "lite":
            raise RuntimeError("--gasal2-top5-column-pruned-scoreinfo requires --output-mode lite")
        if not args.topk_summary_only:
            raise RuntimeError("--gasal2-top5-column-pruned-scoreinfo requires --topk-summary-only")
        if args.topk_summary != 5:
            raise RuntimeError("--gasal2-top5-column-pruned-scoreinfo requires --topk-summary 5")
        if args.shard_output_topk_lite != 5:
            raise RuntimeError("--gasal2-top5-column-pruned-scoreinfo requires --shard-output-topk-lite 5")
    if args.exact_scoreinfo_gpu_max_per_task is not None:
        if args.exact_scoreinfo_gpu_max_per_task < 1:
            raise RuntimeError("--exact-scoreinfo-gpu-max-per-task must be >= 1")
        if args.gasal2_top5_scoreinfo_prune_max_per_task is None:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-max-per-task requires "
                "--gasal2-top5-scoreinfo-prune-max-per-task"
            )
    if args.exact_scoreinfo_gpu_pruned_output:
        if args.exact_scoreinfo_gpu_max_per_task is None:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-pruned-output requires "
                "--exact-scoreinfo-gpu-max-per-task"
            )
        if args.gasal2_top5_scoreinfo_prune_max_per_task is None:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-pruned-output requires "
                "--gasal2-top5-scoreinfo-prune-max-per-task"
            )
    if args.exact_scoreinfo_gpu_column_pruned_output:
        if not args.exact_scoreinfo_gpu_pruned_output:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-column-pruned-output requires "
                "--exact-scoreinfo-gpu-pruned-output"
            )
    if args.gasal2_single_pass_topn:
        if args.gasal2_top5_scoreinfo_prune_max_per_task is None:
            raise RuntimeError(
                "--gasal2-single-pass-topn requires "
                "--gasal2-top5-scoreinfo-prune-max-per-task"
            )

    env_overrides = _parse_env_overrides(args.env)
    _reject_unknown_gasal2_column_pruned_preset_env(args, env_overrides)
    if args.long_query_streaming_scoreinfo_gpu_two_contract_runtime:
        long_query_two_contract_runtime_env = {
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
            "FASIM_ALIGN_GASAL2": "1",
        }
        conflicts = sorted(set(long_query_two_contract_runtime_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-runtime cannot be combined with --env for: "
                + ", ".join(conflicts)
            )
        env_overrides.update(long_query_two_contract_runtime_env)
    if args.long_query_streaming_scoreinfo_gpu_two_contract_trust:
        if args.long_query_streaming_scoreinfo_gpu_flush_replay_probe_max_tasks < 0:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks must be >= 0"
            )
        long_query_two_contract_trust_env = {
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_SELECTED_ONLY_REPLAY_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_GROUPED_SELECTED_REPLAY_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS": str(
                args.long_query_streaming_scoreinfo_gpu_flush_replay_probe_max_tasks
            ),
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_LEN": "2812",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_OVERLAP": "512",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_MAX_SEGMENTS": "0",
            "FASIM_ALIGN_GASAL2": "1",
        }
        conflicts = sorted(set(long_query_two_contract_trust_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --env for: "
                + ", ".join(conflicts)
            )
        env_overrides.update(long_query_two_contract_trust_env)
    if args.long_query_streaming_scoreinfo_gpu_trust:
        if args.long_query_streaming_scoreinfo_gpu_flush_replay_probe_max_tasks < 0:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks must be >= 0"
            )
        long_query_trust_env = {
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_EXTEND_ATTEMPT_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_GROUPED_SELECTED_REPLAY_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_FULL_REPLAY_PROBE": "1",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS": str(
                args.long_query_streaming_scoreinfo_gpu_flush_replay_probe_max_tasks
            ),
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_LEN": "2812",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_OVERLAP": "512",
            "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_MAX_SEGMENTS": "0",
            "FASIM_ALIGN_GASAL2": "1",
        }
        conflicts = sorted(set(long_query_trust_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --env for: "
                + ", ".join(conflicts)
            )
        env_overrides.update(long_query_trust_env)
    if args.gasal2_top5_scoreinfo_prune_max_per_task is not None:
        gasal2_top5_env = {
            "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
            "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
            "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
            "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": str(
                args.gasal2_top5_scoreinfo_prune_max_per_task
            ),
        }
        if args.gasal2_top5_column_pruned_scoreinfo:
            gasal2_top5_env[
                "FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE"
            ] = "1"
            gasal2_top5_env["FASIM_PREALIGN_CUDA_MAX_TASKS"] = "16384"
        conflicts = sorted(set(gasal2_top5_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--gasal2-top5-scoreinfo-prune-max-per-task cannot be combined "
                "with --env for: " + ", ".join(conflicts)
            )
        env_overrides.update(gasal2_top5_env)
    if args.exact_scoreinfo_gpu_max_per_task is not None:
        exact_scoreinfo_env = {
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU": "1",
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK": str(
                args.exact_scoreinfo_gpu_max_per_task
            ),
        }
        conflicts = sorted(set(exact_scoreinfo_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-max-per-task cannot be combined "
                "with --env for: " + ", ".join(conflicts)
            )
        env_overrides.update(exact_scoreinfo_env)
    if args.exact_scoreinfo_gpu_pruned_output:
        pruned_output_env = {
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT": "1",
        }
        conflicts = sorted(set(pruned_output_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-pruned-output cannot be combined "
                "with --env for: " + ", ".join(conflicts)
            )
        env_overrides.update(pruned_output_env)
    if args.exact_scoreinfo_gpu_column_pruned_output:
        column_pruned_output_env = {
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT": "1",
        }
        conflicts = sorted(set(column_pruned_output_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--exact-scoreinfo-gpu-column-pruned-output cannot be combined "
                "with --env for: " + ", ".join(conflicts)
            )
        env_overrides.update(column_pruned_output_env)
    if args.gasal2_single_pass_topn:
        single_pass_topn_env = {
            "FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN": "1",
        }
        conflicts = sorted(set(single_pass_topn_env) & set(env_overrides))
        if conflicts:
            raise RuntimeError(
                "--gasal2-single-pass-topn cannot be combined "
                "with --env for: " + ", ".join(conflicts)
            )
        env_overrides.update(single_pass_topn_env)
    if args.shard_output_topk_lite is not None:
        if "FASIM_OUTPUT_TOPK_LITE" in env_overrides:
            raise RuntimeError(
                "--shard-output-topk-lite cannot be combined with "
                "--env FASIM_OUTPUT_TOPK_LITE=..."
            )
        env_overrides["FASIM_OUTPUT_TOPK_LITE"] = str(args.shard_output_topk_lite)

    gasal2_supported = _fasim_binary_has_gasal2_support(fasim_bin) if _requires_gasal2_enabled_binary(args) else True
    if args.gasal2_top5_column_pruned_scoreinfo and not gasal2_supported:
        raise RuntimeError(
            "--gasal2-top5-column-pruned-scoreinfo requires a GASAL2-enabled "
            "Fasim binary; run make build-fasim-gasal2 and pass --fasim-bin "
            "./fasim_longtarget_gasal2"
        )
    if args.long_query_streaming_scoreinfo_gpu_trust and not gasal2_supported:
        raise RuntimeError(
            "--long-query-streaming-scoreinfo-gpu-trust requires a GASAL2-enabled Fasim binary; "
            "run make build-fasim-gasal2 and pass --fasim-bin ./fasim_longtarget_gasal2"
        )
    if args.long_query_streaming_scoreinfo_gpu_two_contract_trust and not gasal2_supported:
        raise RuntimeError(
            "--long-query-streaming-scoreinfo-gpu-two-contract-trust requires a GASAL2-enabled Fasim binary; "
            "run make build-fasim-gasal2 and pass --fasim-bin ./fasim_longtarget_gasal2"
        )
    if args.long_query_streaming_scoreinfo_gpu_two_contract_runtime and not gasal2_supported:
        raise RuntimeError(
            "--long-query-streaming-scoreinfo-gpu-two-contract-runtime requires a GASAL2-enabled Fasim binary; "
            "run make build-fasim-gasal2 and pass --fasim-bin ./fasim_longtarget_gasal2"
        )
    if _requires_gasal2_enabled_binary(args) and not gasal2_supported:
        raise RuntimeError(
            "GASAL2 scoreInfo/preAlign runner options require a GASAL2-enabled "
            "Fasim binary; run make build-fasim-gasal2 and pass --fasim-bin "
            "./fasim_longtarget_gasal2"
        )

    rna_records = _read_fasta(rna)
    if not rna_records:
        raise RuntimeError(f"no RNA FASTA records found in {rna}")
    gasal2_query_preflight_fields = _gasal2_top5_query_preflight_report_fields(
        args,
        env_overrides,
        rna_records,
    )
    gasal2_query_preflight_error = gasal2_query_preflight_fields[
        "gasal2_top5_query_preflight_error"
    ]
    if gasal2_query_preflight_error is not None:
        raise RuntimeError(gasal2_query_preflight_error)

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
    shards = _write_shard_fastas(
        records,
        work_dir / "shards",
        group_target_records=args.group_target_records,
    )
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
            if (
                args.gasal2_top5_column_pruned_scoreinfo
                and not _manifest_has_verified_gasal2_top5_activation(old_manifest)
            ):
                _eprint(
                    "resume manifest lacks verified GASAL2 top5 activation; "
                    "formal preset shards will rerun"
                )
            old_by_shard = _resume_entries_for_manifest(
                old_manifest,
                args,
                run_config_digest,
            )
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
    shard_outputs: list[CanonicalOutput] = []
    raw_shard_outputs: list[RawOutput] = []
    sharded_raw_records = 0
    sharded_unique_records = 0
    raw_topk_only = bool(args.topk_summary_only)
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
        raw_topk_only=raw_topk_only,
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
        if shard_result.canonical is not None:
            shard_outputs.append(shard_result.canonical)
        if shard_result.raw_output is not None:
            raw_shard_outputs.append(shard_result.raw_output)
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
            "canonicalize_seconds": result.canonicalize_seconds,
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
    topk_summary = None
    topk_summary_seconds = 0.0
    topk_summary_raw_path = bool(raw_shard_outputs)
    if args.topk_summary_only:
        merged = None
        partial_merged = None
        merge_seconds = 0.0
        if complete_run:
            topk_start = time.perf_counter()
            if topk_summary_raw_path:
                topk_summary = _topk_summary_from_outputs(
                    shard_outputs,
                    raw_shard_outputs,
                    args.topk_summary,
                )
            else:
                topk_summary = _topk_summary_from_canonicals(shard_outputs, args.topk_summary)
            topk_summary_seconds = time.perf_counter() - topk_start
    else:
        merge_start = time.perf_counter()
        if complete_run:
            merged = _merge_canonical_outputs(shard_outputs, args.output_mode, merged_output_path)
            partial_merged = None
        else:
            merged = None
            partial_merged = _merge_canonical_outputs(
                shard_outputs,
                args.output_mode,
                partial_merged_output_path,
            )
        merge_seconds = time.perf_counter() - merge_start

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
    if topk_summary is None and not args.topk_summary_only:
        topk_start = time.perf_counter()
        topk_summary = _topk_summary(merged, args.topk_summary)
        topk_summary_seconds = time.perf_counter() - topk_start
    result_contract = _result_contract(args)
    topk_summary_output, topk_summary_digest, topk_summary_payload_digest = _write_topk_summary_artifact(
        topk_summary,
        work_dir / "topk_summary.tsv",
        result_contract,
    )
    topk_rows_output, topk_rows_digest, topk_rows_payload_digest = _write_topk_rows_artifact(
        topk_summary,
        work_dir / "topk_rows.tsv",
        result_contract,
    )
    topk_lite_output, topk_lite_digest, topk_lite_records = _write_topk_lite_artifact(
        topk_summary,
        work_dir / "topk-TFOsorted.lite",
    )
    partial_merged_digest = partial_merged.digest if partial_merged is not None else None
    duplicate_records_removed = (
        sharded_raw_records - len(merged.rows)
        if merged is not None
        else None
    )
    fasim_benchmark_sums, fasim_benchmark_shards = _sum_fasim_benchmarks(per_shard)
    gasal2_top5_activation_fields = _gasal2_top5_activation_report_fields(
        args,
        fasim_benchmark_sums,
        fasim_benchmark_shards,
        len(shards),
    )
    gasal2_top5_activation_error = gasal2_top5_activation_fields[
        "gasal2_top5_activation_error"
    ]
    run_status = "completed" if complete_run else "incomplete"
    if gasal2_top5_activation_error is not None:
        run_status = "failed_activation"
    if manifest is not None:
        manifest.finalize(
            run_status=run_status,
            merged_records=merged_records,
            duplicate_removed=duplicate_records_removed,
            merged_digest=merged_digest,
            partial_merged_digest=partial_merged_digest,
            topk_summary_output=topk_summary_output,
            topk_summary_digest=topk_summary_digest,
            topk_summary_payload_digest=topk_summary_payload_digest,
            topk_rows_output=topk_rows_output,
            topk_rows_digest=topk_rows_digest,
            topk_rows_payload_digest=topk_rows_payload_digest,
            topk_lite_output=topk_lite_output,
            topk_lite_digest=topk_lite_digest,
            topk_lite_records=topk_lite_records,
            gasal2_top5_activation_verified=gasal2_top5_activation_fields[
                "gasal2_top5_activation_verified"
            ],
            gasal2_top5_activation_error=gasal2_top5_activation_error,
            gasal2_top5_query_preflight_supported=gasal2_query_preflight_fields[
                "gasal2_top5_query_preflight_supported"
            ],
            gasal2_top5_query_preflight_error=gasal2_query_preflight_fields[
                "gasal2_top5_query_preflight_error"
            ],
            gasal2_top5_query_preflight_query_len=gasal2_query_preflight_fields[
                "gasal2_top5_query_preflight_query_len"
            ],
            gasal2_top5_query_preflight_max_query_len=gasal2_query_preflight_fields[
                "gasal2_top5_query_preflight_max_query_len"
            ],
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
        "result_contract": result_contract,
        "git_commit": git_commit,
        "runner_version": RUNNER_VERSION,
        "target": str(target),
        "target_fasta_digest": target_digest,
        "target_record_count": len(records),
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
        "group_target_records": args.group_target_records,
        "grouped_shard_count": len(shards),
        "shard_ids": [shard.shard_id for shard in shards],
        "per_worker": per_worker,
        "per_shard": per_shard,
        "fasim_benchmark_sums": fasim_benchmark_sums,
        "fasim_benchmark_shards": fasim_benchmark_shards,
        **gasal2_query_preflight_fields,
        **gasal2_top5_activation_fields,
        "sharded_records": sharded_raw_records,
        "sharded_unique_records": sharded_unique_records,
        "shard_canonicalize_seconds": sum(
            shard_result.canonicalize_seconds
            for shard_result in scheduled_results
            if shard_result.status != "failed"
        ),
        "merge_seconds": merge_seconds,
        "topk_summary_only": bool(args.topk_summary_only),
        "shard_output_topk_lite": args.shard_output_topk_lite,
        "long_query_streaming_scoreinfo_gpu_trust": bool(
            args.long_query_streaming_scoreinfo_gpu_trust
        ),
        "long_query_streaming_scoreinfo_gpu_trust_group32": bool(
            args.long_query_streaming_scoreinfo_gpu_trust_group32
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_trust": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_trust
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_trust_group32
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_runtime": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_runtime
        ),
        "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32": bool(
            args.long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32
        ),
        "long_query_streaming_scoreinfo_gpu_trust_profile": (
            _long_query_streaming_scoreinfo_gpu_profile(args)
        ),
        "long_query_streaming_scoreinfo_gpu_trust_decision": (
            LONG_QUERY_STREAMING_SCOREINFO_GPU_TRUST_DECISION
            if _long_query_streaming_scoreinfo_gpu_uses_external_digest_gate(args)
            else None
        ),
        "gasal2_top5_column_pruned_scoreinfo": bool(
            args.gasal2_top5_column_pruned_scoreinfo
        ),
        "gasal2_top5_scoreinfo_prune_max_per_task": (
            args.gasal2_top5_scoreinfo_prune_max_per_task
        ),
        "exact_scoreinfo_gpu_max_per_task": args.exact_scoreinfo_gpu_max_per_task,
        "exact_scoreinfo_gpu_pruned_output": bool(args.exact_scoreinfo_gpu_pruned_output),
        "exact_scoreinfo_gpu_column_pruned_output": bool(
            args.exact_scoreinfo_gpu_column_pruned_output
        ),
        "gasal2_single_pass_topn": bool(args.gasal2_single_pass_topn),
        "topk_summary_raw_path": topk_summary_raw_path,
        "topk_summary_seconds": topk_summary_seconds,
        "topk_summary": topk_summary,
        "topk_summary_output": topk_summary_output,
        "topk_summary_digest": topk_summary_digest,
        "topk_summary_payload_digest": topk_summary_payload_digest,
        "topk_rows_output": topk_rows_output,
        "topk_rows_digest": topk_rows_digest,
        "topk_rows_payload_digest": topk_rows_payload_digest,
        "topk_lite_output": topk_lite_output,
        "topk_lite_digest": topk_lite_digest,
        "topk_lite_records": topk_lite_records,
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
    if gasal2_top5_activation_error is not None:
        raise RuntimeError(gasal2_top5_activation_error)
    if failed_shards:
        raise RuntimeError(f"sharded run incomplete; failed shards: {','.join(failed_shards)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _eprint(f"error: {exc}")
        raise SystemExit(1)
