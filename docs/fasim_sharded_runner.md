# Fasim Sharded Runner

This document describes the first process-level sharding step for Fasim. The
goal is to run existing Fasim binaries independently on target FASTA records and
merge record outputs deterministically, without changing Fasim runtime behavior.

## Scope

The first version is intentionally narrow:

- Shards are FASTA records, typically chromosomes or contigs.
- No internal chromosome chunking is implemented.
- No chunk overlap is inferred or applied.
- No in-process multi-GPU runtime is added.
- No Fasim scoring, threshold, non-overlap, output, GPU AUTO, SSW, SIM-close, or
  recovery behavior is changed.

This keeps correctness gated on a simple check:

```text
single multi-contig run canonical digest == sharded merged canonical digest
```

## Runner

Use `scripts/fasim_sharded_runner.py` with an existing Fasim binary:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_x86 \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --validate-single
```

The runner writes:

- `shard_plan.json`: contig-level shard metadata.
- `shard_outputs/<shard_id>/`: per-shard Fasim outputs.
- `merged/merged-TFOsorted.lite` or `merged/merged-TFOsorted`: canonical merged
  output.
- `single_output/`: optional single-run output when `--validate-single` is set.
- `report.json`: shard telemetry, Fasim benchmark sums, digests, and validation
  result.

## Complete-Record Grouping

`--group-target-records N` is a default-off runner option for tiny-region
workloads with many small FASTA records. It groups up to `N` complete target
FASTA records into one worker shard FASTA. It does not split records, infer
overlap, rewrite original FASTA headers, or change Fasim runtime semantics.

The default remains one target FASTA record per shard. With grouping enabled,
`shard_plan.json`, `report.json`, and `run_manifest.json` record:

```text
target_record_count
group_target_records
grouped_shard_count
group_member_count
group_member_headers
group_member_names
group_member_ranges
group_member_input_digests
```

Grouping metadata is included in the shard plan and `run_config_digest`, so
`--resume` will not reuse stale shard outputs when the grouping size or member
set changes. Correctness should still be checked with `--validate-single` on
small fixtures or with an authority digest for larger characterization runs.

## Environment

The runner does not default-enable Fasim runtime options. Pass worker
environment explicitly. For the current repo-local `fasim_longtarget_cuda`,
the active Fasim throughput knobs are:

```text
FASIM_ENABLE_PREALIGN_CUDA
FASIM_OUTPUT_MODE
FASIM_EXTEND_THREADS
FASIM_CUDA_DEVICE
FASIM_CUDA_DEVICES
FASIM_PREALIGN_CUDA_MAX_TASKS
FASIM_PREALIGN_CUDA_TOPK
FASIM_PREALIGN_PEAK_SUPPRESS_BP
FASIM_TRANSFERSTRING_TABLE
FASIM_TRANSFERSTRING_TABLE_VALIDATE
FASIM_SSW_PROFILE_CACHE
FASIM_SSW_PROFILE_CACHE_VALIDATE
FASIM_GPU_DP_COLUMN_AUTO
FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS
FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS
FASIM_EXACT_COLUMN_EXTEND_BATCH
FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE
FASIM_SSW_PROFILE_CONTEXT
FASIM_SSW_PROFILE_CONTEXT_VALIDATE
FASIM_SSW_AVX2
FASIM_SSW_AVX2_MODE
FASIM_VERBOSE
FASIM_WRITE_TFOSORTED_LITE
```

`FASIM_TRANSFERSTRING_TABLE=1` is a default-off CPU-side table-driven
`transferString` path. `FASIM_TRANSFERSTRING_TABLE_VALIDATE=1` compares that
path against the legacy converter and falls back to legacy on mismatch.
`FASIM_SSW_PROFILE_CACHE=1` is a default-off CPU-side SSW query-profile cache.
`FASIM_SSW_PROFILE_CACHE_VALIDATE=1` rebuilds the legacy profile for comparison
and falls back to legacy output on mismatch.
`FASIM_GPU_DP_COLUMN_AUTO=1` is default-off and size-gated by
`FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS` and
`FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS`; below the thresholds it stays on the
default path. `FASIM_EXACT_COLUMN_EXTEND_BATCH=1` is default-off and is used
with the GPU DP/AUTO path, with `FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1`
available for comparison fallback. `FASIM_SSW_PROFILE_CONTEXT=1` layers on top
of `FASIM_SSW_PROFILE_CACHE=1`; it is not an independent cache path.
`FASIM_SSW_AVX2=1` requires a Fasim binary built with
`FASIM_SIMD_FLAGS=-mavx2`; the default `-msse2` build exposes the env but cannot
activate the AVX2 kernels.

Enable Fasim's CUDA preAlign path explicitly when using the CUDA binary:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_PREALIGN_CUDA_TOPK=64 \
  --env FASIM_VERBOSE=0
```

For process-level worker scheduling, pass explicit worker options. The runner
still launches ordinary Fasim subprocesses; it does not add an in-process
multi-GPU runtime.

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --workers 2 \
  --gpu-ids 0,1 \
  --cpu-core-ranges 0-7,8-15 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_PREALIGN_CUDA_TOPK=64 \
  --env FASIM_VERBOSE=0
