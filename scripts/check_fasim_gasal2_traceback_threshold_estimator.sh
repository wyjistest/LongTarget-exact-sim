#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_threshold_estimator"}"
ESTIMATOR="$ROOT/scripts/estimate_fasim_gasal2_traceback_threshold.py"
DOC="$ROOT/docs/fasim_gasal2_traceback_threshold_estimator.md"
MAKEFILE="$ROOT/Makefile"

for path in "$ESTIMATOR" "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing traceback threshold estimator dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

python3 - "$WORK/boundary.tsv" "$WORK/lower_bound.tsv" "$WORK/query.fa" <<'PY'
import sys
from pathlib import Path

boundary = Path(sys.argv[1])
lower_bound = Path(sys.argv[2])
query = Path(sys.argv[3])

header = (
    "threshold\ttraceback_requests\ttraceback_reduction\t"
    "traceback_reduction_fraction\twall_seconds\tvs_baseline_gasal2_wall\t"
    "top5_score_equal\ttop5_stability_equal\ttop5_nt_score_equal\t"
    "missing_rows\textra_rows\n"
)
boundary.write_text(
    header
    + "100\t4000\t1000\t0.200000\t10.0\t0.900000\ttrue\ttrue\ttrue\t10\t0\n"
    + "110\t3000\t2000\t0.400000\t9.0\t0.800000\ttrue\ttrue\ttrue\t50\t0\n"
    + "111\t2900\t2100\t0.420000\t8.9\t0.790000\ttrue\tfalse\ttrue\t60\t0\n",
    encoding="utf-8",
)
lower_bound.write_text(
    header
    + "80\t4500\t500\t0.100000\t11.0\t0.950000\ttrue\ttrue\ttrue\t0\t0\n"
    + "90\t4200\t800\t0.160000\t10.5\t0.920000\ttrue\ttrue\ttrue\t0\t0\n",
    encoding="utf-8",
)
query.write_text(">q\n" + "A" * 100 + "\n", encoding="utf-8")
PY

python3 "$ESTIMATOR" \
  --summary "$WORK/boundary.tsv" \
  --query-label fixture \
  --query-fasta "$WORK/query.fa" \
  --require-failing-boundary \
  --output "$WORK/boundary.out"

grep -q '^decision=query_specific_threshold_candidate$' "$WORK/boundary.out"
grep -q '^recommended_threshold=110$' "$WORK/boundary.out"
grep -q '^first_failing_threshold=111$' "$WORK/boundary.out"
grep -q '^first_failing_contracts=stability$' "$WORK/boundary.out"
grep -q '^recommended_threshold_per_query_base=1.100000$' "$WORK/boundary.out"
grep -q '^runtime_recommendation=none_without_same_query_validation$' "$WORK/boundary.out"

set +e
python3 "$ESTIMATOR" \
  --summary "$WORK/lower_bound.tsv" \
  --query-label fixture \
  --require-failing-boundary \
  --output "$WORK/lower_bound.out"
lower_rc=$?
set -e

if [[ "$lower_rc" == "0" ]]; then
  echo "expected lower-bound-only sweep to fail with --require-failing-boundary" >&2
  exit 1
fi
grep -q '^decision=threshold_lower_bound_only_expand_sweep$' "$WORK/lower_bound.out"
grep -q '^recommended_threshold=90$' "$WORK/lower_bound.out"
grep -q '^first_failing_threshold=NA$' "$WORK/lower_bound.out"

grep -q 'query-specific threshold estimator' "$DOC"
grep -q 'not a runtime preset' "$DOC"
grep -q 'first failing stability boundary' "$DOC"
grep -q 'none_without_same_query_validation' "$DOC"
grep -q 'check-fasim-gasal2-traceback-threshold-estimator:' "$MAKEFILE"
grep -q 'check_fasim_gasal2_traceback_threshold_estimator.sh' "$MAKEFILE"

echo "check_fasim_gasal2_traceback_threshold_estimator: ok"
