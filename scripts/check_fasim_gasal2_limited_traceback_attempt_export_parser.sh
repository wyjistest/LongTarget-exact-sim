#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_limited_traceback_attempt_export_parser"}"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/attempts.tsv" <<'TSV'
batch_id	position	attempt_index	decision	prealign_score	scoreinfo_index	start	cutlength	target_size	nt_min_length	target_end_required_for_fallback	target_offset	target_length
0	0	0	keep	220	1	100	80	80	50	179	100	80
0	1	1	keep	140	1	180	70	70	50	249	180	70
0	2	2	skip	70	2	250	55	55	50	304	250	55
0	3	3	skip	50	2	305	50	50	50	354	305	50
TSV

python3 "$ROOT/scripts/analyze_fasim_gasal2_limited_traceback_attempt_export.py" \
  "$WORK/attempts.tsv" >"$WORK/summary.txt"

grep -q '^rows=4$' "$WORK/summary.txt"
grep -q '^keep_rows=2$' "$WORK/summary.txt"
grep -q '^skip_rows=2$' "$WORK/summary.txt"
grep -q '^skip_fraction=0.500000$' "$WORK/summary.txt"
grep -q '^prealign_score_bin$' "$WORK/summary.txt"
grep -q '^bin	keep	skip	total	skip_fraction$' "$WORK/summary.txt"
grep -q $'^<60\t0\t1\t1\t1.000000$' "$WORK/summary.txt"
grep -q $'^60-79\t0\t1\t1\t1.000000$' "$WORK/summary.txt"
grep -q $'^140-159\t1\t0\t1\t0.000000$' "$WORK/summary.txt"
grep -q $'^>=200\t1\t0\t1\t0.000000$' "$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "ok"
