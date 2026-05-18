#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from pathlib import Path
import sys
from typing import Dict
import zlib


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_fasim_gpu_dp_column_characterization import (  # noqa: E402
    ModeSpec,
    RunResult,
    WorkloadSpec,
    run_once,
)


HG38_CHR21_WINDOW_6755 = """
TTGTTGAGTGAAATTCAACAAGAATTTAGAATAAAGAGATCCTAGGAAAAGGCTCTTTGAGTCTCCTTTGGTTTGAGAAA
TGACACCACCTTTGTCCACAGAGCCCAGCAATTGTCAGTAAGAACTGAAGCCACCTGCATTAACATGACAAATATTTGTT
CCTGGAAATTCTTGCTCAAGAATATAAGGTTATAAATCAATAAATAACTTCACTATTTGCTTTAGGAAAATTCCTGCAAA
CCAACTTGTCTGGGCAAATATTTGGTCTCCTATCAGGACAGTAGATTGCTCACCTGGGCaaacaaatcacttatccaact
tcagtttacttatcaggattcacgttaagactctcccgtcttgagtccaccaacatgaaaatattatgacacaaatattt
cctaggcataatcagttctccatcttaaaccacacaccctaagacccacttaagcccagattctatccaaactctatata
aatatcctctcctgacatttgccttcttgaagcatactaagcctcaataaagtaatgttctctgttactctagtaagtaa
atcaacttagttttgtttgccaacatattttgtggggttttttttgatattttacaCTTGGTAGATTTAAGGAATGCCAC
AATGTGATCAAATTCATGAAACTgagaagccttctgcaaacactaagttgtgccttcctagctcttgaacagtttcagtg
acattttgagaaaaggtgaactgttgtctggtgctttgcaAAGCAACATGACATCTTTACACTTCTACAATGCAAGGAAA
AGAAGATTAATTAGCCCTAGTTACTGTCTAGAGGTCAAACACACAAGACCCGTTGGTTCTAGAGTAGGAGCATGTagagg
tttccaaacaatgatgtatattagaatttccaggggacttgtttaaaatgaggataaagtcccatcttccagagactctg
attcagaagtctatggcagggctcaggcatctgcatACCACATAATGTTGCAAGGGGATCATGGCCCACACTCTTTGAAT
CTACACTGTATCTAAAGTCCAGTCACTTAAGACCATTTCTACTACTGGTCAGTTCCCTTAATGGCCATTTTATCTAATAT
TCAACTTGCTTTTGACTAGTTTTATGTTTATTTGACTGTCTTCTTTTTCATCTTGTCCTTTTTTCAACTTTAAGAATTTC
AAAAAGAATGGAGGAAGATGGGAagagagagagagaaagagagTTTCATCTTGCCTAATTTTATTCATCTGATATGTTTT
CTGTATTTTATGAATAATGATAATATATTTCTAATTTTTACATTATTTTTTGTGTTTGCATTGAAAACTAGTTTTAACTA
GGCTTTTGGGAGACACTTCCTTAAAAATAATATTTCCAGCAATATTAATTTATTGATAATACATAAAACATAAATTATAA
TCATTATGCAATGAGCATAATGATCCCTAAAGAAAATGTAGTCAATTTGTCAAATATTAATTTGGTTTAGGAGATGCTTT
CTGTTAATGAGCTTATTATATGGATGATGTCAAAAATAGCTTCTTCTTTCCTGTAAAAAACCTTTGGATTTTCATAGTAA
ATGAAGACATACAGATCCCCCCACACATCTTCCTGACAAGATTTACACTGAGGGCTAGAAAGAGAGCACAAAGAGAGGAT
ATGGTGAGAAGGAATTGTAGGTTATTGGAGAGCAAATTTTCCTTCTTGACAGCTTGCCTAGGACTTGCACTGTGACCCTG
TTTGTACTAAGCTCTTAAGCAGTTCTTCTGAACAATTGATAATGAAGGGTGAAATAACTCCAGGAATATTGCAAGTAATG
TCTTTTATACATACGTATACATATATAtgtgtgtgtgtgtgtgtgtgtgtgtgtCTAAAGTAACTGTTAACAACTTTTTT
CTAGCAAAAGCCAATGCCTTATGTTGTTCATCTTGACAAATTCAAAAAAAAGACAATATTTACATATCAAAGATAGTACC
TTACTTGCAAAGAGGCCTGTTTCTCCAGATACCTTTTTTAACCCCTTTGGATGAGATTTTTATTGTCAAGTTTATTGGAC
ACCAGCTTTTCTACAAGCACGTTGTATTTTATTCATTCAGCAGGAATTGTACCAATTAAACTTGCCTTACAACTTTTTGC
ATTATGGTTGGACTTGGTGATTGGCATTAAAAATATATACTTCACAGCTTTTATTATACATAAGCTAGATAAATTGTTAA
TGCTTTAGAACTCTCTAGGCAATATGAATGATGGAGATTTCTGTGCTATCCTTGATAAAGTTGAGGATACAGAAAGCAGT
TTTAATCCTCTTTTTATACTCTGCCTGTCTGCCTGTGGAACAAGTTCAGGGAGCTGCTGTTTAGCAGGAACGGAGCCACA
GACTTAATTTTCAAAGCCAGATAAAAGTACATGGTCATATATTCTAAATCTACTTAAAATATAAAATAACTAAATAAACT
GACCTAACTAAAGTAATTGTTGTCCTTAAACAATGAATAAGAGtttttttgttttttgtttttttttgtatttttttttA
AGGCTGAATTCAGGCCAGGTAAAATTTCCATTTGTTTGCATTGTTGTTGTCCAAAGTGCCAATGTTTTGTAAAATTTTAG
TCTTTCATTAAAAATAAACCACTATTTTTTATGCAAGAAGGGACAATGATAAATATAGCCAGAGGCAATCTTTTAATTGT
ACCTTAAGTGTTCTGTCACCTATCCCTAATGTCTTCACTTCAGCTTTACACCTTGGATTCTATTCAACCAGATGCATTTT
TTCTTCTAATTATAATCAAGATGTGTCTACATGAAGTGGAAAATGTGAACAATTATTTAGATTGTTCAAAAAAAAAATAA
AAGCACATTTCAACTGAAAACATGCCAGTAATTGGAGTAGAATGAAGTATTTTTGAGATGAGAATTCTTTGAATCTTACA
TTTGTAAATAGTTTCTCTTCATTTTAAATTTCTTATAGTTTGTGGCTTTGTGGATCTGGCTACAGACCTTTTTAAAGTCA
TCGGGAGGGCATTTTTGCTTACAAACATAGCAAGTTATCTATGCCTTTAAACCTCTACTCTCAGAAAAGAGAAGGTTTCT
GAGAATGCATGGCAAGTATGCTTTACATACCTTGTTGGCAATGTTCACAGAAATAAAGCTTTGGTCAAAGGAACCAGTTT
CTCTTTGGCATACAGATGAATGACATTCAGAGGCATCCTTTACATAAGAAGACATAAAATTTTCTGTACCTGACAATCCC
CCAAATTACCGCCCTTGTGTCTCATTCCTTCAGAACCCTGTGGGGGTGATCCATTTCTTAACTTCTGGTCCTCTTATTCC
ACACTTCCTGGTGTTCTGTTTTAGACCAGTGTTTGCAGTGTAATATCcacctagtacttgttagaaatatggagtgttgg
gtcccatctcaaacctaccaaatcaaaacctgtattttaataagatcatcagatatttgtgaggacattagcatttgaga
aTCTTGGGATTAGATCTCAGTAAGCCATAATGTGACCGACTGTCTGCTAATTAAACCACACTCATACTGGATATTCAGCA
AAGGGCCTCCTCATACTCATGTAGGTTTCTGTATTCTCGATGAGACTTGACCTCATCTTTCCCAACTCTTCATTTTCACT
AAAGAGCCCAGCAATATCTTCAGTGTCTTCTCCCGACACAGGCAACTTCTTACCACAAATGCAAGGTTCTACTACAATGG
TGAGAATTTTTAGACACCAGAAAGAACAGGGGCAGGAAAGGGttttttgtttgtttgtctgtttgcttttgagatggagt
ctctctctgtcgcccaggctggagtgcagtgatgcgatctctgctcactgcaacctccgtctcccaggttcacgccattc
tcctgcctcagcctcccgagtagctgggactacaggcgtccaccaccatgcccggctaattttttgtatttttagtacag
acttgggctttcactgtgttagccagaatggtctcgatctcctgacctcgtgatccacctgcctcgacctcccaatgtgc
tgggattgcaggtgtgagccaccgcgcccagccAGGAAAGGGTTTTTAATTTGCTCTCTAAACCATGTGATGTAGGCAGC
AATTCACCCTATCCACATGTGAGGAATGTGTTGTTTATATCCACTTTCCTTATAGAGGAAATAAATTGGTCATAACTCAT
GGGCAATTCTCTTATATTGTAGACCAGTCTTAACAGTACTTTTCAGAATCATTTCTCTGCACAGACTTTAATGAAGACTA
GCCTGCGTTTCTCCATGTTGATTCTGAAATGCTCAATAGAATTCTTCTCTAGGTTCTTAGCCCAAACATACTTTTGATGT
ACAGAAGACTACTAACTATTTCTACTTTATGAACATGACAAGTAATTATTTATTAAAGTAGTGAAAATAATTCTGTCAAG
AACAATTCATTCTCACTTTGCCCAAGCTGAATGAATATAGATAAGTCTATGGCGGTCCCCTGCATCCTTACACCTGAATA
CTTCCTGAAAATATTTTCTCTCTTCTTCgttagggaaaaaaatattcaatggacactttttaaaaatggtaaagccgatt
ttattcagagggagactgttttgataggtgtagggctcattggaatgggcctttgcaatggggggagagatttggctcaa
ctctaaatataacaagaaaaagtgggaatttatagccaaagattaagatggaggccagtacatagaaaattactgaaaga
aaacataagggtaaagaggaagttctggctaaaccaaccacacaggatccttcctgaagacaggctaggatgttcagaca
ccaccttggggagggtgaaggataaagaatttgatcagaaatcaagggtggtgagatacatgttaaggatgaataaactg
gccttttaggattcttgctaaagttagacaatgcagaggc
"""

