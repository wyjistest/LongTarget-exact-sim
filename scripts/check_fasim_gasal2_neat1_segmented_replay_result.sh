#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CAP37="${CAP37:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_no_last/summary.tsv"}"
CAP64="${CAP64:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_no_last_cap64/summary.tsv"}"
NO_PRUNE_NO_LAST="${NO_PRUNE_NO_LAST:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_no_prune_no_last/summary.tsv"}"
NO_PRUNE_WITH_LAST="${NO_PRUNE_WITH_LAST:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_no_prune_with_last/summary.tsv"}"
ALL_SEGMENTS_CAP37="${ALL_SEGMENTS_CAP37:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap37_no_last/summary.tsv"}"
ALL_SEGMENTS_CAP64="${ALL_SEGMENTS_CAP64:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap64_no_last/summary.tsv"}"
ALL_SEGMENTS_NO_PRUNE="${ALL_SEGMENTS_NO_PRUNE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_no_prune_no_last/summary.tsv"}"
ALL_SEGMENTS_CAP37_RANK3="${ALL_SEGMENTS_CAP37_RANK3:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap37_rank3/summary.tsv"}"
ALL_SEGMENTS_CAP37_RANK4="${ALL_SEGMENTS_CAP37_RANK4:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap37_rank4/summary.tsv"}"
ALL_SEGMENTS_CAP64_RANK4="${ALL_SEGMENTS_CAP64_RANK4:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap64_rank4/summary.tsv"}"
ALL_SEGMENTS_NO_PRUNE_RANK4="${ALL_SEGMENTS_NO_PRUNE_RANK4:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_noprune_rank4/summary.tsv"}"
FIRST128_CAP37_RANK4="${FIRST128_CAP37_RANK4:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first128_all_segments_cap37_rank4/summary.tsv"}"
ALL_SEGMENTS_CAP37_RANK3_THRESHOLD_SCORE="${ALL_SEGMENTS_CAP37_RANK3_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap37_rank3_threshold_score/summary.tsv"}"
FIRST128_CAP37_RANK3_THRESHOLD_SCORE="${FIRST128_CAP37_RANK3_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first128_all_segments_cap37_rank3_threshold_score/summary.tsv"}"
FIRST256_CAP37_RANK3_THRESHOLD_SCORE="${FIRST256_CAP37_RANK3_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first256_all_segments_cap37_rank3_threshold_score/summary.tsv"}"
ALL_SEGMENTS_CAP37_RANK2_THRESHOLD_SCORE="${ALL_SEGMENTS_CAP37_RANK2_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_neat1_first64_all_segments_cap37_rank2_threshold_score/summary.tsv"}"
MALAT1_CAP37_RANK3_THRESHOLD_SCORE="${MALAT1_CAP37_RANK3_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_malat1_first64_all_segments_cap37_rank3_threshold_score/summary.tsv"}"
MALAT1_CAP37_RANK2_THRESHOLD_SCORE="${MALAT1_CAP37_RANK2_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_malat1_first64_all_segments_cap37_rank2_threshold_score/summary.tsv"}"
MALAT1_CAP37_RANK1_THRESHOLD_SCORE="${MALAT1_CAP37_RANK1_THRESHOLD_SCORE:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow_malat1_first64_all_segments_cap37_rank1_threshold_score/summary.tsv"}"

for path in "$CAP37" "$CAP64" "$NO_PRUNE_NO_LAST" "$NO_PRUNE_WITH_LAST" "$ALL_SEGMENTS_CAP37" "$ALL_SEGMENTS_CAP64" "$ALL_SEGMENTS_NO_PRUNE" "$ALL_SEGMENTS_CAP37_RANK3" "$ALL_SEGMENTS_CAP37_RANK4" "$ALL_SEGMENTS_CAP64_RANK4" "$ALL_SEGMENTS_NO_PRUNE_RANK4" "$FIRST128_CAP37_RANK4" "$ALL_SEGMENTS_CAP37_RANK3_THRESHOLD_SCORE" "$FIRST128_CAP37_RANK3_THRESHOLD_SCORE" "$FIRST256_CAP37_RANK3_THRESHOLD_SCORE" "$ALL_SEGMENTS_CAP37_RANK2_THRESHOLD_SCORE" "$MALAT1_CAP37_RANK3_THRESHOLD_SCORE" "$MALAT1_CAP37_RANK2_THRESHOLD_SCORE" "$MALAT1_CAP37_RANK1_THRESHOLD_SCORE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing NEAT1 segmented replay result artifact: $path" >&2
    exit 1
  fi
