#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_negative_dataset"
DATASET="$WORK/learned_detector_dataset.tsv"
NEGATIVE_DATASET="$WORK/negative_dataset.tsv"
REPORT="$WORK/negative_report.md"
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
  --base-branch fasim-sim-recovery-learned-detector-negative-dataset \
  --output "$WORK/dataset_report.md" \
  --work-dir "$WORK/work" >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py" \
  --dataset "$DATASET" \
  --output-tsv "$NEGATIVE_DATASET" \
  --report "$REPORT" | tee "$WORK/negative.log"

test -s "$NEGATIVE_DATASET"
head -n 1 "$NEGATIVE_DATASET" | grep -q $'workload_id\tbox_id\tfamily_id\tcandidate_id'
head -n 1 "$NEGATIVE_DATASET" | grep -q $'\thard_negative_source\t'
head -n 1 "$NEGATIVE_DATASET" | grep -q $'\tlabel\t'
head -n 1 "$NEGATIVE_DATASET" | grep -q $'\tsplit\t'
head -n 1 "$NEGATIVE_DATASET" | grep -q $'\tsplit_key'
tail -n +2 "$NEGATIVE_DATASET" | grep -q $'\t1\t'
tail -n +2 "$NEGATIVE_DATASET" | grep -q $'\t0\t'

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_negative_dataset\.total\.enabled=1$' "$WORK/negative.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_negative_dataset\.total\.positive_rows=[1-9][0-9]*$' "$WORK/negative.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_negative_dataset\.total\.negative_rows=[1-9][0-9]*$' "$WORK/negative.log"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_negative_dataset\.total\.learnable_two_class=1$' "$WORK/negative.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_negative_dataset\.total\.train_positive=[0-9]+$' "$WORK/negative.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_negative_dataset\.total\.validation_negative=[0-9]+$' "$WORK/negative.log"
grep -q 'fasim_supported_non_sim' "$WORK/negative.log"
grep -q '## Negative / Contrastive Dataset' "$REPORT"
grep -q 'No production model is trained or loaded.' "$REPORT"
grep -q 'SIM labels remain offline labels only.' "$REPORT"
