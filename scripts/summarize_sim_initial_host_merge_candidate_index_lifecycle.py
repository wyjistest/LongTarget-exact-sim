#!/usr/bin/env python3
import argparse
import ctypes
import csv
import json
from pathlib import Path


CASE_FIELDNAMES = [
    "case_id",
    "aggregate_tsv",
    "workload_id",
    "benchmark_source",
    "profile_mode",
    "terminal_telemetry_overhead_mode_requested",
    "terminal_telemetry_overhead_mode_effective",
    "state_update_bookkeeping_mode_requested",
    "state_update_bookkeeping_mode_effective",
    "context_apply_mean_seconds",
    "sim_initial_scan_cpu_merge_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
    "candidate_index_mean_seconds",
    "candidate_index_share_of_initial_cpu_merge",
    "candidate_index_share_of_sim_seconds",
    "candidate_index_share_of_total_seconds",
    "initial_cpu_merge_share_of_sim_seconds",
    "initial_cpu_merge_share_of_total_seconds",
    "lookup_mean_seconds",
    "lookup_hit_mean_seconds",
    "lookup_miss_mean_seconds",
    "lookup_miss_open_slot_mean_seconds",
    "lookup_miss_candidate_set_full_probe_mean_seconds",
    "lookup_miss_eviction_select_mean_seconds",
    "lookup_miss_reuse_writeback_mean_seconds",
    "candidate_index_erase_mean_seconds",
    "candidate_index_insert_mean_seconds",
    "lookup_miss_reuse_writeback_victim_reset_mean_seconds",
    "lookup_miss_reuse_writeback_key_rebind_mean_seconds",
    "lookup_miss_reuse_writeback_candidate_copy_mean_seconds",
    "lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds",
    "lookup_miss_reuse_writeback_aux_heap_build_mean_seconds",
    "lookup_miss_reuse_writeback_aux_heap_update_mean_seconds",
    "lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds",
    "candidate_index_lookup_count",
    "candidate_index_hit_count",
    "candidate_index_miss_count",
    "candidate_index_erase_count",
    "candidate_index_insert_count",
    "full_set_miss_count",
    "candidate_index_scope_gap_seconds",
    "candidate_index_scope_gap_share_of_candidate_index",
    "candidate_index_parent_seconds",
    "candidate_index_child_known_seconds",
    "candidate_index_unexplained_seconds",
    "candidate_index_unexplained_share_of_candidate_index",
    "lookup_partition_gap_seconds",
    "lookup_partition_gap_share_of_candidate_index",
    "lookup_miss_partition_gap_seconds",
    "lookup_miss_partition_gap_share_of_candidate_index",
    "reuse_writeback_partition_gap_seconds",
    "reuse_writeback_partition_gap_share_of_candidate_index",
    "lookup_miss_reuse_writeback_parent_seconds",
    "lookup_miss_reuse_writeback_child_known_seconds",
    "lookup_miss_reuse_writeback_unexplained_seconds",
    "lookup_miss_reuse_writeback_unexplained_share_of_candidate_index",
    "aux_bookkeeping_partition_gap_seconds",
    "aux_bookkeeping_partition_gap_share_of_candidate_index",
    "aux_other_partition_gap_seconds",
    "aux_other_partition_gap_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_parent_seconds",
    "lookup_miss_reuse_writeback_aux_other_child_known_seconds",
    "lookup_miss_reuse_writeback_aux_other_unexplained_seconds",
    "lookup_miss_reuse_writeback_aux_other_unexplained_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_residual_parent_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_residual_residual_share_of_candidate_index",
    "lookup_hit_share_of_candidate_index",
    "lookup_miss_share_of_candidate_index",
    "lookup_miss_open_slot_share_of_candidate_index",
    "lookup_miss_candidate_set_full_probe_share_of_candidate_index",
    "lookup_miss_candidate_set_full_probe_parent_seconds",
    "lookup_miss_candidate_set_full_probe_scan_seconds",
    "lookup_miss_candidate_set_full_probe_compare_seconds",
    "lookup_miss_candidate_set_full_probe_branch_or_guard_seconds",
    "lookup_miss_candidate_set_full_probe_bookkeeping_seconds",
    "lookup_miss_candidate_set_full_probe_child_known_seconds",
    "lookup_miss_candidate_set_full_probe_unexplained_seconds",
    "lookup_miss_candidate_set_full_probe_unexplained_share",
    "lookup_miss_candidate_set_full_probe_sampled_event_count",
    "lookup_miss_candidate_set_full_probe_covered_sampled_event_count",
    "lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count",
    "lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count",
    "lookup_miss_candidate_set_full_probe_sampled_count_closure_status",
    "lookup_miss_candidate_set_full_probe_dominant_child",
    "lookup_miss_candidate_set_full_probe_coverage_share",
    "lookup_miss_candidate_set_full_probe_unclassified_share",
    "lookup_miss_candidate_set_full_probe_multi_child_share",
    "lookup_miss_candidate_set_full_probe_scan_share",
    "lookup_miss_candidate_set_full_probe_compare_share",
    "lookup_miss_candidate_set_full_probe_branch_or_guard_share",
    "lookup_miss_candidate_set_full_probe_bookkeeping_share",
    "lookup_miss_candidate_set_full_probe_count",
    "lookup_miss_candidate_set_full_probe_slots_scanned_total",
    "lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean",
    "lookup_miss_candidate_set_full_probe_slots_scanned_p50",
    "lookup_miss_candidate_set_full_probe_slots_scanned_p90",
    "lookup_miss_candidate_set_full_probe_slots_scanned_p99",
    "lookup_miss_candidate_set_full_probe_full_scan_count",
    "lookup_miss_candidate_set_full_probe_early_exit_count",
    "lookup_miss_candidate_set_full_probe_found_existing_count",
    "lookup_miss_candidate_set_full_probe_confirmed_absent_count",
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_count",
    "lookup_miss_candidate_set_full_probe_same_key_reprobe_count",
    "lookup_miss_candidate_set_full_probe_same_event_reprobe_count",
    "lookup_miss_candidate_set_full_probe_full_scan_share",
    "lookup_miss_candidate_set_full_probe_early_exit_share",
    "lookup_miss_candidate_set_full_probe_found_existing_share",
    "lookup_miss_candidate_set_full_probe_confirmed_absent_share",
    "lookup_miss_candidate_set_full_probe_redundant_reprobe_share",
    "lookup_miss_eviction_select_share_of_candidate_index",
    "lookup_miss_reuse_writeback_share_of_candidate_index",
    "candidate_index_erase_share_of_candidate_index",
    "candidate_index_insert_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_start_index_rebuild_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_residual_share_of_candidate_index",
    "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_seconds",
    "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index",
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
    "terminal_path_start_index_write_sampled_event_count",
    "terminal_path_start_index_write_covered_sampled_event_count",
    "terminal_path_start_index_write_unclassified_sampled_event_count",
    "terminal_path_start_index_write_multi_child_sampled_event_count",
    "terminal_path_start_index_write_left_sampled_event_count",
    "terminal_path_start_index_write_right_sampled_event_count",
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
    "terminal_lexical_parent_seconds",
    "terminal_span_first_half_seconds",
    "terminal_span_second_half_seconds",
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
    "profile_overhead_status",
    "candidate_index_timer_scope_status",
    "reuse_aux_other_timer_scope_status",
    "terminal_residual_status",
    "timer_scope_status",
    "materiality_status",
    "recommended_next_action",
]

MATERIALITY_BENCHMARK_FIELDS = [
    "sim_initial_scan_cpu_merge_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
]

TERMINAL_PATH_SCOPE = "reuse_writeback_post_victim_reset_tail"
SIM_CANDIDATE_BYTES = ctypes.sizeof(ctypes.c_long) * 9
SIM_CANDIDATE_START_INDEX_ENTRY_BYTES = (
    ctypes.sizeof(ctypes.c_ubyte)
    + ctypes.sizeof(ctypes.c_long) * 2
    + ctypes.sizeof(ctypes.c_int)
)

REQUIRED_FIELDS = [
    "case_id",
    "context_apply_mean_seconds",
    "context_apply_candidate_index_mean_seconds",
    "context_apply_candidate_index_erase_mean_seconds",
    "context_apply_candidate_index_insert_mean_seconds",
    "context_apply_lookup_mean_seconds",
    "context_apply_lookup_miss_mean_seconds",
    "context_apply_lookup_miss_open_slot_mean_seconds",
    "context_apply_lookup_miss_candidate_set_full_probe_mean_seconds",
    "context_apply_lookup_miss_eviction_select_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_victim_reset_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_key_rebind_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_candidate_copy_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_heap_build_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_heap_update_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_other_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds",
    "context_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds",
    "context_apply_candidate_index_lookup_count",
    "context_apply_candidate_index_hit_count",
    "context_apply_candidate_index_miss_count",
    "context_apply_candidate_index_erase_count",
    "context_apply_candidate_index_insert_count",
    "context_apply_full_set_miss_count",
    "verify_ok",
]


class LifecycleInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate-tsv", action="append", required=True)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-index-dominant-threshold", type=float, default=0.15)
    parser.add_argument("--host-merge-materiality-threshold", type=float, default=0.05)
    parser.add_argument("--candidate-index-materiality-threshold", type=float, default=0.03)
    parser.add_argument("--erase-dominant-share-threshold", type=float, default=0.20)
    parser.add_argument("--probe-dominant-share-threshold", type=float, default=0.20)
    parser.add_argument("--full-probe-unexplained-threshold", type=float, default=0.10)
    parser.add_argument("--full-probe-scan-share-threshold", type=float, default=0.40)
    parser.add_argument("--full-probe-compare-share-threshold", type=float, default=0.40)
    parser.add_argument("--full-probe-branch-share-threshold", type=float, default=0.40)
    parser.add_argument(
        "--full-probe-redundant-reprobe-threshold", type=float, default=0.30
    )
    parser.add_argument("--full-probe-full-scan-share-threshold", type=float, default=0.50)
    parser.add_argument("--full-probe-slots-scanned-p90-threshold", type=float, default=64.0)
    parser.add_argument("--reuse-writeback-dominant-share-threshold", type=float, default=0.25)
    parser.add_argument("--aux-other-dominant-share-threshold", type=float, default=0.25)
    parser.add_argument("--timer-scope-gap-threshold", type=float, default=0.10)
    parser.add_argument("--aux-other-residual-threshold", type=float, default=0.15)
    parser.add_argument("--terminal-residual-dominant-share-threshold", type=float, default=0.20)
    parser.add_argument("--start-index-write-dominant-share-threshold", type=float, default=0.20)
    parser.add_argument("--start-index-write-child-share-threshold", type=float, default=0.40)
    parser.add_argument("--start-index-write-unexplained-threshold", type=float, default=0.10)
    parser.add_argument("--start-index-write-idempotent-threshold", type=float, default=0.30)
    parser.add_argument("--start-index-store-child-share-threshold", type=float, default=0.40)
    parser.add_argument("--start-index-store-unexplained-threshold", type=float, default=0.10)
    parser.add_argument("--start-index-store-child-margin-threshold", type=float, default=0.05)
    parser.add_argument(
        "--start-index-store-clear-overwrite-share-threshold",
        type=float,
        default=0.30,
    )
    parser.add_argument("--state-update-dominant-share-threshold", type=float, default=0.20)
    parser.add_argument("--state-update-unexplained-threshold", type=float, default=0.10)
    parser.add_argument(
        "--state-update-bookkeeping-share-threshold", type=float, default=0.40
    )
    parser.add_argument("--state-update-child-share-threshold", type=float, default=0.40)
    parser.add_argument("--state-update-child-margin-threshold", type=float, default=0.05)
    return parser.parse_args()