done

python3 - "$CAP37" "$CAP64" "$NO_PRUNE_NO_LAST" "$NO_PRUNE_WITH_LAST" "$ALL_SEGMENTS_CAP37" "$ALL_SEGMENTS_CAP64" "$ALL_SEGMENTS_NO_PRUNE" "$ALL_SEGMENTS_CAP37_RANK3" "$ALL_SEGMENTS_CAP37_RANK4" "$ALL_SEGMENTS_CAP64_RANK4" "$ALL_SEGMENTS_NO_PRUNE_RANK4" "$FIRST128_CAP37_RANK4" "$ALL_SEGMENTS_CAP37_RANK3_THRESHOLD_SCORE" "$FIRST128_CAP37_RANK3_THRESHOLD_SCORE" "$FIRST256_CAP37_RANK3_THRESHOLD_SCORE" "$ALL_SEGMENTS_CAP37_RANK2_THRESHOLD_SCORE" "$MALAT1_CAP37_RANK3_THRESHOLD_SCORE" "$MALAT1_CAP37_RANK2_THRESHOLD_SCORE" "$MALAT1_CAP37_RANK1_THRESHOLD_SCORE" <<'PY'
import csv
import sys
from pathlib import Path


def one_row(
    path: str,
    *,
    label: str = "neat1_first64",
    target_record_limit: str = "64",
    query_len: str = "22767",
    expected_segments: str | None = None,
    max_segments: str,
    top5_clean: bool,
    nt_score_clean: bool | None = None,
) -> dict[str, str]:
    rows = list(csv.DictReader(Path(path).open(newline="", encoding="utf-8"), delimiter="\t"))
    if len(rows) != 1:
        raise SystemExit(f"{path}: expected one row, got {len(rows)}")
    row = rows[0]
    nt_score_clean = top5_clean if nt_score_clean is None else nt_score_clean
    score_clean = top5_clean
    if row.get("label") != label:
        raise SystemExit(f"{path}: unexpected label: {row}")
    decision_go = score_clean and nt_score_clean
    expected = {
        "target_record_limit": target_record_limit,
        "query_len": query_len,
        "tile_len": "2812",
        "tile_overlap": "512",
        "max_segments": max_segments,
        "requested": "1",
        "active": "1",
        "traceback_requests": "0",
        "fallbacks": "0",
        "top5_score_equal": "true" if score_clean else "false",
        "top5_stability_equal": "true",
        "top5_nt_score_equal": "true" if nt_score_clean else "false",
        "decision": "top5_artifact_go" if decision_go else "top5_artifact_no_go",
    }
    for key, value in expected.items():
        if row.get(key) != value:
            raise SystemExit(f"{path}: {key}={row.get(key)!r}, expected {value!r}: {row}")
    expected_segments = expected_segments or ("10" if max_segments == "0" else "4")
    if row.get("segments") != expected_segments:
        raise SystemExit(f"{path}: segments={row.get('segments')!r}, expected {expected_segments!r}: {row}")
    for key in (
        "gasal2_requests",
        "gasal2_score_batches",
        "cpu_replay_attempts",
        "cpu_replay_selected",
        "cpu_replay_align_calls",
    ):
        if int(float(row.get(key, "0"))) <= 0:
            raise SystemExit(f"{path}: expected positive {key}: {row}")
    if top5_clean:
        if int(float(row.get("missing_rows", "0"))) <= 0 or int(float(row.get("extra_rows", "0"))) <= 0:
            raise SystemExit(f"{path}: full row set may differ, but expected nonzero row diff telemetry: {row}")
    else:
        for key in ("missing_rows", "extra_rows"):
            if int(float(row.get(key, "0"))) <= 0:
                raise SystemExit(f"{path}: expected positive {key}: {row}")
    return row


