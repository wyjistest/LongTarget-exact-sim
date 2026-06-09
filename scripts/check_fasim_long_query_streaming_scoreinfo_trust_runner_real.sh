#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_trust_runner_real"}"
BUILD_BIN="${BUILD_BIN:-1}"
RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
RNA_INPUT="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
DNA_INPUT="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing MALAT1 inputs" >&2
  exit 1
fi

sample="$WORK/inputs/malat1_first${RECORD_LIMIT}.fa"
awk -v limit="$RECORD_LIMIT" '
  /^>/ { ++records }
  records <= limit { print }
' "$DNA_INPUT" >"$sample"

if [[ ! -s "$sample" ]]; then
  echo "empty MALAT1 sample" >&2
  exit 1
fi

run_runner() {
  local label="$1"
  shift
  python3 "$RUNNER" \
    --fasim-bin "$BIN" \
    --target "$sample" \
    --rna "$RNA_INPUT" \
    --rule 0 \
    --work-dir "$WORK/$label" \
    --manifest "$WORK/$label/run_manifest.json" \
    --workers 1 \
    "$@" \
    >"$WORK/$label.report.json"
}

run_runner baseline
run_runner candidate --long-query-streaming-scoreinfo-gpu-trust

python3 - "$WORK/baseline.report.json" "$WORK/candidate.report.json" <<'PY'
import json
import sys
from pathlib import Path

baseline = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

if baseline["merged_digest"] != candidate["merged_digest"]:
    raise SystemExit(
        "runner trust preset changed merged digest: "
        f"baseline={baseline['merged_digest']} candidate={candidate['merged_digest']}"
    )
if candidate["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_experimental_v1":
    raise SystemExit(f"unexpected trust result contract: {candidate['result_contract']}")
if candidate["long_query_streaming_scoreinfo_gpu_trust"] is not True:
    raise SystemExit("candidate did not record trust flag")
if candidate["long_query_streaming_scoreinfo_gpu_trust_decision"] != "experimental_external_digest_gate":
    raise SystemExit("candidate did not record external digest gate decision")
if baseline["result_contract"] == candidate["result_contract"]:
    raise SystemExit("baseline and candidate must have different result contracts")

bench = candidate["fasim_benchmark_sums"]
shard_count = candidate["shard_count"]
expected = {
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_requested": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_active": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_unsupported": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust": shard_count,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds": 0,
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds": 0,
}
for key, expected_value in expected.items():
    actual = bench.get(key)
    if actual != expected_value:
        raise SystemExit(f"unexpected {key}: {actual} expected {expected_value}")

tasks = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks", 0)
realpath_used = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used", 0)
gpu_minscore_used = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used", 0)
gpu_groups = bench.get("fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups", 0)
if not isinstance(tasks, int) or tasks <= 0:
    raise SystemExit(f"expected positive tasks, got {tasks}")
if realpath_used != tasks:
    raise SystemExit(f"realpath_used != tasks: {realpath_used} vs {tasks}")
if gpu_minscore_used != tasks:
    raise SystemExit(f"gpu_minscore_used != tasks: {gpu_minscore_used} vs {tasks}")
if not isinstance(gpu_groups, int) or gpu_groups <= 0:
    raise SystemExit(f"expected positive GPU scoreInfo groups, got {gpu_groups}")

authority = None
for shard in candidate["per_shard"]:
    stderr = Path(shard["run"]["stderr_path"]).read_text(encoding="utf-8", errors="replace")
    for line in stderr.splitlines():
        if line.startswith("benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority="):
            authority = line.split("=", 1)[1]
if authority != "external_digest_gate":
    raise SystemExit(f"unexpected realpath digest authority: {authority}")

print("digest=" + candidate["merged_digest"])
print("tasks=" + str(tasks))
print("realpath_used=" + str(realpath_used))
print("gpu_scoreinfo_groups=" + str(gpu_groups))
print("ok")
PY
