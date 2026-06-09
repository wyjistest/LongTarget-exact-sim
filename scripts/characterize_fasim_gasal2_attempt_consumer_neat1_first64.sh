#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_attempt_consumer_neat1_first64"}"
BUILD_BIN="${BUILD_BIN:-1}"
NEAT1_RECORD_LIMIT="${NEAT1_RECORD_LIMIT:-64}"
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-0}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

case "$NEAT1_RECORD_LIMIT" in
  ''|*[!0-9]*)
    echo "NEAT1_RECORD_LIMIT must be a positive integer, got: $NEAT1_RECORD_LIMIT" >&2
    exit 1
    ;;
esac
if [[ "$NEAT1_RECORD_LIMIT" -le 0 ]]; then
  echo "NEAT1_RECORD_LIMIT must be a positive integer, got: $NEAT1_RECORD_LIMIT" >&2
  exit 1
fi
case "$REPLAY_PROBE_MAX_TASKS" in
  ''|*[!0-9]*)
    echo "REPLAY_PROBE_MAX_TASKS must be a non-negative integer, got: $REPLAY_PROBE_MAX_TASKS" >&2
    exit 1
    ;;
esac

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing NEAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"
sample="$WORK/inputs/neat1_first${NEAT1_RECORD_LIMIT}.fa"
awk -v limit="$NEAT1_RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"
if [[ ! -s "$sample" ]]; then
  echo "empty NEAT1 sample" >&2
  exit 1
fi

run_fasim() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$sample" \
    -f2 "$RNA_INPUT" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

digest_for_dir() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  sha256sum "$out_file" | awk '{print $1}'
}

wall_seconds() {
  local out_dir="$1"
  local wall
  wall="$(awk -F= '$1 == "benchmark.total_wall_seconds" {print $2}' "$out_dir/stderr.log" | tail -n 1)"
  if [[ -z "$wall" ]]; then
    wall="$(sed -n 's/^Running time is //p' "$out_dir/stdout.log" | tail -n 1)"
  fi
  if [[ -z "$wall" ]]; then
    echo "missing wall seconds for $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$wall"
}

baseline_dir="$WORK/baseline"
candidate_dir="$WORK/candidate"

run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_EXTEND_ATTEMPT_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_FULL_REPLAY_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS="$REPLAY_PROBE_MAX_TASKS" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_LEN=2812 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_OVERLAP=512 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_MAX_SEGMENTS=0 \
  FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1 \
  FASIM_ALIGN_GASAL2=1

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
baseline_wall="$(wall_seconds "$baseline_dir")"
candidate_wall="$(wall_seconds "$candidate_dir")"

python3 - \
  "$candidate_dir/stderr.log" \
  "$WORK/report.json" \
  "$baseline_digest" \
  "$candidate_digest" \
  "$baseline_wall" \
  "$candidate_wall" \
  "$NEAT1_RECORD_LIMIT" <<'PY'
import json
import sys
from pathlib import Path

stderr_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
baseline_digest = sys.argv[3]
candidate_digest = sys.argv[4]
baseline_wall = float(sys.argv[5])
candidate_wall = float(sys.argv[6])
record_limit = int(sys.argv[7])

stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

def metric(prefix: str, name: str, default: str = "0") -> str:
    return bench.get(prefix + name, default)

def require_metric(prefix: str, name: str) -> str:
    key = prefix + name
    if key not in bench:
        raise SystemExit(f"missing benchmark metric: {key}")
    return bench[key]

def as_int(value: str) -> int:
    return int(float(value))

def as_float(value: str) -> float:
    return float(value)

stream_prefix = "fasim_long_query_streaming_scoreinfo_gpu_shadow_"
attempt_prefix = "fasim_gasal2_attempt_consumer_shadow_"

candidate_vs_baseline = (
    baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0
)

