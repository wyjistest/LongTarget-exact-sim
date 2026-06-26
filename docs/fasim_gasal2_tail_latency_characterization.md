# Fasim GASAL2 Tail-Latency Characterization

This checkpoint characterizes the H19 whole-genome GASAL2-LongTarget
`rule=0` archive-first run at chromosome-shard granularity. It is
telemetry-only: it does not change scheduling, partitioning, scoring,
traceback, conversion, sorting, de-duplication, or output semantics.

## Scope

```text
query: H19.fa
target: hg38 primary chromosomes, chr1-22 + chrX + chrY
rule: 0
GASAL2 output: archive-first TFOA
Fasim comparison: lite output
```

Inputs:

```text
.tmp/gasal2_hg38_archive_first_rule0_run/summary.json
.tmp/fasim_hg38_rule0_batches/overlap_speedup_by_chromosome.tsv
```

Generated artifacts:

```text
.tmp/fasim_hg38_rule0_batches/gasal2_tail_latency_summary.txt
.tmp/fasim_hg38_rule0_batches/gasal2_tail_latency_by_chromosome.tsv
```

## Key Result

The current chromosome-sharded GASAL2 run does not show a severe
KegAlign-like straggler pattern at shard granularity.

```text
shards                         24
outer wall                     2677.003204 s
sum shard wall                 5265.515529 s
median shard wall               229.207994 s
max shard wall                  427.075548 s
max shard                       chr2
max / median wall ratio           1.863266
top 1 shard wall fraction          8.1108%
top 3 shard wall fraction         22.6178%
top 5 shard wall fraction         35.1214%
decision                       tail_latency_not_material
```

The largest shards are longer, but not pathological. The top shard is only
8.1% of summed shard wall, and the top five account for 35.1%.

## Predictors

Shard wall is almost perfectly explained by work-count telemetry:

```text
wall_corr_gasal2_total_seconds     0.999938
wall_corr_gasal2_requests          0.999872
wall_corr_traceback_requests       0.999853
wall_corr_convert_seconds          0.999866
wall_corr_gasal2_rows              0.967712
wall_corr_gzip_bytes               0.967484
wall_corr_archive_bytes            0.964873
```

The strongest practical predictors are therefore:

```text
GASAL2 requests
traceback requests
convert seconds
```

Output row counts and archive sizes are also correlated, but they are weaker
than request/traceback telemetry.

## Interpretation

This result argues against making diagonal partitioning the immediate next
step. KegAlign-style diagonal partitioning is attractive when the current
partitioning creates extreme stragglers or violates task balance. In this
H19/hg38-primary run, chromosome-level work is already sufficiently smooth that
the best next scheduling improvement is likely simpler:

```text
request-weighted or traceback-weighted bin packing
```

Rather than:

```text
new diagonal partitioning with representative-selection risk
```

Any diagonal or contract-aware candidate-equivalence partition should remain a
shadow design until it proves:

```text
full-row overlap does not regress
top-k contracts remain clean
cross-partition duplicate/representative behavior does not worsen
wall time improves over request-weighted scheduling
```

## Next Useful Work

The missing level is not chromosome-shard telemetry; it is flush-level
pipeline telemetry. The next characterization should record, per flush:

```text
alignment requests
DP cells
traceback requests
exact-column tasks
GPU extend seconds
exact-column seconds
convert seconds
final rows
dedup removed
producer blocked seconds
consumer wait seconds
ready queue depth
completed queue depth
```

This will answer whether GPU utilization is limited by CPU conversion,
archive/output backpressure, or queue starvation. Only if flush-level data
shows a meaningful long tail should the project move to contract-aware
partitioning.

## Verification

```bash
bash scripts/check_fasim_gasal2_tail_latency_parser.sh

python3 scripts/summarize_fasim_gasal2_tail_latency.py \
  --gasal2-summary .tmp/gasal2_hg38_archive_first_rule0_run/summary.json \
  --overlap-tsv .tmp/fasim_hg38_rule0_batches/overlap_speedup_by_chromosome.tsv \
  --output-tsv .tmp/fasim_hg38_rule0_batches/gasal2_tail_latency_by_chromosome.tsv \
  --output-summary .tmp/fasim_hg38_rule0_batches/gasal2_tail_latency_summary.txt
```
