# Real-promoter validation harness

This harness consumes the frozen `61da9b6` binary from checkpoint `500b010`.
It does not rebuild or modify the runtime.

## Layers

1. `run_exact_long_query_hybrid_promoter_case_v1.py` runs one frozen execution
   matrix row. Formal rows remain blocked until a tracked
   `formal_execution_addendum.json` explicitly authorizes them.
2. `decode_exact_long_query_hybrid_promoter_case_v1.py` validates every TFO and
   TTS against the source FASTAs, removes exact duplicate rows, converts shard
   coordinates to canonical logical-concat coordinates, and rejects
   cross-component, reference-N, and non-promoter hits before clustering.
3. `compare_exact_long_query_hybrid_promoter_pair_v1.py` requires raw complete
   `TFOsorted` byte equality, independently decodes both arms, runs the frozen
   eLife 89001 DBD1/DBS/affinity builder at threshold zero, and independently
   generates `biological_topk_candidate_site_v1` products from retained hits.

The pair gate compares these artifacts byte-for-byte:

- complete raw `TFOsorted`;
- decoded logical-concat rows, mapped promoter associations, rejected hits,
  and retained rows;
- DBD1, the complete threshold-zero DBS peak set, promoter affinity pairs, and
  target-gene affinity pairs;
- all three frozen Top-5 candidate-site rankings.

## Authorized shake-down

The only pre-formal runtime authorization is:

```text
workload = shake_ENSG00000229613_shard_0009
query    = LINC01501 / ENSG00000229613 / 4,006 nt
target   = shard_0009 / 4,942,620 bp
repeats  = one CPU baseline plus one exact-hybrid candidate
```

Example commands, with case roots chosen by the operator:

```bash
python3 scripts/run_exact_long_query_hybrid_promoter_case_v1.py \
  --workload-id shake_ENSG00000229613_shard_0009 \
  --arm baseline --repeat 1 --gpu 0 --cpu-set 18 \
  --output /path/to/shake/baseline_1

python3 scripts/run_exact_long_query_hybrid_promoter_case_v1.py \
  --workload-id shake_ENSG00000229613_shard_0009 \
  --arm candidate --repeat 1 --gpu 0 --cpu-set 18 \
  --output /path/to/shake/candidate_1

python3 scripts/compare_exact_long_query_hybrid_promoter_pair_v1.py \
  --baseline-root /path/to/shake/baseline_1 \
  --candidate-root /path/to/shake/candidate_1 \
  --output-root /path/to/shake/pair \
  --promoter-root /data/wenyujianData/linjieData/promoter_sequences/human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1
```

Shake-down timing is diagnostic only while unrelated CPU work is active.

## Formal gate

The 36 full-concat runs remain unauthorized until the shake-down receipt has:

```text
status = pair_gate_pass
all raw/mapping/DBD/DBS/affinity/candidate-site equality gates = true
candidate GPU coverage complete
CPU all-attempt oracle/replay = 0
selected continuation failures = 0
```

Passing this gate permits a separate tracked execution addendum. It does not
authorize production use or change the Bioinformatics v2 state.
