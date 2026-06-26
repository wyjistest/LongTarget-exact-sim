#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_workload_matrix_parser"}"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_workload_matrix.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/matrix.tsv" <<'EOF'
workload	contract	scope	status	row_equal	top5_equal	speedup	fallbacks	scoreinfo_reduced	align_side_reduced	notes
chr22	full_output	claimed	pass	true	NA	1.09	0	false	false	full restored equality
chr21_chr22	top5_artifact	claimed	pass	NA	true	40.12	0	true	false	top5 artifact only
neat1_first64	long_query_boundary	unclaimed	fallback	NA	true	1.01	0	false	false	length guard
malat1_first8	long_query_boundary	blocked	fail	false	true	0.99	0	false	false	full output not equivalent
EOF

python3 "$PARSER" --matrix "$WORK/matrix.tsv" >"$WORK/summary.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "workloads=4"
require_line "claimed_workloads=2"
require_line "claimed_pass=2"
require_line "claimed_fail=0"
require_line "unclaimed_workloads=1"
require_line "blocked_workloads=1"
require_line "performance_claims_workload_specific=1"
require_line "broad_gate_rows=0"
require_line "broad_gate_rows_clean=0"
require_line "scoreinfo_reduced_claimed=1"
require_line "align_side_reduced_claimed=0"
require_line "decision=matrix_has_claimed_scope_only"
require_line "workload.chr22=claimed_pass"
require_line "workload.chr21_chr22=claimed_pass"
require_line "workload.neat1_first64=unclaimed_fallback"
require_line "workload.malat1_first8=blocked_fail"

echo "ok"
