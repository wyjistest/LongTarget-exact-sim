#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_prealign_max_tasks_probe"}"
SOURCE_DNA="${SOURCE_DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
TARGET="${TARGET:-}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
K="${K:-5}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
PREALIGN_CUDA_MAX_TASKS_VALUES="${PREALIGN_CUDA_MAX_TASKS_VALUES:-4096 8192 16384}"

if [[ "$K" != "5" ]]; then
  echo "GASAL2 preAlign max-tasks probe requires K=5" >&2
  exit 1
fi

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

if [[ -z "$TARGET" && ! -s "$SOURCE_DNA" ]]; then
  echo "missing source DNA: $SOURCE_DNA" >&2
  exit 1
fi
if [[ -n "$TARGET" && ! -s "$TARGET" ]]; then
  echo "missing target: $TARGET" >&2
  exit 1
fi
if [[ ! -s "$RNA" ]]; then
  echo "missing RNA: $RNA" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/runs"

if [[ -z "$TARGET" ]]; then
  TARGET="$WORK/inputs/target_two_records.fa"
  python3 - "$SOURCE_DNA" "$TARGET" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

lines = src.read_text(encoding="utf-8").splitlines()
if not lines or not lines[0].startswith(">"):
    raise SystemExit(f"expected FASTA record in {src}")
header = lines[0][1:].strip()
sequence = "".join(line.strip() for line in lines[1:] if line.strip())
if not sequence:
    raise SystemExit(f"empty FASTA sequence in {src}")

mid = len(sequence) // 2
records = [
    (f"{header}_part1", sequence[:mid]),
    (f"{header}_part2", sequence[mid:]),
]
with dst.open("w", encoding="utf-8") as handle:
    offset = 1
    for name, seq in records:
        start = offset
        end = offset + len(seq) - 1
        handle.write(f">{name}|{name}|{start}-{end}\n")
        for i in range(0, len(seq), 80):
            handle.write(seq[i : i + 80] + "\n")
        offset = end + 1
PY
fi

runner_gpu_args=()
if [[ -n "$GPU_IDS" ]]; then
  runner_gpu_args+=(--gpu-ids "$GPU_IDS")
fi

run_formal_default() {
  local run_work="$WORK/runs/formal_default"
  local start_seconds end_seconds
  start_seconds="$(date +%s.%N)"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$TARGET" \
    --rna "$RNA" \
    --rule "$RULE" \
    --work-dir "$run_work" \
    --manifest "$run_work/run_manifest.json" \
    --gasal2-top5-column-pruned-scoreinfo \
    --workers "$WORKERS" \
    "${runner_gpu_args[@]}" \
    --force \
    >"$WORK/formal_default.stdout.log" \
    2>"$WORK/formal_default.stderr.log"
  end_seconds="$(date +%s.%N)"
  awk -v start="$start_seconds" -v end="$end_seconds" \
    'BEGIN {printf "%.6f\n", end - start}' >"$run_work/wall_seconds.txt"
}

run_probe_value() {
  local value="$1"
  local label="max${value}"
  local run_work="$WORK/runs/$label"
  local start_seconds end_seconds
  start_seconds="$(date +%s.%N)"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$TARGET" \
    --rna "$RNA" \
    --rule "$RULE" \
    --work-dir "$run_work" \
    --manifest "$run_work/run_manifest.json" \
    --output-mode lite \
    --topk-summary "$K" \
    --topk-summary-only \
    --shard-output-topk-lite "$K" \
    --gasal2-top5-scoreinfo-prune-max-per-task 64 \
    --exact-scoreinfo-gpu-max-per-task 512 \
    --exact-scoreinfo-gpu-pruned-output \
    --exact-scoreinfo-gpu-column-pruned-output \
    --env "FASIM_PREALIGN_CUDA_MAX_TASKS=$value" \
    --env FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1 \
    --workers "$WORKERS" \
    "${runner_gpu_args[@]}" \
    --force \
    >"$WORK/$label.stdout.log" \
    2>"$WORK/$label.stderr.log"
  end_seconds="$(date +%s.%N)"
  awk -v start="$start_seconds" -v end="$end_seconds" \
    'BEGIN {printf "%.6f\n", end - start}' >"$run_work/wall_seconds.txt"
}

run_formal_default
for value in $PREALIGN_CUDA_MAX_TASKS_VALUES; do
  run_probe_value "$value"
done

python3 - "$WORK" "$PREALIGN_CUDA_MAX_TASKS_VALUES" <<'PY'
import csv
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
values = sys.argv[2].split()
labels = ["formal_default"] + [f"max{value}" for value in values]


def load_report(label: str) -> dict:
    return json.loads((work / "runs" / label / "report.json").read_text(encoding="utf-8"))


def wall_seconds(label: str) -> float:
    return float((work / "runs" / label / "wall_seconds.txt").read_text(encoding="utf-8"))


def metric(report: dict, key: str) -> int:
    return int(float(report.get("fasim_benchmark_sums", {}).get(key, 0)))


def metric_float(report: dict, key: str) -> float:
    return float(report.get("fasim_benchmark_sums", {}).get(key, 0.0))


