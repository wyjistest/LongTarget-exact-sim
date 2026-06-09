#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_runner"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/run"

cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

python3 - "$ROOT/testDNA.fa" "$WORK/inputs/testDNA_multicontig.fa" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

lines = src.read_text().splitlines()
header = lines[0]
sequence = "".join(line.strip() for line in lines[1:] if line.strip())
if not header.startswith(">hg19|chr11|"):
    raise SystemExit(f"unexpected sample header: {header}")

range_text = header.rsplit("|", 1)[1]
start_text, end_text = range_text.split("-", 1)
start = int(start_text)
end = int(end_text)
if start + len(sequence) - 1 != end:
    raise SystemExit("sample length does not match header range")

mid = len(sequence) // 2
left = sequence[:mid]
right = sequence[mid:]
left_start = start
left_end = start + len(left) - 1
right_start = left_end + 1
right_end = end

dst.write_text(
    f">hg19|chr11_left|{left_start}-{left_end}\n"
    f"{left}\n"
    f">hg19|chr11_right|{right_start}-{right_end}\n"
    f"{right}\n"
)
PY

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/run" \
  --output-mode lite \
  --validate-single \
  --topk-summary 5 \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/summary_only" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  >"$WORK/summary_only.stdout.log" \
  2>"$WORK/summary_only.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/summary_only_topk_lite" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --shard-output-topk-lite 5 \
  >"$WORK/summary_only_topk_lite.stdout.log" \
  2>"$WORK/summary_only_topk_lite.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/grouped_records" \
  --output-mode lite \
  --validate-single \
  --topk-summary 5 \
  --group-target-records 2 \
  >"$WORK/grouped_records.stdout.log" \
  2>"$WORK/grouped_records.stderr.log"

python3 - "$WORK/grouped_records/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["target_record_count"] == 2, report
assert report["group_target_records"] == 2, report
assert report["grouped_shard_count"] == 1, report
assert report["shard_count"] == 1, report
assert report["single_vs_sharded_digest_match"] is True, report

shards = json.loads(Path(report["shard_plan"]).read_text(encoding="utf-8"))
assert len(shards) == 1, shards
shard = shards[0]
assert shard["group_member_count"] == 2, shard
assert shard["group_member_names"] == ["chr11_left", "chr11_right"], shard
assert len(shard["group_member_headers"]) == 2, shard
assert len(shard["group_member_ranges"]) == 2, shard
assert len(shard["group_member_input_digests"]) == 2, shard

text = Path(shard["shard_fasta_path"]).read_text(encoding="utf-8")
assert ">hg19|chr11_left|" in text, text
assert ">hg19|chr11_right|" in text, text
PY

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/run/report.json"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/summary_only/report.json" \
  --same-payload-as "$WORK/run/report.json" \
  --different-full-digest-from "$WORK/run/report.json"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/summary_only_topk_lite/report.json" \
  --same-payload-as "$WORK/run/report.json" \
  --different-full-digest-from "$WORK/run/report.json"

