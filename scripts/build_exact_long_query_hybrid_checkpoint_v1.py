#!/usr/bin/env python3
"""Build the long-query hybrid binary from an independently clean worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


BENCHMARK_SOURCE_COMMIT = "61da9b6f1b3d998043d512f5703dc95671d2383e"
GASAL2_COMMIT = "106d94ee53fc847214fb05f2f9f892538a5d3baf"
RUNTIME_PATHS = (
    "cuda/prealign_cuda.cu",
    "cuda/prealign_cuda.h",
    "cuda/prealign_cuda_stub.cpp",
    "fasim/Fasim-LongTarget.cpp",
    "fasim/fastsim.h",
    "fasim/gasal2_align_bridge.cpp",
    "fasim/gasal2_align_bridge.h",
    "fasim/gasal2_align_bridge_stub.cpp",
    "fasim/ssw.h",
    "fasim/sswNew.cpp",
    "fasim/ssw_cpp.cpp",
    "fasim/ssw_cpp.h",
)


class BuildError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BuildError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def output(command: list[str], cwd: Path) -> str:
    return subprocess.run(command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()


def run_logged(command: list[str], cwd: Path, path: Path) -> None:
    with path.open("wb") as log:
        completed = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    require(completed.returncode == 0, f"command failed ({completed.returncode}): {' '.join(command)}")


def status(source: Path) -> str:
    return output(["git", "status", "--porcelain", "--untracked-files=all"], source)


def run(args: argparse.Namespace) -> dict[str, object]:
    source = args.source_root.resolve()
    build_root = args.build_root.resolve()
    require((source / ".git").exists(), f"not a git worktree: {source}")
    require(not build_root.exists(), f"refusing to overwrite build root: {build_root}")
    require(output(["git", "rev-parse", "HEAD"], source) == BENCHMARK_SOURCE_COMMIT, "source worktree is not at benchmark commit")
    status_before = status(source)
    require(status_before == "", f"source worktree is not clean before build: {status_before}")

    build_root.mkdir(parents=True)
    binary = build_root / args.binary_name
    setup_command = ["make", "setup-gasal2"]
    build_command = [
        "make", "build-fasim-gasal2",
        f"FASIM_GASAL2_TARGET={binary}",
        "CPPFLAGS=-DFASIM_WITH_SSW_FORWARD_CONTINUATION",
    ]
    run_logged(setup_command, source, build_root / "setup.log")
    dependency = source / ".tmp/GASAL2"
    require(output(["git", "rev-parse", "HEAD"], dependency) == GASAL2_COMMIT, "GASAL2 dependency commit mismatch")
    dependency_diff = subprocess.run(
        ["git", "diff", "--binary"], cwd=dependency, check=True, stdout=subprocess.PIPE
    ).stdout
    require(dependency_diff, "expected the frozen GASAL2 bridge patch to modify the dependency")
    run_logged(build_command, source, build_root / "build.log")
    require(binary.is_file() and os.access(binary, os.X_OK), "build did not produce an executable")

    status_after = status(source)
    require(status_after == "", f"source worktree changed during build: {status_after}")
    runtime_diff = subprocess.run(
        ["git", "diff", "--binary", BENCHMARK_SOURCE_COMMIT, "--", *RUNTIME_PATHS],
        cwd=source,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    require(runtime_diff == b"", "runtime source differs from benchmark commit")

    receipt = {
        "schema_version": "exact_long_query_hybrid_clean_build_v1",
        "status": "clean_build_pass",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source),
        "source_commit": BENCHMARK_SOURCE_COMMIT,
        "source_status_before": status_before,
        "source_status_after": status_after,
        "source_diff_sha256": sha256_bytes(runtime_diff),
        "runtime_paths": [
            {"path": relative, "sha256": sha256_file(source / relative)}
            for relative in RUNTIME_PATHS
        ],
        "dependency": {
            "name": "GASAL2",
            "commit": GASAL2_COMMIT,
            "patched_diff_sha256": sha256_bytes(dependency_diff),
            "patch_file": str((source / "patches/gasal2-fasim-bridge.patch").resolve()),
            "patch_sha256": sha256_file(source / "patches/gasal2-fasim-bridge.patch"),
        },
        "setup_command": setup_command,
        "build_command": build_command,
        "compiler": output(["g++", "--version"], source).splitlines()[0],
        "nvcc": output(["/usr/local/cuda/bin/nvcc", "--version"], source).splitlines()[-1],
        "binary": str(binary),
        "binary_sha256": sha256_file(binary),
        "setup_log_sha256": sha256_file(build_root / "setup.log"),
        "build_log_sha256": sha256_file(build_root / "build.log"),
    }
    atomic_json(build_root / "build_receipt.json", receipt)
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--source-root", type=Path, required=True)
    result.add_argument("--build-root", type=Path, required=True)
    result.add_argument("--binary-name", default="fasim_longtarget_gasal2_61da9b6")
    return result


def main() -> int:
    try:
        print(json.dumps(run(parser().parse_args()), indent=2, sort_keys=True))
        return 0
    except (BuildError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

