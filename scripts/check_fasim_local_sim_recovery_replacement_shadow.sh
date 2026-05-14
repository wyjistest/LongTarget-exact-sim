#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_local_sim_recovery_replacement_shadow"
mkdir -p "$WORK"

FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 FASIM_SIM_RECOVERY_INTEGRATION_SHADOW=1 FASIM_SIM_RECOVERY_FILTER_SHADOW=1 FASIM_SIM_RECOVERY_REPLACEMENT_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_gap_taxonomy.py" \
  --bin "$BIN" \
  --profile-set smoke \
  --require-sim-gap-taxonomy \
  --risk-detector \
  --executor-shadow \
  --integration-shadow \
  --filter-shadow \
  --replacement-shadow \
  --executor-shadow-output "$WORK/smoke_executor_report.md" \
  --integration-shadow-output "$WORK/smoke_integration_report.md" \
  --filter-shadow-output "$WORK/smoke_filter_report.md" \
  --replacement-shadow-output "$WORK/smoke_report.md" \
  --risk-detector-output "$WORK/smoke_risk_detector.md" \
  --output "$WORK/smoke_taxonomy.md" \
  --work-dir "$WORK" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_replacement_shadow\.total\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_replacement_shadow\.total\.output_mutations=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_replacement_shadow\.strategy\.box_local_replacement\.recall_vs_sim=100\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_replacement_shadow\.strategy\.family_replacement\.fasim_records_suppressed=6$' "$WORK/smoke.log"
