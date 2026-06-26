#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase7_candidate_coverage"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-cpu-authority-candidate-coverage-plan \
  >"$WORK/candidate_coverage_plan.log"
make -C "$ROOT" check-fasim-gasal2-cpu-authority-candidate-coverage-env \
  >"$WORK/candidate_coverage_env.log"
make -C "$ROOT" check-fasim-gasal2-cpu-authority-candidate-coverage-characterization \
  >"$WORK/candidate_coverage_characterization.log"
make -C "$ROOT" check-fasim-gasal2-cpu-authority-candidate-coverage-runtime-smoke \
  WORK="$WORK/runtime_smoke" \
  >"$WORK/candidate_coverage_runtime_smoke.log"
make -C "$ROOT" check-fasim-gasal2-cpu-authority-candidate-coverage-runtime-smoke \
  WORK="$WORK/runtime_smoke_selected_only" \
  SELECTED_ONLY_COVERAGE=1 \
  >"$WORK/candidate_coverage_runtime_smoke_selected_only.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/candidate_coverage_plan.log" "ok"
require_line "$WORK/candidate_coverage_env.log" "ok"
require_line "$WORK/candidate_coverage_characterization.log" "ok"
require_line "$WORK/candidate_coverage_runtime_smoke.log" "candidate_coverage_false_negative_scoreinfos=0"
require_line "$WORK/candidate_coverage_runtime_smoke_selected_only.log" "candidate_coverage_false_negative_scoreinfos=0"

candidate_align_attempts="$(
  awk -F= '$1 == "candidate_coverage_candidate_align_attempts" { print $2 }' \
    "$WORK/candidate_coverage_runtime_smoke.log"
)"
reference_align_attempts="$(
  awk -F= '$1 == "candidate_coverage_reference_align_attempts" { print $2 }' \
    "$WORK/candidate_coverage_runtime_smoke.log"
)"
selected_candidate_attempts="$(
  awk -F= '$1 == "candidate_coverage_candidate_attempts" { print $2 }' \
    "$WORK/candidate_coverage_runtime_smoke_selected_only.log"
)"
selected_candidate_align_attempts="$(
  awk -F= '$1 == "candidate_coverage_candidate_align_attempts" { print $2 }' \
    "$WORK/candidate_coverage_runtime_smoke_selected_only.log"
)"
selected_reference_align_attempts="$(
  awk -F= '$1 == "candidate_coverage_reference_align_attempts" { print $2 }' \
    "$WORK/candidate_coverage_runtime_smoke_selected_only.log"
)"

python3 - \
  "$candidate_align_attempts" \
  "$reference_align_attempts" \
  "$selected_candidate_attempts" \
  "$selected_candidate_align_attempts" \
  "$selected_reference_align_attempts" <<'PY'
import sys

candidate = int(sys.argv[1])
reference = int(sys.argv[2])
selected_candidates = int(sys.argv[3])
selected_candidate = int(sys.argv[4])
selected_reference = int(sys.argv[5])
if min(candidate, reference, selected_candidates, selected_candidate, selected_reference) <= 0:
    raise SystemExit(
        "candidate coverage counts must be positive, got "
        f"candidate={candidate} reference={reference} "
        f"selected_candidates={selected_candidates} "
        f"selected_candidate={selected_candidate} selected_reference={selected_reference}"
    )
if candidate != reference:
    raise SystemExit(
        "current prefix bounded smoke is expected to show no same-scope align reduction: "
        f"candidate={candidate} reference={reference}"
    )
if selected_candidate != selected_reference:
    raise SystemExit(
        "current selected-only bounded smoke is expected to show no same-scope align reduction: "
        f"candidate={selected_candidate} reference={selected_reference}"
    )
PY

echo "phase7_candidate_coverage_gate=defined_not_completion"
echo "candidate_coverage_plan=pass"
echo "candidate_coverage_env=pass"
echo "candidate_coverage_characterization=pass"
echo "candidate_coverage_runtime_smoke=pass"
echo "candidate_coverage_smoke_false_negative_scoreinfos=0"
echo "candidate_coverage_smoke_candidate_align_attempts=$candidate_align_attempts"
echo "candidate_coverage_smoke_reference_align_attempts=$reference_align_attempts"
echo "candidate_coverage_selected_only_runtime_smoke=pass"
echo "candidate_coverage_selected_only_false_negative_scoreinfos=0"
echo "candidate_coverage_selected_only_candidate_attempts=$selected_candidate_attempts"
echo "candidate_coverage_selected_only_candidate_align_attempts=$selected_candidate_align_attempts"
echo "candidate_coverage_selected_only_reference_align_attempts=$selected_reference_align_attempts"
echo "candidate_coverage_current_decision=coverage_clean_no_align_reduction"
echo "cpu_aligner_align_authority=1"
echo "gasal2_output_authority=0"
echo "requires_false_negative_scoreinfos_zero=1"
echo "requires_cpu_align_attempt_reduction=1"
echo "broad_objective_status=open"
echo "must_not_call_update_goal_complete=1"
echo "ok"
