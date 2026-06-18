#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_pretraceback_span_real_workload_parser"}"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_pretraceback_span_real_workloads.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/stderr.log" <<'EOF'
benchmark.total_wall_seconds=100.000000
benchmark.fasim_gasal2_traceback_requests=10
benchmark.fasim_gasal2_traceback_seconds=20.000000
benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds=40.000000
benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds=8.000000
benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds=12.000000
benchmark.fasim_top5_gasal2_phase_output_write_seconds=1.000000
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_attempts=10
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_retained_final_rows=2
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_removed_attempts=8
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_mapped_removed_attempts=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_unmapped_removed_attempts=7
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_same_final_row_different_descriptor=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cigar_dependent_duplicate=2
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_sort_or_dominance_removed=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_pretraceback_span_provable=3
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_cigar_dependent_span=1
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_full_output_safe_candidate_attempts=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_false_prune_shadow=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_missing_rows_shadow=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_extra_rows_shadow=0
benchmark.fasim_gasal2_pretraceback_pruning_eligibility_unknown=0
EOF

cat >"$WORK/top5.summary" <<'EOF'
top5_score_equal=true
top5_stability_equal=true
top5_nt_score_equal=true
EOF

cat >"$WORK/full_lite.summary" <<'EOF'
baseline_rows=20
candidate_rows=20
missing_rows=0
extra_rows=0
EOF

cat >"$WORK/tfosorted.summary" <<'EOF'
baseline_rows=20
candidate_rows=20
missing_rows=0
extra_rows=0
EOF

python3 "$PARSER" \
  --workload-name fixture_complete \
  --status complete \
  --stderr "$WORK/stderr.log" \
  --top5-summary "$WORK/top5.summary" \
  --full-lite-summary "$WORK/full_lite.summary" \
  --tfosorted-summary "$WORK/tfosorted.summary" \
  --target fixture.fa \
  --query H19.fa \
  --mode full_plain \
  --workers 1 \
  --group-target-records null \
  --output-mode lite \
  --gasal2-runtime-env FASIM_GASAL2_PRETRACEBACK_PRUNING_ELIGIBILITY=1 \
  --artifact-provenance "$WORK" \
  --output "$WORK/complete.tsv"

python3 "$PARSER" \
  --workload-name fixture_missing \
  --status missing \
  --target missing.fa \
  --query missing-rna.fa \
  --mode full_plain \
  --workers unknown \
  --group-target-records unknown \
  --output-mode lite \
  --artifact-provenance missing \
  --notes "required artifact lacks #171 counters" \
  --output "$WORK/missing.tsv"

python3 - "$WORK/complete.tsv" "$WORK/missing.tsv" <<'PY'
import csv
import sys
from pathlib import Path

complete_path = Path(sys.argv[1])
missing_path = Path(sys.argv[2])

def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 1:
        raise SystemExit(f"expected one row in {path}, got {len(rows)}")
    return rows[0]

complete = read_one(complete_path)
missing = read_one(missing_path)

required = {
    "workload_name",
    "status",
    "decision",
    "tracebacks_requested",
    "eligibility_attempts",
    "pretraceback_span_provable",
    "pretraceback_span_fraction_of_traceback",
    "pretraceback_span_fraction_of_removed",
    "post_traceback_only_attempts",
    "unknown_eligibility_attempts",
    "false_prune_shadow",
    "missing_rows_shadow",
    "extra_rows_shadow",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "timing_split_available",
    "projected_saved_traceback_seconds",
    "projected_wall_speedup_if_span_pruned",
    "artifact_provenance",
    "notes",
}
missing_columns = sorted(required.difference(complete))
if missing_columns:
    raise SystemExit(f"missing columns: {missing_columns}")

expected = {
    "workload_name": "fixture_complete",
    "status": "complete",
    "tracebacks_requested": "10",
    "eligibility_attempts": "10",
    "retained_final_rows": "2",
    "removed_attempts": "8",
    "pretraceback_span_provable": "3",
    "pretraceback_span_fraction_of_traceback": "0.300000",
    "pretraceback_span_fraction_of_removed": "0.375000",
    "post_traceback_only_attempts": "5",
    "unknown_eligibility_attempts": "0",
    "false_prune_shadow": "0",
    "missing_rows_shadow": "0",
    "extra_rows_shadow": "0",
    "baseline_lite_rows": "20",
    "candidate_lite_rows": "20",
    "full_lite_missing_rows": "0",
    "full_lite_extra_rows": "0",
    "baseline_tfosorted_rows": "20",
    "candidate_tfosorted_rows": "20",
    "full_tfosorted_missing_rows": "0",
    "full_tfosorted_extra_rows": "0",
    "top5_score_equal": "true",
    "top5_stability_equal": "true",
    "top5_nt_score_equal": "true",
    "timing_split_available": "true",
    "gasal2_traceback_seconds": "20.000000",
    "projected_saved_traceback_requests": "3",
    "projected_saved_traceback_fraction": "0.300000",
    "projected_saved_traceback_seconds": "6.000000",
    "projected_wall_speedup_if_span_pruned": "1.063830",
}
for key, value in expected.items():
    if complete.get(key) != value:
        raise SystemExit(f"{key}: expected {value!r}, got {complete.get(key)!r}")

if missing["status"] != "missing":
    raise SystemExit(f"missing row status incorrect: {missing['status']}")
if missing["decision"] != "no_decision":
    raise SystemExit(f"missing row decision incorrect: {missing['decision']}")
if missing["projected_saved_traceback_seconds"] != "unknown":
    raise SystemExit("missing row should not project saved seconds")
if "required artifact lacks #171 counters" not in missing["notes"]:
    raise SystemExit("missing row notes did not preserve reason")

print("ok")
PY