cap37 = one_row(sys.argv[1], max_segments="4", top5_clean=False)
cap64 = one_row(sys.argv[2], max_segments="4", top5_clean=False)
no_prune_no_last = one_row(sys.argv[3], max_segments="4", top5_clean=False)
no_prune_with_last = one_row(sys.argv[4], max_segments="4", top5_clean=False)
all_segments_cap37 = one_row(sys.argv[5], max_segments="0", top5_clean=True)
all_segments_cap64 = one_row(sys.argv[6], max_segments="0", top5_clean=True)
all_segments_no_prune = one_row(sys.argv[7], max_segments="0", top5_clean=True)
all_segments_cap37_rank3 = one_row(sys.argv[8], max_segments="0", top5_clean=True, nt_score_clean=False)
all_segments_cap37_rank4 = one_row(sys.argv[9], max_segments="0", top5_clean=True)
all_segments_cap64_rank4 = one_row(sys.argv[10], max_segments="0", top5_clean=True)
all_segments_no_prune_rank4 = one_row(sys.argv[11], max_segments="0", top5_clean=True)
first128_cap37_rank4 = one_row(
    sys.argv[12],
    label="neat1_first128",
    target_record_limit="128",
    max_segments="0",
    top5_clean=True,
)
all_segments_cap37_rank3_threshold_score = one_row(
    sys.argv[13],
    max_segments="0",
    top5_clean=True,
)
first128_cap37_rank3_threshold_score = one_row(
    sys.argv[14],
    label="neat1_first128",
    target_record_limit="128",
    max_segments="0",
    top5_clean=True,
)
first256_cap37_rank3_threshold_score = one_row(
    sys.argv[15],
    label="neat1_first256",
    target_record_limit="256",
    max_segments="0",
    top5_clean=True,
)
all_segments_cap37_rank2_threshold_score = one_row(
    sys.argv[16],
    max_segments="0",
    top5_clean=True,
    nt_score_clean=False,
)
malat1_cap37_rank3_threshold_score = one_row(
    sys.argv[17],
    label="malat1_first64",
    query_len="8708",
    expected_segments="4",
    max_segments="0",
    top5_clean=True,
)
malat1_cap37_rank2_threshold_score = one_row(
    sys.argv[18],
    label="malat1_first64",
    query_len="8708",
    expected_segments="4",
    max_segments="0",
    top5_clean=True,
)
malat1_cap37_rank1_threshold_score = one_row(
    sys.argv[19],
    label="malat1_first64",
    query_len="8708",
    expected_segments="4",
    max_segments="0",
    top5_clean=True,
)

if cap37.get("scoreinfo_max_per_task") != "37" or cap37.get("scoreinfo_prune_mode") != "score_position_edges":
    raise SystemExit(f"cap37 config mismatch: {cap37}")
if cap64.get("scoreinfo_max_per_task") != "64" or cap64.get("scoreinfo_prune_mode") != "score_position_edges":
    raise SystemExit(f"cap64 config mismatch: {cap64}")
if no_prune_no_last.get("scoreinfo_max_per_task") != "0":
    raise SystemExit(f"no-prune/no-last config mismatch: {no_prune_no_last}")
if no_prune_with_last.get("scoreinfo_max_per_task") != "0":
    raise SystemExit(f"no-prune/with-last config mismatch: {no_prune_with_last}")
if all_segments_cap37.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(f"all-segments cap37 config mismatch: {all_segments_cap37}")
if all_segments_cap64.get("scoreinfo_max_per_task") != "64":
    raise SystemExit(f"all-segments cap64 config mismatch: {all_segments_cap64}")
if all_segments_no_prune.get("scoreinfo_max_per_task") != "0":
    raise SystemExit(f"all-segments no-prune config mismatch: {all_segments_no_prune}")
