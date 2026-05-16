#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import zlib
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Sequence

import benchmark_fasim_sim_recovery_learned_detector_model_shadow as model_shadow


REQUESTED_NEGATIVE_SOURCES = [
    "executor_candidate_non_sim",
    "extra_vs_sim_candidate",
    "fasim_supported_non_sim",
    "near_threshold_rejected_candidate",
    "no_legacy_sim_records_proxy",
]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_float(value: str) -> float:
    if value in ("", "NA", None):
        return 0.0
    return float(value)


def safe_metric_value(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:,|=-]+", "_", value.strip())
    return cleaned.strip("_") or "none"


def split_for_key(split_key: str) -> str:
    return "validation" if zlib.crc32(split_key.encode("utf-8")) % 5 == 0 else "train"


def split_counts(
    rows: Sequence[Dict[str, str]],
    split_func: Callable[[Dict[str, str]], str],
) -> Dict[str, str]:
    counts = Counter((split_func(row), row.get("label", "0")) for row in rows)
    train_rows = sum(1 for row in rows if split_func(row) == "train")
    validation_rows = sum(1 for row in rows if split_func(row) == "validation")
    train_positive = counts.get(("train", "1"), 0)
    train_negative = counts.get(("train", "0"), 0)
    validation_positive = counts.get(("validation", "1"), 0)
    validation_negative = counts.get(("validation", "0"), 0)
    degenerate = int(
        train_rows == 0
        or validation_rows == 0
        or train_positive == 0
        or train_negative == 0
        or validation_positive == 0
        or validation_negative == 0
    )
    return {
        "train_positive": str(train_positive),
        "train_negative": str(train_negative),
        "validation_positive": str(validation_positive),
        "validation_negative": str(validation_negative),
        "degenerate": str(degenerate),
    }


def current_split(row: Dict[str, str]) -> str:
    return row.get("split", "train")


def family_heldout_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("family_id", "unknown"))


def workload_heldout_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("workload_id", "unknown"))


