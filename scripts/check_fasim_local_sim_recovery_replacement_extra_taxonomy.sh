#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy"
mkdir -p "$WORK"

FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 FASIM_SIM_RECOVERY_INTEGRATION_SHADOW=1 FASIM_SIM_RECOVERY_FILTER_SHADOW=1 FASIM_SIM_RECOVERY_REPLACEMENT_SHADOW=1 FASIM_SIM_RECOVERY_REPLACEMENT_EXTRA_TAXONOMY=1 PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_gap_taxonomy.py" \
  --bin "$BIN" \
  --profile-set smoke \
  --require-sim-gap-taxonomy \
  --risk-detector \
  --executor-shadow \
  --integration-shadow \
  --filter-shadow \
  --replacement-shadow \
  --replacement-extra-taxonomy \
  --executor-shadow-output "$WORK/smoke_executor_report.md" \
  --integration-shadow-output "$WORK/smoke_integration_report.md" \
  --filter-shadow-output "$WORK/smoke_filter_report.md" \
  --replacement-shadow-output "$WORK/smoke_replacement_report.md" \
  --replacement-extra-taxonomy-output "$WORK/smoke_report.md" \
  --risk-detector-output "$WORK/smoke_risk_detector.md" \
  --output "$WORK/smoke_taxonomy.md" \
  --work-dir "$WORK" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_extra_taxonomy\.total\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_extra_taxonomy\.total\.output_mutations=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_extra_taxonomy\.total\.true_sim_records=9$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_extra_taxonomy\.total\.extra_records=4$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_extra_taxonomy\.guard\.combined_non_oracle\.output_mutations=0$' "$WORK/smoke.log"
