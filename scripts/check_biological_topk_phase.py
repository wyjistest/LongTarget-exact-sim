#!/usr/bin/env python3
"""Normative checker for biological Top-K phases 0 through 9."""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import Decimal
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
PHASE0_COMMIT = "3e642db8d93fc253972104e6072e2715f52ccb19"
PHASE1_COMMIT_MESSAGE = "repro: freeze candidate-site contract, source universe, and statistical gates"
PHASE1_COMMIT = "0daed2c4e1f181d3ce67ecba52db314a1798146e"
PHASE2_COMMIT_MESSAGE = "test: freeze clustered TFO candidate-site comparator regression"
PHASE2_COMMIT = "4d89d1cd989f50a42e7e3af56333c39219ba1803"
PHASE3_COMMIT_MESSAGE = "repro: freeze fresh clustered TFO candidate-site holdout"
PHASE3_COMMIT = "ca6410c1fc986e91fd855a43ed71dfeb5940f68f"
PHASE4_COMMIT_MESSAGE = "bench: freeze fresh candidate-site concordance decision"
PHASE4_RUNNER_SHA256 = "82d88b6687b5ad67e7f8c5e3e58f276bd31b2a042f6872f9289e11566d3f0d2b"
PHASE4_ANALYZER_SHA256 = "05f68a62727d342b3abf168f3d892cb430763031351e7c21ca62f49b1c396cbe"
PHASE4_ORIGINAL_ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout"
PHASE4_REPAIR_ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk/fresh-holdout-repair1"
PHASE4_REPAIR_RESERVATION_BYTES = 1536 * 1024**2
PHASE4_STORAGE_QUOTA_BYTES = 8 * 1024**3
PHASE4_OUTPUTS = (
    "paper/biological_topk/fresh_holdout_actual_resources.json",
    "paper/biological_topk/fresh_holdout_decision.json",
    "paper/biological_topk/fresh_holdout_receipt.json",
    "paper/biological_topk/source_data/fresh_candidate_matches.tsv",
    "paper/biological_topk/source_data/fresh_empty_workloads.tsv",
    "paper/biological_topk/source_data/fresh_exact_binomial_bounds.tsv",
    "paper/biological_topk/source_data/fresh_failure_ledger.tsv",
    "paper/biological_topk/source_data/fresh_rank_diagnostics.tsv",
    "paper/biological_topk/source_data/fresh_workload_metrics.tsv",
)
PHASE3_COMPONENTS = (
    "reproduce/biological_topk/freeze_fresh_holdout.py",
    "reproduce/biological_topk/run_fresh_holdout.py",
    "reproduce/biological_topk/analyze_fresh_holdout.py",
)
PHASE3_OUTPUTS = (
    "paper/biological_topk/fresh_holdout_plan.json",
    "paper/biological_topk/fresh_holdout_manifest.tsv",
    "paper/biological_topk/fresh_holdout_attempt_plan.tsv",
    "paper/biological_topk/fresh_holdout_manifest.sha256",
    "paper/biological_topk/fresh_holdout_resource_projection.json",
    "paper/biological_topk/fresh_holdout_resource_decision.json",
)
PHASE2_COMPONENTS = (
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/biological_topk/match_candidate_sites.py",
    "reproduce/biological_topk/compare_candidate_topk.py",
    "reproduce/biological_topk/exact_binomial_bounds.py",
    "reproduce/biological_topk/rank_diagnostics.py",
)
PHASE1_BUILDERS = (
    "reproduce/biological_topk/build_contract_artifacts.py",
    "reproduce/biological_topk/build_source_universe.py",
    "reproduce/biological_topk/build_information_plan.py",
    "reproduce/biological_topk/build_resource_model.py",
    "reproduce/biological_topk/build_feasibility_plan.py",
)
PHASE1_DOCS = (
    "docs/biological_topk/scientific_object.md",
    "docs/biological_topk/legacy_clustering_semantics.md",
    "docs/biological_topk/coordinate_mapping.md",
    "docs/biological_topk/coordinate_mapping_table.tsv",
    "docs/biological_topk/canonicalization_spec.md",
    "docs/biological_topk/ranking_semantics.md",
    "docs/biological_topk/matching_spec.md",
    "docs/biological_topk/statistical_analysis_plan.md",
    "docs/biological_topk/source_universe_spec.md",
    "docs/biological_topk/experimental_estimand_spec.md",
    "docs/biological_topk/operating_envelope.md",
)

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


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def directory_bytes(path: Path) -> int:
    require(path.is_dir() and not path.is_symlink(), f"missing or unsafe directory: {path}")
    total = 0
    for child in path.rglob("*"):
        require(not child.is_symlink(), f"artifact tree contains a symlink: {child}")
        if child.is_file():
            total += child.stat().st_size
    return total


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
        require(state["active_phase"] is None, "terminal blocking state requires active_phase=null")
        require(state["last_completed_phase"] == first, "terminal blocking phase completion drift")
        if statuses[str(first)].startswith("blocked_"):
            require(state["last_decision"] == statuses[str(first)], "blocked decision/status drift")
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


def load_json_from_commit(commit: str, relative: str) -> Any:
    try:
        return json.loads(git_bytes("show", f"{commit}:{relative}").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckError(f"invalid committed JSON {commit}:{relative}: {error}") from error


def allowlist_from_commit(phase: int, commit: str) -> list[str]:
    relative = f"paper/biological_topk/phase_{phase}_change_allowlist.txt"
    rows = [
        line.strip()
        for line in git_bytes("show", f"{commit}:{relative}").decode("utf-8").splitlines()
        if line.strip()
    ]
    require(rows == sorted(set(rows)), f"committed Phase {phase} allowlist drift")
    return rows


def phase_commit_for_postcommit(phase: int) -> str:
    next_receipt = PAPER / f"phase_{phase + 1}_start_receipt.json"
    if phase < 9 and next_receipt.is_file():
        receipt = load_json(next_receipt)
        commit = receipt.get("previous_phase_commit")
        require(
            isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
            f"Phase {phase + 1} start receipt does not identify Phase {phase} commit",
        )
        return commit
    return git("rev-parse", "HEAD")


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


def check_precommit_receipt(
    phase: int,
    paths: list[str],
    *,
    committed_at: str | None = None,
) -> None:
    relative = f"paper/biological_topk/phase_{phase}_precommit_receipt.json"
    receipt = (
        load_json_from_commit(committed_at, relative)
        if committed_at is not None
        else load_json(ROOT / relative)
    )
    require(receipt["schema_version"] == 1 and receipt["phase"] == phase, "precommit receipt schema drift")
    require(receipt["phase_start_parent_head"] == EXECUTION_START_HEAD if phase == 0 else True, "phase-start parent drift")
    require(receipt["expected_changed_paths"] == paths, "precommit path inventory drift")
    require(receipt["checker_command"] == ["python3", "scripts/check_biological_topk_phase.py", "--phase", str(phase), "--mode", "precommit"], "precommit checker command drift")
    require(receipt["checker_result"] == "pass", "precommit checker result is not pass")
    require("commit_sha" not in receipt and "phase_commit" not in receipt, "precommit receipt claims a future/self commit")
    for relative, digest in receipt["schema_evidence_sha256"].items():
        observed = (
            sha256_bytes(git_bytes("show", f"{committed_at}:{relative}"))
            if committed_at is not None
            else sha256_file(ROOT / relative)
        )
        require(observed == digest, f"precommit evidence digest drift: {relative}")


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
    phase_commit = phase_commit_for_postcommit(0) if mode == "postcommit" else None
    checked_state = (
        load_json_from_commit(phase_commit, "paper/biological_topk/PROGRAM_STATE.json")
        if phase_commit is not None
        else state
    )
    check_phase0_state(checked_state)
    check_phase0_registries()
    check_phase0_receipts()
    check_historical_decisions()
    run_phase0_unit_tests()
    paths = allowlist_from_commit(0, phase_commit) if phase_commit is not None else allowlist(0)
    check_precommit_receipt(0, paths, committed_at=phase_commit)

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
        require(phase_commit is not None, "Phase 0 postcommit identity missing")
        require(git("merge-base", "--is-ancestor", phase_commit, "HEAD") == "", "Phase 0 commit is not an ancestor")
        require(git("rev-parse", f"{phase_commit}^") == EXECUTION_START_HEAD, "Phase 0 commit parent drift")
        require(git("log", "-1", "--format=%s", phase_commit) == PHASE0_COMMIT_MESSAGE, "Phase 0 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", phase_commit).splitlines())
        require(committed == set(paths), "Phase 0 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported Phase 0 mode: {mode}")


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
            "tests/biological_topk",
            "-p",
            "test_phase1_contract.py",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase1_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    for script in PHASE1_BUILDERS:
        completed = run((sys.executable, script, "--check"), check=False, env=environment)
        require(
            completed.returncode == 0,
            completed.stderr.decode("utf-8", errors="replace")
            or f"Phase 1 builder check failed: {script}",
        )


