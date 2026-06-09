#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat >&2 <<'EOF'
usage: run_fasim_long_query_streaming_scoreinfo_neat1_audited.sh \
  --fasim-bin BIN --target TARGET.fa --rna RNA.fa --work-dir DIR [options]

Runs a CPU-authority baseline and a default-off NEAT1-like non-shared legacy-byte
GASAL2 scoreInfo candidate. The candidate is accepted only when merged digest,
scoreInfo realpath coverage, and segmented/full/oracle replay probes pass.

Options:
  --rule N
  --output-mode MODE
  --replay-probe-max-tasks N  (default 1; 0 = all tasks)
  --resume
  --force
EOF
}

fasim_bin=""
target=""
rna=""
work_dir=""
rule="0"
output_mode="lite"
replay_probe_max_tasks="1"
force=0
resume=0

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --fasim-bin)
      fasim_bin="$2"
      shift 2
      ;;
    --target)
      target="$2"
      shift 2
      ;;
    --rna)
      rna="$2"
      shift 2
      ;;
    --work-dir)
      work_dir="$2"
      shift 2
      ;;
    --rule)
      rule="$2"
      shift 2
      ;;
    --output-mode)
      output_mode="$2"
      shift 2
      ;;
    --replay-probe-max-tasks)
      replay_probe_max_tasks="$2"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    --resume)
      resume=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$fasim_bin" || -z "$target" || -z "$rna" || -z "$work_dir" ]]; then
  usage
  exit 2
fi
if [[ ! -x "$fasim_bin" ]]; then
  echo "missing executable --fasim-bin: $fasim_bin" >&2
  exit 1
fi
if [[ ! -s "$target" ]]; then
  echo "missing --target FASTA: $target" >&2
  exit 1
fi
if [[ ! -s "$rna" ]]; then
  echo "missing --rna FASTA: $rna" >&2
  exit 1
fi
if ! [[ "$replay_probe_max_tasks" =~ ^[0-9]+$ ]]; then
  echo "--replay-probe-max-tasks must be >= 0" >&2
  exit 1
fi
if [[ "$resume" == "1" && "$force" == "1" ]]; then
  echo "--resume cannot be combined with --force" >&2
  exit 2
fi
if [[ "$force" == "1" ]]; then
  rm -rf "$work_dir"
fi
mkdir -p "$work_dir"

baseline_dir="$work_dir/baseline"
candidate_dir="$work_dir/candidate"
accepted_dir="$work_dir/accepted"
summary="$work_dir/audit_summary.json"

if [[ "$resume" == "1" ]]; then
  if [[ ! -s "$summary" ]]; then
    echo "missing accepted audit summary for --resume: $summary" >&2
    exit 1
  fi
  python3 - "$summary" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
payload = json.loads(summary_path.read_text(encoding="utf-8"))
if payload.get("audited_status") != "accepted":
    raise SystemExit(
        f"cannot resume non-accepted audit: {payload.get('audited_status')}"
    )
payload["audited_resume"] = True
print(json.dumps(payload, sort_keys=True))
PY
  exit 0
fi

run_fasim() {
  local out_dir="$1"
  shift
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE="$output_mode" \
    FASIM_VERBOSE=0 \
    "$@" \
    "$fasim_bin" \
    -f1 "$target" \
    -f2 "$rna" \
    -r "$rule" \
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

baseline_start="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
run_fasim "$baseline_dir"
baseline_end="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
baseline_runner_wall_seconds="$(python3 - "$baseline_start" "$baseline_end" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
)"

candidate_start="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
run_fasim "$candidate_dir" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_EXTEND_ATTEMPT_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_EXTEND_ATTEMPT_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_FULL_REPLAY_PROBE=1 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS="$replay_probe_max_tasks" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_LEN=2812 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_TILE_OVERLAP=512 \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SEGMENTED_EXTEND_ATTEMPT_PROBE_MAX_SEGMENTS=0 \
  FASIM_ALIGN_GASAL2=1
candidate_end="$(python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
)"
candidate_runner_wall_seconds="$(python3 - "$candidate_start" "$candidate_end" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
)"

