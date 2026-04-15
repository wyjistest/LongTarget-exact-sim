#!/usr/bin/env python3
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _parse_thread_values(raw_value: str) -> list[int]:
    values: list[int] = []
    for part in raw_value.split(","):
        part = part.strip()
        if not part:
            continue
        parsed = int(part)
        if parsed <= 0:
            raise ValueError(f"thread value must be > 0: {part}")
        if parsed not in values:
            values.append(parsed)
    if not values:
        raise ValueError("at least one thread value is required")
    return values


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_") or "bucket"


def _write_task_list(path: Path, task_keys: list[str]) -> None:
    lines = ["task_key"]
    lines.extend(task_keys)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _expected_tile_filenames(rows: list[dict[str, str]]) -> list[str]:
    return sorted({str(row["tile_filename"]) for row in rows})


def _run_replay(
    *,
    replay_bin: Path,
    corpus_manifest: Path,
    output_dir: Path,
    expected_tile_filenames: list[str],
    extra_args: list[str],
) -> float:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(replay_bin),
        "--corpus-manifest",
        str(corpus_manifest),
        "--output-dir",
        str(output_dir),
    ] + extra_args
    start = time.perf_counter()
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wall_seconds = time.perf_counter() - start
    for tile_filename in expected_tile_filenames:
        output_path = output_dir / tile_filename
        if not output_path.exists():
            raise RuntimeError(f"replay output missing expected tile TSV: {output_path}")
    return wall_seconds


