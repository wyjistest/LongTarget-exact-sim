#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_archive_manifest_parser"}"
CHECKER="$ROOT/scripts/check_fasim_gasal2_archive_manifest.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/manifest.tsv" <<'EOF'
archive_manifest_schema	FASIM_TFO_ARCHIVE_MANIFEST_V1
archive_path	out/sample.archive-first.tfoa
archive_sha256	aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
archive_magic	FATFOC1
archive_version	2
archive_terminator_present	1
query_fasta_path	H19.fa
query_fasta_sha256	bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
target_fasta_path	chr22.fa
target_fasta_sha256	cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
restored_output_path	out/sample.restored-TFOsorted
restored_sha256	dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
restore_command	python3 scripts/restore_fasim_tfosorted_column_archive_probe.py --archive out/sample.archive-first.tfoa --output out/sample.restored-TFOsorted --query-fasta H19.fa --target-fasta chr22.fa
restore_rows	8291
archive_bytes	321411
restored_bytes	1836889
EOF

python3 "$CHECKER" --manifest "$WORK/manifest.tsv" >"$WORK/summary.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "archive_manifest_schema=FASIM_TFO_ARCHIVE_MANIFEST_V1"
require_line "archive_manifest_valid=1"
require_line "archive_version=2"
require_line "archive_terminator_present=1"
require_line "restore_command_present=1"
require_line "restore_command_has_archive=1"
require_line "restore_command_has_output=1"
require_line "restore_command_has_query_fasta=1"
require_line "restore_command_has_target_fasta=1"
require_line "archive_sha256_valid=1"
require_line "query_fasta_sha256_valid=1"
require_line "target_fasta_sha256_valid=1"
require_line "restored_sha256_valid=1"
require_line "required_paths_present=1"
require_line "archive_manifest_decision=ready"

cat >"$WORK/bad_manifest.tsv" <<'EOF'
archive_manifest_schema	FASIM_TFO_ARCHIVE_MANIFEST_V1
archive_path	out/sample.archive-first.tfoa
archive_sha256	not-a-sha
archive_magic	FATFOC1
archive_version	2
archive_terminator_present	1
query_fasta_path	H19.fa
query_fasta_sha256	bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
target_fasta_path	chr22.fa
target_fasta_sha256	cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
restored_output_path	out/sample.restored-TFOsorted
restored_sha256	dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
restore_command	python3 scripts/restore_fasim_tfosorted_column_archive_probe.py --archive out/sample.archive-first.tfoa
restore_rows	8291
archive_bytes	321411
restored_bytes	1836889
EOF

if python3 "$CHECKER" --manifest "$WORK/bad_manifest.tsv" >"$WORK/bad_summary.txt"; then
  echo "expected malformed manifest to fail" >&2
  cat "$WORK/bad_summary.txt" >&2
  exit 1
fi

grep -Fxq "archive_manifest_valid=0" "$WORK/bad_summary.txt"
grep -Fxq "archive_manifest_decision=invalid" "$WORK/bad_summary.txt"

echo "ok"
