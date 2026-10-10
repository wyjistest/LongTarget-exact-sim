# Exact GPU consumer: host preparation and CPU query reuse

Date: 2026-10-10. Development branch `codex/gpu-exact-host-20261010`.
Base: cross-task batching commit `61174008f7065976ae385e49ad3fe5dd8bb73b12`.
Evidence directory:
`/data/wenyujianData/linjieData/longtarget_runs/gasal2_exact_host_20261010_v1`.

Two independent changes were implemented and measured in sequence:

1. `6c71cd5f0e5f1a8f51b0f735981febd1a9bc46a2` resolves the exact-alphabet
   configuration once per endpoint API call. Previously the optimized executable
   called `getenv()` inside every nucleotide iteration of target packing.
   The same encoder and kernel mode are used throughout the call.
2. `fc04eb4f7c88d7d9755ec351c0206b72691fbf68` adds an explicit
   `ForwardQueryContext`, prepared once per streaming flush and reused by CPU
   continuations. It owns the source query, encoded query, scoring matrix and
   byte/word full-query profiles. The consumer checks query identity; the API
   checks the preparing aligner and its matrix generation. Clearing/rebuilding
   the aligner invalidates old contexts, and failed preparation clears old state.

The second change avoids repeated query encoding, profile allocation and hash-key
construction. It does not enable the existing profile-cache switch. Target
substrings/encoding, reverse-prefix profiles and DP/traceback workspaces remain
per alignment. Context storage is bounded by one query and its profiles per flush.

Both paths share the original endpoint-to-SSW continuation and result conversion.
The eager four rounds, ordered threshold/best/last selection and score-decrease
reselection remain unchanged. There is no CPU worker pool, async GPU pipeline,
new CIGAR score-equality requirement or zero-length-op rejection in this change.

## Runtime and build

`FASIM_GPU_EXACT_QUERY_REUSE_V1` defaults off and requires both existing exact
repair and cross-task batching flags. A missing prerequisite fails the run.
The configuration hoist is present in both new development binaries.

```bash
make build-fasim-gpu-exact-host \
  CUDA_CXXFLAGS='-O2 -std=c++11 --generate-code=arch=compute_89,code=sm_89'

CUDA_VISIBLE_DEVICES=0 \
FASIM_GPU_EXACT_REPAIR_V1=1 \
FASIM_GPU_EXACT_BATCH_V1=1 \
FASIM_GPU_EXACT_QUERY_REUSE_V1=1 \
FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH=4096 \
FASIM_OUTPUT_MODE=tfosorted \
.tmp/fasim_gpu_exact_host_v1 -f1 target.fa -f2 query.fa -r 0 -O new_output_dir
```

The worktree contains the same copied/pinned GASAL2 dependency used by the frozen
batching build. These executables target local Linux/CUDA sm_89; this is not an
OpenMP/CentOS deployment package.

## Correctness evidence

- `config_components01` and `reuse_components01`: 973 cases pass, including
  endpoint/numeric-path comparison, CPU continuation and cross-task mapping.
  The reuse test additionally compares every Alignment field and encoded/text
  CIGAR with the original continuation API for each case.
- Lifecycle tests exercise repeated byte/word reuse, a nonterminated target
  view, mutation of the original query buffer, foreign aligner rejection,
  Clear/ReBuild invalidation, query replacement and invalid preparation.
- `config_panel01`, `reuse_panel01`, `reuse_off_panel01`: all nine cases in
  each panel match frozen CPU outputs and per-task semantic counters. Includes
  H19, the repaired affected locus and natural 4,006/8,181/12,397 nt queries.
  Long-query targets in this panel are 20 kb views.
- `config_full01`, `reuse_full_profile01`: full 492 nt query x 20,000,001 nt
  target matches all 8,291 rows and the frozen complete-file SHA-256:
  `8e6842d3967d86827ba22f1e0cd3aee17f1340f70f022be9ed537c47ba72d974`.
  Both retain 195,936 tasks, 12,594,048 forward attempts, 3,148,512 CPU
  continuations and 3,135 endpoint batches; no fallback/failure/reselection.
