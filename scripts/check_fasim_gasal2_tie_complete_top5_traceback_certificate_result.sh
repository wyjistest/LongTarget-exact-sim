#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_tie_complete_top5_traceback_certificate.md"
RESULT="$ROOT/docs/fasim_gasal2_tie_complete_top5_traceback_certificate.tsv"

if [[ ! -s "$DOC" ]]; then
  echo "missing result doc: $DOC" >&2
  exit 1
fi
if [[ ! -s "$RESULT" ]]; then
  echo "missing result table: $RESULT" >&2
  exit 1
fi

python3 - "$DOC" "$RESULT" <<'PY'
import csv
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
result = Path(sys.argv[2])

required_doc = [
    "tie-complete final-top5 traceback certificate",
    "FASIM_GASAL2_TOP5_TRACEBACK_CERTIFICATE_SHADOW=1",
    "no real pruning",
    "no span predicate changes",
    "fixed threshold 116 is historical oracle reference only",
    "full lite equivalence: not claimed",
    "full TFOsorted equivalence: not claimed",
    "raw candidate rank5 threshold is unsound",
    "stability_certificate_supported=false",
    "nt_score_certificate_supported=false",
]
missing_doc = [phrase for phrase in required_doc if phrase not in doc]
if missing_doc:
    raise SystemExit("result doc missing phrases: " + ", ".join(missing_doc))

with result.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if not rows:
    raise SystemExit("result table has no rows")

required_cols = {
    "workload_name",
    "status",
    "decision",
    "baseline_traceback_requests",
    "certificate_traceback_requests",
    "tracebacks_skipped",
    "score_certificate_supported",
    "stability_certificate_supported",
    "nt_score_certificate_supported",
    "top5_score_rows_order_equal",
    "top5_stability_rows_order_equal",
    "top5_nt_score_rows_order_equal",
    "false_prune",
    "missing_top5_rows",
    "extra_top5_rows",
    "full_lite_claim",
    "full_tfosorted_claim",
}
missing_cols = sorted(required_cols.difference(rows[0]))
if missing_cols:
    raise SystemExit(f"result table missing columns: {missing_cols}")

material = [row for row in rows if row["workload_name"] == "chr22_slice_10m_12m"]
if len(material) != 1:
    raise SystemExit("expected one chr22_slice_10m_12m result row")
row = material[0]
expected = {
    "status": "complete",
    "decision": "no_go_unsupported_modes",
    "score_certificate_supported": "true",
    "stability_certificate_supported": "false",
    "nt_score_certificate_supported": "false",
    "top5_score_rows_order_equal": "true",
    "top5_stability_rows_order_equal": "true",
    "top5_nt_score_rows_order_equal": "true",
    "false_prune": "0",
    "missing_top5_rows": "0",
    "extra_top5_rows": "0",
    "full_lite_claim": "not_claimed",
    "full_tfosorted_claim": "not_claimed",
}
for key, value in expected.items():
    if row.get(key) != value:
        raise SystemExit(f"{key}: expected {value!r}, got {row.get(key)!r}")

baseline = int(row["baseline_traceback_requests"])
certificate = int(row["certificate_traceback_requests"])
skipped = int(row["tracebacks_skipped"])
if baseline <= 0:
    raise SystemExit("baseline traceback requests must be positive")
if certificate != baseline:
    raise SystemExit("unsupported modes must keep all authority selected candidates")
if skipped != 0:
    raise SystemExit("unsupported-mode conservative union should skip zero tracebacks")

print("ok")
PY
