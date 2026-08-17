#!/usr/bin/env python3
"""Build the immutable tracked-evidence registry for the predecessor epoch."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREDECESSOR_COMMIT = "7fae3de6b13780d7cc0776038489cf2f22072339"
OUTPUT = ROOT / "paper/biological_topk_successor/v1_evidence_registry.tsv"
PREFIXES = (
    "goal-biological-topk.md",
    "paper/biological_topk/",
    "reproduce/biological_topk/",
    "schemas/biological_topk_program_state.schema.json",
    "scripts/check_biological_topk",
    "tests/biological_topk/",
)


class RegistryError(RuntimeError):
    pass


def git(*args: str) -> bytes:
    completed = subprocess.run(
        ("git", *args), cwd=ROOT, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode != 0:
        raise RegistryError(completed.stderr.decode("utf-8", errors="replace"))
    return completed.stdout


def included(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in PREFIXES)


def build_bytes() -> bytes:
    rows = [
        "path\tfrozen_at_commit\tgit_blob_sha1\tblob_sha256\tsize_bytes\tevidence_role"
    ]
    listing = git("ls-tree", "-r", PREDECESSOR_COMMIT).decode("utf-8").splitlines()
    for line in listing:
        metadata, path = line.split("\t", 1)
        _, kind, blob = metadata.split()
        if kind != "blob" or not included(path):
            continue
        payload = git("show", f"{PREDECESSOR_COMMIT}:{path}")
        rows.append(
            "\t".join(
                (
                    path,
                    PREDECESSOR_COMMIT,
                    blob,
                    hashlib.sha256(payload).hexdigest(),
                    str(len(payload)),
                    "immutable_predecessor_validation_evidence",
                )
            )
        )
    if len(rows) < 50:
        raise RegistryError("predecessor registry unexpectedly small")
    return ("\n".join(rows) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_bytes()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(expected)
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        return 0
    if not OUTPUT.is_file() or OUTPUT.read_bytes() != expected:
        raise RegistryError("predecessor evidence registry does not reproduce")
    print("predecessor evidence registry reproduces byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
