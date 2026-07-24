#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fasim_tfo_archive import TFOSORTED_COLUMNS


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.0.0+submission.1.dev"
SCHEMA_VERSION = "1.0.0"
PAPER_RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
MAX_GPU_QUERY_LENGTH = 2812
MIN_GPU_MEMORY_MIB = 24000
SUPPORTED_GPU_COMPUTE_CAPABILITY = "8.9"
SCHEMA_PATH = ROOT / "schemas/gasal2_longtarget_run_report.schema.json"

EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
EXIT_ENVIRONMENT = 3
EXIT_AUTHORITY_FAILURE = 4
EXIT_CANDIDATE_FAILURE = 5
EXIT_COMPARATOR_FAILURE = 6
EXIT_INTERNAL = 7
EXIT_INTERRUPTED = 130

ACTIVE_CHILD: subprocess.Popen[str] | None = None


class WorkflowError(RuntimeError):
    def __init__(self, message: str, exit_code: int, result_status: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.result_status = result_status


class WorkflowInterrupted(RuntimeError):
    pass


@dataclass
class BackendResult:
    command: list[str]
    returncode: int
    wall_seconds: float
    timed_out: bool
    stdout: str
    stderr: str
    start_utc: str
    end_utc: str

    def report(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "wall_seconds": self.wall_seconds,
            "timed_out": self.timed_out,
            "peak_rss_kib": None,
            "peak_gpu_memory_mib": None,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "stdout_tail": self.stdout[-8192:],
            "stderr_tail": self.stderr[-8192:],
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.partial.{os.getpid()}"
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for raw in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.lower().startswith("model name") and ":" in raw:
                return raw.split(":", 1)[1].strip()
    return platform.processor() or "unavailable"


def parse_fasta(path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise WorkflowError(f"{role} FASTA does not exist: {path}", EXIT_INVALID_INPUT, "invalid_input")
    if not os.access(path, os.R_OK):
        raise WorkflowError(f"{role} FASTA is not readable: {path}", EXIT_INVALID_INPUT, "invalid_input")
    records: list[tuple[str, str]] = []
    header: str | None = None
    sequence: list[str] = []
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, 1):
            try:
                line = raw.decode("utf-8", errors="strict").strip()
            except UnicodeDecodeError as exc:
                raise WorkflowError(
                    f"{role} FASTA is not valid UTF-8 at line {line_number}",
                    EXIT_INVALID_INPUT,
                    "invalid_input",
                ) from exc
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    if not sequence:
                        raise WorkflowError(
                            f"{role} FASTA record {header!r} has no sequence",
                            EXIT_INVALID_INPUT,
                            "invalid_input",
                        )
                    records.append((header, "".join(sequence)))
                header = line[1:].strip()
                sequence = []
                if not header:
                    raise WorkflowError(
                        f"{role} FASTA has an empty header at line {line_number}",
                        EXIT_INVALID_INPUT,
                        "invalid_input",
                    )
                continue
            if header is None:
                raise WorkflowError(
                    f"{role} FASTA has sequence before its first header at line {line_number}",
                    EXIT_INVALID_INPUT,
                    "invalid_input",
                )
            normalized = line.upper()
            invalid = sorted(set(normalized) - set("ACGT"))
            if invalid:
                raise WorkflowError(
                    f"{role} FASTA contains unsupported characters at line {line_number}: {''.join(invalid)}",
                    EXIT_INVALID_INPUT,
                    "invalid_input",
                )
            sequence.append(normalized)
    if header is not None:
        if not sequence:
            raise WorkflowError(
                f"{role} FASTA record {header!r} has no sequence",
                EXIT_INVALID_INPUT,
                "invalid_input",
            )
        records.append((header, "".join(sequence)))
    if not records:
        raise WorkflowError(f"{role} FASTA contains no records", EXIT_INVALID_INPUT, "invalid_input")
    lengths = [len(value) for _, value in records]
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "record_count": len(records),
        "length_min": min(lengths),
        "length_max": max(lengths),
        "lengths": lengths,
        "total_bp": sum(lengths),
    }


def detect_gpus() -> list[dict[str, Any]]:
    if os.environ.get("GASAL2_LONGTARGET_TEST_MODE") == "1":
        try:
            payload = json.loads(os.environ.get("GASAL2_LONGTARGET_TEST_GPU_JSON", "[]"))
        except json.JSONDecodeError as exc:
            raise WorkflowError(
                f"invalid GASAL2_LONGTARGET_TEST_GPU_JSON: {exc}",
                EXIT_INTERNAL,
                "internal_error",
            ) from exc
        if not isinstance(payload, list):
            raise WorkflowError(
                "GASAL2_LONGTARGET_TEST_GPU_JSON must be a list",
                EXIT_INTERNAL,
                "internal_error",
            )
        return payload

    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is not None and visible.strip() in {"", "-1"}:
        return []
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    allowed_indices: set[str] | None = None
    if visible is not None:
        allowed_indices = {item.strip() for item in visible.split(",") if item.strip()}
    gpus: list[dict[str, Any]] = []
    for raw in result.stdout.splitlines():
        parts = [value.strip() for value in raw.split(",")]
        if len(parts) != 5 or (allowed_indices is not None and parts[0] not in allowed_indices):
            continue
        try:
            memory = int(parts[2])
        except ValueError:
            memory = 0
        gpus.append(
            {
                "index": int(parts[0]) if parts[0].isdigit() else parts[0],
                "name": parts[1],
                "memory_total_mib": memory,
                "driver_version": parts[3],
                "compute_capability": parts[4],
            }
        )
    return gpus


def executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def sanitized_environment(candidate: bool) -> tuple[dict[str, str], dict[str, str]]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FASIM_")}
    contract_environment = {
        "FASIM_OUTPUT_MODE": "tfosorted",
        "FASIM_VERBOSE": "0",
    }
    if candidate:
        contract_environment.update(
            {
                "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
                "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
                "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
                "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "256",
                "FASIM_ALIGN_GASAL2_STREAMS": "3",
                "FASIM_ALIGN_GASAL2_BATCH": "20000",
            }
        )
    environment.update(contract_environment)
    return environment, contract_environment


def backend_command(binary: Path, target: Path, query: Path, rule: int, output: Path) -> list[str]:
    return [
        str(binary),
        "-f1",
        str(target),
        "-f2",
        str(query),
        "-r",
        str(rule),
        "-O",
        str(output),
    ]


def _kill_active_child() -> None:
    global ACTIVE_CHILD
    if ACTIVE_CHILD is not None and ACTIVE_CHILD.poll() is None:
        try:
            os.killpg(ACTIVE_CHILD.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def _signal_handler(signum: int, _frame: Any) -> None:
    _kill_active_child()
    raise WorkflowInterrupted(f"interrupted by signal {signum}")


def run_command(command: list[str], environment: dict[str, str], timeout: int) -> BackendResult:
    global ACTIVE_CHILD
    start_utc = utc_now()
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    ACTIVE_CHILD = process
    timed_out = False
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()
    finally:
        ACTIVE_CHILD = None
    return BackendResult(
        command=command,
        returncode=124 if timed_out else process.returncode,
        wall_seconds=time.perf_counter() - started,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        start_utc=start_utc,
        end_utc=utc_now(),
    )


def write_backend_logs(output: Path, result: BackendResult) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "wrapper-stdout.log").write_text(result.stdout, encoding="utf-8")
    (output / "wrapper-stderr.log").write_text(result.stderr, encoding="utf-8")


def validate_tfosorted(output: Path, backend: str) -> Path:
    matches = sorted(path for path in output.rglob("*-TFOsorted") if path.is_file())
    if len(matches) != 1:
        raise WorkflowError(
            f"{backend} produced {len(matches)} TFOsorted files; exactly one is required for verification",
            EXIT_CANDIDATE_FAILURE if backend == "candidate" else EXIT_AUTHORITY_FAILURE,
            "candidate_failure" if backend == "candidate" else "authority_failure",
        )
    path = matches[0]
    try:
        with path.open(newline="", encoding="utf-8", errors="strict") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != list(TFOSORTED_COLUMNS):
                raise ValueError(f"unsupported columns: {reader.fieldnames or []}")
            for row_number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"malformed row {row_number}")
                integer_columns = (
                    "QueryStart",
                    "QueryEnd",
                    "StartInSeq",
                    "EndInSeq",
                    "StartInGenome",
                    "EndInGenome",
                    "Rule",
                    "Nt(bp)",
                    "Class",
                    "MidPoint",
                    "Center",
                )
                try:
                    integers = {column: int(row[column]) for column in integer_columns}
                    numbers = {
                        column: float(row[column])
                        for column in ("MeanStability", "MeanIdentity(%)", "Score")
                    }
                except ValueError as exc:
                    raise ValueError(f"non-numeric value at row {row_number}") from exc
                if not all(math.isfinite(value) for value in numbers.values()):
                    raise ValueError(f"non-finite numeric value at row {row_number}")
                if row["Direction"] not in {"R", "L"}:
                    raise ValueError(f"invalid Direction at row {row_number}")
                if row["Strand"] not in {"ParaPlus", "ParaMinus", "AntiPlus", "AntiMinus"}:
                    raise ValueError(f"invalid Strand at row {row_number}")
                rule_limit = 6 if row["Strand"].startswith("Para") else 18
                if not 1 <= integers["Rule"] <= rule_limit:
                    raise ValueError(f"invalid Rule for Strand at row {row_number}")
                if integers["Nt(bp)"] < 0:
                    raise ValueError(f"negative Nt(bp) at row {row_number}")
                if not 0.0 <= numbers["MeanIdentity(%)"] <= 100.0:
                    raise ValueError(f"MeanIdentity(%) outside 0..100 at row {row_number}")
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkflowError(
            f"{backend} produced an invalid TFOsorted artifact: {exc}",
            EXIT_CANDIDATE_FAILURE if backend == "candidate" else EXIT_AUTHORITY_FAILURE,
            "candidate_failure" if backend == "candidate" else "authority_failure",
        ) from exc
    return path


