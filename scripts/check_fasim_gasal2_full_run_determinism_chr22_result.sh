#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_full_run_determinism_chr22"}"
SUMMARY="$WORK/summary.txt"
PAIRS="$WORK/determinism_pairs.tsv"

if [[ ! -s "$SUMMARY" ]]; then
  echo "missing full-run determinism summary: $SUMMARY" >&2
  exit 1
fi
if [[ ! -s "$PAIRS" ]]; then
  echo "missing full-run determinism pairs: $PAIRS" >&2
  exit 1
fi

python3 - "$SUMMARY" "$PAIRS" <<'PY'
import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
pairs_path = Path(sys.argv[2])
metrics: dict[str, str] = {}
for line in summary_path.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        metrics[key] = value

required = [
    "runs",
    "schema",
    "byte_stable",
    "set_stable",
    "multiset_stable",
    "top5_score_stable",
    "top5_stability_stable",
    "top5_nt_score_stable",
    "max_pair_set_missing",
    "max_pair_set_extra",
    "max_pair_multiset_missing",
    "max_pair_multiset_extra",
    "classification",
    "decision",
]
missing = [key for key in required if key not in metrics]
if missing:
    raise SystemExit("missing metrics: " + ",".join(missing))
if int(metrics["runs"]) < 2:
    raise SystemExit("expected at least two runs")
if metrics["schema"] not in {"lite", "tfosorted"}:
    raise SystemExit("unexpected schema: " + metrics["schema"])
if metrics["decision"] != "determinism_oracle_recorded":
    raise SystemExit("unexpected decision: " + metrics["decision"])
if metrics["top5_score_stable"] != "true":
    raise SystemExit("top5 score is not stable")
if metrics["top5_stability_stable"] != "true":
    raise SystemExit("top5 stability is not stable")
if metrics["top5_nt_score_stable"] != "true":
    raise SystemExit("top5 nt_score is not stable")

with pairs_path.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if not rows:
    raise SystemExit("empty pair report")
for row in rows:
    for key in [
        "byte_equal",
        "set_equal",
        "multiset_equal",
        "set_missing",
        "set_extra",
        "multiset_missing",
        "multiset_extra",
        "top_score_equal",
        "top_stability_equal",
        "top_nt_score_equal",
    ]:
        if key not in row:
            raise SystemExit(f"missing pair column: {key}")

print("full_run_determinism_result=ok")
print("classification=" + metrics["classification"])
print("byte_stable=" + metrics["byte_stable"])
print("set_stable=" + metrics["set_stable"])
print("multiset_stable=" + metrics["multiset_stable"])
PY
