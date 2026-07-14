#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_certificate_shadow_smoke"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
BUILD_BIN="${BUILD_BIN:-0}"

if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
for path in "$BIN" "$DNA" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing traceback certificate smoke dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/shadow"

run_case() {
  local output="$1"
  shift
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
    FASIM_EXACT_COLUMN_SCOREINFO_GPU=1 \
    FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512 \
    FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 \
    FASIM_ALIGN_GASAL2_STREAMS=3 \
    FASIM_ALIGN_GASAL2_BATCH=20000 \
    "$@" \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r 0 -O "$output" \
    >"$output/stdout.log" 2>"$output/stderr.log"
}

run_case "$WORK/baseline"
run_case "$WORK/shadow" FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW=1

baseline_output="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit)"
shadow_output="$(find "$WORK/shadow" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit)"
if [[ -z "$baseline_output" || -z "$shadow_output" ]]; then
  echo "missing traceback certificate smoke output" >&2
  exit 1
fi
cmp -s "$baseline_output" "$shadow_output"

python3 - "$WORK/baseline/stderr.log" "$WORK/shadow/stderr.log" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path


def metrics(path: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


baseline = metrics(sys.argv[1])
shadow = metrics(sys.argv[2])
prefix = "benchmark.fasim_gasal2_traceback_certificate_shadow_"

required = {
    "requested",
    "active",
    "real_skip_enabled",
    "pre_drop_proof_available",
    "candidates_considered",
    "certified_skips",
    "uncertified_candidates",
    "exact_descriptor_duplicate_skips",
    "static_span_skips",
    "score_endpoint_span_skips",
    "shadow_false_rejects",
    "score_frontier_skips",
    "stability_frontier_skips",
    "nt_frontier_skips",
    "tie_rescues",
    "rank_aware_supported",
    "probe_requests",
    "probe_seconds",
    "fallbacks",
}
missing = sorted(name for name in required if prefix + name not in shadow)
if missing:
    raise SystemExit(f"missing traceback certificate metrics: {missing}")

if baseline.get(prefix + "requested") != "0":
    raise SystemExit("baseline unexpectedly requested traceback certificate shadow")
if shadow[prefix + "requested"] != "1" or shadow[prefix + "active"] != "1":
    raise SystemExit("traceback certificate shadow did not activate")
if shadow[prefix + "real_skip_enabled"] != "0":
    raise SystemExit("Phase 6 shadow must not enable real skips")
if shadow[prefix + "pre_drop_proof_available"] != "1":
    raise SystemExit("pre-drop certificate proof must be available")
if shadow[prefix + "rank_aware_supported"] != "0":
    raise SystemExit("rank-aware certificate must stay unsupported")

considered = int(shadow[prefix + "candidates_considered"])
certified = int(shadow[prefix + "certified_skips"])
uncertified = int(shadow[prefix + "uncertified_candidates"])
reasons = sum(
    int(shadow[prefix + name])
    for name in (
        "exact_descriptor_duplicate_skips",
        "static_span_skips",
        "score_endpoint_span_skips",
    )
)
if considered <= 0:
    raise SystemExit("traceback certificate shadow considered no candidates")
if certified + uncertified != considered:
    raise SystemExit("certified + uncertified does not close candidates considered")
if reasons != certified:
    raise SystemExit("certificate reason counters do not close certified skips")
if int(shadow[prefix + "probe_requests"]) != considered:
    raise SystemExit("score probe requests must equal candidates considered")
for name in (
    "shadow_false_rejects",
    "score_frontier_skips",
    "stability_frontier_skips",
    "nt_frontier_skips",
    "tie_rescues",
    "fallbacks",
):
    if int(shadow[prefix + name]) != 0:
        raise SystemExit(f"expected {name}=0, got {shadow[prefix + name]}")
if int(shadow["benchmark.fasim_gasal2_fallbacks"]) != 0:
    raise SystemExit("authority GASAL2 fallback detected")

print(f"candidates_considered={considered}")
print(f"certified_skips={certified}")
print("shadow_false_rejects=0")
print("full_output_byte_equal=1")
PY

echo "ok"
