#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${FASIM_OPENMP_BIN:-$ROOT/fasim_longtarget_openmp}"
THREADS="${FASIM_OPENMP_THREADS:-${OMP_NUM_THREADS:-4}}"

if [[ ! "$THREADS" =~ ^[1-9][0-9]*$ ]]; then
  echo "FASIM_OPENMP_THREADS/OMP_NUM_THREADS must be a positive integer" >&2
  exit 2
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing OpenMP Fasim binary: $BIN" >&2
  echo "build it with: make build-fasim-openmp" >&2
  exit 2
fi

# One process owns the target and each OpenMP worker owns only its DP state.
# A single glibc arena prevents idle worker arenas from retaining peak RSS.
export FASIM_OPENMP=1
export FASIM_OPENMP_THREADS="$THREADS"
export OMP_NUM_THREADS="$THREADS"
export OMP_DYNAMIC="${OMP_DYNAMIC:-FALSE}"
# The legacy full-output path prints one line per target window when verbose.
# Keep that diagnostic mode opt-in: interleaved worker output both destroys
# useful throughput and intentionally disables the OpenMP window loop.
export FASIM_VERBOSE="${FASIM_VERBOSE:-0}"
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-1}"

exec "$BIN" -C "$THREADS" "$@"
