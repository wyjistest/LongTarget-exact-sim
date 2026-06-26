#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh"
ANALYZER="$ROOT/scripts/analyze_fasim_gasal2_task_frontier_proof.py"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase3_cigar_nt_prefilter_shadow"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -x "$RUNNER" ]]; then
  echo "missing NEAT1 audited runner gate: $RUNNER" >&2
  exit 1
fi
if [[ ! -f "$ANALYZER" ]]; then
  echo "missing task frontier analyzer: $ANALYZER" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK"

NEAT1_RECORD_LIMIT=1 \
REPLAY_PROBE_MAX_TASKS=1 \
BUILD_BIN=0 \
BIN="$BIN" \
WORK="$WORK/neat1_first1" \
FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_SHADOW=1 \
  bash "$RUNNER" >"$WORK/stdout.log"

python3 - "$WORK/neat1_first1/fresh.json" \
  "$WORK/neat1_first1/audit/candidate/stderr.log" \
  "$ANALYZER" \
  >"$WORK/summary.txt" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path

fresh_path = Path(sys.argv[1])
stderr_path = Path(sys.argv[2])
analyzer = Path(sys.argv[3])
fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
stderr = stderr_path.read_text(encoding="utf-8", errors="replace")

if fresh["audited_status"] != "accepted":
    raise SystemExit(f"unexpected audited_status={fresh['audited_status']}")
if fresh["baseline_digest"] != fresh["candidate_digest"]:
    raise SystemExit("normal output digest changed under Phase 3 shadow")

bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

def metric(name: str) -> str:
    key = "fasim_gasal2_phase3_cigar_nt_prefilter_" + name
    if key not in bench:
        raise SystemExit(f"missing phase3_cigar_nt_prefilter_{name}")
    return bench[key]

requested = int(metric("requested"))
active = int(metric("active"))
alignments_seen = int(metric("alignments_seen"))
cigar_lt_ntmin = int(metric("cigar_lt_ntmin"))
legacy_nt_lt_ntmin = int(metric("legacy_nt_lt_ntmin"))
agree_lt_ntmin = int(metric("agree_lt_ntmin"))
disagree_lt_ntmin = int(metric("disagree_lt_ntmin"))
candidate_skippable = int(metric("candidate_skippable"))
false_negative_rows = int(metric("candidate_false_negative_rows"))
task_frontier_equal = int(metric("task_frontier_equal"))
task_frontier_safety = metric("task_frontier_safety")
proof_gate = metric("real_prune_proof_gate")
baseline_path = Path(metric("baseline_triplex_path"))
candidate_path = Path(metric("candidate_triplex_path"))
projected_saved = float(metric("convert_seconds_projected_saved"))

if requested != 1 or active != 1:
    raise SystemExit(
        f"expected requested=active=1, got requested={requested} active={active}"
    )
if alignments_seen <= 0:
    raise SystemExit(f"expected alignments_seen > 0, got {alignments_seen}")
if agree_lt_ntmin + disagree_lt_ntmin != alignments_seen:
    raise SystemExit(
        "lt-ntMin accounting does not cover all alignments: "
        f"agree={agree_lt_ntmin} disagree={disagree_lt_ntmin} "
        f"alignments={alignments_seen}"
    )
if cigar_lt_ntmin != legacy_nt_lt_ntmin:
    raise SystemExit(
        f"expected same CIGAR/legacy lt-ntMin counts, got "
        f"cigar={cigar_lt_ntmin} legacy={legacy_nt_lt_ntmin}"
    )
if disagree_lt_ntmin != 0:
    raise SystemExit(f"CIGAR/legacy ntMin disagreement: {disagree_lt_ntmin}")
if false_negative_rows != 0:
    raise SystemExit(f"candidate false-negative rows: {false_negative_rows}")
if task_frontier_equal != 1 or task_frontier_safety != "safe":
    raise SystemExit(
        f"frontier not safe: equal={task_frontier_equal} "
        f"safety={task_frontier_safety}"
    )
if proof_gate != "pass":
    raise SystemExit(f"real_prune_proof_gate={proof_gate}")
if candidate_skippable != cigar_lt_ntmin:
    raise SystemExit(
        f"candidate_skippable={candidate_skippable} "
        f"cigar_lt_ntmin={cigar_lt_ntmin}"
    )
if projected_saved < 0.0:
    raise SystemExit(f"negative projected saved seconds: {projected_saved}")
for path in (baseline_path, candidate_path):
    if not path.is_file():
        raise SystemExit(f"missing task frontier artifact: {path}")

result = subprocess.run(
    [
        sys.executable,
        str(analyzer),
        "--baseline",
        str(baseline_path),
        "--candidate",
        str(candidate_path),
    ],
    text=True,
    check=True,
    stdout=subprocess.PIPE,
)
proof = dict(
    line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
)
if proof.get("task_row_set_equal") != "1":
    raise SystemExit("analyzer task_row_set_equal did not pass")
if proof.get("task_frontier_safety") != "safe":
    raise SystemExit("analyzer task_frontier_safety did not pass")
if proof.get("real_prune_proof_gate") != "pass":
    raise SystemExit("analyzer real_prune_proof_gate did not pass")

digest = metric("candidate_triplex_digest")
if not re.fullmatch(r"[0-9a-f]{16}", digest):
    raise SystemExit(f"unexpected candidate digest: {digest}")

print("phase3_cigar_nt_prefilter_requested=1")
print("phase3_cigar_nt_prefilter_active=1")
print(f"phase3_cigar_nt_prefilter_alignments_seen={alignments_seen}")
print(f"phase3_cigar_nt_prefilter_cigar_lt_ntmin={cigar_lt_ntmin}")
print(f"phase3_cigar_nt_prefilter_legacy_nt_lt_ntmin={legacy_nt_lt_ntmin}")
print("phase3_cigar_nt_prefilter_disagree_lt_ntmin=0")
print("phase3_cigar_nt_prefilter_candidate_false_negative_rows=0")
print("phase3_cigar_nt_prefilter_task_frontier_equal=1")
print("phase3_cigar_nt_prefilter_task_frontier_safety=safe")
print("phase3_cigar_nt_prefilter_real_prune_proof_gate=pass")
print(f"phase3_cigar_nt_prefilter_baseline_triplex_path={baseline_path}")
print(f"phase3_cigar_nt_prefilter_candidate_triplex_path={candidate_path}")
print(f"phase3_cigar_nt_prefilter_candidate_triplex_digest={digest}")
print("ok")
PY

cat "$WORK/summary.txt"
