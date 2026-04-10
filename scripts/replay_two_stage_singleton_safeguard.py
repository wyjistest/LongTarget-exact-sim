#!/usr/bin/env python3
import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402


DEFAULT_MIN_PEAK_SCORE = 80
DEFAULT_MIN_SUPPORT = 2
DEFAULT_MIN_MARGIN = 6
DEFAULT_STRONG_SCORE_OVERRIDE = 100
DEFAULT_MAX_WINDOWS_PER_TASK = 8
DEFAULT_MAX_BP_PER_TASK = 32768


@dataclass(frozen=True)
class TraceWindow:
    task_index: int
    fragment_index: int
    reverse_mode: int
    parallel_mode: int
    strand: str
    rule: int
    window_id: int
    window_start_in_fragment: int
    window_end_in_fragment: int
    window_start_in_seq: int
    window_end_in_seq: int
    best_seed_score: int
    second_best_seed_score: int | None
    margin: int | None
    support_count: int
    window_bp: int
    base_after_gate: bool
    reject_reason: str


@dataclass(frozen=True)
class LegacyTopHit:
    key: tuple[int, int, int, int, str, int]
    query_start: int
    query_end: int
    start_in_genome: int
    end_in_genome: int
    strand: str
    rule: int
    start_in_seq: int
    end_in_seq: int
    score: float


def _load_trace_windows(path: Path) -> list[TraceWindow]:
    rows: list[TraceWindow] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for raw in reader:
            rows.append(
                TraceWindow(
                    task_index=int(raw["task_index"]),
                    fragment_index=int(raw["fragment_index"]),
                    reverse_mode=int(raw["reverse_mode"]),
                    parallel_mode=int(raw["parallel_mode"]),
                    strand=raw["strand"],
                    rule=int(raw["rule"]),
                    window_id=int(raw["window_id"]),
                    window_start_in_fragment=int(raw["window_start_in_fragment"]),
                    window_end_in_fragment=int(raw["window_end_in_fragment"]),
                    window_start_in_seq=int(raw["window_start_in_seq"]),
                    window_end_in_seq=int(raw["window_end_in_seq"]),
                    best_seed_score=int(raw["best_seed_score"]),
                    second_best_seed_score=int(raw["second_best_seed_score"]) if raw["second_best_seed_score"] else None,
                    margin=int(raw["margin"]) if raw["margin"] else None,
                    support_count=int(raw["support_count"]),
                    window_bp=int(raw["window_bp"]),
                    base_after_gate=raw["after_gate"] == "1",
                    reject_reason=raw["reject_reason"],
                )
            )
    return rows


def _load_legacy_top_hits(report_path: Path) -> list[LegacyTopHit]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    legacy_dir = Path(report["runs"]["legacy"]["output_dir"]).resolve()
    compare_output_mode = report["compare_output_mode"]
    output_map = sample_vs_fasim._load_output_map(legacy_dir, compare_output_mode)
    summary = sample_vs_fasim._aggregate_output_summaries(list(output_map.values()))

    row_map: dict[tuple[int, int, int, int, str, int], LegacyTopHit] = {}
    for path in sorted(legacy_dir.glob(sample_vs_fasim._output_glob(compare_output_mode))):
        with path.open("r", encoding="utf-8", errors="replace") as f:
            header = f.readline().rstrip("\n").split("\t")
            index = {name: i for i, name in enumerate(header)}
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                key = (
                    int(parts[index["QueryStart"]]),
                    int(parts[index["QueryEnd"]]),
                    int(parts[index["StartInGenome"]]),
                    int(parts[index["EndInGenome"]]),
                    parts[index["Strand"]],
                    int(parts[index["Rule"]]),
                )
                if key not in summary.top_hit_keys:
                    continue
                row_map[key] = LegacyTopHit(
                    key=key,
                    query_start=key[0],
                    query_end=key[1],
                    start_in_genome=key[2],
                    end_in_genome=key[3],
                    strand=key[4],
                    rule=key[5],
                    start_in_seq=int(parts[index["StartInSeq"]]),
                    end_in_seq=int(parts[index["EndInSeq"]]),
                    score=float(parts[index["Score"]]),
                )
    return [row_map[key] for key in sorted(summary.top_hit_keys)]


def _window_sort_key(window: TraceWindow) -> tuple[int, int, int, int, int]:
    margin_sort = window.margin if window.margin is not None else -10**18
    return (
        -window.best_seed_score,
        -window.support_count,
        -margin_sort,
        window.window_start_in_fragment,
        window.window_end_in_fragment,
    )


def _is_singleton_no_margin_candidate(window: TraceWindow) -> bool:
    return (
        window.reject_reason in {"support_margin", "singleton_missing_margin"}
        and window.support_count == 1
        and window.second_best_seed_score is None
        and window.margin is None
    )


def _base_keep(window: TraceWindow) -> bool:
    if window.best_seed_score < DEFAULT_MIN_PEAK_SCORE:
        return False
    support_ok = window.support_count >= DEFAULT_MIN_SUPPORT
    margin_ok = window.margin is not None and window.margin >= DEFAULT_MIN_MARGIN
    strong_score_ok = window.best_seed_score >= DEFAULT_STRONG_SCORE_OVERRIDE
    return support_ok or margin_ok or strong_score_ok


