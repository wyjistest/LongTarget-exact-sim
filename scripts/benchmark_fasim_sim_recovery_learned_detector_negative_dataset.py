#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


OUTPUT_FIELDS = [
    "workload_id",
    "box_id",
    "family_id",
    "candidate_id",
    "source",
    "original_source",
    "score",
    "Nt",
    "identity",
    "interval_length",
    "local_rank",
    "family_rank",
    "overlap_degree",
    "distance_to_fasim_boundary",
    "family_size",
    "family_span",
    "box_size",
    "interval_overlap_ratio",
    "dominance_margin",
    "score_margin",
    "Nt_margin",
    "near_threshold_density",
    "peak_count",
    "second_peak_gap",
    "plateau_width",
    "candidate_category",
    "hard_negative_source",
    "label",
    "label_source",
    "split",
    "split_key",
]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_float(value: str) -> float:
    if value in ("", "NA"):
        return 0.0
    return float(value)


def parse_int(value: str) -> int:
    if value in ("", "NA"):
        return 0
    return int(float(value))


def fmt(value: float) -> str:
    return f"{value:.6f}"


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("_") or "unknown"


def family_id(row: Dict[str, str]) -> str:
    return safe_id(
        "|".join(
            [
                row.get("rule", "NA"),
                row.get("strand", "NA"),
                row.get("direction", "NA"),
            ]
        )
    )


def row_key(row: Dict[str, str], label: str) -> Tuple[str, ...]:
    return (
        row.get("workload_label", ""),
        row.get("run_index", ""),
        row.get("chr", ""),
        row.get("genome_start", ""),
        row.get("genome_end", ""),
        row.get("query_start", ""),
        row.get("query_end", ""),
        row.get("rule", ""),
        row.get("strand", ""),
        row.get("direction", ""),
        label,
    )


def row_interval_length(row: Dict[str, str]) -> int:
    genome_len = parse_int(row.get("genome_len", "0"))
    query_len = parse_int(row.get("query_len", "0"))
    return max(genome_len, query_len)


def row_genome_interval(row: Dict[str, str]) -> Tuple[int, int]:
    return (
        parse_int(row.get("genome_start", "0")),
        parse_int(row.get("genome_end", "0")),
    )


def row_query_interval(row: Dict[str, str]) -> Tuple[int, int]:
    return (
        parse_int(row.get("query_start", "0")),
        parse_int(row.get("query_end", "0")),
    )


def interval_length(interval: Tuple[int, int]) -> int:
    return max(interval[1] - interval[0] + 1, 0)


def overlap_length(left: Tuple[int, int], right: Tuple[int, int]) -> int:
    return max(min(left[1], right[1]) - max(left[0], right[0]) + 1, 0)


def overlaps(left: Tuple[int, int], right: Tuple[int, int]) -> bool:
    return overlap_length(left, right) > 0


