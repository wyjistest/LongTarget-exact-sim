#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


METRICS = {
    "fasta_read_seconds": "benchmark.fasim_top5_gasal2_phase_fasta_read_seconds",
    "cut_sequence_seconds": "benchmark.fasim_top5_gasal2_phase_cut_sequence_seconds",
    "transfer_string_seconds": "benchmark.fasim_top5_gasal2_phase_transfer_string_seconds",
    "transfer_table_seconds": "benchmark.fasim_top5_gasal2_phase_transfer_table_seconds",
    "src_transform_seconds": "benchmark.fasim_top5_gasal2_phase_src_transform_seconds",
    "encode_seconds": "benchmark.fasim_top5_gasal2_phase_encode_seconds",
    "cuda_query_init_seconds": "benchmark.fasim_top5_gasal2_phase_cuda_query_init_seconds",
    "flush_total_seconds": "benchmark.fasim_top5_gasal2_phase_flush_total_seconds",
    "gasal2_init_seconds": "benchmark.fasim_gasal2_init_seconds",
    "gasal2_fill_seconds": "benchmark.fasim_gasal2_fill_seconds",
    "score_target_bytes": "benchmark.fasim_gasal2_score_target_bytes",
    "traceback_target_bytes": "benchmark.fasim_gasal2_traceback_target_bytes",
    "score_requests": "benchmark.fasim_gasal2_score_requests",
    "traceback_requests": "benchmark.fasim_gasal2_traceback_requests",
    "fallbacks": "benchmark.fasim_gasal2_fallbacks",
}

INTEGER_METRICS = {
    "score_target_bytes",
    "traceback_target_bytes",
    "score_requests",
    "traceback_requests",
    "fallbacks",
}

HOST_SETUP_COMPONENTS = (
    "fasta_read_seconds",
    "cut_sequence_seconds",
    "transfer_string_seconds",
    "src_transform_seconds",
    "encode_seconds",
    "cuda_query_init_seconds",
)


class ProfileError(ValueError):
    pass


def parse_log(path: Path) -> dict[str, str]:
    raw: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            raw[key] = value
    result: dict[str, str] = {}
    for short_name, full_name in METRICS.items():
        if full_name not in raw:
            raise ProfileError(f"missing required metric {short_name} ({full_name}) in {path}")
        result[short_name] = raw[full_name]
    return result


def number(value: str, name: str, source: Path) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ProfileError(f"invalid {name}={value!r} in {source}") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ProfileError(f"invalid non-negative {name}={value!r} in {source}")
    return parsed


def integer(value: str, name: str, source: Path) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ProfileError(f"invalid integer {name}={value!r} in {source}") from exc
    if parsed < 0:
        raise ProfileError(f"invalid non-negative {name}={value!r} in {source}")
    return parsed


def read_wall(path: Path) -> float:
    if not path.is_file():
        raise ProfileError(f"missing wall receipt: {path}")
    values = path.read_text(encoding="utf-8").split()
    if len(values) != 1:
        raise ProfileError(f"wall receipt must contain one value: {path}")
    return number(values[0], "wall_seconds", path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate repeated setup and GASAL2 target-batch costs across segment processes."
    )
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--details", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    logs = sorted(args.run_root.glob("run_*/stderr.log"))
    if not logs:
        parser.error(f"no run_*/stderr.log files under {args.run_root}")

    rows: list[dict[str, float | int | str]] = []
    for log in logs:
        parsed = parse_log(log)
        row: dict[str, float | int | str] = {"run": log.parent.name}
        row["wall_seconds"] = read_wall(log.parent / "wall_seconds.txt")
        for name, value in parsed.items():
            row[name] = integer(value, name, log) if name in INTEGER_METRICS else number(value, name, log)
        rows.append(row)

    def total(name: str) -> float:
        return sum(float(row[name]) for row in rows)

    def total_int(name: str) -> int:
        return sum(int(row[name]) for row in rows)

    wall_seconds = total("wall_seconds")
    flush_seconds = total("flush_total_seconds")
    nonflush_seconds = max(0.0, wall_seconds - flush_seconds)
    host_setup_seconds = sum(total(name) for name in HOST_SETUP_COMPONENTS)
    score_requests = [int(row["score_requests"]) for row in rows]
    traceback_requests = [int(row["traceback_requests"]) for row in rows]
    target_batch_bytes = total_int("score_target_bytes") + total_int("traceback_target_bytes")
    query_dependent = len(set(score_requests)) > 1 or len(set(traceback_requests)) > 1

    summary: dict[str, str | int] = {
        "segments": len(rows),
        "processes": len(rows),
        "target_read_passes": len(rows),
        "wall_seconds": f"{wall_seconds:.6f}",
        "flush_total_seconds": f"{flush_seconds:.6f}",
        "nonflush_wall_seconds": f"{nonflush_seconds:.6f}",
        "nonflush_wall_percent": f"{100.0 * nonflush_seconds / wall_seconds:.2f}" if wall_seconds else "0.00",
        "host_setup_observed_seconds": f"{host_setup_seconds:.6f}",
        "host_setup_observed_percent": f"{100.0 * host_setup_seconds / wall_seconds:.2f}" if wall_seconds else "0.00",
        "fasta_read_seconds": f"{total('fasta_read_seconds'):.6f}",
        "cut_sequence_seconds": f"{total('cut_sequence_seconds'):.6f}",
        "transfer_string_seconds": f"{total('transfer_string_seconds'):.6f}",
        "transfer_table_seconds_nested": f"{total('transfer_table_seconds'):.6f}",
        "src_transform_seconds": f"{total('src_transform_seconds'):.6f}",
        "encode_seconds": f"{total('encode_seconds'):.6f}",
        "cuda_query_init_seconds": f"{total('cuda_query_init_seconds'):.6f}",
        "gasal2_init_seconds": f"{total('gasal2_init_seconds'):.6f}",
        "gasal2_fill_seconds": f"{total('gasal2_fill_seconds'):.6f}",
        "score_target_bytes": total_int("score_target_bytes"),
        "traceback_target_bytes": total_int("traceback_target_bytes"),
        "gasal2_target_batch_bytes": target_batch_bytes,
        "score_requests": sum(score_requests),
        "score_requests_min": min(score_requests),
        "score_requests_max": max(score_requests),
        "traceback_requests": sum(traceback_requests),
        "traceback_requests_min": min(traceback_requests),
        "traceback_requests_max": max(traceback_requests),
        "target_batches_query_dependent": int(query_dependent),
        "fallbacks": total_int("fallbacks"),
        "target_h2d_copy_count": "unavailable",
        "context_creation_events": "unavailable",
        "device_alloc_count": "unavailable",
        "device_alloc_bytes": "unavailable",
        "workspace_initializations": "unavailable",
    }

    output = "".join(f"{key}={value}\n" for key, value in summary.items())
    print(output, end="")
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(output, encoding="utf-8")
    if args.details:
        args.details.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["run", "wall_seconds", *METRICS]
        with args.details.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ProfileError) as exc:
        raise SystemExit(str(exc)) from exc
