#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow as shadow  # noqa: E402


PREFIX = "benchmark.fasim_sim_recovery_learned_detector_large_corpus_model_shadow.total"
REPORT_PREFIX = "fasim_sim_recovery_learned_detector_large_corpus_model_shadow"
BASELINE_90_PREFIX = "fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow"


def baseline_90_metrics() -> Dict[str, str]:
    rows = shadow.metric_report_rows(
        ROOT / "docs" / "fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.md"
    )
    def get(key: str, default: str = "0") -> str:
        return rows.get(f"{BASELINE_90_PREFIX}_{key}", default)

    return {
        "rows": get("rows"),
        "positive_rows": get("positive_rows"),
        "negative_rows": get("negative_rows"),
        "workload_count": get("workload_count"),
        "hard_negative_source_count": get("hard_negative_source_count"),
        "current_guard_precision": get("current_guard_precision", "0.000000"),
        "current_guard_recall": get("current_guard_recall", "0.000000"),
        "learned_shadow_precision": get("learned_shadow_precision", "0.000000"),
        "learned_shadow_recall": get("learned_shadow_recall", "0.000000"),
        "candidate_eligible_precision": get("candidate_eligible_precision", "0.000000"),
        "candidate_eligible_recall": get("candidate_eligible_recall", "0.000000"),
        "decision": get("decision", "unknown"),
    }


def build_metrics(
    *,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    data_metrics: Dict[str, str],
) -> tuple[
    Dict[str, str],
    Dict[str, Dict[str, Any]],
    List[Dict[str, str]],
    int,
    Dict[str, Dict[str, str]],
    Dict[str, str],
]:
    metrics, policies, loo_rows, loo_skipped, baselines = shadow.build_metrics(
        rows=rows,
        source_rows=source_rows,
        data_metrics=data_metrics,
    )
    baseline_90 = baseline_90_metrics()
    metrics["source_rows"] = str(len(source_rows))
    for key, value in baseline_90.items():
        metrics[f"baseline_90_{key}"] = value
    return metrics, policies, loo_rows, loo_skipped, baselines, baseline_90


def append_metric_table(lines: List[str], metrics: Dict[str, str]) -> None:
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| {REPORT_PREFIX}_{key} | {value} |")


def render_split_table(lines: List[str], policies: Dict[str, Dict[str, Any]]) -> None:
    lines.append(
        "| Policy | Train + | Train - | Validation + | Validation - | Degenerate | "
        "Current guard precision | Current guard recall | Learned precision | "
        "Learned recall | Candidate precision | Candidate recall | False + | False - | Threshold |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for policy_name in (
        "current_split",
        "workload_heldout",
        "family_heldout",
        "negative_source_heldout",
    ):
        policy = policies[policy_name]
        lines.append(
            f"| {policy_name} | {policy['train_positive']} | {policy['train_negative']} | "
            f"{policy['validation_positive']} | {policy['validation_negative']} | "
            f"{policy['degenerate']} | {policy['current_guard_precision']} | "
            f"{policy['current_guard_recall']} | {policy['learned_shadow_precision']} | "
            f"{policy['learned_shadow_recall']} | {policy['candidate_eligible_precision']} | "
            f"{policy['candidate_eligible_recall']} | {policy['candidate_eligible_false_positives']} | "
            f"{policy['candidate_eligible_false_negatives']} | {policy['selected_threshold']} |"
        )


def render_negative_source(lines: List[str], policies: Dict[str, Dict[str, Any]]) -> None:
    negative_source = policies["negative_source_heldout"]
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in (
        "train_positive",
        "train_negative",
        "validation_positive",
        "validation_negative",
        "degenerate",
        "current_guard_precision",
        "current_guard_recall",
        "candidate_eligible_precision",
        "candidate_eligible_recall",
        "candidate_eligible_false_positives",
        "candidate_eligible_false_negatives",
        "selected_threshold",
    ):
        lines.append(f"| {key} | {negative_source[key]} |")