attempt_requested = as_int(require_metric(attempt_prefix, "requested"))
attempt_active = as_int(require_metric(attempt_prefix, "active"))
attempt_decision = require_metric(attempt_prefix, "decision")
attempt_tasks = as_int(require_metric(attempt_prefix, "tasks"))
attempt_scoreinfos = as_int(require_metric(attempt_prefix, "scoreinfos"))
attempt_attempts = as_int(require_metric(attempt_prefix, "attempts"))
attempt_selected = as_int(require_metric(attempt_prefix, "selected_attempts"))
attempt_cpu_align = as_int(require_metric(attempt_prefix, "cpu_align_attempts"))
attempt_total = as_float(require_metric(attempt_prefix, "total_seconds"))
attempt_score_seconds = as_float(require_metric(attempt_prefix, "score_seconds"))
attempt_select_seconds = as_float(require_metric(attempt_prefix, "select_seconds"))
attempt_cpu_align_seconds = as_float(require_metric(attempt_prefix, "cpu_align_seconds"))
attempt_convert_seconds = as_float(require_metric(attempt_prefix, "convert_seconds"))
attempt_mismatches = as_int(require_metric(attempt_prefix, "triplex_mismatches"))
attempt_missing = as_int(require_metric(attempt_prefix, "missing_triplexes"))
attempt_extra = as_int(require_metric(attempt_prefix, "extra_triplexes"))
attempt_first = require_metric(attempt_prefix, "first_mismatch")
attempt_fallbacks = as_int(require_metric(attempt_prefix, "fallbacks"))
attempt_digest_match = as_int(require_metric(attempt_prefix, "digest_match"))
attempt_full_rows_equal = as_int(require_metric(attempt_prefix, "full_rows_equal"))

stream_tasks = as_int(require_metric(stream_prefix, "tasks"))
stream_scoreinfo_mismatches = as_int(require_metric(stream_prefix, "scoreinfo_mismatches"))
stream_realpath_fallbacks = as_int(require_metric(stream_prefix, "realpath_fallbacks"))
realpath_extend_seconds = as_float(require_metric(stream_prefix, "realpath_extend_seconds"))
realpath_align_seconds = as_float(require_metric(stream_prefix, "realpath_extend_align_seconds"))
realpath_align_attempts = as_int(require_metric(stream_prefix, "realpath_extend_align_attempts"))
gpu_total_seconds = as_float(metric(stream_prefix, "total_seconds", "0"))
gpu_call_seconds = as_float(metric(stream_prefix, "gpu_call_seconds", "0"))
gpu_kernel_seconds = as_float(metric(stream_prefix, "kernel_seconds", "0"))

decision = "attempt_consumer_shadow_candidate_go"
reasons = []
if baseline_digest != candidate_digest:
    reasons.append("digest_mismatch")
if stream_scoreinfo_mismatches != 0:
    reasons.append("scoreinfo_mismatches")
if stream_realpath_fallbacks != 0:
    reasons.append("realpath_fallbacks")
if attempt_requested != 1:
    reasons.append("attempt_consumer_not_requested")
if attempt_active != 1:
    reasons.append("attempt_consumer_inactive")
if attempt_tasks <= 0 or attempt_scoreinfos <= 0 or attempt_attempts <= 0:
    reasons.append("attempt_consumer_empty")
if attempt_selected <= 0:
    reasons.append("attempt_consumer_no_selected_attempts")
if attempt_cpu_align != attempt_selected:
    reasons.append("shadow_cpu_align_not_equal_selected")
if attempt_mismatches != 0 or attempt_missing != 0 or attempt_extra != 0:
    reasons.append("triplex_mismatch")
if attempt_first != "none":
    reasons.append("first_mismatch_not_none")
if attempt_fallbacks != 0:
    reasons.append("attempt_consumer_fallbacks")
if attempt_digest_match != 1 or attempt_full_rows_equal != 1:
    reasons.append("output_equality_not_recorded")
if attempt_selected >= attempt_attempts:
    reasons.append("selected_attempts_not_below_attempts")
if realpath_align_attempts > 0 and attempt_cpu_align >= realpath_align_attempts:
    reasons.append("cpu_align_attempts_not_reduced")
if candidate_vs_baseline <= 1.0:
    reasons.append("candidate_vs_baseline_not_above_1")
