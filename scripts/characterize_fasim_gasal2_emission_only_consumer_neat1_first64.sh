#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_emission_only_consumer_neat1_first64"}"
BUILD_BIN="${BUILD_BIN:-1}"
NEAT1_RECORD_LIMIT="${NEAT1_RECORD_LIMIT:-64}"

case "$NEAT1_RECORD_LIMIT" in
  ''|*[!0-9]*)
    echo "NEAT1_RECORD_LIMIT must be a positive integer, got: $NEAT1_RECORD_LIMIT" >&2
    exit 1
    ;;
esac
if [[ "$NEAT1_RECORD_LIMIT" -le 0 ]]; then
  echo "NEAT1_RECORD_LIMIT must be a positive integer, got: $NEAT1_RECORD_LIMIT" >&2
  exit 1
fi

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

NEAT1_RECORD_LIMIT="$NEAT1_RECORD_LIMIT" \
REPLAY_PROBE_MAX_TASKS=0 \
BUILD_BIN=0 \
BIN="$BIN" \
WORK="$WORK/neat1_first64" \
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1 \
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1 \
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_LEGACY_BYTE=1 \
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_LEGACY_BYTE_SHARED=1 \
FASIM_GASAL2_LONGTARGET_BRIDGE=1 \
FASIM_GASAL2_CPU_TRACEBACK=1 \
  bash "$RUNNER" >"$WORK/stdout.log"

python3 - \
  "$WORK/neat1_first64/fresh.json" \
  "$WORK/neat1_first64/audit/candidate/stderr.log" \
  "$WORK/report.json" \
  "$NEAT1_RECORD_LIMIT" <<'PY'
import json
import sys
from pathlib import Path

fresh = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
stderr = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
report_path = Path(sys.argv[3])
record_limit = int(sys.argv[4])

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

prefix = "fasim_gasal2_emission_only_consumer_shadow_"
stream_prefix = "fasim_long_query_streaming_scoreinfo_gpu_shadow_"

def metric(name: str, default: str = "0") -> str:
    return bench.get(prefix + name, default)

def require_metric(name: str) -> str:
    key = prefix + name
    if key not in bench:
        raise SystemExit(f"missing benchmark metric: {key}")
    return bench[key]

def stream_metric(name: str, default: str = "0") -> str:
    return bench.get(stream_prefix + name, default)

def as_int(value: str) -> int:
    return int(float(value))

def as_float(value: str) -> float:
    return float(value)

baseline_wall = float(fresh.get("baseline_runner_wall_seconds", 0.0))
candidate_wall = float(fresh.get("candidate_runner_wall_seconds", 0.0))
candidate_vs_baseline = baseline_wall / candidate_wall if candidate_wall > 0.0 else 0.0

requested = as_int(require_metric("requested"))
active = as_int(require_metric("active"))
runtime_decision = require_metric("decision")
tasks = as_int(require_metric("tasks"))
scoreinfos = as_int(require_metric("scoreinfos"))
scored_attempts = as_int(require_metric("scored_attempts"))
threshold_emits = as_int(require_metric("threshold_emits"))
terminal_emits = as_int(require_metric("terminal_emits"))
last_emits = as_int(require_metric("last_emits"))
empty_emits = as_int(require_metric("empty_emits"))
cpu_align_attempts = as_int(require_metric("cpu_align_attempts"))
reference_align_attempts = as_int(require_metric("realpath_reference_align_attempts"))
align_attempt_reduction = as_int(require_metric("align_attempt_reduction"))
score_seconds = as_float(require_metric("score_seconds"))
select_seconds = as_float(require_metric("select_seconds"))
cpu_align_seconds = as_float(require_metric("cpu_align_seconds"))
convert_seconds = as_float(require_metric("convert_seconds"))
total_seconds = as_float(require_metric("total_seconds"))
triplex_mismatches = as_int(require_metric("triplex_mismatches"))
missing_triplexes = as_int(require_metric("missing_triplexes"))
extra_triplexes = as_int(require_metric("extra_triplexes"))
first_mismatch = require_metric("first_mismatch")
fallbacks = as_int(require_metric("fallbacks"))
digest_match_flag = as_int(require_metric("digest_match"))
full_rows_equal = as_int(require_metric("full_rows_equal"))

stream_scoreinfo_mismatches = as_int(stream_metric("scoreinfo_mismatches", "0"))
stream_realpath_fallbacks = as_int(stream_metric("realpath_fallbacks", "0"))
stream_realpath_extend_seconds = as_float(stream_metric("realpath_extend_seconds", "0"))
stream_realpath_align_seconds = as_float(stream_metric("realpath_extend_align_seconds", "0"))
gpu_total_seconds = as_float(stream_metric("total_seconds", "0"))

decision = "emission_only_consumer_shadow_candidate_go"
reasons = []
if fresh.get("audited_status") != "accepted":
    reasons.append("audit_not_accepted")
if fresh.get("baseline_digest") != fresh.get("candidate_digest"):
    reasons.append("digest_mismatch")
if stream_scoreinfo_mismatches != 0:
    reasons.append("stream_scoreinfo_mismatches")
if stream_realpath_fallbacks != 0:
    reasons.append("stream_realpath_fallbacks")
if requested != 1:
    reasons.append("emission_shadow_not_requested")
if active != 1:
    reasons.append("emission_shadow_inactive")
