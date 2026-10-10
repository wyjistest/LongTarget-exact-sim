#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-$ROOT/.tmp/fasim_longtarget_gpu_consumer_spike_v1}"
WORK="${WORK:-$ROOT/.tmp/long_query_gpu_consumer_spike_v1}"
QUERY="${QUERY:-/data/wenyujianData/linjieData/longtarget_runs/segment_owner_authority_probe_v1/inputs/short_header_cpu_authority/ENSG00000229613.fa}"
TARGET="${TARGET:-$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
[[ -s "$QUERY" ]] || { echo "missing query: $QUERY" >&2; exit 1; }
[[ -s "$TARGET" ]] || { echo "missing target: $TARGET" >&2; exit 1; }

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/spike"

run_fasim() {
  local out_dir="$1"
  shift
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -na 512 -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_fasim "$WORK/baseline" \
  FASIM_ALIGN_GASAL2=0 \
  FASIM_ENABLE_PREALIGN_CUDA=0

# The stateful-forward flags below are a frozen forward oracle configuration.
# The legacy GASAL2 guard remains 2812; the isolated endpoint API does not call
# that bridge and must cover the full 4006 nt query without relaxing the guard.
run_fasim "$WORK/spike" \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ENABLE_PREALIGN_CUDA=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_SPIKE_V1=1 \
  FASIM_LONG_QUERY_GPU_CONSUMER_SPIKE_REPORT="$WORK/spike/consumer.tsv"

find_output() {
  find "$1" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit
}
baseline_output="$(find_output "$WORK/baseline")"
spike_output="$(find_output "$WORK/spike")"
[[ -s "$baseline_output" && -s "$spike_output" ]] || {
  echo "missing TFOsorted output" >&2
  exit 1
}
baseline_digest="$(sha256sum "$baseline_output" | awk '{print $1}')"
spike_digest="$(sha256sum "$spike_output" | awk '{print $1}')"

python3 - "$WORK" "$QUERY" "$TARGET" "$BIN" "$baseline_digest" "$spike_digest" <<'PY'
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

work = Path(sys.argv[1])
query = Path(sys.argv[2])
target = Path(sys.argv[3])
binary = Path(sys.argv[4])
baseline_digest = sys.argv[5]
spike_digest = sys.argv[6]
report = work / "spike" / "consumer.tsv"
rows = []
if report.exists():
    with report.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

def as_int(row, key):
    return int(row[key])

technical_failures = [r for r in rows if as_int(r, "ok") != 1]
contract_failures = [r for r in rows if as_int(r, "output_equal") != 1]
fallback_rows = [r for r in rows if r.get("error", "none") not in ("none", "")]
attempt_gate_failures = [r for r in rows if as_int(r, "attempt_mismatch_rows") != 0]
consumer_gate_failures = [r for r in rows if as_int(r, "consumer_selection_equal") != 1]
consumer_prefix_failures = [r for r in rows if as_int(r, "consumer_attempt_prefix_equal") != 1]
summary = {
    "schema_version": "long_query_gpu_consumer_spike_v1",
    "source_commit": subprocess.check_output(
        ["git", "-C", str(binary.parent.parent), "rev-parse", "HEAD"], text=True
    ).strip(),
    "binary": str(binary),
    "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    "query": str(query),
    "query_sha256": hashlib.sha256(query.read_bytes()).hexdigest(),
    "query_length_nt": sum(len(line.strip()) for line in query.read_text().splitlines() if not line.startswith(">")),
    "target": str(target),
    "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "baseline_digest": baseline_digest,
    "spike_digest": spike_digest,
    "rows": len(rows),
    "technical_success_rows": len(rows) - len(technical_failures),
    "contract_pass_rows": len(rows) - len(contract_failures),
    "technical_failures": len(technical_failures),
    "contract_failures": len(contract_failures),
    "fallback_rows": len(fallback_rows),
    "attempt_gate_failures": len(attempt_gate_failures),
    "consumer_gate_failures": len(consumer_gate_failures),
    "consumer_prefix_failures": len(consumer_prefix_failures),
    "decision": "spike_pass" if rows and not technical_failures and not contract_failures and not attempt_gate_failures and not consumer_gate_failures and not consumer_prefix_failures and baseline_digest == spike_digest else "spike_no_go",
}
for key in ("score_seconds", "gpu_kernel_seconds", "h2d_seconds", "d2h_seconds", "cpu_oracle_seconds", "select_seconds", "traceback_seconds", "convert_seconds", "total_seconds"):
    vals = [float(r[key]) for r in rows if r.get(key)]
    summary["sum_" + key] = sum(vals)
summary["gpu_scored_attempts"] = sum(as_int(r, "gpu_scored_attempts") for r in rows)
summary["endpoint_batches"] = sum(as_int(r, "endpoint_batches") for r in rows)
summary["cpu_oracle_attempts"] = sum(as_int(r, "cpu_oracle_attempts") for r in rows)
summary["attempt_mismatch_rows"] = sum(as_int(r, "attempt_mismatch_rows") for r in rows)
summary["score_mismatches"] = sum(as_int(r, "score_mismatches") for r in rows)
summary["query_end_mismatches"] = sum(as_int(r, "query_end_mismatches") for r in rows)
summary["ref_end_local_mismatches"] = sum(as_int(r, "ref_end_local_mismatches") for r in rows)
summary["terminal_mismatches"] = sum(as_int(r, "terminal_mismatches") for r in rows)
summary["control_selected_attempts"] = sum(as_int(r, "control_selected_attempts") for r in rows)
summary["cpu_control_selected_attempts"] = sum(as_int(r, "cpu_control_selected_attempts") for r in rows)
summary["cpu_reference_align_attempts"] = sum(as_int(r, "cpu_reference_align_attempts") for r in rows)
summary["cpu_continuation_requested_rows"] = sum(as_int(r, "cpu_continuation_requested") for r in rows)
summary["cpu_continuation_active_rows"] = sum(as_int(r, "cpu_continuation_active") for r in rows)
summary["cpu_continuation_calls"] = sum(as_int(r, "cpu_continuation_calls") for r in rows)
summary["cpu_continuation_failures"] = sum(as_int(r, "cpu_continuation_failures") for r in rows)
summary["replay_attempts"] = sum(as_int(r, "replay_attempts") for r in rows)
summary["cpu_align_attempts"] = sum(as_int(r, "cpu_align_attempts") for r in rows)
(work / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
if summary["decision"] != "spike_pass":
    raise SystemExit(1)
PY