if all_segments_cap37_rank3.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(f"all-segments cap37 rank3 config mismatch: {all_segments_cap37_rank3}")
if all_segments_cap37_rank4.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(f"all-segments cap37 rank4 config mismatch: {all_segments_cap37_rank4}")
if all_segments_cap64_rank4.get("scoreinfo_max_per_task") != "64":
    raise SystemExit(f"all-segments cap64 rank4 config mismatch: {all_segments_cap64_rank4}")
if all_segments_no_prune_rank4.get("scoreinfo_max_per_task") != "0":
    raise SystemExit(f"all-segments no-prune rank4 config mismatch: {all_segments_no_prune_rank4}")
if first128_cap37_rank4.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(f"first128 cap37 rank4 config mismatch: {first128_cap37_rank4}")
if all_segments_cap37_rank3_threshold_score.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(
        "all-segments cap37 threshold-score rank3 config mismatch: "
        f"{all_segments_cap37_rank3_threshold_score}"
    )
if first128_cap37_rank3_threshold_score.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(
        "first128 cap37 threshold-score rank3 config mismatch: "
        f"{first128_cap37_rank3_threshold_score}"
    )
if first256_cap37_rank3_threshold_score.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(
        "first256 cap37 threshold-score rank3 config mismatch: "
        f"{first256_cap37_rank3_threshold_score}"
    )
if all_segments_cap37_rank2_threshold_score.get("scoreinfo_max_per_task") != "37":
    raise SystemExit(
        "all-segments cap37 threshold-score rank2 config mismatch: "
        f"{all_segments_cap37_rank2_threshold_score}"
    )
for row, label in (
    (malat1_cap37_rank3_threshold_score, "malat1 rank3"),
    (malat1_cap37_rank2_threshold_score, "malat1 rank2"),
    (malat1_cap37_rank1_threshold_score, "malat1 rank1"),
):
    if row.get("scoreinfo_max_per_task") != "37" or row.get("scoreinfo_prune_mode") != "score_position_edges":
        raise SystemExit(f"{label} config mismatch: {row}")

for row in (cap37, cap64, no_prune_no_last):
    if row.get("cpu_traceback_no_last") != "1":
        raise SystemExit(f"expected no-last enabled: {row}")
    if float(row.get("speedup_vs_baseline", "0")) <= 1.0:
        raise SystemExit(f"expected no-last candidate to be faster but no-go: {row}")

for row in (all_segments_cap37, all_segments_cap64, all_segments_no_prune):
    if row.get("cpu_traceback_no_last") != "1":
        raise SystemExit(f"expected all-segments no-last enabled: {row}")
    if float(row.get("speedup_vs_baseline", "0")) >= 1.0:
        raise SystemExit(f"expected all-segments top5-clean candidate to be slower: {row}")

rank_rows = (
    (all_segments_cap37_rank3, "3"),
    (all_segments_cap37_rank4, "4"),
    (all_segments_cap64_rank4, "4"),
    (all_segments_no_prune_rank4, "4"),
    (first128_cap37_rank4, "4"),
    (all_segments_cap37_rank3_threshold_score, "3"),
    (first128_cap37_rank3_threshold_score, "3"),
    (first256_cap37_rank3_threshold_score, "3"),
    (all_segments_cap37_rank2_threshold_score, "2"),
    (malat1_cap37_rank3_threshold_score, "3"),
    (malat1_cap37_rank2_threshold_score, "2"),
    (malat1_cap37_rank1_threshold_score, "1"),
)
for row, rank in rank_rows:
    if row.get("cpu_traceback_no_last") != "1":
        raise SystemExit(f"expected rank-cutoff no-last enabled: {row}")
    if row.get("cpu_traceback_max_rank") != rank:
        raise SystemExit(f"expected max rank {rank}: {row}")
    if int(row.get("cpu_traceback_rank_cutoff_skipped", "0")) <= 0:
        raise SystemExit(f"expected positive rank-cutoff skips: {row}")
    if float(row.get("speedup_vs_baseline", "0")) <= 1.0:
        raise SystemExit(f"expected rank-cutoff candidate to be faster than baseline: {row}")

