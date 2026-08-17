#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-$ROOT/.tmp/fasim_longtarget_gpu_consumer_replacement_prototype_v1}"
WORK="${WORK:-$ROOT/.tmp/long_query_gpu_consumer_replacement_prototype_v1_check}"
QUERY="${QUERY:-/data/wenyujianData/linjieData/longtarget_runs/segment_owner_authority_probe_v1/inputs/short_header_cpu_authority/ENSG00000229613.fa}"
TARGET="${TARGET:-$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa}"
REPEATS="${REPEATS:-1}"
GPU="${GPU:-0}"
BASELINE_DIGEST="${BASELINE_DIGEST:-6f9e95ab6209d2ea053dfdef4872b6fd5616b07a9be8950976786c0a1215c226}"

[[ "$REPEATS" =~ ^[1-9][0-9]*$ ]] || {
  echo "REPEATS must be a positive integer" >&2
  exit 2
}
[[ -s "$QUERY" ]] || { echo "missing query: $QUERY" >&2; exit 2; }
[[ -s "$TARGET" ]] || { echo "missing target: $TARGET" >&2; exit 2; }

make -C "$ROOT" build-fasim-gasal2 \
  FASIM_GASAL2_TARGET="$BIN" \
  CPPFLAGS=-DFASIM_WITH_SSW_FORWARD_CONTINUATION

rm -rf "$WORK"
mkdir -p "$WORK"

find_output() {
  find "$1" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit
}

run_fasim() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  /usr/bin/time \
    -f 'wall_seconds=%e\nmax_rss_kb=%M\nexit_status=%x' \
    -o "$out_dir/time.txt" \
    env CUDA_VISIBLE_DEVICES="$GPU" FASIM_OUTPUT_MODE=lite FASIM_VERBOSE=0 "$@" \
    "$BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -na 512 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

validate_replacement_report() {
  local report="$1"
  awk -F '\t' '
    NR == 1 {
      for (i = 1; i <= NF; ++i) h[$i] = i
      next
    }
    {
      rows++
      ok += $h["ok"]
      unknown += ($h["output_equal"] == -1)
      authority += $h["authority_comparison_available"]
      validation += $h["validation_enabled"]
      attempts += $h["attempts"]
      gpu += $h["gpu_scored_attempts"]
      oracle += $h["cpu_oracle_attempts"]
      reference += $h["cpu_reference_align_attempts"]
      selected += $h["control_selected_attempts"]
      continuation += $h["cpu_continuation_calls"]
      continuation_failures += $h["cpu_continuation_failures"]
      cpu_align += $h["cpu_align_attempts"]
      if ($h["error"] != "none") errors++
    }
    END {
      clean = rows > 0 && ok == rows && unknown == rows &&
              authority == 0 && validation == 0 && attempts == gpu &&
              oracle == 0 && reference == 0 && selected == continuation &&
              continuation_failures == 0 && cpu_align == continuation &&
              errors == 0
      printf "rows=%d ok=%d attempts=%d gpu_scored=%d cpu_oracle=%d " \
             "cpu_reference=%d selected=%d continuation=%d " \
             "continuation_failures=%d errors=%d clean=%d\n", \
             rows, ok, attempts, gpu, oracle, reference, selected, \
             continuation, continuation_failures, errors, clean
      if (!clean) exit 1
    }
  ' "$report"
}

metric() {
  local key="$1"
  local file="$2"
  awk -F= -v key="$key" '$1 == key { value=$2 } END { print value }' "$file"
}

median_file() {
  sort -n "$1" | awk '
    { values[NR]=$1 }
    END {
      if (NR % 2) print values[(NR + 1) / 2]
      else print (values[NR / 2] + values[NR / 2 + 1]) / 2
    }
  '
}

