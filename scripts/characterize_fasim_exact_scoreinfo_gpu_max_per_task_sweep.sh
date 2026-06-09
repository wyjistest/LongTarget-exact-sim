#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_exact_scoreinfo_gpu_max_per_task_sweep"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
MAX_PER_TASK_VALUES="${MAX_PER_TASK_VALUES:-512 1024 2048 4096}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-10}"
BASELINE_VALUE="${BASELINE_VALUE:-default}"
TOPK="${TOPK:-5}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"

if [[ "$TOPK" != "5" ]]; then
  echo "exact scoreInfo GPU max-per-task sweep requires TOPK=5" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

run_one() {
  local label="$1"
  local max_per_task="$2"
  local run_work="$WORK/runs/$label"

  if [[ "$label" == "$BASELINE_VALUE" ]]; then
    TARGET="$TARGET" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    TOPK_SUMMARY_ONLY=1 \
    IN_PROCESS_TOPK=1 \
    EXACT_COLUMN_SCOREINFO_GPU=1 \
    GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      >"$WORK/$label.stdout.log" \
      2>"$WORK/$label.stderr.log"
  else
    TARGET="$TARGET" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    TOPK_SUMMARY_ONLY=1 \
    IN_PROCESS_TOPK=1 \
    EXACT_COLUMN_SCOREINFO_GPU=1 \
    EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$max_per_task" \
    GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      >"$WORK/$label.stdout.log" \
      2>"$WORK/$label.stderr.log"
  fi
}

run_one "$BASELINE_VALUE" ""
for value in $MAX_PER_TASK_VALUES; do
  run_one "max${value}" "$value"
done

python3 - "$WORK" "$BASELINE_VALUE" "$MAX_PER_TASK_VALUES" <<'PY'
import csv
import sys
from pathlib import Path

work = Path(sys.argv[1])
baseline_label = sys.argv[2]
values = sys.argv[3].split()


