#!/usr/bin/env python3
"""Fail-closed phase checker for Bioinformatics submission readiness v2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
STATE = PAPER / "PROGRAM_STATE.json"
SCHEMA = ROOT / "schemas/bioinformatics_submission_readiness_v2_program_state.schema.json"
PROTOCOL = ROOT / "goal-bioinformatics-submission-readiness-v2.md"
BASELINE_COMMIT = "739ee0a8db01f77143a5c993e6c68a56a772502b"
PHASE0_COMMIT_MESSAGE = "docs: start Bioinformatics submission readiness v2"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2"
IMMUTABLE_ROOTS = (
    "paper/bioinformatics",
    "paper/biological_topk",
    "paper/biological_topk_successor",
    "paper/ssw_cuda",
    "paper/source_data",
)
PHASE0_PATHS = (
    "Makefile",
    "goal-bioinformatics-submission-readiness-v2.md",
    "paper/bioinformatics_submission_readiness_v2/PROGRAM_STATE.json",
    "paper/bioinformatics_submission_readiness_v2/STATUS.md",
    "paper/bioinformatics_submission_readiness_v2/epoch_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/legacy_boundary.json",
    "paper/bioinformatics_submission_readiness_v2/owner_phase0_authorization.json",
    "paper/bioinformatics_submission_readiness_v2/phase_0_change_allowlist.txt",
    "paper/bioinformatics_submission_readiness_v2/phase_0_precommit_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_0_start_receipt.json",
    "schemas/bioinformatics_submission_readiness_v2_program_state.schema.json",
    "scripts/check_bioinformatics_submission_readiness_v2.py",
    "scripts/check_bioinformatics_submission_readiness_v2_all.sh",
    "tests/bioinformatics_submission_readiness_v2/__init__.py",
    "tests/bioinformatics_submission_readiness_v2/test_phase0.py",
)
CRITICAL_LEGACY_SHA256 = {
    "paper/bioinformatics/canonical_hybrid_v2_performance_decision.md": "71edaabd0339352df0ca7bd648f33787071d4d2c1097ea09d00aa5572f9999d1",
    "paper/bioinformatics/phase3_postpilot_decision.json": "471898d688386f46b4e7f13b932b6b4f9874d9ed74641240b5c2fd4ad71851fe",
    "paper/biological_topk/PROGRAM_STATE.json": "8c626090b68e9699a30ec3ee7ce3b0b448791d39fa9ede4d1af682236235ff63",
    "paper/biological_topk_successor/PROGRAM_STATE.json": "17869b0ce1913bb10b5592128a00b4a4f7d7de435c0017d2b7c9fef9b98536f0",
    "paper/biological_topk_successor/biological_utility_decision.json": "ab91cb645048d73a21692b9433b41f8197d7e74c41c637a124e00232e163fdef",
    "paper/ssw_cuda/forward_hybrid_decision.json": "d0263d390ad0737275457215ef81ac61658a814461de37bbe5921e54f1979fb1",
}
LEGACY_TREE_SHA256 = "ea89de4d2e5382dca0f823d8d2e9d5b4124c569ab2e283a03c4fe387a8f29502"


class CheckError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def run(arguments: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        tuple(arguments),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
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


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def load_schema_validator():
    path = ROOT / "scripts/check_biological_topk_phase.py"
    spec = importlib.util.spec_from_file_location("v2_schema_validator", path)
    require(spec is not None and spec.loader is not None, "cannot load schema validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules["v2_schema_validator"] = module
    spec.loader.exec_module(module)
    return module


SCHEMA_VALIDATOR = load_schema_validator()
SchemaValidationError = SCHEMA_VALIDATOR.SchemaValidationError


def validate_schema(value: Any, schema: dict[str, Any]) -> None:
    SCHEMA_VALIDATOR.validate_schema(value, schema)


def changed_paths() -> set[str]:
    lines = run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all")
    ).stdout.decode("utf-8").splitlines()
    return {line[3:] for line in lines if len(line) >= 4}


def phase0_commit() -> str:
    commits = []
    for line in git("log", "--format=%H%x09%s", f"{BASELINE_COMMIT}..HEAD").splitlines():
        commit, subject = line.split("\t", 1)
        if subject == PHASE0_COMMIT_MESSAGE:
            commits.append(commit)
    require(len(commits) == 1, "expected exactly one Phase 0 commit")
    require(git("rev-parse", f"{commits[0]}^") == BASELINE_COMMIT, "Phase 0 parent drift")
    return commits[0]


def file_bytes(relative: str, commit: str | None) -> bytes:
    return (ROOT / relative).read_bytes() if commit is None else git_bytes("show", f"{commit}:{relative}")


def check_legacy_boundary() -> None:
    boundary = load_json(PAPER / "legacy_boundary.json")
    require(boundary["baseline_commit"] == BASELINE_COMMIT, "legacy baseline drift")
    require(boundary["immutable_roots"] == list(IMMUTABLE_ROOTS), "legacy roots drift")
    require(boundary["critical_evidence_sha256"] == CRITICAL_LEGACY_SHA256, "legacy critical evidence inventory drift")
    require(boundary["legacy_tree_listing_sha256"] == LEGACY_TREE_SHA256, "legacy tree digest receipt drift")
    observed_tree = sha256_bytes(git_bytes("ls-tree", "-r", BASELINE_COMMIT, "--", *IMMUTABLE_ROOTS))
    require(observed_tree == LEGACY_TREE_SHA256, "baseline legacy tree listing drift")
    diff = run(("git", "diff", "--quiet", BASELINE_COMMIT, "--", *IMMUTABLE_ROOTS), check=False)
    require(diff.returncode == 0, "legacy evidence changed relative to baseline")
    for relative, expected in CRITICAL_LEGACY_SHA256.items():
        require(sha256_file(ROOT / relative) == expected, f"legacy evidence drift: {relative}")


def validate_state_transitions(state: dict[str, Any]) -> None:
    statuses = state["phase_status"]
    require(set(statuses) == {str(index) for index in range(8)}, "v2 phase inventory drift")
    require(state["current_legacy_bioinformatics_route"] == "closed_biological_utility_gap", "legacy route was rewritten")
    require(state["post_hoc_scope_decision"] is True, "post hoc scope disclosure missing")
    require(state["external_comparison_authorized"] is False, "premature external comparison authorization")
    require(state["release_packaging_authorized"] is False, "premature release authorization")
    require(state["submission_drafting_authorized"] is False, "premature manuscript authorization")
    if state["product_status"] == "validated_release_candidate":
        require(statuses["4"] == "pass", "product promoted before Phase 4 pass")
        require(state["validation_status"] == "passed", "validated product status mismatch")
    if state["target_claim_status"] == "supported":
        require(statuses["4"] == "pass", "acceleration claim promoted before Phase 4 pass")
    terminal = [index for index in range(8) if statuses[str(index)] in {"no_go", "blocked"}]
    if terminal:
        first = min(terminal)
        require(state["active_phase"] is None, "terminal v2 state has active phase")
        for later in range(first + 1, 8):
            require(statuses[str(later)] == "not_authorized_previous_no_go", "later phase advanced after terminal gate")


def validate_program_state(state: dict[str, Any] | None = None) -> dict[str, Any]:
    observed = load_json(STATE) if state is None else state
    validate_schema(observed, load_json(SCHEMA))
    validate_state_transitions(observed)
    return observed


def check_authorization_and_epoch() -> None:
    protocol_sha = sha256_file(PROTOCOL)
    authorization_path = PAPER / "owner_phase0_authorization.json"
    authorization = load_json(authorization_path)
    require(authorization["approval_message"] == "启动并完成v2", "authorization message drift")
    require(authorization["baseline_commit"] == BASELINE_COMMIT, "authorization baseline drift")
    require(authorization["historical_evidence_may_be_modified"] is False, "authorization permits legacy modification")
    require(authorization["historical_no_go_may_be_reopened"] is False, "authorization permits historical reopening")
    require(authorization["phase_4_stop_loss_required"] is True, "Phase 4 stop-loss missing")
    require(authorization["protocol_sha256"] == protocol_sha, "authorization protocol digest drift")
    epoch = load_json(PAPER / "epoch_receipt.json")
    require(epoch["baseline_commit"] == BASELINE_COMMIT, "epoch baseline drift")
    require(epoch["authorization_sha256"] == sha256_file(authorization_path), "epoch authorization binding drift")
    require(epoch["legacy_boundary_sha256"] == sha256_file(PAPER / "legacy_boundary.json"), "epoch legacy binding drift")
    require(epoch["protocol_sha256"] == protocol_sha, "epoch protocol binding drift")
    require(epoch["artifact_root_exists_at_phase0"] is False and not ARTIFACT_ROOT.exists(), "v2 artifact root exists at Phase 0")
    require(epoch["new_prediction_started"] is False, "Phase 0 claims prediction execution")
    start = load_json(PAPER / "phase_0_start_receipt.json")
    require(start["baseline_commit"] == BASELINE_COMMIT and start["clean_start"] is True, "Phase 0 clean-start drift")
    require(start["protocol_sha256"] == protocol_sha, "Phase 0 start protocol binding drift")


def check_precommit_receipt(commit: str | None) -> None:
    relative = "paper/bioinformatics_submission_readiness_v2/phase_0_precommit_receipt.json"
    receipt = load_json(PAPER / "phase_0_precommit_receipt.json") if commit is None else load_json_from_commit(commit, relative)
    require(receipt["schema_version"] == 1 and receipt["phase"] == 0, "Phase 0 precommit receipt schema drift")
    require(receipt["phase_start_parent_head"] == BASELINE_COMMIT, "Phase 0 precommit parent drift")
    require(receipt["planned_commit_message"] == PHASE0_COMMIT_MESSAGE, "Phase 0 commit message drift")
    require(receipt["expected_changed_paths"] == list(PHASE0_PATHS), "Phase 0 path inventory drift")
    expected_evidence = set(PHASE0_PATHS) - {relative}
    require(set(receipt["schema_evidence_sha256"]) == expected_evidence, "Phase 0 evidence inventory drift")
    for path, expected in receipt["schema_evidence_sha256"].items():
        require(sha256_bytes(file_bytes(path, commit)) == expected, f"Phase 0 evidence digest drift: {path}")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "precommit receipt claims future commit")


def run_phase0_tests() -> None:
    run((sys.executable, "tests/bioinformatics_submission_readiness_v2/test_phase0.py"))


def check_phase0(mode: str) -> None:
    status_before = changed_paths()
    if mode == "precommit":
        require(git("rev-parse", "HEAD") == BASELINE_COMMIT, "Phase 0 precommit parent is not baseline")
        require(status_before == set(PHASE0_PATHS), "Phase 0 changed paths differ from allowlist")
        allowlist = tuple((PAPER / "phase_0_change_allowlist.txt").read_text(encoding="utf-8").splitlines())
        require(allowlist == PHASE0_PATHS, "Phase 0 allowlist drift")
        check_precommit_receipt(None)
    else:
        require(not status_before, "Phase 0 postcommit requires a clean tree")
        commit = phase0_commit()
        check_precommit_receipt(commit)
    state = validate_program_state()
    require(state["phase_status"] == {"0": "pass", "1": "active", "2": "pending", "3": "pending", "4": "pending", "5": "pending", "6": "pending", "7": "pending"}, "Phase 0 state drift")
    require(state["active_phase"] == 1 and state["last_completed_phase"] == 0, "Phase 0 transition drift")
    require(state["v2_bioinformatics_route"] == "conditionally_open_performance_gated", "v2 route drift")
    require(state["product_status"] == "experimental" and state["validation_status"] == "pending", "premature product validation")
    require(state["target_claim_status"] == "pending_final_rc_performance_validation", "premature target claim promotion")
    check_legacy_boundary()
    check_authorization_and_epoch()
    protocol = PROTOCOL.read_text(encoding="utf-8")
    for required in (
        "transparent post hoc scope decision",
        "one-sided 95% lower confidence bound of validated capacity_ratio >= 10",
        "Any technical failure",
        "No formal external comparison is authorized before Phase 4 passes",
        "Top-P enrichment estimates",
    ):
        require(required in protocol, f"protocol requirement missing: {required}")
    require("check-bioinformatics-submission-readiness-v2" in (ROOT / "Makefile").read_text(encoding="utf-8"), "Make target missing")
    run_phase0_tests()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=range(8), required=True)
    parser.add_argument("--mode", choices=("precommit", "postcommit"), required=True)
    args = parser.parse_args()
    try:
        require(args.phase == 0, "checker for requested phase is not implemented yet")
        check_phase0(args.mode)
        print(f"Bioinformatics submission readiness v2 Phase {args.phase} {args.mode} checks OK")
        return 0
    except (CheckError, OSError, ValueError, KeyError, json.JSONDecodeError, SchemaValidationError) as error:
        print(f"v2 phase check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
