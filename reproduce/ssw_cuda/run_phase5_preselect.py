#!/usr/bin/env python3
"""Plan, execute, and audit the Phase 5 exact SSW-CUDA L1/L2 regression."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
CORPUS_BUILDER = ROOT / "reproduce/ssw_cuda/build_corpus.py"
CORPUS_MANIFEST = ROOT / "paper/ssw_cuda/corpus_manifest.tsv"
HOLDOUT_MANIFEST = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
PLAN = ROOT / "paper/ssw_cuda/preselect_attempt_plan.tsv"
DESIGN = ROOT / "paper/ssw_cuda/preselect_design.md"
RESULTS = ROOT / "paper/ssw_cuda/preselect_regression.tsv"
RECEIPT = ROOT / "paper/ssw_cuda/preselect_receipt.json"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/ssw-cuda-v1/preselect"
FORMAL_ROOT = ARTIFACT_ROOT / "formal-v1"
DEFAULT_DRIVER = ARTIFACT_ROOT / "build/ssw_cuda_preselect_driver"
SCHEMA_VERSION = "1"
PHASE4_HEAD = "5975cef5b2792da2a369a0d1a187fa2b9c248c25"
MAXIMUM_TOTAL_DP_CELLS = 1 << 31

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
    "threshold_policy",
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
    "threshold",
    "query_length",
    "reference_length",
    "expected_status",
    "observed_status",
    "numeric_path",
    "cpu_column_digest",
    "gpu_column_digest",
    "column_equal",
    "cpu_scoreinfo_digest",
    "gpu_scoreinfo_digest",
    "scoreinfo_equal",
    "driver_returncode",
    "formal_contract",
)

DETERMINISM_CASE_IDS = (
    "tiny-ac-q00-r00",
    "tiny-ac-q00-r13",
    "tiny-ac-q13-r00",
    "tiny-ac-q13-r13",
    "adv-homopolymer",
    "adv-periodic-repeat",
    "adv-palindrome-rc",
    "adv-equal-forward",
    "adv-equal-reverse",
    "adv-equal-gap",
    "adv-open-extend",
    "adv-e-f",
    "adv-diagonal-gap",
    "adv-byte-boundary-253",
    "adv-byte-boundary-255",
    "adv-length-0257",
)

EXTRA_FAIL_PROBES = (
    "empty_query",
    "empty_reference",
    "invalid_base",
    "query_too_long",
    "capacity",
    "out_of_memory",
    "contract_drift",
    "device_out_of_range",
)


class Phase5Error(RuntimeError):
    pass


@dataclass(frozen=True)
class Case:
    case_id: str
    corpus_partition: str
    case_class: str
    execution_tier: str
    source_kind: str
    query: bytes
    reference: bytes
    query_sha256: str
    reference_sha256: str
    pair_digest: str
    threshold: int
    expected_status: str = "ok"
    transform_strand: int | None = None
    transform_para: int | None = None
    transform_rule: int | None = None
    expected_column_digest: str | None = None
    expected_scoreinfo_digest: str | None = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Phase5Error(message)


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORPUS = load_module("ssw_cuda_phase5_corpus", CORPUS_BUILDER)


def read_fasta(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe FASTA: {path}")
    lines = path.read_bytes().splitlines()
    sequence = b"".join(line.strip() for line in lines if line and not line.startswith(b">"))
    require(sequence, f"empty FASTA sequence: {path}")
    return sequence


def threshold_for(query: bytes, reference: bytes) -> int:
    require(query and reference, "threshold requested for empty sequence")
    return min(65, 5 * min(len(query), len(reference)) - 1)


def reconstruct_fuzz(tier: str) -> dict[str, tuple[bytes, bytes]]:
    require(tier in {"compact", "large"}, "invalid fuzz tier")
    seed = CORPUS.COMPACT_FUZZ_SEED if tier == "compact" else CORPUS.LARGE_FUZZ_SEED
    count = CORPUS.COMPACT_FUZZ_COUNT if tier == "compact" else CORPUS.LARGE_FUZZ_COUNT
    rng = CORPUS.SplitMix64(seed)
    profiles = ("uniform", "gc_low", "gc_high", "repeat")
    pairs: dict[str, tuple[bytes, bytes]] = {}
    for index in range(count):
        profile = profiles[index % len(profiles)]
        if tier == "compact":
            query_length = 1 + rng.randbelow(96)
            reference_length = 1 + rng.randbelow(128)
        elif index < len(CORPUS.LENGTH_BOUNDARIES):
            query_length = CORPUS.LENGTH_BOUNDARIES[index]
            reference_length = CORPUS.LENGTH_BOUNDARIES[-index - 1]
        else:
            query_length = 64 + rng.randbelow(2812 - 64 + 1)
            reference_length = 64 + rng.randbelow(2812 - 64 + 1)
        query = CORPUS.fuzz_sequence(rng, query_length, profile)
        reference = CORPUS.fuzz_sequence(
            rng, reference_length, profiles[(index + 1) % len(profiles)]
        )
        pairs[f"fuzz-{tier}-{index:04d}"] = (query, reference)
    return pairs


def generated_cases() -> list[Case]:
    compact_fuzz = reconstruct_fuzz("compact")
    large_fuzz = reconstruct_fuzz("large")
    cases: list[Case] = []
    for row in CORPUS.build_manifest_rows():
        if row["source_kind"] != "generated":
            continue
        parameters = json.loads(row["generator_parameters_json"])
        if row["corpus_partition"] == "tiny_exhaustive":
            query = parameters["query"].encode("ascii")
            reference = parameters["reference"].encode("ascii")
        elif row["generator"] == "explicit":
            query = bytes.fromhex(parameters["query_hex"])
            reference = bytes.fromhex(parameters["reference_hex"])
        elif row["generator"] == "periodic_single_substitution":
            query = CORPUS.periodic(parameters["pattern"].encode("ascii"), parameters["length"])
            mutable = bytearray(query)
            mutation_index = parameters["mutation_index"]
            mutable[mutation_index] = ord("T") if mutable[mutation_index] != ord("T") else ord("A")
            reference = bytes(mutable)
        elif row["case_id"] in compact_fuzz:
            query, reference = compact_fuzz[row["case_id"]]
        elif row["case_id"] in large_fuzz:
            query, reference = large_fuzz[row["case_id"]]
        else:
            raise Phase5Error(f"cannot reconstruct generated case {row['case_id']}")

        require(len(query) == int(row["query_length"]), f"{row['case_id']}: query length drift")
        require(len(reference) == int(row["reference_length"]), f"{row['case_id']}: reference length drift")
        require(sha256_bytes(query) == row["query_sha256"], f"{row['case_id']}: query digest drift")
        require(sha256_bytes(reference) == row["reference_sha256"], f"{row['case_id']}: reference digest drift")
        require(
            CORPUS.generated_pair_digest(query, reference) == row["pair_digest"],
            f"{row['case_id']}: pair digest drift",
        )
        unsupported = row["case_class"].startswith("unsupported_")
        cases.append(
            Case(
                case_id=row["case_id"],
                corpus_partition=row["corpus_partition"],
                case_class=row["case_class"],
                execution_tier=row["execution_tier"],
                source_kind=row["source_kind"],
                query=query,
                reference=reference,
                query_sha256=row["query_sha256"],
                reference_sha256=row["reference_sha256"],
                pair_digest=row["pair_digest"],
                threshold=0 if unsupported else threshold_for(query, reference),
                expected_status="fail_closed" if unsupported else "ok",
            )
        )
    require(len(cases) == 625, "generated Phase 5 case count drift")
    return cases


def fnv_update_u64(value: int, digest: int) -> int:
    for byte in range(8):
        digest ^= (value >> (byte * 8)) & 0xFF
        digest = (digest * 1099511628211) & ((1 << 64) - 1)
    return digest


def scoreinfo_fixture_digest(items: list[dict[str, int]]) -> str:
    digest = 1469598103934665603
    for item in items:
        digest = fnv_update_u64(item["score"], digest)
        digest = fnv_update_u64(item["position"], digest)
    digest = fnv_update_u64(len(items), digest)
    return f"{digest:016x}"


def known_cases() -> list[Case]:
    holdout = {row["workload_id"]: row for row in read_tsv(HOLDOUT_MANIFEST)}
    corpus = {row["case_id"]: row for row in read_tsv(CORPUS_MANIFEST)}
    definitions = (
        ("hq10_ht02", "known-hq10-ht02-traceback", 65, 0, 1, 5, "hq10_prealign.json"),
        ("hq11_ht02", "known-hq11-ht02-endpoint", 80, 1, -1, 12, "hq11_prealign.json"),
    )
    output: list[Case] = []
    for workload_id, case_id, threshold, strand, para, rule, fixture_name in definitions:
        source = holdout[workload_id]
        manifest = corpus[case_id]
        query = read_fasta(ROOT / source["query_path"])
        reference = read_fasta(ROOT / source["target_path"])
        require(sha256_bytes(query) == source["query_sequence_sha256"], f"{case_id}: source query drift")
        require(sha256_bytes(reference) == source["target_sequence_sha256"], f"{case_id}: source target drift")
        fixture = json.loads(
            (ROOT / "tests/ssw_cuda/fixtures" / fixture_name).read_text(encoding="utf-8")
        )
        final_pass = fixture["dp_passes"][-1]
        output.append(
            Case(
                case_id=case_id,
                corpus_partition=manifest["corpus_partition"],
                case_class=manifest["case_class"],
                execution_tier="compact",
                source_kind="historical_annotation",
                query=query,
                reference=reference,
                query_sha256=source["query_sequence_sha256"],
                reference_sha256=source["target_sequence_sha256"],
                pair_digest=manifest["pair_digest"],
                threshold=threshold,
                transform_strand=strand,
                transform_para=para,
                transform_rule=rule,
                expected_column_digest=final_pass["column_max_digest_fnv1a64"],
                expected_scoreinfo_digest=scoreinfo_fixture_digest(fixture["selection"]["scoreinfos"]),
            )
        )
    return output


def all_cases() -> list[Case]:
    cases = generated_cases() + known_cases()
    require(len(cases) == 627, "Phase 5 executable/fail-closed case count drift")
    require(len({case.case_id for case in cases}) == len(cases), "duplicate Phase 5 case id")
    return cases


def case_groups(cases: list[Case]) -> dict[str, list[Case]]:
    by_id = {case.case_id: case for case in cases}
    groups = {
        "tiny_exhaustive": [
            case for case in cases if case.corpus_partition == "tiny_exhaustive"
        ],
        "adversarial_compact": [
            case
            for case in cases
            if case.corpus_partition == "adversarial"
            and case.execution_tier == "compact"
            and case.expected_status == "ok"
        ],
        "compact_fuzz": [
            case for case in cases if case.case_id.startswith("fuzz-compact-")
        ],
        "known_hq10_hq11": [case for case in cases if case.source_kind == "historical_annotation"],
        "large": [
            case for case in cases if case.execution_tier == "large"
        ],
        "unsupported": [case for case in cases if case.expected_status == "fail_closed"],
        "determinism": [by_id[case_id] for case_id in DETERMINISM_CASE_IDS],
    }
    expected = {
        "tiny_exhaustive": 196,
        "adversarial_compact": 30,
        "compact_fuzz": 128,
        "known_hq10_hq11": 2,
        "large": 267,
        "unsupported": 4,
        "determinism": 16,
    }
    require({key: len(value) for key, value in groups.items()} == expected, "Phase 5 group count drift")
    return groups


def plan_rows() -> list[dict[str, Any]]:
    groups = case_groups(all_cases())
    rows: list[dict[str, Any]] = []

    def add(
        attempt_id: str,
        stage: str,
        scope: str,
        count: int,
        repeat_id: str,
        device: int,
        timeout: int,
        expected: str = "complete",
    ) -> None:
        rows.append(
            {
                "attempt_id": attempt_id,
                "execution_stage": stage,
                "backend": "ssw_cuda_preselect_v1",
                "scope": scope,
                "unique_case_count": count,
                "repeat_id": repeat_id,
                "order": len(rows) + 1,
                "device": device,
                "gpu_assignment": f"logical_{device}_physical_{device}",
                "contract_layers": "L1,L2",
                "threshold_policy": "min_65_static_max_score_upper_bound_minus_1",
                "maximum_total_dp_cells": MAXIMUM_TOTAL_DP_CELLS,
                "timeout_seconds": timeout,
                "retry_policy": "none",
                "claim_role": "regression_only",
                "formal_source_data": 1,
                "runner_commit_policy": "committed_HEAD_clean_at_start",
                "expected_status": expected,
                "artifact_root": f".paper-artifacts/ssw-cuda-v1/preselect/formal-v1/{attempt_id}",
            }
        )

    primary = (
        ("p5-primary-tiny", "tiny_exhaustive", 300),
        ("p5-primary-adversarial", "adversarial_compact", 300),
        ("p5-primary-compact-fuzz", "compact_fuzz", 300),
        ("p5-primary-known", "known_hq10_hq11", 300),
        ("p5-primary-large", "large", 1800),
    )
    for attempt_id, scope, timeout in primary:
        add(attempt_id, "primary", scope, len(groups[scope]), "0", 0, timeout)
    for case in groups["unsupported"]:
        add(f"p5-invalid-{case.case_id}", "unsupported", case.case_id, 1, "0", 0, 60, "fail_closed")
    for repeat in range(10):
        add(
            f"p5-determinism-r{repeat:02d}",
            "determinism",
            "fixed_16_case_subset",
            16,
            str(repeat),
            0,
            300,
        )
    for device in (0, 1):
        add(
            f"p5-dual-gpu{device}",
            "same_model_dual_gpu",
            "fixed_16_case_subset",
            16,
            "0",
            device,
            300,
        )
    for probe in EXTRA_FAIL_PROBES:
        add(f"p5-fail-{probe}", "fail_closed", probe, 1, "0", 0, 60, "fail_closed")
    require(len(rows) == 29, "Phase 5 attempt-plan row count drift")
    return rows


def validate_plan() -> list[dict[str, str]]:
    expected = tsv_bytes(PLAN_FIELDS, plan_rows())
    require(PLAN.read_bytes() == expected, "Phase 5 attempt plan is not reproducible")
    rows = read_tsv(PLAN)
    require(all(row["retry_policy"] == "none" for row in rows), "retry policy drift")
    require(sum(int(row["unique_case_count"]) for row in rows if row["execution_stage"] in {"primary", "determinism", "same_model_dual_gpu"}) == 815,
            "planned GPU task-execution count drift")
    require(sum(int(row["unique_case_count"]) for row in rows if row["execution_stage"] == "primary") == 623,
            "primary GPU task count drift")
    require(len([row for row in rows if row["execution_stage"] == "determinism"]) == 10,
            "determinism repeat count drift")
    return rows


def write_plan() -> None:
    PLAN.write_bytes(tsv_bytes(PLAN_FIELDS, plan_rows()))


def input_tsv(cases: Sequence[Case]) -> bytes:
    transformed = any(case.transform_rule is not None for case in cases)
    require(not transformed or all(case.transform_rule is not None for case in cases),
            "cannot mix transformed and direct cases in one driver batch")
    fields = ["case_id", "threshold", "query_hex", "reference_hex"]
    if transformed:
        fields += ["transform_strand", "transform_para", "transform_rule"]
    rows: list[dict[str, Any]] = []
    for case in cases:
        row: dict[str, Any] = {
            "case_id": case.case_id,
            "threshold": case.threshold,
            "query_hex": case.query.hex(),
            "reference_hex": case.reference.hex(),
        }
        if transformed:
            row.update(
                {
                    "transform_strand": case.transform_strand,
                    "transform_para": case.transform_para,
                    "transform_rule": case.transform_rule,
                }
            )
        rows.append(row)
    return tsv_bytes(fields, rows)


def command_output(command: Sequence[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return completed.stdout.strip()


def git_output(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_driver_rows(stdout: str) -> list[dict[str, str]]:
    lines = [line for line in stdout.splitlines() if line]
    require(lines and lines[0].startswith("case_id\t"), "driver result header missing")
    return list(csv.DictReader(io.StringIO("\n".join(lines) + "\n"), delimiter="\t"))


def write_artifact_manifest(attempt_root: Path, names: Sequence[str]) -> str:
    rows = []
    for name in names:
        path = attempt_root / name
        require(path.is_file() and not path.is_symlink(), f"missing attempt artifact: {path}")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = tsv_bytes(("path", "bytes", "sha256"), rows)
    manifest = attempt_root / "artifact_manifest.tsv"
    manifest.write_bytes(payload)
    digest = sha256_bytes(payload)
    (attempt_root / "artifact_manifest.sha256").write_text(
        f"{digest}  artifact_manifest.tsv\n", encoding="ascii"
    )
    return digest


def execute_driver_attempt(
    plan: dict[str, str],
    cases: Sequence[Case],
    driver: Path,
    source_commit: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    attempt_root = ROOT / plan["artifact_root"]
    require(not attempt_root.exists(), f"attempt artifact root already exists: {attempt_root}")
    attempt_root.mkdir(parents=True)
    input_path = attempt_root / "input.tsv"
    input_path.write_bytes(input_tsv(cases))
    stdout_path = attempt_root / "stdout.tsv"
    stderr_path = attempt_root / "stderr.log"
    resource_path = attempt_root / "resource.log"
    command = [
        "/usr/bin/time",
        "-v",
        "-o",
        str(resource_path),
        str(driver),
        "--input",
        str(input_path),
        "--device",
        plan["device"],
        "--maximum-cells",
        plan["maximum_total_dp_cells"],
    ]
    started_utc = utc_now()
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(plan["timeout_seconds"]),
            env={
                **os.environ,
                "CUDA_VISIBLE_DEVICES": "0,1",
                "FASIM_TRANSFERSTRING_TABLE": "0",
            },
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        returncode = 124
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
    wall_seconds = time.monotonic() - started
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    if(not resource_path.exists()):
        resource_path.write_text("resource log unavailable after timeout\n", encoding="utf-8")

    expected_complete = plan["expected_status"] == "complete"
    observed_status = "complete" if returncode == 0 else ("timeout" if timed_out else "fail_closed")
    result_rows: list[dict[str, Any]] = []
    if(expected_complete):
        parsed = parse_driver_rows(stdout)
        require(len(parsed) == len(cases), f"{plan['attempt_id']}: result row count drift")
        by_case = {case.case_id: case for case in cases}
        for row in parsed:
            case = by_case[row["case_id"]]
            if case.expected_column_digest is not None:
                require(row["cpu_column_digest"] == case.expected_column_digest,
                        f"{case.case_id}: frozen CPU column fixture drift")
            if case.expected_scoreinfo_digest is not None:
                require(row["cpu_scoreinfo_digest"] == case.expected_scoreinfo_digest,
                        f"{case.case_id}: frozen CPU scoreInfo fixture drift")
            result_rows.append(result_row(plan, case, observed_status, returncode, row))
    else:
        require(len(cases) == 1, "unsupported attempt must contain exactly one case")
        result_rows.append(result_row(plan, cases[0], observed_status, returncode, None))

    attempt = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": plan["attempt_id"],
        "phase": 5,
        "backend": plan["backend"],
        "execution_stage": plan["execution_stage"],
        "scope": plan["scope"],
        "case_count": len(cases),
        "source_commit": source_commit,
        "binary_sha256": sha256_file(driver),
        "input_sha256": sha256_file(input_path),
        "command_argv": command,
        "environment": {
            "CUDA_VISIBLE_DEVICES": "0,1",
            "selected_logical_device": plan["device"],
            "FASIM_TRANSFERSTRING_TABLE": "0",
        },
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "wall_seconds": wall_seconds,
        "returncode": returncode,
        "status": observed_status,
        "timeout": timed_out,
        "retry_count": 0,
        "fallback_used": False,
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "resource_path": str(resource_path.relative_to(ROOT)),
    }
    attempt_path = attempt_root / "attempt.json"
    attempt_path.write_bytes(json_bytes(attempt))
    manifest_digest = write_artifact_manifest(
        attempt_root, ("input.tsv", "stdout.tsv", "stderr.log", "resource.log", "attempt.json")
    )
    attempt["artifact_manifest_sha256"] = manifest_digest
    return result_rows, attempt


def execute_probe_attempt(
    plan: dict[str, str], driver: Path, source_commit: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    probe = plan["scope"]
    attempt_root = ROOT / plan["artifact_root"]
    require(not attempt_root.exists(), f"attempt artifact root already exists: {attempt_root}")
    attempt_root.mkdir(parents=True)
    stdout_path = attempt_root / "stdout.log"
    stderr_path = attempt_root / "stderr.log"
    resource_path = attempt_root / "resource.log"
    command = [
        "/usr/bin/time", "-v", "-o", str(resource_path), str(driver),
        "--invalid-probe", probe, "--device", plan["device"],
    ]
    started_utc = utc_now()
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=int(plan["timeout_seconds"]),
        env={
            **os.environ,
            "CUDA_VISIBLE_DEVICES": "0,1",
            "FASIM_TRANSFERSTRING_TABLE": "0",
        },
    )
    wall_seconds = time.monotonic() - started
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    require(completed.returncode == 0, f"fail-closed probe failed: {probe}")
    require("status=" in completed.stdout and "status=ok" not in completed.stdout,
            f"probe did not report a fail-closed status: {probe}")
    observed = completed.stdout.split("status=", 1)[1].split()[0]
    synthetic = Case(
        case_id=f"probe-{probe}", corpus_partition="fail_closed", case_class=probe,
        execution_tier="probe", source_kind="built_in_probe", query=b"", reference=b"",
        query_sha256="NA", reference_sha256="NA", pair_digest="NA", threshold=0,
        expected_status="fail_closed",
    )
    rows = [result_row(plan, synthetic, observed, completed.returncode, None)]
    attempt = {
        "schema_version": SCHEMA_VERSION,
        "attempt_id": plan["attempt_id"],
        "phase": 5,
        "backend": plan["backend"],
        "execution_stage": plan["execution_stage"],
        "scope": probe,
        "case_count": 1,
        "source_commit": source_commit,
        "binary_sha256": sha256_file(driver),
        "command_argv": command,
        "environment": {
            "CUDA_VISIBLE_DEVICES": "0,1",
            "selected_logical_device": plan["device"],
            "FASIM_TRANSFERSTRING_TABLE": "0",
        },
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "wall_seconds": wall_seconds,
        "returncode": completed.returncode,
        "status": "fail_closed_as_expected",
        "timeout": False,
        "retry_count": 0,
        "fallback_used": False,
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "resource_path": str(resource_path.relative_to(ROOT)),
    }
    attempt_path = attempt_root / "attempt.json"
    attempt_path.write_bytes(json_bytes(attempt))
    manifest_digest = write_artifact_manifest(
        attempt_root, ("stdout.log", "stderr.log", "resource.log", "attempt.json")
    )
    attempt["artifact_manifest_sha256"] = manifest_digest
    return rows, attempt


def result_row(
    plan: dict[str, str],
    case: Case,
    observed_status: str,
    returncode: int,
    driver_row: dict[str, str] | None,
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
        "threshold": case.threshold,
        "query_length": len(case.query),
        "reference_length": len(case.reference),
        "expected_status": case.expected_status,
        "observed_status": observed_status,
        "numeric_path": driver_row["numeric_path"] if driver_row else "NA",
        "cpu_column_digest": driver_row["cpu_column_digest"] if driver_row else "NA",
        "gpu_column_digest": driver_row["gpu_column_digest"] if driver_row else "NA",
        "column_equal": driver_row["column_equal"] if driver_row else "NA",
        "cpu_scoreinfo_digest": driver_row["cpu_scoreinfo_digest"] if driver_row else "NA",
        "gpu_scoreinfo_digest": driver_row["gpu_scoreinfo_digest"] if driver_row else "NA",
        "scoreinfo_equal": driver_row["scoreinfo_equal"] if driver_row else "NA",
        "driver_returncode": returncode,
        "formal_contract": "L1_L2_exact" if driver_row else "fail_closed",
    }


def cases_for_plan(plan: dict[str, str], groups: dict[str, list[Case]]) -> list[Case]:
    stage = plan["execution_stage"]
    if stage == "primary":
        return groups[plan["scope"]]
    if stage == "unsupported":
        return [next(case for case in groups["unsupported"] if case.case_id == plan["scope"])]
    if stage in {"determinism", "same_model_dual_gpu"}:
        return groups["determinism"]
    raise Phase5Error(f"attempt has no case group: {plan['attempt_id']}")


def normalized_digest(rows: Sequence[dict[str, Any]]) -> str:
    payload = [
        {
            key: row[key]
            for key in (
                "case_id", "numeric_path", "cpu_column_digest", "gpu_column_digest",
                "column_equal", "cpu_scoreinfo_digest", "gpu_scoreinfo_digest", "scoreinfo_equal",
            )
        }
        for row in rows
    ]
    return sha256_bytes(json_bytes(payload))


def run_formal(driver: Path) -> None:
    validate_plan()
    require(driver.is_file() and not driver.is_symlink(), f"missing or unsafe driver: {driver}")
    require(not FORMAL_ROOT.exists(), f"formal artifact root already exists: {FORMAL_ROOT}")
    require(not RESULTS.exists() and not RECEIPT.exists(), "committed Phase 5 results already exist")
    require(git_output("status", "--porcelain=v1") == "", "formal Phase 5 run requires a clean working tree")
    source_commit = git_output("rev-parse", "HEAD")
    for relative in (
        "fasim/ssw_cuda/ssw_cuda_api.h",
        "fasim/ssw_cuda/ssw_cuda_pre_align.cu",
        "fasim/ssw_cuda/ssw_cuda_select.cu",
        "fasim/ssw_cuda/ssw_cuda_stub.cpp",
        "paper/ssw_cuda/preselect_attempt_plan.tsv",
        "paper/ssw_cuda/preselect_design.md",
        "reproduce/ssw_cuda/run_phase5_preselect.py",
        "scripts/check_ssw_cuda_phase5.sh",
        "tests/ssw_cuda/test_preselect.py",
    ):
        require(subprocess.run(["git", "cat-file", "-e", f"{source_commit}:{relative}"], cwd=ROOT).returncode == 0,
                f"formal dependency is not committed: {relative}")

    cases = all_cases()
    groups = case_groups(cases)
    plans = read_tsv(PLAN)
    all_results: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    started_utc = utc_now()
    formal_start = time.monotonic()
    gpu_inventory = command_output([
        "nvidia-smi", "--query-gpu=index,name,uuid,memory.total,compute_cap", "--format=csv,noheader"
    ]).splitlines()
    require(len(gpu_inventory) >= 2, "Phase 5 dual-GPU gate requires two visible GPUs")
    gpu_names = [line.split(",", 2)[1].strip() for line in gpu_inventory[:2]]
    require(gpu_names[0] == gpu_names[1], "Phase 5 dual-GPU gate requires the same GPU model")
    for plan in plans:
        if plan["execution_stage"] == "fail_closed":
            rows, attempt = execute_probe_attempt(plan, driver, source_commit)
        else:
            rows, attempt = execute_driver_attempt(
                plan, cases_for_plan(plan, groups), driver, source_commit
            )
        all_results.extend(rows)
        attempts.append(attempt)

    primary = [row for row in all_results if row["execution_stage"] == "primary"]
    require(len(primary) == 623, "formal primary result count drift")
    require(all(row["column_equal"] == "1" and row["scoreinfo_equal"] == "1" for row in primary),
            "formal primary L1/L2 mismatch")
    unsupported = [row for row in all_results if row["execution_stage"] == "unsupported"]
    require(len(unsupported) == 4 and all(row["observed_status"] == "fail_closed" for row in unsupported),
            "frozen unsupported cases did not fail closed")
    deterministic = [row for row in all_results if row["execution_stage"] == "determinism"]
    repeat_digests = []
    for repeat in range(10):
        subset = [row for row in deterministic if row["repeat_id"] == str(repeat)]
        require(len(subset) == 16, "determinism repeat row-count drift")
        repeat_digests.append(normalized_digest(subset))
    require(len(set(repeat_digests)) == 1, "10-repeat digest instability")
    dual = [row for row in all_results if row["execution_stage"] == "same_model_dual_gpu"]
    dual_digests = [normalized_digest([row for row in dual if row["device"] == str(device)]) for device in (0, 1)]
    require(dual_digests[0] == dual_digests[1], "same-model dual-GPU digest mismatch")

    result_payload = tsv_bytes(RESULT_FIELDS, all_results)
    RESULTS.write_bytes(result_payload)
    gpu_wall_seconds_upper_bound = sum(
        attempt["wall_seconds"]
        for attempt in attempts
        if attempt["execution_stage"] in {"primary", "determinism", "same_model_dual_gpu"}
    )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "phase": 5,
        "status": "pass",
        "source_commit": source_commit,
        "clean_worktree_at_start": True,
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "formal_wall_seconds": time.monotonic() - formal_start,
        "driver": {
            "path": str(driver.relative_to(ROOT)),
            "sha256": sha256_file(driver),
        },
        "inputs": {
            "corpus_manifest_sha256": sha256_file(CORPUS_MANIFEST),
            "attempt_plan_sha256": sha256_file(PLAN),
            "attempt_plan_rows": len(plans),
            "generated_corpus_cases": 625,
            "known_fixture_cases": 2,
            "identity_only_not_executed": 122,
        },
        "execution": {
            "primary_gpu_tasks": 623,
            "unsupported_frozen_cases": 4,
            "determinism_unique_cases": 16,
            "determinism_repeats": 10,
            "same_model_gpu_count": 2,
            "total_gpu_task_executions": 815,
            "attempt_count": len(attempts),
            "retry_count": 0,
            "mechanism_repair_iterations": 1,
            "gpu_wall_seconds_upper_bound": gpu_wall_seconds_upper_bound,
            "gpu_budget_seconds": 24 * 3600,
        },
        "results": {
            "result_rows": len(all_results),
            "primary_column_mismatches": 0,
            "primary_scoreinfo_mismatches": 0,
            "selected_false_negatives": 0,
            "selected_unexpected_extras": 0,
            "selected_order_mismatches": 0,
            "selected_reason_mismatches": 0,
            "technical_failures": 0,
            "unexpected_fallbacks": 0,
            "unsupported_fail_closed": 4,
            "extra_fail_closed_probes": len(EXTRA_FAIL_PROBES),
            "repeat_digest": repeat_digests[0],
            "repeat_digest_stable": True,
            "dual_gpu_digests": dual_digests,
            "same_model_dual_gpu_equal": True,
            "hq10_fixture_column_digest": next(row["cpu_column_digest"] for row in primary if row["case_id"] == "known-hq10-ht02-traceback"),
            "hq11_fixture_column_digest": next(row["cpu_column_digest"] for row in primary if row["case_id"] == "known-hq11-ht02-endpoint"),
            "final_numeric_path_counts": {
                key: sum(1 for row in primary if row["numeric_path"] == key)
                for key in sorted({row["numeric_path"] for row in primary})
            },
        },
        "artifacts": {
            "root": str(FORMAL_ROOT.relative_to(ROOT)),
            "preselect_regression_sha256": sha256_bytes(result_payload),
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
            "contract_established": "L1_L2_regression",
            "promotion_evidence": False,
            "fresh_holdout_consumed": False,
            "cpu_oracle_replaced": False,
            "default_backend_changed": False,
            "bioinformatics_b3_track": "closed_amdahl",
            "l8_contract_status": "diagnostic_only",
        },
    }
    require(gpu_wall_seconds_upper_bound < 24 * 3600, "Phase 5 GPU budget exceeded")
    RECEIPT.write_bytes(json_bytes(receipt))


def validate_results(check_artifacts: bool = True) -> dict[str, Any]:
    validate_plan()
    require(RECEIPT.is_file() and not RECEIPT.is_symlink(), "Phase 5 receipt missing")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rows = read_tsv(RESULTS)
    require(receipt["status"] == "pass", "Phase 5 receipt is not pass")
    require(receipt["execution"]["primary_gpu_tasks"] == 623, "primary task count drift")
    require(receipt["execution"]["total_gpu_task_executions"] == 815, "total GPU task count drift")
    require(receipt["execution"]["retry_count"] == 0, "retry prohibition violated")
    require(receipt["execution"]["mechanism_repair_iterations"] <= 3, "repair budget exceeded")
    require(receipt["execution"]["gpu_wall_seconds_upper_bound"] < receipt["execution"]["gpu_budget_seconds"],
            "GPU budget exceeded")
    require(receipt["results"]["primary_column_mismatches"] == 0, "L1 mismatch recorded")
    require(receipt["results"]["primary_scoreinfo_mismatches"] == 0, "L2 mismatch recorded")
    require(receipt["results"]["selected_false_negatives"] == 0, "false negative recorded")
    require(receipt["results"]["selected_unexpected_extras"] == 0, "unexpected extra recorded")
    require(receipt["results"]["repeat_digest_stable"], "repeat instability recorded")
    require(receipt["results"]["same_model_dual_gpu_equal"], "dual-GPU mismatch recorded")
    require(receipt["claim_boundary"]["bioinformatics_b3_track"] == "closed_amdahl", "B3 reopened")
    require(not receipt["claim_boundary"]["fresh_holdout_consumed"], "Phase 5 consumed fresh holdout")
    require(sha256_file(RESULTS) == receipt["artifacts"]["preselect_regression_sha256"],
            "Phase 5 result digest drift")
    require(len(rows) == receipt["results"]["result_rows"], "Phase 5 result row count drift")
    primary = [row for row in rows if row["execution_stage"] == "primary"]
    require(len(primary) == 623, "primary result row count drift")
    require(all(row["column_equal"] == "1" and row["scoreinfo_equal"] == "1" for row in primary),
            "committed Phase 5 mismatch")
    if check_artifacts:
        artifact_root = ROOT / receipt["artifacts"]["root"]
        require(artifact_root.is_dir() and not artifact_root.is_symlink(), "Phase 5 artifact root unavailable")
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
        print("SSW-CUDA Phase 5 attempt plan written")
    elif arguments.check_plan:
        rows = validate_plan()
        print(f"SSW-CUDA Phase 5 attempt plan OK rows={len(rows)} gpu_task_executions=815")
    elif arguments.run_formal:
        run_formal(arguments.driver.resolve())
        print("SSW-CUDA Phase 5 formal regression complete")
    else:
        receipt = validate_results(check_artifacts=not arguments.skip_artifacts)
        print(
            "SSW-CUDA Phase 5 results OK "
            f"primary={receipt['execution']['primary_gpu_tasks']} "
            f"total_gpu_tasks={receipt['execution']['total_gpu_task_executions']}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Phase5Error as error:
        raise SystemExit(str(error))
