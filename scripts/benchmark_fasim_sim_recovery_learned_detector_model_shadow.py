#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import re
import zlib
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


FEATURE_COLUMNS = [
    "score",
    "Nt",
    "identity",
    "interval_length",
    "local_rank",
    "family_rank",
    "overlap_degree",
    "distance_to_fasim_boundary",
    "box_size",
]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_float(value: str) -> float:
    if value in ("", "NA", None):
        return 0.0
    return float(value)


def fmt(value: float) -> str:
    return f"{value:.6f}"


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("_") or "unknown"


def source_family_id(row: Dict[str, str]) -> str:
    return safe_id(
        "|".join(
            [
                row.get("rule", "NA"),
                row.get("strand", "NA"),
                row.get("direction", "NA"),
            ]
        )
    )


def split_for_key(split_key: str) -> str:
    return "validation" if zlib.crc32(split_key.encode("utf-8")) % 5 == 0 else "train"


def source_split(row: Dict[str, str]) -> str:
    split_key = f"{row.get('workload_label', '')}|{source_family_id(row)}"
    return split_for_key(split_key)


def label(row: Dict[str, str]) -> int:
    return 1 if row.get("label") == "1" else 0


def feature_values(row: Dict[str, str]) -> List[float]:
    return [parse_float(row.get(column, "0")) for column in FEATURE_COLUMNS]


def train_feature_stats(rows: Sequence[Dict[str, str]]) -> Tuple[List[float], List[float], List[float]]:
    if not rows:
        return ([0.0] * len(FEATURE_COLUMNS), [1.0] * len(FEATURE_COLUMNS), [0.0] * len(FEATURE_COLUMNS))

    matrix = [feature_values(row) for row in rows]
    means: List[float] = []
    stdevs: List[float] = []
    for column_index in range(len(FEATURE_COLUMNS)):
        values = [row[column_index] for row in matrix]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        means.append(mean)
        stdevs.append(math.sqrt(variance) or 1.0)

    positive_rows = [values for values, row in zip(matrix, rows) if label(row) == 1]
    negative_rows = [values for values, row in zip(matrix, rows) if label(row) == 0]
    weights: List[float] = []
    for column_index in range(len(FEATURE_COLUMNS)):
        if not positive_rows or not negative_rows:
            weights.append(0.0)
            continue
        pos_mean = sum(row[column_index] for row in positive_rows) / len(positive_rows)
        neg_mean = sum(row[column_index] for row in negative_rows) / len(negative_rows)
        weights.append((pos_mean - neg_mean) / stdevs[column_index])
    return (means, stdevs, weights)


def model_scores(
    rows: Sequence[Dict[str, str]],
    *,
    means: Sequence[float],
    stdevs: Sequence[float],
    weights: Sequence[float],
) -> List[float]:
    scores: List[float] = []
    for row in rows:
        values = feature_values(row)
        total = 0.0
        for value, mean, stdev, weight in zip(values, means, stdevs, weights):
            total += ((value - mean) / stdev) * weight
        scores.append(total)
    return scores


def evaluate(rows: Sequence[Dict[str, str]], scores: Sequence[float], threshold: float) -> Dict[str, str]:
    positives = sum(label(row) for row in rows)
    negatives = len(rows) - positives
    selected_pairs = [(row, score) for row, score in zip(rows, scores) if score >= threshold]
    selected = len(selected_pairs)
    true_positive = sum(label(row) for row, _ in selected_pairs)
    false_positive = selected - true_positive
    false_negative = positives - true_positive
    precision = true_positive / selected * 100.0 if selected else 0.0
    recall = true_positive / positives * 100.0 if positives else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall > 0.0
        else 0.0
    )
    return {
        "rows": str(len(rows)),
        "positive": str(positives),
        "negative": str(negatives),
        "selected": str(selected),
        "true_positive": str(true_positive),
        "false_positive": str(false_positive),
        "false_negative": str(false_negative),
        "precision": fmt(precision),
        "recall": fmt(recall),
        "f1": fmt(f1),
    }


def select_threshold(train_rows: Sequence[Dict[str, str]], train_scores: Sequence[float]) -> float:
    if not train_rows or not train_scores:
        return 0.0
    unique_scores = sorted(set(train_scores), reverse=True)
    candidates = [max(unique_scores) + 1.0] + unique_scores + [min(unique_scores) - 1.0]
    best_threshold = candidates[0]
    best_key = (-1.0, -1.0, -1.0, 0)
    for threshold in candidates:
        metrics = evaluate(train_rows, train_scores, threshold)
        selected = int(metrics["selected"])
        key = (
            parse_float(metrics["f1"]),
            parse_float(metrics["precision"]),
            parse_float(metrics["recall"]),
            -selected,
        )
        if key > best_key:
            best_key = key
            best_threshold = threshold
    return best_threshold


