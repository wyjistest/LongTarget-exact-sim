#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke"}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

awk '
  /^>/ { ++records }
  records <= 1 { print }
' "$DNA_INPUT" >"$WORK/inputs/neat1_first1.fa"

run_case() {
  local out_dir="$1"
  shift
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$WORK/inputs/neat1_first1.fa" \
    -f2 "$RNA_INPUT" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" \
  FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE=1

python3 - "$WORK/baseline/stderr.log" "$WORK/candidate/stderr.log" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_"


def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")


def require_eq(label: str, observed: str, expected: str) -> None:
    if observed != expected:
        raise SystemExit(f"{label}: expected {expected}, observed {observed}")


def require_positive_int(label: str, observed: str) -> None:
    try:
        number = int(observed)
    except ValueError as exc:
        raise SystemExit(f"{label}: expected integer, observed {observed!r}") from exc
    if number <= 0:
        raise SystemExit(f"{label}: expected > 0, observed {number}")


require_eq("default requested", value(base, "requested"), "0")
require_eq("default active", value(base, "active"), "0")

require_eq("candidate requested", value(candidate, "requested"), "1")
require_eq("candidate active", value(candidate, "active"), "1")
require_eq("candidate source_is_pre_scoreinfo", value(candidate, "source_is_pre_scoreinfo"), "1")
require_eq("candidate scoreinfo_prealign_reduced", value(candidate, "scoreinfo_prealign_reduced"), "1")
require_positive_int("candidate tasks", value(candidate, "tasks"))
require_positive_int("candidate reference_scoreinfos", value(candidate, "reference_scoreinfos"))
require_positive_int("candidate reference_attempts", value(candidate, "reference_attempts"))
require_positive_int("candidate gpu_descriptor_scoreinfos", value(candidate, "gpu_descriptor_scoreinfos"))
require_positive_int("candidate gpu_descriptor_attempts", value(candidate, "gpu_descriptor_attempts"))
require_eq("candidate descriptor_false_negatives", value(candidate, "descriptor_false_negatives"), "0")
require_eq("candidate missing_required_attempts", value(candidate, "missing_required_attempts"), "0")
require_eq(
    "candidate attempts below all-column replay scale",
    value(candidate, "candidate_attempts_below_all_column_replay_scale"),
    "1",
)
require_eq("candidate cpu_align_authority", value(candidate, "cpu_align_authority"), "1")
require_eq(
    "candidate gpu endpoint/cigar/traceback/output authority",
    value(candidate, "gpu_endpoint_cigar_traceback_output_authority"),
    "0",
)
require_eq("candidate gate_v5_1_pass", value(candidate, "gate_v5_1_pass"), "1")

print("phase7_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke=gate_v5_1_pass_first1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_requested=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_active=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts=0")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass=1")
print("ok")
PY
