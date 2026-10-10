# GPU exact cross-task batching v1

Date: 2026-10-10. Independent branch `codex/gpu-exact-batch-20261010`, based
on the frozen repair commit `9960a87b34f3dabe8c3b5cbaad766b361e2d3c28`.

The repaired GPU consumer previously submitted one endpoint batch per task:
195,936 submissions for 12,594,048 attempts on the full `w010` fixture. This
candidate collects attempts from consecutive tasks with the same query before
calling the existing endpoint API. At a 4,096-attempt limit the fixture uses
3,135 endpoint batches, with exactly the same 195,936 tasks, 12,594,048 forward
attempts, 3,148,512 selected CPU continuations, and 8,291 output rows.

## Scope and contract

The CUDA recurrence, CPU SSW, ordered threshold/best/last selection, triplex
conversion, filtering and output publication are unchanged. The attempt
planner was extracted without changing its arithmetic: its existing float
loop still generates four rounds. No attempt pruning, query segmentation,
sequence-residency change, profile-cache enablement, CPU parallelization,
asynchronous pipeline, score-equality gate, or CIGAR hardening is included.

`FASIM_GPU_EXACT_BATCH_V1=1` requires `FASIM_GPU_EXACT_REPAIR_V1=1` and is off
by default. Without the new flag the same binary follows the per-task path.
The frozen repair binary, production runtimes, and original acceptance state
are separate and unchanged.

The implementation is in `fasim/gpu_exact_batch.h`. Each bounded window owns
the descriptors and returned endpoint arrays for consecutive complete tasks.
The query, target strings and scoreInfo vectors remain owned by the existing
streaming flush until the window is consumed. A task's identity, source
objects, numeric path, local/global coordinates, and request count are checked
before continuation. Group IDs are task-local; selection runs separately for
each task after scattering endpoint results back in original order.

Windows normally contain at most the configured attempt limit. A single task
larger than that limit is kept intact for consumption, while the existing
endpoint bridge splits its scoring calls. Windows also stop at the existing
streaming-flush boundary. Empty tasks are preserved, and partial final batches
are processed. A window's temporary descriptor storage is bounded by the
larger of the configured limit and one existing task, plus one-task lookahead;
it does not grow with the entire input. The existing rectangular target
packing and its resource requirements remain in use.

GPU/API failures or mismatched prepared results fail the task and do not
publish a completed TFOsorted file. There is no silent per-task fallback.

## Use

Build in this independent worktree with its copied/pinned GASAL2 dependency:

```bash
make build-fasim-gpu-exact-batch \
  CUDA_CXXFLAGS='-O2 -std=c++11 --generate-code=arch=compute_89,code=sm_89'
make build-gpu-exact-repair-test \
  CUDA_CXXFLAGS='-O2 -std=c++11 --generate-code=arch=compute_89,code=sm_89'

CUDA_VISIBLE_DEVICES=0 \
FASIM_GPU_EXACT_REPAIR_V1=1 \
FASIM_GPU_EXACT_BATCH_V1=1 \
FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH=4096 \
FASIM_OUTPUT_MODE=tfosorted \
.tmp/fasim_gpu_exact_batch_v1 -f1 target.fa -f2 query.fa -r 0 -O new_output_dir
```

This is a CUDA development executable, not a CentOS 6/OpenMP deployment
package. The repair's supported output modes and shared-memory limits still
apply. The batching parameter has the existing bridge default of 4,096 and
maximum of 32,768; an explicit batch flag is needed to aggregate tasks.

## Validation and evidence

Evidence directory:
`/data/wenyujianData/linjieData/longtarget_runs/gasal2_exact_batch_20261010_v1`.

- `components01`: all 973 endpoint/numeric-path/CPU-continuation cases pass,
  plus cross-task ragged batches, empty tasks, repeated task-local group IDs,
  byte/word mixtures, context rejection and batch limits
  1/7/16/1,024/4,096/8,192.
- `smoke01`: the 5 kb prefix and original affected locus agree byte-for-byte
  with the frozen CPU at batch off/7/1,024/4,096/8,192.
- `panel01`: H19, three other short queries and natural 4,006/8,181/12,397 nt
  queries agree byte-for-byte. Long-query target views are 20 kb, not full
  production targets. Independent CPU min-score/scoreInfo checks are enabled.
- `full01`: full 20,000,001 nt target, 492 nt query; all 8,291 rows match the
  frozen CPU SHA-256
  `8e6842d3967d86827ba22f1e0cd3aee17f1340f70f022be9ed537c47ba72d974`.
  All per-task semantic report fields match `repair/full03`, not just totals.
- `host_sanitizers01`: host planner and all 973 native/continuation cases pass
  ASan, UBSan and leak detection. This host-only executable does not claim to
  sanitize CUDA-host staging/scattering.
- `gpu_memcheck01`: the same component executable, including the new
  cross-task mapping cases, passes compute-sanitizer with zero errors.
- `faults01`: missing repair mode, no GPU, insufficient scoreInfo capacity and
  unsupported output all exit nonzero without publishing completed output.
- `cpu_compat_build.log`: the CPU/stub build compiles with the shared headers.

`scripts/check_gpu_exact_batch_v1.py` reuses frozen development inputs and
checks their identities. It supports `smoke`, `panel`, `full`, `faults`,
`sweep` and `benchmark` stages. Every invocation requires a new output
directory. Timing stages disable the per-task consumer report and CPU oracle;
the AB/BA control is the frozen repair executable, not the serial CPU.

Example:

```bash
python3 scripts/check_gpu_exact_batch_v1.py \
  --binary .tmp/fasim_gpu_exact_batch_v1 --stage full --work /new/full
python3 scripts/check_gpu_exact_batch_v1.py \
  --binary .tmp/fasim_gpu_exact_batch_v1 --stage sweep --work /new/sweep
python3 scripts/check_gpu_exact_batch_v1.py \
  --binary .tmp/fasim_gpu_exact_batch_v1 --stage benchmark --batch 4096 \
  --work /new/benchmark
```

## Telemetry

`benchmark.fasim_gpu_exact_batch_v1.*` records window/task/attempt/batch counts,
peak window sizes, planning time, scoring time, GPU time and transfers.
Existing consumer report semantics are retained. Shared scoring time and
endpoint batch counts are charged once to the first nonempty task of a window;
request/continuation/selection counts stay task-local. These per-task times
are accounting allocations, not independent task latencies.

The instrumented full run took 84.49 s. Attempt scoring took 23.43 s, including
1.75 s of GPU kernel timing, 0.73 s H2D and 0.11 s D2H; CPU continuation took
28.83 s, conversion 12.19 s, and min-score/scoreInfo 4.88 s. Kernel/transfer
times are nested in scoring time. These diagnostics are separate from the
uninstrumented comparison; host build/sanitizer checks and other users' CPU
jobs were present. Timing runs start after our build/sanitizer checks finish.
Another process also holds memory on the tested GPU. The timing plans record
both GPU utilization and process snapshots; this is not an exclusive-device
benchmark.

This remains a development candidate. Reused repair fixtures do not satisfy
fresh paper acceptance, and comparisons with multi-threaded OpenMP production
queues require their own matched-resource benchmark. The rare canonical
score-decrease/reselection path is inherited unchanged and has no newly
observed natural trigger in these fixtures.
