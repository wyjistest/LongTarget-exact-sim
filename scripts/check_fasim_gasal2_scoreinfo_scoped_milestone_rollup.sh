#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone_rollup.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
SCOPED_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
STOP_DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_stop.md"
MALAT1_PRODUCT_DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_product_readiness.md"
MALAT1_RECOMMENDED_DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_recommended_runtime.md"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$DOC" \
  "$CURRENT_STATE_DOC" \
  "$SCOPED_DOC" \
  "$COMPLETION_GAP_DOC" \
  "$FULL_GOAL_DOC" \
  "$STOP_DOC" \
  "$MALAT1_PRODUCT_DOC" \
  "$MALAT1_RECOMMENDED_DOC" \
  "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing scoped milestone rollup dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$SCOPED_DOC" "$COMPLETION_GAP_DOC" "$FULL_GOAL_DOC" "$STOP_DOC" "$MALAT1_PRODUCT_DOC" "$MALAT1_RECOMMENDED_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
scoped = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
stop_doc = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
malat1_product = " ".join(Path(sys.argv[7]).read_text(encoding="utf-8").split())
malat1_recommended = " ".join(Path(sys.argv[8]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[9]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 ScoreInfo Scoped Milestone Rollup",
    "Milestone status: yes, scoped milestone",
    "Full objective status: not complete",
    "short-query/H19 top5 artifact:",
    "scoped go",
    "MEG3 grouped tiny-region top5 wrapper:",
    "MALAT1-like group32 two-contract scoreInfo runtime:",
    "NEAT1/current broad long-query shape:",
    "no-go for real path",
    "score-prepass state-machine consumer:",
    "stopped for real path",
    "make check-fasim-gasal2-top5-release-smoke",
    "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "make check-fasim-gasal2-malat1-two-contract-product-readiness",
    "make check-fasim-gasal2-malat1-two-contract-recommended-runtime",
    "make check-fasim-gasal2-score-prepass-state-machine-stop",
    "make check-fasim-gasal2-scoreinfo-completion-gap",
    "make check-fasim-gasal2-full-goal-decision",
    "contract smoke, not a performance claim",
    "scoped MALAT1-like smoke, not a universal replacement smoke",
    "MALAT1-like product-readiness and recommended-runtime gates",
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "full row-set equality, digest equality, coverage counters, and zero probe leakage",
    "not a real-path candidate",
    "prevent this milestone from being mistaken for completion of the original goal",
    "universal scoreInfo/preAlign replacement",
    "full aligner.Align replacement",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
    "full .lite equivalence for the top5 artifact path",
    "all-row TFO equivalence for the top5 artifact path",
    "NEAT1 broad long-query real path",
    "default production path",
    "Do not call `update_goal complete`",
    "full objective remains open",
    "accepted scoped productization of the top5 artifact contract",
    "broader full-output/TFO equivalence proof over an explicitly claimed scope",
    "different long-query execution architecture",
    "remaining CPU realpath extend/align reduction",
    "promote current score-prepass state-machine trust",
    "promote selected-segment GASAL2 traceback",
    "promote GPU endpoint/CIGAR/traceback authority",
    "claim broad GASAL2 aligner.Align replacement from top5 or MALAT1 scoped gates",
    "make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("scoped milestone rollup doc missing phrases: " + ", ".join(missing))

cross_checks = [
    (
        "current-state",
        current_state,
        [
            "make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
            "scoped milestone rollup",
            "full objective remains open",
        ],
    ),
    (
        "scoped milestone",
        scoped,
        [
            "This is a scoped milestone, not completion of the full objective",
            "Short-query/H19 top5 path: scoped go",
            "MALAT1 streaming scoreInfo trust path: scoped go",
            "Broad scoreInfo/preAlign replacement: not proven",
        ],
    ),
    (
        "completion gap",
        completion_gap,
        [
            "The full objective is not complete",
            "not universal scoreInfo/preAlign replacement",
            "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
            "make check-fasim-gasal2-score-prepass-state-machine-stop",
        ],
    ),
    (
        "full goal",
        full_goal,
        [
            "Current full-goal status: not complete",
            "full objective remains open",
            "make check-fasim-gasal2-top5-release-smoke",
            "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
            "make check-fasim-gasal2-score-prepass-state-machine-stop",
        ],
    ),
    (
        "state-machine stop",
        stop_doc,
        [
            "current real path: no-go",
            "Do not continue by tuning the current segmented score-prepass state-machine implementation",
            "broad scoreInfo/preAlign replacement",
        ],
    ),
    (
        "MALAT1 product-readiness",
        malat1_product,
        [
            "MALAT1-like product-readiness gate",
            "product-readiness candidate",
            "not universal scoreInfo/preAlign replacement",
            "full objective remains open",
        ],
    ),
    (
        "MALAT1 recommended-runtime",
        malat1_recommended,
        [
            "recommended runtime for the scoped MALAT1-like two-contract scoreInfo path",
            "recommended as default-off opt-in for the checked scope",
            "not recommended when:",
            "full objective remains open",
        ],
    ),
]
for name, text, phrases in cross_checks:
    missing_cross = [phrase for phrase in phrases if phrase not in text]
    if missing_cross:
        raise SystemExit(f"{name} doc missing rollup boundary phrase: " + ", ".join(missing_cross))

target = re.search(
    r"^check-fasim-gasal2-scoreinfo-scoped-milestone-rollup:\n"
    r"\tbash \./scripts/check_fasim_gasal2_scoreinfo_scoped_milestone_rollup\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-scoreinfo-scoped-milestone-rollup target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
deps = set(current_target.group("deps").split())
for dep in (
    "check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
    "check-fasim-gasal2-top5-release-smoke",
    "check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "check-fasim-gasal2-malat1-two-contract-product-readiness",
    "check-fasim-gasal2-malat1-two-contract-recommended-runtime",
    "check-fasim-gasal2-score-prepass-state-machine-stop",
    "check-fasim-gasal2-scoreinfo-completion-gap",
    "check-fasim-gasal2-full-goal-decision",
):
    if dep not in deps:
        raise SystemExit(f"current-state target missing milestone rollup dependency: {dep}")

phony_targets = []
lines = makefile.splitlines()
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith(".PHONY:"):
        text = line.split(":", 1)[1].strip()
        while text.endswith("\\") and index + 1 < len(lines):
            text = text[:-1] + " " + lines[index + 1].strip()
            index += 1
        phony_targets.extend(text.split())
    index += 1
if "check-fasim-gasal2-scoreinfo-scoped-milestone-rollup" not in set(phony_targets):
    raise SystemExit("scoped milestone rollup target missing from .PHONY")
PY

echo "ok"
