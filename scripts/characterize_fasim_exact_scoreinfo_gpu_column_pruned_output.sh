#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_exact_scoreinfo_gpu_column_pruned_output"}"
TARGET="${TARGET:-}"
TARGET_PRESET="${TARGET_PRESET:-}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
TOPK="${TOPK:-5}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-16}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
BUILD_BIN="${BUILD_BIN:-0}"

if [[ "$TOPK" != "5" ]]; then
  echo "column-pruned exact scoreInfo characterization requires TOPK=5" >&2
  exit 1
fi

if [[ -z "$TARGET_PRESET" ]]; then
  if [[ -n "$TARGET" ]]; then
    TARGET_PRESET="custom"
  else
    TARGET_PRESET="small"
  fi
fi

case "$TARGET_PRESET" in
  small)
    TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa"}"
    ;;
  chr21_chr22)
    ;;
  custom)
    if [[ -z "$TARGET" ]]; then
      echo "TARGET_PRESET=custom requires TARGET" >&2
      exit 1
    fi
    ;;
  *)
    echo "unknown TARGET_PRESET: $TARGET_PRESET" >&2
    exit 1
    ;;
esac

if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

run_one() {
  local label="$1"
  local column_pruned="$2"
  local run_work="$WORK/runs/$label"
  local run_target="$TARGET"
  local column_env=()
  if [[ "$column_pruned" == "1" ]]; then
    column_env+=(EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1)
  fi
  if [[ "$TARGET_PRESET" == "chr21_chr22" ]]; then
    run_target="$run_work/inputs/chr21_chr22.fa"
  fi

  env \
    BIN="$BIN" \
    TARGET="$run_target" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    TOPK_SUMMARY_ONLY=1 \
    IN_PROCESS_TOPK=1 \
    GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    EXACT_COLUMN_SCOREINFO_GPU=1 \
    EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK="$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
    EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    "${column_env[@]}" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      >"$WORK/$label.stdout.log" \
      2>"$WORK/$label.stderr.log"
}

run_one "exact_pruned_output" 0
run_one "column_pruned_output" 1

python3 - "$WORK" <<'PY'
import csv
import sys
from pathlib import Path

work = Path(sys.argv[1])


def read_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            out[key] = value
    return out


def read_sums(path: Path) -> dict[str, float]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))

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
        "exact_scoreinfo_gpu_batches",
        "exact_scoreinfo_gpu_tasks",
        "exact_scoreinfo_gpu_overflow_batches",
        "exact_scoreinfo_gpu_fallback_batches",
        "exact_scoreinfo_gpu_pruned_output_batches",
        "exact_scoreinfo_gpu_pruned_output_input_groups",
        "exact_scoreinfo_gpu_pruned_output_kept_groups",
        "exact_scoreinfo_gpu_pruned_output_pruned_groups",
        "legacy_score_gpu_requests",
        "legacy_score_gpu_wall_seconds",
        "legacy_score_gpu_kernel_seconds",
        "legacy_score_gpu_h2d_seconds",
        "legacy_score_gpu_d2h_seconds",
        "exact_column_wall_seconds",
        "exact_column_kernel_seconds",
        "exact_column_h2d_seconds",
        "exact_column_d2h_seconds",
        "exact_scoreinfo_gpu_wall_seconds",
        "exact_scoreinfo_gpu_kernel_seconds",
        "exact_scoreinfo_gpu_h2d_seconds",
        "exact_scoreinfo_gpu_d2h_seconds",
        "gasal2_total_seconds",
    ]
    return {field: sum_field(field) for field in fields}


labels = ["exact_pruned_output", "column_pruned_output"]
base = read_kv(work / "runs" / labels[0] / "summary.txt")
base_digests = {
    "score": base["top5_score_digest"],
    "stability": base["top5_stability_digest"],
    "nt_score": base["top5_nt_score_digest"],
}
base_wall = float(base["wall_seconds"])

