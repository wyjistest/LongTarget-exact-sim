#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_tie_complete_top5_traceback_certificate_goal.md"

if [[ ! -f "$DOC" ]]; then
  echo "missing goal doc: $DOC" >&2
  exit 1
fi

require_literal() {
  local needle="$1"
  if ! grep -Fq -- "$needle" "$DOC"; then
    echo "missing required text: $needle" >&2
    exit 1
  fi
}

require_absent_literal() {
  local needle="$1"
  if grep -Fq -- "$needle" "$DOC"; then
    echo "forbidden text present: $needle" >&2
    exit 1
  fi
}

require_literal "fasim: characterize tie-complete top5 traceback certificate"
require_literal "FASIM_GASAL2_TOP5_TRACEBACK_CERTIFICATE_SHADOW=1"
require_literal "final retained unique rows"
require_literal "unprocessed_upper_bound < rank5_boundary"
require_literal "unprocessed_upper_bound == rank5_boundary"
require_literal "score_certificate_supported"
require_literal "stability_certificate_supported"
require_literal "nt_score_certificate_supported"
require_literal "traceback_set = score_candidates union stability_candidates union nt_score_candidates"
require_literal "top5 score rows/order equal"
require_literal "top5 stability rows/order equal"
require_literal "top5 nt_score rows/order equal"
require_literal "full lite equivalence: not claimed"
require_literal "full TFOsorted equivalence: not claimed"
require_literal "fixed threshold 116"
require_literal "historical oracle reference only"
require_literal "no real pruning"
require_literal "no span predicate changes"

require_absent_literal "use fixed threshold 116 as algorithm"
require_absent_literal "claim full lite equivalence"
require_absent_literal "claim full TFOsorted equivalence"

python3 - "$DOC" <<'PY'
import sys
from pathlib import Path

doc = Path(sys.argv[1]).read_text(encoding="utf-8")

goal_count = sum(1 for line in doc.splitlines() if line.strip() == "/goal")
if goal_count != 1:
    raise SystemExit(f"expected exactly one /goal prompt, found {goal_count}")

required_order = [
    "forward score/end for all candidates",
    "global candidate ordering by admissible upper bound",
    "physically run filtered traceback batch",
    "compare against authority top5",
]
positions = []
for marker in required_order:
    index = doc.find(marker)
    if index < 0:
        raise SystemExit(f"missing ordered marker: {marker}")
    positions.append(index)
if positions != sorted(positions):
    raise SystemExit("certificate workflow markers are out of order")

if "Do not:" not in doc or "Hard gates:" not in doc:
    raise SystemExit("doc must contain Do not and Hard gates sections")

if "116" not in doc:
    raise SystemExit("doc must explicitly demote threshold 116")

print("ok")
PY