def check_phase1_start_receipt() -> None:
    start = load_json(PAPER / "phase_1_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 1, "Phase 1 start receipt schema drift")
    require(start["status"] == "pass", "Phase 1 clean-start check did not pass")
    require(start["phase_start_parent_head"] == PHASE0_COMMIT, "Phase 1 parent HEAD drift")
    require(start["previous_phase_number"] == 0, "Phase 1 previous phase number drift")
    require(start["previous_phase_commit"] == PHASE0_COMMIT, "Phase 1 previous commit drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_phase.py", "--phase", "0", "--mode", "postcommit"],
        "Phase 1 previous postcommit command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "Phase 0 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "Phase 1 clean-start evidence drift",
    )


def check_phase1_evidence() -> dict[str, Any]:
    require(sha256_file(ROOT / "goal-biological-topk.md") == PROTOCOL_SHA256, "protocol digest drift")
    for relative in PHASE1_DOCS:
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing Phase 1 specification: {relative}")

    contract_schema = load_json(ROOT / "schemas/biological_topk_contract.schema.json")
    contract = load_json(PAPER / "contract_spec.json")
    validate_schema(contract, contract_schema)
    require(contract["schema_version"] == 2, "contract schema version drift")
    require(contract["coordinate_mapping_table_sha256"] == sha256_file(ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"), "coordinate table digest drift")

    mapping_fields, mapping_rows = read_tsv(ROOT / "docs/biological_topk/coordinate_mapping_table.tsv")
    require(len(mapping_fields) == 13 and len(mapping_rows) == 8, "coordinate mapping table shape drift")
    require(
        {(row["strand_label"], row["direction_label"]) for row in mapping_rows}
        == {(strand, direction) for strand in ("ParaPlus", "ParaMinus", "AntiPlus", "AntiMinus") for direction in ("R", "L")},
        "coordinate mapping combinations are incomplete",
    )
    require(sum(row["status"] == "reachable_current_fast_path" for row in mapping_rows) == 4, "reachable coordinate count drift")
    require(sum(row["status"] == "unreachable_by_current_runtime" for row in mapping_rows) == 4, "unreachable coordinate count drift")

    power = load_json(PAPER / "concordance_power_plan.json")
    require((power["n_binary_required"], power["k_min"], power["allowed_failures"]) == (124, 122, 2), "power boundary drift")
    joint = load_json(PAPER / "joint_information_simulation.json")
    require(joint["joint_information_gate_pass"] is True, "joint information gate failed")
    require(joint["joint_inner_mc_precision_pass"] is True, "joint MC precision failed")
    require(len(joint["outer_q_distribution"]) == 2000, "outer bootstrap count drift")
    require(joint["inner_simulations_are_independent_scientific_evidence"] is False, "inner simulations misclassified")

    source = load_json(PAPER / "source_universe_receipt.json")
    require(source["fresh_pair_selected"] is False and source["new_prediction_run"] is False, "source freeze selected or ran a fresh pair")
    for key in ("query_source_universe.tsv.gz", "target_source_universe.tsv.gz"):
        require((PAPER / key).read_bytes()[4:8] == b"\0\0\0\0", f"nondeterministic gzip mtime: {key}")
    with gzip.open(PAPER / "query_source_universe.tsv.gz", "rt", newline="", encoding="utf-8") as handle:
        query_rows = [row for row in csv.DictReader(handle, delimiter="\t") if row["historical_exclusion_status"] == "fresh_eligible"]
    require(len({row["sequence_sha256"] for row in query_rows}) >= 178, "fresh unique query capacity failed")

    score = load_json(PAPER / "score_integrality_decision.json")
    require(score["decision"] in {"integral_exact", "decimal_exact"}, "invalid score decision")
    require(score["decision"] == "integral_exact" and score["nonintegral_row_count"] == 0, "score audit decision drift")

    feasibility = load_json(PAPER / "fresh_information_feasibility.json")
    sample = load_json(PAPER / "sample_size_plan.json")
    budget = load_json(PAPER / "fresh_budget_projection_plan.json")
    approval = load_json(PAPER / "owner_storage_quota_approval.json")
    require(sample["N_panel"] == 178 and sample["source_capacity_gate_pass"] is True, "sample/source plan drift")
    require(feasibility["gates"]["all_computable_gates_pass"] is True, "a computable feasibility gate failed")
    require(feasibility["phase_1_status_recommendation"] in PHASE_STATUSES, "invalid Phase 1 recommendation")
    require(feasibility["fresh_pair_selected"] is False and feasibility["new_prediction_run"] is False, "fresh work occurred during Phase 1")
    require(budget["fresh_pair_selected"] is False and budget["new_prediction_run"] is False, "resource planning ran fresh predictions")
    require(approval["max_artifact_storage_bytes"] == 8589934592, "owner storage quota drift")
    require(approval["phase_1_commit_replacement_authorized"] is True, "Phase 1 replacement lacks owner authorization")
    require(approval["quota_may_be_raised_after_manifest_projection"] is False, "owner quota mutability drift")
    require(budget["storage_quota_source"] == "paper/biological_topk/owner_storage_quota_approval.json", "budget quota source drift")
    require(budget["storage_quota_source_sha256"] == sha256_file(PAPER / "owner_storage_quota_approval.json"), "budget quota receipt digest drift")
    require(load_json(PAPER / "experimental_power_simulation_plan.json")["status"] == "preregistered_before_dataset_inventory_and_predictions", "experimental plan status drift")
    require(load_json(PAPER / "operating_envelope.json")["hardware_generality_claim"] == "single_gpu_generation_RTX4090_only", "hardware claim drift")
    return feasibility


def check_phase1_state(state: dict[str, Any], feasibility: dict[str, Any]) -> None:
    expected_status = feasibility["phase_1_status_recommendation"]
    require(state["phase_status"]["0"] == "pass", "Phase 0 state drift")
    require(state["phase_status"]["1"] == expected_status, "Phase 1 state does not match feasibility evidence")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(2, 10)), "later phase advanced during Phase 1")
    require(state["previous_phase_commit"] == PHASE0_COMMIT, "PROGRAM_STATE previous commit drift")
    require(state["score_representation"] == "integral_exact", "PROGRAM_STATE score representation drift")
    require(state["rank_order_claim"] == "diagnostic_only", "rank-order claim drift")
    require(state["gpu_screen_status"] == "experimental", "Phase 1 promoted gpu-screen")
    require(state["bioinformatics_route"] == "conditionally_reopened", "Phase 1 route drift")
    if expected_status == "pass":
        require(feasibility["gates"]["all_required_gates_pass"] is True, "Phase 1 pass lacks all gates")
        require(state["active_phase"] == 2, "Phase 1 pass must authorize Phase 2")
        require(state["last_completed_phase"] == 1, "Phase 1 completion drift")
        require(state["last_decision"] == "phase_1_contract_frozen", "Phase 1 pass decision drift")
        require(state["contract_status"] == "in_validation", "Phase 1 pass contract state drift")
    else:
        require(expected_status.startswith("blocked_") or expected_status == "no_go", "unsupported Phase 1 terminal status")
        require(state["active_phase"] is None, "blocked Phase 1 must terminate the epoch")
        require(state["last_completed_phase"] == 1, "blocked Phase 1 completion drift")
        require(state["last_decision"] == expected_status, "blocked Phase 1 decision drift")
        require(state["contract_status"] == "proposed", "blocked Phase 1 cannot promote the contract")


