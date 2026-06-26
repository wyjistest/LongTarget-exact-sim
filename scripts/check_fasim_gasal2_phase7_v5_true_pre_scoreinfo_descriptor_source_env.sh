#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
files = {
    "header": root / "fasim/gasal2_align_bridge.h",
    "bridge": root / "fasim/gasal2_align_bridge.cpp",
    "stub": root / "fasim/gasal2_align_bridge_stub.cpp",
    "main": root / "fasim/Fasim-LongTarget.cpp",
    "makefile": root / "Makefile",
}
for label, path in files.items():
    if not path.exists():
        raise SystemExit(f"missing {label}: {path}")

text = {label: path.read_text(encoding="utf-8", errors="replace") for label, path in files.items()}

env_name = "FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE"
helper = "fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_runtime"
record = "fasim_gasal2_record_phase7_v5_true_pre_scoreinfo_descriptor_source"
prefix = "benchmark.fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_"

required = [
    (text["header"], helper),
    (text["header"], record),
    (text["bridge"], env_name),
    (text["bridge"], helper),
    (text["bridge"], record),
    (text["stub"], helper),
    (text["stub"], record),
    (text["main"], "fasim_print_phase7_v5_true_pre_scoreinfo_descriptor_source_stats"),
    (text["makefile"], "check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env:"),
]
for haystack, needle in required:
    if needle not in haystack:
        raise SystemExit(f"missing required env scaffold symbol: {needle}")

metric_suffixes = [
    "requested",
    "active",
    "tasks",
    "reference_scoreinfos",
    "reference_attempts",
    "gpu_descriptor_scoreinfos",
    "gpu_descriptor_attempts",
    "source_is_pre_scoreinfo",
    "scoreinfo_prealign_reduced",
    "descriptor_false_negatives",
    "missing_required_attempts",
    "candidate_attempts_below_all_column_replay_scale",
    "cpu_align_authority",
    "gpu_endpoint_cigar_traceback_output_authority",
    "gate_v5_1_pass",
]
for suffix in metric_suffixes:
    metric = prefix + suffix
    if metric not in text["main"] and metric not in text["stub"]:
        raise SystemExit(f"missing metric print: {metric}")

for suffix in metric_suffixes:
    field = "phase7_v5_true_pre_scoreinfo_descriptor_source_" + suffix
    if field not in text["header"]:
        raise SystemExit(f"missing stats field: {field}")

print("phase7_v5_true_pre_scoreinfo_descriptor_source_env=pass")
print("required_env=FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE")
print("default_off=1")
print("ok")
PY
