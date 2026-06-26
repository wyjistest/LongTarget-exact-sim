#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase2_equivalence_first_convert"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-convert-cpu-breakdown \
  WORK="$WORK/convert_cpu_breakdown" \
  >"$WORK/convert_cpu_breakdown.log"
make -C "$ROOT" check-fasim-gasal2-equivalence-first-convert \
  WORK="$WORK/equivalence_first" \
  >"$WORK/equivalence_first.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/equivalence_first.log" "equivalence_first_requested=1"
require_line "$WORK/equivalence_first.log" "equivalence_first_active=1"
require_line "$WORK/equivalence_first.log" "equivalence_first_decision=active"
require_line "$WORK/equivalence_first.log" "restored_equal=1"
require_line "$WORK/equivalence_first.log" "legacy_only_rows=0"
require_line "$WORK/equivalence_first.log" "new_only_rows=0"

convert_speedup="$(
  awk -F= '$1 == "convert_wall_speedup" { print $2 }' "$WORK/equivalence_first.log"
)"
legacy_rows="$(
  awk -F= '$1 == "legacy_restored_rows" { print $2 }' "$WORK/equivalence_first.log"
)"
new_rows="$(
  awk -F= '$1 == "new_restored_rows" { print $2 }' "$WORK/equivalence_first.log"
)"

python3 - "$convert_speedup" "$legacy_rows" "$new_rows" <<'PY'
import sys

speedup = float(sys.argv[1])
legacy_rows = int(sys.argv[2])
new_rows = int(sys.argv[3])
if speedup <= 1.0:
    raise SystemExit(f"convert_wall_speedup must be > 1.0, got {speedup}")
if legacy_rows <= 0 or new_rows <= 0:
    raise SystemExit(
        f"restored row counts must be positive, got legacy={legacy_rows} new={new_rows}"
    )
if legacy_rows != new_rows:
    raise SystemExit(
        f"restored row counts differ: legacy={legacy_rows} new={new_rows}"
    )
PY

echo "phase2_equivalence_first_convert_gate=ready"
echo "convert_cpu_breakdown=pass"
echo "equivalence_first_convert=pass"
echo "restored_equal=1"
echo "legacy_only_rows=0"
echo "new_only_rows=0"
echo "convert_wall_speedup_gt_1=1"
echo "ok"
