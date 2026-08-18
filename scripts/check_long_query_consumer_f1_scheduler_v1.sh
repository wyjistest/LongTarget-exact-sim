#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-$ROOT/.tmp/fasim_long_query_consumer_f1_scheduler_v1}"
WORK="${WORK:-$ROOT/.tmp/long_query_consumer_f1_scheduler_v1}"
MODE="${MODE:-tfosorted}"
QUERY="${QUERY:-/data/wenyujianData/linjieData/longtarget_runs/segment_owner_authority_probe_v1/inputs/short_header_cpu_authority/ENSG00000229613.fa}"
TARGET="${TARGET:-$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa}"
BUILD="${BUILD:-1}"
CHECK_FROZEN_COUNTS="${CHECK_FROZEN_COUNTS:-1}"

# Development worktrees share the large fixture with the primary checkout.
# Prefer an explicitly supplied TARGET, then fall back to the adjacent checkout
# only when the local worktree has not materialized the fixture.
if [[ ! -s "$TARGET" && "$TARGET" == "$ROOT/.tmp/"* ]]; then
  SHARED_TARGET="$(cd "$ROOT/.." && pwd)/LongTarget-exact-sim/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"
  if [[ -s "$SHARED_TARGET" ]]; then
    TARGET="$SHARED_TARGET"
  fi
fi

case "$MODE" in
  lite)
    EXPECTED_DIGEST="${EXPECTED_DIGEST:-6f9e95ab6209d2ea053dfdef4872b6fd5616b07a9be8950976786c0a1215c226}"
    OUTPUT_GLOB='*-TFOsorted.lite'
    OUTPUT_MODE=lite
    ;;
  tfosorted)
    EXPECTED_DIGEST="${EXPECTED_DIGEST:-a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b}"
    OUTPUT_GLOB='*-TFOsorted'
    OUTPUT_MODE=tfosorted
    ;;
  *)
    echo "MODE must be lite or tfosorted" >&2
    exit 2
    ;;
esac

[[ -s "$QUERY" ]] || { echo "missing query: $QUERY" >&2; exit 1; }
[[ -s "$TARGET" ]] || { echo "missing target: $TARGET" >&2; exit 1; }

if [[ "$BUILD" != 0 ]]; then
  BUILD_CPPFLAGS="${CPPFLAGS:-} -DFASIM_WITH_SSW_FORWARD_CONTINUATION"
  GASAL2_DIR_VALUE="${GASAL2_DIR:-$ROOT/.tmp/GASAL2}"
  if [[ ! -f "$GASAL2_DIR_VALUE/Makefile" && -f "$ROOT/../LongTarget-exact-sim/.tmp/GASAL2/Makefile" ]]; then
    GASAL2_DIR_VALUE="$ROOT/../LongTarget-exact-sim/.tmp/GASAL2"
  fi
  make -C "$ROOT" -j2 build-fasim-gasal2 \
    FASIM_GASAL2_TARGET="$BIN" \
    CPPFLAGS="$BUILD_CPPFLAGS" \
    NVCC="${NVCC:-/usr/local/cuda/bin/nvcc}" \
    CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}" \
    GASAL2_DIR="$GASAL2_DIR_VALUE"
fi
[[ -x "$BIN" ]] || { echo "missing executable: $BIN" >&2; exit 1; }

rm -rf "$WORK"
mkdir -p "$WORK/out"

env \
  FASIM_OUTPUT_MODE="$OUTPUT_MODE" \
  FASIM_WRITE_TFOSORTED_LITE=0 \
  FASIM_VERBOSE=0 \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ENABLE_PREALIGN_CUDA=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_F1_REPORT="$WORK/f1.tsv" \
  "$BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -na 512 -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

