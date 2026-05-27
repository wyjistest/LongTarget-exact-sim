# Fasim Score-Only GPU Bridge Real-Workload Characterization

This note characterizes the default-off score-only GPU bridge shadow from the
current clean Fasim base on real workloads.

## Scope

This is a docs/script/result checkpoint only:

- No real GPU aligner path is added.
- GPU score/end results are not used for output.
- GPU endpoint is not used for output.
- No GPU CIGAR or traceback is added.
- No scoring, output, threshold, non-overlap, scheduler, merge, chunking,
  default, or in-process multi-GPU behavior is changed.

CPU `aligner.Align()` remains authoritative for score, endpoint, traceback,
CIGAR, candidate state, output, and digest.

## Command

The matrix was run after the score-only bridge prototype:

```bash
timeout 1200s python3 scripts/benchmark_fasim_score_bridge_characterization.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_score_bridge_characterization_rhemac \
  --workload rheMac10_nonchrom_top8_H19:/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --workers 4,6 \
  --max-requests 1000,10000,50000,100000 \
  --gpu-ids 0,1 \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --extend-threads 6 \
  --force

timeout 2400s python3 scripts/benchmark_fasim_score_bridge_characterization.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_score_bridge_characterization_hg38_w4 \
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
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW_MAX_REQUESTS=<sample cap>
```

The max-request cap is per Fasim process/shard. Aggregated processed requests
can therefore exceed the cap when a workload has multiple shard processes.

## Correctness

All characterized rows were clean:

```text
digest clean: 12/12
preAlign CUDA fallbacks: 0
bridge score mismatches: 0
bridge endpoint mismatches: 0
```

## Results

Seconds are sharded telemetry sums across worker/shard processes, not wall
time. `processed` is the number of requests sent to the score bridge GPU
shadow. Requests beyond the per-process cap are counted as unsupported.

`GPU / observed CPU` divides bridge GPU total by CPU forward score/end seconds
for all observed requests. This is optimistic when unsupported requests exist.
`GPU / processed CPU est` estimates the CPU reference for only processed
requests by multiplying observed CPU reference by the processed fraction.

| workload | workers | cap | observed requests | processed | unsupported | groups | descriptor bytes | target bytes | CPU ref s | GPU total s | kernel s | GPU / observed CPU | GPU / processed CPU est |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rheMac10 top8 | 4 | 1,000 | 147,270 | 8,000 | 139,270 | 8 | 256,000 | 557,847 | 5.152 | 0.518 | 0.506 | 0.101 | 1.851 |
| rheMac10 top8 | 4 | 10,000 | 147,270 | 72,979 | 74,291 | 8 | 2,335,328 | 5,024,712 | 4.454 | 3.220 | 3.206 | 0.723 | 1.459 |
| rheMac10 top8 | 4 | 50,000 | 147,270 | 147,270 | 0 | 8 | 4,712,640 | 10,077,807 | 3.437 | 7.272 | 7.242 | 2.116 | 2.116 |
| rheMac10 top8 | 4 | 100,000 | 147,270 | 147,270 | 0 | 8 | 4,712,640 | 10,077,807 | 3.441 | 7.079 | 7.047 | 2.057 | 2.057 |
| rheMac10 top8 | 6 | 1,000 | 147,270 | 8,000 | 139,270 | 8 | 256,000 | 555,647 | 5.748 | 0.414 | 0.413 | 0.072 | 1.327 |
| rheMac10 top8 | 6 | 10,000 | 147,270 | 72,979 | 74,291 | 8 | 2,335,328 | 5,025,625 | 4.945 | 4.187 | 4.129 | 0.847 | 1.709 |
| rheMac10 top8 | 6 | 50,000 | 147,270 | 147,270 | 0 | 8 | 4,712,640 | 10,077,807 | 4.025 | 11.602 | 11.551 | 2.882 | 2.882 |
| rheMac10 top8 | 6 | 100,000 | 147,270 | 147,270 | 0 | 8 | 4,712,640 | 10,077,807 | 3.840 | 11.771 | 11.708 | 3.065 | 3.065 |
| hg38 chr21+chr22 | 4 | 1,000 | 1,420,427 | 2,000 | 1,418,427 | 2 | 64,000 | 137,156 | 45.781 | 0.097 | 0.096 | 0.002 | 1.505 |
| hg38 chr21+chr22 | 4 | 10,000 | 1,420,427 | 20,000 | 1,400,427 | 2 | 640,000 | 1,342,320 | 45.837 | 0.783 | 0.782 | 0.017 | 1.213 |
| hg38 chr21+chr22 | 4 | 50,000 | 1,420,427 | 100,000 | 1,320,427 | 2 | 3,200,000 | 6,712,425 | 45.714 | 3.733 | 3.730 | 0.082 | 1.160 |
| hg38 chr21+chr22 | 4 | 100,000 | 1,420,427 | 200,000 | 1,220,427 | 2 | 6,400,000 | 13,493,284 | 45.681 | 7.468 | 7.464 | 0.163 | 1.161 |

Raw outputs:

```text
.tmp/fasim_score_bridge_characterization_rhemac/summary.tsv
.tmp/fasim_score_bridge_characterization_hg38_w4/summary.tsv
```

## Interpretation

This characterization is the decision gate for the low-copy descriptor/query
reuse bridge prototype. It should not be read as a real GPU aligner result.

The correctness contract stayed clean, but performance is a no-go for the
current implementation. Rows that process all rheMac10 top8 requests are slower
than CPU forward score/end:

```text
rheMac10 top8 workers=4: 2.06-2.12x CPU reference
rheMac10 top8 workers=6: 2.88-3.07x CPU reference
```

The hg38 chr21+chr22 capped rows also do not win on the processed-only estimate:

```text
cap 1,000:   1.51x CPU reference estimate
cap 10,000:  1.21x CPU reference estimate
cap 50,000:  1.16x CPU reference estimate
cap 100,000: 1.16x CPU reference estimate
```

The low-copy bridge reduced descriptor/query/target retention compared with the
older copied-request snapshot scaffold, but the conservative batch DP kernel now
dominates total time. H2D/D2H/unpack are small in these rows; this is not a
copy-only failure.

Continue the GPU score line only if a future implementation changes the DP
execution design enough that meaningful real-workload rows show:

```text
score_mismatches = 0
digest unchanged
bridge total < CPU forward score/end
pack/H2D/kernel/D2H/unpack costs are clearly itemized
retained descriptor/query/target bytes stay bounded
```

With the current score bridge implementation, stop the GPU score path:

```text
kernel time dominates without a credible better DP design
bridge total remains slower than CPU forward score/end
score-only GPU output still has no endpoint/CIGAR/output authority
```

Do not use this result to justify:

```text
GPU endpoint authority
GPU CIGAR
GPU traceback
GPU full extension replacement
Accelign or Parasail real output authority
single-process multi-GPU policy
historical final speed-stack env claims
```
