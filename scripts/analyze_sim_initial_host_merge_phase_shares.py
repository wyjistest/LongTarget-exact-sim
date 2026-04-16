#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

from select_sim_initial_host_merge_cases import enrich_rows

PHASE_FIELDS = {
    "store_materialize": "store_materialize_mean_seconds",
    "store_prune": "store_prune_mean_seconds",
    "store_other_merge": "store_other_merge_mean_seconds",
}
SELECTED_JOINED_FIELDNAMES = [
    "case_id",
    "selection_rank",
    "selection_reason",
    "bucket_key",
    "summary_bin",
    "materialized_bin",
    "prune_bin",
    "logical_event_count",
    "summary_count",
    "store_materialized_count",
    "store_pruned_count",
    "prune_ratio",
    "warmup_iterations",
    "iterations",
    "store_materialize_mean_seconds",
    "store_prune_mean_seconds",
    "store_other_merge_mean_seconds",
    "full_host_merge_mean_seconds",
    "ns_per_logical_event",
    "ns_per_materialized_record",
    "ns_per_pruned_record",
]
BUCKET_ROLLUP_FIELDNAMES = [
    "bucket_key",
    "summary_bin",
    "materialized_bin",
    "prune_bin",
    "bucket_case_count",
    "bucket_logical_event_count",
    "bucket_summary_count",
    "bucket_store_materialized_count",
    "bucket_store_pruned_count",
    "covered_by_selection",
    "representative_case_id",
    "representative_selection_rank",
    "representative_selection_reason",
    "representative_logical_event_count",
    "estimated_store_materialize_seconds",
    "estimated_store_prune_seconds",
    "estimated_store_other_merge_seconds",
]
COVERAGE_THRESHOLD = 0.80
SPLIT_SHARE_GAP_THRESHOLD = 0.05


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def index_by_case_id(rows, label):
    indexed = {}
    for row in rows:
        case_id = row["case_id"]
        if case_id in indexed:
            raise ValueError(f"duplicate {label} case_id: {case_id}")
        indexed[case_id] = row
    return indexed


def bucket_sort_key(bucket_key):
    summary_token, materialized_token, prune_token = bucket_key.split("|")
    return (int(summary_token[1:]), int(materialized_token[1:]), int(prune_token[1:]))


def summarize_manifest_buckets(rows):
    bucket_totals = {}
    total_logical_event_count = 0
    total_store_materialized_count = 0

    for row in rows:
        bucket = bucket_totals.setdefault(
            row["bucket_key"],
            {
                "bucket_key": row["bucket_key"],
                "summary_bin": row["summary_bin"],
                "materialized_bin": row["materialized_bin"],
                "prune_bin": row["prune_bin"],
                "bucket_case_count": 0,
                "bucket_logical_event_count": 0,
                "bucket_summary_count": 0,
                "bucket_store_materialized_count": 0,
                "bucket_store_pruned_count": 0,
            },
        )
        logical_event_count = int(row["logical_event_count"])
        store_materialized_count = int(row["store_materialized_count"])
        bucket["bucket_case_count"] += 1
        bucket["bucket_logical_event_count"] += logical_event_count
        bucket["bucket_summary_count"] += int(row["summary_count"])
        bucket["bucket_store_materialized_count"] += store_materialized_count
        bucket["bucket_store_pruned_count"] += int(row["store_pruned_count"])
        total_logical_event_count += logical_event_count
        total_store_materialized_count += store_materialized_count

    return (
        bucket_totals,
        total_logical_event_count,
        total_store_materialized_count,
    )


def choose_bucket_representatives(selected_joined_rows):
    by_bucket = {}
    for row in selected_joined_rows:
        by_bucket.setdefault(row["_manifest_bucket_key"], []).append(row)

    representatives = {}
    for bucket_key, rows in by_bucket.items():
        representatives[bucket_key] = min(
            rows,
            key=lambda row: (
                row["selection_reason"] != "bucket_representative",
                int(row["selection_rank"]),
                row["case_id"],
            ),
        )
    return representatives


