#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_prep}"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for relative in \
  goal-final.md paper/PAPER_PREP_STATUS.md \
  paper/independent_arithmetic_audit.tsv paper/claim_evidence.tsv \
  paper/source_data/correctness.tsv paper/source_data/exclusions.tsv \
  reproduce/audit_paper_results.py reproduce/audit_claim_language.py \
  tests/check_audit_fasim_gasal2_paper_results.py; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing final paper-prep dependency: $relative" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

python3 "$ROOT/tests/check_audit_fasim_gasal2_paper_results.py"
python3 -m py_compile \
  "$ROOT/reproduce/audit_paper_results.py" \
  "$ROOT/reproduce/audit_claim_language.py"

rm -rf "$WORK"
mkdir -p "$WORK"
python3 "$ROOT/reproduce/audit_paper_results.py" \
  --source-dir "$ROOT/paper/source_data" \
  --table-dir "$ROOT/paper/tables" \
  --output "$WORK/independent_arithmetic_audit.tsv"
cmp "$ROOT/paper/independent_arithmetic_audit.tsv" "$WORK/independent_arithmetic_audit.tsv"
python3 "$ROOT/reproduce/audit_claim_language.py" --paper-dir "$ROOT/paper"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
paper = root / "paper"
runtime_commit = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
freeze_id = "paper-data-v1-dccfd49-20260716"
decision = "paper_preparation_ready_with_declared_limitations"


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


state: dict[str, str] = {}
for raw in (root / "goal-final.md").read_text(encoding="utf-8").splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
if state.get("active_phase") != "complete" or state.get("last_completed_phase") != "9":
    raise SystemExit("paper goal is not complete through Phase 9")
if any(state.get(f"phase_{index}_status") != "pass" for index in range(10)):
    raise SystemExit("not all paper phases are pass")
if state.get("paper_runtime_epoch") != "0" or state.get("paper_runtime_commit") != runtime_commit:
    raise SystemExit("paper runtime freeze drifted")
if state.get("data_freeze_id") != freeze_id or state.get("last_decision") != decision:
    raise SystemExit("data freeze or final decision drifted")

_, claims = read_tsv(paper / "claim_evidence.tsv")
if [row["claim_id"] for row in claims] != [f"C{index}" for index in range(1, 8)]:
    raise SystemExit("claim ledger does not contain ordered C1-C7")
for row in claims:
    if int(row["current_n"]) < 1 or not row["status"].startswith("frozen_"):
        raise SystemExit(f"claim lacks frozen evidence: {row['claim_id']}")
    for field in (
        "current_value", "final_interval_or_range", "correctness_status",
        "source_data_filter", "allowed_manuscript_wording",
    ):
        if not row[field]:
            raise SystemExit(f"claim field missing: {row['claim_id']} {field}")

_, correctness = read_tsv(paper / "source_data/correctness.tsv")
paired = [row for row in correctness if row["row_type"] == "paired_contract"]
guards = [row for row in correctness if row["row_type"] == "preflight_guard"]
clean = [row for row in paired if row["status"] == "clean"]
mismatches = [row for row in paired if row["status"] == "mismatch"]
if (len(correctness), len(paired), len(clean), len(mismatches), len(guards)) != (64, 61, 54, 7, 3):
    raise SystemExit("correctness clean/mismatch/guard counts drifted")
for row in paired:
    if row["fallbacks"] != "0" or row["overflow_fallbacks"] != "0" or row["oom"] != "0":
        raise SystemExit(f"paired fallback/OOM evidence drifted: {row['pair_id_text']}")
for row in clean:
    observed_top5 = [row[key] for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_equal")]
    if any(value not in {"1", "NA"} for value in observed_top5):
        raise SystemExit(f"clean row failed a top5 contract: {row['pair_id_text']}")
for row in mismatches:
    if not any(row[key] == "0" for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_equal")):
        raise SystemExit(f"mismatch row lacks visible top5 drift: {row['pair_id_text']}")
for row in guards:
    if row["status"] != "guarded" or row["supported"] != "0" or row["gpu_fast_path_executed"] != "0":
        raise SystemExit(f"preflight guard did not fail closed: {row['workload_id']}")

_, audit = read_tsv(paper / "independent_arithmetic_audit.tsv")
if len(audit) != 50 or any(row["status"] not in {"match", "derived"} for row in audit):
    raise SystemExit("independent arithmetic audit is incomplete")
if sum(row["metric_id"] == "median_paired_speedup" for row in audit) != 21:
    raise SystemExit("independent audit does not cover all paired workloads")

_, gaps = read_tsv(paper / "gap_register.tsv")
unresolved_core = [row["gap_id"] for row in gaps if not row["status"].startswith("resolved_") and row["severity"] == "core"]
if unresolved_core:
    raise SystemExit(f"core paper-preparation gaps remain: {unresolved_core}")

_, runs = read_tsv(paper / "source_data/benchmark_runs.tsv")
for row in runs:
    workload = row["workload_id"].lower()
    if "121" in workload or "full_hg38" in workload or "kcnq_full" in workload:
        raise SystemExit(f"forbidden full long-query run entered source data: {row['workload_id']}")

status = (paper / "PAPER_PREP_STATUS.md").read_text(encoding="utf-8")
for phrase in (
    decision, runtime_commit, freeze_id, "make check-fasim-gasal2-paper-prep",
    "38.320882x", "10 of 13", "54 of 61", "Full 121-segment KCNQ1OT1 and full hg38 were not run",
    "No release, DOI or tag was created automatically",
):
    if phrase not in status:
        raise SystemExit(f"final status missing: {phrase}")

final_decision = (root / "docs/fasim_gasal2_long_query_final_decision.md").read_text(encoding="utf-8")
if "long_query_architecture_no_go_with_complete_evidence" not in final_decision:
    raise SystemExit("long-query no-go was overwritten")
paper_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(paper.glob("*.md"))).lower()
for pattern in (
    r"recommend(?:ed)?\s+(?:for\s+)?multi-worker",
    r"recommend(?:ed)?\s+(?:for\s+)?(?:four|six)-worker",
    r"traceback threshold pruning\s+is\s+recommended",
):
    if re.search(pattern, paper_text):
        raise SystemExit(f"unsafe production recommendation found: {pattern}")

tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
for relative in filter(None, tracked):
    path = root / relative
    if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
        raise SystemExit(f"large raw artifact is tracked: {relative}")

print("GASAL2 final paper-prep audit OK")
print("final_decision=paper_preparation_ready_with_declared_limitations")
print("claims_complete=7")
print("paired_clean=54")
print("paired_mismatch_retained=7")
print("guarded_full_length_queries=3")
print("independent_arithmetic_rows=50")
PY

if [[ -n "$(git -C "$ROOT" ls-files -o --exclude-standard -- paper/source_data)" ]]; then
  echo "untracked frozen source-data files remain" >&2
  git -C "$ROOT" ls-files -o --exclude-standard -- paper/source_data >&2
  exit 1
fi
if git -C "$ROOT" tag -l gasal2-longtarget-paper-v0.1 | grep -q .; then
  echo "paper release tag was created before owner approval" >&2
  exit 1
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "GASAL2 paper preparation checks OK"
echo "public_release_performed=0"
echo "full_121_or_hg38_run_added=0"
