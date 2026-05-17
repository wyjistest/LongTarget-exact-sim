#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow as shadow  # noqa: E402


PREFIX = "benchmark.fasim_sim_recovery_learned_detector_precision_sweep.total"
REPORT_PREFIX = "fasim_sim_recovery_learned_detector_precision_sweep"
PRECISION_TARGETS = (90, 95, 99)


def pct(value: float) -> str:
    return f"{value:.6f}"


def parse_float(value: str) -> float:
    return shadow.parse_float(value)


def threshold_candidates(scores: Sequence[float]) -> List[float]:
    if not scores:
        return [0.0]
    unique_scores = sorted(set(scores), reverse=True)
    return [max(unique_scores) + 1.0] + unique_scores + [min(unique_scores) - 1.0]


def candidate_metrics_at_threshold(
    validation_rows: Sequence[Dict[str, str]],
    validation_scores: Sequence[float],
    threshold: float,
) -> Dict[str, Any]:
    positives = sum(shadow.model_shadow.label(row) for row in validation_rows)
    selected_rows = [
        row
        for row, score in zip(validation_rows, validation_scores)
        if score >= threshold and row.get("source") != "sim_record_target_positive"
    ]
    true_positive = sum(shadow.model_shadow.label(row) for row in selected_rows)
    selected = len(selected_rows)
    false_positive = selected - true_positive
    false_negative = max(positives - true_positive, 0)
    precision = true_positive / selected * 100.0 if selected else 0.0
    recall = true_positive / positives * 100.0 if positives else 0.0
    false_positive_rows = [
        row for row in selected_rows if shadow.model_shadow.label(row) == 0
    ]
    selected_ids = {row.get("candidate_id", "") for row in selected_rows}
    false_negative_rows = [
        row
        for row in validation_rows
        if shadow.model_shadow.label(row) == 1
        and row.get("candidate_id", "") not in selected_ids
    ]
    return {
        "threshold": pct(threshold),
        "selected": str(selected),
        "true_positive": str(true_positive),
        "false_positive": str(false_positive),
        "false_negative": str(false_negative),
        "precision": pct(precision),
        "recall": pct(recall),
        "_threshold_value": threshold,
        "_selected_rows": selected_rows,
        "_false_positive_rows": false_positive_rows,
        "_false_negative_rows": false_negative_rows,
    }


def sweep_thresholds(
    validation_rows: Sequence[Dict[str, str]],
    validation_scores: Sequence[float],
) -> List[Dict[str, Any]]:
    return [
        candidate_metrics_at_threshold(validation_rows, validation_scores, threshold)
        for threshold in threshold_candidates(validation_scores)
    ]


def best_for_precision(curve: Sequence[Dict[str, Any]], target: int) -> Dict[str, Any] | None:
    eligible = [
        row
        for row in curve
        if int(row["selected"]) > 0 and parse_float(row["precision"]) >= float(target)
    ]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda row: (
            parse_float(row["recall"]),
            parse_float(row["precision"]),
            -int(row["false_positive"]),
            row["_threshold_value"],
        ),
    )


def source_counts_string(rows: Sequence[Dict[str, str]], column: str) -> str:
    return shadow.source_counts_string(Counter(row.get(column, "unknown") for row in rows))


def current_guard_selection(
    source_rows: Sequence[Dict[str, str]],
    split: str,
) -> tuple[int, Dict[str, bool]]:
    sim_records = [
        row
        for row in source_rows
        if row.get("source") == "sim_record"
        and row.get("label_available") == "1"
        and shadow.workload_source_split(row) == split
    ]
    accepted = [
        row
        for row in source_rows
        if row.get("source") == "accepted_candidate"
        and row.get("label_available") == "1"
        and shadow.workload_source_split(row) == split
    ]
    selected: Dict[str, bool] = {}
    for row in accepted:
        candidate_id = row.get("candidate_id", "")
        if not candidate_id:
            continue
        selected[candidate_id] = selected.get(candidate_id, False) or row.get("label_in_sim") == "1"
    return len(sim_records), selected


