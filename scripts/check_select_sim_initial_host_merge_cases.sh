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