baseline_digest="$(digest_for_dir "$baseline_dir")"
candidate_digest="$(digest_for_dir "$candidate_dir")"
python3 - \
  "$baseline_dir/stderr.log" \
  "$candidate_dir/stderr.log" \
  "$baseline_digest" \
  "$candidate_digest" \
  "$candidate_dir" \
  "$accepted_dir" \
  "$summary" \
  "$baseline_runner_wall_seconds" \
  "$candidate_runner_wall_seconds" <<'PY'
import json
import shutil
import sys
from pathlib import Path

baseline_stderr = Path(sys.argv[1])
candidate_stderr = Path(sys.argv[2])
baseline_digest = sys.argv[3]
candidate_digest = sys.argv[4]
candidate_dir = Path(sys.argv[5])
accepted_dir = Path(sys.argv[6])
summary_path = Path(sys.argv[7])
baseline_runner_wall_seconds = float(sys.argv[8])
candidate_runner_wall_seconds = float(sys.argv[9])

def fail(message: str) -> None:
    raise SystemExit(message)

if baseline_digest != candidate_digest:
    fail(f"digest gate failed: baseline={baseline_digest} candidate={candidate_digest}")

bench = {}
for line in candidate_stderr.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key] = value

def metric(name: str) -> str:
    key = "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_" + name
    if key not in bench:
        fail(f"missing metric {key}")
    return bench[key]

def int_metric(name: str) -> int:
    return int(metric(name))

def float_metric(name: str) -> float:
    return float(metric(name))

tasks = int_metric("tasks")
active = int_metric("active")
unsupported = int_metric("unsupported")
legacy_byte_shared = int_metric("legacy_byte_shared")
gpu_tasks = int_metric("gpu_tasks")
gpu_groups = int_metric("gpu_scoreinfo_groups")
cpu_groups = int_metric("cpu_scoreinfo_groups")
scoreinfo_mismatches = int_metric("scoreinfo_mismatches")
realpath_used = int_metric("realpath_used")
realpath_fallbacks = int_metric("realpath_fallbacks")
gpu_minscore_used = int_metric("gpu_minscore_used")
gpu_minscore_fallbacks = int_metric("gpu_minscore_fallbacks")
decision = metric("decision")
error = metric("error")

flushes = int_metric("realpath_extend_flush_segmented_attempt_probe_flushes")
seg_replay_tasks = int_metric("realpath_extend_flush_segmented_replay_probe_tasks")
seg_replay_attempts = int_metric("realpath_extend_flush_segmented_replay_probe_align_attempts")
seg_replay_mismatches = int_metric("realpath_extend_flush_segmented_replay_probe_triplex_mismatches")
seg_replay_seconds = float_metric("realpath_extend_flush_segmented_replay_probe_seconds")
full_replay_tasks = int_metric("realpath_extend_flush_full_replay_probe_tasks")
full_replay_attempts = int_metric("realpath_extend_flush_full_replay_probe_align_attempts")
full_replay_mismatches = int_metric("realpath_extend_flush_full_replay_probe_triplex_mismatches")
full_replay_seconds = float_metric("realpath_extend_flush_full_replay_probe_seconds")
oracle_replay_tasks = int_metric("realpath_extend_flush_oracle_replay_probe_tasks")
oracle_replay_mismatches = int_metric("realpath_extend_flush_oracle_replay_probe_triplex_mismatches")
oracle_replay_seconds = float_metric("realpath_extend_flush_oracle_replay_probe_seconds")

if active != 1 or unsupported != 0:
    fail(f"expected active=1 unsupported=0, got active={active} unsupported={unsupported}")
if legacy_byte_shared != 0:
    fail(f"expected non-shared legacy-byte mode, got {legacy_byte_shared}")
if tasks <= 0 or gpu_tasks != tasks:
    fail(f"expected gpu_tasks == tasks > 0, got tasks={tasks} gpu_tasks={gpu_tasks}")
if gpu_groups <= 0 or cpu_groups != 0:
    fail(f"expected GPU-only scoreInfo groups, got gpu={gpu_groups} cpu={cpu_groups}")
