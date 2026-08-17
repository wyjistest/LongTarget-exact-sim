# Exact long-query hybrid checkpoint v1

This checkpoint is separate from every Bioinformatics successor state. It does
not reopen or modify the historical v2 no-go.

## Scope

The implementation under test is exactly:

```text
stateful whole-query GPU scoreInfo
-> all-attempt GPU score/query-end/ref-end
-> ordered host selection
-> selected-attempt CPU reverse-start/CIGAR continuation
-> canonical Fasim output
```

The mode is an exact hybrid engineering candidate. It is not GPU-only and is
not authorized for production.

```text
long_query_hybrid = engineering_candidate
exactness = passed_on_3_discrete_fixtures
validated_continuous_range = false
production_target_contract = not_validated
full_gpu_traceback = not_implemented
production_authorized = false
bioinformatics_v2_state = unchanged
```

## Clean checkpoint result

The clean checkpoint completed with:

```text
status = checkpoint_gate_pass
benchmark source = 61da9b6f1b3d998043d512f5703dc95671d2383e
formal binary SHA-256 = 6e9d5cec5ff50c9652b9aeb05a8a5533a9d707e0799d9925b2686377cdfdd7ee
run matrix = 36/36
candidate consumer task rows = 186624
all-attempt CPU oracle calls = 0
full CPU consumer replay attempts = 0
selected continuation failures = 0
fallbacks = 0
```

All paired CPU/hybrid `TFOsorted.lite` and complete `TFOsorted` outputs were
byte-identical. Each output digest was deterministic across three repeats.

| Fixture | Query nt | Lite median speedup | Full median speedup |
| --- | ---: | ---: | ---: |
| LINC01501 | 4,006 | 2.086850x | 2.046231x |
| PCAT19 | 8,181 | 2.290544x | 2.291396x |
| AL035530.2 | 12,397 | 2.621838x | 2.583776x |

The independent freezer re-read all run records, recalculated all output
digests, performed paired byte comparisons, and audited every consumer task
row. Its sorted manifest binds 237 formal evidence files with SHA-256:

```text
48179f951eb467832a0c3ba2f79eb975b139cb63dea61ce6182c06d86e9ab583
```

The frozen derived evidence is:

* `checkpoint_results.tsv`: exactness, determinism, coverage, and performance;
* `stage_timing.tsv`: per-repeat forward, attempt, continuation, and output timing;
* `operating_envelope.json`: observed device/resource and numeric boundaries;
* `decision.json`: pass decision, evidence binding, and claim boundary;
* `checksums.sha256`: tracked evidence integrity.

## Evidence boundary

`checkpoint_fixtures.tsv` freezes the three observed query lengths, both clean
output digests, and the development-only 2 Mb target. The clean run was rebuilt
from `61da9b6f1b3d998043d512f5703dc95671d2383e`, recorded an empty source diff
at build time, and compared CPU and hybrid outputs independently.

`build_exact_long_query_hybrid_checkpoint_v1.py` performs that build in a
separate detached worktree. It refuses a dirty source tree, checks the source
again after compilation, verifies the pinned GASAL2 commit and patched-tree
digest, and emits the only build receipt accepted by the formal run.

The manifest separately binds each original metadata-rich FASTA, the
short-header runtime FASTA, and the normalized sequence digest. The short
header is required because Fasim derives its output filename from the FASTA
record name. `preexecution_input_repair_v1.json` records the first 8 kb
pre-alignment filename failure and proves that the repair changes only the
header, not the sequence or runtime.

The three lengths are discrete fixtures. They must not be reported as a
validated continuous 4-12 kb range.

The checkpoint runner requires, for every paired run:

* byte-identical `TFOsorted.lite` and complete `TFOsorted` outputs;
* deterministic output digests across repeats;
* complete GPU endpoint-attempt coverage;
* zero full CPU consumer replay and zero all-attempt CPU oracle calls;
* selected CPU continuation calls equal selected attempts;
* zero continuation failures and zero fallback accounting;
* paired end-to-end speedup of at least 1.5x only after exactness passes.

DBD1, DBS, affinity, promoter mapping, and candidate-site promotion are not
claimed from the contiguous chr22 fixture. Those gates belong to the frozen,
not-yet-executed production promoter panel.

## Production promoter identity

`production_promoter_contract.json` binds the only eligible human target to
the 48,275 TSS rows taken directly from `human_genes20cells.tsv`:

```text
human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1
```

The older target that selected genes first and then expanded them to all TSS
entries is explicitly forbidden:

```text
human_GRCh38_GENCODE_v33_genes20cells_selected_genes_all_tss_promoters_v1
```

The promoter gate verifies artifact digests, the no-separator serialization,
component contiguity, source-row counts, and fail-closed cross-component and
reference-N rules. Passing this identity gate does not validate hybrid
scientific output on the promoter target; it only freezes the correct input
contract before execution.

## Operating envelope

The endpoint kernel currently uses fixed scoring semantics:

```text
match = 5
mismatch = 4
gap_open = 16
gap_extend = 4
CPU continuation numeric path = WORD16
```

Dynamic shared-memory demand is:

```text
3 * ceil(query_length / 32) * 32 * sizeof(int16_t)
```

The runner records device default and opt-in shared-memory limits and reports
resource fit for each fixture. Resource fit is not scientific validation.
The RTX 4090 used here gives a resource-formula-only ceiling of 16,896 nt; that
number is not a validated query-length limit and is not a support claim.
Runtime scoring-parameter and int16 range guards are not implemented in
`61da9b6`; production remains blocked until unsupported configurations fail
closed and boundary fixtures pass.

## Decision and next gate

The implementation remains an exact hybrid engineering candidate. The next
engineering gate is a fresh panel using the frozen real promoter target,
including component-local coordinate restoration and fail-closed rejection of
cross-component and reference-N hits. No production mode, continuous 4-12 kb
range, GPU-only traceback, or Bioinformatics v2 claim is authorized by this
checkpoint.
