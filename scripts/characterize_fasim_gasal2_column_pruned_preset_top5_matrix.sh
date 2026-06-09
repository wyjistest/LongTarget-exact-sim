#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix"}"
TARGET_PRESETS="${TARGET_PRESETS:-small}"
REPEATS="${REPEATS:-1}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
TOPK="${TOPK:-5}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"
BUILD_BIN="${BUILD_BIN:-1}"
CHR21="${CHR21:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr21.fa.gz"}"
CHR22="${CHR22:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr22.fa.gz"}"
GROUP_TARGET_RECORDS="${GROUP_TARGET_RECORDS:-}"

if [[ "$TOPK" != "5" ]]; then
  echo "column-pruned preset top5 matrix requires TOPK=5" >&2
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

resolve_target() {
  local preset="$1"
  local run_work="$2"
  case "$preset" in
    small)
      printf '%s\n' "$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa"
      ;;
    chr21_chr22)
      printf '%s\n' "$run_work/inputs/chr21_chr22.fa"
      ;;
    *)
      if [[ -s "$preset" ]]; then
        printf '%s\n' "$preset"
      else
        echo "unknown TARGET_PRESET or missing target: $preset" >&2
        exit 1
      fi
      ;;
  esac
}

prepare_target() {
  local preset="$1"
  local target="$2"
  case "$preset" in
    chr21_chr22)
      if [[ ! -s "$CHR21" ]]; then
        echo "missing CHR21 FASTA gzip: $CHR21" >&2
        exit 1
      fi
      if [[ ! -s "$CHR22" ]]; then
        echo "missing CHR22 FASTA gzip: $CHR22" >&2
        exit 1
      fi
      mkdir -p "$(dirname "$target")"
      gzip -dc "$CHR21" >"$target"
      gzip -dc "$CHR22" >>"$target"
      ;;
  esac
}

preset_label() {
  local preset="$1"
  local base
  local safe
  case "$preset" in
    small|chr21_chr22)
      printf '%s\n' "$preset"
      ;;
    *)
      base="$(basename "$preset")"
      base="${base%.gz}"
      base="${base%.fa}"
      base="${base%.fasta}"
      safe="$(printf '%s' "$base" | tr -c 'A-Za-z0-9_.-' '_')"
      printf '%s\n' "${safe:-custom_target}"
      ;;
  esac
}

run_one() {
  local preset="$1"
  local repeat="$2"
  local label
  label="$(preset_label "$preset")"
  local run_work="$WORK/runs/${label}_r${repeat}"
  local target
  target="$(resolve_target "$preset" "$run_work")"
  prepare_target "$preset" "$target"
  local runner_gpu_args=()
  if [[ -n "$GPU_IDS" ]]; then
    runner_gpu_args+=(--gpu-ids "$GPU_IDS")
  fi
  local runner_group_args=()
  if [[ -n "$GROUP_TARGET_RECORDS" ]]; then
    runner_group_args+=(--group-target-records "$GROUP_TARGET_RECORDS")
  fi

  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$RNA" \
    --rule "$RULE" \
    --work-dir "$run_work/cpu_summary" \
    --output-mode lite \
    --topk-summary "$TOPK" \
    --topk-summary-only \
    --workers "$WORKERS" \
    "${runner_gpu_args[@]}" \
    "${runner_group_args[@]}" \
    --force \
    >"$WORK/${label}_r${repeat}_cpu.stdout.log" \
    2>"$WORK/${label}_r${repeat}_cpu.stderr.log"

  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$RNA" \
    --rule "$RULE" \
    --work-dir "$run_work/column_pruned_preset" \
    --output-mode lite \
    --topk-summary "$TOPK" \
    --topk-summary-only \
    --gasal2-top5-column-pruned-scoreinfo \
    --workers "$WORKERS" \
    "${runner_gpu_args[@]}" \
    "${runner_group_args[@]}" \
    --force \
    >"$WORK/${label}_r${repeat}_preset.stdout.log" \
    2>"$WORK/${label}_r${repeat}_preset.stderr.log"
}

for preset in $TARGET_PRESETS; do
  for repeat in $(seq 1 "$REPEATS"); do
    run_one "$preset" "$repeat"
  done
done

