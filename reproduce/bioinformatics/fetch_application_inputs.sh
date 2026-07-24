#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'usage: %s [--create-freeze]\n' "${0##*/}" >&2
}

create_freeze=0
case "$#" in
  0)
    ;;
  1)
    if [[ "$1" != "--create-freeze" ]]; then
      usage
      exit 2
    fi
    create_freeze=1
    ;;
  *)
    usage
    exit 2
    ;;
esac

ROOT="$(cd -- "${BASH_SOURCE[0]%/*}/../.." && pwd -P)"
if [[ -n "${SOURCE_DIR+x}" ]]; then
  printf 'application input fetch failed: SOURCE_DIR override is not supported\n' >&2
  exit 2
fi
SOURCE_DIR="$ROOT/.tmp/bioinformatics_application_sources"
BUILDER="$ROOT/reproduce/bioinformatics/build_application_panel.py"
DEVELOPMENT_EXCLUSIONS="$ROOT/paper/bioinformatics/development_query_exclusions.tsv"
HOLDOUT_MANIFEST="$ROOT/paper/bioinformatics/holdout_manifest.tsv"
SELECTION_RECEIPT="$ROOT/paper/bioinformatics/application_selection.json"
APPLICATION_INPUTS="$ROOT/reproduce/bioinformatics/application_inputs"
MANIFEST="$ROOT/paper/bioinformatics/application_manifest.tsv"
MANIFEST_CHECKSUM="$ROOT/paper/bioinformatics/application_manifest.sha256"
SOURCE_LEDGER="$ROOT/paper/bioinformatics/application_sources.tsv"
INPUT_SUMMARY="$ROOT/paper/bioinformatics/application_input_summary.tsv"

die() {
  printf 'application input fetch failed: %s\n' "$1" >&2
  exit 2
}

root_directory_fd=""
temporary_directory_fd=""
source_directory_fd=""
root_directory_identity=""
temporary_directory_identity=""
source_directory_identity=""
root_directory_anchor=""
temporary_directory_anchor=""
source_directory_anchor=""

directory_identity() {
  stat -Lc '%d:%i' -- "$1"
}

file_identity() {
  stat -Lc '%d:%i' -- "$1"
}

path_has_owned_identity() {
  local path="$1"
  local expected_identity="$2"
  local actual_identity

  [[ -n "$path" && -n "$expected_identity" ]] || return 1
  [[ -f "$path" && ! -L "$path" ]] || return 1
  actual_identity="$(file_identity "$path")" || return 1
  [[ "$actual_identity" == "$expected_identity" ]]
}

remove_owned_file() {
  local path="$1"
  local expected_identity="$2"
  local entry_name="${path##*/}"
  local expected_device
  local expected_inode

  [[ "$expected_identity" =~ ^[0-9]+:[0-9]+$ ]] || return 1
  expected_device="${expected_identity%%:*}"
  expected_inode="${expected_identity#*:}"
  python3 "$BUILDER" cleanup-cache-entry \
    --cache-directory-fd "$source_directory_fd" \
    --entry-name "$entry_name" \
    --expected-device "$expected_device" \
    --expected-inode "$expected_inode"
}

verify_source_cache_binding() {
  local current_identity

  [[ -d "$root_directory_anchor" ]] || return 1
  [[ -d "$temporary_directory_anchor" ]] || return 1
  [[ -d "$source_directory_anchor" ]] || return 1
  [[ -d "$ROOT" && ! -L "$ROOT" ]] || return 1
  [[ -d "$ROOT/.tmp" && ! -L "$ROOT/.tmp" ]] || return 1
  [[ -d "$SOURCE_DIR" && ! -L "$SOURCE_DIR" ]] || return 1

  current_identity="$(directory_identity "$ROOT")" || return 1
  [[ "$current_identity" == "$root_directory_identity" ]] || return 1
  current_identity="$(directory_identity "$ROOT/.tmp")" || return 1
  [[ "$current_identity" == "$temporary_directory_identity" ]] || return 1
  current_identity="$(directory_identity "$SOURCE_DIR")" || return 1
  [[ "$current_identity" == "$source_directory_identity" ]] || return 1
  current_identity="$(directory_identity "$root_directory_anchor/.tmp")" || return 1
  [[ "$current_identity" == "$temporary_directory_identity" ]] || return 1
  current_identity="$(
    directory_identity "$temporary_directory_anchor/bioinformatics_application_sources"
  )" || return 1
  [[ "$current_identity" == "$source_directory_identity" ]] || return 1
}

