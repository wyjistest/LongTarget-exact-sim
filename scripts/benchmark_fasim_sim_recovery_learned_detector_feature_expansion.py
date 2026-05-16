#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_fasim_sim_recovery_learned_detector_expanded_model_shadow as expanded_shadow  # noqa: E402
import benchmark_fasim_sim_recovery_learned_detector_model_shadow as model_shadow  # noqa: E402


BASE_FEATURE_COLUMNS = [
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

NEW_FEATURE_COLUMNS = [
    "family_size",
    "family_span",
    "interval_overlap_ratio",
    "dominance_margin",
    "score_margin",
    "Nt_margin",
    "near_threshold_density",
    "peak_count",
    "second_peak_gap",
    "plateau_width",
]

EXPANDED_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + NEW_FEATURE_COLUMNS


def build_feature_metrics(
    *,
    rows: List[Dict[str, str]],
    source_rows: List[Dict[str, str]],
    baseline_metrics: Dict[str, str],
) -> tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
    model_shadow.FEATURE_COLUMNS = list(EXPANDED_FEATURE_COLUMNS)
    metrics, policies = expanded_shadow.build_metrics(
        rows=rows,
        source_rows=source_rows,
        previous_metrics={},
    )
    for key in list(metrics):
        if key.startswith("previous_small_dataset_"):
            del metrics[key]
    if metrics["beats_current_guard_on_validation"] == "1":
        decision = "continue_learned_detector_research"
    elif metrics["workload_heldout_degenerate"] == "1":
        decision = "collect_more_workloads"
    else:
        decision = "pause_model_path_keep_guard"

    metrics.update(
        {
            "expanded_feature_count": str(len(EXPANDED_FEATURE_COLUMNS)),
            "expanded_features": ",".join(EXPANDED_FEATURE_COLUMNS),
            "new_feature_count": str(len(NEW_FEATURE_COLUMNS)),
            "new_features": ",".join(NEW_FEATURE_COLUMNS),
            "baseline_expanded_shadow_recall": baseline_metrics.get(
                "learned_shadow_recall",
                "0.000000",
            ),
            "baseline_expanded_shadow_precision": baseline_metrics.get(
                "learned_shadow_precision",
                "0.000000",
            ),
            "baseline_current_guard_recall": baseline_metrics.get(
                "current_guard_recall",
                "0.000000",
            ),
            "baseline_current_guard_precision": baseline_metrics.get(
                "current_guard_precision",
                "0.000000",
            ),
            "decision": decision,
            "production_model": "0",
            "sim_labels_runtime_inputs": "0",
            "runtime_behavior_changed": "0",
        }
    )
    return metrics, policies


def render_report(
    *,
    metrics: Dict[str, str],
    policies: Dict[str, Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Feature Expansion")
    lines.append("")
    lines.append("## Feature Expansion Shadow")
    lines.append("")
    lines.append(
        "This report reruns the dependency-free learned/ranked detector shadow "
        "with richer offline feature columns derived from Fasim-visible source "
        "rows. It does not train or load a runtime model and does not change "
        "Fasim or SIM-close runtime behavior."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| fasim_sim_recovery_learned_detector_feature_expansion_{key} | {value} |")
    lines.append("")
    lines.append("## Expanded Feature List")
    lines.append("")
    lines.append("| Feature | Source |")
    lines.append("| --- | --- |")
    for feature in BASE_FEATURE_COLUMNS:
        lines.append(f"| {feature} | existing_baseline |")
    for feature in NEW_FEATURE_COLUMNS:
        lines.append(f"| {feature} | expanded_fasim_visible |")
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
    lines.append("## Baseline Comparison")
    lines.append("")
    lines.append("| Source | Current guard precision | Current guard recall | Learned precision | Learned recall | Rows |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    lines.append(
        "| #87_expanded_shadow | "
        f"{metrics['baseline_current_guard_precision']} | "
        f"{metrics['baseline_current_guard_recall']} | "
        f"{metrics['baseline_expanded_shadow_precision']} | "
        f"{metrics['baseline_expanded_shadow_recall']} | "
        f"{metrics['rows']} |"
    )
    lines.append(
        "| feature_expansion_primary | "
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
        "The decision remains based on candidate-eligible held-out metrics, not "
        "oracle-only target rows. If the expanded feature shadow still cannot "
        "beat the current hand-written guard, the learned-detector model path "
        "should pause while the current guard remains the stronger detector."
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
    parser.add_argument("--baseline-expanded-shadow-log", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--doc-report", default="")
    args = parser.parse_args()

    try:
        rows = expanded_shadow.read_rows(Path(args.dataset).resolve())
        source_rows = expanded_shadow.read_rows(Path(args.source_dataset).resolve())
        baseline_metrics = expanded_shadow.read_metric_log(
            Path(args.baseline_expanded_shadow_log).resolve()
        )
        missing = [
            feature
            for feature in EXPANDED_FEATURE_COLUMNS
            if rows and feature not in rows[0]
        ]
        if missing:
            raise RuntimeError("missing feature columns: " + ",".join(missing))

        metrics, policies = build_feature_metrics(
            rows=rows,
            source_rows=source_rows,
            baseline_metrics=baseline_metrics,
        )
        report = render_report(metrics=metrics, policies=policies)
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        if args.doc_report:
            doc_report_path = Path(args.doc_report).resolve()
            doc_report_path.parent.mkdir(parents=True, exist_ok=True)
            doc_report_path.write_text(report, encoding="utf-8")

        for key, value in metrics.items():
            print(
                "benchmark.fasim_sim_recovery_learned_detector_feature_expansion."
                f"total.{key}={value}"
            )
        print(report.rstrip())
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
