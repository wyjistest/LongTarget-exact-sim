#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Sequence


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_fasim_sim_recovery_learned_detector_model_shadow as model_shadow  # noqa: E402


PolicySplit = Callable[[Dict[str, str]], str]


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def fmt(value: float) -> str:
    return f"{value:.6f}"


def parse_float(value: str) -> float:
    if value in ("", "NA", None):
        return 0.0
    return float(value)


def split_for_key(split_key: str) -> str:
    return model_shadow.split_for_key(split_key)


def current_row_split(row: Dict[str, str]) -> str:
    return row.get("split", "train")


def workload_row_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("workload_id", "unknown"))


def family_row_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("family_id", "unknown"))


def current_source_split(row: Dict[str, str]) -> str:
    return model_shadow.source_split(row)


def workload_source_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("workload_label", "unknown"))


def family_source_split(row: Dict[str, str]) -> str:
    return split_for_key(model_shadow.source_family_id(row))


def split_counts(rows: Sequence[Dict[str, str]], split_func: PolicySplit) -> Dict[str, str]:
    counts = Counter((split_func(row), row.get("label", "0")) for row in rows)
    train_positive = counts.get(("train", "1"), 0)
    train_negative = counts.get(("train", "0"), 0)
    validation_positive = counts.get(("validation", "1"), 0)
    validation_negative = counts.get(("validation", "0"), 0)
    degenerate = int(
        train_positive == 0
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


def current_guard_metrics_for_split(
    source_rows: Sequence[Dict[str, str]],
    split_func: PolicySplit,
    split: str,
) -> Dict[str, str]:
    sim_records = [
        row
        for row in source_rows
        if row.get("source") == "sim_record"
        and row.get("label_available") == "1"
        and split_func(row) == split
    ]
    accepted = [
        row
        for row in source_rows
        if row.get("source") == "accepted_candidate"
        and row.get("label_available") == "1"
        and split_func(row) == split
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


def candidate_eligible_metrics(
    *,
    validation_rows: Sequence[Dict[str, str]],
    validation_scores: Sequence[float],
    threshold: float,
) -> Dict[str, str]:
    validation_positive = sum(model_shadow.label(row) for row in validation_rows)
    selected = [
        row for row, score in zip(validation_rows, validation_scores) if score >= threshold
    ]
    selected_candidate_eligible = [
        row for row in selected if row.get("source") != "sim_record_target_positive"
    ]
    true_positive = sum(model_shadow.label(row) for row in selected_candidate_eligible)
    selected_count = len(selected_candidate_eligible)
    false_positive = selected_count - true_positive
    false_negative = max(validation_positive - true_positive, 0)
    precision = true_positive / selected_count * 100.0 if selected_count else 0.0
    recall = true_positive / validation_positive * 100.0 if validation_positive else 0.0
    return {
        "selected": str(selected_count),
        "true_positive": str(true_positive),
        "false_positive": str(false_positive),
        "false_negative": str(false_negative),
        "precision": fmt(precision),
        "recall": fmt(recall),
    }


def evaluate_policy(
    *,
    name: str,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    row_split_func: PolicySplit,
    source_split_func: PolicySplit,
) -> Dict[str, str]:
    counts = split_counts(rows, row_split_func)
    train_rows = [row for row in rows if row_split_func(row) == "train"]
    validation_rows = [row for row in rows if row_split_func(row) == "validation"]
    means, stdevs, weights = model_shadow.train_feature_stats(train_rows)
    train_scores = model_shadow.model_scores(
        train_rows,
        means=means,
        stdevs=stdevs,
        weights=weights,
    )
    validation_scores = model_shadow.model_scores(
        validation_rows,
        means=means,
        stdevs=stdevs,
        weights=weights,
    )
    threshold = model_shadow.select_threshold(train_rows, train_scores)
    train_metrics = model_shadow.evaluate(train_rows, train_scores, threshold)
    validation_metrics = model_shadow.evaluate(validation_rows, validation_scores, threshold)
    candidate_metrics = candidate_eligible_metrics(
        validation_rows=validation_rows,
        validation_scores=validation_scores,
        threshold=threshold,
    )
    current_guard_train = current_guard_metrics_for_split(source_rows, source_split_func, "train")
    current_guard_validation = current_guard_metrics_for_split(
        source_rows,
        source_split_func,
        "validation",
    )
    beats_guard = (
        parse_float(candidate_metrics["recall"]) > parse_float(current_guard_validation["recall"])
        and parse_float(candidate_metrics["precision"])
        >= parse_float(current_guard_validation["precision"])
    )
    return {
        "name": name,
        **counts,
        "selected_threshold": fmt(threshold),
        "train_precision": train_metrics["precision"],
        "train_recall": train_metrics["recall"],
        "train_false_positives": train_metrics["false_positive"],
        "train_false_negatives": train_metrics["false_negative"],
        "learned_shadow_precision": validation_metrics["precision"],
        "learned_shadow_recall": validation_metrics["recall"],
        "false_positives": validation_metrics["false_positive"],
        "false_negatives": validation_metrics["false_negative"],
        "candidate_eligible_precision": candidate_metrics["precision"],
        "candidate_eligible_recall": candidate_metrics["recall"],
        "candidate_eligible_false_positives": candidate_metrics["false_positive"],
        "candidate_eligible_false_negatives": candidate_metrics["false_negative"],
        "current_guard_train_precision": current_guard_train["precision"],
        "current_guard_train_recall": current_guard_train["recall"],
        "current_guard_train_false_positives": current_guard_train["false_positive"],
        "current_guard_train_false_negatives": current_guard_train["false_negative"],
        "current_guard_precision": current_guard_validation["precision"],
        "current_guard_recall": current_guard_validation["recall"],
        "current_guard_false_positives": current_guard_validation["false_positive"],
        "current_guard_false_negatives": current_guard_validation["false_negative"],
        "beats_current_guard_on_validation": "1" if beats_guard else "0",
    }


def read_metric_log(path: Path) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if ".total." not in key:
            continue
        metrics[key.rsplit(".total.", 1)[1]] = value
    return metrics


def source_counts_string(counts: Counter[str]) -> str:
    return ",".join(f"{key}:{value}" for key, value in sorted(counts.items()) if value) or "none"


def choose_primary(policies: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    for name in ("workload_heldout", "family_heldout", "current_split"):
        if policies[name]["degenerate"] == "0":
            return policies[name]
    return policies["current_split"]


def build_metrics(
    *,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    previous_metrics: Dict[str, str],
) -> tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
    labels = Counter(row.get("label", "0") for row in rows)
    hard_negative_sources = Counter(
        row.get("hard_negative_source", "NA") for row in rows if row.get("label") == "0"
    )
    policies = {
        "current_split": evaluate_policy(
            name="current_split",
            rows=rows,
            source_rows=source_rows,
            row_split_func=current_row_split,
            source_split_func=current_source_split,
        ),
        "workload_heldout": evaluate_policy(
            name="workload_heldout",
            rows=rows,
            source_rows=source_rows,
            row_split_func=workload_row_split,
            source_split_func=workload_source_split,
        ),
        "family_heldout": evaluate_policy(
            name="family_heldout",
            rows=rows,
            source_rows=source_rows,
            row_split_func=family_row_split,
            source_split_func=family_source_split,
        ),
    }
    primary = choose_primary(policies)
    expanded_corpus_available = int(
        len({row.get("workload_id", "unknown") for row in rows}) >= 3
        and hard_negative_sources.get("no_legacy_sim_records_proxy", 0) > 0
    )
    decision = "collect_more_data"
    if primary["name"] == "workload_heldout" and primary["degenerate"] == "0":
        decision = (
            "collect_better_features"
            if primary["beats_current_guard_on_validation"] == "0"
            else "expand_features_or_real_corpus"
        )
    elif policies["workload_heldout"]["degenerate"] != "0":
        decision = "collect_more_workloads"

    metrics = {
        "enabled": "1",
        "rows": str(len(rows)),
        "positive_rows": str(labels.get("1", 0)),
        "negative_rows": str(labels.get("0", 0)),
        "hard_negative_sources": source_counts_string(hard_negative_sources),
        "hard_negative_source_count": str(sum(1 for count in hard_negative_sources.values() if count)),
        "expanded_corpus_available": str(expanded_corpus_available),
        "evaluation_policy": primary["name"],
        "train_positive": primary["train_positive"],
        "train_negative": primary["train_negative"],
        "validation_positive": primary["validation_positive"],
        "validation_negative": primary["validation_negative"],
        "current_split_degenerate": policies["current_split"]["degenerate"],
        "workload_heldout_degenerate": policies["workload_heldout"]["degenerate"],
        "family_heldout_degenerate": policies["family_heldout"]["degenerate"],
        "current_guard_recall": primary["current_guard_recall"],
        "current_guard_precision": primary["current_guard_precision"],
        "current_guard_false_positives": primary["current_guard_false_positives"],
        "current_guard_false_negatives": primary["current_guard_false_negatives"],
        "learned_shadow_recall": primary["learned_shadow_recall"],
        "learned_shadow_precision": primary["learned_shadow_precision"],
        "false_positives": primary["false_positives"],
        "false_negatives": primary["false_negatives"],
        "selected_threshold": primary["selected_threshold"],
        "candidate_eligible_recall": primary["candidate_eligible_recall"],
        "candidate_eligible_precision": primary["candidate_eligible_precision"],
        "candidate_eligible_false_positives": primary["candidate_eligible_false_positives"],
        "candidate_eligible_false_negatives": primary["candidate_eligible_false_negatives"],
        "beats_current_guard_on_validation": primary["beats_current_guard_on_validation"],
        "previous_small_dataset_rows": previous_metrics.get("rows", "0"),
        "previous_small_dataset_learned_shadow_recall": previous_metrics.get(
            "validation_candidate_eligible_recall_vs_all_positives",
            previous_metrics.get("validation_recall", "0.000000"),
        ),
        "previous_small_dataset_learned_shadow_precision": previous_metrics.get(
            "validation_candidate_eligible_precision",
            previous_metrics.get("validation_precision", "0.000000"),
        ),
        "previous_small_dataset_current_guard_recall": previous_metrics.get(
            "current_guard_validation_recall",
            "0.000000",
        ),
        "previous_small_dataset_current_guard_precision": previous_metrics.get(
            "current_guard_validation_precision",
            "0.000000",
        ),
        "decision": decision,
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
    }
    for policy_name, policy in policies.items():
        for key in (
            "train_positive",
            "train_negative",
            "validation_positive",
            "validation_negative",
            "degenerate",
            "selected_threshold",
            "current_guard_precision",
            "current_guard_recall",
            "learned_shadow_precision",
            "learned_shadow_recall",
            "candidate_eligible_precision",
            "candidate_eligible_recall",
            "false_positives",
            "false_negatives",
        ):
            metrics[f"{policy_name}_{key}"] = policy[key]
    return metrics, policies


def render_report(
    *,
    metrics: Dict[str, str],
    policies: Dict[str, Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Expanded Model Shadow")
    lines.append("")
    lines.append("## Expanded Corpus Model Shadow")
    lines.append("")
    lines.append(
        "This report evaluates the dependency-free learned/ranked detector shadow "
        "on the expanded offline corpus. It does not train or load a runtime "
        "model and does not change Fasim or SIM-close runtime behavior."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| fasim_sim_recovery_learned_detector_expanded_model_shadow_{key} | {value} |")
    lines.append("")
    lines.append("## Split Evaluation")
    lines.append("")
    lines.append(
        "| Policy | Train + | Train - | Validation + | Validation - | Degenerate | "
        "Current guard precision | Current guard recall | Learned precision | "
        "Learned recall | Candidate precision | Candidate recall | Threshold |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for policy_name in ("current_split", "workload_heldout", "family_heldout"):
        policy = policies[policy_name]
        lines.append(
            f"| {policy_name} | {policy['train_positive']} | {policy['train_negative']} | "
            f"{policy['validation_positive']} | {policy['validation_negative']} | "
            f"{policy['degenerate']} | {policy['current_guard_precision']} | "
            f"{policy['current_guard_recall']} | {policy['learned_shadow_precision']} | "
            f"{policy['learned_shadow_recall']} | {policy['candidate_eligible_precision']} | "
            f"{policy['candidate_eligible_recall']} | {policy['selected_threshold']} |"
        )
    lines.append("")
    lines.append("## Previous Small-Dataset Shadow Comparison")
    lines.append("")
    lines.append("| Source | Current guard precision | Current guard recall | Learned precision | Learned recall | Rows |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    lines.append(
        "| previous_small_dataset | "
        f"{metrics['previous_small_dataset_current_guard_precision']} | "
        f"{metrics['previous_small_dataset_current_guard_recall']} | "
        f"{metrics['previous_small_dataset_learned_shadow_precision']} | "
        f"{metrics['previous_small_dataset_learned_shadow_recall']} | "
        f"{metrics['previous_small_dataset_rows']} |"
    )
    lines.append(
        "| expanded_primary | "
        f"{metrics['current_guard_precision']} | {metrics['current_guard_recall']} | "
        f"{metrics['candidate_eligible_precision']} | {metrics['candidate_eligible_recall']} | "
        f"{metrics['rows']} |"
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"Decision: `{metrics['decision']}`.")
    lines.append("")
    lines.append(
        "If held-out recall only improves by using oracle-only target rows, the "
        "candidate-eligible metrics remain the relevant runtime-feasible view. "
        "If the learned shadow cannot beat the current guard on that view, keep "
        "the hand-written guard and collect better features or more real-corpus "
        "contrastive data."
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
    parser.add_argument("--previous-model-shadow-log", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--doc-report", default="")
    args = parser.parse_args()

    try:
        dataset_path = Path(args.dataset).resolve()
        source_dataset_path = Path(args.source_dataset).resolve()
        previous_log_path = Path(args.previous_model_shadow_log).resolve()
        report_path = Path(args.report).resolve()
        rows = read_rows(dataset_path)
        source_rows = read_rows(source_dataset_path)
        previous_metrics = read_metric_log(previous_log_path)
        metrics, policies = build_metrics(
            rows=rows,
            source_rows=source_rows,
            previous_metrics=previous_metrics,
        )
        report = render_report(metrics=metrics, policies=policies)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        if args.doc_report:
            doc_report_path = Path(args.doc_report).resolve()
            doc_report_path.parent.mkdir(parents=True, exist_ok=True)
            doc_report_path.write_text(report, encoding="utf-8")
        for key, value in metrics.items():
            print(
                "benchmark.fasim_sim_recovery_learned_detector_expanded_model_shadow."
                f"total.{key}={value}"
            )
        print(report.rstrip())
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
