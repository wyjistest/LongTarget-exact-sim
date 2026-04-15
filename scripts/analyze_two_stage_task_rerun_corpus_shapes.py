#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def _load_tsv_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        if not line:
            continue
        values = line.split("\t")
        rows.append(dict(zip(header, values)))
    return rows


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * p
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _bp_bin(value: int) -> str:
    if value <= 512:
        return "<=512"
    if value <= 1024:
        return "513-1024"
    if value <= 2048:
        return "1025-2048"
    return ">2048"


def _target_bin(value: int) -> str:
    if value <= 2048:
        return "<=2048"
    if value <= 4096:
        return "2049-4096"
    if value <= 8192:
        return "4097-8192"
    return ">8192"


def _output_row_bin(value: int) -> str:
    if value == 0:
        return "0"
    if value <= 4:
        return "1-4"
    if value <= 16:
        return "5-16"
    return ">16"


def _bucket_summary(label: str, rows: list[dict[str, object]]) -> dict[str, object]:
    rerun_bp_values = [int(row["rerun_bp"]) for row in rows]
    rerun_seconds_values = [float(row["rerun_total_seconds"]) for row in rows]
    seconds_per_kbp_values = [float(row["seconds_per_kbp"]) for row in rows]
    return {
        "label": label,
        "task_count": len(rows),
        "rerun_bp_total": sum(rerun_bp_values),
        "rerun_seconds_total": sum(rerun_seconds_values),
        "rerun_bp_p50": _percentile([float(value) for value in rerun_bp_values], 0.5),
        "rerun_bp_p90": _percentile([float(value) for value in rerun_bp_values], 0.9),
        "rerun_total_seconds_p50": _percentile(rerun_seconds_values, 0.5),
        "rerun_total_seconds_p90": _percentile(rerun_seconds_values, 0.9),
        "seconds_per_kbp_p50": _percentile(seconds_per_kbp_values, 0.5),
        "seconds_per_kbp_p90": _percentile(seconds_per_kbp_values, 0.9),
    }


def _summarize_named_buckets(
    rows: list[dict[str, object]],
    labels: list[str],
    key_fn,
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {label: [] for label in labels}
    for row in rows:
        grouped.setdefault(key_fn(row), []).append(row)
    return [_bucket_summary(label, grouped.get(label, [])) for label in labels]


def _summarize_rule_strand(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        label = f"{row['rule']}|{row['strand']}"
        grouped.setdefault(label, []).append(row)
    summaries = []
    for label, bucket_rows in sorted(grouped.items()):
        rule_str, strand = label.split("|", 1)
        summary = _bucket_summary(label, bucket_rows)
        summary["rule"] = int(rule_str)
        summary["strand"] = strand
        summaries.append(summary)
    return summaries


def _render_markdown(summary: dict[str, object]) -> str:
    aggregate = summary["aggregate"]
    lines = [
        "# Two-Stage Task Rerun Corpus Shape Audit",
        "",
        f"- corpus_manifest: {summary['corpus_manifest']}",
        f"- task_count: {aggregate['task_count']}",
        f"- rerun_seconds_total: {aggregate['rerun_seconds_total']:.6f}",
        f"- rerun_bp_total: {aggregate['rerun_bp_total']}",
        f"- gpu_batching_candidate: {aggregate['gpu_batching_candidate']}",
        "",
        "## Top Rerun Seconds",
        "",
    ]
    for row in summary["top_rerun_seconds_tasks"]:
        lines.append(
            f"- {row['task_key']}: seconds={row['rerun_total_seconds']:.6f}, "
            f"rerun_bp={row['rerun_bp']}, seconds_per_kbp={row['seconds_per_kbp']:.6f}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit frozen task-rerun corpus shapes for GPU batching feasibility.")
    parser.add_argument("--corpus-manifest", required=True, help="task_rerun_corpus_manifest.tsv path")
    parser.add_argument("--output-dir", required=True, help="output directory for shape-audit summary")
    args = parser.parse_args()

    manifest_path = Path(args.corpus_manifest).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_rows = _load_tsv_rows(manifest_path)
    rows: list[dict[str, object]] = []
    for row in raw_rows:
        rerun_bp = int(row["rerun_bp"])
        rerun_total_seconds = float(row["rerun_total_seconds"])
        seconds_per_kbp = 0.0 if rerun_bp <= 0 else rerun_total_seconds / (float(rerun_bp) / 1000.0)
        rows.append(
            {
                "tile_key": row["tile_key"],
                "tile_filename": row["tile_filename"],
                "task_key": row["task_key"],
                "rule": int(row["rule"]),
                "strand": row["strand"],
                "target_length": int(row["target_length"]),
                "rerun_bp": rerun_bp,
                "task_output_row_count": int(row["task_output_row_count"]),
                "rerun_total_seconds": rerun_total_seconds,
                "seconds_per_kbp": seconds_per_kbp,
            }
        )

    total_rerun_seconds = sum(float(row["rerun_total_seconds"]) for row in rows)
    total_rerun_bp = sum(int(row["rerun_bp"]) for row in rows)

    rerun_bp_bins = _summarize_named_buckets(
        rows,
        ["<=512", "513-1024", "1025-2048", ">2048"],
        lambda row: _bp_bin(int(row["rerun_bp"])),
    )
    target_length_bins = _summarize_named_buckets(
        rows,
        ["<=2048", "2049-4096", "4097-8192", ">8192"],
        lambda row: _target_bin(int(row["target_length"])),
    )
    output_row_bins = _summarize_named_buckets(
        rows,
        ["0", "1-4", "5-16", ">16"],
        lambda row: _output_row_bin(int(row["task_output_row_count"])),
    )
    rule_strand_buckets = _summarize_rule_strand(rows)

    gpu_candidate_seconds = 0.0
    for bucket in rule_strand_buckets:
        label = f"{bucket['rule']}|{bucket['strand']}"
        bucket_rows = [row for row in rows if f"{row['rule']}|{row['strand']}" == label]
        median_rerun_bp = _percentile([float(row["rerun_bp"]) for row in bucket_rows], 0.5)
        if len(bucket_rows) >= 4 and median_rerun_bp >= 512.0:
            gpu_candidate_seconds += sum(float(row["rerun_total_seconds"]) for row in bucket_rows)
    gpu_batching_candidate = total_rerun_seconds > 0.0 and (gpu_candidate_seconds / total_rerun_seconds) >= 0.8

    summary = {
        "corpus_manifest": str(manifest_path),
        "aggregate": {
            "task_count": len(rows),
            "rerun_seconds_total": total_rerun_seconds,
            "rerun_bp_total": total_rerun_bp,
            "gpu_batching_candidate": gpu_batching_candidate,
            "gpu_candidate_seconds_total": gpu_candidate_seconds,
        },
        "rerun_bp_bins": rerun_bp_bins,
        "target_length_bins": target_length_bins,
        "output_row_bins": output_row_bins,
        "rule_strand_buckets": rule_strand_buckets,
        "top_rerun_seconds_tasks": sorted(rows, key=lambda row: (-float(row["rerun_total_seconds"]), str(row["task_key"])))[:10],
        "top_rerun_bp_tasks": sorted(rows, key=lambda row: (-int(row["rerun_bp"]), str(row["task_key"])))[:10],
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
