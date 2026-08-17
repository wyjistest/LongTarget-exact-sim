#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase8}"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

required=(
  goal-final.md paper/outline.md paper/methods_notes.md paper/results_claims.md
  paper/limitations.md paper/related_work_inventory.tsv paper/references.bib
  paper/reporting_checklist.md paper/authorship_metadata_needed.md
  reproduce/render_manuscript_source_kit.py
)
for relative in "${required[@]}"; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing paper Phase 8 dependency: $relative" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

python3 -m py_compile "$ROOT/reproduce/render_manuscript_source_kit.py"
rm -rf "$WORK"
mkdir -p "$WORK"
python3 "$ROOT/reproduce/render_manuscript_source_kit.py" \
  --claims "$ROOT/paper/claim_evidence.tsv" \
  --output "$WORK/results_claims.md"
cmp "$ROOT/paper/results_claims.md" "$WORK/results_claims.md"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
paper = root / "paper"


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
if state.get("active_phase") not in {"9", "complete"} or state.get("phase_8_status") != "pass":
    raise SystemExit("goal state has not completed paper Phase 8")
if state.get("paper_runtime_epoch") != "0" or state.get("data_freeze_id") != "paper-data-v1-dccfd49-20260716":
    raise SystemExit("runtime or data freeze drifted")

outline = (paper / "outline.md").read_text(encoding="utf-8")
for section in ("Introduction", "Methods", "Results", "Discussion", "Availability And Reproducibility"):
    if f"## {section}" not in outline:
        raise SystemExit(f"outline section missing: {section}")
for claim in (f"C{index}" for index in range(1, 8)):
    if claim not in outline:
        raise SystemExit(f"outline does not map claim: {claim}")
if len(re.findall(r"^\d+\. ", outline, flags=re.MULTILINE)) != 3:
    raise SystemExit("outline must contain exactly three title candidates")

methods = (paper / "methods_notes.md").read_text(encoding="utf-8")
for phrase in (
    "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f",
    "106d94ee53fc847214fb05f2f9f892538a5d3baf",
    "MAX_QUERY_LEN=2812",
    "one worker per GPU",
    "paper/workload_manifest.tsv",
    "20260715",
    "10,000-resample bootstrap",
    "fails closed",
):
    if phrase not in methods:
        raise SystemExit(f"methods note missing checked protocol fact: {phrase}")
for unsupported in ("we assume", "presumably", "default settings were used"):
    if unsupported in methods.lower():
        raise SystemExit(f"methods contain an unverified default: {unsupported}")

claims = (paper / "results_claims.md").read_text(encoding="utf-8")
_, ledger = read_tsv(paper / "claim_evidence.tsv")
for row in ledger:
    for value in (
        row["claim_id"], row["current_n"], row["current_value"],
        row["final_interval_or_range"], row["correctness_status"],
        row["source_data_filter"], row["allowed_manuscript_wording"], row["gap"],
    ):
        if value not in claims:
            raise SystemExit(f"results source sheet drifted from {row['claim_id']}: {value}")

limitations = (paper / "limitations.md").read_text(encoding="utf-8")
for phrase in (
    "query_len <= 2812", "not a full-output replacement", "Three of thirteen",
    "Full 121-segment KCNQ1OT1 and full hg38 were not run",
    "one worker per 24 GB GPU", "Traceback", "does not establish biological superiority",
):
    if phrase not in limitations:
        raise SystemExit(f"limitation missing: {phrase}")

fields, references = read_tsv(paper / "related_work_inventory.tsv")
expected_fields = [
    "citation_id", "title", "authors", "year", "venue", "doi", "pmid",
    "primary_source_checked", "metadata_checked_on", "relevance", "claim_supported",
]
if fields != expected_fields or len(references) != 7:
    raise SystemExit("related-work inventory schema/count drifted")
expected_ids = {
    "longtarget2015": ("10.1093/bioinformatics/btu643", "25262155", "2015"),
    "fasimlongtarget2022": ("10.1016/j.csbj.2022.06.017", "35832611", "2022"),
    "gasal2_2019": ("10.1186/s12859-019-3086-9", "31653208", "2019"),
    "triplexator2012": ("10.1101/gr.130237.111", "22550012", "2012"),
    "threeplex2023": ("10.1016/j.csbj.2023.05.016", "37273849", "2023"),
    "cudasw4_2024": ("10.1186/s12859-024-05965-6", "39488701", "2024"),
    "accelign2026": ("10.1186/s12859-026-06521-0", "42324518", "2026"),
}
if {row["citation_id"] for row in references} != set(expected_ids):
    raise SystemExit("related-work citation IDs drifted")
bib = (paper / "references.bib").read_text(encoding="utf-8")
for row in references:
    doi, pmid, year = expected_ids[row["citation_id"]]
    if (row["doi"], row["pmid"], row["year"]) != (doi, pmid, year):
        raise SystemExit(f"verified citation metadata drifted: {row['citation_id']}")
    if row["metadata_checked_on"] != "2026-07-16":
        raise SystemExit(f"citation verification date missing: {row['citation_id']}")
    sources = row["primary_source_checked"]
    if f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" not in sources or f"https://doi.org/{doi}" not in sources:
        raise SystemExit(f"primary citation sources incomplete: {row['citation_id']}")
    entry = re.search(rf"@article\{{{re.escape(row['citation_id'])},(.*?)(?=\n\}})", bib, flags=re.DOTALL)
    if not entry or f"doi = {{{doi}}}" not in entry.group(1) or f"pmid = {{{pmid}}}" not in entry.group(1):
        raise SystemExit(f"BibTeX entry drifted: {row['citation_id']}")

reporting = (paper / "reporting_checklist.md").read_text(encoding="utf-8")
for phrase in ("Software And Environment", "Inputs And Protocol", "Correctness And Failures", "Availability"):
    if phrase not in reporting:
        raise SystemExit(f"reporting checklist section missing: {phrase}")
authors = (paper / "authorship_metadata_needed.md").read_text(encoding="utf-8")
if authors.count("[AUTHOR INPUT REQUIRED]") < 10 or "[RELEASE INPUT REQUIRED]" not in authors:
    raise SystemExit("authorship placeholders are incomplete")
for forbidden_file in ("manuscript.md", "abstract.md"):
    if (paper / forbidden_file).exists():
        raise SystemExit(f"full manuscript prose was generated: {forbidden_file}")

print("GASAL2 paper Phase 8 gate OK")
print("claims_mapped=7")
print("verified_references=7")
print("title_candidates=3")
print("invented_authorship_fields=0")
PY

git -C "$ROOT" diff --check
echo "GASAL2 paper Phase 8 checks OK"
