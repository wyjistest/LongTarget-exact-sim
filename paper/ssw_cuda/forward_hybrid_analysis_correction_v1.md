# Phase 7 offline analysis correction 1

The first offline comparison attempt created only an empty per-attempt
directory and then stopped. Historical Phase 2 authority output directories
contain wrapper stdout/stderr logs alongside exactly one `*-TFOsorted` result.
The original adapter incorrectly required the whole directory to contain one
file.

The corrected adapter selects exactly one regular, non-symlink file whose
basename ends in `-TFOsorted`; zero or multiple matches remain hard failures.
This implements the already-frozen `FASIM_OUTPUT_MODE=tfosorted` comparison
boundary and ignores no result file.

The empty `offline-comparison-v2` root remains immutable. Receipts are written
to `offline-comparison-v3`. This correction launches zero backend attempts,
changes no measurement, consumes no additional input, and leaves the two of
two execution/measurement repairs unchanged. It does not alter the no-go
classification established by the CPU continuation contract failure.
