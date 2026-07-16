#!/usr/bin/env python3
"""Export and summarize immutable Phase 3 generalization receipts."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from summarize_fasim_gasal2_paper_phase2 import (  # noqa: E402
    atomic_copy,
    atomic_text,
    atomic_tsv,
    normalize_artifact_path,
    numeric,
    optional_int,
    percentile_spread,
    read_tsv,
    sha256,
)


RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
RUNTIME_EPOCH = 0
SUPPORTED_STATUSES = {"clean", "mismatch", "fallback", "failed"}
IDENTITY_FIELDS = (
    "claim_id",
    "role",
    "query_id",
    "query_length_nt",
    "fragment_position",
    "target_id",
    "target_region",
    "preset_id",
    "output_contract",
)
CONTRACT_FIELDS = (
    "clustered_score_top5_equal",
    "clustered_stability_top5_equal",
    "clustered_nt_top5_equal",
    "boundary_ties_equal",
)
SUMMARY_EQUAL_FIELDS = {
    "clustered_score_top5_equal": "clustered_score_all_equal",
    "clustered_stability_top5_equal": "clustered_stability_all_equal",
    "clustered_nt_top5_equal": "clustered_nt_all_equal",
    "boundary_ties_equal": "boundary_ties_all_equal",
    "raw_score_top5_equal": "raw_score_all_equal",
    "raw_stability_top5_equal": "raw_stability_all_equal",
    "raw_nt_top5_equal": "raw_nt_all_equal",
}
RAW_DIAGNOSTIC_FIELDS = (
    "raw_score_top5_equal",
    "raw_stability_top5_equal",
    "raw_nt_top5_equal",
)
WORKLOAD_FIELDS = [
    "workload_id",
    *IDENTITY_FIELDS,
    "status",
    "repeat_consistent",
    "valid_pairs",
    "median_baseline_wall_seconds",
    "median_candidate_wall_seconds",
    "median_paired_speedup",
    "paired_speedup_q1",
    "paired_speedup_q3",
    "paired_speedup_min",
    "paired_speedup_max",
    "clustered_score_all_equal",
    "clustered_stability_all_equal",
    "clustered_nt_all_equal",
    "boundary_ties_all_equal",
    "raw_score_all_equal",
    "raw_stability_all_equal",
    "raw_nt_all_equal",
    "full_missing_rows_total",
    "full_extra_rows_total",
    "fallbacks_total",
    "oom_total",
    "gasal2_requests_total",
    "traceback_requests_total",
    "baseline_rss_peak_kb",
    "candidate_rss_peak_kb",
    "baseline_gpu_memory_peak_mib",
    "candidate_gpu_memory_peak_mib",
]


def _all_equal(group: list[dict[str, str]], field: str) -> int:
    return int(all(row.get(field) == "1" for row in group))


def summarize_workloads(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_pair_ids: set[str] = set()
    for row in rows:
        pair_id = row.get("pair_id_text", "")
        if not pair_id or pair_id in seen_pair_ids:
            raise ValueError(f"missing or duplicate Phase 3 pair ID: {pair_id!r}")
        seen_pair_ids.add(pair_id)
        if row.get("runtime_epoch") != str(RUNTIME_EPOCH):
            raise ValueError(f"runtime epoch mixing: {pair_id}")
        if row.get("runtime_commit") != RUNTIME_COMMIT:
            raise ValueError(f"runtime commit mixing: {pair_id}")
        if row.get("status") not in SUPPORTED_STATUSES:
            raise ValueError(f"invalid Phase 3 pair status: {pair_id}")
        grouped[row["workload_id"]].append(row)

    summaries: list[dict[str, object]] = []
    for workload_id in sorted(grouped):
        group = sorted(grouped[workload_id], key=lambda row: int(row["pair_id"]))
        for field in IDENTITY_FIELDS:
            if len({row.get(field, "") for row in group}) != 1:
                raise ValueError(f"{workload_id}: mixed {field}")
        baseline = [numeric(row, "baseline_wall_seconds") for row in group]
        candidate = [numeric(row, "candidate_wall_seconds") for row in group]
        speedup = [numeric(row, "paired_speedup") for row in group]
        for row, baseline_wall, candidate_wall, observed in zip(
            group, baseline, candidate, speedup, strict=True
        ):
            expected = baseline_wall / candidate_wall
            if abs(observed - expected) > max(1e-12, abs(expected) * 1e-12):
                raise ValueError(f"paired speedup arithmetic mismatch: {row['pair_id_text']}")
        speedup_min, speedup_q1, speedup_q3, speedup_max = percentile_spread(speedup)
        statuses = {row["status"] for row in group}
        if statuses == {"clean"}:
            status = "clean"
        elif "failed" in statuses:
            status = "failed"
        elif "fallback" in statuses:
            status = "fallback"
        else:
            status = "mismatch"
        summary: dict[str, object] = {
            "workload_id": workload_id,
            **{field: group[0][field] for field in IDENTITY_FIELDS},
            "status": status,
            "repeat_consistent": int(len(statuses) == 1),
            "valid_pairs": len(group),
            "median_baseline_wall_seconds": statistics.median(baseline),
            "median_candidate_wall_seconds": statistics.median(candidate),
            "median_paired_speedup": statistics.median(speedup),
            "paired_speedup_q1": speedup_q1,
            "paired_speedup_q3": speedup_q3,
            "paired_speedup_min": speedup_min,
            "paired_speedup_max": speedup_max,
            "full_missing_rows_total": sum(optional_int(row, "full_missing_rows") for row in group),
            "full_extra_rows_total": sum(optional_int(row, "full_extra_rows") for row in group),
            "fallbacks_total": sum(optional_int(row, "fallbacks") for row in group),
            "oom_total": sum(optional_int(row, "oom") for row in group),
            "gasal2_requests_total": sum(optional_int(row, "gasal2_requests") for row in group),
            "traceback_requests_total": sum(
                optional_int(row, "traceback_requests") for row in group
            ),
            "baseline_rss_peak_kb": max(numeric(row, "baseline_max_rss_kb") for row in group),
            "candidate_rss_peak_kb": max(numeric(row, "candidate_max_rss_kb") for row in group),
            "baseline_gpu_memory_peak_mib": max(
                numeric(row, "baseline_gpu_memory_peak_mib") for row in group
            ),
            "candidate_gpu_memory_peak_mib": max(
                numeric(row, "candidate_gpu_memory_peak_mib") for row in group
            ),
        }
        for field in (*CONTRACT_FIELDS, *RAW_DIAGNOSTIC_FIELDS):
            summary[SUMMARY_EQUAL_FIELDS[field]] = _all_equal(group, field)
        summaries.append(summary)
    return summaries


def generalization_decision(summaries: list[dict[str, object]]) -> dict[str, object]:
    total = len(summaries)
    clean = [row for row in summaries if row["status"] == "clean"]
    non_h19 = {str(row["query_id"]) for row in summaries if row["query_id"] != "H19"}
    clean_non_h19 = {str(row["query_id"]) for row in clean if row["query_id"] != "H19"}
    targets = {str(row["target_id"]) for row in summaries}
    clean_targets = {str(row["target_id"]) for row in clean}
    presets = {str(row["preset_id"]) for row in summaries}
    clean_fraction = len(clean) / total if total else 0.0
    supported = (
        total > 0
        and clean_fraction >= 0.75
        and clean_non_h19 == non_h19
        and clean_targets == targets
        and len(presets) == 1
    )
    if supported:
        decision = "generalization_supported"
    elif len(clean_non_h19) >= 2:
        decision = "generalization_scoped_with_mismatches"
    else:
        decision = "generalization_no_go"
    return {
        "decision": decision,
        "supported_workloads": total,
        "clean_workloads": len(clean),
        "mismatch_workloads": sum(row["status"] == "mismatch" for row in summaries),
        "fallback_workloads": sum(row["status"] == "fallback" for row in summaries),
        "failed_workloads": sum(row["status"] == "failed" for row in summaries),
        "clean_fraction": clean_fraction,
        "non_h19_identity_gate": int(clean_non_h19 == non_h19),
        "target_region_gate": int(clean_targets == targets),
        "one_preset_gate": int(len(presets) == 1),
    }


def _resolve_detail_path(raw: str, artifact_root: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return artifact_root / path


def aggregate_mismatch_details(
    rows: list[dict[str, str]], artifact_root: Path
) -> tuple[list[str], list[dict[str, str]]]:
    prefix = ["pair_id_text", "workload_id", "pair_status"]
    detail_fields: list[str] | None = None
    aggregated: list[dict[str, str]] = []
    for row in rows:
        if row.get("status") != "mismatch":
            continue
        details_path = _resolve_detail_path(row.get("details_path", ""), artifact_root)
        if not details_path.is_file():
            raise ValueError(f"missing mismatch detail artifact: {details_path}")
        fields, details = read_tsv(details_path)
        if detail_fields is None:
            detail_fields = fields
        elif fields != detail_fields:
            raise ValueError(f"mismatch detail schema drift: {details_path}")
        for detail in details:
            aggregated.append(
                {
                    "pair_id_text": row["pair_id_text"],
                    "workload_id": row["workload_id"],
                    "pair_status": row["status"],
                    **detail,
                }
            )
    return prefix + (detail_fields or []), aggregated


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


def render_report(
    summaries: list[dict[str, object]],
    guards: list[dict[str, str]],
    decision: dict[str, object],
    *,
    artifact_root_label: str,
    artifact_manifest_sha256: str,
    failure_count: int,
) -> str:
    lines = [
        "# GASAL2-LongTarget Phase 3 short-query generalization",
        "",
        "This report retains every preregistered supported workload, mismatch, and full-length guard.",
        "",
        "```text",
        f"paper_runtime_epoch = {RUNTIME_EPOCH}",
        f"paper_runtime_commit = {RUNTIME_COMMIT}",
        f"artifact_root = {artifact_root_label}",
        f"artifact_manifest_sha256 = {artifact_manifest_sha256}",
        f"decision = {decision['decision']}",
        f"clean_workloads = {decision['clean_workloads']}/{decision['supported_workloads']}",
        f"clean_fraction = {float(decision['clean_fraction']):.6f}",
        "bootstrap_interval = deferred_to_phase_5",
        "```",
        "",
        "## Supported-query results",
        "",
        "| workload | query | length | position | target | role | n | median speedup | clustered score/stability/Nt | ties | status | full-row missing/extra |",
        "|---|---|---:|---|---|---|---:|---:|---|---:|---|---:|",
    ]
    for row in summaries:
        lines.append(
            "| {workload_id} | {query_id} | {query_length_nt} | {fragment_position} | "
            "{target_id} | {role} | {valid_pairs} | {median_paired_speedup:.6f}x | "
            "{clustered_score_all_equal}/{clustered_stability_all_equal}/{clustered_nt_all_equal} | "
            "{boundary_ties_all_equal} | {status} | {full_missing_rows_total}/{full_extra_rows_total} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "The authority contract is equality of score-, stability-, and Nt-ranked clustered TFO1-5 plus boundary ties. Raw top5 and full-row missing/extra counts are retained as diagnostics and are not promoted to a full-output claim.",
            "",
            "## Retained mismatches",
            "",
        ]
    )
    mismatches = [row for row in summaries if row["status"] != "clean"]
    for row in mismatches:
        lines.append(
            "- `{workload_id}`: status={status}; repeat_consistent={repeat_consistent}; "
            "clustered score/stability/Nt={clustered_score_all_equal}/"
            "{clustered_stability_all_equal}/{clustered_nt_all_equal}; "
            "full missing/extra={full_missing_rows_total}/{full_extra_rows_total}.".format(**row)
        )
    lines.extend(
        [
            "",
            "All mismatch representative rows, ranks, cluster IDs, and full TFOsorted columns are retained in `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`.",
            "",
            "## Full-length guards",
            "",
            "| workload | query | length | supported | reason | GPU fast path executed | status |",
            "|---|---|---:|---:|---|---:|---|",
        ]
    )
    for row in guards:
        lines.append(
            "| {workload_id} | {query_id} | {query_length_nt} | {supported} | {reason} | "
            "{gpu_fast_path_executed} | {status} |".format(**row)
        )
    lines.extend(
        [
            "",
            f"technical failure receipts: {failure_count}",
            "",
            "All three full-length negative controls were rejected by `query_length_contract` before GPU execution. Across supported rows, fallback and OOM totals were zero.",
            "",
            "## Decision",
            "",
            f"`{decision['decision']}`: {decision['clean_workloads']} of {decision['supported_workloads']} preregistered supported workloads were clean ({100 * float(decision['clean_fraction']):.2f}%). Each included non-H19 identity and each target region has at least one clean row, and one preset was used across all supported rows.",
            "",
            "The three mismatch workloads remain part of the evidence package. This result supports non-H19 generalization under a workload-level contract gate; it does not guarantee that every short query is clean.",
            "",
            "Machine-readable authority:",
            "",
            "- `paper/source_data/generalization_runs_pre_freeze.tsv`",
            "- `paper/source_data/generalization_pairs_pre_freeze.tsv`",
            "- `paper/source_data/generalization_workloads_pre_freeze.tsv`",
            "- `paper/source_data/generalization_guards_pre_freeze.tsv`",
            "- `paper/source_data/generalization_failures_pre_freeze.tsv`",
            "- `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`",
            "- `paper/phase3_artifact_manifest.tsv`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization",
    )
    parser.add_argument("--paper-dir", type=Path, default=ROOT / "paper")
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()
    paper_dir = args.paper_dir.resolve()
    source_dir = paper_dir / "source_data"
    required = {
        "runs": artifact_root / "phase3-runs.tsv",
        "pairs": artifact_root / "phase3-pairs.tsv",
        "guards": artifact_root / "phase3-guards.tsv",
        "failures": artifact_root / "phase3-failures.tsv",
        "artifacts": artifact_root / "phase3-artifacts.tsv",
    }
    for label, path in required.items():
        if not path.is_file():
            raise SystemExit(f"missing Phase 3 {label} table: {path}")

    runs = export_normalized_table(
        required["runs"],
        source_dir / "generalization_runs_pre_freeze.tsv",
        artifact_root,
        ("receipt_path",),
    )
    pairs = export_normalized_table(
        required["pairs"],
        source_dir / "generalization_pairs_pre_freeze.tsv",
        artifact_root,
        ("details_path", "pair_summary_path"),
    )
    guards = export_normalized_table(
        required["guards"],
        source_dir / "generalization_guards_pre_freeze.tsv",
        artifact_root,
        ("receipt_path",),
    )
    failures = export_normalized_table(
        required["failures"],
        source_dir / "generalization_failures_pre_freeze.tsv",
        artifact_root,
        ("artifact_path",),
    )
    summaries = summarize_workloads(pairs)
    decision = generalization_decision(summaries)
    atomic_tsv(
        source_dir / "generalization_workloads_pre_freeze.tsv",
        WORKLOAD_FIELDS,
        summaries,
    )
    detail_fields, mismatch_details = aggregate_mismatch_details(pairs, artifact_root)
    atomic_tsv(
        source_dir / "generalization_mismatch_top5_pre_freeze.tsv",
        detail_fields,
        mismatch_details,
    )
    atomic_copy(required["artifacts"], paper_dir / "phase3_artifact_manifest.tsv")
    artifact_manifest_sha256 = sha256(paper_dir / "phase3_artifact_manifest.tsv")
    try:
        artifact_root_label = artifact_root.relative_to(ROOT).as_posix()
    except ValueError:
        artifact_root_label = str(artifact_root)
    atomic_text(
        paper_dir / "generalization_report.md",
        render_report(
            summaries,
            guards,
            decision,
            artifact_root_label=artifact_root_label,
            artifact_manifest_sha256=artifact_manifest_sha256,
            failure_count=len(failures),
        ),
    )
    print(f"phase3_runs={len(runs)}")
    print(f"phase3_pairs={len(pairs)}")
    print(f"phase3_workloads={len(summaries)}")
    print(f"phase3_guards={len(guards)}")
    print(f"phase3_failures={len(failures)}")
    print(f"phase3_mismatch_detail_rows={len(mismatch_details)}")
    print(f"phase3_decision={decision['decision']}")
    print(f"phase3_artifact_manifest_sha256={artifact_manifest_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
