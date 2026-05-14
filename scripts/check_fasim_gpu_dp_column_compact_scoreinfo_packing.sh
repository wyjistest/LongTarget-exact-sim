#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_DIGEST_FILE="$ROOT/tests/oracle_fasim_profile/sample_lite.digest"
WORK_DIR="$ROOT/.tmp/fasim_gpu_dp_column_compact_scoreinfo_packing/check"
LOG_FILE="$WORK_DIR/profile.log"

mkdir -p "$WORK_DIR"

FASIM_TRANSFERSTRING_TABLE=1 \
FASIM_GPU_DP_COLUMN=1 \
FASIM_GPU_DP_COLUMN_VALIDATE=1 \
FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG=1 \
FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1 \
python3 "$ROOT/scripts/benchmark_fasim_profile.py" \
  --mode exactness \
  --bin "$ROOT/fasim_longtarget_cuda" \
  --expected-digest-file "$EXPECTED_DIGEST_FILE" \
  --require-profile \
  --work-dir "$WORK_DIR/run" \
  >"$LOG_FILE"

require_metric() {
  local key="$1"
  local expected="$2"
  if ! grep -Eq "^benchmark\\.${key}=${expected}$" "$LOG_FILE"; then
    echo "missing or unexpected compact scoreInfo metric: ${key}=${expected}" >&2
    echo "see $LOG_FILE" >&2
    exit 1
  fi
}

require_metric "fasim_gpu_dp_column_compact_scoreinfo_requested" "1"
require_metric "fasim_gpu_dp_column_compact_scoreinfo_active" "1"
require_metric "fasim_gpu_dp_column_compact_scoreinfo_mismatches" "0"
require_metric "fasim_gpu_dp_column_compact_scoreinfo_fallbacks" "0"
require_metric "fasim_gpu_dp_column_exact_scoreinfo_extend_calls" "0"

if ! grep -Eq '^benchmark\.fasim_gpu_dp_column_compact_scoreinfo_records=[1-9][0-9]*$' "$LOG_FILE"; then
  echo "expected compact scoreInfo records to be reported" >&2
  echo "see $LOG_FILE" >&2
  exit 1
fi

if ! grep -Eq '^benchmark\.fasim_output_digest=sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6$' "$LOG_FILE"; then
  echo "unexpected compact scoreInfo output digest" >&2
  echo "see $LOG_FILE" >&2
  exit 1
fi
