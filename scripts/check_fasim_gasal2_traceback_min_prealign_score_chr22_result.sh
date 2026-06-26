#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUMMARY="${SUMMARY:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr22/summary.tsv"}"

if [[ ! -s "$SUMMARY" ]]; then
  echo "missing summary: $SUMMARY" >&2
  exit 1
fi

python3 - "$SUMMARY" <<'PY'
import csv
import sys
from pathlib import Path

summary = Path(sys.argv[1])
rows = {}
with summary.open(newline="") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        rows[row["threshold"]] = row

for threshold in ("80", "90", "100"):
    if threshold not in rows:
        raise SystemExit(f"missing threshold row: {threshold}")
    row = rows[threshold]
    for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
        if row[key] != "true":
            raise SystemExit(f"threshold {threshold} failed {key}: {row[key]}")
    if int(float(row["traceback_reduction"])) <= 0:
        raise SystemExit(f"threshold {threshold} did not reduce traceback")

row100 = rows["100"]
if int(float(row100["traceback_reduction"])) < 2_000_000:
    raise SystemExit("threshold 100 reduction is below expected chr22 signal")
if float(row100["vs_baseline_gasal2_wall"]) >= 1.0:
    raise SystemExit("threshold 100 did not beat baseline GASAL2 wall")

print(f"threshold100_wall={row100['wall_seconds']}")
print(f"threshold100_vs_baseline={row100['vs_baseline_gasal2_wall']}")
print(f"threshold100_traceback={row100['traceback_requests']}")
print(f"threshold100_reduction={row100['traceback_reduction']}")
print("top5_score_equal=true")
print("top5_stability_equal=true")
print("top5_nt_score_equal=true")
print("ok")
PY
