#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_preconvert_prune_readiness"}"
CHECKER="$ROOT/scripts/decide_fasim_gasal2_preconvert_prune_readiness.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/authority_diff.txt" <<'EOF'
baseline_rows=8292
candidate_rows=8290
baseline_unique_rows=8292
candidate_unique_rows=8290
baseline_only_rows=3
candidate_only_rows=1
row_set_equal=0
baseline_only_min_nt=52
baseline_only_max_nt=64
candidate_only_min_nt=109
candidate_only_max_nt=109
cross_overlap_pairs=0
cross_overlap_max_bp=0
cross_overlap_same_rule_pairs=0
baseline_only_rule_count=3
candidate_only_rule_count=1
shared_rule_count=0
min_cross_distance_bp=254209
EOF

cat >"$WORK/frontier_full_safe.txt" <<'EOF'
input_mode=full
baseline_rows=8292
candidate_rows=8292
baseline_unique_rows=8292
candidate_unique_rows=8292
baseline_only_rows=0
candidate_only_rows=0
row_set_equal=1
frontier_key=chrom_strand_rule
frontier_safety=safe
frontier_changed_buckets=0
frontier_shared_changed_buckets=0
frontier_baseline_only_buckets=0
frontier_candidate_only_buckets=0
first_frontier_changed_bucket=
EOF

cat >"$WORK/frontier_diff_unsafe.txt" <<'EOF'
input_mode=diff_only
baseline_rows=3
candidate_rows=1
baseline_unique_rows=3
candidate_unique_rows=1
baseline_only_rows=3
candidate_only_rows=1
row_set_equal=0
frontier_key=chrom_strand_rule
frontier_safety=unsafe
frontier_changed_buckets=4
frontier_shared_changed_buckets=0
frontier_baseline_only_buckets=3
frontier_candidate_only_buckets=1
first_frontier_changed_bucket=chr1	ParaPlus	4
EOF

python3 "$CHECKER" \
  --authority-diff "$WORK/authority_diff.txt" \
  --frontier-full "$WORK/frontier_full_safe.txt" \
  --frontier-diff "$WORK/frontier_diff_unsafe.txt" \
  >"$WORK/decision.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/decision.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/decision.txt" >&2
    exit 1
  fi
}

require_line "current_real_prune_decision=no_go"
require_line "current_real_prune_row_set_equal=0"
require_line "current_real_prune_baseline_only_rows=3"
require_line "current_real_prune_candidate_only_rows=1"
require_line "current_real_prune_frontier_safety=unsafe"
require_line "future_frontier_full_mode_safety=safe"
require_line "future_frontier_full_mode_required=1"
require_line "diff_only_frontier_is_sufficient=0"
require_line "next_required_gate=task_local_frontier_full_mode_proof"
require_line "real_prune_may_be_enabled=0"

echo "ok"
