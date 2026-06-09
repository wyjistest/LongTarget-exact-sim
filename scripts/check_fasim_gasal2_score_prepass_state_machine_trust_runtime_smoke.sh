#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_score_prepass_state_machine_trust_runtime_smoke"}"
BUILD_BIN="${BUILD_BIN:-1}"
NEAT1_RECORD_LIMIT="${NEAT1_RECORD_LIMIT:-1}"
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

baseline_dir="$WORK/baseline"
candidate_dir="$WORK/candidate"
run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS="$REPLAY_PROBE_MAX_TASKS" \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1 \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1 \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1 \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1 \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1 \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1 \
  FASIM_ALIGN_GASAL2=1

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
if [[ "$baseline_digest" != "$candidate_digest" ]]; then
  echo "state-machine trust candidate changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate=$candidate_digest" >&2
  exit 1
fi

python3 - "$candidate_dir/stderr.log" "$candidate_digest" <<'PY'
import sys
from pathlib import Path

stderr = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
digest = sys.argv[2]

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

prefix = "fasim_long_query_streaming_scoreinfo_gpu_shadow_"

def metric(name: str) -> str:
    key = prefix + name
    if key not in bench:
        raise SystemExit(f"missing benchmark metric: {key}")
    return bench[key]

def int_metric(name: str) -> int:
    return int(metric(name))

def float_metric(name: str) -> float:
    return float(metric(name))

tasks = int_metric("tasks")
if tasks <= 0:
    raise SystemExit("expected positive task count")
if int_metric("scoreinfo_mismatches") != 0:
    raise SystemExit("scoreInfo mismatches under state-machine trust smoke")
if int_metric("realpath_fallbacks") != 0:
    raise SystemExit("state-machine trust should not realpath fallback")
if int_metric("score_prepass_state_machine_shadow_requested") != 1:
    raise SystemExit("state-machine trust should request state-machine consumer")
if int_metric("score_prepass_state_machine_shadow_active") != 1:
    raise SystemExit("state-machine trust should activate state-machine consumer")
if int_metric("score_prepass_state_machine_shadow_tasks") != tasks:
    raise SystemExit(
        "state-machine trust must cover every task: "
        + metric("score_prepass_state_machine_shadow_tasks")
        + " vs "
        + str(tasks)
    )
if int_metric("score_prepass_state_machine_shadow_fallbacks") != 0:
    raise SystemExit("state-machine trust should not use state-machine fallback")
if int_metric("score_prepass_state_machine_shadow_triplex_mismatches") != 0:
    raise SystemExit("state-machine trust triplex mismatch")
if int_metric("realpath_extend_calls") != 0:
    raise SystemExit("state-machine trust should skip CPU realpath extend calls")
if int_metric("realpath_extend_align_attempts") != 0:
    raise SystemExit("state-machine trust should skip CPU realpath align attempts")
if float_metric("score_prepass_state_machine_shadow_cpu_align_seconds") <= 0.0:
    raise SystemExit("state-machine trust still needs CPU traceback align seconds")
cache_requested = int_metric("score_prepass_state_machine_shadow_cpu_align_cache_requested")
cache_lookups = int_metric("score_prepass_state_machine_shadow_cpu_align_cache_lookups")
cache_hits = int_metric("score_prepass_state_machine_shadow_cpu_align_cache_hits")
cache_misses = int_metric("score_prepass_state_machine_shadow_cpu_align_cache_misses")
cache_unique_keys = int_metric("score_prepass_state_machine_shadow_cpu_align_cache_unique_keys")
if cache_requested != 1:
    raise SystemExit("state-machine trust smoke should request align cache probe")
if cache_lookups <= 0:
    raise SystemExit("state-machine align cache should record lookups")
if cache_hits + cache_misses != cache_lookups:
    raise SystemExit("state-machine align cache hits+misses must equal lookups")
if cache_unique_keys != cache_misses:
    raise SystemExit("state-machine align cache unique keys must match misses")
if int_metric("score_prepass_state_machine_shadow_cpu_align_attempts") != cache_misses:
    raise SystemExit("state-machine CPU align attempts should equal cache misses")
gasal2_traceback_requested = int_metric("score_prepass_state_machine_shadow_gasal2_traceback_requested")
gasal2_traceback_attempts = int_metric("score_prepass_state_machine_shadow_gasal2_traceback_attempts")
gasal2_traceback_selected = int_metric("score_prepass_state_machine_shadow_gasal2_traceback_selected")
gasal2_traceback_fallbacks = int_metric("score_prepass_state_machine_shadow_gasal2_traceback_fallbacks")
gasal2_traceback_alignment_mismatches = int_metric("score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches")
gasal2_traceback_triplex_mismatches = int_metric("score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches")
if gasal2_traceback_requested != 1:
    raise SystemExit("state-machine trust smoke should request GASAL2 traceback shadow")
if gasal2_traceback_attempts != cache_lookups:
    raise SystemExit("GASAL2 traceback shadow should cover every state-machine alignment lookup")
length_guard_fallbacks = int(bench.get("fasim_gasal2_length_guard_fallbacks", "0"))
length_guard_last_query_len = int(bench.get("fasim_gasal2_length_guard_last_query_len", "0"))
length_guard_max_query_len = int(bench.get("fasim_gasal2_length_guard_max_query_len", "0"))
if gasal2_traceback_fallbacks <= 0:
    raise SystemExit("GASAL2 traceback shadow should fail closed on long-query guard")
if gasal2_traceback_selected != 0:
    raise SystemExit("guarded GASAL2 traceback shadow should not select alignments")
