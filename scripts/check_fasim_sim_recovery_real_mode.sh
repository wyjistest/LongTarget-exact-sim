#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_real_mode"
mkdir -p "$WORK"

FASIM_SIM_RECOVERY=1 FASIM_SIM_RECOVERY_VALIDATE=1 PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_gap_taxonomy.py" \
  --bin "$BIN" \
  --profile-set smoke \
  --require-sim-gap-taxonomy \
  --sim-recovery \
  --sim-recovery-validate \
  --sim-recovery-output "$WORK/sim_close.lite" \
  --sim-recovery-report "$WORK/sim_close_report.md" \
  --output "$WORK/smoke_taxonomy.md" \
  --work-dir "$WORK" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery\.total\.requested=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.active=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.validate_enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.output_digest_available=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.output_records=10$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.recall_vs_sim=100\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.precision_vs_sim=90\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.extra_vs_sim=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.overlap_conflicts=4$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery\.total\.output_mutations_fast_mode=0$' "$WORK/smoke.log"
grep -q '^Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability$' "$WORK/sim_close.lite"