for required_command in \
  cmp curl flock gzip md5sum mkdir mktemp mv python3 rm sha256sum stat wc
do
  command -v "$required_command" >/dev/null 2>&1 || \
    die "required command not found: $required_command"
done

for required_input in "$BUILDER" "$DEVELOPMENT_EXCLUSIONS" "$HOLDOUT_MANIFEST"; do
  [[ -f "$required_input" && ! -L "$required_input" ]] || \
    die "required reconstruction input is missing or unsafe: $required_input"
done

if ((create_freeze == 0)); then
  for committed_output in \
    "$SELECTION_RECEIPT" \
    "$APPLICATION_INPUTS" \
    "$MANIFEST" \
    "$MANIFEST_CHECKSUM" \
    "$SOURCE_LEDGER" \
    "$INPUT_SUMMARY"
  do
    if [[ -L "$committed_output" ]]; then
      die "committed application freeze output is unsafe: $committed_output"
    fi
    if [[ ! -e "$committed_output" ]]; then
      die "committed application freeze output is missing: $committed_output"
    fi
  done
fi

exec {root_directory_fd}<"$ROOT" || die "cannot retain repository root directory"
root_directory_anchor="/proc/self/fd/$root_directory_fd"
root_directory_identity="$(directory_identity "$root_directory_anchor")" || \
  die "cannot identify repository root directory"

temporary_entry="$root_directory_anchor/.tmp"
if [[ -L "$temporary_entry" ]]; then
  die "source cache parent is unsafe: $ROOT/.tmp"
fi
if [[ -e "$temporary_entry" ]]; then
  [[ -d "$temporary_entry" ]] || \
    die "source cache parent is unsafe: $ROOT/.tmp"
else
  mkdir -- "$temporary_entry" || \
    die "cannot create source cache parent: $ROOT/.tmp"
fi
[[ -d "$temporary_entry" && ! -L "$temporary_entry" ]] || \
  die "source cache parent is unsafe: $ROOT/.tmp"
exec {temporary_directory_fd}<"$temporary_entry" || \
  die "cannot retain source cache parent: $ROOT/.tmp"
temporary_directory_anchor="/proc/self/fd/$temporary_directory_fd"
temporary_directory_identity="$(directory_identity "$temporary_directory_anchor")" || \
  die "cannot identify source cache parent: $ROOT/.tmp"
[[ -d "$temporary_entry" && ! -L "$temporary_entry" ]] || \
  die "source cache parent changed during setup: $ROOT/.tmp"
[[ "$(directory_identity "$temporary_entry")" == "$temporary_directory_identity" ]] || \
  die "source cache parent changed during setup: $ROOT/.tmp"

source_entry="$temporary_directory_anchor/bioinformatics_application_sources"
if [[ -L "$source_entry" ]]; then
  die "source cache is unsafe: $SOURCE_DIR"
fi
if [[ -e "$source_entry" ]]; then
  [[ -d "$source_entry" ]] || die "source cache is unsafe: $SOURCE_DIR"
else
  mkdir -- "$source_entry" || die "cannot create source cache: $SOURCE_DIR"
fi
[[ -d "$source_entry" && ! -L "$source_entry" ]] || \
  die "source cache is unsafe: $SOURCE_DIR"
exec {source_directory_fd}<"$source_entry" || \
  die "cannot retain source cache: $SOURCE_DIR"
source_directory_anchor="/proc/self/fd/$source_directory_fd"
source_directory_identity="$(directory_identity "$source_directory_anchor")" || \
  die "cannot identify source cache: $SOURCE_DIR"
[[ -d "$source_entry" && ! -L "$source_entry" ]] || \
  die "source cache changed during setup: $SOURCE_DIR"
[[ "$(directory_identity "$source_entry")" == "$source_directory_identity" ]] || \
  die "source cache changed during setup: $SOURCE_DIR"
verify_source_cache_binding || die "source cache binding changed during setup"

active_partial=""
active_partial_fd=""
active_partial_identity=""
active_cache=""
active_cache_identity=""
source_table=""
selection_workspace=""
selection_repository=""

