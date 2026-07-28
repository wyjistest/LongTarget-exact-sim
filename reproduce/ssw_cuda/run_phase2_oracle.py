#!/usr/bin/env python3
"""Build, execute, and verify the frozen Phase 2 modified-SSW oracle evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper" / "ssw_cuda"
SCHEMA = ROOT / "schemas" / "ssw_oracle_call.schema.json"
FIXTURE_DIR = ROOT / "tests" / "ssw_cuda" / "fixtures"
ARTIFACT_ROOT = ROOT / ".paper-artifacts" / "ssw-cuda-v1" / "phase2" / "formal"
DEFAULT_BINARY = ROOT / ".paper-artifacts" / "ssw-cuda-v1" / "phase2" / "fasim_cpu_oracle"
SOURCE_DATA = PAPER / "cpu_oracle_trace_source_data.tsv"
ARTIFACT_MANIFEST = PAPER / "cpu_oracle_trace_artifacts.tsv"
BINARY_RECEIPT = PAPER / "cpu_oracle_binary_receipt.json"
PLAN = PAPER / "cpu_oracle_attempt_plan.tsv"
OBSERVATIONS = 5
TIMEOUT_SECONDS = 120

SOURCE_FIELDS = (
    "attempt_id",
    "case_id",
    "repeat_id",
    "trace_mode",
    "returncode",
    "timed_out",
    "elapsed_seconds",
    "output_path",
    "output_size_bytes",
    "output_sha256",
    "expected_output_sha256",
    "output_equal_expected",
    "paired_output_equal",
    "stdout_sha256",
    "normalized_stdout_sha256",
    "stderr_sha256",
    "trace_file_count",
    "prealign_trace_sha256",
    "mismatch_call_trace_sha256",
    "artifact_receipt",
)

MANIFEST_FIELDS = ("path", "size_bytes", "sha256", "role")
PLAN_FIELDS = (
    "attempt_id",
    "execution_order",
    "case_id",
    "repeat_id",
    "trace_mode",
    "trace_filter",
    "full_columns",
    "timeout_seconds",
    "retry_policy",
    "formal_source_data",
    "expected_artifact_root",
    "status",
)


@dataclass(frozen=True)
class Case:
    case_id: str
    query: str
    target: str
    query_file_sha256: str
    target_file_sha256: str
    expected_output_sha256: str
    prealign_key: str
    call_key: str
    scoreinfo_index: int
    prealign_score: int
    selection_reason: str
    rule: int
    strand: int
    target_start: int
    cutlength: int
    score1: int
    query_begin: int
    query_end: int
    global_target_begin: int
    global_target_end: int
    cigar: str


CASES = (
    Case(
        case_id="hq10_ht02",
        query="reproduce/bioinformatics/holdout_inputs/queries/hq10_ENSG00000178248_ENST00000785836.fa",
        target="reproduce/bioinformatics/holdout_inputs/targets/ht02_ENSG00000198722_chr9_35159829_35162329.fa",
        query_file_sha256="97edb4ee3631b3b725198e39ffcc7d788a31aaa4a964069ff4d3d032ee073b5b",
        target_file_sha256="15b67727bcbfe8138a9caa1f5100f822c8b021a6008878c65b361caa83fe224e",
        expected_output_sha256="c34ff3fbdb9d1a069397615e2ed695dd336eb2055ce389a8ccade83e3858cb88",
        prealign_key="prealign-w-q01acbd4cee56dd64-tbad996453287e5a7-d0-r5-s0",
        call_key="call-w-q01acbd4cee56dd64-tbad996453287e5a7-d0-r5-s0-si000003-ir00-ts00000512-cl00000069",
        scoreinfo_index=3,
        prealign_score=72,
        selection_reason="best_fallback",
        rule=5,
        strand=0,
        target_start=512,
        cutlength=69,
        score1=68,
        query_begin=1696,
        query_end=1751,
        global_target_begin=524,
        global_target_end=580,
        cigar="20M1I4M2D31M",
    ),
    Case(
        case_id="hq11_ht02",
        query="reproduce/bioinformatics/holdout_inputs/queries/hq11_ENSG00000255857_ENST00000667017.fa",
        target="reproduce/bioinformatics/holdout_inputs/targets/ht02_ENSG00000198722_chr9_35159829_35162329.fa",
        query_file_sha256="a29a008465ae05e377a26d30fbbca1f8f8a324706eec0b3535cac65089a131b9",
        target_file_sha256="15b67727bcbfe8138a9caa1f5100f822c8b021a6008878c65b361caa83fe224e",
        expected_output_sha256="394fe813c2e10d9340165d371255a8a54bf493e3c9da90d57db4e99dfd72cd82",
        prealign_key="prealign-w-q87ef68ef65c6f964-td6ea623950cc9d8a-d0-r12-s1",
        call_key="call-w-q87ef68ef65c6f964-td6ea623950cc9d8a-d0-r12-s1-si000017-ir00-ts00002169-cl00000084",
        scoreinfo_index=17,
        prealign_score=93,
        selection_reason="threshold",
        rule=12,
        strand=1,
        target_start=2169,
        cutlength=84,
        score1=93,
        query_begin=725,
        query_end=790,
        global_target_begin=2191,
        global_target_end=2252,
        cigar="18M4I44M",
    ),
)

FIXTURES = {
    "hq10_ht02": {
        "prealign": FIXTURE_DIR / "hq10_prealign.json",
        "alignment": FIXTURE_DIR / "hq10_mismatch_call.json",
    },
    "hq11_ht02": {
        "prealign": FIXTURE_DIR / "hq11_prealign.json",
        "alignment": FIXTURE_DIR / "hq11_mismatch_call.json",
    },
}

SOURCE_INVENTORY = (
    "Makefile",
    "cuda/prealign_cuda.h",
    "cuda/prealign_cuda_stub.cpp",
    "cuda/prealign_shared.h",
    "fasim/Fasim-LongTarget.cpp",
    "fasim/fastsim.h",
    "fasim/gasal2_align_bridge.h",
    "fasim/gasal2_align_bridge_stub.cpp",
    "fasim/rules.h",
    "fasim/sim.h",
    "fasim/ssw.h",
    "fasim/ssw_cpp.h",
    "fasim/ssw_cpp.cpp",
    "fasim/sswNew.cpp",
    "fasim/ssw_oracle_trace.h",
    "fasim/ssw_oracle_trace.cpp",
    "fasim/stats.h",
    "docs/ssw_cuda/DP_CONTRACT.md",
    "docs/ssw_cuda/ENDPOINT_CONTRACT.md",
    "docs/ssw_cuda/CIGAR_CONTRACT.md",
    "docs/ssw_cuda/TELEMETRY_SPEC.md",
    "schemas/ssw_oracle_call.schema.json",
    "paper/ssw_cuda/cpu_oracle_protocol.md",
    "paper/ssw_cuda/cpu_oracle_attempt_plan.tsv",
    "reproduce/ssw_cuda/scalar_ssw_reference.py",
    "reproduce/ssw_cuda/run_phase2_oracle.py",
    "scripts/check_ssw_cuda_phase2.sh",
    "tests/ssw_cuda/test_phase2_oracle.py",
)


class EvidenceError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fields: Iterable[str], rows: list[dict[str, Any]]) -> bytes:
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(fields), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return output.getvalue().encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def normalized_stdout(data: bytes) -> bytes:
    lines = data.decode("utf-8", errors="replace").splitlines()
    return ("\n".join(line for line in lines if not line.startswith("Running time is ")) + "\n").encode(
        "utf-8"
    )


def fixture_path(case: Case, kind: str) -> Path:
    return FIXTURES[case.case_id][kind]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def case_input_receipt(case: Case) -> dict[str, dict[str, Any]]:
    return {
        "query": {
            "path": case.query,
            "size_bytes": (ROOT / case.query).stat().st_size,
            "sha256": case.query_file_sha256,
        },
        "target": {
            "path": case.target,
            "size_bytes": (ROOT / case.target).stat().st_size,
            "sha256": case.target_file_sha256,
        },
    }


def validate_schema_document() -> dict[str, Any]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "schema draft drift")
    require(schema.get("additionalProperties") is False, "top-level schema must be closed")
    require(set(schema["properties"]["record_kind"]["enum"]) == {"prealign", "alignment"}, "record kinds drift")
    required_defs = {
        "workload",
        "input",
        "scoring",
        "dp_pass",
        "prealign_selection",
        "attempt",
        "forward_endpoint",
        "reverse_start",
        "band_step",
        "traceback",
        "emitted_row",
    }
    require(required_defs <= set(schema["$defs"]), "schema definitions are incomplete")
    return schema


def validate_plan() -> list[dict[str, str]]:
    with PLAN.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == PLAN_FIELDS, "Phase 2 attempt-plan fields drift")
        rows = list(reader)
    expected: list[tuple[str, int, str]] = []
    for case in CASES:
        for repeat_id in range(OBSERVATIONS):
            for trace_mode in ("trace_off", "trace_on"):
                expected.append((case.case_id, repeat_id, trace_mode))
    require(len(rows) == len(expected), "Phase 2 attempt-plan row count drift")
    for index, (row, key) in enumerate(zip(rows, expected), start=1):
        case = next(item for item in CASES if item.case_id == key[0])
        require(int(row["execution_order"]) == index, "Phase 2 execution order drift")
        require((row["case_id"], int(row["repeat_id"]), row["trace_mode"]) == key, "Phase 2 attempt order drift")
        require(row["attempt_id"] == f"{case.case_id}__repeat{key[1]:02d}__{key[2]}", "Phase 2 attempt ID drift")
        expected_filter = "none" if key[2] == "trace_off" else f"{case.prealign_key},{case.call_key}"
        require(row["trace_filter"] == expected_filter, "Phase 2 trace filter drift")
        require(row["full_columns"] == ("0" if key[2] == "trace_off" else "1"), "Phase 2 full-column mode drift")
        require(int(row["timeout_seconds"]) == TIMEOUT_SECONDS, "Phase 2 timeout drift")
        require(row["retry_policy"] == "none", "Phase 2 retry policy drift")
        require(row["formal_source_data"] == "1", "Phase 2 source-data role drift")
        require(
            row["expected_artifact_root"]
            == f".paper-artifacts/ssw-cuda-v1/phase2/formal/{case.case_id}/repeat{key[1]:02d}/{key[2]}",
            "Phase 2 artifact root drift",
        )
        require(row["status"] == "preregistered_not_run", "Phase 2 preexecution status drift")
    return rows


def _digest64(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{16}", value) is not None


def validate_trace_record(record: dict[str, Any], *, full_columns: bool = True) -> None:
    common = {
        "schema_version",
        "oracle_epoch",
        "record_kind",
        "record_key",
        "workload",
        "input",
        "scoring",
        "final_numeric_path",
        "dp_passes",
    }
    require(record.get("schema_version") == "1", "trace schema version drift")
    require(record.get("oracle_epoch") == 2, "trace oracle epoch drift")
    require(record.get("record_kind") in {"prealign", "alignment"}, "invalid trace kind")
    require(isinstance(record.get("record_key"), str) and record["record_key"], "invalid record key")
    require(common <= set(record), "trace common fields missing")
    workload = record["workload"]
    require(workload["key"] in record["record_key"], "record/workload key mismatch")
    require(_digest64(workload["query_digest_fnv1a64"]), "invalid workload query digest")
    require(_digest64(workload["target_digest_fnv1a64"]), "invalid workload target digest")
    scoring = record["scoring"]
    require(
        {key: scoring[key] for key in ("match", "mismatch_penalty", "gap_open", "gap_extend", "mask_len")}
        == {"match": 5, "mismatch_penalty": 4, "gap_open": 16, "gap_extend": 4, "mask_len": 15},
        "effective authority scoring drift",
    )
    passes = record["dp_passes"]
    require(isinstance(passes, list) and passes, "trace DP passes missing")
    for dp_pass in passes:
        require(dp_pass["stage"] in {"prealign", "forward", "reverse"}, "invalid DP stage")
        require(dp_pass["numeric_path"] in {"byte8", "word16", "byte8_avx2", "word16_avx2"}, "invalid numeric path")
        require(dp_pass["column_count"] > 0, "empty DP column vector")
        require(_digest64(dp_pass["column_max_digest_fnv1a64"]), "invalid column digest")
        if full_columns:
            require(isinstance(dp_pass["columns"], list), "full columns were not captured")
            require(len(dp_pass["columns"]) == dp_pass["column_count"], "column count mismatch")
        else:
            require(dp_pass["columns"] is None or isinstance(dp_pass["columns"], list), "invalid columns field")
    if record["record_kind"] == "prealign":
        require(set(record) == common | {"selection"}, "prealign top-level fields drift")
        selection = record["selection"]
        require(selection["threshold_predicate"] == "score_strictly_greater_than_threshold", "threshold predicate drift")
        require(selection["adjacent_distance_exclusive_upper_bound"] == 5, "scoreInfo adjacency drift")
        require(selection["equal_score_tie"] == "lowest_reference_position", "scoreInfo tie drift")
        indexes = [item["index"] for item in selection["scoreinfos"]]
        require(indexes == list(range(len(indexes))), "scoreInfo indexes are not contiguous")
    else:
        alignment_fields = {
            "attempt",
            "status",
            "failure_reason",
            "forward_endpoint",
            "reverse_start",
            "band_history",
            "traceback",
            "emitted_rows",
        }
        require(set(record) == common | alignment_fields, "alignment top-level fields drift")
        require(record["status"] == "complete", "fixture alignment is incomplete")
        attempt = record["attempt"]
        require(attempt["key"] == record["record_key"], "attempt/record key mismatch")
        require(attempt["selection_reason"] in {"threshold", "best_fallback", "last", "not_selected"}, "invalid selection reason")
        stages = [item["stage"] for item in passes]
        require("forward" in stages and "reverse" in stages, "endpoint DP stages missing")
        require(record["band_history"], "band history missing")
        require(_digest64(record["traceback"]["cigar_digest_fnv1a64"]), "invalid CIGAR digest")
        emitted_fields = {
            "row_contract",
            "query_start",
            "query_end",
            "target_start",
            "target_end",
            "direction",
            "strand",
            "reverse",
            "rule",
            "score",
            "nt",
            "mean_identity",
            "mean_stability",
            "aligned_tfo",
            "aligned_tts",
            "ungapped_tfo",
            "ungapped_tts",
            "row_digest_fnv1a64",
        }
        rows = record["emitted_rows"]
        require(isinstance(rows, list), "emitted rows must be an array")
        for row in rows:
            require(set(row) == emitted_fields, "emitted-row fields drift")
            require(row["row_contract"] == "triplex_l6_v1", "emitted-row contract drift")
            require(row["query_start"] <= row["query_end"], "invalid emitted query interval")
            expected_direction = "R" if row["target_start"] < row["target_end"] else "L"
            require(row["direction"] == expected_direction, "emitted-row direction drift")
            require(row["strand"] in {0, 1}, "invalid emitted-row strand")
            require(row["reverse"] in {-1, 1}, "invalid emitted-row reverse mode")
            require(row["rule"] > 0 and row["score"] >= 0 and row["nt"] >= 0, "invalid emitted-row values")
            require(len(row["aligned_tfo"]) == len(row["aligned_tts"]), "aligned row lengths differ")
            require(row["ungapped_tfo"] == row["aligned_tfo"].replace("-", ""), "ungapped TFO drift")
            require(row["ungapped_tts"] == row["aligned_tts"].replace("-", ""), "ungapped TTS drift")
            require(_digest64(row["row_digest_fnv1a64"]), "invalid emitted-row digest")


def validate_case_traces(case: Case, prealign: dict[str, Any], call: dict[str, Any]) -> None:
    validate_trace_record(prealign)
    validate_trace_record(call)
    require(prealign["record_key"] == case.prealign_key, f"{case.case_id}: prealign key drift")
    require(call["record_key"] == case.call_key, f"{case.case_id}: call key drift")
    require(prealign["workload"]["rule"] == case.rule, f"{case.case_id}: prealign rule drift")
    require(prealign["workload"]["strand"] == case.strand, f"{case.case_id}: prealign strand drift")
    scoreinfos = prealign["selection"]["scoreinfos"]
    require(case.scoreinfo_index < len(scoreinfos), f"{case.case_id}: scoreInfo missing")
    require(scoreinfos[case.scoreinfo_index]["score"] == case.prealign_score, f"{case.case_id}: prealign score drift")
    attempt = call["attempt"]
    require(attempt["scoreinfo_index"] == case.scoreinfo_index, f"{case.case_id}: scoreInfo index drift")
    require(attempt["prealign_score"] == case.prealign_score, f"{case.case_id}: attempt prealign score drift")
    require(attempt["identity_round"] == 0 and attempt["identity_ppm"] == 600000, f"{case.case_id}: identity round drift")
    require(attempt["target_start"] == case.target_start, f"{case.case_id}: target start drift")
    require(attempt["cutlength"] == case.cutlength, f"{case.case_id}: cutlength drift")
    require(attempt["selected"] is True, f"{case.case_id}: mismatch call was not selected")
    require(attempt["selection_reason"] == case.selection_reason, f"{case.case_id}: selection reason drift")
    forward = call["forward_endpoint"]
    reverse = call["reverse_start"]
    require(forward["score1"] == case.score1, f"{case.case_id}: score1 drift")
    require(reverse["read_begin1"] == case.query_begin, f"{case.case_id}: query begin drift")
    require(forward["read_end1"] == case.query_end, f"{case.case_id}: query end drift")
    require(attempt["target_start"] + reverse["ref_begin1"] == case.global_target_begin, f"{case.case_id}: global target begin drift")
    require(attempt["target_start"] + forward["ref_end1"] == case.global_target_end, f"{case.case_id}: global target end drift")
    require(call["traceback"]["cigar"] == case.cigar, f"{case.case_id}: CIGAR drift")
    emitted_rows = call["emitted_rows"]
    require(len(emitted_rows) == 1, f"{case.case_id}: mismatch call must emit exactly one retained row")
    row = emitted_rows[0]
    require(
        (row["query_start"], row["query_end"])
        == (case.query_begin + 1, case.query_end + 1),
        f"{case.case_id}: emitted query coordinates drift",
    )
    require(
        (row["target_start"], row["target_end"])
        == (case.global_target_begin + 1, case.global_target_end + 1),
        f"{case.case_id}: emitted target coordinates drift",
    )
    require(row["strand"] == case.strand and row["rule"] == case.rule, f"{case.case_id}: emitted rule/strand drift")
    require(row["score"] == case.score1, f"{case.case_id}: emitted score drift")
    require(len(row["aligned_tfo"]) == row["nt"], f"{case.case_id}: emitted Nt/TFO length drift")
    require(
        len(row["ungapped_tfo"]) == case.query_end - case.query_begin + 1,
        f"{case.case_id}: ungapped TFO/query span drift",
    )
    require(
        len(row["ungapped_tts"]) == case.global_target_end - case.global_target_begin + 1,
        f"{case.case_id}: ungapped TTS/target span drift",
    )


def controlled_environment(trace_dir: Path | None, case: Case | None = None) -> dict[str, str]:
    inherited = os.environ
    environment = {
        key: inherited[key]
        for key in ("PATH", "HOME", "USER", "LOGNAME", "TMPDIR")
        if key in inherited
    }
    environment.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
            "FASIM_EXTEND_THREADS": "1",
            "FASIM_OUTPUT_MODE": "tfosorted",
        }
    )
    if trace_dir is not None:
        require(case is not None, "trace case is required")
        environment.update(
            {
                "FASIM_SSW_ORACLE_TRACE": "1",
                "FASIM_SSW_ORACLE_TRACE_DIR": str(trace_dir),
                "FASIM_SSW_ORACLE_TRACE_FILTER": f"{case.prealign_key},{case.call_key}",
                "FASIM_SSW_ORACLE_TRACE_FULL_COLUMNS": "1",
            }
        )
    return environment


def output_file(output_dir: Path) -> Path:
    paths = [path for path in output_dir.iterdir() if path.is_file() and not path.is_symlink()]
    require(len(paths) == 1, f"expected one authority output in {output_dir}, got {len(paths)}")
    return paths[0]


def trace_records(trace_dir: Path, case: Case) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    require(trace_dir.is_dir() and not trace_dir.is_symlink(), f"missing trace directory: {trace_dir}")
    paths = sorted(trace_dir.glob("*.json"))
    require(len(paths) == 2, f"{case.case_id}: expected two filtered trace files, got {len(paths)}")
    records = {json.loads(path.read_text(encoding="utf-8"))["record_kind"]: path for path in paths}
    require(set(records) == {"prealign", "alignment"}, f"{case.case_id}: trace kinds drift")
    prealign_path = records["prealign"]
    call_path = records["alignment"]
    prealign = json.loads(prealign_path.read_text(encoding="utf-8"))
    call = json.loads(call_path.read_text(encoding="utf-8"))
    validate_case_traces(case, prealign, call)
    return prealign_path, call_path, prealign, call


def run_attempt(binary: Path, case: Case, repeat_id: int, trace_mode: str, root: Path) -> dict[str, Any]:
    attempt_id = f"{case.case_id}__repeat{repeat_id:02d}__{trace_mode}"
    attempt_root = root / case.case_id / f"repeat{repeat_id:02d}" / trace_mode
    require(not attempt_root.exists(), f"attempt root already exists: {attempt_root}")
    output_dir = attempt_root / "output"
    output_dir.mkdir(parents=True)
    trace_dir = attempt_root / "trace"
    trace_enabled = trace_mode == "trace_on"
    environment = controlled_environment(trace_dir if trace_enabled else None, case if trace_enabled else None)
    command = [
        str(binary),
        "-f1",
        str(ROOT / case.target),
        "-f2",
        str(ROOT / case.query),
        "-r",
        "0",
        "-cn",
        "1",
        "-O",
        str(output_dir),
    ]
    start = time.monotonic()
    timed_out = False
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        returncode = 124
        stdout = error.stdout or b""
        stderr = error.stderr or b""
    elapsed = time.monotonic() - start
    atomic_write(attempt_root / "stdout.log", stdout)
    atomic_write(attempt_root / "stderr.log", stderr)
    require(not timed_out, f"{attempt_id}: timed out")
    require(returncode == 0, f"{attempt_id}: return code {returncode}")
    output = output_file(output_dir)
    output_sha = sha256_file(output)
    require(output_sha == case.expected_output_sha256, f"{attempt_id}: authority output drift")
    prealign_sha = ""
    call_sha = ""
    trace_count = 0
    if trace_enabled:
        prealign_path, call_path, _, _ = trace_records(trace_dir, case)
        prealign_sha = sha256_file(prealign_path)
        call_sha = sha256_file(call_path)
        trace_count = 2
    else:
        require(not trace_dir.exists(), f"{attempt_id}: trace-off created a trace directory")
    receipt = {
        "schema_version": 1,
        "phase": 2,
        "attempt_id": attempt_id,
        "case_id": case.case_id,
        "repeat_id": repeat_id,
        "trace_mode": trace_mode,
        "command": command,
        "environment": environment,
        "timeout_seconds": TIMEOUT_SECONDS,
        "retry_policy": "none",
        "inputs": case_input_receipt(case),
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": elapsed,
        "stdout_sha256": sha256_bytes(stdout),
        "normalized_stdout_sha256": sha256_bytes(normalized_stdout(stdout)),
        "stderr_sha256": sha256_bytes(stderr),
        "output_path": display_path(output),
        "output_size_bytes": output.stat().st_size,
        "output_sha256": output_sha,
        "trace_file_count": trace_count,
        "prealign_trace_sha256": prealign_sha,
        "mismatch_call_trace_sha256": call_sha,
    }
    atomic_write(attempt_root / "attempt.json", json_bytes(receipt))
    return receipt


def role_for_artifact(path: Path) -> str:
    if path.name == "attempt.json":
        return "attempt_receipt"
    if path.name == "stdout.log":
        return "stdout"
    if path.name == "stderr.log":
        return "stderr"
    if "trace" in path.parts:
        return "oracle_trace"
    if "output" in path.parts:
        return "authority_output"
    return "supporting"


def artifact_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        require(not path.is_symlink(), f"artifact symlink is forbidden: {path}")
        rows.append(
            {
                "path": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": role_for_artifact(path),
            }
        )
    return rows


def source_row(receipt: dict[str, Any], case: Case, paired_equal: bool) -> dict[str, Any]:
    return {
        "attempt_id": receipt["attempt_id"],
        "case_id": case.case_id,
        "repeat_id": receipt["repeat_id"],
        "trace_mode": receipt["trace_mode"],
        "returncode": receipt["returncode"],
        "timed_out": int(receipt["timed_out"]),
        "elapsed_seconds": f"{receipt['elapsed_seconds']:.9f}",
        "output_path": receipt["output_path"],
        "output_size_bytes": receipt["output_size_bytes"],
        "output_sha256": receipt["output_sha256"],
        "expected_output_sha256": case.expected_output_sha256,
        "output_equal_expected": int(receipt["output_sha256"] == case.expected_output_sha256),
        "paired_output_equal": int(paired_equal),
        "stdout_sha256": receipt["stdout_sha256"],
        "normalized_stdout_sha256": receipt["normalized_stdout_sha256"],
        "stderr_sha256": receipt["stderr_sha256"],
        "trace_file_count": receipt["trace_file_count"],
        "prealign_trace_sha256": receipt["prealign_trace_sha256"],
        "mismatch_call_trace_sha256": receipt["mismatch_call_trace_sha256"],
        "artifact_receipt": str(
            (
                ARTIFACT_ROOT
                / case.case_id
                / f"repeat{int(receipt['repeat_id']):02d}"
                / receipt["trace_mode"]
                / "attempt.json"
            ).relative_to(ROOT)
        ),
    }


def formal_preflight(binary: Path) -> str:
    validate_schema_document()
    validate_plan()
    require(binary.is_file() and os.access(binary, os.X_OK) and not binary.is_symlink(), "Phase 2 binary is missing or unsafe")
    for case in CASES:
        require(sha256_file(ROOT / case.query) == case.query_file_sha256, f"{case.case_id}: query file drift")
        require(sha256_file(ROOT / case.target) == case.target_file_sha256, f"{case.case_id}: target file drift")
    require(git_output("status", "--porcelain") == "", "formal Phase 2 execution requires a clean worktree")
    require(not ARTIFACT_ROOT.exists(), f"formal artifact root already exists: {ARTIFACT_ROOT}")
    for result in (SOURCE_DATA, ARTIFACT_MANIFEST, BINARY_RECEIPT):
        require(not result.exists(), f"formal result already exists: {result}")
    for paths in FIXTURES.values():
        for path in paths.values():
            require(not path.exists(), f"formal fixture already exists: {path}")
    return git_output("rev-parse", "HEAD")


def execute_formal(binary: Path) -> None:
    execution_commit = formal_preflight(binary)
    ARTIFACT_ROOT.mkdir(parents=True)
    receipts: dict[tuple[str, int, str], dict[str, Any]] = {}
    for case in CASES:
        for repeat_id in range(OBSERVATIONS):
            for trace_mode in ("trace_off", "trace_on"):
                receipt = run_attempt(binary, case, repeat_id, trace_mode, ARTIFACT_ROOT)
                receipts[(case.case_id, repeat_id, trace_mode)] = receipt

    source_rows: list[dict[str, Any]] = []
    trace_digests: dict[str, dict[str, str]] = {}
    output_pairs: list[dict[str, Any]] = []
    for case in CASES:
        first_on_root = ARTIFACT_ROOT / case.case_id / "repeat00" / "trace_on" / "trace"
        first_prealign, first_call, _, _ = trace_records(first_on_root, case)
        atomic_write(fixture_path(case, "prealign"), first_prealign.read_bytes())
        atomic_write(fixture_path(case, "alignment"), first_call.read_bytes())
        trace_digests[case.case_id] = {
            "prealign_sha256": sha256_file(first_prealign),
            "mismatch_call_sha256": sha256_file(first_call),
        }
        for repeat_id in range(OBSERVATIONS):
            off = receipts[(case.case_id, repeat_id, "trace_off")]
            on = receipts[(case.case_id, repeat_id, "trace_on")]
            paired_equal = off["output_sha256"] == on["output_sha256"]
            require(paired_equal, f"{case.case_id} repeat {repeat_id}: trace changed authority output")
            require(
                off["normalized_stdout_sha256"] == on["normalized_stdout_sha256"],
                f"{case.case_id} repeat {repeat_id}: trace changed normalized stdout",
            )
            require(off["stderr_sha256"] == on["stderr_sha256"], f"{case.case_id} repeat {repeat_id}: trace changed stderr")
            require(on["prealign_trace_sha256"] == trace_digests[case.case_id]["prealign_sha256"], f"{case.case_id}: prealign trace nondeterminism")
            require(on["mismatch_call_trace_sha256"] == trace_digests[case.case_id]["mismatch_call_sha256"], f"{case.case_id}: call trace nondeterminism")
            source_rows.append(source_row(off, case, paired_equal))
            source_rows.append(source_row(on, case, paired_equal))
            output_pairs.append(
                {
                    "case_id": case.case_id,
                    "repeat_id": repeat_id,
                    "output_sha256": on["output_sha256"],
                    "normalized_stdout_equal": True,
                    "stderr_equal": True,
                }
            )

    manifest = artifact_rows(ARTIFACT_ROOT)
    source_payload = tsv_bytes(SOURCE_FIELDS, source_rows)
    manifest_payload = tsv_bytes(MANIFEST_FIELDS, manifest)
    atomic_write(SOURCE_DATA, source_payload)
    atomic_write(ARTIFACT_MANIFEST, manifest_payload)
    compiler = shutil.which(os.environ.get("CXX", "g++")) or "g++"
    compiler_version = subprocess.run(
        [compiler, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ).stdout.splitlines()[0]
    source_inventory = {relative: sha256_file(ROOT / relative) for relative in SOURCE_INVENTORY}
    receipt = {
        "schema_version": 1,
        "phase": 2,
        "status": "pass",
        "ssw_cpu_oracle_epoch": 2,
        "execution_commit": execution_commit,
        "binary_path": str(binary.relative_to(ROOT)),
        "binary_size_bytes": binary.stat().st_size,
        "binary_sha256": sha256_file(binary),
        "build_command": "make build-ssw-cuda-phase2-oracle",
        "compiler_path": compiler,
        "compiler_version": compiler_version,
        "effective_flags": "-O3 -std=c++11 -pthread -msse2",
        "avx2_authority_active": False,
        "observations_per_case": OBSERVATIONS,
        "cases": [case.case_id for case in CASES],
        "inputs": {case.case_id: case_input_receipt(case) for case in CASES},
        "attempt_count": len(source_rows),
        "attempts_complete": len(source_rows),
        "retry_policy": "none",
        "timeout_seconds": TIMEOUT_SECONDS,
        "instrumentation_off_created_trace_files": 0,
        "authority_outputs_byte_identical_on_off": True,
        "normalized_stdout_identical_on_off": True,
        "stderr_identical_on_off": True,
        "trace_records_deterministic": True,
        "hq10_hq11_stable_attempt_keys": True,
        "fresh_holdout_consumed": False,
        "fixtures": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for paths in FIXTURES.values()
            for path in paths.values()
        },
        "trace_digests": trace_digests,
        "output_pairs": output_pairs,
        "source_data_path": str(SOURCE_DATA.relative_to(ROOT)),
        "source_data_sha256": sha256_bytes(source_payload),
        "artifact_manifest_path": str(ARTIFACT_MANIFEST.relative_to(ROOT)),
        "artifact_manifest_sha256": sha256_bytes(manifest_payload),
        "schema_sha256": sha256_file(SCHEMA),
        "attempt_plan_sha256": sha256_file(PLAN),
        "source_inventory": source_inventory,
    }
    atomic_write(BINARY_RECEIPT, json_bytes(receipt))
    print("SSW-CUDA Phase 2 formal oracle evidence complete")


def read_source_rows() -> list[dict[str, str]]:
    with SOURCE_DATA.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == SOURCE_FIELDS, "Phase 2 source-data fields drift")
        return list(reader)


def check_results(binary: Path) -> None:
    validate_schema_document()
    validate_plan()
    require(ARTIFACT_ROOT.is_dir() and not ARTIFACT_ROOT.is_symlink(), "formal Phase 2 artifact root missing")
    for path in (SOURCE_DATA, ARTIFACT_MANIFEST, BINARY_RECEIPT):
        require(path.is_file() and not path.is_symlink(), f"missing formal Phase 2 result: {path}")
    receipt = json.loads(BINARY_RECEIPT.read_text(encoding="utf-8"))
    require(receipt["status"] == "pass" and receipt["phase"] == 2, "Phase 2 receipt status drift")
    require(receipt["ssw_cpu_oracle_epoch"] == 2, "CPU oracle epoch drift")
    require(receipt["observations_per_case"] == OBSERVATIONS, "observation count drift")
    require(receipt["attempt_count"] == len(CASES) * OBSERVATIONS * 2, "attempt count drift")
    require(receipt["attempts_complete"] == receipt["attempt_count"], "incomplete Phase 2 attempts")
    require(receipt["retry_policy"] == "none", "retry policy drift")
    require(receipt["instrumentation_off_created_trace_files"] == 0, "trace-off file invariant failed")
    require(receipt["authority_outputs_byte_identical_on_off"] is True, "authority output invariant failed")
    require(receipt["normalized_stdout_identical_on_off"] is True, "stdout invariant failed")
    require(receipt["stderr_identical_on_off"] is True, "stderr invariant failed")
    require(receipt["fresh_holdout_consumed"] is False, "fresh holdout was consumed")
    require(
        receipt["inputs"] == {case.case_id: case_input_receipt(case) for case in CASES},
        "Phase 2 input receipt drift",
    )
    require(binary.is_file() and sha256_file(binary) == receipt["binary_sha256"], "Phase 2 binary drift")
    require(sha256_file(SCHEMA) == receipt["schema_sha256"], "schema digest drift")
    require(sha256_file(PLAN) == receipt["attempt_plan_sha256"], "attempt-plan digest drift")
    require(set(receipt["source_inventory"]) == set(SOURCE_INVENTORY), "Phase 2 source-inventory membership drift")
    for relative, digest in receipt["source_inventory"].items():
        require(sha256_file(ROOT / relative) == digest, f"Phase 2 source drift: {relative}")
    manifest_payload = tsv_bytes(MANIFEST_FIELDS, artifact_rows(ARTIFACT_ROOT))
    require(ARTIFACT_MANIFEST.read_bytes() == manifest_payload, "artifact manifest drift")
    require(sha256_bytes(manifest_payload) == receipt["artifact_manifest_sha256"], "artifact manifest receipt drift")
    require(sha256_file(SOURCE_DATA) == receipt["source_data_sha256"], "source-data receipt drift")
    rows = read_source_rows()
    require(len(rows) == len(CASES) * OBSERVATIONS * 2, "source-data row count drift")
    by_key = {(row["case_id"], int(row["repeat_id"]), row["trace_mode"]): row for row in rows}
    for case in CASES:
        require(sha256_file(ROOT / case.query) == case.query_file_sha256, f"{case.case_id}: query drift")
        require(sha256_file(ROOT / case.target) == case.target_file_sha256, f"{case.case_id}: target drift")
        fixture_prealign = json.loads(fixture_path(case, "prealign").read_text(encoding="utf-8"))
        fixture_call = json.loads(fixture_path(case, "alignment").read_text(encoding="utf-8"))
        validate_case_traces(case, fixture_prealign, fixture_call)
        require(sha256_file(fixture_path(case, "prealign")) == receipt["trace_digests"][case.case_id]["prealign_sha256"], f"{case.case_id}: prealign fixture digest drift")
        require(sha256_file(fixture_path(case, "alignment")) == receipt["trace_digests"][case.case_id]["mismatch_call_sha256"], f"{case.case_id}: call fixture digest drift")
        for repeat_id in range(OBSERVATIONS):
            off = by_key[(case.case_id, repeat_id, "trace_off")]
            on = by_key[(case.case_id, repeat_id, "trace_on")]
            for row in (off, on):
                require(row["returncode"] == "0" and row["timed_out"] == "0", "technical Phase 2 failure")
                require(row["output_equal_expected"] == "1" and row["paired_output_equal"] == "1", "authority digest mismatch")
                require(row["output_sha256"] == case.expected_output_sha256, "authority output digest drift")
                attempt_receipt = ROOT / row["artifact_receipt"]
                require(attempt_receipt.is_file() and not attempt_receipt.is_symlink(), "attempt receipt missing")
                attempt = json.loads(attempt_receipt.read_text(encoding="utf-8"))
                require(attempt["output_sha256"] == row["output_sha256"], "attempt/source output drift")
                require(attempt["inputs"] == case_input_receipt(case), "attempt input receipt drift")
            require(off["trace_file_count"] == "0", "trace-off emitted trace files")
            require(on["trace_file_count"] == "2", "trace-on filtered trace count drift")
            require(off["normalized_stdout_sha256"] == on["normalized_stdout_sha256"], "paired stdout drift")
            require(off["stderr_sha256"] == on["stderr_sha256"], "paired stderr drift")
            trace_root = ARTIFACT_ROOT / case.case_id / f"repeat{repeat_id:02d}" / "trace_on" / "trace"
            prealign_path, call_path, prealign, call = trace_records(trace_root, case)
            require(prealign_path.read_bytes() == fixture_path(case, "prealign").read_bytes(), "prealign trace nondeterminism")
            require(call_path.read_bytes() == fixture_path(case, "alignment").read_bytes(), "call trace nondeterminism")
            validate_case_traces(case, prealign, call)
    print("SSW-CUDA Phase 2 formal oracle evidence OK")


def smoke(binary: Path) -> None:
    validate_schema_document()
    require(binary.is_file() and os.access(binary, os.X_OK), "Phase 2 binary is not executable")
    with tempfile.TemporaryDirectory(prefix="ssw-oracle-smoke-") as temporary:
        root = Path(temporary)
        for case in CASES:
            off = run_attempt(binary, case, 0, "trace_off", root)
            on = run_attempt(binary, case, 0, "trace_on", root)
            require(off["output_sha256"] == on["output_sha256"], f"{case.case_id}: smoke trace changed output")
            require(
                off["normalized_stdout_sha256"] == on["normalized_stdout_sha256"],
                f"{case.case_id}: smoke trace changed stdout",
            )
            require(off["stderr_sha256"] == on["stderr_sha256"], f"{case.case_id}: smoke trace changed stderr")
    print("SSW-CUDA Phase 2 oracle smoke OK")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check-schema", action="store_true")
    action.add_argument("--smoke", action="store_true")
    action.add_argument("--run-formal", action="store_true")
    action.add_argument("--check-results", action="store_true")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    binary = args.binary.resolve()
    if args.check_schema:
        validate_schema_document()
        validate_plan()
        print("SSW-CUDA Phase 2 oracle schema and attempt plan OK")
    elif args.smoke:
        smoke(binary)
    elif args.run_formal:
        execute_formal(binary)
    elif args.check_results:
        check_results(binary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as error:
        raise SystemExit(str(error))
