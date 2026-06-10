#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_short_query_top5_tfo_contract.md"
CHARACTERIZE="$ROOT/scripts/characterize_fasim_gasal2_short_query_tfo_contract.sh"
COMPARE="$ROOT/scripts/compare_fasim_tfosorted_tfo_contract.py"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_short_query_top5_tfo_contract"}"

for path in "$DOC" "$CHARACTERIZE" "$COMPARE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing short-query top5 TFO dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$ROOT/Makefile" <<'PY'
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[2]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Short-Query Top5 TFO Contract",
    "short-query/H19 strongest top5 TFO:",
    "scoped go",
    "full TFOsorted output:",
    "not equivalent",
    "full TFO sequence set:",
    "not equivalent",
    "aligner.Align replacement:",
    "not claimed",
    "top5 TFO sequence list is identical",
    "score",
    "MeanStability",
    "Nt(bp)",
    "CPU baseline wall = 2278.208116s",
    "GASAL2 candidate wall = 101.127585s",
    "speedup = 22.528058x",
    "baseline_rows = 388501",
    "candidate_rows = 388820",
    "full_rows_equal = false",
    "tfo_equal = false",
    "gapless_tfo_equal = false",
    "top5_tfo_score_equal = true",
    "top5_tfo_stability_equal = true",
    "top5_tfo_nt_score_equal = true",
    "gpu0_util_avg_all = 30.872549%",
    "gpu0_util_avg_active = 51.623%",
    "gpu0_util_max = 86%",
    "make check-fasim-gasal2-short-query-top5-tfo-contract",
    "short-query/H19 top5 TFO accelerator:",
    "go as default-off scoped milestone",
    "full aligner.Align replacement:",
    "no-go",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("missing short-query top5 TFO doc phrase: " + missing[0])

for phrase in (
    "check-fasim-gasal2-short-query-top5-tfo-contract",
    "scripts/check_fasim_gasal2_short_query_top5_tfo_contract.sh",
):
    if phrase not in makefile:
        raise SystemExit(f"missing Makefile phrase: {phrase}")
PY

WORK="$WORK" \
TARGET="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa" \
RNA="$ROOT/H19.fa" \
PRUNE_MAX_PER_TASK=256 \
GASAL2_STREAMS=3 \
GASAL2_BATCH=20000 \
bash "$CHARACTERIZE" >"$WORK.run.log"

summary="$WORK/summary.txt"
if [[ ! -s "$summary" ]]; then
  echo "missing characterization summary: $summary" >&2
  exit 1
fi

grep -q '^full_rows_equal=false$' "$summary"
grep -q '^tfo_equal=false$' "$summary"
grep -q '^gapless_tfo_equal=false$' "$summary"
grep -q '^top5_tfo_score_equal=true$' "$summary"
grep -q '^top5_tfo_stability_equal=true$' "$summary"
grep -q '^top5_tfo_nt_score_equal=true$' "$summary"

echo "GASAL2 short-query top5 TFO contract OK"
