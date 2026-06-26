#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain"}"
SUMMARY="$WORK/summary.txt"
OUT="${OUT:-"$WORK/optimization_opportunity.txt"}"
MIN_SPEEDUP="${MIN_SPEEDUP:-20}"
MIN_TRACEBACK_REQUESTS="${MIN_TRACEBACK_REQUESTS:-1000000}"

if [[ ! -s "$SUMMARY" ]]; then
  echo "missing GASAL2 full plain summary: $SUMMARY" >&2
  exit 1
fi

python3 "$ROOT/scripts/summarize_fasim_gasal2_full_plain_optimization_opportunity.py" \
  --work "$WORK" \
  --summary "$SUMMARY" \
  --min-speedup "$MIN_SPEEDUP" \
  --min-traceback-requests "$MIN_TRACEBACK_REQUESTS" \
  >"$OUT"

python3 - "$OUT" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
metrics = {}
for line in path.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        metrics[key] = value

required = {
    "decision": "traceback_reduction_is_primary_remaining_optimization",
    "top5_score_equal": "true",
    "top5_stability_equal": "true",
    "top5_nt_score_equal": "true",
    "gasal2_active": "1",
    "gasal2_fallbacks": "0",
    "gasal2_length_guard_fallbacks": "0",
}
for key, expected in required.items():
    actual = metrics.get(key)
    if actual != expected:
        raise SystemExit(f"{key}: expected {expected!r}, got {actual!r}")

for key in (
    "run_wall_speedup",
    "gasal2_traceback_requests",
    "traceback_requests_per_output_row",
    "gasal2_total_seconds",
    "gasal2_extend_wall_seconds",
    "gasal2_convert_wall_seconds",
    "output_write_seconds",
):
    if key not in metrics:
        raise SystemExit(f"missing metric: {key}")

if float(metrics["run_wall_speedup"]) <= 1.0:
    raise SystemExit("expected speedup above 1")
if int(float(metrics["gasal2_traceback_requests"])) <= 0:
    raise SystemExit("expected positive traceback requests")
if metrics.get("next_action") != "prototype_or_characterize_top5_limited_traceback":
    raise SystemExit(f"unexpected next_action: {metrics.get('next_action')!r}")
PY

cat "$OUT"
echo "ok"
