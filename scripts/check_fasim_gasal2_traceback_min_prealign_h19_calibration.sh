#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_traceback_min_prealign_h19_calibration.md"
CHAR_DOC="$ROOT/docs/fasim_gasal2_limited_traceback_characterization.md"
DYNAMIC_DOC="$ROOT/docs/fasim_gasal2_dynamic_traceback_frontier_characterization.md"
CHR22_CHECK="$ROOT/scripts/check_fasim_gasal2_traceback_min_prealign_score_chr22_boundary_result.sh"
MERGE_CHECK="$ROOT/scripts/check_fasim_gasal2_traceback_min_prealign_score_chr21_chr22_result.sh"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CHAR_DOC" "$DYNAMIC_DOC" "$CHR22_CHECK" "$MERGE_CHECK" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing traceback min-prealign calibration dependency: $path" >&2
    exit 1
  fi
done

grep -q 'decision = no_general_runtime_recommendation' "$DOC"
grep -q 'artifact = H19-only traceback pruning calibration' "$DOC"
grep -q 'scope    = chr21/chr22 H19 top5 contract' "$DOC"
grep -q 'runtime  = not recommended as a general preset' "$DOC"
grep -q 'FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116' "$DOC"
grep -q 'not a general runtime recommendation' "$DOC"
grep -q 'not reusable across lncRNAs without calibration' "$DOC"
grep -q 'not a recommended preset for arbitrary targets' "$DOC"
grep -q 'baseline GASAL2 wall        = 70.154883 s' "$DOC"
grep -q 'threshold 116 wall         = 48.483698 s' "$DOC"
grep -q 'traceback reduction         = 4,469,306 / 64.6749%' "$DOC"
grep -q 'threshold 117:' "$DOC"
grep -q 'top5_stability_equal   = false' "$DOC"
grep -q 'future pruning needs a stability-risk feature' "$DOC"
grep -q 'same-query threshold-0 GASAL2 baseline' "$DOC"

grep -q 'FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116' "$CHAR_DOC"
grep -q 'This is not a recommendation to hard-code `116` as a universal runtime' "$CHAR_DOC"
grep -q 'current best passing rule:' "$DYNAMIC_DOC"
grep -q 'fixed threshold 116' "$DYNAMIC_DOC"
grep -q 'needed before further traceback pruning:' "$DYNAMIC_DOC"

bash "$CHR22_CHECK" >/tmp/fasim_gasal2_traceback_min_prealign_chr22_check.$$.log
bash "$MERGE_CHECK" >/tmp/fasim_gasal2_traceback_min_prealign_merge_check.$$.log
rm -f /tmp/fasim_gasal2_traceback_min_prealign_chr22_check.$$.log \
      /tmp/fasim_gasal2_traceback_min_prealign_merge_check.$$.log

grep -q 'check-fasim-gasal2-traceback-min-prealign-h19-calibration:' "$MAKEFILE"
grep -q 'check_fasim_gasal2_traceback_min_prealign_h19_calibration.sh' "$MAKEFILE"

echo "check_fasim_gasal2_traceback_min_prealign_h19_calibration: ok"