cleanup() {
  local status="$?"
  trap - EXIT
  set +e
  if [[ -n "$active_partial" ]]; then
    if [[ -z "$active_partial_identity" && -n "$active_partial_fd" ]]; then
      active_partial_identity="$(
        file_identity "/proc/self/fd/$active_partial_fd"
      )"
    fi
    remove_owned_file "$active_partial" "$active_partial_identity"
  fi
  if [[ -n "$active_cache" ]]; then
    remove_owned_file "$active_cache" "$active_cache_identity"
  fi
  if [[ -n "$active_partial_fd" ]]; then
    exec {active_partial_fd}>&-
  fi
  if [[ -n "$source_table" ]]; then
    rm -f -- "$source_table"
  fi
  if [[ -n "$selection_workspace" ]]; then
    rm -rf -- "$selection_workspace"
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
flock -x "$source_directory_fd" || die "cannot lock source cache"
verify_source_cache_binding || die "source cache binding changed while waiting for lock"

source_identity_matches() {
  local path="$1"
  local expected_md5="$2"
  local expected_compressed_size="$3"
  local expected_compressed_sha256="$4"
  local expected_decompressed_size="$5"
  local expected_decompressed_sha256="$6"
  local allow_descriptor="${7:-0}"
  local actual_line
  local actual_value

  if ((allow_descriptor)); then
    [[ -f "$path" ]] || return 1
  else
    [[ -f "$path" && ! -L "$path" ]] || return 1
  fi

  actual_value="$(stat -Lc '%s' -- "$path")" || return 1
  [[ "$actual_value" == "$expected_compressed_size" ]] || return 1

  actual_line="$(md5sum -- "$path")" || return 1
  actual_value="${actual_line%% *}"
  [[ "$actual_value" == "$expected_md5" ]] || return 1

  actual_line="$(sha256sum -- "$path")" || return 1
  actual_value="${actual_line%% *}"
  [[ "$actual_value" == "$expected_compressed_sha256" ]] || return 1

  actual_line="$(gzip -cd -- "$path" | sha256sum)" || return 1
  actual_value="${actual_line%% *}"
  [[ "$actual_value" == "$expected_decompressed_sha256" ]] || return 1

  actual_value="$(gzip -cd -- "$path" | wc -c)" || return 1
  actual_value="${actual_value//[[:space:]]/}"
  [[ "$actual_value" == "$expected_decompressed_size" ]] || return 1
}

download_source() {
  local source_id="$1"
  local url="$2"
  local destination="$3"
  local destination_entry="$source_directory_anchor/${destination##*/}"
  local partial_descriptor
  local expected_md5="$4"
  local expected_compressed_size="$5"
  local expected_compressed_sha256="$6"
  local expected_decompressed_size="$7"
  local expected_decompressed_sha256="$8"

  verify_source_cache_binding || die "source cache binding changed before $source_id"

  if [[ -e "$destination_entry" || -L "$destination_entry" ]]; then
    source_identity_matches \
      "$destination_entry" \
      "$expected_md5" \
      "$expected_compressed_size" \
      "$expected_compressed_sha256" \
      "$expected_decompressed_size" \
      "$expected_decompressed_sha256" || \
      die "cached source identity mismatch for $source_id: $destination"
    verify_source_cache_binding || \
      die "source cache binding changed while reusing $source_id"
    return
  fi

  active_partial="${destination_entry}.partial.$$"
  if [[ -e "$active_partial" || -L "$active_partial" ]]; then
    die "PID-specific partial already exists: $active_partial"
  fi
  set -o noclobber
  if ! exec {active_partial_fd}>"$active_partial"; then
    set +o noclobber
    die "cannot create PID-specific partial: $active_partial"
  fi
  set +o noclobber
  active_partial_identity="$(
    file_identity "/proc/self/fd/$active_partial_fd"
  )" || die "cannot identify PID-specific partial: $active_partial"
  partial_descriptor="/proc/self/fd/$active_partial_fd"
  path_has_owned_identity "$active_partial" "$active_partial_identity" || \
    die "PID-specific partial changed during creation: $active_partial"
  verify_source_cache_binding || \
    die "source cache binding changed before downloading $source_id"
  curl -fL --retry 3 --output "$partial_descriptor" "$url"
  verify_source_cache_binding || \
    die "source cache binding changed while downloading $source_id"
  path_has_owned_identity "$active_partial" "$active_partial_identity" || \
    die "PID-specific partial changed while downloading $source_id"
  source_identity_matches \
    "$partial_descriptor" \
    "$expected_md5" \
    "$expected_compressed_size" \
    "$expected_compressed_sha256" \
    "$expected_decompressed_size" \
    "$expected_decompressed_sha256" \
    1 || die "downloaded source identity mismatch for $source_id"
  path_has_owned_identity "$active_partial" "$active_partial_identity" || \
    die "PID-specific partial changed while validating $source_id"
  [[ ! -e "$destination_entry" && ! -L "$destination_entry" ]] || \
    die "source destination appeared during download: $destination"
  verify_source_cache_binding || \
    die "source cache binding changed before publishing $source_id"
  active_cache="$destination_entry"
  active_cache_identity="$active_partial_identity"
  mv -T --no-clobber -- "$active_partial" "$destination_entry"
  if [[ -e "$active_partial" || -L "$active_partial" ]]; then
    die "source destination appeared during publication: $destination"
  fi
  path_has_owned_identity "$active_cache" "$active_cache_identity" || \
    die "published source cache ownership mismatch for $source_id"
  active_partial=""
  verify_source_cache_binding || \
    die "source cache binding changed during publication of $source_id"
  source_identity_matches \
    "$active_cache" \
    "$expected_md5" \
    "$expected_compressed_size" \
    "$expected_compressed_sha256" \
    "$expected_decompressed_size" \
    "$expected_decompressed_sha256" || \
    die "published source cache identity mismatch for $source_id"
  path_has_owned_identity "$active_cache" "$active_cache_identity" || \
    die "published source cache ownership changed for $source_id"
  verify_source_cache_binding || \
    die "source cache binding changed after publishing $source_id"
  active_cache=""
  active_cache_identity=""
  active_partial_identity=""
  exec {active_partial_fd}>&-
  active_partial_fd=""
}

