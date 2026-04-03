#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
WORK_DIR="$ROOT_DIR/.tmp/check_project_whole_genome_runtime"
STDERR_LOG="$WORK_DIR/stderr.log"
REPORT_JSON="$WORK_DIR/report.json"

mkdir -p "$WORK_DIR"

cat >"$STDERR_LOG" <<'EOF'
benchmark.sim_solver_backend=cuda_window_pipeline
benchmark.calc_score_seconds=1
benchmark.sim_seconds=3
benchmark.postprocess_seconds=1
benchmark.total_seconds=5
EOF

python3 "$ROOT_DIR/scripts/project_whole_genome_runtime.py" \
  --stderr "$STDERR_LOG" \
  --sample-bp 100 \
  --genome-bp 1000 \
  --parallel-workers 2 \
  --json >"$REPORT_JSON"

python3 - "$REPORT_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

assert data["sample_bp"] == 100
assert data["genome_bp"] == 1000
assert data["parallel_workers"] == 2
assert abs(data["scale_factor"] - 5.0) < 1e-9
assert abs(data["projected_total_seconds"] - 25.0) < 1e-9
assert abs(data["projected_calc_score_seconds"] - 5.0) < 1e-9
assert abs(data["projected_sim_seconds"] - 15.0) < 1e-9
assert abs(data["projected_postprocess_seconds"] - 5.0) < 1e-9
assert data["benchmark"]["sim_solver_backend"] == "cuda_window_pipeline"
PY
