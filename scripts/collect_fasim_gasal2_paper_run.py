#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path


REQUIRED_FILES = (
    "run-config.json",
    "environment.json",
    "execution.json",
    "correctness.json",
    "stdout.log",
    "stderr.log",
    "time.txt",
    "gpu-memory.csv",
)


def load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid collector JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"collector JSON must be an object: {path}")
    return payload


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def max_rss_kb(path: Path) -> int | None:
    prefix = "Maximum resident set size (kbytes):"
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            try:
                return int(line[len(prefix) :].strip())
            except ValueError as exc:
                raise SystemExit(f"invalid max RSS in {path}") from exc
    return None


def benchmark_metrics(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key.startswith("benchmark."):
            metrics[key] = value
    return metrics


def gpu_metrics(path: Path) -> dict[str, object]:
    required = {
        "timestamp",
        "measurement_status",
        "gpu_index",
        "memory_used_mib",
        "memory_total_mib",
        "utilization_gpu_percent",
        "temperature_gpu_c",
        "power_draw_w",
        "clocks_sm_mhz",
    }
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise SystemExit(f"invalid GPU sample schema: {path}")
        rows = list(reader)
    available = [row for row in rows if row["measurement_status"] == "available"]
    if not available:
        return {
            "gpu_measurement_status": "unavailable",
            "gpu_sample_count": 0,
            "gpu_memory_peak_mib": "NA",
            "gpu_utilization_peak_percent": "NA",
            "gpu_temperature_peak_c": "NA",
            "gpu_power_peak_w": "NA",
            "gpu_sm_clock_peak_mhz": "NA",
        }

    def peak(field: str) -> float:
        try:
            return max(float(row[field]) for row in available)
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"invalid GPU sample field {field}: {path}") from exc

    return {
        "gpu_measurement_status": "available",
        "gpu_sample_count": len(available),
        "gpu_memory_peak_mib": peak("memory_used_mib"),
        "gpu_utilization_peak_percent": peak("utilization_gpu_percent"),
        "gpu_temperature_peak_c": peak("temperature_gpu_c"),
        "gpu_power_peak_w": peak("power_draw_w"),
        "gpu_sm_clock_peak_mhz": peak("clocks_sm_mhz"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    missing = [name for name in REQUIRED_FILES if not (args.run_dir / name).is_file()]
    if missing:
        raise SystemExit("missing collector input: " + ",".join(missing))

    config = load_json(args.run_dir / "run-config.json")
    execution = load_json(args.run_dir / "execution.json")
    correctness = load_json(args.run_dir / "correctness.json")
    for key in (
        "run_id",
        "workload_id",
        "pair_id",
        "mode",
        "runtime_epoch",
        "config_digest_sha256",
    ):
        if key not in config:
            raise SystemExit(f"missing collector config field: {key}")
    for key in ("returncode", "wall_seconds", "timed", "command"):
        if key not in execution:
            raise SystemExit(f"missing collector execution field: {key}")
    if execution["returncode"] != 0:
        raise SystemExit("collector refuses a failed run")
    if "status" not in correctness:
        raise SystemExit("missing collector correctness status")

    payload: dict[str, object] = {
        "schema_version": 1,
        "run_id": config["run_id"],
        "workload_id": config["workload_id"],
        "pair_id": config["pair_id"],
        "mode": config["mode"],
        "runtime_epoch": config["runtime_epoch"],
        "config_digest_sha256": config["config_digest_sha256"],
        "wall_seconds": execution["wall_seconds"],
        "max_rss_kb": max_rss_kb(args.run_dir / "time.txt"),
        "correctness_status": correctness["status"],
        "benchmark_metrics": benchmark_metrics(args.run_dir / "stderr.log"),
        "gpu_memory_sample": str(args.run_dir / "gpu-memory.csv"),
        "stdout": str(args.run_dir / "stdout.log"),
        "stderr": str(args.run_dir / "stderr.log"),
    }
    payload.update(gpu_metrics(args.run_dir / "gpu-memory.csv"))
    atomic_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
