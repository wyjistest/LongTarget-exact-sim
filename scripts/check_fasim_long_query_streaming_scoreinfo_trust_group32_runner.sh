#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
DOC="$ROOT/docs/fasim_sharded_runner.md"
MAKEFILE="$ROOT/Makefile"
CHARACTERIZE="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner.sh"
GROUP32_SCALING="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_group32_scaling.sh"
FULL_GROUP32="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_malat1_full_group32.sh"

for path in "$RUNNER" "$DOC" "$MAKEFILE" "$CHARACTERIZE" "$GROUP32_SCALING" "$FULL_GROUP32"; do
  if [[ ! -s "$path" ]]; then
    echo "missing group32 trust runner dependency: $path" >&2
    exit 1
  fi
done

python3 - "$RUNNER" "$DOC" "$MAKEFILE" "$CHARACTERIZE" "$GROUP32_SCALING" "$FULL_GROUP32" <<'PY'
import re
import sys
from pathlib import Path

runner = Path(sys.argv[1]).read_text(encoding="utf-8")
doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")
characterize = Path(sys.argv[4]).read_text(encoding="utf-8")
group32_scaling = Path(sys.argv[5]).read_text(encoding="utf-8")
full_group32 = Path(sys.argv[6]).read_text(encoding="utf-8")

required_runner = [
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "long_query_streaming_scoreinfo_gpu_trust_group32",
    "long_query_streaming_scoreinfo_gpu_trust_profile",
    "malat1_like_group32_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
    "--long-query-streaming-scoreinfo-gpu-trust-group32 uses --group-target-records 32",
]
missing = [phrase for phrase in required_runner if phrase not in runner]
if missing:
    raise SystemExit("runner missing group32 trust preset phrases: " + ", ".join(missing))

for phrase in (
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
    "malat1_like_group32_experimental_v1",
    "default-off",
    "external digest gate",
):
    if phrase not in doc:
        raise SystemExit("runner doc missing group32 trust phrase: " + phrase)

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-trust-group32-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-long-query-streaming-scoreinfo-trust-group32-runner target")

phony_targets = []
lines = makefile.splitlines()
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith(".PHONY:"):
        text = line.split(":", 1)[1].strip()
        while text.endswith("\\") and index + 1 < len(lines):
            text = text[:-1] + " " + lines[index + 1].strip()
            index += 1
        phony_targets.extend(text.split())
    index += 1
if not phony_targets:
    raise SystemExit("Makefile missing .PHONY block")
phony_targets = set(phony_targets)
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-runner" not in phony_targets:
    raise SystemExit("group32 trust runner target missing from .PHONY")

for phrase in (
    "TRUST_PRESET",
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_trust_profile",
    "malat1_like_group32_experimental_v1",
):
    if phrase not in characterize:
        raise SystemExit("trust characterization missing group32 preset phrase: " + phrase)

for name, text in (
    ("group32 scaling", group32_scaling),
    ("full MALAT1 group32", full_group32),
):
    for phrase in (
        'TRUST_PRESET="${TRUST_PRESET:-group32}"',
        'GROUP_TARGET_RECORDS_LIST="${GROUP_TARGET_RECORDS_LIST:-32}"',
    ):
        if phrase not in text:
            raise SystemExit(f"{name} wrapper missing preset phrase: {phrase}")
PY

WORK="$(mktemp -d "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_trust_group32_runner.XXXXXX")"
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
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_active=1
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
printf '>t1|chr1|1-4\nACGT\n>t2|chr2|1-4\nACGT\n>t3|chr3|1-4\nACGT\n' >"$target"
printf '>rna\nACGT\n' >"$rna"
report="$WORK/report.json"
manifest="$WORK/run_manifest.json"

python3 "$RUNNER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/run" \
  --manifest "$manifest" \
  --long-query-streaming-scoreinfo-gpu-trust-group32 \
  >"$report"

python3 - "$report" "$manifest" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
expected_env = {
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE": "1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST": "1",
}
for payload_name, payload in (("report", report), ("manifest", manifest)):
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1":
        raise SystemExit(f"{payload_name} result_contract mismatch: {payload['result_contract']}")
    if payload["group_target_records"] != 32:
        raise SystemExit(f"{payload_name} did not record group_target_records=32")
    if payload["long_query_streaming_scoreinfo_gpu_trust"] is not True:
        raise SystemExit(f"{payload_name} trust flag not true")
    if payload["long_query_streaming_scoreinfo_gpu_trust_group32"] is not True:
        raise SystemExit(f"{payload_name} group32 trust flag not true")
    if payload["long_query_streaming_scoreinfo_gpu_trust_profile"] != "malat1_like_group32_experimental_v1":
        raise SystemExit(f"{payload_name} trust profile mismatch")
    if payload["long_query_streaming_scoreinfo_gpu_trust_decision"] != "experimental_external_digest_gate":
        raise SystemExit(f"{payload_name} trust decision mismatch")
    env = payload["env_overrides"] if payload_name == "report" else payload["env_snapshot"]
    for key, value in expected_env.items():
        if env.get(key) != value:
            raise SystemExit(f"{payload_name} missing {key}={value}")

if report["shard_count"] != 1:
    raise SystemExit(f"expected grouped fake input to produce one shard, got {report['shard_count']}")
PY

set +e
python3 "$RUNNER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/conflict" \
  --long-query-streaming-scoreinfo-gpu-trust-group32 \
  --group-target-records 16 \
  >"$WORK/conflict.stdout" 2>"$WORK/conflict.stderr"
status="$?"
set -e
if [[ "$status" == "0" ]]; then
  echo "expected group32 preset to reject --group-target-records 16" >&2
  exit 1
fi
grep -q -- "--long-query-streaming-scoreinfo-gpu-trust-group32 uses --group-target-records 32" "$WORK/conflict.stderr"

echo "ok"
