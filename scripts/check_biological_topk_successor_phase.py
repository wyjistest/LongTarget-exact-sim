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
    expected_messages = {0: PHASE0_COMMIT_MESSAGE, 1: PHASE1_COMMIT_MESSAGE}
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
