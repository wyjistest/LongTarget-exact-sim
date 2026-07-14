# Fasim GASAL2 Segment Ownership Phase 2

## Decision

Phase 2 is `no_go` for production canonical-grid ownership and work dropping.
The implementation and evidence are complete, but the short-query authority
gate fails:

```text
short_oracle_missing_rows = 0
short_oracle_extra_rows = 17
rows_no_owner = 0
owner_is_unique = 1
all_three_top5_equal = 0
boundary_ties_equal = 1
multiple_shift_matrix_clean = 0
runtime_work_dropped = 0
```

The default remains the existing dual-grid segmented workflow. Phase 3 and
later phases may process multiple segments, but they must not use Phase 2
ownership to discard candidates, exact tasks, or traceback requests.

## Coordinate Contract

Segment descriptors use zero-based half-open coordinates:

```text
[segment_start, segment_end)
[core_start, core_end)
```

TFOsorted rows retain their existing one-based inclusive query coordinates:

```text
[QueryStart, QueryEnd]
```

For adjacent overlapping segments, the deterministic core boundary is:

```text
floor((left.segment_end + right.segment_start) / 2)
```

The outer core edges stop at the first and last selected segment edges. This
supports bounded central KCNQ1OT1 grids without falsely marking them as the
first or last segment of the 91,667-bp transcript. `is_first_segment` is true
only when `segment_start=0`; `is_last_segment` is true only when
`segment_end=query_length`.

The descriptor manifest records:

```text
segment_id
grid_shift
segment_start
segment_end
core_start
core_end
left_halo
right_halo
query_length
is_first_segment
is_last_segment
```

## Ownership Rule

A final row is eligible for a segment only when its complete query span is
contained by that segment. Among eligible segments, the owner is selected by:

1. maximum row-span overlap with the segment core;
2. minimum row-center to core-center distance;
3. lower segment start;
4. stable segment ID.

The rule depends only on final row coordinates and the descriptor manifest. It
does not depend on segment processing order. A row longer than every segment
has no owner and cannot be pruned.

The SQLite shadow stores unique complete rows and whether the computed owner
actually emitted each row. It writes a separate ownership-filtered diagnostic
output. The runtime merged output and downstream grid comparison continue to
use the unfiltered segment artifacts.

```text
FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=0  # default
FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=1  # explicit diagnostic only
```

In both modes:

```text
runtime_work_dropped=0
potential_exact_tasks_removed=unavailable
potential_tracebacks_removed=unavailable
```

## Comparator Contract

`scripts/compare_fasim_segmented_contract.py` compares:

- the complete unique row set;
- raw score, stability, and Nt top5;
- score, stability, and Nt representatives after the same clustering pass;
- conservative tie-complete sets for all non-singleton ranking ties;
- clusters whose representative changes between ranking modes.

Input rows are sorted by the complete 19-column TFOsorted row before the
existing offline clustering implementation runs. Each cluster then chooses an
independent representative for score, stability, and Nt ranking, with the
complete row as the deterministic final tie-break.

## Synthetic Oracle

The synthetic fixture covers core rows, boundary-crossing rows, exact core
edges, first/last query edges, all four strand labels, long spans, ranking
ties, and representative conflicts. It also reverses descriptor and row order
to check order independence.

```text
rows_total=14
rows_unique=9
rows_owned=9
rows_non_owner_duplicate=5
rows_no_owner=0
rows_multi_owner_before_tiebreak=5
authority_missing_rows=0
authority_extra_rows=0
owner_is_unique=1
output_byte_identical_to_authority=1
runtime_work_dropped=0
```

This proves that the ownership implementation can represent a clean oracle.
It does not prove that independently executed LongTarget segments emit the
same complete row set as an unsegmented query.

## H19 CPU Authority Matrix

Receipt:

```text
.tmp/characterize_fasim_segment_ownership_h19_phase2_20260715
query = H19.fa
query_length = 2812
target = testDNA.fa
target_length = 4366
segment_length = 2048
segment_overlap = 512
grid_shifts = 0 128 256
authority = default CPU/existing exact path
authority_rows = 145
```