def _choose_rescue_candidates(
    task_windows: list[TraceWindow],
    strategy: str,
    singleton_override: int,
) -> set[int]:
    candidate_indices = [
        i
        for i, window in enumerate(task_windows)
        if _is_singleton_no_margin_candidate(window) and window.best_seed_score >= singleton_override
    ]
    if not candidate_indices:
        return set()
    if strategy == "singleton_score_override":
        return set(candidate_indices)
    ranked = sorted(candidate_indices, key=lambda idx: _window_sort_key(task_windows[idx]))
    if strategy == "rescue_one_singleton_per_task":
        return {ranked[0]}
    if strategy == "rescue_one_singleton_per_task_if_toplike":
        task_ranked = sorted(range(len(task_windows)), key=lambda idx: _window_sort_key(task_windows[idx]))
        return {ranked[0]} if ranked[0] == task_ranked[0] else set()
    raise RuntimeError(f"unknown strategy: {strategy}")


def _simulate_task(
    task_windows: list[TraceWindow],
    strategy: str,
    singleton_override: int,
) -> tuple[list[TraceWindow], set[int]]:
    rescue_indices = _choose_rescue_candidates(task_windows, strategy, singleton_override)
    kept = []
    rescued = set()
    for i, window in enumerate(task_windows):
        keep = _base_keep(window)
        if not keep and i in rescue_indices:
            keep = True
            rescued.add(i)
        if keep:
            kept.append((i, window))

    kept.sort(key=lambda item: _window_sort_key(item[1]))
    if DEFAULT_MAX_WINDOWS_PER_TASK >= 0:
        kept = kept[:DEFAULT_MAX_WINDOWS_PER_TASK]
    if DEFAULT_MAX_BP_PER_TASK >= 0:
        budgeted: list[tuple[int, TraceWindow]] = []
        total_bp = 0
        for item in kept:
            if total_bp + item[1].window_bp > DEFAULT_MAX_BP_PER_TASK:
                continue
            total_bp += item[1].window_bp
            budgeted.append(item)
        kept = budgeted
    kept_indices = {index for index, _ in kept}
    rescued_kept = {index for index in rescued if index in kept_indices}
    return [window for _, window in kept], rescued_kept


def _load_case_report(report_path: Path, candidate_label: str) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "report": report,
        "candidate": report["runs"][candidate_label],
        "deferred": report["runs"]["deferred_exact"],
        "comparison": report["comparisons_vs_legacy"].get(candidate_label, {}),
    }


def _top_hits_covered(top_hits: list[LegacyTopHit], kept_windows: list[TraceWindow]) -> tuple[int, list[dict[str, object]]]:
    covered_items: list[dict[str, object]] = []
    covered_count = 0
    for top_hit in top_hits:
        matching = [
            {
                "task_index": window.task_index,
                "fragment_index": window.fragment_index,
                "window_id": window.window_id,
                "window_start_in_seq": window.window_start_in_seq,
                "window_end_in_seq": window.window_end_in_seq,
                "best_seed_score": window.best_seed_score,
                "support_count": window.support_count,
            }
            for window in kept_windows
            if window.rule == top_hit.rule
            and window.strand == top_hit.strand
            and window.window_start_in_seq <= top_hit.start_in_seq
            and window.window_end_in_seq >= top_hit.end_in_seq
        ]
        if matching:
            covered_count += 1
        covered_items.append(
            {
                "top_hit": {
                    "query_start": top_hit.query_start,
                    "query_end": top_hit.query_end,
                    "start_in_genome": top_hit.start_in_genome,
                    "end_in_genome": top_hit.end_in_genome,
                    "strand": top_hit.strand,
                    "rule": top_hit.rule,
                    "start_in_seq": top_hit.start_in_seq,
                    "end_in_seq": top_hit.end_in_seq,
                    "score": top_hit.score,
                },
                "covered": bool(matching),
                "covering_windows": matching,
            }
        )
    return covered_count, covered_items


