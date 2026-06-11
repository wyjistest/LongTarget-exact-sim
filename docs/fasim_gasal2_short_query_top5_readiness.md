# Fasim GASAL2 Short-Query Top5 Readiness

This checkpoint narrows the GASAL2 deliverable to the contract that currently
has strong evidence:

```text
short-query/H19 top5 scoreInfo artifact:
  scoped go

full Fasim output replacement:
  not proven

aligner.Align replacement:
  no-go in current evidence
```

## Reproducible GASAL2 Dependency

GASAL2 is no longer an unrecorded local dependency. The Fasim bridge records the
required upstream base and patch:

```text
repo: https://github.com/nahmedraja/GASAL2.git
commit: 106d94ee53fc847214fb05f2f9f892538a5d3baf
patch: patches/gasal2-fasim-bridge.patch
setup: scripts/setup_gasal2.sh
```

The patch captures the local changes needed by the bridge, including CUDA 12.5
build paths and per-alignment CIGAR offsets. `make build-fasim-gasal2` now runs
`setup-gasal2` before building GASAL2 and includes GASAL2 through
`-I$(GASAL2_DIR)/include`, not a hard-coded `.tmp/GASAL2` source path.

The reproducibility contract is checked by:

```bash
make check-fasim-gasal2-reproducible-setup
```

## Short-Query chr22 2Mb Gate

The active short-query/H19 path is:

```text
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
```

`PRUNE_MAX_PER_TASK=16` is too aggressive on the chr22 2Mb H19 slice and is a
top5 no-go:

```text
baseline_rows = 8294
candidate_rows = 5817
missing_rows = 2540
extra_rows = 76
top5_score_equal = false
top5_stability_equal = false
top5_nt_score_equal = false
```

The formal `64` cap is the current short-query contract:

```text
chr22_10m_12m, H19:
  baseline_rows = 8294
  candidate_rows = 8274
  missing_rows = 140
  extra_rows = 120
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
  top5_artifact_equal = true
  scoreinfo_pruned_groups = 1309
  traceback_requests = 173884
  GASAL2 total = 0.723777s
  baseline wall = 58.812301s
  candidate wall = 2.479681s
  speedup = 23.717688x
```

This proves a real GPU/GASAL2 top5 artifact path for checked short-query/H19
workloads. It does not prove full `.lite`, full TFO, endpoint, CIGAR, traceback,
or digest equivalence.

## Boundary

Keep this path default-off and scoped:

```text
Allowed:
  --gasal2-top5-column-pruned-scoreinfo
  top5 artifact contract
  CPU/Fasim authority outside that contract

Forbidden:
  claim aligner.Align replacement
  claim full output replacement
  use GASAL2 endpoint/CIGAR/traceback as authority
  use cap=16 as a correctness-clean chr22/H19 contract
```
