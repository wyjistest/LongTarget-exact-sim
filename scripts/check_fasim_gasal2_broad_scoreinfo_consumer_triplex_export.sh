#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_broad_scoreinfo_consumer_triplex_export"}"
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
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1 \
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1 \
  bash "$RUNNER" >"$WORK/stdout.log"

python3 - "$WORK/neat1_first1/fresh.json" "$WORK/neat1_first1/audit/candidate/stderr.log" <<'PY'
import json
import re
import sys
from pathlib import Path

fresh = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
stderr = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

if fresh["audited_status"] != "accepted":
    raise SystemExit(f"unexpected audited_status={fresh['audited_status']}")
if fresh["baseline_digest"] != fresh["candidate_digest"]:
    raise SystemExit("normal output digest changed under broad CPU triplex export")

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
path = metric("cpu_triplex_path")
triplexes = int(metric("cpu_triplexes"))
digest = metric("cpu_triplex_digest")

if requested != 1:
    raise SystemExit(f"expected broad path requested=1, got {requested}")
if active != 0:
    raise SystemExit(f"expected broad path active=0 until consumer exists, got {active}")
if triplexes <= 0:
    raise SystemExit(f"expected positive broad_path_cpu_triplexes, got {triplexes}")
if not re.fullmatch(r"[0-9a-f]{16}", digest):
    raise SystemExit(f"unexpected broad_path_cpu_triplex_digest={digest}")

artifact = Path(path)
if not artifact.is_file():
    raise SystemExit(f"missing broad CPU triplex artifact: {artifact}")
lines = artifact.read_text(encoding="utf-8", errors="replace").splitlines()
if len(lines) != triplexes + 1:
    raise SystemExit(
        f"artifact row count mismatch: rows={len(lines) - 1} metric={triplexes}"
    )
required_columns = {
    "task_index",
    "legacy_order_index",
    "selected_align_attempt_index",
    "query_start",
    "query_end",
    "target_start",
    "target_end",
    "score",
    "emission_reason",
}
header = set(lines[0].split("\t"))
missing = sorted(required_columns - header)
if missing:
    raise SystemExit("triplex artifact missing columns: " + ", ".join(missing))

print("digest=" + fresh["candidate_digest"])
print("broad_path_cpu_triplex_path=" + path)
print("broad_path_cpu_triplexes=" + str(triplexes))
print("broad_path_cpu_triplex_digest=" + digest)
print("ok")
PY
