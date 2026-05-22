#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WORK="$ROOT/.tmp/check_fasim_sharded_straggler_analysis"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/logs"

cat >"$WORK/inputs/workers_2_report.json" <<'JSON'
{
  "schema_version": 1,
  "run_status": "completed",
  "worker_count": 2,
  "gpu_ids": ["0", "1"],
  "workers_per_gpu": 1,
  "gpu_sharing_mode": "exclusive",
  "cpu_core_ranges": ["0-1", "2-3"],
  "merged_digest": "digest-shared",
  "merged_records": 440,
  "duplicate_records_removed": 4,
  "failed_shards": [],
  "resumed_shards": [],
  "per_worker": [
    {
      "worker_id": 0,
      "gpu_id": "0",
      "cpu_core_range": "0-1",
      "shard_ids": ["shard_a", "shard_d"],
      "estimated_length": 110,
      "estimated_cells": null,
      "wall_seconds": 11.0,
      "records": 110
    },
    {
      "worker_id": 1,
      "gpu_id": "1",
      "cpu_core_range": "2-3",
      "shard_ids": ["shard_b", "shard_c"],
      "estimated_length": 100,
      "estimated_cells": null,
      "wall_seconds": 14.0,
      "records": 330
    }
  ],
  "per_shard": [
    {
      "shard_id": "shard_a",
      "target_name": "chrA",
      "target_start": 1,
      "target_end": 100,
      "estimated_length": 100,
      "estimated_cells": null,
      "worker_id": 0,
      "gpu_id": "0",
      "cpu_core_range": "0-1",
      "records": 100,
      "digest": "digest-a",
      "status": "completed",
      "run": {"wall_seconds": 10.0}
    },
    {
      "shard_id": "shard_b",
      "target_name": "chrB",
      "target_start": 1,
      "target_end": 80,
      "estimated_length": 80,
      "estimated_cells": null,
      "worker_id": 1,
      "gpu_id": "1",
      "cpu_core_range": "2-3",
      "records": 250,
      "digest": "digest-b",
      "status": "completed",
      "run": {"wall_seconds": 9.0}
    },
    {
      "shard_id": "shard_c",
      "target_name": "chrC",
      "target_start": 1,
      "target_end": 20,
      "estimated_length": 20,
      "estimated_cells": null,
      "worker_id": 1,
      "gpu_id": "1",
      "cpu_core_range": "2-3",
      "records": 80,
      "digest": "digest-c",
      "status": "completed",
      "run": {"wall_seconds": 5.0}
    },
    {
      "shard_id": "shard_d",
      "target_name": "chrD",
      "target_start": 1,
      "target_end": 10,
      "estimated_length": 10,
      "estimated_cells": null,
      "worker_id": 0,
      "gpu_id": "0",
      "cpu_core_range": "0-1",
      "records": 10,
      "digest": "digest-d",
      "status": "completed",
      "run": {"wall_seconds": 1.0}
    }
  ]
}
JSON

