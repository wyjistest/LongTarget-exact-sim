#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_recommended_runtime.md"
PRODUCT_DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_product_readiness.md"
SCOPED_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
MAKEFILE="$ROOT/Makefile"
RUNNER="$ROOT/scripts/fasim_sharded_runner.py"

for path in "$DOC" "$PRODUCT_DOC" "$SCOPED_DOC" "$MAKEFILE" "$RUNNER"; do
  if [[ ! -s "$path" ]]; then
    echo "missing MALAT1 two-contract recommended-runtime dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$PRODUCT_DOC" "$SCOPED_DOC" "$MAKEFILE" "$RUNNER" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
product = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
scoped = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")
runner = Path(sys.argv[5]).read_text(encoding="utf-8")

required_doc = [
    "recommended runtime for the scoped MALAT1-like two-contract scoreInfo path",
    "default-off opt-in runtime",
    "make build-fasim-gasal2",
    "env -u FASIM_CUDA_DEVICES",
    "python3 scripts/fasim_sharded_runner.py",
    "--fasim-bin ./fasim_longtarget_gasal2",
    "--target MALAT1-DNAseq.fa",
    "--rna MALAT1.fa",
    "--output-mode lite",
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "--workers 1",
    "--manifest run_manifest.json",
    "--output-mode tfosorted",
    "--group-target-records 32",
    "not chunking, overlap, or an in-process multi-GPU runtime",
    "result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1",
    "FASIM_ALIGN_GASAL2=1",
    "probe_positive_numeric_keys = 0",
    "recommended when:",
    "MALAT1-like workload shape",
    "complete-record group32 is acceptable",
    "schema=lite or schema=tfosorted row-set equality is required",
    "external digest gate is available",
    "two_contract_used == tasks",
    "realpath_used == tasks",
    "gpu_minscore_used == tasks",
    "fallback/mismatch counters = 0",
    "MALAT1 first64",
    "MALAT1 first128",
    "MALAT1 first256",
    "MALAT1 full lite",
    "MALAT1 full TFOsorted",
    "not recommended when:",
    "NEAT1 or broad long-query workload",
    "two_contract bridge launch fails",
    "candidate_vs_baseline <= 1.0x on the claimed workload",
    "diagnostic probe env is required for correctness",
    "endpoint/CIGAR/traceback authority is required",
    "direct aligner.Align replacement is required",
    "default production behavior is required",
    "first8 lite candidate_vs_baseline = 0.990695x",
    "first8 tfosorted candidate_vs_baseline = 0.990699x",
    "recommended as default-off opt-in for the checked scope",
    "NEAT1:",
    "no real path",
    "full objective remains open",
    "make check-fasim-gasal2-malat1-two-contract-recommended-runtime",
    "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "make check-fasim-gasal2-scoreinfo-current-state",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("MALAT1 recommended-runtime doc missing phrases: " + ", ".join(missing))

for phrase in (
    "accepted MALAT1-like two-contract product scope",
    "product-readiness candidate",
    "full objective remains open",
):
    if phrase not in product:
        raise SystemExit(f"product-readiness doc missing recommended-runtime phrase: {phrase}")
for phrase in (
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "Full-MALAT1 Milestone Decision",
    "scoped full-MALAT1 no-probe runtime go",
):
    if phrase not in scoped:
        raise SystemExit(f"scoped milestone doc missing recommended-runtime phrase: {phrase}")
for phrase in (
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1",
    "malat1_like_two_contract_runtime_group32_experimental_v1",
):
    if phrase not in runner:
        raise SystemExit(f"runner missing MALAT1 recommended-runtime phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-malat1-two-contract-recommended-runtime:\n"
    r"\tbash \./scripts/check_fasim_gasal2_malat1_two_contract_recommended_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing MALAT1 two-contract recommended-runtime target")
current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-malat1-two-contract-recommended-runtime" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 two-contract recommended-runtime dependency")
if "check-fasim-gasal2-malat1-two-contract-product-readiness" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 two-contract product-readiness dependency")

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
if "check-fasim-gasal2-malat1-two-contract-recommended-runtime" not in set(phony_targets):
    raise SystemExit("MALAT1 recommended-runtime target missing from .PHONY")
PY

echo "ok"
