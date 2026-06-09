#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_replacement_consumer_shadow_runtime_smoke"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -x "$RUNNER" ]]; then
  echo "missing NEAT1 audited runner gate: $RUNNER" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

NEAT1_RECORD_LIMIT=1 \
REPLAY_PROBE_MAX_TASKS=1 \
BUILD_BIN=0 \
BIN="$BIN" \
WORK="$WORK/neat1_first1" \
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REPLACEMENT_CONSUMER_SHADOW=1 \
  bash "$RUNNER" >"$WORK/stdout.log"

python3 - "$WORK/neat1_first1/fresh.json" "$WORK/neat1_first1/audit/candidate/stderr.log" <<'PY'
import json
import sys
from pathlib import Path

fresh = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
stderr = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

if fresh["audited_status"] != "accepted":
    raise SystemExit(f"unexpected audited_status={fresh['audited_status']}")
if fresh["baseline_digest"] != fresh["candidate_digest"]:
    raise SystemExit("digest mismatch under replacement-consumer shadow")
if fresh["tasks"] != 48:
    raise SystemExit(f"expected NEAT1 first1 tasks=48, got {fresh['tasks']}")
if fresh["realpath_used"] != fresh["tasks"]:
    raise SystemExit(
        f"realpath_used mismatch: {fresh['realpath_used']} vs {fresh['tasks']}"
    )
if fresh["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit("segmented replay mismatch should remain zero")
if fresh["candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit("full replay mismatch should remain zero")
if fresh["candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit("oracle replay mismatch should remain zero")

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

prefix = "fasim_long_query_streaming_scoreinfo_gpu_shadow_"

def metric(name: str) -> str:
    key = prefix + name
    if key not in bench:
        raise SystemExit(f"missing benchmark metric: {key}")
    return bench[key]

def int_metric(name: str) -> int:
    return int(metric(name))

if int_metric("replacement_consumer_shadow_requested") != 1:
    raise SystemExit("replacement-consumer shadow was not requested")
if int_metric("replacement_consumer_shadow_active") != 1:
    raise SystemExit("replacement-consumer shadow was not active")
if int_metric("replacement_consumer_shadow_tasks") != 1:
    raise SystemExit("expected capped replacement-consumer shadow tasks=1")
if int_metric("replacement_consumer_shadow_segmented_triplex_mismatches") != 0:
    raise SystemExit("segmented replacement-consumer alias mismatch")
if int_metric("replacement_consumer_shadow_full_triplex_mismatches") != 0:
    raise SystemExit("full replacement-consumer alias mismatch")
if int_metric("replacement_consumer_shadow_oracle_triplex_mismatches") != 0:
    raise SystemExit("oracle replacement-consumer alias mismatch")
if int_metric("replacement_consumer_shadow_selected_only_triplex_mismatches") != 1:
    raise SystemExit("expected selected-only mismatch to remain visible")
if int_metric("replacement_consumer_shadow_grouped_selected_triplex_mismatches") != 0:
    raise SystemExit("grouped-selected alias mismatch")
if int_metric("replacement_consumer_shadow_triplex_mismatches") != 1:
    raise SystemExit("expected total replacement-consumer mismatch=1")
if metric("replacement_consumer_shadow_first_mismatch_source") != "selected_only":
    raise SystemExit(
        "expected first mismatch source selected_only, got "
        + metric("replacement_consumer_shadow_first_mismatch_source")
    )
if metric("replacement_consumer_shadow_first_mismatch_kind") != "legacy_empty":
    raise SystemExit(
        "expected first mismatch kind legacy_empty, got "
        + metric("replacement_consumer_shadow_first_mismatch_kind")
    )
if int_metric("replacement_consumer_shadow_fallbacks") != 0:
    raise SystemExit("replacement-consumer shadow fallback should be zero")

print("digest=" + fresh["candidate_digest"])
print("tasks=" + str(fresh["tasks"]))
print("replacement_consumer_shadow_triplex_mismatches=1")
print("replacement_consumer_shadow_first_mismatch_source=selected_only")
print("ok")
PY
