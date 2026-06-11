#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_SMOKE="$ROOT/scripts/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke.sh"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_emission_only_consumer_shadow_first1_clean"}"
BUILD_BIN="${BUILD_BIN:-1}"

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK"
BUILD_BIN=0 BIN="$BIN" WORK="$WORK" bash "$BASE_SMOKE" >"$WORK/base_stdout.log"

python3 - "$WORK/neat1_first1/audit/candidate/stderr.log" <<'PY'
import sys
from pathlib import Path

stderr = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
bench = {}
for line in stderr.splitlines():
    if line.startswith("benchmark."):
        key, value = line.split("=", 1)
        bench[key.removeprefix("benchmark.")] = value

prefix = "fasim_gasal2_emission_only_consumer_shadow_"

def metric(name: str) -> str:
    key = prefix + name
    if key not in bench:
        raise SystemExit(f"missing {key}")
    return bench[key]

triplex_mismatches = int(metric("triplex_mismatches"))
missing_triplexes = int(metric("missing_triplexes"))
extra_triplexes = int(metric("extra_triplexes"))
decision = metric("decision")
cpu_align_attempts = int(metric("cpu_align_attempts"))
reference_align_attempts = int(metric("realpath_reference_align_attempts"))

if triplex_mismatches != 0 or missing_triplexes != 0 or extra_triplexes != 0:
    raise SystemExit(
        "emission-only first1 shadow is not clean: "
        f"triplex_mismatches={triplex_mismatches} "
        f"missing_triplexes={missing_triplexes} "
        f"extra_triplexes={extra_triplexes} "
        f"decision={decision}"
    )
if cpu_align_attempts >= reference_align_attempts:
    raise SystemExit(
        "emission-only first1 shadow lost CPU align reduction: "
        f"shadow={cpu_align_attempts} reference={reference_align_attempts}"
    )

print("emission_only_consumer_shadow_first1_triplex_mismatches=0")
print("emission_only_consumer_shadow_first1_missing_triplexes=0")
print("emission_only_consumer_shadow_first1_extra_triplexes=0")
print("emission_only_consumer_shadow_first1_cpu_align_attempts=" + str(cpu_align_attempts))
print("emission_only_consumer_shadow_first1_reference_align_attempts=" + str(reference_align_attempts))
print("ok")
PY
