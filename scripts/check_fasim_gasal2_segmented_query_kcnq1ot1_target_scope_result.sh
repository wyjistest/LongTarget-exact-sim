#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full"}"
SUMMARY="$WORK/summary.txt"
DETAILS="$WORK/offline_cluster_grid_compare_details.tsv"
DOC="$ROOT/docs/fasim_gasal2_segmented_query_kcnq1ot1_target_scope.md"
MERGER="$ROOT/scripts/merge_fasim_segmented_tfosorted.py"
MAKEFILE="$ROOT/Makefile"

for path in "$SUMMARY" "$DETAILS" "$DOC" "$MERGER" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing KCNQ1OT1 target-scope dependency: $path" >&2
    exit 1
  fi
done

python3 - "$SUMMARY" "$DETAILS" "$DOC" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
details_path = Path(sys.argv[2])
doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

summary: dict[str, str] = {}
for raw in summary_path.read_text(encoding="utf-8").splitlines():
    if "=" in raw:
        key, value = raw.split("=", 1)
        summary[key] = value

for key, expected in (
    ("decision", "segmented_query_kcnq1ot1_pilot_grid_stable"),
    ("top5_offline_cluster_equal", "true"),
    ("top5_offline_cluster_overlap", "5"),
    ("gasal2_fallbacks", "0"),
    ("length_guard_fallbacks", "0"),
):
    if summary.get(key) != expected:
        raise SystemExit(f"unexpected {key}: {summary}")

if int(summary.get("query_len", "0")) != 91667:
    raise SystemExit(f"unexpected query length: {summary}")
if int(summary.get("segment_len", "0")) > 2812:
    raise SystemExit(f"segment length exceeds verified contract: {summary}")
if int(summary.get("gasal2_requests", "0")) <= 100000000:
    raise SystemExit(f"target-scope run does not look like chr22 full: {summary}")
if int(summary.get("shift_0_output_rows", "0")) <= 500000:
    raise SystemExit(f"shift 0 output too small for chr22 full: {summary}")
if int(summary.get("shift_256_output_rows", "0")) <= 500000:
    raise SystemExit(f"shift 256 output too small for chr22 full: {summary}")

detail_rows = list(csv.DictReader(details_path.open(newline="", encoding="utf-8"), delimiter="\t"))
if len(detail_rows) != 10:
    raise SystemExit(f"expected 10 clustered top5 detail rows, got {len(detail_rows)}")
baseline = [row for row in detail_rows if row["side"] == "baseline"]
candidate = [row for row in detail_rows if row["side"] == "candidate"]
if len(baseline) != 5 or len(candidate) != 5:
    raise SystemExit("clustered detail rows should contain five baseline and five candidate rows")

key_columns = [
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "Strand",
    "Rule",
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Score",
    "Nt(bp)",
    "MeanIdentity(%)",
    "MeanStability",
]
for left, right in zip(baseline, candidate):
    for column in key_columns:
        if left[column] != right[column]:
            raise SystemExit(f"clustered top5 details differ at {column}: {left} vs {right}")

for phrase in (
    "Segmented KCNQ1OT1 Target-Scope Expansion",
    "full chr22 target",
    "shifted-grid clustered TFO1-TFO5 stability on chr22 full",
    "not full-length KCNQ1OT1 genome-wide validation",
    "top5_offline_cluster_equal = true",
):
    if phrase not in doc:
        raise SystemExit(f"target-scope doc missing phrase: {phrase}")

for phrase in (
    "check-fasim-gasal2-segmented-query-kcnq1ot1-target-scope-result:",
    "scripts/check_fasim_gasal2_segmented_query_kcnq1ot1_target_scope_result.sh",
):
    if phrase not in makefile:
        raise SystemExit(f"Makefile missing phrase: {phrase}")
PY

echo "GASAL2 segmented-query KCNQ1OT1 target scope OK"
