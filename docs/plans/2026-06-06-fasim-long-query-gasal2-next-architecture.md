# Fasim Long-Query GASAL2 Next Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prototype a different long-query architecture for GASAL2 scoreInfo/preAlign so MALAT1/NEAT1-like workloads can become GASAL2-active without promoting the stopped segmented/no-last implementation.

**Architecture:** Keep CPU fallback as authority while building a default-off exact-tile shadow. Export CPU oracle scoreInfo candidate identities, generate query-tile descriptors that fit the supported GASAL2 query bound, run GASAL2 score/preAlign work over those tiles, merge tile-local evidence into global candidate identities, and compare against CPU oracle candidates before any output use.

**Tech Stack:** C++11 Fasim runtime, GASAL2 static library with `GASAL2_MAX_QUERY_LEN=2812`, CUDA, existing top5 artifact comparison scripts, shell/Python characterization gates, Makefile.

---

Goal: Prototype a different long-query architecture.

## Boundary

The current segmented/no-last implementation remains stopped:

```text
current segmented/no-last implementation remains stopped
do not continue current segmented/no-last implementation as a real path
```

Already stopped or diagnostic-only paths:

```text
segmented long-query no-last replay
segmented GASAL2 traceback output
score-prepass stage-only output
single-pass topN scoreInfo
GASAL2_MAX_QUERY_LEN expansion
```

This plan is allowed only because it is a different architecture:

```text
query tiling with exact candidate equivalence
CPU oracle candidate export
tile descriptor generator
exact candidate equivalence shadow
```

CPU fallback remains authority. There is no production opt-in step, no
endpoint/CIGAR authority step, and no GASAL2 traceback output authority in this
plan.

full-output equivalence proof remains separate.

## Diagnostic Interface

Use a new default-off diagnostic flag:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1
```

The initial shadow must report:

```text
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_requested
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_active
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_query_len
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_len
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tiles
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptors
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_max_query_len
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptor_digest
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_cpu_oracle_candidates
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_candidates
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_candidate_missing
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_candidate_extra
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_fallback
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_total_seconds
```

## Decision Contract

The shadow can only produce a continuation signal if:

```text
scoreinfo_gasal2_active = 1
fallback = 0
top5 score/stability/nt_score clean
GPU/GASAL2 total < CPU fallback by a meaningful margin
candidate_missing = 0
candidate_extra = 0
```

Decision values:

```text
decision=next_architecture_not_implemented
decision=next_architecture_go
decision=next_architecture_no_go
```

## Task 1: Static Plan Gate

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_gasal2_long_query_next_architecture_plan.sh`
- Create: `docs/plans/2026-06-06-fasim-long-query-gasal2-next-architecture.md`

- [x] **Step 1: Write the failing plan checker**

Add `scripts/check_fasim_gasal2_long_query_next_architecture_plan.sh` to require
this plan, the current-stop checkpoint, and the composed current-state gate.

- [x] **Step 2: Verify red**

Run:

```bash
make check-fasim-gasal2-long-query-next-architecture-plan
make check-fasim-gasal2-long-query-current-stop
```

Expected before this plan exists:

```text
missing GASAL2 long-query next-architecture dependency
```

- [x] **Step 3: Add this plan**

Add the current document and cross-link it from:

```text
docs/fasim_gasal2_long_query_current_stop.md
docs/fasim_gasal2_full_goal_decision.md
docs/fasim_gasal2_scoreinfo_current_state.md
```

- [ ] **Step 4: Verify green**

Run:

```bash
make check-fasim-gasal2-long-query-next-architecture-plan
```

Expected:

```text
ok
```

## Task 2: CPU Oracle Candidate Export

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_long_query_exact_tile_oracle_export.sh`
- Modify: `Makefile`

- [x] **Step 1: Add the failing oracle export gate**

Create a gate that runs MALAT1 first8 with:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_ORACLE_EXPORT=1
```

Expected red before implementation:

```text
missing benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_cpu_oracle_candidates
```

- [x] **Step 2: Add default-off telemetry only**

Add telemetry that prints zeros when the flag is absent:

```text
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_requested=0
benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_active=0
```

- [x] **Step 3: Export CPU oracle candidate identities**

When the diagnostic flag is set, export the CPU scoreInfo candidate identity
surface without changing output:

```text
target record id
candidate output slot
global query start
global query end
target start
target end
score
scoreInfo rank
```

- [x] **Step 4: Verify oracle export**

Run:

```bash
make check-fasim-gasal2-long-query-exact-tile-oracle-export
```

Expected:

```text
cpu_oracle_candidates > 0
requested = 1
active = 0
output digest unchanged
```

Observed:

```text
digest=b51800fd831dd50fe8ea994e91e8b55c421b36f0c4550328b74316152fbf77cd
cpu_oracle_candidates=31272
tiles=4
ok
```

