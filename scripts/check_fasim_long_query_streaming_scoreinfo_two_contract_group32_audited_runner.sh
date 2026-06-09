#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh"
DOC="$ROOT/docs/fasim_sharded_runner.md"
CHAR_DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_two_contract_trust_characterization.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$CHAR_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing two-contract group32 audited dependency: $path" >&2
    exit 1
  fi
done

python3 - "$WRAPPER" "$DOC" "$CHAR_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

wrapper = Path(sys.argv[1])
doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
char_doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")
real_gate = wrapper.parent / "check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real.sh"

if not wrapper.exists():
    raise SystemExit("missing two-contract group32 audited wrapper")
text = wrapper.read_text(encoding="utf-8")
if not real_gate.exists():
    raise SystemExit("missing real two-contract group32 audited gate")
real_gate_text = real_gate.read_text(encoding="utf-8")
required_wrapper = [
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
    "--replay-probe-max-tasks",
    "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1",
    "malat1_like_two_contract_group32_experimental_v1",
    "digest gate failed",
    "two_contract_used != tasks",
    "two_contract_fallbacks",
    "two_contract_score_mismatches",
    "two_contract_min_score_mismatches",
    "two_contract_scoreinfo_mismatches",
    "realpath_used != tasks",
    "cpu_scoreinfo_groups",
    "cpu_prealign_seconds",
    "compare_seconds",
    "audited_status",
    "audited_resume",
    "baseline_runner_wall_seconds",
    "candidate_runner_wall_seconds",
    "candidate_vs_baseline",
    "candidate_two_contract_total_seconds",
    "candidate_two_contract_h2d_seconds",
    "candidate_two_contract_kernel_seconds",
    "candidate_two_contract_d2h_seconds",
    "candidate_gpu_call_seconds",
    "candidate_kernel_seconds",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_seconds",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks",
    "--resume requires an accepted audit summary",
]
missing = [phrase for phrase in required_wrapper if phrase not in text]
if missing:
    raise SystemExit("two-contract group32 audited wrapper missing phrases: " + ", ".join(missing))

required_real_gate = [
    'REPLAY_PROBE_MAX_TASKS="${REPLAY_PROBE_MAX_TASKS:-1}"',
    "--replay-probe-max-tasks",
    '"$REPLAY_PROBE_MAX_TASKS"',
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff",
        "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo",
        "replay_probe_tasks=",
        "replay_probe_triplex_mismatches=",
        "replay_probe_fallbacks=",
        "selected_only_replay_probe_tasks=",
        "selected_only_replay_probe_selected_scoreinfos=",
        "selected_only_replay_probe_tasks_with_selected=",
        "selected_only_replay_probe_tasks_with_triplex=",
        "selected_only_replay_probe_zero_triplex_tasks=",
        "selected_only_replay_probe_mismatch_selected_empty=",
        "selected_only_replay_probe_mismatch_legacy_empty=",
        "selected_only_replay_probe_mismatch_selected_less=",
        "selected_only_replay_probe_mismatch_selected_more=",
        "selected_only_replay_probe_mismatch_same_count_diff=",
        "selected_only_replay_probe_first_mismatch_task=",
	    "selected_only_replay_probe_first_mismatch_kind=",
	    "selected_only_replay_probe_scoreinfos_with_multiple_triplexes=",
	    "selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo=",
        "selected_only_replay_probe_triplex_mismatches=",
        "selected_only_replay_probe_fallbacks=",
    ]
missing_real_gate = [phrase for phrase in required_real_gate if phrase not in real_gate_text]
if missing_real_gate:
    raise SystemExit(
        "real two-contract group32 audited gate missing replay probe controls: "
        + ", ".join(missing_real_gate)
    )
if real_gate_text.count('--replay-probe-max-tasks "$REPLAY_PROBE_MAX_TASKS"') < 2:
    raise SystemExit("real two-contract group32 audited gate must pass replay probe cap to fresh and resume wrapper calls")

required_runner = [
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_SELECTED_ONLY_REPLAY_PROBE",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS",
    "args.long_query_streaming_scoreinfo_gpu_flush_replay_probe_max_tasks",
]
runner_text = (wrapper.parent / "fasim_sharded_runner.py").read_text(encoding="utf-8")
for phrase in required_runner:
    if phrase not in runner_text:
        raise SystemExit("runner missing two-contract replay probe phrase: " + phrase)
