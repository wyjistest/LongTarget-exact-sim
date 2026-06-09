#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="$ROOT/scripts/run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh"
DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$WRAPPER" "$DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing segmented extend-attempt probe dependency: $path" >&2
    exit 1
  fi
done

python3 - "$WRAPPER" "$DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

wrapper = Path(sys.argv[1]).read_text(encoding="utf-8")
doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_wrapper = [
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
]
missing = [phrase for phrase in required_wrapper if phrase not in wrapper]
if missing:
    raise SystemExit("audited wrapper missing segmented probe phrases: " + ", ".join(missing))

required_doc = [
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested",
    "candidate_realpath_extend_flush_segmented_attempt_probe_segments",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "current short-query GASAL2 select API",
    "flush-level segmented extend-attempt probe",
    "flush-level segmented replay probe",
]
missing_doc = [phrase for phrase in required_doc if phrase not in doc]
if missing_doc:
    raise SystemExit("current-state doc missing segmented probe phrases: " + ", ".join(missing_doc))

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-trust-group32-segmented-probe-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_segmented_probe_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing segmented probe runner check target")

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
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-segmented-probe-runner" not in phony_targets:
    raise SystemExit("segmented probe runner target missing from .PHONY")
PY

WORK="$(mktemp -d "$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_trust_group32_segmented_probe_runner.XXXXXX")"
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
cat >"$out/fake-TFOsorted.lite" <<EOF
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr1	1	4	+	0	1	4	1	4	parallel	${score}	4	100	1
EOF
cat >&2 <<'EOF'
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
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds=0.000004
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_substr_seconds=0.0000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds=0.000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_convert_seconds=0.0000002
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_sort_seconds=0.0000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_filter_seconds=0.0000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_active=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_calls=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_attempts=2
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_selected_attempts=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_seconds=0.000001
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_fallbacks=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_flushes=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_segments=4
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_calls=4
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_attempts=8
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_selected_attempts=3
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_seconds=0.000003
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_fallbacks=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_requested=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_active=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_tasks=1
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_selected_attempts=3
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_align_attempts=3
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_triplex_mismatches=0
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds=0.000004
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_fallbacks=0
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
  >"$WORK/pass.json"

python3 - "$WORK/pass.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload["audited_status"] != "accepted":
    raise SystemExit(f"unexpected audited status: {payload['audited_status']}")
if payload["baseline_digest"] != payload["candidate_digest"]:
    raise SystemExit("segmented probe audit did not preserve digest")
for key in (
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
        raise SystemExit(f"expected positive {key}, got {payload[key]}")
if payload["candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks"] != 0:
    raise SystemExit(
        "expected fallback-clean flush segmented probe, got "
        f"{payload['candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks']}"
    )
if payload["candidate_realpath_extend_flush_segmented_replay_probe_fallbacks"] != 0:
    raise SystemExit(
        "expected fallback-clean flush segmented replay probe, got "
        f"{payload['candidate_realpath_extend_flush_segmented_replay_probe_fallbacks']}"
    )
if payload["candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches"] != 0:
    raise SystemExit(
        "expected triplex-clean flush segmented replay probe, got "
        f"{payload['candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches']}"
    )
print("ok")
PY
