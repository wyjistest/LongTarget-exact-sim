#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"

python3 - "$CPP" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

cpp = Path(sys.argv[1]).read_text(encoding="utf-8")
makefile = Path(sys.argv[2]).read_text(encoding="utf-8")

required_cpp = [
    "FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE",
    "fasim_gasal2_phase7_v3_narrow_certificate_runtime",
]
for needle in required_cpp:
    if needle not in cpp:
        raise SystemExit(f"missing v3 narrow certificate marker: {needle}")

required_targets = [
    "check-fasim-gasal2-phase7-v3-narrow-certificate-env:",
    "check-fasim-gasal2-phase7-v3-narrow-certificate-runtime-smoke:",
]
for target in required_targets:
    if target not in makefile:
        raise SystemExit(f"missing Makefile target: {target}")

print("phase7_v3_narrow_certificate_env=pass")
print("ok")
PY
