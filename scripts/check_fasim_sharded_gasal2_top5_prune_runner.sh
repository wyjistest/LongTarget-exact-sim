#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_sharded_gasal2_top5_prune_runner"}"
SOURCE_DNA="${SOURCE_DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
DNA="${DNA:-}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
K="${K:-5}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-64}"
EXACT_SCOREINFO_GPU_MAX_PER_TASK="${EXACT_SCOREINFO_GPU_MAX_PER_TASK:-512}"
WORKERS="${WORKERS:-2}"
GPU_IDS="${GPU_IDS:-0,1}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK"

if [[ -z "$DNA" ]]; then
  DNA="$WORK/inputs/chr22_slice_10m_12m_two_records.fa"
  mkdir -p "$(dirname "$DNA")"
  python3 - "$SOURCE_DNA" "$DNA" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

lines = src.read_text().splitlines()
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

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/cpu_summary" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/cpu_summary.stdout.log" \
  2>"$WORK/cpu_summary.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_prune" \
  --manifest "$WORK/gasal2_top5_prune/run_manifest.json" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --shard-output-topk-lite "$K" \
  --gasal2-top5-scoreinfo-prune-max-per-task "$PRUNE_MAX_PER_TASK" \
  --exact-scoreinfo-gpu-max-per-task "$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
  --exact-scoreinfo-gpu-pruned-output \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/gasal2_top5_prune.stdout.log" \
  2>"$WORK/gasal2_top5_prune.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_column_pruned_preset" \
  --manifest "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/gasal2_top5_column_pruned_preset.stdout.log" \
  2>"$WORK/gasal2_top5_column_pruned_preset.stderr.log"

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/cpu_summary/report.json"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_prune/report.json" \
  --manifest "$WORK/gasal2_top5_prune/run_manifest.json" \
  --same-payload-as "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/cpu_summary/report.json"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_column_pruned_preset/report.json" \
  --manifest "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" \
  --same-payload-as "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/gasal2_top5_prune/report.json"
python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/preset_bad_integrity_missing_prealign_max_tasks_report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report["env_overrides"].pop("FASIM_PREALIGN_CUDA_MAX_TASKS", None)
Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/preset_bad_integrity_missing_prealign_max_tasks_report.json" \
  >"$WORK/preset_bad_integrity_missing_prealign_max_tasks.stdout.log" \
  2>"$WORK/preset_bad_integrity_missing_prealign_max_tasks.stderr.log"; then
  echo "expected formal artifact integrity to reject missing managed PREALIGN_CUDA_MAX_TASKS" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 artifact env_overrides missing FASIM_PREALIGN_CUDA_MAX_TASKS=16384' \
  "$WORK/preset_bad_integrity_missing_prealign_max_tasks.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/preset_bad_integrity_segmented_shadow_report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report["env_overrides"]["FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW"] = "1"
Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/preset_bad_integrity_segmented_shadow_report.json" \
  >"$WORK/preset_bad_integrity_segmented_shadow.stdout.log" \
  2>"$WORK/preset_bad_integrity_segmented_shadow.stderr.log"; then
  echo "expected formal artifact integrity to reject segmented shadow env" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 artifact env_overrides contains forbidden segmented diagnostic env FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW' \
  "$WORK/preset_bad_integrity_segmented_shadow.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/preset_bad_integrity_cpu_traceback_env_report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report["env_overrides"]["FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST"] = "1"
Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/preset_bad_integrity_cpu_traceback_env_report.json" \
  >"$WORK/preset_bad_integrity_cpu_traceback_env.stdout.log" \
  2>"$WORK/preset_bad_integrity_cpu_traceback_env.stderr.log"; then
  echo "expected formal artifact integrity to reject CPU traceback diagnostic env" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 artifact env_overrides contains unsupported formal env FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST' \
  "$WORK/preset_bad_integrity_cpu_traceback_env.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/preset_bad_integrity_query_max_env_report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report["env_overrides"]["FASIM_ALIGN_GASAL2_MAX_QUERY_LEN"] = "1000"
Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/preset_bad_integrity_query_max_env_report.json" \
  >"$WORK/preset_bad_integrity_query_max_env.stdout.log" \
  2>"$WORK/preset_bad_integrity_query_max_env.stderr.log"; then
  echo "expected formal artifact integrity to reject inconsistent query max env" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 artifact env_overrides FASIM_ALIGN_GASAL2_MAX_QUERY_LEN does not match recorded query preflight max' \
  "$WORK/preset_bad_integrity_query_max_env.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" "$WORK/preset_bad_integrity_missing_prealign_max_tasks_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest["env_snapshot"].pop("FASIM_PREALIGN_CUDA_MAX_TASKS", None)
