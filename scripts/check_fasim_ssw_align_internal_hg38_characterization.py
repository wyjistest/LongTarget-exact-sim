#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def env_default(name: str, fallback: str = "") -> str:
    return os.environ.get(name, fallback)


def positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {value!r}") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be positive, got {parsed}")
    return parsed


def resolve_existing_path(value: str, label: str) -> Path:
    if not value:
        raise RuntimeError(
            f"missing {label}; set FASIM_GPU_DP_COLUMN_AUTO_HG38_{label.upper()} "
            f"or pass --{label.lower()}"
        )
    path = Path(value)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    if not path.exists():
        raise RuntimeError(f"missing {label} path: {path}")
    return path


def require_report(output_path: Path, label: str) -> None:
    if not output_path.exists():
        raise RuntimeError(f"missing generated report: {output_path}")
    report = output_path.read_text(encoding="utf-8")
    required_snippets = [
        "# Fasim SSW Align Internal Decomposition",
        f"Workload: `{label}`",
        "## Required Component Table",
        "CIGAR section",
        "includes banded_sw below",
        "banded_sw",
        "nested core traceback DP inside CIGAR section",
        "Score mismatches",
        "Endpoint mismatches",
        "CIGAR mismatches",
        "Digest mismatches",
        "Fallbacks",
        "real optimization added: no",
        "output semantic change: no",
        "GPU AUTO policy change: no",
    ]
    for snippet in required_snippets:
        if snippet not in report:
            raise RuntimeError(f"generated report is missing required text: {snippet!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument("--dna", default=env_default("FASIM_GPU_DP_COLUMN_AUTO_HG38_DNA"))
    parser.add_argument(
        "--rna",
        default=env_default("FASIM_GPU_DP_COLUMN_AUTO_HG38_RNA", str(ROOT / "H19.fa")),
    )
    parser.add_argument(
        "--label",
        default=env_default("FASIM_GPU_DP_COLUMN_AUTO_HG38_LABEL", "hg38_chr21_H19"),
    )
    parser.add_argument(
        "--repeat",
        default=env_default("FASIM_GPU_DP_COLUMN_AUTO_HG38_REPEAT", "1"),
    )
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_ssw_align_internal_hg38_characterization"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "docs" / "fasim_ssw_align_internal_hg38_characterization.md"),
    )
    parser.add_argument("--force-auto", action="store_true")
    args = parser.parse_args()

    cuda_bin = resolve_existing_path(args.cuda_bin, "cuda-bin")
    dna_path = resolve_existing_path(args.dna, "dna")
    rna_path = resolve_existing_path(args.rna, "rna")
    repeat = positive_int(args.repeat, "repeat")
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    work_dir = Path(args.work_dir)
    if not work_dir.is_absolute():
        work_dir = (ROOT / work_dir).resolve()

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "benchmark_fasim_ssw_align_internal_decomposition.py"),
        "--cuda-bin",
        str(cuda_bin),
        "--dna",
        str(dna_path),
        "--rna",
        str(rna_path),
        "--label",
        args.label,
        "--repeat",
        str(repeat),
        "--work-dir",
        str(work_dir),
        "--output",
        str(output_path),
        "--require-profile",
        "--check",
    ]
    if args.force_auto:
        cmd.append("--force-auto")

    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "Fasim SSW align internal hg38 characterization failed "
            f"with exit {proc.returncode}"
        )

    require_report(output_path, args.label)
    print("Fasim SSW align internal hg38 characterization checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