def source_availability(source_rows: Sequence[Dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {source: 0 for source in REQUESTED_NEGATIVE_SOURCES}
    for row in source_rows:
        source = row.get("source", "")
        stage = row.get("label_miss_stage", "")
        score = parse_float(row.get("score", "0"))
        nt = parse_float(row.get("nt", "0"))
        if source in ("executor_candidate", "accepted_candidate") and stage == "extra":
            counts["extra_vs_sim_candidate"] += 1
        if source == "executor_candidate" and row.get("label_guard_should_accept") == "0":
            counts["executor_candidate_non_sim"] += 1
            if score >= 85.0 and nt >= 45.0:
                counts["near_threshold_rejected_candidate"] += 1
        if source == "fasim_record" and row.get("label_in_sim") == "0":
            counts["fasim_supported_non_sim"] += 1
        if (
            row.get("validate_supported") == "0"
            and row.get("validate_unsupported_reason") == "no_legacy_sim_records"
            and source in ("fasim_record", "executor_candidate", "accepted_candidate")
        ):
            counts["no_legacy_sim_records_proxy"] += 1
    return counts


def source_counts_string(counts: Counter[str] | Dict[str, int]) -> str:
    nonzero = [(key, value) for key, value in sorted(counts.items()) if value]
    return ",".join(f"{key}:{value}" for key, value in nonzero) or "none"


def run_current_split_shadow(
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
) -> Dict[str, str]:
    train_rows = [row for row in rows if row.get("split") == "train"]
    validation_rows = [row for row in rows if row.get("split") == "validation"]
    means, stdevs, weights = model_shadow.train_feature_stats(train_rows)
    train_scores = model_shadow.model_scores(train_rows, means=means, stdevs=stdevs, weights=weights)
    validation_scores = model_shadow.model_scores(
        validation_rows,
        means=means,
        stdevs=stdevs,
        weights=weights,
    )
    threshold = model_shadow.select_threshold(train_rows, train_scores)
    train_metrics = model_shadow.evaluate(train_rows, train_scores, threshold)
    validation_metrics = model_shadow.evaluate(validation_rows, validation_scores, threshold)
    current_guard_train = model_shadow.current_guard_metrics(source_rows, "train")
    current_guard_validation = model_shadow.current_guard_metrics(source_rows, "validation")
    shadow_metrics = model_shadow.telemetry(
        rows=rows,
        train_rows=train_rows,
        validation_rows=validation_rows,
        validation_scores=validation_scores,
        threshold=threshold,
        train_metrics=train_metrics,
        validation_metrics=validation_metrics,
        current_guard_train=current_guard_train,
        current_guard_validation=current_guard_validation,
    )
    return {
        "model_evaluation_mode": shadow_metrics["evaluation_mode"],
        "model_heavy_ml_dependency": shadow_metrics["heavy_ml_dependency"],
        "selected_threshold": shadow_metrics["selected_threshold"],
        "all_row_validation_precision": shadow_metrics["validation_precision"],
        "all_row_validation_recall": shadow_metrics["validation_recall"],
        "all_row_validation_false_positives": shadow_metrics["validation_false_positives"],
        "all_row_validation_false_negatives": shadow_metrics["validation_false_negatives"],
        "candidate_eligible_selected": shadow_metrics["validation_candidate_eligible_selected"],
        "candidate_eligible_true_positive": shadow_metrics["validation_candidate_eligible_true_positive"],
        "candidate_eligible_false_positive": shadow_metrics["validation_candidate_eligible_false_positive"],
        "candidate_eligible_false_negative_vs_all_positives": shadow_metrics[
            "validation_candidate_eligible_false_negative_vs_all_positives"
        ],
        "candidate_eligible_precision": shadow_metrics["validation_candidate_eligible_precision"],
        "candidate_eligible_recall_vs_all_positives": shadow_metrics[
            "validation_candidate_eligible_recall_vs_all_positives"
        ],
        "current_guard_validation_precision": shadow_metrics["current_guard_validation_precision"],
        "current_guard_validation_recall": shadow_metrics["current_guard_validation_recall"],
        "current_guard_validation_false_positives": shadow_metrics[
            "current_guard_validation_false_positives"
        ],
        "current_guard_validation_false_negatives": shadow_metrics[
            "current_guard_validation_false_negatives"
        ],
        "beats_current_guard_on_validation": shadow_metrics["beats_current_guard_on_validation"],
    }


def telemetry(rows: Sequence[Dict[str, str]], source_rows: Sequence[Dict[str, str]]) -> Dict[str, str]:
    labels = Counter(row.get("label", "0") for row in rows)
    hard_negative_sources = Counter(
        row.get("hard_negative_source", "NA") for row in rows if row.get("label") == "0"
    )
    source_avail = source_availability(source_rows)
    current = split_counts(rows, current_split)
    family = split_counts(rows, family_heldout_split)
    workload = split_counts(rows, workload_heldout_split)
    unique_workloads = len({row.get("workload_id", "unknown") for row in rows})
    unique_families = len({row.get("family_id", "unknown") for row in rows})
    candidate_eligible_positive = sum(
        1 for row in rows if row.get("label") == "1" and row.get("source") != "sim_record_target_positive"
    )
    candidate_eligible_negative = sum(1 for row in rows if row.get("label") == "0")
    missing_requested_sources = [
        source for source in REQUESTED_NEGATIVE_SOURCES if hard_negative_sources.get(source, 0) == 0
    ]

    metrics = {
        "enabled": "1",
        "rows": str(len(rows)),
        "positive_rows": str(labels.get("1", 0)),
        "negative_rows": str(labels.get("0", 0)),
        "learnable_two_class": "1" if labels.get("1", 0) and labels.get("0", 0) else "0",
        "source_rows": str(len(source_rows)),
        "unique_workloads": str(unique_workloads),
        "unique_families": str(unique_families),
        "hard_negative_sources": source_counts_string(hard_negative_sources),
        "available_requested_negative_sources": source_counts_string(source_avail),
        "missing_requested_negative_sources": safe_metric_value(",".join(missing_requested_sources)),
        "candidate_eligible_positive_rows": str(candidate_eligible_positive),
        "candidate_eligible_negative_rows": str(candidate_eligible_negative),
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
    }
    for source in REQUESTED_NEGATIVE_SOURCES:
        metrics[f"requested_negative_source_{source}"] = str(hard_negative_sources.get(source, 0))
        metrics[f"available_negative_source_{source}"] = str(source_avail.get(source, 0))
    for prefix, split_metrics in (
        ("current_split", current),
        ("family_heldout", family),
        ("workload_heldout", workload),
    ):
        for key, value in split_metrics.items():
            metrics[f"{prefix}_{key}"] = value
    if unique_workloads < 2:
        metrics["workload_heldout_degenerate"] = "1"
    metrics.update(run_current_split_shadow(rows, source_rows))
    return metrics


def render_report(
    *,
    dataset_path: Path,
    source_dataset_path: Path,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    metrics: Dict[str, str],
) -> str:
    hard_negative_sources = Counter(
        row.get("hard_negative_source", "NA") for row in rows if row.get("label") == "0"
    )
    source_avail = source_availability(source_rows)
    source_kinds = Counter(row.get("source", "NA") for row in source_rows)
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Dataset Expansion")
    lines.append("")
    lines.append("## Offline Dataset Expansion Audit")
    lines.append("")
    lines.append(
        "This report audits the positive + hard-negative learned-detector dataset, "
        "the available hard-negative sources in the source TSV, and split "
        "discipline for future offline detector research. It does not add a "
        "runtime model or change Fasim output."
    )
    lines.append("")
    lines.append(f"Input negative dataset: `{dataset_path}`")
    lines.append(f"Input source learned dataset: `{source_dataset_path}`")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| fasim_sim_recovery_learned_detector_dataset_expansion_{key} | {value} |")
    lines.append("")
    lines.append("## Hard Negative Source Audit")
    lines.append("")
    lines.append("| Source | Dataset rows | Source rows available |")
    lines.append("| --- | ---: | ---: |")
    for source in REQUESTED_NEGATIVE_SOURCES:
        lines.append(
            f"| {source} | {hard_negative_sources.get(source, 0)} | "
            f"{source_avail.get(source, 0)} |"
        )
    lines.append("")
    lines.append("No unavailable hard-negative rows are fabricated.")
    lines.append("")
    lines.append("## Source Row Mix")
    lines.append("")
    lines.append("| Source row kind | Rows |")
    lines.append("| --- | ---: |")
    for source, count in sorted(source_kinds.items()):
        lines.append(f"| {source} | {count} |")
    lines.append("")
    lines.append("## Split Discipline Audit")
    lines.append("")
    lines.append("| Split policy | Train positive | Train negative | Validation positive | Validation negative | Degenerate |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for policy in ("current_split", "family_heldout", "workload_heldout"):
        lines.append(
            f"| {policy} | {metrics[f'{policy}_train_positive']} | "
            f"{metrics[f'{policy}_train_negative']} | "
            f"{metrics[f'{policy}_validation_positive']} | "
            f"{metrics[f'{policy}_validation_negative']} | "
            f"{metrics[f'{policy}_degenerate']} |"
        )
    lines.append("")
    lines.append(
        "Workload-heldout evaluation can be degenerate when only one workload has "
        "candidate rows. In that case the report records the limitation instead "
        "of treating the split as held-out evidence."
    )
    lines.append("")
    lines.append("## Current Split Shadow Metrics")
    lines.append("")
    lines.append("| Method | Precision | Recall | False positives | False negatives |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    lines.append(
        "| current_guard | "
        f"{metrics['current_guard_validation_precision']} | "
        f"{metrics['current_guard_validation_recall']} | "
        f"{metrics['current_guard_validation_false_positives']} | "
        f"{metrics['current_guard_validation_false_negatives']} |"
    )
    lines.append(
        "| learned_shadow_all_rows | "
        f"{metrics['all_row_validation_precision']} | "
        f"{metrics['all_row_validation_recall']} | "
        f"{metrics['all_row_validation_false_positives']} | "
        f"{metrics['all_row_validation_false_negatives']} |"
    )
    lines.append(
        "| learned_shadow_candidate_eligible | "
        f"{metrics['candidate_eligible_precision']} | "
        f"{metrics['candidate_eligible_recall_vs_all_positives']} | "
        f"{metrics['candidate_eligible_false_positive']} | "
        f"{metrics['candidate_eligible_false_negative_vs_all_positives']} |"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "This is a dataset expansion and split-discipline checkpoint, not a model "
        "promotion checkpoint. When requested hard-negative sources are absent "
        "from the source TSV, the correct result is an explicit zero count."
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
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source-dataset", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    try:
        dataset_path = Path(args.dataset).resolve()
        source_dataset_path = Path(args.source_dataset).resolve()
        report_path = Path(args.report).resolve()
        rows = read_rows(dataset_path)
        source_rows = read_rows(source_dataset_path)
        metrics = telemetry(rows, source_rows)
        report = render_report(
            dataset_path=dataset_path,
            source_dataset_path=source_dataset_path,
            rows=rows,
            source_rows=source_rows,
            metrics=metrics,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        for key, value in metrics.items():
            print(f"benchmark.fasim_sim_recovery_learned_detector_dataset_expansion.total.{key}={value}")
        print(report.rstrip())
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