def estimate_phase_seconds(bucket_totals, representatives):
    phase_seconds = {phase: 0.0 for phase in PHASE_FIELDS}
    bucket_rows = []

    for bucket_key in sorted(bucket_totals.keys(), key=bucket_sort_key):
        bucket = dict(bucket_totals[bucket_key])
        representative = representatives.get(bucket_key)
        bucket["covered_by_selection"] = "true" if representative else "false"
        bucket["representative_case_id"] = representative["case_id"] if representative else ""
        bucket["representative_selection_rank"] = (
            representative["selection_rank"] if representative else ""
        )
        bucket["representative_selection_reason"] = (
            representative["selection_reason"] if representative else ""
        )
        bucket["representative_logical_event_count"] = (
            representative["logical_event_count"] if representative else ""
        )

        for phase in PHASE_FIELDS:
            estimate_field = f"estimated_{phase}_seconds"
            bucket[estimate_field] = ""

        if representative:
            representative_logical_event_count = int(representative["logical_event_count"])
            scale = (
                bucket["bucket_logical_event_count"] / representative_logical_event_count
                if representative_logical_event_count > 0
                else 0.0
            )
            for phase, field_name in PHASE_FIELDS.items():
                estimated_seconds = float(representative[field_name]) * scale
                phase_seconds[phase] += estimated_seconds
                bucket[f"estimated_{phase}_seconds"] = f"{estimated_seconds:.6f}"

        bucket_rows.append(bucket)

    return phase_seconds, bucket_rows


def compute_dominant_phase(phase_seconds):
    total_seconds = sum(phase_seconds.values())
    if total_seconds <= 0.0:
        return "unknown", {phase: 0.0 for phase in phase_seconds}

    phase_shares = {
        phase: seconds / total_seconds for phase, seconds in phase_seconds.items()
    }
    ranked = sorted(
        phase_seconds.items(),
        key=lambda item: (-item[1], item[0]),
    )
    top_phase, _ = ranked[0]
    second_phase, _ = ranked[1]
    if {
        top_phase,
        second_phase,
    } == {"store_materialize", "store_prune"} and (
        abs(phase_shares[top_phase] - phase_shares[second_phase])
        <= SPLIT_SHARE_GAP_THRESHOLD
    ):
        return "split", phase_shares
    return top_phase, phase_shares


def compute_next_action(decision_status, dominant_phase):
    if decision_status != "ready":
        return "expand_corpus"
    if dominant_phase == "store_materialize":
        return "optimize_store_materialize"
    if dominant_phase == "store_prune":
        return "optimize_store_prune"
    if dominant_phase == "split":
        return "split_materialize_and_prune"
    if dominant_phase == "store_other_merge":
        return "revisit_store_other_merge"
    return "revisit_measurement"


