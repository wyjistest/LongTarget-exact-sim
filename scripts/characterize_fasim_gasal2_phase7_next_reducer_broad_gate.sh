#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_next_reducer_broad_gate"}"
BUILD_BIN="${BUILD_BIN:-1}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"
FIRST1_RECORD_LIMIT="${FIRST1_RECORD_LIMIT:-1}"
FIRST64_RECORD_LIMIT="${FIRST64_RECORD_LIMIT:-64}"
FORCE_FIRST64="${FORCE_FIRST64:-0}"
TILE_LEN="${TILE_LEN:-2812}"
TILE_OVERLAP="${TILE_OVERLAP:-512}"
MAX_SEGMENTS="${MAX_SEGMENTS:-4}"
SCOREINFO_MAX_PER_TASK="${SCOREINFO_MAX_PER_TASK:-37}"
SCOREINFO_PRUNE_MODE="${SCOREINFO_PRUNE_MODE:-score_position_edges}"
SEGMENTED_MAX_TASKS="${SEGMENTED_MAX_TASKS:-64}"
CPU_TRACEBACK_ORDER="${CPU_TRACEBACK_ORDER:-legacy}"
CPU_TRACEBACK_MAX_RANK="${CPU_TRACEBACK_MAX_RANK:-0}"

require_uint() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "$name must be a non-negative integer, got: $value" >&2
    exit 1
  fi
}

require_positive_uint() {
  local name="$1"
  local value="$2"
  require_uint "$name" "$value"
  if [[ "$value" -le 0 ]]; then
    echo "$name must be positive, got: $value" >&2
    exit 1
  fi
}

require_positive_uint FIRST1_RECORD_LIMIT "$FIRST1_RECORD_LIMIT"
require_positive_uint FIRST64_RECORD_LIMIT "$FIRST64_RECORD_LIMIT"
require_uint FORCE_FIRST64 "$FORCE_FIRST64"
require_positive_uint TILE_LEN "$TILE_LEN"
require_uint TILE_OVERLAP "$TILE_OVERLAP"
require_uint MAX_SEGMENTS "$MAX_SEGMENTS"
require_uint SCOREINFO_MAX_PER_TASK "$SCOREINFO_MAX_PER_TASK"
require_uint SEGMENTED_MAX_TASKS "$SEGMENTED_MAX_TASKS"
require_uint CPU_TRACEBACK_MAX_RANK "$CPU_TRACEBACK_MAX_RANK"
if [[ "$TILE_OVERLAP" -ge "$TILE_LEN" ]]; then
  echo "TILE_OVERLAP must be smaller than TILE_LEN" >&2
  exit 1
fi

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

REPORT="$WORK/report.tsv"
printf '%s\n' \
  "workload	record_limit	attempted	digest_match	full_rows_equal	baseline_only_rows	candidate_only_rows	top5_score_equal	top5_stability_equal	top5_nt_score_equal	false_negative_scoreinfos	triplex_mismatches	missing_triplexes	extra_triplexes	candidate_align_attempts	reference_align_attempts	align_attempt_reduction	candidate_wall_seconds	baseline_wall_seconds	candidate_vs_baseline	decision	decision_reasons	run_dir" \
  >"$REPORT"

make_sample() {
  local limit="$1"
  local output="$2"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$DNA_INPUT" >"$output"
  if [[ ! -s "$output" ]]; then
    echo "empty sample generated for limit=$limit" >&2
    exit 1
  fi
}

run_fasim() {
  local sample="$1"
  local out_dir="$2"
  shift 2
  mkdir -p "$out_dir"
  local start_seconds end_seconds
  start_seconds="$(date +%s.%N)"
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
  end_seconds="$(date +%s.%N)"
  awk -v start="$start_seconds" -v end="$end_seconds" \
    'BEGIN {printf "%.6f\n", end - start}' >"$out_dir/wall_seconds.txt"
}

lite_output() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$out_file"
}

metric() {
  local stderr="$1"
  local key="$2"
  local default_value="${3:-0}"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2}' "$stderr" | tail -n 1)"
  printf '%s' "${value:-$default_value}"
}

