#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke"}"
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
REPLAY_PROBE_MAX_TASKS=0 \
BUILD_BIN=0 \
BIN="$BIN" \
WORK="$WORK/neat1_first1" \
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1 \
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1 \
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_LEGACY_BYTE=1 \
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_LEGACY_BYTE_SHARED=1 \
FASIM_GASAL2_LONGTARGET_BRIDGE=1 \
FASIM_GASAL2_CPU_TRACEBACK=1 \
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
    raise SystemExit("normal output digest changed under emission-only consumer shadow")

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

def metric(name: str) -> str:
    key = "fasim_gasal2_emission_only_consumer_shadow_" + name
    if key not in bench:
        raise SystemExit(f"missing emission_only_consumer_shadow_{name}")
    return bench[key]

requested = int(metric("requested"))
active = int(metric("active"))
decision = metric("decision")
tasks = int(metric("tasks"))
scoreinfos = int(metric("scoreinfos"))
scored_attempts = int(metric("scored_attempts"))
threshold_emits = int(metric("threshold_emits"))
terminal_emits = int(metric("terminal_emits"))
last_emits = int(metric("last_emits"))
cpu_align_attempts = int(metric("cpu_align_attempts"))
reference_align_attempts = int(metric("realpath_reference_align_attempts"))
align_attempt_reduction = int(metric("align_attempt_reduction"))
score_seconds = float(metric("score_seconds"))
total_seconds = float(metric("total_seconds"))

if requested != 1:
    raise SystemExit(f"expected requested=1, got {requested}")
if active != 1:
    raise SystemExit(f"expected active=1, got {active}, decision={decision}")
if decision not in (
    "emission_only_consumer_shadow_active",
    "emission_only_consumer_shadow_mismatch_no_go",
):
    raise SystemExit(f"unexpected emission-only decision={decision}")
if tasks <= 0:
    raise SystemExit(f"expected positive tasks, got {tasks}")
if scoreinfos <= 0:
    raise SystemExit(f"expected positive scoreinfos, got {scoreinfos}")
if scored_attempts <= 0:
    raise SystemExit(f"expected positive scored_attempts, got {scored_attempts}")
if threshold_emits + terminal_emits + last_emits <= 0:
    raise SystemExit(
        "expected at least one threshold, terminal, or last emit, got "
        f"threshold={threshold_emits} terminal={terminal_emits} last={last_emits}"
    )
if cpu_align_attempts <= 0:
    raise SystemExit(f"expected positive cpu_align_attempts, got {cpu_align_attempts}")
if reference_align_attempts <= 0:
    raise SystemExit(
        f"expected positive realpath_reference_align_attempts, got {reference_align_attempts}"
    )
if cpu_align_attempts >= reference_align_attempts:
    raise SystemExit(
        "expected emission-only CPU align attempts below realpath reference, "
        f"got shadow={cpu_align_attempts} reference={reference_align_attempts}"
    )
if align_attempt_reduction != reference_align_attempts - cpu_align_attempts:
    raise SystemExit(
        "align_attempt_reduction mismatch: "
        f"reported={align_attempt_reduction} expected={reference_align_attempts - cpu_align_attempts}"
    )
if score_seconds <= 0.0:
    raise SystemExit(f"expected positive score_seconds, got {score_seconds}")
if total_seconds <= 0.0:
    raise SystemExit(f"expected positive total_seconds, got {total_seconds}")

print("digest=" + fresh["candidate_digest"])
print("emission_only_consumer_shadow_tasks=" + str(tasks))
print("emission_only_consumer_shadow_scoreinfos=" + str(scoreinfos))
print("emission_only_consumer_shadow_scored_attempts=" + str(scored_attempts))
print("emission_only_consumer_shadow_cpu_align_attempts=" + str(cpu_align_attempts))
print("emission_only_consumer_shadow_realpath_reference_align_attempts=" + str(reference_align_attempts))
print("emission_only_consumer_shadow_align_attempt_reduction=" + str(align_attempt_reduction))
print("ok")
PY
