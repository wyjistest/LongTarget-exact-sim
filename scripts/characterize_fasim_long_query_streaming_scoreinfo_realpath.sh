#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_realpath"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-8 16 32 64}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	record_limit	digest	tasks	realpath_requested	realpath_used	realpath_fallbacks	realpath_digest_authority	scoreinfo_mismatches	candidate_missing	candidate_extra	gpu_minscore_used	gpu_minscore_fallbacks	gpu_total_seconds	gpu_call_seconds	kernel_seconds	validation_seconds	validation_minscore_seconds	cpu_prealign_seconds	cpu_vs_gpu_total	speedup_boundary	decision" \
  >"$summary"

metric() {
  local stderr="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2}' "$stderr" | tail -n 1
}

run_limit() {
  local limit="$1"
  case "$limit" in
    ''|*[!0-9]*)
      echo "record limits must contain positive integers, got: $limit" >&2
      exit 1
      ;;
  esac
  if [[ "$limit" -le 0 ]]; then
    echo "record limits must contain positive integers, got: $limit" >&2
    exit 1
  fi

  local run_work="$WORK/malat1_first${limit}"
  local child_work="$run_work/run"
  mkdir -p "$run_work"
  echo "running MALAT1 first${limit} realpath prototype" >&2

  MALAT1_RECORD_LIMIT="$limit" \
  WORK="$child_work" \
  BIN="$BIN" \
  BUILD_BIN=0 \
    bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_realpath_prototype.sh" \
    >"$run_work/check.stdout" 2>"$run_work/check.stderr"

  local stdout="$run_work/check.stdout"
  local stderr="$child_work/candidate/stderr.log"
  if [[ ! -s "$stdout" || ! -s "$stderr" ]]; then
    echo "missing output for MALAT1 first${limit}" >&2
    exit 1
  fi

  local digest tasks realpath_requested realpath_used realpath_fallbacks
  local realpath_digest_authority scoreinfo_mismatches candidate_missing candidate_extra
  local gpu_minscore_used gpu_minscore_fallbacks gpu_total_seconds gpu_call_seconds
  local kernel_seconds validation_seconds validation_minscore_seconds cpu_prealign_seconds
  local decision cpu_vs_gpu_total speedup_boundary

  digest="$(sed -n 's/^digest=//p' "$stdout" | tail -n 1)"
  tasks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
  realpath_requested="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested)"
  realpath_used="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used)"
  realpath_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks)"
  realpath_digest_authority="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority)"
  scoreinfo_mismatches="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
  candidate_missing="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing)"
  candidate_extra="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra)"
  gpu_minscore_used="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used)"
  gpu_minscore_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks)"
  gpu_total_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds)"
  gpu_call_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds)"
  kernel_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds)"
  validation_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds)"
  validation_minscore_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_minscore_seconds)"
  cpu_prealign_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds)"
  decision="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"

  for name in \
    digest tasks realpath_requested realpath_used realpath_fallbacks \
    realpath_digest_authority scoreinfo_mismatches candidate_missing candidate_extra \
    gpu_minscore_used gpu_minscore_fallbacks gpu_total_seconds gpu_call_seconds \
    kernel_seconds validation_seconds validation_minscore_seconds cpu_prealign_seconds \
    decision; do
    if [[ -z "${!name}" ]]; then
      echo "missing metric $name for MALAT1 first${limit}" >&2
      exit 1
    fi
  done

  if [[ "$realpath_requested" != "1" ]]; then
    echo "expected realpath_requested=1 for MALAT1 first${limit}, got $realpath_requested" >&2
    exit 1
  fi
  if [[ "$realpath_used" != "$tasks" ]]; then
    echo "expected realpath_used to equal tasks for MALAT1 first${limit}, got used=$realpath_used tasks=$tasks" >&2
    exit 1
  fi
  if [[ "$gpu_minscore_used" != "$tasks" ]]; then
    echo "expected GPU minScore used to equal tasks for MALAT1 first${limit}, got used=$gpu_minscore_used tasks=$tasks" >&2
    exit 1
  fi
  if [[ "$realpath_fallbacks" != "0" || "$gpu_minscore_fallbacks" != "0" ]]; then
    echo "expected no realpath/GPU minScore fallback for MALAT1 first${limit}, got realpath=$realpath_fallbacks gpu_minscore=$gpu_minscore_fallbacks" >&2
    exit 1
  fi
  if [[ "$realpath_digest_authority" != "cpu_validated" ]]; then
    echo "expected cpu_validated digest authority for MALAT1 first${limit}, got $realpath_digest_authority" >&2
    exit 1
  fi
  if [[ "$scoreinfo_mismatches" != "0" || "$candidate_missing" != "0" || "$candidate_extra" != "0" ]]; then
    echo "expected clean scoreInfo comparison for MALAT1 first${limit}, got mismatches=$scoreinfo_mismatches missing=$candidate_missing extra=$candidate_extra" >&2
    exit 1
  fi
  if [[ "$decision" != "streaming_scoreinfo_shadow_active" ]]; then
    echo "unexpected decision for MALAT1 first${limit}: $decision" >&2
    exit 1
  fi

  cpu_vs_gpu_total="$(
    awk -v cpu="$cpu_prealign_seconds" -v gpu="$gpu_total_seconds" 'BEGIN {
      if ((gpu + 0.0) <= 0.0) {
        print "0";
      } else {
        printf "%.6f", (cpu + 0.0) / (gpu + 0.0);
      }
    }'
  )"
  speedup_boundary="$(
    awk -v ratio="$cpu_vs_gpu_total" 'BEGIN {
      if ((ratio + 0.0) > 1.0) {
        print "marginal_positive";
      } else {
        print "no_go";
      }
    }'
  )"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%sx\t%s\t%s\n' \
    "malat1_first${limit}" \
    "$limit" \
    "$digest" \
    "$tasks" \
    "$realpath_requested" \
    "$realpath_used" \
    "$realpath_fallbacks" \
    "$realpath_digest_authority" \
    "$scoreinfo_mismatches" \
    "$candidate_missing" \
    "$candidate_extra" \
    "$gpu_minscore_used" \
    "$gpu_minscore_fallbacks" \
    "$gpu_total_seconds" \
    "$gpu_call_seconds" \
    "$kernel_seconds" \
    "$validation_seconds" \
    "$validation_minscore_seconds" \
    "$cpu_prealign_seconds" \
    "$cpu_vs_gpu_total" \
    "$speedup_boundary" \
    "$decision" \
    >>"$summary"
}

for limit in $MALAT1_RECORD_LIMITS; do
  run_limit "$limit"
done

cat "$summary"