def tfosorted_row_keys(path: Path) -> set[tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {tuple(row[column] for column in TFOSORTED_COLUMNS) for row in reader}


def failed_comparator_report(result: BackendResult, reason: str) -> dict[str, Any]:
    report = no_comparator_report()
    report.update(
        {
            "status": "failed",
            "returncode": result.returncode,
            "wall_seconds": result.wall_seconds,
            "timed_out": result.timed_out,
            "failure_reason": reason,
            "stdout_tail": result.stdout[-8192:],
            "stderr_tail": result.stderr[-8192:],
        }
    )
    return report


def write_contract_output(
    details: Path,
    contract: str,
    output: Path,
    top_k: int,
    authority_tfosorted: Path,
    candidate_tfosorted: Path,
) -> None:
    modes = ["score"] if contract == "score-top5" else ["score", "stability", "nt"]
    try:
        source_rows = {
            "baseline": tfosorted_row_keys(authority_tfosorted),
            "candidate": tfosorted_row_keys(candidate_tfosorted),
        }
        input_rows_present = bool(source_rows["baseline"] or source_rows["candidate"])
        with details.open(newline="", encoding="utf-8", errors="strict") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            expected_fields = ["side", "kind", "mode", "rank", "cluster_id", *TFOSORTED_COLUMNS]
            if reader.fieldnames != expected_fields:
                raise ValueError(f"unsupported columns: {reader.fieldnames or []}")
            groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
            for row_number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"malformed row {row_number}")
                if row["side"] not in {"baseline", "candidate"}:
                    raise ValueError(f"invalid side at row {row_number}")
                if row["kind"] not in {"raw", "clustered"}:
                    raise ValueError(f"invalid kind at row {row_number}")
                if row["mode"] not in {"score", "stability", "nt"}:
                    raise ValueError(f"invalid mode at row {row_number}")
                try:
                    rank = int(row["rank"])
                except ValueError as exc:
                    raise ValueError(f"invalid rank at row {row_number}") from exc
                if rank < 1 or rank > top_k:
                    raise ValueError(f"rank outside 1..{top_k} at row {row_number}")
                source_key = tuple(row[column] for column in TFOSORTED_COLUMNS)
                if source_key not in source_rows[row["side"]]:
                    raise ValueError(
                        f"{row['side']} row {row_number} is not present in its backend artifact"
                    )
                group_key = (row["side"], row["kind"], row["mode"])
                group = groups.setdefault(group_key, [])
                if any(existing["rank"] == row["rank"] for existing in group):
                    raise ValueError(f"duplicate rank in comparator details at row {row_number}")
                group.append(row)
            for group_key, group in groups.items():
                ranks = sorted(int(row["rank"]) for row in group)
                if ranks != list(range(1, len(group) + 1)):
                    raise ValueError(f"non-contiguous ranks for comparator details group {group_key}")
            for mode in modes:
                baseline = sorted(
                    groups.get(("baseline", "clustered", mode), []),
                    key=lambda row: int(row["rank"]),
                )
                candidate = sorted(
                    groups.get(("candidate", "clustered", mode), []),
                    key=lambda row: int(row["rank"]),
                )
                if input_rows_present and (not baseline or not candidate):
                    raise ValueError(f"missing clustered {mode} rows in comparator details")
                comparable_fields = ["rank", "cluster_id", *TFOSORTED_COLUMNS]
                baseline_values = [tuple(row[field] for field in comparable_fields) for row in baseline]
                candidate_values = [tuple(row[field] for field in comparable_fields) for row in candidate]
                if baseline_values != candidate_values:
                    raise ValueError(f"baseline/candidate clustered {mode} details are inconsistent")
            rows = [
                row
                for mode in modes
                for row in sorted(
                    groups.get(("candidate", "clustered", mode), []),
                    key=lambda item: int(item["rank"]),
                )
            ]
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkflowError(
            f"comparator details artifact is missing or malformed: {exc}",
            EXIT_COMPARATOR_FAILURE,
            "comparator_failure",
        ) from exc
    output.mkdir(parents=True)
    result_path = output / f"gasal2-longtarget-{contract}.tsv"
    fieldnames = ["ranking", "rank", "cluster_id", *TFOSORTED_COLUMNS]
    with result_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({"ranking": row["mode"], **row})
    atomic_json(
        output / "contract.json",
        {
            "schema_version": 1,
            "contract_id": contract,
            "source": "candidate",
            "ranking_modes": modes,
            "top_k": top_k,
            "row_count": len(rows),
            "full_candidate_output_published": False,
        },
    )


