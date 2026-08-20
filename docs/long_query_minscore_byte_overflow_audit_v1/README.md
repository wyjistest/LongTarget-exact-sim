# Long-query min-score byte overflow audit v1

## Decision

```text
weighted overflow distribution = favorable
existing endpoint byte kernel = performance NO-GO for min-score
compact uint8 global-state bounded spike = authorized
production byte fast path = not authorized
```

The audit is default-off instrumentation on top of the exact F1 runtime.  For
one frozen 4,096-task min-score batch, it runs the current word16 global-state
authority and the already exact byte endpoint plus selective word16 replay,
then records task- and DP-cell-weighted replay by rule, strand, and parameter.

Implementation and binary binding:

```text
commit  115c3fc0002b0ae04939740d27ed69f7334db015
binary  3c2ed3c0bc4391e2f865868cb64365ab5d481b126e4797158fb8dfc1c150e998
```

The binary rebuilt byte-for-byte after the implementation commit.

## Frozen results

| Query | DP cells | Word16 replay tasks | Replay cells | Weighted replay | Score mismatches |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4,006 nt | 82,042,880,000 | 0 / 4,096 | 0 | 0% | 0 |
| 8,181 nt | 167,546,880,000 | 6 / 4,096 | 245,430,000 | 0.146484375% | 0 |
| 12,397 nt | 253,890,560,000 | 44 / 4,096 | 2,727,340,000 | 1.07421875% | 0 |

The nonzero strata were sparse:

```text
8,181 nt:
  rule 2, strand 1, para -1: 3 tasks
  rule 3, strand 1, para -1: 2 tasks
  rule 5, strand 1, para -1: 1 task

12,397 nt:
  rule 5,  strand 0, para  1:  1 task
  rule 9,  strand 0, para -1: 18 tasks
  rule 9,  strand 1, para -1: 22 tasks
  rule 12, strand 1, para -1:  3 tasks
```

All three complete `TFOsorted` files match their frozen CPU/F1 authority
digests.  F1 pipeline failures and all GPU fallbacks were zero.

## Why the current byte kernel is not the candidate

The current exact byte endpoint kernel was slower than the word16 global-state
authority in this min-score use:

| Query | Authority wall | Byte plus replay wall | Ratio |
| ---: | ---: | ---: | ---: |
| 4,006 nt | 0.428757 s | 1.012450 s | 2.361361 |
| 8,181 nt | 1.957800 s | 4.132470 s | 2.110772 |
| 12,397 nt | 3.028470 s | 12.030300 s | 3.972402 |

It has a shared endpoint-oriented layout and is not a min-score fast path.
Low replay density therefore authorizes only a new bounded kernel with compact
`uint8` global H/E/H state, one scalar score per task, an exact saturation
certificate, and selective replay through the unchanged word16 authority.

The next kernel must demonstrate:

```text
T_byte(all tasks) + T_word(replay tasks)
<= (1 / 1.5) * T_word16_authority
```

It must also preserve every task score/minScore, downstream scoreInfo, and
complete output digest.  Failure of either gate makes the byte fast path a
NO-GO without runtime integration.
