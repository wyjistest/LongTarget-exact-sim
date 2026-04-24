#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


class RollupInputError(Exception):
    pass


START_INDEX_WRITE_CHILD_SHARE_THRESHOLD = 0.40
START_INDEX_WRITE_UNEXPLAINED_THRESHOLD = 0.10
START_INDEX_WRITE_IDEMPOTENT_THRESHOLD = 0.30
START_INDEX_STORE_CHILD_SHARE_THRESHOLD = 0.40
START_INDEX_STORE_UNEXPLAINED_THRESHOLD = 0.10
START_INDEX_STORE_CHILD_MARGIN_THRESHOLD = 0.05
START_INDEX_STORE_CLEAR_OVERWRITE_SHARE_THRESHOLD = 0.30
STATE_UPDATE_UNEXPLAINED_THRESHOLD = 0.10
PRODUCTION_STATE_UPDATE_UNEXPLAINED_THRESHOLD = 0.50
STATE_UPDATE_CHILD_SHARE_THRESHOLD = 0.40
PRODUCTION_STATE_UPDATE_CHILD_MARGIN_THRESHOLD = 0.05
STATE_UPDATE_BOOKKEEPING_SHARE_THRESHOLD = 0.40
FULL_PROBE_UNEXPLAINED_THRESHOLD = 0.10
FULL_PROBE_SCAN_SHARE_THRESHOLD = 0.40
FULL_PROBE_COMPARE_SHARE_THRESHOLD = 0.40
FULL_PROBE_BRANCH_SHARE_THRESHOLD = 0.40
FULL_PROBE_REDUNDANT_REPROBE_THRESHOLD = 0.30
FULL_PROBE_FULL_SCAN_SHARE_THRESHOLD = 0.50
FULL_PROBE_SLOTS_SCANNED_P90_THRESHOLD = 64.0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-mode-ab-summary", required=True)
    parser.add_argument("--candidate-index-lifecycle-summary", required=True)
    parser.add_argument("--terminal-telemetry-classification-decision")
    parser.add_argument("--state-update-bookkeeping-classification-decision")
    parser.add_argument("--candidate-index-structural-phase-decision")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--share-threshold-of-total-seconds",
        type=float,
        default=0.03,
    )
    return parser.parse_args()


