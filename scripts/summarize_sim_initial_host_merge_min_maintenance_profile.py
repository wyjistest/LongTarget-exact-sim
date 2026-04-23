#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


CASE_FIELDNAMES = [
    "case_id",
    "aggregate_tsv",
    "workload_id",
    "benchmark_source",
    "context_apply_mean_seconds",
    "sim_initial_scan_mean_seconds",
    "sim_initial_scan_cpu_merge_mean_seconds",
    "sim_initial_scan_cpu_merge_subtotal_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
    "full_set_miss_count",
    "full_set_miss_mean_seconds",
    "floor_changed_count",
    "floor_changed_share",
    "running_min_slot_changed_count",
    "running_min_slot_changed_share",
    "victim_was_running_min_count",
    "victim_was_running_min_share",
    "refresh_min_calls",
    "refresh_min_slots_scanned",
    "refresh_min_slots_scanned_per_call",
    "refresh_min_mean_seconds",
    "refresh_min_seconds_per_full_set_miss",
    "refresh_min_calls_per_full_set_miss",
    "refresh_min_slots_scanned_per_full_set_miss",
    "candidate_index_lookup_count",
    "candidate_index_hit_count",
    "candidate_index_miss_count",
    "candidate_index_erase_count",
    "candidate_index_insert_count",
    "candidate_index_mean_seconds",
    "candidate_index_erase_mean_seconds",
    "candidate_index_insert_mean_seconds",
    "candidate_index_seconds_per_full_set_miss",
    "candidate_index_lookups_per_full_set_miss",
    "candidate_index_erases_per_full_set_miss",
    "candidate_index_inserts_per_full_set_miss",
    "refresh_min_share_of_initial_cpu_merge",
    "candidate_index_share_of_initial_cpu_merge",
    "candidate_index_erase_share_of_candidate_index",
    "candidate_index_insert_share_of_candidate_index",
    "total_sim_mean_seconds",
    "initial_cpu_merge_share_of_sim_seconds",
    "initial_cpu_merge_share_of_total_seconds",
    "candidate_index_share_of_sim_seconds",
    "candidate_index_share_of_total_seconds",
    "materiality_status",
    "recommended_next_action",
]

MATERIALITY_BENCHMARK_FIELDS = [
    "sim_initial_scan_mean_seconds",
    "sim_initial_scan_cpu_merge_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
]

REQUIRED_FIELDS = [
    "case_id",
    "context_apply_mean_seconds",
    "context_apply_full_set_miss_mean_seconds",
    "context_apply_refresh_min_mean_seconds",
    "context_apply_candidate_index_mean_seconds",
    "context_apply_candidate_index_erase_mean_seconds",
    "context_apply_candidate_index_insert_mean_seconds",
    "context_apply_full_set_miss_count",
    "context_apply_floor_changed_count",
    "context_apply_floor_changed_share",
    "context_apply_running_min_slot_changed_count",
    "context_apply_running_min_slot_changed_share",
    "context_apply_victim_was_running_min_count",
    "context_apply_victim_was_running_min_share",
    "context_apply_refresh_min_calls",
    "context_apply_refresh_min_slots_scanned",
    "context_apply_refresh_min_slots_scanned_per_call",
    "context_apply_candidate_index_lookup_count",
    "context_apply_candidate_index_hit_count",
    "context_apply_candidate_index_miss_count",
    "context_apply_candidate_index_erase_count",
    "context_apply_candidate_index_insert_count",
    "verify_ok",
]


class ProfileInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate-tsv", action="append", required=True)
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prototype-share-threshold", type=float, default=0.15)
    parser.add_argument("--erase-dominant-share-threshold", type=float, default=0.50)
    parser.add_argument("--host-merge-materiality-threshold", type=float, default=0.05)
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
    raise ProfileInputError(f"invalid verify_ok value: {value!r}")


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    if not rows:
        raise ProfileInputError(f"{path}: no rows")
    missing = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
    if missing:
        raise ProfileInputError(f"{path}: missing required fields: {', '.join(missing)}")
    return rows


