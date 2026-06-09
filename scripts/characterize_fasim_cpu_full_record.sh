#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_cpu_full_record"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr22.fa.gz"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK/input" "$WORK/out"

DNA_RUN="$DNA"
case "$DNA" in
  *.gz)
    DNA_RUN="$WORK/input/$(basename "${DNA%.gz}")"
    gzip -dc "$DNA" >"$DNA_RUN"
    ;;
esac

start_seconds="$(date +%s)"
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  "$BIN" -f1 "$DNA_RUN" -f2 "$RNA" -r "$RULE" -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"
end_seconds="$(date +%s)"
wall_seconds="$((end_seconds - start_seconds))"
printf '%s\n' "$wall_seconds" >"$WORK/wall_seconds.txt"

out_path="$(find "$WORK/out" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$out_path" ]]; then
  echo "expected one lite output" >&2
  exit 1
fi

digest="$(sha256sum "$out_path" | awk '{print $1}')"
lines="$(wc -l < "$out_path")"

cat >"$WORK/summary.txt" <<EOF
dna=$DNA
dna_run=$DNA_RUN
rna=$RNA
rule=$RULE
wall_seconds=$wall_seconds
digest=$digest
lines=$lines
output=$out_path
stdout=$WORK/stdout.log
stderr=$WORK/stderr.log
EOF

cat "$WORK/summary.txt"
