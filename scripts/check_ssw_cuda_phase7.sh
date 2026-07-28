#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---preflight}"
V1_PLAN_SHA256="49e4f5984fdfa32ed38f169f033deb1016027e440860c5855c5130decbf04038"
PLAN_SHA256="fb86f5539dd55d4f553edb6598de881626d70ef4913ea9ce8e0ccce4a4b0a4f1"
CONTINUATION_DRIVER="${SSW_CUDA_PHASE7_CONTINUATION_DRIVER:-$ROOT/.paper-artifacts/ssw-cuda-v1/forward-hybrid/build/ssw_cpu_continuation_driver}"
F_BINARY="${SSW_CUDA_PHASE7_FASIM_BIN:-$ROOT/.paper-artifacts/ssw-cuda-v1/forward-hybrid/build/fasim_forward_hybrid}"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--preflight|--final]" >&2
  exit 2
fi

required=(
  Makefile
  goal-ssw.md
  docs/ssw_cuda/DP_CONTRACT.md
  docs/ssw_cuda/ENDPOINT_CONTRACT.md
  docs/ssw_cuda/TELEMETRY_SPEC.md
  fasim/Fasim-LongTarget.cpp
  fasim/fastsim.h
  fasim/ssw.h
  fasim/sswNew.cpp
  fasim/ssw_cpp.cpp
  fasim/ssw_cpp.h
  fasim/ssw_cuda/ssw_cuda_forward_hybrid.cpp
  fasim/ssw_cuda/ssw_cuda_forward_hybrid.h
  paper/ssw_cuda/PROGRAM_STATE.json
  paper/ssw_cuda/STATUS.md
  paper/ssw_cuda/forward_hybrid_attempt_plan.tsv
  paper/ssw_cuda/forward_hybrid_attempt_plan_v2.tsv
  paper/ssw_cuda/forward_hybrid_analysis_correction_v1.json
  paper/ssw_cuda/forward_hybrid_analysis_correction_v1.md
  paper/ssw_cuda/forward_hybrid_measurement_repair_v1.json
  paper/ssw_cuda/forward_hybrid_measurement_repair_v1.md
  paper/ssw_cuda/forward_hybrid_measurement_repair_v2.json
  paper/ssw_cuda/forward_hybrid_measurement_repair_v2.md
  paper/ssw_cuda/forward_hybrid_protocol.md
  reproduce/ssw_cuda/run_forward_hybrid.py
  scripts/compare_fasim_lite_offline_cluster_topk.py
  scripts/check_ssw_cuda_phase5.sh
  scripts/check_ssw_cuda_phase6.sh
  scripts/check_ssw_cuda_phase7.sh
  tests/ssw_cuda/ssw_cpu_continuation_driver.cpp
  tests/ssw_cuda/test_cpu_continuation.py
  tests/ssw_cuda/test_forward_hybrid_runner.py
  tests/ssw_cuda/test_forward_hybrid_runtime.py
)
for relative in "${required[@]}"; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 7 dependency: $relative" >&2
    exit 1
  fi
done

observed_v1_plan_sha256="$(sha256sum "$ROOT/paper/ssw_cuda/forward_hybrid_attempt_plan.tsv" | awk '{print $1}')"
if [[ "$observed_v1_plan_sha256" != "$V1_PLAN_SHA256" ]]; then
  echo "Phase 7 v1 attempt plan digest drift: $observed_v1_plan_sha256" >&2
  exit 1
fi
observed_plan_sha256="$(sha256sum "$ROOT/paper/ssw_cuda/forward_hybrid_attempt_plan_v2.tsv" | awk '{print $1}')"
if [[ "$observed_plan_sha256" != "$PLAN_SHA256" ]]; then
  echo "Phase 7 attempt plan digest drift: $observed_plan_sha256" >&2
  exit 1
fi
observed_comparator_sha256="$(sha256sum "$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py" | awk '{print $1}')"
if [[ "$observed_comparator_sha256" != "2765d76b6c8e742596b1072a413309a88ef415f3576c9de62be67213ee76dc80" ]]; then
  echo "Phase 7 comparator digest drift: $observed_comparator_sha256" >&2
  exit 1
fi

make -C "$ROOT" \
  build-fasim \
  build-ssw-cuda-phase7-continuation-driver \
  build-ssw-cuda-phase7-fasim

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/run_forward_hybrid.py" \
  "$ROOT/tests/ssw_cuda/test_cpu_continuation.py" \
  "$ROOT/tests/ssw_cuda/test_forward_hybrid_runner.py" \
  "$ROOT/tests/ssw_cuda/test_forward_hybrid_runtime.py"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/reproduce/ssw_cuda/run_forward_hybrid.py" --check-plan