columns = [
    "label",
    "runner_exact_scoreinfo_gpu_column_pruned_output",
    "wall_seconds",
    "speedup_vs_exact_pruned",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_all_equal",
    "traceback_requests",
    "scoreinfo_groups",
    "exact_scoreinfo_gpu_batches",
    "exact_scoreinfo_gpu_tasks",
    "exact_scoreinfo_gpu_overflow_batches",
    "exact_scoreinfo_gpu_fallback_batches",
    "exact_scoreinfo_gpu_pruned_output_batches",
    "exact_scoreinfo_gpu_pruned_output_input_groups",
    "exact_scoreinfo_gpu_pruned_output_kept_groups",
    "exact_scoreinfo_gpu_pruned_output_pruned_groups",
    "legacy_score_gpu_requests",
    "legacy_score_gpu_wall_seconds",
    "legacy_score_gpu_kernel_seconds",
    "legacy_score_gpu_h2d_seconds",
    "legacy_score_gpu_d2h_seconds",
    "exact_column_wall_seconds",
    "exact_column_kernel_seconds",
    "exact_column_h2d_seconds",
    "exact_column_d2h_seconds",
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
rows: list[dict[str, str]] = []
for label in labels:
    run_dir = work / "runs" / label
    summary = read_kv(run_dir / "summary.txt")
    sums = read_sums(run_dir / "shard_benchmark_summary.tsv")
    wall = float(summary["wall_seconds"])
    score_equal = summary["top5_score_digest"] == base_digests["score"]
    stability_equal = summary["top5_stability_digest"] == base_digests["stability"]
    nt_equal = summary["top5_nt_score_digest"] == base_digests["nt_score"]
    rows.append(
        {
            "label": label,
            "runner_exact_scoreinfo_gpu_column_pruned_output": summary.get(
                "runner_exact_scoreinfo_gpu_column_pruned_output", ""
            ),
            "wall_seconds": f"{wall:.6f}",
            "speedup_vs_exact_pruned": f"{base_wall / wall:.6f}",
            "top5_score_equal": str(score_equal).lower(),
            "top5_stability_equal": str(stability_equal).lower(),
            "top5_nt_score_equal": str(nt_equal).lower(),
            "top5_all_equal": str(score_equal and stability_equal and nt_equal).lower(),
            "traceback_requests": str(int(sums["traceback_requests"])),
            "scoreinfo_groups": str(int(sums["scoreinfo_groups"])),
            "exact_scoreinfo_gpu_batches": str(int(sums["exact_scoreinfo_gpu_batches"])),
            "exact_scoreinfo_gpu_tasks": str(int(sums["exact_scoreinfo_gpu_tasks"])),
            "exact_scoreinfo_gpu_overflow_batches": str(int(sums["exact_scoreinfo_gpu_overflow_batches"])),
            "exact_scoreinfo_gpu_fallback_batches": str(int(sums["exact_scoreinfo_gpu_fallback_batches"])),
            "exact_scoreinfo_gpu_pruned_output_batches": str(int(sums["exact_scoreinfo_gpu_pruned_output_batches"])),
            "exact_scoreinfo_gpu_pruned_output_input_groups": str(int(sums["exact_scoreinfo_gpu_pruned_output_input_groups"])),
            "exact_scoreinfo_gpu_pruned_output_kept_groups": str(int(sums["exact_scoreinfo_gpu_pruned_output_kept_groups"])),
            "exact_scoreinfo_gpu_pruned_output_pruned_groups": str(int(sums["exact_scoreinfo_gpu_pruned_output_pruned_groups"])),
            "legacy_score_gpu_requests": str(int(sums["legacy_score_gpu_requests"])),
            "legacy_score_gpu_wall_seconds": f"{sums['legacy_score_gpu_wall_seconds']:.6f}",
            "legacy_score_gpu_kernel_seconds": f"{sums['legacy_score_gpu_kernel_seconds']:.6f}",
            "legacy_score_gpu_h2d_seconds": f"{sums['legacy_score_gpu_h2d_seconds']:.6f}",
            "legacy_score_gpu_d2h_seconds": f"{sums['legacy_score_gpu_d2h_seconds']:.6f}",
            "exact_column_wall_seconds": f"{sums['exact_column_wall_seconds']:.6f}",
            "exact_column_kernel_seconds": f"{sums['exact_column_kernel_seconds']:.6f}",
            "exact_column_h2d_seconds": f"{sums['exact_column_h2d_seconds']:.6f}",
            "exact_column_d2h_seconds": f"{sums['exact_column_d2h_seconds']:.6f}",
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
    writer.writerows(rows)

exact, column = rows
decision = [
    f"exact_pruned_wall_seconds={exact['wall_seconds']}",
    f"column_pruned_wall_seconds={column['wall_seconds']}",
    f"column_pruned_speedup_vs_exact_pruned={column['speedup_vs_exact_pruned']}",
    f"column_pruned_top5_all_equal={column['top5_all_equal']}",
    f"column_pruned_legacy_score_gpu_requests={column['legacy_score_gpu_requests']}",
    f"column_pruned_exact_scoreinfo_gpu_overflow_batches={column['exact_scoreinfo_gpu_overflow_batches']}",
    f"column_pruned_exact_scoreinfo_gpu_fallback_batches={column['exact_scoreinfo_gpu_fallback_batches']}",
    f"exact_scoreinfo_groups={exact['scoreinfo_groups']}",
    f"column_pruned_scoreinfo_groups={column['scoreinfo_groups']}",
]
(work / "decision.txt").write_text("\n".join(decision) + "\n", encoding="utf-8")
print(summary_path.read_text(encoding="utf-8"), end="")
print((work / "decision.txt").read_text(encoding="utf-8"), end="")
PY
