#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"
DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
RUNNER_DOC="$ROOT/docs/fasim_sharded_runner.md"
MAKEFILE="$ROOT/Makefile"

for path in "$RUNNER" "$DOC" "$RUNNER_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing long-query trust runner dependency: $path" >&2
    exit 1
  fi
done

python3 - "$RUNNER" "$DOC" "$RUNNER_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

runner = Path(sys.argv[1]).read_text(encoding="utf-8")
doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
runner_doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

required_runner = [
    "--long-query-streaming-scoreinfo-gpu-trust",
    "long_query_streaming_scoreinfo_gpu_trust",
    "long_query_streaming_scoreinfo_gpu_trust_experimental_v1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST",
    "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --gasal2-top5-column-pruned-scoreinfo",
    "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --validate-single",
    "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --keep-going",
    "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --fasim-arg",
    "--long-query-streaming-scoreinfo-gpu-trust cannot be combined with --env for:",
    "--long-query-streaming-scoreinfo-gpu-trust requires a GASAL2-enabled Fasim binary",
    "long_query_streaming_scoreinfo_gpu_trust",
    "long_query_streaming_scoreinfo_gpu_trust_decision",
]
missing = [phrase for phrase in required_runner if phrase not in runner]
if missing:
    raise SystemExit("runner missing long-query trust phrases: " + ", ".join(missing))

if "args.long_query_streaming_scoreinfo_gpu_trust" not in runner:
    raise SystemExit("runner does not branch on args.long_query_streaming_scoreinfo_gpu_trust")
if "or args.long_query_streaming_scoreinfo_gpu_trust" not in runner:
    raise SystemExit("GASAL2-enabled binary requirement must include long-query trust option")

env_keys = [
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST",
]
for key in env_keys:
    pattern = rf'"{re.escape(key)}": "1"'
    if not re.search(pattern, runner):
        raise SystemExit(f"runner must set {key}=1 for trust preset")

for forbidden_pair in (
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO",
    "FASIM_OUTPUT_TOPK_LITE",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU",
):
    trust_block = re.search(
        r"long_query_trust_env = \{(?P<body>.*?)\n\s*\}",
        runner,
        flags=re.S,
    )
    if not trust_block:
        raise SystemExit("runner missing long_query_trust_env block")
    if forbidden_pair in trust_block.group("body"):
        raise SystemExit(f"trust preset must not set top5/exact env {forbidden_pair}")

required_doc = [
    "--long-query-streaming-scoreinfo-gpu-trust",
    "long_query_streaming_scoreinfo_gpu_trust_experimental_v1",
    "MALAT1 streaming scoreInfo trust path: scoped go",
    "NEAT1 streaming scoreInfo trust path: performance no-go",
    "Broad scoreInfo/preAlign replacement: not proven",
    "default-off",
    "experimental",
    "external digest gate",
]
for name, text in (("milestone", doc), ("runner-doc", runner_doc)):
    missing_doc = [phrase for phrase in required_doc if phrase not in text]
    if missing_doc:
        raise SystemExit(f"{name} missing trust runner phrases: " + ", ".join(missing_doc))

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-trust-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_trust_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-long-query-streaming-scoreinfo-trust-runner target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-trust-runner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing trust runner dependency")

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
if "check-fasim-long-query-streaming-scoreinfo-trust-runner" not in phony_targets:
    raise SystemExit("trust runner target missing from .PHONY")
PY

WORK="$(mktemp -d "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_trust_runner.XXXXXX")"
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
  --long-query-streaming-scoreinfo-gpu-trust \
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
    if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_experimental_v1":
        raise SystemExit(f"{payload_name} result_contract mismatch: {payload['result_contract']}")
    if payload["long_query_streaming_scoreinfo_gpu_trust"] is not True:
        raise SystemExit(f"{payload_name} trust flag not true")
    if payload["long_query_streaming_scoreinfo_gpu_trust_decision"] != "experimental_external_digest_gate":
        raise SystemExit(f"{payload_name} trust decision mismatch")
    env = payload["env_overrides"] if payload_name == "report" else payload["env_snapshot"]
    for key, value in expected_env.items():
        if env.get(key) != value:
            raise SystemExit(f"{payload_name} missing {key}={value}")
    for forbidden in (
        "FASIM_TOP5_GASAL2_GPU_SCOREINFO",
        "FASIM_OUTPUT_TOPK_LITE",
        "FASIM_EXACT_COLUMN_SCOREINFO_GPU",
    ):
        if forbidden in env:
            raise SystemExit(f"{payload_name} unexpectedly set {forbidden}")
PY

echo "ok"
