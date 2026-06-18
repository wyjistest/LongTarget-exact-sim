#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_pretraceback_span_prune_shadow_smoke"}"
SHARED_ROOT="${SHARED_ROOT:-"$(cd "$ROOT/../.." && pwd)"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
if [[ ! -e "$DNA" && -e "$SHARED_ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa" ]]; then
  DNA="$SHARED_ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"
fi
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
BIN_DIR="$(dirname "$BIN")"

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
  mkdir -p "$BIN_DIR"
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN" \
      GASAL2_DIR="${GASAL2_DIR:-$SHARED_ROOT/.tmp/GASAL2}"
  )
fi

for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/shadow"

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
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1 \
    "$@" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline
run_case shadow FASIM_GASAL2_PRETRACEBACK_SPAN_PRUNE_SHADOW=1

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
shadow_out="$(find "$WORK/shadow" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$shadow_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

diff -u "$baseline_out" "$shadow_out" >"$WORK/full_lite.diff"

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$baseline_out" \
  --candidate "$shadow_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"

grep -q '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_requested=1$' "$WORK/shadow/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_active=[01]$' "$WORK/shadow/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_input_attempts=[1-9][0-9]*$' "$WORK/shadow/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_authority_selected_attempts=[1-9][0-9]*$' "$WORK/shadow/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_traceback_requests=[0-9]+$' "$WORK/shadow/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_false_prune=0$' "$WORK/shadow/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_missing_rows=0$' "$WORK/shadow/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_span_prune_shadow_extra_rows=0$' "$WORK/shadow/stderr.log"

baseline_traceback="$(metric_or_default "$WORK/baseline/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
shadow_total_traceback="$(metric_or_default "$WORK/shadow/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
shadow_traceback="$(metric_or_default "$WORK/shadow/stderr.log" benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_requests 0)"
authority_selected="$(metric_or_default "$WORK/shadow/stderr.log" benchmark.fasim_gasal2_pretraceback_span_prune_shadow_authority_selected_attempts 0)"
kept_selected="$(metric_or_default "$WORK/shadow/stderr.log" benchmark.fasim_gasal2_pretraceback_span_prune_shadow_kept_selected_attempts 0)"
skipped_selected="$(metric_or_default "$WORK/shadow/stderr.log" benchmark.fasim_gasal2_pretraceback_span_prune_shadow_skipped_selected_attempts 0)"
python3 - "$baseline_traceback" "$shadow_total_traceback" "$shadow_traceback" "$authority_selected" "$kept_selected" "$skipped_selected" <<'PY'
import sys

baseline_traceback = int(float(sys.argv[1]))
shadow_total_traceback = int(float(sys.argv[2]))
shadow_traceback = int(float(sys.argv[3]))
authority_selected = int(float(sys.argv[4]))
kept_selected = int(float(sys.argv[5]))
skipped_selected = int(float(sys.argv[6]))
if baseline_traceback <= 0:
    raise SystemExit("baseline traceback_requests must be positive")
if authority_selected <= 0:
    raise SystemExit("authority selected attempts must be positive")
if kept_selected + skipped_selected != authority_selected:
    raise SystemExit(
        f"kept+skipped must equal authority selected: {kept_selected}+{skipped_selected}!={authority_selected}"
    )
if shadow_traceback != kept_selected:
    raise SystemExit(
        f"shadow traceback requests should match kept selected attempts: {shadow_traceback}!={kept_selected}"
    )
if shadow_total_traceback < baseline_traceback + shadow_traceback:
    raise SystemExit(
        "shadow run total traceback should include authority and shadow traceback requests"
    )
print(f"baseline_traceback={baseline_traceback}")
print(f"shadow_traceback={shadow_traceback}")
print(f"skipped_selected={skipped_selected}")
PY

cat "$WORK/top5_compare.txt"
echo "ok"
