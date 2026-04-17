#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
WORK_DIR="$ROOT_DIR/.tmp/check_project_whole_genome_runtime"
STDERR_LOG="$WORK_DIR/stderr.log"
REPORT_JSON="$WORK_DIR/report.json"

mkdir -p "$WORK_DIR"

cat >"$STDERR_LOG" <<'EOF'
benchmark.sim_solver_backend=cuda_window_pipeline
benchmark.calc_score_seconds=1
benchmark.calc_score_tasks_total=10
benchmark.calc_score_cuda_tasks=7
benchmark.calc_score_cpu_fallback_tasks=3
benchmark.calc_score_cpu_fallback_query_gt_8192=1
benchmark.calc_score_cpu_fallback_target_gt_8192=1
benchmark.calc_score_cpu_fallback_target_gt_65535=1
benchmark.sim_initial_scan_seconds=2
benchmark.sim_initial_scan_cpu_merge_seconds=0.5
benchmark.sim_initial_scan_cpu_merge_subtotal_seconds=0.4
benchmark.sim_initial_run_summary_pipeline_seconds=0.25
benchmark.sim_initial_ordered_replay_seconds=0.07
benchmark.sim_initial_store_rebuild_seconds=0.3
benchmark.sim_initial_store_materialize_seconds=0.2
benchmark.sim_initial_store_prune_seconds=0.1
benchmark.sim_initial_frontier_sync_seconds=0.05
benchmark.sim_initial_store_other_merge_seconds=0.15
benchmark.sim_initial_store_other_merge_context_apply_seconds=0.12
benchmark.sim_initial_store_other_merge_context_apply_lookup_seconds=0.07
benchmark.sim_initial_store_other_merge_context_apply_mutate_seconds=0.04
benchmark.sim_initial_store_other_merge_context_apply_finalize_seconds=0.01
benchmark.sim_initial_store_other_merge_context_apply_attempted_count=30
benchmark.sim_initial_store_other_merge_context_apply_modified_count=18
benchmark.sim_initial_store_other_merge_context_apply_noop_count=12
benchmark.sim_initial_store_other_merge_context_apply_lookup_hit_count=20
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_count=10
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_seconds=0.02
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_seconds=0.01
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_seconds=0.005
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_seconds=0.015
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_heap_build_seconds=0.004
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_heap_update_seconds=0.006
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds=0.002
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_seconds=0.003
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds=0.0009
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds=0.0006
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds=0.0003
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_seconds=0.0012
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds=0.0002
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds=0.0005
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds=0.0001
benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_seconds=0.0004
benchmark.sim_initial_store_other_merge_residual_seconds=0.03
benchmark.sim_seconds=3
benchmark.postprocess_seconds=1
benchmark.total_seconds=5
benchmark.sim_window_pipeline_tasks_considered=10
benchmark.sim_window_pipeline_tasks_eligible=8
benchmark.sim_window_pipeline_task_fallbacks=2
EOF

python3 "$ROOT_DIR/scripts/project_whole_genome_runtime.py" \
  --stderr "$STDERR_LOG" \
  --sample-bp 100 \
  --genome-bp 1000 \
  --parallel-workers 2 \
  --json >"$REPORT_JSON"

python3 - "$REPORT_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