def read_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def read_shard_sums(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    def sum_field(name: str) -> float:
        total = 0.0
        for row in rows:
            value = row.get(name, "")
            if value:
                total += float(value)
        return total

    return {
        "traceback_requests": sum_field("traceback_requests"),
        "scoreinfo_groups": sum_field("scoreinfo_groups"),
        "scoreinfo_pruned_groups": sum_field("scoreinfo_prune_pruned_groups"),
        "scoreinfo_kept_groups": sum_field("scoreinfo_prune_kept_groups"),
        "gasal2_total_seconds": sum_field("gasal2_total_seconds"),
        "exact_scoreinfo_gpu_enabled_shards": sum_field("exact_scoreinfo_gpu_enabled"),
        "exact_scoreinfo_gpu_batches": sum_field("exact_scoreinfo_gpu_batches"),
        "exact_scoreinfo_gpu_tasks": sum_field("exact_scoreinfo_gpu_tasks"),
        "exact_scoreinfo_gpu_overflow_batches": sum_field("exact_scoreinfo_gpu_overflow_batches"),
        "exact_scoreinfo_gpu_fallback_batches": sum_field("exact_scoreinfo_gpu_fallback_batches"),
        "exact_scoreinfo_gpu_wall_seconds": sum_field("exact_scoreinfo_gpu_wall_seconds"),
        "exact_scoreinfo_gpu_kernel_seconds": sum_field("exact_scoreinfo_gpu_kernel_seconds"),
        "exact_scoreinfo_gpu_h2d_seconds": sum_field("exact_scoreinfo_gpu_h2d_seconds"),
        "exact_scoreinfo_gpu_d2h_seconds": sum_field("exact_scoreinfo_gpu_d2h_seconds"),
        "exact_column_wall_seconds": sum_field("exact_column_wall_seconds"),
        "exact_column_kernel_seconds": sum_field("exact_column_kernel_seconds"),
    }


def read_gpu_avg(path: Path) -> str:
    if not path.exists():
        return ""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    values = [float(row["gpu_util_avg"]) for row in rows if row.get("gpu_util_avg")]
    if not values:
        return ""
    return f"{sum(values) / len(values):.6f}"


labels = [baseline_label] + [f"max{value}" for value in values]
baseline = read_kv(work / "runs" / baseline_label / "summary.txt")
baseline_wall = float(baseline["wall_seconds"])
baseline_digests = {
    "score": baseline["top5_score_digest"],
    "stability": baseline["top5_stability_digest"],
    "nt_score": baseline["top5_nt_score_digest"],
}

columns = [
    "label",
    "exact_scoreinfo_gpu_max_per_task",
    "runner_exact_scoreinfo_gpu_max_per_task",
    "wall_seconds",
    "speedup_vs_baseline",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_all_equal",
    "traceback_requests",
    "scoreinfo_groups",
    "scoreinfo_pruned_groups",
    "scoreinfo_kept_groups",
    "gasal2_total_seconds",
    "exact_scoreinfo_gpu_enabled_shards",
    "exact_scoreinfo_gpu_batches",
    "exact_scoreinfo_gpu_tasks",
    "exact_scoreinfo_gpu_overflow_batches",
    "exact_scoreinfo_gpu_fallback_batches",
    "exact_scoreinfo_gpu_wall_seconds",
    "exact_scoreinfo_gpu_kernel_seconds",
    "exact_scoreinfo_gpu_h2d_seconds",
    "exact_scoreinfo_gpu_d2h_seconds",
    "exact_column_wall_seconds",
    "exact_column_kernel_seconds",
    "gpu_util_avg_mean",
    "top5_score_digest",
    "top5_stability_digest",
    "top5_nt_score_digest",
    "run_work",
]

rows: list[dict[str, str]] = []
for label in labels:
    run_dir = work / "runs" / label
    summary = read_kv(run_dir / "summary.txt")
    sums = read_shard_sums(run_dir / "shard_benchmark_summary.tsv")
    wall = float(summary["wall_seconds"])
    score_equal = summary["top5_score_digest"] == baseline_digests["score"]
    stability_equal = summary["top5_stability_digest"] == baseline_digests["stability"]
    nt_equal = summary["top5_nt_score_digest"] == baseline_digests["nt_score"]
    max_per_task = summary.get("exact_column_scoreinfo_gpu_max_per_task", "")
    if label == baseline_label and not max_per_task:
        max_per_task = "default"
    runner_exact_max_per_task = summary.get("runner_exact_scoreinfo_gpu_max_per_task", "")
    if label == baseline_label and not runner_exact_max_per_task:
        runner_exact_max_per_task = "default"
    rows.append(
        {
            "label": label,
            "exact_scoreinfo_gpu_max_per_task": max_per_task,
            "runner_exact_scoreinfo_gpu_max_per_task": runner_exact_max_per_task,
            "wall_seconds": f"{wall:.6f}",
            "speedup_vs_baseline": f"{baseline_wall / wall:.6f}",
            "top5_score_equal": str(score_equal).lower(),
            "top5_stability_equal": str(stability_equal).lower(),
            "top5_nt_score_equal": str(nt_equal).lower(),
            "top5_all_equal": str(score_equal and stability_equal and nt_equal).lower(),
            "traceback_requests": str(int(sums.get("traceback_requests", 0))),
            "scoreinfo_groups": str(int(sums.get("scoreinfo_groups", 0))),
            "scoreinfo_pruned_groups": str(int(sums.get("scoreinfo_pruned_groups", 0))),
            "scoreinfo_kept_groups": str(int(sums.get("scoreinfo_kept_groups", 0))),
            "gasal2_total_seconds": f"{sums.get('gasal2_total_seconds', 0.0):.6f}",
            "exact_scoreinfo_gpu_enabled_shards": str(int(sums.get("exact_scoreinfo_gpu_enabled_shards", 0))),
            "exact_scoreinfo_gpu_batches": str(int(sums.get("exact_scoreinfo_gpu_batches", 0))),
            "exact_scoreinfo_gpu_tasks": str(int(sums.get("exact_scoreinfo_gpu_tasks", 0))),
            "exact_scoreinfo_gpu_overflow_batches": str(
                int(sums.get("exact_scoreinfo_gpu_overflow_batches", 0))
            ),
            "exact_scoreinfo_gpu_fallback_batches": str(
                int(sums.get("exact_scoreinfo_gpu_fallback_batches", 0))
            ),
            "exact_scoreinfo_gpu_wall_seconds": f"{sums.get('exact_scoreinfo_gpu_wall_seconds', 0.0):.6f}",
            "exact_scoreinfo_gpu_kernel_seconds": f"{sums.get('exact_scoreinfo_gpu_kernel_seconds', 0.0):.6f}",
            "exact_scoreinfo_gpu_h2d_seconds": f"{sums.get('exact_scoreinfo_gpu_h2d_seconds', 0.0):.6f}",
            "exact_scoreinfo_gpu_d2h_seconds": f"{sums.get('exact_scoreinfo_gpu_d2h_seconds', 0.0):.6f}",
            "exact_column_wall_seconds": f"{sums.get('exact_column_wall_seconds', 0.0):.6f}",
            "exact_column_kernel_seconds": f"{sums.get('exact_column_kernel_seconds', 0.0):.6f}",
            "gpu_util_avg_mean": read_gpu_avg(run_dir / "gpu_utilization_summary.csv"),
            "top5_score_digest": summary["top5_score_digest"],
            "top5_stability_digest": summary["top5_stability_digest"],
            "top5_nt_score_digest": summary["top5_nt_score_digest"],
            "run_work": str(run_dir),
        }
    )

summary_path = work / "summary.tsv"
with summary_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

best = None
for row in rows:
    if row["top5_all_equal"] != "true":
        continue
    if int(row["exact_scoreinfo_gpu_fallback_batches"]) != 0:
        continue
    if int(row["exact_scoreinfo_gpu_overflow_batches"]) != 0:
        continue
    if best is None or float(row["wall_seconds"]) < float(best["wall_seconds"]):
        best = row

decision_path = work / "decision.txt"
if best:
    decision_path.write_text(
        "\n".join(
            [
                f"best_top5_clean_label={best['label']}",
                f"best_top5_clean_max_per_task={best['exact_scoreinfo_gpu_max_per_task']}",
                f"best_top5_clean_wall_seconds={best['wall_seconds']}",
                f"best_top5_clean_speedup_vs_baseline={best['speedup_vs_baseline']}",
                f"best_top5_clean_exact_scoreinfo_gpu_wall_seconds={best['exact_scoreinfo_gpu_wall_seconds']}",
                f"best_top5_clean_exact_scoreinfo_gpu_kernel_seconds={best['exact_scoreinfo_gpu_kernel_seconds']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
else:
    decision_path.write_text("best_top5_clean_label=\n", encoding="utf-8")

print(summary_path.read_text(encoding="utf-8"), end="")
print(decision_path.read_text(encoding="utf-8"), end="")
PY
