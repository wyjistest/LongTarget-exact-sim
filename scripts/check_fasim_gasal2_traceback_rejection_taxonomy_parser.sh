#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_rejection_taxonomy_parser"}"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_traceback_rejection_taxonomy.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/taxonomy.tsv" <<'TSV'
attempt_id	task_id	scoreinfo_index	prealign_score	target_size	decision_bucket	pre_traceback_decidable	post_traceback_only	top5_only_safe_candidate	full_output_safe_candidate	emitted_row	final_row	output_global_start	output_global_end	score	nt	identity	stability	notes
1	0	0	120	75	retained_emitted	0	0	0	1	1	1	100	174	120	60	0.95	0.91	kept
2	0	1	88	60	filtered_nt	0	1	0	0	0	0	0	0	88	20	0.90	0.85	nt
3	0	2	70	55	filtered_score	1	0	1	1	0	0	0	0	70	45	0.92	0.88	score
4	1	0	130	80	final_sort_dedup_removed	0	1	0	0	1	0	200	279	130	70	0.96	0.93	dedup
5	1	1	95	65	unknown	0	0	0	0	0	0	0	0	95	50	0.91	0.87	unknown
TSV

python3 "$PARSER" \
  --taxonomy "$WORK/taxonomy.tsv" \
  --label synthetic \
  >"$WORK/summary.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "label=synthetic"
require_line "taxonomy_attempts=5"
require_line "taxonomy_known_attempts=4"
require_line "taxonomy_unknown_attempts=1"
require_line "pre_traceback_decidable_attempts=1"
require_line "post_traceback_only_attempts=2"
require_line "top5_only_safe_candidate_attempts=1"
require_line "full_output_safe_candidate_attempts=2"
require_line "emitted_attempts=2"
require_line "final_attempts=1"
require_line "rejected_attempts=4"
require_line "unknown_fraction=0.200000"
require_line $'retained_emitted\t1\t0.200000\t0.200000\t0\t0\t0\t1\tkept through emit/final output'
require_line $'filtered_score\t1\t0.200000\t0.200000\t1\t0\t1\t1\tbelow score/minScore threshold'
require_line $'filtered_nt\t1\t0.200000\t0.200000\t0\t1\t0\t0\tpost-CIGAR nt threshold'
require_line $'final_sort_dedup_removed\t1\t0.200000\t0.200000\t0\t1\t0\t0\tremoved by final sort/dedup'
require_line $'unknown\t1\t0.200000\t0.200000\t0\t0\t0\t0\tunclassified diagnostic bucket'

cat >"$WORK/stderr.log" <<'EOF'
benchmark.fasim_gasal2_traceback_rejection_taxonomy_requested=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_active=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_attempts=10
benchmark.fasim_gasal2_traceback_rejection_taxonomy_retained_emitted=2
benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_score=3
benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_identity=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_stability=0
benchmark.fasim_gasal2_traceback_rejection_taxonomy_filtered_nt=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_invalid_span_bound=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_duplicate_descriptor=0
benchmark.fasim_gasal2_traceback_rejection_taxonomy_duplicate_row=0
benchmark.fasim_gasal2_traceback_rejection_taxonomy_final_sort_dedup_removed=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_final_nonoverlap_dominated=0
benchmark.fasim_gasal2_traceback_rejection_taxonomy_top5_frontier_dominated=0
benchmark.fasim_gasal2_traceback_rejection_taxonomy_post_cigar_only=1
benchmark.fasim_gasal2_traceback_rejection_taxonomy_unknown=0
benchmark.fasim_gasal2_traceback_rejection_taxonomy_export_path=/tmp/taxonomy.tsv
benchmark.fasim_gasal2_traceback_rejection_taxonomy_export_rows=10
benchmark.fasim_gasal2_traceback_rejection_taxonomy_export_truncated=0
EOF

python3 "$PARSER" \
  --stderr "$WORK/stderr.log" \
  --label stderr \
  >"$WORK/stderr_summary.txt"

require_stderr_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/stderr_summary.txt"; then
    echo "missing expected stderr line: $expected" >&2
    cat "$WORK/stderr_summary.txt" >&2
    exit 1
  fi
}

require_stderr_line "label=stderr"
require_stderr_line "taxonomy_attempts=10"
require_stderr_line "taxonomy_known_attempts=10"
require_stderr_line "taxonomy_unknown_attempts=0"
require_stderr_line "pre_traceback_decidable_attempts=4"
require_stderr_line "post_traceback_only_attempts=4"
require_stderr_line "top5_only_safe_candidate_attempts=4"
require_stderr_line "full_output_safe_candidate_attempts=6"
require_stderr_line "emitted_attempts=3"
require_stderr_line "final_attempts=2"
require_stderr_line "rejected_attempts=8"
require_stderr_line "unknown_fraction=0.000000"
require_stderr_line $'post_cigar_only\t1\t0.100000\t0.100000\t0\t1\t0\t0\trequires CIGAR/traceback before classification'

echo "ok"
