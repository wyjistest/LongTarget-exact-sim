#!/usr/bin/env python3
import argparse
import csv
import gzip
import json
import math
from array import array
from collections import Counter
from pathlib import Path

EXPECTED_SCHEMA_VERSION = 2

STOPPED_RUNTIME_PROTOTYPES = [
    "lazy_generation_index",
    "incoming_key_coalescing",
    "victim_slot_event_reorder",
    "full_set_miss_batch_collapse",
]

CASE_FIELDNAMES = [
    "audit_dir",
    "case_id",
    "decision_status",
    "schema_version",
    "locality_status",
    "exactness_hazard_status",
    "observed_full_set_miss_count",
    "mixed_hazard_mode",
    "floor_changed_count",
    "floor_unchanged_count",
    "floor_changed_share",
    "running_min_slot_changed_count",
    "running_min_slot_unchanged_count",
    "running_min_slot_changed_share",
    "running_min_delta_signed_min",
    "running_min_delta_signed_p50",
    "running_min_delta_signed_p90",
    "running_min_delta_signed_p99",
    "running_min_delta_abs_min",
    "running_min_delta_abs_p50",
    "running_min_delta_abs_p90",
    "running_min_delta_abs_p99",
    "same_running_min_slot_run_count",
    "same_running_min_slot_run_mean",
    "same_running_min_slot_run_p50",
    "same_running_min_slot_run_p90",
    "same_running_min_slot_run_p99",
    "incoming_key_reuse_before_eviction_share",
    "victim_key_reappears_after_eviction_count",
    "victim_key_reappears_after_eviction_share",
    "victim_key_reappear_event_distance_p50",
    "victim_key_reappear_event_distance_p90",
    "victim_key_reappear_event_distance_p99",
    "victim_key_reappears_before_next_full_set_miss_floor_change_share",
    "victim_key_reappears_after_next_full_set_miss_floor_change_share",
    "victim_key_reappears_without_future_full_set_miss_floor_change_share",
    "floor_churn_blocker",
    "victim_reappear_blocker",
    "key_reuse_blocker",
    "floor_churn_dominant",
    "victim_reappear_dominant",
    "key_reuse_dominant",
    "candidate_runtime_prototypes",
    "recommended_next_action",
]


class AuditInputError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-schema-version", type=int, default=EXPECTED_SCHEMA_VERSION)
    parser.add_argument("--floor-blocker-threshold", type=float, default=0.50)
    parser.add_argument("--floor-dominant-threshold", type=float, default=0.75)
    parser.add_argument("--victim-reappear-blocker-threshold", type=float, default=0.50)
    parser.add_argument("--victim-reappear-dominant-threshold", type=float, default=0.50)
    parser.add_argument("--key-reuse-blocker-threshold", type=float, default=0.05)
    parser.add_argument("--key-reuse-dominant-threshold", type=float, default=0.10)
    return parser.parse_args()


def share(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditInputError(f"{path}: invalid json: {exc}") from exc


def parse_bool(value):
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise AuditInputError(f"invalid boolean value {value!r}")


def open_timeline(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def timeline_path_for_audit(audit_dir: Path):
    candidates = [
        audit_dir / "victim_slot_timeline.tsv.gz",
        audit_dir / "victim_slot_timeline.tsv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise AuditInputError(f"{audit_dir}: missing victim_slot_timeline.tsv(.gz)")


def quantile(values, probability):
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * probability) - 1))
    return int(ordered[index])


def weighted_quantile(pairs, probability):
    weighted = [(int(value), int(weight)) for value, weight in pairs if int(weight) > 0]
    if not weighted:
        return 0
    weighted.sort(key=lambda item: item[0])
    total_weight = sum(weight for _, weight in weighted)
    threshold = max(1, math.ceil(total_weight * probability))
    cumulative_weight = 0
    for value, weight in weighted:
        cumulative_weight += weight
        if cumulative_weight >= threshold:
            return value
    return weighted[-1][0]