```

With `--gpu-ids`, each worker is intentionally made a single-visible-GPU
process: the runner sets `CUDA_VISIBLE_DEVICES=<assigned physical GPU>`, sets
`FASIM_CUDA_DEVICE=0`, and strips inherited `FASIM_CUDA_DEVICES` from the
worker environment. This keeps the final-speed-stack path on the supported
single-process/single-GPU contract while using multiple GPUs through
process-level sharding. CPU core ranges are optional and use `taskset`; provide
one range per worker when used. When estimated DP cells are unavailable, shard
assignment falls back to target sequence length. `CUDA_VISIBLE_DEVICES` only
selects visible devices; it does not enable Fasim CUDA by itself. Use
`FASIM_ENABLE_PREALIGN_CUDA=1` for the Fasim preAlign CUDA path.

For topK-only lite artifact runs, the runner can ask each shard to emit only
its in-process topK lite rows. GASAL2 presets require a GASAL2-enabled Fasim
binary:

```bash
make build-fasim-gasal2
```

The runner checks the binary for the positive
`benchmark.fasim_gasal2_built=1` marker before accepting GASAL2
scoreInfo/preAlign runner options. Non-GASAL2 binaries fail before shard
execution; use `make check-fasim-gasal2-top5-binary-guard` for the focused
guard.

For every completed shard, `report.json` also parses numeric `benchmark.*`
stderr fields into `fasim_benchmark_sums` and records the contributing shard
count in `fasim_benchmark_shards`. GASAL2/top5 runs should audit these report
fields directly for active path and fallback status, for example:

```text
fasim_top5_gasal2_gpu_scoreinfo_requested
fasim_top5_gasal2_gpu_scoreinfo_active
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled
fasim_gasal2_requests
fasim_gasal2_score_requests
fasim_gasal2_traceback_requests
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches
fasim_gasal2_fallbacks
fasim_gasal2_length_guard_fallbacks
```

The runner also records `result_contract` in both `report.json` and
`run_manifest.json`. The formal GASAL2 column-pruned preset reports
`gasal2_top5_column_pruned_scoreinfo_artifact_v1`; lower-level GASAL2 top5
diagnostics report `gasal2_top5_scoreinfo_artifact_v1`; non-GASAL2
`--topk-summary-only` runs report `topk_summary_artifact_v1`; ordinary merged
output runs report `merged_output_v1`.

`topk_summary.tsv` is self-describing: its first line is
`# result_contract=<contract>`, followed by deterministic top5 row-key payload
rows. `topk_rows.tsv` carries the same mode/rank ordering with full lite-output
rows. `topk-TFOsorted.lite` is a deduplicated lite-output file containing the
selected top rows with the normal lite header. The `*_digest` fields cover full
artifacts, including contract metadata where present. The `*_payload_digest`
fields cover only payload rows and are the digests to compare across CPU/GASAL2
contracts when checking top5 artifact equivalence.

The formal `--gasal2-top5-column-pruned-scoreinfo` preset fail-closes on this
telemetry. Every shard must report requested/active GASAL2 scoreInfo, active
exact scoreInfo GPU, non-zero GASAL2 score/traceback requests, non-zero exact
scoreInfo GPU tasks, and zero exact-scoreInfo/GASAL2/length-guard fallback or
overflow. Long-query workloads that are blocked by the current GASAL2 query guard
therefore fail the formal preset instead of silently producing a CPU-fallback
top5 artifact. The runner checks RNA query length before shard execution using
`FASIM_ALIGN_GASAL2_MAX_QUERY_LEN`, which defaults to `2812`. The formal preset
rejects values above `2812`, non-integers, and non-positive values before shard
execution. `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN` remains an allowed diagnostic
override, but the formal preset rejects values above `2812`, non-integers, and
non-positive values; set larger or disabled query guards only for lower-level
diagnostics, not for the formal preset.
For auditability, the formal preset records
`gasal2_top5_query_preflight_supported`,
`gasal2_top5_query_preflight_query_len`, and
`gasal2_top5_query_preflight_max_query_len` in `report.json` and
`run_manifest.json`, along with the preflight error field. Formal resume also
requires verified query preflight and reruns instead of reusing older manifests
that do not carry it. Formal resume requires the same verified query-preflight
length bounds before reusing shards. The formal artifact integrity checks
require manifest query-preflight fields to match the report. The formal artifact
integrity checks also require query length to be within the recorded max query
length. The formal artifact integrity checks require managed preset
`env_overrides`, including `FASIM_PREALIGN_CUDA_MAX_TASKS=16384`, to match the
formal preset. The formal artifact integrity checks also require manifest
`env_snapshot` to carry the same managed preset values. The formal artifact
integrity checks recompute the active-path requirement from
`fasim_benchmark_sums`: active per-shard GASAL2/exact-scoreInfo flags, positive
GASAL2 request and exact-scoreInfo task counts, and zero fallback/overflow.
The formal artifact integrity checks also require topK-lite scoreInfo-rank
observe telemetry to be enabled, non-empty, and free of unknown rows.
The formal GASAL2 top5 artifact path is not full lite-output equivalence and is
not an `aligner.Align()` replacement.

The GASAL2 top5 recommended runtime is documented in
`docs/fasim_gasal2_top5_recommended_runtime.md` and checked by:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

That recommended runtime is a default-off opt-in for the short-query/H19 top5
contract. The full objective remains open.

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_gasal2 \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded_topk \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers 2 \
  --gpu-ids 0,1 \
  --env FASIM_VERBOSE=0
