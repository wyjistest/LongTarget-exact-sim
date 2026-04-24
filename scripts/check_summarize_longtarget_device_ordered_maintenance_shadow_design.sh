#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-device-ordered-shadow-design-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

OUT_DIR="$WORK/out"
ORDERED_DECISION="$WORK/ordered_candidate_maintenance_budget_decision.json"

cat >"$ORDERED_DECISION" <<'EOF'
{
  "decision_status": "ready",
  "phase": "device_side_ordered_candidate_maintenance_budget",
  "telemetry_status": "closed",
  "device_side_ordered_candidate_maintenance_feasibility": "plausible",
  "recommended_next_action": "design_device_side_ordered_candidate_maintenance_shadow",
  "runtime_prototype_allowed": false,
  "aggregate": {
    "ordered_shape_confidence": "coarse",
    "inter_state_machine_parallelism": 48.0,
    "estimated_cpu_merge_seconds_avoidable": 117.128172
  }
}
EOF

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_design.py \
  --ordered-maintenance-budget-decision "$ORDERED_DECISION" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/device_ordered_maintenance_shadow_design.json" "$OUT_DIR/device_ordered_maintenance_shadow_design.md"
import json
import sys
from pathlib import Path

design = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
markdown = Path(sys.argv[2]).read_text(encoding="utf-8")

assert design["decision_status"] == "ready", design
assert design["phase"] == "device_side_ordered_candidate_maintenance_shadow_design", design
assert design["shadow_design_status"] == "ready_for_opt_in_shadow_implementation", design
assert design["recommended_next_action"] == "implement_opt_in_device_ordered_maintenance_shadow", design
assert design["runtime_prototype_allowed"] is False, design
assert design["default_path_changes_allowed"] is False, design
assert design["input_contract"] == "row_run_summaries_ordered", design
assert design["ordering_contract"] == "preserve_original_summary_order", design
assert "unordered_key_summary" in design["forbidden_transforms"], design
assert "victim_slot_reorder" in design["forbidden_transforms"], design
assert "lazy_generation_index" in design["forbidden_transforms"], design
assert "floor_update_skip" in design["forbidden_transforms"], design
assert "final_candidate_state_hash" in design["required_validation_hashes"], design
assert "replacement_sequence_hash" in design["required_validation_hashes"], design
assert "running_min_update_sequence_hash" in design["required_validation_hashes"], design
assert "safe_store_state_hash" in design["required_validation_hashes"], design
assert "LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW" in design["opt_in_environment_flags"], design
assert "LONGTARGET_SIM_DEVICE_ORDERED_MAINTENANCE_SHADOW_VALIDATE" in design["opt_in_environment_flags"], design
assert "runtime_prototype_allowed: `false`" in markdown, markdown
assert "default_path_changes_allowed: `false`" in markdown, markdown
PY

INACTIVE_DECISION="$WORK/inactive_ordered_candidate_maintenance_budget_decision.json"
cat >"$INACTIVE_DECISION" <<'EOF'
{
  "decision_status": "ready",
  "phase": "device_side_ordered_candidate_maintenance_budget",
  "telemetry_status": "closed",
  "device_side_ordered_candidate_maintenance_feasibility": "weak",
  "recommended_next_action": "refine_ordered_maintenance_shape_telemetry",
  "runtime_prototype_allowed": false
}
EOF

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_design.py \
  --ordered-maintenance-budget-decision "$INACTIVE_DECISION" \
  --output-dir "$OUT_DIR/inactive"

python3 - <<'PY' "$OUT_DIR/inactive/device_ordered_maintenance_shadow_design.json"
import json
import sys
from pathlib import Path

design = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert design["decision_status"] == "inactive", design
assert design["shadow_design_status"] == "blocked_by_phase3b_decision", design
assert design["recommended_next_action"] == "return_to_ordered_candidate_maintenance_budget", design
assert design["runtime_prototype_allowed"] is False, design
assert design["default_path_changes_allowed"] is False, design
PY

echo "check_summarize_longtarget_device_ordered_maintenance_shadow_design: PASS"
