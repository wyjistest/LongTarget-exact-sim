#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

make tests/sim_initial_host_merge_context_apply_profile

CORPUS_DIR=".tmp/sim_initial_host_merge_real_census_cuda_2026-04-16_16-47-25/coverage_weighted_16_real/corpus"
CASE_ID="case-00000028"
WORK=$(mktemp -d /tmp/longtarget-same-workload-materiality-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

EMPTY_BENCH="$WORK/empty.stderr.log"
touch "$EMPTY_BENCH"

if scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
    --corpus-dir "$CORPUS_DIR" \
    --case "$CASE_ID" \
    --workload-id "check-empty" \
    --benchmark-stderr "$EMPTY_BENCH" \
    --output-dir "$WORK/out-empty" \
    --warmup-iterations 0 \
    --iterations 1; then
  echo "expected empty benchmark stderr to fail" >&2
  exit 1
fi

BENCH="$WORK/full_run.stderr.log"
cat >"$BENCH" <<'EOF'
benchmark.sim_initial_scan_seconds=2.5
benchmark.sim_initial_scan_cpu_merge_seconds=0.5
benchmark.sim_initial_scan_cpu_merge_subtotal_seconds=0.45
benchmark.sim_seconds=10.0
benchmark.total_seconds=20.0
EOF

scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir "$CORPUS_DIR" \
  --case "$CASE_ID" \
  --workload-id "check-same-workload" \
  --benchmark-stderr "$BENCH" \
  --output-dir "$WORK/out-ok" \
  --profile-mode lexical_first_half \
  --warmup-iterations 0 \
  --iterations 1

scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir "$CORPUS_DIR" \
  --case "$CASE_ID" \
  --workload-id "check-sampled" \
  --benchmark-stderr "$BENCH" \
  --output-dir "$WORK/out-sampled" \
  --profile-mode lexical_first_half_sampled \
  --profile-sample-log2 6 \
  --warmup-iterations 0 \
  --iterations 1

scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir "$CORPUS_DIR" \
  --case "$CASE_ID" \
  --workload-id "check-sampled-terminal-telemetry-on" \
  --benchmark-stderr "$BENCH" \
  --output-dir "$WORK/out-sampled-terminal-telemetry-on" \
  --profile-mode lexical_first_half_sampled \
  --terminal-telemetry-overhead on \
  --profile-sample-log2 6 \
  --warmup-iterations 0 \
  --iterations 1

scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir "$CORPUS_DIR" \
  --case "$CASE_ID" \
  --workload-id "check-sampled-no-terminal-telemetry" \
  --benchmark-stderr "$BENCH" \
  --output-dir "$WORK/out-sampled-no-terminal-telemetry" \
  --profile-mode lexical_first_half_sampled_no_terminal_telemetry \
  --profile-sample-log2 6 \
  --warmup-iterations 0 \
  --iterations 1

scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir "$CORPUS_DIR" \
  --case "$CASE_ID" \
  --workload-id "check-sampled-no-state-update-bookkeeping" \
  --benchmark-stderr "$BENCH" \
  --output-dir "$WORK/out-sampled-no-state-update-bookkeeping" \
  --profile-mode lexical_first_half_sampled_no_state_update_bookkeeping \
  --profile-sample-log2 6 \
  --warmup-iterations 0 \
  --iterations 1

SAME_PATH_DIR="$WORK/out-same-path"
mkdir -p "$SAME_PATH_DIR"
cat >"$SAME_PATH_DIR/full_run.stderr.log" <<'EOF'
benchmark.sim_initial_scan_seconds=2.5
benchmark.sim_initial_scan_cpu_merge_seconds=0.5
benchmark.sim_initial_scan_cpu_merge_subtotal_seconds=0.45
benchmark.sim_seconds=10.0
benchmark.total_seconds=20.0
EOF

scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh \
  --corpus-dir "$CORPUS_DIR" \
  --case "$CASE_ID" \
  --workload-id "check-same-path" \
  --benchmark-stderr "$SAME_PATH_DIR/full_run.stderr.log" \
  --output-dir "$SAME_PATH_DIR" \
  --profile-mode lexical_first_half_sampled \
  --profile-sample-log2 6 \
  --warmup-iterations 0 \
  --iterations 1

python3 - <<'PY' "$WORK/out-ok" "$CASE_ID"
import csv
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
case_id = sys.argv[2]
aggregate_tsv = out_dir / "cases" / f"{case_id}.aggregate.tsv"
benchmark_log = out_dir / "full_run.stderr.log"
min_decision = out_dir / "min_maintenance_profile" / "min_maintenance_profile_decision.json"
lifecycle_decision = out_dir / "candidate_index_lifecycle" / "candidate_index_lifecycle_decision.json"

assert aggregate_tsv.is_file(), aggregate_tsv
assert benchmark_log.is_file(), benchmark_log
assert benchmark_log.stat().st_size > 0, benchmark_log

with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))
assert row["workload_id"] == "check-same-workload", row
assert row["benchmark_source"] == str(benchmark_log), row
assert row["benchmark_source_original_path"] == str(Path(sys.argv[1]).parent / "full_run.stderr.log"), row
assert row["benchmark_source_copied_path"] == str(benchmark_log), row
assert row["benchmark_identity_basis"] == "content_sha256", row
assert row["benchmark_source_size_bytes"], row
assert row["benchmark_source_sha256"], row
assert row["profile_mode"] == "lexical_first_half", row
assert row["sim_initial_scan_cpu_merge_seconds_mean_seconds"] == "0.5", row
assert row["sim_seconds_mean_seconds"] == "10", row
assert row["total_seconds_mean_seconds"] == "20", row

