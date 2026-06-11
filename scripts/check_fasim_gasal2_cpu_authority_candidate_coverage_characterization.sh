#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAR="$ROOT/scripts/characterize_fasim_gasal2_cpu_authority_candidate_coverage.sh"
RESULT="$ROOT/scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_result.sh"
MAKEFILE="$ROOT/Makefile"

for path in "$CHAR" "$RESULT" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing CPU-authority candidate coverage characterization dependency: $path" >&2
    exit 1
  fi
done

python3 - "$CHAR" "$RESULT" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

char = Path(sys.argv[1]).read_text(encoding="utf-8")
result = Path(sys.argv[2]).read_text(encoding="utf-8")
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_char = [
    "FASIM_GASAL2_CPU_AUTHORITY_CANDIDATE_COVERAGE_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1",
    "candidate_coverage_false_negative_scoreinfos",
    "candidate_align_attempts",
    "candidate_coverage_reference_align_attempts",
    "realpath_extend_align_attempts",
    "same_scope_cpu_align_reduction_ratio",
    "coverage_report.json",
    "summary.tsv",
]
for needle in required_char:
    if needle not in char:
        raise SystemExit(f"characterization script missing marker: {needle}")

required_result = [
    "false_negative_scoreinfos",
    "candidate_coverage_covered",
    "candidate_coverage_selected",
    "candidate_align_attempts",
    "same_scope_cpu_align_reduction_ratio",
    "candidate_coverage_reference_align_attempts",
    "triplex_mismatches",
    "coverage_candidate_go",
    "coverage_candidate_no_go",
]
for needle in required_result:
    if needle not in result:
        raise SystemExit(f"result checker missing marker: {needle}")

targets = {
    "characterize-fasim-gasal2-cpu-authority-candidate-coverage":
        r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
        r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_gasal2_cpu_authority_candidate_coverage\.sh",
    "check-fasim-gasal2-cpu-authority-candidate-coverage-result":
        r"\tbash \./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_result\.sh",
    "check-fasim-gasal2-cpu-authority-candidate-coverage-characterization":
        r"\tbash \./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_characterization\.sh",
}
for name, body in targets.items():
    pattern = r"^" + re.escape(name) + r":\n" + body + r"$"
    if not re.search(pattern, makefile, flags=re.MULTILINE):
        raise SystemExit(f"Makefile missing target: {name}")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
deps = current_target.group("deps").split()
if "check-fasim-gasal2-cpu-authority-candidate-coverage-characterization" not in deps:
    raise SystemExit("current-state target missing candidate coverage characterization dependency")

phony = set()
for line in makefile.splitlines():
    if line.startswith(".PHONY:"):
        phony.update(line.split(":", 1)[1].split())
for name in targets:
    if name not in phony:
        raise SystemExit(f"target missing from .PHONY: {name}")

print("ok")
PY