def share(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def parse_bool_like(value):
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    raise LifecycleInputError(f"invalid verify_ok value: {value!r}")


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    if not rows:
        raise LifecycleInputError(f"{path}: no rows")
    missing = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
    if missing:
        raise LifecycleInputError(f"{path}: missing required fields: {', '.join(missing)}")
    return rows


def to_float(row, field, path):
    try:
        return float(row[field])
    except (TypeError, ValueError) as exc:
        raise LifecycleInputError(f"{path}: invalid float for {field}: {row.get(field)!r}") from exc


def to_int(row, field, path):
    try:
        return int(float(row[field]))
    except (TypeError, ValueError) as exc:
        raise LifecycleInputError(f"{path}: invalid int for {field}: {row.get(field)!r}") from exc


def resolve_optional_float(row, fields):
    for field in fields:
        if field in row and str(row[field]).strip() != "":
            return float(row[field])
    return None


def resolve_optional_int(row, fields):
    for field in fields:
        if field in row and str(row[field]).strip() != "":
            return int(float(row[field]))
    return None


def resolve_optional_text(row, field):
    return str(row.get(field, "")).strip()


def dominant_terminal_child(values):
    return max(
        values.items(),
        key=lambda item: (item[1], item[0]),
    )[0]


def dominant_binary_child(left_seconds, right_seconds):
    if left_seconds is None or right_seconds is None:
        return "unknown"
    if left_seconds <= 0.0 and right_seconds <= 0.0:
        return "unknown"
    if left_seconds >= right_seconds:
        return "left"
    return "right"


def sum_optional_rows(rows, key):
    if not rows:
        return None
    total = 0.0
    saw_value = False
    for row in rows:
        value = row.get(key)
        if value is None:
            return None
        total += value
        saw_value = True
    return total if saw_value else None


def sum_optional_int_rows(rows, key):
    if not rows:
        return None
    total = 0
    saw_value = False
    for row in rows:
        value = row.get(key)
        if value is None:
            return None
        total += int(value)
        saw_value = True
    return total if saw_value else None


def max_optional_rows(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return None
    return max(values)


def classify_sampled_count_closure_status(
    sampled_event_count,
    covered_sampled_event_count,
    unclassified_sampled_event_count,
):
    if (
        sampled_event_count is None
        or covered_sampled_event_count is None
        or unclassified_sampled_event_count is None
        or sampled_event_count <= 0
    ):
        return "unknown"
    if (
        covered_sampled_event_count == sampled_event_count
        and unclassified_sampled_event_count == 0
    ):
        return "closed"
    return "open"


def dominant_full_probe_child(scan_seconds, compare_seconds, branch_or_guard_seconds, bookkeeping_seconds):
    values = {
        "scan": scan_seconds or 0.0,
        "compare": compare_seconds or 0.0,
        "branch_or_guard": branch_or_guard_seconds or 0.0,
        "bookkeeping": bookkeeping_seconds or 0.0,
    }
    best_value = max(values.values())
    if best_value <= 0.0:
        return "unknown"
    winners = [name for name, value in values.items() if abs(value - best_value) <= 1e-12]
    if len(winners) != 1:
        return "unknown"
    return winners[0]


def derive_lookup_miss_candidate_set_full_probe_metrics(
    *,
    fallback_parent_seconds,
    split_parent_seconds=None,
    scan_seconds=None,
    compare_seconds=None,
    branch_or_guard_seconds=None,
    bookkeeping_seconds=None,
    child_known_seconds=None,
    unexplained_seconds=None,
    sampled_event_count=None,
    covered_sampled_event_count=None,
    unclassified_sampled_event_count=None,
    multi_child_sampled_event_count=None,
    full_probe_count=None,
    slots_scanned_total=None,
    slots_scanned_per_probe_mean=None,
    slots_scanned_p50=None,
    slots_scanned_p90=None,
    slots_scanned_p99=None,
    full_scan_count=None,
    early_exit_count=None,
    found_existing_count=None,
    confirmed_absent_count=None,
    redundant_reprobe_count=None,
    same_key_reprobe_count=None,
    same_event_reprobe_count=None,
):
    split_present = any(
        value is not None
        for value in (
            split_parent_seconds,
            scan_seconds,
            compare_seconds,
            branch_or_guard_seconds,
            bookkeeping_seconds,
            child_known_seconds,
            unexplained_seconds,
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
        )
    )

    parent_seconds = (
        split_parent_seconds if split_parent_seconds is not None else fallback_parent_seconds
    )
    if parent_seconds is None:
        parent_seconds = 0.0

    if split_present:
        scan_seconds = scan_seconds or 0.0
        compare_seconds = compare_seconds or 0.0
        branch_or_guard_seconds = branch_or_guard_seconds or 0.0
        bookkeeping_seconds = bookkeeping_seconds or 0.0
        child_known_seconds = (
            child_known_seconds
            if child_known_seconds is not None
            else (
                scan_seconds
                + compare_seconds
                + branch_or_guard_seconds
                + bookkeeping_seconds
            )
        )
        unexplained_seconds = (
            unexplained_seconds
            if unexplained_seconds is not None
            else max(parent_seconds - child_known_seconds, 0.0)
        )
    else:
        scan_seconds = 0.0
        compare_seconds = 0.0
        branch_or_guard_seconds = 0.0
        bookkeeping_seconds = 0.0
        child_known_seconds = 0.0
        unexplained_seconds = max(parent_seconds, 0.0)

    sampled_event_count = sampled_event_count or 0
    covered_sampled_event_count = covered_sampled_event_count or 0
    unclassified_sampled_event_count = unclassified_sampled_event_count or 0
    multi_child_sampled_event_count = multi_child_sampled_event_count or 0
    full_probe_count = full_probe_count or 0
    slots_scanned_total = slots_scanned_total or 0
    slots_scanned_per_probe_mean = (
        slots_scanned_per_probe_mean
        if slots_scanned_per_probe_mean is not None
        else share(slots_scanned_total, full_probe_count)
    )
    slots_scanned_p50 = slots_scanned_p50 or 0.0
    slots_scanned_p90 = slots_scanned_p90 or 0.0
    slots_scanned_p99 = slots_scanned_p99 or 0.0
    full_scan_count = full_scan_count or 0
    early_exit_count = early_exit_count or 0
    found_existing_count = found_existing_count or 0
    confirmed_absent_count = confirmed_absent_count or 0
    redundant_reprobe_count = redundant_reprobe_count or 0
    same_key_reprobe_count = same_key_reprobe_count or 0
    same_event_reprobe_count = same_event_reprobe_count or 0

    sampled_count_closure_status = (
        classify_sampled_count_closure_status(
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
        )
        if split_present
        else "unknown"
    )

    return {
        "parent_seconds": parent_seconds,
        "scan_seconds": scan_seconds,
        "compare_seconds": compare_seconds,
        "branch_or_guard_seconds": branch_or_guard_seconds,
        "bookkeeping_seconds": bookkeeping_seconds,
        "child_known_seconds": child_known_seconds,
        "unexplained_seconds": unexplained_seconds,
        "unexplained_share": share(unexplained_seconds, parent_seconds),
        "sampled_event_count": sampled_event_count,
        "covered_sampled_event_count": covered_sampled_event_count,
        "unclassified_sampled_event_count": unclassified_sampled_event_count,
        "multi_child_sampled_event_count": multi_child_sampled_event_count,
        "sampled_count_closure_status": sampled_count_closure_status,
        "dominant_child": dominant_full_probe_child(
            scan_seconds,
            compare_seconds,
            branch_or_guard_seconds,
            bookkeeping_seconds,
        ),
        "coverage_share": share(covered_sampled_event_count, sampled_event_count),
        "unclassified_share": share(unclassified_sampled_event_count, sampled_event_count),
        "multi_child_share": share(multi_child_sampled_event_count, sampled_event_count),
        "scan_share": share(scan_seconds, parent_seconds),
        "compare_share": share(compare_seconds, parent_seconds),
        "branch_or_guard_share": share(branch_or_guard_seconds, parent_seconds),
        "bookkeeping_share": share(bookkeeping_seconds, parent_seconds),
        "count": full_probe_count,
        "slots_scanned_total": slots_scanned_total,
        "slots_scanned_per_probe_mean": slots_scanned_per_probe_mean,
        "slots_scanned_p50": slots_scanned_p50,
        "slots_scanned_p90": slots_scanned_p90,
        "slots_scanned_p99": slots_scanned_p99,
        "full_scan_count": full_scan_count,
        "early_exit_count": early_exit_count,
        "found_existing_count": found_existing_count,
        "confirmed_absent_count": confirmed_absent_count,
        "redundant_reprobe_count": redundant_reprobe_count,
        "same_key_reprobe_count": same_key_reprobe_count,
        "same_event_reprobe_count": same_event_reprobe_count,
        "full_scan_share": share(full_scan_count, full_probe_count),
        "early_exit_share": share(early_exit_count, full_probe_count),
        "found_existing_share": share(found_existing_count, full_probe_count),
        "confirmed_absent_share": share(confirmed_absent_count, full_probe_count),
        "redundant_reprobe_share": share(redundant_reprobe_count, full_probe_count),
    }


def derive_start_index_write_metrics(
    *,
    candidate_index_seconds,
    fallback_parent_seconds,
    split_parent_seconds=None,
    left_seconds=None,
    right_seconds=None,
    child_known_seconds=None,
    unexplained_seconds=None,
    sampled_event_count=None,
    covered_sampled_event_count=None,
    unclassified_sampled_event_count=None,
    multi_child_sampled_event_count=None,
    left_sampled_event_count=None,
    right_sampled_event_count=None,
    insert_count=None,
    update_existing_count=None,
    clear_count=None,
    overwrite_count=None,
    idempotent_count=None,
    value_changed_count=None,
    probe_count=None,
    probe_steps_total=None,
):
    split_present = any(
        value is not None
        for value in (
            split_parent_seconds,
            left_seconds,
            right_seconds,
            child_known_seconds,
            unexplained_seconds,
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
        )
    )

    parent_seconds = (
        split_parent_seconds if split_parent_seconds is not None else fallback_parent_seconds
    )
    if parent_seconds is None:
        parent_seconds = 0.0

    if split_present:
        left_seconds = left_seconds or 0.0
        right_seconds = right_seconds or 0.0
        child_known_seconds = (
            child_known_seconds
            if child_known_seconds is not None
            else (left_seconds + right_seconds)
        )
        unexplained_seconds = (
            unexplained_seconds
            if unexplained_seconds is not None
            else max(parent_seconds - child_known_seconds, 0.0)
        )
    else:
        left_seconds = 0.0
        right_seconds = 0.0
        child_known_seconds = 0.0
        unexplained_seconds = max(parent_seconds, 0.0)

    sampled_event_count = sampled_event_count or 0
    covered_sampled_event_count = covered_sampled_event_count or 0
    unclassified_sampled_event_count = unclassified_sampled_event_count or 0
    multi_child_sampled_event_count = multi_child_sampled_event_count or 0
    left_sampled_event_count = left_sampled_event_count or 0
    right_sampled_event_count = right_sampled_event_count or 0
    insert_count = insert_count or 0
    update_existing_count = update_existing_count or 0
    clear_count = clear_count or 0
    overwrite_count = overwrite_count or 0
    idempotent_count = idempotent_count or 0
    value_changed_count = value_changed_count or 0
    probe_count = probe_count or 0
    probe_steps_total = probe_steps_total or 0

    sampled_count_closure_status = (
        classify_sampled_count_closure_status(
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
        )
        if split_present
        else "unknown"
    )
    dominant_child = (
        dominant_binary_child(left_seconds, right_seconds) if split_present else "unknown"
    )

    return {
        "parent_seconds": parent_seconds,
        "left_seconds": left_seconds,
        "right_seconds": right_seconds,
        "child_known_seconds": child_known_seconds,
        "unexplained_seconds": unexplained_seconds,
        "unexplained_share": share(unexplained_seconds, candidate_index_seconds),
        "sampled_event_count": sampled_event_count,
        "covered_sampled_event_count": covered_sampled_event_count,
        "unclassified_sampled_event_count": unclassified_sampled_event_count,
        "multi_child_sampled_event_count": multi_child_sampled_event_count,
        "left_sampled_event_count": left_sampled_event_count,
        "right_sampled_event_count": right_sampled_event_count,
        "sampled_count_closure_status": sampled_count_closure_status,
        "dominant_child": dominant_child,
        "coverage_share": share(covered_sampled_event_count, sampled_event_count),
        "unclassified_share": share(unclassified_sampled_event_count, sampled_event_count),
        "multi_child_share": share(multi_child_sampled_event_count, sampled_event_count),
        "probe_or_locate_share": share(left_seconds, parent_seconds),
        "entry_store_share": share(right_seconds, parent_seconds),
        "insert_count": insert_count,
        "update_existing_count": update_existing_count,
        "clear_count": clear_count,
        "overwrite_count": overwrite_count,
        "idempotent_count": idempotent_count,
        "value_changed_count": value_changed_count,
        "probe_count": probe_count,
        "probe_steps_total": probe_steps_total,
    }


def dominant_store_child(insert_seconds, clear_seconds, overwrite_seconds):
    values = {
        "insert": insert_seconds or 0.0,
        "clear": clear_seconds or 0.0,
        "overwrite": overwrite_seconds or 0.0,
    }
    best_value = max(values.values())
    if best_value <= 0.0:
        return "unknown"
    winners = [name for name, value in values.items() if abs(value - best_value) <= 1e-12]
    if len(winners) != 1:
        return "unknown"
    return winners[0]


def dominant_store_child_with_mixed(values):
    best_value = max(values.values())
    if best_value <= 0.0:
        return "unknown"
    winners = [name for name, value in values.items() if abs(value - best_value) <= 1e-12]
    if len(winners) == 1:
        return winners[0]
    return "mixed"


def start_index_store_child_margin_share(insert_seconds, clear_seconds, overwrite_seconds, parent_seconds):
    values = sorted(
        [insert_seconds or 0.0, clear_seconds or 0.0, overwrite_seconds or 0.0],
        reverse=True,
    )
    if len(values) < 2 or parent_seconds is None or parent_seconds <= 0.0:
        return 0.0
    return share(max(values[0] - values[1], 0.0), parent_seconds)


def classify_start_index_store_dominance(
    *,
    case_weighted_dominant_child,
    seconds_weighted_dominant_child,
    child_margin_share,
    child_margin_threshold,
):
    known_children = {"insert", "clear", "overwrite"}
    if (
        case_weighted_dominant_child in known_children
        and seconds_weighted_dominant_child in known_children
        and case_weighted_dominant_child != seconds_weighted_dominant_child
    ):
        return "case_weighted_aggregate_conflict"
    if child_margin_share < child_margin_threshold:
        return "near_tie"
    if seconds_weighted_dominant_child in known_children:
        return "stable"
    return "unknown"


def aggregate_start_index_store_case_dominance(rows):
    counts = {"insert": 0, "clear": 0, "overwrite": 0}
    event_weights = {"insert": 0, "clear": 0, "overwrite": 0}
    total_cases = len(rows)
    for row in rows:
        dominant_child = dominant_store_child(
            row.get("terminal_path_start_index_store_insert_seconds", 0.0),
            row.get("terminal_path_start_index_store_clear_seconds", 0.0),
            row.get("terminal_path_start_index_store_overwrite_seconds", 0.0),
        )
        if dominant_child in counts:
            counts[dominant_child] += 1
        event_weights["insert"] += int(
            row.get("terminal_path_start_index_store_insert_sampled_event_count", 0) or 0
        )
        event_weights["clear"] += int(
            row.get("terminal_path_start_index_store_clear_sampled_event_count", 0) or 0
        )
        event_weights["overwrite"] += int(
            row.get("terminal_path_start_index_store_overwrite_sampled_event_count", 0) or 0
        )

    best_case_count = max(counts.values()) if counts else 0
    if best_case_count <= 0:
        case_weighted_dominant_child = "unknown"
    else:
        case_winners = [
            label for label, value in counts.items() if value == best_case_count and value > 0
        ]
        if len(case_winners) == 1:
            case_weighted_dominant_child = case_winners[0]
        else:
            case_weighted_dominant_child = "mixed"

    case_majority_share = share(best_case_count, total_cases) if total_cases > 0 else 0.0
    event_weighted_dominant_child = dominant_store_child_with_mixed(event_weights)
    return {
        "case_weighted_dominant_child": case_weighted_dominant_child,
        "case_majority_share": case_majority_share,
        "event_weighted_dominant_child": event_weighted_dominant_child,
    }


def derive_start_index_store_metrics(
    *,
    fallback_parent_seconds,
    split_parent_seconds=None,
    insert_seconds=None,
    clear_seconds=None,
    overwrite_seconds=None,
    child_known_seconds=None,
    unexplained_seconds=None,
    sampled_event_count=None,
    covered_sampled_event_count=None,
    unclassified_sampled_event_count=None,
    multi_child_sampled_event_count=None,
    insert_sampled_event_count=None,
    clear_sampled_event_count=None,
    overwrite_sampled_event_count=None,
    insert_count=None,
    clear_count=None,
    overwrite_count=None,
    insert_bytes=None,
    clear_bytes=None,
    overwrite_bytes=None,
    unique_entry_count=None,
    unique_slot_count=None,
    unique_key_count=None,
    same_entry_rewrite_count=None,
    same_cacheline_rewrite_count=None,
    back_to_back_same_entry_write_count=None,
    clear_then_overwrite_same_entry_count=None,
    overwrite_then_insert_same_entry_count=None,
    insert_then_clear_same_entry_count=None,
):
    split_present = any(
        value is not None
        for value in (
            split_parent_seconds,
            insert_seconds,
            clear_seconds,
            overwrite_seconds,
            child_known_seconds,
            unexplained_seconds,
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
        )
    )

    parent_seconds = (
        split_parent_seconds if split_parent_seconds is not None else fallback_parent_seconds
    )
    if parent_seconds is None:
        parent_seconds = 0.0

    if split_present:
        insert_seconds = insert_seconds or 0.0
        clear_seconds = clear_seconds or 0.0
        overwrite_seconds = overwrite_seconds or 0.0
        child_known_seconds = (
            child_known_seconds
            if child_known_seconds is not None
            else (insert_seconds + clear_seconds + overwrite_seconds)
        )
        unexplained_seconds = (
            unexplained_seconds
            if unexplained_seconds is not None
            else max(parent_seconds - child_known_seconds, 0.0)
        )
    else:
        insert_seconds = 0.0
        clear_seconds = 0.0
        overwrite_seconds = 0.0
        child_known_seconds = 0.0
        unexplained_seconds = max(parent_seconds, 0.0)

    sampled_event_count = sampled_event_count or 0
    covered_sampled_event_count = covered_sampled_event_count or 0
    unclassified_sampled_event_count = unclassified_sampled_event_count or 0
    multi_child_sampled_event_count = multi_child_sampled_event_count or 0
    insert_sampled_event_count = insert_sampled_event_count or 0
    clear_sampled_event_count = clear_sampled_event_count or 0
    overwrite_sampled_event_count = overwrite_sampled_event_count or 0
    insert_count = insert_count or 0
    clear_count = clear_count or 0
    overwrite_count = overwrite_count or 0
    insert_bytes = insert_bytes or 0
    clear_bytes = clear_bytes or 0
    overwrite_bytes = overwrite_bytes or 0
    unique_entry_count = unique_entry_count or 0
    unique_slot_count = unique_slot_count or 0
    unique_key_count = unique_key_count or 0
    same_entry_rewrite_count = same_entry_rewrite_count or 0
    same_cacheline_rewrite_count = same_cacheline_rewrite_count or 0
    back_to_back_same_entry_write_count = back_to_back_same_entry_write_count or 0
    clear_then_overwrite_same_entry_count = clear_then_overwrite_same_entry_count or 0
    overwrite_then_insert_same_entry_count = overwrite_then_insert_same_entry_count or 0
    insert_then_clear_same_entry_count = insert_then_clear_same_entry_count or 0

    sampled_count_closure_status = (
        classify_sampled_count_closure_status(
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
        )
        if split_present
        else "unknown"
    )
    seconds_weighted_dominant_child = dominant_store_child(
        insert_seconds, clear_seconds, overwrite_seconds
    )
    event_weighted_dominant_child = dominant_store_child_with_mixed(
        {
            "insert": insert_sampled_event_count,
            "clear": clear_sampled_event_count,
            "overwrite": overwrite_sampled_event_count,
        }
    )
    child_margin_share = start_index_store_child_margin_share(
        insert_seconds, clear_seconds, overwrite_seconds, parent_seconds
    )
    case_weighted_dominant_child = (
        seconds_weighted_dominant_child
        if seconds_weighted_dominant_child in {"insert", "clear", "overwrite"}
        else "unknown"
    )
    case_majority_share = 1.0 if case_weighted_dominant_child != "unknown" else 0.0
    dominance_status = classify_start_index_store_dominance(
        case_weighted_dominant_child=case_weighted_dominant_child,
        seconds_weighted_dominant_child=seconds_weighted_dominant_child,
        child_margin_share=child_margin_share,
        child_margin_threshold=0.05,
    )

    return {
        "parent_seconds": parent_seconds,
        "insert_seconds": insert_seconds,
        "clear_seconds": clear_seconds,
        "overwrite_seconds": overwrite_seconds,
        "child_known_seconds": child_known_seconds,
        "unexplained_seconds": unexplained_seconds,
        "unexplained_share": share(unexplained_seconds, parent_seconds),
        "sampled_event_count": sampled_event_count,
        "covered_sampled_event_count": covered_sampled_event_count,
        "unclassified_sampled_event_count": unclassified_sampled_event_count,
        "multi_child_sampled_event_count": multi_child_sampled_event_count,
        "insert_sampled_event_count": insert_sampled_event_count,
        "clear_sampled_event_count": clear_sampled_event_count,
        "overwrite_sampled_event_count": overwrite_sampled_event_count,
        "sampled_count_closure_status": sampled_count_closure_status,
        "dominant_child": seconds_weighted_dominant_child,
        "case_weighted_dominant_child": case_weighted_dominant_child,
        "seconds_weighted_dominant_child": seconds_weighted_dominant_child,
        "event_weighted_dominant_child": event_weighted_dominant_child,
        "case_majority_share": case_majority_share,
        "child_margin_share": child_margin_share,
        "dominance_status": dominance_status,
        "coverage_share": share(covered_sampled_event_count, sampled_event_count),
        "unclassified_share": share(unclassified_sampled_event_count, sampled_event_count),
        "multi_child_share": share(multi_child_sampled_event_count, sampled_event_count),
        "insert_share": share(insert_seconds, parent_seconds),
        "clear_share": share(clear_seconds, parent_seconds),
        "overwrite_share": share(overwrite_seconds, parent_seconds),
        "insert_count": insert_count,
        "clear_count": clear_count,
        "overwrite_count": overwrite_count,
        "insert_bytes": insert_bytes,
        "clear_bytes": clear_bytes,
        "overwrite_bytes": overwrite_bytes,
        "unique_entry_count": unique_entry_count,
        "unique_slot_count": unique_slot_count,
        "unique_key_count": unique_key_count,
        "same_entry_rewrite_count": same_entry_rewrite_count,
        "same_cacheline_rewrite_count": same_cacheline_rewrite_count,
        "back_to_back_same_entry_write_count": back_to_back_same_entry_write_count,
        "clear_then_overwrite_same_entry_count": clear_then_overwrite_same_entry_count,
        "overwrite_then_insert_same_entry_count": overwrite_then_insert_same_entry_count,
        "insert_then_clear_same_entry_count": insert_then_clear_same_entry_count,
        "clear_then_overwrite_same_entry_share": share(
            clear_then_overwrite_same_entry_count, overwrite_count
        ),
    }


def dominant_terminal_span_label(first_half_seconds, second_half_seconds):
    if first_half_seconds is None or second_half_seconds is None:
        return "unknown"
    if first_half_seconds >= second_half_seconds:
        return "first_half"
    return "second_half"


def dominant_terminal_first_half_span_label(span_a_seconds, span_b_seconds):
    if span_a_seconds is None or span_b_seconds is None:
        return "unknown"
    if span_a_seconds >= span_b_seconds:
        return "span_a"
    return "span_b"


def dominant_state_update_child(
    heap_build_seconds,
    heap_update_seconds,
    start_index_rebuild_seconds,
    trace_or_profile_bookkeeping_seconds,
):
    values = {
        "heap_build": heap_build_seconds or 0.0,
        "heap_update": heap_update_seconds or 0.0,
        "start_index_rebuild": start_index_rebuild_seconds or 0.0,
        "trace_or_profile_bookkeeping": trace_or_profile_bookkeeping_seconds or 0.0,
    }
    best_value = max(values.values())
    if best_value <= 0.0:
        return "unknown"
    winners = [name for name, value in values.items() if abs(value - best_value) <= 1e-12]
    if len(winners) != 1:
        return "unknown"
    return winners[0]


def dominant_production_state_update_child(
    benchmark_counter_seconds,
    trace_replay_required_state_seconds,
):
    values = {
        "benchmark_counter": benchmark_counter_seconds or 0.0,
        "trace_replay_required_state": trace_replay_required_state_seconds or 0.0,
    }
    best_value = max(values.values())
    if best_value <= 0.0:
        return "unknown"
    winners = [name for name, value in values.items() if abs(value - best_value) <= 1e-12]
    if len(winners) != 1:
        return "unknown"
    return winners[0]


def dominant_production_state_update_child_with_mixed(values):
    best_value = max(values.values())
    if best_value <= 0.0:
        return "unknown"
    winners = [name for name, value in values.items() if abs(value - best_value) <= 1e-12]
    if len(winners) == 1:
        return winners[0]
    return "mixed"


def production_state_update_child_margin_share(
    benchmark_counter_seconds,
    trace_replay_required_state_seconds,
    parent_seconds,
):
    values = sorted(
        [benchmark_counter_seconds or 0.0, trace_replay_required_state_seconds or 0.0],
        reverse=True,
    )
    if len(values) < 2 or parent_seconds is None or parent_seconds <= 0.0:
        return 0.0
    return share(max(values[0] - values[1], 0.0), parent_seconds)


def classify_production_state_update_dominance(
    *,
    case_weighted_dominant_child,
    seconds_weighted_dominant_child,
    child_margin_share,
    child_margin_threshold,
):
    known_children = {"benchmark_counter", "trace_replay_required_state"}
    if (
        case_weighted_dominant_child in known_children
        and seconds_weighted_dominant_child in known_children
        and case_weighted_dominant_child != seconds_weighted_dominant_child
    ):
        return "case_weighted_aggregate_conflict"
    if child_margin_share < child_margin_threshold:
        return "near_tie"
    if seconds_weighted_dominant_child in known_children:
        return "stable"
    return "unknown"


def aggregate_production_state_update_case_dominance(rows):
    counts = {"benchmark_counter": 0, "trace_replay_required_state": 0}
    event_weights = {"benchmark_counter": 0, "trace_replay_required_state": 0}
    total_cases = len(rows)
    for row in rows:
        dominant_child = dominant_production_state_update_child(
            row.get("production_state_update_benchmark_counter_seconds", 0.0),
            row.get("production_state_update_trace_replay_required_state_seconds", 0.0),
        )
        if dominant_child in counts:
            counts[dominant_child] += 1
        event_weights["benchmark_counter"] += int(
            row.get("production_state_update_benchmark_counter_sampled_event_count", 0) or 0
        )
        event_weights["trace_replay_required_state"] += int(
            row.get(
                "production_state_update_trace_replay_required_state_sampled_event_count",
                0,
            )
            or 0
        )

    best_case_count = max(counts.values()) if counts else 0
    if best_case_count <= 0:
        case_weighted_dominant_child = "unknown"
    else:
        case_winners = [
            label for label, value in counts.items() if value == best_case_count and value > 0
        ]
        if len(case_winners) == 1:
            case_weighted_dominant_child = case_winners[0]
        else:
            case_weighted_dominant_child = "mixed"

    case_majority_share = share(best_case_count, total_cases) if total_cases > 0 else 0.0
    event_weighted_dominant_child = dominant_production_state_update_child_with_mixed(
        event_weights
    )
    return {
        "case_weighted_dominant_child": case_weighted_dominant_child,
        "case_majority_share": case_majority_share,
        "event_weighted_dominant_child": event_weighted_dominant_child,
    }


def derive_terminal_path_state_update_metrics(
    *,
    fallback_parent_seconds,
    split_parent_seconds=None,
    heap_build_seconds=None,
    heap_update_seconds=None,
    start_index_rebuild_seconds=None,
    trace_or_profile_bookkeeping_seconds=None,
    child_known_seconds=None,
    unexplained_seconds=None,
    sampled_event_count=None,
    covered_sampled_event_count=None,
    unclassified_sampled_event_count=None,
    multi_child_sampled_event_count=None,
    heap_build_sampled_event_count=None,
    heap_update_sampled_event_count=None,
    start_index_rebuild_sampled_event_count=None,
    trace_or_profile_bookkeeping_sampled_event_count=None,
    event_count=None,
    heap_build_count=None,
    heap_update_count=None,
    start_index_rebuild_count=None,
    trace_or_profile_bookkeeping_count=None,
    aux_updates_total=None,
    coverage_source=None,
    unexplained_share_threshold=0.10,
):
    split_present = any(
        value is not None
        for value in (
            split_parent_seconds,
            heap_build_seconds,
            heap_update_seconds,
            start_index_rebuild_seconds,
            trace_or_profile_bookkeeping_seconds,
            child_known_seconds,
            unexplained_seconds,
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
            multi_child_sampled_event_count,
            heap_build_sampled_event_count,
            heap_update_sampled_event_count,
            start_index_rebuild_sampled_event_count,
            trace_or_profile_bookkeeping_sampled_event_count,
            event_count,
            heap_build_count,
            heap_update_count,
            start_index_rebuild_count,
            trace_or_profile_bookkeeping_count,
            aux_updates_total,
        )
    )

    parent_seconds = (
        split_parent_seconds if split_parent_seconds is not None else fallback_parent_seconds
    )
    if parent_seconds is None:
        parent_seconds = 0.0

    if split_present:
        heap_build_seconds = heap_build_seconds or 0.0
        heap_update_seconds = heap_update_seconds or 0.0
        start_index_rebuild_seconds = start_index_rebuild_seconds or 0.0
        trace_or_profile_bookkeeping_seconds = (
            trace_or_profile_bookkeeping_seconds or 0.0
        )
        child_known_seconds = (
            child_known_seconds
            if child_known_seconds is not None
            else (
                heap_build_seconds
                + heap_update_seconds
                + start_index_rebuild_seconds
                + trace_or_profile_bookkeeping_seconds
            )
        )
        unexplained_seconds = (
            unexplained_seconds
            if unexplained_seconds is not None
            else max(parent_seconds - child_known_seconds, 0.0)
        )
    else:
        heap_build_seconds = 0.0
        heap_update_seconds = 0.0
        start_index_rebuild_seconds = 0.0
        trace_or_profile_bookkeeping_seconds = 0.0
        child_known_seconds = 0.0
        unexplained_seconds = max(parent_seconds, 0.0)

    sampled_event_count = sampled_event_count or 0
    covered_sampled_event_count = covered_sampled_event_count or 0
    unclassified_sampled_event_count = unclassified_sampled_event_count or 0
    multi_child_sampled_event_count = multi_child_sampled_event_count or 0
    heap_build_sampled_event_count = heap_build_sampled_event_count or 0
    heap_update_sampled_event_count = heap_update_sampled_event_count or 0
    start_index_rebuild_sampled_event_count = start_index_rebuild_sampled_event_count or 0
    trace_or_profile_bookkeeping_sampled_event_count = (
        trace_or_profile_bookkeeping_sampled_event_count or 0
    )
    event_count = event_count or 0
    heap_build_count = heap_build_count or 0
    heap_update_count = heap_update_count or 0
    start_index_rebuild_count = start_index_rebuild_count or 0
    trace_or_profile_bookkeeping_count = trace_or_profile_bookkeeping_count or 0
    aux_updates_total = aux_updates_total or 0

    sampled_count_closure_status = (
        classify_sampled_count_closure_status(
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
        )
        if split_present
        else "unknown"
    )
    normalized_coverage_source = (
        "event_level_sampled"
        if split_present and coverage_source == "event_level_sampled"
        else "placeholder"
    )
    unexplained_share = share(unexplained_seconds, parent_seconds)
    if normalized_coverage_source != "event_level_sampled":
        timer_scope_status = "missing_event_level_coverage"
    elif (
        sampled_count_closure_status != "closed"
        or unexplained_share >= unexplained_share_threshold
    ):
        timer_scope_status = "open"
    else:
        timer_scope_status = "closed"

    dominant_child = dominant_state_update_child(
        heap_build_seconds,
        heap_update_seconds,
        start_index_rebuild_seconds,
        trace_or_profile_bookkeeping_seconds,
    )

    return {
        "parent_seconds": parent_seconds,
        "heap_build_seconds": heap_build_seconds,
        "heap_update_seconds": heap_update_seconds,
        "start_index_rebuild_seconds": start_index_rebuild_seconds,
        "trace_or_profile_bookkeeping_seconds": trace_or_profile_bookkeeping_seconds,
        "child_known_seconds": child_known_seconds,
        "unexplained_seconds": unexplained_seconds,
        "unexplained_share": unexplained_share,
        "sampled_event_count": sampled_event_count,
        "covered_sampled_event_count": covered_sampled_event_count,
        "unclassified_sampled_event_count": unclassified_sampled_event_count,
        "multi_child_sampled_event_count": multi_child_sampled_event_count,
        "heap_build_sampled_event_count": heap_build_sampled_event_count,
        "heap_update_sampled_event_count": heap_update_sampled_event_count,
        "start_index_rebuild_sampled_event_count": start_index_rebuild_sampled_event_count,
        "trace_or_profile_bookkeeping_sampled_event_count": (
            trace_or_profile_bookkeeping_sampled_event_count
        ),
        "sampled_count_closure_status": sampled_count_closure_status,
        "coverage_source": normalized_coverage_source,
        "timer_scope_status": timer_scope_status,
        "dominant_child": dominant_child,
        "coverage_share": share(covered_sampled_event_count, sampled_event_count),
        "unclassified_share": share(unclassified_sampled_event_count, sampled_event_count),
        "multi_child_share": share(multi_child_sampled_event_count, sampled_event_count),
        "heap_build_share": share(heap_build_seconds, parent_seconds),
        "heap_update_share": share(heap_update_seconds, parent_seconds),
        "start_index_rebuild_share": share(start_index_rebuild_seconds, parent_seconds),
        "trace_or_profile_bookkeeping_share": share(
            trace_or_profile_bookkeeping_seconds, parent_seconds
        ),
        "event_count": event_count,
        "heap_build_count": heap_build_count,
        "heap_update_count": heap_update_count,
        "start_index_rebuild_count": start_index_rebuild_count,
        "trace_or_profile_bookkeeping_count": trace_or_profile_bookkeeping_count,
        "aux_updates_total": aux_updates_total,
    }


def derive_production_state_update_metrics(
    *,
    fallback_parent_seconds,
    split_parent_seconds=None,
    benchmark_counter_seconds=None,
    trace_replay_required_state_seconds=None,
    child_known_seconds=None,
    unexplained_seconds=None,
    sampled_event_count=None,
    covered_sampled_event_count=None,
    unclassified_sampled_event_count=None,
    multi_child_sampled_event_count=None,
    benchmark_counter_sampled_event_count=None,
    trace_replay_required_state_sampled_event_count=None,
    event_count=None,
    benchmark_counter_count=None,
    trace_replay_required_state_count=None,
    coverage_source=None,
    unexplained_share_threshold=0.10,
):
    split_present = any(
        value is not None
        for value in (
            split_parent_seconds,
            benchmark_counter_seconds,
            trace_replay_required_state_seconds,
            child_known_seconds,
            unexplained_seconds,
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
            multi_child_sampled_event_count,
            benchmark_counter_sampled_event_count,
            trace_replay_required_state_sampled_event_count,
            event_count,
            benchmark_counter_count,
            trace_replay_required_state_count,
        )
    )

    parent_seconds = (
        split_parent_seconds if split_parent_seconds is not None else fallback_parent_seconds
    )
    if parent_seconds is None:
        parent_seconds = 0.0

    if split_present:
        benchmark_counter_seconds = benchmark_counter_seconds or 0.0
        trace_replay_required_state_seconds = trace_replay_required_state_seconds or 0.0
        child_known_seconds = (
            child_known_seconds
            if child_known_seconds is not None
            else (benchmark_counter_seconds + trace_replay_required_state_seconds)
        )
        unexplained_seconds = (
            unexplained_seconds
            if unexplained_seconds is not None
            else max(parent_seconds - child_known_seconds, 0.0)
        )
    else:
        benchmark_counter_seconds = 0.0
        trace_replay_required_state_seconds = 0.0
        child_known_seconds = 0.0
        unexplained_seconds = max(parent_seconds, 0.0)

    sampled_event_count = sampled_event_count or 0
    covered_sampled_event_count = covered_sampled_event_count or 0
    unclassified_sampled_event_count = unclassified_sampled_event_count or 0
    multi_child_sampled_event_count = multi_child_sampled_event_count or 0
    benchmark_counter_sampled_event_count = benchmark_counter_sampled_event_count or 0
    trace_replay_required_state_sampled_event_count = (
        trace_replay_required_state_sampled_event_count or 0
    )
    event_count = event_count or 0
    benchmark_counter_count = benchmark_counter_count or 0
    trace_replay_required_state_count = trace_replay_required_state_count or 0

    sampled_count_closure_status = (
        classify_sampled_count_closure_status(
            sampled_event_count,
            covered_sampled_event_count,
            unclassified_sampled_event_count,
        )
        if split_present
        else "unknown"
    )
    normalized_coverage_source = (
        "event_level_sampled"
        if split_present and coverage_source == "event_level_sampled"
        else "placeholder"
    )
    unexplained_share = share(unexplained_seconds, parent_seconds)
    if normalized_coverage_source != "event_level_sampled":
        timer_scope_status = "missing_event_level_coverage"
    elif (
        sampled_count_closure_status != "closed"
        or unexplained_share >= unexplained_share_threshold
    ):
        timer_scope_status = "open"
    else:
        timer_scope_status = "closed"

    dominant_child = dominant_production_state_update_child(
        benchmark_counter_seconds,
        trace_replay_required_state_seconds,
    )

    return {
        "parent_seconds": parent_seconds,
        "benchmark_counter_seconds": benchmark_counter_seconds,
        "trace_replay_required_state_seconds": trace_replay_required_state_seconds,
        "child_known_seconds": child_known_seconds,
        "unexplained_seconds": unexplained_seconds,
        "unexplained_share": unexplained_share,
        "sampled_event_count": sampled_event_count,
        "covered_sampled_event_count": covered_sampled_event_count,
        "unclassified_sampled_event_count": unclassified_sampled_event_count,
        "multi_child_sampled_event_count": multi_child_sampled_event_count,
        "benchmark_counter_sampled_event_count": benchmark_counter_sampled_event_count,
        "trace_replay_required_state_sampled_event_count": (
            trace_replay_required_state_sampled_event_count
        ),
        "sampled_count_closure_status": sampled_count_closure_status,
        "coverage_source": normalized_coverage_source,
        "timer_scope_status": timer_scope_status,
        "dominant_child": dominant_child,
        "coverage_share": share(covered_sampled_event_count, sampled_event_count),
        "unclassified_share": share(unclassified_sampled_event_count, sampled_event_count),
        "multi_child_share": share(multi_child_sampled_event_count, sampled_event_count),
        "benchmark_counter_share": share(benchmark_counter_seconds, parent_seconds),
        "trace_replay_required_state_share": share(
            trace_replay_required_state_seconds, parent_seconds
        ),
        "event_count": event_count,
        "benchmark_counter_count": benchmark_counter_count,
        "trace_replay_required_state_count": trace_replay_required_state_count,
    }


def classify_timer_closure_status(parent_seconds, child_known_seconds, threshold):
    if parent_seconds is None or child_known_seconds is None or parent_seconds <= 0.0:
        return "unknown"
    gap_ratio = abs(child_known_seconds - parent_seconds) / parent_seconds
    if gap_ratio <= threshold:
        return "closed"
    return "residual_unexplained"


def classify_intra_profile_closure_status(
    lexical_parent_seconds,
    first_half_seconds,
    second_half_seconds,
):
    if (
        lexical_parent_seconds is None
        or first_half_seconds is None
        or second_half_seconds is None
        or lexical_parent_seconds <= 0.0
    ):
        return "unknown"
    accounted_ratio = (first_half_seconds + second_half_seconds) / lexical_parent_seconds
    if 0.90 <= accounted_ratio <= 1.10:
        return "ok"
    return "residual_unexplained"


def classify_profile_mode_overhead_status(
    intra_profile_closure_status,
    profile_mode_ratio_vs_coarse=None,
):
    if profile_mode_ratio_vs_coarse is not None:
        if profile_mode_ratio_vs_coarse > 1.10:
            return "suspect"
        return "ok"
    if intra_profile_closure_status == "unknown":
        return "unknown"
    if intra_profile_closure_status != "ok":
        return "unknown"
    return "needs_coarse_vs_lexical_ab"


def classify_candidate_index_materiality_status(
    initial_cpu_merge_share_of_sim_seconds,
    candidate_index_share_of_sim_seconds,
    *,
    host_merge_materiality_threshold,
    candidate_index_materiality_threshold,
):
    if (
        initial_cpu_merge_share_of_sim_seconds is None
        or candidate_index_share_of_sim_seconds is None
    ):
        return "unknown"
    if (
        initial_cpu_merge_share_of_sim_seconds >= host_merge_materiality_threshold
        and candidate_index_share_of_sim_seconds >= candidate_index_materiality_threshold
    ):
        return "material"
    return "immaterial"


def derive_terminal_path_metrics(
    row,
    *,
    candidate_index_seconds,
    state_update_unexplained_threshold,
    full_set_miss_count,
    lookup_miss_reuse_writeback_key_rebind_seconds,
    lookup_miss_reuse_writeback_candidate_copy_seconds,
    lookup_miss_reuse_writeback_aux_bookkeeping_seconds,
    lookup_miss_reuse_writeback_aux_heap_build_seconds,
    lookup_miss_reuse_writeback_aux_heap_update_seconds,
    lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds,
    lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds,
    lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds,
    lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds,
    lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds,
    lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds,
    lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds,
    lookup_miss_reuse_writeback_aux_other_residual_residual_seconds,
):
    production_state_update_unexplained_threshold = max(
        state_update_unexplained_threshold, 0.50
    )
    terminal_parent_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_parent_mean_seconds",)
    )

    terminal_candidate_slot_write_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_mean_seconds",)
    )
    if terminal_candidate_slot_write_seconds is None:
        terminal_candidate_slot_write_seconds = (
            lookup_miss_reuse_writeback_candidate_copy_seconds
        )

    terminal_start_index_write_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_mean_seconds",)
    )
    if terminal_start_index_write_seconds is None:
        terminal_start_index_write_seconds = lookup_miss_reuse_writeback_key_rebind_seconds

    start_index_write_metrics = derive_start_index_write_metrics(
        candidate_index_seconds=candidate_index_seconds,
        fallback_parent_seconds=terminal_start_index_write_seconds,
        split_parent_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_mean_seconds",),
        ),
        left_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_mean_seconds",),
        ),
        right_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_mean_seconds",),
        ),
        child_known_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_mean_seconds",),
        ),
        unexplained_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_mean_seconds",),
        ),
        sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_sampled_event_count",),
        ),
        covered_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_covered_sampled_event_count",
            ),
        ),
        unclassified_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unclassified_sampled_event_count",
            ),
        ),
        multi_child_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_multi_child_sampled_event_count",
            ),
        ),
        left_sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_sampled_event_count",),
        ),
        right_sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_sampled_event_count",),
        ),
        insert_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_insert_count",),
        ),
        update_existing_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_update_existing_count",),
        ),
        clear_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_clear_count",),
        ),
        overwrite_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_overwrite_count",),
        ),
        idempotent_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_idempotent_count",),
        ),
        value_changed_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_value_changed_count",),
        ),
        probe_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_count",),
        ),
        probe_steps_total=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_steps_total",),
        ),
    )
    terminal_start_index_write_seconds = start_index_write_metrics["parent_seconds"]
    start_index_store_metrics = derive_start_index_store_metrics(
        fallback_parent_seconds=start_index_write_metrics["right_seconds"],
        split_parent_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_mean_seconds",),
        ),
        insert_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_mean_seconds",),
        ),
        clear_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_mean_seconds",),
        ),
        overwrite_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_mean_seconds",),
        ),
        child_known_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_mean_seconds",),
        ),
        unexplained_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_mean_seconds",),
        ),
        sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_sampled_event_count",),
        ),
        covered_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_covered_sampled_event_count",
            ),
        ),
        unclassified_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unclassified_sampled_event_count",
            ),
        ),
        multi_child_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_multi_child_sampled_event_count",
            ),
        ),
        insert_sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_sampled_event_count",),
        ),
        clear_sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_sampled_event_count",),
        ),
        overwrite_sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_sampled_event_count",),
        ),
        insert_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_count",),
        ),
        clear_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_count",),
        ),
        overwrite_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_count",),
        ),
        insert_bytes=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_bytes",),
        ),
        clear_bytes=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_bytes",),
        ),
        overwrite_bytes=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_bytes",),
        ),
        unique_entry_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_entry_count",),
        ),
        unique_slot_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_slot_count",),
        ),
        unique_key_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_key_count",),
        ),
        same_entry_rewrite_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_entry_rewrite_count",),
        ),
        same_cacheline_rewrite_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_cacheline_rewrite_count",),
        ),
        back_to_back_same_entry_write_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_back_to_back_same_entry_write_count",
            ),
        ),
        clear_then_overwrite_same_entry_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_then_overwrite_same_entry_count",
            ),
        ),
        overwrite_then_insert_same_entry_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_then_insert_same_entry_count",
            ),
        ),
        insert_then_clear_same_entry_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_then_clear_same_entry_count",
            ),
        ),
    )

    terminal_state_update_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_mean_seconds",)
    )
    if terminal_state_update_seconds is None:
        terminal_state_update_seconds = (
            lookup_miss_reuse_writeback_aux_heap_build_seconds
            + lookup_miss_reuse_writeback_aux_heap_update_seconds
            + lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds
        )
    state_update_metrics = derive_terminal_path_state_update_metrics(
        fallback_parent_seconds=terminal_state_update_seconds,
        split_parent_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_mean_seconds",),
        ),
        heap_build_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_mean_seconds",),
        )
        if resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_mean_seconds",),
        )
        is not None
        else lookup_miss_reuse_writeback_aux_heap_build_seconds,
        heap_update_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_mean_seconds",),
        )
        if resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_mean_seconds",),
        )
        is not None
        else lookup_miss_reuse_writeback_aux_heap_update_seconds,
        start_index_rebuild_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_mean_seconds",
            ),
        )
        if resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_mean_seconds",
            ),
        )
        is not None
        else lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds,
        trace_or_profile_bookkeeping_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_mean_seconds",
            ),
        ),
        child_known_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_mean_seconds",),
        ),
        unexplained_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_mean_seconds",),
        ),
        sampled_event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count",),
        ),
        covered_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count",
            ),
        ),
        unclassified_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count",
            ),
        ),
        multi_child_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_multi_child_sampled_event_count",
            ),
        ),
        heap_build_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_sampled_event_count",
            ),
        ),
        heap_update_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count",
            ),
        ),
        start_index_rebuild_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_sampled_event_count",
            ),
        ),
        trace_or_profile_bookkeeping_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_sampled_event_count",
            ),
        ),
        event_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_event_count",),
        ),
        heap_build_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_count",),
        ),
        heap_update_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_count",),
        ),
        start_index_rebuild_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_count",
            ),
        ),
        trace_or_profile_bookkeeping_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_count",
            ),
        ),
        aux_updates_total=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_aux_updates_total",),
        ),
        coverage_source=resolve_optional_text(
            row,
            "context_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source",
        ),
        unexplained_share_threshold=state_update_unexplained_threshold,
    )
    production_state_update_metrics = derive_production_state_update_metrics(
        fallback_parent_seconds=state_update_metrics[
            "trace_or_profile_bookkeeping_seconds"
        ],
        split_parent_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_mean_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_mean_seconds",
            ),
        ),
        benchmark_counter_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_mean_seconds",
            ),
        ),
        trace_replay_required_state_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_mean_seconds",
            ),
        ),
        child_known_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_mean_seconds",
            ),
        ),
        unexplained_seconds=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_mean_seconds",
            ),
        ),
        sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_sampled_event_count",
            ),
        ),
        covered_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_covered_sampled_event_count",
            ),
        ),
        unclassified_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unclassified_sampled_event_count",
            ),
        ),
        multi_child_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_multi_child_sampled_event_count",
            ),
        ),
        benchmark_counter_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_sampled_event_count",
            ),
        ),
        trace_replay_required_state_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_sampled_event_count",
            ),
        ),
        event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_event_count",
            ),
        ),
        benchmark_counter_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_count",
            ),
        ),
        trace_replay_required_state_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_count",
            ),
        ),
        coverage_source=resolve_optional_text(
            row,
            "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_coverage_source",
        ),
        unexplained_share_threshold=production_state_update_unexplained_threshold,
    )

    terminal_telemetry_overhead_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_mean_seconds",)
    )
    if terminal_telemetry_overhead_seconds is None:
        terminal_telemetry_overhead_seconds = (
            lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds
        )

    terminal_residual_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_residual_mean_seconds",)
    )
    if terminal_residual_seconds is None:
        terminal_residual_seconds = lookup_miss_reuse_writeback_aux_other_residual_residual_seconds

    if terminal_parent_seconds is None:
        terminal_parent_seconds = (
            terminal_candidate_slot_write_seconds
            + terminal_start_index_write_seconds
            + lookup_miss_reuse_writeback_aux_bookkeeping_seconds
        )

    terminal_child_known_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_child_known_mean_seconds",)
    )
    if terminal_child_known_seconds is None:
        terminal_child_known_seconds = (
            terminal_candidate_slot_write_seconds
            + terminal_start_index_write_seconds
            + terminal_state_update_seconds
            + terminal_telemetry_overhead_seconds
            + terminal_residual_seconds
        )

    terminal_event_count = resolve_optional_int(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_event_count",)
    )
    if terminal_event_count is None:
        terminal_event_count = full_set_miss_count

    terminal_candidate_slot_write_count = resolve_optional_int(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_count",)
    )
    if terminal_candidate_slot_write_count is None:
        terminal_candidate_slot_write_count = full_set_miss_count

    terminal_start_index_write_count = resolve_optional_int(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_count",)
    )
    if terminal_start_index_write_count is None:
        terminal_start_index_write_count = full_set_miss_count

    terminal_state_update_count = resolve_optional_int(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_state_update_count",)
    )
    if terminal_state_update_count is None:
        terminal_state_update_count = 0

    terminal_candidate_bytes_written = resolve_optional_int(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_candidate_bytes_written",)
    )
    if terminal_candidate_bytes_written is None:
        terminal_candidate_bytes_written = full_set_miss_count * SIM_CANDIDATE_BYTES

    terminal_start_index_bytes_written = resolve_optional_int(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_start_index_bytes_written",)
    )
    if terminal_start_index_bytes_written is None:
        terminal_start_index_bytes_written = (
            full_set_miss_count * SIM_CANDIDATE_START_INDEX_ENTRY_BYTES
        )

    terminal_child_values = {
        "candidate_slot_write": terminal_candidate_slot_write_seconds,
        "start_index_write": terminal_start_index_write_seconds,
        "state_update": terminal_state_update_seconds,
        "telemetry_overhead": terminal_telemetry_overhead_seconds,
        "residual": terminal_residual_seconds,
    }

    return {
        "scope": TERMINAL_PATH_SCOPE,
        "parent_seconds": terminal_parent_seconds,
        "child_known_seconds": terminal_child_known_seconds,
        "candidate_slot_write_seconds": terminal_candidate_slot_write_seconds,
        "start_index_write_seconds": terminal_start_index_write_seconds,
        "state_update_seconds": terminal_state_update_seconds,
        "telemetry_overhead_seconds": terminal_telemetry_overhead_seconds,
        "residual_seconds": terminal_residual_seconds,
        "candidate_slot_write_share_of_candidate_index": share(
            terminal_candidate_slot_write_seconds, candidate_index_seconds
        ),
        "start_index_write_share_of_candidate_index": share(
            terminal_start_index_write_seconds, candidate_index_seconds
        ),
        "state_update_share_of_candidate_index": share(
            terminal_state_update_seconds, candidate_index_seconds
        ),
        "state_update_parent_seconds": state_update_metrics["parent_seconds"],
        "state_update_heap_build_seconds": state_update_metrics["heap_build_seconds"],
        "state_update_heap_update_seconds": state_update_metrics["heap_update_seconds"],
        "state_update_start_index_rebuild_seconds": state_update_metrics[
            "start_index_rebuild_seconds"
        ],
        "state_update_trace_or_profile_bookkeeping_seconds": state_update_metrics[
            "trace_or_profile_bookkeeping_seconds"
        ],
        "state_update_child_known_seconds": state_update_metrics["child_known_seconds"],
        "state_update_unexplained_seconds": state_update_metrics["unexplained_seconds"],
        "state_update_unexplained_share": state_update_metrics["unexplained_share"],
        "state_update_sampled_event_count": state_update_metrics["sampled_event_count"],
        "state_update_covered_sampled_event_count": state_update_metrics[
            "covered_sampled_event_count"
        ],
        "state_update_unclassified_sampled_event_count": state_update_metrics[
            "unclassified_sampled_event_count"
        ],
        "state_update_multi_child_sampled_event_count": state_update_metrics[
            "multi_child_sampled_event_count"
        ],
        "state_update_heap_build_sampled_event_count": state_update_metrics[
            "heap_build_sampled_event_count"
        ],
        "state_update_heap_update_sampled_event_count": state_update_metrics[
            "heap_update_sampled_event_count"
        ],
        "state_update_start_index_rebuild_sampled_event_count": state_update_metrics[
            "start_index_rebuild_sampled_event_count"
        ],
        "state_update_trace_or_profile_bookkeeping_sampled_event_count": (
            state_update_metrics["trace_or_profile_bookkeeping_sampled_event_count"]
        ),
        "state_update_sampled_count_closure_status": state_update_metrics[
            "sampled_count_closure_status"
        ],
        "state_update_coverage_source": state_update_metrics["coverage_source"],
        "state_update_timer_scope_status": state_update_metrics["timer_scope_status"],
        "state_update_dominant_child": state_update_metrics["dominant_child"],
        "state_update_coverage_share": state_update_metrics["coverage_share"],
        "state_update_unclassified_share": state_update_metrics["unclassified_share"],
        "state_update_multi_child_share": state_update_metrics["multi_child_share"],
        "state_update_heap_build_share": state_update_metrics["heap_build_share"],
        "state_update_heap_update_share": state_update_metrics["heap_update_share"],
        "state_update_start_index_rebuild_share": state_update_metrics[
            "start_index_rebuild_share"
        ],
        "state_update_trace_or_profile_bookkeeping_share": state_update_metrics[
            "trace_or_profile_bookkeeping_share"
        ],
        "telemetry_overhead_share_of_candidate_index": share(
            terminal_telemetry_overhead_seconds, candidate_index_seconds
        ),
        "residual_share_of_candidate_index": share(
            terminal_residual_seconds, candidate_index_seconds
        ),
        "event_count": terminal_event_count,
        "candidate_slot_write_count": terminal_candidate_slot_write_count,
        "start_index_write_count": terminal_start_index_write_count,
        "state_update_count": terminal_state_update_count,
        "state_update_event_count": state_update_metrics["event_count"],
        "state_update_heap_build_count": state_update_metrics["heap_build_count"],
        "state_update_heap_update_count": state_update_metrics["heap_update_count"],
        "state_update_start_index_rebuild_count": state_update_metrics[
            "start_index_rebuild_count"
        ],
        "state_update_trace_or_profile_bookkeeping_count": state_update_metrics[
            "trace_or_profile_bookkeeping_count"
        ],
        "state_update_aux_updates_total": state_update_metrics["aux_updates_total"],
        "production_state_update_parent_seconds": production_state_update_metrics[
            "parent_seconds"
        ],
        "production_state_update_benchmark_counter_seconds": (
            production_state_update_metrics["benchmark_counter_seconds"]
        ),
        "production_state_update_trace_replay_required_state_seconds": (
            production_state_update_metrics["trace_replay_required_state_seconds"]
        ),
        "production_state_update_child_known_seconds": production_state_update_metrics[
            "child_known_seconds"
        ],
        "production_state_update_unexplained_seconds": (
            production_state_update_metrics["unexplained_seconds"]
        ),
        "production_state_update_unexplained_share": production_state_update_metrics[
            "unexplained_share"
        ],
        "production_state_update_sampled_event_count": production_state_update_metrics[
            "sampled_event_count"
        ],
        "production_state_update_covered_sampled_event_count": (
            production_state_update_metrics["covered_sampled_event_count"]
        ),
        "production_state_update_unclassified_sampled_event_count": (
            production_state_update_metrics["unclassified_sampled_event_count"]
        ),
        "production_state_update_multi_child_sampled_event_count": (
            production_state_update_metrics["multi_child_sampled_event_count"]
        ),
        "production_state_update_benchmark_counter_sampled_event_count": (
            production_state_update_metrics["benchmark_counter_sampled_event_count"]
        ),
        "production_state_update_trace_replay_required_state_sampled_event_count": (
            production_state_update_metrics[
                "trace_replay_required_state_sampled_event_count"
            ]
        ),
        "production_state_update_sampled_count_closure_status": (
            production_state_update_metrics["sampled_count_closure_status"]
        ),
        "production_state_update_coverage_source": production_state_update_metrics[
            "coverage_source"
        ],
        "production_state_update_timer_scope_status": production_state_update_metrics[
            "timer_scope_status"
        ],
        "production_state_update_dominant_child": production_state_update_metrics[
            "dominant_child"
        ],
        "production_state_update_coverage_share": production_state_update_metrics[
            "coverage_share"
        ],
        "production_state_update_unclassified_share": (
            production_state_update_metrics["unclassified_share"]
        ),
        "production_state_update_multi_child_share": production_state_update_metrics[
            "multi_child_share"
        ],
        "production_state_update_benchmark_counter_share": (
            production_state_update_metrics["benchmark_counter_share"]
        ),
        "production_state_update_trace_replay_required_state_share": (
            production_state_update_metrics["trace_replay_required_state_share"]
        ),
        "production_state_update_share_of_candidate_index": share(
            production_state_update_metrics["parent_seconds"], candidate_index_seconds
        ),
        "production_state_update_event_count": production_state_update_metrics[
            "event_count"
        ],
        "production_state_update_benchmark_counter_count": (
            production_state_update_metrics["benchmark_counter_count"]
        ),
        "production_state_update_trace_replay_required_state_count": (
            production_state_update_metrics["trace_replay_required_state_count"]
        ),
        "candidate_bytes_written": terminal_candidate_bytes_written,
        "start_index_bytes_written": terminal_start_index_bytes_written,
        "dominant_child": dominant_terminal_child(terminal_child_values),
        "start_index_write_parent_seconds": start_index_write_metrics["parent_seconds"],
        "start_index_write_left_seconds": start_index_write_metrics["left_seconds"],
        "start_index_write_right_seconds": start_index_write_metrics["right_seconds"],
        "start_index_write_child_known_seconds": start_index_write_metrics[
            "child_known_seconds"
        ],
        "start_index_write_unexplained_seconds": start_index_write_metrics[
            "unexplained_seconds"
        ],
        "start_index_write_unexplained_share": start_index_write_metrics[
            "unexplained_share"
        ],
        "start_index_write_sampled_event_count": start_index_write_metrics[
            "sampled_event_count"
        ],
        "start_index_write_covered_sampled_event_count": start_index_write_metrics[
            "covered_sampled_event_count"
        ],
        "start_index_write_unclassified_sampled_event_count": start_index_write_metrics[
            "unclassified_sampled_event_count"
        ],
        "start_index_write_multi_child_sampled_event_count": start_index_write_metrics[
            "multi_child_sampled_event_count"
        ],
        "start_index_write_left_sampled_event_count": start_index_write_metrics[
            "left_sampled_event_count"
        ],
        "start_index_write_right_sampled_event_count": start_index_write_metrics[
            "right_sampled_event_count"
        ],
        "start_index_write_sampled_count_closure_status": start_index_write_metrics[
            "sampled_count_closure_status"
        ],
        "start_index_write_dominant_child": start_index_write_metrics["dominant_child"],
        "start_index_write_coverage_share": start_index_write_metrics["coverage_share"],
        "start_index_write_unclassified_share": start_index_write_metrics[
            "unclassified_share"
        ],
        "start_index_write_multi_child_share": start_index_write_metrics[
            "multi_child_share"
        ],
        "start_index_write_probe_or_locate_share": start_index_write_metrics[
            "probe_or_locate_share"
        ],
        "start_index_write_entry_store_share": start_index_write_metrics[
            "entry_store_share"
        ],
        "start_index_write_insert_count": start_index_write_metrics["insert_count"],
        "start_index_write_update_existing_count": start_index_write_metrics[
            "update_existing_count"
        ],
        "start_index_write_clear_count": start_index_write_metrics["clear_count"],
        "start_index_write_overwrite_count": start_index_write_metrics[
            "overwrite_count"
        ],
        "start_index_write_idempotent_count": start_index_write_metrics[
            "idempotent_count"
        ],
        "start_index_write_value_changed_count": start_index_write_metrics[
            "value_changed_count"
        ],
        "start_index_write_probe_count": start_index_write_metrics["probe_count"],
        "start_index_write_probe_steps_total": start_index_write_metrics[
            "probe_steps_total"
        ],
        "start_index_store_parent_seconds": start_index_store_metrics["parent_seconds"],
        "start_index_store_insert_seconds": start_index_store_metrics["insert_seconds"],
        "start_index_store_clear_seconds": start_index_store_metrics["clear_seconds"],
        "start_index_store_overwrite_seconds": start_index_store_metrics[
            "overwrite_seconds"
        ],
        "start_index_store_child_known_seconds": start_index_store_metrics[
            "child_known_seconds"
        ],
        "start_index_store_unexplained_seconds": start_index_store_metrics[
            "unexplained_seconds"
        ],
        "start_index_store_unexplained_share": start_index_store_metrics[
            "unexplained_share"
        ],
        "start_index_store_sampled_event_count": start_index_store_metrics[
            "sampled_event_count"
        ],
        "start_index_store_covered_sampled_event_count": start_index_store_metrics[
            "covered_sampled_event_count"
        ],
        "start_index_store_unclassified_sampled_event_count": start_index_store_metrics[
            "unclassified_sampled_event_count"
        ],
        "start_index_store_multi_child_sampled_event_count": start_index_store_metrics[
            "multi_child_sampled_event_count"
        ],
        "start_index_store_insert_sampled_event_count": start_index_store_metrics[
            "insert_sampled_event_count"
        ],
        "start_index_store_clear_sampled_event_count": start_index_store_metrics[
            "clear_sampled_event_count"
        ],
        "start_index_store_overwrite_sampled_event_count": start_index_store_metrics[
            "overwrite_sampled_event_count"
        ],
        "start_index_store_sampled_count_closure_status": start_index_store_metrics[
            "sampled_count_closure_status"
        ],
        "start_index_store_dominant_child": start_index_store_metrics[
            "dominant_child"
        ],
        "start_index_store_coverage_share": start_index_store_metrics[
            "coverage_share"
        ],
        "start_index_store_unclassified_share": start_index_store_metrics[
            "unclassified_share"
        ],
        "start_index_store_multi_child_share": start_index_store_metrics[
            "multi_child_share"
        ],
        "start_index_store_insert_share": start_index_store_metrics["insert_share"],
        "start_index_store_clear_share": start_index_store_metrics["clear_share"],
        "start_index_store_overwrite_share": start_index_store_metrics[
            "overwrite_share"
        ],
        "start_index_store_insert_count": start_index_store_metrics["insert_count"],
        "start_index_store_clear_count": start_index_store_metrics["clear_count"],
        "start_index_store_overwrite_count": start_index_store_metrics[
            "overwrite_count"
        ],
        "start_index_store_insert_bytes": start_index_store_metrics["insert_bytes"],
        "start_index_store_clear_bytes": start_index_store_metrics["clear_bytes"],
        "start_index_store_overwrite_bytes": start_index_store_metrics[
            "overwrite_bytes"
        ],
        "start_index_store_unique_entry_count": start_index_store_metrics[
            "unique_entry_count"
        ],
        "start_index_store_unique_slot_count": start_index_store_metrics[
            "unique_slot_count"
        ],
        "start_index_store_unique_key_count": start_index_store_metrics[
            "unique_key_count"
        ],
        "start_index_store_same_entry_rewrite_count": start_index_store_metrics[
            "same_entry_rewrite_count"
        ],
        "start_index_store_same_cacheline_rewrite_count": start_index_store_metrics[
            "same_cacheline_rewrite_count"
        ],
        "start_index_store_back_to_back_same_entry_write_count": start_index_store_metrics[
            "back_to_back_same_entry_write_count"
        ],
        "start_index_store_clear_then_overwrite_same_entry_count": start_index_store_metrics[
            "clear_then_overwrite_same_entry_count"
        ],
        "start_index_store_overwrite_then_insert_same_entry_count": start_index_store_metrics[
            "overwrite_then_insert_same_entry_count"
        ],
        "start_index_store_insert_then_clear_same_entry_count": start_index_store_metrics[
            "insert_then_clear_same_entry_count"
        ],
        "start_index_store_clear_then_overwrite_same_entry_share": start_index_store_metrics[
            "clear_then_overwrite_same_entry_share"
        ],
    }


