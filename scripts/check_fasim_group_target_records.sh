#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

WORK="$ROOT/.tmp/check_fasim_group_target_records"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/logs"

cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

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
dst.write_text("".join(records), encoding="utf-8")
PY

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/default/run" \
  --output-mode lite \
  --validate-single \
  --manifest "$WORK/default/run_manifest.json" \
  --workers 2 \
  >"$WORK/logs/default.stdout.log" \
  2>"$WORK/logs/default.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/group2/run" \
  --output-mode lite \
  --validate-single \
  --manifest "$WORK/group2/run_manifest.json" \
  --workers 2 \
  --group-target-records 2 \
  >"$WORK/logs/group2.stdout.log" \
  2>"$WORK/logs/group2.stderr.log"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/group2/run" \
  --output-mode lite \
  --validate-single \
  --manifest "$WORK/group2/run_manifest.json" \
  --workers 2 \
  --group-target-records 2 \
  --resume \
  >"$WORK/logs/group2_resume.stdout.log" \
  2>"$WORK/logs/group2_resume.stderr.log"

cp "$WORK/group2/run/report.json" "$WORK/group2_report_before_changed_resume.json"
cp "$WORK/group2/run_manifest.json" "$WORK/group2_manifest_before_changed_resume.json"
cp "$WORK/group2/run/shard_plan.json" "$WORK/group2_shard_plan_before_changed_resume.json"

python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/group2/run" \
  --output-mode lite \
  --validate-single \
  --manifest "$WORK/group2/run_manifest.json" \
  --workers 2 \
  --group-target-records 3 \
  --resume \
  >"$WORK/logs/group3_resume.stdout.log" \
  2>"$WORK/logs/group3_resume.stderr.log"

python3 - "$WORK/default/run/report.json" "$WORK/default/run_manifest.json" "$WORK/group2_report_before_changed_resume.json" "$WORK/group2_manifest_before_changed_resume.json" "$WORK/group2_shard_plan_before_changed_resume.json" "$WORK/group2/run/report.json" "$WORK/group2/run_manifest.json" "$WORK/logs/group3_resume.stderr.log" <<'PY'
import json
import sys
from pathlib import Path

default_report = json.loads(Path(sys.argv[1]).read_text())
default_manifest = json.loads(Path(sys.argv[2]).read_text())
group_report = json.loads(Path(sys.argv[3]).read_text())
group_manifest = json.loads(Path(sys.argv[4]).read_text())
group_plan = json.loads(Path(sys.argv[5]).read_text())
changed_report = json.loads(Path(sys.argv[6]).read_text())
changed_manifest = json.loads(Path(sys.argv[7]).read_text())
changed_resume_stderr = Path(sys.argv[8]).read_text()

assert default_report["group_target_records"] is None, default_report
assert default_report["grouped_shard_count"] == 3, default_report
assert default_report["target_record_count"] == 3, default_report
assert default_report["shard_count"] == 3, default_report
assert default_report["single_vs_sharded_digest_match"] is True, default_report
assert default_manifest["group_target_records"] is None, default_manifest
assert default_manifest["grouped_shard_count"] == 3, default_manifest

assert group_report["group_target_records"] == 2, group_report
assert group_report["grouped_shard_count"] == 2, group_report
assert group_report["target_record_count"] == 3, group_report
assert group_report["shard_count"] == 2, group_report
assert group_report["single_vs_sharded_digest_match"] is True, group_report
assert group_report["merged_digest"] == default_report["merged_digest"], group_report
assert group_report["merged_records"] == default_report["merged_records"], group_report
assert group_report["duplicate_records_removed"] == default_report["duplicate_records_removed"], group_report

assert changed_report["group_target_records"] == 3, changed_report
assert changed_report["grouped_shard_count"] == 1, changed_report
assert changed_report["resumed_shards"] == [], changed_report
assert changed_report["merged_digest"] == default_report["merged_digest"], changed_report
assert changed_manifest["group_target_records"] == 3, changed_manifest
assert changed_manifest["grouped_shard_count"] == 1, changed_manifest
assert len(changed_manifest["per_shard"]) == 1, changed_manifest
assert changed_manifest["run_config_digest"] != group_manifest["run_config_digest"], (
    group_manifest,
    changed_manifest,
)
assert group_report["resumed_shards"] == group_report["shard_ids"], group_report
assert all(shard["skipped_by_resume"] is True for shard in group_report["per_shard"]), group_report
assert "resume manifest run_config_digest differs" in changed_resume_stderr, changed_resume_stderr

first_group = [
    shard for shard in group_report["per_shard"]
    if shard["shard_id"].startswith("shard_0000")
][0]
assert first_group["group_member_count"] == 2, first_group
assert first_group["group_member_headers"] == [
    ">hg19|chr11_part1|2158478-2159932",
    ">hg19|chr11_part2|2159933-2161387",
], first_group
assert first_group["target_name"] == "chr11_part1..chr11_part2", first_group
shard_text = Path(first_group["shard_fasta_path"]).read_text()
assert ">hg19|chr11_part1|2158478-2159932" in shard_text, shard_text
assert ">hg19|chr11_part2|2159933-2161387" in shard_text, shard_text
assert ">group" not in shard_text, shard_text

assert group_plan[0]["group_member_count"] == 2, group_plan
assert group_plan[0]["group_member_headers"] == first_group["group_member_headers"], group_plan
assert group_plan[0]["group_member_input_digests"], group_plan
assert group_plan[1]["group_member_count"] == 1, group_plan
PY

mkdir -p "$WORK/errors"
if python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$BIN" \
  --target "$WORK/inputs/testDNA_three_contigs.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/errors/zero/run" \
  --output-mode lite \
  --group-target-records 0 \
  >"$WORK/errors/zero.stdout.log" \
  2>"$WORK/errors/zero.stderr.log"; then
  echo "expected --group-target-records 0 to fail" >&2
  exit 1
fi
grep -q -- "--group-target-records must be >= 1" "$WORK/errors/zero.stderr.log"

echo "ok"
