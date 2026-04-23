#!/usr/bin/env python3
import argparse
import csv
import json
import math
import struct
from array import array
from collections import Counter
from pathlib import Path

HEADER_STRUCT = struct.Struct("<8sIIQQ")
EVENT_STRUCT = struct.Struct("<i4xQIIIIQQiiiiiiii")
EXPECTED_MAGIC = b"LTHMSSE1"
EXPECTED_VERSION = 1
EXPECTED_SCHEMA_VERSION = 2
EXPECTED_PATH_KIND = "steady_state_full_set_miss_trace"
FULL_SET_MISS = 2

DEFAULT_TRACE_ROOT = ".tmp/steady_state_bench_2026-04-17_rkgd02"
DEFAULT_WINDOW_SIZE = 1000
REVERSE_CHUNK_RECORDS = 65536

BLOCKED_RUNTIME_PROTOTYPES = [
    "incoming_key_coalescing",
    "unordered_key_summary",
    "event_reorder_by_slot",
]

PER_CASE_FIELDNAMES = [
    "case_id",
    "logical_event_count",
    "post_fill_event_count",
    "meta_post_fill_full_set_miss_count",
    "observed_full_set_miss_count",
    "meta_count_match",
    "slot_write_after_write_count",
    "slot_write_after_write_share",
    "slot_write_after_write_without_intervening_observation_count",
    "slot_write_after_write_without_intervening_observation_share",
    "incoming_key_reuse_before_eviction_count",
    "incoming_key_reuse_before_eviction_share",
    "victim_key_reappears_after_eviction_count",
    "victim_key_reappears_after_eviction_share",
    "floor_change_count",
    "floor_change_per_full_set_miss",
    "min_slot_change_count",
    "min_slot_change_per_full_set_miss",
    "victim_slot_top1_share",
    "victim_slot_top5_share",
    "victim_slot_top10_share",
    "victim_slot_unique_per_1k_mean",
    "incoming_key_unique_per_1k_mean",
    "victim_slot_signal",
    "incoming_key_signal",
    "locality_status",
    "locality_reason",
    "exactness_hazard_status",
    "exactness_hazard_reason",
    "recommended_runtime_prototype",
]

TIMELINE_FIELDNAMES = [
    "case_id",
    "event_ordinal",
    "summary_ordinal",
    "victim_slot",
    "observed_candidate_index_before",
    "victim_key_before",
    "incoming_key",
    "incoming_score",
    "victim_score_before",
    "running_min_before",
    "running_min_after",
    "running_min_slot_before",
    "running_min_slot_after",
    "floor_changed",
    "min_slot_changed",
    "incoming_key_next_seen_distance",
    "victim_key_next_seen_distance",
]

CONTINUOUS_FIELDS = [
    "slot_write_after_write_share",
    "slot_write_after_write_without_intervening_observation_share",
    "incoming_key_reuse_before_eviction_share",
    "victim_key_reappears_after_eviction_share",
    "floor_change_per_full_set_miss",
    "min_slot_change_per_full_set_miss",
    "victim_slot_top1_share",
    "victim_slot_top5_share",
    "victim_slot_top10_share",
    "victim_slot_unique_per_1k_mean",
    "incoming_key_unique_per_1k_mean",
]


class TraceInputError(Exception):
    pass


class NeedsSchemaV2Error(Exception):
    pass


class WindowUniqueTracker:
    def __init__(self, window_size: int):
        self.window_size = window_size
        self._values = set()
        self._count = 0
        self.window_unique_counts = []

    def add(self, value: int):
        self._values.add(value)
        self._count += 1
        if self._count >= self.window_size:
            self.window_unique_counts.append(len(self._values))
            self._values.clear()
            self._count = 0

    def finalize(self):
        if self._count > 0:
            self.window_unique_counts.append(len(self._values))
            self._values.clear()
            self._count = 0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", default=DEFAULT_TRACE_ROOT)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE)
    args = parser.parse_args()
    if args.window_size <= 0:
        raise SystemExit("--window-size must be > 0")
    return args


