#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_fasim_gpu_dp_column_hg38_score_mismatch_fix import (  # noqa: E402
    HG38_CHR21_SOFTMASK_COMPACT_REGION_Z,
    decode_fixture,
    write_fasta,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_ssw_profile_cache_characterization_check"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / ".tmp" / "fasim_ssw_profile_cache_characterization_check.md"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir).resolve()
    fixture_dir = work_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    hg38_dna = fixture_dir / "hg38_chr21_softmask_compact_region.fa"
    write_fasta(
        hg38_dna,
        "hg38|chr21|41825001-41830000",
        decode_fixture(HG38_CHR21_SOFTMASK_COMPACT_REGION_Z),
    )

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "benchmark_fasim_ssw_profile_cache_characterization.py"),
        "--cuda-bin",
        str(cuda_bin),
        "--synthetic-entries",
        "1,8",
        "--hg38-dna",
        str(hg38_dna),
        "--hg38-rna",
        str(ROOT / "H19.fa"),
        "--hg38-label",
        "hg38_chr21_softmask_compact_region",
        "--require-hg38",
        "--repeat",
        "1",
        "--force-auto-small",
        "--work-dir",
        str(work_dir),
        "--output",
        str(Path(args.output).resolve()),
        "--require-profile",
        "--check",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "Fasim SSW profile cache characterization check failed "
            f"with exit {proc.returncode}"
        )
    print("Fasim SSW profile cache characterization checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