def current_guard_metrics(source_rows: Sequence[Dict[str, str]], split: str) -> Dict[str, str]:
    if not source_rows:
        return {
            "selected": "0",
            "true_positive": "0",
            "false_positive": "0",
            "false_negative": "0",
            "precision": fmt(0.0),
            "recall": fmt(0.0),
        }
    sim_records = [
        row
        for row in source_rows
        if row.get("source") == "sim_record"
        and row.get("label_available") == "1"
        and source_split(row) == split
    ]
    accepted = [
        row
        for row in source_rows
        if row.get("source") == "accepted_candidate"
        and row.get("label_available") == "1"
        and source_split(row) == split
    ]
    true_positive = sum(1 for row in accepted if row.get("label_in_sim") == "1")
    selected = len(accepted)
    positives = len(sim_records)
    false_positive = selected - true_positive
    false_negative = max(positives - true_positive, 0)
    precision = true_positive / selected * 100.0 if selected else 0.0
    recall = true_positive / positives * 100.0 if positives else 0.0
    return {
        "selected": str(selected),
        "true_positive": str(true_positive),
        "false_positive": str(false_positive),
        "false_negative": str(false_negative),
        "precision": fmt(precision),
        "recall": fmt(recall),
    }


def telemetry(
    *,
    rows: Sequence[Dict[str, str]],
    train_rows: Sequence[Dict[str, str]],
    validation_rows: Sequence[Dict[str, str]],
    validation_scores: Sequence[float],
    threshold: float,
    train_metrics: Dict[str, str],
    validation_metrics: Dict[str, str],
    current_guard_train: Dict[str, str],
    current_guard_validation: Dict[str, str],
) -> Dict[str, str]:
    labels = Counter(row.get("label", "0") for row in rows)
    source_counts = Counter(row.get("hard_negative_source", "NA") for row in rows if row.get("label") == "0")
    validation_positive = sum(label(row) for row in validation_rows)
    selected_validation = [
        row for row, score in zip(validation_rows, validation_scores) if score >= threshold
    ]
    selected_candidate_eligible = [
        row for row in selected_validation if row.get("source") != "sim_record_target_positive"
    ]
    candidate_eligible_tp = sum(label(row) for row in selected_candidate_eligible)
    candidate_eligible_selected = len(selected_candidate_eligible)
    candidate_eligible_fp = candidate_eligible_selected - candidate_eligible_tp
    candidate_eligible_fn = max(validation_positive - candidate_eligible_tp, 0)
    candidate_eligible_precision = (
        candidate_eligible_tp / candidate_eligible_selected * 100.0
        if candidate_eligible_selected
        else 0.0
    )
    candidate_eligible_recall = (
        candidate_eligible_tp / validation_positive * 100.0
        if validation_positive
        else 0.0
    )
    target_rows = [row for row in validation_rows if row.get("source") == "sim_record_target_positive"]
    selected_target_rows = [
        row for row in selected_validation if row.get("source") == "sim_record_target_positive"
    ]
    beats_guard = (
        candidate_eligible_recall > parse_float(current_guard_validation["recall"])
        and candidate_eligible_precision >= parse_float(current_guard_validation["precision"])
    )
    return {
        "enabled": "1",
        "rows": str(len(rows)),
        "positive_rows": str(labels.get("1", 0)),
        "negative_rows": str(labels.get("0", 0)),
        "learnable_two_class": "1" if labels.get("1", 0) and labels.get("0", 0) else "0",
        "evaluation_mode": "heldout_split",
        "model": "standardized_mean_difference_threshold",
        "heavy_ml_dependency": "0",
        "features": ",".join(FEATURE_COLUMNS),
        "train_positive": train_metrics["positive"],
        "train_negative": train_metrics["negative"],
        "validation_positive": validation_metrics["positive"],
        "validation_negative": validation_metrics["negative"],
        "selected_threshold": fmt(threshold),
        "train_selected": train_metrics["selected"],
        "train_precision": train_metrics["precision"],
        "train_recall": train_metrics["recall"],
        "train_false_positives": train_metrics["false_positive"],
        "train_false_negatives": train_metrics["false_negative"],
        "validation_selected": validation_metrics["selected"],
        "validation_precision": validation_metrics["precision"],
        "validation_recall": validation_metrics["recall"],
        "validation_false_positives": validation_metrics["false_positive"],
        "validation_false_negatives": validation_metrics["false_negative"],
        "validation_candidate_eligible_selected": str(candidate_eligible_selected),
        "validation_candidate_eligible_true_positive": str(candidate_eligible_tp),
        "validation_candidate_eligible_false_positive": str(candidate_eligible_fp),
        "validation_candidate_eligible_false_negative_vs_all_positives": str(candidate_eligible_fn),
        "validation_candidate_eligible_precision": fmt(candidate_eligible_precision),
        "validation_candidate_eligible_recall_vs_all_positives": fmt(candidate_eligible_recall),
        "validation_target_rows": str(len(target_rows)),
        "validation_target_rows_selected": str(len(selected_target_rows)),
        "current_guard_train_precision": current_guard_train["precision"],
        "current_guard_train_recall": current_guard_train["recall"],
        "current_guard_train_false_positives": current_guard_train["false_positive"],
        "current_guard_train_false_negatives": current_guard_train["false_negative"],
        "current_guard_validation_precision": current_guard_validation["precision"],
        "current_guard_validation_recall": current_guard_validation["recall"],
        "current_guard_validation_false_positives": current_guard_validation["false_positive"],
        "current_guard_validation_false_negatives": current_guard_validation["false_negative"],
        "beats_current_guard_on_validation": "1" if beats_guard else "0",
        "hard_negative_sources": ",".join(f"{key}:{value}" for key, value in sorted(source_counts.items())) or "none",
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
    }


