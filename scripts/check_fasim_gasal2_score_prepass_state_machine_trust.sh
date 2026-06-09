#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_trust.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"
SMOKE="$ROOT/scripts/check_fasim_gasal2_score_prepass_state_machine_trust_runtime_smoke.sh"
FASTSIM="$ROOT/fasim/fastsim.h"
MAIN="$ROOT/fasim/Fasim-LongTarget.cpp"

for path in "$DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" "$SMOKE" "$FASTSIM" "$MAIN"; do
  if [[ ! -s "$path" ]]; then
    echo "missing score-prepass state-machine trust dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" "$SMOKE" "$FASTSIM" "$MAIN" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")
smoke = Path(sys.argv[4]).read_text(encoding="utf-8")
fastsim = Path(sys.argv[5]).read_text(encoding="utf-8")
main = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Score-Prepass State-Machine Trust",
    "default-off audited trust checkpoint",
    "external digest gate",
    "It is not a production recommendation",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1",
    "skips CPU realpath extend if every task is covered",
    "writes state-machine triplexes to the candidate output",
    "requires external baseline digest equality",
    "falls back to CPU if coverage/fallback checks fail",
    "CPU `aligner.Align()` is still used for selected/fallback traceback",
    "NEAT1 first1:",
    "state_machine_cpu_align_attempts = 2,008",
    "align_cache_lookups = 2,008",
    "align_cache_hits = 0",
    "align_cache_misses = 2,008",
    "NEAT1 first4:",
    "state_machine_cpu_align_attempts = 8,480",
    "align_cache_lookups = 8,480",
    "align_cache_misses = 8,480",
    "candidate_vs_baseline = 0.5810x",
    "NEAT1 first16:",
    "state_machine_cpu_align_attempts = 35,152",
    "align_cache_lookups = 35,152",
    "align_cache_misses = 35,152",
    "candidate_vs_baseline = 0.5951x",
    "trust path proves the state-machine output can replace CPU realpath output",
    "Performance is no-go for the current implementation",
    "does not reduce the dominant CPU traceback work",
    "align cache probe",
    "cache lookups / hits / misses / unique keys",
    "cache hits are zero",
    "local same-flush CPU alignment cache does not reduce the work",
    "GASAL2 traceback shadow",
    "gasal2_traceback_shadow_alignment_mismatches",
    "gasal2_traceback_shadow_triplex_mismatches",
    "gasal2_traceback_shadow_attempts = 2,008",
    "gasal2_traceback_shadow_fallbacks = 1",
    "gasal2_length_guard_last_query_len = 22,767",
    "gasal2_length_guard_max_query_len = 2,812",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=30000",
    "CUDA illegal memory access",
    "src/gasal_align.cu:343",
    "full-query GASAL2 traceback cannot replace the state-machine CPU `Align()` path",
    "segmented-query traceback shadow",
    "segment_traceback_shadow_attempts",
    "segment_traceback_shadow_alignment_mismatches",
    "segment_traceback_shadow_triplex_mismatches",
    "segment_traceback_shadow_cpu_query_outside_segment",
    "segment_traceback_shadow_score_mismatches",
    "segment_traceback_shadow_endpoint_mismatches",
    "segment_traceback_shadow_cigar_mismatches",
    "expanded_segment_traceback_shadow_attempts",
    "expanded_segment_traceback_shadow_alignment_mismatches",
    "expanded_segment_traceback_shadow_triplex_mismatches",
    "expanded_segment_traceback_shadow_cpu_query_outside_expanded_segment",
    "expanded_segment_traceback_shadow_required_max_len",
    "expanded_segment_traceback_shadow_required_over_gasal2_limit",
    "Correctness/shape:",
    "go as audited trust scaffold",
    "Performance:",
    "no-go for current implementation",
    "Real path:",
    "no",
    "Do not promote this env as a recommended runtime",
    "make check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "score-prepass state-machine trust doc missing phrases: "
        + ", ".join(missing)
    )

for phrase in (
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST",
    "fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE",
    "fasim_gasal2_score_prepass_state_machine_align_cache_runtime",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW",
    "fasim_gasal2_score_prepass_state_machine_gasal2_traceback_shadow_runtime",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW",
    "fasim_gasal2_score_prepass_state_machine_segment_traceback_shadow_runtime",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW",
    "fasim_gasal2_score_prepass_state_machine_expanded_segment_traceback_shadow_runtime",
):
    if phrase not in fastsim:
        raise SystemExit(f"fastsim missing trust runtime phrase: {phrase}")

for phrase in (
    "fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime",
    "fasim_gasal2_score_prepass_state_machine_align_cache_runtime",
    "fasim_gasal2_score_prepass_state_machine_gasal2_traceback_shadow_runtime",
    "fasim_gasal2_score_prepass_state_machine_segment_traceback_shadow_runtime",
    "fasim_gasal2_score_prepass_state_machine_expanded_segment_traceback_shadow_runtime",
    "score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches",
    "score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches",
    "score_prepass_state_machine_shadow_cpu_align_cache_hits",
):
    if phrase not in main:
        raise SystemExit(f"main missing trust implementation phrase: {phrase}")

for phrase in (
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1",
    "realpath_extend_align_attempts=0",
    "state-machine trust should skip CPU realpath align attempts",
    "score_prepass_state_machine_shadow_cpu_align_cache_lookups",
    "score_prepass_state_machine_shadow_cpu_align_cache_hits",
    "score_prepass_state_machine_shadow_cpu_align_cache_misses",
    "score_prepass_state_machine_shadow_cpu_align_cache_unique_keys",
    "score_prepass_state_machine_shadow_gasal2_traceback_requested",
    "score_prepass_state_machine_shadow_gasal2_traceback_attempts",
    "score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches",
    "score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches",
    "score_prepass_state_machine_shadow_segment_traceback_requested",
    "score_prepass_state_machine_shadow_segment_traceback_attempts",
    "score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches",
    "score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches",
    "score_prepass_state_machine_shadow_segment_traceback_missing_segment",
    "score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment",
    "score_prepass_state_machine_shadow_segment_traceback_score_mismatches",
    "score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches",
    "score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_requested",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_attempts",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len",
    "score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit",
):
    if phrase not in smoke:
        raise SystemExit(f"trust smoke missing phrase: {phrase}")

if "score-prepass state-machine trust" not in current_state:
    raise SystemExit("current-state doc missing score-prepass state-machine trust phrase")

for target_name, script_name in (
    (
        "check-fasim-gasal2-score-prepass-state-machine-trust",
        "check_fasim_gasal2_score_prepass_state_machine_trust.sh",
    ),
    (
        "check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke",
        "check_fasim_gasal2_score_prepass_state_machine_trust_runtime_smoke.sh",
    ),
):
    match = re.search(
        rf"^{target_name}:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    if not match or f"bash ./scripts/{script_name}" not in match.group("body"):
        raise SystemExit(f"Makefile missing {target_name} target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
for dep in (
    "check-fasim-gasal2-score-prepass-state-machine-trust",
    "check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke",
):
    if dep not in current_target.group("deps").split():
        raise SystemExit(f"current-state target missing {dep}")

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
if not phony_targets:
    raise SystemExit("Makefile missing .PHONY block")
phony_targets = set(phony_targets)
for dep in (
    "check-fasim-gasal2-score-prepass-state-machine-trust",
    "check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke",
):
    if dep not in phony_targets:
        raise SystemExit(f"{dep} missing from .PHONY")
PY

echo "ok"
