#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_guard_score_band_smoke"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

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

for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/band"

run_case() {
  local out_dir="$1"
  shift
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

run_case "$WORK/baseline"
run_case "$WORK/band" \
  FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=120 \
  FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MIN_PREALIGN_SCORE=115 \
  FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_PREALIGN_SCORE=116 \
  FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_TARGET_SIZE=120 \
  FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_ATTEMPT_EXPORT="$WORK/band_attempts.tsv"

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
band_out="$(find "$WORK/band" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$band_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$baseline_out" \
  --candidate "$band_out" \
  --k 5 \
  >"$WORK/top5_compare.txt" || true

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=false$' "$WORK/top5_compare.txt"
grep -q '^benchmark\.fasim_gasal2_limited_traceback_enabled=1$' "$WORK/band/stderr.log"
grep -q '^benchmark\.fasim_gasal2_limited_traceback_min_prealign_score=120$' "$WORK/band/stderr.log"
grep -q '^benchmark\.fasim_gasal2_limited_traceback_guard_min_prealign_score=115$' "$WORK/band/stderr.log"
grep -q '^benchmark\.fasim_gasal2_limited_traceback_guard_max_prealign_score=116$' "$WORK/band/stderr.log"
grep -q '^benchmark\.fasim_gasal2_limited_traceback_guard_max_target_size=120$' "$WORK/band/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_limited_traceback_guard_kept=[1-9][0-9]*$' "$WORK/band/stderr.log"
grep -q $'^batch_id\tposition\tattempt_index\tdecision\tprealign_score\tscoreinfo_index\tstart\tcutlength\ttarget_size\tnt_min_length\ttarget_end_required_for_fallback\ttarget_offset\ttarget_length\ttarget_global_start\ttarget_global_end\toutput_global_start\toutput_global_end\ttask_strand\ttask_para\ttask_rule$' "$WORK/band_attempts.tsv"
grep -q $'\tskip\t' "$WORK/band_attempts.tsv"

baseline_traceback="$(metric_or_default "$WORK/baseline/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
band_traceback="$(metric_or_default "$WORK/band/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
python3 - "$baseline_traceback" "$band_traceback" <<'PY'
import sys

baseline = int(float(sys.argv[1]))
band = int(float(sys.argv[2]))
if baseline <= 0:
    raise SystemExit("baseline traceback_requests must be positive")
if band <= 0:
    raise SystemExit("band traceback_requests must be positive")
if band >= baseline:
    raise SystemExit(f"expected band traceback_requests < baseline: {band} >= {baseline}")
print(f"baseline_traceback_requests={baseline}")
print(f"band_traceback_requests={band}")
print(f"traceback_reduction={baseline - band}")
PY

cat "$WORK/top5_compare.txt"
echo "score-band guard no-go captured: stability top5 is not protected by score band alone"
echo "ok"
