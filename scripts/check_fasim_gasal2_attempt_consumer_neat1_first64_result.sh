#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_attempt_consumer_neat1_first64/report.json"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing attempt-consumer NEAT1 first64 report: $REPORT" >&2
  echo "decision=attempt_consumer_shadow_not_proven" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

decision = report.get("decision", "attempt_consumer_shadow_not_proven")
allowed = {
    "attempt_consumer_shadow_candidate_go",
    "attempt_consumer_shadow_correctness_no_go",
    "attempt_consumer_shadow_no_reduction_no_go",
    "attempt_consumer_shadow_no_cpu_align_reduction_no_go",
    "attempt_consumer_shadow_performance_no_go",
}
require(decision in allowed, f"unexpected decision={decision}")
require(report.get("workload") == "NEAT1_first64", "unexpected workload")
require(int(report.get("record_limit", 0)) == 64, "expected record_limit=64")
require(report.get("digest_match") is True, "digest mismatch")
require(report.get("baseline_digest") == report.get("candidate_digest"),
        "baseline/candidate digest mismatch")
require(int(report.get("stream_scoreinfo_mismatches", -1)) == 0,
        "stream scoreInfo mismatches")
require(int(report.get("stream_realpath_fallbacks", -1)) == 0,
        "stream realpath fallback")
require(int(report.get("attempt_consumer_shadow_requested", 0)) == 1,
        "attempt consumer not requested")
require(int(report.get("attempt_consumer_shadow_active", 0)) == 1,
        "attempt consumer not active")
require(int(report.get("attempt_consumer_shadow_tasks", 0)) > 0,
        "attempt consumer tasks missing")
require(int(report.get("attempt_consumer_shadow_scoreinfos", 0)) > 0,
        "attempt consumer scoreinfos missing")
require(int(report.get("attempt_consumer_shadow_attempts", 0)) > 0,
        "attempt consumer attempts missing")
require(int(report.get("attempt_consumer_shadow_selected_attempts", 0)) > 0,
        "attempt consumer selected attempts missing")
require(int(report.get("attempt_consumer_shadow_cpu_align_attempts", 0)) ==
        int(report.get("attempt_consumer_shadow_selected_attempts", -1)),
        "shadow CPU align attempts must equal selected attempts")
require(int(report.get("attempt_consumer_shadow_triplex_mismatches", -1)) == 0,
        "attempt consumer triplex mismatches")
require(int(report.get("attempt_consumer_shadow_missing_triplexes", -1)) == 0,
        "attempt consumer missing triplexes")
require(int(report.get("attempt_consumer_shadow_extra_triplexes", -1)) == 0,
        "attempt consumer extra triplexes")
require(report.get("attempt_consumer_shadow_first_mismatch") == "none",
        "attempt consumer first mismatch not none")
require(int(report.get("attempt_consumer_shadow_fallbacks", -1)) == 0,
        "attempt consumer fallback")
require(int(report.get("attempt_consumer_shadow_digest_match", 0)) == 1,
        "attempt consumer digest flag not set")
require(int(report.get("attempt_consumer_shadow_full_rows_equal", 0)) == 1,
        "attempt consumer full row equality flag not set")

attempts = int(report["attempt_consumer_shadow_attempts"])
selected = int(report["attempt_consumer_shadow_selected_attempts"])
cpu_align = int(report["attempt_consumer_shadow_cpu_align_attempts"])
realpath_align = int(report["realpath_extend_align_attempts"])
candidate_vs_baseline = float(report["candidate_vs_baseline"])
attempt_total = float(report["attempt_consumer_shadow_total_seconds"])
realpath_seconds = float(report["realpath_extend_seconds"])

require(selected < attempts,
        f"selected attempts should be below attempt space, got {selected}/{attempts}")
require(attempt_total > 0.0, "attempt consumer total seconds missing")
require(realpath_seconds > 0.0, "CPU reference seconds missing")

if decision == "attempt_consumer_shadow_candidate_go":
    require(cpu_align < realpath_align,
            f"CPU align attempts not reduced: {cpu_align} vs {realpath_align}")
    require(candidate_vs_baseline > 1.0,
            f"candidate_vs_baseline <= 1: {candidate_vs_baseline}")
    require(attempt_total < realpath_seconds,
            "attempt consumer total does not beat CPU reference")
else:
    reasons = set(report.get("decision_reasons", []))
    require(reasons, "no-go decision must include decision_reasons")
    if decision == "attempt_consumer_shadow_no_cpu_align_reduction_no_go":
        require("cpu_align_attempts_not_reduced" in reasons,
                "missing cpu-align reduction reason")
        require(cpu_align >= realpath_align,
                f"expected no CPU align reduction, got {cpu_align} < {realpath_align}")
    if decision == "attempt_consumer_shadow_performance_no_go":
        require(
            "candidate_vs_baseline_not_above_1" in reasons or
            "attempt_consumer_total_not_below_cpu_reference" in reasons,
            "missing performance no-go reason",
        )
    if decision == "attempt_consumer_shadow_correctness_no_go":
        require(False, "correctness no-go is not acceptable for this result gate")

print("decision=" + decision)
print("candidate_vs_baseline=" + f"{candidate_vs_baseline:.6f}x")
print("attempt_consumer_shadow_attempts=" + str(attempts))
print("attempt_consumer_shadow_cpu_align_attempts=" + str(cpu_align))
print("realpath_extend_align_attempts=" + str(realpath_align))
print("attempt_consumer_shadow_triplex_mismatches=0")
print("ok")
PY
