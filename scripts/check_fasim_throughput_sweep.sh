#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"
FASIM_BIN="${FASIM_BIN:-$ROOT/fasim_longtarget_cuda}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

if [[ ! -x "$FASIM_BIN" ]]; then
  (cd "$ROOT" && make build-fasim-cuda)
fi

WORK="$ROOT/.tmp/check_fasim_throughput_sweep"
rm -rf "$WORK"

(
  cd "$ROOT"
  python3 ./scripts/benchmark_fasim_throughput_sweep.py \
    --work-dir "$WORK" \
    --longtarget ./longtarget_cuda \
    --fasim-local-cuda ./fasim_longtarget_cuda \
    --device-sets 0 \
    --extend-threads 1,2 >/dev/null
)

python3 - "$WORK/report.json" <<'PY'
import json
import sys

report_path = sys.argv[1]
with open(report_path, "r", encoding="utf-8") as fh:
    report = json.load(fh)

assert report["compare_output_mode"] == "lite"
assert report["threshold_policy"] == "fasim_peak80"
assert report["device_sets"] == ["0"]
assert report["extend_threads"] == [1, 2]

exact = report["exact"]
assert exact["output_mode"] == "lite"
assert exact["line_count"] >= 0

runs = report["runs"]
assert len(runs) == 2

for run in runs:
    assert run["device_set"] == "0"
    assert run["extend_threads"] in (1, 2)
    assert run["wall_seconds"] >= 0
    assert run["output_mode"] == "lite"
    assert "strict" in run["comparison"]
    assert "relaxed" in run["comparison"]
    assert "score_delta_summary" in run["comparison"]
    assert "top_hit_retention" in run["comparison"]
    assert "recall_proxy" in run["comparison"]
    assert "per_output_comparisons" in run["comparison"]
    assert run["comparison"]["per_output_comparisons"]

best = report["best"]
assert best["device_set"] == "0"
assert best["extend_threads"] in (1, 2)
PY

echo "ok"
