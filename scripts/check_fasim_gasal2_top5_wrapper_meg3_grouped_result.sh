#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/fasim_gasal2_meg3_group32_topk"}"
AUTHORITY_WORK="${AUTHORITY_WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_meg3_full_formal_group32"}"

report="$WORK/report.json"
summary="$WORK/summary.tsv"
manifest="$WORK/run_manifest.json"
authority_cpu_report="$AUTHORITY_WORK/runs/MEG3-ENST00000451743-DNAseq_r1/cpu_summary/report.json"

for path in "$report" "$summary" "$manifest" "$authority_cpu_report"; do
  if [[ ! -s "$path" ]]; then
    echo "missing MEG3 wrapper grouped artifact: $path" >&2
    echo "generate with GROUP_TARGET_RECORDS=32 scripts/run_fasim_gasal2_topk_lite.sh" >&2
    exit 1
  fi
done

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$report" \
  --manifest "$manifest" \
  --same-payload-as "$authority_cpu_report"

python3 - "$report" "$summary" <<'PY'
import csv
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows = list(csv.DictReader(Path(sys.argv[2]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one wrapper summary row, got {len(rows)}")
summary = rows[0]

expected_report = {
    "run_status": "completed",
    "target_record_count": 532,
    "group_target_records": 32,
    "grouped_shard_count": 17,
    "shard_count": 17,
    "fasim_benchmark_shards": 17,
    "result_contract": "gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "topk_summary_only": True,
    "shard_output_topk_lite": 5,
    "gasal2_top5_column_pruned_scoreinfo": True,
    "gasal2_top5_scoreinfo_prune_max_per_task": 64,
    "exact_scoreinfo_gpu_max_per_task": 512,
    "exact_scoreinfo_gpu_pruned_output": True,
    "exact_scoreinfo_gpu_column_pruned_output": True,
    "gasal2_top5_activation_verified": True,
    "gasal2_top5_activation_error": None,
    "gasal2_top5_query_preflight_supported": True,
    "gasal2_top5_query_preflight_error": None,
    "gasal2_top5_query_preflight_query_len": 1582,
    "gasal2_top5_query_preflight_max_query_len": 2812,
}
for key, value in expected_report.items():
    if report.get(key) != value:
        raise SystemExit(f"report {key}={report.get(key)!r}, expected {value!r}")

expected_summary = {
    "rule": "0",
    "k": "5",
    "contract": "gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "topk_lite_records": "15",
    "run_status": "completed",
    "group_target_records": "32",
    "grouped_shard_count": "17",
    "activation_verified": "true",
    "query_preflight_supported": "true",
    "query_preflight_query_len": "1582",
    "query_preflight_max_query_len": "2812",
    "gasal2_fallbacks": "0",
    "length_guard_fallbacks": "0",
}
for key, value in expected_summary.items():
    if summary.get(key) != value:
        raise SystemExit(f"summary {key}={summary.get(key)!r}, expected {value!r}: {summary}")

sums = report.get("fasim_benchmark_sums", {})
positive = {
    "fasim_gasal2_requests": int(summary["gasal2_requests"]),
    "fasim_gasal2_traceback_requests": int(summary["gasal2_traceback_requests"]),
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks": int(summary["exact_scoreinfo_gpu_tasks"]),
}
for key, summary_value in positive.items():
    if summary_value <= 0:
        raise SystemExit(f"summary {key} is not positive: {summary}")
    if int(sums.get(key, 0)) != summary_value:
        raise SystemExit(f"summary/report mismatch for {key}: {summary_value} vs {sums.get(key)}")

zero = (
    "fasim_gasal2_fallbacks",
    "fasim_gasal2_length_guard_fallbacks",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
)
for key in zero:
    if int(sums.get(key, 0)) != 0:
        raise SystemExit(f"benchmark {key} is not zero: {sums}")

topk_lite = Path(report["topk_lite_output"])
top5_lite = Path(report["topk_lite_output"]).with_name("top5.lite")
if not top5_lite.exists():
    raise SystemExit(f"missing wrapper top5 copy: {top5_lite}")
if topk_lite.read_bytes() != top5_lite.read_bytes():
    raise SystemExit("wrapper top5.lite does not match topk-TFOsorted.lite")
PY

echo "ok"
