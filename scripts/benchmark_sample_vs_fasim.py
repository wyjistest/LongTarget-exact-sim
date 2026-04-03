#!/usr/bin/env python3
import argparse
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class RunResult:
    label: str
    cmd: list[str]
    env_overrides: dict[str, str]
    wall_seconds: float
    stderr_path: Path
    output_dir: Path
    internal_seconds: float | None = None


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_checked(
    *,
    label: str,
    cmd: list[str],
    env_overrides: dict[str, str],
    stderr_path: Path,
    output_dir: Path,
    expect_benchmark_total: bool,
    cwd: Path,
) -> RunResult:
    env = os.environ.copy()
    env.update(env_overrides)

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(cwd),
        check=False,
    )
    t1 = time.perf_counter()

    stderr_path.write_text(proc.stderr)

    if proc.returncode != 0:
        raise RuntimeError(
            f"{label} failed (exit={proc.returncode}). See: {stderr_path}"
        )

    internal_seconds = None
    if expect_benchmark_total:
        m = re.search(r"^benchmark\.total_seconds=([0-9]*\.?[0-9]+)$", proc.stderr, re.M)
        if not m:
            raise RuntimeError(
                f"{label} did not print benchmark.total_seconds. See: {stderr_path}"
            )
        internal_seconds = float(m.group(1))

    return RunResult(
        label=label,
        cmd=cmd,
        env_overrides=env_overrides,
        wall_seconds=t1 - t0,
        stderr_path=stderr_path,
        output_dir=output_dir,
        internal_seconds=internal_seconds,
    )


def _ensure_fasim_repo(*, repo_dir: Path, repo_url: str, rev: str | None) -> None:
    if repo_dir.exists():
        if not (repo_dir / ".git").exists():
            raise RuntimeError(f"Fasim repo dir exists but is not a git repo: {repo_dir}")
        if rev:
            subprocess.run(["git", "-C", str(repo_dir), "checkout", rev], check=True)
        return

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    _eprint(f"[fasim] cloning {repo_url} -> {repo_dir}")
    subprocess.run(["git", "clone", repo_url, str(repo_dir)], check=True)

    if rev:
        subprocess.run(["git", "-C", str(repo_dir), "checkout", rev], check=True)


def _ensure_fasim_binary(*, repo_dir: Path) -> Path:
    fasim = repo_dir / "fasim"
    if fasim.exists():
        return fasim

    cpp = repo_dir / "Fasim-LongTarget.cpp"
    ssw_cpp = repo_dir / "ssw_cpp.cpp"
    ssw_new = repo_dir / "sswNew.cpp"
    for p in (cpp, ssw_cpp, ssw_new):
        if not p.exists():
            raise RuntimeError(f"missing fasim source file: {p}")

    _eprint(f"[fasim] building {fasim}")
    subprocess.run(
        [
            "g++",
            str(cpp),
            str(ssw_cpp),
            str(ssw_new),
            "-O3",
            "-msse2",
            "-o",
            str(fasim),
        ],
        check=True,
    )
    return fasim


def _load_tfo_keys(tfo_sorted: Path) -> tuple[set[tuple], set[tuple]]:
    # strict key: (QueryStart, QueryEnd, StartInGenome, EndInGenome, Strand, Rule)
    # relaxed key: (StartInGenome, EndInGenome, Strand, Rule)
    strict: set[tuple] = set()
    relaxed: set[tuple] = set()

    with tfo_sorted.open("r", encoding="utf-8", errors="replace") as f:
        header = f.readline().rstrip("\n")
        if not header:
            return strict, relaxed
        cols = header.split("\t")
        idx = {name: i for i, name in enumerate(cols)}
        required = ["QueryStart", "QueryEnd", "StartInGenome", "EndInGenome", "Strand", "Rule"]
        for name in required:
            if name not in idx:
                raise RuntimeError(f"{tfo_sorted} missing column: {name}")

        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            try:
                qs = int(parts[idx["QueryStart"]])
                qe = int(parts[idx["QueryEnd"]])
                gs = int(parts[idx["StartInGenome"]])
                ge = int(parts[idx["EndInGenome"]])
                strand = parts[idx["Strand"]]
                rule = int(parts[idx["Rule"]])
            except (ValueError, IndexError) as e:
                raise RuntimeError(f"failed parsing {tfo_sorted}: {e}") from e

            strict.add((qs, qe, gs, ge, strand, rule))
            relaxed.add((gs, ge, strand, rule))

    return strict, relaxed