python3 - "$WORK" "$TARGET_PRESETS" "$REPEATS" "$ROOT" <<'PY'
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path

work = Path(sys.argv[1])
presets = sys.argv[2].split()
repeats = int(sys.argv[3])
root = Path(sys.argv[4])


def preset_label(preset: str) -> str:
    if preset in {"small", "chr21_chr22"}:
        return preset
    name = Path(preset).name
    for suffix in (".gz", ".fa", ".fasta"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    safe = "".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in name)
    return safe or "custom_target"


def metric(path: Path, key: str) -> str:
    prefix = f"{key}="
    try:
        for line in path.read_text(errors="replace").splitlines():
            if line.startswith(prefix):
                return line[len(prefix) :]
    except FileNotFoundError:
        return ""
    return ""


def stderr_paths(report: dict) -> list[Path]:
    return [
        Path(shard["run"]["stderr_path"])
        for shard in report.get("per_shard", [])
        if shard.get("run", {}).get("stderr_path")
    ]


def metric_sum(report: dict, key: str) -> float:
    total = 0.0
    for path in stderr_paths(report):
        value = metric(path, key)
        if value:
            total += float(value)
    return total


def check_artifacts(cpu_report: Path, candidate_report: Path) -> bool:
    checker = root / "scripts" / "check_topk_summary_digest_integrity.py"
    subprocess.run(
        [sys.executable, str(checker), "--report", str(cpu_report)],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(checker),
            "--report",
            str(candidate_report),
            "--same-payload-as",
            str(cpu_report),
        ],
        check=True,
    )
    return True


