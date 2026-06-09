#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_cuda"}"
GASAL2_BIN="${GASAL2_BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_top5_binary_guard"}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-cuda
  )
fi

if [[ ! -x "$GASAL2_BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$GASAL2_BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK"
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

first_records_fasta \
  "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
  "$WORK/malat1_first1.fa" \
  1

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$ROOT/testDNA.fa" \
  --rna "$ROOT/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/not_built" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  >"$WORK/not_built.stdout.log" \
  2>"$WORK/not_built.stderr.log"; then
  echo "expected GASAL2 column-pruned preset with non-GASAL2 binary to fail" >&2
  exit 1
fi

grep -q -- "--gasal2-top5-column-pruned-scoreinfo requires a GASAL2-enabled Fasim binary" \
  "$WORK/not_built.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$ROOT/testDNA.fa" \
  --rna "$ROOT/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/not_built_scoreinfo_prune" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --shard-output-topk-lite 5 \
  --gasal2-top5-scoreinfo-prune-max-per-task 64 \
  --exact-scoreinfo-gpu-max-per-task 512 \
  --exact-scoreinfo-gpu-pruned-output \
  >"$WORK/not_built_scoreinfo_prune.stdout.log" \
  2>"$WORK/not_built_scoreinfo_prune.stderr.log"; then
  echo "expected GASAL2 scoreInfo preset with non-GASAL2 binary to fail" >&2
  exit 1
fi

grep -q -- "GASAL2 scoreInfo/preAlign runner options require a GASAL2-enabled Fasim binary" \
  "$WORK/not_built_scoreinfo_prune.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$GASAL2_BIN" \
  --target "$ROOT/testDNA.fa" \
  --rna "$ROOT/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/built_self_contained" \
  --gasal2-top5-column-pruned-scoreinfo \
  >"$WORK/built_self_contained.stdout.log" \
  2>"$WORK/built_self_contained.stderr.log"; then
  :
else
  echo "expected GASAL2-enabled formal preset to be self-contained" >&2
  exit 1
fi

if grep -q -- "requires a GASAL2-enabled Fasim binary" \
  "$WORK/built_self_contained.stderr.log"; then
  echo "GASAL2-enabled binary was rejected by binary guard" >&2
  exit 1
fi
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/built_self_contained/report.json"
python3 - "$WORK/built_self_contained/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["run_status"] == "completed", report
assert report["output_mode"] == "lite", report
assert report["topk_summary_only"] is True, report
assert report["shard_output_topk_lite"] == 5, report
assert report["gasal2_top5_column_pruned_scoreinfo"] is True, report
assert report["gasal2_top5_activation_verified"] is True, report
assert report["gasal2_top5_activation_error"] is None, report
assert report["topk_summary"]["k"] == 5, report
assert Path(report["topk_summary_output"]).exists(), report
assert len(report["topk_summary_digest"]) == 64, report
assert Path(report["topk_rows_output"]).exists(), report
assert len(report["topk_rows_digest"]) == 64, report
assert Path(report["topk_lite_output"]).exists(), report
assert len(report["topk_lite_digest"]) == 64, report
PY

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$GASAL2_BIN" \
  --target "$WORK/malat1_first1.fa" \
  --rna "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
  --rule 0 \
  --work-dir "$WORK/long_query_not_active" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  >"$WORK/long_query_not_active.stdout.log" \
  2>"$WORK/long_query_not_active.stderr.log"; then
  echo "expected formal GASAL2 top5 preset with inactive long-query path to fail" >&2
  exit 1
fi

grep -q -- "--gasal2-top5-column-pruned-scoreinfo requires active GASAL2/exact-scoreInfo GPU shards" \
  "$WORK/long_query_not_active.stderr.log"
grep -q -- "query length" "$WORK/long_query_not_active.stderr.log"
if [[ -e "$WORK/long_query_not_active/report.json" ||
      -d "$WORK/long_query_not_active/shard_outputs" ||
      -d "$WORK/long_query_not_active/logs" ]]; then
  echo "expected long-query formal preset rejection before shard execution" >&2
  exit 1
fi

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$GASAL2_BIN" \
  --target "$WORK/malat1_first1.fa" \
  --rna "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
  --rule 0 \
  --work-dir "$WORK/formal_raised_query_guard" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  --env FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=8708 \
  >"$WORK/formal_raised_query_guard.stdout.log" \
  2>"$WORK/formal_raised_query_guard.stderr.log"; then
  echo "expected formal GASAL2 top5 preset with raised query guard to fail" >&2
  exit 1
fi

grep -q -- "--gasal2-top5-column-pruned-scoreinfo cannot override FASIM_ALIGN_GASAL2_MAX_QUERY_LEN above verified limit" \
  "$WORK/formal_raised_query_guard.stderr.log"
if [[ -e "$WORK/formal_raised_query_guard/report.json" ||
      -d "$WORK/formal_raised_query_guard/shard_outputs" ||
      -d "$WORK/formal_raised_query_guard/logs" ]]; then
  echo "expected raised-query-guard formal preset rejection before shard execution" >&2
  exit 1
fi

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$GASAL2_BIN" \
  --target "$WORK/malat1_first1.fa" \
  --rna "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
  --rule 0 \
  --work-dir "$WORK/formal_disabled_query_guard" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  --env FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=0 \
  >"$WORK/formal_disabled_query_guard.stdout.log" \
  2>"$WORK/formal_disabled_query_guard.stderr.log"; then
  echo "expected formal GASAL2 top5 preset with disabled query guard to fail" >&2
  exit 1
fi

grep -q -- "--gasal2-top5-column-pruned-scoreinfo requires positive FASIM_ALIGN_GASAL2_MAX_QUERY_LEN" \
  "$WORK/formal_disabled_query_guard.stderr.log"
if [[ -e "$WORK/formal_disabled_query_guard/report.json" ||
      -d "$WORK/formal_disabled_query_guard/shard_outputs" ||
      -d "$WORK/formal_disabled_query_guard/logs" ]]; then
  echo "expected disabled-query-guard formal preset rejection before shard execution" >&2
  exit 1
fi

echo "ok"
