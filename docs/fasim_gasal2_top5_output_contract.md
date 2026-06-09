# Fasim GASAL2 Top5 Output Contract

This contract is the usable surface for the current short-query GASAL2
scoreInfo/preAlign path. It is intentionally top5-only.

## Contract

The formal preset is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

It emits:

```text
result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
```

The contract output artifacts are:

```text
topk_summary.tsv
topk_rows.tsv
topk-TFOsorted.lite
report.json
run_manifest.json
```

`topk_summary.tsv` and `topk_rows.tsv` are self-describing. Their first line is:

```text
# result_contract=gasal2_top5_column_pruned_scoreinfo_artifact_v1
```

The payload after that contract line is the cross-contract comparable content.
Full artifact digests include the contract line; payload digests are used for
CPU/full-vs-GASAL2 top5 equivalence.

## Ranking Modes

The checked top5 modes are:

```text
score
stability
nt_score
```

The directly consumable lite artifact, `topk-TFOsorted.lite`, is the
deterministic de-duplicated union of those mode/rank rows. It may contain fewer
than fifteen rows when the same row appears in multiple modes.

## Required State

A run satisfies this contract only when all of the following are true:

```text
topk_summary_only = true
shard_output_topk_lite = 5
topk_summary.k = 5
gasal2_top5_column_pruned_scoreinfo = true
gasal2_top5_scoreinfo_prune_max_per_task = 64
exact_scoreinfo_gpu_max_per_task = 512
exact_scoreinfo_gpu_pruned_output = true
exact_scoreinfo_gpu_column_pruned_output = true
gasal2_top5_activation_verified = true
gasal2_top5_activation_error = null
gasal2_top5_query_preflight_supported = true
gasal2_top5_query_preflight_error = null
gasal2_top5_query_preflight_query_len <= gasal2_top5_query_preflight_max_query_len
gasal2_top5_query_preflight_max_query_len <= 2812
```

The formal preset-managed environment is:

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

The report benchmark sums must prove active GASAL2 and exact-scoreInfo GPU use:

```text
fasim_top5_gasal2_gpu_scoreinfo_requested = shard_count
fasim_top5_gasal2_gpu_scoreinfo_active = shard_count
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled = shard_count
fasim_gasal2_requests > 0
fasim_gasal2_score_requests > 0
fasim_gasal2_traceback_requests > 0
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks > 0
fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled = shard_count
fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows > 0
fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank > 0
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches = 0
fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches = 0
fasim_gasal2_fallbacks = 0
fasim_gasal2_length_guard_fallbacks = 0
fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows = 0
```

The formal runner activation check uses the same active-path predicates before
the run is accepted as completed. topK-lite rank-observe telemetry is enabled,
non-empty, and free of unknown rows; otherwise the formal preset fails closed
instead of producing an activation-clean artifact.

## Non-Goals

This contract does not claim:

```text
full lite-output equivalence
full scoreInfo/preAlign universal replacement
exact legacy scoreInfo equivalence
aligner.Align replacement
GPU endpoint authority
GPU CIGAR / traceback authority
validity for long-query MALAT1/NEAT1 GASAL2 execution
segmented long-query GASAL2 traceback
segmented long-query score-prepass
CPU replay for long-query segmented candidates
```

The long-query segmented probes remain outside this contract. The direct and
pruned segmented traceback shadows are performance no-go, and the
score-prepass batched shadow is stage-only; it does not provide endpoint,
CIGAR, traceback, candidate state, output, or digest authority.
The formal preset also rejects segmented long-query diagnostic `--env` keys
such as `FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW`, so a formal artifact
cannot silently mix this top5 contract with the segmented shadow line.
Formal artifact integrity checks reject the same segmented diagnostic env keys
if they appear in `report.json` or `run_manifest.json`. They also reject
unsupported formal env extras such as `FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST`;
only the managed preset env and checked diagnostic overrides are accepted.
If `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN` is present, it must match the recorded
`gasal2_top5_query_preflight_max_query_len`.

Rows outside the checked top5 modes are not contract output. Full merged `.lite`
or final all-row TFO output must not be inferred from this contract.

## Verification

Focused contract gate:

```bash
make check-fasim-gasal2-top5-output-contract
make check-fasim-gasal2-top5-activation-contract
```

Formal GASAL2 top5 gate:

```bash
make check-fasim-gasal2-top5-formal-gate
```

Current scoreInfo/preAlign milestone gate:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

Top5-only product-readiness gate:

```bash
make check-fasim-gasal2-top5-product-readiness
```

Top5 broader workload validation gate:

```bash
make check-fasim-gasal2-top5-broader-validation
```

GASAL2 top5 recommended runtime gate:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

Top5 scoped completion candidate gate:

```bash
make check-fasim-gasal2-top5-scoped-completion-candidate
```

The current scoreInfo/preAlign milestone is checked by the current-state gate.
It composes the recorded chr21+chr22 result, MEG3 grouped top5 wrapper result,
this top5 output contract, and the long-query boundary. Its scope is:

```text
short-query/H19 top5 scoreInfo/preAlign: milestone go
MEG3 grouped top5 wrapper: milestone go
full replacement goal remains open
```

The top5-only product-readiness gate records the accepted opt-in boundary for
this contract. It does not expand the contract to full output, long-query
production output, endpoint authority, CIGAR, or traceback. The full objective
remains open.

The artifact integrity checker is:

```bash
python3 scripts/check_topk_summary_digest_integrity.py \
  --report <candidate-report.json> \
  --manifest <candidate-run_manifest.json> \
  --same-payload-as <cpu-full-top5-report.json>
```

That checker enforces the contract line, payload digests, report fields,
manifest fields, managed env, active-path benchmark sums, and the deterministic
`topk-TFOsorted.lite` union.