def write_summary_markdown(path: Path, summary):
    phase_lines = []
    for phase in ["store_materialize", "store_prune", "store_other_merge"]:
        phase_lines.append(
            f"| {phase} | {summary['phase_seconds'][phase]:.6f} | {summary['phase_shares'][phase]:.4f} |"
        )

    content = (
        "# SIM Initial Host Merge Phase Share Analysis\n\n"
        f"- decision_status: `{summary['decision_status']}`\n"
        f"- next_action: `{summary['next_action']}`\n"
        f"- dominant_phase: `{summary['dominant_phase']}`\n"
        f"- covered_bucket_share: `{summary['covered_bucket_share']:.4f}`\n"
        f"- covered_logical_event_share: `{summary['covered_logical_event_share']:.4f}`\n"
        f"- covered_store_materialized_share: `{summary['covered_store_materialized_share']:.4f}`\n\n"
        "| phase | estimated_seconds | share |\n"
        "| --- | ---: | ---: |\n"
        + "\n".join(phase_lines)
        + "\n"
    )
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--selected", required=True)
    parser.add_argument("--aggregate", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = enrich_rows(load_rows(Path(args.manifest)))
    selected_rows = load_rows(Path(args.selected))
    aggregate_rows = load_rows(Path(args.aggregate))

    manifest_by_case = index_by_case_id(manifest_rows, "manifest")
    aggregate_by_case = index_by_case_id(aggregate_rows, "aggregate")
    bucket_totals, total_logical_event_count, total_store_materialized_count = (
        summarize_manifest_buckets(manifest_rows)
    )

    selected_joined_rows = []
    for selected_row in selected_rows:
        case_id = selected_row["case_id"]
        if case_id not in manifest_by_case:
            raise ValueError(f"selected case_id missing from manifest: {case_id}")
        if case_id not in aggregate_by_case:
            raise ValueError(f"selected case_id missing from aggregate: {case_id}")

        joined = dict(manifest_by_case[case_id])
        joined["_manifest_bucket_key"] = manifest_by_case[case_id]["bucket_key"]
        joined.update(selected_row)
        joined.update(aggregate_by_case[case_id])
        selected_joined_rows.append(joined)

    representatives = choose_bucket_representatives(selected_joined_rows)
    phase_seconds, bucket_rollup_rows = estimate_phase_seconds(
        bucket_totals, representatives
    )

    covered_bucket_count = len(representatives)
    total_nonempty_bucket_count = len(bucket_totals)
    covered_logical_event_count = sum(
        bucket_totals[bucket_key]["bucket_logical_event_count"]
        for bucket_key in representatives.keys()
    )
    covered_store_materialized_count = sum(
        bucket_totals[bucket_key]["bucket_store_materialized_count"]
        for bucket_key in representatives.keys()
    )

    covered_bucket_share = (
        covered_bucket_count / total_nonempty_bucket_count
        if total_nonempty_bucket_count
        else 0.0
    )
    covered_logical_event_share = (
        covered_logical_event_count / total_logical_event_count
        if total_logical_event_count
        else 0.0
    )
    covered_store_materialized_share = (
        covered_store_materialized_count / total_store_materialized_count
        if total_store_materialized_count
        else 0.0
    )

    dominant_phase, phase_shares = compute_dominant_phase(phase_seconds)
    decision_status = (
        "ready"
        if (
            covered_logical_event_share >= COVERAGE_THRESHOLD
            and covered_store_materialized_share >= COVERAGE_THRESHOLD
        )
        else "insufficient_coverage"
    )
    next_action = compute_next_action(decision_status, dominant_phase)

    selected_joined_tsv = output_dir / "selected_joined.tsv"
    bucket_rollup_tsv = output_dir / "bucket_rollup.tsv"
    summary_json_path = output_dir / "summary.json"
    summary_markdown_path = output_dir / "summary.md"

    write_rows(selected_joined_tsv, SELECTED_JOINED_FIELDNAMES, selected_joined_rows)
    write_rows(bucket_rollup_tsv, BUCKET_ROLLUP_FIELDNAMES, bucket_rollup_rows)

    summary = {
        "decision_status": decision_status,
        "next_action": next_action,
        "dominant_phase": dominant_phase,
        "covered_bucket_count": covered_bucket_count,
        "total_nonempty_bucket_count": total_nonempty_bucket_count,
        "covered_bucket_share": covered_bucket_share,
        "covered_logical_event_share": covered_logical_event_share,
        "covered_store_materialized_share": covered_store_materialized_share,
        "phase_seconds": phase_seconds,
        "phase_shares": phase_shares,
        "selected_joined_tsv": str(selected_joined_tsv),
        "bucket_rollup_tsv": str(bucket_rollup_tsv),
        "summary_markdown": str(summary_markdown_path),
    }
    summary_json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_summary_markdown(summary_markdown_path, summary)


if __name__ == "__main__":
    main()
