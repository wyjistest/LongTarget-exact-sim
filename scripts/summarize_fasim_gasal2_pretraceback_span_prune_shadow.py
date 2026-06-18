#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


PREFIX_SHADOW = "benchmark.fasim_gasal2_pretraceback_span_prune_shadow_"
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
    "output_mode",
    "gasal2_runtime_env",
    "shadow_requested",
    "shadow_active",
    "shadow_batches",
    "input_attempts",
    "authority_selected_attempts",
    "kept_selected_attempts",
    "skipped_selected_attempts",
    "skipped_fraction_of_selected",
    "shadow_score_requests",
    "shadow_score_batches",
    "shadow_traceback_requests",
    "shadow_traceback_batches",
    "shadow_traceback_fill_seconds",
    "shadow_traceback_submit_seconds",
    "shadow_traceback_wait_seconds",
    "shadow_traceback_result_copy_seconds",
    "shadow_traceback_cigar_vector_seconds",
    "shadow_traceback_cigar_string_seconds",
    "shadow_traceback_seconds",
    "shadow_total_seconds",
    "authority_skipped_seen",
    "authority_skipped_invalid_span",
    "false_prune",
    "missing_rows",
    "extra_rows",
    "fallbacks",
    "baseline_lite_rows",
    "candidate_lite_rows",
    "full_lite_missing_rows",
    "full_lite_extra_rows",
    "baseline_tfosorted_rows",
    "candidate_tfosorted_rows",
    "full_tfosorted_missing_rows",
    "full_tfosorted_extra_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "artifact_provenance",
    "notes",
]

INT_KEYS = [
    "requested",
    "active",
    "batches",
    "input_attempts",
    "authority_selected_attempts",
    "kept_selected_attempts",
    "skipped_selected_attempts",
    "score_requests",
    "score_batches",
    "traceback_requests",
    "traceback_batches",
    "authority_skipped_seen",
    "authority_skipped_invalid_span",
    "false_prune",
    "missing_rows",
    "extra_rows",
    "fallbacks",
]