def check_phase1(mode: str, current_state: dict[str, Any]) -> None:
    check_phase1_start_receipt()
    check_phase1_reproduction()
    feasibility = check_phase1_evidence()
    run_phase1_unit_tests()
    if mode == "precommit":
        state = current_state
        paths = allowlist(1)
        check_precommit_receipt(1, paths)
        check_phase1_state(state, feasibility)
        head = git("rev-parse", "HEAD")
        if head == PHASE0_COMMIT:
            prospective = changed_paths()
        else:
            require(git("rev-parse", "HEAD^") == PHASE0_COMMIT, "Phase 1 amend parent drift")
            require(git("log", "-1", "--format=%s") == PHASE1_COMMIT_MESSAGE, "unexpected Phase 1 amend target")
            require(changed_paths() <= set(paths), "Phase 1 correction touched a path outside the allowlist")
            prospective = set(git("diff", "--name-only", "HEAD^").splitlines())
        require(prospective == set(paths), "Phase 1 allowlisted diff mismatch")
    elif mode == "postcommit":
        require(not changed_paths(), "Phase 1 postcommit checker requires a clean tree")
        commit = phase_commit_for_postcommit(1)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "Phase 1 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk/PROGRAM_STATE.json")
        paths = allowlist_from_commit(1, commit)
        check_precommit_receipt(1, paths, committed_at=commit)
        check_phase1_state(state, feasibility)
        require(git("rev-parse", f"{commit}^") == PHASE0_COMMIT, "Phase 1 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE1_COMMIT_MESSAGE, "Phase 1 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "Phase 1 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported Phase 1 mode: {mode}")


def check_phase2_start_receipt() -> None:
    start = load_json(PAPER / "phase_2_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 2, "Phase 2 start receipt drift")
    require(start["phase_start_parent_head"] == PHASE1_COMMIT, "Phase 2 parent HEAD drift")
    require(start["previous_phase_number"] == 1, "Phase 2 previous phase drift")
    require(start["previous_phase_commit"] == PHASE1_COMMIT, "Phase 2 previous commit drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_phase.py", "--phase", "1", "--mode", "postcommit"],
        "Phase 2 previous postcommit command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "Phase 1 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "Phase 2 clean-start evidence drift",
    )
    require(start["status"] == "pass", "Phase 2 start receipt did not pass")


def run_phase2_unit_tests() -> None:
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
            "test_phase2_comparator.py",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase2_evidence() -> None:
    require(sha256_file(ROOT / "goal-biological-topk.md") == PROTOCOL_SHA256, "protocol digest drift")
    for relative in (*PHASE2_COMPONENTS, "reproduce/biological_topk/build_phase2_regression.py"):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing Phase 2 implementation: {relative}")

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    reproduction = run(
        (sys.executable, "reproduce/biological_topk/build_phase2_regression.py", "--check"),
        check=False,
        env=environment,
    )
    require(
        reproduction.returncode == 0,
        reproduction.stderr.decode("utf-8", errors="replace") or "Phase 2 regression does not reproduce",
    )

    receipt = load_json(PAPER / "phase2_regression_receipt.json")
    require(receipt["schema_version"] == 1 and receipt["phase"] == 2, "Phase 2 regression receipt drift")
    require(receipt["status"] == "pass", "Phase 2 regression receipt is not pass")
    require(receipt["evidence_role"] == "historical_regression_only", "Phase 2 evidence role drift")
    require(receipt["fresh_pair_selected"] is False, "Phase 2 selected a fresh pair")
    require(receipt["new_prediction_run"] is False, "Phase 2 ran a new prediction")
    require(receipt["independent_validation_claim"] is False, "historical regression claimed independence")
    require(receipt["comparison_count"] == 184, "Phase 2 comparison count drift")
    require(receipt["ranking_result_count"] == 552, "Phase 2 ranking result count drift")
    require(receipt["detail_count"] == 2391, "Phase 2 detail count drift")
    require(
        receipt["dataset_comparison_counts"]
        == {
            "canonical_hybrid_v2_former_fresh_60_regression_only": 60,
            "canonical_hybrid_v2_regression_36": 36,
            "historical_paper_core_available": 8,
            "historical_paper_generalization_available": 44,
            "phase2_holdout_36": 36,
        },
        "Phase 2 historical dataset coverage drift",
    )
    require(receipt["technical_failure_count"] == 0, "Phase 2 technical failure count is nonzero")
    require(receipt["input_identity_mismatch_count"] == 0, "Phase 2 input identity mismatch")
    require(receipt["ambiguous_matching_result_count"] == 0, "Phase 2 historical ambiguity")
    require(receipt["no_parser_or_comparator_technical_failures"] is True, "Phase 2 parser/comparator gate failed")
    require(receipt["all_regression_deterministic"] is True, "Phase 2 deterministic gate failed")

    manifest_fields, manifest = read_tsv(PAPER / "phase2_regression_manifest.tsv")
    result_fields, results = read_tsv(PAPER / "phase2_regression_results.tsv")
    detail_fields, details = read_tsv(PAPER / "phase2_regression_details.tsv")
    require(len(manifest) == 184 and len(results) == 552 and len(details) == 2391, "Phase 2 TSV shape drift")
    require(manifest_fields[0:5] == ["comparison_id", "dataset_class", "evidence_role", "workload_id", "repeat_id"], "Phase 2 manifest schema drift")
    require(result_fields[0:7] == ["comparison_id", "dataset_class", "workload_id", "repeat_id", "comparison_status", "technical_failure", "ranking_mode"], "Phase 2 result schema drift")
    require(detail_fields[0:5] == ["comparison_id", "dataset_class", "workload_id", "repeat_id", "ranking_mode"], "Phase 2 detail schema drift")
    require(len({row["comparison_id"] for row in manifest}) == 184, "duplicate Phase 2 comparison ID")
    require(all(row["evidence_role"] == "historical_regression_only" for row in manifest), "nonhistorical Phase 2 row")
    require(all(row["technical_failure"] == "0" for row in results), "technical result retained as clean")
    require({row["ranking_mode"] for row in results} == {"score", "stability", "nt"}, "ranking coverage drift")
    require(receipt["manifest_sha256"] == sha256_file(PAPER / "phase2_regression_manifest.tsv"), "Phase 2 manifest digest drift")
    require(receipt["results_sha256"] == sha256_file(PAPER / "phase2_regression_results.tsv"), "Phase 2 results digest drift")
    require(receipt["details_sha256"] == sha256_file(PAPER / "phase2_regression_details.tsv"), "Phase 2 details digest drift")

    known = load_json(PAPER / "phase2_known_cases.json")
    require(known["implementation_has_workload_id_special_cases"] is False, "known-case special case declared")
    require(
        known["hq10_ht02"]["strict_row_diagnostic"] == "mismatch"
        and known["hq10_ht02"]["unique_candidate_site_match"] is True
        and known["hq10_ht02"]["set_membership"] == "preserved",
        "hq10 known case drift",
    )
    require(
        known["hq11_ht02"]["strict_row_diagnostic"] == "mismatch"
        and known["hq11_ht02"]["target_reciprocal_overlap"] == "62/65"
        and known["hq11_ht02"]["unique_candidate_site_match"] is True
        and known["hq11_ht02"]["set_membership"] == "preserved",
        "hq11 known case drift",
    )
    for relative in (
        "reproduce/biological_topk/canonicalize_rows.py",
        "reproduce/biological_topk/recluster_candidate_sites.py",
        "reproduce/biological_topk/match_candidate_sites.py",
        "reproduce/biological_topk/compare_candidate_topk.py",
    ):
        implementation = (ROOT / relative).read_text(encoding="utf-8").lower()
        require("hq10" not in implementation and "hq11" not in implementation, f"workload special case in {relative}")

    freeze = load_json(PAPER / "phase2_comparator_freeze.json")
    require(freeze["source_commit"] == PHASE1_COMMIT, "Phase 2 comparator source commit drift")
    require(freeze["python_version"] == platform.python_version(), "Phase 2 Python version drift")
    require(freeze["default_fail_closed"] is True, "Phase 2 comparator is not fail closed by default")
    require(freeze["independent_validation_claim"] is False, "Phase 2 freeze claims independence")
    require(freeze["contract_module_sha256"] == sha256_file(ROOT / "reproduce/biological_topk/contract.py"), "Phase 2 contract module digest drift")
    require(freeze["contract_spec_sha256"] == sha256_file(PAPER / "contract_spec.json"), "Phase 2 contract spec digest drift")
    require(freeze["coordinate_mapping_sha256"] == sha256_file(ROOT / "docs/biological_topk/coordinate_mapping_table.tsv"), "Phase 2 coordinate mapping digest drift")
    require(freeze["expected_regression_digest"] == receipt["results_sha256"], "expected regression digest drift")
    require(freeze["known_cases_sha256"] == sha256_file(PAPER / "phase2_known_cases.json"), "known-case digest drift")
    require(
        freeze["component_sha256"]
        == {relative: sha256_file(ROOT / relative) for relative in PHASE2_COMPONENTS},
        "Phase 2 component digest drift",
    )
    require(
        freeze["comparator_sha256"]
        == sha256_file(ROOT / "reproduce/biological_topk/compare_candidate_topk.py"),
        "Phase 2 comparator digest drift",
    )

    help_result = run(
        (sys.executable, "reproduce/biological_topk/compare_candidate_topk.py", "--help"),
        check=False,
        env=environment,
    )
    help_text = help_result.stdout.decode("utf-8", errors="replace")
    require(help_result.returncode == 0, "Phase 2 comparator --help failed")
    for option in (
        "--authority",
        "--candidate",
        "--authority-receipt",
        "--candidate-receipt",
        "--contract-spec",
        "--output-json",
        "--details-tsv",
        "--fail-closed",
    ):
        require(option in help_text, f"Phase 2 comparator CLI missing {option}")


