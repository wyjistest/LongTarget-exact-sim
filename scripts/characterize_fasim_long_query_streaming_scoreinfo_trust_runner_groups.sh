#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-64}"
WORKERS="${WORKERS:-1}"
GROUP_TARGET_RECORDS_LIST="${GROUP_TARGET_RECORDS_LIST:-null 2 4 8 16 32}"
GPU_IDS="${GPU_IDS:-}"
REUSE_EXISTING="${REUSE_EXISTING:-0}"
TRUST_PRESET="${TRUST_PRESET:-plain}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

if [[ "$REUSE_EXISTING" != "1" ]]; then
  rm -rf "$WORK"
fi
mkdir -p "$WORK"

summary="$WORK/summary.tsv"
header_written=0

for group_size in $GROUP_TARGET_RECORDS_LIST; do
  case "$group_size" in
    null)
      group_env=""
      group_label="null"
      ;;
    ''|*[!0-9]*)
      echo "GROUP_TARGET_RECORDS_LIST must contain null or positive integers, got: $group_size" >&2
      exit 1
      ;;
    *)
      if [[ "$group_size" -le 0 ]]; then
        echo "GROUP_TARGET_RECORDS_LIST must contain null or positive integers, got: $group_size" >&2
        exit 1
      fi
      group_env="$group_size"
      group_label="$group_size"
      ;;
  esac

  run_work="$WORK/group_${group_label}"
  if [[ "$REUSE_EXISTING" == "1" && -s "$run_work/summary.tsv" ]]; then
    echo "reusing MALAT1 trust runner grouping sweep group_target_records=${group_label}" >&2
  else
    echo "running MALAT1 trust runner grouping sweep group_target_records=${group_label}" >&2
    WORK="$run_work" \
    BIN="$BIN" \
    BUILD_BIN=0 \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    GROUP_TARGET_RECORDS="$group_env" \
    TRUST_PRESET="$TRUST_PRESET" \
    MALAT1_RECORD_LIMITS="$MALAT1_RECORD_LIMITS" \
      bash "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner.sh" \
      >"$run_work.stdout" 2>"$run_work.stderr"
  fi

  if [[ ! -s "$run_work/summary.tsv" ]]; then
    echo "missing grouping sweep summary for group_target_records=${group_label}" >&2
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
    raise SystemExit("grouping sweep produced no rows")

expected_contracts = {
    "long_query_streaming_scoreinfo_gpu_trust_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
}
digests_by_case = {}
speedups = []
for row in rows:
    label = f"{row['label']} group={row['group_target_records']}"
    previous_digest = digests_by_case.setdefault(label, row["digest"])
    if previous_digest != row["digest"]:
        raise SystemExit(
            f"{label}: inconsistent digest rows: {previous_digest} vs {row['digest']}"
        )
    if row["result_contract"] not in expected_contracts:
        raise SystemExit(f"{label}: unexpected result_contract={row['result_contract']}")
    if row["result_contract"].endswith("_group32_experimental_v1"):
        if row.get("trust_profile") != "malat1_like_group32_experimental_v1":
            raise SystemExit(f"{label}: unexpected trust_profile={row.get('trust_profile')}")
        if row["group_target_records"] != "32":
            raise SystemExit(f"{label}: group32 preset requires group_target_records=32")
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
    speedups.append(float(row["candidate_vs_baseline"].removesuffix("x")))

print("rows=" + str(len(rows)))
print("best_runner_speedup=" + f"{max(speedups):.6f}x")
PY

cat "$summary"
