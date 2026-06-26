#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAX4="${MAX4:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full"}"
MAX8="${MAX8:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full_max8"}"
DOC="$ROOT/docs/fasim_gasal2_segmented_query_kcnq1ot1_coverage_ladder.md"
MAKEFILE="$ROOT/Makefile"

for path in "$MAX4/summary.txt" "$MAX8/summary.txt" "$MAX8/offline_cluster_grid_compare_details.tsv" "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing KCNQ1OT1 coverage-ladder dependency: $path" >&2
    exit 1
  fi
done

python3 - "$MAX4" "$MAX8" "$DOC" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

max4 = Path(sys.argv[1])
max8 = Path(sys.argv[2])
doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

def read_summary(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in (path / "summary.txt").read_text(encoding="utf-8").splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            result[key] = value
    return result

def wall_sum(path: Path) -> float:
    return sum(float(p.read_text().strip()) for p in sorted(path.glob("grids/shift_*/run_*/wall_seconds.txt")))

def artifact_mb(path: Path) -> int:
    out = subprocess.check_output(["du", "-sm", str(path)], text=True)
    return int(out.split()[0])

s4 = read_summary(max4)
s8 = read_summary(max8)

for label, summary, expected_segments in (
    ("max4", s4, "4"),
    ("max8", s8, "8"),
):
    if summary.get("decision") != "segmented_query_kcnq1ot1_pilot_grid_stable":
        raise SystemExit(f"{label} not grid-stable: {summary}")
    if summary.get("top5_offline_cluster_equal") != "true":
        raise SystemExit(f"{label} clustered top5 not equal: {summary}")
    if summary.get("top5_offline_cluster_overlap") != "5":
        raise SystemExit(f"{label} clustered top5 overlap not 5: {summary}")
    if summary.get("gasal2_fallbacks") != "0" or summary.get("length_guard_fallbacks") != "0":
        raise SystemExit(f"{label} fallback nonzero: {summary}")
    if summary.get("shift_0_segments") != expected_segments or summary.get("shift_256_segments") != expected_segments:
        raise SystemExit(f"{label} unexpected segment count: {summary}")

if int(s8["gasal2_requests"]) <= int(s4["gasal2_requests"]):
    raise SystemExit("max8 requests should exceed max4 requests")
if int(s8["gasal2_traceback_requests"]) <= int(s4["gasal2_traceback_requests"]):
    raise SystemExit("max8 traceback requests should exceed max4 traceback requests")
if wall_sum(max8) <= wall_sum(max4):
    raise SystemExit("max8 wall sum should exceed max4 wall sum")
if artifact_mb(max8) <= artifact_mb(max4):
    raise SystemExit("max8 artifact should exceed max4 artifact")

detail_rows = list(csv.DictReader((max8 / "offline_cluster_grid_compare_details.tsv").open(newline="", encoding="utf-8"), delimiter="\t"))
if len(detail_rows) != 10:
    raise SystemExit(f"expected 10 max8 clustered detail rows, got {len(detail_rows)}")

for phrase in (
    "KCNQ1OT1 Coverage Ladder",
    "max_segments | total_segments",
    "151666259",
    "303560481",
    "~2.30B",
    "~121",
    "Full query coverage",
    "extrapolated only",
    "not claimed",
    "output reduction or offline per-segment topK sensitivity",
):
    if phrase not in doc:
        raise SystemExit(f"coverage ladder doc missing phrase: {phrase}")

for phrase in (
    "check-fasim-gasal2-segmented-query-kcnq1ot1-coverage-ladder-result:",
    "scripts/check_fasim_gasal2_segmented_query_kcnq1ot1_coverage_ladder_result.sh",
):
    if phrase not in makefile:
        raise SystemExit(f"Makefile missing phrase: {phrase}")
PY

echo "GASAL2 segmented-query KCNQ1OT1 coverage ladder OK"
