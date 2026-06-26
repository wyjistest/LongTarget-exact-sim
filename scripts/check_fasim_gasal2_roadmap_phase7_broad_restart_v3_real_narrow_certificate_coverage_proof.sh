#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md"
SMOKE="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md"
EXACT_DOC="$ROOT/docs/fasim_long_query_exact_column_scoreinfo_shadow.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$SMOKE" "$EXACT_DOC" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
smoke = Path(sys.argv[2])
exact_doc = Path(sys.argv[3])
matrix = Path(sys.argv[4])
makefile = Path(sys.argv[5])
for path in [doc, smoke, exact_doc, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
smoke_flat = " ".join(smoke.read_text(encoding="utf-8").split())
exact_flat = " ".join(exact_doc.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_real_narrow_certificate_coverage_proof = exact_column_candidate_no_go",
    "phase7_broad_restart_v3_exact_column_candidate_status = no_go",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "non_optin_active = 0",
    "non_optin_error = invalid argument",
    "non_optin_required_smem = 52416",
    "non_optin_default_smem_limit = 49152",
    "non_optin_optin_smem_limit = 101376",
    "smem_optin_active = 1",
    "smem_optin_gpu_tasks = 432",
    "smem_optin_scoreinfo_mismatches = 1",
    "smem_optin_decision = smem_optin_scoreinfo_no_go",
    "exact-column GPU scoreInfo is not a valid real narrow certificate source",
    "CPU aligner.Align() output authority",
    "no GPU endpoint/CIGAR/traceback/output authority",
    "Do not add a broad_replacement workload-matrix row from this checkpoint.",
    "phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required real narrow coverage phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_narrow_certificate_smoke = bounded_probe_no_go_missing_certificate",
    "phase7_broad_restart_v3_next_gate = real_narrow_certificate_coverage_proof",
]:
    if phrase not in smoke_flat:
        raise SystemExit(f"missing narrow smoke prerequisite phrase: {phrase}")

for phrase in [
    "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_active=0",
    "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_error=invalid argument",
    "decision = smem_optin_scoreinfo_no_go",
]:
    if phrase not in exact_flat:
        raise SystemExit(f"missing exact-column source evidence phrase: {phrase}")

for target in [
    "check-fasim-long-query-exact-column-scoreinfo-shadow:",
    "check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-real-narrow-certificate-coverage-proof:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from exact-column checkpoint")

print("phase7_broad_restart_v3_real_narrow_certificate_coverage_proof=exact_column_candidate_no_go")
print("phase7_broad_restart_v3_exact_column_candidate_status=no_go")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("phase7_broad_restart_v3_next_gate=different_exact_scoreinfo_source_or_seed_certificate")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