SSW_CUDA_PHASE7_CONTINUATION_DRIVER="$CONTINUATION_DRIVER" \
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_cpu_continuation.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_forward_hybrid_runner.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_forward_hybrid_runtime.py"

bash "$ROOT/scripts/check_ssw_cuda_phase5.sh" --final
bash "$ROOT/scripts/check_ssw_cuda_phase6.sh" --final

python3 - "$ROOT" "$MODE" "$PLAN_SHA256" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
plan_sha256 = sys.argv[3]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")
protocol = (root / "paper/ssw_cuda/forward_hybrid_protocol.md").read_text(encoding="utf-8")
repair_protocol = (
    root / "paper/ssw_cuda/forward_hybrid_measurement_repair_v1.md"
).read_text(encoding="utf-8")
repair_receipt = json.loads(
    (root / "paper/ssw_cuda/forward_hybrid_measurement_repair_v1.json").read_text(
        encoding="utf-8"
    )
)
repair2_protocol = (
    root / "paper/ssw_cuda/forward_hybrid_measurement_repair_v2.md"
).read_text(encoding="utf-8")
repair2_receipt = json.loads(
    (root / "paper/ssw_cuda/forward_hybrid_measurement_repair_v2.json").read_text(
        encoding="utf-8"
    )
)
analysis_correction_protocol = (
    root / "paper/ssw_cuda/forward_hybrid_analysis_correction_v1.md"
).read_text(encoding="utf-8")
analysis_correction = json.loads(
    (root / "paper/ssw_cuda/forward_hybrid_analysis_correction_v1.json").read_text(
        encoding="utf-8"
    )
)

if mode == "--preflight":
    if (
        state["active_phase"] != 7
        or state["phase_status"]["6"] != "pass"
        or state["phase_status"]["7"] != "in_progress"
    ):
        raise SystemExit("Phase 7 preflight requires the frozen in-progress state")
    required_goal = (
        "active_phase = 7",
        "phase_6_status = pass",
        "phase_7_status = in_progress",
        "bioinformatics_b3_track = closed_amdahl",
    )
else:
    decision = json.loads(
        (root / "paper/ssw_cuda/forward_hybrid_decision.json").read_text(encoding="utf-8")
    )
    if decision["phase7_status"] == "pass":
        if (
            state["active_phase"] != 8
            or state["phase_status"]["7"] != "pass"
            or state["phase_status"]["8"] != "in_progress"
        ):
            raise SystemExit("passed Phase 7 did not advance to Phase 8")
    elif decision["phase7_status"] == "blocked":
        if state["active_phase"] != 7 or state["phase_status"]["7"] != "blocked":
            raise SystemExit("blocked Phase 7 state drift")
    else:
        if state["phase_status"]["7"] != "no_go":
            raise SystemExit("Phase 7 no-go state drift")
    required_goal = (
        f"active_phase = {state['active_phase']}",
        f"phase_7_status = {state['phase_status']['7']}",
        f"last_decision = {decision['decision']}",
        "bioinformatics_b3_track = closed_amdahl",
    )

for phrase in required_goal:
    if phrase not in goal:
        raise SystemExit(f"goal-ssw Phase 7 state drift: {phrase}")
for phrase in (
    f"active_phase = {state['active_phase']}",
    f"phase_7_status = {state['phase_status']['7']}",
    "bioinformatics_b3_track = closed_amdahl",
    "l8_contract_status = diagnostic_only",
):
    if phrase not in status:
        raise SystemExit(f"SSW-CUDA status drift: {phrase}")
for phrase in (
    "49e4f5984fdfa32ed38f169f033deb1016027e440860c5855c5130decbf04038",
    "total new F processes                                             = 49",
    "new A processes                                                    = 0",
    "new H2 processes                                                   = 0",
    "Full-output equality is reported only as L8 diagnostic evidence",
    "50 x 668 application panel",
):
    if phrase not in protocol:
        raise SystemExit(f"Phase 7 protocol drift: {phrase}")
for phrase in (
    plan_sha256,
    "completed receipts  = 25/49",
    "replacement retries = 0",
    "repair count     = 1 of at most 2",
):
    if phrase not in repair_protocol:
        raise SystemExit(f"Phase 7 repair protocol drift: {phrase}")