if scoreinfo_mismatches != 0:
    fail(f"scoreInfo mismatches={scoreinfo_mismatches}")
if realpath_used != tasks or realpath_fallbacks != 0:
    fail(f"expected realpath_used=tasks and fallback=0, got used={realpath_used} tasks={tasks} fallback={realpath_fallbacks}")
if gpu_minscore_used != tasks or gpu_minscore_fallbacks != 0:
    fail(f"expected GPU minScore used=tasks and fallback=0, got used={gpu_minscore_used} tasks={tasks} fallback={gpu_minscore_fallbacks}")
if decision != "streaming_scoreinfo_shadow_active" or error != "none":
    fail(f"unexpected decision/error: {decision}/{error}")
if flushes <= 0:
    fail(f"expected positive replay flushes, got {flushes}")
if not (seg_replay_tasks == full_replay_tasks == oracle_replay_tasks):
    fail(f"replay tasks disagree: seg={seg_replay_tasks} full={full_replay_tasks} oracle={oracle_replay_tasks}")
if seg_replay_tasks <= 0:
    fail(f"expected positive replay tasks, got {seg_replay_tasks}")
if seg_replay_attempts <= 0 or full_replay_attempts <= 0:
    fail(f"expected positive replay attempts, got seg={seg_replay_attempts} full={full_replay_attempts}")
if seg_replay_mismatches != 0 or full_replay_mismatches != 0 or oracle_replay_mismatches != 0:
    fail(f"replay mismatches: seg={seg_replay_mismatches} full={full_replay_mismatches} oracle={oracle_replay_mismatches}")

accepted_dir.mkdir(parents=True, exist_ok=True)
candidate_output = sorted(candidate_dir.glob("*-TFOsorted.lite"))
if not candidate_output:
    fail("missing candidate lite output")
accepted_output = accepted_dir / candidate_output[0].name
shutil.copy2(candidate_output[0], accepted_output)

summary = {
    "audited_status": "accepted",
    "audited_resume": False,
    "baseline_digest": baseline_digest,
    "candidate_digest": candidate_digest,
    "accepted_output": str(accepted_output),
    "result_contract": "long_query_streaming_scoreinfo_gpu_trust_nonshared_neat1_audit_v1",
    "trust_profile": "neat1_like_nonshared_experimental_v1",
    "baseline_runner_wall_seconds": baseline_runner_wall_seconds,
    "candidate_runner_wall_seconds": candidate_runner_wall_seconds,
    "candidate_vs_baseline": (
        baseline_runner_wall_seconds / candidate_runner_wall_seconds
        if candidate_runner_wall_seconds > 0.0
        else 0.0
    ),
    "tasks": tasks,
    "realpath_used": realpath_used,
    "realpath_fallbacks": realpath_fallbacks,
    "gpu_scoreinfo_groups": gpu_groups,
    "cpu_scoreinfo_groups": cpu_groups,
    "legacy_byte_shared": legacy_byte_shared,
    "gpu_total_seconds": float_metric("total_seconds"),
    "gpu_call_seconds": float_metric("gpu_call_seconds"),
    "gpu_kernel_seconds": float_metric("kernel_seconds"),
    "candidate_realpath_extend_seconds": float_metric("realpath_extend_seconds"),
    "candidate_realpath_extend_align_seconds": float_metric("realpath_extend_align_seconds"),
    "candidate_realpath_extend_flush_segmented_attempt_probe_flushes": flushes,
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks": seg_replay_tasks,
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts": seg_replay_attempts,
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches": seg_replay_mismatches,
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds": seg_replay_seconds,
    "candidate_realpath_extend_flush_full_replay_probe_tasks": full_replay_tasks,
    "candidate_realpath_extend_flush_full_replay_probe_align_attempts": full_replay_attempts,
    "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches": full_replay_mismatches,
    "candidate_realpath_extend_flush_full_replay_probe_seconds": full_replay_seconds,
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks": oracle_replay_tasks,
    "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches": oracle_replay_mismatches,
    "candidate_realpath_extend_flush_oracle_replay_probe_seconds": oracle_replay_seconds,
}
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
PY