@dataclasses.dataclass(frozen=True)
class MatchStats:
    ref: int
    cand: int
    inter: int

    @property
    def precision(self) -> float:
        return self.inter / self.cand if self.cand else 0.0

    @property
    def recall(self) -> float:
        return self.inter / self.ref if self.ref else 0.0

    @property
    def jaccard(self) -> float:
        denom = self.ref + self.cand - self.inter
        return self.inter / denom if denom else 1.0


def _compare_tfo_sorted(ref_dir: Path, cand_dir: Path) -> dict[str, MatchStats]:
    ref_files = sorted(ref_dir.glob("*-TFOsorted"))
    if not ref_files:
        raise RuntimeError(f"no *-TFOsorted in {ref_dir}")

    # sample 基准只预期一个文件，但这里也支持多文件聚合
    strict_ref_all: set[tuple] = set()
    relaxed_ref_all: set[tuple] = set()
    strict_cand_all: set[tuple] = set()
    relaxed_cand_all: set[tuple] = set()

    for ref_file in ref_files:
        cand_file = cand_dir / ref_file.name
        if not cand_file.exists():
            continue

        ref_strict, ref_relaxed = _load_tfo_keys(ref_file)
        cand_strict, cand_relaxed = _load_tfo_keys(cand_file)

        strict_ref_all |= ref_strict
        relaxed_ref_all |= ref_relaxed
        strict_cand_all |= cand_strict
        relaxed_cand_all |= cand_relaxed

    strict_inter = len(strict_ref_all & strict_cand_all)
    relaxed_inter = len(relaxed_ref_all & relaxed_cand_all)

    return {
        "strict": MatchStats(len(strict_ref_all), len(strict_cand_all), strict_inter),
        "relaxed": MatchStats(len(relaxed_ref_all), len(relaxed_cand_all), relaxed_inter),
    }