python3 - "$WORK/run/report.json" "$WORK/corrupt_topk_lite" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
topk_lite = out_dir / "topk-empty-TFOsorted.lite"
header = Path(report["topk_lite_output"]).read_text(encoding="utf-8").splitlines()[0]
content = header + "\n"
topk_lite.write_text(content, encoding="utf-8")
report["topk_lite_output"] = str(topk_lite)
report["topk_lite_digest"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
report["topk_lite_records"] = 0
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_topk_lite/report.json" \
  >"$WORK/corrupt_topk_lite.stdout.log" \
  2>"$WORK/corrupt_topk_lite.stderr.log"; then
  echo "expected checker to reject topK lite artifact that does not match topK rows" >&2
  exit 1
fi
grep -q -- "topK lite artifact rows do not match topK rows artifact" \
  "$WORK/corrupt_topk_lite.stderr.log"

python3 - "$WORK/run/report.json" "$WORK/corrupt_topk_rows" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

rows_path = out_dir / "topk-empty-rows.tsv"
rows_header = Path(report["topk_rows_output"]).read_text(encoding="utf-8").splitlines()[1]
rows_content = "# result_contract=" + report["result_contract"] + "\n" + rows_header + "\n"
rows_path.write_text(rows_content, encoding="utf-8")

lite_path = out_dir / "topk-empty-TFOsorted.lite"
lite_header = Path(report["topk_lite_output"]).read_text(encoding="utf-8").splitlines()[0]
lite_content = lite_header + "\n"
lite_path.write_text(lite_content, encoding="utf-8")

rows_payload = rows_content.split("\n", 1)[1]
report["topk_rows_output"] = str(rows_path)
report["topk_rows_digest"] = hashlib.sha256(rows_content.encode("utf-8")).hexdigest()
report["topk_rows_payload_digest"] = hashlib.sha256(rows_payload.encode("utf-8")).hexdigest()
report["topk_lite_output"] = str(lite_path)
report["topk_lite_digest"] = hashlib.sha256(lite_content.encode("utf-8")).hexdigest()
report["topk_lite_records"] = 0
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_topk_rows/report.json" \
  >"$WORK/corrupt_topk_rows.stdout.log" \
  2>"$WORK/corrupt_topk_rows.stderr.log"; then
  echo "expected checker to reject topK rows artifact that does not match topK summary" >&2
  exit 1
fi
grep -q -- "topK rows artifact rows do not match topK summary artifact" \
  "$WORK/corrupt_topk_rows.stderr.log"

python3 - "$WORK/run/report.json" "$WORK/corrupt_topk_summary_object" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
report["topk_summary"]["modes"]["score"]["digest"] = "0" * 64
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_topk_summary_object/report.json" \
  >"$WORK/corrupt_topk_summary_object.stdout.log" \
  2>"$WORK/corrupt_topk_summary_object.stderr.log"; then
  echo "expected checker to reject report topk_summary object that does not match artifact" >&2
  exit 1
fi
grep -q -- "topk_summary object does not match topK summary artifact" \
  "$WORK/corrupt_topk_summary_object.stderr.log"

python3 - "$WORK/run/report.json" "$WORK/corrupt_formal_activation" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
contract = "gasal2_top5_column_pruned_scoreinfo_artifact_v1"
formal_env = {
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO": "1",
    "FASIM_TOP5_GASAL2_PHASE_TIMING": "1",
    "FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE": "1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK": "64",
    "FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE": "1",
    "FASIM_PREALIGN_CUDA_MAX_TASKS": "16384",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU": "1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK": "512",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT": "1",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT": "1",
    "FASIM_OUTPUT_TOPK_LITE": "5",
}
shard_count = int(report["shard_count"])
formal_benchmarks = {
    "fasim_top5_gasal2_gpu_scoreinfo_requested": shard_count,
    "fasim_top5_gasal2_gpu_scoreinfo_active": shard_count,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled": shard_count,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled": shard_count,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled": shard_count,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled": shard_count,
    "fasim_gasal2_requests": 1,
    "fasim_gasal2_score_requests": 1,
    "fasim_gasal2_traceback_requests": 1,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks": 1,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows": 1,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank": 1,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches": 0,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches": 0,
    "fasim_gasal2_fallbacks": 0,
    "fasim_gasal2_length_guard_fallbacks": 0,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows": 0,
}

for output_field, digest_field in (
    ("topk_summary_output", "topk_summary_digest"),
    ("topk_rows_output", "topk_rows_digest"),
):
    src = Path(report[output_field])
    lines = src.read_text(encoding="utf-8").splitlines()
    lines[0] = "# result_contract=" + contract
    content = "\n".join(lines) + "\n"
    dst = out_dir / src.name
    dst.write_text(content, encoding="utf-8")
    report[output_field] = str(dst)
    report[digest_field] = hashlib.sha256(content.encode("utf-8")).hexdigest()

report["result_contract"] = contract
report["topk_summary_only"] = True
report["shard_output_topk_lite"] = 5
report["gasal2_top5_column_pruned_scoreinfo"] = True
report["gasal2_top5_scoreinfo_prune_max_per_task"] = 64
report["exact_scoreinfo_gpu_max_per_task"] = 512
report["exact_scoreinfo_gpu_pruned_output"] = True
report["exact_scoreinfo_gpu_column_pruned_output"] = True
report["env_overrides"] = formal_env
report["fasim_benchmark_shards"] = shard_count
report["fasim_benchmark_sums"] = formal_benchmarks
report["gasal2_top5_activation_verified"] = False
report["gasal2_top5_activation_error"] = "synthetic unverified activation"
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_activation/report.json" \
  >"$WORK/corrupt_formal_activation.stdout.log" \
  2>"$WORK/corrupt_formal_activation.stderr.log"; then
  echo "expected checker to reject formal GASAL2 topK artifact without verified activation" >&2
  exit 1
fi
grep -q -- "formal GASAL2 topK artifact requires verified activation" \
  "$WORK/corrupt_formal_activation.stderr.log"

python3 - "$WORK/corrupt_formal_activation/report.json" "$WORK/corrupt_formal_activation_error" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
report["gasal2_top5_activation_verified"] = True
report["gasal2_top5_activation_error"] = "synthetic stale activation error"
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_activation_error/report.json" \
  >"$WORK/corrupt_formal_activation_error.stdout.log" \
  2>"$WORK/corrupt_formal_activation_error.stderr.log"; then
  echo "expected checker to reject formal GASAL2 topK artifact with activation error" >&2
  exit 1
fi
grep -q -- "formal GASAL2 topK artifact activation error must be empty" \
  "$WORK/corrupt_formal_activation_error.stderr.log"

python3 - "$WORK/corrupt_formal_activation/report.json" "$WORK/corrupt_formal_query_preflight" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
for output_field, digest_field in (
    ("topk_summary_output", "topk_summary_digest"),
    ("topk_rows_output", "topk_rows_digest"),
):
    src = Path(report[output_field])
    dst = out_dir / src.name
    content = src.read_text(encoding="utf-8")
    dst.write_text(content, encoding="utf-8")
    report[output_field] = str(dst)
    report[digest_field] = hashlib.sha256(content.encode("utf-8")).hexdigest()
src_lite = Path(report["topk_lite_output"])
dst_lite = out_dir / src_lite.name
lite_content = src_lite.read_text(encoding="utf-8")
dst_lite.write_text(lite_content, encoding="utf-8")
report["topk_lite_output"] = str(dst_lite)
report["topk_lite_digest"] = hashlib.sha256(lite_content.encode("utf-8")).hexdigest()
report["gasal2_top5_activation_verified"] = True
report["gasal2_top5_activation_error"] = None
report["gasal2_top5_query_preflight_supported"] = False
report["gasal2_top5_query_preflight_error"] = "synthetic query preflight failure"
report["gasal2_top5_query_preflight_query_len"] = 8708
report["gasal2_top5_query_preflight_max_query_len"] = 2812
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_query_preflight/report.json" \
  >"$WORK/corrupt_formal_query_preflight.stdout.log" \
  2>"$WORK/corrupt_formal_query_preflight.stderr.log"; then
  echo "expected checker to reject formal GASAL2 topK artifact without verified query preflight" >&2
  exit 1
fi
grep -q -- "formal GASAL2 topK artifact requires verified query preflight" \
  "$WORK/corrupt_formal_query_preflight.stderr.log"

python3 - "$WORK/corrupt_formal_activation/report.json" "$WORK/corrupt_formal_manifest" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
formal_env = dict(report["env_overrides"])

report["gasal2_top5_activation_verified"] = True
report["gasal2_top5_activation_error"] = None
report["gasal2_top5_query_preflight_supported"] = True
report["gasal2_top5_query_preflight_error"] = None
report["gasal2_top5_query_preflight_query_len"] = 2812
report["gasal2_top5_query_preflight_max_query_len"] = 2812
report_path = out_dir / "report.json"
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

manifest = {
    "run_status": "completed",
    "result_contract": report["result_contract"],
    "topk_summary_output": report["topk_summary_output"],
    "topk_summary_digest": report["topk_summary_digest"],
    "topk_summary_payload_digest": report["topk_summary_payload_digest"],
    "topk_rows_output": report["topk_rows_output"],
    "topk_rows_digest": report["topk_rows_digest"],
    "topk_rows_payload_digest": report["topk_rows_payload_digest"],
    "topk_lite_output": report["topk_lite_output"],
    "topk_lite_digest": report["topk_lite_digest"],
    "topk_lite_records": report["topk_lite_records"],
    "env_snapshot": formal_env,
    "gasal2_top5_activation_verified": False,
    "gasal2_top5_activation_error": "synthetic unverified manifest",
}
(out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_manifest/report.json" \
  --manifest "$WORK/corrupt_formal_manifest/run_manifest.json" \
  >"$WORK/corrupt_formal_manifest.stdout.log" \
  2>"$WORK/corrupt_formal_manifest.stderr.log"; then
  echo "expected checker to reject formal GASAL2 manifest without verified activation" >&2
  exit 1
fi
grep -q -- "formal GASAL2 manifest requires verified activation" \
  "$WORK/corrupt_formal_manifest.stderr.log"

python3 - "$WORK/corrupt_formal_manifest/report.json" "$WORK/corrupt_formal_manifest_query_preflight" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
formal_env = dict(report["env_overrides"])
report_path = out_dir / "report.json"
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

manifest = {
    "run_status": "completed",
    "result_contract": report["result_contract"],
    "topk_summary_output": report["topk_summary_output"],
    "topk_summary_digest": report["topk_summary_digest"],
    "topk_summary_payload_digest": report["topk_summary_payload_digest"],
    "topk_rows_output": report["topk_rows_output"],
    "topk_rows_digest": report["topk_rows_digest"],
    "topk_rows_payload_digest": report["topk_rows_payload_digest"],
    "topk_lite_output": report["topk_lite_output"],
    "topk_lite_digest": report["topk_lite_digest"],
    "topk_lite_records": report["topk_lite_records"],
    "env_snapshot": formal_env,
    "gasal2_top5_activation_verified": True,
    "gasal2_top5_activation_error": None,
    "gasal2_top5_query_preflight_supported": False,
    "gasal2_top5_query_preflight_error": "synthetic unverified manifest query preflight",
    "gasal2_top5_query_preflight_query_len": 8708,
    "gasal2_top5_query_preflight_max_query_len": 2812,
}
(out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_manifest_query_preflight/report.json" \
  --manifest "$WORK/corrupt_formal_manifest_query_preflight/run_manifest.json" \
  >"$WORK/corrupt_formal_manifest_query_preflight.stdout.log" \
  2>"$WORK/corrupt_formal_manifest_query_preflight.stderr.log"; then
  echo "expected checker to reject formal GASAL2 manifest without verified query preflight" >&2
  exit 1
fi
grep -q -- "formal GASAL2 manifest requires verified query preflight" \
  "$WORK/corrupt_formal_manifest_query_preflight.stderr.log"

python3 - "$WORK/corrupt_formal_manifest/report.json" "$WORK/corrupt_formal_manifest_query_preflight_mismatch" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
formal_env = dict(report["env_overrides"])
report_path = out_dir / "report.json"
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

manifest = {
    "run_status": "completed",
    "result_contract": report["result_contract"],
    "topk_summary_output": report["topk_summary_output"],
    "topk_summary_digest": report["topk_summary_digest"],
    "topk_summary_payload_digest": report["topk_summary_payload_digest"],
    "topk_rows_output": report["topk_rows_output"],
    "topk_rows_digest": report["topk_rows_digest"],
    "topk_rows_payload_digest": report["topk_rows_payload_digest"],
    "topk_lite_output": report["topk_lite_output"],
    "topk_lite_digest": report["topk_lite_digest"],
    "topk_lite_records": report["topk_lite_records"],
    "env_snapshot": formal_env,
    "gasal2_top5_activation_verified": True,
    "gasal2_top5_activation_error": None,
    "gasal2_top5_query_preflight_supported": True,
    "gasal2_top5_query_preflight_error": None,
    "gasal2_top5_query_preflight_query_len": 8708,
    "gasal2_top5_query_preflight_max_query_len": report["gasal2_top5_query_preflight_max_query_len"],
}
(out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_manifest_query_preflight_mismatch/report.json" \
  --manifest "$WORK/corrupt_formal_manifest_query_preflight_mismatch/run_manifest.json" \
  >"$WORK/corrupt_formal_manifest_query_preflight_mismatch.stdout.log" \
  2>"$WORK/corrupt_formal_manifest_query_preflight_mismatch.stderr.log"; then
  echo "expected checker to reject stale formal GASAL2 manifest query preflight fields" >&2
  exit 1
fi
grep -q -- "formal GASAL2 manifest query preflight fields do not match report" \
  "$WORK/corrupt_formal_manifest_query_preflight_mismatch.stderr.log"

python3 - "$WORK/corrupt_formal_manifest/report.json" "$WORK/corrupt_formal_query_preflight_inconsistent" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
report["gasal2_top5_query_preflight_supported"] = True
report["gasal2_top5_query_preflight_error"] = None
report["gasal2_top5_query_preflight_query_len"] = 8708
report["gasal2_top5_query_preflight_max_query_len"] = 2812
(out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY

if python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/corrupt_formal_query_preflight_inconsistent/report.json" \
  >"$WORK/corrupt_formal_query_preflight_inconsistent.stdout.log" \
  2>"$WORK/corrupt_formal_query_preflight_inconsistent.stderr.log"; then
  echo "expected checker to reject internally inconsistent formal GASAL2 query preflight" >&2
  exit 1
fi
grep -q -- "formal GASAL2 query preflight length exceeds max" \
  "$WORK/corrupt_formal_query_preflight_inconsistent.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/topk_lite_errors/no_summary_only" \
  --output-mode lite \
  --topk-summary 5 \
  --shard-output-topk-lite 5 \
  >"$WORK/topk_lite_errors_no_summary_only.stdout.log" \
  2>"$WORK/topk_lite_errors_no_summary_only.stderr.log"; then
  echo "expected --shard-output-topk-lite without --topk-summary-only to fail" >&2
  exit 1
fi
grep -q -- "--shard-output-topk-lite requires --topk-summary-only" \
  "$WORK/topk_lite_errors_no_summary_only.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/topk_lite_errors/k_mismatch" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --shard-output-topk-lite 3 \
  >"$WORK/topk_lite_errors_k_mismatch.stdout.log" \
  2>"$WORK/topk_lite_errors_k_mismatch.stderr.log"; then
  echo "expected mismatched topK values to fail" >&2
  exit 1
fi
grep -q -- "--shard-output-topk-lite must match --topk-summary" \
  "$WORK/topk_lite_errors_k_mismatch.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/topk_lite_errors/env_conflict" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --shard-output-topk-lite 5 \
  --env FASIM_OUTPUT_TOPK_LITE=5 \
  >"$WORK/topk_lite_errors_env_conflict.stdout.log" \
  2>"$WORK/topk_lite_errors_env_conflict.stderr.log"; then
  echo "expected env conflict to fail" >&2
  exit 1
fi
grep -q -- "--shard-output-topk-lite cannot be combined" \
  "$WORK/topk_lite_errors_env_conflict.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_top5_prune_errors/no_summary_only" \
  --output-mode lite \
  --topk-summary 5 \
  --gasal2-top5-scoreinfo-prune-max-per-task 16 \
  >"$WORK/gasal2_top5_prune_errors_no_summary_only.stdout.log" \
  2>"$WORK/gasal2_top5_prune_errors_no_summary_only.stderr.log"; then
  echo "expected GASAL2 top5 prune preset without --topk-summary-only to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-scoreinfo-prune-max-per-task requires --topk-summary-only" \
  "$WORK/gasal2_top5_prune_errors_no_summary_only.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_top5_prune_errors/topk_not_5" \
  --output-mode lite \
  --topk-summary 3 \
  --topk-summary-only \
  --gasal2-top5-scoreinfo-prune-max-per-task 16 \
  >"$WORK/gasal2_top5_prune_errors_topk_not_5.stdout.log" \
  2>"$WORK/gasal2_top5_prune_errors_topk_not_5.stderr.log"; then
  echo "expected GASAL2 top5 prune preset with --topk-summary != 5 to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-scoreinfo-prune-max-per-task requires --topk-summary 5" \
  "$WORK/gasal2_top5_prune_errors_topk_not_5.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_top5_prune_errors/env_conflict" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --gasal2-top5-scoreinfo-prune-max-per-task 16 \
  --env FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  >"$WORK/gasal2_top5_prune_errors_env_conflict.stdout.log" \
  2>"$WORK/gasal2_top5_prune_errors_env_conflict.stderr.log"; then
  echo "expected GASAL2 top5 prune preset env conflict to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-scoreinfo-prune-max-per-task cannot be combined" \
  "$WORK/gasal2_top5_prune_errors_env_conflict.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_column_pruned_errors/keep_going" \
  --output-mode lite \
  --gasal2-top5-column-pruned-scoreinfo \
  --keep-going \
  >"$WORK/gasal2_column_pruned_errors_keep_going.stdout.log" \
  2>"$WORK/gasal2_column_pruned_errors_keep_going.stderr.log"; then
  echo "expected GASAL2 column-pruned preset with --keep-going to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-column-pruned-scoreinfo cannot be combined with --keep-going" \
  "$WORK/gasal2_column_pruned_errors_keep_going.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_column_pruned_errors/fasim_arg" \
  --output-mode lite \
  --gasal2-top5-column-pruned-scoreinfo \
  --fasim-arg=--synthetic-option \
  >"$WORK/gasal2_column_pruned_errors_fasim_arg.stdout.log" \
  2>"$WORK/gasal2_column_pruned_errors_fasim_arg.stderr.log"; then
  echo "expected GASAL2 column-pruned preset with --fasim-arg to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-column-pruned-scoreinfo cannot be combined with --fasim-arg" \
  "$WORK/gasal2_column_pruned_errors_fasim_arg.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_column_pruned_errors/unknown_env" \
  --output-mode lite \
  --gasal2-top5-column-pruned-scoreinfo \
  --env FASIM_SYNTHETIC_UNSAFE=1 \
  >"$WORK/gasal2_column_pruned_errors_unknown_env.stdout.log" \
  2>"$WORK/gasal2_column_pruned_errors_unknown_env.stderr.log"; then
  echo "expected GASAL2 column-pruned preset with unknown --env to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-column-pruned-scoreinfo cannot be combined with --env for: FASIM_SYNTHETIC_UNSAFE" \
  "$WORK/gasal2_column_pruned_errors_unknown_env.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_column_pruned_errors/not_built" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --gasal2-top5-column-pruned-scoreinfo \
  >"$WORK/gasal2_column_pruned_errors_not_built.stdout.log" \
  2>"$WORK/gasal2_column_pruned_errors_not_built.stderr.log"; then
  echo "expected GASAL2 column-pruned preset with non-GASAL2 binary to fail" >&2
  exit 1
fi
grep -q -- "--gasal2-top5-column-pruned-scoreinfo requires a GASAL2-enabled Fasim binary" \
  "$WORK/gasal2_column_pruned_errors_not_built.stderr.log"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/gasal2_top5_prune_errors/not_built" \
  --output-mode lite \
  --topk-summary 5 \
  --topk-summary-only \
  --shard-output-topk-lite 5 \
  --gasal2-top5-scoreinfo-prune-max-per-task 16 \
  >"$WORK/gasal2_top5_prune_errors_not_built.stdout.log" \
  2>"$WORK/gasal2_top5_prune_errors_not_built.stderr.log"; then
  echo "expected GASAL2 top5 prune preset with non-GASAL2 binary to fail" >&2
  exit 1
fi
grep -q -- "GASAL2 scoreInfo/preAlign runner options require a GASAL2-enabled Fasim binary" \
  "$WORK/gasal2_top5_prune_errors_not_built.stderr.log"

python3 - "$ROOT/scripts/fasim_sharded_runner.py" <<'PY'
import importlib.util
import sys
from pathlib import Path

module_path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("fasim_sharded_runner", module_path)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


class Args:
    gasal2_top5_column_pruned_scoreinfo = True


class NonFormalArgs:
    gasal2_top5_column_pruned_scoreinfo = False


short_query = [runner.FastaRecord(header="short", sequence="A" * 2812)]
long_query = [runner.FastaRecord(header="long", sequence="A" * 8708)]
assert runner._gasal2_top5_query_preflight_error(Args(), {}, short_query) is None
assert runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "2812"},
    short_query,
) is None
long_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "8708"},
    long_query,
)
assert long_error is not None and "cannot override" in long_error, long_error
query_cap_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "2813"},
    short_query,
)
assert query_cap_error is not None and "cannot override" in query_cap_error, query_cap_error
zero_query_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "0"},
    short_query,
)
assert zero_query_error is not None and "positive" in zero_query_error, zero_query_error
bad_query_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "synthetic"},
    short_query,
)
assert bad_query_error is not None and "integer" in bad_query_error, bad_query_error
assert runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_BATCH": "30000"},
    short_query,
) is None
batch_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_BATCH": "40000"},
    short_query,
)
assert batch_error is not None and "FASIM_ALIGN_GASAL2_BATCH" in batch_error, batch_error
zero_batch_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_BATCH": "0"},
    short_query,
)
assert zero_batch_error is not None and "positive" in zero_batch_error, zero_batch_error
bad_batch_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_BATCH": "synthetic"},
    short_query,
)
assert bad_batch_error is not None and "integer" in bad_batch_error, bad_batch_error
assert runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_STREAMS": "2"},
    short_query,
) is None
assert runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_STREAMS": "16"},
    short_query,
) is None
streams_cap_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_STREAMS": "17"},
    short_query,
)
assert streams_cap_error is not None and "FASIM_ALIGN_GASAL2_STREAMS" in streams_cap_error, streams_cap_error
zero_streams_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_STREAMS": "0"},
    short_query,
)
assert zero_streams_error is not None and "positive" in zero_streams_error, zero_streams_error
bad_streams_error = runner._gasal2_top5_query_preflight_error(
    Args(),
    {"FASIM_ALIGN_GASAL2_STREAMS": "synthetic"},
    short_query,
)
assert bad_streams_error is not None and "integer" in bad_streams_error, bad_streams_error

