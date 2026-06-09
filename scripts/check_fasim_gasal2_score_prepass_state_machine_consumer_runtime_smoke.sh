#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_score_prepass_state_machine_consumer_runtime_smoke"}"
BUILD_BIN="${BUILD_BIN:-1}"
NEAT1_RECORD_LIMIT="${NEAT1_RECORD_LIMIT:-1}"
REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-1}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

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
case "$REPLAY_PROBE_MAX_TASKS" in
  ''|*[!0-9]*)
    echo "REPLAY_PROBE_MAX_TASKS must be a non-negative integer, got: $REPLAY_PROBE_MAX_TASKS" >&2
    exit 1
    ;;
esac
if [[ "$REPLAY_PROBE_MAX_TASKS" -le 0 ]]; then
  echo "runtime smoke requires REPLAY_PROBE_MAX_TASKS > 0 to bound cost" >&2
  exit 1
fi

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing NEAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"
sample="$WORK/inputs/neat1_first${NEAT1_RECORD_LIMIT}.fa"
awk -v limit="$NEAT1_RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"
if [[ ! -s "$sample" ]]; then
  echo "empty NEAT1 sample" >&2
  exit 1
fi

run_fasim() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$sample" \
    -f2 "$RNA_INPUT" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

digest_for_dir() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  sha256sum "$out_file" | awk '{print $1}'
}

baseline_dir="$WORK/baseline"
candidate_dir="$WORK/candidate"
run_fasim "$baseline_dir"
run_fasim "$candidate_dir" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS="$REPLAY_PROBE_MAX_TASKS" \
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1 \
  FASIM_ALIGN_GASAL2=1

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
if [[ "$baseline_digest" != "$candidate_digest" ]]; then
  echo "segmented score-prepass state-machine shadow changed lite output digest" >&2
  echo "baseline=$baseline_digest candidate=$candidate_digest" >&2
  exit 1
fi

python3 - "$candidate_dir/stderr.log" "$candidate_digest" "$REPLAY_PROBE_MAX_TASKS" <<'PY'
import sys
from pathlib import Path

stderr = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
digest = sys.argv[2]
max_tasks = int(sys.argv[3])

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

def float_metric(name: str) -> float:
    return float(metric(name))

if int_metric("scoreinfo_mismatches") != 0:
    raise SystemExit("streaming scoreInfo mismatch under segmented state-machine smoke")
if int_metric("realpath_fallbacks") != 0:
    raise SystemExit("streaming realpath fallback should remain zero")
if int_metric("score_prepass_state_machine_shadow_requested") != 1:
    raise SystemExit("segmented state-machine shadow was not requested")
if int_metric("score_prepass_state_machine_shadow_active") != 1:
    raise SystemExit("segmented state-machine shadow was not active")
shadow_tasks = int_metric("score_prepass_state_machine_shadow_tasks")
if shadow_tasks <= 0:
    raise SystemExit("segmented state-machine task count should be positive")
if shadow_tasks < max_tasks:
    raise SystemExit("segmented state-machine task count below requested probe cap")
if shadow_tasks > int_metric("tasks"):
    raise SystemExit("segmented state-machine task count exceeds total tasks")
if int_metric("score_prepass_state_machine_shadow_attempts") <= 0:
    raise SystemExit("segmented state-machine attempts should be positive")
if int_metric("score_prepass_state_machine_shadow_selected_attempts") <= 0:
    raise SystemExit("segmented state-machine selected attempts should be positive")
if int_metric("score_prepass_state_machine_shadow_cpu_align_attempts") <= 0:
    raise SystemExit("segmented state-machine CPU align attempts should be positive")
if int_metric("score_prepass_state_machine_shadow_fallbacks") != 0:
    raise SystemExit("segmented state-machine fallback should be zero")
if int_metric("score_prepass_state_machine_shadow_triplex_mismatches") != 0:
    raise SystemExit(
        "segmented state-machine triplex mismatch: "
        + metric("score_prepass_state_machine_shadow_first_mismatch_kind")
    )
if metric("score_prepass_state_machine_shadow_first_mismatch_source") != "none":
    raise SystemExit("unexpected segmented state-machine mismatch source")
if float_metric("score_prepass_state_machine_shadow_cpu_align_seconds") <= 0.0:
    raise SystemExit("segmented state-machine CPU align seconds should be positive")
if int(bench.get("fasim_gasal2_length_guard_fallbacks", "0")) != 0:
    raise SystemExit("segmented state-machine path should not hit GASAL2 length guard")

print("digest=" + digest)
print("tasks=" + metric("tasks"))
print("score_prepass_state_machine_shadow_attempts=" + metric("score_prepass_state_machine_shadow_attempts"))
print("score_prepass_state_machine_shadow_selected_attempts=" + metric("score_prepass_state_machine_shadow_selected_attempts"))
print("score_prepass_state_machine_shadow_cpu_align_attempts=" + metric("score_prepass_state_machine_shadow_cpu_align_attempts"))
print("score_prepass_state_machine_shadow_triplex_mismatches=0")
print("ok")
PY
