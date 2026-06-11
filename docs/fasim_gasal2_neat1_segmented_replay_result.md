# Fasim GASAL2 NEAT1 Segmented Replay Result

This checkpoint records the NEAT1 first64 result for the long-query GASAL2
segmented score-prepass plus CPU replay path.

It is not a production path and not a full `aligner.Align()` replacement. GPU
endpoint, CIGAR, traceback, output, and digest authority remain forbidden.

## Setup

All rows used:

```text
workload = NEAT1 first64
query_len = 22,767
tile_len = 2,812
tile_overlap = 512
SCORE_PREPASS_SHADOW = 1
CPU_TRACEBACK_REPLAY = 1
CPU_TRACEBACK_NO_LAST = 1 unless noted
GASAL2 traceback requests = 0
fallbacks = 0
```

## Four-Segment Boundary

With `MAX_SEGMENTS=4`, the candidate is faster but does not preserve the top5
contract:

```text
score_position_edges, max_per_task=37:
  segments = 4
  top5 score/stability/nt_score = false/true/false
  cpu_replay_align_calls = 92,218
  speedup_vs_baseline = 1.253720x

score_position_edges, max_per_task=64:
  segments = 4
  top5 score/stability/nt_score = false/true/false
  cpu_replay_align_calls = 96,469
  speedup_vs_baseline = 1.222750x

no scoreInfo prune:
  segments = 4
  top5 score/stability/nt_score = false/true/false
  cpu_replay_align_calls = 97,155
  speedup_vs_baseline = 1.225141x
```

This is a coverage boundary, not proof that segmented replay can never preserve
NEAT1 top5. Four segments do not cover enough of the 22.8 kb query.

Keeping last candidates with four segments does not fix the contract and is
slower:

```text
no scoreInfo prune, with-last:
  segments = 4
  top5 score/stability/nt_score = false/true/false
  cpu_replay_align_calls = 230,838
  speedup_vs_baseline = 0.780952x
```

## All-Segments Boundary

With `MAX_SEGMENTS=0`, the query is covered by 10 segments. This restores the
top5 contract but loses the speedup:

```text
score_position_edges, max_per_task=37:
  segments = 10
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 169,711
  speedup_vs_baseline = 0.867124x

score_position_edges, max_per_task=64:
  segments = 10
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 176,875
  speedup_vs_baseline = 0.844647x

no scoreInfo prune:
  segments = 10
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 177,908
  speedup_vs_baseline = 0.849981x
```

The candidate still has full row-set differences, so the only clean contract
here is top5 score/stability/nt_score.

## Rank-Cutoff Replay Probe

The all-segments path was then tested with a default-off CPU replay rank cutoff:

```text
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_MAX_RANK=N
```

This limits CPU authority `Align()` replay to the first N GASAL2-scored
candidates per scoreInfo group. It does not make GPU endpoint, CIGAR,
traceback, output, or digest authoritative.

```text
all segments, score_position_edges, max_per_task=37, max_rank=3:
  top5 score/stability/nt_score = true/true/false
  cpu_replay_align_calls = 91,702
  cpu_traceback_rank_cutoff_skipped = 78,006
  speedup_vs_baseline = 1.147361x

all segments, score_position_edges, max_per_task=37, max_rank=4:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 109,538
  cpu_traceback_rank_cutoff_skipped = 60,172
  speedup_vs_baseline = 1.066762x

all segments, score_position_edges, max_per_task=64, max_rank=4:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 114,590
  cpu_traceback_rank_cutoff_skipped = 62,288
  speedup_vs_baseline = 1.040536x

all segments, no scoreInfo prune, max_rank=4:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 115,419
  cpu_traceback_rank_cutoff_skipped = 62,488
  speedup_vs_baseline = 1.038238x
```

The best first64 rank-cutoff configuration was also replayed on NEAT1 first128:

```text
all segments, score_position_edges, max_per_task=37, max_rank=4, first128:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 219,743
  cpu_traceback_rank_cutoff_skipped = 119,841
  speedup_vs_baseline = 1.063734x
```

The first128 speedup is essentially the same as first64. This does not show
scale-up evidence for the current rank-cutoff replay shape.

Changing the replay order from legacy order to threshold-first score order gives
a better rank-limited point:

```text
all segments, score_position_edges, max_per_task=37, max_rank=3,
cpu_traceback_order=threshold_score, first64:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 91,702
  cpu_traceback_rank_cutoff_skipped = 78,006
  speedup_vs_baseline = 1.161335x

all segments, score_position_edges, max_per_task=37, max_rank=3,
cpu_traceback_order=threshold_score, first128:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 183,932
  cpu_traceback_rank_cutoff_skipped = 155,663
  speedup_vs_baseline = 1.166254x

all segments, score_position_edges, max_per_task=37, max_rank=3,
cpu_traceback_order=threshold_score, first256:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 369,472
  cpu_traceback_rank_cutoff_skipped = 314,755
  speedup_vs_baseline = 1.163252x

all segments, score_position_edges, max_per_task=37, max_rank=2,
cpu_traceback_order=threshold_score, first64:
  top5 score/stability/nt_score = true/true/false
  cpu_replay_align_calls = 70,848
  cpu_traceback_rank_cutoff_skipped = 98,863
  speedup_vs_baseline = 1.278230x
```

