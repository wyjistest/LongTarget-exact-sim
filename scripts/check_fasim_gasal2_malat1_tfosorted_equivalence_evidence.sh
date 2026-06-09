#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh"
COMPARE="$ROOT/scripts/compare_fasim_lite_full_equivalence.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence"}"
BUILD_BIN="${BUILD_BIN:-1}"
RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
EXPECTED_ROWS="${EXPECTED_ROWS:-796}"
CHECK_FIRST64="${CHECK_FIRST64:-0}"
CHECK_FULL="${CHECK_FULL:-0}"
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-1}"
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
case "$REPLAY_PROBE_MAX_TASKS" in
  ''|*[!0-9]*)
    echo "REPLAY_PROBE_MAX_TASKS must be a non-negative integer, got: $REPLAY_PROBE_MAX_TASKS" >&2
    exit 1
    ;;
esac
case "$CHECK_FIRST64" in
  0|1)
    ;;
  *)
    echo "CHECK_FIRST64 must be 0 or 1, got: $CHECK_FIRST64" >&2
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

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
for path in "$WRAPPER" "$COMPARE" "$RNA_INPUT" "$DNA_INPUT"; do
  if [[ ! -s "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

run_case() {
  local label="$1"
  local record_limit="$2"
  local expected_rows="$3"
  local expected_tasks="$4"
  local case_work="$WORK/$label"

  rm -rf "$case_work"
  mkdir -p "$case_work/inputs"
  local sample="$case_work/inputs/malat1_${label}.fa"
  awk -v limit="$record_limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$DNA_INPUT" >"$sample"
  if [[ ! -s "$sample" ]]; then
    echo "empty MALAT1 sample for $label" >&2
    exit 1
  fi

  "$WRAPPER" \
    --fasim-bin "$BIN" \
    --target "$sample" \
    --rna "$RNA_INPUT" \
    --work-dir "$case_work/audit" \
    --workers 1 \
    --output-mode tfosorted \
    --replay-probe-max-tasks "$REPLAY_PROBE_MAX_TASKS" \
    --force \
    >"$case_work/fresh.json"

  python3 "$COMPARE" \
    --baseline-report "$case_work/audit/baseline.report.json" \
    --candidate-report "$case_work/audit/candidate.report.json" \
    >"$case_work/compare.txt"

  grep -q '^schema=tfosorted$' "$case_work/compare.txt"
  grep -q "^baseline_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q "^candidate_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q "^baseline_unique_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q "^candidate_unique_rows=$expected_rows$" "$case_work/compare.txt"
  grep -q '^missing_rows=0$' "$case_work/compare.txt"
  grep -q '^extra_rows=0$' "$case_work/compare.txt"
  grep -q '^full_rows_equal=true$' "$case_work/compare.txt"

  python3 - "$case_work/fresh.json" "$case_work/audit/baseline.report.json" "$case_work/audit/candidate.report.json" "$expected_rows" "$record_limit" "$expected_tasks" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
baseline = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
candidate = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
expected_rows = int(sys.argv[4])
record_limit = int(sys.argv[5])
expected_tasks = int(sys.argv[6])

if summary.get("audited_status") != "accepted":
    raise SystemExit(f"unexpected audited_status={summary.get('audited_status')}")
if summary.get("baseline_digest") != summary.get("candidate_digest"):
    raise SystemExit("summary digest mismatch")
if summary.get("merged_records") != expected_rows:
    raise SystemExit(
        f"summary merged_records mismatch: {summary.get('merged_records')} vs {expected_rows}"
    )
if summary.get("result_contract") != "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1":
    raise SystemExit(f"unexpected result_contract={summary.get('result_contract')}")
if summary.get("trust_profile") != "malat1_like_two_contract_group32_experimental_v1":
    raise SystemExit(f"unexpected trust_profile={summary.get('trust_profile')}")
if summary.get("group_target_records") != 32:
    raise SystemExit(f"unexpected group_target_records={summary.get('group_target_records')}")
expected_shards = (record_limit + 31) // 32
if summary.get("shard_count") != expected_shards:
    raise SystemExit(
        f"unexpected shard_count={summary.get('shard_count')} expected={expected_shards}"
    )
if summary.get("tasks", 0) <= 0:
    raise SystemExit("expected positive task count")
if summary.get("tasks") != expected_tasks:
    raise SystemExit(f"unexpected tasks={summary.get('tasks')} expected={expected_tasks}")
if summary.get("two_contract_used") != summary.get("tasks"):
    raise SystemExit("two_contract_used must equal tasks")
if summary.get("realpath_used") != summary.get("tasks"):
    raise SystemExit("realpath_used must equal tasks")
for key in (
    "two_contract_fallbacks",
    "two_contract_score_mismatches",
    "two_contract_min_score_mismatches",
    "two_contract_scoreinfo_mismatches",
    "realpath_fallbacks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks",
):
    if summary.get(key) != 0:
        raise SystemExit(f"expected {key}=0, got {summary.get(key)}")
for label, report in (("baseline", baseline), ("candidate", candidate)):
    if report.get("run_status") != "completed":
        raise SystemExit(f"{label}: run_status={report.get('run_status')}")
    if report.get("output_mode") != "tfosorted":
        raise SystemExit(f"{label}: output_mode={report.get('output_mode')}")
    if report.get("merged_records") != expected_rows:
        raise SystemExit(
            f"{label}: merged_records={report.get('merged_records')} expected={expected_rows}"
        )
    output = str(report.get("merged_output", ""))
    if not output.endswith("merged-TFOsorted"):
        raise SystemExit(f"{label}: unexpected merged_output={output}")
if baseline.get("merged_digest") != candidate.get("merged_digest"):
    raise SystemExit("report digest mismatch")
PY
}

rm -rf "$WORK"
mkdir -p "$WORK"
if [[ "$CHECK_FULL" == "1" ]]; then
  if [[ "$RECORD_LIMIT" != "670" || "$EXPECTED_ROWS" != "98713" ]]; then
    echo "CHECK_FULL requires MALAT1_RECORD_LIMIT=670 and EXPECTED_ROWS=98713" >&2
    exit 1
  fi
  run_case full 670 98713 200400
else
  if [[ "$RECORD_LIMIT" != "8" || "$EXPECTED_ROWS" != "796" ]]; then
    echo "custom MALAT1_RECORD_LIMIT/EXPECTED_ROWS requires an explicit CHECK_* preset" >&2
    exit 1
  fi
  run_case "first${RECORD_LIMIT}" "$RECORD_LIMIT" "$EXPECTED_ROWS" 1824
fi
if [[ "$CHECK_FIRST64" == "1" && "$RECORD_LIMIT" != "64" ]]; then
  run_case first64 64 9741 18096
fi

echo "ok"