mapfile -t OUTPUTS < <(find "$WORK/out" -maxdepth 1 -type f -name "$OUTPUT_GLOB" -print)
[[ "${#OUTPUTS[@]}" -eq 1 ]] || {
  echo "expected one $OUTPUT_GLOB output, found ${#OUTPUTS[@]}" >&2
  exit 1
}
ACTUAL_DIGEST="$(sha256sum "${OUTPUTS[0]}" | awk '{print $1}')"
[[ "$ACTUAL_DIGEST" == "$EXPECTED_DIGEST" ]] || {
  echo "output digest mismatch: expected $EXPECTED_DIGEST, got $ACTUAL_DIGEST" >&2
  exit 1
}

python3 - "$WORK/f1.tsv" "$WORK/summary.json" "$CHECK_FROZEN_COUNTS" <<'PY'
import csv
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
check_frozen_counts = sys.argv[3] != "0"
with report_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

def integer(row, key):
    return int(row[key])

def total(key):
    return sum(integer(row, key) for row in rows)

def round_totals(key):
    values = []
    for row in rows:
        parts = row[key].split(",") if row[key] else []
        if len(values) < len(parts):
            values.extend([0] * (len(parts) - len(values)))
        for index, value in enumerate(parts):
            values[index] += int(value)
    return values

failures = []
for row in rows:
    if row.get("execution_mode") != "f1_round_scheduled":
        failures.append("execution_mode")
    if integer(row, "ok") != 1:
        failures.append("ok")
    if integer(row, "cpu_continuation_failures") != 0:
        failures.append("cpu_continuation_failures")
    if integer(row, "cpu_continuation_calls") != integer(row, "selected_attempts"):
        failures.append("continuation_count")
    if integer(row, "reverse_scored_attempts") != integer(row, "reverse_requests"):
        failures.append("reverse_count")
    if integer(row, "empty_groups") != 0:
        failures.append("empty_groups")
    if row.get("error") not in (None, "", "none"):
        failures.append("error")

summary = {
    "rows": len(rows),
    "ok_rows": sum(integer(row, "ok") for row in rows),
    "scoreinfo_groups": total("scoreinfo_groups"),
    "attempts": total("attempts"),
    "forward_attempts": total("forward_attempts"),
    "reverse_requests": total("reverse_requests"),
    "reverse_scored_attempts": total("reverse_scored_attempts"),
    "selected_attempts": total("selected_attempts"),
    "cpu_continuation_calls": total("cpu_continuation_calls"),
    "cpu_continuation_failures": total("cpu_continuation_failures"),
    "threshold_groups": total("threshold_groups"),
    "best_fallback_groups": total("best_fallback_groups"),
    "last_groups": total("last_groups"),
    "empty_groups": total("empty_groups"),
    "round_active_groups": round_totals("round_active_groups"),
    "round_forward_attempts": round_totals("round_forward_attempts"),
    "round_reverse_requests": round_totals("round_reverse_requests"),
    "row_contract_failures": len(failures),
}

expected = {
    "rows": 10368,
    "scoreinfo_groups": 245422,
    "attempts": 981688,
    "forward_attempts": 389089,
    "reverse_requests": 245422,
    "reverse_scored_attempts": 245422,
    "selected_attempts": 245422,
    "cpu_continuation_calls": 245422,
    "cpu_continuation_failures": 0,
    "threshold_groups": 197533,
    "best_fallback_groups": 26535,
    "last_groups": 21354,
    "empty_groups": 0,
    "round_active_groups": [245422, 47889, 47889, 47889, 0],
    "round_forward_attempts": [245422, 47889, 47889, 47889, 0],
    "round_reverse_requests": [214373, 3856, 3090, 2749, 21354],
}
if check_frozen_counts:
    for key, value in expected.items():
        if summary.get(key) != value:
            failures.append(f"{key}: expected {value}, got {summary.get(key)}")
else:
    summary["frozen_count_check"] = "skipped"

summary["decision"] = "f1_scheduler_pass" if not failures else "f1_scheduler_no_go"
summary["failures"] = failures
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
if failures:
    raise SystemExit(1)
PY

echo "F1 scheduler exactness pass: $ACTUAL_DIGEST"
echo "report: $WORK/f1.tsv"
echo "summary: $WORK/summary.json"
