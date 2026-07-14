#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_exact_scoreinfo_pruned_full_output"}"
BUILD_BIN="${BUILD_BIN:-1}"

python3 - "$ROOT/fasim/Fasim-LongTarget.cpp" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text(encoding="utf-8")
required = [
    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_validation_tasks=",
    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_validation_mismatches=",
    "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_cells=",
]
missing = [value for value in required if value not in source]
if missing:
    raise SystemExit(f"missing exact scoreInfo validation telemetry: {missing}")
PY

if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2 binary: $BIN" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/base" "$WORK/candidate" "$WORK/top5"

run_case() {
  local out_dir="$1"
  shift
  env "$@" \
    FASIM_OUTPUT_MODE=tfosorted \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
    FASIM_ALIGN_GASAL2_STREAMS=3 \
    FASIM_ALIGN_GASAL2_BATCH=20000 \
    "$BIN" -f1 "$ROOT/testDNA.fa" -f2 "$ROOT/H19.fa" -r 0 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/base"
run_case "$WORK/candidate" \
  FASIM_EXACT_COLUMN_SCOREINFO_GPU=1 \
  FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512 \
  FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 \
  FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1

base_output="$(find "$WORK/base" -maxdepth 1 -type f -name '*-TFOsorted' -print -quit)"
candidate_output="$(find "$WORK/candidate" -maxdepth 1 -type f -name '*-TFOsorted' -print -quit)"
if [[ -z "$base_output" || -z "$candidate_output" ]]; then
  echo "missing exact scoreInfo pruned full output" >&2
  exit 1
fi
cmp -s "$base_output" "$candidate_output"

python3 - "$base_output" "$candidate_output" "$WORK/top5" <<'PY'
import csv
import sys
from pathlib import Path

columns = [
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "Strand",
    "Rule",
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Score",
    "Nt(bp)",
    "MeanIdentity(%)",
    "MeanStability",
]
out_dir = Path(sys.argv[3])
for label, source in (("base", Path(sys.argv[1])), ("candidate", Path(sys.argv[2]))):
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    with (out_dir / f"{label}_lite.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in columns})
PY

for mode in score stability nt_score; do
  python3 "$ROOT/scripts/extract_fasim_lite_topk.py" \
    --input "$WORK/top5/base_lite.tsv" \
    --output "$WORK/top5/base_${mode}.tsv" \
    --k 5 \
    --mode "$mode" \
    >"$WORK/top5/base_${mode}.log"
  python3 "$ROOT/scripts/extract_fasim_lite_topk.py" \
    --input "$WORK/top5/candidate_lite.tsv" \
    --output "$WORK/top5/candidate_${mode}.tsv" \
    --k 5 \
    --mode "$mode" \
    >"$WORK/top5/candidate_${mode}.log"
  cmp -s "$WORK/top5/base_${mode}.tsv" "$WORK/top5/candidate_${mode}.tsv"
done

python3 "$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py" \
  --baseline "$base_output" \
  --candidate "$candidate_output" \
  --k 5 \
  --details "$WORK/top5/offline_cluster.tsv" \
  >"$WORK/top5/offline_cluster.txt"

python3 - "$WORK/candidate/stderr.log" "$WORK/top5/offline_cluster.txt" <<'PY'
import sys
from pathlib import Path


def metrics(path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


candidate = metrics(sys.argv[1])
cluster = metrics(sys.argv[2])
prefix = "benchmark.fasim_top5_gasal2_phase_"
tasks = int(candidate[prefix + "exact_scoreinfo_gpu_tasks"])
scoreinfo_cells = int(candidate[prefix + "exact_scoreinfo_gpu_cells"])
validation_tasks = int(candidate[prefix + "exact_scoreinfo_gpu_validation_tasks"])
validation_mismatches = int(
    candidate[prefix + "exact_scoreinfo_gpu_validation_mismatches"]
)
assert tasks > 0, candidate
assert scoreinfo_cells > 0, candidate
assert validation_tasks == tasks, candidate
assert validation_mismatches == 0, candidate
assert candidate[prefix + "exact_scoreinfo_gpu_pruned_output_enabled"] == "1"
assert candidate[prefix + "exact_scoreinfo_gpu_column_pruned_output_enabled"] == "0"
assert int(candidate[prefix + "exact_scoreinfo_gpu_overflow_batches"]) == 0
assert int(candidate[prefix + "exact_scoreinfo_gpu_fallback_batches"]) == 0
assert int(candidate["benchmark.fasim_gasal2_fallbacks"]) == 0
assert cluster["top5_offline_cluster_equal"] == "true", cluster
assert cluster["top5_offline_cluster_overlap"] == "5", cluster

print(f"per_task_exact_outputs_equal={int(validation_mismatches == 0)}")
print("full_row_set_equal=1")
print("top5_score_equal=1")
print("top5_stability_equal=1")
print("top5_nt_score_equal=1")
print("offline_clustered_top5_equal=1")
print("fallbacks=0")
PY

echo "ok"
