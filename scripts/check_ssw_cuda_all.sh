#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"

if [[ "$MODE" != "--precommit" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--precommit|--final]" >&2
  exit 2
fi

required=(
  goal-ssw.md
  paper/ssw_cuda/PROGRAM_STATE.json
  paper/ssw_cuda/STATUS.md
  paper/ssw_cuda/FINAL_STATUS.md
  paper/ssw_cuda/final_decision.json
  paper/ssw_cuda/claim_to_evidence.tsv
  paper/ssw_cuda/limitations.md
  paper/ssw_cuda/release_checklist.md
  paper/ssw_cuda/manuscript_handoff.md
  paper/ssw_cuda/completion_audit.tsv
  paper/ssw_cuda/historical_evidence_receipt.json
  paper/ssw_cuda/amdahl_v2_decision.json
  paper/ssw_cuda/cpu_oracle_binary_receipt.json
  paper/ssw_cuda/corpus_receipt.json
  paper/ssw_cuda/upstream_build_receipt.json
  paper/ssw_cuda/preselect_receipt.json
  paper/ssw_cuda/forward_endpoint_receipt.json
  paper/ssw_cuda/forward_hybrid_decision.json
  paper/ssw_cuda/forward_hybrid_source_data.tsv
  paper/ssw_cuda/forward_hybrid_projection.json
  paper/ssw_cuda/used_input_exclusion_registry.tsv
  paper/ssw_cuda/used_input_exclusion_registry.sha256
  paper/ssw_cuda/license_inventory.tsv
  scripts/check_ssw_cuda_all.sh
)
for relative in "${required[@]}"; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe final SSW-CUDA artifact: $relative" >&2
    exit 1
  fi
done

python3 - "$ROOT" "$MODE" <<'PY'
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(relative):
    path = root / relative
    require(path.is_file() and not path.is_symlink(), f"unsafe JSON: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_tsv(relative, fields):
    path = root / relative
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == tuple(fields), f"schema drift: {relative}")
        rows = list(reader)
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows),
            f"malformed TSV: {relative}")
    return rows


state = load_json("paper/ssw_cuda/PROGRAM_STATE.json")
decision = load_json("paper/ssw_cuda/final_decision.json")
phase7 = load_json("paper/ssw_cuda/forward_hybrid_decision.json")
amdahl = load_json("paper/ssw_cuda/amdahl_v2_decision.json")
h2 = load_json("paper/bioinformatics/canonical_hybrid_v2_performance_receipt.json")
oracle = load_json("paper/ssw_cuda/cpu_oracle_binary_receipt.json")
preselect = load_json("paper/ssw_cuda/preselect_receipt.json")
forward = load_json("paper/ssw_cuda/forward_endpoint_receipt.json")
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")
final_status = (root / "paper/ssw_cuda/FINAL_STATUS.md").read_text(encoding="utf-8")
limitations = (root / "paper/ssw_cuda/limitations.md").read_text(encoding="utf-8")
handoff = (root / "paper/ssw_cuda/manuscript_handoff.md").read_text(encoding="utf-8")

expected_phases = {
    "0": "pass", "1": "pass", "2": "pass", "3": "pass",
    "4": "pass", "5": "pass", "6": "pass", "7": "no_go",
    "8": "not_run_phase7_no_go", "9": "not_run_phase7_no_go",
    "10": "not_run_phase7_no_go", "11": "not_run_phase7_no_go",
    "12": "not_run_phase7_no_go",
}
for phase, expected in expected_phases.items():
    require(state["phase_status"][phase] == expected, f"phase {phase} state drift")
require(state["active_phase"] == 13, "final audit must remain at Phase 13")
require(state["bioinformatics_b3_track"] == "closed_amdahl", "B3 state reopened")
require(state["engineering_track"] == "closed_phase7_forward_hybrid_no_go",
        "engineering no-go state drift")
