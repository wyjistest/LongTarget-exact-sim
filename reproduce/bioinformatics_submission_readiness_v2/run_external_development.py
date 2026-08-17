#!/usr/bin/env python3
"""Run PATO or Triplexator on excluded inputs with corrected output semantics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence


SUMMARY_FIELDS = (
    "# Duplex-ID",
    "Sequence-ID",
    "Total (abs)",
    "Total (rel)",
    "GA (abs)",
    "GA (rel)",
    "TC (abs)",
    "TC (rel)",
    "GT (abs)",
    "GT (rel)",
)


class ExternalDevelopmentError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_summary(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ExternalDevelopmentError(f"missing or unsafe summary output: {path}")
    with path.open(newline="", encoding="utf-8", errors="strict") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != SUMMARY_FIELDS:
            raise ExternalDevelopmentError("external summary columns drift")
        rows = list(reader)
    for row_number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ExternalDevelopmentError(f"malformed external summary row {row_number}")
        for field in SUMMARY_FIELDS[2:]:
            try:
                value = float(row[field])
            except ValueError as error:
                raise ExternalDevelopmentError(
                    f"nonnumeric {field} at external summary row {row_number}"
                ) from error
            if value < 0:
                raise ExternalDevelopmentError(
                    f"negative {field} at external summary row {row_number}"
                )
    return {
        "row_count": len(rows),
        "header_only": not rows,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def command_for(
    tool: str,
    binary: Path,
    query: Path,
    target: Path,
    output_basename: str,
) -> list[str]:
    common = [
        str(binary),
        "-ss",
        str(query),
        "-ds",
        str(target),
        "-l",
        "16",
        "-L",
        "30",
        "-e",
        "5",
        "-of",
        "2",
    ]
    if tool == "pato":
        return [*common, "--version-check", "false", "-cs", "1", "-o", output_basename]
    if tool == "triplexator":
        return [*common, "-rm", "0", "-o", output_basename]
    raise ExternalDevelopmentError(f"unsupported external tool: {tool}")


def run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str],
) -> tuple[dict[str, Any], str, str]:
    started = time.perf_counter()
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
    return (
        {
            "returncode": 124 if timed_out else process.returncode,
            "timed_out": timed_out,
            "wall_seconds": time.perf_counter() - started,
        },
        stdout,
        stderr,
    )


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise ExternalDevelopmentError(f"output directory already exists: {args.output}")
    if not args.binary.is_file() or not os.access(args.binary, os.X_OK):
        raise ExternalDevelopmentError("external binary is missing or not executable")
    for path in (args.query, args.target):
        if not path.is_file() or path.is_symlink():
            raise ExternalDevelopmentError(f"missing or unsafe external input: {path}")
    args.output.mkdir(parents=True)
    basename = "external-result"
    command = command_for(args.tool, args.binary, args.query, args.target, basename)
    environment = {
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
        "OMP_NUM_THREADS": str(args.threads),
        "CUDA_VISIBLE_DEVICES": "",
    }
    execution, stdout, stderr = run_process(
        command,
        cwd=args.output,
        timeout=args.timeout,
        environment=environment,
    )
    (args.output / "stdout.log").write_text(stdout, encoding="utf-8")
    (args.output / "stderr.log").write_text(stderr, encoding="utf-8")
    summary_path = args.output / f"{basename}.summary"
    status = "technical_failure"
    failure_reason = None
    summary = None
    try:
        if execution["timed_out"]:
            raise ExternalDevelopmentError("external development attempt timed out")
        if execution["returncode"] != 0:
            raise ExternalDevelopmentError(
                f"external development attempt exited {execution['returncode']}"
            )
        summary = validate_summary(summary_path)
        status = "development_success"
    except ExternalDevelopmentError as error:
        failure_reason = str(error)
    report = {
        "schema_version": 1,
        "development_diagnostic_only": True,
        "excluded_from_all_v2_formal_panels": True,
        "tool": args.tool,
        "tool_identity": {
            "binary_path": str(args.binary),
            "binary_sha256": sha256(args.binary),
        },
        "inputs": {
            "query": {"path": str(args.query), "sha256": sha256(args.query)},
            "target": {"path": str(args.target), "sha256": sha256(args.target)},
        },
        "command": command,
        "threads": args.threads,
        "environment": {
            "LANG": environment["LANG"],
            "LC_ALL": environment["LC_ALL"],
            "OMP_NUM_THREADS": environment["OMP_NUM_THREADS"],
            "CUDA_VISIBLE_DEVICES": environment["CUDA_VISIBLE_DEVICES"],
        },
        "output_basename_only": True,
        "expected_summary_suffix": ".summary",
        "execution": execution,
        "status": status,
        "failure_reason": failure_reason,
        "summary": summary,
    }
    (args.output / "development-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=("pato", "triplexator"), required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--query", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    for field in ("binary", "query", "target", "output"):
        setattr(args, field, getattr(args, field).resolve())
    try:
        report = execute(args)
    except (OSError, ValueError, ExternalDevelopmentError) as error:
        print(f"external development harness failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "development_success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