if not re.search(
    r"if args\.long_query_streaming_scoreinfo_gpu_two_contract_trust:.*?"
    r"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE.*?"
    r"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_SELECTED_ONLY_REPLAY_PROBE.*?"
    r"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS",
    runner_text,
    flags=re.S,
):
    raise SystemExit("runner does not enable flush replay probe for two-contract trust preset")

required_doc = [
    "run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1",
    "malat1_like_two_contract_group32_experimental_v1",
    "audited_status = accepted",
    "digest gate failed",
    "--replay-probe-max-tasks N",
    "`N=0` means all tasks in each flush",
    "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks",
    "does not give GPU endpoint, CIGAR, traceback, or output authority",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256",
]
for name, body in (("runner doc", doc), ("two-contract characterization doc", char_doc)):
    missing_doc = [phrase for phrase in required_doc if phrase not in body]
    if missing_doc:
        raise SystemExit(f"{name} missing two-contract group32 audited phrases: " + ", ".join(missing_doc))

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing two-contract group32 audited check target")

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
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner" not in phony_targets:
    raise SystemExit("two-contract group32 audited target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real" not in phony_targets:
    raise SystemExit("real two-contract group32 audited target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64" not in phony_targets:
    raise SystemExit("real first64 two-contract group32 audited target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128" not in phony_targets:
    raise SystemExit("real first128 two-contract group32 audited target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256" not in phony_targets:
    raise SystemExit("real first256 two-contract group32 audited target missing from .PHONY")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing two-contract group32 audited dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real two-contract group32 audited dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real first64 two-contract group32 audited dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real first128 two-contract group32 audited dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real first256 two-contract group32 audited dependency")

real_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not real_target:
    raise SystemExit("Makefile missing real two-contract group32 audited check target")

first64_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=64 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not first64_target:
    raise SystemExit("Makefile missing real first64 two-contract group32 audited check target")

first128_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=128 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not first128_target:
    raise SystemExit("Makefile missing real first128 two-contract group32 audited check target")

first256_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=256 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not first256_target:
    raise SystemExit("Makefile missing real first256 two-contract group32 audited check target")
PY

WORK="$(mktemp -d "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

fake_bin="$WORK/fake_fasim_gasal2"
cat >"$fake_bin" <<'SH'
#!/usr/bin/env bash
# benchmark.fasim_gasal2_built=1
set -euo pipefail
out=""
mode="baseline"
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -O)
      out="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -z "$out" ]]; then
  echo "missing -O" >&2
  exit 2
fi
if [[ "${FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST:-0}" == "1" ]]; then
  mode="candidate"
fi
mkdir -p "$out"
score="4"
if [[ "$mode" == "candidate" && "${FAKE_FASIM_AUDIT_MISMATCH:-0}" == "1" ]]; then
  score="5"
fi
replay_tasks="${FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FLUSH_SEGMENTED_REPLAY_PROBE_MAX_TASKS:-1}"
if [[ "$replay_tasks" == "0" ]]; then
  replay_tasks="1"
fi
cat >"$out/fake-TFOsorted.lite" <<EOF
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr1	1	4	+	0	1	4	1	4	parallel	${score}	4	100	1
EOF
cat >&2 <<EOF
benchmark.fasim_gasal2_built=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds=0.000010
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds=0.000004
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority=external_digest_gate
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_tasks=${replay_tasks}
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_selected_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_align_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds=0.000003
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks=${replay_tasks}
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks=${replay_tasks}
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count=-1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance=none
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups=3
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds=0.000008
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds=0.000004
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision=two_contract_bridge_trust_active
EOF
SH
chmod +x "$fake_bin"

target="$WORK/target.fa"
rna="$WORK/rna.fa"
printf '>t1|chr1|1-4\nACGT\n>t2|chr2|1-4\nACGT\n>t3|chr3|1-4\nACGT\n' >"$target"
printf '>rna\nACGT\n' >"$rna"

"$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/pass" \
  --workers 1 \
  --replay-probe-max-tasks 2 \
  >"$WORK/pass.json"

python3 - "$WORK/pass.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload["audited_status"] != "accepted":
    raise SystemExit(f"unexpected audited_status={payload['audited_status']}")
if payload["baseline_digest"] != payload["candidate_digest"]:
    raise SystemExit("positive audit did not preserve digest")
if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1":
    raise SystemExit(f"unexpected result_contract={payload['result_contract']}")
if payload["trust_profile"] != "malat1_like_two_contract_group32_experimental_v1":
    raise SystemExit(f"unexpected trust_profile={payload['trust_profile']}")
if payload["group_target_records"] != 32:
    raise SystemExit(f"unexpected group_target_records={payload['group_target_records']}")
if payload["tasks"] != 1 or payload["two_contract_used"] != 1 or payload["realpath_used"] != 1:
    raise SystemExit("unexpected two-contract coverage")
for key in (
    "two_contract_fallbacks",
    "two_contract_score_mismatches",
    "two_contract_min_score_mismatches",
    "two_contract_scoreinfo_mismatches",
    "realpath_fallbacks",
    "cpu_scoreinfo_groups",
    "cpu_prealign_seconds",
    "compare_seconds",
):
    if payload[key] != 0:
        raise SystemExit(f"expected {key}=0, got {payload[key]}")
for key in (
    "baseline_runner_wall_seconds",
    "candidate_runner_wall_seconds",
    "candidate_vs_baseline",
    "candidate_two_contract_total_seconds",
    "candidate_two_contract_h2d_seconds",
    "candidate_two_contract_kernel_seconds",
    "candidate_two_contract_d2h_seconds",
    "candidate_gpu_call_seconds",
    "candidate_kernel_seconds",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos",
	    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex",
    "candidate_realpath_extend_flush_segmented_selected_only_replay_probe_seconds",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds",
):
    if float(payload[key]) <= 0.0:
        raise SystemExit(f"expected positive {key}, got {payload[key]}")
if payload["candidate_realpath_extend_flush_segmented_replay_probe_tasks"] != 2:
    raise SystemExit("replay-probe-max-tasks was not forwarded to candidate env")
if payload["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit("expected replay triplex mismatches to remain zero")
if payload["candidate_realpath_extend_flush_segmented_replay_probe_fallbacks"] != 0:
    raise SystemExit("expected replay fallback counter to remain zero")
if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks"] != 2:
    raise SystemExit("selected-only replay probe did not receive replay task cap")
if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit("expected selected-only replay triplex mismatches to remain zero in fake gate")
if payload["candidate_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks"] != 0:
    raise SystemExit("expected selected-only replay fallback counter to remain zero")
if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks"] != 2:
    raise SystemExit("grouped-selected replay probe did not receive replay task cap")
if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit("expected grouped-selected replay triplex mismatches to remain zero in fake gate")
if payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks"] != 0:
    raise SystemExit("expected grouped-selected replay fallback counter to remain zero")
grouped_selected_mismatch_keys = (
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more",
    "candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff",
)
grouped_selected_mismatch_total = sum(payload[key] for key in grouped_selected_mismatch_keys)
if grouped_selected_mismatch_total != payload["candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches"]:
    raise SystemExit("grouped-selected replay mismatch classes do not sum to mismatch count")
PY

"$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/pass" \
  --workers 1 \
  --replay-probe-max-tasks 2 \
  --resume \
  >"$WORK/resume.json"

python3 - "$WORK/resume.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload["audited_resume"] is not True:
    raise SystemExit("resume summary did not record audited_resume=true")
if payload["audited_status"] != "accepted":
    raise SystemExit(f"unexpected resumed audited_status={payload['audited_status']}")
PY

if FAKE_FASIM_AUDIT_MISMATCH=1 "$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/fail" \
  --workers 1 \
  >"$WORK/fail.json" 2>"$WORK/fail.stderr"; then
  echo "expected audited wrapper to reject digest mismatch" >&2
  exit 1
fi
grep -q "digest gate failed" "$WORK/fail.stderr"

if "$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/no-summary" \
  --workers 1 \
  --resume \
  >"$WORK/no-summary.json" 2>"$WORK/no-summary.stderr"; then
  echo "expected audited wrapper to reject resume without accepted summary" >&2
  exit 1
fi
grep -q -- "--resume requires an accepted audit summary" "$WORK/no-summary.stderr"

echo "ok"
