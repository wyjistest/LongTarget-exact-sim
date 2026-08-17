#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_h19_control"}"
SUMMARY="$WORK/summary.txt"
DETAILS="$WORK/offline_cluster_top5_details.tsv"
DOC="$ROOT/docs/fasim_gasal2_segmented_query_h19_control.md"
RUNNER="$ROOT/scripts/characterize_fasim_gasal2_segmented_query_h19_control.sh"
MERGER="$ROOT/scripts/merge_fasim_segmented_tfosorted.py"
MAKEFILE="$ROOT/Makefile"

for path in "$SUMMARY" "$DETAILS" "$DOC" "$RUNNER" "$MERGER" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing segmented-query H19 dependency: $path" >&2
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

required = {
    "decision": "segmented_query_h19_control_clean",
    "top5_offline_cluster_equal": "true",
    "top5_offline_cluster_overlap": "5",
    "gasal2_fallbacks": "0",
    "length_guard_fallbacks": "0",
}
for key, expected in required.items():
    if summary.get(key) != expected:
        raise SystemExit(f"unexpected {key}: {summary}")

if int(summary.get("segment_count", "0")) < 2:
    raise SystemExit(f"segmentation control should use at least two segments: {summary}")
if int(summary.get("segment_len", "0")) > 2812:
    raise SystemExit(f"segment length exceeds current GASAL2 contract: {summary}")
if int(summary.get("max_query_span", "0")) <= 0:
    raise SystemExit(f"missing derived query span: {summary}")
if int(summary.get("actual_overlap_max", "0")) <= 0:
    raise SystemExit(f"missing actual segment overlap: {summary}")
if int(summary.get("output_rows", "0")) <= 0:
    raise SystemExit(f"merged output is empty: {summary}")
if int(summary.get("gasal2_requests", "0")) <= 0:
    raise SystemExit(f"missing GASAL2 requests: {summary}")

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
    "Segmented-Query H19 Control",
    "restore segment-local QueryStart/QueryEnd to global RNA coordinates",
    "clustered TFO1-TFO5",
    "not an unsegmented full-length KCNQ1OT1 claim",
    "make characterize-fasim-gasal2-segmented-query-h19-control",
):
    if phrase not in doc:
        raise SystemExit(f"segmented-query H19 doc missing phrase: {phrase}")

for phrase in (
    "characterize-fasim-gasal2-segmented-query-h19-control:",
    "check-fasim-gasal2-segmented-query-h19-control-result:",
    "scripts/check_fasim_gasal2_segmented_query_h19_control_result.sh",
):
    if phrase not in makefile:
        raise SystemExit(f"Makefile missing phrase: {phrase}")
PY

echo "GASAL2 segmented-query H19 control OK"
