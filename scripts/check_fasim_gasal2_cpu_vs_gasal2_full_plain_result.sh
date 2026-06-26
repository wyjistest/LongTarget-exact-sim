#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_cpu_vs_gasal2_full_plain_chr22"}"
SUMMARY="$WORK/summary.txt"
MIN_SPEEDUP="${MIN_SPEEDUP:-20}"

if [[ ! -s "$SUMMARY" ]]; then
  echo "missing CPU-vs-GASAL2 full plain summary: $SUMMARY" >&2
  exit 1
fi

python3 - "$ROOT" "$WORK" "$SUMMARY" "$MIN_SPEEDUP" <<'PY'
import math
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
work = Path(sys.argv[2])
summary = Path(sys.argv[3])
min_speedup = float(sys.argv[4])
metrics: dict[str, str] = {}
for line in summary.read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        metrics[key] = value

def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

def f(key: str) -> float:
    try:
        return float(metrics[key])
    except KeyError as exc:
        raise SystemExit(f"missing metric: {key}") from exc

def i(key: str) -> int:
    try:
        return int(float(metrics[key]))
    except KeyError as exc:
        raise SystemExit(f"missing metric: {key}") from exc

def read_kv(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key] = value
    return data

def metric_from_stderr(path: Path, key: str, default: str = "0") -> str:
    if not path.exists():
        return default
    prefix = key + "="
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return default

cpu_case = read_kv(work / "cpu" / "case_metrics.txt")
gasal2_case = read_kv(work / "gasal2" / "case_metrics.txt")
for prefix, case in (("cpu", cpu_case), ("gasal2", gasal2_case)):
    for key in ("wall_seconds", "lines", "lite"):
        if key in case:
            metrics.setdefault(f"{prefix}_{key}", case[key])
if "run_wall_speedup" not in metrics and "cpu_wall_seconds" in metrics and "gasal2_wall_seconds" in metrics:
    gasal2_wall = float(metrics["gasal2_wall_seconds"])
    metrics["run_wall_speedup"] = "nan" if gasal2_wall == 0.0 else f"{float(metrics['cpu_wall_seconds']) / gasal2_wall:.6f}"
if not metrics.get("gasal2_active"):
    metrics["gasal2_active"] = metric_from_stderr(
        work / "gasal2" / "stderr.log",
        "benchmark.fasim_top5_gasal2_gpu_scoreinfo_active",
    )
for key, stderr_key in (
    ("gasal2_requests", "benchmark.fasim_gasal2_requests"),
    ("gasal2_traceback_requests", "benchmark.fasim_gasal2_traceback_requests"),
    ("gasal2_fallbacks", "benchmark.fasim_gasal2_fallbacks"),
    ("gasal2_length_guard_fallbacks", "benchmark.fasim_gasal2_length_guard_fallbacks"),
):
    if not metrics.get(key):
        metrics[key] = metric_from_stderr(work / "gasal2" / "stderr.log", stderr_key)

cpu_lite = Path(metrics.get("cpu_lite", ""))
gasal2_lite = Path(metrics.get("gasal2_lite", ""))
if not cpu_lite.is_absolute():
    cpu_lite = root / cpu_lite
if not gasal2_lite.is_absolute():
    gasal2_lite = root / gasal2_lite
require(cpu_lite.exists(), f"missing CPU lite output: {cpu_lite}")
require(gasal2_lite.exists(), f"missing GASAL2 lite output: {gasal2_lite}")

top5_compare = work / "top5_compare.txt"
if not top5_compare.exists():
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "compare_fasim_lite_topk.py"),
            "--baseline",
            str(cpu_lite),
            "--candidate",
            str(gasal2_lite),
            "--k",
            "5",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    top5_compare.write_text(result.stdout, encoding="utf-8")
top5_metrics = read_kv(top5_compare)
for key in ("top5_score_equal", "top5_stability_equal", "top5_nt_score_equal"):
    metrics.setdefault(key, top5_metrics.get(key, "false"))

if not {"common_rows", "cpu_only_rows", "gasal2_only_rows"} <= metrics.keys():
    baseline_unique = int(top5_metrics.get("baseline_unique_rows", "0"))
    missing_rows = int(top5_metrics.get("missing_rows", "0"))
    extra_rows = int(top5_metrics.get("extra_rows", "0"))
    metrics.setdefault("common_rows", str(baseline_unique - missing_rows))
    metrics.setdefault("cpu_only_rows", str(missing_rows))
    metrics.setdefault("gasal2_only_rows", str(extra_rows))

require(metrics.get("top5_score_equal") == "true", "top5 score differs")
require(metrics.get("top5_stability_equal") == "true", "top5 stability differs")
require(metrics.get("top5_nt_score_equal") == "true", "top5 nt_score differs")
require(metrics.get("gasal2_active") == "1", "GASAL2 path inactive")
require(i("gasal2_fallbacks") == 0, "GASAL2 fallbacks occurred")
require(i("gasal2_length_guard_fallbacks") == 0, "GASAL2 length guard fallbacks occurred")
require(i("gasal2_requests") > 0, "missing GASAL2 requests")
require(i("gasal2_traceback_requests") > 0, "missing GASAL2 traceback requests")
require(i("cpu_lines") > 0 and i("gasal2_lines") > 0, "missing output rows")
require(i("common_rows") > 0, "no common rows")

speedup = f("run_wall_speedup")
require(math.isfinite(speedup), "speedup is not finite")
require(speedup >= min_speedup, f"speedup {speedup:.6f} below required {min_speedup:.6f}")

full_rows_equal = i("cpu_only_rows") == 0 and i("gasal2_only_rows") == 0
if full_rows_equal:
    decision = "top5_equivalent_full_rows_equal_fast_path"
else:
    decision = "top5_equivalent_fast_path_not_full_row_equivalent"

print(f"decision={decision}")
print(f"run_wall_speedup={speedup:.6f}x")
print(f"cpu_lines={i('cpu_lines')}")
print(f"gasal2_lines={i('gasal2_lines')}")
print(f"common_rows={i('common_rows')}")
print(f"cpu_only_rows={i('cpu_only_rows')}")
print(f"gasal2_only_rows={i('gasal2_only_rows')}")
print("top5_score_equal=true")
print("top5_stability_equal=true")
print("top5_nt_score_equal=true")
print("ok")
PY
