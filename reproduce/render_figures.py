#!/usr/bin/env python3
"""Render GASAL2-LongTarget paper figures and tables from frozen source data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
FREEZE_ID = "paper-data-v1-dccfd49-20260716"
FIGURE_BASES = (
    "fig1_method_fast_topk",
    "fig2_performance_generalization",
    "fig3_ablation_resources",
    "fig4_operating_envelope",
    "figS1_archive_first",
)
FASIM = "#D55E00"
GASAL2 = "#0072B2"
SHARED = "#6B7280"
CLEAN = "#009E73"
MISMATCH = "#CC79A7"
GUARD = "#8A8A8A"
ACCENT = "#E69F00"
RED = "#A61B1B"
GRID = "#D8DCE2"
INK = "#1F2933"


matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.7,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "svg.hashsalt": FREEZE_ID,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "pdf.compression": 9,
    }
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"missing TSV header: {path}")
        rows = list(reader)
    if rows and {row.get("data_freeze_id", "") for row in rows} != {FREEZE_ID}:
        raise ValueError(f"source data is not from {FREEZE_ID}: {path}")
    return rows


def number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite plot value: {value}")
    return result


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_tsv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def figure1_panel_boxes() -> dict[str, tuple[float, float, float, float]]:
    return {
        "A": (0.06, 0.88, 0.81, 0.15),
        "B1": (0.06, 0.42, 0.47, 0.27),
        "B2": (0.52, 0.42, 0.47, 0.27),
        "C": (0.06, 0.42, 0.08, 0.27),
        "D": (0.52, 0.42, 0.08, 0.27),
    }


def matplotlib_panel_rectangle(
    box: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    left, width, bottom, height = box
    return left, bottom, width, height


def primary_fast_topk_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row["output_contract"] == "fast_topk_score_stability_nt"
        and row["claim_id"] in {"C1", "C2", "C4"}
    ]


def panel_label(ax: Axes, label: str) -> None:
    ax.text(
        -0.02,
        1.04,
        label,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="right",
        va="bottom",
        color=INK,
    )


def clean_axis(ax: Axes, *, grid_axis: str = "y") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6, zorder=0)
    ax.tick_params(length=3, width=0.6, color=INK)


def save_figure(fig: Figure, output_dir: Path, base: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / f"{base}.svg"
    fig.savefig(
        svg_path,
        format="svg",
        metadata={"Creator": "reproduce/render_figures.py", "Date": None},
    )
    svg_text = svg_path.read_text(encoding="utf-8")
    atomic_text(svg_path, "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n")
    fig.savefig(
        output_dir / f"{base}.pdf",
        format="pdf",
        metadata={
            "Creator": "reproduce/render_figures.py",
            "Producer": "Matplotlib",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(
        output_dir / f"{base}_600dpi.png",
        format="png",
        dpi=600,
        metadata={"Software": "reproduce/render_figures.py"},
    )
    plt.close(fig)


def draw_box(ax: Axes, x: float, width: float, label: str, color: str) -> None:
    ax.add_patch(Rectangle((x, 0.28), width, 0.44, facecolor="white", edgecolor=color, linewidth=1.3))
    ax.text(x + width / 2, 0.5, label, ha="center", va="center", color=INK, fontsize=8)


def arrow(ax: Axes, start: tuple[float, float], end: tuple[float, float], color: str = SHARED) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=9, color=color, linewidth=1))


def render_figure1(source: Path, figures: Path) -> None:
    pairs = read_tsv(source / "paired_speedups.tsv")
    c1 = [row for row in pairs if row["workload_id"] == "c1_h19_chr21_chr22_fast_topk"]
    fig = plt.figure(figsize=(7.2, 8.0))
    axes = {
        name: fig.add_axes(matplotlib_panel_rectangle(box))
        for name, box in figure1_panel_boxes().items()
    }

    ax = axes["A"]
    panel_label(ax, "A")
    ax.set_title("Shared LongTarget task construction and output semantics", loc="left", fontweight="bold")
    ax.set(xlim=(0, 1), ylim=(0, 1))
    draw_box(ax, 0.02, 0.19, "RNA query +\nDNA targets", SHARED)
    draw_box(ax, 0.28, 0.19, "Triplex task\nconstruction", SHARED)
    draw_box(ax, 0.54, 0.19, "Candidate\nevaluation", SHARED)
    draw_box(ax, 0.80, 0.18, "Clustered\nTFO1-TFO5", SHARED)
    for start, end in ((0.21, 0.28), (0.47, 0.54), (0.73, 0.80)):
        arrow(ax, (start, 0.5), (end, 0.5))
    ax.axis("off")

    ax = axes["B1"]
    panel_label(ax, "B1")
    ax.set_title("Fasim-LongTarget", loc="left", color=FASIM, fontweight="bold")
    ax.set(xlim=(0, 1), ylim=(0, 1))
    draw_box(ax, 0.04, 0.25, "Peak-guided\nreduction", FASIM)
    draw_box(ax, 0.38, 0.25, "CPU exact\nalignment", FASIM)
    draw_box(ax, 0.72, 0.24, "Rank +\ncluster", SHARED)
    arrow(ax, (0.29, 0.5), (0.38, 0.5), FASIM)
    arrow(ax, (0.63, 0.5), (0.72, 0.5), FASIM)
    ax.text(0.5, 0.08, "CPU-authoritative candidate semantics", ha="center", color=SHARED, fontsize=7.5)
    ax.axis("off")

    ax = axes["B2"]
    panel_label(ax, "B2")
    ax.set_title("GASAL2-LongTarget fast top-K", loc="left", color=GASAL2, fontweight="bold")
    ax.set(xlim=(0, 1), ylim=(0, 1))
    draw_box(ax, 0.03, 0.25, "GPU batched\nscore", GASAL2)
    draw_box(ax, 0.37, 0.27, "Traceback +\nmaterialize", GASAL2)
    draw_box(ax, 0.73, 0.24, "Ordered\ncommit", SHARED)
    arrow(ax, (0.28, 0.5), (0.37, 0.5), GASAL2)
    arrow(ax, (0.64, 0.5), (0.73, 0.5), GASAL2)
    ax.text(0.5, 0.08, "Checked score / stability / Nt top-K contract", ha="center", color=SHARED, fontsize=7.5)
    ax.axis("off")

    ax = axes["C"]
    panel_label(ax, "C")
    ax.set_title("Conceptual execution pattern", loc="left", fontweight="bold")
    ax.set(xlim=(-2, 10), ylim=(-0.2, 2.4))
    ax.broken_barh([(0.3, 2.1), (2.7, 2.0), (5.0, 2.2), (7.5, 2.0)], (1.35, 0.42), facecolors=FASIM)
    ax.broken_barh([(0.3, 2.1), (2.9, 2.0), (5.5, 2.1)], (0.45, 0.42), facecolors=GASAL2)
    ax.broken_barh([(2.0, 1.5), (4.6, 1.5), (7.2, 1.5)], (0.02, 0.30), facecolors=ACCENT)
    ax.text(-0.2, 1.56, "Fasim CPU", ha="right", va="center", fontsize=7.5)
    ax.text(-0.2, 0.66, "GPU", ha="right", va="center", fontsize=7.5)
    ax.text(-0.2, 0.16, "CPU finalizer", ha="right", va="center", fontsize=7.5)
    ax.set_xlabel("Execution order (conceptual)")
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_yticks([])
    clean_axis(ax, grid_axis="x")

    ax = axes["D"]
    panel_label(ax, "D")
    ax.set_title("Measured fast top-K speedup", loc="left", fontweight="bold")
    values = [number(row["paired_speedup"]) for row in c1]
    y = [1 + (index - 2) * 0.035 for index in range(len(values))]
    ax.scatter(values, y, s=32, facecolor="white", edgecolor=GASAL2, linewidth=1.2, zorder=3, label="paired run")
    median = statistics.median(values)
    ax.axvline(median, color=GASAL2, linewidth=1.5, label=f"median {median:.2f}x")
    ax.axvline(1, color=SHARED, linestyle="--", linewidth=0.9)
    ax.set(yticks=[], xlabel="Baseline wall / GASAL2 wall", ylim=(0.75, 1.25))
    ax.legend(frameon=False, loc="lower left")
    clean_axis(ax, grid_axis="x")
    save_figure(fig, figures, FIGURE_BASES[0])


def render_figure2(source: Path, figures: Path) -> None:
    pairs = read_tsv(source / "paired_speedups.tsv")
    generalization = read_tsv(source / "generalization.tsv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.3), gridspec_kw={"width_ratios": [0.8, 1.7]})

    ax = axes[0]
    panel_label(ax, "A")
    rows = [row for row in pairs if row["workload_id"] == "c1_h19_chr21_chr22_fast_topk"]
    values = [number(row["paired_speedup"]) for row in rows]
    ax.scatter([0] * len(values), values, marker="o", facecolor="white", edgecolor=GASAL2, s=40, zorder=3)
    summary = next(row for row in read_tsv(source / "paired_speedup_summary.tsv") if row["workload_id"] == "c1_h19_chr21_chr22_fast_topk")
    median = number(summary["median_paired_speedup"])
    low = number(summary["paired_speedup_bootstrap_ci_low"])
    high = number(summary["paired_speedup_bootstrap_ci_high"])
    ax.errorbar([0], [median], yerr=[[median - low], [high - median]], fmt="s", color=GASAL2, capsize=4, markersize=5, zorder=4)
    ax.set(xticks=[0], xticklabels=["H19\nchr21+chr22\nn=5"], ylabel="Paired speedup (x)", title="Primary fast top-K")
    ax.set_ylim(min(values) - 0.2, max(values) + 0.2)
    clean_axis(ax)

    ax = axes[1]
    panel_label(ax, "B")
    supported = [row for row in generalization if row["row_type"] == "supported_query"]
    labels = [row["workload_id"].replace("_", " ") for row in supported]
    ypos = list(range(len(supported)))
    for y, row in zip(ypos, supported, strict=True):
        clean = row["status"] == "clean"
        ax.scatter(
            number(row["median_paired_speedup"]), y,
            marker="o" if clean else "X", s=36 if clean else 42,
            facecolor="white" if clean else MISMATCH,
            edgecolor=CLEAN if clean else MISMATCH,
            linewidth=1.1, zorder=3,
        )
        ax.text(number(row["median_paired_speedup"]) + 0.35, y, f"n={row['valid_pairs']}", va="center", fontsize=7)
    ax.set(yticks=ypos, yticklabels=labels, xlabel="Median paired speedup (x)", title="Preregistered supported-query panel")
    ax.invert_yaxis()
    ax.axvline(1, color=SHARED, linestyle="--", linewidth=0.9)
    clean_axis(ax, grid_axis="x")
    ax.scatter([], [], marker="o", facecolor="white", edgecolor=CLEAN, label="contract clean")
    ax.scatter([], [], marker="X", color=MISMATCH, label="mismatch retained")
    ax.legend(frameon=False, loc="lower left")
    fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.16, wspace=0.48)
    save_figure(fig, figures, FIGURE_BASES[1])


def median_by(rows: list[dict[str, str]], field: str) -> float:
    values = [number(row[field]) for row in rows if row.get(field, "NA") not in {"NA", ""}]
    if not values:
        raise ValueError(f"no values for {field}")
    return statistics.median(values)


def render_figure3(source: Path, figures: Path) -> None:
    pairs = read_tsv(source / "paired_speedups.tsv")
    summaries = read_tsv(source / "paired_speedup_summary.tsv")
    ablation = read_tsv(source / "ablation.tsv")
    resources = read_tsv(source / "resources.tsv")
    runs = read_tsv(source / "benchmark_runs.tsv")
    summary_map = {row["workload_id"]: row for row in summaries}
    ablation_map = {row["workload_id"]: row for row in ablation if row["row_type"] == "phase4_paired"}
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.2))

    ax = axes[0, 0]
    panel_label(ax, "A")
    workloads = ["c4_h19_chr21_two_slot", "c4_h19_chr22_two_slot"]
    for x, workload in enumerate(workloads):
        values = [number(row["paired_speedup"]) for row in pairs if row["workload_id"] == workload]
        offsets = [-0.08, -0.04, 0, 0.04, 0.08]
        ax.scatter([x + value for value in offsets], values, facecolor="white", edgecolor=GASAL2, s=30, zorder=3)
        row = summary_map[workload]
        median = number(row["median_paired_speedup"])
        low = number(row["paired_speedup_bootstrap_ci_low"])
        high = number(row["paired_speedup_bootstrap_ci_high"])
        ax.errorbar([x], [median], yerr=[[median-low], [high-median]], fmt="s", color=GASAL2, capsize=4, zorder=4)
    ax.axhline(1, color=SHARED, linestyle="--", linewidth=0.9)
    ax.set(xticks=[0, 1], xticklabels=["chr21\nn=5", "chr22\nn=5"], ylabel="Two-slot / sync speedup (x)", title="Two-slot scheduling")
    clean_axis(ax)

    ax = axes[0, 1]
    panel_label(ax, "B")
    exact_ids = ["c6_exact_h19_2mb", "c6_exact_kcnq_segment_chr22"]
    x = [0, 1]
    width = 0.32
    stage = [number(ablation_map[w]["median_exact_stage_speedup"]) for w in exact_ids]
    end = [number(ablation_map[w]["median_paired_speedup"]) for w in exact_ids]
    ax.bar([v - width/2 for v in x], stage, width, color=GASAL2, label="exact-column stage")
    ax.bar([v + width/2 for v in x], end, width, color=FASIM, label="end-to-end")
    ax.axhline(1, color=SHARED, linestyle="--", linewidth=0.9)
    ax.set(xticks=x, xticklabels=["H19 2 Mb\nn=3", "KCNQ1OT1\nsegment n=3"], ylabel="Speedup (x)", title="Exact-column optimization")
    ax.legend(frameon=False)
    clean_axis(ax)

    ax = axes[1, 0]
    panel_label(ax, "C")
    resource_ids = ["phase4_c5_archive_h19_2mb", "phase4_c6_exact_h19_2mb", "phase4_c6_exact_kcnq_segment_chr22"]
    resource_map = {row["resource_id"]: row for row in resources}
    gpu = [number(resource_map[w]["device_memory_peak_mib"]) / 1024 for w in resource_ids]
    rss = [number(resource_map[w]["host_rss_peak_kb"]) / 1024 / 1024 for w in resource_ids]
    xpos = list(range(3))
    ax.bar([v - width/2 for v in xpos], gpu, width, color=GASAL2, label="device peak (GiB)")
    ax.bar([v + width/2 for v in xpos], rss, width, color=ACCENT, label="host RSS (GiB)")
    ax.set(xticks=xpos, xticklabels=["archive", "exact H19", "exact KCNQ"], ylabel="Peak memory (GiB)", title="Measured resource peaks")
    ax.legend(frameon=False)
    clean_axis(ax)

    ax = axes[1, 1]
    panel_label(ax, "D")
    ratios: list[tuple[str, float, float]] = []
    for workload, label in (("c6_exact_h19_2mb", "H19"), ("c6_exact_kcnq_segment_chr22", "KCNQ")):
        timed = [row for row in runs if row["workload_id"] == workload and row["excluded"] == "0"]
        base = [row for row in timed if row["mode"] == "baseline"]
        candidate = [row for row in timed if row["mode"] == "candidate"]
        request_ratio = median_by(candidate, "gasal2_requests") / median_by(base, "gasal2_requests")
        traceback_ratio = median_by(candidate, "traceback_requests") / median_by(base, "traceback_requests")
        ratios.append((label, request_ratio, traceback_ratio))
    for xvalue, (label, request_ratio, traceback_ratio) in enumerate(ratios):
        ax.scatter(xvalue - 0.08, request_ratio, marker="o", facecolor="white", edgecolor=GASAL2, s=38, label="requests" if xvalue == 0 else None)
        ax.scatter(xvalue + 0.08, traceback_ratio, marker="s", facecolor="white", edgecolor=FASIM, s=34, label="tracebacks" if xvalue == 0 else None)
    ax.axhline(1, color=SHARED, linestyle="--", linewidth=0.9)
    ax.set(xticks=[0, 1], xticklabels=["H19\nn=3", "KCNQ\nn=3"], ylabel="Candidate / baseline count", title="Work volume unchanged")
    ax.set_ylim(0.96, 1.04)
    ax.legend(frameon=False)
    clean_axis(ax)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.93, bottom=0.10, hspace=0.42, wspace=0.34)
    save_figure(fig, figures, FIGURE_BASES[2])


def render_figure4(source: Path, figures: Path) -> None:
    rows = read_tsv(source / "operating_envelope.tsv")
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    categories = {
        "equivalence_first_full_output": (FASIM, "s"),
        "segmented_archive_first_exact_scoreinfo_v1": (SHARED, "D"),
        "long_query_boundary": (RED, "X"),
        "shifted_grid_bounded_full_rows": (ACCENT, "^"),
    }
    for index, row in enumerate(rows):
        color, marker = categories[row["contract"]]
        ax.scatter(index, number(row["speedup"]), color=color, marker=marker, s=58, zorder=3)
        ax.text(index, number(row["speedup"]) + 0.017, f"n={row['n']}", ha="center", fontsize=7)
    ax.axhline(1, color=INK, linestyle="--", linewidth=0.9, label="parity")
    labels = [row["workload_id"].replace("_", " ") for row in rows]
    ax.set(xticks=range(len(rows)), xticklabels=labels, ylabel="Speedup (x)")
    ax.tick_params(axis="x", rotation=25)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    clean_axis(ax)
    handles = []
    for contract, (color, marker) in categories.items():
        handles.append(ax.scatter([], [], color=color, marker=marker, label=contract.replace("_", " ")))
    ax.legend(handles=handles, frameon=False, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Operating envelope by output contract", y=0.98, fontsize=11)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.73, bottom=0.27)
    save_figure(fig, figures, FIGURE_BASES[3])


def render_archive_figure(source: Path, figures: Path) -> None:
    rows = read_tsv(source / "archive_first.tsv")
    restore = [row for row in rows if row["row_type"] == "archive_restore"]
    merge = [row for row in rows if row["row_type"] == "bounded_exact_merge"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.2))

    ax = axes[0]
    panel_label(ax, "A")
    text_bytes = statistics.median(number(row["legacy_text_bytes"]) for row in restore)
    archive_bytes = statistics.median(number(row["archive_bytes"]) for row in restore)
    ax.bar([0, 1], [text_bytes / 1024**2, archive_bytes / 1024**2], color=[FASIM, GASAL2])
    ax.set(xticks=[0, 1], xticklabels=["text", "archive"], ylabel="Stored output (MiB)", title="Lossless storage")
    ax.text(0.5, max(text_bytes, archive_bytes) / 1024**2 * 0.82, f"{text_bytes/archive_bytes:.2f}x smaller", ha="center", fontsize=7.5)
    clean_axis(ax)

    ax = axes[1]
    panel_label(ax, "B")
    memory = statistics.median(number(row["memory_peak_rss_kb"]) for row in merge) / 1024
    sqlite = statistics.median(number(row["sqlite_peak_rss_kb"]) for row in merge) / 1024
    ax.bar([0, 1], [memory, sqlite], color=[FASIM, GASAL2])
    ax.set(xticks=[0, 1], xticklabels=["memory", "SQLite"], ylabel="Peak RSS (MiB)", title="Exact merge memory")
    clean_axis(ax)

    ax = axes[2]
    panel_label(ax, "C")
    run_restore = [number(row["candidate_run_restore_wall_seconds"]) for row in restore]
    baseline = [number(row["baseline_wall_seconds"]) for row in restore]
    merge_memory = [number(row["memory_merge_wall_seconds"]) for row in merge]
    merge_sqlite = [number(row["sqlite_merge_wall_seconds"]) for row in merge]
    ax.bar([0, 1, 2, 3], [statistics.median(baseline), statistics.median(run_restore), statistics.median(merge_memory), statistics.median(merge_sqlite)], color=[FASIM, GASAL2, FASIM, GASAL2])
    ax.set(
        xticks=[0, 1, 2, 3],
        xticklabels=["text run", "archive + restore", "memory merge", "SQLite merge"],
        ylabel="Wall time (s)",
        title="Wall-time trade-off",
    )
    ax.tick_params(axis="x", labelrotation=27, labelsize=6.7)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    clean_axis(ax)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.85, bottom=0.30, wspace=0.48)
    save_figure(fig, figures, FIGURE_BASES[4])


def compact(value: str, digits: int = 3) -> str:
    if value in {"NA", ""}:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except ValueError:
        return value


def markdown_table(fields: list[str], rows: list[dict[str, object]]) -> str:
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[field]).replace("|", "\\|") for field in fields) + " |")
    return "\n".join(lines) + "\n"


def latex_escape(value: object) -> str:
    text = str(value)
    for old, new in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"), ("&", r"\&"), ("#", r"\#")):
        text = text.replace(old, new)
    return text


def latex_table(fields: list[str], rows: list[dict[str, object]]) -> str:
    columns = "l" * len(fields)
    body = [
        f"\\begin{{tabular}}{{{columns}}}",
        "\\toprule",
        " & ".join(latex_escape(f) for f in fields) + " \\\\",
        "\\midrule",
    ]
    body.extend(
        " & ".join(latex_escape(row[field]) for field in fields) + " \\\\" for row in rows
    )
    body.extend(["\\bottomrule", "\\end{tabular}", ""])
    return "\n".join(body)


def write_table_bundle(output: Path, name: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    write_tsv(output / f"{name}.tsv", fields, rows)
    atomic_text(output / f"{name}.md", markdown_table(fields, rows))
    atomic_text(output / f"{name}.tex", latex_table(fields, rows))


def render_tables(source: Path, output: Path) -> None:
    pairs = read_tsv(source / "paired_speedups.tsv")
    summaries = read_tsv(source / "paired_speedup_summary.tsv")
    generalization = read_tsv(source / "generalization.tsv")
    ablation = read_tsv(source / "ablation.tsv")
    resources = read_tsv(source / "resources.tsv")
    correctness = read_tsv(source / "correctness.tsv")
    first_pair: dict[str, dict[str, str]] = {}
    for row in pairs:
        first_pair.setdefault(row["workload_id"], row)

    fields = ["workload_id", "claim", "query", "query_nt", "target", "contract", "n", "machine_id"]
    rows = [
        {
            "workload_id": row["workload_id"], "claim": row["claim_id"],
            "query": first_pair[row["workload_id"]]["query_id"],
            "query_nt": first_pair[row["workload_id"]]["query_length_nt"],
            "target": first_pair[row["workload_id"]]["target_id"],
            "contract": row["output_contract"], "n": row["n"], "machine_id": row["machine_id"],
        }
        for row in summaries
    ]
    write_table_bundle(output, "table1_workloads", fields, rows)

    fields = ["workload_id", "claim", "n", "baseline_s", "candidate_s", "median_speedup", "bootstrap95_low", "bootstrap95_high", "clean_pairs"]
    rows = [
        {
            "workload_id": row["workload_id"], "claim": row["claim_id"], "n": row["n"],
            "baseline_s": compact(row["median_baseline_wall_seconds"]),
            "candidate_s": compact(row["median_candidate_wall_seconds"]),
            "median_speedup": compact(row["median_paired_speedup"]),
            "bootstrap95_low": compact(row["paired_speedup_bootstrap_ci_low"]),
            "bootstrap95_high": compact(row["paired_speedup_bootstrap_ci_high"]),
            "clean_pairs": row["contract_clean_pairs"],
        }
        for row in summaries
    ]
    write_table_bundle(output, "table2_performance", fields, rows)

    fields = ["workload_id", "row_type", "status", "score_top5", "stability_top5", "nt_top5", "fallbacks", "guard_reason"]
    rows = []
    for row in correctness:
        rows.append(
            {
                "workload_id": row["workload_id"], "row_type": row["row_type"], "status": row["status"],
                "score_top5": row["top5_score_equal"], "stability_top5": row["top5_stability_equal"],
                "nt_top5": row["top5_nt_equal"], "fallbacks": row["fallbacks"], "guard_reason": row["guard_reason"],
            }
        )
    write_table_bundle(output, "table3_correctness", fields, rows)

    fields = ["row_type", "workload_id", "metric", "value", "n", "status"]
    rows = []
    for row in ablation:
        metric = "median_paired_speedup"
        value = row[metric]
        if row["workload_id"] == "c5_archive_h19_2mb":
            metric, value = "storage_reduction_ratio", row["median_storage_reduction_ratio"]
        elif row["workload_id"] == "c5_archive_large_synthetic":
            metric, value = "peak_rss_reduction_fraction", row["median_peak_rss_reduction_fraction"]
        elif row["claim_id"] == "C6":
            metric, value = "exact_stage_speedup", row["median_exact_stage_speedup"]
        rows.append({"row_type": row["row_type"], "workload_id": row["workload_id"], "metric": metric, "value": compact(value, 6), "n": row["n"], "status": "clean"})
    for row in resources:
        rows.append({"row_type": "resource", "workload_id": row["workload_id"], "metric": "device_peak_mib", "value": row["device_memory_peak_mib"], "n": row["worker_count"], "status": row["status"]})
    write_table_bundle(output, "table4_ablation_resources", fields, rows)

    supplementary = output.parent / "supplementary"
    supplementary.mkdir(parents=True, exist_ok=True)
    envelope = read_tsv(source / "operating_envelope.tsv")
    write_tsv(supplementary / "operating_envelope.tsv", list(envelope[0]), envelope)
    guard_rows = [row for row in generalization if row["row_type"] == "full_length_guard"]
    if len(guard_rows) != 3:
        raise ValueError("expected three full-length guard rows")


def render_mapping(output: Path) -> None:
    fields = ["figure_id", "panel", "source_data_file", "filter", "output_contract"]
    rows = [
        {"figure_id": "Figure 1", "panel": "D", "source_data_file": "paired_speedups.tsv", "filter": "workload_id=c1_h19_chr21_chr22_fast_topk", "output_contract": "fast_topk_score_stability_nt"},
        {"figure_id": "Figure 2", "panel": "A", "source_data_file": "paired_speedups.tsv;paired_speedup_summary.tsv", "filter": "claim_id=C1", "output_contract": "fast_topk_score_stability_nt"},
        {"figure_id": "Figure 2", "panel": "B", "source_data_file": "generalization.tsv", "filter": "row_type=supported_query", "output_contract": "fast_topk_score_stability_nt"},
        {"figure_id": "Figure 3", "panel": "A", "source_data_file": "paired_speedups.tsv;paired_speedup_summary.tsv", "filter": "claim_id=C4", "output_contract": "fast_topk_score_stability_nt"},
        {"figure_id": "Figure 3", "panel": "B-D", "source_data_file": "ablation.tsv;resources.tsv;benchmark_runs.tsv", "filter": "claim_id in {C5,C6}", "output_contract": "full_tfosorted_rowset;archive_restore_only"},
        {"figure_id": "Figure 4", "panel": "all", "source_data_file": "operating_envelope.tsv", "filter": "all rows", "output_contract": "mixed;shape-coded"},
        {"figure_id": "Figure S1", "panel": "all", "source_data_file": "archive_first.tsv", "filter": "all rows", "output_contract": "archive_restore_only"},
    ]
    write_tsv(output, fields, rows)


def render_captions(output: Path) -> None:
    text = """# Figure Captions

