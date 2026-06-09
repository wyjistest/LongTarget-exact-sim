#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
COMPARE="$ROOT/scripts/compare_fasim_lite_full_equivalence.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_malat1_no_probe_two_contract_runtime"}"
BUILD_BIN="${BUILD_BIN:-1}"
RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
EXPECTED_ROWS="${EXPECTED_ROWS:-796}"
CHECK_FIRST64="${CHECK_FIRST64:-0}"
CHECK_FIRST128="${CHECK_FIRST128:-0}"
CHECK_FIRST256="${CHECK_FIRST256:-0}"
CHECK_FULL="${CHECK_FULL:-0}"
OUTPUT_MODE="${OUTPUT_MODE:-lite}"
RNA_INPUT="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
DNA_INPUT="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"

case "$RECORD_LIMIT" in
  ''|*[!0-9]*)
    echo "MALAT1_RECORD_LIMIT must be a positive integer, got: $RECORD_LIMIT" >&2
    exit 1
    ;;
esac
if [[ "$RECORD_LIMIT" -le 0 ]]; then
  echo "MALAT1_RECORD_LIMIT must be a positive integer, got: $RECORD_LIMIT" >&2
  exit 1
fi
case "$EXPECTED_ROWS" in
  ''|*[!0-9]*)
    echo "EXPECTED_ROWS must be a positive integer, got: $EXPECTED_ROWS" >&2
    exit 1
    ;;
esac
if [[ "$EXPECTED_ROWS" -le 0 ]]; then
  echo "EXPECTED_ROWS must be a positive integer, got: $EXPECTED_ROWS" >&2
  exit 1
fi
case "$CHECK_FIRST64" in
  0|1)
    ;;
  *)
    echo "CHECK_FIRST64 must be 0 or 1, got: $CHECK_FIRST64" >&2
    exit 1
    ;;
esac
case "$CHECK_FIRST128" in
  0|1)
    ;;
  *)
    echo "CHECK_FIRST128 must be 0 or 1, got: $CHECK_FIRST128" >&2
    exit 1
    ;;
esac
case "$CHECK_FIRST256" in
  0|1)
    ;;
  *)
    echo "CHECK_FIRST256 must be 0 or 1, got: $CHECK_FIRST256" >&2
    exit 1
    ;;
esac
case "$CHECK_FULL" in
  0|1)
    ;;
  *)
    echo "CHECK_FULL must be 0 or 1, got: $CHECK_FULL" >&2
    exit 1
    ;;
esac
case "$OUTPUT_MODE" in
  lite|tfosorted)
    ;;
  *)
    echo "OUTPUT_MODE must be lite or tfosorted, got: $OUTPUT_MODE" >&2
    exit 1
    ;;
esac

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
for path in "$RUNNER" "$COMPARE" "$RNA_INPUT" "$DNA_INPUT"; do
  if [[ ! -s "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

run_case() {
  local label="$1"
  local record_limit="$2"
  local expected_rows="$3"
  local expected_tasks="$4"
  local expected_gpu_scoreinfo_groups="$5"
  local case_work="$WORK/$label"

  rm -rf "$case_work"
  mkdir -p "$case_work/inputs"
  local sample="$case_work/inputs/malat1_first${record_limit}.fa"
  awk -v limit="$record_limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$DNA_INPUT" >"$sample"
  if [[ ! -s "$sample" ]]; then
    echo "empty MALAT1 sample for $label" >&2
    exit 1
  fi

  local baseline_start baseline_end candidate_start candidate_end
  baseline_start="$(now_seconds)"
  python3 "$RUNNER" \
    --fasim-bin "$BIN" \
    --target "$sample" \
    --rna "$RNA_INPUT" \
    --rule 0 \
    --output-mode "$OUTPUT_MODE" \
    --group-target-records 32 \
    --workers 1 \
    --work-dir "$case_work/baseline" \
    --manifest "$case_work/baseline/run_manifest.json" \
    >"$case_work/baseline.report.json"
  baseline_end="$(now_seconds)"

  candidate_start="$(now_seconds)"
  python3 "$RUNNER" \
    --fasim-bin "$BIN" \
    --target "$sample" \
    --rna "$RNA_INPUT" \
    --rule 0 \
    --output-mode "$OUTPUT_MODE" \
    --workers 1 \
    --work-dir "$case_work/candidate" \
    --manifest "$case_work/candidate/run_manifest.json" \
    --long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32 \
    >"$case_work/candidate.report.json"
  candidate_end="$(now_seconds)"

  local baseline_wall candidate_wall
  baseline_wall="$(elapsed_seconds "$baseline_start" "$baseline_end")"
  candidate_wall="$(elapsed_seconds "$candidate_start" "$candidate_end")"

  python3 "$COMPARE" \
    --baseline-report "$case_work/baseline.report.json" \
    --candidate-report "$case_work/candidate.report.json" \
    >"$case_work/compare.txt"

  grep -q "^schema=$OUTPUT_MODE$" "$case_work/compare.txt"
  grep -q "^baseline_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q "^candidate_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q "^baseline_unique_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q "^candidate_unique_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q '^missing_rows=0$' "$case_work/compare.txt"
  grep -q '^extra_rows=0$' "$case_work/compare.txt"
  grep -q '^full_rows_equal=true$' "$case_work/compare.txt"

  python3 - \
    "$case_work/baseline.report.json" \
    "$case_work/candidate.report.json" \
    "$case_work/compare.txt" \
    "$case_work/summary.json" \
    "$expected_rows" \
    "$record_limit" \
    "$label" \
    "$expected_tasks" \
    "$expected_gpu_scoreinfo_groups" \
    "$baseline_wall" \
    "$candidate_wall" \
    "$OUTPUT_MODE" <<'PY'
import json
import sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
compare = Path(sys.argv[3]).read_text(encoding="utf-8")
summary_path = Path(sys.argv[4])
expected_rows = int(sys.argv[5])
record_limit = int(sys.argv[6])
case_label = sys.argv[7]
expected_tasks = int(sys.argv[8])
expected_gpu_scoreinfo_groups = int(sys.argv[9])
baseline_wall = float(sys.argv[10])
candidate_wall = float(sys.argv[11])
output_mode = sys.argv[12]
bench = candidate.get("fasim_benchmark_sums", {})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def num(key: str) -> float:
    value = bench.get(key)
    require(value is not None, f"missing benchmark key: {key}")
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)),
        f"benchmark key {key} is not numeric: {value!r}",
    )
    return float(value)


