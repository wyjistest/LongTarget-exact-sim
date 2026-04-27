#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-device-ordered-shadow-cost-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

VALIDATION_PASSED="$WORK/validation_passed.json"
cat >"$VALIDATION_PASSED" <<'EOF'
{
  "phase": "device_side_ordered_candidate_maintenance_shadow_validation",
  "shadow_validation_status": "passed",
  "runtime_prototype_allowed": false,
  "default_path_changes_allowed": false,
  "enabled_workload_count": 1,
  "total_shadow_case_count": 4,
  "total_shadow_summary_count": 1000,
  "total_shadow_mismatch_count": 0,
  "digest_mismatch_workload_count": 0
}
EOF

VALIDATION_MISMATCH="$WORK/validation_mismatch.json"
cat >"$VALIDATION_MISMATCH" <<'EOF'
{
  "phase": "device_side_ordered_candidate_maintenance_shadow_validation",
  "shadow_validation_status": "mismatch",
  "runtime_prototype_allowed": false,
  "default_path_changes_allowed": false,
  "enabled_workload_count": 1,
  "total_shadow_case_count": 4,
  "total_shadow_summary_count": 1000,
  "total_shadow_mismatch_count": 1,
  "digest_mismatch_workload_count": 0
}
EOF

write_case() {
  local path="$1"
  local workload="$2"
  local mode="$3"
  local shadow_enabled="$4"
  local shadow_validate_enabled="$5"
  local total_seconds="$6"
  local sim_seconds="$7"
  local host_seconds="$8"
  local shadow_seconds="$9"
  local summary_count="${10}"
  local mismatch_count="${11}"
  cat >"$path" <<EOF
{
  "workload_id": "${workload}",
  "workload_class": "synthetic",
  "shadow_cost_mode": "${mode}",
  "total_seconds": ${total_seconds},
  "sim_seconds": ${sim_seconds},
  "sim_initial_scan_cpu_merge_seconds": ${host_seconds},
  "sim_ordered_maintenance_shadow_enabled": ${shadow_enabled},
  "sim_ordered_maintenance_shadow_validate_enabled": ${shadow_validate_enabled},
  "sim_ordered_maintenance_shadow_status": "ran",
  "sim_ordered_maintenance_shadow_case_count": 4,
  "sim_ordered_maintenance_shadow_summary_count": ${summary_count},
  "sim_ordered_maintenance_shadow_event_count": ${summary_count},
  "sim_ordered_maintenance_shadow_mismatch_count": ${mismatch_count},
  "sim_ordered_maintenance_shadow_seconds": ${shadow_seconds},
  "sim_ordered_maintenance_shadow_host_cpu_merge_seconds": ${host_seconds},
  "sim_ordered_maintenance_estimated_cpu_merge_seconds_avoidable": ${host_seconds},
  "sim_ordered_maintenance_estimated_d2h_bytes_avoided": 1048576
}
EOF
}

write_case "$WORK/design_baseline.json" "design_case" "baseline" 0 0 20.0 12.0 10.0 0.0 1000 0
write_case "$WORK/design_shadow_no_validate.json" "design_case" "shadow_no_validate" 1 0 34.0 24.0 10.0 14.0 1000 0
write_case "$WORK/design_shadow_validate.json" "design_case" "shadow_validate" 1 1 35.0 25.0 10.0 15.0 1000 0

OUT_DESIGN="$WORK/design"
python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_cost.py \
  --shadow-validation-decision "$VALIDATION_PASSED" \
  --cost-telemetry "$WORK/design_baseline.json" \
  --cost-telemetry "$WORK/design_shadow_no_validate.json" \
  --cost-telemetry "$WORK/design_shadow_validate.json" \
  --output-dir "$OUT_DESIGN"

python3 - <<'PY' "$OUT_DESIGN/device_ordered_maintenance_shadow_cost_decision.json" "$OUT_DESIGN/device_ordered_maintenance_shadow_cost_summary.json" "$OUT_DESIGN/device_ordered_maintenance_shadow_cost_cases.tsv" "$OUT_DESIGN/device_ordered_maintenance_shadow_cost.md"
import csv
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
summary = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
rows = list(csv.DictReader(Path(sys.argv[3]).open(encoding="utf-8"), delimiter="\t"))
markdown = Path(sys.argv[4]).read_text(encoding="utf-8")

assert decision["shadow_cost_status"] == "ready", decision
assert decision["recommended_next_action"] == "design_device_shadow_kernel", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert decision["default_path_changes_allowed"] is False, decision
assert abs(decision["shadow_vs_host_cpu_merge_ratio"] - 1.5) < 1e-9, decision
assert summary["aggregate"]["shadow_validate_workload_count"] == 1, summary
assert len(rows) == 3, rows
assert "recommended_next_action: `design_device_shadow_kernel`" in markdown, markdown
PY

write_case "$WORK/breakdown_baseline.json" "breakdown_case" "baseline" 0 0 20.0 12.0 10.0 0.0 1000 0
write_case "$WORK/breakdown_shadow_no_validate.json" "breakdown_case" "shadow_no_validate" 1 0 48.0 38.0 10.0 28.0 1000 0
write_case "$WORK/breakdown_shadow_validate.json" "breakdown_case" "shadow_validate" 1 1 50.0 40.0 10.0 30.0 1000 0

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_cost.py \
  --shadow-validation-decision "$VALIDATION_PASSED" \
  --cost-telemetry "$WORK/breakdown_baseline.json" \
  --cost-telemetry "$WORK/breakdown_shadow_no_validate.json" \
  --cost-telemetry "$WORK/breakdown_shadow_validate.json" \
  --output-dir "$WORK/breakdown"

python3 - <<'PY' "$WORK/breakdown/device_ordered_maintenance_shadow_cost_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_cost_status"] == "cost_breakdown_needed", decision
assert decision["recommended_next_action"] == "profile_shadow_cost_breakdown", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

write_case "$WORK/stop_baseline.json" "stop_case" "baseline" 0 0 20.0 12.0 10.0 0.0 1000 0
write_case "$WORK/stop_shadow_validate.json" "stop_case" "shadow_validate" 1 1 92.0 82.0 10.0 80.0 1000 0

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_cost.py \
  --shadow-validation-decision "$VALIDATION_PASSED" \
  --cost-telemetry "$WORK/stop_baseline.json" \
  --cost-telemetry "$WORK/stop_shadow_validate.json" \
  --output-dir "$WORK/stop"

python3 - <<'PY' "$WORK/stop/device_ordered_maintenance_shadow_cost_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_cost_status"] == "too_expensive", decision
assert decision["recommended_next_action"] == "stop_device_ordered_shadow", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_cost.py \
  --shadow-validation-decision "$VALIDATION_MISMATCH" \
  --cost-telemetry "$WORK/design_shadow_validate.json" \
  --output-dir "$WORK/validation_mismatch"

python3 - <<'PY' "$WORK/validation_mismatch/device_ordered_maintenance_shadow_cost_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_cost_status"] == "validation_not_passed", decision
assert decision["recommended_next_action"] == "debug_shadow_mismatch", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

echo "check_summarize_longtarget_device_ordered_maintenance_shadow_cost: PASS"
