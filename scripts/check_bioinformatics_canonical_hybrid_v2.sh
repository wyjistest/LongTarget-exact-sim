#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_bioinformatics_canonical_hybrid_v2}"
CPU_BIN="$WORK/fasim_longtarget_x86"
HYBRID_BIN="$WORK/fasim_longtarget_gasal2"
QUERY="$ROOT/reproduce/bioinformatics/holdout_inputs/queries/hq10_ENSG00000178248_ENST00000785836.fa"
TARGET="$ROOT/reproduce/bioinformatics/holdout_inputs/targets/ht02_ENSG00000198722_chr9_35159829_35162329.fa"

rm -rf "$WORK"
mkdir -p "$WORK/authority" "$WORK/candidate" "$WORK/hybrid"

python3 -m json.tool \
  "$ROOT/schemas/canonical_hybrid_v2_attempt_telemetry.schema.json" >/dev/null
python3 -m py_compile \
  "$ROOT/scripts/canonical_hybrid_v2_telemetry.py" \
  "$ROOT/scripts/freeze_bioinformatics_canonical_hybrid_v2.py" \
  "$ROOT/reproduce/bioinformatics/run_canonical_hybrid_v2.py" \
  "$ROOT/tests/check_canonical_hybrid_v2.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_canonical_hybrid_v2.py"

mkdir -p "$WORK/comparator-snapshot"
cp \
  "$ROOT/scripts/compare_fasim_segmented_contract.py" \
  "$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py" \
  "$ROOT/scripts/fasim_tfo_archive.py" \
  "$WORK/comparator-snapshot/"
env -i PATH="$PATH" PYTHONDONTWRITEBYTECODE=1 \
  python3 "$WORK/comparator-snapshot/compare_fasim_segmented_contract.py" --help \
  >/dev/null

make -C "$ROOT" build-fasim FASIM_TARGET="$CPU_BIN"
make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$HYBRID_BIN"

clean_fasim_environment() {
  local name
  while IFS= read -r name; do
    unset "$name"
  done < <(compgen -v | awk '/^FASIM_/')
  "$@"
}

clean_fasim_environment env \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  "$CPU_BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -O "$WORK/authority" \
  >"$WORK/authority.stdout.log" 2>"$WORK/authority.stderr.log"

clean_fasim_environment env \
  CUDA_VISIBLE_DEVICES=1 \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
  FASIM_ALIGN_GASAL2_STREAMS=3 \
  FASIM_ALIGN_GASAL2_BATCH=20000 \
  "$HYBRID_BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -O "$WORK/candidate" \
  >"$WORK/candidate.stdout.log" 2>"$WORK/candidate.stderr.log"

candidate_output="$(find "$WORK/candidate" -maxdepth 1 -type f -name '*TFOsorted')"
expected_candidate_sha="$(awk -F '\t' \
  '$1 == "hq10_ht02__repeat00" && $2 == "gpu_traceback" {print $4}' \
  "$ROOT/paper/bioinformatics/phase2_traceback_replay.tsv")"
test -n "$expected_candidate_sha"
test "$(sha256sum "$candidate_output" | awk '{print $1}')" = "$expected_candidate_sha"
if grep -q 'benchmark.fasim_canonical_hybrid_v2_requested=' "$WORK/candidate.stderr.log"; then
  echo "default candidate unexpectedly activated canonical-hybrid-v2 telemetry" >&2
  exit 1
fi

clean_fasim_environment env \
  CUDA_VISIBLE_DEVICES=1 \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
  FASIM_ALIGN_GASAL2_STREAMS=3 \
  FASIM_ALIGN_GASAL2_BATCH=20000 \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1 \
  FASIM_CANONICAL_HYBRID_V2=1 \
  FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH="$WORK/hybrid-attempts.tsv" \
  "$HYBRID_BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -O "$WORK/hybrid" \
  >"$WORK/hybrid.stdout.log" 2>"$WORK/hybrid.stderr.log"

authority_output="$(find "$WORK/authority" -maxdepth 1 -type f -name '*TFOsorted')"
hybrid_output="$(find "$WORK/hybrid" -maxdepth 1 -type f -name '*TFOsorted')"
cmp "$authority_output" "$hybrid_output"

