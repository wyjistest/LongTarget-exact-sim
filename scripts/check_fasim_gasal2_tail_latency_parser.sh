#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_tail_latency_parser"}"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/gasal2_summary.json" <<'JSON'
{
  "outer_wall_seconds": 100.0,
  "total_archive_bytes": 3000,
  "total_archive_gzip_bytes": 1200,
  "shards": [
    {
      "chrom": "chrA",
      "wall_seconds": 10.0,
      "archive_bytes": 1000,
      "archive_gzip_bytes": 400,
      "metrics": {
        "benchmark.fasim_gasal2_requests": "100",
        "benchmark.fasim_gasal2_traceback_requests": "50",
        "benchmark.fasim_gasal2_cpu_traceback_convert_seconds": "4",
        "benchmark.fasim_gasal2_total_seconds": "7"
      }
    },
    {
      "chrom": "chrB",
      "wall_seconds": 30.0,
      "archive_bytes": 2000,
      "archive_gzip_bytes": 800,
      "metrics": {
        "benchmark.fasim_gasal2_requests": "300",
        "benchmark.fasim_gasal2_traceback_requests": "150",
        "benchmark.fasim_gasal2_cpu_traceback_convert_seconds": "12",
        "benchmark.fasim_gasal2_total_seconds": "21"
      }
    }
  ]
}
JSON

cat >"$WORK/overlap.tsv" <<'TSV'
chrom	fasim_wall_seconds	gasal2_wall_seconds	speedup	fasim_rows	gasal2_rows	common_rows	fasim_only_rows	gasal2_only_rows	overlap_vs_fasim	overlap_vs_gasal2	jaccard	fasim_output_bytes	gasal2_archive_bytes	gasal2_gzip_bytes
chrA	100.0	10.0	10.0	1000	1001	990	10	11	0.990000	0.989011	0.979229	10000	1000	400
chrB	400.0	30.0	13.333333	2000	2002	1980	20	22	0.990000	0.989011	0.979229	20000	2000	800
TOTAL_SUM_SHARD_WALL	500.0	40.0	12.5	3000	3003	2970	30	33	0.990000	0.989011	0.979229	30000	3000	1200
TSV

python3 "$ROOT/scripts/summarize_fasim_gasal2_tail_latency.py" \
  --gasal2-summary "$WORK/gasal2_summary.json" \
  --overlap-tsv "$WORK/overlap.tsv" \
  --output-tsv "$WORK/tail.tsv" \
  --output-summary "$WORK/summary.txt"

grep -q '^tail_latency_decision=material_tail_latency$' "$WORK/summary.txt"
grep -q '^max_to_median_wall_ratio=1.500000$' "$WORK/summary.txt"
grep -q '^top_1_shards_wall_fraction=0.750000$' "$WORK/summary.txt"
grep -q '^wall_corr_gasal2_requests=1.000000$' "$WORK/summary.txt"
grep -Eq '^best_wall_predictor=(gasal2_requests|traceback_requests|gasal2_total_seconds|convert_seconds|gasal2_rows|archive_bytes|gzip_bytes)$' "$WORK/summary.txt"
grep -q '^chrB	30.000000	0.750000	300.000000	150.000000	2002.000000	13.333333' "$WORK/tail.tsv"

echo "check_fasim_gasal2_tail_latency_parser: ok"
