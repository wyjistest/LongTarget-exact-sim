#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_task_frontier_proof_parser"}"
PARSER="$ROOT/scripts/analyze_fasim_gasal2_task_frontier_proof.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/baseline.tsv" <<'EOF'
task_index	legacy_order_index	selected_align_attempt_index	scoreinfo_identity	emission_reason	chr	genome_start	genome_end	query_start	query_end	target_start	target_end	score	identity	tri_score	nt	rule	strand	para	dna_start_pos
1	0	-1	task:1:row:0	legacy_output	chr1	100	110	1	10	100	110	120	70	2	11	4	ParaPlus	0	100
1	1	-1	task:1:row:1	legacy_output	chr1	200	212	20	30	200	212	90	70	2	13	4	ParaPlus	0	200
2	0	-1	task:2:row:0	legacy_output	chr1	400	410	40	50	400	410	80	70	2	11	5	ParaMinus	0	400
EOF

cp "$WORK/baseline.tsv" "$WORK/same.tsv"

cat >"$WORK/pruned.tsv" <<'EOF'
task_index	legacy_order_index	selected_align_attempt_index	scoreinfo_identity	emission_reason	chr	genome_start	genome_end	query_start	query_end	target_start	target_end	score	identity	tri_score	nt	rule	strand	para	dna_start_pos
1	0	-1	task:1:row:0	legacy_output	chr1	100	110	1	10	100	110	120	70	2	11	4	ParaPlus	0	100
2	0	-1	task:2:row:0	legacy_output	chr1	400	410	40	50	400	410	80	70	2	11	5	ParaMinus	0	400
EOF

python3 "$PARSER" \
  --baseline "$WORK/baseline.tsv" \
  --candidate "$WORK/same.tsv" \
  >"$WORK/same_summary.txt"

python3 "$PARSER" \
  --baseline "$WORK/baseline.tsv" \
  --candidate "$WORK/pruned.tsv" \
  >"$WORK/pruned_summary.txt"

require_same_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/same_summary.txt"; then
    echo "missing expected safe line: $expected" >&2
    cat "$WORK/same_summary.txt" >&2
    exit 1
  fi
}

require_pruned_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/pruned_summary.txt"; then
    echo "missing expected unsafe line: $expected" >&2
    cat "$WORK/pruned_summary.txt" >&2
    exit 1
  fi
}

require_same_line "input_mode=task_triplex_full"
require_same_line "baseline_rows=3"
require_same_line "candidate_rows=3"
require_same_line "task_row_set_equal=1"
require_same_line "task_frontier_safety=safe"
require_same_line "task_count=2"
require_same_line "changed_tasks=0"
require_same_line "baseline_only_rows=0"
require_same_line "candidate_only_rows=0"
require_same_line "first_changed_task=none"
require_same_line "first_changed_task_baseline_rows=0"
require_same_line "first_changed_task_candidate_rows=0"
require_same_line "real_prune_proof_gate=pass"

require_pruned_line "input_mode=task_triplex_full"
require_pruned_line "baseline_rows=3"
require_pruned_line "candidate_rows=2"
require_pruned_line "task_row_set_equal=0"
require_pruned_line "task_frontier_safety=unsafe"
require_pruned_line "task_count=2"
require_pruned_line "changed_tasks=1"
require_pruned_line "baseline_only_rows=1"
require_pruned_line "candidate_only_rows=0"
require_pruned_line "first_changed_task=1"
require_pruned_line "first_changed_task_baseline_rows=2"
require_pruned_line "first_changed_task_candidate_rows=1"
require_pruned_line "real_prune_proof_gate=fail"

echo "ok"
