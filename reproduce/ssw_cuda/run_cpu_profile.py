#!/usr/bin/env python3
"""Run and audit the SSW-CUDA Phase 1 CPU authority profile."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import random
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/ssw_cuda"
PLAN = PAPER / "cpu_profile_attempt_plan.tsv"
SOURCE_DATA = PAPER / "cpu_profile_source_data.tsv"
STATISTICS = PAPER / "cpu_profile_statistics.json"
DECISION_JSON = PAPER / "amdahl_decision.json"
DECISION_MD = PAPER / "amdahl_decision.md"
EXECUTION_RECEIPT = PAPER / "cpu_profile_execution_receipt.json"
REGISTRY = PAPER / "used_input_exclusion_registry.tsv"
DEFAULT_ARTIFACT_ROOT = ROOT / ".paper-artifacts/ssw-cuda-v1/phase1/profile-runs"
PROFILE_PREFIX = "benchmark.ssw_cuda_phase1."
TARGET_SPEEDUP = 10.0
BOOTSTRAP_ITERATIONS = 10_000
BOOTSTRAP_SEED = 20260727

STAGES = (
    "pre_align",
    "selection",
    "forward_alignment",
    "reverse_alignment",
    "banded_traceback",
    "backend_bridge",
    "downstream_triplex_conversion",
    "stability_identity_nt",
    "clustering_ranking_sort",
    "serialization_io",
    "wrapper_other",
    "process_wrapper",
)
STRICT_STAGES = (
    "pre_align",
    "selection",
    "forward_alignment",
    "reverse_alignment",
    "banded_traceback",
)
BACKEND_STAGES = STRICT_STAGES + ("backend_bridge",)

PLAN_FIELDS = (
    "attempt_id",
    "execution_order",
    "workload_id",
    "workload_class",
    "claim_relevant",
    "query_path",
    "target_path",
    "query_file_sha256",
    "target_file_sha256",
    "query_sequence_sha256",
    "target_sequence_sha256",
    "observation_id",
    "cache_state",
    "profile_mode",
    "command",
    "environment_json",
    "timeout_seconds",
    "retry_policy",
    "formal_source_data",
    "expected_artifact_root",
    "status",
)

SOURCE_FIELDS = (
    "attempt_id",
    "execution_order",
    "workload_id",
    "workload_class",
    "claim_relevant",
    "observation_id",
    "cache_state",
    "profile_mode",
    "returncode",
    "timed_out",
    "outer_wall_seconds",
    "profile_total_seconds",
    *tuple(f"{stage}_seconds" for stage in STAGES),
    "stage_sum_seconds",
    "p_strict_ssw",
    "p_backend_addressable",
    "maximum_speedup_infinite",
    "required_backend_speedup",
    "output_digest",
    "paired_output_equal",
    "profile_stack_errors",
    "profile_active_depth",
    "profile_max_depth",
    "max_rss_kib",
    "cache_drop_hint",
    "binary_sha256",
    "git_commit",
    "query_file_sha256",
    "target_file_sha256",
    "artifact_receipt",
)

WORKLOAD_SPECS = (
    {
        "workload_id": "overhead_aq001_at0001",
        "workload_class": "small_overhead",
        "claim_relevant": "0",
        "query_path": "reproduce/bioinformatics/application_inputs/queries/aq001.fa",
        "target_path": "reproduce/bioinformatics/application_inputs/targets/at0001.fa",
    },
    {
        "workload_id": "medium_h19_chr22_2mb",
        "workload_class": "medium_real",
        "claim_relevant": "0",
        "query_path": "H19.fa",
        "target_path": ".tmp/fasim_gasal2_chr22_slice_10m_12m.fa",
    },
    {
        "workload_id": "large_h19_chr21",
        "workload_class": "claim_relevant_large",
        "claim_relevant": "1",
        "query_path": "H19.fa",
        "target_path": ".tmp/gasal2_hg38_archive_first_run/shards/chr21.fa",
    },
    {
        "workload_id": "large_h19_chr22",
        "workload_class": "claim_relevant_large",
        "claim_relevant": "1",
        "query_path": "H19.fa",
        "target_path": ".tmp/gasal2_hg38_archive_first_run/shards/chr22.fa",
    },
    {
        "workload_id": "application_aq005_at0199",
        "workload_class": "application_like_consumed",
        "claim_relevant": "0",
        "query_path": "reproduce/bioinformatics/application_inputs/queries/aq005.fa",
        "target_path": "reproduce/bioinformatics/application_inputs/targets/at0199.fa",
    },
)


class ProfileError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProfileError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.partial.{os.getpid()}"
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fields: Sequence[str], rows: Iterable[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def read_tsv(
    path: Path, expected_fields: Sequence[str] | None = None
) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if expected_fields is not None:
            require(tuple(reader.fieldnames or ()) == tuple(expected_fields), f"unexpected fields: {path}")
        return list(reader)


def parse_single_fasta(path: Path) -> tuple[str, int]:
    sequences: list[str] = []
    current: list[str] | None = None
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                require(current is None, f"Phase 1 input must contain one FASTA record: {path}")
                current = []
                continue
            require(current is not None, f"sequence before FASTA header: {path}")
            normalized = line.upper()
            require(not (set(normalized) - set("ACGTN")), f"invalid FASTA sequence: {path}")
            current.append(normalized)
    require(current is not None and current, f"empty FASTA: {path}")
    sequences.append("".join(current))
    sequence = sequences[0]
    return sha256_bytes(sequence.encode("ascii")), len(sequence)


def compact_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def expected_plan_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    execution_order = 0
    for workload in WORKLOAD_SPECS:
        query = ROOT / workload["query_path"]
        target = ROOT / workload["target_path"]
        require(query.is_file() and not query.is_symlink(), f"missing query: {query}")
        require(target.is_file() and not target.is_symlink(), f"missing target: {target}")
        query_sequence_sha, _ = parse_single_fasta(query)
        target_sequence_sha, _ = parse_single_fasta(target)
        for observation in range(1, 6):
            modes = ("profile_off", "profile_on") if observation % 2 else ("profile_on", "profile_off")
            for mode in modes:
                execution_order += 1
                profile_value = "1" if mode == "profile_on" else "0"
                attempt_id = f"p1_{workload['workload_id']}_o{observation:02d}_{mode}"
                environment = {
                    "FASIM_EXTEND_THREADS": "1",
                    "FASIM_OUTPUT_MODE": "tfosorted",
                    "FASIM_SSW_CUDA_PHASE1_PROFILE": profile_value,
                    "FASIM_VERBOSE": "0",
                }
                command = (
                    f"{{binary}} -f1 {workload['target_path']} -f2 {workload['query_path']} "
                    f"-r 0 -cn 1 -O {{attempt_output}}"
                )
                rows.append(
                    {
                        "attempt_id": attempt_id,
                        "execution_order": execution_order,
                        "workload_id": workload["workload_id"],
                        "workload_class": workload["workload_class"],
                        "claim_relevant": workload["claim_relevant"],
                        "query_path": workload["query_path"],
                        "target_path": workload["target_path"],
                        "query_file_sha256": sha256_file(query),
                        "target_file_sha256": sha256_file(target),
                        "query_sequence_sha256": query_sequence_sha,
                        "target_sequence_sha256": target_sequence_sha,
                        "observation_id": observation,
                        "cache_state": "cold_advisory" if observation == 1 else "steady_state",
                        "profile_mode": mode,
                        "command": command,
                        "environment_json": compact_json(environment),
                        "timeout_seconds": 1800,
                        "retry_policy": "none",
                        "formal_source_data": 1,
                        "expected_artifact_root": (
                            ".paper-artifacts/ssw-cuda-v1/phase1/profile-runs/" + attempt_id
                        ),
                        "status": "preregistered_not_run",
                    }
                )
    return rows


def registry_consumed(row: dict[str, object], registry: list[dict[str, str]]) -> bool:
    query_digests = {str(row["query_file_sha256"]), str(row["query_sequence_sha256"])}
    target_digests = {str(row["target_file_sha256"]), str(row["target_sequence_sha256"])}
    return any(
        item.get("record_type") == "pair"
        and item.get("query_sha256") in query_digests
        and item.get("target_sha256") in target_digests
        for item in registry
    )


def validate_plan() -> list[dict[str, str]]:
    expected = expected_plan_rows()
    expected_payload = tsv_bytes(PLAN_FIELDS, expected)
    require(PLAN.is_file() and not PLAN.is_symlink(), f"missing frozen plan: {PLAN}")
    require(PLAN.read_bytes() == expected_payload, "CPU profile attempt plan drift")
    observed = read_tsv(PLAN, PLAN_FIELDS)
    require(len(observed) == 50, "Phase 1 plan must contain exactly 50 attempts")
    require(len({row["attempt_id"] for row in observed}) == 50, "duplicate attempt ID")
    require(
        [int(row["execution_order"]) for row in observed] == list(range(1, 51)),
        "execution order is not contiguous",
    )
    registry = read_tsv(REGISTRY)
    require(all(registry_consumed(row, registry) for row in expected), "plan consumes a fresh input")
    for row in observed:
        require(row["retry_policy"] == "none", "retry policy drift")
        require(row["formal_source_data"] == "1", "profile evidence role drift")
        require(row["status"] == "preregistered_not_run", "preexecution status drift")
        environment = json.loads(row["environment_json"])
        require(environment["FASIM_EXTEND_THREADS"] == "1", "thread count drift")
        require(environment["FASIM_OUTPUT_MODE"] == "tfosorted", "output contract drift")
    return observed


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(result.returncode == 0, result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def clean_environment(values: dict[str, str]) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FASIM_")}
    environment.update(values)
    environment["LC_ALL"] = "C"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def cache_drop_hint(paths: Sequence[Path]) -> str:
    if not hasattr(os, "posix_fadvise") or not hasattr(os, "POSIX_FADV_DONTNEED"):
        return "not_available"
    statuses: list[str] = []
    for path in paths:
        try:
            with path.open("rb") as handle:
                os.posix_fadvise(handle.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            statuses.append("advised")
        except OSError as exc:
            statuses.append(f"error_{exc.errno}")
    return ";".join(statuses)


def parse_profile_metrics(stderr: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in stderr.splitlines():
        if not line.startswith(PROFILE_PREFIX) or "=" not in line:
            continue
        key, value = line[len(PROFILE_PREFIX) :].split("=", 1)
        require(key not in metrics, f"duplicate profile metric: {key}")
        metrics[key] = value
    return metrics


def output_digest(output_dir: Path) -> tuple[str, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    for path in sorted(output_dir.rglob("*")):
        require(not path.is_symlink(), f"output symlink is forbidden: {path}")
        if path.is_file():
            rows.append(
                {
                    "path": str(path.relative_to(output_dir)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    require(rows, f"authority emitted no files: {output_dir}")
    return sha256_bytes(tsv_bytes(("path", "size_bytes", "sha256"), rows)), rows


def parse_max_rss(path: Path) -> int | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Maximum resident set size (kbytes):"):
            return int(line.split(":", 1)[1].strip())
    return None


def kill_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_attempt(
    row: dict[str, str],
    *,
    binary: Path,
    artifact_root: Path,
    git_commit: str,
) -> dict[str, object]:
    attempt_dir = artifact_root / row["attempt_id"]
    require(not attempt_dir.exists(), f"attempt already exists: {attempt_dir}")
    output_dir = attempt_dir / "output"
    output_dir.mkdir(parents=True)
    query = ROOT / row["query_path"]
    target = ROOT / row["target_path"]
    require(sha256_file(query) == row["query_file_sha256"], "query digest drift")
    require(sha256_file(target) == row["target_file_sha256"], "target digest drift")

    command = [
        str(binary),
        "-f1",
        str(target),
        "-f2",
        str(query),
        "-r",
        "0",
        "-cn",
        "1",
        "-O",
        str(output_dir),
    ]
    environment_values = json.loads(row["environment_json"])
    environment = clean_environment(environment_values)
    cache_hint = "not_requested"
    if row["cache_state"] == "cold_advisory":
        cache_hint = cache_drop_hint((query, target))

    resource_path = attempt_dir / "time.txt"
    measured_command = command
    if Path("/usr/bin/time").is_file():
        measured_command = ["/usr/bin/time", "-v", "-o", str(resource_path), *command]
    started_utc = utc_now()
    started = time.perf_counter()
    timed_out = False
    with (attempt_dir / "stdout.log").open("w", encoding="utf-8") as stdout_handle, (
        attempt_dir / "stderr.log"
    ).open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            measured_command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=int(row["timeout_seconds"]))
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_process_group(process)
            returncode = 124
    outer_wall = time.perf_counter() - started
    stderr = (attempt_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    metrics = parse_profile_metrics(stderr)
    profile_on = row["profile_mode"] == "profile_on"
    if profile_on:
        required = {
            "schema_version",
            "profile_enabled",
            "total_seconds",
            "stage_sum_seconds",
            "wrapper_other_seconds",
            "stack_errors",
            "max_depth",
            "active_depth",
            *tuple(f"{stage}_seconds" for stage in STAGES[:-2]),
        }
        require(required.issubset(metrics), f"missing profile metrics: {sorted(required - metrics.keys())}")
    else:
        require(not metrics, "default-off attempt unexpectedly emitted profile metrics")

    digest, output_rows = output_digest(output_dir) if returncode == 0 else ("", [])
    receipt = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "status": "complete" if returncode == 0 and not timed_out else "technical_failure",
        "start_utc": started_utc,
        "end_utc": utc_now(),
        "git_commit": git_commit,
        "binary_path": str(binary),
        "binary_sha256": sha256_file(binary),
        "command": command,
        "measured_command": measured_command,
        "environment": environment_values,
        "plan_row": row,
        "returncode": returncode,
        "timed_out": timed_out,
        "outer_wall_seconds": outer_wall,
        "cache_drop_hint": cache_hint,
        "max_rss_kib": parse_max_rss(resource_path),
        "profile_metrics": metrics,
        "output_digest": digest,
        "output_manifest": output_rows,
    }
    atomic_write(attempt_dir / "attempt.json", json_bytes(receipt))
    return receipt


def receipts_from_artifacts(rows: list[dict[str, str]], artifact_root: Path) -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    for row in rows:
        path = artifact_root / row["attempt_id"] / "attempt.json"
        require(path.is_file() and not path.is_symlink(), f"missing attempt receipt: {path}")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        require(receipt["attempt_id"] == row["attempt_id"], "attempt receipt ID drift")
        require(receipt["plan_row"] == row, "attempt receipt plan row drift")
        require(receipt["status"] == "complete", f"incomplete attempt: {row['attempt_id']}")
        receipts.append(receipt)
    return receipts


def optional_float(value: float | None) -> str:
    return "" if value is None or not math.isfinite(value) else format(value, ".12g")


def amdahl_projection(addressable_fraction: float) -> tuple[float, float | None]:
    require(0.0 <= addressable_fraction <= 1.000001, "invalid addressable fraction")
    maximum = (
        math.inf
        if addressable_fraction >= 1.0
        else 1.0 / (1.0 - addressable_fraction)
    )
    if addressable_fraction <= 0.90:
        return maximum, None
    denominator = 1.0 / TARGET_SPEEDUP - (1.0 - addressable_fraction)
    require(denominator > 0.0, "invalid positive-headroom Amdahl denominator")
    return maximum, addressable_fraction / denominator


def source_rows(
    rows: list[dict[str, str]], receipts: list[dict[str, object]]
) -> list[dict[str, object]]:
    by_attempt = {str(receipt["attempt_id"]): receipt for receipt in receipts}
    paired: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        key = (row["workload_id"], row["observation_id"])
        paired.setdefault(key, {})[row["profile_mode"]] = by_attempt[row["attempt_id"]]
    for key, modes in paired.items():
        require(set(modes) == {"profile_off", "profile_on"}, f"incomplete on/off pair: {key}")
        require(
            modes["profile_off"]["output_digest"] == modes["profile_on"]["output_digest"],
            f"instrumentation changed authority output: {key}",
        )

    output: list[dict[str, object]] = []
    for row in rows:
        receipt = by_attempt[row["attempt_id"]]
        profile_on = row["profile_mode"] == "profile_on"
        metrics = receipt["profile_metrics"]
        outer = float(receipt["outer_wall_seconds"])
        values: dict[str, float | None] = {stage: None for stage in STAGES}
        profile_total: float | None = None
        stage_sum: float | None = None
        p_strict: float | None = None
        p_backend: float | None = None
        maximum: float | None = None
        required_backend: float | None = None
        if profile_on:
            profile_total = float(metrics["total_seconds"])
            for stage in STAGES[:-2]:
                values[stage] = float(metrics[f"{stage}_seconds"])
            values["wrapper_other"] = float(metrics["wrapper_other_seconds"])
            process_wrapper = outer - profile_total
            require(
                process_wrapper >= -max(0.002, outer * 0.02),
                f"profile timer exceeds outer wall materially: {row['attempt_id']}",
            )
            values["process_wrapper"] = max(0.0, process_wrapper)
            stage_sum = sum(float(values[stage] or 0.0) for stage in STAGES)
            require(
                abs(stage_sum - outer) <= max(0.002, outer * 0.02),
                f"stage coverage exceeds 2% tolerance: {row['attempt_id']}",
            )
            p_strict = sum(float(values[stage] or 0.0) for stage in STRICT_STAGES) / outer
            p_backend = sum(float(values[stage] or 0.0) for stage in BACKEND_STAGES) / outer
            require(0.0 <= p_strict <= p_backend <= 1.000001, "invalid addressable fraction")
            maximum, required_backend = amdahl_projection(p_backend)
        key = (row["workload_id"], row["observation_id"])
        pair_modes = paired[key]
        output.append(
            {
                "attempt_id": row["attempt_id"],
                "execution_order": row["execution_order"],
                "workload_id": row["workload_id"],
                "workload_class": row["workload_class"],
                "claim_relevant": row["claim_relevant"],
                "observation_id": row["observation_id"],
                "cache_state": row["cache_state"],
                "profile_mode": row["profile_mode"],
                "returncode": receipt["returncode"],
                "timed_out": int(bool(receipt["timed_out"])),
                "outer_wall_seconds": optional_float(outer),
                "profile_total_seconds": optional_float(profile_total),
                **{f"{stage}_seconds": optional_float(values[stage]) for stage in STAGES},
                "stage_sum_seconds": optional_float(stage_sum),
                "p_strict_ssw": optional_float(p_strict),
                "p_backend_addressable": optional_float(p_backend),
                "maximum_speedup_infinite": optional_float(maximum),
                "required_backend_speedup": optional_float(required_backend),
                "output_digest": receipt["output_digest"],
                "paired_output_equal": int(
                    pair_modes["profile_off"]["output_digest"]
                    == pair_modes["profile_on"]["output_digest"]
                ),
                "profile_stack_errors": metrics.get("stack_errors", "") if profile_on else "",
                "profile_active_depth": metrics.get("active_depth", "") if profile_on else "",
                "profile_max_depth": metrics.get("max_depth", "") if profile_on else "",
                "max_rss_kib": receipt["max_rss_kib"] if receipt["max_rss_kib"] is not None else "",
                "cache_drop_hint": receipt["cache_drop_hint"],
                "binary_sha256": receipt["binary_sha256"],
                "git_commit": receipt["git_commit"],
                "query_file_sha256": row["query_file_sha256"],
                "target_file_sha256": row["target_file_sha256"],
                "artifact_receipt": str(
                    Path(row["expected_artifact_root"]) / "attempt.json"
                ),
            }
        )
    return output


def quantile(values: Sequence[float], probability: float) -> float:
    require(values, "cannot calculate a quantile of an empty sample")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_median_ci(values: Sequence[float], seed_offset: int) -> tuple[float, float]:
    require(values, "cannot bootstrap an empty sample")
    generator = random.Random(BOOTSTRAP_SEED + seed_offset)
    estimates = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sample = [values[generator.randrange(len(values))] for _ in values]
        estimates.append(statistics.median(sample))
    return quantile(estimates, 0.025), quantile(estimates, 0.975)


def summary(values: Sequence[float], seed_offset: int) -> dict[str, object]:
    lower, upper = bootstrap_median_ci(values, seed_offset)
    return {
        "n": len(values),
        "median": statistics.median(values),
        "q1": quantile(values, 0.25),
        "q3": quantile(values, 0.75),
        "iqr": quantile(values, 0.75) - quantile(values, 0.25),
        "bootstrap_median_ci95": {"lower": lower, "upper": upper},
    }


def build_statistics(source: list[dict[str, object]]) -> dict[str, object]:
    profile_rows = [row for row in source if row["profile_mode"] == "profile_on"]
    control_rows = [row for row in source if row["profile_mode"] == "profile_off"]
    workloads: dict[str, object] = {}
    seed_offset = 0
    for spec in WORKLOAD_SPECS:
        workload_id = str(spec["workload_id"])
        observed = [row for row in profile_rows if row["workload_id"] == workload_id]
        controls = [row for row in control_rows if row["workload_id"] == workload_id]
        require(len(observed) == 5 and len(controls) == 5, f"observation count drift: {workload_id}")
        steady = [row for row in observed if row["cache_state"] == "steady_state"]
        require(len(steady) == 4, f"steady-state count drift: {workload_id}")
        metrics: dict[str, object] = {}
        for metric in (
            "outer_wall_seconds",
            *tuple(f"{stage}_seconds" for stage in STAGES),
            "p_strict_ssw",
            "p_backend_addressable",
            "maximum_speedup_infinite",
        ):
            values = [float(row[metric]) for row in steady]
            seed_offset += 1
            metrics[metric] = summary(values, seed_offset)
        overhead_ratios = []
        for observation in range(1, 6):
            profiled = next(row for row in observed if int(row["observation_id"]) == observation)
            control = next(row for row in controls if int(row["observation_id"]) == observation)
            overhead_ratios.append(
                float(profiled["outer_wall_seconds"]) / float(control["outer_wall_seconds"])
            )
        seed_offset += 1
        workloads[workload_id] = {
            "workload_class": spec["workload_class"],
            "claim_relevant": spec["claim_relevant"] == "1",
            "observations": {"cold_advisory": 1, "steady_state": 4},
            "steady_state": metrics,
            "instrumentation_overhead_ratio_all_pairs": summary(overhead_ratios, seed_offset),
            "output_digest_unique_count": len({str(row["output_digest"]) for row in observed + controls}),
        }
    return {
        "schema_version": 1,
        "method": {
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "central_estimator": "median",
            "conservative_p_definition": (
                "lower endpoint of the deterministic 95% percentile-bootstrap CI "
                "for the steady-state median p_backend_addressable"
            ),
            "cold_definition": "per-attempt POSIX_FADV_DONTNEED advisory before process launch",
            "steady_definition": "subsequent independent process observations without cache-drop advice",
        },
        "source_data_sha256": sha256_bytes(tsv_bytes(SOURCE_FIELDS, source)),
        "workloads": workloads,
    }


def build_decision(stats: dict[str, object]) -> dict[str, object]:
    workloads = stats["workloads"]
    claim_ids = [
        str(spec["workload_id"])
        for spec in WORKLOAD_SPECS
        if spec["claim_relevant"] == "1"
    ]
    bounds = {
        workload_id: float(
            workloads[workload_id]["steady_state"]["p_backend_addressable"]
            ["bootstrap_median_ci95"]["lower"]
        )
        for workload_id in claim_ids
    }
    conservative_p = min(bounds.values())
    maximum, required = amdahl_projection(conservative_p)
    if conservative_p <= 0.90:
        b3_track = "closed_amdahl"
        gate = "closed_amdahl"
        reason = "conservative_backend_fraction_at_or_below_0.90"
    elif maximum < 12.0:
        b3_track = "open_low_headroom"
        gate = "open_low_headroom"
        reason = "theoretical_maximum_between_10_and_12"
    else:
        b3_track = "open_amdahl"
        gate = "open_amdahl"
        reason = "theoretical_maximum_at_least_12"
    return {
        "schema_version": 1,
        "phase": 1,
        "status": "pass",
        "target_end_to_end_speedup": TARGET_SPEEDUP,
        "b3_threshold_changed": False,
        "claim_relevant_workloads": claim_ids,
        "claim_relevant_conservative_p_by_workload": bounds,
        "conservative_p_backend_addressable": conservative_p,
        "maximum_speedup_infinite": maximum if math.isfinite(maximum) else None,
        "required_backend_speedup": required,
        "amdahl_gate": gate,
        "bioinformatics_b3_track": b3_track,
        "engineering_track": "active",
        "reason": reason,
        "fresh_holdout_consumed": False,
        "authority_output_changed": False,
        "performance_gate_passed": False,
        "cuda_dp_kernel_authorized_by_phase1": False,
        "statistics_sha256": sha256_bytes(json_bytes(stats)),
    }


def render_decision_markdown(decision: dict[str, object]) -> bytes:
    maximum = decision["maximum_speedup_infinite"]
    maximum_text = "infinite" if maximum is None else f"{maximum:.9f}x"
    required = decision["required_backend_speedup"]
    required_text = "unreachable" if required is None else f"{required:.9f}x"
    lines = [
        "# Phase 1 CPU Profile And Amdahl Decision",
        "",
        f"Status: `{decision['status']}`",
        "",
        f"Bioinformatics B3 track: `{decision['bioinformatics_b3_track']}`.",
        f"Engineering track: `{decision['engineering_track']}`.",
        "",
        "The original end-to-end target remains 10x. The gate uses the lower 95%",
        "bootstrap bound of the steady-state median addressable fraction for each",
        "claim-relevant large workload, then takes the less favorable workload.",
        "",
        f"Conservative addressable fraction: `{decision['conservative_p_backend_addressable']:.9f}`.",
        f"Infinite-backend Amdahl ceiling: `{maximum_text}`.",
        f"Backend speedup required for 10x end-to-end: `{required_text}`.",
        f"Decision reason: `{decision['reason']}`.",
        "",
        "Profiling used only previously consumed development/regression inputs. The",
        "default-off and instrumented runs produced byte-identical authority artifacts",
        "for every paired observation. This decision does not establish performance or",
        "correctness for a future GPU backend and does not authorize a CUDA DP kernel",
        "before the later phase gates.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def analyze(rows: list[dict[str, str]], artifact_root: Path) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    receipts = receipts_from_artifacts(rows, artifact_root)
    source = source_rows(rows, receipts)
    stats = build_statistics(source)
    decision = build_decision(stats)
    return source, stats, decision


def write_analysis(
    rows: list[dict[str, str]], artifact_root: Path, *, execution_receipt: dict[str, object] | None
) -> None:
    source, stats, decision = analyze(rows, artifact_root)
    atomic_write(SOURCE_DATA, tsv_bytes(SOURCE_FIELDS, source))
    atomic_write(STATISTICS, json_bytes(stats))
    atomic_write(DECISION_JSON, json_bytes(decision))
    atomic_write(DECISION_MD, render_decision_markdown(decision))
    if execution_receipt is not None:
        execution_receipt.update(
            {
                "source_data_sha256": sha256_file(SOURCE_DATA),
                "statistics_sha256": sha256_file(STATISTICS),
                "decision_sha256": sha256_file(DECISION_JSON),
                "attempts_complete": len(source),
                "paired_outputs_equal": all(int(row["paired_output_equal"]) == 1 for row in source),
                "status": "complete",
            }
        )
        atomic_write(EXECUTION_RECEIPT, json_bytes(execution_receipt))


def execute(binary: Path, artifact_root: Path) -> None:
    rows = validate_plan()
    require(binary.is_file() and not binary.is_symlink() and os.access(binary, os.X_OK), "invalid binary")
    require(not artifact_root.exists(), f"artifact root already exists: {artifact_root}")
    require(git_output("status", "--porcelain") == "", "formal profiling requires a clean worktree")
    commit = git_output("rev-parse", "HEAD")
    artifact_root.mkdir(parents=True)
    execution_receipt: dict[str, object] = {
        "schema_version": 1,
        "status": "running",
        "start_utc": utc_now(),
        "git_commit": commit,
        "binary_path": str(binary),
        "binary_sha256": sha256_file(binary),
        "plan_sha256": sha256_file(PLAN),
        "runner_sha256": sha256_file(Path(__file__)),
        "retry_policy": "none",
        "attempt_count": len(rows),
    }
    for row in rows:
        receipt = run_attempt(row, binary=binary, artifact_root=artifact_root, git_commit=commit)
        require(receipt["status"] == "complete", f"attempt failed: {row['attempt_id']}")
    execution_receipt["end_utc"] = utc_now()
    write_analysis(rows, artifact_root, execution_receipt=execution_receipt)


def check_results(artifact_root: Path) -> None:
    rows = validate_plan()
    expected_source, expected_stats, expected_decision = analyze(rows, artifact_root)
    require(SOURCE_DATA.read_bytes() == tsv_bytes(SOURCE_FIELDS, expected_source), "source data drift")
    require(STATISTICS.read_bytes() == json_bytes(expected_stats), "statistics drift")
    require(DECISION_JSON.read_bytes() == json_bytes(expected_decision), "decision drift")
    require(DECISION_MD.read_bytes() == render_decision_markdown(expected_decision), "decision report drift")
    receipt = json.loads(EXECUTION_RECEIPT.read_text(encoding="utf-8"))
    require(receipt["status"] == "complete", "execution receipt is incomplete")
    require(receipt["attempts_complete"] == 50, "attempt receipt count drift")
    require(receipt["paired_outputs_equal"] is True, "authority output equality failed")
    require(receipt["plan_sha256"] == sha256_file(PLAN), "plan receipt drift")
    require(expected_decision["b3_threshold_changed"] is False, "B3 threshold changed")
    require(expected_decision["engineering_track"] == "active", "engineering track closed")
    for row in expected_source:
        if row["profile_mode"] == "profile_on":
            require(int(row["profile_stack_errors"]) == 0, "profile stack error")
            require(int(row["profile_active_depth"]) == 0, "profile stage leaked")
            require(int(row["paired_output_equal"]) == 1, "profile output mismatch")


def smoke(binary: Path) -> None:
    rows = expected_plan_rows()[:2]
    with tempfile.TemporaryDirectory(prefix="ssw-cuda-phase1-smoke-") as temporary:
        root = Path(temporary)
        receipts = [
            run_attempt(
                {key: str(value) for key, value in row.items()},
                binary=binary,
                artifact_root=root,
                git_commit=git_output("rev-parse", "HEAD"),
            )
            for row in rows
        ]
        require(all(receipt["status"] == "complete" for receipt in receipts), "smoke failed")
        require(receipts[0]["output_digest"] == receipts[1]["output_digest"], "smoke output drift")
        metrics = receipts[1]["profile_metrics"]
        require(int(metrics["stack_errors"]) == 0, "smoke profile stack error")
        require(int(metrics["active_depth"]) == 0, "smoke profile stack leak")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--render-plan", action="store_true")
    action.add_argument("--check-plan", action="store_true")
    action.add_argument("--smoke", action="store_true")
    action.add_argument("--execute", action="store_true")
    action.add_argument("--analyze-only", action="store_true")
    action.add_argument("--check-results", action="store_true")
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    if args.render_plan:
        sys.stdout.buffer.write(tsv_bytes(PLAN_FIELDS, expected_plan_rows()))
    elif args.check_plan:
        validate_plan()
        print("SSW-CUDA Phase 1 attempt plan OK")
    elif args.smoke:
        require(args.binary is not None, "--smoke requires --binary")
        smoke(args.binary.resolve())
        print("SSW-CUDA Phase 1 profiler smoke OK")
    elif args.execute:
        require(args.binary is not None, "--execute requires --binary")
        execute(args.binary.resolve(), artifact_root)
        print("SSW-CUDA Phase 1 formal profile complete")
    elif args.analyze_only:
        rows = validate_plan()
        write_analysis(rows, artifact_root, execution_receipt=None)
        print("SSW-CUDA Phase 1 analysis rebuilt")
    else:
        check_results(artifact_root)
        print("SSW-CUDA Phase 1 results OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
