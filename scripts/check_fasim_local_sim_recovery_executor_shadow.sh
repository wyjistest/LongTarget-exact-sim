#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_local_sim_recovery_executor_shadow"
mkdir -p "$WORK"

FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_gap_taxonomy.py" \
  --bin "$BIN" \
  --profile-set smoke \
  --require-sim-gap-taxonomy \
  --risk-detector \
  --executor-shadow \
  --executor-shadow-output "$WORK/smoke_report.md" \
  --risk-detector-output "$WORK/smoke_risk_detector.md" \
  --output "$WORK/smoke_taxonomy.md" \
  --work-dir "$WORK" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_executor_shadow\.total\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_executor_shadow\.total\.recovered_records=9$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_executor_shadow\.total\.output_mutations=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_executor_shadow\.total\.executor_failures=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_executor_shadow\.total\.unsupported_boxes=0$' "$WORK/smoke.log"
