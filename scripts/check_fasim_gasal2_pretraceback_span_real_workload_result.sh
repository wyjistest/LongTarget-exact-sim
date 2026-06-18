#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULT_TSV="${RESULT_TSV:-"$ROOT/docs/fasim_gasal2_pretraceback_span_real_workload_characterization.tsv"}"
DOC="${DOC:-"$ROOT/docs/fasim_gasal2_pretraceback_span_real_workload_characterization.md"}"

if [[ ! -s "$RESULT_TSV" ]]; then
  echo "missing result TSV: $RESULT_TSV" >&2
  exit 1
fi
if [[ ! -s "$DOC" ]]; then
  echo "missing result doc: $DOC" >&2
  exit 1
fi

python3 - "$RESULT_TSV" "$DOC" <<'PY'
import csv
import re
import sys
from pathlib import Path

result_tsv = Path(sys.argv[1])
doc_path = Path(sys.argv[2])
doc = doc_path.read_text(encoding="utf-8")

required_columns = {
    "workload_name",
    "status",
    "decision",
    "target",
    "query",
    "mode",
    "workers",
    "group_target_records",
    "output_mode",
    "gasal2_runtime_env",
    "tracebacks_requested",
    "eligibility_attempts",
    "retained_final_rows",
    "removed_attempts",
    "pretraceback_span_provable",
    "pretraceback_span_fraction_of_traceback",
    "pretraceback_span_fraction_of_removed",
    "post_traceback_only_attempts",
    "unknown_eligibility_attempts",
    "mapped_removed_attempts",
    "unmapped_removed_attempts",
    "cigar_dependent_duplicate",
    "cigar_dependent_span",
    "same_final_row_different_descriptor",
    "sort_or_dominance_removed",
    "full_output_safe_candidate_attempts",
    "false_prune_shadow",
    "missing_rows_shadow",
    "extra_rows_shadow",
    "baseline_lite_rows",
    "candidate_lite_rows",
    "full_lite_missing_rows",
    "full_lite_extra_rows",
    "baseline_tfosorted_rows",
    "candidate_tfosorted_rows",
    "full_tfosorted_missing_rows",
    "full_tfosorted_extra_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "timing_split_available",
    "gasal2_wall_seconds",
    "gasal2_extend_seconds",
    "gasal2_convert_seconds",
    "gasal2_traceback_seconds",
    "exact_column_seconds",
    "output_write_seconds",
    "projected_saved_traceback_requests",
    "projected_saved_traceback_fraction",
    "projected_saved_traceback_seconds",
    "projected_wall_speedup_if_span_pruned",
    "artifact_provenance",
    "notes",
}
required_workloads = {
    "chr22_full_plain",
    "malat1_group32_two_contract",
    "neat1_attempt_consumer_control",
}
numeric_or_unknown = re.compile(r"^(unknown|-?[0-9]+(?:\.[0-9]+)?)$")
integer_or_unknown = re.compile(r"^(unknown|[0-9]+)$")
boolean_or_unknown = {"true", "false", "unknown"}

with result_tsv.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    if reader.fieldnames is None:
        raise SystemExit("result TSV has no header")
    missing_columns = sorted(required_columns.difference(reader.fieldnames))
    if missing_columns:
        raise SystemExit(f"result TSV missing required columns: {missing_columns}")
    rows = list(reader)

by_workload = {row["workload_name"]: row for row in rows}
missing_rows = sorted(required_workloads.difference(by_workload))
if missing_rows:
    raise SystemExit(f"result TSV missing required workload rows: {missing_rows}")

