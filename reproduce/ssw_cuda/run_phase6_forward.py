#!/usr/bin/env python3
"""Plan, execute, and audit the Phase 6 exact forward-endpoint regression."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
PHASE5_RUNNER = ROOT / "reproduce/ssw_cuda/run_phase5_preselect.py"
HOLDOUT_MANIFEST = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
PLAN = ROOT / "paper/ssw_cuda/forward_endpoint_attempt_plan.tsv"
DESIGN = ROOT / "paper/ssw_cuda/forward_endpoint_design.md"
RESULTS = ROOT / "paper/ssw_cuda/forward_endpoint_regression.tsv"
RECEIPT = ROOT / "paper/ssw_cuda/forward_endpoint_receipt.json"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/ssw-cuda-v1/forward"
FORMAL_ROOT = ARTIFACT_ROOT / "formal-v1"
DEFAULT_DRIVER = ARTIFACT_ROOT / "build/ssw_cuda_forward_driver"
SCHEMA_VERSION = "1"
PHASE5_HEAD = "2cf9e7c9d03e2905cb1d171ed4e2056e727b87c8"
MAXIMUM_TOTAL_DP_CELLS = 1 << 31
GPU_BUDGET_SECONDS = 24 * 3600

PLAN_FIELDS = (
    "attempt_id",
    "execution_stage",
    "backend",
    "scope",
    "unique_case_count",
    "repeat_id",
    "order",
    "device",
    "gpu_assignment",
    "contract_layers",
    "maximum_total_dp_cells",
    "timeout_seconds",
    "retry_policy",
    "claim_role",
    "formal_source_data",
    "runner_commit_policy",
    "expected_status",
    "artifact_root",
)

RESULT_FIELDS = (
    "attempt_id",
    "execution_stage",
    "repeat_id",
    "device",
    "case_id",
    "corpus_partition",
    "case_class",
    "execution_tier",
    "source_kind",
    "query_sha256",
    "reference_sha256",
    "pair_digest",
    "query_length",
    "reference_length",
    "expected_status",
    "observed_status",
    "numeric_path",
    "cpu_score1",
    "reducer_score1",
    "gpu_score1",
    "cpu_ref_end1",
    "reducer_ref_end1",
    "gpu_ref_end1",
    "cpu_read_end1",
    "gpu_read_end1",
    "cpu_score2",
    "reducer_score2",
    "gpu_score2",
    "cpu_ref_end2",
    "reducer_ref_end2",
    "gpu_ref_end2",
    "reducer_equal",
    "gpu_equal",
    "column_equal",
    "cpu_column_digest",
    "gpu_column_digest",
    "cpu_endpoint_digest",
    "reducer_endpoint_digest",
    "gpu_endpoint_digest",
    "cpu_endpoint_calls",
    "driver_returncode",
    "formal_contract",
)

ENDPOINT_CALL_DEFINITIONS = (
    (
        "hq10_ht02",
        "known-hq10-ht02-forward-call",
        "hq10_mismatch_call.json",
        0,
        1,
        5,
    ),
    (
        "hq11_ht02",
        "known-hq11-ht02-forward-call",
        "hq11_mismatch_call.json",
        1,
        -1,
        12,
    ),
)

FORWARD_FAIL_PROBES = (
    "empty_query",
    "empty_reference",
    "invalid_base",
    "query_too_long",
    "capacity",
    "out_of_memory",
    "contract_drift",
    "device_out_of_range",
)

REDUCER_FAIL_PROBES = (
    "empty_batch",
    "empty_columns",
    "invalid_numeric_path",
    "invalid_mask",
    "invalid_column_score",
)


class Phase6Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenEndpoint:
    score1: int
    ref_end1: int
    read_end1: int
    score2: int
    ref_end2: int
    numeric_path: str


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    wall_seconds: float


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase6Error(message)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P5 = load_module("ssw_cuda_phase6_phase5", PHASE5_RUNNER)
Case = P5.Case


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_fasta(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe FASTA: {path}")
    sequence = b"".join(
        line.strip()
        for line in path.read_bytes().splitlines()
        if line and not line.startswith(b">")
    )
    require(sequence, f"empty FASTA sequence: {path}")
    return sequence


def endpoint_call_cases() -> tuple[list[Any], dict[str, FrozenEndpoint]]:
    holdout = {row["workload_id"]: row for row in read_tsv(HOLDOUT_MANIFEST)}
    cases: list[Any] = []
    expected: dict[str, FrozenEndpoint] = {}
    for workload_id, case_id, fixture_name, strand, para, rule in ENDPOINT_CALL_DEFINITIONS:
        source = holdout[workload_id]
        query = read_fasta(ROOT / source["query_path"])
        target = read_fasta(ROOT / source["target_path"])
        require(sha256_bytes(query) == source["query_sequence_sha256"], f"{case_id}: query drift")
        require(sha256_bytes(target) == source["target_sequence_sha256"], f"{case_id}: target drift")
        fixture = json.loads(
            (ROOT / "tests/ssw_cuda/fixtures" / fixture_name).read_text(encoding="utf-8")
        )
        attempt = fixture["attempt"]
        start = int(attempt["target_start"])
        length = int(attempt["cutlength"])
        reference = target[start : start + length]
        require(len(reference) == length, f"{case_id}: target window truncated")
        pair_digest = sha256_bytes(
            b"ssw-cuda-phase6-endpoint-call-v1\0"
            + query
            + b"\0"
            + reference
            + b"\0"
            + f"{strand}:{para}:{rule}".encode("ascii")
        )
        cases.append(
            Case(
                case_id=case_id,
                corpus_partition="historical_regression",
                case_class="known_endpoint_call",
                execution_tier="compact",
                source_kind="historical_call_fixture",
                query=query,
                reference=reference,
                query_sha256=sha256_bytes(query),
                reference_sha256=sha256_bytes(reference),
                pair_digest=pair_digest,
                threshold=int(attempt["prealign_score"]),
                transform_strand=strand,
                transform_para=para,
                transform_rule=rule,
            )
        )
        endpoint = fixture["forward_endpoint"]
        expected[case_id] = FrozenEndpoint(
            score1=int(endpoint["score1"]),
            ref_end1=int(endpoint["ref_end1"]),
            read_end1=int(endpoint["read_end1"]),
            score2=int(endpoint["score2"]),
            ref_end2=int(endpoint["ref_end2"]),
            numeric_path=fixture["final_numeric_path"],
        )
    return cases, expected


def primary_cases() -> tuple[list[Any], dict[str, FrozenEndpoint]]:
    base = [case for case in P5.all_cases() if case.expected_status == "ok"]
    calls, expected = endpoint_call_cases()
    cases = base + calls
    require(len(cases) == 625, "Phase 6 primary case count drift")
    require(len({case.case_id for case in cases}) == 625, "duplicate Phase 6 primary case")
    return cases, expected


def case_groups() -> tuple[dict[str, list[Any]], dict[str, FrozenEndpoint]]:
    cases, expected = primary_cases()
    by_id = {case.case_id: case for case in cases}
    determinism_ids = tuple(P5.DETERMINISM_CASE_IDS) + tuple(expected)
    groups = {
        "tiny_exhaustive": [case for case in cases if case.corpus_partition == "tiny_exhaustive"],
        "adversarial_compact": [
            case
            for case in cases
            if case.corpus_partition == "adversarial" and case.execution_tier == "compact"
        ],
        "compact_fuzz": [case for case in cases if case.case_id.startswith("fuzz-compact-")],
        "known_forward": [
            case
            for case in cases
            if case.source_kind in {"historical_annotation", "historical_call_fixture"}
        ],
        "large": [case for case in cases if case.execution_tier == "large"],
        "determinism": [by_id[case_id] for case_id in determinism_ids],
        "unsupported": [case for case in P5.all_cases() if case.expected_status == "fail_closed"],
    }
    observed = {name: len(values) for name, values in groups.items()}
    required = {
        "tiny_exhaustive": 196,
        "adversarial_compact": 30,
        "compact_fuzz": 128,
        "known_forward": 4,
        "large": 267,
        "determinism": 18,
        "unsupported": 4,
    }
    require(observed == required, f"Phase 6 group count drift: {observed}")
    return groups, expected


def input_tsv(cases: Sequence[Any]) -> bytes:
    fields = (
        "case_id",
        "threshold",
        "query_hex",
        "reference_hex",
        "transform_enabled",
        "transform_strand",
        "transform_para",
        "transform_rule",
    )
    rows = []
    for case in cases:
        transformed = case.transform_rule is not None
        rows.append(
            {
                "case_id": case.case_id,
                "threshold": case.threshold,
                "query_hex": case.query.hex(),
                "reference_hex": case.reference.hex(),
                "transform_enabled": int(transformed),
                "transform_strand": case.transform_strand if transformed else 0,
                "transform_para": case.transform_para if transformed else 0,
                "transform_rule": case.transform_rule if transformed else 0,
            }
        )
    return tsv_bytes(fields, rows)


def frozen_column_input_tsv() -> bytes:
    fields = (
        "case_id",
        "numeric_path",
        "mask_length",
        "columns",
        "score1",
        "ref_end1",
        "score2",
        "ref_end2",
    )
    rows = []
    for _, case_id, fixture_name, _, _, _ in ENDPOINT_CALL_DEFINITIONS:
        fixture = json.loads(
            (ROOT / "tests/ssw_cuda/fixtures" / fixture_name).read_text(encoding="utf-8")
        )
        passes = [item for item in fixture["dp_passes"] if item["stage"] == "forward"]
        require(len(passes) == 1, f"{case_id}: frozen forward vector cardinality drift")
        forward = passes[0]
        endpoint = fixture["forward_endpoint"]
        require(len(forward["columns"]) == int(forward["column_count"]),
                f"{case_id}: frozen forward column count drift")
        rows.append(
            {
                "case_id": case_id,
                "numeric_path": forward["numeric_path"],
                "mask_length": 15,
                "columns": ",".join(str(value) for value in forward["columns"]),
                "score1": endpoint["score1"],
                "ref_end1": endpoint["ref_end1"],
                "score2": endpoint["score2"],
                "ref_end2": endpoint["ref_end2"],
            }
        )
    require(len(rows) == 2, "frozen CPU forward vector count drift")
    return tsv_bytes(fields, rows)


def plan_rows() -> list[dict[str, Any]]:
    groups, _ = case_groups()
    rows: list[dict[str, Any]] = []

    def add(
        attempt_id: str,
        stage: str,
        scope: str,
        count: int,
        repeat_id: str,
        device: int,
        timeout: int,
        expected_status: str = "complete",
    ) -> None:
        rows.append(
            {
                "attempt_id": attempt_id,
                "execution_stage": stage,
                "backend": "ssw_cuda_exact_forward_v1",
                "scope": scope,
                "unique_case_count": count,
                "repeat_id": repeat_id,
                "order": len(rows) + 1,
                "device": device,
                "gpu_assignment": f"logical_{device}_physical_{device}",
                "contract_layers": "L1,L3",
                "maximum_total_dp_cells": MAXIMUM_TOTAL_DP_CELLS,
                "timeout_seconds": timeout,
                "retry_policy": "none",
                "claim_role": "regression_only",
                "formal_source_data": 1,
                "runner_commit_policy": "committed_HEAD_clean_at_start",
                "expected_status": expected_status,
                "artifact_root": f".paper-artifacts/ssw-cuda-v1/forward/formal-v1/{attempt_id}",
            }
        )

    for attempt_id, scope, timeout in (
        ("p6-primary-tiny", "tiny_exhaustive", 300),
        ("p6-primary-adversarial", "adversarial_compact", 300),
        ("p6-primary-compact-fuzz", "compact_fuzz", 300),
        ("p6-primary-known", "known_forward", 300),
        ("p6-primary-large", "large", 1800),
    ):
        add(attempt_id, "primary", scope, len(groups[scope]), "0", 0, timeout)
    add(
        "p6-cpu-vector-reducer",
        "cpu_forward_vector_reducer",
        "frozen_hq10_hq11_forward_columns",
        2,
        "0",
        0,
        60,
    )
    for repeat in range(10):
        add(
            f"p6-determinism-r{repeat:02d}",
            "determinism",
            "fixed_18_case_subset",
            len(groups["determinism"]),
            str(repeat),
            0,
            300,
        )
    for device in (0, 1):
        add(
            f"p6-dual-gpu{device}",
            "same_model_dual_gpu",
            "fixed_18_case_subset",
            len(groups["determinism"]),
            "0",
            device,
            300,
        )
    for probe in FORWARD_FAIL_PROBES:
        add(f"p6-forward-fail-{probe}", "forward_fail_closed", probe, 1, "0", 0, 60, "fail_closed")
    for probe in REDUCER_FAIL_PROBES:
        add(f"p6-reducer-fail-{probe}", "reducer_fail_closed", probe, 1, "0", 0, 60, "fail_closed")
    require(len(rows) == 31, "Phase 6 attempt-plan row count drift")
    return rows


def write_plan() -> None:
    PLAN.write_bytes(tsv_bytes(PLAN_FIELDS, plan_rows()))


def validate_plan() -> list[dict[str, str]]:
    expected = tsv_bytes(PLAN_FIELDS, plan_rows())
    require(PLAN.read_bytes() == expected, "Phase 6 attempt plan is not reproducible")
    rows = read_tsv(PLAN)
    require(len(rows) == 31, "Phase 6 attempt plan row count drift")
    require(all(row["retry_policy"] == "none" for row in rows), "retry policy drift")
    supported = {"primary", "determinism", "same_model_dual_gpu"}
    task_count = sum(int(row["unique_case_count"]) for row in rows if row["execution_stage"] in supported)
    require(task_count == 841, "Phase 6 supported GPU task-execution count drift")
    require(sum(int(row["unique_case_count"]) for row in rows if row["execution_stage"] == "primary") == 625,
            "Phase 6 primary task count drift")
    require(len([row for row in rows if row["execution_stage"] == "determinism"]) == 10,
            "Phase 6 determinism repeat count drift")
    require(len([row for row in rows if row["execution_stage"] == "same_model_dual_gpu"]) == 2,
            "Phase 6 dual-GPU count drift")
    require(sum(int(row["unique_case_count"]) for row in rows
                if row["execution_stage"] == "cpu_forward_vector_reducer") == 2,
            "Phase 6 frozen CPU-vector reducer count drift")
    return rows


def parse_driver_rows(stdout: str) -> list[dict[str, str]]:
    lines = [line for line in stdout.splitlines() if line]
    require(lines and lines[0].startswith("case_id\t"), "forward driver result header missing")
    return list(csv.DictReader(io.StringIO("\n".join(lines) + "\n"), delimiter="\t"))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_output(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def command_output(command: Sequence[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def run_command(command: Sequence[str], timeout_seconds: int, environment: dict[str, str]) -> CommandResult:
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        returncode = process.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        returncode = 124
    return CommandResult(returncode, stdout, stderr, timed_out, time.monotonic() - started)


def write_artifact_manifest(attempt_root: Path, names: Sequence[str]) -> str:
    rows = []
    for name in names:
        path = attempt_root / name
        require(path.is_file() and not path.is_symlink(), f"missing attempt artifact: {path}")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = tsv_bytes(("path", "bytes", "sha256"), rows)
    (attempt_root / "artifact_manifest.tsv").write_bytes(payload)
    digest = sha256_bytes(payload)
    (attempt_root / "artifact_manifest.sha256").write_text(
        f"{digest}  artifact_manifest.tsv\n", encoding="ascii"
    )
    return digest


def blank_result(plan: dict[str, str], case_id: str, observed_status: str, returncode: int) -> dict[str, Any]:
    row = {field: "" for field in RESULT_FIELDS}
    row.update(
        {
            "attempt_id": plan["attempt_id"],
            "execution_stage": plan["execution_stage"],
            "repeat_id": plan["repeat_id"],
            "device": plan["device"],
            "case_id": case_id,
            "expected_status": plan["expected_status"],
            "observed_status": observed_status,
            "driver_returncode": returncode,
            "formal_contract": "fail_closed" if observed_status == "fail_closed" else "technical_failure",
        }
    )
    return row


def supported_result(
    plan: dict[str, str], case: Any, observed_status: str, returncode: int, driver: dict[str, str]
) -> dict[str, Any]:
    return {
        "attempt_id": plan["attempt_id"],
        "execution_stage": plan["execution_stage"],
        "repeat_id": plan["repeat_id"],
        "device": plan["device"],
        "case_id": case.case_id,
        "corpus_partition": case.corpus_partition,
        "case_class": case.case_class,
        "execution_tier": case.execution_tier,
        "source_kind": case.source_kind,
        "query_sha256": case.query_sha256,
        "reference_sha256": case.reference_sha256,
        "pair_digest": case.pair_digest,
        "query_length": len(case.query),
        "reference_length": len(case.reference),
        "expected_status": plan["expected_status"],
        "observed_status": observed_status,
        "numeric_path": driver["numeric_path"],
        "cpu_score1": driver["cpu_score1"],
        "reducer_score1": driver["reducer_score1"],
        "gpu_score1": driver["gpu_score1"],
        "cpu_ref_end1": driver["cpu_ref_end1"],
        "reducer_ref_end1": driver["reducer_ref_end1"],
        "gpu_ref_end1": driver["gpu_ref_end1"],
        "cpu_read_end1": driver["cpu_read_end1"],
        "gpu_read_end1": driver["gpu_read_end1"],
        "cpu_score2": driver["cpu_score2"],
        "reducer_score2": driver["reducer_score2"],
        "gpu_score2": driver["gpu_score2"],
        "cpu_ref_end2": driver["cpu_ref_end2"],
        "reducer_ref_end2": driver["reducer_ref_end2"],
        "gpu_ref_end2": driver["gpu_ref_end2"],
        "reducer_equal": driver["reducer_equal"],
        "gpu_equal": driver["gpu_equal"],
        "column_equal": driver["column_equal"],
        "cpu_column_digest": driver["cpu_column_digest"],
        "gpu_column_digest": driver["gpu_column_digest"],
        "cpu_endpoint_digest": driver["cpu_endpoint_digest"],
        "reducer_endpoint_digest": driver["reducer_endpoint_digest"],
        "gpu_endpoint_digest": driver["gpu_endpoint_digest"],
        "cpu_endpoint_calls": driver["cpu_endpoint_calls"],
        "driver_returncode": returncode,
        "formal_contract": "L3_exact" if driver["reducer_equal"] == driver["gpu_equal"] == "1" else "mismatch",
    }


def column_reducer_result(
    plan: dict[str, str], observed_status: str, returncode: int, driver: dict[str, str]
) -> dict[str, Any]:
    row = blank_result(plan, driver["case_id"], observed_status, returncode)
    row.update(
        {
            "numeric_path": driver["numeric_path"],
            "cpu_score1": driver["expected_score1"],
            "reducer_score1": driver["reducer_score1"],
            "cpu_ref_end1": driver["expected_ref_end1"],
            "reducer_ref_end1": driver["reducer_ref_end1"],
            "cpu_score2": driver["expected_score2"],
            "reducer_score2": driver["reducer_score2"],
            "cpu_ref_end2": driver["expected_ref_end2"],
            "reducer_ref_end2": driver["reducer_ref_end2"],
            "reducer_equal": driver["reducer_equal"],
            "cpu_endpoint_calls": driver["cpu_endpoint_calls"],
            "formal_contract": "L3_cpu_vector_reducer_exact"
            if driver["reducer_equal"] == "1" else "mismatch",
        }
    )
    return row


def execute_attempt(
    plan: dict[str, str],
    cases: Sequence[Any] | None,
    driver: Path,
    source_commit: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    attempt_root = ROOT / plan["artifact_root"]
    require(not attempt_root.exists(), f"attempt artifact root already exists: {attempt_root}")
    attempt_root.mkdir(parents=True)
    stdout_path = attempt_root / "stdout.tsv"
    stderr_path = attempt_root / "stderr.log"
    resource_path = attempt_root / "resource.log"
    command = ["/usr/bin/time", "-v", "-o", str(resource_path), str(driver)]
    artifact_names = ["stdout.tsv", "stderr.log", "resource.log", "attempt.json"]
    if plan["execution_stage"] == "cpu_forward_vector_reducer":
        input_path = attempt_root / "column-input.tsv"
        input_path.write_bytes(frozen_column_input_tsv())
        command += ["--column-input", str(input_path), "--device", plan["device"]]
        artifact_names.insert(0, "column-input.tsv")
    elif cases is not None:
        input_path = attempt_root / "input.tsv"
        input_path.write_bytes(input_tsv(cases))
        command += [
            "--input",
            str(input_path),
            "--device",
            plan["device"],
            "--maximum-cells",
            plan["maximum_total_dp_cells"],
        ]
        artifact_names.insert(0, "input.tsv")
    elif plan["execution_stage"] == "forward_fail_closed":
        command += ["--invalid-forward-probe", plan["scope"], "--device", plan["device"]]
    elif plan["execution_stage"] == "reducer_fail_closed":
        command += ["--invalid-reducer-probe", plan["scope"], "--device", plan["device"]]
    else:
        raise Phase6Error(f"{plan['attempt_id']}: missing case input")

    environment_values = {
        "CUDA_VISIBLE_DEVICES": "0,1",
        "FASIM_TRANSFERSTRING_TABLE": "0",
        "FASIM_SSW_ORACLE_TRACE": "0",
    }
    environment = {**os.environ, **environment_values}
    started_utc = utc_now()
    completed = run_command(command, int(plan["timeout_seconds"]), environment)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    if not resource_path.exists():
        resource_path.write_text("resource log unavailable after timeout\n", encoding="utf-8")

    expected_complete = plan["expected_status"] == "complete"
    if completed.timed_out:
        observed_status = "timeout"
    elif expected_complete and completed.returncode in {0, 1}:
        observed_status = "complete" if completed.returncode == 0 else "complete_with_mismatch"
    elif not expected_complete and completed.returncode == 0:
        observed_status = "fail_closed"
    else:
        observed_status = "technical_failure"

    results: list[dict[str, Any]] = []
    if expected_complete and completed.returncode in {0, 1}:
        parsed = parse_driver_rows(completed.stdout)
        if plan["execution_stage"] == "cpu_forward_vector_reducer":
            require(len(parsed) == 2, "frozen CPU-vector reducer result count drift")
            results = [
                column_reducer_result(plan, observed_status, completed.returncode, row)
                for row in parsed
            ]
        else:
            require(cases is not None and len(parsed) == len(cases), f"{plan['attempt_id']}: result count drift")
            by_id = {case.case_id: case for case in cases}
            require(set(by_id) == {row["case_id"] for row in parsed}, f"{plan['attempt_id']}: case identity drift")
            results = [
                supported_result(plan, by_id[row["case_id"]], observed_status, completed.returncode, row)
                for row in parsed
            ]
    elif not expected_complete:
        case_id = cases[0].case_id if cases is not None else plan["scope"]
        results = [blank_result(plan, case_id, observed_status, completed.returncode)]
        if cases is not None:
            case = cases[0]
            results[0].update(
                {
                    "corpus_partition": case.corpus_partition,
                    "case_class": case.case_class,
                    "execution_tier": case.execution_tier,
                    "source_kind": case.source_kind,
                    "query_sha256": case.query_sha256,
                    "reference_sha256": case.reference_sha256,
                    "pair_digest": case.pair_digest,
                    "query_length": len(case.query),
                    "reference_length": len(case.reference),
                }
            )
    else:
        results = [blank_result(plan, plan["scope"], observed_status, completed.returncode)]

    attempt = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": plan["attempt_id"],
        "phase": 6,
        "backend": plan["backend"],
        "execution_stage": plan["execution_stage"],
        "scope": plan["scope"],
        "case_count": int(plan["unique_case_count"]),
        "source_commit": source_commit,
        "binary_sha256": sha256_file(driver),
        "input_sha256": (
            sha256_file(attempt_root / "column-input.tsv")
            if plan["execution_stage"] == "cpu_forward_vector_reducer"
            else (sha256_file(attempt_root / "input.tsv") if cases is not None else None)
        ),
        "command_argv": command,
        "environment": environment_values,
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "wall_seconds": completed.wall_seconds,
        "returncode": completed.returncode,
        "status": observed_status,
        "timeout": completed.timed_out,
        "retry_count": 0,
        "fallback_used": False,
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "resource_path": str(resource_path.relative_to(ROOT)),
    }
    (attempt_root / "attempt.json").write_bytes(json_bytes(attempt))
    attempt["artifact_manifest_sha256"] = write_artifact_manifest(attempt_root, artifact_names)
    return results, attempt


def rows_digest(rows: Sequence[dict[str, Any]]) -> str:
    payload = "\n".join(
        f"{row['case_id']}\t{row['gpu_endpoint_digest']}\t{row['gpu_column_digest']}"
        for row in sorted(rows, key=lambda value: value["case_id"])
    ).encode("utf-8")
    return sha256_bytes(payload)


def verify_frozen_endpoints(rows: Sequence[dict[str, Any]], expected: dict[str, FrozenEndpoint]) -> None:
    by_id = {row["case_id"]: row for row in rows}
    for case_id, endpoint in expected.items():
        require(case_id in by_id, f"missing frozen endpoint row: {case_id}")
        row = by_id[case_id]
        fields = {
            "score1": int(row["cpu_score1"]),
            "ref_end1": int(row["cpu_ref_end1"]),
            "read_end1": int(row["cpu_read_end1"]),
            "score2": int(row["cpu_score2"]),
            "ref_end2": int(row["cpu_ref_end2"]),
            "numeric_path": row["numeric_path"],
        }
        require(fields == endpoint.__dict__, f"{case_id}: frozen CPU endpoint drift: {fields}")
        require(row["gpu_equal"] == "1", f"{case_id}: GPU endpoint mismatch")


def run_formal(driver: Path) -> None:
    plan = validate_plan()
    groups, expected = case_groups()
    require(driver.is_file() and not driver.is_symlink() and os.access(driver, os.X_OK),
            f"missing executable Phase 6 driver: {driver}")
    require(not FORMAL_ROOT.exists(), f"formal artifact root already exists: {FORMAL_ROOT}")
    require(not RESULTS.exists() and not RECEIPT.exists(), "Phase 6 formal results already exist")
    require(git_output("status", "--porcelain=v1") == "", "Phase 6 formal run requires a clean worktree")
    source_commit = git_output("rev-parse", "HEAD")
    require(
        subprocess.run(["git", "merge-base", "--is-ancestor", PHASE5_HEAD, source_commit], cwd=ROOT).returncode == 0,
        "Phase 6 implementation is not descended from frozen Phase 5",
    )
    for relative in (
        "Makefile",
        "fasim/ssw_cuda/ssw_cuda_api.h",
        "fasim/ssw_cuda/ssw_cuda_forward.cu",
        "fasim/ssw_cuda/ssw_cuda_striped.cuh",
        "paper/ssw_cuda/forward_endpoint_attempt_plan.tsv",
        "paper/ssw_cuda/forward_endpoint_design.md",
        "reproduce/ssw_cuda/run_phase6_forward.py",
        "scripts/check_ssw_cuda_phase6.sh",
        "tests/ssw_cuda/ssw_cuda_forward_driver.cpp",
        "tests/ssw_cuda/test_forward_endpoint.py",
    ):
        require(
            subprocess.run(["git", "cat-file", "-e", f"{source_commit}:{relative}"], cwd=ROOT).returncode == 0,
            f"formal Phase 6 dependency was not committed: {relative}",
        )

    all_results: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for row in plan:
        stage = row["execution_stage"]
        cases: Sequence[Any] | None
        if stage == "primary":
            cases = groups[row["scope"]]
        elif stage in {"determinism", "same_model_dual_gpu"}:
            cases = groups["determinism"]
        else:
            cases = None
        result_rows, attempt = execute_attempt(row, cases, driver, source_commit)
        all_results.extend(result_rows)
        attempts.append(attempt)

    result_payload = tsv_bytes(RESULT_FIELDS, all_results)
    RESULTS.write_bytes(result_payload)
    primary = [row for row in all_results if row["execution_stage"] == "primary"]
    supported = [
        row
        for row in all_results
        if row["execution_stage"] in {"primary", "determinism", "same_model_dual_gpu"}
    ]
    cpu_vector_reducer = [
        row for row in all_results if row["execution_stage"] == "cpu_forward_vector_reducer"
    ]
    verify_frozen_endpoints(primary, expected)
    repeat_digests = [
        rows_digest([row for row in all_results if row["attempt_id"] == f"p6-determinism-r{repeat:02d}"])
        for repeat in range(10)
    ]
    dual_digests = [
        rows_digest([row for row in all_results if row["attempt_id"] == f"p6-dual-gpu{device}"])
        for device in (0, 1)
    ]
    expected_fail_closed = [row for row in all_results if row["expected_status"] == "fail_closed"]
    technical_failures = sum(
        1 for attempt in attempts if attempt["status"] in {"timeout", "technical_failure"}
    )
    mismatch_count = sum(row["gpu_equal"] != "1" for row in supported)
    reducer_mismatch_count = sum(row["reducer_equal"] != "1" for row in supported)
    prealign_forward_column_differences = sum(row["column_equal"] != "1" for row in supported)
    cpu_endpoint_calls = sum(int(row["cpu_endpoint_calls"]) for row in supported)
    gpu_wall_seconds_upper_bound = sum(attempt["wall_seconds"] for attempt in attempts)
    gates_pass = (
        len(primary) == 625
        and len(supported) == 841
        and technical_failures == 0
        and mismatch_count == 0
        and reducer_mismatch_count == 0
        and len(cpu_vector_reducer) == 2
        and all(row["reducer_equal"] == "1" for row in cpu_vector_reducer)
        and all(row["cpu_endpoint_calls"] == "0" for row in cpu_vector_reducer)
        and cpu_endpoint_calls == 0
        and all(row["observed_status"] == "fail_closed" for row in expected_fail_closed)
        and len(set(repeat_digests)) == 1
        and len(set(dual_digests)) == 1
        and gpu_wall_seconds_upper_bound < GPU_BUDGET_SECONDS
    )
    gpu_inventory = command_output(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,compute_cap",
            "--format=csv,noheader,nounits",
        ]
    ).splitlines()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "phase": 6,
        "status": "pass" if gates_pass else "no_go",
        "source_commit": source_commit,
        "binary_sha256": sha256_file(driver),
        "plan_sha256": sha256_file(PLAN),
        "frozen_utc": utc_now(),
        "execution": {
            "attempt_count": len(attempts),
            "primary_gpu_tasks": len(primary),
            "total_supported_gpu_task_executions": len(supported),
            "frozen_cpu_vector_reducer_tasks": len(cpu_vector_reducer),
            "determinism_unique_cases": len(groups["determinism"]),
            "determinism_repeats": 10,
            "same_model_gpu_count": 2,
            "unsupported_frozen_cases": len(groups["unsupported"]),
            "forward_fail_closed_probes": len(FORWARD_FAIL_PROBES),
            "reducer_fail_closed_probes": len(REDUCER_FAIL_PROBES),
            "retry_count": 0,
            "fallback_count": 0,
            "mechanism_repair_iterations": 0,
            "gpu_budget_seconds": GPU_BUDGET_SECONDS,
            "gpu_wall_seconds_upper_bound": gpu_wall_seconds_upper_bound,
        },
        "results": {
            "result_rows": len(all_results),
            "primary_endpoint_mismatches": sum(row["gpu_equal"] != "1" for row in primary),
            "supported_endpoint_mismatches": mismatch_count,
            "supported_reducer_mismatches": reducer_mismatch_count,
            "frozen_cpu_vector_reducer_mismatches": sum(
                row["reducer_equal"] != "1" for row in cpu_vector_reducer
            ),
            "prealign_forward_column_differences_diagnostic": prealign_forward_column_differences,
            "technical_failures": technical_failures,
            "cpu_endpoint_calls": cpu_endpoint_calls,
            "fail_closed_expected": len(expected_fail_closed),
            "fail_closed_observed": sum(row["observed_status"] == "fail_closed" for row in expected_fail_closed),
            "repeat_digests": repeat_digests,
            "repeat_digest_stable": len(set(repeat_digests)) == 1,
            "dual_gpu_digests": dual_digests,
            "same_model_dual_gpu_equal": len(set(dual_digests)) == 1,
            "numeric_path_counts": {
                path: sum(row["numeric_path"] == path for row in primary)
                for path in sorted({row["numeric_path"] for row in primary})
            },
            "frozen_endpoint_calls": {
                case_id: endpoint.__dict__ for case_id, endpoint in expected.items()
            },
        },
        "artifacts": {
            "root": str(FORMAL_ROOT.relative_to(ROOT)),
            "forward_endpoint_regression_sha256": sha256_bytes(result_payload),
            "attempt_manifest_digests": {
                attempt["attempt_id"]: attempt["artifact_manifest_sha256"] for attempt in attempts
            },
        },
        "environment": {
            "gpu_inventory": gpu_inventory,
            "nvcc_version": command_output(["/usr/local/cuda/bin/nvcc", "--version"]),
            "cxx_version": command_output(["g++", "--version"]).splitlines()[0],
        },
        "claim_boundary": {
            "contract_established": "L3_forward_endpoint_regression",
            "promotion_evidence": False,
            "fresh_holdout_consumed": False,
            "cpu_oracle_replaced": False,
            "default_backend_changed": False,
            "bioinformatics_b3_track": "closed_amdahl",
            "l8_contract_status": "diagnostic_only",
        },
    }
    RECEIPT.write_bytes(json_bytes(receipt))


def validate_results(check_artifacts: bool = True) -> dict[str, Any]:
    validate_plan()
    require(RECEIPT.is_file() and not RECEIPT.is_symlink(), "Phase 6 receipt missing")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = read_tsv(RESULTS)
    require(receipt["status"] == "pass", "Phase 6 receipt is not pass")
    require(receipt["execution"]["primary_gpu_tasks"] == 625, "primary task count drift")
    require(receipt["execution"]["total_supported_gpu_task_executions"] == 841,
            "supported task count drift")
    require(receipt["execution"]["frozen_cpu_vector_reducer_tasks"] == 2,
            "frozen CPU-vector reducer task count drift")
    require(receipt["execution"]["retry_count"] == 0, "retry prohibition violated")
    require(receipt["execution"]["mechanism_repair_iterations"] <= 3, "repair budget exceeded")
    require(receipt["results"]["supported_endpoint_mismatches"] == 0, "L3 mismatch recorded")
    require(receipt["results"]["supported_reducer_mismatches"] == 0, "reducer mismatch recorded")
    require(receipt["results"]["frozen_cpu_vector_reducer_mismatches"] == 0,
            "frozen CPU-vector reducer mismatch recorded")
    require(receipt["results"]["technical_failures"] == 0, "technical failure recorded")
    require(receipt["results"]["cpu_endpoint_calls"] == 0, "CPU endpoint call recorded")
    require(receipt["results"]["repeat_digest_stable"], "repeat instability recorded")
    require(receipt["results"]["same_model_dual_gpu_equal"], "dual-GPU mismatch recorded")
    require(receipt["claim_boundary"]["bioinformatics_b3_track"] == "closed_amdahl", "B3 reopened")
    require(not receipt["claim_boundary"]["fresh_holdout_consumed"], "Phase 6 consumed fresh holdout")
    require(sha256_file(RESULTS) == receipt["artifacts"]["forward_endpoint_regression_sha256"],
            "Phase 6 result digest drift")
    require(len(rows) == receipt["results"]["result_rows"], "Phase 6 result row count drift")
    primary = [row for row in rows if row["execution_stage"] == "primary"]
    require(len(primary) == 625, "primary result row count drift")
    require(all(row["reducer_equal"] == row["gpu_equal"] == "1" for row in primary),
            "committed Phase 6 mismatch")
    if check_artifacts:
        artifact_root = ROOT / receipt["artifacts"]["root"]
        require(artifact_root.is_dir() and not artifact_root.is_symlink(), "Phase 6 artifact root unavailable")
        for attempt_id, expected in receipt["artifacts"]["attempt_manifest_digests"].items():
            manifest = artifact_root / attempt_id / "artifact_manifest.tsv"
            require(sha256_file(manifest) == expected, f"{attempt_id}: artifact manifest drift")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-plan", action="store_true")
    mode.add_argument("--check-plan", action="store_true")
    mode.add_argument("--run-formal", action="store_true")
    mode.add_argument("--check-results", action="store_true")
    parser.add_argument("--driver", type=Path, default=DEFAULT_DRIVER)
    parser.add_argument("--skip-artifacts", action="store_true")
    arguments = parser.parse_args()
    if arguments.write_plan:
        write_plan()
        print("SSW-CUDA Phase 6 attempt plan written")
    elif arguments.check_plan:
        rows = validate_plan()
        print(f"SSW-CUDA Phase 6 attempt plan OK rows={len(rows)} supported_gpu_tasks=841")
    elif arguments.run_formal:
        run_formal(arguments.driver.resolve())
        print("SSW-CUDA Phase 6 formal regression complete")
    else:
        receipt = validate_results(check_artifacts=not arguments.skip_artifacts)
        print(
            "SSW-CUDA Phase 6 results OK "
            f"primary={receipt['execution']['primary_gpu_tasks']} "
            f"total_gpu_tasks={receipt['execution']['total_supported_gpu_task_executions']}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Phase6Error, P5.Phase5Error) as error:
        raise SystemExit(str(error))