def read_json(path_text):
    path = Path(path_text)
    if not path.is_file():
        raise RollupInputError(f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8")), path


def require_float(mapping, key):
    value = mapping.get(key, None)
    if value is None:
        raise RollupInputError(f"missing float field: {key}")
    return float(value)


def require_str(mapping, key):
    value = mapping.get(key, None)
    if value is None or str(value).strip() == "":
        raise RollupInputError(f"missing string field: {key}")
    return str(value)


def optional_str(mapping, key, default="unknown"):
    value = mapping.get(key, None)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def share_of_total(share_of_candidate_index, candidate_index_share_of_total_seconds):
    return share_of_candidate_index * candidate_index_share_of_total_seconds


def share_of_count(numerator, denominator):
    denominator_value = float(denominator)
    if denominator_value <= 0.0:
        return 0.0
    return float(numerator) / denominator_value


def build_row(
    *,
    path,
    share_of_candidate_index,
    candidate_index_share_of_total_seconds,
    closure_status,
    overhead_status,
    dominance_status,
    subtree_status,
    attempt_count,
    branch_kind,
    branch_actionability,
    threshold,
):
    share_total_seconds = share_of_total(
        share_of_candidate_index, candidate_index_share_of_total_seconds
    )
    eligible = (
        overhead_status == "ok"
        and closure_status == "closed"
        and subtree_status not in {"distributed_overhead_no_stable_leaf", "exhausted"}
        and share_total_seconds >= threshold
    )
    if subtree_status in {"distributed_overhead_no_stable_leaf", "exhausted"}:
        recommended_action = "stop_splitting"
    elif share_total_seconds < threshold:
        recommended_action = "below_material_threshold"
    elif branch_actionability == "classify_first" and eligible:
        recommended_action = "classify_branch_before_profiling"
    elif eligible:
        recommended_action = "candidate_for_backtrack_selection"
    else:
        recommended_action = "inspect_branch_rollup_missing_fields"
    return {
        "path": path,
        "share_of_candidate_index": share_of_candidate_index,
        "share_of_total_seconds": share_total_seconds,
        "closure_status": closure_status,
        "overhead_status": overhead_status,
        "dominance_status": dominance_status,
        "subtree_status": subtree_status,
        "attempt_count": attempt_count,
        "branch_kind": branch_kind,
        "branch_actionability": branch_actionability,
        "eligible_for_selection": eligible,
        "recommended_action": recommended_action,
    }


def classification_override(classification_decision):
    if not isinstance(classification_decision, dict):
        return None
    if classification_decision.get("decision_status") != "ready":
        return None
    if classification_decision.get("current_branch") != "terminal_path_telemetry_overhead":
        return None

    branch_kind = optional_str(
        classification_decision, "telemetry_branch_kind", "unknown"
    )
    recommended_next_action = optional_str(
        classification_decision, "recommended_next_action", "unknown"
    )
    if branch_kind == "profiler_only_overhead":
        return {
            "current_classified_branch": "terminal_path_telemetry_overhead",
            "branch_kind": "profiler_only_overhead",
            "branch_actionability": "reduce_profiler_overhead_first",
            "row_recommended_action": "reduce_profiler_overhead_first",
            "top_level_recommended_next_action": recommended_next_action,
        }
    return {
        "current_classified_branch": "terminal_path_telemetry_overhead",
        "branch_kind": branch_kind,
        "branch_actionability": "classified",
        "row_recommended_action": recommended_next_action,
        "top_level_recommended_next_action": recommended_next_action,
    }


def state_update_classification_action(classification_decision):
    if not isinstance(classification_decision, dict):
        return None
    if classification_decision.get("decision_status") != "ready":
        return None
    if classification_decision.get("current_branch") != "terminal_path_state_update":
        return None
    return optional_str(classification_decision, "recommended_next_action", "")


def is_start_index_branch_local_action(action):
    if not action:
        return False
    return action.startswith(
        (
            "profile_start_index_",
            "inspect_start_index_",
            "prototype_start_index_",
        )
    ) or action in {
        "mark_start_index_store_as_distributed_store_overhead",
        "resolve_start_index_store_dominance_conflict",
        "no_runtime_prototype_selected",
    }


def infer_start_index_branch_local_action(candidate):
    if not isinstance(candidate, dict):
        return None

    if candidate.get("terminal_path_start_index_write_sampled_count_closure_status") != "closed":
        return "inspect_start_index_write_timer_scope"
    if (
        float(candidate.get("terminal_path_start_index_write_unexplained_share", 0.0))
        >= START_INDEX_WRITE_UNEXPLAINED_THRESHOLD
    ):
        return "inspect_start_index_write_timer_scope"
    if (
        float(candidate.get("terminal_path_start_index_write_probe_or_locate_share", 0.0))
        >= START_INDEX_WRITE_CHILD_SHARE_THRESHOLD
    ):
        return "profile_start_index_probe_or_locate_path"
    if (
        float(candidate.get("terminal_path_start_index_write_entry_store_share", 0.0))
        >= START_INDEX_WRITE_CHILD_SHARE_THRESHOLD
    ):
        store_closure_status = optional_str(
            candidate, "terminal_path_start_index_store_sampled_count_closure_status"
        )
        if store_closure_status == "unknown":
            return "profile_start_index_store_path"
        if store_closure_status != "closed":
            return "inspect_start_index_store_timer_scope"
        if (
            float(candidate.get("terminal_path_start_index_store_unexplained_share", 0.0))
            >= START_INDEX_STORE_UNEXPLAINED_THRESHOLD
        ):
            return "inspect_start_index_store_timer_scope"
        if (
            float(
                candidate.get(
                    "terminal_path_start_index_store_clear_then_overwrite_same_entry_share",
                    0.0,
                )
            )
            >= START_INDEX_STORE_CLEAR_OVERWRITE_SHARE_THRESHOLD
        ):
            return "profile_start_index_clear_overwrite_write_amplification"
        store_dominance_status = optional_str(
            candidate, "terminal_path_start_index_store_dominance_status", "unknown"
        )
        store_margin_share = float(
            candidate.get("terminal_path_start_index_store_child_margin_share", 0.0)
        )
        store_dominant_child = optional_str(
            candidate,
            "terminal_path_start_index_store_seconds_weighted_dominant_child",
            optional_str(candidate, "terminal_path_start_index_store_dominant_child", "unknown"),
        )
        if store_dominance_status == "near_tie":
            return "mark_start_index_store_as_distributed_store_overhead"
        if store_dominance_status == "case_weighted_aggregate_conflict":
            return "resolve_start_index_store_dominance_conflict"
        if (
            store_dominance_status == "stable"
            and store_margin_share >= START_INDEX_STORE_CHILD_MARGIN_THRESHOLD
        ):
            if store_dominant_child == "insert":
                return "profile_start_index_insert_store_path"
            if store_dominant_child == "clear":
                return "profile_start_index_clear_store_path"
            if store_dominant_child == "overwrite":
                return "profile_start_index_overwrite_store_path"
        if store_dominance_status == "unknown":
            if (
                float(candidate.get("terminal_path_start_index_store_insert_share", 0.0))
                >= START_INDEX_STORE_CHILD_SHARE_THRESHOLD
            ):
                return "profile_start_index_insert_store_path"
            if (
                float(candidate.get("terminal_path_start_index_store_clear_share", 0.0))
                >= START_INDEX_STORE_CHILD_SHARE_THRESHOLD
            ):
                return "profile_start_index_clear_store_path"
            if (
                float(candidate.get("terminal_path_start_index_store_overwrite_share", 0.0))
                >= START_INDEX_STORE_CHILD_SHARE_THRESHOLD
            ):
                return "profile_start_index_overwrite_store_path"
            return "profile_start_index_store_path"
        return "no_runtime_prototype_selected"

    idempotent_share = share_of_count(
        candidate.get("terminal_path_start_index_write_idempotent_count", 0),
        candidate.get("terminal_path_start_index_write_count", 0),
    )
    if idempotent_share >= START_INDEX_WRITE_IDEMPOTENT_THRESHOLD:
        return "prototype_start_index_idempotent_write_skip_shadow"
    return "profile_start_index_bookkeeping_path"


def resolve_start_index_branch_local_action(lifecycle_summary, candidate):
    lifecycle_action = optional_str(lifecycle_summary, "recommended_next_action", "")
    if is_start_index_branch_local_action(lifecycle_action):
        return lifecycle_action
    return infer_start_index_branch_local_action(candidate)


def is_full_probe_branch_local_action(action):
    return action in {
        "inspect_lookup_miss_candidate_set_full_probe_timer_scope",
        "profile_candidate_set_full_scan_path",
        "profile_candidate_set_probe_compare_path",
        "profile_lookup_miss_probe_branch_path",
        "prototype_redundant_full_probe_skip_shadow",
        "no_single_stable_leaf_found_under_current_profiler",
    }


def infer_full_probe_branch_local_action(candidate):
    if not isinstance(candidate, dict):
        return None
    closure_status = optional_str(
        candidate, "lookup_miss_candidate_set_full_probe_sampled_count_closure_status", "unknown"
    )
    if closure_status == "unknown":
        return None
    if closure_status != "closed":
        return "inspect_lookup_miss_candidate_set_full_probe_timer_scope"
    if (
        float(candidate.get("lookup_miss_candidate_set_full_probe_unexplained_share", 0.0))
        >= FULL_PROBE_UNEXPLAINED_THRESHOLD
    ):
        return "inspect_lookup_miss_candidate_set_full_probe_timer_scope"
    if (
        float(candidate.get("lookup_miss_candidate_set_full_probe_full_scan_share", 0.0))
        >= FULL_PROBE_FULL_SCAN_SHARE_THRESHOLD
        or float(candidate.get("lookup_miss_candidate_set_full_probe_slots_scanned_p90", 0.0))
        >= FULL_PROBE_SLOTS_SCANNED_P90_THRESHOLD
    ):
        return "profile_candidate_set_full_scan_path"
    if (
        float(candidate.get("lookup_miss_candidate_set_full_probe_scan_share", 0.0))
        >= FULL_PROBE_SCAN_SHARE_THRESHOLD
    ):
        return "profile_candidate_set_full_scan_path"
    if (
        float(candidate.get("lookup_miss_candidate_set_full_probe_compare_share", 0.0))
        >= FULL_PROBE_COMPARE_SHARE_THRESHOLD
    ):
        return "profile_candidate_set_probe_compare_path"
    if (
        float(candidate.get("lookup_miss_candidate_set_full_probe_branch_or_guard_share", 0.0))
        >= FULL_PROBE_BRANCH_SHARE_THRESHOLD
    ):
        return "profile_lookup_miss_probe_branch_path"
    if (
        float(
            candidate.get("lookup_miss_candidate_set_full_probe_redundant_reprobe_share", 0.0)
        )
        >= FULL_PROBE_REDUNDANT_REPROBE_THRESHOLD
    ):
        return "prototype_redundant_full_probe_skip_shadow"
    return "no_single_stable_leaf_found_under_current_profiler"


def resolve_full_probe_branch_local_action(lifecycle_summary, candidate):
    lifecycle_action = optional_str(lifecycle_summary, "recommended_next_action", "")
    if is_full_probe_branch_local_action(lifecycle_action):
        return lifecycle_action
    return infer_full_probe_branch_local_action(candidate)


def is_state_update_branch_local_action(action):
    return action in {
        "inspect_terminal_path_state_update_timer_scope",
        "classify_terminal_path_state_update_bookkeeping",
        "profile_production_state_update_bookkeeping_path",
        "inspect_production_state_update_timer_scope",
        "reduce_or_cold_path_benchmark_state_update_counters",
        "profile_trace_replay_required_state_update_path",
        "profile_heap_update_path",
        "profile_heap_build_path",
        "profile_start_index_rebuild_path",
        "mark_terminal_path_state_update_as_distributed_overhead",
        "mark_production_state_update_as_distributed_overhead",
    }


def infer_terminal_path_state_update_branch_local_action(candidate):
    if not isinstance(candidate, dict):
        return None
    closure_status = optional_str(
        candidate, "terminal_path_state_update_sampled_count_closure_status", "unknown"
    )
    if closure_status == "unknown":
        return None
    if closure_status != "closed":
        return "inspect_terminal_path_state_update_timer_scope"
    if (
        float(candidate.get("terminal_path_state_update_unexplained_share", 0.0))
        >= STATE_UPDATE_UNEXPLAINED_THRESHOLD
    ):
        return "inspect_terminal_path_state_update_timer_scope"
    if (
        float(
            candidate.get(
                "terminal_path_state_update_trace_or_profile_bookkeeping_share", 0.0
            )
        )
        >= STATE_UPDATE_BOOKKEEPING_SHARE_THRESHOLD
    ):
        if (
            optional_str(candidate, "production_state_update_coverage_source", "placeholder")
            != "event_level_sampled"
        ):
            return "classify_terminal_path_state_update_bookkeeping"
        if (
            optional_str(
                candidate,
                "production_state_update_sampled_count_closure_status",
                "unknown",
            )
            != "closed"
        ):
            return "inspect_production_state_update_timer_scope"
        if (
            float(candidate.get("production_state_update_unexplained_share", 0.0))
            >= PRODUCTION_STATE_UPDATE_UNEXPLAINED_THRESHOLD
        ):
            return "inspect_production_state_update_timer_scope"
        production_state_update_dominance_status = optional_str(
            candidate, "production_state_update_dominance_status", "unknown"
        )
        production_state_update_margin_share = float(
            candidate.get("production_state_update_child_margin_share", 0.0)
        )
        production_state_update_dominant_child = optional_str(
            candidate,
            "production_state_update_seconds_weighted_dominant_child",
            optional_str(candidate, "production_state_update_dominant_child", "unknown"),
        )
        if production_state_update_dominance_status in {
            "near_tie",
            "case_weighted_aggregate_conflict",
        }:
            return "mark_production_state_update_as_distributed_overhead"
        if (
            production_state_update_dominance_status == "stable"
            and production_state_update_margin_share
            >= PRODUCTION_STATE_UPDATE_CHILD_MARGIN_THRESHOLD
        ):
            if production_state_update_dominant_child == "benchmark_counter":
                return "reduce_or_cold_path_benchmark_state_update_counters"
            if production_state_update_dominant_child == "trace_replay_required_state":
                return "profile_trace_replay_required_state_update_path"
        if (
            production_state_update_dominance_status == "unknown"
            and float(candidate.get("production_state_update_benchmark_counter_share", 0.0))
            >= STATE_UPDATE_CHILD_SHARE_THRESHOLD
        ):
            return "reduce_or_cold_path_benchmark_state_update_counters"
        if (
            production_state_update_dominance_status == "unknown"
            and float(
                candidate.get("production_state_update_trace_replay_required_state_share", 0.0)
            )
            >= STATE_UPDATE_CHILD_SHARE_THRESHOLD
        ):
            return "profile_trace_replay_required_state_update_path"
        if (
            float(
                candidate.get(
                    "production_state_update_trace_replay_required_state_share", 0.0
                )
            )
            >= STATE_UPDATE_CHILD_SHARE_THRESHOLD
            and production_state_update_dominance_status == "unknown"
        ):
            return "profile_trace_replay_required_state_update_path"
        return "mark_production_state_update_as_distributed_overhead"
    if (
        float(candidate.get("terminal_path_state_update_heap_update_share", 0.0))
        >= STATE_UPDATE_CHILD_SHARE_THRESHOLD
    ):
        return "profile_heap_update_path"
    if (
        float(candidate.get("terminal_path_state_update_heap_build_share", 0.0))
        >= STATE_UPDATE_CHILD_SHARE_THRESHOLD
    ):
        return "profile_heap_build_path"
    if (
        float(candidate.get("terminal_path_state_update_start_index_rebuild_share", 0.0))
        >= STATE_UPDATE_CHILD_SHARE_THRESHOLD
    ):
        return "profile_start_index_rebuild_path"
    return "mark_terminal_path_state_update_as_distributed_overhead"


def resolve_terminal_path_state_update_branch_local_action(lifecycle_summary, candidate):
    lifecycle_action = optional_str(lifecycle_summary, "recommended_next_action", "")
    if is_state_update_branch_local_action(lifecycle_action):
        return lifecycle_action
    return infer_terminal_path_state_update_branch_local_action(candidate)


def build_rows(
    ab_summary,
    lifecycle_summary,
    threshold,
    terminal_telemetry_classification,
    state_update_bookkeeping_classification,
    structural_phase_decision,
):
    candidate = lifecycle_summary.get("candidate_index", None)
    if not isinstance(candidate, dict):
        raise RollupInputError("candidate_index lifecycle summary missing candidate_index object")

    candidate_seconds = require_float(candidate, "seconds")
    candidate_share_total_seconds = require_float(candidate, "share_of_total_seconds")
    overhead_status = require_str(ab_summary, "profile_mode_overhead_status")
    terminal_closure_status = optional_str(
        candidate, "terminal_timer_closure_status", optional_str(lifecycle_summary, "terminal_timer_closure_status", "unknown")
    )

    rows = []

    gap_parent_seconds = require_float(
        ab_summary, "terminal_first_half_span_a0_gap_before_a00_parent_seconds"
    )
    span_0_share = require_float(
        ab_summary, "terminal_first_half_span_a0_gap_before_a00_span_0_share"
    )
    alt_left_share = require_float(ab_summary, "gap_before_a00_span_0_alt_left_share")
    alt_right_share = require_float(ab_summary, "gap_before_a00_span_0_alt_right_share")

    alt_left_share_of_candidate = (
        gap_parent_seconds * span_0_share * alt_left_share / candidate_seconds
    )
    alt_right_share_of_candidate = (
        gap_parent_seconds * span_0_share * alt_right_share / candidate_seconds
    )

    alt_right_subtree_status = optional_str(
        ab_summary, "gap_before_a00_span_0_alt_right_subtree_status", "unknown"
    )
    alt_right_attempt_count = int(
        float(
            ab_summary.get(
                "gap_before_a00_span_0_alt_right_repartition_attempt_count", 0
            )
        )
    )
    alt_right_closure_status = optional_str(
        ab_summary,
        "gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status",
        optional_str(
            ab_summary,
            "gap_before_a00_span_0_alt_right_sampled_count_closure_status",
            "unknown",
        ),
    )

    rows.append(
        build_row(
            path="gap_before_a00_span_0_alt_right",
            share_of_candidate_index=alt_right_share_of_candidate,
            candidate_index_share_of_total_seconds=candidate_share_total_seconds,
            closure_status=alt_right_closure_status,
            overhead_status=overhead_status,
            dominance_status=optional_str(
                ab_summary, "gap_before_a00_span_0_alt_right_dominance_status"
            ),
            subtree_status=alt_right_subtree_status,
            attempt_count=alt_right_attempt_count,
            branch_kind="exhausted",
            branch_actionability="exhausted",
            threshold=threshold,
        )
    )
    rows.append(
        build_row(
            path="gap_before_a00_span_0_alt_left",
            share_of_candidate_index=alt_left_share_of_candidate,
            candidate_index_share_of_total_seconds=candidate_share_total_seconds,
            closure_status=optional_str(
                ab_summary, "gap_before_a00_span_0_alt_sampled_count_closure_status", "unknown"
            ),
            overhead_status=overhead_status,
            dominance_status="backtracked_sibling",
            subtree_status="not_profiled",
            attempt_count=0,
            branch_kind="runtime_candidate",
            branch_actionability="not_material",
            threshold=threshold,
        )
    )

    terminal_telemetry_override = classification_override(
        terminal_telemetry_classification
    )

    lifecycle_branches = [
        (
            "terminal_path_candidate_slot_write",
            "terminal_path_candidate_slot_write_share_of_candidate_index",
            "runtime_candidate",
            "actionable",
        ),
        (
            "terminal_path_start_index_write",
            "terminal_path_start_index_write_share_of_candidate_index",
            "runtime_candidate",
            "actionable",
        ),
        (
            "terminal_path_state_update",
            "terminal_path_state_update_share_of_candidate_index",
            "runtime_candidate",
            "actionable",
        ),
        (
            "terminal_path_telemetry_overhead",
            "terminal_path_telemetry_overhead_share_of_candidate_index",
            (
                terminal_telemetry_override["branch_kind"]
                if terminal_telemetry_override
                else "unknown"
            ),
            (
                terminal_telemetry_override["branch_actionability"]
                if terminal_telemetry_override
                else "classify_first"
            ),
        ),
        (
            "lookup_miss_candidate_set_full_probe",
            "lookup_miss_candidate_set_full_probe_share_of_candidate_index",
            "runtime_candidate",
            "actionable",
        ),
    ]
    for path_name, share_key, branch_kind, branch_actionability in lifecycle_branches:
        rows.append(
            build_row(
                path=path_name,
                share_of_candidate_index=require_float(candidate, share_key),
                candidate_index_share_of_total_seconds=candidate_share_total_seconds,
                closure_status=terminal_closure_status,
                overhead_status=overhead_status,
                dominance_status="stable_leaf",
                subtree_status="not_profiled",
                attempt_count=0,
                branch_kind=branch_kind,
                branch_actionability=branch_actionability,
                threshold=threshold,
            )
        )

    if terminal_telemetry_override:
        for row in rows:
            if row["path"] == "terminal_path_telemetry_overhead":
                row["recommended_action"] = terminal_telemetry_override[
                    "row_recommended_action"
                ]
                break

    start_index_branch_local_action = resolve_start_index_branch_local_action(
        lifecycle_summary, candidate
    )
    full_probe_branch_local_action = resolve_full_probe_branch_local_action(
        lifecycle_summary, candidate
    )
    state_update_branch_local_action = resolve_terminal_path_state_update_branch_local_action(
        lifecycle_summary, candidate
    )
    state_update_classification_recommended_action = state_update_classification_action(
        state_update_bookkeeping_classification
    )
    if start_index_branch_local_action == "mark_start_index_store_as_distributed_store_overhead":
        for index, row in enumerate(rows):
            if row["path"] != "terminal_path_start_index_write":
                continue
            rows[index] = build_row(
                path="terminal_path_start_index_write",
                share_of_candidate_index=row["share_of_candidate_index"],
                candidate_index_share_of_total_seconds=candidate_share_total_seconds,
                closure_status=row["closure_status"],
                overhead_status=overhead_status,
                dominance_status=optional_str(
                    candidate, "terminal_path_start_index_store_dominance_status", "unknown"
                ),
                subtree_status="distributed_overhead_no_stable_leaf",
                attempt_count=0,
                branch_kind="distributed_store_overhead",
                branch_actionability="exhausted",
                threshold=threshold,
            )
            break
    if state_update_branch_local_action in {
        "mark_terminal_path_state_update_as_distributed_overhead",
        "mark_production_state_update_as_distributed_overhead",
    }:
        dominance_key = (
            "production_state_update_dominant_child"
            if state_update_branch_local_action
            == "mark_production_state_update_as_distributed_overhead"
            else "terminal_path_state_update_dominant_child"
        )
        for index, row in enumerate(rows):
            if row["path"] != "terminal_path_state_update":
                continue
            rows[index] = build_row(
                path="terminal_path_state_update",
                share_of_candidate_index=row["share_of_candidate_index"],
                candidate_index_share_of_total_seconds=candidate_share_total_seconds,
                closure_status=row["closure_status"],
                overhead_status=overhead_status,
                dominance_status=optional_str(candidate, dominance_key, "unknown"),
                subtree_status="distributed_overhead_no_stable_leaf",
                attempt_count=0,
                branch_kind=(
                    "distributed_production_state_update_overhead"
                    if state_update_branch_local_action
                    == "mark_production_state_update_as_distributed_overhead"
                    else "distributed_state_update_overhead"
                ),
                branch_actionability="exhausted",
                threshold=threshold,
            )
            break

    eligible_rows = sorted(
        (row for row in rows if row["eligible_for_selection"]),
        key=lambda row: (-row["share_of_total_seconds"], row["path"]),
    )

    for index, row in enumerate(eligible_rows, start=1):
        row["selection_rank"] = index
    for row in rows:
        row.setdefault("selection_rank", "")

    current_exhausted_subtrees = [
        row["path"]
        for row in rows
        if row["subtree_status"] == "distributed_overhead_no_stable_leaf"
    ]
    current_exhausted_subtree = (
        current_exhausted_subtrees[0] if current_exhausted_subtrees else None
    )

    optional_next_action = None
    leaf_level_candidate_index_profiling_detail = None

    if eligible_rows:
        selected_row = eligible_rows[0]
        next_candidate_branch = selected_row["path"]
        next_candidate_branch_decision = None
        if (
            next_candidate_branch == "lookup_miss_candidate_set_full_probe"
            and full_probe_branch_local_action
            == "no_single_stable_leaf_found_under_current_profiler"
        ):
            if len(eligible_rows) == 1:
                next_candidate_branch_decision = full_probe_branch_local_action
                recommended_next_action = "stop_leaf_level_candidate_index_profiling"
                optional_next_action = "profile_candidate_index_common_memory_behavior"
                leaf_level_candidate_index_profiling_detail = (
                    "candidate_index_material_but_no_single_stable_leaf_found"
                )
            else:
                selected_row = eligible_rows[1]
                next_candidate_branch = selected_row["path"]
        if leaf_level_candidate_index_profiling_detail is not None:
            pass
        elif selected_row["branch_actionability"] == "classify_first":
            recommended_next_action = f"classify_{next_candidate_branch}"
        elif selected_row["branch_actionability"] == "reduce_profiler_overhead_first":
            recommended_next_action = terminal_telemetry_override[
                "top_level_recommended_next_action"
            ]
        elif (
            next_candidate_branch == "terminal_path_start_index_write"
            and start_index_branch_local_action is not None
        ):
            next_candidate_branch_decision = start_index_branch_local_action
            recommended_next_action = next_candidate_branch_decision
        elif next_candidate_branch == "terminal_path_start_index_write":
            next_candidate_branch_decision = infer_start_index_branch_local_action(candidate)
            if next_candidate_branch_decision is not None:
                recommended_next_action = next_candidate_branch_decision
            else:
                recommended_next_action = "profile_next_stable_material_branch"
        elif (
            next_candidate_branch == "lookup_miss_candidate_set_full_probe"
            and full_probe_branch_local_action is not None
        ):
            next_candidate_branch_decision = full_probe_branch_local_action
            recommended_next_action = next_candidate_branch_decision
        elif next_candidate_branch == "lookup_miss_candidate_set_full_probe":
            recommended_next_action = "profile_lookup_miss_candidate_set_full_probe"
        elif (
            next_candidate_branch == "terminal_path_state_update"
            and state_update_branch_local_action is not None
        ):
            if (
                state_update_branch_local_action
                == "classify_terminal_path_state_update_bookkeeping"
                and state_update_classification_recommended_action
            ):
                next_candidate_branch_decision = (
                    state_update_classification_recommended_action
                )
            else:
                next_candidate_branch_decision = state_update_branch_local_action
            recommended_next_action = next_candidate_branch_decision
        elif next_candidate_branch == "terminal_path_state_update":
            recommended_next_action = "profile_terminal_path_state_update"
        elif start_index_branch_local_action == "mark_start_index_store_as_distributed_store_overhead":
            recommended_next_action = "select_next_material_branch"
        else:
            recommended_next_action = "profile_next_stable_material_branch"
    else:
        next_candidate_branch = None
        next_candidate_branch_decision = None
        recommended_next_action = "no_single_stable_leaf_found_under_current_profiler"

    leaf_level_candidate_index_profiling_status = "active"
    active_frontier = next_candidate_branch
    stop_reason = None
    if recommended_next_action in {
        "stop_leaf_level_candidate_index_profiling",
        "no_single_stable_leaf_found_under_current_profiler",
    }:
        leaf_level_candidate_index_profiling_status = "stopped"
        active_frontier = None
        stop_reason = next_candidate_branch_decision or recommended_next_action

    current_phase = "leaf_level_candidate_index_profiling"
    current_phase_status = "active"
    current_focus = next_candidate_branch
    phase_transition_reason = None
    structural_context_status = "missing"
    if leaf_level_candidate_index_profiling_status == "stopped":
        current_phase = "candidate_index_structural_profiling"
        current_phase_status = "active"
        current_focus = "operation_rollup"
        phase_transition_reason = "leaf_level_candidate_index_profiling_stopped"
        recommended_next_action = "profile_candidate_index_operation_rollup"
        structural_context_status = "ready"
        if isinstance(structural_phase_decision, dict) and structural_phase_decision.get(
            "decision_status"
        ) == "ready":
            current_phase_status = optional_str(
                structural_phase_decision, "phase_status", "active"
            )
            focus_value = structural_phase_decision.get("current_focus")
            current_focus = focus_value if focus_value not in {"", "unknown"} else None
            recommended_next_action = optional_str(
                structural_phase_decision,
                "recommended_next_action",
                recommended_next_action,
            )
            optional_value = structural_phase_decision.get("optional_next_action")
            optional_next_action = (
                str(optional_value).strip()
                if optional_value is not None and str(optional_value).strip() != ""
                else None
            )
            structural_stop_reason = structural_phase_decision.get("stop_reason")
            if structural_stop_reason is not None and str(structural_stop_reason).strip() != "":
                stop_reason = str(structural_stop_reason).strip()
            if current_phase_status == "stopped":
                active_frontier = None
            structural_context_status = "provided"

    current_classified_branch = (
        terminal_telemetry_override["current_classified_branch"]
        if terminal_telemetry_override
        else None
    )
    exhausted_or_non_actionable_branches = []
    for path in current_exhausted_subtrees:
        if path and path not in exhausted_or_non_actionable_branches:
            exhausted_or_non_actionable_branches.append(path)
    if (
        current_classified_branch
        and current_classified_branch not in exhausted_or_non_actionable_branches
    ):
        exhausted_or_non_actionable_branches.append(current_classified_branch)
    if stop_reason and next_candidate_branch:
        if next_candidate_branch not in exhausted_or_non_actionable_branches:
            exhausted_or_non_actionable_branches.append(next_candidate_branch)

    rows.sort(key=lambda row: (-row["share_of_total_seconds"], row["path"]))

    return {
        "rows": rows,
        "current_exhausted_subtree": current_exhausted_subtree,
        "current_exhausted_subtrees": current_exhausted_subtrees,
        "current_classified_branch": current_classified_branch,
        "next_candidate_branch": next_candidate_branch,
        "next_candidate_branch_decision": next_candidate_branch_decision,
        "active_frontier": active_frontier,
        "stop_reason": stop_reason,
        "exhausted_or_non_actionable_branches": exhausted_or_non_actionable_branches,
        "recommended_next_action": recommended_next_action,
        "optional_next_action": optional_next_action,
        "leaf_level_candidate_index_profiling_status": leaf_level_candidate_index_profiling_status,
        "leaf_level_candidate_index_profiling_detail": (
            leaf_level_candidate_index_profiling_detail
        ),
        "current_phase": current_phase,
        "current_phase_status": current_phase_status,
        "current_focus": current_focus,
        "phase_transition_reason": phase_transition_reason,
        "structural_phase_decision_context_status": structural_context_status,
        "selection_threshold_share_of_total_seconds": threshold,
        "candidate_index_materiality_status": optional_str(
            ab_summary, "candidate_index_materiality_status", "unknown"
        ),
        "runtime_prototype_allowed": False,
        "profile_mode_overhead_status": overhead_status,
        "trusted_span_timing": bool(ab_summary.get("trusted_span_timing", False)),
        "trusted_span_source": optional_str(ab_summary, "trusted_span_source", "none"),
    }


def render_markdown(summary):
    lines = [
        "# SIM Initial Host Merge Profile Branch Rollup",
        "",
        f"- current_exhausted_subtree: `{summary.get('current_exhausted_subtree') or 'none'}`",
        f"- current_exhausted_subtrees: `{', '.join(summary.get('current_exhausted_subtrees', [])) or 'none'}`",
        f"- current_classified_branch: `{summary.get('current_classified_branch') or 'none'}`",
        f"- next_candidate_branch: `{summary.get('next_candidate_branch') or 'none'}`",
        f"- next_candidate_branch_decision: `{summary.get('next_candidate_branch_decision') or 'none'}`",
        f"- active_frontier: `{summary.get('active_frontier') or 'none'}`",
        f"- stop_reason: `{summary.get('stop_reason') or 'none'}`",
        f"- current_phase: `{summary.get('current_phase') or 'unknown'}`",
        f"- current_phase_status: `{summary.get('current_phase_status') or 'unknown'}`",
        f"- current_focus: `{summary.get('current_focus') or 'none'}`",
        f"- phase_transition_reason: `{summary.get('phase_transition_reason') or 'none'}`",
        f"- exhausted_or_non_actionable_branches: `{', '.join(summary.get('exhausted_or_non_actionable_branches', [])) or 'none'}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- leaf_level_candidate_index_profiling_status: `{summary.get('leaf_level_candidate_index_profiling_status') or 'unknown'}`",
        f"- leaf_level_candidate_index_profiling_detail: `{summary.get('leaf_level_candidate_index_profiling_detail') or 'none'}`",
        f"- runtime_prototype_allowed: `{str(summary.get('runtime_prototype_allowed', False)).lower()}`",
        f"- selection_threshold_share_of_total_seconds: `{summary['selection_threshold_share_of_total_seconds']:.6f}`",
        "",
        "| path | share_of_candidate_index | share_of_total_seconds | closure_status | dominance_status | subtree_status | branch_kind | branch_actionability | eligible | action |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary["rows"]:
        lines.append(
            "| "
            + f"{row['path']} | "
            + f"{row['share_of_candidate_index']:.6f} | "
            + f"{row['share_of_total_seconds']:.6f} | "
            + f"{row['closure_status']} | "
            + f"{row['dominance_status']} | "
            + f"{row['subtree_status']} | "
            + f"{row['branch_kind']} | "
            + f"{row['branch_actionability']} | "
            + f"{str(row['eligible_for_selection']).lower()} | "
            + f"{row['recommended_action']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ab_summary, ab_path = read_json(args.profile_mode_ab_summary)
    lifecycle_summary, lifecycle_path = read_json(args.candidate_index_lifecycle_summary)
    terminal_telemetry_classification, terminal_telemetry_classification_path = (
        read_json(args.terminal_telemetry_classification_decision)
        if args.terminal_telemetry_classification_decision
        else ({}, None)
    )
    state_update_bookkeeping_classification, state_update_bookkeeping_classification_path = (
        read_json(args.state_update_bookkeeping_classification_decision)
        if args.state_update_bookkeeping_classification_decision
        else ({}, None)
    )
    structural_phase_decision, structural_phase_decision_path = (
        read_json(args.candidate_index_structural_phase_decision)
        if args.candidate_index_structural_phase_decision
        else ({}, None)
    )

    summary = build_rows(
        ab_summary,
        lifecycle_summary,
        args.share_threshold_of_total_seconds,
        terminal_telemetry_classification,
        state_update_bookkeeping_classification,
        structural_phase_decision,
    )
    summary["decision_status"] = "ready"
    summary["source_profile_mode_ab_summary"] = str(ab_path)
    summary["source_candidate_index_lifecycle_summary"] = str(lifecycle_path)
    authoritative_sources = {
        "profile_mode_ab_summary": str(ab_path),
        "sampled_lifecycle_summary": str(lifecycle_path),
    }
    if terminal_telemetry_classification_path is not None:
        summary["source_terminal_telemetry_classification_decision"] = str(
            terminal_telemetry_classification_path
        )
        authoritative_sources["terminal_telemetry_classification_decision"] = str(
            terminal_telemetry_classification_path
        )
    if state_update_bookkeeping_classification_path is not None:
        summary["source_state_update_bookkeeping_classification_decision"] = str(
            state_update_bookkeeping_classification_path
        )
        authoritative_sources["state_update_bookkeeping_classification_decision"] = str(
            state_update_bookkeeping_classification_path
        )
    if structural_phase_decision_path is not None:
        summary["source_candidate_index_structural_phase_decision"] = str(
            structural_phase_decision_path
        )
        authoritative_sources["candidate_index_structural_phase_decision"] = str(
            structural_phase_decision_path
        )
    summary["authoritative_sources"] = authoritative_sources

    decision = {
        "decision_status": "ready",
        "current_exhausted_subtree": summary["current_exhausted_subtree"],
        "current_exhausted_subtrees": summary["current_exhausted_subtrees"],
        "current_classified_branch": summary["current_classified_branch"],
        "next_candidate_branch": summary["next_candidate_branch"],
        "next_candidate_branch_decision": summary["next_candidate_branch_decision"],
        "active_frontier": summary["active_frontier"],
        "stop_reason": summary["stop_reason"],
        "exhausted_or_non_actionable_branches": summary[
            "exhausted_or_non_actionable_branches"
        ],
        "current_phase": summary["current_phase"],
        "current_phase_status": summary["current_phase_status"],
        "current_focus": summary["current_focus"],
        "phase_transition_reason": summary["phase_transition_reason"],
        "structural_phase_decision_context_status": summary[
            "structural_phase_decision_context_status"
        ],
        "recommended_next_action": summary["recommended_next_action"],
        "optional_next_action": summary["optional_next_action"],
        "leaf_level_candidate_index_profiling_status": summary[
            "leaf_level_candidate_index_profiling_status"
        ],
        "leaf_level_candidate_index_profiling_detail": summary[
            "leaf_level_candidate_index_profiling_detail"
        ],
        "selection_threshold_share_of_total_seconds": summary[
            "selection_threshold_share_of_total_seconds"
        ],
        "candidate_index_materiality_status": summary[
            "candidate_index_materiality_status"
        ],
        "runtime_prototype_allowed": summary["runtime_prototype_allowed"],
        "profile_mode_overhead_status": summary["profile_mode_overhead_status"],
        "trusted_span_timing": summary["trusted_span_timing"],
        "trusted_span_source": summary["trusted_span_source"],
        "authoritative_sources": authoritative_sources,
    }

    with (output_dir / "branch_rollup.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "branch_rollup_decision.json").open("w", encoding="utf-8") as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with (output_dir / "branch_rollup.tsv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "path",
            "share_of_candidate_index",
            "share_of_total_seconds",
            "closure_status",
            "overhead_status",
            "dominance_status",
            "subtree_status",
            "attempt_count",
            "branch_kind",
            "branch_actionability",
            "eligible_for_selection",
            "selection_rank",
            "recommended_action",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(summary["rows"])
    (output_dir / "branch_rollup.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