```

For the same reviewed surface behind a small wrapper,
`run_fasim_gasal2_topk_lite.sh` defaults to the formal
`--gasal2-top5-column-pruned-scoreinfo` runner preset and writes
`topk-TFOsorted.lite`, `top5.lite`, `topk_summary.tsv`, `topk_rows.tsv`,
`report.json`, and `summary.tsv` under `$OUT`. `LEGACY_DIRECT=1` keeps the
older direct-env wrapper path available for investigation only. The wrapper
also accepts `GROUP_TARGET_RECORDS=N` and forwards it to
`--group-target-records N` for tiny-region complete-record grouping. The wrapper
also accepts `AUTO_CPU_CORE_RANGES=1`, `CPU_POOL=<range>`, and
`CPU_CORES_PER_WORKER=N` and forwards them to the runner's CPU-affinity options.
For resumable formal runs, use `RESUME=1 FORCE=0`; the wrapper forwards that
state to `--resume` and rejects `RESUME=1 FORCE=1` before invoking the runner.
The wrapper contract is checked by `check-fasim-gasal2-topk-lite-wrapper-contract`.

`--shard-output-topk-lite K` is default-off and is only valid with
`--output-mode lite`, `--topk-summary-only`, and the same `K` as
`--topk-summary`. The runner records the setting in `run_config_digest` and
passes `FASIM_OUTPUT_TOPK_LITE=K` to each worker, so resume will not silently
reuse full-lite shards for a topK-lite run or vice versa. This is a topK
artifact mode, not a full merged-output mode. Manifest resume validates these
raw topK shard outputs with their file digest and rebuilds the topK summary
from the raw shard rows. When `--topk-summary` is active, the runner also writes
`topk_summary.tsv` and records `topk_summary_output` plus
`topk_summary_digest` and `topk_summary_payload_digest` in `report.json` and
`run_manifest.json`. It also writes `topk_rows.tsv` and records
`topk_rows_output`, `topk_rows_digest`, and `topk_rows_payload_digest`. The
summary TSV is the deterministic row-key artifact; the rows TSV is the full-row
mode/rank artifact. The runner also writes `topk-TFOsorted.lite` and records
`topk_lite_output`, `topk_lite_digest`, and `topk_lite_records`; that file is
the directly consumable deduplicated topK lite artifact. Full digests include
the contract metadata line where present, while payload digests are the
cross-contract comparable values. artifact integrity checks require the
`topk_summary` report object to match the topK summary and rows artifacts.
Merged full-lite output remains disabled for `--topk-summary-only`.

`--gasal2-top5-scoreinfo-prune-max-per-task N` is a separate default-off
compute-prune preset for the GASAL2 scoreInfo/preAlign top5 path. It sets:

```text
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
FASIM_TOP5_GASAL2_PHASE_TIMING=1
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=N
```

The preset requires `--output-mode lite`, `--topk-summary 5`, and
`--topk-summary-only`. It is intentionally top5-only: scoreInfo/attempt pruning
can change the full lite row set, so the runner does not present it as full
merged-output equivalence. The setting is included in `run_config_digest`, and
the runner rejects conflicting `--env` values for the managed GASAL2 preset
keys. It also rejects long-query segmented diagnostic env keys such as
`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW`; those probes are outside the
formal top5 artifact contract. Formal artifact integrity checks reject the same
segmented diagnostic env keys if they appear in `report.json` or
`run_manifest.json`. They also reject unsupported formal env extras such as
`FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST`; only the managed preset env and
checked diagnostic overrides are accepted. If `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN`
is present, it must match the recorded
`gasal2_top5_query_preflight_max_query_len`.

`--exact-scoreinfo-gpu-max-per-task N` is an additional default-off option for
the same GASAL2/top5 preset. It sets:

```text
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=N
```

It requires `--gasal2-top5-scoreinfo-prune-max-per-task`, and the runner rejects
conflicting `--env` values for the managed exact-scoreInfo GPU keys. This option
controls the per-task compact scoreInfo output capacity, not the top5 ranking
contract. Too small can overflow and fall back; too large increases D2H/staging
cost. The setting is recorded in `report.json`, included in `run_config_digest`,
and manifest resume will rerun shards when the value changes.

The formal gate for the current GASAL2/top5 artifact path is:

```bash
make check-fasim-gasal2-top5-formal-gate
```

The recorded chr21+chr22 milestone result artifact has a separate local
verification gate:

```bash
make check-fasim-gasal2-top5-scoreinfo-milestone-result
```

That gate is intentionally not part of the formal gate because it requires the
saved chr21+chr22 characterization artifact under `.tmp`.

The composed current-state milestone gate is:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

It ties together the recorded chr21+chr22 result, MEG3 grouped result, wrapper
result, top5 output contract, long-query boundary, and long-query no-last
scaling artifact. Its conclusion is intentionally scoped:

```text
short-query/H19 top5 scoreInfo/preAlign: milestone go
MEG3 grouped top5 wrapper: milestone go
long-query current best is marginal
long-query MALAT1/NEAT1: no real path
full replacement goal remains open
```

It starts with a Makefile hygiene guard that checks the formal-gate dependency
list, `.PHONY` coverage, and the ignored root `fasim_longtarget_gasal2` build
artifact. It then covers the milestone doc gate, the top5 output-contract gate,
the long-query boundary gate, the GASAL2-enabled binary guard, default-off
guard, env/telemetry-key guard, sharded preset runner/resume check, bounded
preset-vs-CPU/full top5 matrix check, lowercase FASTA input normalization, and
the MEG3/MALAT1/NEAT1 examples boundary gate. The output contract is documented
in `docs/fasim_gasal2_top5_output_contract.md`; the long-query no-go boundary is
documented in `docs/fasim_gasal2_long_query_boundary.md`. Use the focused gates
below when debugging one part of that contract:

The MALAT1 scoped long-query trust path has a separate default-off experimental
runner control surface:

```text
--long-query-streaming-scoreinfo-gpu-trust
result_contract = long_query_streaming_scoreinfo_gpu_trust_experimental_v1
default-off
experimental
external digest gate
```

It packages the current `MALAT1 streaming scoreInfo trust path: scoped go`
environment stack and records the `NEAT1 streaming scoreInfo trust path:
performance no-go` boundary. `Broad scoreInfo/preAlign replacement: not
proven` remains the current decision. The option does not use GPU endpoint,
CIGAR, traceback, or GASAL2 long-query traceback authority. It must be validated
with an external baseline/candidate digest gate.

The runner option has a MALAT1 bounded characterization through first64:

```text
record_limit  tasks  realpath_used  fallback  GPU groups  runner speedup
8             1824   1824           0         31272       0.914539x
16            4416   4416           0         77852       0.957250x
32            8160   8160           0         144841      0.934600x
64            18096  18096          0         319280      0.953067x
```

Those rows are digest-clean and remove CPU `preAlign` from the candidate
scoreInfo path, but the runner-level wall time is still slower than baseline on
the bounded samples. Treat the option as an experimental digest-gated control
surface, not a recommended general runtime.

MALAT1 first64 worker sweep:

```text
workers  tasks  realpath_used  fallback  GPU total  runner speedup
1        18096  18096          0         44.999s    0.956003x
2        18096  18096          0         62.025s    0.912482x
4        18096  18096          0         79.532s    0.843978x
```

The digest contract remains clean, but adding workers does not make the current
trust path faster than the baseline. Use the worker sweep to characterize
contention; do not treat worker count as a production enablement knob for this
experimental path.

Complete-record grouping gives a different result on MALAT1 first64:

```text
group_target_records  shards  runner speedup
null                  64      0.952645x
2                     32      0.989676x
4                     16      1.011415x
8                     8       1.022417x
16                    4       1.028119x
32                    2       1.028873x
```

All rows are digest-clean and keep `realpath_used = tasks`, fallback=0, and CPU
`preAlign`/compare at zero in the candidate. The gain is small, but it shows
that complete-record grouping is the right way to test setup amortization for
this path. It does not make the trust option a broad replacement.

Group32 scaling:

```text
record_limit  shards  tasks  runner speedup
64            2       18096  1.029346x
128           4       40128  1.041244x
256           8       80640  1.040806x
```

Use this as a MALAT1-like experimental path only: `--group-target-records 32`
with `--long-query-streaming-scoreinfo-gpu-trust` is digest-gated and modestly
positive on the checked samples, but it is not a default runtime policy.

Full MALAT1 group32 result:

```text
shards = 21
tasks = 200,400
realpath_used = 200,400
fallback = 0
gpu_scoreinfo_groups = 3,561,123
baseline runner wall = 2634.969799s
candidate runner wall = 2541.655441s
runner speedup = 1.036714x
```

Full MALAT1 no-probe two-contract runtime gate:

```text
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full
schema = lite
rows = 98,713
digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
baseline_wall_seconds = 2611.940621
candidate_wall_seconds = 2514.945686
candidate_vs_baseline = 1.038567x
tasks = 200,400
two_contract_used = 200,400
realpath_used = 200,400
gpu_scoreinfo_groups = 3,561,123
probe_positive_numeric_keys = 0
```

For MALAT1-like workloads, the current experimental profile is:

```bash
python3 scripts/fasim_sharded_runner.py \
  --long-query-streaming-scoreinfo-gpu-trust-group32