wall_seconds() {
  local out_dir="$1"
  local wall
  if [[ -s "$out_dir/wall_seconds.txt" ]]; then
    head -n 1 "$out_dir/wall_seconds.txt"
    return
  fi
  wall="$(metric "$out_dir/stderr.log" benchmark.total_wall_seconds "")"
  if [[ -z "$wall" ]]; then
    wall="$(sed -n 's/^Running time is //p' "$out_dir/stdout.log" | tail -n 1)"
  fi
  if [[ -z "$wall" ]]; then
    echo "missing wall seconds for $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$wall"
}

append_skipped_first64() {
  local reason="$1"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "neat1_first64" \
    "$FIRST64_RECORD_LIMIT" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "NA" \
    "NA" \
    "NA" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0.000000" \
    "0.000000" \
    "0.000000" \
    "phase7_next_reducer_broad_gate_skipped_first1_no_go" \
    "$reason" \
    "none" \
    >>"$REPORT"
}

run_case() {
  local label="$1"
  local limit="$2"
  local run_dir="$WORK/$label"
  local sample="$WORK/inputs/$label.fa"
  make_sample "$limit" "$sample"

  local baseline_dir="$run_dir/baseline"
  local candidate_dir="$run_dir/candidate"
  mkdir -p "$run_dir"

  echo "running Phase 7 next reducer broad gate $label" >&2
  run_fasim "$sample" "$baseline_dir"
  run_fasim "$sample" "$candidate_dir" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1 \
    FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN="$TILE_LEN" \
    FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP="$TILE_OVERLAP" \
    FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS="$MAX_SEGMENTS" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1 \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK="$SCOREINFO_MAX_PER_TASK" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE="$SCOREINFO_PRUNE_MODE" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS="$SEGMENTED_MAX_TASKS" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_REPLAY=1 \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_ORDER="$CPU_TRACEBACK_ORDER" \
    FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST=1 \
    FASIM_ALIGN_GASAL2_CPU_TRACEBACK_MAX_RANK="$CPU_TRACEBACK_MAX_RANK" \
    FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW=1

  local baseline_out candidate_out baseline_digest candidate_digest digest_match
  baseline_out="$(lite_output "$baseline_dir")"
  candidate_out="$(lite_output "$candidate_dir")"
  baseline_digest="$(sha256sum "$baseline_out" | awk '{print $1}')"
  candidate_digest="$(sha256sum "$candidate_out" | awk '{print $1}')"
  digest_match=0
  if [[ "$baseline_digest" == "$candidate_digest" ]]; then
    digest_match=1
  fi

  local compare_status=0
  python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
    --baseline "$baseline_out" \
    --candidate "$candidate_out" \
    --k 5 \
    >"$run_dir/top5_compare.txt" || compare_status=$?
  if [[ "$compare_status" -gt 1 ]]; then
    echo "top5 compare failed with status $compare_status" >&2
    exit "$compare_status"
  fi

  python3 - \
    "$REPORT" \
    "$baseline_out" \
    "$candidate_out" \
    "$run_dir/top5_compare.txt" \
    "$candidate_dir/stderr.log" \
    "$label" \
    "$limit" \
    "$digest_match" \
    "$(wall_seconds "$baseline_dir")" \
    "$(wall_seconds "$candidate_dir")" \
    "$run_dir" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

report = Path(sys.argv[1])
baseline_out = Path(sys.argv[2])
candidate_out = Path(sys.argv[3])
top5_compare = Path(sys.argv[4])
stderr_path = Path(sys.argv[5])
label = sys.argv[6]
limit = sys.argv[7]
digest_match = int(sys.argv[8])
baseline_wall = float(sys.argv[9])
candidate_wall = float(sys.argv[10])
run_dir = sys.argv[11]

baseline_rows = [line.rstrip("\n") for line in baseline_out.read_text(encoding="utf-8", errors="replace").splitlines() if line.rstrip("\n")]
candidate_rows = [line.rstrip("\n") for line in candidate_out.read_text(encoding="utf-8", errors="replace").splitlines() if line.rstrip("\n")]
baseline_set = set(baseline_rows)
candidate_set = set(candidate_rows)
baseline_only_rows = len(baseline_set - candidate_set)
candidate_only_rows = len(candidate_set - baseline_set)
full_rows_equal = 1 if baseline_set == candidate_set else 0

top5 = {}
for line in top5_compare.read_text(encoding="utf-8", errors="replace").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        top5[key] = value

bench = {}
for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key] = value