columns = [
    "target_preset",
    "repeat",
    "artifact_checked",
    "group_target_records",
    "cpu_shard_count",
    "preset_shard_count",
    "cpu_worker_wall_sum_seconds",
    "preset_worker_wall_sum_seconds",
    "speedup_vs_cpu_worker_wall_sum",
    "cpu_max_worker_wall_seconds",
    "preset_max_worker_wall_seconds",
    "speedup_vs_cpu_max_worker_wall",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "top5_all_equal",
    "preset_active_path",
    "preset_gasal2_requested_shards",
    "preset_gasal2_active_shards",
    "preset_exact_scoreinfo_gpu_enabled_shards",
    "preset_gasal2_requests",
    "preset_exact_scoreinfo_gpu_tasks",
    "preset_gasal2_fallbacks",
    "preset_length_guard_fallbacks",
    "preset_legacy_score_gpu_requests",
    "preset_exact_column_wall_seconds",
    "preset_exact_scoreinfo_gpu_wall_seconds",
    "preset_overflow_batches",
    "preset_fallback_batches",
    "preset_gasal2_total_seconds",
    "preset_traceback_requests",
    "preset_score_digest",
    "preset_stability_digest",
    "preset_nt_score_digest",
    "run_work",
]
rows: list[dict[str, str]] = []
for preset in presets:
    for repeat in range(1, repeats + 1):
        run_work = work / "runs" / f"{preset_label(preset)}_r{repeat}"
        cpu_report = run_work / "cpu_summary" / "report.json"
        candidate_report = run_work / "column_pruned_preset" / "report.json"
        artifact_checked = check_artifacts(cpu_report, candidate_report)
        cpu = json.loads(cpu_report.read_text(encoding="utf-8"))
        candidate = json.loads(candidate_report.read_text(encoding="utf-8"))
        if cpu["run_status"] != "completed":
            raise SystemExit(f"CPU run incomplete for {preset} repeat {repeat}")
        if candidate["run_status"] != "completed":
            raise SystemExit(f"candidate run incomplete for {preset} repeat {repeat}")
        if cpu["topk_summary_only"] is not True or cpu["shard_output_topk_lite"] is not None:
            raise SystemExit(f"CPU baseline is not the full top5-summary authority for {preset} repeat {repeat}")
        if candidate["topk_summary_only"] is not True:
            raise SystemExit(f"candidate top5-summary-only mode is disabled for {preset} repeat {repeat}")
        if candidate["topk_summary_raw_path"] is not True:
            raise SystemExit(f"candidate did not use raw topK summary path for {preset} repeat {repeat}")
        if candidate["shard_output_topk_lite"] != 5:
            raise SystemExit(f"candidate shard output topK is not 5 for {preset} repeat {repeat}")
        if candidate["gasal2_top5_column_pruned_scoreinfo"] is not True:
            raise SystemExit(f"candidate column-pruned GASAL2 preset is disabled for {preset} repeat {repeat}")
        if candidate["gasal2_top5_scoreinfo_prune_max_per_task"] != 64:
            raise SystemExit(f"candidate scoreInfo prune cap is not 64 for {preset} repeat {repeat}")
        if candidate["exact_scoreinfo_gpu_max_per_task"] != 512:
            raise SystemExit(f"candidate exact scoreInfo GPU cap is not 512 for {preset} repeat {repeat}")
        if candidate["exact_scoreinfo_gpu_pruned_output"] is not True:
            raise SystemExit(f"candidate exact scoreInfo GPU pruned output is disabled for {preset} repeat {repeat}")
        if candidate["exact_scoreinfo_gpu_column_pruned_output"] is not True:
            raise SystemExit(f"candidate exact-column pruned output is disabled for {preset} repeat {repeat}")
        env = candidate.get("env_overrides", {})
        expected_env = {
            "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
            "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
            "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
            "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "64",
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU": "1",
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK": "512",
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT": "1",
            "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT": "1",
            "FASIM_OUTPUT_TOPK_LITE": "5",
        }
        for key, value in expected_env.items():
            if env.get(key) != value:
                raise SystemExit(
                    f"candidate env {key}={env.get(key)!r}, expected {value!r} "
                    f"for {preset} repeat {repeat}"
                )
        if any(shard.get("raw_topk_only") is not True for shard in candidate.get("per_shard", [])):
            raise SystemExit(f"candidate shard raw topK output is disabled for {preset} repeat {repeat}")
        if any(int(shard.get("records", 0)) > 15 for shard in candidate.get("per_shard", [])):
            raise SystemExit(f"candidate shard emitted more than top5*3 lite rows for {preset} repeat {repeat}")
        cpu_modes = cpu["topk_summary"]["modes"]
        candidate_modes = candidate["topk_summary"]["modes"]
        score_equal = candidate_modes["score"] == cpu_modes["score"]
        stability_equal = candidate_modes["stability"] == cpu_modes["stability"]
        nt_equal = candidate_modes["nt_score"] == cpu_modes["nt_score"]
        cpu_worker_walls = [float(worker["wall_seconds"]) for worker in cpu["per_worker"]]
        candidate_worker_walls = [float(worker["wall_seconds"]) for worker in candidate["per_worker"]]
        cpu_wall_sum = sum(cpu_worker_walls)
        candidate_wall_sum = sum(candidate_worker_walls)
        cpu_wall_max = max(cpu_worker_walls) if cpu_worker_walls else 0.0
        candidate_wall_max = max(candidate_worker_walls) if candidate_worker_walls else 0.0
        benchmark_shards = int(candidate.get("fasim_benchmark_shards") or candidate.get("shard_count") or 0)
        gasal2_requested_shards = int(metric_sum(candidate, "benchmark.fasim_top5_gasal2_gpu_scoreinfo_requested"))
        gasal2_active_shards = int(metric_sum(candidate, "benchmark.fasim_top5_gasal2_gpu_scoreinfo_active"))
        exact_scoreinfo_gpu_enabled_shards = int(
            metric_sum(candidate, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled")
        )
        gasal2_requests = int(metric_sum(candidate, "benchmark.fasim_gasal2_requests"))
        gasal2_traceback_requests = int(metric_sum(candidate, "benchmark.fasim_gasal2_traceback_requests"))
        exact_scoreinfo_gpu_tasks = int(
            metric_sum(candidate, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks")
        )
        gasal2_fallbacks = int(metric_sum(candidate, "benchmark.fasim_gasal2_fallbacks"))
        length_guard_fallbacks = int(metric_sum(candidate, "benchmark.fasim_gasal2_length_guard_fallbacks"))
        legacy_score_gpu_requests = int(
            metric_sum(candidate, "benchmark.fasim_exact_column_legacy_score_gpu_shadow_requests")
        )
        overflow_batches = int(
            metric_sum(candidate, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches")
        )
        fallback_batches = int(
            metric_sum(candidate, "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches")
        )
        active_path = (
            benchmark_shards > 0
            and gasal2_requested_shards == benchmark_shards
            and gasal2_active_shards == benchmark_shards
            and exact_scoreinfo_gpu_enabled_shards == benchmark_shards
            and gasal2_requests > 0
            and gasal2_traceback_requests > 0
            and exact_scoreinfo_gpu_tasks > 0
            and gasal2_fallbacks == 0
            and length_guard_fallbacks == 0
            and overflow_batches == 0
            and fallback_batches == 0
        )
        rows.append(
            {
                "target_preset": preset,
                "repeat": str(repeat),
                "artifact_checked": str(artifact_checked).lower(),
                "group_target_records": str(candidate.get("group_target_records") or ""),
                "cpu_shard_count": str(cpu.get("shard_count", "")),
                "preset_shard_count": str(candidate.get("shard_count", "")),
                "cpu_worker_wall_sum_seconds": f"{cpu_wall_sum:.6f}",
                "preset_worker_wall_sum_seconds": f"{candidate_wall_sum:.6f}",
                "speedup_vs_cpu_worker_wall_sum": f"{cpu_wall_sum / candidate_wall_sum:.6f}"
                if candidate_wall_sum
                else "",
                "cpu_max_worker_wall_seconds": f"{cpu_wall_max:.6f}",
                "preset_max_worker_wall_seconds": f"{candidate_wall_max:.6f}",
                "speedup_vs_cpu_max_worker_wall": f"{cpu_wall_max / candidate_wall_max:.6f}"
                if candidate_wall_max
                else "",
                "top5_score_equal": str(score_equal).lower(),
                "top5_stability_equal": str(stability_equal).lower(),
                "top5_nt_score_equal": str(nt_equal).lower(),
                "top5_all_equal": str(score_equal and stability_equal and nt_equal).lower(),
                "preset_active_path": str(active_path).lower(),
                "preset_gasal2_requested_shards": str(gasal2_requested_shards),
                "preset_gasal2_active_shards": str(gasal2_active_shards),
                "preset_exact_scoreinfo_gpu_enabled_shards": str(exact_scoreinfo_gpu_enabled_shards),
                "preset_gasal2_requests": str(gasal2_requests),
                "preset_exact_scoreinfo_gpu_tasks": str(exact_scoreinfo_gpu_tasks),
                "preset_gasal2_fallbacks": str(gasal2_fallbacks),
                "preset_length_guard_fallbacks": str(length_guard_fallbacks),
                "preset_legacy_score_gpu_requests": str(legacy_score_gpu_requests),
                "preset_exact_column_wall_seconds": f"{metric_sum(candidate, 'benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds'):.6f}",
                "preset_exact_scoreinfo_gpu_wall_seconds": f"{metric_sum(candidate, 'benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds'):.6f}",
                "preset_overflow_batches": str(overflow_batches),
                "preset_fallback_batches": str(fallback_batches),
                "preset_gasal2_total_seconds": f"{metric_sum(candidate, 'benchmark.fasim_gasal2_total_seconds'):.6f}",
                "preset_traceback_requests": str(gasal2_traceback_requests),
                "preset_score_digest": candidate_modes["score"]["digest"],
                "preset_stability_digest": candidate_modes["stability"]["digest"],
                "preset_nt_score_digest": candidate_modes["nt_score"]["digest"],
                "run_work": str(run_work),
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
    "artifact_checked_runs",
    "top5_clean_runs",
    "active_path_runs",
    "zero_legacy_score_runs",
    "zero_overflow_runs",
    "zero_fallback_runs",
    "zero_gasal2_fallback_runs",
    "zero_length_guard_fallback_runs",
    "positive_gasal2_request_runs",
    "positive_exact_scoreinfo_task_runs",
    "speedup_vs_cpu_worker_wall_sum_min",
    "speedup_vs_cpu_worker_wall_sum_median",
    "speedup_vs_cpu_worker_wall_sum_max",
    "speedup_vs_cpu_max_worker_wall_min",
    "speedup_vs_cpu_max_worker_wall_median",
    "speedup_vs_cpu_max_worker_wall_max",
    "decision",
]
aggregate_rows: list[dict[str, str]] = []
for preset in presets:
    preset_rows = [row for row in rows if row["target_preset"] == preset]
    speedups_wall_sum = [float(row["speedup_vs_cpu_worker_wall_sum"]) for row in preset_rows]
    speedups_wall_max = [float(row["speedup_vs_cpu_max_worker_wall"]) for row in preset_rows]
    artifact_checked = sum(row["artifact_checked"] == "true" for row in preset_rows)
    top5_clean = sum(row["top5_all_equal"] == "true" for row in preset_rows)
    active_path = sum(row["preset_active_path"] == "true" for row in preset_rows)
    zero_legacy = sum(int(row["preset_legacy_score_gpu_requests"]) == 0 for row in preset_rows)
    zero_overflow = sum(int(row["preset_overflow_batches"]) == 0 for row in preset_rows)
    zero_fallback = sum(int(row["preset_fallback_batches"]) == 0 for row in preset_rows)
    zero_gasal2_fallback = sum(int(row["preset_gasal2_fallbacks"]) == 0 for row in preset_rows)
    zero_length_guard_fallback = sum(int(row["preset_length_guard_fallbacks"]) == 0 for row in preset_rows)
    positive_gasal2_request = sum(int(row["preset_gasal2_requests"]) > 0 for row in preset_rows)
    positive_exact_scoreinfo_task = sum(int(row["preset_exact_scoreinfo_gpu_tasks"]) > 0 for row in preset_rows)
    all_clean = (
        artifact_checked == len(preset_rows)
        and top5_clean == len(preset_rows)
        and active_path == len(preset_rows)
        and zero_legacy == len(preset_rows)
        and zero_overflow == len(preset_rows)
        and zero_fallback == len(preset_rows)
        and zero_gasal2_fallback == len(preset_rows)
        and zero_length_guard_fallback == len(preset_rows)
        and positive_gasal2_request == len(preset_rows)
        and positive_exact_scoreinfo_task == len(preset_rows)
    )
    decision = "top5_artifact_go" if all_clean else "no_go_or_needs_review"
    aggregate_rows.append(
        {
            "target_preset": preset,
            "runs": str(len(preset_rows)),
            "artifact_checked_runs": str(artifact_checked),
            "top5_clean_runs": str(top5_clean),
            "active_path_runs": str(active_path),
            "zero_legacy_score_runs": str(zero_legacy),
            "zero_overflow_runs": str(zero_overflow),
            "zero_fallback_runs": str(zero_fallback),
            "zero_gasal2_fallback_runs": str(zero_gasal2_fallback),
            "zero_length_guard_fallback_runs": str(zero_length_guard_fallback),
            "positive_gasal2_request_runs": str(positive_gasal2_request),
            "positive_exact_scoreinfo_task_runs": str(positive_exact_scoreinfo_task),
            "speedup_vs_cpu_worker_wall_sum_min": f"{min(speedups_wall_sum):.6f}",
            "speedup_vs_cpu_worker_wall_sum_median": f"{statistics.median(speedups_wall_sum):.6f}",
            "speedup_vs_cpu_worker_wall_sum_max": f"{max(speedups_wall_sum):.6f}",
            "speedup_vs_cpu_max_worker_wall_min": f"{min(speedups_wall_max):.6f}",
            "speedup_vs_cpu_max_worker_wall_median": f"{statistics.median(speedups_wall_max):.6f}",
            "speedup_vs_cpu_max_worker_wall_max": f"{max(speedups_wall_max):.6f}",
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
                f"artifact_checked_runs={row['artifact_checked_runs']}",
                f"top5_clean_runs={row['top5_clean_runs']}",
                f"active_path_runs={row['active_path_runs']}",
                f"speedup_vs_cpu_worker_wall_sum_min={row['speedup_vs_cpu_worker_wall_sum_min']}",
                f"speedup_vs_cpu_worker_wall_sum_median={row['speedup_vs_cpu_worker_wall_sum_median']}",
                f"speedup_vs_cpu_max_worker_wall_median={row['speedup_vs_cpu_max_worker_wall_median']}",
            ]
        )
    )
(work / "decision.txt").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")

print(summary_path.read_text(encoding="utf-8"), end="")
print(aggregate_path.read_text(encoding="utf-8"), end="")
print((work / "decision.txt").read_text(encoding="utf-8"), end="")
PY
