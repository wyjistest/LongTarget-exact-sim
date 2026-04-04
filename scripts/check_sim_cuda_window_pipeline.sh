#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TARGET="${TARGET:-$ROOT_DIR/longtarget_cuda}"
WORK_DIR="$ROOT_DIR/.tmp/check_sim_cuda_window_pipeline"
BASE_OUT_DIR="$WORK_DIR/base_out"
PIPE_OUT_DIR="$WORK_DIR/pipeline_out"
PIPE_STDERR="$WORK_DIR/pipeline.stderr"

mkdir -p "$WORK_DIR"
rm -rf "$BASE_OUT_DIR" "$PIPE_OUT_DIR"
mkdir -p "$BASE_OUT_DIR" "$PIPE_OUT_DIR"
rm -f "$PIPE_STDERR"

cd "$ROOT_DIR"

RULE="${RULE:-1}"

LONGTARGET_OUTPUT_MODE=lite \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$BASE_OUT_DIR" >/dev/null

LONGTARGET_BENCHMARK=1 \
LONGTARGET_OUTPUT_MODE=lite \
LONGTARGET_ENABLE_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 \
LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 \
LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 \
"$TARGET" -f1 testDNA.fa -f2 H19.fa -r "$RULE" -O "$PIPE_OUT_DIR" >/dev/null 2>"$PIPE_STDERR"

grep -Eq '^benchmark\.sim_solver_backend=cuda_window_pipeline$' "$PIPE_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_batches=[1-9][0-9]*$' "$PIPE_STDERR"
grep -Eq '^benchmark\.sim_window_pipeline_tasks_batched=[1-9][0-9]*$' "$PIPE_STDERR"

python3 - "$PIPE_STDERR" <<'PY'
import sys

metrics = {}
with open(sys.argv[1], "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line.startswith("benchmark.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        metrics[key[len("benchmark."):]] = value

required = [
    "sim_window_pipeline_tasks_considered",
    "sim_window_pipeline_tasks_eligible",
    "sim_window_pipeline_ineligible_two_stage",
    "sim_window_pipeline_ineligible_sim_fast",
    "sim_window_pipeline_ineligible_validate",
    "sim_window_pipeline_ineligible_runtime_disabled",
    "sim_window_pipeline_ineligible_query_gt_8192",
    "sim_window_pipeline_ineligible_target_gt_8192",
    "sim_window_pipeline_ineligible_negative_min_score",
    "sim_window_pipeline_batch_runtime_fallbacks",
]
for key in required:
    assert key in metrics, key

considered = int(metrics["sim_window_pipeline_tasks_considered"])
eligible = int(metrics["sim_window_pipeline_tasks_eligible"])
batched = int(metrics["sim_window_pipeline_tasks_batched"])
fallbacks = int(metrics["sim_window_pipeline_task_fallbacks"])
ineligible = sum(
    int(metrics[key])
    for key in required
    if key.startswith("sim_window_pipeline_ineligible_")
)

assert considered >= batched
assert eligible >= batched
assert considered == eligible + ineligible
assert fallbacks >= int(metrics["sim_window_pipeline_batch_runtime_fallbacks"])
PY

BASE_LITE="$BASE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"
PIPE_LITE="$PIPE_OUT_DIR/hg19-H19-testDNA-TFOsorted.lite"

if [ ! -s "$BASE_LITE" ] || [ ! -s "$PIPE_LITE" ]; then
  echo "missing lite outputs for window pipeline check" >&2
  exit 1
fi

cmp -s "$BASE_LITE" "$PIPE_LITE"
