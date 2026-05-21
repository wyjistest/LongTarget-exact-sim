#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/benchmark_fasim_gpu_dp_column_compact_threshold.py"
DOC="$ROOT/docs/fasim_gpu_dp_column_compact_threshold.md"

test -x "$RUNNER"
test -f "$DOC"

python3 "$RUNNER" --help >/dev/null

grep -qi "activation threshold" "$DOC"
grep -qi "crossover" "$DOC"
grep -q "FASIM_GPU_DP_COLUMN_COMPACT_SCOREINFO=1" "$DOC"
grep -q "FASIM_GPU_DP_COLUMN_AUTO=1" "$DOC"