def consistent_optional_metric(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return None
    first = values[0]
    for value in values[1:]:
        if abs(value - first) > 1e-12:
            raise LifecycleInputError(f"inconsistent duplicated workload metric: {key}")
    return first


def consistent_optional_text(rows, key):
    values = [row[key] for row in rows if row.get(key) not in {None, ""}]
    if not values:
        return "unknown"
    first = values[0]
    for value in values[1:]:
        if value != first:
            return "mixed"
    return first


def grouped_optional_metric(rows, group_key, metric_key):
    groups = {}
    for row in rows:
        groups.setdefault(row[group_key], []).append(row)
    if not groups:
        return None

    total = 0.0
    for group_rows in groups.values():
        value = consistent_optional_metric(group_rows, metric_key)
        if value is None:
            return None
        total += value
    return total


def validate_positive_optional(value, path, case_id, field):
    if value is not None and value <= 0:
        raise LifecycleInputError(
            f"{path}: case {case_id} has non-positive benchmark metric {field}: {value!r}"
        )


def consistent_group_metric(group_rows, metric_key):
    value = consistent_optional_metric(group_rows, metric_key)
    if value is None:
        raise LifecycleInputError(f"missing grouped workload metric: {metric_key}")
    return value


def evaluate_materiality_pairing(rows):
    groups = {}
    workload_sources = {}
    missing = False

    for row in rows:
        workload_id = row.get("workload_id", "")
        benchmark_source = row.get("benchmark_source", "")
        if not workload_id or not benchmark_source:
            missing = True
        for field in MATERIALITY_BENCHMARK_FIELDS:
            if row.get(field) is None:
                missing = True

        if workload_id:
            previous_source = workload_sources.get(workload_id)
            if previous_source is None:
                workload_sources[workload_id] = benchmark_source
            elif previous_source != benchmark_source:
                return {"status": "mismatched", "groups": {}}

        if workload_id and benchmark_source:
            groups.setdefault((workload_id, benchmark_source), []).append(row)

    if missing:
        return {"status": "missing", "groups": {}}

    try:
        for group_rows in groups.values():
            for field in MATERIALITY_BENCHMARK_FIELDS:
                consistent_group_metric(group_rows, field)
    except LifecycleInputError:
        return {"status": "mismatched", "groups": {}}

    duplicate_grouped = any(len(group_rows) > 1 for group_rows in groups.values())
    return {
        "status": "duplicate_grouped" if duplicate_grouped else "complete",
        "groups": groups,
    }


def grouped_metric_from_pairing(groups, metric_key):
    if not groups:
        return None
    total = 0.0
    for group_rows in groups.values():
        total += consistent_group_metric(group_rows, metric_key)
    return total


def recommended_start_index_store_action(metrics, args):
    if (
        metrics.get("terminal_path_start_index_write_entry_store_share", 0.0)
        < args.start_index_write_child_share_threshold
    ):
        return None
    if metrics.get("terminal_path_start_index_store_sampled_count_closure_status") == "unknown":
        return "profile_start_index_store_path"
    if metrics.get("terminal_path_start_index_store_sampled_count_closure_status") != "closed":
        return "inspect_start_index_store_timer_scope"
    if (
        metrics.get("terminal_path_start_index_store_unexplained_share", 0.0)
        >= args.start_index_store_unexplained_threshold
    ):
        return "inspect_start_index_store_timer_scope"
    if (
        metrics.get(
            "terminal_path_start_index_store_clear_then_overwrite_same_entry_share",
            0.0,
        )
        >= args.start_index_store_clear_overwrite_share_threshold
    ):
        return "profile_start_index_clear_overwrite_write_amplification"
    store_dominance_status = metrics.get(
        "terminal_path_start_index_store_dominance_status", "unknown"
    )
    store_margin_share = metrics.get("terminal_path_start_index_store_child_margin_share", 0.0)
    store_dominant_child = metrics.get(
        "terminal_path_start_index_store_seconds_weighted_dominant_child",
        metrics.get("terminal_path_start_index_store_dominant_child", "unknown"),
    )
    if store_dominance_status == "near_tie":
        return "mark_start_index_store_as_distributed_store_overhead"
    if store_dominance_status == "case_weighted_aggregate_conflict":
        return "resolve_start_index_store_dominance_conflict"
    if (
        store_dominance_status == "stable"
        and store_margin_share >= args.start_index_store_child_margin_threshold
    ):
        if store_dominant_child == "insert":
            return "profile_start_index_insert_store_path"
        if store_dominant_child == "clear":
            return "profile_start_index_clear_store_path"
        if store_dominant_child == "overwrite":
            return "profile_start_index_overwrite_store_path"
    if store_dominance_status == "unknown":
        if (
            metrics.get("terminal_path_start_index_store_insert_share", 0.0)
            >= args.start_index_store_child_share_threshold
        ):
            return "profile_start_index_insert_store_path"
        if (
            metrics.get("terminal_path_start_index_store_clear_share", 0.0)
            >= args.start_index_store_child_share_threshold
        ):
            return "profile_start_index_clear_store_path"
        if (
            metrics.get("terminal_path_start_index_store_overwrite_share", 0.0)
            >= args.start_index_store_child_share_threshold
        ):
            return "profile_start_index_overwrite_store_path"
        return "profile_start_index_store_path"
    return "no_runtime_prototype_selected"


def recommended_lookup_miss_candidate_set_full_probe_action(metrics, args):
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_share_of_candidate_index", 0.0)
        < args.probe_dominant_share_threshold
    ):
        return None
    closure_status = metrics.get(
        "lookup_miss_candidate_set_full_probe_sampled_count_closure_status", "unknown"
    )
    if closure_status == "unknown":
        return "profile_lookup_miss_candidate_set_full_probe"
    if closure_status != "closed":
        return "inspect_lookup_miss_candidate_set_full_probe_timer_scope"
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_unexplained_share", 0.0)
        >= args.full_probe_unexplained_threshold
    ):
        return "inspect_lookup_miss_candidate_set_full_probe_timer_scope"
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_full_scan_share", 0.0)
        >= args.full_probe_full_scan_share_threshold
        or metrics.get("lookup_miss_candidate_set_full_probe_slots_scanned_p90", 0.0)
        >= args.full_probe_slots_scanned_p90_threshold
    ):
        return "profile_candidate_set_full_scan_path"
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_scan_share", 0.0)
        >= args.full_probe_scan_share_threshold
    ):
        return "profile_candidate_set_full_scan_path"
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_compare_share", 0.0)
        >= args.full_probe_compare_share_threshold
    ):
        return "profile_candidate_set_probe_compare_path"
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_branch_or_guard_share", 0.0)
        >= args.full_probe_branch_share_threshold
    ):
        return "profile_lookup_miss_probe_branch_path"
    if (
        metrics.get("lookup_miss_candidate_set_full_probe_redundant_reprobe_share", 0.0)
        >= args.full_probe_redundant_reprobe_threshold
    ):
        return "prototype_redundant_full_probe_skip_shadow"
    return "no_single_stable_leaf_found_under_current_profiler"


def recommended_terminal_path_state_update_action(metrics, args):
    production_state_update_unexplained_threshold = max(
        args.state_update_unexplained_threshold, 0.50
    )
    if (
        metrics.get("terminal_path_state_update_share_of_candidate_index", 0.0)
        < args.state_update_dominant_share_threshold
    ):
        return None
    if metrics.get("terminal_path_state_update_coverage_source") != "event_level_sampled":
        return "instrument_terminal_path_state_update_event_level_closure"
    closure_status = metrics.get(
        "terminal_path_state_update_sampled_count_closure_status", "unknown"
    )
    if closure_status == "unknown":
        return "profile_terminal_path_state_update"
    if closure_status != "closed":
        return "inspect_terminal_path_state_update_timer_scope"
    if (
        metrics.get("terminal_path_state_update_unexplained_share", 0.0)
        >= args.state_update_unexplained_threshold
    ):
        return "inspect_terminal_path_state_update_timer_scope"
    if (
        metrics.get("terminal_path_state_update_trace_or_profile_bookkeeping_share", 0.0)
        >= args.state_update_bookkeeping_share_threshold
    ):
        if metrics.get("production_state_update_coverage_source") != "event_level_sampled":
            return "classify_terminal_path_state_update_bookkeeping"
        if (
            metrics.get("production_state_update_sampled_count_closure_status", "unknown")
            != "closed"
        ):
            return "inspect_production_state_update_timer_scope"
        if (
            metrics.get("production_state_update_unexplained_share", 0.0)
            >= production_state_update_unexplained_threshold
        ):
            return "inspect_production_state_update_timer_scope"
        production_state_update_dominance_status = metrics.get(
            "production_state_update_dominance_status", "unknown"
        )
        production_state_update_margin_share = metrics.get(
            "production_state_update_child_margin_share", 0.0
        )
        production_state_update_dominant_child = metrics.get(
            "production_state_update_seconds_weighted_dominant_child",
            metrics.get("production_state_update_dominant_child", "unknown"),
        )
        if production_state_update_dominance_status in {
            "near_tie",
            "case_weighted_aggregate_conflict",
        }:
            return "mark_production_state_update_as_distributed_overhead"
        if (
            production_state_update_dominance_status == "stable"
            and production_state_update_margin_share
            >= args.state_update_child_margin_threshold
        ):
            if production_state_update_dominant_child == "benchmark_counter":
                return "reduce_or_cold_path_benchmark_state_update_counters"
            if production_state_update_dominant_child == "trace_replay_required_state":
                return "profile_trace_replay_required_state_update_path"
        if (
            production_state_update_dominance_status == "unknown"
            and metrics.get("production_state_update_benchmark_counter_share", 0.0)
            >= args.state_update_child_share_threshold
        ):
            return "reduce_or_cold_path_benchmark_state_update_counters"
        if (
            production_state_update_dominance_status == "unknown"
            and metrics.get("production_state_update_trace_replay_required_state_share", 0.0)
            >= args.state_update_child_share_threshold
        ):
            return "profile_trace_replay_required_state_update_path"
        return "mark_production_state_update_as_distributed_overhead"
    if (
        metrics.get("terminal_path_state_update_heap_update_share", 0.0)
        >= args.state_update_child_share_threshold
    ):
        return "profile_heap_update_path"
    if (
        metrics.get("terminal_path_state_update_heap_build_share", 0.0)
        >= args.state_update_child_share_threshold
    ):
        return "profile_heap_build_path"
    if (
        metrics.get("terminal_path_state_update_start_index_rebuild_share", 0.0)
        >= args.state_update_child_share_threshold
    ):
        return "profile_start_index_rebuild_path"
    return "mark_terminal_path_state_update_as_distributed_overhead"


def recommended_next_action(metrics, args):
    start_index_write_idempotent_share = share(
        metrics.get("terminal_path_start_index_write_idempotent_count", 0),
        metrics.get("terminal_path_start_index_write_count", 0),
    )
    start_index_store_action = recommended_start_index_store_action(metrics, args)
    full_probe_action = recommended_lookup_miss_candidate_set_full_probe_action(metrics, args)
    state_update_action = recommended_terminal_path_state_update_action(metrics, args)

    if metrics["candidate_index_share_of_initial_cpu_merge"] < args.candidate_index_dominant_threshold:
        return "no_host_merge_runtime_work"
    if (
        metrics["initial_cpu_merge_share_of_sim_seconds"] is not None
        and (
            metrics["initial_cpu_merge_share_of_sim_seconds"] < args.host_merge_materiality_threshold
            or metrics["candidate_index_share_of_sim_seconds"]
            < args.candidate_index_materiality_threshold
        )
    ):
        return "no_host_merge_runtime_work"
    if metrics.get("intra_profile_closure_status") == "residual_unexplained":
        return "reduce_profiler_timer_overhead"
    if metrics.get("profile_mode_overhead_status") == "suspect":
        return "reduce_profiler_timer_overhead"
    if (
        metrics.get("terminal_path_dominant_child") == "telemetry_overhead"
        and metrics["lookup_miss_reuse_writeback_aux_other_share_of_candidate_index"]
        >= args.aux_other_dominant_share_threshold
    ):
        return "reduce_profiler_timer_overhead"
    if metrics["candidate_index_timer_scope_status"] != "closed":
        return "inspect_candidate_index_timer_scope"
    if metrics["reuse_aux_other_timer_scope_status"] != "closed":
        return "inspect_candidate_index_timer_scope"
    if (
        metrics.get("terminal_path_start_index_write_share_of_candidate_index", 0.0)
        >= args.start_index_write_dominant_share_threshold
    ):
        if (
            metrics.get("terminal_path_start_index_write_sampled_count_closure_status")
            != "closed"
        ):
            return "inspect_start_index_write_timer_scope"
        if (
            metrics.get("terminal_path_start_index_write_unexplained_share", 0.0)
            >= args.start_index_write_unexplained_threshold
        ):
            return "inspect_start_index_write_timer_scope"
        if (
            metrics.get("terminal_path_start_index_write_probe_or_locate_share", 0.0)
            >= args.start_index_write_child_share_threshold
        ):
            return "profile_start_index_probe_or_locate_path"
        if (
            metrics.get("terminal_path_start_index_write_entry_store_share", 0.0)
            >= args.start_index_write_child_share_threshold
        ):
            if start_index_store_action is not None:
                return start_index_store_action
        if start_index_write_idempotent_share >= args.start_index_write_idempotent_threshold:
            return "prototype_start_index_idempotent_write_skip_shadow"
        return "profile_start_index_bookkeeping_path"
    if (
        metrics.get("terminal_path_start_index_write_entry_store_share", 0.0)
        >= args.start_index_write_child_share_threshold
        and metrics.get("terminal_path_start_index_store_sampled_count_closure_status") == "closed"
        and start_index_store_action not in {None, "profile_start_index_store_path"}
    ):
        return start_index_store_action
    if (
        metrics.get("terminal_path_state_update_share_of_candidate_index", 0.0)
        >= args.state_update_dominant_share_threshold
    ):
        return state_update_action or "profile_terminal_path_state_update"
    if (
        metrics["terminal_residual_share_of_candidate_index"]
        >= args.terminal_residual_dominant_share_threshold
    ):
        if metrics.get("lexical_span_closure_status") != "closed":
            return "profile_terminal_residual_by_lexical_spans"
        if metrics.get("profile_mode_overhead_status") in {"unknown", "needs_coarse_vs_lexical_ab"}:
            return "run_profile_mode_ab"
        if metrics.get("profile_mode_overhead_status") == "suspect":
            return "reduce_profiler_timer_overhead"
        if metrics.get("dominant_terminal_span") == "first_half":
            if metrics.get("dominant_terminal_first_half_span") == "span_a":
                return "split_terminal_first_half_span_a"
            if metrics.get("dominant_terminal_first_half_span") == "span_b":
                return "split_terminal_first_half_span_b"
            return "split_terminal_first_half_lexical_span"
        if metrics.get("dominant_terminal_span") == "second_half":
            return "split_terminal_second_half_lexical_span"
        return "profile_terminal_residual_by_lexical_spans"
    if (
        metrics["lookup_miss_reuse_writeback_aux_other_share_of_candidate_index"]
        >= args.aux_other_dominant_share_threshold
    ):
        return "inspect_candidate_index_timer_scope"
    if metrics["candidate_index_erase_share_of_candidate_index"] >= args.erase_dominant_share_threshold:
        return "prototype_eager_index_erase_handle_shadow"
    if (
        metrics["lookup_miss_candidate_set_full_probe_share_of_candidate_index"]
        >= args.probe_dominant_share_threshold
    ):
        return full_probe_action or "profile_lookup_miss_candidate_set_full_probe"
    if (
        metrics["lookup_miss_reuse_writeback_share_of_candidate_index"]
        >= args.reuse_writeback_dominant_share_threshold
    ):
        return "profile_lookup_miss_reuse_writeback"
    return "inspect_candidate_index_timer_scope"


