#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_long_query_streaming_scoreinfo_realpath_trust"}"
BUILD_BIN="${BUILD_BIN:-1}"
MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-8 16 32 64}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

summary="$WORK/summary.tsv"
printf '%s\n' \
  "label	record_limit	digest	tasks	realpath_trust	realpath_used	realpath_fallbacks	realpath_digest_authority	gpu_scoreinfo_groups	cpu_scoreinfo_groups	gpu_minscore_used	gpu_minscore_fallbacks	gpu_total_seconds	gpu_call_seconds	kernel_seconds	validation_seconds	cpu_prealign_seconds	compare_seconds	baseline_wall_seconds	candidate_wall_seconds	candidate_vs_baseline	decision" \
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
  echo "running MALAT1 first${limit} realpath trust prototype" >&2

  MALAT1_RECORD_LIMIT="$limit" \
  WORK="$child_work" \
  BIN="$BIN" \
  BUILD_BIN=0 \
    bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_realpath_trust.sh" \
    >"$run_work/check.stdout" 2>"$run_work/check.stderr"

  local stdout="$run_work/check.stdout"
  local stderr="$child_work/candidate/stderr.log"
  local baseline_stdout="$child_work/baseline/stdout.log"
  local candidate_stdout="$child_work/candidate/stdout.log"
  if [[ ! -s "$stdout" || ! -s "$stderr" || ! -s "$baseline_stdout" || ! -s "$candidate_stdout" ]]; then
    echo "missing output for MALAT1 first${limit}" >&2
    exit 1
  fi

  local digest tasks realpath_trust realpath_used realpath_fallbacks
  local realpath_digest_authority gpu_scoreinfo_groups cpu_scoreinfo_groups
  local gpu_minscore_used gpu_minscore_fallbacks gpu_total_seconds gpu_call_seconds
  local kernel_seconds validation_seconds cpu_prealign_seconds compare_seconds
  local baseline_wall_seconds candidate_wall_seconds candidate_vs_baseline decision

  digest="$(sed -n 's/^digest=//p' "$stdout" | tail -n 1)"
  tasks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks)"
  realpath_trust="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust)"
  realpath_used="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used)"
  realpath_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks)"
  realpath_digest_authority="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority)"
  gpu_scoreinfo_groups="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups)"
  cpu_scoreinfo_groups="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups)"
  gpu_minscore_used="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used)"
  gpu_minscore_fallbacks="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks)"
  gpu_total_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds)"
  gpu_call_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds)"
  kernel_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds)"
  validation_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds)"
  cpu_prealign_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds)"
  compare_seconds="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds)"
  decision="$(metric "$stderr" benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision)"
  baseline_wall_seconds="$(awk -F= '$1 == "benchmark.total_wall_seconds" {print $2}' "$child_work/baseline/stderr.log" | tail -n 1)"
  candidate_wall_seconds="$(awk -F= '$1 == "benchmark.total_wall_seconds" {print $2}' "$stderr" | tail -n 1)"
  if [[ -z "$baseline_wall_seconds" ]]; then
    baseline_wall_seconds="$(sed -n 's/^Running time is //p' "$baseline_stdout" | tail -n 1)"
  fi
  if [[ -z "$candidate_wall_seconds" ]]; then
    candidate_wall_seconds="$(sed -n 's/^Running time is //p' "$candidate_stdout" | tail -n 1)"
  fi
  if [[ -z "$baseline_wall_seconds" ]]; then
    baseline_wall_seconds="$(awk '/^real\t/ {print $2}' "$baseline_stdout" | tail -n 1)"
  fi
  if [[ -z "$candidate_wall_seconds" ]]; then
    candidate_wall_seconds="$(awk '/^real\t/ {print $2}' "$candidate_stdout" | tail -n 1)"
  fi

  for name in \
    digest tasks realpath_trust realpath_used realpath_fallbacks \
    realpath_digest_authority gpu_scoreinfo_groups cpu_scoreinfo_groups \
    gpu_minscore_used gpu_minscore_fallbacks gpu_total_seconds gpu_call_seconds \
    kernel_seconds validation_seconds cpu_prealign_seconds compare_seconds \
    decision; do
    if [[ -z "${!name}" ]]; then
      echo "missing metric $name for MALAT1 first${limit}" >&2
      exit 1
    fi
  done

  if [[ "$realpath_trust" != "1" || "$realpath_digest_authority" != "external_digest_gate" ]]; then
    echo "expected trust external digest gate for MALAT1 first${limit}, got trust=$realpath_trust authority=$realpath_digest_authority" >&2
    exit 1
  fi
  if [[ "$realpath_used" != "$tasks" || "$gpu_minscore_used" != "$tasks" ]]; then
    echo "expected realpath/GPU minScore used to equal tasks for MALAT1 first${limit}, got realpath=$realpath_used gpu_minscore=$gpu_minscore_used tasks=$tasks" >&2
    exit 1
  fi
  if [[ "$realpath_fallbacks" != "0" || "$gpu_minscore_fallbacks" != "0" ]]; then
    echo "expected no trust fallback for MALAT1 first${limit}, got realpath=$realpath_fallbacks gpu_minscore=$gpu_minscore_fallbacks" >&2
    exit 1
  fi
  if [[ "$gpu_scoreinfo_groups" -le 0 || "$cpu_scoreinfo_groups" != "0" ]]; then
    echo "expected GPU scoreInfo only for MALAT1 first${limit}, got gpu=$gpu_scoreinfo_groups cpu=$cpu_scoreinfo_groups" >&2
    exit 1
  fi
  if [[ "$cpu_prealign_seconds" != "0" || "$compare_seconds" != "0" ]]; then
    echo "expected no CPU preAlign/compare validation for MALAT1 first${limit}, got cpu=$cpu_prealign_seconds compare=$compare_seconds" >&2
    exit 1
  fi
  if [[ "$decision" != "streaming_scoreinfo_shadow_active" ]]; then
    echo "unexpected trust decision for MALAT1 first${limit}: $decision" >&2
    exit 1
  fi

  candidate_vs_baseline="$(
    awk -v base="$baseline_wall_seconds" -v cand="$candidate_wall_seconds" 'BEGIN {
      if ((base + 0.0) <= 0.0 || (cand + 0.0) <= 0.0) {
        print "na";
      } else {
        printf "%.6f", (base + 0.0) / (cand + 0.0);
      }
    }'
  )"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%sx\t%s\n' \
    "malat1_first${limit}" \
    "$limit" \
    "$digest" \
    "$tasks" \
    "$realpath_trust" \
    "$realpath_used" \
    "$realpath_fallbacks" \
    "$realpath_digest_authority" \
    "$gpu_scoreinfo_groups" \
    "$cpu_scoreinfo_groups" \
    "$gpu_minscore_used" \
    "$gpu_minscore_fallbacks" \
    "$gpu_total_seconds" \
    "$gpu_call_seconds" \
    "$kernel_seconds" \
    "$validation_seconds" \
    "$cpu_prealign_seconds" \
    "$compare_seconds" \
    "${baseline_wall_seconds:-na}" \
    "${candidate_wall_seconds:-na}" \
    "$candidate_vs_baseline" \
    "$decision" \
    >>"$summary"
}

for limit in $MALAT1_RECORD_LIMITS; do
  run_limit "$limit"
done

cat "$summary"
