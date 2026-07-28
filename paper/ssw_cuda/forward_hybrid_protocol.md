# Phase 7 Exact Forward-Hybrid Protocol

Status: preregistered, not run

## Purpose

Phase 7 tests `ssw_cuda_forward_hybrid_v1` as an engineering checkpoint:

```text
GPU L1 per-column maxima
+ GPU L2 scoreInfo and attempt selection
+ GPU L3 exact forward endpoint
+ selected-only CPU L4 reverse-start
+ selected-only CPU L5 banded traceback/CIGAR
+ unchanged LongTarget L6/L7 downstream
```

This phase does not reopen Bioinformatics B3. The Phase 1 conservative
addressable fraction remains `0.619448148`, its infinite-backend Amdahl ceiling
remains `2.627762802x`, and the original B3 threshold remains `>=10x`.

## Frozen arms and evidence roles

```text
A  = frozen Phase 1 epoch-2 profile-off CPU authority observations
H2 = historical canonical-hybrid-v2 performance receipt, track closed
F  = new ssw_cuda_forward_hybrid_v1 process executions
```

A already contains five observations on each of the five fixed development
workloads, using the same input files, host, and frozen authority semantics.
Those observations are imported as a checkpoint reference and are not rerun.
H2 remains the immutable 18-instance historical result with primary speedup
`0.25759196676394047x`, slowdown `3.8821086408972096x`, and status
`closed_performance_no_go`; no H2 process is rerun.

Because A and F are not newly paired in this phase, `A/F` values are named
`checkpoint_reference_ratio`. They are not a formal speedup claim and cannot
promote or rescue B3. The purpose of avoiding new A and H2 executions is to
prevent a redundant 50- or 75-process performance panel after those arms have
already been frozen.

## New execution scope

The machine-readable plan has exactly 49 new F attempts:

```text
24 consumed Phase 2 workload pairs x one correctness execution = 24
5 fixed development workloads x five F observations             = 25
total new F processes                                             = 49
new A processes                                                    = 0
new H2 processes                                                   = 0
```

The 24 correctness inputs are regression evidence, not fresh promotion data.
The five development workloads are:

```text
overhead_aq001_at0001
medium_h19_chr22_2mb
large_h19_chr21
large_h19_chr22
application_aq005_at0199
```

Observation 1 uses the same best-effort input cache hint as Phase 1; observations
2-5 are independent steady-state processes. Workload order and GPU mapping are
fixed in the plan. `FASIM_SSW_FORWARD_HYBRID_MAX_TASKS=16` is frozen from the
pre-plan correctness implementation and may not be tuned after any formal
attempt is observed.

Attempt-plan SHA-256:

```text
49e4f5984fdfa32ed38f169f033deb1016027e440860c5855c5130decbf04038
```

Offline comparator SHA-256:

```text
2765d76b6c8e742596b1072a413309a88ef415f3576c9de62be67213ee76dc80
```

## Isolation

Every F attempt is a separate process with a separate artifact root. Its argv
and environment contain only the F binary, frozen input paths, output path,
telemetry path, device, and fixed runtime parameters. The F process cannot read
an A or H2 output, digest, receipt, or comparator result. Reference artifacts
are read only by the offline comparison phase after all planned F processes
have terminated.

The runner takes no result-dependent branch that changes a later command,
input, parameter, device mapping, or timeout. The only prospective early stops
are a technical failure or exhaustion of the fixed total GPU wall budget.

## Authority boundary

The Phase 0 authority binary and all prior evidence remain immutable. The
existing `ssw_align()` and `Aligner::Align()` bodies are unchanged. The additive
`ssw_align_from_forward()` and `Aligner::AlignFromForward()` entry points are
compiled only when `FASIM_WITH_SSW_CUDA_FORWARD_HYBRID` is defined. The default
CPU binary does not contain the continuation API and rejects an explicit
`cuda-forward-hybrid` request rather than falling back.

The candidate continuation receives only the exact frozen L3 tuple. It must
record zero CPU pre-align calls and zero CPU forward calls. Every selected
attempt must record exactly one CPU reverse call and one CPU banded traceback
call. Any fallback, counter mismatch, invalid tuple, missing telemetry, or
continuation failure is a technical failure.

## Correctness gate

The preexecution checker reruns the 625-case continuation corpus, the 549-group
selection/continuation regression, the Phase 5 L1/L2 checker, and the Phase 6
L3 checker. Formal end-to-end outputs are compared offline with the frozen
cluster-distance-15, minimum-Nt-50 comparator.

Phase 7 correctness requires, for every completed planned attempt:

```text
score-ranked clustered Top-5 canonical rows equal
stability-ranked clustered Top-5 canonical rows equal
Nt-ranked clustered Top-5 canonical rows equal
boundary-tie diagnostics equal
CPU pre-align calls = 0
CPU forward calls = 0
CPU reverse calls = selected continuation calls
CPU banded traceback calls = selected continuation calls
fallbacks = 0
```

Full-output equality is reported only as L8 diagnostic evidence. It is never
used to upgrade the product contract.

## Telemetry

Each attempt records:

```text
command, environment, source commit, binary digest
input and output digests
return code, timeout, stdout, stderr, GNU time resource log
GPU samples and peak observed memory/temperature/power
GPU packing, H2D, pre-align, selection, forward, endpoint reduction, D2H
GPU unattributed overhead and workspace bytes
CPU substring, reverse-start, banded traceback, CIGAR, continuation
downstream conversion, cluster sort, filtering
all CPU SSW call counters and fallback count
artifact manifest and receipt digests
```

The projection uses observed F wall and measured selected CPU continuation:

```text
optimistic G wall = F wall - selected CPU continuation
conservative G wall = F wall
```

These bounds are a development model, not observed G timing.

## Failure, retry, and budget policy

```text
per-attempt timeout = 600 s correctness, 7200 s performance
total GPU wall budget = 43200 s
retry policy = none
replacement retry = forbidden
runner/measurement repair after formal start <= 2
```

Attempt roots, failed logs, timeout artifacts, partial output, and slow results
are never deleted or overwritten. A pre-existing formal root is a hard error.
There is no automatic resume. A failed or interrupted row remains failed; any
future repair requires a new versioned plan and does not replace this evidence.

Formal execution is forbidden until the implementation, this protocol, the
attempt plan, runner, checker, and tests are committed and the worktree is
clean.

## Allowed decisions

```text
forward_hybrid_checkpoint_pass_continue_full_gpu
forward_hybrid_correct_but_b3_track_closed
forward_hybrid_performance_futility_stop
blocked_by_environment
```

With the already-closed Amdahl gate, an exact F result yields
`forward_hybrid_correct_but_b3_track_closed`. It may authorize the bounded
methods-track Phase 8 implementation, but it cannot authorize Bioinformatics
B3 or the 50 x 668 application panel. No lower threshold may be introduced.

## Artifacts

Large artifacts are written under:

```text
.paper-artifacts/ssw-cuda-v1/forward-hybrid/
```

Committed evidence is generated only after execution:

```text
paper/ssw_cuda/forward_hybrid_source_data.tsv
paper/ssw_cuda/forward_hybrid_projection.json
paper/ssw_cuda/forward_hybrid_decision.json
```
