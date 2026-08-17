# Phase 6 Exact SSW-CUDA Forward Endpoint Design

## Scope and claim boundary

Phase 6 implements L3 of the frozen modified-SSW contract:

```text
score1, ref_end1, read_end1, score2, ref_end2, final_numeric_path
```

The CPU SSE2 `Align()` path remains the authority. This checkpoint does not
implement reverse start, banded traceback, CIGAR, emitted rows, a production
backend, a fresh holdout, or an application-speed claim. The default Fasim
binary does not link the Phase 6 CUDA object. The Bioinformatics B3 route
remains closed by the Phase 1 Amdahl ceiling of `2.627762802x`.

## Exact forward implementation

The Phase 5 striped recurrence is shared through
`fasim/ssw_cuda/ssw_cuda_striped.cuh`. The Phase 6 entry point executes a
complete forward pass on GPU and retains the H lanes from the first reference
column that establishes a strictly greater global score. It maps striped lanes
back to query coordinates exactly as frozen in `docs/ssw_cuda/ENDPOINT_CONTRACT.md`
and selects the smallest logical query coordinate equal to `score1`.

The byte pass uses 16 lanes, unsigned saturation, bias 4, the historical
signed lazy-F stop comparison, and the frozen padding behavior. The authority
reports the byte overflow sentinel when `maximum + bias >= 255`; Phase 6 then
recomputes the complete task with the 8-lane word path. This means final scores
253-256 in the frozen adversarial corpus use `word16`, even though Phase 5's
separate pre-align routine can retain a byte column vector for part of this
range.

`score2/ref_end2` are reduced in increasing reference order with strict `>`
replacement. Equal scores retain the first coordinate. The byte path resumes
after `edge + 1`; the word path resumes at `edge`. This historical mask-boundary
difference is explicit in the kernel and tests.

One CUDA thread owns one complete task in this correctness checkpoint. There
is no case ID, sequence digest, gene name, allowlist, blacklist, CPU endpoint
call, fallback, or result-dependent path in production CUDA code.

## Pre-align versus full-forward columns

Phase 5 L1 freezes `ssw_pre_align()` column maxima. Phase 6 L3 is defined by
the distinct full `ssw_align()` forward pass. The two CPU routines are not
interchangeable near byte saturation: the frozen 253-256 cases have different
pre-align and full-forward vectors while producing exact Phase 6 endpoints.

Accordingly:

- CPU `Align()` supplies the formal L3 endpoint authority;
- Phase 5 pre-align versus Phase 6 forward vector equality is diagnostic only;
- the standalone GPU reducer replays the exported full-forward vector;
- two Phase 2 CPU-oracle full-forward vectors, hq10 and hq11, independently
  test reducer score, reference endpoint, mask, and tie semantics.

No pre-align vector difference is counted as an L3 mismatch or used to rewrite
the already-passed Phase 5 L1 contract.

## APIs and fail-closed behavior

`forward_align()` returns independent per-task endpoints, optional full-forward
column vectors, and telemetry. `reduce_forward_columns()` accepts explicit
frozen column vectors for isolated reducer validation. Supported CUDA paths
must report `cpu_endpoint_calls = 0`.

Both APIs reject empty batches, invalid bases or numeric paths, non-frozen
scoring/mask settings, overlength queries, DP capacity overflow, invalid
devices, forced or real allocation failures, and CUDA runtime failures. The
non-CUDA stub returns `not_built` for both APIs and never executes CPU work
under a CUDA backend label.

## Frozen formal matrix

The machine-readable plan is
`paper/ssw_cuda/forward_endpoint_attempt_plan.tsv`, SHA-256:

```text
dbbe24ebc46282a66fdbbcab200cc83e6d7c3d7755b15d3b683f9bf00fab5e41
```

It contains 31 non-retry attempts:

| Evidence block | Unique cases | Repeats / GPUs | GPU task executions |
| --- | ---: | ---: | ---: |
| Tiny exhaustive | 196 | 1 | 196 |
| Compact adversarial | 30 | 1 | 30 |
| Compact deterministic fuzz | 128 | 1 | 128 |
| Historical full-pair and endpoint-call regression | 4 | 1 | 4 |
| Large deterministic/adversarial | 267 | 1 | 267 |
| Determinism subset | 18 | 10 | 180 |
| Same-model cross-device subset | 18 | 2 GPUs | 36 |
| **Supported full-forward task executions** |  |  | **841** |
| Frozen CPU-vector reducer tasks | 2 | 1 | 2 |

Eight forward-API and five reducer-API attempts must fail closed. The four raw
unsupported corpus inputs remain covered by the committed Phase 5 gate; Phase 6
does not recast parser rejection as a new L3 execution.

The two added endpoint-call inputs are reconstructed before execution from the
frozen Phase 2 fixtures and consumed holdout FASTA files:

```text
hq10: rule 5, strand 0, target window 512 + 69
       expected (score1, ref_end1, read_end1, score2, ref_end2)
              = (68, 68, 1751, 60, 52)
hq11: rule 12, strand 1, target window 2169 + 84
       expected = (93, 83, 790, 78, 64)
```

The fixed 18-case repeat subset is the Phase 5 16-case subset plus these two
endpoint calls. Input identity, order, transforms, commands, devices, timeouts,
and artifact roots are frozen before execution.

## Budgets and execution discipline

```text
mechanism repair iterations <= 3
observed Phase 6 mechanism repair iterations before formal run = 0
GPU budget <= 24 hours
retry policy = none
large formal batch timeout = 1800 seconds
all other supported batch timeouts = 300 seconds
fail-closed timeout = 60 seconds
```

Code, plan, tests, runner, checker, and this design must be committed, and the
worktree must be clean, before `--run-formal`. Every attempt uses an independent
non-overwriting artifact root and records input, command, environment, source
commit, binary digest, stdout, stderr, GNU-time resource log, return code,
timeout, retry/fallback status, and a checksummed manifest.

No `50 x 668` application panel or fresh holdout is authorized in Phase 6.

## Pass and stop rules

Phase 6 passes only if all of the following hold:

- 625/625 primary full-GPU endpoints equal CPU `Align()` in all L3 fields;
- both frozen CPU full-forward vectors reduce to their exact endpoints;
- all 841 supported task executions have zero endpoint/reducer mismatch;
- the 18-case subset is stable across 10 repeats and equal on both RTX 4090s;
- supported CUDA paths record zero CPU endpoint calls, fallback, retry, timeout,
  OOM, and technical failure;
- all 13 API probes fail closed and the fixed GPU budget is respected.

After at most three mechanism-level repairs, any remaining L3 mismatch closes
the exact-forward track as `no_go`; it cannot be hidden by weakening endpoint
identity or by excluding a case.