def to_float(row, field, path):
    try:
        return float(row[field])
    except (TypeError, ValueError) as exc:
        raise ProfileInputError(f"{path}: invalid float for {field}: {row.get(field)!r}") from exc


def to_int(row, field, path):
    try:
        return int(float(row[field]))
    except (TypeError, ValueError) as exc:
        raise ProfileInputError(f"{path}: invalid int for {field}: {row.get(field)!r}") from exc


def resolve_total_sim_seconds(row):
    for field in ("sim_seconds_mean_seconds", "sim_seconds_seconds", "sim_total_mean_seconds"):
        if field in row and str(row[field]).strip() != "":
            return float(row[field])
    return None


def resolve_optional_float(row, fields):
    for field in fields:
        if field in row and str(row[field]).strip() != "":
            return float(row[field])
    return None


def resolve_optional_text(row, field):
    return str(row.get(field, "")).strip()


def consistent_optional_metric(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return None
    first = values[0]
    for value in values[1:]:
        if abs(value - first) > 1e-12:
            raise ProfileInputError(f"inconsistent duplicated workload metric: {key}")
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
        raise ProfileInputError(
            f"{path}: case {case_id} has non-positive benchmark metric {field}: {value!r}"
        )


def consistent_group_metric(group_rows, metric_key):
    value = consistent_optional_metric(group_rows, metric_key)
    if value is None:
        raise ProfileInputError(f"missing grouped workload metric: {metric_key}")
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
    except ProfileInputError:
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


def grouped_optional_metric_from_pairing(groups, metric_key):
    if not groups:
        return None
    total = 0.0
    for group_rows in groups.values():
        value = consistent_optional_metric(group_rows, metric_key)
        if value is None:
            return None
        total += value
    return total


def recommended_next_action(
    refresh_share,
    candidate_share,
    erase_share_of_candidate,
    initial_cpu_merge_share_of_sim,
    args,
):
    if (
        initial_cpu_merge_share_of_sim is not None
        and initial_cpu_merge_share_of_sim < args.host_merge_materiality_threshold
    ):
        return "no_host_merge_runtime_work"
    if (
        refresh_share >= args.prototype_share_threshold
        and candidate_share >= args.prototype_share_threshold
    ):
        return "prototype_stable_min_maintenance"
    if refresh_share >= args.prototype_share_threshold:
        return "prototype_stable_min_maintenance"
    if candidate_share >= args.prototype_share_threshold:
        if erase_share_of_candidate >= args.erase_dominant_share_threshold:
            return "prototype_eager_index_erase_handle"
        return "profile_candidate_index_lifecycle"
    return "return_to_initial_run_summary_kernel"


def analyze_case(row, path, args):
    case_id = row["case_id"]
    verify_ok = parse_bool_like(row["verify_ok"])
    if not verify_ok:
        raise ProfileInputError(f"{path}: case {case_id} has verify_ok=0")

    context_apply_mean_seconds = to_float(row, "context_apply_mean_seconds", path)
    full_set_miss_mean_seconds = to_float(row, "context_apply_full_set_miss_mean_seconds", path)
    refresh_min_mean_seconds = to_float(row, "context_apply_refresh_min_mean_seconds", path)
    candidate_index_mean_seconds = to_float(row, "context_apply_candidate_index_mean_seconds", path)
    candidate_index_erase_mean_seconds = to_float(
        row, "context_apply_candidate_index_erase_mean_seconds", path
    )
    candidate_index_insert_mean_seconds = to_float(
        row, "context_apply_candidate_index_insert_mean_seconds", path
    )
    full_set_miss_count = to_int(row, "context_apply_full_set_miss_count", path)
    floor_changed_count = to_int(row, "context_apply_floor_changed_count", path)
    floor_changed_share = to_float(row, "context_apply_floor_changed_share", path)
    running_min_slot_changed_count = to_int(
        row, "context_apply_running_min_slot_changed_count", path
    )
    running_min_slot_changed_share = to_float(
        row, "context_apply_running_min_slot_changed_share", path
    )
    victim_was_running_min_count = to_int(
        row, "context_apply_victim_was_running_min_count", path
    )
    victim_was_running_min_share = to_float(
        row, "context_apply_victim_was_running_min_share", path
    )
    refresh_min_calls = to_int(row, "context_apply_refresh_min_calls", path)
    refresh_min_slots_scanned = to_int(row, "context_apply_refresh_min_slots_scanned", path)
    refresh_min_slots_scanned_per_call = to_float(
        row, "context_apply_refresh_min_slots_scanned_per_call", path
    )
    candidate_index_lookup_count = to_int(
        row, "context_apply_candidate_index_lookup_count", path
    )
    candidate_index_hit_count = to_int(row, "context_apply_candidate_index_hit_count", path)
    candidate_index_miss_count = to_int(row, "context_apply_candidate_index_miss_count", path)
    candidate_index_erase_count = to_int(row, "context_apply_candidate_index_erase_count", path)
    candidate_index_insert_count = to_int(
        row, "context_apply_candidate_index_insert_count", path
    )

    refresh_share = share(refresh_min_mean_seconds, context_apply_mean_seconds)
    candidate_share = share(candidate_index_mean_seconds, context_apply_mean_seconds)
    erase_share_of_candidate = share(
        candidate_index_erase_mean_seconds, candidate_index_mean_seconds
    )
    insert_share_of_candidate = share(
        candidate_index_insert_mean_seconds, candidate_index_mean_seconds
    )
    sim_initial_scan_seconds = resolve_optional_float(
        row, ("sim_initial_scan_seconds_mean_seconds",)
    )
    sim_initial_scan_cpu_merge_seconds = resolve_optional_float(
        row,
        (
            "sim_initial_scan_cpu_merge_seconds_mean_seconds",
            "sim_initial_scan_cpu_merge_seconds_seconds",
        ),
    )
    sim_initial_scan_cpu_merge_subtotal_seconds = resolve_optional_float(
        row, ("sim_initial_scan_cpu_merge_subtotal_seconds_mean_seconds",)
    )
    sim_seconds = resolve_total_sim_seconds(row)
    total_seconds = resolve_optional_float(
        row, ("total_seconds_mean_seconds", "total_seconds_seconds")
    )
    workload_id = resolve_optional_text(row, "workload_id")
    benchmark_source = resolve_optional_text(row, "benchmark_source")

    validate_positive_optional(
        sim_initial_scan_seconds, path, case_id, "sim_initial_scan_seconds_mean_seconds"
    )
    validate_positive_optional(
        sim_initial_scan_cpu_merge_seconds,
        path,
        case_id,
        "sim_initial_scan_cpu_merge_seconds_mean_seconds",
    )
    validate_positive_optional(
        sim_initial_scan_cpu_merge_subtotal_seconds,
        path,
        case_id,
        "sim_initial_scan_cpu_merge_subtotal_seconds_mean_seconds",
    )
    validate_positive_optional(sim_seconds, path, case_id, "sim_seconds_mean_seconds")
    validate_positive_optional(total_seconds, path, case_id, "total_seconds_mean_seconds")

    case_materiality_known = (
        bool(workload_id)
        and bool(benchmark_source)
        and all(
            value is not None
            for value in (
                sim_initial_scan_seconds,
                sim_initial_scan_cpu_merge_seconds,
                sim_initial_scan_cpu_merge_subtotal_seconds,
                sim_seconds,
                total_seconds,
            )
        )
    )
    initial_cpu_merge_share_of_sim = (
        share(sim_initial_scan_cpu_merge_seconds, sim_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and sim_seconds is not None
        else None
    )
    initial_cpu_merge_share_of_total = (
        share(sim_initial_scan_cpu_merge_seconds, total_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and total_seconds is not None
        else None
    )
    candidate_index_share_of_sim = (
        candidate_share * initial_cpu_merge_share_of_sim
        if initial_cpu_merge_share_of_sim is not None
        else None
    )
    candidate_index_share_of_total = (
        candidate_share * initial_cpu_merge_share_of_total
        if initial_cpu_merge_share_of_total is not None
        else None
    )
    next_action = recommended_next_action(
        refresh_share,
        candidate_share,
        erase_share_of_candidate,
        initial_cpu_merge_share_of_sim,
        args,
    )

    return {
        "case_id": case_id,
        "aggregate_tsv": str(path),
        "workload_id": workload_id,
        "benchmark_source": benchmark_source,
        "context_apply_mean_seconds": context_apply_mean_seconds,
        "sim_initial_scan_mean_seconds": sim_initial_scan_seconds,
        "sim_initial_scan_cpu_merge_mean_seconds": sim_initial_scan_cpu_merge_seconds,
        "sim_initial_scan_cpu_merge_subtotal_mean_seconds": sim_initial_scan_cpu_merge_subtotal_seconds,
        "sim_seconds_mean_seconds": sim_seconds,
        "total_seconds_mean_seconds": total_seconds,
        "full_set_miss_count": full_set_miss_count,
        "full_set_miss_mean_seconds": full_set_miss_mean_seconds,
        "floor_changed_count": floor_changed_count,
        "floor_changed_share": floor_changed_share,
        "running_min_slot_changed_count": running_min_slot_changed_count,
        "running_min_slot_changed_share": running_min_slot_changed_share,
        "victim_was_running_min_count": victim_was_running_min_count,
        "victim_was_running_min_share": victim_was_running_min_share,
        "refresh_min_calls": refresh_min_calls,
        "refresh_min_slots_scanned": refresh_min_slots_scanned,
        "refresh_min_slots_scanned_per_call": refresh_min_slots_scanned_per_call,
        "refresh_min_mean_seconds": refresh_min_mean_seconds,
        "refresh_min_seconds_per_full_set_miss": share(
            refresh_min_mean_seconds, full_set_miss_count
        ),
        "refresh_min_calls_per_full_set_miss": share(refresh_min_calls, full_set_miss_count),
        "refresh_min_slots_scanned_per_full_set_miss": share(
            refresh_min_slots_scanned, full_set_miss_count
        ),
        "candidate_index_lookup_count": candidate_index_lookup_count,
        "candidate_index_hit_count": candidate_index_hit_count,
        "candidate_index_miss_count": candidate_index_miss_count,
        "candidate_index_erase_count": candidate_index_erase_count,
        "candidate_index_insert_count": candidate_index_insert_count,
        "candidate_index_mean_seconds": candidate_index_mean_seconds,
        "candidate_index_erase_mean_seconds": candidate_index_erase_mean_seconds,
        "candidate_index_insert_mean_seconds": candidate_index_insert_mean_seconds,
        "candidate_index_seconds_per_full_set_miss": share(
            candidate_index_mean_seconds, full_set_miss_count
        ),
        "candidate_index_lookups_per_full_set_miss": share(
            candidate_index_lookup_count, full_set_miss_count
        ),
        "candidate_index_erases_per_full_set_miss": share(
            candidate_index_erase_count, full_set_miss_count
        ),
        "candidate_index_inserts_per_full_set_miss": share(
            candidate_index_insert_count, full_set_miss_count
        ),
        "refresh_min_share_of_initial_cpu_merge": refresh_share,
        "candidate_index_share_of_initial_cpu_merge": candidate_share,
        "candidate_index_erase_share_of_candidate_index": erase_share_of_candidate,
        "candidate_index_insert_share_of_candidate_index": insert_share_of_candidate,
        "total_sim_mean_seconds": sim_seconds,
        "initial_cpu_merge_share_of_sim_seconds": initial_cpu_merge_share_of_sim,
        "initial_cpu_merge_share_of_total_seconds": initial_cpu_merge_share_of_total,
        "candidate_index_share_of_sim_seconds": candidate_index_share_of_sim,
        "candidate_index_share_of_total_seconds": candidate_index_share_of_total,
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


def aggregate_summary(rows):
    case_count = len(rows)
    initial_cpu_merge_seconds = sum(row["context_apply_mean_seconds"] for row in rows)
    refresh_min_seconds = sum(row["refresh_min_mean_seconds"] for row in rows)
    candidate_index_seconds = sum(row["candidate_index_mean_seconds"] for row in rows)
    candidate_index_erase_seconds = sum(
        row["candidate_index_erase_mean_seconds"] for row in rows
    )
    candidate_index_insert_seconds = sum(
        row["candidate_index_insert_mean_seconds"] for row in rows
    )
    pairing = evaluate_materiality_pairing(rows)
    pairing_groups = pairing["groups"]
    if pairing["status"] in {"complete", "duplicate_grouped"}:
        sim_initial_scan_seconds = grouped_metric_from_pairing(
            pairing_groups, "sim_initial_scan_mean_seconds"
        )
        sim_initial_scan_cpu_merge_seconds = grouped_metric_from_pairing(
            pairing_groups, "sim_initial_scan_cpu_merge_mean_seconds"
        )
        sim_initial_scan_cpu_merge_subtotal_seconds = grouped_optional_metric_from_pairing(
            pairing_groups, "sim_initial_scan_cpu_merge_subtotal_mean_seconds"
        )
        total_sim_seconds = grouped_metric_from_pairing(pairing_groups, "sim_seconds_mean_seconds")
        total_seconds = grouped_metric_from_pairing(pairing_groups, "total_seconds_mean_seconds")
    else:
        sim_initial_scan_seconds = None
        sim_initial_scan_cpu_merge_seconds = None
        sim_initial_scan_cpu_merge_subtotal_seconds = None
        total_sim_seconds = None
        total_seconds = None
    all_have_total_sim = pairing["status"] in {"complete", "duplicate_grouped"}
    initial_cpu_merge_share_of_sim = (
        share(sim_initial_scan_cpu_merge_seconds, total_sim_seconds)
        if all_have_total_sim
        else None
    )
    initial_cpu_merge_share_of_total = (
        share(sim_initial_scan_cpu_merge_seconds, total_seconds)
        if sim_initial_scan_cpu_merge_seconds is not None and total_seconds is not None
        else None
    )
    refresh_share = share(refresh_min_seconds, initial_cpu_merge_seconds)
    candidate_share = share(candidate_index_seconds, initial_cpu_merge_seconds)
    candidate_index_share_of_sim = (
        candidate_share * initial_cpu_merge_share_of_sim
        if initial_cpu_merge_share_of_sim is not None
        else None
    )
    candidate_index_share_of_total = (
        candidate_share * initial_cpu_merge_share_of_total
        if initial_cpu_merge_share_of_total is not None
        else None
    )
    profiled_subtotal_share = share(
        refresh_min_seconds + candidate_index_seconds, initial_cpu_merge_seconds
    )
    unprofiled_share = max(0.0, 1.0 - profiled_subtotal_share)
    erase_share = share(candidate_index_erase_seconds, candidate_index_seconds)
    insert_share = share(candidate_index_insert_seconds, candidate_index_seconds)

    return {
        "case_count": case_count,
        "full_set_miss_count": sum(row["full_set_miss_count"] for row in rows),
        "initial_cpu_merge_seconds": initial_cpu_merge_seconds,
        "materiality_status": "known" if all_have_total_sim else "unknown",
        "materiality_pairing_status": pairing["status"],
        "sim_initial_scan_seconds": sim_initial_scan_seconds,
        "sim_initial_scan_cpu_merge_seconds": sim_initial_scan_cpu_merge_seconds,
        "sim_initial_scan_cpu_merge_subtotal_seconds": sim_initial_scan_cpu_merge_subtotal_seconds,
        "sim_seconds": total_sim_seconds,
        "total_seconds": total_seconds,
        "refresh_min": {
            "calls": sum(row["refresh_min_calls"] for row in rows),
            "seconds": refresh_min_seconds,
            "slots_scanned": sum(row["refresh_min_slots_scanned"] for row in rows),
            "slots_scanned_per_call": share(
                sum(row["refresh_min_slots_scanned"] for row in rows),
                sum(row["refresh_min_calls"] for row in rows),
            ),
            "seconds_per_call": share(
                refresh_min_seconds, sum(row["refresh_min_calls"] for row in rows)
            ),
            "seconds_per_full_set_miss": share(
                refresh_min_seconds, sum(row["full_set_miss_count"] for row in rows)
            ),
            "calls_per_full_set_miss": share(
                sum(row["refresh_min_calls"] for row in rows),
                sum(row["full_set_miss_count"] for row in rows),
            ),
            "slots_scanned_per_full_set_miss": share(
                sum(row["refresh_min_slots_scanned"] for row in rows),
                sum(row["full_set_miss_count"] for row in rows),
            ),
        },
        "candidate_index": {
            "lookup_count": sum(row["candidate_index_lookup_count"] for row in rows),
            "hit_count": sum(row["candidate_index_hit_count"] for row in rows),
            "miss_count": sum(row["candidate_index_miss_count"] for row in rows),
            "erase_count": sum(row["candidate_index_erase_count"] for row in rows),
            "insert_count": sum(row["candidate_index_insert_count"] for row in rows),
            "seconds": candidate_index_seconds,
            "erase_seconds": candidate_index_erase_seconds,
            "insert_seconds": candidate_index_insert_seconds,
            "seconds_per_full_set_miss": share(
                candidate_index_seconds, sum(row["full_set_miss_count"] for row in rows)
            ),
            "lookups_per_full_set_miss": share(
                sum(row["candidate_index_lookup_count"] for row in rows),
                sum(row["full_set_miss_count"] for row in rows),
            ),
            "erases_per_full_set_miss": share(
                sum(row["candidate_index_erase_count"] for row in rows),
                sum(row["full_set_miss_count"] for row in rows),
            ),
            "inserts_per_full_set_miss": share(
                sum(row["candidate_index_insert_count"] for row in rows),
                sum(row["full_set_miss_count"] for row in rows),
            ),
            "erase_share_of_candidate_index": erase_share,
            "insert_share_of_candidate_index": insert_share,
            "share_of_sim_seconds": candidate_index_share_of_sim,
            "share_of_total_seconds": candidate_index_share_of_total,
        },
        "cost_shares": {
            "refresh_min_share_of_initial_cpu_merge": refresh_share,
            "candidate_index_share_of_initial_cpu_merge": candidate_share,
            "profiled_subtotal_share_of_initial_cpu_merge": profiled_subtotal_share,
            "unprofiled_initial_cpu_merge_share": unprofiled_share,
            "initial_cpu_merge_share_of_sim_seconds": initial_cpu_merge_share_of_sim,
            "initial_cpu_merge_share_of_total_seconds": initial_cpu_merge_share_of_total,
        },
        "floor_changed_count": sum(row["floor_changed_count"] for row in rows),
        "floor_changed_share": share(
            sum(row["floor_changed_count"] for row in rows),
            sum(row["full_set_miss_count"] for row in rows),
        ),
        "running_min_slot_changed_count": sum(
            row["running_min_slot_changed_count"] for row in rows
        ),
        "running_min_slot_changed_share": share(
            sum(row["running_min_slot_changed_count"] for row in rows),
            sum(row["full_set_miss_count"] for row in rows),
        ),
        "victim_was_running_min_count": sum(
            row["victim_was_running_min_count"] for row in rows
        ),
        "victim_was_running_min_share": share(
            sum(row["victim_was_running_min_count"] for row in rows),
            sum(row["full_set_miss_count"] for row in rows),
        ),
    }


def write_summary_markdown(path: Path, summary):
    lines = [
        "# SIM Initial Host Merge Min Maintenance Profile Summary",
        "",
        f"- decision_status: `{summary['decision_status']}`",
        f"- materiality_status: `{summary['materiality_status']}`",
        f"- materiality_pairing_status: `{summary['materiality_pairing_status']}`",
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
        initial_cpu_merge_share_of_sim = summary["cost_shares"]["initial_cpu_merge_share_of_sim_seconds"]
        initial_cpu_merge_share_of_total = summary["cost_shares"]["initial_cpu_merge_share_of_total_seconds"]
        initial_cpu_merge_share_text = (
            f"{initial_cpu_merge_share_of_sim:.6f}"
            if initial_cpu_merge_share_of_sim is not None
            else "n/a"
        )
        initial_cpu_merge_share_of_total_text = (
            f"{initial_cpu_merge_share_of_total:.6f}"
            if initial_cpu_merge_share_of_total is not None
            else "n/a"
        )
        candidate_share_of_sim = summary["candidate_index"]["share_of_sim_seconds"]
        candidate_share_of_total = summary["candidate_index"]["share_of_total_seconds"]
        candidate_share_of_sim_text = (
            f"{candidate_share_of_sim:.6f}" if candidate_share_of_sim is not None else "n/a"
        )
        candidate_share_of_total_text = (
            f"{candidate_share_of_total:.6f}" if candidate_share_of_total is not None else "n/a"
        )
        lines.extend(
            [
                "## Aggregate",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| full_set_miss_count | {summary['full_set_miss_count']} |",
                f"| initial_cpu_merge_seconds | {summary['initial_cpu_merge_seconds']:.6f} |",
                f"| refresh_min_seconds | {summary['refresh_min']['seconds']:.6f} |",
                f"| candidate_index_seconds | {summary['candidate_index']['seconds']:.6f} |",
                f"| refresh_min_share_of_initial_cpu_merge | {summary['cost_shares']['refresh_min_share_of_initial_cpu_merge']:.6f} |",
                f"| candidate_index_share_of_initial_cpu_merge | {summary['cost_shares']['candidate_index_share_of_initial_cpu_merge']:.6f} |",
                f"| candidate_index_share_of_sim_seconds | {candidate_share_of_sim_text} |",
                f"| candidate_index_share_of_total_seconds | {candidate_share_of_total_text} |",
                f"| profiled_subtotal_share_of_initial_cpu_merge | {summary['cost_shares']['profiled_subtotal_share_of_initial_cpu_merge']:.6f} |",
                f"| unprofiled_initial_cpu_merge_share | {summary['cost_shares']['unprofiled_initial_cpu_merge_share']:.6f} |",
                f"| initial_cpu_merge_share_of_sim_seconds | {initial_cpu_merge_share_text} |",
                f"| initial_cpu_merge_share_of_total_seconds | {initial_cpu_merge_share_of_total_text} |",
                "",
                "## Cases",
                "",
                "| case_id | context_apply_mean_seconds | refresh_min_share | candidate_index_share | candidate_index_share_of_sim | materiality_status | next_action |",
                "| --- | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for row in summary["cases"]:
            candidate_share_of_sim_case = (
                f"{row['candidate_index_share_of_sim_seconds']:.6f}"
                if row["candidate_index_share_of_sim_seconds"] is not None
                else "n/a"
            )
            lines.append(
                f"| {row['case_id']} | {row['context_apply_mean_seconds']:.6f} | "
                f"{row['refresh_min_share_of_initial_cpu_merge']:.6f} | "
                f"{row['candidate_index_share_of_initial_cpu_merge']:.6f} | "
                f"{candidate_share_of_sim_case} | "
                f"{row['materiality_status']} | "
                f"{row['recommended_next_action']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        except ProfileInputError as exc:
            errors.append(str(exc))
            continue
        for raw_row in raw_rows:
            case_id = raw_row["case_id"]
            if selected_case_ids and case_id not in selected_case_ids:
                continue
            if case_id in seen_case_ids:
                errors.append(f"duplicate case_id across profile inputs: {case_id}")
                continue
            try:
                row = analyze_case(raw_row, path, args)
            except ProfileInputError as exc:
                errors.append(str(exc))
                continue
            rows.append(row)
            seen_case_ids.add(case_id)

    cases_tsv = output_dir / "min_maintenance_profile_cases.tsv"
    summary_json = output_dir / "min_maintenance_profile_summary.json"
    decision_json = output_dir / "min_maintenance_profile_decision.json"
    summary_md = output_dir / "min_maintenance_profile_summary.md"

    write_rows(cases_tsv, CASE_FIELDNAMES, [format_row(row) for row in rows])

    if errors or not rows:
        summary = {
            "decision_status": "not_ready",
            "materiality_status": "unknown",
            "materiality_pairing_status": "missing",
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": sum(row["full_set_miss_count"] for row in rows),
            "recommended_next_action": "fix_profile_inputs",
            "errors": errors if errors else ["no ready profile rows"],
            "cases": rows,
            "cases_tsv": str(cases_tsv),
            "summary_markdown": str(summary_md),
        }
        decision = {
            "decision_status": "not_ready",
            "materiality_status": "unknown",
            "materiality_pairing_status": "missing",
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": sum(row["full_set_miss_count"] for row in rows),
            "recommended_next_action": "fix_profile_inputs",
            "blocking_reasons": summary["errors"],
        }
    else:
        aggregate = aggregate_summary(rows)
        next_action = recommended_next_action(
            aggregate["cost_shares"]["refresh_min_share_of_initial_cpu_merge"],
            aggregate["cost_shares"]["candidate_index_share_of_initial_cpu_merge"],
            aggregate["candidate_index"]["erase_share_of_candidate_index"],
            aggregate["cost_shares"]["initial_cpu_merge_share_of_sim_seconds"],
            args,
        )
        decision_status = (
            "ready"
            if aggregate["materiality_status"] == "known"
            else "ready_but_materiality_unknown"
        )
        summary = {
            "decision_status": decision_status,
            "materiality_status": aggregate["materiality_status"],
            "materiality_pairing_status": aggregate["materiality_pairing_status"],
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": aggregate["full_set_miss_count"],
            "initial_cpu_merge_seconds": aggregate["initial_cpu_merge_seconds"],
            "refresh_min": aggregate["refresh_min"],
            "candidate_index": aggregate["candidate_index"],
            "cost_shares": aggregate["cost_shares"],
            "floor_changed_count": aggregate["floor_changed_count"],
            "floor_changed_share": aggregate["floor_changed_share"],
            "running_min_slot_changed_count": aggregate["running_min_slot_changed_count"],
            "running_min_slot_changed_share": aggregate["running_min_slot_changed_share"],
            "victim_was_running_min_count": aggregate["victim_was_running_min_count"],
            "victim_was_running_min_share": aggregate["victim_was_running_min_share"],
            "recommended_next_action": next_action,
            "errors": [],
            "cases": rows,
            "cases_tsv": str(cases_tsv),
            "summary_markdown": str(summary_md),
        }
        decision = {
            "decision_status": decision_status,
            "materiality_status": aggregate["materiality_status"],
            "materiality_pairing_status": aggregate["materiality_pairing_status"],
            "case_count": len(rows),
            "ready_case_count": len(rows),
            "full_set_miss_count": aggregate["full_set_miss_count"],
            "refresh_min": aggregate["refresh_min"],
            "candidate_index": aggregate["candidate_index"],
            "cost_shares": aggregate["cost_shares"],
            "recommended_next_action": next_action,
        }

    write_summary_markdown(summary_md, summary)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision_json.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
