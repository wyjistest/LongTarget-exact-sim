#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_gap_taxonomy.py" \
  --bin "$BIN" \
  --profile-set smoke \
  --require-sim-gap-taxonomy \
  --sim-recovery-output "$ROOT/.tmp/fasim_sim_gap_taxonomy/sim_close.lite" \
  --sim-recovery-report "$ROOT/.tmp/fasim_sim_gap_taxonomy/sim_recovery_report.md" \
  --output "$ROOT/.tmp/fasim_sim_gap_taxonomy/smoke_report.md" \
  --work-dir "$ROOT/.tmp/fasim_sim_gap_taxonomy"
