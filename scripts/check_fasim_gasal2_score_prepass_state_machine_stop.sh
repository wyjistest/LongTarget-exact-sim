#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_stop.md"
TRUST_DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_trust.md"
CHAR_DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_characterization.md"
CONSUMER_DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_consumer.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$TRUST_DOC" "$CHAR_DOC" "$CONSUMER_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing score-prepass stop dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$TRUST_DOC" "$CHAR_DOC" "$CONSUMER_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
trust = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
char = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
consumer = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Score-Prepass State-Machine Stop",
    "current segmented score-prepass state-machine consumer line as a real-path candidate",
    "current implementation shape is exhausted",
    "correctness scaffold: clean",
    "current real path: no-go",
    "NEAT1 first16:",
    "state_machine_cpu_align_attempts = 35,152",
    "align_cache_hits = 0",
    "align_cache_misses = 35,152",
    "candidate_vs_baseline = 0.5951x",
    "full-query GASAL2 traceback:",
    "guarded out at query_len = 22,767",
    "raising guard to 30,000 hit CUDA illegal memory access",
    "selected-segment traceback:",
    "NEAT1 first1 mismatches = 1,288 / 2,008",
    "NEAT1 first4 mismatches = 5,337 / 8,480",
    "NEAT1 first16 mismatches = 22,000 / 35,152",
    "expanded-segment oracle:",
    "required_max_len = 22,767",
    "required_over_gasal2_limit = 21,991 on first16",
    "effectively full-query traceback for many attempts",
    "Do not continue by tuning the current segmented score-prepass state-machine implementation",
    "Do not promote:",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
    "broad scoreInfo/preAlign replacement",
    "triplex_mismatches = 0",
    "candidate total < CPU fallback on the claimed workload",
    "CPU traceback attempts materially reduced or replaced",
    "legacy-compatible full-query traceback replacement",
    "consumer design that preserves scoreInfo-level single-emission semantics",
    "raising GASAL2 query guard as a fix",
    "make check-fasim-gasal2-score-prepass-state-machine-stop",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("score-prepass stop doc missing phrases: " + ", ".join(missing))

for name, text, phrases in (
    ("trust", trust, ("Performance is no-go for the current implementation", "cache hits are zero", "full-query GASAL2 traceback cannot replace", "selected query segment", "expanded-segment oracle confirms this boundary")),
    ("characterization", char, ("go as default-off shadow scaffold", "no-go for current shadow implementation", "Real path:", "no")),
    ("consumer", consumer, ("The goal is not selected-only replay", "If score-prepass total plus CPU traceback is still slower than CPU fallback", "no production opt-in")),
):
    missing_sub = [phrase for phrase in phrases if phrase not in text]
    if missing_sub:
        raise SystemExit(f"{name} doc missing stop evidence: " + ", ".join(missing_sub))

if "score-prepass state-machine trust" not in current_state:
    raise SystemExit("current-state doc missing score-prepass trust boundary")

target = re.search(
    r"^check-fasim-gasal2-score-prepass-state-machine-stop:\n"
    r"\tbash \./scripts/check_fasim_gasal2_score_prepass_state_machine_stop\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing score-prepass state-machine stop target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-score-prepass-state-machine-stop" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass stop dependency")

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
if "check-fasim-gasal2-score-prepass-state-machine-stop" not in set(phony_targets):
    raise SystemExit("score-prepass state-machine stop target missing from .PHONY")
PY

echo "ok"
