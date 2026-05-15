#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_model_shadow_check"
SOURCE_DATASET="$WORK/learned_detector_dataset.tsv"
NEGATIVE_DATASET="$WORK/negative_dataset.tsv"
NEGATIVE_REPORT="$WORK/negative_dataset_report.md"
REPORT="$WORK/model_shadow_report.md"
LOG="$WORK/model_shadow.log"
mkdir -p "$WORK"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_validate "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_validate \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --learned-detector-dataset "$SOURCE_DATASET" \
  --learned-detector-dataset-report \
  --report-title "Fasim SIM-Close Learned Detector Dataset" \
  --base-branch fasim-sim-recovery-learned-detector-model-shadow \
  --output "$WORK/dataset_report.md" \
  --work-dir "$WORK/dataset_work" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py" \
  --dataset "$SOURCE_DATASET" \
  --output-tsv "$NEGATIVE_DATASET" \
  --report "$NEGATIVE_REPORT" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_model_shadow.py" \
  --dataset "$NEGATIVE_DATASET" \
  --source-dataset "$SOURCE_DATASET" \
  --report "$REPORT" | tee "$LOG"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.enabled=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.positive_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.negative_rows=[1-9][0-9]*$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.evaluation_mode=heldout_split$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_positive=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_negative=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.selected_threshold=-?[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_false_positives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_false_negatives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_candidate_eligible_selected=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_candidate_eligible_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_candidate_eligible_false_negative_vs_all_positives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.validation_target_rows=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.beats_current_guard_on_validation=[01]$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.production_model=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.sim_labels_runtime_inputs=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_model_shadow\.total\.runtime_behavior_changed=0$' "$LOG"
grep -q '## Held-out Validation' "$REPORT"
grep -q '## Target Row Audit' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
