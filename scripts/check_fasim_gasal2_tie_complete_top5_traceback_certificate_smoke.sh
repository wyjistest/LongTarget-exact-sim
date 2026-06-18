#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_tie_complete_top5_traceback_certificate_smoke"}"
SHARED_ROOT="${SHARED_ROOT:-"$(cd "$ROOT/../.." && pwd)"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
if [[ ! -e "$DNA" && -e "$SHARED_ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa" ]]; then
  DNA="$SHARED_ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"
fi
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
BIN_DIR="$(dirname "$BIN")"
RESULT="$ROOT/docs/fasim_gasal2_tie_complete_top5_traceback_certificate.tsv"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_tie_complete_top5_traceback_certificate.py"

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
run_case shadow FASIM_GASAL2_TOP5_TRACEBACK_CERTIFICATE_SHADOW=1

SHADOW_METRICS="$WORK/shadow/metrics.log"
cp "$WORK/shadow/stderr.log" "$SHADOW_METRICS"
shadow_wall_seconds="$(sed -n 's/^Running time is //p' "$WORK/shadow/stdout.log" | tail -n 1)"
if [[ -n "$shadow_wall_seconds" ]]; then
  echo "benchmark.total_wall_seconds=$shadow_wall_seconds" >>"$SHADOW_METRICS"
fi

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
shadow_out="$(find "$WORK/shadow" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$shadow_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$baseline_out" \
  --candidate "$shadow_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"

{
  cat "$WORK/top5_compare.txt"
  awk -F= '
    $1 == "top5_score_equal" {print "top5_score_rows_order_equal="$2}
    $1 == "top5_stability_equal" {print "top5_stability_rows_order_equal="$2}
    $1 == "top5_nt_score_equal" {print "top5_nt_score_rows_order_equal="$2}
  ' "$WORK/top5_compare.txt"
} >"$WORK/top5.summary"

grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_requested=1$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_active=1$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_decision=no_go_unsupported_modes$' "$SHADOW_METRICS"
grep -Eq '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_baseline_traceback_requests=[1-9][0-9]*$' "$SHADOW_METRICS"
grep -Eq '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_certificate_traceback_requests=[1-9][0-9]*$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_tracebacks_skipped=0$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_score_certificate_supported=1$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_stability_certificate_supported=0$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_nt_score_certificate_supported=0$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_false_prune=0$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_missing_top5_rows=0$' "$SHADOW_METRICS"
grep -q '^benchmark\.fasim_gasal2_top5_traceback_certificate_shadow_extra_top5_rows=0$' "$SHADOW_METRICS"

baseline_traceback="$(metric_or_default "$SHADOW_METRICS" benchmark.fasim_gasal2_top5_traceback_certificate_shadow_baseline_traceback_requests 0)"
certificate_traceback="$(metric_or_default "$SHADOW_METRICS" benchmark.fasim_gasal2_top5_traceback_certificate_shadow_certificate_traceback_requests 0)"
tracebacks_skipped="$(metric_or_default "$SHADOW_METRICS" benchmark.fasim_gasal2_top5_traceback_certificate_shadow_tracebacks_skipped 0)"
python3 - "$baseline_traceback" "$certificate_traceback" "$tracebacks_skipped" <<'PY'
import sys

baseline = int(float(sys.argv[1]))
certificate = int(float(sys.argv[2]))
skipped = int(float(sys.argv[3]))
if baseline <= 0:
    raise SystemExit("baseline traceback requests must be positive")
if certificate != baseline:
    raise SystemExit(
        f"unsupported-mode conservative union should keep all selected tracebacks: {certificate}!={baseline}"
    )
if skipped != 0:
    raise SystemExit(f"unsupported-mode conservative union should skip zero tracebacks: {skipped}")
print(f"baseline_traceback={baseline}")
print(f"certificate_traceback={certificate}")
print(f"tracebacks_skipped={skipped}")
PY

python3 "$PARSER" \
  --workload-name chr22_slice_10m_12m \
  --status complete \
  --stderr "$SHADOW_METRICS" \
  --top5-summary "$WORK/top5.summary" \
  --target "$DNA" \
  --query H19.fa \
  --mode full_plain_slice_top5 \
  --workers 1 \
  --group-target-records null \
  --output-contract gasal2_top5_column_pruned_scoreinfo_artifact_v1 \
  --artifact-provenance "$WORK" \
  --notes "unsupported stability/nt_score modes force conservative union; no real pruning" \
  --output "$RESULT"

cat "$WORK/top5_compare.txt"
echo "result=$RESULT"
echo "ok"
