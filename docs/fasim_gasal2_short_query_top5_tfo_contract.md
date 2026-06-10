# Fasim GASAL2 Short-Query Top5 TFO Contract

This checkpoint narrows the GASAL2 result to the TFO contract that is actually
clean today.

```text
short-query/H19 strongest top5 TFO:
  scoped go

full TFOsorted output:
  not equivalent

full TFO sequence set:
  not equivalent

aligner.Align replacement:
  not claimed
```

## Contract

The checked contract is:

```text
For short-query/H19 workloads, the top5 TFO sequence list is identical between
CPU Fasim authority and the GASAL2 candidate for these rankings:
  score
  MeanStability
  Nt(bp)
```

This is intentionally narrower than full output equivalence. CPU/Fasim remains
the authority outside the top5 TFO artifact contract.

## Full chr22 Result

Fresh full chr22 `tfosorted` characterization:

```text
target = .tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa
rna = H19.fa
rule = 0

CPU baseline wall    = 2278.208116s
GASAL2 candidate wall = 101.127585s
speedup              = 22.528058x

baseline_rows  = 388501
candidate_rows = 388820
full_rows_equal = false
full_missing_rows = 4186
full_extra_rows = 4502

tfo_equal = false
tfo_missing = 1475
tfo_extra = 1593

gapless_tfo_equal = false
gapless_tfo_missing = 97
gapless_tfo_extra = 103

top5_tfo_score_equal = true
top5_tfo_stability_equal = true
top5_tfo_nt_score_equal = true

score_prepass_first_requests = 6910419
score_prepass_remaining_requests = 7981209
score_prepass_pruned_remaining_requests = 3781035
traceback_requests = 6910419
query_reuse_saved_bytes = 41872856488
traceback_query_reuse_saved_bytes = 19430981864
```

This result is a strong short-query top5 TFO milestone. It is not a full
`TFOsorted` or full TFO sequence-set milestone.

## GPU Utilization

The full chr22 candidate-only utilization run reused the CPU baseline output and
measured only the GASAL2 candidate phase:

```text
candidate_wall_seconds = 101.456345
gasal2_total_seconds = 19.3525
gasal2_wait_seconds = 16.5974
gasal2_score_wait_seconds = 8.54136
gasal2_traceback_wait_seconds = 8.05605

gpu0_samples = 102
gpu0_util_avg_all = 30.872549%
gpu0_active_samples = 61
gpu0_util_avg_active = 51.623%
gpu0_util_max = 86%
gpu0_high_samples_>=80 = 10

gpu1_samples = 102
gpu1_util_avg_all = 0%
```

The candidate can hit high GPU utilization peaks, but it does not run the GPU
for the full 101s wall time. CPU-side selection, conversion, and output still
consume a large fraction of candidate wall time.

## 2Mb Smoke Gate

The lightweight smoke gate uses the chr22 10m-12m slice:

```text
baseline_wall_seconds = 59.851994
candidate_wall_seconds = 3.928390
speedup_vs_baseline = 15.235757

full_rows_equal = false
tfo_equal = false
gapless_tfo_equal = false

top5_tfo_score_equal = true
top5_tfo_stability_equal = true
top5_tfo_nt_score_equal = true
```

Run it with:

```bash
make check-fasim-gasal2-short-query-top5-tfo-contract
```

Full chr22 characterization can be rerun with:

```bash
WORK=.tmp/characterize_fasim_gasal2_short_query_tfo_contract_chr22_full \
TARGET=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
RNA=H19.fa \
PRUNE_MAX_PER_TASK=256 \
GASAL2_STREAMS=3 \
GASAL2_BATCH=20000 \
bash scripts/characterize_fasim_gasal2_short_query_tfo_contract.sh
```

## Decision

```text
short-query/H19 top5 TFO accelerator:
  go as default-off scoped milestone

full TFO output:
  no-go

full aligner.Align replacement:
  no-go

next product shape:
  explicit top5/strongest-TFO artifact, not complete Fasim output
```
