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


@dataclasses.dataclass
class OutputSummary:
    files: list[str]
    strict_keys: set[tuple]
    relaxed_keys: set[tuple]
    strict_scores: dict[tuple, float]
    line_count: int
    top_hit_keys: set[tuple]


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


def _output_glob(compare_output_mode: str) -> str:
    if compare_output_mode == "lite":
        return "*-TFOsorted.lite"
    return "*-TFOsorted"


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


def _load_output_summary(path: Path) -> OutputSummary:
    # strict key: (QueryStart, QueryEnd, StartInGenome, EndInGenome, Strand, Rule)
    # relaxed key: (StartInGenome, EndInGenome, Strand, Rule)
    strict: set[tuple] = set()
    relaxed: set[tuple] = set()
    strict_scores: dict[tuple, float] = {}
    line_count = 0

    with path.open("r", encoding="utf-8", errors="replace") as f:
        header = f.readline().rstrip("\n")
        if not header:
            return OutputSummary([path.name], strict, relaxed, strict_scores, line_count, set())
        cols = header.split("\t")
        idx = {name: i for i, name in enumerate(cols)}
        required = ["QueryStart", "QueryEnd", "StartInGenome", "EndInGenome", "Strand", "Rule", "Score"]
        for name in required:
            if name not in idx:
                raise RuntimeError(f"{path} missing column: {name}")

        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            line_count += 1
            parts = line.split("\t")
            try:
                qs = int(parts[idx["QueryStart"]])
                qe = int(parts[idx["QueryEnd"]])
                gs = int(parts[idx["StartInGenome"]])
                ge = int(parts[idx["EndInGenome"]])
                strand = parts[idx["Strand"]]
                rule = int(parts[idx["Rule"]])
                score = float(parts[idx["Score"]])
            except (ValueError, IndexError) as e:
                raise RuntimeError(f"failed parsing {path}: {e}") from e

            strict_key = (qs, qe, gs, ge, strand, rule)
            strict.add(strict_key)
            relaxed.add((gs, ge, strand, rule))
            prev_score = strict_scores.get(strict_key)
            if prev_score is None or score > prev_score:
                strict_scores[strict_key] = score

    top_hit_keys: set[tuple] = set()
    if strict_scores:
        top_score = max(strict_scores.values())
        top_hit_keys = {key for key, score in strict_scores.items() if score == top_score}

    return OutputSummary([path.name], strict, relaxed, strict_scores, line_count, top_hit_keys)


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


def _load_output_map(dir_path: Path, compare_output_mode: str) -> dict[str, OutputSummary]:
    files = sorted(dir_path.glob(_output_glob(compare_output_mode)))
    if not files:
        raise RuntimeError(f"no {_output_glob(compare_output_mode)} in {dir_path}")
    return {path.name: _load_output_summary(path) for path in files}


def _aggregate_output_summaries(summaries: list[OutputSummary]) -> OutputSummary:
    strict_keys: set[tuple] = set()
    relaxed_keys: set[tuple] = set()
    strict_scores: dict[tuple, float] = {}
    files: list[str] = []
    line_count = 0

    for summary in summaries:
        files.extend(summary.files)
        strict_keys |= summary.strict_keys
        relaxed_keys |= summary.relaxed_keys
        line_count += summary.line_count
        for key, score in summary.strict_scores.items():
            prev_score = strict_scores.get(key)
            if prev_score is None or score > prev_score:
                strict_scores[key] = score

    top_hit_keys: set[tuple] = set()
    if strict_scores:
        top_score = max(strict_scores.values())
        top_hit_keys = {key for key, score in strict_scores.items() if score == top_score}

    return OutputSummary(files, strict_keys, relaxed_keys, strict_scores, line_count, top_hit_keys)


def _score_delta_summary(ref_scores: dict[tuple, float], cand_scores: dict[tuple, float]) -> dict[str, float | int]:
    common_keys = sorted(set(ref_scores) & set(cand_scores))
    if not common_keys:
        return {
            "matched_count": 0,
            "changed_count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "positive": 0,
            "negative": 0,
            "zero": 0,
        }

    deltas = [cand_scores[key] - ref_scores[key] for key in common_keys]
    positive = sum(1 for delta in deltas if delta > 0)
    negative = sum(1 for delta in deltas if delta < 0)
    zero = len(deltas) - positive - negative
    return {
        "matched_count": len(deltas),
        "changed_count": positive + negative,
        "min": min(deltas),
        "max": max(deltas),
        "mean": sum(deltas) / len(deltas),
        "positive": positive,
        "negative": negative,
        "zero": zero,
    }