```

`--long-query-streaming-scoreinfo-gpu-trust-group32` is default-off and is
equivalent to `--long-query-streaming-scoreinfo-gpu-trust --group-target-records
32`. It records:

```text
result_contract = long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_group32_experimental_v1
```

Keep it behind an external digest gate. This profile is not validated for
NEAT1-like long-query shapes and is not a broad scoreInfo/preAlign replacement.
The group32 scaling and full-MALAT1 characterization wrappers now run this
preset contract directly, so their summaries should report the group32 contract
and `malat1_like_group32_experimental_v1` profile.

The two-contract bridge trust prototype is a narrower follow-up preset:

```bash
python3 scripts/fasim_sharded_runner.py \
  --long-query-streaming-scoreinfo-gpu-two-contract-trust
```

It records:

```text
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1
```

Internally it sets:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1
```

Then it feeds two-contract GPU scoreInfo into the existing CPU extend/output
path. It is default-off, external-digest-gated, and not a default replacement
path.

For the checked MALAT1-like group32 shape, the grouped two-contract preset is:

```bash
python3 scripts/fasim_sharded_runner.py \
  --long-query-streaming-scoreinfo-gpu-two-contract-trust-group32
```

It is equivalent to `--long-query-streaming-scoreinfo-gpu-two-contract-trust
--group-target-records 32` and records:

```text
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_group32_experimental_v1
```

Keep this profile default-off and behind an external digest gate. It packages
the current MALAT1-like grouped two-contract evidence; it does not validate
NEAT1-like shapes and does not give GPU endpoint, CIGAR, traceback, or output
authority.

For the same MALAT1-like group32 shape without audited replay/attempt probes,
use the no-probe runtime preset:

```bash
python3 scripts/fasim_sharded_runner.py \
  --long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32
```

It is equivalent to
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime
--group-target-records 32` and records:

```text
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1
```

Internally it sets only the two-contract bridge trust env, hot GPU minScore,
legacy-byte shared scoreInfo, and `FASIM_ALIGN_GASAL2=1`. It does not set any
`FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_*PROBE` env. Keep it default-off and
externally digest-gated; it is the clean runtime wall preset for the scoped
MALAT1-like two-contract bridge, not a broad scoreInfo/preAlign replacement.

For a fail-closed audited run of that two-contract grouped preset, use:

```bash
scripts/run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh \
  --fasim-bin .tmp/fasim_longtarget_gasal2_direct \
  --target target.fa \
  --rna rna.fa \
  --work-dir audit_work \
  --workers 1 \
  --replay-probe-max-tasks 1
```

The wrapper runs a CPU-authority baseline with `--group-target-records 32` and
the two-contract group32 candidate, then accepts the candidate only if the
external digest gate and two-contract coverage checks pass:

```text
audited_status = accepted
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_group32_experimental_v1
```

If the baseline and candidate merged digests differ, it exits non-zero with
`digest gate failed` and does not publish an accepted output. This wrapper does
not give GPU endpoint, CIGAR, traceback, or output authority.
`--replay-probe-max-tasks N` defaults to `1`; `N=0` means all tasks in each
flush. It is passed through to
`--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks` and only
widens the diagnostic flush-level selected-attempt replay surface.

When the replay probe is active, the accepted summary also records:

```text
candidate_realpath_extend_flush_segmented_replay_probe_requested
candidate_realpath_extend_flush_segmented_replay_probe_active
candidate_realpath_extend_flush_segmented_replay_probe_tasks
candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts
candidate_realpath_extend_flush_segmented_replay_probe_align_attempts
candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches
candidate_realpath_extend_flush_segmented_replay_probe_seconds
candidate_realpath_extend_flush_segmented_replay_probe_fallbacks
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_seconds
candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_active
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds
candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks
```

The real MALAT1 smoke gate for the audited wrapper is:

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256
```

For a fail-closed audited run, use:

```bash
scripts/run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh \
  --fasim-bin .tmp/fasim_longtarget_gasal2_direct \
  --target target.fa \
  --rna rna.fa \
  --work-dir audit_work \
  --workers 1 \
  --replay-probe-max-tasks 1
```

The wrapper runs a CPU-authority baseline with `--group-target-records 32` and
the group32 GASAL2 candidate, then accepts the candidate only if the external
digest gate and scoreInfo coverage checks pass:

```text
audited_status = accepted
result_contract = long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_group32_experimental_v1
```

If the baseline and candidate merged digests differ, it exits non-zero with
`digest gate failed` and does not publish an accepted output.
`--replay-probe-max-tasks N` defaults to `1`; `0` means all tasks in each
flush. It only expands the diagnostic flush-level selected/full/oracle replay
coverage. It is passed through to
`--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks`; it does
not give GPU endpoint, CIGAR, traceback, or output authority.
`--resume` requires an existing accepted `audit_summary.json`, forwards resume
to both underlying runner invocations, and records:

