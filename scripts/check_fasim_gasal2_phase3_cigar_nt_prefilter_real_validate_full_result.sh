#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate_full/report.tsv"}"
REQUIRED_WORKLOADS="${REQUIRED_WORKLOADS:-chr22 chr1}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 3 CIGAR NT prefilter real-validate full characterization report: $REPORT" >&2
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
    if as_int(row, "baseline_real_active") != 0:
        raise SystemExit(f"{name}: baseline unexpectedly activated real prefilter")
    for key in (
        "phase3_requested",
        "phase3_active",
        "real_requested",
        "real_active",
        "real_validate_requested",
        "real_validate_active",
    ):
        if as_int(row, key) != 1:
            raise SystemExit(f"{name}: {key} did not activate")
    if as_int(row, "real_skipped_alignments") <= 0:
        raise SystemExit(f"{name}: no real skipped alignments")
    if as_int(row, "real_validated_skips") != as_int(row, "real_skipped_alignments"):
        raise SystemExit(f"{name}: validated skips do not match skipped alignments")
    if as_int(row, "real_validate_mismatches") != 0:
        raise SystemExit(f"{name}: real validate mismatches")
    if as_int(row, "real_fallbacks") != 0:
        raise SystemExit(f"{name}: real fallbacks")
    if row.get("real_decision") != "validated_clean":
        raise SystemExit(f"{name}: unexpected real decision {row.get('real_decision')}")
    if as_int(row, "restored_equal") != 1:
        raise SystemExit(f"{name}: restored output differs")
    if as_int(row, "legacy_only_rows") != 0:
        raise SystemExit(f"{name}: baseline-only rows present")
    if as_int(row, "candidate_only_rows") != 0:
        raise SystemExit(f"{name}: candidate-only rows present")
    if as_int(row, "baseline_rows") != as_int(row, "real_validate_rows"):
        raise SystemExit(f"{name}: restored row counts differ")
    if as_float(row, "baseline_run_wall_seconds") <= 0.0:
        raise SystemExit(f"{name}: baseline run wall must be positive")
    if as_float(row, "real_validate_run_wall_seconds") <= 0.0:
        raise SystemExit(f"{name}: real-validate run wall must be positive")
    if as_float(row, "baseline_convert_wall_seconds") <= 0.0:
        raise SystemExit(f"{name}: baseline convert wall must be positive")
    if as_float(row, "real_validate_convert_wall_seconds") <= 0.0:
        raise SystemExit(f"{name}: real-validate convert wall must be positive")
    if row.get("decision") not in {
        "real_validate_clean_speedup",
        "real_validate_clean_no_speedup",
    }:
        raise SystemExit(f"{name}: unexpected decision {row.get('decision')}")

print("phase3_cigar_nt_prefilter_real_validate_full_characterization=pass")
for name in required:
    row = by_workload[name]
    print(f"{name}_real_skipped_alignments={row['real_skipped_alignments']}")
    print(f"{name}_convert_wall_speedup={row['convert_wall_speedup']}")
    print(f"{name}_run_wall_speedup={row['run_wall_speedup']}")
    print(f"{name}_decision={row['decision']}")
print("ok")
PY
