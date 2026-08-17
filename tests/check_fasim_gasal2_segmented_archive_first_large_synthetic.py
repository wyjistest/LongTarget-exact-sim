#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts" / "merge_fasim_segmented_tfosorted.py"
TFOSORTED_COLUMNS = [
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "MeanStability",
    "MeanIdentity(%)",
    "Strand",
    "Rule",
    "Score",
    "Nt(bp)",
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
]


def metrics(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_input(path: Path, row_count: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(TFOSORTED_COLUMNS)
        for index in range(row_count):
            query_start = index + 1
            query_end = query_start + 3
            midpoint = query_start + 1
            target_start = index * 5 + 1
            writer.writerow(
                [
                    query_start,
                    query_end,
                    target_start,
                    target_start + 3,
                    "R",
                    "chrSynthetic",
                    target_start,
                    target_start + 3,
                    "1.5",
                    "75",
                    "ParaPlus",
                    0,
                    index,
                    4,
                    0,
                    midpoint,
                    midpoint,
                    "ACGT",
                    "TGCA",
                ]
            )


def run_merge(work: Path, manifest: Path, backend: str) -> tuple[dict[str, str], Path, float]:
    output = work / f"{backend}-merged.tsv"
    command = [
        sys.executable,
        str(MERGE),
        "--segments",
        str(manifest),
        "--output",
        str(output),
        "--dedup-backend",
        backend,
    ]
    if backend == "sqlite":
        command.extend(["--dedup-db", str(work / "sqlite-dedup.sqlite")])
    start = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return metrics(result.stdout), output, time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=150000)
    parser.add_argument("--min-rss-reduction-kb", type=int, default=8192)
    parser.add_argument("--min-rss-reduction-fraction", type=float, default=0.10)
    args = parser.parse_args()
    if args.rows < 10000:
        parser.error("--rows must be at least 10000 for a meaningful memory gate")

    args.work.mkdir(parents=True, exist_ok=True)
    source = args.work / "large-TFOsorted"
    write_input(source, args.rows)
    manifest = args.work / "segments.tsv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            ["segment_id", "global_start", "global_end", "artifact_kind", "artifact_path"]
        )
        writer.writerow([0, 0, args.rows + 10, "tfosorted", source])

    memory, memory_output, memory_process_wall = run_merge(args.work, manifest, "memory")
    sqlite, sqlite_output, sqlite_process_wall = run_merge(args.work, manifest, "sqlite")
    memory_rss = int(memory["peak_rss_kb"])
    sqlite_rss = int(sqlite["peak_rss_kb"])
    rss_reduction = memory_rss - sqlite_rss
    rss_reduction_fraction = rss_reduction / memory_rss
    outputs_equal = digest(memory_output) == digest(sqlite_output)
    row_counts_equal = memory["output_rows"] == sqlite["output_rows"] == str(args.rows)
    bounded_memory_backend_active = sqlite["dedup_backend"] == "sqlite"
    rss_gate = (
        rss_reduction >= args.min_rss_reduction_kb
        and rss_reduction_fraction >= args.min_rss_reduction_fraction
    )

    summary = {
        "large_synthetic_rows": str(args.rows),
        "large_synthetic_input_bytes": str(source.stat().st_size),
        "large_synthetic_outputs_byte_identical": "1" if outputs_equal else "0",
        "large_synthetic_row_counts_equal": "1" if row_counts_equal else "0",
        "memory_peak_rss_kb": str(memory_rss),
        "sqlite_peak_rss_kb": str(sqlite_rss),
        "peak_rss_reduction_kb": str(rss_reduction),
        "peak_rss_reduction_fraction": f"{rss_reduction_fraction:.6f}",
        "memory_process_wall_seconds": f"{memory_process_wall:.6f}",
        "sqlite_process_wall_seconds": f"{sqlite_process_wall:.6f}",
        "memory_merge_wall_seconds": memory["merge_wall_seconds"],
        "sqlite_merge_wall_seconds": sqlite["merge_wall_seconds"],
        "bounded_memory_backend_active": "1" if bounded_memory_backend_active else "0",
        "peak_rss_materially_below_memory": "1" if rss_gate else "0",
        "decision": "pass" if outputs_equal and row_counts_equal and bounded_memory_backend_active and rss_gate else "fail",
    }
    summary_path = args.work / "summary.txt"
    summary_path.write_text(
        "".join(f"{key}={value}\n" for key, value in summary.items()),
        encoding="utf-8",
    )
    print(summary_path.read_text(encoding="utf-8"), end="")
    return 0 if summary["decision"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
