#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HISTORICAL_COMPLETION="a98d80d44d4418cdb8a67dc8d83ee41b8e599023"
PAPER_RUNTIME="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for relative in \
  goal-bioinformatics.md \
  paper/bioinformatics/README.md \
  paper/bioinformatics/journal_requirements.md \
  paper/bioinformatics/claim_evidence.tsv \
  paper/bioinformatics/gap_register.tsv \
  paper/bioinformatics/owner_metadata_needed.md \
  paper/bioinformatics/submission_manifest.tsv; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing Bioinformatics Phase 0 dependency: $relative" >&2
    exit 1
  fi
done

python3 - "$ROOT" "$HISTORICAL_COMPLETION" "$PAPER_RUNTIME" <<'PY'
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


root = Path(sys.argv[1])
historical_completion = sys.argv[2]
paper_runtime = sys.argv[3]
bio = root / "paper/bioinformatics"
allowed_statuses = {"pending", "in_progress", "pass", "no_go", "blocked", "not_available"}


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


def require_phrases(path: Path, phrases: tuple[str, ...]) -> str:
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            raise SystemExit(f"{path.relative_to(root)} missing required text: {phrase}")
    return text


goal = require_phrases(
    root / "goal-bioinformatics.md",
    (
        f"submission_baseline_commit = {historical_completion}",
        "phase_0_status = pass",
    ),
)
state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
if state.get("historical_paper_runtime_commit") != paper_runtime:
    raise SystemExit("historical paper runtime commit drifted")
if state.get("historical_paper_runtime_epoch") != "0":
    raise SystemExit("historical paper runtime epoch drifted")
if state.get("submission_software_epoch") != "1":
    raise SystemExit("submission software epoch must start at 1")
active = state.get("active_phase", "")
if active != "complete" and (not active.isdigit() or int(active) < 1):
    raise SystemExit(f"Bioinformatics Phase 0 is not complete: active_phase={active!r}")
last_completed = state.get("last_completed_phase", "")
if not last_completed.isdigit() or int(last_completed) < 0:
    raise SystemExit("Bioinformatics last_completed_phase has regressed below Phase 0")

if subprocess.run(
    ["git", "-C", str(root), "merge-base", "--is-ancestor", historical_completion, "HEAD"],
    check=False,
).returncode != 0:
    raise SystemExit("historical completion commit is not an ancestor of HEAD")

runtime_paths = ["fasim", "cuda", "longtarget.cpp", "sim.h", "exact_sim.h", "rules.h", "stats.h"]
if subprocess.run(
    ["git", "-C", str(root), "diff", "--quiet", paper_runtime, "--", *runtime_paths],
    check=False,
).returncode != 0:
    raise SystemExit("Phase 0 changed frozen runtime behavior paths")
if subprocess.run(
    ["git", "-C", str(root), "diff", "--quiet", historical_completion, "--", "paper/source_data"],
    check=False,
).returncode != 0:
    raise SystemExit("historical frozen source data changed")

readme = require_phrases(
    bio / "README.md",
    (
        "historical source data stays immutable",
        "submission software changes tracked separately",
        "new holdout and application data receive new freeze ID",
        "make check-fasim-gasal2-paper-prep",
        "user-facing wrapper/CLI",
        "authority/candidate comparator",
        "external-tool wrapper",
        "manuscript template",
        "runtime_behavior_change = 0",
        "new_benchmark_started = 0",
    ),
)

journal = require_phrases(
    bio / "journal_requirements.md",
    (
        "2026-07-24",
        "https://academic.oup.com/bioinformatics/pages/instructions_for_authors",
        "https://academic.oup.com/bioinformatics/pages/scope_guidelines",
        "https://academic.oup.com/bioinformatics/pages/submission_online",
        "Application Note",
        "4 pages",
        "2,600 words",
        "2,000 words",
        "Availability and Implementation",
        "state-of-the-art",
        "real biological data",
        "figure resolution",
        "initial submission",
        "Supplementary",
        "Cloudflare",
        "requirements_rechecked = 1",
    ),
)
if "No difference identified" not in journal and "Difference identified" not in journal:
    raise SystemExit("journal requirements do not state whether the execution baseline changed")

claim_header, claims = read_tsv(bio / "claim_evidence.tsv")
expected_claim_header = [
    "claim_id",
    "allowed_wording",
    "prohibited_wording",
    "required_evidence",
    "authoritative_source",
    "promotion_gate",
    "phase",
    "status",
]
if claim_header != expected_claim_header:
    raise SystemExit(f"Bioinformatics claim ledger schema mismatch: {claim_header}")
