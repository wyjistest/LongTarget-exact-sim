#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-device-ordered-shadow-validation-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

PASSED_TELEMETRY="$WORK/passed_shadow_telemetry.json"
cat >"$PASSED_TELEMETRY" <<'EOF'
{
  "workload_id": "synthetic_shadow_pass",
  "workload_class": "synthetic",
  "sim_ordered_maintenance_shadow_enabled": 1,
  "sim_ordered_maintenance_shadow_validate_enabled": 1,
  "sim_ordered_maintenance_shadow_status": "ran",
  "sim_ordered_maintenance_shadow_case_count": 4,
  "sim_ordered_maintenance_shadow_summary_count": 128,
  "sim_ordered_maintenance_shadow_event_count": 384,
  "sim_ordered_maintenance_shadow_mismatch_count": 0,
  "sim_ordered_maintenance_shadow_first_mismatch_case_id": "none",
  "sim_ordered_maintenance_shadow_first_mismatch_summary_ordinal": 0,
  "sim_ordered_maintenance_shadow_first_mismatch_kind": "none",
  "sim_ordered_maintenance_shadow_seconds": 0.05,
  "sim_ordered_maintenance_shadow_host_cpu_merge_seconds": 0.12,
  "sim_ordered_maintenance_host_final_candidate_state_hash": 101,
  "sim_ordered_maintenance_shadow_final_candidate_state_hash": 101,
  "sim_ordered_maintenance_host_replacement_sequence_hash": 202,
  "sim_ordered_maintenance_shadow_replacement_sequence_hash": 202,
  "sim_ordered_maintenance_host_running_min_sequence_hash": 303,
  "sim_ordered_maintenance_shadow_running_min_sequence_hash": 303,
  "sim_ordered_maintenance_host_candidate_index_visibility_hash": 404,
  "sim_ordered_maintenance_shadow_candidate_index_visibility_hash": 404,
  "sim_ordered_maintenance_host_safe_store_state_hash": 505,
  "sim_ordered_maintenance_shadow_safe_store_state_hash": 505,
  "sim_ordered_maintenance_host_observed_candidate_index_hash": 606,
  "sim_ordered_maintenance_shadow_observed_candidate_index_hash": 606
}
EOF

OUT_DIR="$WORK/passed"
python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_validation.py \
  --shadow-telemetry "$PASSED_TELEMETRY" \
  --output-dir "$OUT_DIR"

python3 - <<'PY' "$OUT_DIR/device_ordered_maintenance_shadow_validation_decision.json" "$OUT_DIR/device_ordered_maintenance_shadow_validation_summary.json" "$OUT_DIR/device_ordered_maintenance_shadow_validation_cases.tsv" "$OUT_DIR/device_ordered_maintenance_shadow_validation.md"
import csv
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
summary = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
rows = list(csv.DictReader(Path(sys.argv[3]).open(encoding="utf-8"), delimiter="\t"))
markdown = Path(sys.argv[4]).read_text(encoding="utf-8")

assert decision["phase"] == "device_side_ordered_candidate_maintenance_shadow_validation", decision
assert decision["shadow_validation_status"] == "passed", decision
assert decision["recommended_next_action"] == "profile_shadow_cost", decision
assert decision["runtime_prototype_allowed"] is False, decision
assert decision["default_path_changes_allowed"] is False, decision
assert summary["enabled_workload_count"] == 1, summary
assert summary["total_shadow_mismatch_count"] == 0, summary
assert rows[0]["workload_id"] == "synthetic_shadow_pass", rows
assert rows[0]["shadow_status"] == "ran", rows
assert "shadow_validation_status: `passed`" in markdown, markdown
PY

MISMATCH_TELEMETRY="$WORK/mismatch_shadow_telemetry.json"
cat >"$MISMATCH_TELEMETRY" <<'EOF'
{
  "workload_id": "synthetic_shadow_mismatch",
  "sim_ordered_maintenance_shadow_enabled": 1,
  "sim_ordered_maintenance_shadow_validate_enabled": 1,
  "sim_ordered_maintenance_shadow_status": "mismatch",
  "sim_ordered_maintenance_shadow_case_count": 1,
  "sim_ordered_maintenance_shadow_summary_count": 12,
  "sim_ordered_maintenance_shadow_event_count": 36,
  "sim_ordered_maintenance_shadow_mismatch_count": 1,
  "sim_ordered_maintenance_shadow_first_mismatch_case_id": "case-1",
  "sim_ordered_maintenance_shadow_first_mismatch_summary_ordinal": 7,
  "sim_ordered_maintenance_shadow_first_mismatch_kind": "replacement_sequence_hash",
  "sim_ordered_maintenance_shadow_seconds": 0.01,
  "sim_ordered_maintenance_shadow_host_cpu_merge_seconds": 0.02,
  "sim_ordered_maintenance_host_final_candidate_state_hash": 101,
  "sim_ordered_maintenance_shadow_final_candidate_state_hash": 999,
  "sim_ordered_maintenance_host_replacement_sequence_hash": 202,
  "sim_ordered_maintenance_shadow_replacement_sequence_hash": 999,
  "sim_ordered_maintenance_host_running_min_sequence_hash": 303,
  "sim_ordered_maintenance_shadow_running_min_sequence_hash": 303,
  "sim_ordered_maintenance_host_candidate_index_visibility_hash": 404,
  "sim_ordered_maintenance_shadow_candidate_index_visibility_hash": 404,
  "sim_ordered_maintenance_host_safe_store_state_hash": 505,
  "sim_ordered_maintenance_shadow_safe_store_state_hash": 505
}
EOF

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_validation.py \
  --shadow-telemetry "$MISMATCH_TELEMETRY" \
  --output-dir "$WORK/mismatch"

