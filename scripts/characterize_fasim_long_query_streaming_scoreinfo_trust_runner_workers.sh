#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_workers"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-64}"
WORKER_COUNTS="${WORKER_COUNTS:-1 2 4}"
GPU_IDS="${GPU_IDS:-}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

summary="$WORK/summary.tsv"
header_written=0

for workers in $WORKER_COUNTS; do
  case "$workers" in
    ''|*[!0-9]*)
      echo "WORKER_COUNTS must contain positive integers, got: $workers" >&2
      exit 1
      ;;
  esac
  if [[ "$workers" -le 0 ]]; then
    echo "WORKER_COUNTS must contain positive integers, got: $workers" >&2
    exit 1
  fi

  run_work="$WORK/workers_${workers}"
  echo "running MALAT1 trust runner worker sweep workers=${workers}" >&2
  WORK="$run_work" \
  BIN="$BIN" \
  BUILD_BIN=0 \
  WORKERS="$workers" \
  GPU_IDS="$GPU_IDS" \
  MALAT1_RECORD_LIMITS="$MALAT1_RECORD_LIMITS" \
    bash "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner.sh" \
    >"$run_work.stdout" 2>"$run_work.stderr"

  if [[ ! -s "$run_work/summary.tsv" ]]; then
    echo "missing worker sweep summary for workers=${workers}" >&2
    exit 1
  fi

  if [[ "$header_written" == "0" ]]; then
    cat "$run_work/summary.tsv" >"$summary"
    header_written=1
  else
    tail -n +2 "$run_work/summary.tsv" >>"$summary"
  fi
done

python3 - "$summary" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
rows = list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))
if not rows:
    raise SystemExit("worker sweep produced no rows")

expected_speedups = []
for row in rows:
    label = f"{row['label']} workers={row['worker_count']}"
    if row["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_experimental_v1":
        raise SystemExit(f"{label}: unexpected result_contract={row['result_contract']}")
    if row["realpath_used"] != row["tasks"]:
        raise SystemExit(f"{label}: realpath_used != tasks")
    if row["gpu_minscore_used"] != row["tasks"]:
        raise SystemExit(f"{label}: gpu_minscore_used != tasks")
    for key in ("realpath_fallbacks", "cpu_scoreinfo_groups", "gpu_minscore_fallbacks", "cpu_prealign_seconds", "compare_seconds"):
        if row[key] not in {"0", "0.0"}:
            raise SystemExit(f"{label}: expected {key}=0, got {row[key]}")
    if row["realpath_digest_authority"] != "external_digest_gate":
        raise SystemExit(f"{label}: unexpected authority={row['realpath_digest_authority']}")
    if not row["candidate_vs_baseline"].endswith("x"):
        raise SystemExit(f"{label}: malformed speedup={row['candidate_vs_baseline']}")
    expected_speedups.append(float(row["candidate_vs_baseline"].removesuffix("x")))

print("rows=" + str(len(rows)))
print("best_runner_speedup=" + f"{max(expected_speedups):.6f}x")
PY

cat "$summary"
