#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_v5_cpu_authority_replay_first64/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 v5 CPU-authority replay first64 report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in rows}
row = by_workload.get("neat1_first64")
if row is None:
    raise SystemExit("missing neat1_first64 v5 CPU-authority replay first64 row")

required_columns = [
    "attempted",
    "digest_match",
    "full_rows_equal",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "candidate_align_attempts",
    "reference_align_attempts",
    "align_attempt_reduction",
    "candidate_wall_seconds",
    "baseline_wall_seconds",
    "candidate_vs_baseline",
    "requested",
    "active",
    "source_is_pre_scoreinfo",
    "scoreinfo_prealign_reduced",
    "gpu_descriptor_scoreinfos",
    "gpu_descriptor_attempts",
    "descriptor_false_negatives",
    "missing_required_attempts",
    "cpu_align_authority",
    "gpu_endpoint_cigar_traceback_output_authority",
    "fallback_accounting_clean",
    "broad_gate_pass",
    "decision",
    "decision_reasons",
]
missing = [key for key in required_columns if key not in row]
if missing:
    raise SystemExit("missing columns: " + ",".join(missing))

if row["attempted"] != "1":
    raise SystemExit("neat1_first64 was not attempted")
for key in [
    "requested",
    "active",
    "source_is_pre_scoreinfo",
    "scoreinfo_prealign_reduced",
    "cpu_align_authority",
]:
    if row[key] != "1":
        raise SystemExit(f"expected {key}=1")
if row["gpu_endpoint_cigar_traceback_output_authority"] != "0":
    raise SystemExit("GPU endpoint/CIGAR/traceback/output authority must stay 0")
if row["descriptor_false_negatives"] != "0":
    raise SystemExit("descriptor false negatives must be zero")
if int(row["gpu_descriptor_scoreinfos"]) <= 0:
    raise SystemExit("expected non-empty GPU descriptor scoreInfos")
if int(row["gpu_descriptor_attempts"]) <= 0:
    raise SystemExit("expected non-empty GPU descriptor attempts")

candidate = int(row["candidate_align_attempts"])
reference = int(row["reference_align_attempts"])
reduction = int(row["align_attempt_reduction"])
if candidate <= 0 or reference <= 0:
    raise SystemExit("expected positive align attempts")
if candidate >= reference:
    raise SystemExit(f"expected align reduction, got {candidate}/{reference}")
if reduction != reference - candidate:
    raise SystemExit("align_attempt_reduction does not match reference-candidate")

allowed = {
    "phase7_v5_cpu_authority_replay_first64_broad_gate_go",
    "phase7_v5_cpu_authority_replay_first64_broad_gate_no_go",
}
if row["decision"] not in allowed:
    raise SystemExit("unexpected decision: " + row["decision"])

if row["broad_gate_pass"] == "1":
    if row["decision"] != "phase7_v5_cpu_authority_replay_first64_broad_gate_go":
        raise SystemExit("broad_gate_pass=1 requires go decision")
    if row["digest_match"] != "1" or row["full_rows_equal"] != "1":
        raise SystemExit("broad gate pass requires digest and row equality")
    if row["missing_rows"] != "0" or row["extra_rows"] != "0":
        raise SystemExit("broad gate pass requires no row diff")
    if row["triplex_mismatches"] != "0":
        raise SystemExit("broad gate pass requires no triplex mismatches")
    if row["missing_required_attempts"] != "0":
        raise SystemExit("broad gate pass requires no missing required attempts")
    if row["fallback_accounting_clean"] != "1":
        raise SystemExit("broad gate pass requires clean fallback accounting")
    if float(row["candidate_vs_baseline"]) <= 1.0:
        raise SystemExit("broad gate pass requires speedup > 1.0")
else:
    if row["decision"] != "phase7_v5_cpu_authority_replay_first64_broad_gate_no_go":
        raise SystemExit("broad_gate_pass=0 requires no-go decision")
    reasons = {
        reason for reason in row["decision_reasons"].split(",") if reason and reason != "none"
    }
    if not reasons:
        raise SystemExit("broad_gate_pass=0 requires explicit decision reasons")
    if row["missing_required_attempts"] != "0" and "fallback_accounting_not_clean" not in reasons:
        raise SystemExit("missing required attempts must be reflected in no-go reasons")

print("phase7_v5_cpu_authority_replay_first64_result=pass")
print("phase7_v5_cpu_authority_replay_first64_decision=" + row["decision"])
print("phase7_v5_cpu_authority_replay_first64_digest_match=" + row["digest_match"])
print("phase7_v5_cpu_authority_replay_first64_full_rows_equal=" + row["full_rows_equal"])
print("phase7_v5_cpu_authority_replay_first64_candidate_align_attempts=" + row["candidate_align_attempts"])
print("phase7_v5_cpu_authority_replay_first64_reference_align_attempts=" + row["reference_align_attempts"])
print("phase7_v5_cpu_authority_replay_first64_align_attempt_reduction=" + row["align_attempt_reduction"])
print("phase7_v5_cpu_authority_replay_first64_candidate_wall_seconds=" + row["candidate_wall_seconds"])
print("phase7_v5_cpu_authority_replay_first64_baseline_wall_seconds=" + row["baseline_wall_seconds"])
print("phase7_v5_cpu_authority_replay_first64_candidate_vs_baseline=" + row["candidate_vs_baseline"])
print("phase7_v5_cpu_authority_replay_first64_broad_gate_pass=" + row["broad_gate_pass"])
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
