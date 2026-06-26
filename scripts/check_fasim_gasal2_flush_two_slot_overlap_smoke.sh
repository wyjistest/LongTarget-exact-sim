#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_two_slot_overlap_smoke"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

metric_value() {
  local file="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file"
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/two_slot_serialized" "$WORK/two_slot" "$WORK/two_slot_validate"

run_case() {
  local label="$1"
  local extracted="$2"
  local two_slot="$3"
  local validate="$4"
  local serialized="$5"
  local out_dir="$WORK/$label"
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
    FASIM_ALIGN_GASAL2_STREAMS=3 \
    FASIM_ALIGN_GASAL2_BATCH=20000 \
    FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER="$extracted" \
    FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP="$two_slot" \
    FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP_VALIDATE="$validate" \
    FASIM_GASAL2_FLUSH_TWO_SLOT_SERIALIZED_CONTROL="$serialized" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 1 0 0 0
run_case two_slot_serialized 0 0 0 1
run_case two_slot 0 1 0 0
run_case two_slot_validate 0 1 1 0

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
serialized_lite="$(find "$WORK/two_slot_serialized" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
two_slot_lite="$(find "$WORK/two_slot" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
validate_lite="$(find "$WORK/two_slot_validate" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$serialized_lite" || -z "$two_slot_lite" || -z "$validate_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
for lite in "$serialized_lite" "$two_slot_lite" "$validate_lite"; do
  if ! cmp -s "$baseline_lite" "$lite"; then
    echo "two-slot path changed lite output: $lite" >&2
    exit 1
  fi
done

stderr="$WORK/two_slot/stderr.log"
requested="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_requested)"
active="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_active)"
validate_requested="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_validate_requested)"
validate_active="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_validate_active)"
disabled_reason="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_disabled_reason)"
flushes="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_observed)"
submitted="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_gpu_submitted)"
finalized="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_finalized)"
committed="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_flushes_committed)"
unsupported="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_unsupported_flushes)"
fallback="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_legacy_fallback_flushes)"
slot0_submit="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_submit_count)"
slot1_submit="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_submit_count)"
slot0_finalize="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_finalize_count)"
slot1_finalize="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_finalize_count)"
slot0_commit="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_commit_count)"
slot1_commit="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_commit_count)"
state_violations="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_state_transition_violations)"
order_violations="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_order_violations)"
missing_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_missing_rows)"
extra_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_extra_rows)"
host_peak="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_host_peak_bytes)"
gpu_cpu_supported="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_measurement_supported)"
gpu_cpu_overlap="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_gpu_cpu_overlap_seconds)"
slot0_peak_live="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot0_peak_live_bytes)"
slot1_peak_live="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_slot1_peak_live_bytes)"
max_live_slots="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_max_live_slots)"
time_with_two_live="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_time_with_2_live_slots_seconds)"
host_overlap="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds)"
decision="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_decision)"

if [[ "$requested" != "1" || "$active" != "1" || "$validate_requested" != "0" || "$validate_active" != "0" ]]; then
  echo "unexpected two-slot activation: requested=$requested active=$active validate_requested=$validate_requested validate_active=$validate_active" >&2
  exit 1
fi
if [[ "$disabled_reason" != "none" || "$decision" != "two_slot_active_clean_no_fallback" ]]; then
  echo "unexpected two-slot decision: disabled=$disabled_reason decision=$decision" >&2
  exit 1
fi
if (( flushes < 1 || submitted != finalized || submitted != committed || submitted < 1 )); then
  echo "two-slot flush accounting mismatch: flushes=$flushes submitted=$submitted finalized=$finalized committed=$committed" >&2
  exit 1
fi
if (( unsupported != 0 || fallback != 0 || state_violations != 0 || order_violations != 0 || missing_rows != 0 || extra_rows != 0 )); then
  echo "two-slot correctness counters not clean" >&2
  exit 1
fi
if (( host_peak < 1 )); then
  echo "expected nonzero host peak bytes" >&2
  exit 1
fi
if [[ "$gpu_cpu_supported" != "0" || "$gpu_cpu_overlap" != "unavailable" ]]; then
  echo "unexpected GPU/CPU overlap support marker: supported=$gpu_cpu_supported overlap=$gpu_cpu_overlap" >&2
  exit 1