def share(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def average(values):
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def topk_share(counter, k, total):
    if total <= 0 or not counter:
        return 0.0
    counts = sorted(counter.values(), reverse=True)
    return float(sum(counts[:k])) / float(total)


def format_row(row):
    formatted = {}
    for key, value in row.items():
        if isinstance(value, bool):
            formatted[key] = "true" if value else "false"
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


def init_timeline_writer(path: Path):
    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=TIMELINE_FIELDNAMES, delimiter="\t")
    writer.writeheader()
    return handle, writer


def load_meta_json(case_dir: Path):
    meta_path = case_dir / "meta.json"
    if not meta_path.exists():
        raise TraceInputError(f"{case_dir.name}: missing meta.json")
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TraceInputError(f"{case_dir.name}: invalid meta.json: {exc}") from exc


def validate_meta_shape(meta, case_id):
    required_fields = [
        "schema_version",
        "path_kind",
        "logical_event_count",
        "post_fill_event_count",
        "post_fill_full_set_miss_count",
    ]
    for field in required_fields:
        if field not in meta:
            raise TraceInputError(f"{case_id}: missing meta field {field}")
    if meta["path_kind"] != EXPECTED_PATH_KIND:
        raise TraceInputError(f"{case_id}: unexpected path_kind {meta['path_kind']!r}")


def preflight_trace_root(case_dirs):
    meta_by_case = {}
    schema_errors = []
    validation_errors = []
    for case_dir in case_dirs:
        try:
            meta = load_meta_json(case_dir)
            validate_meta_shape(meta, case_dir.name)
        except TraceInputError as exc:
            validation_errors.append(str(exc))
            continue

        schema_version = meta.get("schema_version")
        if schema_version != EXPECTED_SCHEMA_VERSION:
            schema_errors.append(
                f"{case_dir.name}: steady-state trace schema_version={schema_version}, expected {EXPECTED_SCHEMA_VERSION}"
            )
            continue
        meta_by_case[case_dir.name] = meta

    if schema_errors:
        raise NeedsSchemaV2Error("\n".join(schema_errors))
    if validation_errors:
        raise TraceInputError("\n".join(validation_errors))
    return meta_by_case


def read_binary_header(handle, case_id):
    header_bytes = handle.read(HEADER_STRUCT.size)
    if len(header_bytes) != HEADER_STRUCT.size:
        raise TraceInputError(f"{case_id}: truncated header")
    magic, version, reserved, record_count, record_size = HEADER_STRUCT.unpack(header_bytes)
    if magic != EXPECTED_MAGIC:
        raise TraceInputError(f"{case_id}: unexpected magic {magic!r}")
    if version != EXPECTED_VERSION:
        raise TraceInputError(f"{case_id}: unexpected version {version}")
    if record_size != EVENT_STRUCT.size:
        raise TraceInputError(
            f"{case_id}: unexpected record size {record_size}, expected {EVENT_STRUCT.size}"
        )
    return record_count, record_size


def classify_locality(metrics):
    victim_strong_hits = 0
    if metrics["slot_write_after_write_share"] >= 0.30:
        victim_strong_hits += 1
    if metrics["slot_write_after_write_without_intervening_observation_share"] >= 0.20:
        victim_strong_hits += 1
    if metrics["victim_slot_top5_share"] >= 0.50:
        victim_strong_hits += 1
    if metrics["victim_slot_unique_per_1k_mean"] <= 20.0:
        victim_strong_hits += 1
    victim_slot_signal = "strong" if victim_strong_hits >= 2 else "weak"

    key_weak = (
        metrics["incoming_key_reuse_before_eviction_share"] <= 0.05
        and metrics["victim_key_reappears_after_eviction_share"] <= 0.05
    )
    incoming_key_signal = "weak" if key_weak else "mixed"

    if victim_slot_signal == "strong" and incoming_key_signal == "weak":
        locality_status = "victim_strong_key_weak"
    elif victim_slot_signal == "strong":
        locality_status = "victim_strong_key_mixed"
    else:
        locality_status = "no_actionable_locality"

    return (
        victim_slot_signal,
        incoming_key_signal,
        locality_status,
        f"victim_slot_signal={victim_slot_signal}, incoming_key_signal={incoming_key_signal}",
    )


