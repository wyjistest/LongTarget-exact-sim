#!/usr/bin/env python3
"""Fail-closed phase checker for Bioinformatics submission readiness v2."""

from __future__ import annotations

import argparse
import csv
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
PHASE1_COMMIT_MESSAGE = "repro: freeze v2 GPU-only release candidate"
PHASE1_IMPLEMENTATION_COMMIT = "0f04c241b6fda746f061b043aa9a9d26c79938ab"
PHASE2_COMMIT_MESSAGE = "repro: freeze v2 development harnesses"
PHASE2_FREEZE_PARENT = "8114ce45be9bd5b25e52dc8fe7bc768eb6aee589"
PHASE2_RUNTIME_COMMIT = PHASE2_FREEZE_PARENT
PHASE2_CAPACITY_COMMIT = "49ed7d5242def174a0bd8708b9bb24825d49ee67"
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
PHASE1_PATHS = (
    "paper/bioinformatics_submission_readiness_v2/PROGRAM_STATE.json",
    "paper/bioinformatics_submission_readiness_v2/STATUS.md",
    "paper/bioinformatics_submission_readiness_v2/phase_1_artifact_manifest.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_change_allowlist.txt",
    "paper/bioinformatics_submission_readiness_v2/phase_1_precommit_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_runtime_identity.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_smoke_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_start_receipt.json",
    "scripts/check_bioinformatics_submission_readiness_v2.py",
    "scripts/check_bioinformatics_submission_readiness_v2_all.sh",
    "tests/bioinformatics_submission_readiness_v2/test_phase0.py",
    "tests/bioinformatics_submission_readiness_v2/test_phase1.py",
)
PHASE1_RUNTIME_PATHS = (
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/contract.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/bioinformatics_submission_readiness_v2/Dockerfile.runtime",
    "schemas/gasal2_candidate_sites_tsv_v1.schema.json",
    "schemas/gasal2_gpu_screen_run_report_v1.schema.json",
    "scripts/fasim_tfo_archive.py",
    "scripts/gasal2_candidate_sites.py",
    "scripts/gasal2_gpu_screen.py",
    "scripts/gasal2_longtarget.py",
)
PHASE1_FROZEN_EVIDENCE_PATHS = (
    "paper/bioinformatics_submission_readiness_v2/phase_1_artifact_manifest.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_change_allowlist.txt",
    "paper/bioinformatics_submission_readiness_v2/phase_1_precommit_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_runtime_identity.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_smoke_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_1_start_receipt.json",
)
PHASE2_PATHS = (
    "paper/bioinformatics_submission_readiness_v2/PROGRAM_STATE.json",
    "paper/bioinformatics_submission_readiness_v2/STATUS.md",
    "paper/bioinformatics_submission_readiness_v2/external_method_landscape.tsv",
    "paper/bioinformatics_submission_readiness_v2/phase_2_artifact_manifest.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_change_allowlist.txt",
    "paper/bioinformatics_submission_readiness_v2/phase_2_development_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_external_search_protocol.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_external_tool_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_precommit_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_runtime_identity.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_start_receipt.json",
    "paper/bioinformatics_submission_readiness_v2/phase_2_supersession_receipt.json",
    "reproduce/bioinformatics_submission_readiness_v2/cpu_reference_screen.py",
    "reproduce/bioinformatics_submission_readiness_v2/run_development_harness.py",
    "reproduce/bioinformatics_submission_readiness_v2/run_external_development.py",
    "scripts/check_bioinformatics_submission_readiness_v2.py",
    "tests/bioinformatics_submission_readiness_v2/test_development_harness.py",
    "tests/bioinformatics_submission_readiness_v2/test_external_development.py",
    "tests/bioinformatics_submission_readiness_v2/test_phase2.py",
)
PHASE2_RUNTIME_PATHS = PHASE1_RUNTIME_PATHS
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


def commit_with_subject(subject: str) -> str:
    commits = []
    for line in git("log", "--format=%H%x09%s", f"{BASELINE_COMMIT}..HEAD").splitlines():
        commit, observed = line.split("\t", 1)
        if observed == subject:
            commits.append(commit)
    require(len(commits) == 1, f"expected exactly one commit with subject: {subject}")
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
    require(
        state["external_comparison_authorized"] is (statuses["4"] == "pass"),
        "external comparison authorization does not follow Phase 4",
    )
    require(
        state["release_packaging_authorized"] is (statuses["5"] == "pass"),
        "release authorization does not follow Phase 5",
    )
    require(
        state["submission_drafting_authorized"] is (statuses["6"] == "pass"),
        "manuscript authorization does not follow Phase 6",
    )
    if state["artifact_role"] is not None:
        require(statuses["1"] == "pass", "artifact role assigned before Phase 1 pass")
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
    elif state["active_phase"] is not None:
        active = state["active_phase"]
        require(statuses[str(active)] == "active", "active phase/status mismatch")
        require(state["last_completed_phase"] == active - 1, "last completed phase mismatch")
        for earlier in range(active):
            require(statuses[str(earlier)] == "pass", "non-pass phase precedes active phase")
        for later in range(active + 1, 8):
            require(statuses[str(later)] == "pending", "future phase advanced prematurely")


