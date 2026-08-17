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

## Evidence boundary

`checkpoint_fixtures.tsv` freezes the three already observed query lengths and
the development-only 2 Mb target. A clean checkpoint run must rebuild from
`61da9b6f1b3d998043d512f5703dc95671d2383e`, record an empty source diff at
build time, and compare CPU and hybrid outputs independently.

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
Runtime scoring-parameter and int16 range guards are not implemented in
`61da9b6`; production remains blocked until unsupported configurations fail
closed and boundary fixtures pass.
