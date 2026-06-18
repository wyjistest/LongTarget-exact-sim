#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_pretraceback_pruning_eligibility_parser"}"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/stderr.log" <<'EOF'
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_requested=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_active=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_attempts=10
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_retained_final_rows=2
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_removed_attempts=8
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_mapped_removed_attempts=3
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_unmapped_removed_attempts=5
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_exact_request_duplicate=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_exact_descriptor_duplicate=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_same_final_row_different_descriptor=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cross_flush_exact_duplicate=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cigar_dependent_duplicate=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_representative_selection_dependent=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_sort_or_dominance_removed=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_pretraceback_span_provable=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_reverse_start_dependent_span=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cigar_dependent_span=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_unknown=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_false_prune_shadow=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_missing_rows_shadow=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_extra_rows_shadow=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_export_path=/tmp/eligibility.tsv
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_export_rows=10
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_export_truncated=0
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
require_stderr_line "eligibility_attempts=10"
require_stderr_line "retained_final_rows=2"
require_stderr_line "removed_attempts=8"
require_stderr_line "mapped_removed_attempts=3"
require_stderr_line "unmapped_removed_attempts=5"
require_stderr_line "known_eligibility_attempts=7"
require_stderr_line "unknown_eligibility_attempts=1"
require_stderr_line "pre_traceback_decidable_attempts=3"
require_stderr_line "post_traceback_only_attempts=4"
require_stderr_line "top5_only_safe_candidate_attempts=3"
require_stderr_line "full_output_safe_candidate_attempts=0"
require_stderr_line "false_prune_shadow=0"
require_stderr_line "missing_rows_shadow=0"
require_stderr_line "extra_rows_shadow=0"
require_stderr_line "unknown_fraction=0.125000"
require_stderr_line $'exact_request_duplicate\t1\t0.100000\t0.125000\t1\t1\t0\t1\t0\t0\t0\t0\tsame pre-traceback request as representative'
require_stderr_line $'cigar_dependent_span\t1\t0.100000\t0.125000\t0\t0\t1\t0\t0\t0\t0\t0\tspan rejection depends on traceback endpoints/CIGAR'
require_stderr_line $'unknown\t1\t0.100000\t0.125000\t0\t0\t0\t0\t0\t0\t0\t0\tunclassified eligibility bucket'

cat >"$WORK/eligibility.tsv" <<'TSV'
attempt_id	flush_id	task_id	scoreinfo_index	prealign_score	query_len	target_size	target_start	cutlength	request_key_hash	descriptor_key_hash	final_row_hash	representative_attempt_id	representative_flush_id	representative_request_key_hash	representative_descriptor_key_hash	same_flush	cross_flush	score	query_begin	query_end	ref_begin	ref_end	output_global_start	output_global_end	nt	identity	stability	cigar_hash	final_rejection_bucket	eligibility_bucket	pre_traceback_decidable	post_traceback_only	top5_only_safe_candidate	full_output_safe_candidate	notes
1	1	0	0	120	2800	80	10	80	req1	desc1	row1	1	1	req1	desc1	1	0	120	0	70	0	79	100	179	70	0.95	0.9	cig1	retained_emitted	representative_selection_dependent	0	0	0	1	kept
2	1	0	0	120	2800	80	10	80	req1	desc1	row1	1	1	req1	desc1	1	0	120	0	70	0	79	100	179	70	0.95	0.9	cig1	final_sort_dedup_removed	exact_request_duplicate	1	0	1	0	duplicate
3	1	0	1	90	2800	20	20	20	req2	desc2	0	0	0	0	0	0	0	90	0	10	0	10	0	0	0	0	0	cig2	invalid_span_bound	pretraceback_span_provable	1	0	1	0	span
4	1	0	2	80	2800	60	30	60	req3	desc3	0	0	0	0	0	0	0	80	0	20	0	20	0	0	0	0	0	cig3	post_cigar_only	cigar_dependent_duplicate	0	1	0	0	cigar
TSV

python3 "$PARSER" \
  --eligibility "$WORK/eligibility.tsv" \
  --label tsv \
  >"$WORK/tsv_summary.txt"

require_tsv_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/tsv_summary.txt"; then
    echo "missing expected TSV line: $expected" >&2
    cat "$WORK/tsv_summary.txt" >&2
    exit 1
  fi
}

require_tsv_line "label=tsv"
require_tsv_line "eligibility_attempts=4"
require_tsv_line "retained_final_rows=1"
require_tsv_line "removed_attempts=3"
require_tsv_line "mapped_removed_attempts=1"
require_tsv_line "unmapped_removed_attempts=2"
require_tsv_line "known_eligibility_attempts=3"
require_tsv_line "unknown_eligibility_attempts=0"
require_tsv_line "pre_traceback_decidable_attempts=2"
require_tsv_line "post_traceback_only_attempts=1"
require_tsv_line "top5_only_safe_candidate_attempts=2"
require_tsv_line "full_output_safe_candidate_attempts=0"
require_tsv_line $'pretraceback_span_provable\t1\t0.250000\t0.333333\t0\t1\t0\t1\t0\t0\t0\t0\tspan rejection provable before traceback'

echo "ok"