def check_phase2_state(state: dict[str, Any]) -> None:
    require(state["phase_status"]["0"] == state["phase_status"]["1"] == "pass", "Phase 2 prerequisite state drift")
    require(state["phase_status"]["2"] == "pass", "Phase 2 final state must be pass")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(3, 10)), "later phase advanced during Phase 2")
    require(state["active_phase"] == 3 and state["last_completed_phase"] == 2, "Phase 2 transition drift")
    require(state["last_decision"] == "phase_2_regression_frozen", "Phase 2 decision drift")
    require(state["previous_phase_commit"] == PHASE1_COMMIT, "Phase 2 previous commit state drift")
    require(state["contract_status"] == "in_validation", "Phase 2 promoted the contract")
    require(state["gpu_screen_status"] == "experimental", "Phase 2 promoted gpu-screen")
    require(state["bioinformatics_route"] == "conditionally_reopened", "Phase 2 route drift")
    require(state["rank_order_claim"] == "diagnostic_only", "Phase 2 promoted rank order")


def check_phase2(mode: str, current_state: dict[str, Any]) -> None:
    check_phase2_start_receipt()
    check_phase2_evidence()
    run_phase2_unit_tests()
    if mode == "precommit":
        paths = allowlist(2)
        check_precommit_receipt(2, paths)
        check_phase2_state(current_state)
        require(git("rev-parse", "HEAD") == PHASE1_COMMIT, "Phase 2 precommit parent drift")
        require(changed_paths() == set(paths), "Phase 2 allowlisted diff mismatch")
    elif mode == "postcommit":
        require(not changed_paths(), "Phase 2 postcommit checker requires a clean tree")
        commit = phase_commit_for_postcommit(2)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "Phase 2 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk/PROGRAM_STATE.json")
        paths = allowlist_from_commit(2, commit)
        check_precommit_receipt(2, paths, committed_at=commit)
        check_phase2_state(state)
        require(git("rev-parse", f"{commit}^") == PHASE1_COMMIT, "Phase 2 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE2_COMMIT_MESSAGE, "Phase 2 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "Phase 2 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported Phase 2 mode: {mode}")


def check_phase3_start_receipt() -> None:
    start = load_json(PAPER / "phase_3_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 3, "Phase 3 start receipt drift")
    require(start["phase_start_parent_head"] == PHASE2_COMMIT, "Phase 3 parent HEAD drift")
    require(start["previous_phase_number"] == 2, "Phase 3 previous phase drift")
    require(start["previous_phase_commit"] == PHASE2_COMMIT, "Phase 3 previous commit drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_phase.py", "--phase", "2", "--mode", "postcommit"],
        "Phase 3 previous postcommit command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "Phase 2 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "Phase 3 clean-start evidence drift",
    )
    require(start["status"] == "pass", "Phase 3 start receipt did not pass")


