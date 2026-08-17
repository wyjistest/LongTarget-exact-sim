# Exact long-query hybrid real-promoter panel v1

This stage is downstream of checkpoint `500b010`. It does not modify the
frozen `61da9b6` runtime or reopen Bioinformatics v2.

## Preexecution state

```text
shake_down_authorized = true
formal_panel_authorized = false
production_authorized = false
```

Six queries were selected only by fixed length targets after applying the
frozen historical-exclusion ledger:

| Stratum | Gene | Length | Required dynamic shared memory |
| --- | --- | ---: | ---: |
| 4_6kb | LCAL1 (ENSG00000286042) | 4,498 nt | 27,072 bytes |
| 4_6kb | AC025171.2 (ENSG00000215068) | 5,465 nt | 32,832 bytes |
| 7_9kb | AP002026.1 (ENSG00000246090) | 7,494 nt | 45,120 bytes |
| 7_9kb | AC008555.2 (ENSG00000269086) | 8,481 nt | 51,072 bytes |
| 10_13kb | AC246817.2 (ENSG00000254319) | 10,350 nt | 62,208 bytes |
| 10_13kb | SUCLG2-AS1 (ENSG00000241316) | 11,122 nt | 66,816 bytes |

The formal target is the complete 164,917,643 bp canonical concat. The nine
shards are identity and reconstruction artifacts only: independent shard
execution is not substituted because no validated merge preserves global
TFOsorted order and DBD tie semantics.

Before the 36 formal runs, LINC01501 x shard_0009 must pass paired raw-output,
GPU accounting, coordinate mapping, DBD/DBS/affinity, and positive boundary
fixtures. Passing the shake-down permits a separate execution addendum; it
does not itself authorize production.

Tracked preexecution artifact SHA-256 values are in `checksums.sha256`.
