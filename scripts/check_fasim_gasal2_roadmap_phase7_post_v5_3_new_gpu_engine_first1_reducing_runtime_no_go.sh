#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
CANONICAL="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
MAKEFILE="$ROOT/Makefile"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
LONGTARGET="$ROOT/fasim/Fasim-LongTarget.cpp"

python3 - "$DOC" "$PREV" "$ROADMAP" "$CLOSURE" "$DRIVER" "$CANONICAL" \
  "$MAKEFILE" "$BRIDGE_CPP" "$LONGTARGET" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    closure,
    driver,
    canonical,
    makefile,
    bridge_cpp,
    longtarget,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [doc, prev, roadmap, closure, driver, canonical, makefile, bridge_cpp, longtarget]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
canonical_text = canonical.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")
runtime_text = bridge_cpp.read_text(encoding="utf-8") + "\n" + longtarget.read_text(encoding="utf-8")

required_doc = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Reducing Runtime No-Go",
    "phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md",
    "previous_gate = first1_reducing_runtime_with_certificate_or_no_go",
    "runtime_reduction_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "certificate_producer_active = 1",
    "certificate_valid_before_d2h = 1",
    "certificate_producer_is_synthetic_api_gate = 1",
    "real_fasim_runtime_certificate_source = 0",
    "real_fasim_runtime_work_drop_path = 0",
    "prealign_cuda_emit_new_engine_skipped_work_certificates_runtime_call_count = 0",
    "scoreInfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "fallback_accounting_clean = 0",
    "candidate_wall_seconds_lt_baseline_wall_seconds = 0",
    "full_rows_equal = unproven",
    "digest_match = unproven",
    "missing_rows = unproven",
    "extra_rows = unproven",
    "no_first64_from_failed_first1 = 1",
    "do_not_relabel_synthetic_certificate_as_runtime_reduction = 1",
    "do_not_use_final_cpu_output_membership_as_runtime_proof = 1",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "path_b_current_implementation_available = 0",
    "path_b_runtime_pr_allowed = 0",
    "path_b_different_gpu_execution_design_required = 1",
    "path_a_user_acceptance_required = 1",
    "next_valid_work = path_a_scoped_acceptance_or_new_engine_design_doc",
    "current_execution_gate = path_a_scoped_acceptance_or_new_engine_design_doc",
    "current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design",
]
missing = [phrase for phrase in required_doc if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new GPU engine first1 reducing runtime no-go phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 1",
    "candidate_wall_seconds_lt_baseline_wall_seconds = 1",
    "path_b_current_implementation_available = 1",
    "path_b_runtime_pr_allowed = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(
            "new GPU engine first1 runtime no-go contains forbidden phrase: "
            + forbidden
        )

if "next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go" not in prev_text:
    raise SystemExit("previous producer checkpoint no longer points to first1 reducing runtime gate")

runtime_call_count = runtime_text.count("prealign_cuda_emit_new_engine_skipped_work_certificates(")
if runtime_call_count != 0:
    raise SystemExit(
        "unexpected direct runtime call to certificate API in bridge/LongTarget files: "
        + str(runtime_call_count)
    )

doc_link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md"
for path_name, path_text in [
    ("roadmap", roadmap_text),
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("canonical phase plan", canonical_text),
]:
    if doc_link not in path_text:
        raise SystemExit(f"{path_name} does not link first1 reducing runtime no-go checkpoint")

for path_name, path_text in [
    ("goal closure phase plan", closure_text),
    ("phase driver", driver_text),
    ("canonical phase plan", canonical_text),
]:
    for phrase in [
        "current_gate = path_a_scoped_acceptance_or_new_engine_design_doc",
        "current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design",
        "first1_runtime_reduction_gate_pass = 0",
        "first64_runtime_allowed = 0",
    ]:
        if phrase not in path_text:
            raise SystemExit(f"{path_name} missing current no-go cursor phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-reducing-runtime-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

current_state_line = next(
    (line for line in makefile_text.splitlines() if line.startswith("check-fasim-gasal2-roadmap-current-state:")),
    "",
)
target_name = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-reducing-runtime-no-go"
if target_name not in current_state_line:
    raise SystemExit("current-state aggregate does not include first1 reducing runtime no-go target")

print("phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go=recorded")
print("first1_runtime_reduction_gate_pass=0")
print("real_fasim_runtime_certificate_source=0")
print("real_fasim_runtime_work_drop_path=0")
print("first64_runtime_allowed=0")
print("path_b_different_gpu_execution_design_required=1")
print("path_a_user_acceptance_required=1")
print("current_execution_gate=path_a_scoped_acceptance_or_new_engine_design_doc")
print("current_next_pr=fasim_path_a_scope_acceptance_or_new_gpu_engine_design")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