def classify_exactness_hazard(metrics):
    floor_hazard = (
        metrics["floor_change_per_full_set_miss"] >= 0.20
        or metrics["min_slot_change_per_full_set_miss"] >= 0.20
    )
    key_hazard = (
        metrics["incoming_key_reuse_before_eviction_share"] >= 0.10
        or metrics["victim_key_reappears_after_eviction_share"] >= 0.10
    )

    if floor_hazard and key_hazard:
        return "mixed", "floor_change/key_reuse both elevated"
    if floor_hazard:
        return "floor_churn", "running floor or min-slot changes frequently"
    if key_hazard:
        return "key_reuse", "incoming/victim keys reappear before the path stabilizes"
    return "low", "no strong floor churn or key reuse hazard detected"


def recommend_runtime_prototype(locality_status, exactness_hazard_status):
    if locality_status == "victim_strong_key_weak" and exactness_hazard_status == "low":
        return "lazy_generation_index"
    return "none"


def iter_reverse_records(handle, record_count, record_size):
    remaining = record_count
    while remaining > 0:
        chunk_records = min(REVERSE_CHUNK_RECORDS, remaining)
        chunk_start_record = remaining - chunk_records
        handle.seek(HEADER_STRUCT.size + chunk_start_record * record_size)
        chunk = handle.read(chunk_records * record_size)
        for reverse_offset in range(chunk_records - 1, -1, -1):
            offset = reverse_offset * record_size
            yield chunk_start_record + reverse_offset, EVENT_STRUCT.unpack_from(chunk, offset)
        remaining = chunk_start_record


