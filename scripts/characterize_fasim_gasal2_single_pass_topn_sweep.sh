#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_single_pass_topn_sweep"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
TOPK="${TOPK:-5}"
TOPN_VALUES="${TOPN_VALUES:-64 128 256}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-10}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
SINGLE_PASS_GASAL2_BATCH="${SINGLE_PASS_GASAL2_BATCH:-10000}"

if [[ "$TOPK" != "5" ]]; then
  echo "single-pass topN sweep requires TOPK=5" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

run_exact() {
  local run_work="$WORK/runs/exact_pruned_output"
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
    EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1 \
    BIN="$BIN" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      >"$WORK/exact_pruned_output.stdout.log" \
      2>"$WORK/exact_pruned_output.stderr.log"
}

run_single() {
  local topn="$1"
  local label="single_pass_topn${topn}"
  local run_work="$WORK/runs/$label"
  env \
    TARGET="$TARGET" \
    RNA="$RNA" \
    RULE="$RULE" \
    TOPK="$TOPK" \
    TOPK_SUMMARY_ONLY=1 \
    IN_PROCESS_TOPK=1 \
    GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    GASAL2_SINGLE_PASS_TOPN=1 \
    GASAL2_BATCH="$SINGLE_PASS_GASAL2_BATCH" \
    BIN="$BIN" \
    WORKERS="$WORKERS" \
    GPU_IDS="$GPU_IDS" \
    WORK="$run_work" \
    bash "$ROOT/scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh" \
      --env "FASIM_PREALIGN_CUDA_TOPK=$topn" \
      >"$WORK/$label.stdout.log" \
      2>"$WORK/$label.stderr.log"
}

run_exact
for topn in $TOPN_VALUES; do
  run_single "$topn"
done

python3 - "$WORK" "$TOPN_VALUES" <<'PY'
import csv
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
topn_values = sys.argv[2].split()
labels = ["exact_pruned_output"] + [f"single_pass_topn{v}" for v in topn_values]


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
        "single_pass_topn_batches",
        "single_pass_topn_tasks",
        "single_pass_topn_scoreinfo_groups",
        "legacy_score_gpu_requests",
        "exact_scoreinfo_gpu_batches",
        "exact_scoreinfo_gpu_wall_seconds",
        "exact_scoreinfo_gpu_kernel_seconds",
        "gasal2_total_seconds",
    ]
    return {field: sum_field(field) for field in fields}


baseline = read_kv(work / "runs" / "exact_pruned_output" / "summary.txt")
baseline_wall = float(baseline["wall_seconds"])
baseline_digests = {
    "score": baseline["top5_score_digest"],
    "stability": baseline["top5_stability_digest"],
    "nt_score": baseline["top5_nt_score_digest"],
}
baseline_report = json.loads(
    (work / "runs" / "exact_pruned_output" / "run" / "report.json").read_text(encoding="utf-8")
)
baseline_topk_keys = {
    mode: baseline_report["topk_summary"]["modes"][mode]["keys"]
    for mode in ("score", "stability", "nt_score")
}

columns = [
    "label",
    "topn",
    "wall_seconds",
    "speedup_vs_exact",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_all_equal",
    "traceback_requests",
    "scoreinfo_groups",
    "single_pass_topn_batches",
    "single_pass_topn_tasks",
    "single_pass_topn_scoreinfo_groups",
    "legacy_score_gpu_requests",
    "exact_scoreinfo_gpu_batches",
    "exact_scoreinfo_gpu_wall_seconds",
    "exact_scoreinfo_gpu_kernel_seconds",
    "gasal2_total_seconds",
    "top5_score_digest",
    "top5_stability_digest",
    "top5_nt_score_digest",
    "run_work",
]

