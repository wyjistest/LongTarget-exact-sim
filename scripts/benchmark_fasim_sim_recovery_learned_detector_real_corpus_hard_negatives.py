#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence


PREFIX = "benchmark.fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.total"
REPORT_PREFIX = "fasim_sim_recovery_learned_detector_real_corpus_hard_negatives"
REQUESTED_NEGATIVE_SOURCES = [
    "executor_candidate_non_sim",
    "extra_vs_sim_candidate",
    "fasim_supported_non_sim",
    "near_threshold_rejected_candidate",
    "no_legacy_sim_records_proxy",
]
DEFAULT_EXCLUDED_MARMOSET_GENES = {
    "ENSG00000259006.1",
    "ENSG00000233639.1",
    "ENSG00000229743.2",
}


@dataclass(frozen=True)
class MarmosetCase:
    label: str
    dna_path: Path
    rna_path: Path
    gene: str
    dna_bytes: int
    rna_bytes: int

    @property
    def total_bytes(self) -> int:
        return self.dna_bytes + self.rna_bytes


def safe_label(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip())
    return cleaned.strip("_") or "unknown"


def safe_metric_value(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:,|=-]+", "_", value.strip())
    return cleaned.strip("_") or "none"


def parse_float(value: str) -> float:
    if value in ("", "NA", None):
        return 0.0
    return float(value)


def split_for_key(split_key: str) -> str:
    return "validation" if zlib.crc32(split_key.encode("utf-8")) % 5 == 0 else "train"


def current_split(row: Dict[str, str]) -> str:
    return row.get("split", "train")


def family_heldout_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("family_id", "unknown"))


def workload_heldout_split(row: Dict[str, str]) -> str:
    return split_for_key(row.get("workload_id", "unknown"))


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


def source_counts_string(counts: Counter[str] | Dict[str, int]) -> str:
    nonzero = [(key, value) for key, value in sorted(counts.items()) if value]
    return ",".join(f"{key}:{value}" for key, value in nonzero) or "none"


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


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def fasta_files(path: Path) -> List[Path]:
    files: List[Path] = []
    for pattern in ("*.fa", "*.fasta", "*.fna"):
        files.extend(path.glob(pattern))
    return sorted({item.resolve() for item in files})


def fasta_sequence_length(path: Path) -> int:
    length = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                continue
            length += len(line.strip())
    return length


def header_interval_span(path: Path) -> int | None:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                matches = re.findall(r"(\d+)-(\d+)", line)
                if not matches:
                    return None
                start, end = matches[-1]
                return abs(int(end) - int(start)) + 1
    return None


def fasta_interval_sane(path: Path) -> bool:
    span = header_interval_span(path)
    if span is None:
        return True
    return span == fasta_sequence_length(path)


def smallest_file(paths: Sequence[Path], *, require_interval_sane: bool) -> Path | None:
    if not paths:
        return None
    for path in sorted(paths, key=lambda item: (item.stat().st_size, str(item))):
        if not require_interval_sane or fasta_interval_sane(path):
            return path
    return None


def discover_marmoset_pairs(root: Path) -> List[MarmosetCase]:
    if not root.is_dir():
        return []

    cases: List[MarmosetCase] = []
    for rna_dir in sorted(root.glob("*_marmoset")):
        if not rna_dir.is_dir() or rna_dir.name.endswith("_marmoset-targetDNA"):
            continue
        gene = rna_dir.name[: -len("_marmoset")]
        dna_dir = root / f"{gene}_marmoset-targetDNA"
        if not dna_dir.is_dir():
            continue
        rna_path = smallest_file(fasta_files(rna_dir), require_interval_sane=False)
        dna_path = smallest_file(fasta_files(dna_dir), require_interval_sane=True)
        if rna_path is None or dna_path is None:
            continue
        cases.append(
            MarmosetCase(
                label=f"marmoset_extra_{safe_label(gene)}",
                dna_path=dna_path,
                rna_path=rna_path,
                gene=gene,
                dna_bytes=dna_path.stat().st_size,
                rna_bytes=rna_path.stat().st_size,
            )
        )
    return cases


