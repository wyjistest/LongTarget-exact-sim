# Fasim SIM-Close Recovery Real Mode

Base branch:

```text
fasim-sim-recovery-real-mode-design
```

This document describes the first default-off `FASIM_SIM_RECOVERY=1`
skeleton. The implementation lives in the taxonomy benchmark/check harness and
uses the existing Fasim binary plus bounded local legacy SIM execution to emit a
side SIM-close lite output. It does not change the default Fasim output path.

## Modes

Fast mode is unchanged. When `FASIM_SIM_RECOVERY` is unset, the existing Fasim
output and canonical digest remain the authority.

SIM-close mode is explicitly requested with:

```bash
FASIM_SIM_RECOVERY=1
```

This mode intentionally emits a separate SIM-close output. Its digest is not
expected to match the default Fasim digest; it must instead be deterministic for
the same fixture and settings.

Validation is requested with:

```bash
FASIM_SIM_RECOVERY=1 FASIM_SIM_RECOVERY_VALIDATE=1
```

Validation may use legacy `-F` SIM output only after SIM-close output is already
generated. SIM labels, SIM-only records, and oracle membership are not used to
select, rank, suppress, or emit production candidates.

## Skeleton Shape

The current skeleton follows the #70 design:

1. Run default Fasim and keep its records.
2. Build Fasim-visible recovery boxes from Fasim output records.
3. Run bounded local legacy SIM inside those boxes.
4. Apply the #69 `combined_non_oracle` guard.
5. Use box-local replacement: suppress Fasim records in recovered boxes, then
   add accepted recovered records.
6. Write a side SIM-close lite output and report an independent digest.

The `combined_non_oracle` guard accepts a recovered candidate only when it is
inside a detector box, has `score >= 89`, has `Nt >= 50`, has local rank `<= 2`
within the accepted candidate set, and is not contained by a same-family
higher-score candidate.

## Telemetry

The harness reports:

```text
fasim_sim_recovery_requested
fasim_sim_recovery_active
fasim_sim_recovery_validate_enabled
fasim_sim_recovery_validate_supported
fasim_sim_recovery_boxes
fasim_sim_recovery_cells
fasim_sim_recovery_executor_seconds
fasim_sim_recovery_fasim_records
fasim_sim_recovery_recovered_candidates
fasim_sim_recovery_recovered_accepted
fasim_sim_recovery_fasim_suppressed
fasim_sim_recovery_output_records
fasim_sim_recovery_output_digest_available
fasim_sim_recovery_output_digest
fasim_sim_recovery_recall_vs_sim
fasim_sim_recovery_precision_vs_sim
fasim_sim_recovery_extra_vs_sim
fasim_sim_recovery_overlap_conflicts
fasim_sim_recovery_fallbacks
fasim_sim_recovery_output_mutations_fast_mode
```

When validation is unavailable, `validate_supported=0` and recall/precision
metrics are reported as zero while the SIM-close output digest remains stable.

## Boundaries

This is not a default or recommended mode. It is CPU-only, uses the existing
legacy SIM executor for bounded local boxes, and has no GPU recovery path.

The current evidence is from deterministic synthetic fixtures. Production-corpus
evaluation is still required before this can be recommended as a high-accuracy
mode.

## Checks

Use:

```bash
make check-fasim-sim-recovery-real-mode
```

The smoke check asserts that the skeleton is active only under
`FASIM_SIM_RECOVERY=1`, writes a side `.lite` output, reports a stable digest,
keeps `output_mutations_fast_mode=0`, and under validation reports the expected
smoke recall/precision/extra/conflict metrics.
