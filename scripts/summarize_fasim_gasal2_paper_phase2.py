#!/usr/bin/env python3
"""Export and summarize immutable Phase 2 paper benchmark receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import statistics
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
RUNTIME_EPOCH = 0
SUMMARY_FIELDS = [
    "workload_id",
    "claim_id",
    "output_contract",
    "valid_pairs",
    "median_baseline_wall_seconds",
    "baseline_wall_q1_seconds",
    "baseline_wall_q3_seconds",
    "baseline_wall_min_seconds",
    "baseline_wall_max_seconds",
    "median_candidate_wall_seconds",
    "candidate_wall_q1_seconds",
    "candidate_wall_q3_seconds",
    "candidate_wall_min_seconds",
    "candidate_wall_max_seconds",
    "median_paired_speedup",
    "paired_speedup_q1",
    "paired_speedup_q3",
    "paired_speedup_min",
    "paired_speedup_max",
    "top5_contract_clean",
    "full_output_contract_clean",
    "fallbacks_total",
    "oom_total",
    "diagnostic_missing_rows_total",
    "diagnostic_extra_rows_total",
    "baseline_gpu_memory_peak_mib",
    "candidate_gpu_memory_peak_mib",
    "baseline_rss_peak_kb",
    "candidate_rss_peak_kb",
]
OPERATING_ENVELOPE_IDS = {
    "chr1_full",
    "chr22_full",
    "h19_short_integrated",
    "malat1_first8",
    "neat1_first64",
}
OPERATING_FIELDS = [
    "workload_id",
    "contract",
    "scope",
    "status",
    "row_equal",
    "top5_equal",
    "speedup",
    "fallbacks",
    "n",
    "source_class",
    "evidence_path",
    "evidence_sha256",
    "notes",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        with source.open("rb") as source_handle:
            for block in iter(lambda: source_handle.read(1024 * 1024), b""):
                handle.write(block)
        temporary = Path(handle.name)
    os.replace(temporary, destination)


def atomic_tsv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def normalize_artifact_path(raw: str, artifact_root: Path) -> str:
    if raw in {"", "NA"}:
        return raw
    path = Path(raw)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(artifact_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"artifact path escapes Phase 2 root: {path}") from exc


def percentile_spread(values: list[float]) -> tuple[float, float, float, float]:
    if not values:
        raise ValueError("cannot summarize an empty value list")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0], ordered[0], ordered[0], ordered[0]
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
    return ordered[0], quartiles[0], quartiles[2], ordered[-1]


def numeric(row: dict[str, str], field: str) -> float:
    value = row.get(field, "")
    if value in {"", "NA"}:
        raise ValueError(f"{row.get('pair_id_text', 'pair')}: missing numeric field {field}")
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"invalid numeric field {field}: {value}") from exc
    if result < 0:
        raise ValueError(f"negative numeric field {field}: {value}")
    return result


def optional_int(row: dict[str, str], field: str) -> int:
    value = row.get(field, "")
    if value in {"", "NA"}:
        return 0
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"invalid integer field {field}: {value}") from exc


def summarize_pairs(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_pair_ids: set[str] = set()
    for row in rows:
        pair_id = row.get("pair_id_text", "")
        if not pair_id or pair_id in seen_pair_ids:
            raise ValueError(f"missing or duplicate pair ID: {pair_id!r}")
        seen_pair_ids.add(pair_id)
        if row.get("status") != "clean":
            raise ValueError(f"non-clean pair cannot enter valid summary: {pair_id}")
        if row.get("runtime_epoch") != str(RUNTIME_EPOCH):
            raise ValueError(f"runtime epoch mixing: {pair_id}")
        if row.get("runtime_commit") != RUNTIME_COMMIT:
            raise ValueError(f"runtime commit mixing: {pair_id}")
        grouped[row["workload_id"]].append(row)

    summaries: list[dict[str, object]] = []
    for workload_id in sorted(grouped):
        group = sorted(grouped[workload_id], key=lambda row: int(row["pair_id"]))
        baseline = [numeric(row, "baseline_wall_seconds") for row in group]
        candidate = [numeric(row, "candidate_wall_seconds") for row in group]
        speedup = [numeric(row, "paired_speedup") for row in group]
        for row, baseline_wall, candidate_wall, observed in zip(
            group, baseline, candidate, speedup, strict=True
        ):
            expected = baseline_wall / candidate_wall
            if abs(observed - expected) > max(1e-12, abs(expected) * 1e-12):
                raise ValueError(f"paired speedup arithmetic mismatch: {row['pair_id_text']}")
        baseline_min, baseline_q1, baseline_q3, baseline_max = percentile_spread(baseline)
        candidate_min, candidate_q1, candidate_q3, candidate_max = percentile_spread(candidate)
        speedup_min, speedup_q1, speedup_q3, speedup_max = percentile_spread(speedup)
        top5_clean = int(
            all(
                row.get(field) == "1"
                for row in group
                for field in (
                    "top5_score_equal",
                    "top5_stability_equal",
                    "top5_nt_score_equal",
                )
            )
        )
        full_values = [row.get("full_output_byte_equal", "NA") for row in group]
        full_clean: object = "NA" if set(full_values) == {"NA"} else int(all(v == "1" for v in full_values))
        summaries.append(
            {
                "workload_id": workload_id,
                "claim_id": group[0]["claim_id"],
                "output_contract": group[0]["output_contract"],
                "valid_pairs": len(group),
                "median_baseline_wall_seconds": statistics.median(baseline),
                "baseline_wall_q1_seconds": baseline_q1,
                "baseline_wall_q3_seconds": baseline_q3,
                "baseline_wall_min_seconds": baseline_min,
                "baseline_wall_max_seconds": baseline_max,
                "median_candidate_wall_seconds": statistics.median(candidate),
                "candidate_wall_q1_seconds": candidate_q1,
                "candidate_wall_q3_seconds": candidate_q3,
                "candidate_wall_min_seconds": candidate_min,
                "candidate_wall_max_seconds": candidate_max,
                "median_paired_speedup": statistics.median(speedup),
                "paired_speedup_q1": speedup_q1,
                "paired_speedup_q3": speedup_q3,
                "paired_speedup_min": speedup_min,
                "paired_speedup_max": speedup_max,
                "top5_contract_clean": top5_clean,
                "full_output_contract_clean": full_clean,
                "fallbacks_total": sum(optional_int(row, "fallbacks") for row in group),
                "oom_total": sum(optional_int(row, "oom") for row in group),
                "diagnostic_missing_rows_total": sum(
                    optional_int(row, "missing_rows") for row in group
                ),
                "diagnostic_extra_rows_total": sum(optional_int(row, "extra_rows") for row in group),
                "baseline_gpu_memory_peak_mib": max(
                    numeric(row, "baseline_gpu_memory_peak_mib") for row in group
                ),
                "candidate_gpu_memory_peak_mib": max(
                    numeric(row, "candidate_gpu_memory_peak_mib") for row in group
                ),
                "baseline_rss_peak_kb": max(numeric(row, "baseline_max_rss_kb") for row in group),
                "candidate_rss_peak_kb": max(numeric(row, "candidate_max_rss_kb") for row in group),
            }
        )
    return summaries


def select_operating_envelope(
    rows: list[dict[str, str]], evidence_sha256: str
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for row in rows:
        workload_id = row.get("workload", "")
        if workload_id not in OPERATING_ENVELOPE_IDS:
            continue
        selected.append(
            {
                "workload_id": workload_id,
                "contract": row.get("contract", "NA"),
                "scope": row.get("scope", "NA"),
                "status": row.get("status", "NA"),
                "row_equal": row.get("row_equal", "NA"),
                "top5_equal": row.get("top5_equal", "NA"),
                "speedup": row.get("speedup", "NA"),
                "fallbacks": row.get("fallbacks", "NA"),
                "n": 1,
                "source_class": "committed_historical_artifact",
                "evidence_path": "docs/fasim_gasal2_workload_matrix.tsv",
                "evidence_sha256": evidence_sha256,
                "notes": row.get("notes", ""),
            }
        )
    selected.sort(key=lambda row: str(row["workload_id"]))
    found = {str(row["workload_id"]) for row in selected}
    if found != OPERATING_ENVELOPE_IDS:
        raise ValueError(
            "missing descriptive operating-envelope rows: "
            + ",".join(sorted(OPERATING_ENVELOPE_IDS - found))
        )
    return selected


def render_report(
    summaries: list[dict[str, object]],
    *,
    failure_count: int,
    artifact_root_label: str,
    artifact_manifest_sha256: str,
    failure_reason_counts: dict[str, int] | None = None,
    operating_envelope: list[dict[str, object]] | None = None,
) -> str:
    lines = [
        "# GASAL2-LongTarget Phase 2 core paired benchmarks",
        "",
        "This report is generated from the Phase 2 machine-readable receipt tables; no timing value is copied from historical prose.",
        "",
        "```text",
        f"paper_runtime_epoch = {RUNTIME_EPOCH}",
        f"paper_runtime_commit = {RUNTIME_COMMIT}",
        f"artifact_root = {artifact_root_label}",
        f"artifact_manifest_sha256 = {artifact_manifest_sha256}",
        "bootstrap_interval = deferred_to_phase_5",
        "```",
        "",
        "## Paired results",
        "",
        "| workload | contract | n | baseline median (s) | candidate median (s) | median speedup | speedup IQR | speedup range | correctness | fallback/OOM |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in summaries:
        full = row["full_output_contract_clean"]
        correctness = f"top5={row['top5_contract_clean']}"
        if full != "NA":
            correctness += f"; byte={full}"
        lines.append(
            "| {workload_id} | {output_contract} | {valid_pairs} | "
            "{median_baseline_wall_seconds:.6f} | {median_candidate_wall_seconds:.6f} | "
            "{median_paired_speedup:.6f}x | {paired_speedup_q1:.6f}-{paired_speedup_q3:.6f} | "
            "{paired_speedup_min:.6f}-{paired_speedup_max:.6f} | {correctness} | "
            "{fallbacks_total}/{oom_total} |".format(**row, correctness=correctness)
        )
    lines.extend(
        [
            "",
            "The `fast_topk_score_stability_nt` rows require equality of score-, stability-, and Nt-ranked clustered TFO1-5. Diagnostic row-set drift is not promoted to a full-output requirement. The bounded max8 row additionally requires byte-identical materialized output and zero missing/extra rows.",
            "",
            "## Failure inventory",
            "",
            f"retained failure/mismatch artifacts: {failure_count}",
            "",
            "failure reasons: "
            + "; ".join(
                f"{reason}={count}"
                for reason, count in sorted((failure_reason_counts or {}).items())
            ),
            "",
            "Technical comparator failures and superseded mismatch receipts remain in `core_benchmark_failures_pre_freeze.tsv`. A parser or relocated-path repair creates a new derived comparator receipt; it never edits the failed receipt or raw run artifact.",
            "",
        ]
    )
    if operating_envelope:
        lines.extend(
            [
                "## Descriptive operating envelope",
                "",
                "| workload | contract | n | status | speedup | fallback | source class |",
                "|---|---|---:|---|---:|---:|---|",
            ]
        )
        for row in operating_envelope:
            lines.append(
                "| {workload_id} | {contract} | {n} | {status} | {speedup}x | "
                "{fallbacks} | {source_class} |".format(**row)
            )
        lines.extend(
            [
                "",
                "These are one-run historical descriptive rows from the digest-verified tracked workload matrix. They receive no Phase 2 bootstrap claim and are not pooled with current-epoch pairs.",
                "",
            ]
        )
    lines.extend(
        [
            "## Scope",
            "",
            "The C1 result supersedes the historical single-pair 40.119136x starting value for paper reporting. Historical and Phase 2 samples are not pooled. C4 is limited to one worker per GPU. C7 is the preregistered bounded max8 dual-grid workload; full 121-segment KCNQ1OT1 and full hg38 were not run.",
            "",
            "Machine-readable authority:",
            "",
            "- `paper/source_data/core_benchmark_runs_pre_freeze.tsv`",
            "- `paper/source_data/core_benchmark_pairs_pre_freeze.tsv`",
            "- `paper/source_data/core_benchmark_failures_pre_freeze.tsv`",
            "- `paper/source_data/core_benchmark_summary_pre_freeze.tsv`",
            "- `paper/source_data/core_operating_envelope_pre_freeze.tsv`",
            "- `paper/phase2_artifact_manifest.tsv`",
            "",
        ]
    )
    return "\n".join(lines)


def export_normalized_table(
    source: Path,
    destination: Path,
    artifact_root: Path,
    path_fields: tuple[str, ...],
) -> list[dict[str, str]]:
    fields, rows = read_tsv(source)
    for row in rows:
        for field in path_fields:
            if field in row:
                row[field] = normalize_artifact_path(row[field], artifact_root)
    atomic_tsv(destination, fields, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core",
    )
    parser.add_argument("--paper-dir", type=Path, default=ROOT / "paper")
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()
    paper_dir = args.paper_dir.resolve()
    source_dir = paper_dir / "source_data"
    required = {
        "runs": artifact_root / "phase2-runs.tsv",
        "pairs": artifact_root / "phase2-pairs.tsv",
        "failures": artifact_root / "phase2-failures.tsv",
        "artifacts": artifact_root / "phase2-artifacts.tsv",
    }
    for label, path in required.items():
        if not path.is_file():
            raise SystemExit(f"missing Phase 2 {label} table: {path}")

    export_normalized_table(
        required["runs"],
        source_dir / "core_benchmark_runs_pre_freeze.tsv",
        artifact_root,
        ("receipt_path",),
    )
    pairs = export_normalized_table(
        required["pairs"],
        source_dir / "core_benchmark_pairs_pre_freeze.tsv",
        artifact_root,
        ("pair_summary_path",),
    )
    failures = export_normalized_table(
        required["failures"],
        source_dir / "core_benchmark_failures_pre_freeze.tsv",
        artifact_root,
        ("artifact_path",),
    )
    summaries = summarize_pairs(pairs)
    atomic_tsv(source_dir / "core_benchmark_summary_pre_freeze.tsv", SUMMARY_FIELDS, summaries)
    _, artifact_rows = read_tsv(required["artifacts"])
    atomic_copy(required["artifacts"], paper_dir / "phase2_artifact_manifest.tsv")
    manifest_digest = sha256(paper_dir / "phase2_artifact_manifest.tsv")
    workload_matrix = ROOT / "docs/fasim_gasal2_workload_matrix.tsv"
    _, workload_rows = read_tsv(workload_matrix)
    operating_envelope = select_operating_envelope(workload_rows, sha256(workload_matrix))
    atomic_tsv(
        source_dir / "core_operating_envelope_pre_freeze.tsv",
        OPERATING_FIELDS,
        operating_envelope,
    )
    try:
        artifact_root_label = artifact_root.relative_to(ROOT).as_posix()
    except ValueError:
        artifact_root_label = str(artifact_root)
    report = render_report(
        summaries,
        failure_count=len(failures),
        artifact_root_label=artifact_root_label,
        artifact_manifest_sha256=manifest_digest,
        failure_reason_counts=dict(Counter(row["reason"] for row in failures)),
        operating_envelope=operating_envelope,
    )
    atomic_text(paper_dir / "core_benchmark_report.md", report)
    print(f"phase2_workloads={len(summaries)}")
    print(f"phase2_pairs={len(pairs)}")
    print(f"phase2_failures={len(failures)}")
    print(f"phase2_artifact_manifest_sha256={manifest_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
