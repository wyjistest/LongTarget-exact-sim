#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_scoreinfo_prune_sweep"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_VALUES="${PRUNE_VALUES:-16 12 10 9 8}"
BASELINE_VALUE="${BASELINE_VALUE:-artifact}"
TOPK="${TOPK:-5}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
EXACT_COLUMN_SCOREINFO_GPU="${EXACT_COLUMN_SCOREINFO_GPU:-0}"
EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK:-}"

if [[ "$TOPK" != "5" ]]; then
  echo "scoreInfo-prune sweep requires TOPK=5" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

run_one() {
  local label="$1"
  local prune_value="$2"
  local run_work="$WORK/runs/$label"

  if [[ "$label" == "$BASELINE_VALUE" ]]; then
    TARGET="$TARGET" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    TOPK_SUMMARY_ONLY=1 \
    IN_PROCESS_TOPK=1 \
    EXACT_COLUMN_SCOREINFO_GPU="$EXACT_COLUMN_SCOREINFO_GPU" \
    EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK" \
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
    GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$prune_value" \
    EXACT_COLUMN_SCOREINFO_GPU="$EXACT_COLUMN_SCOREINFO_GPU" \
    EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      >"$WORK/$label.stdout.log" \
      2>"$WORK/$label.stderr.log"
  fi
}

run_one "$BASELINE_VALUE" ""
for value in $PRUNE_VALUES; do
  run_one "prune${value}" "$value"
done

python3 - "$WORK" "$BASELINE_VALUE" "$PRUNE_VALUES" <<'PY'
import csv
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
baseline_label = sys.argv[2]
prune_values = sys.argv[3].split()
row_key_columns = [
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "Strand",
    "Rule",
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Score",
    "Nt(bp)",
    "MeanIdentity(%)",
    "MeanStability",
]


def read_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


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
        "scoreinfo_prune_pruned_groups": sum_field("scoreinfo_prune_pruned_groups"),
        "scoreinfo_prune_kept_groups": sum_field("scoreinfo_prune_kept_groups"),
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
        "exact_column_kernel_seconds": sum_field("exact_column_kernel_seconds"),
        "exact_column_wall_seconds": sum_field("exact_column_wall_seconds"),
        "exact_column_h2d_seconds": sum_field("exact_column_h2d_seconds"),
        "exact_column_d2h_seconds": sum_field("exact_column_d2h_seconds"),
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


def row_key(row: dict[str, str]) -> str:
    return "\t".join(row.get(column, "") for column in row_key_columns)


def row_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value else float("-inf")


def rank_key(row: dict[str, str], mode: str) -> tuple[float, ...]:
    if mode == "score":
        return (
            row_float(row, "Score"),
            row_float(row, "Nt(bp)"),
            row_float(row, "MeanStability"),
        )
    if mode == "stability":
        return (
            row_float(row, "MeanStability"),
            row_float(row, "Nt(bp)"),
            row_float(row, "Score"),
        )
    if mode == "nt_score":
        return (
            row_float(row, "Nt(bp)"),
            row_float(row, "Score"),
            row_float(row, "MeanStability"),
        )
    raise ValueError(f"unknown mode: {mode}")


def output_paths(run_dir: Path) -> list[Path]:
    report_path = run_dir / "run" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    paths = []
    for shard in report.get("per_shard", []):
        output_path = shard.get("run", {}).get("output_path")
        if output_path:
            paths.append(Path(output_path))
    return paths


def lite_rows(run_dir: Path) -> list[dict[str, str]]:
    dedup: dict[str, dict[str, str]] = {}
    for path in output_paths(run_dir):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                dedup[row_key(row)] = row
    return list(dedup.values())


def topk_rows(run_dir: Path, mode: str, k: int = 5) -> list[dict[str, str]]:
    return sorted(
        lite_rows(run_dir),
        key=lambda row: (rank_key(row, mode), row_key(row)),
        reverse=True,
    )[:k]


def row_summary(row: dict[str, str]) -> str:
    return (
        f"chr={row.get('Chr', '')};"
        f"genome={row.get('StartInGenome', '')}-{row.get('EndInGenome', '')};"
        f"strand={row.get('Strand', '')};"
        f"rule={row.get('Rule', '')};"
        f"query={row.get('QueryStart', '')}-{row.get('QueryEnd', '')};"
        f"seq={row.get('StartInSeq', '')}-{row.get('EndInSeq', '')};"
        f"direction={row.get('Direction', '')};"
        f"score={row.get('Score', '')};"
        f"nt={row.get('Nt(bp)', '')};"
        f"identity={row.get('MeanIdentity(%)', '')};"
        f"stability={row.get('MeanStability', '')}"
    )


