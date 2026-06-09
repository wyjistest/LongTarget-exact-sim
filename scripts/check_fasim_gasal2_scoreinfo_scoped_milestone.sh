#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
STREAMING_DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"
RUNNER_CHARACTERIZATION="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner.sh"
RUNNER_GROUP_CHARACTERIZATION="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups.sh"

for path in "$DOC" "$CURRENT_STATE_DOC" "$STREAMING_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" "$RUNNER_CHARACTERIZATION" "$RUNNER_GROUP_CHARACTERIZATION"; do
  if [[ ! -s "$path" ]]; then
    echo "missing scoped milestone dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$CURRENT_STATE_DOC" "$STREAMING_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" "$RUNNER_CHARACTERIZATION" "$RUNNER_GROUP_CHARACTERIZATION" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
streaming = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")
runner_characterization = Path(sys.argv[6]).read_text(encoding="utf-8")
runner_group_characterization = Path(sys.argv[7]).read_text(encoding="utf-8")

required_doc = [
    "Fasim GASAL2 ScoreInfo Scoped Milestone",
    "This is a scoped milestone, not completion of the full objective",
    "Milestone name: GASAL2 / GPU scoreInfo scoped feasibility checkpoint",
    "Short-query/H19 top5 path: scoped go",
    "chr21+chr22 formal result",
    "speedup = 40.119136x",
    "MEG3 grouped top5 wrapper: scoped go",
    "MALAT1 streaming scoreInfo trust path: scoped go for MALAT1-like workload shape",
    "MALAT1 two-contract group32 audited first256",
    "digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e",
    "tasks = 80,640",
    "two_contract_used = 80,640",
    "realpath_used = 80,640",
    "two_contract_fallbacks = 0",
    "two_contract_score_mismatches = 0",
    "two_contract_min_score_mismatches = 0",
    "two_contract_scoreinfo_mismatches = 0",
    "realpath_fallbacks = 0",
    "gpu_scoreinfo_groups = 1,434,844",
    "baseline runner wall = 1058.944629s",
    "candidate runner wall = 1015.698961s",
    "candidate_vs_baseline = 1.042577x",
    "resume_audited = true",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256",
    "record_limit = 670",
    "tasks = 200,400",
    "realpath_used = 200,400",
    "realpath_fallbacks = 0",
    "cpu_scoreinfo_groups = 0",
    "gpu_scoreinfo_groups = 3,561,123",
    "cpu_prealign_seconds = 0",
    "gpu_total_seconds = 486.763",
    "baseline Running time = 2631.57s",
    "candidate Running time = 2532.48s",
    "candidate/baseline speedup = 1.039128x",
    "Full Lite-Output / TFOsorted Boundary",
    "schema=lite:",
    "14-column FASIM_OUTPUT_MODE=lite rows",
    "schema=tfosorted:",
    "19-column full TFOsorted rows including Class/MidPoint/Center/TFO/TTS sequence",
    "Existing MALAT1 report pairs are full lite-output clean",
    "python3 scripts/compare_fasim_lite_full_equivalence.py",
    "--baseline-report .tmp/characterize_two_contract_hot_smoke/malat1_first8/baseline/report.json",
    "--candidate-report .tmp/characterize_two_contract_hot_smoke/malat1_first8/candidate/report.json",
    "schema=lite",
    "baseline_rows=796",
    "candidate_rows=796",
    "MALAT1 first64:",
    "baseline_rows=9741",
    "candidate_rows=9741",
    "MALAT1 full group32 two-contract:",
    "baseline_rows=98713",
    "candidate_rows=98713",
    "MALAT1 full group32 trust:",
    "MALAT1 current audited first256:",
    "baseline_rows=42504",
    "candidate_rows=42504",
    "complete de-duplicated 14-column lite row set",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "MALAT1 first8/group32 two-contract TFOsorted:",
    "output_mode = tfosorted",
    "runner merged digest = c245a4c1e34b9c640bdd5e8e44a896f470ec9d8e83799f7de977e0716955dad5",
    "schema=tfosorted",
    "baseline_rows = 796",
    "candidate_rows = 796",
    "baseline_unique_rows = 796",
    "candidate_unique_rows = 796",
    "full_rows_equal=true",
    "missing_rows = 0",
    "extra_rows = 0",
    "focused first8 19-column row-set equivalence point",
    "It still does not prove full MALAT1 19-column TFOsorted/TFO-sequence equivalence",
    "CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "MALAT1 first64/group32 two-contract TFOsorted:",
    "runner merged digest = 2789f4bea9cef5914dfdaa9555e5f22b827b122aee0a1220b402c107dc806ba5",
    "baseline_rows = 9741",
    "candidate_rows = 9741",
    "baseline_unique_rows = 9741",
    "candidate_unique_rows = 9741",
    "tasks = 18,096",
    "two_contract_used = 18,096",
    "realpath_used = 18,096",
    "gpu_scoreinfo_groups = 319,280",
    "baseline runner wall = 237.215788s",
    "candidate runner wall = 246.114701s",
    "candidate_vs_baseline = 0.963842x",
    "strengthens correctness evidence, not performance evidence",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full",
    "MALAT1 full/group32 two-contract TFOsorted:",
    "baseline_rows = 98,713",
    "candidate_rows = 98,713",
    "baseline_full_digest = ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca",
    "candidate_vs_baseline = 0.403059x",
    "decision = full-output correctness proof, not runtime claim",
    "make check-fasim-gasal2-malat1-tfosorted-runtime-breakdown",
    "MALAT1 first64/group32 two-contract TFOsorted runtime breakdown:",
    "wall_delta = 8.898913s",
    "two_contract_total_seconds = 45.198600s",
    "gpu_minscore_wall_seconds = 14.655500s",
    "realpath_extend_seconds = 104.648700s",
    "diagnostic_probe_seconds = 22.010077s",
    "attempt_probe_seconds = 15.994410s",
    "decision = audited_wall_not_real_runtime_claim",
    "The diagnostic probe time exceeds the wall-time regression",
    "first64 `tfosorted` result in the correctness-evidence bucket",
    "No-Probe Two-Contract Runtime Gate",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1",
    "FASIM_ALIGN_GASAL2=1",
    "rejects probe env leakage",
    "Fresh first8 result:",
    "digest = 093a0d693301322e027ba6f3bd760bcbde60759131f156224f3924b7478581df",
    "baseline_wall_seconds = 23.093321",
    "candidate_wall_seconds = 23.310225",
    "candidate_vs_baseline = 0.990695x",
    "tasks = 1,824",
    "Fresh first8 TFOsorted no-probe result:",
    "schema = tfosorted",
    "digest = c245a4c1e34b9c640bdd5e8e44a896f470ec9d8e83799f7de977e0716955dad5",
    "candidate_vs_baseline = 0.990699x",
    "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "first8 no-probe lite and first8 no-probe TFOsorted gates",
    "scoped MALAT1-like contract/runtime smoke",
    "not a universal replacement smoke and not a performance claim",
    "make check-fasim-gasal2-malat1-two-contract-product-readiness",
    "make check-fasim-gasal2-malat1-two-contract-recommended-runtime",
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "default-off scope",
    "direct `aligner.Align()` replacement",
    "Fresh optional first64 result:",
    "rows = 9,741",
    "digest = f57a418be0ec9439cf2c4c453e2e45cc9d35b03df5e2c63f60860e6575db180d",
    "baseline_wall_seconds = 234.981992",
    "candidate_wall_seconds = 227.945703",
    "candidate_vs_baseline = 1.030868x",
    "tasks = 18,096",
    "two_contract_used = 18,096",
    "realpath_used = 18,096",
    "gpu_minscore_used = 18,096",
    "gpu_scoreinfo_groups = 319,280",
    "two_contract_total_seconds = 45.133800",
    "gpu_minscore_wall_seconds = 14.666610",
    "realpath_extend_seconds = 102.495900",
    "realpath_extend_align_seconds = 102.015200",
    "probe_positive_numeric_keys = 0",
    "Fresh optional first128 result:",
    "rows = 22,531",
    "tasks = 40,128",
    "two_contract_used = 40,128",
    "realpath_used = 40,128",
    "gpu_scoreinfo_groups = 715,473",
    "candidate_vs_baseline = 1.043793x",
    "two_contract_total_seconds = 94.842700",
    "gpu_minscore_wall_seconds = 31.285140",
    "realpath_extend_seconds = 229.344300",
    "realpath_extend_align_seconds = 228.267200",
    "Fresh optional first256 result:",
    "Fresh full-MALAT1 no-probe result:",
    "baseline_wall_seconds = 2616.446186",
    "candidate_wall_seconds = 2521.276554",
    "candidate_vs_baseline = 1.037747x",
    "tasks = 200,400",
    "two_contract_used = 200,400",
    "realpath_used = 200,400",
    "gpu_minscore_used = 200,400",
    "gpu_scoreinfo_groups = 3,561,123",
    "probe_positive_numeric_keys = 0",
    "Full-MALAT1 Milestone Decision",
    "scoped full-MALAT1 no-probe runtime go",
    "not broad scoreInfo/preAlign replacement",
    "remaining bottleneck is CPU realpath extend/align",
    "realpath_extend_align_attempts = 8,526,477",
    "two_contract kernel remains substantial, but it is not the only wall-time limiter",
    "rows = 42,504",
    "digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e",
    "baseline_wall_seconds = 1056.005165",
    "candidate_wall_seconds = 1012.697865",
    "candidate_vs_baseline = 1.042764x",
    "tasks = 80,640",
    "two_contract_used = 80,640",
    "realpath_used = 80,640",
    "gpu_scoreinfo_groups = 1,434,844",
    "two_contract_total_seconds = 191.051600",
    "gpu_minscore_wall_seconds = 62.517270",
    "realpath_extend_seconds = 461.650400",
    "realpath_extend_align_seconds = 459.494600",
    "Fresh full-MALAT1 TFOsorted no-probe result:",
    "schema = tfosorted",
    "digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc",
    "candidate_vs_baseline = 1.037590x",
    "realpath_extend_seconds = 1165.680900",
    "realpath_extend_align_seconds = 1139.782800",
    "no-probe evidence into a repeatable repository gate",
    "first64 is only a slight speedup",
    "first8 is slightly slower",
    "`aligner.Align()` authority",
    "NEAT1 streaming scoreInfo trust path: performance no-go for current global-state kernel",
    "NEAT1 non-shared legacy-byte trust path is correctness-clean through a first128 audited replay",
    "record_limit = 64",
    "realpath_used = 3,072",
    "realpath_fallbacks = 0",
    "gpu_scoreinfo_groups = 52,994",
    "candidate/baseline speedup = 0.708143x",
    "NEAT1 non-shared audited replay first64",
    "replay tasks = 3,072",
    "replay align attempts = 140,087",
    "NEAT1 non-shared audited replay first128",
    "digest = 6b0f50f11373ce2dcd8b86045847236d7a094bb43bfa95a0b68a3f66840f9c6e",
    "replay tasks = 6,144",
    "gpu_scoreinfo_groups = 105,845",
    "replay align attempts = 281,588",
    "candidate/baseline speedup = 0.300675x",
    "shared scoreInfo kernel fails with `invalid argument`",
    "`gpu_scoreinfo_groups=0`, `realpath_used=0`, and `realpath_fallbacks=4`",
    "Broad scoreInfo/preAlign replacement: not proven",
    "Full aligner.Align replacement: not proven",
    "GPU endpoint/CIGAR/traceback authority: not proven",
    "Do not mark the active full objective complete from this milestone",
    "make check-fasim-gasal2-scoreinfo-scoped-milestone",
    "make check-fasim-gasal2-malat1-lite-equivalence-evidence",
    "make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "make check-fasim-long-query-streaming-scoreinfo-trust-group32-runner",
    "make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner",
    "make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real",
    "make check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real",
    "make characterize-fasim-long-query-streaming-scoreinfo-trust-runner",
    "make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers",
    "make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups",
    "make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling",
    "make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32",
    "make characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust",
    "make characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust",
    "Runner-level MALAT1 trust characterization now covers first8/first16/first32/ first64",
    "0.914539x",
    "0.957250x",
    "0.934600x",
    "0.953067x",
    "the runner-level wall time remains slower than baseline",
    "first64 worker sweep keeps the same correctness contract",
    "0.956003x",
    "0.912482x",
    "0.843978x",
    "batch scoreInfo work across shards",
    "Complete-record grouping is a small positive signal",
    "0.952645x",
    "0.989676x",
    "1.011415x",
    "1.022417x",
    "1.028119x",
    "1.028873x",
    "Group32 scaling keeps that small positive signal through MALAT1 first256",
    "1.029346x",
    "1.041244x",
    "1.040806x",
    "80640",
    "Full MALAT1 group32 trust runner result",
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
    "malat1_like_group32_experimental_v1",
    "characterization wrappers exercise this preset contract directly",
    "run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh",
    "audited_status = accepted",
    "digest gate failed",
    "candidate_realpath_extend_scoreinfo_groups",
    "candidate_realpath_extend_align_attempts",
    "candidate_realpath_extend_substr_seconds",
    "candidate_realpath_extend_align_seconds",
    "candidate_realpath_extend_align_fraction",
    "candidate_realpath_extend_convert_seconds",
    "candidate_realpath_extend_sort_seconds",
    "candidate_realpath_extend_filter_seconds",
    "next GASAL2/batched-extend candidate",
    "candidate_realpath_extend_align_attempts = 74,646",
    "candidate_vs_baseline ~= 0.93x",
    "candidate_realpath_extend_align_seconds ~= 10.12",
    "candidate_realpath_extend_align_fraction ~= 0.405",
    "candidate_realpath_extend_segmented_attempt_probe_requested = 0",
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested = 16",
    "candidate_realpath_extend_flush_segmented_attempt_probe_active = 64",
    "candidate_realpath_extend_flush_segmented_attempt_probe_calls = 64",
    "candidate_realpath_extend_flush_segmented_attempt_probe_attempts = 500,352",
    "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts ~= 218,570",
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds ~= 1.44",
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks = 0",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested = 16",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks = 16",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts = 638",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches = 0",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks = 0",
    "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches = 0",
    "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches = 0",
    "diagnostic replay bug",
    "sorted top `N` before threshold filtering",
    "segmented replay, full hand replay, and oracle replay all report zero triplex mismatches",
    "legacy helper re-entry can be clean",
    "larger/full task scope",
    "--replay-probe-max-tasks N",
    "`N=0` means all tasks in each flush",
    "MALAT1 first8/group32 replay cap=4",
    "replay tasks = 64",
    "replay align attempts = 2,855",
    "MALAT1 first8/group32 replay cap=16",
    "replay tasks = 256",
    "replay align attempts = 10,424",
    "MALAT1 first8/group32 replay cap=0",
    "replay tasks = 1,824",
    "replay selected attempts = 218,570",
    "replay align attempts = 74,646",
    "MALAT1 first8/group32 selected-only replay cap=0",
    "selected-only attempts = 218,570",
    "selected-only align attempts = 99,022",
    "selected-only selected scoreInfos = 31,272",
    "selected-only tasks with selected attempts = 1,752",
    "selected-only tasks with triplex = 1,348",
    "selected-only zero-triplex tasks = 476",
    "selected-only mismatch selected_empty = 5",
    "selected-only mismatch legacy_empty = 277",
    "selected-only mismatch selected_less = 28",
    "selected-only mismatch selected_more = 828",
    "selected-only mismatch same_count_diff = 36",
    "selected-only first mismatch task = 0",
    "selected-only first mismatch kind = selected_more",
    "selected-only first mismatch provenance = scoreinfo=7;start=4023;cutlength=37;sw_score=73;ref_begin=11;ref_end=30;query_begin=3460;query_end=3479",
    "selected-only scoreInfos with multiple triplexes = 845",
    "selected-only extra triplexes from repeated scoreInfo = 965",
    "selected-only triplex mismatches = 1,174",
    "decision = no-go for direct selected-only consumer",
    "MALAT1 first16/group32 replay cap=0",
    "replay tasks = 4,416",
    "replay align attempts = 186,488",
    "MALAT1 first32/group32 replay cap=0",
    "replay tasks = 8,160",
    "replay align attempts = 344,974",
    "MALAT1 first64/group32 replay cap=0",
    "replay tasks = 18,096",
    "replay align attempts = 764,324",
    "full hand replay mismatches = 0",
    "oracle replay mismatches = 0",
    "full replay of the checked first8, first16, first32, and first64 task sets",
    "most mismatches are selected-only extra triplexes rather than coverage misses",
    "first extra comes from an additional selected attempt inside scoreInfo 7",
    "breaks the legacy scoreInfo-level single-emission contract",
    "GASAL2 select calls from 7,008 to 64",
    "capped replay probe",
    "batched/GASAL2 extend attempt consumption",
    "2541.655441s",
    "1.036714x",
    "f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b",
    "strongest current MALAT1-like real runner profile",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("scoped milestone doc missing phrases: " + ", ".join(missing))

for forbidden in (
    "Current full-goal status: complete",
    "Universal replacement status: proven",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
):
    if forbidden in doc:
        raise SystemExit(f"scoped milestone doc contains forbidden phrase: {forbidden}")

for name, text in (
    ("current-state", current_state),
    ("streaming", streaming),
    ("full-goal", full_goal),
):
    for phrase in (
        "GASAL2 / GPU scoreInfo scoped feasibility checkpoint",
        "MALAT1 streaming scoreInfo trust path: scoped go",
        "NEAT1 streaming scoreInfo trust path: performance no-go",
        "Broad scoreInfo/preAlign replacement: not proven",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing scoped milestone phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-scoreinfo-scoped-milestone:\n"
    r"\tbash \./scripts/check_fasim_gasal2_scoreinfo_scoped_milestone\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-scoreinfo-scoped-milestone target")

malat1_lite_target = re.search(
    r"^check-fasim-gasal2-malat1-lite-equivalence-evidence:\n"
    r"\tbash \./scripts/check_fasim_gasal2_malat1_lite_equivalence_evidence\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_lite_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-lite-equivalence-evidence target")

malat1_tfosorted_target = re.search(
    r"^check-fasim-gasal2-malat1-tfosorted-equivalence-evidence:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_tfosorted_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-tfosorted-equivalence-evidence target")

malat1_tfosorted_full_target = re.search(
    r"^check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=670 EXPECTED_ROWS=98713 CHECK_FULL=1 REPLAY_PROBE_MAX_TASKS=0 bash \./scripts/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_tfosorted_full_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full target")

malat1_tfosorted_runtime_target = re.search(
    r"^check-fasim-gasal2-malat1-tfosorted-runtime-breakdown:\n"
    r"\tbash \./scripts/check_fasim_gasal2_malat1_tfosorted_runtime_breakdown\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_tfosorted_runtime_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-tfosorted-runtime-breakdown target")

malat1_no_probe_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime target")

malat1_no_probe_tfosorted_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 OUTPUT_MODE=tfosorted bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_tfosorted_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted target")

malat1_no_probe_first64_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 CHECK_FIRST64=1 bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_first64_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64 target")

malat1_no_probe_first128_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 CHECK_FIRST128=1 bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_first128_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128 target")

malat1_no_probe_first256_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 CHECK_FIRST256=1 bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_first256_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256 target")

malat1_no_probe_full_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=670 EXPECTED_ROWS=98713 CHECK_FULL=1 bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_full_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full target")

malat1_no_probe_full_tfosorted_target = re.search(
    r"^check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=670 EXPECTED_ROWS=98713 CHECK_FULL=1 OUTPUT_MODE=tfosorted bash \./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not malat1_no_probe_full_tfosorted_target:
    raise SystemExit("Makefile missing check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted target")

runner_char_target = re.search(
    r"^characterize-fasim-long-query-streaming-scoreinfo-trust-runner:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runner_char_target:
    raise SystemExit("Makefile missing characterize-fasim-long-query-streaming-scoreinfo-trust-runner target")

runner_worker_target = re.search(
    r"^characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_workers\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runner_worker_target:
    raise SystemExit("Makefile missing characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers target")

runner_group_target = re.search(
    r"^characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runner_group_target:
    raise SystemExit("Makefile missing characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups target")

runner_group32_target = re.search(
    r"^characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_group32_scaling\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runner_group32_target:
    raise SystemExit("Makefile missing characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling target")

runner_full_group32_target = re.search(
    r"^characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_malat1_full_group32\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runner_full_group32_target:
    raise SystemExit("Makefile missing characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32 target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-scoreinfo-scoped-milestone" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing scoped milestone dependency")
if "check-fasim-gasal2-scoreinfo-scoped-release-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing scoped release-smoke dependency")
if "check-fasim-gasal2-malat1-two-contract-product-readiness" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 two-contract product-readiness dependency")
if "check-fasim-gasal2-malat1-two-contract-recommended-runtime" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 two-contract recommended-runtime dependency")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-runner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing group32 trust runner dependency")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing audited group32 trust runner dependency")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real audited group32 trust runner dependency")
if "check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real audited NEAT1 trust runner dependency")
if "check-fasim-gasal2-malat1-lite-equivalence-evidence" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 lite-equivalence evidence dependency")
if "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 TFOsorted-equivalence evidence dependency")
if "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing MALAT1 full TFOsorted-equivalence evidence dependency")
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
if "check-fasim-gasal2-scoreinfo-scoped-milestone" not in phony_targets:
    raise SystemExit("scoped milestone target missing from .PHONY")
if "check-fasim-gasal2-malat1-lite-equivalence-evidence" not in phony_targets:
    raise SystemExit("MALAT1 lite-equivalence evidence target missing from .PHONY")
if "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence" not in phony_targets:
    raise SystemExit("MALAT1 TFOsorted-equivalence evidence target missing from .PHONY")
if "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full" not in phony_targets:
    raise SystemExit("MALAT1 full TFOsorted-equivalence evidence target missing from .PHONY")
if "check-fasim-gasal2-malat1-tfosorted-runtime-breakdown" not in phony_targets:
    raise SystemExit("MALAT1 TFOsorted runtime breakdown target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime TFOsorted target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime first64 target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime first128 target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime first256 target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime full target missing from .PHONY")
if "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted" not in phony_targets:
    raise SystemExit("MALAT1 no-probe two-contract runtime full TFOsorted target missing from .PHONY")
if "check-fasim-gasal2-scoreinfo-scoped-release-smoke" not in phony_targets:
    raise SystemExit("scoreInfo scoped release-smoke target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-runner" not in phony_targets:
    raise SystemExit("group32 trust runner target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner" not in phony_targets:
    raise SystemExit("audited group32 trust runner target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real" not in phony_targets:
    raise SystemExit("real audited group32 trust runner target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real" not in phony_targets:
    raise SystemExit("real audited NEAT1 trust runner target missing from .PHONY")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner" not in phony_targets:
    raise SystemExit("runner trust characterization target missing from .PHONY")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers" not in phony_targets:
    raise SystemExit("runner trust worker characterization target missing from .PHONY")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups" not in phony_targets:
    raise SystemExit("runner trust grouping characterization target missing from .PHONY")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling" not in phony_targets:
    raise SystemExit("runner trust group32 scaling characterization target missing from .PHONY")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32" not in phony_targets:
    raise SystemExit("runner trust full MALAT1 group32 characterization target missing from .PHONY")

for phrase in (
    "--long-query-streaming-scoreinfo-gpu-trust",
    "long_query_streaming_scoreinfo_gpu_trust_experimental_v1",
    "external_digest_gate",
    "realpath_used != tasks",
    "cpu_prealign_seconds",
    "compare_seconds",
    "candidate_vs_baseline",
    "GROUP_TARGET_RECORDS",
    "--group-target-records",
):
    if phrase not in runner_characterization:
        raise SystemExit("runner trust characterization missing phrase: " + phrase)
for phrase in (
    "REUSE_EXISTING",
    "digests_by_case",
    "GROUP_TARGET_RECORDS_LIST",
):
    if phrase not in runner_group_characterization:
        raise SystemExit("runner trust grouping characterization missing phrase: " + phrase)
PY

echo "ok"