def _render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Task Rerun CPU Bucket Benchmark",
        "",
        f"- corpus_manifest: {summary['corpus_manifest']}",
        f"- shape_summary: {summary['shape_summary']}",
        f"- replay_bin: {summary['replay_bin']}",
        f"- recommended_cpu_bucket_count: {summary['recommended_cpu_bucket_count']}",
        f"- continue_cpu_executor_prototype: {summary['continue_cpu_executor_prototype']}",
        "",
        "## Best CPU Bucket Results",
        "",
    ]
    if not summary["bucket_results"]:
        lines.append("- none")
        lines.append("")
        return "\n".join(lines)

    for bucket in summary["bucket_results"]:
        best = bucket["best_parallel"]
        lines.append(
            f"- {bucket['bucket_family']}:{bucket['bucket_label']}: "
            f"tasks={bucket['task_count']}, isolated={bucket['isolated_serial_wall_seconds']:.6f}s, "
            f"bucket_serial={bucket['bucket_serial_wall_seconds']:.6f}s, "
            f"best_parallel(thread={best['thread_count']})={best['bucket_parallel_wall_seconds']:.6f}s, "
            f"speedup_vs_isolated={best['speedup_vs_isolated_serial']:.3f}, "
            f"speedup_vs_bucket_serial={best['speedup_vs_bucket_serial']:.3f}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark CPU-side bucketed replay executor candidates on a frozen task-rerun corpus.",
    )
    parser.add_argument("--corpus-manifest", required=True, help="task_rerun_corpus_manifest.tsv path")
    parser.add_argument("--shape-summary", required=True, help="shape_audit summary.json path")
    parser.add_argument("--replay-bin", required=True, help="path to exact_sim_task_rerun_replay-compatible binary")
    parser.add_argument("--output-dir", required=True, help="output directory for benchmark summaries and run artifacts")
    parser.add_argument("--thread-values", default="1,2,4,8", help="comma-separated thread counts to try")
    args = parser.parse_args()

    corpus_manifest = Path(args.corpus_manifest).resolve()
    shape_summary = Path(args.shape_summary).resolve()
    replay_bin = Path(args.replay_bin).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    thread_values = _parse_thread_values(args.thread_values)
    manifest_rows = _load_tsv_rows(corpus_manifest)
    manifest_by_task = {str(row["task_key"]): row for row in manifest_rows}
    shape = _load_json(shape_summary)
    recommended_cpu_buckets = list(shape.get("recommended_cpu_buckets", []))

    bucket_results: list[dict[str, object]] = []
    continue_cpu_executor_prototype = False
    runs_root = output_dir / "runs"

    for bucket_index, bucket in enumerate(recommended_cpu_buckets):
        task_keys = list(bucket.get("task_keys", []))
        if not task_keys:
            continue
        bucket_rows = [manifest_by_task[str(task_key)] for task_key in task_keys if str(task_key) in manifest_by_task]
        if not bucket_rows:
            continue

        bucket_family = str(bucket["bucket_family"])
        bucket_label = str(bucket["label"])
        bucket_slug = f"{bucket_index + 1}_{_safe_slug(bucket_family)}_{_safe_slug(bucket_label)}"
        bucket_dir = runs_root / bucket_slug
        bucket_dir.mkdir(parents=True, exist_ok=True)
        expected_tiles = _expected_tile_filenames(bucket_rows)
        task_list_path = bucket_dir / "task_list.tsv"
        _write_task_list(task_list_path, [str(task_key) for task_key in task_keys])

        isolated_serial_wall_seconds = 0.0
        isolated_outputs: list[str] = []
        for task_index, task_key in enumerate(task_keys):
            isolated_output_dir = bucket_dir / f"isolated_{task_index + 1}"
            wall_seconds = _run_replay(
                replay_bin=replay_bin,
                corpus_manifest=corpus_manifest,
                output_dir=isolated_output_dir,
                expected_tile_filenames=_expected_tile_filenames([manifest_by_task[str(task_key)]]),
                extra_args=["--task-key", str(task_key), "--threads", "1"],
            )
            isolated_serial_wall_seconds += wall_seconds
            isolated_outputs.append(str(isolated_output_dir))

        bucket_serial_output_dir = bucket_dir / "bucket_serial"
        bucket_serial_wall_seconds = _run_replay(
            replay_bin=replay_bin,
            corpus_manifest=corpus_manifest,
            output_dir=bucket_serial_output_dir,
            expected_tile_filenames=expected_tiles,
            extra_args=["--task-list-tsv", str(task_list_path), "--threads", "1"],
        )

        parallel_runs: list[dict[str, object]] = []
        for thread_count in sorted(value for value in thread_values if value > 1 and value <= len(task_keys)):
            bucket_parallel_output_dir = bucket_dir / f"bucket_parallel_t{thread_count}"
            bucket_parallel_wall_seconds = _run_replay(
                replay_bin=replay_bin,
                corpus_manifest=corpus_manifest,
                output_dir=bucket_parallel_output_dir,
                expected_tile_filenames=expected_tiles,
                extra_args=["--task-list-tsv", str(task_list_path), "--threads", str(thread_count)],
            )
            parallel_runs.append(
                {
                    "run_kind": "bucket_parallel",
                    "thread_count": thread_count,
                    "bucket_parallel_wall_seconds": bucket_parallel_wall_seconds,
                    "speedup_vs_isolated_serial": 0.0
                    if bucket_parallel_wall_seconds <= 0.0
                    else isolated_serial_wall_seconds / bucket_parallel_wall_seconds,
                    "speedup_vs_bucket_serial": 0.0
                    if bucket_parallel_wall_seconds <= 0.0
                    else bucket_serial_wall_seconds / bucket_parallel_wall_seconds,
                    "bp_per_second": 0.0
                    if bucket_parallel_wall_seconds <= 0.0
                    else float(bucket["rerun_bp_total"]) / bucket_parallel_wall_seconds,
                    "output_dir": str(bucket_parallel_output_dir),
                }
            )

        best_parallel: dict[str, object] | None = None
        if parallel_runs:
            best_parallel = min(parallel_runs, key=lambda item: (float(item["bucket_parallel_wall_seconds"]), int(item["thread_count"])))
            if (
                float(best_parallel["speedup_vs_isolated_serial"]) >= 1.25
                and float(best_parallel["speedup_vs_bucket_serial"]) >= 1.10
            ):
                continue_cpu_executor_prototype = True

        runs: list[dict[str, object]] = [
            {
                "run_kind": "isolated_serial",
                "thread_count": 1,
                "wall_seconds": isolated_serial_wall_seconds,
                "bp_per_second": 0.0
                if isolated_serial_wall_seconds <= 0.0
                else float(bucket["rerun_bp_total"]) / isolated_serial_wall_seconds,
                "output_dirs": isolated_outputs,
            },
            {
                "run_kind": "bucket_serial",
                "thread_count": 1,
                "wall_seconds": bucket_serial_wall_seconds,
                "speedup_vs_isolated_serial": 0.0
                if bucket_serial_wall_seconds <= 0.0
                else isolated_serial_wall_seconds / bucket_serial_wall_seconds,
                "speedup_vs_bucket_serial": 1.0,
                "bp_per_second": 0.0
                if bucket_serial_wall_seconds <= 0.0
                else float(bucket["rerun_bp_total"]) / bucket_serial_wall_seconds,
                "output_dir": str(bucket_serial_output_dir),
            },
        ]
        runs.extend(parallel_runs)

        bucket_results.append(
            {
                "bucket_family": bucket_family,
                "bucket_label": bucket_label,
                "task_count": len(task_keys),
                "task_keys": task_keys,
                "rerun_bp_total": int(bucket["rerun_bp_total"]),
                "isolated_serial_wall_seconds": isolated_serial_wall_seconds,
                "bucket_serial_wall_seconds": bucket_serial_wall_seconds,
                "best_parallel": best_parallel,
                "runs": runs,
            }
        )

    summary = {
        "corpus_manifest": str(corpus_manifest),
        "shape_summary": str(shape_summary),
        "replay_bin": str(replay_bin),
        "thread_values": thread_values,
        "recommended_cpu_bucket_count": len(recommended_cpu_buckets),
        "continue_cpu_executor_prototype": continue_cpu_executor_prototype,
        "bucket_results": bucket_results,
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
