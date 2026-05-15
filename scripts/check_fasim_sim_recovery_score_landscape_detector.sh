#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_score_landscape_detector"
mkdir -p "$WORK"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_validate "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_validate \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --score-landscape-detector-shadow \
  --report-title "Fasim SIM-Close Score-Landscape Detector Shadow" \
  --base-branch fasim-sim-recovery-real-corpus-validation-matrix \
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_score_landscape_detector\.total\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_score_landscape_detector\.total\.output_mutations=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_score_landscape_detector\.tiny_validate\.baseline_current\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_score_landscape_detector\.tiny_validate\.combined_score_landscape_detector\.enabled=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_score_landscape_detector\.tiny_validate\.combined_detector_relaxed_guard\.enabled=1$' "$WORK/smoke.log"
grep -q '| score_landscape_detector_shadow | yes |' "$WORK/smoke_report.md"
grep -q '## Score-Landscape Detector Shadow' "$WORK/smoke_report.md"
grep -q 'score-landscape/local-max detector shadow is diagnostic-only' "$WORK/smoke_report.md"
grep -q 'Do not recommend or default SIM-close mode from this PR.' "$WORK/smoke_report.md"
