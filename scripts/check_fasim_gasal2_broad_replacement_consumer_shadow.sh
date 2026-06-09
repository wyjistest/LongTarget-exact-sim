#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_broad_replacement_consumer_shadow"}"
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
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1 \
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1 \
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER=1 \
FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW=1 \
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
    raise SystemExit("normal output digest changed under broad replacement consumer shadow")

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

def metric(name: str) -> str:
    key = "fasim_gasal2_broad_path_" + name
    if key not in bench:
        raise SystemExit(f"missing broad_path_{name}")
    return bench[key]

requested = int(metric("requested"))
active = int(metric("active"))
decision = metric("decision")
tasks = int(metric("tasks"))
scoreinfos = int(metric("scoreinfo_groups"))
attempts = int(metric("align_attempts"))
selected = int(metric("selected_attempts"))
mismatches = int(metric("triplex_mismatches"))
missing = int(metric("missing_triplexes"))
extra = int(metric("extra_triplexes"))
first = metric("first_mismatch")
consumer_seconds = float(metric("consumer_seconds"))
cpu_triplexes = int(metric("cpu_triplexes"))

if requested != 1:
    raise SystemExit(f"expected requested=1, got {requested}")
if active != 1:
    raise SystemExit(f"expected active=1 for broad replacement consumer shadow, got {active}")
if decision != "replacement_consumer_shadow_active":
    raise SystemExit(f"unexpected broad replacement consumer decision={decision}")
if tasks <= 0:
    raise SystemExit(f"expected positive broad_path_tasks, got {tasks}")
if scoreinfos <= 0:
    raise SystemExit(f"expected positive broad_path_scoreinfo_groups, got {scoreinfos}")
if attempts < scoreinfos:
    raise SystemExit(f"expected align_attempts >= scoreinfo_groups, got {attempts} < {scoreinfos}")
if selected < 0 or selected > attempts:
    raise SystemExit(f"selected attempts out of range: {selected}/{attempts}")
if consumer_seconds <= 0.0:
    raise SystemExit(f"expected positive consumer_seconds, got {consumer_seconds}")
if cpu_triplexes <= 0:
    raise SystemExit(f"expected positive CPU authority triplexes, got {cpu_triplexes}")
if mismatches != 0 or missing != 0 or extra != 0:
    raise SystemExit(
        "broad replacement consumer mismatch: "
        f"mismatches={mismatches} missing={missing} extra={extra} first={first}"
    )
if first != "none":
    raise SystemExit(f"expected first_mismatch=none, got {first}")

print("digest=" + fresh["candidate_digest"])
print("broad_path_tasks=" + str(tasks))
print("broad_path_scoreinfo_groups=" + str(scoreinfos))
print("broad_path_align_attempts=" + str(attempts))
print("broad_path_triplex_mismatches=0")
print("broad_path_missing_triplexes=0")
print("broad_path_extra_triplexes=0")
print("ok")
PY