## Figure 1. Contract-aware fast top-K execution

**A**, shared LongTarget task construction and downstream clustered TFO1-TFO5 semantics. **B1**, Fasim-LongTarget peak-guided reduction and CPU exact alignment. **B2**, the checked GASAL2 fast top-K path; no full-output replacement is implied. **C**, conceptual execution patterns. **D**, five paired H19 chr21+chr22 fast top-K runs on the recorded two-GPU machine; points are paired speedups and the line is the median. Source: `paper/source_data/paired_speedups.tsv`.

## Figure 2. Primary performance and preregistered generalization

**A**, five paired H19 chr21+chr22 fast top-K speedups with the median and deterministic bootstrap 95% interval. **B**, median paired speedup for 13 preregistered supported-query workloads under the score/stability/Nt clustered TFO1-TFO5 contract. Circles denote 10 contract-clean workloads; crosses retain three mismatch workloads. Labels report paired `n`; four breadth rows have `n=1` and no inferential interval. Hardware is the machine recorded in the frozen source data. Source: `paired_speedups.tsv`, `paired_speedup_summary.tsv`, and `generalization.tsv`.

## Figure 3. Scheduling, exact-column, work-volume, and resource ablations

**A**, paired two-slot versus synchronous GASAL2 speedups on chr21 and chr22 (`n=5` each, one worker per GPU), with median bootstrap 95% intervals. **B**, median exact-column stage and end-to-end speedups for H19 2 Mb and a KCNQ1OT1 2048-nt segment (`n=3` each); stage gains are not interpreted as equal end-to-end gains. **C**, measured device-memory and host-RSS peaks. **D**, candidate-to-baseline GASAL2 request and traceback count ratios computed from frozen run rows; both remain unchanged. All paired output gates were clean and fallbacks were zero. Source: `paired_speedups.tsv`, `paired_speedup_summary.tsv`, `ablation.tsv`, `resources.tsv`, and `benchmark_runs.tsv`.

