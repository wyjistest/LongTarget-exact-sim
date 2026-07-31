#!/usr/bin/env python3
"""Normative phase checker for the biological Top-K successor epoch."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/biological_topk_successor"
STATE_PATH = PAPER / "PROGRAM_STATE.json"
SCHEMA_PATH = ROOT / "schemas/biological_topk_successor_program_state.schema.json"
PROTOCOL_PATH = ROOT / "goal-biological-topk-successor.md"
PROTOCOL_SHA256 = "7404c52e0ef19db1ca48186fae610ff28bc9c4989febb5667ec09bfa4cc6f2f1"
PREDECESSOR_COMMIT = "7fae3de6b13780d7cc0776038489cf2f22072339"
PREDECESSOR_PROTOCOL_SHA256 = "1cd5e5a023d53655641ba831142f489011111fd2c166d895b2a851b0f513f6c3"
PREDECESSOR_STATE_SHA256 = "8c626090b68e9699a30ec3ee7ce3b0b448791d39fa9ede4d1af682236235ff63"
PREDECESSOR_DECISION_SHA256 = "d96fd8a0a8d7d86e7cfcbdd9e44a76affdaa8d175e609ace5ebd91a2ab5b398c"
PREDECESSOR_RECEIPT_SHA256 = "4b3c404a60853713e7823ea37c7695a03a1889b7c1a51ef13a413d61236cf4c6"
PREDECESSOR_MAKEFILE_SHA256 = "48caf9e1ceba4768b8a2782d6ccda2f874aea223c31b9d9770a0c135f96ac8fe"
EXECUTION_BRANCH = "gasal2-kcnq1ot1-focused-review"
FIXED_TOTAL_STORAGE_BYTES = 64 * 1024**3
SUCCESSOR_ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor"
PHASE0_COMMIT_MESSAGE = "docs: freeze biological Top-K successor validation epoch"
PHASE0_COMMIT = "4ef45838f9164b4c0e4f3cb16e22971e022e9f3d"
PHASE1_COMMIT_MESSAGE = "repro: freeze successor contract, source universe, and corrected resource gates"
PHASE1_COMMIT = "c68891dab08a777e54c9e301e8dd3515a11bcc31"
PHASE2_COMMIT_MESSAGE = "test: freeze successor candidate-site comparator regression"
PHASE2_COMMIT = "a48bcf814d4d055320ee1ab437666bde9d03d390"
PHASE3_COMMIT_MESSAGE = "repro: freeze successor fresh candidate-site holdout"
PHASE3_COMMIT = "7e3f46ee94df6651240052f5f317202129f73d05"
PHASE4_COMMIT_MESSAGE = "bench: freeze successor fresh candidate-site concordance decision"
PINNED_V1_AUDIT_COMMAND = ["python3", "scripts/check_biological_topk_successor_v1_audit.py"]
PHASE1_OUTPUTS = (
    "paper/biological_topk_successor/contract_binding.json",
    "paper/biological_topk_successor/information_feasibility.json",
    "paper/biological_topk_successor/query_source_universe.tsv.gz",
    "paper/biological_topk_successor/resource_decision.json",
    "paper/biological_topk_successor/resource_projection.json",
    "paper/biological_topk_successor/resource_projection_model.json",
    "paper/biological_topk_successor/source_universe_receipt.json",
    "paper/biological_topk_successor/successor_exclusion_registry.tsv",
    "paper/biological_topk_successor/target_source_universe.tsv.gz",
)
PHASE2_COMPONENTS = (
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/biological_topk/match_candidate_sites.py",
    "reproduce/biological_topk/compare_candidate_topk.py",
    "reproduce/biological_topk/exact_binomial_bounds.py",
    "reproduce/biological_topk/rank_diagnostics.py",
)
PHASE2_OUTPUTS = (
    "paper/biological_topk_successor/phase2_comparator_freeze.json",
    "paper/biological_topk_successor/phase2_known_cases.json",
    "paper/biological_topk_successor/phase2_regression_details.tsv",
    "paper/biological_topk_successor/phase2_regression_manifest.tsv",
    "paper/biological_topk_successor/phase2_regression_receipt.json",
    "paper/biological_topk_successor/phase2_regression_results.tsv",
)
PHASE3_OUTPUTS = (
    "paper/biological_topk_successor/fresh_holdout_attempt_plan.tsv",
    "paper/biological_topk_successor/fresh_holdout_manifest.sha256",
    "paper/biological_topk_successor/fresh_holdout_manifest.tsv",
    "paper/biological_topk_successor/fresh_holdout_plan.json",
    "paper/biological_topk_successor/fresh_holdout_resource_decision.json",
    "paper/biological_topk_successor/fresh_holdout_resource_projection.json",
)
PHASE4_OUTPUTS = (
    "paper/biological_topk_successor/fresh_holdout_actual_resources.json",
    "paper/biological_topk_successor/fresh_holdout_decision.json",
    "paper/biological_topk_successor/fresh_holdout_receipt.json",
    "paper/biological_topk_successor/source_data/fresh_candidate_matches.tsv",
    "paper/biological_topk_successor/source_data/fresh_empty_workloads.tsv",
    "paper/biological_topk_successor/source_data/fresh_exact_binomial_bounds.tsv",
    "paper/biological_topk_successor/source_data/fresh_failure_ledger.tsv",
    "paper/biological_topk_successor/source_data/fresh_rank_diagnostics.tsv",
    "paper/biological_topk_successor/source_data/fresh_workload_metrics.tsv",
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V1_CHECKER = load_module("biological_topk_v1_checker", ROOT / "scripts/check_biological_topk_phase.py")
SchemaValidationError = V1_CHECKER.SchemaValidationError


class CheckError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def run(
    arguments: Sequence[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        tuple(arguments),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if check and completed.returncode != 0:
        raise CheckError(
            completed.stderr.decode("utf-8", errors="replace")
            or completed.stdout.decode("utf-8", errors="replace")
            or f"command failed: {arguments}"
        )
    return completed


def git(*arguments: str) -> str:
    return run(("git", *arguments)).stdout.decode("utf-8").strip()


def git_bytes(*arguments: str) -> bytes:
    return run(("git", *arguments)).stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    ).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckError(f"invalid JSON {path}: {error}") from error


def load_json_from_commit(commit: str, relative: str) -> Any:
    try:
        return json.loads(git_bytes("show", f"{commit}:{relative}").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckError(f"invalid committed JSON {commit}:{relative}: {error}") from error


def directory_file_bytes(path: Path) -> int:
    require(path.is_dir() and not path.is_symlink(), f"missing or unsafe artifact root: {path}")
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    require(fields and all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return fields, rows


def changed_paths() -> set[str]:
    return V1_CHECKER.changed_paths()


def validate_schema(value: Any, schema: dict[str, Any]) -> None:
    V1_CHECKER.validate_schema(value, schema)


def validate_state_transitions(state: dict[str, Any]) -> None:
    statuses = state["phase_status"]
    require(set(statuses) == {str(index) for index in range(10)}, "successor phase keys drift")
    require(state["predecessor_commit"] == PREDECESSOR_COMMIT, "predecessor commit drift")
    require(state["predecessor_decision"] == "blocked_fixed_budget", "predecessor decision drift")
    require(state["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES, "successor quota drift")
    if state["gpu_screen_status"] == "validated_screening_backend_v1_release_candidate":
        require(statuses["8"] == "pass", "premature successor product promotion")
        require(state["contract_status"] == "validated_within_fixed_operating_envelope", "validated product contract drift")
    blocking = [
        index
        for index in range(10)
        if statuses[str(index)] == "no_go" or statuses[str(index)].startswith("blocked_")
    ]
    if blocking:
        first = min(blocking)
        require(state["active_phase"] is None, "blocked successor state must be terminal")
        require(state["last_completed_phase"] == first, "blocked successor phase completion drift")
        for later in range(first + 1, 10):
            require(statuses[str(later)] in {"pending", "not_authorized_previous_no_go"}, "later successor phase advanced after block")


def validate_program_state() -> dict[str, Any]:
    schema = load_json(SCHEMA_PATH)
    state = load_json(STATE_PATH)
    validate_program_state_value(state, schema)
    return state


def validate_program_state_value(state: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    if schema is None:
        schema = load_json(SCHEMA_PATH)
    validate_schema(state, schema)
    validate_state_transitions(state)


def allowlist(phase: int) -> list[str]:
    path = PAPER / f"phase_{phase}_change_allowlist.txt"
    require(path.is_file() and not path.is_symlink(), f"missing successor Phase {phase} allowlist")
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(rows == sorted(set(rows)), f"successor Phase {phase} allowlist must be sorted and unique")
    require(all(not Path(row).is_absolute() and ".." not in Path(row).parts for row in rows), "unsafe successor allowlist")
    return rows


def allowlist_from_commit(phase: int, commit: str) -> list[str]:
    relative = f"paper/biological_topk_successor/phase_{phase}_change_allowlist.txt"
    rows = [
        line.strip()
        for line in git_bytes("show", f"{commit}:{relative}").decode("utf-8").splitlines()
        if line.strip()
    ]
    require(rows == sorted(set(rows)), f"committed successor Phase {phase} allowlist drift")
    return rows


def check_precommit_receipt(
    phase: int,
    paths: list[str],
    *,
    committed_at: str | None = None,
) -> None:
    relative = f"paper/biological_topk_successor/phase_{phase}_precommit_receipt.json"
    receipt = load_json_from_commit(committed_at, relative) if committed_at else load_json(ROOT / relative)
    require(receipt["schema_version"] == 1 and receipt["phase"] == phase, "successor precommit receipt schema drift")
    require(receipt["expected_changed_paths"] == paths, "successor precommit path inventory drift")
    require(
        receipt["checker_command"]
        == ["python3", "scripts/check_biological_topk_successor_phase.py", "--phase", str(phase), "--mode", "precommit"],
        "successor precommit command drift",
    )
    require(receipt["checker_result"] == "pass", "successor precommit receipt did not pass")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "successor receipt claims self/future commit")
    expected_evidence = set(paths) - {relative}
    require(set(receipt["schema_evidence_sha256"]) == expected_evidence, "successor precommit evidence inventory drift")
    expected_messages = {
        0: PHASE0_COMMIT_MESSAGE,
        1: PHASE1_COMMIT_MESSAGE,
        2: PHASE2_COMMIT_MESSAGE,
        3: PHASE3_COMMIT_MESSAGE,
        4: PHASE4_COMMIT_MESSAGE,
    }
    if phase in expected_messages:
        require(receipt["planned_commit_message"] == expected_messages[phase], "successor planned commit message drift")
    for relative, digest in receipt["schema_evidence_sha256"].items():
        observed = (
            hashlib.sha256(git_bytes("show", f"{committed_at}:{relative}")).hexdigest()
            if committed_at
            else sha256_file(ROOT / relative)
        )
        require(observed == digest, f"successor precommit evidence drift: {relative}")


def check_v1_registry() -> None:
    completed = run(
        (sys.executable, "reproduce/biological_topk_successor/build_v1_evidence_registry.py", "--check"),
        check=False,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))
    fields, rows = read_tsv(PAPER / "v1_evidence_registry.tsv")
    require(
        fields == ["path", "frozen_at_commit", "git_blob_sha1", "blob_sha256", "size_bytes", "evidence_role"],
        "predecessor registry schema drift",
    )
    require(len(rows) >= 50, "predecessor registry is incomplete")
    for row in rows:
        require(row["frozen_at_commit"] == PREDECESSOR_COMMIT, "predecessor registry commit drift")
        require(row["evidence_role"] == "immutable_predecessor_validation_evidence", "predecessor role drift")
        path = ROOT / row["path"]
        require(path.is_file() and not path.is_symlink(), f"missing predecessor tracked evidence: {row['path']}")
        require(path.stat().st_size == int(row["size_bytes"]), f"predecessor tracked size drift: {row['path']}")
        require(sha256_file(path) == row["blob_sha256"], f"predecessor tracked digest drift: {row['path']}")


def check_v1_boundary() -> None:
    boundary = load_json(PAPER / "v1_artifact_boundary.json")
    require(boundary["schema_version"] == 1, "predecessor boundary schema drift")
    require(boundary["predecessor_commit"] == PREDECESSOR_COMMIT, "predecessor boundary commit drift")
    require(boundary["decision"] == "blocked_fixed_budget", "predecessor boundary decision drift")
    require(boundary["comparison_started"] is False and boundary["scientific_decision_reached"] is False, "predecessor boundary invented a scientific decision")
    require(boundary["predecessor_protocol_sha256"] == PREDECESSOR_PROTOCOL_SHA256, "predecessor protocol binding drift")
    require(boundary["predecessor_program_state_sha256"] == PREDECESSOR_STATE_SHA256, "predecessor state binding drift")
    require(boundary["decision_sha256"] == PREDECESSOR_DECISION_SHA256, "predecessor decision binding drift")
    require(boundary["predecessor_receipt_sha256"] == PREDECESSOR_RECEIPT_SHA256, "predecessor receipt binding drift")
    require(boundary["aggregate_checker_command"] == PINNED_V1_AUDIT_COMMAND, "predecessor pinned audit command drift")
    require(boundary["aggregate_checker_required_result"] == "pass", "predecessor pinned audit result drift")
    require(sha256_file(ROOT / "goal-biological-topk.md") == PREDECESSOR_PROTOCOL_SHA256, "live predecessor protocol drift")
    require(sha256_file(ROOT / "paper/biological_topk/PROGRAM_STATE.json") == PREDECESSOR_STATE_SHA256, "live predecessor state drift")
    require(sha256_file(ROOT / "paper/biological_topk/fresh_holdout_decision.json") == PREDECESSOR_DECISION_SHA256, "live predecessor decision drift")
    require(sha256_file(ROOT / "paper/biological_topk/fresh_holdout_receipt.json") == PREDECESSOR_RECEIPT_SHA256, "live predecessor receipt drift")
    total = 0
    for item in boundary["artifact_roots"]:
        path = ROOT / item["path"]
        require(item["mutable"] is False, "predecessor artifact root marked mutable")
        observed = directory_file_bytes(path)
        require(observed == item["logical_file_bytes"], f"predecessor artifact byte drift: {item['path']}")
        require(sha256_file(path / "run-summary.json") == item["run_summary_sha256"], f"predecessor summary drift: {item['path']}")
        total += observed
    require(total == boundary["total_logical_file_bytes"] == 7142325727, "predecessor total artifact bytes drift")

    old_state = load_json(ROOT / "paper/biological_topk/PROGRAM_STATE.json")
    require(old_state["active_phase"] is None and old_state["phase_status"]["4"] == "blocked_fixed_budget", "predecessor terminal state reopened")
    require(all(old_state["phase_status"][str(index)] == "not_authorized_previous_no_go" for index in range(5, 10)), "predecessor later phase authorized")


def check_authorization() -> None:
    authorization = load_json(PAPER / "owner_successor_authorization.json")
    require(authorization["schema_version"] == 1, "successor authorization schema drift")
    require(authorization["approval_message"] == "\u6279\u51c6", "successor approval message drift")
    require(authorization["approved_by"] == "repository_owner_via_active_codex_thread", "successor approval authority drift")
    require(authorization["predecessor_commit"] == PREDECESSOR_COMMIT, "successor approval predecessor drift")
    require(authorization["max_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES, "successor approved quota drift")
    require(authorization["includes_predecessor_artifact_bytes"] is True, "successor quota excludes predecessor evidence")
    require(authorization["predecessor_evidence_may_be_modified"] is False, "successor approval permits predecessor mutation")
    require(authorization["quota_may_be_raised_after_successor_phase3_projection"] is False, "successor quota remains adjustable")
    require(authorization["protocol_sha256"] == PROTOCOL_SHA256, "successor authorization protocol drift")


def check_phase0_receipts() -> None:
    start = load_json(PAPER / "phase_0_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 0, "successor Phase 0 start schema drift")
    require(start["execution_start_head"] == PREDECESSOR_COMMIT, "successor Phase 0 start HEAD drift")
    require(start["previous_epoch_commit"] == PREDECESSOR_COMMIT, "successor previous epoch binding drift")
    require(start["execution_branch"] == EXECUTION_BRANCH, "successor execution branch drift")
    require(start["owner_approval_message"] == "\u6279\u51c6", "successor start approval drift")
    require(start["protocol_sha256"] == PROTOCOL_SHA256, "successor start protocol drift")
    require(start["clean_start_check"] == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""}, "successor clean-start evidence drift")
    require(start["status"] == "pass", "successor Phase 0 start did not pass")
    require(sha256_file(PROTOCOL_PATH) == PROTOCOL_SHA256, "successor protocol file drift")

    epoch = load_json(PAPER / "epoch_receipt.json")
    require(epoch["schema_version"] == 1 and epoch["epoch_id"] == "biological_topk_successor_v2", "successor epoch receipt drift")
    require(epoch["execution_start_head"] == PREDECESSOR_COMMIT, "successor epoch start drift")
    require(epoch["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES, "successor epoch quota drift")
    require(epoch["new_scientific_run_started"] is False, "successor Phase 0 started a scientific run")
    require(epoch["successor_artifact_root_exists"] is False, "successor epoch receipt claims runtime output")
    require(epoch["protocol_sha256"] == PROTOCOL_SHA256, "successor epoch protocol drift")
    require(epoch["owner_authorization_sha256"] == sha256_file(PAPER / "owner_successor_authorization.json"), "successor epoch authorization digest drift")
    require(epoch["predecessor_evidence_registry_sha256"] == sha256_file(PAPER / "v1_evidence_registry.tsv"), "successor epoch registry digest drift")
    require(epoch["predecessor_aggregate_check"] == {"command": PINNED_V1_AUDIT_COMMAND, "required_result": "pass"}, "successor epoch pinned audit receipt drift")


def check_phase0_state(state: dict[str, Any]) -> None:
    require(state["phase_status"]["0"] == "pass", "successor Phase 0 final state must pass")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(1, 10)), "successor later phase advanced during Phase 0")
    require(state["active_phase"] == 1 and state["last_completed_phase"] == 0, "successor Phase 0 transition drift")
    require(state["last_decision"] == "successor_phase_0_protocol_frozen", "successor Phase 0 decision drift")
    require(state["contract_status"] == "in_validation", "successor Phase 0 contract drift")
    require(state["gpu_screen_status"] == "experimental", "successor Phase 0 promoted product status")
    require(state["score_representation"] == "pending_phase1", "successor Phase 0 pre-decided score representation")
    require(state["previous_phase_commit"] is None, "successor Phase 0 claims a previous successor phase")


def run_phase0_unit_tests() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/biological_topk_successor",
            "-p",
            "test_phase0.py",
            "-v",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def run_predecessor_phase4_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (
            sys.executable,
            "reproduce/biological_topk/adjudicate_fresh_holdout_repair1_budget_stop.py",
            "--check",
            "--artifact-root",
            ".paper-artifacts/biological-topk/fresh-holdout-repair1",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def run_predecessor_aggregate() -> None:
    completed = run(
        (sys.executable, "scripts/check_biological_topk_successor_v1_audit.py"),
        check=False,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))
    require(b"pinned predecessor Phase 0-4 aggregate audit OK" in completed.stdout, "predecessor aggregate success marker missing")


def phase_commit_for_postcommit(phase: int) -> str:
    next_start = PAPER / f"phase_{phase + 1}_start_receipt.json"
    if phase < 9 and next_start.is_file():
        receipt = load_json(next_start)
        commit = receipt.get("previous_phase_commit")
        require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), "next successor phase does not bind previous commit")
        return commit
    return git("rev-parse", "HEAD")


def check_phase0(mode: str, state: dict[str, Any], status_before: set[str]) -> None:
    if mode == "postcommit":
        require(not status_before, "successor Phase 0 postcommit requires a clean tree")
        commit = phase_commit_for_postcommit(0)
        phase_state = load_json_from_commit(commit, "paper/biological_topk_successor/PROGRAM_STATE.json")
        validate_program_state_value(phase_state)
        paths = allowlist_from_commit(0, commit)
        check_precommit_receipt(0, paths, committed_at=commit)
    else:
        phase_state = state
        paths = allowlist(0)
        check_precommit_receipt(0, paths)

    check_phase0_state(phase_state)
    check_authorization()
    check_phase0_receipts()
    check_v1_registry()
    check_v1_boundary()
    if mode == "precommit":
        require(not SUCCESSOR_ARTIFACT_ROOT.exists(), "successor scientific artifact root exists during Phase 0")
    run_phase0_unit_tests()
    run_predecessor_phase4_reproduction()

    if mode == "precommit":
        head = git("rev-parse", "HEAD")
        observed = changed_paths()
        if head == PREDECESSOR_COMMIT:
            prospective = observed
        else:
            require(git("rev-parse", "HEAD^") == PREDECESSOR_COMMIT, "successor Phase 0 amend parent drift")
            require(git("log", "-1", "--format=%s") == PHASE0_COMMIT_MESSAGE, "unexpected successor Phase 0 amend target")
            correction_only = observed - set(paths)
            require(correction_only <= {"Makefile"}, "successor Phase 0 correction touched an unexpected path")
            if "Makefile" in correction_only:
                require(sha256_file(ROOT / "Makefile") == PREDECESSOR_MAKEFILE_SHA256, "Phase 0 correction did not restore predecessor Makefile")
            prospective = set(git("diff", "--name-only", "HEAD^").splitlines())
        require(prospective == set(paths), "successor Phase 0 allowlisted diff mismatch")
    elif mode == "postcommit":
        commit = phase_commit_for_postcommit(0)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "successor Phase 0 commit is not an ancestor")
        require(git("rev-parse", f"{commit}^") == PREDECESSOR_COMMIT, "successor Phase 0 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE0_COMMIT_MESSAGE, "successor Phase 0 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "successor Phase 0 committed paths differ from allowlist")
        run_predecessor_aggregate()
    else:
        raise CheckError(f"unsupported successor Phase 0 mode: {mode}")


def read_gzip_tsv(path: Path) -> tuple[list[str], list[dict[str, str]], bytes]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe gzip TSV: {path}")
    compressed = path.read_bytes()
    require(compressed[:2] == b"\x1f\x8b" and compressed[4:8] == b"\0\0\0\0", f"nondeterministic gzip header: {path}")
    try:
        payload = gzip.decompress(compressed)
        text = payload.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CheckError(f"invalid gzip TSV {path}: {error}") from error
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    fields = list(reader.fieldnames or [])
    rows = list(reader)
    require(fields and all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed gzip TSV: {path}")
    return fields, rows, payload


def check_phase1_start_receipt() -> None:
    start = load_json(PAPER / "phase_1_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 1, "successor Phase 1 start schema drift")
    require(start["phase_start_parent_head"] == PHASE0_COMMIT, "successor Phase 1 parent HEAD drift")
    require(start["previous_phase_number"] == 0, "successor Phase 1 previous phase drift")
    require(start["previous_phase_commit"] == PHASE0_COMMIT, "successor Phase 1 previous commit drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_successor_phase.py", "--phase", "0", "--mode", "postcommit"],
        "successor Phase 1 previous checker command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "successor Phase 0 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "successor Phase 1 clean-start evidence drift",
    )
    require(start["status"] == "pass", "successor Phase 1 start did not pass")


def run_phase1_unit_tests() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/biological_topk_successor",
            "-p",
            "test_phase1.py",
            "-v",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase1_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (sys.executable, "reproduce/biological_topk_successor/freeze_phase1.py", "--check"),
        check=False,
        env=environment,
    )
    require(
        completed.returncode == 0,
        completed.stderr.decode("utf-8", errors="replace") or "successor Phase 1 artifacts do not reproduce",
    )


def check_phase1_evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    require(sha256_file(PROTOCOL_PATH) == PROTOCOL_SHA256, "successor protocol digest drift")
    for relative in (*PHASE1_OUTPUTS, "reproduce/biological_topk_successor/freeze_phase1.py"):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing successor Phase 1 evidence: {relative}")

    contract = load_json(PAPER / "contract_binding.json")
    require(contract["schema_version"] == 1 and contract["status"] == "exact_predecessor_contract_reused", "successor contract binding drift")
    require(contract["contract_name"] == "biological_topk_candidate_site_v1", "successor contract name drift")
    require(contract["scientific_contract_changed"] is False, "successor scientific contract changed")
    require(contract["comparator_changed"] is False and contract["threshold_changed"] is False, "successor comparator or threshold changed")
    require((contract["N_panel"], contract["n_binary_required"], contract["k_min"], contract["allowed_failures"]) == (178, 124, 122, 2), "successor statistical boundary drift")
    require(contract["score_representation"] == "integral_exact" and contract["rank_order_claim"] == "diagnostic_only", "successor score/rank contract drift")
    require(
        contract["bindings"] == {relative: sha256_file(ROOT / relative) for relative in contract["bindings"]},
        "successor predecessor contract binding digest drift",
    )
    require(len(contract["bindings"]) == 24, "successor contract binding inventory drift")

    source = load_json(PAPER / "source_universe_receipt.json")
    require(source["schema_version"] == 1 and source["status"] == "successor_source_universe_frozen", "successor source receipt drift")
    require(source["assembly"] == "GRCh38" and source["annotation_release"] == "GENCODE v49", "successor source release drift")
    require(source["fresh_pair_selected"] is False and source["new_prediction_run"] is False, "successor Phase 1 selected or ran a fresh pair")
    require(source["predecessor_overlap_allowed"] is False, "successor source permits predecessor overlap")

    query_path = PAPER / "query_source_universe.tsv.gz"
    target_path = PAPER / "target_source_universe.tsv.gz"
    query_fields, query_rows, query_payload = read_gzip_tsv(query_path)
    target_fields, target_rows, target_payload = read_gzip_tsv(target_path)
    require({"query_ordinal_namespace", "source_ordinal", "sequence_sha256", "operating_envelope_eligible", "historical_exclusion_status"} <= set(query_fields), "successor query universe schema drift")
    require({"target_ordinal_namespace", "source_ordinal", "sequence_sha256", "target_scale_stratum", "operating_envelope_eligible", "historical_exclusion_status"} <= set(target_fields), "successor target universe schema drift")
    require(source["query_universe"]["gzip_sha256"] == sha256_file(query_path), "successor query gzip digest drift")
    require(source["target_universe"]["gzip_sha256"] == sha256_file(target_path), "successor target gzip digest drift")
    require(source["query_universe"]["uncompressed_tsv_sha256"] == hashlib.sha256(query_payload).hexdigest(), "successor query TSV digest drift")
    require(source["target_universe"]["uncompressed_tsv_sha256"] == hashlib.sha256(target_payload).hexdigest(), "successor target TSV digest drift")

    old_fields, old_manifest = read_tsv(ROOT / "paper/biological_topk/fresh_holdout_manifest.tsv")
    require(len(old_manifest) == 178 and "input_pair_digest" in old_fields, "predecessor Phase 4 manifest drift")
    old_query_digests = {row["query_sequence_sha256"] for row in old_manifest}
    old_query_ordinals = {(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in old_manifest}
    old_target_digests = {row["target_sequence_sha256"] for row in old_manifest}
    old_target_ordinals = {(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in old_manifest}
    eligible_queries = [row for row in query_rows if row["operating_envelope_eligible"] == "1" and row["historical_exclusion_status"] == "fresh_eligible"]
    eligible_targets = [row for row in target_rows if row["operating_envelope_eligible"] == "1" and row["historical_exclusion_status"] == "fresh_eligible"]
    require(not old_query_digests & {row["sequence_sha256"] for row in eligible_queries}, "predecessor query digest remains successor-eligible")
    require(not old_query_ordinals & {(row["query_ordinal_namespace"], row["source_ordinal"]) for row in eligible_queries}, "predecessor query ordinal remains successor-eligible")
    require(not old_target_digests & {row["sequence_sha256"] for row in eligible_targets}, "predecessor target digest remains successor-eligible")
    require(not old_target_ordinals & {(row["target_ordinal_namespace"], row["source_ordinal"]) for row in eligible_targets}, "predecessor target ordinal remains successor-eligible")

    query_summary = source["query_universe"]
    require(query_summary["row_count"] == len(query_rows) == 27139, "successor query row count drift")
    require(query_summary["predecessor_identity_excluded_row_count"] == 178, "successor query predecessor exclusion count drift")
    require(query_summary["fresh_eligible_row_count"] == len(eligible_queries) == 26903, "successor eligible query count drift")
    require(query_summary["fresh_unique_namespaced_ordinal_count"] == len({(row["query_ordinal_namespace"], row["source_ordinal"]) for row in eligible_queries}), "successor unique query ordinal count drift")
    require(query_summary["fresh_unique_sequence_digest_count"] == len({row["sequence_sha256"] for row in eligible_queries}) == 26882, "successor unique query digest count drift")

    target_summary = source["target_universe"]
    require(target_summary["row_count"] == len(target_rows) == 2004, "successor target row count drift")
    require(target_summary["predecessor_identity_excluded_row_count"] == 309, "successor target predecessor exclusion count drift")
    quotas = {"short": 60, "medium": 59, "large": 59}
    expected_unique = {"short": 606, "medium": 559, "large": 480}
    for stratum, required in quotas.items():
        selected = [row for row in eligible_targets if row["target_scale_stratum"] == stratum]
        summary = target_summary["strata"][stratum]
        require(summary["required"] == required, f"successor {stratum} target quota drift")
        require(summary["fresh_eligible_row_count"] == len(selected), f"successor {stratum} eligible target count drift")
        require(summary["fresh_unique_namespaced_ordinal_count"] == len({(row["target_ordinal_namespace"], row["source_ordinal"]) for row in selected}), f"successor {stratum} target ordinal count drift")
        require(summary["fresh_unique_sequence_digest_count"] == len({row["sequence_sha256"] for row in selected}) == expected_unique[stratum], f"successor {stratum} target digest count drift")
        require(summary["fresh_unique_sequence_digest_count"] >= required, f"successor {stratum} target capacity failed")

    exclusion_fields, exclusions = read_tsv(PAPER / "successor_exclusion_registry.tsv")
    base_fields, base_exclusions = read_tsv(ROOT / "paper/biological_topk/fresh_input_exclusion_registry.tsv")
    require(exclusion_fields == base_fields and exclusions[: len(base_exclusions)] == base_exclusions, "successor exclusion registry does not preserve its base")
    added = exclusions[len(base_exclusions) :]
    require(len(base_exclusions) == 1455 and len(added) == 178 and len(exclusions) == 1633, "successor exclusion registry count drift")
    require(all(row["exclusion_reason"] == "predecessor_phase4_fresh_concordance_input" for row in added), "successor predecessor exclusion reason drift")
    require({row["pair_digest"] for row in added} == {row["input_pair_digest"] for row in old_manifest}, "successor predecessor pair exclusion coverage drift")
    exclusion_summary = source["exclusion_registry"]
    require(exclusion_summary["sha256"] == sha256_file(PAPER / "successor_exclusion_registry.tsv"), "successor exclusion registry digest drift")
    require((exclusion_summary["base_exclusion_count"], exclusion_summary["predecessor_phase4_added_count"], exclusion_summary["total_exclusion_count"]) == (1455, 178, 1633), "successor exclusion receipt count drift")

    information = load_json(PAPER / "information_feasibility.json")
    require(information["schema_version"] == 1 and information["status"] == "pass", "successor information gate did not pass")
    require(information["contract_binding_sha256"] == sha256_file(PAPER / "contract_binding.json"), "successor information contract digest drift")
    require(information["source_universe_receipt_sha256"] == sha256_file(PAPER / "source_universe_receipt.json"), "successor information source digest drift")
    require(information["fresh_pair_selected"] is False and information["new_prediction_run"] is False, "successor information plan ran fresh work")
    require(information["predecessor_overlap_count"] == 0 and information["all_information_gates_pass"] is True, "successor information gates failed")
    query_capacity = {
        key: query_summary[key]
        for key in (
            "row_count",
            "predecessor_identity_excluded_row_count",
            "fresh_eligible_row_count",
            "fresh_unique_namespaced_ordinal_count",
            "fresh_unique_sequence_digest_count",
        )
    }
    target_capacity = {
        key: target_summary[key]
        for key in ("row_count", "predecessor_identity_excluded_row_count", "strata")
    }
    require(
        information["source_capacity"]
        == {
            "query_gate_pass": True,
            "target_gate_pass_by_stratum": {"large": True, "medium": True, "short": True},
            "query": query_capacity,
            "target": target_capacity,
        },
        "successor information capacity receipt drift",
    )

    model = load_json(PAPER / "resource_projection_model.json")
    require(model["schema_version"] == 1 and model["status"] == "corrected_from_predecessor_observed_execution", "successor resource model status drift")
    require(model["resource_values_are_performance_claims"] is False and model["scientific_output_fields_read"] is False, "successor resource model used scientific output")
    require(model["observation_source"] == "terminal_attempt_receipts_and_directory_file_bytes_only", "successor resource observation source drift")
    require(model["predecessor_manifest_sha256"] == sha256_file(ROOT / "paper/biological_topk/fresh_holdout_manifest.tsv"), "successor resource manifest binding drift")
    require(model["predecessor_actual_resources_sha256"] == sha256_file(ROOT / "paper/biological_topk/fresh_holdout_actual_resources.json"), "successor actual-resource binding drift")
    require(model["predecessor_run_summary_sha256"] == sha256_file(ROOT / ".paper-artifacts/biological-topk/fresh-holdout-repair1/run-summary.json"), "successor resource run-summary binding drift")
    observations = model["observations"]
    expected_observation_fields = {"attempt_id", "arm", "target_scale_stratum", "query_length", "target_length", "wall_seconds", "artifact_storage_bytes"}
    require(len(observations) == 165 and len({row["attempt_id"] for row in observations}) == 165, "successor resource observation count drift")
    require(all(set(row) == expected_observation_fields for row in observations), "successor resource observation field drift")
    require(sum(row["arm"] == "A" for row in observations) == 83 and sum(row["arm"] == "G" for row in observations) == 82, "successor resource arm count drift")
    require(all(float(row["wall_seconds"]) > 0 and int(row["artifact_storage_bytes"]) > 0 for row in observations), "successor resource observation is nonpositive")

    projection = load_json(PAPER / "resource_projection.json")
    require(projection["schema_version"] == 1 and projection["status"] == "pass", "successor resource projection did not pass")
    require(projection["resource_projection_model_sha256"] == sha256_file(PAPER / "resource_projection_model.json"), "successor resource model digest drift")
    require(projection["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES, "successor projected quota drift")
    require(projection["includes_predecessor_artifact_bytes"] is True and projection["quota_may_be_raised_after_phase3_projection"] is False, "successor quota semantics drift")
    values = projection["projection"]
    storage = values["artifact_storage_bytes"]
    require((values["planned_primary_workloads"], values["planned_validation_instances"], values["planned_attempts_per_arm"], values["technical_repeats"]) == (178, 184, 184, 6), "successor resource attempt plan drift")
    require(storage["predecessor_retained"] == 7142325727 and storage["raw_g_reservation"] == 1536 * 1024**2, "successor retained/raw reservation drift")
    require(storage["total_point_with_reservation"] == storage["predecessor_retained"] + storage["successor_point"] + storage["raw_g_reservation"], "successor point storage arithmetic drift")
    require(storage["total_upper_95_with_reservation"] == storage["predecessor_retained"] + storage["successor_upper_95"] + storage["raw_g_reservation"], "successor upper storage arithmetic drift")
    require(storage["total_max_observed_stress_with_reservation"] == storage["predecessor_retained"] + storage["successor_max_observed_per_arm_stress"] + storage["raw_g_reservation"], "successor stress storage arithmetic drift")
    require(storage["gate_basis"] == max(storage["total_upper_95_with_reservation"], storage["total_max_observed_stress_with_reservation"]), "successor storage gate basis drift")
    require(storage["quota"] == FIXED_TOTAL_STORAGE_BYTES and storage["margin"] == FIXED_TOTAL_STORAGE_BYTES - storage["gate_basis"], "successor storage margin drift")
    require(storage["gate_pass"] is True and storage["margin"] > 0, "successor storage gate failed")
    require(values["gpu_hours"]["limit"] == 72 and float(values["gpu_hours"]["upper_95"]) <= 72 and values["gpu_hours"]["gate_pass"] is True, "successor GPU-hour gate failed")
    require(values["scheduled_elapsed_wall_seconds"]["limit"] == 172800 and float(values["scheduled_elapsed_wall_seconds"]["upper_95"]) <= 172800 and values["scheduled_elapsed_wall_seconds"]["gate_pass"] is True, "successor wall-time gate failed")

    decision = load_json(PAPER / "resource_decision.json")
    require(decision["schema_version"] == 1 and decision["phase"] == 1 and decision["decision"] == "pass", "successor Phase 1 resource decision drift")
    require(decision["resource_projection_sha256"] == sha256_file(PAPER / "resource_projection.json"), "successor resource projection digest drift")
    require(decision["resource_projection_model_sha256"] == sha256_file(PAPER / "resource_projection_model.json"), "successor resource decision model digest drift")
    require(decision["fresh_pair_selected"] is False and decision["new_prediction_run"] is False, "successor resource decision ran fresh work")
    require(decision["all_resource_gates_pass"] is True and decision["later_phase_authorized_if_state_committed"] is True, "successor resource decision blocks later phases")
    require(all(decision[key] is True for key in ("artifact_storage_gate_pass", "gpu_hours_gate_pass", "scheduled_wall_gate_pass")), "successor resource subgate failed")
    return information, decision


def check_phase1_state(state: dict[str, Any], information: dict[str, Any], decision: dict[str, Any]) -> None:
    require(state["phase_status"]["0"] == state["phase_status"]["1"] == "pass", "successor Phase 1 prerequisite/final status drift")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(2, 10)), "successor later phase advanced during Phase 1")
    require(information["all_information_gates_pass"] is True and decision["all_resource_gates_pass"] is True, "successor Phase 1 pass lacks all gates")
    require(state["active_phase"] == 2 and state["last_completed_phase"] == 1, "successor Phase 1 transition drift")
    require(state["last_decision"] == "successor_phase_1_contract_frozen", "successor Phase 1 decision drift")
    require(state["previous_phase_commit"] == PHASE0_COMMIT, "successor Phase 1 previous commit drift")
    require(state["score_representation"] == "integral_exact", "successor Phase 1 score representation drift")
    require(state["contract_status"] == "in_validation" and state["gpu_screen_status"] == "experimental", "successor Phase 1 promoted product status")
    require(state["bioinformatics_route"] == "conditionally_reopened" and state["rank_order_claim"] == "diagnostic_only", "successor Phase 1 claim scope drift")


def check_phase1(mode: str, current_state: dict[str, Any], status_before: set[str]) -> None:
    check_phase1_start_receipt()
    check_phase1_reproduction()
    information, decision = check_phase1_evidence()
    run_phase1_unit_tests()
    if mode == "precommit":
        paths = allowlist(1)
        check_precommit_receipt(1, paths)
        check_phase1_state(current_state, information, decision)
        head = git("rev-parse", "HEAD")
        if head == PHASE0_COMMIT:
            prospective = changed_paths()
        else:
            require(git("rev-parse", "HEAD^") == PHASE0_COMMIT, "successor Phase 1 amend parent drift")
            require(git("log", "-1", "--format=%s") == PHASE1_COMMIT_MESSAGE, "unexpected successor Phase 1 amend target")
            require(changed_paths() <= set(paths), "successor Phase 1 correction touched a path outside the allowlist")
            prospective = set(git("diff", "--name-only", "HEAD^").splitlines())
        require(prospective == set(paths), "successor Phase 1 allowlisted diff mismatch")
        require(not SUCCESSOR_ARTIFACT_ROOT.exists(), "successor Phase 1 created a scientific artifact root")
    elif mode == "postcommit":
        require(not status_before, "successor Phase 1 postcommit requires a clean tree")
        commit = phase_commit_for_postcommit(1)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "successor Phase 1 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk_successor/PROGRAM_STATE.json")
        validate_program_state_value(state)
        paths = allowlist_from_commit(1, commit)
        check_precommit_receipt(1, paths, committed_at=commit)
        check_phase1_state(state, information, decision)
        require(git("rev-parse", f"{commit}^") == PHASE0_COMMIT, "successor Phase 1 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE1_COMMIT_MESSAGE, "successor Phase 1 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "successor Phase 1 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported successor Phase 1 mode: {mode}")


def check_phase2_start_receipt() -> None:
    start = load_json(PAPER / "phase_2_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 2, "successor Phase 2 start schema drift")
    require(start["phase_start_parent_head"] == PHASE1_COMMIT, "successor Phase 2 parent HEAD drift")
    require(start["previous_phase_number"] == 1 and start["previous_phase_commit"] == PHASE1_COMMIT, "successor Phase 2 previous phase binding drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_successor_phase.py", "--phase", "1", "--mode", "postcommit"],
        "successor Phase 2 previous checker command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "successor Phase 1 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "successor Phase 2 clean-start evidence drift",
    )
    require(start["status"] == "pass", "successor Phase 2 start did not pass")


def check_phase2_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (sys.executable, "reproduce/biological_topk_successor/freeze_phase2.py", "--check"),
        check=False,
        env=environment,
    )
    require(
        completed.returncode == 0,
        completed.stderr.decode("utf-8", errors="replace") or "successor Phase 2 regression does not reproduce",
    )


def run_phase2_unit_tests() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    commands = (
        (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/biological_topk",
            "-p",
            "test_phase2_comparator.py",
            "-v",
        ),
        (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/biological_topk_successor",
            "-p",
            "test_phase2.py",
            "-v",
        ),
    )
    for command in commands:
        completed = run(command, check=False, env=environment)
        require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase2_evidence() -> None:
    for relative in (*PHASE2_COMPONENTS, *PHASE2_OUTPUTS, "reproduce/biological_topk_successor/freeze_phase2.py"):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing successor Phase 2 evidence: {relative}")

    regression_names = (
        "phase2_known_cases.json",
        "phase2_regression_details.tsv",
        "phase2_regression_manifest.tsv",
        "phase2_regression_receipt.json",
        "phase2_regression_results.tsv",
    )
    for name in regression_names:
        require(
            (PAPER / name).read_bytes() == (ROOT / "paper/biological_topk" / name).read_bytes(),
            f"successor Phase 2 did not preserve predecessor regression bytes: {name}",
        )

    receipt = load_json(PAPER / "phase2_regression_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2 and receipt["status"] == "pass", "successor Phase 2 regression receipt drift")
    require(receipt["evidence_role"] == "historical_regression_only" and receipt["independent_validation_claim"] is False, "successor historical evidence role drift")
    require(receipt["fresh_pair_selected"] is False and receipt["new_prediction_run"] is False, "successor Phase 2 ran fresh predictions")
    require((receipt["comparison_count"], receipt["ranking_result_count"], receipt["detail_count"]) == (184, 552, 2391), "successor Phase 2 regression shape drift")
    require(receipt["technical_failure_count"] == 0 and receipt["input_identity_mismatch_count"] == 0, "successor Phase 2 technical/input failure")
    require(receipt["ambiguous_matching_result_count"] == 0, "successor Phase 2 ambiguous matching drift")
    require(receipt["strict_row_mismatch_result_count"] == 14, "successor Phase 2 prior mismatch count drift")
    require(receipt["all_regression_deterministic"] is True and receipt["no_parser_or_comparator_technical_failures"] is True, "successor Phase 2 regression gate failed")
    require(
        receipt["dataset_comparison_counts"]
        == {
            "canonical_hybrid_v2_former_fresh_60_regression_only": 60,
            "canonical_hybrid_v2_regression_36": 36,
            "historical_paper_core_available": 8,
            "historical_paper_generalization_available": 44,
            "phase2_holdout_36": 36,
        },
        "successor Phase 2 dataset coverage drift",
    )

    manifest_fields, manifest = read_tsv(PAPER / "phase2_regression_manifest.tsv")
    result_fields, results = read_tsv(PAPER / "phase2_regression_results.tsv")
    detail_fields, details = read_tsv(PAPER / "phase2_regression_details.tsv")
    require(len(manifest) == 184 and len(results) == 552 and len(details) == 2391, "successor Phase 2 TSV count drift")
    require(manifest_fields[:5] == ["comparison_id", "dataset_class", "evidence_role", "workload_id", "repeat_id"], "successor Phase 2 manifest schema drift")
    require(result_fields[:7] == ["comparison_id", "dataset_class", "workload_id", "repeat_id", "comparison_status", "technical_failure", "ranking_mode"], "successor Phase 2 result schema drift")
    require(detail_fields[:5] == ["comparison_id", "dataset_class", "workload_id", "repeat_id", "ranking_mode"], "successor Phase 2 detail schema drift")
    require(len({row["comparison_id"] for row in manifest}) == 184, "successor Phase 2 duplicate comparison ID")
    require(all(row["technical_failure"] == "0" for row in results), "successor Phase 2 retained technical failure")
    require({row["ranking_mode"] for row in results} == {"score", "stability", "nt"}, "successor Phase 2 ranking coverage drift")
    require(receipt["manifest_sha256"] == sha256_file(PAPER / "phase2_regression_manifest.tsv"), "successor Phase 2 manifest digest drift")
    require(receipt["results_sha256"] == sha256_file(PAPER / "phase2_regression_results.tsv"), "successor Phase 2 results digest drift")
    require(receipt["details_sha256"] == sha256_file(PAPER / "phase2_regression_details.tsv"), "successor Phase 2 details digest drift")

    known = load_json(PAPER / "phase2_known_cases.json")
    require(known["implementation_has_workload_id_special_cases"] is False, "successor comparator declares workload special cases")
    require(known["hq10_ht02"]["strict_row_diagnostic"] == "mismatch" and known["hq10_ht02"]["set_membership"] == "preserved", "successor hq10 mismatch drift")
    require(known["hq11_ht02"]["strict_row_diagnostic"] == "mismatch" and known["hq11_ht02"]["target_reciprocal_overlap"] == "62/65" and known["hq11_ht02"]["set_membership"] == "preserved", "successor hq11 mismatch drift")
    for relative in PHASE2_COMPONENTS[:4]:
        implementation = (ROOT / relative).read_text(encoding="utf-8").lower()
        require("hq10" not in implementation and "hq11" not in implementation, f"successor comparator workload special case: {relative}")

    binding = load_json(PAPER / "contract_binding.json")
    freeze = load_json(PAPER / "phase2_comparator_freeze.json")
    require(freeze["schema_version"] == 1 and freeze["phase"] == 2 and freeze["status"] == "pass", "successor Phase 2 freeze status drift")
    require(freeze["source_commit"] == PHASE1_COMMIT and freeze["predecessor_phase2_commit"] == "4d89d1cd989f50a42e7e3af56333c39219ba1803", "successor Phase 2 commit binding drift")
    require(freeze["historical_regression_rerun"] is True and freeze["prior_mismatch_and_no_go_preserved"] is True, "successor Phase 2 did not preserve prior outcomes")
    require(freeze["regression_artifacts_byte_identical_to_predecessor"] is True, "successor Phase 2 byte identity claim drift")
    require(freeze["scientific_contract_changed"] is False and freeze["comparator_changed"] is False, "successor Phase 2 changed contract/comparator")
    require(freeze["fresh_pair_selected"] is False and freeze["new_prediction_run"] is False, "successor Phase 2 freeze ran fresh work")
    require(freeze["python_version"] == platform.python_version(), "successor Phase 2 Python version drift")
    require(freeze["contract_binding_sha256"] == sha256_file(PAPER / "contract_binding.json"), "successor Phase 2 contract binding digest drift")
    require(freeze["component_sha256"] == {relative: sha256_file(ROOT / relative) for relative in PHASE2_COMPONENTS}, "successor Phase 2 component digest drift")
    require(freeze["comparator_sha256"] == binding["bindings"]["reproduce/biological_topk/compare_candidate_topk.py"], "successor comparator differs from Phase 1 binding")
    require(freeze["comparator_sha256"] == sha256_file(ROOT / "reproduce/biological_topk/compare_candidate_topk.py"), "successor comparator live digest drift")
    for name in regression_names:
        require(freeze["successor_regression_sha256"][f"paper/biological_topk_successor/{name}"] == sha256_file(PAPER / name), f"successor Phase 2 freeze digest drift: {name}")
        require(freeze["predecessor_regression_sha256"][f"paper/biological_topk/{name}"] == sha256_file(ROOT / "paper/biological_topk" / name), f"predecessor Phase 2 freeze digest drift: {name}")

    help_result = run((sys.executable, "reproduce/biological_topk/compare_candidate_topk.py", "--help"), check=False)
    require(help_result.returncode == 0 and b"--fail-closed" in help_result.stdout, "successor comparator is not fail closed")


def check_phase2_state(state: dict[str, Any]) -> None:
    require(all(state["phase_status"][str(index)] == "pass" for index in range(3)), "successor Phase 2 prerequisite/final state drift")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(3, 10)), "successor later phase advanced during Phase 2")
    require(state["active_phase"] == 3 and state["last_completed_phase"] == 2, "successor Phase 2 transition drift")
    require(state["last_decision"] == "successor_phase_2_regression_frozen", "successor Phase 2 decision drift")
    require(state["previous_phase_commit"] == PHASE1_COMMIT, "successor Phase 2 previous commit drift")
    require(state["contract_status"] == "in_validation" and state["gpu_screen_status"] == "experimental", "successor Phase 2 promoted product status")
    require(state["bioinformatics_route"] == "conditionally_reopened" and state["rank_order_claim"] == "diagnostic_only", "successor Phase 2 claim scope drift")


def check_phase2(mode: str, current_state: dict[str, Any], status_before: set[str]) -> None:
    check_phase2_start_receipt()
    check_phase2_reproduction()
    check_phase2_evidence()
    run_phase2_unit_tests()
    if mode == "precommit":
        paths = allowlist(2)
        check_precommit_receipt(2, paths)
        check_phase2_state(current_state)
        require(git("rev-parse", "HEAD") == PHASE1_COMMIT, "successor Phase 2 precommit parent drift")
        require(changed_paths() == set(paths), "successor Phase 2 allowlisted diff mismatch")
        require(not SUCCESSOR_ARTIFACT_ROOT.exists(), "successor Phase 2 created a scientific artifact root")
    elif mode == "postcommit":
        require(not status_before, "successor Phase 2 postcommit requires a clean tree")
        commit = phase_commit_for_postcommit(2)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "successor Phase 2 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk_successor/PROGRAM_STATE.json")
        validate_program_state_value(state)
        paths = allowlist_from_commit(2, commit)
        check_precommit_receipt(2, paths, committed_at=commit)
        check_phase2_state(state)
        require(git("rev-parse", f"{commit}^") == PHASE1_COMMIT, "successor Phase 2 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE2_COMMIT_MESSAGE, "successor Phase 2 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "successor Phase 2 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported successor Phase 2 mode: {mode}")


def check_phase3_start_receipt() -> None:
    start = load_json(PAPER / "phase_3_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 3, "successor Phase 3 start schema drift")
    require(start["phase_start_parent_head"] == PHASE2_COMMIT, "successor Phase 3 parent HEAD drift")
    require(start["previous_phase_number"] == 2 and start["previous_phase_commit"] == PHASE2_COMMIT, "successor Phase 3 previous phase binding drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_successor_phase.py", "--phase", "2", "--mode", "postcommit"],
        "successor Phase 3 previous checker command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "successor Phase 2 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "successor Phase 3 clean-start evidence drift",
    )
    require(start["status"] == "pass", "successor Phase 3 start did not pass")


def check_phase3_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (sys.executable, "reproduce/biological_topk_successor/freeze_phase3.py", "--check"),
        check=False,
        env=environment,
    )
    require(
        completed.returncode == 0,
        completed.stderr.decode("utf-8", errors="replace") or "successor Phase 3 holdout does not reproduce",
    )


def run_phase3_unit_tests() -> None:
    environment = dict(os.environ)
    environment["PYTHONDWRITEBYTECODE"] = "1"
    completed = run(
        (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/biological_topk_successor",
            "-p",
            "test_phase3.py",
            "-v",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase3_evidence() -> None:
    implementation_paths = (
        "reproduce/biological_topk_successor/freeze_phase3.py",
        "reproduce/biological_topk_successor/run_phase4.py",
        "reproduce/biological_topk_successor/analyze_phase4.py",
    )
    for relative in (*PHASE3_OUTPUTS, *implementation_paths):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing successor Phase 3 evidence: {relative}")

    manifest_fields, manifest = read_tsv(PAPER / "fresh_holdout_manifest.tsv")
    attempt_fields, attempts = read_tsv(PAPER / "fresh_holdout_attempt_plan.tsv")
    require(len(manifest) == 178 and len(attempts) == 368, "successor Phase 3 manifest/attempt count drift")
    require(manifest_fields[0:5] == ["workload_id", "evidence_role", "primary_unit", "query_length_stratum", "target_scale_stratum"], "successor Phase 3 manifest schema drift")
    require(attempt_fields[0:5] == ["attempt_id", "execution_index", "validation_instance_id", "workload_id", "repeat_id"], "successor Phase 3 attempt schema drift")
    require(all(row["workload_id"] == f"bts3_w{index:03d}" for index, row in enumerate(manifest, 1)), "successor Phase 3 workload ID drift")
    for field in ("workload_id", "query_sequence_sha256", "target_sequence_sha256", "input_pair_digest"):
        require(len({row[field] for row in manifest}) == 178, f"successor Phase 3 nonunique {field}")
    require(len({(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in manifest}) == 178, "successor Phase 3 query ordinal duplication")
    require(len({(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in manifest}) == 178, "successor Phase 3 target ordinal duplication")
    quotas = {"short": 60, "medium": 59, "large": 59}
    require({key: sum(row["query_length_stratum"] == key for row in manifest) for key in quotas} == quotas, "successor Phase 3 query quota drift")
    require({key: sum(row["target_scale_stratum"] == key for row in manifest) for key in quotas} == quotas, "successor Phase 3 target quota drift")
    require(sum(row["technical_repeat_count"] == "1" for row in manifest) == 6, "successor Phase 3 technical repeat drift")

    predecessor_fields, predecessor = read_tsv(ROOT / "paper/biological_topk/fresh_holdout_manifest.tsv")
    require(len(predecessor) == 178 and "input_pair_digest" in predecessor_fields, "predecessor Phase 4 manifest drift during successor Phase 3")
    require(not {row["query_sequence_sha256"] for row in predecessor} & {row["query_sequence_sha256"] for row in manifest}, "successor Phase 3 predecessor query overlap")
    require(not {row["target_sequence_sha256"] for row in predecessor} & {row["target_sequence_sha256"] for row in manifest}, "successor Phase 3 predecessor target overlap")
    require(not {row["input_pair_digest"] for row in predecessor} & {row["input_pair_digest"] for row in manifest}, "successor Phase 3 predecessor pair overlap")
    _, exclusions = read_tsv(PAPER / "successor_exclusion_registry.tsv")
    excluded_query_digests = {row["query_sha256"] for row in exclusions if row["query_sha256"] != "NA"}
    excluded_target_digests = {row["target_sha256"] for row in exclusions if row["target_sha256"] != "NA"}
    excluded_pairs = {row["pair_digest"] for row in exclusions if row["pair_digest"] != "NA"}
    excluded_query_ordinals = {(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in exclusions if row["query_ordinal_namespace"] != "NA" and row["query_source_ordinal"] != "NA"}
    excluded_target_ordinals = {(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in exclusions if row["target_ordinal_namespace"] != "NA" and row["target_source_ordinal"] != "NA"}
    require(not excluded_query_digests & {row["query_sequence_sha256"] for row in manifest}, "successor Phase 3 excluded query digest selected")
    require(not excluded_target_digests & {row["target_sequence_sha256"] for row in manifest}, "successor Phase 3 excluded target digest selected")
    require(not excluded_pairs & {row["input_pair_digest"] for row in manifest}, "successor Phase 3 excluded pair selected")
    require(not excluded_query_ordinals & {(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in manifest}, "successor Phase 3 excluded query ordinal selected")
    require(not excluded_target_ordinals & {(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in manifest}, "successor Phase 3 excluded target ordinal selected")

    manifest_sha = sha256_file(PAPER / "fresh_holdout_manifest.tsv")
    require((PAPER / "fresh_holdout_manifest.sha256").read_text(encoding="ascii").split() == [manifest_sha, "fresh_holdout_manifest.tsv"], "successor Phase 3 manifest checksum drift")
    plan = load_json(PAPER / "fresh_holdout_plan.json")
    require(plan["schema_version"] == 1 and plan["phase"] == 3 and plan["status"] == "frozen_not_run", "successor Phase 3 plan status drift")
    require(plan["epoch_id"] == "biological_topk_successor_v2" and plan["phase_2_parent_commit"] == PHASE2_COMMIT, "successor Phase 3 epoch/commit binding drift")
    require(plan["selection_kind"] == "input_only_static_source_metadata" and plan["prohibited_selection_fields_used"] == [], "successor Phase 3 selection leakage")
    require(plan["fresh_pair_selected"] is True and plan["new_prediction_run"] is False and plan["scientific_output_created"] is False, "successor Phase 3 prediction timing drift")
    require(plan["predecessor_phase4_input_overlap_count"] == 0 and plan["exclusion_checks"]["hard_gate_pass"] is True, "successor Phase 3 exclusion gate failed")
    require((plan["primary_workload_count"], plan["technical_repeat_workload_count"], plan["validation_instance_count"], plan["attempt_count"]) == (178, 6, 184, 368), "successor Phase 3 plan count drift")
    require(plan["raw_telemetry_policy"] == "validate_then_deterministic_lossless_gzip_before_next_attempt", "successor telemetry storage policy drift")
    require(plan["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES and plan["fixed_quota_includes_predecessor_evidence"] is True, "successor Phase 3 quota semantics drift")
    require(plan["output_sha256"]["paper/biological_topk_successor/fresh_holdout_manifest.tsv"] == manifest_sha, "successor Phase 3 plan manifest digest drift")
    require(plan["output_sha256"]["paper/biological_topk_successor/fresh_holdout_attempt_plan.tsv"] == sha256_file(PAPER / "fresh_holdout_attempt_plan.tsv"), "successor Phase 3 plan attempt digest drift")
    require(plan["exact_analysis_command"] == ["python3", "reproduce/biological_topk_successor/analyze_phase4.py", "--analyze", "--artifact-root", ".paper-artifacts/biological-topk-successor/fresh-holdout"], "successor Phase 3 analysis command drift")

    by_validation: dict[str, list[dict[str, str]]] = {}
    for row in attempts:
        by_validation.setdefault(row["validation_instance_id"], []).append(row)
    require(len(by_validation) == 184 and len({row["attempt_id"] for row in attempts}) == 368, "successor Phase 3 attempt identity drift")
    require(sum(pair[0]["pair_order"] == "AG" for pair in by_validation.values()) == 92 and sum(pair[0]["pair_order"] == "GA" for pair in by_validation.values()) == 92, "successor Phase 3 A/G order imbalance")
    identity_fields = (
        "query_ordinal_namespace", "query_source_ordinal", "query_sequence_sha256",
        "target_ordinal_namespace", "target_source_ordinal", "target_sequence_sha256",
        "assembly", "target_coordinate_namespace", "query_extraction_recipe_id",
        "target_extraction_recipe_id", "input_pair_digest", "parameter_bundle_sha256",
    )
    for validation_id, pair in by_validation.items():
        require(len(pair) == 2 and {row["arm"] for row in pair} == {"A", "G"}, f"successor Phase 3 incomplete A/G pair: {validation_id}")
        require(all(len({row[field] for row in pair}) == 1 for field in identity_fields), f"successor Phase 3 A/G identity drift: {validation_id}")
        require(sorted(int(row["arm_launch_order"]) for row in pair) == [1, 2], f"successor Phase 3 launch order drift: {validation_id}")
    require(all(row["artifact_root"].startswith(".paper-artifacts/biological-topk-successor/fresh-holdout/") for row in attempts), "successor Phase 3 artifact namespace drift")
    require({row["runner_sha256"] for row in attempts} == {sha256_file(ROOT / "reproduce/biological_topk_successor/run_phase4.py")}, "successor Phase 3 runner binding drift")
    require({row["analyzer_sha256"] for row in attempts} == {sha256_file(ROOT / "reproduce/biological_topk_successor/analyze_phase4.py")}, "successor Phase 3 analyzer binding drift")

    projection = load_json(PAPER / "fresh_holdout_resource_projection.json")
    require(projection["schema_version"] == 1 and projection["status"] == "manifest_specific_projection_frozen", "successor Phase 3 projection status drift")
    require(projection["manifest_sha256"] == manifest_sha and projection["resource_model_sha256"] == sha256_file(PAPER / "resource_projection_model.json"), "successor Phase 3 projection binding drift")
    require(projection["scientific_output_fields_read"] is False and projection["model_unchanged_from_phase_1"] is True, "successor Phase 3 resource model leakage/drift")
    require((projection["primary_workload_count"], projection["technical_repeat_instance_count"], projection["projected_validation_instance_count"], projection["projected_attempt_count"]) == (178, 6, 184, 368), "successor Phase 3 projected attempt count drift")
    values = projection["projection"]
    require(values["predecessor_retained_bytes"] == 7142325727, "successor Phase 3 predecessor byte reservation drift")
    require(values["successor_tracked_bytes_through_phase2"] > 0 and values["successor_phase3_phase4_tracked_reservation_bytes"] == 256 * 1024**2, "successor Phase 3 tracked reservation drift")
    require(values["raw_g_telemetry_reservation_bytes"] == 1536 * 1024**2, "successor Phase 3 raw telemetry reservation drift")
    require(values["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES, "successor Phase 3 fixed quota drift")
    require(values["total_artifact_storage_gate_basis_bytes"] == max(values["total_artifact_storage_bytes_upper_95_with_reservations"], values["total_artifact_storage_bytes_max_observed_stress_with_reservations"]), "successor Phase 3 storage basis drift")
    require(values["artifact_storage_margin_bytes"] == FIXED_TOTAL_STORAGE_BYTES - values["total_artifact_storage_gate_basis_bytes"] > 0, "successor Phase 3 storage margin failed")

    decision = load_json(PAPER / "fresh_holdout_resource_decision.json")
    require(decision["schema_version"] == 1 and decision["phase"] == 3 and decision["status"] == "pass", "successor Phase 3 resource decision drift")
    require(decision["manifest_sha256"] == manifest_sha and decision["resource_projection_sha256"] == sha256_file(PAPER / "fresh_holdout_resource_projection.json"), "successor Phase 3 decision binding drift")
    require(decision["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES and decision["includes_predecessor_artifact_bytes"] is True, "successor Phase 3 decision quota drift")
    require(decision["owner_quota_may_be_raised_after_manifest_projection"] is False, "successor quota remains mutable after Phase 3")
    require(decision["fixed_budget_gate_pass"] is True and decision["phase_4_execution_authorized"] is True, "successor Phase 3 did not authorize execution")
    require(float(decision["projected_gpu_hours_upper_95"]) <= 72 and float(decision["projected_scheduled_elapsed_wall_seconds_upper_95"]) <= 172800, "successor Phase 3 runtime gate failed")

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for command in (
        (sys.executable, "reproduce/biological_topk_successor/run_phase4.py", "--preflight"),
        (sys.executable, "reproduce/biological_topk_successor/analyze_phase4.py", "--preflight"),
    ):
        completed = run(command, check=False, env=environment)
        require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))
        summary = json.loads(completed.stdout)
        require(summary["status"] == "preflight_pass" and summary["read_only"] is True and summary["scientific_output_created"] is False, "successor Phase 3 preflight drift")


def check_phase3_state(state: dict[str, Any]) -> None:
    require(all(state["phase_status"][str(index)] == "pass" for index in range(4)), "successor Phase 3 prerequisite/final state drift")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(4, 10)), "successor later phase advanced during Phase 3")
    require(state["active_phase"] == 4 and state["last_completed_phase"] == 3, "successor Phase 3 transition drift")
    require(state["last_decision"] == "successor_phase_3_holdout_frozen", "successor Phase 3 decision drift")
    require(state["previous_phase_commit"] == PHASE2_COMMIT, "successor Phase 3 previous commit drift")
    require(state["contract_status"] == "in_validation" and state["gpu_screen_status"] == "experimental", "successor Phase 3 promoted product status")
    require(state["bioinformatics_route"] == "conditionally_reopened" and state["rank_order_claim"] == "diagnostic_only", "successor Phase 3 claim scope drift")


def check_phase3(mode: str, current_state: dict[str, Any], status_before: set[str]) -> None:
    check_phase3_start_receipt()
    check_phase3_reproduction()
    check_phase3_evidence()
    run_phase3_unit_tests()
    if mode == "precommit":
        paths = allowlist(3)
        check_precommit_receipt(3, paths)
        check_phase3_state(current_state)
        require(git("rev-parse", "HEAD") == PHASE2_COMMIT, "successor Phase 3 precommit parent drift")
        require(changed_paths() == set(paths), "successor Phase 3 allowlisted diff mismatch")
        require(not SUCCESSOR_ARTIFACT_ROOT.exists(), "successor Phase 3 created a scientific artifact root")
    elif mode == "postcommit":
        require(not status_before, "successor Phase 3 postcommit requires a clean tree")
        commit = phase_commit_for_postcommit(3)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "successor Phase 3 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk_successor/PROGRAM_STATE.json")
        validate_program_state_value(state)
        paths = allowlist_from_commit(3, commit)
        check_precommit_receipt(3, paths, committed_at=commit)
        check_phase3_state(state)
        require(git("rev-parse", f"{commit}^") == PHASE2_COMMIT, "successor Phase 3 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE3_COMMIT_MESSAGE, "successor Phase 3 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "successor Phase 3 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported successor Phase 3 mode: {mode}")


def check_phase4_start_receipt() -> None:
    start = load_json(PAPER / "phase_4_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 4 and start["status"] == "pass", "successor Phase 4 start schema/status drift")
    require(start["phase_start_parent_head"] == PHASE3_COMMIT, "successor Phase 4 parent HEAD drift")
    require(start["previous_phase_number"] == 3 and start["previous_phase_commit"] == PHASE3_COMMIT, "successor Phase 4 previous phase binding drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_successor_phase.py", "--phase", "3", "--mode", "postcommit"],
        "successor Phase 4 previous checker command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "successor Phase 3 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "successor Phase 4 clean-start evidence drift",
    )
    require(
        start["fixed_execution_limits"]
        == {
            "max_formal_scheduled_wall_seconds": 172800,
            "max_gpu_hours": 72,
            "max_infrastructure_repair_epochs": 1,
            "max_total_artifact_storage_bytes": FIXED_TOTAL_STORAGE_BYTES,
        },
        "successor Phase 4 fixed limits drift",
    )
    require(start["resource_decision_sha256"] == sha256_file(PAPER / "fresh_holdout_resource_decision.json"), "successor Phase 4 resource decision binding drift")
    incidents = start["pre_execution_validation_incidents"]
    require(
        incidents
        == [
            {
                "artifact_root_created": False,
                "attempts_started": 0,
                "classification": "git_porcelain_leading_space_parser_rejection",
                "resolution": "stage_existing_phase_4_allowlisted_paths_before_formal_runner_invocation",
                "scientific_output_created": False,
            }
        ],
        "successor Phase 4 pre-execution incident receipt drift",
    )


def check_phase4_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (sys.executable, "reproduce/biological_topk_successor/finalize_phase4.py", "--check"),
        check=False,
        env=environment,
    )
    require(
        completed.returncode == 0,
        completed.stderr.decode("utf-8", errors="replace") or "successor Phase 4 evidence does not reproduce",
    )


def run_phase4_unit_tests() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/biological_topk_successor",
            "-p",
            "test_phase4.py",
            "-v",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase4_attempt_artifacts(row: dict[str, str]) -> dict[str, Any]:
    destination = ROOT / row["artifact_root"]
    require(destination.is_dir() and not destination.is_symlink(), f"missing successor attempt directory: {row['attempt_id']}")
    receipt = load_json(destination / "attempt-complete.json")
    require(receipt["attempt_id"] == row["attempt_id"] and receipt["status"] == "success", f"successor attempt did not succeed: {row['attempt_id']}")
    require(receipt["source_commit"] == PHASE3_COMMIT, f"successor attempt source commit drift: {row['attempt_id']}")
    require(receipt["attempt_config_sha256"] == canonical_digest(row), f"successor attempt config drift: {row['attempt_id']}")
    require(receipt["comparison_started"] is False, f"successor runner compared output: {row['attempt_id']}")
    require(receipt["retry_policy"] == "none" and receipt["replacement_retry_allowed"] is False, f"successor attempt retry policy drift: {row['attempt_id']}")
    require(receipt["binary_sha256"] == row["binary_sha256"], f"successor attempt binary drift: {row['attempt_id']}")

    manifest_path = destination / "artifact-manifest.tsv"
    checksum = (destination / "artifact-manifest.sha256").read_text(encoding="ascii").split()
    require(checksum == [sha256_file(manifest_path), manifest_path.name], f"successor attempt manifest checksum drift: {row['attempt_id']}")
    fields, artifacts = read_tsv(manifest_path)
    require(fields == ["path", "size_bytes", "sha256"], f"successor attempt artifact schema drift: {row['attempt_id']}")
    require(len({item["path"] for item in artifacts}) == len(artifacts), f"successor duplicate artifact path: {row['attempt_id']}")
    excluded = {"artifact-manifest.tsv", "artifact-manifest.sha256", "attempt-complete.json"}
    actual = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file() and path.relative_to(destination).as_posix() not in excluded
    }
    require({item["path"] for item in artifacts} == actual, f"successor attempt artifact inventory drift: {row['attempt_id']}")
    observed: dict[str, tuple[int, str]] = {}
    for item in artifacts:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe successor attempt artifact path")
        path = destination / relative
        require(path.is_file() and not path.is_symlink(), f"missing successor attempt artifact: {path}")
        size = path.stat().st_size
        digest = sha256_file(path)
        require(size == int(item["size_bytes"]) and digest == item["sha256"], f"successor attempt artifact digest drift: {path}")
        observed[item["path"]] = (size, digest)

    output = destination / str(receipt["output_path"])
    input_receipt = load_json(destination / str(receipt["input_receipt_path"]))
    require(output.is_file() and sha256_file(output) == receipt["output_sha256"], f"successor attempt output drift: {row['attempt_id']}")
    identity = input_receipt["input_identity"]
    for receipt_field, plan_field in (
        ("query_ordinal_namespace", "query_ordinal_namespace"),
        ("query_source_ordinal", "query_source_ordinal"),
        ("query_sequence_sha256", "query_sequence_sha256"),
        ("target_ordinal_namespace", "target_ordinal_namespace"),
        ("target_source_ordinal", "target_source_ordinal"),
        ("target_sequence_sha256", "target_sequence_sha256"),
        ("assembly", "assembly"),
        ("target_coordinate_namespace", "target_coordinate_namespace"),
        ("input_pair_digest", "input_pair_digest"),
    ):
        require(str(identity[receipt_field]) == row[plan_field], f"successor attempt input identity drift: {row['attempt_id']} {receipt_field}")

    if row["arm"] == "G":
        require(not (destination / "telemetry.json").exists(), f"raw successor telemetry retained: {row['attempt_id']}")
        archive = destination / "telemetry.json.gz"
        metadata = receipt["telemetry_storage"]
        require(metadata["path"] == archive.name and metadata["compression"] == "gzip_level_9_mtime_0_no_filename", f"successor telemetry policy drift: {row['attempt_id']}")
        require(metadata["validated_before_compression"] is True and metadata["lossless"] is True, f"successor telemetry validation receipt drift: {row['attempt_id']}")
        require(observed[archive.name] == (int(metadata["compressed_size_bytes"]), metadata["compressed_sha256"]), f"successor telemetry archive binding drift: {row['attempt_id']}")
        with archive.open("rb") as handle:
            header = handle.read(10)
        require(header[:2] == b"\x1f\x8b" and header[4:8] == b"\0\0\0\0", f"successor telemetry gzip header drift: {row['attempt_id']}")
        raw_digest = hashlib.sha256()
        raw_size = 0
        with gzip.open(archive, "rb") as decoded:
            for block in iter(lambda: decoded.read(1024 * 1024), b""):
                raw_digest.update(block)
                raw_size += len(block)
        require(raw_size == int(metadata["uncompressed_size_bytes"]), f"successor telemetry round-trip size drift: {row['attempt_id']}")
        require(raw_digest.hexdigest() == metadata["uncompressed_sha256"], f"successor telemetry round-trip digest drift: {row['attempt_id']}")
    else:
        require(not (destination / "telemetry.json").exists() and not (destination / "telemetry.json.gz").exists(), f"successor A attempt contains G telemetry: {row['attempt_id']}")
    return receipt


def check_phase4_evidence() -> dict[str, Any]:
    for relative in (*PHASE4_OUTPUTS, "reproduce/biological_topk_successor/finalize_phase4.py"):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing successor Phase 4 evidence: {relative}")
    _, attempts = read_tsv(PAPER / "fresh_holdout_attempt_plan.tsv")
    require(len(attempts) == 368, "successor Phase 4 attempt plan count drift")
    artifact_root = SUCCESSOR_ARTIFACT_ROOT / "fresh-holdout"
    require(artifact_root.is_dir() and not artifact_root.is_symlink(), "missing successor Phase 4 artifact root")
    summary = load_json(artifact_root / "run-summary.json")
    require(summary["status"] == "complete_success", "successor Phase 4 run did not complete successfully")
    require(summary["planned_attempt_count"] == summary["terminal_attempt_count"] == summary["successful_attempt_count"] == 368, "successor Phase 4 run-summary count drift")
    require(summary["technical_failure_count"] == 0 and summary["missing_attempt_ids"] == [], "successor Phase 4 run-summary failure drift")
    require(summary["comparison_started"] is False, "successor runner violated global comparison barrier")
    require(not list(artifact_root.glob(".*.partial.*")), "successor Phase 4 stale partial attempt remains")
    checked = {row["attempt_id"]: check_phase4_attempt_artifacts(row) for row in attempts}
    require(len(checked) == 368 and sum(receipt["arm"] == "G" for receipt in checked.values()) == 184, "successor Phase 4 checked receipt count drift")

    receipt = load_json(PAPER / "fresh_holdout_receipt.json")
    decision = load_json(PAPER / "fresh_holdout_decision.json")
    resources = load_json(PAPER / "fresh_holdout_actual_resources.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 4 and receipt["status"] == "complete", "successor Phase 4 receipt status drift")
    require(receipt["manifest_sha256"] == sha256_file(PAPER / "fresh_holdout_manifest.tsv"), "successor Phase 4 receipt manifest drift")
    require(receipt["attempt_plan_sha256"] == sha256_file(PAPER / "fresh_holdout_attempt_plan.tsv"), "successor Phase 4 receipt attempt plan drift")
    require(receipt["source_commit"] == PHASE3_COMMIT, "successor Phase 4 receipt source commit drift")
    require(receipt["planned_attempts"] == receipt["terminal_attempts"] == receipt["successful_attempts"] == 368, "successor Phase 4 receipt terminal count drift")
    require(receipt["comparison_global_start_gate_pass"] is True and receipt["comparison_count"] == 184, "successor Phase 4 global comparison gate drift")
    require(receipt["scientific_comparison_started_only_after_all_attempts_terminal"] is True, "successor Phase 4 comparison timing receipt drift")
    require(receipt["telemetry_archive_count"] == 184 and receipt["raw_telemetry_file_count"] == 0, "successor Phase 4 telemetry receipt count drift")
    require(receipt["telemetry_storage_policy"] == "validated_then_deterministic_lossless_gzip_mtime0_before_next_attempt", "successor Phase 4 telemetry policy receipt drift")
    require(receipt["infrastructure_repair_epochs_used"] == 0 and receipt["no_retries_or_replacements"] is True, "successor Phase 4 repair/retry drift")
    require(receipt["rank_order_claim"] == "diagnostic_only", "successor Phase 4 receipt promoted rank order")
    require(receipt["actual_resources_sha256"] == sha256_file(PAPER / "fresh_holdout_actual_resources.json"), "successor Phase 4 resource digest drift")
    require(receipt["run_summary_sha256"] == sha256_file(artifact_root / "run-summary.json"), "successor Phase 4 run-summary digest drift")
    require(
        receipt["attempt_receipt_sha256"]
        == {attempt_id: sha256_file(ROOT / next(row["artifact_root"] for row in attempts if row["attempt_id"] == attempt_id) / "attempt-complete.json") for attempt_id in sorted(checked)},
        "successor Phase 4 attempt receipt registry drift",
    )
    for relative, digest in receipt["source_data_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, f"successor Phase 4 source data drift: {relative}")

    require(decision["schema_version"] == 1 and decision["phase"] == 4, "successor Phase 4 decision schema drift")
    require(decision["decision"] in {"pass", "no_go", "blocked_insufficient_information", "blocked_fixed_budget"}, "successor Phase 4 decision value drift")
    require(decision["rank_order_claim"] == "diagnostic_only" and decision["gpu_screen_status_if_applied"] == "experimental", "successor Phase 4 promoted unsupported claims")
    require(decision["primary_workload_count"] == 178 and decision["primary_identity_uniqueness_gate_pass"] is True, "successor Phase 4 independent-unit gate drift")
    require(decision["technical_failure_count"] == decision["missing_output_count"] == decision["input_identity_mismatch_count"] == decision["ambiguous_matching_count"] == decision["unexpected_fallback_count"] == 0, "successor Phase 4 technical gate drift")
    require(decision["zero_technical_failure_gate_pass"] is True, "successor Phase 4 zero-failure gate failed")
    require(decision["fresh_holdout_receipt_sha256"] == sha256_file(PAPER / "fresh_holdout_receipt.json"), "successor Phase 4 decision receipt digest drift")
    require(decision["actual_resources_sha256"] == sha256_file(PAPER / "fresh_holdout_actual_resources.json"), "successor Phase 4 decision resource digest drift")
    require(decision["no_post_run_supplementation"] is True and decision["infrastructure_repair_epochs_used"] == 0, "successor Phase 4 supplementation/repair drift")
    require(decision["scientific_decision_reached"] is (decision["decision"] in {"pass", "no_go"}), "successor scientific decision timing drift")

    require(resources["schema_version"] == 1 and resources["phase"] == 4, "successor Phase 4 actual resource schema drift")
    require(resources["planned_attempt_count"] == resources["terminal_attempt_count"] == resources["successful_attempt_count"] == 368, "successor Phase 4 actual resource count drift")
    require(resources["completed_cpu_attempt_count"] == resources["completed_gpu_attempt_count"] == 184, "successor Phase 4 actual arm count drift")
    require(resources["predecessor_retained_artifact_bytes"] == 7142325727 and resources["successor_phase4_tracked_reservation_bytes"] == 256 * 1024**2, "successor Phase 4 actual storage reservation drift")
    require(resources["successor_runtime_artifact_bytes"] == directory_file_bytes(artifact_root), "successor Phase 4 runtime byte count drift")
    require(resources["actual_total_artifact_storage_bytes_with_tracked_reservation"] == resources["predecessor_retained_artifact_bytes"] + resources["successor_tracked_bytes_through_phase3"] + resources["successor_phase4_tracked_reservation_bytes"] + resources["successor_runtime_artifact_bytes"], "successor Phase 4 total storage arithmetic drift")
    require(resources["fixed_total_artifact_storage_bytes"] == FIXED_TOTAL_STORAGE_BYTES and resources["artifact_storage_margin_bytes"] == FIXED_TOTAL_STORAGE_BYTES - resources["actual_total_artifact_storage_bytes_with_tracked_reservation"], "successor Phase 4 storage margin drift")
    require(float(resources["actual_gpu_hours"]) <= 72 and float(resources["actual_scheduled_elapsed_wall_seconds"]) <= 172800, "successor Phase 4 actual runtime limit failed")
    require(resources["fixed_budget_gate_pass"] is True and resources["status"] == "pass", "successor Phase 4 actual fixed-budget gate failed")
    require(resources["telemetry_archive_count"] == 184 and resources["raw_telemetry_file_count"] == 0, "successor Phase 4 actual telemetry count drift")
    require(resources["resource_values_are_performance_claims"] is False, "successor Phase 4 resource values promoted to performance claims")

    bound_fields, bounds = read_tsv(PAPER / "source_data/fresh_exact_binomial_bounds.tsv")
    metric_fields, metrics = read_tsv(PAPER / "source_data/fresh_workload_metrics.tsv")
    failure_fields, failures = read_tsv(PAPER / "source_data/fresh_failure_ledger.tsv")
    require(bound_fields[:4] == ["endpoint_order", "endpoint_name", "ranking_mode", "successes"], "successor Phase 4 bound schema drift")
    require(metric_fields[:5] == ["validation_instance_id", "workload_id", "repeat_id", "primary_instance", "ranking_mode"], "successor Phase 4 metric schema drift")
    require(failure_fields[:4] == ["failure_id", "validation_instance_id", "workload_id", "repeat_id"], "successor Phase 4 failure schema drift")
    require(len(metrics) == 184 * 3 and len([row for row in metrics if row["primary_instance"] == "1"]) == 178 * 3, "successor Phase 4 metric count drift")
    require(not failures, "successor Phase 4 failure ledger is nonempty")
    require(all(row["threshold_pass"] == "1" for row in bounds) is (decision["endpoint_gate_pass"] is True), "successor Phase 4 endpoint bound/decision drift")
    return decision


def check_phase4_state(state: dict[str, Any], decision: dict[str, Any]) -> None:
    outcome = decision["decision"]
    require(all(state["phase_status"][str(index)] == "pass" for index in range(4)), "successor Phase 4 prerequisite state drift")
    require(state["previous_phase_commit"] == PHASE3_COMMIT, "successor Phase 4 previous commit drift")
    require(state["last_completed_phase"] == 4 and state["gpu_screen_status"] == "experimental", "successor Phase 4 completion/product state drift")
    require(state["rank_order_claim"] == "diagnostic_only", "successor Phase 4 promoted rank order")
    if outcome == "pass":
        require(state["phase_status"]["4"] == "pass" and all(state["phase_status"][str(index)] == "pending" for index in range(5, 10)), "successor Phase 4 pass status drift")
        require(state["active_phase"] == 5 and state["last_decision"] == "fresh_concordance_pass", "successor Phase 4 pass transition drift")
        require(state["contract_status"] == "fresh_concordance_pass" and state["bioinformatics_route"] == "conditionally_reopened", "successor Phase 4 pass contract/route drift")
        require(decision["all_promotion_gates_pass"] is True and decision["later_phase_authorized"] is True, "successor Phase 4 pass lacks promotion authorization")
    elif outcome == "no_go":
        require(state["phase_status"]["4"] == "no_go" and state["active_phase"] is None, "successor Phase 4 no-go state drift")
        require(all(state["phase_status"][str(index)] == "not_authorized_previous_no_go" for index in range(5, 10)), "successor phases advanced after concordance no-go")
        require(state["last_decision"] == "concordance_no_go" and state["contract_status"] == "concordance_no_go", "successor Phase 4 no-go decision drift")
        require(state["bioinformatics_route"] == "closed_for_this_contract", "successor Phase 4 no-go route drift")
    else:
        require(outcome in {"blocked_insufficient_information", "blocked_fixed_budget"}, "unsupported successor Phase 4 blocked outcome")
        require(state["phase_status"]["4"] == outcome and state["active_phase"] is None, "successor Phase 4 blocked state drift")
        require(state["last_decision"] == outcome and state["contract_status"] == "in_validation", "successor Phase 4 blocked decision drift")


def check_phase4(mode: str, current_state: dict[str, Any], status_before: set[str]) -> None:
    check_phase4_start_receipt()
    check_phase4_reproduction()
    decision = check_phase4_evidence()
    run_phase4_unit_tests()
    if mode == "precommit":
        paths = allowlist(4)
        check_precommit_receipt(4, paths)
        check_phase4_state(current_state, decision)
        require(git("rev-parse", "HEAD") == PHASE3_COMMIT, "successor Phase 4 precommit parent drift")
        require(changed_paths() == set(paths), "successor Phase 4 allowlisted diff mismatch")
    elif mode == "postcommit":
        require(not status_before, "successor Phase 4 postcommit requires a clean tree")
        commit = phase_commit_for_postcommit(4)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "successor Phase 4 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk_successor/PROGRAM_STATE.json")
        validate_program_state_value(state)
        paths = allowlist_from_commit(4, commit)
        check_precommit_receipt(4, paths, committed_at=commit)
        check_phase4_state(state, decision)
        require(git("rev-parse", f"{commit}^") == PHASE3_COMMIT, "successor Phase 4 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE4_COMMIT_MESSAGE, "successor Phase 4 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "successor Phase 4 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported successor Phase 4 mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=range(10), required=True)
    parser.add_argument("--mode", choices=("precommit", "postcommit"), required=True)
    args = parser.parse_args()
    status_before = changed_paths()
    try:
        state = validate_program_state()
        if args.phase == 0:
            check_phase0(args.mode, state, status_before)
        elif args.phase == 1:
            check_phase1(args.mode, state, status_before)
        elif args.phase == 2:
            check_phase2(args.mode, state, status_before)
        elif args.phase == 3:
            check_phase3(args.mode, state, status_before)
        elif args.phase == 4:
            check_phase4(args.mode, state, status_before)
        else:
            raise CheckError(f"successor Phase {args.phase} checker is not frozen yet")
        require(changed_paths() == status_before, "successor checker modified the working tree")
        print(f"biological Top-K successor Phase {args.phase} {args.mode} checks OK")
        print(f"contract_status={state['contract_status']}")
        print(f"gpu_screen_status={state['gpu_screen_status']}")
        print(f"fixed_total_artifact_storage_bytes={state['fixed_total_artifact_storage_bytes']}")
        return 0
    except (CheckError, SchemaValidationError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"biological Top-K successor check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