cat >"$WORK/inputs/workers_3_report.json" <<'JSON'
{
  "schema_version": 1,
  "run_status": "completed",
  "worker_count": 3,
  "gpu_ids": ["0", "1"],
  "workers_per_gpu": null,
  "gpu_sharing_mode": "shared",
  "cpu_core_ranges": ["0-1", "2-3", "4-5"],
  "merged_digest": "digest-shared",
  "merged_records": 440,
  "duplicate_records_removed": 4,
  "failed_shards": [],
  "resumed_shards": [],
  "per_worker": [
    {
      "worker_id": 0,
      "gpu_id": "0",
      "cpu_core_range": "0-1",
      "shard_ids": ["shard_a"],
      "estimated_length": 100,
      "estimated_cells": null,
      "wall_seconds": 10.0,
      "records": 100
    },
    {
      "worker_id": 1,
      "gpu_id": "1",
      "cpu_core_range": "2-3",
      "shard_ids": ["shard_b", "shard_d"],
      "estimated_length": 90,
      "estimated_cells": null,
      "wall_seconds": 10.0,
      "records": 260
    },
    {
      "worker_id": 2,
      "gpu_id": "0",
      "cpu_core_range": "4-5",
      "shard_ids": ["shard_c"],
      "estimated_length": 20,
      "estimated_cells": null,
      "wall_seconds": 5.0,
      "records": 80
    }
  ],
  "per_shard": [
    {
      "shard_id": "shard_a",
      "target_name": "chrA",
      "target_start": 1,
      "target_end": 100,
      "estimated_length": 100,
      "estimated_cells": null,
      "worker_id": 0,
      "gpu_id": "0",
      "cpu_core_range": "0-1",
      "records": 100,
      "digest": "digest-a",
      "status": "completed",
      "run": {"wall_seconds": 10.0}
    },
    {
      "shard_id": "shard_b",
      "target_name": "chrB",
      "target_start": 1,
      "target_end": 80,
      "estimated_length": 80,
      "estimated_cells": null,
      "worker_id": 1,
      "gpu_id": "1",
      "cpu_core_range": "2-3",
      "records": 250,
      "digest": "digest-b",
      "status": "completed",
      "run": {"wall_seconds": 9.0}
    },
    {
      "shard_id": "shard_c",
      "target_name": "chrC",
      "target_start": 1,
      "target_end": 20,
      "estimated_length": 20,
      "estimated_cells": null,
      "worker_id": 2,
      "gpu_id": "0",
      "cpu_core_range": "4-5",
      "records": 80,
      "digest": "digest-c",
      "status": "completed",
      "run": {"wall_seconds": 5.0}
    },
    {
      "shard_id": "shard_d",
      "target_name": "chrD",
      "target_start": 1,
      "target_end": 10,
      "estimated_length": 10,
      "estimated_cells": null,
      "worker_id": 1,
      "gpu_id": "1",
      "cpu_core_range": "2-3",
      "records": 10,
      "digest": "digest-d",
      "status": "completed",
      "run": {"wall_seconds": 1.0}
    }
  ]
}
JSON

python3 "$ROOT/scripts/analyze_fasim_sharded_run_stragglers.py" \
  --workload-name synthetic_stragglers \
  --run "workers_2=$WORK/inputs/workers_2_report.json" \
  --run "workers_3=$WORK/inputs/workers_3_report.json" \
  --simulate-workers 1,2,3,4,5 \
  --output "$WORK/report.json" \
  >"$WORK/logs/analyze.stdout.log" \
  2>"$WORK/logs/analyze.stderr.log"

python3 - "$WORK/report.json" <<'PY'
import json
import math
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
assert report["schema_version"] == 1, report
assert report["mode"] == "sharded_run_straggler_analysis", report
assert report["fasim_execution"] is False, report
assert report["workload_name"] == "synthetic_stragglers", report
assert report["run_labels"] == ["workers_2", "workers_3"], report
assert report["cross_run"]["merged_digest_consistent"] is True, report
assert report["cross_run"]["per_shard_digest_consistent"] is True, report
assert report["cross_run"]["best_observed_run_label"] == "workers_3", report

runs = {run["run_label"]: run for run in report["runs"]}
two = runs["workers_2"]
assert two["worker_count"] == 2, two
assert two["actual_makespan_seconds"] == 14.0, two
assert two["total_shard_seconds"] == 25.0, two
assert two["ideal_makespan_seconds"] == 12.5, two
assert math.isclose(two["scheduler_efficiency"], 12.5 / 14.0), two
assert math.isclose(two["idle_fraction_estimate"], 1.0 - 12.5 / 14.0), two
assert two["straggler_worker"] == 1, two
assert [shard["shard_id"] for shard in two["straggler_shards"]] == ["shard_b", "shard_c"], two
assert two["time_correlation"]["estimated_length_vs_seconds"] > 0.8, two

sim = {item["worker_count"]: item for item in two["observed_time_greedy_simulation"]}
assert sorted(sim) == [1, 2, 3, 4, 5], sim
assert sim[1]["predicted_makespan_seconds"] == 25.0, sim
assert sim[2]["predicted_makespan_seconds"] == 14.0, sim
assert sim[3]["predicted_makespan_seconds"] == 10.0, sim
assert sim[4]["predicted_makespan_seconds"] == 10.0, sim
assert sim[5]["predicted_makespan_seconds"] == 10.0, sim
assert sim[5]["empty_worker_count"] == 1, sim
assert two["predicted_best_worker_count_by_observed_times"] == 3, two

three = runs["workers_3"]
assert three["actual_makespan_seconds"] == 10.0, three
assert three["straggler_worker"] == 0, three
assert three["empty_worker_count"] == 0, three
PY

echo "ok"
