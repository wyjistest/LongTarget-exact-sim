#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_full/report.tsv"}"
REQUIRED_WORKLOADS="${REQUIRED_WORKLOADS:-chr22 chr1}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 3 CIGAR NT prefilter full characterization report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" "$REQUIRED_WORKLOADS" <<'PY'
import csv
import sys
from pathlib import Path

report = Path(sys.argv[1])
required = sys.argv[2].split()
with report.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
by_workload = {row.get("workload", ""): row for row in rows}

missing = [name for name in required if name not in by_workload]
if missing:
    raise SystemExit(f"missing workload rows: {','.join(missing)}")

def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except KeyError as exc:
        raise SystemExit(f"{row.get('workload', '<unknown>')} missing {key}") from exc

def as_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except KeyError as exc:
        raise SystemExit(f"{row.get('workload', '<unknown>')} missing {key}") from exc

for name in required:
    row = by_workload[name]
    if as_int(row, "attempted") != 1:
        raise SystemExit(f"{name}: characterization not attempted")
    if as_int(row, "phase3_requested") != 1 or as_int(row, "phase3_active") != 1:
        raise SystemExit(f"{name}: Phase 3 shadow did not activate")
    if as_int(row, "alignments_seen") <= 0:
        raise SystemExit(f"{name}: alignments_seen must be > 0")
    if as_int(row, "cigar_lt_ntmin") != as_int(row, "legacy_nt_lt_ntmin"):
        raise SystemExit(f"{name}: CIGAR/legacy lt-ntMin counts differ")
    if as_int(row, "candidate_skippable") != as_int(row, "cigar_lt_ntmin"):
        raise SystemExit(f"{name}: candidate_skippable does not match CIGAR lt-ntMin")
    if as_int(row, "agree_lt_ntmin") + as_int(row, "disagree_lt_ntmin") != as_int(row, "alignments_seen"):
        raise SystemExit(f"{name}: lt-ntMin accounting does not cover all alignments")
    if as_int(row, "disagree_lt_ntmin") != 0:
        raise SystemExit(f"{name}: CIGAR/legacy ntMin disagreement")
    if as_int(row, "candidate_false_negative_rows") != 0:
        raise SystemExit(f"{name}: candidate false-negative rows")
    if as_int(row, "task_frontier_equal") != 1:
        raise SystemExit(f"{name}: task frontier differs")
    if row.get("task_frontier_safety") != "safe":
        raise SystemExit(f"{name}: task frontier not safe")
    if row.get("real_prune_proof_gate") != "pass":
        raise SystemExit(f"{name}: real prune proof gate did not pass")
    if row.get("analyzer_real_prune_proof_gate") != "pass":
        raise SystemExit(f"{name}: analyzer proof gate did not pass")
    if as_int(row, "broad_cpu_triplexes") <= 0:
        raise SystemExit(f"{name}: no broad CPU triplex rows exported")
    if as_float(row, "projected_saved_seconds") < 0.0:
        raise SystemExit(f"{name}: negative projected saved seconds")
    if row.get("decision") != "phase3_cigar_nt_prefilter_shadow_clean":
        raise SystemExit(f"{name}: unexpected decision {row.get('decision')}")

print("phase3_cigar_nt_prefilter_full_characterization=pass")
for name in required:
    row = by_workload[name]
    print(f"{name}_alignments_seen={row['alignments_seen']}")
    print(f"{name}_candidate_skippable={row['candidate_skippable']}")
    print(f"{name}_projected_saved_seconds={row['projected_saved_seconds']}")
print("ok")
PY
