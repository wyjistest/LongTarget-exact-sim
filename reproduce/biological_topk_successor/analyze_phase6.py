#!/usr/bin/env python3
"""Analyze the frozen successor Phase 6 biological utility benchmark."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/experimental-phase6"
MANIFEST = PAPER / "experimental_benchmark_manifest.tsv"
ATTEMPT_PLAN = PAPER / "experimental_attempt_plan.tsv"
BENCHMARK_PLAN = PAPER / "experimental_benchmark_plan.json"
REGION_SCORES = PAPER / "source_data/experimental_region_scores.tsv"
METRICS = PAPER / "source_data/experimental_metrics.tsv"
FAILURES = PAPER / "source_data/experimental_failure_ledger.tsv"
BOOTSTRAP = PAPER / "source_data/experimental_bootstrap.tsv"
RECEIPT = PAPER / "biological_utility_receipt.json"
DECISION = PAPER / "biological_utility_decision.json"
BOOTSTRAP_SEED = 20260816
BOOTSTRAP_REPLICATES = 10_000
SENTINEL = -1
TFOSORTED_COLUMNS = (
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "MeanStability",
    "MeanIdentity(%)",
    "Strand",
    "Rule",
    "Score",
    "Nt(bp)",
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
)
SUPPORTED_STRANDS = frozenset({"ParaPlus", "ParaMinus", "AntiMinus", "AntiPlus"})
NONNEGATIVE_INTEGER = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*\Z", re.ASCII)


class AnalysisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError(message)


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    ).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    require(fields and all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return fields, rows


def tsv_bytes(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    import io

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in fields})
    return output.getvalue().encode("utf-8")


@dataclass(frozen=True)
class Region:
    dataset_id: str
    outer_lncRNA_id: str
    region_id: str
    label: int
    chromosome: str
    concat_start0: int
    concat_end0: int


@dataclass(frozen=True)
class RegionIndex:
    regions: tuple[Region, ...]
    starts: tuple[int, ...]
    target_end0: int


@dataclass(frozen=True)
class DatasetMetrics:
    dataset_id: str
    outer_lncRNA_id: str
    arm: str
    region_count: int
    positive_count: int
    prevalence: float
    aucpr: float
    recall_at_p: float
    precision_at_p: float
    fold_enrichment: float
    log_enrichment: float | None
    zero_precision: bool


def manifest_regions() -> list[Region]:
    _, rows = read_tsv(MANIFEST)
    regions = [
        Region(
            row["dataset_id"],
            row["outer_lncRNA_id"],
            row["region_id"],
            int(row["label"]),
            row["target_chromosome"],
            int(row["target_concat_start0"]),
            int(row["target_concat_end0"]),
        )
        for row in rows
    ]
    require(len(regions) == 5000 and len({region.region_id for region in regions}) == 5000, "experimental region manifest drift")
    return regions


def build_region_index(regions: Sequence[Region]) -> RegionIndex:
    ordered = tuple(sorted(regions, key=lambda region: (region.concat_start0, region.concat_end0, region.region_id)))
    require(ordered, "cannot index an empty region set")
    require(
        all(
            region.concat_start0 >= 0
            and region.concat_end0 > region.concat_start0
            and (index == 0 or ordered[index - 1].concat_end0 <= region.concat_start0)
            for index, region in enumerate(ordered)
        ),
        "region concatenation intervals overlap or are invalid",
    )
    return RegionIndex(ordered, tuple(region.concat_start0 for region in ordered), ordered[-1].concat_end0)


def canonical_integer(raw: str, label: str, *, positive: bool = False) -> int:
    pattern = POSITIVE_INTEGER if positive else NONNEGATIVE_INTEGER
    require(pattern.fullmatch(raw) is not None, f"{label} is not a canonical {'positive' if positive else 'nonnegative'} integer")
    return int(raw)


def normalized_target_interval(row: Mapping[str, str]) -> tuple[int, int]:
    try:
        raw_start = canonical_integer(row["StartInSeq"], "StartInSeq")
        raw_end = canonical_integer(row["EndInSeq"], "EndInSeq")
        strand = row["Strand"]
    except KeyError as error:
        raise AnalysisError(f"missing Fasim target-coordinate field: {error}") from error
    require(strand in SUPPORTED_STRANDS, f"unsupported Fasim Strand: {strand!r}")
    if strand in {"ParaPlus", "AntiMinus"}:
        start0, end0 = raw_start - 1, raw_end
    else:
        start0, end0 = raw_start, raw_end + 1
    require(0 <= start0 < end0, "normalized Fasim target interval is invalid")
    return start0, end0


def map_output_row(row: Mapping[str, str], regions: Sequence[Region] | RegionIndex) -> str | None:
    index = regions if isinstance(regions, RegionIndex) else build_region_index(regions)
    start0, end0 = normalized_target_interval(row)
    require(end0 <= index.target_end0, "normalized Fasim target interval exceeds target FASTA")
    position = bisect.bisect_right(index.starts, start0) - 1
    if position < 0:
        return None
    region = index.regions[position]
    return region.region_id if start0 >= region.concat_start0 and end0 <= region.concat_end0 else None


def parse_fasim_scores(
    path: Path,
    regions: Sequence[Region],
    *,
    query_length: int | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    scores = {region.region_id: SENTINEL for region in regions}
    valid_counts = {region.region_id: 0 for region in regions}
    index = build_region_index(regions)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == TFOSORTED_COLUMNS, f"Fasim output schema drift: {path}")
        for row_number, row in enumerate(reader, 2):
            require(None not in row and all(value is not None for value in row.values()), f"malformed Fasim row {row_number}: {path}")
            query_start = canonical_integer(row["QueryStart"], "QueryStart", positive=True)
            query_end = canonical_integer(row["QueryEnd"], "QueryEnd", positive=True)
            require(query_end >= query_start, f"invalid Fasim query interval at row {row_number}: {path}")
            if query_length is not None:
                require(query_end <= query_length, f"Fasim query interval exceeds query FASTA at row {row_number}: {path}")
            require(row["Direction"] == "R", f"unsupported Fasim Direction at row {row_number}: {path}")
            canonical_integer(row["StartInGenome"], "StartInGenome")
            canonical_integer(row["EndInGenome"], "EndInGenome")
            canonical_integer(row["Rule"], "Rule")
            canonical_integer(row["Class"], "Class")
            canonical_integer(row["MidPoint"], "MidPoint")
            canonical_integer(row["Center"], "Center")
            nt = canonical_integer(row["Nt(bp)"], "Nt(bp)")
            score = canonical_integer(row["Score"], "Score")
            try:
                stability = float(row["MeanStability"])
                identity = float(row["MeanIdentity(%)"])
            except ValueError as error:
                raise AnalysisError(f"invalid Fasim decimal at row {row_number}: {path}") from error
            require(math.isfinite(stability) and math.isfinite(identity) and 0 <= identity <= 100, f"invalid Fasim stability/identity at row {row_number}: {path}")
            require(bool(row["TFO sequence"]) and bool(row["TTS sequence"]), f"empty Fasim aligned sequence at row {row_number}: {path}")
            if nt <= 50:
                continue
            region_id = map_output_row(row, index)
            if region_id is None:
                continue
            scores[region_id] = max(scores[region_id], score)
            valid_counts[region_id] += 1
    return scores, valid_counts


def average_precision(labels: Sequence[int], scores: Sequence[int], identities: Sequence[str]) -> float:
    require(len(labels) == len(scores) == len(identities) and labels, "invalid AUCPR inputs")
    positives = sum(labels)
    require(positives > 0, "AUCPR undefined without positives")
    order = sorted(range(len(labels)), key=lambda index: (-scores[index], identities[index]))
    seen_positive = 0
    precision_sum = 0.0
    for rank, index in enumerate(order, 1):
        if labels[index]:
            seen_positive += 1
            precision_sum += seen_positive / rank
    return precision_sum / positives


def dataset_metrics(regions: Sequence[Region], scores: Mapping[str, int], arm: str) -> DatasetMetrics:
    require(regions and len({region.dataset_id for region in regions}) == 1, "dataset metric received mixed datasets")
    labels = [region.label for region in regions]
    values = [scores[region.region_id] for region in regions]
    identities = [region.region_id for region in regions]
    positives = sum(labels)
    require(positives > 0, "dataset has no positives")
    order = sorted(range(len(regions)), key=lambda index: (-values[index], identities[index]))
    top = order[:positives]
    true_positives = sum(labels[index] for index in top)
    recall = true_positives / positives
    precision = true_positives / len(top)
    prevalence = positives / len(regions)
    fold = precision / prevalence
    log_enrichment = None if precision == 0 else math.log(fold)
    return DatasetMetrics(
        regions[0].dataset_id,
        regions[0].outer_lncRNA_id,
        arm,
        len(regions),
        positives,
        prevalence,
        average_precision(labels, values, identities),
        recall,
        precision,
        fold,
        log_enrichment,
        precision == 0,
    )


def endpoint_values(a: DatasetMetrics, g: DatasetMetrics) -> tuple[float, float, float, float | None]:
    require(a.dataset_id == g.dataset_id and a.outer_lncRNA_id == g.outer_lncRNA_id, "unpaired A/G dataset metrics")
    return (
        g.aucpr - a.aucpr,
        g.recall_at_p - a.recall_at_p,
        g.aucpr - g.prevalence,
        g.log_enrichment,
    )


def paired_hierarchical_bootstrap(
    regions: Sequence[Region],
    arm_scores: Mapping[str, Mapping[str, int]],
    *,
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> tuple[list[tuple[float, float, float, float]], dict[str, Any]]:
    by_lnc: dict[str, list[Region]] = defaultdict(list)
    for region in regions:
        by_lnc[region.outer_lncRNA_id].append(region)
    lnc_ids = sorted(by_lnc)
    require(len(lnc_ids) == 5, "bootstrap outer lncRNA count drift")
    rng = np.random.default_rng(seed)
    output: list[tuple[float, float, float, float]] = []
    index_digest = hashlib.sha256()
    for _ in range(replicates):
        sampled_lnc_indices = rng.integers(0, len(lnc_ids), size=len(lnc_ids))
        index_digest.update(sampled_lnc_indices.astype("<i8", copy=False).tobytes())
        outer_values: list[tuple[float, float, float, float]] = []
        for lnc_index in sampled_lnc_indices:
            lnc_regions = by_lnc[lnc_ids[int(lnc_index)]]
            by_chromosome: dict[str, list[Region]] = defaultdict(list)
            for region in lnc_regions:
                by_chromosome[region.chromosome].append(region)
            chromosomes = sorted(by_chromosome)
            sampled_chromosome_indices = rng.integers(0, len(chromosomes), size=len(chromosomes))
            index_digest.update(sampled_chromosome_indices.astype("<i8", copy=False).tobytes())
            sampled_regions: list[Region] = []
            sampled_a: dict[str, int] = {}
            sampled_g: dict[str, int] = {}
            occurrence = 0
            for chromosome_index in sampled_chromosome_indices:
                chromosome = chromosomes[int(chromosome_index)]
                for region in by_chromosome[chromosome]:
                    occurrence += 1
                    synthetic_id = f"{region.region_id}__bootstrap_{occurrence}"
                    sampled_regions.append(
                        Region(region.dataset_id, region.outer_lncRNA_id, synthetic_id, region.label, region.chromosome, region.concat_start0, region.concat_end0)
                    )
                    sampled_a[synthetic_id] = arm_scores["A"][region.region_id]
                    sampled_g[synthetic_id] = arm_scores["G"][region.region_id]
            a_metrics = dataset_metrics(sampled_regions, sampled_a, "A")
            g_metrics = dataset_metrics(sampled_regions, sampled_g, "G")
            values = endpoint_values(a_metrics, g_metrics)
            e4 = float("-inf") if values[3] is None else float(values[3])
            outer_values.append((values[0], values[1], values[2], e4))
        output.append(tuple(sum(values[index] for values in outer_values) / len(outer_values) for index in range(4)))
    return output, {
        "seed": seed,
        "replicates": replicates,
        "shared_resample_index_for_all_endpoints": True,
        "paired_A_G_at_every_level": True,
        "outer_unit": "distinct_lncRNA",
        "nested_block": "chromosome",
        "zero_precision_resample_rule": "negative_infinity_E4_no_pseudocount_or_replacement",
        "index_stream_sha256": index_digest.hexdigest(),
    }


def percentile_lcb(values: Sequence[float]) -> float:
    require(values and all(not math.isnan(value) and value != float("inf") for value in values), "invalid bootstrap endpoint")
    return float(np.quantile(np.asarray(values, dtype=np.float64), 0.05, method="inverted_cdf"))


def attempt_receipts(attempts: Sequence[Mapping[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    receipts: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for attempt in attempts:
        path = ROOT / attempt["artifact_root"] / "attempt-complete.json"
        if not path.is_file():
            failures.append({"attempt_id": attempt["attempt_id"], "dataset_id": attempt["dataset_id"], "arm": attempt["arm"], "failure_reason": "missing_terminal_receipt"})
            continue
        receipt = read_json(path)
        require(receipt["schema_version"] == 1 and receipt["phase"] == 6, "attempt receipt schema/phase drift")
        require(receipt["attempt_id"] == attempt["attempt_id"], "attempt receipt identity drift")
        require(receipt["dataset_id"] == attempt["dataset_id"] and receipt["arm"] == attempt["arm"], "attempt receipt dataset/arm drift")
        require(receipt["status"] in {"success", "technical_failure"}, "attempt receipt is not terminal")
        require(receipt["attempt_config_sha256"] == canonical_digest(dict(attempt)), "attempt receipt config drift")
        require(receipt["query_fasta_sha256"] == attempt["query_fasta_sha256"], "attempt query FASTA binding drift")
        require(receipt["target_fasta_sha256"] == attempt["target_fasta_sha256"], "attempt target FASTA binding drift")
        require(receipt["binary_sha256"] == attempt["binary_sha256"], "attempt binary binding drift")
        require(receipt["labels_visible_to_backend"] is False, "attempt backend saw labels")
        require(receipt["label_manifest_mounted_in_sandbox"] is False, "attempt sandbox mounted labels")
        require(receipt["comparison_started"] is False, "attempt performed a comparison")
        require(receipt["retry_policy"] == "none" and receipt["replacement_retry_allowed"] is False, "attempt retry policy drift")
        if receipt["status"] == "success":
            output_relative = Path(str(receipt["output_path"]))
            require(
                not output_relative.is_absolute() and ".." not in output_relative.parts,
                "unsafe attempt output path",
            )
            output = path.parent / output_relative
            require(output.is_file() and not output.is_symlink(), "successful attempt output missing")
            require(sha256_file(output) == receipt["output_sha256"], "successful attempt output digest drift")
        else:
            require(isinstance(receipt["failure_reason"], str) and receipt["failure_reason"], "technical failure lacks reason")
        receipts.append(receipt)
        if receipt["status"] != "success":
            failures.append({"attempt_id": attempt["attempt_id"], "dataset_id": attempt["dataset_id"], "arm": attempt["arm"], "failure_reason": str(receipt["failure_reason"])})
    return receipts, failures


def single_fasta_length(path: Path) -> int:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe FASTA: {path}")
    records = 0
    length = 0
    active = False
    with path.open(encoding="ascii") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.rstrip("\r\n")
            if line.startswith(">"):
                records += 1
                active = True
                continue
            require(active and line and line == line.strip(), f"malformed FASTA at line {line_number}: {path}")
            require(not (set(line) - set("ACGTN")), f"unsupported FASTA alphabet: {path}")
            length += len(line)
    require(records == 1 and length > 0, f"FASTA must contain one nonempty record: {path}")
    return length


def preflight() -> dict[str, Any]:
    plan = read_json(BENCHMARK_PLAN)
    _, attempts = read_tsv(ATTEMPT_PLAN)
    require(plan["evaluation_prediction_started"] is False, "Phase 5 plan claims evaluation prediction")
    require(len(attempts) == 15 and {row["arm"] for row in attempts} == {"A", "G", "X"}, "experimental attempt plan drift")
    require(all(row["labels_visible_to_backend"] == "0" for row in attempts), "attempt backend can see labels")
    require(not ARTIFACT_ROOT.exists(), "Phase 6 prediction artifact root exists before execution")
    return {
        "status": "preflight_pass",
        "region_count": plan["dataset_count"] * plan["regions_per_dataset"],
        "attempt_count": len(attempts),
        "prediction_started": False,
        "manifest_labels_read": False,
    }


SCORE_FIELDS = ("dataset_id", "outer_lncRNA_id", "region_id", "label", "target_chromosome", "arm", "region_score", "valid_row_count")
METRIC_FIELDS = (
    "dataset_id",
    "outer_lncRNA_id",
    "arm",
    "region_count",
    "positive_count",
    "prevalence",
    "aucpr",
    "recall_at_P",
    "precision_at_P",
    "fold_enrichment",
    "log_enrichment",
    "zero_precision",
)
FAILURE_FIELDS = ("attempt_id", "dataset_id", "arm", "failure_reason")
BOOTSTRAP_FIELDS = ("replicate", "E1", "E2", "E3", "E4")


def analyze() -> dict[Path, bytes]:
    plan = read_json(BENCHMARK_PLAN)
    _, attempts = read_tsv(ATTEMPT_PLAN)
    summary = read_json(ARTIFACT_ROOT / "run-summary.json")
    require(summary["status"] == "complete", "analysis barrier requires a complete run summary")
    require(summary["planned_attempt_count"] == summary["terminal_attempt_count"] == 15, "analysis barrier requires all attempts terminal")
    require(summary["comparison_started"] is False, "runner performed prohibited comparison")
    receipts, failure_rows = attempt_receipts(attempts)
    require(len(receipts) == len(attempts) == 15, "labels remain sealed until all 15 terminal receipts validate")
    require(summary["successful_attempt_count"] == sum(receipt["status"] == "success" for receipt in receipts), "run-summary success count drift")
    require(summary["technical_failure_count"] == sum(receipt["status"] != "success" for receipt in receipts), "run-summary failure count drift")
    snapshot = read_json(ARTIFACT_ROOT / "execution-snapshot.json")
    require(all(receipt["source_commit"] == snapshot["source_commit"] for receipt in receipts), "attempt source commit drift")
    require(snapshot["labels_copied_or_mounted"] is False and snapshot["comparison_started"] is False, "execution snapshot violated label/comparison barrier")

    # This is the first label read in Phase 6, after every attempt is terminal.
    regions = manifest_regions()
    primary_failures = [row for row in failure_rows if row["arm"] in {"A", "G"}]

    by_dataset: dict[str, list[Region]] = defaultdict(list)
    for region in regions:
        by_dataset[region.dataset_id].append(region)
    arm_scores: dict[str, dict[str, int]] = {"A": {}, "G": {}}
    score_rows: list[dict[str, Any]] = []
    metric_values: dict[tuple[str, str], DatasetMetrics] = {}
    if not primary_failures:
        for attempt in attempts:
            if attempt["arm"] not in {"A", "G"}:
                continue
            receipt = next(value for value in receipts if value["attempt_id"] == attempt["attempt_id"])
            output = ROOT / attempt["artifact_root"] / receipt["output_path"]
            query_length = single_fasta_length(ROOT / attempt["query_fasta_path"])
            scores, counts = parse_fasim_scores(
                output,
                by_dataset[attempt["dataset_id"]],
                query_length=query_length,
            )
            arm_scores[attempt["arm"]].update(scores)
            for region in by_dataset[attempt["dataset_id"]]:
                score_rows.append(
                    {
                        "dataset_id": region.dataset_id,
                        "outer_lncRNA_id": region.outer_lncRNA_id,
                        "region_id": region.region_id,
                        "label": region.label,
                        "target_chromosome": region.chromosome,
                        "arm": attempt["arm"],
                        "region_score": scores[region.region_id],
                        "valid_row_count": counts[region.region_id],
                    }
                )
            metric_values[(attempt["dataset_id"], attempt["arm"])] = dataset_metrics(by_dataset[attempt["dataset_id"]], scores, attempt["arm"])

    metric_rows: list[dict[str, Any]] = []
    for key in sorted(metric_values):
        metric = metric_values[key]
        metric_rows.append(
            {
                "dataset_id": metric.dataset_id,
                "outer_lncRNA_id": metric.outer_lncRNA_id,
                "arm": metric.arm,
                "region_count": metric.region_count,
                "positive_count": metric.positive_count,
                "prevalence": format(metric.prevalence, ".17g"),
                "aucpr": format(metric.aucpr, ".17g"),
                "recall_at_P": format(metric.recall_at_p, ".17g"),
                "precision_at_P": format(metric.precision_at_p, ".17g"),
                "fold_enrichment": format(metric.fold_enrichment, ".17g"),
                "log_enrichment": "" if metric.log_enrichment is None else format(metric.log_enrichment, ".17g"),
                "zero_precision": int(metric.zero_precision),
            }
        )

    zero_precision = any(metric.arm == "G" and metric.zero_precision for metric in metric_values.values())
    bootstrap_rows: list[dict[str, Any]] = []
    bootstrap_meta: dict[str, Any] | None = None
    lcbs: dict[str, float | None] = {endpoint: None for endpoint in ("E1", "E2", "E3", "E4")}
    endpoint_pass = {endpoint: False for endpoint in lcbs}
    point_estimates: dict[str, float | None] = {endpoint: None for endpoint in lcbs}
    if not primary_failures and not zero_precision:
        for dataset_id in by_dataset:
            require((dataset_id, "A") in metric_values and (dataset_id, "G") in metric_values, "missing primary dataset metric")
        point_by_dataset = [endpoint_values(metric_values[(dataset_id, "A")], metric_values[(dataset_id, "G")]) for dataset_id in sorted(by_dataset)]
        for index, endpoint in enumerate(("E1", "E2", "E3", "E4")):
            point_estimates[endpoint] = sum(float(values[index]) for values in point_by_dataset) / len(point_by_dataset)
        samples, bootstrap_meta = paired_hierarchical_bootstrap(regions, arm_scores)
        for replicate, values in enumerate(samples, 1):
            bootstrap_rows.append({"replicate": replicate, "E1": format(values[0], ".17g"), "E2": format(values[1], ".17g"), "E3": format(values[2], ".17g"), "E4": format(values[3], ".17g")})
        for index, endpoint in enumerate(("E1", "E2", "E3", "E4")):
            lcbs[endpoint] = percentile_lcb([values[index] for values in samples])
        endpoint_pass = {
            "E1": float(lcbs["E1"]) >= -0.02,
            "E2": float(lcbs["E2"]) >= -0.05,
            "E3": float(lcbs["E3"]) > 0,
            "E4": float(lcbs["E4"]) > 0,
        }

    biological_pass = not primary_failures and not zero_precision and all(endpoint_pass.values())
    decision_name = "pass" if biological_pass else "no_go"
    output_payloads = {
        REGION_SCORES: tsv_bytes(SCORE_FIELDS, sorted(score_rows, key=lambda row: (row["dataset_id"], row["arm"], row["region_id"]))),
        METRICS: tsv_bytes(METRIC_FIELDS, metric_rows),
        FAILURES: tsv_bytes(FAILURE_FIELDS, failure_rows),
        BOOTSTRAP: tsv_bytes(BOOTSTRAP_FIELDS, bootstrap_rows),
    }
    receipt_value = {
        "schema_version": 1,
        "phase": 6,
        "status": "complete",
        "source_phase5_plan_sha256": sha256_file(BENCHMARK_PLAN),
        "manifest_sha256": sha256_file(MANIFEST),
        "attempt_plan_sha256": sha256_file(ATTEMPT_PLAN),
        "run_summary_sha256": sha256_file(ARTIFACT_ROOT / "run-summary.json"),
        "planned_attempts": 15,
        "terminal_attempts": len(receipts),
        "successful_attempts": sum(receipt["status"] == "success" for receipt in receipts),
        "technical_failures": len(failure_rows),
        "primary_technical_failures": len(primary_failures),
        "comparison_started_only_after_all_attempts_terminal": True,
        "labels_unsealed_only_by_offline_analyzer": True,
        "distinct_lncRNA_outer_units": 5,
        "bootstrap": bootstrap_meta,
        "source_data_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(payload).hexdigest() for path, payload in output_payloads.items()},
        "infrastructure_repair_epochs_used": 0,
        "scientific_retries_or_replacements": 0,
    }
    output_payloads[RECEIPT] = canonical_json_bytes(receipt_value)
    decision_value = {
        "schema_version": 1,
        "phase": 6,
        "decision": decision_name,
        "biological_utility_pass": biological_pass,
        "distinct_lncRNA_outer_units": 5,
        "minimum_distinct_lncRNA_gate_pass": True,
        "primary_dataset_count": 5,
        "primary_technical_failure_count": len(primary_failures),
        "missing_primary_output_count": sum(row["failure_reason"] == "missing_terminal_receipt" and row["arm"] in {"A", "G"} for row in failure_rows),
        "zero_precision_primary_dataset": zero_precision,
        "zero_precision_rule": "automatic_E4_and_global_failure_no_pseudocount",
        "point_estimates": {key: None if value is None else format(value, ".17g") for key, value in point_estimates.items()},
        "one_sided_95_lcb": {key: None if value is None else format(value, ".17g") for key, value in lcbs.items()},
        "endpoint_pass": endpoint_pass,
        "intersection_union_gate": "E1_AND_E2_AND_E3_AND_E4",
        "all_four_endpoints_use_identical_paired_resample_indices": bootstrap_meta is not None,
        "cross_assay_generality_claim": "not_supported",
        "gpu_screen_status_if_applied": "experimental",
        "contract_status_if_applied": "concordance_and_utility_pass" if biological_pass else "biological_utility_no_go",
        "bioinformatics_route_if_applied": "conditionally_reopened" if biological_pass else "closed_biological_utility_gap",
        "later_phase_authorized": biological_pass,
        "biological_utility_receipt_sha256": hashlib.sha256(output_payloads[RECEIPT]).hexdigest(),
    }
    output_payloads[DECISION] = canonical_json_bytes(decision_value)
    return output_payloads


def write_payloads(payloads: Mapping[Path, bytes]) -> None:
    for path, payload in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--analyze", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.preflight:
            print(json.dumps(preflight(), sort_keys=True))
            return 0
        payloads = analyze()
        if args.analyze:
            write_payloads(payloads)
            print(f"wrote {len(payloads)} successor Phase 6 analysis artifacts")
            return 0
        stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.is_symlink() or path.read_bytes() != payload]
        require(not stale, f"Phase 6 analysis artifacts do not reproduce: {stale}")
        print("successor Phase 6 analysis artifacts reproduce byte-for-byte")
        return 0
    except (AnalysisError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"successor Phase 6 analysis failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
