#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_meg3_full_formal_group32"}"
UNGROUPED_WORK="${UNGROUPED_WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_meg3_full_formal"}"

aggregate="$WORK/aggregate.tsv"
summary="$WORK/summary.tsv"
run_dir="$WORK/runs/MEG3-ENST00000451743-DNAseq_r1"
cpu_report="$run_dir/cpu_summary/report.json"
candidate_report="$run_dir/column_pruned_preset/report.json"
ungrouped_cpu_report="$UNGROUPED_WORK/runs/MEG3-ENST00000451743-DNAseq_r1/cpu_summary/report.json"

for path in "$aggregate" "$summary" "$cpu_report" "$candidate_report" "$ungrouped_cpu_report"; do
  if [[ ! -s "$path" ]]; then
    echo "missing MEG3 grouped milestone artifact: $path" >&2
    echo "generate with GROUP_TARGET_RECORDS=32 scripts/characterize_fasim_gasal2_column_pruned_preset_top5_matrix.sh" >&2
    exit 1
  fi
done

python3 - "$aggregate" "$summary" "$candidate_report" <<'PY'
import csv
import json
import sys
from pathlib import Path

aggregate = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
summary = list(csv.DictReader(Path(sys.argv[2]).open(newline="", encoding="utf-8"), delimiter="\t"))
candidate = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

if len(aggregate) != 1:
    raise SystemExit(f"expected one aggregate row, got {len(aggregate)}")
if len(summary) != 1:
    raise SystemExit(f"expected one summary row, got {len(summary)}")

agg = aggregate[0]
row = summary[0]
if agg.get("decision") != "top5_artifact_go":
    raise SystemExit(f"unexpected aggregate decision: {agg}")
for key in (
    "artifact_checked_runs",
    "top5_clean_runs",
    "active_path_runs",
    "zero_legacy_score_runs",
    "zero_overflow_runs",
    "zero_fallback_runs",
    "zero_gasal2_fallback_runs",
    "zero_length_guard_fallback_runs",
    "positive_gasal2_request_runs",
    "positive_exact_scoreinfo_task_runs",
):
    if agg.get(key) != "1":
        raise SystemExit(f"{key} is not 1: {agg}")

if row.get("group_target_records") != "32":
    raise SystemExit(f"unexpected group_target_records: {row}")
if row.get("cpu_shard_count") != "17" or row.get("preset_shard_count") != "17":
    raise SystemExit(f"unexpected shard counts: {row}")
for key in (
    "artifact_checked",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_all_equal",
    "preset_active_path",
):
    if row.get(key) != "true":
        raise SystemExit(f"{key} is not true: {row}")
for key in (
    "preset_gasal2_fallbacks",
    "preset_length_guard_fallbacks",
    "preset_legacy_score_gpu_requests",
    "preset_overflow_batches",
    "preset_fallback_batches",
):
    if row.get(key) != "0":
        raise SystemExit(f"{key} is not zero: {row}")
for key in (
    "preset_gasal2_requests",
    "preset_traceback_requests",
    "preset_exact_scoreinfo_gpu_tasks",
):
    if int(row.get(key) or "0") <= 0:
        raise SystemExit(f"{key} is not positive: {row}")
if float(row.get("speedup_vs_cpu_worker_wall_sum") or "0") <= 1.0:
    raise SystemExit(f"MEG3 grouped candidate did not beat CPU worker wall sum: {row}")
if float(row.get("speedup_vs_cpu_max_worker_wall") or "0") <= 1.0:
    raise SystemExit(f"MEG3 grouped candidate did not beat CPU max worker wall: {row}")

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
    if candidate.get(key) != value:
        raise SystemExit(f"candidate report {key}={candidate.get(key)!r}, expected {value!r}")

sums = candidate.get("fasim_benchmark_sums", {})
expected_positive = (
    "fasim_gasal2_requests",
    "fasim_gasal2_traceback_requests",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks",
)
for key in expected_positive:
    if float(sums.get(key, 0)) <= 0:
        raise SystemExit(f"candidate benchmark {key} is not positive: {sums}")
expected_zero = (
    "fasim_gasal2_fallbacks",
    "fasim_gasal2_length_guard_fallbacks",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches",
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches",
)
for key in expected_zero:
    if float(sums.get(key, 0)) != 0:
        raise SystemExit(f"candidate benchmark {key} is not zero: {sums}")

required_env = {
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
    "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
    "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "64",
    "FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE": "1",
    "FASIM_PREALIGN_CUDA_MAX_TASKS": "16384",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU": "1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK": "512",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT": "1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT": "1",
    "FASIM_OUTPUT_TOPK_LITE": "5",
}
env = candidate.get("env_overrides", {})
for key, value in required_env.items():
    if env.get(key) != value:
        raise SystemExit(f"candidate env {key}={env.get(key)!r}, expected {value!r}")
PY

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$cpu_report"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$candidate_report" \
  --same-payload-as "$cpu_report"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$cpu_report" \
  --same-payload-as "$ungrouped_cpu_report"

echo "ok"
