#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_malat1_lite_equivalence_evidence"}"
COMPARE="$ROOT/scripts/compare_fasim_lite_full_equivalence.py"

mkdir -p "$WORK"

run_case() {
  local label="$1"
  local baseline_report="$2"
  local candidate_report="$3"
  local expected_rows="$4"
  local out="$WORK/${label}.txt"

  if [[ ! -s "$baseline_report" || ! -s "$candidate_report" ]]; then
    echo "missing report pair for $label" >&2
    echo "baseline=$baseline_report" >&2
    echo "candidate=$candidate_report" >&2
    return 1
  fi

  python3 "$COMPARE" \
    --baseline-report "$baseline_report" \
    --candidate-report "$candidate_report" \
    >"$out"

  grep -q '^schema=lite$' "$out"
  grep -q "^baseline_rows=$expected_rows$" "$out"
  grep -q "^candidate_rows=$expected_rows$" "$out"
  grep -q '^missing_rows=0$' "$out"
  grep -q '^extra_rows=0$' "$out"
  grep -q '^full_rows_equal=true$' "$out"
}

run_case \
  malat1_first8 \
  "$ROOT/.tmp/characterize_two_contract_hot_smoke/malat1_first8/baseline/report.json" \
  "$ROOT/.tmp/characterize_two_contract_hot_smoke/malat1_first8/candidate/report.json" \
  796

run_case \
  malat1_first64 \
  "$ROOT/.tmp/characterize_two_contract_hot_malat1_64_group32/malat1_first64/baseline/report.json" \
  "$ROOT/.tmp/characterize_two_contract_hot_malat1_64_group32/malat1_first64/candidate/report.json" \
  9741

run_case \
  malat1_full_group32_two_contract \
  "$ROOT/.tmp/characterize_two_contract_hot_malat1_full_group32/malat1_first670/baseline/report.json" \
  "$ROOT/.tmp/characterize_two_contract_hot_malat1_full_group32/malat1_first670/candidate/report.json" \
  98713

run_case \
  malat1_full_group32_trust \
  "$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups/group_32/malat1_first670/baseline/report.json" \
  "$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups/group_32/malat1_first670/candidate/report.json" \
  98713

run_case \
  malat1_current_audited_first256 \
  "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real/audit/baseline/report.json" \
  "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real/audit/candidate/report.json" \
  42504

echo "ok"