labels = [baseline_label] + [f"prune{value}" for value in prune_values]
baseline = read_kv(work / "runs" / baseline_label / "summary.txt")
baseline_wall = float(baseline["wall_seconds"])
baseline_digests = {
    "score": baseline["top5_score_digest"],
    "stability": baseline["top5_stability_digest"],
    "nt_score": baseline["top5_nt_score_digest"],
}

columns = [
    "label",
    "max_per_task",
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
    "exact_column_kernel_seconds",
    "exact_column_wall_seconds",
    "exact_column_h2d_seconds",
    "exact_column_d2h_seconds",
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
    max_per_task = "" if label == baseline_label else summary.get("gasal2_scoreinfo_prune_max_per_task", "")
    runner_exact_max_per_task = summary.get("runner_exact_scoreinfo_gpu_max_per_task", "")
    rows.append(
        {
            "label": label,
            "max_per_task": max_per_task,
            "runner_exact_scoreinfo_gpu_max_per_task": runner_exact_max_per_task,
            "wall_seconds": f"{wall:.6f}",
            "speedup_vs_baseline": f"{baseline_wall / wall:.6f}",
            "top5_score_equal": str(score_equal).lower(),
            "top5_stability_equal": str(stability_equal).lower(),
            "top5_nt_score_equal": str(nt_equal).lower(),
            "top5_all_equal": str(score_equal and stability_equal and nt_equal).lower(),
            "traceback_requests": str(int(sums.get("traceback_requests", 0))),
            "scoreinfo_groups": str(int(sums.get("scoreinfo_groups", 0))),
            "scoreinfo_pruned_groups": str(int(sums.get("scoreinfo_prune_pruned_groups", 0))),
            "scoreinfo_kept_groups": str(int(sums.get("scoreinfo_prune_kept_groups", 0))),
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
            "exact_column_kernel_seconds": f"{sums.get('exact_column_kernel_seconds', 0.0):.6f}",
            "exact_column_wall_seconds": f"{sums.get('exact_column_wall_seconds', 0.0):.6f}",
            "exact_column_h2d_seconds": f"{sums.get('exact_column_h2d_seconds', 0.0):.6f}",
            "exact_column_d2h_seconds": f"{sums.get('exact_column_d2h_seconds', 0.0):.6f}",
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
    if row["label"] == baseline_label or row["top5_all_equal"] != "true":
        continue
    if best is None or float(row["wall_seconds"]) < float(best["wall_seconds"]):
        best = row

decision_path = work / "decision.txt"
if best:
    decision_path.write_text(
        "\n".join(
            [
                f"best_top5_clean_label={best['label']}",
                f"best_top5_clean_max_per_task={best['max_per_task']}",
                f"best_top5_clean_wall_seconds={best['wall_seconds']}",
                f"best_top5_clean_speedup_vs_baseline={best['speedup_vs_baseline']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
else:
    decision_path.write_text("best_top5_clean_label=\n", encoding="utf-8")

diff_columns = [
    "label",
    "mode",
    "kind",
    "rank",
    "row",
]
diff_rows: list[dict[str, str]] = []
for row in rows:
    label = row["label"]
    if label == baseline_label or row["top5_all_equal"] == "true":
        continue
    run_dir = work / "runs" / label
    baseline_dir = work / "runs" / baseline_label
    for mode in ("score", "stability", "nt_score"):
        baseline_top = topk_rows(baseline_dir, mode)
        candidate_top = topk_rows(run_dir, mode)
        baseline_by_key = {row_key(item): (index + 1, item) for index, item in enumerate(baseline_top)}
        candidate_by_key = {row_key(item): (index + 1, item) for index, item in enumerate(candidate_top)}
        for key, (rank, item) in baseline_by_key.items():
            if key not in candidate_by_key:
                diff_rows.append(
                    {
                        "label": label,
                        "mode": mode,
                        "kind": "missing",
                        "rank": str(rank),
                        "row": row_summary(item),
                    }
                )
        for key, (rank, item) in candidate_by_key.items():
            if key not in baseline_by_key:
                diff_rows.append(
                    {
                        "label": label,
                        "mode": mode,
                        "kind": "extra",
                        "rank": str(rank),
                        "row": row_summary(item),
                    }
                )

diff_path = work / "top5_diff.tsv"
with diff_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=diff_columns, delimiter="\t")
    writer.writeheader()
    writer.writerows(diff_rows)

print(summary_path.read_text(encoding="utf-8"), end="")
print(decision_path.read_text(encoding="utf-8"), end="")
if diff_rows:
    print(f"top5_diff={diff_path}")
PY