- `reuse_host_sanitizers01`: ASan/UBSan with leak detection pass on the host
  lifecycle/planner tests and all 973 native/continuation cases. This host-only
  sanitizer executable does not exercise CUDA staging or the full application.
- `reuse_faults01`: missing batch flag, missing repair flag, no GPU and scoreInfo
  capacity failure all return nonzero without publishing completed output.
- `reuse_build02.log`: the GPU application, component test and CPU/stub
  compatibility executable compile successfully.

The CUDA recurrence and scalar/SIMD/traceback implementation are byte-unchanged:

```text
cuda/prealign_cuda.cu
a8b89a4b1fa312df1b23483b2cfbc86d60498fdb2fdc757e1e586e2d21c50fe6
fasim/sswNew.cpp
5c89012dd8a595ea03bddba490a547785a71ff8279262141982082acbee23c1f
```

## End-to-end AB/BA

Each comparison uses the full 20 Mb fixture, in control/candidate/candidate/control
order, with detailed consumer reporting and the in-process CPU oracle disabled.
All eight timed outputs match the frozen CPU digest.

| Change | Control repetitions (s) | Candidate repetitions (s) | Medians (s) | Additional speedup | Wall reduction |
| --- | --- | --- | --- | --- | --- |
| Resolve configuration once | 75.6463, 72.9947 | 56.7988, 56.8092 | 74.3205 -> 56.8040 | 1.30837x | 23.5688% |
| Add prepared CPU query | 56.7476, 56.7346 | 45.5189, 45.4772 | 56.7411 -> 45.4981 | 1.24711x | 19.8146% |

Evidence: `config_benchmark01/performance.json` and
`reuse_benchmark01/performance.json`. The first control is the frozen batching
release; the second control is the frozen configuration-only binary. These are
two separate paired comparisons, not one directly measured combined speedup.
Earlier 83-86 s baseline/profile figures are from another measurement period and
are not the denominator for these ratios. The server's other CPU/GPU workload
changed during this session; the two arms of each comparison share its own
measurement window. No compilation or our sanitizer runs overlap either AB/BA.

## Profiling and limits

The first change's full diagnostic scoring envelope is 2.93367 s, including
1.72197 s of kernels and 0.295279 s of transfers. The previous frozen batch
diagnostic recorded 23.428 s. This attribution is separate from the AB/BA
end-to-end measurement below.

The final diagnostic takes 47.6332 s and prepares 49 CPU query contexts for
3,148,512 continuations. Total preparation time is 0.000299211 s. Exclusive
SSW bridge time is 1.56527 s, reverse alignment (including reverse-profile
construction) 9.25369 s, and banded traceback 4.72193 s. Consumer continuation
timing is 15.6413 s, and conversion 11.3525 s. These timers overlap at different
levels; they must not all be added together. The earlier assessment's exclusive
bridge time was 14.4925 s, but that diagnostic was from a different time period.

`scripts/check_gpu_exact_host_v1.py` records input/binary digests, machine/GPU
snapshots, environment, output identities and append-only receipts. Benchmark
mode disables the consumer TSV and in-process CPU oracle and runs AB/BA using
the specified frozen baseline. These are reused development fixtures, not new
paper acceptance or a matched-resource OpenMP comparison. Performance is measured
on one complete workload, with two repetitions per arm on a shared server.
The tests introduce no natural trigger of the existing rare reselection branch.

Released binaries are in the evidence directory's `release/` subdirectory:

```text
fasim_gpu_exact_host_config_v1
16eb0a6f4b44641ab00d96fd10731cafe6c427e65f95ad6945c34a79e2833b31
fasim_gpu_exact_host_v1
bb750ac4fb6504c850fc84c35ac4b47eac3623f87c1916197c3ba9f28a98df5f
```

Each implementation step has its own patch and performance receipts. Production
runtimes, the original dirty worktree and the previous frozen releases are intact.
