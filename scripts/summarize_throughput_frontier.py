#!/usr/bin/env python3
import argparse
import json
import statistics
import sys
from pathlib import Path


def _load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _anchor_name(report: dict, path: Path) -> str:
    inputs = report.get("inputs", {})
    return inputs.get("dna_basename") or path.parent.name


def _run_topk(run: dict, report: dict) -> int:
    if "topk" in run:
        return int(run["topk"])
    return int(report.get("fasim_prealign_cuda_topk", 64))


def _run_suppress_bp(run: dict, report: dict) -> int:
    if "suppress_bp" in run:
        return int(run["suppress_bp"])
    return int(report.get("fasim_prealign_peak_suppress_bp", 5))


def _run_qualifies(run: dict, report: dict) -> bool:
    gate = report.get("quality_gate")
    if not gate:
        return True
    relaxed_recall = float(run["comparison"]["relaxed"]["recall"])
    top_hit_retention = float(run["comparison"]["top_hit_retention"])
    return (
        relaxed_recall >= float(gate.get("min_relaxed_recall", 0.0))
        and top_hit_retention >= float(gate.get("min_top_hit_retention", 0.0))
    )


def _worst_output_metrics(run: dict) -> tuple[str | None, float, float, bool]:
    per_output = run["comparison"].get("per_output_comparisons") or {}
    if not per_output:
        recall = float(run["comparison"]["relaxed"]["recall"])
        top_hit = float(run["comparison"]["top_hit_retention"])
        return None, recall, top_hit, top_hit == 0.0

    worst_name = None
    worst_recall = None
    worst_top_hit = None
    zero_top_hit = False
    for name, stats in per_output.items():
        recall = float(stats["relaxed"]["recall"])
        top_hit = float(stats["top_hit_retention"])
        if top_hit == 0.0:
            zero_top_hit = True
        if worst_name is None:
            worst_name = name
            worst_recall = recall
            worst_top_hit = top_hit
            continue
        assert worst_recall is not None
        assert worst_top_hit is not None
        if (top_hit, recall, name) < (worst_top_hit, worst_recall, worst_name):
            worst_name = name
            worst_recall = recall
            worst_top_hit = top_hit
    assert worst_name is not None
    assert worst_recall is not None
    assert worst_top_hit is not None
    return worst_name, worst_recall, worst_top_hit, zero_top_hit


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _build_rows(report_paths: list[Path]) -> list[dict]:
    buckets: dict[tuple[str, int, int, int], dict] = {}
    for report_path in report_paths:
        report = _load_report(report_path)
        anchor = _anchor_name(report, report_path)
        for run in report.get("runs", []):
            key = (
                run["device_set"],
                int(run["extend_threads"]),
                _run_topk(run, report),
                _run_suppress_bp(run, report),
            )
            bucket = buckets.setdefault(
                key,
                {
                    "device_set": key[0],
                    "extend_threads": key[1],
                    "topk": key[2],
                    "suppress_bp": key[3],
                    "anchors": [],
                    "wall_seconds": [],
                    "relaxed_recall": [],
                    "top_hit_retention": [],
                    "worst_output_relaxed_recall": [],
                    "worst_output_top_hit_retention": [],
                    "zero_top_hit_reports": 0,
                    "qualifying_reports": 0,
                },
            )
            worst_name, worst_recall, worst_top_hit, zero_top_hit = _worst_output_metrics(run)
            bucket["anchors"].append(
                {
                    "anchor": anchor,
                    "report_path": str(report_path),
                    "wall_seconds": float(run["wall_seconds"]),
                    "relaxed_recall": float(run["comparison"]["relaxed"]["recall"]),
                    "top_hit_retention": float(run["comparison"]["top_hit_retention"]),
                    "worst_output": worst_name,
                    "worst_output_relaxed_recall": worst_recall,
                    "worst_output_top_hit_retention": worst_top_hit,
                    "zero_top_hit": zero_top_hit,
                    "qualifies": _run_qualifies(run, report),
                }
            )
            bucket["wall_seconds"].append(float(run["wall_seconds"]))
            bucket["relaxed_recall"].append(float(run["comparison"]["relaxed"]["recall"]))
            bucket["top_hit_retention"].append(float(run["comparison"]["top_hit_retention"]))
            bucket["worst_output_relaxed_recall"].append(worst_recall)
            bucket["worst_output_top_hit_retention"].append(worst_top_hit)
            if zero_top_hit:
                bucket["zero_top_hit_reports"] += 1
            if bucket["anchors"][-1]["qualifies"]:
                bucket["qualifying_reports"] += 1

    rows: list[dict] = []
    for bucket in buckets.values():
        report_count = len(bucket["anchors"])
        row = {
            "device_set": bucket["device_set"],
            "extend_threads": bucket["extend_threads"],
            "topk": bucket["topk"],
            "suppress_bp": bucket["suppress_bp"],
            "report_count": report_count,
            "anchor_names": [item["anchor"] for item in bucket["anchors"]],
            "mean_wall_seconds": _mean(bucket["wall_seconds"]),
            "max_wall_seconds": max(bucket["wall_seconds"]),
            "mean_relaxed_recall": _mean(bucket["relaxed_recall"]),
            "min_relaxed_recall": min(bucket["relaxed_recall"]),
            "mean_top_hit_retention": _mean(bucket["top_hit_retention"]),
            "min_top_hit_retention": min(bucket["top_hit_retention"]),
            "mean_worst_output_relaxed_recall": _mean(bucket["worst_output_relaxed_recall"]),
            "min_worst_output_relaxed_recall": min(bucket["worst_output_relaxed_recall"]),
            "mean_worst_output_top_hit_retention": _mean(bucket["worst_output_top_hit_retention"]),
            "min_worst_output_top_hit_retention": min(bucket["worst_output_top_hit_retention"]),
            "zero_top_hit_reports": bucket["zero_top_hit_reports"],
            "all_top_hit_nonzero": bucket["zero_top_hit_reports"] == 0,
            "qualifying_reports": bucket["qualifying_reports"],
            "qualifies_all_reports": bucket["qualifying_reports"] == report_count,
            "anchor_details": bucket["anchors"],
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            row["mean_wall_seconds"],
            -row["min_worst_output_top_hit_retention"],
            -row["min_worst_output_relaxed_recall"],
            row["topk"],
            row["suppress_bp"],
        )
    )
    return rows


