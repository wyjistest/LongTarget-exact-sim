#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_sharded_runner_resume"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/logs" "$WORK/errors"

cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"
FAIL_BIN="$WORK/fail_fasim.sh"
cat >"$FAIL_BIN" <<'SH'
#!/usr/bin/env bash
echo "intentional shard failure" >&2
exit 7
SH
chmod +x "$FAIL_BIN"

python3 - "$ROOT/testDNA.fa" "$WORK/inputs/testDNA_three_contigs.fa" <<'PY'
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

third = len(sequence) // 3
parts = [sequence[:third], sequence[third : 2 * third], sequence[2 * third :]]
records = []
offset = start
for idx, part in enumerate(parts, start=1):
    part_start = offset
    part_end = offset + len(part) - 1
    records.append(f">hg19|chr11_part{idx}|{part_start}-{part_end}\n{part}\n")
    offset = part_end + 1
dst.write_text("".join(records))
PY

RUN_DIR="$WORK/run"
MANIFEST="$RUN_DIR/run_manifest.json"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$RUN_DIR" \
  --manifest "$MANIFEST" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --gpu-ids 0,1 \
  >"$WORK/logs/fresh.stdout.log" \
  2>"$WORK/logs/fresh.stderr.log"

python3 - "$RUN_DIR/report.json" "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())

assert manifest["run_status"] == "completed", manifest
assert manifest["run_config_digest"], manifest
assert manifest["target_fasta_digest"], manifest
assert manifest["rna_fasta_digest"], manifest
assert manifest["shard_plan_digest"], manifest
assert len(manifest["per_shard"]) == report["shard_count"], manifest
assert report["resumed_shards"] == [], report
assert report["failed_shards"] == [], report
assert report["merged_digest"] == manifest["merged_digest"], report
assert report["partial_merged_digest"] is None, report
for shard in manifest["per_shard"]:
    assert shard["status"] == "completed", shard
    assert shard["output_path"], shard
    assert Path(shard["output_path"]).exists(), shard
    assert shard["output_digest"], shard
    assert shard["records"] is not None, shard
    assert shard["skipped_by_resume"] is False, shard
PY

FRESH_DIGEST="$(python3 - "$RUN_DIR/report.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["merged_digest"])
PY
)"
FRESH_FIRST_OUTPUT="$(python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text())
print(manifest["per_shard"][0]["output_path"])
PY
)"

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$RUN_DIR" \
  --manifest "$MANIFEST" \
  --output-mode lite \
  --validate-single \
  --workers 2 \
  --gpu-ids 0,1 \
  >"$WORK/errors/existing_workdir.stdout.log" \
  2>"$WORK/errors/existing_workdir.stderr.log"; then
  echo "expected existing work-dir without --resume/--force to fail" >&2
  exit 1
fi
grep -q -- "--resume or --force" "$WORK/errors/existing_workdir.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$RUN_DIR" \
  --manifest "$MANIFEST" \
  --output-mode lite \
  --validate-single \
  --resume \
  --workers 2 \
  --gpu-ids 0,1 \
  >"$WORK/logs/resume.stdout.log" \
  2>"$WORK/logs/resume.stderr.log"

python3 - "$RUN_DIR/report.json" "$MANIFEST" "$FRESH_DIGEST" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())
fresh_digest = sys.argv[3]

assert report["merged_digest"] == fresh_digest, report
assert len(report["resumed_shards"]) == report["shard_count"], report
assert report["failed_shards"] == [], report
assert all(shard["status"] == "skipped_by_resume" for shard in manifest["per_shard"]), manifest
assert all(shard["skipped_by_resume"] is True for shard in manifest["per_shard"]), manifest
PY

rm -f "$FRESH_FIRST_OUTPUT"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$RUN_DIR" \
  --manifest "$MANIFEST" \
  --output-mode lite \
  --validate-single \
  --resume \
  --workers 2 \
  --gpu-ids 0,1 \
  >"$WORK/logs/resume_missing_output.stdout.log" \
  2>"$WORK/logs/resume_missing_output.stderr.log"

python3 - "$RUN_DIR/report.json" "$MANIFEST" "$FRESH_DIGEST" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())
fresh_digest = sys.argv[3]

assert report["merged_digest"] == fresh_digest, report
assert len(report["resumed_shards"]) == report["shard_count"] - 1, report
completed = [shard for shard in manifest["per_shard"] if shard["status"] == "completed"]
skipped = [shard for shard in manifest["per_shard"] if shard["status"] == "skipped_by_resume"]
assert len(completed) == 1, manifest
assert len(skipped) == report["shard_count"] - 1, manifest
PY

FORCE_MANIFEST_BEFORE="$(python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["run_id"])
PY
)"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$RUN_DIR" \
  --manifest "$MANIFEST" \
  --output-mode lite \
  --validate-single \
  --force \
  --workers 2 \
  --gpu-ids 0,1 \
  >"$WORK/logs/force.stdout.log" \
  2>"$WORK/logs/force.stderr.log"

python3 - "$RUN_DIR/report.json" "$MANIFEST" "$FRESH_DIGEST" "$FORCE_MANIFEST_BEFORE" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(sys.argv[2]).read_text())
fresh_digest = sys.argv[3]
old_run_id = sys.argv[4]

assert report["merged_digest"] == fresh_digest, report
assert report["resumed_shards"] == [], report
assert manifest["run_id"] != old_run_id, manifest
assert all(shard["status"] == "completed" for shard in manifest["per_shard"]), manifest
PY

if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$FAIL_BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/keep_going/run" \
  --manifest "$WORK/keep_going/run_manifest.json" \
  --output-mode lite \
  --keep-going \
  --workers 2 \
  >"$WORK/keep_going.stdout.log" \
  2>"$WORK/keep_going.stderr.log"; then
  echo "expected keep-going run with failed shards to return non-zero" >&2
  exit 1
fi

python3 - "$WORK/keep_going/run_manifest.json" "$WORK/keep_going/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
report = json.loads(Path(sys.argv[2]).read_text())

assert manifest["run_status"] == "incomplete", manifest
assert report["run_status"] == "incomplete", report
assert report["failed_shards"], report
assert report["merged_digest"] is None, report
assert report["partial_merged_digest"] is not None, report
assert manifest["merged_digest"] is None, manifest
assert manifest["partial_merged_digest"] == report["partial_merged_digest"], manifest
PY

echo "ok"
