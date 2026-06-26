#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase3_cigar_nt_prefilter_design.md"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase3_cigar_nt_prefilter_design"}"

if [[ ! -s "$DOC" ]]; then
  echo "missing Phase 3 CIGAR NT prefilter design doc: $DOC" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

python3 - "$DOC" >"$WORK/summary.txt" <<'PY'
from pathlib import Path
import sys

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())

required = [
    "Fasim GASAL2 Phase 3 CIGAR NT Prefilter Design",
    "Phase 3 design gate",
    "not runtime code",
    "not a completion claim",
    "not permission to enable a real prune",
    "current_real_prune_decision = no_go",
    "current_real_prune_row_set_equal = 0",
    "real_prune_may_be_enabled = 0",
    "nt-sum-span pruning can perturb task-local sort/unique/top-N competition",
    "cigar_nt_prefilter",
    "FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_SHADOW=1",
    "FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER=1",
    "aligned_len = fasim_cigar_aligned_len(alignment.cigar)",
    "aligned_len < ntMin",
    "not based on GASAL2 endpoint",
    "not based on top5 output",
    "phase3_cigar_nt_prefilter_disagree_lt_ntmin",
    "phase3_cigar_nt_prefilter_candidate_false_negative_rows",
    "phase3_cigar_nt_prefilter_task_frontier_safety",
    "disagree_lt_ntmin = 0",
    "candidate_false_negative_rows = 0",
    "task_row_set_equal = 1",
    "task_frontier_safety = safe",
    "real_prune_proof_gate = pass",
    "candidate_broad_cpu_triplex.tsv",
    "broad_cpu_triplex.tsv",
    "full restored row-set equality clean",
    "convert wall lower than Phase 2",
    "default-on pruning",
    "GASAL2 endpoint authority",
    "GPU CIGAR or traceback authority",
    "top5-only proof as full-output proof",
    "nt-sum-span real prune resurrection",
    "scoreInfo rank pruning",
    "sort/top-N partial selection",
    "If the CIGAR NT prefilter shadow proves exact and saves material convert work:",
    "If the proof fails:",
    "If the proof passes but saved work is small:",
]

missing = [needle for needle in required if needle not in doc]
if missing:
    raise SystemExit(
        "Phase 3 CIGAR NT prefilter design missing phrases: "
        + ", ".join(missing)
    )

print("phase3_cigar_nt_prefilter_design_gate=defined")
print("candidate=cigar_nt_prefilter")
print("requires_shadow_first=1")
print("requires_disagree_lt_ntmin_zero=1")
print("requires_candidate_false_negative_rows_zero=1")
print("requires_task_frontier_safety_safe=1")
print("requires_real_prune_proof_gate_pass=1")
print("current_nt_sum_span_prune_status=no_go")
print("real_prune_may_be_enabled=0")
print("must_not_call_update_goal_complete=1")
print("ok")
PY

cat "$WORK/summary.txt"
