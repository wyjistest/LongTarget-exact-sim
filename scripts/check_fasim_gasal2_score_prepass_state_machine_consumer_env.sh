#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTSIM="$ROOT/fasim/fastsim.h"
FASIM_MAIN="$ROOT/fasim/Fasim-LongTarget.cpp"
DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_consumer.md"
MAKEFILE="$ROOT/Makefile"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
BUILD_BIN="${BUILD_BIN:-0}"

for path in "$FASTSIM" "$FASIM_MAIN" "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing score-prepass state-machine env dependency: $path" >&2
    exit 1
  fi
done

python3 - "$FASTSIM" "$FASIM_MAIN" "$DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

fastsim = Path(sys.argv[1]).read_text(encoding="utf-8")
main = Path(sys.argv[2]).read_text(encoding="utf-8")
doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

env = "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW"
runtime = "fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime"

for phrase in (env, runtime):
    if phrase not in fastsim:
        raise SystemExit(f"fastsim missing score-prepass runtime phrase: {phrase}")

for phrase in (
    runtime,
    "stateMachinePrefixAttemptOrdinals",
    "score_prepass_state_machine_no_segmented_selected_attempts",
    "scorePrepassStateMachineShadowRequested",
):
    if phrase not in main:
        raise SystemExit(f"main missing score-prepass state-machine phrase: {phrase}")

required_metrics = [
    "score_prepass_state_machine_shadow_requested",
    "score_prepass_state_machine_shadow_active",
    "score_prepass_state_machine_shadow_tasks",
    "score_prepass_state_machine_shadow_scoreinfos",
    "score_prepass_state_machine_shadow_attempts",
    "score_prepass_state_machine_shadow_selected_attempts",
    "score_prepass_state_machine_shadow_cpu_align_attempts",
    "score_prepass_state_machine_shadow_triplex_mismatches",
    "score_prepass_state_machine_shadow_first_mismatch_source",
    "score_prepass_state_machine_shadow_first_mismatch_kind",
    "score_prepass_state_machine_shadow_score_seconds",
    "score_prepass_state_machine_shadow_select_seconds",
    "score_prepass_state_machine_shadow_cpu_align_seconds",
    "score_prepass_state_machine_shadow_convert_seconds",
    "score_prepass_state_machine_shadow_total_seconds",
    "score_prepass_state_machine_shadow_fallbacks",
]
missing = [metric for metric in required_metrics if metric not in main]
if missing:
    raise SystemExit(
        "main missing score-prepass state-machine telemetry: " + ", ".join(missing)
    )

for phrase in (
    env + "=1",
    "segmented GASAL2 score-prepass",
    "CPU-align only the selected/fallback attempt per scoreInfo",
    "Do not use shadow output for candidate state, output, or digest",
):
    if phrase not in doc:
        raise SystemExit(f"doc missing score-prepass state-machine phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-score-prepass-state-machine-consumer-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing score-prepass state-machine env target")

runtime_target = re.search(
    r"^check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer_runtime_smoke\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runtime_target:
    raise SystemExit("Makefile missing score-prepass state-machine runtime smoke target")

segmented_runtime_target = re.search(
    r"^check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer_segmented_runtime_smoke\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not segmented_runtime_target:
    raise SystemExit("Makefile missing segmented score-prepass state-machine runtime smoke target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-env" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass env dependency")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass runtime smoke dependency")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing segmented score-prepass runtime smoke dependency")

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
if "check-fasim-gasal2-score-prepass-state-machine-consumer-env" not in phony_targets:
    raise SystemExit("score-prepass env target missing from .PHONY")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke" not in phony_targets:
    raise SystemExit("score-prepass runtime smoke target missing from .PHONY")
if "check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke" not in phony_targets:
    raise SystemExit("segmented score-prepass runtime smoke target missing from .PHONY")
PY

if [[ "$BUILD_BIN" == "1" ]]; then
  if [[ ! -x "$BIN" ]]; then
    make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  fi
  WORK="$ROOT/.tmp/check_fasim_gasal2_score_prepass_state_machine_consumer_env"
  rm -rf "$WORK"
  mkdir -p "$WORK"
  strings "$BIN" >"$WORK/strings.txt"
  grep -q 'FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW' "$WORK/strings.txt"
  grep -q 'score_prepass_state_machine_shadow_triplex_mismatches' "$WORK/strings.txt"
fi

echo "ok"
