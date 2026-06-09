#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_exact_scoreinfo_gpu_column_pruned_output_matrix"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
TARGET_PRESETS="${TARGET_PRESETS:-small}"
REPEATS="${REPEATS:-2}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
TOPK="${TOPK:-5}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-16}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$TOPK" != "5" ]]; then
  echo "column-pruned exact scoreInfo matrix requires TOPK=5" >&2
  exit 1
fi
if [[ "$REPEATS" -lt 1 ]]; then
  echo "REPEATS must be >= 1" >&2
  exit 1
fi

if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

for preset in $TARGET_PRESETS; do
  for repeat in $(seq 1 "$REPEATS"); do
    run_work="$WORK/runs/${preset}_r${repeat}"
    TARGET_PRESET="$preset" \
    BUILD_BIN=0 \
    BIN="$BIN" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    EXACT_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    bash "$ROOT/scripts/characterize_fasim_exact_scoreinfo_gpu_column_pruned_output.sh" \
      >"$WORK/${preset}_r${repeat}.stdout.log" \
      2>"$WORK/${preset}_r${repeat}.stderr.log"
  done
done

python3 - "$WORK" "$TARGET_PRESETS" "$REPEATS" <<'PY'
import csv
import statistics
import sys
from pathlib import Path

work = Path(sys.argv[1])
presets = sys.argv[2].split()
repeats = int(sys.argv[3])


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


columns = [
    "target_preset",
    "repeat",
    "exact_wall_seconds",
    "column_wall_seconds",
    "speedup_vs_exact_pruned",
    "top5_all_equal",
    "column_legacy_score_gpu_requests",
    "column_overflow_batches",
    "column_fallback_batches",
    "exact_scoreinfo_groups",
    "column_scoreinfo_groups",
    "scoreinfo_group_delta",
    "exact_gasal2_total_seconds",
    "column_gasal2_total_seconds",
    "run_work",
]
rows: list[dict[str, str]] = []
for preset in presets:
    for repeat in range(1, repeats + 1):
        run_dir = work / "runs" / f"{preset}_r{repeat}"
        pair = read_rows(run_dir / "summary.tsv")
        if len(pair) != 2:
            raise SystemExit(f"expected 2 rows in {run_dir / 'summary.tsv'}")
        exact, column = pair
        exact_groups = int(exact["scoreinfo_groups"])
        column_groups = int(column["scoreinfo_groups"])
        rows.append(
            {
                "target_preset": preset,
                "repeat": str(repeat),
                "exact_wall_seconds": exact["wall_seconds"],
                "column_wall_seconds": column["wall_seconds"],
                "speedup_vs_exact_pruned": column["speedup_vs_exact_pruned"],
                "top5_all_equal": column["top5_all_equal"],
                "column_legacy_score_gpu_requests": column["legacy_score_gpu_requests"],
                "column_overflow_batches": column["exact_scoreinfo_gpu_overflow_batches"],
                "column_fallback_batches": column["exact_scoreinfo_gpu_fallback_batches"],
                "exact_scoreinfo_groups": exact["scoreinfo_groups"],
                "column_scoreinfo_groups": column["scoreinfo_groups"],
                "scoreinfo_group_delta": str(column_groups - exact_groups),
                "exact_gasal2_total_seconds": exact["gasal2_total_seconds"],
                "column_gasal2_total_seconds": column["gasal2_total_seconds"],
                "run_work": str(run_dir),
            }
        )

summary_path = work / "summary.tsv"
with summary_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

aggregate_columns = [
    "target_preset",
    "runs",
    "top5_clean_runs",
    "zero_legacy_score_runs",
    "zero_overflow_runs",
    "zero_fallback_runs",
    "speedup_min",
    "speedup_median",
    "speedup_max",
    "scoreinfo_group_delta_min",
    "scoreinfo_group_delta_max",
    "decision",
]
aggregate_rows: list[dict[str, str]] = []
for preset in presets:
    preset_rows = [row for row in rows if row["target_preset"] == preset]
    speedups = [float(row["speedup_vs_exact_pruned"]) for row in preset_rows]
    deltas = [int(row["scoreinfo_group_delta"]) for row in preset_rows]
    top5_clean = sum(row["top5_all_equal"] == "true" for row in preset_rows)
    zero_legacy = sum(int(row["column_legacy_score_gpu_requests"]) == 0 for row in preset_rows)
    zero_overflow = sum(int(row["column_overflow_batches"]) == 0 for row in preset_rows)
    zero_fallback = sum(int(row["column_fallback_batches"]) == 0 for row in preset_rows)
    all_clean = (
        top5_clean == len(preset_rows)
        and zero_legacy == len(preset_rows)
        and zero_overflow == len(preset_rows)
        and zero_fallback == len(preset_rows)
    )
    decision = "top5_artifact_go" if all_clean and min(speedups) > 1.0 else "no_go_or_needs_review"
    aggregate_rows.append(
        {
            "target_preset": preset,
            "runs": str(len(preset_rows)),
            "top5_clean_runs": str(top5_clean),
            "zero_legacy_score_runs": str(zero_legacy),
            "zero_overflow_runs": str(zero_overflow),
            "zero_fallback_runs": str(zero_fallback),
            "speedup_min": f"{min(speedups):.6f}",
            "speedup_median": f"{statistics.median(speedups):.6f}",
            "speedup_max": f"{max(speedups):.6f}",
            "scoreinfo_group_delta_min": str(min(deltas)),
            "scoreinfo_group_delta_max": str(max(deltas)),
            "decision": decision,
        }
    )

aggregate_path = work / "aggregate.tsv"
with aggregate_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=aggregate_columns, delimiter="\t")
    writer.writeheader()
    writer.writerows(aggregate_rows)

decision_lines = []
for row in aggregate_rows:
    decision_lines.append(
        " ".join(
            [
                f"target_preset={row['target_preset']}",
                f"decision={row['decision']}",
                f"runs={row['runs']}",
                f"top5_clean_runs={row['top5_clean_runs']}",
                f"speedup_min={row['speedup_min']}",
                f"speedup_median={row['speedup_median']}",
                f"scoreinfo_group_delta={row['scoreinfo_group_delta_min']}..{row['scoreinfo_group_delta_max']}",
            ]
        )
    )
(work / "decision.txt").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")

print(summary_path.read_text(encoding="utf-8"), end="")
print(aggregate_path.read_text(encoding="utf-8"), end="")
print((work / "decision.txt").read_text(encoding="utf-8"), end="")
PY