Path(sys.argv[2]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_column_pruned_preset/report.json" \
  --manifest "$WORK/preset_bad_integrity_missing_prealign_max_tasks_manifest.json" \
  >"$WORK/preset_bad_integrity_missing_prealign_max_tasks_manifest.stdout.log" \
  2>"$WORK/preset_bad_integrity_missing_prealign_max_tasks_manifest.stderr.log"; then
  echo "expected formal manifest integrity to reject missing managed PREALIGN_CUDA_MAX_TASKS" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 manifest env_snapshot missing FASIM_PREALIGN_CUDA_MAX_TASKS=16384' \
  "$WORK/preset_bad_integrity_missing_prealign_max_tasks_manifest.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" "$WORK/preset_bad_integrity_segmented_shadow_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest["env_snapshot"]["FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW"] = "1"
Path(sys.argv[2]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_column_pruned_preset/report.json" \
  --manifest "$WORK/preset_bad_integrity_segmented_shadow_manifest.json" \
  >"$WORK/preset_bad_integrity_segmented_shadow_manifest.stdout.log" \
  2>"$WORK/preset_bad_integrity_segmented_shadow_manifest.stderr.log"; then
  echo "expected formal manifest integrity to reject segmented shadow env" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 manifest env_snapshot contains forbidden segmented diagnostic env FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW' \
  "$WORK/preset_bad_integrity_segmented_shadow_manifest.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" "$WORK/preset_bad_integrity_cpu_traceback_env_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest["env_snapshot"]["FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST"] = "1"
Path(sys.argv[2]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_column_pruned_preset/report.json" \
  --manifest "$WORK/preset_bad_integrity_cpu_traceback_env_manifest.json" \
  >"$WORK/preset_bad_integrity_cpu_traceback_env_manifest.stdout.log" \
  2>"$WORK/preset_bad_integrity_cpu_traceback_env_manifest.stderr.log"; then
  echo "expected formal manifest integrity to reject CPU traceback diagnostic env" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 manifest env_snapshot contains unsupported formal env FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST' \
  "$WORK/preset_bad_integrity_cpu_traceback_env_manifest.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" "$WORK/preset_bad_integrity_query_max_env_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest["env_snapshot"]["FASIM_ALIGN_GASAL2_MAX_QUERY_LEN"] = "1000"
Path(sys.argv[2]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_column_pruned_preset/report.json" \
  --manifest "$WORK/preset_bad_integrity_query_max_env_manifest.json" \
  >"$WORK/preset_bad_integrity_query_max_env_manifest.stdout.log" \
  2>"$WORK/preset_bad_integrity_query_max_env_manifest.stderr.log"; then
  echo "expected formal manifest integrity to reject inconsistent query max env" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 manifest env_snapshot FASIM_ALIGN_GASAL2_MAX_QUERY_LEN does not match recorded query preflight max' \
  "$WORK/preset_bad_integrity_query_max_env_manifest.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/preset_bad_integrity_zero_gasal2_requests_report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report["fasim_benchmark_sums"]["fasim_gasal2_requests"] = 0
Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/preset_bad_integrity_zero_gasal2_requests_report.json" \
  >"$WORK/preset_bad_integrity_zero_gasal2_requests.stdout.log" \
  2>"$WORK/preset_bad_integrity_zero_gasal2_requests.stderr.log"; then
  echo "expected formal artifact integrity to reject zero GASAL2 requests" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 artifact requires positive fasim_gasal2_requests' \
  "$WORK/preset_bad_integrity_zero_gasal2_requests.stderr.log"
python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/preset_bad_integrity_rank_observe_unknown_report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report["fasim_benchmark_sums"][
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows"
] = 1
Path(sys.argv[2]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/preset_bad_integrity_rank_observe_unknown_report.json" \
  >"$WORK/preset_bad_integrity_rank_observe_unknown.stdout.log" \
  2>"$WORK/preset_bad_integrity_rank_observe_unknown.stderr.log"; then
  echo "expected formal artifact integrity to reject unknown topK-lite rank observe rows" >&2
  exit 1
fi
grep -q -- 'formal GASAL2 artifact requires zero fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows' \
  "$WORK/preset_bad_integrity_rank_observe_unknown.stderr.log"

	python3 - "$WORK/cpu_summary/report.json" "$WORK/gasal2_top5_prune/report.json" "$WORK/gasal2_top5_column_pruned_preset/report.json" "$K" "$PRUNE_MAX_PER_TASK" "$EXACT_SCOREINFO_GPU_MAX_PER_TASK" "$WORKERS" <<'PY'
import json
import sys
from pathlib import Path

cpu = json.loads(Path(sys.argv[1]).read_text())
gasal2 = json.loads(Path(sys.argv[2]).read_text())
preset = json.loads(Path(sys.argv[3]).read_text())
k = int(sys.argv[4])
prune_max = int(sys.argv[5])
exact_scoreinfo_max = int(sys.argv[6])

assert cpu["run_status"] == "completed", cpu
assert gasal2["run_status"] == "completed", gasal2
assert preset["run_status"] == "completed", preset
assert gasal2["gasal2_top5_activation_verified"] is None, gasal2
assert gasal2["gasal2_top5_activation_error"] is None, gasal2
assert preset["gasal2_top5_activation_verified"] is True, preset
assert preset["gasal2_top5_activation_error"] is None, preset
for report in (cpu, gasal2):
    assert report["gasal2_top5_query_preflight_supported"] is None, report
    assert report["gasal2_top5_query_preflight_error"] is None, report
    assert report["gasal2_top5_query_preflight_query_len"] is None, report
    assert report["gasal2_top5_query_preflight_max_query_len"] is None, report
assert preset["gasal2_top5_query_preflight_supported"] is True, preset
assert preset["gasal2_top5_query_preflight_error"] is None, preset
assert isinstance(preset["gasal2_top5_query_preflight_query_len"], int), preset
assert isinstance(preset["gasal2_top5_query_preflight_max_query_len"], int), preset
assert preset["gasal2_top5_query_preflight_query_len"] > 0, preset
assert preset["gasal2_top5_query_preflight_max_query_len"] == 2812, preset
assert (
    preset["gasal2_top5_query_preflight_query_len"]
    <= preset["gasal2_top5_query_preflight_max_query_len"]
), preset
assert cpu["shard_count"] >= 2, cpu
assert gasal2["shard_count"] == cpu["shard_count"], (cpu, gasal2)
assert preset["shard_count"] == cpu["shard_count"], (cpu, preset)
assert gasal2["worker_count"] == int(sys.argv[7]), gasal2
assert preset["worker_count"] == int(sys.argv[7]), preset
assert cpu["topk_summary_only"] is True, cpu
assert gasal2["topk_summary_only"] is True, gasal2
assert preset["topk_summary_only"] is True, preset
assert cpu["result_contract"] == "topk_summary_artifact_v1", cpu
assert gasal2["result_contract"] == "gasal2_top5_scoreinfo_artifact_v1", gasal2
assert preset["result_contract"] == "gasal2_top5_column_pruned_scoreinfo_artifact_v1", preset
assert cpu["shard_output_topk_lite"] is None, cpu
assert gasal2["shard_output_topk_lite"] == k, gasal2
assert preset["shard_output_topk_lite"] == k, preset
assert gasal2["gasal2_top5_column_pruned_scoreinfo"] is False, gasal2
assert preset["gasal2_top5_column_pruned_scoreinfo"] is True, preset
assert gasal2["gasal2_top5_scoreinfo_prune_max_per_task"] == prune_max, gasal2
assert preset["gasal2_top5_scoreinfo_prune_max_per_task"] == prune_max, preset
assert gasal2["exact_scoreinfo_gpu_max_per_task"] == exact_scoreinfo_max, gasal2
assert preset["exact_scoreinfo_gpu_max_per_task"] == exact_scoreinfo_max, preset
assert gasal2["exact_scoreinfo_gpu_pruned_output"] is True, gasal2
assert preset["exact_scoreinfo_gpu_pruned_output"] is True, preset
assert gasal2["exact_scoreinfo_gpu_column_pruned_output"] is False, gasal2
assert preset["exact_scoreinfo_gpu_column_pruned_output"] is True, preset
assert preset["env_overrides"]["FASIM_PREALIGN_CUDA_MAX_TASKS"] == "16384", preset
assert preset["env_overrides"]["FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE"] == "1", preset
assert gasal2["topk_summary"]["k"] == cpu["topk_summary"]["k"] == k, (cpu, gasal2)
for mode in ("score", "stability", "nt_score"):
    assert gasal2["topk_summary"]["modes"][mode] == cpu["topk_summary"]["modes"][mode], (
        mode,
        cpu["topk_summary"]["modes"][mode],
        gasal2["topk_summary"]["modes"][mode],
    )
    assert preset["topk_summary"]["modes"][mode] == gasal2["topk_summary"]["modes"][mode], (
        mode,
        gasal2["topk_summary"]["modes"][mode],
        preset["topk_summary"]["modes"][mode],
    )
for report in (cpu, gasal2, preset):
    topk_output = Path(report["topk_summary_output"])
    assert topk_output.exists() and topk_output.stat().st_size > 0, report
    assert len(report["topk_summary_digest"]) == 64, report
    assert len(report["topk_summary_payload_digest"]) == 64, report
    lines = topk_output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# result_contract=" + report["result_contract"], lines[:1]
    assert lines[1].startswith("mode\trank\t"), lines[:2]
    topk_rows_output = Path(report["topk_rows_output"])
    assert topk_rows_output.exists() and topk_rows_output.stat().st_size > 0, report
    assert len(report["topk_rows_digest"]) == 64, report
    assert len(report["topk_rows_payload_digest"]) == 64, report
    row_lines = topk_rows_output.read_text(encoding="utf-8").splitlines()
    assert row_lines[0] == "# result_contract=" + report["result_contract"], row_lines[:1]
    assert row_lines[1].startswith("mode\trank\tChr\t"), row_lines[:2]
    topk_lite_output = Path(report["topk_lite_output"])
    assert topk_lite_output.exists() and topk_lite_output.stat().st_size > 0, report
    assert len(report["topk_lite_digest"]) == 64, report
    assert 0 < report["topk_lite_records"] <= k * 3, report
    lite_lines = topk_lite_output.read_text(encoding="utf-8").splitlines()
    assert lite_lines[0].startswith("Chr\tStartInGenome\t"), lite_lines[:1]
    assert len(lite_lines) == report["topk_lite_records"] + 1, report
assert gasal2["topk_summary_payload_digest"] == cpu["topk_summary_payload_digest"], (cpu, gasal2)
assert preset["topk_summary_payload_digest"] == cpu["topk_summary_payload_digest"], (cpu, preset)
assert gasal2["topk_rows_payload_digest"] == cpu["topk_rows_payload_digest"], (cpu, gasal2)
assert preset["topk_rows_payload_digest"] == cpu["topk_rows_payload_digest"], (cpu, preset)
assert gasal2["topk_lite_digest"] == cpu["topk_lite_digest"], (cpu, gasal2)
assert preset["topk_lite_digest"] == cpu["topk_lite_digest"], (cpu, preset)
assert gasal2["topk_lite_records"] == cpu["topk_lite_records"], (cpu, gasal2)
assert preset["topk_lite_records"] == cpu["topk_lite_records"], (cpu, preset)
assert gasal2["topk_summary_raw_path"] is True, gasal2
assert preset["topk_summary_raw_path"] is True, preset
assert gasal2["env_overrides"]["FASIM_TOP5_GASAL2_GPU_SCOREINFO"] == "1", gasal2
assert gasal2["env_overrides"]["FASIM_TOP5_GASAL2_PHASE_TIMING"] == "1", gasal2
assert gasal2["env_overrides"]["FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE"] == "1", gasal2
assert gasal2["env_overrides"]["FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK"] == str(prune_max), gasal2
assert gasal2["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU"] == "1", gasal2
assert gasal2["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK"] == str(exact_scoreinfo_max), gasal2
assert gasal2["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT"] == "1", gasal2
assert gasal2["env_overrides"]["FASIM_OUTPUT_TOPK_LITE"] == str(k), gasal2
assert preset["env_overrides"]["FASIM_TOP5_GASAL2_GPU_SCOREINFO"] == "1", preset
assert preset["env_overrides"]["FASIM_TOP5_GASAL2_PHASE_TIMING"] == "1", preset
assert preset["env_overrides"]["FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE"] == "1", preset
assert preset["env_overrides"]["FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK"] == str(prune_max), preset
assert preset["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU"] == "1", preset
assert preset["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK"] == str(exact_scoreinfo_max), preset
assert preset["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT"] == "1", preset
assert preset["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT"] == "1", preset
assert preset["env_overrides"]["FASIM_OUTPUT_TOPK_LITE"] == str(k), preset
assert all(shard["raw_topk_only"] is True for shard in gasal2["per_shard"]), gasal2
assert all(shard["raw_topk_only"] is True for shard in preset["per_shard"]), preset
assert all(shard["records"] <= k * 3 for shard in gasal2["per_shard"]), gasal2
assert all(shard["records"] <= k * 3 for shard in preset["per_shard"]), preset
for report in (gasal2, preset):
    benchmark_sums = report["fasim_benchmark_sums"]
    benchmark_shards = report["fasim_benchmark_shards"]
    assert benchmark_shards == report["shard_count"], report
    assert benchmark_sums["fasim_top5_gasal2_gpu_scoreinfo_requested"] == report["shard_count"], benchmark_sums
    assert benchmark_sums["fasim_top5_gasal2_gpu_scoreinfo_active"] == report["shard_count"], benchmark_sums
    assert benchmark_sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled"] == report["shard_count"], benchmark_sums
    assert benchmark_sums["fasim_gasal2_requests"] > 0, benchmark_sums
    assert benchmark_sums["fasim_gasal2_score_requests"] > 0, benchmark_sums
    assert benchmark_sums["fasim_gasal2_traceback_requests"] > 0, benchmark_sums
    assert benchmark_sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches"] == 0, benchmark_sums
    assert benchmark_sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches"] == 0, benchmark_sums
    assert benchmark_sums["fasim_gasal2_fallbacks"] == 0, benchmark_sums
    assert benchmark_sums["fasim_gasal2_length_guard_fallbacks"] == 0, benchmark_sums
for shard in preset["per_shard"]:
    output_dir = Path(shard["run"]["cmd"][-1])
    lite_outputs = sorted(output_dir.glob("*-TFOsorted.lite"))
    assert len(lite_outputs) == 1, (output_dir, lite_outputs)
    rank_dump = Path(str(lite_outputs[0]) + ".topk_rank.tsv")
    assert rank_dump.exists(), rank_dump
    lines = rank_dump.read_text().splitlines()
    assert lines[0] == "mode\trank_in_mode\tscoreinfo_rank\tkey", lines[:1]
    assert len(lines) == 1 + k * 3, rank_dump
    assert any(line.split("\t", 3)[2] != "0" for line in lines[1:]), rank_dump
print("topk_summary_match=true")
print("preset_topk_summary_match=true")
for mode, payload in sorted(gasal2["topk_summary"]["modes"].items()):
    print(f"{mode}_digest={payload['digest']}")
PY

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_column_pruned_preset" \
  --manifest "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --resume \
  >"$WORK/gasal2_top5_column_pruned_preset_resume.stdout.log" \
  2>"$WORK/gasal2_top5_column_pruned_preset_resume.stderr.log"

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_column_pruned_preset/report.json" \
  --manifest "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" \
  --same-payload-as "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/gasal2_top5_prune/report.json"

python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())

assert report["run_status"] == "completed", report
assert manifest["run_status"] == "completed", manifest
assert report["gasal2_top5_activation_verified"] is True, report
assert report["gasal2_top5_activation_error"] is None, report
assert manifest["gasal2_top5_activation_verified"] is True, manifest
assert manifest["gasal2_top5_activation_error"] is None, manifest
for field in (
    "gasal2_top5_query_preflight_supported",
    "gasal2_top5_query_preflight_error",
    "gasal2_top5_query_preflight_query_len",
    "gasal2_top5_query_preflight_max_query_len",
):
    assert manifest[field] == report[field], (field, report, manifest)
assert report["gasal2_top5_query_preflight_supported"] is True, report
assert report["gasal2_top5_query_preflight_error"] is None, report
assert report["gasal2_top5_query_preflight_query_len"] <= report["gasal2_top5_query_preflight_max_query_len"], report
assert len(report["resumed_shards"]) == report["shard_count"], report
assert all(shard["status"] == "skipped_by_resume" for shard in manifest["per_shard"]), manifest
assert all(shard["skipped_by_resume"] is True for shard in manifest["per_shard"]), manifest
assert all(shard["raw_topk_only"] is True for shard in manifest["per_shard"]), manifest
print("preset_resume_activation_verified=true")
PY

python3 - "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
manifest = json.loads(manifest_path.read_text())
manifest["gasal2_top5_activation_verified"] = True
manifest["gasal2_top5_activation_error"] = "synthetic stale activation error"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_column_pruned_preset" \
  --manifest "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --resume \
  >"$WORK/gasal2_top5_column_pruned_preset_stale_activation_resume.stdout.log" \
  2>"$WORK/gasal2_top5_column_pruned_preset_stale_activation_resume.stderr.log"

grep -q -- "resume manifest lacks verified GASAL2 top5 activation" \
  "$WORK/gasal2_top5_column_pruned_preset_stale_activation_resume.stderr.log"

python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" "$WORK/gasal2_top5_column_pruned_preset/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())

assert report["run_status"] == "completed", report
assert manifest["run_status"] == "completed", manifest
assert report["gasal2_top5_activation_verified"] is True, report
assert report["gasal2_top5_activation_error"] is None, report
assert manifest["gasal2_top5_activation_verified"] is True, manifest
assert manifest["gasal2_top5_activation_error"] is None, manifest
assert not report["resumed_shards"], report
assert all(shard["status"] == "completed" for shard in manifest["per_shard"]), manifest
assert all(shard["skipped_by_resume"] is False for shard in manifest["per_shard"]), manifest
PY

fresh_summary="$(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.dumps(json.loads(Path(sys.argv[1]).read_text())["topk_summary"], sort_keys=True))
PY
)"
fresh_topk_digest="$(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["topk_summary_digest"])
PY
)"
fresh_topk_payload_digest="$(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["topk_summary_payload_digest"])
PY
)"
fresh_topk_rows_digest="$(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["topk_rows_digest"])
PY
)"
fresh_topk_rows_payload_digest="$(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["topk_rows_payload_digest"])
PY
)"
fresh_topk_lite_digest="$(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["topk_lite_digest"])
PY
)"
fresh_run_config_digest="$(python3 - "$WORK/gasal2_top5_prune/run_manifest.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["run_config_digest"])
PY
)"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_prune" \
  --manifest "$WORK/gasal2_top5_prune/run_manifest.json" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --shard-output-topk-lite "$K" \
  --gasal2-top5-scoreinfo-prune-max-per-task "$PRUNE_MAX_PER_TASK" \
  --exact-scoreinfo-gpu-max-per-task "$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
  --exact-scoreinfo-gpu-pruned-output \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --resume \
  >"$WORK/gasal2_top5_prune_resume.stdout.log" \
  2>"$WORK/gasal2_top5_prune_resume.stderr.log"

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/gasal2_top5_prune/report.json" \
  --manifest "$WORK/gasal2_top5_prune/run_manifest.json" \
  --same-payload-as "$WORK/cpu_summary/report.json" \
  --different-full-digest-from "$WORK/cpu_summary/report.json"

