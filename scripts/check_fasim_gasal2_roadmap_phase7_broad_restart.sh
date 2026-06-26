#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase7_broad_restart"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-roadmap-broad-restart-gate \
  >"$WORK/broad_restart_gate.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/broad_restart_gate.log" "roadmap_broad_restart_gate=current_architecture_no_go"
require_line "$WORK/broad_restart_gate.log" "broad_objective_status=open"
require_line "$WORK/broad_restart_gate.log" "broad_restart_required=1"
require_line "$WORK/broad_restart_gate.log" "broad_gate_rows_clean=0"
require_line "$WORK/broad_restart_gate.log" "forbidden_restarts_checked=1"
require_line "$WORK/broad_restart_gate.log" "phase7_next_architecture_required=1"
require_line "$WORK/broad_restart_gate.log" "must_not_call_update_goal_complete=1"

echo "phase7_broad_restart_gate=current_architecture_no_go"
echo "roadmap_broad_restart_gate=pass"
echo "broad_objective_status=open"
echo "broad_restart_required=1"
echo "broad_gate_rows_clean=0"
echo "phase7_next_architecture_required=1"
echo "must_not_call_update_goal_complete=1"
echo "ok"
