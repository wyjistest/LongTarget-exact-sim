#!/usr/bin/env python3
import argparse
import dataclasses
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


@dataclasses.dataclass(frozen=True)
class TileSpec:
    length_bp: int
    stride_bp: int
    select_count: int


def _default_heavy_anchors() -> list[str]:
    anchors = [
        ROOT / ".tmp" / "ucsc" / "hg38" / "anchors_200kb" / "hg38_chr22_21500001_200000.fa",
        ROOT / ".tmp" / "ucsc" / "hg38" / "anchors_200kb" / "hg38_chr22_42500001_200000.fa",
    ]
    return [str(path) for path in anchors if path.exists()]


def _parse_tile_spec(raw: str) -> TileSpec:
    parts = raw.split(":")
    if len(parts) != 3:
        raise RuntimeError(f"invalid --tile-spec {raw!r}; expected LENGTH:STRIDE:SELECT_COUNT")
    length_bp, stride_bp, select_count = (int(part) for part in parts)
    if length_bp <= 0 or stride_bp <= 0 or select_count <= 0:
        raise RuntimeError(f"--tile-spec values must be > 0: {raw!r}")
    return TileSpec(length_bp=length_bp, stride_bp=stride_bp, select_count=select_count)


def _read_single_fasta_length(path: Path) -> int:
    seq_len = 0
    header_seen = False
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header_seen:
                    raise RuntimeError(f"{path} contains multiple FASTA records")
                header_seen = True
                continue
            if not header_seen:
                raise RuntimeError(f"{path} is not a FASTA file")
            seq_len += len(line)
    if not header_seen:
        raise RuntimeError(f"{path} is empty")
    return seq_len


def _tile_starts(seq_len: int, length_bp: int, stride_bp: int) -> list[int]:
    if length_bp > seq_len:
        raise RuntimeError(f"tile length {length_bp} exceeds FASTA length {seq_len}")
    starts = list(range(1, seq_len - length_bp + 2, stride_bp))
    last_start = seq_len - length_bp + 1
    if not starts or starts[-1] != last_start:
        starts.append(last_start)
    deduped: list[int] = []
    seen: set[int] = set()
    for start in starts:
        if start in seen:
            continue
        seen.add(start)
        deduped.append(start)
    return deduped


def _safe_label(path: Path) -> str:
    return path.stem.replace(".", "_")


def _shard_filename(prefix: str, start_bp: int, length_bp: int) -> str:
    return f"{prefix}_{start_bp}_{length_bp}.fa"


def _run_checked(cmd: list[str], *, cwd: Path) -> None:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0:
        return
    raise RuntimeError(
        "command failed\n"
        f"cmd: {' '.join(cmd)}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )


def _make_anchor_shards(anchor_path: Path, output_dir: Path, starts: list[int], length_bp: int) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = _safe_label(anchor_path)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "make_anchor_shards.py"),
        "--input-fasta",
        str(anchor_path),
        "--output-dir",
        str(output_dir),
        "--starts",
        ",".join(str(start) for start in starts),
        "--length",
        str(length_bp),
        "--output-prefix",
        prefix,
    ]
    _run_checked(cmd, cwd=ROOT)
    return [output_dir / _shard_filename(prefix, start, length_bp) for start in starts]


