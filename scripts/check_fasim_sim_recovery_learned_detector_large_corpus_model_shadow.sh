#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

EXPANSION_WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_large_corpus_expansion_check"
SOURCE_DATASET="$EXPANSION_WORK/learned_detector_dataset.tsv"
NEGATIVE_DATASET="$EXPANSION_WORK/negative_dataset.tsv"
DATA_LOG="$EXPANSION_WORK/real_corpus_hard_negatives.log"

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_large_corpus_model_shadow_check"
REPORT="$WORK/large_corpus_model_shadow_report.md"
LOG="$WORK/large_corpus_model_shadow.log"
DOC_REPORT="$ROOT/docs/fasim_sim_recovery_learned_detector_large_corpus_model_shadow.md"
mkdir -p "$WORK"

BIN="$BIN" "$ROOT/scripts/check_fasim_sim_recovery_learned_detector_large_corpus_expansion.sh" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.py" \
  --dataset "$NEGATIVE_DATASET" \
  --source-dataset "$SOURCE_DATASET" \
  --data-expansion-log "$DATA_LOG" \
  --report "$REPORT" \
  --doc-report "$DOC_REPORT" | tee "$LOG"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.enabled=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.positive_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.negative_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.workload_count=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.validate_supported_workload_count=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.hard_negative_source_count=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.train_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.train_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.validation_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.validation_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.workload_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.family_heldout_degenerate=[01]$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.current_guard_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.current_guard_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.learned_shadow_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.learned_shadow_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.candidate_eligible_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.candidate_eligible_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.false_positives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.false_negatives=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.false_positives_by_negative_source=[A-Za-z0-9_.:,|=-]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.false_negatives_by_workload=[A-Za-z0-9_.:,|=-]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.selected_threshold=-?[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.decision=[A-Za-z0-9_]+$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.production_model=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.sim_labels_runtime_inputs=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.runtime_behavior_changed=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.model_training_added=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.deep_learning_dependency=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_large_corpus_model_shadow\.total\.recommended_default_sim_close=0$' "$LOG"

grep -q '## Large Corpus Model Shadow' "$REPORT"
grep -q '## Split Evaluation' "$REPORT"
grep -q '## Negative-Source Held-Out' "$REPORT"
grep -q '## Leave-One-Workload-Out' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
grep -q 'Recommended/default SIM-close: no' "$REPORT"
grep -q '## Large Corpus Model Shadow' "$DOC_REPORT"
