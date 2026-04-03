#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BIN="${BIN:-"$ROOT/fasim_longtarget_x86"}"
if [[ ! -x "$BIN" ]]; then
  (cd "$ROOT" && make build-fasim)
fi

run_case() {
  local label="$1"
  local f1_arg="$2"
  local work_dir="$3"

  rm -rf "$work_dir"
  mkdir -p "$work_dir/out" "$work_dir/inputs"
  cp "$ROOT/testDNA.fa" "$work_dir/inputs/testDNA.fa"
  cp "$ROOT/H19.fa" "$work_dir/inputs/H19.fa"

  (
    cd "$work_dir/inputs"
    FASIM_VERBOSE=0 FASIM_OUTPUT_MODE=lite "$BIN" \
      -f1 "$f1_arg" -f2 "H19.fa" -r 1 -O "$work_dir/out" >/dev/null
  )

  local out_file="$work_dir/out/hg19-H19-testDNA-TFOsorted.lite"
  if [[ ! -s "$out_file" ]]; then
    echo "[$label] expected lite output missing: $out_file" >&2
    ls -la "$work_dir/out" >&2 || true
    exit 1
  fi

  if [[ -e "$work_dir/out/hg19-H19-testDNA-TFOsorted" ]]; then
    echo "[$label] unexpected full TFOsorted produced in lite mode" >&2
    exit 1
  fi

  local header
  header="$(head -n 1 "$out_file" | tr -d '\r')"
  if [[ "$header" != $'Chr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\tMeanStability' ]]; then
    echo "[$label] unexpected header:" >&2
    echo "$header" >&2
    exit 1
  fi
}

base_work="$ROOT/.tmp/check_fasim_lite_output"
run_case "basename" "testDNA.fa" "$base_work/basename"
run_case "path" "$base_work/basename/inputs/testDNA.fa" "$base_work/path"

echo "ok"

