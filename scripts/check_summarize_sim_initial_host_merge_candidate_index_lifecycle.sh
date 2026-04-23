#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-candidate-index-lifecycle-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

HEADER=$(printf '%b' "case_id\tcandidate_index_backend\tprofile_mode\twarmup_iterations\titerations\tlogical_event_count\tcontext_candidate_count_after_context_apply\tcontext_apply_attempted_count\tcontext_apply_modified_count\tcontext_apply_noop_count\tcontext_apply_lookup_hit_count\tcontext_apply_full_set_miss_count\tcontext_apply_floor_changed_count\tcontext_apply_floor_changed_share\tcontext_apply_running_min_slot_changed_count\tcontext_apply_running_min_slot_changed_share\tcontext_apply_victim_was_running_min_count\tcontext_apply_victim_was_running_min_share\tcontext_apply_refresh_min_calls\tcontext_apply_refresh_min_slots_scanned\tcontext_apply_refresh_min_slots_scanned_per_call\tcontext_apply_candidate_index_lookup_count\tcontext_apply_candidate_index_hit_count\tcontext_apply_candidate_index_miss_count\tcontext_apply_candidate_index_erase_count\tcontext_apply_candidate_index_insert_count\tcontext_apply_lookup_miss_count\tcontext_apply_lookup_probe_steps_total\tcontext_apply_lookup_probe_steps_max\tcontext_apply_lookup_miss_open_slot_count\tcontext_apply_lookup_miss_candidate_set_full_count\tcontext_apply_eviction_selected_count\tcontext_apply_reused_slot_count\tcontext_apply_mean_seconds\tcontext_apply_p50_seconds\tcontext_apply_p95_seconds\tcontext_apply_full_set_miss_mean_seconds\tcontext_apply_full_set_miss_p50_seconds\tcontext_apply_full_set_miss_p95_seconds\tcontext_apply_refresh_min_mean_seconds\tcontext_apply_refresh_min_p50_seconds\tcontext_apply_refresh_min_p95_seconds\tcontext_apply_candidate_index_mean_seconds\tcontext_apply_candidate_index_p50_seconds\tcontext_apply_candidate_index_p95_seconds\tcontext_apply_candidate_index_erase_mean_seconds\tcontext_apply_candidate_index_erase_p50_seconds\tcontext_apply_candidate_index_erase_p95_seconds\tcontext_apply_candidate_index_insert_mean_seconds\tcontext_apply_candidate_index_insert_p50_seconds\tcontext_apply_candidate_index_insert_p95_seconds\tcontext_apply_lookup_mean_seconds\tcontext_apply_lookup_p50_seconds\tcontext_apply_lookup_p95_seconds\tcontext_apply_lookup_miss_mean_seconds\tcontext_apply_lookup_miss_p50_seconds\tcontext_apply_lookup_miss_p95_seconds\tcontext_apply_lookup_miss_open_slot_mean_seconds\tcontext_apply_lookup_miss_open_slot_p50_seconds\tcontext_apply_lookup_miss_open_slot_p95_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_mean_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_p50_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_p95_seconds\tcontext_apply_lookup_miss_eviction_select_mean_seconds\tcontext_apply_lookup_miss_eviction_select_p50_seconds\tcontext_apply_lookup_miss_eviction_select_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_p95_SECONDS\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_p95_SECONDS\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_p95_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_p95_SECONDS\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_p95_SECONDS\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_p95_SECONDS\tcontext_apply_mutate_mean_seconds\tcontext_apply_mutate_p50_seconds\tcontext_apply_mutate_p95_seconds\tcontext_apply_finalize_mean_seconds\tcontext_apply_finalize_p50_SECONDS\tcontext_apply_finalize_p95_SECONDS\tverify_ok\tsim_initial_scan_cpu_merge_seconds_mean_seconds\tsim_seconds_mean_seconds\ttotal_seconds_mean_seconds\tworkload_id\tbenchmark_source")

write_profile_tsv() {
  local path="$1"
  local case_id="$2"
  local context_apply_mean="$3"
  local candidate_index_mean="$4"
  local candidate_index_erase_mean="$5"
  local candidate_index_insert_mean="$6"
  local lookup_mean="$7"
  local lookup_miss_mean="$8"
  local lookup_miss_open_slot_mean="$9"
  local lookup_miss_candidate_set_full_probe_mean="${10}"
  local lookup_miss_eviction_select_mean="${11}"
  local lookup_miss_reuse_writeback_mean="${12}"
  local lookup_miss_reuse_writeback_aux_start_index_rebuild_mean="${13}"
  local lookup_miss_reuse_writeback_aux_other_mean="${14}"
  local candidate_lookup_count="${15}"
  local candidate_hit_count="${16}"
  local candidate_miss_count="${17}"
  local candidate_erase_count="${18}"
  local candidate_insert_count="${19}"
  local full_set_miss_count="${20}"
  local sim_seconds_mean="${21}"
  local sim_initial_scan_cpu_merge_mean="${22}"
  local total_seconds_mean="${23}"
  local lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean="${24}"
  local lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean="${25}"
  local lookup_miss_reuse_writeback_aux_other_trace_finalize_mean="${26}"
  local lookup_miss_reuse_writeback_aux_other_residual_mean="${27}"
  local workload_id="${28:-}"
  local benchmark_source="${29:-}"
  local profile_mode="${30:-terminal}"

  cat >"$path" <<EOF
${HEADER}
${case_id}	tombstone	${profile_mode}	1	5	1000	64	1000	1000	0	${candidate_hit_count}	${full_set_miss_count}	80	0.80	75	0.75	60	0.60	0	0	0.0	${candidate_lookup_count}	${candidate_hit_count}	${candidate_miss_count}	${candidate_erase_count}	${candidate_insert_count}	${candidate_miss_count}	4096	17	8	${full_set_miss_count}	${full_set_miss_count}	${full_set_miss_count}	${context_apply_mean}	${context_apply_mean}	${context_apply_mean}	0.20	0.20	0.20	0.00	0.00	0.00	${candidate_index_mean}	${candidate_index_mean}	${candidate_index_mean}	${candidate_index_erase_mean}	${candidate_index_erase_mean}	${candidate_index_erase_mean}	${candidate_index_insert_mean}	${candidate_index_insert_mean}	${candidate_index_insert_mean}	${lookup_mean}	${lookup_mean}	${lookup_mean}	${lookup_miss_mean}	${lookup_miss_mean}	${lookup_miss_mean}	${lookup_miss_open_slot_mean}	${lookup_miss_open_slot_mean}	${lookup_miss_open_slot_mean}	${lookup_miss_candidate_set_full_probe_mean}	${lookup_miss_candidate_set_full_probe_mean}	${lookup_miss_candidate_set_full_probe_mean}	${lookup_miss_eviction_select_mean}	${lookup_miss_eviction_select_mean}	${lookup_miss_eviction_select_mean}	${lookup_miss_reuse_writeback_mean}	${lookup_miss_reuse_writeback_mean}	${lookup_miss_reuse_writeback_mean}	0.04	0.04	0.04	0.05	0.05	0.05	0.03	0.03	0.03	0.08	0.08	0.08	0.00	0.00	0.00	0.06	0.06	0.06	${lookup_miss_reuse_writeback_aux_start_index_rebuild_mean}	${lookup_miss_reuse_writeback_aux_start_index_rebuild_mean}	${lookup_miss_reuse_writeback_aux_start_index_rebuild_mean}	${lookup_miss_reuse_writeback_aux_other_mean}	${lookup_miss_reuse_writeback_aux_other_mean}	${lookup_miss_reuse_writeback_aux_other_mean}	${lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean}	${lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean}	${lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean}	${lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean}	${lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean}	${lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean}	${lookup_miss_reuse_writeback_aux_other_trace_finalize_mean}	${lookup_miss_reuse_writeback_aux_other_trace_finalize_mean}	${lookup_miss_reuse_writeback_aux_other_trace_finalize_mean}	${lookup_miss_reuse_writeback_aux_other_residual_mean}	${lookup_miss_reuse_writeback_aux_other_residual_mean}	${lookup_miss_reuse_writeback_aux_other_residual_mean}	0.02	0.02	0.02	0.01	0.01	0.01	1	${sim_initial_scan_cpu_merge_mean}	${sim_seconds_mean}	${total_seconds_mean}	${workload_id}	${benchmark_source}
EOF
}

run_and_assert() {
  local output_dir="$1"
  shift
  python3 ./scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py "$@" --output-dir "$output_dir"
}

