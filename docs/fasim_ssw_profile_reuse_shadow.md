# Fasim SSW Profile Reuse Shadow

This telemetry-only checkpoint evaluates whether repeated SSW query profile
construction inside `aligner.Align` is reusable for identical query/scoring
keys. The runtime path still builds and destroys the legacy SSW profile on every
call; the shadow cache is used only for sampled side comparisons.

## Scope

```text
real output changed: no
CPU aligner.Align skipped: no
real SSW profile cache: no
scoring/threshold/non-overlap changed: no
GPU AUTO policy changed: no
SIM-close/recovery changed: no
validation relaxed: no
```

## How It Works

`FASIM_SSW_PROFILE_REUSE_SHADOW=1` records the translated query and scoring
matrix key used by `ssw_init(...)`. The first occurrence of a key builds a
shadow cached profile from copied query/matrix buffers. Later calls with the
same key are counted as reuse opportunities and, up to
`FASIM_SSW_PROFILE_REUSE_SHADOW_MAX_COMPARE`, are re-run through `ssw_align(...)`
with the cached profile for side comparison.

The authoritative path remains:

```text
translate query/ref
ssw_init(...)
ssw_align(...)
ConvertAlignment(...)
init_destroy(...)
```

The shadow compares:

```text
score
ref/query endpoints
CIGAR string/vector
digest-relevant alignment fields
```

## Fixture Result

The small hg38 soft-mask fixture passes the new check:

```text
Fasim SSW profile reuse shadow checks passed
```

Required metrics:

```text
fasim_ssw_profile_reuse_shadow_enabled
fasim_ssw_profile_build_calls
fasim_ssw_profile_unique_keys
fasim_ssw_profile_reused_possible_calls
fasim_ssw_profile_build_seconds
fasim_ssw_profile_est_reuse_saved_seconds
fasim_ssw_profile_key_query_length
fasim_ssw_profile_key_scoring_hash
fasim_ssw_profile_key_orientation
fasim_ssw_profile_shadow_compared
fasim_ssw_profile_shadow_score_mismatches
fasim_ssw_profile_shadow_endpoint_mismatches
fasim_ssw_profile_shadow_cigar_mismatches
fasim_ssw_profile_shadow_output_digest_mismatches
```

## Large Workload Command

Use the existing CPU-internals benchmark to produce the full report, now with an
additional `auto_profile_reuse_shadow` mode:

```bash
python3 scripts/benchmark_fasim_aligner_align_cpu_internals.py \
  --cuda-bin ./fasim_longtarget_cuda \
  --dna "$FASIM_GPU_DP_COLUMN_AUTO_HG38_DNA" \
  --rna "$FASIM_GPU_DP_COLUMN_AUTO_HG38_RNA" \
  --label "${FASIM_GPU_DP_COLUMN_AUTO_HG38_LABEL:-hg38_chr21_H19}" \
  --repeat "${FASIM_GPU_DP_COLUMN_AUTO_HG38_REPEAT:-1}" \
  --require-profile \
  --check \
  --output docs/fasim_aligner_align_cpu_internals.md
```

For small fixtures, add `--force-auto` to lower AUTO activation thresholds.

## Decision Rule

If the large workload shows high reuse opportunity and all shadow mismatches are
zero, the next PR can evaluate a default-off real SSW profile cache with
validation/fallback. If profile keys are not repetitive, estimated savings are
small, or any score/endpoint/CIGAR mismatch appears, this line should remain a
telemetry checkpoint only.
