#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_real_corpus_validation_matrix"
mkdir -p "$WORK"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_validate "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --case tiny_footprint "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_validate \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --validation-matrix-report \
  --report-title "Fasim SIM-Close Recovery Real-Corpus Validation Matrix" \
  --base-branch fasim-sim-recovery-real-corpus-recall-repair \
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.cases=2$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.validate_supported_cases=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.unsupported_cases=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.high_recall_high_precision_cases=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.precision_clean_recall_low_cases=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.sim_records=9$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.shared_records=9$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_validation_matrix\.missed_records=0$' "$WORK/smoke.log"
grep -q '| validation_matrix_report | yes |' "$WORK/smoke_report.md"
grep -q '## Validation Matrix' "$WORK/smoke_report.md"
grep -q 'precision-clean / recall-low' "$WORK/smoke_report.md"
grep -q 'Do not recommend or default SIM-close mode from this PR.' "$WORK/smoke_report.md"