python3 - "$WORK/gasal2_top5_prune/report.json" "$WORK/gasal2_top5_prune/run_manifest.json" "$fresh_summary" "$fresh_topk_digest" "$fresh_topk_payload_digest" "$fresh_topk_rows_digest" "$fresh_topk_rows_payload_digest" "$fresh_topk_lite_digest" "$fresh_run_config_digest" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())
fresh_summary = json.loads(sys.argv[3])
fresh_topk_digest = sys.argv[4]
fresh_topk_payload_digest = sys.argv[5]
fresh_topk_rows_digest = sys.argv[6]
fresh_topk_rows_payload_digest = sys.argv[7]
fresh_topk_lite_digest = sys.argv[8]
fresh_digest = sys.argv[9]

assert report["run_status"] == "completed", report
assert report["run_config_digest"] == fresh_digest, report
assert report["topk_summary"] == fresh_summary, report
assert report["topk_summary_digest"] == fresh_topk_digest, report
assert report["topk_summary_payload_digest"] == fresh_topk_payload_digest, report
assert report["topk_rows_digest"] == fresh_topk_rows_digest, report
assert report["topk_rows_payload_digest"] == fresh_topk_rows_payload_digest, report
assert report["topk_lite_digest"] == fresh_topk_lite_digest, report
assert manifest["topk_summary_digest"] == fresh_topk_digest, manifest
assert manifest["topk_summary_payload_digest"] == fresh_topk_payload_digest, manifest
assert manifest["topk_rows_digest"] == fresh_topk_rows_digest, manifest
assert manifest["topk_rows_payload_digest"] == fresh_topk_rows_payload_digest, manifest
assert manifest["topk_lite_digest"] == fresh_topk_lite_digest, manifest
assert manifest["result_contract"] == "gasal2_top5_scoreinfo_artifact_v1", manifest
assert Path(manifest["topk_summary_output"]).exists(), manifest
assert Path(manifest["topk_rows_output"]).exists(), manifest
assert Path(manifest["topk_lite_output"]).exists(), manifest
assert len(report["resumed_shards"]) == report["shard_count"], report
assert manifest["run_status"] == "completed", manifest
assert all(shard["status"] == "skipped_by_resume" for shard in manifest["per_shard"]), manifest
assert all(shard["raw_topk_only"] is True for shard in manifest["per_shard"]), manifest
assert all(shard["skipped_by_resume"] is True for shard in manifest["per_shard"]), manifest
assert all(shard["output_digest"] for shard in manifest["per_shard"]), manifest
print("resume_topk_summary_match=true")
PY

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_prune" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  --gasal2-top5-scoreinfo-prune-max-per-task 9 \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_prune.stdout.log" \
  2>"$WORK/preset_bad_prune.stderr.log"; then
  echo "expected preset_bad_prune to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo uses --gasal2-top5-scoreinfo-prune-max-per-task 64' \
  "$WORK/preset_bad_prune.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_cap32" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  --gasal2-top5-scoreinfo-prune-max-per-task 32 \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_cap32.stdout.log" \
  2>"$WORK/preset_bad_cap32.stderr.log"; then
  echo "expected preset_bad_cap32 to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo uses --gasal2-top5-scoreinfo-prune-max-per-task 64' \
  "$WORK/preset_bad_cap32.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_prealign_max_tasks" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  --env FASIM_PREALIGN_CUDA_MAX_TASKS=4096 \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_prealign_max_tasks.stdout.log" \
  2>"$WORK/preset_bad_prealign_max_tasks.stderr.log"; then
  echo "expected preset_bad_prealign_max_tasks to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo cannot be combined with --env for: FASIM_PREALIGN_CUDA_MAX_TASKS' \
  "$WORK/preset_bad_prealign_max_tasks.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_segmented_shadow_env" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  --env FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1 \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_segmented_shadow_env.stdout.log" \
  2>"$WORK/preset_bad_segmented_shadow_env.stderr.log"; then
  echo "expected preset_bad_segmented_shadow_env to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo cannot be combined with --env for: FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW' \
  "$WORK/preset_bad_segmented_shadow_env.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_topk" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --shard-output-topk-lite 4 \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_topk.stdout.log" \
  2>"$WORK/preset_bad_topk.stderr.log"; then
  echo "expected preset_bad_topk to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo requires --shard-output-topk-lite 5' \
  "$WORK/preset_bad_topk.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_summary_k" \
  --topk-summary 4 \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_summary_k.stdout.log" \
  2>"$WORK/preset_bad_summary_k.stderr.log"; then
  echo "expected preset_bad_summary_k to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo uses --topk-summary 5' \
  "$WORK/preset_bad_summary_k.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_output_mode" \
  --output-mode tfosorted \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_output_mode.stdout.log" \
  2>"$WORK/preset_bad_output_mode.stderr.log"; then
  echo "expected preset_bad_output_mode to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo requires --output-mode lite' \
  "$WORK/preset_bad_output_mode.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_validate_single" \
  --validate-single \
  --gasal2-top5-column-pruned-scoreinfo \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_validate_single.stdout.log" \
  2>"$WORK/preset_bad_validate_single.stderr.log"; then
  echo "expected preset_bad_validate_single to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo cannot be combined with --validate-single' \
  "$WORK/preset_bad_validate_single.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/preset_bad_single_pass_topn" \
  --gasal2-top5-column-pruned-scoreinfo \
  --gasal2-single-pass-topn \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --force \
  >"$WORK/preset_bad_single_pass_topn.stdout.log" \
  2>"$WORK/preset_bad_single_pass_topn.stderr.log"; then
  echo "expected preset_bad_single_pass_topn to fail" >&2
  exit 1