def learned_selection(row_metrics: Dict[str, Any]) -> Dict[str, bool]:
    selected: Dict[str, bool] = {}
    for row in row_metrics.get("_selected_rows", []):
        candidate_id = row.get("candidate_id", "")
        if not candidate_id:
            continue
        selected[candidate_id] = selected.get(candidate_id, False) or shadow.model_shadow.label(row) == 1
    return selected


def selection_metrics(
    *,
    positives: int,
    selected: Dict[str, bool],
) -> Dict[str, str]:
    selected_count = len(selected)
    true_positive = sum(1 for value in selected.values() if value)
    false_positive = selected_count - true_positive
    capped_true_positive = min(true_positive, positives)
    false_negative = max(positives - capped_true_positive, 0)
    precision = true_positive / selected_count * 100.0 if selected_count else 0.0
    recall = capped_true_positive / positives * 100.0 if positives else 0.0
    return {
        "selected": str(selected_count),
        "true_positive": str(true_positive),
        "false_positive": str(false_positive),
        "false_negative": str(false_negative),
        "precision": pct(precision),
        "recall": pct(recall),
    }


def union_selection(left: Dict[str, bool], right: Dict[str, bool]) -> Dict[str, bool]:
    combined = dict(left)
    for key, value in right.items():
        combined[key] = combined.get(key, False) or value
    return combined


def intersection_selection(left: Dict[str, bool], right: Dict[str, bool]) -> Dict[str, bool]:
    return {
        key: left[key] or right[key]
        for key in sorted(set(left) & set(right))
    }


def target_value(row: Dict[str, Any] | None, key: str, default: str = "0.000000") -> str:
    if row is None:
        return "none" if key == "threshold" else default
    return str(row[key])


