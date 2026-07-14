#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_exact_task_compaction_shadow"}"
BUILD_BIN="${BUILD_BIN:-1}"

python3 - "$ROOT/fasim/Fasim-LongTarget.cpp" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8")
required = [
    "FASIM_GASAL2_EXACT_TASK_COMPACTION_SHADOW",
    "benchmark.fasim_top5_gasal2_phase_exact_task_shadow_requested=",
    "benchmark.fasim_top5_gasal2_phase_exact_tasks_before=",
    "benchmark.fasim_top5_gasal2_phase_exact_tasks_after=",
    "benchmark.fasim_top5_gasal2_phase_exact_tasks_dropped_identical=",
    "benchmark.fasim_top5_gasal2_phase_exact_task_shadow_candidate_tasks_after=",
    "benchmark.fasim_top5_gasal2_phase_exact_task_shadow_candidate_tasks_dropped_identical=",
    "benchmark.fasim_top5_gasal2_phase_exact_task_shadow_runtime_work_dropped=",
]
missing = [value for value in required if value not in source]
if missing:
    raise SystemExit(f"missing exact-task shadow source contract: {missing}")
PY

if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2 binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/base" "$WORK/shadow"

run_case() {
  local out_dir="$1"
  shift
  env "$@" \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_GPU_DP_COLUMN_AUTO=1 \
    FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 \
    FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 \
    FASIM_EXACT_COLUMN_EXTEND_BATCH=1 \
    FASIM_PREALIGN_CUDA_TOPK=64 \
    "$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 0 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/base"
run_case "$WORK/shadow" FASIM_GASAL2_EXACT_TASK_COMPACTION_SHADOW=1

base_output="$(find "$WORK/base" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit)"
shadow_output="$(find "$WORK/shadow" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit)"
if [[ -z "$base_output" || -z "$shadow_output" ]]; then
  echo "missing exact-task shadow output" >&2
  exit 1
fi
cmp -s "$base_output" "$shadow_output"

python3 - "$WORK/base/stderr.log" "$WORK/shadow/stderr.log" <<'PY'
import sys
from pathlib import Path


def metrics(path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


base = metrics(sys.argv[1])
shadow = metrics(sys.argv[2])
prefix = "benchmark.fasim_top5_gasal2_phase_"

assert base[prefix + "exact_task_shadow_requested"] == "0", base
assert base[prefix + "exact_task_shadow_active"] == "0", base
base_before = int(base[prefix + "exact_tasks_before"])
base_after = int(base[prefix + "exact_tasks_after"])
assert base_before > 0, base
assert base_after == base_before, base
assert int(base[prefix + "exact_tasks_dropped_identical"]) == 0, base
assert int(base[prefix + "exact_cells_after"]) == int(base[prefix + "exact_cells_before"]), base
assert shadow[prefix + "exact_task_shadow_requested"] == "1", shadow
assert shadow[prefix + "exact_task_shadow_active"] == "1", shadow

before = int(shadow[prefix + "exact_tasks_before"])
after = int(shadow[prefix + "exact_tasks_after"])
dropped = int(shadow[prefix + "exact_tasks_dropped_identical"])
candidate_after = int(shadow[prefix + "exact_task_shadow_candidate_tasks_after"])
candidate_dropped = int(
    shadow[prefix + "exact_task_shadow_candidate_tasks_dropped_identical"]
)
cells_before = int(shadow[prefix + "exact_cells_before"])
cells_after = int(shadow[prefix + "exact_cells_after"])
candidate_cells_after = int(shadow[prefix + "exact_task_shadow_candidate_cells_after"])
assert before > 0, shadow
assert after == before, shadow
assert dropped == 0, shadow
assert 0 < candidate_after <= before, shadow
assert candidate_dropped == before - candidate_after, shadow
assert cells_after == cells_before, shadow
assert 0 < candidate_cells_after <= cells_before, shadow
assert shadow[prefix + "exact_task_shadow_runtime_work_dropped"] == "0", shadow
assert int(shadow["benchmark.fasim_gasal2_fallbacks"]) == 0, shadow

print(f"exact_tasks_before={before}")
print(f"exact_tasks_after={after}")
print(f"exact_tasks_dropped_identical={dropped}")
print(f"shadow_candidate_tasks_after={candidate_after}")
print(f"shadow_candidate_tasks_dropped_identical={candidate_dropped}")
print(f"exact_cells_before={cells_before}")
print(f"exact_cells_after={cells_after}")
print("runtime_work_dropped=0")
PY

echo "ok"
