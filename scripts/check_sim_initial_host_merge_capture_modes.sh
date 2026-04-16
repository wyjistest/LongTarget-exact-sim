#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

TEST_BIN=./tests/test_sim_initial_host_merge_capture_modes

WORK=$(mktemp -d /tmp/longtarget-host-merge-capture-modes-XXXXXX)
trap 'rm -rf "$WORK"' EXIT

LONGTARGET_SIM_INITIAL_HOST_MERGE_MANIFEST_PATH="$WORK/manifest-only.tsv" \
LONGTARGET_SIM_CUDA_LOCATE_MODE=safe_workset \
"$TEST_BIN" manifest-only

LONGTARGET_SIM_INITIAL_HOST_MERGE_MANIFEST_PATH="$WORK/manifest-progress.tsv" \
LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_SECONDS=0 \
LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_CASES=1 \
LONGTARGET_SIM_CUDA_LOCATE_MODE=safe_workset \
"$TEST_BIN" manifest-progress >"$WORK/manifest-progress.stdout.log" 2>"$WORK/manifest-progress.stderr.log"

test -s "$WORK/manifest-progress.tsv"
grep -q '^case_id' "$WORK/manifest-progress.tsv"
grep -q 'SIM initial host-merge manifest heartbeat:' "$WORK/manifest-progress.stderr.log"
grep -q 'processed_cases=1' "$WORK/manifest-progress.stderr.log"

cat >"$WORK/case-list.tsv" <<'EOF'
case_id
case-00000002
EOF

mkdir -p "$WORK/corpus"
LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_DIR="$WORK/corpus" \
LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST="$WORK/case-list.tsv" \
LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_MAX_CASES=1 \
LONGTARGET_SIM_CUDA_LOCATE_MODE=safe_workset \
"$TEST_BIN" case-list