require(f"schema={output_mode}" in compare, f"expected schema={output_mode} comparison")
require(f"baseline_rows={expected_rows}" in compare, "baseline row count mismatch")
require(f"candidate_rows={expected_rows}" in compare, "candidate row count mismatch")
require("missing_rows=0" in compare, "expected no missing rows")
require("extra_rows=0" in compare, "expected no extra rows")
require("full_rows_equal=true" in compare, "expected full row equality")
for label, report in (("baseline", baseline), ("candidate", candidate)):
    require(report.get("run_status") == "completed", f"{label}: run_status={report.get('run_status')}")
    require(report.get("output_mode") == output_mode, f"{label}: output_mode={report.get('output_mode')}")
    require(report.get("merged_records") == expected_rows, f"{label}: merged_records mismatch")
    require(report.get("target_record_count") == record_limit, f"{label}: target_record_count mismatch")
    require(report.get("group_target_records") == 32, f"{label}: group_target_records mismatch")
    require(report.get("shard_count") == (record_limit + 31) // 32, f"{label}: shard_count mismatch")
    require(report.get("worker_count") == 1, f"{label}: worker_count mismatch")
require(baseline.get("result_contract") == "merged_output_v1", "baseline: unexpected result_contract")
require(baseline.get("merged_digest") == candidate.get("merged_digest"), "merged digest mismatch")

baseline_env = baseline.get("env_overrides", {})
candidate_env = candidate.get("env_overrides", {})
require(baseline_env == {}, f"baseline must not set env overrides: {baseline_env}")
expected_env = {
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
    "FASIM_ALIGN_GASAL2": "1",
}
require(candidate_env == expected_env, f"unexpected candidate env overrides: {candidate_env}")
for key in candidate_env:
    require("PROBE" not in key, f"probe env leaked into no-probe runtime: {key}")
require(
    candidate.get("result_contract")
    == "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1",
    f"unexpected runtime result_contract: {candidate.get('result_contract')}",
)
require(
    candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_runtime") is True,
    "candidate did not record two-contract runtime flag",
)
require(
    candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32") is True,
    "candidate did not record two-contract runtime group32 flag",
)
require(
    candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_trust") is False,
    "runtime candidate must not record audited two-contract trust flag",
)
require(
    candidate.get("long_query_streaming_scoreinfo_gpu_two_contract_trust_group32") is False,
    "runtime candidate must not record audited two-contract trust group32 flag",
)
require(
    candidate.get("long_query_streaming_scoreinfo_gpu_trust_profile")
    == "malat1_like_two_contract_runtime_group32_experimental_v1",
    f"unexpected runtime trust profile: {candidate.get('long_query_streaming_scoreinfo_gpu_trust_profile')}",
)
require(
    candidate.get("long_query_streaming_scoreinfo_gpu_trust_decision")
    == "experimental_external_digest_gate",
    f"unexpected runtime trust decision: {candidate.get('long_query_streaming_scoreinfo_gpu_trust_decision')}",
)

tasks = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks"))
gpu_tasks = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_tasks"))
two_requested = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested"))
two_active = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active"))
two_used = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used"))
realpath_requested = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested"))
realpath_trust = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust"))
realpath_used = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used"))
gpu_minscore_requested = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_requested"))
gpu_minscore_active = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_active"))
gpu_minscore_hot = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot"))
gpu_minscore_used = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used"))
require(tasks > 0, "expected positive task count")
require(tasks == expected_tasks, f"tasks != expected_tasks: {tasks} vs {expected_tasks}")
require(gpu_tasks == tasks, f"gpu_tasks != tasks: {gpu_tasks} vs {tasks}")
require(two_requested > 0 and two_active == two_requested, "two-contract bridge must be active")
require(two_used == tasks, f"two_contract_used != tasks: {two_used} vs {tasks}")
require(realpath_requested > 0 and realpath_trust > 0, "realpath trust must be active")
require(realpath_used == tasks, f"realpath_used != tasks: {realpath_used} vs {tasks}")
require(gpu_minscore_requested > 0 and gpu_minscore_active == gpu_minscore_requested, "GPU minScore must be active")
require(gpu_minscore_hot == gpu_minscore_requested, "hot GPU minScore must be active")
require(gpu_minscore_used == tasks, f"gpu_minscore_used != tasks: {gpu_minscore_used} vs {tasks}")
for key in (
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_score_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_min_score_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds",
):
    require(num(key) == 0.0, f"expected {key}=0, got {bench.get(key)}")
require(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority")
    == "external_digest_gate",
    "expected external_digest_gate authority",
)
require(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_error") == "none",
    "unexpected two-contract error",
)
require(
    bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_error") == "none",
    "unexpected GPU minScore error",
)
gpu_scoreinfo_groups = int(num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups"))
require(
    gpu_scoreinfo_groups == expected_gpu_scoreinfo_groups,
    f"gpu_scoreinfo_groups != expected: {gpu_scoreinfo_groups} vs {expected_gpu_scoreinfo_groups}",
)
for key in (
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_wall_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_kernel_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds",
):
    require(num(key) > 0.0, f"expected positive {key}, got {bench.get(key)}")

positive_probe_keys = []
for key, value in bench.items():
    if "probe" not in key.lower():
        continue
    if isinstance(value, bool):
        continue
    if isinstance(value, (int, float)) and value > 0:
        positive_probe_keys.append((key, value))
require(not positive_probe_keys, f"probe telemetry was active in no-probe runtime: {positive_probe_keys[:8]}")

candidate_vs_baseline = baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0
summary = {
    "label": "malat1_full" if case_label == "full" else f"malat1_first{record_limit}",
    "schema": output_mode,
    "rows": expected_rows,
    "digest": candidate.get("merged_digest"),
    "baseline_wall_seconds": baseline_wall,
    "candidate_wall_seconds": candidate_wall,
    "candidate_vs_baseline": candidate_vs_baseline,
    "tasks": tasks,
    "two_contract_used": two_used,
    "realpath_used": realpath_used,
    "gpu_minscore_used": gpu_minscore_used,
    "gpu_scoreinfo_groups": gpu_scoreinfo_groups,
    "two_contract_total_seconds": num("fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds"),
    "gpu_minscore_wall_seconds": num("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_wall_seconds"),
    "realpath_extend_seconds": num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds"),
    "realpath_extend_align_seconds": num("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds"),
    "probe_positive_numeric_keys": 0,
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"label={summary['label']}")
print(f"schema={summary['schema']}")
print(f"rows={summary['rows']}")
print(f"digest={summary['digest']}")
print(f"baseline_wall_seconds={baseline_wall:.6f}")
print(f"candidate_wall_seconds={candidate_wall:.6f}")
print(f"candidate_vs_baseline={candidate_vs_baseline:.6f}")
print(f"tasks={tasks}")
print(f"two_contract_used={two_used}")
print(f"realpath_used={realpath_used}")
print(f"gpu_minscore_used={gpu_minscore_used}")
print(f"gpu_scoreinfo_groups={summary['gpu_scoreinfo_groups']}")
print(f"two_contract_total_seconds={summary['two_contract_total_seconds']:.6f}")
print(f"gpu_minscore_wall_seconds={summary['gpu_minscore_wall_seconds']:.6f}")
print(f"realpath_extend_seconds={summary['realpath_extend_seconds']:.6f}")
print(f"realpath_extend_align_seconds={summary['realpath_extend_align_seconds']:.6f}")
print("probe_positive_numeric_keys=0")
PY
}

rm -rf "$WORK"
mkdir -p "$WORK"
if [[ "$CHECK_FULL" == "1" && "$RECORD_LIMIT" != "670" ]]; then
  run_case full 670 98713 200400 3561123
else
  if [[ "$CHECK_FULL" == "1" ]]; then
    run_case full "$RECORD_LIMIT" "$EXPECTED_ROWS" 200400 3561123
  else
    if [[ "$RECORD_LIMIT" != "8" || "$EXPECTED_ROWS" != "796" ]]; then
      echo "custom MALAT1_RECORD_LIMIT/EXPECTED_ROWS requires an explicit CHECK_* preset" >&2
      exit 1
    fi
    run_case "first${RECORD_LIMIT}" "$RECORD_LIMIT" "$EXPECTED_ROWS" 1824 31272
  fi
fi
if [[ "$CHECK_FIRST64" == "1" && "$RECORD_LIMIT" != "64" ]]; then
  run_case first64 64 9741 18096 319280
fi
if [[ "$CHECK_FIRST128" == "1" && "$RECORD_LIMIT" != "128" ]]; then
  run_case first128 128 22531 40128 715473
fi
if [[ "$CHECK_FIRST256" == "1" && "$RECORD_LIMIT" != "256" ]]; then
  run_case first256 256 42504 80640 1434844
fi

echo "ok"