min_data = json.loads(min_decision.read_text(encoding="utf-8"))
assert min_data["materiality_pairing_status"] == "complete", min_data
assert min_data["decision_status"] == "ready", min_data

lifecycle_data = json.loads(lifecycle_decision.read_text(encoding="utf-8"))
assert lifecycle_data["materiality_pairing_status"] == "complete", lifecycle_data
assert lifecycle_data["decision_status"] == "ready", lifecycle_data

lifecycle_summary = json.loads((out_dir / "candidate_index_lifecycle" / "candidate_index_lifecycle_summary.json").read_text(encoding="utf-8"))
assert lifecycle_summary["candidate_index"]["terminal_telemetry_overhead_mode_requested"] == "auto", lifecycle_summary["candidate_index"]
assert lifecycle_summary["candidate_index"]["terminal_telemetry_overhead_mode_effective"] == "on", lifecycle_summary["candidate_index"]

lifecycle_cases = out_dir / "candidate_index_lifecycle" / "candidate_index_lifecycle_cases.tsv"
with lifecycle_cases.open(newline="", encoding="utf-8") as handle:
    lifecycle_row = next(csv.DictReader(handle, delimiter="\t"))
assert lifecycle_row["profile_mode"] == "lexical_first_half", lifecycle_row
PY

python3 - <<'PY' "$WORK/out-sampled" "$CASE_ID"
import csv
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
case_id = sys.argv[2]
aggregate_tsv = out_dir / "cases" / f"{case_id}.aggregate.tsv"
with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))
assert row["profile_mode"] == "lexical_first_half_sampled", row
assert row["profile_sample_log2"] == "6", row
assert row["profile_sample_rate"] == "0.015625", row
assert row["terminal_telemetry_overhead_mode_requested"] == "auto", row
assert row["terminal_telemetry_overhead_mode_effective"] == "off", row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_covered_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count"], row
assert row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count"], row
assert row["dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_covered_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unclassified_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_multi_child_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_insert_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_update_existing_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_clear_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_overwrite_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_idempotent_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_value_changed_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_steps_total"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_covered_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unclassified_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_multi_child_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_bytes"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_bytes"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_bytes"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_entry_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_slot_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_key_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_entry_rewrite_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_cacheline_rewrite_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_back_to_back_same_entry_write_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_then_overwrite_same_entry_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_then_insert_same_entry_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_then_clear_same_entry_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_parent_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_scan_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_compare_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_branch_or_guard_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_bookkeeping_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_child_known_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_unexplained_mean_seconds"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_sampled_event_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_covered_sampled_event_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_total"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p50"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p90"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p99"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_full_scan_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_early_exit_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_found_existing_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_confirmed_absent_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_redundant_reprobe_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_same_key_reprobe_count"], row
assert row["context_apply_lookup_miss_candidate_set_full_probe_same_event_reprobe_count"], row
assert float(row["context_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_mean_seconds"]) == 0.0, row
repart_parent = float(row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds"])
repart_left = float(row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds"])
repart_right = float(row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds"])
repart_child_known = float(row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_mean_seconds"])
assert repart_parent >= repart_left, row
assert repart_parent >= repart_right, row
assert repart_parent >= repart_child_known, row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unclassified_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_multi_child_sampled_event_count"], row
assert row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_overlap_sampled_event_count"], row
PY

python3 - <<'PY' "$WORK/out-sampled-terminal-telemetry-on" "$CASE_ID"
import csv
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
case_id = sys.argv[2]
aggregate_tsv = out_dir / "cases" / f"{case_id}.aggregate.tsv"
with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))
assert row["profile_mode"] == "lexical_first_half_sampled", row
assert row["terminal_telemetry_overhead_mode_requested"] == "on", row
assert row["terminal_telemetry_overhead_mode_effective"] == "on", row
assert float(row["context_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_mean_seconds"]) >= 0.0, row
PY

python3 - <<'PY' "$WORK/out-sampled-no-terminal-telemetry" "$CASE_ID"
import csv
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
case_id = sys.argv[2]
aggregate_tsv = out_dir / "cases" / f"{case_id}.aggregate.tsv"
summary_json = out_dir / "candidate_index_lifecycle" / "candidate_index_lifecycle_summary.json"

with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))
assert row["profile_mode"] == "lexical_first_half_sampled_no_terminal_telemetry", row
assert row["profile_sample_log2"] == "6", row
assert row["terminal_telemetry_overhead_mode_effective"] == "off", row

summary = json.loads(summary_json.read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["terminal_path_telemetry_overhead_seconds"] == 0.0, candidate
assert candidate["seconds"] >= candidate["terminal_path_parent_seconds"], candidate
PY

python3 - <<'PY' "$WORK/out-sampled-no-state-update-bookkeeping" "$CASE_ID"
import csv
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
case_id = sys.argv[2]
aggregate_tsv = out_dir / "cases" / f"{case_id}.aggregate.tsv"
summary_json = out_dir / "candidate_index_lifecycle" / "candidate_index_lifecycle_summary.json"

with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))
assert row["profile_mode"] == "lexical_first_half_sampled_no_state_update_bookkeeping", row
assert row["profile_sample_log2"] == "6", row
assert row["state_update_bookkeeping_mode_requested"] == "off", row
assert row["state_update_bookkeeping_mode_effective"] == "off", row
assert row["terminal_telemetry_overhead_mode_effective"] == "off", row