require(state["l8_contract_status"] == "diagnostic_only", "L8 state drift")
require(decision["decision"] == "ssw_cuda_forward_or_reverse_checkpoint_only",
        "unexpected final decision")
require(decision["bioinformatics_b3_track"] == "closed_amdahl", "final B3 drift")
require(not decision["full_gpu_backend_integrated"] and
        not decision["full_gpu_contract_promoted"] and
        not decision["safe_gpu_user_contract"] and
        not decision["fresh_holdout_executed"] and
        not decision["release_candidate_created"],
        "unsupported final promotion flag")
require(decision["target_end_to_end_speedup"] == 10.0 and
        decision["threshold_changed"] is False,
        "B3 threshold drift")

for entry in decision["evidence"].values():
    path = root / entry["path"]
    require(sha256(path) == entry["sha256"], f"final evidence digest drift: {entry['path']}")

require(h2["rescue_track_status"] == "closed_performance_no_go", "historical H2 reopened")
require(abs(h2["primary_aggregate_speedup"] - 0.25759196676394047) < 1e-15,
        "historical H2 speedup drift")
require(abs(h2["hybrid_slowdown_vs_authority"] - 3.8821086408972096) < 1e-15,
        "historical H2 slowdown drift")
require(amdahl["bioinformatics_b3_track"] == "closed_amdahl", "Amdahl decision drift")
require(abs(amdahl["conservative_p_backend_addressable"] - 0.619448148391) < 1e-12,
        "Amdahl addressable fraction drift")
require(abs(amdahl["maximum_speedup_infinite"] - 2.6277628022881236) < 1e-12,
        "Amdahl ceiling drift")
require(amdahl["target_end_to_end_speedup"] == 10 and not amdahl["b3_threshold_changed"],
        "Amdahl threshold changed")

oracle_binary = root / oracle["binary_path"]
require(sha256(oracle_binary) == oracle["binary_sha256"], "CPU oracle binary drift")
require(oracle["status"] == "pass" and oracle["ssw_cpu_oracle_epoch"] == 2,
        "CPU oracle receipt drift")
require(preselect["status"] == "pass", "Phase 5 receipt is not pass")
require(preselect["results"]["primary_column_mismatches"] == 0 and
        preselect["results"]["primary_scoreinfo_mismatches"] == 0 and
        preselect["results"]["selected_false_negatives"] == 0 and
        preselect["results"]["technical_failures"] == 0,
        "Phase 5 exactness drift")
require(forward["status"] == "pass", "Phase 6 receipt is not pass")
require(forward["results"]["supported_endpoint_mismatches"] == 0 and
        forward["results"]["supported_reducer_mismatches"] == 0 and
        forward["results"]["cpu_endpoint_calls"] == 0 and
        forward["results"]["technical_failures"] == 0,
        "Phase 6 exactness drift")

require(phase7["decision"] == "forward_hybrid_performance_futility_stop" and
        phase7["phase7_status"] == "no_go" and
        phase7["no_go_reason"] == "forward_hybrid_implementation_contract_failure",
        "Phase 7 no-go drift")
require(phase7["completed_attempts"] == 26 and
        phase7["correctness_regression_attempts"] == 24 and
        phase7["performance_observations"] == 2 and
        phase7["technical_failures"] == 1 and
        phase7["implementation_contract_failures"] == 1 and
        phase7["declared_contract_mismatches"] == 0,
        "Phase 7 cardinality drift")
require(phase7["cpu_prealign_calls"] == 0 and phase7["cpu_forward_calls"] == 0 and
        phase7["fallbacks"] == 0 and phase7["replacement_retries"] == 0,
        "Phase 7 call boundary drift")
require(not phase7["fresh_holdout_consumed"] and
        not phase7["application_50x668_panel_run"] and
        not phase7["historical_h2_rerun"] and
        phase7["new_cpu_authority_performance_attempts"] == 0,
        "Phase 7 unauthorized execution recorded")

