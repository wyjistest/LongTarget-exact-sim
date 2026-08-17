# Phase 4 Exact SSW-CUDA Architecture Decision

## Decision

Status: `pass`

Selected candidate: **C, mixed in-tree design with checkpoint/recompute
traceback**.

All executable L1-L5 semantics will be implemented in this repository and
validated against the epoch-2 CPU oracle. Accelign and G3SA are design
references only; neither library is linked, copied into the product, or used as
an authority.

## Bounded spike result

Accelign was pinned at `c7ecd32d59e256716cca193556110051c171570f`
(Apache-2.0). Its affine local score/start/end example built on the first
attempt for `sm_89` with CUDA 12.5, although upstream documents CUDA 12.9 as
its tested minimum. The fixed self-check passed for eight 64x64 single-tile
alignments and two 2812x2812 multi-tile alignments. Scalar 32-bit score and
positions agreed with Accelign's own CPU reference; packed 16x2 results agreed
with its scalar path. This establishes upstream self-consistency on this host,
not SSW equivalence.

Accelign supplies useful one-to-one batch descriptors, cooperative thread
groups, length-tuned configurations, and single/multi-tile temporary-storage
patterns. It does not expose L1 per-column maxima or L2 selection. Its endpoint
reduction explicitly prefers smaller query end on score ties, while the frozen
SSW contract first retains the earliest reference column and then chooses the
smallest logical query coordinate. Its endpoint API therefore cannot be used
unchanged.

G3SA was pinned at `f0e0c130631dc2e06f92822b66c0494683f77eef`
(GPL-3.0). The first two minimap2 build attempts failed on an absolute CUDA
12.1 include and the missing host include path. The third and final allowed
attempt succeeded for `sm_89` after a two-line sandbox-only header portability
patch and an explicit `/usr/local/cuda/include` host flag. A `-h` invocation is
not supported, and a no-argument invocation detected the GPU then exited with
signal 11; no G3SA runtime correctness claim is made.

The source inspection is still decisive for the bounded design question.
G3SA stores H/E/F values on block rows and columns, then recomputes directions
inside a traversed 64x64 minimap2 block; its BWA `ksw_global3` path applies the
same broad idea to 16x16 grids. Both emit merged BAM CIGAR operations. Their
global/banded workflows, N penalty, E/F preference, gap open/extend ties,
boundary conditions, and KSW/GASAL rules differ from modified SSW. GPL and
bundled-component provenance are also not sufficiently audited for source
reuse. Only the checkpoint/recompute structure is retained as a design idea.

## Layer ownership

| Layer | Implementation owner | Permitted upstream influence |
| --- | --- | --- |
| L1 per-column maxima | In-tree exact kernels | Accelign cooperative tiling and length bins only |
| L2 scoreInfo selection | In-tree exact kernels | None; this is LongTarget-specific |
| L3 forward endpoint | In-tree exact kernels | Accelign batch descriptors and tile scheduling only |
| L4 reverse start | In-tree exact kernels | General reversed-input staging only |
| L5 banded CIGAR | In-tree dense oracle, then in-tree checkpoint/recompute | G3SA block-boundary storage/recompute shape only |

The first implementation at each layer remains a readable reference path.
Packed precision, pruning, fusion, or memory compression may follow only after
the corresponding exact differential gate passes.

## Candidate disposition

- **A, in-tree dense/reference kernels:** retained as the correctness ladder
  and fallback implementation, but rejected as the final architecture because
  dense L5 direction storage does not meet the intended memory envelope.
- **B, Accelign-style forward plus in-tree SSW semantics:** retained inside C
  as the forward scheduling plan, but rejected as a complete choice because it
  does not answer L5.
- **C, mixed in-tree design:** selected. It covers forward scheduling and a
  bounded L5 memory strategy without importing third-party semantics.

## Budgets and claim boundary

The spike used one Accelign build attempt and all three allowed G3SA build
attempts. GPU runtime was below one second for the successful Accelign checks;
external build wall time was below two minutes, well under the eight-hour GPU
budget. No additional upstream repair or architecture candidate is authorized
in this epoch.

This decision does not reopen Bioinformatics B3. The frozen Amdahl ceiling
remains 2.627762802x and `bioinformatics_b3_track` remains `closed_amdahl`.
Phase 5 may now implement L1/L2 under the engineering track.
