#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIER="${1:-quick}"
BINARY="${BINARY:-$ROOT/.tmp/fasim_longtarget_gasal2_direct}"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-$ROOT/.paper-artifacts/reproduction}"

case "$TIER" in
quick)
  make -C "$ROOT" check-fasim-gasal2-paper-reproduction
  ;;
source-data)
  # Requires the digest-covered Phase 2-4 raw artifact roots at their documented paths.
  make -C "$ROOT" paper-source-data
  ;;
figures)
  make -C "$ROOT" paper-figures
  ;;
core-gpu)
  # Requires two visible RTX 4090-class GPUs and all inputs in input_manifest.tsv.
  python3 "$ROOT/scripts/run_fasim_gasal2_paper_phase2.py" \
    --manifest "$ROOT/paper/workload_manifest.tsv" \
    --binary "$BINARY" --artifact-root "$ARTIFACT_ROOT/phase2-core" \
    --workload-id c1_h19_chr21_chr22_fast_topk \
    --workload-id c4_h19_chr21_two_slot \
    --workload-id c4_h19_chr22_two_slot
  ;;
max8)
  # Bounded max8 only; this command does not expand to the complete transcript or genome.
  python3 "$ROOT/scripts/run_fasim_gasal2_paper_phase2.py" \
    --manifest "$ROOT/paper/workload_manifest.tsv" \
    --binary "$BINARY" --artifact-root "$ARTIFACT_ROOT/phase2-max8" \
    --workload-id c7_kcnq_max8_chr22
  ;;
*)
  echo "usage: $0 {quick|source-data|figures|core-gpu|max8}" >&2
  exit 2
  ;;
esac
