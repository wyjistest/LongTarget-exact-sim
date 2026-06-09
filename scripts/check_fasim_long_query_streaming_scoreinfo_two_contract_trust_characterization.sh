#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_two_contract_trust_characterization.md"
SCRIPT="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_two_contract_trust.sh"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$SCRIPT" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing two-contract trust characterization dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$SCRIPT" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
script = Path(sys.argv[2]).read_text(encoding="utf-8")
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_doc = [
    "Fasim Long-Query Streaming ScoreInfo Two-Contract Trust Characterization",
    "GASAL2 / GPU scoreInfo scoped feasibility checkpoint",
    "not completion of the full scoreInfo/preAlign GPU/GASAL2 objective",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1",
    "malat1_like_two_contract_group32_experimental_v1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1",
    "CPU output digest remains the external authority",
    "GPU endpoint/CIGAR/traceback authority remains forbidden",
    "score_mismatches = 0",
    "min_score_mismatches = 0",
    "scoreinfo_mismatches = 0",
    "realpath_fallbacks = 0",
    "cpu_scoreinfo_groups = 0",
    "cpu_prealign_seconds = 0",
    "MALAT1 first8",
    "tasks = 1,824",
    "candidate_vs_baseline = 0.92x",
    "gpu_minscore_hot = 8/8 shards",
    "minscore_seconds ~= 0",
    "NEAT1 first64",
    "two_contract_bridge_launch_failed",
    "two_contract_active = 0/64 shards",
    "64/64 fallback",
    "invalid argument",
    "MALAT1 first64",
    "tasks = 18,096",
    "gpu_scoreinfo_groups = 319,280",
    "candidate_vs_baseline = 0.95x",
    "MALAT1 first64 group32",
    "grouped_shard_count = 2",
    "gpu_minscore_hot = 2/2 shards",
    "candidate_vs_baseline = 1.03x",
    "MALAT1 full",
    "MALAT1 full group32",
    "grouped_shard_count = 21",
    "tasks = 200,400",
    "two_contract_used = 200,400",
    "gpu_scoreinfo_groups = 3,561,123",
    "gpu_minscore_hot = 21/21 shards",
    "two_contract_total_seconds = 483.9203s",
    "candidate_vs_baseline = 1.037881x",
    "f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b",
    "candidate_vs_baseline",
    "make characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust",
    "TWO_CONTRACT_CASES=\"MALAT1:64 NEAT1:64\"",
    "TWO_CONTRACT_CASES=\"MALAT1:670\"",
    "TWO_CONTRACT_TRUST_PRESET=group32",
    "decision = two_contract_trust_characterization_gate",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit(
        "two-contract trust characterization doc missing phrases: "
        + ", ".join(missing)
    )

for forbidden in (
    "full objective complete",
    "production replacement",
    "default-on",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
):
    if forbidden in doc:
        raise SystemExit(f"doc contains forbidden phrase: {forbidden}")

required_script = [
    "TWO_CONTRACT_CASES",
    "TWO_CONTRACT_TRUST_PRESET",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot",
    "fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds",
    "two_contract_bridge_launch_failed",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1",
    "malat1_like_two_contract_group32_experimental_v1",
]
missing_script = [phrase for phrase in required_script if phrase not in script]
if missing_script:
    raise SystemExit(
        "two-contract trust characterization script missing phrases: "
        + ", ".join(missing_script)
    )

char_target = re.search(
    r"^characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_long_query_streaming_scoreinfo_two_contract_trust\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not char_target:
    raise SystemExit("Makefile missing two-contract trust characterization target")

check_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-trust-characterization:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_trust_characterization\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not check_target:
    raise SystemExit("Makefile missing two-contract trust characterization check target")
PY

echo "ok"