PYTHONDONTWRITEBYTECODE=1 python3 - \
  "$ROOT" "$WORK/hybrid-attempts.tsv" "$hybrid_output" "$WORK/hybrid.stderr.log" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from canonical_hybrid_v2_telemetry import validate_attempt

summary = validate_attempt(
    Path(sys.argv[2]),
    Path(sys.argv[3]),
    Path(sys.argv[4]).read_text(encoding="utf-8"),
)
if summary["selected_attempts"] != summary["cpu_traceback_calls"]:
    raise SystemExit("selected/CPU traceback count drift")
if summary["output_rows"] < 1:
    raise SystemExit("hybrid smoke emitted no rows")
print(json.dumps(summary, indent=2, sort_keys=True))
PY

printf 'sentinel\n' >"$WORK/existing-telemetry.tsv"
existing_sha="$(sha256sum "$WORK/existing-telemetry.tsv" | awk '{print $1}')"
set +e
clean_fasim_environment env \
  CUDA_VISIBLE_DEVICES=1 \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1 \
  FASIM_CANONICAL_HYBRID_V2=1 \
  FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH="$WORK/existing-telemetry.tsv" \
  "$HYBRID_BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -O "$WORK/existing-path-output" \
  >"$WORK/existing-path.stdout.log" 2>"$WORK/existing-path.stderr.log"
existing_rc=$?
set -e
if [[ "$existing_rc" -eq 0 ]]; then
  echo "canonical hybrid accepted an existing telemetry path" >&2
  exit 1
fi
test "$existing_sha" = "$(sha256sum "$WORK/existing-telemetry.tsv" | awk '{print $1}')"
grep -q 'failure_reason=telemetry_path_exists' "$WORK/existing-path.stderr.log"

set +e
clean_fasim_environment env \
  CUDA_VISIBLE_DEVICES=1 \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  FASIM_CANONICAL_HYBRID_V2=1 \
  FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH="$WORK/missing-cpu.tsv" \
  "$HYBRID_BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -O "$WORK/missing-cpu-output" \
  >"$WORK/missing-cpu.stdout.log" 2>"$WORK/missing-cpu.stderr.log"
missing_cpu_rc=$?
set -e
if [[ "$missing_cpu_rc" -eq 0 ]]; then
  echo "canonical hybrid ran without selected CPU traceback" >&2
  exit 1
fi
grep -q 'failure_reason=cpu_traceback_not_enabled' "$WORK/missing-cpu.stderr.log"

set +e
clean_fasim_environment env \
  CUDA_VISIBLE_DEVICES=1 \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1 \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK_ALL=1 \
  FASIM_CANONICAL_HYBRID_V2=1 \
  FASIM_CANONICAL_HYBRID_V2_TELEMETRY_PATH="$WORK/forbidden-all.tsv" \
  "$HYBRID_BIN" -f1 "$TARGET" -f2 "$QUERY" -r 0 -O "$WORK/forbidden-all-output" \
  >"$WORK/forbidden-all.stdout.log" 2>"$WORK/forbidden-all.stderr.log"
forbidden_all_rc=$?
set -e
if [[ "$forbidden_all_rc" -eq 0 ]]; then
  echo "canonical hybrid accepted complete CPU traceback-all mode" >&2
  exit 1
fi
grep -q 'failure_reason=complete_cpu_authority_forbidden' "$WORK/forbidden-all.stderr.log"

test "$(sha256sum "$ROOT/paper/bioinformatics/phase2_decision.md" | awk '{print $1}')" = \
  "44167694cc44b6e0b46cae598f4b90451806ba7ef902eebdf9858076a859b9b6"
test "$(sha256sum "$ROOT/paper/bioinformatics/phase3_postpilot_decision.json" | awk '{print $1}')" = \
  "471898d688386f46b4e7f13b932b6b4f9874d9ed74641240b5c2fd4ad71851fe"

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics canonical-hybrid-v2 implementation checks OK"
echo "historical_phase2_decision=verified_only_contract"
echo "historical_phase3_v1_b3=no_go"
echo "complete_cpu_authority_inside_hybrid=0"
echo "runtime_epoch=1_pending_commit_freeze"