def render_loo(
    lines: List[str],
    *,
    loo_rows: Sequence[Dict[str, str]],
    loo_skipped: int,
) -> None:
    lines.append(f"Skipped degenerate workloads: `{loo_skipped}`.")
    lines.append("")
    lines.append(
        "| Workload | Train + | Train - | Validation + | Validation - | Current guard precision | "
        "Current guard recall | Candidate precision | Candidate recall | False + | False - | Threshold |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    if not loo_rows:
        lines.append("| none | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |")
        return
    for row in loo_rows:
        lines.append(
            f"| {row['workload_id']} | {row['train_positive']} | {row['train_negative']} | "
            f"{row['validation_positive']} | {row['validation_negative']} | "
            f"{row['current_guard_precision']} | {row['current_guard_recall']} | "
            f"{row['candidate_eligible_precision']} | {row['candidate_eligible_recall']} | "
            f"{row['false_positives']} | {row['false_negatives']} | {row['selected_threshold']} |"
        )


def render_baselines(
    lines: List[str],
    *,
    metrics: Dict[str, str],
    baselines: Dict[str, Dict[str, str]],
    baseline_90: Dict[str, str],
) -> None:
    lines.append("| Source | Rows | Current guard precision | Current guard recall | Learned precision | Learned recall | Decision |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for name, baseline in baselines.items():
        lines.append(
            f"| {name} | {baseline['rows']} | {baseline['current_guard_precision']} | "
            f"{baseline['current_guard_recall']} | {baseline['learned_shadow_precision']} | "
            f"{baseline['learned_shadow_recall']} | historical |"
        )
    lines.append(
        f"| #90_expanded_hard_negative_primary | {baseline_90['rows']} | "
        f"{baseline_90['current_guard_precision']} | {baseline_90['current_guard_recall']} | "
        f"{baseline_90['learned_shadow_precision']} | {baseline_90['learned_shadow_recall']} | "
        f"{baseline_90['decision']} |"
    )
    lines.append(
        f"| #91_large_corpus_primary | {metrics['rows']} | "
        f"{metrics['current_guard_precision']} | {metrics['current_guard_recall']} | "
        f"{metrics['candidate_eligible_precision']} | {metrics['candidate_eligible_recall']} | "
        f"{metrics['decision']} |"
    )


def render_report(
    *,
    metrics: Dict[str, str],
    policies: Dict[str, Dict[str, Any]],
    loo_rows: Sequence[Dict[str, str]],
    loo_skipped: int,
    baselines: Dict[str, Dict[str, str]],
    baseline_90: Dict[str, str],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Large Corpus Model Shadow")
    lines.append("")
    lines.append("## Large Corpus Model Shadow")
    lines.append("")
    lines.append(
        "This report evaluates the dependency-free learned/ranked detector shadow "
        "on the #91 large corpus. It is an offline evaluation only: no runtime "
        "model is trained or loaded, and Fasim/SIM-close runtime behavior is unchanged."
    )
    lines.append("")
    append_metric_table(lines, metrics)
    lines.append("")
    lines.append("## Split Evaluation")
    lines.append("")
    render_split_table(lines, policies)
    lines.append("")
    lines.append("## Negative-Source Held-Out")
    lines.append("")
    render_negative_source(lines, policies)
    lines.append("")
    lines.append("## Error Attribution")
    lines.append("")
    lines.append("| Error bucket | Rows |")
    lines.append("| --- | --- |")
    lines.append(f"| false_positives_by_negative_source | {metrics['false_positives_by_negative_source']} |")
    lines.append(f"| false_negatives_by_workload | {metrics['false_negatives_by_workload']} |")
    lines.append(f"| no_legacy_proxy_false_positives | {metrics['no_legacy_proxy_false_positives']} |")
    lines.append("")
    lines.append("## Leave-One-Workload-Out")
    lines.append("")
    render_loo(lines, loo_rows=loo_rows, loo_skipped=loo_skipped)
    lines.append("")
    lines.append("## Baseline Comparison")
    lines.append("")
    render_baselines(
        lines,
        metrics=metrics,
        baselines=baselines,
        baseline_90=baseline_90,
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"Decision: `{metrics['decision']}`.")
    lines.append("")
    lines.append(
        "The decision is based on candidate-eligible held-out metrics. If only "
        "current-split/resubstitution improves, this is not evidence for runtime "
        "promotion. If learned shadow still loses to the hand-written guard, keep "
        "the guard and collect better signal before revisiting runtime work."
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

    dataset_path = Path(args.dataset).resolve()
    source_dataset_path = Path(args.source_dataset).resolve()
    data_expansion_log = Path(args.data_expansion_log).resolve()
    report_path = Path(args.report).resolve()

    rows = shadow.read_rows(dataset_path)
    source_rows = shadow.read_rows(source_dataset_path)
    missing = [
        feature
        for feature in shadow.EXPANDED_FEATURE_COLUMNS
        if rows and feature not in rows[0]
    ]
    if missing:
        raise RuntimeError("missing feature columns: " + ",".join(missing))
    data_metrics = shadow.read_metric_log(data_expansion_log)
    metrics, policies, loo_rows, loo_skipped, baselines, baseline_90 = build_metrics(
        rows=rows,
        source_rows=source_rows,
        data_metrics=data_metrics,
    )
    report = render_report(
        metrics=metrics,
        policies=policies,
        loo_rows=loo_rows,
        loo_skipped=loo_skipped,
        baselines=baselines,
        baseline_90=baseline_90,
    )

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
