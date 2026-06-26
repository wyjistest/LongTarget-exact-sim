#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_limited_traceback_smoke"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
MAX_SCOREINFOS="${MAX_SCOREINFOS:-65536}"
LIMITED_TRACEBACK_MODE="${LIMITED_TRACEBACK_MODE:-score}"

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
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/limited"

run_case() {
  local label="$1"
  shift
  local out_dir="$WORK/$label"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    "$@" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline
run_case limited \
  FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MAX_SCOREINFOS="$MAX_SCOREINFOS" \
  FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MODE="$LIMITED_TRACEBACK_MODE" \
  FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_ATTEMPT_EXPORT="$WORK/limited_traceback_attempts.tsv"

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
limited_out="$(find "$WORK/limited" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$limited_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$baseline_out" \
  --candidate "$limited_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^benchmark\.fasim_gasal2_limited_traceback_enabled=1$' "$WORK/limited/stderr.log"
grep -q "^benchmark\\.fasim_gasal2_limited_traceback_max_scoreinfos=$MAX_SCOREINFOS$" "$WORK/limited/stderr.log"
grep -q "^benchmark\\.fasim_gasal2_limited_traceback_mode=$LIMITED_TRACEBACK_MODE$" "$WORK/limited/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_limited_traceback_before=[1-9][0-9]*$' "$WORK/limited/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_limited_traceback_after=[1-9][0-9]*$' "$WORK/limited/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_limited_traceback_skipped=[1-9][0-9]*$' "$WORK/limited/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_limited_traceback_attempt_export_rows=[1-9][0-9]*$' "$WORK/limited/stderr.log"
grep -q '^benchmark\.fasim_gasal2_fallbacks=0$' "$WORK/limited/stderr.log"
grep -q '^benchmark\.fasim_gasal2_length_guard_fallbacks=0$' "$WORK/limited/stderr.log"
grep -q $'^batch_id\tposition\tattempt_index\tdecision\tprealign_score\tscoreinfo_index\tstart\tcutlength\ttarget_size\tnt_min_length\ttarget_end_required_for_fallback\ttarget_offset\ttarget_length\ttarget_global_start\ttarget_global_end\toutput_global_start\toutput_global_end\ttask_strand\ttask_para\ttask_rule$' "$WORK/limited_traceback_attempts.tsv"
grep -q $'\tkeep\t' "$WORK/limited_traceback_attempts.tsv"
grep -q $'\tskip\t' "$WORK/limited_traceback_attempts.tsv"

baseline_traceback="$(metric_or_default "$WORK/baseline/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
limited_traceback="$(metric_or_default "$WORK/limited/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
python3 - "$baseline_traceback" "$limited_traceback" <<'PY'
import sys

baseline = int(float(sys.argv[1]))
limited = int(float(sys.argv[2]))
if baseline <= 0:
    raise SystemExit("baseline traceback_requests must be positive")
if limited <= 0:
    raise SystemExit("limited traceback_requests must be positive")
if limited >= baseline:
    raise SystemExit(
        f"expected limited traceback_requests < baseline: {limited} >= {baseline}"
    )
print(f"baseline_traceback_requests={baseline}")
print(f"limited_traceback_requests={limited}")
print(f"traceback_reduction={baseline - limited}")
PY

cat "$WORK/top5_compare.txt"
echo "ok"
