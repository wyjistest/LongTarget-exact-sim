#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Tuple


ROOT = Path(__file__).resolve().parent.parent


TIMING_RE = re.compile(r"TIMING:\s+([0-9.]+)\s+ms\s+([0-9.]+)\s+GCUPS\s+\(([^)]+)\)")


def run_example(binary: Path, args: List[str]) -> str:
    if not binary.exists():
        raise RuntimeError(f"missing Accelign example binary: {binary}")
    result = subprocess.run(
        [str(binary)] + args,
        cwd=str(binary.parent),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout


def parse_timings(output: str) -> List[Tuple[str, str, float, float]]:
    rows: List[Tuple[str, str, float, float]] = []
    precision = "unknown"
    for line in output.splitlines():
        stripped = line.strip()
        if stripped in {"float:", "half2:"}:
            precision = stripped[:-1]
            continue
        match = TIMING_RE.search(line)
        if match:
            rows.append((precision, match.group(3), float(match.group(1)), float(match.group(2))))
    if not rows:
        raise RuntimeError(f"no timing rows parsed from output:\n{output}")
    return rows


def speedup(cpu_seconds: float, gpu_ms: float) -> float:
    gpu_seconds = gpu_ms / 1000.0
    return cpu_seconds / gpu_seconds if gpu_seconds > 0.0 else 0.0


def append_table(lines: List[str], headers: List[str], rows: List[List[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--accelign-dir",
        default=str(ROOT / ".tmp" / "accelign_12_5_test" / "Accelign"),
    )
    parser.add_argument("--cpu-50k-seconds", type=float, default=2.2525)
    parser.add_argument("--output", default=str(ROOT / "docs" / "fasim_accelign_shape_benchmark.md"))
    args = parser.parse_args()

    accelign_dir = Path(args.accelign_dir).resolve()
    high_level = accelign_dir / "examples" / "high-level"
    score_binary = high_level / "oneToOneScoreOnly"
    endpoint_binary = high_level / "oneToOneStartEndPos"

    cases = [
        (
            "fixed_50k_avg_shape",
            ["50000", "67", "2812", "--randomSeqs"],
            "50k alignments, target=67, query=2812",
        ),
        (
            "random_100k_max_shape",
            ["100000", "190", "2812", "--randomSeqs", "--randomLengths"],
            "100k alignments, target<=190, query<=2812, random lengths",
        ),
    ]

    lines: List[str] = []
    lines.append("# Fasim Accelign Shape Benchmark")
    lines.append("")
    lines.append(
        "This report benchmarks standalone Accelign examples on Fasim-like "
        "`aligner.Align` request shapes. It does not integrate Accelign into "
        "Fasim, does not change runtime output, and does not use Accelign "
        "results for scoring, thresholds, non-overlap, CIGAR, alignment strings, "
        "SIM-close, or recovery behavior."
    )
    lines.append("")
    lines.append("## Reference")
    lines.append("")
    lines.append("```text")
    lines.append("Fasim hg38_chr21_H19 aligner.Align shape:")
    lines.append("  align calls = 979,282")
    lines.append("  avg query len = 2812")
    lines.append("  avg target len = 67.38")
    lines.append("  max target len = 190")
    lines.append("  CPU reference for 50k sampled requests = 2.252500s")
    lines.append("```")
    lines.append("")

    smoke_args = ["1000", "67", "2812", "--randomSeqs", "--checkResults"]
    smoke_output = run_example(score_binary, smoke_args)

    benchmark_rows: List[List[str]] = []
    raw_lines: List[str] = []
    for label, run_args, notes in cases:
        score_output = run_example(score_binary, run_args)
        endpoint_output = run_example(endpoint_binary, run_args)
        raw_lines.append(f"### {label} score-only")
        raw_lines.append("```text")
        raw_lines.append(score_output.strip())
        raw_lines.append("```")
        raw_lines.append("")
        raw_lines.append(f"### {label} endpoints")
        raw_lines.append("```text")
        raw_lines.append(endpoint_output.strip())
        raw_lines.append("```")
        raw_lines.append("")

        for precision, component, milliseconds, gcups in parse_timings(score_output):
            benchmark_rows.append(
                [
                    label,
                    "score-only",
                    precision,
                    component,
                    f"{milliseconds:.6f}",
                    f"{gcups:.2f}",
                    f"{speedup(args.cpu_50k_seconds, milliseconds):.2f}x",
                    notes,
                ]
            )
        for precision, component, milliseconds, gcups in parse_timings(endpoint_output):
            benchmark_rows.append(
                [
                    label,
                    "score+endpoint",
                    precision,
                    component,
                    f"{milliseconds:.6f}",
                    f"{gcups:.2f}",
                    f"{speedup(args.cpu_50k_seconds, milliseconds):.2f}x",
                    notes,
                ]
            )

    lines.append("## Results")
    lines.append("")
    lines.append(
        "The speedup column is a kernel-level reference ratio against the "
        "previously measured 50k CPU `aligner.Align` sample. It is not an "
        "apples-to-apples Fasim end-to-end speedup, especially for the 100k "
        "random-length case."
    )
    lines.append("")
    lines.append(
        "For exact Fasim shadow work, treat the float path as the candidate path. "
        "The CUDA 12.5 smoke check reports `gpu scores ok` for float but score "
        "errors for the high-level `half2` path, so `half2` is not considered "
        "correctness-ready here."
    )
    lines.append("")
    append_table(
        lines,
        [
            "Case",
            "Mode",
            "Precision",
            "Component",
            "Milliseconds",
            "GCUPS",
            "Speedup vs 50k CPU reference",
            "Notes",
        ],
        benchmark_rows,
    )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(
        "Accelign float shows a strong standalone kernel-level speed signal on "
        "Fasim-like short-target, long-query request shapes. The next step is a "
        "default-off Fasim shadow that compares score and endpoints against CPU "
        "`aligner.Align`; Accelign must not feed runtime output until "
        "score/endpoints are mismatch-free and staging overhead is measured."
    )
    lines.append("")
    lines.append("## Boundaries")
    lines.append("")
    lines.append("```text")
    lines.append("Accelign integrated into Fasim runtime: no")
    lines.append("use Accelign result for output: no")
    lines.append("CIGAR/alignment-string support: no")
    lines.append("half2 exactness-ready on CUDA 12.5 smoke check: no")
    lines.append("scoring/threshold/non-overlap change: no")
    lines.append("SIM-close/recovery change: no")
    lines.append("```")
    lines.append("")
    lines.append("## CUDA 12.5 Smoke Check")
    lines.append("")
    lines.append("```text")
    lines.append(smoke_output.strip())
    lines.append("```")
    lines.append("")
    lines.append("## Raw Output")
    lines.append("")
    lines.extend(raw_lines)
    while lines and lines[-1] == "":
        lines.pop()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
