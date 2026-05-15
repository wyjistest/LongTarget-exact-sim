#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_model"
DATASET="$WORK/learned_detector_dataset.tsv"
mkdir -p "$WORK"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_validate "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_validate \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --learned-detector-dataset "$DATASET" \
  --learned-detector-dataset-report \
  --report-title "Fasim SIM-Close Learned Detector Dataset" \
  --base-branch fasim-sim-recovery-score-landscape-detector-shadow \
  --output "$WORK/dataset_report.md" \
  --work-dir "$WORK/work"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_model.py" \
  --dataset "$DATASET" \
  --output "$WORK/model_report.md" | tee "$WORK/model.log"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.enabled=1$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.candidate_rows=[1-9][0-9]*$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.positive_rows=[1-9][0-9]*$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.learnable_two_class=[01]$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.model_topn_recall=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.model_topn_precision=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.model_topn_recall_vs_sim=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.candidate_oracle_recall_vs_sim=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.candidate_oracle_precision=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.guard_policy_shadow_enabled=1$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.guard_policy_shadow_policies=[1-9][0-9]*$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.guard_policy_shadow_current_guard_recall_vs_sim=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.guard_policy_shadow_accept_all_executor_recall_vs_sim=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.guard_policy_shadow_best_non_oracle_recall_vs_sim=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.guard_policy_shadow_best_non_oracle_precision=[0-9]+\.[0-9]{6}$' "$WORK/model.log"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model\.total\.production_model=0$' "$WORK/model.log"
grep -q '## Learned Detector Model Shadow' "$WORK/model_report.md"
grep -q 'diagnostic-only offline model shadow' "$WORK/model_report.md"
grep -q '## Interpretation' "$WORK/model_report.md"
grep -q '## Guard Policy Shadow' "$WORK/model_report.md"
grep -q '## Guard Policy By Workload' "$WORK/model_report.md"
grep -q '| accept_all_executor |' "$WORK/model_report.md"
grep -q '| score_nt_rank5 |' "$WORK/model_report.md"
grep -q '| relaxed_score_nt_rank10 |' "$WORK/model_report.md"
grep -q 'candidate_oracle_*' "$WORK/model_report.md"
grep -q 'Do not use this model for production selection.' "$WORK/model_report.md"
