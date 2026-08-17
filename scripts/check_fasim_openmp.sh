#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${FASIM_OPENMP_BIN:-$ROOT/.tmp/fasim_longtarget_openmp_check}"
THREADS="${FASIM_OPENMP_THREADS:-4}"

make -C "$ROOT" --no-print-directory build-fasim-openmp \
  FASIM_OPENMP_TARGET="$BIN"

FASIM_OPENMP=1 \
FASIM_OPENMP_THREADS="$THREADS" \
OMP_NUM_THREADS="$THREADS" \
FASIM_VERBOSE=0 \
FASIM_OPENMP_BIN="$BIN" \
MALLOC_ARENA_MAX=1 \
BIN="$BIN" \
bash "$ROOT/scripts/check_fasim_sharded_runner.sh"

# The sharded runner intentionally uses the streaming/lite path. Exercise the
# legacy full-output path separately, because that is where the window-level
# OpenMP implementation lives.
WORK="$ROOT/.tmp/check_fasim_openmp_full"
rm -rf "$WORK"
mkdir -p "$WORK/serial" "$WORK/parallel"

FASIM_VERBOSE=0 \
FASIM_OPENMP=0 \
FASIM_OUTPUT_MODE=full \
OMP_NUM_THREADS=1 \
MALLOC_ARENA_MAX=1 \
"$BIN" \
  -f1 "$ROOT/testDNA.fa" \
  -f2 "$ROOT/H19.fa" \
  -r 1 \
  -c 1000 \
  -O "$WORK/serial" \
  >"$WORK/serial.stdout.log" \
  2>"$WORK/serial.stderr.log"

FASIM_VERBOSE=0 \
FASIM_OPENMP=1 \
FASIM_OUTPUT_MODE=full \
FASIM_OPENMP_THREADS="$THREADS" \
OMP_NUM_THREADS="$THREADS" \
OMP_DYNAMIC=FALSE \
MALLOC_ARENA_MAX=1 \
"$BIN" \
  -f1 "$ROOT/testDNA.fa" \
  -f2 "$ROOT/H19.fa" \
  -r 1 \
  -c 1000 \
  -O "$WORK/parallel" \
  >"$WORK/parallel.stdout.log" \
  2>"$WORK/parallel.stderr.log"

grep -q '^benchmark\.fasim_openmp\.active=1$' "$WORK/parallel.stderr.log"
windows="$(sed -n 's/^benchmark\.fasim_openmp\.windows=//p' "$WORK/parallel.stderr.log")"
if [[ -z "$windows" || "$windows" -le 1 ]]; then
  echo "OpenMP full-output probe did not report multiple target windows" >&2
  exit 1
fi

for suffix in TFOsorted TFOclass1-15-50 TFOclass2-15-50; do
  serial_file="$(find "$WORK/serial" -type f -name "*-${suffix}" -print -quit)"
  parallel_file="$(find "$WORK/parallel" -type f -name "*-${suffix}" -print -quit)"
  if [[ -z "$serial_file" || -z "$parallel_file" ]]; then
    echo "missing full-output probe artifact: $suffix" >&2
    exit 1
  fi
  cmp -s "$serial_file" "$parallel_file" || {
    echo "OpenMP full-output mismatch: $suffix" >&2
    exit 1
  }
done

# Do not use rg -q in a pipe under pipefail: rg exits as soon as it finds a
# match, which can make nm receive SIGPIPE and incorrectly fail this check.
if ! nm -C "$BIN" | rg 'GOMP_parallel|omp_get_max_threads' >/dev/null; then
  echo "OpenMP runtime symbols are missing from $BIN" >&2
  exit 1
fi

echo "fasim OpenMP exactness check OK (threads=$THREADS)"
