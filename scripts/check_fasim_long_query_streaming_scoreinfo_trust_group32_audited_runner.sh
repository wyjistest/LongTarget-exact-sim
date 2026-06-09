#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh"
DOC="$ROOT/docs/fasim_sharded_runner.md"
MILESTONE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md"
CURRENT_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$MILESTONE_DOC" "$CURRENT_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing audited group32 dependency: $path" >&2
    exit 1
  fi
done

python3 - "$WRAPPER" "$DOC" "$MILESTONE_DOC" "$CURRENT_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

wrapper = Path(sys.argv[1])
doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
milestone = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
current = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

if not wrapper.exists():
    raise SystemExit("missing audited group32 wrapper")
text = wrapper.read_text(encoding="utf-8")
required_wrapper = [
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "--replay-probe-max-tasks",
    "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
    "malat1_like_group32_experimental_v1",
    "digest gate failed",
    "realpath_used != tasks",
    "cpu_prealign_seconds",
    "compare_seconds",
    "audited_status",
    "baseline_runner_wall_seconds",
    "candidate_runner_wall_seconds",
    "candidate_vs_baseline",
    "candidate_gpu_scoreinfo_total_seconds",
    "candidate_gpu_scoreinfo_call_seconds",
    "candidate_gpu_scoreinfo_kernel_seconds",
    "candidate_non_gpu_wall_seconds",
    "candidate_gpu_scoreinfo_wall_fraction",
    "candidate_gpu_scoreinfo_call_fraction",
    "candidate_realpath_extend_seconds",
    "candidate_realpath_extend_calls",
    "candidate_realpath_extend_fraction",
    "candidate_realpath_extend_scoreinfo_groups",
    "candidate_realpath_extend_align_attempts",
    "candidate_realpath_extend_align_seconds",
    "candidate_realpath_extend_align_fraction",
    "candidate_realpath_extend_substr_seconds",
    "candidate_realpath_extend_convert_seconds",
    "candidate_realpath_extend_sort_seconds",
    "candidate_realpath_extend_filter_seconds",
    "candidate_realpath_extend_attempt_probe_requested",
    "candidate_realpath_extend_attempt_probe_active",
    "candidate_realpath_extend_attempt_probe_calls",
    "candidate_realpath_extend_attempt_probe_attempts",
    "candidate_realpath_extend_attempt_probe_selected_attempts",
    "candidate_realpath_extend_attempt_probe_seconds",
    "candidate_realpath_extend_attempt_probe_fallbacks",
    "candidate_realpath_extend_segmented_attempt_probe_requested",
    "candidate_realpath_extend_segmented_attempt_probe_active",
    "candidate_realpath_extend_segmented_attempt_probe_segments",
    "candidate_realpath_extend_segmented_attempt_probe_calls",
    "candidate_realpath_extend_segmented_attempt_probe_attempts",
    "candidate_realpath_extend_segmented_attempt_probe_selected_attempts",
    "candidate_realpath_extend_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested",
    "candidate_realpath_extend_flush_segmented_attempt_probe_active",
    "candidate_realpath_extend_flush_segmented_attempt_probe_flushes",
    "candidate_realpath_extend_flush_segmented_attempt_probe_segments",
    "candidate_realpath_extend_flush_segmented_attempt_probe_calls",
    "candidate_realpath_extend_flush_segmented_attempt_probe_attempts",
    "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
    "candidate_realpath_extend_flush_full_replay_probe_requested",
    "candidate_realpath_extend_flush_full_replay_probe_active",
    "candidate_realpath_extend_flush_full_replay_probe_tasks",
    "candidate_realpath_extend_flush_full_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_full_replay_probe_fallbacks",
    "candidate_realpath_extend_flush_full_replay_probe_seconds",
    "candidate_realpath_extend_flush_oracle_replay_probe_requested",
    "candidate_realpath_extend_flush_oracle_replay_probe_active",
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
    "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_oracle_replay_probe_seconds",
    "candidate_post_scoreinfo_unattributed_seconds",
    "candidate_post_scoreinfo_unattributed_fraction",
    "--resume",
    "resumed_shards",
    "--resume requires an accepted audit summary",
]
missing = [phrase for phrase in required_wrapper if phrase not in text]
if missing:
    raise SystemExit("audited wrapper missing phrases: " + ", ".join(missing))