fi
if (( slot0_submit < 1 || slot1_submit < 1 || slot0_finalize < 1 || slot1_finalize < 1 || slot0_commit < 1 || slot1_commit < 1 )); then
  echo "expected both slots to be used: submit=$slot0_submit/$slot1_submit finalize=$slot0_finalize/$slot1_finalize commit=$slot0_commit/$slot1_commit" >&2
  exit 1
fi
if (( slot0_peak_live < 1 || slot1_peak_live < 1 || max_live_slots < 1 )); then
  echo "expected live slot accounting: slot_peak=$slot0_peak_live/$slot1_peak_live max_live_slots=$max_live_slots" >&2
  exit 1
fi
python3 - "$time_with_two_live" "$host_overlap" <<'PY'
import sys
time_with_two = float(sys.argv[1])
host_overlap = float(sys.argv[2])
if time_with_two < 0.0:
    raise SystemExit("negative time_with_2_live_slots_seconds")
if host_overlap < 0.0:
    raise SystemExit("negative host_scheduling_overlap_seconds")
PY

serialized_stderr="$WORK/two_slot_serialized/stderr.log"
serialized_requested="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_requested)"
serialized_active="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_active)"
serialized_control_requested="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_serialized_control_requested)"
serialized_control_active="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_serialized_control_active)"
serialized_decision="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_decision)"
serialized_max_live_slots="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_max_live_slots)"
serialized_host_overlap="$(metric_value "$serialized_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_host_scheduling_overlap_seconds)"
if [[ "$serialized_requested" != "1" || "$serialized_active" != "1" || "$serialized_control_requested" != "1" || "$serialized_control_active" != "1" ]]; then
  echo "unexpected serialized control activation: requested=$serialized_requested active=$serialized_active control_requested=$serialized_control_requested control_active=$serialized_control_active" >&2
  exit 1
fi
if [[ "$serialized_decision" != "two_slot_serialized_control_clean_no_fallback" ]]; then
  echo "unexpected serialized decision: $serialized_decision" >&2
  exit 1
fi
if (( serialized_max_live_slots > 1 )); then
  echo "serialized control should not have two live slots: max_live_slots=$serialized_max_live_slots" >&2
  exit 1
fi
python3 - "$serialized_host_overlap" <<'PY'
import sys
if float(sys.argv[1]) != 0.0:
    raise SystemExit("serialized control should have zero host scheduling overlap")
PY

validate_stderr="$WORK/two_slot_validate/stderr.log"
validate_case_requested="$(metric_value "$validate_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_requested)"
validate_case_active="$(metric_value "$validate_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_active)"
validate_case_validate_requested="$(metric_value "$validate_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_validate_requested)"
validate_case_validate_active="$(metric_value "$validate_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_validate_active)"
validate_case_decision="$(metric_value "$validate_stderr" benchmark.fasim_gasal2_flush_two_slot_overlap_decision)"
if [[ "$validate_case_requested" != "1" || "$validate_case_active" != "0" || "$validate_case_validate_requested" != "1" || "$validate_case_validate_active" != "1" ]]; then
  echo "unexpected validate accounting: requested=$validate_case_requested active=$validate_case_active validate_requested=$validate_case_validate_requested validate_active=$validate_case_validate_active" >&2
  exit 1
fi
if [[ "$validate_case_decision" != "validate_mode_synchronous_audit" ]]; then
  echo "unexpected validate decision: $validate_case_decision" >&2
  exit 1
fi

{
  printf 'two_slot_requested=%s\n' "$requested"
  printf 'two_slot_active=%s\n' "$active"
  printf 'two_slot_flushes_gpu_submitted=%s\n' "$submitted"
  printf 'two_slot_flushes_finalized=%s\n' "$finalized"
  printf 'two_slot_flushes_committed=%s\n' "$committed"
  printf 'two_slot_slot0_submit_count=%s\n' "$slot0_submit"
  printf 'two_slot_slot1_submit_count=%s\n' "$slot1_submit"
  printf 'two_slot_max_live_slots=%s\n' "$max_live_slots"
  printf 'two_slot_host_scheduling_overlap_seconds=%s\n' "$host_overlap"
  printf 'two_slot_host_peak_bytes=%s\n' "$host_peak"
  printf 'two_slot_decision=%s\n' "$decision"
  printf 'serialized_decision=%s\n' "$serialized_decision"
  printf 'lite_sha256=%s\n' "$(sha256sum "$two_slot_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_two_slot_overlap_smoke: ok"
