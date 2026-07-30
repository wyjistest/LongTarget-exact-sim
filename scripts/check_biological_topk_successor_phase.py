#!/usr/bin/env python3
"""Normative phase checker for the biological Top-K successor epoch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
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
PINNED_V1_AUDIT_COMMAND = ["python3", "scripts/check_biological_topk_successor_v1_audit.py"]


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
    validate_schema(state, schema)
    validate_state_transitions(state)
    return state


def allowlist(phase: int) -> list[str]:
    path = PAPER / f"phase_{phase}_change_allowlist.txt"
    require(path.is_file() and not path.is_symlink(), f"missing successor Phase {phase} allowlist")
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(rows == sorted(set(rows)), f"successor Phase {phase} allowlist must be sorted and unique")
    require(all(not Path(row).is_absolute() and ".." not in Path(row).parts for row in rows), "unsafe successor allowlist")
    return rows


def check_precommit_receipt(phase: int, paths: list[str]) -> None:
    receipt = load_json(PAPER / f"phase_{phase}_precommit_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == phase, "successor precommit receipt schema drift")
    require(receipt["expected_changed_paths"] == paths, "successor precommit path inventory drift")
    require(
        receipt["checker_command"]
        == ["python3", "scripts/check_biological_topk_successor_phase.py", "--phase", str(phase), "--mode", "precommit"],
        "successor precommit command drift",
    )
    require(receipt["checker_result"] == "pass", "successor precommit receipt did not pass")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "successor receipt claims self/future commit")
    for relative, digest in receipt["schema_evidence_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, f"successor precommit evidence drift: {relative}")


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
    check_phase0_state(state)
    check_authorization()
    check_phase0_receipts()
    check_v1_registry()
    check_v1_boundary()
    require(not SUCCESSOR_ARTIFACT_ROOT.exists(), "successor scientific artifact root exists during Phase 0")
    run_phase0_unit_tests()
    run_predecessor_phase4_reproduction()
    paths = allowlist(0)
    check_precommit_receipt(0, paths)

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
        require(not status_before, "successor Phase 0 postcommit requires a clean tree")
        commit = phase_commit_for_postcommit(0)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "successor Phase 0 commit is not an ancestor")
        require(git("rev-parse", f"{commit}^") == PREDECESSOR_COMMIT, "successor Phase 0 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE0_COMMIT_MESSAGE, "successor Phase 0 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "successor Phase 0 committed paths differ from allowlist")
        run_predecessor_aggregate()
    else:
        raise CheckError(f"unsupported successor Phase 0 mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=range(10), required=True)
    parser.add_argument("--mode", choices=("precommit", "postcommit"), required=True)
    args = parser.parse_args()
    status_before = changed_paths()
    try:
        state = validate_program_state()
        if args.phase != 0:
            raise CheckError(f"successor Phase {args.phase} checker is not frozen yet")
        check_phase0(args.mode, state, status_before)
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
