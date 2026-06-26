#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_task_frontier_proof_export"}"
EXPORT_CHECK="$ROOT/scripts/check_fasim_gasal2_broad_scoreinfo_consumer_triplex_export.sh"
ANALYZER="$ROOT/scripts/analyze_fasim_gasal2_task_frontier_proof.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -f "$EXPORT_CHECK" ]]; then
  echo "missing broad CPU triplex export check: $EXPORT_CHECK" >&2
  exit 1
fi
if [[ ! -f "$ANALYZER" ]]; then
  echo "missing task frontier proof analyzer: $ANALYZER" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

BUILD_BIN=0 \
BIN="$BIN" \
WORK="$WORK/export" \
  bash "$EXPORT_CHECK" >"$WORK/export_summary.txt"

triplex_path="$(
  awk -F= '$1 == "broad_path_cpu_triplex_path" { print $2 }' \
    "$WORK/export_summary.txt"
)"
triplexes="$(
  awk -F= '$1 == "broad_path_cpu_triplexes" { print $2 }' \
    "$WORK/export_summary.txt"
)"

if [[ -z "$triplex_path" ]]; then
  echo "broad_path_cpu_triplex_path missing from export summary" >&2
  cat "$WORK/export_summary.txt" >&2
  exit 1
fi
if [[ ! -f "$triplex_path" ]]; then
  echo "missing exported broad CPU triplex file: $triplex_path" >&2
  cat "$WORK/export_summary.txt" >&2
  exit 1
fi
if [[ -z "$triplexes" || "$triplexes" -le 0 ]]; then
  echo "expected positive broad_path_cpu_triplexes, got: ${triplexes:-missing}" >&2
  cat "$WORK/export_summary.txt" >&2
  exit 1
fi

python3 "$ANALYZER" \
  --baseline "$triplex_path" \
  --candidate "$triplex_path" \
  >"$WORK/same_summary.txt"

python3 - "$triplex_path" "$WORK/one_row_removed.tsv" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1])
dest = Path(sys.argv[2])
lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
if len(lines) <= 1:
    raise SystemExit(f"not enough rows to create negative candidate: {source}")
dest.write_text("\n".join([lines[0], *lines[2:]]) + "\n", encoding="utf-8")
PY

python3 "$ANALYZER" \
  --baseline "$triplex_path" \
  --candidate "$WORK/one_row_removed.tsv" \
  >"$WORK/removed_summary.txt"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/same_summary.txt" "input_mode=task_triplex_full"
require_line "$WORK/same_summary.txt" "task_row_set_equal=1"
require_line "$WORK/same_summary.txt" "task_frontier_safety=safe"
require_line "$WORK/same_summary.txt" "changed_tasks=0"
require_line "$WORK/same_summary.txt" "baseline_only_rows=0"
require_line "$WORK/same_summary.txt" "candidate_only_rows=0"
require_line "$WORK/same_summary.txt" "real_prune_proof_gate=pass"

require_line "$WORK/removed_summary.txt" "input_mode=task_triplex_full"
require_line "$WORK/removed_summary.txt" "task_row_set_equal=0"
require_line "$WORK/removed_summary.txt" "task_frontier_safety=unsafe"
require_line "$WORK/removed_summary.txt" "baseline_only_rows=1"
require_line "$WORK/removed_summary.txt" "candidate_only_rows=0"
require_line "$WORK/removed_summary.txt" "real_prune_proof_gate=fail"

echo "broad_path_cpu_triplex_path=$triplex_path"
echo "broad_path_cpu_triplexes=$triplexes"
echo "real_export_same_gate=pass"
echo "real_export_removed_row_gate=fail_as_expected"
echo "ok"