assert data["sample_bp"] == 100
assert data["genome_bp"] == 1000
assert data["parallel_workers"] == 2
assert abs(data["scale_factor"] - 5.0) < 1e-9
assert abs(data["projected_total_seconds"] - 25.0) < 1e-9
assert abs(data["projected_calc_score_seconds"] - 5.0) < 1e-9
assert abs(data["projected_sim_seconds"] - 15.0) < 1e-9
assert abs(data["projected_postprocess_seconds"] - 5.0) < 1e-9
assert abs(data["projected_sim_initial_scan_seconds"] - 10.0) < 1e-9
assert abs(data["projected_sim_initial_scan_cpu_merge_seconds"] - 2.5) < 1e-9
assert abs(data["projected_sim_initial_scan_cpu_merge_subtotal_seconds"] - 2.0) < 1e-9
assert abs(data["projected_sim_initial_run_summary_pipeline_seconds"] - 1.25) < 1e-9
assert abs(data["projected_sim_initial_ordered_replay_seconds"] - 0.35) < 1e-9
assert abs(data["projected_sim_initial_store_rebuild_seconds"] - 1.5) < 1e-9
assert abs(data["projected_sim_initial_store_materialize_seconds"] - 1.0) < 1e-9
assert abs(data["projected_sim_initial_store_prune_seconds"] - 0.5) < 1e-9
assert abs(data["projected_sim_initial_frontier_sync_seconds"] - 0.25) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_seconds"] - 0.75) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_seconds"] - 0.6) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_seconds"] - 0.35) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_mutate_seconds"] - 0.2) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_finalize_seconds"] - 0.05) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_seconds"] - 0.1) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_seconds"] - 0.05) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_seconds"] - 0.025) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_seconds"] - 0.075) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_heap_build_seconds"] - 0.02) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_heap_update_seconds"] - 0.03) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds"] - 0.01) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_seconds"] - 0.015) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds"] - 0.0045) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds"] - 0.003) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds"] - 0.0015) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_seconds"] - 0.006) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds"] - 0.001) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds"] - 0.0025) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds"] - 0.0005) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_seconds"] - 0.002) < 1e-9
assert abs(data["projected_sim_initial_store_other_merge_residual_seconds"] - 0.15) < 1e-9
assert abs(data["window_pipeline_eligible_ratio"] - 0.8) < 1e-9
assert abs(data["window_pipeline_fallback_ratio"] - 0.2) < 1e-9
assert abs(data["calc_score_cuda_task_ratio"] - 0.7) < 1e-9
assert abs(data["calc_score_cpu_fallback_ratio"] - 0.3) < 1e-9
assert data["benchmark"]["sim_solver_backend"] == "cuda_window_pipeline"
assert data["benchmark"]["calc_score_tasks_total"] == 10
assert data["benchmark"]["sim_window_pipeline_tasks_considered"] == 10
PY

cat >"$STDERR_LOG" <<'EOF'
benchmark.sim_solver_backend=cuda_window_pipeline
benchmark.calc_score_seconds=1
benchmark.sim_seconds=3
benchmark.postprocess_seconds=1
benchmark.total_seconds=5
EOF

python3 "$ROOT_DIR/scripts/project_whole_genome_runtime.py" \
  --stderr "$STDERR_LOG" \
  --sample-bp 100 \
  --genome-bp 1000 \
  --parallel-workers 2 \
  --json >"$REPORT_JSON"

python3 - "$REPORT_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

assert "window_pipeline_eligible_ratio" not in data
assert "window_pipeline_fallback_ratio" not in data
assert "calc_score_cuda_task_ratio" not in data
assert "calc_score_cpu_fallback_ratio" not in data
assert "projected_sim_initial_scan_seconds" not in data
assert "projected_sim_initial_scan_cpu_merge_seconds" not in data
assert "projected_sim_initial_scan_cpu_merge_subtotal_seconds" not in data
assert "projected_sim_initial_run_summary_pipeline_seconds" not in data
assert "projected_sim_initial_ordered_replay_seconds" not in data
assert "projected_sim_initial_store_rebuild_seconds" not in data
assert "projected_sim_initial_store_materialize_seconds" not in data
assert "projected_sim_initial_store_prune_seconds" not in data
assert "projected_sim_initial_frontier_sync_seconds" not in data
assert "projected_sim_initial_store_other_merge_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_mutate_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_finalize_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_heap_build_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_heap_update_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds" not in data
assert "projected_sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_seconds" not in data
assert "projected_sim_initial_store_other_merge_residual_seconds" not in data
PY