if tasks <= 0 or scoreinfos <= 0 or scored_attempts <= 0:
    reasons.append("emission_shadow_empty")
if threshold_emits + terminal_emits + last_emits <= 0:
    reasons.append("emission_shadow_no_emits")
if triplex_mismatches != 0 or missing_triplexes != 0 or extra_triplexes != 0:
    reasons.append("triplex_mismatch")
if first_mismatch != "none":
    reasons.append("first_mismatch_not_none")
if fallbacks != 0:
    reasons.append("emission_shadow_fallbacks")
if digest_match_flag != 1 or full_rows_equal != 1:
    reasons.append("output_equality_not_recorded")
if reference_align_attempts > 0 and cpu_align_attempts >= reference_align_attempts:
    reasons.append("cpu_align_attempts_not_reduced")
if align_attempt_reduction != reference_align_attempts - cpu_align_attempts:
    reasons.append("align_attempt_reduction_mismatch")
if candidate_vs_baseline <= 1.0:
    reasons.append("candidate_vs_baseline_not_above_1")
if total_seconds >= stream_realpath_extend_seconds:
    reasons.append("emission_shadow_total_not_below_cpu_reference")

correctness_reasons = {
    "audit_not_accepted",
    "digest_mismatch",
    "stream_scoreinfo_mismatches",
    "stream_realpath_fallbacks",
    "emission_shadow_inactive",
    "emission_shadow_empty",
    "emission_shadow_no_emits",
    "triplex_mismatch",
    "first_mismatch_not_none",
    "emission_shadow_fallbacks",
    "output_equality_not_recorded",
}
if correctness_reasons.intersection(reasons):
    decision = "emission_only_consumer_shadow_correctness_no_go"
elif "cpu_align_attempts_not_reduced" in reasons:
    decision = "emission_only_consumer_shadow_no_cpu_align_reduction_no_go"
elif ("candidate_vs_baseline_not_above_1" in reasons or
      "emission_shadow_total_not_below_cpu_reference" in reasons):
    decision = "emission_only_consumer_shadow_performance_no_go"

report = {
    "workload": "NEAT1_first64",
    "record_limit": record_limit,
    "decision": decision,
    "decision_reasons": reasons,
    "audited_status": fresh.get("audited_status"),
    "baseline_digest": fresh.get("baseline_digest"),
    "candidate_digest": fresh.get("candidate_digest"),
    "digest_match": fresh.get("baseline_digest") == fresh.get("candidate_digest"),
    "baseline_wall_seconds": baseline_wall,
    "candidate_wall_seconds": candidate_wall,
    "candidate_vs_baseline": candidate_vs_baseline,
    "stream_scoreinfo_mismatches": stream_scoreinfo_mismatches,
    "stream_realpath_fallbacks": stream_realpath_fallbacks,
    "stream_realpath_extend_seconds": stream_realpath_extend_seconds,
    "stream_realpath_align_seconds": stream_realpath_align_seconds,
    "gpu_total_seconds": gpu_total_seconds,
    "emission_only_consumer_shadow_requested": requested,
    "emission_only_consumer_shadow_active": active,
    "emission_only_consumer_shadow_runtime_decision": runtime_decision,
    "emission_only_consumer_shadow_tasks": tasks,
    "emission_only_consumer_shadow_scoreinfos": scoreinfos,
    "emission_only_consumer_shadow_scored_attempts": scored_attempts,
    "emission_only_consumer_shadow_threshold_emits": threshold_emits,
    "emission_only_consumer_shadow_terminal_emits": terminal_emits,
    "emission_only_consumer_shadow_last_emits": last_emits,
    "emission_only_consumer_shadow_empty_emits": empty_emits,
    "emission_only_consumer_shadow_cpu_align_attempts": cpu_align_attempts,
    "emission_only_consumer_shadow_realpath_reference_align_attempts": reference_align_attempts,
    "emission_only_consumer_shadow_align_attempt_reduction": align_attempt_reduction,
    "emission_only_consumer_shadow_score_seconds": score_seconds,
    "emission_only_consumer_shadow_select_seconds": select_seconds,
    "emission_only_consumer_shadow_cpu_align_seconds": cpu_align_seconds,
    "emission_only_consumer_shadow_convert_seconds": convert_seconds,
    "emission_only_consumer_shadow_total_seconds": total_seconds,
    "emission_only_consumer_shadow_triplex_mismatches": triplex_mismatches,
    "emission_only_consumer_shadow_missing_triplexes": missing_triplexes,
    "emission_only_consumer_shadow_extra_triplexes": extra_triplexes,
    "emission_only_consumer_shadow_first_mismatch": first_mismatch,
    "emission_only_consumer_shadow_fallbacks": fallbacks,
    "emission_only_consumer_shadow_digest_match": digest_match_flag,
    "emission_only_consumer_shadow_full_rows_equal": full_rows_equal,
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

print("decision=" + decision)
print("decision_reasons=" + ",".join(reasons))
print("candidate_vs_baseline=" + f"{candidate_vs_baseline:.6f}x")
print("emission_only_consumer_shadow_triplex_mismatches=" + str(triplex_mismatches))
print("emission_only_consumer_shadow_cpu_align_attempts=" + str(cpu_align_attempts))
print("emission_only_consumer_shadow_realpath_reference_align_attempts=" + str(reference_align_attempts))
print("report=" + str(report_path))
PY