required_doc = [
    "run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh",
    "audited_status = accepted",
    "--replay-probe-max-tasks N",
    "0` means all tasks in each flush",
    "--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks",
    "does not give GPU endpoint, CIGAR, traceback, or output authority",
    "candidate_vs_baseline",
    "audited_resume = true",
    "resumed_shards",
    "digest gate failed",
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "external digest gate",
    "candidate_realpath_extend_scoreinfo_groups",
    "candidate_realpath_extend_align_attempts",
    "candidate_realpath_extend_substr_seconds",
    "candidate_realpath_extend_align_seconds",
    "candidate_realpath_extend_align_fraction",
    "candidate_realpath_extend_convert_seconds",
    "candidate_realpath_extend_sort_seconds",
    "candidate_realpath_extend_filter_seconds",
    "candidate_realpath_extend_attempt_probe_requested",
    "candidate_realpath_extend_attempt_probe_attempts",
    "candidate_realpath_extend_attempt_probe_seconds",
    "candidate_realpath_extend_attempt_probe_fallbacks",
    "candidate_realpath_extend_segmented_attempt_probe_requested",
    "candidate_realpath_extend_segmented_attempt_probe_segments",
    "candidate_realpath_extend_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested",
    "candidate_realpath_extend_flush_segmented_attempt_probe_segments",
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real",
]
for name, body in (
    ("runner doc", doc),
    ("milestone doc", milestone),
    ("current-state doc", current),
):
    missing_doc = [phrase for phrase in required_doc if phrase not in body]
    if missing_doc:
        raise SystemExit(f"{name} missing audited wrapper phrases: " + ", ".join(missing_doc))

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing audited group32 check target")

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
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner" not in phony_targets:
    raise SystemExit("audited group32 target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real" not in phony_targets:
    raise SystemExit("real audited group32 target missing from .PHONY")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing audited group32 dependency")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing real audited group32 dependency")

real_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner_real\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not real_target:
    raise SystemExit("Makefile missing real audited group32 check target")

cpp = (wrapper.parent.parent / "fasim" / "Fasim-LongTarget.cpp").read_text(
    encoding="utf-8"
)
if re.search(
    r"replayIndex\s*<\s*replayTriplexes\.size\(\)\s*&&\s*"
    r"replayFilteredTriplexes\.size\(\)\s*<\s*N",
    cpp,
    flags=re.S,
):
    raise SystemExit(
        "hand replay filter must match fastSIM_extend_from_scoreinfo: "
        "inspect only the sorted top N before threshold filtering"
    )
if re.search(
    r"replayIndex\s*<\s*replayAnnotatedTriplexes\.size\(\)\s*&&\s*"
    r"replayFilteredTriplexes\.size\(\)\s*<\s*N",
    cpp,
    flags=re.S,
):
    raise SystemExit(
        "segmented hand replay filter must match fastSIM_extend_from_scoreinfo: "
        "inspect only the sorted top N before threshold filtering"
    )
PY

WORK="$(mktemp -d "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner.XXXXXX")"
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
case "${FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST:-0}" in
  1) mode="candidate" ;;
esac
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
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_unsupported=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority=external_digest_gate
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_calls=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_substr_seconds=0.0000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds=0.000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_convert_seconds=0.0000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_sort_seconds=0.0000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_filter_seconds=0.0000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_calls=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_selected_attempts=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_seconds=0.000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_segments=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_calls=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_attempts=4
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_selected_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_flushes=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_segments=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_calls=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_attempts=4
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_selected_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_tasks=${replay_tasks}
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_selected_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_align_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds=0.000003
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_tasks=${replay_tasks}
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_align_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_seconds=0.000003
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_tasks=${replay_tasks}
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_seconds=0.000003
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds=0.000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds=0.0000008
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds=0.0000007
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
    raise SystemExit(f"unexpected audited status: {payload['audited_status']}")
if payload["baseline_digest"] != payload["candidate_digest"]:
    raise SystemExit("positive audit did not preserve digest")
if payload["result_contract"] != "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1":
    raise SystemExit(f"unexpected contract: {payload['result_contract']}")
if payload["trust_profile"] != "malat1_like_group32_experimental_v1":
    raise SystemExit(f"unexpected profile: {payload['trust_profile']}")
if payload["group_target_records"] != 32:
    raise SystemExit(f"unexpected group_target_records: {payload['group_target_records']}")
for key in (
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_full_replay_probe_tasks",
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
):
    if payload[key] != 2:
        raise SystemExit(f"replay probe cap did not propagate to {key}: {payload[key]}")
if payload["tasks"] != payload["realpath_used"]:
    raise SystemExit("realpath coverage mismatch")
if payload["realpath_fallbacks"] != 0:
    raise SystemExit("unexpected realpath fallback")
if payload["cpu_prealign_seconds"] != 0 or payload["compare_seconds"] != 0:
    raise SystemExit("candidate should not retain CPU preAlign/compare hot path")
for key in ("baseline_runner_wall_seconds", "candidate_runner_wall_seconds", "candidate_vs_baseline"):
    if float(payload[key]) <= 0.0:
        raise SystemExit(f"expected positive {key}, got {payload[key]}")