def average(values):
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def format_row(row):
    formatted = {}
    for key, value in row.items():
        if isinstance(value, bool):
            formatted[key] = "true" if value else "false"
        elif isinstance(value, float):
            formatted[key] = f"{value:.6f}"
        elif isinstance(value, list):
            formatted[key] = ",".join(value)
        else:
            formatted[key] = value
    return formatted


def write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def classify_mode(floor_blocker, victim_blocker, key_blocker):
    if floor_blocker and victim_blocker and key_blocker:
        return "all_blockers"
    if floor_blocker and victim_blocker:
        return "floor_and_victim_reappear"
    if floor_blocker and key_blocker:
        return "floor_and_key_reuse"
    if victim_blocker and key_blocker:
        return "victim_reappear_and_key_reuse"
    if floor_blocker:
        return "floor_only"
    if victim_blocker:
        return "victim_reappear_only"
    if key_blocker:
        return "key_reuse_only"
    return "none"


def candidate_runtime_prototypes(floor_blocker, victim_blocker):
    candidates = []
    if floor_blocker:
        candidates.append("stable_min_maintenance")
    if victim_blocker:
        candidates.append("eager_index_erase_handle")
    return candidates


def recommended_next_action(
    floor_dominant,
    victim_dominant,
    key_dominant,
    floor_blocker,
    victim_blocker,
    key_blocker,
):
    if floor_dominant or floor_blocker:
        return "profile_floor_min_maintenance"
    if victim_dominant or victim_blocker:
        return "profile_candidate_index_lifecycle"
    if key_dominant or key_blocker:
        return "inspect_key_reuse"
    return "no_actionable_mixed_hazard"