def validate_program_state(state: dict[str, Any] | None = None) -> dict[str, Any]:
    observed = load_json(STATE) if state is None else state
    validate_schema(observed, load_json(SCHEMA))
    validate_state_transitions(observed)
    return observed


def check_authorization_and_epoch(*, require_phase0_artifact_boundary: bool) -> None:
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
    require(epoch["artifact_root_exists_at_phase0"] is False, "Phase 0 artifact-boundary receipt drift")
    if require_phase0_artifact_boundary:
        require(not ARTIFACT_ROOT.exists(), "v2 artifact root exists at Phase 0")
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
    check_authorization_and_epoch(require_phase0_artifact_boundary=True)
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


def check_phase0_history() -> None:
    commit = phase0_commit()
    check_precommit_receipt(commit)
    phase0_state = load_json_from_commit(
        commit, "paper/bioinformatics_submission_readiness_v2/PROGRAM_STATE.json"
    )
    validate_schema(phase0_state, load_json(SCHEMA))
    validate_state_transitions(phase0_state)
    require(phase0_state["active_phase"] == 1, "committed Phase 0 state drift")
    check_authorization_and_epoch(require_phase0_artifact_boundary=False)


def check_phase1_start_receipt() -> None:
    receipt = load_json(PAPER / "phase_1_start_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 1, "Phase 1 start receipt drift")
    require(receipt["phase_0_transition_commit"] == phase0_commit(), "Phase 1 start/Phase 0 binding drift")
    require(receipt["phase_start_tree_was_clean"] is True, "Phase 1 did not start from a clean committed tree")
    require(receipt["receipt_created_at_freeze"] is True, "Phase 1 receipt timing disclosure missing")
    require(receipt["freeze_parent_head"] == PHASE1_IMPLEMENTATION_COMMIT, "Phase 1 freeze parent drift")
    require(receipt["previous_phase_postcommit_check_result"] == "pass", "Phase 0 audit was not preserved")


def check_phase1_precommit_receipt(commit: str | None) -> None:
    relative = "paper/bioinformatics_submission_readiness_v2/phase_1_precommit_receipt.json"
    receipt = load_json(PAPER / "phase_1_precommit_receipt.json") if commit is None else load_json_from_commit(commit, relative)
    require(receipt["schema_version"] == 1 and receipt["phase"] == 1, "Phase 1 precommit receipt drift")
    require(receipt["phase_start_parent_head"] == PHASE1_IMPLEMENTATION_COMMIT, "Phase 1 precommit parent drift")
    require(receipt["planned_commit_message"] == PHASE1_COMMIT_MESSAGE, "Phase 1 commit message drift")
    require(receipt["expected_changed_paths"] == list(PHASE1_PATHS), "Phase 1 path inventory drift")
    expected_evidence = set(PHASE1_PATHS) - {relative}
    require(set(receipt["schema_evidence_sha256"]) == expected_evidence, "Phase 1 evidence inventory drift")
    for path, expected in receipt["schema_evidence_sha256"].items():
        require(sha256_bytes(file_bytes(path, commit)) == expected, f"Phase 1 evidence digest drift: {path}")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "Phase 1 precommit receipt claims future commit")


def artifact_path(relative: str) -> Path:
    candidate = (ARTIFACT_ROOT / relative).resolve()
    require(candidate.is_relative_to(ARTIFACT_ROOT.resolve()), "artifact path escapes v2 root")
    return candidate


def check_phase1_artifact_manifest() -> None:
    manifest = load_json(PAPER / "phase_1_artifact_manifest.json")
    require(manifest["schema_version"] == 1 and manifest["phase"] == 1, "Phase 1 artifact manifest drift")
    require(manifest["formal_claim_evidence"] is False, "Phase 1 artifacts were promoted to claim evidence")
    observed_paths: set[str] = set()
    for item in manifest["artifacts"]:
        relative = item["relative_path"]
        require(relative not in observed_paths, "duplicate Phase 1 artifact path")
        observed_paths.add(relative)
        path = artifact_path(relative)
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 1 artifact: {relative}")
        require(path.stat().st_size == item["size_bytes"], f"Phase 1 artifact size drift: {relative}")
        require(sha256_file(path) == item["sha256"], f"Phase 1 artifact digest drift: {relative}")
    total = sum(path.stat().st_size for path in ARTIFACT_ROOT.rglob("*") if path.is_file())
    state = validate_program_state()
    require(total <= state["fixed_v2_artifact_storage_bytes"], "v2 artifact quota exceeded")
    require(manifest["bytes_at_phase1_freeze"] <= state["fixed_v2_artifact_storage_bytes"], "Phase 1 froze over quota")