formal = load_report("formal_default")
formal_wall = wall_seconds("formal_default")
formal_topk_payload = formal["topk_summary_payload_digest"]
formal_rows_payload = formal["topk_rows_payload_digest"]
formal_lite_digest = formal["topk_lite_digest"]

columns = [
    "label",
    "prealign_cuda_max_tasks",
    "result_contract",
    "shard_count",
    "wall_seconds",
    "speedup_vs_formal",
    "topk_payload_equal_vs_formal",
    "topk_rows_payload_equal_vs_formal",
    "topk_lite_equal_vs_formal",
    "scoreinfo_rank_observe_enabled_shards",
    "scoreinfo_rank_observe_rows",
    "scoreinfo_rank_observe_unknown_rows",
    "scoreinfo_rank_observe_max_rank",
    "gasal2_requests",
    "gasal2_score_requests",
    "gasal2_traceback_requests",
    "gasal2_total_seconds",
    "exact_scoreinfo_gpu_batches",
    "exact_scoreinfo_gpu_tasks",
    "exact_scoreinfo_gpu_overflow_batches",
    "exact_scoreinfo_gpu_fallback_batches",
    "exact_scoreinfo_gpu_wall_seconds",
    "exact_scoreinfo_gpu_kernel_seconds",
    "topk_summary_payload_digest",
    "topk_rows_payload_digest",
    "topk_lite_digest",
    "run_work",
]

rows = []
for label in labels:
    report = load_report(label)
    env = report.get("env_overrides", {})
    value = env.get("FASIM_PREALIGN_CUDA_MAX_TASKS", "formal_default")
    wall = wall_seconds(label)
    rows.append(
        {
            "label": label,
            "prealign_cuda_max_tasks": value,
            "result_contract": report["result_contract"],
            "shard_count": str(report["shard_count"]),
            "wall_seconds": f"{wall:.6f}",
            "speedup_vs_formal": f"{formal_wall / wall:.6f}",
            "topk_payload_equal_vs_formal": str(report["topk_summary_payload_digest"] == formal_topk_payload).lower(),
            "topk_rows_payload_equal_vs_formal": str(report["topk_rows_payload_digest"] == formal_rows_payload).lower(),
            "topk_lite_equal_vs_formal": str(report["topk_lite_digest"] == formal_lite_digest).lower(),
            "scoreinfo_rank_observe_enabled_shards": str(metric(report, "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled")),
            "scoreinfo_rank_observe_rows": str(metric(report, "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows")),
            "scoreinfo_rank_observe_unknown_rows": str(metric(report, "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows")),
            "scoreinfo_rank_observe_max_rank": str(metric(report, "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank")),
            "gasal2_requests": str(metric(report, "fasim_gasal2_requests")),
            "gasal2_score_requests": str(metric(report, "fasim_gasal2_score_requests")),
            "gasal2_traceback_requests": str(metric(report, "fasim_gasal2_traceback_requests")),
            "gasal2_total_seconds": f"{metric_float(report, 'fasim_gasal2_total_seconds'):.6f}",
            "exact_scoreinfo_gpu_batches": str(metric(report, "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches")),
            "exact_scoreinfo_gpu_tasks": str(metric(report, "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks")),
            "exact_scoreinfo_gpu_overflow_batches": str(metric(report, "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches")),
            "exact_scoreinfo_gpu_fallback_batches": str(metric(report, "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches")),
            "exact_scoreinfo_gpu_wall_seconds": f"{metric_float(report, 'fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds'):.6f}",
            "exact_scoreinfo_gpu_kernel_seconds": f"{metric_float(report, 'fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds'):.6f}",
            "topk_summary_payload_digest": report["topk_summary_payload_digest"],
            "topk_rows_payload_digest": report["topk_rows_payload_digest"],
            "topk_lite_digest": report["topk_lite_digest"],
            "run_work": str(work / "runs" / label),
        }
    )

summary_path = work / "summary.tsv"
with summary_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

best = None
for row in rows:
    if row["topk_payload_equal_vs_formal"] != "true":
        continue
    if row["topk_rows_payload_equal_vs_formal"] != "true":
        continue
    if row["topk_lite_equal_vs_formal"] != "true":
        continue
    if int(row["exact_scoreinfo_gpu_overflow_batches"]) != 0:
        continue
    if int(row["exact_scoreinfo_gpu_fallback_batches"]) != 0:
        continue
    if best is None or float(row["wall_seconds"]) < float(best["wall_seconds"]):
        best = row

if best is None:
    raise SystemExit("no top5-clean max-tasks row")

(work / "decision.txt").write_text(
    "\n".join(
        [
            f"best_top5_clean_label={best['label']}",
            f"best_top5_clean_prealign_cuda_max_tasks={best['prealign_cuda_max_tasks']}",
            f"best_top5_clean_wall_seconds={best['wall_seconds']}",
            f"best_top5_clean_speedup_vs_formal={best['speedup_vs_formal']}",
            f"best_top5_clean_exact_scoreinfo_gpu_batches={best['exact_scoreinfo_gpu_batches']}",
            f"best_top5_clean_exact_scoreinfo_gpu_wall_seconds={best['exact_scoreinfo_gpu_wall_seconds']}",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print(summary_path)
print(work / "decision.txt")
PY
