#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import statistics
from typing import Dict, List, Sequence, Tuple


FEATURE_COLUMNS = [
    "score",
    "nt",
    "identity",
    "mean_stability",
    "genome_len",
    "query_len",
    "same_family_overlap_count",
    "nearest_fasim_score_delta",
    "local_rank",
    "box_count_covering",
    "cell_cost",
]


GUARD_POLICY_NAMES = [
    "current_guard",
    "score_nt_threshold",
    "score_nt_rank5",
    "local_rank_top3",
    "relaxed_score_nt_rank3",
    "relaxed_score_nt_rank5",
    "relaxed_score_nt_rank10",
    "accept_all_executor",
]


def parse_float(value: str) -> float:
    if value in ("", "NA"):
        return 0.0
    return float(value)


def fmt(value: float) -> str:
    return f"{value:.6f}"


def read_dataset(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def candidate_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("source") == "executor_candidate"
        and row.get("label_available") == "1"
        and row.get("label_guard_should_accept") in ("0", "1")
    ]


def accepted_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("source") == "accepted_candidate"
        and row.get("label_available") == "1"
        and row.get("label_guard_should_accept") in ("0", "1")
    ]


def sim_record_rows(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("source") == "sim_record" and row.get("label_available") == "1"
    ]


def feature_matrix(rows: Sequence[Dict[str, str]]) -> List[List[float]]:
    return [[parse_float(row.get(column, "0")) for column in FEATURE_COLUMNS] for row in rows]


def labels(rows: Sequence[Dict[str, str]]) -> List[int]:
    return [1 if row.get("label_guard_should_accept") == "1" else 0 for row in rows]


def row_score(row: Dict[str, str]) -> float:
    return parse_float(row.get("score", "0"))


def row_nt(row: Dict[str, str]) -> float:
    return parse_float(row.get("nt", "0"))


def row_local_rank(row: Dict[str, str]) -> int:
    return int(parse_float(row.get("local_rank", "0")))


def heuristic_scores(rows: Sequence[Dict[str, str]]) -> List[float]:
    raw_scores: List[float] = []
    for row in rows:
        score = parse_float(row.get("score", "0"))
        nt = parse_float(row.get("nt", "0"))
        identity = parse_float(row.get("identity", "0"))
        rank = parse_float(row.get("local_rank", "0"))
        rank_bonus = 1.0 / rank if rank > 0 else 0.0
        raw_scores.append(score + nt + identity + rank_bonus)
    return raw_scores


def model_scores(rows: Sequence[Dict[str, str]], y: Sequence[int]) -> Tuple[str, int, List[float]]:
    if len(set(y)) < 2:
        return ("heuristic_score_nt_identity", 0, heuristic_scores(rows))

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception:
        return ("heuristic_score_nt_identity", 0, heuristic_scores(rows))

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0),
    )
    model.fit(feature_matrix(rows), y)
    probabilities = model.predict_proba(feature_matrix(rows))[:, 1]
    return ("logistic_regression_resubstitution", 1, [float(value) for value in probabilities])


def precision_recall_at_top_n(
    *,
    rows: Sequence[Dict[str, str]],
    y: Sequence[int],
    scores: Sequence[float],
    top_n: int,
) -> Tuple[int, int, float, float]:
    if not rows or not y:
        return (0, 0, 0.0, 0.0)
    selected_count = min(max(top_n, 0), len(rows))
    if selected_count == 0:
        return (0, 0, 0.0, 0.0)
    ranked = sorted(zip(scores, y), key=lambda item: item[0], reverse=True)
    selected = ranked[:selected_count]
    true_positive = sum(label for _, label in selected)
    total_positive = sum(y)
    recall = true_positive / total_positive * 100.0 if total_positive else 0.0
    precision = true_positive / selected_count * 100.0 if selected_count else 0.0
    return (selected_count, true_positive, recall, precision)


def pairwise_auc(y: Sequence[int], scores: Sequence[float]) -> float:
    positives = [score for score, label in zip(scores, y) if label == 1]
    negatives = [score for score, label in zip(scores, y) if label == 0]
    if not positives or not negatives:
        return 0.0
    wins = 0.0
    total = 0
    for pos in positives:
        for neg in negatives:
            total += 1
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / total * 100.0 if total else 0.0


def median_score_by_label(y: Sequence[int], scores: Sequence[float], label: int) -> float:
    values = [score for score, current in zip(scores, y) if current == label]
    return float(statistics.median(values)) if values else 0.0