complete_rows = []
for name in sorted(required_workloads):
    row = by_workload[name]
    status = row["status"]
    decision = row["decision"]
    if status == "missing":
        if decision != "no_decision":
            raise SystemExit(f"{name}: missing row must use decision=no_decision")
        if not row["notes"] or row["notes"] == "unknown":
            raise SystemExit(f"{name}: missing row must explain missing evidence")
        continue
    if status != "complete":
        raise SystemExit(f"{name}: unexpected status={status}")
    complete_rows.append(row)
    for key in (
        "tracebacks_requested",
        "eligibility_attempts",
        "retained_final_rows",
        "removed_attempts",
        "pretraceback_span_provable",
        "post_traceback_only_attempts",
        "unknown_eligibility_attempts",
        "mapped_removed_attempts",
        "unmapped_removed_attempts",
        "cigar_dependent_duplicate",
        "cigar_dependent_span",
        "same_final_row_different_descriptor",
        "sort_or_dominance_removed",
        "full_output_safe_candidate_attempts",
        "false_prune_shadow",
        "missing_rows_shadow",
        "extra_rows_shadow",
        "baseline_lite_rows",
        "candidate_lite_rows",
        "full_lite_missing_rows",
        "full_lite_extra_rows",
        "baseline_tfosorted_rows",
        "candidate_tfosorted_rows",
        "full_tfosorted_missing_rows",
        "full_tfosorted_extra_rows",
        "projected_saved_traceback_requests",
    ):
        if not integer_or_unknown.match(row[key]):
            raise SystemExit(f"{name}: {key} must be integer or unknown, got {row[key]!r}")
        if row[key] == "unknown":
            raise SystemExit(f"{name}: complete row must not use unknown for {key}")
    for key in (
        "top5_score_equal",
        "top5_stability_equal",
        "top5_nt_score_equal",
        "timing_split_available",
    ):
        if row[key] not in boolean_or_unknown:
            raise SystemExit(f"{name}: {key} must be true/false/unknown, got {row[key]!r}")
    if row["timing_split_available"] == "true":
        if not numeric_or_unknown.match(row["projected_saved_traceback_seconds"]):
            raise SystemExit(f"{name}: projected seconds is not numeric/unknown")
        if row["projected_saved_traceback_seconds"] == "unknown":
            raise SystemExit(f"{name}: split timing cannot use unknown projected seconds")
    else:
        if row["projected_saved_traceback_seconds"] != "unknown":
            raise SystemExit(f"{name}: unknown split timing must use unknown projected seconds")
    if row["projected_saved_traceback_fraction"] != "unknown":
        fraction = float(row["projected_saved_traceback_fraction"])
        if not (0.0 <= fraction <= 1.0):
            raise SystemExit(f"{name}: projected fraction out of range: {fraction}")
    else:
        if row["tracebacks_requested"] != "0":
            raise SystemExit(
                f"{name}: projected fraction can be unknown only when tracebacks_requested=0"
            )
    if row["tracebacks_requested"] == "0" and row["pretraceback_span_provable"] != "0":
        raise SystemExit(f"{name}: zero-traceback row cannot have span candidates")

required_doc_phrases = [
    "telemetry-only",
    "No real pruning is enabled",
    "generic pre-traceback dedup is unsupported",
    "CIGAR/representative/sort-dependent",
    "pretraceback_span_provable",
]
for phrase in required_doc_phrases:
    if phrase not in doc:
        raise SystemExit(f"result doc missing required phrase: {phrase}")

allowed_doc_decisions = {
    "Decision: strong_go_for_default_off_span_prune_shadow",
    "Decision: weak_go_more_characterization_needed",
    "Decision: no_go_span_bucket_not_material",
    "Decision: no_decision_missing_real_workload_data",
}
if not any(decision in doc for decision in allowed_doc_decisions):
    raise SystemExit("result doc missing an allowed Decision label")

for forbidden in (
    "safe to prune all final_sort_dedup_removed",
    "generic pre-traceback dedup supported",
    "GASAL2 replaces aligner.Align",
):
    if forbidden in doc:
        raise SystemExit(f"result doc overclaims forbidden phrase: {forbidden}")

if "FASIM_GASAL2_PRETRACEBACK_SPAN_PRUNE=1" in doc:
    raise SystemExit("result doc must not add or recommend real span prune env")

if complete_rows:
    for row in complete_rows:
        if row["unknown_eligibility_attempts"] != "0":
            raise SystemExit(
                f"{row['workload_name']}: complete row has unknown eligibility attempts"
            )
else:
    if "Decision: no_decision_missing_real_workload_data" not in doc:
        raise SystemExit("all rows missing, doc must use no_decision_missing_real_workload_data")

print("ok")
PY
