#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
RUNNER_DOC="$ROOT/docs/fasim_sharded_runner.md"
MAKEFILE="$ROOT/Makefile"

for path in "$RUNNER" "$RUNNER_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing two-contract runner dependency: $path" >&2
    exit 1
  fi
done

python3 - "$RUNNER" "$RUNNER_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

runner = Path(sys.argv[1]).read_text(encoding="utf-8")
runner_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_runner = [
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1",
    "malat1_like_two_contract_group32_experimental_v1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --long-query-streaming-scoreinfo-gpu-trust",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32 uses --group-target-records 32",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --gasal2-top5-column-pruned-scoreinfo",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust requires a GASAL2-enabled Fasim binary",
]
missing = [phrase for phrase in required_runner if phrase not in runner]
if missing:
    raise SystemExit("runner missing two-contract trust phrases: " + ", ".join(missing))

required_doc = [
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1",
    "malat1_like_two_contract_group32_experimental_v1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1",
    "external-digest-gated",
    "not a default replacement path",
]
missing_doc = [phrase for phrase in required_doc if phrase not in runner_doc]
if missing_doc:
    raise SystemExit("runner doc missing two-contract trust phrases: " + ", ".join(missing_doc))

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing two-contract bridge runner target")
PY

WORK="$(mktemp -d "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_runner.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

fake_bin="$WORK/fake_fasim_gasal2"
cat >"$fake_bin" <<'SH'
#!/usr/bin/env bash
# benchmark.fasim_gasal2_built=1
set -euo pipefail
out=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -O)
      out="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -z "$out" ]]; then
  echo "missing -O" >&2
  exit 2
fi
mkdir -p "$out"
cat >"$out/fake-TFOsorted.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr1	1	4	+	0	1	4	1	4	parallel	4	4	100	1
EOF
cat >&2 <<'EOF'
benchmark.fasim_gasal2_built=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority=external_digest_gate
EOF
SH
chmod +x "$fake_bin"

target="$WORK/target.fa"
rna="$WORK/rna.fa"
printf '>t|chr1|1-4\nACGT\n' >"$target"
printf '>rna\nACGT\n' >"$rna"
report="$WORK/report.json"
manifest="$WORK/run_manifest.json"

python3 "$RUNNER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/run" \
  --manifest "$manifest" \
  --long-query-streaming-scoreinfo-gpu-two-contract-trust \
  >"$report"

python3 - "$report" "$manifest" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
expected_env = {
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
}
for payload_name, payload in (("report", report), ("manifest", manifest)):
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1":
        raise SystemExit(f"{payload_name} result_contract mismatch: {payload['result_contract']}")
    if payload["long_query_streaming_scoreinfo_gpu_two_contract_trust"] is not True:
        raise SystemExit(f"{payload_name} two-contract trust flag not true")
    if payload["long_query_streaming_scoreinfo_gpu_trust"] is not False:
        raise SystemExit(f"{payload_name} legacy trust flag must be false")
    env = payload["env_overrides"] if payload_name == "report" else payload["env_snapshot"]
    for key, value in expected_env.items():
        if env.get(key) != value:
            raise SystemExit(f"{payload_name} missing {key}={value}")
    for forbidden in (
        "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE",
        "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST",
        "FASIM_TOP5_GASAL2_GPU_SCOREINFO",
    ):
        if forbidden in env:
            raise SystemExit(f"{payload_name} unexpectedly set {forbidden}")
PY

if python3 "$RUNNER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/conflict" \
  --long-query-streaming-scoreinfo-gpu-trust \
  --long-query-streaming-scoreinfo-gpu-two-contract-trust \
  >"$WORK/conflict.json" 2>"$WORK/conflict.stderr"; then
  echo "expected two-contract trust conflict to fail" >&2
  exit 1
fi
grep -q -- "--long-query-streaming-scoreinfo-gpu-two-contract-trust cannot be combined with --long-query-streaming-scoreinfo-gpu-trust" "$WORK/conflict.stderr"

group32_report="$WORK/group32.report.json"
group32_manifest="$WORK/group32_manifest.json"
python3 "$RUNNER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/group32-run" \
  --manifest "$group32_manifest" \
  --long-query-streaming-scoreinfo-gpu-two-contract-trust-group32 \
  >"$group32_report"

python3 - "$group32_report" "$group32_manifest" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
for payload_name, payload in (("report", report), ("manifest", manifest)):
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1":
        raise SystemExit(f"{payload_name} group32 result_contract mismatch: {payload['result_contract']}")
    if payload["group_target_records"] != 32:
        raise SystemExit(f"{payload_name} did not record group_target_records=32")
    if payload["long_query_streaming_scoreinfo_gpu_two_contract_trust"] is not True:
        raise SystemExit(f"{payload_name} two-contract trust flag not true")
    if payload["long_query_streaming_scoreinfo_gpu_two_contract_trust_group32"] is not True:
        raise SystemExit(f"{payload_name} two-contract group32 flag not true")
    if payload["long_query_streaming_scoreinfo_gpu_trust"] is not False:
        raise SystemExit(f"{payload_name} legacy trust flag must be false")
    if payload["long_query_streaming_scoreinfo_gpu_trust_group32"] is not False:
        raise SystemExit(f"{payload_name} legacy trust group32 flag must be false")
    if payload["long_query_streaming_scoreinfo_gpu_trust_profile"] != "malat1_like_two_contract_group32_experimental_v1":
        raise SystemExit(f"{payload_name} two-contract group32 profile mismatch")
    if payload["long_query_streaming_scoreinfo_gpu_trust_decision"] != "experimental_external_digest_gate":
        raise SystemExit(f"{payload_name} trust decision mismatch")

if report["shard_count"] != 1:
    raise SystemExit(f"expected grouped fake input to produce one shard, got {report['shard_count']}")
PY

if python3 "$RUNNER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/group32-conflict" \
  --long-query-streaming-scoreinfo-gpu-two-contract-trust-group32 \
  --group-target-records 16 \
  >"$WORK/group32-conflict.json" 2>"$WORK/group32-conflict.stderr"; then
  echo "expected two-contract group32 preset conflict to fail" >&2
  exit 1
fi
grep -q -- "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32 uses --group-target-records 32" "$WORK/group32-conflict.stderr"

echo "ok"
