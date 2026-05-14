#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

FASIM_SIM_RECOVERY_RISK_DETECTOR=1 PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_gap_taxonomy.py" \
  --bin "$BIN" \
  --profile-set smoke \
  --require-sim-gap-taxonomy \
  --risk-detector \
  --risk-detector-output "$ROOT/.tmp/fasim_sim_recovery_risk_detector/smoke_report.md" \
  --output "$ROOT/.tmp/fasim_sim_recovery_risk_detector/smoke_taxonomy.md" \
  --work-dir "$ROOT/.tmp/fasim_sim_recovery_risk_detector"
