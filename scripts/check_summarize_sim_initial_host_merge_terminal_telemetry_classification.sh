#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-terminal-telemetry-classify-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

write_summary() {
  local path="$1"
  local candidate_index_seconds="$2"
  local terminal_parent_seconds="$3"
  local telemetry_overhead_seconds="$4"
  local profile_mode="$5"
  local requested_mode="$6"
  local effective_mode="$7"
  cat >"$path" <<EOF
{
  "decision_status": "ready",
  "candidate_index_materiality_status": "material",
  "profile_mode_overhead_status": "ok",
  "trusted_span_timing": true,
  "trusted_span_source": "sampled",
  "runtime_prototype_allowed": false,
  "profile_mode": "${profile_mode}",
  "candidate_index": {
    "profile_mode": "${profile_mode}",
    "terminal_telemetry_overhead_mode_requested": "${requested_mode}",
    "terminal_telemetry_overhead_mode_effective": "${effective_mode}",
    "seconds": ${candidate_index_seconds},
    "terminal_path_parent_seconds": ${terminal_parent_seconds},
    "terminal_path_telemetry_overhead_seconds": ${telemetry_overhead_seconds},
    "terminal_path_telemetry_overhead_share_of_candidate_index": 0.125
  },
  "cases": [
    {
      "case_id": "case-1",
      "workload_id": "wl-1",
      "profile_mode": "${profile_mode}",
      "terminal_telemetry_overhead_mode_requested": "${requested_mode}",
      "terminal_telemetry_overhead_mode_effective": "${effective_mode}",
      "full_set_miss_count": 12,
      "candidate_index_lookup_count": 100,
      "candidate_index_insert_count": 7,
      "candidate_index_erase_count": 7,
      "terminal_path_event_count": 12,
      "terminal_path_candidate_slot_write_count": 12,
      "terminal_path_start_index_write_count": 12,
      "terminal_path_state_update_count": 12
    }
  ]
}
EOF
}

assert_ready_decision() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "terminal_telemetry_classification_decision.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "terminal_telemetry_classification_summary.json").read_text(encoding="utf-8"))

assert decision["current_branch"] == "terminal_path_telemetry_overhead", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert decision["telemetry_branch_kind"] == "profiler_only_overhead", decision
assert decision["recommended_next_action"] == "reduce_or_cold_path_profiler_telemetry", decision
assert summary["decision_status"] == "ready", summary
assert summary["with_terminal_telemetry_mode_effective"] == "on", summary
assert summary["without_terminal_telemetry_mode_effective"] == "off", summary
assert summary["terminal_telemetry_mode_status"] == "matched", summary
assert summary["off_equivalence_status"] == "matched", summary
assert summary["forced_off_terminal_telemetry_mode_effective"] == "off", summary
assert abs(float(summary["telemetry_delta_explains_share"]) - 0.9) < 1e-9, summary
PY
}

assert_mode_not_ready() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
decision = json.loads((out_dir / "terminal_telemetry_classification_decision.json").read_text(encoding="utf-8"))
summary = json.loads((out_dir / "terminal_telemetry_classification_summary.json").read_text(encoding="utf-8"))

assert decision["runtime_prototype_allowed"] is False, decision
assert decision["telemetry_branch_kind"] == "unknown", decision
assert decision["recommended_next_action"] == "rerun_with_explicit_terminal_telemetry_modes", decision
assert summary["decision_status"] == "not_ready", summary
assert summary["terminal_telemetry_mode_status"] == "mismatch", summary
PY
}

WITH_SUMMARY="$WORK/with.json"
WITHOUT_SUMMARY="$WORK/without.json"
FORCED_OFF_SUMMARY="$WORK/forced-off.json"
OUT_DIR="$WORK/out"

write_summary "$WITH_SUMMARY" "8.0" "5.0" "1.0" "lexical_first_half_sampled" "on" "on"
write_summary "$WITHOUT_SUMMARY" "7.1" "4.2" "0.1" "lexical_first_half_sampled" "auto" "off"
write_summary "$FORCED_OFF_SUMMARY" "7.1" "4.2" "0.1" "lexical_first_half_sampled_no_terminal_telemetry" "off" "off"

python3 ./scripts/summarize_sim_initial_host_merge_terminal_telemetry_classification.py \
  --with-terminal-telemetry-summary "$WITH_SUMMARY" \
  --without-terminal-telemetry-summary "$WITHOUT_SUMMARY" \
  --forced-off-terminal-telemetry-summary "$FORCED_OFF_SUMMARY" \
  --output-dir "$OUT_DIR"

assert_ready_decision "$OUT_DIR"

MODE_MISMATCH_OUT="$WORK/out-mode-mismatch"
write_summary "$WITH_SUMMARY" "8.0" "5.0" "1.0" "lexical_first_half_sampled" "auto" "off"

python3 ./scripts/summarize_sim_initial_host_merge_terminal_telemetry_classification.py \
  --with-terminal-telemetry-summary "$WITH_SUMMARY" \
  --without-terminal-telemetry-summary "$WITHOUT_SUMMARY" \
  --output-dir "$MODE_MISMATCH_OUT"

assert_mode_not_ready "$MODE_MISMATCH_OUT"

echo "check_summarize_sim_initial_host_merge_terminal_telemetry_classification: PASS"
