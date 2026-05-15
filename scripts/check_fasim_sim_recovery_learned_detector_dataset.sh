#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"

if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/fasim_sim_recovery_learned_detector_dataset"
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
  --output "$WORK/smoke_report.md" \
  --work-dir "$WORK/work" | tee "$WORK/smoke.log"

test -s "$DATASET"
head -n 1 "$DATASET" | grep -q $'workload_label\trun_index\tcandidate_id\tsource\tvalidate_supported'
head -n 1 "$DATASET" | grep -q $'\tlabel_in_sim\tlabel_sim_only\tlabel_shared_sim_close\tlabel_guard_should_accept\tlabel_miss_stage'
tail -n +2 "$DATASET" | grep -q '^tiny_validate	1	'

grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset\.total\.enabled=1$' "$WORK/smoke.log"
grep -Eq '^benchmark\.fasim_sim_recovery_learned_detector_dataset\.total\.rows=[1-9][0-9]*$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset\.total\.sim_label_columns=1$' "$WORK/smoke.log"
grep -q '^benchmark\.fasim_sim_recovery_learned_detector_dataset\.total\.output_mutations=0$' "$WORK/smoke.log"
grep -q '| learned_detector_dataset_report | yes |' "$WORK/smoke_report.md"
grep -q '## Learned Detector Dataset' "$WORK/smoke_report.md"
grep -q 'SIM labels are post-hoc training labels only' "$WORK/smoke_report.md"
grep -q 'Do not train or ship a production learned detector from this report.' "$WORK/smoke_report.md"