fi
grep -q -- '--gasal2-top5-column-pruned-scoreinfo cannot be combined with --gasal2-single-pass-topn' \
  "$WORK/preset_bad_single_pass_topn.stderr.log"

mapfile -t stderr_paths < <(python3 - "$WORK/gasal2_top5_prune/report.json" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text())
for shard in report["per_shard"]:
    print(shard["run"]["stderr_path"])
PY
)
mapfile -t preset_stderr_paths < <(python3 - "$WORK/gasal2_top5_column_pruned_preset/report.json" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text())
for shard in report["per_shard"]:
    print(shard["run"]["stderr_path"])
PY
)

for stderr_path in "${stderr_paths[@]}"; do
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_requested=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_active=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled=1$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_batches=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_input_groups=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_kept_groups=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_pruned_groups=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks=[1-9][0-9]*$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches=0$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches=0$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_enabled=1$' "$stderr_path"
  grep -q "^benchmark\\.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task=$PRUNE_MAX_PER_TASK$" "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_pruned_groups=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_gasal2_requests=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_gasal2_score_requests=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_gasal2_traceback_requests=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_tasks=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_tasks_with_input=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0(\.0+)?$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds=0(\.0+)?$' "$stderr_path"
  grep -q '^benchmark\.fasim_gasal2_fallbacks=0$' "$stderr_path"
  grep -q '^benchmark\.fasim_gasal2_length_guard_fallbacks=0$' "$stderr_path"
