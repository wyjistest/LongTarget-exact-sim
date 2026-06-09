# Long-query exact-column scoreInfo shadow

## Scope

`FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW=1` is a default-off
diagnostic probe for long-query scoreInfo/preAlign work.

It runs before the normal preAlign CUDA topK path and never uses GPU scoreInfo
for candidate state, endpoint, CIGAR, traceback, output, or digest. CPU Fasim
output remains the authority.

## Why it exists

The earlier MALAT1 long-query probe did not prove that full-query exact-column
scoreInfo CUDA was slow or wrong. The preAlign CUDA topK launch failed first, so
the exact-column scoreInfo path never launched:

```text
[fasim.cuda.topk] error requests=432 error=invalid argument
exact_scoreinfo_gpu_batches = 0
exact_column_batches = 0
```

This shadow bypasses that topK precondition and directly calls the
column-pruned scoreInfo CUDA helper against the prepared full-query profile.

## Current MALAT1 first8 result

The direct shadow preserves output digest, but the full-query column kernel
itself still cannot launch for the 8,708 bp MALAT1 query:

```text
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_requested=1
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_active=0
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_query_len=8708
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_batches=1
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_tasks=0
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_scoreinfo_mismatches=0
benchmark.fasim_long_query_exact_column_scoreinfo_shadow_error=invalid argument
```

Interpretation:

```text
topK bypass:
  works as a diagnostic shape

full-query exact-column CUDA for MALAT1-length query:
  launch no-go in current kernel/resource shape

output authority:
  unchanged CPU fallback
```

## Shared-memory opt-in result

With `FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW_SMEM_OPTIN=1`, the
MALAT1 first8 shape crosses the default dynamic shared-memory limit and fits the
device opt-in limit:

```text
query_len = 8708
required_smem = 52416
default_smem_limit = 49152
optin_smem_limit = 101376
resource_fit = 1
smem_optin_active = 1
gpu_tasks = 432
scoreinfo_mismatches = 1
output digest unchanged
decision = smem_optin_scoreinfo_no_go
```

Interpretation:

```text
shared-memory opt-in:
  proves the kernel can launch for this MALAT1 resource shape

scoreInfo equivalence:
  not clean

real path:
  no
```

It is checked by:

```bash
make check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin
```

## Decision

This closes one ambiguity in the long-query path: the current full-query
exact-column scoreInfo CUDA kernel is not a ready replacement for MALAT1/NEAT1
long-query scoreInfo/preAlign. The non-opt-in path cannot launch, and the
shared-memory opt-in diagnostic path launches but is not scoreInfo-equivalent.
Further long-query GPU work needs a different execution design, not another
wrapper around the same full-query column kernel.
