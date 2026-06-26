#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase5_archive_artifact"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-tfo-archive-integrity-parser \
  >"$WORK/integrity_parser.log"
make -C "$ROOT" check-fasim-gasal2-archive-manifest-parser \
  >"$WORK/manifest_parser.log"
make -C "$ROOT" check-fasim-gasal2-archive-first-output \
  WORK="$WORK/archive_first" \
  >"$WORK/archive_first.log"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/archive_first.log"; then
    echo "missing expected archive-first line: $expected" >&2
    cat "$WORK/archive_first.log" >&2
    exit 1
  fi
}

require_line "archive_first_requested=1"
require_line "archive_first_active=1"
require_line "archive_first_decision=active"
require_line "restored_equal=1"
require_line "legacy_only_rows=0"
require_line "archive_only_rows=0"
require_line "archive_manifest_valid=1"
require_line "restore_command_present=1"
require_line "restore_command_has_archive=1"
require_line "restore_command_has_output=1"
require_line "restore_command_has_query_fasta=1"
require_line "restore_command_has_target_fasta=1"
require_line "archive_manifest_decision=ready"
require_line "archive_magic=FATFOC1"
require_line "archive_version=2"
require_line "archive_terminator_present=1"

archive_bytes="$(
  awk -F= '$1 == "archive_bytes" { print $2 }' "$WORK/archive_first.log"
)"
restored_rows="$(
  awk -F= '$1 == "restored_rows" { print $2 }' "$WORK/archive_first.log"
)"
restore_wall="$(
  awk -F= '$1 == "restore_wall_seconds" { print $2 }' "$WORK/archive_first.log"
)"

python3 - "$archive_bytes" "$restored_rows" "$restore_wall" <<'PY'
import sys

archive_bytes = int(sys.argv[1])
restored_rows = int(sys.argv[2])
restore_wall = float(sys.argv[3])
if archive_bytes <= 0:
    raise SystemExit(f"archive_bytes must be positive, got {archive_bytes}")
if restored_rows <= 0:
    raise SystemExit(f"restored_rows must be positive, got {restored_rows}")
if restore_wall < 0:
    raise SystemExit(f"restore_wall_seconds must be non-negative, got {restore_wall}")
PY

echo "phase5_archive_artifact_gate=ready"
echo "archive_integrity_parser=pass"
echo "archive_manifest_parser=pass"
echo "archive_first_output=pass"
echo "archive_manifest_decision=ready"
echo "restored_equal=1"
echo "ok"
