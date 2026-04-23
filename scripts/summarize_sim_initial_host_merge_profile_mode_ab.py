#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
from pathlib import Path


BASE_REQUIRED_CASE_FIELDS = [
    "case_id",
    "aggregate_tsv",
    "workload_id",
    "benchmark_source",
    "profile_mode",
    "candidate_index_mean_seconds",
    "sim_seconds_mean_seconds",
    "total_seconds_mean_seconds",
    "terminal_path_parent_seconds",
    "terminal_first_half_parent_seconds",
    "terminal_first_half_span_a_seconds",
    "terminal_first_half_span_b_seconds",
    "terminal_first_half_unexplained_seconds",
    "timer_call_count",
    "terminal_timer_call_count",
    "lexical_timer_call_count",
    "dominant_terminal_span",
    "dominant_terminal_first_half_span",
]


class AbInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coarse-dir", required=True)
    parser.add_argument("--terminal-dir", required=True)
    parser.add_argument("--lexical-first-half-dir")
    parser.add_argument("--count-only-dir")
    parser.add_argument("--sampled-dir")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    legacy = bool(args.lexical_first_half_dir)
    low_overhead = bool(args.count_only_dir or args.sampled_dir)
    if legacy == low_overhead:
        raise SystemExit(
            "choose exactly one input style: --lexical-first-half-dir or --count-only-dir/--sampled-dir"
        )
    if low_overhead and not (args.count_only_dir and args.sampled_dir):
        raise SystemExit("--count-only-dir and --sampled-dir must be provided together")
    return args


def read_tsv_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        return reader.fieldnames or [], rows


def load_single_aggregate_row(path_text, expected_case_id):
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.is_file():
        raise AbInputError(f"missing aggregate TSV: {path}")
    fieldnames, rows = read_tsv_rows(path)
    if not rows:
        raise AbInputError(f"{path}: no rows")
    if len(rows) != 1:
        raise AbInputError(f"{path}: expected exactly one row, found {len(rows)}")
    row = rows[0]
    if row.get("case_id") != expected_case_id:
        raise AbInputError(
            f"{path}: expected case_id={expected_case_id}, got {row.get('case_id')!r}"
        )
    return row


def load_artifact_dir(path_text):
    path = Path(path_text)
    cases_path = path / "candidate_index_lifecycle_cases.tsv"
    summary_path = path / "candidate_index_lifecycle_summary.json"
    if not cases_path.is_file():
        raise AbInputError(f"missing cases TSV: {cases_path}")
    if not summary_path.is_file():
        raise AbInputError(f"missing summary JSON: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    fieldnames, rows = read_tsv_rows(cases_path)
    missing = [field for field in BASE_REQUIRED_CASE_FIELDS if field not in fieldnames]
    if missing:
        raise AbInputError(f"{cases_path}: missing required fields: {', '.join(missing)}")
    if not rows:
        raise AbInputError(f"{cases_path}: no rows")
    if summary.get("decision_status") not in {"ready", "ready_but_materiality_unknown"}:
        raise AbInputError(f"{summary_path}: unsupported decision_status {summary.get('decision_status')!r}")
    if summary.get("materiality_pairing_status") not in {"complete", "duplicate_grouped"}:
        raise AbInputError(
            f"{summary_path}: unsupported materiality_pairing_status {summary.get('materiality_pairing_status')!r}"
        )

    merged_rows = []
    workload_ids = set()
    benchmark_sources = set()
    profile_modes = set()
    for row in rows:
        aggregate_row = load_single_aggregate_row(row.get("aggregate_tsv", ""), row["case_id"])
        merged = dict(row)
        for key, value in aggregate_row.items():
            merged.setdefault(key, value)
        merged_rows.append(merged)
        workload_ids.add(row["workload_id"])
        benchmark_sources.add(row["benchmark_source"])
        profile_modes.add(row["profile_mode"])

    if len(workload_ids) != 1:
        raise AbInputError(f"{cases_path}: expected exactly one workload_id, found {sorted(workload_ids)}")
    if len(benchmark_sources) != 1:
        raise AbInputError(
            f"{cases_path}: expected exactly one benchmark_source, found {sorted(benchmark_sources)}"
        )
    if len(profile_modes) != 1:
        raise AbInputError(f"{cases_path}: expected exactly one profile_mode, found {sorted(profile_modes)}")

    return {
        "dir": str(path),
        "cases_path": str(cases_path),
        "summary_path": str(summary_path),
        "summary": summary,
        "rows": merged_rows,
        "workload_id": next(iter(workload_ids)),
        "profile_mode": next(iter(profile_modes)),
        "benchmark_source": next(iter(benchmark_sources)),
    }


def to_float(row, field, default=None):
    value = row.get(field, "")
    if str(value).strip() == "":
        return default
    value = float(value)
    if value < 0.0:
        raise AbInputError(f"negative float field {field}={value} in row {row.get('case_id')}")
    return value


def to_int(row, field, default=None):
    value = row.get(field, "")
    if str(value).strip() == "":
        return default
    value = int(float(value))
    if value < 0:
        raise AbInputError(f"negative int field {field}={value} in row {row.get('case_id')}")
    return value


def ratio(numerator, denominator):
    if denominator <= 0.0:
        raise AbInputError(f"non-positive denominator for ratio: {denominator}")
    return numerator / denominator


def optional_ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator <= 0.0:
        return None
    return numerator / denominator


def format_metric(value):
    if value is None:
        return "n/a"
    return f"{value:.6f}"


def case_map(artifact):
    return {row["case_id"]: row for row in artifact["rows"]}


def sum_case_field(rows, field, cast, default=None):
    total = 0.0
    found = False
    for row in rows:
        value = cast(row, field, default)
        if value is None:
            continue
        total += value
        found = True
    if not found:
        return None
    return total


def sum_case_field_with_fallback(rows, fields, cast, default=None):
    for field in fields:
        total = sum_case_field(rows, field, cast, None)
        if total is not None:
            return total
    return None


def row_value_with_fallback(row, fields, cast, default=None):
    for field in fields:
        value = cast(row, field, None)
        if value is not None:
            return value
    return default


def dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_child_for_row(row):
    child_0 = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_mean_seconds",
        ],
        to_float,
        None,
    )
    child_1 = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_mean_seconds",
        ],
        to_float,
        None,
    )
    if child_0 is not None or child_1 is not None:
        child_0 = child_0 or 0.0
        child_1 = child_1 or 0.0
        if child_0 > child_1:
            return "child_0"
        if child_1 > child_0:
            return "child_1"
        parent = row_value_with_fallback(
            row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_mean_seconds",
            ],
            to_float,
            None,
        )
        if (parent or 0.0) > 0.0:
            return "mixed"
        return "unknown"
    label = row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child", "")
    return label or "unknown"


def dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_for_row(row):
    repart_left = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds",
        ],
        to_float,
        None,
    )
    repart_right = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds",
        ],
        to_float,
        None,
    )
    if repart_left is not None or repart_right is not None:
        repart_left = repart_left or 0.0
        repart_right = repart_right or 0.0
        if repart_left > repart_right:
            return "repart_left"
        if repart_right > repart_left:
            return "repart_right"
        parent = row_value_with_fallback(
            row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds",
            ],
            to_float,
            None,
        )
        if (parent or 0.0) > 0.0:
            return "mixed"
        return "unknown"
    label = row.get(
        "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child",
        "",
    )
    return label or "unknown"


def consistent_text(rows, field):
    values = {row.get(field, "") for row in rows if row.get(field, "") != ""}
    if not values:
        return None
    if len(values) != 1:
        raise AbInputError(f"inconsistent {field}: {sorted(values)}")
    return next(iter(values))


def benchmark_source_identity(path_text):
    path = Path(path_text)
    if not path.is_file():
        return None
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def benchmark_identity_for_artifact(artifact):
    sha256_value = consistent_text(artifact["rows"], "benchmark_source_sha256")
    if sha256_value:
        basis = consistent_text(artifact["rows"], "benchmark_identity_basis") or "content_sha256"
        return sha256_value, basis
    file_identity = benchmark_source_identity(artifact["benchmark_source"])
    if file_identity:
        return file_identity, "content_sha256"
    return artifact["benchmark_source"], "source_path"


def benchmark_scope(artifacts):
    identities = {}
    bases = {}
    for artifact in artifacts:
        identity, basis = benchmark_identity_for_artifact(artifact)
        identities[artifact["profile_mode"]] = identity
        bases[artifact["profile_mode"]] = basis
    unique_identities = set(identities.values())
    if len(unique_identities) == 1:
        return "shared_workload", next(iter(set(bases.values())))
    if len(unique_identities) == len(identities):
        return "per_profile_mode", next(iter(set(bases.values())))
    raise AbInputError(f"unsupported benchmark identity mix across modes: {identities}")


def dominant_first_half_span_from_rows(rows):
    labels = {row.get("dominant_terminal_first_half_span", "") for row in rows if row.get("dominant_terminal_first_half_span", "")}
    if len(labels) == 1:
        return next(iter(labels))
    span_a_total = sum_case_field(rows, "terminal_first_half_span_a_seconds", to_float, 0.0) or 0.0
    span_b_total = sum_case_field(rows, "terminal_first_half_span_b_seconds", to_float, 0.0) or 0.0
    if span_a_total > span_b_total:
        return "span_a"
    if span_b_total > span_a_total:
        return "span_b"
    return "mixed"


def dominant_first_half_span_a_child_from_rows(rows):
    labels = {
        row.get("dominant_terminal_first_half_span_a_child", "")
        for row in rows
        if row.get("dominant_terminal_first_half_span_a_child", "")
    }
    if len(labels) == 1:
        return next(iter(labels))
    span_a0_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    span_a1_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a1_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    if span_a0_total > span_a1_total:
        return "span_a0"
    if span_a1_total > span_a0_total:
        return "span_a1"
    span_a_parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if span_a_parent_total is None:
        span_a_parent_total = sum_case_field(rows, "terminal_first_half_span_a_seconds", to_float, 0.0)
    if (span_a_parent_total or 0.0) > 0.0:
        return "mixed"
    return "unknown"


def dominant_first_half_span_a0_child_from_rows(rows):
    labels = {
        row.get("dominant_terminal_first_half_span_a0_child", "")
        for row in rows
        if row.get("dominant_terminal_first_half_span_a0_child", "")
    }
    if len(labels) == 1:
        return next(iter(labels))
    gap_before_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    span_a00_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a00_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    gap_between_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_between_a00_a01_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    span_a01_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a01_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    gap_after_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_after_a01_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    totals = {
        "gap_before_a00": gap_before_total,
        "span_a00": span_a00_total,
        "gap_between_a00_a01": gap_between_total,
        "span_a01": span_a01_total,
        "gap_after_a01": gap_after_total,
    }
    dominant_label, dominant_value = max(totals.items(), key=lambda item: item[1])
    if dominant_value > 0.0 and list(totals.values()).count(dominant_value) == 1:
        return dominant_label
    span_a0_parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if span_a0_parent_total is None:
        span_a0_parent_total = sum_case_field(
            rows, "terminal_first_half_span_a0_seconds", to_float, 0.0
        )
    if (span_a0_parent_total or 0.0) > 0.0:
        return "mixed"
    return "unknown"


def sampled_count_closure_status_for_row(row):
    parent_count = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_sampled_event_count",
        ],
        to_int,
        None,
    )
    covered = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    unclassified = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    multi_child = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if parent_count is None or unclassified is None:
        return "unknown"
    if parent_count <= 0:
        return "unknown"
    if covered is None:
        covered = max(parent_count - unclassified, 0)
    if multi_child is None:
        multi_child = 0
    if covered < 0 or covered > parent_count or multi_child < 0:
        return "unknown"
    if optional_ratio(unclassified, parent_count) is None:
        return "unknown"
    if optional_ratio(unclassified, parent_count) > 0.01:
        return "open"
    return "closed"


def sampled_count_closure_status_from_rows(rows):
    statuses = {sampled_count_closure_status_for_row(row) for row in rows}
    if statuses == {"closed"}:
        return "closed"
    if "open" in statuses:
        return "open"
    return "unknown"


def dominant_first_half_span_a0_gap_before_a00_child_from_rows(rows):
    labels = {
        row.get("dominant_terminal_first_half_span_a0_gap_before_a00_child", "")
        for row in rows
        if row.get("dominant_terminal_first_half_span_a0_gap_before_a00_child", "")
    }
    if len(labels) == 1:
        return next(iter(labels))
    span_0_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    span_1_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_1_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    if span_0_total > span_1_total:
        return "span_0"
    if span_1_total > span_0_total:
        return "span_1"
    parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_mean_seconds",
            "terminal_first_half_span_a0_gap_before_a00_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
        ],
        to_float,
        None,
    )
    if (parent_total or 0.0) > 0.0:
        return "mixed"
    return "unknown"


def gap_before_a00_sampled_count_closure_status_for_row(row):
    parent_count = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_sampled_event_count",
        ],
        to_int,
        None,
    )
    covered = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    unclassified = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    multi_child = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if parent_count is None or unclassified is None:
        return "unknown"
    if parent_count <= 0:
        return "unknown"
    if covered is None:
        covered = max(parent_count - unclassified, 0)
    if multi_child is None:
        multi_child = 0
    if covered < 0 or covered > parent_count or multi_child < 0:
        return "unknown"
    if optional_ratio(unclassified, parent_count) is None:
        return "unknown"
    if optional_ratio(unclassified, parent_count) > 0.01:
        return "open"
    return "closed"


def gap_before_a00_sampled_count_closure_status_from_rows(rows):
    statuses = {gap_before_a00_sampled_count_closure_status_for_row(row) for row in rows}
    if statuses == {"closed"}:
        return "closed"
    if "open" in statuses:
        return "open"
    return "unknown"


def dominant_first_half_span_a0_gap_before_a00_span_0_child_from_rows(rows):
    labels = {
        row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child", "")
        for row in rows
        if row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child", "")
    }
    if len(labels) == 1:
        return next(iter(labels))
    child_0_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    child_1_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    if child_0_total > child_1_total:
        return "child_0"
    if child_1_total > child_0_total:
        return "child_1"
    parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_mean_seconds",
            "terminal_first_half_span_a0_gap_before_a00_span_0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds",
        ],
        to_float,
        None,
    )
    if (parent_total or 0.0) > 0.0:
        return "mixed"
    return "unknown"


def gap_before_a00_span_0_sampled_count_closure_status_for_row(row):
    parent_count = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
        ],
        to_int,
        None,
    )
    covered = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    unclassified = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    multi_child = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if parent_count is None or unclassified is None:
        return "unknown"
    if parent_count <= 0:
        return "unknown"
    if covered is None:
        covered = max(parent_count - unclassified, 0)
    if multi_child is None:
        multi_child = 0
    if covered < 0 or covered > parent_count or multi_child < 0:
        return "unknown"
    if optional_ratio(unclassified, parent_count) is None:
        return "unknown"
    if optional_ratio(unclassified, parent_count) > 0.01:
        return "open"
    return "closed"


def gap_before_a00_span_0_sampled_count_closure_status_from_rows(rows):
    statuses = {
        gap_before_a00_span_0_sampled_count_closure_status_for_row(row) for row in rows
    }
    if statuses == {"closed"}:
        return "closed"
    if "open" in statuses:
        return "open"
    return "unknown"


