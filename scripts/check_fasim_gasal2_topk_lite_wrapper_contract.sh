#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_topk_lite_wrapper_contract"}"

rm -rf "$WORK"
mkdir -p "$WORK"

DRY_RUN=1 \
GROUP_TARGET_RECORDS=32 \
AUTO_CPU_CORE_RANGES=1 \
CPU_POOL=0-19 \
CPU_CORES_PER_WORKER=3 \
BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
DNA="$WORK/target.fa" \
RNA="$WORK/query.fa" \
RULE=0 \
OUT="$WORK/run" \
bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
  >"$WORK/dry_run.stdout.log" \
  2>"$WORK/dry_run.stderr.log"

grep -q -- 'scripts/fasim_sharded_runner.py' "$WORK/dry_run.stdout.log"
grep -q -- '--gasal2-top5-column-pruned-scoreinfo' "$WORK/dry_run.stdout.log"
grep -q -- '--output-mode lite' "$WORK/dry_run.stdout.log"
grep -q -- '--work-dir' "$WORK/dry_run.stdout.log"
grep -q -- '--manifest' "$WORK/dry_run.stdout.log"
grep -q -- 'run_manifest\.json' "$WORK/dry_run.stdout.log"
grep -q -- '--group-target-records 32' "$WORK/dry_run.stdout.log"
grep -q -- '--auto-cpu-core-ranges' "$WORK/dry_run.stdout.log"
grep -q -- '--cpu-pool 0-19' "$WORK/dry_run.stdout.log"
grep -q -- '--cpu-cores-per-worker 3' "$WORK/dry_run.stdout.log"
grep -q -- '--force' "$WORK/dry_run.stdout.log"
if grep -q -- 'FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK' "$WORK/dry_run.stdout.log"; then
  echo "default wrapper dry-run must not expose low-level GASAL2 scoreInfo env" >&2
  exit 1
fi

DRY_RUN=1 \
RESUME=1 \
FORCE=0 \
BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
DNA="$WORK/target.fa" \
RNA="$WORK/query.fa" \
RULE=0 \
OUT="$WORK/resume_run" \
bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
  >"$WORK/resume_dry_run.stdout.log" \
  2>"$WORK/resume_dry_run.stderr.log"

grep -q -- '--manifest' "$WORK/resume_dry_run.stdout.log"
grep -q -- 'run_manifest\.json' "$WORK/resume_dry_run.stdout.log"
grep -q -- '--resume' "$WORK/resume_dry_run.stdout.log"
if grep -q -- '--force' "$WORK/resume_dry_run.stdout.log"; then
  echo "RESUME=1 FORCE=0 dry-run must not include --force" >&2
  exit 1
fi

if DRY_RUN=1 \
  RESUME=1 \
  FORCE=1 \
  BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
  DNA="$WORK/target.fa" \
  RNA="$WORK/query.fa" \
  RULE=0 \
  OUT="$WORK/resume_force_conflict" \
  bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
    >"$WORK/resume_force_conflict.stdout.log" \
    2>"$WORK/resume_force_conflict.stderr.log"; then
  echo "expected RESUME=1 FORCE=1 to fail closed" >&2
  exit 1
fi
grep -q -- 'RESUME=1 cannot be combined with FORCE=1' \
  "$WORK/resume_force_conflict.stderr.log"

LEGACY_DIRECT=1 \
DRY_RUN=1 \
BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
DNA="$WORK/target.fa" \
RNA="$WORK/query.fa" \
RULE=0 \
OUT="$WORK/legacy" \
bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
  >"$WORK/legacy_dry_run.stdout.log" \
  2>"$WORK/legacy_dry_run.stderr.log"

grep -q -- 'LEGACY_DIRECT=1' "$WORK/legacy_dry_run.stdout.log"
grep -q -- 'FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK' "$WORK/legacy_dry_run.stdout.log"

if BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
  DNA="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa" \
  RNA="$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa" \
  RULE=0 \
  OUT="$WORK/long_query_fail" \
  WORKERS=1 \
  GPU_IDS=0 \
  bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
    >"$WORK/long_query_fail.stdout.log" \
    2>"$WORK/long_query_fail.stderr.log"; then
  echo "expected formal wrapper to fail closed on long-query MALAT1" >&2
  exit 1
fi
grep -q -- 'query length 8708 exceeds FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812' \
  "$WORK/long_query_fail/stderr.log"
