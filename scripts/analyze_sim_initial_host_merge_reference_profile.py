#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path


SELECTED_CASE_FIELDNAMES = [
    "case_id",
    "selection_rank",
    "selection_reason",
    "context_apply_seconds",
    "context_apply_lookup_seconds",
    "context_apply_lookup_miss_seconds",
    "context_apply_lookup_miss_candidate_set_full_probe_seconds",
    "context_apply_lookup_miss_reuse_writeback_seconds",
    "reference_total_mean_seconds",
    "reference_full_set_miss_mean_seconds",
    "dominant_hotspot_family",
    "candidate_index_map_self_seconds",
    "heap_maintenance_self_seconds",
    "other_reference_path_self_seconds",
    "setup_or_materialize_noise_self_seconds",
]
HOTSPOT_FAMILY_ORDER = [
    "candidate_index_map_path",
    "heap_maintenance_path",
    "other_reference_path",
    "setup_or_materialize_noise",
]
ACTIONABLE_HOTSPOT_FAMILY_ORDER = [
    "candidate_index_map_path",
    "heap_maintenance_path",
    "other_reference_path",
]
HOTSPOT_RECOMMENDATIONS = {
    "candidate_index_map_path": "optimize_candidate_index_map_path",
    "heap_maintenance_path": "optimize_heap_path",
    "other_reference_path": "inspect_other_reference_path",
    "setup_or_materialize_noise": "tighten_profile_isolation",
}
GPROF_PATTERN = re.compile(
    r"^\s*"
    r"(?P<pct>[0-9]+(?:\.[0-9]+)?)\s+"
    r"(?P<cumulative>[0-9]+(?:\.[0-9]+)?)\s+"
    r"(?P<self>[0-9]+(?:\.[0-9]+)?)"
    r"(?:\s+\S+\s+\S+\s+\S+)?\s+"
    r"(?P<name>\S.*\S|\S)\s*$"
)


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="	"))