def gap_before_a00_span_0_case_weighted_dominance(rows):
    child_0_count = 0
    child_1_count = 0
    total_cases = len(rows)
    child_0_event_weight = 0
    child_1_event_weight = 0
    for row in rows:
        label = row.get(
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child", ""
        )
        event_weight = row_value_with_fallback(
            row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
            ],
            to_int,
            0,
        ) or 0
        if label == "child_0":
            child_0_count += 1
            child_0_event_weight += event_weight
        elif label == "child_1":
            child_1_count += 1
            child_1_event_weight += event_weight
    if child_0_count > child_1_count:
        dominant = "child_0"
        dominant_count = child_0_count
    elif child_1_count > child_0_count:
        dominant = "child_1"
        dominant_count = child_1_count
    elif child_0_count == child_1_count and child_0_count > 0:
        dominant = "mixed"
        dominant_count = child_0_count
    else:
        dominant = "unknown"
        dominant_count = 0
    share = optional_ratio(dominant_count, total_cases) or 0.0
    if child_0_event_weight > child_1_event_weight:
        event_weighted_dominant = "child_0"
    elif child_1_event_weight > child_0_event_weight:
        event_weighted_dominant = "child_1"
    elif child_0_event_weight == child_1_event_weight and child_0_event_weight > 0:
        event_weighted_dominant = "mixed"
    else:
        event_weighted_dominant = "unknown"
    return {
        "child_0_count": child_0_count,
        "child_1_count": child_1_count,
        "case_weighted_dominant_child": dominant,
        "case_majority_share": share,
        "child_0_event_weight": child_0_event_weight,
        "child_1_event_weight": child_1_event_weight,
        "event_weighted_dominant_child": event_weighted_dominant,
    }


def dominant_first_half_span_a0_gap_before_a00_span_0_alt_child_from_rows(rows):
    labels = {
        row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child", "")
        for row in rows
        if row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child", "")
    }
    if len(labels) == 1:
        return next(iter(labels))
    alt_left_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    alt_right_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    if alt_left_total > alt_right_total:
        return "alt_left"
    if alt_right_total > alt_left_total:
        return "alt_right"
    parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if (parent_total or 0.0) > 0.0:
        return "mixed"
    return "unknown"


def gap_before_a00_span_0_alt_sampled_count_closure_status_for_row(row):
    parent_count = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
        ],
        to_int,
        None,
    )
    covered = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    unclassified = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    multi_child = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if parent_count is None or unclassified is None:
        return "unknown"
    if parent_count <= 0:
        return "unknown"
    if covered is None:
        covered = max(parent_count - unclassified, 0)
    if multi_child is None:
        multi_child = 0
    if covered < 0 or covered > parent_count or multi_child < 0:
        return "unknown"
    if optional_ratio(unclassified, parent_count) is None:
        return "unknown"
    if optional_ratio(unclassified, parent_count) > 0.01:
        return "open"
    return "closed"


def gap_before_a00_span_0_alt_sampled_count_closure_status_from_rows(rows):
    statuses = {
        gap_before_a00_span_0_alt_sampled_count_closure_status_for_row(row)
        for row in rows
    }
    if statuses == {"closed"}:
        return "closed"
    if "open" in statuses:
        return "open"
    return "unknown"


def gap_before_a00_span_0_alt_case_weighted_dominance(rows):
    alt_left_count = 0
    alt_right_count = 0
    total_cases = len(rows)
    alt_left_event_weight = 0
    alt_right_event_weight = 0
    for row in rows:
        label = row.get(
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child", ""
        )
        event_weight = row_value_with_fallback(
            row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
            ],
            to_int,
            0,
        ) or 0
        if label == "alt_left":
            alt_left_count += 1
            alt_left_event_weight += event_weight
        elif label == "alt_right":
            alt_right_count += 1
            alt_right_event_weight += event_weight
    if alt_left_count > alt_right_count:
        dominant = "alt_left"
        dominant_count = alt_left_count
    elif alt_right_count > alt_left_count:
        dominant = "alt_right"
        dominant_count = alt_right_count
    elif alt_left_count == alt_right_count and alt_left_count > 0:
        dominant = "mixed"
        dominant_count = alt_left_count
    else:
        dominant = "unknown"
        dominant_count = 0
    share = optional_ratio(dominant_count, total_cases) or 0.0
    if alt_left_event_weight > alt_right_event_weight:
        event_weighted_dominant = "alt_left"
    elif alt_right_event_weight > alt_left_event_weight:
        event_weighted_dominant = "alt_right"
    elif alt_left_event_weight == alt_right_event_weight and alt_left_event_weight > 0:
        event_weighted_dominant = "mixed"
    else:
        event_weighted_dominant = "unknown"
    return {
        "alt_left_count": alt_left_count,
        "alt_right_count": alt_right_count,
        "case_weighted_dominant_child": dominant,
        "case_majority_share": share,
        "alt_left_event_weight": alt_left_event_weight,
        "alt_right_event_weight": alt_right_event_weight,
        "event_weighted_dominant_child": event_weighted_dominant,
    }


def dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_child_from_rows(rows):
    child_0_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    child_1_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    if child_0_total > child_1_total:
        return "child_0"
    if child_1_total > child_0_total:
        return "child_1"
    parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if (parent_total or 0.0) > 0.0:
        return "mixed"
    labels = {
        row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child", "")
        for row in rows
        if row.get("dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child", "")
    }
    if len(labels) == 1:
        return next(iter(labels))
    return "unknown"


def gap_before_a00_span_0_alt_right_sampled_count_closure_status_for_row(row):
    parent_count = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
        ],
        to_int,
        None,
    )
    covered = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    unclassified = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    multi_child = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if parent_count is None or unclassified is None:
        return "unknown"
    if parent_count <= 0:
        return "unknown"
    if covered is None:
        covered = max(parent_count - unclassified, 0)
    if multi_child is None:
        multi_child = 0
    if covered < 0 or covered > parent_count or multi_child < 0:
        return "unknown"
    if optional_ratio(unclassified, parent_count) is None:
        return "unknown"
    if optional_ratio(unclassified, parent_count) > 0.01:
        return "open"
    return "closed"


def gap_before_a00_span_0_alt_right_sampled_count_closure_status_from_rows(rows):
    statuses = {
        gap_before_a00_span_0_alt_right_sampled_count_closure_status_for_row(row)
        for row in rows
    }
    if statuses == {"closed"}:
        return "closed"
    if "open" in statuses:
        return "open"
    return "unknown"


def dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_from_rows(rows):
    repart_left_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    repart_right_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds",
        ],
        to_float,
        0.0,
    ) or 0.0
    if repart_left_total > repart_right_total:
        return "repart_left"
    if repart_right_total > repart_left_total:
        return "repart_right"
    parent_total = sum_case_field_with_fallback(
        rows,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if (parent_total or 0.0) > 0.0:
        return "mixed"
    labels = {
        row.get(
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child",
            "",
        )
        for row in rows
        if row.get(
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child",
            "",
        )
    }
    if len(labels) == 1:
        return next(iter(labels))
    return "unknown"


def gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status_for_row(row):
    parent_count = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
        ],
        to_int,
        None,
    )
    covered = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    unclassified = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    multi_child = row_value_with_fallback(
        row,
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if parent_count is None or unclassified is None:
        return "unknown"
    if parent_count <= 0:
        return "unknown"
    if covered is None:
        covered = max(parent_count - unclassified, 0)
    if multi_child is None:
        multi_child = 0
    if covered < 0 or covered > parent_count or multi_child < 0:
        return "unknown"
    if optional_ratio(unclassified, parent_count) is None:
        return "unknown"
    if optional_ratio(unclassified, parent_count) > 0.01:
        return "open"
    return "closed"


def gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status_from_rows(rows):
    statuses = {
        gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status_for_row(row)
        for row in rows
    }
    if statuses == {"closed"}:
        return "closed"
    if "open" in statuses:
        return "open"
    return "unknown"


def gap_before_a00_span_0_alt_right_case_weighted_dominance(rows):
    child_0_count = 0
    child_1_count = 0
    total_cases = len(rows)
    child_0_event_weight = 0
    child_1_event_weight = 0
    for row in rows:
        label = dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_child_for_row(row)
        event_weight = row_value_with_fallback(
            row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
            ],
            to_int,
            0,
        ) or 0
        if label == "child_0":
            child_0_count += 1
            child_0_event_weight += event_weight
        elif label == "child_1":
            child_1_count += 1
            child_1_event_weight += event_weight
    if child_0_count > child_1_count:
        dominant = "child_0"
        dominant_count = child_0_count
    elif child_1_count > child_0_count:
        dominant = "child_1"
        dominant_count = child_1_count
    elif child_0_count == child_1_count and child_0_count > 0:
        dominant = "mixed"
        dominant_count = child_0_count
    else:
        dominant = "unknown"
        dominant_count = 0
    share = optional_ratio(dominant_count, total_cases) or 0.0
    if child_0_event_weight > child_1_event_weight:
        event_weighted_dominant = "child_0"
    elif child_1_event_weight > child_0_event_weight:
        event_weighted_dominant = "child_1"
    elif child_0_event_weight == child_1_event_weight and child_0_event_weight > 0:
        event_weighted_dominant = "mixed"
    else:
        event_weighted_dominant = "unknown"
    return {
        "child_0_count": child_0_count,
        "child_1_count": child_1_count,
        "case_weighted_dominant_child": dominant,
        "case_majority_share": share,
        "child_0_event_weight": child_0_event_weight,
        "child_1_event_weight": child_1_event_weight,
        "event_weighted_dominant_child": event_weighted_dominant,
    }


def gap_before_a00_span_0_alt_right_repart_case_weighted_dominance(rows):
    repart_left_count = 0
    repart_right_count = 0
    total_cases = len(rows)
    repart_left_event_weight = 0
    repart_right_event_weight = 0
    for row in rows:
        label = dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_for_row(
            row
        )
        event_weight = row_value_with_fallback(
            row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
            ],
            to_int,
            0,
        ) or 0
        if label == "repart_left":
            repart_left_count += 1
            repart_left_event_weight += event_weight
        elif label == "repart_right":
            repart_right_count += 1
            repart_right_event_weight += event_weight
    if repart_left_count > repart_right_count:
        dominant = "repart_left"
        dominant_count = repart_left_count
    elif repart_right_count > repart_left_count:
        dominant = "repart_right"
        dominant_count = repart_right_count
    elif repart_left_count == repart_right_count and repart_left_count > 0:
        dominant = "mixed"
        dominant_count = repart_left_count
    else:
        dominant = "unknown"
        dominant_count = 0
    share = optional_ratio(dominant_count, total_cases) or 0.0
    if repart_left_event_weight > repart_right_event_weight:
        event_weighted_dominant = "repart_left"
    elif repart_right_event_weight > repart_left_event_weight:
        event_weighted_dominant = "repart_right"
    elif repart_left_event_weight == repart_right_event_weight and repart_left_event_weight > 0:
        event_weighted_dominant = "mixed"
    else:
        event_weighted_dominant = "unknown"
    return {
        "repart_left_count": repart_left_count,
        "repart_right_count": repart_right_count,
        "case_weighted_dominant_child": dominant,
        "case_majority_share": share,
        "repart_left_event_weight": repart_left_event_weight,
        "repart_right_event_weight": repart_right_event_weight,
        "event_weighted_dominant_child": event_weighted_dominant,
    }


