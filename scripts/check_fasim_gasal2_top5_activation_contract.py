#!/usr/bin/env python3
"""Check formal GASAL2 top5 activation fail-close predicates."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "fasim_sharded_runner.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("fasim_sharded_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load runner module: {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _args() -> argparse.Namespace:
    return argparse.Namespace(gasal2_top5_column_pruned_scoreinfo=True)


def _base_sums(shard_count: int = 2) -> dict[str, float]:
    return {
        "fasim_top5_gasal2_gpu_scoreinfo_requested": float(shard_count),
        "fasim_top5_gasal2_gpu_scoreinfo_active": float(shard_count),
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled": float(shard_count),
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled": float(
            shard_count
        ),
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled": float(
            shard_count
        ),
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled": float(
            shard_count
        ),
        "fasim_gasal2_requests": 100.0,
        "fasim_gasal2_score_requests": 60.0,
        "fasim_gasal2_traceback_requests": 40.0,
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks": 20.0,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows": 15.0,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank": 3.0,
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches": 0.0,
        "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches": 0.0,
        "fasim_gasal2_fallbacks": 0.0,
        "fasim_gasal2_length_guard_fallbacks": 0.0,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows": 0.0,
    }


def _activation_error(runner, sums: dict[str, float], shard_count: int = 2) -> str | None:
    return runner._gasal2_top5_activation_error(
        _args(),
        sums,
        shard_count,
        shard_count,
    )


def _assert_error_contains(
    runner,
    sums: dict[str, float],
    expected: str,
    shard_count: int = 2,
) -> None:
    error = _activation_error(runner, sums, shard_count)
    if error is None or expected not in error:
        raise AssertionError(f"expected activation error containing {expected!r}, got {error!r}")


def main() -> int:
    runner = _load_runner()
    clean = _activation_error(runner, _base_sums())
    if clean is not None:
        raise AssertionError(f"clean formal activation unexpectedly failed: {clean}")

    disabled = _base_sums()
    disabled["fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled"] = 1.0
    _assert_error_contains(
        runner,
        disabled,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled",
    )

    zero_rows = _base_sums()
    zero_rows["fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows"] = 0.0
    _assert_error_contains(
        runner,
        zero_rows,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows",
    )

    zero_max_rank = _base_sums()
    zero_max_rank[
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank"
    ] = 0.0
    _assert_error_contains(
        runner,
        zero_max_rank,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank",
    )

    unknown = _base_sums()
    unknown["fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows"] = 1.0
    _assert_error_contains(
        runner,
        unknown,
        "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows",
    )

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
