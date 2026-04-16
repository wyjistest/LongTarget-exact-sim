#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

WORK=$(mktemp -d /tmp/longtarget-host-merge-select-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/manifest.tsv" <<'EOF'
case_id	case_index	query_length	target_length	logical_event_count	summary_count	candidate_count_after_context_apply	store_materialized_count	store_pruned_count	prune_ratio	gpu_mirror_requested
case-00000001	1	64	128	100	10	5	100	10	0.1	true
case-00000002	2	64	128	200	20	5	200	180	0.9	true
case-00000003	3	64	128	300	30	5	300	150	0.5	true
case-00000004	4	64	128	400	40	5	400	40	0.1	true
case-00000005	5	64	128	500	50	5	500	450	0.9	true
case-00000006	6	64	128	600	60	5	600	300	0.5	true
EOF

python3 ./scripts/select_sim_initial_host_merge_cases.py \
  --manifest "$WORK/manifest.tsv" \
  --output "$WORK/selected.tsv" \
  --limit 4

python3 - "$WORK/selected.tsv" <<'PY'
import csv
import sys

path = sys.argv[1]
with open(path, newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

actual = [row["case_id"] for row in rows]
expected = ["case-00000006", "case-00000005", "case-00000004", "case-00000003"]
assert actual == expected, (actual, expected)
expected_fields = [
    "case_id",
    "bucket_key",
    "summary_bin",
    "materialized_bin",
    "prune_bin",
    "logical_event_count",
    "summary_count",
    "store_materialized_count",
    "store_pruned_count",
    "prune_ratio",
    "selection_rank",
    "selection_reason",
]
assert rows, "expected selected rows"
assert list(rows[0].keys()) == expected_fields, rows[0].keys()
assert rows[0]["bucket_key"] == "s2|m2|p1"
assert rows[0]["summary_bin"] == "2"
assert rows[0]["materialized_bin"] == "2"
assert rows[0]["prune_bin"] == "1"
assert rows[0]["selection_rank"] == "1"
assert rows[0]["selection_reason"] == "bucket_representative"
PY

cat >"$WORK/coverage.manifest.tsv" <<'EOF'
case_id	case_index	query_length	target_length	logical_event_count	summary_count	candidate_count_after_context_apply	store_materialized_count	store_pruned_count	prune_ratio	gpu_mirror_requested
case-00000001	1	64	128	100	10	5	10	1	0.1	true
case-00000002	2	64	128	200	20	5	20	2	0.2	true
case-00000003	3	64	128	300	30	5	1000	3	0.3	true
case-00000004	4	64	128	400	40	5	40	4	0.4	true
case-00000005	5	64	128	500	50	5	50	5	0.5	true
case-00000006	6	64	128	600	60	5	60	6	0.6	true
EOF

python3 ./scripts/select_sim_initial_host_merge_cases.py \
  --manifest "$WORK/coverage.manifest.tsv" \
  --output "$WORK/coverage.selected.tsv" \
  --limit 4 \
  --strategy coverage_weighted \
  --logical-weight 1 \
  --materialized-weight 2 \
  --coverage-report "$WORK/coverage.report.json"

python3 - "$WORK/coverage.selected.tsv" "$WORK/coverage.report.json" <<'PY'
import csv
import json
import math
import sys

selected_path = sys.argv[1]
report_path = sys.argv[2]

with open(selected_path, newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

actual = [row["case_id"] for row in rows]
expected = ["case-00000003", "case-00000006", "case-00000005", "case-00000004"]
assert actual == expected, (actual, expected)
assert all(row["selection_reason"] == "bucket_representative" for row in rows)

report = json.load(open(report_path, encoding="utf-8"))
assert report["strategy"] == "coverage_weighted", report
assert report["logical_weight"] == 1.0, report
assert report["materialized_weight"] == 2.0, report
assert report["limit"] == 4, report
assert report["selected_case_count"] == 4, report
assert report["covered_bucket_count"] == 4, report
assert report["total_bucket_count"] == 5, report
assert report["selected_case_ids"] == expected, report
assert report["selected_bucket_keys"] == ["s1|m2|p1", "s2|m2|p2", "s2|m1|p2", "s1|m1|p1"], report
assert math.isclose(report["predicted_covered_bucket_share"], 0.8, rel_tol=1e-9), report
assert math.isclose(report["predicted_covered_logical_event_share"], 1800.0 / 2100.0, rel_tol=1e-9), report
assert math.isclose(report["predicted_covered_store_materialized_share"], 1150.0 / 1180.0, rel_tol=1e-9), report
PY
