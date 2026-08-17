# Exact long-query hybrid runtime guards v1

## Status

```text
base_checkpoint = 500b0104b5a07407f5749b8ea5271916d47267fd
implementation_commit = 0b52f80a0d6fed1ac71fd9faf0a572a7181078ea
runtime_guard_implementation = complete
clean_fixture_gate = pass
formal_promoter_panel_modified = false
production_authorized = false
bioinformatics_v2_state_modified = false
```

This epoch adds fail-closed operating-envelope checks to the exact long-query
hybrid prototype. It does not modify the stateful scoreInfo kernels, endpoint
kernel recurrence, attempt ordering, host consumer, selected CPU continuation,
output schema, promoter mapping, clustering, or ranking.

The active promoter formal panel remains on
`exact-long-query-hybrid-promoter-panel-v1` at `dc534608b11d26d6248f6fa52768144ccb6d4ae4`.
It was still active when this evidence was frozen. None of its source files,
runtime binaries, scheduler state, or partial outputs were changed by this
epoch.

## Two-stage preflight

The replacement mode now performs two checks.

1. Query-level preflight runs after reading the query and before any long-query
   GPU allocation or launch. It verifies the exact scoring contract, forced
   `WORD16` continuation path, CUDA availability, selected device, and dynamic
   shared-memory demand. It also covers workloads that later produce no
   scoreInfo rows.
2. Attempt-level preflight runs before preparing the cached query profile. It
   validates every target view, records the maximum target-subview length, and
   checks the conservative `int16_t` score bound before endpoint work begins.

The frozen contract is:

```text
match = 5
mismatch_penalty = 4
gap_open = 16
gap_extend = 4
continuation_numeric_path = WORD16
maximum_possible_score = 5 * min(query_length, max_target_subview_length)
maximum_possible_score <= INT16_MAX
required_dynamic_smem = 3 * ceil(query_length / 32) * 32 * sizeof(int16_t)
required_dynamic_smem <= actual_device_optin_limit
```

The scoring values are read from the actual SSW `Aligner`; they are not merely
repeated constants at the call site. A compile-time assertion also binds the
guard's `WORD16` value to the SSW continuation ABI.

## Runtime descriptor

The query and attempt APIs return a `FasimLongQueryRuntimeDescriptor` with:

```text
query_length
maximum_target_subview_length
maximum_target_subview_length_known
query_length_limit
target_subview_length_limit
segment_length
maximum_possible_score
required_dynamic_smem_bytes
default_dynamic_smem_limit_bytes
optin_dynamic_smem_limit_bytes
scoring contract and numeric path
device_index
query/target/scoring/numeric/resource fit flags
supported
decision
```

Unsupported configurations return a stable reason and do not fall back to CPU
alignment. Reasons cover CUDA not built, invalid or unrepresentable lengths,
malformed target views, scoring mismatch, numeric-path mismatch, `int16_t`
overflow, unsupported device, and shared-memory overflow.

## Clean evidence

The implementation was committed before the final build. A clean
`0b52f80a0d6fed1ac71fd9faf0a572a7181078ea` tree produced binary SHA-256:

```text
8f1efa8fbc706d5a7604e66f6311bd301a323635f9124217859b73c5160c060a
```

On device 0, the runtime query reported:

```text
default shared memory = 49,152 bytes
opt-in shared memory = 101,376 bytes
resource-formula fit point = 16,896 nt
next point = rejected
```

The 25,498 nt LINC02055 query failed at query preflight with:

```text
dynamic_shared_memory_limit_exceeded:
required=153024:optin_limit=101376
```

The guarded LINC01501 regression retained the frozen lite-output digest:

```text
6f9e95ab6209d2ea053dfdef4872b6fd5616b07a9be8950976786c0a1215c226
```

Its execution coverage was:

```text
GPU tasks = 10,368 / 10,368
scoreInfo groups = 245,422
GPU endpoint attempts = 981,688 / 981,688
CPU all-attempt oracle = 0
CPU reference attempts = 0
selected continuation failures = 0
fallbacks = 0
```

The observed `171.39 s` wall time is resource-contaminated diagnostic timing.
It is excluded from all speedup claims because the OpenMP production worker
and formal CPU baselines were active concurrently.

## Evidence boundary

This is a runtime-guard engineering checkpoint, not a production promotion.
The existing six-query full-concat formal panel remains authoritative for the
real promoter scientific contract. Promoter component, cross-component, and
reference-N fixtures stay in that validation epoch and were not copied into
this preflight-only change.

If the formal promoter panel passes, evidence inheritance for this guard binary
still requires `runtime_path_allowlist.tsv` plus at least one guarded full-concat
paired regression for each of the six queries. CUDA kernel code, GPU descriptor
layout, defaults, scheduling, mapping, clustering, and ranking are outside the
allowlist; a change to any of them invalidates this limited inheritance route.
