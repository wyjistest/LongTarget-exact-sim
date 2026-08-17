#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_segmented_archive_first"}"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
REGULAR_TARGET="${REGULAR_TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
COMPOUND_TARGET="${COMPOUND_TARGET:-"$ROOT/testDNA.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
LARGE_SYNTHETIC_ROWS="${LARGE_SYNTHETIC_ROWS:-150000}"
EVIDENCE_DOC="$ROOT/docs/fasim_gasal2_segmented_archive_first.md"
GOAL="$ROOT/goal.md"

metric() {
  local path="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$path"
}

unique_file() {
  local directory="$1"
  local pattern="$2"
  local -a paths=()
  mapfile -t paths < <(find "$directory" -maxdepth 1 -type f -name "$pattern" | sort)
  if (( ${#paths[@]} != 1 )); then
    echo "expected exactly one $pattern in $directory; found ${#paths[@]}" >&2
    return 1
  fi
  printf '%s\n' "${paths[0]}"
}

for path in "$REGULAR_TARGET" "$COMPOUND_TARGET" "$RNA"; do
  if [[ ! -f "$path" ]]; then
    echo "missing Phase 1 dependency: $path" >&2
    exit 1
  fi
done
for path in "$EVIDENCE_DOC" "$GOAL"; do
  if [[ ! -f "$path" ]]; then
    echo "missing Phase 1 completion artifact: $path" >&2
    exit 1
  fi
done

if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$ROOT/tests/check_merge_fasim_segmented_tfosorted.py" \
  >"$WORK/parser_tests.log" 2>&1
python3 "$ROOT/tests/check_characterize_fasim_gasal2_segmented_archive_first_runner.py" \
  >"$WORK/runner_tests.log" 2>&1
python3 "$ROOT/tests/check_fasim_gasal2_segmented_archive_first_large_synthetic.py" \
  --work "$WORK/large_synthetic" \
  --rows "$LARGE_SYNTHETIC_ROWS" \
  >"$WORK/large_synthetic.log"

BIN="$BIN" WORK="$WORK/archive_regular" TARGET="$REGULAR_TARGET" RNA="$RNA" \
  bash "$ROOT/scripts/check_fasim_gasal2_archive_first_output.sh" \
  >"$WORK/archive_regular.log"
BIN="$BIN" WORK="$WORK/archive_compound" TARGET="$COMPOUND_TARGET" RNA="$RNA" \
  bash "$ROOT/scripts/check_fasim_gasal2_archive_first_output.sh" \
  >"$WORK/archive_compound.log"

regular_archive="$(unique_file "$WORK/archive_regular/archive" '*.archive-first.tfoa')"
regular_legacy="$(unique_file "$WORK/archive_regular/legacy" '*-TFOsorted')"
query_sha256="$(sha256sum "$RNA" | awk '{print $1}')"
target_sha256="$(sha256sum "$REGULAR_TARGET" | awk '{print $1}')"
query_bases="$(metric "$WORK/archive_regular/summary.txt" query_bases)"
typed_manifest="$WORK/real_archive_segments.tsv"
{
  printf 'segment_id\tglobal_start\tglobal_end\tartifact_kind\tartifact_path\tquery_fasta\tquery_fasta_sha256\ttarget_fasta\ttarget_fasta_sha256\n'
  printf '0\t0\t%s\tarchive_first_tfoa\t%s\t%s\t%s\t%s\t%s\n' \
    "$query_bases" "$regular_archive" "$RNA" "$query_sha256" \
    "$REGULAR_TARGET" "$target_sha256"
} >"$typed_manifest"

legacy_manifest="$WORK/real_text_segments.tsv"
{
  printf 'segment_id\tglobal_start\tglobal_end\ttfosorted\n'
  printf '0\t0\t%s\t%s\n' "$query_bases" "$regular_legacy"
} >"$legacy_manifest"

python3 "$ROOT/scripts/merge_fasim_segmented_tfosorted.py" \
  --segments "$legacy_manifest" \
  --output "$WORK/real_text_merged-TFOsorted" \
  --dedup-backend memory \
  >"$WORK/real_text_merge_summary.txt"

python3 "$ROOT/scripts/merge_fasim_segmented_tfosorted.py" \
  --segments "$typed_manifest" \
  --output "$WORK/real_archive_merged-TFOsorted" \
  --dedup-backend sqlite \
  --dedup-db "$WORK/real_archive_merge.sqlite" \
  >"$WORK/real_archive_merge_summary.txt"

legacy_text_vs_archive_merged_equal=0
missing_rows=0
extra_rows=0
if cmp -s "$WORK/real_text_merged-TFOsorted" "$WORK/real_archive_merged-TFOsorted"; then
  legacy_text_vs_archive_merged_equal=1
else
  comm -23 \
    <(LC_ALL=C sort "$WORK/real_text_merged-TFOsorted") \
    <(LC_ALL=C sort "$WORK/real_archive_merged-TFOsorted") \
    >"$WORK/missing_rows.txt"
  comm -13 \
    <(LC_ALL=C sort "$WORK/real_text_merged-TFOsorted") \
    <(LC_ALL=C sort "$WORK/real_archive_merged-TFOsorted") \
    >"$WORK/extra_rows.txt"
  missing_rows="$(wc -l <"$WORK/missing_rows.txt")"
  extra_rows="$(wc -l <"$WORK/extra_rows.txt")"
fi

env \
  BIN="$BIN" \
  WORK="$WORK/segmented_runtime" \
  TARGET="$COMPOUND_TARGET" \
  RNA="$RNA" \
  KCNQ1OT1_FASTA="$RNA" \
  SEGMENT_LEN=512 \
  SEGMENT_OVERLAP=128 \
  GRID_SHIFTS='0 64' \
  MAX_SEGMENTS=2 \
  bash "$ROOT/scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh" \
  >"$WORK/segmented_runtime.log"

regular_restored_equal="$(metric "$WORK/archive_regular/summary.txt" restored_equal)"
compound_restored_equal="$(metric "$WORK/archive_compound/summary.txt" restored_equal)"
regular_legacy_only="$(metric "$WORK/archive_regular/summary.txt" legacy_only_rows)"
regular_archive_only="$(metric "$WORK/archive_regular/summary.txt" archive_only_rows)"
compound_legacy_only="$(metric "$WORK/archive_compound/summary.txt" legacy_only_rows)"
compound_archive_only="$(metric "$WORK/archive_compound/summary.txt" archive_only_rows)"
legacy_text_bytes="$(metric "$WORK/archive_regular/summary.txt" legacy_text_bytes)"
archive_bytes="$(metric "$WORK/archive_regular/summary.txt" archive_bytes)"
archive_run_wall_seconds="$(metric "$WORK/archive_regular/summary.txt" archive_run_wall_seconds)"
archive_restore_wall_seconds="$(metric "$WORK/archive_regular/summary.txt" restore_wall_seconds)"
archive_pipeline_wall_seconds="$(awk -v run="$archive_run_wall_seconds" -v restore="$archive_restore_wall_seconds" 'BEGIN {printf "%.6f", run + restore}')"
segmented_fallbacks="$(metric "$WORK/segmented_runtime/summary.txt" gasal2_fallbacks)"
segmented_length_guard_fallbacks="$(metric "$WORK/segmented_runtime/summary.txt" length_guard_fallbacks)"
per_segment_full_text_emitted="$(metric "$WORK/segmented_runtime/summary.txt" per_segment_full_text_emitted)"
bounded_memory_backend_active="$(metric "$WORK/segmented_runtime/summary.txt" bounded_memory_backend_active)"
segmented_pipeline_wall_seconds="$(metric "$WORK/segmented_runtime/summary.txt" pipeline_wall_seconds)"
large_rss_gate="$(metric "$WORK/large_synthetic/summary.txt" peak_rss_materially_below_memory)"
large_outputs_equal="$(metric "$WORK/large_synthetic/summary.txt" large_synthetic_outputs_byte_identical)"
memory_peak_rss_kb="$(metric "$WORK/large_synthetic/summary.txt" memory_peak_rss_kb)"
sqlite_peak_rss_kb="$(metric "$WORK/large_synthetic/summary.txt" sqlite_peak_rss_kb)"
real_dedup_backend="$(metric "$WORK/real_archive_merge_summary.txt" dedup_backend)"
real_dedup_db_bytes="$(metric "$WORK/real_archive_merge_summary.txt" dedup_db_bytes)"
real_merge_wall_seconds="$(metric "$WORK/real_archive_merge_summary.txt" merge_wall_seconds)"
real_restore_wall_seconds="$(metric "$WORK/real_archive_merge_summary.txt" restore_wall_seconds)"

archive_bytes_less_than_legacy=0
if (( archive_bytes < legacy_text_bytes )); then
  archive_bytes_less_than_legacy=1
fi
bounded_backend_exact=0
if [[ "$real_dedup_backend" == "sqlite" && "$real_dedup_db_bytes" =~ ^[1-9][0-9]*$ ]]; then
  bounded_backend_exact=1
fi

goal_state_consistent=0
active_phase="$(awk -F' = ' '$1 == "active_phase" {print $2; exit}' "$GOAL")"
last_completed_phase="$(awk -F' = ' '$1 == "last_completed_phase" {print $2; exit}' "$GOAL")"
active_phase_complete=0
if [[ "$active_phase" == "complete" ]]; then
  active_phase_complete=1
fi
if grep -Fq 'phase_1_status = pass' "$GOAL" && \
   { [[ "$active_phase_complete" == "1" ]] || \
     { [[ "$active_phase" =~ ^[0-9]+$ ]] && (( active_phase >= 2 )); }; } && \
   [[ "$last_completed_phase" =~ ^[0-9]+$ ]] && (( last_completed_phase >= 1 )); then
  goal_state_consistent=1
fi

evidence_doc_consistent=0
if grep -Fq 'Phase 1 is `pass`' "$EVIDENCE_DOC" && \
   grep -Fq 'legacy_text_vs_archive_merged_equal=1' "$EVIDENCE_DOC" && \
   grep -Fq 'peak_rss_materially_below_legacy=1' "$EVIDENCE_DOC" && \
   grep -Fq 'No multi-hour' "$EVIDENCE_DOC"; then
  evidence_doc_consistent=1
fi

make_target_present=0
if grep -Fq 'check-fasim-gasal2-segmented-archive-first:' "$ROOT/Makefile"; then
  make_target_present=1
fi

small_fixture_byte_identical=0
if [[ "$regular_restored_equal" == "1" && "$compound_restored_equal" == "1" && \
      "$regular_legacy_only" == "0" && "$regular_archive_only" == "0" && \
      "$compound_legacy_only" == "0" && "$compound_archive_only" == "0" ]]; then
  small_fixture_byte_identical=1
fi

existing_default_path_unchanged="$regular_restored_equal"
phase1_decision=fail
if [[ "$legacy_text_vs_archive_merged_equal" == "1" && "$missing_rows" == "0" && \
      "$extra_rows" == "0" && "$small_fixture_byte_identical" == "1" && \
      "$per_segment_full_text_emitted" == "0" && "$bounded_memory_backend_active" == "1" && \
      "$bounded_backend_exact" == "1" && "$segmented_fallbacks" == "0" && \
      "$segmented_length_guard_fallbacks" == "0" && "$existing_default_path_unchanged" == "1" && \
      "$archive_bytes_less_than_legacy" == "1" && "$large_rss_gate" == "1" && \
      "$large_outputs_equal" == "1" && "$goal_state_consistent" == "1" && \
      "$evidence_doc_consistent" == "1" && "$make_target_present" == "1" ]]; then
  phase1_decision=pass
fi

{
  printf 'legacy_text_vs_archive_merged_equal=%s\n' "$legacy_text_vs_archive_merged_equal"
  printf 'missing_rows=%s\n' "$missing_rows"
  printf 'extra_rows=%s\n' "$extra_rows"
  printf 'small_fixture_byte_identical=%s\n' "$small_fixture_byte_identical"
  printf 'compound_header_byte_identical=%s\n' "$compound_restored_equal"
  printf 'per_segment_full_text_emitted=%s\n' "$per_segment_full_text_emitted"
  printf 'bounded_memory_backend_active=%s\n' "$bounded_memory_backend_active"
  printf 'bounded_backend_exact=%s\n' "$bounded_backend_exact"
  printf 'fallbacks=%s\n' "$segmented_fallbacks"
  printf 'length_guard_fallbacks=%s\n' "$segmented_length_guard_fallbacks"
  printf 'existing_default_path_unchanged=%s\n' "$existing_default_path_unchanged"
  printf 'legacy_text_bytes=%s\n' "$legacy_text_bytes"
  printf 'archive_bytes=%s\n' "$archive_bytes"
  printf 'archive_bytes_less_than_legacy=%s\n' "$archive_bytes_less_than_legacy"
  printf 'archive_run_wall_seconds=%s\n' "$archive_run_wall_seconds"
  printf 'archive_restore_wall_seconds=%s\n' "$archive_restore_wall_seconds"
  printf 'archive_pipeline_wall_seconds=%s\n' "$archive_pipeline_wall_seconds"
  printf 'real_archive_merge_wall_seconds=%s\n' "$real_merge_wall_seconds"
  printf 'real_archive_restore_wall_seconds=%s\n' "$real_restore_wall_seconds"
  printf 'segmented_pipeline_wall_seconds=%s\n' "$segmented_pipeline_wall_seconds"
  printf 'memory_peak_rss_kb=%s\n' "$memory_peak_rss_kb"
  printf 'sqlite_peak_rss_kb=%s\n' "$sqlite_peak_rss_kb"
  printf 'peak_rss_materially_below_legacy=%s\n' "$large_rss_gate"
  printf 'large_synthetic_outputs_byte_identical=%s\n' "$large_outputs_equal"
  printf 'goal_state_consistent=%s\n' "$goal_state_consistent"
  printf 'evidence_doc_consistent=%s\n' "$evidence_doc_consistent"
  printf 'make_target_present=%s\n' "$make_target_present"
  printf 'phase1_decision=%s\n' "$phase1_decision"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
if [[ "$phase1_decision" != "pass" ]]; then
  echo "Fasim GASAL2 segmented archive-first Phase 1 gate failed" >&2
  exit 1
fi
echo "Fasim GASAL2 segmented archive-first Phase 1 OK"