def main() -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Benchmark sample and compare LongTarget vs Fasim-LongTarget outputs.",
    )
    parser.add_argument("--dna", default="testDNA.fa")
    parser.add_argument("--rna", default="H19.fa")
    parser.add_argument("--rule", default=0, type=int)
    parser.add_argument("--strand", default="", help="optional: pass to LongTarget -t")
    parser.add_argument(
        "--work-dir",
        default=str(root / ".tmp" / "sample_benchmark_vs_fasim"),
        help="work directory for outputs and logs",
    )
    parser.add_argument(
        "--longtarget",
        default=os.environ.get("TARGET", str(root / "longtarget_cuda")),
        help="path to LongTarget binary (default: $TARGET or ./longtarget_cuda)",
    )
    parser.add_argument(
        "--fasim-repo-dir",
        default=os.environ.get("FASIM_LONGTARGET_DIR", str(root / ".tmp" / "Fasim-LongTarget")),
    )
    parser.add_argument(
        "--fasim-repo-url",
        default=os.environ.get("FASIM_LONGTARGET_URL", "https://github.com/LongTarget/Fasim-LongTarget"),
    )
    parser.add_argument(
        "--fasim-rev",
        default=os.environ.get("FASIM_LONGTARGET_REV", "f7b24d6ca723c2eee855715c8736fd9ab03c8235"),
        help="git revision to checkout (set empty to use current HEAD)",
    )
    parser.add_argument(
        "--fast-update-budget",
        default=int(os.environ.get("LONGTARGET_SIM_FAST_UPDATE_BUDGET", "0")),
        type=int,
        help="LongTarget fast/hybrid update budget (default: env LONGTARGET_SIM_FAST_UPDATE_BUDGET or 0)",
    )
    parser.add_argument(
        "--fast-update-on-fail",
        default=os.environ.get("LONGTARGET_SIM_FAST_UPDATE_ON_FAIL", "0") in ("1", "true", "TRUE", "yes", "YES"),
        action=argparse.BooleanOptionalAction,
        help="LongTarget hybrid mode: update-on-fail (default from env LONGTARGET_SIM_FAST_UPDATE_ON_FAIL)",
    )
    parser.add_argument(
        "--run-fasim-sim",
        default=False,
        action="store_true",
        help="also run fasim with -F (SIM mode, slow)",
    )
    parser.add_argument(
        "--run-local-fasim",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="also run local fasim binaries if present (default: true)",
    )
    parser.add_argument(
        "--run-longtarget-two-stage",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="also run LongTarget in two-stage mode (LONGTARGET_TWO_STAGE=1)",
    )
    parser.add_argument(
        "--two-stage-prefilter-backend",
        default="",
        help="optional: set LONGTARGET_PREFILTER_BACKEND for the two-stage run (e.g. sim, prealign_cuda)",
    )

    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    dna_src = Path(args.dna)
    if not dna_src.is_absolute():
        dna_src = (root / dna_src).resolve()
    rna_src = Path(args.rna)
    if not rna_src.is_absolute():
        rna_src = (root / rna_src).resolve()
    if not dna_src.exists():
        raise RuntimeError(f"missing DNA fasta: {dna_src}")
    if not rna_src.exists():
        raise RuntimeError(f"missing RNA fasta: {rna_src}")

    # 注意：LongTarget 会把 -f1/-f2 的“参数字符串”拼接进输出文件名；
    # 如果这里带路径分隔符（/），会导致输出路径非法。统一 copy 到 work_dir/inputs 并用 basename 运行。
    inputs_dir = work_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    dna = inputs_dir / dna_src.name
    rna = inputs_dir / rna_src.name
    shutil.copyfile(dna_src, dna)
    shutil.copyfile(rna_src, rna)

    longtarget = Path(args.longtarget)
    if not longtarget.exists():
        raise RuntimeError(f"missing LongTarget binary: {longtarget}")

    fasim_repo_dir = Path(args.fasim_repo_dir)
    fasim_rev = args.fasim_rev.strip() or None

    _ensure_fasim_repo(repo_dir=fasim_repo_dir, repo_url=args.fasim_repo_url, rev=fasim_rev)
    fasim_bin = _ensure_fasim_binary(repo_dir=fasim_repo_dir)

    local_fasim_cpu = root / "fasim_longtarget_x86"
    local_fasim_cuda = root / "fasim_longtarget_cuda"

    base_args = ["-f1", dna.name, "-f2", rna.name, "-r", str(args.rule)]
    if args.strand:
        base_args += ["-t", args.strand]

    # 统一使用 CUDA + SIM CUDA(initial+region) 做 exact 参照；fast/hybrid 用相同后端。
    longtarget_common_env = {
        "LONGTARGET_ENABLE_CUDA": "1",
        "LONGTARGET_ENABLE_SIM_CUDA": "1",
        "LONGTARGET_ENABLE_SIM_CUDA_REGION": "1",
        "LONGTARGET_BENCHMARK": "1",
    }

    # 1) LongTarget exact
    lt_exact_out = work_dir / "longtarget_exact" / "output"
    lt_exact_log = work_dir / "longtarget_exact" / "stderr.log"
    lt_exact_out.parent.mkdir(parents=True, exist_ok=True)
    lt_exact_out.mkdir(parents=True, exist_ok=True)
    lt_exact = _run_checked(
        label="longtarget_exact",
        cmd=[str(longtarget), *base_args, "-O", str(lt_exact_out)],
        env_overrides=longtarget_common_env,
        stderr_path=lt_exact_log,
        output_dir=lt_exact_out,
        expect_benchmark_total=True,
        cwd=inputs_dir,
    )

    # 2) LongTarget fast/hybrid
    lt_fast_out = work_dir / "longtarget_fast" / "output"
    lt_fast_log = work_dir / "longtarget_fast" / "stderr.log"
    lt_fast_out.parent.mkdir(parents=True, exist_ok=True)
    lt_fast_out.mkdir(parents=True, exist_ok=True)
    fast_env = dict(longtarget_common_env)
    fast_env["LONGTARGET_SIM_FAST"] = "1"
    fast_env["LONGTARGET_SIM_FAST_UPDATE_BUDGET"] = str(args.fast_update_budget)
    if args.fast_update_on_fail:
        fast_env["LONGTARGET_SIM_FAST_UPDATE_ON_FAIL"] = "1"
    lt_fast = _run_checked(
        label="longtarget_fast",
        cmd=[str(longtarget), *base_args, "-O", str(lt_fast_out)],
        env_overrides=fast_env,
        stderr_path=lt_fast_log,
        output_dir=lt_fast_out,
        expect_benchmark_total=True,
        cwd=inputs_dir,
    )

    lt_two_stage: RunResult | None = None
    lt_two_stage_out = work_dir / "longtarget_two_stage" / "output"
    lt_two_stage_log = work_dir / "longtarget_two_stage" / "stderr.log"
    if args.run_longtarget_two_stage:
        lt_two_stage_out.parent.mkdir(parents=True, exist_ok=True)
        lt_two_stage_out.mkdir(parents=True, exist_ok=True)
        two_stage_env = dict(longtarget_common_env)
        two_stage_env["LONGTARGET_TWO_STAGE"] = "1"
        backend = args.two_stage_prefilter_backend.strip()
        if backend:
            if backend not in ("sim", "prealign", "prealign_cuda", "prealign-cuda"):
                raise RuntimeError(f"invalid --two-stage-prefilter-backend: {backend}")
            if backend == "prealign":
                backend = "prealign_cuda"
            if backend == "prealign-cuda":
                backend = "prealign_cuda"
            two_stage_env["LONGTARGET_PREFILTER_BACKEND"] = backend
        lt_two_stage = _run_checked(
            label="longtarget_two_stage",
            cmd=[str(longtarget), *base_args, "-O", str(lt_two_stage_out)],
            env_overrides=two_stage_env,
            stderr_path=lt_two_stage_log,
            output_dir=lt_two_stage_out,
            expect_benchmark_total=True,
            cwd=inputs_dir,
        )

    # 3) Fasim (fastSim)
    fasim_fast_out = work_dir / "fasim_fast" / "output"
    fasim_fast_log = work_dir / "fasim_fast" / "stderr.log"
    fasim_fast_out.parent.mkdir(parents=True, exist_ok=True)
    fasim_fast_out.mkdir(parents=True, exist_ok=True)
    fasim_fast = _run_checked(
        label="fasim_fast",
        cmd=[str(fasim_bin), "-f1", dna.name, "-f2", rna.name, "-r", str(args.rule), "-O", str(fasim_fast_out)],
        env_overrides={},
        stderr_path=fasim_fast_log,
        output_dir=fasim_fast_out,
        expect_benchmark_total=False,
        cwd=inputs_dir,
    )

    fasim_sim: RunResult | None = None
    if args.run_fasim_sim:
        fasim_sim_out = work_dir / "fasim_sim" / "output"
        fasim_sim_log = work_dir / "fasim_sim" / "stderr.log"
        fasim_sim_out.parent.mkdir(parents=True, exist_ok=True)
        fasim_sim_out.mkdir(parents=True, exist_ok=True)
        fasim_sim = _run_checked(
            label="fasim_sim",
            cmd=[
                str(fasim_bin),
                "-F",
                "-f1",
                dna.name,
                "-f2",
                rna.name,
                "-r",
                str(args.rule),
                "-O",
                str(fasim_sim_out),
            ],
            env_overrides={},
            stderr_path=fasim_sim_log,
            output_dir=fasim_sim_out,
            expect_benchmark_total=False,
            cwd=inputs_dir,
        )

    local_fasim_cpu_run: RunResult | None = None
    local_fasim_cuda_run: RunResult | None = None
    if args.run_local_fasim and local_fasim_cpu.exists():
        out_dir = work_dir / "fasim_local_cpu" / "output"
        log_path = work_dir / "fasim_local_cpu" / "stderr.log"
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        local_fasim_cpu_run = _run_checked(
            label="fasim_local_cpu",
            cmd=[
                str(local_fasim_cpu),
                "-f1",
                dna.name,
                "-f2",
                rna.name,
                "-r",
                str(args.rule),
                "-O",
                str(out_dir),
            ],
            env_overrides={
                "FASIM_VERBOSE": "0",
                "FASIM_OUTPUT_MODE": "tfosorted",
            },
            stderr_path=log_path,
            output_dir=out_dir,
            expect_benchmark_total=False,
            cwd=inputs_dir,
        )

    if args.run_local_fasim and local_fasim_cuda.exists():
        out_dir = work_dir / "fasim_local_cuda" / "output"
        log_path = work_dir / "fasim_local_cuda" / "stderr.log"
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        local_fasim_cuda_run = _run_checked(
            label="fasim_local_cuda",
            cmd=[
                str(local_fasim_cuda),
                "-f1",
                dna.name,
                "-f2",
                rna.name,
                "-r",
                str(args.rule),
                "-O",
                str(out_dir),
            ],
            env_overrides={
                "FASIM_ENABLE_PREALIGN_CUDA": "1",
                "FASIM_VERBOSE": "0",
                "FASIM_OUTPUT_MODE": "tfosorted",
            },
            stderr_path=log_path,
            output_dir=out_dir,
            expect_benchmark_total=False,
            cwd=inputs_dir,
        )

    # Compare results against LongTarget exact.
    comparisons: dict[str, dict[str, MatchStats]] = {}
    comparisons["longtarget_fast"] = _compare_tfo_sorted(lt_exact_out, lt_fast_out)
    if lt_two_stage:
        comparisons["longtarget_two_stage"] = _compare_tfo_sorted(lt_exact_out, lt_two_stage.output_dir)
    comparisons["fasim_fast"] = _compare_tfo_sorted(lt_exact_out, fasim_fast_out)
    if fasim_sim:
        comparisons["fasim_sim"] = _compare_tfo_sorted(lt_exact_out, fasim_sim.output_dir)
    if local_fasim_cpu_run:
        comparisons["fasim_local_cpu"] = _compare_tfo_sorted(lt_exact_out, local_fasim_cpu_run.output_dir)
    if local_fasim_cuda_run:
        comparisons["fasim_local_cuda"] = _compare_tfo_sorted(lt_exact_out, local_fasim_cuda_run.output_dir)

    # Record representative hashes for quick eyeballing.
    def tfo_sha(dir_path: Path) -> str:
        files = list(dir_path.glob("*-TFOsorted"))
        if len(files) != 1:
            return "n/a"
        return _sha256_file(files[0])

    def run_to_dict(r: RunResult) -> dict:
        return {
            "label": r.label,
            "cmd": r.cmd,
            "env_overrides": r.env_overrides,
            "wall_seconds": r.wall_seconds,
            "internal_seconds": r.internal_seconds,
            "stderr_path": str(r.stderr_path),
            "output_dir": str(r.output_dir),
        }

    report = {
        "work_dir": str(work_dir),
        "inputs": {
            "dna_src": str(dna_src),
            "rna_src": str(rna_src),
            "dna_basename": dna.name,
            "rna_basename": rna.name,
            "rule": args.rule,
            "strand": args.strand,
        },
        "longtarget": {
            "path": str(longtarget),
            "exact": run_to_dict(lt_exact) | {"tfosorted_sha256": tfo_sha(lt_exact_out)},
            "fast": run_to_dict(lt_fast) | {"tfosorted_sha256": tfo_sha(lt_fast_out)},
            "two_stage": (run_to_dict(lt_two_stage) | {"tfosorted_sha256": tfo_sha(lt_two_stage.output_dir)})
            if lt_two_stage
            else None,
            "fast_update_budget": args.fast_update_budget,
            "fast_update_on_fail": bool(args.fast_update_on_fail),
        },
        "fasim": {
            "repo_dir": str(fasim_repo_dir),
            "rev": fasim_rev,
            "fast": run_to_dict(fasim_fast) | {"tfosorted_sha256": tfo_sha(fasim_fast_out)},
            "sim": (run_to_dict(fasim_sim) | {"tfosorted_sha256": tfo_sha(fasim_sim.output_dir)})
            if fasim_sim
            else None,
            "local_cpu": (run_to_dict(local_fasim_cpu_run) | {"tfosorted_sha256": tfo_sha(local_fasim_cpu_run.output_dir)})
            if local_fasim_cpu_run
            else None,
            "local_cuda": (run_to_dict(local_fasim_cuda_run) | {"tfosorted_sha256": tfo_sha(local_fasim_cuda_run.output_dir)})
            if local_fasim_cuda_run
            else None,
        },
        "comparisons": {
            k: {mode: dataclasses.asdict(v) for mode, v in stats.items()}
            for k, stats in comparisons.items()
        },
    }

    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    _eprint("")
    _eprint("=== Runtime (wall / internal) ===")
    _eprint(
        f"longtarget_exact  wall={lt_exact.wall_seconds:.3f}s  internal={lt_exact.internal_seconds:.3f}s  sha256(TFOsorted)={tfo_sha(lt_exact_out)[:12]}"
    )
    _eprint(
        f"longtarget_fast   wall={lt_fast.wall_seconds:.3f}s  internal={lt_fast.internal_seconds:.3f}s  budget={args.fast_update_budget}  sha256(TFOsorted)={tfo_sha(lt_fast_out)[:12]}"
    )
    if lt_two_stage:
        _eprint(
            f"longtarget_2stage wall={lt_two_stage.wall_seconds:.3f}s  internal={lt_two_stage.internal_seconds:.3f}s  sha256(TFOsorted)={tfo_sha(lt_two_stage.output_dir)[:12]}"
        )
    _eprint(
        f"fasim_fast        wall={fasim_fast.wall_seconds:.3f}s  sha256(TFOsorted)={tfo_sha(fasim_fast_out)[:12]}"
    )
    if fasim_sim:
        _eprint(f"fasim_sim         wall={fasim_sim.wall_seconds:.3f}s  sha256(TFOsorted)={tfo_sha(fasim_sim.output_dir)[:12]}")
    if local_fasim_cpu_run:
        _eprint(
            f"fasim_local_cpu   wall={local_fasim_cpu_run.wall_seconds:.3f}s  sha256(TFOsorted)={tfo_sha(local_fasim_cpu_run.output_dir)[:12]}"
        )
    if local_fasim_cuda_run:
        _eprint(
            f"fasim_local_cuda  wall={local_fasim_cuda_run.wall_seconds:.3f}s  sha256(TFOsorted)={tfo_sha(local_fasim_cuda_run.output_dir)[:12]}"
        )

    def _fmt_stats(s: MatchStats) -> str:
        return f"ref={s.ref} cand={s.cand} inter={s.inter} prec={s.precision:.3f} rec={s.recall:.3f} jac={s.jaccard:.3f}"

    _eprint("")
    _eprint("=== TFOsorted vs longtarget_exact ===")
    for label, stats in comparisons.items():
        _eprint(f"{label}.strict  {_fmt_stats(stats['strict'])}")
        _eprint(f"{label}.relaxed {_fmt_stats(stats['relaxed'])}")

    _eprint("")
    _eprint(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        _eprint(f"error: {e}")
        raise