| Candidate | Missing | Extra | Cluster score | Cluster stability | Cluster Nt | All three | Row reduction opportunity |
|---|---:|---:|---:|---:|---:|---:|---:|
| shift 0 merged | 0 | 22 | 1 | 0 | 1 | 0 | unavailable |
| shift 0 ownership | 0 | 17 | 1 | 0 | 1 | 0 | 7.43% |
| shift 128 merged | 0 | 92 | 1 | 0 | 1 | 0 | unavailable |
| shift 128 ownership | 0 | 13 | 1 | 0 | 1 | 0 | 41.48% |
| shift 256 merged | 0 | 93 | 1 | 0 | 1 | 0 | unavailable |
| shift 256 ownership | 0 | 11 | 1 | 0 | 1 | 0 | 42.22% |
| dual-grid merged | 0 | 152 | 1 | 0 | 1 | 0 | unavailable |

The shift-0 ownership accounting is:

```text
rows_total=175
rows_unique=167
rows_owned=162
rows_no_owner=0
rows_multi_owner_before_tiebreak=20
rows_owner_mismatch_vs_authority=5
authority_missing_rows=0
authority_extra_rows=17
```

The result reproduces the critical no-go chain:

```text
CPU unsegmented authority = 145 rows
CPU canonical segmented grid = 167 unique rows (0 missing, 22 extra)
ownership-filtered shadow = 162 rows (0 missing, 17 extra)
```

Ownership removes five segmented-only rows because their computed owner did
not emit them, but it does not remove the remaining 17 extras. More
importantly, the stability-ranked clustered top5 differs in every real grid.
No single-grid or ownership candidate satisfies the Phase 2 hard gate.

The frozen unsegmented GPU probe has 144 rows relative to the 145-row CPU
authority (`missing=2`, `extra=1`) while all tested raw and clustered top5
rankings are equal. It remains a candidate path, not authority.

## KCNQ1OT1 Bounded Shadow

The existing max4 chr22-full shift-0 text artifacts were read without rerunning
chr22 and without modifying the old result directory. The shadow receipt is:

```text
.tmp/characterize_fasim_segment_ownership_kcnq1ot1_max4_shift0_20260715
query_length=91667
bounded_segment_range=41472-48128
segments=4
segment_length=2048
segment_overlap=512
rows_total=932168
rows_unique=631258
rows_owned=599940
rows_non_owner_duplicate=329103
rows_no_owner=0
rows_multi_owner_before_tiebreak=367615
rows_owner_mismatch_vs_authority=31318
potential_row_observations_removed=332228
potential_row_reduction_percent=35.64
runtime_work_dropped=0
elapsed_seconds=39.75
peak_rss_kb=180652
sqlite_bytes=215109632
```

This is a bounded row-level scale measurement only. There is no unsegmented
full-length KCNQ1OT1 authority, and the archive/TFOsorted schema does not carry
the identity of upstream exact tasks or traceback requests. Therefore:

```text
potential_exact_tasks_removed=unavailable
potential_tracebacks_removed=unavailable
```

The 35.64% row-observation opportunity must not be reported as a 35.64% GPU
work or wall-time opportunity. The 31,318 rows whose computed owner did not
emit the row are direct evidence that final-row ownership cannot safely be
projected backward into a work-dropping certificate.

## Interpretation

Shifted-grid clustered stability is useful for a bounded segmented screening
workflow, but:

```text
grid stability != unsegmented equivalence
duplicate final rows != duplicate exact tasks
duplicate final rows != duplicate tracebacks
row-level potential reduction != runtime work reduction
```

Phase 2 is complete as an evidence-backed `no_go`. The safe retained changes
are descriptor derivation, the deterministic shadow, the tri-ranking contract
comparator, and default-off runner telemetry. Production ownership and
single-grid pruning are not promoted.

## Reproduction

```bash
python3 tests/check_fasim_segment_ownership.py
python3 tests/check_compare_fasim_segmented_contract.py
python3 tests/check_characterize_fasim_segment_ownership_h19_runner.py
python3 tests/check_characterize_fasim_gasal2_segmented_archive_first_runner.py
make check-fasim-gasal2-segment-ownership
```

The Make gate reruns the small H19 CPU matrix. The KCNQ1OT1 receipt depends on
large local chr22 artifacts and is checked when present; its recorded metrics
remain an external/local characterization, not a clean-checkout CI benchmark.