preflight_ok = runner._gasal2_top5_query_preflight_report_fields(
    Args(),
    {},
    short_query,
)
assert preflight_ok == {
    "gasal2_top5_query_preflight_supported": True,
    "gasal2_top5_query_preflight_error": None,
    "gasal2_top5_query_preflight_query_len": 2812,
    "gasal2_top5_query_preflight_max_query_len": 2812,
}, preflight_ok
preflight_cap_error = runner._gasal2_top5_query_preflight_report_fields(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "2813"},
    short_query,
)
assert preflight_cap_error["gasal2_top5_query_preflight_supported"] is False, preflight_cap_error
assert "cannot override" in preflight_cap_error["gasal2_top5_query_preflight_error"], preflight_cap_error
assert preflight_cap_error["gasal2_top5_query_preflight_query_len"] == 2812, preflight_cap_error
assert preflight_cap_error["gasal2_top5_query_preflight_max_query_len"] == 2813, preflight_cap_error
preflight_parse_error = runner._gasal2_top5_query_preflight_report_fields(
    Args(),
    {"FASIM_ALIGN_GASAL2_MAX_QUERY_LEN": "synthetic"},
    short_query,
)
assert preflight_parse_error["gasal2_top5_query_preflight_supported"] is False, preflight_parse_error
assert "integer" in preflight_parse_error["gasal2_top5_query_preflight_error"], preflight_parse_error
assert preflight_parse_error["gasal2_top5_query_preflight_query_len"] == 2812, preflight_parse_error
assert preflight_parse_error["gasal2_top5_query_preflight_max_query_len"] is None, preflight_parse_error
preflight_non_formal = runner._gasal2_top5_query_preflight_report_fields(
    NonFormalArgs(),
    {},
    short_query,
)
assert preflight_non_formal == {
    "gasal2_top5_query_preflight_supported": None,
    "gasal2_top5_query_preflight_error": None,
    "gasal2_top5_query_preflight_query_len": None,
    "gasal2_top5_query_preflight_max_query_len": None,
}, preflight_non_formal


