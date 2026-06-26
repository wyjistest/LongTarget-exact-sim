#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUMMARY="${SUMMARY:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr22_boundary/summary.tsv"}"

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

for threshold in ("116", "117"):
    if threshold not in rows:
        raise SystemExit(f"missing threshold row: {threshold}")

row116 = rows["116"]
if row116["top5_score_equal"] != "true":
    raise SystemExit("threshold 116 score top5 failed")
if row116["top5_stability_equal"] != "true":
    raise SystemExit("threshold 116 stability top5 failed")
if row116["top5_nt_score_equal"] != "true":
    raise SystemExit("threshold 116 nt_score top5 failed")
if int(float(row116["traceback_reduction"])) < 4_000_000:
    raise SystemExit("threshold 116 reduction is below expected chr22 signal")

row117 = rows["117"]
if row117["top5_stability_equal"] != "false":
    raise SystemExit("threshold 117 did not capture the expected stability boundary")

print(f"threshold116_wall={row116['wall_seconds']}")
print(f"threshold116_vs_baseline={row116['vs_baseline_gasal2_wall']}")
print(f"threshold116_traceback={row116['traceback_requests']}")
print(f"threshold116_reduction={row116['traceback_reduction']}")
print("threshold116_top5_score_equal=true")
print("threshold116_top5_stability_equal=true")
print("threshold116_top5_nt_score_equal=true")
print("threshold117_top5_stability_equal=false")
print("ok")
PY