python3 - <<'PY' "$WORK/mismatch/device_ordered_maintenance_shadow_validation_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_validation_status"] == "mismatch", decision
assert decision["recommended_next_action"] == "debug_shadow_mismatch", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

DIGEST_MISMATCH_TELEMETRY="$WORK/digest_mismatch_shadow_telemetry.json"
cat >"$DIGEST_MISMATCH_TELEMETRY" <<'EOF'
{
  "workload_id": "synthetic_shadow_digest_mismatch",
  "sim_ordered_maintenance_shadow_enabled": 1,
  "sim_ordered_maintenance_shadow_validate_enabled": 1,
  "sim_ordered_maintenance_shadow_status": "ran",
  "sim_ordered_maintenance_shadow_case_count": 1,
  "sim_ordered_maintenance_shadow_summary_count": 12,
  "sim_ordered_maintenance_shadow_event_count": 36,
  "sim_ordered_maintenance_shadow_mismatch_count": 0,
  "sim_ordered_maintenance_shadow_first_mismatch_case_id": "none",
  "sim_ordered_maintenance_shadow_first_mismatch_summary_ordinal": 0,
  "sim_ordered_maintenance_shadow_first_mismatch_kind": "none",
  "sim_ordered_maintenance_shadow_seconds": 0.01,
  "sim_ordered_maintenance_shadow_host_cpu_merge_seconds": 0.02,
  "sim_ordered_maintenance_host_final_candidate_state_hash": 101,
  "sim_ordered_maintenance_shadow_final_candidate_state_hash": 999,
  "sim_ordered_maintenance_host_replacement_sequence_hash": 202,
  "sim_ordered_maintenance_shadow_replacement_sequence_hash": 202,
  "sim_ordered_maintenance_host_running_min_sequence_hash": 303,
  "sim_ordered_maintenance_shadow_running_min_sequence_hash": 303,
  "sim_ordered_maintenance_host_candidate_index_visibility_hash": 404,
  "sim_ordered_maintenance_shadow_candidate_index_visibility_hash": 404,
  "sim_ordered_maintenance_host_safe_store_state_hash": 505,
  "sim_ordered_maintenance_shadow_safe_store_state_hash": 505
}
EOF

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_validation.py \
  --shadow-telemetry "$DIGEST_MISMATCH_TELEMETRY" \
  --output-dir "$WORK/digest_mismatch"

python3 - <<'PY' "$WORK/digest_mismatch/device_ordered_maintenance_shadow_validation_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_validation_status"] == "mismatch", decision
assert decision["recommended_next_action"] == "debug_shadow_mismatch", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

DISABLED_TELEMETRY="$WORK/disabled_shadow_telemetry.json"
cat >"$DISABLED_TELEMETRY" <<'EOF'
{
  "workload_id": "disabled_shadow",
  "sim_ordered_maintenance_shadow_enabled": 0,
  "sim_ordered_maintenance_shadow_validate_enabled": 0,
  "sim_ordered_maintenance_shadow_status": "disabled",
  "sim_ordered_maintenance_shadow_case_count": 0,
  "sim_ordered_maintenance_shadow_summary_count": 0,
  "sim_ordered_maintenance_shadow_event_count": 0,
  "sim_ordered_maintenance_shadow_mismatch_count": 0,
  "sim_ordered_maintenance_host_final_candidate_state_hash": 0,
  "sim_ordered_maintenance_shadow_final_candidate_state_hash": 0,
  "sim_ordered_maintenance_host_replacement_sequence_hash": 0,
  "sim_ordered_maintenance_shadow_replacement_sequence_hash": 0,
  "sim_ordered_maintenance_host_running_min_sequence_hash": 0,
  "sim_ordered_maintenance_shadow_running_min_sequence_hash": 0,
  "sim_ordered_maintenance_host_candidate_index_visibility_hash": 0,
  "sim_ordered_maintenance_shadow_candidate_index_visibility_hash": 0,
  "sim_ordered_maintenance_host_safe_store_state_hash": 0,
  "sim_ordered_maintenance_shadow_safe_store_state_hash": 0
}
EOF

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_validation.py \
  --shadow-telemetry "$DISABLED_TELEMETRY" \
  --output-dir "$WORK/disabled"

python3 - <<'PY' "$WORK/disabled/device_ordered_maintenance_shadow_validation_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_validation_status"] == "disabled", decision
assert decision["recommended_next_action"] == "enable_shadow_validation", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

INCOMPLETE_TELEMETRY="$WORK/incomplete_shadow_telemetry.json"
cat >"$INCOMPLETE_TELEMETRY" <<'EOF'
{
  "workload_id": "incomplete_shadow",
  "sim_ordered_maintenance_shadow_enabled": 1,
  "sim_ordered_maintenance_shadow_status": "ran"
}
EOF

python3 scripts/summarize_longtarget_device_ordered_maintenance_shadow_validation.py \
  --shadow-telemetry "$INCOMPLETE_TELEMETRY" \
  --output-dir "$WORK/incomplete"

python3 - <<'PY' "$WORK/incomplete/device_ordered_maintenance_shadow_validation_decision.json"
import json
import sys
from pathlib import Path

decision = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert decision["shadow_validation_status"] == "incomplete", decision
assert decision["recommended_next_action"] == "collect_shadow_validation_telemetry", decision
assert decision["runtime_prototype_allowed"] is False, decision
PY

echo "check_summarize_longtarget_device_ordered_maintenance_shadow_validation: PASS"
