# Formal panel runner

`run_exact_long_query_hybrid_promoter_formal_panel_v1.py` executes the 36 rows
authorized by `formal_execution_addendum.json` as 18 paired work units:

```text
CPU complete TFOsorted
-> exact-hybrid complete TFOsorted
-> raw/mapping/DBD/DBS/affinity/candidate-site pair gate
```

The default resources are:

```text
slot 0: GPU 0, CPU 0
slot 1: GPU 1, CPU 19
```

The 18 pairs are sorted by estimated pair time from long to short and assigned
with deterministic longest-processing-time balancing. The frozen planning
loads are approximately 47.6 and 47.0 hours. Together with the existing
16-thread OpenMP production worker, the two formal slots keep total intended
CPU occupancy at 18 threads and leave two CPU threads unused.

Run:

```bash
python3 scripts/run_exact_long_query_hybrid_promoter_formal_panel_v1.py
```

After interruption, use the identical slot configuration and:

```bash
python3 scripts/run_exact_long_query_hybrid_promoter_formal_panel_v1.py --resume
```

Resume accepts only complete, identity-matching receipts. An existing partial
case or pair directory blocks continuation and must be audited; it is never
deleted or silently overwritten. The saved `schedule.tsv` must also match the
requested resource configuration.

Runtime status is written atomically to `state.json`, and transitions are
appended to `events.jsonl`. Any case or pair-gate failure stops that slot and
prevents both slots from taking new work after their current work unit. A
successful panel ends with `summary.json`, 18 passed pair receipts, and
three-repeat raw-output determinism for all six queries.

Formal panel execution remains an experimental scientific validation. Its
timings run alongside unrelated production work and are diagnostic rather than
the separately controlled performance contract.