def select_guard_policy_rows(
    policy: str,
    *,
    candidates: Sequence[Dict[str, str]],
    accepted: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    if policy == "current_guard":
        return list(accepted)
    if policy == "accept_all_executor":
        return list(candidates)
    if policy == "score_nt_threshold":
        return [row for row in candidates if row_score(row) >= 89.0 and row_nt(row) >= 50.0]
    if policy == "score_nt_rank5":
        return [
            row
            for row in candidates
            if row_score(row) >= 89.0
            and row_nt(row) >= 50.0
            and 0 < row_local_rank(row) <= 5
        ]
    if policy == "local_rank_top3":
        return [
            row
            for row in candidates
            if row_score(row) >= 89.0
            and row_nt(row) >= 50.0
            and 0 < row_local_rank(row) <= 3
        ]
    if policy == "relaxed_score_nt_rank3":
        return [
            row
            for row in candidates
            if row_score(row) >= 85.0
            and row_nt(row) >= 45.0
            and 0 < row_local_rank(row) <= 3
        ]
    if policy == "relaxed_score_nt_rank5":
        return [
            row
            for row in candidates
            if row_score(row) >= 85.0
            and row_nt(row) >= 45.0
            and 0 < row_local_rank(row) <= 5
        ]
    if policy == "relaxed_score_nt_rank10":
        return [
            row
            for row in candidates
            if row_score(row) >= 85.0
            and row_nt(row) >= 45.0
            and 0 < row_local_rank(row) <= 10
        ]
    raise RuntimeError(f"unknown guard policy: {policy}")


def guard_policy_shadow_rows(
    *,
    workload_label: str,
    candidates: Sequence[Dict[str, str]],
    accepted: Sequence[Dict[str, str]],
    total_candidate_positive: int,
    total_sim_records: int,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for policy in GUARD_POLICY_NAMES:
        selected = select_guard_policy_rows(policy, candidates=candidates, accepted=accepted)
        selected_positive = sum(labels(selected))
        selected_count = len(selected)
        selected_negative = selected_count - selected_positive
        rows.append(
            {
                "workload_label": workload_label,
                "policy": policy,
                "selected_rows": str(selected_count),
                "selected_positive_rows": str(selected_positive),
                "selected_negative_rows": str(selected_negative),
                "recall_within_candidates": fmt(
                    selected_positive / total_candidate_positive * 100.0
                    if total_candidate_positive
                    else 0.0
                ),
                "recall_vs_sim": fmt(
                    selected_positive / total_sim_records * 100.0
                    if total_sim_records
                    else 0.0
                ),
                "precision": fmt(
                    selected_positive / selected_count * 100.0 if selected_count else 0.0
                ),
            }
        )
    return rows


def best_non_oracle_policy(rows: Sequence[Dict[str, str]]) -> Dict[str, str]:
    non_oracle = [row for row in rows if row["policy"] != "accept_all_executor"]
    if not non_oracle:
        return {
            "workload_label": "all",
            "policy": "none",
            "selected_rows": "0",
            "selected_positive_rows": "0",
            "selected_negative_rows": "0",
            "recall_within_candidates": "0.000000",
            "recall_vs_sim": "0.000000",
            "precision": "0.000000",
        }
    return max(
        non_oracle,
        key=lambda row: (
            parse_float(row["recall_vs_sim"]),
            parse_float(row["precision"]),
            -int(row["selected_rows"]),
        ),
    )


def grouped_rows_by_workload(rows: Sequence[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    grouped: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row.get("workload_label", "unknown"), []).append(row)
    return grouped


def guard_policy_rows_by_workload(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    table_rows: List[Dict[str, str]] = []
    candidate_groups = grouped_rows_by_workload(candidate_rows(rows))
    accepted_groups = grouped_rows_by_workload(accepted_rows(rows))
    sim_groups = grouped_rows_by_workload(sim_record_rows(rows))
    for workload_label in sorted(set(candidate_groups) | set(accepted_groups) | set(sim_groups)):
        candidates = candidate_groups.get(workload_label, [])
        accepted = accepted_groups.get(workload_label, [])
        if not candidates and not accepted:
            continue
        table_rows.extend(
            guard_policy_shadow_rows(
                workload_label=workload_label,
                candidates=candidates,
                accepted=accepted,
                total_candidate_positive=sum(labels(candidates)),
                total_sim_records=len(sim_groups.get(workload_label, [])),
            )
        )
    return table_rows


def render_report(
    *,
    dataset_path: Path,
    output_path: Path,
    telemetry: Dict[str, str],
    guard_policy_rows: Sequence[Dict[str, str]],
    workload_guard_policy_rows: Sequence[Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Model Shadow")
    lines.append("")
    lines.append("## Learned Detector Model Shadow")
    lines.append("")
    lines.append(
        "This is a diagnostic-only offline model shadow over the learned-detector "
        "dataset TSV. It trains or scores candidate rows outside the Fasim "
        "runtime path and does not change recovery boxes, guards, replacement, "
        "output ordering, or default behavior."
    )
    lines.append("")
    lines.append(f"Dataset: `{dataset_path}`")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in telemetry.items():
        lines.append(f"| fasim_sim_recovery_learned_detector_model_{key} | {value} |")
    lines.append("")
    lines.append("## Guard Policy Shadow")
    lines.append("")
    lines.append(
        "These rows replay simple non-oracle guard policies over exported executor "
        "candidates. They are TSV-only diagnostics; they do not change the runtime "
        "`combined_non_oracle` guard or SIM-close output."
    )
    lines.append("")
    lines.append(
        "| Policy | Selected | Positive | Negative | Recall within candidates | "
        "Recall vs SIM | Precision |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in guard_policy_rows:
        lines.append(
            f"| {row['policy']} | {row['selected_rows']} | "
            f"{row['selected_positive_rows']} | {row['selected_negative_rows']} | "
            f"{row['recall_within_candidates']} | {row['recall_vs_sim']} | "
            f"{row['precision']} |"
        )
    lines.append("")
    lines.append("## Guard Policy By Workload")
    lines.append("")
    lines.append(
        "This table keeps workload-specific behavior visible so a policy that is "
        "clean on one real case but dirty on a fixture is not hidden by aggregate "
        "telemetry."
    )
    lines.append("")
    lines.append(
        "| Workload | Policy | Selected | Positive | Negative | "
        "Recall within candidates | Recall vs SIM | Precision |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in workload_guard_policy_rows:
        lines.append(
            f"| {row['workload_label']} | {row['policy']} | {row['selected_rows']} | "
            f"{row['selected_positive_rows']} | {row['selected_negative_rows']} | "
            f"{row['recall_within_candidates']} | {row['recall_vs_sim']} | "
            f"{row['precision']} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "`current_accepted_recall` and `model_topn_recall` are measured within "
        "the executor-candidate rows. The `*_recall_vs_sim` metrics are the "
        "production-relevant view against all validate-supported SIM records."
    )
    lines.append("")
    lines.append(
        "`candidate_oracle_*` means accepting every exported executor candidate "
        "using post-hoc SIM labels as an upper-bound diagnostic. It is not a "
        "runtime policy and must not be used for production selection."
    )
    lines.append("")
    if telemetry.get("learnable_two_class") == "0":
        lines.append(
            "This dataset has only one candidate label class, so no two-class "
            "learned ranker can be validated from it. The result should be read "
            "as guard/detector diagnostic evidence, not model-quality evidence."
        )
        lines.append("")
    lines.append(
        "`evaluation_mode=resubstitution_smoke` means the model is evaluated on "
        "the same rows it was fit on. This is only a separability smoke check, "
        "not held-out real-corpus evidence."
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(
        "This report is a guard/detector shadow only. The best non-oracle guard "
        f"policy is `{telemetry.get('guard_policy_shadow_best_non_oracle_policy', 'NA')}` "
        "with "
        f"{telemetry.get('guard_policy_shadow_best_non_oracle_recall_vs_sim', '0.000000')} "
        "recall vs SIM and "
        f"{telemetry.get('guard_policy_shadow_best_non_oracle_precision', '0.000000')} "
        "precision. The current guard remains the runtime behavior."
    )
    lines.append("")
    lines.append(
        "`accept_all_executor` is an oracle-style upper-bound diagnostic over "
        "already exported executor candidates. It does not solve records that "
        "were never covered by recovery boxes, and it must not be used as a "
        "production policy."
    )
    lines.append("")
    lines.append(
        "Do not default or recommend SIM-close mode from this report. Broader "
        "real-corpus coverage and a detector for not-box-covered records are "
        "still required before any high-accuracy claim."
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
    lines.append("Do not use this model for production selection.")
    lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


def telemetry_for_dataset(dataset_path: Path) -> Dict[str, str]:
    rows = read_dataset(dataset_path)
    candidates = candidate_rows(rows)
    accepted = accepted_rows(rows)
    sim_records = sim_record_rows(rows)
    y = labels(candidates)
    scores_model, used_sklearn, scores = model_scores(candidates, y)

    accepted_positive = sum(labels(accepted))
    total_positive = sum(y)
    total_sim_records = len(sim_records)
    accepted_count = len(accepted)
    current_recall = accepted_positive / total_positive * 100.0 if total_positive else 0.0
    current_precision = accepted_positive / accepted_count * 100.0 if accepted_count else 0.0
    top_n = accepted_count if accepted_count else total_positive
    selected_count, selected_positive, model_recall, model_precision = precision_recall_at_top_n(
        rows=candidates,
        y=y,
        scores=scores,
        top_n=top_n,
    )
    negative_count = len(candidates) - total_positive
    guard_rows = guard_policy_shadow_rows(
        workload_label="all",
        candidates=candidates,
        accepted=accepted,
        total_candidate_positive=total_positive,
        total_sim_records=total_sim_records,
    )
    guard_by_policy = {row["policy"]: row for row in guard_rows}
    best_guard = best_non_oracle_policy(guard_rows)
    telemetry = {
        "enabled": "1",
        "dataset_rows": str(len(rows)),
        "sim_record_rows": str(total_sim_records),
        "candidate_rows": str(len(candidates)),
        "accepted_rows": str(accepted_count),
        "positive_rows": str(total_positive),
        "negative_rows": str(negative_count),
        "learnable_two_class": "1" if total_positive and negative_count else "0",
        "model": scores_model,
        "sklearn_used": str(used_sklearn),
        "evaluation_mode": "resubstitution_smoke",
        "top_n": str(top_n),
        "current_accepted_recall": fmt(current_recall),
        "current_accepted_precision": fmt(current_precision),
        "current_accepted_recall_vs_sim": fmt(
            accepted_positive / total_sim_records * 100.0 if total_sim_records else 0.0
        ),
        "model_selected_rows": str(selected_count),
        "model_selected_positive_rows": str(selected_positive),
        "model_topn_recall": fmt(model_recall),
        "model_topn_precision": fmt(model_precision),
        "model_topn_recall_vs_sim": fmt(
            selected_positive / total_sim_records * 100.0 if total_sim_records else 0.0
        ),
        "candidate_oracle_selected_rows": str(len(candidates)),
        "candidate_oracle_positive_rows": str(total_positive),
        "candidate_oracle_recall_vs_sim": fmt(
            total_positive / total_sim_records * 100.0 if total_sim_records else 0.0
        ),
        "candidate_oracle_precision": fmt(
            total_positive / len(candidates) * 100.0 if candidates else 0.0
        ),
        "model_auc": fmt(pairwise_auc(y, scores)),
        "positive_score_median": fmt(median_score_by_label(y, scores, 1)),
        "negative_score_median": fmt(median_score_by_label(y, scores, 0)),
        "guard_policy_shadow_enabled": "1",
        "guard_policy_shadow_policies": str(len(guard_rows)),
        "guard_policy_shadow_best_non_oracle_policy": best_guard["policy"],
        "guard_policy_shadow_best_non_oracle_recall_vs_sim": best_guard["recall_vs_sim"],
        "guard_policy_shadow_best_non_oracle_precision": best_guard["precision"],
        "guard_policy_shadow_current_guard_recall_vs_sim": guard_by_policy[
            "current_guard"
        ]["recall_vs_sim"],
        "guard_policy_shadow_current_guard_precision": guard_by_policy[
            "current_guard"
        ]["precision"],
        "guard_policy_shadow_accept_all_executor_recall_vs_sim": guard_by_policy[
            "accept_all_executor"
        ]["recall_vs_sim"],
        "guard_policy_shadow_accept_all_executor_precision": guard_by_policy[
            "accept_all_executor"
        ]["precision"],
        "guard_policy_shadow_relaxed_score_nt_rank3_recall_vs_sim": guard_by_policy[
            "relaxed_score_nt_rank3"
        ]["recall_vs_sim"],
        "guard_policy_shadow_relaxed_score_nt_rank3_precision": guard_by_policy[
            "relaxed_score_nt_rank3"
        ]["precision"],
        "production_model": "0",
    }
    return telemetry


def guard_policy_rows_for_dataset(dataset_path: Path) -> List[Dict[str, str]]:
    rows = read_dataset(dataset_path)
    candidates = candidate_rows(rows)
    accepted = accepted_rows(rows)
    return guard_policy_shadow_rows(
        workload_label="all",
        candidates=candidates,
        accepted=accepted,
        total_candidate_positive=sum(labels(candidates)),
        total_sim_records=len(sim_record_rows(rows)),
    )


def workload_guard_policy_rows_for_dataset(dataset_path: Path) -> List[Dict[str, str]]:
    return guard_policy_rows_by_workload(read_dataset(dataset_path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        dataset_path = Path(args.dataset).resolve()
        output_path = Path(args.output).resolve()
        telemetry = telemetry_for_dataset(dataset_path)
        guard_policy_rows = guard_policy_rows_for_dataset(dataset_path)
        workload_guard_policy_rows = workload_guard_policy_rows_for_dataset(dataset_path)
        report = render_report(
            dataset_path=dataset_path,
            output_path=output_path,
            telemetry=telemetry,
            guard_policy_rows=guard_policy_rows,
            workload_guard_policy_rows=workload_guard_policy_rows,
        )
        for key, value in telemetry.items():
            print(f"benchmark.fasim_sim_recovery_learned_detector_model.total.{key}={value}")
        print(report)
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