with (root / "paper/ssw_cuda/forward_hybrid_source_data.tsv").open(
    newline="", encoding="utf-8"
) as handle:
    source = list(csv.DictReader(handle, delimiter="\t"))
require(len(source) == 49, "Phase 7 source-data cardinality drift")
require(sum(row["status"] == "complete" for row in source) == 26, "complete count drift")
require(sum(row["status"] == "technical_failure" for row in source) == 1,
        "technical-failure count drift")
require(sum(row["status"] == "not_started" for row in source) == 22,
        "not-started count drift")
complete = [row for row in source if row["status"] == "complete"]
require(all(row["comparison_status"] == "clean" and row["declared_contract_clean"] == "1"
            for row in complete), "completed comparison drift")
require(all(row["clustered_score_top5_equal"] == "1" and
            row["clustered_stability_top5_equal"] == "1" and
            row["clustered_nt_top5_equal"] == "1" for row in complete),
        "declared Top-5 contract drift")
failed = next(row for row in source if row["status"] == "technical_failure")
require(failed["attempt_id"] == "p7v2p_large_h19_chr21_o01" and
        failed["returncode"] == "2" and failed["timed_out"] == "0" and
        failed["cpu_failures"] == "1" and failed["fallback_calls"] == "0",
        "Phase 7 failure inventory drift")

claim_fields = (
    "claim_id", "claim_text", "disposition", "contract_scope",
    "evidence_path", "evidence_sha256", "caveat",
)
claims = load_tsv("paper/ssw_cuda/claim_to_evidence.tsv", claim_fields)
require(len(claims) == 10 and len({row["claim_id"] for row in claims}) == 10,
        "claim map cardinality drift")
for row in claims:
    require(sha256(root / row["evidence_path"]) == row["evidence_sha256"],
            f"claim evidence drift: {row['claim_id']}")
claim_by_id = {row["claim_id"]: row for row in claims}
require(claim_by_id["C06"]["disposition"] == "forbidden" and
        claim_by_id["C07"]["disposition"] == "forbidden" and
        claim_by_id["C09"]["disposition"] == "forbidden",
        "prohibited claim disposition drift")

audit_fields = (
    "audit_id", "requirement", "expected_status", "observed_status",
    "evidence_path", "evidence_sha256", "note",
)
audit = load_tsv("paper/ssw_cuda/completion_audit.tsv", audit_fields)
require(len(audit) == 28 and len({row["audit_id"] for row in audit}) == 28,
        "completion audit cardinality drift")
for row in audit:
    if row["evidence_path"] != "NA":
        require(re.fullmatch(r"[0-9a-f]{64}", row["evidence_sha256"]) is not None,
                f"invalid audit digest: {row['audit_id']}")
        require(sha256(root / row["evidence_path"]) == row["evidence_sha256"],
                f"audit evidence drift: {row['audit_id']}")
audit_by_id = {row["audit_id"]: row for row in audit}
require(audit_by_id["A019"]["observed_status"] == "not_achieved" and
        audit_by_id["A025"]["observed_status"] == "not_achieved",
        "negative completion result was hidden")

checksum = (root / "paper/ssw_cuda/used_input_exclusion_registry.sha256").read_text(
    encoding="ascii"
).split()[0]
require(sha256(root / "paper/ssw_cuda/used_input_exclusion_registry.tsv") == checksum,
        "used-input registry checksum drift")
licenses = load_tsv(
    "paper/ssw_cuda/license_inventory.tsv",
    ("component", "license_expression", "notice_path", "notice_sha256",
     "source_commit", "use_status", "notes"),
)
require({row["component"] for row in licenses} >=
        {"LongTarget-exact-sim", "Complete Striped Smith-Waterman core", "GASAL2"},
        "license inventory is incomplete")

for phrase in (
    "ssw_cuda_forward_or_reverse_checkpoint_only",
    "There is no full-GPU safe backend",
    "Full-output equality remains diagnostic only",
):
    require(phrase in final_status, f"FINAL_STATUS wording drift: {phrase}")
