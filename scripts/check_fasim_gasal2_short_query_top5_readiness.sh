#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_short_query_top5_readiness.md"
MATRIX="$ROOT/scripts/check_fasim_gasal2_scoreinfo_prune_top5_matrix.sh"

for path in "$DOC" "$MATRIX" "$ROOT/patches/gasal2-fasim-bridge.patch" "$ROOT/scripts/setup_gasal2.sh"; do
  if [[ ! -s "$path" ]]; then
    echo "missing short-query readiness dependency: $path" >&2
    exit 1
  fi
done

grep -q 'PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-64}"' "$MATRIX"

python3 - "$DOC" "$ROOT/Makefile" <<'PY'
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[2]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Short-Query Top5 Readiness",
    "short-query/H19 top5 scoreInfo artifact:",
    "scoped go",
    "full Fasim output replacement:",
    "not proven",
    "aligner.Align replacement:",
    "no-go in current evidence",
    "repo: https://github.com/nahmedraja/GASAL2.git",
    "commit: 106d94ee53fc847214fb05f2f9f892538a5d3baf",
    "patch: patches/gasal2-fasim-bridge.patch",
    "setup: scripts/setup_gasal2.sh",
    "make check-fasim-gasal2-reproducible-setup",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64",
    "`PRUNE_MAX_PER_TASK=16` is too aggressive",
    "top5_score_equal = false",
    "top5_stability_equal = false",
    "top5_nt_score_equal = false",
    "The formal `64` cap is the current short-query contract",
    "baseline_rows = 8294",
    "candidate_rows = 8274",
    "top5_score_equal = true",
    "top5_stability_equal = true",
    "top5_nt_score_equal = true",
    "top5_artifact_equal = true",
    "speedup = 23.717688x",
    "does not prove full `.lite`, full TFO, endpoint, CIGAR, traceback, or digest equivalence",
    "claim aligner.Align replacement",
    "claim full output replacement",
    "use cap=16 as a correctness-clean chr22/H19 contract",
]

missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("missing readiness doc phrase: " + missing[0])

required_make = [
    "check-fasim-gasal2-reproducible-setup",
    "check-fasim-gasal2-scoreinfo-prune-top5-chr22-2mb",
]
for phrase in required_make:
    if phrase not in makefile:
        raise SystemExit(f"missing Makefile phrase: {phrase}")
PY

echo "GASAL2 short-query top5 readiness OK"
