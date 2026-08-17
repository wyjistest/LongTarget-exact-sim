# Exact SSW-CUDA Final Status

The final decision is `ssw_cuda_forward_or_reverse_checkpoint_only`.

Phases 0-6 passed. The project established exact, bounded GPU checkpoints for
L1/L2 pre-align and selection and for the L3 forward endpoint. Phase 7 did not
promote their integrated forward-hybrid: the first large chr21 observation
failed closed after one selected-only CPU continuation contract mismatch.
Phases 8-12 were therefore not authorized or run.

The Bioinformatics widening route remains closed independently by the Phase 1
Amdahl ceiling of 2.627762802x against the unchanged 10x target. The completed
Phase 7 overhead and medium observations were also slower than their historical
CPU references, with checkpoint reference ratios of 0.097064x and 0.046022x.

There is no full-GPU safe backend, fresh promotion holdout, formal B3 result,
application-panel result, CLI promotion, or release candidate. The default CPU
authority and historical verified paths remain the user-facing contracts.
Full-output equality remains diagnostic only.

The retained result is useful engineering evidence: exact L1-L3 CUDA kernels,
their differential corpora and API guards, a reproducible large-workload
continuation failure, and bounded negative performance evidence. It may support
a checkpoint or negative-results methods handoff, but not a safe acceleration
claim or a Bioinformatics-ready software release.