def check_phase1_runtime() -> None:
    receipt = load_json(PAPER / "phase_1_runtime_identity.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 1, "Phase 1 runtime receipt drift")
    require(receipt["status"] == "frozen_release_candidate_under_test", "Phase 1 runtime role drift")
    require(receipt["validation_status"] == "pending_phase4", "Phase 1 runtime prematurely validated")
    require(receipt["implementation_commit"] == PHASE1_IMPLEMENTATION_COMMIT, "implementation commit drift")
    identity = receipt["execution_identity"]
    require(
        identity
        == {
            "execution_mode": "gpu-screen",
            "scientific_contract": "biological_topk_candidate_site_v1",
            "output_schema": "gasal2_candidate_sites_tsv_v1",
            "software_epoch": "submission_rc_v2",
        },
        "four-way runtime identity drift",
    )
    require(set(receipt["runtime_source_sha256"]) == set(PHASE1_RUNTIME_PATHS), "runtime source inventory drift")
    for relative, expected in receipt["runtime_source_sha256"].items():
        require(sha256_bytes(git_bytes("show", f"{PHASE1_IMPLEMENTATION_COMMIT}:{relative}")) == expected, f"frozen runtime source drift: {relative}")
        require(sha256_file(ROOT / relative) == expected, f"working runtime source changed: {relative}")
    diff = run(("git", "diff", "--quiet", PHASE1_IMPLEMENTATION_COMMIT, "--", *PHASE1_RUNTIME_PATHS), check=False)
    require(diff.returncode == 0, "runtime path changed after implementation freeze")

    candidate = receipt["candidate_binary"]
    candidate_path = ROOT / candidate["source_path"]
    require(candidate_path.is_file(), "frozen candidate binary is missing")
    require(sha256_file(candidate_path) == candidate["sha256"], "candidate binary digest drift")
    require(candidate["sha256"] == "ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9", "candidate binary identity drift")

    container = receipt["container"]
    archive = artifact_path(container["archive_relative_path"])
    require(archive.stat().st_size == container["archive_bytes"], "container archive size drift")
    require(sha256_file(archive) == container["archive_sha256"], "container archive digest drift")
    embedded_path = artifact_path(container["embedded_identity_relative_path"])
    require(sha256_file(embedded_path) == container["embedded_identity_sha256"], "embedded identity digest drift")
    embedded = load_json(embedded_path)
    require(embedded["implementation_commit"] == PHASE1_IMPLEMENTATION_COMMIT, "embedded implementation commit drift")
    require(embedded["candidate_binary_sha256"] == candidate["sha256"], "embedded candidate digest drift")
    for field, expected in identity.items():
        require(embedded[field] == expected, f"embedded runtime {field} drift")
    image = run(("docker", "image", "inspect", container["image_tag"], "--format", "{{.Id}}"), check=False)
    require(image.returncode == 0, "frozen Phase 1 container image is unavailable")
    require(image.stdout.decode().strip() == container["image_digest"], "container image digest drift")
    require(container["entrypoint"] == ["/usr/bin/python3.11", "/opt/gasal2/gasal2_gpu_screen.py"], "container entrypoint drift")
    schedule = receipt["validated_gpu_container_schedule"]
    require(schedule["nvidia_container_toolkit_available"] is False, "toolkit availability receipt drift")
    require(schedule["mode"] == "explicit_device_and_read_only_host_driver_bind", "container GPU schedule drift")
    require(schedule["standard_gpus_attempt_result"] == "environment_unavailable_before_product_execution", "failed standard GPU attempt was hidden")
    for absolute, expected in schedule["host_driver_sha256"].items():
        path = Path(absolute)
        require(path.is_file() and sha256_file(path) == expected, f"host driver identity drift: {absolute}")
    require(receipt["complete_cpu_authority_inside_product"] is False, "runtime includes complete CPU authority")
    require(receipt["formal_performance_claim"] is False, "Phase 1 runtime claims performance")


def load_candidate_sites_module():
    path = ROOT / "scripts/gasal2_candidate_sites.py"
    spec = importlib.util.spec_from_file_location("v2_candidate_sites_checker", path)
    require(spec is not None and spec.loader is not None, "cannot load candidate-sites validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules["v2_candidate_sites_checker"] = module
    spec.loader.exec_module(module)
    return module


def load_gpu_screen_schema_validator():
    path = ROOT / "scripts/gasal2_longtarget.py"
    spec = importlib.util.spec_from_file_location("v2_gpu_screen_schema_validator", path)
    require(spec is not None and spec.loader is not None, "cannot load GPU-screen schema validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules["v2_gpu_screen_schema_validator"] = module
    spec.loader.exec_module(module)
    return module


def check_phase1_smoke() -> None:
    receipt = load_json(PAPER / "phase_1_smoke_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 1, "Phase 1 smoke receipt drift")
    require(receipt["development_diagnostic_only"] is True, "Phase 1 smoke was promoted")
    require(receipt["excluded_from_all_v2_formal_panels"] is True, "smoke input not excluded from formal panels")
    report_schema = load_json(ROOT / "schemas/gasal2_gpu_screen_run_report_v1.schema.json")
    report_validator = load_gpu_screen_schema_validator()
    reports = {}
    for arm in ("host", "container"):
        record = receipt["reports"][arm]
        path = artifact_path(record["relative_path"])
        require(sha256_file(path) == record["sha256"], f"{arm} smoke report digest drift")
        report = load_json(path)
        report_validator.validate_schema_value(report_schema, report, "report")
        require(report["result_status"] == "release_candidate_under_test_complete", f"{arm} smoke failed")
        require(report["backend_telemetry"]["gasal2_requests"] > 0, f"{arm} smoke had no GPU requests")
        require(report["backend_telemetry"]["fallbacks"] == 0, f"{arm} smoke used fallback")
        require(report["runtime_identity"]["source_commit"] == PHASE1_IMPLEMENTATION_COMMIT, f"{arm} source identity drift")
        require(report["runtime_identity"]["container_image_digest"] == receipt["container_image_digest"], f"{arm} image identity drift")
        reports[arm] = report
    host_sites = artifact_path(receipt["candidate_sites"]["host_relative_path"])
    container_sites = artifact_path(receipt["candidate_sites"]["container_relative_path"])
    require(host_sites.read_bytes() == container_sites.read_bytes(), "host/container candidate sites are not byte-identical")
    require(sha256_file(container_sites) == receipt["candidate_sites"]["sha256"], "smoke candidate-sites digest drift")
    summary = load_candidate_sites_module().validate_candidate_sites(container_sites)
    require(summary["row_count"] == receipt["candidate_sites"]["row_count"], "smoke row-count drift")
    require(reports["host"]["candidate_sites"]["sha256"] == summary["sha256"], "host report/product mismatch")
    require(reports["container"]["candidate_sites"]["sha256"] == summary["sha256"], "container report/product mismatch")
    for input_record in receipt["inputs"]:
        path = ROOT / input_record["path"]
        require(path.is_file() and sha256_file(path) == input_record["sha256"], "Phase 1 smoke input drift")
    require(receipt["performance_estimate_generated"] is False, "Phase 1 generated a performance estimate")


def run_phase1_tests() -> None:
    run((sys.executable, "tests/bioinformatics_submission_readiness_v2/test_phase1.py"))
    run((sys.executable, "tests/bioinformatics_submission_readiness_v2/test_gpu_screen.py"))
    run((sys.executable, "tests/check_gasal2_longtarget_cli.py"))


def check_phase1(mode: str) -> None:
    status_before = changed_paths()
    if mode == "precommit":
        require(git("rev-parse", "HEAD") == PHASE1_IMPLEMENTATION_COMMIT, "Phase 1 precommit parent drift")
        require(status_before == set(PHASE1_PATHS), "Phase 1 changed paths differ from allowlist")
        allowlist = tuple((PAPER / "phase_1_change_allowlist.txt").read_text(encoding="utf-8").splitlines())
        require(allowlist == PHASE1_PATHS, "Phase 1 allowlist drift")
        check_phase1_precommit_receipt(None)
    else:
        require(not status_before, "Phase 1 postcommit requires a clean tree")
        commit = commit_with_subject(PHASE1_COMMIT_MESSAGE)
        require(git("rev-parse", f"{commit}^") == PHASE1_IMPLEMENTATION_COMMIT, "Phase 1 commit parent drift")
        check_phase1_precommit_receipt(commit)
    state = validate_program_state()
    require(state["phase_status"] == {"0": "pass", "1": "pass", "2": "active", "3": "pending", "4": "pending", "5": "pending", "6": "pending", "7": "pending"}, "Phase 1 state drift")
    require(state["active_phase"] == 2 and state["last_completed_phase"] == 1, "Phase 1 transition drift")
    require(state["artifact_role"] == "frozen_release_candidate_under_test", "Phase 1 artifact role drift")
    require(state["product_status"] == "experimental" and state["validation_status"] == "pending", "Phase 1 product prematurely validated")
    require(state["target_claim_status"] == "pending_final_rc_performance_validation", "Phase 1 target claim promoted")
    check_phase0_history()
    check_phase1_start_receipt()
    check_phase1_runtime()
    check_phase1_artifact_manifest()
    check_phase1_smoke()
    check_legacy_boundary()
    run_phase1_tests()


def check_phase1_history() -> None:
    commit = commit_with_subject(PHASE1_COMMIT_MESSAGE)
    require(git("rev-parse", f"{commit}^") == PHASE1_IMPLEMENTATION_COMMIT, "Phase 1 historical parent drift")
    check_phase1_precommit_receipt(commit)
    state = load_json_from_commit(
        commit, "paper/bioinformatics_submission_readiness_v2/PROGRAM_STATE.json"
    )
    validate_schema(state, load_json(SCHEMA))
    validate_state_transitions(state)
    require(state["active_phase"] == 2 and state["last_completed_phase"] == 1, "Phase 1 historical state drift")
    require(state["software_epoch"] == "submission_rc_v2", "Phase 1 historical epoch was rewritten")
    for relative in PHASE1_FROZEN_EVIDENCE_PATHS:
        require(
            (ROOT / relative).read_bytes() == git_bytes("show", f"{commit}:{relative}"),
            f"Phase 1 frozen evidence was rewritten: {relative}",
        )
    check_phase0_history()


def check_phase2_start_receipt() -> None:
    receipt = load_json(PAPER / "phase_2_start_receipt.json")
    phase1_commit = commit_with_subject(PHASE1_COMMIT_MESSAGE)
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "Phase 2 start receipt drift")
    require(receipt["phase_1_transition_commit"] == phase1_commit, "Phase 2 start/Phase 1 binding drift")
    require(receipt["phase_start_parent_head"] == phase1_commit, "Phase 2 start parent drift")
    require(receipt["freeze_parent_head"] == PHASE2_FREEZE_PARENT, "Phase 2 freeze parent drift")
    require(receipt["phase_start_tree_was_clean"] is True, "Phase 2 did not start from a clean Phase 1 commit")
    require(receipt["previous_phase_postcommit_check_result"] == "pass", "Phase 1 postcommit audit was not preserved")
    require(receipt["receipt_created_at_freeze"] is True, "Phase 2 receipt timing disclosure missing")


def check_phase2_precommit_receipt(commit: str | None) -> None:
    relative = "paper/bioinformatics_submission_readiness_v2/phase_2_precommit_receipt.json"
    receipt = load_json(PAPER / "phase_2_precommit_receipt.json") if commit is None else load_json_from_commit(commit, relative)
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "Phase 2 precommit receipt drift")
    require(receipt["phase_start_parent_head"] == PHASE2_FREEZE_PARENT, "Phase 2 precommit parent drift")
    require(receipt["planned_commit_message"] == PHASE2_COMMIT_MESSAGE, "Phase 2 commit message drift")
    require(receipt["expected_changed_paths"] == list(PHASE2_PATHS), "Phase 2 path inventory drift")
    expected_evidence = set(PHASE2_PATHS) - {relative}
    require(set(receipt["schema_evidence_sha256"]) == expected_evidence, "Phase 2 evidence inventory drift")
    for path, expected in receipt["schema_evidence_sha256"].items():
        require(sha256_bytes(file_bytes(path, commit)) == expected, f"Phase 2 evidence digest drift: {path}")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "Phase 2 receipt claims future commit")


def check_phase2_supersession() -> None:
    receipt = load_json(PAPER / "phase_2_supersession_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "Phase 2 supersession receipt drift")
    require(receipt["discovered_during_excluded_development"] is True, "supersession discovery boundary drift")
    require(receipt["formal_attempts_before_discovery"] == 0, "formal attempts preceded runtime correction")
    require(receipt["supersession_does_not_rewrite_phase_1"] is True, "supersession permits Phase 1 rewrite")
    old = receipt["old_epoch"]
    new = receipt["new_epoch"]
    require(old["software_epoch"] == "submission_rc_v2" and old["preserved_artifact"] is True, "old epoch was not preserved")
    require(old["implementation_commit"] == PHASE1_IMPLEMENTATION_COMMIT, "old epoch commit drift")
    require(new["software_epoch"] == "submission_rc_v2_2", "new epoch identity drift")
    require(new["implementation_commit"] == PHASE2_RUNTIME_COMMIT, "new epoch commit drift")
    require(new["validation_status"] == "pending_phase4", "new epoch prematurely validated")
    require(old["candidate_binary_sha256"] == new["candidate_binary_sha256"], "candidate binary changed during identity correction")
    phase1_runtime = load_json(PAPER / "phase_1_runtime_identity.json")
    require(phase1_runtime["execution_identity"]["software_epoch"] == "submission_rc_v2", "Phase 1 runtime receipt was rewritten")


def check_phase2_runtime() -> None:
    receipt = load_json(PAPER / "phase_2_runtime_identity.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "Phase 2 runtime receipt drift")
    require(receipt["status"] == "frozen_release_candidate_under_test", "Phase 2 runtime role drift")
    require(receipt["validation_status"] == "pending_phase4", "Phase 2 runtime prematurely validated")
    require(receipt["implementation_commit"] == PHASE2_RUNTIME_COMMIT, "Phase 2 implementation commit drift")
    require(
        receipt["execution_identity"]
        == {
            "execution_mode": "gpu-screen",
            "scientific_contract": "biological_topk_candidate_site_v1",
            "output_schema": "gasal2_candidate_sites_tsv_v1",
            "software_epoch": "submission_rc_v2_2",
        },
        "Phase 2 four-way runtime identity drift",
    )
    require(set(receipt["runtime_source_sha256"]) == set(PHASE2_RUNTIME_PATHS), "Phase 2 runtime inventory drift")
    for relative, expected in receipt["runtime_source_sha256"].items():
        require(sha256_bytes(git_bytes("show", f"{PHASE2_RUNTIME_COMMIT}:{relative}")) == expected, f"v2.2 committed runtime drift: {relative}")
        require(sha256_file(ROOT / relative) == expected, f"v2.2 working runtime drift: {relative}")
    runtime_diff = run(("git", "diff", "--quiet", PHASE2_RUNTIME_COMMIT, "--", *PHASE2_RUNTIME_PATHS), check=False)
    require(runtime_diff.returncode == 0, "runtime path changed after v2.2 freeze")
    require(
        sha256_file(ROOT / "reproduce/bioinformatics_submission_readiness_v2/build_runtime_image.py")
        == receipt["container"]["build_script_sha256"],
        "v2.2 build script drift",
    )

    candidate = receipt["candidate_binary"]
    candidate_path = ROOT / candidate["source_path"]
    require(candidate_path.is_file() and sha256_file(candidate_path) == candidate["sha256"], "v2.2 candidate binary drift")
    require(candidate["sha256"] == "ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9", "v2.2 candidate identity drift")
    require(receipt["complete_cpu_authority_inside_product"] is False, "v2.2 product embeds complete CPU authority")
    require(receipt["formal_performance_claim"] is False, "Phase 2 runtime claims performance")

    container = receipt["container"]
    archive = artifact_path(container["archive_relative_path"])
    require(archive.stat().st_size == container["archive_bytes"], "v2.2 archive size drift")
    require(sha256_file(archive) == container["archive_sha256"], "v2.2 archive digest drift")
    embedded_path = artifact_path(container["embedded_identity_relative_path"])
    require(sha256_file(embedded_path) == container["embedded_identity_sha256"], "v2.2 embedded identity drift")
    embedded = load_json(embedded_path)
    require(embedded["implementation_commit"] == PHASE2_RUNTIME_COMMIT, "v2.2 embedded commit drift")
    require(embedded["candidate_binary_sha256"] == candidate["sha256"], "v2.2 embedded binary drift")
    for field, expected in receipt["execution_identity"].items():
        require(embedded[field] == expected, f"v2.2 embedded {field} drift")
    image = run(("docker", "image", "inspect", container["image_tag"], "--format", "{{.Id}}"), check=False)
    require(image.returncode == 0, "v2.2 container image is unavailable")
    require(image.stdout.decode().strip() == container["image_digest"], "v2.2 image digest drift")
    require(container["entrypoint"] == ["/usr/bin/python3.11", "/opt/gasal2/gasal2_gpu_screen.py"], "v2.2 entrypoint drift")
    schedule = receipt["validated_gpu_container_schedule"]
    require(schedule["nvidia_container_toolkit_available"] is False, "v2.2 toolkit availability drift")
    require(schedule["mode"] == "explicit_device_and_read_only_host_driver_bind", "v2.2 container schedule drift")

    report_schema = load_json(ROOT / "schemas/gasal2_gpu_screen_run_report_v1.schema.json")
    report_validator = load_gpu_screen_schema_validator()
    reports: dict[str, Any] = {}
    smoke = receipt["smoke"]
    for arm in ("host", "container"):
        relative = smoke[f"{arm}_report_relative_path"]
        path = artifact_path(relative)
        require(sha256_file(path) == smoke[f"{arm}_report_sha256"], f"v2.2 {arm} smoke digest drift")
        report = load_json(path)
        report_validator.validate_schema_value(report_schema, report, "report")
        require(report["result_status"] == "release_candidate_under_test_complete", f"v2.2 {arm} smoke failed")
        require(report["runtime_identity"]["source_commit"] == PHASE2_RUNTIME_COMMIT, f"v2.2 {arm} source drift")
        require(report["runtime_identity"]["container_image_digest"] == container["image_digest"], f"v2.2 {arm} image binding drift")
        require(report["backend_telemetry"]["fallbacks"] == 0, f"v2.2 {arm} used fallback")
        require(report["backend_telemetry"]["gasal2_requests"] == smoke["gasal2_requests"], f"v2.2 {arm} request-count drift")
        reports[arm] = report
    host_sites = artifact_path("phase1/runtime-epoch-v2-2/real-gpu-smoke-host/product/candidate_sites.tsv")
    container_sites = artifact_path("phase1/runtime-epoch-v2-2/real-gpu-smoke/product/candidate_sites.tsv")
    require(host_sites.read_bytes() == container_sites.read_bytes(), "v2.2 host/container sites differ")
    require(sha256_file(container_sites) == smoke["candidate_sites_sha256"], "v2.2 candidate-sites digest drift")
    summary = load_candidate_sites_module().validate_candidate_sites(container_sites)
    require(summary["software_epoch"] == "submission_rc_v2_2", "v2.2 product epoch drift")
    require(reports["host"]["candidate_sites"]["sha256"] == summary["sha256"], "v2.2 host report/product mismatch")
    require(reports["container"]["candidate_sites"]["sha256"] == summary["sha256"], "v2.2 container report/product mismatch")
    require(reports["host"]["product_identity"]["target_region_start0"] == smoke["target_region_start0"], "v2.2 host target start drift")
    require(reports["container"]["product_identity"]["target_region_start0"] == smoke["target_region_start0"], "v2.2 container target start drift")

    module = load_candidate_sites_module()
    query_path = ROOT / "reproduce/bioinformatics/holdout_inputs/queries/hq01_ENSG00000276454_ENST00000615076.fa"
    target_path = ROOT / "reproduce/bioinformatics/holdout_inputs/targets/ht01_ENSG00000159423_chr1_18902299_18904799.fa"
    identity = module.ProductIdentity(
        workload_id="phase1_v2_2_excluded_smoke",
        assembly="GRCh38",
        target_coordinate_namespace="GRCh38_0_based_half_open",
        target_region_start0=smoke["target_region_start0"],
    )
    input_receipt = module.build_receipt(
        query=module.read_single_fasta(query_path, "query"),
        target=module.read_single_fasta(target_path, "target"),
        tfosorted=artifact_path("phase1/runtime-epoch-v2-2/real-gpu-smoke/product/diagnostics/native-TFOsorted"),
        identity=identity,
    )
    interval = input_receipt.input_identity["target_extracted_interval"]
    require([interval["start0"], interval["end0"]] == smoke["target_extracted_interval"], "v2.2 genomic extraction identity drift")


def check_phase2_artifact_manifest() -> None:
    manifest = load_json(PAPER / "phase_2_artifact_manifest.json")
    require(manifest["schema_version"] == 1 and manifest["phase"] == 2, "Phase 2 artifact manifest drift")
    require(manifest["formal_claim_evidence"] is False, "Phase 2 artifacts were promoted")
    observed: set[str] = set()
    for item in manifest["artifacts"]:
        relative = item["relative_path"]
        require(relative not in observed, "duplicate Phase 2 artifact path")
        observed.add(relative)
        path = artifact_path(relative)
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 2 artifact: {relative}")
        require(path.stat().st_size == item["size_bytes"], f"Phase 2 artifact size drift: {relative}")
        require(sha256_file(path) == item["sha256"], f"Phase 2 artifact digest drift: {relative}")
    total = sum(path.stat().st_size for path in ARTIFACT_ROOT.rglob("*") if path.is_file())
    state = validate_program_state()
    require(total <= state["fixed_v2_artifact_storage_bytes"], "v2 artifact quota exceeded")
    require(manifest["bytes_at_phase2_freeze"] <= manifest["quota_bytes"], "Phase 2 froze over quota")


def check_phase2_development() -> None:
    receipt = load_json(PAPER / "phase_2_development_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "Phase 2 development receipt drift")
    require(receipt["formal_claim"] is False and receipt["formal_performance_estimate"] is None, "development diagnostics were promoted")
    require(receipt["all_development_inputs_excluded_from_formal_panels"] is True, "development input exclusion drift")
    summary_path = artifact_path(receipt["summary_relative_path"])
    require(sha256_file(summary_path) == receipt["summary_sha256"], "development summary digest drift")
    summary = load_json(summary_path)
    require(summary["formal_claim"] is False and summary["workload_count"] == 3, "development summary boundary drift")
    expected = {
        "phase2_dev_bts3_w022": ("development_failure", False),
        "phase2_dev_bts3_w006": ("development_failure", False),
        "phase2_dev_bts3_w153": ("development_pass", True),
    }
    require({item["workload_id"] for item in receipt["development_pairs"]} == set(expected), "development pair inventory drift")
    for item in receipt["development_pairs"]:
        workload_id = item["workload_id"]
        status, contract_pass = expected[workload_id]
        require(item["status"] == status and item["contract_pass"] is contract_pass, f"development decision drift: {workload_id}")
        require(abs(item["diagnostic_speedup"] - item["authority_wall_seconds"] / item["candidate_wall_seconds"]) < 1e-12, f"development speedup arithmetic drift: {workload_id}")
        pair_path = artifact_path(f"phase2/development-harness/{workload_id}/pair-complete.json")
        pair = load_json(pair_path)
        require(pair["development_diagnostic_only"] is True and pair["excluded_from_all_v2_formal_panels"] is True, f"development pair promoted: {workload_id}")
        require(pair["status"] == status, f"development terminal status drift: {workload_id}")
        require(pair["comparison"]["result"]["contract_pass"] is contract_pass, f"development comparator drift: {workload_id}")
    invalid = receipt["non_acgt_preflight"]
    invalid_report = load_json(artifact_path(invalid["artifact_relative_path"]))
    require(sha256_file(artifact_path(invalid["artifact_relative_path"])) == invalid["artifact_sha256"], "non-ACGT receipt digest drift")
    require(invalid_report["result_status"] == "invalid_input" and invalid["backend_executed"] is False, "non-ACGT preflight drift")


def check_phase2_external() -> None:
    protocol = load_json(PAPER / "phase_2_external_search_protocol.json")
    require(protocol["schema_version"] == 1 and protocol["phase"] == 2, "external search protocol drift")
    require(protocol["search_date"] == "2026-07-31", "external search date drift")
    require(protocol["formal_comparator_selection_frozen"] is False, "formal comparator selected before Phase 3")
    require(len(protocol["inclusion_criteria"]) >= 4 and len(protocol["exclusion_criteria"]) >= 5, "external search criteria incomplete")
    with (PAPER / "external_method_landscape.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    tools = {row["tool"]: row for row in rows}
    require(set(tools) == {"PATO", "Triplexator", "3plex", "TriplexAligner", "TripLexicon", "TriplexFPP", "Triplexity", "Triplex_Bioconductor"}, "external landscape inventory drift")
    require(tools["PATO"]["phase2_decision"] == "retain_for_phase3_semantic_freeze", "PATO landscape decision drift")
    require(tools["Triplexator"]["phase2_decision"] == "retain_as_legacy_reference", "Triplexator landscape decision drift")
    require(tools["TripLexicon"]["direct_runtime_candidate"] == "no", "web resource promoted to runtime comparator")

    receipt = load_json(PAPER / "phase_2_external_tool_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "external tool receipt drift")
    require(receipt["formal_comparison_authorized"] is False, "formal external comparison began in Phase 2")
    pato = receipt["pato"]
    pato_binary = ROOT / pato["binary_path"]
    require(sha256_file(pato_binary) == pato["binary_sha256"], "PATO binary drift")
    require(sha256_file(ROOT / pato["license_path"]) == pato["license_sha256"], "PATO license drift")
    require(pato["upstream_tag"] == "1.0.6" and pato["upstream_commit"] == "0c90c163f3582a457dfc808d656a8c992a95a3ba", "PATO release identity drift")
    pato_head = run(("git", "-C", str(pato_binary.parents[3]), "rev-parse", "HEAD")).stdout.decode().strip()
    require(pato_head == pato["upstream_commit"], "PATO checkout drift")
    require(pato["upstream_test_diagnostics"]["clean_serial_final_result"] == "224_of_224_pass", "PATO isolated test result drift")
    triplexator = receipt["triplexator"]
    require(sha256_file(ROOT / triplexator["binary_path"]) == triplexator["binary_sha256"], "Triplexator binary drift")
    require(sha256_file(ROOT / triplexator["license_path"]) == triplexator["license_sha256"], "Triplexator license drift")
    require(triplexator["historical_five_failures_reinterpreted"] is False, "historical Triplexator failures were rewritten")
    for tool in ("pato", "triplexator"):
        record = receipt[tool]
        report_path = artifact_path(record["development_report_relative_path"])
        require(sha256_file(report_path) == record["development_report_sha256"], f"{tool} development report drift")
        report = load_json(report_path)
        require(report["status"] == "development_success", f"{tool} development smoke failed")
        require(report["development_diagnostic_only"] is True and report["excluded_from_all_v2_formal_panels"] is True, f"{tool} development result promoted")
        require(report["output_basename_only"] is True and report["expected_summary_suffix"] == ".summary", f"{tool} output semantics drift")
        require(report["tool_identity"]["binary_sha256"] == record["binary_sha256"], f"{tool} report binary binding drift")


def run_phase2_tests() -> None:
    for relative in (
        "tests/bioinformatics_submission_readiness_v2/test_capacity.py",
        "tests/bioinformatics_submission_readiness_v2/test_development_harness.py",
        "tests/bioinformatics_submission_readiness_v2/test_external_development.py",
        "tests/bioinformatics_submission_readiness_v2/test_gpu_screen.py",
        "tests/bioinformatics_submission_readiness_v2/test_phase2.py",
    ):
        run((sys.executable, relative))
    for relative in (
        "reproduce/bioinformatics_submission_readiness_v2/cpu_reference_screen.py",
        "reproduce/bioinformatics_submission_readiness_v2/run_development_harness.py",
        "reproduce/bioinformatics_submission_readiness_v2/run_external_development.py",
    ):
        run((sys.executable, "-m", "py_compile", relative))
    capacity_paths = (
        "reproduce/bioinformatics_submission_readiness_v2/capacity.py",
        "tests/bioinformatics_submission_readiness_v2/test_capacity.py",
    )
    diff = run(("git", "diff", "--quiet", PHASE2_CAPACITY_COMMIT, "--", *capacity_paths), check=False)
    require(diff.returncode == 0, "capacity estimator changed after its Phase 2 commit")


def check_phase2(mode: str) -> None:
    status_before = changed_paths()
    if mode == "precommit":
        require(git("rev-parse", "HEAD") == PHASE2_FREEZE_PARENT, "Phase 2 precommit parent drift")
        require(status_before == set(PHASE2_PATHS), "Phase 2 changed paths differ from allowlist")
        allowlist = tuple((PAPER / "phase_2_change_allowlist.txt").read_text(encoding="utf-8").splitlines())
        require(allowlist == PHASE2_PATHS, "Phase 2 allowlist drift")
        check_phase2_precommit_receipt(None)
    else:
        require(not status_before, "Phase 2 postcommit requires a clean tree")
        commit = commit_with_subject(PHASE2_COMMIT_MESSAGE)
        require(git("rev-parse", f"{commit}^") == PHASE2_FREEZE_PARENT, "Phase 2 commit parent drift")
        check_phase2_precommit_receipt(commit)
    state = validate_program_state()
    require(state["phase_status"] == {"0": "pass", "1": "pass", "2": "pass", "3": "active", "4": "pending", "5": "pending", "6": "pending", "7": "pending"}, "Phase 2 state drift")
    require(state["active_phase"] == 3 and state["last_completed_phase"] == 2, "Phase 2 transition drift")
    require(state["software_epoch"] == "submission_rc_v2_2", "Phase 2 active software epoch drift")
    require(state["artifact_role"] == "frozen_release_candidate_under_test", "Phase 2 artifact role drift")
    require(state["product_status"] == "experimental" and state["validation_status"] == "pending", "Phase 2 product prematurely validated")
    require(state["target_claim_status"] == "pending_final_rc_performance_validation", "Phase 2 target claim promoted")
    require(not state["external_comparison_authorized"] and not state["release_packaging_authorized"] and not state["submission_drafting_authorized"], "Phase 2 granted downstream authorization")
    check_phase1_history()
    check_phase2_start_receipt()
    check_phase2_supersession()
    check_phase2_runtime()
    check_phase2_artifact_manifest()
    check_phase2_development()
    check_phase2_external()
    check_legacy_boundary()
    run_phase2_tests()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=range(8), required=True)
    parser.add_argument("--mode", choices=("precommit", "postcommit"), required=True)
    args = parser.parse_args()
    try:
        if args.phase == 0:
            check_phase0(args.mode)
        elif args.phase == 1:
            check_phase1(args.mode)
        elif args.phase == 2:
            check_phase2(args.mode)
        else:
            raise CheckError("checker for requested phase is not implemented yet")
        print(f"Bioinformatics submission readiness v2 Phase {args.phase} {args.mode} checks OK")
        return 0
    except (CheckError, OSError, ValueError, KeyError, json.JSONDecodeError, SchemaValidationError) as error:
        print(f"v2 phase check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
