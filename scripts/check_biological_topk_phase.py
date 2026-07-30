#!/usr/bin/env python3
"""Normative checker for biological Top-K phases 0 through 9."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/biological_topk"
STATE_PATH = PAPER / "PROGRAM_STATE.json"
SCHEMA_PATH = ROOT / "schemas/biological_topk_program_state.schema.json"
EXECUTION_START_HEAD = "2658a98fea8f34bd295892e6236607060e2f2803"
EXECUTION_BRANCH = "gasal2-kcnq1ot1-focused-review"
PROTOCOL_SHA256 = "1cd5e5a023d53655641ba831142f489011111fd2c166d895b2a851b0f513f6c3"
PHASE0_COMMIT_MESSAGE = "docs: freeze biological Top-K candidate-site validation epoch"

PHASE_STATUSES = {
    "pending",
    "active",
    "pass",
    "no_go",
    "blocked_missing_evidence",
    "blocked_insufficient_source_universe",
    "blocked_insufficient_information",
    "blocked_insufficient_experimental_information",
    "blocked_external_data",
    "blocked_fixed_budget",
    "blocked_technical_failure",
    "not_authorized_previous_no_go",
}
BLOCKING_STATUSES = {
    status for status in PHASE_STATUSES if status.startswith("blocked_")
} | {"no_go"}


class CheckError(RuntimeError):
    pass


class SchemaValidationError(CheckError):
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
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise CheckError(detail or f"command failed: {' '.join(arguments)}")
    return completed


def git(*arguments: str) -> str:
    return run(("git", *arguments)).stdout.decode("utf-8").strip()


def git_bytes(*arguments: str) -> bytes:
    return run(("git", *arguments)).stdout


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckError(f"invalid JSON {path}: {error}") from error


def schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise SchemaValidationError(f"unsupported schema type: {expected}")


def resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    require(reference.startswith("#/"), f"unsupported schema reference: {reference}")
    node: Any = root_schema
    for part in reference[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    require(isinstance(node, dict), f"schema reference is not an object: {reference}")
    return node


def validate_schema(
    value: Any,
    schema: dict[str, Any],
    *,
    root_schema: dict[str, Any] | None = None,
    path: str = "$",
) -> None:
    root = root_schema or schema
    if "$ref" in schema:
        validate_schema(value, resolve_ref(root, schema["$ref"]), root_schema=root, path=path)
        return
    if "anyOf" in schema:
        errors: list[str] = []
        for candidate in schema["anyOf"]:
            try:
                validate_schema(value, candidate, root_schema=root, path=path)
                break
            except CheckError as error:
                errors.append(str(error))
        else:
            raise SchemaValidationError(f"{path}: no anyOf branch matched: {'; '.join(errors)}")
    if "type" in schema and not schema_type_matches(value, schema["type"]):
        raise SchemaValidationError(f"{path}: expected {schema['type']}, got {type(value).__name__}")
    if "const" in schema and value != schema["const"]:
        raise SchemaValidationError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path}: unknown enum value {value!r}")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaValidationError(f"{path}: value below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaValidationError(f"{path}: value above maximum")
    if isinstance(value, str) and "pattern" in schema:
        if re.fullmatch(schema["pattern"], value) is None:
            raise SchemaValidationError(f"{path}: string does not match pattern")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise SchemaValidationError(f"{path}: missing required keys: {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise SchemaValidationError(f"{path}: unknown keys: {unknown}")
        for key, child in value.items():
            if key in properties:
                validate_schema(child, properties[key], root_schema=root, path=f"{path}.{key}")


def final_route(decision: str) -> str:
    mapping = {
        "bioinformatics_application_note_ready_for_submission":
            "bioinformatics_application_note_ready_for_submission",
        "bioinformatics_application_note_ready_pending_owner_actions":
            "bioinformatics_application_note_ready_pending_owner_actions",
        "release_or_reproducibility_blocked": "release_or_reproducibility_blocked",
        "candidate_site_concordance_no_go": "closed_for_this_contract",
        "biological_utility_no_go": "closed_biological_utility_gap",
        "performance_widening_no_go_retarget_csbj": "no_go_retarget_csbj_or_methods",
    }
    require(decision in mapping, f"unknown final decision: {decision}")
    return mapping[decision]


def validate_state_transitions(state: dict[str, Any]) -> None:
    statuses = state["phase_status"]
    require(set(statuses) == {str(index) for index in range(10)}, "phase status keys drift")
    require(set(statuses.values()) <= PHASE_STATUSES, "unknown phase status")

    if state["gpu_screen_status"] == "validated_screening_backend_v1_release_candidate":
        require(statuses["8"] == "pass", "validated product status requires Phase 8 pass")
        require(
            state["contract_status"] == "validated_within_fixed_operating_envelope",
            "validated product status requires validated contract status",
        )
    if statuses["8"] == "no_go":
        require(state["gpu_screen_status"] == "experimental", "Phase 8 no-go must revoke product status")
        require(
            state["contract_status"] == "release_or_reproducibility_blocked",
            "Phase 8 no-go contract state drift",
        )
        require(statuses["9"] == "not_authorized_previous_no_go", "Phase 9 must be unauthorized")
    if statuses["9"] == "pass":
        require(state["active_phase"] is None, "Phase 9 pass requires terminal active_phase")
        require(state["final_decision"] is not None, "Phase 9 pass requires final decision")
        require(
            state["final_decision"] == state["final_decision_candidate"],
            "certified decision differs from audit candidate",
        )
        require(
            state["bioinformatics_route"] == final_route(state["final_decision"]),
            "final decision route mapping drift",
        )

    blocking = [index for index in range(10) if statuses[str(index)] in BLOCKING_STATUSES]
    if blocking:
        first = min(blocking)
        if state["active_phase"] is not None:
            require(state["active_phase"] <= first, "later phase active after terminal blocking state")
        for later in range(first + 1, 10):
            require(
                statuses[str(later)] in {"pending", "not_authorized_previous_no_go"},
                "later phase advanced after terminal blocking state",
            )


def validate_program_state() -> dict[str, Any]:
    schema = load_json(SCHEMA_PATH)
    state = load_json(STATE_PATH)
    validate_schema(state, schema)
    validate_state_transitions(state)
    return state


def changed_paths() -> set[str]:
    payload = git_bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = payload.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        require(len(entry) >= 4 and entry[2:3] == b" ", f"cannot parse git status: {entry!r}")
        paths.add(entry[3:].decode("utf-8"))
        if entry[:1] in {b"R", b"C"} or entry[1:2] in {b"R", b"C"}:
            require(index < len(entries) and entries[index], "truncated git rename status")
            paths.add(entries[index].decode("utf-8"))
            index += 1
    return paths


def allowlist(phase: int) -> list[str]:
    path = PAPER / f"phase_{phase}_change_allowlist.txt"
    require(path.is_file() and not path.is_symlink(), f"missing Phase {phase} allowlist")
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(rows == sorted(set(rows)), f"Phase {phase} allowlist must be sorted and unique")
    require(all(not Path(row).is_absolute() and ".." not in Path(row).parts for row in rows), "unsafe allowlist path")
    return rows


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    require(fields and all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return fields, rows


def frozen_text(path: str) -> str:
    return git_bytes("show", f"{EXECUTION_START_HEAD}:{path}").decode("utf-8")


def check_historical_decisions() -> None:
    phase2 = frozen_text("paper/bioinformatics/phase2_decision.md")
    hybrid_regression = frozen_text("paper/bioinformatics/canonical_hybrid_v2_regression_decision.md")
    hybrid_holdout = frozen_text("paper/bioinformatics/canonical_hybrid_v2_holdout_decision.md")
    hybrid_performance = frozen_text("paper/bioinformatics/canonical_hybrid_v2_performance_decision.md")
    ssw_decision = json.loads(frozen_text("paper/ssw_cuda/final_decision.json"))
    paper_status = frozen_text("paper/PAPER_PREP_STATUS.md")
    require("verified_only_contract" in phase2, "strict canonical-row v1 decision drift")
    require("36/36" in hybrid_regression and "35/36" in hybrid_regression, "hybrid regression drift")
    require("60/60" in hybrid_holdout, "hybrid holdout drift")
    require("0.257592x" in hybrid_performance and "3.882109x" in hybrid_performance, "hybrid performance drift")
    require("performance_gate = no_go" in hybrid_performance, "hybrid no-go drift")
    require(
        ssw_decision["decision"] == "ssw_cuda_forward_or_reverse_checkpoint_only",
        "SSW-CUDA final decision drift",
    )
    require("38.320882x" in paper_status, "historical 38.32x anchor missing")


def check_phase0_registries() -> None:
    for script in (
        "reproduce/biological_topk/build_historical_blob_registry.py",
        "reproduce/biological_topk/build_exclusion_registry.py",
    ):
        completed = run((sys.executable, script, "--check"), check=False)
        require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))

    historical_fields, historical = read_tsv(PAPER / "historical_blob_registry.tsv")
    require(
        historical_fields == [
            "path", "frozen_at_commit", "git_blob_sha1", "blob_sha256", "size_bytes",
            "evidence_role", "live_path_mutable", "frozen_blob_mutable",
        ],
        "historical registry schema drift",
    )
    require(len(historical) == 27, "historical registry row count drift")
    require(all(row["frozen_at_commit"] == EXECUTION_START_HEAD for row in historical), "historical commit drift")
    require(all(row["live_path_mutable"] == "1" and row["frozen_blob_mutable"] == "0" for row in historical), "blob mutability contract drift")

    exclusion_fields, exclusions = read_tsv(PAPER / "fresh_input_exclusion_registry.tsv")
    require(exclusion_fields[-5:] == ["assembly", "coordinate_namespace", "pair_digest", "source_receipt_path", "exclusion_reason"], "exclusion registry schema drift")
    require(len(exclusions) == 1455, "exclusion registry row count drift")
    reasons = {reason for row in exclusions for reason in row["exclusion_reason"].split(";")}
    require(
        {
            "historical_development_or_paper_workload",
            "historical_development_lncRNA",
            "phase2_correctness_holdout",
            "phase2_traceback_replay",
            "phase3_v1_fixed_pilot",
            "canonical_hybrid_v2_regression",
            "canonical_hybrid_v2_fresh_holdout",
            "canonical_hybrid_v2_performance_pilot",
            "phase3_v1_preregistered_application_universe",
            "ssw_cuda_differential_corpus_tiny_exhaustive",
            "ssw_cuda_differential_corpus_adversarial",
            "ssw_cuda_differential_corpus_deterministic_fuzz",
        } <= reasons,
        "fresh exclusion classes are incomplete",
    )
    require(
        sum(row["exclusion_reason"] == "phase3_v1_preregistered_application_universe" for row in exclusions) == 718,
        "the complete historical 50-query/668-target application universe is not excluded",
    )


def check_phase0_receipts() -> None:
    start = load_json(PAPER / "phase_0_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 0, "Phase 0 start receipt schema drift")
    require(start["execution_start_head"] == EXECUTION_START_HEAD, "Phase 0 start HEAD drift")
    require(start["execution_branch"] == EXECUTION_BRANCH, "Phase 0 branch drift")
    require(start["protocol_source_sha256"] == PROTOCOL_SHA256, "protocol source digest drift")
    require(start["clean_start_check"] == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""}, "clean-start evidence drift")
    require(start["previous_phase_commit"] is None and start["previous_phase_number"] is None, "Phase 0 cannot claim a previous phase")
    require(sha256_file(ROOT / "goal-biological-topk.md") == PROTOCOL_SHA256, "repository protocol digest drift")

    epoch = load_json(PAPER / "epoch_receipt.json")
    require(epoch["execution_start_head"] == EXECUTION_START_HEAD, "epoch HEAD drift")
    require(epoch["protocol_source_sha256"] == PROTOCOL_SHA256, "epoch protocol digest drift")
    require(epoch["new_scientific_run_started"] is False, "Phase 0 started a scientific run")
    require(epoch["historical_blob_registry"]["sha256"] == sha256_file(PAPER / "historical_blob_registry.tsv"), "epoch historical registry digest drift")
    require(epoch["fresh_input_exclusion_registry"]["sha256"] == sha256_file(PAPER / "fresh_input_exclusion_registry.tsv"), "epoch exclusion digest drift")
    checks = {row["check_id"]: row for row in epoch["historical_checks"]}
    require(checks["bioinformatics_phase0"]["exit_code"] == 2, "historical paper runtime guard result drift")
    require(checks["bioinformatics_phase0"]["classification"] == "expected_historical_runtime_epoch_guard", "paper guard classification drift")
    for check_id in ("canonical_hybrid_v2_runtime", "canonical_hybrid_v2_regression", "canonical_hybrid_v2_holdout", "canonical_hybrid_v2_performance", "ssw_cuda_aggregate"):
        require(checks[check_id]["exit_code"] == 0, f"historical check did not pass: {check_id}")

    fields, claims = read_tsv(PAPER / "claim_ledger.tsv")
    require(fields[0] == "claim_id" and len({row["claim_id"] for row in claims}) == len(claims), "claim ledger identity drift")
    by_id = {row["claim_id"]: row for row in claims}
    require(by_id["HIST_STRICT_CANONICAL_ROW_V1"]["status"] == "no_go", "strict-row no-go rewritten")
    require(by_id["HIST_SEQUENTIAL_VERIFIED_V1"]["status"] == "no_go", "sequential no-go rewritten")
    require(by_id["HIST_CANONICAL_HYBRID_V2_CORRECTNESS"]["status"] == "pass", "hybrid correctness drift")
    require(by_id["HIST_CANONICAL_HYBRID_V2_PERFORMANCE"]["status"] == "no_go", "hybrid performance no-go rewritten")
    require(by_id["HIST_38_32X"]["status"] == "historical_candidate_performance_anchor", "historical speedup promoted")


def check_phase0_state(state: dict[str, Any]) -> None:
    require(state["phase_status"]["0"] == "pass", "Phase 0 final state must be pass")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(1, 10)), "later phase advanced during Phase 0")
    require(state["active_phase"] == 1 and state["last_completed_phase"] == 0, "Phase 0 transition drift")
    require(state["last_decision"] == "phase_0_protocol_frozen", "Phase 0 decision drift")
    require(state["contract_status"] == "proposed", "Phase 0 promoted the contract")
    require(state["gpu_screen_status"] == "experimental", "Phase 0 promoted gpu-screen")
    require(state["bioinformatics_route"] == "conditionally_reopened", "Phase 0 route drift")
    require(state["score_representation"] == "pending_phase1", "Phase 0 pre-decided Score representation")


def check_precommit_receipt(phase: int, paths: list[str]) -> None:
    receipt = load_json(PAPER / f"phase_{phase}_precommit_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == phase, "precommit receipt schema drift")
    require(receipt["phase_start_parent_head"] == EXECUTION_START_HEAD if phase == 0 else True, "phase-start parent drift")
    require(receipt["expected_changed_paths"] == paths, "precommit path inventory drift")
    require(receipt["checker_command"] == ["python3", "scripts/check_biological_topk_phase.py", "--phase", str(phase), "--mode", "precommit"], "precommit checker command drift")
    require(receipt["checker_result"] == "pass", "precommit checker result is not pass")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "precommit receipt claims a future/self commit")
    for relative, digest in receipt["schema_evidence_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, f"precommit evidence digest drift: {relative}")


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
            "tests/biological_topk",
            "-p",
            "test_phase0.py",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase0(mode: str, state: dict[str, Any]) -> None:
    check_phase0_state(state)
    check_phase0_registries()
    check_phase0_receipts()
    check_historical_decisions()
    run_phase0_unit_tests()
    paths = allowlist(0)
    check_precommit_receipt(0, paths)

    if mode == "precommit":
        head = git("rev-parse", "HEAD")
        observed = changed_paths()
        if head == EXECUTION_START_HEAD:
            prospective = observed
        else:
            require(git("rev-parse", "HEAD^") == EXECUTION_START_HEAD, "Phase 0 amend parent drift")
            require(git("log", "-1", "--format=%s") == PHASE0_COMMIT_MESSAGE, "unexpected Phase 0 amend target")
            require(observed <= set(paths), "Phase 0 correction touched a path outside the allowlist")
            prospective = set(git("diff", "--name-only", "HEAD^").splitlines())
        require(prospective == set(paths), f"Phase 0 allowlisted diff mismatch: missing={sorted(set(paths)-prospective)} extra={sorted(prospective-set(paths))}")
    elif mode == "postcommit":
        require(not changed_paths(), "Phase 0 postcommit checker requires a clean tree")
        require(git("rev-parse", "HEAD^") == EXECUTION_START_HEAD, "Phase 0 commit parent drift")
        require(git("log", "-1", "--format=%s") == PHASE0_COMMIT_MESSAGE, "Phase 0 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
        require(committed == set(paths), "Phase 0 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported Phase 0 mode: {mode}")


def check_generic_phase(phase: int, mode: str, state: dict[str, Any]) -> None:
    paths = allowlist(phase)
    check_precommit_receipt(phase, paths)
    start = load_json(PAPER / f"phase_{phase}_start_receipt.json")
    require(start["previous_phase_number"] == phase - 1, "previous phase number drift")
    require(re.fullmatch(r"[0-9a-f]{40}", start["previous_phase_commit"]) is not None, "previous phase commit missing")
    require(git("merge-base", "--is-ancestor", start["previous_phase_commit"], "HEAD") == "", "previous phase commit is not an ancestor")
    if mode == "precommit":
        require(changed_paths() == set(paths), f"Phase {phase} allowlisted diff mismatch")
    else:
        require(not changed_paths(), f"Phase {phase} read-only mode requires a clean tree")
    require(state["phase_status"][str(phase)] != "pending", f"Phase {phase} has no auditable state")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, choices=range(10), required=True)
    parser.add_argument(
        "--mode",
        choices=("precommit", "postcommit", "audit-candidate", "certification", "post-certification"),
        required=True,
    )
    args = parser.parse_args()
    before = git_bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
    state = validate_program_state()
    require(git("branch", "--show-current") == EXECUTION_BRANCH, "execution branch drift")
    if args.phase == 0:
        check_phase0(args.mode, state)
    else:
        check_generic_phase(args.phase, args.mode, state)
    after = git_bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
    require(before == after, "checker modified the working tree")
    print(f"biological Top-K Phase {args.phase} {args.mode} checks OK")
    print(f"contract_status={state['contract_status']}")
    print(f"gpu_screen_status={state['gpu_screen_status']}")
    print(f"bioinformatics_route={state['bioinformatics_route']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as error:
        print(f"biological Top-K check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
