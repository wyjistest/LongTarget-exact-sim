#!/usr/bin/env python3
import tempfile
from pathlib import Path

import fasim_sharded_runner as runner


def main() -> int:
    stderr_text = "\n".join(
        [
            "ordinary stderr line",
            "benchmark.fasim_prealign_cuda_requested=1",
            "benchmark.fasim_prealign_cuda_active=1",
            "benchmark.fasim_prealign_cuda_device=0",
            "benchmark.fasim_prealign_cuda_devices=1",
            "benchmark.fasim_prealign_cuda_tasks=12",
            "benchmark.fasim_prealign_cuda_batches=3",
            "benchmark.fasim_prealign_cuda_topk=64",
            "benchmark.fasim_prealign_cuda_max_tasks=4096",
            "benchmark.fasim_prealign_cuda_peak_suppress_bp=5",
            "benchmark.fasim_prealign_cuda_h2d_seconds=0.010000",
            "benchmark.fasim_prealign_cuda_kernel_seconds=0.120000",
            "benchmark.fasim_prealign_cuda_d2h_seconds=0.020000",
            "benchmark.fasim_prealign_cuda_total_seconds=0.150000",
            "benchmark.fasim_extend_threads=2",
            "benchmark.fasim_extend_seconds=0.500000",
            "benchmark.fasim_output_seconds=0.020000",
            "benchmark.fasim_prealign_cuda_fallbacks=0",
            "",
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        stderr_path = Path(tmp) / "worker.stderr.log"
        stderr_path.write_text(stderr_text, encoding="utf-8")

        telemetry = runner._parse_fasim_telemetry_file(stderr_path)
        assert telemetry["fasim_prealign_cuda_requested"] == 1, telemetry
        assert telemetry["fasim_prealign_cuda_active"] == 1, telemetry
        assert telemetry["fasim_prealign_cuda_tasks"] == 12, telemetry
        assert telemetry["fasim_prealign_cuda_batches"] == 3, telemetry
        assert telemetry["fasim_prealign_cuda_kernel_seconds"] == 0.12, telemetry
        assert telemetry["fasim_extend_seconds"] == 0.5, telemetry

        summed = runner._sum_fasim_telemetry([telemetry, telemetry])
        assert summed["fasim_prealign_cuda_requested"] == 1, summed
        assert summed["fasim_prealign_cuda_active"] == 1, summed
        assert summed["fasim_prealign_cuda_tasks"] == 24, summed
        assert summed["fasim_prealign_cuda_batches"] == 6, summed
        assert summed["fasim_prealign_cuda_kernel_seconds"] == 0.24, summed
        assert summed["fasim_extend_seconds"] == 1.0, summed
        assert summed["fasim_prealign_cuda_topk"] == 64, summed

        run = runner.RunResult(
            label="synthetic",
            cmd=["fake"],
            env_overrides={"FASIM_ENABLE_PREALIGN_CUDA": "1"},
            wall_seconds=1.25,
            stdout_path=Path(tmp) / "worker.stdout.log",
            stderr_path=stderr_path,
            output_dir=Path(tmp),
            output_path=Path(tmp) / "out.lite",
            exit_code=0,
            telemetry=telemetry,
        )
        run_json = runner._run_to_json(run)
        assert run_json["telemetry"]["fasim_prealign_cuda_tasks"] == 12, run_json

        worker = runner._worker_telemetry_from_shards(
            [
                {"run": run_json},
                {"run": {**run_json, "telemetry": {"fasim_prealign_cuda_tasks": 4}}},
                {"status": "skipped_by_resume", "run": {"telemetry": {}}},
            ]
        )
        assert worker["fasim_prealign_cuda_tasks"] == 16, worker
        assert worker["fasim_prealign_cuda_requested"] == 1, worker

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
