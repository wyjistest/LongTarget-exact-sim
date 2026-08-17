# Phase 7 offline analysis correction 2

The second offline analysis attempt used the preregistered lite comparator,
which emits only one `top5_offline_cluster_*` view. The Phase 7 adapter expects
the full score, stability, Nt, boundary-tie, and full-row metric schema. All 26
eligible comparison receipts therefore failed closed with empty metric maps;
no receipt is admissible evidence.

Historical Phase 2 `attempt-config.json` files prove that the declared contract
was evaluated by `scripts/compare_fasim_segmented_contract.py`, SHA-256
`6a589d7960a69be7c84a410f1bbd9d3ea34de929f8f04943d9c7ae033d682eda`.
Correction 2 binds Phase 7 offline analysis to that same frozen comparator and
renames its baseline representative-conflict field exactly as emitted.

The 26 technical-failure receipts under `offline-comparison-v3` remain
immutable. Valid comparison receipts are written only under
`offline-comparison-v4`. The adapter now also records comparison status and
error explicitly so an empty metric map cannot reach source-data aggregation.

This correction starts zero backend attempts, changes no measurement or
scientific contract, consumes no new input, and leaves execution/measurement
repair use at 2 of 2. It does not alter the Phase 7 implementation no-go.