def run_phase3_unit_tests() -> None:
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
            "test_phase3_holdout.py",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase3_reproduction() -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = run(
        (sys.executable, "reproduce/biological_topk/freeze_fresh_holdout.py", "--check"),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase3_evidence() -> None:
    for relative in (*PHASE3_COMPONENTS, *PHASE3_OUTPUTS):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 3 artifact: {relative}")
    require(sha256_file(ROOT / "goal-biological-topk.md") == PROTOCOL_SHA256, "protocol file drift")
    check_phase3_reproduction()

    manifest_fields, manifest = read_tsv(PAPER / "fresh_holdout_manifest.tsv")
    expected_manifest_fields = (
        "workload_id", "evidence_role", "primary_unit", "query_length_stratum",
        "target_scale_stratum", "query_ordinal_namespace", "query_source_ordinal",
        "query_transcript_id", "query_gene_id", "query_source_path",
        "query_extraction_recipe_id", "query_extracted_start0", "query_extracted_end0",
        "query_sequence_length", "query_sequence_sha256", "query_gc_fraction",
        "query_complexity_proxy", "query_gc_quartile", "query_complexity_quartile",
        "target_ordinal_namespace", "target_source_ordinal", "target_source_path",
        "target_extraction_recipe_id", "target_chromosome", "target_anchor_strand",
        "target_anchor_transcript_id", "target_anchor_gene_id", "target_region_start0",
        "target_region_end0", "target_sequence_length", "target_sequence_sha256",
        "target_gc_fraction", "target_complexity_proxy", "target_gc_quartile",
        "target_complexity_quartile", "assembly", "target_coordinate_namespace",
        "parameter_bundle_sha256", "input_pair_digest", "selection_hash",
        "technical_repeat_count", "status",
    )
    require(tuple(manifest_fields) == expected_manifest_fields, "Phase 3 manifest schema drift")
    require(len(manifest) == 178, "Phase 3 panel size drift")
    quotas = Counter({"short": 60, "medium": 59, "large": 59})
    require(Counter(row["query_length_stratum"] for row in manifest) == quotas, "query length quotas drift")
    require(Counter(row["target_scale_stratum"] for row in manifest) == quotas, "target scale quotas drift")
    expected_matrix = Counter(
        {
            ("short", "short"): 20, ("short", "medium"): 20, ("short", "large"): 20,
            ("medium", "short"): 20, ("medium", "medium"): 20, ("medium", "large"): 19,
            ("large", "short"): 20, ("large", "medium"): 19, ("large", "large"): 20,
        }
    )
    require(
        Counter((row["query_length_stratum"], row["target_scale_stratum"]) for row in manifest)
        == expected_matrix,
        "query/target pairing matrix drift",
    )
    for field in ("workload_id", "query_sequence_sha256", "target_sequence_sha256", "input_pair_digest"):
        require(len({row[field] for row in manifest}) == 178, f"Phase 3 {field} is not unique")
    require(
        len({(row["query_ordinal_namespace"], row["query_source_ordinal"]) for row in manifest}) == 178,
        "query namespaced ordinals are not unique",
    )
    require(
        len({(row["target_ordinal_namespace"], row["target_source_ordinal"]) for row in manifest}) == 178,
        "target namespaced ordinals are not unique",
    )
    require(
        Counter(row["target_scale_stratum"] for row in manifest if row["technical_repeat_count"] == "1")
        == Counter({"short": 2, "medium": 2, "large": 2}),
        "technical repeat selection drift",
    )
    checksum = (PAPER / "fresh_holdout_manifest.sha256").read_text(encoding="ascii").split()
    require(checksum == [sha256_file(PAPER / "fresh_holdout_manifest.tsv"), "fresh_holdout_manifest.tsv"], "manifest checksum drift")

    attempt_fields, attempts = read_tsv(PAPER / "fresh_holdout_attempt_plan.tsv")
    require(len(attempt_fields) == 46, "Phase 3 attempt-plan schema width drift")
    require(len(attempts) == 368, "Phase 3 attempt count drift")
    require(Counter(row["arm"] for row in attempts) == Counter({"A": 184, "G": 184}), "A/G attempt counts drift")
    by_validation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in attempts:
        by_validation[row["validation_instance_id"]].append(row)
    require(len(by_validation) == 184, "validation instance count drift")
    identity_fields = (
        "query_ordinal_namespace", "query_source_ordinal", "query_sequence_sha256",
        "target_ordinal_namespace", "target_source_ordinal", "target_sequence_sha256",
        "assembly", "target_coordinate_namespace", "query_extraction_recipe_id",
        "target_extraction_recipe_id", "input_pair_digest", "parameter_bundle_sha256",
    )
    pair_orders: Counter[str] = Counter()
    for validation_id, pair in by_validation.items():
        require(len(pair) == 2 and {row["arm"] for row in pair} == {"A", "G"}, f"A/G pair drift: {validation_id}")
        require(all(len({row[field] for row in pair}) == 1 for field in identity_fields), f"A/G identity drift: {validation_id}")
        require(sorted(int(row["arm_launch_order"]) for row in pair) == [1, 2], f"launch order drift: {validation_id}")
        require(len({row["artifact_root"] for row in pair}) == 2, f"arm artifact roots collide: {validation_id}")
        require(all(row["retry_policy"] == "none" for row in pair), f"retry policy drift: {validation_id}")
        require(all(row["comparison_policy"] == "offline_after_both_arms_terminal" for row in pair), f"comparison isolation drift: {validation_id}")
        pair_orders[pair[0]["pair_order"]] += 1
    require(pair_orders == Counter({"AG": 92, "GA": 92}), "balanced A/G order drift")

    authority_path = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86"
    candidate_path = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_gasal2"
    require(sha256_file(authority_path) == "75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e", "archived authority binary drift")
    require(sha256_file(candidate_path) == "ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9", "archived candidate binary drift")
    require({row["binary_path"] for row in attempts if row["arm"] == "A"} == {authority_path.relative_to(ROOT).as_posix()}, "authority binary path substitution")
    require({row["binary_path"] for row in attempts if row["arm"] == "G"} == {candidate_path.relative_to(ROOT).as_posix()}, "candidate binary path substitution")

    plan = load_json(PAPER / "fresh_holdout_plan.json")
    require(plan["status"] == "frozen_not_run" and plan["selection_kind"] == "input_only_static_source_metadata", "fresh holdout plan status drift")
    require(plan["prohibited_selection_fields_used"] == [], "prohibited output-side selection field used")
    require(plan["new_prediction_run"] is False and plan["scientific_output_created"] is False, "Phase 3 plan claims a scientific run")
    require(plan["N_panel"] == 178 and plan["validation_instance_count"] == 184 and plan["attempt_count"] == 368, "fresh plan counts drift")
    require(plan["exclusion_checks"]["hard_gate_pass"] is True, "fresh exclusion hard gate failed")
    require(all(value == 0 for key, value in plan["exclusion_checks"].items() if key.endswith("_overlap")), "fresh exclusion overlap detected")

    projection = load_json(PAPER / "fresh_holdout_resource_projection.json")
    require(projection["resource_model_sha256"] == "8fb81ff5de6c51015954e1891a8e5cf96001e6a7fdd182debee3b922c2672286", "resource model substitution")
    require(projection["primary_workload_count"] == 178, "resource primary count drift")
    require(projection["technical_repeat_instance_count"] == 6, "resource repeat count drift")
    require(projection["projected_validation_instance_count"] == 184, "resource instance count drift")
    require(projection["technical_repeats_included"] is True, "resource projection omitted technical repeats")
    decision = load_json(PAPER / "fresh_holdout_resource_decision.json")
    require(decision["status"] == "pass" and decision["fixed_budget_gate_pass"] is True, "manifest-specific resource decision failed")
    require(Decimal(decision["projected_scheduled_elapsed_wall_seconds_upper_95"]) <= Decimal(172800), "elapsed resource gate failed")
    require(Decimal(decision["projected_gpu_hours_upper_95"]) <= Decimal(72), "GPU-hour resource gate failed")
    require(int(decision["projected_artifact_storage_bytes_upper_95"]) <= 8589934592, "storage resource gate failed")
    require(decision["owner_quota_may_be_raised_after_manifest_projection"] is False, "post-manifest quota raise enabled")


def check_phase3_state(state: dict[str, Any]) -> None:
    require(all(state["phase_status"][str(index)] == "pass" for index in range(4)), "Phase 3 prerequisite/final state drift")
    require(all(state["phase_status"][str(index)] == "pending" for index in range(4, 10)), "later phase advanced during Phase 3")
    require(state["active_phase"] == 4 and state["last_completed_phase"] == 3, "Phase 3 transition drift")
    require(state["last_decision"] == "phase_3_holdout_frozen", "Phase 3 decision drift")
    require(state["previous_phase_commit"] == PHASE2_COMMIT, "Phase 3 previous commit state drift")
    require(state["contract_status"] == "in_validation", "Phase 3 promoted the contract")
    require(state["gpu_screen_status"] == "experimental", "Phase 3 promoted gpu-screen")
    require(state["bioinformatics_route"] == "conditionally_reopened", "Phase 3 route drift")
    require(state["rank_order_claim"] == "diagnostic_only", "Phase 3 promoted rank order")


def check_phase3(mode: str, current_state: dict[str, Any]) -> None:
    check_phase3_start_receipt()
    check_phase3_evidence()
    run_phase3_unit_tests()
    if mode == "precommit":
        paths = allowlist(3)
        check_precommit_receipt(3, paths)
        check_phase3_state(current_state)
        require(git("rev-parse", "HEAD") == PHASE2_COMMIT, "Phase 3 precommit parent drift")
        require(changed_paths() == set(paths), "Phase 3 allowlisted diff mismatch")
        require(not (ROOT / ".paper-artifacts/biological-topk/fresh-holdout").exists(), "scientific output exists before Phase 3 freeze commit")
    elif mode == "postcommit":
        require(not changed_paths(), "Phase 3 postcommit checker requires a clean tree")
        commit = phase_commit_for_postcommit(3)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "Phase 3 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk/PROGRAM_STATE.json")
        paths = allowlist_from_commit(3, commit)
        check_precommit_receipt(3, paths, committed_at=commit)
        check_phase3_state(state)
        require(git("rev-parse", f"{commit}^") == PHASE2_COMMIT, "Phase 3 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE3_COMMIT_MESSAGE, "Phase 3 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "Phase 3 committed paths differ from allowlist")
        if current_state["phase_status"]["4"] == "pending":
            require(not (ROOT / ".paper-artifacts/biological-topk/fresh-holdout").exists(), "scientific output predates Phase 4 activation")
    else:
        raise CheckError(f"unsupported Phase 3 mode: {mode}")


