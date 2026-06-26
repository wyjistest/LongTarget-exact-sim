#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase6_workload_matrix"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-workload-matrix-parser \
  >"$WORK/workload_matrix_parser.log"
make -C "$ROOT" check-fasim-gasal2-workload-matrix \
  >"$WORK/workload_matrix.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/workload_matrix_parser.log" "ok"
require_line "$WORK/workload_matrix.log" "workloads=7"
require_line "$WORK/workload_matrix.log" "claimed_workloads=4"
require_line "$WORK/workload_matrix.log" "claimed_pass=4"
require_line "$WORK/workload_matrix.log" "claimed_fail=0"
require_line "$WORK/workload_matrix.log" "unclaimed_workloads=2"
require_line "$WORK/workload_matrix.log" "blocked_workloads=1"
require_line "$WORK/workload_matrix.log" "performance_claims_workload_specific=1"
require_line "$WORK/workload_matrix.log" "broad_gate_rows=0"
require_line "$WORK/workload_matrix.log" "broad_gate_rows_clean=0"
require_line "$WORK/workload_matrix.log" "scoreinfo_reduced_claimed=2"
require_line "$WORK/workload_matrix.log" "align_side_reduced_claimed=0"
require_line "$WORK/workload_matrix.log" "decision=matrix_has_claimed_scope_only"

echo "phase6_workload_matrix_gate=claimed_scope_only"
echo "workload_matrix_parser=pass"
echo "claimed_workloads=4"
echo "claimed_pass=4"
echo "claimed_fail=0"
echo "broad_gate_rows_clean=0"
echo "align_side_reduced_claimed=0"
echo "decision=matrix_has_claimed_scope_only"
echo "ok"