ok_sums = {
    "fasim_top5_gasal2_gpu_scoreinfo_requested": 2,
    "fasim_top5_gasal2_gpu_scoreinfo_active": 2,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled": 2,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled": 2,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled": 2,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled": 2,
    "fasim_gasal2_requests": 10,
    "fasim_gasal2_score_requests": 10,
    "fasim_gasal2_traceback_requests": 10,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks": 10,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows": 10,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank": 5,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches": 0,
    "fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches": 0,
    "fasim_gasal2_fallbacks": 0,
    "fasim_gasal2_length_guard_fallbacks": 0,
    "fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows": 0,
}
ok = runner._gasal2_top5_activation_report_fields(Args(), ok_sums, 2, 2)
assert ok["gasal2_top5_activation_verified"] is True, ok
assert ok["gasal2_top5_activation_error"] is None, ok

bad_sums = dict(ok_sums)
bad_sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled"] = 1
bad = runner._gasal2_top5_activation_report_fields(Args(), bad_sums, 2, 2)
assert bad["gasal2_top5_activation_verified"] is False, bad
assert "column_pruned_output_enabled" in bad["gasal2_top5_activation_error"], bad


class Manifest:
    def __init__(
        self,
        verified,
        activation_error=None,
        *,
        query_supported=True,
        query_error=None,
        query_len=2812,
        max_query_len=2812,
    ):
        self.payload = {
            "run_config_digest": "digest",
            "gasal2_top5_activation_verified": verified,
            "gasal2_top5_activation_error": activation_error,
            "gasal2_top5_query_preflight_supported": query_supported,
            "gasal2_top5_query_preflight_error": query_error,
            "gasal2_top5_query_preflight_query_len": query_len,
            "gasal2_top5_query_preflight_max_query_len": max_query_len,
            "per_shard": [
                {"shard_id": "shard_0000", "status": "completed"},
                {"shard_id": "shard_0001", "status": "completed"},
            ],
        }