if (
    repair_receipt["repair_number"] != 1
    or repair_receipt["v1_status"] != "incomplete"
    or repair_receipt["v1_completed_attempt_receipts"] != 25
    or repair_receipt["v1_replacement_retries"] != 0
    or repair_receipt["v2_plan_sha256"] != plan_sha256
):
    raise SystemExit("Phase 7 repair receipt drift")
for phrase in (
    "repair 2 of the maximum 2",
    "forward_hybrid_implementation_contract_failure",
    "It authorizes zero new",
):
    if phrase not in repair2_protocol:
        raise SystemExit(f"Phase 7 repair 2 protocol drift: {phrase}")
if (
    repair2_receipt["repair_number"] != 2
    or repair2_receipt["classification"] != "implementation_contract_no_go"
    or repair2_receipt["failing_attempt_cpu_failures"] != 1
    or repair2_receipt["failing_attempt_timed_out"] is not False
    or repair2_receipt["phase7_status"] != "no_go"
    or repair2_receipt["phase8_engineering_authorized"] is not False
    or repair2_receipt["new_attempts_authorized"] != 0
):
    raise SystemExit("Phase 7 repair 2 receipt drift")
for phrase in (
    "basename ends in `-TFOsorted`",
    "launches zero backend attempts",
    "execution/measurement repairs unchanged",
):
    if phrase not in analysis_correction_protocol:
        raise SystemExit(f"Phase 7 analysis correction drift: {phrase}")
if (
    analysis_correction["correction_number"] != 1
    or analysis_correction["new_backend_attempts"] != 0
    or analysis_correction["measurement_repairs_used"] != 2
    or analysis_correction["scientific_contract_changed"] is not False
):
    raise SystemExit("Phase 7 analysis correction receipt drift")

def git_file(commit, relative):
    return subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout

def function_body(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise SystemExit(f"unterminated function: {marker}")

phase6_commit = state["phase6_implementation_commit"]
guards = (
    ("fasim/sswNew.cpp", "s_align* ssw_align("),
    ("fasim/ssw_cpp.cpp", "bool Aligner::Align("),
)
for relative, marker in guards:
    frozen = function_body(git_file(phase6_commit, relative), marker)
    current = function_body((root / relative).read_text(encoding="utf-8"), marker)
    if hashlib.sha256(frozen.encode()).digest() != hashlib.sha256(current.encode()).digest():
        raise SystemExit(f"frozen authority body drift: {relative}:{marker}")

ssw = (root / "fasim/sswNew.cpp").read_text(encoding="utf-8")
wrapper = (root / "fasim/ssw_cpp.cpp").read_text(encoding="utf-8")
for source, symbol in ((ssw, "ssw_align_from_forward"), (wrapper, "AlignFromForward")):
    symbol_at = source.index(symbol)
    guard_at = source.rfind("#ifdef FASIM_WITH_SSW_CUDA_FORWARD_HYBRID", 0, symbol_at)
    endif_at = source.find("#endif", symbol_at)
    if guard_at < 0 or endif_at < 0:
        raise SystemExit(f"candidate-only continuation guard missing: {symbol}")

production = "\n".join(
    (root / relative).read_text(encoding="utf-8")
    for relative in (
        "fasim/ssw_cuda/ssw_cuda_forward_hybrid.cpp",
        "fasim/fastsim.h",
    )
)
for forbidden in ("FAM230I", "PXN-AS1", "allowlist", "blacklist"):
    if forbidden in production:
        raise SystemExit(f"case specialization token in Phase 7 production: {forbidden}")

makefile = (root / "Makefile").read_text(encoding="utf-8")
sources_line = next(line for line in makefile.splitlines() if line.startswith("FASIM_SOURCES :="))
if "ssw_cuda" in sources_line:
    raise SystemExit("default Fasim sources unexpectedly link SSW-CUDA")
PY

if nm -C "$ROOT/fasim_longtarget_x86" | grep -E 'AlignFromForward|ssw_align_from_forward' >/dev/null; then
  echo "default CPU binary unexpectedly contains Phase 7 continuation symbols" >&2
  exit 1
fi
if ! nm -C "$F_BINARY" | grep 'StripedSmithWaterman::Aligner::AlignFromForward' >/dev/null; then
  echo "Phase 7 binary is missing the continuation wrapper" >&2
  exit 1
fi
if ! nm -C "$F_BINARY" | grep 'ssw_align_from_forward' >/dev/null; then
  echo "Phase 7 binary is missing the continuation core" >&2
  exit 1
fi

if [[ "$MODE" == "--final" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 \
    "$ROOT/reproduce/ssw_cuda/run_forward_hybrid.py" --check-results
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 7 $MODE checks OK"
