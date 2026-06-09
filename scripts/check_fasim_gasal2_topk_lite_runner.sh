#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_topk_lite_runner"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
K="${K:-5}"
CASE_PRESET="${CASE_PRESET:-single}"
ALLOW_LEGACY_GASAL2_TOPK_LITE="${ALLOW_LEGACY_GASAL2_TOPK_LITE:-0}"

if [[ "$ALLOW_LEGACY_GASAL2_TOPK_LITE" != "1" ]]; then
  cat >&2 <<'EOF'
check_fasim_gasal2_topk_lite_runner.sh is legacy diagnostic coverage.
Use check-fasim-sharded-gasal2-top5-prune-runner for the current formal GASAL2/top5 gate.
Use make investigate-fasim-gasal2-topk-lite-runner-legacy only when intentionally
investigating this older standalone wrapper.
EOF
  exit 2
fi

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK"

declare -a LABELS=()
declare -a TARGETS=()
declare -a RNAS=()
declare -a RULES=()

add_case() {
  LABELS+=("$1")
  TARGETS+=("$2")
  RNAS+=("$3")
  RULES+=("$4")
}

first_records_fasta() {
  local input="$1"
  local output="$2"
  local count="$3"
  awk -v limit="$count" '
    /^>/ {
      ++records
    }
    records <= limit {
      print
    }
  ' "$input" >"$output"
}

case "$CASE_PRESET" in
  single)
    add_case "single" "$DNA" "$RNA" "$RULE"
    ;;
  chr22_2mb)
    add_case "chr22_10m_12m" "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa" "$ROOT/H19.fa" "$RULE"
    ;;
  examples)
    add_case \
      "meg3_full" \
      "$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa" \
      "$ROOT/.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa" \
      "$RULE"
    mkdir -p "$WORK/inputs"
    first_records_fasta \
      "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
      "$WORK/inputs/malat1_first8.fa" \
      8
    add_case \
      "malat1_first8" \
      "$WORK/inputs/malat1_first8.fa" \
      "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
      "$RULE"
    first_records_fasta \
      "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
      "$WORK/inputs/neat1_first64.fa" \
      64
    add_case \
      "neat1_first64" \
      "$WORK/inputs/neat1_first64.fa" \
      "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa" \
      "$RULE"
    ;;
  *)
    echo "unknown CASE_PRESET: $CASE_PRESET" >&2
    exit 1
    ;;
esac

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	dna	rna	rule	k	cpu_rows	gasal2_post_rows	gasal2_inprocess_rows	cpu_digest	gasal2_post_digest	gasal2_inprocess_digest	query_preflight_supported	gasal2_requests	length_guard_fallbacks" \
  >"$summary"

