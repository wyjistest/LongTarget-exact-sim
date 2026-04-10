#!/usr/bin/env python3
import argparse
import dataclasses
import json
import os
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


def _parse_metrics(stderr_path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("benchmark.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        metrics[key[len("benchmark."):]] = value
    return metrics


def _metric_str(metrics: dict[str, str], key: str, *, default: str = "") -> str:
    value = metrics.get(key)
    return default if value is None or value == "" else value


def _metric_int(metrics: dict[str, str], key: str, *, default: int = 0) -> int:
    value = metrics.get(key)
    return default if value is None or value == "" else int(value)


def _metric_float(metrics: dict[str, str], key: str, *, default: float = 0.0) -> float:
    value = metrics.get(key)
    return default if value is None or value == "" else float(value)


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


def _discovery_payload_from_metrics(metrics: dict[str, str]) -> dict[str, object]:
    return {
        "mode": _metric_str(metrics, "two_stage_discovery_mode", default="off"),
        "status": _metric_str(metrics, "two_stage_discovery_status", default="hard_failed"),
        "prefilter_backend": _metric_str(metrics, "prefilter_backend", default="disabled"),
        "prefilter_hits": _metric_int(metrics, "prefilter_hits"),
        "task_count": _metric_int(metrics, "two_stage_discovery_task_count"),
        "prefilter_failed_tasks": _metric_int(metrics, "two_stage_discovery_prefilter_failed_tasks"),
        "tasks_with_any_seed": _metric_int(metrics, "two_stage_tasks_with_any_seed"),
        "tasks_with_any_refine_window_before_gate": _metric_int(
            metrics, "two_stage_tasks_with_any_refine_window_before_gate"
        ),
        "tasks_with_any_refine_window_after_gate": _metric_int(
            metrics, "two_stage_tasks_with_any_refine_window_after_gate"
        ),
        "windows_before_gate": _metric_int(metrics, "two_stage_windows_before_gate"),
        "windows_after_gate": _metric_int(metrics, "two_stage_windows_after_gate"),
        "predicted_skip": _metric_int(metrics, "two_stage_discovery_predicted_skip") != 0,
        "predicted_skip_tasks": _metric_int(metrics, "two_stage_discovery_predicted_skip_tasks"),
        "prefilter_only_seconds": _metric_float(metrics, "two_stage_discovery_prefilter_only_seconds"),
        "gate_seconds": _metric_float(metrics, "two_stage_discovery_gate_seconds"),
        "total_seconds": _metric_float(metrics, "total_seconds"),
    }


def _fallback_discovery_payload(status: str) -> dict[str, object]:
    return {
        "mode": "prefilter_only",
        "status": status,
        "prefilter_backend": "prealign_cuda",
        "prefilter_hits": 0,
        "task_count": 0,
        "prefilter_failed_tasks": 0,
        "tasks_with_any_seed": 0,
        "tasks_with_any_refine_window_before_gate": 0,
        "tasks_with_any_refine_window_after_gate": 0,
        "windows_before_gate": 0,
        "windows_after_gate": 0,
        "predicted_skip": False,
        "predicted_skip_tasks": 0,
        "prefilter_only_seconds": 0.0,
        "gate_seconds": 0.0,
        "total_seconds": 0.0,
    }


def _run_discovery_mode(
    *,
    dna_path: Path,
    args: argparse.Namespace,
    work_dir: Path,
) -> dict[str, object]:
    work_dir.mkdir(parents=True, exist_ok=True)
    stderr_path = work_dir / "stderr.log"
    stdout_path = work_dir / "stdout.log"
    discovery_path = work_dir / "discovery.json"
    out_dir = work_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(args.longtarget),
        "-f1",
        str(dna_path),
        "-f2",
        str(args.rna),
        "-r",
        str(args.rule),
        "-O",
        str(out_dir),
    ]
    if args.strand:
        cmd += ["-t", args.strand]

    env = dict(os.environ)
    env.update(
        {
            "LONGTARGET_ENABLE_CUDA": "1",
            "LONGTARGET_BENCHMARK": "1",
            "LONGTARGET_OUTPUT_MODE": args.compare_output_mode,
            "LONGTARGET_TWO_STAGE": "1",
            "LONGTARGET_TWO_STAGE_THRESHOLD_MODE": "deferred_exact",
            "LONGTARGET_TWO_STAGE_DISCOVERY_MODE": "prefilter_only",
            "LONGTARGET_TWO_STAGE_REJECT_MODE": args.discovery_reject_mode,
            "LONGTARGET_TWO_STAGE_MIN_PEAK_SCORE": str(args.min_peak_score),
            "LONGTARGET_TWO_STAGE_MIN_SUPPORT": str(args.min_support),
            "LONGTARGET_TWO_STAGE_MIN_MARGIN": str(args.min_margin),
            "LONGTARGET_TWO_STAGE_STRONG_SCORE_OVERRIDE": str(args.strong_score_override),
            "LONGTARGET_TWO_STAGE_MAX_WINDOWS_PER_TASK": str(args.max_windows_per_task),
            "LONGTARGET_TWO_STAGE_MAX_BP_PER_TASK": str(args.max_bp_per_task),
            "LONGTARGET_PREFILTER_BACKEND": "prealign_cuda",
            "LONGTARGET_PREFILTER_TOPK": str(args.prefilter_topk),
            "LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP": str(args.peak_suppress_bp),
            "LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA": str(args.score_floor_delta),
            "LONGTARGET_REFINE_PAD_BP": str(args.refine_pad_bp),
            "LONGTARGET_REFINE_MERGE_GAP_BP": str(args.refine_merge_gap_bp),
        }
    )

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        stderr_text = proc.stderr.lower()
        status = "unsupported" if "requires " in stderr_text or "support in this build" in stderr_text else "hard_failed"
        payload = _fallback_discovery_payload(status)
    else:
        metrics = _parse_metrics(stderr_path)
        payload = _discovery_payload_from_metrics(metrics)
        if payload["mode"] != "prefilter_only":
            payload = _fallback_discovery_payload("hard_failed")
        status = str(payload["status"])

    discovery_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "status": status,
        "discovery": payload,
        "discovery_report_path": str(discovery_path),
        "discovery_stderr_path": str(stderr_path),
        "discovery_stdout_path": str(stdout_path),
    }