def _run_threshold_modes(
    *,
    dna_path: Path,
    args: argparse.Namespace,
    work_dir: Path,
    run_labels: list[str] | None = None,
) -> tuple[Path, dict[str, object]]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "benchmark_two_stage_threshold_modes.py"),
        "--work-dir",
        str(work_dir),
        "--longtarget",
        str(args.longtarget),
        "--compare-output-mode",
        args.compare_output_mode,
        "--dna",
        str(dna_path),
        "--rna",
        str(args.rna),
        "--rule",
        str(args.rule),
        "--prefilter-topk",
        str(args.prefilter_topk),
        "--peak-suppress-bp",
        str(args.peak_suppress_bp),
        "--score-floor-delta",
        str(args.score_floor_delta),
        "--refine-pad-bp",
        str(args.refine_pad_bp),
        "--refine-merge-gap-bp",
        str(args.refine_merge_gap_bp),
        "--min-peak-score",
        str(args.min_peak_score),
        "--min-support",
        str(args.min_support),
        "--min-margin",
        str(args.min_margin),
        "--strong-score-override",
        str(args.strong_score_override),
        "--max-windows-per-task",
        str(args.max_windows_per_task),
        "--max-bp-per-task",
        str(args.max_bp_per_task),
    ]
    if args.strand:
        cmd += ["--strand", args.strand]
    for label in run_labels or []:
        cmd += ["--run-label", label]
    _run_checked(cmd, cwd=ROOT)
    report_path = work_dir / "report.json"
    if not report_path.exists():
        raise RuntimeError(f"missing report.json after threshold-mode run: {report_path}")
    return report_path, json.loads(report_path.read_text(encoding="utf-8"))


def _candidate_rank_key(candidate: dict[str, object]) -> tuple[object, ...]:
    run = candidate["runs"]["deferred_exact"]
    return (
        -int(run["windows_before_gate"]),
        -int(run["refine_total_bp"]),
        -int(run["prefilter_hits"]),
        candidate["start_bp"],
    )


def _gate_value_flags(item: dict[str, object]) -> dict[str, bool]:
    deferred = item["runs"]["deferred_exact"]
    gated = item["runs"]["deferred_exact_minimal_v1"]
    return {
        "skip_created": int(gated["threshold_skipped_after_gate"]) > 0,
        "threshold_work_reduced": int(gated["threshold_invoked"]) < int(deferred["threshold_invoked"]),
        "window_work_reduced": int(gated["windows_after_gate"]) < int(gated["windows_before_gate"]),
        "refine_bp_reduced": int(gated["refine_total_bp"]) < int(deferred["refine_total_bp"]),
    }


