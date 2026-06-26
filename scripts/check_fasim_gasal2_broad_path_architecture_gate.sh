#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
SPEED_DOC="$ROOT/docs/fasim_gasal2_neat1_speed_ceiling.md"
NEXT_REQ_DOC="$ROOT/docs/fasim_gasal2_neat1_next_architecture_requirements.md"
CONSUMER_DOC="$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md"
STOP_DOC="$ROOT/docs/fasim_gasal2_score_prepass_state_machine_stop.md"
MALAT1_PRODUCT_DOC="$ROOT/docs/fasim_gasal2_malat1_two_contract_product_readiness.md"
ROLLUP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone_rollup.md"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$DOC" \
  "$CURRENT_STATE_DOC" \
  "$FULL_GOAL_DOC" \
  "$COMPLETION_GAP_DOC" \
  "$SPEED_DOC" \
  "$NEXT_REQ_DOC" \
  "$CONSUMER_DOC" \
  "$STOP_DOC" \
  "$MALAT1_PRODUCT_DOC" \
  "$ROLLUP_DOC" \
  "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing broad-path architecture gate dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$SPEED_DOC" "$NEXT_REQ_DOC" "$CONSUMER_DOC" "$STOP_DOC" "$MALAT1_PRODUCT_DOC" "$ROLLUP_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
