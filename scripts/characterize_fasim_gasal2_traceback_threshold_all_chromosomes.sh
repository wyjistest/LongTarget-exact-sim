#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
CHR_DIR="${CHR_DIR:-"$ROOT/.tmp/gasal2_hg38_archive_first_rule0_run/shards"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_traceback_threshold_all_chromosomes"}"
CHROMS="${CHROMS:-chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY}"
THRESHOLDS="${THRESHOLDS:-80 90 100 105 110 112 114 115 116 117 118 120 125 130 140}"
MAX_BASES="${MAX_BASES:-2000000}"
WINDOWS="${WINDOWS:-8}"
MIN_TRACEBACK_REQUESTS="${MIN_TRACEBACK_REQUESTS:-1}"
ANCHOR_WINDOW_BASES="${ANCHOR_WINDOW_BASES:-250000}"
ANCHOR_MAX_WINDOWS="${ANCHOR_MAX_WINDOWS:-8}"
WORKERS="${WORKERS:-1}"
GPU_IDS="${GPU_IDS:-0}"
FORCE_CHROM="${FORCE_CHROM:-0}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$RNA" "$CHR_DIR"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

mkdir -p "$WORK"

is_completed_report() {
  local report="$1"
  [[ -s "$report" ]] || return 1
  python3 - "$report" <<'PY'
import json
import sys
from pathlib import Path

try:
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if report.get("run_status") == "completed" else 1)
PY
}

run_formal() {
  local target="$1"
  local out_dir="$2"
  local threshold="${3:-}"
  local -a cmd=(
    python3 "$ROOT/scripts/fasim_sharded_runner.py"
    --fasim-bin "$BIN"
    --target "$target"
    --rna "$RNA"
    --rule "$RULE"
    --work-dir "$out_dir"
    --manifest "$out_dir/run_manifest.json"
    --output-mode lite
    --gasal2-top5-column-pruned-scoreinfo
    --workers "$WORKERS"
    --gpu-ids "$GPU_IDS"
    --force
  )
  if [[ -n "$threshold" ]]; then
    cmd+=(--env "FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=$threshold")
  fi
  "${cmd[@]}" >"$out_dir.wrapper.stdout" 2>"$out_dir.wrapper.stderr"
}

run_calibration() {
  local target="$1"
  local anchor_tsv="$2"
  local out_dir="$3"
  rm -rf "$out_dir"
  mkdir -p "$out_dir"
  BIN="$BIN" \
  DNA="$target" \
  RNA="$RNA" \
  RULE="$RULE" \
  WORK="$out_dir" \
  THRESHOLDS="$THRESHOLDS" \
  MAX_RECORDS=1 \
  MAX_BASES="$MAX_BASES" \
  WINDOWS="$WINDOWS" \
  MIN_TRACEBACK_REQUESTS="$MIN_TRACEBACK_REQUESTS" \
  ANCHOR_TSV="$anchor_tsv" \
  ANCHOR_WINDOW_BASES="$ANCHOR_WINDOW_BASES" \
  ANCHOR_MAX_WINDOWS="$ANCHOR_MAX_WINDOWS" \
  ESTIMATOR_REQUIRE_FAILING_BOUNDARY=1 \
    bash "$ROOT/scripts/calibrate_fasim_gasal2_traceback_threshold.sh" \
    >"$out_dir.wrapper.stdout" 2>"$out_dir.wrapper.stderr" || true
}