: >"$WORK/baseline_wall_seconds.txt"
: >"$WORK/replacement_wall_seconds.txt"
for repeat in $(seq 1 "$REPEATS"); do
  baseline_dir="$WORK/baseline_${repeat}"
  replacement_dir="$WORK/replacement_${repeat}"

  run_fasim "$baseline_dir" \
    FASIM_ALIGN_GASAL2=0 \
    FASIM_ENABLE_PREALIGN_CUDA=0

  run_fasim "$replacement_dir" \
    FASIM_ALIGN_GASAL2=1 \
    FASIM_ENABLE_PREALIGN_CUDA=1 \
    FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
    FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_REPORT="$replacement_dir/consumer.tsv"

  baseline_output="$(find_output "$baseline_dir")"
  replacement_output="$(find_output "$replacement_dir")"
  [[ -s "$baseline_output" && -s "$replacement_output" ]] || {
    echo "missing TFOsorted output for repeat $repeat" >&2
    exit 1
  }
  baseline_sha="$(sha256sum "$baseline_output" | awk '{print $1}')"
  replacement_sha="$(sha256sum "$replacement_output" | awk '{print $1}')"
  [[ "$baseline_sha" == "$BASELINE_DIGEST" ]] || {
    echo "baseline digest changed: $baseline_sha" >&2
    exit 1
  }
  [[ "$replacement_sha" == "$baseline_sha" ]] || {
    echo "replacement digest mismatch on repeat $repeat" >&2
    exit 1
  }

  validate_replacement_report "$replacement_dir/consumer.tsv" \
    >"$replacement_dir/consumer_summary.txt"
  [[ "$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches "$replacement_dir/stderr.log")" == 0 ]]
  [[ "$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks "$replacement_dir/stderr.log")" == 0 ]]
  [[ "$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds "$replacement_dir/stderr.log")" == 0 ]]
  [[ "$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks "$replacement_dir/stderr.log")" == 0 ]]
  [[ "$(metric benchmark.fasim_gasal2_fallbacks "$replacement_dir/stderr.log")" == 0 ]]

  metric wall_seconds "$baseline_dir/time.txt" >>"$WORK/baseline_wall_seconds.txt"
  metric wall_seconds "$replacement_dir/time.txt" >>"$WORK/replacement_wall_seconds.txt"
done

median_baseline="$(median_file "$WORK/baseline_wall_seconds.txt")"
median_replacement="$(median_file "$WORK/replacement_wall_seconds.txt")"
speedup="$(awk -v cpu="$median_baseline" -v replacement="$median_replacement" \
  'BEGIN { printf "%.9f", cpu / replacement }')"
awk -v speedup="$speedup" 'BEGIN { exit !(speedup >= 1.5) }' || {
  echo "replacement prototype missed the 1.5x gate: $speedup" >&2
  exit 1
}

source_diff_sha256="$(git -C "$ROOT" diff --binary -- \
  cuda/prealign_cuda.cu cuda/prealign_cuda.h cuda/prealign_cuda_stub.cpp \
  fasim/Fasim-LongTarget.cpp fasim/fastsim.h fasim/gasal2_align_bridge.cpp \
  fasim/gasal2_align_bridge.h fasim/gasal2_align_bridge_stub.cpp \
  fasim/ssw.h fasim/sswNew.cpp fasim/ssw_cpp.cpp fasim/ssw_cpp.h | \
  sha256sum | awk '{print $1}')"

jq -n \
  --arg schema_version "long_query_gpu_consumer_replacement_prototype_v1" \
  --arg decision "fixture_gate_pass" \
  --arg source_commit "$(git -C "$ROOT" rev-parse HEAD)" \
  --arg source_diff_sha256 "$source_diff_sha256" \
  --arg binary "$BIN" \
  --arg binary_sha256 "$(sha256sum "$BIN" | awk '{print $1}')" \
  --arg query "$QUERY" \
  --arg query_sha256 "$(sha256sum "$QUERY" | awk '{print $1}')" \
  --arg target "$TARGET" \
  --arg target_sha256 "$(sha256sum "$TARGET" | awk '{print $1}')" \
  --arg output_sha256 "$BASELINE_DIGEST" \
  --argjson repeats "$REPEATS" \
  --argjson median_cpu_wall_seconds "$median_baseline" \
  --argjson median_replacement_wall_seconds "$median_replacement" \
  --argjson median_speedup "$speedup" \
  '{
    schema_version: $schema_version,
    decision: $decision,
    artifact_role: "development_fixture_only",
    implementation: "stateful_gpu_scoreinfo_plus_gpu_endpoint_plus_host_selection_plus_selected_cpu_continuation",
    gpu_only_traceback: false,
    production_authorized: false,
    source_commit: $source_commit,
    source_diff_sha256: $source_diff_sha256,
    binary: $binary,
    binary_sha256: $binary_sha256,
    query: $query,
    query_sha256: $query_sha256,
    target: $target,
    target_sha256: $target_sha256,
    output_sha256: $output_sha256,
    repeats: $repeats,
    median_cpu_wall_seconds: $median_cpu_wall_seconds,
    median_replacement_wall_seconds: $median_replacement_wall_seconds,
    median_speedup: $median_speedup
  }' >"$WORK/report.json"

cat "$WORK/report.json"