for key in (
    "candidate_gpu_scoreinfo_total_seconds",
    "candidate_gpu_scoreinfo_call_seconds",
    "candidate_gpu_scoreinfo_kernel_seconds",
    "candidate_gpu_scoreinfo_wall_fraction",
    "candidate_gpu_scoreinfo_call_fraction",
    "candidate_realpath_extend_seconds",
    "candidate_realpath_extend_calls",
    "candidate_realpath_extend_fraction",
    "candidate_realpath_extend_scoreinfo_groups",
    "candidate_realpath_extend_align_attempts",
    "candidate_realpath_extend_align_seconds",
    "candidate_realpath_extend_align_fraction",
    "candidate_realpath_extend_attempt_probe_requested",
    "candidate_realpath_extend_attempt_probe_active",
    "candidate_realpath_extend_attempt_probe_calls",
    "candidate_realpath_extend_attempt_probe_attempts",
    "candidate_realpath_extend_attempt_probe_selected_attempts",
    "candidate_realpath_extend_attempt_probe_seconds",
    "candidate_realpath_extend_segmented_attempt_probe_requested",
    "candidate_realpath_extend_segmented_attempt_probe_active",
    "candidate_realpath_extend_segmented_attempt_probe_segments",
    "candidate_realpath_extend_segmented_attempt_probe_calls",
    "candidate_realpath_extend_segmented_attempt_probe_attempts",
    "candidate_realpath_extend_segmented_attempt_probe_selected_attempts",
    "candidate_realpath_extend_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested",
    "candidate_realpath_extend_flush_segmented_attempt_probe_active",
    "candidate_realpath_extend_flush_segmented_attempt_probe_flushes",
    "candidate_realpath_extend_flush_segmented_attempt_probe_segments",
    "candidate_realpath_extend_flush_segmented_attempt_probe_calls",
    "candidate_realpath_extend_flush_segmented_attempt_probe_attempts",
    "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
    "candidate_realpath_extend_flush_full_replay_probe_requested",
    "candidate_realpath_extend_flush_full_replay_probe_active",
    "candidate_realpath_extend_flush_full_replay_probe_tasks",
    "candidate_realpath_extend_flush_full_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_full_replay_probe_seconds",
    "candidate_realpath_extend_flush_oracle_replay_probe_requested",
    "candidate_realpath_extend_flush_oracle_replay_probe_active",
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
    "candidate_realpath_extend_flush_oracle_replay_probe_seconds",
):
    if float(payload[key]) <= 0.0:
        raise SystemExit(f"expected positive {key}, got {payload[key]}")
for key in (
    "candidate_realpath_extend_substr_seconds",
    "candidate_realpath_extend_convert_seconds",
    "candidate_realpath_extend_sort_seconds",
    "candidate_realpath_extend_filter_seconds",
    "candidate_realpath_extend_attempt_probe_fallbacks",
    "candidate_realpath_extend_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
    "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_full_replay_probe_fallbacks",
    "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches",
):
    if float(payload[key]) < 0.0:
        raise SystemExit(f"expected non-negative {key}, got {payload[key]}")
for key in (
    "candidate_post_scoreinfo_unattributed_seconds",
    "candidate_post_scoreinfo_unattributed_fraction",
):
    if float(payload[key]) <= 0.0:
        raise SystemExit(f"expected positive {key}, got {payload[key]}")
if float(payload["candidate_non_gpu_wall_seconds"]) < 0.0:
    raise SystemExit(
        "expected non-negative candidate_non_gpu_wall_seconds, got "
        f"{payload['candidate_non_gpu_wall_seconds']}"
    )
PY

"$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/full_replay" \
  --workers 1 \
  --replay-probe-max-tasks 0 \
  >"$WORK/full_replay.json"

python3 - "$WORK/full_replay.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload["audited_status"] != "accepted":
    raise SystemExit(f"unexpected full replay audited status: {payload['audited_status']}")
for key in (
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_full_replay_probe_tasks",
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
):
    if payload[key] != payload["tasks"]:
        raise SystemExit(
            f"replay probe cap=0 did not request full task coverage for {key}: "
            f"{payload[key]} != {payload['tasks']}"
        )
PY

"$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/pass" \
  --workers 1 \
  --replay-probe-max-tasks 2 \
  --resume \
  >"$WORK/pass_resume.json"

python3 - "$WORK/pass_resume.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload["audited_status"] != "accepted":
    raise SystemExit(f"unexpected resumed audited status: {payload['audited_status']}")
if payload["audited_resume"] is not True:
    raise SystemExit("resume summary did not record audited_resume=true")
if payload["baseline_resumed_shards_count"] != 1:
    raise SystemExit(
        f"expected one resumed baseline shard, got {payload['baseline_resumed_shards_count']}"
    )
if payload["candidate_resumed_shards_count"] != 1:
    raise SystemExit(
        f"expected one resumed candidate shard, got {payload['candidate_resumed_shards_count']}"
    )