done

for stderr_path in "${preset_stderr_paths[@]}"; do
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_requested=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_active=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled=1$' "$stderr_path"
  grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_requests=0$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_column_wall_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_exact_column_wall_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches=0$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches=0$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_enabled=1$' "$stderr_path"
  grep -q "^benchmark\\.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task=$PRUNE_MAX_PER_TASK$" "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled=1$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows=[1-9][0-9]*$' "$stderr_path"
  grep -q '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows=0$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_gasal2_requests=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_gasal2_score_requests=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_gasal2_traceback_requests=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_tasks=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_tasks_with_input=[1-9][0-9]*$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0(\.0+)?$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -Eq '^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds=0\.[0-9]*[1-9][0-9]*$|^benchmark\.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds=[1-9][0-9]*(\.[0-9]+)?$' "$stderr_path"
  grep -q '^benchmark\.fasim_gasal2_fallbacks=0$' "$stderr_path"
  grep -q '^benchmark\.fasim_gasal2_length_guard_fallbacks=0$' "$stderr_path"
done

changed_digest_stdout="$WORK/gasal2_top5_prune_changed_digest.stdout.log"
changed_digest_stderr="$WORK/gasal2_top5_prune_changed_digest.stderr.log"
changed_exact_scoreinfo_max=$((EXACT_SCOREINFO_GPU_MAX_PER_TASK + 1))
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_prune" \
  --manifest "$WORK/gasal2_top5_prune/run_manifest.json" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --shard-output-topk-lite "$K" \
  --gasal2-top5-scoreinfo-prune-max-per-task "$PRUNE_MAX_PER_TASK" \
  --exact-scoreinfo-gpu-max-per-task "$changed_exact_scoreinfo_max" \
  --exact-scoreinfo-gpu-pruned-output \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --resume \
  >"$changed_digest_stdout" \
  2>"$changed_digest_stderr"

