#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_make_anchor_shards"
rm -rf "$WORK"
mkdir -p "$WORK/out"

cat >"$WORK/hg38_chr22.fa" <<'EOF'
>hg38|chr22|1-20
ACGTACGTACGTACGTACGT
EOF

python3 "$ROOT/scripts/make_anchor_shards.py" \
  --input-fasta "$WORK/hg38_chr22.fa" \
  --output-dir "$WORK/out" \
  --starts 1,5 \
  --length 4 >/dev/null

python3 - "$WORK/out" <<'PY'
from pathlib import Path
import sys

out_dir = Path(sys.argv[1])
files = sorted(path.name for path in out_dir.glob("*.fa"))
assert files == ["hg38_chr22_1_4.fa", "hg38_chr22_5_4.fa"], files

expected = {
    "hg38_chr22_1_4.fa": (">hg38|chr22|1-4", "ACGT"),
    "hg38_chr22_5_4.fa": (">hg38|chr22|5-8", "ACGT"),
}

for name, (header, seq) in expected.items():
    lines = (out_dir / name).read_text(encoding="utf-8").splitlines()
    assert lines[0] == header, (name, lines[0])
    assert "".join(lines[1:]) == seq, (name, lines[1:])
PY

if python3 "$ROOT/scripts/make_anchor_shards.py" \
  --input-fasta "$WORK/hg38_chr22.fa" \
  --output-dir "$WORK/out_overflow" \
  --starts 18 \
  --length 4 >/dev/null 2>"$WORK/overflow.err"; then
  echo "expected overflow request to fail" >&2
  exit 1
fi

grep -q "exceeds sequence length" "$WORK/overflow.err"

echo "ok"