assert sorted(runner._resume_entries_for_manifest(Manifest(True), Args(), "digest")) == [
    "shard_0000",
    "shard_0001",
]
assert runner._resume_entries_for_manifest(Manifest(False), Args(), "digest") == {}
assert runner._resume_entries_for_manifest(Manifest(None), Args(), "digest") == {}
assert runner._resume_entries_for_manifest(Manifest(True, "stale activation error"), Args(), "digest") == {}
assert runner._resume_entries_for_manifest(Manifest(True, query_supported=None), Args(), "digest") == {}
assert runner._resume_entries_for_manifest(Manifest(True, query_supported=False), Args(), "digest") == {}
assert runner._resume_entries_for_manifest(
    Manifest(True, query_error="stale query preflight error"),
    Args(),
    "digest",
) == {}
assert runner._resume_entries_for_manifest(
    Manifest(True, query_len=None),
    Args(),
    "digest",
) == {}
assert runner._resume_entries_for_manifest(
    Manifest(True, max_query_len=None),
    Args(),
    "digest",
) == {}
assert runner._resume_entries_for_manifest(
    Manifest(True, query_len=2813, max_query_len=2812),
    Args(),
    "digest",
) == {}
assert runner._resume_entries_for_manifest(
    Manifest(True, max_query_len=2813),
    Args(),
    "digest",
) == {}
PY

