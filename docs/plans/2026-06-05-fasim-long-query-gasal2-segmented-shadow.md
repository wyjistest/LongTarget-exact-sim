# Fasim Long-Query GASAL2 Segmented Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prototype a default-off segmented GASAL2 shadow for long-query scoreInfo/preAlign workloads, starting with MALAT1, without changing Fasim production output.

**Architecture:** Keep the current formal short-query preset unchanged. For long queries, split the query into bounded GASAL2-compatible segments, run diagnostic GASAL2 score/traceback work per segment, translate segment-local query coordinates back to global query coordinates, and compare top5 artifacts against CPU fallback authority. The prototype is shadow-only until top5 score/stability/nt_score equivalence and speed beat CPU fallback.

**Tech Stack:** C++11 Fasim runtime, GASAL2 static library built with the current `GASAL2_MAX_QUERY_LEN=2812`, CUDA, existing topK artifact checker, shell/Python characterization scripts, Makefile gates.

---

## Boundary Facts

Current accepted state:

```text
short-query H19/MEG3:
  GASAL2 + exact scoreInfo GPU active
  formal top5 contract clean

long-query MALAT1/NEAT1:
  current formal path guarded out
  CPU fallback remains authority
```

Do not repeat the no-go max-query path:

```text
GASAL2_MAX_QUERY_LEN=8708:
  batch=20000, streams=3 -> CUDA OOM
  batch=128, streams=1 -> top5_stability_equal=false and slower than CPU
```

The prototype must keep:

```text
GASAL2_MAX_QUERY_LEN=2812
FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812
```

## Proposed Diagnostic Interface

Add these default-off diagnostic envs:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1
FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812
FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512
FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=0
```

`MAX_SEGMENTS=0` means unlimited. The initial gate may cap it in scripts to keep
small probes bounded.

Required telemetry:

```text
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_requested
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_active
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_query_len
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_len
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_overlap
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_segments
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_gasal2_requests
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_traceback_requests
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_cpu_reference_seconds
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_total_seconds
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_top5_score_equal
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_top5_stability_equal
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_top5_nt_score_equal
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_fallbacks
```

## Task 1: Add Static Env/Telemetry Gate

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh`
- Create or modify: `docs/fasim_gasal2_long_query_segmented_shadow.md`

- [x] **Step 1: Write the static check script**

Create `scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_long_query_segmented_shadow.md"

if [[ ! -s "$DOC" ]]; then
  echo "missing segmented shadow doc: $DOC" >&2
  exit 1
fi

python3 - "$DOC" <<'PY'
import sys
from pathlib import Path

text = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
required = [
    "FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1",
    "FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812",
    "FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512",
    "FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=0",
    "CPU fallback remains authority",
    "not production output",
    "top5_score_equal = true",
    "top5_stability_equal = true",
    "top5_nt_score_equal = true",
    "GPU total < CPU fallback",
]
missing = [phrase for phrase in required if phrase not in text]
if missing:
    raise SystemExit("segmented shadow doc missing phrases: " + ", ".join(missing))
PY

echo "ok"
```

- [x] **Step 2: Verify red**

Run:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-env
```

Expected before the doc and Makefile target exist: fail because the target or
document is missing.

- [x] **Step 3: Add the Makefile target**

Add:

```make
check-fasim-gasal2-long-query-segmented-shadow-env:
	bash ./scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh
```

Add the target to `.PHONY`.

- [x] **Step 4: Add the design doc**

Create `docs/fasim_gasal2_long_query_segmented_shadow.md` with:

```text
scope:
  default-off diagnostic only
  CPU fallback remains authority
  no production output use
  no formal preset change
  no GASAL2_MAX_QUERY_LEN increase

gate:
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
  scoreinfo_gasal2_active = 1
  fallback = 0
  GPU total < CPU fallback
```

- [x] **Step 5: Verify green**

Run:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-env
git diff --check -- Makefile docs/fasim_gasal2_long_query_segmented_shadow.md scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh
```

Expected: both pass.

