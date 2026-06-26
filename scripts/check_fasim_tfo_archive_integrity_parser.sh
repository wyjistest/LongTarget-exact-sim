#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_tfo_archive_integrity_parser"}"
CHECKER="$ROOT/scripts/check_fasim_tfo_archive_integrity.py"

rm -rf "$WORK"
mkdir -p "$WORK"

printf '>q\nACGT\n' >"$WORK/query.fa"
printf '>t\nACGTACGT\n' >"$WORK/target.fa"
printf 'rows=2\ndictionary_payloads=2\nrestored_bytes=12\n' >"$WORK/restore.log"
printf 'restored\nrow\n' >"$WORK/restored-TFOsorted"
python3 - <<'PY' >"$WORK/archive.tfoa"
import struct
import sys
sys.stdout.buffer.write(b"FATFOC1\0")
sys.stdout.buffer.write(struct.pack("<II", 2, 0))
sys.stdout.buffer.write(struct.pack("<I", 0))
PY

python3 "$CHECKER" \
  --archive "$WORK/archive.tfoa" \
  --query-fasta "$WORK/query.fa" \
  --target-fasta "$WORK/target.fa" \
  --restore-log "$WORK/restore.log" \
  --restored-output "$WORK/restored-TFOsorted" \
  >"$WORK/summary.txt"

require_prefix() {
  local prefix="$1"
  if ! grep -Eq "^${prefix}" "$WORK/summary.txt"; then
    echo "missing expected prefix: $prefix" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "archive_magic=FATFOC1"
require_line "archive_version=2"
require_line "archive_block_rows=0"
require_line "archive_terminator_present=1"
require_line "query_bases=4"
require_line "target_bases=8"
require_line "restore_rows=2"
require_line "restore_dictionary_payloads=2"
require_line "restore_reported_bytes=12"
require_line "restored_bytes=13"
require_prefix "archive_sha256=[0-9a-f]{64}$"
require_prefix "query_fasta_sha256=[0-9a-f]{64}$"
require_prefix "target_fasta_sha256=[0-9a-f]{64}$"
require_prefix "restored_sha256=[0-9a-f]{64}$"

echo "ok"