refresh_summary() {
  python3 - "$WORK" $CHROMS <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
chroms = sys.argv[2:]


def kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def report_metrics(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    report = json.loads(path.read_text(encoding="utf-8"))
    sums = report.get("fasim_benchmark_sums", {})
    per_worker = report.get("per_worker") or []
    wall = per_worker[0].get("wall_seconds") if per_worker else None
    return {
        "status": report.get("run_status", ""),
        "wall": wall,
        "digest": report.get("topk_lite_digest", ""),
        "rows": report.get("topk_lite_records", ""),
        "gasal2": int(sums.get("fasim_gasal2_requests", 0)),
        "traceback": int(sums.get("fasim_gasal2_traceback_requests", 0)),
        "fallbacks": int(sums.get("fasim_gasal2_fallbacks", 0)),
        "length_guard": int(sums.get("fasim_gasal2_length_guard_fallbacks", 0)),
    }


columns = [
    "chrom",
    "decision",
    "recommended_threshold",
    "first_failing_threshold",
    "first_failing_contracts",
    "baseline_wall_seconds",
    "candidate_wall_seconds",
    "wall_delta_seconds",
    "wall_reduction_fraction",
    "speedup",
    "baseline_traceback_requests",
    "candidate_traceback_requests",
    "traceback_delta",
    "traceback_reduction_fraction",
    "baseline_gasal2_requests",
    "candidate_gasal2_requests",
    "topk_digest_equal",
    "baseline_topk_digest",
    "candidate_topk_digest",
    "baseline_rows",
    "candidate_rows",
    "baseline_status",
    "candidate_status",
    "fallbacks",
    "length_guard_fallbacks",
    "calibration_baseline_traceback_requests",
    "calibration_recommended_traceback_requests",
]

rows: list[list[str]] = []
for chrom in chroms:
    chrom_dir = work / chrom
    baseline = report_metrics(chrom_dir / "baseline" / "report.json")
    candidate = report_metrics(chrom_dir / "candidate" / "report.json")
    estimate = kv(chrom_dir / "calibration" / "estimate.txt")
    b_wall = baseline.get("wall")
    c_wall = candidate.get("wall")
    wall_delta = None
    wall_reduction = None
    speedup = None
    if isinstance(b_wall, (int, float)) and isinstance(c_wall, (int, float)) and c_wall:
        wall_delta = b_wall - c_wall
        wall_reduction = wall_delta / b_wall if b_wall else None
        speedup = b_wall / c_wall
    b_trace = int(baseline.get("traceback", 0) or 0)
    c_trace = int(candidate.get("traceback", 0) or 0)
    trace_delta = b_trace - c_trace if candidate else 0
    trace_reduction = trace_delta / b_trace if b_trace else None
    digest_equal = (
        baseline.get("digest") == candidate.get("digest")
        if baseline.get("digest") and candidate.get("digest")
        else ""
    )
    values = {
        "chrom": chrom,
        "decision": estimate.get("decision", ""),
        "recommended_threshold": estimate.get("recommended_threshold", ""),
        "first_failing_threshold": estimate.get("first_failing_threshold", ""),
        "first_failing_contracts": estimate.get("first_failing_contracts", ""),
        "baseline_wall_seconds": f"{b_wall:.6f}" if isinstance(b_wall, (int, float)) else "",
        "candidate_wall_seconds": f"{c_wall:.6f}" if isinstance(c_wall, (int, float)) else "",
        "wall_delta_seconds": f"{wall_delta:.6f}" if wall_delta is not None else "",
        "wall_reduction_fraction": f"{wall_reduction:.6f}" if wall_reduction is not None else "",
        "speedup": f"{speedup:.6f}" if speedup is not None else "",
        "baseline_traceback_requests": str(b_trace) if baseline else "",
        "candidate_traceback_requests": str(c_trace) if candidate else "",
        "traceback_delta": str(trace_delta) if candidate else "",
        "traceback_reduction_fraction": f"{trace_reduction:.6f}" if trace_reduction is not None and candidate else "",
        "baseline_gasal2_requests": str(baseline.get("gasal2", "")),
        "candidate_gasal2_requests": str(candidate.get("gasal2", "")),
        "topk_digest_equal": str(digest_equal).lower() if digest_equal != "" else "",
        "baseline_topk_digest": str(baseline.get("digest", "")),
        "candidate_topk_digest": str(candidate.get("digest", "")),
        "baseline_rows": str(baseline.get("rows", "")),
        "candidate_rows": str(candidate.get("rows", "")),
        "baseline_status": str(baseline.get("status", "")),
        "candidate_status": str(candidate.get("status", "")),
        "fallbacks": str(int(baseline.get("fallbacks", 0) or 0) + int(candidate.get("fallbacks", 0) or 0)),
        "length_guard_fallbacks": str(int(baseline.get("length_guard", 0) or 0) + int(candidate.get("length_guard", 0) or 0)),
        "calibration_baseline_traceback_requests": estimate.get("baseline_traceback_requests", ""),
        "calibration_recommended_traceback_requests": estimate.get("recommended_traceback_requests", ""),
    }
    rows.append([values[column] for column in columns])

(work / "summary.tsv").write_text(
    "\t".join(columns) + "\n" + "\n".join("\t".join(row) for row in rows) + "\n",
    encoding="utf-8",
)

clean = [row for row in rows if row[columns.index("topk_digest_equal")] == "true"]
speedups = [
    float(row[columns.index("speedup")])
    for row in clean
    if row[columns.index("speedup")]
]
summary = [
    "# Fasim GASAL2 traceback threshold all chromosomes",
    "",
    f"chromosomes_requested={len(chroms)}",
    f"chromosomes_candidate_digest_clean={len(clean)}",
]
if speedups:
    summary.extend([
        f"median_speedup={sorted(speedups)[len(speedups)//2]:.6f}",
        f"min_speedup={min(speedups):.6f}",
        f"max_speedup={max(speedups):.6f}",
    ])
summary.extend(["", "See summary.tsv for per-chromosome metrics.", ""])
(work / "summary.md").write_text("\n".join(summary), encoding="utf-8")
print((work / "summary.tsv").read_text(encoding="utf-8"), end="")
PY
}

for chrom in $CHROMS; do
  target="$CHR_DIR/$chrom.fa"
  chrom_dir="$WORK/$chrom"
  baseline_dir="$chrom_dir/baseline"
  calibration_dir="$chrom_dir/calibration"
  candidate_dir="$chrom_dir/candidate"

  if [[ ! -s "$target" ]]; then
    echo "[$chrom] missing target: $target" >&2
    continue
  fi

  mkdir -p "$chrom_dir"
  echo "[$chrom] baseline"
  baseline_done=0
  if is_completed_report "$baseline_dir/report.json"; then
    baseline_done=1
  fi
  if [[ "$FORCE_CHROM" == "1" || "$baseline_done" != "1" ]]; then
    rm -rf "$baseline_dir"
    mkdir -p "$baseline_dir"
    run_formal "$target" "$baseline_dir"
  else
    echo "[$chrom] baseline already completed"
  fi

  echo "[$chrom] anchored calibration"
  if [[ "$FORCE_CHROM" == "1" || ! -s "$calibration_dir/estimate.txt" ]]; then
    run_calibration "$target" "$baseline_dir/topk_rows.tsv" "$calibration_dir"
  else
    echo "[$chrom] calibration already completed"
  fi

  decision="$(awk -F= '/^decision=/{print $2}' "$calibration_dir/estimate.txt" 2>/dev/null || true)"
  threshold="$(awk -F= '/^recommended_threshold=/{print $2}' "$calibration_dir/estimate.txt" 2>/dev/null || true)"
  if [[ "$decision" == "query_specific_threshold_candidate" && -n "$threshold" && "$threshold" != "NA" ]]; then
    echo "[$chrom] candidate threshold=$threshold"
    candidate_done=0
    if is_completed_report "$candidate_dir/report.json"; then
      candidate_done=1
    fi
    if [[ "$FORCE_CHROM" == "1" || "$candidate_done" != "1" ]]; then
      rm -rf "$candidate_dir"
      mkdir -p "$candidate_dir"
      run_formal "$target" "$candidate_dir" "$threshold"
    else
      echo "[$chrom] candidate already completed"
    fi
  else
    echo "[$chrom] no bounded threshold; candidate skipped (decision=${decision:-missing})"
  fi

  refresh_summary >"$WORK/summary.latest.tsv"
done

refresh_summary >"$WORK/summary.latest.tsv"
echo "summary: $WORK/summary.tsv"