python3 - "$WORK/run/report.json" "$WORK/summary_only/report.json" "$WORK/summary_only_topk_lite/report.json" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
report = json.loads(report_path.read_text())
summary_only = json.loads(Path(sys.argv[2]).read_text())
summary_only_topk_lite = json.loads(Path(sys.argv[3]).read_text())

assert report["shard_count"] == 2, report
assert report["result_contract"] == "merged_output_v1", report
assert report["single_vs_sharded_digest_match"] is True, report
assert report["single_records"] == report["merged_records"], report
assert report["sharded_records"] >= report["merged_records"], report
assert len(report["per_shard"]) == 2, report
for shard in report["per_shard"]:
    assert shard["target_name"] in {"chr11_left", "chr11_right"}, shard
    assert len(shard["digest"]) == 64, shard

merged = Path(report["merged_output"])
assert merged.exists() and merged.stat().st_size > 0, report
assert len(report["merged_digest"]) == 64, report
assert len(report["single_digest"]) == 64, report
topk = report["topk_summary"]
assert topk["k"] == 5, topk
assert topk["rows_considered"] == report["merged_records"], topk
assert set(topk["modes"]) == {"score", "stability", "nt_score"}, topk
for mode, payload in topk["modes"].items():
    assert len(payload["digest"]) == 64, (mode, payload)
    assert 0 < len(payload["keys"]) <= 5, (mode, payload)
    assert 0 < len(payload["rows"]) <= 5, (mode, payload)
    assert len(payload["rows"]) == len(payload["keys"]), (mode, payload)