prefix = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_"

def metric(name: str, default: str = "0") -> str:
    return bench.get(prefix + name, default)

def as_int(name: str) -> int:
    return int(float(metric(name)))

false_negative_scoreinfos = as_int("false_negative_scoreinfos")
triplex_mismatches = as_int("triplex_mismatches")
missing_triplexes = as_int("missing_triplexes")
extra_triplexes = as_int("extra_triplexes")
candidate_align_attempts = as_int("candidate_align_attempts")
reference_align_attempts = as_int("reference_align_attempts")
align_attempt_reduction = reference_align_attempts - candidate_align_attempts
candidate_vs_baseline = baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0

reasons: list[str] = []
if digest_match != 1 and full_rows_equal != 1:
    reasons.append("output_rows_differ")
if top5.get("top5_score_equal") != "true":
    reasons.append("top5_score_differs")
if top5.get("top5_stability_equal") != "true":
    reasons.append("top5_stability_differs")
if top5.get("top5_nt_score_equal") != "true":
    reasons.append("top5_nt_score_differs")
if false_negative_scoreinfos != 0:
    reasons.append("false_negative_scoreinfos")
if triplex_mismatches != 0 or missing_triplexes != 0 or extra_triplexes != 0:
    reasons.append("triplex_mismatches")
if candidate_align_attempts <= 0 or reference_align_attempts <= 0:
    reasons.append("missing_align_attempt_telemetry")
elif candidate_align_attempts >= reference_align_attempts:
    reasons.append("align_attempts_not_reduced")
if candidate_vs_baseline <= 1.0:
    reasons.append("candidate_vs_baseline_not_above_1")

if "output_rows_differ" in reasons or any(reason.startswith("top5_") for reason in reasons):
    decision = "phase7_next_reducer_broad_gate_correctness_no_go"
elif "false_negative_scoreinfos" in reasons or "triplex_mismatches" in reasons:
    decision = "phase7_next_reducer_broad_gate_correctness_no_go"
elif "align_attempts_not_reduced" in reasons or "missing_align_attempt_telemetry" in reasons:
    decision = "phase7_next_reducer_broad_gate_no_reduction_no_go"
elif "candidate_vs_baseline_not_above_1" in reasons:
    decision = "phase7_next_reducer_broad_gate_performance_no_go"
else:
    decision = "phase7_next_reducer_broad_gate_go"

values = [
    label,
    str(limit),
    "1",
    str(digest_match),
    str(full_rows_equal),
    str(baseline_only_rows),
    str(candidate_only_rows),
    top5.get("top5_score_equal", "NA"),
    top5.get("top5_stability_equal", "NA"),
    top5.get("top5_nt_score_equal", "NA"),
    str(false_negative_scoreinfos),
    str(triplex_mismatches),
    str(missing_triplexes),
    str(extra_triplexes),
    str(candidate_align_attempts),
    str(reference_align_attempts),
    str(align_attempt_reduction),
    f"{candidate_wall:.6f}",
    f"{baseline_wall:.6f}",
    f"{candidate_vs_baseline:.6f}",
    decision,
    ",".join(reasons) if reasons else "none",
    run_dir,
]
with report.open("a", encoding="utf-8") as handle:
    handle.write("\t".join(values) + "\n")
PY
}

run_case "neat1_first1" "$FIRST1_RECORD_LIMIT"

first1_decision="$(awk -F'\t' '$1 == "neat1_first1" {print $21}' "$REPORT" | tail -n 1)"
if [[ "$first1_decision" == "phase7_next_reducer_broad_gate_go" || "$FORCE_FIRST64" != "0" ]]; then
  run_case "neat1_first64" "$FIRST64_RECORD_LIMIT"
else
  append_skipped_first64 "first1_${first1_decision}"
fi

cat "$REPORT"
