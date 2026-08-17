#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_segment_ownership"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
KCNQ_SUMMARY="${KCNQ_SUMMARY:-"$ROOT/.tmp/characterize_fasim_segment_ownership_kcnq1ot1_max4_shift0_20260715/summary.txt"}"
DOC="$ROOT/docs/fasim_gasal2_segment_ownership.md"
GOAL="$ROOT/goal.md"

metric() {
  local path="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$path"
}

for path in "$ROOT/H19.fa" "$ROOT/testDNA.fa" "$DOC" "$GOAL"; do
  if [[ ! -f "$path" ]]; then
    echo "missing Phase 2 dependency: $path" >&2
    exit 1
  fi
done
if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$ROOT/tests/check_fasim_segment_ownership.py" >"$WORK/ownership_tests.log" 2>&1
python3 "$ROOT/tests/check_compare_fasim_segmented_contract.py" >"$WORK/comparator_tests.log" 2>&1
python3 "$ROOT/tests/check_characterize_fasim_segment_ownership_h19_runner.py" >"$WORK/h19_runner_tests.log" 2>&1
python3 "$ROOT/tests/check_characterize_fasim_gasal2_segmented_archive_first_runner.py" >"$WORK/segmented_runner_tests.log" 2>&1

env \
  BIN="$BIN" \
  WORK="$WORK/h19" \
  TARGET="$ROOT/testDNA.fa" \
  RNA="$ROOT/H19.fa" \
  SEGMENT_LEN=2048 \
  SEGMENT_OVERLAP=512 \
  GRID_SHIFTS='0 128 256' \
  FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=1 \
  python3 "$ROOT/scripts/characterize_fasim_segment_ownership_h19.py" \
  >"$WORK/h19.log"

summary="$WORK/h19/summary.txt"
decision="$(metric "$summary" phase2_decision)"
hard_gate="$(metric "$summary" hard_gate_pass)"
promotion_gate="$(metric "$summary" promotion_gate_pass)"
runtime_work_dropped="$(metric "$summary" runtime_work_dropped)"
potential_exact="$(metric "$summary" potential_exact_tasks_removed)"
potential_tracebacks="$(metric "$summary" potential_tracebacks_removed)"
grid_implication="$(metric "$summary" grid_stability_implies_unsegmented_equivalence)"
shift_count="$(metric "$summary" grid_shift_count)"
short_missing="$(metric "$summary" short_oracle_missing_rows)"
short_extra="$(metric "$summary" short_oracle_extra_rows)"
all_three="$(metric "$summary" all_three_top5_equal)"

evidence_complete=0
if [[ "$runtime_work_dropped" == "0" && "$potential_exact" == "unavailable" && \
      "$potential_tracebacks" == "unavailable" && "$grid_implication" == "0" && \
      "$shift_count" -ge 3 ]]; then
  if [[ "$decision" == "pass" && "$hard_gate" == "1" && "$promotion_gate" == "1" ]]; then
    evidence_complete=1
  elif [[ "$decision" == "no_go" && "$promotion_gate" == "0" ]]; then
    if [[ "$hard_gate" == "1" ]] || \
       [[ "$hard_gate" == "0" && \
          ( "$short_missing" -gt 0 || "$short_extra" -gt 0 || "$all_three" == "0" ) ]]; then
      evidence_complete=1
    fi
  fi
fi

kcnq_receipt_available=0
kcnq_receipt_consistent=0
if [[ -f "$KCNQ_SUMMARY" ]]; then
  kcnq_receipt_available=1
  if [[ "$(metric "$KCNQ_SUMMARY" rows_total)" == "932168" && \
        "$(metric "$KCNQ_SUMMARY" rows_unique)" == "631258" && \
        "$(metric "$KCNQ_SUMMARY" rows_owned)" == "599940" && \
        "$(metric "$KCNQ_SUMMARY" rows_no_owner)" == "0" && \
        "$(metric "$KCNQ_SUMMARY" rows_owner_mismatch_vs_authority)" == "31318" && \
        "$(metric "$KCNQ_SUMMARY" potential_row_reduction_percent)" == "35.64" && \
        "$(metric "$KCNQ_SUMMARY" potential_exact_tasks_removed)" == "unavailable" && \
        "$(metric "$KCNQ_SUMMARY" potential_tracebacks_removed)" == "unavailable" && \
        "$(metric "$KCNQ_SUMMARY" runtime_work_dropped)" == "0" ]]; then
    kcnq_receipt_consistent=1
  fi