```text
audited_resume = true
resumed_shards
baseline_resumed_shards_count
candidate_resumed_shards_count
baseline_runner_wall_seconds
candidate_runner_wall_seconds
candidate_vs_baseline
candidate_gpu_scoreinfo_total_seconds
candidate_gpu_scoreinfo_call_seconds
candidate_gpu_scoreinfo_kernel_seconds
candidate_non_gpu_wall_seconds
candidate_gpu_scoreinfo_wall_fraction
candidate_gpu_scoreinfo_call_fraction
candidate_realpath_extend_seconds
candidate_realpath_extend_calls
candidate_realpath_extend_fraction
candidate_realpath_extend_scoreinfo_groups
candidate_realpath_extend_align_attempts
candidate_realpath_extend_substr_seconds
candidate_realpath_extend_align_seconds
candidate_realpath_extend_align_fraction
candidate_realpath_extend_convert_seconds
candidate_realpath_extend_sort_seconds
candidate_realpath_extend_filter_seconds
candidate_realpath_extend_attempt_probe_requested
candidate_realpath_extend_attempt_probe_active
candidate_realpath_extend_attempt_probe_calls
candidate_realpath_extend_attempt_probe_attempts
candidate_realpath_extend_attempt_probe_selected_attempts
candidate_realpath_extend_attempt_probe_seconds
candidate_realpath_extend_attempt_probe_fallbacks
candidate_realpath_extend_segmented_attempt_probe_requested
candidate_realpath_extend_segmented_attempt_probe_active
candidate_realpath_extend_segmented_attempt_probe_segments
candidate_realpath_extend_segmented_attempt_probe_calls
candidate_realpath_extend_segmented_attempt_probe_attempts
candidate_realpath_extend_segmented_attempt_probe_selected_attempts
candidate_realpath_extend_segmented_attempt_probe_seconds
candidate_realpath_extend_segmented_attempt_probe_fallbacks
candidate_realpath_extend_flush_segmented_attempt_probe_requested
candidate_realpath_extend_flush_segmented_attempt_probe_active
candidate_realpath_extend_flush_segmented_attempt_probe_flushes
candidate_realpath_extend_flush_segmented_attempt_probe_segments
candidate_realpath_extend_flush_segmented_attempt_probe_calls
candidate_realpath_extend_flush_segmented_attempt_probe_attempts
candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts
candidate_realpath_extend_flush_segmented_attempt_probe_seconds
candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks
candidate_realpath_extend_flush_segmented_replay_probe_requested
candidate_realpath_extend_flush_segmented_replay_probe_active
candidate_realpath_extend_flush_segmented_replay_probe_tasks
candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts
candidate_realpath_extend_flush_segmented_replay_probe_align_attempts
candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches
candidate_realpath_extend_flush_segmented_replay_probe_seconds
candidate_realpath_extend_flush_segmented_replay_probe_fallbacks
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_task
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key
candidate_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance
candidate_realpath_extend_flush_full_replay_probe_requested
candidate_realpath_extend_flush_full_replay_probe_active
candidate_realpath_extend_flush_full_replay_probe_tasks
candidate_realpath_extend_flush_full_replay_probe_align_attempts
candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches
candidate_realpath_extend_flush_full_replay_probe_fallbacks
candidate_realpath_extend_flush_full_replay_probe_seconds
candidate_realpath_extend_flush_oracle_replay_probe_requested
candidate_realpath_extend_flush_oracle_replay_probe_active
candidate_realpath_extend_flush_oracle_replay_probe_tasks
candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches
candidate_realpath_extend_flush_oracle_replay_probe_seconds
candidate_post_scoreinfo_unattributed_seconds
candidate_post_scoreinfo_unattributed_fraction
```

The `candidate_realpath_extend_*` subphase fields break down CPU
`fastSIM_extend_from_scoreinfo()` consumption of trusted GPU scoreInfo. They are
diagnostic only; the accepted output is still chosen by the external digest gate.
The `candidate_realpath_extend_attempt_probe_*` fields are a default-off GASAL2
score-only/select probe over the same extend-attempt window shape. The probe does
not feed triplex output, endpoint, CIGAR, candidate state, or digest authority.
The `candidate_realpath_extend_segmented_attempt_probe_*` fields run the same
diagnostic through bounded long-query segments so the short-query GASAL2
`MAX_QUERY_LEN=2812` guard remains intact.
The `candidate_realpath_extend_flush_segmented_attempt_probe_*` fields batch the
same diagnostic at the trusted-scoreInfo flush level to avoid per-scoreInfo
segment launches.
The `candidate_realpath_extend_flush_segmented_replay_probe_*` fields replay a
small capped subset of those selected attempts through CPU `aligner.Align()` and
compare the resulting triplex list against the CPU-authoritative extend output.
The `first_mismatch_*` fields describe the first replay-vs-legacy triplex
difference when one exists. They remain diagnostic only and do not feed output.
The `candidate_realpath_extend_flush_full_replay_probe_*` fields replay all
scoreInfo attempts for the same capped task subset through the legacy per-group
emit/rank/filter shape. They separate task-level replay mechanics from
GASAL2-selected candidate coverage and also remain output-passive.
The `candidate_realpath_extend_flush_oracle_replay_probe_*` fields call the
legacy `fastSIM_extend_from_scoreinfo()` helper a second time for the same
capped task subset. They test whether replay comparison can be clean when the
exact legacy helper is the probe implementation.

Use `--force` to discard prior audit work; `--resume --force` is rejected.

The bounded matrix aggregate reports `active_path_runs` so top5-clean rows must
also prove active GASAL2/exact-scoreInfo coverage.

```bash
make check-fasim-gasal2-top5-binary-guard
make check-fasim-gasal2-top5-scoreinfo-milestone-result
make check-fasim-gasal2-top5-output-contract
make check-fasim-gasal2-topk-lite-wrapper-contract
make check-fasim-gasal2-long-query-boundary
make check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow
make check-fasim-gasal2-long-query-segmented-replay-no-last
make check-fasim-sharded-gasal2-top5-prune-runner
make check-fasim-gasal2-top5-lowercase-input
make check-fasim-exact-scoreinfo-gpu-max-per-task-sweep
make check-fasim-exact-scoreinfo-gpu-pruned-output
make characterize-fasim-exact-scoreinfo-gpu-column-pruned-output
make check-fasim-exact-scoreinfo-gpu-column-pruned-output
make characterize-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix
make check-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix
make characterize-fasim-gasal2-column-pruned-preset-top5-matrix
make check-fasim-gasal2-column-pruned-preset-top5-matrix
make characterize-fasim-gasal2-prealign-max-tasks-probe
make check-fasim-gasal2-prealign-max-tasks-probe
make check-fasim-gasal2-prealign-max-tasks-chr21-chr22-result
make check-fasim-gasal2-single-pass-topn
make check-fasim-long-query-streaming-scoreinfo-trust-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-trust-runner-real
make check-fasim-gasal2-formal-makefile-gate
make check-fasim-gasal2-formal-preset-examples
make check-fasim-exact-scoreinfo-gpu-examples-gate
```

