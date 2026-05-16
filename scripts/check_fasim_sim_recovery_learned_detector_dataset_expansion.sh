#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion_check"
SOURCE_DATASET="$WORK/learned_detector_dataset.tsv"
NEGATIVE_DATASET="$WORK/negative_dataset.tsv"
NEGATIVE_REPORT="$WORK/negative_dataset_report.md"
REPORT="$WORK/dataset_expansion_report.md"
LOG="$WORK/dataset_expansion.log"
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

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py" \
  --dataset "$NEGATIVE_DATASET" \
  --source-dataset "$SOURCE_DATASET" \
  --report "$REPORT" | tee "$LOG"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.enabled=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.positive_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.negative_rows=[1-9][0-9]*$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.learnable_two_class=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.current_split_train_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.family_heldout_validation_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.workload_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.candidate_eligible_positive_rows=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.requested_negative_source_executor_candidate_non_sim=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.requested_negative_source_extra_vs_sim_candidate=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.requested_negative_source_near_threshold_rejected_candidate=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.requested_negative_source_no_legacy_sim_records_proxy=[0-9]+$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.production_model=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.sim_labels_runtime_inputs=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset_expansion\.total\.runtime_behavior_changed=0$' "$LOG"

grep -q '## Hard Negative Source Audit' "$REPORT"
grep -q '## Split Discipline Audit' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
grep -q 'No unavailable hard-negative rows are fabricated.' "$REPORT"
grep -q 'too small and too narrow for production learned-detector claims' "$REPORT"