def _candidate_rank_key(candidate: dict[str, object]) -> tuple[object, ...]:
    discovery = candidate["discovery"]
    return (
        -int(bool(discovery["predicted_skip"])),
        -(int(discovery["windows_before_gate"]) - int(discovery["windows_after_gate"])),
        -int(discovery["windows_before_gate"]),
        -int(discovery["prefilter_hits"]),
        candidate["start_bp"],
    )


def _bisect_lengths(length_bp: int) -> list[int]:
    left = length_bp // 2
    right = length_bp - left
    return [part for part in (left, right) if part > 0]


def _candidate_shrink_delta(candidate: dict[str, object]) -> int:
    discovery = candidate["discovery"]
    return int(discovery["windows_before_gate"]) - int(discovery["windows_after_gate"])


def _select_bucket_candidates(matching: list[dict[str, object]]) -> list[tuple[str, dict[str, object]]]:
    if not matching:
        return []
    selected: list[tuple[str, dict[str, object]]] = [("strongest_shrink", matching[0])]
    used = {str(matching[0]["shard_path"])}

    shrink_positive = [
        candidate
        for candidate in matching
        if _candidate_shrink_delta(candidate) > 0 and str(candidate["shard_path"]) not in used
    ]
    medium_candidate = shrink_positive[len(shrink_positive) // 2] if shrink_positive else None
    if medium_candidate is None or str(medium_candidate["shard_path"]) in used:
        medium_candidate = next(
            (candidate for candidate in matching if str(candidate["shard_path"]) not in used),
            None,
        )
    if medium_candidate is not None and str(medium_candidate["shard_path"]) not in used:
        selected.append(("medium_shrink", medium_candidate))
    return selected


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _gate_value_flags(item: dict[str, object], *, gated_run_label: str) -> dict[str, bool]:
    deferred = item["runs"]["deferred_exact"]
    gated = item["runs"][gated_run_label]
    return {
        "skip_created": int(gated["threshold_skipped_after_gate"]) > 0,
        "threshold_work_reduced": int(gated["threshold_invoked"]) < int(deferred["threshold_invoked"]),
        "window_work_reduced": int(gated["windows_after_gate"]) < int(gated["windows_before_gate"]),
        "refine_bp_reduced": int(gated["refine_total_bp"]) < int(deferred["refine_total_bp"]),
    }


def _quality_flags(
    item: dict[str, object],
    *,
    gated_run_label: str,
    min_strict_recall: float,
    min_relaxed_recall: float,
    min_top_hit_retention: float,
) -> dict[str, bool]:
    comparison = item["comparisons_vs_legacy"][gated_run_label]
    return {
        "strict_recall_ok": float(comparison["strict"]["recall"]) >= min_strict_recall,
        "relaxed_recall_ok": float(comparison["relaxed"]["recall"]) >= min_relaxed_recall,
        "top_hit_retention_ok": float(comparison["top_hit_retention"]) >= min_top_hit_retention,
    }


def _aggregate_selected_microanchors(
    selected_microanchors: list[dict[str, object]],
    *,
    gated_run_label: str,
    quality_fail_count: int,
) -> dict[str, object]:
    if not selected_microanchors:
        return {
            "skip_positive_count": 0,
            "quality_fail_count": quality_fail_count,
            "selected_microanchor_count": 0,
            "top_hit_preserved_count": 0,
            "mean_strict_recall": 0.0,
            "min_strict_recall": 0.0,
            "mean_relaxed_recall": 0.0,
            "min_relaxed_recall": 0.0,
            "mean_top_hit_retention": 0.0,
            "min_top_hit_retention": 0.0,
            "mean_top5_retention": 0.0,
            "min_top5_retention": 0.0,
            "mean_top10_retention": 0.0,
            "min_top10_retention": 0.0,
            "mean_score_weighted_recall": 0.0,
            "min_score_weighted_recall": 0.0,
            "mean_threshold_batch_size_mean": 0.0,
            "min_threshold_batch_size_mean": 0.0,
            "mean_threshold_skipped_after_gate": 0.0,
            "min_threshold_skipped_after_gate": 0.0,
        }

    strict_recall = []
    relaxed_recall = []
    top_hit_retention = []
    top5_retention = []
    top10_retention = []
    score_weighted_recall = []
    threshold_batch_size_mean = []
    threshold_skipped_after_gate = []
    skip_positive_count = 0
    top_hit_preserved_count = 0

    for item in selected_microanchors:
        comparison = item["comparisons_vs_legacy"][gated_run_label]
        run = item["runs"][gated_run_label]
        strict_recall.append(float(comparison["strict"]["recall"]))
        relaxed_recall.append(float(comparison["relaxed"]["recall"]))
        top_hit_retention.append(float(comparison["top_hit_retention"]))
        top5_retention.append(float(comparison["top5_retention"]))
        top10_retention.append(float(comparison["top10_retention"]))
        score_weighted_recall.append(float(comparison["score_weighted_recall"]))
        threshold_batch_size_mean.append(float(run["threshold_batch_size_mean"]))
        threshold_skipped_after_gate.append(float(run["threshold_skipped_after_gate"]))
        if int(run["threshold_skipped_after_gate"]) > 0:
            skip_positive_count += 1
        if float(comparison["top_hit_retention"]) >= 1.0:
            top_hit_preserved_count += 1

    return {
        "skip_positive_count": skip_positive_count,
        "quality_fail_count": quality_fail_count,
        "selected_microanchor_count": len(selected_microanchors),
        "top_hit_preserved_count": top_hit_preserved_count,
        "mean_strict_recall": _mean(strict_recall),
        "min_strict_recall": min(strict_recall),
        "mean_relaxed_recall": _mean(relaxed_recall),
        "min_relaxed_recall": min(relaxed_recall),
        "mean_top_hit_retention": _mean(top_hit_retention),
        "min_top_hit_retention": min(top_hit_retention),
        "mean_top5_retention": _mean(top5_retention),
        "min_top5_retention": min(top5_retention),
        "mean_top10_retention": _mean(top10_retention),
        "min_top10_retention": min(top10_retention),
        "mean_score_weighted_recall": _mean(score_weighted_recall),
        "min_score_weighted_recall": min(score_weighted_recall),
        "mean_threshold_batch_size_mean": _mean(threshold_batch_size_mean),
        "min_threshold_batch_size_mean": min(threshold_batch_size_mean),
        "mean_threshold_skipped_after_gate": _mean(threshold_skipped_after_gate),
        "min_threshold_skipped_after_gate": min(threshold_skipped_after_gate),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_summary_markdown(summary: dict[str, object]) -> str:
    gated_run_label = str(summary["gated_run_label"])
    aggregate = summary["aggregate"]
    lines = [
        "# Two-Stage Threshold Heavy Micro-Anchor Summary",
        "",
        f"- selected_microanchors: {len(summary['selected_microanchors'])}",
        f"- discovery_reports: {summary['discovery_report_count']}",
        f"- gated_run_label: {gated_run_label}",
        f"- discovery_reject_mode: {summary['discovery_reject_mode']}",
        f"- needs_stronger_gate: {summary['decision_flags']['needs_stronger_gate']}",
        f"- needs_relaxation: {summary['decision_flags']['needs_relaxation']}",
        f"- ready_for_broader_anchor_sweep: {summary['decision_flags']['ready_for_broader_anchor_sweep']}",
        f"- mean_top5_retention: {aggregate['mean_top5_retention']:.6f}",
        f"- mean_top10_retention: {aggregate['mean_top10_retention']:.6f}",
        f"- mean_score_weighted_recall: {aggregate['mean_score_weighted_recall']:.6f}",
        "",
        "| anchor | bucket_length_bp | length_bp | selection_kind | selection_rank | start_bp | end_bp | skip_after_gate | strict_recall | relaxed_recall | top_hit_retention | top5_retention | top10_retention | score_weighted_recall | difference_class |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in summary["selected_microanchors"]:
        comparison = item["comparisons_vs_legacy"][gated_run_label]
        run = item["runs"][gated_run_label]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["anchor_label"]),
                    str(item["selection_bucket_length_bp"]),
                    str(item["length_bp"]),
                    str(item["selection_kind"]),
                    str(item["selection_rank"]),
                    str(item["start_bp"]),
                    str(item["end_bp"]),
                    str(run["threshold_skipped_after_gate"]),
                    f"{float(comparison['strict']['recall']):.6f}",
                    f"{float(comparison['relaxed']['recall']):.6f}",
                    f"{float(comparison['top_hit_retention']):.6f}",
                    f"{float(comparison['top5_retention']):.6f}",
                    f"{float(comparison['top10_retention']):.6f}",
                    f"{float(comparison['score_weighted_recall']):.6f}",
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
    parser.add_argument(
        "--gated-run-label",
        default="deferred_exact_minimal_v2",
        help="threshold-mode run label used for gated calibration and reporting",
    )
    parser.add_argument(
        "--discovery-reject-mode",
        default="minimal_v2",
        help="reject mode used during prefilter-only discovery",
    )
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
    selection_target_count = 2

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
                candidate = {
                    "anchor_label": anchor_label,
                    "anchor_path": str(anchor_path),
                    "length_bp": tile_spec.length_bp,
                    "selection_bucket_length_bp": tile_spec.length_bp,
                    "stride_bp": tile_spec.stride_bp,
                    "select_count": tile_spec.select_count,
                    "start_bp": start_bp,
                    "end_bp": end_bp,
                    "shard_path": str(shard_path),
                    "bisect_depth": 0,
                }
                candidate.update(
                    _run_discovery_mode(
                        dna_path=shard_path,
                        args=args,
                        work_dir=run_dir,
                    )
                )
                discovery_candidates.append(candidate)

                if candidate["status"] != "prefilter_failed":
                    continue

                child_lengths = _bisect_lengths(tile_spec.length_bp)
                if len(child_lengths) != 2:
                    candidate["status"] = "hard_failed"
                    candidate["discovery"]["status"] = "hard_failed"
                    Path(candidate["discovery_report_path"]).write_text(
                        json.dumps(candidate["discovery"], indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    continue

                child_starts = [start_bp, start_bp + child_lengths[0]]
                child_statuses: list[str] = []
                for child_index, (child_start_bp, child_length_bp) in enumerate(zip(child_starts, child_lengths), start=1):
                    child_shard_dir = run_dir / "bisect_shards" / f"child_{child_index}"
                    child_shard_path = _make_anchor_shards(
                        anchor_path,
                        child_shard_dir,
                        [child_start_bp],
                        child_length_bp,
                    )[0]
                    child_end_bp = child_start_bp + child_length_bp - 1
                    child_run_dir = run_dir / "bisect_runs" / f"{child_start_bp}_{child_length_bp}"
                    child_candidate = {
                        "anchor_label": anchor_label,
                        "anchor_path": str(anchor_path),
                        "length_bp": child_length_bp,
                        "selection_bucket_length_bp": tile_spec.length_bp,
                        "stride_bp": tile_spec.stride_bp,
                        "select_count": tile_spec.select_count,
                        "start_bp": child_start_bp,
                        "end_bp": child_end_bp,
                        "shard_path": str(child_shard_path),
                        "bisect_depth": 1,
                        "bisect_parent_start_bp": start_bp,
                        "bisect_parent_length_bp": tile_spec.length_bp,
                    }
                    child_candidate.update(
                        _run_discovery_mode(
                            dna_path=child_shard_path,
                            args=args,
                            work_dir=child_run_dir,
                        )
                    )
                    discovery_candidates.append(child_candidate)
                    child_statuses.append(str(child_candidate["status"]))

                if child_statuses and all(status in {"prefilter_failed", "hard_failed", "unsupported"} for status in child_statuses):
                    candidate["status"] = "hard_failed"
                    candidate["discovery"]["status"] = "hard_failed"
                    Path(candidate["discovery_report_path"]).write_text(
                        json.dumps(candidate["discovery"], indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )

    selected_microanchors: list[dict[str, object]] = []
    selection_shortfalls: list[dict[str, object]] = []
    for anchor_path in heavy_anchors:
        anchor_label = _safe_label(anchor_path)
        for tile_spec in tile_specs:
            matching = sorted(
                [
                    candidate
                    for candidate in discovery_candidates
                    if candidate["status"] == "ok"
                    and candidate["anchor_label"] == anchor_label
                    and candidate["selection_bucket_length_bp"] == tile_spec.length_bp
                ],
                key=_candidate_rank_key,
            )
            bucket_selection = _select_bucket_candidates(matching)
            if len(bucket_selection) < selection_target_count:
                selection_shortfalls.append(
                    {
                        "anchor_label": anchor_label,
                        "selection_bucket_length_bp": tile_spec.length_bp,
                        "stride_bp": tile_spec.stride_bp,
                        "requested_count": selection_target_count,
                        "selected_count": len(bucket_selection),
                        "available_count": len(matching),
                    }
                )
            run_labels = ["legacy", "deferred_exact"]
            if args.gated_run_label not in run_labels:
                run_labels.append(args.gated_run_label)
            for rank, (selection_kind, candidate) in enumerate(bucket_selection, start=1):
                calibration_dir = (
                    work_dir
                    / "calibration"
                    / anchor_label
                    / f"{tile_spec.length_bp}bp_stride_{tile_spec.stride_bp}"
                    / f"{anchor_label}_{candidate['start_bp']}_{candidate['length_bp']}"
                )
                calibration_report_path, calibration_report = _run_threshold_modes(
                    dna_path=Path(candidate["shard_path"]),
                    args=args,
                    work_dir=calibration_dir,
                    run_labels=run_labels,
                )
                selected = {
                    **candidate,
                    "selection_kind": selection_kind,
                    "selection_rank": rank,
                    "discovery_report_path": candidate["discovery_report_path"],
                    "report_path": str(calibration_report_path),
                    "runs": calibration_report["runs"],
                    "comparisons_vs_legacy": calibration_report["comparisons_vs_legacy"],
                }
                selected["gate_value_flags"] = _gate_value_flags(
                    selected,
                    gated_run_label=args.gated_run_label,
                )
                selected["quality_flags"] = _quality_flags(
                    selected,
                    gated_run_label=args.gated_run_label,
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
    aggregate = _aggregate_selected_microanchors(
        selected_microanchors,
        gated_run_label=args.gated_run_label,
        quality_fail_count=quality_fail_count,
    )
    decision_flags = {
        "needs_stronger_gate": skip_positive_count == 0,
        "needs_relaxation": quality_fail_count > 0,
        "ready_for_broader_anchor_sweep": skip_positive_count > 0 and quality_fail_count == 0,
    }
    status_counts: dict[str, int] = {}
    for candidate in discovery_candidates:
        status = str(candidate["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    discovery_report = {
        "compare_output_mode": args.compare_output_mode,
        "prefilter_backend": "prealign_cuda",
        "discovery_mode": "prefilter_only",
        "discovery_reject_mode": args.discovery_reject_mode,
        "heavy_anchors": [str(path) for path in heavy_anchors],
        "tile_specs": [dataclasses.asdict(spec) for spec in tile_specs],
        "report_count": len(discovery_candidates),
        "status_counts": status_counts,
        "candidates": discovery_candidates,
    }
    _write_json(work_dir / "discovery_report.json", discovery_report)

    summary = {
        "compare_output_mode": args.compare_output_mode,
        "prefilter_backend": "prealign_cuda",
        "gated_run_label": args.gated_run_label,
        "discovery_reject_mode": args.discovery_reject_mode,
        "heavy_anchors": [str(path) for path in heavy_anchors],
        "tile_specs": [dataclasses.asdict(spec) for spec in tile_specs],
        "discovery_report_count": len(discovery_candidates),
        "selected_microanchors": selected_microanchors,
        "selection_shortfalls": selection_shortfalls,
        "decision_flags": decision_flags,
        "aggregate": aggregate,
    }
    _write_json(work_dir / "summary.json", summary)
    (work_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(work_dir / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
