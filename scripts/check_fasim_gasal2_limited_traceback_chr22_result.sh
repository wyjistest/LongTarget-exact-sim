#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_limited_traceback_chr22"}"
SUMMARY="$WORK/summary.txt"

if [[ ! -s "$SUMMARY" ]]; then
  echo "missing limited traceback chr22 summary: $SUMMARY" >&2
  exit 1
fi

python3 - "$SUMMARY" <<'PY'
import sys
from pathlib import Path

summary = Path(sys.argv[1])
metrics = {}
for line in summary.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        metrics[key] = value

def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

def i(key: str) -> int:
    try:
        return int(float(metrics[key]))
    except KeyError as exc:
        raise SystemExit(f"missing metric: {key}") from exc

def f(key: str) -> float:
    try:
        return float(metrics[key])
    except KeyError as exc:
        raise SystemExit(f"missing metric: {key}") from exc

require(metrics.get("top5_score_equal") == "true", "top5 score differs")
require(metrics.get("top5_stability_equal") == "true", "top5 stability differs")
require(metrics.get("top5_nt_score_equal") == "true", "top5 nt_score differs")
require(i("fasim_gasal2_limited_traceback_enabled") == 1, "limited traceback inactive")
require(i("fasim_gasal2_limited_traceback_max_scoreinfos") > 0, "missing max scoreinfos")
require(i("fasim_gasal2_limited_traceback_before") > 0, "missing before count")
require(i("fasim_gasal2_limited_traceback_after") > 0, "missing after count")
require(i("fasim_gasal2_limited_traceback_skipped") > 0, "expected skipped traceback candidates")
require(i("fasim_gasal2_fallbacks") == 0, "GASAL2 fallbacks occurred")
require(i("fasim_gasal2_length_guard_fallbacks") == 0, "length guard fallback occurred")
require(i("baseline_gasal2_traceback_requests") > i("limited_traceback_requests"), "traceback did not reduce")
require(f("traceback_reduction_fraction") > 0.0, "missing reduction fraction")

print(f"limited_wall_seconds={metrics['limited_wall_seconds']}")
print(f"limited_vs_baseline_gasal2_wall={metrics['limited_vs_baseline_gasal2_wall']}")
print(f"baseline_gasal2_traceback_requests={metrics['baseline_gasal2_traceback_requests']}")
print(f"limited_traceback_requests={metrics['limited_traceback_requests']}")
print(f"traceback_reduction={metrics['traceback_reduction']}")
print(f"traceback_reduction_fraction={metrics['traceback_reduction_fraction']}")
print("top5_score_equal=true")
print("top5_stability_equal=true")
print("top5_nt_score_equal=true")
print("ok")
PY
