#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_tie_complete_top5_traceback_certificate_parser"}"
PARSER="$ROOT/scripts/summarize_fasim_gasal2_tie_complete_top5_traceback_certificate.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/stderr.log" <<'EOF'
benchmark.total_wall_seconds=70.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_requested=1
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_active=1
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_decision=no_go_unsupported_modes
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_baseline_traceback_requests=100
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_certificate_traceback_requests=100
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_tracebacks_skipped=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_tracebacks_skipped_fraction=0.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_score_certificate_supported=1
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_stability_certificate_supported=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_nt_score_certificate_supported=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_score_rank5_boundary=116
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_stability_rank5_boundary=unknown
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_nt_score_rank5_boundary=unknown
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_score_boundary_ties=3
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_stability_boundary_ties=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_nt_score_boundary_ties=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_score_groups_processed=7
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_stability_groups_processed=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_nt_score_groups_processed=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_boundary_updates=4
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_invalid_after_traceback=5
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_filtered_nt_after_traceback=6
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_dedup_removed_after_traceback=7
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_certificate_pack_seconds=1.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_certificate_traceback_seconds=2.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_certificate_convert_seconds=3.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_certificate_total_seconds=6.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_measured_net_saved_seconds=0.000000
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_false_prune=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_missing_top5_rows=0
benchmark.fasim_gasal2_top5_traceback_certificate_shadow_extra_top5_rows=0
EOF

cat >"$WORK/top5.summary" <<'EOF'
top5_score_equal=true
top5_stability_equal=true
top5_nt_score_equal=true
top5_score_rows_order_equal=true
top5_stability_rows_order_equal=true
top5_nt_score_rows_order_equal=true
EOF

python3 "$PARSER" \
  --workload-name fixture_top5_certificate \
  --status complete \
  --stderr "$WORK/stderr.log" \
  --top5-summary "$WORK/top5.summary" \
  --target chr22.fixture.fa \
  --query H19.fa \
  --mode full_plain_top5 \
  --workers 1 \
  --group-target-records null \
  --output-contract gasal2_top5_column_pruned_scoreinfo_artifact_v1 \
  --artifact-provenance "$WORK" \
  --notes "parser fixture" \
  --output "$WORK/result.tsv"

python3 - "$WORK/result.tsv" <<'PY'
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
    "target",
    "query",
    "mode",
    "workers",
    "group_target_records",
    "output_contract",
    "baseline_traceback_requests",
    "certificate_traceback_requests",
    "tracebacks_skipped",
    "tracebacks_skipped_fraction",
    "score_certificate_supported",
    "stability_certificate_supported",
    "nt_score_certificate_supported",
    "score_rank5_boundary",
    "stability_rank5_boundary",
    "nt_score_rank5_boundary",
    "score_boundary_ties",
    "stability_boundary_ties",
    "nt_score_boundary_ties",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_score_rows_order_equal",
    "top5_stability_rows_order_equal",
    "top5_nt_score_rows_order_equal",
    "false_prune",
    "missing_top5_rows",
    "extra_top5_rows",
    "measured_net_saved_seconds",
    "wall_speedup_vs_authority",
    "full_lite_claim",
    "full_tfosorted_claim",
    "artifact_provenance",
    "notes",
}
missing = sorted(required.difference(row))
if missing:
    raise SystemExit(f"missing columns: {missing}")

expected = {
    "workload_name": "fixture_top5_certificate",
    "status": "complete",
    "decision": "no_go_unsupported_modes",
    "baseline_traceback_requests": "100",
    "certificate_traceback_requests": "100",
    "tracebacks_skipped": "0",
    "tracebacks_skipped_fraction": "0.000000",
    "score_certificate_supported": "true",
    "stability_certificate_supported": "false",
    "nt_score_certificate_supported": "false",
    "score_rank5_boundary": "116",
    "stability_rank5_boundary": "unknown",
    "nt_score_rank5_boundary": "unknown",
    "score_boundary_ties": "3",
    "top5_score_equal": "true",
    "top5_stability_equal": "true",
    "top5_nt_score_equal": "true",
    "top5_score_rows_order_equal": "true",
    "top5_stability_rows_order_equal": "true",
    "top5_nt_score_rows_order_equal": "true",
    "false_prune": "0",
    "missing_top5_rows": "0",
    "extra_top5_rows": "0",
    "measured_net_saved_seconds": "0.000000",
    "wall_speedup_vs_authority": "1.000000",
    "full_lite_claim": "not_claimed",
    "full_tfosorted_claim": "not_claimed",
}
for key, value in expected.items():
    if row.get(key) != value:
        raise SystemExit(f"{key}: expected {value!r}, got {row.get(key)!r}")

print("ok")
PY