rows = []
diff_rows = []
for label in labels:
    run_dir = work / "runs" / label
    summary = read_kv(run_dir / "summary.txt")
    sums = read_shard_sums(run_dir / "shard_benchmark_summary.tsv")
    report = json.loads((run_dir / "run" / "report.json").read_text(encoding="utf-8"))
    wall = float(summary["wall_seconds"])
    score_equal = summary["top5_score_digest"] == baseline_digests["score"]
    stability_equal = summary["top5_stability_digest"] == baseline_digests["stability"]
    nt_equal = summary["top5_nt_score_digest"] == baseline_digests["nt_score"]
    topn = "" if label == "exact_pruned_output" else label.replace("single_pass_topn", "")
    rows.append(
        {
            "label": label,
            "topn": topn,
            "wall_seconds": f"{wall:.6f}",
            "speedup_vs_exact": f"{baseline_wall / wall:.6f}",
            "top5_score_equal": str(score_equal).lower(),
            "top5_stability_equal": str(stability_equal).lower(),
            "top5_nt_score_equal": str(nt_equal).lower(),
            "top5_all_equal": str(score_equal and stability_equal and nt_equal).lower(),
            "traceback_requests": str(int(sums["traceback_requests"])),
            "scoreinfo_groups": str(int(sums["scoreinfo_groups"])),
            "single_pass_topn_batches": str(int(sums["single_pass_topn_batches"])),
            "single_pass_topn_tasks": str(int(sums["single_pass_topn_tasks"])),
            "single_pass_topn_scoreinfo_groups": str(int(sums["single_pass_topn_scoreinfo_groups"])),
            "legacy_score_gpu_requests": str(int(sums["legacy_score_gpu_requests"])),
            "exact_scoreinfo_gpu_batches": str(int(sums["exact_scoreinfo_gpu_batches"])),
            "exact_scoreinfo_gpu_wall_seconds": f"{sums['exact_scoreinfo_gpu_wall_seconds']:.6f}",
            "exact_scoreinfo_gpu_kernel_seconds": f"{sums['exact_scoreinfo_gpu_kernel_seconds']:.6f}",
            "gasal2_total_seconds": f"{sums['gasal2_total_seconds']:.6f}",
            "top5_score_digest": summary["top5_score_digest"],
            "top5_stability_digest": summary["top5_stability_digest"],
            "top5_nt_score_digest": summary["top5_nt_score_digest"],
            "run_work": str(run_dir),
        }
    )
    if label != "exact_pruned_output":
        for mode, baseline_keys in baseline_topk_keys.items():
            candidate_keys = report["topk_summary"]["modes"][mode]["keys"]
            baseline_set = set(baseline_keys)
            candidate_set = set(candidate_keys)
            for rank, key in enumerate(baseline_keys, 1):
                if key not in candidate_set:
                    diff_rows.append(
                        {
                            "label": label,
                            "mode": mode,
                            "diff_type": "missing_from_candidate",
                            "rank": str(rank),
                            "key": key,
                        }
                    )
            for rank, key in enumerate(candidate_keys, 1):
                if key not in baseline_set:
                    diff_rows.append(
                        {
                            "label": label,
                            "mode": mode,
                            "diff_type": "extra_in_candidate",
                            "rank": str(rank),
                            "key": key,
                        }
                    )

summary_path = work / "summary.tsv"
with summary_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

diff_path = work / "top5_diff.tsv"
with diff_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["label", "mode", "diff_type", "rank", "key"],
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(diff_rows)

clean = [r for r in rows if r["label"] != "exact_pruned_output" and r["top5_all_equal"] == "true"]
decision = [
    f"exact_wall_seconds={rows[0]['wall_seconds']}",
    f"topn_values={' '.join(topn_values)}",
    f"single_pass_top5_clean_labels={','.join(r['label'] for r in clean)}",
]
if clean:
    best = min(clean, key=lambda r: float(r["wall_seconds"]))
    decision.extend(
        [
            f"best_clean_label={best['label']}",
            f"best_clean_wall_seconds={best['wall_seconds']}",
            f"best_clean_speedup_vs_exact={best['speedup_vs_exact']}",
        ]
    )
else:
    decision.append("best_clean_label=")
(work / "decision.txt").write_text("\n".join(decision) + "\n", encoding="utf-8")

print(summary_path.read_text(encoding="utf-8"), end="")
print(diff_path.read_text(encoding="utf-8"), end="")
print((work / "decision.txt").read_text(encoding="utf-8"), end="")
PY
