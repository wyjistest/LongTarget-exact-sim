#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_real_corpus_validation_coverage"
mkdir -p "$WORK"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_smoke "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_smoke \
  --repeat 2 \
  --validation-coverage-report \
  --report-title "Fasim SIM-Close Recovery Real-Corpus Validation Coverage" \
  --base-branch fasim-sim-recovery-real-corpus-characterization \
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.validate_supported_cases=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.validate_supported_records_median=9\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.sim_records_median=9\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.shared_records_median=9\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.sim_only_records_median=9\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.sim_close_extra_records_median=1\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.recall_vs_sim_median=100\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.precision_vs_sim_median=90\.000000$' "$WORK/smoke.log"
grep -q '| coverage_report | yes |' "$WORK/smoke_report.md"
grep -q 'validate_unsupported_reason' "$WORK/smoke_report.md"
grep -q 'SIM labels used as production input: no' "$WORK/smoke_report.md"