`check-fasim-gasal2-prealign-max-tasks-probe` is not part of the formal gate.
It compares the current formal preset against equivalent lower-level runs with
explicit `FASIM_PREALIGN_CUDA_MAX_TASKS` values and requires top5 summary,
topK-rows, and topK-lite artifacts to remain payload-clean.
The focused probe now includes `4096`, `8192`, and `32768`; `16384` is the
formal reference setting and `32768` remains a larger lower-level comparison.

The examples gate keeps the recommendation scoped: `512` is clean for the
short-query MEG3 shape, while MALAT1/NEAT1 remain blocked by the current GASAL2
query-length guard and do not exercise exact scoreInfo GPU. The examples gate
reports `scoreinfo_gasal2_active` so guarded long-query CPU fallback rows cannot
be mistaken for active GASAL2/exact-scoreInfo shards.

`--gasal2-top5-column-pruned-scoreinfo` is the default-off preset for the
current column-pruned one-DP GASAL2 top5 artifact path. It expands to the
checked settings:

```text
--gasal2-top5-scoreinfo-prune-max-per-task 64
--exact-scoreinfo-gpu-max-per-task 512
--exact-scoreinfo-gpu-pruned-output
--exact-scoreinfo-gpu-column-pruned-output
--topk-summary 5
--topk-summary-only
--shard-output-topk-lite 5
```

The runner sets those topK artifact options automatically when the preset is
used. It still requires lite output mode and rejects conflicting explicit topK
settings. It is not a full lite-output mode and does not claim exact legacy
scoreInfo equivalence; the checked contract is the top5 summary artifact only.
The formal `--gasal2-top5-column-pruned-scoreinfo` preset additionally sets
these managed worker env values:

```text
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
FASIM_TOP5_GASAL2_PHASE_TIMING=1
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64
FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1
FASIM_PREALIGN_CUDA_MAX_TASKS=16384
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1
FASIM_OUTPUT_TOPK_LITE=5
```

`FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1` is managed by the
formal preset to record the final topK-lite rows' scoreInfo-rank distribution
without changing pruning, output, or digest.
`FASIM_PREALIGN_CUDA_MAX_TASKS=16384` is managed by the formal preset to reduce
exact-scoreInfo GPU flush count. Manual `--env FASIM_PREALIGN_CUDA_MAX_TASKS=...`
remains rejected by the formal preset; use the max-tasks probe for lower-level
characterization.
On the current chr21+chr22/H19 top5 artifact path, a lower-level probe kept
top5 summary, topK-rows, and topK-lite payloads clean for `16384` and `32768`;
`16384` reduced exact-scoreInfo GPU batches from `96` to `49` and improved wall
time from `59.103306s` to `57.506064s`. The recorded chr21+chr22 promotion
evidence is checked by
`make check-fasim-gasal2-prealign-max-tasks-chr21-chr22-result`.
After promotion, the refreshed chr21+chr22 formal matrix remains
`top5_artifact_go`: CPU worker wall sum `4565.987188s`, formal worker wall sum
`113.810705s`, speedup `40.119136x`, exact-scoreInfo GPU batches `49`, and
fallback/overflow `0 / 0`.
The setting is recorded in `report.json`, included
in `run_config_digest`, and resume reruns shards when it changes.
The preset also requires the active-path telemetry described above; use the
lower-level diagnostic switches rather than this preset when characterizing
query-guarded or fallback-heavy workloads.
`FASIM_ALIGN_GASAL2_BATCH` remains an allowed diagnostic override, but the
formal preset rejects values above `30000`, non-integers, and non-positive
values before shard execution. `40000` is outside the checked resource boundary
and must stay a lower-level characterization setting.
`FASIM_ALIGN_GASAL2_STREAMS` remains an allowed diagnostic override, but the
formal preset rejects values above `16`, non-integers, and non-positive values
before shard execution.
When this column-pruned path is active, the Fasim worker skips the unused
legacy-score GPU input encoding by default. `encode_dual_seconds=0` is expected;
`encode_prealign_seconds` records the single remaining preAlign target encoding
pass. Explicit `FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1` can still request the
legacy-score GPU diagnostic path.

The focused preset gate is:

```bash
make check-fasim-gasal2-column-pruned-preset-top5-matrix
```

It compares the preset against a CPU/full top5 summary artifact for score,
stability, and nt-score. That is stricter than comparing against an
exact-pruned-output diagnostic baseline, but it still validates only the top5
summary artifact. It does not validate full lite output equivalence.

The sharded utilization helper can run the same formal preset switch:

