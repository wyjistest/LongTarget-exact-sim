#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_direct_phase_roadmap.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])

for path in [doc, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Direct Goal Completion Phase Roadmap",
    "This is the direct phase roadmap for making the active Fasim/GASAL2 goal closable.",
    "It is a plan, not a completion claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "default behavior unchanged = 1",
    "Path A - scoped product completion",
    "Path B - broad objective completion",
    "Do not mix Path A evidence into Path B completion.",
    "current_phase = Phase 7",
    "current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md",
    "runtime_reduction_allowed = 0",
    "runtime_work_drop_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go = recorded",
    "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status = no_go_no_rejected_work",
    "path_b_gpu_upper_bound_reject_certificate_family_stopped = 1",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go = recorded",
    "path_b_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go_status = required_not_defined",
    "path_b_new_design_family_after_gpu_upper_bound_reject_certificate_no_go = undefined",
    "phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance = defined",
    "phase7_gpu_exact_work_unit_compaction_design_spec_status = spec_defined",
    "design_family = gpu_exact_work_unit_compaction_replay",
    "next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "## Phase 0 - Reproducibility",
    "## Phase 1 - Scope Decision",
    "## Phase 2 - Full-Output Baseline",
    "## Phase 3 - CPU Output-Side Reduction",
    "## Phase 4 - Sort/Top-N Reduction",
    "## Phase 5 - Archive Artifact",
    "## Phase 6 - Workload Matrix",
    "## Phase 7 - Broad GPU Path",
    "## Phase 8 - Completion Decision",
    "### Phase 7.1 - Upper-Bound Reject First1 Shadow Scaffold",
    "### Phase 7.2 - Upper-Bound Reject Consumer Or No-Go",
    "### Phase 7.3 - First1 Reducing Runtime",
    "### Phase 7.4 - First64 Broad Gate",
    "### Phase 7.5 - Broad Workload Promotion",
    "design_family = gpu_exact_work_unit_compaction_replay",
    "full_rows_equal = 1",
    "digest_match = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "scoreInfo/preAlign work reduced or replaced = 1",
    "Align-side work reduced or replaced = 1",
    "fallback_accounting_clean = 1",
    "fallback_to_full_cpu_replay",
    "runtime_reduction_enabled",
    "runtime_work_drop_enabled",
    "gate_first1_shadow_pass",
    "gate_first1_pass",
    "Phase 7.3 passes.",
    "Phase 7.4 passes.",
    "Title:",
    "fasim: add exact work-unit compaction first1 shadow scaffold",
    "Goal:",
    "Make exact scoreInfo/preAlign and Align work-unit key compaction observable without enabling runtime reduction or work drop.",
    "no runtime work drop",
    "no scoreInfo/preAlign reduction",
    "no Align-side reduction",
    "no first64",
    "no GPU endpoint/CIGAR/traceback/output/digest authority",
    "no default behavior change",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing direct phase roadmap phrase(s):\n" + "\n".join(missing)
    )

phase_order = [
    "## Phase 0 - Reproducibility",
    "## Phase 1 - Scope Decision",
    "## Phase 2 - Full-Output Baseline",
    "## Phase 3 - CPU Output-Side Reduction",
    "## Phase 4 - Sort/Top-N Reduction",
    "## Phase 5 - Archive Artifact",
    "## Phase 6 - Workload Matrix",
    "## Phase 7 - Broad GPU Path",
    "## Phase 8 - Completion Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("direct phase roadmap headings are out of order")

phase7_order = [
    "### Phase 7.1 - Upper-Bound Reject First1 Shadow Scaffold",
    "### Phase 7.2 - Upper-Bound Reject Consumer Or No-Go",
    "### Phase 7.3 - First1 Reducing Runtime",
    "### Phase 7.4 - First64 Broad Gate",
    "### Phase 7.5 - Broad Workload Promotion",
]
positions = [text.index(heading) for heading in phase7_order]
if positions != sorted(positions):
    raise SystemExit("direct phase roadmap Phase 7 gates are out of order")

for forbidden in [
    "broad_objective_status = complete",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "top5-only evidence closes broad objective = 1",
    "archive-only evidence closes broad objective = 1",
    "output-drift speedup counts as success = 1",
    "first64_runtime_allowed = 1",
    "runtime_reduction_allowed = 1",
    "runtime_work_drop_allowed = 1",
]:
    if forbidden in text:
        raise SystemExit(f"direct phase roadmap contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_completion_direct_phase_roadmap.md"
if link not in roadmap_text:
    raise SystemExit(f"roadmap does not link {link}")

print("direct_phase_roadmap_document=present")
print("direct_phase_roadmap_current_phase=phase7")
print("direct_phase_roadmap_current_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold")
print("direct_phase_roadmap_path_a_requires_user_acceptance=1")
print("direct_phase_roadmap_path_b_requires_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
