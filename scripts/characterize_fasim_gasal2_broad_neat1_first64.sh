#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_broad_neat1_first64"}"
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

NEAT1_RECORD_LIMIT=64 \
REPLAY_PROBE_MAX_TASKS=0 \
BUILD_BIN=0 \
BIN="$BIN" \
WORK="$WORK/neat1_first64" \
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1 \
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1 \
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER=1 \
FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW=1 \
  bash "$RUNNER" >"$WORK/stdout.log"

python3 - \
  "$WORK/neat1_first64/fresh.json" \
  "$WORK/neat1_first64/audit/candidate/stderr.log" \
  "$WORK/report.json" <<'PY'
import json
import sys
from pathlib import Path

fresh_path = Path(sys.argv[1])
stderr_path = Path(sys.argv[2])
report_path = Path(sys.argv[3])

fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
stderr = stderr_path.read_text(encoding="utf-8", errors="replace")

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

def metric(name: str, default: str = "0") -> str:
    return bench.get("fasim_gasal2_broad_path_" + name, default)

def gpu_metric(name: str, default: str = "0") -> str:
    return bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_" + name, default)

def as_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return int(float(value))

def as_float(value: str) -> float:
    return float(value)

baseline_wall = float(fresh.get("baseline_runner_wall_seconds", 0.0))
candidate_wall = float(fresh.get("candidate_runner_wall_seconds", 0.0))
candidate_vs_baseline = (
    baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0
)
broad_scoreinfo = as_float(metric("scoreinfo_seconds"))
broad_consumer = as_float(metric("consumer_seconds"))
baseline_reference = as_float(gpu_metric("realpath_extend_seconds"))
realpath_align_attempts = as_int(gpu_metric("realpath_extend_align_attempts"))
broad_align_attempts = as_int(metric("align_attempts"))

decision = "broad_path_candidate_go"
reasons = []
if fresh.get("audited_status") != "accepted":
    reasons.append("audit_not_accepted")
if fresh.get("baseline_digest") != fresh.get("candidate_digest"):
    reasons.append("digest_mismatch")
if as_int(metric("active")) != 1:
    reasons.append("broad_path_inactive")
if as_int(metric("triplex_mismatches")) != 0:
    reasons.append("triplex_mismatches")
if as_int(metric("missing_triplexes")) != 0:
    reasons.append("missing_triplexes")
if as_int(metric("extra_triplexes")) != 0:
    reasons.append("extra_triplexes")
if candidate_wall <= 0.0 or candidate_wall >= 86.0335:
    reasons.append("candidate_wall_not_below_neat1_baseline_ceiling")
if candidate_vs_baseline <= 1.0:
    reasons.append("candidate_vs_baseline_not_above_1")
if baseline_reference <= 0.0 or broad_scoreinfo + broad_consumer >= baseline_reference:
    reasons.append("broad_scoreinfo_consumer_not_below_cpu_reference")
if realpath_align_attempts != 0 and broad_align_attempts >= realpath_align_attempts:
    reasons.append("align_attempts_not_reduced")
if reasons:
    decision = "broad_path_current_architecture_no_go"

report = {
    "workload": "NEAT1_first64",
    "record_limit": 64,
    "decision": decision,
    "decision_reasons": reasons,
    "audited_status": fresh.get("audited_status"),
    "baseline_digest": fresh.get("baseline_digest"),
    "candidate_digest": fresh.get("candidate_digest"),
    "baseline_wall_seconds": baseline_wall,
    "candidate_wall_seconds": candidate_wall,
    "candidate_vs_baseline": candidate_vs_baseline,
    "tasks": fresh.get("tasks"),
    "realpath_used": fresh.get("realpath_used"),
    "gpu_scoreinfo_groups": fresh.get("gpu_scoreinfo_groups"),
    "realpath_extend_align_attempts": realpath_align_attempts,
    "baseline_cpu_reference_seconds": baseline_reference,
    "broad_path_requested": as_int(metric("requested")),
    "broad_path_active": as_int(metric("active")),
    "broad_path_decision": metric("decision", "unknown"),
    "broad_path_tasks": as_int(metric("tasks")),
    "broad_path_scoreinfo_groups": as_int(metric("scoreinfo_groups")),
    "broad_path_scoreinfo_seconds": broad_scoreinfo,
    "broad_path_consumer_seconds": broad_consumer,
    "broad_path_align_attempts": broad_align_attempts,
    "broad_path_selected_attempts": as_int(metric("selected_attempts")),
    "broad_path_triplex_mismatches": as_int(metric("triplex_mismatches")),
    "broad_path_missing_triplexes": as_int(metric("missing_triplexes")),
    "broad_path_extra_triplexes": as_int(metric("extra_triplexes")),
    "broad_path_first_mismatch": metric("first_mismatch", "none"),
    "broad_path_cpu_triplexes": as_int(metric("cpu_triplexes")),
    "broad_path_cpu_triplex_digest": metric("cpu_triplex_digest", ""),
    "broad_path_planner_descriptors": as_int(metric("planner_descriptors")),
    "broad_path_planner_descriptor_digest": metric("planner_descriptor_digest", ""),
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

print("decision=" + decision)
print("decision_reasons=" + ",".join(reasons))
print("candidate_vs_baseline=" + f"{candidate_vs_baseline:.6f}x")
print("broad_path_triplex_mismatches=" + str(report["broad_path_triplex_mismatches"]))
print("report=" + str(report_path))
PY
