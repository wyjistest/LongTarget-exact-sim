#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
SCOPED_DOC="$ROOT/docs/fasim_gasal2_top5_scoped_completion_candidate.md"
SCOREINFO_SCOPED_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
REPLACEMENT_CONSUMER_DOC="$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md"
BROAD_PATH_DOC="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
EMISSION_DEBUG_DOC="$ROOT/docs/fasim_gasal2_emission_only_consumer_debug.md"
SCORING_MATRIX_DOC="$ROOT/docs/fasim_gasal2_scoring_parameter_matrix.md"
CPU_AUTHORITY_COVERAGE_DOC="$ROOT/docs/fasim_gasal2_cpu_authority_candidate_coverage_plan.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$SCOPED_DOC" "$SCOREINFO_SCOPED_DOC" "$REPLACEMENT_CONSUMER_DOC" "$BROAD_PATH_DOC" "$EMISSION_DEBUG_DOC" "$SCORING_MATRIX_DOC" "$CPU_AUTHORITY_COVERAGE_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing GASAL2 full-goal decision dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" "$SCOPED_DOC" "$SCOREINFO_SCOPED_DOC" "$REPLACEMENT_CONSUMER_DOC" "$BROAD_PATH_DOC" "$EMISSION_DEBUG_DOC" "$SCORING_MATRIX_DOC" "$CPU_AUTHORITY_COVERAGE_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
scoped = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
scoreinfo_scoped = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
replacement_consumer = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
broad_path = " ".join(Path(sys.argv[7]).read_text(encoding="utf-8").split())
emission_debug = " ".join(Path(sys.argv[8]).read_text(encoding="utf-8").split())
scoring_matrix = " ".join(Path(sys.argv[9]).read_text(encoding="utf-8").split())
cpu_authority_coverage = " ".join(Path(sys.argv[10]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[11]).read_text(encoding="utf-8")

required_doc = [
    "Full Goal Decision Audit",
    "active objective: GPU-ize or GASAL2-ize scoreInfo/preAlign",
    "Current full-goal status: not complete",
    "Scoped top5 status: conditional completion candidate",
    "Universal replacement status: not proven",
    "Long-query status: no real path",
    "GASAL2 / GPU scoreInfo scoped feasibility checkpoint",
    "Post-selected-replay status: scoped milestone, not completion",
    "Current viable productized scope: short-query/H19 top5 artifact plus MEG3 grouping",
    "MALAT1 streaming scoreInfo trust path: scoped go",
    "MALAT1 grouped two-contract trust path: scoped/research go with modest speedup",
    "NEAT1 non-shared streaming scoreInfo trust path: replay clean but performance no-go",
    "Selected-attempt real output authority: not proven",
    "Broad scoreInfo/preAlign replacement: not proven",
    "Broad co-designed replacement-consumer shadow: correctness clean, performance no-go",
    "Attempt-consumer shadow: correctness clean, no CPU-align reduction, performance no-go",
    "--gasal2-top5-column-pruned-scoreinfo",
    "scoreinfo_gasal2_active = 1 for short-query/H19",
    "zero_legacy_score_runs = 1",
    "top5 score/stability/nt_score clean",
    "full `.lite` output is not contract output",
    "final all-row TFO equivalence is not claimed",
    "MALAT1/NEAT1 scoreinfo_gasal2_active = 0 via query guard",
    "single-pass topN is not top5-safe",
    "long-query no-last replay remains marginal through malat1_first128 speedup=1.038017x",
    "current segmented no-last replay line: stopped for real path",
    "full-query exact-column scoreInfo shadow is launch no-go for MALAT1 query_len=8708",
    "shared-memory opt-in launches but is not scoreInfo-equivalent",
    "long-query next-architecture decision = next_architecture_no_go",
    "NEAT1 non-shared scoreInfo realpath replay is clean through first128 but candidate/baseline speedup=0.300675x",
    "NEAT1 first64 fresh runtime attribution",
    "candidate_wall_seconds = 121.948",
    "baseline_wall_seconds = 86.0335",
    "candidate_vs_baseline = 0.705493x",
    "gpu_total_seconds = 49.9507 (~41.0% candidate wall)",
    "realpath_extend_seconds = 52.0682 (~42.7% candidate wall)",
    "unattributed_overhead_seconds ~= 19.9291 (~16.3% candidate wall)",
    "current selector/global-state long-query shape is architecture no-go for broad replacement",
    "NEAT1 shared scoreInfo runner preset fails launch with legacy_byte_shared_smem_exceeds_optin_limit and does not enter scoreInfo realpath",
    "replacement consumer shadow",
    "selected-only replay is not sufficient",
    "If NEAT1 remains slower than CPU fallback, do not promote",
    "make check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "make check-fasim-gasal2-replacement-consumer-shadow-env",
    "broad replacement-consumer shadow on NEAT1 first64:",
    "make check-fasim-gasal2-broad-neat1-first64-result",
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
    "attempt-consumer shadow on NEAT1 first64:",
    "make check-fasim-gasal2-attempt-consumer-neat1-first64-result",
    "decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go",
    "attempts = 211,976",
    "selected_attempts = 140,087",
    "cpu_align_attempts = 140,087",
    "score_seconds = 241.768",
    "total_seconds = 294.821",
    "attempt_consumer_total_not_below_cpu_reference",
    "Selected-attempt CPU-align reduction: no-go for current selector",
    "selected-prefix replay clean but no CPU-align reduction",
    "direct selected-only replay over-emits repeated scoreInfos",
    "legacy-byte streaming scoreInfo: correctness clean, performance no-go",
    "hot GPU minScore / realpath trust: MALAT1 scoped positive, modest speedup",
    "fused minScore: no-go; score/minScore and scoreInfo are separate contracts",
    "two-contract bridge: MALAT1 scoped positive, still default-off and digest-gated",
    "selected-attempt replay reduction: no-go for current selector",
    "NEAT1 current execution shape: correctness-clean diagnostics but performance no-go",
    "score-prepass state-machine trust traceback boundary",
    "do not promote segmented score-prepass state-machine consumer trust",
    "make check-fasim-gasal2-score-prepass-state-machine-stop",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1",
    "selected-segment traceback is not equivalent",
    "expanded-segment oracle is clean only by requiring full NEAT1 query length",
    "expanded_segment_traceback_shadow_required_max_len = 22,767",
    "expanded_segment_traceback_shadow_required_over_gasal2_limit = 21,991",
    "current GASAL2 2,812 bp query guard",
    "GASAL2 selected/expanded segment traceback: no-go for real path",
    "full objective remains open",
    "Do not call update_goal complete for the original full objective",
    "Only mark the original goal complete if universal replacement is proven or the user explicitly accepts the narrowed top5-only product scope as the goal",
    "Next universal-path work must be a different long-query architecture or a full-output/TFO equivalence proof",
    "make check-fasim-gasal2-broad-path-architecture-gate",
    "previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer",
    "decision = broad_path_current_architecture_no_go",
    "reduce both GPU scoreInfo work and CPU realpath extend/align work",
    "current selector/global-state NEAT1 path",
    "score-prepass state-machine consumer trust",
    "current broad replay consumer",
    "scoped MALAT1 two-contract runtime as a broad replacement",
    "The full-output/TFO equivalence proof now has a focused local gate",
    "make check-fasim-lite-full-equivalence",
    "python3 scripts/compare_fasim_lite_full_equivalence.py",
    "--baseline <cpu-authority-TFOsorted.lite>",
    "--candidate <gpu-or-gasal2-TFOsorted.lite>",
    "--baseline-report <cpu-report.json>",
    "--candidate-report <gpu-or-gasal2-report.json>",
    "complete de-duplicated row set for the detected schema",
    "14-column `schema=lite` outputs",
    "19-column `schema=tfosorted` outputs",
    "first missing/extra row",
    "unsupported schemas",
    "mixed baseline/candidate schemas",
    "malformed rows with too few or too many fields",
    "`schema_error` or `parse_error`",
    "resolves `merged_output` by default",
    "`--report-output-field`",
    "`topk_lite_output`",
    "must not be presented as full-output equivalence",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "MALAT1 first8/group32 two-contract",
    "`--output-mode tfosorted`",
    "checks the complete 19-column row set",
    "baseline_rows=796",
    "candidate_rows=796",
    "full_rows_equal=true",
    "scoped first8 proof point only",
    "does not prove full MALAT1",
    "does not close the full objective",
    "CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full",
    "exercised first64 result was also row-set clean",
    "baseline_rows=9741",
    "candidate_rows=9741",
    "MALAT1 full TFOsorted:",
    "baseline_rows = 98,713",
    "candidate_rows = 98,713",
    "baseline_full_digest = ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca",
    "full_rows_equal = true",
    "candidate_vs_baseline = 0.403059x",
    "decision = full-output correctness proof, not runtime claim",
    "limited-scope probe",
    "candidate wall time was slower than baseline",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted",
    "does not use the audited replay/attempt probes",
    "`schema=tfosorted` row-set",
    "`two_contract_used == tasks`",
    "`realpath_used == tasks`",
    "`probe_positive_numeric_keys=0`",
    "MALAT1 first8 no-probe:",
    "candidate_vs_baseline = 0.990695x",
    "tasks = 1,824",
    "MALAT1 first8 TFOsorted no-probe:",
    "schema = tfosorted",
    "candidate_vs_baseline = 0.990699x",
    "MALAT1 first64 no-probe:",
    "digest = f57a418be0ec9439cf2c4c453e2e45cc9d35b03df5e2c63f60860e6575db180d",
    "candidate_vs_baseline = 1.029812x",
    "tasks = 18,096",
    "MALAT1 first128 no-probe:",
    "rows = 22,531",
    "digest = 91ea0b8191027916e3237fb5381c6271fc9acd03b46a5cf67826c253fe41edd1",
    "candidate_vs_baseline = 1.041215x",
    "tasks = 40,128",
    "MALAT1 first256 no-probe:",
    "rows = 42,504",
    "digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e",
    "candidate_vs_baseline = 1.040931x",
    "tasks = 80,640",
    "MALAT1 full no-probe:",
    "baseline_wall_seconds = 2611.940621",
    "candidate_wall_seconds = 2514.945686",
    "candidate_vs_baseline = 1.038567x",
    "tasks = 200,400",
    "MALAT1 full TFOsorted no-probe:",
    "schema = tfosorted",
    "digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc",
    "baseline_wall_seconds = 2636.136998",
    "candidate_wall_seconds = 2537.678266",
    "candidate_vs_baseline = 1.038799x",
    "gpu_scoreinfo_groups = 3,561,123",
    "gpu_scoreinfo_groups = 715,473",
    "scoped milestone for the MALAT1-like grouped two-contract bridge",
    "not broad completion of the original objective",
    "make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256",
    "do not promote fused minScore",
    "do not promote MALAT1 grouped two-contract trust as a broad long-query path",
    "accepted top5-only product scope with explicit output contract",
    "full-output/TFO equivalence proof over the intended workload scope",
    "a genuinely different long-query execution design, not the current selector/global-state path",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "make check-fasim-gasal2-top5-scoped-completion-candidate",
    "make check-fasim-gasal2-top5-release-smoke",
    "formal_preset_example = meg3_first32",
    "formal_preset_topk_artifact_match = true",
    "formal_preset_gasal2_requests = 63,035",
    "formal_preset_exact_scoreinfo_gpu_tasks = 1,536",
    "formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0",
    "contract smoke, not a performance claim",
    "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "first8 no-probe lite and TFOsorted checks plus the scoped/full-goal static gates",
    "scoped MALAT1-like smoke, not a universal replacement smoke",
    "make check-fasim-gasal2-emission-only-consumer-debug",
    "task117 shows CPU score = 68 but GASAL2 segmented score = 138 for the same attempt",
    "FASIM_ALIGN_GASAL2_GAP_OPEN=16 lowers that task117 shadow score to 104",
    "gap-open 16 breaks the NEAT1 first1 emission-only clean gate",
    "validated default fix",
    "production authority or safe reject/accept authority",
    "make check-fasim-gasal2-scoring-parameter-matrix",
    "task49 is an endpoint/terminal mismatch even when score matches",
    "task117 is a segmented score/threshold mismatch",
    "NEAT1 first1 shows gap-open 16 creates new triplex mismatches",
    "not a single scoring-parameter change",
    "make check-fasim-gasal2-cpu-authority-candidate-coverage-plan",
    "GASAL2 may propose threshold/fallback/last candidate attempts",
    "legacy selected attempt must be present in the GASAL2 candidate set",
    "`false_negative_scoreinfos` is nonzero, this reducer stops",
    "make check-fasim-gasal2-full-goal-decision",
    "make check-fasim-gasal2-long-query-current-stop",
    "make check-fasim-gasal2-long-query-next-architecture-decision",
    "make check-fasim-long-query-streaming-scoreinfo-design",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("full-goal decision doc missing phrases: " + ", ".join(missing))

for name, text in (
    ("current-state", current_state),
    ("completion-gap", completion_gap),
    ("scoped-candidate", scoped),
    ("scoreinfo-scoped", scoreinfo_scoped),
):
    for phrase in (
    "make check-fasim-gasal2-full-goal-decision",
        "Full Goal Decision Audit",
        "GASAL2 / GPU scoreInfo scoped feasibility checkpoint",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing full-goal decision phrase: {phrase}")

for phrase in (
    "make check-fasim-gasal2-emission-only-consumer-debug",
    "make check-fasim-gasal2-scoring-parameter-matrix",
    "make check-fasim-gasal2-cpu-authority-candidate-coverage-plan",
    "task_key=49",
    "GASAL2 score equals CPU score for attempt 26",
    "task_key=117 scoreinfo_index=26 attempt_index=104",
    "FASIM_ALIGN_GASAL2_GAP_OPEN=16",
    "GASAL2 endpoint/terminal and current segmented max-score threshold must not become output authority or safe reject/accept authority",
    "GASAL2 may only propose candidate attempts",
    "false_negative_scoreinfos = 0",
    "cpu_align_attempts < realpath_reference_align_attempts",
):
    if phrase not in current_state:
        raise SystemExit(f"current-state doc missing emission-only debug phrase: {phrase}")

for phrase in (
    "Fasim GASAL2 Scoring Parameter Matrix",
    "task_key=49 scoreinfo_index=6 attempt_index=26",
    "CPU ref_end = 1574, terminal = 0",
    "GASAL2 ref_end = 1575, terminal = 1",
    "task_key=117 scoreinfo_index=26 attempt_index=104",
    "gap_open=12",
    "GASAL2 score = 138",
    "gap_open=16",
    "GASAL2 score = 104",
    "NEAT1 first1",
    "triplex_mismatches = 12",
    "parameter change trades one failure mode for another",
    "Do not promote GASAL2 endpoint, terminal, segmented max-score, or gap-open 16 as authority.",
):
    if phrase not in scoring_matrix:
        raise SystemExit(f"scoring-parameter matrix doc missing phrase: {phrase}")

for phrase in (
    "Fasim GASAL2 CPU-Authority Candidate Coverage Plan",
    "This is the next broad-path probe toward the active objective",
    "CPU `aligner.Align()` remains the only authority",
    "GASAL2 may only propose candidate attempts",
    "legacy selected attempt is present in the GASAL2 candidate set",
    "false_negative_scoreinfos = 0",
    "triplex_mismatches = 0",
    "cpu_align_attempts < realpath_reference_align_attempts",
    "total_seconds < realpath_reference_seconds",
    "score_margin sweep",
    "Do not use GASAL2 endpoint as terminal authority",
    "If false_negative_scoreinfos is nonzero, stop this candidate reducer",
):
    if phrase not in cpu_authority_coverage:
        raise SystemExit(f"CPU-authority coverage doc missing phrase: {phrase}")

for phrase in (
    "Fasim GASAL2 Replacement Consumer Shadow Requirements",
    "triplex_mismatches = 0",
    "candidate_wall_seconds < 86.0335",
):
    if phrase not in replacement_consumer:
        raise SystemExit(f"replacement-consumer doc missing phrase: {phrase}")
for phrase in (
    "Fasim GASAL2 Broad Path Architecture Gate",
    "decision = broad_path_current_architecture_no_go",
    "co-designed scoreInfo plus replacement consumer architecture",
):
    if phrase not in broad_path:
        raise SystemExit(f"broad-path doc missing phrase: {phrase}")

for phrase in (
    "Fasim GASAL2 Emission-Only Consumer Debug",
    "task_key=49 scoreinfo_index=6 attempt_index=26",
    "task_key=117 scoreinfo_index=26 attempt_index=104",
    "FASIM_ALIGN_GASAL2_GAP_OPEN=16",
    "GASAL2 endpoint as terminal authority",
    "current segmented max-score threshold",
    "real replacement path: no",
):
    if phrase not in emission_debug:
        raise SystemExit(f"emission-only debug doc missing phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-full-goal-decision:\n"
    r"\tbash \./scripts/check_fasim_gasal2_full_goal_decision\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-full-goal-decision target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-full-goal-decision" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing full-goal decision dependency")
if "check-fasim-gasal2-score-prepass-state-machine-stop" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass stop dependency")
if "check-fasim-gasal2-emission-only-consumer-debug" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing emission-only consumer debug dependency")
if "check-fasim-gasal2-scoring-parameter-matrix" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing scoring-parameter matrix dependency")
if "check-fasim-gasal2-cpu-authority-candidate-coverage-plan" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing CPU-authority candidate coverage dependency")
if "check-fasim-gasal2-scoreinfo-scoped-release-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing scoped release-smoke dependency")
if "check-fasim-gasal2-replacement-consumer-shadow-requirements" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing replacement-consumer shadow requirements dependency")
if "check-fasim-gasal2-broad-path-architecture-gate" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad-path architecture gate dependency")
if "check-fasim-gasal2-long-query-next-architecture-decision" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing long-query next-architecture decision dependency")
if "check-fasim-long-query-streaming-scoreinfo-design" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing long-query streaming scoreInfo design dependency")
if "check-fasim-lite-full-equivalence" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing full lite equivalence dependency")
if "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 TFOsorted equivalence dependency")
if "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 full TFOsorted equivalence dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime TFOsorted dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime first64 dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime first128 dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime first256 dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime full dependency")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 no-probe two-contract runtime full TFOsorted dependency")
PY

echo "ok"