def contains(outer: Tuple[int, int], inner: Tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def box_id(row: Dict[str, str]) -> str:
    categories = row.get("box_categories", "NA")
    if categories in ("", "NA"):
        categories = "no_box"
    return safe_id(
        "|".join(
            [
                row.get("workload_label", "unknown"),
                f"run{row.get('run_index', '0')}",
                categories,
                row.get("box_count_covering", "0"),
            ]
        )
    )


def box_size(row: Dict[str, str]) -> int:
    cell_cost = parse_int(row.get("cell_cost", "0"))
    if cell_cost > 0:
        return cell_cost
    genome_len = parse_int(row.get("genome_len", "0"))
    query_len = parse_int(row.get("query_len", "0"))
    return max(genome_len * query_len, 0)


def group_key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (row.get("workload_label", ""), row.get("run_index", ""), family_id(row))


def fasim_records_by_group(rows: Sequence[Dict[str, str]]) -> Dict[Tuple[str, str, str], List[Dict[str, str]]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("source") == "fasim_record":
            grouped[group_key(row)].append(row)
    return grouped


def accepted_records_by_group(rows: Sequence[Dict[str, str]]) -> Dict[Tuple[str, str, str], List[Dict[str, str]]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("source") == "accepted_candidate":
            grouped[group_key(row)].append(row)
    return grouped


def distance_to_fasim_boundary(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    fasim_rows = fasim_grouped.get(group_key(row), [])
    if not fasim_rows:
        return "NA"
    start = parse_int(row.get("genome_start", "0"))
    end = parse_int(row.get("genome_end", "0"))
    distances: List[int] = []
    for fasim in fasim_rows:
        fasim_start = parse_int(fasim.get("genome_start", "0"))
        fasim_end = parse_int(fasim.get("genome_end", "0"))
        distances.extend(
            [
                abs(start - fasim_start),
                abs(start - fasim_end),
                abs(end - fasim_start),
                abs(end - fasim_end),
            ]
        )
    return str(min(distances)) if distances else "NA"


def interval_overlap_ratio(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    fasim_rows = fasim_grouped.get(group_key(row), [])
    if not fasim_rows:
        return "0.000000"
    genome = row_genome_interval(row)
    query = row_query_interval(row)
    genome_len = interval_length(genome) or 1
    query_len = interval_length(query) or 1
    best = 0.0
    for fasim in fasim_rows:
        genome_fraction = overlap_length(genome, row_genome_interval(fasim)) / genome_len
        query_fraction = overlap_length(query, row_query_interval(fasim)) / query_len
        best = max(best, min(genome_fraction, query_fraction))
    return fmt(best)


def family_size(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    return str(len(fasim_grouped.get(group_key(row), [])))


def family_span(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    fasim_rows = fasim_grouped.get(group_key(row), [])
    if not fasim_rows:
        return str(interval_length(row_genome_interval(row)))
    starts = [parse_int(fasim.get("genome_start", "0")) for fasim in fasim_rows]
    ends = [parse_int(fasim.get("genome_end", "0")) for fasim in fasim_rows]
    return str(max(ends) - min(starts) + 1)


def containing_higher_score_margin(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    score = parse_float(row.get("score", "0"))
    genome = row_genome_interval(row)
    query = row_query_interval(row)
    margins: List[float] = []
    for fasim in fasim_grouped.get(group_key(row), []):
        fasim_score = parse_float(fasim.get("score", "0"))
        if fasim_score <= score:
            continue
        if contains(row_genome_interval(fasim), genome) and contains(row_query_interval(fasim), query):
            margins.append(fasim_score - score)
    return fmt(max(margins) if margins else 0.0)


def best_reference_rows(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
    accepted_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> List[Dict[str, str]]:
    return accepted_grouped.get(group_key(row), []) or fasim_grouped.get(group_key(row), [])


def score_margin(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
    accepted_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    references = best_reference_rows(row, fasim_grouped, accepted_grouped)
    if not references:
        return "0.000000"
    best_score = max(parse_float(reference.get("score", "0")) for reference in references)
    return fmt(parse_float(row.get("score", "0")) - best_score)


def nt_margin(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
    accepted_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    references = best_reference_rows(row, fasim_grouped, accepted_grouped)
    if not references:
        return "0"
    best_nt = max(parse_int(reference.get("nt", "0")) for reference in references)
    return str(parse_int(row.get("nt", "0")) - best_nt)


def near_threshold_density(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    score = parse_float(row.get("score", "0"))
    genome = row_genome_interval(row)
    query = row_query_interval(row)
    count = 0
    for fasim in fasim_grouped.get(group_key(row), []):
        if abs(parse_float(fasim.get("score", "0")) - score) > 5.0:
            continue
        if overlaps(genome, row_genome_interval(fasim)) or overlaps(query, row_query_interval(fasim)):
            count += 1
    return str(count)


def peak_count(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    genome = row_genome_interval(row)
    query = row_query_interval(row)
    count = 0
    for fasim in fasim_grouped.get(group_key(row), []):
        if overlaps(genome, row_genome_interval(fasim)) or overlaps(query, row_query_interval(fasim)):
            count += 1
    return str(count)


def second_peak_gap(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    scores = sorted(
        {parse_float(fasim.get("score", "0")) for fasim in fasim_grouped.get(group_key(row), [])},
        reverse=True,
    )
    if len(scores) < 2:
        return "0.000000"
    return fmt(scores[0] - scores[1])


def plateau_width(
    row: Dict[str, str],
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> str:
    fasim_rows = fasim_grouped.get(group_key(row), [])
    if not fasim_rows:
        return "0"
    best_score = max(parse_float(fasim.get("score", "0")) for fasim in fasim_rows)
    plateau = [
        fasim
        for fasim in fasim_rows
        if best_score - parse_float(fasim.get("score", "0")) <= 1.0
    ]
    if not plateau:
        return "0"
    starts = [parse_int(fasim.get("genome_start", "0")) for fasim in plateau]
    ends = [parse_int(fasim.get("genome_end", "0")) for fasim in plateau]
    return str(max(ends) - min(starts) + 1)


def split_for_key(split_key: str) -> str:
    return "validation" if zlib.crc32(split_key.encode("utf-8")) % 5 == 0 else "train"


def candidate_category(row: Dict[str, str], source: str) -> str:
    stage = row.get("label_miss_stage", "NA")
    box_state = "box_covered" if row.get("box_covered") == "1" else "not_box_covered"
    return safe_id("|".join([source, stage, box_state]))


def hard_negative_source(row: Dict[str, str], source: str, label: str) -> str:
    if label == "1":
        return "positive"
    if row.get("validate_supported") == "0":
        return "no_legacy_sim_records_proxy"
    stage = row.get("label_miss_stage", "")
    original_source = row.get("source", source)
    if original_source == "accepted_candidate" and stage == "extra":
        return "extra_vs_sim_candidate"
    if original_source == "executor_candidate":
        if stage == "extra":
            return "extra_vs_sim_candidate"
        if parse_float(row.get("score", "0")) >= 85.0 and parse_float(row.get("nt", "0")) >= 45.0:
            return "near_threshold_rejected_candidate"
        return "executor_candidate_non_sim"
    if original_source == "fasim_record":
        return "fasim_supported_non_sim"
    return "negative"


def label_source(row: Dict[str, str], label: str) -> str:
    if row.get("validate_supported") == "0":
        return "unsupported_no_legacy_proxy"
    return "post_hoc_sim_label" if label in ("0", "1") else "unlabeled"


def output_row(
    row: Dict[str, str],
    *,
    source: str,
    label: str,
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
    accepted_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> Dict[str, str]:
    workload = row.get("workload_label", "unknown")
    family = family_id(row)
    split_key = f"{workload}|{family}"
    return {
        "workload_id": workload,
        "box_id": box_id(row),
        "family_id": family,
        "candidate_id": row.get("candidate_id", ""),
        "source": source,
        "original_source": row.get("source", ""),
        "score": row.get("score", "0"),
        "Nt": row.get("nt", "0"),
        "identity": row.get("identity", "0"),
        "interval_length": str(row_interval_length(row)),
        "local_rank": row.get("local_rank", "0"),
        "family_rank": "0",
        "overlap_degree": row.get("same_family_overlap_count", "0"),
        "distance_to_fasim_boundary": distance_to_fasim_boundary(row, fasim_grouped),
        "family_size": family_size(row, fasim_grouped),
        "family_span": family_span(row, fasim_grouped),
        "box_size": str(box_size(row)),
        "interval_overlap_ratio": interval_overlap_ratio(row, fasim_grouped),
        "dominance_margin": containing_higher_score_margin(row, fasim_grouped),
        "score_margin": score_margin(row, fasim_grouped, accepted_grouped),
        "Nt_margin": nt_margin(row, fasim_grouped, accepted_grouped),
        "near_threshold_density": near_threshold_density(row, fasim_grouped),
        "peak_count": peak_count(row, fasim_grouped),
        "second_peak_gap": second_peak_gap(row, fasim_grouped),
        "plateau_width": plateau_width(row, fasim_grouped),
        "candidate_category": candidate_category(row, source),
        "hard_negative_source": hard_negative_source(row, source, label),
        "label": label,
        "label_source": label_source(row, label),
        "split": split_for_key(split_key),
        "split_key": split_key,
    }


def add_row(
    rows: List[Dict[str, str]],
    seen: set[Tuple[str, ...]],
    source_row: Dict[str, str],
    *,
    source: str,
    label: str,
    fasim_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
    accepted_grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]],
) -> None:
    key = row_key(source_row, label)
    if key in seen:
        return
    seen.add(key)
    rows.append(
        output_row(
            source_row,
            source=source,
            label=label,
            fasim_grouped=fasim_grouped,
            accepted_grouped=accepted_grouped,
        )
    )


def assign_family_ranks(rows: List[Dict[str, str]]) -> None:
    grouped: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["workload_id"], row["family_id"])].append(row)
    for group_rows in grouped.values():
        ordered = sorted(
            group_rows,
            key=lambda row: (
                -parse_float(row.get("score", "0")),
                parse_int(row.get("local_rank", "0")) or 999999,
                row.get("candidate_id", ""),
            ),
        )
        for rank, row in enumerate(ordered, start=1):
            row["family_rank"] = str(rank)


def build_negative_dataset(source_rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    fasim_grouped = fasim_records_by_group(source_rows)
    accepted_grouped = accepted_records_by_group(source_rows)
    output: List[Dict[str, str]] = []
    seen: set[Tuple[str, ...]] = set()

    for row in source_rows:
        if row.get("source") == "executor_candidate" and row.get("label_guard_should_accept") == "1":
            add_row(
                output,
                seen,
                row,
                source="executor_candidate_sim_positive",
                label="1",
                fasim_grouped=fasim_grouped,
                accepted_grouped=accepted_grouped,
            )

    for row in source_rows:
        if row.get("source") == "sim_record" and row.get("label_in_sim") == "1":
            add_row(
                output,
                seen,
                row,
                source="sim_record_target_positive",
                label="1",
                fasim_grouped=fasim_grouped,
                accepted_grouped=accepted_grouped,
            )

    for row in source_rows:
        if row.get("source") == "accepted_candidate" and row.get("label_guard_should_accept") == "0":
            add_row(
                output,
                seen,
                row,
                source="accepted_extra_negative",
                label="0",
                fasim_grouped=fasim_grouped,
                accepted_grouped=accepted_grouped,
            )

    for row in source_rows:
        if row.get("source") == "executor_candidate" and row.get("label_guard_should_accept") == "0":
            add_row(
                output,
                seen,
                row,
                source="executor_candidate_negative",
                label="0",
                fasim_grouped=fasim_grouped,
                accepted_grouped=accepted_grouped,
            )

    for row in source_rows:
        if row.get("source") == "fasim_record" and row.get("label_in_sim") == "0":
            add_row(
                output,
                seen,
                row,
                source="fasim_supported_negative",
                label="0",
                fasim_grouped=fasim_grouped,
                accepted_grouped=accepted_grouped,
            )

    for row in source_rows:
        if (
            row.get("validate_supported") == "0"
            and row.get("validate_unsupported_reason") == "no_legacy_sim_records"
            and row.get("source") in ("fasim_record", "executor_candidate", "accepted_candidate")
        ):
            add_row(
                output,
                seen,
                row,
                source="no_legacy_sim_records_proxy_negative",
                label="0",
                fasim_grouped=fasim_grouped,
                accepted_grouped=accepted_grouped,
            )

    assign_family_ranks(output)
    return output


def write_tsv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def telemetry(rows: Sequence[Dict[str, str]], source_rows: Sequence[Dict[str, str]]) -> Dict[str, str]:
    labels = Counter(row["label"] for row in rows)
    splits = Counter((row["split"], row["label"]) for row in rows)
    negative_sources = Counter(
        row["hard_negative_source"] for row in rows if row["label"] == "0"
    )
    accepted = [
        row
        for row in source_rows
        if row.get("source") == "accepted_candidate"
        and row.get("label_guard_should_accept") in ("0", "1")
    ]
    accepted_positive = sum(1 for row in accepted if row.get("label_guard_should_accept") == "1")
    sim_records = [
        row
        for row in source_rows
        if row.get("source") == "sim_record" and row.get("label_available") == "1"
    ]
    positive = labels.get("1", 0)
    negative = labels.get("0", 0)
    return {
        "enabled": "1",
        "source_rows": str(len(source_rows)),
        "rows": str(len(rows)),
        "positive_rows": str(positive),
        "negative_rows": str(negative),
        "learnable_two_class": "1" if positive and negative else "0",
        "class_balance": fmt(negative / positive if positive else 0.0),
        "train_positive": str(splits.get(("train", "1"), 0)),
        "train_negative": str(splits.get(("train", "0"), 0)),
        "validation_positive": str(splits.get(("validation", "1"), 0)),
        "validation_negative": str(splits.get(("validation", "0"), 0)),
        "hard_negative_sources": ",".join(
            f"{key}:{value}" for key, value in sorted(negative_sources.items())
        )
        or "none",
        "baseline_guard_recall_vs_sim": fmt(
            accepted_positive / len(sim_records) * 100.0 if sim_records else 0.0
        ),
        "baseline_guard_precision": fmt(
            accepted_positive / len(accepted) * 100.0 if accepted else 0.0
        ),
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
    }


def render_report(
    *,
    dataset_path: Path,
    output_tsv: Path,
    report_path: Path,
    rows: Sequence[Dict[str, str]],
    metrics: Dict[str, str],
) -> str:
    negative_sources = Counter(
        row["hard_negative_source"] for row in rows if row["label"] == "0"
    )
    split_counts = Counter((row["split"], row["label"]) for row in rows)
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Negative Dataset")
    lines.append("")
    lines.append("## Negative / Contrastive Dataset")
    lines.append("")
    lines.append(
        "This report builds an offline trainable contrastive table from the "
        "learned-detector TSV. It adds positives plus hard negatives for future "
        "SIM-close detector research."
    )
    lines.append("")
    lines.append(f"Input dataset: `{dataset_path}`")
    lines.append(f"Output TSV: `{output_tsv}`")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| fasim_sim_recovery_learned_detector_negative_dataset_{key} | {value} |")
    lines.append("")
    lines.append("## Hard Negative Sources")
    lines.append("")
    lines.append("| Source | Rows |")
    lines.append("| --- | ---: |")
    for source, count in sorted(negative_sources.items()):
        lines.append(f"| {source} | {count} |")
    lines.append("")
    lines.append("## Split Counts")
    lines.append("")
    lines.append("| Split | Positive | Negative |")
    lines.append("| --- | ---: | ---: |")
    for split in ("train", "validation"):
        lines.append(
            f"| {split} | {split_counts.get((split, '1'), 0)} | "
            f"{split_counts.get((split, '0'), 0)} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Positive rows include executor candidates that match legacy SIM and "
        "SIM-record target positives not already represented by executor "
        "candidates. The latter keep not-box-covered positives visible for "
        "future detector work."
    )
    lines.append("")
    lines.append(
        "Hard negatives include executor candidates or accepted candidates that "
        "do not match SIM, Fasim-supported records that are not SIM records, "
        "and no-legacy-SIM proxy negatives only when such rows are present."
    )
    lines.append("")
    lines.append(
        "No production model is trained or loaded. SIM labels remain offline "
        "labels only. They must not be used as runtime detector inputs, guard "
        "inputs, replacement inputs, or output ordering inputs."
    )
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("```text")
    lines.append("Production model added: no")
    lines.append("Fasim runtime changed: no")
    lines.append("SIM-close runtime changed: no")
    lines.append("Scoring/threshold/non-overlap behavior changed: no")
    lines.append("GPU/filter behavior changed: no")
    lines.append("SIM labels used as runtime input: no")
    lines.append("Recommended/default mode: no")
    lines.append("```")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines).rstrip() + "\n"
    report_path.write_text(report, encoding="utf-8")
    return report.rstrip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-tsv", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    try:
        dataset_path = Path(args.dataset).resolve()
        output_tsv = Path(args.output_tsv).resolve()
        report_path = Path(args.report).resolve()
        source_rows = read_rows(dataset_path)
        rows = build_negative_dataset(source_rows)
        write_tsv(output_tsv, rows)
        metrics = telemetry(rows, source_rows)
        report = render_report(
            dataset_path=dataset_path,
            output_tsv=output_tsv,
            report_path=report_path,
            rows=rows,
            metrics=metrics,
        )
        for key, value in metrics.items():
            print(f"benchmark.fasim_sim_recovery_learned_detector_negative_dataset.total.{key}={value}")
        print(report)
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
