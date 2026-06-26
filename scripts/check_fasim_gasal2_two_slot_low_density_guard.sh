#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_two_slot_low_density_guard"}"
TARGET="${TARGET:-"$ROOT/.tmp/check_fasim_gasal2_flush_two_slot_multi_worker_2gpu_smoke_v2/inputs/smoke_multi_worker.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

if [[ ! -s "$TARGET" ]]; then
  SMOKE=1 WORK="$WORK/input_smoke" REPEATS=1 "$ROOT/scripts/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu.sh" >/dev/null
  TARGET="$WORK/input_smoke/inputs/smoke_multi_worker.fa"
fi

rm -rf "$WORK/fail" "$WORK/allow"
mkdir -p "$WORK"

set +e
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$TARGET" \
  --rna "$RNA" \
  --rule 0 \
  --work-dir "$WORK/fail" \
  --output-mode lite \
  --workers 2 \
  --gpu-ids 0 \
  --env FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1 \
  >"$WORK/fail.stdout" 2>"$WORK/fail.stderr"
fail_rc=$?
set -e

if [[ "$fail_rc" == "0" ]]; then
  echo "expected low-density guard to reject two-slot GPU sharing" >&2
  exit 1
fi
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP is default-off recommended only' "$WORK/fail.stderr"
grep -q 'one-worker-per-GPU' "$WORK/fail.stderr"
grep -q 'FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING=1' "$WORK/fail.stderr"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$TARGET" \
  --rna "$RNA" \
  --rule 0 \
  --work-dir "$WORK/allow" \
  --output-mode lite \
  --workers 2 \
  --gpu-ids 0 \
  --env FASIM_GASAL2_FLUSH_TWO_SLOT_OVERLAP=1 \
  --env FASIM_GASAL2_FLUSH_TWO_SLOT_ALLOW_GPU_SHARING=1 \
  >"$WORK/allow.stdout" 2>"$WORK/allow.stderr"

python3 - "$WORK/allow/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
guard = report["two_slot_low_density_guard"]
assert guard["requested"] is True
assert guard["active"] is True
assert guard["allow_gpu_sharing"] is True
assert guard["gpu_sharing"] is True
assert guard["disabled_reason"] == "none"
assert guard["recommended_scope"] == "single_worker_or_one_worker_per_gpu"
print("check_fasim_gasal2_two_slot_low_density_guard: ok")
PY