grep -q 'resume manifest run_config_digest differs' "$changed_digest_stderr"
python3 - "$WORK/gasal2_top5_prune/report.json" "$fresh_run_config_digest" "$changed_exact_scoreinfo_max" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
fresh_digest = sys.argv[2]
changed_exact_scoreinfo_max = int(sys.argv[3])

assert report["run_status"] == "completed", report
assert report["run_config_digest"] != fresh_digest, report
assert report["exact_scoreinfo_gpu_max_per_task"] == changed_exact_scoreinfo_max, report
assert report["exact_scoreinfo_gpu_pruned_output"] is True, report
assert not report["resumed_shards"], report
assert report["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK"] == str(changed_exact_scoreinfo_max), report
assert report["env_overrides"]["FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT"] == "1", report
PY

changed_pruned_stdout="$WORK/gasal2_top5_prune_changed_pruned_output.stdout.log"
changed_pruned_stderr="$WORK/gasal2_top5_prune_changed_pruned_output.stderr.log"
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$DNA" \
  --rna "$RNA" \
  --rule "$RULE" \
  --work-dir "$WORK/gasal2_top5_prune" \
  --manifest "$WORK/gasal2_top5_prune/run_manifest.json" \
  --output-mode lite \
  --topk-summary "$K" \
  --topk-summary-only \
  --shard-output-topk-lite "$K" \
  --gasal2-top5-scoreinfo-prune-max-per-task "$PRUNE_MAX_PER_TASK" \
  --exact-scoreinfo-gpu-max-per-task "$EXACT_SCOREINFO_GPU_MAX_PER_TASK" \
  --workers "$WORKERS" \
  "${runner_gpu_args[@]}" \
  --resume \
  >"$changed_pruned_stdout" \
  2>"$changed_pruned_stderr"

