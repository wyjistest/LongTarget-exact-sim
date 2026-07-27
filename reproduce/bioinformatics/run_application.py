#!/usr/bin/env python3
"""Plan and execute the preregistered Bioinformatics Phase 3 application."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from collect_fasim_gasal2_paper_run import gpu_metrics, max_rss_kb  # noqa: E402
from gasal2_longtarget import SCHEMA_PATH as RUN_REPORT_SCHEMA_PATH  # noqa: E402
from gasal2_longtarget import validate_schema_value  # noqa: E402
from run_fasim_gasal2_paper_benchmarks import GpuSampler  # noqa: E402


RUNNER_PATH = Path(__file__).resolve()
MANIFEST_PATH = ROOT / "paper/bioinformatics/application_manifest.tsv"
MANIFEST_CHECKSUM_PATH = ROOT / "paper/bioinformatics/application_manifest.sha256"
PLAN_PATH = ROOT / "paper/bioinformatics/application_attempt_plan.tsv"
PLAN_CHECKSUM_PATH = ROOT / "paper/bioinformatics/application_attempt_plan.sha256"
SUBSET_PATH = ROOT / "paper/bioinformatics/application_repeat_subset.tsv"
DECISION_PATH = ROOT / "paper/bioinformatics/phase3_preexecution_decision.json"
PILOT_RECEIPT_PATH = ROOT / "paper/bioinformatics/application_pilot_receipt.json"
PILOT_ARTIFACTS_PATH = ROOT / "paper/bioinformatics/application_pilot_artifacts.tsv"
PILOT_ARTIFACTS_CHECKSUM_PATH = (
    ROOT / "paper/bioinformatics/application_pilot_artifacts.sha256"
)
RESOURCE_PROJECTION_PATH = (
    ROOT / "paper/bioinformatics/application_resource_projection.json"
)
POSTPILOT_DECISION_PATH = ROOT / "paper/bioinformatics/phase3_postpilot_decision.json"
CANONICAL_ARTIFACT_ROOT = (
    ROOT / ".paper-artifacts/bioinformatics-phase3-application-v1"
)

FREEZE_ID = "bioinformatics-phase3-application-v1-e8c5441c"
MANIFEST_SHA256 = "e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
SELECTION_SEED = "gasal2-longtarget-phase3-application-v1-20260724"
PHASE2_DECISION = "verified_only_contract"
PAPER_RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
BACKEND_TIMEOUT_SECONDS = 3600
TOTAL_BUDGET_SECONDS = 86400
WORKER_COUNT = 2
GPU_ASSIGNMENT = "worker0=GPU0;worker1=GPU1;pair_index_mod_2"
RETRY_POLICY = "none"
PLAN_STATUS = "preregistered_not_run"
PROJECTION_CONSERVATISM_FACTOR = 1.25
PILOT_QUERY_ID = "aq001"
PILOT_TARGET_ID = "at0001"
REPEAT_COUNT = 6
REPEAT_QUERY_COUNT = 10
REPEAT_TARGETS_PER_CHROMOSOME = 10

MANIFEST_FIELDS = (
    "record_id",
    "record_role",
    "source_release",
    "assembly",
    "original_gene_id",
    "original_gene_name",
    "original_transcript_id",
    "selection_rule",
    "sequence_length",
    "chromosome",
    "strand",
    "tss",
    "region_start",
    "region_end",
    "sequence_sha256",
    "file_sha256",
    "path",
    "license_note",
    "split",
    "status",
)
SUBSET_FIELDS = (
    "record_role",
    "subset_order",
    "record_id",
    "chromosome",
    "sequence_length",
    "sequence_sha256",
    "file_sha256",
    "path",
    "selection_rule",
)
PLAN_FIELDS = (
    "attempt_id",
    "execution_stage",
    "arm",
    "mode",
    "scope",
    "query_id",
    "target_id",
    "repeat_id",
    "order",
    "contract",
    "manifest_sha256",
    "runner_commit",
    "runner_sha256",
    "worker_count",
    "gpu_assignment",
    "backend_timeout_seconds",
    "total_budget_seconds",
    "retry_policy",
    "claim_role",
    "formal_source_data",
    "expected_artifact_root",
    "command_template",
    "status",
)
ARM_SPECS = {
    "A": ("cpu-authority", "all-ranked-top5"),
    "B": ("fast-experimental", "auto"),
    "C": ("safe", "all-ranked-top5"),
}
ALLOWED_POST_PILOT_DECISIONS = (
    "continue_full_descriptive_negative",
    "stop_after_pilot_futility",
    "blocked_by_operational_failure",
    "blocked_by_fixed_budget",
)
RUN_REPORT_SCHEMA = json.loads(RUN_REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ToolPaths:
    workflow: Path = ROOT / "scripts/gasal2_longtarget.py"
    comparator: Path = ROOT / "scripts/compare_fasim_segmented_contract.py"
    authority_binary: Path = ROOT / "fasim_longtarget_x86"
    candidate_binary: Path = ROOT / "fasim_longtarget_gasal2"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, payload: object) -> None:
    atomic_bytes(path, canonical_json_bytes(payload))


def tsv_bytes(fieldnames: Sequence[str], rows: Iterable[dict[str, object]]) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(fieldnames),
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def write_tsv(
    path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, object]]
) -> None:
    atomic_bytes(path, tsv_bytes(fieldnames, rows))


def read_tsv(path: Path, expected_fields: Sequence[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(
            tuple(reader.fieldnames or ()) == tuple(expected_fields),
            f"TSV schema drift: {path}",
        )
        rows = list(reader)
    require(
        all(
            tuple(row) == tuple(expected_fields)
            and all(value is not None for value in row.values())
            for row in rows
        ),
        f"malformed TSV row: {path}",
    )
    return rows


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(
        completed.returncode == 0,
        f"Git command failed: {' '.join(arguments)}: {completed.stderr.strip()}",
    )
    return completed.stdout.strip()


def git_head() -> str:
    value = git_output("rev-parse", "HEAD")
    require(
        len(value) == 40 and set(value) <= set("0123456789abcdef"),
        "invalid Git HEAD",
    )
    return value


def checkout_changes() -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--ignored=no",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if completed.returncode != 0:
        return [f"git_status_returncode={completed.returncode}"]
    return completed.stdout.splitlines()


def _load_single_fasta(path: Path) -> str:
    sequence_parts: list[str] = []
    header_count = 0
    for raw in path.read_text(encoding="ascii").splitlines():
        if raw.startswith(">"):
            header_count += 1
        elif raw:
            sequence_parts.append(raw.strip().upper())
    require(header_count == 1, f"expected one FASTA record: {path}")
    sequence = "".join(sequence_parts)
    require(sequence and set(sequence) <= set("ACGT"), f"invalid FASTA sequence: {path}")
    return sequence


def load_application_manifest(
    path: Path = MANIFEST_PATH, *, verify_files: bool = True
) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), "application manifest is missing or unsafe")
    observed_digest = sha256_file(path)
    if path.resolve() == MANIFEST_PATH.resolve():
        require(observed_digest == MANIFEST_SHA256, "application manifest SHA-256 drift")
        checksum_fields = MANIFEST_CHECKSUM_PATH.read_text(encoding="ascii").split()
        require(
            checksum_fields and checksum_fields[0] == MANIFEST_SHA256,
            "application manifest checksum receipt drift",
        )
    rows = read_tsv(path, MANIFEST_FIELDS)
    require(len(rows) == 718, "application manifest must contain 718 records")
    require(len({row["record_id"] for row in rows}) == len(rows), "duplicate application record ID")
    queries = [row for row in rows if row["record_role"] == "query"]
    targets = [row for row in rows if row["record_role"] == "target"]
    require(len(queries) == 50 and len(targets) == 668, "application panel cardinality drift")
    for row in rows:
        require(row["source_release"] == "GENCODE v49", "source release drift")
        require(row["assembly"] == "GRCh38", "assembly drift")
        require(row["split"] == "application", "application split drift")
        require(row["status"] == PLAN_STATUS, "application input status drift")
        require(len(row["file_sha256"]) == 64, "invalid input file digest")
        require(len(row["sequence_sha256"]) == 64, "invalid input sequence digest")
        if verify_files:
            input_path = ROOT / row["path"]
            require(input_path.is_file() and not input_path.is_symlink(), f"missing input: {row['path']}")
            require(sha256_file(input_path) == row["file_sha256"], f"input file digest drift: {row['record_id']}")
            sequence = _load_single_fasta(input_path)
            require(len(sequence) == int(row["sequence_length"]), f"input length drift: {row['record_id']}")
            require(
                hashlib.sha256(sequence.encode("ascii")).hexdigest()
                == row["sequence_sha256"],
                f"input sequence digest drift: {row['record_id']}",
            )
    return rows


def _query_subset(queries: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(queries, key=lambda row: (int(row["sequence_length"]), row["record_id"]))
    indexes = [round(index * (len(ordered) - 1) / (REPEAT_QUERY_COUNT - 1)) for index in range(REPEAT_QUERY_COUNT)]
    require(len(set(indexes)) == REPEAT_QUERY_COUNT, "query quantile selection is not unique")
    return [ordered[index] for index in indexes]


def _target_subset(targets: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for chromosome in ("chr21", "chr22"):
        chromosome_rows = [row for row in targets if row["chromosome"] == chromosome]

        def selection_key(row: dict[str, str]) -> tuple[str, str]:
            identity = (
                f"{SELECTION_SEED}|phase3-repeat-target|{row['record_id']}|"
                f"{row['sequence_sha256']}"
            )
            return hashlib.sha256(identity.encode("ascii")).hexdigest(), row["record_id"]

        selected.extend(sorted(chromosome_rows, key=selection_key)[:REPEAT_TARGETS_PER_CHROMOSOME])
    return selected


def expected_subset_rows(manifest_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    queries = _query_subset([row for row in manifest_rows if row["record_role"] == "query"])
    targets = _target_subset([row for row in manifest_rows if row["record_role"] == "target"])
    rows: list[dict[str, object]] = []
    query_rule = "ten query-length quantiles from frozen metadata; ties by record_id"
    target_rule = "first ten per chromosome by SHA256(selection_seed|phase3-repeat-target|record_id|sequence_sha256)"
    for index, row in enumerate(queries, start=1):
        rows.append(
            {
                "record_role": "query",
                "subset_order": index,
                "record_id": row["record_id"],
                "chromosome": "NA",
                "sequence_length": row["sequence_length"],
                "sequence_sha256": row["sequence_sha256"],
                "file_sha256": row["file_sha256"],
                "path": row["path"],
                "selection_rule": query_rule,
            }
        )
    for index, row in enumerate(targets, start=1):
        rows.append(
            {
                "record_role": "target",
                "subset_order": index,
                "record_id": row["record_id"],
                "chromosome": row["chromosome"],
                "sequence_length": row["sequence_length"],
                "sequence_sha256": row["sequence_sha256"],
                "file_sha256": row["file_sha256"],
                "path": row["path"],
                "selection_rule": target_rule,
            }
        )
    return rows


def _command_template(mode: str, contract: str) -> str:
    return (
        "python3 scripts/gasal2_longtarget.py"
        f" --mode {mode} --contract {contract}"
        " --query {query_path} --target {target_path}"
        " --output {pair_output} --report {pair_run_report}"
        " --rule 0 --triplex-preset normal --top-k 5"
        " --assembly GRCh38 --annotation-release 'GENCODE v49'"
        f" --timeout {BACKEND_TIMEOUT_SECONDS}"
        " --authority-binary fasim_longtarget_x86"
        " --candidate-binary fasim_longtarget_gasal2"
        " --comparator scripts/compare_fasim_segmented_contract.py"
    )


def _plan_row(
    *,
    attempt_id: str,
    stage: str,
    arm: str,
    scope: str,
    query_id: str,
    target_id: str,
    repeat_id: int,
    order: int,
    runner_commit: str,
    runner_sha256: str,
) -> dict[str, object]:
    mode, contract = ARM_SPECS[arm]
    formal = stage != "pilot"
    claim_role = "operational_only" if not formal else "descriptive_negative_only"
    root_part = {
        "pilot": "pilot",
        "formal_full": "formal-full",
        "formal_repeat": "formal-repeat",
    }[stage]
    return {
        "attempt_id": attempt_id,
        "execution_stage": stage,
        "arm": arm,
        "mode": mode,
        "scope": scope,
        "query_id": query_id,
        "target_id": target_id,
        "repeat_id": repeat_id,
        "order": order,
        "contract": contract,
        "manifest_sha256": MANIFEST_SHA256,
        "runner_commit": runner_commit,
        "runner_sha256": runner_sha256,
        "worker_count": WORKER_COUNT,
        "gpu_assignment": GPU_ASSIGNMENT,
        "backend_timeout_seconds": BACKEND_TIMEOUT_SECONDS,
        "total_budget_seconds": TOTAL_BUDGET_SECONDS,
        "retry_policy": RETRY_POLICY,
        "claim_role": claim_role,
        "formal_source_data": 1 if formal else 0,
        "expected_artifact_root": str(
            Path(".paper-artifacts/bioinformatics-phase3-application-v1")
            / root_part
            / attempt_id
        ),
        "command_template": _command_template(mode, contract),
        "status": PLAN_STATUS,
    }


def expected_plan_rows(runner_commit: str, runner_sha256: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for order, arm in enumerate(("A", "B", "C"), start=1):
        rows.append(
            _plan_row(
                attempt_id=f"p3pilot_{arm.lower()}_{PILOT_QUERY_ID}_{PILOT_TARGET_ID}",
                stage="pilot",
                arm=arm,
                scope=f"{PILOT_QUERY_ID}_{PILOT_TARGET_ID}",
                query_id=PILOT_QUERY_ID,
                target_id=PILOT_TARGET_ID,
                repeat_id=0,
                order=order,
                runner_commit=runner_commit,
                runner_sha256=runner_sha256,
            )
        )
    for order, arm in enumerate(("A", "B", "C"), start=1):
        rows.append(
            _plan_row(
                attempt_id=f"p3full_{arm.lower()}",
                stage="formal_full",
                arm=arm,
                scope="50x668",
                query_id="ALL_50",
                target_id="ALL_668",
                repeat_id=0,
                order=order,
                runner_commit=runner_commit,
                runner_sha256=runner_sha256,
            )
        )
    for repeat_id in range(REPEAT_COUNT):
        arm_order = ("A", "B", "C") if repeat_id % 2 == 0 else ("C", "B", "A")
        for order, arm in enumerate(arm_order, start=1):
            rows.append(
                _plan_row(
                    attempt_id=f"p3repeat_r{repeat_id:02d}_{arm.lower()}",
                    stage="formal_repeat",
                    arm=arm,
                    scope="10x20",
                    query_id="SUBSET_10",
                    target_id="SUBSET_20",
                    repeat_id=repeat_id,
                    order=order,
                    runner_commit=runner_commit,
                    runner_sha256=runner_sha256,
                )
            )
    require(len(rows) == 24, "Phase 3 plan must contain 24 block attempts")
    return rows


def expected_preexecution_decision(
    *,
    runner_commit: str,
    runner_sha256: str,
    plan_sha256: str,
    subset_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "preexecution_frozen",
        "freeze_id": FREEZE_ID,
        "manifest_sha256": MANIFEST_SHA256,
        "attempt_plan_sha256": plan_sha256,
        "repeat_subset_sha256": subset_sha256,
        "runner_commit": runner_commit,
        "runner_sha256": runner_sha256,
        "phase2_decision": PHASE2_DECISION,
        "b3_threshold_changed": False,
        "b3_safe_speedup_threshold": 10.0,
        "b3_wall_reduction_threshold_seconds": 28800,
        "b3_capacity_gain_threshold": 10.0,
        "safe_pipeline_definition": ["candidate", "complete_authority", "comparison"],
        "safe_pipeline_execution_order": ["candidate", "complete_authority", "comparison"],
        "safe_timing_identity": "T_C=T_candidate+T_authority+T_compare+wrapper_overhead",
        "b3_promotion_feasibility": "structurally_unreachable_under_verified_only_v1",
        "b3_reason": (
            "sequential safe C includes the complete authority A workload plus "
            "candidate, comparison, and nonnegative wrapper overhead"
        ),
        "pilot_scope": f"{PILOT_QUERY_ID}_{PILOT_TARGET_ID}",
        "pilot_attempt_ids": [
            f"p3pilot_{arm.lower()}_{PILOT_QUERY_ID}_{PILOT_TARGET_ID}"
            for arm in ("A", "B", "C")
        ],
        "pilot_role": "operational_and_resource_characterization_only",
        "pilot_can_promote_b3": False,
        "pilot_can_rescue_b3": False,
        "pilot_can_change_panel": False,
        "pilot_can_change_parameters": False,
        "pilot_can_change_scale": False,
        "pilot_can_change_claim_boundary": False,
        "candidate_only_can_be_reported_as_safe_acceleration": False,
        "formal_execution_started": False,
        "full_run_decision": "pending_fixed_pilot",
        "allowed_post_pilot_decisions": list(ALLOWED_POST_PILOT_DECISIONS),
        "postpilot_decision_precedence": [
            "blocked_by_operational_failure",
            "blocked_by_fixed_budget",
            "stop_after_pilot_futility",
        ],
        "continue_full_descriptive_negative_requires_owner_authorization": True,
        "resource_projection_method_version": "pilot_max_pair_or_sequence_worker_scale_v1",
        "resource_projection_conservatism_factor": PROJECTION_CONSERVATISM_FACTOR,
        "lower_substitute_threshold_allowed": False,
    }


def generate_frozen_plan(runner_commit: str) -> dict[str, str]:
    require(
        len(runner_commit) == 40 and set(runner_commit) <= set("0123456789abcdef"),
        "--runner-commit must be a full lowercase Git SHA",
    )
    require(git_head() == runner_commit, "plan generation must run at the runner source commit")
    require(not checkout_changes(), "plan generation requires a clean checkout")
    runner_sha256 = sha256_file(RUNNER_PATH)
    manifest_rows = load_application_manifest()
    subset_rows = expected_subset_rows(manifest_rows)
    subset_payload = tsv_bytes(SUBSET_FIELDS, subset_rows)
    plan_rows = expected_plan_rows(runner_commit, runner_sha256)
    plan_payload = tsv_bytes(PLAN_FIELDS, plan_rows)
    plan_sha256 = hashlib.sha256(plan_payload).hexdigest()
    subset_sha256 = hashlib.sha256(subset_payload).hexdigest()
    decision = expected_preexecution_decision(
        runner_commit=runner_commit,
        runner_sha256=runner_sha256,
        plan_sha256=plan_sha256,
        subset_sha256=subset_sha256,
    )
    atomic_bytes(SUBSET_PATH, subset_payload)
    atomic_bytes(PLAN_PATH, plan_payload)
    atomic_bytes(
        PLAN_CHECKSUM_PATH,
        f"{plan_sha256}  {PLAN_PATH.name}\n".encode("ascii"),
    )
    write_json(DECISION_PATH, decision)
    return {
        "runner_commit": runner_commit,
        "runner_sha256": runner_sha256,
        "plan_sha256": plan_sha256,
        "subset_sha256": subset_sha256,
    }


def load_and_validate_plan(*, verify_inputs: bool = True) -> tuple[list[dict[str, str]], dict[str, object]]:
    for path in (PLAN_PATH, PLAN_CHECKSUM_PATH, SUBSET_PATH, DECISION_PATH):
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe preexecution artifact: {path}")
    rows = read_tsv(PLAN_PATH, PLAN_FIELDS)
    require(len(rows) == 24, "attempt plan row count drift")
    runner_commits = {row["runner_commit"] for row in rows}
    runner_digests = {row["runner_sha256"] for row in rows}
    require(len(runner_commits) == 1 and len(runner_digests) == 1, "attempt plan runner binding drift")
    runner_commit = next(iter(runner_commits))
    runner_sha256 = next(iter(runner_digests))
    require(sha256_file(RUNNER_PATH) == runner_sha256, "runner SHA-256 drift")
    expected_rows = [
        {field: str(value) for field, value in row.items()}
        for row in expected_plan_rows(runner_commit, runner_sha256)
    ]
    require(rows == expected_rows, "attempt plan semantic drift")
    plan_sha256 = sha256_file(PLAN_PATH)
    checksum_fields = PLAN_CHECKSUM_PATH.read_text(encoding="ascii").split()
    require(
        checksum_fields == [plan_sha256, PLAN_PATH.name],
        "attempt plan checksum receipt drift",
    )
    manifest_rows = load_application_manifest(verify_files=verify_inputs)
    subset_rows = read_tsv(SUBSET_PATH, SUBSET_FIELDS)
    expected_subset = [
        {field: str(value) for field, value in row.items()}
        for row in expected_subset_rows(manifest_rows)
    ]
    require(subset_rows == expected_subset, "repeat subset semantic drift")
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    require(isinstance(decision, dict), "preexecution decision must be an object")
    expected_decision = expected_preexecution_decision(
        runner_commit=runner_commit,
        runner_sha256=runner_sha256,
        plan_sha256=plan_sha256,
        subset_sha256=sha256_file(SUBSET_PATH),
    )
    require(decision == expected_decision, "preexecution decision semantic drift")
    require(
        canonical_json_bytes(decision) == DECISION_PATH.read_bytes(),
        "preexecution decision is not canonical JSON",
    )
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", runner_commit, "HEAD"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, "runner source commit is not an ancestor of HEAD")
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff",
            "--quiet",
            runner_commit,
            "HEAD",
            "--",
            str(RUNNER_PATH.relative_to(ROOT)),
        ],
        check=False,
        timeout=30,
    )
    require(completed.returncode == 0, "runner changed after its pinned source commit")
    return rows, decision


def tool_identity(tools: ToolPaths) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name in ("workflow", "comparator", "authority_binary", "candidate_binary"):
        path = getattr(tools, name)
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe tool: {name}")
        result[name] = {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return result


def visible_gpu_inventory() -> list[dict[str, object]]:
    if os.environ.get("PHASE3_APPLICATION_TEST_MODE") == "1":
        return [
            {"physical_index": 0, "name": "test-gpu-0", "uuid": "TEST-0"},
            {"physical_index": 1, "name": "test-gpu-1", "uuid": "TEST-1"},
        ]
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, f"cannot query GPUs: {completed.stderr.strip()}")
    rows: list[dict[str, object]] = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        require(len(fields) == 5, "unexpected nvidia-smi inventory row")
        rows.append(
            {
                "physical_index": int(fields[0]),
                "name": fields[1],
                "uuid": fields[2],
                "memory_total_mib": int(fields[3]),
                "compute_capability": fields[4],
            }
        )
    require([row["physical_index"] for row in rows[:2]] == [0, 1], "GPU 0 and GPU 1 are required")
    return rows


def capture_execution_identity(
    rows: list[dict[str, str]], decision: dict[str, object], tools: ToolPaths
) -> dict[str, object]:
    require(not checkout_changes(), "pilot/formal execution requires a clean checkout")
    gpus = visible_gpu_inventory()
    require(len(gpus) >= WORKER_COUNT, "two visible GPUs are required by the frozen plan")
    identity = {
        "schema_version": 1,
        "git_head": git_head(),
        "runner_commit": decision["runner_commit"],
        "runner_sha256": sha256_file(RUNNER_PATH),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "attempt_plan_sha256": sha256_file(PLAN_PATH),
        "preexecution_decision_sha256": sha256_file(DECISION_PATH),
        "repeat_subset_sha256": sha256_file(SUBSET_PATH),
        "paper_runtime_commit": PAPER_RUNTIME_COMMIT,
        "tools": tool_identity(tools),
        "gpus": gpus[:WORKER_COUNT],
        "worker_count": WORKER_COUNT,
        "gpu_assignment": GPU_ASSIGNMENT,
        "attempt_ids": [row["attempt_id"] for row in rows],
    }
    identity["identity_sha256"] = canonical_digest(identity)
    return identity


def validate_execution_identity(identity: dict[str, object], tools: ToolPaths) -> None:
    require(not checkout_changes(), "execution checkout changed")
    require(git_head() == identity["git_head"], "execution Git HEAD changed")
    require(sha256_file(RUNNER_PATH) == identity["runner_sha256"], "execution runner changed")
    require(sha256_file(MANIFEST_PATH) == identity["manifest_sha256"], "execution manifest changed")
    require(sha256_file(PLAN_PATH) == identity["attempt_plan_sha256"], "execution plan changed")
    require(sha256_file(DECISION_PATH) == identity["preexecution_decision_sha256"], "execution decision changed")
    require(sha256_file(SUBSET_PATH) == identity["repeat_subset_sha256"], "execution subset changed")
    require(tool_identity(tools) == identity["tools"], "execution tool identity changed")
    expected_digest_payload = dict(identity)
    observed_digest = expected_digest_payload.pop("identity_sha256")
    require(canonical_digest(expected_digest_payload) == observed_digest, "execution identity digest drift")


def pairs_for_attempt(
    row: dict[str, str], manifest_rows: list[dict[str, str]], subset_rows: list[dict[str, str]]
) -> list[tuple[dict[str, str], dict[str, str]]]:
    by_id = {item["record_id"]: item for item in manifest_rows}
    if row["execution_stage"] == "pilot":
        return [(by_id[PILOT_QUERY_ID], by_id[PILOT_TARGET_ID])]
    if row["execution_stage"] == "formal_full":
        queries = [item for item in manifest_rows if item["record_role"] == "query"]
        targets = [item for item in manifest_rows if item["record_role"] == "target"]
    else:
        queries = [by_id[item["record_id"]] for item in subset_rows if item["record_role"] == "query"]
        targets = [by_id[item["record_id"]] for item in subset_rows if item["record_role"] == "target"]
    return [(query, target) for query in queries for target in targets]


def _kill_process_group(process: subprocess.Popen[object]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def _outer_timeout(arm: str) -> int:
    return BACKEND_TIMEOUT_SECONDS + 120 if arm in {"A", "B"} else 3 * BACKEND_TIMEOUT_SECONDS + 120


def workflow_command(
    row: dict[str, str], query: Path, target: Path, pair_dir: Path, tools: ToolPaths
) -> list[str]:
    return [
        sys.executable,
        str(tools.workflow.resolve()),
        "--mode",
        row["mode"],
        "--contract",
        row["contract"],
        "--query",
        str(query.resolve()),
        "--target",
        str(target.resolve()),
        "--output",
        str((pair_dir / "output").resolve()),
        "--report",
        str((pair_dir / "run-report.json").resolve()),
        "--rule",
        "0",
        "--triplex-preset",
        "normal",
        "--top-k",
        "5",
        "--assembly",
        "GRCh38",
        "--annotation-release",
        "GENCODE v49",
        "--timeout",
        str(BACKEND_TIMEOUT_SECONDS),
        "--authority-binary",
        str(tools.authority_binary.resolve()),
        "--candidate-binary",
        str(tools.candidate_binary.resolve()),
        "--comparator",
        str(tools.comparator.resolve()),
    ]


def read_and_validate_report(path: Path, row: dict[str, str]) -> dict[str, object]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"run report is missing or invalid: {type(exc).__name__}") from exc
    require(isinstance(report, dict), "run report must be an object")
    validate_schema_value(RUN_REPORT_SCHEMA, report, "report")
    require(report["mode"] == row["mode"], "run report mode drift")
    require(report["requested_contract"] == row["contract"], "run report contract drift")
    require(report["timestamps"]["wall_seconds"] is not None, "run report total wall time unavailable")
    arm = row["arm"]
    if arm == "A":
        require(report["resolved_execution"] == "cpu-authority", "arm A did not use authority")
        require(report["backends"]["authority"] is not None, "arm A authority was not executed")
        require(report["backends"]["candidate"] is None, "arm A unexpectedly executed candidate")
        require(report["result_status"] == "authority_complete", "arm A did not complete")
    elif arm == "B":
        require(report["resolved_execution"] == "fast-experimental", "arm B mode drift")
        require(report["backends"]["candidate"] is not None, "arm B candidate was not executed")
        require(report["backends"]["authority"] is None, "arm B unexpectedly executed authority")
        require(report["result_status"] == "experimental_unverified", "arm B result status drift")
    else:
        require(report["resolved_execution"] == "verified", "safe C did not resolve to verified")
        require(report["backends"]["candidate"] is not None, "safe C candidate was not executed")
        authority = report["backends"]["authority"]
        require(authority is not None, "safe C complete authority was not executed")
        require(authority["returncode"] == 0 and not authority["timed_out"], "safe C authority did not complete")
        require(report["comparators"]["status"] != "not_run", "safe C comparison was not attempted")
        require(report["published_source"] in {"candidate", "authority"}, "safe C publication source drift")
    return report


def component_timings(report: dict[str, object] | None, total_wall: float) -> dict[str, object]:
    backends = report.get("backends", {}) if report else {}
    comparators = report.get("comparators", {}) if report else {}
    candidate = backends.get("candidate") if isinstance(backends, dict) else None
    authority = backends.get("authority") if isinstance(backends, dict) else None
    candidate_wall = candidate.get("wall_seconds") if isinstance(candidate, dict) else None
    authority_wall = authority.get("wall_seconds") if isinstance(authority, dict) else None
    comparison_wall = comparators.get("wall_seconds") if isinstance(comparators, dict) else None
    known = [value for value in (candidate_wall, authority_wall, comparison_wall) if isinstance(value, (int, float))]
    return {
        "candidate_wall_seconds": candidate_wall,
        "authority_wall_seconds": authority_wall,
        "comparison_wall_seconds": comparison_wall,
        "component_wall_seconds_sum": sum(known),
        "workflow_wall_seconds": report.get("timestamps", {}).get("wall_seconds") if report else None,
        "total_wall_seconds": total_wall,
        "runner_and_wrapper_overhead_seconds": max(0.0, total_wall - sum(known)),
        "candidate_status": candidate.get("returncode") if isinstance(candidate, dict) else None,
        "authority_status": authority.get("returncode") if isinstance(authority, dict) else None,
        "contract_result": comparators.get("declared_contract_clean") if isinstance(comparators, dict) else None,
        "fallback_used": bool(report and report.get("counters", {}).get("fallback", 0)),
        "published_backend": report.get("published_source") if report else None,
    }


def _artifact_rows(root: Path, excluded: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"artifact tree contains symlink: {path}")
        if not path.is_file():
            continue
        relative = str(path.relative_to(root))
        if relative in excluded:
            continue
        rows.append(
            {
                "artifact_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def write_artifact_manifest(root: Path) -> tuple[str, int]:
    excluded = {"artifact_manifest.tsv", "artifact_manifest.sha256", "attempt-complete.json"}
    rows = _artifact_rows(root, excluded)
    manifest_path = root / "artifact_manifest.tsv"
    write_tsv(manifest_path, ("artifact_path", "size_bytes", "sha256"), rows)
    digest = sha256_file(manifest_path)
    atomic_bytes(
        root / "artifact_manifest.sha256",
        f"{digest}  artifact_manifest.tsv\n".encode("ascii"),
    )
    return digest, len(rows)


def validate_attempt_receipt(path: Path, expected_attempt_id: str) -> dict[str, object]:
    require(path.is_dir() and not path.is_symlink(), f"attempt directory is missing: {path}")
    receipt_path = path / "attempt-complete.json"
    require(receipt_path.is_file() and not receipt_path.is_symlink(), "attempt receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("attempt_id") == expected_attempt_id, "attempt receipt ID drift")
    require(receipt.get("status") == "complete", "attempt receipt is not complete")
    manifest_path = path / "artifact_manifest.tsv"
    require(sha256_file(manifest_path) == receipt.get("artifact_manifest_sha256"), "artifact manifest digest drift")
    rows = read_tsv(manifest_path, ("artifact_path", "size_bytes", "sha256"))
    expected_files = {
        row["artifact_path"] for row in rows
    } | {"artifact_manifest.tsv", "artifact_manifest.sha256", "attempt-complete.json"}
    observed_files: set[str] = set()
    for artifact in sorted(path.rglob("*")):
        require(not artifact.is_symlink(), f"attempt artifact is a symlink: {artifact}")
        if artifact.is_file():
            observed_files.add(str(artifact.relative_to(path)))
    require(observed_files == expected_files, "attempt artifact file set drift")
    checksum_fields = (path / "artifact_manifest.sha256").read_text(encoding="ascii").split()
    require(
        checksum_fields == [receipt.get("artifact_manifest_sha256"), "artifact_manifest.tsv"],
        "artifact manifest checksum receipt drift",
    )
    for row in rows:
        artifact = path / row["artifact_path"]
        require(artifact.is_file() and not artifact.is_symlink(), f"missing attempt artifact: {row['artifact_path']}")
        require(artifact.stat().st_size == int(row["size_bytes"]), f"artifact size drift: {row['artifact_path']}")
        require(sha256_file(artifact) == row["sha256"], f"artifact digest drift: {row['artifact_path']}")
    require(len(rows) == receipt.get("artifact_count"), "attempt artifact count drift")
    return receipt


def run_pair(
    *,
    row: dict[str, str],
    pair_index: int,
    query_row: dict[str, str],
    target_row: dict[str, str],
    worker_id: int,
    attempt_dir: Path,
    tools: ToolPaths,
    formal_deadline_epoch: float | None = None,
) -> dict[str, object]:
    pair_id = f"pair{pair_index:05d}_{query_row['record_id']}_{target_row['record_id']}"
    pair_dir = attempt_dir / "pairs" / pair_id
    require(not pair_dir.exists(), f"pair attempt already exists: {pair_id}")
    pair_dir.mkdir(parents=True)
    query = ROOT / query_row["path"]
    target = ROOT / target_row["path"]
    command = workflow_command(row, query, target, pair_dir, tools)
    write_json(
        pair_dir / "command.json",
        {
            "schema_version": 1,
            "attempt_id": row["attempt_id"],
            "pair_id": pair_id,
            "pair_index": pair_index,
            "query_id": query_row["record_id"],
            "target_id": target_row["record_id"],
            "worker_id": worker_id,
            "physical_gpu": worker_id,
            "cuda_visible_devices": str(worker_id),
            "query_file_sha256": query_row["file_sha256"],
            "target_file_sha256": target_row["file_sha256"],
            "command": command,
        },
    )
    time_path = pair_dir / "time.txt"
    measured_command = command
    if Path("/usr/bin/time").is_file():
        measured_command = ["/usr/bin/time", "-v", "-o", str(time_path), *command]
    else:
        atomic_bytes(time_path, b"resource_measurement=unavailable\n")
    environment = os.environ.copy()
    environment["CUDA_VISIBLE_DEVICES"] = str(worker_id)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started_utc = utc_now()
    started = time.perf_counter()
    timed_out = False
    returncode = 125
    outer_timeout = float(_outer_timeout(row["arm"]))
    if formal_deadline_epoch is not None:
        outer_timeout = min(outer_timeout, max(0.0, formal_deadline_epoch - time.time()))
    require(outer_timeout > 0, "fixed 24-hour formal execution budget exhausted before pair launch")
    with (pair_dir / "stdout.log").open("wb") as stdout, (pair_dir / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(
            measured_command,
            cwd=pair_dir,
            env=environment,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        try:
            try:
                returncode = process.wait(timeout=outer_timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_process_group(process)
                returncode = 124
        except BaseException:
            _kill_process_group(process)
            raise
    total_wall = time.perf_counter() - started
    report: dict[str, object] | None = None
    validation_error: str | None = None
    try:
        report = read_and_validate_report(pair_dir / "run-report.json", row)
    except (KeyError, TypeError, ValueError) as exc:
        validation_error = str(exc)
    try:
        rss = max_rss_kb(time_path) if time_path.is_file() else None
    except (OSError, SystemExit, ValueError):
        rss = None
    resource = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "pair_id": pair_id,
        "pair_index": pair_index,
        "worker_id": worker_id,
        "physical_gpu": worker_id,
        "start_utc": started_utc,
        "end_utc": utc_now(),
        "returncode": returncode,
        "timed_out": timed_out,
        "max_rss_kb": rss,
        "report_schema_valid": validation_error is None,
        "report_validation_error": validation_error,
    }
    resource.update(component_timings(report, total_wall))
    write_json(pair_dir / "resource.json", resource)
    pair_manifest, pair_artifact_count = write_artifact_manifest(pair_dir)
    result_status = report.get("result_status") if report else None
    result = {
        "pair_id": pair_id,
        "pair_index": pair_index,
        "query_id": query_row["record_id"],
        "target_id": target_row["record_id"],
        "worker_id": worker_id,
        "physical_gpu": worker_id,
        "returncode": returncode,
        "timed_out": timed_out,
        "report_schema_valid": validation_error is None,
        "report_validation_error": validation_error,
        "result_status": result_status,
        "fallback_count": int(report.get("counters", {}).get("fallback", 0)) if report else 0,
        "oom_count": int(report.get("counters", {}).get("oom", 0)) if report else 0,
        "timeout_count": int(report.get("counters", {}).get("timeout", 0)) if report else int(timed_out),
        "published_backend": report.get("published_source") if report else None,
        "contract_result": report.get("comparators", {}).get("declared_contract_clean") if report else None,
        "total_wall_seconds": total_wall,
        "candidate_wall_seconds": resource["candidate_wall_seconds"],
        "authority_wall_seconds": resource["authority_wall_seconds"],
        "comparison_wall_seconds": resource["comparison_wall_seconds"],
        "artifact_manifest_sha256": pair_manifest,
        "artifact_count": pair_artifact_count,
        "status": "complete"
        if returncode == 0 and not timed_out and validation_error is None
        else "technical_failure",
    }
    return result


PairExecutor = Callable[..., dict[str, object]]


def execute_attempt(
    *,
    row: dict[str, str],
    manifest_rows: list[dict[str, str]],
    subset_rows: list[dict[str, str]],
    identity: dict[str, object],
    tools: ToolPaths,
    artifact_root: Path,
    resume: bool,
    pair_executor: PairExecutor = run_pair,
    formal_deadline_epoch: float | None = None,
) -> dict[str, object]:
    expected = ROOT / row["expected_artifact_root"]
    if os.environ.get("PHASE3_APPLICATION_TEST_MODE") != "1":
        observed = (
            artifact_root
            / row["execution_stage"].replace("_", "-")
            / row["attempt_id"]
        )
        require(
            expected.resolve() == observed.resolve(),
            "attempt artifact path does not match frozen plan",
        )
    destination = artifact_root / {
        "pilot": "pilot",
        "formal_full": "formal-full",
        "formal_repeat": "formal-repeat",
    }[row["execution_stage"]] / row["attempt_id"]
    if destination.exists():
        if resume:
            receipt = validate_attempt_receipt(destination, row["attempt_id"])
            return {"status": "reused", "receipt": receipt, "attempt_id": row["attempt_id"]}
        raise ValueError(f"attempt already exists and cannot be overwritten: {row['attempt_id']}")
    destination.mkdir(parents=True)
    pairs = pairs_for_attempt(row, manifest_rows, subset_rows)
    write_json(
        destination / "attempt.json",
        {
            "schema_version": 1,
            "status": "started",
            "start_utc": utc_now(),
            "plan_row": row,
            "execution_identity": identity,
            "pair_count": len(pairs),
            "worker_count": WORKER_COUNT,
            "retry_policy": RETRY_POLICY,
        },
    )
    sampler = GpuSampler(destination / "gpu-memory.csv")
    sampler_started = False
    attempt_started = time.perf_counter()

    def worker(worker_id: int) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for pair_index, (query_row, target_row) in enumerate(pairs):
            if pair_index % WORKER_COUNT != worker_id:
                continue
            require(
                formal_deadline_epoch is None or time.time() < formal_deadline_epoch,
                "fixed 24-hour formal execution budget exhausted",
            )
            try:
                result = pair_executor(
                    row=row,
                    pair_index=pair_index,
                    query_row=query_row,
                    target_row=target_row,
                    worker_id=worker_id,
                    attempt_dir=destination,
                    tools=tools,
                    formal_deadline_epoch=formal_deadline_epoch,
                )
            except BaseException as exc:
                write_json(
                    destination / "pairs" / f"pair{pair_index:05d}-runner-exception.json",
                    {
                        "schema_version": 1,
                        "pair_index": pair_index,
                        "worker_id": worker_id,
                        "exception_type": type(exc).__name__,
                        "exception": str(exc),
                    },
                )
                raise
            results.append(result)
        return results

    try:
        sampler.start()
        sampler_started = True
        with ThreadPoolExecutor(max_workers=WORKER_COUNT, thread_name_prefix="phase3-gpu-worker") as pool:
            futures = [pool.submit(worker, worker_id) for worker_id in range(WORKER_COUNT)]
            pair_results = [result for future in futures for result in future.result()]
    finally:
        if sampler_started:
            sampler.stop()
    pair_results.sort(key=lambda result: int(result["pair_index"]))
    validate_execution_identity(identity, tools)
    attempt_wall = time.perf_counter() - attempt_started
    failed = [result for result in pair_results if result["status"] != "complete"]
    aggregate_resource: dict[str, object] = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "arm": row["arm"],
        "mode": row["mode"],
        "pair_count": len(pair_results),
        "worker_count": WORKER_COUNT,
        "total_wall_seconds": attempt_wall,
        "candidate_wall_seconds": sum(float(result["candidate_wall_seconds"] or 0) for result in pair_results),
        "authority_wall_seconds": sum(float(result["authority_wall_seconds"] or 0) for result in pair_results),
        "comparison_wall_seconds": sum(float(result["comparison_wall_seconds"] or 0) for result in pair_results),
        "fallback_count": sum(int(result["fallback_count"]) for result in pair_results),
        "oom_count": sum(int(result["oom_count"]) for result in pair_results),
        "timeout_count": sum(int(result["timeout_count"]) for result in pair_results),
        "technical_failure_count": len(failed),
    }
    try:
        aggregate_resource["gpu"] = gpu_metrics(destination / "gpu-memory.csv")
    except (OSError, SystemExit, ValueError) as exc:
        aggregate_resource["gpu"] = {
            "gpu_measurement_status": "unavailable",
            "reason": f"{type(exc).__name__}:{exc}",
        }
    write_json(destination / "resource.json", aggregate_resource)
    write_tsv(
        destination / "pair-results.tsv",
        (
            "pair_id",
            "pair_index",
            "query_id",
            "target_id",
            "worker_id",
            "physical_gpu",
            "returncode",
            "timed_out",
            "report_schema_valid",
            "report_validation_error",
            "result_status",
            "fallback_count",
            "oom_count",
            "timeout_count",
            "published_backend",
            "contract_result",
            "total_wall_seconds",
            "candidate_wall_seconds",
            "authority_wall_seconds",
            "comparison_wall_seconds",
            "artifact_manifest_sha256",
            "artifact_count",
            "status",
        ),
        pair_results,
    )
    if len(pair_results) == 1:
        pair_dir = destination / "pairs" / str(pair_results[0]["pair_id"])
        for name in ("stdout.log", "stderr.log", "run-report.json"):
            source = pair_dir / name
            if source.is_file():
                shutil.copy2(source, destination / name)
    summary = {
        "schema_version": 1,
        "attempt_id": row["attempt_id"],
        "execution_stage": row["execution_stage"],
        "arm": row["arm"],
        "mode": row["mode"],
        "scope": row["scope"],
        "pair_count": len(pair_results),
        "complete_pair_count": len(pair_results) - len(failed),
        "technical_failure_count": len(failed),
        "fallback_count": aggregate_resource["fallback_count"],
        "oom_count": aggregate_resource["oom_count"],
        "timeout_count": aggregate_resource["timeout_count"],
        "total_wall_seconds": attempt_wall,
        "outcome": "complete" if not failed else "technical_failure",
        "end_utc": utc_now(),
    }
    write_json(destination / "attempt-summary.json", summary)
    manifest_sha256, artifact_count = write_artifact_manifest(destination)
    receipt = {
        "schema_version": 1,
        "status": "complete",
        "attempt_id": row["attempt_id"],
        "outcome": summary["outcome"],
        "plan_sha256": identity["attempt_plan_sha256"],
        "execution_identity_sha256": identity["identity_sha256"],
        "summary_sha256": sha256_file(destination / "attempt-summary.json"),
        "resource_sha256": sha256_file(destination / "resource.json"),
        "artifact_manifest_sha256": manifest_sha256,
        "artifact_count": artifact_count,
    }
    write_json(destination / "attempt-complete.json", receipt)
    validate_attempt_receipt(destination, row["attempt_id"])
    return {"status": "executed", "receipt": receipt, "attempt_id": row["attempt_id"]}


def _selected_plan_rows(rows: list[dict[str, str]], stage: str) -> list[dict[str, str]]:
    selected = [row for row in rows if row["execution_stage"] == stage]
    return sorted(selected, key=lambda row: (int(row["repeat_id"]), int(row["order"])))


def validate_artifact_root(artifact_root: Path) -> None:
    trusted = ROOT.resolve()
    candidate = Path(os.path.abspath(artifact_root))
    try:
        candidate.relative_to(trusted)
    except ValueError as exc:
        raise ValueError("artifact root must stay inside the repository") from exc
    current = trusted
    for part in candidate.relative_to(trusted).parts:
        current = current / part
        require(not current.is_symlink(), f"artifact root component is a symlink: {current}")
    if os.environ.get("PHASE3_APPLICATION_TEST_MODE") != "1":
        require(
            candidate == CANONICAL_ARTIFACT_ROOT.resolve(),
            "production execution requires canonical artifact root",
        )


def formal_budget_deadline(artifact_root: Path, identity: dict[str, object]) -> float:
    path = artifact_root / "formal-budget.json"
    if path.exists():
        require(path.is_file() and not path.is_symlink(), "formal budget receipt is unsafe")
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("schema_version") == 1, "formal budget schema drift")
        require(payload.get("budget_seconds") == TOTAL_BUDGET_SECONDS, "formal budget drift")
        require(payload.get("attempt_plan_sha256") == identity["attempt_plan_sha256"], "formal budget plan drift")
        require(payload.get("execution_git_head") == identity["git_head"], "formal budget Git identity drift")
    else:
        artifact_root.mkdir(parents=True, exist_ok=True)
        started_epoch = time.time()
        payload = {
            "schema_version": 1,
            "status": "formal_budget_started",
            "start_utc": utc_now(),
            "start_epoch_seconds": started_epoch,
            "budget_seconds": TOTAL_BUDGET_SECONDS,
            "deadline_epoch_seconds": started_epoch + TOTAL_BUDGET_SECONDS,
            "attempt_plan_sha256": identity["attempt_plan_sha256"],
            "execution_git_head": identity["git_head"],
            "retry_policy": RETRY_POLICY,
        }
        write_json(path, payload)
    deadline = float(payload["deadline_epoch_seconds"])
    require(time.time() < deadline, "fixed 24-hour formal execution budget is exhausted")
    return deadline


def execute_stage(stage: str, *, resume: bool, artifact_root: Path) -> list[dict[str, object]]:
    validate_artifact_root(artifact_root)
    rows, decision = load_and_validate_plan()
    selected = _selected_plan_rows(rows, stage)
    require(selected, f"no planned attempts for stage: {stage}")
    if stage != "pilot":
        postpilot = ROOT / "paper/bioinformatics/phase3_postpilot_decision.json"
        require(postpilot.is_file(), "formal execution is blocked pending a post-pilot decision")
        payload = json.loads(postpilot.read_text(encoding="utf-8"))
        require(
            payload.get("selected_decision") == "continue_full_descriptive_negative",
            "formal execution is not authorized for descriptive-negative evidence",
        )
    destinations = [
        artifact_root
        / {"pilot": "pilot", "formal_full": "formal-full", "formal_repeat": "formal-repeat"}[stage]
        / row["attempt_id"]
        for row in selected
    ]
    for destination, row in zip(destinations, selected, strict=True):
        if destination.exists():
            if resume:
                validate_attempt_receipt(destination, row["attempt_id"])
            else:
                raise ValueError(f"attempt already exists: {row['attempt_id']}")
    manifest_rows = load_application_manifest()
    subset_rows = read_tsv(SUBSET_PATH, SUBSET_FIELDS)
    tools = ToolPaths()
    identity = capture_execution_identity(selected, decision, tools)
    deadline_epoch = None
    if stage != "pilot":
        deadline_epoch = formal_budget_deadline(artifact_root, identity)
    results: list[dict[str, object]] = []
    for row in selected:
        validate_execution_identity(identity, tools)
        results.append(
            execute_attempt(
                row=row,
                manifest_rows=manifest_rows,
                subset_rows=subset_rows,
                identity=identity,
                tools=tools,
                artifact_root=artifact_root,
                resume=resume,
                formal_deadline_epoch=deadline_epoch,
            )
        )
    validate_execution_identity(identity, tools)
    index_path = artifact_root / {
        "pilot": "pilot-index.json",
        "formal_full": "formal-full-index.json",
        "formal_repeat": "formal-repeat-index.json",
    }[stage]
    require(not index_path.exists(), f"stage index already exists: {index_path}")
    write_json(
        index_path,
        {
            "schema_version": 1,
            "execution_stage": stage,
            "attempt_plan_sha256": sha256_file(PLAN_PATH),
            "execution_identity": identity,
            "results": results,
        },
    )
    return results


def plan_summary() -> dict[str, object]:
    rows, decision = load_and_validate_plan()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["execution_stage"]] = counts.get(row["execution_stage"], 0) + 1
    return {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "manifest_sha256": MANIFEST_SHA256,
        "attempt_plan_sha256": sha256_file(PLAN_PATH),
        "runner_commit": decision["runner_commit"],
        "runner_sha256": decision["runner_sha256"],
        "attempt_count": len(rows),
        "attempt_counts_by_stage": counts,
        "pilot_attempt_ids": decision["pilot_attempt_ids"],
        "b3_promotion_feasibility": decision["b3_promotion_feasibility"],
        "full_run_decision": decision["full_run_decision"],
        "application_execution_started": CANONICAL_ARTIFACT_ROOT.exists(),
    }


def _pilot_attempt_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = _selected_plan_rows(rows, "pilot")
    require([row["arm"] for row in selected] == ["A", "B", "C"], "pilot arm order drift")
    return selected


def _load_pilot_attempts(
    artifact_root: Path, rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    index_path = artifact_root / "pilot-index.json"
    require(index_path.is_file() and not index_path.is_symlink(), "pilot index is missing")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    require(index.get("execution_stage") == "pilot", "pilot index stage drift")
    require(index.get("attempt_plan_sha256") == sha256_file(PLAN_PATH), "pilot index plan drift")
    require(not (artifact_root / "formal-full").exists(), "formal full execution already started")
    require(not (artifact_root / "formal-repeat").exists(), "formal repeat execution already started")
    attempts: list[dict[str, object]] = []
    for row in _pilot_attempt_rows(rows):
        attempt_dir = artifact_root / "pilot" / row["attempt_id"]
        receipt = validate_attempt_receipt(attempt_dir, row["attempt_id"])
        summary = json.loads((attempt_dir / "attempt-summary.json").read_text(encoding="utf-8"))
        resource = json.loads((attempt_dir / "resource.json").read_text(encoding="utf-8"))
        run_report = json.loads((attempt_dir / "run-report.json").read_text(encoding="utf-8"))
        read_and_validate_report(attempt_dir / "run-report.json", row)
        attempts.append(
            {
                "attempt_id": row["attempt_id"],
                "arm": row["arm"],
                "mode": row["mode"],
                "contract": row["contract"],
                "outcome": receipt["outcome"],
                "attempt_receipt_sha256": sha256_file(attempt_dir / "attempt-complete.json"),
                "artifact_manifest_sha256": receipt["artifact_manifest_sha256"],
                "artifact_count": receipt["artifact_count"],
                "total_wall_seconds": resource["total_wall_seconds"],
                "candidate_wall_seconds": resource["candidate_wall_seconds"],
                "authority_wall_seconds": resource["authority_wall_seconds"],
                "comparison_wall_seconds": resource["comparison_wall_seconds"],
                "fallback_count": resource["fallback_count"],
                "oom_count": resource["oom_count"],
                "timeout_count": resource["timeout_count"],
                "technical_failure_count": resource["technical_failure_count"],
                "result_status": run_report["result_status"],
                "published_backend": run_report["published_source"],
                "declared_contract_clean": run_report["comparators"].get(
                    "declared_contract_clean"
                ),
                "raw_attempt_root": str(attempt_dir.relative_to(ROOT)),
                "start_utc": json.loads(
                    (attempt_dir / "attempt.json").read_text(encoding="utf-8")
                )["start_utc"],
                "end_utc": summary["end_utc"],
            }
        )
    return attempts


def _panel_work_units(
    manifest_rows: list[dict[str, str]], subset_rows: list[dict[str, str]]
) -> dict[str, object]:
    queries = [row for row in manifest_rows if row["record_role"] == "query"]
    targets = [row for row in manifest_rows if row["record_role"] == "target"]
    by_id = {row["record_id"]: row for row in manifest_rows}
    subset_queries = [by_id[row["record_id"]] for row in subset_rows if row["record_role"] == "query"]
    subset_targets = [by_id[row["record_id"]] for row in subset_rows if row["record_role"] == "target"]

    def worker_units(
        left: list[dict[str, str]], right: list[dict[str, str]], repeat_count: int
    ) -> list[int]:
        result = [0, 0]
        pairs = [(query, target) for query in left for target in right]
        for _repeat in range(repeat_count):
            for pair_index, (query, target) in enumerate(pairs):
                result[pair_index % WORKER_COUNT] += int(query["sequence_length"]) * int(
                    target["sequence_length"]
                )
        return result

    pilot_query = by_id[PILOT_QUERY_ID]
    pilot_target = by_id[PILOT_TARGET_ID]
    full_workers = worker_units(queries, targets, 1)
    repeat_workers = worker_units(subset_queries, subset_targets, REPEAT_COUNT)
    return {
        "pilot": int(pilot_query["sequence_length"]) * int(pilot_target["sequence_length"]),
        "formal_full": sum(full_workers),
        "formal_repeats": sum(repeat_workers),
        "formal_full_by_worker": full_workers,
        "formal_repeats_by_worker": repeat_workers,
        "full_plus_repeats_by_worker": [
            full_workers[index] + repeat_workers[index]
            for index in range(WORKER_COUNT)
        ],
    }


def build_resource_projection(
    attempts: list[dict[str, object]],
    manifest_rows: list[dict[str, str]],
    subset_rows: list[dict[str, str]],
) -> dict[str, object]:
    by_arm = {str(attempt["arm"]): attempt for attempt in attempts}
    require(set(by_arm) == set(ARM_SPECS), "pilot projection requires exactly A, B, and C")
    units = _panel_work_units(manifest_rows, subset_rows)
    formal_pair_count = 50 * 668
    repeat_pair_count = REPEAT_COUNT * REPEAT_QUERY_COUNT * (
        2 * REPEAT_TARGETS_PER_CHROMOSOME
    )
    pair_scale_per_worker = (formal_pair_count + repeat_pair_count) / WORKER_COUNT
    work_scale_per_worker = max(units["full_plus_repeats_by_worker"]) / units["pilot"]
    selected_scale = max(pair_scale_per_worker, work_scale_per_worker)
    arm_projections: list[dict[str, object]] = []
    for arm in ("A", "B", "C"):
        observed = float(by_arm[arm]["total_wall_seconds"])
        projected = observed * selected_scale * PROJECTION_CONSERVATISM_FACTOR
        arm_projections.append(
            {
                "arm": arm,
                "observed_pilot_wall_seconds": observed,
                "pair_count_scale_per_worker": pair_scale_per_worker,
                "sequence_work_scale_per_worker": work_scale_per_worker,
                "selected_scale_per_worker": selected_scale,
                "conservatism_factor": PROJECTION_CONSERVATISM_FACTOR,
                "projected_full_plus_repeats_wall_seconds": projected,
            }
        )
    projected_total = sum(
        float(row["projected_full_plus_repeats_wall_seconds"])
        for row in arm_projections
    )
    return {
        "schema_version": 1,
        "status": "pilot_based_nonclaim_projection",
        "freeze_id": FREEZE_ID,
        "manifest_sha256": MANIFEST_SHA256,
        "attempt_plan_sha256": sha256_file(PLAN_PATH),
        "pilot_receipt_role": "operational_and_resource_characterization_only",
        "projection_is_formal_source_data": False,
        "fixed_budget_seconds": TOTAL_BUDGET_SECONDS,
        "worker_count": WORKER_COUNT,
        "formal_pair_count_per_arm": formal_pair_count,
        "repeat_pair_count_per_arm": repeat_pair_count,
        "work_units": units,
        "method": (
            "for each arm, pilot wall multiplied by the larger of the exact "
            "maximum per-worker pair-count scale and exact maximum per-worker "
            "sequence-length-product scale under frozen modulo-2 assignment, "
            "then multiplied by a prespecified 1.25 conservatism factor"
        ),
        "arm_projections": arm_projections,
        "projected_total_wall_seconds": projected_total,
        "within_fixed_budget": projected_total <= TOTAL_BUDGET_SECONDS,
        "limitations": [
            "one fixed short-query pilot cannot estimate workload-tail variance",
            "projection is a prospective stop-control estimate, not a performance claim",
            "no panel, parameter, threshold, or claim boundary may change from this estimate",
        ],
    }


def select_postpilot_decision(
    attempts: list[dict[str, object]], projection: dict[str, object]
) -> str:
    operational_failure = any(
        attempt["outcome"] != "complete"
        or int(attempt["technical_failure_count"]) != 0
        or int(attempt["timeout_count"]) != 0
        or int(attempt["oom_count"]) != 0
        for attempt in attempts
    )
    if operational_failure:
        return "blocked_by_operational_failure"
    if not bool(projection["within_fixed_budget"]):
        return "blocked_by_fixed_budget"
    return "stop_after_pilot_futility"


def build_pilot_receipt(
    attempts: list[dict[str, object]], projection: dict[str, object]
) -> dict[str, object]:
    by_arm = {str(attempt["arm"]): attempt for attempt in attempts}
    authority_wall = float(by_arm["A"]["total_wall_seconds"])
    candidate_wall = float(by_arm["B"]["total_wall_seconds"])
    safe_wall = float(by_arm["C"]["total_wall_seconds"])
    safe_components = {
        "candidate_wall_seconds": by_arm["C"]["candidate_wall_seconds"],
        "authority_wall_seconds": by_arm["C"]["authority_wall_seconds"],
        "comparison_wall_seconds": by_arm["C"]["comparison_wall_seconds"],
    }
    component_sum = sum(
        float(value) for value in safe_components.values() if value is not None
    )
    return {
        "schema_version": 1,
        "status": "fixed_pilot_complete",
        "freeze_id": FREEZE_ID,
        "manifest_sha256": MANIFEST_SHA256,
        "attempt_plan_sha256": sha256_file(PLAN_PATH),
        "preexecution_decision_sha256": sha256_file(DECISION_PATH),
        "pilot_scope": f"{PILOT_QUERY_ID}_{PILOT_TARGET_ID}",
        "pilot_role": "operational_and_resource_characterization_only",
        "formal_source_data": False,
        "attempts": attempts,
        "observed": {
            "authority_a_wall_seconds": authority_wall,
            "candidate_b_wall_seconds": candidate_wall,
            "safe_c_wall_seconds": safe_wall,
            "candidate_only_speedup_vs_authority": authority_wall / candidate_wall,
            "safe_speedup_vs_authority": authority_wall / safe_wall,
            "safe_wall_reduction_seconds": authority_wall - safe_wall,
            "safe_24h_capacity_gain_vs_authority": authority_wall / safe_wall,
            "safe_c_components": safe_components,
            "safe_c_component_sum_seconds": component_sum,
            "safe_c_unattributed_overhead_seconds": max(0.0, safe_wall - component_sum),
        },
        "b3_promotion_feasibility": "structurally_unreachable_under_verified_only_v1",
        "pilot_can_promote_or_rescue_b3": False,
        "candidate_only_is_safe_acceleration": False,
        "resource_projection_sha256": hashlib.sha256(
            canonical_json_bytes(projection)
        ).hexdigest(),
    }


def _raw_pilot_artifact_rows(artifact_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    pilot_root = artifact_root / "pilot"
    require(pilot_root.is_dir() and not pilot_root.is_symlink(), "pilot artifact directory is missing")
    for path in sorted(pilot_root.rglob("*")):
        require(not path.is_symlink(), f"raw pilot artifact is a symlink: {path}")
        if path.is_file():
            rows.append(
                {
                    "artifact_path": str(path.relative_to(ROOT)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "retention": "raw_ignored_local_artifact",
                    "formal_source_data": 0,
                }
            )
    index_path = artifact_root / "pilot-index.json"
    rows.append(
        {
            "artifact_path": str(index_path.relative_to(ROOT)),
            "size_bytes": index_path.stat().st_size,
            "sha256": sha256_file(index_path),
            "retention": "raw_ignored_local_artifact",
            "formal_source_data": 0,
        }
    )
    return rows


def summarize_pilot(artifact_root: Path = CANONICAL_ARTIFACT_ROOT) -> dict[str, object]:
    validate_artifact_root(artifact_root)
    require(not checkout_changes(), "pilot summary generation requires a clean tracked checkout")
    rows, decision = load_and_validate_plan()
    require(decision["full_run_decision"] == "pending_fixed_pilot", "preexecution decision drift")
    attempts = _load_pilot_attempts(artifact_root, rows)
    manifest_rows = load_application_manifest()
    subset_rows = read_tsv(SUBSET_PATH, SUBSET_FIELDS)
    projection = build_resource_projection(attempts, manifest_rows, subset_rows)
    pilot_receipt = build_pilot_receipt(attempts, projection)
    selected = select_postpilot_decision(attempts, projection)
    b3_status = "blocked" if selected == "blocked_by_operational_failure" else "no_go"
    postpilot = {
        "schema_version": 1,
        "status": "postpilot_decision_frozen",
        "selected_decision": selected,
        "allowed_decisions": list(ALLOWED_POST_PILOT_DECISIONS),
        "freeze_id": FREEZE_ID,
        "attempt_plan_sha256": sha256_file(PLAN_PATH),
        "pilot_receipt_sha256": hashlib.sha256(
            canonical_json_bytes(pilot_receipt)
        ).hexdigest(),
        "resource_projection_sha256": hashlib.sha256(
            canonical_json_bytes(projection)
        ).hexdigest(),
        "b3_promotion_feasibility": "structurally_unreachable_under_verified_only_v1",
        "b3_threshold_changed": False,
        "b3_status": b3_status,
        "formal_execution_started": False,
        "formal_run_purpose_if_later_authorized": "descriptive_negative_and_operating_envelope_only",
        "candidate_capability_role": "pilot_only_nonclaim_evidence",
        "candidate_only_can_be_reported_as_safe_acceleration": False,
        "lower_substitute_threshold_introduced": False,
        "decision_rule": (
            "operational failure first; fixed-budget failure second; otherwise "
            "stop prospectively because B3 promotion is structurally unreachable "
            "and no owner authorization for a full descriptive-negative run exists"
        ),
    }
    artifact_rows = _raw_pilot_artifact_rows(artifact_root)
    artifact_payload = tsv_bytes(
        (
            "artifact_path",
            "size_bytes",
            "sha256",
            "retention",
            "formal_source_data",
        ),
        artifact_rows,
    )
    artifact_digest = hashlib.sha256(artifact_payload).hexdigest()
    outputs = {
        PILOT_ARTIFACTS_PATH: artifact_payload,
        PILOT_ARTIFACTS_CHECKSUM_PATH: (
            f"{artifact_digest}  {PILOT_ARTIFACTS_PATH.name}\n".encode("ascii")
        ),
        PILOT_RECEIPT_PATH: canonical_json_bytes(pilot_receipt),
        RESOURCE_PROJECTION_PATH: canonical_json_bytes(projection),
        POSTPILOT_DECISION_PATH: canonical_json_bytes(postpilot),
    }
    require(
        not any(path.exists() or path.is_symlink() for path in outputs),
        "checked-in pilot receipt already exists and cannot be overwritten",
    )
    staged: dict[Path, Path] = {}
    published: list[Path] = []
    try:
        for destination, payload in outputs.items():
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.", suffix=".pilot-stage", dir=destination.parent
            )
            temporary = Path(temporary_name)
            staged[destination] = temporary
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        for destination, temporary in staged.items():
            os.replace(temporary, destination)
            published.append(destination)
    except BaseException:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
    return {
        "selected_decision": selected,
        "b3_status": b3_status,
        "pilot_receipt_sha256": sha256_file(PILOT_RECEIPT_PATH),
        "resource_projection_sha256": sha256_file(RESOURCE_PROJECTION_PATH),
        "raw_artifact_ledger_sha256": artifact_digest,
        "raw_artifact_count": len(artifact_rows),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    actions = result.add_mutually_exclusive_group(required=True)
    actions.add_argument("--generate-plan", action="store_true")
    actions.add_argument("--plan-only", action="store_true")
    actions.add_argument("--pilot", action="store_true")
    actions.add_argument("--formal-full", action="store_true")
    actions.add_argument("--formal-repeats", action="store_true")
    actions.add_argument("--summarize-pilot", action="store_true")
    result.add_argument("--runner-commit")
    result.add_argument("--resume", action="store_true")
    result.add_argument("--artifact-root", type=Path, default=CANONICAL_ARTIFACT_ROOT)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.generate_plan:
            require(args.runner_commit is not None, "--generate-plan requires --runner-commit")
            require(not args.resume, "--resume is not valid with --generate-plan")
            print(json.dumps(generate_frozen_plan(args.runner_commit), sort_keys=True))
            return 0
        require(args.runner_commit is None, "--runner-commit is valid only with --generate-plan")
        if args.plan_only:
            require(not args.resume, "--resume is not valid with --plan-only")
            print(json.dumps(plan_summary(), sort_keys=True))
            return 0
        if args.summarize_pilot:
            require(not args.resume, "--resume is not valid with --summarize-pilot")
            print(json.dumps(summarize_pilot(args.artifact_root), sort_keys=True))
            return 0
        stage = "pilot" if args.pilot else "formal_full" if args.formal_full else "formal_repeat"
        results = execute_stage(stage, resume=args.resume, artifact_root=args.artifact_root)
        print(json.dumps({"execution_stage": stage, "results": results}, sort_keys=True))
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Phase 3 application runner failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