def write_rows(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="	", extrasaction="ignore"
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


def parse_gprof_reports(values):
    reports = defaultdict(list)
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid --gprof-report value: {value}")
        case_id, raw_path = value.split("=", 1)
        case_id = case_id.strip()
        report_path = Path(raw_path.strip())
        if not case_id:
            raise ValueError(f"invalid --gprof-report value: {value}")
        reports[case_id].append(report_path)
    return reports


def classify_hotspot_family(symbol_name):
    if (
        "std::chrono::" in symbol_name
        or "simElapsedNanoseconds(" in symbol_name
        or "set_gprof_sampling_enabled(" in symbol_name
    ):
        return "setup_or_materialize_noise"
    if (
        "probeSimCandidateIndexSlot" in symbol_name
        or "ensureSimCandidateIndexForRun" in symbol_name
        or "_M_find_before_node" in symbol_name
        or "_M_emplace" in symbol_name
        or "insertSimCandidateIndexEntry" in symbol_name
        or "eraseSimCandidateIndexEntry" in symbol_name
        or "simCandidateIndexHash" in symbol_name
        or "findSimCandidateIndexEntry" in symbol_name
    ):
        return "candidate_index_map_path"
    if (
        "updateSimCandidateMinHeapIndex" in symbol_name
        or "peekMinSimCandidateIndex" in symbol_name
        or "simCandidateHeapSiftUp" in symbol_name
        or "simCandidateHeapSiftDown" in symbol_name
        or "simCandidateHeapSwap" in symbol_name
        or "simCandidateHeapLess" in symbol_name
    ):
        return "heap_maintenance_path"
    if "mergeSimCudaInitialRunSummariesIntoSafeStore" in symbol_name:
        return "setup_or_materialize_noise"
    return "other_reference_path"


def parse_gprof_self_seconds(path: Path):
    family_seconds = defaultdict(float)
    symbol_seconds = defaultdict(float)
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = GPROF_PATTERN.match(raw_line)
        if not match:
            continue
        symbol_name = match.group("name")
        self_seconds = float(match.group("self"))
        family_name = classify_hotspot_family(symbol_name)
        family_seconds[family_name] += self_seconds
        symbol_seconds[symbol_name] += self_seconds
    return family_seconds, symbol_seconds


def merge_case_family_seconds(report_paths):
    merged = defaultdict(float)
    merged_symbols = defaultdict(float)
    for report_path in report_paths:
        family_seconds, symbol_seconds = parse_gprof_self_seconds(report_path)
        for family_name, seconds in family_seconds.items():
            merged[family_name] += seconds
        for symbol_name, seconds in symbol_seconds.items():
            merged_symbols[symbol_name] += seconds
    for family_name in HOTSPOT_FAMILY_ORDER:
        merged.setdefault(family_name, 0.0)
    return dict(merged), dict(merged_symbols)


def choose_selected_case_ids(context_rows, anchor_case_id, heavy_case_count):
    indexed = index_by_case_id(context_rows, "context_apply")
    if anchor_case_id not in indexed:
        raise ValueError(f"anchor case not found in context_apply TSV: {anchor_case_id}")

    ranked = sorted(
        (row for row in context_rows if row["case_id"] != anchor_case_id),
        key=lambda row: (-float(row["context_apply_seconds"]), row["case_id"]),
    )
    selected = [anchor_case_id]
    selected.extend(row["case_id"] for row in ranked[:heavy_case_count])
    return selected


def choose_dominant_family(family_seconds, family_names=None):
    if family_names is None:
        ranked_source = family_seconds.items()
    else:
        ranked_source = [
            (family_name, family_seconds.get(family_name, 0.0))
            for family_name in family_names
        ]
    ranked = sorted(
        ranked_source,
        key=lambda item: (-item[1], item[0]),
    )
    return ranked[0][0], ranked


def compute_recommendation(dominant_family, top_family_case_count, selected_case_count):
    if selected_case_count <= 0:
        return "insufficient_signal"
    required_case_count = max(1, math.ceil(selected_case_count / 2.0))
    if top_family_case_count < required_case_count:
        return "insufficient_signal"
    return HOTSPOT_RECOMMENDATIONS.get(dominant_family, "inspect_other_reference_path")


def build_selected_rows(selected_case_ids, context_rows, reference_rows, gprof_reports):
    context_by_case = index_by_case_id(context_rows, "context_apply")
    reference_by_case = index_by_case_id(reference_rows, "reference_aggregate")
    selected_rows = []
    case_dominant_families = {}
    aggregate_family_seconds = {family: 0.0 for family in HOTSPOT_FAMILY_ORDER}
    aggregate_symbol_seconds = defaultdict(float)

    for selection_rank, case_id in enumerate(selected_case_ids, start=1):
        if case_id not in context_by_case:
            raise ValueError(f"missing context_apply row for selected case: {case_id}")
        if case_id not in reference_by_case:
            raise ValueError(f"missing reference aggregate row for selected case: {case_id}")
        if case_id not in gprof_reports:
            raise ValueError(f"missing gprof report for selected case: {case_id}")

        family_seconds, symbol_seconds = merge_case_family_seconds(gprof_reports[case_id])
        dominant_family, _ = choose_dominant_family(
            family_seconds, ACTIONABLE_HOTSPOT_FAMILY_ORDER
        )
        case_dominant_families[case_id] = dominant_family
        for family_name, seconds in family_seconds.items():
            aggregate_family_seconds[family_name] += seconds
        for symbol_name, seconds in symbol_seconds.items():
            aggregate_symbol_seconds[symbol_name] += seconds

        context_row = context_by_case[case_id]
        reference_row = reference_by_case[case_id]
        selected_rows.append(
            {
                "case_id": case_id,
                "selection_rank": selection_rank,
                "selection_reason": "anchor_case" if selection_rank == 1 else "heavy_context_apply_case",
                "context_apply_seconds": context_row["context_apply_seconds"],
                "context_apply_lookup_seconds": context_row["context_apply_lookup_seconds"],
                "context_apply_lookup_miss_seconds": context_row["context_apply_lookup_miss_seconds"],
                "context_apply_lookup_miss_candidate_set_full_probe_seconds": context_row[
                    "context_apply_lookup_miss_candidate_set_full_probe_seconds"
                ],
                "context_apply_lookup_miss_reuse_writeback_seconds": context_row[
                    "context_apply_lookup_miss_reuse_writeback_seconds"
                ],
                "reference_total_mean_seconds": reference_row["total_mean_seconds"],
                "reference_full_set_miss_mean_seconds": reference_row["full_set_miss_mean_seconds"],
                "dominant_hotspot_family": dominant_family,
                "candidate_index_map_self_seconds": f"{family_seconds['candidate_index_map_path']:.6f}",
                "heap_maintenance_self_seconds": f"{family_seconds['heap_maintenance_path']:.6f}",
                "other_reference_path_self_seconds": f"{family_seconds['other_reference_path']:.6f}",
                "setup_or_materialize_noise_self_seconds": f"{family_seconds['setup_or_materialize_noise']:.6f}",
            }
        )

    return (
        selected_rows,
        case_dominant_families,
        aggregate_family_seconds,
        dict(aggregate_symbol_seconds),
    )


def write_summary_markdown(path: Path, summary):
    family_lines = []
    for family_name in HOTSPOT_FAMILY_ORDER:
        family_lines.append(
            f"| {family_name} | {summary['family_self_seconds'][family_name]:.6f} | {summary['family_self_share'][family_name]:.4f} |"
        )

    top_symbol_lines = []
    for symbol_name, seconds in summary["top_symbols"]:
        top_symbol_lines.append(f"| `{symbol_name}` | {seconds:.6f} |")

    content = (
        "# Host-Merge Reference Profile Summary\n\n"
        f"- anchor_case_id: `{summary['anchor_case_id']}`\n"
        f"- selected_case_count: `{summary['selected_case_count']}`\n"
        f"- selected_case_ids: `{', '.join(summary['selected_case_ids'])}`\n"
        f"- dominant_hotspot_family: `{summary['dominant_hotspot_family']}`\n"
        f"- recommended_next_step: `{summary['recommended_next_step']}`\n"
        f"- top_hotspot_family_case_count: `{summary['top_hotspot_family_case_count']}`\n\n"
        "| hotspot_family | self_seconds | share |\n"
        "| --- | ---: | ---: |\n"
        + "\n".join(family_lines)
        + "\n\n"
        "## Top Symbols\n\n"
        "| symbol | self_seconds |\n"
        "| --- | ---: |\n"
        + "\n".join(top_symbol_lines)
        + "\n"
    )
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-apply-tsv", required=True)
    parser.add_argument("--reference-aggregate-tsv", required=True)
    parser.add_argument("--gprof-report", action="append", default=[])
    parser.add_argument("--anchor-case", required=True)
    parser.add_argument("--heavy-case-count", type=int, default=5)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    context_rows = load_rows(Path(args.context_apply_tsv))
    reference_rows = load_rows(Path(args.reference_aggregate_tsv))
    gprof_reports = parse_gprof_reports(args.gprof_report)

    selected_case_ids = choose_selected_case_ids(
        context_rows, args.anchor_case, args.heavy_case_count
    )
    (
        selected_rows,
        case_dominant_families,
        aggregate_family_seconds,
        aggregate_symbol_seconds,
    ) = build_selected_rows(
        selected_case_ids,
        context_rows,
        reference_rows,
        gprof_reports,
    )

    dominant_family, ranked_families = choose_dominant_family(
        aggregate_family_seconds, ACTIONABLE_HOTSPOT_FAMILY_ORDER
    )
    top_hotspot_family_case_count = sum(
        1 for family_name in case_dominant_families.values() if family_name == dominant_family
    )
    recommended_next_step = compute_recommendation(
        dominant_family, top_hotspot_family_case_count, len(selected_case_ids)
    )
    total_family_seconds = sum(aggregate_family_seconds.values())
    family_self_share = {}
    for family_name in HOTSPOT_FAMILY_ORDER:
        if total_family_seconds > 0.0:
            family_self_share[family_name] = (
                aggregate_family_seconds[family_name] / total_family_seconds
            )
        else:
            family_self_share[family_name] = 0.0

    summary_md_path = output_dir / "summary.md"
    selected_cases_path = output_dir / "selected_cases.tsv"
    top_symbols = sorted(
        aggregate_symbol_seconds.items(),
        key=lambda item: (-item[1], item[0]),
    )[:8]
    summary = {
        "anchor_case_id": args.anchor_case,
        "selected_case_ids": selected_case_ids,
        "selected_case_count": len(selected_case_ids),
        "dominant_hotspot_family": dominant_family,
        "recommended_next_step": recommended_next_step,
        "top_hotspot_family_case_count": top_hotspot_family_case_count,
        "family_self_seconds": {
            family_name: round(aggregate_family_seconds[family_name], 6)
            for family_name in HOTSPOT_FAMILY_ORDER
        },
        "family_self_share": {
            family_name: round(family_self_share[family_name], 6)
            for family_name in HOTSPOT_FAMILY_ORDER
        },
        "ranked_hotspot_families": [
            {"family": family_name, "self_seconds": round(seconds, 6)}
            for family_name, seconds in ranked_families
        ],
        "case_dominant_families": case_dominant_families,
        "top_symbols": [
            {"symbol": symbol_name, "self_seconds": round(seconds, 6)}
            for symbol_name, seconds in top_symbols
        ],
        "summary_markdown": str(summary_md_path),
        "selected_cases_tsv": str(selected_cases_path),
    }

    write_rows(selected_cases_path, SELECTED_CASE_FIELDNAMES, selected_rows)
    write_summary_markdown(
        summary_md_path,
        {
            **summary,
            "top_symbols": [(item["symbol"], item["self_seconds"]) for item in summary["top_symbols"]],
        },
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
