# Phase 1 CPU Profile And Amdahl Decision

Execution epoch: `phase1-profile-v2`.

The v1 fixed-timeout failure remains immutable and was not reused in these
statistics. V2 repeated the complete 50-attempt panel from the beginning;
the only execution-policy change was the preregistered outer timeout.

Status: `pass`

Bioinformatics B3 track: `closed_amdahl`.
Engineering track: `active`.

The original end-to-end target remains 10x. The gate uses the lower 95%
bootstrap bound of the steady-state median addressable fraction for each
claim-relevant large workload, then takes the less favorable workload.

Conservative addressable fraction: `0.619448148`.
Infinite-backend Amdahl ceiling: `2.627762802x`.
Backend speedup required for 10x end-to-end: `unreachable`.
Decision reason: `conservative_backend_fraction_at_or_below_0.90`.

Profiling used only previously consumed development/regression inputs. The
default-off and instrumented runs produced byte-identical authority artifacts
for every paired observation. This decision does not establish performance or
correctness for a future GPU backend and does not authorize a CUDA DP kernel
before the later phase gates.