def write_rows(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary_markdown(path, summary):
    lines = [
        "# SIM Initial Host Merge Profile Mode AB Summary",
        "",
        f"- decision_status: `{summary['decision_status']}`",
        f"- analysis_mode: `{summary.get('analysis_mode', 'unknown')}`",
        f"- benchmark_scope: `{summary.get('benchmark_scope', 'unknown')}`",
        f"- benchmark_identity_basis: `{summary.get('benchmark_identity_basis', 'unknown')}`",
        f"- candidate_index_materiality_status: `{summary.get('candidate_index_materiality_status', 'unknown')}`",
        f"- materiality_status_all_modes_match: `{str(summary.get('materiality_status_all_modes_match', False)).lower()}`",
        f"- profile_mode_overhead_status: `{summary['profile_mode_overhead_status']}`",
        f"- sampled_count_closure_status: `{summary.get('sampled_count_closure_status', 'unknown')}`",
        f"- gap_before_a00_sampled_count_closure_status: `{summary.get('gap_before_a00_sampled_count_closure_status', 'unknown')}`",
        f"- gap_before_a00_span_0_sampled_count_closure_status: `{summary.get('gap_before_a00_span_0_sampled_count_closure_status', 'unknown')}`",
        f"- gap_before_a00_span_0_dominance_status: `{summary.get('gap_before_a00_span_0_dominance_status', 'unknown')}`",
        f"- gap_before_a00_span_0_case_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_case_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_seconds_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_seconds_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_event_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_event_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_sampled_count_closure_status: `{summary.get('gap_before_a00_span_0_alt_sampled_count_closure_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_dominance_status: `{summary.get('gap_before_a00_span_0_alt_dominance_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_case_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_case_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_seconds_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_seconds_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_event_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_event_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_sampled_count_closure_status: `{summary.get('gap_before_a00_span_0_alt_right_sampled_count_closure_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_dominance_status: `{summary.get('gap_before_a00_span_0_alt_right_dominance_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_case_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_right_case_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_event_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_right_event_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_repartition_attempt_count: `{summary.get('gap_before_a00_span_0_alt_right_repartition_attempt_count', 0)}`",
        f"- gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count: `{summary.get('gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count', 0)}`",
        f"- gap_before_a00_span_0_alt_right_subtree_status: `{summary.get('gap_before_a00_span_0_alt_right_subtree_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status: `{summary.get('gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_repart_dominance_status: `{summary.get('gap_before_a00_span_0_alt_right_repart_dominance_status', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child', 'unknown')}`",
        f"- gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child: `{summary.get('gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child', 'unknown')}`",
        f"- trusted_span_timing: `{str(summary.get('trusted_span_timing', False)).lower()}`",
        f"- trusted_span_source: `{summary.get('trusted_span_source', 'none')}`",
        f"- runtime_prototype_allowed: `{str(summary.get('runtime_prototype_allowed', False)).lower()}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        f"- workload_id: `{summary.get('workload_id', 'unknown')}`",
        f"- case_count: `{summary.get('case_count', 0)}`",
        "",
        "## Ratios",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for field in [
        "candidate_index_seconds_ratio_terminal_vs_coarse",
        "candidate_index_seconds_ratio_lexical_vs_coarse",
        "terminal_parent_seconds_ratio_lexical_vs_terminal",
        "candidate_index_seconds_ratio_count_only_vs_coarse",
        "candidate_index_seconds_ratio_sampled_vs_terminal",
        "candidate_index_seconds_ratio_sampled_vs_coarse",
        "terminal_parent_seconds_ratio_sampled_vs_terminal",
        "timer_call_count_ratio_count_only_vs_coarse",
        "timer_call_count_ratio_sampled_vs_terminal",
        "terminal_first_half_unexplained_share",
        "terminal_first_half_span_a_unexplained_share",
        "terminal_first_half_span_a0_unexplained_share",
        "profile_sample_rate",
        "span_a0_coverage_share",
        "span_a0_unclassified_share",
        "span_a0_multi_child_share",
        "terminal_first_half_span_a0_gap_before_a00_parent_seconds",
        "terminal_first_half_span_a0_gap_before_a00_unexplained_share",
        "terminal_first_half_span_a0_gap_before_a00_span_0_share",
        "terminal_first_half_span_a0_gap_before_a00_span_1_share",
        "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_share",
        "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_share",
        "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_share",
        "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_share",
        "gap_before_a00_span_0_case_majority_share",
        "gap_before_a00_span_0_child_margin_share",
        "gap_before_a00_span_0_alt_left_share",
        "gap_before_a00_span_0_alt_right_share",
        "gap_before_a00_span_0_alt_case_majority_share",
        "gap_before_a00_span_0_alt_child_margin_share",
        "gap_before_a00_span_0_alt_right_case_majority_share",
        "gap_before_a00_span_0_alt_right_child_margin_share",
        "gap_before_a00_span_0_alt_right_repart_left_share",
        "gap_before_a00_span_0_alt_right_repart_right_share",
        "gap_before_a00_span_0_alt_right_repart_case_majority_share",
        "gap_before_a00_span_0_alt_right_repart_child_margin_share",
        "gap_before_a00_span_0_alt_right_repart_unexplained_share",
        "gap_before_a00_coverage_share",
        "gap_before_a00_unclassified_share",
        "gap_before_a00_multi_child_share",
        "gap_before_a00_span_0_coverage_share",
        "gap_before_a00_span_0_unclassified_share",
        "gap_before_a00_span_0_multi_child_share",
        "gap_before_a00_span_0_alt_coverage_share",
        "gap_before_a00_span_0_alt_unclassified_share",
        "gap_before_a00_span_0_alt_multi_child_share",
        "gap_before_a00_span_0_alt_right_coverage_share",
        "gap_before_a00_span_0_alt_right_unclassified_share",
        "gap_before_a00_span_0_alt_right_multi_child_share",
        "gap_before_a00_span_0_alt_right_repart_coverage_share",
        "gap_before_a00_span_0_alt_right_repart_unclassified_share",
        "gap_before_a00_span_0_alt_right_repart_multi_child_share",
    ]:
        if field in summary:
            lines.append(f"| {field} | {format_metric(summary.get(field))} |")
    lines.append("")
    if summary.get("cases"):
        headers = list(summary["cases"][0].keys())
        lines.extend(
            [
                "## Cases",
                "",
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join("---" for _ in headers) + " |",
            ]
        )
        for row in summary["cases"]:
            values = []
            for header in headers:
                value = row.get(header)
                if isinstance(value, float):
                    values.append(format_metric(value))
                else:
                    values.append(str(value))
            lines.append("| " + " | ".join(values) + " |")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_artifact_set(args):
    coarse = load_artifact_dir(args.coarse_dir)
    terminal = load_artifact_dir(args.terminal_dir)
    if coarse["profile_mode"] != "coarse":
        raise AbInputError(f"expected coarse profile_mode, got {coarse['profile_mode']!r}")
    if terminal["profile_mode"] != "terminal":
        raise AbInputError(f"expected terminal profile_mode, got {terminal['profile_mode']!r}")
    if args.lexical_first_half_dir:
        lexical = load_artifact_dir(args.lexical_first_half_dir)
        if lexical["profile_mode"] != "lexical_first_half":
            raise AbInputError(
                f"expected lexical_first_half profile_mode, got {lexical['profile_mode']!r}"
            )
        return {"mode": "legacy_lexical", "coarse": coarse, "terminal": terminal, "lexical": lexical}
    count_only = load_artifact_dir(args.count_only_dir)
    sampled = load_artifact_dir(args.sampled_dir)
    if count_only["profile_mode"] != "lexical_first_half_count_only":
        raise AbInputError(
            f"expected lexical_first_half_count_only profile_mode, got {count_only['profile_mode']!r}"
        )
    if sampled["profile_mode"] != "lexical_first_half_sampled":
        raise AbInputError(
            f"expected lexical_first_half_sampled profile_mode, got {sampled['profile_mode']!r}"
        )
    return {
        "mode": "low_overhead",
        "coarse": coarse,
        "terminal": terminal,
        "count_only": count_only,
        "sampled": sampled,
    }


def verify_common_inputs(artifacts):
    workload_ids = {artifact["workload_id"] for artifact in artifacts}
    if len(workload_ids) != 1:
        raise AbInputError(f"workload_id mismatch across modes: {sorted(workload_ids)}")
    case_ids = None
    for artifact in artifacts:
        artifact_case_ids = set(case_map(artifact).keys())
        if case_ids is None:
            case_ids = artifact_case_ids
        elif artifact_case_ids != case_ids:
            raise AbInputError("case_id mismatch across profile modes")
    return next(iter(workload_ids)), sorted(case_ids or [])


def mirrored_materiality_status(artifacts):
    statuses = {}
    for artifact in artifacts:
        status = artifact["summary"].get("candidate_index_materiality_status")
        if not status:
            raise AbInputError(
                f"{artifact['summary_path']}: missing candidate_index_materiality_status"
            )
        statuses[artifact["profile_mode"]] = status
    if len(set(statuses.values())) != 1:
        raise AbInputError(
            "candidate_index_materiality_status mismatch across modes: "
            + ", ".join(f"{mode}={status}" for mode, status in sorted(statuses.items()))
        )
    return next(iter(set(statuses.values()))), True


def build_legacy_summary(loaded):
    coarse = loaded["coarse"]
    terminal = loaded["terminal"]
    lexical = loaded["lexical"]
    workload_id, case_ids = verify_common_inputs([coarse, terminal, lexical])
    scope, basis = benchmark_scope([coarse, terminal, lexical])
    materiality_status, materiality_status_all_modes_match = mirrored_materiality_status(
        [coarse, terminal, lexical]
    )

    coarse_cases = case_map(coarse)
    terminal_cases = case_map(terminal)
    lexical_cases = case_map(lexical)
    case_rows = []
    for case_id in case_ids:
        coarse_row = coarse_cases[case_id]
        terminal_row = terminal_cases[case_id]
        lexical_row = lexical_cases[case_id]
        first_half_parent = to_float(lexical_row, "terminal_first_half_parent_seconds", 0.0)
        first_half_unexplained = to_float(lexical_row, "terminal_first_half_unexplained_seconds", 0.0)
        case_rows.append(
            {
                "case_id": case_id,
                "workload_id": workload_id,
                "candidate_index_seconds_ratio_terminal_vs_coarse": ratio(
                    to_float(terminal_row, "candidate_index_mean_seconds", 0.0),
                    to_float(coarse_row, "candidate_index_mean_seconds", 0.0),
                ),
                "candidate_index_seconds_ratio_lexical_vs_coarse": ratio(
                    to_float(lexical_row, "candidate_index_mean_seconds", 0.0),
                    to_float(coarse_row, "candidate_index_mean_seconds", 0.0),
                ),
                "terminal_parent_seconds_ratio_terminal_vs_coarse": ratio(
                    to_float(terminal_row, "terminal_path_parent_seconds", 0.0),
                    to_float(coarse_row, "terminal_path_parent_seconds", 0.0),
                ),
                "terminal_parent_seconds_ratio_lexical_vs_coarse": ratio(
                    to_float(lexical_row, "terminal_path_parent_seconds", 0.0),
                    to_float(coarse_row, "terminal_path_parent_seconds", 0.0),
                ),
                "terminal_parent_seconds_ratio_lexical_vs_terminal": ratio(
                    to_float(lexical_row, "terminal_path_parent_seconds", 0.0),
                    to_float(terminal_row, "terminal_path_parent_seconds", 0.0),
                ),
                "terminal_first_half_parent_seconds_ratio_lexical_vs_terminal": optional_ratio(
                    first_half_parent,
                    to_float(terminal_row, "terminal_first_half_parent_seconds", 0.0),
                ),
                "sim_seconds_ratio_lexical_vs_coarse": ratio(
                    to_float(lexical_row, "sim_seconds_mean_seconds", 0.0),
                    to_float(coarse_row, "sim_seconds_mean_seconds", 0.0),
                ),
                "total_seconds_ratio_lexical_vs_coarse": ratio(
                    to_float(lexical_row, "total_seconds_mean_seconds", 0.0),
                    to_float(coarse_row, "total_seconds_mean_seconds", 0.0),
                ),
                "timer_call_count_ratio_lexical_vs_coarse": ratio(
                    float(to_int(lexical_row, "timer_call_count", 0)),
                    max(float(to_int(coarse_row, "timer_call_count", 0)), 1.0),
                ),
                "terminal_first_half_unexplained_share": optional_ratio(
                    first_half_unexplained, first_half_parent
                )
                or 0.0,
                "dominant_terminal_span": lexical_row["dominant_terminal_span"],
                "dominant_terminal_first_half_span": lexical_row["dominant_terminal_first_half_span"],
            }
        )

    candidate_index_seconds_ratio_terminal_vs_coarse = ratio(
        sum_case_field(terminal["rows"], "candidate_index_mean_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "candidate_index_mean_seconds", to_float, 0.0),
    )
    candidate_index_seconds_ratio_lexical_vs_coarse = ratio(
        sum_case_field(lexical["rows"], "candidate_index_mean_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "candidate_index_mean_seconds", to_float, 0.0),
    )
    terminal_parent_seconds_ratio_terminal_vs_coarse = ratio(
        sum_case_field(terminal["rows"], "terminal_path_parent_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "terminal_path_parent_seconds", to_float, 0.0),
    )
    terminal_parent_seconds_ratio_lexical_vs_coarse = ratio(
        sum_case_field(lexical["rows"], "terminal_path_parent_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "terminal_path_parent_seconds", to_float, 0.0),
    )
    terminal_parent_seconds_ratio_lexical_vs_terminal = ratio(
        sum_case_field(lexical["rows"], "terminal_path_parent_seconds", to_float, 0.0),
        sum_case_field(terminal["rows"], "terminal_path_parent_seconds", to_float, 0.0),
    )
    terminal_first_half_parent_seconds_ratio_lexical_vs_terminal = optional_ratio(
        sum_case_field(lexical["rows"], "terminal_first_half_parent_seconds", to_float, 0.0) or 0.0,
        sum_case_field(terminal["rows"], "terminal_first_half_parent_seconds", to_float, 0.0),
    )
    sim_seconds_ratio_lexical_vs_coarse = ratio(
        sum_case_field(lexical["rows"], "sim_seconds_mean_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "sim_seconds_mean_seconds", to_float, 0.0),
    )
    total_seconds_ratio_lexical_vs_coarse = ratio(
        sum_case_field(lexical["rows"], "total_seconds_mean_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "total_seconds_mean_seconds", to_float, 0.0),
    )
    timer_call_count_ratio_lexical_vs_coarse = ratio(
        sum_case_field(lexical["rows"], "timer_call_count", to_int, 0) or 0.0,
        max(sum_case_field(coarse["rows"], "timer_call_count", to_int, 0) or 0.0, 1.0),
    )
    terminal_first_half_unexplained_share = optional_ratio(
        sum_case_field(lexical["rows"], "terminal_first_half_unexplained_seconds", to_float, 0.0) or 0.0,
        sum_case_field(lexical["rows"], "terminal_first_half_parent_seconds", to_float, 0.0),
    ) or 0.0
    dominant_span = dominant_first_half_span_from_rows(lexical["rows"])
    overhead_suspect = (
        candidate_index_seconds_ratio_lexical_vs_coarse > 1.10
        or terminal_parent_seconds_ratio_lexical_vs_terminal > 1.10
    )
    if scope == "per_profile_mode":
        overhead_suspect = overhead_suspect or sim_seconds_ratio_lexical_vs_coarse > 1.05
        overhead_suspect = overhead_suspect or total_seconds_ratio_lexical_vs_coarse > 1.05
    if overhead_suspect:
        profile_mode_overhead_status = "suspect"
        trusted_span_timing = False
        trusted_span_source = "none"
        recommended_next_action = "reduce_profiler_timer_overhead"
    else:
        profile_mode_overhead_status = "ok"
        trusted_span_timing = True
        trusted_span_source = "lexical_first_half"
        if terminal_first_half_unexplained_share >= 0.20:
            recommended_next_action = "inspect_first_half_timer_scope"
        elif dominant_span == "span_a":
            recommended_next_action = "split_terminal_first_half_span_a"
        elif dominant_span == "span_b":
            recommended_next_action = "split_terminal_first_half_span_b"
        else:
            recommended_next_action = "inspect_first_half_timer_scope"
    for row in case_rows:
        row["recommended_next_action"] = recommended_next_action

    summary = {
        "decision_status": "ready",
        "analysis_mode": "legacy_lexical",
        "benchmark_scope": scope,
        "benchmark_identity_basis": basis,
        "candidate_index_materiality_status": materiality_status,
        "materiality_status_all_modes_match": materiality_status_all_modes_match,
        "materiality_source": "per_mode_lifecycle_summary",
        "profile_mode_overhead_status": profile_mode_overhead_status,
        "trusted_span_timing": trusted_span_timing,
        "trusted_span_source": trusted_span_source,
        "runtime_prototype_allowed": False,
        "recommended_next_action": recommended_next_action,
        "workload_id": workload_id,
        "case_count": len(case_rows),
        "candidate_index_seconds_ratio_terminal_vs_coarse": candidate_index_seconds_ratio_terminal_vs_coarse,
        "candidate_index_seconds_ratio_lexical_vs_coarse": candidate_index_seconds_ratio_lexical_vs_coarse,
        "terminal_parent_seconds_ratio_terminal_vs_coarse": terminal_parent_seconds_ratio_terminal_vs_coarse,
        "terminal_parent_seconds_ratio_lexical_vs_coarse": terminal_parent_seconds_ratio_lexical_vs_coarse,
        "terminal_parent_seconds_ratio_lexical_vs_terminal": terminal_parent_seconds_ratio_lexical_vs_terminal,
        "terminal_first_half_parent_seconds_ratio_lexical_vs_terminal": terminal_first_half_parent_seconds_ratio_lexical_vs_terminal,
        "sim_seconds_ratio_lexical_vs_coarse": sim_seconds_ratio_lexical_vs_coarse,
        "total_seconds_ratio_lexical_vs_coarse": total_seconds_ratio_lexical_vs_coarse,
        "timer_call_count_ratio_lexical_vs_coarse": timer_call_count_ratio_lexical_vs_coarse,
        "terminal_first_half_unexplained_share": terminal_first_half_unexplained_share,
        "dominant_terminal_first_half_span": dominant_span,
        "cases": case_rows,
    }
    return summary


def build_low_overhead_summary(loaded):
    coarse = loaded["coarse"]
    terminal = loaded["terminal"]
    count_only = loaded["count_only"]
    sampled = loaded["sampled"]
    workload_id, case_ids = verify_common_inputs([coarse, terminal, count_only, sampled])
    scope, basis = benchmark_scope([coarse, terminal, count_only, sampled])
    materiality_status, materiality_status_all_modes_match = mirrored_materiality_status(
        [coarse, terminal, count_only, sampled]
    )

    coarse_cases = case_map(coarse)
    terminal_cases = case_map(terminal)
    count_cases = case_map(count_only)
    sampled_cases = case_map(sampled)

    count_only_ratio = ratio(
        sum_case_field(count_only["rows"], "candidate_index_mean_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "candidate_index_mean_seconds", to_float, 0.0),
    )
    sampled_vs_terminal_ratio = ratio(
        sum_case_field(sampled["rows"], "candidate_index_mean_seconds", to_float, 0.0),
        sum_case_field(terminal["rows"], "candidate_index_mean_seconds", to_float, 0.0),
    )
    sampled_vs_coarse_ratio = ratio(
        sum_case_field(sampled["rows"], "candidate_index_mean_seconds", to_float, 0.0),
        sum_case_field(coarse["rows"], "candidate_index_mean_seconds", to_float, 0.0),
    )
    sampled_terminal_parent_ratio = ratio(
        sum_case_field(sampled["rows"], "terminal_path_parent_seconds", to_float, 0.0),
        sum_case_field(terminal["rows"], "terminal_path_parent_seconds", to_float, 0.0),
    )
    timer_count_only_ratio = optional_ratio(
        float(sum_case_field(count_only["rows"], "timer_call_count", to_int, 0) or 0.0),
        max(float(sum_case_field(coarse["rows"], "timer_call_count", to_int, 0) or 0.0), 1.0),
    )
    timer_sampled_ratio = optional_ratio(
        float(sum_case_field(sampled["rows"], "timer_call_count", to_int, 0) or 0.0),
        max(float(sum_case_field(terminal["rows"], "timer_call_count", to_int, 0) or 0.0), 1.0),
    )
    terminal_first_half_unexplained_share = optional_ratio(
        sum_case_field(sampled["rows"], "terminal_first_half_unexplained_seconds", to_float, 0.0) or 0.0,
        sum_case_field(sampled["rows"], "terminal_first_half_parent_seconds", to_float, 0.0),
    ) or 0.0
    dominant_span = dominant_first_half_span_from_rows(sampled["rows"])
    span_a_parent_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if span_a_parent_seconds is None:
        span_a_parent_seconds = sum_case_field(
            sampled["rows"], "terminal_first_half_span_a_seconds", to_float, 0.0
        )
    span_a_unexplained_share = optional_ratio(
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0,
        span_a_parent_seconds,
    ) or 0.0
    dominant_span_a_child = dominant_first_half_span_a_child_from_rows(sampled["rows"])
    span_a0_parent_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_mean_seconds",
        ],
        to_float,
        None,
    )
    if span_a0_parent_seconds is None:
        span_a0_parent_seconds = sum_case_field(
            sampled["rows"], "terminal_first_half_span_a0_seconds", to_float, 0.0
        )
    span_a0_unexplained_share = optional_ratio(
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0,
        span_a0_parent_seconds,
    ) or 0.0
    span_a0_gap_before_a00_share = optional_ratio(
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0,
        span_a0_parent_seconds,
    ) or 0.0
    span_a0_gap_between_a00_a01_share = optional_ratio(
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_between_a00_a01_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0,
        span_a0_parent_seconds,
    ) or 0.0
    span_a0_gap_after_a01_share = optional_ratio(
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_after_a01_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0,
        span_a0_parent_seconds,
    ) or 0.0
    span_a0_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_sampled_event_count",
        ],
        to_int,
        None,
    )
    span_a0_covered_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    span_a0_unclassified_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    span_a0_multi_child_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if (
        span_a0_covered_sampled_event_count is None
        and span_a0_sampled_event_count is not None
        and span_a0_unclassified_sampled_event_count is not None
    ):
        span_a0_covered_sampled_event_count = max(
            int(span_a0_sampled_event_count) - int(span_a0_unclassified_sampled_event_count), 0
        )
    span_a0_coverage_share = optional_ratio(
        span_a0_covered_sampled_event_count, span_a0_sampled_event_count
    ) or 0.0
    span_a0_unclassified_share = optional_ratio(
        span_a0_unclassified_sampled_event_count, span_a0_sampled_event_count
    ) or 0.0
    span_a0_multi_child_share = optional_ratio(
        span_a0_multi_child_sampled_event_count, span_a0_sampled_event_count
    ) or 0.0
    dominant_span_a0_child = dominant_first_half_span_a0_child_from_rows(sampled["rows"])
    sampled_count_closure_status = sampled_count_closure_status_from_rows(sampled["rows"])
    gap_before_a00_parent_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_mean_seconds",
            "terminal_first_half_span_a0_gap_before_a00_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
        ],
        to_float,
        None,
    )
    if gap_before_a00_parent_seconds is None:
        gap_before_a00_parent_seconds = 0.0
    gap_before_a00_span_0_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_parent_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_mean_seconds",
            "terminal_first_half_span_a0_gap_before_a00_span_0_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds",
        ],
        to_float,
        None,
    )
    if gap_before_a00_span_0_parent_seconds is None:
        gap_before_a00_span_0_parent_seconds = gap_before_a00_span_0_seconds
    gap_before_a00_span_0_child_0_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_child_1_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_1_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_1_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_child_known_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_child_known_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_child_known_mean_seconds",
        ],
        to_float,
        None,
    )
    if gap_before_a00_child_known_seconds is None:
        gap_before_a00_child_known_seconds = (
            gap_before_a00_span_0_seconds + gap_before_a00_span_1_seconds
        )
    gap_before_a00_unexplained_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_unexplained_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unexplained_mean_seconds",
        ],
        to_float,
        None,
    )
    if gap_before_a00_unexplained_seconds is None:
        gap_before_a00_unexplained_seconds = max(
            gap_before_a00_parent_seconds - gap_before_a00_child_known_seconds, 0.0
        )
    gap_before_a00_unexplained_share = optional_ratio(
        gap_before_a00_unexplained_seconds, gap_before_a00_parent_seconds
    ) or 0.0
    gap_before_a00_span_0_child_known_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_known_mean_seconds",
        ],
        to_float,
        None,
    )
    if gap_before_a00_span_0_child_known_seconds is None:
        gap_before_a00_span_0_child_known_seconds = (
            gap_before_a00_span_0_child_0_seconds + gap_before_a00_span_0_child_1_seconds
        )
    gap_before_a00_span_0_unexplained_seconds = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_mean_seconds",
        ],
        to_float,
        None,
    )
    if gap_before_a00_span_0_unexplained_seconds is None:
        gap_before_a00_span_0_unexplained_seconds = max(
            gap_before_a00_span_0_parent_seconds
            - gap_before_a00_span_0_child_known_seconds,
            0.0,
        )
    gap_before_a00_span_0_share = optional_ratio(
        gap_before_a00_span_0_seconds, gap_before_a00_parent_seconds
    ) or 0.0
    gap_before_a00_span_1_share = optional_ratio(
        gap_before_a00_span_1_seconds, gap_before_a00_parent_seconds
    ) or 0.0
    gap_before_a00_span_0_child_0_share = optional_ratio(
        gap_before_a00_span_0_child_0_seconds, gap_before_a00_span_0_parent_seconds
    ) or 0.0
    gap_before_a00_span_0_child_1_share = optional_ratio(
        gap_before_a00_span_0_child_1_seconds, gap_before_a00_span_0_parent_seconds
    ) or 0.0
    gap_before_a00_span_0_unexplained_share = optional_ratio(
        gap_before_a00_span_0_unexplained_seconds, gap_before_a00_span_0_parent_seconds
    ) or 0.0
    gap_before_a00_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_covered_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_unclassified_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_multi_child_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if (
        gap_before_a00_covered_sampled_event_count is None
        and gap_before_a00_sampled_event_count is not None
        and gap_before_a00_unclassified_sampled_event_count is not None
    ):
        gap_before_a00_covered_sampled_event_count = max(
            int(gap_before_a00_sampled_event_count)
            - int(gap_before_a00_unclassified_sampled_event_count),
            0,
        )
    gap_before_a00_coverage_share = optional_ratio(
        gap_before_a00_covered_sampled_event_count, gap_before_a00_sampled_event_count
    ) or 0.0
    gap_before_a00_unclassified_share = optional_ratio(
        gap_before_a00_unclassified_sampled_event_count, gap_before_a00_sampled_event_count
    ) or 0.0
    gap_before_a00_multi_child_share = optional_ratio(
        gap_before_a00_multi_child_sampled_event_count, gap_before_a00_sampled_event_count
    ) or 0.0
    dominant_gap_before_a00_child = dominant_first_half_span_a0_gap_before_a00_child_from_rows(
        sampled["rows"]
    )
    gap_before_a00_sampled_count_closure_status = (
        gap_before_a00_sampled_count_closure_status_from_rows(sampled["rows"])
    )
    gap_before_a00_span_0_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_covered_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_child_0_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_child_1_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_unclassified_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_multi_child_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count",
        ],
        to_int,
        None,
    )
    if (
        gap_before_a00_span_0_covered_sampled_event_count is None
        and gap_before_a00_span_0_sampled_event_count is not None
        and gap_before_a00_span_0_unclassified_sampled_event_count is not None
    ):
        gap_before_a00_span_0_covered_sampled_event_count = max(
            int(gap_before_a00_span_0_sampled_event_count)
            - int(gap_before_a00_span_0_unclassified_sampled_event_count),
            0,
        )
    gap_before_a00_span_0_coverage_share = optional_ratio(
        gap_before_a00_span_0_covered_sampled_event_count,
        gap_before_a00_span_0_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_unclassified_share = optional_ratio(
        gap_before_a00_span_0_unclassified_sampled_event_count,
        gap_before_a00_span_0_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_multi_child_share = optional_ratio(
        gap_before_a00_span_0_multi_child_sampled_event_count,
        gap_before_a00_span_0_sampled_event_count,
    ) or 0.0
    dominant_gap_before_a00_span_0_child = (
        dominant_first_half_span_a0_gap_before_a00_span_0_child_from_rows(sampled["rows"])
    )
    gap_before_a00_span_0_sampled_count_closure_status = (
        gap_before_a00_span_0_sampled_count_closure_status_from_rows(sampled["rows"])
    )
    span_a0_split_available = (
        (
            sum_case_field_with_fallback(
                sampled["rows"],
                [
                    "terminal_first_half_span_a0_gap_before_a00_seconds",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
                ],
                to_float,
                0.0,
            )
            or 0.0
        )
        + (
            sum_case_field_with_fallback(
                sampled["rows"],
                [
                    "terminal_first_half_span_a00_seconds",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_mean_seconds",
                ],
                to_float,
                0.0,
            )
            or 0.0
        )
        + (
            sum_case_field_with_fallback(
                sampled["rows"],
                [
                    "terminal_first_half_span_a0_gap_between_a00_a01_seconds",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_mean_seconds",
                ],
                to_float,
                0.0,
            )
            or 0.0
        )
        + (
            sum_case_field_with_fallback(
                sampled["rows"],
                [
                    "terminal_first_half_span_a01_seconds",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_mean_seconds",
                ],
                to_float,
                0.0,
            )
            or 0.0
        )
        + (
            sum_case_field_with_fallback(
                sampled["rows"],
                [
                    "terminal_first_half_span_a0_gap_after_a01_seconds",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_mean_seconds",
                ],
                to_float,
                0.0,
            )
            or 0.0
        )
    ) > 0.0 or dominant_span_a0_child not in {"", "unknown", "mixed"}
    gap_before_a00_split_available = (
        gap_before_a00_span_0_seconds + gap_before_a00_span_1_seconds
    ) > 0.0 or dominant_gap_before_a00_child not in {"", "unknown", "mixed"}
    gap_before_a00_span_0_split_available = (
        gap_before_a00_span_0_child_0_seconds + gap_before_a00_span_0_child_1_seconds
    ) > 0.0 or dominant_gap_before_a00_span_0_child not in {"", "unknown", "mixed"}
    gap_before_a00_span_0_case_dominance = gap_before_a00_span_0_case_weighted_dominance(
        sampled["rows"]
    )
    gap_before_a00_span_0_case_weighted_dominant_child = gap_before_a00_span_0_case_dominance[
        "case_weighted_dominant_child"
    ]
    gap_before_a00_span_0_case_majority_share = gap_before_a00_span_0_case_dominance[
        "case_majority_share"
    ]
    gap_before_a00_span_0_event_weighted_dominant_child = gap_before_a00_span_0_case_dominance[
        "event_weighted_dominant_child"
    ]
    gap_before_a00_span_0_seconds_weighted_dominant_child = (
        dominant_gap_before_a00_span_0_child
    )
    gap_before_a00_span_0_child_margin_seconds = abs(
        gap_before_a00_span_0_child_0_seconds - gap_before_a00_span_0_child_1_seconds
    )
    gap_before_a00_span_0_child_margin_share = optional_ratio(
        gap_before_a00_span_0_child_margin_seconds, gap_before_a00_span_0_parent_seconds
    ) or 0.0
    if (
        gap_before_a00_span_0_case_weighted_dominant_child in {"child_0", "child_1"}
        and gap_before_a00_span_0_seconds_weighted_dominant_child in {"child_0", "child_1"}
        and gap_before_a00_span_0_case_weighted_dominant_child
        != gap_before_a00_span_0_seconds_weighted_dominant_child
    ):
        gap_before_a00_span_0_dominance_status = "case_weighted_aggregate_conflict"
    elif gap_before_a00_span_0_case_majority_share < 0.80:
        gap_before_a00_span_0_dominance_status = "unstable"
    elif gap_before_a00_span_0_child_margin_share < 0.05:
        gap_before_a00_span_0_dominance_status = "near_tie"
    elif gap_before_a00_span_0_seconds_weighted_dominant_child in {"child_0", "child_1"}:
        gap_before_a00_span_0_dominance_status = "stable"
    else:
        gap_before_a00_span_0_dominance_status = "unknown"
    gap_before_a00_span_0_alt_parent_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_left_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_child_known_seconds = (
        gap_before_a00_span_0_alt_left_seconds + gap_before_a00_span_0_alt_right_seconds
    )
    gap_before_a00_span_0_alt_unexplained_seconds = max(
        gap_before_a00_span_0_alt_parent_seconds
        - gap_before_a00_span_0_alt_child_known_seconds,
        0.0,
    )
    gap_before_a00_span_0_alt_unexplained_share = optional_ratio(
        gap_before_a00_span_0_alt_unexplained_seconds,
        gap_before_a00_span_0_alt_parent_seconds,
    ) or 0.0
    gap_before_a00_span_0_alt_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_alt_covered_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_alt_left_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_alt_right_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_alt_unclassified_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_multi_child_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    if (
        gap_before_a00_span_0_alt_covered_sampled_event_count is None
        and gap_before_a00_span_0_alt_sampled_event_count is not None
        and gap_before_a00_span_0_alt_unclassified_sampled_event_count is not None
    ):
        gap_before_a00_span_0_alt_covered_sampled_event_count = max(
            int(gap_before_a00_span_0_alt_sampled_event_count)
            - int(gap_before_a00_span_0_alt_unclassified_sampled_event_count),
            0,
        )
    gap_before_a00_span_0_alt_coverage_share = optional_ratio(
        gap_before_a00_span_0_alt_covered_sampled_event_count,
        gap_before_a00_span_0_alt_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_alt_unclassified_share = optional_ratio(
        gap_before_a00_span_0_alt_unclassified_sampled_event_count,
        gap_before_a00_span_0_alt_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_alt_multi_child_share = optional_ratio(
        gap_before_a00_span_0_alt_multi_child_sampled_event_count,
        gap_before_a00_span_0_alt_sampled_event_count,
    ) or 0.0
    dominant_gap_before_a00_span_0_alt_child = (
        dominant_first_half_span_a0_gap_before_a00_span_0_alt_child_from_rows(
            sampled["rows"]
        )
    )
    gap_before_a00_span_0_alt_sampled_count_closure_status = (
        gap_before_a00_span_0_alt_sampled_count_closure_status_from_rows(sampled["rows"])
    )
    gap_before_a00_span_0_alt_split_available = (
        gap_before_a00_span_0_alt_left_seconds + gap_before_a00_span_0_alt_right_seconds
    ) > 0.0 or dominant_gap_before_a00_span_0_alt_child not in {"", "unknown", "mixed"}
    gap_before_a00_span_0_alt_case_dominance = (
        gap_before_a00_span_0_alt_case_weighted_dominance(sampled["rows"])
    )
    gap_before_a00_span_0_alt_case_weighted_dominant_child = (
        gap_before_a00_span_0_alt_case_dominance["case_weighted_dominant_child"]
    )
    gap_before_a00_span_0_alt_case_majority_share = (
        gap_before_a00_span_0_alt_case_dominance["case_majority_share"]
    )
    gap_before_a00_span_0_alt_event_weighted_dominant_child = (
        gap_before_a00_span_0_alt_case_dominance["event_weighted_dominant_child"]
    )
    gap_before_a00_span_0_alt_seconds_weighted_dominant_child = (
        dominant_gap_before_a00_span_0_alt_child
    )
    gap_before_a00_span_0_alt_child_margin_seconds = abs(
        gap_before_a00_span_0_alt_left_seconds - gap_before_a00_span_0_alt_right_seconds
    )
    gap_before_a00_span_0_alt_child_margin_share = optional_ratio(
        gap_before_a00_span_0_alt_child_margin_seconds,
        gap_before_a00_span_0_alt_parent_seconds,
    ) or 0.0
    if (
        gap_before_a00_span_0_alt_case_weighted_dominant_child
        in {"alt_left", "alt_right"}
        and gap_before_a00_span_0_alt_seconds_weighted_dominant_child
        in {"alt_left", "alt_right"}
        and gap_before_a00_span_0_alt_case_weighted_dominant_child
        != gap_before_a00_span_0_alt_seconds_weighted_dominant_child
    ):
        gap_before_a00_span_0_alt_dominance_status = (
            "case_weighted_aggregate_conflict"
        )
    elif gap_before_a00_span_0_alt_case_majority_share < 0.80:
        gap_before_a00_span_0_alt_dominance_status = "unstable"
    elif gap_before_a00_span_0_alt_child_margin_share < 0.05:
        gap_before_a00_span_0_alt_dominance_status = "near_tie"
    elif gap_before_a00_span_0_alt_seconds_weighted_dominant_child in {
        "alt_left",
        "alt_right",
    }:
        gap_before_a00_span_0_alt_dominance_status = "stable"
    else:
        gap_before_a00_span_0_alt_dominance_status = "unknown"
    gap_before_a00_span_0_alt_left_share = optional_ratio(
        gap_before_a00_span_0_alt_left_seconds, gap_before_a00_span_0_alt_parent_seconds
    ) or 0.0
    gap_before_a00_span_0_alt_right_share = optional_ratio(
        gap_before_a00_span_0_alt_right_seconds, gap_before_a00_span_0_alt_parent_seconds
    ) or 0.0
    gap_before_a00_span_0_alt_right_parent_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_child_0_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_child_1_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_child_known_seconds = (
        gap_before_a00_span_0_alt_right_child_0_seconds
        + gap_before_a00_span_0_alt_right_child_1_seconds
    )
    gap_before_a00_span_0_alt_right_unexplained_seconds = max(
        gap_before_a00_span_0_alt_right_parent_seconds
        - gap_before_a00_span_0_alt_right_child_known_seconds,
        0.0,
    )
    gap_before_a00_span_0_alt_right_unexplained_share = optional_ratio(
        gap_before_a00_span_0_alt_right_unexplained_seconds,
        gap_before_a00_span_0_alt_right_parent_seconds,
    ) or 0.0
    gap_before_a00_span_0_alt_right_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_alt_right_covered_sampled_event_count = sum_case_field_with_fallback(
        sampled["rows"],
        [
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
            "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
        ],
        to_int,
        None,
    )
    gap_before_a00_span_0_alt_right_child_0_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_child_1_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_unclassified_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_multi_child_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    if (
        gap_before_a00_span_0_alt_right_covered_sampled_event_count is None
        and gap_before_a00_span_0_alt_right_sampled_event_count is not None
        and gap_before_a00_span_0_alt_right_unclassified_sampled_event_count is not None
    ):
        gap_before_a00_span_0_alt_right_covered_sampled_event_count = max(
            int(gap_before_a00_span_0_alt_right_sampled_event_count)
            - int(gap_before_a00_span_0_alt_right_unclassified_sampled_event_count),
            0,
        )
    gap_before_a00_span_0_alt_right_coverage_share = optional_ratio(
        gap_before_a00_span_0_alt_right_covered_sampled_event_count,
        gap_before_a00_span_0_alt_right_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_alt_right_unclassified_share = optional_ratio(
        gap_before_a00_span_0_alt_right_unclassified_sampled_event_count,
        gap_before_a00_span_0_alt_right_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_alt_right_multi_child_share = optional_ratio(
        gap_before_a00_span_0_alt_right_multi_child_sampled_event_count,
        gap_before_a00_span_0_alt_right_sampled_event_count,
    ) or 0.0
    dominant_gap_before_a00_span_0_alt_right_child = (
        dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_child_from_rows(
            sampled["rows"]
        )
    )
    gap_before_a00_span_0_alt_right_sampled_count_closure_status = (
        gap_before_a00_span_0_alt_right_sampled_count_closure_status_from_rows(
            sampled["rows"]
        )
    )
    gap_before_a00_span_0_alt_right_split_available = (
        gap_before_a00_span_0_alt_right_child_0_seconds
        + gap_before_a00_span_0_alt_right_child_1_seconds
    ) > 0.0 or dominant_gap_before_a00_span_0_alt_right_child not in {"", "unknown", "mixed"}
    gap_before_a00_span_0_alt_right_case_dominance = (
        gap_before_a00_span_0_alt_right_case_weighted_dominance(sampled["rows"])
    )
    gap_before_a00_span_0_alt_right_case_weighted_dominant_child = (
        gap_before_a00_span_0_alt_right_case_dominance["case_weighted_dominant_child"]
    )
    gap_before_a00_span_0_alt_right_case_majority_share = (
        gap_before_a00_span_0_alt_right_case_dominance["case_majority_share"]
    )
    gap_before_a00_span_0_alt_right_event_weighted_dominant_child = (
        gap_before_a00_span_0_alt_right_case_dominance["event_weighted_dominant_child"]
    )
    gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child = (
        dominant_gap_before_a00_span_0_alt_right_child
    )
    gap_before_a00_span_0_alt_right_child_margin_seconds = abs(
        gap_before_a00_span_0_alt_right_child_0_seconds
        - gap_before_a00_span_0_alt_right_child_1_seconds
    )
    gap_before_a00_span_0_alt_right_child_margin_share = optional_ratio(
        gap_before_a00_span_0_alt_right_child_margin_seconds,
        gap_before_a00_span_0_alt_right_parent_seconds,
    ) or 0.0
    if (
        gap_before_a00_span_0_alt_right_case_weighted_dominant_child
        in {"child_0", "child_1"}
        and gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child
        in {"child_0", "child_1"}
        and gap_before_a00_span_0_alt_right_case_weighted_dominant_child
        != gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child
    ):
        gap_before_a00_span_0_alt_right_dominance_status = (
            "case_weighted_aggregate_conflict"
        )
    elif gap_before_a00_span_0_alt_right_case_majority_share < 0.80:
        gap_before_a00_span_0_alt_right_dominance_status = "unstable"
    elif gap_before_a00_span_0_alt_right_child_margin_share < 0.05:
        gap_before_a00_span_0_alt_right_dominance_status = "near_tie"
    elif gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child in {
        "child_0",
        "child_1",
    }:
        gap_before_a00_span_0_alt_right_dominance_status = "stable"
    else:
        gap_before_a00_span_0_alt_right_dominance_status = "unknown"
    gap_before_a00_span_0_alt_right_repart_parent_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_repart_left_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_repart_right_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds",
            ],
            to_float,
            0.0,
        )
        or 0.0
    )
    gap_before_a00_span_0_alt_right_repart_unexplained_seconds = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_mean_seconds",
            ],
            to_float,
            None,
        )
    )
    if gap_before_a00_span_0_alt_right_repart_unexplained_seconds is None:
        gap_before_a00_span_0_alt_right_repart_unexplained_seconds = max(
            gap_before_a00_span_0_alt_right_repart_parent_seconds
            - (
                gap_before_a00_span_0_alt_right_repart_left_seconds
                + gap_before_a00_span_0_alt_right_repart_right_seconds
            ),
            0.0,
        )
    gap_before_a00_span_0_alt_right_repart_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_repart_left_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_repart_right_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count = (
        sum_case_field_with_fallback(
            sampled["rows"],
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
    )
    if (
        gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count is None
        and gap_before_a00_span_0_alt_right_repart_sampled_event_count is not None
        and gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count is not None
    ):
        gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count = max(
            int(gap_before_a00_span_0_alt_right_repart_sampled_event_count)
            - int(gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count),
            0,
        )
    gap_before_a00_span_0_alt_right_repart_coverage_share = optional_ratio(
        gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count,
        gap_before_a00_span_0_alt_right_repart_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_alt_right_repart_unclassified_share = optional_ratio(
        gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count,
        gap_before_a00_span_0_alt_right_repart_sampled_event_count,
    ) or 0.0
    gap_before_a00_span_0_alt_right_repart_multi_child_share = optional_ratio(
        gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count,
        gap_before_a00_span_0_alt_right_repart_sampled_event_count,
    ) or 0.0
    dominant_gap_before_a00_span_0_alt_right_repart_child = (
        dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_from_rows(
            sampled["rows"]
        )
    )
    gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status = (
        gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status_from_rows(
            sampled["rows"]
        )
    )
    gap_before_a00_span_0_alt_right_repart_split_available = (
        gap_before_a00_span_0_alt_right_repart_left_seconds
        + gap_before_a00_span_0_alt_right_repart_right_seconds
    ) > 0.0 or dominant_gap_before_a00_span_0_alt_right_repart_child not in {
        "",
        "unknown",
        "mixed",
    }
    gap_before_a00_span_0_alt_right_repart_case_dominance = (
        gap_before_a00_span_0_alt_right_repart_case_weighted_dominance(sampled["rows"])
    )
    gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child = (
        gap_before_a00_span_0_alt_right_repart_case_dominance["case_weighted_dominant_child"]
    )
    gap_before_a00_span_0_alt_right_repart_case_majority_share = (
        gap_before_a00_span_0_alt_right_repart_case_dominance["case_majority_share"]
    )
    gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child = (
        gap_before_a00_span_0_alt_right_repart_case_dominance["event_weighted_dominant_child"]
    )
    gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child = (
        dominant_gap_before_a00_span_0_alt_right_repart_child
    )
    gap_before_a00_span_0_alt_right_repart_child_margin_seconds = abs(
        gap_before_a00_span_0_alt_right_repart_left_seconds
        - gap_before_a00_span_0_alt_right_repart_right_seconds
    )
    gap_before_a00_span_0_alt_right_repart_child_margin_share = optional_ratio(
        gap_before_a00_span_0_alt_right_repart_child_margin_seconds,
        gap_before_a00_span_0_alt_right_repart_parent_seconds,
    ) or 0.0
    gap_before_a00_span_0_alt_right_repart_unexplained_share = optional_ratio(
        gap_before_a00_span_0_alt_right_repart_unexplained_seconds,
        gap_before_a00_span_0_alt_right_repart_parent_seconds,
    ) or 0.0
    if (
        gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child
        in {"repart_left", "repart_right"}
        and gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child
        in {"repart_left", "repart_right"}
        and gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child
        != gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child
    ):
        gap_before_a00_span_0_alt_right_repart_dominance_status = (
            "case_weighted_aggregate_conflict"
        )
    elif gap_before_a00_span_0_alt_right_repart_case_majority_share < 0.80:
        gap_before_a00_span_0_alt_right_repart_dominance_status = "unstable"
    elif gap_before_a00_span_0_alt_right_repart_child_margin_share < 0.05:
        gap_before_a00_span_0_alt_right_repart_dominance_status = "near_tie"
    elif gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child in {
        "repart_left",
        "repart_right",
    }:
        gap_before_a00_span_0_alt_right_repart_dominance_status = "stable"
    else:
        gap_before_a00_span_0_alt_right_repart_dominance_status = "unknown"
    gap_before_a00_span_0_alt_right_repartition_statuses = []
    if gap_before_a00_span_0_alt_right_split_available:
        gap_before_a00_span_0_alt_right_repartition_statuses.append(
            gap_before_a00_span_0_alt_right_dominance_status
        )
    if gap_before_a00_span_0_alt_right_repart_split_available:
        gap_before_a00_span_0_alt_right_repartition_statuses.append(
            gap_before_a00_span_0_alt_right_repart_dominance_status
        )
    gap_before_a00_span_0_alt_right_repartition_attempt_count = len(
        gap_before_a00_span_0_alt_right_repartition_statuses
    )
    gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count = 0
    for dominance_status in reversed(
        gap_before_a00_span_0_alt_right_repartition_statuses
    ):
        if dominance_status != "near_tie":
            break
        gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count += 1
    if gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count >= 2:
        gap_before_a00_span_0_alt_right_subtree_status = (
            "distributed_overhead_no_stable_leaf"
        )
    elif gap_before_a00_span_0_alt_right_repartition_attempt_count > 0:
        gap_before_a00_span_0_alt_right_subtree_status = "profiling_active"
    else:
        gap_before_a00_span_0_alt_right_subtree_status = "not_started"
    profile_sample_log2 = to_int(sampled["rows"][0], "profile_sample_log2", None)
    profile_sample_rate = to_float(sampled["rows"][0], "profile_sample_rate", None)

    if count_only_ratio > 1.10:
        overhead_status = "suspect_count_bookkeeping"
        trusted_span_timing = False
        trusted_span_source = "none"
        recommended_next_action = "reduce_profiler_timer_overhead"
    elif sampled_vs_terminal_ratio > 1.10 or sampled_terminal_parent_ratio > 1.10:
        overhead_status = "suspect_sampled_timer"
        trusted_span_timing = False
        trusted_span_source = "none"
        recommended_next_action = "lower_sampling_rate"
    else:
        overhead_status = "ok"
        trusted_span_timing = True
        trusted_span_source = "sampled"
        if terminal_first_half_unexplained_share >= 0.20:
            recommended_next_action = "inspect_first_half_timer_scope"
        elif dominant_span == "span_a":
            if span_a_unexplained_share >= 0.20:
                recommended_next_action = "inspect_terminal_first_half_span_a_timer_scope"
            elif dominant_span_a_child == "span_a0":
                if not span_a0_split_available:
                    recommended_next_action = "split_terminal_first_half_span_a0"
                elif (
                    span_a0_unexplained_share >= 0.20
                    or sampled_count_closure_status != "closed"
                ):
                    recommended_next_action = "inspect_terminal_first_half_span_a0_timer_scope"
                elif dominant_span_a0_child == "gap_before_a00":
                    if not gap_before_a00_split_available:
                        recommended_next_action = "split_terminal_first_half_span_a0_gap_before_a00"
                    elif (
                        gap_before_a00_sampled_count_closure_status != "closed"
                        or gap_before_a00_unexplained_share >= 0.20
                    ):
                        recommended_next_action = (
                            "inspect_terminal_first_half_span_a0_gap_before_a00_timer_scope"
                        )
                    elif dominant_gap_before_a00_child == "span_0":
                        if not gap_before_a00_span_0_split_available:
                            recommended_next_action = (
                                "split_terminal_first_half_span_a0_gap_before_a00_span_0"
                            )
                        elif (
                            gap_before_a00_span_0_sampled_count_closure_status != "closed"
                            or gap_before_a00_span_0_unclassified_share > 0.01
                            or gap_before_a00_span_0_unexplained_share >= 0.10
                        ):
                            recommended_next_action = (
                                "inspect_gap_before_a00_span_0_timer_scope"
                            )
                        elif gap_before_a00_span_0_alt_split_available:
                            if (
                                gap_before_a00_span_0_alt_sampled_count_closure_status
                                != "closed"
                                or gap_before_a00_span_0_alt_unclassified_share > 0.01
                                or gap_before_a00_span_0_alt_unexplained_share >= 0.10
                            ):
                                recommended_next_action = (
                                    "inspect_gap_before_a00_span_0_alt_timer_scope"
                                )
                            elif (
                                gap_before_a00_span_0_alt_dominance_status
                                in {"near_tie", "unstable"}
                                or (
                                    gap_before_a00_span_0_alt_dominance_status
                                    == "case_weighted_aggregate_conflict"
                                    and gap_before_a00_span_0_alt_child_margin_share
                                    < 0.01
                                )
                            ):
                                recommended_next_action = (
                                    "repartition_gap_before_a00_span_0_boundary"
                                )
                            elif (
                                gap_before_a00_span_0_alt_dominance_status
                                == "case_weighted_aggregate_conflict"
                            ):
                                recommended_next_action = (
                                    "split_gap_before_a00_span_0_alt_children_in_parallel"
                                )
                            elif (
                                gap_before_a00_span_0_alt_dominance_status == "stable"
                                and gap_before_a00_span_0_alt_child_margin_share >= 0.05
                                and gap_before_a00_span_0_alt_seconds_weighted_dominant_child
                                == "alt_left"
                            ):
                                recommended_next_action = (
                                    "split_gap_before_a00_span_0_alt_left"
                                )
                            elif (
                                gap_before_a00_span_0_alt_dominance_status == "stable"
                                and gap_before_a00_span_0_alt_child_margin_share >= 0.05
                                and gap_before_a00_span_0_alt_seconds_weighted_dominant_child
                                == "alt_right"
                            ):
                                if not gap_before_a00_span_0_alt_right_split_available:
                                    recommended_next_action = (
                                        "split_gap_before_a00_span_0_alt_right"
                                    )
                                elif (
                                    gap_before_a00_span_0_alt_right_sampled_count_closure_status
                                    != "closed"
                                    or gap_before_a00_span_0_alt_right_unclassified_share
                                    > 0.01
                                    or gap_before_a00_span_0_alt_right_unexplained_share
                                    >= 0.10
                                ):
                                    recommended_next_action = (
                                        "inspect_gap_before_a00_span_0_alt_right_timer_scope"
                                    )
                                elif gap_before_a00_span_0_alt_right_repart_split_available:
                                    if (
                                        gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status
                                        != "closed"
                                        or gap_before_a00_span_0_alt_right_repart_unclassified_share
                                        > 0.01
                                        or gap_before_a00_span_0_alt_right_repart_unexplained_share
                                        >= 0.10
                                    ):
                                        recommended_next_action = (
                                            "inspect_gap_before_a00_span_0_alt_right_repart_timer_scope"
                                        )
                                    elif (
                                        gap_before_a00_span_0_alt_right_subtree_status
                                        == "distributed_overhead_no_stable_leaf"
                                    ):
                                        recommended_next_action = (
                                            "mark_gap_before_a00_span_0_alt_right_as_distributed_overhead"
                                        )
                                    elif (
                                        gap_before_a00_span_0_alt_right_repart_dominance_status
                                        in {"near_tie", "unstable"}
                                        or (
                                            gap_before_a00_span_0_alt_right_repart_dominance_status
                                            == "case_weighted_aggregate_conflict"
                                            and gap_before_a00_span_0_alt_right_repart_child_margin_share
                                            < 0.01
                                        )
                                    ):
                                        recommended_next_action = (
                                            "repartition_gap_before_a00_span_0_alt_right_boundary"
                                        )
                                    elif (
                                        gap_before_a00_span_0_alt_right_repart_dominance_status
                                        == "case_weighted_aggregate_conflict"
                                    ):
                                        recommended_next_action = (
                                            "split_gap_before_a00_span_0_alt_right_repart_children_in_parallel"
                                        )
                                    elif (
                                        gap_before_a00_span_0_alt_right_repart_dominance_status
                                        == "stable"
                                        and gap_before_a00_span_0_alt_right_repart_child_margin_share
                                        >= 0.05
                                        and gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child
                                        == "repart_left"
                                    ):
                                        recommended_next_action = (
                                            "split_gap_before_a00_span_0_alt_right_repart_left"
                                        )
                                    elif (
                                        gap_before_a00_span_0_alt_right_repart_dominance_status
                                        == "stable"
                                        and gap_before_a00_span_0_alt_right_repart_child_margin_share
                                        >= 0.05
                                        and gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child
                                        == "repart_right"
                                    ):
                                        recommended_next_action = (
                                            "split_gap_before_a00_span_0_alt_right_repart_right"
                                        )
                                    else:
                                        recommended_next_action = (
                                            "no_runtime_prototype_selected"
                                        )
                                elif (
                                    gap_before_a00_span_0_alt_right_dominance_status
                                    in {"near_tie", "unstable"}
                                    or (
                                        gap_before_a00_span_0_alt_right_dominance_status
                                        == "case_weighted_aggregate_conflict"
                                        and gap_before_a00_span_0_alt_right_child_margin_share
                                        < 0.01
                                    )
                                ):
                                    recommended_next_action = (
                                        "repartition_gap_before_a00_span_0_alt_right_boundary"
                                    )
                                elif (
                                    gap_before_a00_span_0_alt_right_dominance_status
                                    == "case_weighted_aggregate_conflict"
                                ):
                                    recommended_next_action = (
                                        "split_gap_before_a00_span_0_alt_right_children_in_parallel"
                                    )
                                elif (
                                    gap_before_a00_span_0_alt_right_dominance_status
                                    == "stable"
                                    and gap_before_a00_span_0_alt_right_child_margin_share
                                    >= 0.05
                                    and gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child
                                    == "child_0"
                                ):
                                    recommended_next_action = (
                                        "split_gap_before_a00_span_0_alt_right_child_0"
                                    )
                                elif (
                                    gap_before_a00_span_0_alt_right_dominance_status
                                    == "stable"
                                    and gap_before_a00_span_0_alt_right_child_margin_share
                                    >= 0.05
                                    and gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child
                                    == "child_1"
                                ):
                                    recommended_next_action = (
                                        "split_gap_before_a00_span_0_alt_right_child_1"
                                    )
                                else:
                                    recommended_next_action = (
                                        "no_runtime_prototype_selected"
                                    )
                            else:
                                recommended_next_action = (
                                    "no_runtime_prototype_selected"
                                )
                        elif (
                            gap_before_a00_span_0_dominance_status == "near_tie"
                            or (
                                gap_before_a00_span_0_dominance_status
                                == "case_weighted_aggregate_conflict"
                                and gap_before_a00_span_0_child_margin_share < 0.01
                            )
                        ):
                            recommended_next_action = (
                                "repartition_gap_before_a00_span_0_boundary"
                            )
                        elif (
                            gap_before_a00_span_0_dominance_status
                            == "case_weighted_aggregate_conflict"
                        ):
                            recommended_next_action = (
                                "split_gap_before_a00_span_0_children_in_parallel"
                            )
                        elif gap_before_a00_span_0_dominance_status != "stable":
                            recommended_next_action = (
                                "resolve_gap_before_a00_span_0_child_dominance_conflict"
                            )
                        elif (
                            gap_before_a00_span_0_seconds_weighted_dominant_child
                            == "child_0"
                        ):
                            recommended_next_action = (
                                "split_terminal_first_half_span_a0_gap_before_a00_span_0_child_0"
                            )
                        elif (
                            gap_before_a00_span_0_seconds_weighted_dominant_child
                            == "child_1"
                        ):
                            recommended_next_action = (
                                "split_terminal_first_half_span_a0_gap_before_a00_span_0_child_1"
                            )
                        else:
                            recommended_next_action = (
                                "split_terminal_first_half_span_a0_gap_before_a00_span_0"
                            )
                    elif dominant_gap_before_a00_child == "span_1":
                        recommended_next_action = (
                            "split_terminal_first_half_span_a0_gap_before_a00_span_1"
                        )
                    else:
                        recommended_next_action = "split_terminal_first_half_span_a0_gap_before_a00"
                elif dominant_span_a0_child == "gap_between_a00_a01":
                    recommended_next_action = "split_terminal_first_half_span_a0_gap_between_a00_a01"
                elif dominant_span_a0_child == "gap_after_a01":
                    recommended_next_action = "split_terminal_first_half_span_a0_gap_after_a01"
                elif dominant_span_a0_child == "span_a00":
                    recommended_next_action = "split_terminal_first_half_span_a00"
                elif dominant_span_a0_child == "span_a01":
                    recommended_next_action = "split_terminal_first_half_span_a01"
                else:
                    recommended_next_action = "split_terminal_first_half_span_a0"
            elif dominant_span_a_child == "span_a1":
                recommended_next_action = "split_terminal_first_half_span_a1"
            else:
                recommended_next_action = "split_terminal_first_half_span_a"
        elif dominant_span == "span_b":
            recommended_next_action = "split_terminal_first_half_span_b"
        else:
            recommended_next_action = "inspect_first_half_timer_scope"

    case_rows = []
    for case_id in case_ids:
        coarse_row = coarse_cases[case_id]
        terminal_row = terminal_cases[case_id]
        count_row = count_cases[case_id]
        sampled_row = sampled_cases[case_id]
        sampled_parent = to_float(sampled_row, "terminal_first_half_parent_seconds", 0.0)
        sampled_unexplained = to_float(sampled_row, "terminal_first_half_unexplained_seconds", 0.0)
        sampled_span_a_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_mean_seconds",
            ],
            to_float,
            None,
        )
        if sampled_span_a_parent is None:
            sampled_span_a_parent = to_float(sampled_row, "terminal_first_half_span_a_seconds", 0.0)
        sampled_span_a_unexplained = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_span_a0_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_mean_seconds",
            ],
            to_float,
            None,
        )
        if sampled_span_a0_parent is None:
            sampled_span_a0_parent = to_float(
                sampled_row, "terminal_first_half_span_a0_seconds", 0.0
            )
        sampled_span_a0_unexplained = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_span_a0_gap_before_a00 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_span_a0_gap_between_a00_a01 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_between_a00_a01_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_span_a0_gap_after_a01 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_after_a01_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_mean_seconds",
                "terminal_first_half_span_a0_gap_before_a00_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_mean_seconds",
                "terminal_first_half_span_a0_gap_before_a00_span_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_child_0 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_child_1 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_1 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_1_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_unexplained = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unexplained_mean_seconds",
            ],
            to_float,
            None,
        )
        if sampled_gap_before_a00_unexplained is None:
            sampled_gap_before_a00_unexplained = max(
                sampled_gap_before_a00_parent
                - (
                    sampled_gap_before_a00_span_0
                    + sampled_gap_before_a00_span_1
                ),
                0.0,
            )
        sampled_gap_before_a00_span_0_unexplained = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_mean_seconds",
            ],
            to_float,
            None,
        )
        if sampled_gap_before_a00_span_0_unexplained is None:
            sampled_gap_before_a00_span_0_unexplained = max(
                sampled_gap_before_a00_span_0_parent
                - (
                    sampled_gap_before_a00_span_0_child_0
                    + sampled_gap_before_a00_span_0_child_1
                ),
                0.0,
            )
        sampled_span_a0_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_span_a0_covered_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_covered_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_covered_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_span_a0_unclassified_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_span_a0_multi_child_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
        if (
            sampled_span_a0_covered_sampled_event_count is None
            and sampled_span_a0_sampled_event_count is not None
            and sampled_span_a0_unclassified_sampled_event_count is not None
        ):
            sampled_span_a0_covered_sampled_event_count = max(
                int(sampled_span_a0_sampled_event_count)
                - int(sampled_span_a0_unclassified_sampled_event_count),
                0,
            )
        sampled_gap_before_a00_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_covered_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_unclassified_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_multi_child_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
        if (
            sampled_gap_before_a00_covered_sampled_event_count is None
            and sampled_gap_before_a00_sampled_event_count is not None
            and sampled_gap_before_a00_unclassified_sampled_event_count is not None
        ):
            sampled_gap_before_a00_covered_sampled_event_count = max(
                int(sampled_gap_before_a00_sampled_event_count)
                - int(sampled_gap_before_a00_unclassified_sampled_event_count),
                0,
            )
        sampled_gap_before_a00_span_0_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_covered_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_child_0_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_child_1_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_unclassified_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_multi_child_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
        if (
            sampled_gap_before_a00_span_0_covered_sampled_event_count is None
            and sampled_gap_before_a00_span_0_sampled_event_count is not None
            and sampled_gap_before_a00_span_0_unclassified_sampled_event_count is not None
        ):
            sampled_gap_before_a00_span_0_covered_sampled_event_count = max(
                int(sampled_gap_before_a00_span_0_sampled_event_count)
                - int(sampled_gap_before_a00_span_0_unclassified_sampled_event_count),
                0,
            )
        sampled_gap_before_a00_span_0_alt_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_left = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_unexplained = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_mean_seconds",
            ],
            to_float,
            None,
        )
        if sampled_gap_before_a00_span_0_alt_unexplained is None:
            sampled_gap_before_a00_span_0_alt_unexplained = max(
                sampled_gap_before_a00_span_0_alt_parent
                - (sampled_gap_before_a00_span_0_alt_left + sampled_gap_before_a00_span_0_alt_right),
                0.0,
            )
        sampled_gap_before_a00_span_0_alt_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_alt_covered_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_alt_unclassified_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_alt_multi_child_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count",
            ],
            to_int,
            None,
        )
        if (
            sampled_gap_before_a00_span_0_alt_covered_sampled_event_count is None
            and sampled_gap_before_a00_span_0_alt_sampled_event_count is not None
            and sampled_gap_before_a00_span_0_alt_unclassified_sampled_event_count is not None
        ):
            sampled_gap_before_a00_span_0_alt_covered_sampled_event_count = max(
                int(sampled_gap_before_a00_span_0_alt_sampled_event_count)
                - int(sampled_gap_before_a00_span_0_alt_unclassified_sampled_event_count),
                0,
            )
        sampled_gap_before_a00_span_0_alt_right_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right_child_0 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right_child_1 = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right_unexplained = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_mean_seconds",
            ],
            to_float,
            None,
        )
        if sampled_gap_before_a00_span_0_alt_right_unexplained is None:
            sampled_gap_before_a00_span_0_alt_right_unexplained = max(
                sampled_gap_before_a00_span_0_alt_right_parent
                - (
                    sampled_gap_before_a00_span_0_alt_right_child_0
                    + sampled_gap_before_a00_span_0_alt_right_child_1
                ),
                0.0,
            )
        sampled_gap_before_a00_span_0_alt_right_sampled_event_count = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count",
            ],
            to_int,
            None,
        )
        sampled_gap_before_a00_span_0_alt_right_covered_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_child_0_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_child_1_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        if (
            sampled_gap_before_a00_span_0_alt_right_covered_sampled_event_count is None
            and sampled_gap_before_a00_span_0_alt_right_sampled_event_count is not None
            and sampled_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count
            is not None
        ):
            sampled_gap_before_a00_span_0_alt_right_covered_sampled_event_count = max(
                int(sampled_gap_before_a00_span_0_alt_right_sampled_event_count)
                - int(sampled_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count),
                0,
            )
        sampled_gap_before_a00_span_0_alt_right_repart_parent = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right_repart_left = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right_repart_right = row_value_with_fallback(
            sampled_row,
            [
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds",
                "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds",
            ],
            to_float,
            0.0,
        )
        sampled_gap_before_a00_span_0_alt_right_repart_unexplained = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_seconds",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_mean_seconds",
                ],
                to_float,
                None,
            )
        )
        if sampled_gap_before_a00_span_0_alt_right_repart_unexplained is None:
            sampled_gap_before_a00_span_0_alt_right_repart_unexplained = max(
                sampled_gap_before_a00_span_0_alt_right_repart_parent
                - (
                    sampled_gap_before_a00_span_0_alt_right_repart_left
                    + sampled_gap_before_a00_span_0_alt_right_repart_right
                ),
                0.0,
            )
        sampled_gap_before_a00_span_0_alt_right_repart_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        sampled_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count = (
            row_value_with_fallback(
                sampled_row,
                [
                    "terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
                    "context_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count",
                ],
                to_int,
                None,
            )
        )
        if (
            sampled_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count
            is None
            and sampled_gap_before_a00_span_0_alt_right_repart_sampled_event_count
            is not None
            and sampled_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count
            is not None
        ):
            sampled_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count = max(
                int(sampled_gap_before_a00_span_0_alt_right_repart_sampled_event_count)
                - int(
                    sampled_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count
                ),
                0,
            )
        case_rows.append(
            {
                "case_id": case_id,
                "candidate_index_seconds_ratio_count_only_vs_coarse": ratio(
                    to_float(count_row, "candidate_index_mean_seconds", 0.0),
                    to_float(coarse_row, "candidate_index_mean_seconds", 0.0),
                ),
                "candidate_index_seconds_ratio_sampled_vs_terminal": ratio(
                    to_float(sampled_row, "candidate_index_mean_seconds", 0.0),
                    to_float(terminal_row, "candidate_index_mean_seconds", 0.0),
                ),
                "terminal_parent_seconds_ratio_sampled_vs_terminal": ratio(
                    to_float(sampled_row, "terminal_path_parent_seconds", 0.0),
                    to_float(terminal_row, "terminal_path_parent_seconds", 0.0),
                ),
                "terminal_first_half_unexplained_share": optional_ratio(
                    sampled_unexplained, sampled_parent
                )
                or 0.0,
                "dominant_terminal_first_half_span": sampled_row["dominant_terminal_first_half_span"],
                "terminal_first_half_span_a_unexplained_share": optional_ratio(
                    sampled_span_a_unexplained, sampled_span_a_parent
                )
                or 0.0,
                "dominant_terminal_first_half_span_a_child": sampled_row.get(
                    "dominant_terminal_first_half_span_a_child", dominant_span_a_child
                ),
                "terminal_first_half_span_a0_unexplained_share": optional_ratio(
                    sampled_span_a0_unexplained, sampled_span_a0_parent
                )
                or 0.0,
                "dominant_terminal_first_half_span_a0_child": sampled_row.get(
                    "dominant_terminal_first_half_span_a0_child", dominant_span_a0_child
                ),
                "terminal_first_half_span_a0_gap_before_a00_share": optional_ratio(
                    sampled_span_a0_gap_before_a00, sampled_span_a0_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_between_a00_a01_share": optional_ratio(
                    sampled_span_a0_gap_between_a00_a01, sampled_span_a0_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_after_a01_share": optional_ratio(
                    sampled_span_a0_gap_after_a01, sampled_span_a0_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_parent_seconds": sampled_gap_before_a00_parent,
                "terminal_first_half_span_a0_gap_before_a00_unexplained_share": optional_ratio(
                    sampled_gap_before_a00_unexplained, sampled_gap_before_a00_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_span_0_share": optional_ratio(
                    sampled_gap_before_a00_span_0, sampled_gap_before_a00_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_span_1_share": optional_ratio(
                    sampled_gap_before_a00_span_1, sampled_gap_before_a00_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_share": optional_ratio(
                    sampled_gap_before_a00_span_0_unexplained, sampled_gap_before_a00_span_0_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_unexplained,
                    sampled_gap_before_a00_span_0_alt_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_left_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_left,
                    sampled_gap_before_a00_span_0_alt_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right,
                    sampled_gap_before_a00_span_0_alt_parent,
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_share": optional_ratio(
                    sampled_gap_before_a00_span_0_child_0, sampled_gap_before_a00_span_0_parent
                )
                or 0.0,
                "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_share": optional_ratio(
                    sampled_gap_before_a00_span_0_child_1, sampled_gap_before_a00_span_0_parent
                )
                or 0.0,
                "dominant_terminal_first_half_span_a0_gap_before_a00_child": sampled_row.get(
                    "dominant_terminal_first_half_span_a0_gap_before_a00_child",
                    dominant_gap_before_a00_child,
                ),
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child": sampled_row.get(
                    "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child",
                    dominant_gap_before_a00_span_0_child,
                ),
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child": sampled_row.get(
                    "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child",
                    dominant_gap_before_a00_span_0_alt_child,
                ),
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child": dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_child_for_row(
                    sampled_row
                ),
                "gap_before_a00_coverage_share": optional_ratio(
                    sampled_gap_before_a00_covered_sampled_event_count,
                    sampled_gap_before_a00_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_unclassified_share": optional_ratio(
                    sampled_gap_before_a00_unclassified_sampled_event_count,
                    sampled_gap_before_a00_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_multi_child_share": optional_ratio(
                    sampled_gap_before_a00_multi_child_sampled_event_count,
                    sampled_gap_before_a00_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_sampled_count_closure_status": gap_before_a00_sampled_count_closure_status_for_row(
                    sampled_row
                ),
                "gap_before_a00_span_0_coverage_share": optional_ratio(
                    sampled_gap_before_a00_span_0_covered_sampled_event_count,
                    sampled_gap_before_a00_span_0_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_unclassified_share": optional_ratio(
                    sampled_gap_before_a00_span_0_unclassified_sampled_event_count,
                    sampled_gap_before_a00_span_0_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_multi_child_share": optional_ratio(
                    sampled_gap_before_a00_span_0_multi_child_sampled_event_count,
                    sampled_gap_before_a00_span_0_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_coverage_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_covered_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_unclassified_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_unclassified_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_multi_child_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_multi_child_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_coverage_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_covered_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_right_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_unclassified_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_right_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_multi_child_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_right_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_repart_coverage_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_right_repart_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_repart_unclassified_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_right_repart_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_repart_multi_child_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count,
                    sampled_gap_before_a00_span_0_alt_right_repart_sampled_event_count,
                )
                or 0.0,
                "gap_before_a00_span_0_sampled_count_closure_status": gap_before_a00_span_0_sampled_count_closure_status_for_row(
                    sampled_row
                ),
                "gap_before_a00_span_0_alt_sampled_count_closure_status": gap_before_a00_span_0_alt_sampled_count_closure_status_for_row(
                    sampled_row
                ),
                "gap_before_a00_span_0_alt_right_sampled_count_closure_status": gap_before_a00_span_0_alt_right_sampled_count_closure_status_for_row(
                    sampled_row
                ),
                "gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status": gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status_for_row(
                    sampled_row
                ),
                "gap_before_a00_span_0_case_weighted_dominant_child": gap_before_a00_span_0_case_weighted_dominant_child,
                "gap_before_a00_span_0_seconds_weighted_dominant_child": gap_before_a00_span_0_seconds_weighted_dominant_child,
                "gap_before_a00_span_0_event_weighted_dominant_child": gap_before_a00_span_0_event_weighted_dominant_child,
                "gap_before_a00_span_0_dominance_status": gap_before_a00_span_0_dominance_status,
                "gap_before_a00_span_0_alt_case_weighted_dominant_child": gap_before_a00_span_0_alt_case_weighted_dominant_child,
                "gap_before_a00_span_0_alt_seconds_weighted_dominant_child": gap_before_a00_span_0_alt_seconds_weighted_dominant_child,
                "gap_before_a00_span_0_alt_event_weighted_dominant_child": gap_before_a00_span_0_alt_event_weighted_dominant_child,
                "gap_before_a00_span_0_alt_dominance_status": gap_before_a00_span_0_alt_dominance_status,
                "gap_before_a00_span_0_alt_case_majority_share": gap_before_a00_span_0_alt_case_majority_share,
                "gap_before_a00_span_0_alt_child_margin_share": gap_before_a00_span_0_alt_child_margin_share,
                "gap_before_a00_span_0_alt_right_case_weighted_dominant_child": gap_before_a00_span_0_alt_right_case_weighted_dominant_child,
                "gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child": gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child,
                "gap_before_a00_span_0_alt_right_event_weighted_dominant_child": gap_before_a00_span_0_alt_right_event_weighted_dominant_child,
                "gap_before_a00_span_0_alt_right_dominance_status": gap_before_a00_span_0_alt_right_dominance_status,
                "gap_before_a00_span_0_alt_right_case_majority_share": gap_before_a00_span_0_alt_right_case_majority_share,
                "gap_before_a00_span_0_alt_right_child_margin_share": gap_before_a00_span_0_alt_right_child_margin_share,
                "gap_before_a00_span_0_alt_right_repartition_attempt_count": gap_before_a00_span_0_alt_right_repartition_attempt_count,
                "gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count": gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count,
                "gap_before_a00_span_0_alt_right_subtree_status": gap_before_a00_span_0_alt_right_subtree_status,
                "gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child": gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child,
                "gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child": gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child,
                "gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child": gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child,
                "gap_before_a00_span_0_alt_right_repart_dominance_status": gap_before_a00_span_0_alt_right_repart_dominance_status,
                "gap_before_a00_span_0_alt_right_repart_case_majority_share": gap_before_a00_span_0_alt_right_repart_case_majority_share,
                "gap_before_a00_span_0_alt_right_repart_child_margin_share": gap_before_a00_span_0_alt_right_repart_child_margin_share,
                "gap_before_a00_span_0_alt_right_child_0_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_child_0,
                    sampled_gap_before_a00_span_0_alt_right_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_child_1_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_child_1,
                    sampled_gap_before_a00_span_0_alt_right_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_unexplained_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_unexplained,
                    sampled_gap_before_a00_span_0_alt_right_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_repart_left_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_repart_left,
                    sampled_gap_before_a00_span_0_alt_right_repart_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_repart_right_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_repart_right,
                    sampled_gap_before_a00_span_0_alt_right_repart_parent,
                )
                or 0.0,
                "gap_before_a00_span_0_alt_right_repart_unexplained_share": optional_ratio(
                    sampled_gap_before_a00_span_0_alt_right_repart_unexplained,
                    sampled_gap_before_a00_span_0_alt_right_repart_parent,
                )
                or 0.0,
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child": dominant_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_for_row(
                    sampled_row
                ),
                "span_a0_coverage_share": optional_ratio(
                    sampled_span_a0_covered_sampled_event_count,
                    sampled_span_a0_sampled_event_count,
                )
                or 0.0,
                "span_a0_unclassified_share": optional_ratio(
                    sampled_span_a0_unclassified_sampled_event_count,
                    sampled_span_a0_sampled_event_count,
                )
                or 0.0,
                "span_a0_multi_child_share": optional_ratio(
                    sampled_span_a0_multi_child_sampled_event_count,
                    sampled_span_a0_sampled_event_count,
                )
                or 0.0,
                "sampled_count_closure_status": sampled_count_closure_status_for_row(sampled_row),
                "recommended_next_action": recommended_next_action,
            }
        )

    summary = {
        "decision_status": "ready",
        "analysis_mode": "low_overhead",
        "benchmark_scope": scope,
        "benchmark_identity_basis": basis,
        "candidate_index_materiality_status": materiality_status,
        "materiality_status_all_modes_match": materiality_status_all_modes_match,
        "materiality_source": "per_mode_lifecycle_summary",
        "profile_mode_overhead_status": overhead_status,
        "sampled_count_closure_status": sampled_count_closure_status,
        "gap_before_a00_sampled_count_closure_status": gap_before_a00_sampled_count_closure_status,
        "gap_before_a00_span_0_sampled_count_closure_status": gap_before_a00_span_0_sampled_count_closure_status,
        "gap_before_a00_span_0_dominance_status": gap_before_a00_span_0_dominance_status,
        "gap_before_a00_span_0_alt_sampled_count_closure_status": gap_before_a00_span_0_alt_sampled_count_closure_status,
        "gap_before_a00_span_0_alt_dominance_status": gap_before_a00_span_0_alt_dominance_status,
        "gap_before_a00_span_0_alt_right_sampled_count_closure_status": gap_before_a00_span_0_alt_right_sampled_count_closure_status,
        "gap_before_a00_span_0_alt_right_dominance_status": gap_before_a00_span_0_alt_right_dominance_status,
        "gap_before_a00_span_0_alt_right_repartition_attempt_count": gap_before_a00_span_0_alt_right_repartition_attempt_count,
        "gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count": gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count,
        "gap_before_a00_span_0_alt_right_subtree_status": gap_before_a00_span_0_alt_right_subtree_status,
        "gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status": gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status,
        "gap_before_a00_span_0_alt_right_repart_dominance_status": gap_before_a00_span_0_alt_right_repart_dominance_status,
        "trusted_span_timing": trusted_span_timing,
        "trusted_span_source": trusted_span_source,
        "runtime_prototype_allowed": False,
        "recommended_next_action": recommended_next_action,
        "workload_id": workload_id,
        "case_count": len(case_rows),
        "candidate_index_seconds_ratio_count_only_vs_coarse": count_only_ratio,
        "candidate_index_seconds_ratio_sampled_vs_terminal": sampled_vs_terminal_ratio,
        "candidate_index_seconds_ratio_sampled_vs_coarse": sampled_vs_coarse_ratio,
        "terminal_parent_seconds_ratio_sampled_vs_terminal": sampled_terminal_parent_ratio,
        "timer_call_count_ratio_count_only_vs_coarse": timer_count_only_ratio,
        "timer_call_count_ratio_sampled_vs_terminal": timer_sampled_ratio,
        "terminal_first_half_unexplained_share": terminal_first_half_unexplained_share,
        "terminal_first_half_span_a_unexplained_share": span_a_unexplained_share,
        "terminal_first_half_span_a0_unexplained_share": span_a0_unexplained_share,
        "terminal_first_half_span_a0_gap_before_a00_parent_seconds": gap_before_a00_parent_seconds,
        "terminal_first_half_span_a0_gap_before_a00_share": span_a0_gap_before_a00_share,
        "terminal_first_half_span_a0_gap_before_a00_unexplained_share": gap_before_a00_unexplained_share,
        "terminal_first_half_span_a0_gap_before_a00_span_0_share": gap_before_a00_span_0_share,
        "terminal_first_half_span_a0_gap_before_a00_span_1_share": gap_before_a00_span_1_share,
        "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_share": gap_before_a00_span_0_unexplained_share,
        "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_share": gap_before_a00_span_0_alt_unexplained_share,
        "terminal_first_half_span_a0_gap_before_a00_span_0_child_0_share": gap_before_a00_span_0_child_0_share,
        "terminal_first_half_span_a0_gap_before_a00_span_0_child_1_share": gap_before_a00_span_0_child_1_share,
        "terminal_first_half_span_a0_gap_between_a00_a01_share": span_a0_gap_between_a00_a01_share,
        "terminal_first_half_span_a0_gap_after_a01_share": span_a0_gap_after_a01_share,
        "gap_before_a00_sampled_event_count": gap_before_a00_sampled_event_count,
        "gap_before_a00_covered_sampled_event_count": gap_before_a00_covered_sampled_event_count,
        "gap_before_a00_unclassified_sampled_event_count": gap_before_a00_unclassified_sampled_event_count,
        "gap_before_a00_multi_child_sampled_event_count": gap_before_a00_multi_child_sampled_event_count,
        "gap_before_a00_coverage_share": gap_before_a00_coverage_share,
        "gap_before_a00_unclassified_share": gap_before_a00_unclassified_share,
        "gap_before_a00_multi_child_share": gap_before_a00_multi_child_share,
        "gap_before_a00_span_0_sampled_event_count": gap_before_a00_span_0_sampled_event_count,
        "gap_before_a00_span_0_covered_sampled_event_count": gap_before_a00_span_0_covered_sampled_event_count,
        "gap_before_a00_span_0_unclassified_sampled_event_count": gap_before_a00_span_0_unclassified_sampled_event_count,
        "gap_before_a00_span_0_multi_child_sampled_event_count": gap_before_a00_span_0_multi_child_sampled_event_count,
        "gap_before_a00_span_0_coverage_share": gap_before_a00_span_0_coverage_share,
        "gap_before_a00_span_0_unclassified_share": gap_before_a00_span_0_unclassified_share,
        "gap_before_a00_span_0_multi_child_share": gap_before_a00_span_0_multi_child_share,
        "gap_before_a00_span_0_alt_sampled_event_count": gap_before_a00_span_0_alt_sampled_event_count,
        "gap_before_a00_span_0_alt_covered_sampled_event_count": gap_before_a00_span_0_alt_covered_sampled_event_count,
        "gap_before_a00_span_0_alt_unclassified_sampled_event_count": gap_before_a00_span_0_alt_unclassified_sampled_event_count,
        "gap_before_a00_span_0_alt_multi_child_sampled_event_count": gap_before_a00_span_0_alt_multi_child_sampled_event_count,
        "gap_before_a00_span_0_alt_coverage_share": gap_before_a00_span_0_alt_coverage_share,
        "gap_before_a00_span_0_alt_unclassified_share": gap_before_a00_span_0_alt_unclassified_share,
        "gap_before_a00_span_0_alt_multi_child_share": gap_before_a00_span_0_alt_multi_child_share,
        "gap_before_a00_span_0_alt_right_coverage_share": gap_before_a00_span_0_alt_right_coverage_share,
        "gap_before_a00_span_0_alt_right_unclassified_share": gap_before_a00_span_0_alt_right_unclassified_share,
        "gap_before_a00_span_0_alt_right_multi_child_share": gap_before_a00_span_0_alt_right_multi_child_share,
        "gap_before_a00_span_0_alt_right_repart_parent_seconds": gap_before_a00_span_0_alt_right_repart_parent_seconds,
        "gap_before_a00_span_0_alt_right_repart_left_seconds": gap_before_a00_span_0_alt_right_repart_left_seconds,
        "gap_before_a00_span_0_alt_right_repart_right_seconds": gap_before_a00_span_0_alt_right_repart_right_seconds,
        "gap_before_a00_span_0_alt_right_repart_left_share": optional_ratio(
            gap_before_a00_span_0_alt_right_repart_left_seconds,
            gap_before_a00_span_0_alt_right_repart_parent_seconds,
        )
        or 0.0,
        "gap_before_a00_span_0_alt_right_repart_right_share": optional_ratio(
            gap_before_a00_span_0_alt_right_repart_right_seconds,
            gap_before_a00_span_0_alt_right_repart_parent_seconds,
        )
        or 0.0,
        "gap_before_a00_span_0_alt_right_repart_unexplained_share": gap_before_a00_span_0_alt_right_repart_unexplained_share,
        "gap_before_a00_span_0_alt_right_repart_coverage_share": gap_before_a00_span_0_alt_right_repart_coverage_share,
        "gap_before_a00_span_0_alt_right_repart_unclassified_share": gap_before_a00_span_0_alt_right_repart_unclassified_share,
        "gap_before_a00_span_0_alt_right_repart_multi_child_share": gap_before_a00_span_0_alt_right_repart_multi_child_share,
        "gap_before_a00_span_0_child_0_seconds": gap_before_a00_span_0_child_0_seconds,
        "gap_before_a00_span_0_child_1_seconds": gap_before_a00_span_0_child_1_seconds,
        "gap_before_a00_span_0_child_margin_seconds": gap_before_a00_span_0_child_margin_seconds,
        "gap_before_a00_span_0_child_margin_share": gap_before_a00_span_0_child_margin_share,
        "gap_before_a00_span_0_alt_left_seconds": gap_before_a00_span_0_alt_left_seconds,
        "gap_before_a00_span_0_alt_right_seconds": gap_before_a00_span_0_alt_right_seconds,
        "gap_before_a00_span_0_alt_left_share": gap_before_a00_span_0_alt_left_share,
        "gap_before_a00_span_0_alt_right_share": gap_before_a00_span_0_alt_right_share,
        "gap_before_a00_span_0_alt_child_margin_seconds": gap_before_a00_span_0_alt_child_margin_seconds,
        "gap_before_a00_span_0_alt_child_margin_share": gap_before_a00_span_0_alt_child_margin_share,
        "gap_before_a00_span_0_case_weighted_child_0_count": gap_before_a00_span_0_case_dominance["child_0_count"],
        "gap_before_a00_span_0_case_weighted_child_1_count": gap_before_a00_span_0_case_dominance["child_1_count"],
        "gap_before_a00_span_0_case_majority_share": gap_before_a00_span_0_case_majority_share,
        "gap_before_a00_span_0_case_weighted_dominant_child": gap_before_a00_span_0_case_weighted_dominant_child,
        "gap_before_a00_span_0_seconds_weighted_dominant_child": gap_before_a00_span_0_seconds_weighted_dominant_child,
        "gap_before_a00_span_0_event_weighted_dominant_child": gap_before_a00_span_0_event_weighted_dominant_child,
        "gap_before_a00_span_0_alt_case_weighted_child_0_count": gap_before_a00_span_0_alt_case_dominance["alt_left_count"],
        "gap_before_a00_span_0_alt_case_weighted_child_1_count": gap_before_a00_span_0_alt_case_dominance["alt_right_count"],
        "gap_before_a00_span_0_alt_case_majority_share": gap_before_a00_span_0_alt_case_majority_share,
        "gap_before_a00_span_0_alt_case_weighted_dominant_child": gap_before_a00_span_0_alt_case_weighted_dominant_child,
        "gap_before_a00_span_0_alt_seconds_weighted_dominant_child": gap_before_a00_span_0_alt_seconds_weighted_dominant_child,
        "gap_before_a00_span_0_alt_event_weighted_dominant_child": gap_before_a00_span_0_alt_event_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_case_weighted_child_0_count": gap_before_a00_span_0_alt_right_case_dominance["child_0_count"],
        "gap_before_a00_span_0_alt_right_case_weighted_child_1_count": gap_before_a00_span_0_alt_right_case_dominance["child_1_count"],
        "gap_before_a00_span_0_alt_right_case_majority_share": gap_before_a00_span_0_alt_right_case_majority_share,
        "gap_before_a00_span_0_alt_right_case_weighted_dominant_child": gap_before_a00_span_0_alt_right_case_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child": gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_event_weighted_dominant_child": gap_before_a00_span_0_alt_right_event_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_child_0_seconds": gap_before_a00_span_0_alt_right_child_0_seconds,
        "gap_before_a00_span_0_alt_right_child_1_seconds": gap_before_a00_span_0_alt_right_child_1_seconds,
        "gap_before_a00_span_0_alt_right_child_margin_seconds": gap_before_a00_span_0_alt_right_child_margin_seconds,
        "gap_before_a00_span_0_alt_right_child_margin_share": gap_before_a00_span_0_alt_right_child_margin_share,
        "gap_before_a00_span_0_alt_right_repart_case_weighted_repart_left_count": gap_before_a00_span_0_alt_right_repart_case_dominance["repart_left_count"],
        "gap_before_a00_span_0_alt_right_repart_case_weighted_repart_right_count": gap_before_a00_span_0_alt_right_repart_case_dominance["repart_right_count"],
        "gap_before_a00_span_0_alt_right_repart_case_majority_share": gap_before_a00_span_0_alt_right_repart_case_majority_share,
        "gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child": gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child": gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child": gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child,
        "gap_before_a00_span_0_alt_right_repart_child_margin_seconds": gap_before_a00_span_0_alt_right_repart_child_margin_seconds,
        "gap_before_a00_span_0_alt_right_repart_child_margin_share": gap_before_a00_span_0_alt_right_repart_child_margin_share,
        "span_a0_sampled_event_count": span_a0_sampled_event_count,
        "span_a0_covered_sampled_event_count": span_a0_covered_sampled_event_count,
        "span_a0_unclassified_sampled_event_count": span_a0_unclassified_sampled_event_count,
        "span_a0_multi_child_sampled_event_count": span_a0_multi_child_sampled_event_count,
        "span_a0_coverage_share": span_a0_coverage_share,
        "span_a0_unclassified_share": span_a0_unclassified_share,
        "span_a0_multi_child_share": span_a0_multi_child_share,
        "span_a0_split_available": span_a0_split_available,
        "gap_before_a00_split_available": gap_before_a00_split_available,
        "gap_before_a00_span_0_split_available": gap_before_a00_span_0_split_available,
        "gap_before_a00_span_0_alt_split_available": gap_before_a00_span_0_alt_split_available,
        "gap_before_a00_span_0_alt_right_split_available": gap_before_a00_span_0_alt_right_split_available,
        "gap_before_a00_span_0_alt_right_repart_split_available": gap_before_a00_span_0_alt_right_repart_split_available,
        "dominant_terminal_first_half_span": dominant_span,
        "dominant_terminal_first_half_span_a_child": dominant_span_a_child,
        "dominant_terminal_first_half_span_a0_child": dominant_span_a0_child,
        "dominant_terminal_first_half_span_a0_gap_before_a00_child": dominant_gap_before_a00_child,
        "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child": dominant_gap_before_a00_span_0_child,
        "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child": dominant_gap_before_a00_span_0_alt_child,
        "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child": dominant_gap_before_a00_span_0_alt_right_child,
        "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child": dominant_gap_before_a00_span_0_alt_right_repart_child,
        "profile_sample_log2": profile_sample_log2,
        "profile_sample_rate": profile_sample_rate,
        "cases": case_rows,
    }
    return summary


