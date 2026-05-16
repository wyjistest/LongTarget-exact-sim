#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence


PREFIX = "benchmark.fasim_sim_recovery_learned_detector_large_corpus_expansion.total"
REPORT_PREFIX = "fasim_sim_recovery_learned_detector_large_corpus_expansion"
BASELINE_EXPANDED_HARD_NEGATIVE_ROWS = 59
BASELINE_EXPANDED_HARD_NEGATIVE_POSITIVES = 26
BASELINE_EXPANDED_HARD_NEGATIVE_NEGATIVES = 33
BASELINE_EXPANDED_HARD_NEGATIVE_WORKLOADS = 7
BASELINE_EXPANDED_HARD_NEGATIVE_SOURCE_COUNT = 5


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_metric_log(path: Path) -> Dict[str, str]:
    metrics: Dict[str, str] = {}
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or ".total." not in line:
            continue
        key, value = line.split("=", 1)
        metrics[key.rsplit(".total.", 1)[1]] = value
    return metrics


def read_manifest(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def source_counts_string(counts: Counter[str] | Dict[str, int]) -> str:
    nonzero = [(key, value) for key, value in sorted(counts.items()) if value]
    return ",".join(f"{key}:{value}" for key, value in nonzero) or "none"


def metric(metrics: Dict[str, str], key: str, default: str = "0") -> str:
    value = metrics.get(key, default)
    return value if value != "" else default


def build_metrics(
    *,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    data_metrics: Dict[str, str],
    manifest_rows: Sequence[Dict[str, str]],
    extra_marmoset_limit: int,
    extra_marmoset_min_rna_bytes: int,
) -> Dict[str, str]:
    labels = Counter(row.get("label", "0") for row in rows)
    hard_negative_sources = Counter(
        row.get("hard_negative_source", "unknown")
        for row in rows
        if row.get("label") == "0"
    )
    workload_count = len({row.get("workload_id", "unknown") for row in rows})
    positive_rows = labels.get("1", 0)
    negative_rows = labels.get("0", 0)

    selected_extra_case_count = metric(
        data_metrics,
        "selected_extra_case_count",
        str(len(manifest_rows)),
    )
    metrics = {
        "enabled": "1",
        "extra_marmoset_limit": str(extra_marmoset_limit),
        "extra_marmoset_min_rna_bytes": str(extra_marmoset_min_rna_bytes),
        "rows": str(len(rows)),
        "positive_rows": str(positive_rows),
        "negative_rows": str(negative_rows),
        "source_rows": str(len(source_rows)),
        "workload_count": str(workload_count),
        "family_count": metric(
            data_metrics,
            "family_count",
            str(len({row.get("family_id", "unknown") for row in rows})),
        ),
        "validate_supported_workload_count": metric(
            data_metrics,
            "validate_supported_workload_count",
        ),
        "no_legacy_sim_records_workload_count": metric(
            data_metrics,
            "no_legacy_sim_records_workload_count",
        ),
        "hard_negative_sources": source_counts_string(hard_negative_sources),
        "hard_negative_source_count": str(
            sum(1 for value in hard_negative_sources.values() if value)
        ),
        "candidate_eligible_positive_rows": metric(
            data_metrics,
            "candidate_eligible_positive_rows",
        ),
        "candidate_eligible_negative_rows": metric(
            data_metrics,
            "candidate_eligible_negative_rows",
        ),
        "discovered_marmoset_pair_count": metric(
            data_metrics,
            "discovered_marmoset_pair_count",
        ),
        "eligible_extra_marmoset_pair_count": metric(
            data_metrics,
            "eligible_extra_marmoset_pair_count",
        ),
        "selected_extra_case_count": selected_extra_case_count,
        "selected_extra_source_rows": metric(data_metrics, "selected_extra_source_rows"),
        "selected_extra_positive_rows": metric(data_metrics, "selected_extra_positive_rows"),
        "selected_extra_negative_rows": metric(data_metrics, "selected_extra_negative_rows"),
        "heldout_workload_available": metric(data_metrics, "heldout_workload_available"),
        "heldout_family_available": metric(data_metrics, "heldout_family_available"),
        "workload_heldout_degenerate": metric(data_metrics, "workload_heldout_degenerate"),
        "family_heldout_degenerate": metric(data_metrics, "family_heldout_degenerate"),
        "modeling_gate": metric(data_metrics, "modeling_gate", "unknown"),
        "baseline_expanded_hard_negative_rows": str(
            BASELINE_EXPANDED_HARD_NEGATIVE_ROWS
        ),
        "baseline_expanded_hard_negative_positive_rows": str(
            BASELINE_EXPANDED_HARD_NEGATIVE_POSITIVES
        ),
        "baseline_expanded_hard_negative_negative_rows": str(
            BASELINE_EXPANDED_HARD_NEGATIVE_NEGATIVES
        ),
        "baseline_expanded_hard_negative_workload_count": str(
            BASELINE_EXPANDED_HARD_NEGATIVE_WORKLOADS
        ),
        "baseline_expanded_hard_negative_source_count": str(
            BASELINE_EXPANDED_HARD_NEGATIVE_SOURCE_COUNT
        ),
        "growth_vs_expanded_hard_negative_rows": str(
            len(rows) - BASELINE_EXPANDED_HARD_NEGATIVE_ROWS
        ),
        "growth_vs_expanded_hard_negative_positive_rows": str(
            positive_rows - BASELINE_EXPANDED_HARD_NEGATIVE_POSITIVES
        ),
        "growth_vs_expanded_hard_negative_negative_rows": str(
            negative_rows - BASELINE_EXPANDED_HARD_NEGATIVE_NEGATIVES
        ),
        "growth_vs_expanded_hard_negative_workloads": str(
            workload_count - BASELINE_EXPANDED_HARD_NEGATIVE_WORKLOADS
        ),
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
        "model_training_added": "0",
        "deep_learning_dependency": "0",
        "recommended_default_sim_close": "0",
    }
    return metrics


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def render_report(
    *,
    metrics: Dict[str, str],
    manifest_rows: Sequence[Dict[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Large Corpus Expansion")
    lines.append("")
    lines.append("## Large Corpus Expansion")
    lines.append("")
    lines.append(
        "This report generates a larger offline learned-detector real-corpus "
        "dataset by raising the bounded optional marmoset expansion limit. It "
        "is data generation only: no runtime model is trained or loaded, and "
        "Fasim/SIM-close runtime behavior is unchanged."
    )
    lines.append("")
    lines.extend(
        markdown_table(
            ["Metric", "Value"],
            [
                [f"{REPORT_PREFIX}_{key}", value]
                for key, value in metrics.items()
            ],
        )
    )
    lines.append("")
    lines.append("## Corpus Growth")
    lines.append("")
    lines.extend(
        markdown_table(
            ["Metric", "#90 baseline", "Large corpus", "Growth"],
            [
                [
                    "rows",
                    metrics["baseline_expanded_hard_negative_rows"],
                    metrics["rows"],
                    metrics["growth_vs_expanded_hard_negative_rows"],
                ],
                [
                    "positive_rows",
                    metrics["baseline_expanded_hard_negative_positive_rows"],
                    metrics["positive_rows"],
                    metrics["growth_vs_expanded_hard_negative_positive_rows"],
                ],
                [
                    "negative_rows",
                    metrics["baseline_expanded_hard_negative_negative_rows"],
                    metrics["negative_rows"],
                    metrics["growth_vs_expanded_hard_negative_negative_rows"],
                ],
                [
                    "workload_count",
                    metrics["baseline_expanded_hard_negative_workload_count"],
                    metrics["workload_count"],
                    metrics["growth_vs_expanded_hard_negative_workloads"],
                ],
            ],
        )
    )
    lines.append("")
    lines.append("## Hard Negative Source Audit")
    lines.append("")
    source_rows = [
        source.split(":", 1)
        for source in metrics["hard_negative_sources"].split(",")
        if ":" in source
    ]
    lines.extend(markdown_table(["Source", "Rows"], source_rows or [["none", "0"]]))
    lines.append("")
    lines.append("## Selected Extra Marmoset Cases")
    lines.append("")
    if manifest_rows:
        table_rows = [
            [
                row.get("label", ""),
                row.get("gene", ""),
                row.get("dna_bytes", "0"),
                row.get("rna_bytes", "0"),
            ]
            for row in manifest_rows
        ]
        lines.extend(
            markdown_table(
                ["Label", "Gene", "DNA bytes", "RNA bytes"],
                table_rows,
            )
        )
    else:
        lines.append("No optional marmoset cases were selected in this environment.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(
        "This PR expands the offline corpus only. A future learned-detector "
        "model shadow, if pursued, must be a separate PR and must re-check "
        "held-out behavior against the current hand-written guard."
    )
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("```text")
    lines.append("Production model added: no")
    lines.append("Runtime behavior changed: no")
    lines.append("Fasim runtime changed: no")
    lines.append("SIM-close runtime changed: no")
    lines.append("Scoring/threshold/non-overlap behavior changed: no")
    lines.append("GPU/filter behavior changed: no")
    lines.append("SIM labels used as runtime input: no")
    lines.append("Recommended/default SIM-close: no")
    lines.append("Deep learning dependency added: no")
    lines.append("```")
    lines.append("")
    lines.append(
        "No production model is trained or loaded. SIM labels remain offline "
        "labels only. They must not be used as runtime detector inputs, guard "
        "inputs, replacement inputs, or output ordering inputs."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source-dataset", required=True)
    parser.add_argument("--data-expansion-log", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--extra-marmoset-limit", type=int, required=True)
    parser.add_argument("--extra-marmoset-min-rna-bytes", type=int, required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--doc-report", default="")
    args = parser.parse_args()

    rows = read_rows(Path(args.dataset))
    source_rows = read_rows(Path(args.source_dataset))
    data_metrics = read_metric_log(Path(args.data_expansion_log))
    manifest_rows = read_manifest(Path(args.manifest))
    metrics = build_metrics(
        rows=rows,
        source_rows=source_rows,
        data_metrics=data_metrics,
        manifest_rows=manifest_rows,
        extra_marmoset_limit=args.extra_marmoset_limit,
        extra_marmoset_min_rna_bytes=args.extra_marmoset_min_rna_bytes,
    )
    for key, value in metrics.items():
        print(f"{PREFIX}.{key}={value}")

    report = render_report(metrics=metrics, manifest_rows=manifest_rows)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    if args.doc_report:
        doc_path = Path(args.doc_report)
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