topk_artifact = Path(report["topk_summary_output"])
assert topk_artifact.exists() and topk_artifact.stat().st_size > 0, report
assert len(report["topk_summary_digest"]) == 64, report
assert len(report["topk_summary_payload_digest"]) == 64, report
topk_artifact_lines = topk_artifact.read_text(encoding="utf-8").splitlines()
assert topk_artifact_lines[0] == "# result_contract=merged_output_v1", topk_artifact_lines[:1]
assert topk_artifact_lines[1].startswith("mode\trank\t"), topk_artifact_lines[:2]
topk_rows_artifact = Path(report["topk_rows_output"])
assert topk_rows_artifact.exists() and topk_rows_artifact.stat().st_size > 0, report
assert len(report["topk_rows_digest"]) == 64, report
assert len(report["topk_rows_payload_digest"]) == 64, report
topk_rows_lines = topk_rows_artifact.read_text(encoding="utf-8").splitlines()
assert topk_rows_lines[0] == "# result_contract=merged_output_v1", topk_rows_lines[:1]
assert topk_rows_lines[1].startswith("mode\trank\tChr\t"), topk_rows_lines[:2]
topk_lite = Path(report["topk_lite_output"])
assert topk_lite.exists() and topk_lite.stat().st_size > 0, report
assert len(report["topk_lite_digest"]) == 64, report
assert 0 < report["topk_lite_records"] <= 15, report
topk_lite_lines = topk_lite.read_text(encoding="utf-8").splitlines()
assert topk_lite_lines[0].startswith("Chr\tStartInGenome\t"), topk_lite_lines[:1]
assert len(topk_lite_lines) == report["topk_lite_records"] + 1, report

