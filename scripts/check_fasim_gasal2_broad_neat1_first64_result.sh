#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_broad_neat1_first64/report.json"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing broad NEAT1 first64 report: $REPORT" >&2
  echo "decision=broad_path_not_proven" >&2
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

decision = report.get("decision", "broad_path_not_proven")
require(decision in {"broad_path_candidate_go", "broad_path_current_architecture_no_go"},
        f"unexpected decision={decision}")

require(report.get("workload") == "NEAT1_first64", "unexpected workload")
require(report.get("record_limit") == 64, "expected record_limit=64")
require(report.get("broad_path_active") == 1, "broad path not active")
require(report.get("broad_path_triplex_mismatches") == 0, "triplex mismatches")
require(report.get("broad_path_missing_triplexes") == 0, "missing triplexes")
require(report.get("broad_path_extra_triplexes") == 0, "extra triplexes")
require(report.get("broad_path_first_mismatch") == "none", "first mismatch not none")
require(report.get("baseline_digest") == report.get("candidate_digest"), "digest mismatch")
require(report.get("audited_status") == "accepted", "audit not accepted")

candidate_wall = float(report.get("candidate_wall_seconds", 0.0))
baseline_wall = float(report.get("baseline_wall_seconds", 0.0))
candidate_vs_baseline = float(report.get("candidate_vs_baseline", 0.0))
broad_scoreinfo = float(report.get("broad_path_scoreinfo_seconds", 0.0))
broad_consumer = float(report.get("broad_path_consumer_seconds", 0.0))
baseline_reference = float(report.get("baseline_cpu_reference_seconds", 0.0))
realpath_align_attempts = int(report.get("realpath_extend_align_attempts", 0))
broad_align_attempts = int(report.get("broad_path_align_attempts", 0))

require(candidate_wall > 0.0, "candidate wall missing")
require(baseline_wall > 0.0, "baseline wall missing")

if decision == "broad_path_candidate_go":
    require(candidate_wall < 86.0335, f"candidate wall too slow: {candidate_wall}")
    require(candidate_vs_baseline > 1.0, f"candidate_vs_baseline <= 1: {candidate_vs_baseline}")
    require(broad_scoreinfo + broad_consumer < baseline_reference,
            "broad scoreInfo+consumer does not beat baseline reference")
    require(realpath_align_attempts == 0 or broad_align_attempts < realpath_align_attempts,
            "realpath extend/align attempts not materially reduced")
else:
    reasons = set(report.get("decision_reasons", []))
    required_reasons = {
        "candidate_wall_not_below_neat1_baseline_ceiling",
        "candidate_vs_baseline_not_above_1",
        "broad_scoreinfo_consumer_not_below_cpu_reference",
        "align_attempts_not_reduced",
    }
    missing = sorted(required_reasons - reasons)
    require(not missing, "no-go report missing reasons: " + ",".join(missing))
    require(candidate_vs_baseline < 1.0,
            f"expected measured no-go speedup < 1, got {candidate_vs_baseline}")
    require(broad_align_attempts >= realpath_align_attempts,
            "expected no-go align attempts not reduced")

print("decision=" + decision)
print("candidate_vs_baseline=" + f"{candidate_vs_baseline:.6f}x")
print("broad_path_triplex_mismatches=0")
print("ok")
PY