def analyze_case(case_dir: Path, meta, window_size: int, timeline_writer):
    case_id = case_dir.name
    events_path = case_dir / "events.bin"
    if not events_path.exists():
        raise TraceInputError(f"{case_id}: missing events.bin")

    victim_slot_counts = Counter()
    incoming_windows = WindowUniqueTracker(window_size)
    victim_windows = WindowUniqueTracker(window_size)

    last_write_event_by_slot = {}
    last_observed_event_by_slot = {}
    inflight_key_by_slot = {}
    inflight_observed_by_slot = {}

    event_ordinals = array("Q")
    summary_ordinals = array("Q")
    victim_slots = array("i")
    observed_slots = array("i")
    victim_keys = array("Q")
    incoming_keys = array("Q")
    incoming_scores = array("i")
    victim_scores = array("i")
    running_min_before = array("i")
    running_min_after = array("i")
    running_min_slot_before = array("i")
    running_min_slot_after = array("i")

    slot_write_after_write_count = 0
    slot_write_after_write_without_obs_count = 0
    incoming_key_reuse_before_eviction_count = 0
    incoming_key_reuse_evaluated_count = 0
    floor_change_count = 0
    min_slot_change_count = 0
    observed_full_set_miss_count = 0

    with events_path.open("rb") as handle:
        record_count, record_size = read_binary_header(handle, case_id)
        for event_ordinal in range(record_count):
            record_bytes = handle.read(record_size)
            if len(record_bytes) != record_size:
                raise TraceInputError(f"{case_id}: truncated record at {event_ordinal}")
            (
                score,
                start_coord,
                end_i,
                min_end_j,
                max_end_j,
                score_end_j,
                summary_ordinal,
                victim_start_coord_before,
                reference_event_kind,
                observed_candidate_index_before,
                victim_candidate_index_before,
                victim_score_before,
                event_running_min_before,
                event_running_min_after,
                event_running_min_slot_before,
                event_running_min_slot_after,
            ) = EVENT_STRUCT.unpack(record_bytes)

            if observed_candidate_index_before >= 0:
                last_observed_event_by_slot[observed_candidate_index_before] = event_ordinal
                inflight_key = inflight_key_by_slot.get(observed_candidate_index_before)
                if inflight_key is not None and inflight_key == start_coord:
                    inflight_observed_by_slot[observed_candidate_index_before] = True

            if reference_event_kind != FULL_SET_MISS:
                continue

            observed_full_set_miss_count += 1
            victim_slot = victim_candidate_index_before
            victim_slot_counts[victim_slot] += 1
            incoming_windows.add(start_coord)
            victim_windows.add(victim_slot)

            previous_write_event = last_write_event_by_slot.get(victim_slot)
            if previous_write_event is not None:
                slot_write_after_write_count += 1
                if last_observed_event_by_slot.get(victim_slot, -1) <= previous_write_event:
                    slot_write_after_write_without_obs_count += 1

            if victim_slot in inflight_key_by_slot:
                incoming_key_reuse_evaluated_count += 1
                if inflight_observed_by_slot.get(victim_slot, False):
                    incoming_key_reuse_before_eviction_count += 1

            inflight_key_by_slot[victim_slot] = start_coord
            inflight_observed_by_slot[victim_slot] = False
            last_write_event_by_slot[victim_slot] = event_ordinal
            last_observed_event_by_slot[victim_slot] = event_ordinal

            if event_running_min_before != event_running_min_after:
                floor_change_count += 1
            if event_running_min_slot_before != event_running_min_slot_after:
                min_slot_change_count += 1

            event_ordinals.append(event_ordinal)
            summary_ordinals.append(summary_ordinal)
            victim_slots.append(victim_slot)
            observed_slots.append(observed_candidate_index_before)
            victim_keys.append(victim_start_coord_before)
            incoming_keys.append(start_coord)
            incoming_scores.append(score)
            victim_scores.append(victim_score_before)
            running_min_before.append(event_running_min_before)
            running_min_after.append(event_running_min_after)
            running_min_slot_before.append(event_running_min_slot_before)
            running_min_slot_after.append(event_running_min_slot_after)

        trailing = handle.read(1)
        if trailing:
            raise TraceInputError(f"{case_id}: unexpected trailing bytes in events.bin")

    incoming_windows.finalize()
    victim_windows.finalize()

    for slot, was_observed in inflight_observed_by_slot.items():
        if slot not in inflight_key_by_slot:
            continue
        incoming_key_reuse_evaluated_count += 1
        if was_observed:
            incoming_key_reuse_before_eviction_count += 1

    meta_post_fill_full_set_miss_count = int(meta["post_fill_full_set_miss_count"])
    if observed_full_set_miss_count != meta_post_fill_full_set_miss_count:
        raise TraceInputError(
            f"{case_id}: observed_full_set_miss_count={observed_full_set_miss_count} "
            f"!= meta_post_fill_full_set_miss_count={meta_post_fill_full_set_miss_count}"
        )

    incoming_next_seen_distance = array("q", [-1] * observed_full_set_miss_count)
    victim_next_seen_distance = array("q", [-1] * observed_full_set_miss_count)
    victim_key_reappears_after_eviction_count = 0
    next_event_ordinal_by_key = {}
    reverse_full_miss_index = observed_full_set_miss_count - 1

    with events_path.open("rb") as handle:
        record_count, record_size = read_binary_header(handle, case_id)
        for event_ordinal, record in iter_reverse_records(handle, record_count, record_size):
            (
                score,
                start_coord,
                end_i,
                min_end_j,
                max_end_j,
                score_end_j,
                summary_ordinal,
                victim_start_coord_before,
                reference_event_kind,
                observed_candidate_index_before,
                victim_candidate_index_before,
                victim_score_before,
                event_running_min_before,
                event_running_min_after,
                event_running_min_slot_before,
                event_running_min_slot_after,
            ) = record

            next_seen = next_event_ordinal_by_key.get(start_coord)
            if reference_event_kind == FULL_SET_MISS:
                if reverse_full_miss_index < 0:
                    raise TraceInputError(f"{case_id}: reverse full-set miss underflow")
                if next_seen is not None:
                    incoming_next_seen_distance[reverse_full_miss_index] = next_seen - event_ordinal
                victim_next = next_event_ordinal_by_key.get(victim_start_coord_before)
                if victim_next is not None:
                    victim_next_seen_distance[reverse_full_miss_index] = victim_next - event_ordinal
                    victim_key_reappears_after_eviction_count += 1
                reverse_full_miss_index -= 1

            next_event_ordinal_by_key[start_coord] = event_ordinal

    if reverse_full_miss_index != -1:
        raise TraceInputError(f"{case_id}: reverse full-set miss count mismatch")

    metrics = {
        "slot_write_after_write_count": slot_write_after_write_count,
        "slot_write_after_write_share": share(
            slot_write_after_write_count,
            observed_full_set_miss_count,
        ),
        "slot_write_after_write_without_intervening_observation_count": slot_write_after_write_without_obs_count,
        "slot_write_after_write_without_intervening_observation_share": share(
            slot_write_after_write_without_obs_count,
            observed_full_set_miss_count,
        ),
        "incoming_key_reuse_before_eviction_count": incoming_key_reuse_before_eviction_count,
        "incoming_key_reuse_before_eviction_share": share(
            incoming_key_reuse_before_eviction_count,
            incoming_key_reuse_evaluated_count,
        ),
        "victim_key_reappears_after_eviction_count": victim_key_reappears_after_eviction_count,
        "victim_key_reappears_after_eviction_share": share(
            victim_key_reappears_after_eviction_count,
            observed_full_set_miss_count,
        ),
        "floor_change_count": floor_change_count,
        "floor_change_per_full_set_miss": share(floor_change_count, observed_full_set_miss_count),
        "min_slot_change_count": min_slot_change_count,
        "min_slot_change_per_full_set_miss": share(min_slot_change_count, observed_full_set_miss_count),
        "victim_slot_top1_share": topk_share(victim_slot_counts, 1, observed_full_set_miss_count),
        "victim_slot_top5_share": topk_share(victim_slot_counts, 5, observed_full_set_miss_count),
        "victim_slot_top10_share": topk_share(victim_slot_counts, 10, observed_full_set_miss_count),
        "victim_slot_unique_per_1k_mean": average(victim_windows.window_unique_counts),
        "incoming_key_unique_per_1k_mean": average(incoming_windows.window_unique_counts),
    }

    (
        victim_slot_signal,
        incoming_key_signal,
        locality_status,
        locality_reason,
    ) = classify_locality(metrics)
    exactness_hazard_status, exactness_hazard_reason = classify_exactness_hazard(metrics)
    recommended_runtime_prototype = recommend_runtime_prototype(
        locality_status,
        exactness_hazard_status,
    )

    row = {
        "case_id": case_id,
        "logical_event_count": int(meta["logical_event_count"]),
        "post_fill_event_count": int(meta["post_fill_event_count"]),
        "meta_post_fill_full_set_miss_count": meta_post_fill_full_set_miss_count,
        "observed_full_set_miss_count": observed_full_set_miss_count,
        "meta_count_match": True,
        **metrics,
        "victim_slot_signal": victim_slot_signal,
        "incoming_key_signal": incoming_key_signal,
        "locality_status": locality_status,
        "locality_reason": locality_reason,
        "exactness_hazard_status": exactness_hazard_status,
        "exactness_hazard_reason": exactness_hazard_reason,
        "recommended_runtime_prototype": recommended_runtime_prototype,
    }

    for index in range(observed_full_set_miss_count):
        timeline_writer.writerow(
            {
                "case_id": case_id,
                "event_ordinal": int(event_ordinals[index]),
                "summary_ordinal": int(summary_ordinals[index]),
                "victim_slot": int(victim_slots[index]),
                "observed_candidate_index_before": int(observed_slots[index]),
                "victim_key_before": int(victim_keys[index]),
                "incoming_key": int(incoming_keys[index]),
                "incoming_score": int(incoming_scores[index]),
                "victim_score_before": int(victim_scores[index]),
                "running_min_before": int(running_min_before[index]),
                "running_min_after": int(running_min_after[index]),
                "running_min_slot_before": int(running_min_slot_before[index]),
                "running_min_slot_after": int(running_min_slot_after[index]),
                "floor_changed": "true"
                if running_min_before[index] != running_min_after[index]
                else "false",
                "min_slot_changed": "true"
                if running_min_slot_before[index] != running_min_slot_after[index]
                else "false",
                "incoming_key_next_seen_distance": int(incoming_next_seen_distance[index]),
                "victim_key_next_seen_distance": int(victim_next_seen_distance[index]),
            }
        )

    hazard_case = {
        "case_id": case_id,
        "observed_full_set_miss_count": observed_full_set_miss_count,
        "locality_status": locality_status,
        "exactness_hazard_status": exactness_hazard_status,
        "recommended_runtime_prototype": recommended_runtime_prototype,
        "metrics": {key: row[key] for key in CONTINUOUS_FIELDS},
    }
    return row, hazard_case