if attempt_total >= realpath_extend_seconds:
    reasons.append("attempt_consumer_total_not_below_cpu_reference")

if any(reason in reasons for reason in (
    "digest_mismatch",
    "scoreinfo_mismatches",
    "realpath_fallbacks",
    "attempt_consumer_inactive",
    "triplex_mismatch",
    "first_mismatch_not_none",
    "attempt_consumer_fallbacks",
    "output_equality_not_recorded",
)):
    decision = "attempt_consumer_shadow_correctness_no_go"
elif "selected_attempts_not_below_attempts" in reasons:
    decision = "attempt_consumer_shadow_no_reduction_no_go"
elif "cpu_align_attempts_not_reduced" in reasons:
    decision = "attempt_consumer_shadow_no_cpu_align_reduction_no_go"
elif ("candidate_vs_baseline_not_above_1" in reasons or
      "attempt_consumer_total_not_below_cpu_reference" in reasons):
    decision = "attempt_consumer_shadow_performance_no_go"

report = {
    "workload": "NEAT1_first64",
    "record_limit": record_limit,
    "decision": decision,
    "decision_reasons": reasons,
    "baseline_digest": baseline_digest,
    "candidate_digest": candidate_digest,
    "digest_match": baseline_digest == candidate_digest,
    "baseline_wall_seconds": baseline_wall,
    "candidate_wall_seconds": candidate_wall,
    "candidate_vs_baseline": candidate_vs_baseline,
    "stream_tasks": stream_tasks,
    "stream_scoreinfo_mismatches": stream_scoreinfo_mismatches,
    "stream_realpath_fallbacks": stream_realpath_fallbacks,
    "gpu_total_seconds": gpu_total_seconds,
    "gpu_call_seconds": gpu_call_seconds,
    "gpu_kernel_seconds": gpu_kernel_seconds,
    "realpath_extend_seconds": realpath_extend_seconds,
    "realpath_extend_align_seconds": realpath_align_seconds,
    "realpath_extend_align_attempts": realpath_align_attempts,
    "attempt_consumer_shadow_requested": attempt_requested,
    "attempt_consumer_shadow_active": attempt_active,
    "attempt_consumer_shadow_runtime_decision": attempt_decision,
    "attempt_consumer_shadow_tasks": attempt_tasks,
    "attempt_consumer_shadow_scoreinfos": attempt_scoreinfos,
    "attempt_consumer_shadow_attempts": attempt_attempts,
    "attempt_consumer_shadow_selected_attempts": attempt_selected,
    "attempt_consumer_shadow_cpu_align_attempts": attempt_cpu_align,
    "attempt_consumer_shadow_score_seconds": attempt_score_seconds,
    "attempt_consumer_shadow_select_seconds": attempt_select_seconds,
    "attempt_consumer_shadow_cpu_align_seconds": attempt_cpu_align_seconds,
    "attempt_consumer_shadow_convert_seconds": attempt_convert_seconds,
    "attempt_consumer_shadow_total_seconds": attempt_total,
    "attempt_consumer_shadow_triplex_mismatches": attempt_mismatches,
    "attempt_consumer_shadow_missing_triplexes": attempt_missing,
    "attempt_consumer_shadow_extra_triplexes": attempt_extra,
    "attempt_consumer_shadow_first_mismatch": attempt_first,
    "attempt_consumer_shadow_fallbacks": attempt_fallbacks,
    "attempt_consumer_shadow_digest_match": attempt_digest_match,
    "attempt_consumer_shadow_full_rows_equal": attempt_full_rows_equal,
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

print("decision=" + decision)
print("decision_reasons=" + ",".join(reasons))
print("candidate_vs_baseline=" + f"{candidate_vs_baseline:.6f}x")
print("attempt_consumer_shadow_triplex_mismatches=" + str(attempt_mismatches))
print("attempt_consumer_shadow_cpu_align_attempts=" + str(attempt_cpu_align))
print("realpath_extend_align_attempts=" + str(realpath_align_attempts))
print("report=" + str(report_path))
PY
