#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_top5_lowercase_input"}"
SOURCE_DNA="${SOURCE_DNA:-"$ROOT/testDNA.fa"}"
SOURCE_RNA="${SOURCE_RNA:-"$ROOT/H19.fa"}"

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
mkdir -p "$WORK/inputs"

python3 - "$SOURCE_DNA" "$SOURCE_RNA" "$WORK/inputs/target_upper.fa" "$WORK/inputs/rna_upper.fa" "$WORK/inputs/target_lower.fa" "$WORK/inputs/rna_lower.fa" <<'PY'
import sys
from pathlib import Path


def read_fasta(path: Path) -> list[tuple[str, str]]:
    records = []
    header = None
    seq = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(seq)))
            header = line
            seq = []
        elif line.strip():
            seq.append(line.strip())
    if header is not None:
        records.append((header, "".join(seq)))
    if not records:
        raise SystemExit(f"no FASTA records in {path}")
    return records


def write_fasta(path: Path, records: list[tuple[str, str]], *, lower: bool) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for header, sequence in records:
            handle.write(header + "\n")
            normalized = sequence.lower() if lower else sequence.upper()
            for i in range(0, len(normalized), 80):
                handle.write(normalized[i : i + 80] + "\n")


target_records = read_fasta(Path(sys.argv[1]))
rna_records = read_fasta(Path(sys.argv[2]))
write_fasta(Path(sys.argv[3]), target_records, lower=False)
write_fasta(Path(sys.argv[4]), rna_records, lower=False)
write_fasta(Path(sys.argv[5]), target_records, lower=True)
write_fasta(Path(sys.argv[6]), rna_records, lower=True)
PY

run_case() {
  local label="$1"
  local target="$2"
  local rna="$3"
  python3 "$ROOT/scripts/fasim_sharded_runner.py" \
    --fasim-bin "$BIN" \
    --target "$target" \
    --rna "$rna" \
    --rule 0 \
    --work-dir "$WORK/$label" \
    --gasal2-top5-column-pruned-scoreinfo \
    --workers 1 \
    --gpu-ids 0 \
    --force \
    >"$WORK/$label.stdout.log" \
    2>"$WORK/$label.stderr.log"
}

run_case upper "$WORK/inputs/target_upper.fa" "$WORK/inputs/rna_upper.fa"
run_case lower "$WORK/inputs/target_lower.fa" "$WORK/inputs/rna_lower.fa"

python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/upper/report.json"
python3 "$ROOT/scripts/check_topk_summary_digest_integrity.py" \
  --report "$WORK/lower/report.json" \
  --same-payload-as "$WORK/upper/report.json"

python3 - "$WORK/upper/report.json" "$WORK/lower/report.json" <<'PY'
import json
import sys
from pathlib import Path

upper = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
lower = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

for label, report in (("upper", upper), ("lower", lower)):
    assert report["run_status"] == "completed", (label, report)
    assert report["gasal2_top5_column_pruned_scoreinfo"] is True, (label, report)
    assert report["topk_summary_only"] is True, (label, report)
    assert report["shard_output_topk_lite"] == 5, (label, report)
    assert report["fasim_benchmark_shards"] == report["shard_count"], (label, report)
    sums = report["fasim_benchmark_sums"]
    assert sums["fasim_top5_gasal2_gpu_scoreinfo_requested"] == report["shard_count"], (label, sums)
    assert sums["fasim_top5_gasal2_gpu_scoreinfo_active"] == report["shard_count"], (label, sums)
    assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled"] == report["shard_count"], (label, sums)
    assert sums["fasim_gasal2_requests"] > 0, (label, sums)
    assert sums["fasim_gasal2_score_requests"] > 0, (label, sums)
    assert sums["fasim_gasal2_traceback_requests"] > 0, (label, sums)
    assert sums["fasim_gasal2_fallbacks"] == 0, (label, sums)
    assert sums["fasim_gasal2_length_guard_fallbacks"] == 0, (label, sums)
    assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches"] == 0, (label, sums)
    assert sums["fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches"] == 0, (label, sums)

for mode in ("score", "stability", "nt_score"):
    upper_digest = upper["topk_summary"]["modes"][mode]["digest"]
    lower_digest = lower["topk_summary"]["modes"][mode]["digest"]
    assert upper_digest == lower_digest, (mode, upper_digest, lower_digest)
    print(f"{mode}_digest={upper_digest}")

assert upper["topk_rows_payload_digest"] == lower["topk_rows_payload_digest"], (upper, lower)
assert upper["topk_lite_digest"] == lower["topk_lite_digest"], (upper, lower)
assert upper["topk_lite_records"] == lower["topk_lite_records"], (upper, lower)

print("lowercase_topk_summary_match=true")
print("lowercase_topk_artifact_match=true")
PY

echo "ok"
