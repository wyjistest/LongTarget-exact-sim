#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_rejection_taxonomy_smoke"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
EXPORT_LIMIT="${EXPORT_LIMIT:-25}"

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
mkdir -p "$WORK/baseline" "$WORK/taxonomy"

run_case() {
  local label="$1"
  shift
  local out_dir="$WORK/$label"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    "$@" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline
run_case taxonomy \
  FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY=1 \
  FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT="$WORK/taxonomy.tsv" \
  FASIM_GASAL2_TRACEBACK_REJECTION_TAXONOMY_EXPORT_LIMIT="$EXPORT_LIMIT"

baseline_out="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
taxonomy_out="$(find "$WORK/taxonomy" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_out" || -z "$taxonomy_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$baseline_out" \
  --candidate "$taxonomy_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"

grep -q '^benchmark\.fasim_gasal2_traceback_rejection_taxonomy_requested=1$' "$WORK/taxonomy/stderr.log"
grep -q '^benchmark\.fasim_gasal2_traceback_rejection_taxonomy_active=1$' "$WORK/taxonomy/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_traceback_rejection_taxonomy_attempts=[1-9][0-9]*$' "$WORK/taxonomy/stderr.log"
grep -q "^benchmark\\.fasim_gasal2_traceback_rejection_taxonomy_export_path=$WORK/taxonomy.tsv$" "$WORK/taxonomy/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_traceback_rejection_taxonomy_export_rows=[1-9][0-9]*$' "$WORK/taxonomy/stderr.log"
grep -q '^benchmark\.fasim_gasal2_traceback_rejection_taxonomy_export_truncated=1$' "$WORK/taxonomy/stderr.log"

test -f "$WORK/taxonomy.tsv"
grep -q $'^attempt_id\ttask_id\tscoreinfo_index\tprealign_score\ttarget_size\tdecision_bucket\tpre_traceback_decidable\tpost_traceback_only\ttop5_only_safe_candidate\tfull_output_safe_candidate\temitted_row\tfinal_row\toutput_global_start\toutput_global_end\tscore\tnt\tidentity\tstability\tnotes$' "$WORK/taxonomy.tsv"
awk -F'\t' 'NR > 1 && $2 != "-1" && $3 != "-1" {found=1} END {exit found ? 0 : 1}' "$WORK/taxonomy.tsv"

line_count="$(wc -l <"$WORK/taxonomy.tsv")"
python3 - "$line_count" "$EXPORT_LIMIT" <<'PY'
import sys

line_count = int(sys.argv[1])
limit = int(sys.argv[2])
if line_count < 2:
    raise SystemExit("taxonomy export must contain header and at least one row")
if line_count > limit + 1:
    raise SystemExit(
        f"taxonomy export exceeded cap: lines={line_count}, limit={limit}"
    )
PY

python3 "$ROOT/scripts/summarize_fasim_gasal2_traceback_rejection_taxonomy.py" \
  --stderr "$WORK/taxonomy/stderr.log" \
  --label smoke \
  >"$WORK/taxonomy_summary.txt"

grep -Eq '^taxonomy_attempts=[1-9][0-9]*$' "$WORK/taxonomy_summary.txt"
grep -q '^taxonomy_unknown_attempts=0$' "$WORK/taxonomy_summary.txt"
grep -q $'^bucket\tattempts\tfraction_of_traceback_attempts\tfraction_of_gasal2_requests\tpre_traceback_decidable\tpost_traceback_only\ttop5_only_safe_candidate\tfull_output_safe_candidate\tnotes$' "$WORK/taxonomy_summary.txt"

baseline_traceback="$(metric_or_default "$WORK/baseline/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
taxonomy_traceback="$(metric_or_default "$WORK/taxonomy/stderr.log" benchmark.fasim_gasal2_traceback_requests 0)"
python3 - "$baseline_traceback" "$taxonomy_traceback" <<'PY'
import sys

baseline = int(float(sys.argv[1]))
taxonomy = int(float(sys.argv[2]))
if baseline <= 0:
    raise SystemExit("baseline traceback_requests must be positive")
if taxonomy <= 0:
    raise SystemExit("taxonomy traceback_requests must be positive")
if baseline != taxonomy:
    raise SystemExit(
        f"taxonomy must not change traceback_requests: {baseline} != {taxonomy}"
    )
print(f"traceback_requests={taxonomy}")
PY

cat "$WORK/top5_compare.txt"
cat "$WORK/taxonomy_summary.txt"
echo "ok"
