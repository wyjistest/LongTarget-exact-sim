#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_product_readiness.md"
RECOMMENDED_DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_recommended_runtime.md"
SCOPED_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
ROLLUP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone_rollup.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$RECOMMENDED_DOC" "$SCOPED_DOC" "$ROLLUP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing MALAT1 two-contract product-readiness dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$RECOMMENDED_DOC" "$SCOPED_DOC" "$ROLLUP_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
recommended = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
scoped = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
rollup = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "MALAT1-like product-readiness gate",
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "default-off opt-in",
    "external digest gate required",
    "no diagnostic probe env leakage",
    "schema=lite",
    "schema=tfosorted",
    "result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1",
    "long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1",
    "CPU-output authority path",
    "GPU endpoint, CIGAR, traceback, final output, and digest authority remain forbidden",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted",
    "rows = 98,713",
    "digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b",
    "baseline_wall_seconds = 2611.940621",
    "candidate_wall_seconds = 2514.945686",
    "candidate_vs_baseline = 1.038567x",
    "digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc",
    "baseline_wall_seconds = 2636.136998",
    "candidate_wall_seconds = 2537.678266",
    "candidate_vs_baseline = 1.038799x",
    "two_contract_used = 200,400",
    "realpath_used = 200,400",
    "gpu_minscore_used = 200,400",
    "gpu_scoreinfo_groups = 3,561,123",
    "probe_positive_numeric_keys = 0",
    "first64:",
    "digest = f57a418be0ec9439cf2c4c453e2e45cc9d35b03df5e2c63f60860e6575db180d",
    "candidate_vs_baseline = 1.029812x",
    "first128:",
    "digest = 91ea0b8191027916e3237fb5381c6271fc9acd03b46a5cf67826c253fe41edd1",
    "candidate_vs_baseline = 1.041215x",
    "first256:",
    "digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e",
    "candidate_vs_baseline = 1.040931x",
    "first8 lite:",
    "candidate_vs_baseline = 0.990695x",
    "first8 tfosorted:",
    "candidate_vs_baseline = 0.990699x",
    "workload-shape dependent",
    "accepted MALAT1-like two-contract product scope",
    "require two_contract_used == tasks",
    "require realpath_used == tasks",
    "require gpu_minscore_used == tasks",
    "require fallback/mismatch counters = 0",
    "require probe_positive_numeric_keys = 0",
    "require full row-set equality for the claimed schema",
    "MALAT1-like group32 lite:",
    "product-readiness candidate",
    "MALAT1-like group32 TFOsorted:",
    "first8 tiny sample:",
    "correctness smoke only, not performance evidence",
    "NEAT1:",
    "no broad real path",
    "full objective remains open",
    "not universal scoreInfo/preAlign replacement",
    "not full aligner.Align replacement",
    "not GPU endpoint authority",
    "not GPU CIGAR authority",
    "not GPU traceback authority",
    "not NEAT1 broad long-query real path",
    "not default production path",
    "make check-fasim-gasal2-malat1-two-contract-product-readiness",
    "make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("MALAT1 product-readiness doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("recommended runtime", recommended),
    ("scoped milestone", scoped),
    ("rollup", rollup),
    ("full goal", full_goal),
):
    for phrase in (
        "MALAT1-like",
        "two-contract",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing MALAT1 product-readiness phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-malat1-two-contract-product-readiness:\n"
    r"\tbash \./scripts/check_fasim_gasal2_malat1_two_contract_product_readiness\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing MALAT1 two-contract product-readiness target")

for dep in (
    "check-fasim-gasal2-malat1-two-contract-product-readiness",
    "check-fasim-gasal2-malat1-two-contract-recommended-runtime",
):
    current_target = re.search(
        r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
        makefile,
        flags=re.MULTILINE,
    )
    if not current_target or dep not in current_target.group("deps").split():
        raise SystemExit(f"current-state target missing dependency: {dep}")

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
if "check-fasim-gasal2-malat1-two-contract-product-readiness" not in set(phony_targets):
    raise SystemExit("MALAT1 product-readiness target missing from .PHONY")
PY

echo "ok"