if no_prune_with_last.get("cpu_traceback_no_last") != "0":
    raise SystemExit(f"expected with-last run: {no_prune_with_last}")
if float(no_prune_with_last.get("speedup_vs_baseline", "0")) >= 1.0:
    raise SystemExit(f"expected with-last candidate to be slower: {no_prune_with_last}")

if int(no_prune_with_last["cpu_replay_align_calls"]) <= int(no_prune_no_last["cpu_replay_align_calls"]):
    raise SystemExit(
        "with-last should increase CPU replay Align calls: "
        f"with_last={no_prune_with_last['cpu_replay_align_calls']} "
        f"no_last={no_prune_no_last['cpu_replay_align_calls']}"
    )

if int(cap64["scoreinfo_pruned_groups"]) >= int(cap37["scoreinfo_pruned_groups"]):
    raise SystemExit(f"cap64 should prune fewer groups than cap37: cap37={cap37} cap64={cap64}")
if int(all_segments_cap64["scoreinfo_pruned_groups"]) >= int(all_segments_cap37["scoreinfo_pruned_groups"]):
    raise SystemExit(
        "all-segments cap64 should prune fewer groups than cap37: "
        f"cap37={all_segments_cap37} cap64={all_segments_cap64}"
    )
if int(all_segments_no_prune["cpu_replay_align_calls"]) <= int(all_segments_cap64["cpu_replay_align_calls"]):
    raise SystemExit(
        "all-segments no-prune should replay at least as many CPU Align calls as cap64: "
        f"no_prune={all_segments_no_prune} cap64={all_segments_cap64}"
    )
if int(all_segments_cap37_rank3["cpu_replay_align_calls"]) >= int(all_segments_cap37_rank4["cpu_replay_align_calls"]):
    raise SystemExit(
        "rank3 should replay fewer CPU Align calls than rank4: "
        f"rank3={all_segments_cap37_rank3} rank4={all_segments_cap37_rank4}"
    )
if int(all_segments_cap37_rank4["cpu_replay_align_calls"]) >= int(all_segments_cap37["cpu_replay_align_calls"]):
    raise SystemExit(
        "rank4 should replay fewer CPU Align calls than uncapped all-segments cap37: "
        f"rank4={all_segments_cap37_rank4} uncapped={all_segments_cap37}"
    )
if float(all_segments_cap37_rank4["speedup_vs_baseline"]) > 1.10:
    raise SystemExit(f"rank4 result should remain a weak speedup checkpoint: {all_segments_cap37_rank4}")
if float(all_segments_cap64_rank4["speedup_vs_baseline"]) > float(all_segments_cap37_rank4["speedup_vs_baseline"]):
    raise SystemExit(
        "rank4 cap64 should not outperform cap37 in this checkpoint: "
        f"cap37={all_segments_cap37_rank4} cap64={all_segments_cap64_rank4}"
    )
if float(all_segments_no_prune_rank4["speedup_vs_baseline"]) > float(all_segments_cap37_rank4["speedup_vs_baseline"]):
    raise SystemExit(
        "rank4 no-prune should not outperform cap37 in this checkpoint: "
        f"cap37={all_segments_cap37_rank4} no_prune={all_segments_no_prune_rank4}"
    )
if float(first128_cap37_rank4["speedup_vs_baseline"]) > float(all_segments_cap37_rank4["speedup_vs_baseline"]) + 0.02:
    raise SystemExit(
        "first128 rank4 should not show meaningful scale-up over first64 in this checkpoint: "
        f"first64={all_segments_cap37_rank4} first128={first128_cap37_rank4}"
    )
if int(first128_cap37_rank4["cpu_replay_align_calls"]) <= int(all_segments_cap37_rank4["cpu_replay_align_calls"]):
    raise SystemExit(
        "first128 should replay more CPU Align calls than first64: "
        f"first64={all_segments_cap37_rank4} first128={first128_cap37_rank4}"
    )
