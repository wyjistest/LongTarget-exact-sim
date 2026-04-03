#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
ORACLE_TARGET="${ORACLE_TARGET:-$ROOT_DIR/longtarget_x86}"
TARGET="${TARGET:-$ROOT_DIR/longtarget_x86}"
OUTPUT_SUBDIR="${OUTPUT_SUBDIR:-rule_matrix_exactness}"
WORK_DIR="$ROOT_DIR/.tmp/$OUTPUT_SUBDIR"
EXPECTED_DIR="${EXPECTED_DIR:-$ROOT_DIR/tests/oracle_matrix}"
ORACLE_BACKEND="${ORACLE_BACKEND:-}"
BACKEND="${BACKEND:-}"
GENERATE_ORACLE=0

if [ "${1:-}" = "--generate-oracle" ]; then
  GENERATE_ORACLE=1
fi

RUN_PREFIX=""
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  RUN_PREFIX="arch -x86_64"
fi

run_case() {
  label="$1"
  rule="$2"
  strand="$3"
  output_dir="$4"
  target_bin="$5"
  backend="$6"

  rm -rf "$output_dir"
  mkdir -p "$output_dir"

  set -- "$target_bin" -f1 testDNA.fa -f2 H19.fa -r "$rule" -O "$output_dir"
  if [ "$strand" != "0" ]; then
    set -- "$@" -t "$strand"
  fi

  if [ -n "$backend" ]; then
    LONGTARGET_SIM_INITIAL_BACKEND="$backend" $RUN_PREFIX "$@"
  else
    $RUN_PREFIX "$@"
  fi

  echo "$label"
}

run_case_matrix() {
  base_dir="$1"
  target_bin="$2"
  backend="$3"

  run_case rule0_both 0 0 "$base_dir/rule0_both" "$target_bin" "$backend" >/dev/null

  rule=1
  while [ "$rule" -le 6 ]; do
    run_case "para_rule$rule" "$rule" 1 "$base_dir/para_rule$rule" "$target_bin" "$backend" >/dev/null
    rule=$((rule + 1))
  done

  rule=1
  while [ "$rule" -le 18 ]; do
    run_case "anti_rule$rule" "$rule" -1 "$base_dir/anti_rule$rule" "$target_bin" "$backend" >/dev/null
    rule=$((rule + 1))
  done
}

if [ "$GENERATE_ORACLE" -eq 1 ]; then
  if [ ! -x "$ORACLE_TARGET" ]; then
    echo "missing oracle binary: $ORACLE_TARGET" >&2
    exit 1
  fi
  rm -rf "$EXPECTED_DIR"
  mkdir -p "$EXPECTED_DIR"
  cd "$ROOT_DIR"
  run_case_matrix "$EXPECTED_DIR" "$ORACLE_TARGET" "$ORACLE_BACKEND"
  echo "matrix oracle updated in $EXPECTED_DIR"
  exit 0
fi

if [ ! -x "$TARGET" ]; then
  echo "missing binary: $TARGET" >&2
  exit 1
fi

if [ ! -d "$EXPECTED_DIR" ]; then
  echo "missing oracle directory: $EXPECTED_DIR" >&2
  exit 1
fi

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$ROOT_DIR"
run_case_matrix "$WORK_DIR" "$TARGET" "$BACKEND"
diff -ru "$EXPECTED_DIR" "$WORK_DIR"