def check_phase4_start_receipt() -> None:
    start = load_json(PAPER / "phase_4_start_receipt.json")
    require(start["schema_version"] == 1 and start["phase"] == 4, "Phase 4 start receipt drift")
    require(start["phase_start_parent_head"] == PHASE3_COMMIT, "Phase 4 parent HEAD drift")
    require(start["previous_phase_number"] == 3, "Phase 4 previous phase drift")
    require(start["previous_phase_commit"] == PHASE3_COMMIT, "Phase 4 previous commit drift")
    require(
        start["previous_phase_postcommit_check_command"]
        == ["python3", "scripts/check_biological_topk_phase.py", "--phase", "3", "--mode", "postcommit"],
        "Phase 4 previous postcommit command drift",
    )
    require(start["previous_phase_postcommit_check_result"] == "pass", "Phase 3 postcommit result drift")
    require(
        start["clean_start_check"]
        == {"command": ["git", "status", "--porcelain=v1"], "exit_code": 0, "stderr": "", "stdout": ""},
        "Phase 4 clean-start evidence drift",
    )
    require(start["status"] == "pass", "Phase 4 start receipt did not pass")


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
            "tests/biological_topk",
            "-p",
            "test_phase4_concordance.py",
        ),
        check=False,
        env=environment,
    )
    require(completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace"))


def check_phase4_reproduction(decision: str) -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    plan_check = run(
        (sys.executable, "reproduce/biological_topk/run_fresh_holdout_repair1.py", "--check-plan"),
        check=False,
        env=environment,
    )
    require(plan_check.returncode == 0, plan_check.stderr.decode("utf-8", errors="replace"))
    if decision == "blocked_fixed_budget":
        command = (
            sys.executable,
            "reproduce/biological_topk/adjudicate_fresh_holdout_repair1_budget_stop.py",
            "--check",
            "--artifact-root",
            ".paper-artifacts/biological-topk/fresh-holdout-repair1",
        )
    else:
        command = (
            sys.executable,
            "reproduce/biological_topk/analyze_fresh_holdout_repair1.py",
            "--check",
            "--artifact-root",
            ".paper-artifacts/biological-topk/fresh-holdout-repair1",
        )
    analysis_check = run(command, check=False, env=environment)
    require(analysis_check.returncode == 0, analysis_check.stderr.decode("utf-8", errors="replace"))


def check_phase4_attempt_artifacts(row: dict[str, str]) -> dict[str, Any]:
    destination = ROOT / row["artifact_root"]
    require(destination.is_dir() and not destination.is_symlink(), f"missing attempt directory: {row['attempt_id']}")
    receipt = load_json(destination / "attempt-complete.json")
    require(receipt["attempt_id"] == row["attempt_id"], "attempt receipt identity drift")
    require(receipt["status"] == "success", f"repair attempt did not succeed: {row['attempt_id']}")
    require(receipt["source_commit"] == PHASE3_COMMIT, "attempt source commit drift")
    require(receipt["attempt_config_sha256"] == canonical_digest(row), "attempt config digest drift")
    require(receipt["comparison_started"] is False, "runner performed a comparison")
    require(receipt["retry_policy"] == "none", "attempt retry policy drift")
    require(receipt["replacement_retry_allowed"] is False, "replacement retry was enabled")
    require(receipt["binary_sha256"] == row["binary_sha256"], "attempt binary digest drift")

    manifest_path = destination / "artifact-manifest.tsv"
    checksum = (destination / "artifact-manifest.sha256").read_text(encoding="ascii").split()
    require(checksum == [sha256_file(manifest_path), manifest_path.name], "attempt manifest checksum drift")
    fields, manifest = read_tsv(manifest_path)
    require(fields == ["path", "size_bytes", "sha256"], "attempt artifact-manifest schema drift")
    require(len({item["path"] for item in manifest}) == len(manifest), "duplicate attempt artifact path")
    excluded = {"artifact-manifest.tsv", "artifact-manifest.sha256", "attempt-complete.json"}
    actual_paths = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file() and path.relative_to(destination).as_posix() not in excluded
    }
    require({item["path"] for item in manifest} == actual_paths, "attempt artifact inventory drift")
    observed: dict[str, tuple[int, str]] = {}
    for item in manifest:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "unsafe attempt artifact path")
        path = destination / relative
        require(path.is_file() and not path.is_symlink(), f"missing attempt artifact: {path}")
        size = path.stat().st_size
        digest = sha256_file(path)
        require(size == int(item["size_bytes"]), f"attempt artifact size drift: {path}")
        require(digest == item["sha256"], f"attempt artifact digest drift: {path}")
        observed[item["path"]] = (size, digest)

    output = destination / str(receipt["output_path"])
    input_receipt_path = destination / str(receipt["input_receipt_path"])
    require(output.is_file() and sha256_file(output) == receipt["output_sha256"], "attempt output drift")
    input_receipt = load_json(input_receipt_path)
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
        require(str(identity[receipt_field]) == row[plan_field], f"attempt input identity drift: {receipt_field}")

    if row["arm"] == "G":
        require(
            receipt["telemetry_storage_policy"] == "validate_raw_then_lossless_gzip_mtime0",
            "G telemetry storage policy drift",
        )
        require(not (destination / "telemetry.json").exists(), "raw G telemetry was not removed after compression")
        compressed_name = str(receipt["telemetry_compressed_path"])
        require(compressed_name == "attempt-telemetry.tsv.gz", "compressed telemetry path drift")
        compressed = destination / compressed_name
        require(compressed_name in observed, "compressed telemetry omitted from artifact manifest")
        require(
            observed[compressed_name]
            == (int(receipt["telemetry_compressed_size_bytes"]), receipt["telemetry_compressed_sha256"]),
            "compressed telemetry receipt drift",
        )
        with compressed.open("rb") as handle:
            header = handle.read(10)
        require(len(header) == 10 and header[:2] == b"\x1f\x8b", "invalid gzip telemetry header")
        require(header[4:8] == b"\x00\x00\x00\x00", "gzip telemetry mtime is not deterministic")
        raw_digest = hashlib.sha256()
        raw_size = 0
        with gzip.open(compressed, "rb") as decoded:
            for block in iter(lambda: decoded.read(1024 * 1024), b""):
                raw_digest.update(block)
                raw_size += len(block)
        require(raw_size == int(receipt["telemetry_uncompressed_size_bytes"]), "telemetry round-trip size drift")
        require(raw_digest.hexdigest() == receipt["telemetry_uncompressed_sha256"], "telemetry round-trip digest drift")
    else:
        require(not (destination / "telemetry.json").exists(), "A attempt contains G telemetry")
        require(not (destination / "attempt-telemetry.tsv.gz").exists(), "A attempt contains compressed G telemetry")
    return receipt


def check_phase4_freeze_and_incident() -> tuple[list[dict[str, str]], dict[str, Any]]:
    require(sha256_file(ROOT / "goal-biological-topk.md") == PROTOCOL_SHA256, "protocol file drift")
    require(
        sha256_file(ROOT / "reproduce/biological_topk/run_fresh_holdout_repair1.py")
        == PHASE4_RUNNER_SHA256,
        "Phase 4 repair runner drift",
    )
    require(
        sha256_file(ROOT / "reproduce/biological_topk/analyze_fresh_holdout_repair1.py")
        == PHASE4_ANALYZER_SHA256,
        "Phase 4 repair analyzer drift",
    )
    incident = load_json(PAPER / "fresh_holdout_infrastructure_incident.json")
    require(incident["schema_version"] == 1 and incident["phase"] == 4, "infrastructure incident schema drift")
    require(incident["status"] == "superseded_epoch_retained_repair1_authorized", "incident status drift")
    require(incident["terminal_attempt_count"] == 3, "superseded terminal-attempt count drift")
    require(incident["successful_attempt_count"] == 1, "superseded success count drift")
    require(incident["budget_stop_technical_failure_count"] == 2, "superseded failure count drift")
    require(incident["comparison_started"] is False, "superseded epoch started comparison")
    require(incident["automatic_retry_used"] is False, "superseded epoch used an automatic retry")
    require(incident["repair_epoch_authorized"] == incident["repair_epoch_limit"] == 1, "repair limit drift")
    require(incident["fixed_storage_quota_bytes"] == PHASE4_STORAGE_QUOTA_BYTES, "incident storage quota drift")
    require(directory_bytes(PHASE4_ORIGINAL_ARTIFACT_ROOT) == incident["superseded_artifact_bytes"], "superseded evidence size drift")
    require(
        sha256_file(ROOT / incident["run_summary_path"]) == incident["run_summary_sha256"],
        "superseded run-summary drift",
    )
    for item in incident["terminal_attempt_receipts"] + incident["large_candidate_telemetry_observations"]:
        path = ROOT / item["path"]
        require(path.stat().st_size == item.get("size_bytes", path.stat().st_size), "incident evidence size drift")
        require(sha256_file(path) == item["sha256"], "incident evidence digest drift")

    plan = load_json(PAPER / "fresh_holdout_repair1_plan.json")
    require(plan["repair_epoch"] == plan["repair_epoch_limit"] == 1, "repair plan epoch-limit drift")
    require(plan["full_panel_rerun"] is True and plan["original_evidence_retained"] is True, "repair rerun/retention drift")
    require(plan["planned_attempts"] == 368 and plan["planned_validation_instances"] == 184, "repair plan counts drift")
    require(plan["planned_primary_workloads"] == 178, "repair primary-workload count drift")
    require(plan["fixed_storage_quota_bytes"] == PHASE4_STORAGE_QUOTA_BYTES, "repair quota drift")
    require(plan["telemetry_raw_reservation_bytes"] == PHASE4_REPAIR_RESERVATION_BYTES, "repair reservation drift")
    require(plan["runner_sha256"] == PHASE4_RUNNER_SHA256, "repair-plan runner digest drift")
    require(plan["analyzer_sha256"] == PHASE4_ANALYZER_SHA256, "repair-plan analyzer digest drift")
    require(plan["scientific_input_changed"] is False, "repair changed scientific input")
    require(plan["scientific_contract_changed"] is False, "repair changed scientific contract")
    require(plan["runtime_binary_changed"] is False, "repair changed runtime binary")
    require(plan["panel_or_attempt_order_changed"] is False, "repair changed panel/order")

    original_fields, original = read_tsv(PAPER / "fresh_holdout_attempt_plan.tsv")
    repair_fields, attempts = read_tsv(PAPER / "fresh_holdout_repair1_attempt_plan.tsv")
    require(
        repair_fields
        == original_fields
        + ["supersedes_attempt_id", "repair_epoch", "repair_reason", "telemetry_storage_policy"],
        "repair attempt-plan schema drift",
    )
    require(len(original) == len(attempts) == 368, "repair attempt-plan count drift")
    checksum = (PAPER / "fresh_holdout_repair1_attempt_plan.sha256").read_text(encoding="ascii").split()
    require(
        checksum == [sha256_file(PAPER / "fresh_holdout_repair1_attempt_plan.tsv"), "fresh_holdout_repair1_attempt_plan.tsv"],
        "repair attempt-plan checksum drift",
    )
    identity_fields = (
        "execution_index", "workload_id", "repeat_id", "primary_instance", "independent_sample",
        "arm", "pair_order", "arm_launch_order", "worker_index", "query_ordinal_namespace",
        "query_source_ordinal", "query_sequence_sha256", "target_ordinal_namespace",
        "target_source_ordinal", "target_sequence_sha256", "assembly",
        "target_coordinate_namespace", "query_extraction_recipe_id", "target_extraction_recipe_id",
        "input_pair_digest", "parameter_bundle_sha256", "binary_path", "binary_sha256",
        "gpu_physical_index", "cpu_affinity", "timeout_seconds", "retry_policy", "comparison_policy",
    )
    for source, row in zip(original, attempts):
        require(row["attempt_id"] == f"r1_{source['attempt_id']}", "repair attempt ID drift")
        require(row["validation_instance_id"] == f"r1_{source['validation_instance_id']}", "repair validation ID drift")
        require(row["supersedes_attempt_id"] == source["attempt_id"], "repair supersession drift")
        require(all(row[field] == source[field] for field in identity_fields), "repair changed a frozen attempt")
    return attempts, plan


