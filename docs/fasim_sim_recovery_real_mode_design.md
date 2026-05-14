# Fasim SIM-Close Recovery Real Mode Design

Base branch:

```text
fasim-local-sim-recovery-replacement-extra-taxonomy
```

This document defines the real opt-in SIM-close recovery mode before implementation. It is design-only: no `FASIM_SIM_RECOVERY=1` path is added here, Fasim output is not mutated, and scoring, threshold, non-overlap, GPU, and filter behavior are unchanged.

The design is based on the diagnostic stack through replacement extra taxonomy. The strongest current representative synthetic signal is:

| Signal | Value |
| --- | --- |
| baseline replacement true SIM records | 369 |
| baseline replacement extra records | 164 |
| `combined_non_oracle` recall vs SIM | 100.00% |
| `combined_non_oracle` precision vs SIM | 90.00% |
| `combined_non_oracle` extra vs SIM | 41 |
| `combined_non_oracle` overlap conflicts | 164 |
| output mutations in shadows | 0 |

This crosses the design threshold for a real opt-in mode. It does not justify default enablement or production accuracy claims.

## Modes

### Fast Mode

Fast mode is the existing default Fasim path. It remains the default behavior when `FASIM_SIM_RECOVERY` is unset or `0`.

Required invariants:

| Invariant | Requirement |
| --- | --- |
| default output | unchanged |
| baseline digest | must match current Fasim digest |
| recovery executor | not run |
| recovered records | not emitted |
| validation against SIM | not required |

Fast mode may continue to use already validated accelerations such as `FASIM_TRANSFERSTRING_TABLE=1` when those are explicitly enabled by their own controls. SIM-close recovery must not change that contract.

### SIM-Close Mode

SIM-close mode is the future explicit opt-in path:

```bash
FASIM_SIM_RECOVERY=1
```

This mode intentionally produces a different output from default Fasim. Its goal is to recover SIM-like overlap, nested, and internal-peak records in Fasim-supported local regions. It is not a speed optimization for Fasim-identical output.

Required invariants:

| Invariant | Requirement |
| --- | --- |
| opt-in | explicit env only |
| default output | unchanged when env is off |
| output digest | stable SIM-close digest, not Fasim baseline digest |
| candidate selection | non-oracle only |
| final report | includes recovery telemetry and digest |

### Validate Mode

Validation mode is a diagnostic overlay:

```bash
FASIM_SIM_RECOVERY=1 FASIM_SIM_RECOVERY_VALIDATE=1
```

When legacy SIM output is available, validation compares the SIM-close result against legacy `-F` SIM taxonomy after candidate generation. SIM labels are evaluation-only and must never select, rank, suppress, or emit production candidates.

When legacy SIM output is unavailable, validation should still report internal invariants: deterministic digest, recovered candidate counts, fallback counts, box/cell cost, and output record count.

## Candidate Source

The real implementation should use the same non-oracle source chain that passed the diagnostic shadows:

1. Run default Fasim and retain its output records.
2. Build Fasim-visible risk detector boxes from Fasim output family, orientation, and coordinates.
3. Run bounded local legacy SIM executor inside those boxes.
4. Convert local executor records back to global coordinates.
5. Apply the `combined_non_oracle` guard from the extra-taxonomy PR.
6. Merge selected recovery records with untouched Fasim records outside recovered boxes.

Forbidden production inputs:

| Input | Production use |
| --- | --- |
| SIM-only coordinates | forbidden |
| taxonomy labels | forbidden |
| legacy SIM membership | forbidden |
| oracle boxes | forbidden |

Allowed evaluation inputs under `FASIM_SIM_RECOVERY_VALIDATE=1`:

| Input | Evaluation use |
| --- | --- |
| legacy SIM output | recall, precision, extra, conflict metrics |
| SIM-only labels | post-hoc taxonomy only |
| oracle guard | analysis-only upper bound in reports, not real selection |

## Guard Definition

The initial real-mode guard should be the #69 `combined_non_oracle` guard:

```text
candidate is accepted when:
  candidate is inside a Fasim-visible detector box
  score >= 89
  Nt >= 50
  local_rank_per_box <= 2
  not dominated_by_higher_score
```

The local rank must be deterministic. The diagnostic runner currently orders candidates by:

```text
score descending
Nt descending
genomic start ascending
query start ascending
raw canonical record ascending
```

`dominated_by_higher_score` means a same-family candidate with higher score contains both the genomic and query intervals. If implementation details differ from the diagnostic runner, the real PR must document the difference and rerun validation before enabling the mode.

## Merge Semantics

The real mode should use box-local replacement, not raw union.

For each recovered detector box:

1. Suppress Fasim records inside the recovered box.
2. Add recovered records accepted by `combined_non_oracle`.
3. Keep Fasim records outside recovered boxes unchanged.
4. De-duplicate exact canonical lite records.
5. Emit a deterministic SIM-close output order.

This replacement shape is the current best non-oracle structure:

| Strategy | Recall vs SIM | Precision vs SIM | Extra vs SIM | Overlap conflicts |
| --- | ---: | ---: | ---: | ---: |
| raw union | 100.00% | 34.62% | 697 | 1968 |
| filtered union | 100.00% | 47.37% | 410 | 984 |
| box-local replacement | 100.00% | 69.23% | 164 | 451 |
| combined non-oracle replacement | 100.00% | 90.00% | 41 | 164 |

### De-Duplication

The first real implementation should de-duplicate by exact canonical lite record identity:

```text
family
orientation
DNA coordinates
RNA coordinates
score
Nt / alignment length fields used by existing lite output
```