if [row["claim_id"] for row in claims] != [f"B{index}" for index in range(1, 7)]:
    raise SystemExit("Bioinformatics claim ledger must contain ordered B1-B6")
for row in claims:
    if row["status"] not in allowed_statuses:
        raise SystemExit(f"invalid claim status: {row['claim_id']} {row['status']}")
    for field in expected_claim_header[1:-1]:
        if not row[field]:
            raise SystemExit(f"empty claim field: {row['claim_id']} {field}")

gap_header, gaps = read_tsv(bio / "gap_register.tsv")
expected_gap_header = [
    "gap_id",
    "capability",
    "required_phase",
    "current_evidence",
    "classification",
    "resolution_gate",
    "owner_only",
    "status",
]
if gap_header != expected_gap_header:
    raise SystemExit(f"Bioinformatics gap register schema mismatch: {gap_header}")
required_gap_ids = [
    "G01_user_cli",
    "G02_input_guard",
    "G03_comparator",
    "G04_json_report",
    "G05_container_lock",
    "G06_ci",
    "G07_external_tool",
    "G08_release_metadata",
    "G09_manuscript_template",
    "G10_journal_live_verification",
    "G11_owner_metadata",
    "G12_second_gpu_architecture",
]
if [row["gap_id"] for row in gaps] != required_gap_ids:
    raise SystemExit("gap register does not contain the stable Phase 0 capability audit")
for row in gaps:
    if row["status"] not in allowed_statuses:
        raise SystemExit(f"invalid gap status: {row['gap_id']} {row['status']}")
    if row["classification"] not in {"available", "partial", "missing", "access_blocked", "owner_only", "optional_unavailable"}:
        raise SystemExit(f"invalid gap classification: {row['gap_id']} {row['classification']}")
    if row["owner_only"] not in {"0", "1"}:
        raise SystemExit(f"invalid owner_only flag: {row['gap_id']}")
    if not row["current_evidence"] or not row["resolution_gate"]:
        raise SystemExit(f"unclassified gap: {row['gap_id']}")

owner = require_phrases(
    bio / "owner_metadata_needed.md",
    (
        "Author order",
        "Affiliations",
        "ORCIDs",
        "Funding",
        "CRediT",
        "Corresponding author",
        "Third-party redistribution",
        "Final software version",
        "Public DOI",
        "Signed release tag",
        "Submission-system answers",
    ),
)

manifest_header, manifest = read_tsv(bio / "submission_manifest.tsv")
expected_manifest_header = [
    "artifact_id",
    "path",
    "phase",
    "artifact_class",
    "authority",
    "freeze_or_epoch",
    "required",
    "status",
]
if manifest_header != expected_manifest_header:
    raise SystemExit(f"submission manifest schema mismatch: {manifest_header}")
phase0_paths = {
    "paper/bioinformatics/README.md",
    "paper/bioinformatics/journal_requirements.md",
    "paper/bioinformatics/claim_evidence.tsv",
    "paper/bioinformatics/gap_register.tsv",
    "paper/bioinformatics/owner_metadata_needed.md",
    "paper/bioinformatics/submission_manifest.tsv",
    "scripts/check_bioinformatics_phase0.sh",
}
manifest_paths = {row["path"] for row in manifest if row["phase"] == "0"}
if manifest_paths != phase0_paths:
    raise SystemExit("submission manifest does not enumerate the exact Phase 0 artifacts")
for row in manifest:
    if row["status"] not in allowed_statuses:
        raise SystemExit(f"invalid manifest status: {row['artifact_id']} {row['status']}")
    if row["required"] not in {"0", "1"}:
        raise SystemExit(f"invalid manifest required flag: {row['artifact_id']}")

makefile = require_phrases(
    root / "Makefile",
    (
        "check-bioinformatics-phase0:",
        "$(MAKE) check-fasim-gasal2-paper-prep",
        "bash ./scripts/check_bioinformatics_phase0.sh",
    ),
)

print("Bioinformatics Phase 0 checks OK")
print(f"submission_baseline_commit={historical_completion}")
print("historical_aggregate_check=pass")
print("head_ancestry_recorded=1")
print("journal_requirements_rechecked=1")
print("bioinformatics_claims=6")
print(f"classified_gaps={len(gaps)}")
print("runtime_behavior_change=0")
print("new_benchmark_started=0")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check
