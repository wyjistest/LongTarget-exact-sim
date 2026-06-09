#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_exact_scoreinfo_gpu_pruned_output"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
TOPK="${TOPK:-5}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-10}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"

if [[ "$TOPK" != "5" ]]; then
  echo "exact scoreInfo GPU pruned-output characterization requires TOPK=5" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

run_one() {
  local label="$1"
  local pruned_output="$2"
  local run_work="$WORK/runs/$label"

  local pruned_env=()
  if [[ "$pruned_output" == "1" ]]; then
    pruned_env+=(EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1)
  fi

  env \
    TARGET="$TARGET" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    TOPK_SUMMARY_ONLY=1 \
    IN_PROCESS_TOPK=1 \
    GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    EXACT_COLUMN_SCOREINFO_GPU=1 \
    EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    "${pruned_env[@]}" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      >"$WORK/$label.stdout.log" \
      2>"$WORK/$label.stderr.log"
}

run_one "max${EXACT_SCOREINFO_GPU_MAX_PER_TASK}" 0
run_one "max${EXACT_SCOREINFO_GPU_MAX_PER_TASK}_pruned_output" 1

python3 - "$WORK" "$EXACT_SCOREINFO_GPU_MAX_PER_TASK" <<'PY'
import csv
import sys
from pathlib import Path

work = Path(sys.argv[1])
max_per_task = sys.argv[2]