```bash
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

Use this form for preset GPU utilization and phase-breakdown reports. The
helper rejects combining `GASAL2_TOP5_COLUMN_PRUNED_PRESET=1` with manual
scoreInfo-prune, single-pass topN, nt-span pruning, `PREALIGN_CUDA_MAX_TASKS`,
or exact-column scoreInfo settings, so the report corresponds to the actual
`--gasal2-top5-column-pruned-scoreinfo` runner option.
The helper's shard TSV includes transfer/src-transform call and byte counters;
use them to evaluate future host-side transform-cache or fused-construction
work without changing the top5 artifact contract.

`--exact-scoreinfo-gpu-pruned-output` is an additional default-off experimental
switch for the same top5 GASAL2 scoreInfo/preAlign path. It requires both
`--gasal2-top5-scoreinfo-prune-max-per-task N` and
`--exact-scoreinfo-gpu-max-per-task M`, sets
`FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1`, and asks the exact scoreInfo
GPU compact path to emit only the same per-task top-N scoreInfo groups that the
CPU prune would keep. It is not a different prune rule and it is not a full
Fasim-output mode. The setting is recorded in `report.json`, included in
`run_config_digest`, and resume reruns shards when it changes.

`--gasal2-single-pass-topn` is a default-off diagnostic switch for the same top5
artifact path. It requires `--gasal2-top5-scoreinfo-prune-max-per-task N`, sets
`FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1`, and forces the existing CUDA topK
column-maxima pass to feed GASAL2 directly instead of running exact scoreInfo
GPU. This avoids the legacy max-score plus exact scoreInfo double-pass, but it
is only a bounded topN candidate path, not exact scoreInfo equivalence. The
setting is recorded in `report.json`, included in `run_config_digest`, and
resume reruns shards when it changes.

`--exact-scoreinfo-gpu-column-pruned-output` is a narrower diagnostic switch for
the same exact-scoreInfo/pruned-output path. It requires
`--exact-scoreinfo-gpu-pruned-output`, sets
`FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1`, and asks one
exact-column GPU pass to write column maxima and compact the pruned scoreInfo
groups directly. It is not exact legacy scoreInfo, not a full Fasim output mode,
and is currently only a top5 artifact probe. The setting is recorded in
`report.json`, included in `run_config_digest`, and resume reruns shards when it
changes.

Do not use `FASIM_CUDA_DEVICES=0,1` as the final-speed-stack multi-GPU mode.
`FASIM_EXACT_COLUMN_EXTEND_BATCH=1` is correctness-critical for the reconciled
GPU DP/AUTO path and is supported only when a Fasim process sees one CUDA
device. The binary now fails closed if exact-column batch is requested with a
multi-device `FASIM_CUDA_DEVICES` list.

Use `--workers-per-gpu N` with `--gpu-ids` to derive the worker count as
`len(gpu_ids) * N`. This is a default-off convenience option and is mutually
exclusive with `--workers`; it does not change scheduler defaults.

Use `--auto-cpu-core-ranges` with `--cpu-pool` and
`--cpu-cores-per-worker` to derive one `taskset` range per worker. Explicit
`--cpu-core-ranges` still works and remains mutually exclusive with auto CPU
range derivation. Without these CPU options, worker CPU binding remains off.

## Manifest and Resume

Long sharded runs can write an auditable manifest:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --manifest .tmp/fasim_sharded/run_manifest.json \
  --output-mode lite \
  --workers-per-gpu 3 \
  --gpu-ids 0,1
```

When `--manifest` is used, an existing run directory with a manifest requires
either `--resume` or `--force`. `--resume` only skips a shard when the previous
manifest entry is compatible with the current run config, the shard input digest
matches, the output file exists, and the recorded output digest still matches.
Otherwise the shard is rerun. `--force` clears the old work directory and starts
a new run id.

`--keep-going` records failed shards and continues other workers. A run with any
failed shard is marked `run_status=incomplete`; it writes only
`partial_merged_digest`, leaving the final `merged_digest` unset so partial
outputs cannot be mistaken for a complete whole-target result.

## Merge Semantics

The merge step supports `lite` and `tfosorted` record outputs. It:

1. Reads each shard output.
2. Validates that all headers match.
3. Sorts records by canonical record fields.
4. Removes exact duplicate records.
5. Writes a stable merged output and SHA-256 digest.

The merge does not depend on worker completion order.

## Validation

Run the local check:

```bash
make check-fasim-sharded-runner
make check-fasim-sharded-scheduler
```

The check builds `fasim_longtarget_x86`, creates a deterministic two-contig
fixture from `testDNA.fa`, runs Fasim once on the multi-contig target, runs Fasim
once per contig shard, merges shard output, and verifies digest equality.

The scheduler check runs both the baseline sharded mode and a two-worker
scheduled mode, then verifies that both merged outputs have the same canonical
digest and record counts.

Expected report fields include:

```text
shard_count
shard_ids
per_shard[*].target_name
per_shard[*].records
per_shard[*].digest
worker_count
gpu_ids
cpu_core_ranges
per_worker[*].worker_id
per_worker[*].gpu_id
per_worker[*].shard_ids
sharded_records
merged_records
duplicate_records_removed
single_records
single_digest
merged_digest
single_vs_sharded_digest_match
```

## Current Limits

This runner is safe for chromosome/contig-level sharding. It should not be used
for arbitrary chunk splitting yet. Chunking needs a separate safe-overlap design
derived from the window planner, maximum extension span, record coordinates, and
downstream non-overlap semantics.

If a contig-level single-vs-sharded digest differs, fix canonical merge or output
normalization before adding any scheduler or multi-GPU work.

## Next Step

After digest equality is stable on representative multi-contig fixtures, the
next PR should characterize process-level scaling:

- Compare one, two, and four workers where hardware is available.
- Record per-worker wall time, CPU/GPU assignment, records, digests, and
  fallbacks.
- Keep merged digest validation as the release gate.
