#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_real_corpus_characterization"
mkdir -p "$WORK"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_smoke "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_smoke \
  --repeat 2 \
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.cases=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.repeat=2$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.fast_digest_stable=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.sim_close_digest_stable=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.validate_selection_stable=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.fast_mode_output_mutations=0$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.boxes_median=6\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.cells_median=95812\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.cell_fraction_median=0\.780406$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.recovered_candidates_median=20\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.recovered_accepted_median=10\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.fasim_suppressed_median=6\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.sim_close_output_records_median=10\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.recall_vs_sim_median=100\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.precision_vs_sim_median=90\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.extra_vs_sim_median=1\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.overlap_conflicts_median=4\.000000$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_real_corpus\.total\.recommendation=experimental_opt_in$' "$WORK/smoke.log"
grep -q 'SIM labels used as production input: no' "$WORK/smoke_report.md"
