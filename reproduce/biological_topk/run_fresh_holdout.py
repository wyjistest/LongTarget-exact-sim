#!/usr/bin/env python3
"""Preflight or execute the frozen biological Top-K fresh holdout attempts."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import freeze_fresh_holdout as frozen
except ImportError:  # pragma: no cover
    import freeze_fresh_holdout as frozen  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
MANIFEST_PATH = PAPER / "fresh_holdout_manifest.tsv"
ATTEMPT_PLAN_PATH = PAPER / "fresh_holdout_attempt_plan.tsv"
PLAN_PATH = PAPER / "fresh_holdout_plan.json"
MANIFEST_CHECKSUM_PATH = PAPER / "fresh_holdout_manifest.sha256"
RESOURCE_DECISION_PATH = PAPER / "fresh_holdout_resource_decision.json"
STATE_PATH = PAPER / "PROGRAM_STATE.json"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout"
PHASE3_COMMIT_MESSAGE = "repro: freeze fresh clustered TFO candidate-site holdout"
RUNTIME_ENVIRONMENT_G = {
    "FASIM_OUTPUT_MODE": "tfosorted",
    "FASIM_VERBOSE": "0",
    "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
    "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "256",
    "FASIM_ALIGN_GASAL2_STREAMS": "3",
    "FASIM_ALIGN_GASAL2_BATCH": "20000",
    "FASIM_ALIGN_GASAL2_CPU_TRACEBACK": "1",
    "FASIM_CANONICAL_HYBRID_V2": "1",
}
RUNTIME_ENVIRONMENT_A = {
    "FASIM_OUTPUT_MODE": "tfosorted",
    "FASIM_VERBOSE": "0",
}


class RunnerError(RuntimeError):
    """Raised for a fail-closed runner precondition or attempt failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RunnerError(message)


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    ).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: Any) -> None:
    atomic_write(path, canonical_json_bytes(value))


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_tsv(path: Path, fields: Sequence[str]) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == tuple(fields), f"TSV schema drift: {path}")
        rows = list(reader)
    require(all(tuple(row) == tuple(fields) and None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return rows


def fasta_records(path: Path) -> Iterable[tuple[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe FASTA source: {path}")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="ascii") as handle:
        header: str | None = None
        chunks: list[str] = []
        for raw in handle:
            line = raw.rstrip("\r\n")
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks).upper()
                header = line[1:]
                chunks = []
            elif line:
                require(header is not None, f"FASTA sequence precedes header: {path}")
                require(line == line.strip() and not any(character.isspace() for character in line), f"FASTA whitespace drift: {path}")
                chunks.append(line)
        if header is not None:
            yield header, "".join(chunks).upper()


def sequence_digest(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class FrozenInputs:
    queries: Mapping[str, str]
    chromosomes: Mapping[str, str]

    def target(self, row: Mapping[str, str]) -> str:
        chromosome = self.chromosomes[row["target_chromosome"]]
        start = int(row["target_region_start0"])
        end = int(row["target_region_end0"])
        return chromosome[start:end]


def load_inputs(manifest: Sequence[Mapping[str, str]]) -> FrozenInputs:
    selected_transcripts = {row["query_transcript_id"] for row in manifest}
    transcript_sequences: dict[str, str] = {}
    query_source = ROOT / next(iter({row["query_source_path"] for row in manifest}))
    for header, sequence in fasta_records(query_source):
        transcript_id = header.split("|", 1)[0]
        if transcript_id in selected_transcripts:
            require(transcript_id not in transcript_sequences, f"duplicate selected transcript in FASTA: {transcript_id}")
            transcript_sequences[transcript_id] = sequence
    require(set(transcript_sequences) == selected_transcripts, "selected query transcript missing from source FASTA")
    query_by_workload: dict[str, str] = {}
    for row in manifest:
        sequence = transcript_sequences[row["query_transcript_id"]]
        require(len(sequence) == int(row["query_sequence_length"]), f"query length drift: {row['workload_id']}")
        require(sequence_digest(sequence) == row["query_sequence_sha256"], f"query digest drift: {row['workload_id']}")
        require(not (set(sequence) - set("ACGT")), f"query alphabet drift: {row['workload_id']}")
        query_by_workload[row["workload_id"]] = sequence

    target_sources = {row["target_chromosome"]: ROOT / row["target_source_path"] for row in manifest}
    chromosomes: dict[str, str] = {}
    for chromosome, path in target_sources.items():
        records = list(fasta_records(path))
        require(len(records) == 1, f"target chromosome FASTA must have one record: {path}")
        require(records[0][0].split()[0] == chromosome, f"target chromosome identity drift: {path}")
        chromosomes[chromosome] = records[0][1]
    inputs = FrozenInputs(queries=query_by_workload, chromosomes=chromosomes)
    for row in manifest:
        target = inputs.target(row)
        require(len(target) == int(row["target_sequence_length"]), f"target length drift: {row['workload_id']}")
        require(sequence_digest(target) == row["target_sequence_sha256"], f"target digest drift: {row['workload_id']}")
        require(not (set(target) - set("ACGTN")), f"target alphabet drift: {row['workload_id']}")
    return inputs


def validate_frozen_plan() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any], FrozenInputs]:
    manifest = read_tsv(MANIFEST_PATH, frozen.MANIFEST_FIELDS)
    attempts = read_tsv(ATTEMPT_PLAN_PATH, frozen.ATTEMPT_FIELDS)
    plan = read_json(PLAN_PATH)
    decision = read_json(RESOURCE_DECISION_PATH)
    require(len(manifest) == 178 and len(attempts) == 368, "frozen plan count drift")
    checksum = MANIFEST_CHECKSUM_PATH.read_text(encoding="ascii").split()
    require(checksum == [sha256_file(MANIFEST_PATH), MANIFEST_PATH.name], "manifest checksum receipt drift")
    require(plan["output_sha256"][MANIFEST_PATH.relative_to(ROOT).as_posix()] == sha256_file(MANIFEST_PATH), "plan manifest digest drift")
    require(plan["output_sha256"][ATTEMPT_PLAN_PATH.relative_to(ROOT).as_posix()] == sha256_file(ATTEMPT_PLAN_PATH), "plan attempt digest drift")
    require(plan["resource_decision"] == "pass" and decision["phase_4_execution_authorized"] is True, "Phase 4 is not resource-authorized")
    frozen.validate_manifest(manifest, frozen.exclusion_indexes())

    expected_runner_sha = sha256_file(Path(__file__).resolve())
    require({row["runner_sha256"] for row in attempts} == {expected_runner_sha}, "attempt plan runner digest drift")
    require({row["analyzer_sha256"] for row in attempts} == {sha256_file(frozen.ANALYZER_PATH)}, "attempt plan analyzer digest drift")
    by_workload = {row["workload_id"]: row for row in manifest}
    by_validation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in attempts:
        require(row["workload_id"] in by_workload, "attempt references unknown workload")
        workload = by_workload[row["workload_id"]]
        for field in (
            "query_ordinal_namespace", "query_source_ordinal", "query_sequence_sha256",
            "target_ordinal_namespace", "target_source_ordinal", "target_sequence_sha256",
            "assembly", "target_coordinate_namespace", "query_extraction_recipe_id",
            "target_extraction_recipe_id", "input_pair_digest", "parameter_bundle_sha256",
        ):
            require(row[field] == workload[field], f"attempt/manifest identity drift: {row['attempt_id']} {field}")
        binary = ROOT / row["binary_path"]
        require(sha256_file(binary) == row["binary_sha256"], f"attempt binary digest drift: {row['attempt_id']}")
        require(sha256_file(ROOT / row["runtime_receipt_path"]) == row["runtime_receipt_sha256"], "runtime receipt drift")
        require(sha256_file(ROOT / row["contract_spec_path"]) == row["contract_spec_sha256"], "contract digest drift")
        require(sha256_file(ROOT / row["comparator_path"]) == row["comparator_sha256"], "comparator digest drift")
        require(row["retry_policy"] == "none" and row["comparison_policy"] == "offline_after_both_arms_terminal", "attempt isolation policy drift")
        by_validation[row["validation_instance_id"]].append(row)
    require(len(by_validation) == 184, "validation instance count drift")
    for validation_id, pair in by_validation.items():
        require(len(pair) == 2 and {row["arm"] for row in pair} == {"A", "G"}, f"invalid A/G pair: {validation_id}")
        require(len({row["input_pair_digest"] for row in pair}) == 1, f"A/G pair digest mismatch: {validation_id}")
        require(sorted(int(row["arm_launch_order"]) for row in pair) == [1, 2], f"A/G launch order drift: {validation_id}")
    inputs = load_inputs(manifest)
    return manifest, attempts, plan, inputs


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.strip() or f"git command failed: {' '.join(arguments)}")
    return completed.stdout.strip()


def execution_source_commit() -> str:
    head = git("rev-parse", "HEAD")
    require(git("log", "-1", "--format=%s", head) == PHASE3_COMMIT_MESSAGE, "formal execution requires the Phase 3 freeze commit at HEAD")
    committed_state = json.loads(git("show", f"{head}:paper/biological_topk/PROGRAM_STATE.json"))
    require(committed_state["phase_status"]["3"] == "pass" and committed_state["active_phase"] == 4, "committed Phase 3 state did not authorize Phase 4")
    live_state = read_json(STATE_PATH)
    require(live_state["phase_status"]["4"] == "active", "formal execution requires live Phase 4 active state")
    changed = set(git("status", "--porcelain=v1", "--untracked-files=all").splitlines())
    changed_paths = {line[3:] for line in changed if len(line) >= 4}
    allowlist_path = PAPER / "phase_4_change_allowlist.txt"
    if allowlist_path.is_file():
        allowed = {line.strip() for line in allowlist_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    else:
        allowed = {
            "paper/biological_topk/PROGRAM_STATE.json",
            "paper/biological_topk/STATUS.md",
            "paper/biological_topk/phase_4_start_receipt.json",
        }
    require(changed_paths <= allowed, f"formal execution checkout has out-of-scope changes: {sorted(changed_paths - allowed)}")
    for path in (Path(__file__).resolve(), MANIFEST_PATH, ATTEMPT_PLAN_PATH, PLAN_PATH):
        relative = path.relative_to(ROOT).as_posix()
        require(not git("diff", "--name-only", head, "--", relative), f"frozen execution source changed after Phase 3: {relative}")
    return head


def visible_gpu_inventory() -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,uuid,memory.total,compute_cap", "--format=csv,noheader,nounits"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, f"cannot query GPUs: {completed.stderr.strip()}")
    rows = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        require(len(fields) == 5, "unexpected GPU inventory row")
        rows.append(
            {
                "index": int(fields[0]),
                "name": fields[1],
                "uuid": fields[2],
                "memory_total_mib": int(fields[3]),
                "compute_capability": fields[4],
            }
        )
    require(len(rows) >= 2 and [row["index"] for row in rows[:2]] == [0, 1], "frozen two-GPU mapping unavailable")
    require(all(row["name"] == "NVIDIA GeForce RTX 4090" and row["memory_total_mib"] == frozen.MAX_GPU_MEMORY_MIB for row in rows[:2]), "GPU operating envelope drift")
    return rows[:2]


def initialize_snapshot(source_commit: str, attempts: Sequence[Mapping[str, str]]) -> Path:
    snapshot = ARTIFACT_ROOT / "execution-snapshot"
    if snapshot.is_dir():
        metadata = read_json(snapshot / "snapshot.json")
        require(metadata["source_commit"] == source_commit, "execution snapshot source commit drift")
        for relative, identity in metadata["files"].items():
            path = snapshot / relative
            require(path.stat().st_size == identity["size_bytes"] and sha256_file(path) == identity["sha256"], f"execution snapshot file drift: {relative}")
        return snapshot
    require(not ARTIFACT_ROOT.exists(), f"artifact root already exists without a complete snapshot: {ARTIFACT_ROOT}")
    ARTIFACT_ROOT.mkdir(parents=True)
    partial = ARTIFACT_ROOT / f".execution-snapshot.partial.{os.getpid()}"
    partial.mkdir()
    sources = (
        MANIFEST_PATH,
        MANIFEST_CHECKSUM_PATH,
        ATTEMPT_PLAN_PATH,
        PLAN_PATH,
        RESOURCE_DECISION_PATH,
        frozen.RUNTIME_RECEIPT_PATH,
        frozen.CONTRACT_PATH,
        frozen.COMPARATOR_PATH,
        Path(__file__).resolve(),
        frozen.ANALYZER_PATH,
        frozen.AUTHORITY_BINARY_PATH,
        frozen.CANDIDATE_BINARY_PATH,
    )
    names = [path.name for path in sources]
    require(len(names) == len(set(names)), "execution snapshot basenames collide")
    for source in sources:
        shutil.copy2(source, partial / source.name)
    files = {
        path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        for path in sorted(partial.iterdir())
        if path.is_file()
    }
    metadata = {
        "schema_version": 1,
        "source_commit": source_commit,
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "attempt_plan_sha256": sha256_file(ATTEMPT_PLAN_PATH),
        "attempt_count": len(attempts),
        "gpu_inventory": visible_gpu_inventory(),
        "files": files,
        "created_utc": utc_now(),
    }
    atomic_json(partial / "snapshot.json", metadata)
    os.replace(partial, snapshot)
    return snapshot


def fasta_bytes(identifier: str, sequence: str) -> bytes:
    lines = [f">{identifier}"] + [sequence[index : index + 80] for index in range(0, len(sequence), 80)]
    return ("\n".join(lines) + "\n").encode("ascii")


def output_file(output_root: Path) -> Path:
    paths = sorted(path for path in output_root.iterdir() if path.is_file() and path.name.endswith("TFOsorted"))
    require(len(paths) == 1, f"expected one TFOsorted output, found {len(paths)}")
    return paths[0]


def detect_oom(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(token in lowered for token in ("out of memory", "std::bad_alloc", "cuda_error_memory_allocation"))


def _limit_address_space(limit: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def run_process(command: list[str], environment: Mapping[str, str], root: Path, timeout_seconds: int, address_limit: int) -> dict[str, Any]:
    time_path = root / "time.txt"
    measured = ["/usr/bin/time", "-v", "-o", str(time_path), *command] if Path("/usr/bin/time").is_file() else command
    if measured is command:
        atomic_write(time_path, b"")
    started_utc = utc_now()
    started = time.perf_counter()
    process = subprocess.Popen(
        measured,
        cwd=ROOT,
        env=dict(environment),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        preexec_fn=lambda: _limit_address_space(address_limit),
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    wall_seconds = time.perf_counter() - started
    atomic_write(root / "stdout.log", stdout.encode("utf-8"))
    atomic_write(root / "stderr.log", stderr.encode("utf-8"))
    return {
        "started_utc": started_utc,
        "finished_utc": utc_now(),
        "wall_seconds": wall_seconds,
        "returncode": process.returncode,
        "timed_out": timed_out,
        "oom_detected": detect_oom(stderr),
        "stdout_sha256": sha256_file(root / "stdout.log"),
        "stderr_sha256": sha256_file(root / "stderr.log"),
        "time_sha256": sha256_file(time_path),
        "stderr": stderr,
    }


def input_identity(workload: Mapping[str, str]) -> dict[str, Any]:
    return frozen.manifest_identity(workload)


def input_receipt(
    *,
    row: Mapping[str, str],
    workload: Mapping[str, str],
    root: Path,
    output: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "receipt_kind": "biological_topk_input_receipt_v1",
        "workload_id": workload["workload_id"],
        "arm": row["arm"],
        "evidence_role": "fresh_concordance_promotion",
        "technical_success": True,
        "output_valid": True,
        "output_sha256": sha256_file(output),
        "query_fasta": (root / "inputs/query.fa").relative_to(root).as_posix(),
        "query_fasta_interval": [0, int(workload["query_sequence_length"])],
        "target_fasta": (root / "inputs/target.fa").relative_to(root).as_posix(),
        "target_fasta_interval": [0, int(workload["target_sequence_length"])],
        "target_region_start0": int(workload["target_region_start0"]),
        "chromosome_or_target_id": workload["target_chromosome"],
        "input_identity": input_identity(workload),
    }


def artifact_manifest(root: Path) -> bytes:
    fields = ("path", "size_bytes", "sha256")
    rows = []
    excluded = {"artifact-manifest.tsv", "artifact-manifest.sha256", "attempt-complete.json"}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"attempt artifact is a symlink: {path}")
        if path.is_file() and path.relative_to(root).as_posix() not in excluded:
            rows.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def validate_completed_attempt(destination: Path, row: Mapping[str, str]) -> dict[str, Any]:
    receipt = read_json(destination / "attempt-complete.json")
    require(receipt["attempt_id"] == row["attempt_id"] and receipt["status"] in {"success", "technical_failure"}, "attempt receipt identity/status drift")
    require(receipt["attempt_config_sha256"] == canonical_digest(dict(row)), "attempt receipt config drift")
    require(receipt["comparison_started"] is False, "runner performed a comparison")
    manifest_path = destination / "artifact-manifest.tsv"
    checksum = (destination / "artifact-manifest.sha256").read_text(encoding="ascii").split()
    require(checksum == [sha256_file(manifest_path), manifest_path.name], "attempt artifact checksum drift")
    return receipt


def execute_attempt(
    row: Mapping[str, str],
    workload: Mapping[str, str],
    inputs: FrozenInputs,
    snapshot: Path,
    source_commit: str,
) -> dict[str, Any]:
    destination = ROOT / row["artifact_root"]
    if destination.is_dir():
        receipt = validate_completed_attempt(destination, row)
        if receipt["status"] != "success":
            raise RunnerError(f"attempt is already terminal failure and cannot be retried: {row['attempt_id']}")
        return receipt
    stale = sorted(ARTIFACT_ROOT.glob(f".{row['attempt_id']}.partial.*"))
    require(not stale, f"stale partial attempt is retained and cannot be retried: {row['attempt_id']}")
    partial = ARTIFACT_ROOT / f".{row['attempt_id']}.partial.{os.getpid()}.{row['worker_index']}"
    partial.mkdir()
    (partial / "inputs").mkdir()
    (partial / "output").mkdir()
    query_sequence = inputs.queries[workload["workload_id"]]
    target_sequence = inputs.target(workload)
    atomic_write(partial / "inputs/query.fa", fasta_bytes(f"{workload['workload_id']}_query", query_sequence))
    atomic_write(partial / "inputs/target.fa", fasta_bytes(f"{workload['workload_id']}_{workload['target_chromosome']}", target_sequence))
    require(sequence_digest(query_sequence) == row["query_sequence_sha256"], "attempt query digest drift")
    require(sequence_digest(target_sequence) == row["target_sequence_sha256"], "attempt target digest drift")
    binary = snapshot / Path(row["binary_path"]).name
    require(sha256_file(binary) == row["binary_sha256"], "snapshot binary digest drift")
    command = [
        "taskset", "-c", row["cpu_affinity"], str(binary),
        "-f1", str(partial / "inputs/target.fa"),
        "-f2", str(partial / "inputs/query.fa"),
        "-r", "0", "-O", str(partial / "output"),
    ]
    environment = {
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
        "OMP_NUM_THREADS": "10",
    }
    explicit = dict(RUNTIME_ENVIRONMENT_A if row["arm"] == "A" else RUNTIME_ENVIRONMENT_G)
    if row["arm"] == "A":
        explicit["CUDA_VISIBLE_DEVICES"] = ""
    else:
        explicit["CUDA_VISIBLE_DEVICES"] = row["gpu_physical_index"]
        explicit["FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH"] = str(partial / "telemetry.json")
    environment.update(explicit)
    atomic_json(
        partial / "attempt-config.json",
        {
            "attempt": dict(row),
            "attempt_config_sha256": canonical_digest(dict(row)),
            "input_identity": input_identity(workload),
            "command": command,
            "explicit_environment": explicit,
            "source_commit": source_commit,
        },
    )
    execution = run_process(
        command,
        environment,
        partial,
        int(row["timeout_seconds"]),
        int(row["max_address_space_bytes"]),
    )
    technical_success = (
        execution["returncode"] == 0
        and execution["timed_out"] is False
        and execution["oom_detected"] is False
    )
    output: Path | None = None
    failure_reason: str | None = None
    fallback_used = False
    telemetry_summary: dict[str, Any] | None = None
    if technical_success:
        try:
            output = output_file(partial / "output")
            if row["arm"] == "G":
                sys.path.insert(0, str(ROOT / "scripts"))
                from canonical_hybrid_v2_telemetry import validate_attempt as validate_telemetry

                telemetry_summary = validate_telemetry(
                    partial / "telemetry.json",
                    output,
                    str(execution["stderr"]),
                )
                fallback_used = int(telemetry_summary.get("fallbacks", -1)) != 0
                technical_success = not fallback_used
                if fallback_used:
                    failure_reason = "unexpected_fallback"
        except Exception as error:  # Output/telemetry validation is a technical gate.
            technical_success = False
            failure_reason = f"output_validation:{type(error).__name__}:{error}"
    if not technical_success and failure_reason is None:
        if execution["timed_out"]:
            failure_reason = "timeout"
        elif execution["oom_detected"]:
            failure_reason = "oom"
        elif execution["returncode"] != 0:
            failure_reason = f"nonzero_exit_{execution['returncode']}"
        else:
            failure_reason = "missing_or_invalid_output"

    canonical_receipt_path: str | None = None
    output_sha: str | None = None
    if technical_success and output is not None:
        receipt_value = input_receipt(row=row, workload=workload, root=partial, output=output)
        atomic_json(partial / "input-receipt.json", receipt_value)
        canonical_receipt_path = "input-receipt.json"
        output_sha = sha256_file(output)
    if telemetry_summary is not None:
        atomic_json(partial / "telemetry-summary.json", telemetry_summary)

    receipt = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "workload_id": row["workload_id"],
        "validation_instance_id": row["validation_instance_id"],
        "repeat_id": int(row["repeat_id"]),
        "primary_instance": row["primary_instance"] == "1",
        "arm": row["arm"],
        "evidence_role": "fresh_concordance_promotion",
        "query_ordinal_namespace": row["query_ordinal_namespace"],
        "query_source_ordinal": row["query_source_ordinal"],
        "query_sha256": row["query_sequence_sha256"],
        "target_ordinal_namespace": row["target_ordinal_namespace"],
        "target_source_ordinal": row["target_source_ordinal"],
        "target_sha256": row["target_sequence_sha256"],
        "assembly": row["assembly"],
        "coordinate_namespace": row["target_coordinate_namespace"],
        "input_pair_digest": row["input_pair_digest"],
        "parameter_bundle_sha256": row["parameter_bundle_sha256"],
        "status": "success" if technical_success else "technical_failure",
        "failure_reason": failure_reason,
        "command": command,
        "explicit_environment": explicit,
        "source_commit": source_commit,
        "binary_sha256": row["binary_sha256"],
        "attempt_config_sha256": canonical_digest(dict(row)),
        "output_path": None if output is None else output.relative_to(partial).as_posix(),
        "output_sha256": output_sha,
        "input_receipt_path": canonical_receipt_path,
        "wall_seconds": execution["wall_seconds"],
        "returncode": execution["returncode"],
        "timed_out": execution["timed_out"],
        "oom_detected": execution["oom_detected"],
        "fallback_used": fallback_used,
        "telemetry_summary": telemetry_summary,
        "comparison_started": False,
        "retry_policy": "none",
        "replacement_retry_allowed": False,
        "completed_utc": utc_now(),
    }
    execution.pop("stderr", None)
    receipt["execution"] = execution
    artifact_bytes = artifact_manifest(partial)
    atomic_write(partial / "artifact-manifest.tsv", artifact_bytes)
    artifact_sha = sha256_file(partial / "artifact-manifest.tsv")
    atomic_write(partial / "artifact-manifest.sha256", f"{artifact_sha}  artifact-manifest.tsv\n".encode("ascii"))
    receipt["artifact_manifest_sha256"] = artifact_sha
    atomic_json(partial / "attempt-complete.json", receipt)
    os.replace(partial, destination)
    validated = validate_completed_attempt(destination, row)
    if validated["status"] != "success":
        raise RunnerError(f"attempt failed and was retained without retry: {row['attempt_id']} ({failure_reason})")
    return validated


def rebuild_summary(attempts: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    receipts = []
    missing = []
    for row in attempts:
        destination = ROOT / row["artifact_root"]
        if (destination / "attempt-complete.json").is_file():
            receipts.append(validate_completed_attempt(destination, row))
        else:
            missing.append(row["attempt_id"])
    summary = {
        "schema_version": 1,
        "status": (
            "complete_success" if len(receipts) == len(attempts) and all(receipt["status"] == "success" for receipt in receipts)
            else "complete_with_technical_failure" if len(receipts) == len(attempts)
            else "in_progress_or_interrupted"
        ),
        "planned_attempt_count": len(attempts),
        "terminal_attempt_count": len(receipts),
        "successful_attempt_count": sum(receipt["status"] == "success" for receipt in receipts),
        "technical_failure_count": sum(receipt["status"] != "success" for receipt in receipts),
        "missing_attempt_ids": missing,
        "comparison_started": False,
        "updated_utc": utc_now(),
    }
    atomic_json(ARTIFACT_ROOT / "run-summary.json", summary)
    return summary


def execute(attempts: Sequence[dict[str, str]], manifest: Sequence[dict[str, str]], inputs: FrozenInputs) -> dict[str, Any]:
    source_commit = execution_source_commit()
    snapshot = initialize_snapshot(source_commit, attempts)
    by_workload = {row["workload_id"]: row for row in manifest}
    by_validation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in attempts:
        by_validation[row["validation_instance_id"]].append(row)
    worker_instances: dict[int, list[list[dict[str, str]]]] = {0: [], 1: []}
    for validation_id, pair in sorted(by_validation.items(), key=lambda item: min(int(row["execution_index"]) for row in item[1])):
        del validation_id
        ordered = sorted(pair, key=lambda row: int(row["arm_launch_order"]))
        worker = int(ordered[0]["worker_index"])
        require(all(int(row["worker_index"]) == worker for row in ordered), "paired attempt worker drift")
        worker_instances[worker].append(ordered)

    def run_worker(worker: int) -> int:
        completed = 0
        for pair in worker_instances[worker]:
            for row in pair:
                execute_attempt(row, by_workload[row["workload_id"]], inputs, snapshot, source_commit)
                completed += 1
                rebuild_summary(attempts)
        return completed

    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="biological-topk") as executor:
            futures = [executor.submit(run_worker, worker) for worker in (0, 1)]
            completed = sum(future.result() for future in futures)
    except Exception:
        rebuild_summary(attempts)
        raise
    require(completed == len(attempts), "runner did not execute every frozen attempt")
    summary = rebuild_summary(attempts)
    require(summary["status"] == "complete_success", "fresh holdout execution did not complete cleanly")
    return summary


def preflight_summary(manifest: Sequence[Mapping[str, str]], attempts: Sequence[Mapping[str, str]], plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "preflight_pass",
        "read_only": True,
        "scientific_output_created": False,
        "primary_workload_count": len(manifest),
        "validation_instance_count": len({row["validation_instance_id"] for row in attempts}),
        "attempt_count": len(attempts),
        "arm_counts": dict(Counter(row["arm"] for row in attempts)),
        "pair_order_counts": {key: value // 2 for key, value in Counter(row["pair_order"] for row in attempts).items()},
        "runtime_binding": plan["runtime_binding"],
        "artifact_root_exists": ARTIFACT_ROOT.exists(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true", help="perform read-only validation")
    modes.add_argument("--execute", action="store_true", help="execute the frozen attempts")
    parser.add_argument("--artifact-root", type=Path, default=ARTIFACT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        require(args.artifact_root.resolve() == ARTIFACT_ROOT.resolve(), "artifact root differs from the frozen path")
        manifest, attempts, plan, inputs = validate_frozen_plan()
        result = preflight_summary(manifest, attempts, plan) if args.preflight else execute(attempts, manifest, inputs)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (RunnerError, frozen.FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"biological Top-K fresh holdout runner failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("_")]