def analyze_case(row, path, args):
    case_id = row["case_id"]
    if not parse_bool_like(row["verify_ok"]):
        raise LifecycleInputError(f"{path}: case {case_id} has verify_ok=0")

    context_apply_mean_seconds = to_float(row, "context_apply_mean_seconds", path)
    candidate_index_mean_seconds = to_float(row, "context_apply_candidate_index_mean_seconds", path)
    candidate_index_erase_mean_seconds = to_float(
        row, "context_apply_candidate_index_erase_mean_seconds", path
    )
    candidate_index_insert_mean_seconds = to_float(
        row, "context_apply_candidate_index_insert_mean_seconds", path
    )
    lookup_mean_seconds = to_float(row, "context_apply_lookup_mean_seconds", path)
    lookup_miss_mean_seconds = to_float(row, "context_apply_lookup_miss_mean_seconds", path)
    lookup_miss_open_slot_mean_seconds = to_float(
        row, "context_apply_lookup_miss_open_slot_mean_seconds", path
    )
    lookup_miss_candidate_set_full_probe_mean_seconds = to_float(
        row, "context_apply_lookup_miss_candidate_set_full_probe_mean_seconds", path
    )
    lookup_miss_eviction_select_mean_seconds = to_float(
        row, "context_apply_lookup_miss_eviction_select_mean_seconds", path
    )
    lookup_miss_reuse_writeback_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_mean_seconds", path
    )
    lookup_miss_reuse_writeback_victim_reset_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_victim_reset_mean_seconds", path
    )
    lookup_miss_reuse_writeback_key_rebind_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_key_rebind_mean_seconds", path
    )
    lookup_miss_reuse_writeback_candidate_copy_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_candidate_copy_mean_seconds", path
    )
    lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds", path
    )
    lookup_miss_reuse_writeback_aux_heap_build_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_aux_heap_build_mean_seconds", path
    )
    lookup_miss_reuse_writeback_aux_heap_update_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_aux_heap_update_mean_seconds", path
    )
    lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds", path
    )
    lookup_miss_reuse_writeback_aux_other_mean_seconds = to_float(
        row, "context_apply_lookup_miss_reuse_writeback_aux_other_mean_seconds", path
    )
    lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds = to_float(
        row,
        "context_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds",
        path,
    )
    lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds = to_float(
        row,
        "context_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds",
        path,
    )
    lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds = to_float(
        row,
        "context_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds",
        path,
    )
    lookup_miss_reuse_writeback_aux_other_residual_mean_seconds = to_float(
        row,
        "context_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds",
        path,
    )
    lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds = (
        resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds",
            ),
        )
    )
    lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds = (
        resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds",
            ),
        )
    )
    lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds = (
        resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds",
            ),
        )
    )
    lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds = resolve_optional_float(
        row,
        ("context_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds",),
    )
    candidate_index_lookup_count = to_int(row, "context_apply_candidate_index_lookup_count", path)
    candidate_index_hit_count = to_int(row, "context_apply_candidate_index_hit_count", path)
    candidate_index_miss_count = to_int(row, "context_apply_candidate_index_miss_count", path)
    candidate_index_erase_count = to_int(row, "context_apply_candidate_index_erase_count", path)
    candidate_index_insert_count = to_int(row, "context_apply_candidate_index_insert_count", path)
    full_set_miss_count = to_int(row, "context_apply_full_set_miss_count", path)
    full_probe_metrics = derive_lookup_miss_candidate_set_full_probe_metrics(
        fallback_parent_seconds=lookup_miss_candidate_set_full_probe_mean_seconds,
        split_parent_seconds=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_parent_mean_seconds",)
        ),
        scan_seconds=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_scan_mean_seconds",)
        ),
        compare_seconds=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_compare_mean_seconds",)
        ),
        branch_or_guard_seconds=resolve_optional_float(
            row,
            ("context_apply_lookup_miss_candidate_set_full_probe_branch_or_guard_mean_seconds",),
        ),
        bookkeeping_seconds=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_bookkeeping_mean_seconds",)
        ),
        child_known_seconds=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_child_known_mean_seconds",)
        ),
        unexplained_seconds=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_unexplained_mean_seconds",)
        ),
        sampled_event_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_sampled_event_count",)
        ),
        covered_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_candidate_set_full_probe_covered_sampled_event_count",
            ),
        ),
        unclassified_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count",
            ),
        ),
        multi_child_sampled_event_count=resolve_optional_int(
            row,
            (
                "context_apply_lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count",
            ),
        ),
        full_probe_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_count",)
        ),
        slots_scanned_total=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_total",)
        ),
        slots_scanned_per_probe_mean=resolve_optional_float(
            row,
            (
                "context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean",
            ),
        ),
        slots_scanned_p50=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p50",)
        ),
        slots_scanned_p90=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p90",)
        ),
        slots_scanned_p99=resolve_optional_float(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p99",)
        ),
        full_scan_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_full_scan_count",)
        ),
        early_exit_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_early_exit_count",)
        ),
        found_existing_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_found_existing_count",)
        ),
        confirmed_absent_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_candidate_set_full_probe_confirmed_absent_count",),
        ),
        redundant_reprobe_count=resolve_optional_int(
            row,
            ("context_apply_lookup_miss_candidate_set_full_probe_redundant_reprobe_count",),
        ),
        same_key_reprobe_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_same_key_reprobe_count",)
        ),
        same_event_reprobe_count=resolve_optional_int(
            row, ("context_apply_lookup_miss_candidate_set_full_probe_same_event_reprobe_count",)
        ),
    )

    sim_initial_scan_cpu_merge_seconds = resolve_optional_float(
        row,
        (
            "sim_initial_scan_cpu_merge_seconds_mean_seconds",
            "sim_initial_scan_cpu_merge_seconds_seconds",
        ),
    )
    sim_seconds = resolve_optional_float(
        row, ("sim_seconds_mean_seconds", "sim_seconds_seconds", "sim_total_mean_seconds")
    )
    total_seconds = resolve_optional_float(
        row, ("total_seconds_mean_seconds", "total_seconds_seconds")
    )
    workload_id = resolve_optional_text(row, "workload_id")
    benchmark_source = resolve_optional_text(row, "benchmark_source")
    profile_mode = resolve_optional_text(row, "profile_mode") or "unknown"
    terminal_telemetry_overhead_mode_requested = (
        resolve_optional_text(row, "terminal_telemetry_overhead_mode_requested")
        or "unknown"
    )
    terminal_telemetry_overhead_mode_effective = (
        resolve_optional_text(row, "terminal_telemetry_overhead_mode_effective")
        or "unknown"
    )
    state_update_bookkeeping_mode_requested = (
        resolve_optional_text(row, "state_update_bookkeeping_mode_requested")
        or "unknown"
    )
    state_update_bookkeeping_mode_effective = (
        resolve_optional_text(row, "state_update_bookkeeping_mode_effective")
        or "unknown"
    )

    validate_positive_optional(
        sim_initial_scan_cpu_merge_seconds,
        path,
        case_id,
        "sim_initial_scan_cpu_merge_seconds_mean_seconds",
    )
    validate_positive_optional(sim_seconds, path, case_id, "sim_seconds_mean_seconds")
    validate_positive_optional(total_seconds, path, case_id, "total_seconds_mean_seconds")

    case_materiality_known = (
        bool(workload_id)
        and bool(benchmark_source)
        and all(
            value is not None
            for value in (
                sim_initial_scan_cpu_merge_seconds,
                sim_seconds,
                total_seconds,
            )
        )
    )

    lookup_hit_mean_seconds = max(0.0, lookup_mean_seconds - lookup_miss_mean_seconds)
    candidate_index_share_of_initial_cpu_merge = share(
        candidate_index_mean_seconds, context_apply_mean_seconds
    )
    initial_cpu_merge_share_of_sim_seconds = (
        share(sim_initial_scan_cpu_merge_seconds, sim_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and sim_seconds is not None
        else None
    )
    initial_cpu_merge_share_of_total_seconds = (
        share(sim_initial_scan_cpu_merge_seconds, total_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and total_seconds is not None
        else None
    )
    candidate_index_share_of_sim_seconds = (
        candidate_index_share_of_initial_cpu_merge * initial_cpu_merge_share_of_sim_seconds
        if initial_cpu_merge_share_of_sim_seconds is not None
        else None
    )
    candidate_index_share_of_total_seconds = (
        candidate_index_share_of_initial_cpu_merge * initial_cpu_merge_share_of_total_seconds
        if initial_cpu_merge_share_of_total_seconds is not None
        else None
    )

    candidate_index_scope_gap_seconds = abs(candidate_index_mean_seconds - lookup_mean_seconds)
    candidate_index_parent_seconds = candidate_index_mean_seconds
    candidate_index_child_known_seconds = lookup_mean_seconds
    lookup_partition_gap_seconds = abs(
        lookup_mean_seconds - (lookup_hit_mean_seconds + lookup_miss_mean_seconds)
    )
    lookup_miss_partition_gap_seconds = abs(
        lookup_miss_mean_seconds
        - (
            lookup_miss_open_slot_mean_seconds
            + lookup_miss_candidate_set_full_probe_mean_seconds
            + lookup_miss_eviction_select_mean_seconds
            + lookup_miss_reuse_writeback_mean_seconds
        )
    )
    reuse_writeback_partition_gap_seconds = abs(
        lookup_miss_reuse_writeback_mean_seconds
        - (
            lookup_miss_reuse_writeback_victim_reset_mean_seconds
            + lookup_miss_reuse_writeback_key_rebind_mean_seconds
            + lookup_miss_reuse_writeback_candidate_copy_mean_seconds
            + lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds
        )
    )
    lookup_miss_reuse_writeback_parent_seconds = lookup_miss_reuse_writeback_mean_seconds
    lookup_miss_reuse_writeback_child_known_seconds = (
        lookup_miss_reuse_writeback_victim_reset_mean_seconds
        + lookup_miss_reuse_writeback_key_rebind_mean_seconds
        + lookup_miss_reuse_writeback_candidate_copy_mean_seconds
        + lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds
    )
    aux_bookkeeping_partition_gap_seconds = abs(
        lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds
        - (
            lookup_miss_reuse_writeback_aux_heap_build_mean_seconds
            + lookup_miss_reuse_writeback_aux_heap_update_mean_seconds
            + lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds
            + lookup_miss_reuse_writeback_aux_other_mean_seconds
        )
    )
    aux_other_partition_gap_seconds = abs(
        lookup_miss_reuse_writeback_aux_other_mean_seconds
        - (
            lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds
            + lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds
            + lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_mean_seconds
        )
    )
    lookup_miss_reuse_writeback_aux_other_parent_seconds = (
        lookup_miss_reuse_writeback_aux_other_mean_seconds
    )
    lookup_miss_reuse_writeback_aux_other_child_known_seconds = (
        lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds
        + lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds
        + lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds
        + lookup_miss_reuse_writeback_aux_other_residual_mean_seconds
    )
    aux_other_residual_components_present = any(
        value is not None
        for value in (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds,
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds,
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds,
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds,
        )
    )
    if not aux_other_residual_components_present:
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds = 0.0
        lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds = 0.0
        lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds = 0.0
        lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_mean_seconds
        )
    else:
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds
            or 0.0
        )
        lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds
            or 0.0
        )
        lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds
            or 0.0
        )
        lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds or 0.0
        )
    lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds = (
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds
        + lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds
        + lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds
        + lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds
    )
    lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds = abs(
        lookup_miss_reuse_writeback_aux_other_residual_mean_seconds
        - lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds
    )
    candidate_index_timer_scope_status = "closed"
    if (
        max(
            share(candidate_index_scope_gap_seconds, candidate_index_mean_seconds),
            share(lookup_partition_gap_seconds, candidate_index_mean_seconds),
            share(lookup_miss_partition_gap_seconds, candidate_index_mean_seconds),
        )
        >= args.timer_scope_gap_threshold
    ):
        candidate_index_timer_scope_status = "residual_unexplained"
    reuse_aux_other_timer_scope_status = "closed"
    if (
        max(
            share(reuse_writeback_partition_gap_seconds, candidate_index_mean_seconds),
            share(aux_bookkeeping_partition_gap_seconds, candidate_index_mean_seconds),
            share(aux_other_partition_gap_seconds, candidate_index_mean_seconds),
        )
        >= args.timer_scope_gap_threshold
    ):
        reuse_aux_other_timer_scope_status = "residual_unexplained"
    terminal_residual_share_of_candidate_index = share(
        lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds,
        candidate_index_mean_seconds,
    )
    terminal_residual_status = (
        "dominant"
        if terminal_residual_share_of_candidate_index
        >= args.terminal_residual_dominant_share_threshold
        else "minor"
    )
    terminal_path = derive_terminal_path_metrics(
        row,
        candidate_index_seconds=candidate_index_mean_seconds,
        state_update_unexplained_threshold=args.state_update_unexplained_threshold,
        full_set_miss_count=full_set_miss_count,
        lookup_miss_reuse_writeback_key_rebind_seconds=(
            lookup_miss_reuse_writeback_key_rebind_mean_seconds
        ),
        lookup_miss_reuse_writeback_candidate_copy_seconds=(
            lookup_miss_reuse_writeback_candidate_copy_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_bookkeeping_seconds=(
            lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_heap_build_seconds=(
            lookup_miss_reuse_writeback_aux_heap_build_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_heap_update_seconds=(
            lookup_miss_reuse_writeback_aux_heap_update_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds=(
            lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds=(
            lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds=(
            lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds=(
            lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_residual_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds
        ),
    )
    terminal_lexical_parent_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_mean_seconds",)
    )
    terminal_span_first_half_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_span_first_half_mean_seconds",)
    )
    terminal_span_second_half_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_span_second_half_mean_seconds",)
    )
    terminal_first_half_parent_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_mean_seconds",)
    )
    if terminal_first_half_parent_seconds is None:
        terminal_first_half_parent_seconds = terminal_span_first_half_seconds
    terminal_first_half_span_a_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_mean_seconds",)
    )
    terminal_first_half_span_b_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_mean_seconds",)
    )
    terminal_first_half_child_known_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_mean_seconds",)
    )
    if (
        terminal_first_half_child_known_seconds is None
        and terminal_first_half_span_a_seconds is not None
        and terminal_first_half_span_b_seconds is not None
    ):
        terminal_first_half_child_known_seconds = (
            terminal_first_half_span_a_seconds + terminal_first_half_span_b_seconds
        )
    terminal_first_half_unexplained_seconds = resolve_optional_float(
        row, ("context_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_mean_seconds",)
    )
    if (
        terminal_first_half_unexplained_seconds is None
        and terminal_first_half_parent_seconds is not None
        and terminal_first_half_child_known_seconds is not None
    ):
        terminal_first_half_unexplained_seconds = max(
            terminal_first_half_parent_seconds - terminal_first_half_child_known_seconds,
            0.0,
        )
    dominant_terminal_span = dominant_terminal_span_label(
        terminal_span_first_half_seconds,
        terminal_span_second_half_seconds,
    )
    dominant_terminal_first_half_span = dominant_terminal_first_half_span_label(
        terminal_first_half_span_a_seconds,
        terminal_first_half_span_b_seconds,
    )
    timer_call_count = resolve_optional_int(row, ("context_apply_timer_call_count",))
    terminal_timer_call_count = resolve_optional_int(
        row, ("context_apply_terminal_timer_call_count",)
    )
    lexical_timer_call_count = resolve_optional_int(
        row, ("context_apply_lexical_timer_call_count",)
    )
    intra_profile_closure_status = classify_intra_profile_closure_status(
        terminal_lexical_parent_seconds,
        terminal_span_first_half_seconds,
        terminal_span_second_half_seconds,
    )
    profile_mode_overhead_status = classify_profile_mode_overhead_status(
        intra_profile_closure_status
    )
    terminal_timer_closure_status = classify_timer_closure_status(
        terminal_path["parent_seconds"],
        terminal_path["child_known_seconds"],
        args.timer_scope_gap_threshold,
    )
    lexical_span_closure_status = (
        "closed"
        if intra_profile_closure_status == "ok"
        else (
            "unknown"
            if intra_profile_closure_status == "unknown"
            else "residual_unexplained"
        )
    )
    candidate_index_materiality_status = classify_candidate_index_materiality_status(
        initial_cpu_merge_share_of_sim_seconds,
        candidate_index_share_of_sim_seconds,
        host_merge_materiality_threshold=args.host_merge_materiality_threshold,
        candidate_index_materiality_threshold=args.candidate_index_materiality_threshold,
    )

    metrics = {
        "candidate_index_share_of_initial_cpu_merge": candidate_index_share_of_initial_cpu_merge,
        "candidate_index_share_of_sim_seconds": candidate_index_share_of_sim_seconds,
        "initial_cpu_merge_share_of_sim_seconds": initial_cpu_merge_share_of_sim_seconds,
        "candidate_index_timer_scope_status": candidate_index_timer_scope_status,
        "reuse_aux_other_timer_scope_status": reuse_aux_other_timer_scope_status,
        "terminal_residual_share_of_candidate_index": terminal_residual_share_of_candidate_index,
        "terminal_residual_status": terminal_residual_status,
        "profile_mode": profile_mode if profile_mode else "unknown",
        "terminal_telemetry_overhead_mode_requested": (
            terminal_telemetry_overhead_mode_requested
        ),
        "terminal_telemetry_overhead_mode_effective": (
            terminal_telemetry_overhead_mode_effective
        ),
        "state_update_bookkeeping_mode_requested": (
            state_update_bookkeeping_mode_requested
        ),
        "state_update_bookkeeping_mode_effective": (
            state_update_bookkeeping_mode_effective
        ),
        "candidate_index_erase_share_of_candidate_index": share(
            candidate_index_erase_mean_seconds, candidate_index_mean_seconds
        ),
        "candidate_index_insert_share_of_candidate_index": share(
            candidate_index_insert_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_hit_share_of_candidate_index": share(
            lookup_hit_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_share_of_candidate_index": share(
            lookup_miss_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_open_slot_share_of_candidate_index": share(
            lookup_miss_open_slot_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_candidate_set_full_probe_share_of_candidate_index": share(
            lookup_miss_candidate_set_full_probe_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_candidate_set_full_probe_parent_seconds": full_probe_metrics[
            "parent_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_scan_seconds": full_probe_metrics[
            "scan_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_compare_seconds": full_probe_metrics[
            "compare_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_branch_or_guard_seconds": full_probe_metrics[
            "branch_or_guard_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_bookkeeping_seconds": full_probe_metrics[
            "bookkeeping_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_child_known_seconds": full_probe_metrics[
            "child_known_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_unexplained_seconds": full_probe_metrics[
            "unexplained_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_unexplained_share": full_probe_metrics[
            "unexplained_share"
        ],
        "lookup_miss_candidate_set_full_probe_sampled_event_count": full_probe_metrics[
            "sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_covered_sampled_event_count": full_probe_metrics[
            "covered_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count": full_probe_metrics[
            "unclassified_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count": full_probe_metrics[
            "multi_child_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": full_probe_metrics[
            "sampled_count_closure_status"
        ],
        "lookup_miss_candidate_set_full_probe_dominant_child": full_probe_metrics[
            "dominant_child"
        ],
        "lookup_miss_candidate_set_full_probe_coverage_share": full_probe_metrics[
            "coverage_share"
        ],
        "lookup_miss_candidate_set_full_probe_unclassified_share": full_probe_metrics[
            "unclassified_share"
        ],
        "lookup_miss_candidate_set_full_probe_multi_child_share": full_probe_metrics[
            "multi_child_share"
        ],
        "lookup_miss_candidate_set_full_probe_scan_share": full_probe_metrics[
            "scan_share"
        ],
        "lookup_miss_candidate_set_full_probe_compare_share": full_probe_metrics[
            "compare_share"
        ],
        "lookup_miss_candidate_set_full_probe_branch_or_guard_share": full_probe_metrics[
            "branch_or_guard_share"
        ],
        "lookup_miss_candidate_set_full_probe_bookkeeping_share": full_probe_metrics[
            "bookkeeping_share"
        ],
        "lookup_miss_candidate_set_full_probe_count": full_probe_metrics["count"],
        "lookup_miss_candidate_set_full_probe_slots_scanned_total": full_probe_metrics[
            "slots_scanned_total"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean": full_probe_metrics[
            "slots_scanned_per_probe_mean"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p50": full_probe_metrics[
            "slots_scanned_p50"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p90": full_probe_metrics[
            "slots_scanned_p90"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p99": full_probe_metrics[
            "slots_scanned_p99"
        ],
        "lookup_miss_candidate_set_full_probe_full_scan_count": full_probe_metrics[
            "full_scan_count"
        ],
        "lookup_miss_candidate_set_full_probe_early_exit_count": full_probe_metrics[
            "early_exit_count"
        ],
        "lookup_miss_candidate_set_full_probe_found_existing_count": full_probe_metrics[
            "found_existing_count"
        ],
        "lookup_miss_candidate_set_full_probe_confirmed_absent_count": full_probe_metrics[
            "confirmed_absent_count"
        ],
        "lookup_miss_candidate_set_full_probe_redundant_reprobe_count": full_probe_metrics[
            "redundant_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_same_key_reprobe_count": full_probe_metrics[
            "same_key_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_same_event_reprobe_count": full_probe_metrics[
            "same_event_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_full_scan_share": full_probe_metrics[
            "full_scan_share"
        ],
        "lookup_miss_candidate_set_full_probe_early_exit_share": full_probe_metrics[
            "early_exit_share"
        ],
        "lookup_miss_candidate_set_full_probe_found_existing_share": full_probe_metrics[
            "found_existing_share"
        ],
        "lookup_miss_candidate_set_full_probe_confirmed_absent_share": full_probe_metrics[
            "confirmed_absent_share"
        ],
        "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": full_probe_metrics[
            "redundant_reprobe_share"
        ],
        "lookup_miss_eviction_select_share_of_candidate_index": share(
            lookup_miss_eviction_select_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_reuse_writeback_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_start_index_rebuild_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds,
            candidate_index_mean_seconds,
        ),
        "lookup_miss_reuse_writeback_aux_other_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_mean_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_residual_mean_seconds,
            candidate_index_mean_seconds,
        ),
        "terminal_path_dominant_child": terminal_path["dominant_child"],
        "terminal_lexical_parent_seconds": terminal_lexical_parent_seconds,
        "terminal_span_first_half_seconds": terminal_span_first_half_seconds,
        "terminal_span_second_half_seconds": terminal_span_second_half_seconds,
        "terminal_first_half_parent_seconds": terminal_first_half_parent_seconds,
        "terminal_first_half_span_a_seconds": terminal_first_half_span_a_seconds,
        "terminal_first_half_span_b_seconds": terminal_first_half_span_b_seconds,
        "terminal_first_half_child_known_seconds": terminal_first_half_child_known_seconds,
        "terminal_first_half_unexplained_seconds": terminal_first_half_unexplained_seconds,
        "dominant_terminal_span": dominant_terminal_span,
        "dominant_terminal_first_half_span": dominant_terminal_first_half_span,
        "timer_call_count": timer_call_count,
        "terminal_timer_call_count": terminal_timer_call_count,
        "lexical_timer_call_count": lexical_timer_call_count,
        "intra_profile_closure_status": intra_profile_closure_status,
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "candidate_index_materiality_status": candidate_index_materiality_status,
        "terminal_timer_closure_status": terminal_timer_closure_status,
        "lexical_span_closure_status": lexical_span_closure_status,
        "profile_overhead_status": profile_mode_overhead_status,
        "candidate_index_scope_gap_share_of_candidate_index": share(
            candidate_index_scope_gap_seconds, candidate_index_mean_seconds
        ),
        "candidate_index_parent_seconds": candidate_index_parent_seconds,
        "candidate_index_child_known_seconds": candidate_index_child_known_seconds,
        "candidate_index_unexplained_seconds": candidate_index_scope_gap_seconds,
        "candidate_index_unexplained_share_of_candidate_index": share(
            candidate_index_scope_gap_seconds, candidate_index_parent_seconds
        ),
        "lookup_partition_gap_share_of_candidate_index": share(
            lookup_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_partition_gap_share_of_candidate_index": share(
            lookup_miss_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "reuse_writeback_partition_gap_share_of_candidate_index": share(
            reuse_writeback_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_reuse_writeback_parent_seconds": lookup_miss_reuse_writeback_parent_seconds,
        "lookup_miss_reuse_writeback_child_known_seconds": (
            lookup_miss_reuse_writeback_child_known_seconds
        ),
        "lookup_miss_reuse_writeback_unexplained_seconds": reuse_writeback_partition_gap_seconds,
        "lookup_miss_reuse_writeback_unexplained_share_of_candidate_index": share(
            reuse_writeback_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "aux_bookkeeping_partition_gap_share_of_candidate_index": share(
            aux_bookkeeping_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "aux_other_partition_gap_share_of_candidate_index": share(
            aux_other_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_parent_seconds": (
            lookup_miss_reuse_writeback_aux_other_parent_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_child_known_seconds": (
            lookup_miss_reuse_writeback_aux_other_child_known_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_unexplained_seconds": aux_other_partition_gap_seconds,
        "lookup_miss_reuse_writeback_aux_other_unexplained_share_of_candidate_index": share(
            aux_other_partition_gap_seconds, candidate_index_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_parent_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds,
            candidate_index_mean_seconds,
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_residual_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds,
            candidate_index_mean_seconds,
        ),
        "terminal_path_scope": terminal_path["scope"],
        "terminal_path_parent_seconds": terminal_path["parent_seconds"],
        "terminal_path_child_known_seconds": terminal_path["child_known_seconds"],
        "terminal_path_candidate_slot_write_seconds": terminal_path[
            "candidate_slot_write_seconds"
        ],
        "terminal_path_start_index_write_seconds": terminal_path[
            "start_index_write_seconds"
        ],
        "terminal_path_state_update_seconds": terminal_path["state_update_seconds"],
        "terminal_path_state_update_parent_seconds": terminal_path[
            "state_update_parent_seconds"
        ],
        "terminal_path_state_update_heap_build_seconds": terminal_path[
            "state_update_heap_build_seconds"
        ],
        "terminal_path_state_update_heap_update_seconds": terminal_path[
            "state_update_heap_update_seconds"
        ],
        "terminal_path_state_update_start_index_rebuild_seconds": terminal_path[
            "state_update_start_index_rebuild_seconds"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_seconds": terminal_path[
            "state_update_trace_or_profile_bookkeeping_seconds"
        ],
        "terminal_path_state_update_child_known_seconds": terminal_path[
            "state_update_child_known_seconds"
        ],
        "terminal_path_state_update_unexplained_seconds": terminal_path[
            "state_update_unexplained_seconds"
        ],
        "terminal_path_state_update_unexplained_share": terminal_path[
            "state_update_unexplained_share"
        ],
        "terminal_path_state_update_sampled_event_count": terminal_path[
            "state_update_sampled_event_count"
        ],
        "terminal_path_state_update_covered_sampled_event_count": terminal_path[
            "state_update_covered_sampled_event_count"
        ],
        "terminal_path_state_update_unclassified_sampled_event_count": terminal_path[
            "state_update_unclassified_sampled_event_count"
        ],
        "terminal_path_state_update_multi_child_sampled_event_count": terminal_path[
            "state_update_multi_child_sampled_event_count"
        ],
        "terminal_path_state_update_heap_build_sampled_event_count": terminal_path[
            "state_update_heap_build_sampled_event_count"
        ],
        "terminal_path_state_update_heap_update_sampled_event_count": terminal_path[
            "state_update_heap_update_sampled_event_count"
        ],
        "terminal_path_state_update_start_index_rebuild_sampled_event_count": terminal_path[
            "state_update_start_index_rebuild_sampled_event_count"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count": terminal_path[
            "state_update_trace_or_profile_bookkeeping_sampled_event_count"
        ],
        "terminal_path_state_update_sampled_count_closure_status": terminal_path[
            "state_update_sampled_count_closure_status"
        ],
        "terminal_path_state_update_coverage_source": terminal_path[
            "state_update_coverage_source"
        ],
        "terminal_path_state_update_timer_scope_status": terminal_path[
            "state_update_timer_scope_status"
        ],
        "terminal_path_state_update_dominant_child": terminal_path[
            "state_update_dominant_child"
        ],
        "terminal_path_state_update_coverage_share": terminal_path[
            "state_update_coverage_share"
        ],
        "terminal_path_state_update_unclassified_share": terminal_path[
            "state_update_unclassified_share"
        ],
        "terminal_path_state_update_multi_child_share": terminal_path[
            "state_update_multi_child_share"
        ],
        "terminal_path_state_update_heap_build_share": terminal_path[
            "state_update_heap_build_share"
        ],
        "terminal_path_state_update_heap_update_share": terminal_path[
            "state_update_heap_update_share"
        ],
        "terminal_path_state_update_start_index_rebuild_share": terminal_path[
            "state_update_start_index_rebuild_share"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_share": terminal_path[
            "state_update_trace_or_profile_bookkeeping_share"
        ],
        "terminal_path_telemetry_overhead_seconds": terminal_path[
            "telemetry_overhead_seconds"
        ],
        "terminal_path_residual_seconds": terminal_path["residual_seconds"],
        "terminal_path_candidate_slot_write_share_of_candidate_index": terminal_path[
            "candidate_slot_write_share_of_candidate_index"
        ],
        "terminal_path_start_index_write_share_of_candidate_index": terminal_path[
            "start_index_write_share_of_candidate_index"
        ],
        "terminal_path_state_update_share_of_candidate_index": terminal_path[
            "state_update_share_of_candidate_index"
        ],
        "terminal_path_telemetry_overhead_share_of_candidate_index": terminal_path[
            "telemetry_overhead_share_of_candidate_index"
        ],
        "terminal_path_residual_share_of_candidate_index": terminal_path[
            "residual_share_of_candidate_index"
        ],
        "terminal_path_event_count": terminal_path["event_count"],
        "terminal_path_candidate_slot_write_count": terminal_path[
            "candidate_slot_write_count"
        ],
        "terminal_path_start_index_write_count": terminal_path[
            "start_index_write_count"
        ],
        "terminal_path_state_update_count": terminal_path["state_update_count"],
        "terminal_path_state_update_event_count": terminal_path[
            "state_update_event_count"
        ],
        "terminal_path_state_update_heap_build_count": terminal_path[
            "state_update_heap_build_count"
        ],
        "terminal_path_state_update_heap_update_count": terminal_path[
            "state_update_heap_update_count"
        ],
        "terminal_path_state_update_start_index_rebuild_count": terminal_path[
            "state_update_start_index_rebuild_count"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_count": terminal_path[
            "state_update_trace_or_profile_bookkeeping_count"
        ],
        "terminal_path_state_update_aux_updates_total": terminal_path[
            "state_update_aux_updates_total"
        ],
        "production_state_update_parent_seconds": terminal_path[
            "production_state_update_parent_seconds"
        ],
        "production_state_update_benchmark_counter_seconds": terminal_path[
            "production_state_update_benchmark_counter_seconds"
        ],
        "production_state_update_trace_replay_required_state_seconds": terminal_path[
            "production_state_update_trace_replay_required_state_seconds"
        ],
        "production_state_update_child_known_seconds": terminal_path[
            "production_state_update_child_known_seconds"
        ],
        "production_state_update_unexplained_seconds": terminal_path[
            "production_state_update_unexplained_seconds"
        ],
        "production_state_update_unexplained_share": terminal_path[
            "production_state_update_unexplained_share"
        ],
        "production_state_update_sampled_event_count": terminal_path[
            "production_state_update_sampled_event_count"
        ],
        "production_state_update_covered_sampled_event_count": terminal_path[
            "production_state_update_covered_sampled_event_count"
        ],
        "production_state_update_unclassified_sampled_event_count": terminal_path[
            "production_state_update_unclassified_sampled_event_count"
        ],
        "production_state_update_multi_child_sampled_event_count": terminal_path[
            "production_state_update_multi_child_sampled_event_count"
        ],
        "production_state_update_benchmark_counter_sampled_event_count": terminal_path[
            "production_state_update_benchmark_counter_sampled_event_count"
        ],
        "production_state_update_trace_replay_required_state_sampled_event_count": terminal_path[
            "production_state_update_trace_replay_required_state_sampled_event_count"
        ],
        "production_state_update_sampled_count_closure_status": terminal_path[
            "production_state_update_sampled_count_closure_status"
        ],
        "production_state_update_coverage_source": terminal_path[
            "production_state_update_coverage_source"
        ],
        "production_state_update_timer_scope_status": terminal_path[
            "production_state_update_timer_scope_status"
        ],
        "production_state_update_dominant_child": terminal_path[
            "production_state_update_dominant_child"
        ],
        "production_state_update_coverage_share": terminal_path[
            "production_state_update_coverage_share"
        ],
        "production_state_update_unclassified_share": terminal_path[
            "production_state_update_unclassified_share"
        ],
        "production_state_update_multi_child_share": terminal_path[
            "production_state_update_multi_child_share"
        ],
        "production_state_update_benchmark_counter_share": terminal_path[
            "production_state_update_benchmark_counter_share"
        ],
        "production_state_update_trace_replay_required_state_share": terminal_path[
            "production_state_update_trace_replay_required_state_share"
        ],
        "production_state_update_share_of_candidate_index": terminal_path[
            "production_state_update_share_of_candidate_index"
        ],
        "production_state_update_event_count": terminal_path[
            "production_state_update_event_count"
        ],
        "production_state_update_benchmark_counter_count": terminal_path[
            "production_state_update_benchmark_counter_count"
        ],
        "production_state_update_trace_replay_required_state_count": terminal_path[
            "production_state_update_trace_replay_required_state_count"
        ],
        "terminal_path_candidate_bytes_written": terminal_path[
            "candidate_bytes_written"
        ],
        "terminal_path_start_index_bytes_written": terminal_path[
            "start_index_bytes_written"
        ],
        "terminal_path_dominant_child": terminal_path["dominant_child"],
        "terminal_path_start_index_write_parent_seconds": terminal_path[
            "start_index_write_parent_seconds"
        ],
        "terminal_path_start_index_write_left_seconds": terminal_path[
            "start_index_write_left_seconds"
        ],
        "terminal_path_start_index_write_right_seconds": terminal_path[
            "start_index_write_right_seconds"
        ],
        "terminal_path_start_index_write_child_known_seconds": terminal_path[
            "start_index_write_child_known_seconds"
        ],
        "terminal_path_start_index_write_unexplained_seconds": terminal_path[
            "start_index_write_unexplained_seconds"
        ],
        "terminal_path_start_index_write_unexplained_share": terminal_path[
            "start_index_write_unexplained_share"
        ],
        "terminal_path_start_index_write_sampled_event_count": terminal_path[
            "start_index_write_sampled_event_count"
        ],
        "terminal_path_start_index_write_covered_sampled_event_count": terminal_path[
            "start_index_write_covered_sampled_event_count"
        ],
        "terminal_path_start_index_write_unclassified_sampled_event_count": terminal_path[
            "start_index_write_unclassified_sampled_event_count"
        ],
        "terminal_path_start_index_write_multi_child_sampled_event_count": terminal_path[
            "start_index_write_multi_child_sampled_event_count"
        ],
        "terminal_path_start_index_write_left_sampled_event_count": terminal_path[
            "start_index_write_left_sampled_event_count"
        ],
        "terminal_path_start_index_write_right_sampled_event_count": terminal_path[
            "start_index_write_right_sampled_event_count"
        ],
        "terminal_path_start_index_write_sampled_count_closure_status": terminal_path[
            "start_index_write_sampled_count_closure_status"
        ],
        "terminal_path_start_index_write_dominant_child": terminal_path[
            "start_index_write_dominant_child"
        ],
        "terminal_path_start_index_write_coverage_share": terminal_path[
            "start_index_write_coverage_share"
        ],
        "terminal_path_start_index_write_unclassified_share": terminal_path[
            "start_index_write_unclassified_share"
        ],
        "terminal_path_start_index_write_multi_child_share": terminal_path[
            "start_index_write_multi_child_share"
        ],
        "terminal_path_start_index_write_probe_or_locate_share": terminal_path[
            "start_index_write_probe_or_locate_share"
        ],
        "terminal_path_start_index_write_entry_store_share": terminal_path[
            "start_index_write_entry_store_share"
        ],
        "terminal_path_start_index_write_insert_count": terminal_path[
            "start_index_write_insert_count"
        ],
        "terminal_path_start_index_write_update_existing_count": terminal_path[
            "start_index_write_update_existing_count"
        ],
        "terminal_path_start_index_write_clear_count": terminal_path[
            "start_index_write_clear_count"
        ],
        "terminal_path_start_index_write_overwrite_count": terminal_path[
            "start_index_write_overwrite_count"
        ],
        "terminal_path_start_index_write_idempotent_count": terminal_path[
            "start_index_write_idempotent_count"
        ],
        "terminal_path_start_index_write_value_changed_count": terminal_path[
            "start_index_write_value_changed_count"
        ],
        "terminal_path_start_index_write_probe_count": terminal_path[
            "start_index_write_probe_count"
        ],
        "terminal_path_start_index_write_probe_steps_total": terminal_path[
            "start_index_write_probe_steps_total"
        ],
        "terminal_path_start_index_store_parent_seconds": terminal_path[
            "start_index_store_parent_seconds"
        ],
        "terminal_path_start_index_store_insert_seconds": terminal_path[
            "start_index_store_insert_seconds"
        ],
        "terminal_path_start_index_store_clear_seconds": terminal_path[
            "start_index_store_clear_seconds"
        ],
        "terminal_path_start_index_store_overwrite_seconds": terminal_path[
            "start_index_store_overwrite_seconds"
        ],
        "terminal_path_start_index_store_child_known_seconds": terminal_path[
            "start_index_store_child_known_seconds"
        ],
        "terminal_path_start_index_store_unexplained_seconds": terminal_path[
            "start_index_store_unexplained_seconds"
        ],
        "terminal_path_start_index_store_unexplained_share": terminal_path[
            "start_index_store_unexplained_share"
        ],
        "terminal_path_start_index_store_sampled_event_count": terminal_path[
            "start_index_store_sampled_event_count"
        ],
        "terminal_path_start_index_store_covered_sampled_event_count": terminal_path[
            "start_index_store_covered_sampled_event_count"
        ],
        "terminal_path_start_index_store_unclassified_sampled_event_count": terminal_path[
            "start_index_store_unclassified_sampled_event_count"
        ],
        "terminal_path_start_index_store_multi_child_sampled_event_count": terminal_path[
            "start_index_store_multi_child_sampled_event_count"
        ],
        "terminal_path_start_index_store_insert_sampled_event_count": terminal_path[
            "start_index_store_insert_sampled_event_count"
        ],
        "terminal_path_start_index_store_clear_sampled_event_count": terminal_path[
            "start_index_store_clear_sampled_event_count"
        ],
        "terminal_path_start_index_store_overwrite_sampled_event_count": terminal_path[
            "start_index_store_overwrite_sampled_event_count"
        ],
        "terminal_path_start_index_store_sampled_count_closure_status": terminal_path[
            "start_index_store_sampled_count_closure_status"
        ],
        "terminal_path_start_index_store_dominant_child": terminal_path[
            "start_index_store_dominant_child"
        ],
        "terminal_path_start_index_store_coverage_share": terminal_path[
            "start_index_store_coverage_share"
        ],
        "terminal_path_start_index_store_unclassified_share": terminal_path[
            "start_index_store_unclassified_share"
        ],
        "terminal_path_start_index_store_multi_child_share": terminal_path[
            "start_index_store_multi_child_share"
        ],
        "terminal_path_start_index_store_insert_share": terminal_path[
            "start_index_store_insert_share"
        ],
        "terminal_path_start_index_store_clear_share": terminal_path[
            "start_index_store_clear_share"
        ],
        "terminal_path_start_index_store_overwrite_share": terminal_path[
            "start_index_store_overwrite_share"
        ],
        "terminal_path_start_index_store_insert_count": terminal_path[
            "start_index_store_insert_count"
        ],
        "terminal_path_start_index_store_clear_count": terminal_path[
            "start_index_store_clear_count"
        ],
        "terminal_path_start_index_store_overwrite_count": terminal_path[
            "start_index_store_overwrite_count"
        ],
        "terminal_path_start_index_store_insert_bytes": terminal_path[
            "start_index_store_insert_bytes"
        ],
        "terminal_path_start_index_store_clear_bytes": terminal_path[
            "start_index_store_clear_bytes"
        ],
        "terminal_path_start_index_store_overwrite_bytes": terminal_path[
            "start_index_store_overwrite_bytes"
        ],
        "terminal_path_start_index_store_unique_entry_count": terminal_path[
            "start_index_store_unique_entry_count"
        ],
        "terminal_path_start_index_store_unique_slot_count": terminal_path[
            "start_index_store_unique_slot_count"
        ],
        "terminal_path_start_index_store_unique_key_count": terminal_path[
            "start_index_store_unique_key_count"
        ],
        "terminal_path_start_index_store_same_entry_rewrite_count": terminal_path[
            "start_index_store_same_entry_rewrite_count"
        ],
        "terminal_path_start_index_store_same_cacheline_rewrite_count": terminal_path[
            "start_index_store_same_cacheline_rewrite_count"
        ],
        "terminal_path_start_index_store_back_to_back_same_entry_write_count": terminal_path[
            "start_index_store_back_to_back_same_entry_write_count"
        ],
        "terminal_path_start_index_store_clear_then_overwrite_same_entry_count": terminal_path[
            "start_index_store_clear_then_overwrite_same_entry_count"
        ],
        "terminal_path_start_index_store_overwrite_then_insert_same_entry_count": terminal_path[
            "start_index_store_overwrite_then_insert_same_entry_count"
        ],
        "terminal_path_start_index_store_insert_then_clear_same_entry_count": terminal_path[
            "start_index_store_insert_then_clear_same_entry_count"
        ],
        "terminal_path_start_index_store_clear_then_overwrite_same_entry_share": terminal_path[
            "start_index_store_clear_then_overwrite_same_entry_share"
        ],
    }
    timer_scope_status = (
        "closed"
        if candidate_index_timer_scope_status == "closed"
        and reuse_aux_other_timer_scope_status == "closed"
        and terminal_residual_status != "dominant"
        else "residual_unexplained"
    )
    metrics["timer_scope_status"] = timer_scope_status
    materiality_status = (
        "known" if initial_cpu_merge_share_of_sim_seconds is not None else "unknown"
    )
    next_action = recommended_next_action(metrics, args)

    return {
        "case_id": case_id,
        "aggregate_tsv": str(path),
        "workload_id": workload_id,
        "benchmark_source": benchmark_source,
        "profile_mode": metrics["profile_mode"],
        "terminal_telemetry_overhead_mode_requested": metrics[
            "terminal_telemetry_overhead_mode_requested"
        ],
        "terminal_telemetry_overhead_mode_effective": metrics[
            "terminal_telemetry_overhead_mode_effective"
        ],
        "state_update_bookkeeping_mode_requested": metrics[
            "state_update_bookkeeping_mode_requested"
        ],
        "state_update_bookkeeping_mode_effective": metrics[
            "state_update_bookkeeping_mode_effective"
        ],
        "context_apply_mean_seconds": context_apply_mean_seconds,
        "sim_initial_scan_cpu_merge_mean_seconds": sim_initial_scan_cpu_merge_seconds,
        "sim_seconds_mean_seconds": sim_seconds,
        "total_seconds_mean_seconds": total_seconds,
        "candidate_index_mean_seconds": candidate_index_mean_seconds,
        "candidate_index_share_of_initial_cpu_merge": candidate_index_share_of_initial_cpu_merge,
        "candidate_index_share_of_sim_seconds": candidate_index_share_of_sim_seconds,
        "candidate_index_share_of_total_seconds": candidate_index_share_of_total_seconds,
        "initial_cpu_merge_share_of_sim_seconds": initial_cpu_merge_share_of_sim_seconds,
        "initial_cpu_merge_share_of_total_seconds": initial_cpu_merge_share_of_total_seconds,
        "lookup_mean_seconds": lookup_mean_seconds,
        "lookup_hit_mean_seconds": lookup_hit_mean_seconds,
        "lookup_miss_mean_seconds": lookup_miss_mean_seconds,
        "lookup_miss_open_slot_mean_seconds": lookup_miss_open_slot_mean_seconds,
        "lookup_miss_candidate_set_full_probe_mean_seconds": lookup_miss_candidate_set_full_probe_mean_seconds,
        "lookup_miss_eviction_select_mean_seconds": lookup_miss_eviction_select_mean_seconds,
        "lookup_miss_reuse_writeback_mean_seconds": lookup_miss_reuse_writeback_mean_seconds,
        "candidate_index_erase_mean_seconds": candidate_index_erase_mean_seconds,
        "candidate_index_insert_mean_seconds": candidate_index_insert_mean_seconds,
        "lookup_miss_reuse_writeback_victim_reset_mean_seconds": lookup_miss_reuse_writeback_victim_reset_mean_seconds,
        "lookup_miss_reuse_writeback_key_rebind_mean_seconds": lookup_miss_reuse_writeback_key_rebind_mean_seconds,
        "lookup_miss_reuse_writeback_candidate_copy_mean_seconds": lookup_miss_reuse_writeback_candidate_copy_mean_seconds,
        "lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds": lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds,
        "lookup_miss_reuse_writeback_aux_heap_build_mean_seconds": lookup_miss_reuse_writeback_aux_heap_build_mean_seconds,
        "lookup_miss_reuse_writeback_aux_heap_update_mean_seconds": lookup_miss_reuse_writeback_aux_heap_update_mean_seconds,
        "lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds": lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds,
        "lookup_miss_reuse_writeback_aux_other_mean_seconds": lookup_miss_reuse_writeback_aux_other_mean_seconds,
        "lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds": lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds,
        "lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds": lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds,
        "lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds": lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds,
        "lookup_miss_reuse_writeback_aux_other_residual_mean_seconds": lookup_miss_reuse_writeback_aux_other_residual_mean_seconds,
        "lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds
        ),
        "candidate_index_lookup_count": candidate_index_lookup_count,
        "candidate_index_hit_count": candidate_index_hit_count,
        "candidate_index_miss_count": candidate_index_miss_count,
        "candidate_index_erase_count": candidate_index_erase_count,
        "candidate_index_insert_count": candidate_index_insert_count,
        "full_set_miss_count": full_set_miss_count,
        "candidate_index_scope_gap_seconds": candidate_index_scope_gap_seconds,
        "candidate_index_scope_gap_share_of_candidate_index": metrics[
            "candidate_index_scope_gap_share_of_candidate_index"
        ],
        "candidate_index_parent_seconds": metrics["candidate_index_parent_seconds"],
        "candidate_index_child_known_seconds": metrics["candidate_index_child_known_seconds"],
        "candidate_index_unexplained_seconds": metrics["candidate_index_unexplained_seconds"],
        "candidate_index_unexplained_share_of_candidate_index": metrics[
            "candidate_index_unexplained_share_of_candidate_index"
        ],
        "lookup_partition_gap_seconds": lookup_partition_gap_seconds,
        "lookup_partition_gap_share_of_candidate_index": metrics[
            "lookup_partition_gap_share_of_candidate_index"
        ],
        "lookup_miss_partition_gap_seconds": lookup_miss_partition_gap_seconds,
        "lookup_miss_partition_gap_share_of_candidate_index": metrics[
            "lookup_miss_partition_gap_share_of_candidate_index"
        ],
        "reuse_writeback_partition_gap_seconds": reuse_writeback_partition_gap_seconds,
        "reuse_writeback_partition_gap_share_of_candidate_index": metrics[
            "reuse_writeback_partition_gap_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_parent_seconds": metrics[
            "lookup_miss_reuse_writeback_parent_seconds"
        ],
        "lookup_miss_reuse_writeback_child_known_seconds": metrics[
            "lookup_miss_reuse_writeback_child_known_seconds"
        ],
        "lookup_miss_reuse_writeback_unexplained_seconds": metrics[
            "lookup_miss_reuse_writeback_unexplained_seconds"
        ],
        "lookup_miss_reuse_writeback_unexplained_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_unexplained_share_of_candidate_index"
        ],
        "aux_bookkeeping_partition_gap_seconds": aux_bookkeeping_partition_gap_seconds,
        "aux_bookkeeping_partition_gap_share_of_candidate_index": metrics[
            "aux_bookkeeping_partition_gap_share_of_candidate_index"
        ],
        "aux_other_partition_gap_seconds": aux_other_partition_gap_seconds,
        "aux_other_partition_gap_share_of_candidate_index": metrics[
            "aux_other_partition_gap_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_other_parent_seconds": metrics[
            "lookup_miss_reuse_writeback_aux_other_parent_seconds"
        ],
        "lookup_miss_reuse_writeback_aux_other_child_known_seconds": metrics[
            "lookup_miss_reuse_writeback_aux_other_child_known_seconds"
        ],
        "lookup_miss_reuse_writeback_aux_other_unexplained_seconds": metrics[
            "lookup_miss_reuse_writeback_aux_other_unexplained_seconds"
        ],
        "lookup_miss_reuse_writeback_aux_other_unexplained_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_aux_other_unexplained_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_parent_seconds": metrics[
            "lookup_miss_reuse_writeback_aux_other_residual_parent_seconds"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds": metrics[
            "lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds": metrics[
            "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_residual_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_aux_other_residual_residual_share_of_candidate_index"
        ],
        "lookup_hit_share_of_candidate_index": metrics["lookup_hit_share_of_candidate_index"],
        "lookup_miss_share_of_candidate_index": metrics["lookup_miss_share_of_candidate_index"],
        "lookup_miss_open_slot_share_of_candidate_index": metrics[
            "lookup_miss_open_slot_share_of_candidate_index"
        ],
        "lookup_miss_candidate_set_full_probe_share_of_candidate_index": metrics[
            "lookup_miss_candidate_set_full_probe_share_of_candidate_index"
        ],
        "lookup_miss_candidate_set_full_probe_parent_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_parent_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_scan_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_scan_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_compare_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_compare_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_branch_or_guard_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_branch_or_guard_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_bookkeeping_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_bookkeeping_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_child_known_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_child_known_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_unexplained_seconds": metrics[
            "lookup_miss_candidate_set_full_probe_unexplained_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_unexplained_share": metrics[
            "lookup_miss_candidate_set_full_probe_unexplained_share"
        ],
        "lookup_miss_candidate_set_full_probe_sampled_event_count": metrics[
            "lookup_miss_candidate_set_full_probe_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_covered_sampled_event_count": metrics[
            "lookup_miss_candidate_set_full_probe_covered_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count": metrics[
            "lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count": metrics[
            "lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": metrics[
            "lookup_miss_candidate_set_full_probe_sampled_count_closure_status"
        ],
        "lookup_miss_candidate_set_full_probe_dominant_child": metrics[
            "lookup_miss_candidate_set_full_probe_dominant_child"
        ],
        "lookup_miss_candidate_set_full_probe_coverage_share": metrics[
            "lookup_miss_candidate_set_full_probe_coverage_share"
        ],
        "lookup_miss_candidate_set_full_probe_unclassified_share": metrics[
            "lookup_miss_candidate_set_full_probe_unclassified_share"
        ],
        "lookup_miss_candidate_set_full_probe_multi_child_share": metrics[
            "lookup_miss_candidate_set_full_probe_multi_child_share"
        ],
        "lookup_miss_candidate_set_full_probe_scan_share": metrics[
            "lookup_miss_candidate_set_full_probe_scan_share"
        ],
        "lookup_miss_candidate_set_full_probe_compare_share": metrics[
            "lookup_miss_candidate_set_full_probe_compare_share"
        ],
        "lookup_miss_candidate_set_full_probe_branch_or_guard_share": metrics[
            "lookup_miss_candidate_set_full_probe_branch_or_guard_share"
        ],
        "lookup_miss_candidate_set_full_probe_bookkeeping_share": metrics[
            "lookup_miss_candidate_set_full_probe_bookkeeping_share"
        ],
        "lookup_miss_candidate_set_full_probe_count": metrics[
            "lookup_miss_candidate_set_full_probe_count"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_total": metrics[
            "lookup_miss_candidate_set_full_probe_slots_scanned_total"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean": metrics[
            "lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p50": metrics[
            "lookup_miss_candidate_set_full_probe_slots_scanned_p50"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p90": metrics[
            "lookup_miss_candidate_set_full_probe_slots_scanned_p90"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p99": metrics[
            "lookup_miss_candidate_set_full_probe_slots_scanned_p99"
        ],
        "lookup_miss_candidate_set_full_probe_full_scan_count": metrics[
            "lookup_miss_candidate_set_full_probe_full_scan_count"
        ],
        "lookup_miss_candidate_set_full_probe_early_exit_count": metrics[
            "lookup_miss_candidate_set_full_probe_early_exit_count"
        ],
        "lookup_miss_candidate_set_full_probe_found_existing_count": metrics[
            "lookup_miss_candidate_set_full_probe_found_existing_count"
        ],
        "lookup_miss_candidate_set_full_probe_confirmed_absent_count": metrics[
            "lookup_miss_candidate_set_full_probe_confirmed_absent_count"
        ],
        "lookup_miss_candidate_set_full_probe_redundant_reprobe_count": metrics[
            "lookup_miss_candidate_set_full_probe_redundant_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_same_key_reprobe_count": metrics[
            "lookup_miss_candidate_set_full_probe_same_key_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_same_event_reprobe_count": metrics[
            "lookup_miss_candidate_set_full_probe_same_event_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_full_scan_share": metrics[
            "lookup_miss_candidate_set_full_probe_full_scan_share"
        ],
        "lookup_miss_candidate_set_full_probe_early_exit_share": metrics[
            "lookup_miss_candidate_set_full_probe_early_exit_share"
        ],
        "lookup_miss_candidate_set_full_probe_found_existing_share": metrics[
            "lookup_miss_candidate_set_full_probe_found_existing_share"
        ],
        "lookup_miss_candidate_set_full_probe_confirmed_absent_share": metrics[
            "lookup_miss_candidate_set_full_probe_confirmed_absent_share"
        ],
        "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": metrics[
            "lookup_miss_candidate_set_full_probe_redundant_reprobe_share"
        ],
        "lookup_miss_eviction_select_share_of_candidate_index": metrics[
            "lookup_miss_eviction_select_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_share_of_candidate_index"
        ],
        "candidate_index_erase_share_of_candidate_index": metrics[
            "candidate_index_erase_share_of_candidate_index"
        ],
        "candidate_index_insert_share_of_candidate_index": metrics[
            "candidate_index_insert_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_start_index_rebuild_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_aux_start_index_rebuild_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_other_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_aux_other_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_share_of_candidate_index": metrics[
            "lookup_miss_reuse_writeback_aux_other_residual_share_of_candidate_index"
        ],
        "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index": terminal_residual_share_of_candidate_index,
        "terminal_path_scope": metrics["terminal_path_scope"],
        "terminal_path_parent_seconds": metrics["terminal_path_parent_seconds"],
        "terminal_path_child_known_seconds": metrics["terminal_path_child_known_seconds"],
        "terminal_path_candidate_slot_write_seconds": metrics[
            "terminal_path_candidate_slot_write_seconds"
        ],
        "terminal_path_start_index_write_seconds": metrics[
            "terminal_path_start_index_write_seconds"
        ],
        "terminal_path_state_update_seconds": metrics["terminal_path_state_update_seconds"],
        "terminal_path_state_update_parent_seconds": metrics[
            "terminal_path_state_update_parent_seconds"
        ],
        "terminal_path_state_update_heap_build_seconds": metrics[
            "terminal_path_state_update_heap_build_seconds"
        ],
        "terminal_path_state_update_heap_update_seconds": metrics[
            "terminal_path_state_update_heap_update_seconds"
        ],
        "terminal_path_state_update_start_index_rebuild_seconds": metrics[
            "terminal_path_state_update_start_index_rebuild_seconds"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_seconds": metrics[
            "terminal_path_state_update_trace_or_profile_bookkeeping_seconds"
        ],
        "terminal_path_state_update_child_known_seconds": metrics[
            "terminal_path_state_update_child_known_seconds"
        ],
        "terminal_path_state_update_unexplained_seconds": metrics[
            "terminal_path_state_update_unexplained_seconds"
        ],
        "terminal_path_state_update_unexplained_share": metrics[
            "terminal_path_state_update_unexplained_share"
        ],
        "terminal_path_state_update_sampled_event_count": metrics[
            "terminal_path_state_update_sampled_event_count"
        ],
        "terminal_path_state_update_covered_sampled_event_count": metrics[
            "terminal_path_state_update_covered_sampled_event_count"
        ],
        "terminal_path_state_update_unclassified_sampled_event_count": metrics[
            "terminal_path_state_update_unclassified_sampled_event_count"
        ],
        "terminal_path_state_update_multi_child_sampled_event_count": metrics[
            "terminal_path_state_update_multi_child_sampled_event_count"
        ],
        "terminal_path_state_update_heap_build_sampled_event_count": metrics[
            "terminal_path_state_update_heap_build_sampled_event_count"
        ],
        "terminal_path_state_update_heap_update_sampled_event_count": metrics[
            "terminal_path_state_update_heap_update_sampled_event_count"
        ],
        "terminal_path_state_update_start_index_rebuild_sampled_event_count": metrics[
            "terminal_path_state_update_start_index_rebuild_sampled_event_count"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count": metrics[
            "terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count"
        ],
        "terminal_path_state_update_sampled_count_closure_status": metrics[
            "terminal_path_state_update_sampled_count_closure_status"
        ],
        "terminal_path_state_update_coverage_source": metrics[
            "terminal_path_state_update_coverage_source"
        ],
        "terminal_path_state_update_timer_scope_status": metrics[
            "terminal_path_state_update_timer_scope_status"
        ],
        "terminal_path_state_update_dominant_child": metrics[
            "terminal_path_state_update_dominant_child"
        ],
        "terminal_path_state_update_coverage_share": metrics[
            "terminal_path_state_update_coverage_share"
        ],
        "terminal_path_state_update_unclassified_share": metrics[
            "terminal_path_state_update_unclassified_share"
        ],
        "terminal_path_state_update_multi_child_share": metrics[
            "terminal_path_state_update_multi_child_share"
        ],
        "terminal_path_state_update_heap_build_share": metrics[
            "terminal_path_state_update_heap_build_share"
        ],
        "terminal_path_state_update_heap_update_share": metrics[
            "terminal_path_state_update_heap_update_share"
        ],
        "terminal_path_state_update_start_index_rebuild_share": metrics[
            "terminal_path_state_update_start_index_rebuild_share"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_share": metrics[
            "terminal_path_state_update_trace_or_profile_bookkeeping_share"
        ],
        "terminal_path_telemetry_overhead_seconds": metrics[
            "terminal_path_telemetry_overhead_seconds"
        ],
        "terminal_path_residual_seconds": metrics["terminal_path_residual_seconds"],
        "terminal_path_candidate_slot_write_share_of_candidate_index": metrics[
            "terminal_path_candidate_slot_write_share_of_candidate_index"
        ],
        "terminal_path_start_index_write_share_of_candidate_index": metrics[
            "terminal_path_start_index_write_share_of_candidate_index"
        ],
        "terminal_path_state_update_share_of_candidate_index": metrics[
            "terminal_path_state_update_share_of_candidate_index"
        ],
        "terminal_path_telemetry_overhead_share_of_candidate_index": metrics[
            "terminal_path_telemetry_overhead_share_of_candidate_index"
        ],
        "terminal_path_residual_share_of_candidate_index": metrics[
            "terminal_path_residual_share_of_candidate_index"
        ],
        "terminal_path_event_count": metrics["terminal_path_event_count"],
        "terminal_path_candidate_slot_write_count": metrics[
            "terminal_path_candidate_slot_write_count"
        ],
        "terminal_path_start_index_write_count": metrics[
            "terminal_path_start_index_write_count"
        ],
        "terminal_path_state_update_count": metrics["terminal_path_state_update_count"],
        "terminal_path_state_update_event_count": metrics[
            "terminal_path_state_update_event_count"
        ],
        "terminal_path_state_update_heap_build_count": metrics[
            "terminal_path_state_update_heap_build_count"
        ],
        "terminal_path_state_update_heap_update_count": metrics[
            "terminal_path_state_update_heap_update_count"
        ],
        "terminal_path_state_update_start_index_rebuild_count": metrics[
            "terminal_path_state_update_start_index_rebuild_count"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_count": metrics[
            "terminal_path_state_update_trace_or_profile_bookkeeping_count"
        ],
        "terminal_path_state_update_aux_updates_total": metrics[
            "terminal_path_state_update_aux_updates_total"
        ],
        "production_state_update_parent_seconds": metrics[
            "production_state_update_parent_seconds"
        ],
        "production_state_update_benchmark_counter_seconds": metrics[
            "production_state_update_benchmark_counter_seconds"
        ],
        "production_state_update_trace_replay_required_state_seconds": metrics[
            "production_state_update_trace_replay_required_state_seconds"
        ],
        "production_state_update_child_known_seconds": metrics[
            "production_state_update_child_known_seconds"
        ],
        "production_state_update_unexplained_seconds": metrics[
            "production_state_update_unexplained_seconds"
        ],
        "production_state_update_unexplained_share": metrics[
            "production_state_update_unexplained_share"
        ],
        "production_state_update_sampled_event_count": metrics[
            "production_state_update_sampled_event_count"
        ],
        "production_state_update_covered_sampled_event_count": metrics[
            "production_state_update_covered_sampled_event_count"
        ],
        "production_state_update_unclassified_sampled_event_count": metrics[
            "production_state_update_unclassified_sampled_event_count"
        ],
        "production_state_update_multi_child_sampled_event_count": metrics[
            "production_state_update_multi_child_sampled_event_count"
        ],
        "production_state_update_benchmark_counter_sampled_event_count": metrics[
            "production_state_update_benchmark_counter_sampled_event_count"
        ],
        "production_state_update_trace_replay_required_state_sampled_event_count": metrics[
            "production_state_update_trace_replay_required_state_sampled_event_count"
        ],
        "production_state_update_sampled_count_closure_status": metrics[
            "production_state_update_sampled_count_closure_status"
        ],
        "production_state_update_coverage_source": metrics[
            "production_state_update_coverage_source"
        ],
        "production_state_update_timer_scope_status": metrics[
            "production_state_update_timer_scope_status"
        ],
        "production_state_update_dominant_child": metrics[
            "production_state_update_dominant_child"
        ],
        "production_state_update_coverage_share": metrics[
            "production_state_update_coverage_share"
        ],
        "production_state_update_unclassified_share": metrics[
            "production_state_update_unclassified_share"
        ],
        "production_state_update_multi_child_share": metrics[
            "production_state_update_multi_child_share"
        ],
        "production_state_update_benchmark_counter_share": metrics[
            "production_state_update_benchmark_counter_share"
        ],
        "production_state_update_trace_replay_required_state_share": metrics[
            "production_state_update_trace_replay_required_state_share"
        ],
        "production_state_update_share_of_candidate_index": metrics[
            "production_state_update_share_of_candidate_index"
        ],
        "production_state_update_event_count": metrics[
            "production_state_update_event_count"
        ],
        "production_state_update_benchmark_counter_count": metrics[
            "production_state_update_benchmark_counter_count"
        ],
        "production_state_update_trace_replay_required_state_count": metrics[
            "production_state_update_trace_replay_required_state_count"
        ],
        "terminal_path_candidate_bytes_written": metrics[
            "terminal_path_candidate_bytes_written"
        ],
        "terminal_path_start_index_bytes_written": metrics[
            "terminal_path_start_index_bytes_written"
        ],
        "terminal_path_dominant_child": metrics["terminal_path_dominant_child"],
        "terminal_path_start_index_write_parent_seconds": metrics[
            "terminal_path_start_index_write_parent_seconds"
        ],
        "terminal_path_start_index_write_left_seconds": metrics[
            "terminal_path_start_index_write_left_seconds"
        ],
        "terminal_path_start_index_write_right_seconds": metrics[
            "terminal_path_start_index_write_right_seconds"
        ],
        "terminal_path_start_index_write_child_known_seconds": metrics[
            "terminal_path_start_index_write_child_known_seconds"
        ],
        "terminal_path_start_index_write_unexplained_seconds": metrics[
            "terminal_path_start_index_write_unexplained_seconds"
        ],
        "terminal_path_start_index_write_unexplained_share": metrics[
            "terminal_path_start_index_write_unexplained_share"
        ],
        "terminal_path_start_index_write_sampled_event_count": metrics[
            "terminal_path_start_index_write_sampled_event_count"
        ],
        "terminal_path_start_index_write_covered_sampled_event_count": metrics[
            "terminal_path_start_index_write_covered_sampled_event_count"
        ],
        "terminal_path_start_index_write_unclassified_sampled_event_count": metrics[
            "terminal_path_start_index_write_unclassified_sampled_event_count"
        ],
        "terminal_path_start_index_write_multi_child_sampled_event_count": metrics[
            "terminal_path_start_index_write_multi_child_sampled_event_count"
        ],
        "terminal_path_start_index_write_left_sampled_event_count": metrics[
            "terminal_path_start_index_write_left_sampled_event_count"
        ],
        "terminal_path_start_index_write_right_sampled_event_count": metrics[
            "terminal_path_start_index_write_right_sampled_event_count"
        ],
        "terminal_path_start_index_write_sampled_count_closure_status": metrics[
            "terminal_path_start_index_write_sampled_count_closure_status"
        ],
        "terminal_path_start_index_write_dominant_child": metrics[
            "terminal_path_start_index_write_dominant_child"
        ],
        "terminal_path_start_index_write_coverage_share": metrics[
            "terminal_path_start_index_write_coverage_share"
        ],
        "terminal_path_start_index_write_unclassified_share": metrics[
            "terminal_path_start_index_write_unclassified_share"
        ],
        "terminal_path_start_index_write_multi_child_share": metrics[
            "terminal_path_start_index_write_multi_child_share"
        ],
        "terminal_path_start_index_write_probe_or_locate_share": metrics[
            "terminal_path_start_index_write_probe_or_locate_share"
        ],
        "terminal_path_start_index_write_entry_store_share": metrics[
            "terminal_path_start_index_write_entry_store_share"
        ],
        "terminal_path_start_index_write_insert_count": metrics[
            "terminal_path_start_index_write_insert_count"
        ],
        "terminal_path_start_index_write_update_existing_count": metrics[
            "terminal_path_start_index_write_update_existing_count"
        ],
        "terminal_path_start_index_write_clear_count": metrics[
            "terminal_path_start_index_write_clear_count"
        ],
        "terminal_path_start_index_write_overwrite_count": metrics[
            "terminal_path_start_index_write_overwrite_count"
        ],
        "terminal_path_start_index_write_idempotent_count": metrics[
            "terminal_path_start_index_write_idempotent_count"
        ],
        "terminal_path_start_index_write_value_changed_count": metrics[
            "terminal_path_start_index_write_value_changed_count"
        ],
        "terminal_path_start_index_write_probe_count": metrics[
            "terminal_path_start_index_write_probe_count"
        ],
        "terminal_path_start_index_write_probe_steps_total": metrics[
            "terminal_path_start_index_write_probe_steps_total"
        ],
        "terminal_path_start_index_store_parent_seconds": metrics[
            "terminal_path_start_index_store_parent_seconds"
        ],
        "terminal_path_start_index_store_insert_seconds": metrics[
            "terminal_path_start_index_store_insert_seconds"
        ],
        "terminal_path_start_index_store_clear_seconds": metrics[
            "terminal_path_start_index_store_clear_seconds"
        ],
        "terminal_path_start_index_store_overwrite_seconds": metrics[
            "terminal_path_start_index_store_overwrite_seconds"
        ],
        "terminal_path_start_index_store_child_known_seconds": metrics[
            "terminal_path_start_index_store_child_known_seconds"
        ],
        "terminal_path_start_index_store_unexplained_seconds": metrics[
            "terminal_path_start_index_store_unexplained_seconds"
        ],
        "terminal_path_start_index_store_unexplained_share": metrics[
            "terminal_path_start_index_store_unexplained_share"
        ],
        "terminal_path_start_index_store_sampled_event_count": metrics[
            "terminal_path_start_index_store_sampled_event_count"
        ],
        "terminal_path_start_index_store_covered_sampled_event_count": metrics[
            "terminal_path_start_index_store_covered_sampled_event_count"
        ],
        "terminal_path_start_index_store_unclassified_sampled_event_count": metrics[
            "terminal_path_start_index_store_unclassified_sampled_event_count"
        ],
        "terminal_path_start_index_store_multi_child_sampled_event_count": metrics[
            "terminal_path_start_index_store_multi_child_sampled_event_count"
        ],
        "terminal_path_start_index_store_insert_sampled_event_count": metrics[
            "terminal_path_start_index_store_insert_sampled_event_count"
        ],
        "terminal_path_start_index_store_clear_sampled_event_count": metrics[
            "terminal_path_start_index_store_clear_sampled_event_count"
        ],
        "terminal_path_start_index_store_overwrite_sampled_event_count": metrics[
            "terminal_path_start_index_store_overwrite_sampled_event_count"
        ],
        "terminal_path_start_index_store_sampled_count_closure_status": metrics[
            "terminal_path_start_index_store_sampled_count_closure_status"
        ],
        "terminal_path_start_index_store_dominant_child": metrics[
            "terminal_path_start_index_store_dominant_child"
        ],
        "terminal_path_start_index_store_coverage_share": metrics[
            "terminal_path_start_index_store_coverage_share"
        ],
        "terminal_path_start_index_store_unclassified_share": metrics[
            "terminal_path_start_index_store_unclassified_share"
        ],
        "terminal_path_start_index_store_multi_child_share": metrics[
            "terminal_path_start_index_store_multi_child_share"
        ],
        "terminal_path_start_index_store_insert_share": metrics[
            "terminal_path_start_index_store_insert_share"
        ],
        "terminal_path_start_index_store_clear_share": metrics[
            "terminal_path_start_index_store_clear_share"
        ],
        "terminal_path_start_index_store_overwrite_share": metrics[
            "terminal_path_start_index_store_overwrite_share"
        ],
        "terminal_path_start_index_store_insert_count": metrics[
            "terminal_path_start_index_store_insert_count"
        ],
        "terminal_path_start_index_store_clear_count": metrics[
            "terminal_path_start_index_store_clear_count"
        ],
        "terminal_path_start_index_store_overwrite_count": metrics[
            "terminal_path_start_index_store_overwrite_count"
        ],
        "terminal_path_start_index_store_insert_bytes": metrics[
            "terminal_path_start_index_store_insert_bytes"
        ],
        "terminal_path_start_index_store_clear_bytes": metrics[
            "terminal_path_start_index_store_clear_bytes"
        ],
        "terminal_path_start_index_store_overwrite_bytes": metrics[
            "terminal_path_start_index_store_overwrite_bytes"
        ],
        "terminal_path_start_index_store_unique_entry_count": metrics[
            "terminal_path_start_index_store_unique_entry_count"
        ],
        "terminal_path_start_index_store_unique_slot_count": metrics[
            "terminal_path_start_index_store_unique_slot_count"
        ],
        "terminal_path_start_index_store_unique_key_count": metrics[
            "terminal_path_start_index_store_unique_key_count"
        ],
        "terminal_path_start_index_store_same_entry_rewrite_count": metrics[
            "terminal_path_start_index_store_same_entry_rewrite_count"
        ],
        "terminal_path_start_index_store_same_cacheline_rewrite_count": metrics[
            "terminal_path_start_index_store_same_cacheline_rewrite_count"
        ],
        "terminal_path_start_index_store_back_to_back_same_entry_write_count": metrics[
            "terminal_path_start_index_store_back_to_back_same_entry_write_count"
        ],
        "terminal_path_start_index_store_clear_then_overwrite_same_entry_count": metrics[
            "terminal_path_start_index_store_clear_then_overwrite_same_entry_count"
        ],
        "terminal_path_start_index_store_overwrite_then_insert_same_entry_count": metrics[
            "terminal_path_start_index_store_overwrite_then_insert_same_entry_count"
        ],
        "terminal_path_start_index_store_insert_then_clear_same_entry_count": metrics[
            "terminal_path_start_index_store_insert_then_clear_same_entry_count"
        ],
        "terminal_path_start_index_store_clear_then_overwrite_same_entry_share": metrics[
            "terminal_path_start_index_store_clear_then_overwrite_same_entry_share"
        ],
        "terminal_lexical_parent_seconds": metrics["terminal_lexical_parent_seconds"],
        "terminal_span_first_half_seconds": metrics["terminal_span_first_half_seconds"],
        "terminal_span_second_half_seconds": metrics["terminal_span_second_half_seconds"],
        "terminal_first_half_parent_seconds": metrics["terminal_first_half_parent_seconds"],
        "terminal_first_half_span_a_seconds": metrics["terminal_first_half_span_a_seconds"],
        "terminal_first_half_span_b_seconds": metrics["terminal_first_half_span_b_seconds"],
        "terminal_first_half_child_known_seconds": metrics[
            "terminal_first_half_child_known_seconds"
        ],
        "terminal_first_half_unexplained_seconds": metrics[
            "terminal_first_half_unexplained_seconds"
        ],
        "dominant_terminal_span": metrics["dominant_terminal_span"],
        "dominant_terminal_first_half_span": metrics["dominant_terminal_first_half_span"],
        "timer_call_count": metrics["timer_call_count"],
        "terminal_timer_call_count": metrics["terminal_timer_call_count"],
        "lexical_timer_call_count": metrics["lexical_timer_call_count"],
        "intra_profile_closure_status": metrics["intra_profile_closure_status"],
        "profile_mode_overhead_status": metrics["profile_mode_overhead_status"],
        "candidate_index_materiality_status": metrics["candidate_index_materiality_status"],
        "terminal_timer_closure_status": metrics["terminal_timer_closure_status"],
        "lexical_span_closure_status": metrics["lexical_span_closure_status"],
        "profile_overhead_status": metrics["profile_overhead_status"],
        "candidate_index_timer_scope_status": candidate_index_timer_scope_status,
        "reuse_aux_other_timer_scope_status": reuse_aux_other_timer_scope_status,
        "terminal_residual_status": terminal_residual_status,
        "timer_scope_status": timer_scope_status,
        "materiality_status": ("known" if case_materiality_known else "unknown"),
        "recommended_next_action": next_action,
    }


def format_row(row):
    formatted = {}
    for key, value in row.items():
        if value is None:
            formatted[key] = ""
        elif isinstance(value, float):
            formatted[key] = f"{value:.6f}"
        else:
            formatted[key] = value
    return formatted


def write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def aggregate_summary(rows, args):
    candidate_index_seconds = sum(row["candidate_index_mean_seconds"] for row in rows)
    context_apply_seconds = sum(row["context_apply_mean_seconds"] for row in rows)
    pairing = evaluate_materiality_pairing(rows)
    pairing_groups = pairing["groups"]
    if pairing["status"] in {"complete", "duplicate_grouped"}:
        sim_initial_scan_cpu_merge_seconds = grouped_metric_from_pairing(
            pairing_groups, "sim_initial_scan_cpu_merge_mean_seconds"
        )
        sim_seconds = grouped_metric_from_pairing(pairing_groups, "sim_seconds_mean_seconds")
        total_seconds = grouped_metric_from_pairing(pairing_groups, "total_seconds_mean_seconds")
    else:
        sim_initial_scan_cpu_merge_seconds = None
        sim_seconds = None
        total_seconds = None

    candidate_index_share_of_initial_cpu_merge = share(
        candidate_index_seconds, context_apply_seconds
    )
    initial_cpu_merge_share_of_sim_seconds = (
        share(sim_initial_scan_cpu_merge_seconds, sim_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and sim_seconds is not None
        else None
    )
    initial_cpu_merge_share_of_total_seconds = (
        share(sim_initial_scan_cpu_merge_seconds, total_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and total_seconds is not None
        else None
    )
    candidate_index_share_of_sim_seconds = (
        candidate_index_share_of_initial_cpu_merge * initial_cpu_merge_share_of_sim_seconds
        if initial_cpu_merge_share_of_sim_seconds is not None
        else None
    )
    candidate_index_share_of_total_seconds = (
        candidate_index_share_of_initial_cpu_merge * initial_cpu_merge_share_of_total_seconds
        if initial_cpu_merge_share_of_total_seconds is not None
        else None
    )

    def sum_key(key):
        return sum(row[key] for row in rows)

    def sum_optional_key(key):
        values = [row[key] for row in rows if row.get(key) is not None]
        if not values:
            return None
        return sum(values)

    lookup_seconds = sum_key("lookup_mean_seconds")
    lookup_hit_seconds = sum_key("lookup_hit_mean_seconds")
    lookup_miss_seconds = sum_key("lookup_miss_mean_seconds")
    lookup_miss_open_slot_seconds = sum_key("lookup_miss_open_slot_mean_seconds")
    lookup_miss_candidate_set_full_probe_seconds = sum_key(
        "lookup_miss_candidate_set_full_probe_mean_seconds"
    )
    lookup_miss_eviction_select_seconds = sum_key(
        "lookup_miss_eviction_select_mean_seconds"
    )
    lookup_miss_reuse_writeback_seconds = sum_key(
        "lookup_miss_reuse_writeback_mean_seconds"
    )
    candidate_index_erase_seconds = sum_key("candidate_index_erase_mean_seconds")
    candidate_index_insert_seconds = sum_key("candidate_index_insert_mean_seconds")
    lookup_miss_reuse_writeback_victim_reset_seconds = sum_key(
        "lookup_miss_reuse_writeback_victim_reset_mean_seconds"
    )
    lookup_miss_reuse_writeback_key_rebind_seconds = sum_key(
        "lookup_miss_reuse_writeback_key_rebind_mean_seconds"
    )
    lookup_miss_reuse_writeback_candidate_copy_seconds = sum_key(
        "lookup_miss_reuse_writeback_candidate_copy_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_bookkeeping_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_heap_build_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_heap_build_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_heap_update_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_heap_update_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_other_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_residual_seconds = sum_key(
        "lookup_miss_reuse_writeback_aux_other_residual_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds = sum_optional_key(
        "lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds = sum_optional_key(
        "lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds = sum_optional_key(
        "lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds"
    )
    lookup_miss_reuse_writeback_aux_other_residual_residual_seconds = sum_optional_key(
        "lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds"
    )
    aggregate_aux_other_residual_components_present = any(
        value is not None
        for value in (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds,
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds,
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds,
            lookup_miss_reuse_writeback_aux_other_residual_residual_seconds,
        )
    )
    if not aggregate_aux_other_residual_components_present:
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds = 0.0
        lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds = 0.0
        lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds = 0.0
        lookup_miss_reuse_writeback_aux_other_residual_residual_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_seconds
        )
    else:
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds or 0.0
        )
        lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds or 0.0
        )
        lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds or 0.0
        )
        lookup_miss_reuse_writeback_aux_other_residual_residual_seconds = (
            lookup_miss_reuse_writeback_aux_other_residual_residual_seconds or 0.0
        )
    full_probe_metrics = derive_lookup_miss_candidate_set_full_probe_metrics(
        fallback_parent_seconds=lookup_miss_candidate_set_full_probe_seconds,
        split_parent_seconds=sum_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_parent_seconds"
        ),
        scan_seconds=sum_optional_rows(rows, "lookup_miss_candidate_set_full_probe_scan_seconds"),
        compare_seconds=sum_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_compare_seconds"
        ),
        branch_or_guard_seconds=sum_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_branch_or_guard_seconds"
        ),
        bookkeeping_seconds=sum_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_bookkeeping_seconds"
        ),
        child_known_seconds=sum_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_child_known_seconds"
        ),
        unexplained_seconds=sum_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_unexplained_seconds"
        ),
        sampled_event_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_sampled_event_count"
        ),
        covered_sampled_event_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_covered_sampled_event_count"
        ),
        unclassified_sampled_event_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count"
        ),
        multi_child_sampled_event_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count"
        ),
        full_probe_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_count"
        ),
        slots_scanned_total=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_slots_scanned_total"
        ),
        slots_scanned_per_probe_mean=None,
        slots_scanned_p50=max_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_slots_scanned_p50"
        ),
        slots_scanned_p90=max_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_slots_scanned_p90"
        ),
        slots_scanned_p99=max_optional_rows(
            rows, "lookup_miss_candidate_set_full_probe_slots_scanned_p99"
        ),
        full_scan_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_full_scan_count"
        ),
        early_exit_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_early_exit_count"
        ),
        found_existing_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_found_existing_count"
        ),
        confirmed_absent_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_confirmed_absent_count"
        ),
        redundant_reprobe_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_redundant_reprobe_count"
        ),
        same_key_reprobe_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_same_key_reprobe_count"
        ),
        same_event_reprobe_count=sum_optional_int_rows(
            rows, "lookup_miss_candidate_set_full_probe_same_event_reprobe_count"
        ),
    )

    candidate_index_scope_gap_seconds = abs(candidate_index_seconds - lookup_seconds)
    lookup_partition_gap_seconds = abs(lookup_seconds - (lookup_hit_seconds + lookup_miss_seconds))
    lookup_miss_partition_gap_seconds = abs(
        lookup_miss_seconds
        - (
            lookup_miss_open_slot_seconds
            + lookup_miss_candidate_set_full_probe_seconds
            + lookup_miss_eviction_select_seconds
            + lookup_miss_reuse_writeback_seconds
        )
    )
    reuse_writeback_partition_gap_seconds = abs(
        lookup_miss_reuse_writeback_seconds
        - (
            lookup_miss_reuse_writeback_victim_reset_seconds
            + lookup_miss_reuse_writeback_key_rebind_seconds
            + lookup_miss_reuse_writeback_candidate_copy_seconds
            + lookup_miss_reuse_writeback_aux_bookkeeping_seconds
        )
    )
    aux_bookkeeping_partition_gap_seconds = abs(
        lookup_miss_reuse_writeback_aux_bookkeeping_seconds
        - (
            lookup_miss_reuse_writeback_aux_heap_build_seconds
            + lookup_miss_reuse_writeback_aux_heap_update_seconds
            + lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds
            + lookup_miss_reuse_writeback_aux_other_seconds
        )
    )
    aux_other_partition_gap_seconds = abs(
        lookup_miss_reuse_writeback_aux_other_seconds
        - (
            lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_seconds
        )
    )
    candidate_index_timer_scope_status = "closed"
    if (
        max(
            share(candidate_index_scope_gap_seconds, candidate_index_seconds),
            share(lookup_partition_gap_seconds, candidate_index_seconds),
            share(lookup_miss_partition_gap_seconds, candidate_index_seconds),
        )
        >= args.timer_scope_gap_threshold
    ):
        candidate_index_timer_scope_status = "residual_unexplained"
    reuse_aux_other_timer_scope_status = "closed"
    if (
        max(
            share(reuse_writeback_partition_gap_seconds, candidate_index_seconds),
            share(aux_bookkeeping_partition_gap_seconds, candidate_index_seconds),
            share(aux_other_partition_gap_seconds, candidate_index_seconds),
        )
        >= args.timer_scope_gap_threshold
    ):
        reuse_aux_other_timer_scope_status = "residual_unexplained"
    terminal_residual_share_of_candidate_index = share(
        lookup_miss_reuse_writeback_aux_other_residual_residual_seconds,
        candidate_index_seconds,
    )
    terminal_residual_status = (
        "dominant"
        if terminal_residual_share_of_candidate_index
        >= args.terminal_residual_dominant_share_threshold
        else "minor"
    )
    terminal_lexical_parent_seconds = sum_optional_rows(rows, "terminal_lexical_parent_seconds")
    terminal_span_first_half_seconds = sum_optional_rows(rows, "terminal_span_first_half_seconds")
    terminal_span_second_half_seconds = sum_optional_rows(rows, "terminal_span_second_half_seconds")
    terminal_first_half_parent_seconds = sum_optional_rows(rows, "terminal_first_half_parent_seconds")
    terminal_first_half_span_a_seconds = sum_optional_rows(rows, "terminal_first_half_span_a_seconds")
    terminal_first_half_span_b_seconds = sum_optional_rows(rows, "terminal_first_half_span_b_seconds")
    terminal_first_half_child_known_seconds = sum_optional_rows(
        rows, "terminal_first_half_child_known_seconds"
    )
    terminal_first_half_unexplained_seconds = sum_optional_rows(
        rows, "terminal_first_half_unexplained_seconds"
    )
    dominant_terminal_span = dominant_terminal_span_label(
        terminal_span_first_half_seconds,
        terminal_span_second_half_seconds,
    )
    dominant_terminal_first_half_span = dominant_terminal_first_half_span_label(
        terminal_first_half_span_a_seconds,
        terminal_first_half_span_b_seconds,
    )
    intra_profile_closure_status = classify_intra_profile_closure_status(
        terminal_lexical_parent_seconds,
        terminal_span_first_half_seconds,
        terminal_span_second_half_seconds,
    )
    profile_mode_overhead_status = classify_profile_mode_overhead_status(
        intra_profile_closure_status
    )
    aggregate_state_update_coverage_source = (
        "event_level_sampled"
        if any(
            resolve_optional_text(row, "terminal_path_state_update_coverage_source")
            == "event_level_sampled"
            for row in rows
        )
        else "placeholder"
    )
    aggregate_production_state_update_coverage_source = (
        "event_level_sampled"
        if any(
            resolve_optional_text(row, "production_state_update_coverage_source")
            == "event_level_sampled"
            for row in rows
        )
        else "placeholder"
    )
    aggregate_terminal_row = {
        "context_apply_lookup_miss_reuse_writeback_terminal_parent_mean_seconds": sum_optional_rows(
            rows, "terminal_path_parent_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_child_known_mean_seconds": sum_optional_rows(
            rows, "terminal_path_child_known_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_mean_seconds": sum_optional_rows(
            rows, "terminal_path_candidate_slot_write_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_write_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_parent_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_heap_build_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_heap_update_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_start_index_rebuild_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_trace_or_profile_bookkeeping_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_child_known_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_mean_seconds": sum_optional_rows(
            rows, "terminal_path_state_update_unexplained_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_mean_seconds": sum_optional_rows(
            rows, "terminal_path_telemetry_overhead_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_residual_mean_seconds": sum_optional_rows(
            rows, "terminal_path_residual_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_event_count": sum_optional_int_rows(
            rows, "terminal_path_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_count": sum_optional_int_rows(
            rows, "terminal_path_candidate_slot_write_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_heap_build_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_heap_update_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_start_index_rebuild_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_trace_or_profile_bookkeeping_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_aux_updates_total": sum_optional_int_rows(
            rows, "terminal_path_state_update_aux_updates_total"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_covered_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_unclassified_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_multi_child_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_multi_child_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_heap_build_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_heap_update_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_start_index_rebuild_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source": (
            aggregate_state_update_coverage_source
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_mean_seconds": sum_optional_rows(
            rows, "production_state_update_parent_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_mean_seconds": sum_optional_rows(
            rows, "production_state_update_parent_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_mean_seconds": sum_optional_rows(
            rows, "production_state_update_benchmark_counter_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_mean_seconds": sum_optional_rows(
            rows, "production_state_update_trace_replay_required_state_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_mean_seconds": sum_optional_rows(
            rows, "production_state_update_child_known_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_mean_seconds": sum_optional_rows(
            rows, "production_state_update_unexplained_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_sampled_event_count": sum_optional_int_rows(
            rows, "production_state_update_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_covered_sampled_event_count": sum_optional_int_rows(
            rows, "production_state_update_covered_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unclassified_sampled_event_count": sum_optional_int_rows(
            rows, "production_state_update_unclassified_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_multi_child_sampled_event_count": sum_optional_int_rows(
            rows, "production_state_update_multi_child_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_sampled_event_count": sum_optional_int_rows(
            rows, "production_state_update_benchmark_counter_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_sampled_event_count": sum_optional_int_rows(
            rows, "production_state_update_trace_replay_required_state_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_event_count": sum_optional_int_rows(
            rows, "production_state_update_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_count": sum_optional_int_rows(
            rows, "production_state_update_benchmark_counter_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_count": sum_optional_int_rows(
            rows, "production_state_update_trace_replay_required_state_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_production_state_update_coverage_source": (
            aggregate_production_state_update_coverage_source
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_candidate_bytes_written": sum_optional_int_rows(
            rows, "terminal_path_candidate_bytes_written"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_bytes_written": sum_optional_int_rows(
            rows, "terminal_path_start_index_bytes_written"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_write_parent_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_write_left_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_write_right_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_write_child_known_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_write_unexplained_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_covered_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_covered_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unclassified_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_unclassified_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_multi_child_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_multi_child_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_left_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_right_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_insert_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_insert_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_update_existing_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_update_existing_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_clear_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_clear_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_overwrite_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_overwrite_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_idempotent_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_idempotent_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_value_changed_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_value_changed_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_probe_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_steps_total": sum_optional_int_rows(
            rows, "terminal_path_start_index_write_probe_steps_total"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_store_parent_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_store_insert_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_store_clear_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_store_overwrite_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_store_child_known_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_mean_seconds": sum_optional_rows(
            rows, "terminal_path_start_index_store_unexplained_seconds"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_covered_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_covered_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unclassified_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_unclassified_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_multi_child_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_multi_child_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_insert_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_clear_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_sampled_event_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_overwrite_sampled_event_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_insert_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_clear_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_overwrite_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_bytes": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_insert_bytes"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_bytes": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_clear_bytes"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_bytes": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_overwrite_bytes"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_entry_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_unique_entry_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_slot_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_unique_slot_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_key_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_unique_key_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_entry_rewrite_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_same_entry_rewrite_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_cacheline_rewrite_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_same_cacheline_rewrite_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_back_to_back_same_entry_write_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_back_to_back_same_entry_write_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_then_overwrite_same_entry_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_clear_then_overwrite_same_entry_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_then_insert_same_entry_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_overwrite_then_insert_same_entry_count"
        ),
        "context_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_then_clear_same_entry_count": sum_optional_int_rows(
            rows, "terminal_path_start_index_store_insert_then_clear_same_entry_count"
        ),
    }
    aggregate_terminal_row = {
        key: value for key, value in aggregate_terminal_row.items() if value is not None
    }
    terminal_path = derive_terminal_path_metrics(
        aggregate_terminal_row,
        candidate_index_seconds=candidate_index_seconds,
        state_update_unexplained_threshold=args.state_update_unexplained_threshold,
        full_set_miss_count=sum_key("full_set_miss_count"),
        lookup_miss_reuse_writeback_key_rebind_seconds=(
            lookup_miss_reuse_writeback_key_rebind_seconds
        ),
        lookup_miss_reuse_writeback_candidate_copy_seconds=(
            lookup_miss_reuse_writeback_candidate_copy_seconds
        ),
        lookup_miss_reuse_writeback_aux_bookkeeping_seconds=(
            lookup_miss_reuse_writeback_aux_bookkeeping_seconds
        ),
        lookup_miss_reuse_writeback_aux_heap_build_seconds=(
            lookup_miss_reuse_writeback_aux_heap_build_seconds
        ),
        lookup_miss_reuse_writeback_aux_heap_update_seconds=(
            lookup_miss_reuse_writeback_aux_heap_update_seconds
        ),
        lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds=(
            lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds=(
            lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds=(
            lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds=(
            lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds
        ),
        lookup_miss_reuse_writeback_aux_other_residual_residual_seconds=(
            lookup_miss_reuse_writeback_aux_other_residual_residual_seconds
        ),
    )
    terminal_timer_closure_status = classify_timer_closure_status(
        terminal_path["parent_seconds"],
        terminal_path["child_known_seconds"],
        args.timer_scope_gap_threshold,
    )
    start_index_store_case_dominance = aggregate_start_index_store_case_dominance(rows)
    start_index_store_case_weighted_dominant_child = start_index_store_case_dominance[
        "case_weighted_dominant_child"
    ]
    start_index_store_case_majority_share = start_index_store_case_dominance[
        "case_majority_share"
    ]
    start_index_store_event_weighted_dominant_child = start_index_store_case_dominance[
        "event_weighted_dominant_child"
    ]
    start_index_store_seconds_weighted_dominant_child = terminal_path[
        "start_index_store_dominant_child"
    ]
    start_index_store_margin_share = start_index_store_child_margin_share(
        terminal_path["start_index_store_insert_seconds"],
        terminal_path["start_index_store_clear_seconds"],
        terminal_path["start_index_store_overwrite_seconds"],
        terminal_path["start_index_store_parent_seconds"],
    )
    start_index_store_dominance_status = classify_start_index_store_dominance(
        case_weighted_dominant_child=start_index_store_case_weighted_dominant_child,
        seconds_weighted_dominant_child=start_index_store_seconds_weighted_dominant_child,
        child_margin_share=start_index_store_margin_share,
        child_margin_threshold=args.start_index_store_child_margin_threshold,
    )
    production_state_update_case_dominance = aggregate_production_state_update_case_dominance(
        rows
    )
    production_state_update_case_weighted_dominant_child = (
        production_state_update_case_dominance["case_weighted_dominant_child"]
    )
    production_state_update_case_majority_share = production_state_update_case_dominance[
        "case_majority_share"
    ]
    production_state_update_event_weighted_dominant_child = (
        production_state_update_case_dominance["event_weighted_dominant_child"]
    )
    production_state_update_seconds_weighted_dominant_child = terminal_path[
        "production_state_update_dominant_child"
    ]
    production_state_update_margin_share = production_state_update_child_margin_share(
        terminal_path["production_state_update_benchmark_counter_seconds"],
        terminal_path["production_state_update_trace_replay_required_state_seconds"],
        terminal_path["production_state_update_parent_seconds"],
    )
    production_state_update_dominance_status = classify_production_state_update_dominance(
        case_weighted_dominant_child=production_state_update_case_weighted_dominant_child,
        seconds_weighted_dominant_child=production_state_update_seconds_weighted_dominant_child,
        child_margin_share=production_state_update_margin_share,
        child_margin_threshold=args.state_update_child_margin_threshold,
    )
    lexical_span_closure_status = (
        "closed"
        if intra_profile_closure_status == "ok"
        else (
            "unknown"
            if intra_profile_closure_status == "unknown"
            else "residual_unexplained"
        )
    )
    candidate_index_materiality_status = classify_candidate_index_materiality_status(
        initial_cpu_merge_share_of_sim_seconds,
        candidate_index_share_of_sim_seconds,
        host_merge_materiality_threshold=args.host_merge_materiality_threshold,
        candidate_index_materiality_threshold=args.candidate_index_materiality_threshold,
    )

    candidate_index = {
        "profile_mode": consistent_optional_text(rows, "profile_mode"),
        "terminal_telemetry_overhead_mode_requested": consistent_optional_text(
            rows, "terminal_telemetry_overhead_mode_requested"
        ),
        "terminal_telemetry_overhead_mode_effective": consistent_optional_text(
            rows, "terminal_telemetry_overhead_mode_effective"
        ),
        "state_update_bookkeeping_mode_requested": consistent_optional_text(
            rows, "state_update_bookkeeping_mode_requested"
        ),
        "state_update_bookkeeping_mode_effective": consistent_optional_text(
            rows, "state_update_bookkeeping_mode_effective"
        ),
        "seconds": candidate_index_seconds,
        "share_of_initial_cpu_merge": candidate_index_share_of_initial_cpu_merge,
        "share_of_sim_seconds": candidate_index_share_of_sim_seconds,
        "share_of_total_seconds": candidate_index_share_of_total_seconds,
        "aux_other_share_of_sim_seconds": (
            share(lookup_miss_reuse_writeback_aux_other_seconds, candidate_index_seconds)
            * candidate_index_share_of_sim_seconds
            if candidate_index_share_of_sim_seconds is not None
            else None
        ),
        "candidate_index_unexplained_share_of_sim_seconds": (
            share(candidate_index_scope_gap_seconds, candidate_index_seconds)
            * candidate_index_share_of_sim_seconds
            if candidate_index_share_of_sim_seconds is not None
            else None
        ),
        "lookup_seconds": lookup_seconds,
        "lookup_hit_seconds": lookup_hit_seconds,
        "lookup_miss_seconds": lookup_miss_seconds,
        "lookup_miss_open_slot_seconds": lookup_miss_open_slot_seconds,
        "lookup_miss_candidate_set_full_probe_seconds": lookup_miss_candidate_set_full_probe_seconds,
        "lookup_miss_eviction_select_seconds": lookup_miss_eviction_select_seconds,
        "lookup_miss_reuse_writeback_seconds": lookup_miss_reuse_writeback_seconds,
        "erase_seconds": candidate_index_erase_seconds,
        "insert_seconds": candidate_index_insert_seconds,
        "lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds": lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds,
        "lookup_miss_reuse_writeback_aux_other_seconds": lookup_miss_reuse_writeback_aux_other_seconds,
        "lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds": lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds,
        "lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds": lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds,
        "lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds": lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds,
        "lookup_miss_reuse_writeback_aux_other_residual_seconds": lookup_miss_reuse_writeback_aux_other_residual_seconds,
        "lookup_count": sum_key("candidate_index_lookup_count"),
        "hit_count": sum_key("candidate_index_hit_count"),
        "miss_count": sum_key("candidate_index_miss_count"),
        "erase_count": sum_key("candidate_index_erase_count"),
        "insert_count": sum_key("candidate_index_insert_count"),
        "lookup_hit_share_of_candidate_index": share(lookup_hit_seconds, candidate_index_seconds),
        "lookup_miss_share_of_candidate_index": share(
            lookup_miss_seconds, candidate_index_seconds
        ),
        "lookup_miss_open_slot_share_of_candidate_index": share(
            lookup_miss_open_slot_seconds, candidate_index_seconds
        ),
        "lookup_miss_candidate_set_full_probe_share_of_candidate_index": share(
            lookup_miss_candidate_set_full_probe_seconds, candidate_index_seconds
        ),
        "lookup_miss_candidate_set_full_probe_parent_seconds": full_probe_metrics[
            "parent_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_scan_seconds": full_probe_metrics[
            "scan_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_compare_seconds": full_probe_metrics[
            "compare_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_branch_or_guard_seconds": full_probe_metrics[
            "branch_or_guard_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_bookkeeping_seconds": full_probe_metrics[
            "bookkeeping_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_child_known_seconds": full_probe_metrics[
            "child_known_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_unexplained_seconds": full_probe_metrics[
            "unexplained_seconds"
        ],
        "lookup_miss_candidate_set_full_probe_unexplained_share": full_probe_metrics[
            "unexplained_share"
        ],
        "lookup_miss_candidate_set_full_probe_sampled_event_count": full_probe_metrics[
            "sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_covered_sampled_event_count": full_probe_metrics[
            "covered_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count": full_probe_metrics[
            "unclassified_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count": full_probe_metrics[
            "multi_child_sampled_event_count"
        ],
        "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": full_probe_metrics[
            "sampled_count_closure_status"
        ],
        "lookup_miss_candidate_set_full_probe_dominant_child": full_probe_metrics[
            "dominant_child"
        ],
        "lookup_miss_candidate_set_full_probe_coverage_share": full_probe_metrics[
            "coverage_share"
        ],
        "lookup_miss_candidate_set_full_probe_unclassified_share": full_probe_metrics[
            "unclassified_share"
        ],
        "lookup_miss_candidate_set_full_probe_multi_child_share": full_probe_metrics[
            "multi_child_share"
        ],
        "lookup_miss_candidate_set_full_probe_scan_share": full_probe_metrics[
            "scan_share"
        ],
        "lookup_miss_candidate_set_full_probe_compare_share": full_probe_metrics[
            "compare_share"
        ],
        "lookup_miss_candidate_set_full_probe_branch_or_guard_share": full_probe_metrics[
            "branch_or_guard_share"
        ],
        "lookup_miss_candidate_set_full_probe_bookkeeping_share": full_probe_metrics[
            "bookkeeping_share"
        ],
        "lookup_miss_candidate_set_full_probe_count": full_probe_metrics["count"],
        "lookup_miss_candidate_set_full_probe_slots_scanned_total": full_probe_metrics[
            "slots_scanned_total"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean": full_probe_metrics[
            "slots_scanned_per_probe_mean"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p50": full_probe_metrics[
            "slots_scanned_p50"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p90": full_probe_metrics[
            "slots_scanned_p90"
        ],
        "lookup_miss_candidate_set_full_probe_slots_scanned_p99": full_probe_metrics[
            "slots_scanned_p99"
        ],
        "lookup_miss_candidate_set_full_probe_full_scan_count": full_probe_metrics[
            "full_scan_count"
        ],
        "lookup_miss_candidate_set_full_probe_early_exit_count": full_probe_metrics[
            "early_exit_count"
        ],
        "lookup_miss_candidate_set_full_probe_found_existing_count": full_probe_metrics[
            "found_existing_count"
        ],
        "lookup_miss_candidate_set_full_probe_confirmed_absent_count": full_probe_metrics[
            "confirmed_absent_count"
        ],
        "lookup_miss_candidate_set_full_probe_redundant_reprobe_count": full_probe_metrics[
            "redundant_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_same_key_reprobe_count": full_probe_metrics[
            "same_key_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_same_event_reprobe_count": full_probe_metrics[
            "same_event_reprobe_count"
        ],
        "lookup_miss_candidate_set_full_probe_full_scan_share": full_probe_metrics[
            "full_scan_share"
        ],
        "lookup_miss_candidate_set_full_probe_early_exit_share": full_probe_metrics[
            "early_exit_share"
        ],
        "lookup_miss_candidate_set_full_probe_found_existing_share": full_probe_metrics[
            "found_existing_share"
        ],
        "lookup_miss_candidate_set_full_probe_confirmed_absent_share": full_probe_metrics[
            "confirmed_absent_share"
        ],
        "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": full_probe_metrics[
            "redundant_reprobe_share"
        ],
        "lookup_miss_eviction_select_share_of_candidate_index": share(
            lookup_miss_eviction_select_seconds, candidate_index_seconds
        ),
        "lookup_miss_reuse_writeback_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_seconds, candidate_index_seconds
        ),
        "erase_share_of_candidate_index": share(
            candidate_index_erase_seconds, candidate_index_seconds
        ),
        "insert_share_of_candidate_index": share(
            candidate_index_insert_seconds, candidate_index_seconds
        ),
        "lookup_miss_reuse_writeback_aux_start_index_rebuild_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds,
            candidate_index_seconds,
        ),
        "lookup_miss_reuse_writeback_aux_other_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_seconds, candidate_index_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_residual_seconds,
            candidate_index_seconds,
        ),
        "parent_seconds": candidate_index_seconds,
        "child_known_seconds": lookup_seconds,
        "unexplained_seconds": candidate_index_scope_gap_seconds,
        "unexplained_share_of_candidate_index": share(
            candidate_index_scope_gap_seconds, candidate_index_seconds
        ),
        "candidate_index_scope_gap_seconds": candidate_index_scope_gap_seconds,
        "candidate_index_scope_gap_share_of_candidate_index": share(
            candidate_index_scope_gap_seconds, candidate_index_seconds
        ),
        "lookup_partition_gap_seconds": lookup_partition_gap_seconds,
        "lookup_partition_gap_share_of_candidate_index": share(
            lookup_partition_gap_seconds, candidate_index_seconds
        ),
        "lookup_miss_partition_gap_seconds": lookup_miss_partition_gap_seconds,
        "lookup_miss_partition_gap_share_of_candidate_index": share(
            lookup_miss_partition_gap_seconds, candidate_index_seconds
        ),
        "reuse_writeback_partition_gap_seconds": reuse_writeback_partition_gap_seconds,
        "reuse_writeback_partition_gap_share_of_candidate_index": share(
            reuse_writeback_partition_gap_seconds, candidate_index_seconds
        ),
        "lookup_miss_reuse_writeback_parent_seconds": lookup_miss_reuse_writeback_seconds,
        "lookup_miss_reuse_writeback_child_known_seconds": (
            lookup_miss_reuse_writeback_victim_reset_seconds
            + lookup_miss_reuse_writeback_key_rebind_seconds
            + lookup_miss_reuse_writeback_candidate_copy_seconds
            + lookup_miss_reuse_writeback_aux_bookkeeping_seconds
        ),
        "lookup_miss_reuse_writeback_unexplained_seconds": reuse_writeback_partition_gap_seconds,
        "lookup_miss_reuse_writeback_unexplained_share_of_candidate_index": share(
            reuse_writeback_partition_gap_seconds, candidate_index_seconds
        ),
        "aux_bookkeeping_partition_gap_seconds": aux_bookkeeping_partition_gap_seconds,
        "aux_bookkeeping_partition_gap_share_of_candidate_index": share(
            aux_bookkeeping_partition_gap_seconds, candidate_index_seconds
        ),
        "aux_other_partition_gap_seconds": aux_other_partition_gap_seconds,
        "aux_other_partition_gap_share_of_candidate_index": share(
            aux_other_partition_gap_seconds, candidate_index_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_parent_seconds": (
            lookup_miss_reuse_writeback_aux_other_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_child_known_seconds": (
            lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_unexplained_seconds": aux_other_partition_gap_seconds,
        "lookup_miss_reuse_writeback_aux_other_unexplained_share_of_candidate_index": share(
            aux_other_partition_gap_seconds, candidate_index_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_parent_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds
            + lookup_miss_reuse_writeback_aux_other_residual_residual_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_seconds": abs(
            lookup_miss_reuse_writeback_aux_other_residual_seconds
            - (
                lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds
                + lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds
                + lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds
                + lookup_miss_reuse_writeback_aux_other_residual_residual_seconds
            )
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_closure_gap_share_of_candidate_index": share(
            abs(
                lookup_miss_reuse_writeback_aux_other_residual_seconds
                - (
                    lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds
                    + lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds
                    + lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds
                    + lookup_miss_reuse_writeback_aux_other_residual_residual_seconds
                )
            ),
            candidate_index_seconds,
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_residual_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_residual_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_residual_share_of_candidate_index": share(
            lookup_miss_reuse_writeback_aux_other_residual_residual_seconds,
            candidate_index_seconds,
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_seconds": (
            lookup_miss_reuse_writeback_aux_other_residual_residual_seconds
        ),
        "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index": (
            terminal_residual_share_of_candidate_index
        ),
        "terminal_path_scope": terminal_path["scope"],
        "terminal_path_parent_seconds": terminal_path["parent_seconds"],
        "terminal_path_child_known_seconds": terminal_path["child_known_seconds"],
        "terminal_path_candidate_slot_write_seconds": terminal_path[
            "candidate_slot_write_seconds"
        ],
        "terminal_path_start_index_write_seconds": terminal_path[
            "start_index_write_seconds"
        ],
        "terminal_path_state_update_seconds": terminal_path["state_update_seconds"],
        "terminal_path_state_update_parent_seconds": terminal_path[
            "state_update_parent_seconds"
        ],
        "terminal_path_state_update_heap_build_seconds": terminal_path[
            "state_update_heap_build_seconds"
        ],
        "terminal_path_state_update_heap_update_seconds": terminal_path[
            "state_update_heap_update_seconds"
        ],
        "terminal_path_state_update_start_index_rebuild_seconds": terminal_path[
            "state_update_start_index_rebuild_seconds"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_seconds": terminal_path[
            "state_update_trace_or_profile_bookkeeping_seconds"
        ],
        "terminal_path_state_update_child_known_seconds": terminal_path[
            "state_update_child_known_seconds"
        ],
        "terminal_path_state_update_unexplained_seconds": terminal_path[
            "state_update_unexplained_seconds"
        ],
        "terminal_path_state_update_unexplained_share": terminal_path[
            "state_update_unexplained_share"
        ],
        "terminal_path_state_update_sampled_event_count": terminal_path[
            "state_update_sampled_event_count"
        ],
        "terminal_path_state_update_covered_sampled_event_count": terminal_path[
            "state_update_covered_sampled_event_count"
        ],
        "terminal_path_state_update_unclassified_sampled_event_count": terminal_path[
            "state_update_unclassified_sampled_event_count"
        ],
        "terminal_path_state_update_multi_child_sampled_event_count": terminal_path[
            "state_update_multi_child_sampled_event_count"
        ],
        "terminal_path_state_update_heap_build_sampled_event_count": terminal_path[
            "state_update_heap_build_sampled_event_count"
        ],
        "terminal_path_state_update_heap_update_sampled_event_count": terminal_path[
            "state_update_heap_update_sampled_event_count"
        ],
        "terminal_path_state_update_start_index_rebuild_sampled_event_count": terminal_path[
            "state_update_start_index_rebuild_sampled_event_count"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_sampled_event_count": terminal_path[
            "state_update_trace_or_profile_bookkeeping_sampled_event_count"
        ],
        "terminal_path_state_update_sampled_count_closure_status": terminal_path[
            "state_update_sampled_count_closure_status"
        ],
        "terminal_path_state_update_coverage_source": terminal_path[
            "state_update_coverage_source"
        ],
        "terminal_path_state_update_timer_scope_status": terminal_path[
            "state_update_timer_scope_status"
        ],
        "terminal_path_state_update_dominant_child": terminal_path[
            "state_update_dominant_child"
        ],
        "terminal_path_state_update_coverage_share": terminal_path[
            "state_update_coverage_share"
        ],
        "terminal_path_state_update_unclassified_share": terminal_path[
            "state_update_unclassified_share"
        ],
        "terminal_path_state_update_multi_child_share": terminal_path[
            "state_update_multi_child_share"
        ],
        "terminal_path_state_update_heap_build_share": terminal_path[
            "state_update_heap_build_share"
        ],
        "terminal_path_state_update_heap_update_share": terminal_path[
            "state_update_heap_update_share"
        ],
        "terminal_path_state_update_start_index_rebuild_share": terminal_path[
            "state_update_start_index_rebuild_share"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_share": terminal_path[
            "state_update_trace_or_profile_bookkeeping_share"
        ],
        "terminal_path_telemetry_overhead_seconds": terminal_path[
            "telemetry_overhead_seconds"
        ],
        "terminal_path_residual_seconds": terminal_path["residual_seconds"],
        "terminal_path_candidate_slot_write_share_of_candidate_index": terminal_path[
            "candidate_slot_write_share_of_candidate_index"
        ],
        "terminal_path_start_index_write_share_of_candidate_index": terminal_path[
            "start_index_write_share_of_candidate_index"
        ],
        "terminal_path_state_update_share_of_candidate_index": terminal_path[
            "state_update_share_of_candidate_index"
        ],
        "terminal_path_telemetry_overhead_share_of_candidate_index": terminal_path[
            "telemetry_overhead_share_of_candidate_index"
        ],
        "terminal_path_residual_share_of_candidate_index": terminal_path[
            "residual_share_of_candidate_index"
        ],
        "terminal_path_event_count": terminal_path["event_count"],
        "terminal_path_candidate_slot_write_count": terminal_path[
            "candidate_slot_write_count"
        ],
        "terminal_path_start_index_write_count": terminal_path[
            "start_index_write_count"
        ],
        "terminal_path_state_update_count": terminal_path["state_update_count"],
        "terminal_path_state_update_event_count": terminal_path[
            "state_update_event_count"
        ],
        "terminal_path_state_update_heap_build_count": terminal_path[
            "state_update_heap_build_count"
        ],
        "terminal_path_state_update_heap_update_count": terminal_path[
            "state_update_heap_update_count"
        ],
        "terminal_path_state_update_start_index_rebuild_count": terminal_path[
            "state_update_start_index_rebuild_count"
        ],
        "terminal_path_state_update_trace_or_profile_bookkeeping_count": terminal_path[
            "state_update_trace_or_profile_bookkeeping_count"
        ],
        "terminal_path_state_update_aux_updates_total": terminal_path[
            "state_update_aux_updates_total"
        ],
        "production_state_update_parent_seconds": terminal_path[
            "production_state_update_parent_seconds"
        ],
        "production_state_update_benchmark_counter_seconds": terminal_path[
            "production_state_update_benchmark_counter_seconds"
        ],
        "production_state_update_trace_replay_required_state_seconds": terminal_path[
            "production_state_update_trace_replay_required_state_seconds"
        ],
        "production_state_update_child_known_seconds": terminal_path[
            "production_state_update_child_known_seconds"
        ],
        "production_state_update_unexplained_seconds": terminal_path[
            "production_state_update_unexplained_seconds"
        ],
        "production_state_update_unexplained_share": terminal_path[
            "production_state_update_unexplained_share"
        ],
        "production_state_update_sampled_event_count": terminal_path[
            "production_state_update_sampled_event_count"
        ],
        "production_state_update_covered_sampled_event_count": terminal_path[
            "production_state_update_covered_sampled_event_count"
        ],
        "production_state_update_unclassified_sampled_event_count": terminal_path[
            "production_state_update_unclassified_sampled_event_count"
        ],
        "production_state_update_multi_child_sampled_event_count": terminal_path[
            "production_state_update_multi_child_sampled_event_count"
        ],
        "production_state_update_benchmark_counter_sampled_event_count": terminal_path[
            "production_state_update_benchmark_counter_sampled_event_count"
        ],
        "production_state_update_trace_replay_required_state_sampled_event_count": terminal_path[
            "production_state_update_trace_replay_required_state_sampled_event_count"
        ],
        "production_state_update_sampled_count_closure_status": terminal_path[
            "production_state_update_sampled_count_closure_status"
        ],
        "production_state_update_coverage_source": terminal_path[
            "production_state_update_coverage_source"
        ],
        "production_state_update_timer_scope_status": terminal_path[
            "production_state_update_timer_scope_status"
        ],
        "production_state_update_dominant_child": terminal_path[
            "production_state_update_dominant_child"
        ],
        "production_state_update_case_weighted_dominant_child": (
            production_state_update_case_weighted_dominant_child
        ),
        "production_state_update_seconds_weighted_dominant_child": (
            production_state_update_seconds_weighted_dominant_child
        ),
        "production_state_update_event_weighted_dominant_child": (
            production_state_update_event_weighted_dominant_child
        ),
        "production_state_update_case_majority_share": (
            production_state_update_case_majority_share
        ),
        "production_state_update_child_margin_share": production_state_update_margin_share,
        "production_state_update_dominance_status": (
            production_state_update_dominance_status
        ),
        "production_state_update_coverage_share": terminal_path[
            "production_state_update_coverage_share"
        ],
        "production_state_update_unclassified_share": terminal_path[
            "production_state_update_unclassified_share"
        ],
        "production_state_update_multi_child_share": terminal_path[
            "production_state_update_multi_child_share"
        ],
        "production_state_update_benchmark_counter_share": terminal_path[
            "production_state_update_benchmark_counter_share"
        ],
        "production_state_update_trace_replay_required_state_share": terminal_path[
            "production_state_update_trace_replay_required_state_share"
        ],
        "production_state_update_share_of_candidate_index": terminal_path[
            "production_state_update_share_of_candidate_index"
        ],
        "production_state_update_event_count": terminal_path[
            "production_state_update_event_count"
        ],
        "production_state_update_benchmark_counter_count": terminal_path[
            "production_state_update_benchmark_counter_count"
        ],
        "production_state_update_trace_replay_required_state_count": terminal_path[
            "production_state_update_trace_replay_required_state_count"
        ],
        "terminal_path_candidate_bytes_written": terminal_path[
            "candidate_bytes_written"
        ],
        "terminal_path_start_index_bytes_written": terminal_path[
            "start_index_bytes_written"
        ],
        "terminal_path_dominant_child": terminal_path["dominant_child"],
        "terminal_path_start_index_write_parent_seconds": terminal_path[
            "start_index_write_parent_seconds"
        ],
        "terminal_path_start_index_write_left_seconds": terminal_path[
            "start_index_write_left_seconds"
        ],
        "terminal_path_start_index_write_right_seconds": terminal_path[
            "start_index_write_right_seconds"
        ],
        "terminal_path_start_index_write_child_known_seconds": terminal_path[
            "start_index_write_child_known_seconds"
        ],
        "terminal_path_start_index_write_unexplained_seconds": terminal_path[
            "start_index_write_unexplained_seconds"
        ],
        "terminal_path_start_index_write_unexplained_share": terminal_path[
            "start_index_write_unexplained_share"
        ],
        "terminal_path_start_index_write_sampled_event_count": terminal_path[
            "start_index_write_sampled_event_count"
        ],
        "terminal_path_start_index_write_covered_sampled_event_count": terminal_path[
            "start_index_write_covered_sampled_event_count"
        ],
        "terminal_path_start_index_write_unclassified_sampled_event_count": terminal_path[
            "start_index_write_unclassified_sampled_event_count"
        ],
        "terminal_path_start_index_write_multi_child_sampled_event_count": terminal_path[
            "start_index_write_multi_child_sampled_event_count"
        ],
        "terminal_path_start_index_write_left_sampled_event_count": terminal_path[
            "start_index_write_left_sampled_event_count"
        ],
        "terminal_path_start_index_write_right_sampled_event_count": terminal_path[
            "start_index_write_right_sampled_event_count"
        ],
        "terminal_path_start_index_write_sampled_count_closure_status": terminal_path[
            "start_index_write_sampled_count_closure_status"
        ],
        "terminal_path_start_index_write_dominant_child": terminal_path[
            "start_index_write_dominant_child"
        ],
        "terminal_path_start_index_write_coverage_share": terminal_path[
            "start_index_write_coverage_share"
        ],
        "terminal_path_start_index_write_unclassified_share": terminal_path[
            "start_index_write_unclassified_share"
        ],
        "terminal_path_start_index_write_multi_child_share": terminal_path[
            "start_index_write_multi_child_share"
        ],
        "terminal_path_start_index_write_probe_or_locate_share": terminal_path[
            "start_index_write_probe_or_locate_share"
        ],
        "terminal_path_start_index_write_entry_store_share": terminal_path[
            "start_index_write_entry_store_share"
        ],
        "terminal_path_start_index_write_insert_count": terminal_path[
            "start_index_write_insert_count"
        ],
        "terminal_path_start_index_write_update_existing_count": terminal_path[
            "start_index_write_update_existing_count"
        ],
        "terminal_path_start_index_write_clear_count": terminal_path[
            "start_index_write_clear_count"
        ],
        "terminal_path_start_index_write_overwrite_count": terminal_path[
            "start_index_write_overwrite_count"
        ],
        "terminal_path_start_index_write_idempotent_count": terminal_path[
            "start_index_write_idempotent_count"
        ],
        "terminal_path_start_index_write_value_changed_count": terminal_path[
            "start_index_write_value_changed_count"
        ],
        "terminal_path_start_index_write_probe_count": terminal_path[
            "start_index_write_probe_count"
        ],
        "terminal_path_start_index_write_probe_steps_total": terminal_path[
            "start_index_write_probe_steps_total"
        ],
        "terminal_path_start_index_store_parent_seconds": terminal_path[
            "start_index_store_parent_seconds"
        ],
        "terminal_path_start_index_store_insert_seconds": terminal_path[
            "start_index_store_insert_seconds"
        ],
        "terminal_path_start_index_store_clear_seconds": terminal_path[
            "start_index_store_clear_seconds"
        ],
        "terminal_path_start_index_store_overwrite_seconds": terminal_path[
            "start_index_store_overwrite_seconds"
        ],
        "terminal_path_start_index_store_child_known_seconds": terminal_path[
            "start_index_store_child_known_seconds"
        ],
        "terminal_path_start_index_store_unexplained_seconds": terminal_path[
            "start_index_store_unexplained_seconds"
        ],
        "terminal_path_start_index_store_unexplained_share": terminal_path[
            "start_index_store_unexplained_share"
        ],
        "terminal_path_start_index_store_sampled_event_count": terminal_path[
            "start_index_store_sampled_event_count"
        ],
        "terminal_path_start_index_store_covered_sampled_event_count": terminal_path[
            "start_index_store_covered_sampled_event_count"
        ],
        "terminal_path_start_index_store_unclassified_sampled_event_count": terminal_path[
            "start_index_store_unclassified_sampled_event_count"
        ],
        "terminal_path_start_index_store_multi_child_sampled_event_count": terminal_path[
            "start_index_store_multi_child_sampled_event_count"
        ],
        "terminal_path_start_index_store_insert_sampled_event_count": terminal_path[
            "start_index_store_insert_sampled_event_count"
        ],
        "terminal_path_start_index_store_clear_sampled_event_count": terminal_path[
            "start_index_store_clear_sampled_event_count"
        ],
        "terminal_path_start_index_store_overwrite_sampled_event_count": terminal_path[
            "start_index_store_overwrite_sampled_event_count"
        ],
        "terminal_path_start_index_store_sampled_count_closure_status": terminal_path[
            "start_index_store_sampled_count_closure_status"
        ],
        "terminal_path_start_index_store_dominant_child": terminal_path[
            "start_index_store_dominant_child"
        ],
        "terminal_path_start_index_store_coverage_share": terminal_path[
            "start_index_store_coverage_share"
        ],
        "terminal_path_start_index_store_unclassified_share": terminal_path[
            "start_index_store_unclassified_share"
        ],
        "terminal_path_start_index_store_multi_child_share": terminal_path[
            "start_index_store_multi_child_share"
        ],
        "terminal_path_start_index_store_insert_share": terminal_path[
            "start_index_store_insert_share"
        ],
        "terminal_path_start_index_store_clear_share": terminal_path[
            "start_index_store_clear_share"
        ],
        "terminal_path_start_index_store_overwrite_share": terminal_path[
            "start_index_store_overwrite_share"
        ],
        "terminal_path_start_index_store_insert_count": terminal_path[
            "start_index_store_insert_count"
        ],
        "terminal_path_start_index_store_clear_count": terminal_path[
            "start_index_store_clear_count"
        ],
        "terminal_path_start_index_store_overwrite_count": terminal_path[
            "start_index_store_overwrite_count"
        ],
        "terminal_path_start_index_store_insert_bytes": terminal_path[
            "start_index_store_insert_bytes"
        ],
        "terminal_path_start_index_store_clear_bytes": terminal_path[
            "start_index_store_clear_bytes"
        ],
        "terminal_path_start_index_store_overwrite_bytes": terminal_path[
            "start_index_store_overwrite_bytes"
        ],
        "terminal_path_start_index_store_unique_entry_count": terminal_path[
            "start_index_store_unique_entry_count"
        ],
        "terminal_path_start_index_store_unique_slot_count": terminal_path[
            "start_index_store_unique_slot_count"
        ],
        "terminal_path_start_index_store_unique_key_count": terminal_path[
            "start_index_store_unique_key_count"
        ],
        "terminal_path_start_index_store_same_entry_rewrite_count": terminal_path[
            "start_index_store_same_entry_rewrite_count"
        ],
        "terminal_path_start_index_store_same_cacheline_rewrite_count": terminal_path[
            "start_index_store_same_cacheline_rewrite_count"
        ],
        "terminal_path_start_index_store_back_to_back_same_entry_write_count": terminal_path[
            "start_index_store_back_to_back_same_entry_write_count"
        ],
        "terminal_path_start_index_store_clear_then_overwrite_same_entry_count": terminal_path[
            "start_index_store_clear_then_overwrite_same_entry_count"
        ],
        "terminal_path_start_index_store_overwrite_then_insert_same_entry_count": terminal_path[
            "start_index_store_overwrite_then_insert_same_entry_count"
        ],
        "terminal_path_start_index_store_insert_then_clear_same_entry_count": terminal_path[
            "start_index_store_insert_then_clear_same_entry_count"
        ],
        "terminal_path_start_index_store_clear_then_overwrite_same_entry_share": terminal_path[
            "start_index_store_clear_then_overwrite_same_entry_share"
        ],
        "terminal_path_start_index_store_case_weighted_dominant_child": start_index_store_case_weighted_dominant_child,
        "terminal_path_start_index_store_seconds_weighted_dominant_child": start_index_store_seconds_weighted_dominant_child,
        "terminal_path_start_index_store_event_weighted_dominant_child": start_index_store_event_weighted_dominant_child,
        "terminal_path_start_index_store_case_majority_share": start_index_store_case_majority_share,
        "terminal_path_start_index_store_child_margin_share": start_index_store_margin_share,
        "terminal_path_start_index_store_dominance_status": start_index_store_dominance_status,
        "terminal_lexical_parent_seconds": terminal_lexical_parent_seconds,
        "terminal_span_first_half_seconds": terminal_span_first_half_seconds,
        "terminal_span_second_half_seconds": terminal_span_second_half_seconds,
        "terminal_first_half_parent_seconds": terminal_first_half_parent_seconds,
        "terminal_first_half_span_a_seconds": terminal_first_half_span_a_seconds,
        "terminal_first_half_span_b_seconds": terminal_first_half_span_b_seconds,
        "terminal_first_half_child_known_seconds": terminal_first_half_child_known_seconds,
        "terminal_first_half_unexplained_seconds": terminal_first_half_unexplained_seconds,
        "dominant_terminal_span": dominant_terminal_span,
        "dominant_terminal_first_half_span": dominant_terminal_first_half_span,
        "timer_call_count": sum_optional_int_rows(rows, "timer_call_count"),
        "terminal_timer_call_count": sum_optional_int_rows(rows, "terminal_timer_call_count"),
        "lexical_timer_call_count": sum_optional_int_rows(rows, "lexical_timer_call_count"),
        "intra_profile_closure_status": intra_profile_closure_status,
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "candidate_index_materiality_status": candidate_index_materiality_status,
        "terminal_timer_closure_status": terminal_timer_closure_status,
        "lexical_span_closure_status": lexical_span_closure_status,
        "profile_overhead_status": profile_mode_overhead_status,
        "candidate_index_timer_scope_status": candidate_index_timer_scope_status,
        "reuse_aux_other_timer_scope_status": reuse_aux_other_timer_scope_status,
        "terminal_residual_status": terminal_residual_status,
    }
    timer_scope_status = (
        "closed"
        if candidate_index_timer_scope_status == "closed"
        and reuse_aux_other_timer_scope_status == "closed"
        and terminal_residual_status != "dominant"
        else "residual_unexplained"
    )

    return {
        "materiality_status": "known"
        if pairing["status"] in {"complete", "duplicate_grouped"}
        else "unknown",
        "materiality_pairing_status": pairing["status"],
        "case_count": len(rows),
        "full_set_miss_count": sum_key("full_set_miss_count"),
        "candidate_index": candidate_index,
        "cost_shares": {
            "initial_cpu_merge_share_of_sim_seconds": initial_cpu_merge_share_of_sim_seconds,
            "initial_cpu_merge_share_of_total_seconds": initial_cpu_merge_share_of_total_seconds,
        },
        "candidate_index_timer_scope_status": candidate_index_timer_scope_status,
        "reuse_aux_other_timer_scope_status": reuse_aux_other_timer_scope_status,
        "terminal_residual_status": terminal_residual_status,
        "intra_profile_closure_status": intra_profile_closure_status,
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "candidate_index_materiality_status": candidate_index_materiality_status,
        "terminal_timer_closure_status": terminal_timer_closure_status,
        "lexical_span_closure_status": lexical_span_closure_status,
        "profile_overhead_status": profile_mode_overhead_status,
        "timer_scope_status": timer_scope_status,
    }


def write_summary_markdown(path: Path, summary):
    candidate = summary.get("candidate_index", {})
    initial_cpu_merge_share_of_sim = summary["cost_shares"]["initial_cpu_merge_share_of_sim_seconds"]
    initial_cpu_merge_share_of_total = summary["cost_shares"]["initial_cpu_merge_share_of_total_seconds"]
    candidate_share_of_sim_text = (
        "n/a"
        if candidate.get("share_of_sim_seconds") is None
        else f"{candidate['share_of_sim_seconds']:.6f}"
    )
    candidate_share_of_total_text = (
        "n/a"
        if candidate.get("share_of_total_seconds") is None
        else f"{candidate['share_of_total_seconds']:.6f}"
    )
    initial_cpu_merge_share_of_sim_text = (
        "n/a" if initial_cpu_merge_share_of_sim is None else f"{initial_cpu_merge_share_of_sim:.6f}"
    )
    initial_cpu_merge_share_of_total_text = (
        "n/a"
        if initial_cpu_merge_share_of_total is None
        else f"{initial_cpu_merge_share_of_total:.6f}"
    )
    lines = [
        "# SIM Initial Host Merge Candidate Index Lifecycle Summary",
        "",
        f"- decision_status: `{summary['decision_status']}`",
        f"- materiality_status: `{summary['materiality_status']}`",
        f"- materiality_pairing_status: `{summary['materiality_pairing_status']}`",
        f"- runtime_prototype_allowed: `{str(summary.get('runtime_prototype_allowed', False)).lower()}`",
        f"- candidate_index_materiality_status: `{summary.get('candidate_index_materiality_status', 'unknown')}`",
        f"- candidate_index_timer_scope_status: `{summary.get('candidate_index_timer_scope_status', 'unknown')}`",
        f"- reuse_aux_other_timer_scope_status: `{summary.get('reuse_aux_other_timer_scope_status', 'unknown')}`",
        f"- terminal_timer_closure_status: `{summary.get('terminal_timer_closure_status', 'unknown')}`",
        f"- lexical_span_closure_status: `{summary.get('lexical_span_closure_status', 'unknown')}`",
        f"- intra_profile_closure_status: `{summary.get('intra_profile_closure_status', 'unknown')}`",
        f"- profile_mode_overhead_status: `{summary.get('profile_mode_overhead_status', 'unknown')}`",
        f"- decision_context_status: `{summary.get('decision_context_status', summary['decision_status'])}`",
        f"- authoritative_next_action_context_status: `{summary.get('authoritative_next_action_context_status', 'ready_but_requires_branch_rollup_context')}`",
        f"- authoritative_next_action_source: `{summary.get('authoritative_next_action_source', 'branch_rollup_decision')}`",
        f"- profile_mode_overhead_status_context: `{summary.get('profile_mode_overhead_status_context', 'self_contained')}`",
        f"- authoritative_profile_mode_overhead_source_kind: `{summary.get('authoritative_profile_mode_overhead_source_kind', 'candidate_index_lifecycle_summary')}`",
        f"- terminal_residual_status: `{summary.get('terminal_residual_status', 'unknown')}`",
        f"- profile_overhead_status: `{summary.get('profile_overhead_status', 'unknown')}`",
        f"- timer_scope_status: `{summary.get('timer_scope_status', 'unknown')}`",
        f"- case_count: `{summary['case_count']}`",
        f"- ready_case_count: `{summary['ready_case_count']}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        "",
    ]
    if summary["errors"]:
        lines.extend(["## Errors", ""])
        for error in summary["errors"]:
            lines.append(f"- {error}")
        lines.append("")
    if summary["decision_status"] in {"ready", "ready_but_materiality_unknown"}:
        lines.extend(
            [
                "## Aggregate",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| full_set_miss_count | {summary['full_set_miss_count']} |",
                f"| candidate_index_seconds | {candidate['seconds']:.6f} |",
                f"| candidate_index_share_of_initial_cpu_merge | {candidate['share_of_initial_cpu_merge']:.6f} |",
                f"| candidate_index_share_of_sim_seconds | {candidate_share_of_sim_text} |",
                f"| candidate_index_share_of_total_seconds | {candidate_share_of_total_text} |",
                f"| initial_cpu_merge_share_of_sim_seconds | {initial_cpu_merge_share_of_sim_text} |",
                f"| initial_cpu_merge_share_of_total_seconds | {initial_cpu_merge_share_of_total_text} |",
                f"| candidate_index_parent_seconds | {candidate['parent_seconds']:.6f} |",
                f"| candidate_index_child_known_seconds | {candidate['child_known_seconds']:.6f} |",
                f"| candidate_index_unexplained_seconds | {candidate['unexplained_seconds']:.6f} |",
                f"| candidate_index_unexplained_share_of_candidate_index | {candidate['unexplained_share_of_candidate_index']:.6f} |",
                f"| lookup_miss_reuse_writeback_parent_seconds | {candidate['lookup_miss_reuse_writeback_parent_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_child_known_seconds | {candidate['lookup_miss_reuse_writeback_child_known_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_unexplained_seconds | {candidate['lookup_miss_reuse_writeback_unexplained_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_parent_seconds | {candidate['lookup_miss_reuse_writeback_aux_other_parent_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_child_known_seconds | {candidate['lookup_miss_reuse_writeback_aux_other_child_known_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_unexplained_seconds | {candidate['lookup_miss_reuse_writeback_aux_other_unexplained_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_residual_parent_seconds | {candidate['lookup_miss_reuse_writeback_aux_other_residual_parent_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds | {candidate['lookup_miss_reuse_writeback_aux_other_residual_child_known_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_seconds | {candidate['lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_seconds']:.6f} |",
                f"| lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index | {candidate['lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index']:.6f} |",
                f"| terminal_path_scope | {candidate['terminal_path_scope']} |",
                f"| terminal_path_parent_seconds | {candidate['terminal_path_parent_seconds']:.6f} |",
                f"| terminal_path_child_known_seconds | {candidate['terminal_path_child_known_seconds']:.6f} |",
                f"| terminal_path_candidate_slot_write_seconds | {candidate['terminal_path_candidate_slot_write_seconds']:.6f} |",
                f"| terminal_path_start_index_write_seconds | {candidate['terminal_path_start_index_write_seconds']:.6f} |",
                f"| terminal_path_state_update_seconds | {candidate['terminal_path_state_update_seconds']:.6f} |",
                f"| terminal_path_telemetry_overhead_seconds | {candidate['terminal_path_telemetry_overhead_seconds']:.6f} |",
                f"| terminal_path_residual_seconds | {candidate['terminal_path_residual_seconds']:.6f} |",
                f"| terminal_path_dominant_child | {candidate['terminal_path_dominant_child']} |",
                f"| dominant_terminal_span | {candidate['dominant_terminal_span']} |",
                f"| intra_profile_closure_status | {summary.get('intra_profile_closure_status', 'unknown')} |",
                f"| profile_mode_overhead_status | {summary.get('profile_mode_overhead_status', 'unknown')} |",
                f"| decision_context_status | {summary.get('decision_context_status', summary['decision_status'])} |",
                f"| authoritative_next_action_context_status | {summary.get('authoritative_next_action_context_status', 'ready_but_requires_branch_rollup_context')} |",
                f"| authoritative_next_action_source | {summary.get('authoritative_next_action_source', 'branch_rollup_decision')} |",
                f"| profile_mode_overhead_status_context | {summary.get('profile_mode_overhead_status_context', 'self_contained')} |",
                f"| authoritative_profile_mode_overhead_source_kind | {summary.get('authoritative_profile_mode_overhead_source_kind', 'candidate_index_lifecycle_summary')} |",
                f"| profile_overhead_status | {summary.get('profile_overhead_status', 'unknown')} |",
                f"| probe_share_of_candidate_index | {candidate['lookup_miss_candidate_set_full_probe_share_of_candidate_index']:.6f} |",
                f"| erase_share_of_candidate_index | {candidate['erase_share_of_candidate_index']:.6f} |",
                f"| reuse_writeback_share_of_candidate_index | {candidate['lookup_miss_reuse_writeback_share_of_candidate_index']:.6f} |",
                f"| aux_other_share_of_candidate_index | {candidate['lookup_miss_reuse_writeback_aux_other_share_of_candidate_index']:.6f} |",
                f"| aux_other_residual_share_of_candidate_index | {candidate['lookup_miss_reuse_writeback_aux_other_residual_share_of_candidate_index']:.6f} |",
                f"| candidate_index_scope_gap_share_of_candidate_index | {candidate['candidate_index_scope_gap_share_of_candidate_index']:.6f} |",
                f"| lookup_partition_gap_share_of_candidate_index | {candidate['lookup_partition_gap_share_of_candidate_index']:.6f} |",
                f"| lookup_miss_partition_gap_share_of_candidate_index | {candidate['lookup_miss_partition_gap_share_of_candidate_index']:.6f} |",
                f"| reuse_writeback_partition_gap_share_of_candidate_index | {candidate['reuse_writeback_partition_gap_share_of_candidate_index']:.6f} |",
                f"| aux_bookkeeping_partition_gap_share_of_candidate_index | {candidate['aux_bookkeeping_partition_gap_share_of_candidate_index']:.6f} |",
                f"| aux_other_partition_gap_share_of_candidate_index | {candidate['aux_other_partition_gap_share_of_candidate_index']:.6f} |",
                "",
                "## Cases",
                "",
                "| case_id | candidate_index_share | candidate_index_share_of_sim | probe_share | terminal_residual_share | terminal_path_dominant_child | dominant_terminal_span | next_action |",
                "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
            ]
        )
        for row in summary["cases"]:
            case_share_of_sim = (
                "n/a"
                if row["candidate_index_share_of_sim_seconds"] is None
                else f"{row['candidate_index_share_of_sim_seconds']:.6f}"
            )
            lines.append(
                f"| {row['case_id']} | {row['candidate_index_share_of_initial_cpu_merge']:.6f} | "
                f"{case_share_of_sim} | "
                f"{row['lookup_miss_candidate_set_full_probe_share_of_candidate_index']:.6f} | "
                f"{row['lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index']:.6f} | "
                f"{row['terminal_path_dominant_child']} | "
                f"{row['dominant_terminal_span']} | "
                f"{row['recommended_next_action']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def overhead_context_fields(decision_status, profile_mode_overhead_status):
    if profile_mode_overhead_status == "needs_coarse_vs_lexical_ab":
        return {
            "decision_context_status": "ready_but_requires_ab_context",
            "profile_mode_overhead_status_context": "delegated_to_profile_mode_ab",
            "authoritative_profile_mode_overhead_source_kind": "profile_mode_ab_summary",
        }
    return {
        "decision_context_status": decision_status,
        "profile_mode_overhead_status_context": "self_contained",
        "authoritative_profile_mode_overhead_source_kind": "candidate_index_lifecycle_summary",
    }


def format_row(row):
    formatted = {}
    for key, value in row.items():
        if value is None:
            formatted[key] = ""
        elif isinstance(value, float):
            formatted[key] = f"{value:.6f}"
        else:
            formatted[key] = value
    return formatted


def write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_case_ids = set(args.case_id or [])
    errors = []
    rows = []
    seen_case_ids = set()

    for aggregate_tsv in args.aggregate_tsv:
        path = Path(aggregate_tsv)
        try:
            raw_rows = load_rows(path)
        except LifecycleInputError as exc:
            errors.append(str(exc))
            continue
        for raw_row in raw_rows:
            case_id = raw_row["case_id"]
            if selected_case_ids and case_id not in selected_case_ids:
                continue
            if case_id in seen_case_ids:
                errors.append(f"duplicate case_id across lifecycle inputs: {case_id}")
                continue
            try:
                row = analyze_case(raw_row, path, args)
            except LifecycleInputError as exc:
                errors.append(str(exc))
                continue
            rows.append(row)
            seen_case_ids.add(case_id)

    cases_tsv = output_dir / "candidate_index_lifecycle_cases.tsv"
    summary_json = output_dir / "candidate_index_lifecycle_summary.json"
    decision_json = output_dir / "candidate_index_lifecycle_decision.json"
    summary_md = output_dir / "candidate_index_lifecycle_summary.md"
    write_rows(cases_tsv, CASE_FIELDNAMES, [format_row(row) for row in rows])

    if errors or not rows:
        context_fields = overhead_context_fields("not_ready", "unknown")
        summary = {
            "decision_status": "not_ready",
            "authoritative_next_action_context_status": "ready_but_requires_branch_rollup_context",
            "authoritative_next_action_source": "branch_rollup_decision",
            "materiality_status": "unknown",
            "materiality_pairing_status": "missing",
            "runtime_prototype_allowed": False,
            "candidate_index_timer_scope_status": "unknown",
            "reuse_aux_other_timer_scope_status": "unknown",
            "terminal_residual_status": "unknown",
            "intra_profile_closure_status": "unknown",
            "profile_mode_overhead_status": "unknown",
            "candidate_index_materiality_status": "unknown",
            "terminal_timer_closure_status": "unknown",
            "lexical_span_closure_status": "unknown",
            "profile_overhead_status": "unknown",
            "timer_scope_status": "unknown",
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": sum(row["full_set_miss_count"] for row in rows),
            "recommended_next_action": "fix_profile_inputs",
            "errors": errors if errors else ["no ready lifecycle rows"],
            "cases": rows,
            "cases_tsv": str(cases_tsv),
            "summary_markdown": str(summary_md),
            "cost_shares": {
                "initial_cpu_merge_share_of_sim_seconds": None,
                "initial_cpu_merge_share_of_total_seconds": None,
            },
        }
        summary.update(context_fields)
        decision = {
            "decision_status": "not_ready",
            "authoritative_next_action_context_status": "ready_but_requires_branch_rollup_context",
            "authoritative_next_action_source": "branch_rollup_decision",
            "materiality_status": "unknown",
            "materiality_pairing_status": "missing",
            "runtime_prototype_allowed": False,
            "candidate_index_timer_scope_status": "unknown",
            "reuse_aux_other_timer_scope_status": "unknown",
            "terminal_residual_status": "unknown",
            "intra_profile_closure_status": "unknown",
            "profile_mode_overhead_status": "unknown",
            "candidate_index_materiality_status": "unknown",
            "terminal_timer_closure_status": "unknown",
            "lexical_span_closure_status": "unknown",
            "profile_overhead_status": "unknown",
            "timer_scope_status": "unknown",
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": sum(row["full_set_miss_count"] for row in rows),
            "recommended_next_action": "fix_profile_inputs",
            "blocking_reasons": summary["errors"],
        }
        decision.update(context_fields)
    else:
        aggregate = aggregate_summary(rows, args)
        metrics = {
            "candidate_index_share_of_initial_cpu_merge": aggregate["candidate_index"][
                "share_of_initial_cpu_merge"
            ],
            "candidate_index_share_of_sim_seconds": aggregate["candidate_index"][
                "share_of_sim_seconds"
            ],
            "initial_cpu_merge_share_of_sim_seconds": aggregate["cost_shares"][
                "initial_cpu_merge_share_of_sim_seconds"
            ],
            "candidate_index_erase_share_of_candidate_index": aggregate["candidate_index"][
                "erase_share_of_candidate_index"
            ],
            "lookup_miss_candidate_set_full_probe_share_of_candidate_index": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_share_of_candidate_index"],
            "lookup_miss_candidate_set_full_probe_sampled_count_closure_status": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_sampled_count_closure_status"],
            "lookup_miss_candidate_set_full_probe_unexplained_share": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_unexplained_share"],
            "lookup_miss_candidate_set_full_probe_scan_share": aggregate["candidate_index"][
                "lookup_miss_candidate_set_full_probe_scan_share"
            ],
            "lookup_miss_candidate_set_full_probe_compare_share": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_compare_share"],
            "lookup_miss_candidate_set_full_probe_branch_or_guard_share": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_branch_or_guard_share"],
            "lookup_miss_candidate_set_full_probe_bookkeeping_share": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_bookkeeping_share"],
            "lookup_miss_candidate_set_full_probe_full_scan_share": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_full_scan_share"],
            "lookup_miss_candidate_set_full_probe_redundant_reprobe_share": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_redundant_reprobe_share"],
            "lookup_miss_candidate_set_full_probe_slots_scanned_p90": aggregate[
                "candidate_index"
            ]["lookup_miss_candidate_set_full_probe_slots_scanned_p90"],
            "lookup_miss_reuse_writeback_share_of_candidate_index": aggregate[
                "candidate_index"
            ]["lookup_miss_reuse_writeback_share_of_candidate_index"],
            "lookup_miss_reuse_writeback_aux_other_share_of_candidate_index": aggregate[
                "candidate_index"
            ]["lookup_miss_reuse_writeback_aux_other_share_of_candidate_index"],
            "candidate_index_timer_scope_status": aggregate[
                "candidate_index_timer_scope_status"
            ],
            "reuse_aux_other_timer_scope_status": aggregate[
                "reuse_aux_other_timer_scope_status"
            ],
            "terminal_residual_share_of_candidate_index": aggregate["candidate_index"][
                "lookup_miss_reuse_writeback_aux_other_residual_terminal_residual_share_of_candidate_index"
            ],
            "terminal_path_dominant_child": aggregate["candidate_index"][
                "terminal_path_dominant_child"
            ],
            "terminal_path_start_index_write_share_of_candidate_index": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_write_share_of_candidate_index"],
            "terminal_path_start_index_write_unexplained_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_write_unexplained_share"],
            "terminal_path_start_index_write_sampled_count_closure_status": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_write_sampled_count_closure_status"],
            "terminal_path_start_index_write_probe_or_locate_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_write_probe_or_locate_share"],
            "terminal_path_start_index_write_entry_store_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_write_entry_store_share"],
            "terminal_path_start_index_write_count": aggregate["candidate_index"][
                "terminal_path_start_index_write_count"
            ],
            "terminal_path_start_index_write_idempotent_count": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_write_idempotent_count"],
            "terminal_path_start_index_store_sampled_count_closure_status": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_sampled_count_closure_status"],
            "terminal_path_start_index_store_unexplained_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_unexplained_share"],
            "terminal_path_start_index_store_case_weighted_dominant_child": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_case_weighted_dominant_child"],
            "terminal_path_start_index_store_seconds_weighted_dominant_child": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_seconds_weighted_dominant_child"],
            "terminal_path_start_index_store_event_weighted_dominant_child": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_event_weighted_dominant_child"],
            "terminal_path_start_index_store_case_majority_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_case_majority_share"],
            "terminal_path_start_index_store_child_margin_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_child_margin_share"],
            "terminal_path_start_index_store_dominance_status": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_dominance_status"],
            "terminal_path_start_index_store_insert_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_insert_share"],
            "terminal_path_start_index_store_clear_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_clear_share"],
            "terminal_path_start_index_store_overwrite_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_overwrite_share"],
            "terminal_path_start_index_store_overwrite_count": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_overwrite_count"],
            "terminal_path_start_index_store_clear_then_overwrite_same_entry_share": aggregate[
                "candidate_index"
            ]["terminal_path_start_index_store_clear_then_overwrite_same_entry_share"],
            "terminal_path_state_update_share_of_candidate_index": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_share_of_candidate_index"],
            "terminal_path_state_update_sampled_count_closure_status": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_sampled_count_closure_status"],
            "terminal_path_state_update_coverage_source": aggregate["candidate_index"][
                "terminal_path_state_update_coverage_source"
            ],
            "terminal_path_state_update_timer_scope_status": aggregate["candidate_index"][
                "terminal_path_state_update_timer_scope_status"
            ],
            "terminal_path_state_update_unexplained_share": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_unexplained_share"],
            "terminal_path_state_update_trace_or_profile_bookkeeping_share": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_trace_or_profile_bookkeeping_share"],
            "terminal_path_state_update_heap_update_share": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_heap_update_share"],
            "terminal_path_state_update_heap_build_share": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_heap_build_share"],
            "terminal_path_state_update_start_index_rebuild_share": aggregate[
                "candidate_index"
            ]["terminal_path_state_update_start_index_rebuild_share"],
            "production_state_update_share_of_candidate_index": aggregate[
                "candidate_index"
            ]["production_state_update_share_of_candidate_index"],
            "production_state_update_sampled_count_closure_status": aggregate[
                "candidate_index"
            ]["production_state_update_sampled_count_closure_status"],
            "production_state_update_coverage_source": aggregate["candidate_index"][
                "production_state_update_coverage_source"
            ],
            "production_state_update_timer_scope_status": aggregate["candidate_index"][
                "production_state_update_timer_scope_status"
            ],
            "production_state_update_unexplained_share": aggregate[
                "candidate_index"
            ]["production_state_update_unexplained_share"],
            "production_state_update_dominance_status": aggregate["candidate_index"][
                "production_state_update_dominance_status"
            ],
            "production_state_update_child_margin_share": aggregate["candidate_index"][
                "production_state_update_child_margin_share"
            ],
            "production_state_update_seconds_weighted_dominant_child": aggregate[
                "candidate_index"
            ]["production_state_update_seconds_weighted_dominant_child"],
            "production_state_update_benchmark_counter_share": aggregate[
                "candidate_index"
            ]["production_state_update_benchmark_counter_share"],
            "production_state_update_trace_replay_required_state_share": aggregate[
                "candidate_index"
            ]["production_state_update_trace_replay_required_state_share"],
            "dominant_terminal_span": aggregate["candidate_index"]["dominant_terminal_span"],
            "dominant_terminal_first_half_span": aggregate["candidate_index"][
                "dominant_terminal_first_half_span"
            ],
            "lexical_span_closure_status": aggregate["lexical_span_closure_status"],
            "intra_profile_closure_status": aggregate["intra_profile_closure_status"],
            "profile_mode_overhead_status": aggregate["profile_mode_overhead_status"],
            "profile_overhead_status": aggregate["profile_overhead_status"],
            "timer_scope_status": aggregate["timer_scope_status"],
        }
        next_action = recommended_next_action(metrics, args)
        decision_status = (
            "ready"
            if aggregate["materiality_status"] == "known"
            else "ready_but_materiality_unknown"
        )
        context_fields = overhead_context_fields(
            decision_status, aggregate["profile_mode_overhead_status"]
        )
        summary = {
            "decision_status": decision_status,
            "authoritative_next_action_context_status": "ready_but_requires_branch_rollup_context",
            "authoritative_next_action_source": "branch_rollup_decision",
            "materiality_status": aggregate["materiality_status"],
            "materiality_pairing_status": aggregate["materiality_pairing_status"],
            "runtime_prototype_allowed": False,
            "terminal_telemetry_overhead_mode_requested": aggregate["candidate_index"][
                "terminal_telemetry_overhead_mode_requested"
            ],
            "terminal_telemetry_overhead_mode_effective": aggregate["candidate_index"][
                "terminal_telemetry_overhead_mode_effective"
            ],
            "state_update_bookkeeping_mode_requested": aggregate["candidate_index"][
                "state_update_bookkeeping_mode_requested"
            ],
            "state_update_bookkeeping_mode_effective": aggregate["candidate_index"][
                "state_update_bookkeeping_mode_effective"
            ],
            "candidate_index_timer_scope_status": aggregate[
                "candidate_index_timer_scope_status"
            ],
            "reuse_aux_other_timer_scope_status": aggregate[
                "reuse_aux_other_timer_scope_status"
            ],
            "terminal_residual_status": aggregate["terminal_residual_status"],
            "intra_profile_closure_status": aggregate["intra_profile_closure_status"],
            "profile_mode_overhead_status": aggregate["profile_mode_overhead_status"],
            "candidate_index_materiality_status": aggregate[
                "candidate_index_materiality_status"
            ],
            "terminal_timer_closure_status": aggregate["terminal_timer_closure_status"],
            "lexical_span_closure_status": aggregate["lexical_span_closure_status"],
            "profile_overhead_status": aggregate["profile_overhead_status"],
            "timer_scope_status": aggregate["timer_scope_status"],
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": aggregate["full_set_miss_count"],
            "candidate_index": aggregate["candidate_index"],
            "cost_shares": aggregate["cost_shares"],
            "recommended_next_action": next_action,
            "errors": [],
            "cases": rows,
            "cases_tsv": str(cases_tsv),
            "summary_markdown": str(summary_md),
        }
        summary.update(context_fields)
        decision = {
            "decision_status": decision_status,
            "authoritative_next_action_context_status": "ready_but_requires_branch_rollup_context",
            "authoritative_next_action_source": "branch_rollup_decision",
            "materiality_status": aggregate["materiality_status"],
            "materiality_pairing_status": aggregate["materiality_pairing_status"],
            "runtime_prototype_allowed": False,
            "terminal_telemetry_overhead_mode_requested": aggregate["candidate_index"][
                "terminal_telemetry_overhead_mode_requested"
            ],
            "terminal_telemetry_overhead_mode_effective": aggregate["candidate_index"][
                "terminal_telemetry_overhead_mode_effective"
            ],
            "state_update_bookkeeping_mode_requested": aggregate["candidate_index"][
                "state_update_bookkeeping_mode_requested"
            ],
            "state_update_bookkeeping_mode_effective": aggregate["candidate_index"][
                "state_update_bookkeeping_mode_effective"
            ],
            "candidate_index_timer_scope_status": aggregate[
                "candidate_index_timer_scope_status"
            ],
            "reuse_aux_other_timer_scope_status": aggregate[
                "reuse_aux_other_timer_scope_status"
            ],
            "terminal_residual_status": aggregate["terminal_residual_status"],
            "intra_profile_closure_status": aggregate["intra_profile_closure_status"],
            "profile_mode_overhead_status": aggregate["profile_mode_overhead_status"],
            "candidate_index_materiality_status": aggregate[
                "candidate_index_materiality_status"
            ],
            "terminal_timer_closure_status": aggregate["terminal_timer_closure_status"],
            "lexical_span_closure_status": aggregate["lexical_span_closure_status"],
            "profile_overhead_status": aggregate["profile_overhead_status"],
            "timer_scope_status": aggregate["timer_scope_status"],
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": aggregate["full_set_miss_count"],
            "candidate_index": aggregate["candidate_index"],
            "cost_shares": aggregate["cost_shares"],
            "recommended_next_action": next_action,
        }
        decision.update(context_fields)

    write_summary_markdown(summary_md, summary)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision_json.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