summary = json.loads(summary_json.read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["state_update_bookkeeping_mode_requested"] == "off", candidate
assert candidate["state_update_bookkeeping_mode_effective"] == "off", candidate
assert candidate["terminal_path_state_update_trace_or_profile_bookkeeping_count"] == 0, candidate
assert candidate["terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count"] == 0, candidate
PY

python3 - <<'PY' "$WORK/out-sampled/candidate_index_lifecycle/candidate_index_lifecycle_summary.json" "$WORK/out-sampled-no-terminal-telemetry/candidate_index_lifecycle/candidate_index_lifecycle_summary.json" "$WORK/out-sampled-no-state-update-bookkeeping/candidate_index_lifecycle/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

with_summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
without_summary = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
without_bookkeeping_summary = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
assert with_summary["candidate_index"]["terminal_telemetry_overhead_mode_requested"] == "auto", with_summary["candidate_index"]
assert with_summary["candidate_index"]["terminal_telemetry_overhead_mode_effective"] == "off", with_summary["candidate_index"]
assert without_summary["candidate_index"]["terminal_telemetry_overhead_mode_effective"] == "off", without_summary["candidate_index"]
assert with_summary["candidate_index"]["terminal_path_telemetry_overhead_seconds"] == 0.0, with_summary["candidate_index"]
assert with_summary["candidate_index"]["state_update_bookkeeping_mode_requested"] == "auto", with_summary["candidate_index"]
assert with_summary["candidate_index"]["state_update_bookkeeping_mode_effective"] == "on", with_summary["candidate_index"]
assert without_bookkeeping_summary["candidate_index"]["state_update_bookkeeping_mode_requested"] == "off", without_bookkeeping_summary["candidate_index"]
assert without_bookkeeping_summary["candidate_index"]["state_update_bookkeeping_mode_effective"] == "off", without_bookkeeping_summary["candidate_index"]
for summary in (with_summary, without_summary, without_bookkeeping_summary):
    candidate = summary["candidate_index"]
    assert candidate["terminal_path_start_index_write_parent_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_write_left_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_write_right_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_write_child_known_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_write_unexplained_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_write_unexplained_share"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_write_sampled_count_closure_status"] in {
        "closed",
        "open",
        "unknown",
    }, candidate
    assert candidate["terminal_path_start_index_write_dominant_child"] in {
        "left",
        "right",
        "unknown",
    }, candidate
    assert candidate["terminal_path_start_index_write_probe_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_write_probe_steps_total"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_parent_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_insert_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_clear_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_overwrite_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_child_known_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_unexplained_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_unexplained_share"] >= 0.0, candidate
    assert candidate["terminal_path_start_index_store_sampled_count_closure_status"] in {
        "closed",
        "open",
        "unknown",
    }, candidate
    assert candidate["terminal_path_start_index_store_dominant_child"] in {
        "insert",
        "clear",
        "overwrite",
        "unknown",
    }, candidate
    assert candidate["terminal_path_start_index_store_insert_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_clear_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_overwrite_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_unique_entry_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_unique_slot_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_unique_key_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_same_entry_rewrite_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_same_cacheline_rewrite_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_back_to_back_same_entry_write_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_clear_then_overwrite_same_entry_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_overwrite_then_insert_same_entry_count"] >= 0, candidate
    assert candidate["terminal_path_start_index_store_insert_then_clear_same_entry_count"] >= 0, candidate
    assert candidate["terminal_path_state_update_trace_or_profile_bookkeeping_seconds"] >= 0.0, candidate
    assert candidate["terminal_path_state_update_trace_or_profile_bookkeeping_count"] >= 0, candidate
with_cases = {case["case_id"]: case for case in with_summary["cases"]}
without_cases = {case["case_id"]: case for case in without_summary["cases"]}
without_bookkeeping_cases = {
    case["case_id"]: case for case in without_bookkeeping_summary["cases"]
}
assert sorted(with_cases) == sorted(without_cases), (sorted(with_cases), sorted(without_cases))
assert sorted(with_cases) == sorted(without_bookkeeping_cases), (
    sorted(with_cases),
    sorted(without_bookkeeping_cases),
)

for case_id in sorted(with_cases):
    with_case = with_cases[case_id]
    without_case = without_cases[case_id]
    without_bookkeeping_case = without_bookkeeping_cases[case_id]
    for field in [
        "full_set_miss_count",
        "candidate_index_lookup_count",
        "candidate_index_insert_count",
        "candidate_index_erase_count",
        "terminal_path_event_count",
        "terminal_path_candidate_slot_write_count",
        "terminal_path_start_index_write_count",
        "terminal_path_state_update_count",
        "terminal_path_start_index_write_insert_count",
        "terminal_path_start_index_write_update_existing_count",
        "terminal_path_start_index_write_clear_count",
        "terminal_path_start_index_write_overwrite_count",
        "terminal_path_start_index_write_idempotent_count",
        "terminal_path_start_index_write_value_changed_count",
        "terminal_path_start_index_write_probe_count",
        "terminal_path_start_index_write_probe_steps_total",
        "terminal_path_start_index_store_insert_count",
        "terminal_path_start_index_store_clear_count",
        "terminal_path_start_index_store_overwrite_count",
    ]:
        assert int(round(float(with_case[field]))) == int(round(float(without_case[field]))), (
            case_id,
            field,
            with_case[field],
            without_case[field],
        )
        assert int(round(float(with_case[field]))) == int(round(float(without_bookkeeping_case[field]))), (
            case_id,
            field,
            with_case[field],
            without_bookkeeping_case[field],
        )
PY

python3 - <<'PY' "$SAME_PATH_DIR" "$CASE_ID"
import csv
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
case_id = sys.argv[2]
aggregate_tsv = out_dir / "cases" / f"{case_id}.aggregate.tsv"
benchmark_log = out_dir / "full_run.stderr.log"

assert aggregate_tsv.is_file(), aggregate_tsv
assert benchmark_log.is_file(), benchmark_log
assert benchmark_log.stat().st_size > 0, benchmark_log

with aggregate_tsv.open(newline="", encoding="utf-8") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))
assert row["workload_id"] == "check-same-path", row
assert row["benchmark_source"] == str(benchmark_log), row
required_state_update_fields = [
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_aux_updates_total",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_multi_child_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_sampled_event_count",
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source",
]
for field in required_state_update_fields:
    assert field in row, field
    if field == "context_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source":
        assert row[field] == "event_level_sampled", (field, row[field])
    else:
        assert float(row[field]) >= 0.0, (field, row[field])

sampled_event_count = int(float(row["context_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count"]))
covered_sampled_event_count = int(float(row["context_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count"]))
unclassified_sampled_event_count = int(float(row["context_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count"]))
heap_update_sampled_event_count = int(float(row["context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count"]))

assert sampled_event_count > 0, sampled_event_count
assert covered_sampled_event_count > 0, covered_sampled_event_count
assert covered_sampled_event_count <= sampled_event_count, (
    covered_sampled_event_count,
    sampled_event_count,
)
assert unclassified_sampled_event_count <= sampled_event_count, (
    unclassified_sampled_event_count,
    sampled_event_count,
)
assert heap_update_sampled_event_count > 0, heap_update_sampled_event_count
PY

echo "check_run_sim_initial_host_merge_same_workload_materiality_profile: PASS"
