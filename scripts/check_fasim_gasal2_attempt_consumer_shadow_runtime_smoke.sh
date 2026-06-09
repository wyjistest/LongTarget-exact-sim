#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke"}"
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
FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1 \
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
    raise SystemExit("normal output digest changed under attempt consumer shadow")

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

def metric(name: str) -> str:
    key = "fasim_gasal2_attempt_consumer_shadow_" + name
    if key not in bench:
        raise SystemExit(f"missing attempt_consumer_shadow_{name}")
    return bench[key]

requested = int(metric("requested"))
active = int(metric("active"))
decision = metric("decision")
tasks = int(metric("tasks"))
scoreinfos = int(metric("scoreinfos"))
attempts = int(metric("attempts"))
selected = int(metric("selected_attempts"))
cpu_align_attempts = int(metric("cpu_align_attempts"))
cpu_reference_key = "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts"
if cpu_reference_key not in bench:
    raise SystemExit(f"missing {cpu_reference_key}")
cpu_reference_align_attempts = int(bench[cpu_reference_key])
mismatches = int(metric("triplex_mismatches"))
missing = int(metric("missing_triplexes"))
extra = int(metric("extra_triplexes"))
first = metric("first_mismatch")
total_seconds = float(metric("total_seconds"))

if requested != 1:
    raise SystemExit(f"expected requested=1, got {requested}")
if active != 1:
    raise SystemExit(f"expected active=1 for attempt consumer shadow, got {active}")
if decision not in ("attempt_consumer_shadow_active", "attempt_consumer_shadow_no_go"):
    raise SystemExit(f"unexpected attempt consumer decision={decision}")
if tasks <= 0:
    raise SystemExit(f"expected positive tasks, got {tasks}")
if scoreinfos <= 0:
    raise SystemExit(f"expected positive scoreinfos, got {scoreinfos}")
if attempts <= 0:
    raise SystemExit(f"expected positive attempts, got {attempts}")
if selected <= 0:
    raise SystemExit(f"expected positive selected_attempts, got {selected}")
if cpu_align_attempts != selected:
    raise SystemExit(
        "expected cpu_align_attempts == selected_attempts, "
        f"got {cpu_align_attempts} vs {selected}"
    )
if cpu_align_attempts > attempts:
    raise SystemExit(
        "expected attempt consumer CPU align attempts within legacy attempt space, "
        f"got cpu={cpu_align_attempts} attempts={attempts}"
    )
if cpu_align_attempts != cpu_reference_align_attempts:
    raise SystemExit(
        "current conservative attempt consumer shadow should match CPU reference "
        "align attempts before any performance claim, "
        f"got shadow={cpu_align_attempts} reference={cpu_reference_align_attempts}"
    )
if total_seconds <= 0.0:
    raise SystemExit(f"expected positive total_seconds, got {total_seconds}")
if mismatches != 0 or missing != 0 or extra != 0:
    raise SystemExit(
        "attempt consumer shadow mismatch: "
        f"mismatches={mismatches} missing={missing} extra={extra} first={first}"
    )
if first != "none":
    raise SystemExit(f"expected first_mismatch=none, got {first}")

print("digest=" + fresh["candidate_digest"])
print("attempt_consumer_shadow_tasks=" + str(tasks))
print("attempt_consumer_shadow_scoreinfos=" + str(scoreinfos))
print("attempt_consumer_shadow_attempts=" + str(attempts))
print("attempt_consumer_shadow_selected_attempts=" + str(selected))
print("attempt_consumer_shadow_cpu_align_attempts=" + str(cpu_align_attempts))
print("attempt_consumer_shadow_cpu_reference_align_attempts=" + str(cpu_reference_align_attempts))
print("attempt_consumer_shadow_triplex_mismatches=0")
print("attempt_consumer_shadow_missing_triplexes=0")
print("attempt_consumer_shadow_extra_triplexes=0")
print("ok")
PY