if payload["baseline_digest"] != payload["candidate_digest"]:
    raise SystemExit("resumed audit did not preserve digest")
for key in (
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_full_replay_probe_tasks",
    "candidate_realpath_extend_flush_oracle_replay_probe_tasks",
):
    if payload[key] != 2:
        raise SystemExit(f"resumed replay probe cap did not propagate to {key}: {payload[key]}")
for key in ("baseline_runner_wall_seconds", "candidate_runner_wall_seconds", "candidate_vs_baseline"):
    if float(payload[key]) <= 0.0:
        raise SystemExit(f"expected positive resumed {key}, got {payload[key]}")
for key in (
    "candidate_gpu_scoreinfo_total_seconds",
    "candidate_gpu_scoreinfo_call_seconds",
    "candidate_gpu_scoreinfo_kernel_seconds",
    "candidate_gpu_scoreinfo_wall_fraction",
    "candidate_gpu_scoreinfo_call_fraction",
    "candidate_realpath_extend_seconds",
    "candidate_realpath_extend_calls",
    "candidate_realpath_extend_fraction",
    "candidate_realpath_extend_scoreinfo_groups",
    "candidate_realpath_extend_align_attempts",
    "candidate_realpath_extend_align_seconds",
    "candidate_realpath_extend_align_fraction",
    "candidate_realpath_extend_attempt_probe_requested",
    "candidate_realpath_extend_attempt_probe_active",
    "candidate_realpath_extend_attempt_probe_calls",
    "candidate_realpath_extend_attempt_probe_attempts",
    "candidate_realpath_extend_attempt_probe_selected_attempts",
    "candidate_realpath_extend_attempt_probe_seconds",
    "candidate_realpath_extend_segmented_attempt_probe_requested",
    "candidate_realpath_extend_segmented_attempt_probe_active",
    "candidate_realpath_extend_segmented_attempt_probe_segments",
    "candidate_realpath_extend_segmented_attempt_probe_calls",
    "candidate_realpath_extend_segmented_attempt_probe_attempts",
    "candidate_realpath_extend_segmented_attempt_probe_selected_attempts",
    "candidate_realpath_extend_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested",
    "candidate_realpath_extend_flush_segmented_attempt_probe_active",
    "candidate_realpath_extend_flush_segmented_attempt_probe_flushes",
    "candidate_realpath_extend_flush_segmented_attempt_probe_segments",
    "candidate_realpath_extend_flush_segmented_attempt_probe_calls",
    "candidate_realpath_extend_flush_segmented_attempt_probe_attempts",
    "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_active",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts",
    "candidate_realpath_extend_flush_segmented_replay_probe_seconds",
):
    if float(payload[key]) <= 0.0:
        raise SystemExit(f"expected positive resumed {key}, got {payload[key]}")
for key in (
    "candidate_realpath_extend_substr_seconds",
    "candidate_realpath_extend_convert_seconds",
    "candidate_realpath_extend_sort_seconds",
    "candidate_realpath_extend_filter_seconds",
    "candidate_realpath_extend_attempt_probe_fallbacks",
    "candidate_realpath_extend_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks",
):
    if float(payload[key]) < 0.0:
        raise SystemExit(f"expected non-negative resumed {key}, got {payload[key]}")
for key in (
    "candidate_post_scoreinfo_unattributed_seconds",
    "candidate_post_scoreinfo_unattributed_fraction",
):
    if float(payload[key]) < 0.0:
        raise SystemExit(f"expected non-negative resumed {key}, got {payload[key]}")
if float(payload["candidate_non_gpu_wall_seconds"]) < 0.0:
    raise SystemExit(
        "expected non-negative resumed candidate_non_gpu_wall_seconds, got "
        f"{payload['candidate_non_gpu_wall_seconds']}"
    )
PY

set +e
"$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/missing_resume" \
  --workers 1 \
  --resume \
  >"$WORK/missing_resume.stdout" 2>"$WORK/missing_resume.stderr"
status="$?"
set -e
if [[ "$status" == "0" ]]; then
  echo "expected audited wrapper to reject resume without accepted summary" >&2
  exit 1
fi
grep -q -- "--resume requires an accepted audit summary" "$WORK/missing_resume.stderr"

set +e
FAKE_FASIM_AUDIT_MISMATCH=1 "$WRAPPER" \
  --fasim-bin "$fake_bin" \
  --target "$target" \
  --rna "$rna" \
  --work-dir "$WORK/fail" \
  --workers 1 \
  >"$WORK/fail.stdout" 2>"$WORK/fail.stderr"
status="$?"
set -e
if [[ "$status" == "0" ]]; then
  echo "expected audited wrapper to fail closed on digest mismatch" >&2
  exit 1
fi
grep -q "digest gate failed" "$WORK/fail.stderr"

echo "ok"