def _parse_case(value: str) -> tuple[str, Path, Path]:
    parts = value.split("|")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("case must be LABEL|REPORT_JSON|DEBUG_TSV")
    label, report_path, debug_csv = parts
    return label, Path(report_path).resolve(), Path(debug_csv).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay singleton-no-margin safeguards against per-window gate traces.",
    )
    parser.add_argument(
        "--case",
        action="append",
        required=True,
        type=_parse_case,
        help="LABEL|REPORT_JSON|DEBUG_TSV (repeatable)",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        default=None,
        choices=(
            "singleton_score_override",
            "rescue_one_singleton_per_task",
            "rescue_one_singleton_per_task_if_toplike",
        ),
        help="subset of strategies to replay",
    )
    parser.add_argument(
        "--singleton-override",
        action="append",
        type=int,
        default=None,
        help="singleton override scores to replay (default: 85,90)",
    )
    parser.add_argument("--output", default="", help="optional JSON output path")
    args = parser.parse_args()

    strategies = args.strategy or [
        "singleton_score_override",
        "rescue_one_singleton_per_task",
        "rescue_one_singleton_per_task_if_toplike",
    ]
    overrides = args.singleton_override or [85, 90]

    cases_output: list[dict[str, object]] = []
    aggregate: dict[str, dict[str, float | int]] = {}

    for label, report_path, debug_csv in args.case:
        report_info = _load_case_report(report_path, "deferred_exact_minimal_v1")
        trace_windows = _load_trace_windows(debug_csv)
        top_hits = _load_legacy_top_hits(report_path)
        by_task: dict[int, list[TraceWindow]] = defaultdict(list)
        for window in trace_windows:
            by_task[window.task_index].append(window)

        baseline_threshold_invoked = int(report_info["candidate"]["threshold_invoked"])
        baseline_windows_after_gate = int(report_info["candidate"]["windows_after_gate"])
        baseline_top_hit_retention = float(report_info["comparison"].get("top_hit_retention", 0.0))
        case_result = {
            "label": label,
            "report": str(report_path),
            "debug_csv": str(debug_csv),
            "task_count_with_windows_before_gate": len(by_task),
            "baseline": {
                "threshold_invoked": baseline_threshold_invoked,
                "threshold_skipped_after_gate": int(report_info["candidate"]["threshold_skipped_after_gate"]),
                "windows_after_gate": baseline_windows_after_gate,
                "refine_total_bp": int(report_info["candidate"]["refine_total_bp"]),
                "top_hit_retention": baseline_top_hit_retention,
                "legacy_top_hit_count": len(top_hits),
                "singleton_missing_margin_candidates": sum(1 for window in trace_windows if _is_singleton_no_margin_candidate(window)),
            },
            "replays": [],
        }

        for strategy in strategies:
            for override in overrides:
                kept_windows: list[TraceWindow] = []
                rescued_window_count = 0
                rescued_task_count = 0
                threshold_invoked = 0
                windows_after_gate = 0
                refine_total_bp = 0
                for task_windows in by_task.values():
                    kept, rescued_indices = _simulate_task(task_windows, strategy, override)
                    if kept:
                        threshold_invoked += 1
                    if rescued_indices:
                        rescued_task_count += 1
                        rescued_window_count += len(rescued_indices)
                    windows_after_gate += len(kept)
                    refine_total_bp += sum(window.window_bp for window in kept)
                    kept_windows.extend(kept)

                top_hit_covered_count, top_hit_details = _top_hits_covered(top_hits, kept_windows)
                replay = {
                    "strategy": strategy,
                    "singleton_override": override,
                    "rescued_window_count": rescued_window_count,
                    "rescued_task_count": rescued_task_count,
                    "threshold_invoked_predicted": threshold_invoked,
                    "threshold_skipped_after_gate_predicted": len(by_task) - threshold_invoked,
                    "windows_after_gate_predicted": windows_after_gate,
                    "refine_total_bp_predicted": refine_total_bp,
                    "delta_threshold_invoked_vs_baseline": threshold_invoked - baseline_threshold_invoked,
                    "delta_windows_after_gate_vs_baseline": windows_after_gate - baseline_windows_after_gate,
                    "top_hit_covered_count": top_hit_covered_count,
                    "top_hit_missing_count": len(top_hits) - top_hit_covered_count,
                    "top_hit_details": top_hit_details,
                }
                case_result["replays"].append(replay)

                key = f"{strategy}@{override}"
                agg = aggregate.setdefault(
                    key,
                    {
                        "case_count": 0,
                        "rescued_window_count": 0,
                        "rescued_task_count": 0,
                        "delta_threshold_invoked_vs_baseline": 0,
                        "delta_windows_after_gate_vs_baseline": 0,
                        "top_hit_covered_count": 0,
                        "top_hit_missing_count": 0,
                    },
                )
                agg["case_count"] += 1
                agg["rescued_window_count"] += rescued_window_count
                agg["rescued_task_count"] += rescued_task_count
                agg["delta_threshold_invoked_vs_baseline"] += replay["delta_threshold_invoked_vs_baseline"]
                agg["delta_windows_after_gate_vs_baseline"] += replay["delta_windows_after_gate_vs_baseline"]
                agg["top_hit_covered_count"] += top_hit_covered_count
                agg["top_hit_missing_count"] += replay["top_hit_missing_count"]

        cases_output.append(case_result)

    result = {
        "cases": cases_output,
        "aggregate": aggregate,
        "defaults": {
            "min_peak_score": DEFAULT_MIN_PEAK_SCORE,
            "min_support": DEFAULT_MIN_SUPPORT,
            "min_margin": DEFAULT_MIN_MARGIN,
            "strong_score_override": DEFAULT_STRONG_SCORE_OVERRIDE,
            "max_windows_per_task": DEFAULT_MAX_WINDOWS_PER_TASK,
            "max_bp_per_task": DEFAULT_MAX_BP_PER_TASK,
        },
    }

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(output_path)
        return 0

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