for row in (
    all_segments_cap37_rank3_threshold_score,
    first128_cap37_rank3_threshold_score,
    first256_cap37_rank3_threshold_score,
    all_segments_cap37_rank2_threshold_score,
    malat1_cap37_rank3_threshold_score,
    malat1_cap37_rank2_threshold_score,
    malat1_cap37_rank1_threshold_score,
):
    if row.get("cpu_traceback_order") != "threshold_score":
        raise SystemExit(f"expected threshold_score replay order: {row}")
if all_segments_cap37_rank3.get("cpu_traceback_order") != "legacy":
    raise SystemExit(f"expected legacy rank3 baseline order: {all_segments_cap37_rank3}")
if float(all_segments_cap37_rank3_threshold_score["speedup_vs_baseline"]) <= float(all_segments_cap37_rank4["speedup_vs_baseline"]):
    raise SystemExit(
        "threshold_score rank3 should outperform legacy rank4 on first64: "
        f"threshold_rank3={all_segments_cap37_rank3_threshold_score} legacy_rank4={all_segments_cap37_rank4}"
    )
if float(first128_cap37_rank3_threshold_score["speedup_vs_baseline"]) <= float(first128_cap37_rank4["speedup_vs_baseline"]):
    raise SystemExit(
        "threshold_score rank3 should outperform legacy rank4 on first128: "
        f"threshold_rank3={first128_cap37_rank3_threshold_score} legacy_rank4={first128_cap37_rank4}"
    )
if int(all_segments_cap37_rank3_threshold_score["cpu_replay_align_calls"]) != int(all_segments_cap37_rank3["cpu_replay_align_calls"]):
    raise SystemExit(
        "threshold_score rank3 should keep the same first64 replay cap as legacy rank3: "
        f"threshold_rank3={all_segments_cap37_rank3_threshold_score} legacy_rank3={all_segments_cap37_rank3}"
    )
if float(first128_cap37_rank3_threshold_score["speedup_vs_baseline"]) < 1.10:
    raise SystemExit(
        "first128 threshold_score rank3 should stay a modest positive checkpoint: "
        f"{first128_cap37_rank3_threshold_score}"
    )
if float(first256_cap37_rank3_threshold_score["speedup_vs_baseline"]) < 1.10:
    raise SystemExit(
        "first256 threshold_score rank3 should stay a modest positive checkpoint: "
        f"{first256_cap37_rank3_threshold_score}"
    )
if float(first256_cap37_rank3_threshold_score["speedup_vs_baseline"]) > float(first128_cap37_rank3_threshold_score["speedup_vs_baseline"]) + 0.03:
    raise SystemExit(
        "first256 threshold_score rank3 should not show strong scale-up in this checkpoint: "
        f"first128={first128_cap37_rank3_threshold_score} first256={first256_cap37_rank3_threshold_score}"
    )
if float(all_segments_cap37_rank2_threshold_score["speedup_vs_baseline"]) <= float(all_segments_cap37_rank3_threshold_score["speedup_vs_baseline"]):
    raise SystemExit(
        "threshold_score rank2 should be faster but top5 nt_score no-go: "
        f"rank2={all_segments_cap37_rank2_threshold_score} rank3={all_segments_cap37_rank3_threshold_score}"
    )
if int(all_segments_cap37_rank2_threshold_score["cpu_replay_align_calls"]) >= int(all_segments_cap37_rank3_threshold_score["cpu_replay_align_calls"]):
    raise SystemExit(
        "threshold_score rank2 should replay fewer CPU Align calls than rank3: "
        f"rank2={all_segments_cap37_rank2_threshold_score} rank3={all_segments_cap37_rank3_threshold_score}"
    )
if float(malat1_cap37_rank3_threshold_score["speedup_vs_baseline"]) < 1.10:
    raise SystemExit(
        "MALAT1 threshold_score rank3 should stay a modest positive checkpoint: "
        f"{malat1_cap37_rank3_threshold_score}"
    )
