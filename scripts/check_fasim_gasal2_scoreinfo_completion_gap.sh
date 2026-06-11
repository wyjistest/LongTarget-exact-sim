#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
REPLACEMENT_CONSUMER_DOC="$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md"
BROAD_PATH_DOC="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CURRENT_STATE_DOC" "$REPLACEMENT_CONSUMER_DOC" "$BROAD_PATH_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing completion-gap dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$REPLACEMENT_CONSUMER_DOC" "$BROAD_PATH_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
replacement_consumer = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
broad_path = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_doc = [
    "GPU-ize or GASAL2-ize scoreInfo/preAlign",
    "prevent the current top5 artifact milestone from being mistaken for completion",
    "--gasal2-top5-column-pruned-scoreinfo",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "short-query/H19 top5 artifact path",
    "chr21+chr22",
    "top5 artifact clean",
    "GASAL2 requests > 0",
    "GASAL2 traceback requests > 0",
    "exact scoreInfo GPU tasks > 0",
    "fallback/overflow = 0",
    "speedup vs CPU worker wall sum = 40.119136x",
    "MEG3 grouped",
    "complete-record grouped wrapper path clean",
    "runtime examples boundary",
    "MEG3 scoreinfo_gasal2_active = 1",
    "MALAT1/NEAT1 scoreinfo_gasal2_active = 0 via query guard",
    "The full objective is not complete",
    "not universal scoreInfo/preAlign replacement",
    "not full lite-output equivalence",
    "not exact legacy scoreInfo equivalence",
    "not final all-row TFO equivalence",
    "not `aligner.Align()` replacement",
    "not GPU endpoint/CIGAR/traceback authority",
    "not broad long-query MALAT1/NEAT1 GASAL2 active path",
    "not default production path",
    "GASAL2_MAX_QUERY_LEN = 2812",
    "MEG3 query_len = 1582",
    "MALAT1 query_len = 8708",
    "NEAT1 query_len = 22767",
    "malat1_first8 speedup = 1.009996x",
    "malat1_first16 speedup = 1.029101x",
    "malat1_first32 speedup = 1.031832x",
    "malat1_first64 speedup = 1.034623x",
    "malat1_first128 speedup = 1.038017x",
    "NEAT1 non-shared streaming scoreInfo trust path: replay clean but performance no-go",
    "NEAT1 non-shared replay-clean boundary",
    "shared runner trust preset does not enter scoreInfo realpath",
    "NEAT1 first64 fresh runtime attribution",
    "candidate_wall_seconds = 121.948",
    "baseline_wall_seconds = 86.0335",
    "candidate_vs_baseline = 0.705493x",
    "gpu_total_seconds = 49.9507 (~41.0% candidate wall)",
    "realpath_extend_seconds = 52.0682 (~42.7% candidate wall)",
    "unattributed_overhead_seconds ~= 19.9291 (~16.3% candidate wall)",
    "current selector/global-state long-query shape is architecture no-go for broad replacement",
    "NEAT1 non-shared audited replay first128",
    "tasks = 6,144",
    "realpath_used = 6,144",
    "gpu_scoreinfo_groups = 105,845",
    "replay align attempts = 281,588",
    "segmented/full/oracle replay mismatches = 0",
    "candidate/baseline speedup = 0.300675x",
    "NEAT1 shared runner trust preset",
    "shared scoreInfo kernel error = legacy_byte_shared_smem_exceeds_optin_limit",
    "realpath_fallbacks = 4 on first4",
    "make check-fasim-gasal2-long-query-current-stop",
    "current segmented no-last replay line: stopped for real path",
    "single-pass topN scoreInfo probe",
    "first DP pass can produce bounded topN scoreInfo-like candidates",
    "does not currently produce exact legacy scoreInfo",
    "not top5-safe for the current artifact contract",
    "make check-fasim-gasal2-single-pass-topn-sweep",
    "Universal Replacement",
    "Accepted Top5-Only Product Scope",
    "Long-Query Continuation",
    "scoreinfo_gasal2_active = 1 where the path is claimed",
    "different long-query architecture, not current selector/global-state tuning",
    "or full-output/TFO equivalence proof over the claimed scope",
    "full output or explicitly scoped output contract clean",
    "performance wins CPU authority on representative workloads",
    "For a full-output/TFO equivalence claim, use the canonical full-row comparator",
    "make check-fasim-lite-full-equivalence",
    "python3 scripts/compare_fasim_lite_full_equivalence.py",
    "--baseline <cpu-authority-TFOsorted.lite>",
    "--candidate <gpu-or-gasal2-TFOsorted.lite>",
    "--baseline-report <cpu-report.json>",
    "--candidate-report <gpu-or-gasal2-report.json>",
    "complete de-duplicated row set for the detected schema",
    "14-column `schema=lite` outputs",
    "19-column `schema=tfosorted` outputs",
    "baseline and candidate schemas must match",
    "fails closed on unsupported schemas",
    "mixed-schema comparisons",
    "malformed rows with too few or too many fields",
    "schema/parse failures",
    "Top5 artifact equality is not a substitute",
    "resolves the runner `merged_output` field by default",
    "Explicitly selecting `topk_lite_output` keeps the comparison in the top5 artifact scope",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "MALAT1 first8/group32 two-contract path",
    "`--output-mode tfosorted`",
    "baseline_rows=796",
    "candidate_rows=796",
    "full_rows_equal=true",
    "meaningful 19-column row-set evidence for a small MALAT1-like slice",
    "not full MALAT1 or broad long-query TFO equivalence",
    "CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "baseline_rows=9741",
    "candidate_rows=9741",
    "candidate wall time was slower than baseline",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full",
    "MALAT1 full TFOsorted:",
    "baseline_full_digest=ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca",
    "candidate_vs_baseline=0.403059x",
    "decision=full-output correctness proof, not runtime claim",
    "make check-fasim-gasal2-malat1-tfosorted-runtime-breakdown",
    "wall_delta = 8.898913s",
    "diagnostic_probe_seconds = 22.010077s",
    "attempt_probe_seconds = 15.994410s",
    "audited_wall_not_real_runtime_claim",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted",
    "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1",
    "decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go",
    "attempts = 211,976",
    "selected_attempts = 140,087",
    "cpu_align_attempts = 140,087",
    "candidate_vs_baseline = 0.148434x",
    "does not reduce CPU `aligner.Align()` attempts",
    "first8 no-probe lite and TFOsorted checks",
    "MALAT1-like scoped smoke, not a universal replacement smoke",
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1",
    "rejects probe env leakage",
    "numeric probe telemetry to remain zero",
    "candidate_vs_baseline=0.990695x",
    "tasks=1,824",
    "probe_positive_numeric_keys=0",
    "schema=tfosorted",
    "candidate_vs_baseline=0.990699x",
    "digest=f57a418be0ec9439cf2c4c453e2e45cc9d35b03df5e2c63f60860e6575db180d",
    "candidate_vs_baseline=1.029812x",
    "tasks=18,096",
    "gpu_scoreinfo_groups=319,280",
    "full MALAT1:",
    "candidate_vs_baseline=1.038567x",
    "tasks=200,400",
    "gpu_scoreinfo_groups=3,561,123",
    "full MALAT1 TFOsorted:",
    "schema=tfosorted",
    "digest=ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc",
    "candidate_vs_baseline=1.038799x",
    "realpath_extend_seconds=1165.840400",
    "clean runtime evidence for the scoped MALAT1-like two-contract bridge",
    "rows=22531",
    "digest=91ea0b8191027916e3237fb5381c6271fc9acd03b46a5cf67826c253fe41edd1",
    "candidate_vs_baseline=1.041215x",
    "tasks=40,128",
    "rows=42504",
    "candidate_vs_baseline=1.040931x",
    "tasks=80,640",
    "not a universal scoreInfo/preAlign replacement claim",
    "top5-only output contract accepted",
    "long-query fallback policy accepted",
    "make check-fasim-gasal2-top5-broader-validation",
    "make check-fasim-gasal2-top5-recommended-runtime",
    "make check-fasim-gasal2-top5-scoped-completion-candidate",
    "make check-fasim-gasal2-top5-release-smoke",
    "formal_preset_example = meg3_first32",
    "formal_preset_topk_artifact_match = true",
    "formal_preset_gasal2_requests = 63,035",
    "formal_preset_exact_scoreinfo_gpu_tasks = 1,536",
    "formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0",
    "contract smoke, not a performance claim",
    "GPU/GASAL2 total < CPU fallback",
    "legacy-byte streaming scoreInfo: correctness clean, performance no-go",
    "hot GPU minScore / realpath trust: MALAT1 scoped positive, modest speedup",
    "fused minScore: no-go",
    "two-contract bridge: MALAT1 scoped/research positive, default-off and digest-gated",
    "selected-attempt CPU-align reduction: no-go for current selector",
    "NEAT1 current execution shape: performance no-go",
    "make check-fasim-gasal2-score-prepass-state-machine-stop",
    "does not reduce CPU traceback work",
    "selected-segment traceback is not equivalent to full-query `aligner.Align()`",
    "post-selected-replay status:",
    "scoped milestone, not completion",
    "full objective",
    "not complete",
    "Do not call `update_goal complete`",
    "make check-fasim-gasal2-scoreinfo-completion-gap",
    "make check-fasim-gasal2-full-goal-decision",
    "make check-fasim-gasal2-broad-path-architecture-gate",
    "previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer",
    "decision = broad_path_current_architecture_no_go",
    "current co-designed broad replacement-consumer shadow is correctness-clean but a performance no-go",
    "make check-fasim-gasal2-broad-neat1-first64-result",
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
    "Kernel-only scoreInfo work is not enough",
    "selected-only replay is not a valid broad consumer",
    "make check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "make check-fasim-gasal2-replacement-consumer-shadow-env",
    "replacement consumer shadow",
    "selected-only replay is not sufficient",
    "If NEAT1 remains slower than CPU fallback, do not promote",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("completion-gap doc missing phrases: " + ", ".join(missing))

for phrase in (
    "full replacement goal: still open",
    "post-selected-replay status = scoped milestone, not completion",
    "not universal scoreInfo/preAlign replacement",
    "long-query MALAT1/NEAT1: no real path",
    "FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1 is not recommended",
    "top5 broader workload validation",
    "GASAL2 top5 recommended runtime",
    "full objective remains open",
):
    if phrase not in current_state:
        raise SystemExit(f"current-state doc missing completion gap phrase: {phrase}")

for phrase in (
    "Fasim GASAL2 Replacement Consumer Shadow Requirements",
    "CPU fastSIM_extend_from_scoreinfo remains authority",
    "replacement consumer plus GPU scoreInfo total beats CPU fallback",
):
    if phrase not in replacement_consumer:
        raise SystemExit(f"replacement-consumer doc missing phrase: {phrase}")
for phrase in (
    "Fasim GASAL2 Broad Path Architecture Gate",
    "decision = broad_path_current_architecture_no_go",
    "kernel-only scoreInfo improvement cannot close the broad goal",
):
    if phrase not in broad_path:
        raise SystemExit(f"broad-path doc missing phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-scoreinfo-completion-gap:\n"
    r"\tbash \./scripts/check_fasim_gasal2_scoreinfo_completion_gap\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-scoreinfo-completion-gap target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-scoreinfo-completion-gap" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing completion-gap dependency")
if "check-fasim-gasal2-score-prepass-state-machine-stop" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing score-prepass stop dependency")
if "check-fasim-gasal2-scoreinfo-scoped-release-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing scoped release-smoke dependency")
if "check-fasim-gasal2-replacement-consumer-shadow-requirements" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing replacement-consumer shadow requirements dependency")
if "check-fasim-gasal2-broad-path-architecture-gate" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing broad-path architecture gate dependency")
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