def render_report(
    *,
    dataset_path: Path,
    source_dataset_path: Path | None,
    rows: Sequence[Dict[str, str]],
    metrics: Dict[str, str],
    weights: Sequence[float],
) -> str:
    split_counts = Counter((row.get("split", "NA"), row.get("label", "0")) for row in rows)
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Model Shadow")
    lines.append("")
    lines.append("## Offline Model Shadow")
    lines.append("")
    lines.append(
        "This report trains a dependency-free ranking/threshold shadow over the "
        "offline positive + hard-negative dataset. It is evaluated on the "
        "exported train/validation split and does not add a runtime model."
    )
    lines.append("")
    lines.append(f"Input negative dataset: `{dataset_path}`")
    if source_dataset_path is not None:
        lines.append(f"Input source learned dataset: `{source_dataset_path}`")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| fasim_sim_recovery_learned_detector_model_shadow_{key} | {value} |")
    lines.append("")
    lines.append("## Feature List")
    lines.append("")
    lines.append("| Feature | Weight |")
    lines.append("| --- | ---: |")
    for feature, weight in zip(FEATURE_COLUMNS, weights):
        lines.append(f"| {feature} | {fmt(weight)} |")
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
    lines.append("## Held-out Validation")
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
        f"{metrics['validation_precision']} | "
        f"{metrics['validation_recall']} | "
        f"{metrics['validation_false_positives']} | "
        f"{metrics['validation_false_negatives']} |"
    )
    lines.append(
        "| learned_shadow_candidate_eligible | "
        f"{metrics['validation_candidate_eligible_precision']} | "
        f"{metrics['validation_candidate_eligible_recall_vs_all_positives']} | "
        f"{metrics['validation_candidate_eligible_false_positive']} | "
        f"{metrics['validation_candidate_eligible_false_negative_vs_all_positives']} |"
    )
    lines.append("")
    lines.append("## Target Row Audit")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    lines.append(f"| validation target rows | {metrics['validation_target_rows']} |")
    lines.append(f"| validation target rows selected | {metrics['validation_target_rows_selected']} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "`evaluation_mode=heldout_split` means the selected threshold is fitted "
        "only on rows marked `split=train` and scored on rows marked "
        "`split=validation`."
    )
    lines.append("")
    lines.append(
        "This is still a small offline feasibility check. It must not be read as "
        "held-out production accuracy, especially when hard negatives come from "
        "a narrow source mix."
    )
    lines.append("")
    lines.append(
        "`learned_shadow_all_rows` includes `sim_record_target_positive` rows, "
        "which are offline oracle target rows used to study not-box-covered "
        "positives. `beats_current_guard_on_validation` is therefore computed "
        "from `learned_shadow_candidate_eligible`, not from the all-row target "
        "view."
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
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source-dataset")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    try:
        dataset_path = Path(args.dataset).resolve()
        source_dataset_path = Path(args.source_dataset).resolve() if args.source_dataset else None
        report_path = Path(args.report).resolve()
        rows = read_rows(dataset_path)
        source_rows = read_rows(source_dataset_path) if source_dataset_path is not None else []
        train_rows = [row for row in rows if row.get("split") == "train"]
        validation_rows = [row for row in rows if row.get("split") == "validation"]
        means, stdevs, weights = train_feature_stats(train_rows)
        train_scores = model_scores(train_rows, means=means, stdevs=stdevs, weights=weights)
        validation_scores = model_scores(validation_rows, means=means, stdevs=stdevs, weights=weights)
        threshold = select_threshold(train_rows, train_scores)
        train_metrics = evaluate(train_rows, train_scores, threshold)
        validation_metrics = evaluate(validation_rows, validation_scores, threshold)
        current_guard_train = current_guard_metrics(source_rows, "train")
        current_guard_validation = current_guard_metrics(source_rows, "validation")
        metrics = telemetry(
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
        report = render_report(
            dataset_path=dataset_path,
            source_dataset_path=source_dataset_path,
            rows=rows,
            metrics=metrics,
            weights=weights,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        for key, value in metrics.items():
            print(f"benchmark.fasim_sim_recovery_learned_detector_model_shadow.total.{key}={value}")
        print(report.rstrip())
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