def select_extra_cases(
    cases: Sequence[MarmosetCase],
    *,
    limit: int,
    min_rna_bytes: int,
    excluded_genes: set[str],
) -> List[MarmosetCase]:
    if limit <= 0:
        return []
    candidates = [
        case
        for case in cases
        if case.gene not in excluded_genes and case.rna_bytes >= min_rna_bytes
    ]
    return sorted(candidates, key=lambda case: (case.total_bytes, case.gene))[:limit]


def write_manifest(path: Path, cases: Sequence[MarmosetCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["label", "dna_path", "rna_path", "gene", "dna_bytes", "rna_bytes"])
        for case in cases:
            writer.writerow(
                [
                    case.label,
                    str(case.dna_path),
                    str(case.rna_path),
                    case.gene,
                    str(case.dna_bytes),
                    str(case.rna_bytes),
                ]
            )


def read_manifest(path: Path) -> List[MarmosetCase]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [
            MarmosetCase(
                label=row["label"],
                dna_path=Path(row["dna_path"]).resolve(),
                rna_path=Path(row["rna_path"]).resolve(),
                gene=row["gene"],
                dna_bytes=int(row.get("dna_bytes", "0") or 0),
                rna_bytes=int(row.get("rna_bytes", "0") or 0),
            )
            for row in reader
            if row.get("label")
        ]


def source_counts(rows: Sequence[Dict[str, str]]) -> Counter[str]:
    return Counter(row.get("hard_negative_source", "NA") for row in rows if row.get("label") == "0")


def source_kind_counts(rows: Sequence[Dict[str, str]]) -> Counter[str]:
    return Counter(row.get("source", "NA") for row in rows)


def data_line_metrics(
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
) -> Dict[str, str]:
    labels = Counter(row.get("label", "0") for row in rows)
    hard_negative_sources = source_counts(rows)
    source_avail = source_availability(source_rows)
    current = split_counts(rows, current_split)
    family = split_counts(rows, family_heldout_split)
    workload = split_counts(rows, workload_heldout_split)
    unique_workloads = len({row.get("workload_id", "unknown") for row in rows})
    unique_families = len({row.get("family_id", "unknown") for row in rows})
    validate_supported_workloads = {
        row.get("workload_label", "unknown")
        for row in source_rows
        if row.get("validate_supported") == "1"
    }
    no_legacy_workloads = {
        row.get("workload_label", "unknown")
        for row in source_rows
        if row.get("validate_unsupported_reason") == "no_legacy_sim_records"
    }
    hard_negative_source_count = sum(1 for value in hard_negative_sources.values() if value)
    heldout_workload_available = unique_workloads >= 2 and workload["degenerate"] == "0"
    heldout_family_available = unique_families >= 2 and family["degenerate"] == "0"
    candidate_eligible_positive = sum(
        1 for row in rows if row.get("label") == "1" and row.get("source") != "sim_record_target_positive"
    )
    candidate_eligible_negative = sum(1 for row in rows if row.get("label") == "0")
    missing_requested_sources = [
        source
        for source in REQUESTED_NEGATIVE_SOURCES
        if hard_negative_sources.get(source, 0) == 0
    ]
    if not heldout_workload_available:
        modeling_gate = "collect_more_workloads"
    elif not heldout_family_available:
        modeling_gate = "collect_more_families"
    elif hard_negative_source_count < 3:
        modeling_gate = "collect_more_hard_negatives"
    else:
        modeling_gate = "ready_for_offline_shadow"

    metrics = {
        "enabled": "1",
        "rows": str(len(rows)),
        "positive_rows": str(labels.get("1", 0)),
        "negative_rows": str(labels.get("0", 0)),
        "learnable_two_class": "1" if labels.get("1", 0) and labels.get("0", 0) else "0",
        "source_rows": str(len(source_rows)),
        "workload_count": str(unique_workloads),
        "family_count": str(unique_families),
        "validate_supported_workload_count": str(len(validate_supported_workloads)),
        "no_legacy_sim_records_workload_count": str(len(no_legacy_workloads)),
        "unique_workloads": str(unique_workloads),
        "unique_families": str(unique_families),
        "hard_negative_sources": source_counts_string(hard_negative_sources),
        "hard_negative_source_count": str(hard_negative_source_count),
        "available_requested_negative_sources": source_counts_string(source_avail),
        "missing_requested_negative_sources": safe_metric_value(",".join(missing_requested_sources) or "none"),
        "candidate_eligible_positive_rows": str(candidate_eligible_positive),
        "candidate_eligible_negative_rows": str(candidate_eligible_negative),
        "heldout_workload_available": "1" if heldout_workload_available else "0",
        "heldout_family_available": "1" if heldout_family_available else "0",
        "modeling_gate": modeling_gate,
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
    return metrics


def selected_case_value(cases: Sequence[MarmosetCase]) -> str:
    return safe_metric_value(",".join(case.label for case in cases) or "none")


def discovery_metrics(
    *,
    discovered: Sequence[MarmosetCase],
    selected: Sequence[MarmosetCase],
    limit: int,
    min_rna_bytes: int,
) -> Dict[str, str]:
    excluded_discovered = sum(1 for case in discovered if case.gene in DEFAULT_EXCLUDED_MARMOSET_GENES)
    eligible_discovered = sum(
        1
        for case in discovered
        if case.gene not in DEFAULT_EXCLUDED_MARMOSET_GENES and case.rna_bytes >= min_rna_bytes
    )
    return {
        "enabled": "1",
        "discovered_marmoset_pair_count": str(len(discovered)),
        "excluded_existing_marmoset_pair_count": str(excluded_discovered),
        "eligible_extra_marmoset_pair_count": str(eligible_discovered),
        "extra_marmoset_limit": str(limit),
        "extra_marmoset_min_rna_bytes": str(min_rna_bytes),
        "selected_extra_case_count": str(len(selected)),
        "selected_extra_cases": selected_case_value(selected),
        "production_model": "0",
        "sim_labels_runtime_inputs": "0",
        "runtime_behavior_changed": "0",
    }


def combined_metrics(
    *,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    discovered: Sequence[MarmosetCase],
    selected: Sequence[MarmosetCase],
    limit: int,
    min_rna_bytes: int,
) -> Dict[str, str]:
    metrics = data_line_metrics(rows, source_rows)
    metrics.update(
        discovery_metrics(
            discovered=discovered,
            selected=selected,
            limit=limit,
            min_rna_bytes=min_rna_bytes,
        )
    )
    metrics["real_corpus_data_line"] = "1"
    metrics["runtime_model_path"] = "paused"
    metrics["model_training_added"] = "0"
    metrics["deep_learning_dependency"] = "0"
    metrics["recommended_default_sim_close"] = "0"
    metrics["selected_extra_source_rows"] = str(
        sum(1 for row in source_rows if row.get("workload_label") in {case.label for case in selected})
    )
    metrics["selected_extra_negative_rows"] = str(
        sum(1 for row in rows if row.get("workload_id") in {case.label for case in selected} and row.get("label") == "0")
    )
    metrics["selected_extra_positive_rows"] = str(
        sum(1 for row in rows if row.get("workload_id") in {case.label for case in selected} and row.get("label") == "1")
    )
    return metrics


def render_report(
    *,
    dataset_path: Path,
    source_dataset_path: Path,
    negative_dataset_report: Path,
    rows: Sequence[Dict[str, str]],
    source_rows: Sequence[Dict[str, str]],
    selected: Sequence[MarmosetCase],
    metrics: Dict[str, str],
) -> str:
    hard_negative_sources = source_counts(rows)
    source_avail = source_availability(source_rows)
    source_kinds = source_kind_counts(source_rows)
    lines: List[str] = []
    lines.append("# Fasim SIM-Close Learned Detector Real-Corpus Hard Negatives")
    lines.append("")
    lines.append("## Real-Corpus Expansion")
    lines.append("")
    lines.append(
        "This report expands the offline learned-detector data line with bounded "
        "optional marmoset real-corpus cases when local FASTA pairs are available. "
        "It collects hard-negative evidence only; it does not train a model or "
        "change runtime behavior."
    )
    lines.append("")
    lines.append(f"Input negative dataset: `{dataset_path}`")
    lines.append(f"Input source learned dataset: `{source_dataset_path}`")
    lines.append(f"Negative dataset report: `{negative_dataset_report}`")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key, value in metrics.items():
        lines.append(f"| {REPORT_PREFIX}_{key} | {value} |")
    lines.append("")
    lines.append("## Selected Extra Marmoset Cases")
    lines.append("")
    lines.append("| Label | Gene | DNA bytes | RNA bytes | DNA | RNA |")
    lines.append("| --- | --- | ---: | ---: | --- | --- |")
    if selected:
        for case in selected:
            lines.append(
                f"| {case.label} | {case.gene} | {case.dna_bytes} | {case.rna_bytes} | "
                f"`{case.dna_path}` | `{case.rna_path}` |"
            )
    else:
        lines.append("| none | none | 0 | 0 | NA | NA |")
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
    lines.append("## Corpus Gate")
    lines.append("")
    lines.append("| Gate | Value |")
    lines.append("| --- | --- |")
    for key in (
        "workload_count",
        "family_count",
        "validate_supported_workload_count",
        "no_legacy_sim_records_workload_count",
        "hard_negative_source_count",
        "heldout_workload_available",
        "heldout_family_available",
        "modeling_gate",
    ):
        lines.append(f"| {key} | {metrics[key]} |")
    lines.append("")
    lines.append(
        "This PR deliberately stays on the data-expansion path after the #88 "
        "negative model result. Any future model shadow should be a separate "
        "offline evaluation PR and must re-check held-out behavior."
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
    return "\n".join(lines).rstrip() + "\n"


def print_metrics(metrics: Dict[str, str]) -> None:
    for key, value in metrics.items():
        print(f"{PREFIX}.{key}={value}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover-marmoset-root", required=True)
    parser.add_argument("--extra-marmoset-limit", type=int, default=9)
    parser.add_argument("--extra-marmoset-min-rna-bytes", type=int, default=700)
    parser.add_argument("--write-manifest", default="")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--dataset", default="")
    parser.add_argument("--source-dataset", default="")
    parser.add_argument("--negative-dataset-report", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--doc-report", default="")
    args = parser.parse_args()

    try:
        root = Path(args.discover_marmoset_root).resolve()
        limit = max(args.extra_marmoset_limit, 0)
        min_rna_bytes = max(args.extra_marmoset_min_rna_bytes, 0)
        discovered = discover_marmoset_pairs(root)
        selected = select_extra_cases(
            discovered,
            limit=limit,
            min_rna_bytes=min_rna_bytes,
            excluded_genes=DEFAULT_EXCLUDED_MARMOSET_GENES,
        )
        if args.write_manifest:
            write_manifest(Path(args.write_manifest).resolve(), selected)
        if args.manifest:
            selected = read_manifest(Path(args.manifest).resolve())

        if not args.dataset or not args.source_dataset:
            print_metrics(
                discovery_metrics(
                    discovered=discovered,
                    selected=selected,
                    limit=limit,
                    min_rna_bytes=min_rna_bytes,
                )
            )
            return 0

        dataset_path = Path(args.dataset).resolve()
        source_dataset_path = Path(args.source_dataset).resolve()
        negative_dataset_report = Path(args.negative_dataset_report).resolve()
        rows = read_rows(dataset_path)
        source_rows = read_rows(source_dataset_path)
        metrics = combined_metrics(
            rows=rows,
            source_rows=source_rows,
            discovered=discovered,
            selected=selected,
            limit=limit,
            min_rna_bytes=min_rna_bytes,
        )
        report = render_report(
            dataset_path=dataset_path,
            source_dataset_path=source_dataset_path,
            negative_dataset_report=negative_dataset_report,
            rows=rows,
            source_rows=source_rows,
            selected=selected,
            metrics=metrics,
        )
        for output in [args.report, args.doc_report]:
            if output:
                output_path = Path(output).resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(report, encoding="utf-8")
        print_metrics(metrics)
        print(report.rstrip())
        return 0
    except Exception as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
