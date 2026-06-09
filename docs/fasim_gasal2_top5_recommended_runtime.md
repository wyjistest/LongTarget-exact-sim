# Fasim GASAL2 Top5 Recommended Runtime

This document records the GASAL2 top5 recommended runtime for the scoped
scoreInfo/preAlign path.

It is a default-off opt-in runtime, not a broad production default.

## Command

Use a GASAL2-enabled Fasim binary:

```bash
make build-fasim-gasal2
```

Recommended short-query/H19 invocation:

```bash
env -u FASIM_CUDA_DEVICES \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_gasal2 \
  --target targets.fa \
  --rna H19.fa \
  --rule 0 \
  --work-dir .tmp/fasim_gasal2_top5 \
  --output-mode lite \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers 2 \
  --gpu-ids 0,1 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest run_manifest.json
```

For many-record tiny-region targets such as MEG3 grouped, add complete-record
grouping:

```bash
  --group-target-records 32
```

This is grouping complete FASTA records. It is not chunking, overlap, or an
in-process multi-GPU runtime.

The same recommended surface is available through the topK-lite wrapper:

```bash
AUTO_CPU_CORE_RANGES=1 \
CPU_POOL=0-19 \
CPU_CORES_PER_WORKER=3 \
GROUP_TARGET_RECORDS=32 \
DNA=targets.fa \
RNA=H19.fa \
OUT=.tmp/fasim_gasal2_top5 \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

`run_fasim_gasal2_topk_lite.sh` forwards those CPU-affinity settings to the
formal sharded runner while keeping the same `--gasal2-top5-column-pruned-scoreinfo`
contract.

For manifest resume through the wrapper:

```bash
RESUME=1 \
FORCE=0 \
DNA=targets.fa \
RNA=H19.fa \
OUT=.tmp/fasim_gasal2_top5 \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

The wrapper forwards `RESUME=1` as `--resume`. `RESUME=1` must be used with
`FORCE=0`; `RESUME=1 FORCE=1` fails closed before invoking the runner. In
resume mode the wrapper does not clear `OUT`, so manifest-compatible shards can
be reused and `top5.lite`/`summary.tsv` are regenerated from the resumed report.
The wrapper summary records `shard_count` and `resumed_shards_count`, so resume
reuse is visible without opening `report.json`.

## Output Contract

The preset is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

It emits:

```text
result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
```

The contract artifacts are:

```text
topk_summary.tsv
topk_rows.tsv
topk-TFOsorted.lite
report.json
run_manifest.json
```

## Recommended When

This runtime is recommended when:

```text
recommended when:
  short-query/H19 workload
  top5 broader workload validation passes
  top5 product-readiness passes
  top5 score/stability/nt_score payload is the required output
```

The checked positive set is:

```text
small chr22 slice
chr21+chr22
MEG3 grouped
```

## Not Recommended When

This runtime is not recommended when:

```text
not recommended when:
  MALAT1/NEAT1
  query_len > GASAL2_MAX_QUERY_LEN
  scoreinfo_gasal2_active = 0
  wrapper fails closed before report/summary output
  full `.lite` output equivalence is required
  final all-row TFO equivalence is required
  endpoint/CIGAR/traceback authority is required
```

This runtime is not `aligner.Align()` replacement and not GPU
endpoint/CIGAR/traceback authority.

## Decision

```text
short-query/H19 top5:
  recommended as default-off opt-in

MEG3 grouped:
  recommended with --group-target-records 32 when the grouped gate is clean

MALAT1/NEAT1:
  no real GASAL2 path
  GASAL2 selected/expanded segment traceback: no-go for real path

default production:
  not broad production default

full objective:
  full objective remains open
```

## Gate

Focused gate:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

Focused release smoke:

```bash
make check-fasim-gasal2-top5-release-smoke
```

Composed gate:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```