def compute_aggregate(rows):
    total_full_set_miss_count = sum(int(row["observed_full_set_miss_count"]) for row in rows)
    aggregate_metrics = {}
    for field in CONTINUOUS_FIELDS:
        weighted_sum = 0.0
        for row in rows:
            weight = int(row["observed_full_set_miss_count"])
            weighted_sum += float(row[field]) * weight
        aggregate_metrics[field] = share(weighted_sum, total_full_set_miss_count)

    victim_slot_signal, incoming_key_signal, locality_status, locality_reason = classify_locality(
        aggregate_metrics
    )
    exactness_hazard_status, exactness_hazard_reason = classify_exactness_hazard(aggregate_metrics)
    recommended_runtime_prototype = recommend_runtime_prototype(
        locality_status,
        exactness_hazard_status,
    )

    case_count_by_locality = Counter(row["locality_status"] for row in rows)
    case_count_by_hazard = Counter(row["exactness_hazard_status"] for row in rows)

    return {
        "total_full_set_miss_count": total_full_set_miss_count,
        "aggregate_metrics": aggregate_metrics,
        "victim_slot_signal": victim_slot_signal,
        "incoming_key_signal": incoming_key_signal,
        "locality_status": locality_status,
        "locality_reason": locality_reason,
        "exactness_hazard_status": exactness_hazard_status,
        "exactness_hazard_reason": exactness_hazard_reason,
        "recommended_runtime_prototype": recommended_runtime_prototype,
        "case_count_by_locality": dict(case_count_by_locality),
        "case_count_by_hazard": dict(case_count_by_hazard),
    }