fi

doc_consistent=0
if grep -Fq 'Phase 2 is `no_go`' "$DOC" && \
   grep -Fq 'grid stability != unsegmented equivalence' "$DOC" && \
   grep -Fq 'potential_row_reduction_percent=35.64' "$DOC" && \
   grep -Fq 'potential_exact_tasks_removed=unavailable' "$DOC" && \
   grep -Fq 'runtime_work_dropped=0' "$DOC"; then
  doc_consistent=1
fi

goal_consistent=0
active_phase="$(awk -F' = ' '$1 == "active_phase" {print $2; exit}' "$GOAL")"
last_completed_phase="$(awk -F' = ' '$1 == "last_completed_phase" {print $2; exit}' "$GOAL")"
active_phase_complete=0
if [[ "$active_phase" == "complete" ]]; then
  active_phase_complete=1
fi
if grep -Fq 'phase_2_status = no_go' "$GOAL" && \
   { [[ "$active_phase_complete" == "1" ]] || \
     { [[ "$active_phase" =~ ^[0-9]+$ ]] && (( active_phase >= 3 )); }; } && \
   [[ "$last_completed_phase" =~ ^[0-9]+$ ]] && (( last_completed_phase >= 2 )); then
  goal_consistent=1
fi

make_target_present=0
if grep -Fq 'check-fasim-gasal2-segment-ownership:' "$ROOT/Makefile"; then
  make_target_present=1
fi

phase2_gate=fail
if [[ "$evidence_complete" == "1" && "$doc_consistent" == "1" && \
      "$goal_consistent" == "1" && "$make_target_present" == "1" && \
      ( "$kcnq_receipt_available" == "0" || "$kcnq_receipt_consistent" == "1" ) ]]; then
  phase2_gate="$decision"
fi

{
  printf 'phase2_decision=%s\n' "$decision"
  printf 'hard_gate_pass=%s\n' "$hard_gate"
  printf 'promotion_gate_pass=%s\n' "$promotion_gate"
  printf 'short_oracle_missing_rows=%s\n' "$short_missing"
  printf 'short_oracle_extra_rows=%s\n' "$short_extra"
  printf 'all_three_top5_equal=%s\n' "$all_three"
  printf 'grid_shift_count=%s\n' "$shift_count"
  printf 'runtime_work_dropped=%s\n' "$runtime_work_dropped"
  printf 'potential_exact_tasks_removed=%s\n' "$potential_exact"
  printf 'potential_tracebacks_removed=%s\n' "$potential_tracebacks"
  printf 'evidence_complete=%s\n' "$evidence_complete"
  printf 'kcnq_receipt_available=%s\n' "$kcnq_receipt_available"
  printf 'kcnq_receipt_consistent=%s\n' "$kcnq_receipt_consistent"
  printf 'doc_consistent=%s\n' "$doc_consistent"
  printf 'goal_consistent=%s\n' "$goal_consistent"
  printf 'make_target_present=%s\n' "$make_target_present"
  printf 'phase2_gate=%s\n' "$phase2_gate"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
if [[ "$phase2_gate" != "pass" && "$phase2_gate" != "no_go" ]]; then
  echo "Fasim GASAL2 segment ownership Phase 2 gate failed" >&2
  exit 1
fi
echo "Fasim GASAL2 segment ownership Phase 2 evidence complete: $phase2_gate"