Near-duplicate or fuzzy suppression must remain diagnostic until it is proven not to drop SIM-like nested or overlap records.

### Overlap Conflict Handling

SIM-close mode should not treat every same-family overlap as a failure. The SIM gaps found so far are specifically concentrated in overlap chains, nested alignments, and long-hit internal peaks. Dropping all overlap conflicts would erase the target signal.

Initial real-mode behavior:

| Case | Handling |
| --- | --- |
| exact duplicate | keep one canonical record |
| selected recovered record overlaps another selected recovered record | keep both, report conflict |
| selected recovered record overlaps suppressed in-box Fasim record | recovered record wins |
| selected recovered record overlaps out-of-box Fasim record | keep both initially, report conflict |
| unsupported box or executor failure | keep original Fasim records and increment fallback |

This preserves SIM-close recall while making conflict cost visible. A later PR may add stricter optional conflict policies, but the first real mode should not silently apply Fasim fast-mode non-overlap suppression to recovered SIM-like records.

### Ordering and Canonicalization

SIM-close output must be deterministic. The first implementation should use a canonical comparator equivalent to:

```text
family / orientation
genomic start
genomic end
query start
query end
score descending
Nt descending
raw canonical record
```

The exact comparator should be documented in the real implementation PR. The SIM-close digest is computed after this canonicalization.

## Validation Semantics

SIM-close validation is different from fast-mode validation.

Fast mode success:

```text
default Fasim output digest equals baseline digest
```

SIM-close mode success:

```text
default digest remains unchanged when recovery is off
SIM-close digest is stable when recovery is on
recall vs SIM improves or remains high
precision vs SIM remains acceptable
extra records and overlap conflicts are reported
runtime overhead is documented
```

When legacy SIM output is available, `FASIM_SIM_RECOVERY_VALIDATE=1` should report:

| Metric | Meaning |
| --- | --- |
| `recall_vs_SIM` | SIM records present in SIM-close output / SIM records |
| `precision_vs_SIM` | SIM-close records present in SIM / SIM-close records |
| `extra_vs_SIM` | SIM-close records not present in SIM |
| `overlap_conflicts` | diagnostic same-family genomic overlap pairs |
| `sim_only_recovered` | legacy SIM-only records recovered by SIM-close output |
| `output_digest` | stable SIM-close canonical digest |

Validation must not require SIM-close output to match the default Fasim digest.

## Telemetry

The future real implementation should expose at least:

```text
fasim_sim_recovery_requested
fasim_sim_recovery_active
fasim_sim_recovery_validate_enabled
fasim_sim_recovery_boxes
fasim_sim_recovery_cells
fasim_sim_recovery_executor_seconds
fasim_sim_recovery_fasim_records
fasim_sim_recovery_recovered_candidates
fasim_sim_recovery_recovered_accepted
fasim_sim_recovery_fasim_suppressed
fasim_sim_recovery_output_records
fasim_sim_recovery_recall_vs_sim
fasim_sim_recovery_precision_vs_sim
fasim_sim_recovery_extra_vs_sim
fasim_sim_recovery_overlap_conflicts
fasim_sim_recovery_output_digest
fasim_sim_recovery_fallbacks
```

Recommended additional telemetry:

```text
fasim_sim_recovery_guard_combined_non_oracle_selected
fasim_sim_recovery_guard_local_rank_rejected
fasim_sim_recovery_guard_dominated_rejected
fasim_sim_recovery_executor_failures
fasim_sim_recovery_unsupported_boxes
fasim_sim_recovery_default_digest
fasim_sim_recovery_digest_mode
```

## Future Real PR Success Criteria

The implementation PR for `FASIM_SIM_RECOVERY=1` should pass these gates before review:

| Gate | Requirement |
| --- | --- |
| default behavior | default Fasim digest unchanged |
| opt-in behavior | SIM-close output digest stable |
| production inputs | no SIM oracle labels in candidate selection |
| representative recall | remains high, target >= 90% vs SIM when validation is available |
| representative precision | remains acceptable, target >= 80% vs SIM when validation is available |
| extra records | quantified and not hidden |
| overlap conflicts | quantified and not hidden |
| runtime | executor and total overhead reported |
| fallbacks | unsupported boxes preserve default Fasim records |
| documentation | mode semantics and digest expectations documented |

The first real mode may still be default-off and experimental even if these gates pass. Recommendation or default enablement requires separate production-corpus evidence.

## Non-Goals

This design explicitly excludes:

| Non-goal | Reason |
| --- | --- |
| default enablement | SIM-close output changes semantics |
| GPU recovery path | CPU bounded local SIM must be correct first |
| approximate output without opt-in | users need explicit SIM-close semantics |
| scoring changes | would confound recovery validation |
| threshold changes | would confound recall/precision interpretation |
| fast-mode non-overlap changes | default Fasim must remain stable |
| production accuracy claim from synthetic fixtures | current evidence is representative synthetic only |

## Recommended Next PR

The next PR can implement the real opt-in skeleton:

```bash
FASIM_SIM_RECOVERY=1
FASIM_SIM_RECOVERY_VALIDATE=1
```

Recommended scope:

1. Keep default Fasim output byte-for-byte stable.
2. Implement CPU-only risk boxes, bounded local SIM executor, `combined_non_oracle` guard, and box-local replacement.
3. Emit SIM-close output only when `FASIM_SIM_RECOVERY=1`.
4. Add `FASIM_SIM_RECOVERY_VALIDATE=1` telemetry against legacy SIM when available.
5. Report separate fast-mode and SIM-close digests.

The real implementation PR should remain opt-in and should not claim recommended/default status.
