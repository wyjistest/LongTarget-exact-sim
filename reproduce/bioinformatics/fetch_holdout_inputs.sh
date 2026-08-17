#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-$ROOT/.tmp/bioinformatics_holdout_sources}"
GENCODE_BASE="https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49"
UCSC_BASE="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes"

mkdir -p -- "$SOURCE_DIR" "$SOURCE_DIR/chromosomes"

download() {
  local url="$1"
  local destination="$2"
  local expected_md5="$3"
  local expected_sha256="$4"
  local expected_size="$5"
  if [[ -f "$destination" ]] && \
     [[ "$(stat -c '%s' "$destination")" == "$expected_size" ]] && \
     [[ "$(sha256sum "$destination" | cut -d' ' -f1)" == "$expected_sha256" ]]; then
    return
  fi
  local partial="${destination}.partial.$$"
  trap 'rm -f -- "$partial"' EXIT RETURN
  curl -fL --retry 3 --output "$partial" "$url"
  [[ "$(md5sum "$partial" | cut -d' ' -f1)" == "$expected_md5" ]]
  [[ "$(sha256sum "$partial" | cut -d' ' -f1)" == "$expected_sha256" ]]
  [[ "$(stat -c '%s' "$partial")" == "$expected_size" ]]
  mv -f -- "$partial" "$destination"
  trap - EXIT RETURN
}

download_chromosome() {
  local archive_name="$1"
  local chromosome="${archive_name%.fa.gz}"
  local expected_md5="$2"
  local expected_sha256="$3"
  local expected_size="$4"
  local destination="$SOURCE_DIR/chromosomes/${chromosome}.fa"
  if [[ -f "$destination" ]] && \
     [[ "$(stat -c '%s' "$destination")" == "$expected_size" ]] && \
     [[ "$(sha256sum "$destination" | cut -d' ' -f1)" == "$expected_sha256" ]]; then
    return
  fi
  local archive="$SOURCE_DIR/$archive_name"
  local archive_partial="${archive}.partial.$$"
  local destination_partial="${destination}.partial.$$"
  trap 'rm -f -- "$archive_partial" "$destination_partial"' EXIT RETURN
  curl -fL --retry 3 --output "$archive_partial" "$UCSC_BASE/$archive_name"
  [[ "$(md5sum "$archive_partial" | cut -d' ' -f1)" == "$expected_md5" ]]
  mv -f -- "$archive_partial" "$archive"
  gzip -cd -- "$archive" >"$destination_partial"
  [[ "$(sha256sum "$destination_partial" | cut -d' ' -f1)" == "$expected_sha256" ]]
  [[ "$(stat -c '%s' "$destination_partial")" == "$expected_size" ]]
  mv -f -- "$destination_partial" "$destination"
  trap - EXIT RETURN
}

download \
  "$GENCODE_BASE/gencode.v49.lncRNA_transcripts.fa.gz" \
  "$SOURCE_DIR/gencode.v49.lncRNA_transcripts.fa.gz" \
  "6d52ea2c72933c864e46a560fe0b5d4c" \
  "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4" \
  "37870043"
download \
  "$GENCODE_BASE/gencode.v49.annotation.gtf.gz" \
  "$SOURCE_DIR/gencode.v49.annotation.gtf.gz" \
  "0ef4a024ea2d35b1b88c12447b0b70b9" \
  "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4" \
  "93374019"
download_chromosome \
  chr1.fa.gz "f069c41e7cc8c2d3a7655cbb2d4186b8" \
  "04ee6db2e94ccc4daddc168453189d8c17a01454ba67ac0443a73a0401408ee0" \
  "253935557"
download_chromosome \
  chr9.fa.gz "f7e98217b35f5a7451f1166196b4b33c" \
  "2a7cc20841202497a89700a4e6f9a342f138bad761fab64c673fa95d3f773a1f" \
  "141162618"

selection_check="$(mktemp "$SOURCE_DIR/selection.XXXXXX.json")"
trap 'rm -f -- "$selection_check"' EXIT
python3 "$ROOT/reproduce/bioinformatics/build_holdout_panel.py" select \
  --lncrna-fasta "$SOURCE_DIR/gencode.v49.lncRNA_transcripts.fa.gz" \
  --annotation-gtf "$SOURCE_DIR/gencode.v49.annotation.gtf.gz" \
  --development-exclusions "$ROOT/paper/bioinformatics/development_query_exclusions.tsv" \
  --output "$selection_check"
cmp -- "$selection_check" "$ROOT/paper/bioinformatics/holdout_selection.json"

python3 "$ROOT/reproduce/bioinformatics/build_holdout_panel.py" materialize \
  --selection "$ROOT/paper/bioinformatics/holdout_selection.json" \
  --lncrna-fasta "$SOURCE_DIR/gencode.v49.lncRNA_transcripts.fa.gz" \
  --chromosome-dir "$SOURCE_DIR/chromosomes" \
  --output-root "$ROOT/reproduce/bioinformatics/holdout_inputs" \
  --manifest "$ROOT/paper/bioinformatics/holdout_manifest.tsv" \
  --manifest-sha256 "$ROOT/paper/bioinformatics/holdout_manifest.sha256"

(cd "$ROOT/paper/bioinformatics" && sha256sum -c holdout_manifest.sha256)
echo "Bioinformatics Phase 2 holdout inputs reconstructed"
