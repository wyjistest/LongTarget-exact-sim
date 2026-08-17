#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def command_output(command: list[str]) -> dict[str, object]:
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": type(exc).__name__}
    return {
        "available": True,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    governor_paths = sorted(Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_governor"))
    governors: dict[str, str] = {}
    for path in governor_paths:
        try:
            governors[path.parent.parent.name] = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue

    payload: dict[str, object] = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cwd": str(Path.cwd()),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "NA"),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "NA"),
        "cpu_governors": governors or "unavailable",
        "uname": command_output(["uname", "-a"]),
        "lscpu": command_output(["lscpu"]),
        "compiler": command_output([os.environ.get("CXX", "g++"), "--version"]),
        "nvcc": command_output([os.environ.get("NVCC", "nvcc"), "--version"]),
        "nvidia_smi": command_output(["nvidia-smi", "-q"]),
    }
    atomic_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