source_table="$(mktemp "${TMPDIR:-/tmp}/bioinformatics-application-sources.XXXXXX.tsv")"
python3 "$BUILDER" sources >"$source_table"
verify_source_cache_binding || die "source cache binding changed after source discovery"

expected_header=$'source_id\trole\tprovider\trelease\tassembly\turl\tupstream_md5\tcompressed_size_bytes\tcompressed_sha256\tdecompressed_size_bytes\tdecompressed_sha256\tlocal_source_path\tlicense_or_terms\tredistribution_note\tdownload_command'
expected_source_ids=(
  gencode_v49_lncrna
  gencode_v49_gtf
  ucsc_hg38_chr21
  ucsc_hg38_chr22
)
declare -A seen_source_ids=()
source_count=0
lncrna_fasta=""
annotation_gtf=""
chr21_fasta=""
chr22_fasta=""

{
  IFS= read -r header || die "canonical source table is empty"
  [[ "$header" == "$expected_header" ]] || die "canonical source table schema drift"
  while IFS=$'\t' read -r \
    source_id role provider release assembly url upstream_md5 \
    compressed_size compressed_sha256 decompressed_size decompressed_sha256 \
    local_source_path license_or_terms redistribution_note download_command \
    extra
  do
    [[ -n "$source_id" && -z "$extra" ]] || die "malformed canonical source row"
    ((source_count < ${#expected_source_ids[@]})) || die "extra canonical source row"
    [[ "$source_id" == "${expected_source_ids[$source_count]}" ]] || \
      die "canonical source order or identity drift: $source_id"
    [[ -z "${seen_source_ids[$source_id]+present}" ]] || \
      die "duplicate canonical source identity: $source_id"
    seen_source_ids[$source_id]=1
    [[ -n "$role" && -n "$provider" && -n "$release" && -n "$assembly" ]] || \
      die "incomplete canonical source authority: $source_id"
    [[ "$url" == https://* ]] || die "non-HTTPS canonical source URL: $source_id"
    [[ "$upstream_md5" =~ ^[0-9a-f]{32}$ ]] || \
      die "invalid canonical source MD5: $source_id"
    [[ "$compressed_size" =~ ^[1-9][0-9]*$ ]] || \
      die "invalid canonical compressed size: $source_id"
    [[ "$compressed_sha256" =~ ^[0-9a-f]{64}$ ]] || \
      die "invalid canonical compressed SHA-256: $source_id"
    [[ "$decompressed_size" =~ ^[1-9][0-9]*$ ]] || \
      die "invalid canonical decompressed size: $source_id"
    [[ "$decompressed_sha256" =~ ^[0-9a-f]{64}$ ]] || \
      die "invalid canonical decompressed SHA-256: $source_id"
    [[ "$local_source_path" == .tmp/bioinformatics_application_sources/*.gz ]] || \
      die "invalid canonical local source path: $source_id"
    [[ -n "$license_or_terms" && -n "$redistribution_note" ]] || \
      die "incomplete canonical source terms: $source_id"
    [[ -n "$download_command" ]] || die "incomplete canonical source row: $source_id"

    destination="$SOURCE_DIR/${local_source_path##*/}"
    download_source \
      "$source_id" \
      "$url" \
      "$destination" \
      "$upstream_md5" \
      "$compressed_size" \
      "$compressed_sha256" \
      "$decompressed_size" \
      "$decompressed_sha256"
    case "$source_id" in
      gencode_v49_lncrna) lncrna_fasta="$destination" ;;
      gencode_v49_gtf) annotation_gtf="$destination" ;;
      ucsc_hg38_chr21) chr21_fasta="$destination" ;;
      ucsc_hg38_chr22) chr22_fasta="$destination" ;;
      *) die "unknown canonical source identity: $source_id" ;;
    esac
    ((source_count += 1))
  done
} <"$source_table"

((source_count == ${#expected_source_ids[@]})) || \
  die "canonical source table has $source_count rows; expected 4"
for required_source in "$lncrna_fasta" "$annotation_gtf" "$chr21_fasta" "$chr22_fasta"; do
  [[ -n "$required_source" ]] || die "canonical source mapping is incomplete"
done
verify_source_cache_binding || die "source cache binding changed after acquisition"

selection_workspace="$(mktemp -d "${TMPDIR:-/tmp}/bioinformatics-application-selection.XXXXXX")"
selection_repository="$selection_workspace/repository"
mkdir -- "$selection_repository"
mkdir -p -- "$selection_repository/paper/bioinformatics"
temporary_selection="$selection_repository/paper/bioinformatics/application_selection.json"

source_arguments=(
  --lncrna-fasta "$lncrna_fasta"
  --annotation-gtf "$annotation_gtf"
  --chr21-fasta "$chr21_fasta"
  --chr22-fasta "$chr22_fasta"
  --development-exclusions "$DEVELOPMENT_EXCLUSIONS"
  --holdout-manifest "$HOLDOUT_MANIFEST"
)
python3 "$BUILDER" select \
  --repository-root "$selection_repository" \
  "${source_arguments[@]}" \
  --selection-receipt "$temporary_selection" \
  --application-inputs "$selection_repository/reproduce/bioinformatics/application_inputs" \
  --manifest "$selection_repository/paper/bioinformatics/application_manifest.tsv" \
  --manifest-checksum "$selection_repository/paper/bioinformatics/application_manifest.sha256" \
  --source-ledger "$selection_repository/paper/bioinformatics/application_sources.tsv" \
  --input-summary "$selection_repository/paper/bioinformatics/application_input_summary.tsv"

selection_input="$temporary_selection"
if ((create_freeze == 0)); then
  cmp -- "$temporary_selection" "$SELECTION_RECEIPT" || \
    die "committed application selection receipt drift"
  selection_input="$SELECTION_RECEIPT"
fi

if ((create_freeze == 0)); then
  python3 "$BUILDER" verify \
    --repository-root "$ROOT" \
    "${source_arguments[@]}" \
    --selection-receipt "$SELECTION_RECEIPT" \
    --application-inputs "$APPLICATION_INPUTS" \
    --manifest "$MANIFEST" \
    --manifest-checksum "$MANIFEST_CHECKSUM" \
    --source-ledger "$SOURCE_LEDGER" \
    --input-summary "$INPUT_SUMMARY" \
    --selection "$selection_input"
else
  python3 "$BUILDER" materialize \
    --repository-root "$ROOT" \
    "${source_arguments[@]}" \
    --selection-receipt "$SELECTION_RECEIPT" \
    --application-inputs "$APPLICATION_INPUTS" \
    --manifest "$MANIFEST" \
    --manifest-checksum "$MANIFEST_CHECKSUM" \
    --source-ledger "$SOURCE_LEDGER" \
    --input-summary "$INPUT_SUMMARY" \
    --selection "$selection_input"
fi
verify_source_cache_binding || die "source cache binding changed after reconstruction"

printf 'Bioinformatics Phase 3 application inputs reconstructed\n'