## Task 3: Tile Descriptor Generator

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_long_query_exact_tile_descriptors.sh`
- Modify: `Makefile`

- [x] **Step 1: Add the failing descriptor gate**

Run MALAT1 first8 and require descriptor telemetry:

```text
tile_len = 2812
tiles > 1
tile_descriptors > 0
all tile query lengths <= 2812
```

- [x] **Step 2: Generate deterministic query tiles**

Generate tile descriptors from the long query:

```text
tile_id
global_query_start
global_query_end
tile_query_len
overlap_left
overlap_right
```

- [x] **Step 3: Verify descriptor determinism**

Run the descriptor gate twice and compare descriptor digest:

```bash
make check-fasim-gasal2-long-query-exact-tile-descriptors
```

Expected:

```text
tile_descriptor_digest stable
output digest unchanged
```

Observed:

```text
digest=b51800fd831dd50fe8ea994e91e8b55c421b36f0c4550328b74316152fbf77cd
tile_descriptors=4
tile_max_query_len=2812
tile_descriptor_digest=16919590609729549896
ok
```

## Task 4: Exact Candidate Equivalence Shadow

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Create: `scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence.sh`
- Modify: `Makefile`

- [x] **Step 1: Add the failing candidate equivalence gate**

The gate must fail until tile candidates are mapped back to CPU oracle
candidates:

```text
candidate_missing = 0
candidate_extra = 0
```

- [ ] **Step 2: Run GASAL2 score/preAlign over tile descriptors**

Run GASAL2 against tile-local query strings and target windows. Map tile-local
query coordinates back to global query coordinates before comparison.

- [x] **Preflight result: non-overlap exact tiling is not candidate-equivalent**

Before promoting this to a GASAL2/GPU tile implementation, the diagnostic
candidate-equivalence path compared CPU full-query oracle scoreInfo candidates
against the union of exact non-overlap tile scoreInfo candidates. Output digest
remained unchanged, but candidate equivalence failed:

```text
cpu_oracle_candidates = 31272
tile_candidates = 31591
candidate_missing = 1720
candidate_extra = 2039
fallback = 0
```

This stops the current non-overlap exact-tile shape. A future implementation
must use a different candidate-equivalence strategy before performance
characterization is meaningful.

Overlap was also probed and remains no-go for simple tile-local candidate
union:

```text
overlap = 1406:
  candidate_missing = 1
  candidate_extra = 2591

overlap = 2048:
  candidate_missing = 1
  candidate_extra = 2961
```

The overlap result checkpoint is:

```bash
make check-fasim-gasal2-long-query-exact-tile-overlap-result
```

- [ ] **Step 3: Compare exact candidate identities**

Compare the GPU/GASAL2 tile candidate set against the CPU oracle candidate set.
Do not use GPU endpoint, CIGAR, traceback, candidate state, output, or digest.

- [ ] **Step 4: Verify candidate equivalence**

Run:

```bash
make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence
```

Expected:

```text
scoreinfo_gasal2_active = 1
fallback = 0
candidate_missing = 0
candidate_extra = 0
top5 score/stability/nt_score clean
```

The current no-go result checkpoint is checked by:

```bash
make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result
```

## Task 5: Performance Characterization

**Files:**
- Create: `scripts/characterize_fasim_gasal2_long_query_exact_tile_shadow.sh`
- Create: `scripts/check_fasim_gasal2_long_query_exact_tile_scaling_result.sh`
- Create: `docs/fasim_gasal2_long_query_exact_tile_shadow.md`
- Modify: `Makefile`

- [ ] **Step 1: Add the characterization script**

Run:

```text
MALAT1 first8
MALAT1 first32
MALAT1 first128
NEAT1 first64
```

- [ ] **Step 2: Collect timing**

Collect:

```text
CPU fallback wall seconds
tile pack seconds
GASAL2 score/preAlign seconds
candidate merge seconds
total seconds
candidate_missing
candidate_extra
top5 score/stability/nt_score
```

- [ ] **Step 3: Verify scaling decision**

Run:

```bash
make check-fasim-gasal2-long-query-exact-tile-scaling-result
```

Expected continuation threshold:

```text
GPU/GASAL2 total < CPU fallback by a meaningful margin
candidate_missing = 0
candidate_extra = 0
```

## Task 6: Decision Gate

**Files:**
- Create: `docs/fasim_gasal2_long_query_next_architecture_decision.md`
- Create: `scripts/check_fasim_gasal2_long_query_next_architecture_decision.sh`
- Modify: `Makefile`

- [ ] **Step 1: Record decision**

Decision rules:

```text
if candidate equivalence is clean and performance wins:
  decision=next_architecture_go

if candidate equivalence is clean but performance is marginal:
  decision=next_architecture_no_go

if candidate equivalence is not clean:
  decision=next_architecture_no_go

if the implementation is absent:
  decision=next_architecture_not_implemented
```

- [ ] **Step 2: Keep full goal honest**

The decision gate must update the full-goal audit. It must not mark the original
objective complete unless the verified scope proves scoreInfo/preAlign
GPU/GASAL2 replacement for the claimed workloads.

- [ ] **Step 3: Verify composed gate**

Run:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

Expected:

```text
short-query/H19 top5 milestone remains intact
current segmented/no-last implementation remains stopped
next architecture decision is explicit
full objective remains open unless replacement is proven
```