grep -q 'resume manifest run_config_digest differs' "$changed_pruned_stderr"
python3 - "$WORK/gasal2_top5_prune/report.json" "$fresh_run_config_digest" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
fresh_digest = sys.argv[2]

assert report["run_status"] == "completed", report
assert report["run_config_digest"] != fresh_digest, report
assert report["exact_scoreinfo_gpu_pruned_output"] is False, report
assert not report["resumed_shards"], report
assert "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT" not in report["env_overrides"], report
PY

awk -F= '
  /^benchmark\.fasim_top5_gasal2_phase_scoreinfo_prune_(input_groups|kept_groups|pruned_groups)=/ ||
  /^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_(input_groups|kept_groups|pruned_groups)=/ ||
  /^benchmark\.fasim_gasal2_(requests|score_requests|traceback_requests|total_seconds)=/ {
    print
  }
' "${stderr_paths[@]}"

python3 - "$ROOT/fasim/gasal2_align_bridge.cpp" <<'PY'
import re
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
match = re.search(
    r"void decode_gasal_cigar\([^{}]*\)\n\{(?P<body>.*?)\n\}\n\nvoid copy_alignment",
    source,
    re.S,
)
assert match, "decode_gasal_cigar function not found"
body = match.group("body")
assert "std::vector<uint32_t> ops" not in body, "decode_gasal_cigar must write directly into alignment.cigar"
assert "alignment.cigar.push_back" in body, "decode_gasal_cigar must materialize BAM CIGAR ops"
PY

python3 - "$ROOT/fasim/Fasim-LongTarget.cpp" <<'PY'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()
assert (
    "FasimGasal2SelectedAlignment selectedAlignment = replaySelectedByTask[t][si];" not in source
), "GASAL2 convert loop must not copy selected alignments"
assert (
    "StripedSmithWaterman::Alignment gasalAlignment = selectedAlignment.alignment;" not in source
), "GASAL2 convert loop must avoid unconditional Alignment/CIGAR copies"
assert (
    "const FasimGasal2SelectedAlignment &selectedAlignment = replaySelectedByTask[t][si];" in source
), "GASAL2 convert loop should read selected alignments by const reference"
PY

echo "ok"
