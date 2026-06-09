#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_top5_scoped_completion_candidate.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
PRODUCT_DOC="$ROOT/docs/fasim_gasal2_top5_product_readiness.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$PRODUCT_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing top5 scoped completion-candidate dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$PRODUCT_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
product = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_doc = [
    "Top5 Scoped Completion Candidate",
    "conditional completion candidate",
    "not universal scoreInfo/preAlign replacement",
    "not the full objective by itself",
    "--gasal2-top5-column-pruned-scoreinfo",
    "result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "topk-TFOsorted.lite",
    "top5 score/stability/nt_score payload is the product output",
    "full `.lite` output and final all-row TFO are outside the accepted contract",
    "short-query/H19",
    "chr21+chr22",
    "MEG3 grouped",
    "scoreinfo_gasal2_active = 1",
    "GASAL2 requests > 0",
    "GASAL2 traceback requests > 0",
    "exact scoreInfo GPU tasks > 0",
    "zero_legacy_score_runs = 1",
    "fallback/overflow = 0",
    "default-off opt-in",
    "MALAT1/NEAT1",
    "query_len > GASAL2_MAX_QUERY_LEN",
    "CPU fallback remains authority",
    "not a GASAL2-active success",
    "GASAL2 selected/expanded segment traceback: no-go for real path",
    "not `aligner.Align()` replacement",
    "not GPU endpoint/CIGAR/traceback authority",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "make check-fasim-gasal2-top5-product-readiness",
    "make check-fasim-gasal2-top5-broader-validation",
    "make check-fasim-gasal2-top5-recommended-runtime",
    "make check-fasim-gasal2-top5-release-smoke",
    "make check-fasim-gasal2-full-goal-decision",
    "full goal remains active unless this narrowed product scope is explicitly accepted",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "top5 scoped completion-candidate doc missing phrases: "
        + ", ".join(missing)
    )

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("product-readiness", product),
):
    for phrase in (
        "make check-fasim-gasal2-top5-scoped-completion-candidate",
        "top5 scoped completion candidate",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing scoped completion phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-top5-scoped-completion-candidate:\n"
    r"\tbash \./scripts/check_fasim_gasal2_top5_scoped_completion_candidate\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-top5-scoped-completion-candidate target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-top5-scoped-completion-candidate" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing scoped completion-candidate dependency")
if "check-fasim-gasal2-top5-release-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing top5 release-smoke dependency")
PY

echo "ok"
