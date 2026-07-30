# Frozen Operating Envelope

## Runtime and inputs

The contract runtime is normal-triplex fast Top-K with CPU fast-Top-K authority
and canonical-hybrid-v2 candidate modes. Query length is 500 through 2,812
bases. Query input alphabet is ACGT; target and normalized output alphabets are
ACGTN. The three target recipes are 4,097, 2,000,001, and 10,000,001 bp.

Frozen parameters include K 5, cluster distance 15, strict `Nt(bp)>50`, cut
length 5,000, overlap 100, minimum identity 60, minimum stability 1, score
minimum 0, Nt runtime range 20 through 100,000, penalty T -1000, penalty C 0,
all rules, and all strands. The exact parameter-bundle SHA-256 is in
`paper/biological_topk/operating_envelope.json`.

## Hardware and scheduling

The frozen host inventory has two NVIDIA GeForce RTX 4090 GPUs, 24,564 MiB
each, compute capability 8.9, driver 555.42.06, CUDA 12.5, one worker per GPU,
and two logical workers. Batch size is 20,000 with three GASAL2 streams and a
score-info prune maximum of 256 per task. The only hardware generality claim is
the RTX 4090 generation.

OOM, unexpected fallback, and unsupported input are technical failures. There
is no retry that can remove a preregistered workload from the binary
denominator.

## Resource projection

The input-only ridge log-response model uses query and target lengths, their
product, static complexity proxies, stratum, and execution configuration. It is
fit only to historical timing/storage observations and uses 10,000 stratified
workload bootstraps (seed 20260810), a nonnegative within-stratum 95th residual,
and a fixed two-worker 1.10 inefficiency scheduler.

For candidate panel 178, the 95% upper projections are 35,416.83 aggregate CPU
seconds, 2,020.90 aggregate GPU seconds, 0.5614 GPU-hours, 20,576.31 scheduled
seconds, and 5,508,762,270 artifact bytes. The 48-hour and 72-GPU-hour gates
pass. Only one chromosome-scale resource observation exists and target-scale
effects are partly aliased with historical execution configuration; projections
are planning controls, not performance claims.

The owner approved a fixed 8 GiB artifact-storage quota
(`8589934592` bytes), recorded in
`paper/biological_topk/owner_storage_quota_approval.json`. The projected upper
bound is below that quota, so the storage and fixed-budget gates pass. The quota
may not be raised after a Phase 3 manifest projection.