def _mark_pareto(rows: list[dict]) -> None:
    for row in rows:
        dominated = False
        for other in rows:
            if other is row:
                continue
            if (
                other["mean_wall_seconds"] <= row["mean_wall_seconds"]
                and other["min_worst_output_relaxed_recall"] >= row["min_worst_output_relaxed_recall"]
                and other["min_worst_output_top_hit_retention"] >= row["min_worst_output_top_hit_retention"]
                and (
                    other["mean_wall_seconds"] < row["mean_wall_seconds"]
                    or other["min_worst_output_relaxed_recall"] > row["min_worst_output_relaxed_recall"]
                    or other["min_worst_output_top_hit_retention"] > row["min_worst_output_top_hit_retention"]
                )
            ):
                dominated = True
                break
        row["pareto_optimal"] = not dominated


def _render_markdown(rows: list[dict], report_count: int) -> str:
    headers = [
        "device_set",
        "extend_threads",
        "topk",
        "suppress_bp",
        "report_count",
        "mean_wall_seconds",
        "min_worst_output_relaxed_recall",
        "min_worst_output_top_hit_retention",
        "zero_top_hit_reports",
        "all_top_hit_nonzero",
        "qualifying_reports",
        "pareto_optimal",
    ]
    lines = [
        f"# Throughput Frontier Summary",
        "",
        f"- reports: {report_count}",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = [
            str(row["device_set"]),
            str(row["extend_threads"]),
            str(row["topk"]),
            str(row["suppress_bp"]),
            str(row["report_count"]),
            f"{row['mean_wall_seconds']:.3f}",
            f"{row['min_worst_output_relaxed_recall']:.3f}",
            f"{row['min_worst_output_top_hit_retention']:.3f}",
            str(row["zero_top_hit_reports"]),
            "yes" if row["all_top_hit_nonzero"] else "no",
            str(row["qualifying_reports"]),
            "yes" if row["pareto_optimal"] else "no",
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize multiple throughput sweep report.json files into a Pareto-oriented table.",
    )
    parser.add_argument("reports", nargs="+", help="paths to throughput sweep report.json files")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="summary output format (default: markdown)",
    )
    args = parser.parse_args()

    report_paths = [Path(item).resolve() for item in args.reports]
    for path in report_paths:
        if not path.exists():
            raise RuntimeError(f"missing report: {path}")

    rows = _build_rows(report_paths)
    _mark_pareto(rows)
    payload = {
        "report_count": len(report_paths),
        "rows": rows,
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(_render_markdown(rows, len(report_paths)), end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise
