#!/usr/bin/env python3
"""Freeze the complete Phase 4 artifact inventory and terminal decision receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
V2_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2"
PHASE4_ROOT = V2_ROOT / "phase4"
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
MANIFEST = PAPER / "phase_4_artifact_manifest.json"
RECEIPT = PAPER / "phase_4_decision_receipt.json"
PHASE3_COMMIT = "53e57591da1bfe8ffa34ebe57d89a5d2cd347d29"
QUOTA_BYTES = 68_719_476_736


class FreezeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_role(relative: Path) -> str:
    value = relative.as_posix()
    name = relative.name
    if value == "phase4/run-start.json":
        return "formal_run_start"
    if value == "phase4/run-summary.json":
        return "formal_run_summary"
    if value.startswith("phase4/formal/"):
        return {
            "attempt-terminal.json": "formal_attempt_terminal",
            "backend-stderr.log": "formal_backend_log",
            "backend-stdout.log": "formal_backend_log",
            "candidate_sites.tsv": "formal_candidate_sites",
            "contract.json": "formal_product_contract",
            "input-receipt.json": "formal_input_receipt",
            "native-TFOsorted": "formal_native_diagnostic",
            "run-report.json": "formal_run_report",
            "runner-stderr.log": "formal_runner_log",
            "runner-stdout.log": "formal_runner_log",
        }.get(name, "")
    if value.startswith("phase4/comparisons/"):
        return {
            "comparator-stderr.log": "formal_comparator_log",
            "comparator-stdout.log": "formal_comparator_log",
            "comparison-details.tsv": "formal_comparison_details",
            "comparison.json": "formal_comparison_result",
            "gpu-input-receipt.json": "formal_gpu_input_receipt",
            "pair-terminal.json": "formal_pair_terminal",
        }.get(name, "")
    if value.startswith("phase4/analysis/"):
        return {
            "decision.json": "formal_decision",
            "determinism.json": "formal_determinism_result",
            "pair-results.tsv": "formal_pair_result_table",
            "timings.json": "formal_eligible_timing_input",
        }.get(name, "")
    return ""


def inventory() -> tuple[list[dict[str, Any]], Counter[str]]:
    require(PHASE4_ROOT.is_dir(), "Phase 4 artifact root is missing")
    require(not any(".partial" in path.parts for path in PHASE4_ROOT.rglob("*")), "orphaned Phase 4 partial exists")
    artifacts: list[dict[str, Any]] = []
    roles: Counter[str] = Counter()
    for path in sorted(PHASE4_ROOT.rglob("*")):
        if not path.is_file():
            continue
        require(not path.is_symlink(), f"unsafe Phase 4 artifact symlink: {path}")
        relative = path.relative_to(V2_ROOT)
        role = artifact_role(relative)
        require(bool(role), f"unclassified Phase 4 artifact: {relative}")
        roles[role] += 1
        artifacts.append(
            {
                "relative_path": relative.as_posix(),
                "role": role,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return artifacts, roles


def repeat_digest_diagnostic() -> dict[str, Any]:
    terminals = [
        load_json(path)
        for path in sorted((PHASE4_ROOT / "formal").glob("*/attempt-terminal.json"))
    ]
    require(len(terminals) == 100, "formal terminal denominator drift")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for terminal in terminals:
        grouped[(terminal["workload_id"], terminal["arm"])].append(terminal)
    require(len(grouped) == 20, "workload-arm repeat inventory drift")
    rows = []
    for (workload_id, arm), values in sorted(grouped.items()):
        digests = {value["product"]["candidate_sites_sha256"] for value in values}
        rows.append(
            {
                "workload_id": workload_id,
                "arm": arm,
                "repeat_count": len(values),
                "unique_candidate_sites_digests": len(digests),
                "pass": len(values) == 5 and len(digests) == 1,
            }
        )
    return {
        "diagnostic_only": True,
        "formal_analyzer_all_outputs_deterministic_field": False,
        "formal_analyzer_field_reason": "eligibility short-circuit before determinism branch",
        "workload_arm_groups": rows,
        "all_observed_repeat_digests_deterministic": all(row["pass"] for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", required=True)
    parser.parse_args()
    try:
        require(not MANIFEST.exists() and not RECEIPT.exists(), "Phase 4 freeze output already exists")
        run_start = load_json(PHASE4_ROOT / "run-start.json")
        run_summary = load_json(PHASE4_ROOT / "run-summary.json")
        decision = load_json(PHASE4_ROOT / "analysis/decision.json")
        require(run_start["phase3_commit"] == PHASE3_COMMIT, "run-start commit drift")
        require(run_summary["phase3_commit"] == PHASE3_COMMIT, "run-summary commit drift")
        require(decision["phase3_commit"] == PHASE3_COMMIT, "decision commit drift")
        require(run_summary["formal_execution_complete"] is True, "formal execution incomplete")
        require(run_summary["planned_arm_attempts"] == run_summary["terminal_arm_attempts"] == 100, "formal arm denominator drift")
        require(run_summary["technical_success_arm_attempts"] == 100, "formal technical success denominator drift")
        require(run_summary["technical_failure_arm_attempts"] == 0 and run_summary["retry_count"] == 0, "formal failure or retry observed")
        require(decision["decision"] == "performance_no_go", "unexpected Phase 4 decision")
        require(decision["planned_pair_rows"] == decision["technical_success_pair_rows"] == 50, "formal pair denominator drift")
        require(decision["candidate_site_contract_pass_rows"] == 45, "formal contract-pass count drift")
        require(decision["primary_capacity_estimate_computed"] is False and decision["capacity"] is None, "ineligible capacity estimate was computed")
        require(decision["primary_gate_pass"] is False and decision["downstream_phases_authorized"] is False, "no-go authorized downstream work")

        pair_terminals = [
            load_json(path)
            for path in sorted((PHASE4_ROOT / "comparisons").glob("*/pair-terminal.json"))
        ]
        require(len(pair_terminals) == 50, "formal comparison denominator drift")
        failures = sorted(pair["pair_id"] for pair in pair_terminals if pair["contract_pass"] is not True)
        expected_failures = [f"v2p4_w010__repeat{index:02d}" for index in range(5)]
        require(failures == expected_failures, "formal contract-failure identity drift")

        artifacts, roles = inventory()
        phase4_bytes = sum(item["size_bytes"] for item in artifacts)
        total_bytes = sum(path.stat().st_size for path in V2_ROOT.rglob("*") if path.is_file())
        require(total_bytes <= QUOTA_BYTES, "fixed v2 artifact quota exceeded")
        manifest = {
            "schema_version": 1,
            "phase": 4,
            "formal_decision_evidence": True,
            "decision": "performance_no_go",
            "artifacts": artifacts,
            "role_counts": dict(sorted(roles.items())),
            "phase4_artifact_count": len(artifacts),
            "phase4_artifact_bytes": phase4_bytes,
            "bytes_at_phase4_freeze": total_bytes,
            "quota_bytes": QUOTA_BYTES,
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        diagnostic = repeat_digest_diagnostic()
        receipt = {
            "schema_version": 1,
            "phase": 4,
            "phase3_commit": PHASE3_COMMIT,
            "software_epoch": "submission_rc_v2_2",
            "decision": "performance_no_go",
            "stop_loss_applied": True,
            "run_start_sha256": sha256(PHASE4_ROOT / "run-start.json"),
            "run_summary_sha256": sha256(PHASE4_ROOT / "run-summary.json"),
            "analysis_decision_sha256": sha256(PHASE4_ROOT / "analysis/decision.json"),
            "artifact_manifest_sha256": sha256(MANIFEST),
            "formal_execution": {
                "planned_arm_attempts": 100,
                "terminal_arm_attempts": 100,
                "technical_success_arm_attempts": 100,
                "technical_failure_arm_attempts": 0,
                "retry_count": 0,
            },
            "formal_comparison": {
                "planned_pair_rows": 50,
                "technical_success_pair_rows": 50,
                "candidate_site_contract_pass_rows": 45,
                "contract_failure_pair_rows": 5,
                "contract_failure_pair_ids": failures,
                "failure_scope": "v2p4_w010 stability Top-5 complete-set substitution; score and nt passed and stability Top-1 was retained",
            },
            "repeat_digest_diagnostic": diagnostic,
            "primary_capacity": {
                "eligible": False,
                "estimate_computed": False,
                "gate_pass": False,
                "reason": "planned_pair_rows != candidate_site_contract_pass_rows",
            },
            "downstream": {
                "phase_5": "not_authorized_previous_no_go",
                "phase_6": "not_authorized_previous_no_go",
                "phase_7": "not_authorized_previous_no_go",
                "formal_external_comparison_executed": False,
                "release_packaging_executed": False,
                "application_note_drafting_executed": False,
            },
        }
        RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, FreezeError) as error:
        print(f"Phase 4 evidence freeze failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"decision": receipt["decision"], "artifact_count": len(artifacts), "phase4_artifact_bytes": phase4_bytes}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