speed_doc = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
next_req = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
consumer = " ".join(Path(sys.argv[7]).read_text(encoding="utf-8").split())
stop_doc = " ".join(Path(sys.argv[8]).read_text(encoding="utf-8").split())
malat1_product = " ".join(Path(sys.argv[9]).read_text(encoding="utf-8").split())
rollup = " ".join(Path(sys.argv[10]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[11]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 Broad Path Architecture Gate",
    "design gate, not runtime code",
    "short-query/H19 top5 artifact:",
    "scoped product candidate",
    "MALAT1-like group32 two-contract runtime:",
    "scoped product-readiness candidate",
    "NEAT1 non-shared trust runtime first64:",
    "candidate_vs_baseline = 0.705493x",
    "gpu_total_seconds = 49.9507",
    "realpath_extend_seconds = 52.0682",
    "ideal_zero_gpu_call_speedup = 0.9747x",
    "ideal_zero_gpu_total_speedup = 1.1950x",
    "ideal_zero_realpath_extend_speedup = 1.2312x",
    "score-prepass state-machine consumer:",
    "candidate_vs_baseline = 0.5951x on NEAT1 first16",
    "selected-segment traceback mismatches = 22,000 / 35,152 on first16",
    "expanded-segment oracle requires full query length",
    "co-designed broad replacement-consumer shadow on NEAT1 first64:",
    "decision = broad_path_current_architecture_no_go",
    "broad_path_tasks = 3,058",
    "broad_path_scoreinfo_groups = 52,994",
    "broad_path_align_attempts = 264,970",
    "broad_path_triplex_mismatches = 0",
    "broad_path_missing_triplexes = 0",
    "broad_path_extra_triplexes = 0",
    "baseline_wall_seconds = 86.932816",
    "candidate_wall_seconds = 288.4177",
    "candidate_vs_baseline = 0.301413x",
    "broad_path_scoreinfo_seconds = 19.1704",
    "broad_path_consumer_seconds = 52.0465",
    "baseline_cpu_reference_seconds = 52.0833",
    "realpath_extend_align_attempts = 140,087",
    "candidate_wall_not_below_neat1_baseline_ceiling",
    "candidate_vs_baseline_not_above_1",
    "broad_scoreinfo_consumer_not_below_cpu_reference",
    "align_attempts_not_reduced",
    "kernel-only scoreInfo improvement cannot close the broad goal",
    "current co-designed broad replacement-consumer shadow is also a measured performance no-go",
    "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1",
    "decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go",
    "attempts = 211,976",
    "selected_attempts = 140,087",
    "cpu_align_attempts = 140,087",
    "total_seconds = 294.821",
    "candidate_vs_baseline = 0.148434x",
    "reduce both GPU scoreInfo work and CPU realpath extend/align work",
    "co-designed scoreInfo plus replacement consumer architecture",
    "produce legacy-byte-compatible scoreInfo or prove an explicitly scoped output contract",
    "preserve scoreInfo-level single-emission semantics",
    "avoid current CPU preAlign replay",
    "reduce or replace current CPU realpath extend/align replay",
    "compare complete task triplex lists against CPU authority",
    "keep external digest or full row-set equality as output authority",
    "keep GPU endpoint/CIGAR/traceback out of authority unless separately proven",
    "The replacement consumer must not be selected-only replay",
    "legacy scoreInfo-local break/best-end state",
    "broad_path_requested",
    "broad_path_active",
    "broad_path_scoreinfo_seconds",
    "broad_path_consumer_seconds",
    "broad_path_triplex_mismatches",
    "broad_path_candidate_vs_baseline",
    "two_contract_used",
    "two_contract_scoreinfo_mismatches",
    "realpath_used",
    "gpu_scoreinfo_groups",
    "NEAT1 first64 is the broad-path gate",
    "digest clean or full row-set equality clean",
    "triplex_mismatches = 0",
    "scoreinfo_gasal2_active = 1 or explicitly scoped equivalent active path",
    "fallback = 0",
    "scoreInfo mismatches = 0",
    "candidate_wall_seconds < 86.0335",
    "candidate_vs_baseline > 1.0x",
    "GPU scoreInfo plus replacement-consumer total beats CPU fallback",
    "realpath_extend_align_attempts materially reduced or replaced",
    "MALAT1 scoped product-readiness remains clean",
    "stop the NEAT1 broad path",
    "kernel-only improvement is the main change",
    "selected-only replay is the consumer",
    "prefix replay is required and align attempts are not reduced",
    "triplex output changes",
    "full row-set equality fails for the claimed scope",
    "NEAT1 remains slower than CPU fallback",
    "MALAT1 scoped product-readiness regresses",
    "Do not promote:",
    "current selector/global-state NEAT1 path",
    "segmented no-last replay",
    "single-pass topN",
    "exact tiling",
    "overlap tiling",
    "smem opt-in exact-column",
    "score-prepass state-machine consumer trust",
    "selected-segment GASAL2 traceback",
    "MALAT1 scoped two-contract runtime as broad long-query replacement",
    "top5 artifact path as full-output replacement",
    "phase7_broad_restart_v3_candidate_certificate_design = defined",
    "phase7_broad_restart_v3_current_status = design_only",
    "phase7_broad_restart_v3_next_gate = descriptor_source_smoke",
    "requires_gpu_or_native_descriptor_source = 1",
    "requires_candidate_certificate = 1",
    "requires_cpu_authority_replay = 1",
    "requires_scoreinfo_prealign_reduction = 1",
    "requires_align_side_reduction = 1",
    "requires_full_output_equality = 1",
    "phase7_broad_restart_v3_may_claim_completion = 0",
    "phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source",
    "phase7_broad_restart_v3_current_status = scaffold_no_go",
    "phase7_v3_descriptor_source_requested = 1",
    "phase7_v3_descriptor_source_active = 0",
    "phase7_v3_descriptor_source_candidate_attempts = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "phase7_broad_restart_v3_next_gate = real_pre_scoreinfo_descriptor_source",
    "phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke = pre_scoreinfo_descriptors_no_reduction",
    "phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go",
    "phase7_v3_descriptor_source_active = 1",
    "phase7_v3_descriptor_source_pre_scoreinfo_source = 1",
    "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0",
    "phase7_v3_descriptor_source_candidate_certificate_checked = 0",
    "phase7_broad_restart_v3_next_gate = certificate_checked_scoreinfo_reducing_descriptor_source",
    "prototype a materially different scoreInfo plus replacement consumer architecture",
    "reduce scoreInfo/align attempts before replaying CPU aligner state",
    "productize an accepted scoped contract without claiming broad replacement",
    "previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer",
    "decision = broad_path_current_architecture_no_go",
    "full objective remains open",
    "make check-fasim-gasal2-broad-path-architecture-gate",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("broad-path architecture gate doc missing phrases: " + ", ".join(missing))

for name, text, phrases in (
    (
        "speed ceiling",
        speed_doc,
        [
            "ideal_zero_gpu_call_speedup = 0.9747x",
            "next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work",
        ],
    ),
    (
        "NEAT1 next requirements",
        next_req,
        [
            "kernel-only win is not sufficient",
            "avoid current CPU realpath extend/align replay or replace it with an equivalent batched consumer",
        ],
    ),
    (
        "replacement consumer",
        consumer,
        [
            "selected-only replay is not sufficient",
            "preserve scoreInfo-level single-emission semantics",
            "candidate_wall_seconds < 86.0335",
        ],
    ),
    (
        "score-prepass stop",
        stop_doc,
        [
            "current real path: no-go",
            "selected-segment traceback",
            "expanded-segment oracle",
        ],
    ),
    (
        "MALAT1 product-readiness",
        malat1_product,
        [
            "product-readiness candidate",
            "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
            "full objective remains open",
        ],
    ),
    (
        "rollup",
        rollup,
        [
            "Milestone status: yes, scoped milestone",
            "Full objective status: not complete",
            "full objective remains open",
        ],
    ),
):
    missing_cross = [phrase for phrase in phrases if phrase not in text]
    if missing_cross:
        raise SystemExit(f"{name} doc missing broad-path prerequisite phrase: " + ", ".join(missing_cross))

for name, text in (
    ("current-state", current_state),
    ("full-goal", full_goal),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "make check-fasim-gasal2-broad-path-architecture-gate",
        "decision = broad_path_current_architecture_no_go",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing broad-path architecture phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-broad-path-architecture-gate:\n"
    r"\tbash \./scripts/check_fasim_gasal2_broad_path_architecture_gate\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-broad-path-architecture-gate target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
deps = set(current_target.group("deps").split())
for dep in (
    "check-fasim-gasal2-broad-path-architecture-gate",
    "check-fasim-gasal2-neat1-speed-ceiling",
    "check-fasim-gasal2-neat1-next-architecture-requirements",
    "check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "check-fasim-gasal2-score-prepass-state-machine-stop",
    "check-fasim-gasal2-malat1-two-contract-product-readiness",
):
    if dep not in deps:
        raise SystemExit(f"current-state target missing broad-path dependency: {dep}")

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
if "check-fasim-gasal2-broad-path-architecture-gate" not in set(phony_targets):
    raise SystemExit("broad-path architecture gate target missing from .PHONY")
PY

echo "ok"
