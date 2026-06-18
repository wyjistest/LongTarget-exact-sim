#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


PREFIX_SHADOW = "benchmark.fasim_gasal2_top5_traceback_certificate_shadow_"
PREFIX_BENCH = "benchmark."

FIELDS = [
    "workload_name",
    "status",
    "decision",
    "target",
    "query",
    "mode",
    "workers",
    "group_target_records",
    "output_contract",
    "baseline_traceback_requests",
    "certificate_traceback_requests",
    "tracebacks_skipped",
    "tracebacks_skipped_fraction",
    "score_certificate_supported",
    "stability_certificate_supported",
    "nt_score_certificate_supported",
    "score_rank5_boundary",
    "stability_rank5_boundary",
    "nt_score_rank5_boundary",
    "score_boundary_ties",
    "stability_boundary_ties",
    "nt_score_boundary_ties",
    "score_groups_processed",
    "stability_groups_processed",
    "nt_score_groups_processed",
    "boundary_updates",
    "invalid_after_traceback",
    "filtered_nt_after_traceback",
    "dedup_removed_after_traceback",
    "certificate_pack_seconds",
    "certificate_traceback_seconds",
    "certificate_convert_seconds",
    "certificate_total_seconds",
    "false_prune",
    "missing_top5_rows",
    "extra_top5_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_score_rows_order_equal",
    "top5_stability_rows_order_equal",
    "top5_nt_score_rows_order_equal",
    "measured_net_saved_seconds",
    "wall_speedup_vs_authority",
    "full_lite_claim",
    "full_tfosorted_claim",
    "artifact_provenance",
    "notes",
]

INT_KEYS = [
    "requested",
    "active",
    "baseline_traceback_requests",
    "certificate_traceback_requests",
    "tracebacks_skipped",
    "score_certificate_supported",
    "stability_certificate_supported",
    "nt_score_certificate_supported",
    "score_boundary_ties",
    "stability_boundary_ties",
    "nt_score_boundary_ties",
    "score_groups_processed",
    "stability_groups_processed",
    "nt_score_groups_processed",
    "boundary_updates",
    "invalid_after_traceback",
    "filtered_nt_after_traceback",
    "dedup_removed_after_traceback",
    "false_prune",
    "missing_top5_rows",
    "extra_top5_rows",
]

FLOAT_KEYS = [
    "tracebacks_skipped_fraction",
    "certificate_pack_seconds",
    "certificate_traceback_seconds",
    "certificate_convert_seconds",
    "certificate_total_seconds",
    "measured_net_saved_seconds",
]

TEXT_KEYS = [
    "decision",
    "score_rank5_boundary",
    "stability_rank5_boundary",
    "nt_score_rank5_boundary",
]


