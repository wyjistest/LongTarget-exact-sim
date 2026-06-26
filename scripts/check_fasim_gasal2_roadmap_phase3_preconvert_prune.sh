#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase3_preconvert_prune"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-convert-funnel-parser \
  WORK="$WORK/convert_funnel" \
  >"$WORK/convert_funnel.log"
make -C "$ROOT" check-fasim-gasal2-prune-authority-diff-parser \
  WORK="$WORK/prune_authority_diff" \
  >"$WORK/prune_authority_diff.log"
make -C "$ROOT" check-fasim-gasal2-prune-frontier-safety-parser \
  WORK="$WORK/prune_frontier_safety" \
  >"$WORK/prune_frontier_safety.log"
make -C "$ROOT" check-fasim-gasal2-preconvert-prune-readiness \
  WORK="$WORK/preconvert_prune_readiness" \
  >"$WORK/preconvert_prune_readiness.log"
make -C "$ROOT" check-fasim-gasal2-task-frontier-proof-parser \
  WORK="$WORK/task_frontier_parser" \
  >"$WORK/task_frontier_parser.log"
make -C "$ROOT" check-fasim-gasal2-preconvert-prune-shadow \
  WORK="$WORK/preconvert_prune_shadow" \
  >"$WORK/preconvert_prune_shadow.log"
make -C "$ROOT" check-fasim-gasal2-task-frontier-proof-export \
  WORK="$WORK/task_frontier_export" \
  >"$WORK/task_frontier_export.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/preconvert_prune_readiness.log" "ok"
require_line "$WORK/task_frontier_parser.log" "ok"
require_line "$WORK/preconvert_prune_shadow.log" "preconvert_prune_shadow_requested=1"
require_line "$WORK/preconvert_prune_shadow.log" "preconvert_prune_shadow_active=1"
require_line "$WORK/preconvert_prune_shadow.log" "preconvert_prune_shadow_false_negatives=0"
require_line "$WORK/task_frontier_export.log" "broad_path_cpu_triplexes=60"
require_line "$WORK/task_frontier_export.log" "real_export_same_gate=pass"
require_line "$WORK/task_frontier_export.log" "real_export_removed_row_gate=fail_as_expected"

python3 "$ROOT/scripts/decide_fasim_gasal2_preconvert_prune_readiness.py" \
  --authority-diff "$WORK/preconvert_prune_readiness/authority_diff.txt" \
  --frontier-full "$WORK/preconvert_prune_readiness/frontier_full_safe.txt" \
  --frontier-diff "$WORK/preconvert_prune_readiness/frontier_diff_unsafe.txt" \
  >"$WORK/phase3_decision.txt"

require_line "$WORK/phase3_decision.txt" "current_real_prune_decision=no_go"
require_line "$WORK/phase3_decision.txt" "current_real_prune_row_set_equal=0"
require_line "$WORK/phase3_decision.txt" "current_real_prune_frontier_safety=unsafe"
require_line "$WORK/phase3_decision.txt" "next_required_gate=task_local_frontier_full_mode_proof"
require_line "$WORK/phase3_decision.txt" "real_prune_may_be_enabled=0"

echo "phase3_preconvert_prune_gate=not_ready_current_prune_no_go"
echo "convert_funnel_parser=pass"
echo "preconvert_prune_shadow=pass"
echo "preconvert_prune_readiness=pass"
echo "task_frontier_proof_parser=pass"
echo "task_frontier_proof_export=pass"
echo "current_real_prune_decision=no_go"
echo "real_prune_may_be_enabled=0"
echo "next_required_gate=task_local_frontier_full_mode_proof"
echo "ok"