## Task 2: Add Runtime Default-Off Telemetry Stub

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `Makefile`
- Create: `scripts/check_fasim_gasal2_long_query_segmented_shadow_default_off.sh`

- [x] **Step 1: Add failing default-off check**

Create `scripts/check_fasim_gasal2_long_query_segmented_shadow_default_off.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_shadow_default_off"}"

if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

env FASIM_OUTPUT_MODE=lite FASIM_VERBOSE=0 \
  "$BIN" \
  -f1 "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa" \
  -f2 "$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
  -r 0 \
  -O "$WORK/default_off" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

grep -Eq '^benchmark\.fasim_top5_gasal2_long_query_segmented_shadow_requested=0$' "$WORK/stderr.log"
grep -Eq '^benchmark\.fasim_top5_gasal2_long_query_segmented_shadow_active=0$' "$WORK/stderr.log"
```

- [x] **Step 2: Verify red**

Run:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-default-off
```

Expected before telemetry stub exists: fail because metrics are absent.

- [x] **Step 3: Add telemetry fields**

In `fasim/Fasim-LongTarget.cpp`, add cached env helper:

```cpp
static inline bool fasim_gasal2_long_query_segmented_shadow_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW");
		return env != NULL && env[0] != '\0' && env[0] != '0';
	}();
	return enabled;
}
```

Add benchmark output defaults:

```text
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_requested
benchmark.fasim_top5_gasal2_long_query_segmented_shadow_active
```

Default-off runs must print `0` for both.

- [x] **Step 4: Wire Makefile target**

Add:

```make
check-fasim-gasal2-long-query-segmented-shadow-default-off:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_segmented_shadow_default_off.sh
```

Add the target to `.PHONY`.

- [x] **Step 5: Verify green**

Run:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-default-off
make check-fasim-gasal2-top5-formal-gate
```

Expected: default-off telemetry appears and the formal short-query gate remains
unchanged.

## Task 3: Add Bounded MALAT1 Characterization Script

**Files:**
- Create: `scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh`
- Create: `scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh`
- Modify: `Makefile`

- [x] **Step 1: Create characterization script**

The script should run CPU fallback authority and segmented-shadow candidate for
MALAT1 first8:

```bash
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1 \
  FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN=2812 \
  FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP=512 \
  FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS=4 \
  "$BIN" -f1 "$MALAT1_FIRST8" -f2 "$MALAT1_RNA" -r 0 -O "$CANDIDATE_DIR"
```

It must compare candidate against CPU with:

```bash
python3 scripts/compare_fasim_lite_topk.py \
  --baseline "$CPU_LITE" \
  --candidate "$CANDIDATE_LITE" \
  --k 5
```

- [x] **Step 2: Add no-claim probe check**

`scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh` must require:

```text
query_len = 8708
tile_len = 2812
segments > 1
```

It must not require success until the implementation exists. If the candidate is
inactive, the check should print `decision=not_implemented` and exit `0`.

- [x] **Step 3: Add Makefile targets**

Add:

```make
characterize-fasim-gasal2-long-query-segmented-shadow:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh

check-fasim-gasal2-long-query-segmented-shadow-probe:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh
```

- [x] **Step 4: Verify**

Run:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-probe
```

Expected before implementation: `decision=not_implemented`, exit `0`.

## Task 4: Implement Shadow-Only Segment Descriptor Collection

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `docs/fasim_gasal2_long_query_segmented_shadow.md`

- [x] **Step 1: Add descriptor structs**

Add C++ structs for diagnostic descriptors only:

```cpp
struct FasimGasal2LongQuerySegment
{
	size_t global_query_start;
	size_t global_query_end;
	std::string query_segment;
};

struct FasimGasal2LongQueryShadowStats
{
	uint64_t requested;
	uint64_t active;
	uint64_t query_len;
	uint64_t tile_len;
	uint64_t tile_overlap;
	uint64_t segments;
	uint64_t gasal2_requests;
	uint64_t traceback_requests;
	uint64_t fallbacks;
	double total_seconds;
};
```

- [x] **Step 2: Add segment builder**

Add a pure helper:

```cpp
static std::vector<FasimGasal2LongQuerySegment>
fasim_build_gasal2_long_query_segments(const std::string &query,
                                       size_t tile_len,
                                       size_t overlap,
                                       size_t max_segments)