def _read_key_values(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _parse_stderr(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith(PREFIX_SHADOW):
            values["shadow." + key[len(PREFIX_SHADOW) :]] = value
        elif key.startswith(PREFIX_BENCH):
            values["benchmark." + key[len(PREFIX_BENCH) :]] = value
    return values


def _bool_text(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes"}:
        return "true"
    if lowered in {"0", "false", "no"}:
        return "false"
    return "unknown"


def _summary_bool(summary: dict[str, str], key: str) -> str:
    return _bool_text(summary.get(key, "unknown"))


def _int_text(values: dict[str, str], key: str) -> str:
    value = values.get("shadow." + key)
    if value is None:
        return "unknown"
    try:
        return str(int(float(value)))
    except ValueError:
        return "unknown"


def _float_text(values: dict[str, str], key: str) -> str:
    value = values.get("shadow." + key)
    if value is None:
        return "unknown"
    try:
        return f"{float(value):.6f}"
    except ValueError:
        return "unknown"


def _ratio(num_text: str, den_text: str) -> str:
    try:
        num = int(num_text)
        den = int(den_text)
    except ValueError:
        return "unknown"
    if den <= 0:
        return "unknown"
    return f"{num / den:.6f}"


def _speedup(total_text: str, saved_text: str) -> str:
    try:
        total = float(total_text)
        saved = float(saved_text)
    except ValueError:
        return "unknown"
    denominator = total - saved
    if total <= 0.0 or denominator <= 0.0:
        return "unknown"
    return f"{total / denominator:.6f}"


def _unknown_row(args: argparse.Namespace, decision: str, notes: str) -> dict[str, str]:
    row = {field: "unknown" for field in FIELDS}
    row.update(
        {
            "workload_name": args.workload_name,
            "status": args.status,
            "decision": decision,
            "target": args.target,
            "query": args.query,
            "mode": args.mode,
            "workers": args.workers,
            "group_target_records": args.group_target_records,
            "output_contract": args.output_contract,
            "full_lite_claim": "not_claimed",
            "full_tfosorted_claim": "not_claimed",
            "artifact_provenance": args.artifact_provenance,
            "notes": notes,
        }
    )
    return row


def _derive_decision(row: dict[str, str], parsed_decision: str) -> str:
    if parsed_decision and parsed_decision != "unknown":
        return parsed_decision
    if row["status"] != "complete":
        return "no_decision"
    clean = [
        row["top5_score_rows_order_equal"] == "true",
        row["top5_stability_rows_order_equal"] == "true",
        row["top5_nt_score_rows_order_equal"] == "true",
        row["false_prune"] == "0",
        row["missing_top5_rows"] == "0",
        row["extra_top5_rows"] == "0",
    ]
    if not all(clean):
        return "no_go_top5_mismatch"
    supported = [
        row["score_certificate_supported"] == "true",
        row["stability_certificate_supported"] == "true",
        row["nt_score_certificate_supported"] == "true",
    ]
    if not all(supported):
        return "no_go_unsupported_modes"
    try:
        speedup = float(row["wall_speedup_vs_authority"])
    except ValueError:
        speedup = 1.0
    if speedup >= 1.10:
        return "strong_go_top5_shadow"
    if speedup > 1.0:
        return "weak_go_more_characterization_needed"
    return "no_go_measured_saving_immaterial"


def build_row(args: argparse.Namespace) -> dict[str, str]:
    if args.status != "complete":
        return _unknown_row(args, "no_decision", args.notes)

    stderr_values = _parse_stderr(args.stderr)
    top5 = _read_key_values(args.top5_summary)
    if "shadow.requested" not in stderr_values:
        return _unknown_row(args, "no_decision", "missing top5 certificate shadow counters")

    row = {field: "unknown" for field in FIELDS}
    row.update(
        {
            "workload_name": args.workload_name,
            "status": args.status,
            "target": args.target,
            "query": args.query,
            "mode": args.mode,
            "workers": args.workers,
            "group_target_records": args.group_target_records,
            "output_contract": args.output_contract,
            "full_lite_claim": "not_claimed",
            "full_tfosorted_claim": "not_claimed",
            "artifact_provenance": args.artifact_provenance,
            "notes": args.notes or "none",
        }
    )
    for key in INT_KEYS:
        if key in {"requested", "active"}:
            continue
        if key.endswith("_certificate_supported"):
            row[key] = _bool_text(stderr_values.get("shadow." + key, "unknown"))
        else:
            row[key] = _int_text(stderr_values, key)
    for key in FLOAT_KEYS:
        row[key] = _float_text(stderr_values, key)
    for key in TEXT_KEYS:
        row[key] = stderr_values.get("shadow." + key, "unknown")

    if row["tracebacks_skipped_fraction"] == "unknown":
        row["tracebacks_skipped_fraction"] = _ratio(
            row["tracebacks_skipped"],
            row["baseline_traceback_requests"],
        )

    row["top5_score_equal"] = _summary_bool(top5, "top5_score_equal")
    row["top5_stability_equal"] = _summary_bool(top5, "top5_stability_equal")
    row["top5_nt_score_equal"] = _summary_bool(top5, "top5_nt_score_equal")
    row["top5_score_rows_order_equal"] = _summary_bool(
        top5,
        "top5_score_rows_order_equal",
    )
    row["top5_stability_rows_order_equal"] = _summary_bool(
        top5,
        "top5_stability_rows_order_equal",
    )
    row["top5_nt_score_rows_order_equal"] = _summary_bool(
        top5,
        "top5_nt_score_rows_order_equal",
    )
    row["wall_speedup_vs_authority"] = _speedup(
        stderr_values.get("benchmark.total_wall_seconds", "unknown"),
        row["measured_net_saved_seconds"],
    )
    row["decision"] = _derive_decision(
        row,
        stderr_values.get("shadow.decision", "unknown"),
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload-name", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--stderr", type=Path)
    parser.add_argument("--top5-summary", type=Path)
    parser.add_argument("--target", default="unknown")
    parser.add_argument("--query", default="unknown")
    parser.add_argument("--mode", default="unknown")
    parser.add_argument("--workers", default="unknown")
    parser.add_argument("--group-target-records", default="unknown")
    parser.add_argument("--output-contract", default="unknown")
    parser.add_argument("--artifact-provenance", default="unknown")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    row = build_row(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
