#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-$ROOT/.tmp/fasim_f1_legacy_cpu_replay_v1}"
WORK="${WORK:-$ROOT/.tmp/check_long_query_consumer_f1_legacy_cpu_replay_v1}"
GPU="${GPU:-0}"
BUILD="${BUILD:-1}"
PROMOTER_CONCAT="${PROMOTER_CONCAT:-/data/wenyujianData/linjieData/promoter_sequences/human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1/promoter_components_concat.fa}"
QUERY_ROOT="${QUERY_ROOT:-/data/wenyujianData/linjieData/lncrna_sequences/human_GRCh38_GENCODE_v33/gene_exon_union/per_gene}"

[[ -s "$PROMOTER_CONCAT" ]] || { echo "missing promoter concat: $PROMOTER_CONCAT" >&2; exit 1; }

if [[ "$BUILD" != 0 ]]; then
  mkdir -p "$(dirname "$BIN")"
  GASAL2_DIR_VALUE="${GASAL2_DIR:-$ROOT/.tmp/GASAL2}"
  if [[ ! -f "$GASAL2_DIR_VALUE/Makefile" && -f "$ROOT/../LongTarget-exact-sim/.tmp/GASAL2/Makefile" ]]; then
    GASAL2_DIR_VALUE="$ROOT/../LongTarget-exact-sim/.tmp/GASAL2"
  fi
  make -C "$ROOT" -j2 build-fasim-gasal2 \
    FASIM_GASAL2_TARGET="$BIN" \
    CPPFLAGS="${CPPFLAGS:-} -DFASIM_WITH_SSW_FORWARD_CONTINUATION" \
    NVCC="${NVCC:-/usr/local/cuda/bin/nvcc}" \
    CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}" \
    GASAL2_DIR="$GASAL2_DIR_VALUE"
fi
[[ -x "$BIN" ]] || { echo "missing binary: $BIN" >&2; exit 1; }

rm -rf "$WORK"
mkdir -p "$WORK"

extract_window()
{
  local name=$1
  local start=$2
  local end=$3
  local output=$4
  awk -v start="$start" -v end="$end" -v name="$name" '
    BEGIN { pos = 0; print ">" name }
    /^>/ { next }
    {
      gsub(/[[:space:]]/, "")
      line_start = pos + 1
      line_end = pos + length($0)
      if (line_end >= start && line_start <= end) {
        from = start > line_start ? start - line_start + 1 : 1
        to = end < line_end ? end - line_start + 1 : length($0)
        print substr($0, from, to - from + 1)
      }
      pos = line_end
      if (pos >= end) exit
    }
  ' "$PROMOTER_CONCAT" > "$output"
  [[ "$(awk '!/^>/ { total += length($0) } END { print total + 0 }' "$output")" == 5000 ]] || {
    echo "unexpected fixture length: $output" >&2
    exit 1
  }
}

run_f1()
{
  local target=$1
  local query=$2
  local rule=$3
  local strand=$4
  local output=$5
  local replay=$6
  mkdir -p "$output/out"
  env -u FASIM_LONG_QUERY_GPU_CONSUMER_F1_LEGACY_CPU_REPLAY \
    CUDA_VISIBLE_DEVICES="$GPU" \
    OMP_NUM_THREADS=1 \
    FASIM_OUTPUT_MODE=tfosorted \
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
    FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_REPLACEMENT_PROTOTYPE=0 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_PROFILE_REUSE=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_CONTINUATION_THREADS=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_PIPELINE=1 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_LEGACY_CPU_REPLAY="$replay" \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=0 \
    FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED_AUTO=1 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=0 \
    FASIM_LONG_QUERY_GPU_CONSUMER_F1_REPORT="$output/f1.tsv" \
    "$BIN" -f1 "$target" -f2 "$query" -r "$rule" -t "$strand" -na 512 \
      -O "$output/out" > "$output/stdout.log" 2> "$output/stderr.log"
}

run_cpu()
{
  local target=$1
  local query=$2
  local rule=$3
  local strand=$4
  local output=$5
  mkdir -p "$output/out"
  env -u FASIM_LONG_QUERY_GPU_CONSUMER_F1_LEGACY_CPU_REPLAY \
    OMP_NUM_THREADS=1 FASIM_OUTPUT_MODE=tfosorted FASIM_VERBOSE=0 \
    "$BIN" -f1 "$target" -f2 "$query" -r "$rule" -t "$strand" -na 512 \
      -O "$output/out" > "$output/stdout.log" 2> "$output/stderr.log"
}

check_case()
{
  local name=$1
  local start=$2
  local gene=$3
  local rule=$4
  local strand=$5
  local fixture="$WORK/$name.fa"
  local query_source="$QUERY_ROOT/$gene.fa"
  local query="$WORK/$gene.fa"
  [[ -s "$query_source" ]] || { echo "missing query: $query_source" >&2; exit 1; }
  awk -v gene="$gene" 'BEGIN { print ">" gene } !/^>/ { gsub(/[[:space:]]/, ""); print toupper($0) }' \
    "$query_source" > "$query"
  extract_window "$name" "$start" "$((start + 4999))" "$fixture"

  set +e
  run_f1 "$fixture" "$query" "$rule" "$strand" "$WORK/$name-strict" 0
  local strict_status=$?
  set -e
  [[ "$strict_status" -ne 0 ]] || { echo "$name strict mode unexpectedly succeeded" >&2; exit 1; }
  rg -q 'f1_global_continuation_contract_mismatch' "$WORK/$name-strict/stderr.log"

  run_f1 "$fixture" "$query" "$rule" "$strand" "$WORK/$name-replay" 1
  run_cpu "$fixture" "$query" "$rule" "$strand" "$WORK/$name-cpu"

  mapfile -t replay_outputs < <(find "$WORK/$name-replay/out" -maxdepth 1 -type f -name '*-TFOsorted' -print)
  mapfile -t cpu_outputs < <(find "$WORK/$name-cpu/out" -maxdepth 1 -type f -name '*-TFOsorted' -print)
  [[ ${#replay_outputs[@]} -eq 1 && ${#cpu_outputs[@]} -eq 1 ]] || {
    echo "$name did not produce one replay and one CPU output" >&2
    exit 1
  }
  cmp -s "${replay_outputs[0]}" "${cpu_outputs[0]}" || {
    echo "$name replay output differs from CPU" >&2
    exit 1
  }
  rg -q '^benchmark\.fasim_long_query_gpu_consumer_f1_pipeline_failures=0$' \
    "$WORK/$name-replay/stderr.log"

  awk -F '\t' '
    NR == 1 { for (i = 1; i <= NF; ++i) column[$i] = i; next }
    $column["legacy_cpu_replay_active"] == 1 {
      active += 1
      if ($column["ok"] != 1 ||
          $column["legacy_cpu_replay_requested"] != 1 ||
          $column["cpu_continuation_failures"] != 1 ||
          $column["legacy_cpu_replay_attempts"] <= 0 ||
          $column["legacy_cpu_replay_reason"] !~ /continuation_contract_mismatch/) bad += 1
    }
    END { exit !(active == 1 && bad == 0) }
  ' "$WORK/$name-replay/f1.tsv"

  printf '%s\tpass\t%s\n' "$name" "$(sha256sum "${replay_outputs[0]}" | awk '{print $1}')"
}

# These two windows isolate the fresh-query failures found in the production queue.
check_case window_1293 6335701 ENSG00000229852 3 1
check_case window_0959 4699101 ENSG00000250208 17 -1
