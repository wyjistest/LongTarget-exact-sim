#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULT="$ROOT/docs/fasim_gasal2_pretraceback_span_prune_shadow.tsv"

python3 - "$RESULT" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(f"missing result table: {path}")

with path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

if len(rows) != 1:
    raise SystemExit(f"expected one result row, got {len(rows)}")

row = rows[0]
expected = {
    "workload_name": "chr22_slice_10m_12m",
    "status": "complete",
    "decision": "shadow_clean_more_characterization_needed",
    "shadow_requested": "1",
    "shadow_active": "1",
    "authority_selected_attempts": "175193",
    "kept_selected_attempts": "175171",
    "skipped_selected_attempts": "22",
    "shadow_traceback_requests": "175171",
    "authority_skipped_seen": "22",
    "authority_skipped_invalid_span": "22",
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

fraction = float(row["skipped_fraction_of_selected"])
if not (0.0 < fraction < 0.001):
    raise SystemExit(f"unexpected skipped fraction: {fraction}")

print("ok")
PY
