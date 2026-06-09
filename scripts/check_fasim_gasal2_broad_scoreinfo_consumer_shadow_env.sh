#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN="$ROOT/fasim/Fasim-LongTarget.cpp"
PLAN="$ROOT/docs/plans/2026-06-09-fasim-gasal2-broad-co-designed-scoreinfo-consumer.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$MAIN" "$PLAN" "$CURRENT_STATE_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing broad scoreInfo consumer shadow env dependency: $path" >&2
    exit 1
  fi
done

python3 - "$MAIN" "$PLAN" "$CURRENT_STATE_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

main = Path(sys.argv[1]).read_text(encoding="utf-8")
plan = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

env = "FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW"

required_main = [
    "fasim_gasal2_broad_scoreinfo_consumer_shadow_runtime",
    env,
    "broad_path_requested",
    "broad_path_active",
    "broad_path_decision",
    "broad_path_tasks",
    "broad_path_scoreinfo_groups",
    "broad_path_scoreinfo_seconds",
    "broad_path_consumer_seconds",
    "broad_path_align_attempts",
    "broad_path_selected_attempts",
    "broad_path_triplex_mismatches",
    "broad_path_missing_triplexes",
    "broad_path_extra_triplexes",
    "broad_path_first_mismatch",
    "broad_path_digest_match",
    "broad_path_full_rows_equal",
    "broad_path_candidate_wall_seconds",
    "broad_path_baseline_wall_seconds",
    "broad_path_candidate_vs_baseline",
    "broad_path_cpu_triplex_path",
    "broad_path_cpu_triplexes",
    "broad_path_cpu_triplex_digest",
    "broad_path_planner_descriptor_path",
    "broad_path_planner_descriptors",
    "broad_path_planner_descriptor_digest",
    "benchmark.fasim_gasal2_broad_path_requested=",
    "benchmark.fasim_gasal2_broad_path_active=",
    "benchmark.fasim_gasal2_broad_path_decision=",
    "benchmark.fasim_gasal2_broad_path_tasks=",
    "benchmark.fasim_gasal2_broad_path_scoreinfo_groups=",
    "benchmark.fasim_gasal2_broad_path_scoreinfo_seconds=",
    "benchmark.fasim_gasal2_broad_path_consumer_seconds=",
    "benchmark.fasim_gasal2_broad_path_align_attempts=",
    "benchmark.fasim_gasal2_broad_path_selected_attempts=",
    "benchmark.fasim_gasal2_broad_path_triplex_mismatches=",
    "benchmark.fasim_gasal2_broad_path_missing_triplexes=",
    "benchmark.fasim_gasal2_broad_path_extra_triplexes=",
    "benchmark.fasim_gasal2_broad_path_first_mismatch=",
    "benchmark.fasim_gasal2_broad_path_digest_match=",
    "benchmark.fasim_gasal2_broad_path_full_rows_equal=",
    "benchmark.fasim_gasal2_broad_path_candidate_wall_seconds=",
    "benchmark.fasim_gasal2_broad_path_baseline_wall_seconds=",
    "benchmark.fasim_gasal2_broad_path_candidate_vs_baseline=",
    "benchmark.fasim_gasal2_broad_path_cpu_triplex_path=",
    "benchmark.fasim_gasal2_broad_path_cpu_triplexes=",
    "benchmark.fasim_gasal2_broad_path_cpu_triplex_digest=",
    "benchmark.fasim_gasal2_broad_path_planner_descriptor_path=",
    "benchmark.fasim_gasal2_broad_path_planner_descriptors=",
    "benchmark.fasim_gasal2_broad_path_planner_descriptor_digest=",
    "FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX",
    "FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER",
    "FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW",
    "planner_descriptors_only",
    "cpu_triplex_export_only",
    "replacement_consumer_shadow_active",
]
missing = [phrase for phrase in required_main if phrase not in main]
if missing:
    raise SystemExit("main broad scoreInfo consumer env missing phrases: " + ", ".join(missing))

for phrase in (
    env,
    "benchmark.fasim_gasal2_broad_path_requested=0",
    "benchmark.fasim_gasal2_broad_path_active=0",
    "benchmark.fasim_gasal2_broad_path_decision=not_implemented",
    "broad_path_cpu_triplex_path",
    "broad_path_cpu_triplexes",
    "broad_path_cpu_triplex_digest",
    "broad_path_planner_descriptor_path",
    "broad_path_planner_descriptors",
    "broad_path_planner_descriptor_digest",
):
    if phrase not in plan:
        raise SystemExit(f"plan missing broad env phrase: {phrase}")

for phrase in (
    "make check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env",
    "make check-fasim-gasal2-broad-replacement-consumer-shadow",
    "co-designed scoreInfo plus replacement-consumer shadow",
    "full objective remains open",
):
    if phrase not in current_state:
        raise SystemExit(f"current-state doc missing broad env phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_broad_scoreinfo_consumer_shadow_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing broad scoreInfo consumer shadow env target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad scoreInfo consumer shadow env dependency")
if "check-fasim-gasal2-broad-replacement-consumer-shadow" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad replacement consumer shadow dependency")

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
if "check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env" not in set(phony_targets):
    raise SystemExit("broad scoreInfo consumer shadow env target missing from .PHONY")
if "check-fasim-gasal2-broad-replacement-consumer-shadow" not in set(phony_targets):
    raise SystemExit("broad replacement consumer shadow target missing from .PHONY")
PY

echo "ok"
