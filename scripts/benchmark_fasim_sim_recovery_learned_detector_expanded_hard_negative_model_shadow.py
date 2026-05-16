#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence


SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_fasim_sim_recovery_learned_detector_model_shadow as model_shadow  # noqa: E402


PREFIX = "benchmark.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.total"
REPORT_PREFIX = "fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow"

EXPANDED_FEATURE_COLUMNS = [
    "score",
    "Nt",
    "identity",
    "interval_length",
    "local_rank",
    "family_rank",
    "overlap_degree",
    "distance_to_fasim_boundary",
    "box_size",
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


def safe_metric_value(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:,|=-]+", "_", value.strip())
    return cleaned.strip("_") or "none"


def source_counts_string(counts: Counter[str] | Dict[str, int]) -> str:
    nonzero = [(key, value) for key, value in sorted(counts.items()) if value]
    return ",".join(f"{key}:{value}" for key, value in nonzero) or "none"


def metric_report_rows(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    metrics: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("| "):
                continue
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) != 2:
                continue
            key, value = parts
            if key in ("Metric", "---"):
                continue
            metrics[key] = value
    return metrics


def read_metric_log(path: Path) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if ".total." not in key:
            continue
        metrics[key.rsplit(".total.", 1)[1]] = value
    return metrics


def normalize_baselines() -> Dict[str, Dict[str, str]]:
    model = metric_report_rows(ROOT / "docs" / "fasim_sim_recovery_learned_detector_model_shadow.md")
    expanded = metric_report_rows(ROOT / "docs" / "fasim_sim_recovery_learned_detector_expanded_model_shadow.md")
    feature = metric_report_rows(ROOT / "docs" / "fasim_sim_recovery_learned_detector_feature_expansion.md")
    return {
        "#84_small_dataset": {
            "rows": model.get("fasim_sim_recovery_learned_detector_model_shadow_rows", "0"),
            "current_guard_precision": model.get(
                "fasim_sim_recovery_learned_detector_model_shadow_current_guard_validation_precision",
                "0.000000",
            ),
            "current_guard_recall": model.get(
                "fasim_sim_recovery_learned_detector_model_shadow_current_guard_validation_recall",
                "0.000000",
            ),
            "learned_shadow_precision": model.get(
                "fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_precision",
                model.get(
                    "fasim_sim_recovery_learned_detector_model_shadow_validation_precision",
                    "0.000000",
                ),
            ),
            "learned_shadow_recall": model.get(
                "fasim_sim_recovery_learned_detector_model_shadow_validation_candidate_eligible_recall_vs_all_positives",
                model.get(
                    "fasim_sim_recovery_learned_detector_model_shadow_validation_recall",
                    "0.000000",
                ),
            ),
        },
        "#87_expanded_corpus": {
            "rows": expanded.get("fasim_sim_recovery_learned_detector_expanded_model_shadow_rows", "0"),
            "current_guard_precision": expanded.get(
                "fasim_sim_recovery_learned_detector_expanded_model_shadow_current_guard_precision",
                "0.000000",
            ),
            "current_guard_recall": expanded.get(
                "fasim_sim_recovery_learned_detector_expanded_model_shadow_current_guard_recall",
                "0.000000",
            ),
            "learned_shadow_precision": expanded.get(
                "fasim_sim_recovery_learned_detector_expanded_model_shadow_candidate_eligible_precision",
                expanded.get(
                    "fasim_sim_recovery_learned_detector_expanded_model_shadow_learned_shadow_precision",
                    "0.000000",
                ),
            ),
            "learned_shadow_recall": expanded.get(
                "fasim_sim_recovery_learned_detector_expanded_model_shadow_candidate_eligible_recall",
                expanded.get(
                    "fasim_sim_recovery_learned_detector_expanded_model_shadow_learned_shadow_recall",
                    "0.000000",
                ),
            ),
        },
        "#88_feature_expanded": {
            "rows": feature.get("fasim_sim_recovery_learned_detector_feature_expansion_rows", "0"),
            "current_guard_precision": feature.get(
                "fasim_sim_recovery_learned_detector_feature_expansion_current_guard_precision",
                "0.000000",
            ),
            "current_guard_recall": feature.get(
                "fasim_sim_recovery_learned_detector_feature_expansion_current_guard_recall",
                "0.000000",
            ),
            "learned_shadow_precision": feature.get(
                "fasim_sim_recovery_learned_detector_feature_expansion_candidate_eligible_precision",
                feature.get(
                    "fasim_sim_recovery_learned_detector_feature_expansion_learned_shadow_precision",
                    "0.000000",
                ),
            ),
            "learned_shadow_recall": feature.get(
                "fasim_sim_recovery_learned_detector_feature_expansion_candidate_eligible_recall",
                feature.get(
                    "fasim_sim_recovery_learned_detector_feature_expansion_learned_shadow_recall",
                    "0.000000",
                ),
            ),
        },
    }


def current_row_split(row: Dict[str, str]) -> str:
    return row.get("split", "train")


def workload_row_split(row: Dict[str, str]) -> str:
    return model_shadow.split_for_key(row.get("workload_id", "unknown"))


def family_row_split(row: Dict[str, str]) -> str:
    return model_shadow.split_for_key(row.get("family_id", "unknown"))


def negative_source_row_split(row: Dict[str, str]) -> str:
    if row.get("label") == "0":
        return model_shadow.split_for_key(f"negative_source|{row.get('hard_negative_source', 'unknown')}")
    return workload_row_split(row)


def current_source_split(row: Dict[str, str]) -> str:
    return model_shadow.source_split(row)


def workload_source_split(row: Dict[str, str]) -> str:
    return model_shadow.split_for_key(row.get("workload_label", "unknown"))


def family_source_split(row: Dict[str, str]) -> str:
    return model_shadow.split_for_key(model_shadow.source_family_id(row))


def negative_source_source_split(row: Dict[str, str]) -> str:
    if row.get("source") == "sim_record" or row.get("label_in_sim") == "1":
        return workload_source_split(row)
    source = source_row_negative_source(row)
    return model_shadow.split_for_key(f"negative_source|{source}")


def source_row_negative_source(row: Dict[str, str]) -> str:
    source = row.get("source", "")
    stage = row.get("label_miss_stage", "")
    score = parse_float(row.get("score", "0"))
    nt = parse_float(row.get("nt", "0"))
    if row.get("validate_supported") == "0":
        return "no_legacy_sim_records_proxy"
    if source in ("accepted_candidate", "executor_candidate") and stage == "extra":
        return "extra_vs_sim_candidate"
    if source == "executor_candidate":
        if score >= 85.0 and nt >= 45.0:
            return "near_threshold_rejected_candidate"
        return "executor_candidate_non_sim"
    if source == "fasim_record":
        return "fasim_supported_non_sim"
    return "other"


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


def train_and_score(
    train_rows: Sequence[Dict[str, str]],
    validation_rows: Sequence[Dict[str, str]],
) -> tuple[float, List[float], Dict[str, str], Dict[str, str]]:
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
    return threshold, validation_scores, train_metrics, validation_metrics


def error_rows(
    validation_rows: Sequence[Dict[str, str]],
    validation_scores: Sequence[float],
    threshold: float,
) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    false_positives: List[Dict[str, str]] = []
    false_negatives: List[Dict[str, str]] = []
    for row, score in zip(validation_rows, validation_scores):
        predicted = score >= threshold and row.get("source") != "sim_record_target_positive"
        actual = model_shadow.label(row) == 1
        if predicted and not actual:
            false_positives.append(row)
        elif actual and not predicted:
            false_negatives.append(row)
    return false_positives, false_negatives


def evaluate_policy(
    *,
    name: str,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    row_split_func: PolicySplit,
    source_split_func: PolicySplit,
) -> Dict[str, Any]:
    counts = split_counts(rows, row_split_func)
    train_rows = [row for row in rows if row_split_func(row) == "train"]
    validation_rows = [row for row in rows if row_split_func(row) == "validation"]
    threshold, validation_scores, train_metrics, validation_metrics = train_and_score(
        train_rows,
        validation_rows,
    )
    candidate_metrics = candidate_eligible_metrics(
        validation_rows=validation_rows,
        validation_scores=validation_scores,
        threshold=threshold,
    )
    false_positive_rows, false_negative_rows = error_rows(
        validation_rows,
        validation_scores,
        threshold,
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
        "_false_positive_rows": false_positive_rows,
        "_false_negative_rows": false_negative_rows,
    }


def choose_primary(policies: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    for name in ("workload_heldout", "family_heldout", "current_split"):
        if policies[name]["degenerate"] == "0":
            return policies[name]
    return policies["current_split"]


def leave_one_workload_out(
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
) -> tuple[List[Dict[str, str]], int]:
    workload_ids = sorted({row.get("workload_id", "unknown") for row in rows})
    summaries: List[Dict[str, str]] = []
    skipped = 0
    for workload_id in workload_ids:
        def row_split(row: Dict[str, str], heldout: str = workload_id) -> str:
            return "validation" if row.get("workload_id", "unknown") == heldout else "train"

        def source_split(row: Dict[str, str], heldout: str = workload_id) -> str:
            return "validation" if row.get("workload_label", "unknown") == heldout else "train"

        policy = evaluate_policy(
            name=f"loo_{workload_id}",
            rows=rows,
            source_rows=source_rows,
            row_split_func=row_split,
            source_split_func=source_split,
        )
        if policy["degenerate"] != "0":
            skipped += 1
            continue
        summaries.append(
            {
                "workload_id": workload_id,
                "train_positive": policy["train_positive"],
                "train_negative": policy["train_negative"],
                "validation_positive": policy["validation_positive"],
                "validation_negative": policy["validation_negative"],
                "current_guard_precision": policy["current_guard_precision"],
                "current_guard_recall": policy["current_guard_recall"],
                "candidate_eligible_precision": policy["candidate_eligible_precision"],
                "candidate_eligible_recall": policy["candidate_eligible_recall"],
                "false_positives": policy["candidate_eligible_false_positives"],
                "false_negatives": policy["candidate_eligible_false_negatives"],
                "selected_threshold": policy["selected_threshold"],
            }
        )
    return summaries, skipped


def false_positive_source_counts(policy: Dict[str, Any]) -> Counter[str]:
    rows = policy.get("_false_positive_rows", [])
    return Counter(row.get("hard_negative_source", "unknown") for row in rows)


def false_negative_workload_counts(policy: Dict[str, Any]) -> Counter[str]:
    rows = policy.get("_false_negative_rows", [])
    return Counter(row.get("workload_id", "unknown") for row in rows)


def no_legacy_false_positives(policy: Dict[str, Any]) -> int:
    rows = policy.get("_false_positive_rows", [])
    return sum(
        1
        for row in rows
        if row.get("hard_negative_source") == "no_legacy_sim_records_proxy"
    )


def build_metrics(
    *,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    data_metrics: Dict[str, str],
) -> tuple[Dict[str, str], Dict[str, Dict[str, Any]], List[Dict[str, str]], int, Dict[str, Dict[str, str]]]:
    model_shadow.FEATURE_COLUMNS = list(EXPANDED_FEATURE_COLUMNS)
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
        "negative_source_heldout": evaluate_policy(
            name="negative_source_heldout",
            rows=rows,
            source_rows=source_rows,
            row_split_func=negative_source_row_split,
            source_split_func=negative_source_source_split,
        ),
    }
    loo_rows, loo_skipped = leave_one_workload_out(rows, source_rows)
    primary = choose_primary(policies)
    fp_by_source = source_counts_string(false_positive_source_counts(primary))
    fn_by_workload = source_counts_string(false_negative_workload_counts(primary))
    baselines = normalize_baselines()
    current_split_wins = policies["current_split"]["beats_current_guard_on_validation"] == "1"
    if primary["name"] == "workload_heldout" and primary["degenerate"] == "0":
        if primary["beats_current_guard_on_validation"] == "1":
            decision = "continue_learned_detector_research"
        elif current_split_wins:
            decision = "resubstitution_only_collect_more_data"
        elif no_legacy_false_positives(primary) > 0:
            decision = "split_no_legacy_controls_keep_guard"
        else:
            decision = "pause_model_path_keep_guard"
    else:
        decision = "collect_more_workloads"

    metrics = {
        "enabled": "1",
        "rows": str(len(rows)),
        "positive_rows": str(labels.get("1", 0)),
        "negative_rows": str(labels.get("0", 0)),
        "workload_count": str(len({row.get("workload_id", "unknown") for row in rows})),
        "validate_supported_workload_count": data_metrics.get("validate_supported_workload_count", "0"),
        "no_legacy_sim_records_workload_count": data_metrics.get(
            "no_legacy_sim_records_workload_count",
            "0",
        ),
        "hard_negative_sources": source_counts_string(hard_negative_sources),
        "hard_negative_source_count": str(sum(1 for count in hard_negative_sources.values() if count)),
        "feature_count": str(len(EXPANDED_FEATURE_COLUMNS)),
        "features": ",".join(EXPANDED_FEATURE_COLUMNS),
        "evaluation_policy": primary["name"],
        "train_positive": primary["train_positive"],
        "train_negative": primary["train_negative"],
        "validation_positive": primary["validation_positive"],
        "validation_negative": primary["validation_negative"],
        "current_split_degenerate": policies["current_split"]["degenerate"],
        "workload_heldout_degenerate": policies["workload_heldout"]["degenerate"],
        "family_heldout_degenerate": policies["family_heldout"]["degenerate"],
        "negative_source_heldout_degenerate": policies["negative_source_heldout"]["degenerate"],
        "current_guard_recall": primary["current_guard_recall"],
        "current_guard_precision": primary["current_guard_precision"],
        "current_guard_false_positives": primary["current_guard_false_positives"],
        "current_guard_false_negatives": primary["current_guard_false_negatives"],
        "learned_shadow_recall": primary["learned_shadow_recall"],
        "learned_shadow_precision": primary["learned_shadow_precision"],
        "candidate_eligible_recall": primary["candidate_eligible_recall"],
        "candidate_eligible_precision": primary["candidate_eligible_precision"],
        "false_positives": primary["candidate_eligible_false_positives"],
        "false_negatives": primary["candidate_eligible_false_negatives"],
        "false_positives_by_negative_source": safe_metric_value(fp_by_source),
        "false_negatives_by_workload": safe_metric_value(fn_by_workload),
        "no_legacy_proxy_false_positives": str(no_legacy_false_positives(primary)),
        "selected_threshold": primary["selected_threshold"],
        "loo_workload_evaluated": str(len(loo_rows)),
        "loo_workload_skipped": str(loo_skipped),
        "beats_current_guard_on_validation": primary["beats_current_guard_on_validation"],
        "decision": decision,
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
        "model_training_added": "0",
        "deep_learning_dependency": "0",
        "recommended_default_sim_close": "0",
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
            "candidate_eligible_false_positives",
            "candidate_eligible_false_negatives",
        ):
            metrics[f"{policy_name}_{key}"] = str(policy[key])
    for baseline_name, baseline in baselines.items():
        key_prefix = baseline_name.strip("#").replace("-", "_").replace(" ", "_").lower()
        for key, value in baseline.items():
            metrics[f"baseline_{key_prefix}_{key}"] = value
    return metrics, policies, loo_rows, loo_skipped, baselines


def render_report(
    *,
    metrics: Dict[str, str],
    policies: Dict[str, Dict[str, Any]],
    loo_rows: Sequence[Dict[str, str]],
    loo_skipped: int,
    baselines: Dict[str, Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Expanded Hard-Negative Model Shadow")
    lines.append("")
    lines.append("## Expanded Hard-Negative Model Shadow")
    lines.append("")
    lines.append(
        "This report evaluates the dependency-free learned/ranked detector shadow "
        "on the #89 expanded hard-negative corpus. It is an offline evaluation "
        "only: no runtime model is trained or loaded, and Fasim/SIM-close "
        "runtime behavior is unchanged."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| {REPORT_PREFIX}_{key} | {value} |")
    lines.append("")
    lines.append("## Split Evaluation")
    lines.append("")
    lines.append(
        "| Policy | Train + | Train - | Validation + | Validation - | Degenerate | "
        "Current guard precision | Current guard recall | Learned precision | "
        "Learned recall | Candidate precision | Candidate recall | False + | False - | Threshold |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for policy_name in ("current_split", "workload_heldout", "family_heldout", "negative_source_heldout"):
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
    lines.append("")
    lines.append("## Negative-Source Held-Out")
    lines.append("")
    negative_source = policies["negative_source_heldout"]
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in (
        "train_positive",
        "train_negative",
        "validation_positive",
        "validation_negative",
        "degenerate",
        "candidate_eligible_precision",
        "candidate_eligible_recall",
        "candidate_eligible_false_positives",
        "candidate_eligible_false_negatives",
        "selected_threshold",
    ):
        lines.append(f"| {key} | {negative_source[key]} |")
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
    lines.append(f"Skipped degenerate workloads: `{loo_skipped}`.")
    lines.append("")
    lines.append(
        "| Workload | Train + | Train - | Validation + | Validation - | Current guard precision | "
        "Current guard recall | Candidate precision | Candidate recall | False + | False - | Threshold |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    if loo_rows:
        for row in loo_rows:
            lines.append(
                f"| {row['workload_id']} | {row['train_positive']} | {row['train_negative']} | "
                f"{row['validation_positive']} | {row['validation_negative']} | "
                f"{row['current_guard_precision']} | {row['current_guard_recall']} | "
                f"{row['candidate_eligible_precision']} | {row['candidate_eligible_recall']} | "
                f"{row['false_positives']} | {row['false_negatives']} | {row['selected_threshold']} |"
            )
    else:
        lines.append("| none | 0 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 0.000000 |")
    lines.append("")
    lines.append("## Baseline Comparison")
    lines.append("")
    lines.append("| Source | Rows | Current guard precision | Current guard recall | Learned precision | Learned recall |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for name, baseline in baselines.items():
        lines.append(
            f"| {name} | {baseline['rows']} | {baseline['current_guard_precision']} | "
            f"{baseline['current_guard_recall']} | {baseline['learned_shadow_precision']} | "
            f"{baseline['learned_shadow_recall']} |"
        )
    lines.append(
        f"| #90_expanded_hard_negative_primary | {metrics['rows']} | "
        f"{metrics['current_guard_precision']} | {metrics['current_guard_recall']} | "
        f"{metrics['candidate_eligible_precision']} | {metrics['candidate_eligible_recall']} |"
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"Decision: `{metrics['decision']}`.")
    lines.append("")
    lines.append(
        "The decision is based on candidate-eligible held-out metrics. "
        "If only current-split/resubstitution improves, this is not evidence for "
        "runtime promotion. If learned shadow still loses to the hand-written "
        "guard, keep the guard and treat #89 as a data foundation."
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

    try:
        dataset_path = Path(args.dataset).resolve()
        source_dataset_path = Path(args.source_dataset).resolve()
        data_expansion_log = Path(args.data_expansion_log).resolve()
        report_path = Path(args.report).resolve()
        rows = read_rows(dataset_path)
        source_rows = read_rows(source_dataset_path)
        missing = [feature for feature in EXPANDED_FEATURE_COLUMNS if rows and feature not in rows[0]]
        if missing:
            raise RuntimeError("missing feature columns: " + ",".join(missing))
        data_metrics = read_metric_log(data_expansion_log)
        metrics, policies, loo_rows, loo_skipped, baselines = build_metrics(
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
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        if args.doc_report:
            doc_report_path = Path(args.doc_report).resolve()
            doc_report_path.parent.mkdir(parents=True, exist_ok=True)
            doc_report_path.write_text(report, encoding="utf-8")
        for key, value in metrics.items():
            print(f"{PREFIX}.{key}={value}")
        print(report.rstrip())
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