HG38_CHR21_SOFTMASK_COMPACT_REGION_Z = """
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
AeEyRdg=
"""


def decode_fixture(payload: str) -> str:
    return zlib.decompress(base64.b64decode("".join(payload.split()))).decode("ascii")


def require_count(metrics: Dict[str, str], key: str, expected: int) -> None:
    try:
        observed = int(round(float(metrics[key])))
    except KeyError as exc:
        raise RuntimeError(f"missing metric {key}") from exc
    except ValueError as exc:
        raise RuntimeError(f"non-numeric metric {key}={metrics[key]!r}") from exc
    if observed != expected:
        raise RuntimeError(f"{key}: expected {expected}, got {observed}")


def require_digest_match(table: RunResult, auto: RunResult, label: str) -> None:
    if table.digest != auto.digest:
        raise RuntimeError(
            f"{label}: digest mismatch against table-only: "
            f"{table.digest} vs {auto.digest}"
        )
    if table.records != auto.records:
        raise RuntimeError(
            f"{label}: record count mismatch between table-only and auto_validate: "
            f"{table.records} vs {auto.records}"
        )


def write_fasta(path: Path, header: str, sequence: str) -> None:
    cleaned = "".join(line.strip() for line in sequence.splitlines() if line.strip())
    if len(cleaned) != 5000:
        raise RuntimeError(f"expected 5000 bp fixture, got {len(cleaned)}")
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f">{header}\n")
        for i in range(0, len(cleaned), 80):
            handle.write(cleaned[i : i + 80] + "\n")