This is the strongest current NEAT1 segmented replay point. It is still only a
top5-scoped result with full row-set differences, but it shows a real lever:
ordering CPU replay candidates by threshold/score can preserve top5 with a
smaller rank cutoff than legacy order.

## MALAT1 Broad Gate

The threshold-score replay shape was also tested on MALAT1 first64:

```text
all segments, score_position_edges, max_per_task=37, max_rank=3,
cpu_traceback_order=threshold_score, MALAT1 first64:
  query_len = 8,708
  segments = 4
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 441,117
  cpu_traceback_rank_cutoff_skipped = 156,634
  speedup_vs_baseline = 1.167749x

all segments, score_position_edges, max_per_task=37, max_rank=2,
cpu_traceback_order=threshold_score, MALAT1 first64:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 365,762
  cpu_traceback_rank_cutoff_skipped = 231,995
  speedup_vs_baseline = 1.205416x

all segments, score_position_edges, max_per_task=37, max_rank=1,
cpu_traceback_order=threshold_score, MALAT1 first64:
  top5 score/stability/nt_score = true/true/true
  cpu_replay_align_calls = 271,296
  cpu_traceback_rank_cutoff_skipped = 326,485
  speedup_vs_baseline = 1.287740x
```

MALAT1 first64 has a looser rank cutoff boundary than NEAT1: rank1 is clean for
this sampled workload. That does not make rank1 a global setting, because NEAT1
rank2 already fails top5 nt_score.

The rank cutoff creates a narrow positive point, but it is not a strong
performance candidate:

```text
max_rank=3:
  legacy order:
    faster
    top5 nt_score no-go
  threshold_score order:
    rank=2:
      NEAT1:
        faster
        top5 nt_score no-go
      MALAT1 first64:
        top5 clean
        about 1.21x faster
    rank=3:
      top5 clean on NEAT1 first64, first128, and first256
      top5 clean on MALAT1 first64
      about 1.16x faster
    rank=1:
      MALAT1 first64 top5 clean
      NEAT1 not safe by rank2 boundary

max_rank=4:
  top5 clean on NEAT1 first64
  top5 clean on NEAT1 first128 for the best tested setting
  only 1.04-1.07x faster
  still has full row-set differences
  does not strengthen from first64 to first128
```

This is a useful probe because it identifies where the current all-segments
path spends time: once enough query coverage is restored, remaining speedup
depends on reducing CPU authority replay. It is not enough evidence for a real
path.

## Decision

```text
NEAT1 segmented replay:
  four-segment mode:
    performance positive
    top5 score/nt correctness no-go

  all-segments mode:
    top5 correctness clean
    performance no-go

  all-segments + CPU replay rank cutoff:
    legacy rank=3:
      top5 nt_score no-go
    legacy rank=4:
      top5 clean on NEAT1 first64 and first128
      performance only weakly positive
    threshold_score rank=3:
      top5 clean on NEAT1 first64, first128, and first256
      top5 clean on MALAT1 first64
      modest performance positive
    threshold_score rank=1:
      MALAT1 first64 clean
      not a global setting
```

This is still not a real-path candidate. The exact failure mode is now clear:

```text
insufficient query coverage:
  can be faster but drops top5 score/nt rows

complete query coverage:
  preserves top5 but CPU replay + GASAL2 score-prepass is slower than CPU baseline

rank-limited complete query coverage:
  legacy order can preserve top5 at rank=4, but speedup is only about 1.04-1.07x
  threshold_score order can preserve top5 at rank=3, with about 1.16x stable speedup
  threshold_score rank=2 is faster but top5 nt_score no-go
  MALAT1 first64 can go down to rank=1, but NEAT1 cannot
  full row-set equivalence remains false
```

Do not promote:

```text
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_REPLAY
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_MAX_RANK
FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_ORDER
current segmented score-prepass/no-last combination
```

## Remaining Directions

The remaining plausible directions are materially different:

```text
1. validate threshold_score + max_rank=3 on broader workloads as the cross-workload safe candidate
2. reduce all-segments replay cost without dropping top5 score/nt
3. replace segmented selection with an exact long-query candidate path
4. replace CPU traceback with a Fasim-compatible traceback path
```

Until one of those is clean and faster, CPU Fasim output remains authority.

## Verification

```bash
bash scripts/check_fasim_gasal2_long_query_segmented_workload_param.sh
bash scripts/check_fasim_gasal2_neat1_segmented_replay_result.sh
```
