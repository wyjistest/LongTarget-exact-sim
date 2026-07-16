#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/gasal2-paper-reproduction-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

python3 - "$ROOT" <<'PY'
import csv
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
source = root / "paper/source_data"

def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()

with (source / "source_data_manifest.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 11:
    raise SystemExit("source manifest count drifted")
for row in rows:
    path = source / row["path"]
    if not path.is_file() or path.stat().st_size != int(row["size_bytes"]) or digest(path) != row["sha256"]:
        raise SystemExit(f"source checksum mismatch: {path}")
PY

python3 "$ROOT/reproduce/analyze_results.py" \
  --pairs "$ROOT/paper/source_data/paired_speedups.tsv" \
  --summary-tsv "$WORK/paired_speedup_summary.tsv" \
  --summary-json "$WORK/paired_speedup_summary.json" >/dev/null
cmp "$ROOT/paper/source_data/paired_speedup_summary.tsv" "$WORK/paired_speedup_summary.tsv"
cmp "$ROOT/paper/source_data/paired_speedup_summary.json" "$WORK/paired_speedup_summary.json"

python3 "$ROOT/reproduce/render_figures.py" \
  --source-dir "$ROOT/paper/source_data" \
  --output-root "$WORK/paper" >/dev/null
cmp "$ROOT/paper/captions.md" "$WORK/paper/captions.md"
diff -r "$ROOT/paper/figures" "$WORK/paper/figures"
diff -r "$ROOT/paper/tables" "$WORK/paper/tables"
diff -r "$ROOT/paper/supplementary" "$WORK/paper/supplementary"

echo "quick_reproduction=pass"
echo "data_freeze_id=paper-data-v1-dccfd49-20260716"
echo "source_manifest_files=11"
echo "paired_summary_workloads=21"
echo "render_manifest_files=30"
echo "figure_sets=5"
echo "table_bundles=4"
echo "gpu_benchmarks_rerun=0"
