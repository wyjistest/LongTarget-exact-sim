#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_pretraceback_span_prune_shadow_parser"}"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_pretraceback_span_prune_shadow.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/stderr.log" <<'EOF'
benchmark.total_wall_seconds=70.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_requested=1
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_active=1
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_decision=shadow_clean_more_characterization_needed
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_batches=2
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_input_attempts=1000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_authority_selected_attempts=100
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_kept_selected_attempts=87
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_skipped_selected_attempts=13
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_skipped_fraction_of_selected=0.130000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_score_requests=1000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_score_batches=10
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_requests=87
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_batches=3
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_fill_seconds=1.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_submit_seconds=2.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_wait_seconds=3.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_result_copy_seconds=4.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_cigar_vector_seconds=5.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_cigar_string_seconds=6.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_traceback_seconds=21.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_total_seconds=24.000000
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_authority_skipped_seen=13
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_authority_skipped_invalid_span=13
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_false_prune=0
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_missing_rows=0
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_extra_rows=0
benchmark.fasim_gasal2_pretraceback_span_prune_shadow_fallbacks=0
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
  --workload-name fixture_shadow \
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
  --gasal2-runtime-env FASIM_GASAL2_PRETRACEBACK_SPAN_PRUNE_SHADOW=1 \
  --artifact-provenance "$WORK" \
  --output "$WORK/complete.tsv"

python3 - "$WORK/complete.tsv" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one row, got {len(rows)}")
row = rows[0]

required = {
    "workload_name",
    "status",
    "decision",
    "shadow_requested",
    "shadow_active",
    "shadow_batches",
    "input_attempts",
    "authority_selected_attempts",
    "kept_selected_attempts",
    "skipped_selected_attempts",
    "skipped_fraction_of_selected",
    "shadow_score_requests",
    "shadow_traceback_requests",
    "shadow_traceback_seconds",
    "shadow_total_seconds",
    "authority_skipped_seen",
    "authority_skipped_invalid_span",
    "false_prune",
    "missing_rows",
    "extra_rows",
    "fallbacks",
    "full_lite_missing_rows",
    "full_lite_extra_rows",
    "full_tfosorted_missing_rows",
    "full_tfosorted_extra_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "artifact_provenance",
}
missing = sorted(required.difference(row))
if missing:
    raise SystemExit(f"missing columns: {missing}")

expected = {
    "workload_name": "fixture_shadow",
    "status": "complete",
    "decision": "shadow_clean_more_characterization_needed",
    "shadow_requested": "1",
    "shadow_active": "1",
    "shadow_batches": "2",
    "input_attempts": "1000",
    "authority_selected_attempts": "100",
    "kept_selected_attempts": "87",
    "skipped_selected_attempts": "13",
    "skipped_fraction_of_selected": "0.130000",
    "shadow_score_requests": "1000",
    "shadow_traceback_requests": "87",
    "shadow_traceback_seconds": "21.000000",
    "shadow_total_seconds": "24.000000",
    "authority_skipped_seen": "13",
    "authority_skipped_invalid_span": "13",
    "false_prune": "0",
    "missing_rows": "0",
    "extra_rows": "0",
    "fallbacks": "0",
    "full_lite_missing_rows": "0",
    "full_lite_extra_rows": "0",
    "full_tfosorted_missing_rows": "0",
    "full_tfosorted_extra_rows": "0",
    "top5_score_equal": "true",
    "top5_stability_equal": "true",
    "top5_nt_score_equal": "true",
}
for key, value in expected.items():
    if row.get(key) != value:
        raise SystemExit(f"{key}: expected {value!r}, got {row.get(key)!r}")
print("ok")
PY
