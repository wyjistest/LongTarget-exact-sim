#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_emission_only_consumer_neat1_first64/report.json"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing emission-only NEAT1 first64 report: $REPORT" >&2
  echo "decision=emission_only_consumer_shadow_not_proven" >&2
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

decision = report.get("decision", "emission_only_consumer_shadow_not_proven")
allowed = {
    "emission_only_consumer_shadow_candidate_go",
    "emission_only_consumer_shadow_correctness_no_go",
    "emission_only_consumer_shadow_no_cpu_align_reduction_no_go",
    "emission_only_consumer_shadow_performance_no_go",
}
require(decision in allowed, f"unexpected decision={decision}")
require(report.get("workload") == "NEAT1_first64", "unexpected workload")
require(int(report.get("record_limit", 0)) == 64, "expected record_limit=64")
require(report.get("baseline_digest") == report.get("candidate_digest"),
        "baseline/candidate digest mismatch")
require(report.get("audited_status") == "accepted", "audit not accepted")
require(int(report.get("stream_scoreinfo_mismatches", -1)) == 0,
        "stream scoreInfo mismatches")
require(int(report.get("stream_realpath_fallbacks", -1)) == 0,
        "stream realpath fallback")
require(int(report.get("emission_only_consumer_shadow_requested", 0)) == 1,
        "emission-only shadow not requested")
require(int(report.get("emission_only_consumer_shadow_active", 0)) == 1,
        "emission-only shadow not active")
require(int(report.get("emission_only_consumer_shadow_tasks", 0)) > 0,
        "emission-only tasks missing")
require(int(report.get("emission_only_consumer_shadow_scoreinfos", 0)) > 0,
        "emission-only scoreinfos missing")
require(int(report.get("emission_only_consumer_shadow_scored_attempts", 0)) > 0,
        "emission-only scored attempts missing")
require(int(report.get("emission_only_consumer_shadow_threshold_emits", 0)) +
        int(report.get("emission_only_consumer_shadow_terminal_emits", 0)) +
        int(report.get("emission_only_consumer_shadow_last_emits", 0)) > 0,
        "emission-only emits missing")
require(int(report.get("emission_only_consumer_shadow_fallbacks", -1)) == 0,
        "emission-only fallback")
require(int(report.get("emission_only_consumer_shadow_digest_match", 0)) == 1,
        "emission-only digest flag not set")
require(int(report.get("emission_only_consumer_shadow_full_rows_equal", 0)) == 1,
        "emission-only full row equality flag not set")

cpu_align = int(report["emission_only_consumer_shadow_cpu_align_attempts"])
reference_align = int(report["emission_only_consumer_shadow_realpath_reference_align_attempts"])
align_reduction = int(report["emission_only_consumer_shadow_align_attempt_reduction"])
triplex_mismatches = int(report["emission_only_consumer_shadow_triplex_mismatches"])
missing_triplexes = int(report["emission_only_consumer_shadow_missing_triplexes"])
extra_triplexes = int(report["emission_only_consumer_shadow_extra_triplexes"])
first_mismatch = report["emission_only_consumer_shadow_first_mismatch"]
candidate_vs_baseline = float(report["candidate_vs_baseline"])
shadow_total = float(report["emission_only_consumer_shadow_total_seconds"])
cpu_reference = float(report["stream_realpath_extend_seconds"])

require(align_reduction == reference_align - cpu_align,
        "align reduction mismatch")
require(shadow_total > 0.0, "shadow total seconds missing")
require(cpu_reference > 0.0, "CPU reference seconds missing")

if decision == "emission_only_consumer_shadow_candidate_go":
    require(triplex_mismatches == 0, "candidate go requires zero triplex mismatches")
    require(missing_triplexes == 0, "candidate go requires zero missing triplexes")
    require(extra_triplexes == 0, "candidate go requires zero extra triplexes")
    require(first_mismatch == "none", "candidate go requires no first mismatch")
    require(cpu_align < reference_align,
            f"CPU align attempts not reduced: {cpu_align} vs {reference_align}")
    require(candidate_vs_baseline > 1.0,
            f"candidate_vs_baseline <= 1: {candidate_vs_baseline}")
    require(shadow_total < cpu_reference,
            "emission shadow total does not beat CPU reference")
else:
    reasons = set(report.get("decision_reasons", []))
    require(reasons, "no-go decision must include decision_reasons")
    if decision == "emission_only_consumer_shadow_correctness_no_go":
        require(
            "triplex_mismatch" in reasons or "first_mismatch_not_none" in reasons,
            "correctness no-go must record triplex/first-mismatch reason",
        )
    if decision == "emission_only_consumer_shadow_no_cpu_align_reduction_no_go":
        require("cpu_align_attempts_not_reduced" in reasons,
                "missing CPU align reduction reason")
        require(cpu_align >= reference_align,
                f"expected no CPU align reduction, got {cpu_align} < {reference_align}")
    if decision == "emission_only_consumer_shadow_performance_no_go":
        require(
            "candidate_vs_baseline_not_above_1" in reasons or
            "emission_shadow_total_not_below_cpu_reference" in reasons,
            "missing performance no-go reason",
        )

print("decision=" + decision)
print("candidate_vs_baseline=" + f"{candidate_vs_baseline:.6f}x")
print("emission_only_consumer_shadow_cpu_align_attempts=" + str(cpu_align))
print("emission_only_consumer_shadow_realpath_reference_align_attempts=" + str(reference_align))
print("emission_only_consumer_shadow_triplex_mismatches=" + str(triplex_mismatches))
print("ok")
PY