inject_start_index_write_split() {
  local path="$1"
  local parent_seconds="$2"
  local left_seconds="$3"
  local right_seconds="$4"
  local sampled_event_count="$5"
  local covered_sampled_event_count="$6"
  local unclassified_sampled_event_count="$7"
  local multi_child_sampled_event_count="$8"
  local left_sampled_event_count="$9"
  local right_sampled_event_count="${10}"
  local insert_count="${11}"
  local update_existing_count="${12}"
  local clear_count="${13}"
  local overwrite_count="${14}"
  local idempotent_count="${15}"
  local value_changed_count="${16}"
  local probe_count="${17}"
  local probe_steps_total="${18}"
  python3 - <<'PY' "$path" "$parent_seconds" "$left_seconds" "$right_seconds" \
    "$sampled_event_count" "$covered_sampled_event_count" "$unclassified_sampled_event_count" \
    "$multi_child_sampled_event_count" "$left_sampled_event_count" "$right_sampled_event_count" \
    "$insert_count" "$update_existing_count" "$clear_count" "$overwrite_count" \
    "$idempotent_count" "$value_changed_count" "$probe_count" "$probe_steps_total"
import csv
import sys
from pathlib import Path

(
    path_str,
    parent_seconds,
    left_seconds,
    right_seconds,
    sampled_event_count,
    covered_sampled_event_count,
    unclassified_sampled_event_count,
    multi_child_sampled_event_count,
    left_sampled_event_count,
    right_sampled_event_count,
    insert_count,
    update_existing_count,
    clear_count,
    overwrite_count,
    idempotent_count,
    value_changed_count,
    probe_count,
    probe_steps_total,
) = sys.argv[1:]

path = Path(path_str)
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

row = rows[0]
updates = {
    "profile_mode": "lexical_first_half_sampled",
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_mean_seconds": parent_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_mean_seconds": left_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_mean_seconds": right_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_mean_seconds": str(
        float(left_seconds) + float(right_seconds)
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_mean_seconds": str(
        max(float(parent_seconds) - float(left_seconds) - float(right_seconds), 0.0)
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_sampled_event_count": sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_covered_sampled_event_count": covered_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unclassified_sampled_event_count": unclassified_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_multi_child_sampled_event_count": multi_child_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_sampled_event_count": left_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_sampled_event_count": right_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_insert_count": insert_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_update_existing_count": update_existing_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_clear_count": clear_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_overwrite_count": overwrite_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_idempotent_count": idempotent_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_value_changed_count": value_changed_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_count": probe_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_steps_total": probe_steps_total,
}
row.update(updates)
fieldnames = list(rows[0].keys())
for field in updates:
    if field not in fieldnames:
        fieldnames.append(field)

with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
}

inject_start_index_store_split() {
  local path="$1"
  local parent_seconds="$2"
  local insert_seconds="$3"
  local clear_seconds="$4"
  local overwrite_seconds="$5"
  local sampled_event_count="$6"
  local covered_sampled_event_count="$7"
  local unclassified_sampled_event_count="$8"
  local multi_child_sampled_event_count="$9"
  local insert_sampled_event_count="${10}"
  local clear_sampled_event_count="${11}"
  local overwrite_sampled_event_count="${12}"
  local insert_count="${13}"
  local clear_count="${14}"
  local overwrite_count="${15}"
  local insert_bytes="${16}"
  local clear_bytes="${17}"
  local overwrite_bytes="${18}"
  local unique_entry_count="${19}"
  local unique_slot_count="${20}"
  local unique_key_count="${21}"
  local same_entry_rewrite_count="${22}"
  local same_cacheline_rewrite_count="${23}"
  local back_to_back_same_entry_write_count="${24}"
  local clear_then_overwrite_same_entry_count="${25}"
  local overwrite_then_insert_same_entry_count="${26}"
  local insert_then_clear_same_entry_count="${27}"
  python3 - <<'PY' "$path" "$parent_seconds" "$insert_seconds" "$clear_seconds" "$overwrite_seconds" \
    "$sampled_event_count" "$covered_sampled_event_count" "$unclassified_sampled_event_count" \
    "$multi_child_sampled_event_count" "$insert_sampled_event_count" "$clear_sampled_event_count" \
    "$overwrite_sampled_event_count" "$insert_count" "$clear_count" "$overwrite_count" \
    "$insert_bytes" "$clear_bytes" "$overwrite_bytes" "$unique_entry_count" "$unique_slot_count" \
    "$unique_key_count" "$same_entry_rewrite_count" "$same_cacheline_rewrite_count" \
    "$back_to_back_same_entry_write_count" "$clear_then_overwrite_same_entry_count" \
    "$overwrite_then_insert_same_entry_count" "$insert_then_clear_same_entry_count"
import csv
import sys
from pathlib import Path

(
    path_str,
    parent_seconds,
    insert_seconds,
    clear_seconds,
    overwrite_seconds,
    sampled_event_count,
    covered_sampled_event_count,
    unclassified_sampled_event_count,
    multi_child_sampled_event_count,
    insert_sampled_event_count,
    clear_sampled_event_count,
    overwrite_sampled_event_count,
    insert_count,
    clear_count,
    overwrite_count,
    insert_bytes,
    clear_bytes,
    overwrite_bytes,
    unique_entry_count,
    unique_slot_count,
    unique_key_count,
    same_entry_rewrite_count,
    same_cacheline_rewrite_count,
    back_to_back_same_entry_write_count,
    clear_then_overwrite_same_entry_count,
    overwrite_then_insert_same_entry_count,
    insert_then_clear_same_entry_count,
) = sys.argv[1:]

path = Path(path_str)
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

row = rows[0]
updates = {
    "profile_mode": "lexical_first_half_sampled",
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_mean_seconds": parent_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_mean_seconds": insert_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_mean_seconds": clear_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_mean_seconds": overwrite_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_mean_seconds": str(
        float(insert_seconds) + float(clear_seconds) + float(overwrite_seconds)
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_mean_seconds": str(
        max(
            float(parent_seconds)
            - float(insert_seconds)
            - float(clear_seconds)
            - float(overwrite_seconds),
            0.0,
        )
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_sampled_event_count": sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_covered_sampled_event_count": covered_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unclassified_sampled_event_count": unclassified_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_multi_child_sampled_event_count": multi_child_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_sampled_event_count": insert_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_sampled_event_count": clear_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_sampled_event_count": overwrite_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_count": insert_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_count": clear_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_count": overwrite_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_bytes": insert_bytes,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_bytes": clear_bytes,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_bytes": overwrite_bytes,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_entry_count": unique_entry_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_slot_count": unique_slot_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_key_count": unique_key_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_entry_rewrite_count": same_entry_rewrite_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_cacheline_rewrite_count": same_cacheline_rewrite_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_back_to_back_same_entry_write_count": back_to_back_same_entry_write_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_then_overwrite_same_entry_count": clear_then_overwrite_same_entry_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_then_insert_same_entry_count": overwrite_then_insert_same_entry_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_then_clear_same_entry_count": insert_then_clear_same_entry_count,
}
row.update(updates)
fieldnames = list(rows[0].keys())
for field in updates:
    if field not in fieldnames:
        fieldnames.append(field)

with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
}

inject_full_probe_split() {
  local path="$1"
  local parent_seconds="$2"
  local scan_seconds="$3"
  local compare_seconds="$4"
  local branch_seconds="$5"
  local bookkeeping_seconds="$6"
  local sampled_event_count="$7"
  local covered_sampled_event_count="$8"
  local unclassified_sampled_event_count="$9"
  local multi_child_sampled_event_count="${10}"
  local full_probe_count="${11}"
  local slots_scanned_total="${12}"
  local slots_scanned_per_probe_mean="${13}"
  local slots_scanned_p50="${14}"
  local slots_scanned_p90="${15}"
  local slots_scanned_p99="${16}"
  local full_scan_count="${17}"
  local early_exit_count="${18}"
  local found_existing_count="${19}"
  local confirmed_absent_count="${20}"
  local redundant_reprobe_count="${21}"
  local same_key_reprobe_count="${22}"
  local same_event_reprobe_count="${23}"
  python3 - <<'PY' "$path" "$parent_seconds" "$scan_seconds" "$compare_seconds" \
    "$branch_seconds" "$bookkeeping_seconds" "$sampled_event_count" \
    "$covered_sampled_event_count" "$unclassified_sampled_event_count" \
    "$multi_child_sampled_event_count" "$full_probe_count" "$slots_scanned_total" \
    "$slots_scanned_per_probe_mean" "$slots_scanned_p50" "$slots_scanned_p90" \
    "$slots_scanned_p99" "$full_scan_count" "$early_exit_count" "$found_existing_count" \
    "$confirmed_absent_count" "$redundant_reprobe_count" "$same_key_reprobe_count" \
    "$same_event_reprobe_count"
import csv
import sys
from pathlib import Path

(
    path_str,
    parent_seconds,
    scan_seconds,
    compare_seconds,
    branch_seconds,
    bookkeeping_seconds,
    sampled_event_count,
    covered_sampled_event_count,
    unclassified_sampled_event_count,
    multi_child_sampled_event_count,
    full_probe_count,
    slots_scanned_total,
    slots_scanned_per_probe_mean,
    slots_scanned_p50,
    slots_scanned_p90,
    slots_scanned_p99,
    full_scan_count,
    early_exit_count,
    found_existing_count,
    confirmed_absent_count,
    redundant_reprobe_count,
    same_key_reprobe_count,
    same_event_reprobe_count,
) = sys.argv[1:]

path = Path(path_str)
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

row = rows[0]
updates = {
    "profile_mode": "lexical_first_half_sampled",
    "context_apply_lookup_miss_candidate_set_full_probe_parent_mean_seconds": parent_seconds,
    "context_apply_lookup_miss_candidate_set_full_probe_scan_mean_seconds": scan_seconds,
    "context_apply_lookup_miss_candidate_set_full_probe_compare_mean_seconds": compare_seconds,
    "context_apply_lookup_miss_candidate_set_full_probe_branch_or_guard_mean_seconds": branch_seconds,
    "context_apply_lookup_miss_candidate_set_full_probe_bookkeeping_mean_seconds": bookkeeping_seconds,
    "context_apply_lookup_miss_candidate_set_full_probe_child_known_mean_seconds": str(
        float(scan_seconds)
        + float(compare_seconds)
        + float(branch_seconds)
        + float(bookkeeping_seconds)
    ),
    "context_apply_lookup_miss_candidate_set_full_probe_unexplained_mean_seconds": str(
        max(
            float(parent_seconds)
            - float(scan_seconds)
            - float(compare_seconds)
            - float(branch_seconds)
            - float(bookkeeping_seconds),
            0.0,
        )
    ),
    "context_apply_lookup_miss_candidate_set_full_probe_sampled_event_count": sampled_event_count,
    "context_apply_lookup_miss_candidate_set_full_probe_covered_sampled_event_count": covered_sampled_event_count,
    "context_apply_lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count": unclassified_sampled_event_count,
    "context_apply_lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count": multi_child_sampled_event_count,
    "context_apply_lookup_miss_candidate_set_full_probe_count": full_probe_count,
    "context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_total": slots_scanned_total,
    "context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean": slots_scanned_per_probe_mean,
    "context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p50": slots_scanned_p50,
    "context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p90": slots_scanned_p90,
    "context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p99": slots_scanned_p99,
    "context_apply_lookup_miss_candidate_set_full_probe_full_scan_count": full_scan_count,
    "context_apply_lookup_miss_candidate_set_full_probe_early_exit_count": early_exit_count,
    "context_apply_lookup_miss_candidate_set_full_probe_found_existing_count": found_existing_count,
    "context_apply_lookup_miss_candidate_set_full_probe_confirmed_absent_count": confirmed_absent_count,
    "context_apply_lookup_miss_candidate_set_full_probe_redundant_reprobe_count": redundant_reprobe_count,
    "context_apply_lookup_miss_candidate_set_full_probe_same_key_reprobe_count": same_key_reprobe_count,
    "context_apply_lookup_miss_candidate_set_full_probe_same_event_reprobe_count": same_event_reprobe_count,
}
row.update(updates)
fieldnames = list(rows[0].keys())
for field in updates:
    if field not in fieldnames:
        fieldnames.append(field)

with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
}

inject_state_update_split() {
  local path="$1"
  local state_update_seconds="$2"
  local parent_seconds="$3"
  local heap_build_seconds="$4"
  local heap_update_seconds="$5"
  local start_index_rebuild_seconds="$6"
  local bookkeeping_seconds="$7"
  local sampled_event_count="$8"
  local covered_sampled_event_count="$9"
  local unclassified_sampled_event_count="${10}"
  local multi_child_sampled_event_count="${11}"
  local heap_build_sampled_event_count="${12}"
  local heap_update_sampled_event_count="${13}"
  local start_index_rebuild_sampled_event_count="${14}"
  local bookkeeping_sampled_event_count="${15}"
  local event_count="${16}"
  local heap_build_count="${17}"
  local heap_update_count="${18}"
  local start_index_rebuild_count="${19}"
  local bookkeeping_count="${20}"
  local aux_updates_total="${21}"
  local coverage_source="${22:-event_level_sampled}"
  python3 - <<'PY' "$path" "$state_update_seconds" "$parent_seconds" "$heap_build_seconds" \
    "$heap_update_seconds" "$start_index_rebuild_seconds" "$bookkeeping_seconds" \
    "$sampled_event_count" "$covered_sampled_event_count" "$unclassified_sampled_event_count" \
    "$multi_child_sampled_event_count" "$heap_build_sampled_event_count" \
    "$heap_update_sampled_event_count" "$start_index_rebuild_sampled_event_count" \
    "$bookkeeping_sampled_event_count" "$event_count" "$heap_build_count" \
    "$heap_update_count" "$start_index_rebuild_count" "$bookkeeping_count" "$aux_updates_total" \
    "$coverage_source"
import csv
import sys
from pathlib import Path

(
    path_str,
    state_update_seconds,
    parent_seconds,
    heap_build_seconds,
    heap_update_seconds,
    start_index_rebuild_seconds,
    bookkeeping_seconds,
    sampled_event_count,
    covered_sampled_event_count,
    unclassified_sampled_event_count,
    multi_child_sampled_event_count,
    heap_build_sampled_event_count,
    heap_update_sampled_event_count,
    start_index_rebuild_sampled_event_count,
    bookkeeping_sampled_event_count,
    event_count,
    heap_build_count,
    heap_update_count,
    start_index_rebuild_count,
    bookkeeping_count,
    aux_updates_total,
    coverage_source,
) = sys.argv[1:]

path = Path(path_str)
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

row = rows[0]
lookup_miss_open_slot_seconds = float(
    row.get("context_apply_lookup_miss_open_slot_mean_seconds") or 0.0
)
lookup_miss_candidate_set_full_probe_seconds = 0.05
lookup_miss_eviction_select_seconds = float(
    row.get("context_apply_lookup_miss_eviction_select_mean_seconds") or 0.0
)
lookup_miss_reuse_writeback_seconds = float(
    row.get("context_apply_lookup_miss_reuse_writeback_mean_seconds") or 0.0
)
lookup_miss_seconds = (
    lookup_miss_open_slot_seconds
    + lookup_miss_candidate_set_full_probe_seconds
    + lookup_miss_eviction_select_seconds
    + lookup_miss_reuse_writeback_seconds
)
updates = {
    "profile_mode": "lexical_first_half_sampled",
    "context_apply_lookup_miss_mean_seconds": str(lookup_miss_seconds),
    "context_apply_lookup_miss_p50_seconds": str(lookup_miss_seconds),
    "context_apply_lookup_miss_p95_seconds": str(lookup_miss_seconds),
    "context_apply_lookup_miss_candidate_set_full_probe_mean_seconds": str(
        lookup_miss_candidate_set_full_probe_seconds
    ),
    "context_apply_lookup_miss_candidate_set_full_probe_p50_seconds": str(
        lookup_miss_candidate_set_full_probe_seconds
    ),
    "context_apply_lookup_miss_candidate_set_full_probe_p95_seconds": str(
        lookup_miss_candidate_set_full_probe_seconds
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_mean_seconds": state_update_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_count": aux_updates_total,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_mean_seconds": parent_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_mean_seconds": heap_build_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_mean_seconds": heap_update_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_mean_seconds": start_index_rebuild_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_mean_seconds": bookkeeping_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_mean_seconds": str(
        float(heap_build_seconds)
        + float(heap_update_seconds)
        + float(start_index_rebuild_seconds)
        + float(bookkeeping_seconds)
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_mean_seconds": str(
        max(
            float(parent_seconds)
            - float(heap_build_seconds)
            - float(heap_update_seconds)
            - float(start_index_rebuild_seconds)
            - float(bookkeeping_seconds),
            0.0,
        )
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count": sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count": covered_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count": unclassified_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_multi_child_sampled_event_count": multi_child_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_sampled_event_count": heap_build_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count": heap_update_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_sampled_event_count": start_index_rebuild_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_sampled_event_count": bookkeeping_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_event_count": event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_count": heap_build_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_count": heap_update_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_count": start_index_rebuild_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_count": bookkeeping_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_aux_updates_total": aux_updates_total,
    "context_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source": coverage_source,
}
row.update(updates)
fieldnames = list(rows[0].keys())
for field in updates:
    if field not in fieldnames:
        fieldnames.append(field)

with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
}

inject_production_state_update_split() {
  local path="$1"
  local parent_seconds="$2"
  local benchmark_counter_seconds="$3"
  local trace_replay_required_state_seconds="$4"
  local sampled_event_count="$5"
  local covered_sampled_event_count="$6"
  local unclassified_sampled_event_count="$7"
  local multi_child_sampled_event_count="$8"
  local benchmark_counter_sampled_event_count="$9"
  local trace_replay_required_state_sampled_event_count="${10}"
  local event_count="${11}"
  local benchmark_counter_count="${12}"
  local trace_replay_required_state_count="${13}"
  local coverage_source="${14:-event_level_sampled}"
  python3 - <<'PY' "$path" "$parent_seconds" "$benchmark_counter_seconds" \
    "$trace_replay_required_state_seconds" "$sampled_event_count" \
    "$covered_sampled_event_count" "$unclassified_sampled_event_count" \
    "$multi_child_sampled_event_count" "$benchmark_counter_sampled_event_count" \
    "$trace_replay_required_state_sampled_event_count" "$event_count" \
    "$benchmark_counter_count" "$trace_replay_required_state_count" "$coverage_source"
import csv
import sys
from pathlib import Path

(
    path_str,
    parent_seconds,
    benchmark_counter_seconds,
    trace_replay_required_state_seconds,
    sampled_event_count,
    covered_sampled_event_count,
    unclassified_sampled_event_count,
    multi_child_sampled_event_count,
    benchmark_counter_sampled_event_count,
    trace_replay_required_state_sampled_event_count,
    event_count,
    benchmark_counter_count,
    trace_replay_required_state_count,
    coverage_source,
) = sys.argv[1:]

path = Path(path_str)
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

row = rows[0]
updates = {
    "profile_mode": "lexical_first_half_sampled",
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_mean_seconds": parent_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_mean_seconds": parent_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_mean_seconds": benchmark_counter_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_mean_seconds": trace_replay_required_state_seconds,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_mean_seconds": str(
        float(benchmark_counter_seconds) + float(trace_replay_required_state_seconds)
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_mean_seconds": str(
        max(
            float(parent_seconds)
            - float(benchmark_counter_seconds)
            - float(trace_replay_required_state_seconds),
            0.0,
        )
    ),
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_sampled_event_count": sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_covered_sampled_event_count": covered_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unclassified_sampled_event_count": unclassified_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_multi_child_sampled_event_count": multi_child_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_sampled_event_count": benchmark_counter_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_sampled_event_count": trace_replay_required_state_sampled_event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_event_count": event_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_count": benchmark_counter_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_count": trace_replay_required_state_count,
    "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_coverage_source": coverage_source,
}
row.update(updates)
fieldnames = list(rows[0].keys())
for field in updates:
    if field not in fieldnames:
        fieldnames.append(field)

with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
}

assert_decision() {
  local output_dir="$1"
  local expected_status="$2"
  local expected_action="$3"
  local expected_pairing="$4"
  python3 - "$output_dir" "$expected_status" "$expected_action" "$expected_pairing" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_status = sys.argv[2]
expected_action = sys.argv[3]
expected_pairing = sys.argv[4]
summary = json.loads((output_dir / "candidate_index_lifecycle_summary.json").read_text(encoding="utf-8"))
decision = json.loads((output_dir / "candidate_index_lifecycle_decision.json").read_text(encoding="utf-8"))
assert summary["decision_status"] == expected_status, summary
assert decision["decision_status"] == expected_status, decision
assert decision["recommended_next_action"] == expected_action, decision
assert summary["materiality_pairing_status"] == expected_pairing, summary
assert decision["materiality_pairing_status"] == expected_pairing, decision
assert (
    summary["authoritative_next_action_context_status"]
    == "ready_but_requires_branch_rollup_context"
), summary
assert (
    decision["authoritative_next_action_context_status"]
    == "ready_but_requires_branch_rollup_context"
), decision
assert summary["authoritative_next_action_source"] == "branch_rollup_decision", summary
assert decision["authoritative_next_action_source"] == "branch_rollup_decision", decision
assert Path(summary["cases_tsv"]).name == "candidate_index_lifecycle_cases.tsv", summary
assert Path(summary["summary_markdown"]).name == "candidate_index_lifecycle_summary.md", summary
if summary["profile_mode_overhead_status"] == "needs_coarse_vs_lexical_ab":
    assert summary["decision_context_status"] == "ready_but_requires_ab_context", summary
    assert decision["decision_context_status"] == "ready_but_requires_ab_context", decision
    assert (
        summary["profile_mode_overhead_status_context"] == "delegated_to_profile_mode_ab"
    ), summary
    assert (
        decision["profile_mode_overhead_status_context"] == "delegated_to_profile_mode_ab"
    ), decision
    assert summary["authoritative_profile_mode_overhead_source_kind"] == "profile_mode_ab_summary", summary
    assert decision["authoritative_profile_mode_overhead_source_kind"] == "profile_mode_ab_summary", decision
if expected_action == "profile_terminal_residual_by_lexical_spans":
    assert summary["candidate_index_timer_scope_status"] == "closed", summary
    assert summary["reuse_aux_other_timer_scope_status"] == "closed", summary
    assert summary["terminal_residual_status"] == "dominant", summary
    assert decision["terminal_residual_status"] == "dominant", decision
    assert summary["intra_profile_closure_status"] in {"ok", "unknown"}, summary
    assert summary["profile_mode_overhead_status"] in {
        "unknown",
        "needs_coarse_vs_lexical_ab",
        "ok",
        "suspect",
    }, summary
if expected_action == "split_terminal_first_half_lexical_span":
    assert summary["candidate_index_timer_scope_status"] == "closed", summary
    assert summary["reuse_aux_other_timer_scope_status"] == "closed", summary
    assert summary["terminal_timer_closure_status"] == "closed", summary
    assert summary["lexical_span_closure_status"] == "closed", summary
    assert summary["intra_profile_closure_status"] == "ok", summary
    assert summary["profile_mode_overhead_status"] == "needs_coarse_vs_lexical_ab", summary
    assert summary["candidate_index_materiality_status"] == "material", summary
    assert decision["candidate_index"]["dominant_terminal_span"] == "first_half", decision
if expected_action == "run_profile_mode_ab":
    assert summary["candidate_index_timer_scope_status"] == "closed", summary
    assert summary["reuse_aux_other_timer_scope_status"] == "closed", summary
    assert summary["terminal_timer_closure_status"] == "closed", summary
    assert summary["lexical_span_closure_status"] == "closed", summary
    assert summary["intra_profile_closure_status"] == "ok", summary
    assert summary["profile_mode_overhead_status"] == "needs_coarse_vs_lexical_ab", summary
    assert summary["candidate_index_materiality_status"] == "material", summary
    assert decision["candidate_index"]["dominant_terminal_span"] == "first_half", decision
PY
}

assert_closure_fields() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
summary = json.loads((output_dir / "candidate_index_lifecycle_summary.json").read_text(encoding="utf-8"))
candidate = summary["candidate_index"]

required_candidate_fields = [
    "parent_seconds",
    "child_known_seconds",
    "unexplained_seconds",
    "unexplained_share_of_candidate_index",
]
required_reuse_fields = [
    "lookup_miss_reuse_writeback_parent_seconds",
    "lookup_miss_reuse_writeback_child_known_seconds",
    "lookup_miss_reuse_writeback_unexplained_seconds",
    "lookup_miss_reuse_writeback_unexplained_share_of_candidate_index",
]
required_aux_other_fields = [
    "lookup_miss_reuse_writeback_aux_other_parent_seconds",
    "lookup_miss_reuse_writeback_aux_other_child_known_seconds",
    "lookup_miss_reuse_writeback_aux_other_unexplained_seconds",
    "lookup_miss_reuse_writeback_aux_other_unexplained_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_residual_parent_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_residual_share_of_candidate_index",
]
required_terminal_path_fields = [
    "profile_mode",
    "terminal_path_scope",
    "terminal_path_parent_seconds",
    "terminal_path_child_known_seconds",
    "terminal_path_candidate_slot_write_seconds",
    "terminal_path_start_index_write_seconds",
    "terminal_path_state_update_seconds",
    "terminal_path_state_update_parent_seconds",
    "terminal_path_state_update_heap_build_seconds",
    "terminal_path_state_update_heap_update_seconds",
    "terminal_path_state_update_start_index_rebuild_seconds",
    "terminal_path_state_update_trace_or_profile_bookkeeping_seconds",
    "terminal_path_state_update_child_known_seconds",
    "terminal_path_state_update_unexplained_seconds",
    "terminal_path_state_update_unexplained_share",
    "terminal_path_state_update_sampled_event_count",
    "terminal_path_state_update_covered_sampled_event_count",
    "terminal_path_state_update_unclassified_sampled_event_count",
    "terminal_path_state_update_multi_child_sampled_event_count",
    "terminal_path_state_update_heap_build_sampled_event_count",
    "terminal_path_state_update_heap_update_sampled_event_count",
    "terminal_path_state_update_start_index_rebuild_sampled_event_count",
    "terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count",
    "terminal_path_state_update_sampled_count_closure_status",
    "terminal_path_state_update_coverage_source",
    "terminal_path_state_update_timer_scope_status",
    "terminal_path_state_update_dominant_child",
    "terminal_path_state_update_coverage_share",
    "terminal_path_state_update_unclassified_share",
    "terminal_path_state_update_multi_child_share",
    "terminal_path_state_update_heap_build_share",
    "terminal_path_state_update_heap_update_share",
    "terminal_path_state_update_start_index_rebuild_share",
    "terminal_path_state_update_trace_or_profile_bookkeeping_share",
    "terminal_path_telemetry_overhead_seconds",
    "terminal_path_residual_seconds",
    "terminal_path_candidate_slot_write_share_of_candidate_index",
    "terminal_path_start_index_write_share_of_candidate_index",
    "terminal_path_state_update_share_of_candidate_index",
    "terminal_path_telemetry_overhead_share_of_candidate_index",
    "terminal_path_residual_share_of_candidate_index",
    "terminal_path_event_count",
    "terminal_path_candidate_slot_write_count",
    "terminal_path_start_index_write_count",
    "terminal_path_state_update_count",
    "terminal_path_state_update_event_count",
    "terminal_path_state_update_heap_build_count",
    "terminal_path_state_update_heap_update_count",
    "terminal_path_state_update_start_index_rebuild_count",
    "terminal_path_state_update_trace_or_profile_bookkeeping_count",
    "terminal_path_state_update_aux_updates_total",
    "production_state_update_parent_seconds",
    "production_state_update_benchmark_counter_seconds",
    "production_state_update_trace_replay_required_state_seconds",
    "production_state_update_child_known_seconds",
    "production_state_update_unexplained_seconds",
    "production_state_update_unexplained_share",
    "production_state_update_sampled_event_count",
    "production_state_update_covered_sampled_event_count",
    "production_state_update_unclassified_sampled_event_count",
    "production_state_update_multi_child_sampled_event_count",
    "production_state_update_benchmark_counter_sampled_event_count",
    "production_state_update_trace_replay_required_state_sampled_event_count",
    "production_state_update_sampled_count_closure_status",
    "production_state_update_coverage_source",
    "production_state_update_timer_scope_status",
    "production_state_update_dominant_child",
    "production_state_update_coverage_share",
    "production_state_update_unclassified_share",
    "production_state_update_multi_child_share",
    "production_state_update_benchmark_counter_share",
    "production_state_update_trace_replay_required_state_share",
    "production_state_update_share_of_candidate_index",
    "production_state_update_event_count",
    "production_state_update_benchmark_counter_count",
    "production_state_update_trace_replay_required_state_count",
    "terminal_path_candidate_bytes_written",
    "terminal_path_start_index_bytes_written",
    "terminal_path_dominant_child",
    "terminal_path_start_index_write_parent_seconds",
    "terminal_path_start_index_write_left_seconds",
    "terminal_path_start_index_write_right_seconds",
    "terminal_path_start_index_write_child_known_seconds",
    "terminal_path_start_index_write_unexplained_seconds",
    "terminal_path_start_index_write_unexplained_share",
    "terminal_path_start_index_write_sampled_count_closure_status",
    "terminal_path_start_index_write_dominant_child",
    "terminal_path_start_index_write_coverage_share",
    "terminal_path_start_index_write_unclassified_share",
    "terminal_path_start_index_write_multi_child_share",
    "terminal_path_start_index_write_probe_or_locate_share",
    "terminal_path_start_index_write_entry_store_share",
    "terminal_path_start_index_write_insert_count",
    "terminal_path_start_index_write_update_existing_count",
    "terminal_path_start_index_write_clear_count",
    "terminal_path_start_index_write_overwrite_count",
    "terminal_path_start_index_write_idempotent_count",
    "terminal_path_start_index_write_value_changed_count",
    "terminal_path_start_index_write_probe_count",
    "terminal_path_start_index_write_probe_steps_total",
    "terminal_path_start_index_store_parent_seconds",
    "terminal_path_start_index_store_insert_seconds",
    "terminal_path_start_index_store_clear_seconds",
    "terminal_path_start_index_store_overwrite_seconds",
    "terminal_path_start_index_store_child_known_seconds",
    "terminal_path_start_index_store_unexplained_seconds",
    "terminal_path_start_index_store_unexplained_share",
    "terminal_path_start_index_store_sampled_event_count",
    "terminal_path_start_index_store_covered_sampled_event_count",
    "terminal_path_start_index_store_unclassified_sampled_event_count",
    "terminal_path_start_index_store_multi_child_sampled_event_count",
    "terminal_path_start_index_store_insert_sampled_event_count",
    "terminal_path_start_index_store_clear_sampled_event_count",
    "terminal_path_start_index_store_overwrite_sampled_event_count",
    "terminal_path_start_index_store_sampled_count_closure_status",
    "terminal_path_start_index_store_dominant_child",
    "terminal_path_start_index_store_coverage_share",
    "terminal_path_start_index_store_unclassified_share",
    "terminal_path_start_index_store_multi_child_share",
    "terminal_path_start_index_store_insert_share",
    "terminal_path_start_index_store_clear_share",
    "terminal_path_start_index_store_overwrite_share",
    "terminal_path_start_index_store_insert_count",
    "terminal_path_start_index_store_clear_count",
    "terminal_path_start_index_store_overwrite_count",
    "terminal_path_start_index_store_insert_bytes",
    "terminal_path_start_index_store_clear_bytes",
    "terminal_path_start_index_store_overwrite_bytes",
    "terminal_path_start_index_store_unique_entry_count",
    "terminal_path_start_index_store_unique_slot_count",
    "terminal_path_start_index_store_unique_key_count",
    "terminal_path_start_index_store_same_entry_rewrite_count",
    "terminal_path_start_index_store_same_cacheline_rewrite_count",
    "terminal_path_start_index_store_back_to_back_same_entry_write_count",
    "terminal_path_start_index_store_clear_then_overwrite_same_entry_count",
    "terminal_path_start_index_store_overwrite_then_insert_same_entry_count",
    "terminal_path_start_index_store_insert_then_clear_same_entry_count",
    "terminal_path_start_index_store_clear_then_overwrite_same_entry_share",
    "terminal_first_half_parent_seconds",
    "terminal_first_half_span_a_seconds",
    "terminal_first_half_span_b_seconds",
    "terminal_first_half_child_known_seconds",
    "terminal_first_half_unexplained_seconds",
    "dominant_terminal_span",
    "dominant_terminal_first_half_span",
    "timer_call_count",
    "terminal_timer_call_count",
    "lexical_timer_call_count",
    "intra_profile_closure_status",
    "profile_mode_overhead_status",
    "candidate_index_materiality_status",
    "terminal_timer_closure_status",
    "lexical_span_closure_status",
]

for field in (
    required_candidate_fields
    + required_reuse_fields
    + required_aux_other_fields
    + required_terminal_path_fields
):
    assert field in candidate, field

assert candidate["parent_seconds"] >= 0.0, candidate
assert candidate["child_known_seconds"] >= 0.0, candidate
assert candidate["unexplained_seconds"] >= 0.0, candidate
assert candidate["lookup_miss_reuse_writeback_parent_seconds"] >= 0.0, candidate
assert candidate["lookup_miss_reuse_writeback_aux_other_parent_seconds"] >= 0.0, candidate
assert candidate["terminal_path_scope"] == "reuse_writeback_post_victim_reset_tail", candidate
assert candidate["terminal_path_parent_seconds"] >= 0.0, candidate
assert candidate["terminal_path_child_known_seconds"] >= 0.0, candidate
assert candidate["terminal_path_residual_seconds"] >= 0.0, candidate
assert candidate["terminal_path_event_count"] >= 0, candidate
assert candidate["terminal_path_start_index_write_parent_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_write_left_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_write_right_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_write_child_known_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_write_unexplained_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_store_parent_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_store_insert_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_store_clear_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_store_overwrite_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_store_child_known_seconds"] >= 0.0, candidate
assert candidate["terminal_path_start_index_store_unexplained_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_parent_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_heap_build_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_heap_update_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_start_index_rebuild_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_trace_or_profile_bookkeeping_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_child_known_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_unexplained_seconds"] >= 0.0, candidate
assert candidate["terminal_path_state_update_event_count"] >= 0, candidate
assert candidate["production_state_update_parent_seconds"] >= 0.0, candidate
assert candidate["production_state_update_benchmark_counter_seconds"] >= 0.0, candidate
assert candidate["production_state_update_trace_replay_required_state_seconds"] >= 0.0, candidate
assert candidate["production_state_update_child_known_seconds"] >= 0.0, candidate
assert candidate["production_state_update_unexplained_seconds"] >= 0.0, candidate
assert candidate["production_state_update_event_count"] >= 0, candidate
assert candidate["profile_mode"] in {
    "coarse",
    "terminal",
    "lexical_first_half",
    "lexical_first_half_sampled",
    "lexical_first_half_sampled_no_terminal_telemetry",
    "unknown",
}, candidate
assert candidate["terminal_first_half_parent_seconds"] is None or candidate["terminal_first_half_parent_seconds"] >= 0.0, candidate
assert candidate["terminal_first_half_span_a_seconds"] is None or candidate["terminal_first_half_span_a_seconds"] >= 0.0, candidate
assert candidate["terminal_first_half_span_b_seconds"] is None or candidate["terminal_first_half_span_b_seconds"] >= 0.0, candidate
assert candidate["timer_call_count"] is None or candidate["timer_call_count"] >= 0, candidate
assert candidate["terminal_timer_call_count"] is None or candidate["terminal_timer_call_count"] >= 0, candidate
assert candidate["lexical_timer_call_count"] is None or candidate["lexical_timer_call_count"] >= 0, candidate
assert candidate["terminal_path_dominant_child"] in {
    "candidate_slot_write",
    "start_index_write",
    "state_update",
    "telemetry_overhead",
    "residual",
}, candidate
assert candidate["terminal_path_start_index_write_dominant_child"] in {"left", "right", "unknown"}, candidate
assert candidate["terminal_path_start_index_write_sampled_count_closure_status"] in {
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
assert candidate["terminal_path_start_index_store_sampled_count_closure_status"] in {
    "closed",
    "open",
    "unknown",
}, candidate
assert candidate["terminal_path_state_update_dominant_child"] in {
    "heap_build",
    "heap_update",
    "start_index_rebuild",
    "trace_or_profile_bookkeeping",
    "unknown",
}, candidate
assert candidate["terminal_path_state_update_sampled_count_closure_status"] in {
    "closed",
    "open",
    "unknown",
}, candidate
assert candidate["terminal_path_state_update_coverage_source"] in {
    "placeholder",
    "event_level_sampled",
}, candidate
assert candidate["terminal_path_state_update_timer_scope_status"] in {
    "missing_event_level_coverage",
    "closed",
    "open",
    "unknown",
}, candidate
assert candidate["production_state_update_dominant_child"] in {
    "benchmark_counter",
    "trace_replay_required_state",
    "unknown",
}, candidate
assert candidate["production_state_update_sampled_count_closure_status"] in {
    "closed",
    "open",
    "unknown",
}, candidate
assert candidate["production_state_update_coverage_source"] in {
    "placeholder",
    "event_level_sampled",
}, candidate
assert candidate["production_state_update_timer_scope_status"] in {
    "missing_event_level_coverage",
    "closed",
    "open",
    "unknown",
}, candidate
assert candidate["dominant_terminal_span"] in {"unknown", "first_half", "second_half"}, candidate
assert summary["intra_profile_closure_status"] in {"unknown", "ok"}, summary
assert summary["profile_mode_overhead_status"] in {
    "unknown",
    "needs_coarse_vs_lexical_ab",
    "ok",
    "suspect",
}, summary
assert summary["candidate_index_materiality_status"] in {"material", "immaterial", "unknown"}, summary
assert summary["terminal_timer_closure_status"] in {"closed", "residual_unexplained"}, summary
assert summary["lexical_span_closure_status"] in {"closed", "unknown", "residual_unexplained"}, summary
PY
}

PROBE="$WORK/probe.tsv"
write_profile_tsv "$PROBE" "case-probe" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.26" "0.05" "0.16" "0.01" "0.02" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.01" "0.01" "0.01" "0.01" "wl-probe" "/tmp/wl-probe.stderr.log"
run_and_assert "$WORK/out-probe" --aggregate-tsv "$PROBE"
assert_decision "$WORK/out-probe" "ready" "profile_lookup_miss_candidate_set_full_probe" "complete"

FULL_PROBE_SCAN="$WORK/full-probe-scan.tsv"
cp "$PROBE" "$FULL_PROBE_SCAN"
inject_full_probe_split "$FULL_PROBE_SCAN" "0.26" "0.16" "0.04" "0.03" "0.03" "200" "200" "0" "160" "350" "11200" "32.0" "16" "64" "128" "220" "130" "0" "350" "20" "12" "4"
run_and_assert "$WORK/out-full-probe-scan" --aggregate-tsv "$FULL_PROBE_SCAN"
assert_decision "$WORK/out-full-probe-scan" "ready" "profile_candidate_set_full_scan_path" "complete"
python3 - <<'PY' "$WORK/out-full-probe-scan/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["lookup_miss_candidate_set_full_probe_sampled_count_closure_status"] == "closed", candidate
assert candidate["lookup_miss_candidate_set_full_probe_scan_share"] > candidate["lookup_miss_candidate_set_full_probe_compare_share"], candidate
assert candidate["lookup_miss_candidate_set_full_probe_full_scan_share"] > 0.5, candidate
PY

FULL_PROBE_COMPARE="$WORK/full-probe-compare.tsv"
cp "$PROBE" "$FULL_PROBE_COMPARE"
inject_full_probe_split "$FULL_PROBE_COMPARE" "0.26" "0.06" "0.13" "0.04" "0.03" "180" "180" "0" "140" "350" "2800" "8.0" "4" "8" "16" "30" "320" "0" "350" "24" "10" "3"
run_and_assert "$WORK/out-full-probe-compare" --aggregate-tsv "$FULL_PROBE_COMPARE"
assert_decision "$WORK/out-full-probe-compare" "ready" "profile_candidate_set_probe_compare_path" "complete"

FULL_PROBE_BRANCH="$WORK/full-probe-branch.tsv"
cp "$PROBE" "$FULL_PROBE_BRANCH"
inject_full_probe_split "$FULL_PROBE_BRANCH" "0.26" "0.05" "0.05" "0.12" "0.04" "160" "160" "0" "120" "350" "2450" "7.0" "4" "8" "12" "24" "326" "0" "350" "18" "8" "2"
run_and_assert "$WORK/out-full-probe-branch" --aggregate-tsv "$FULL_PROBE_BRANCH"
assert_decision "$WORK/out-full-probe-branch" "ready" "profile_lookup_miss_probe_branch_path" "complete"

FULL_PROBE_REDUNDANT="$WORK/full-probe-redundant.tsv"
cp "$PROBE" "$FULL_PROBE_REDUNDANT"
inject_full_probe_split "$FULL_PROBE_REDUNDANT" "0.26" "0.08" "0.07" "0.05" "0.06" "150" "150" "0" "120" "350" "1750" "5.0" "4" "8" "8" "20" "330" "0" "350" "140" "120" "95"
run_and_assert "$WORK/out-full-probe-redundant" --aggregate-tsv "$FULL_PROBE_REDUNDANT"
assert_decision "$WORK/out-full-probe-redundant" "ready" "prototype_redundant_full_probe_skip_shadow" "complete"

FULL_PROBE_TIMER_SCOPE="$WORK/full-probe-timer-scope.tsv"
cp "$PROBE" "$FULL_PROBE_TIMER_SCOPE"
inject_full_probe_split "$FULL_PROBE_TIMER_SCOPE" "0.26" "0.10" "0.05" "0.04" "0.03" "150" "120" "30" "90" "350" "2100" "6.0" "4" "8" "12" "40" "310" "0" "350" "18" "9" "3"
run_and_assert "$WORK/out-full-probe-timer-scope" --aggregate-tsv "$FULL_PROBE_TIMER_SCOPE"
assert_decision "$WORK/out-full-probe-timer-scope" "ready" "inspect_lookup_miss_candidate_set_full_probe_timer_scope" "complete"

FULL_PROBE_DISTRIBUTED="$WORK/full-probe-distributed.tsv"
cp "$PROBE" "$FULL_PROBE_DISTRIBUTED"
inject_full_probe_split "$FULL_PROBE_DISTRIBUTED" "0.26" "0.07" "0.06" "0.06" "0.07" "140" "140" "0" "110" "350" "2100" "6.0" "4" "8" "12" "30" "320" "0" "350" "20" "8" "2"
run_and_assert "$WORK/out-full-probe-distributed" --aggregate-tsv "$FULL_PROBE_DISTRIBUTED"
assert_decision "$WORK/out-full-probe-distributed" "ready" "no_single_stable_leaf_found_under_current_profiler" "complete"

STATE_UPDATE_BOOKKEEPING="$WORK/state-update-bookkeeping.tsv"
cp "$PROBE" "$STATE_UPDATE_BOOKKEEPING"
inject_state_update_split "$STATE_UPDATE_BOOKKEEPING" "0.11" "0.25" "0.03" "0.04" "0.03" "0.15" "120" "120" "0" "60" "15" "25" "12" "80" "120" "15" "25" "12" "80" "52"
run_and_assert "$WORK/out-state-update-bookkeeping" --aggregate-tsv "$STATE_UPDATE_BOOKKEEPING"
assert_decision "$WORK/out-state-update-bookkeeping" "ready" "classify_terminal_path_state_update_bookkeeping" "complete"

STATE_UPDATE_PRODUCTION_TRACE="$WORK/state-update-production-trace.tsv"
cp "$STATE_UPDATE_BOOKKEEPING" "$STATE_UPDATE_PRODUCTION_TRACE"
inject_production_state_update_split "$STATE_UPDATE_PRODUCTION_TRACE" "0.15" "0.03" "0.10" "90" "90" "0" "20" "28" "74" "90" "28" "74"
run_and_assert "$WORK/out-state-update-production-trace" --aggregate-tsv "$STATE_UPDATE_PRODUCTION_TRACE"
assert_decision "$WORK/out-state-update-production-trace" "ready" "profile_trace_replay_required_state_update_path" "complete"

STATE_UPDATE_PRODUCTION_BENCHMARK="$WORK/state-update-production-benchmark.tsv"
cp "$STATE_UPDATE_BOOKKEEPING" "$STATE_UPDATE_PRODUCTION_BENCHMARK"
inject_production_state_update_split "$STATE_UPDATE_PRODUCTION_BENCHMARK" "0.15" "0.10" "0.03" "90" "90" "0" "20" "74" "28" "90" "74" "28"
run_and_assert "$WORK/out-state-update-production-benchmark" --aggregate-tsv "$STATE_UPDATE_PRODUCTION_BENCHMARK"
assert_decision "$WORK/out-state-update-production-benchmark" "ready" "reduce_or_cold_path_benchmark_state_update_counters" "complete"

STATE_UPDATE_PRODUCTION_NEAR_TIE="$WORK/state-update-production-near-tie.tsv"
cp "$STATE_UPDATE_BOOKKEEPING" "$STATE_UPDATE_PRODUCTION_NEAR_TIE"
inject_production_state_update_split "$STATE_UPDATE_PRODUCTION_NEAR_TIE" "0.15" "0.0749" "0.0751" "90" "90" "0" "90" "45" "45" "90" "45" "45"
run_and_assert "$WORK/out-state-update-production-near-tie" --aggregate-tsv "$STATE_UPDATE_PRODUCTION_NEAR_TIE"
assert_decision "$WORK/out-state-update-production-near-tie" "ready" "mark_production_state_update_as_distributed_overhead" "complete"

STATE_UPDATE_PRODUCTION_TIMER_SCOPE="$WORK/state-update-production-timer-scope.tsv"
cp "$STATE_UPDATE_BOOKKEEPING" "$STATE_UPDATE_PRODUCTION_TIMER_SCOPE"
inject_production_state_update_split "$STATE_UPDATE_PRODUCTION_TIMER_SCOPE" "0.15" "0.03" "0.03" "90" "70" "20" "15" "40" "40" "90" "40" "40"
run_and_assert "$WORK/out-state-update-production-timer-scope" --aggregate-tsv "$STATE_UPDATE_PRODUCTION_TIMER_SCOPE"
assert_decision "$WORK/out-state-update-production-timer-scope" "ready" "inspect_production_state_update_timer_scope" "complete"

STATE_UPDATE_PRODUCTION_DISTRIBUTED="$WORK/state-update-production-distributed.tsv"
cp "$STATE_UPDATE_BOOKKEEPING" "$STATE_UPDATE_PRODUCTION_DISTRIBUTED"
inject_production_state_update_split "$STATE_UPDATE_PRODUCTION_DISTRIBUTED" "0.15" "0.055" "0.050" "90" "90" "0" "35" "58" "54" "90" "58" "54"
run_and_assert "$WORK/out-state-update-production-distributed" --aggregate-tsv "$STATE_UPDATE_PRODUCTION_DISTRIBUTED"
assert_decision "$WORK/out-state-update-production-distributed" "ready" "mark_production_state_update_as_distributed_overhead" "complete"

STATE_UPDATE_PLACEHOLDER="$WORK/state-update-placeholder.tsv"
cp "$PROBE" "$STATE_UPDATE_PLACEHOLDER"
inject_state_update_split "$STATE_UPDATE_PLACEHOLDER" "0.18" "0.20" "0.02" "0.12" "0.04" "0.02" "0" "0" "0" "0" "0" "0" "0" "0" "110" "10" "70" "18" "18" "98" "placeholder"
run_and_assert "$WORK/out-state-update-placeholder" --aggregate-tsv "$STATE_UPDATE_PLACEHOLDER"
assert_decision "$WORK/out-state-update-placeholder" "ready" "instrument_terminal_path_state_update_event_level_closure" "complete"

STATE_UPDATE_HEAP_UPDATE="$WORK/state-update-heap-update.tsv"
cp "$PROBE" "$STATE_UPDATE_HEAP_UPDATE"
inject_state_update_split "$STATE_UPDATE_HEAP_UPDATE" "0.18" "0.20" "0.02" "0.12" "0.04" "0.02" "110" "110" "0" "24" "10" "70" "18" "18" "110" "10" "70" "18" "18" "98"
run_and_assert "$WORK/out-state-update-heap-update" --aggregate-tsv "$STATE_UPDATE_HEAP_UPDATE"
assert_decision "$WORK/out-state-update-heap-update" "ready" "profile_heap_update_path" "complete"

STATE_UPDATE_HEAP_BUILD="$WORK/state-update-heap-build.tsv"
cp "$PROBE" "$STATE_UPDATE_HEAP_BUILD"
inject_state_update_split "$STATE_UPDATE_HEAP_BUILD" "0.18" "0.20" "0.11" "0.03" "0.04" "0.02" "100" "100" "0" "20" "65" "15" "12" "18" "100" "65" "15" "12" "18" "92"
run_and_assert "$WORK/out-state-update-heap-build" --aggregate-tsv "$STATE_UPDATE_HEAP_BUILD"
assert_decision "$WORK/out-state-update-heap-build" "ready" "profile_heap_build_path" "complete"

STATE_UPDATE_REBUILD="$WORK/state-update-rebuild.tsv"
cp "$PROBE" "$STATE_UPDATE_REBUILD"
inject_state_update_split "$STATE_UPDATE_REBUILD" "0.18" "0.20" "0.03" "0.04" "0.11" "0.02" "100" "100" "0" "22" "12" "16" "62" "18" "100" "12" "16" "62" "18" "90"
run_and_assert "$WORK/out-state-update-rebuild" --aggregate-tsv "$STATE_UPDATE_REBUILD"
assert_decision "$WORK/out-state-update-rebuild" "ready" "profile_start_index_rebuild_path" "complete"

STATE_UPDATE_TIMER_SCOPE="$WORK/state-update-timer-scope.tsv"
cp "$PROBE" "$STATE_UPDATE_TIMER_SCOPE"
inject_state_update_split "$STATE_UPDATE_TIMER_SCOPE" "0.18" "0.20" "0.05" "0.05" "0.05" "0.05" "120" "100" "20" "40" "24" "28" "24" "40" "120" "24" "28" "24" "40" "76"
run_and_assert "$WORK/out-state-update-timer-scope" --aggregate-tsv "$STATE_UPDATE_TIMER_SCOPE"
assert_decision "$WORK/out-state-update-timer-scope" "ready" "inspect_terminal_path_state_update_timer_scope" "complete"

STATE_UPDATE_DISTRIBUTED="$WORK/state-update-distributed.tsv"
cp "$PROBE" "$STATE_UPDATE_DISTRIBUTED"
inject_state_update_split "$STATE_UPDATE_DISTRIBUTED" "0.15" "0.20" "0.05" "0.05" "0.05" "0.05" "100" "100" "0" "35" "22" "24" "22" "32" "100" "22" "24" "22" "32" "68"
run_and_assert "$WORK/out-state-update-distributed" --aggregate-tsv "$STATE_UPDATE_DISTRIBUTED"
assert_decision "$WORK/out-state-update-distributed" "ready" "mark_terminal_path_state_update_as_distributed_overhead" "complete"

ERASE="$WORK/erase.tsv"
write_profile_tsv "$ERASE" "case-erase" "1.00" "0.50" "0.28" "0.03" "0.50" "0.45" "0.01" "0.05" "0.05" "0.35" "0.01" "0.02" "1000" "650" "350" "300" "350" "350" "2.50" "0.50" "5.00" "0.01" "0.01" "0.01" "0.01" "wl-erase" "/tmp/wl-erase.stderr.log"
run_and_assert "$WORK/out-erase" --aggregate-tsv "$ERASE"
assert_decision "$WORK/out-erase" "ready" "inspect_candidate_index_timer_scope" "complete"

REUSE="$WORK/reuse.tsv"
write_profile_tsv "$REUSE" "case-reuse" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.05" "0.05" "0.34" "0.03" "0.12" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.03" "0.03" "0.03" "0.03" "wl-reuse" "/tmp/wl-reuse.stderr.log"
run_and_assert "$WORK/out-reuse" --aggregate-tsv "$REUSE"
assert_decision "$WORK/out-reuse" "ready" "inspect_candidate_index_timer_scope" "complete"

RESIDUAL="$WORK/residual.tsv"
write_profile_tsv "$RESIDUAL" "case-residual" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.05" "0.05" "0.37" "0.01" "0.22" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.01" "0.01" "0.01" "0.19" "wl-residual" "/tmp/wl-residual.stderr.log"
run_and_assert "$WORK/out-residual" --aggregate-tsv "$RESIDUAL"
assert_decision "$WORK/out-residual" "ready" "inspect_candidate_index_timer_scope" "complete"
assert_closure_fields "$WORK/out-residual"

TERMINAL="$WORK/terminal.tsv"
write_profile_tsv "$TERMINAL" "case-terminal" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.05" "0.05" "0.37" "0.01" "0.22" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.01" "0.01" "0.01" "0.19" "wl-terminal" "/tmp/wl-terminal.stderr.log"
python3 - <<'PY' "$TERMINAL"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

row = rows[0]
updates = {
    "context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds": "0.25",
    "context_apply_lookup_miss_reuse_writeback_aux_heap_update_mean_seconds": "0.02",
    "context_apply_lookup_miss_reuse_writeback_aux_other_mean_seconds": "0.22",
    "context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds": "0.01",
    "context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds": "0.01",
    "context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds": "0.01",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds": "0.19",
}
row.update(updates)

with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
run_and_assert "$WORK/out-terminal" --aggregate-tsv "$TERMINAL"
assert_decision "$WORK/out-terminal" "ready" "profile_terminal_residual_by_lexical_spans" "complete"
assert_closure_fields "$WORK/out-terminal"
python3 - <<'PY' "$WORK/out-terminal/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["terminal_path_dominant_child"] == "residual", candidate
assert candidate["terminal_path_residual_seconds"] > candidate["terminal_path_candidate_slot_write_seconds"], candidate
assert candidate["terminal_path_residual_seconds"] > candidate["terminal_path_start_index_write_seconds"], candidate
assert candidate["dominant_terminal_span"] == "unknown", candidate
assert summary["intra_profile_closure_status"] == "unknown", summary
assert summary["profile_mode_overhead_status"] == "unknown", summary
PY

FIRST_HALF="$WORK/first-half.tsv"
cp "$TERMINAL" "$FIRST_HALF"
python3 - <<'PY' "$FIRST_HALF"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
row = rows[0]
extra_fields = [
    "profile_mode",
    "context_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_span_first_half_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_span_second_half_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_mean_seconds",
    "context_apply_timer_call_count",
    "context_apply_terminal_timer_call_count",
    "context_apply_lexical_timer_call_count",
]
for field in extra_fields:
    row.setdefault(field, "")
row["profile_mode"] = "lexical_first_half"
row["context_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_mean_seconds"] = "0.30"
row["context_apply_lookup_miss_reuse_writeback_terminal_span_first_half_mean_seconds"] = "0.18"
row["context_apply_lookup_miss_reuse_writeback_terminal_span_second_half_mean_seconds"] = "0.11"
row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_mean_seconds"] = "0.18"
row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_mean_seconds"] = "0.11"
row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_mean_seconds"] = "0.05"
row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_mean_seconds"] = "0.16"
row["context_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_mean_seconds"] = "0.02"
row["context_apply_timer_call_count"] = "560"
row["context_apply_terminal_timer_call_count"] = "420"
row["context_apply_lexical_timer_call_count"] = "140"
fieldnames = list(rows[0].keys())
for field in extra_fields:
    if field not in fieldnames:
        fieldnames.append(field)
with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
run_and_assert "$WORK/out-first-half" --aggregate-tsv "$FIRST_HALF"
assert_decision "$WORK/out-first-half" "ready" "run_profile_mode_ab" "complete"
python3 - <<'PY' "$WORK/out-first-half/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["dominant_terminal_span"] == "first_half", candidate
assert candidate["profile_mode"] == "lexical_first_half", candidate
assert candidate["terminal_first_half_parent_seconds"] == 0.18, candidate
assert candidate["terminal_first_half_span_a_seconds"] == 0.11, candidate
assert candidate["terminal_first_half_span_b_seconds"] == 0.05, candidate
assert candidate["dominant_terminal_first_half_span"] == "span_a", candidate
assert candidate["timer_call_count"] == 560, candidate
assert candidate["terminal_timer_call_count"] == 420, candidate
assert candidate["lexical_timer_call_count"] == 140, candidate
assert summary["intra_profile_closure_status"] == "ok", summary
assert summary["profile_mode_overhead_status"] == "needs_coarse_vs_lexical_ab", summary
PY

START_INDEX_PROBE="$WORK/start-index-probe.tsv"
cp "$TERMINAL" "$START_INDEX_PROBE"
inject_start_index_write_split "$START_INDEX_PROBE" "0.18" "0.12" "0.04" "300" "300" "0" "0" "300" "300" "300" "0" "0" "0" "0" "300" "300" "1800"
run_and_assert "$WORK/out-start-index-probe" --aggregate-tsv "$START_INDEX_PROBE"
assert_decision "$WORK/out-start-index-probe" "ready" "profile_start_index_probe_or_locate_path" "complete"
python3 - <<'PY' "$WORK/out-start-index-probe/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["terminal_path_start_index_write_parent_seconds"] == 0.18, candidate
assert candidate["terminal_path_start_index_write_left_seconds"] == 0.12, candidate
assert candidate["terminal_path_start_index_write_right_seconds"] == 0.04, candidate
assert candidate["terminal_path_start_index_write_dominant_child"] == "left", candidate
assert candidate["terminal_path_start_index_write_sampled_count_closure_status"] == "closed", candidate
assert candidate["terminal_path_start_index_write_probe_count"] == 300, candidate
assert candidate["terminal_path_start_index_write_probe_steps_total"] == 1800, candidate
PY

START_INDEX_STORE="$WORK/start-index-store.tsv"
cp "$TERMINAL" "$START_INDEX_STORE"
inject_start_index_write_split "$START_INDEX_STORE" "0.18" "0.03" "0.13" "300" "300" "0" "300" "300" "300" "300" "0" "0" "0" "0" "300" "0" "0"
run_and_assert "$WORK/out-start-index-store" --aggregate-tsv "$START_INDEX_STORE"
assert_decision "$WORK/out-start-index-store" "ready" "profile_start_index_store_path" "complete"
python3 - <<'PY' "$WORK/out-start-index-store/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["terminal_path_start_index_write_dominant_child"] == "right", candidate
assert candidate["terminal_path_start_index_write_probe_or_locate_share"] < candidate["terminal_path_start_index_write_entry_store_share"], candidate
PY

START_INDEX_STORE_INSERT="$WORK/start-index-store-insert.tsv"
cp "$START_INDEX_STORE" "$START_INDEX_STORE_INSERT"
inject_start_index_store_split "$START_INDEX_STORE_INSERT" "0.13" "0.09" "0.02" "0.02" "300" "300" "0" "0" "220" "40" "40" "220" "40" "40" "3520" "640" "640" "120" "120" "120" "35" "20" "18" "10" "8" "4"
run_and_assert "$WORK/out-start-index-store-insert" --aggregate-tsv "$START_INDEX_STORE_INSERT"
assert_decision "$WORK/out-start-index-store-insert" "ready" "profile_start_index_insert_store_path" "complete"
python3 - <<'PY' "$WORK/out-start-index-store-insert/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["terminal_path_start_index_store_dominant_child"] == "insert", candidate
assert candidate["terminal_path_start_index_store_insert_share"] > candidate["terminal_path_start_index_store_clear_share"], candidate
assert candidate["terminal_path_start_index_store_insert_share"] > candidate["terminal_path_start_index_store_overwrite_share"], candidate
PY

START_INDEX_STORE_CLEAR="$WORK/start-index-store-clear.tsv"
cp "$START_INDEX_STORE" "$START_INDEX_STORE_CLEAR"
inject_start_index_store_split "$START_INDEX_STORE_CLEAR" "0.13" "0.02" "0.08" "0.03" "300" "300" "0" "0" "40" "210" "50" "40" "210" "50" "640" "3360" "800" "90" "90" "90" "60" "36" "28" "14" "7" "9"
run_and_assert "$WORK/out-start-index-store-clear" --aggregate-tsv "$START_INDEX_STORE_CLEAR"
assert_decision "$WORK/out-start-index-store-clear" "ready" "profile_start_index_clear_store_path" "complete"

START_INDEX_STORE_WRITE_AMP_PRECEDENCE="$WORK/start-index-store-write-amp-precedence.tsv"
cp "$START_INDEX_STORE" "$START_INDEX_STORE_WRITE_AMP_PRECEDENCE"
inject_start_index_store_split "$START_INDEX_STORE_WRITE_AMP_PRECEDENCE" "0.13" "0.02" "0.08" "0.03" "300" "300" "0" "0" "40" "210" "50" "40" "210" "50" "640" "3360" "800" "90" "90" "90" "60" "36" "28" "20" "7" "9"
run_and_assert "$WORK/out-start-index-store-write-amp-precedence" --aggregate-tsv "$START_INDEX_STORE_WRITE_AMP_PRECEDENCE"
assert_decision "$WORK/out-start-index-store-write-amp-precedence" "ready" "profile_start_index_clear_overwrite_write_amplification" "complete"

START_INDEX_STORE_OVERWRITE="$WORK/start-index-store-overwrite.tsv"
cp "$START_INDEX_STORE" "$START_INDEX_STORE_OVERWRITE"
inject_start_index_store_split "$START_INDEX_STORE_OVERWRITE" "0.13" "0.02" "0.03" "0.08" "300" "300" "0" "0" "40" "50" "210" "40" "50" "210" "640" "800" "3360" "75" "75" "75" "68" "42" "39" "26" "12" "10"
run_and_assert "$WORK/out-start-index-store-overwrite" --aggregate-tsv "$START_INDEX_STORE_OVERWRITE"
assert_decision "$WORK/out-start-index-store-overwrite" "ready" "profile_start_index_overwrite_store_path" "complete"

START_INDEX_STORE_WRITE_AMP="$WORK/start-index-store-write-amp.tsv"
cp "$START_INDEX_STORE" "$START_INDEX_STORE_WRITE_AMP"
inject_start_index_store_split "$START_INDEX_STORE_WRITE_AMP" "0.13" "0.04" "0.04" "0.05" "300" "300" "0" "0" "100" "90" "110" "100" "90" "110" "1600" "1440" "1760" "70" "70" "70" "66" "48" "44" "72" "6" "5"
run_and_assert "$WORK/out-start-index-store-write-amp" --aggregate-tsv "$START_INDEX_STORE_WRITE_AMP"
assert_decision "$WORK/out-start-index-store-write-amp" "ready" "profile_start_index_clear_overwrite_write_amplification" "complete"

START_INDEX_STORE_NEAR_TIE="$WORK/start-index-store-near-tie.tsv"
cp "$START_INDEX_STORE" "$START_INDEX_STORE_NEAR_TIE"
inject_start_index_store_split "$START_INDEX_STORE_NEAR_TIE" "0.13" "0.06490" "0.06510" "0.00" "300" "300" "0" "0" "150" "150" "0" "150" "150" "0" "2400" "2400" "0" "80" "80" "80" "24" "16" "0" "0" "0" "0"
run_and_assert "$WORK/out-start-index-store-near-tie" --aggregate-tsv "$START_INDEX_STORE_NEAR_TIE"
assert_decision "$WORK/out-start-index-store-near-tie" "ready" "mark_start_index_store_as_distributed_store_overhead" "complete"
python3 - <<'PY' "$WORK/out-start-index-store-near-tie/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["terminal_path_start_index_store_case_weighted_dominant_child"] == "clear", candidate
assert candidate["terminal_path_start_index_store_seconds_weighted_dominant_child"] == "clear", candidate
assert candidate["terminal_path_start_index_store_case_majority_share"] == 1.0, candidate
assert candidate["terminal_path_start_index_store_dominance_status"] == "near_tie", candidate
assert candidate["terminal_path_start_index_store_child_margin_share"] < 0.05, candidate
PY

START_INDEX_STORE_NEAR_TIE_LOW_SHARE="$WORK/start-index-store-near-tie-low-share.tsv"
cp "$TERMINAL" "$START_INDEX_STORE_NEAR_TIE_LOW_SHARE"
inject_start_index_write_split "$START_INDEX_STORE_NEAR_TIE_LOW_SHARE" "0.075" "0.00" "0.075" "300" "300" "0" "0" "0" "300" "300" "0" "0" "0" "0" "300" "0" "0"
inject_start_index_store_split "$START_INDEX_STORE_NEAR_TIE_LOW_SHARE" "0.075" "0.03740" "0.03760" "0.00" "300" "300" "0" "0" "150" "150" "0" "150" "150" "0" "2400" "2400" "0" "80" "80" "80" "24" "16" "0" "0" "0" "0"
run_and_assert "$WORK/out-start-index-store-near-tie-low-share" --aggregate-tsv "$START_INDEX_STORE_NEAR_TIE_LOW_SHARE"
assert_decision "$WORK/out-start-index-store-near-tie-low-share" "ready" "mark_start_index_store_as_distributed_store_overhead" "complete"

TELEMETRY="$WORK/telemetry.tsv"
cp "$TERMINAL" "$TELEMETRY"
python3 - <<'PY' "$TELEMETRY"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
row = rows[0]
row.update({
    "context_apply_lookup_miss_reuse_writeback_candidate_copy_mean_seconds": "0.02",
    "context_apply_lookup_miss_reuse_writeback_key_rebind_mean_seconds": "0.02",
    "context_apply_lookup_miss_reuse_writeback_aux_heap_build_mean_seconds": "0.01",
    "context_apply_lookup_miss_reuse_writeback_aux_heap_update_mean_seconds": "0.01",
    "context_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds": "0.01",
    "context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds": "0.09",
    "context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds": "0.08",
    "context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds": "0.07",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds": "0.03",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds": "0.03",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds": "0.03",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds": "0.02",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds": "0.11",
    "context_apply_lookup_miss_reuse_writeback_aux_other_mean_seconds": "0.35",
    "context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds": "0.40",
})
with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
run_and_assert "$WORK/out-telemetry" --aggregate-tsv "$TELEMETRY"
assert_decision "$WORK/out-telemetry" "ready" "reduce_profiler_timer_overhead" "complete"

LEXICAL="$WORK/lexical.tsv"
cp "$TERMINAL" "$LEXICAL"
python3 - <<'PY' "$LEXICAL"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
row = rows[0]
extra_fields = [
    "context_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_span_first_half_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_terminal_span_second_half_mean_seconds",
]
for field in extra_fields:
    row.setdefault(field, "")
row["context_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_mean_seconds"] = "0.30"
row["context_apply_lookup_miss_reuse_writeback_terminal_span_first_half_mean_seconds"] = "0.20"
row["context_apply_lookup_miss_reuse_writeback_terminal_span_second_half_mean_seconds"] = "0.18"
fieldnames = list(rows[0].keys())
for field in extra_fields:
    if field not in fieldnames:
        fieldnames.append(field)
with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerow(row)
PY
run_and_assert "$WORK/out-lexical" --aggregate-tsv "$LEXICAL"
assert_decision "$WORK/out-lexical" "ready" "reduce_profiler_timer_overhead" "complete"
python3 - <<'PY' "$WORK/out-lexical/candidate_index_lifecycle_summary.json"
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = summary["candidate_index"]
assert candidate["dominant_terminal_span"] == "first_half", candidate
assert summary["intra_profile_closure_status"] == "residual_unexplained", summary
assert summary["profile_mode_overhead_status"] == "unknown", summary
PY

IMMATERIAL="$WORK/immaterial.tsv"
write_profile_tsv "$IMMATERIAL" "case-immaterial" "0.02" "0.015" "0.001" "0.001" "0.015" "0.013" "0.0005" "0.006" "0.001" "0.006" "0.0005" "0.001" "1000" "650" "350" "20" "350" "350" "2.00" "0.02" "4.00" "0.0002" "0.0002" "0.0002" "0.0002" "wl-immaterial" "/tmp/wl-immaterial.stderr.log"
run_and_assert "$WORK/out-immaterial" --aggregate-tsv "$IMMATERIAL"
assert_decision "$WORK/out-immaterial" "ready" "no_host_merge_runtime_work" "complete"

UNKNOWN="$WORK/unknown.tsv"
write_profile_tsv "$UNKNOWN" "case-unknown" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.05" "0.05" "0.37" "0.01" "0.22" "1000" "650" "350" "20" "350" "350" "" "" "" "0.01" "0.01" "0.01" "0.19"
run_and_assert "$WORK/out-unknown" --aggregate-tsv "$UNKNOWN"
assert_decision "$WORK/out-unknown" "ready_but_materiality_unknown" "inspect_candidate_index_timer_scope" "missing"

DUP="$WORK/dup.tsv"
DUP_A="$WORK/dup-a.tsv"
DUP_B="$WORK/dup-b.tsv"
write_profile_tsv "$DUP_A" "case-a" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.26" "0.05" "0.16" "0.01" "0.02" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.01" "0.01" "0.01" "0.01" "wl-dup" "/tmp/wl-dup.stderr.log"
write_profile_tsv "$DUP_B" "case-b" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.26" "0.05" "0.16" "0.01" "0.02" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.01" "0.01" "0.01" "0.01" "wl-dup" "/tmp/wl-dup.stderr.log"
cp "$DUP_A" "$DUP"
tail -n +2 "$DUP_B" >>"$DUP"
run_and_assert "$WORK/out-dup" --aggregate-tsv "$DUP"
assert_decision "$WORK/out-dup" "ready" "profile_lookup_miss_candidate_set_full_probe" "duplicate_grouped"

MISMATCH="$WORK/mismatch.tsv"
MISMATCH_A="$WORK/mismatch-a.tsv"
MISMATCH_B="$WORK/mismatch-b.tsv"
write_profile_tsv "$MISMATCH_A" "case-a" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.05" "0.05" "0.34" "0.03" "0.12" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.03" "0.03" "0.03" "0.03" "wl-shared" "/tmp/wl-a.stderr.log"
write_profile_tsv "$MISMATCH_B" "case-b" "1.00" "0.50" "0.02" "0.03" "0.50" "0.48" "0.01" "0.05" "0.05" "0.34" "0.03" "0.12" "1000" "650" "350" "20" "350" "350" "2.50" "0.50" "5.00" "0.03" "0.03" "0.03" "0.03" "wl-shared" "/tmp/wl-b.stderr.log"
cp "$MISMATCH_A" "$MISMATCH"
tail -n +2 "$MISMATCH_B" >>"$MISMATCH"
run_and_assert "$WORK/out-mismatch" --aggregate-tsv "$MISMATCH"
assert_decision "$WORK/out-mismatch" "ready_but_materiality_unknown" "inspect_candidate_index_timer_scope" "mismatched"

MISSING="$WORK/missing.tsv"
cat >"$MISSING" <<'EOF'
case_id	context_apply_mean_seconds
case-missing	1.0
EOF
run_and_assert "$WORK/out-missing" --aggregate-tsv "$MISSING"
assert_decision "$WORK/out-missing" "not_ready" "fix_profile_inputs" "missing"

echo "check_summarize_sim_initial_host_merge_candidate_index_lifecycle: PASS"