def analyze_timeline(path: Path, expected_case_id: str):
    floor_change_ordinals = array("Q")
    floor_deltas_signed = array("q")
    floor_deltas_abs = array("Q")
    run_lengths = array("Q")

    observed_full_set_miss_count = 0
    floor_changed_count = 0
    running_min_slot_changed_count = 0
    last_running_min_slot_after = None
    current_run_length = 0

    with open_timeline(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            row_case_id = row.get("case_id")
            if row_case_id and row_case_id != expected_case_id:
                raise AuditInputError(
                    f"{path}: row case_id={row_case_id!r} != expected {expected_case_id!r}"
                )

            event_ordinal = int(row["event_ordinal"])
            running_min_before = int(row["running_min_before"])
            running_min_after = int(row["running_min_after"])
            running_min_slot_before = int(row["running_min_slot_before"])
            running_min_slot_after = int(row["running_min_slot_after"])

            floor_changed = parse_bool(row["floor_changed"]) or (
                running_min_before != running_min_after
            )
            running_min_slot_changed = parse_bool(row["min_slot_changed"]) or (
                running_min_slot_before != running_min_slot_after
            )

            observed_full_set_miss_count += 1
            if floor_changed:
                floor_changed_count += 1
                floor_change_ordinals.append(event_ordinal)
                floor_delta = running_min_after - running_min_before
                floor_deltas_signed.append(floor_delta)
                floor_deltas_abs.append(abs(floor_delta))
            if running_min_slot_changed:
                running_min_slot_changed_count += 1

            if last_running_min_slot_after is None or running_min_slot_after != last_running_min_slot_after:
                if current_run_length > 0:
                    run_lengths.append(current_run_length)
                current_run_length = 1
                last_running_min_slot_after = running_min_slot_after
            else:
                current_run_length += 1

    if current_run_length > 0:
        run_lengths.append(current_run_length)

    victim_reappear_distances = array("Q")
    victim_key_reappears_after_eviction_count = 0
    victim_key_reappears_before_next_full_set_miss_floor_change_count = 0
    victim_key_reappears_after_next_full_set_miss_floor_change_count = 0
    victim_key_reappears_without_future_full_set_miss_floor_change_count = 0
    next_floor_index = 0

    with open_timeline(path) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            event_ordinal = int(row["event_ordinal"])
            while next_floor_index < len(floor_change_ordinals) and floor_change_ordinals[next_floor_index] <= event_ordinal:
                next_floor_index += 1

            victim_distance = int(row["victim_key_next_seen_distance"])
            if victim_distance < 0:
                continue

            victim_key_reappears_after_eviction_count += 1
            victim_reappear_distances.append(victim_distance)

            if next_floor_index >= len(floor_change_ordinals):
                victim_key_reappears_after_next_full_set_miss_floor_change_count += 1
                victim_key_reappears_without_future_full_set_miss_floor_change_count += 1
                continue

            next_floor_change_distance = int(floor_change_ordinals[next_floor_index] - event_ordinal)
            if victim_distance < next_floor_change_distance:
                victim_key_reappears_before_next_full_set_miss_floor_change_count += 1
            else:
                victim_key_reappears_after_next_full_set_miss_floor_change_count += 1

    return {
        "observed_full_set_miss_count": observed_full_set_miss_count,
        "floor_changed_count": floor_changed_count,
        "floor_unchanged_count": observed_full_set_miss_count - floor_changed_count,
        "floor_changed_share": share(floor_changed_count, observed_full_set_miss_count),
        "running_min_slot_changed_count": running_min_slot_changed_count,
        "running_min_slot_unchanged_count": observed_full_set_miss_count - running_min_slot_changed_count,
        "running_min_slot_changed_share": share(
            running_min_slot_changed_count,
            observed_full_set_miss_count,
        ),
        "running_min_delta_signed_min": int(min(floor_deltas_signed)) if floor_deltas_signed else 0,
        "running_min_delta_signed_p50": quantile(floor_deltas_signed, 0.50),
        "running_min_delta_signed_p90": quantile(floor_deltas_signed, 0.90),
        "running_min_delta_signed_p99": quantile(floor_deltas_signed, 0.99),
        "running_min_delta_abs_min": int(min(floor_deltas_abs)) if floor_deltas_abs else 0,
        "running_min_delta_abs_p50": quantile(floor_deltas_abs, 0.50),
        "running_min_delta_abs_p90": quantile(floor_deltas_abs, 0.90),
        "running_min_delta_abs_p99": quantile(floor_deltas_abs, 0.99),
        "same_running_min_slot_run_count": len(run_lengths),
        "same_running_min_slot_run_mean": average(run_lengths),
        "same_running_min_slot_run_p50": quantile(run_lengths, 0.50),
        "same_running_min_slot_run_p90": quantile(run_lengths, 0.90),
        "same_running_min_slot_run_p99": quantile(run_lengths, 0.99),
        "victim_key_reappears_after_eviction_count": victim_key_reappears_after_eviction_count,
        "victim_key_reappears_after_eviction_share": share(
            victim_key_reappears_after_eviction_count,
            observed_full_set_miss_count,
        ),
        "victim_key_reappear_event_distance_p50": quantile(victim_reappear_distances, 0.50),
        "victim_key_reappear_event_distance_p90": quantile(victim_reappear_distances, 0.90),
        "victim_key_reappear_event_distance_p99": quantile(victim_reappear_distances, 0.99),
        "victim_key_reappears_before_next_full_set_miss_floor_change_share": share(
            victim_key_reappears_before_next_full_set_miss_floor_change_count,
            victim_key_reappears_after_eviction_count,
        ),
        "victim_key_reappears_after_next_full_set_miss_floor_change_share": share(
            victim_key_reappears_after_next_full_set_miss_floor_change_count,
            victim_key_reappears_after_eviction_count,
        ),
        "victim_key_reappears_without_future_full_set_miss_floor_change_share": share(
            victim_key_reappears_without_future_full_set_miss_floor_change_count,
            victim_key_reappears_after_eviction_count,
        ),
    }


def analyze_audit_dir(audit_dir: Path, args):
    summary_path = audit_dir / "summary.json"
    decision_path = audit_dir / "decision.json"
    hazard_path = audit_dir / "hazard_summary.json"
    missing = [str(path.name) for path in [summary_path, decision_path, hazard_path] if not path.exists()]
    if missing:
        raise AuditInputError(f"{audit_dir}: missing required files: {', '.join(missing)}")

    summary = load_json(summary_path)
    decision = load_json(decision_path)
    hazard = load_json(hazard_path)

    decision_status = decision.get("decision_status", summary.get("decision_status", "unknown"))
    if summary.get("decision_status") != decision_status:
        raise AuditInputError(f"{audit_dir}: summary/decision status mismatch")
    if decision_status != "ready":
        raise AuditInputError(f"{audit_dir}: decision_status={decision_status}")

    schema_version = int(summary.get("schema_version", args.expected_schema_version))
    if schema_version != args.expected_schema_version:
        raise AuditInputError(
            f"{audit_dir}: schema_version={schema_version}, expected {args.expected_schema_version}"
        )

    cases = hazard.get("cases")
    if not isinstance(cases, list) or len(cases) != 1:
        raise AuditInputError(f"{audit_dir}: expected exactly one case in hazard_summary.json")
    case = cases[0]
    case_id = case.get("case_id")
    if not case_id:
        raise AuditInputError(f"{audit_dir}: missing case_id")

    case_metrics = case.get("metrics", {})
    aggregate_metrics = summary.get("aggregate_metrics", {})
    incoming_key_reuse_before_eviction_share = float(
        case_metrics.get(
            "incoming_key_reuse_before_eviction_share",
            aggregate_metrics.get("incoming_key_reuse_before_eviction_share", 0.0),
        )
    )

    timeline_metrics = analyze_timeline(timeline_path_for_audit(audit_dir), case_id)
    observed_full_set_miss_count = int(case.get("observed_full_set_miss_count", 0))
    if observed_full_set_miss_count and observed_full_set_miss_count != timeline_metrics["observed_full_set_miss_count"]:
        raise AuditInputError(
            f"{audit_dir}: timeline full-set miss count {timeline_metrics['observed_full_set_miss_count']} "
            f"!= hazard_summary observed_full_set_miss_count {observed_full_set_miss_count}"
        )

    floor_blocker = timeline_metrics["floor_changed_share"] >= args.floor_blocker_threshold
    victim_blocker = (
        timeline_metrics["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_blocker_threshold
    )
    key_blocker = incoming_key_reuse_before_eviction_share >= args.key_reuse_blocker_threshold

    floor_dominant = timeline_metrics["floor_changed_share"] >= args.floor_dominant_threshold
    victim_dominant = (
        timeline_metrics["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_dominant_threshold
    )
    key_dominant = incoming_key_reuse_before_eviction_share >= args.key_reuse_dominant_threshold

    mixed_hazard_mode = classify_mode(floor_blocker, victim_blocker, key_blocker)
    candidates = candidate_runtime_prototypes(floor_blocker, victim_blocker)
    next_action = recommended_next_action(
        floor_dominant,
        victim_dominant,
        key_dominant,
        floor_blocker,
        victim_blocker,
        key_blocker,
    )

    return {
        "audit_dir": str(audit_dir),
        "case_id": case_id,
        "decision_status": decision_status,
        "schema_version": schema_version,
        "locality_status": case.get("locality_status", summary.get("locality_status", "unknown")),
        "exactness_hazard_status": case.get(
            "exactness_hazard_status",
            summary.get("exactness_hazard_status", "unknown"),
        ),
        "observed_full_set_miss_count": timeline_metrics["observed_full_set_miss_count"],
        "mixed_hazard_mode": mixed_hazard_mode,
        **timeline_metrics,
        "incoming_key_reuse_before_eviction_share": incoming_key_reuse_before_eviction_share,
        "floor_churn_blocker": floor_blocker,
        "victim_reappear_blocker": victim_blocker,
        "key_reuse_blocker": key_blocker,
        "floor_churn_dominant": floor_dominant,
        "victim_reappear_dominant": victim_dominant,
        "key_reuse_dominant": key_dominant,
        "candidate_runtime_prototypes": candidates,
        "recommended_next_action": next_action,
    }


def compute_case_weighted(rows):
    return {
        "mixed_hazard_mode_counts": dict(Counter(row["mixed_hazard_mode"] for row in rows)),
        "recommended_next_action_counts": dict(
            Counter(row["recommended_next_action"] for row in rows)
        ),
    }


def compute_event_weighted(rows):
    total = sum(int(row["observed_full_set_miss_count"]) for row in rows)

    def event_sum(predicate):
        return sum(
            int(row["observed_full_set_miss_count"])
            for row in rows
            if predicate(row)
        )

    reappear_count = sum(int(row["victim_key_reappears_after_eviction_count"]) for row in rows)

    return {
        "full_set_miss_count": total,
        "floor_changed_share": share(
            sum(int(row["floor_changed_count"]) for row in rows),
            total,
        ),
        "running_min_slot_changed_share": share(
            sum(int(row["running_min_slot_changed_count"]) for row in rows),
            total,
        ),
        "incoming_key_reuse_before_eviction_share": share(
            sum(
                float(row["incoming_key_reuse_before_eviction_share"])
                * int(row["observed_full_set_miss_count"])
                for row in rows
            ),
            total,
        ),
        "victim_key_reappears_after_eviction_share": share(
            sum(int(row["victim_key_reappears_after_eviction_count"]) for row in rows),
            total,
        ),
        "running_min_delta_signed_min": min(
            int(row["running_min_delta_signed_min"])
            for row in rows
        ) if rows else 0,
        "running_min_delta_signed_p50": weighted_quantile(
            [
                (
                    int(row["running_min_delta_signed_p50"]),
                    int(row["observed_full_set_miss_count"]),
                )
                for row in rows
            ],
            0.50,
        ),
        "running_min_delta_signed_p90": weighted_quantile(
            [
                (
                    int(row["running_min_delta_signed_p90"]),
                    int(row["observed_full_set_miss_count"]),
                )
                for row in rows
            ],
            0.90,
        ),
        "running_min_delta_signed_p99": weighted_quantile(
            [
                (
                    int(row["running_min_delta_signed_p99"]),
                    int(row["observed_full_set_miss_count"]),
                )
                for row in rows
            ],
            0.99,
        ),
        "running_min_delta_abs_min": min(
            int(row["running_min_delta_abs_min"])
            for row in rows
        ) if rows else 0,
        "running_min_delta_abs_p50": weighted_quantile(
            [
                (
                    int(row["running_min_delta_abs_p50"]),
                    int(row["observed_full_set_miss_count"]),
                )
                for row in rows
            ],
            0.50,
        ),
        "running_min_delta_abs_p90": weighted_quantile(
            [
                (
                    int(row["running_min_delta_abs_p90"]),
                    int(row["observed_full_set_miss_count"]),
                )
                for row in rows
            ],
            0.90,
        ),
        "running_min_delta_abs_p99": weighted_quantile(
            [
                (
                    int(row["running_min_delta_abs_p99"]),
                    int(row["observed_full_set_miss_count"]),
                )
                for row in rows
            ],
            0.99,
        ),
        "victim_key_reappears_before_next_full_set_miss_floor_change_share": share(
            sum(
                float(row["victim_key_reappears_before_next_full_set_miss_floor_change_share"])
                * int(row["victim_key_reappears_after_eviction_count"])
                for row in rows
            ),
            reappear_count,
        ),
        "victim_key_reappears_after_next_full_set_miss_floor_change_share": share(
            sum(
                float(row["victim_key_reappears_after_next_full_set_miss_floor_change_share"])
                * int(row["victim_key_reappears_after_eviction_count"])
                for row in rows
            ),
            reappear_count,
        ),
        "victim_key_reappears_without_future_full_set_miss_floor_change_share": share(
            sum(
                float(row["victim_key_reappears_without_future_full_set_miss_floor_change_share"])
                * int(row["victim_key_reappears_after_eviction_count"])
                for row in rows
            ),
            reappear_count,
        ),
        "floor_churn_dominant_event_share": share(
            event_sum(lambda row: row["floor_churn_dominant"]),
            total,
        ),
        "victim_reappear_dominant_event_share": share(
            event_sum(lambda row: row["victim_reappear_dominant"]),
            total,
        ),
        "key_reuse_dominant_event_share": share(
            event_sum(lambda row: row["key_reuse_dominant"]),
            total,
        ),
    }


def dominant_blockers(event_weighted, args):
    blockers = []
    if event_weighted["floor_changed_share"] >= args.floor_dominant_threshold:
        blockers.append("floor_churn")
    if (
        event_weighted["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_dominant_threshold
    ):
        blockers.append("victim_key_reappears_after_eviction")
    if (
        event_weighted["incoming_key_reuse_before_eviction_share"]
        >= args.key_reuse_dominant_threshold
    ):
        blockers.append("key_reuse")
    return blockers


def aggregate_mode(event_weighted, args):
    floor_blocker = event_weighted["floor_changed_share"] >= args.floor_blocker_threshold
    victim_blocker = (
        event_weighted["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_blocker_threshold
    )
    key_blocker = (
        event_weighted["incoming_key_reuse_before_eviction_share"]
        >= args.key_reuse_blocker_threshold
    )
    return classify_mode(floor_blocker, victim_blocker, key_blocker)


def aggregate_candidates(event_weighted, args):
    return candidate_runtime_prototypes(
        event_weighted["floor_changed_share"] >= args.floor_blocker_threshold,
        event_weighted["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_blocker_threshold,
    )


def aggregate_next_action(event_weighted, args):
    return recommended_next_action(
        event_weighted["floor_changed_share"] >= args.floor_dominant_threshold,
        event_weighted["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_dominant_threshold,
        event_weighted["incoming_key_reuse_before_eviction_share"]
        >= args.key_reuse_dominant_threshold,
        event_weighted["floor_changed_share"] >= args.floor_blocker_threshold,
        event_weighted["victim_key_reappears_after_eviction_share"]
        >= args.victim_reappear_blocker_threshold,
        event_weighted["incoming_key_reuse_before_eviction_share"]
        >= args.key_reuse_blocker_threshold,
    )


def write_summary_markdown(path: Path, summary, errors):
    lines = [
        "# SIM Initial Host Merge Mixed Hazard Modes",
        "",
        f"- decision_status: `{summary['decision_status']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- ready_case_count: `{summary['ready_case_count']}`",
        f"- schema_version_all: `{summary['schema_version_all']}`",
        "",
    ]

    if errors:
        lines.extend(["## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    if summary["aggregate"]:
        aggregate = summary["aggregate"]
        lines.extend(
            [
                "## Aggregate",
                "",
                f"- mixed_hazard_mode: `{aggregate['mixed_hazard_mode']}`",
                f"- recommended_next_action: `{aggregate['recommended_next_action']}`",
                f"- candidate_runtime_prototypes: `{', '.join(aggregate['candidate_runtime_prototypes'])}`",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
            ]
        )
        for key in sorted(aggregate["event_weighted"]):
            value = aggregate["event_weighted"][key]
            if isinstance(value, float):
                lines.append(f"| {key} | {value:.6f} |")
            else:
                lines.append(f"| {key} | {value} |")
        lines.append("")

    if summary["cases"]:
        lines.extend(
            [
                "## Cases",
                "",
                "| case_id | miss_count | mixed_hazard_mode | floor_changed_share | victim_reappear_share | key_reuse_share | next_action |",
                "| --- | ---: | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in sorted(
            summary["cases"],
            key=lambda item: (-int(item["observed_full_set_miss_count"]), item["case_id"]),
        ):
            lines.append(
                "| {case_id} | {miss_count} | {mode} | {floor:.6f} | {victim:.6f} | {reuse:.6f} | {action} |".format(
                    case_id=row["case_id"],
                    miss_count=row["observed_full_set_miss_count"],
                    mode=row["mixed_hazard_mode"],
                    floor=float(row["floor_changed_share"]),
                    victim=float(row["victim_key_reappears_after_eviction_share"]),
                    reuse=float(row["incoming_key_reuse_before_eviction_share"]),
                    action=row["recommended_next_action"],
                )
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    audit_dirs = [Path(path) for path in args.audit_dir]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "modes_tsv": output_dir / "mixed_hazard_modes.tsv",
        "summary_json": output_dir / "mixed_hazard_summary.json",
        "decision_json": output_dir / "mixed_hazard_decision.json",
        "summary_markdown": output_dir / "mixed_hazard_summary.md",
    }

    rows = []
    errors = []
    ready_case_count = 0

    for audit_dir in audit_dirs:
        try:
            row = analyze_audit_dir(audit_dir, args)
        except AuditInputError as exc:
            errors.append(str(exc))
            continue
        rows.append(row)
        ready_case_count += 1

    write_rows(
        output_paths["modes_tsv"],
        CASE_FIELDNAMES,
        [format_row(row) for row in rows],
    )

    if errors or ready_case_count != len(audit_dirs):
        summary = {
            "decision_status": "not_ready",
            "case_count": len(audit_dirs),
            "ready_case_count": ready_case_count,
            "schema_version_all": None,
            "aggregate": {},
            "cases": rows,
            "errors": errors if errors else ["one or more cases were not ready"],
            "mixed_hazard_modes_tsv": str(output_paths["modes_tsv"]),
            "mixed_hazard_decision_json": str(output_paths["decision_json"]),
            "mixed_hazard_summary_markdown": str(output_paths["summary_markdown"]),
        }
        decision = {
            "decision_status": "not_ready",
            "case_count": len(audit_dirs),
            "ready_case_count": ready_case_count,
            "schema_version_all": None,
            "full_set_miss_count": sum(int(row["observed_full_set_miss_count"]) for row in rows),
            "mixed_hazard_mode": "unknown",
            "dominant_blockers": [],
            "stopped_runtime_prototypes": STOPPED_RUNTIME_PROTOTYPES,
            "candidate_runtime_prototypes": [],
            "recommended_next_action": "fix_audit_inputs",
            "blocking_reasons": summary["errors"],
        }
    else:
        case_weighted = compute_case_weighted(rows)
        event_weighted = compute_event_weighted(rows)
        mixed_mode = aggregate_mode(event_weighted, args)
        blockers = dominant_blockers(event_weighted, args)
        candidates = aggregate_candidates(event_weighted, args)
        next_action = aggregate_next_action(event_weighted, args)

        aggregate = {
            "mixed_hazard_mode": mixed_mode,
            "dominant_blockers": blockers,
            "candidate_runtime_prototypes": candidates,
            "recommended_next_action": next_action,
            **event_weighted,
            "case_weighted": case_weighted,
            "event_weighted": event_weighted,
        }
        summary = {
            "decision_status": "ready",
            "case_count": len(audit_dirs),
            "ready_case_count": ready_case_count,
            "schema_version_all": args.expected_schema_version,
            "aggregate": aggregate,
            "cases": rows,
            "errors": [],
            "mixed_hazard_modes_tsv": str(output_paths["modes_tsv"]),
            "mixed_hazard_decision_json": str(output_paths["decision_json"]),
            "mixed_hazard_summary_markdown": str(output_paths["summary_markdown"]),
        }
        decision = {
            "decision_status": "ready",
            "case_count": len(audit_dirs),
            "ready_case_count": ready_case_count,
            "schema_version_all": args.expected_schema_version,
            "full_set_miss_count": event_weighted["full_set_miss_count"],
            "mixed_hazard_mode": mixed_mode,
            "dominant_blockers": blockers,
            "stopped_runtime_prototypes": STOPPED_RUNTIME_PROTOTYPES,
            "candidate_runtime_prototypes": candidates,
            "recommended_next_action": next_action,
            "case_weighted": case_weighted,
            "event_weighted": event_weighted,
        }

    write_summary_markdown(output_paths["summary_markdown"], summary, summary["errors"])
    output_paths["summary_json"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_paths["decision_json"].write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
