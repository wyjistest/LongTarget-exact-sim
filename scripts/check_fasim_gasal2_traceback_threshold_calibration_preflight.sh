#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_threshold_calibration_preflight"}"
WRAPPER="$ROOT/scripts/run_fasim_gasal2_topk_lite.sh"
CALIBRATOR="$ROOT/scripts/calibrate_fasim_gasal2_traceback_threshold.sh"
ESTIMATOR="$ROOT/scripts/estimate_fasim_gasal2_traceback_threshold.py"
DOC="$ROOT/docs/fasim_gasal2_traceback_threshold_estimator.md"
MAKEFILE="$ROOT/Makefile"

for path in "$WRAPPER" "$CALIBRATOR" "$ESTIMATOR" "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing traceback calibration preflight dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/target.fa" <<'EOF'
>target1
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
EOF
cat >"$WORK/query.fa" <<'EOF'
>query1
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
EOF

DRY_RUN=1 \
TRACEBACK_THRESHOLD_CALIBRATE=1 \
TRACEBACK_THRESHOLD_CALIBRATION_THRESHOLDS="80 90 100" \
TRACEBACK_THRESHOLD_CALIBRATION_MAX_RECORDS=1 \
TRACEBACK_THRESHOLD_CALIBRATION_MAX_BASES=60 \
TRACEBACK_THRESHOLD_CALIBRATION_WINDOWS=3 \
TRACEBACK_THRESHOLD_CALIBRATION_MIN_TRACEBACK_REQUESTS=10 \
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_TSV="$WORK/anchors.tsv" \
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_WINDOW_BASES=20 \
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_MAX_WINDOWS=2 \
DNA="$WORK/target.fa" \
RNA="$WORK/query.fa" \
OUT="$WORK/out" \
WORKERS=1 \
GPU_IDS=0 \
bash "$WRAPPER" >"$WORK/dry_run.txt"

grep -q '^TRACEBACK_THRESHOLD_CALIBRATE=1$' "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_THRESHOLDS=80 90 100$' "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_MAX_RECORDS=1$' "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_MAX_BASES=60$' "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_WINDOWS=3$' "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_MIN_TRACEBACK_REQUESTS=10$' "$WORK/dry_run.txt"
grep -q "^TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_TSV=$WORK/anchors.tsv$" "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_WINDOW_BASES=20$' "$WORK/dry_run.txt"
grep -q '^TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_MAX_WINDOWS=2$' "$WORK/dry_run.txt"
grep -q -- '--gasal2-top5-column-pruned-scoreinfo' "$WORK/dry_run.txt"
grep -q -- '--workers 1' "$WORK/dry_run.txt"

grep -q 'TRACEBACK_THRESHOLD_CALIBRATE' "$WRAPPER"
grep -q 'calibrate_fasim_gasal2_traceback_threshold.sh' "$WRAPPER"
grep -q 'FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=' "$WRAPPER"
grep -q 'TRACEBACK_THRESHOLD_CALIBRATION_WINDOWS' "$WRAPPER"
grep -q 'TRACEBACK_THRESHOLD_CALIBRATION_MIN_TRACEBACK_REQUESTS' "$WRAPPER"
grep -q 'TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_TSV' "$WRAPPER"
grep -q 'FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE' "$ROOT/scripts/fasim_sharded_runner.py"
grep -q 'ESTIMATOR_REQUIRE_FAILING_BOUNDARY' "$CALIBRATOR"
grep -q 'MAX_BASES' "$CALIBRATOR"
grep -q 'sample_fasta_windows.py' "$CALIBRATOR"
grep -q 'MIN_TRACEBACK_REQUESTS' "$CALIBRATOR"
grep -q 'ANCHOR_TSV' "$CALIBRATOR"
grep -q 'compare_fasim_lite_topk.py' "$CALIBRATOR"
grep -q 'estimate_fasim_gasal2_traceback_threshold.py' "$CALIBRATOR"
grep -q 'TRACEBACK_THRESHOLD_CALIBRATE=1' "$DOC"
grep -q 'calibration preflight' "$DOC"
grep -q 'check-fasim-gasal2-traceback-threshold-calibration-preflight:' "$MAKEFILE"
grep -q 'check_fasim_gasal2_traceback_threshold_calibration_preflight.sh' "$MAKEFILE"

echo "check_fasim_gasal2_traceback_threshold_calibration_preflight: ok"