def build_summary(args):
    loaded = load_artifact_set(args)
    if loaded["mode"] == "legacy_lexical":
        return build_legacy_summary(loaded)
    return build_low_overhead_summary(loaded)


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cases_tsv = output_dir / "profile_mode_ab_cases.tsv"
    summary_json = output_dir / "profile_mode_ab_summary.json"
    decision_json = output_dir / "profile_mode_ab_decision.json"
    summary_md = output_dir / "profile_mode_ab_summary.md"

    try:
        summary = build_summary(args)
        decision = {
            "decision_status": summary["decision_status"],
            "analysis_mode": summary.get("analysis_mode", "unknown"),
            "benchmark_scope": summary.get("benchmark_scope", "unknown"),
            "benchmark_identity_basis": summary.get("benchmark_identity_basis", "unknown"),
            "candidate_index_materiality_status": summary.get(
                "candidate_index_materiality_status", "unknown"
            ),
            "materiality_status_all_modes_match": summary.get(
                "materiality_status_all_modes_match", False
            ),
            "profile_mode_overhead_status": summary["profile_mode_overhead_status"],
            "sampled_count_closure_status": summary.get("sampled_count_closure_status", "unknown"),
            "gap_before_a00_sampled_count_closure_status": summary.get(
                "gap_before_a00_sampled_count_closure_status", "unknown"
            ),
            "gap_before_a00_span_0_sampled_count_closure_status": summary.get(
                "gap_before_a00_span_0_sampled_count_closure_status", "unknown"
            ),
            "gap_before_a00_span_0_dominance_status": summary.get(
                "gap_before_a00_span_0_dominance_status", "unknown"
            ),
            "gap_before_a00_span_0_alt_sampled_count_closure_status": summary.get(
                "gap_before_a00_span_0_alt_sampled_count_closure_status", "unknown"
            ),
            "gap_before_a00_span_0_alt_dominance_status": summary.get(
                "gap_before_a00_span_0_alt_dominance_status", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_sampled_count_closure_status": summary.get(
                "gap_before_a00_span_0_alt_right_sampled_count_closure_status", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_dominance_status": summary.get(
                "gap_before_a00_span_0_alt_right_dominance_status", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_repartition_attempt_count": summary.get(
                "gap_before_a00_span_0_alt_right_repartition_attempt_count", 0
            ),
            "gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count": summary.get(
                "gap_before_a00_span_0_alt_right_consecutive_near_tie_repartition_count",
                0,
            ),
            "gap_before_a00_span_0_alt_right_subtree_status": summary.get(
                "gap_before_a00_span_0_alt_right_subtree_status", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status": summary.get(
                "gap_before_a00_span_0_alt_right_repart_sampled_count_closure_status",
                "unknown",
            ),
            "gap_before_a00_span_0_alt_right_repart_dominance_status": summary.get(
                "gap_before_a00_span_0_alt_right_repart_dominance_status", "unknown"
            ),
            "trusted_span_timing": summary.get("trusted_span_timing", False),
            "trusted_span_source": summary.get("trusted_span_source", "none"),
            "runtime_prototype_allowed": False,
            "recommended_next_action": summary["recommended_next_action"],
            "dominant_terminal_first_half_span": summary.get(
                "dominant_terminal_first_half_span", "unknown"
            ),
            "dominant_terminal_first_half_span_a_child": summary.get(
                "dominant_terminal_first_half_span_a_child", "unknown"
            ),
            "dominant_terminal_first_half_span_a0_child": summary.get(
                "dominant_terminal_first_half_span_a0_child", "unknown"
            ),
            "dominant_terminal_first_half_span_a0_gap_before_a00_child": summary.get(
                "dominant_terminal_first_half_span_a0_gap_before_a00_child", "unknown"
            ),
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child": summary.get(
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_child", "unknown"
            ),
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child": summary.get(
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child",
                "unknown",
            ),
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child": summary.get(
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child",
                "unknown",
            ),
            "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child": summary.get(
                "dominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child",
                "unknown",
            ),
            "gap_before_a00_span_0_case_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_case_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_seconds_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_seconds_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_event_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_event_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_case_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_case_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_seconds_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_seconds_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_event_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_event_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_case_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_right_case_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_right_seconds_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_event_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_right_event_weighted_dominant_child", "unknown"
            ),
            "gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_right_repart_case_weighted_dominant_child",
                "unknown",
            ),
            "gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_right_repart_seconds_weighted_dominant_child",
                "unknown",
            ),
            "gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child": summary.get(
                "gap_before_a00_span_0_alt_right_repart_event_weighted_dominant_child",
                "unknown",
            ),
            "terminal_first_half_unexplained_share": summary.get(
                "terminal_first_half_unexplained_share", 0.0
            ),
            "terminal_first_half_span_a_unexplained_share": summary.get(
                "terminal_first_half_span_a_unexplained_share", 0.0
            ),
            "terminal_first_half_span_a0_unexplained_share": summary.get(
                "terminal_first_half_span_a0_unexplained_share", 0.0
            ),
            "terminal_first_half_span_a0_gap_before_a00_unexplained_share": summary.get(
                "terminal_first_half_span_a0_gap_before_a00_unexplained_share", 0.0
            ),
            "gap_before_a00_coverage_share": summary.get("gap_before_a00_coverage_share", 0.0),
            "gap_before_a00_unclassified_share": summary.get(
                "gap_before_a00_unclassified_share", 0.0
            ),
            "gap_before_a00_multi_child_share": summary.get(
                "gap_before_a00_multi_child_share", 0.0
            ),
            "gap_before_a00_span_0_coverage_share": summary.get(
                "gap_before_a00_span_0_coverage_share", 0.0
            ),
            "gap_before_a00_span_0_unclassified_share": summary.get(
                "gap_before_a00_span_0_unclassified_share", 0.0
            ),
            "gap_before_a00_span_0_multi_child_share": summary.get(
                "gap_before_a00_span_0_multi_child_share", 0.0
            ),
            "gap_before_a00_span_0_alt_coverage_share": summary.get(
                "gap_before_a00_span_0_alt_coverage_share", 0.0
            ),
            "gap_before_a00_span_0_alt_unclassified_share": summary.get(
                "gap_before_a00_span_0_alt_unclassified_share", 0.0
            ),
            "gap_before_a00_span_0_alt_multi_child_share": summary.get(
                "gap_before_a00_span_0_alt_multi_child_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_coverage_share": summary.get(
                "gap_before_a00_span_0_alt_right_coverage_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_unclassified_share": summary.get(
                "gap_before_a00_span_0_alt_right_unclassified_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_multi_child_share": summary.get(
                "gap_before_a00_span_0_alt_right_multi_child_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_coverage_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_coverage_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_unclassified_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_unclassified_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_multi_child_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_multi_child_share", 0.0
            ),
            "gap_before_a00_span_0_child_margin_share": summary.get(
                "gap_before_a00_span_0_child_margin_share", 0.0
            ),
            "gap_before_a00_span_0_case_majority_share": summary.get(
                "gap_before_a00_span_0_case_majority_share", 0.0
            ),
            "gap_before_a00_span_0_alt_child_margin_share": summary.get(
                "gap_before_a00_span_0_alt_child_margin_share", 0.0
            ),
            "gap_before_a00_span_0_alt_case_majority_share": summary.get(
                "gap_before_a00_span_0_alt_case_majority_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_child_margin_share": summary.get(
                "gap_before_a00_span_0_alt_right_child_margin_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_case_majority_share": summary.get(
                "gap_before_a00_span_0_alt_right_case_majority_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_left_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_left_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_right_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_right_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_child_margin_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_child_margin_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_repart_case_majority_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_case_majority_share", 0.0
            ),
            "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_share": summary.get(
                "terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_share", 0.0
            ),
            "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_share": summary.get(
                "terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_share",
                0.0,
            ),
            "gap_before_a00_span_0_alt_right_repart_unexplained_share": summary.get(
                "gap_before_a00_span_0_alt_right_repart_unexplained_share", 0.0
            ),
            "gap_before_a00_span_0_alt_left_share": summary.get(
                "gap_before_a00_span_0_alt_left_share", 0.0
            ),
            "gap_before_a00_span_0_alt_right_share": summary.get(
                "gap_before_a00_span_0_alt_right_share", 0.0
            ),
            "span_a0_coverage_share": summary.get("span_a0_coverage_share", 0.0),
            "span_a0_unclassified_share": summary.get("span_a0_unclassified_share", 0.0),
            "span_a0_multi_child_share": summary.get("span_a0_multi_child_share", 0.0),
            "workload_id": summary.get("workload_id", "unknown"),
            "case_count": summary.get("case_count", 0),
        }
    except AbInputError as exc:
        summary = {
            "decision_status": "not_ready",
            "analysis_mode": "unknown",
            "benchmark_scope": "unknown",
            "benchmark_identity_basis": "unknown",
            "profile_mode_overhead_status": "unknown",
            "sampled_count_closure_status": "unknown",
            "trusted_span_timing": False,
            "trusted_span_source": "none",
            "runtime_prototype_allowed": False,
            "recommended_next_action": "fix_profile_mode_ab_inputs",
            "errors": [str(exc)],
            "cases": [],
        }
        decision = {
            "decision_status": "not_ready",
            "analysis_mode": "unknown",
            "benchmark_scope": "unknown",
            "benchmark_identity_basis": "unknown",
            "profile_mode_overhead_status": "unknown",
            "sampled_count_closure_status": "unknown",
            "trusted_span_timing": False,
            "trusted_span_source": "none",
            "runtime_prototype_allowed": False,
            "recommended_next_action": "fix_profile_mode_ab_inputs",
            "blocking_reasons": [str(exc)],
        }

    fieldnames = list(summary["cases"][0].keys()) if summary.get("cases") else ["case_id"]
    write_rows(cases_tsv, fieldnames, summary.get("cases", []))
    write_summary_markdown(summary_md, summary)
    summary["cases_tsv"] = str(cases_tsv)
    summary["summary_markdown"] = str(summary_md)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision_json.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