def read_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def read_shard_sums(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    def sum_field(name: str) -> float:
        total = 0.0
        for row in rows:
            value = row.get(name, "")
            if value:
                total += float(value)
        return total

    fields = [
        "traceback_requests",
        "scoreinfo_groups",
        "scoreinfo_prune_input_groups",
        "scoreinfo_prune_kept_groups",
        "scoreinfo_prune_pruned_groups",
        "exact_scoreinfo_gpu_batches",
        "exact_scoreinfo_gpu_tasks",
        "exact_scoreinfo_gpu_overflow_batches",
        "exact_scoreinfo_gpu_fallback_batches",
        "exact_scoreinfo_gpu_pruned_output_batches",
        "exact_scoreinfo_gpu_pruned_output_input_groups",
        "exact_scoreinfo_gpu_pruned_output_kept_groups",
        "exact_scoreinfo_gpu_pruned_output_pruned_groups",
        "legacy_score_gpu_requests",
        "legacy_score_gpu_replacement_used",
        "legacy_score_gpu_replacement_fallbacks",
        "legacy_score_gpu_mismatches",
        "legacy_score_gpu_min_score_mismatches",
        "legacy_score_gpu_wall_seconds",
        "legacy_score_gpu_kernel_seconds",
        "legacy_score_gpu_h2d_seconds",
        "legacy_score_gpu_d2h_seconds",
        "exact_scoreinfo_gpu_wall_seconds",
        "exact_scoreinfo_gpu_kernel_seconds",
        "exact_scoreinfo_gpu_h2d_seconds",
        "exact_scoreinfo_gpu_d2h_seconds",
        "gasal2_total_seconds",
    ]
    return {field: sum_field(field) for field in fields}


labels = [f"max{max_per_task}", f"max{max_per_task}_pruned_output"]
baseline = read_kv(work / "runs" / labels[0] / "summary.txt")
baseline_wall = float(baseline["wall_seconds"])
baseline_digests = {
    "score": baseline["top5_score_digest"],
    "stability": baseline["top5_stability_digest"],
    "nt_score": baseline["top5_nt_score_digest"],
}

columns = [
    "label",
    "exact_scoreinfo_gpu_max_per_task",
    "runner_exact_scoreinfo_gpu_pruned_output",
    "wall_seconds",
    "speedup_vs_max",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_all_equal",
    "traceback_requests",
    "scoreinfo_groups",
    "scoreinfo_prune_input_groups",
    "scoreinfo_prune_kept_groups",
    "scoreinfo_prune_pruned_groups",
    "exact_scoreinfo_gpu_batches",
    "exact_scoreinfo_gpu_tasks",
    "exact_scoreinfo_gpu_overflow_batches",
    "exact_scoreinfo_gpu_fallback_batches",
    "exact_scoreinfo_gpu_pruned_output_batches",
    "exact_scoreinfo_gpu_pruned_output_input_groups",
    "exact_scoreinfo_gpu_pruned_output_kept_groups",
    "exact_scoreinfo_gpu_pruned_output_pruned_groups",
    "legacy_score_gpu_requests",
    "legacy_score_gpu_replacement_used",
    "legacy_score_gpu_replacement_fallbacks",
    "legacy_score_gpu_mismatches",
    "legacy_score_gpu_min_score_mismatches",
    "legacy_score_gpu_wall_seconds",
    "legacy_score_gpu_kernel_seconds",
    "legacy_score_gpu_h2d_seconds",
    "legacy_score_gpu_d2h_seconds",
    "exact_scoreinfo_gpu_wall_seconds",
    "exact_scoreinfo_gpu_kernel_seconds",
    "exact_scoreinfo_gpu_h2d_seconds",
    "exact_scoreinfo_gpu_d2h_seconds",
    "gasal2_total_seconds",
    "top5_score_digest",
    "top5_stability_digest",
    "top5_nt_score_digest",
    "run_work",
]

out_rows: list[dict[str, str]] = []
for label in labels:
    run_dir = work / "runs" / label
    summary = read_kv(run_dir / "summary.txt")
    sums = read_shard_sums(run_dir / "shard_benchmark_summary.tsv")
    wall = float(summary["wall_seconds"])
    score_equal = summary["top5_score_digest"] == baseline_digests["score"]
    stability_equal = summary["top5_stability_digest"] == baseline_digests["stability"]
    nt_equal = summary["top5_nt_score_digest"] == baseline_digests["nt_score"]
    out_rows.append(
        {
            "label": label,
            "exact_scoreinfo_gpu_max_per_task": summary.get("runner_exact_scoreinfo_gpu_max_per_task", ""),
            "runner_exact_scoreinfo_gpu_pruned_output": summary.get("runner_exact_scoreinfo_gpu_pruned_output", ""),
            "wall_seconds": f"{wall:.6f}",
            "speedup_vs_max": f"{baseline_wall / wall:.6f}",
            "top5_score_equal": str(score_equal).lower(),
            "top5_stability_equal": str(stability_equal).lower(),
            "top5_nt_score_equal": str(nt_equal).lower(),
            "top5_all_equal": str(score_equal and stability_equal and nt_equal).lower(),
            "traceback_requests": str(int(sums["traceback_requests"])),
            "scoreinfo_groups": str(int(sums["scoreinfo_groups"])),
            "scoreinfo_prune_input_groups": str(int(sums["scoreinfo_prune_input_groups"])),
            "scoreinfo_prune_kept_groups": str(int(sums["scoreinfo_prune_kept_groups"])),
            "scoreinfo_prune_pruned_groups": str(int(sums["scoreinfo_prune_pruned_groups"])),
            "exact_scoreinfo_gpu_batches": str(int(sums["exact_scoreinfo_gpu_batches"])),
            "exact_scoreinfo_gpu_tasks": str(int(sums["exact_scoreinfo_gpu_tasks"])),
            "exact_scoreinfo_gpu_overflow_batches": str(int(sums["exact_scoreinfo_gpu_overflow_batches"])),
            "exact_scoreinfo_gpu_fallback_batches": str(int(sums["exact_scoreinfo_gpu_fallback_batches"])),
            "exact_scoreinfo_gpu_pruned_output_batches": str(int(sums["exact_scoreinfo_gpu_pruned_output_batches"])),
            "exact_scoreinfo_gpu_pruned_output_input_groups": str(int(sums["exact_scoreinfo_gpu_pruned_output_input_groups"])),
            "exact_scoreinfo_gpu_pruned_output_kept_groups": str(int(sums["exact_scoreinfo_gpu_pruned_output_kept_groups"])),
            "exact_scoreinfo_gpu_pruned_output_pruned_groups": str(int(sums["exact_scoreinfo_gpu_pruned_output_pruned_groups"])),
            "legacy_score_gpu_requests": str(int(sums["legacy_score_gpu_requests"])),
            "legacy_score_gpu_replacement_used": str(int(sums["legacy_score_gpu_replacement_used"])),
            "legacy_score_gpu_replacement_fallbacks": str(int(sums["legacy_score_gpu_replacement_fallbacks"])),
            "legacy_score_gpu_mismatches": str(int(sums["legacy_score_gpu_mismatches"])),
            "legacy_score_gpu_min_score_mismatches": str(int(sums["legacy_score_gpu_min_score_mismatches"])),
            "legacy_score_gpu_wall_seconds": f"{sums['legacy_score_gpu_wall_seconds']:.6f}",
            "legacy_score_gpu_kernel_seconds": f"{sums['legacy_score_gpu_kernel_seconds']:.6f}",
            "legacy_score_gpu_h2d_seconds": f"{sums['legacy_score_gpu_h2d_seconds']:.6f}",
            "legacy_score_gpu_d2h_seconds": f"{sums['legacy_score_gpu_d2h_seconds']:.6f}",
            "exact_scoreinfo_gpu_wall_seconds": f"{sums['exact_scoreinfo_gpu_wall_seconds']:.6f}",
            "exact_scoreinfo_gpu_kernel_seconds": f"{sums['exact_scoreinfo_gpu_kernel_seconds']:.6f}",
            "exact_scoreinfo_gpu_h2d_seconds": f"{sums['exact_scoreinfo_gpu_h2d_seconds']:.6f}",
            "exact_scoreinfo_gpu_d2h_seconds": f"{sums['exact_scoreinfo_gpu_d2h_seconds']:.6f}",
            "gasal2_total_seconds": f"{sums['gasal2_total_seconds']:.6f}",
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
    writer.writerows(out_rows)

baseline_row, pruned_row = out_rows
decision = [
    f"baseline_label={baseline_row['label']}",
    f"baseline_wall_seconds={baseline_row['wall_seconds']}",
    f"pruned_output_label={pruned_row['label']}",
    f"pruned_output_wall_seconds={pruned_row['wall_seconds']}",
    f"pruned_output_speedup_vs_max={pruned_row['speedup_vs_max']}",
    f"pruned_output_top5_all_equal={pruned_row['top5_all_equal']}",
    f"pruned_output_overflow_batches={pruned_row['exact_scoreinfo_gpu_overflow_batches']}",
    f"pruned_output_fallback_batches={pruned_row['exact_scoreinfo_gpu_fallback_batches']}",
    f"pruned_output_d2h_seconds={pruned_row['exact_scoreinfo_gpu_d2h_seconds']}",
]
(work / "decision.txt").write_text("\n".join(decision) + "\n", encoding="utf-8")

print(summary_path.read_text(encoding="utf-8"), end="")
print((work / "decision.txt").read_text(encoding="utf-8"), end="")
PY
