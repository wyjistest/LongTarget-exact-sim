#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_expanded_model_shadow_check"
SOURCE_DATASET="$WORK/expanded_learned_detector_dataset.tsv"
NEGATIVE_DATASET="$WORK/expanded_negative_dataset.tsv"
NEGATIVE_REPORT="$WORK/expanded_negative_dataset_report.md"
PREVIOUS_SOURCE_DATASET="$WORK/previous_learned_detector_dataset.tsv"
PREVIOUS_NEGATIVE_DATASET="$WORK/previous_negative_dataset.tsv"
PREVIOUS_NEGATIVE_REPORT="$WORK/previous_negative_dataset_report.md"
PREVIOUS_REPORT="$WORK/previous_model_shadow_report.md"
PREVIOUS_LOG="$WORK/previous_model_shadow.log"
REPORT="$WORK/expanded_model_shadow_report.md"
LOG="$WORK/expanded_model_shadow.log"
DOC_REPORT="$ROOT/docs/fasim_sim_recovery_learned_detector_expanded_model_shadow.md"
mkdir -p "$WORK"

MARMOSET_ROOT="${FASIM_SIM_RECOVERY_LEARNED_DETECTOR_MARMOSET_ROOT:-/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset}"
MARMOSET_59006_DNA="$MARMOSET_ROOT/ENSG00000259006.1_marmoset-targetDNA/ENSG00000259006.1_marmoset-44344695-44349695.fa"
MARMOSET_59006_RNA="$MARMOSET_ROOT/ENSG00000259006.1_marmoset/marmoset_chr20_ENSG00000259006.1_RP11-566K11.4.fa"
MARMOSET_33639_DNA="$MARMOSET_ROOT/ENSG00000233639.1_marmoset-targetDNA/ENSG00000233639.1_marmoset-9489642-9494642.fa"
MARMOSET_33639_RNA="$MARMOSET_ROOT/ENSG00000233639.1_marmoset/marmoset_chr14_ENSG00000233639.1_AC018730.1.fa"
MARMOSET_NO_LEGACY_DNA="$MARMOSET_ROOT/ENSG00000229743.2_marmoset-targetDNA/ENSCJAG00000018089-90232548-90237548.fa"
MARMOSET_NO_LEGACY_RNA="$MARMOSET_ROOT/ENSG00000229743.2_marmoset/marmoset_chr14_ENSG00000229743.2_AC018730.3.fa"
MARMOSET_CASES_AVAILABLE=0
if [[ -f "$MARMOSET_59006_DNA" \
  && -f "$MARMOSET_59006_RNA" \
  && -f "$MARMOSET_33639_DNA" \
  && -f "$MARMOSET_33639_RNA" \
  && -f "$MARMOSET_NO_LEGACY_DNA" \
  && -f "$MARMOSET_NO_LEGACY_RNA" ]]; then
  MARMOSET_CASES_AVAILABLE=1
fi

CASE_ARGS=(
  --case tiny_validate "$ROOT/testDNA.fa" "$ROOT/H19.fa"
  --validate-case tiny_validate
)
if [[ "$MARMOSET_CASES_AVAILABLE" == "1" ]]; then
  CASE_ARGS+=(
    --case marmoset_59006 "$MARMOSET_59006_DNA" "$MARMOSET_59006_RNA"
    --validate-case marmoset_59006
    --case marmoset_33639 "$MARMOSET_33639_DNA" "$MARMOSET_33639_RNA"
    --validate-case marmoset_33639
    --case marmoset_29743_no_legacy "$MARMOSET_NO_LEGACY_DNA" "$MARMOSET_NO_LEGACY_RNA"
    --validate-case marmoset_29743_no_legacy
  )
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  "${CASE_ARGS[@]}" \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --learned-detector-dataset "$SOURCE_DATASET" \
  --learned-detector-dataset-report \
  --report-title "Fasim SIM-Close Learned Detector Expanded Dataset" \
  --base-branch fasim-sim-recovery-learned-detector-corpus-expansion \
  --output "$WORK/expanded_dataset_report.md" \
  --work-dir "$WORK/expanded_dataset_work" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py" \
  --dataset "$SOURCE_DATASET" \
  --output-tsv "$NEGATIVE_DATASET" \
  --report "$NEGATIVE_REPORT" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  --case tiny_validate "$ROOT/testDNA.fa" "$ROOT/H19.fa" \
  --validate-case tiny_validate \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --learned-detector-dataset "$PREVIOUS_SOURCE_DATASET" \
  --learned-detector-dataset-report \
  --report-title "Fasim SIM-Close Learned Detector Previous Dataset" \
  --base-branch fasim-sim-recovery-learned-detector-model-shadow \
  --output "$WORK/previous_dataset_report.md" \
  --work-dir "$WORK/previous_dataset_work" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py" \
  --dataset "$PREVIOUS_SOURCE_DATASET" \
  --output-tsv "$PREVIOUS_NEGATIVE_DATASET" \
  --report "$PREVIOUS_NEGATIVE_REPORT" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_model_shadow.py" \
  --dataset "$PREVIOUS_NEGATIVE_DATASET" \
  --source-dataset "$PREVIOUS_SOURCE_DATASET" \
  --report "$PREVIOUS_REPORT" | tee "$PREVIOUS_LOG" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_model_shadow.py" \
  --dataset "$NEGATIVE_DATASET" \
  --source-dataset "$SOURCE_DATASET" \
  --previous-model-shadow-log "$PREVIOUS_LOG" \
  --report "$REPORT" \
  --doc-report "$DOC_REPORT" | tee "$LOG"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.enabled=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.positive_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.negative_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.hard_negative_source_count=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.train_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.train_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.validation_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.validation_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.workload_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.family_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.current_guard_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.current_guard_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.learned_shadow_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.learned_shadow_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.false_positives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.false_negatives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.selected_threshold=-?[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.candidate_eligible_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.candidate_eligible_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.previous_small_dataset_learned_shadow_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.previous_small_dataset_learned_shadow_precision=[0-9.]+$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.production_model=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.sim_labels_runtime_inputs=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.runtime_behavior_changed=0$' "$LOG"

if [[ "$MARMOSET_CASES_AVAILABLE" == "1" ]]; then
  grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.expanded_corpus_available=1$' "$LOG"
  grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.evaluation_policy=workload_heldout$' "$LOG"
  grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_model_shadow\.total\.workload_heldout_degenerate=0$' "$LOG"
fi

grep -q '## Expanded Corpus Model Shadow' "$REPORT"
grep -q '## Split Evaluation' "$REPORT"
grep -q '## Previous Small-Dataset Shadow Comparison' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
grep -q 'Recommended/default SIM-close: no' "$REPORT"

grep -q '## Expanded Corpus Model Shadow' "$DOC_REPORT"