for i in "${!LABELS[@]}"; do
  label="${LABELS[$i]}"
  target="${TARGETS[$i]}"
  rna="${RNAS[$i]}"
  rule="${RULES[$i]}"
  run_dir="$WORK/$label"
  mkdir -p "$run_dir/cpu"

  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$target" -f2 "$rna" -r "$rule" -O "$run_dir/cpu" \
    >"$run_dir/cpu/stdout.log" 2>"$run_dir/cpu/stderr.log"

  mapfile -t cpu_outputs < <(find "$run_dir/cpu" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort)
  if [[ "${#cpu_outputs[@]}" -ne 1 ]]; then
    echo "expected one CPU lite output for $label, found ${#cpu_outputs[@]}" >&2
    printf '%s\n' "${cpu_outputs[@]}" >&2
    exit 1
  fi

  cpu_topk="$run_dir/cpu.top${K}.lite"
  python3 "$ROOT/scripts/extract_fasim_lite_topk.py" \
    --input "${cpu_outputs[0]}" \
    --output "$cpu_topk" \
    --k "$K" \
    >"$run_dir/cpu_topk_extract.txt"

  BIN="$BIN" \
  DNA="$target" \
  RNA="$rna" \
  RULE="$rule" \
  K="$K" \
  LEGACY_DIRECT=1 \
  OUT="$run_dir/gasal2_topk" \
  bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
    >"$run_dir/gasal2_topk_runner_stdout.log" \
    2>"$run_dir/gasal2_topk_runner_stderr.log"

  cmp -s "$cpu_topk" "$run_dir/gasal2_topk/top${K}.lite"

  BIN="$BIN" \
  DNA="$target" \
  RNA="$rna" \
  RULE="$rule" \
  K="$K" \
  LEGACY_DIRECT=1 \
  IN_PROCESS_TOPK=1 \
  OUT="$run_dir/gasal2_topk_inprocess" \
  bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
    >"$run_dir/gasal2_topk_inprocess_runner_stdout.log" \
    2>"$run_dir/gasal2_topk_inprocess_runner_stderr.log"

  cmp -s "$cpu_topk" "$run_dir/gasal2_topk_inprocess/top${K}.lite"
  cmp -s "$run_dir/gasal2_topk/top${K}.lite" "$run_dir/gasal2_topk_inprocess/top${K}.lite"

  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_requested=1$' "$run_dir/gasal2_topk/stderr.log"
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_active=1$' "$run_dir/gasal2_topk/stderr.log"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task=16$' "$run_dir/gasal2_topk/stderr.log"
  grep -q '^benchmark\.fasim_gasal2_length_guard_fallbacks=0$' "$run_dir/gasal2_topk/stderr.log"
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_requested=1$' "$run_dir/gasal2_topk_inprocess/stderr.log"
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_active=1$' "$run_dir/gasal2_topk_inprocess/stderr.log"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task=16$' "$run_dir/gasal2_topk_inprocess/stderr.log"
  grep -q '^benchmark\.fasim_gasal2_length_guard_fallbacks=0$' "$run_dir/gasal2_topk_inprocess/stderr.log"

  query_preflight_supported="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_query_preflight_supported=/{print $2}' "$run_dir/gasal2_topk/stderr.log")"
  gasal2_requests="$(awk -F= '/^benchmark\.fasim_gasal2_requests=/{print $2}' "$run_dir/gasal2_topk/stderr.log")"
  length_guard_fallbacks="$(awk -F= '/^benchmark\.fasim_gasal2_length_guard_fallbacks=/{print $2}' "$run_dir/gasal2_topk/stderr.log")"
  if [[ "${query_preflight_supported:-0}" == "1" ]]; then
    [[ "${gasal2_requests:-0}" != "0" ]]
  else
    [[ "${gasal2_requests:-0}" == "0" ]]
  fi

  cpu_digest="$(sha256sum "$cpu_topk" | awk '{print $1}')"
  gasal2_digest="$(sha256sum "$run_dir/gasal2_topk/top${K}.lite" | awk '{print $1}')"
  gasal2_inprocess_digest="$(sha256sum "$run_dir/gasal2_topk_inprocess/top${K}.lite" | awk '{print $1}')"
  cpu_rows="$(awk 'END {print (NR > 0 ? NR - 1 : 0)}' "$cpu_topk")"
  gasal2_rows="$(awk 'END {print (NR > 0 ? NR - 1 : 0)}' "$run_dir/gasal2_topk/top${K}.lite")"
  gasal2_inprocess_rows="$(awk 'END {print (NR > 0 ? NR - 1 : 0)}' "$run_dir/gasal2_topk_inprocess/top${K}.lite")"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$label" \
    "$target" \
    "$rna" \
    "$rule" \
    "$K" \
    "$cpu_rows" \
    "$gasal2_rows" \
    "$gasal2_inprocess_rows" \
    "$cpu_digest" \
    "$gasal2_digest" \
    "$gasal2_inprocess_digest" \
    "${query_preflight_supported:-0}" \
    "${gasal2_requests:-0}" \
    "${length_guard_fallbacks:-0}" \
    >>"$summary"
done

cat "$summary"
