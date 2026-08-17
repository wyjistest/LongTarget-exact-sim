#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_short_query_generalization_panel"}"
SUMMARY="$WORK/summary.tsv"
NEGATIVE="$WORK/full_negative_controls.tsv"
AUDIT="$WORK/runtime_audit.txt"
DOC="$ROOT/docs/fasim_gasal2_short_query_generalization_panel.md"
RUNNER="$ROOT/scripts/characterize_fasim_gasal2_short_query_generalization_panel.sh"
MAKEFILE="$ROOT/Makefile"

for path in "$SUMMARY" "$NEGATIVE" "$AUDIT" "$DOC" "$RUNNER" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing short-query generalization dependency: $path" >&2
    exit 1
  fi
done

python3 - "$SUMMARY" "$NEGATIVE" "$AUDIT" "$DOC" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
negative_path = Path(sys.argv[2])
audit_path = Path(sys.argv[3])
doc_text = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

rows = list(csv.DictReader(summary_path.open(newline="", encoding="utf-8"), delimiter="\t"))
neg = list(csv.DictReader(negative_path.open(newline="", encoding="utf-8"), delimiter="\t"))
audit: dict[str, str] = {}
for raw in audit_path.read_text(encoding="utf-8").splitlines():
    if "=" in raw:
        key, value = raw.split("=", 1)
        audit[key] = value

if audit.get("decision") != "short_query_generalization_clean":
    raise SystemExit(f"unexpected decision: {audit}")
if int(audit.get("panel_rows", "0")) != len(rows):
    raise SystemExit(f"panel_rows disagrees with summary: {audit}")
if int(audit.get("completed_rows", "0")) != len(rows):
    raise SystemExit(f"not all panel rows completed: {audit}")
if int(audit.get("top5_clean_supported_non_h19_rows", "0")) < 8:
    raise SystemExit(f"insufficient non-H19 clean supported rows: {audit}")
if int(audit.get("negative_controls_guarded", "0")) != 3:
    raise SystemExit(f"expected three guarded negative controls: {audit}")
if float(audit.get("median_speedup_clean", "0")) < 10.0:
    raise SystemExit(f"median clean speedup too low: {audit}")

def find_row(query: str, segment: str) -> dict[str, str]:
    matches = [row for row in rows if row["query_name"] == query and row["segment_kind"] == segment]
    if len(matches) != 1:
        raise SystemExit(f"expected one row for {query} {segment}, got {len(matches)}")
    return matches[0]

def is_clean(row: dict[str, str]) -> bool:
    return (
        row["status"] == "completed"
        and row["top5_tfo_score_equal"] == "true"
        and row["top5_tfo_stability_equal"] == "true"
        and row["top5_tfo_nt_score_equal"] == "true"
        and row["query_preflight_supported"] == "1"
        and row["length_guard_fallbacks"] == "0"
        and row["gasal2_requests"] not in {"", "0"}
    )

def require_clean(query: str, segment: str, min_speedup: float = 1.0) -> None:
    row = find_row(query, segment)
    if not is_clean(row):
        raise SystemExit(f"expected clean row for {query} {segment}: {row}")
    if float(row["speedup_vs_baseline"]) < min_speedup:
        raise SystemExit(f"speedup too low for {query} {segment}: {row}")

require_clean("H19", "full", 10.0)
for query in ("MALAT1", "NEAT1"):
    for length in (1024, 2048, 2812):
        require_clean(query, f"fragment_mid_{length}", 10.0)
for length in (2048, 2812):
    require_clean("KCNQ1OT1", f"fragment_mid_{length}", 10.0)

meg3 = find_row("MEG3", "full")
if not (
    meg3["top5_tfo_score_equal"] == "true"
    and meg3["top5_tfo_stability_equal"] == "false"
    and meg3["top5_tfo_nt_score_equal"] == "true"
):
    raise SystemExit(f"expected acknowledged MEG3 boundary mismatch: {meg3}")
kcnq1024 = find_row("KCNQ1OT1", "fragment_mid_1024")
if not (
    kcnq1024["top5_tfo_score_equal"] == "false"
    and kcnq1024["top5_tfo_stability_equal"] == "true"
    and kcnq1024["top5_tfo_nt_score_equal"] == "false"
):
    raise SystemExit(f"expected acknowledged KCNQ1OT1 1024 boundary mismatch: {kcnq1024}")

negative_by_query = {row["query_name"]: row for row in neg}
for query, expected_len in (("MALAT1", 8708), ("NEAT1", 22767), ("KCNQ1OT1", 91667)):
    row = negative_by_query.get(query)
    if row is None:
        raise SystemExit(f"missing negative control: {query}")
    if row["query_preflight_supported"] != "0":
        raise SystemExit(f"negative control should be unsupported: {row}")
    if int(float(row["query_preflight_query_len"])) != expected_len:
        raise SystemExit(f"negative control length mismatch: {row}")
    if int(float(row["query_preflight_max_query_len"])) != 2812:
        raise SystemExit(f"negative control max length mismatch: {row}")

required_doc = [
    "not H19 sequence-special-cased",
    "not a universal guarantee for every short query",
    "verified 2812-bp GASAL2 query contract",
    "top5_clean_supported_non_h19_rows = 8",
    "MALAT1 mid 2812",
    "NEAT1 mid 2812",
    "KCNQ1OT1 mid 2812",
    "MEG3 full 1582",
    "KCNQ1OT1 mid 1024",
    "full-length inputs exceed the current unsegmented GASAL2 contract",
    "default-off, contract-checked short-query accelerator",
]
missing = [phrase for phrase in required_doc if phrase not in doc_text]
if missing:
    raise SystemExit("generalization doc missing phrase: " + missing[0])

for phrase in (
    "characterize-fasim-gasal2-short-query-generalization-panel:",
    "check-fasim-gasal2-short-query-generalization-panel-result:",
    "scripts/check_fasim_gasal2_short_query_generalization_panel_result.sh",
):
    if phrase not in makefile:
        raise SystemExit(f"Makefile missing phrase: {phrase}")
PY

echo "GASAL2 short-query generalization panel OK"