def _quality_flags(
    item: dict[str, object],
    *,
    min_strict_recall: float,
    min_relaxed_recall: float,
    min_top_hit_retention: float,
) -> dict[str, bool]:
    comparison = item["comparisons_vs_legacy"]["deferred_exact_minimal_v1"]
    return {
        "strict_recall_ok": float(comparison["strict"]["recall"]) >= min_strict_recall,
        "relaxed_recall_ok": float(comparison["relaxed"]["recall"]) >= min_relaxed_recall,
        "top_hit_retention_ok": float(comparison["top_hit_retention"]) >= min_top_hit_retention,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Threshold Heavy Micro-Anchor Summary",
        "",
        f"- selected_microanchors: {len(summary['selected_microanchors'])}",
        f"- discovery_reports: {summary['discovery_report_count']}",
        f"- needs_stronger_gate: {summary['decision_flags']['needs_stronger_gate']}",
        f"- needs_relaxation: {summary['decision_flags']['needs_relaxation']}",
        f"- ready_for_broader_anchor_sweep: {summary['decision_flags']['ready_for_broader_anchor_sweep']}",
        "",
        "| anchor | length_bp | selection_rank | start_bp | end_bp | skip_after_gate | strict_recall | relaxed_recall | top_hit_retention | difference_class |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in summary["selected_microanchors"]:
        comparison = item["comparisons_vs_legacy"]["deferred_exact_minimal_v1"]
        run = item["runs"]["deferred_exact_minimal_v1"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["anchor_label"]),
                    str(item["length_bp"]),
                    str(item["selection_rank"]),
                    str(item["start_bp"]),
                    str(item["end_bp"]),
                    str(run["threshold_skipped_after_gate"]),
                    f"{float(comparison['strict']['recall']):.6f}",
                    f"{float(comparison['relaxed']['recall']):.6f}",
                    f"{float(comparison['top_hit_retention']):.6f}",
                    str(comparison["difference_class"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and calibrate heavy-zone two-stage threshold-mode micro-anchors.",
    )
    parser.add_argument(
        "--heavy-anchor",
        action="append",
        default=None,
        help="heavy anchor FASTA path (repeatable). Defaults to known hg38 chr22 heavy 200 kb anchors when present.",
    )
    parser.add_argument("--rna", default="H19.fa")
    parser.add_argument("--rule", default=0, type=int)
    parser.add_argument("--strand", default="")
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "two_stage_threshold_heavy_microanchors"),
        help="output directory for discovery reports and summaries",
    )
    parser.add_argument(
        "--longtarget",
        default=str(ROOT / "longtarget_cuda"),
        help="path to LongTarget binary",
    )
    parser.add_argument(
        "--compare-output-mode",
        choices=("lite", "tfosorted"),
        default="lite",
    )
    parser.add_argument("--prefilter-topk", default=64, type=int)
    parser.add_argument("--peak-suppress-bp", default=5, type=int)
    parser.add_argument("--score-floor-delta", default=0, type=int)
    parser.add_argument("--refine-pad-bp", default=64, type=int)
    parser.add_argument("--refine-merge-gap-bp", default=32, type=int)
    parser.add_argument("--min-peak-score", default=80, type=int)
    parser.add_argument("--min-support", default=2, type=int)
    parser.add_argument("--min-margin", default=6, type=int)
    parser.add_argument("--strong-score-override", default=100, type=int)
    parser.add_argument("--max-windows-per-task", default=8, type=int)
    parser.add_argument("--max-bp-per-task", default=32768, type=int)
    parser.add_argument(
        "--tile-spec",
        action="append",
        default=None,
        help="micro-anchor spec as LENGTH:STRIDE:SELECT_COUNT (repeatable)",
    )
    parser.add_argument("--min-strict-recall", default=0.98, type=float)
    parser.add_argument("--min-relaxed-recall", default=0.98, type=float)
    parser.add_argument("--min-top-hit-retention", default=1.0, type=float)
    args = parser.parse_args()

    heavy_anchor_values = args.heavy_anchor or _default_heavy_anchors()
    if not heavy_anchor_values:
        raise RuntimeError("no heavy anchors available; pass --heavy-anchor explicitly")
    heavy_anchors = [Path(value).resolve() for value in heavy_anchor_values]
    for anchor in heavy_anchors:
        if not anchor.exists():
            raise RuntimeError(f"missing heavy anchor FASTA: {anchor}")

    rna = Path(args.rna)
    if not rna.is_absolute():
        rna = (ROOT / rna).resolve()
    longtarget = Path(args.longtarget)
    if not longtarget.is_absolute():
        longtarget = (ROOT / longtarget).resolve()
    if not rna.exists():
        raise RuntimeError(f"missing RNA fasta: {rna}")
    if not longtarget.exists():
        raise RuntimeError(f"missing LongTarget binary: {longtarget}")
    args.rna = str(rna)
    args.longtarget = str(longtarget)

    tile_specs = [_parse_tile_spec(raw) for raw in (args.tile_spec or ["25000:12500:2", "50000:25000:1"])]

    work_dir = Path(args.work_dir).resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    discovery_candidates: list[dict[str, object]] = []
    for anchor_path in heavy_anchors:
        anchor_label = _safe_label(anchor_path)
        seq_len = _read_single_fasta_length(anchor_path)
        anchor_root = work_dir / "discovery" / anchor_label
        for tile_spec in tile_specs:
            starts = _tile_starts(seq_len, tile_spec.length_bp, tile_spec.stride_bp)
            tile_root = anchor_root / f"{tile_spec.length_bp}bp_stride_{tile_spec.stride_bp}"
            shard_dir = tile_root / "shards"
            report_root = tile_root / "reports"
            shard_paths = _make_anchor_shards(anchor_path, shard_dir, starts, tile_spec.length_bp)
            for start_bp, shard_path in zip(starts, shard_paths):
                end_bp = start_bp + tile_spec.length_bp - 1
                run_dir = report_root / f"{anchor_label}_{start_bp}_{tile_spec.length_bp}"
                report_path, report = _run_threshold_modes(
                    dna_path=shard_path,
                    args=args,
                    work_dir=run_dir,
                    run_labels=["deferred_exact"],
                )
                discovery_candidates.append(
                    {
                        "anchor_label": anchor_label,
                        "anchor_path": str(anchor_path),
                        "length_bp": tile_spec.length_bp,
                        "stride_bp": tile_spec.stride_bp,
                        "select_count": tile_spec.select_count,
                        "start_bp": start_bp,
                        "end_bp": end_bp,
                        "shard_path": str(shard_path),
                        "report_path": str(report_path),
                        "runs": report["runs"],
                        "comparisons_vs_legacy": report["comparisons_vs_legacy"],
                    }
                )

    discovery_candidates.sort(key=_candidate_rank_key)
    selected_microanchors: list[dict[str, object]] = []
    for anchor_path in heavy_anchors:
        anchor_label = _safe_label(anchor_path)
        for tile_spec in tile_specs:
            matching = [
                candidate
                for candidate in discovery_candidates
                if candidate["anchor_label"] == anchor_label and candidate["length_bp"] == tile_spec.length_bp
            ]
            for rank, candidate in enumerate(matching[: tile_spec.select_count], start=1):
                calibration_dir = (
                    work_dir
                    / "calibration"
                    / anchor_label
                    / f"{tile_spec.length_bp}bp_stride_{tile_spec.stride_bp}"
                    / f"{anchor_label}_{candidate['start_bp']}_{tile_spec.length_bp}"
                )
                calibration_report_path, calibration_report = _run_threshold_modes(
                    dna_path=Path(candidate["shard_path"]),
                    args=args,
                    work_dir=calibration_dir,
                )
                selected = {
                    **candidate,
                    "selection_rank": rank,
                    "discovery_report_path": candidate["report_path"],
                    "report_path": str(calibration_report_path),
                    "runs": calibration_report["runs"],
                    "comparisons_vs_legacy": calibration_report["comparisons_vs_legacy"],
                }
                selected["gate_value_flags"] = _gate_value_flags(selected)
                selected["quality_flags"] = _quality_flags(
                    selected,
                    min_strict_recall=args.min_strict_recall,
                    min_relaxed_recall=args.min_relaxed_recall,
                    min_top_hit_retention=args.min_top_hit_retention,
                )
                selected_microanchors.append(selected)

    skip_positive_count = sum(
        1 for item in selected_microanchors if item["gate_value_flags"]["skip_created"]
    )
    quality_fail_count = sum(
        1 for item in selected_microanchors if not all(item["quality_flags"].values())
    )
    decision_flags = {
        "needs_stronger_gate": skip_positive_count == 0,
        "needs_relaxation": quality_fail_count > 0,
        "ready_for_broader_anchor_sweep": skip_positive_count > 0 and quality_fail_count == 0,
    }

    discovery_report = {
        "compare_output_mode": args.compare_output_mode,
        "prefilter_backend": "prealign_cuda",
        "heavy_anchors": [str(path) for path in heavy_anchors],
        "tile_specs": [dataclasses.asdict(spec) for spec in tile_specs],
        "report_count": len(discovery_candidates),
        "candidates": discovery_candidates,
    }
    _write_json(work_dir / "discovery_report.json", discovery_report)

    summary = {
        "compare_output_mode": args.compare_output_mode,
        "prefilter_backend": "prealign_cuda",
        "heavy_anchors": [str(path) for path in heavy_anchors],
        "tile_specs": [dataclasses.asdict(spec) for spec in tile_specs],
        "discovery_report_count": len(discovery_candidates),
        "selected_microanchors": selected_microanchors,
        "decision_flags": decision_flags,
        "aggregate": {
            "skip_positive_count": skip_positive_count,
            "quality_fail_count": quality_fail_count,
            "selected_microanchor_count": len(selected_microanchors),
        },
    }
    _write_json(work_dir / "summary.json", summary)
    (work_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(work_dir / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