## Figure 4. Operating envelope

Speedup by workload and output contract, with a dashed 1x parity line. Shapes distinguish full-output, short integrated, long-query boundary, and bounded max8 contracts. The max8 KCNQ1OT1 point has three paired repeats; historical full-output and boundary points are descriptive `n=1` evidence. Negative, fallback, and below-promotion results are retained. Source: `paper/source_data/operating_envelope.tsv`.

## Figure S1. Archive-first storage and bounded-memory merge

**A**, text and lossless archive bytes across three paired H19 2 Mb runs. **B**, peak RSS for in-memory and SQLite exact merge across three 150,000-row synthetic repetitions. **C**, median complete run plus restore and merge wall times. All six comparisons restored or merged byte-identical output. SQLite reduces memory at additional wall-time cost; storage reduction is not reported as compute acceleration. Source: `paper/source_data/archive_first.tsv`.
"""
    atomic_text(output, text)


def render_output_manifest(output_root: Path) -> None:
    fields = ["data_freeze_id", "path", "size_bytes", "sha256"]
    rows = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.name == "render_manifest.tsv":
            continue
        relative = path.relative_to(output_root).as_posix()
        if not (
            relative == "captions.md"
            or relative.startswith("figures/")
            or relative.startswith("tables/")
            or relative.startswith("supplementary/")
        ):
            continue
        rows.append(
            {
                "data_freeze_id": FREEZE_ID,
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    write_tsv(output_root / "figures/render_manifest.tsv", fields, rows)


def render_all(source: Path, output_root: Path) -> None:
    source = source.resolve()
    output_root = output_root.resolve()
    manifest = json.loads((source / "paired_speedup_summary.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or any(
        row.get("data_freeze_id") != FREEZE_ID for row in manifest.get("workloads", [])
    ):
        raise ValueError("paired summary JSON is not from the frozen dataset")
    figures = output_root / "figures"
    render_figure1(source, figures)
    render_figure2(source, figures)
    render_figure3(source, figures)
    render_figure4(source, figures)
    render_archive_figure(source, figures)
    render_tables(source, output_root / "tables")
    render_mapping(figures / "source_mapping.tsv")
    render_captions(output_root / "captions.md")
    render_output_manifest(output_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=ROOT / "paper/source_data")
    parser.add_argument("--output-root", type=Path, default=ROOT / "paper")
    args = parser.parse_args()
    render_all(args.source_dir, args.output_root)
    print(f"data_freeze_id={FREEZE_ID}")
    print(f"figures={len(FIGURE_BASES)}")
    print("table_bundles=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