def build_metrics(
    *,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    data_metrics: Dict[str, str],
) -> tuple[Dict[str, str], List[Dict[str, Any]], Dict[int, Dict[str, Any] | None], Dict[str, Dict[str, str]]]:
    shadow.model_shadow.FEATURE_COLUMNS = list(shadow.EXPANDED_FEATURE_COLUMNS)
    labels = Counter(row.get("label", "0") for row in rows)
    hard_negative_sources = Counter(
        row.get("hard_negative_source", "unknown")
        for row in rows
        if row.get("label") == "0"
    )
    counts = shadow.split_counts(rows, shadow.workload_row_split)
    train_rows = [row for row in rows if shadow.workload_row_split(row) == "train"]
    validation_rows = [row for row in rows if shadow.workload_row_split(row) == "validation"]
    selected_threshold, validation_scores, _train_metrics, validation_metrics = shadow.train_and_score(
        train_rows,
        validation_rows,
    )
    learned_shadow = shadow.candidate_eligible_metrics(
        validation_rows=validation_rows,
        validation_scores=validation_scores,
        threshold=selected_threshold,
    )
    current_guard = shadow.current_guard_metrics_for_split(
        source_rows,
        shadow.workload_source_split,
        "validation",
    )
    curve = sweep_thresholds(validation_rows, validation_scores)
    target_rows = {target: best_for_precision(curve, target) for target in PRECISION_TARGETS}

    positives, current_selection = current_guard_selection(source_rows, "validation")
    learned_90_selection = learned_selection(target_rows[90]) if target_rows[90] else {}
    hybrid_policies = {
        "current_guard_only": selection_metrics(
            positives=positives,
            selected=current_selection,
        ),
        "learned_precision_90_only": selection_metrics(
            positives=positives,
            selected=learned_90_selection,
        ),
        "hybrid_or_precision_90": selection_metrics(
            positives=positives,
            selected=union_selection(current_selection, learned_90_selection),
        ),
        "hybrid_and_precision_90": selection_metrics(
            positives=positives,
            selected=intersection_selection(current_selection, learned_90_selection),
        ),
    }
    fp_rows_90 = target_rows[90].get("_false_positive_rows", []) if target_rows[90] else []
    fn_rows_90 = (
        target_rows[90].get("_false_negative_rows", [])
        if target_rows[90]
        else [row for row in validation_rows if shadow.model_shadow.label(row) == 1]
    )
    max_recall_90 = parse_float(target_value(target_rows[90], "recall"))
    hybrid_or_90 = hybrid_policies["hybrid_or_precision_90"]
    current_guard_recall = parse_float(current_guard["recall"])
    if (
        max_recall_90 > current_guard_recall
        or parse_float(hybrid_or_90["recall"]) > current_guard_recall
    ):
        decision = "continue_precision_constrained_shadow"
    else:
        decision = "pause_model_path_keep_guard"

    metrics = {
        "enabled": "1",
        "rows": str(len(rows)),
        "positive_rows": str(labels.get("1", 0)),
        "negative_rows": str(labels.get("0", 0)),
        "source_rows": str(len(source_rows)),
        "workload_count": str(len({row.get("workload_id", "unknown") for row in rows})),
        "validate_supported_workload_count": data_metrics.get("validate_supported_workload_count", "0"),
        "hard_negative_sources": shadow.source_counts_string(hard_negative_sources),
        "hard_negative_source_count": str(sum(1 for value in hard_negative_sources.values() if value)),
        "evaluation_policy": "workload_heldout",
        "train_positive": counts["train_positive"],
        "train_negative": counts["train_negative"],
        "validation_positive": counts["validation_positive"],
        "validation_negative": counts["validation_negative"],
        "workload_heldout_degenerate": counts["degenerate"],
        "sweep_threshold_count": str(len(curve)),
        "selected_threshold": pct(selected_threshold),
        "current_guard_recall": current_guard["recall"],
        "current_guard_precision": current_guard["precision"],
        "current_guard_false_positives": current_guard["false_positive"],
        "current_guard_false_negatives": current_guard["false_negative"],
        "learned_shadow_recall": learned_shadow["recall"],
        "learned_shadow_precision": learned_shadow["precision"],
        "learned_shadow_false_positives": learned_shadow["false_positive"],
        "learned_shadow_false_negatives": learned_shadow["false_negative"],
        "false_positives_by_negative_source": source_counts_string(fp_rows_90, "hard_negative_source"),
        "false_negatives_by_workload": source_counts_string(fn_rows_90, "workload_id"),
        "decision": decision,
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
        "model_training_added": "0",
        "deep_learning_dependency": "0",
        "recommended_default_sim_close": "0",
    }
    for target, row in target_rows.items():
        metrics[f"max_recall_at_precision_{target}"] = target_value(row, "recall")
        metrics[f"precision_at_precision_{target}"] = target_value(row, "precision")
        metrics[f"threshold_at_precision_{target}"] = target_value(row, "threshold")
        metrics[f"false_positives_at_precision_{target}"] = target_value(row, "false_positive", "0")
        metrics[f"false_negatives_at_precision_{target}"] = (
            target_value(row, "false_negative", "0")
            if row
            else counts["validation_positive"]
        )
    for policy_name, policy in hybrid_policies.items():
        for key, value in policy.items():
            metrics[f"{policy_name}_{key}"] = value
    return metrics, curve, target_rows, hybrid_policies


def append_metric_table(lines: List[str], metrics: Dict[str, str]) -> None:
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| {REPORT_PREFIX}_{key} | {value} |")