require("Cross-architecture GPU determinism was not established" in limitations,
        "cross-architecture limitation missing")
require("Bioinformatics Applications Note widening claim is closed" in handoff,
        "publication route drift")
for phase in range(8, 13):
    require(f"phase_{phase}_status = not_run_phase7_no_go" in goal,
            f"goal skipped-phase state drift: {phase}")

absent_results = (
    "paper/ssw_cuda/reverse_start_receipt.json",
    "paper/ssw_cuda/traceback_receipt.json",
    "paper/ssw_cuda/full_gpu_decision.json",
    "paper/ssw_cuda/fresh_holdout_decision.json",
    "paper/ssw_cuda/performance_decision.json",
    "paper/ssw_cuda/release_candidate_receipt.json",
)
require(all(not (root / relative).exists() for relative in absent_results),
        "an unauthorized Phase 8-12 result artifact exists")
require(sha256(root / "goal.md") ==
        "8489d7a4e37c9a2d4bdee78fcee40158230c513bfc6adcea9993abd7b8c71509",
        "goal.md was overwritten")

if mode == "--precommit":
    require(state["phase_status"]["13"] == "in_progress", "precommit Phase 13 state drift")
    require(decision["phase13_status"] == "in_progress" and
            decision["final_certification"] == "pending_clean_commit",
            "precommit final-decision state drift")
    for audit_id in ("A026", "A027", "A028"):
        require(audit_by_id[audit_id]["observed_status"] == "pending_clean_commit",
                f"precommit audit state drift: {audit_id}")
else:
    require(state["phase_status"]["13"] == "pass", "final Phase 13 state drift")
    require(decision["phase13_status"] == "pass" and
            decision["final_certification"] == "aggregate_checker_passed",
            "final certification state drift")
    for audit_id in ("A026", "A027", "A028"):
        require(audit_by_id[audit_id]["observed_status"] == "pass",
                f"final audit state drift: {audit_id}")
    require(not subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=root, check=True,
        text=True, stdout=subprocess.PIPE
    ).stdout, "final aggregate checker requires a clean worktree")
    message = subprocess.run(
        ["git", "log", "-1", "--format=%s"], cwd=root, check=True,
        text=True, stdout=subprocess.PIPE
    ).stdout.strip()
    require(message == "docs: certify exact SSW-CUDA completion audit and publication route",
            "unexpected final certification commit")
    tracked = set(subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.splitlines())
    for relative in (
        "paper/ssw_cuda/final_decision.json",
        "paper/ssw_cuda/completion_audit.tsv",
        "paper/ssw_cuda/FINAL_STATUS.md",
        "scripts/check_ssw_cuda_all.sh",
    ):
        require(relative in tracked, f"uncommitted final artifact: {relative}")

for phrase in (
    f"active_phase = {state['active_phase']}",
    f"phase_13_status = {state['phase_status']['13']}",
    "bioinformatics_b3_track = closed_amdahl",
    "engineering_track = closed_phase7_forward_hybrid_no_go",
    "l8_contract_status = diagnostic_only",
):
    require(phrase in goal and phrase in status, f"final state text drift: {phrase}")
PY

make -C "$ROOT" check-ssw-cuda-phase0
make -C "$ROOT" check-ssw-cuda-phase1-recovery
make -C "$ROOT" check-ssw-cuda-phase2
make -C "$ROOT" check-ssw-cuda-phase3
make -C "$ROOT" check-ssw-cuda-phase4
make -C "$ROOT" check-ssw-cuda-phase5
make -C "$ROOT" check-ssw-cuda-phase6
make -C "$ROOT" check-ssw-cuda-phase7

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA aggregate $MODE checks OK"
echo "final_decision=ssw_cuda_forward_or_reverse_checkpoint_only"
echo "bioinformatics_b3_track=closed_amdahl"