FLOAT_KEYS = [
    "skipped_fraction_of_selected",
    "traceback_fill_seconds",
    "traceback_submit_seconds",
    "traceback_wait_seconds",
    "traceback_result_copy_seconds",
    "traceback_cigar_vector_seconds",
    "traceback_cigar_string_seconds",
    "traceback_seconds",
    "total_seconds",
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


def _unknown_row(args: argparse.Namespace, status: str, decision: str, notes: str) -> dict[str, str]:
    row = {field: "unknown" for field in FIELDS}
    row.update(
        {
            "workload_name": args.workload_name,
            "status": status,
            "decision": decision,
            "target": args.target,
            "query": args.query,
            "mode": args.mode,
            "workers": args.workers,
            "group_target_records": args.group_target_records,
            "output_mode": args.output_mode,
            "gasal2_runtime_env": args.gasal2_runtime_env,
            "artifact_provenance": args.artifact_provenance,
            "notes": notes,
        }
    )
    return row


def _as_int(values: dict[str, str], key: str) -> int:
    if key not in values:
        raise ValueError(f"missing required metric: {key}")
    try:
        return int(float(values[key]))
    except ValueError as exc:
        raise ValueError(f"invalid integer metric {key}: {values[key]}") from exc


def _float_text(values: dict[str, str], key: str) -> str:
    if key not in values:
        return "unknown"
    try:
        return f"{float(values[key]):.6f}"
    except ValueError:
        return "unknown"


def _ratio(num: int, den: int) -> str:
    if den <= 0:
        return "unknown"
    return f"{num / den:.6f}"


def _first_value(values: dict[str, str], keys: list[str], default: str = "unknown") -> str:
    for key in keys:
        if key in values and values[key] != "":
            return values[key]
    return default


def _bool_from_summary(values: dict[str, str], key: str) -> str:
    value = values.get(key, "").strip().lower()
    if value in {"true", "1", "yes"}:
        return "true"
    if value in {"false", "0", "no"}:
        return "false"
    return "unknown"


def _combine_notes(*parts: str) -> str:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    return "; ".join(cleaned) if cleaned else "none"


def _derive_decision(row: dict[str, str]) -> str:
    if row["status"] != "complete":
        return "no_decision"
    if row["shadow_requested"] != "1":
        return "no_decision"
    clean = [
        row["shadow_active"] == "1",
        row["false_prune"] == "0",
        row["missing_rows"] == "0",
        row["extra_rows"] == "0",
        row["fallbacks"] == "0",
        row["full_lite_missing_rows"] in {"0", "unknown"},
        row["full_lite_extra_rows"] in {"0", "unknown"},
        row["full_tfosorted_missing_rows"] in {"0", "unknown"},
        row["full_tfosorted_extra_rows"] in {"0", "unknown"},
        row["top5_score_equal"] in {"true", "unknown"},
        row["top5_stability_equal"] in {"true", "unknown"},
        row["top5_nt_score_equal"] in {"true", "unknown"},
    ]
    if not all(clean):
        return "no_go_shadow_not_clean"
    try:
        skipped = int(row["skipped_selected_attempts"])
    except ValueError:
        skipped = 0
    if skipped <= 0:
        return "no_go_no_span_candidates"
    return "shadow_clean_more_characterization_needed"


def build_row(args: argparse.Namespace) -> dict[str, str]:
    if args.status != "complete":
        return _unknown_row(args, args.status, "no_decision", args.notes)

    stderr_values = _parse_stderr(args.stderr)
    top5 = _read_key_values(args.top5_summary)
    lite = _read_key_values(args.full_lite_summary)
    tfosorted = _read_key_values(args.tfosorted_summary)
    try:
        metrics = {key: _as_int(stderr_values, "shadow." + key) for key in INT_KEYS}
    except ValueError as exc:
        return _unknown_row(args, "incomplete", "no_decision", _combine_notes(args.notes, str(exc)))

    float_metrics = {key: _float_text(stderr_values, "shadow." + key) for key in FLOAT_KEYS}
    skipped_fraction = float_metrics["skipped_fraction_of_selected"]
    if skipped_fraction == "unknown":
        skipped_fraction = _ratio(
            metrics["skipped_selected_attempts"],
            metrics["authority_selected_attempts"],
        )

    row = {field: "unknown" for field in FIELDS}
    row.update(
        {
            "workload_name": args.workload_name,
            "status": "complete",
            "decision": _first_value(stderr_values, ["shadow.decision"], "unknown"),
            "target": args.target,
            "query": args.query,
            "mode": args.mode,
            "workers": args.workers,
            "group_target_records": args.group_target_records,
            "output_mode": args.output_mode,
            "gasal2_runtime_env": args.gasal2_runtime_env,
            "shadow_requested": str(metrics["requested"]),
            "shadow_active": str(metrics["active"]),
            "shadow_batches": str(metrics["batches"]),
            "input_attempts": str(metrics["input_attempts"]),
            "authority_selected_attempts": str(metrics["authority_selected_attempts"]),
            "kept_selected_attempts": str(metrics["kept_selected_attempts"]),
            "skipped_selected_attempts": str(metrics["skipped_selected_attempts"]),
            "skipped_fraction_of_selected": skipped_fraction,
            "shadow_score_requests": str(metrics["score_requests"]),
            "shadow_score_batches": str(metrics["score_batches"]),
            "shadow_traceback_requests": str(metrics["traceback_requests"]),
            "shadow_traceback_batches": str(metrics["traceback_batches"]),
            "shadow_traceback_fill_seconds": float_metrics["traceback_fill_seconds"],
            "shadow_traceback_submit_seconds": float_metrics["traceback_submit_seconds"],
            "shadow_traceback_wait_seconds": float_metrics["traceback_wait_seconds"],
            "shadow_traceback_result_copy_seconds": float_metrics["traceback_result_copy_seconds"],
            "shadow_traceback_cigar_vector_seconds": float_metrics["traceback_cigar_vector_seconds"],
            "shadow_traceback_cigar_string_seconds": float_metrics["traceback_cigar_string_seconds"],
            "shadow_traceback_seconds": float_metrics["traceback_seconds"],
            "shadow_total_seconds": float_metrics["total_seconds"],
            "authority_skipped_seen": str(metrics["authority_skipped_seen"]),
            "authority_skipped_invalid_span": str(metrics["authority_skipped_invalid_span"]),
            "false_prune": str(metrics["false_prune"]),
            "missing_rows": str(metrics["missing_rows"]),
            "extra_rows": str(metrics["extra_rows"]),
            "fallbacks": str(metrics["fallbacks"]),
            "baseline_lite_rows": _first_value(lite, ["baseline_rows", "baseline_lite_rows"]),
            "candidate_lite_rows": _first_value(lite, ["candidate_rows", "candidate_lite_rows"]),
            "full_lite_missing_rows": _first_value(lite, ["missing_rows", "full_lite_missing_rows"], "unknown"),
            "full_lite_extra_rows": _first_value(lite, ["extra_rows", "full_lite_extra_rows"], "unknown"),
            "baseline_tfosorted_rows": _first_value(tfosorted, ["baseline_rows", "baseline_tfosorted_rows"], _first_value(lite, ["baseline_rows", "baseline_lite_rows"])),
            "candidate_tfosorted_rows": _first_value(tfosorted, ["candidate_rows", "candidate_tfosorted_rows"], _first_value(lite, ["candidate_rows", "candidate_lite_rows"])),
            "full_tfosorted_missing_rows": _first_value(tfosorted, ["missing_rows", "full_tfosorted_missing_rows"], "unknown"),
            "full_tfosorted_extra_rows": _first_value(tfosorted, ["extra_rows", "full_tfosorted_extra_rows"], "unknown"),
            "top5_score_equal": _bool_from_summary(top5, "top5_score_equal"),
            "top5_stability_equal": _bool_from_summary(top5, "top5_stability_equal"),
            "top5_nt_score_equal": _bool_from_summary(top5, "top5_nt_score_equal"),
            "artifact_provenance": args.artifact_provenance,
            "notes": _combine_notes(args.notes),
        }
    )
    if row["decision"] == "unknown":
        row["decision"] = _derive_decision(row)
    return row


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "unknown") for field in FIELDS})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 pre-traceback span-prune shadow counters."
    )
    parser.add_argument("--workload-name", required=True)
    parser.add_argument("--status", default="complete", choices=["complete", "missing", "incomplete"])
    parser.add_argument("--stderr", type=Path)
    parser.add_argument("--top5-summary", type=Path)
    parser.add_argument("--full-lite-summary", type=Path)
    parser.add_argument("--tfosorted-summary", type=Path)
    parser.add_argument("--target", default="unknown")
    parser.add_argument("--query", default="unknown")
    parser.add_argument("--mode", default="unknown")
    parser.add_argument("--workers", default="unknown")
    parser.add_argument("--group-target-records", default="unknown")
    parser.add_argument("--output-mode", default="unknown")
    parser.add_argument("--gasal2-runtime-env", default="unknown")
    parser.add_argument("--artifact-provenance", default="unknown")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_rows(args.output, [build_row(args)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