```

Rules:

```text
tile_len > 0
overlap < tile_len
segments cover query in deterministic order
each segment length <= tile_len
global_query_start/global_query_end are zero-based half-open offsets
```

- [x] **Step 3: Unit-test segment boundaries via script-visible telemetry**

Use MALAT1 first8 with `MAX_SEGMENTS=4`. Expected:

```text
query_len = 8708
tile_len = 2812
tile_overlap = 512
segments = 4
```

- [x] **Step 4: Keep output untouched**

The implementation must not change:

```text
candidate state
merged output
digest
topk_summary artifact
formal short-query preset
CPU fallback authority
```

## Task 5: Add Segment GASAL2 Execution Shadow

**Files:**
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh`

- [x] **Step 1: Run GASAL2 per segment**

For each segment:

```text
use query_segment as the GASAL2 query
keep target descriptors unchanged
translate query_start/query_end by global_query_start after traceback
record GASAL2 requests and traceback requests
do not feed results into production output
```

- [x] **Step 2: Compare top5 artifacts**

The probe check should classify:

```text
top5_artifact_go:
  top5_score_equal=true
  top5_stability_equal=true
  top5_nt_score_equal=true
  active=1
  fallbacks=0
  GPU total < CPU fallback

top5_artifact_no_go:
  any top5 mode differs
  or fallbacks > 0
  or GPU total >= CPU fallback
```

- [x] **Step 3: Verify MALAT1 first8**

Run:

```bash
make check-fasim-gasal2-long-query-segmented-shadow-probe
```

Expected acceptable outcomes:

```text
decision=top5_artifact_go
decision=top5_artifact_no_go
```

`decision=top5_artifact_go` is required before any follow-up considers
production use.

## Task 6: Re-run Formal Gates

**Files:**
- No new files.

- [x] **Step 1: Run focused gates**

Run:

```bash
make check-fasim-gasal2-long-query-boundary
make check-fasim-gasal2-top5-output-contract
make check-fasim-gasal2-top5-scoreinfo-milestone
make check-fasim-gasal2-long-query-segmented-shadow-probe
```

- [x] **Step 2: Run formal gate**

Run:

```bash
make check-fasim-gasal2-top5-formal-gate
```

- [x] **Step 3: Run hygiene**

Run:

```bash
bash -n scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh \
       scripts/check_fasim_gasal2_long_query_segmented_shadow_default_off.sh \
       scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh \
       scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh
python3 -m py_compile scripts/fasim_sharded_runner.py scripts/check_topk_summary_digest_integrity.py
git diff --check -- Makefile docs/fasim_gasal2_long_query_segmented_shadow.md scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh scripts/check_fasim_gasal2_long_query_segmented_shadow_default_off.sh scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh
```

## Stop Conditions

Stop the long-query GASAL2 line if:

```text
segmented shadow changes top5 stability
segmented shadow needs full output authority before top5 equivalence is proven
segmented shadow is slower than CPU fallback
segment merge cannot deterministically translate query coordinates
GASAL2 fallback or overflow appears
```

Continue only if:

```text
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
scoreinfo_gasal2_active = 1
fallback = 0
GPU total < CPU fallback
```

## Self-Review

Spec coverage:

```text
covered:
  long-query MALAT1/NEAT1 boundary remains no-go for max-query increase
  short-query formal preset remains unchanged
  next implementation is segmented shadow-only
  CPU fallback remains authority
  top5 contract is the only allowed comparison target
  performance and correctness gates are explicit
```

Placeholder scan:

```text
no unresolved placeholder tokens
no production opt-in step
no endpoint/CIGAR authority step
```

Type consistency:

```text
env names, Makefile target names, and telemetry names are repeated consistently
across tasks
```
