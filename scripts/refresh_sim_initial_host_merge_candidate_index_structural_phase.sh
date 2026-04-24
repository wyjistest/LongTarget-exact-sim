#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage: scripts/refresh_sim_initial_host_merge_candidate_index_structural_phase.sh \
  --profile-mode-ab-summary PATH \
  --candidate-index-lifecycle-summary PATH \
  --terminal-telemetry-classification-decision PATH \
  --state-update-bookkeeping-classification-decision PATH \
  --branch-rollup-decision PATH \
  --output-root DIR
EOF
}

die() {
  echo "$*" >&2
  exit 1
}

PROFILE_MODE_AB_SUMMARY=""
CANDIDATE_INDEX_LIFECYCLE_SUMMARY=""
TERMINAL_TELEMETRY_CLASSIFICATION_DECISION=""
STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION=""
BRANCH_ROLLUP_DECISION=""
OUTPUT_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile-mode-ab-summary)
      PROFILE_MODE_AB_SUMMARY="$2"
      shift 2
      ;;
    --candidate-index-lifecycle-summary)
      CANDIDATE_INDEX_LIFECYCLE_SUMMARY="$2"
      shift 2
      ;;
    --terminal-telemetry-classification-decision)
      TERMINAL_TELEMETRY_CLASSIFICATION_DECISION="$2"
      shift 2
      ;;
    --state-update-bookkeeping-classification-decision)
      STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION="$2"
      shift 2
      ;;
    --branch-rollup-decision)
      BRANCH_ROLLUP_DECISION="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$PROFILE_MODE_AB_SUMMARY" ]] || { usage >&2; die "--profile-mode-ab-summary is required"; }
[[ -n "$CANDIDATE_INDEX_LIFECYCLE_SUMMARY" ]] || { usage >&2; die "--candidate-index-lifecycle-summary is required"; }
[[ -n "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" ]] || { usage >&2; die "--terminal-telemetry-classification-decision is required"; }
[[ -n "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" ]] || { usage >&2; die "--state-update-bookkeeping-classification-decision is required"; }
[[ -n "$BRANCH_ROLLUP_DECISION" ]] || { usage >&2; die "--branch-rollup-decision is required"; }
[[ -n "$OUTPUT_ROOT" ]] || { usage >&2; die "--output-root is required"; }

for required_path in \
  "$PROFILE_MODE_AB_SUMMARY" \
  "$CANDIDATE_INDEX_LIFECYCLE_SUMMARY" \
  "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  "$BRANCH_ROLLUP_DECISION"
do
  [[ -f "$required_path" ]] || die "missing input file: $required_path"
done

mkdir -p "$OUTPUT_ROOT"
OUTPUT_ROOT=$(cd "$OUTPUT_ROOT" && pwd)

OPERATION_ROLLUP_DIR="$OUTPUT_ROOT/candidate_index_operation_rollup"
COMMON_MEMORY_DIR="$OUTPUT_ROOT/candidate_index_common_memory_behavior"
STRUCTURAL_PHASE_DIR="$OUTPUT_ROOT/candidate_index_structural_phase"
REFRESHED_BRANCH_ROLLUP_DIR="$OUTPUT_ROOT/branch_rollup"

python3 scripts/summarize_sim_initial_host_merge_candidate_index_operation_rollup.py \
  --profile-mode-ab-summary "$PROFILE_MODE_AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$CANDIDATE_INDEX_LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  --output-dir "$OPERATION_ROLLUP_DIR"

python3 scripts/summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.py \
  --candidate-index-lifecycle-summary "$CANDIDATE_INDEX_LIFECYCLE_SUMMARY" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DIR/candidate_index_operation_rollup_decision.json" \
  --output-dir "$COMMON_MEMORY_DIR"

python3 scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py \
  --branch-rollup-decision "$BRANCH_ROLLUP_DECISION" \
  --candidate-index-operation-rollup-decision "$OPERATION_ROLLUP_DIR/candidate_index_operation_rollup_decision.json" \
  --candidate-index-common-memory-behavior-decision "$COMMON_MEMORY_DIR/candidate_index_common_memory_behavior_decision.json" \
  --output-dir "$STRUCTURAL_PHASE_DIR"

python3 scripts/summarize_sim_initial_host_merge_profile_branch_rollup.py \
  --profile-mode-ab-summary "$PROFILE_MODE_AB_SUMMARY" \
  --candidate-index-lifecycle-summary "$CANDIDATE_INDEX_LIFECYCLE_SUMMARY" \
  --terminal-telemetry-classification-decision "$TERMINAL_TELEMETRY_CLASSIFICATION_DECISION" \
  --state-update-bookkeeping-classification-decision "$STATE_UPDATE_BOOKKEEPING_CLASSIFICATION_DECISION" \
  --candidate-index-structural-phase-decision "$STRUCTURAL_PHASE_DIR/candidate_index_structural_phase_decision.json" \
  --output-dir "$REFRESHED_BRANCH_ROLLUP_DIR"