def _aggregate_output_sha256(dir_path: Path, compare_output_mode: str) -> str:
    files = sorted(dir_path.glob(_output_glob(compare_output_mode)))
    if not files:
        return "n/a"

    h = hashlib.sha256()
    for path in files:
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def _empty_output_summary(filename: str) -> OutputSummary:
    return OutputSummary(
        files=[filename],
        strict_keys=set(),
        relaxed_keys=set(),
        strict_scores={},
        line_count=0,
        top_hit_keys=set(),
    )


def _sorted_strict_score_keys(strict_scores: dict[tuple, float]) -> list[tuple]:
    return [
        key
        for key, _score in sorted(
            strict_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def _topk_retention(ref_scores: dict[tuple, float], cand_keys: set[tuple], *, k: int) -> float:
    if k <= 0:
        return 1.0
    ranked_keys = _sorted_strict_score_keys(ref_scores)
    if not ranked_keys:
        return 1.0
    topk = ranked_keys[: min(k, len(ranked_keys))]
    if not topk:
        return 1.0
    retained = sum(1 for key in topk if key in cand_keys)
    return retained / len(topk)


def _score_weighted_recall(ref_scores: dict[tuple, float], cand_keys: set[tuple]) -> float:
    total_weight = sum(max(score, 0.0) for score in ref_scores.values())
    if total_weight <= 0.0:
        return 1.0
    retained_weight = sum(max(score, 0.0) for key, score in ref_scores.items() if key in cand_keys)
    return retained_weight / total_weight


def _comparison_from_summaries(ref_aggregate: OutputSummary, cand_aggregate: OutputSummary) -> dict[str, object]:
    strict_stats = MatchStats(
        len(ref_aggregate.strict_keys),
        len(cand_aggregate.strict_keys),
        len(ref_aggregate.strict_keys & cand_aggregate.strict_keys),
    )
    relaxed_stats = MatchStats(
        len(ref_aggregate.relaxed_keys),
        len(cand_aggregate.relaxed_keys),
        len(ref_aggregate.relaxed_keys & cand_aggregate.relaxed_keys),
    )
    top_hit_retention = (
        len(ref_aggregate.top_hit_keys & cand_aggregate.strict_keys) / len(ref_aggregate.top_hit_keys)
        if ref_aggregate.top_hit_keys
        else 1.0
    )

    comparison = {
        "strict": _match_stats_dict(strict_stats),
        "relaxed": _match_stats_dict(relaxed_stats),
        "score_delta_summary": _score_delta_summary(ref_aggregate.strict_scores, cand_aggregate.strict_scores),
        "top_hit_retention": top_hit_retention,
        "top5_retention": _topk_retention(ref_aggregate.strict_scores, cand_aggregate.strict_keys, k=5),
        "top10_retention": _topk_retention(ref_aggregate.strict_scores, cand_aggregate.strict_keys, k=10),
        "score_weighted_recall": _score_weighted_recall(ref_aggregate.strict_scores, cand_aggregate.strict_keys),
        "recall_proxy": relaxed_stats.recall,
    }
    return comparison


def _compare_output_mode(ref_dir: Path, cand_dir: Path, compare_output_mode: str) -> tuple[dict[str, object], OutputSummary, OutputSummary]:
    ref_map = _load_output_map(ref_dir, compare_output_mode)
    cand_map = _load_output_map(cand_dir, compare_output_mode)

    ref_aggregate = _aggregate_output_summaries(list(ref_map.values()))
    cand_aggregate = _aggregate_output_summaries(list(cand_map.values()))
    comparison = _comparison_from_summaries(ref_aggregate, cand_aggregate)
    per_output_comparisons: dict[str, dict[str, object]] = {}
    for filename in sorted(set(ref_map) | set(cand_map)):
        ref_summary = ref_map.get(filename, _empty_output_summary(filename))
        cand_summary = cand_map.get(filename, _empty_output_summary(filename))
        per_output_comparisons[filename] = _comparison_from_summaries(ref_summary, cand_summary)

    comparison["per_output_comparisons"] = per_output_comparisons
    return comparison, ref_aggregate, cand_aggregate


def _match_stats_dict(stats: MatchStats) -> dict[str, float | int]:
    return {
        "ref": stats.ref,
        "cand": stats.cand,
        "inter": stats.inter,
        "precision": stats.precision,
        "recall": stats.recall,
        "jaccard": stats.jaccard,
    }


def _output_report(r: RunResult, *, output_mode: str, output_summary: OutputSummary, output_sha256: str) -> dict[str, object]:
    return {
        "label": r.label,
        "cmd": r.cmd,
        "env_overrides": r.env_overrides,
        "wall_seconds": r.wall_seconds,
        "internal_seconds": r.internal_seconds,
        "stderr_path": str(r.stderr_path),
        "output_dir": str(r.output_dir),
        "output_mode": output_mode,
        "output_files": output_summary.files,
        "line_count": output_summary.line_count,
        "output_sha256": output_sha256,
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
        "--mode",
        choices=("legacy", "throughput"),
        default="legacy",
        help="legacy keeps the existing sample benchmark matrix; throughput runs exact LongTarget vs the local fasim throughput preset",
    )
    parser.add_argument(
        "--compare-output-mode",
        choices=("tfosorted", "lite"),
        default=None,
        help="output schema used for comparison/reporting (default: legacy=tfosorted, throughput=lite)",
    )
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
        "--fasim-local-cpu",
        default=str(root / "fasim_longtarget_x86"),
        help="path to the vendored/local fasim CPU binary",
    )
    parser.add_argument(
        "--fasim-local-cuda",
        default=str(root / "fasim_longtarget_cuda"),
        help="path to the vendored/local fasim CUDA binary",
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
    parser.add_argument(
        "--throughput-threshold-policy",
        default=os.environ.get("FASIM_THRESHOLD_POLICY", "fasim_peak80"),
        help="throughput-mode threshold policy name passed to the local fasim preset wrapper",
    )
    parser.add_argument(
        "--fasim-cuda-devices",
        default=os.environ.get("FASIM_CUDA_DEVICES", ""),
        help="optional: comma-separated CUDA devices for the throughput local fasim run",
    )
    parser.add_argument(
        "--fasim-extend-threads",
        default=os.environ.get("FASIM_EXTEND_THREADS", ""),
        help="optional: CPU extend/output thread count for the throughput local fasim run",
    )
    parser.add_argument(
        "--fasim-prealign-cuda-topk",
        default=os.environ.get("FASIM_PREALIGN_CUDA_TOPK", "64"),
        help="throughput-mode FASIM_PREALIGN_CUDA_TOPK override",
    )
    parser.add_argument(
        "--fasim-prealign-peak-suppress-bp",
        default=os.environ.get("FASIM_PREALIGN_PEAK_SUPPRESS_BP", "5"),
        help="throughput-mode FASIM_PREALIGN_PEAK_SUPPRESS_BP override",
    )

    args = parser.parse_args()
    compare_output_mode = args.compare_output_mode or ("lite" if args.mode == "throughput" else "tfosorted")
    if args.mode == "legacy" and compare_output_mode != "tfosorted":
        raise RuntimeError("legacy mode currently only supports --compare-output-mode=tfosorted")

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
    if not longtarget.is_absolute():
        longtarget = (root / longtarget).resolve()
    if not longtarget.exists():
        raise RuntimeError(f"missing LongTarget binary: {longtarget}")

    fasim_repo_dir = Path(args.fasim_repo_dir)
    fasim_rev = args.fasim_rev.strip() or None
    fasim_bin: Path | None = None
    if args.mode == "legacy":
        _ensure_fasim_repo(repo_dir=fasim_repo_dir, repo_url=args.fasim_repo_url, rev=fasim_rev)
        fasim_bin = _ensure_fasim_binary(repo_dir=fasim_repo_dir)

    local_fasim_cpu = Path(args.fasim_local_cpu)
    if not local_fasim_cpu.is_absolute():
        local_fasim_cpu = (root / local_fasim_cpu).resolve()
    local_fasim_cuda = Path(args.fasim_local_cuda)
    if not local_fasim_cuda.is_absolute():
        local_fasim_cuda = (root / local_fasim_cuda).resolve()

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
    if args.mode == "throughput":
        longtarget_common_env["LONGTARGET_OUTPUT_MODE"] = compare_output_mode

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

    lt_fast: RunResult | None = None
    lt_fast_out = work_dir / "longtarget_fast" / "output"
    if args.mode == "legacy":
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
    if args.mode == "legacy" and args.run_longtarget_two_stage:
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

    fasim_fast: RunResult | None = None
    fasim_sim: RunResult | None = None
    fasim_fast_out = work_dir / "fasim_fast" / "output"
    if args.mode == "legacy":
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

    if args.mode == "legacy" and args.run_fasim_sim:
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
    throughput_runner_script = root / "scripts" / "run_fasim_throughput_preset.sh"
    if args.mode == "legacy" and args.run_local_fasim and local_fasim_cpu.exists():
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

    if args.mode == "legacy" and args.run_local_fasim and local_fasim_cuda.exists():
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
    elif args.mode == "throughput":
        out_dir = work_dir / "fasim_local_cuda" / "output"
        log_path = work_dir / "fasim_local_cuda" / "stderr.log"
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        throughput_env = {
            "BIN": str(local_fasim_cuda),
            "FASIM_THRESHOLD_POLICY": args.throughput_threshold_policy,
            "FASIM_OUTPUT_MODE": compare_output_mode,
            "FASIM_PREALIGN_CUDA_TOPK": str(args.fasim_prealign_cuda_topk),
            "FASIM_PREALIGN_PEAK_SUPPRESS_BP": str(args.fasim_prealign_peak_suppress_bp),
        }
        if args.fasim_cuda_devices:
            throughput_env["FASIM_CUDA_DEVICES"] = args.fasim_cuda_devices
        if args.fasim_extend_threads:
            throughput_env["FASIM_EXTEND_THREADS"] = str(args.fasim_extend_threads)
        local_fasim_cuda_run = _run_checked(
            label="fasim_local_cuda",
            cmd=[str(throughput_runner_script), "-f1", dna.name, "-f2", rna.name, "-r", str(args.rule), "-O", str(out_dir)],
            env_overrides=throughput_env,
            stderr_path=log_path,
            output_dir=out_dir,
            expect_benchmark_total=False,
            cwd=inputs_dir,
        )

    # Compare results against LongTarget exact.
    comparisons: dict[str, dict[str, object]] = {}
    output_summaries: dict[str, OutputSummary] = {}
    output_shas: dict[str, str] = {}

    def capture_output(label: str, dir_path: Path, mode: str) -> None:
        output_map = _load_output_map(dir_path, mode)
        output_summaries[label] = _aggregate_output_summaries(list(output_map.values()))
        output_shas[label] = _aggregate_output_sha256(dir_path, mode)

    capture_output("longtarget_exact", lt_exact_out, compare_output_mode)

    if lt_fast:
        capture_output("longtarget_fast", lt_fast_out, compare_output_mode)
        comparisons["longtarget_fast"], _, _ = _compare_output_mode(lt_exact_out, lt_fast_out, compare_output_mode)
    if lt_two_stage:
        capture_output("longtarget_two_stage", lt_two_stage.output_dir, compare_output_mode)
        comparisons["longtarget_two_stage"], _, _ = _compare_output_mode(lt_exact_out, lt_two_stage.output_dir, compare_output_mode)
    if fasim_fast:
        capture_output("fasim_fast", fasim_fast_out, compare_output_mode)
        comparisons["fasim_fast"], _, _ = _compare_output_mode(lt_exact_out, fasim_fast_out, compare_output_mode)
    if fasim_sim:
        capture_output("fasim_sim", fasim_sim.output_dir, compare_output_mode)
        comparisons["fasim_sim"], _, _ = _compare_output_mode(lt_exact_out, fasim_sim.output_dir, compare_output_mode)
    if local_fasim_cpu_run:
        capture_output("fasim_local_cpu", local_fasim_cpu_run.output_dir, compare_output_mode)
        comparisons["fasim_local_cpu"], _, _ = _compare_output_mode(lt_exact_out, local_fasim_cpu_run.output_dir, compare_output_mode)
    if local_fasim_cuda_run:
        capture_output("fasim_local_cuda", local_fasim_cuda_run.output_dir, compare_output_mode)
        comparisons["fasim_local_cuda"], _, _ = _compare_output_mode(lt_exact_out, local_fasim_cuda_run.output_dir, compare_output_mode)

    report = {
        "mode": args.mode,
        "compare_output_mode": compare_output_mode,
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
            "exact": _output_report(
                lt_exact,
                output_mode=compare_output_mode,
                output_summary=output_summaries["longtarget_exact"],
                output_sha256=output_shas["longtarget_exact"],
            ),
            "fast": _output_report(
                lt_fast,
                output_mode=compare_output_mode,
                output_summary=output_summaries["longtarget_fast"],
                output_sha256=output_shas["longtarget_fast"],
            )
            if lt_fast
            else None,
            "two_stage": _output_report(
                lt_two_stage,
                output_mode=compare_output_mode,
                output_summary=output_summaries["longtarget_two_stage"],
                output_sha256=output_shas["longtarget_two_stage"],
            )
            if lt_two_stage
            else None,
            "fast_update_budget": args.fast_update_budget,
            "fast_update_on_fail": bool(args.fast_update_on_fail),
        },
        "fasim": {
            "repo_dir": str(fasim_repo_dir),
            "rev": fasim_rev,
            "fast": _output_report(
                fasim_fast,
                output_mode=compare_output_mode,
                output_summary=output_summaries["fasim_fast"],
                output_sha256=output_shas["fasim_fast"],
            )
            if fasim_fast
            else None,
            "sim": _output_report(
                fasim_sim,
                output_mode=compare_output_mode,
                output_summary=output_summaries["fasim_sim"],
                output_sha256=output_shas["fasim_sim"],
            )
            if fasim_sim
            else None,
            "local_cpu": _output_report(
                local_fasim_cpu_run,
                output_mode=compare_output_mode,
                output_summary=output_summaries["fasim_local_cpu"],
                output_sha256=output_shas["fasim_local_cpu"],
            )
            if local_fasim_cpu_run
            else None,
            "local_cuda": _output_report(
                local_fasim_cuda_run,
                output_mode=compare_output_mode,
                output_summary=output_summaries["fasim_local_cuda"],
                output_sha256=output_shas["fasim_local_cuda"],
            )
            if local_fasim_cuda_run
            else None,
        },
        "throughput": {
            "runner": "fasim_local_cuda",
            "threshold_policy": args.throughput_threshold_policy,
            "fasim_cuda_devices": args.fasim_cuda_devices or None,
            "fasim_extend_threads": int(args.fasim_extend_threads) if args.fasim_extend_threads else None,
            "fasim_prealign_cuda_topk": int(args.fasim_prealign_cuda_topk),
            "fasim_prealign_peak_suppress_bp": int(args.fasim_prealign_peak_suppress_bp),
        }
        if args.mode == "throughput"
        else None,
        "comparisons": comparisons,
    }

    report_path = work_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    _eprint("")
    _eprint("=== Runtime (wall / internal) ===")
    _eprint(
        f"longtarget_exact  wall={lt_exact.wall_seconds:.3f}s  internal={lt_exact.internal_seconds:.3f}s  sha256({compare_output_mode})={output_shas['longtarget_exact'][:12]}"
    )
    if lt_fast:
        _eprint(
            f"longtarget_fast   wall={lt_fast.wall_seconds:.3f}s  internal={lt_fast.internal_seconds:.3f}s  budget={args.fast_update_budget}  sha256({compare_output_mode})={output_shas['longtarget_fast'][:12]}"
        )
    if lt_two_stage:
        _eprint(
            f"longtarget_2stage wall={lt_two_stage.wall_seconds:.3f}s  internal={lt_two_stage.internal_seconds:.3f}s  sha256({compare_output_mode})={output_shas['longtarget_two_stage'][:12]}"
        )
    if fasim_fast:
        _eprint(
            f"fasim_fast        wall={fasim_fast.wall_seconds:.3f}s  sha256({compare_output_mode})={output_shas['fasim_fast'][:12]}"
        )
    if fasim_sim:
        _eprint(f"fasim_sim         wall={fasim_sim.wall_seconds:.3f}s  sha256({compare_output_mode})={output_shas['fasim_sim'][:12]}")
    if local_fasim_cpu_run:
        _eprint(
            f"fasim_local_cpu   wall={local_fasim_cpu_run.wall_seconds:.3f}s  sha256({compare_output_mode})={output_shas['fasim_local_cpu'][:12]}"
        )
    if local_fasim_cuda_run:
        _eprint(
            f"fasim_local_cuda  wall={local_fasim_cuda_run.wall_seconds:.3f}s  sha256({compare_output_mode})={output_shas['fasim_local_cuda'][:12]}"
        )

    _eprint("")
    _eprint(f"=== {compare_output_mode} vs longtarget_exact ===")
    for label, stats in comparisons.items():
        strict = stats["strict"]
        relaxed = stats["relaxed"]
        _eprint(
            f"{label}.strict  ref={strict['ref']} cand={strict['cand']} inter={strict['inter']} prec={strict['precision']:.3f} rec={strict['recall']:.3f} jac={strict['jaccard']:.3f}"
        )
        _eprint(
            f"{label}.relaxed ref={relaxed['ref']} cand={relaxed['cand']} inter={relaxed['inter']} prec={relaxed['precision']:.3f} rec={relaxed['recall']:.3f} jac={relaxed['jaccard']:.3f}"
        )

    _eprint("")
    _eprint(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        _eprint(f"error: {e}")
        raise
