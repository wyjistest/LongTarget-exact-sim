# Fasim Forward Score GPU Batch Shadow Real-Workload Characterization

This note characterizes the default-off batched forward score/end GPU shadow
from #157 on real workloads.

## Scope

This is a docs/script/result checkpoint only:

- No real score bridge is added.
- GPU score/end results are not used for output.
- GPU endpoint is not used for output.
- No GPU CIGAR or traceback is added.
- No scoring, output, threshold, non-overlap, scheduler, merge, chunking,
  default, or in-process multi-GPU behavior is changed.

CPU `aligner.Align()` remains authoritative for score, endpoint, traceback,
CIGAR, candidate state, output, and digest.

## Command

The matrix was run after #157:

```bash
timeout 1200s python3 scripts/benchmark_fasim_forward_score_batch_shadow_characterization.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_forward_score_batch_shadow_characterization_rhemac \
  --workload rheMac10_nonchrom_top8_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --workers 4,6 \
  --max-requests 1000,10000,50000,100000 \
  --gpu-ids 0,1 \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --extend-threads 6 \
  --force

timeout 2400s python3 scripts/benchmark_fasim_forward_score_batch_shadow_characterization.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_forward_score_batch_shadow_characterization_hg38_w4 \
  --workload hg38_chr21_chr22_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa:H19.fa:1 \
  --workers 4 \
  --max-requests 1000,10000,50000,100000 \
  --gpu-ids 0,1 \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --extend-threads 6 \
  --force
```

Each worker process used one visible GPU via the sharded runner. The parent
environment removed inherited `FASIM_CUDA_DEVICES`.

Active env:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1
FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW_MAX_REQUESTS=<sample cap>
```

The max-request cap is per Fasim process/shard. Aggregated processed requests
can therefore exceed the cap when a workload has multiple shard processes.

## Correctness

All 12 rows were clean:

```text
digest clean: 12/12
preAlign CUDA fallbacks: 0
batch score mismatches: 0
batch endpoint mismatches: 0
```

## Results

Seconds are sharded telemetry sums across worker/shard processes, not wall
time. `processed` is the number of requests actually sent to the batch GPU
shadow. Requests beyond the per-process cap are counted as unsupported.

`GPU / observed CPU` divides batch GPU total by CPU forward score/end seconds
for all observed requests. This is optimistic when unsupported requests exist.
`GPU / processed CPU est` estimates the CPU reference for only processed
requests by multiplying observed CPU reference by the processed fraction.

| workload | workers | cap | observed requests | processed | unsupported | CPU ref s | GPU total s | kernel s | GPU / observed CPU | GPU / processed CPU est |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 1,000 | 147,270 | 8,000 | 139,270 | 5.339 | 0.424 | 0.399 | 0.079 | 1.461 |
| rheMac10 top8 | 4 | 10,000 | 147,270 | 72,979 | 74,291 | 7.217 | 3.137 | 3.049 | 0.435 | 0.877 |
| rheMac10 top8 | 4 | 50,000 | 147,270 | 147,270 | 0 | 9.609 | 8.150 | 8.068 | 0.848 | 0.848 |
| rheMac10 top8 | 4 | 100,000 | 147,270 | 147,270 | 0 | 9.891 | 6.914 | 6.841 | 0.699 | 0.699 |
| rheMac10 top8 | 6 | 1,000 | 147,270 | 8,000 | 139,270 | 6.211 | 0.577 | 0.485 | 0.093 | 1.711 |
| rheMac10 top8 | 6 | 10,000 | 147,270 | 72,979 | 74,291 | 8.120 | 4.435 | 4.350 | 0.546 | 1.102 |
| rheMac10 top8 | 6 | 50,000 | 147,270 | 147,270 | 0 | 11.053 | 10.051 | 9.961 | 0.909 | 0.909 |
| rheMac10 top8 | 6 | 100,000 | 147,270 | 147,270 | 0 | 10.709 | 10.223 | 10.142 | 0.955 | 0.955 |
| hg38 chr21+chr22 | 4 | 1,000 | 1,420,427 | 2,000 | 1,418,427 | 45.351 | 0.105 | 0.103 | 0.002 | 1.641 |
| hg38 chr21+chr22 | 4 | 10,000 | 1,420,427 | 20,000 | 1,400,427 | 43.962 | 0.804 | 0.797 | 0.018 | 1.299 |
| hg38 chr21+chr22 | 4 | 50,000 | 1,420,427 | 100,000 | 1,320,427 | 46.580 | 3.768 | 3.732 | 0.081 | 1.149 |
| hg38 chr21+chr22 | 4 | 100,000 | 1,420,427 | 200,000 | 1,220,427 | 49.905 | 7.539 | 7.469 | 0.151 | 1.073 |

Raw outputs:

```text
.tmp/fasim_forward_score_batch_shadow_characterization_rhemac/summary.tsv
.tmp/fasim_forward_score_batch_shadow_characterization_hg38_w4/summary.tsv
```

## Interpretation

The result improves on #157 smoke in one important way: larger batches do make
the naive batch shadow competitive with CPU forward score/end on the smaller
same-query multi-target workload. On `rheMac10_nonchrom_top8_H19`, rows that
processed all requests had:

```text
GPU total / CPU reference:
  workers=4: 0.70-0.85x
  workers=6: 0.91-0.95x
```

That means batching was the right diagnostic shape. It does not mean this code
is ready for a real path. The shadow still copies requests, allocates/frees GPU
buffers per snapshot group, and runs after the CPU authority path has already
done the work.

The larger `hg38_chr21_chr22_H19` workload shows the practical limit of the
current scaffold. At the 100,000 cap, only about 14% of requests were processed
and the estimated processed-only comparison was still slower:

```text
GPU total / processed CPU estimate:
  hg38 chr21+chr22 workers=4 cap=100000: 1.07x
```

Running the current copy-retaining scaffold at full hg38 request count is not a
good performance experiment: it would retain too many copied query/reference
buffers until telemetry snapshot. That is exactly why #157 keeps the path
default-off and diagnostic-only.

The kernel time dominates rows with large processed counts. Pack/H2D/D2H/unpack
are visible but not the primary cost in these local runs.

## Decision

Do not promote `FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1` to a real opt-in.

The GPU score line has a narrow remaining path:

```text
score-only bridge design
contiguous/device-resident request layout
no endpoint authority
no CIGAR/traceback
CPU output remains authority until digest-clean bridge proof exists
```

If that bridge is not worth building, stop the GPU forward-score path and keep
the current practical runtime on:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
process-level sharding
```

Any further GPU score work must first remove the current scaffold limitations:

```text
avoid retaining copied requests for full-workload capture
reuse or prebuild contiguous buffers
avoid per-snapshot allocation churn
use a credible parallel DP design rather than one-thread-per-request DP
prove score_mismatches = 0
keep endpoint/CIGAR/output out of the path
```
