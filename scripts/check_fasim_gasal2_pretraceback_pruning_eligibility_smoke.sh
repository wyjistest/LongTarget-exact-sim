#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_pretraceback_pruning_eligibility_smoke"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
EXPORT_LIMIT="${EXPORT_LIMIT:-25}"
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
      GASAL2_DIR="${GASAL2_DIR:-$ROOT/.tmp/GASAL2}"
  )
fi

for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/eligibility"

run_case() {
  local label="$1"
  shift
  local out_dir="$WORK/$label"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1 \
    "$@" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline
run_case eligibility \
  FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1 \
  FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT="$WORK/eligibility.tsv" \
  FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY_EXPORT_LIMIT="$EXPORT_LIMIT"

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
eligibility_out="$(find "$WORK/eligibility" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$eligibility_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

diff -u "$baseline_out" "$eligibility_out" >"$WORK/full_lite.diff"

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$baseline_out" \
  --candidate "$eligibility_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"

grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_requested=1$' "$WORK/eligibility/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_active=1$' "$WORK/eligibility/stderr.log"
grep -q '^benchmark\.fasim_gasal2_direct_lite_archive_convert_active=1$' "$WORK/eligibility/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_attempts=[1-9][0-9]*$' "$WORK/eligibility/stderr.log"
grep -q "^benchmark\\.fasim_gasal2_pretraceback_pruning_eligibility_export_path=$WORK/eligibility.tsv$" "$WORK/eligibility/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_export_rows=[1-9][0-9]*$' "$WORK/eligibility/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_export_truncated=1$' "$WORK/eligibility/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_false_prune_shadow=0$' "$WORK/eligibility/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_missing_rows_shadow=0$' "$WORK/eligibility/stderr.log"
grep -q '^benchmark\.fasim_gasal2_pretraceback_pruning_eligibility_extra_rows_shadow=0$' "$WORK/eligibility/stderr.log"

test -f "$WORK/eligibility.tsv"
grep -q $'^attempt_id\tflush_id\ttask_id\tscoreinfo_index\tprealign_score\tquery_len\ttarget_size\ttarget_start\tcutlength\trequest_key_hash\tdescriptor_key_hash\tfinal_row_hash\trepresentative_attempt_id\trepresentative_flush_id\trepresentative_request_key_hash\trepresentative_descriptor_key_hash\tsame_flush\tcross_flush\tscore\tquery_begin\tquery_end\tref_begin\tref_end\toutput_global_start\toutput_global_end\tnt\tidentity\tstability\tcigar_hash\tfinal_rejection_bucket\teligibility_bucket\tpre_traceback_decidable\tpost_traceback_only\ttop5_only_safe_candidate\tfull_output_safe_candidate\tnotes$' "$WORK/eligibility.tsv"
awk -F'\t' 'NR > 1 && $3 != "-1" && $4 != "-1" {found=1} END {exit found ? 0 : 1}' "$WORK/eligibility.tsv"

line_count="$(wc -l <"$WORK/eligibility.tsv")"
python3 - "$line_count" "$EXPORT_LIMIT" <<'PY'
import sys

line_count = int(sys.argv[1])
limit = int(sys.argv[2])
if line_count < 2:
    raise SystemExit("eligibility export must contain header and at least one row")
if line_count > limit + 1:
    raise SystemExit(
        f"eligibility export exceeded cap: lines={line_count}, limit={limit}"
    )
PY

python3 "$ROOT/scripts/summarize_fasim_gasal2_pretraceback_pruning_eligibility.py" \
  --stderr "$WORK/eligibility/stderr.log" \
  --label smoke \
  >"$WORK/eligibility_summary.txt"

grep -Eq '^eligibility_attempts=[1-9][0-9]*$' "$WORK/eligibility_summary.txt"
grep -q '^false_prune_shadow=0$' "$WORK/eligibility_summary.txt"
grep -q '^missing_rows_shadow=0$' "$WORK/eligibility_summary.txt"
grep -q '^extra_rows_shadow=0$' "$WORK/eligibility_summary.txt"
grep -q $'^eligibility_bucket\tattempts\tfraction_of_traceback_attempts\tfraction_of_removed_attempts\trepresentative_mapped\tpre_traceback_decidable\tpost_traceback_only\ttop5_only_safe_candidate\tfull_output_safe_candidate\tfalse_prune_shadow\tmissing_rows_shadow\textra_rows_shadow\tnotes$' "$WORK/eligibility_summary.txt"

baseline_traceback="$(metric_or_default "$WORK/baseline/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
eligibility_traceback="$(metric_or_default "$WORK/eligibility/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
python3 - "$baseline_traceback" "$eligibility_traceback" "$WORK/eligibility/stderr.log" <<'PY'
import sys
from pathlib import Path

baseline = int(float(sys.argv[1]))
eligibility = int(float(sys.argv[2]))
stderr = Path(sys.argv[3])
if baseline <= 0:
    raise SystemExit("baseline traceback_requests must be positive")
if eligibility <= 0:
    raise SystemExit("eligibility traceback_requests must be positive")
if baseline != eligibility:
    raise SystemExit(
        f"eligibility telemetry must not change traceback_requests: {baseline} != {eligibility}"
    )

prefix = "benchmark.fasim_gasal2_pretraceback_pruning_eligibility_"
metrics = {}
for line in stderr.read_text().splitlines():
    if not line.startswith(prefix) or "=" not in line:
        continue
    key, value = line.split("=", 1)
    metrics[key[len(prefix):]] = value

attempts = int(metrics["attempts"])
retained = int(metrics["retained_final_rows"])
removed = int(metrics["removed_attempts"])
mapped = int(metrics["mapped_removed_attempts"])
unmapped = int(metrics["unmapped_removed_attempts"])
if retained + removed != attempts:
    raise SystemExit(
        f"retained+removed must equal attempts: {retained}+{removed}!={attempts}"
    )
if mapped + unmapped != removed:
    raise SystemExit(
        f"mapped+unmapped must equal removed: {mapped}+{unmapped}!={removed}"
    )
if attempts != eligibility:
    raise SystemExit(
        f"eligibility attempts should match traceback requests in smoke: {attempts}!={eligibility}"
    )
print(f"traceback_requests={eligibility}")
PY

cat "$WORK/top5_compare.txt"
cat "$WORK/eligibility_summary.txt"
echo "ok"
