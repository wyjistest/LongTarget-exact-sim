#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
BIN="${BIN:-"$ROOT_DIR/fasim_longtarget_cuda"}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT_DIR"
    make build-fasim-cuda
  )
fi

POLICY="${FASIM_THRESHOLD_POLICY:-fasim_peak80}"
case "$POLICY" in
  fasim_peak80)
    ;;
  *)
    echo "unsupported FASIM_THRESHOLD_POLICY: $POLICY" >&2
    exit 2
    ;;
esac

export FASIM_ENABLE_PREALIGN_CUDA="${FASIM_ENABLE_PREALIGN_CUDA:-1}"
export FASIM_PREALIGN_CUDA_TOPK="${FASIM_PREALIGN_CUDA_TOPK:-64}"
export FASIM_PREALIGN_PEAK_SUPPRESS_BP="${FASIM_PREALIGN_PEAK_SUPPRESS_BP:-5}"
export FASIM_VERBOSE="${FASIM_VERBOSE:-0}"
export FASIM_OUTPUT_MODE="${FASIM_OUTPUT_MODE:-lite}"

exec "$BIN" "$@" >/dev/null