def write_summary_markdown(path: Path, summary, rows, errors):
    lines = [
        "# Steady-State Hazard Audit",
        "",
        f"- decision_status: `{summary['decision_status']}`",
        f"- locality_status: `{summary['locality_status']}`",
        f"- exactness_hazard_status: `{summary['exactness_hazard_status']}`",
        f"- recommended_runtime_prototype: `{summary['recommended_runtime_prototype']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- analyzed_case_count: `{summary['analyzed_case_count']}`",
        f"- total_full_set_miss_count: `{summary['total_full_set_miss_count']}`",
        "",
    ]

    if errors:
        lines.extend(["## Errors", ""])
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    if summary["aggregate_metrics"]:
        lines.extend(["## Aggregate Metrics", "", "| Metric | Value |", "| --- | ---: |"])
        for key in sorted(summary["aggregate_metrics"]):
            lines.append(f"| {key} | {summary['aggregate_metrics'][key]:.6f} |")
        lines.extend(
            [
                f"| victim_slot_signal | {summary['victim_slot_signal']} |",
                f"| incoming_key_signal | {summary['incoming_key_signal']} |",
                "",
            ]
        )

    if rows:
        lines.extend(
            [
                "## Per-Case Summary",
                "",
                "| case_id | miss_count | locality | hazard | reuse_share | floor_change | slot_waW_no_obs | runtime_prototype |",
                "| --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for row in sorted(rows, key=lambda item: (-int(item["observed_full_set_miss_count"]), item["case_id"])):
            lines.append(
                "| {case_id} | {miss_count} | {locality} | {hazard} | {reuse:.6f} | {floor:.6f} | {slot:.6f} | {runtime} |".format(
                    case_id=row["case_id"],
                    miss_count=row["observed_full_set_miss_count"],
                    locality=row["locality_status"],
                    hazard=row["exactness_hazard_status"],
                    reuse=float(row["incoming_key_reuse_before_eviction_share"]),
                    floor=float(row["floor_change_per_full_set_miss"]),
                    slot=float(
                        row["slot_write_after_write_without_intervening_observation_share"]
                    ),
                    runtime=row["recommended_runtime_prototype"],
                )
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_non_ready_summary(decision_status, trace_root, output_paths, case_count, errors):
    return {
        "decision_status": decision_status,
        "locality_status": "unknown",
        "exactness_hazard_status": "unknown",
        "recommended_runtime_prototype": "none",
        "trace_root": str(trace_root),
        "case_count": case_count,
        "analyzed_case_count": 0,
        "total_full_set_miss_count": 0,
        "victim_slot_signal": "unknown",
        "incoming_key_signal": "unknown",
        "aggregate_metrics": {},
        "per_case_tsv": str(output_paths["per_case_tsv"]),
        "victim_slot_timeline_tsv": str(output_paths["victim_slot_timeline_tsv"]),
        "hazard_summary_json": str(output_paths["hazard_summary_json"]),
        "decision_json": str(output_paths["decision_json"]),
        "summary_markdown": str(output_paths["summary_markdown"]),
        "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
        "errors": errors,
    }


def main():
    args = parse_args()
    trace_root = Path(args.trace_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "per_case_tsv": output_dir / "per_case.tsv",
        "summary_json": output_dir / "summary.json",
        "summary_markdown": output_dir / "summary.md",
        "victim_slot_timeline_tsv": output_dir / "victim_slot_timeline.tsv",
        "hazard_summary_json": output_dir / "hazard_summary.json",
        "decision_json": output_dir / "decision.json",
    }

    timeline_handle, timeline_writer = init_timeline_writer(output_paths["victim_slot_timeline_tsv"])
    try:
        case_dirs = []
        if trace_root.exists():
            case_dirs = sorted(
                path for path in trace_root.iterdir() if path.is_dir() and path.name.startswith("case-")
            )

        if not case_dirs:
            summary = make_non_ready_summary(
                "invalid_trace_input",
                trace_root,
                output_paths,
                0,
                [f"no case directories found under {trace_root}"],
            )
            hazard_summary = {"trace_root": str(trace_root), "aggregate": {}, "cases": [], "errors": summary["errors"]}
            decision = {
                "decision_status": summary["decision_status"],
                "locality_status": summary["locality_status"],
                "exactness_hazard_status": summary["exactness_hazard_status"],
                "recommended_runtime_prototype": summary["recommended_runtime_prototype"],
                "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
                "trace_root": str(trace_root),
                "errors": summary["errors"],
            }
        else:
            try:
                meta_by_case = preflight_trace_root(case_dirs)
            except NeedsSchemaV2Error as exc:
                errors = [line for line in str(exc).splitlines() if line]
                summary = make_non_ready_summary(
                    "needs_schema_v2",
                    trace_root,
                    output_paths,
                    len(case_dirs),
                    errors,
                )
                hazard_summary = {
                    "trace_root": str(trace_root),
                    "aggregate": {},
                    "cases": [],
                    "errors": errors,
                }
                decision = {
                    "decision_status": "needs_schema_v2",
                    "locality_status": "unknown",
                    "exactness_hazard_status": "unknown",
                    "recommended_runtime_prototype": "none",
                    "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
                    "trace_root": str(trace_root),
                    "errors": errors,
                }
            except TraceInputError as exc:
                errors = [line for line in str(exc).splitlines() if line]
                summary = make_non_ready_summary(
                    "invalid_trace_input",
                    trace_root,
                    output_paths,
                    len(case_dirs),
                    errors,
                )
                hazard_summary = {
                    "trace_root": str(trace_root),
                    "aggregate": {},
                    "cases": [],
                    "errors": errors,
                }
                decision = {
                    "decision_status": "invalid_trace_input",
                    "locality_status": "unknown",
                    "exactness_hazard_status": "unknown",
                    "recommended_runtime_prototype": "none",
                    "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
                    "trace_root": str(trace_root),
                    "errors": errors,
                }
            else:
                rows = []
                hazard_cases = []
                errors = []
                invalid_input = False
                for case_dir in case_dirs:
                    try:
                        row, hazard_case = analyze_case(
                            case_dir,
                            meta_by_case[case_dir.name],
                            args.window_size,
                            timeline_writer,
                        )
                    except Exception as exc:
                        invalid_input = True
                        errors.append(str(exc))
                        continue
                    rows.append(row)
                    hazard_cases.append(hazard_case)

                if invalid_input or not rows or len(rows) != len(case_dirs):
                    summary = make_non_ready_summary(
                        "invalid_trace_input",
                        trace_root,
                        output_paths,
                        len(case_dirs),
                        errors if errors else ["failed to analyze one or more cases"],
                    )
                    hazard_summary = {
                        "trace_root": str(trace_root),
                        "aggregate": {},
                        "cases": [],
                        "errors": summary["errors"],
                    }
                    decision = {
                        "decision_status": "invalid_trace_input",
                        "locality_status": "unknown",
                        "exactness_hazard_status": "unknown",
                        "recommended_runtime_prototype": "none",
                        "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
                        "trace_root": str(trace_root),
                        "errors": summary["errors"],
                    }
                    rows = []
                else:
                    aggregate = compute_aggregate(rows)
                    summary = {
                        "decision_status": "ready",
                        "locality_status": aggregate["locality_status"],
                        "exactness_hazard_status": aggregate["exactness_hazard_status"],
                        "recommended_runtime_prototype": aggregate["recommended_runtime_prototype"],
                        "trace_root": str(trace_root),
                        "case_count": len(case_dirs),
                        "analyzed_case_count": len(rows),
                        "total_full_set_miss_count": aggregate["total_full_set_miss_count"],
                        "victim_slot_signal": aggregate["victim_slot_signal"],
                        "incoming_key_signal": aggregate["incoming_key_signal"],
                        "aggregate_metrics": aggregate["aggregate_metrics"],
                        "case_count_by_locality": aggregate["case_count_by_locality"],
                        "case_count_by_hazard": aggregate["case_count_by_hazard"],
                        "per_case_tsv": str(output_paths["per_case_tsv"]),
                        "victim_slot_timeline_tsv": str(output_paths["victim_slot_timeline_tsv"]),
                        "hazard_summary_json": str(output_paths["hazard_summary_json"]),
                        "decision_json": str(output_paths["decision_json"]),
                        "summary_markdown": str(output_paths["summary_markdown"]),
                        "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
                        "errors": [],
                    }
                    hazard_summary = {
                        "trace_root": str(trace_root),
                        "aggregate": {
                            "locality_status": aggregate["locality_status"],
                            "exactness_hazard_status": aggregate["exactness_hazard_status"],
                            "recommended_runtime_prototype": aggregate["recommended_runtime_prototype"],
                            "victim_slot_signal": aggregate["victim_slot_signal"],
                            "incoming_key_signal": aggregate["incoming_key_signal"],
                            **aggregate["aggregate_metrics"],
                        },
                        "cases": hazard_cases,
                        "errors": [],
                    }
                    decision = {
                        "decision_status": "ready",
                        "locality_status": aggregate["locality_status"],
                        "exactness_hazard_status": aggregate["exactness_hazard_status"],
                        "recommended_runtime_prototype": aggregate["recommended_runtime_prototype"],
                        "blocked_runtime_prototypes": BLOCKED_RUNTIME_PROTOTYPES,
                        "trace_root": str(trace_root),
                        "errors": [],
                    }

        rows_for_output = rows if "rows" in locals() else []
        write_rows(
            output_paths["per_case_tsv"],
            PER_CASE_FIELDNAMES,
            [format_row(row) for row in rows_for_output],
        )
        write_summary_markdown(output_paths["summary_markdown"], summary, rows_for_output, summary["errors"])
        output_paths["summary_json"].write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output_paths["hazard_summary_json"].write_text(
            json.dumps(hazard_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        output_paths["decision_json"].write_text(
            json.dumps(decision, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        timeline_handle.close()


if __name__ == "__main__":
    main()