assert summary_only["run_status"] == "completed", summary_only
assert summary_only["result_contract"] == "topk_summary_artifact_v1", summary_only
assert summary_only["topk_summary_only"] is True, summary_only
assert summary_only["topk_summary_raw_path"] is True, summary_only
assert summary_only["merge_seconds"] == 0.0, summary_only
assert summary_only["merged_output"] is None, summary_only
assert summary_only["merged_digest"] is None, summary_only
assert summary_only["merged_records"] is None, summary_only
assert summary_only["duplicate_records_removed"] is None, summary_only
assert summary_only["topk_summary"] == report["topk_summary"], summary_only
assert summary_only["topk_summary_payload_digest"] == report["topk_summary_payload_digest"], summary_only
assert summary_only["topk_rows_payload_digest"] == report["topk_rows_payload_digest"], summary_only
assert summary_only["topk_lite_digest"] == report["topk_lite_digest"], summary_only
assert summary_only["topk_lite_records"] == report["topk_lite_records"], summary_only
assert Path(summary_only["topk_summary_output"]).exists(), summary_only
assert Path(summary_only["topk_rows_output"]).exists(), summary_only
assert Path(summary_only["topk_lite_output"]).exists(), summary_only
summary_only_lines = Path(summary_only["topk_summary_output"]).read_text(encoding="utf-8").splitlines()
assert summary_only_lines[0] == "# result_contract=topk_summary_artifact_v1", summary_only_lines[:1]
summary_only_rows_lines = Path(summary_only["topk_rows_output"]).read_text(encoding="utf-8").splitlines()
assert summary_only_rows_lines[0] == "# result_contract=topk_summary_artifact_v1", summary_only_rows_lines[:1]

assert summary_only_topk_lite["run_status"] == "completed", summary_only_topk_lite
assert summary_only_topk_lite["result_contract"] == "topk_summary_artifact_v1", summary_only_topk_lite
assert summary_only_topk_lite["topk_summary_only"] is True, summary_only_topk_lite
assert summary_only_topk_lite["topk_summary_raw_path"] is True, summary_only_topk_lite
assert summary_only_topk_lite["shard_output_topk_lite"] == 5, summary_only_topk_lite
assert summary_only_topk_lite["env_overrides"]["FASIM_OUTPUT_TOPK_LITE"] == "5", summary_only_topk_lite
assert summary_only_topk_lite["topk_summary"] == report["topk_summary"], summary_only_topk_lite
assert summary_only_topk_lite["topk_summary_payload_digest"] == report["topk_summary_payload_digest"], summary_only_topk_lite
assert summary_only_topk_lite["topk_rows_payload_digest"] == report["topk_rows_payload_digest"], summary_only_topk_lite
assert summary_only_topk_lite["topk_lite_digest"] == report["topk_lite_digest"], summary_only_topk_lite
assert summary_only_topk_lite["topk_lite_records"] == report["topk_lite_records"], summary_only_topk_lite
assert Path(summary_only_topk_lite["topk_summary_output"]).exists(), summary_only_topk_lite
assert Path(summary_only_topk_lite["topk_rows_output"]).exists(), summary_only_topk_lite
assert Path(summary_only_topk_lite["topk_lite_output"]).exists(), summary_only_topk_lite
assert summary_only_topk_lite["run_config_digest"] != summary_only["run_config_digest"], (
    summary_only_topk_lite,
    summary_only,
)
for shard in summary_only_topk_lite["per_shard"]:
    assert shard["records"] <= 15, shard
PY

echo "ok"
