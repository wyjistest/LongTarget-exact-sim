#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GASAL2_DIR="${GASAL2_DIR:-"$ROOT/.tmp/GASAL2"}"
GASAL2_REPO_URL="${GASAL2_REPO_URL:-https://github.com/nahmedraja/GASAL2.git}"
GASAL2_COMMIT="${GASAL2_COMMIT:-106d94ee53fc847214fb05f2f9f892538a5d3baf}"
GASAL2_PATCH="${GASAL2_PATCH:-"$ROOT/patches/gasal2-fasim-bridge.patch"}"

if [[ ! -s "$GASAL2_PATCH" ]]; then
  echo "missing GASAL2 patch: $GASAL2_PATCH" >&2
  exit 1
fi

if [[ ! -d "$GASAL2_DIR/.git" ]]; then
  mkdir -p "$(dirname "$GASAL2_DIR")"
  git clone "$GASAL2_REPO_URL" "$GASAL2_DIR"
fi

if [[ "$(git -C "$GASAL2_DIR" rev-parse HEAD)" != "$GASAL2_COMMIT" ]]; then
  if ! git -C "$GASAL2_DIR" diff --quiet --ignore-submodules -- ||
     ! git -C "$GASAL2_DIR" diff --cached --quiet --ignore-submodules --; then
    echo "GASAL2 checkout is dirty and not at expected commit; refusing to overwrite" >&2
    exit 1
  fi
  git -C "$GASAL2_DIR" fetch --depth=1 origin "$GASAL2_COMMIT"
  git -C "$GASAL2_DIR" checkout --detach "$GASAL2_COMMIT"
fi

patch_body="$(mktemp)"
current_diff="$(mktemp)"
trap 'rm -f "$patch_body" "$current_diff"' EXIT

sed -n '/^diff --git /,$p' "$GASAL2_PATCH" >"$patch_body"
git -C "$GASAL2_DIR" diff --binary >"$current_diff"

if cmp -s "$patch_body" "$current_diff"; then
  echo "GASAL2 patch already applied"
  exit 0
fi

if [[ -s "$current_diff" ]]; then
  echo "GASAL2 checkout has local changes that do not match $GASAL2_PATCH" >&2
  exit 1
fi

git -C "$GASAL2_DIR" apply --check "$GASAL2_PATCH"
git -C "$GASAL2_DIR" apply "$GASAL2_PATCH"
echo "GASAL2 patch applied"
