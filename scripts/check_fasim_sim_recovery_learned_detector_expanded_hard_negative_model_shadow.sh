#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow_check"
SOURCE_DATASET="$WORK/learned_detector_dataset.tsv"
NEGATIVE_DATASET="$WORK/negative_dataset.tsv"
NEGATIVE_REPORT="$WORK/negative_dataset_report.md"
MANIFEST="$WORK/marmoset_extra_cases.tsv"
DATA_REPORT="$WORK/real_corpus_hard_negatives_report.md"
DATA_LOG="$WORK/real_corpus_hard_negatives.log"
REPORT="$WORK/expanded_hard_negative_model_shadow_report.md"
LOG="$WORK/expanded_hard_negative_model_shadow.log"
DOC_REPORT="$ROOT/docs/fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.md"
mkdir -p "$WORK"

MARMOSET_ROOT="${FASIM_SIM_RECOVERY_LEARNED_DETECTOR_MARMOSET_ROOT:-/data/wenyujianData/humanLncAtlas/wenyujian/inputForShenzhen-marmoset}"
EXTRA_LIMIT="${FASIM_SIM_RECOVERY_LEARNED_DETECTOR_EXTRA_MARMOSET_LIMIT:-9}"
EXTRA_MIN_RNA_BYTES="${FASIM_SIM_RECOVERY_LEARNED_DETECTOR_EXTRA_MARMOSET_MIN_RNA_BYTES:-700}"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.py" \
  --discover-marmoset-root "$MARMOSET_ROOT" \
  --extra-marmoset-limit "$EXTRA_LIMIT" \
  --extra-marmoset-min-rna-bytes "$EXTRA_MIN_RNA_BYTES" \
  --write-manifest "$MANIFEST" >/dev/null

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

if [[ -s "$MANIFEST" ]]; then
  while IFS=$'\t' read -r label dna rna gene dna_bytes rna_bytes; do
    if [[ "$label" == "label" ]]; then
      continue
    fi
    CASE_ARGS+=(--case "$label" "$dna" "$rna" --validate-case "$label")
  done < "$MANIFEST"
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py" \
  --bin "$BIN" \
  "${CASE_ARGS[@]}" \
  --repeat 1 \
  --validation-coverage-report \
  --miss-taxonomy-report \
  --learned-detector-dataset "$SOURCE_DATASET" \
  --learned-detector-dataset-report \
  --report-title "Fasim SIM-Close Learned Detector Expanded Hard-Negative Shadow Dataset" \
  --base-branch fasim-sim-recovery-learned-detector-real-corpus-hard-negatives \
  --output "$WORK/dataset_report.md" \
  --work-dir "$WORK/dataset_work" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py" \
  --dataset "$SOURCE_DATASET" \
  --output-tsv "$NEGATIVE_DATASET" \
  --report "$NEGATIVE_REPORT" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.py" \
  --discover-marmoset-root "$MARMOSET_ROOT" \
  --extra-marmoset-limit "$EXTRA_LIMIT" \
  --extra-marmoset-min-rna-bytes "$EXTRA_MIN_RNA_BYTES" \
  --write-manifest "$MANIFEST" \
  --manifest "$MANIFEST" \
  --source-dataset "$SOURCE_DATASET" \
  --dataset "$NEGATIVE_DATASET" \
  --negative-dataset-report "$NEGATIVE_REPORT" \
  --report "$DATA_REPORT" | tee "$DATA_LOG" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.py" \
  --dataset "$NEGATIVE_DATASET" \
  --source-dataset "$SOURCE_DATASET" \
  --data-expansion-log "$DATA_LOG" \
  --report "$REPORT" \
  --doc-report "$DOC_REPORT" | tee "$LOG"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.enabled=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.positive_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.negative_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.workload_count=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.validate_supported_workload_count=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.hard_negative_source_count=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.train_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.train_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.validation_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.validation_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.workload_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.family_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.current_guard_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.current_guard_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.learned_shadow_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.learned_shadow_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.candidate_eligible_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.candidate_eligible_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.false_positives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.false_negatives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.false_positives_by_negative_source=[A-Za-z0-9_.:,|=-]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.false_negatives_by_workload=[A-Za-z0-9_.:,|=-]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.selected_threshold=-?[0-9.]+$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.production_model=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.sim_labels_runtime_inputs=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.runtime_behavior_changed=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow\.total\.deep_learning_dependency=0$' "$LOG"

grep -q '## Expanded Hard-Negative Model Shadow' "$REPORT"
grep -q '## Split Evaluation' "$REPORT"
grep -q '## Negative-Source Held-Out' "$REPORT"
grep -q '## Leave-One-Workload-Out' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
grep -q 'Recommended/default SIM-close: no' "$REPORT"
grep -q '## Expanded Hard-Negative Model Shadow' "$DOC_REPORT"
