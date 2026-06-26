#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_limited_traceback_chr22"}"
TARGET="${TARGET:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
MAX_SCOREINFOS="${MAX_SCOREINFOS:-65536}"
LIMITED_TRACEBACK_MODE="${LIMITED_TRACEBACK_MODE:-score}"
CPU_BASELINE_LITE="${CPU_BASELINE_LITE:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/cpu/chr22-H19-chr22-TFOsorted.lite"}"
BASELINE_GASAL2_STDERR="${BASELINE_GASAL2_STDERR:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/gasal2/stderr.log"}"
BASELINE_GASAL2_SUMMARY="${BASELINE_GASAL2_SUMMARY:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/summary.txt"}"
BASELINE_GASAL2_CASE_METRICS="${BASELINE_GASAL2_CASE_METRICS:-"$ROOT/.tmp/measure_cpu_vs_gasal2_full_chr22_plain/gasal2/case_metrics.txt"}"

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.perf_counter():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

metric_or_default() {
  local file="$1"
  local key="$2"
  local default="$3"
  awk -F= -v key="$key" -v default="$default" '
    $1 == key {print $2; found=1}
    END {if (!found) print default}
  ' "$file"
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$CPU_BASELINE_LITE"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/limited"

start="$(now_seconds)"
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MAX_SCOREINFOS="$MAX_SCOREINFOS" \
  FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MODE="$LIMITED_TRACEBACK_MODE" \
  "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$WORK/limited" \
  >"$WORK/limited/stdout.log" 2>"$WORK/limited/stderr.log"
end="$(now_seconds)"

limited_lite="$(find "$WORK/limited" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$limited_lite" || ! -s "$limited_lite" ]]; then
  echo "missing limited lite output" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$CPU_BASELINE_LITE" \
  --candidate "$limited_lite" \
  --k 5 \
  >"$WORK/top5_compare.txt"

baseline_traceback="$(metric_or_default "$BASELINE_GASAL2_STDERR" benchmark.fasim_gasal2_traceback_requests 0)"
baseline_wall="$(metric_or_default "$BASELINE_GASAL2_SUMMARY" gasal2_wall_seconds 0)"
if [[ "$baseline_wall" == "0" || "$baseline_wall" == "0.000000" ]]; then
  baseline_wall="$(metric_or_default "$BASELINE_GASAL2_CASE_METRICS" wall_seconds 0)"
fi
limited_wall="$(elapsed_seconds "$start" "$end")"
limited_traceback="$(metric_or_default "$WORK/limited/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"

python3 - "$WORK" "$limited_lite" "$limited_wall" "$baseline_wall" "$baseline_traceback" "$limited_traceback" <<'PY'
import sys
from pathlib import Path

work = Path(sys.argv[1])
limited_lite = Path(sys.argv[2])
limited_wall = float(sys.argv[3])
baseline_wall = float(sys.argv[4])
baseline_traceback = int(float(sys.argv[5]))
limited_traceback = int(float(sys.argv[6]))

def read_kv(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key] = value
    return data

def ratio(num: float, den: float) -> str:
    return "nan" if den == 0.0 else f"{num / den:.6f}"

top5 = read_kv(work / "top5_compare.txt")
stderr = read_kv(work / "limited" / "stderr.log")
summary = {
    "limited_lite": str(limited_lite),
    "limited_wall_seconds": f"{limited_wall:.6f}",
    "baseline_gasal2_wall_seconds": f"{baseline_wall:.6f}",
    "limited_vs_baseline_gasal2_wall": ratio(limited_wall, baseline_wall),
    "baseline_gasal2_traceback_requests": str(baseline_traceback),
    "limited_traceback_requests": str(limited_traceback),
    "traceback_reduction": str(max(baseline_traceback - limited_traceback, 0)),
    "traceback_reduction_fraction": ratio(
        float(max(baseline_traceback - limited_traceback, 0)),
        float(baseline_traceback),
    ),
    "top5_score_equal": top5.get("top5_score_equal", "false"),
    "top5_stability_equal": top5.get("top5_stability_equal", "false"),
    "top5_nt_score_equal": top5.get("top5_nt_score_equal", "false"),
    "missing_rows": top5.get("missing_rows", "0"),
    "extra_rows": top5.get("extra_rows", "0"),
}
for key in (
    "benchmark.fasim_gasal2_limited_traceback_enabled",
    "benchmark.fasim_gasal2_limited_traceback_max_scoreinfos",
    "benchmark.fasim_gasal2_limited_traceback_mode",
    "benchmark.fasim_gasal2_limited_traceback_before",
    "benchmark.fasim_gasal2_limited_traceback_after",
    "benchmark.fasim_gasal2_limited_traceback_skipped",
    "benchmark.fasim_gasal2_fallbacks",
    "benchmark.fasim_gasal2_length_guard_fallbacks",
    "benchmark.fasim_gasal2_total_seconds",
    "benchmark.fasim_top5_gasal2_phase_flush_total_seconds",
    "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds",
    "benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds",
    "benchmark.fasim_top5_gasal2_phase_output_write_seconds",
):
    summary[key.replace("benchmark.", "")] = stderr.get(key, "0")

(work / "summary.txt").write_text(
    "".join(f"{key}={value}\n" for key, value in summary.items()),
    encoding="utf-8",
)
print((work / "summary.txt").read_text(encoding="utf-8"), end="")
PY