def parse_comparator(stdout: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for raw in stdout.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        metrics[key.strip()] = value.strip()
    required = {
        "full_missing_rows",
        "full_extra_rows",
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "boundary_ties_equal",
    }
    missing = sorted(required - metrics.keys())
    if missing:
        raise WorkflowError(
            "comparator did not emit required metrics: " + ",".join(missing),
            EXIT_COMPARATOR_FAILURE,
            "comparator_failure",
        )
    for key in (
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "boundary_ties_equal",
    ):
        if metrics[key] not in {"0", "1"}:
            raise WorkflowError(
                f"comparator metric {key} must be 0 or 1",
                EXIT_COMPARATOR_FAILURE,
                "comparator_failure",
            )
    for key in ("full_missing_rows", "full_extra_rows"):
        try:
            value = int(metrics[key])
        except ValueError as exc:
            raise WorkflowError(
                f"comparator metric {key} must be a non-negative integer",
                EXIT_COMPARATOR_FAILURE,
                "comparator_failure",
            ) from exc
        if value < 0:
            raise WorkflowError(
                f"comparator metric {key} must be a non-negative integer",
                EXIT_COMPARATOR_FAILURE,
                "comparator_failure",
            )
    return metrics


def comparator_report(metrics: dict[str, str], result: BackendResult) -> dict[str, Any]:
    score = metrics["clustered_score_top5_equal"] == "1"
    stability = metrics["clustered_stability_top5_equal"] == "1"
    nt = metrics["clustered_nt_top5_equal"] == "1"
    ties = metrics["boundary_ties_equal"] == "1"
    full = metrics["full_missing_rows"] == "0" and metrics["full_extra_rows"] == "0"
    return {
        "status": "evaluated",
        "returncode": result.returncode,
        "wall_seconds": result.wall_seconds,
        "score_top5_equal": score,
        "stability_top5_equal": stability,
        "nt_top5_equal": nt,
        "boundary_ties_equal": ties,
        "all_ranked_top5_equal": score and stability and nt and ties,
        "full_rows_equal": full,
        "full_missing_rows": int(metrics["full_missing_rows"]),
        "full_extra_rows": int(metrics["full_extra_rows"]),
        "metrics": metrics,
        "stdout_tail": result.stdout[-8192:],
        "stderr_tail": result.stderr[-8192:],
    }


def contract_clean(contract: str, comparison: dict[str, Any]) -> bool:
    if contract == "score-top5":
        return bool(comparison["score_top5_equal"] and comparison["boundary_ties_equal"])
    if contract == "all-ranked-top5":
        return bool(comparison["all_ranked_top5_equal"])
    if contract == "full-output":
        return bool(comparison["full_rows_equal"])
    raise ValueError(f"unknown resolved contract: {contract}")


def gpu_eligibility(
    query: dict[str, Any], target: dict[str, Any], candidate_binary: Path, gpus: list[dict[str, Any]]
) -> list[str]:
    reasons: list[str] = []
    if not executable(candidate_binary):
        reasons.append(f"candidate binary is missing or not executable: {candidate_binary}")
    if query["length_max"] > MAX_GPU_QUERY_LENGTH:
        reasons.append(f"query length {query['length_max']} exceeds checked boundary {MAX_GPU_QUERY_LENGTH}")
    if not gpus:
        reasons.append("no visible NVIDIA GPU was detected")
    else:
        gpu = gpus[0]
        if int(gpu.get("memory_total_mib", 0)) < MIN_GPU_MEMORY_MIB:
            reasons.append(f"visible GPU memory is below checked {MIN_GPU_MEMORY_MIB} MiB boundary")
        if str(gpu.get("compute_capability")) != SUPPORTED_GPU_COMPUTE_CAPABILITY:
            reasons.append(
                "visible GPU compute capability is outside the checked "
                f"{SUPPORTED_GPU_COMPUTE_CAPABILITY} submission envelope"
            )
    return reasons


def no_comparator_report() -> dict[str, Any]:
    return {
        "status": "not_run",
        "returncode": None,
        "wall_seconds": None,
        "score_top5_equal": None,
        "stability_top5_equal": None,
        "nt_top5_equal": None,
        "boundary_ties_equal": None,
        "all_ranked_top5_equal": None,
        "full_rows_equal": None,
        "full_missing_rows": None,
        "full_extra_rows": None,
        "metrics": {},
    }


def base_report(args: argparse.Namespace, started_utc: str) -> dict[str, Any]:
    resolved_contract = (
        "experimental-native"
        if args.mode == "fast-experimental" and args.contract == "auto"
        else "all-ranked-top5"
        if args.contract == "auto"
        else args.contract
    )
    relevant = {
        key: os.environ[key]
        for key in ("CUDA_VISIBLE_DEVICES",)
        if key in os.environ
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "software_version": VERSION,
        "wrapper_commit": git_commit(),
        "paper_runtime_commit": PAPER_RUNTIME_COMMIT,
        "mode": args.mode,
        "requested_contract": args.contract,
        "resolved_contract": resolved_contract,
        "resolved_execution": None,
        "result_status": "preflight_pending",
        "authority_backend": str(args.authority_binary.resolve()),
        "candidate_backend": str(args.candidate_binary.resolve()),
        "inputs": {
            "query": {
                "path": str(args.query),
                "sha256": None,
                "size_bytes": None,
                "record_count": None,
                "length_min": None,
                "length_max": None,
                "lengths": [],
                "total_bp": None,
            },
            "target": {
                "path": str(args.target),
                "sha256": None,
                "size_bytes": None,
                "record_count": None,
                "length_min": None,
                "length_max": None,
                "lengths": [],
                "total_bp": None,
            },
        },
        "biological_metadata": {
            "assembly": args.assembly,
            "annotation_release": args.annotation_release,
        },
        "environment": {
            "platform": platform.platform(),
            "cpu_model": cpu_model(),
            "cpu_thread_count": os.cpu_count(),
            "gpu_count": None,
            "gpus": [],
            "worker_density": 1,
            "minimum_gpu_memory_mib": MIN_GPU_MEMORY_MIB,
            "checked_compute_capability": SUPPORTED_GPU_COMPUTE_CAPABILITY,
            "cuda_toolkit": None,
        },
        "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "relevant_environment": relevant,
        "timestamps": {"start_utc": started_utc, "end_utc": None, "wall_seconds": None},
        "backends": {"authority": None, "candidate": None},
        "comparators": no_comparator_report(),
        "counters": {"fallback": 0, "guard": 0, "oom": 0, "timeout": 0},
        "preflight": {"passed": False, "checks": {}, "gpu_ineligibility_reasons": []},
        "planned_commands": [],
        "published_source": None,
        "published_outputs": [],
        "warnings": [],
        "errors": [],
    }


def finish_report(report: dict[str, Any], started: float) -> None:
    report["timestamps"]["end_utc"] = utc_now()
    report["timestamps"]["wall_seconds"] = time.perf_counter() - started


def validate_schema_value(schema: dict[str, Any], value: Any, path: str) -> None:
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} is outside the allowed enum")
    expected_type = schema.get("type")
    if expected_type is not None:
        names = expected_type if isinstance(expected_type, list) else [expected_type]

        def matches(name: str) -> bool:
            if name == "array":
                return isinstance(value, list)
            if name == "boolean":
                return isinstance(value, bool)
            if name == "integer":
                return isinstance(value, int) and not isinstance(value, bool)
            if name == "null":
                return value is None
            if name == "number":
                return isinstance(value, (int, float)) and not isinstance(value, bool)
            if name == "object":
                return isinstance(value, dict)
            if name == "string":
                return isinstance(value, str)
            raise ValueError(f"unsupported JSON Schema type in validator: {name}")

        if not any(matches(name) for name in names):
            raise ValueError(f"{path} has the wrong JSON type")
    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                raise ValueError(f"{path}.{field} is required")
        for field, child_schema in schema.get("properties", {}).items():
            if field in value:
                validate_schema_value(child_schema, value[field], f"{path}.{field}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate_schema_value(schema["items"], item, f"{path}[{index}]")


def validate_report(report: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        validate_schema_value(schema, report, "report")
    except ValueError as exc:
        raise WorkflowError(
            f"run report does not validate against schema: {exc}",
            EXIT_INTERNAL,
            "internal_error",
        ) from exc


def check_destination(args: argparse.Namespace) -> None:
    output = args.output.resolve()
    report = args.report.resolve()
    if report == output or output in report.parents:
        raise WorkflowError(
            "--report must be outside --output so both artifacts have independent atomic publication",
            EXIT_INVALID_INPUT,
            "invalid_input",
        )
    if output.exists() and not args.force:
        raise WorkflowError(f"output already exists: {output}", EXIT_INVALID_INPUT, "invalid_input")
    if report.exists() and not args.force:
        raise WorkflowError(f"report already exists: {report}", EXIT_INVALID_INPUT, "invalid_input")
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    for parent, label in ((output.parent, "output"), (report.parent, "report")):
        if not parent.is_dir() or not os.access(parent, os.W_OK):
            raise WorkflowError(f"{label} parent is not writable: {parent}", EXIT_INVALID_INPUT, "invalid_input")


def collect_outputs(stage: Path, final_output: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for path in sorted(item for item in stage.rglob("*") if item.is_file()):
        relative = path.relative_to(stage)
        records: int | None = None
        if path.name.endswith("-TFOsorted") or path.suffix == ".tsv":
            with path.open(encoding="utf-8", errors="replace") as handle:
                records = max(sum(1 for _ in handle) - 1, 0)
        outputs.append(
            {
                "path": str(final_output / relative),
                "relative_path": str(relative),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "record_count": records,
            }
        )
    return outputs


def publish(
    selected: Path,
    source: str,
    report: dict[str, Any],
    args: argparse.Namespace,
    temporary_root: Path,
) -> None:
    stage = temporary_root / "published"
    shutil.copytree(selected, stage)
    report["published_source"] = source
    report["published_outputs"] = collect_outputs(stage, args.output.resolve())
    validate_report(report)

    backup: Path | None = None
    if args.output.exists():
        backup = args.output.parent / f".{args.output.name}.backup.{os.getpid()}"
        os.replace(args.output, backup)
    try:
        os.replace(stage, args.output)
        atomic_json(args.report, report)
    except Exception:
        shutil.rmtree(args.output, ignore_errors=True)
        if backup is not None:
            os.replace(backup, args.output)
        raise
    else:
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)


def plan_commands(args: argparse.Namespace, execution: str) -> list[list[str]]:
    placeholder = Path("<temporary>")
    commands: list[list[str]] = []
    if execution in {"verified", "fast-experimental"}:
        commands.append(
            backend_command(args.candidate_binary, args.target, args.query, args.rule, placeholder / "candidate")
        )
    if execution in {"verified", "cpu-authority"}:
        commands.append(
            backend_command(args.authority_binary, args.target, args.query, args.rule, placeholder / "authority")
        )
    if execution == "verified":
        commands.append(
            [
                sys.executable,
                str(args.comparator),
                "--baseline",
                str(placeholder / "authority" / "*-TFOsorted"),
                "--candidate",
                str(placeholder / "candidate" / "*-TFOsorted"),
            ]
        )
    return commands


def execute(args: argparse.Namespace, report: dict[str, Any], started: float) -> int:
    check_destination(args)
    query = parse_fasta(args.query, "query")
    target = parse_fasta(args.target, "target")
    report["inputs"] = {"query": query, "target": target}
    if query["record_count"] != 1:
        raise WorkflowError(
            "the current workflow requires exactly one query FASTA record per invocation",
            EXIT_INVALID_INPUT,
            "invalid_input",
        )
    if target["record_count"] != 1:
        raise WorkflowError(
            "the current workflow requires exactly one target FASTA record per invocation",
            EXIT_INVALID_INPUT,
            "invalid_input",
        )
    gpus = detect_gpus()
    report["environment"]["gpu_count"] = len(gpus)
    report["environment"]["gpus"] = gpus

    resolved_contract = report["resolved_contract"]
    if args.mode == "fast-experimental" and args.contract != "auto":
        raise WorkflowError(
            "fast-experimental publishes only experimental-native output; named product contracts require verification",
            EXIT_INVALID_INPUT,
            "unsupported_contract",
        )
    if args.mode in {"verified", "fast-experimental"} and query["length_max"] > MAX_GPU_QUERY_LENGTH:
        raise WorkflowError(
            f"query length {query['length_max']} exceeds checked GPU boundary {MAX_GPU_QUERY_LENGTH}",
            EXIT_INVALID_INPUT,
            "invalid_input",
        )

    eligibility = gpu_eligibility(query, target, args.candidate_binary, gpus)
    report["preflight"]["gpu_ineligibility_reasons"] = eligibility
    authority_needed = args.mode in {"safe", "verified", "cpu-authority"}
    if authority_needed and not executable(args.authority_binary):
        raise WorkflowError(
            f"authority binary is missing or not executable: {args.authority_binary}",
            EXIT_ENVIRONMENT,
            "environment_unavailable",
        )

    if args.mode == "cpu-authority":
        execution = "cpu-authority"
    elif args.mode == "fast-experimental":
        if eligibility:
            raise WorkflowError("; ".join(eligibility), EXIT_ENVIRONMENT, "environment_unavailable")
        execution = "fast-experimental"
    elif args.mode == "verified":
        if eligibility:
            raise WorkflowError("; ".join(eligibility), EXIT_ENVIRONMENT, "environment_unavailable")
        execution = "verified"
    else:
        if resolved_contract == "full-output" or eligibility:
            execution = "cpu-authority"
            if eligibility:
                report["warnings"].append(
                    "candidate environment is not eligible; safe mode selected CPU authority before execution: "
                    + "; ".join(eligibility)
                )
                report["counters"]["guard"] += 1
        else:
            execution = "verified"

    report["resolved_execution"] = execution
    report["planned_commands"] = plan_commands(args, execution)
    report["preflight"]["checks"] = {
        "query_fasta_valid": True,
        "target_fasta_valid": True,
        "output_parent_writable": True,
        "report_parent_writable": True,
        "normal_triplex_preset": args.triplex_preset == "normal",
        "rule_explicit": args.rule == 0,
        "top_k_fixed": args.top_k == 5,
        "worker_density": 1,
        "authority_binary_available": executable(args.authority_binary),
        "candidate_binary_available": executable(args.candidate_binary),
    }
    report["preflight"]["passed"] = True
    authority_environment, authority_contract_env = sanitized_environment(False)
    candidate_environment, candidate_contract_env = sanitized_environment(True)
    report["relevant_environment"]["authority_contract"] = authority_contract_env
    report["relevant_environment"]["candidate_contract"] = candidate_contract_env

    if args.dry_run:
        report["result_status"] = "dry_run"
        finish_report(report, started)
        validate_report(report)
        atomic_json(args.report, report)
        return EXIT_SUCCESS

    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.partial.", dir=args.output.parent)
    )
    try:
        authority_output = temporary_root / "authority"
        candidate_output = temporary_root / "candidate"
        selected: Path
        selected_source: str

        candidate_result: BackendResult | None = None
        candidate_usable = False
        candidate_tfosorted: Path | None = None
        candidate_validation_error: str | None = None
        if execution in {"verified", "fast-experimental"}:
            candidate_output.mkdir(parents=True)
            candidate_result = run_command(
                backend_command(args.candidate_binary, args.target, args.query, args.rule, candidate_output),
                candidate_environment,
                args.timeout,
            )
            write_backend_logs(candidate_output, candidate_result)
            report["backends"]["candidate"] = candidate_result.report()
            if candidate_result.timed_out:
                report["counters"]["timeout"] += 1
            if "out of memory" in candidate_result.stderr.lower():
                report["counters"]["oom"] += 1
            candidate_usable = candidate_result.returncode == 0
            if candidate_usable:
                try:
                    candidate_tfosorted = validate_tfosorted(candidate_output, "candidate")
                except WorkflowError as exc:
                    candidate_usable = False
                    candidate_validation_error = str(exc)
            if execution == "fast-experimental":
                if not candidate_usable:
                    raise WorkflowError(
                        candidate_validation_error or "candidate backend failed without a safe fallback",
                        EXIT_CANDIDATE_FAILURE,
                        "candidate_failure",
                    )
                print(
                    "WARNING: EXPERIMENTAL GPU output is unverified and outside a promoted safe contract.",
                    file=sys.stderr,
                )
                report["warnings"].append(
                    "EXPERIMENTAL GPU output was published without authority verification"
                )
                atomic_json(
                    candidate_output / "contract.json",
                    {
                        "schema_version": 1,
                        "contract_id": "experimental-native",
                        "status": "experimental_unverified",
                        "source": "candidate",
                        "raw_candidate_output_published": True,
                        "product_contract_satisfied": False,
                    },
                )
                report["result_status"] = "experimental_unverified"
                selected = candidate_output
                selected_source = "candidate"

        authority_result: BackendResult | None = None
        authority_tfosorted: Path | None = None
        if execution in {"verified", "cpu-authority"}:
            authority_output.mkdir(parents=True)
            authority_result = run_command(
                backend_command(args.authority_binary, args.target, args.query, args.rule, authority_output),
                authority_environment,
                args.timeout,
            )
            write_backend_logs(authority_output, authority_result)
            report["backends"]["authority"] = authority_result.report()
            if authority_result.timed_out:
                report["counters"]["timeout"] += 1
            if authority_result.returncode != 0:
                raise WorkflowError(
                    "authority backend failed",
                    EXIT_AUTHORITY_FAILURE,
                    "authority_failure",
                )
            authority_tfosorted = validate_tfosorted(authority_output, "authority")
            if execution == "cpu-authority":
                report["result_status"] = "authority_complete"
                selected = authority_output
                selected_source = "authority"

        if execution == "verified":
            assert authority_result is not None
            if not candidate_usable:
                report["counters"]["fallback"] += 1
                report["result_status"] = "cpu_fallback_after_candidate_failure"
                report["warnings"].append(
                    (candidate_validation_error or "candidate failed")
                    + "; authority output was published"
                )
                selected = authority_output
                selected_source = "authority"
            else:
                try:
                    assert authority_tfosorted is not None
                    assert candidate_tfosorted is not None
                    comparator_details = temporary_root / "comparator-details.tsv"
                    comparator_environment = os.environ.copy()
                    comparator_result = run_command(
                        [
                            sys.executable,
                            str(args.comparator),
                            "--baseline",
                            str(authority_tfosorted),
                            "--candidate",
                            str(candidate_tfosorted),
                            "--k",
                            str(args.top_k),
                            "--details",
                            str(comparator_details),
                        ],
                        comparator_environment,
                        args.timeout,
                    )
                    if comparator_result.timed_out:
                        report["counters"]["timeout"] += 1
                        report["comparators"] = failed_comparator_report(
                            comparator_result, "comparator timed out"
                        )
                        raise WorkflowError(
                            "comparator timed out",
                            EXIT_COMPARATOR_FAILURE,
                            "comparator_failure",
                        )
                    if comparator_result.returncode not in {0, 1}:
                        report["comparators"] = failed_comparator_report(
                            comparator_result,
                            f"unsupported comparator return code {comparator_result.returncode}",
                        )
                        raise WorkflowError(
                            f"comparator returned unsupported code {comparator_result.returncode}",
                            EXIT_COMPARATOR_FAILURE,
                            "comparator_failure",
                        )
                    try:
                        metrics = parse_comparator(comparator_result.stdout)
                    except WorkflowError as exc:
                        report["comparators"] = failed_comparator_report(
                            comparator_result, str(exc)
                        )
                        raise
                    comparison = comparator_report(metrics, comparator_result)
                    declared_clean = contract_clean(str(resolved_contract), comparison)
                    comparison["declared_contract"] = resolved_contract
                    comparison["declared_contract_clean"] = declared_clean
                    comparison["status"] = "clean" if declared_clean else "mismatch"
                    report["comparators"] = comparison
                    if declared_clean:
                        report["result_status"] = "candidate_clean"
                        if resolved_contract in {"score-top5", "all-ranked-top5"}:
                            contract_output = temporary_root / "contract-output"
                            write_contract_output(
                                comparator_details,
                                str(resolved_contract),
                                contract_output,
                                args.top_k,
                                authority_tfosorted,
                                candidate_tfosorted,
                            )
                            selected = contract_output
                        else:
                            selected = candidate_output
                        selected_source = "candidate"
                    else:
                        report["counters"]["fallback"] += 1
                        report["result_status"] = "cpu_fallback_after_mismatch"
                        report["warnings"].append(
                            "candidate did not satisfy the declared contract; authority output was published"
                        )
                        selected = authority_output
                        selected_source = "authority"
                except WorkflowError as exc:
                    if exc.result_status in {"candidate_failure", "comparator_failure"}:
                        if (
                            exc.result_status == "comparator_failure"
                            and report["comparators"]["status"] != "failed"
                        ):
                            report["comparators"] = failed_comparator_report(
                                comparator_result, str(exc)
                            )
                        report["counters"]["fallback"] += 1
                        report["result_status"] = (
                            "cpu_fallback_after_candidate_failure"
                            if exc.result_status == "candidate_failure"
                            else "cpu_fallback_after_comparator_failure"
                        )
                        report["warnings"].append(f"{exc}; authority output was published")
                        selected = authority_output
                        selected_source = "authority"
                    else:
                        raise

        finish_report(report, started)
        publish(selected, selected_source, report, args, temporary_root)
        return EXIT_SUCCESS
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="gasal2-longtarget",
        description="Contract-aware Fasim/GASAL2 LongTarget workflow.",
    )
    result.add_argument("--version", action="version", version=f"gasal2-longtarget {VERSION}")
    result.add_argument(
        "--mode",
        choices=("safe", "verified", "fast-experimental", "cpu-authority"),
        default="safe",
    )
    result.add_argument(
        "--contract",
        choices=("auto", "score-top5", "all-ranked-top5", "full-output"),
        default="auto",
    )
    result.add_argument("--query", required=True, type=Path)
    result.add_argument("--target", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--report", required=True, type=Path)
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--force", action="store_true")
    result.add_argument("--rule", type=int, choices=(0,), default=0)
    result.add_argument("--triplex-preset", choices=("normal",), default="normal")
    result.add_argument("--top-k", type=int, choices=(5,), default=5)
    result.add_argument("--assembly")
    result.add_argument("--annotation-release")
    result.add_argument("--timeout", type=int, default=3600)
    result.add_argument("--authority-binary", type=Path, default=ROOT / "fasim_longtarget_x86")
    result.add_argument("--candidate-binary", type=Path, default=ROOT / "fasim_longtarget_gasal2")
    result.add_argument(
        "--comparator",
        type=Path,
        default=ROOT / "scripts/compare_fasim_segmented_contract.py",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    if args.timeout <= 0:
        parser().error("--timeout must be positive")
    for attribute in (
        "query",
        "target",
        "output",
        "report",
        "authority_binary",
        "candidate_binary",
        "comparator",
    ):
        setattr(args, attribute, getattr(args, attribute).resolve())
    started = time.perf_counter()
    report = base_report(args, utc_now())
    old_sigint = signal.getsignal(signal.SIGINT)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    report_allowed = not args.report.exists() or args.force
    try:
        return execute(args, report, started)
    except WorkflowInterrupted as exc:
        report["result_status"] = "interrupted"
        report["errors"].append(str(exc))
        finish_report(report, started)
        if report_allowed:
            try:
                validate_report(report)
                atomic_json(args.report, report)
            except Exception:
                pass
        print(str(exc), file=sys.stderr)
        return EXIT_INTERRUPTED
    except WorkflowError as exc:
        report["result_status"] = exc.result_status
        report["errors"].append(str(exc))
        finish_report(report, started)
        if report_allowed:
            try:
                validate_report(report)
                atomic_json(args.report, report)
            except Exception as report_exc:
                print(f"failed to write run report: {report_exc}", file=sys.stderr)
                return EXIT_INTERNAL
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        _kill_active_child()
        report["result_status"] = "internal_error"
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        finish_report(report, started)
        if report_allowed:
            try:
                validate_report(report)
                atomic_json(args.report, report)
            except Exception:
                pass
        print(f"internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)


if __name__ == "__main__":
    raise SystemExit(main())