def render_curve(lines: List[str], curve: Sequence[Dict[str, Any]]) -> None:
    lines.append("| Threshold | Selected | Precision | Recall | False + | False - |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in curve:
        lines.append(
            f"| {row['threshold']} | {row['selected']} | {row['precision']} | "
            f"{row['recall']} | {row['false_positive']} | {row['false_negative']} |"
        )


def render_targets(
    lines: List[str],
    *,
    target_rows: Dict[int, Dict[str, Any] | None],
    metrics: Dict[str, str],
) -> None:
    lines.append("| Precision target | Threshold | Precision | Max recall | False + | False - |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for target in PRECISION_TARGETS:
        row = target_rows[target]
        lines.append(
            f"| >= {target}% | {target_value(row, 'threshold')} | "
            f"{target_value(row, 'precision')} | {target_value(row, 'recall')} | "
            f"{metrics[f'false_positives_at_precision_{target}']} | "
            f"{metrics[f'false_negatives_at_precision_{target}']} |"
        )


def render_hybrid(lines: List[str], hybrid_policies: Dict[str, Dict[str, str]]) -> None:
    lines.append("| Policy | Selected | Precision | Recall | False + | False - |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for name in (
        "current_guard_only",
        "learned_precision_90_only",
        "hybrid_or_precision_90",
        "hybrid_and_precision_90",
    ):
        policy = hybrid_policies[name]
        lines.append(
            f"| {name} | {policy['selected']} | {policy['precision']} | "
            f"{policy['recall']} | {policy['false_positive']} | {policy['false_negative']} |"
        )


def render_report(
    *,
    metrics: Dict[str, str],
    curve: Sequence[Dict[str, Any]],
    target_rows: Dict[int, Dict[str, Any] | None],
    hybrid_policies: Dict[str, Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Precision Sweep")
    lines.append("")
    lines.append("## Precision-Constrained Threshold Sweep")
    lines.append("")
    lines.append(
        "This report sweeps thresholds for the dependency-free learned/ranked "
        "detector shadow on the #92 large-corpus workload-heldout split. The "
        "thresholds are validation-label characterizations only; they are not "
        "runtime thresholds and are not production detector inputs."
    )
    lines.append("")
    append_metric_table(lines, metrics)
    lines.append("")
    lines.append("## Precision Targets")
    lines.append("")
    render_targets(lines, target_rows=target_rows, metrics=metrics)
    lines.append("")
    lines.append("## Precision/Recall Curve")
    lines.append("")
    render_curve(lines, curve)
    lines.append("")
    lines.append("## Hybrid Policies")
    lines.append("")
    lines.append(
        "`learned_precision_90_only` uses the best offline learned threshold "
        "with precision >= 90%. Hybrid policies are offline comparisons against "
        "the current hand-written guard and do not change runtime behavior."
    )
    lines.append("")
    render_hybrid(lines, hybrid_policies)
    lines.append("")
    lines.append("## Error Attribution")
    lines.append("")
    lines.append("| Error bucket | Rows |")
    lines.append("| --- | --- |")
    lines.append(f"| false_positives_by_negative_source | {metrics['false_positives_by_negative_source']} |")
    lines.append(f"| false_negatives_by_workload | {metrics['false_negatives_by_workload']} |")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"Decision: `{metrics['decision']}`.")
    lines.append("")
    lines.append(
        "If learned or hybrid policy beats the current guard at precision >= 90%, "
        "the learned-detector research line remains worth offline follow-up. If "
        "recall falls below the current guard once precision is constrained, keep "
        "the hand-written guard and collect better signal."
    )
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("```text")
    lines.append("Production model added: no")
    lines.append("Runtime model added: no")
    lines.append("Deep learning dependency added: no")
    lines.append("Fasim runtime changed: no")
    lines.append("SIM-close runtime changed: no")
    lines.append("Scoring/threshold/non-overlap behavior changed: no")
    lines.append("GPU/filter behavior changed: no")
    lines.append("SIM labels used as runtime input: no")
    lines.append("Recommended/default SIM-close: no")
    lines.append("```")
    lines.append("")
    lines.append(
        "No production model is trained or loaded. SIM labels remain offline "
        "labels only and must not be used as runtime detector inputs, guard "
        "inputs, replacement inputs, or output ordering inputs."
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source-dataset", required=True)
    parser.add_argument("--data-expansion-log", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--doc-report", default="")
    args = parser.parse_args()

    rows = shadow.read_rows(Path(args.dataset).resolve())
    source_rows = shadow.read_rows(Path(args.source_dataset).resolve())
    data_metrics = shadow.read_metric_log(Path(args.data_expansion_log).resolve())
    metrics, curve, target_rows, hybrid_policies = build_metrics(
        rows=rows,
        source_rows=source_rows,
        data_metrics=data_metrics,
    )
    report = render_report(
        metrics=metrics,
        curve=curve,
        target_rows=target_rows,
        hybrid_policies=hybrid_policies,
    )

    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    if args.doc_report:
        doc_report_path = Path(args.doc_report).resolve()
        doc_report_path.parent.mkdir(parents=True, exist_ok=True)
        doc_report_path.write_text(report, encoding="utf-8")
    for key, value in metrics.items():
        print(f"{PREFIX}.{key}={value}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
