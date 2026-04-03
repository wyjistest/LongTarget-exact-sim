#!/usr/bin/env python3
import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_fasta_sequence(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        raise RuntimeError(f"empty fasta: {path}")
    seq = "".join(line.strip().replace("\r", "") for line in lines[1:])
    if not seq:
        raise RuntimeError(f"empty fasta sequence: {path}")
    return seq


def _write_multi_fasta(path: Path, *, seq: str, entries: int) -> None:
    with path.open("w", encoding="utf-8") as f:
        for i in range(entries):
            # Keep regions tightly packed to avoid downstream per-genome-position
            # bookkeeping from dominating the runtime (some fasim outputs build
            # per-position distributions).
            start = i * len(seq) + 1
            end = start + len(seq) - 1
            f.write(f">hg19|chr11|{start}-{end}\n")
            f.write(seq)
            f.write("\n")


@dataclasses.dataclass(frozen=True)
class BenchRun:
    label: str
    cmd: list[str]
    env_overrides: dict[str, str]
    wall_seconds: float
    output_dir: str


def _run(
    *,
    label: str,
    cmd: list[str],
    env_overrides: dict[str, str],
    cwd: Path,
    output_dir: Path,
) -> BenchRun:
    env = os.environ.copy()
    env.update(env_overrides)

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(cwd),
        check=False,
    )
    t1 = time.perf_counter()
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed (exit={proc.returncode})")

    return BenchRun(
        label=label,
        cmd=cmd,
        env_overrides=env_overrides,
        wall_seconds=t1 - t0,
        output_dir=str(output_dir),
    )


def main() -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Throughput benchmark for many-region fasta (CPU fasim vs CUDA-prealign fasim).",
    )
    parser.add_argument("--entries", type=int, default=512, help="number of fasta entries (regions)")
    parser.add_argument("--dna", default="testDNA.fa")
    parser.add_argument("--rna", default="H19.fa")
    parser.add_argument("--rule", type=int, default=0)
    parser.add_argument(
        "--work-dir",
        default=str(root / ".tmp" / "fasim_batch_throughput"),
        help="work directory for generated inputs and outputs",
    )
    parser.add_argument("--fasim-cpu", default=str(root / "fasim_longtarget_x86"))
    parser.add_argument("--fasim-cuda", default=str(root / "fasim_longtarget_cuda"))
    parser.add_argument(
        "--cuda-max-tasks",
        type=int,
        default=int(os.environ.get("FASIM_PREALIGN_CUDA_MAX_TASKS", "4096")),
        help="env FASIM_PREALIGN_CUDA_MAX_TASKS override for CUDA run",
    )
    parser.add_argument(
        "--cuda-topk",
        type=int,
        default=int(os.environ.get("FASIM_PREALIGN_CUDA_TOPK", "64")),
        help="env FASIM_PREALIGN_CUDA_TOPK override for CUDA run",
    )
    parser.add_argument(
        "--extend-threads",
        type=int,
        default=int(os.environ.get("FASIM_EXTEND_THREADS", "1")),
        help="env FASIM_EXTEND_THREADS override for both runs",
    )

    args = parser.parse_args()
    if args.entries <= 0:
        raise RuntimeError("--entries must be > 0")
    if args.extend_threads <= 0:
        raise RuntimeError("--extend-threads must be > 0")

    work_dir = Path(args.work_dir).resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    dna_src = Path(args.dna)
    if not dna_src.is_absolute():
        dna_src = (root / dna_src).resolve()
    rna_src = Path(args.rna)
    if not rna_src.is_absolute():
        rna_src = (root / rna_src).resolve()

    seq = _read_fasta_sequence(dna_src)

    inputs_dir = work_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    dna_multi = inputs_dir / f"regions_{args.entries}.fa"
    rna = inputs_dir / rna_src.name
    _write_multi_fasta(dna_multi, seq=seq, entries=args.entries)
    shutil.copyfile(rna_src, rna)

    fasim_cpu = Path(args.fasim_cpu)
    fasim_cuda = Path(args.fasim_cuda)
    if not fasim_cpu.exists():
        raise RuntimeError(f"missing fasim CPU binary: {fasim_cpu}")
    if not fasim_cuda.exists():
        raise RuntimeError(f"missing fasim CUDA binary: {fasim_cuda}")

    base_args = ["-f1", dna_multi.name, "-f2", rna.name, "-r", str(args.rule)]

    cpu_out = work_dir / "fasim_cpu" / "output"
    cpu_out.parent.mkdir(parents=True, exist_ok=True)
    cpu_out.mkdir(parents=True, exist_ok=True)
    cpu = _run(
        label="fasim_cpu",
        cmd=[str(fasim_cpu), *base_args, "-O", str(cpu_out)],
        env_overrides={
            "FASIM_VERBOSE": "0",
            "FASIM_OUTPUT_MODE": "tfosorted",
            "FASIM_EXTEND_THREADS": str(args.extend_threads),
        },
        cwd=inputs_dir,
        output_dir=cpu_out,
    )

    cuda_out = work_dir / "fasim_cuda" / "output"
    cuda_out.parent.mkdir(parents=True, exist_ok=True)
    cuda_out.mkdir(parents=True, exist_ok=True)
    cuda = _run(
        label="fasim_cuda",
        cmd=[str(fasim_cuda), *base_args, "-O", str(cuda_out)],
        env_overrides={
            "FASIM_VERBOSE": "0",
            "FASIM_OUTPUT_MODE": "tfosorted",
            "FASIM_ENABLE_PREALIGN_CUDA": "1",
            "FASIM_PREALIGN_CUDA_MAX_TASKS": str(args.cuda_max_tasks),
            "FASIM_PREALIGN_CUDA_TOPK": str(args.cuda_topk),
            "FASIM_EXTEND_THREADS": str(args.extend_threads),
        },
        cwd=inputs_dir,
        output_dir=cuda_out,
    )

    report = {
        "work_dir": str(work_dir),
        "entries": args.entries,
        "inputs": {
            "dna_template": str(dna_src),
            "rna": str(rna_src),
            "dna_multi": str(dna_multi),
        },
        "runs": {
            "cpu": dataclasses.asdict(cpu),
            "cuda": dataclasses.asdict(cuda),
        },
        "speedup": (cpu.wall_seconds / cuda.wall_seconds) if cuda.wall_seconds else None,
    }
    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"cpu wall={cpu.wall_seconds:.3f}s")
    print(f"cuda wall={cuda.wall_seconds:.3f}s  speedup={report['speedup']:.3f}x")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise
