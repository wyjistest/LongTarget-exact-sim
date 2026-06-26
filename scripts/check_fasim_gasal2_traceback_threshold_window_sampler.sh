#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_traceback_threshold_window_sampler"}"
SAMPLER="$ROOT/scripts/sample_fasta_windows.py"

if [[ ! -s "$SAMPLER" ]]; then
  echo "missing FASTA window sampler: $SAMPLER" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

python3 - "$WORK/input.fa" <<'PY'
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    ">chrTest\n" + "A" * 100 + "\n",
    encoding="utf-8",
)
PY

python3 "$SAMPLER" \
  --input "$WORK/input.fa" \
  --output "$WORK/windows.fa" \
  --max-records 1 \
  --max-bases 30 \
  --windows 3 \
  --manifest "$WORK/windows.tsv" \
  --metrics "$WORK/metrics.txt"

grep -q '^sample_windows=3$' "$WORK/metrics.txt"
grep -q '^anchor_windows=0$' "$WORK/metrics.txt"
grep -q '^uniform_windows=3$' "$WORK/metrics.txt"
grep -q '^sampled_bases=30$' "$WORK/metrics.txt"
grep -q 'source_start=0|source_end=10' "$WORK/windows.fa"
grep -q 'source_start=45|source_end=55' "$WORK/windows.fa"
grep -q 'source_start=90|source_end=100' "$WORK/windows.fa"
grep -q $'^0\tchrTest\t0\t10\t10\tuniform$' "$WORK/windows.tsv"
grep -q $'^1\tchrTest\t45\t55\t10\tuniform$' "$WORK/windows.tsv"
grep -q $'^2\tchrTest\t90\t100\t10\tuniform$' "$WORK/windows.tsv"

cat >"$WORK/anchors.tsv" <<'EOF'
mode	rank	Chr	StartInGenome	EndInGenome
stability	1	chrTest	70	80
EOF

python3 "$SAMPLER" \
  --input "$WORK/input.fa" \
  --output "$WORK/anchored.fa" \
  --max-records 1 \
  --max-bases 40 \
  --windows 2 \
  --anchor-tsv "$WORK/anchors.tsv" \
  --anchor-window-bases 10 \
  --anchor-max-windows 1 \
  --manifest "$WORK/anchored.tsv" \
  --metrics "$WORK/anchored_metrics.txt"

grep -q '^sample_windows=3$' "$WORK/anchored_metrics.txt"
grep -q '^anchor_windows=1$' "$WORK/anchored_metrics.txt"
grep -q '^uniform_windows=2$' "$WORK/anchored_metrics.txt"
grep -q '^sampled_bases=40$' "$WORK/anchored_metrics.txt"
grep -q $'^0\tchrTest\t70\t80\t10\tanchor$' "$WORK/anchored.tsv"
grep -q $'^1\tchrTest\t0\t15\t15\tuniform$' "$WORK/anchored.tsv"
grep -q $'^2\tchrTest\t85\t100\t15\tuniform$' "$WORK/anchored.tsv"
grep -q 'sample_kind=anchor|source_start=70|source_end=80' "$WORK/anchored.fa"

echo "check_fasim_gasal2_traceback_threshold_window_sampler: ok"
