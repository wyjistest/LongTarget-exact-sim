#!/usr/bin/env python3
"""Build a network-independent scratch OCI image from one clean source commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
IMAGE_TAG = "longtarget/gasal2-gpu-screen:submission-rc-v2"
CANDIDATE_SHA256 = "ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9"
FILES = (
    "scripts/gasal2_gpu_screen.py",
    "scripts/gasal2_candidate_sites.py",
    "scripts/gasal2_longtarget.py",
    "scripts/fasim_tfo_archive.py",
    "schemas/gasal2_gpu_screen_run_report_v1.schema.json",
    "schemas/gasal2_candidate_sites_tsv_v1.schema.json",
    "reproduce/biological_topk/canonicalize_rows.py",
    "reproduce/biological_topk/contract.py",
    "reproduce/biological_topk/recluster_candidate_sites.py",
    "reproduce/bioinformatics_submission_readiness_v2/Dockerfile.runtime",
)
LDD_PATH = re.compile(r"=>\s+(/[^ ]+)|^\s*(/[^ ]+)\s+\(")


class BuildError(RuntimeError):
    pass


def run(arguments: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        tuple(arguments), cwd=ROOT, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if check and completed.returncode != 0:
        raise BuildError(
            completed.stderr.decode("utf-8", errors="replace")
            or completed.stdout.decode("utf-8", errors="replace")
        )
    return completed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_bytes(commit: str, relative: str) -> bytes:
    return run(("git", "show", f"{commit}:{relative}")).stdout


def write_git_file(commit: str, relative: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(git_bytes(commit, relative))


def copy_root_file(source: Path, rootfs: Path, destination: Path | None = None) -> Path:
    resolved = source.resolve()
    target_relative = destination or Path(str(resolved).lstrip("/"))
    target = rootfs / target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        target.unlink()
    shutil.copy2(resolved, target)
    return target


def ldd_dependencies(path: Path) -> set[Path]:
    completed = run(("ldd", str(path)))
    dependencies: set[Path] = set()
    for raw in completed.stdout.decode("utf-8").splitlines():
        match = LDD_PATH.search(raw)
        if match:
            dependencies.add(Path(match.group(1) or match.group(2)))
        if "not found" in raw:
            raise BuildError(f"unresolved dependency for {path}: {raw}")
    return dependencies


def copy_dependencies(paths: Iterable[Path], rootfs: Path) -> None:
    pending = list(paths)
    copied: set[Path] = set()
    while pending:
        source = pending.pop()
        resolved = source.resolve()
        if resolved in copied:
            continue
        copied.add(resolved)
        copy_root_file(resolved, rootfs, Path(str(source).lstrip("/")))
        pending.extend(ldd_dependencies(resolved) - copied)


def build(source_commit: str, artifact_root: Path, candidate_binary: Path) -> dict[str, object]:
    if run(("git", "status", "--porcelain=v1")).stdout:
        raise BuildError("runtime image build requires a clean worktree")
    if run(("git", "rev-parse", "HEAD")).stdout.decode().strip() != source_commit:
        raise BuildError("runtime image build requires source commit at HEAD")
    if sha256_file(candidate_binary) != CANDIDATE_SHA256:
        raise BuildError("candidate binary digest drift")
    if artifact_root.exists():
        raise BuildError(f"artifact root already exists: {artifact_root}")
    context = artifact_root / "container-context"
    rootfs = context / "rootfs"
    app = rootfs / "opt/gasal2"
    app.mkdir(parents=True)
    mapping = {
        "scripts/gasal2_gpu_screen.py": app / "gasal2_gpu_screen.py",
        "scripts/gasal2_candidate_sites.py": app / "gasal2_candidate_sites.py",
        "scripts/gasal2_longtarget.py": app / "gasal2_longtarget.py",
        "scripts/fasim_tfo_archive.py": app / "fasim_tfo_archive.py",
        "schemas/gasal2_gpu_screen_run_report_v1.schema.json": app / "schemas/gasal2_gpu_screen_run_report_v1.schema.json",
        "schemas/gasal2_candidate_sites_tsv_v1.schema.json": app / "schemas/gasal2_candidate_sites_tsv_v1.schema.json",
        "reproduce/biological_topk/canonicalize_rows.py": app / "biological_topk/canonicalize_rows.py",
        "reproduce/biological_topk/contract.py": app / "biological_topk/contract.py",
        "reproduce/biological_topk/recluster_candidate_sites.py": app / "biological_topk/recluster_candidate_sites.py",
    }
    source_sha256 = {}
    for relative, destination in mapping.items():
        write_git_file(source_commit, relative, destination)
        source_sha256[relative] = sha256_file(destination)
    dockerfile = context / "Dockerfile"
    write_git_file(
        source_commit,
        "reproduce/bioinformatics_submission_readiness_v2/Dockerfile.runtime",
        dockerfile,
    )
    binary_in_image = app / "bin/fasim_longtarget_gasal2"
    binary_in_image.parent.mkdir()
    shutil.copy2(candidate_binary, binary_in_image)
    binary_in_image.chmod(0o755)

    python = Path("/usr/bin/python3.11")
    copy_root_file(python, rootfs, Path("usr/bin/python3.11"))
    stdlib_source = Path("/usr/lib/python3.11")
    shutil.copytree(stdlib_source, rootfs / "usr/lib/python3.11", symlinks=True)
    shared_objects = {
        path.resolve()
        for path in stdlib_source.rglob("*.so")
        if path.is_file()
    }
    dependency_sources = {python, candidate_binary}
    dependency_sources.update(shared_objects)
    copy_dependencies(dependency_sources, rootfs)
    (rootfs / "tmp").mkdir()
    (rootfs / "work").mkdir()

    runtime_identity = {
        "schema_version": 1,
        "execution_mode": "gpu-screen",
        "scientific_contract": "biological_topk_candidate_site_v1",
        "output_schema": "gasal2_candidate_sites_tsv_v1",
        "software_epoch": "submission_rc_v2",
        "implementation_commit": source_commit,
        "candidate_binary_sha256": CANDIDATE_SHA256,
        "container_image_digest": None,
        "source_sha256": source_sha256,
        "base_image": "scratch",
    }
    (app / "runtime_identity.json").write_text(
        json.dumps(runtime_identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result = run(("docker", "build", "--network=none", "--tag", IMAGE_TAG, str(context)))
    image_digest = run(("docker", "image", "inspect", IMAGE_TAG, "--format", "{{.Id}}" )).stdout.decode().strip()
    archive = artifact_root / "gasal2-gpu-screen-submission-rc-v2.tar"
    with archive.open("wb") as handle:
        saved = subprocess.run(
            ("docker", "save", IMAGE_TAG), cwd=ROOT, check=False, stdout=handle, stderr=subprocess.PIPE
        )
    if saved.returncode != 0:
        raise BuildError(saved.stderr.decode("utf-8", errors="replace"))
    return {
        "schema_version": 1,
        "implementation_commit": source_commit,
        "image_tag": IMAGE_TAG,
        "container_image_digest": image_digest,
        "container_archive_path": archive.relative_to(ROOT).as_posix(),
        "container_archive_sha256": sha256_file(archive),
        "container_archive_bytes": archive.stat().st_size,
        "candidate_binary_source_path": candidate_binary.relative_to(ROOT).as_posix(),
        "candidate_binary_sha256": CANDIDATE_SHA256,
        "source_sha256": source_sha256,
        "docker_build_stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "base_image": "scratch_host_runtime_snapshot",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase1",
    )
    parser.add_argument(
        "--candidate-binary",
        type=Path,
        default=ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_gasal2",
    )
    args = parser.parse_args()
    try:
        receipt = build(args.source_commit, args.artifact_root.resolve(), args.candidate_binary.resolve())
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    except (BuildError, OSError, ValueError, KeyError) as error:
        print(f"runtime image build failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
