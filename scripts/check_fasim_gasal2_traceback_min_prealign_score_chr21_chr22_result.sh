#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHR21_SUMMARY="${CHR21_SUMMARY:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr21/summary.tsv"}"
MERGE_DIR="${MERGE_DIR:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr21_chr22_merge"}"
COMPARE_116="${COMPARE_116:-"$MERGE_DIR/compare_116.txt"}"
COMPARE_117="${COMPARE_117:-"$MERGE_DIR/compare_117.txt"}"

for path in "$CHR21_SUMMARY" "$COMPARE_116" "$COMPARE_117"; do
  if [[ ! -s "$path" ]]; then
    echo "missing result dependency: $path" >&2
    exit 1
  fi
done

python3 - "$CHR21_SUMMARY" "$COMPARE_116" "$COMPARE_117" <<'PY'
import csv
import sys
from pathlib import Path

chr21_summary = Path(sys.argv[1])
compare_116 = Path(sys.argv[2])
compare_117 = Path(sys.argv[3])


def read_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


rows = {}
with chr21_summary.open(newline="", encoding="utf-8") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        rows[row["threshold"]] = row

for threshold in ("0", "116", "117"):
    if threshold not in rows:
        raise SystemExit(f"missing chr21 threshold row: {threshold}")

base = rows["0"]
row116 = rows["116"]
row117 = rows["117"]

base_wall = float(base["wall_seconds"])
base_traceback = int(base["traceback_requests"])
if base_wall <= 0:
    raise SystemExit("chr21 threshold 0 wall must be positive")
if base_traceback <= 0:
    raise SystemExit("chr21 threshold 0 traceback must be positive")

for label, row in (("116", row116), ("117", row117)):
    wall = float(row["wall_seconds"])
    traceback = int(row["traceback_requests"])
    if wall <= 0:
        raise SystemExit(f"chr21 threshold {label} wall must be positive")
    if traceback >= base_traceback:
        raise SystemExit(f"chr21 threshold {label} did not reduce traceback")
    if wall >= base_wall:
        raise SystemExit(f"chr21 threshold {label} did not beat threshold 0 wall")

merged116 = read_kv(compare_116)
merged117 = read_kv(compare_117)

for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    if merged116.get(key) != "true":
        raise SystemExit(f"merged threshold 116 failed {key}: {merged116.get(key)}")

if merged117.get("top5_score_equal") != "true":
    raise SystemExit("merged threshold 117 score top5 unexpectedly failed")
if merged117.get("top5_nt_score_equal") != "true":
    raise SystemExit("merged threshold 117 nt_score top5 unexpectedly failed")
if merged117.get("top5_stability_equal") != "false":
    raise SystemExit("merged threshold 117 did not capture stability boundary")

print(f"chr21_threshold0_wall={base_wall:.6f}")
print(f"chr21_threshold0_traceback={base_traceback}")
for label, row in (("116", row116), ("117", row117)):
    wall = float(row["wall_seconds"])
    traceback = int(row["traceback_requests"])
    print(f"chr21_threshold{label}_wall={wall:.6f}")
    print(f"chr21_threshold{label}_speedup_vs_threshold0={base_wall / wall:.6f}")
    print(f"chr21_threshold{label}_traceback={traceback}")
    print(f"chr21_threshold{label}_traceback_reduction_vs_threshold0={base_traceback - traceback}")

print("merged_threshold116_top5_score_equal=true")
print("merged_threshold116_top5_stability_equal=true")
print("merged_threshold116_top5_nt_score_equal=true")
print("merged_threshold117_top5_stability_equal=false")
print("ok")
PY