def check_phase4_evidence() -> dict[str, Any]:
    for relative in PHASE4_OUTPUTS:
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe Phase 4 artifact: {relative}")
    attempts, plan = check_phase4_freeze_and_incident()
    decision = load_json(PAPER / "fresh_holdout_decision.json")
    receipt = load_json(PAPER / "fresh_holdout_receipt.json")
    resources = load_json(PAPER / "fresh_holdout_actual_resources.json")
    require(decision["schema_version"] == 1 and decision["phase"] == 4, "Phase 4 decision schema drift")
    require(
        decision["decision"] in {"pass", "no_go", "blocked_insufficient_information", "blocked_fixed_budget"},
        "unknown Phase 4 decision",
    )
    require(receipt["schema_version"] == 1 and receipt["phase"] == 4, "Phase 4 receipt schema drift")
    require(resources["schema_version"] == 1 and resources["phase"] == 4, "Phase 4 resource schema drift")
    require(decision["rank_order_claim"] == "diagnostic_only", "Phase 4 promoted rank order")
    require(decision["gpu_screen_status_if_applied"] == "experimental", "Phase 4 promoted product status")
    require(receipt["rank_order_claim"] == "diagnostic_only", "Phase 4 receipt promoted rank order")
    require(receipt["attempt_plan_sha256"] == sha256_file(PAPER / "fresh_holdout_repair1_attempt_plan.tsv"), "receipt attempt plan drift")
    require(receipt["repair_plan_sha256"] == sha256_file(PAPER / "fresh_holdout_repair1_plan.json"), "receipt repair plan drift")
    require(decision["repair_plan_sha256"] == receipt["repair_plan_sha256"], "decision repair plan drift")
    require(
        decision["fresh_holdout_receipt_sha256"] == sha256_file(PAPER / "fresh_holdout_receipt.json"),
        "decision/receipt digest drift",
    )
    require(
        receipt["actual_resources_sha256"] == sha256_file(PAPER / "fresh_holdout_actual_resources.json"),
        "receipt/resource digest drift",
    )
    for relative, digest in receipt["source_data_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, f"Phase 4 source-data digest drift: {relative}")

    summary = load_json(PHASE4_REPAIR_ARTIFACT_ROOT / "run-summary.json")
    require(summary["planned_attempt_count"] == len(attempts) == 368, "run-summary plan count drift")
    require(summary["comparison_started"] is False, "runner comparison isolation drift")
    require(not list(PHASE4_REPAIR_ARTIFACT_ROOT.glob(".*.partial.*")), "stale partial attempt remains")
    attempt_by_id = {row["attempt_id"]: row for row in attempts}
    completed_paths = sorted(PHASE4_REPAIR_ARTIFACT_ROOT.glob("*/attempt-complete.json"))
    completed_ids = {path.parent.name for path in completed_paths}
    require(completed_ids <= set(attempt_by_id), "unplanned repair attempt exists")
    checked_receipts = {
        attempt_id: check_phase4_attempt_artifacts(attempt_by_id[attempt_id])
        for attempt_id in sorted(completed_ids)
    }
    require(summary["terminal_attempt_count"] == len(checked_receipts), "terminal attempt count drift")
    require(summary["successful_attempt_count"] == len(checked_receipts), "successful attempt count drift")
    require(summary["technical_failure_count"] == 0, "repair contains a technical failure")
    require(
        receipt["attempt_receipt_sha256"]
        == {
            attempt_id: sha256_file(PHASE4_REPAIR_ARTIFACT_ROOT / attempt_id / "attempt-complete.json")
            for attempt_id in sorted(checked_receipts)
        },
        "Phase 4 attempt-receipt inventory drift",
    )

    _, matches = read_tsv(PAPER / "source_data/fresh_candidate_matches.tsv")
    _, metrics = read_tsv(PAPER / "source_data/fresh_workload_metrics.tsv")
    _, empty = read_tsv(PAPER / "source_data/fresh_empty_workloads.tsv")
    _, failures = read_tsv(PAPER / "source_data/fresh_failure_ledger.tsv")
    _, bounds = read_tsv(PAPER / "source_data/fresh_exact_binomial_bounds.tsv")
    _, ranks = read_tsv(PAPER / "source_data/fresh_rank_diagnostics.tsv")
    require(len(metrics) == 184 * 3 and len(bounds) == 6, "Phase 4 metric/bound row count drift")
    require(sum(row["primary_instance"] == "1" for row in metrics) == 178 * 3, "primary metric count drift")
    require({row["ranking_mode"] for row in metrics} == {"score", "stability", "nt"}, "ranking mode drift")

    if decision["decision"] == "blocked_fixed_budget":
        require(summary["status"] == "in_progress_or_interrupted", "budget-stop summary status drift")
        require(0 < len(checked_receipts) < len(attempts), "budget-stop terminal count is not partial")
        require(summary["missing_attempt_ids"] == [row["attempt_id"] for row in attempts if row["attempt_id"] not in checked_receipts], "budget-stop missing-attempt order drift")
        require(receipt["status"] == "fixed_budget_stop_with_missing_attempts", "budget-stop receipt status drift")
        require(receipt["comparison_global_start_gate_pass"] is False, "partial epoch passed comparison gate")
        require(receipt["comparison_count"] == 0 and receipt["scientific_comparison_started"] is False, "partial epoch ran comparisons")
        require(receipt["fixed_budget_stop"] is True and receipt["repair_epoch_limit_exhausted"] is True, "budget-stop receipt drift")
        require(resources["status"] == "blocked_fixed_budget", "budget resource status drift")
        require(resources["terminal_attempt_count"] == len(checked_receipts), "budget resource terminal count drift")
        require(resources["unstarted_attempt_count"] == len(attempts) - len(checked_receipts), "budget resource missing count drift")
        require(resources["terminal_technical_failure_count"] == 0, "budget stop masked a terminal failure")
        require(resources["fixed_budget_gate_pass"] is False, "budget-stop resource gate passed")
        require(
            resources["retained_artifact_storage_within_quota"] is False
            or resources["next_g_storage_reservation_gate_pass"] is False,
            "budget-stop storage condition is not proven",
        )
        retained = directory_bytes(PHASE4_ORIGINAL_ARTIFACT_ROOT) + directory_bytes(PHASE4_REPAIR_ARTIFACT_ROOT)
        require(resources["actual_total_epoch_artifact_storage_bytes"] == retained, "actual retained storage drift")
        require(resources["max_artifact_storage_bytes"] == PHASE4_STORAGE_QUOTA_BYTES, "actual resource quota drift")
        require(resources["next_raw_g_telemetry_reservation_bytes"] == PHASE4_REPAIR_RESERVATION_BYTES, "actual resource reservation drift")
        require(decision["fixed_budget_stop"] is True, "decision omitted fixed-budget stop")
        require(decision["scientific_decision_reached"] is False, "partial epoch claims a scientific decision")
        require(decision["later_phase_authorized"] is False, "budget stop authorized a later phase")
        require(decision["contract_status_if_applied"] == "in_validation", "budget stop changed contract status")
        require(decision["bioinformatics_route_if_applied"] == "conditionally_reopened", "budget stop changed route")
        require(len(matches) == len(empty) == len(ranks) == 0, "partial epoch contains scientific comparisons")
        require(len(failures) == len(attempts) - len(checked_receipts), "budget-stop failure ledger count drift")
        require(all(row["failure_class"] == "missing_attempt" for row in failures), "budget ledger failure class drift")
        require(all(row["replacement_or_retry_used"] == "0" for row in failures), "budget ledger contains retry")
        require(all(row["comparison_status"] == "technical_failure" for row in metrics), "partial metrics claim comparison success")
        require(all(row["matching_started"] == "0" for row in metrics), "partial metrics started matching")
        require(all(row["binary_success"] == "0" for row in metrics), "partial metrics claim binary success")
        require(all(row["successes"] == "0" and row["trials"] == "178" for row in bounds), "partial exact bounds drift")
        require(all(row["threshold_pass"] == "0" for row in bounds), "partial exact bound passed")
    else:
        require(len(checked_receipts) == len(attempts) == 368, "complete decision lacks every attempt")
        require(summary["status"] == "complete_success", "complete repair summary did not pass")
        require(receipt["status"] == "complete", "complete receipt status drift")
        require(receipt["comparison_global_start_gate_pass"] is True, "complete epoch comparison gate failed")
        require(receipt["comparison_count"] == 184, "complete comparison count drift")
        require(resources["status"] == "pass" and resources["fixed_budget_gate_pass"] is True, "complete resource gate failed")
        require(len(ranks) == 184 * 3, "complete rank-diagnostic count drift")
        if decision["decision"] == "pass":
            require(decision["all_promotion_gates_pass"] is True, "Phase 4 pass lacks all gates")
            require(decision["information_gate_pass"] is True, "Phase 4 pass lacks information")
            require(decision["endpoint_gate_pass"] is True, "Phase 4 pass lacks endpoint gate")
            require(decision["zero_technical_failure_gate_pass"] is True, "Phase 4 pass lacks technical gate")
            require(all(row["threshold_pass"] == "1" for row in bounds), "Phase 4 pass bound failure")
            require(not failures, "Phase 4 pass contains failures")

    require(plan["repair_epoch_limit"] == 1, "repair epoch limit changed during analysis")
    check_phase4_reproduction(str(decision["decision"]))
    return decision


def check_phase4_state(state: dict[str, Any], decision: dict[str, Any]) -> None:
    require(all(state["phase_status"][str(index)] == "pass" for index in range(4)), "Phase 4 prerequisite state drift")
    result = decision["decision"]
    require(state["previous_phase_commit"] == PHASE3_COMMIT, "Phase 4 previous commit state drift")
    require(state["gpu_screen_status"] == "experimental", "Phase 4 promoted gpu-screen")
    require(state["rank_order_claim"] == "diagnostic_only", "Phase 4 promoted rank order")
    if result == "pass":
        require(state["phase_status"]["4"] == "pass", "Phase 4 pass state drift")
        require(all(state["phase_status"][str(index)] == "pending" for index in range(5, 10)), "later phase advanced during Phase 4")
        require(state["active_phase"] == 5 and state["last_completed_phase"] == 4, "Phase 4 pass transition drift")
        require(state["last_decision"] == "fresh_concordance_pass", "Phase 4 pass decision drift")
        require(state["contract_status"] == "fresh_concordance_pass", "Phase 4 contract promotion drift")
        require(state["bioinformatics_route"] == "conditionally_reopened", "Phase 4 pass route drift")
    elif result == "no_go":
        require(state["phase_status"]["4"] == "no_go", "Phase 4 no-go state drift")
        require(all(state["phase_status"][str(index)] == "not_authorized_previous_no_go" for index in range(5, 10)), "later phase authorized after no-go")
        require(state["active_phase"] is None and state["last_completed_phase"] == 4, "Phase 4 no-go transition drift")
        require(state["last_decision"] == "concordance_no_go", "Phase 4 no-go decision drift")
        require(state["contract_status"] == "concordance_no_go", "Phase 4 no-go contract drift")
        require(state["bioinformatics_route"] == "closed_for_this_contract", "Phase 4 no-go route drift")
    else:
        require(result in {"blocked_insufficient_information", "blocked_fixed_budget"}, "unsupported Phase 4 block")
        require(state["phase_status"]["4"] == result, "Phase 4 blocking state drift")
        require(all(state["phase_status"][str(index)] == "not_authorized_previous_no_go" for index in range(5, 10)), "later phase authorized after block")
        require(state["active_phase"] is None and state["last_completed_phase"] == 4, "Phase 4 blocked transition drift")
        require(state["last_decision"] == result, "Phase 4 blocked decision drift")
        require(state["contract_status"] == "in_validation", "Phase 4 block changed contract status")
        require(state["bioinformatics_route"] == "conditionally_reopened", "Phase 4 block changed route")


def check_phase4(mode: str, current_state: dict[str, Any]) -> None:
    check_phase4_start_receipt()
    decision = check_phase4_evidence()
    run_phase4_unit_tests()
    if mode == "precommit":
        paths = allowlist(4)
        check_precommit_receipt(4, paths)
        check_phase4_state(current_state, decision)
        require(git("rev-parse", "HEAD") == PHASE3_COMMIT, "Phase 4 precommit parent drift")
        require(changed_paths() == set(paths), "Phase 4 allowlisted diff mismatch")
    elif mode == "postcommit":
        require(not changed_paths(), "Phase 4 postcommit checker requires a clean tree")
        commit = phase_commit_for_postcommit(4)
        require(git("merge-base", "--is-ancestor", commit, "HEAD") == "", "Phase 4 commit is not an ancestor")
        state = load_json_from_commit(commit, "paper/biological_topk/PROGRAM_STATE.json")
        paths = allowlist_from_commit(4, commit)
        check_precommit_receipt(4, paths, committed_at=commit)
        check_phase4_state(state, decision)
        require(git("rev-parse", f"{commit}^") == PHASE3_COMMIT, "Phase 4 commit parent drift")
        require(git("log", "-1", "--format=%s", commit) == PHASE4_COMMIT_MESSAGE, "Phase 4 commit message drift")
        committed = set(git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines())
        require(committed == set(paths), "Phase 4 committed paths differ from allowlist")
    else:
        raise CheckError(f"unsupported Phase 4 mode: {mode}")


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
    elif args.phase == 1:
        check_phase1(args.mode, state)
    elif args.phase == 2:
        check_phase2(args.mode, state)
    elif args.phase == 3:
        check_phase3(args.mode, state)
    elif args.phase == 4:
        check_phase4(args.mode, state)
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