test ! -e "$WORK/long_query_fail/report.json"
test ! -e "$WORK/long_query_fail/summary.tsv"

BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
DNA="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa" \
RNA="$ROOT/H19.fa" \
RULE=0 \
K=5 \
OUT="$WORK/actual" \
WORKERS=2 \
GPU_IDS=0,1 \
GROUP_TARGET_RECORDS=2 \
bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
  >"$WORK/actual.stdout.log" \
  2>"$WORK/actual.stderr.log"

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/actual/report.json" \
  --manifest "$WORK/actual/run_manifest.json"
test -s "$WORK/actual/top5.lite"

python3 - "$WORK/actual/report.json" "$WORK/actual/summary.tsv" <<'PY'
import csv
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
summary_rows = list(csv.DictReader(Path(sys.argv[2]).open(encoding="utf-8"), delimiter="\t"))
if len(summary_rows) != 1:
    raise SystemExit(f"expected one summary row, got {len(summary_rows)}")
summary = summary_rows[0]
sums = report["fasim_benchmark_sums"]
assert report["result_contract"] == "gasal2_top5_column_pruned_scoreinfo_artifact_v1", report
assert report["run_status"] == "completed", report
assert report["target_record_count"] == 2, report
assert report["group_target_records"] == 2, report
assert report["grouped_shard_count"] == 1, report
assert report["shard_count"] == 1, report
assert report["gasal2_top5_activation_verified"] is True, report
assert report["gasal2_top5_activation_error"] is None, report
assert report["gasal2_top5_query_preflight_supported"] is True, report
assert report["topk_lite_output"].endswith("topk-TFOsorted.lite"), report
assert Path(report["topk_lite_output"]).read_bytes() == Path(sys.argv[1]).with_name("top5.lite").read_bytes()
assert int(sums["fasim_gasal2_requests"]) > 0, sums
assert int(sums["fasim_gasal2_traceback_requests"]) > 0, sums
assert int(sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks"]) > 0, sums
assert int(sums["fasim_gasal2_fallbacks"]) == 0, sums
assert int(sums["fasim_gasal2_length_guard_fallbacks"]) == 0, sums
assert summary["contract"] == report["result_contract"], summary
assert summary["run_status"] == "completed", summary
assert summary["shard_count"] == "1", summary
assert summary["resumed_shards_count"] == "0", summary
assert summary["group_target_records"] == "2", summary
assert summary["grouped_shard_count"] == "1", summary
assert summary["activation_verified"] == "true", summary
assert summary["query_preflight_supported"] == "true", summary
assert int(summary["gasal2_requests"]) > 0, summary
assert int(summary["gasal2_fallbacks"]) == 0, summary
assert int(summary["length_guard_fallbacks"]) == 0, summary
PY

BIN="$ROOT/.tmp/fasim_longtarget_gasal2_direct" \
DNA="$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa" \
RNA="$ROOT/H19.fa" \
RULE=0 \
K=5 \
OUT="$WORK/actual" \
WORKERS=2 \
GPU_IDS=0,1 \
GROUP_TARGET_RECORDS=2 \
RESUME=1 \
FORCE=0 \
bash "$ROOT/scripts/run_fasim_gasal2_topk_lite.sh" \
  >"$WORK/actual_resume.stdout.log" \
  2>"$WORK/actual_resume.stderr.log"

python3 - "$WORK/actual/report.json" "$WORK/actual/run_manifest.json" "$WORK/actual/summary.tsv" <<'PY'
import csv
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
summary_rows = list(csv.DictReader(Path(sys.argv[3]).open(encoding="utf-8"), delimiter="\t"))
if len(summary_rows) != 1:
    raise SystemExit(f"expected one resume summary row, got {len(summary_rows)}")
assert report["run_status"] == "completed", report
assert len(report["resumed_shards"]) == report["shard_count"], report
assert all(shard["status"] == "skipped_by_resume" for shard in manifest["per_shard"]), manifest
assert all(shard["skipped_by_resume"] is True for shard in manifest["per_shard"]), manifest
summary = summary_rows[0]
assert summary["run_status"] == "completed", summary
assert summary["shard_count"] == str(report["shard_count"]), summary
assert summary["resumed_shards_count"] == str(report["shard_count"]), summary
assert Path(sys.argv[1]).with_name("top5.lite").exists()
PY

echo "ok"