def run_mode(
    *,
    workload: WorkloadSpec,
    mode: ModeSpec,
    cuda_bin: Path,
    work_dir: Path,
) -> RunResult:
    return run_once(
        workload=workload,
        mode=mode,
        bin_path=cuda_bin,
        work_dir=work_dir / workload.label / mode.label,
        require_profile=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cuda-bin", required=True)
    parser.add_argument(
        "--work-dir",
        default=str(ROOT / ".tmp" / "fasim_gpu_dp_column_hg38_score_mismatch_fix"),
    )
    args = parser.parse_args()

    cuda_bin = Path(args.cuda_bin)
    if not cuda_bin.is_absolute():
        cuda_bin = (ROOT / cuda_bin).resolve()
    if not cuda_bin.exists():
        raise RuntimeError(f"missing CUDA Fasim binary: {cuda_bin}")

    work_dir = Path(args.work_dir)
    fixture_dir = work_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        (
            "hg38_chr21_window6755_source",
            "hg38|chr21|14700001-14705000",
            HG38_CHR21_WINDOW_6755,
            "5kb hg38 chr21 source window reproducing GPU DP+column score mismatch",
        ),
        (
            "hg38_chr21_softmask_compact_region",
            "hg38|chr21|41825001-41830000",
            decode_fixture(HG38_CHR21_SOFTMASK_COMPACT_REGION_Z),
            "5kb hg38 chr21 soft-mask region reproducing compact exact-extend threshold drift",
        ),
    ]

    for label, header, sequence, description in cases:
        dna_path = fixture_dir / f"{label}.fa"
        write_fasta(dna_path, header, sequence)
        workload = WorkloadSpec(
            label,
            description,
            dna_path=dna_path,
            rna_path=ROOT / "H19.fa",
        )
        table = run_mode(
            workload=workload,
            mode=ModeSpec("table_only", "cuda", {"FASIM_TRANSFERSTRING_TABLE": "1"}),
            cuda_bin=cuda_bin,
            work_dir=work_dir,
        )
        auto = run_mode(
            workload=workload,
            mode=ModeSpec(
                "auto",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                },
            ),
            cuda_bin=cuda_bin,
            work_dir=work_dir,
        )
        auto_validate = run_mode(
            workload=workload,
            mode=ModeSpec(
                "auto_validate",
                "cuda",
                {
                    "FASIM_TRANSFERSTRING_TABLE": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS": "1",
                    "FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS": "1",
                    "FASIM_GPU_DP_COLUMN_VALIDATE": "1",
                    "FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG": "1",
                },
            ),
            cuda_bin=cuda_bin,
            work_dir=work_dir,
        )

        require_digest_match(table, auto, f"{workload.label}/auto")
        require_digest_match(table, auto_validate, f"{workload.label}/auto_validate")

        metrics = auto_validate.metrics
        require_count(metrics, "fasim_gpu_dp_column_auto_active", 1)
        require_count(metrics, "fasim_gpu_dp_column_auto_selected_path", 1)
        require_count(metrics, "fasim_gpu_dp_column_score_mismatches", 0)
        require_count(metrics, "fasim_gpu_dp_column_validate_windows_failed", 0)
        require_count(metrics, "fasim_gpu_dp_column_validate_score_mismatch_windows", 0)
        require_count(metrics, "fasim_gpu_dp_column_validate_scoreinfo_mismatch_windows", 0)
        require_count(metrics, "fasim_gpu_dp_column_validate_batch_fallback_windows", 0)
        require_count(metrics, "fasim_gpu_dp_column_fallbacks", 0)
        require_count(metrics, "fasim_gpu_dp_column_validate_first_failed_window", -1)
        require_count(metrics, "fasim_gpu_dp_column_validate_first_failure_reason", 0)

    print("Fasim GPU DP+column hg38 score mismatch regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