if float(malat1_cap37_rank2_threshold_score["speedup_vs_baseline"]) <= float(malat1_cap37_rank3_threshold_score["speedup_vs_baseline"]):
    raise SystemExit(
        "MALAT1 threshold_score rank2 should outperform rank3 in this checkpoint: "
        f"rank2={malat1_cap37_rank2_threshold_score} rank3={malat1_cap37_rank3_threshold_score}"
    )
if float(malat1_cap37_rank1_threshold_score["speedup_vs_baseline"]) <= float(malat1_cap37_rank2_threshold_score["speedup_vs_baseline"]):
    raise SystemExit(
        "MALAT1 threshold_score rank1 should outperform rank2 in this checkpoint: "
        f"rank1={malat1_cap37_rank1_threshold_score} rank2={malat1_cap37_rank2_threshold_score}"
    )
if int(malat1_cap37_rank1_threshold_score["cpu_replay_align_calls"]) >= int(malat1_cap37_rank2_threshold_score["cpu_replay_align_calls"]):
    raise SystemExit(
        "MALAT1 threshold_score rank1 should replay fewer CPU Align calls than rank2: "
        f"rank1={malat1_cap37_rank1_threshold_score} rank2={malat1_cap37_rank2_threshold_score}"
    )

print("decision=neat1_segmented_replay_perf_no_go")
print("coverage_boundary=4_segments_top5_no_go")
print("correctness_boundary=all_segments_top5_clean")
print("performance_boundary=all_segments_slower_than_baseline")
print("rank_cutoff_boundary=legacy_rank3_nt_score_no_go_legacy_rank4_weak_go")
print("threshold_score_boundary=neat1_rank2_nt_score_no_go_cross_workload_rank3_modest_go")
print("malat1_threshold_score_boundary=rank1_top5_clean_sampled_go")
print("cap37_4segment_speedup_vs_baseline=" + cap37["speedup_vs_baseline"])
print("cap64_4segment_speedup_vs_baseline=" + cap64["speedup_vs_baseline"])
print("all_segments_cap37_speedup_vs_baseline=" + all_segments_cap37["speedup_vs_baseline"])
print("all_segments_cap64_speedup_vs_baseline=" + all_segments_cap64["speedup_vs_baseline"])
print("all_segments_no_prune_speedup_vs_baseline=" + all_segments_no_prune["speedup_vs_baseline"])
print("all_segments_cap37_rank3_speedup_vs_baseline=" + all_segments_cap37_rank3["speedup_vs_baseline"])
print("all_segments_cap37_rank4_speedup_vs_baseline=" + all_segments_cap37_rank4["speedup_vs_baseline"])
print("all_segments_cap64_rank4_speedup_vs_baseline=" + all_segments_cap64_rank4["speedup_vs_baseline"])
print("all_segments_no_prune_rank4_speedup_vs_baseline=" + all_segments_no_prune_rank4["speedup_vs_baseline"])
print("first128_cap37_rank4_speedup_vs_baseline=" + first128_cap37_rank4["speedup_vs_baseline"])
print("all_segments_cap37_rank3_threshold_score_speedup_vs_baseline=" + all_segments_cap37_rank3_threshold_score["speedup_vs_baseline"])
print("first128_cap37_rank3_threshold_score_speedup_vs_baseline=" + first128_cap37_rank3_threshold_score["speedup_vs_baseline"])
print("first256_cap37_rank3_threshold_score_speedup_vs_baseline=" + first256_cap37_rank3_threshold_score["speedup_vs_baseline"])
print("all_segments_cap37_rank2_threshold_score_speedup_vs_baseline=" + all_segments_cap37_rank2_threshold_score["speedup_vs_baseline"])
print("malat1_cap37_rank3_threshold_score_speedup_vs_baseline=" + malat1_cap37_rank3_threshold_score["speedup_vs_baseline"])
print("malat1_cap37_rank2_threshold_score_speedup_vs_baseline=" + malat1_cap37_rank2_threshold_score["speedup_vs_baseline"])
print("malat1_cap37_rank1_threshold_score_speedup_vs_baseline=" + malat1_cap37_rank1_threshold_score["speedup_vs_baseline"])
PY
