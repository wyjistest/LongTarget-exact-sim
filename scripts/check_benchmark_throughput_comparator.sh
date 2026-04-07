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

WORK="$ROOT/.tmp/check_benchmark_throughput_comparator"
rm -rf "$WORK"

python3 "$ROOT/scripts/benchmark_sample_vs_fasim.py" \
  --mode throughput \
  --compare-output-mode lite \
  --work-dir "$WORK" \
  --longtarget "$LONGTARGET_BIN" \
  --fasim-local-cuda "$FASIM_BIN" \
  --throughput-threshold-policy fasim_peak80 \
  --fasim-prealign-cuda-topk 64 \
  --fasim-prealign-peak-suppress-bp 5 \
  --fasim-extend-threads 1 >/dev/null

python3 - "$WORK/report.json" <<'PY'
import json
import sys

report_path = sys.argv[1]
with open(report_path, "r", encoding="utf-8") as fh:
    report = json.load(fh)

assert report["mode"] == "throughput"
assert report["compare_output_mode"] == "lite"
assert report["throughput"]["threshold_policy"] == "fasim_peak80"
assert report["throughput"]["runner"] == "fasim_local_cuda"

exact = report["longtarget"]["exact"]
throughput = report["fasim"]["local_cuda"]
cmp = report["comparisons"]["fasim_local_cuda"]

assert exact["output_mode"] == "lite"
assert throughput["output_mode"] == "lite"
assert exact["line_count"] >= 0
assert throughput["line_count"] >= 0

assert "strict" in cmp
assert "relaxed" in cmp
assert "score_delta_summary" in cmp
assert "top_hit_retention" in cmp
assert "recall_proxy" in cmp
PY

echo "ok"
