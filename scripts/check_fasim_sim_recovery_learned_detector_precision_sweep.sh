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

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_precision_sweep_check"
REPORT="$WORK/precision_sweep_report.md"
LOG="$WORK/precision_sweep.log"
DOC_REPORT="$ROOT/docs/fasim_sim_recovery_learned_detector_precision_sweep.md"
mkdir -p "$WORK"

BIN="$BIN" "$ROOT/scripts/check_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.sh" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_precision_sweep.py" \
  --dataset "$NEGATIVE_DATASET" \
  --source-dataset "$SOURCE_DATASET" \
  --data-expansion-log "$DATA_LOG" \
  --report "$REPORT" \
  --doc-report "$DOC_REPORT" | tee "$LOG"

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.enabled=1$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.positive_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.negative_rows=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.workload_count=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.hard_negative_source_count=[1-9][0-9]*$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.evaluation_policy=workload_heldout$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.train_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.train_negative=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.validation_positive=[0-9]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.validation_negative=[0-9]+$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.workload_heldout_degenerate=0$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.sweep_threshold_count=[1-9][0-9]*$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.current_guard_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.current_guard_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.learned_shadow_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.learned_shadow_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.max_recall_at_precision_90=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.max_recall_at_precision_95=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.max_recall_at_precision_99=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.threshold_at_precision_90=(-?[0-9.]+|none)$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.hybrid_or_precision_90_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.hybrid_or_precision_90_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.hybrid_and_precision_90_recall=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.hybrid_and_precision_90_precision=[0-9.]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.false_positives_by_negative_source=[A-Za-z0-9_.:,|=-]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.false_negatives_by_workload=[A-Za-z0-9_.:,|=-]+$' "$LOG"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.decision=[A-Za-z0-9_]+$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.production_model=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.sim_labels_runtime_inputs=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.runtime_behavior_changed=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.model_training_added=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.deep_learning_dependency=0$' "$LOG"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_precision_sweep\.total\.recommended_default_sim_close=0$' "$LOG"

grep -q '## Precision-Constrained Threshold Sweep' "$REPORT"
grep -q '## Precision Targets' "$REPORT"
grep -q '## Hybrid Policies' "$REPORT"
grep -q '## Error Attribution' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
grep -q 'Recommended/default SIM-close: no' "$REPORT"
grep -q '## Precision-Constrained Threshold Sweep' "$DOC_REPORT"