if length_guard_fallbacks <= 0:
    raise SystemExit("GASAL2 traceback shadow should record a length-guard fallback")
if length_guard_last_query_len <= length_guard_max_query_len:
    raise SystemExit("expected long-query length guard boundary")
segment_traceback_requested = int_metric("score_prepass_state_machine_shadow_segment_traceback_requested")
segment_traceback_attempts = int_metric("score_prepass_state_machine_shadow_segment_traceback_attempts")
segment_traceback_alignment_mismatches = int_metric("score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches")
segment_traceback_triplex_mismatches = int_metric("score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches")
segment_traceback_missing_segment = int_metric("score_prepass_state_machine_shadow_segment_traceback_missing_segment")
segment_traceback_cpu_query_outside_segment = int_metric("score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment")
segment_traceback_score_mismatches = int_metric("score_prepass_state_machine_shadow_segment_traceback_score_mismatches")
segment_traceback_endpoint_mismatches = int_metric("score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches")
segment_traceback_cigar_mismatches = int_metric("score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches")
if segment_traceback_requested != 1:
    raise SystemExit("state-machine trust smoke should request segment traceback shadow")
if segment_traceback_attempts != cache_lookups:
    raise SystemExit("segment traceback shadow should cover every state-machine alignment lookup")
expanded_segment_traceback_requested = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_requested")
expanded_segment_traceback_attempts = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_attempts")
expanded_segment_traceback_alignment_mismatches = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches")
expanded_segment_traceback_triplex_mismatches = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches")
expanded_segment_traceback_cpu_query_outside_expanded_segment = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment")
expanded_segment_traceback_score_mismatches = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_score_mismatches")
expanded_segment_traceback_endpoint_mismatches = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_endpoint_mismatches")
expanded_segment_traceback_cigar_mismatches = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_cigar_mismatches")
expanded_segment_traceback_required_max_len = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len")
expanded_segment_traceback_required_over_gasal2_limit = int_metric("score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit")
if expanded_segment_traceback_requested != 1:
    raise SystemExit("state-machine trust smoke should request expanded segment traceback shadow")
if expanded_segment_traceback_attempts != cache_lookups:
    raise SystemExit("expanded segment traceback shadow should cover every state-machine alignment lookup")

print("digest=" + digest)
print("tasks=" + str(tasks))
print("state_machine_cpu_align_attempts=" + metric("score_prepass_state_machine_shadow_cpu_align_attempts"))
print("state_machine_cpu_align_cache_lookups=" + str(cache_lookups))
print("state_machine_cpu_align_cache_hits=" + str(cache_hits))
print("state_machine_cpu_align_cache_misses=" + str(cache_misses))
print("state_machine_cpu_align_cache_unique_keys=" + str(cache_unique_keys))
print("gasal2_traceback_shadow_attempts=" + str(gasal2_traceback_attempts))
print("gasal2_traceback_shadow_selected=" + str(gasal2_traceback_selected))
print("gasal2_traceback_shadow_fallbacks=" + str(gasal2_traceback_fallbacks))
print("gasal2_traceback_shadow_alignment_mismatches=" + str(gasal2_traceback_alignment_mismatches))
print("gasal2_traceback_shadow_triplex_mismatches=" + str(gasal2_traceback_triplex_mismatches))
print("gasal2_length_guard_last_query_len=" + str(length_guard_last_query_len))
print("gasal2_length_guard_max_query_len=" + str(length_guard_max_query_len))
print("segment_traceback_shadow_attempts=" + str(segment_traceback_attempts))
print("segment_traceback_shadow_alignment_mismatches=" + str(segment_traceback_alignment_mismatches))
print("segment_traceback_shadow_triplex_mismatches=" + str(segment_traceback_triplex_mismatches))
print("segment_traceback_shadow_missing_segment=" + str(segment_traceback_missing_segment))
print("segment_traceback_shadow_cpu_query_outside_segment=" + str(segment_traceback_cpu_query_outside_segment))
print("segment_traceback_shadow_score_mismatches=" + str(segment_traceback_score_mismatches))
print("segment_traceback_shadow_endpoint_mismatches=" + str(segment_traceback_endpoint_mismatches))
print("segment_traceback_shadow_cigar_mismatches=" + str(segment_traceback_cigar_mismatches))
print("expanded_segment_traceback_shadow_attempts=" + str(expanded_segment_traceback_attempts))
print("expanded_segment_traceback_shadow_alignment_mismatches=" + str(expanded_segment_traceback_alignment_mismatches))
print("expanded_segment_traceback_shadow_triplex_mismatches=" + str(expanded_segment_traceback_triplex_mismatches))
print("expanded_segment_traceback_shadow_cpu_query_outside_expanded_segment=" + str(expanded_segment_traceback_cpu_query_outside_expanded_segment))
print("expanded_segment_traceback_shadow_score_mismatches=" + str(expanded_segment_traceback_score_mismatches))
print("expanded_segment_traceback_shadow_endpoint_mismatches=" + str(expanded_segment_traceback_endpoint_mismatches))
print("expanded_segment_traceback_shadow_cigar_mismatches=" + str(expanded_segment_traceback_cigar_mismatches))
print("expanded_segment_traceback_shadow_required_max_len=" + str(expanded_segment_traceback_required_max_len))
print("expanded_segment_traceback_shadow_required_over_gasal2_limit=" + str(expanded_segment_traceback_required_over_gasal2_limit))
print("realpath_extend_align_attempts=0")
print("score_prepass_state_machine_shadow_triplex_mismatches=0")
print("ok")
PY
