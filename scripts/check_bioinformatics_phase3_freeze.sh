#!/usr/bin/env bash
set -euo pipefail

if [[ "${PHASE3_FREEZE_CLEAN_BOOTSTRAP+x}" != "x" \
      || "${PHASE3_FREEZE_CLEAN_BOOTSTRAP-}" != "phase3-freeze-v1" ]]; then
  printf '%s\n' \
    "Phase 3 checker clean bootstrap failed: missing or malformed contract" >&2
  exit 2
fi
unset PHASE3_FREEZE_CLEAN_BOOTSTRAP

checker_source="${BASH_SOURCE[0]}"
if [[ "$checker_source" == */* ]]; then
  checker_directory="${checker_source%/*}"
else
  checker_directory="."
fi
ROOT="$(cd -- "$checker_directory/.." && pwd -P)"
unset checker_source checker_directory
BASELINE="bf94dc75c5fe3e996472a1e90d242f582da361bf"
FETCHER="$ROOT/reproduce/bioinformatics/fetch_application_inputs.sh"
WORK="${WORK:-$ROOT/.tmp/check_bioinformatics_phase3_freeze}"

trusted_bash_receipt="$(python3 - "$BASH" <<'PY_TRUSTED_BASH'
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


argument = sys.argv[1]
if not os.path.isabs(argument) or any(character in argument for character in "\r\n\t"):
    raise SystemExit("Phase 3 checker trusted Bash validation failed: unsafe path")
trusted_bash = Path(os.path.realpath(argument))
if any(character in str(trusted_bash) for character in "\r\n\t"):
    raise SystemExit("Phase 3 checker trusted Bash validation failed: unsafe path")
try:
    named = os.lstat(trusted_bash)
except OSError as error:
    raise SystemExit(
        f"Phase 3 checker trusted Bash validation failed: {error}"
    ) from error
if (
    not trusted_bash.is_absolute()
    or os.path.realpath(trusted_bash) != str(trusted_bash)
    or not stat.S_ISREG(named.st_mode)
    or not named.st_mode & 0o111
    or not os.access(trusted_bash, os.X_OK)
):
    raise SystemExit("Phase 3 checker trusted Bash validation failed: unsafe executable")
flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
try:
    descriptor = os.open(trusted_bash, flags)
except OSError as error:
    raise SystemExit(
        f"Phase 3 checker trusted Bash validation failed: {error}"
    ) from error
try:
    retained = os.fstat(descriptor)
    if (
        not stat.S_ISREG(retained.st_mode)
        or (retained.st_dev, retained.st_ino) != (named.st_dev, named.st_ino)
        or not retained.st_mode & 0o111
    ):
        raise SystemExit(
            "Phase 3 checker trusted Bash validation failed: identity changed"
        )
finally:
    os.close(descriptor)
print(f"{trusted_bash}\t{retained.st_dev}\t{retained.st_ino}")
PY_TRUSTED_BASH
)"
IFS=$'\t' read -r TRUSTED_BASH TRUSTED_BASH_DEVICE TRUSTED_BASH_INODE \
  <<<"$trusted_bash_receipt"
if [[ -z "$TRUSTED_BASH" || ! "$TRUSTED_BASH_DEVICE" =~ ^[0-9]+$ \
      || ! "$TRUSTED_BASH_INODE" =~ ^[0-9]+$ ]]; then
  echo "Phase 3 checker trusted Bash validation failed: malformed receipt" >&2
  exit 1
fi

# BEGIN_PHASE3_SOURCE_CACHE_BINDING
capture_source_cache_binding() {
  python3 - "$ROOT" <<'PY_SOURCE_CACHE_BINDING'
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path


root = Path(sys.argv[1])
temporary_name = ".tmp"
cache_name = "bioinformatics_application_sources"
expected_names = (
    "gencode.v49.lncRNA_transcripts.fa.gz",
    "gencode.v49.annotation.gtf.gz",
    "chr21.fa.gz",
    "chr22.fa.gz",
)
expected_name_set = set(expected_names)
directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
file_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def fail(message: str) -> None:
    raise SystemExit(f"Bioinformatics Phase 3 cache preflight failed: {message}")


def directory_binding(metadata: os.stat_result) -> dict[str, int | bool]:
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "present": True,
    }


def missing_directory_binding() -> dict[str, int | bool | None]:
    return {"device": None, "inode": None, "present": False}


def archive_binding(name: str, metadata: os.stat_result) -> dict[str, int | str]:
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": metadata.st_mode,
        "mtime_ns": metadata.st_mtime_ns,
        "name": name,
        "nlink": metadata.st_nlink,
        "size": metadata.st_size,
        "type": "regular",
    }


def retained_directory(
    name: str,
    *,
    parent_fd: int,
    unsafe_message: str,
) -> tuple[int, os.stat_result]:
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        raise
    if not stat.S_ISDIR(named.st_mode):
        fail(unsafe_message)
    try:
        descriptor = os.open(name, directory_flags, dir_fd=parent_fd)
    except OSError:
        fail(unsafe_message)
    retained = os.fstat(descriptor)
    if not stat.S_ISDIR(retained.st_mode) or (
        retained.st_dev,
        retained.st_ino,
    ) != (named.st_dev, named.st_ino):
        os.close(descriptor)
        fail(unsafe_message)
    return descriptor, retained


def require_retained_directory(
    name: str,
    *,
    parent_fd: int,
    descriptor: int,
    expected: os.stat_result,
    changed_message: str,
) -> None:
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        retained = os.fstat(descriptor)
    except OSError:
        fail(changed_message)
    if (
        not stat.S_ISDIR(named.st_mode)
        or not stat.S_ISDIR(retained.st_mode)
        or (named.st_dev, named.st_ino) != (expected.st_dev, expected.st_ino)
        or (retained.st_dev, retained.st_ino) != (
            expected.st_dev,
            expected.st_ino,
        )
    ):
        fail(changed_message)


def require_missing_directory(
    name: str,
    *,
    parent_fd: int,
    changed_message: str,
) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError:
        fail(changed_message)
    fail(changed_message)


def emit(
    *,
    count: int,
    temporary: dict[str, int | bool | None],
    cache: dict[str, int | bool | None],
    archives: list[dict[str, int | str]],
) -> None:
    receipt = {
        "archives": archives,
        "cache": cache,
        "count": count,
        "schema_version": 1,
        "temporary": temporary,
    }
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


try:
    root_named = os.lstat(root)
    if not stat.S_ISDIR(root_named.st_mode):
        fail("repository root is unsafe")
    root_fd = os.open(root, directory_flags)
except OSError:
    fail("repository root is unsafe")
try:
    root_retained = os.fstat(root_fd)
    if (root_retained.st_dev, root_retained.st_ino) != (
        root_named.st_dev,
        root_named.st_ino,
    ):
        fail("repository root changed during preflight")
    try:
        temporary_fd, temporary_identity = retained_directory(
            temporary_name,
            parent_fd=root_fd,
            unsafe_message="unsafe Phase 3 source-cache parent",
        )
    except FileNotFoundError:
        require_missing_directory(
            temporary_name,
            parent_fd=root_fd,
            changed_message="source-cache parent changed during inspection",
        )
        current_root = os.lstat(root)
        if (current_root.st_dev, current_root.st_ino) != (
            root_retained.st_dev,
            root_retained.st_ino,
        ):
            fail("repository root changed during preflight")
        emit(
            count=0,
            temporary=missing_directory_binding(),
            cache=missing_directory_binding(),
            archives=[],
        )
        raise SystemExit(0)
    try:
        try:
            cache_fd, cache_identity = retained_directory(
                cache_name,
                parent_fd=temporary_fd,
                unsafe_message="unsafe Phase 3 source-cache directory",
            )
        except FileNotFoundError:
            require_missing_directory(
                cache_name,
                parent_fd=temporary_fd,
                changed_message="source-cache directory changed during inspection",
            )
            require_retained_directory(
                temporary_name,
                parent_fd=root_fd,
                descriptor=temporary_fd,
                expected=temporary_identity,
                changed_message="source-cache parent changed during inspection",
            )
            emit(
                count=0,
                temporary=directory_binding(temporary_identity),
                cache=missing_directory_binding(),
                archives=[],
            )
            raise SystemExit(0)
        try:
            names = set(os.listdir(cache_fd))
            unexpected = sorted(names - expected_name_set)
            if unexpected:
                fail(
                    "unexpected Phase 3 source-cache entry: "
                    + ", ".join(unexpected)
                )
            if names and names != expected_name_set:
                fail("source cache must contain zero or exactly four canonical archives")
            if not names:
                if os.listdir(cache_fd):
                    fail("source-cache directory changed during inspection")
                require_retained_directory(
                    cache_name,
                    parent_fd=temporary_fd,
                    descriptor=cache_fd,
                    expected=cache_identity,
                    changed_message="source-cache directory changed during inspection",
                )
                require_retained_directory(
                    temporary_name,
                    parent_fd=root_fd,
                    descriptor=temporary_fd,
                    expected=temporary_identity,
                    changed_message="source-cache parent changed during inspection",
                )
                emit(
                    count=0,
                    temporary=directory_binding(temporary_identity),
                    cache=directory_binding(cache_identity),
                    archives=[],
                )
                raise SystemExit(0)

            seen_inodes: set[tuple[int, int]] = set()
            archives: list[dict[str, int | str]] = []
            for name in expected_names:
                try:
                    named = os.stat(name, dir_fd=cache_fd, follow_symlinks=False)
                except FileNotFoundError:
                    fail("source cache changed during archive validation")
                if not stat.S_ISREG(named.st_mode):
                    fail(f"source-cache entry is not a regular file: {name}")
                if named.st_nlink != 1:
                    fail(f"source-cache archive has a hardlink alias: {name}")
                inode = (named.st_dev, named.st_ino)
                if inode in seen_inodes:
                    fail(f"source-cache archives share an inode: {name}")
                seen_inodes.add(inode)
                try:
                    descriptor = os.open(name, file_flags, dir_fd=cache_fd)
                except OSError:
                    fail(f"source-cache archive changed while opening: {name}")
                try:
                    opened = os.fstat(descriptor)
                    if (
                        not stat.S_ISREG(opened.st_mode)
                        or opened.st_nlink != 1
                        or archive_binding(name, opened) != archive_binding(name, named)
                    ):
                        fail(f"source-cache archive changed while opening: {name}")
                finally:
                    os.close(descriptor)
                try:
                    current = os.stat(
                        name,
                        dir_fd=cache_fd,
                        follow_symlinks=False,
                    )
                except OSError:
                    fail("source cache changed during archive validation")
                if archive_binding(name, current) != archive_binding(name, named):
                    fail("source cache changed during archive validation")
                archives.append(archive_binding(name, named))

            if set(os.listdir(cache_fd)) != expected_name_set:
                fail("source-cache directory changed during inspection")
            require_retained_directory(
                cache_name,
                parent_fd=temporary_fd,
                descriptor=cache_fd,
                expected=cache_identity,
                changed_message="source-cache directory changed during inspection",
            )
            require_retained_directory(
                temporary_name,
                parent_fd=root_fd,
                descriptor=temporary_fd,
                expected=temporary_identity,
                changed_message="source-cache parent changed during inspection",
            )
            emit(
                count=4,
                temporary=directory_binding(temporary_identity),
                cache=directory_binding(cache_identity),
                archives=archives,
            )
        finally:
            os.close(cache_fd)
    finally:
        os.close(temporary_fd)
finally:
    os.close(root_fd)
PY_SOURCE_CACHE_BINDING
}

source_cache_count_from_binding() {
  python3 - "$1" <<'PY_SOURCE_CACHE_COUNT'
from __future__ import annotations

import json
import sys


try:
    receipt = json.loads(sys.argv[1])
except (json.JSONDecodeError, TypeError) as error:
    raise SystemExit(
        f"Bioinformatics Phase 3 cache binding receipt is malformed: {error}"
    ) from error
if not isinstance(receipt, dict):
    raise SystemExit("Bioinformatics Phase 3 cache binding receipt is malformed")
count = receipt.get("count")
if not isinstance(count, int) or isinstance(count, bool) or count not in {0, 4}:
    raise SystemExit("Bioinformatics Phase 3 cache binding count is malformed")
print(count)
PY_SOURCE_CACHE_COUNT
}

require_source_cache_binding() {
  local expected="$1"
  local current
  if ! current="$(capture_source_cache_binding)"; then
    echo "Bioinformatics Phase 3 cache binding changed: fresh inspection failed" >&2
    return 1
  fi
  if [[ "$current" != "$expected" ]]; then
    echo "Bioinformatics Phase 3 cache binding changed: structural receipt differs" >&2
    return 1
  fi
}
# END_PHASE3_SOURCE_CACHE_BINDING

capture_source_cache_binding >/dev/null

workspace_receipt="$(python3 - "$ROOT" "$WORK" <<'PY_WORKSPACE'
from __future__ import annotations

import os
import secrets
import stat
import sys
from pathlib import Path


root = Path(os.path.realpath(sys.argv[1]))
base_argument = sys.argv[2]
if any(character in base_argument for character in "\r\n\t"):
    raise SystemExit("Phase 3 checker workspace failed: invalid work base path")
base = Path(os.path.abspath(base_argument))
directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def fail(message: str) -> None:
    raise SystemExit(f"Phase 3 checker workspace failed: {message}")


def within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def projected_physical_path(path: Path) -> Path:
    missing: list[str] = []
    current = path
    while not os.path.lexists(current):
        missing.append(current.name)
        parent = current.parent
        if parent == current:
            fail("cannot resolve work base")
        current = parent
    physical = Path(os.path.realpath(current))
    for name in reversed(missing):
        physical /= name
    return Path(os.path.normpath(physical))


source_cache = projected_physical_path(
    root / ".tmp/bioinformatics_application_sources"
)


def require_allowed_location(path: Path) -> None:
    repository_temporary = root / ".tmp"
    if within(path, source_cache):
        fail("work base overlaps Phase 3 source cache")
    if within(path, root) and not within(path, repository_temporary):
        fail("Phase 3 checker work base overlaps protected repository paths")


require_allowed_location(projected_physical_path(base))
if os.path.lexists(base):
    initial = os.lstat(base)
    if stat.S_ISLNK(initial.st_mode):
        fail("work base final component is a symlink")
    if not stat.S_ISDIR(initial.st_mode):
        fail("work base is not a directory")
else:
    try:
        os.makedirs(base, mode=0o700, exist_ok=False)
    except FileExistsError:
        pass
    except OSError as error:
        fail(f"cannot create work base: {error}")

named_base = os.lstat(base)
if stat.S_ISLNK(named_base.st_mode):
    fail("work base final component is a symlink")
if not stat.S_ISDIR(named_base.st_mode):
    fail("work base is not a directory")
base_real = Path(os.path.realpath(base))
require_allowed_location(base_real)
try:
    base_fd = os.open(base, directory_flags)
except OSError as error:
    fail(f"cannot retain work base: {error}")
try:
    retained_base = os.fstat(base_fd)
    if not stat.S_ISDIR(retained_base.st_mode) or (
        retained_base.st_dev,
        retained_base.st_ino,
    ) != (named_base.st_dev, named_base.st_ino):
        fail("work base identity changed during setup")

    run_name = ""
    for _attempt in range(128):
        candidate = (
            f"bioinformatics-phase3-freeze.{os.getpid()}."
            f"{secrets.token_hex(8)}"
        )
        try:
            os.mkdir(candidate, mode=0o700, dir_fd=base_fd)
        except FileExistsError:
            continue
        run_name = candidate
        break
    if not run_name:
        fail("cannot allocate exclusive run directory")

    named_run = os.stat(run_name, dir_fd=base_fd, follow_symlinks=False)
    if not stat.S_ISDIR(named_run.st_mode):
        fail("exclusive run path is not a directory")
    try:
        run_fd = os.open(run_name, directory_flags, dir_fd=base_fd)
    except OSError as error:
        fail(f"cannot retain exclusive run directory: {error}")
    try:
        retained_run = os.fstat(run_fd)
        if (retained_run.st_dev, retained_run.st_ino) != (
            named_run.st_dev,
            named_run.st_ino,
        ):
            fail("exclusive run directory identity changed during setup")
        os.fchmod(run_fd, 0o700)
        retained_run = os.fstat(run_fd)
        if stat.S_IMODE(retained_run.st_mode) != 0o700:
            fail("exclusive run directory mode is not 0700")
        current_base = os.lstat(base)
        if (current_base.st_dev, current_base.st_ino) != (
            retained_base.st_dev,
            retained_base.st_ino,
        ):
            fail("work base identity changed after run creation")
        run_real = base_real / run_name
        print(
            "\t".join(
                (
                    str(run_real),
                    str(base_real),
                    str(retained_base.st_dev),
                    str(retained_base.st_ino),
                    str(retained_run.st_dev),
                    str(retained_run.st_ino),
                )
            )
        )
    finally:
        os.close(run_fd)
finally:
    os.close(base_fd)
PY_WORKSPACE
)"
IFS=$'\t' read -r \
  WORK WORK_BASE_REAL WORK_BASE_DEVICE WORK_BASE_INODE WORK_DEVICE WORK_INODE \
  <<<"$workspace_receipt"
if [[ -z "$WORK" || -z "$WORK_BASE_REAL" || ! "$WORK_BASE_DEVICE" =~ ^[0-9]+$ \
      || ! "$WORK_BASE_INODE" =~ ^[0-9]+$ || ! "$WORK_DEVICE" =~ ^[0-9]+$ \
      || ! "$WORK_INODE" =~ ^[0-9]+$ ]]; then
  echo "Phase 3 checker workspace failed: malformed workspace receipt" >&2
  exit 1
fi

validate_workspace_identity() {
  python3 - \
    "$WORK_BASE_REAL" "$WORK_BASE_DEVICE" "$WORK_BASE_INODE" \
    "$WORK" "$WORK_DEVICE" "$WORK_INODE" <<'PY_WORK_IDENTITY'
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


base = Path(sys.argv[1])
expected_base = (int(sys.argv[2]), int(sys.argv[3]))
run = Path(sys.argv[4])
expected_run = (int(sys.argv[5]), int(sys.argv[6]))
flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def verify(path: Path, expected: tuple[int, int], label: str) -> None:
    try:
        named = os.lstat(path)
    except FileNotFoundError:
        raise SystemExit(f"Phase 3 checker workspace failed: missing {label}")
    if not stat.S_ISDIR(named.st_mode) or (named.st_dev, named.st_ino) != expected:
        raise SystemExit(f"Phase 3 checker workspace failed: {label} identity changed")
    descriptor = os.open(path, flags)
    try:
        retained = os.fstat(descriptor)
        if (retained.st_dev, retained.st_ino) != expected:
            raise SystemExit(
                f"Phase 3 checker workspace failed: {label} identity changed"
            )
        if label == "run directory" and stat.S_IMODE(retained.st_mode) != 0o700:
            raise SystemExit("Phase 3 checker workspace failed: run mode changed")
    finally:
        os.close(descriptor)


verify(base, expected_base, "work base")
verify(run, expected_run, "run directory")
if run.parent != base:
    raise SystemExit("Phase 3 checker workspace failed: run escaped work base")
PY_WORK_IDENTITY
}
validate_workspace_identity
authoritative_source_cache_binding="$(capture_source_cache_binding)"
cached_source_count="$(
  source_cache_count_from_binding "$authoritative_source_cache_binding"
)"
before_snapshot="$WORK/application-freeze.before.json"
after_snapshot="$WORK/application-freeze.after.json"

for relative in \
  paper/bioinformatics/README.md \
  paper/bioinformatics/application_input_summary.tsv \
  paper/bioinformatics/application_manifest.sha256 \
  paper/bioinformatics/application_manifest.tsv \
  paper/bioinformatics/application_protocol.md \
  paper/bioinformatics/application_selection.json \
  paper/bioinformatics/application_sources.tsv \
  paper/bioinformatics/claim_evidence.tsv \
  paper/bioinformatics/development_query_exclusions.tsv \
  paper/bioinformatics/holdout_manifest.tsv \
  paper/bioinformatics/submission_manifest.tsv \
  reproduce/bioinformatics/application_inputs; do
  if [[ ! -e "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe Bioinformatics Phase 3 freeze dependency: $relative" >&2
    exit 1
  fi
done

# BEGIN_PHASE3_PREEXECUTION_DEPENDENCIES
/usr/bin/python3 -I - \
  "$ROOT" "$BASELINE" \
  "$TRUSTED_BASH" "$TRUSTED_BASH_DEVICE" "$TRUSTED_BASH_INODE" \
  <<'PY_PREEXECUTION_DEPENDENCIES'
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath


root = Path(sys.argv[1])
baseline = sys.argv[2]
trusted_bash = sys.argv[3]
expected_bash_identity = (int(sys.argv[4]), int(sys.argv[5]))
dependency_relatives = (
    "reproduce/bioinformatics/build_application_panel.py",
    "reproduce/bioinformatics/fetch_application_inputs.sh",
    "scripts/check_bioinformatics_phase3_freeze.sh",
    "tests/check_build_bioinformatics_application_panel.py",
)
test_relative = "tests/check_build_bioinformatics_application_panel.py"
directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
file_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


class PreexecutionDependencyError(Exception):
    def __init__(self, message: str, status: int = 1) -> None:
        super().__init__(message)
        self.status = status if 0 < status < 256 else 1


class ParentBinding:
    def __init__(
        self,
        parent_fd: int,
        name: str,
        descriptor: int,
        signature: tuple[int, int, int, int, int, int],
        relative: str,
    ) -> None:
        self.parent_fd = parent_fd
        self.name = name
        self.descriptor = descriptor
        self.signature = signature
        self.relative = relative


class RetainedDependency:
    def __init__(
        self,
        relative: str,
        parent_fd: int,
        name: str,
        descriptor: int,
        signature: tuple[int, int, int, int, int, int],
        parents: list[ParentBinding],
    ) -> None:
        self.relative = relative
        self.parent_fd = parent_fd
        self.name = name
        self.descriptor = descriptor
        self.signature = signature
        self.parents = parents


def fail(message: str, status: int = 1) -> None:
    raise PreexecutionDependencyError(message, status)


def metadata_signature(
    metadata: os.stat_result,
) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


root_fd: int | None = None
root_signature: tuple[int, int, int, int, int, int] | None = None
bash_fd: int | None = None
dependencies: list[RetainedDependency] = []
failure: PreexecutionDependencyError | None = None


def verify_root() -> None:
    if root_fd is None or root_signature is None:
        fail("repository root descriptor is unavailable")
    try:
        named = os.lstat(root)
        retained = os.fstat(root_fd)
    except OSError as error:
        fail(f"repository root identity changed: {error}")
    if (
        not stat.S_ISDIR(named.st_mode)
        or not stat.S_ISDIR(retained.st_mode)
        or metadata_signature(named) != root_signature
        or metadata_signature(retained) != root_signature
    ):
        fail("repository root identity changed")


def close_parent_bindings(bindings: list[ParentBinding]) -> None:
    for binding in reversed(bindings):
        os.close(binding.descriptor)


def open_dependency(relative: str) -> RetainedDependency:
    if root_fd is None:
        fail("repository root descriptor is unavailable")
    path = PurePosixPath(relative)
    parts = path.parts
    if path.is_absolute() or not parts or any(
        part in {"", ".", ".."} for part in parts
    ):
        fail(f"unsafe dependency path: {relative}")
    verify_root()
    current_fd = root_fd
    parents: list[ParentBinding] = []
    dependency_fd: int | None = None
    try:
        for index, name in enumerate(parts[:-1]):
            traversed = "/".join(parts[: index + 1])
            try:
                named = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            except OSError:
                fail(f"unsafe parent directory: {traversed}")
            if not stat.S_ISDIR(named.st_mode):
                fail(f"unsafe parent directory: {traversed}")
            try:
                descriptor = os.open(name, directory_flags, dir_fd=current_fd)
            except OSError:
                fail(f"unsafe parent directory: {traversed}")
            try:
                retained = os.fstat(descriptor)
            except OSError:
                os.close(descriptor)
                fail(f"parent directory identity changed: {traversed}")
            signature = metadata_signature(named)
            if (
                not stat.S_ISDIR(retained.st_mode)
                or metadata_signature(retained) != signature
            ):
                os.close(descriptor)
                fail(f"parent directory identity changed: {traversed}")
            parents.append(
                ParentBinding(current_fd, name, descriptor, signature, traversed)
            )
            current_fd = descriptor
        name = parts[-1]
        try:
            named_dependency = os.stat(
                name,
                dir_fd=current_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            fail(f"missing dependency: {relative}")
        except OSError:
            fail(f"unsafe dependency: {relative}")
        if not stat.S_ISREG(named_dependency.st_mode):
            fail(f"dependency is not a regular file: {relative}")
        if named_dependency.st_nlink != 1:
            fail(f"dependency has a hardlink alias: {relative}")
        try:
            dependency_fd = os.open(name, file_flags, dir_fd=current_fd)
        except OSError:
            fail(f"cannot retain dependency: {relative}")
        retained_dependency = os.fstat(dependency_fd)
        signature = metadata_signature(named_dependency)
        if (
            not stat.S_ISREG(retained_dependency.st_mode)
            or retained_dependency.st_nlink != 1
            or metadata_signature(retained_dependency) != signature
        ):
            fail(f"dependency identity changed while opening: {relative}")
        result = RetainedDependency(
            relative,
            current_fd,
            name,
            dependency_fd,
            signature,
            parents,
        )
        dependency_fd = None
        parents = []
        return result
    finally:
        if dependency_fd is not None:
            os.close(dependency_fd)
        close_parent_bindings(parents)


def verify_dependency(dependency: RetainedDependency) -> None:
    verify_root()
    for binding in dependency.parents:
        try:
            named = os.stat(
                binding.name,
                dir_fd=binding.parent_fd,
                follow_symlinks=False,
            )
            retained = os.fstat(binding.descriptor)
        except OSError:
            fail(f"parent directory identity changed: {binding.relative}")
        if (
            not stat.S_ISDIR(named.st_mode)
            or not stat.S_ISDIR(retained.st_mode)
            or metadata_signature(named) != binding.signature
            or metadata_signature(retained) != binding.signature
        ):
            fail(f"parent directory identity changed: {binding.relative}")
    try:
        named_dependency = os.stat(
            dependency.name,
            dir_fd=dependency.parent_fd,
            follow_symlinks=False,
        )
        retained_dependency = os.fstat(dependency.descriptor)
    except OSError:
        fail(f"dependency bound name changed: {dependency.relative}")
    if (
        not stat.S_ISREG(named_dependency.st_mode)
        or not stat.S_ISREG(retained_dependency.st_mode)
        or named_dependency.st_nlink != 1
        or retained_dependency.st_nlink != 1
        or metadata_signature(named_dependency) != dependency.signature
        or metadata_signature(retained_dependency) != dependency.signature
    ):
        fail(f"dependency identity changed: {dependency.relative}")


def verify_dependencies() -> None:
    for dependency in dependencies:
        verify_dependency(dependency)


def verify_trusted_bash() -> None:
    if bash_fd is None:
        fail("trusted Bash descriptor is unavailable")
    try:
        named = os.lstat(trusted_bash)
        retained = os.fstat(bash_fd)
    except OSError as error:
        fail(f"trusted Bash identity changed: {error}")
    if (
        not os.path.isabs(trusted_bash)
        or os.path.realpath(trusted_bash) != trusted_bash
        or not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(retained.st_mode)
        or (named.st_dev, named.st_ino) != expected_bash_identity
        or (retained.st_dev, retained.st_ino) != expected_bash_identity
        or not retained.st_mode & 0o111
    ):
        fail("trusted Bash identity changed")


def retained_path(dependency: RetainedDependency) -> str:
    return f"/proc/self/fd/{dependency.descriptor}"


def run_git(arguments: list[str], *, allowed_statuses: set[int] = {0}):
    git_path = next(
        (path for path in ("/usr/bin/git", "/bin/git") if os.access(path, os.X_OK)),
        None,
    )
    if git_path is None:
        fail("trusted Git executable is unavailable")
    environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "HOME": "/nonexistent",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    completed = subprocess.run(
        [
            git_path,
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(root),
            *arguments,
        ],
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode not in allowed_statuses:
        fail(
            "Git preexecution check failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed


def verify_git_scope() -> None:
    core_scope = (
        "paper/bioinformatics",
        ":(exclude)paper/bioinformatics/README.md",
        ":(exclude)paper/bioinformatics/submission_manifest.tsv",
        ":(exclude)paper/bioinformatics/application_*",
        "reproduce/bioinformatics",
        ":(exclude)reproduce/bioinformatics/build_application_panel.py",
        ":(exclude)reproduce/bioinformatics/fetch_application_inputs.sh",
        ":(exclude)reproduce/bioinformatics/application_inputs/**",
        "scripts",
        ":(exclude)scripts/check_bioinformatics_phase3_freeze.sh",
        "tests",
        ":(exclude)tests/check_build_bioinformatics_application_panel.py",
        "config",
        "schemas",
        "fasim",
        "cuda",
        "longtarget.cpp",
        "exact_sim.h",
        "sim.h",
        "stats.h",
        "rules.h",
    )
    core_diff = run_git(
        [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--quiet",
            baseline,
            "--",
            *core_scope,
        ],
        allowed_statuses={0, 1},
    )
    if core_diff.returncode == 1:
        fail("Phase 2 or core runtime path changed from bf94dc7")

    allowed_exact = {
        "Makefile",
        "docs/superpowers/plans/2026-07-24-bioinformatics-phase3-application-freeze.md",
        "docs/superpowers/specs/2026-07-24-bioinformatics-phase3-application-design.md",
        "paper/bioinformatics/README.md",
        "paper/bioinformatics/application_input_summary.tsv",
        "paper/bioinformatics/application_manifest.sha256",
        "paper/bioinformatics/application_manifest.tsv",
        "paper/bioinformatics/application_protocol.md",
        "paper/bioinformatics/application_selection.json",
        "paper/bioinformatics/application_sources.tsv",
        "paper/bioinformatics/submission_manifest.tsv",
        "reproduce/bioinformatics/build_application_panel.py",
        "reproduce/bioinformatics/fetch_application_inputs.sh",
        "scripts/check_bioinformatics_phase3_freeze.sh",
        "tests/check_build_bioinformatics_application_panel.py",
    }

    def allowed_checkpoint_path(path: str) -> bool:
        return path in allowed_exact or path.startswith(
            "reproduce/bioinformatics/application_inputs/"
        )

    changed = run_git(
        [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-only",
            "-z",
            baseline,
            "--",
        ]
    ).stdout
    changed_paths = [
        value.decode("utf-8", errors="strict")
        for value in changed.split(b"\0")
        if value
    ]
    disallowed_changed = [
        path for path in changed_paths if not allowed_checkpoint_path(path)
    ]
    if disallowed_changed:
        fail(
            "Phase 2 or core runtime path changed from bf94dc7: "
            + ", ".join(disallowed_changed)
        )

    status = run_git(
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    ).stdout
    parts = status.split(b"\0")
    status_paths: list[str] = []
    index = 0
    while index < len(parts) and parts[index]:
        entry = parts[index].decode("utf-8", errors="strict")
        if len(entry) < 4 or entry[2] != " ":
            fail(f"cannot parse git status entry: {entry!r}")
        code = entry[:2]
        status_paths.append(entry[3:])
        index += 1
        if "R" in code or "C" in code:
            if index >= len(parts) or not parts[index]:
                fail("truncated rename in git status")
            status_paths.append(parts[index].decode("utf-8", errors="strict"))
            index += 1
    disallowed_status = [
        path for path in status_paths if not allowed_checkpoint_path(path)
    ]
    if disallowed_status:
        fail(
            "working tree path outside Phase 3 checkpoint: "
            + ", ".join(disallowed_status)
        )
    run_git(["diff", "--no-ext-diff", "--no-textconv", "--check"])
    run_git(
        ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--check"]
    )


def compile_python_dependency(dependency: RetainedDependency) -> None:
    verify_dependency(dependency)
    os.lseek(dependency.descriptor, 0, os.SEEK_SET)
    blocks: list[bytes] = []
    while block := os.read(dependency.descriptor, 1024 * 1024):
        blocks.append(block)
    verify_dependency(dependency)
    try:
        compile(b"".join(blocks), dependency.relative, "exec")
    except (SyntaxError, ValueError) as error:
        fail(f"Python syntax check failed: {dependency.relative}: {error}")


try:
    if (
        not root.is_absolute()
        or os.path.realpath(root) != str(root)
        or not os.path.isdir("/proc/self/fd")
    ):
        fail("supported Linux repository root or /proc/self/fd is unavailable")
    try:
        named_root = os.lstat(root)
        root_fd = os.open(root, directory_flags)
    except OSError as error:
        fail(f"cannot retain repository root: {error}")
    retained_root = os.fstat(root_fd)
    root_signature = metadata_signature(named_root)
    if (
        not stat.S_ISDIR(named_root.st_mode)
        or not stat.S_ISDIR(retained_root.st_mode)
        or metadata_signature(retained_root) != root_signature
    ):
        fail("repository root identity changed while opening")

    for relative in dependency_relatives:
        dependencies.append(open_dependency(relative))
    verify_dependencies()

    try:
        named_bash = os.lstat(trusted_bash)
        bash_fd = os.open(trusted_bash, file_flags)
    except OSError as error:
        fail(f"cannot retain trusted Bash: {error}")
    retained_bash = os.fstat(bash_fd)
    if (
        not stat.S_ISREG(named_bash.st_mode)
        or not stat.S_ISREG(retained_bash.st_mode)
        or (named_bash.st_dev, named_bash.st_ino) != expected_bash_identity
        or (retained_bash.st_dev, retained_bash.st_ino) != expected_bash_identity
    ):
        fail("trusted Bash identity changed while opening")
    verify_trusted_bash()

    verify_git_scope()
    verify_dependencies()
    verify_trusted_bash()

    by_relative = {
        dependency.relative: dependency for dependency in dependencies
    }
    for relative in (
        "reproduce/bioinformatics/build_application_panel.py",
        test_relative,
    ):
        compile_python_dependency(by_relative[relative])

    inherited_fds = tuple(
        [dependency.descriptor for dependency in dependencies] + [bash_fd]
    )
    bash_path = f"/proc/self/fd/{bash_fd}"
    for relative in (
        "reproduce/bioinformatics/fetch_application_inputs.sh",
        "scripts/check_bioinformatics_phase3_freeze.sh",
    ):
        dependency = by_relative[relative]
        verify_dependencies()
        verify_trusted_bash()
        syntax = subprocess.run(
            [bash_path, "-n", retained_path(dependency)],
            pass_fds=inherited_fds,
            check=False,
        )
        verify_dependencies()
        verify_trusted_bash()
        if syntax.returncode != 0:
            fail(
                f"Bash syntax check failed: {relative}",
                syntax.returncode,
            )

    verify_dependencies()
    verify_trusted_bash()
    child_environment = {
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "PHASE3_AUTHENTICATED_BUILDER": retained_path(
            by_relative["reproduce/bioinformatics/build_application_panel.py"]
        ),
        "PHASE3_AUTHENTICATED_CHECKER": retained_path(
            by_relative["scripts/check_bioinformatics_phase3_freeze.sh"]
        ),
        "PHASE3_AUTHENTICATED_FETCHER": retained_path(
            by_relative["reproduce/bioinformatics/fetch_application_inputs.sh"]
        ),
        "PHASE3_AUTHENTICATED_TEST": retained_path(by_relative[test_relative]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    executed = subprocess.run(
        [sys.executable, "-I", retained_path(by_relative[test_relative])],
        cwd=root,
        env=child_environment,
        pass_fds=inherited_fds,
        check=False,
    )
    verify_dependencies()
    verify_trusted_bash()
    if executed.returncode != 0:
        fail("application builder tests failed", executed.returncode)
except PreexecutionDependencyError as error:
    failure = error
except OSError as error:
    failure = PreexecutionDependencyError(f"operating-system error: {error}")
except UnicodeError as error:
    failure = PreexecutionDependencyError(f"invalid Git path encoding: {error}")
finally:
    if bash_fd is not None:
        os.close(bash_fd)
    for dependency in reversed(dependencies):
        os.close(dependency.descriptor)
        close_parent_bindings(dependency.parents)
    if root_fd is not None:
        os.close(root_fd)

if failure is not None:
    print(
        f"Phase 3 preexecution dependency failed: {failure}",
        file=sys.stderr,
    )
    raise SystemExit(failure.status)
PY_PREEXECUTION_DEPENDENCIES
# END_PHASE3_PREEXECUTION_DEPENDENCIES

python3 -m json.tool "$ROOT/paper/bioinformatics/application_selection.json" >/dev/null
python3 -m json.tool "$ROOT/config/gasal2_longtarget_contracts.json" >/dev/null
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_contracts.schema.json" >/dev/null
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_run_report.schema.json" >/dev/null
(cd "$ROOT/paper/bioinformatics" && sha256sum -c application_manifest.sha256)
git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

forbidden_paths=(
  "$ROOT/reproduce/bioinformatics/run_application.py"
  "$ROOT/reproduce/bioinformatics/application_backend.py"
  "$ROOT/reproduce/bioinformatics/application_raw"
  "$ROOT/reproduce/bioinformatics/application_outputs"
  "$ROOT/paper/bioinformatics/source_data"
  "$ROOT/paper/bioinformatics/application_attempt_results.tsv"
  "$ROOT/paper/bioinformatics/application_results.tsv"
  "$ROOT/paper/bioinformatics/application_summary.json"
  "$ROOT/paper/bioinformatics/application_retry_ledger.tsv"
  "$ROOT/paper/bioinformatics/application_exclusion_ledger.tsv"
  "$ROOT/paper/bioinformatics/phase3_decision.md"
)
for forbidden_path in "${forbidden_paths[@]}"; do
  if [[ -e "$forbidden_path" || -L "$forbidden_path" ]]; then
    echo "forbidden Phase 3 execution artifact exists: $forbidden_path" >&2
    exit 1
  fi
done
shopt -s nullglob
phase3_artifact_roots=("$ROOT"/.paper-artifacts/bioinformatics-phase3-*)
if ((${#phase3_artifact_roots[@]})); then
  echo "forbidden .paper-artifacts/bioinformatics-phase3-* root exists" >&2
  exit 1
fi
shopt -u nullglob

if ! git -C "$ROOT" diff --quiet "$BASELINE" -- \
  paper/bioinformatics \
  ':(exclude)paper/bioinformatics/README.md' \
  ':(exclude)paper/bioinformatics/submission_manifest.tsv' \
  ':(exclude)paper/bioinformatics/application_*' \
  reproduce/bioinformatics \
  ':(exclude)reproduce/bioinformatics/build_application_panel.py' \
  ':(exclude)reproduce/bioinformatics/fetch_application_inputs.sh' \
  ':(exclude)reproduce/bioinformatics/application_inputs/**' \
  scripts \
  ':(exclude)scripts/check_bioinformatics_phase3_freeze.sh' \
  tests \
  ':(exclude)tests/check_build_bioinformatics_application_panel.py' \
  config schemas fasim cuda longtarget.cpp exact_sim.h sim.h stats.h rules.h; then
  echo "Phase 2 or core runtime path changed from bf94dc7" >&2
  exit 1
fi

python3 - "$ROOT" "$BASELINE" <<'PY'
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


root = Path(sys.argv[1])
baseline = sys.argv[2]
FREEZE_ID = "bioinformatics-phase3-application-v1-e8c5441c"
MANIFEST_SHA256 = "e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
SELECTION_SEED = "gasal2-longtarget-phase3-application-v1-20260724"
SELECTION_SHA256 = "de7248b64bd534367204ad436e7911e1047702df23de84f0f41e347e5c7699f5"
SUBMISSION_PREFIX_SHA256 = "db7f0aba2508ce9693a770f2ceea68ff71047c874b71729e35c08b92f21cc7ee"
SUBMISSION_SHA256 = "af95263e2076aa9c4f0443cb4047bb7eb8fe2f22aafb7562652d824c32e772db"
PROTOCOL_SHA256 = "494fdd5d255a02932a9a43187bdc74a6a9100a0fd73a0e260e72421190161c51"
README_SHA256 = "c84a6f24857556c87d40bc569857e3f45ff22fda377444092e2fa162eb4daca8"
QUERY_SELECTION_RULE = (
    "GENCODE v49 lncRNA transcript on chr1-chr22 or chrX; canonical ACGT; "
    "500-2812 nt; exclude development and Phase 2 holdout gene/sequence "
    "identities; one transcript per stable gene by level, basic tag, "
    "descending length, and transcript ID; first 50 by seeded SHA-256"
)
TARGET_SELECTION_RULE = (
    "GENCODE v49 protein-coding transcript on chr21 or chr22; one transcript "
    "per stable gene by MANE Select, Ensembl canonical, APPRIS principal, "
    "basic tag, level, descending length, and transcript ID; forward-genomic "
    "strand-aware TSS window -2000/+500; canonical ACGT"
)
SELECTION_TOP_LEVEL_FIELDS = {
    "annotation_release",
    "assembly",
    "final_freeze_id",
    "manifest_sha256",
    "proposed_freeze_id",
    "query_counts",
    "query_selection_rule",
    "schema_version",
    "selected_queries",
    "selected_targets",
    "selection_seed",
    "source_identities",
    "target_counts",
    "target_selection_rule",
}
EXPECTED_QUERY_COUNTS = {
    "eligible_query_transcript_count": 151975,
    "excluded_development_gene_id_count": 171,
    "excluded_development_gene_name_count": 0,
    "excluded_development_sequence_sha256_count": 0,
    "excluded_holdout_gene_id_count": 113,
    "excluded_holdout_sequence_sha256_count": 0,
    "excluded_missing_gtf_metadata_count": 6132,
    "excluded_non_lncRNA_count": 1038,
    "excluded_non_primary_chromosome_count": 1090,
    "excluded_noncanonical_sequence_count": 0,
    "excluded_query_length_count": 36692,
    "input_query_record_count": 197211,
    "representative_query_count": 27125,
    "selected_query_count": 50,
    "validated_query_candidate_count": 152259,
}
EXPECTED_TARGET_COUNTS = {
    "annotation_target_candidate_count": 668,
    "chr21_annotation_target_candidate_count": 221,
    "chr21_excluded_target_count": 0,
    "chr21_retained_target_count": 221,
    "chr22_annotation_target_candidate_count": 447,
    "chr22_excluded_target_count": 0,
    "chr22_retained_target_count": 447,
    "excluded_empty_promoter_count": 0,
    "excluded_noncanonical_promoter_count": 0,
    "excluded_target_count": 0,
    "retained_target_count": 668,
}
MANIFEST_FIELDS = (
    "record_id", "record_role", "source_release", "assembly",
    "original_gene_id", "original_gene_name", "original_transcript_id",
    "selection_rule", "sequence_length", "chromosome", "strand", "tss",
    "region_start", "region_end", "sequence_sha256", "file_sha256", "path",
    "license_note", "split", "status",
)
SUMMARY_FIELDS = (
    "freeze_id", "manifest_sha256", "query_count", "target_count", "pair_count",
    "query_total_bp", "target_total_bp", "chr21_target_count",
    "chr22_target_count", "min_query_length", "max_query_length",
    "annotation_target_candidate_count", "excluded_target_count",
)
SOURCE_FIELDS = (
    "source_id", "role", "provider", "release", "assembly", "url",
    "upstream_md5", "compressed_size_bytes", "compressed_sha256",
    "decompressed_size_bytes", "decompressed_sha256", "local_source_path",
    "license_or_terms", "redistribution_note", "download_command", "status",
)
HOLDOUT_FIELDS = (
    "workload_id", "query_id", "gene_id", "gene_name", "transcript_id",
    "query_length_nt", "length_stratum", "query_sequence_sha256",
    "query_file_sha256", "query_path", "target_id", "target_gene_id",
    "target_gene_name", "target_chromosome", "target_strand", "target_tss",
    "target_region_start", "target_region_end", "target_length_bp",
    "target_sequence_sha256", "target_file_sha256", "target_path", "assembly",
    "annotation_release", "selection_seed", "requested_contract", "run_modes",
    "repeat_count", "status",
)
SOURCE_AUTHORITIES = (
    {
        "source_id": "gencode_v49_lncrna",
        "role": "lncRNA transcript sequences", "provider": "GENCODE",
        "release": "v49", "assembly": "GRCh38.p14",
        "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
        "upstream_md5": "6d52ea2c72933c864e46a560fe0b5d4c",
        "compressed_size_bytes": "37870043",
        "compressed_sha256": "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4",
        "decompressed_size_bytes": "223740848",
        "decompressed_sha256": "4c632018e0198d76fe76471baa5511a1c07af86bf7bab6ce6747edb8d5add5ae",
        "local_source_path": ".tmp/bioinformatics_application_sources/gencode.v49.lncRNA_transcripts.fa.gz",
        "license_or_terms": "GENCODE project data are open access",
        "redistribution_note": "Selected small transcript FASTAs are retained with source attribution; final redistribution approval remains owner-controlled",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/gencode.v49.lncRNA_transcripts.fa.gz.partial.$$ https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
        "status": "verified",
    },
    {
        "source_id": "gencode_v49_gtf", "role": "gene and transcript annotation",
        "provider": "GENCODE", "release": "v49", "assembly": "GRCh38.p14",
        "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz",
        "upstream_md5": "0ef4a024ea2d35b1b88c12447b0b70b9",
        "compressed_size_bytes": "93374019",
        "compressed_sha256": "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4",
        "decompressed_size_bytes": "3323462848",
        "decompressed_sha256": "ff32fd55c6799b3b94fe10aa17b2b5d4da952fa1de12fe44afadf32e949ec914",
        "local_source_path": ".tmp/bioinformatics_application_sources/gencode.v49.annotation.gtf.gz",
        "license_or_terms": "GENCODE project data are open access",
        "redistribution_note": "Annotation is downloaded for reconstruction and is not redistributed in this repository",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/gencode.v49.annotation.gtf.gz.partial.$$ https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz",
        "status": "verified",
    },
    {
        "source_id": "ucsc_hg38_chr21", "role": "forward genomic reference sequence",
        "provider": "UCSC Genome Browser / Genome Reference Consortium",
        "release": "hg38 2014-01-23", "assembly": "GRCh38",
        "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz",
        "upstream_md5": "184df2bd9b812b6e6b6da16c6021369e",
        "compressed_size_bytes": "12709705",
        "compressed_sha256": "c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b",
        "decompressed_size_bytes": "47644190",
        "decompressed_sha256": "35c71b68436d1a278ecb6a1e875af3ba4020738a028a7feac769a6d62790ae1f",
        "local_source_path": ".tmp/bioinformatics_application_sources/chr21.fa.gz",
        "license_or_terms": "UCSC data-use conditions and Genome Reference Consortium attribution apply",
        "redistribution_note": "Only selected promoter sequences are retained; final redistribution approval remains owner-controlled",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/chr21.fa.gz.partial.$$ https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz",
        "status": "verified",
    },
    {
        "source_id": "ucsc_hg38_chr22", "role": "forward genomic reference sequence",
        "provider": "UCSC Genome Browser / Genome Reference Consortium",
        "release": "hg38 2014-01-23", "assembly": "GRCh38",
        "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz",
        "upstream_md5": "41b47ce1cc21b558409c19b892e1c0d1",
        "compressed_size_bytes": "12255678",
        "compressed_sha256": "05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695",
        "decompressed_size_bytes": "51834845",
        "decompressed_sha256": "ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f",
        "local_source_path": ".tmp/bioinformatics_application_sources/chr22.fa.gz",
        "license_or_terms": "UCSC data-use conditions and Genome Reference Consortium attribution apply",
        "redistribution_note": "Only selected promoter sequences are retained; final redistribution approval remains owner-controlled",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/chr22.fa.gz.partial.$$ https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz",
        "status": "verified",
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: {message}")


class DuplicateJSONKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(key)
        result[key] = value
    return result


def stable_id(value: str) -> str:
    return value.split(".", 1)[0]


directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
file_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def metadata_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def repository_parts(path: Path) -> tuple[str, ...]:
    try:
        relative = path.relative_to(root)
    except ValueError:
        require(False, f"repository path escaped root: {path}")
    parts = relative.parts
    require(parts and all(part not in {"", ".", ".."} for part in parts), f"unsafe repository path: {path}")
    return parts


def no_follow_failure(parts: tuple[str, ...]) -> None:
    require(False, "no-follow repository path failed: " + "/".join(parts))


def revalidate_repository_root() -> None:
    try:
        named = os.lstat(root)
        retained = os.fstat(repository_root_fd)
    except OSError:
        require(False, "repository root identity changed")
    require(
        stat.S_ISDIR(named.st_mode)
        and stat.S_ISDIR(retained.st_mode)
        and metadata_signature(named) == repository_root_signature
        and metadata_signature(retained) == repository_root_signature,
        "repository root identity changed",
    )


def close_parent_chain(
    chain: list[tuple[int, str, int, tuple[int, int, int, int, int, int], tuple[str, ...]]],
) -> None:
    for _parent_fd, _name, descriptor, _signature, _parts in reversed(chain):
        os.close(descriptor)


def revalidate_parent_chain(
    chain: list[tuple[int, str, int, tuple[int, int, int, int, int, int], tuple[str, ...]]],
) -> None:
    for parent_fd, name, descriptor, expected, parts in reversed(chain):
        try:
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            retained = os.fstat(descriptor)
        except OSError:
            no_follow_failure(parts)
        if (
            not stat.S_ISDIR(named.st_mode)
            or not stat.S_ISDIR(retained.st_mode)
            or metadata_signature(named) != expected
            or metadata_signature(retained) != expected
        ):
            no_follow_failure(parts)
    revalidate_repository_root()


def open_repository_parent(
    path: Path,
) -> tuple[
    int,
    str,
    list[tuple[int, str, int, tuple[int, int, int, int, int, int], tuple[str, ...]]],
]:
    parts = repository_parts(path)
    revalidate_repository_root()
    current_fd = repository_root_fd
    chain: list[
        tuple[int, str, int, tuple[int, int, int, int, int, int], tuple[str, ...]]
    ] = []
    try:
        for index, name in enumerate(parts[:-1]):
            traversed = parts[: index + 1]
            try:
                named = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            except OSError:
                no_follow_failure(traversed)
            if not stat.S_ISDIR(named.st_mode):
                no_follow_failure(traversed)
            try:
                descriptor = os.open(name, directory_flags, dir_fd=current_fd)
            except OSError:
                no_follow_failure(traversed)
            retained = os.fstat(descriptor)
            expected = metadata_signature(named)
            if (
                not stat.S_ISDIR(retained.st_mode)
                or metadata_signature(retained) != expected
            ):
                os.close(descriptor)
                no_follow_failure(traversed)
            chain.append((current_fd, name, descriptor, expected, traversed))
            current_fd = descriptor
        return current_fd, parts[-1], chain
    except BaseException:
        close_parent_chain(chain)
        raise


def read_repository_file(path: Path, label: str) -> tuple[bytes, os.stat_result]:
    parent_fd, name, chain = open_repository_parent(path)
    descriptor: int | None = None
    try:
        try:
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            require(False, f"missing {label}: {path}")
        except OSError:
            no_follow_failure(repository_parts(path))
        require(stat.S_ISREG(named.st_mode), f"{label} is not a regular file: {path}")
        require(named.st_nlink == 1, f"{label} has a hardlink alias: {path}")
        try:
            descriptor = os.open(name, file_flags, dir_fd=parent_fd)
        except OSError:
            no_follow_failure(repository_parts(path))
        opened = os.fstat(descriptor)
        expected = metadata_signature(named)
        require(
            stat.S_ISREG(opened.st_mode)
            and opened.st_nlink == 1
            and metadata_signature(opened) == expected,
            f"{label} identity changed while opening: {path}",
        )
        blocks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            blocks.append(block)
        after = os.fstat(descriptor)
        require(
            metadata_signature(after) == expected,
            f"{label} identity changed while reading: {path}",
        )
        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError:
            require(False, f"{label} bound name changed after reading: {path}")
        require(
            metadata_signature(current) == expected,
            f"{label} bound name changed after reading: {path}",
        )
        revalidate_parent_chain(chain)
        return b"".join(blocks), opened
    finally:
        if descriptor is not None:
            os.close(descriptor)
        close_parent_chain(chain)


@contextmanager
def retained_repository_directory(path: Path, label: str):
    parent_fd, name, chain = open_repository_parent(path)
    descriptor: int | None = None
    try:
        try:
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError:
            no_follow_failure(repository_parts(path))
        if not stat.S_ISDIR(named.st_mode):
            no_follow_failure(repository_parts(path))
        try:
            descriptor = os.open(name, directory_flags, dir_fd=parent_fd)
        except OSError:
            no_follow_failure(repository_parts(path))
        opened = os.fstat(descriptor)
        expected = metadata_signature(named)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or metadata_signature(opened) != expected
        ):
            no_follow_failure(repository_parts(path))
        yield descriptor, opened
        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            retained = os.fstat(descriptor)
        except OSError:
            no_follow_failure(repository_parts(path))
        if (
            metadata_signature(current) != expected
            or metadata_signature(retained) != expected
        ):
            no_follow_failure(repository_parts(path))
        revalidate_parent_chain(chain)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        close_parent_chain(chain)


def read_bytes(path: Path, label: str) -> bytes:
    data, _metadata = read_repository_file(path, label)
    return data


def read_tsv(path: Path, fields: tuple[str, ...], label: str) -> list[dict[str, str]]:
    data = read_bytes(path, label)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: invalid UTF-8 in {label}: {error}")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    require(tuple(reader.fieldnames or ()) == fields, f"{label} schema drift")
    rows = list(reader)
    require(
        all(tuple(row) == fields and all(value is not None for value in row.values()) for row in rows),
        f"{label} contains a malformed row",
    )
    return rows


try:
    repository_root_named = os.lstat(root)
    if not stat.S_ISDIR(repository_root_named.st_mode):
        require(False, "repository root is unsafe")
    repository_root_fd = os.open(root, directory_flags)
except OSError:
    require(False, "repository root is unsafe")
repository_root_opened = os.fstat(repository_root_fd)
repository_root_signature = metadata_signature(repository_root_named)
require(
    stat.S_ISDIR(repository_root_opened.st_mode)
    and metadata_signature(repository_root_opened) == repository_root_signature,
    "repository root identity changed while opening",
)


manifest_path = root / "paper/bioinformatics/application_manifest.tsv"
manifest_bytes = read_bytes(manifest_path, "application manifest")
require(hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA256, "manifest checksum drift")
checksum = read_bytes(
    root / "paper/bioinformatics/application_manifest.sha256",
    "manifest checksum receipt",
)
require(
    checksum == f"{MANIFEST_SHA256}  application_manifest.tsv\n".encode("ascii"),
    "manifest checksum receipt drift",
)
rows = read_tsv(manifest_path, MANIFEST_FIELDS, "application manifest")
require(len(rows) == 718, f"expected 718 manifest records, found {len(rows)}")
queries = [row for row in rows if row["record_role"] == "query"]
targets = [row for row in rows if row["record_role"] == "target"]
require(len(queries) == 50, f"expected 50 queries, found {len(queries)}")
require(len(targets) == 668 and len(targets) >= 300, f"invalid target count: {len(targets)}")
require(queries + targets == rows, "manifest must order queries before targets")
require(
    [row["record_id"] for row in queries] == [f"aq{index:03d}" for index in range(1, 51)],
    "query IDs or order drifted",
)
require(
    [row["record_id"] for row in targets] == [f"at{index:04d}" for index in range(1, 669)],
    "target IDs or order drifted",
)
require(len({row["record_id"] for row in rows}) == 718, "record IDs are not unique")
require(len({row["path"] for row in rows}) == 718, "record paths are not unique")
require(
    len({stable_id(row["original_gene_id"]) for row in queries}) == 50
    and len({stable_id(row["original_gene_id"]) for row in targets}) == 668,
    "stable gene IDs are not unique within record role",
)
require(
    len({row["original_transcript_id"] for row in queries}) == 50
    and len({row["original_transcript_id"] for row in targets}) == 668,
    "transcript IDs are not unique within record role",
)
require(len({row["sequence_sha256"] for row in queries}) == 50, "query sequence digests are not unique")
require(
    all(
        row["source_release"] == "GENCODE v49"
        and row["assembly"] == "GRCh38"
        and row["split"] == "application"
        and row["status"] == "preregistered_not_run"
        and row["selection_rule"].strip()
        and row["license_note"].strip()
        for row in rows
    ),
    "common manifest metadata or preregistered status drifted",
)

input_root = root / "reproduce/bioinformatics/application_inputs"
expected_paths: set[str] = set()
query_total = 0
target_total = 0
chromosome_counts: Counter[str] = Counter()
target_digest_groups: dict[str, list[dict[str, str]]] = {}
seen_file_inodes: set[tuple[int, int]] = set()
fasta_metadata_by_path: dict[str, os.stat_result] = {}
for row in rows:
    role = row["record_role"]
    record_id = row["record_id"]
    require(role in {"query", "target"}, f"invalid record role: {record_id}")
    subdirectory = "queries" if role == "query" else "targets"
    expected_path = f"reproduce/bioinformatics/application_inputs/{subdirectory}/{record_id}.fa"
    require(row["path"] == expected_path, f"noncanonical FASTA path: {record_id}")
    relative = PurePosixPath(row["path"])
    require(
        not relative.is_absolute() and ".." not in relative.parts and "." not in relative.parts,
        f"unsafe FASTA path: {record_id}",
    )
    expected_paths.add(row["path"])
    path = root / relative
    fasta, metadata = read_repository_file(path, f"FASTA {record_id}")
    inode = (metadata.st_dev, metadata.st_ino)
    require(inode not in seen_file_inodes, f"aliased FASTA inode: {record_id}")
    seen_file_inodes.add(inode)
    fasta_metadata_by_path[row["path"]] = metadata
    require(hashlib.sha256(fasta).hexdigest() == row["file_sha256"], f"FASTA hash drift: {record_id}")
    try:
        lines = fasta.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError as error:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: non-ASCII FASTA {record_id}: {error}")
    require(lines and lines[0].startswith(">") and len(lines[0]) > 1, f"invalid FASTA header: {record_id}")
    require(
        all(line and line == line.strip() and not line.startswith(">") for line in lines[1:]),
        f"FASTA is not exactly one record: {record_id}",
    )
    sequence = "".join(lines[1:])
    require(sequence and set(sequence) <= set("ACGT"), f"noncanonical FASTA: {record_id}")
    require(row["sequence_length"].isdigit() and row["sequence_length"] != "0", f"invalid length: {record_id}")
    length = int(row["sequence_length"])
    require(len(sequence) == length, f"FASTA length drift: {record_id}")
    require(
        hashlib.sha256(sequence.encode("ascii")).hexdigest() == row["sequence_sha256"],
        f"FASTA sequence hash drift: {record_id}",
    )
    if role == "query":
        require(500 <= length <= 2812, f"query length outside frozen range: {record_id}")
        require(
            all(row[field] == "NA" for field in ("chromosome", "strand", "tss", "region_start", "region_end")),
            f"query coordinate fields drifted: {record_id}",
        )
        expected_header = (
            f">{record_id}|{row['original_transcript_id']}|{row['original_gene_id']}|"
            f"{row['original_gene_name']}|GENCODE v49|GRCh38|application_query"
        )
        query_total += length
    else:
        require(row["chromosome"] in {"chr21", "chr22"}, f"target chromosome drift: {record_id}")
        require(row["strand"] in {"+", "-"}, f"target strand drift: {record_id}")
        require(
            all(row[field].isdigit() and row[field] != "0" for field in ("tss", "region_start", "region_end")),
            f"invalid target geometry: {record_id}",
        )
        tss, start, end = (int(row[field]) for field in ("tss", "region_start", "region_end"))
        require(end - start + 1 == length, f"target interval length drift: {record_id}")
        expected_geometry = (
            (max(1, tss - 2000), tss + 500)
            if row["strand"] == "+"
            else (max(1, tss - 500), tss + 2000)
        )
        require((start, end) == expected_geometry, f"target promoter geometry drift: {record_id}")
        expected_header = (
            f">{record_id}|{row['original_transcript_id']}|{row['original_gene_id']}|"
            f"{row['original_gene_name']}|GRCh38|{row['chromosome']}:{start}-{end}|"
            "promoter_forward_genomic"
        )
        target_total += length
        chromosome_counts[row["chromosome"]] += 1
        target_digest_groups.setdefault(row["sequence_sha256"], []).append(row)
    require(lines[0] == expected_header, f"FASTA header drift: {record_id}")

actual_paths: set[str] = set()
expected_names_by_role = {
    role: {
        PurePosixPath(path).name
        for path in expected_paths
        if PurePosixPath(path).parent.name == role
    }
    for role in ("queries", "targets")
}
with retained_repository_directory(input_root, "application input root") as (
    input_fd,
    _input_metadata,
):
    input_names = set(os.listdir(input_fd))
    require(
        input_names == {"queries", "targets"},
        "application input tree has unexpected root entries",
    )
    input_children: dict[str, os.stat_result] = {}
    for role in sorted(input_names):
        metadata = os.stat(role, dir_fd=input_fd, follow_symlinks=False)
        require(
            stat.S_ISDIR(metadata.st_mode),
            f"application input role is not a directory: {role}",
        )
        input_children[role] = metadata

    for role in ("queries", "targets"):
        role_path = input_root / role
        with retained_repository_directory(
            role_path,
            f"application {role} directory",
        ) as (role_fd, role_metadata):
            require(
                metadata_signature(role_metadata)
                == metadata_signature(input_children[role]),
                f"application input role identity changed: {role}",
            )
            names = set(os.listdir(role_fd))
            require(
                names == expected_names_by_role[role],
                f"application {role} directory differs from manifest",
            )
            children: dict[str, os.stat_result] = {}
            for name in sorted(names):
                metadata = os.stat(name, dir_fd=role_fd, follow_symlinks=False)
                relative = f"reproduce/bioinformatics/application_inputs/{role}/{name}"
                require(
                    stat.S_ISREG(metadata.st_mode),
                    f"application input tree contains a symlink or special: {relative}",
                )
                require(
                    metadata.st_nlink == 1,
                    f"application FASTA has a hardlink alias: {relative}",
                )
                require(
                    metadata_signature(metadata)
                    == metadata_signature(fasta_metadata_by_path[relative]),
                    f"application FASTA identity changed after reading: {relative}",
                )
                children[name] = metadata
                actual_paths.add(relative)
            require(
                set(os.listdir(role_fd)) == names,
                f"application {role} directory changed during validation",
            )
            for name, metadata in children.items():
                current = os.stat(name, dir_fd=role_fd, follow_symlinks=False)
                require(
                    metadata_signature(current) == metadata_signature(metadata),
                    f"application FASTA identity changed during validation: {role}/{name}",
                )

    require(
        set(os.listdir(input_fd)) == input_names,
        "application input root changed during validation",
    )
    for role, metadata in input_children.items():
        current = os.stat(role, dir_fd=input_fd, follow_symlinks=False)
        require(
            metadata_signature(current) == metadata_signature(metadata),
            f"application input role identity changed during validation: {role}",
        )
require(actual_paths == expected_paths and len(actual_paths) == 718, "application FASTA tree differs from manifest")

duplicate_target_groups = [group for group in target_digest_groups.values() if len(group) > 1]
require(len(duplicate_target_groups) == 2, "target duplicate digest group count drifted")
for group in duplicate_target_groups:
    require(len(group) == 2, "target digest is shared by more than one permitted pair")
    coordinates = {
        (row["chromosome"], row["strand"], row["tss"], row["region_start"], row["region_end"])
        for row in group
    }
    require(len(coordinates) == 1, "duplicate target digest does not share exact coordinates")

pair_count = len(queries) * len(targets)
require(pair_count == 33400 and pair_count >= 15000, f"pair count drifted: {pair_count}")
require(query_total == 56381, f"query total drifted: {query_total}")
require(target_total == 1670668, f"target total drifted: {target_total}")
require(chromosome_counts == {"chr21": 221, "chr22": 447}, "target chromosome counts drifted")

summary = read_tsv(
    root / "paper/bioinformatics/application_input_summary.tsv",
    SUMMARY_FIELDS,
    "application input summary",
)
expected_summary = {
    "freeze_id": FREEZE_ID, "manifest_sha256": MANIFEST_SHA256,
    "query_count": "50", "target_count": "668", "pair_count": "33400",
    "query_total_bp": "56381", "target_total_bp": "1670668",
    "chr21_target_count": "221", "chr22_target_count": "447",
    "min_query_length": "513", "max_query_length": "2709",
    "annotation_target_candidate_count": "668", "excluded_target_count": "0",
}
require(summary == [expected_summary], "application input summary drifted")
require(FREEZE_ID == f"bioinformatics-phase3-application-v1-{MANIFEST_SHA256[:8]}", "freeze derivation drifted")

development = read_tsv(
    root / "paper/bioinformatics/development_query_exclusions.tsv",
    ("exclusion_type", "value", "reason"),
    "development exclusion ledger",
)
require(
    len({(row["exclusion_type"], row["value"]) for row in development}) == len(development),
    "development exclusions contain duplicates",
)
require(
    all(
        row["exclusion_type"] in {"gene_id", "gene_name", "sequence_sha256"}
        and row["value"] and row["reason"].strip()
        for row in development
    ),
    "development exclusion row is invalid",
)
excluded_ids = {row["value"] for row in development if row["exclusion_type"] == "gene_id"}
excluded_names = {row["value"] for row in development if row["exclusion_type"] == "gene_name"}
excluded_digests = {row["value"] for row in development if row["exclusion_type"] == "sequence_sha256"}
require(
    all(
        stable_id(row["original_gene_id"]) not in excluded_ids
        and row["original_gene_name"] not in excluded_names
        and row["sequence_sha256"] not in excluded_digests
        for row in queries
    ),
    "application query overlaps development identities",
)
holdout = read_tsv(
    root / "paper/bioinformatics/holdout_manifest.tsv",
    HOLDOUT_FIELDS,
    "Phase 2 holdout manifest",
)
require(len(holdout) == 24, "Phase 2 holdout row count drifted")
holdout_ids = {stable_id(row["gene_id"]) for row in holdout}
holdout_digests = {row["query_sequence_sha256"] for row in holdout}
require(
    all(
        stable_id(row["original_gene_id"]) not in holdout_ids
        and row["sequence_sha256"] not in holdout_digests
        for row in queries
    ),
    "application query overlaps Phase 2 holdout identities",
)

selection_bytes = read_bytes(
    root / "paper/bioinformatics/application_selection.json",
    "application selection receipt",
)
try:
    selection = json.loads(
        selection_bytes.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_duplicate_json_keys,
    )
except DuplicateJSONKeyError as error:
    raise SystemExit(
        "Bioinformatics Phase 3 freeze check failed: application selection "
        f"contains duplicate JSON key: {error.key}"
    ) from error
except (json.JSONDecodeError, UnicodeDecodeError) as error:
    raise SystemExit(
        f"Bioinformatics Phase 3 freeze check failed: invalid application selection JSON: {error}"
    ) from error
require(isinstance(selection, dict), "application selection receipt is not an object")
require(
    set(selection) == SELECTION_TOP_LEVEL_FIELDS,
    "application selection top-level schema drifted",
)
require(selection.get("schema_version") == 1, "selection schema version drifted")
require(selection.get("selection_seed") == SELECTION_SEED, "selection seed drifted")
require(selection.get("assembly") == "GRCh38", "selection assembly drifted")
require(selection.get("annotation_release") == "GENCODE v49", "selection annotation drifted")
require(selection.get("proposed_freeze_id") == FREEZE_ID, "proposed freeze ID drifted")
require(selection.get("final_freeze_id") == FREEZE_ID, "final freeze ID drifted")
require(selection.get("manifest_sha256") == MANIFEST_SHA256, "selection manifest digest drifted")
require(
    selection.get("query_selection_rule") == QUERY_SELECTION_RULE,
    "selection query rule drifted",
)
require(
    selection.get("target_selection_rule") == TARGET_SELECTION_RULE,
    "selection target rule drifted",
)
selected_queries = selection.get("selected_queries")
selected_targets = selection.get("selected_targets")
require(isinstance(selected_queries, list) and len(selected_queries) == 50, "selected query count drifted")
require(isinstance(selected_targets, list) and len(selected_targets) == 668, "selected target count drifted")
for selected, row in zip(selected_queries, queries, strict=True):
    expected_hash = hashlib.sha256(
        "|".join((
            SELECTION_SEED, stable_id(row["original_gene_id"]),
            stable_id(row["original_transcript_id"]), row["sequence_sha256"],
        )).encode("ascii")
    ).hexdigest()
    require(
        selected == {
            "query_id": row["record_id"], "original_gene_id": row["original_gene_id"],
            "original_gene_name": row["original_gene_name"],
            "original_transcript_id": row["original_transcript_id"],
            "sequence_length": int(row["sequence_length"]),
            "sequence_sha256": row["sequence_sha256"], "selection_hash": expected_hash,
        },
        f"selected query drifted: {row['record_id']}",
    )
for selected, row in zip(selected_targets, targets, strict=True):
    require(
        selected == {
            "target_id": row["record_id"], "original_gene_id": row["original_gene_id"],
            "original_gene_name": row["original_gene_name"],
            "original_transcript_id": row["original_transcript_id"],
            "sequence_length": int(row["sequence_length"]),
            "sequence_sha256": row["sequence_sha256"], "chromosome": row["chromosome"],
            "strand": row["strand"], "tss": int(row["tss"]),
            "region_start": int(row["region_start"]), "region_end": int(row["region_end"]),
        },
        f"selected target drifted: {row['record_id']}",
    )

query_counts = selection.get("query_counts")
target_counts = selection.get("target_counts")
require(isinstance(query_counts, dict) and isinstance(target_counts, dict), "selection counts are missing")
require(query_counts == EXPECTED_QUERY_COUNTS, "selection query counts drifted")
require(target_counts == EXPECTED_TARGET_COUNTS, "selection target counts drifted")
require(
    all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in query_counts.values()),
    "query exclusion count is invalid",
)
require(
    all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in target_counts.values()),
    "target exclusion count is invalid",
)
require(
    query_counts.get("selected_query_count") == 50
    and query_counts.get("input_query_record_count")
    == query_counts.get("validated_query_candidate_count")
    + query_counts.get("excluded_missing_gtf_metadata_count")
    + query_counts.get("excluded_non_lncRNA_count")
    + query_counts.get("excluded_non_primary_chromosome_count")
    + query_counts.get("excluded_noncanonical_sequence_count")
    + query_counts.get("excluded_query_length_count")
    and query_counts.get("eligible_query_transcript_count")
    == query_counts.get("validated_query_candidate_count")
    - query_counts.get("excluded_development_gene_id_count")
    - query_counts.get("excluded_development_gene_name_count")
    - query_counts.get("excluded_development_sequence_sha256_count")
    - query_counts.get("excluded_holdout_gene_id_count")
    - query_counts.get("excluded_holdout_sequence_sha256_count")
    and query_counts.get("selected_query_count")
    <= query_counts.get("representative_query_count")
    <= query_counts.get("eligible_query_transcript_count"),
    "selection query exclusion arithmetic drifted",
)
require(
    target_counts.get("annotation_target_candidate_count") == 668
    and target_counts.get("retained_target_count") == 668
    and target_counts.get("excluded_target_count") == 0
    and target_counts.get("chr21_annotation_target_candidate_count") == 221
    and target_counts.get("chr22_annotation_target_candidate_count") == 447
    and target_counts.get("annotation_target_candidate_count")
    == target_counts.get("retained_target_count") + target_counts.get("excluded_target_count")
    and target_counts.get("excluded_target_count")
    == target_counts.get("excluded_empty_promoter_count")
    + target_counts.get("excluded_noncanonical_promoter_count")
    and target_counts.get("chr21_annotation_target_candidate_count")
    == target_counts.get("chr21_retained_target_count")
    + target_counts.get("chr21_excluded_target_count")
    and target_counts.get("chr22_annotation_target_candidate_count")
    == target_counts.get("chr22_retained_target_count")
    + target_counts.get("chr22_excluded_target_count")
    and target_counts.get("retained_target_count")
    == target_counts.get("chr21_retained_target_count")
    + target_counts.get("chr22_retained_target_count")
    and target_counts.get("excluded_target_count")
    == target_counts.get("chr21_excluded_target_count")
    + target_counts.get("chr22_excluded_target_count"),
    "selection target exclusion arithmetic drifted",
)

source_rows = read_tsv(
    root / "paper/bioinformatics/application_sources.tsv",
    SOURCE_FIELDS,
    "application source ledger",
)
require(len(source_rows) == 4, f"expected four source rows, found {len(source_rows)}")
require(
    all(tuple(authority) == SOURCE_FIELDS for authority in SOURCE_AUTHORITIES),
    "source authority constant schema drifted",
)
for row, authority in zip(source_rows, SOURCE_AUTHORITIES, strict=True):
    for field in SOURCE_FIELDS:
        require(
            row[field] == authority[field],
            f"source authority drifted: {authority['source_id']} {field}",
        )

authorities = {row["source_id"]: row for row in SOURCE_AUTHORITIES}
development_identity_bytes, development_identity_metadata = read_repository_file(
    root / "paper/bioinformatics/development_query_exclusions.tsv",
    "development exclusions",
)
holdout_identity_bytes, holdout_identity_metadata = read_repository_file(
    root / "paper/bioinformatics/holdout_manifest.tsv",
    "Phase 2 holdout manifest",
)
expected_source_identities = {
    "lncrna_fasta": {
        "sha256": authorities["gencode_v49_lncrna"]["compressed_sha256"],
        "size_bytes": int(authorities["gencode_v49_lncrna"]["compressed_size_bytes"]),
    },
    "annotation_gtf": {
        "sha256": authorities["gencode_v49_gtf"]["compressed_sha256"],
        "size_bytes": int(authorities["gencode_v49_gtf"]["compressed_size_bytes"]),
    },
    "chr21_fasta": {
        "sha256": authorities["ucsc_hg38_chr21"]["compressed_sha256"],
        "size_bytes": int(authorities["ucsc_hg38_chr21"]["compressed_size_bytes"]),
    },
    "chr22_fasta": {
        "sha256": authorities["ucsc_hg38_chr22"]["compressed_sha256"],
        "size_bytes": int(authorities["ucsc_hg38_chr22"]["compressed_size_bytes"]),
    },
    "development_exclusions": {
        "sha256": hashlib.sha256(development_identity_bytes).hexdigest(),
        "size_bytes": development_identity_metadata.st_size,
    },
    "phase2_holdout_manifest": {
        "sha256": hashlib.sha256(holdout_identity_bytes).hexdigest(),
        "size_bytes": holdout_identity_metadata.st_size,
    },
}
require(selection.get("source_identities") == expected_source_identities, "selection source identities drifted")
require(
    hashlib.sha256(selection_bytes).hexdigest() == SELECTION_SHA256,
    "application selection checksum drift",
)

claim_fields = (
    "claim_id", "allowed_wording", "prohibited_wording", "required_evidence",
    "authoritative_source", "promotion_gate", "phase", "status",
)
claims = read_tsv(root / "paper/bioinformatics/claim_evidence.tsv", claim_fields, "claim ledger")
b3 = [row for row in claims if row["claim_id"] == "B3"]
require(len(b3) == 1 and b3[0]["phase"] == "3" and b3[0]["status"] == "pending", "claim B3 is not pending")

submission_fields = (
    "artifact_id", "path", "phase", "artifact_class", "authority",
    "freeze_or_epoch", "required", "status",
)
submission_bytes = read_bytes(
    root / "paper/bioinformatics/submission_manifest.tsv",
    "submission manifest",
)
try:
    submission_text = submission_bytes.decode("utf-8", errors="strict")
except UnicodeDecodeError as error:
    raise SystemExit(
        f"Bioinformatics Phase 3 freeze check failed: invalid UTF-8 in submission manifest: {error}"
    ) from error
submission_reader = csv.DictReader(
    io.StringIO(submission_text, newline=""),
    delimiter="\t",
)
require(
    tuple(submission_reader.fieldnames or ()) == submission_fields,
    "submission manifest schema drift",
)
submission = list(submission_reader)
require(
    all(
        tuple(row) == submission_fields
        and all(value is not None for value in row.values())
        for row in submission
    ),
    "submission manifest contains a malformed row",
)
expected_submission = (
    ("S0301", "paper/bioinformatics/application_selection.json", "application_selection", "build_application_panel.py"),
    ("S0302", "paper/bioinformatics/application_manifest.tsv", "application_manifest", "application_protocol.md"),
    ("S0303", "paper/bioinformatics/application_manifest.sha256", "application_manifest_checksum", "application_manifest.tsv"),
    ("S0304", "paper/bioinformatics/application_sources.tsv", "application_source_ledger", "provider_checksums_and_local_sha256"),
    ("S0305", "paper/bioinformatics/application_protocol.md", "application_protocol", "goal-bioinformatics.md"),
    ("S0306", "paper/bioinformatics/application_input_summary.tsv", "application_input_summary", "application_manifest.tsv"),
    ("S0307", "reproduce/bioinformatics/build_application_panel.py", "application_builder", "application_protocol.md"),
    ("S0308", "reproduce/bioinformatics/fetch_application_inputs.sh", "application_fetcher", "application_sources.tsv"),
    ("S0309", "tests/check_build_bioinformatics_application_panel.py", "application_builder_tests", "goal-bioinformatics.md"),
    ("S0310", "scripts/check_bioinformatics_phase3_freeze.sh", "preexecution_phase_gate", "goal-bioinformatics.md"),
)
submission_lines = submission_bytes.splitlines(keepends=True)
require(len(submission_lines) >= 50, "submission manifest baseline prefix is truncated")
require(
    hashlib.sha256(b"".join(submission_lines[:50])).hexdigest()
    == SUBMISSION_PREFIX_SHA256,
    "submission manifest baseline prefix checksum drift",
)


def is_application_submission_row(row: dict[str, str]) -> bool:
    path = row["path"]
    artifact_class = row["artifact_class"]
    return (
        path.startswith("paper/bioinformatics/application_")
        or path.startswith("paper/bioinformatics/source_data")
        or path.startswith("reproduce/bioinformatics/application_")
        or artifact_class.startswith("application_")
        or artifact_class in {"application_results", "source_data"}
    )


for index, row in enumerate(submission):
    if is_application_submission_row(row) and not 49 <= index < 59:
        require(
            False,
            "submission manifest contains application row outside Phase 3 suffix: "
            + row["artifact_id"],
        )

require(
    len(submission_lines) == 60
    and all(line.endswith(b"\n") for line in submission_lines),
    "submission manifest physical line count drifted",
)
require(len(submission) == 59, "submission manifest row count drifted")
phase3_rows = submission[49:]
require(len(phase3_rows) == 10, "submission Phase 3 suffix row count drifted")
for row, expected in zip(phase3_rows, expected_submission, strict=True):
    artifact_id, path, artifact_class, authority = expected
    require(
        row == {
            "artifact_id": artifact_id, "path": path, "phase": "3",
            "artifact_class": artifact_class, "authority": authority,
            "freeze_or_epoch": FREEZE_ID, "required": "1", "status": "pass",
        },
        f"submission row drifted: {artifact_id}",
    )
require(
    hashlib.sha256(submission_bytes).hexdigest() == SUBMISSION_SHA256,
    "submission manifest checksum drift",
)

readme_bytes = read_bytes(
    root / "paper/bioinformatics/README.md",
    "Bioinformatics README",
)
readme = readme_bytes.decode("utf-8")
marker = "## Phase 3 input freeze receipt\n"
require(marker in readme, "README Phase 3 receipt missing")
receipt = readme.split(marker, 1)[1].split("\n## ", 1)[0]
for required_text in (
    f"freeze_id = {FREEZE_ID}", f"manifest_sha256 = {MANIFEST_SHA256}",
    "query_count = 50", "target_count = 668", "pair_count = 33400",
    "query_total_nt = 56381", "target_total_bp = 1670668",
    "chr21_target_count = 221", "chr22_target_count = 447",
    "fasta_file_count = 718", "record_status = preregistered_not_run",
    "application_execution_started = 0", "Phase 3 and claim B3 remain pending.",
):
    require(required_text in receipt, f"README receipt missing: {required_text}")
require(not re.search(r"\b(?:completed|decision|results?|speedup|no_go)\b", receipt.lower()), "README contains result wording")
require(
    hashlib.sha256(readme_bytes).hexdigest() == README_SHA256,
    "README checksum drift",
)
protocol_bytes = read_bytes(
    root / "paper/bioinformatics/application_protocol.md",
    "application protocol",
)
protocol = protocol_bytes.decode("utf-8", errors="strict")
for required_text in (
    FREEZE_ID,
    MANIFEST_SHA256,
    "33,400",
    "preregistered_not_run",
    "Execution remains planned, not run.",
    "Candidate-only B speedup\ncannot establish, rescue, or be reported as a B3 widening claim.",
    "Phase 3 and B3 remain\npending",
):
    require(required_text in protocol, f"protocol receipt missing: {required_text}")
require(
    hashlib.sha256(protocol_bytes).hexdigest() == PROTOCOL_SHA256,
    "application protocol checksum drift",
)

allowed_paper_application = {
    "application_input_summary.tsv", "application_manifest.sha256",
    "application_manifest.tsv", "application_protocol.md",
    "application_selection.json", "application_sources.tsv",
}
paper_directory = root / "paper/bioinformatics"
with retained_repository_directory(
    paper_directory,
    "Bioinformatics paper directory",
) as (paper_fd, _paper_metadata):
    paper_names = set(os.listdir(paper_fd))
    paper_children = {
        name: os.stat(name, dir_fd=paper_fd, follow_symlinks=False)
        for name in paper_names
    }
    for name in paper_names:
        if name.startswith("application_"):
            require(
                name in allowed_paper_application,
                f"unexpected Phase 3 paper artifact: {name}",
            )
    require(
        set(os.listdir(paper_fd)) == paper_names,
        "Bioinformatics paper directory changed during validation",
    )
    for name, metadata in paper_children.items():
        current = os.stat(name, dir_fd=paper_fd, follow_symlinks=False)
        require(
            metadata_signature(current) == metadata_signature(metadata),
            f"Bioinformatics paper entry changed during validation: {name}",
        )

revalidate_repository_root()
os.close(repository_root_fd)

allowed_exact = {
    "Makefile",
    "docs/superpowers/plans/2026-07-24-bioinformatics-phase3-application-freeze.md",
    "docs/superpowers/specs/2026-07-24-bioinformatics-phase3-application-design.md",
    "paper/bioinformatics/README.md",
    "paper/bioinformatics/application_input_summary.tsv",
    "paper/bioinformatics/application_manifest.sha256",
    "paper/bioinformatics/application_manifest.tsv",
    "paper/bioinformatics/application_protocol.md",
    "paper/bioinformatics/application_selection.json",
    "paper/bioinformatics/application_sources.tsv",
    "paper/bioinformatics/submission_manifest.tsv",
    "reproduce/bioinformatics/build_application_panel.py",
    "reproduce/bioinformatics/fetch_application_inputs.sh",
    "scripts/check_bioinformatics_phase3_freeze.sh",
    "tests/check_build_bioinformatics_application_panel.py",
}


def allowed_checkpoint_path(path: str) -> bool:
    return path in allowed_exact or path.startswith("reproduce/bioinformatics/application_inputs/")


changed = subprocess.run(
    ["git", "-C", str(root), "diff", "--name-only", "-z", baseline, "--"],
    check=True,
    stdout=subprocess.PIPE,
).stdout
changed_paths = [value.decode("utf-8", errors="strict") for value in changed.split(b"\0") if value]
require(
    all(allowed_checkpoint_path(path) for path in changed_paths),
    "Phase 2 or core runtime path changed from bf94dc7: "
    + ", ".join(path for path in changed_paths if not allowed_checkpoint_path(path)),
)
status = subprocess.run(
    ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
    check=True,
    stdout=subprocess.PIPE,
).stdout
parts = status.split(b"\0")
status_paths: list[str] = []
index = 0
while index < len(parts) and parts[index]:
    entry = parts[index].decode("utf-8", errors="strict")
    require(len(entry) >= 4 and entry[2] == " ", f"cannot parse git status entry: {entry!r}")
    code = entry[:2]
    status_paths.append(entry[3:])
    index += 1
    if "R" in code or "C" in code:
        require(index < len(parts) and parts[index], "truncated rename in git status")
        status_paths.append(parts[index].decode("utf-8", errors="strict"))
        index += 1
require(
    all(allowed_checkpoint_path(path) for path in status_paths),
    "working tree path outside Phase 3 checkpoint: "
    + ", ".join(path for path in status_paths if not allowed_checkpoint_path(path)),
)
PY

write_application_snapshot() {
  local destination="$1"
  python3 - \
    "$ROOT" "$destination" "$WORK" "$WORK_DEVICE" "$WORK_INODE" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath


root = Path(sys.argv[1])
destination = Path(sys.argv[2])
run_directory = Path(sys.argv[3])
expected_run_identity = (int(sys.argv[4]), int(sys.argv[5]))
metadata_paths = (
    "Makefile",
    "goal-bioinformatics.md",
    "docs/superpowers/plans/2026-07-24-bioinformatics-phase3-application-freeze.md",
    "docs/superpowers/specs/2026-07-24-bioinformatics-phase3-application-design.md",
    "paper/bioinformatics/README.md",
    "paper/bioinformatics/application_input_summary.tsv",
    "paper/bioinformatics/application_manifest.sha256",
    "paper/bioinformatics/application_manifest.tsv",
    "paper/bioinformatics/application_protocol.md",
    "paper/bioinformatics/application_selection.json",
    "paper/bioinformatics/application_sources.tsv",
    "paper/bioinformatics/claim_evidence.tsv",
    "paper/bioinformatics/development_query_exclusions.tsv",
    "paper/bioinformatics/holdout_manifest.tsv",
    "paper/bioinformatics/submission_manifest.tsv",
    "reproduce/bioinformatics/build_application_panel.py",
    "reproduce/bioinformatics/fetch_application_inputs.sh",
    "scripts/check_bioinformatics_phase3_freeze.sh",
    "tests/check_build_bioinformatics_application_panel.py",
    "config/gasal2_longtarget_contracts.json",
    "schemas/gasal2_longtarget_contracts.schema.json",
    "schemas/gasal2_longtarget_run_report.schema.json",
)
entries: list[dict[str, object]] = []
seen_inodes: set[tuple[int, int]] = set()


def fail(message: str) -> None:
    raise SystemExit(f"Bioinformatics Phase 3 snapshot failed: {message}")


directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
file_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def metadata_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def common_entry(relative: str, metadata: os.stat_result) -> dict[str, object]:
    return {
        "path": relative,
        "mode": metadata.st_mode,
        "size": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "links": metadata.st_nlink,
    }


def revalidate_root() -> None:
    try:
        named = os.lstat(root)
        retained = os.fstat(root_fd)
    except OSError as error:
        fail(f"repository root identity changed: {error}")
    if (
        not stat.S_ISDIR(named.st_mode)
        or not stat.S_ISDIR(retained.st_mode)
        or metadata_signature(named) != root_signature
        or metadata_signature(retained) != root_signature
    ):
        fail("repository root identity changed")


def close_parent_chain(
    chain: list[tuple[int, str, int, tuple[int, int, int, int, int, int], str]],
) -> None:
    for _parent_fd, _name, descriptor, _signature, _relative in reversed(chain):
        os.close(descriptor)


def revalidate_parent_chain(
    chain: list[tuple[int, str, int, tuple[int, int, int, int, int, int], str]],
) -> None:
    for parent_fd, name, descriptor, expected, relative in reversed(chain):
        try:
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            retained = os.fstat(descriptor)
        except OSError as error:
            fail(f"frozen parent directory identity changed: {relative}: {error}")
        if (
            not stat.S_ISDIR(named.st_mode)
            or not stat.S_ISDIR(retained.st_mode)
            or metadata_signature(named) != expected
            or metadata_signature(retained) != expected
        ):
            fail(f"frozen parent directory identity changed: {relative}")
    revalidate_root()


def open_parent_chain(
    relative: str,
) -> tuple[
    int,
    str,
    list[tuple[int, str, int, tuple[int, int, int, int, int, int], str]],
]:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        fail(f"unsafe frozen output path: {relative}")
    revalidate_root()
    current_fd = root_fd
    chain: list[
        tuple[int, str, int, tuple[int, int, int, int, int, int], str]
    ] = []
    try:
        for index, name in enumerate(path.parts[:-1]):
            traversed = "/".join(path.parts[: index + 1])
            try:
                named = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            except OSError as error:
                fail(f"unsafe frozen parent directory: {traversed}: {error}")
            if not stat.S_ISDIR(named.st_mode):
                fail(f"unsafe frozen parent directory: {traversed}")
            try:
                descriptor = os.open(name, directory_flags, dir_fd=current_fd)
            except OSError as error:
                fail(f"unsafe frozen parent directory: {traversed}: {error}")
            retained = os.fstat(descriptor)
            expected = metadata_signature(named)
            if (
                not stat.S_ISDIR(retained.st_mode)
                or metadata_signature(retained) != expected
            ):
                os.close(descriptor)
                fail(f"frozen parent directory identity changed: {traversed}")
            chain.append((current_fd, name, descriptor, expected, traversed))
            current_fd = descriptor
        return current_fd, path.parts[-1], chain
    except BaseException:
        close_parent_chain(chain)
        raise


def hash_regular(
    parent_fd: int,
    name: str,
    relative: str,
    metadata: os.stat_result,
) -> str:
    try:
        descriptor = os.open(name, file_flags, dir_fd=parent_fd)
    except OSError as error:
        fail(f"unsafe regular file while opening: {relative}: {error}")
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            fail(f"unsafe regular file after open: {relative}")
        expected = metadata_signature(metadata)
        if metadata_signature(opened) != expected:
            fail(f"file identity changed while opening: {relative}")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        after = os.fstat(descriptor)
        if metadata_signature(after) != expected:
            fail(f"file mutated while hashing: {relative}")
        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as error:
            fail(f"file bound name changed after hashing: {relative}: {error}")
        if metadata_signature(current) != expected:
            fail(f"file bound name changed after hashing: {relative}")
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def visit_entry(
    parent_fd: int,
    name: str,
    relative: str,
    expected_metadata: os.stat_result | None = None,
) -> None:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        fail(f"missing frozen output: {relative}")
    except OSError as error:
        fail(f"cannot inspect frozen output: {relative}: {error}")
    if (
        expected_metadata is not None
        and metadata_signature(metadata) != metadata_signature(expected_metadata)
    ):
        fail(f"frozen directory child identity changed: {relative}")
    common = common_entry(relative, metadata)
    if stat.S_ISDIR(metadata.st_mode):
        entries.append({**common, "type": "directory", "sha256": ""})
        try:
            directory_fd = os.open(name, directory_flags, dir_fd=parent_fd)
        except OSError as error:
            fail(f"unsafe frozen directory while opening: {relative}: {error}")
        try:
            opened = os.fstat(directory_fd)
            expected = metadata_signature(metadata)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or metadata_signature(opened) != expected
            ):
                fail(f"frozen directory identity changed while opening: {relative}")
            child_names = sorted(os.listdir(directory_fd))
            child_metadata: dict[str, os.stat_result] = {}
            for child_name in child_names:
                try:
                    child_metadata[child_name] = os.stat(
                        child_name,
                        dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                except OSError as error:
                    fail(
                        f"cannot inspect frozen directory child: "
                        f"{relative}/{child_name}: {error}"
                    )
            for child_name in child_names:
                visit_entry(
                    directory_fd,
                    child_name,
                    f"{relative}/{child_name}",
                    child_metadata[child_name],
                )
            if sorted(os.listdir(directory_fd)) != child_names:
                fail(f"frozen directory child set changed: {relative}")
            for child_name, child_initial in child_metadata.items():
                try:
                    child_current = os.stat(
                        child_name,
                        dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                except OSError as error:
                    fail(
                        f"frozen directory child identity changed: "
                        f"{relative}/{child_name}: {error}"
                    )
                if metadata_signature(child_current) != metadata_signature(
                    child_initial
                ):
                    fail(
                        f"frozen directory child identity changed: "
                        f"{relative}/{child_name}"
                    )
            retained = os.fstat(directory_fd)
            if metadata_signature(retained) != expected:
                fail(f"frozen directory metadata changed: {relative}")
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except OSError as error:
                fail(f"frozen directory bound name changed: {relative}: {error}")
            if metadata_signature(current) != expected:
                fail(f"frozen directory bound name changed: {relative}")
        finally:
            os.close(directory_fd)
        return
    if not stat.S_ISREG(metadata.st_mode):
        fail(f"symlink or special frozen output: {relative}")
    if metadata.st_nlink != 1:
        fail(f"frozen output has a hardlink alias: {relative}")
    inode = (metadata.st_dev, metadata.st_ino)
    if inode in seen_inodes:
        fail(f"frozen outputs share an inode: {relative}")
    seen_inodes.add(inode)
    entries.append(
        {
            **common,
            "type": "file",
            "sha256": hash_regular(parent_fd, name, relative, metadata),
        }
    )


def visit_repository_path(relative: str) -> None:
    parent_fd, name, chain = open_parent_chain(relative)
    try:
        visit_entry(parent_fd, name, relative)
        revalidate_parent_chain(chain)
    finally:
        close_parent_chain(chain)


try:
    root_named = os.lstat(root)
    if not stat.S_ISDIR(root_named.st_mode):
        fail("repository root is unsafe")
    root_fd = os.open(root, directory_flags)
except OSError as error:
    fail(f"repository root is unsafe: {error}")
try:
    root_opened = os.fstat(root_fd)
    root_signature = metadata_signature(root_named)
    if (
        not stat.S_ISDIR(root_opened.st_mode)
        or metadata_signature(root_opened) != root_signature
    ):
        fail("repository root identity changed while opening")
    visit_repository_path("reproduce/bioinformatics/application_inputs")
    for relative in metadata_paths:
        visit_repository_path(relative)
    revalidate_root()
finally:
    os.close(root_fd)

payload = (
    json.dumps(entries, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
).encode("ascii")
if destination.parent != run_directory or destination.name not in {
    "application-freeze.before.json",
    "application-freeze.after.json",
}:
    fail(f"snapshot destination escaped run directory: {destination}")
run_named = os.lstat(run_directory)
if (
    not stat.S_ISDIR(run_named.st_mode)
    or (run_named.st_dev, run_named.st_ino) != expected_run_identity
    or stat.S_IMODE(run_named.st_mode) != 0o700
):
    fail("run directory identity changed before snapshot write")
run_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
run_fd = os.open(run_directory, run_flags)
try:
    run_retained = os.fstat(run_fd)
    if (run_retained.st_dev, run_retained.st_ino) != expected_run_identity:
        fail("run directory identity changed while opening snapshot destination")
    try:
        os.stat(destination.name, dir_fd=run_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        fail(f"snapshot destination already exists: {destination}")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(destination.name, flags, 0o600, dir_fd=run_fd)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail(f"short write for snapshot destination: {destination}")
            view = view[written:]
    finally:
        os.close(descriptor)
finally:
    os.close(run_fd)
PY
}

stream_cached_sources=0
validate_workspace_identity
write_application_snapshot "$before_snapshot"
validate_workspace_identity

# BEGIN_PHASE3_OFFLINE_RECONSTRUCTION
run_offline_reconstruction() {
  local offline_bin="$WORK/offline-bin"
  python3 - \
    "$WORK" "$WORK_DEVICE" "$WORK_INODE" "$offline_bin" \
    "$TRUSTED_BASH" "$TRUSTED_BASH_DEVICE" "$TRUSTED_BASH_INODE" \
    "$ROOT" <<'PY_OFFLINE_RECONSTRUCTION'
from __future__ import annotations

from dataclasses import dataclass
import os
import stat
import subprocess
import sys
from pathlib import Path


run_directory = Path(sys.argv[1])
expected_run_identity = (int(sys.argv[2]), int(sys.argv[3]))
offline_directory = Path(sys.argv[4])
trusted_bash = sys.argv[5]
expected_bash_identity = (int(sys.argv[6]), int(sys.argv[7]))
repository_root = Path(sys.argv[8])
fetcher_relative = "reproduce/bioinformatics/fetch_application_inputs.sh"
builder_relative = "reproduce/bioinformatics/build_application_panel.py"
dependency_relatives = (fetcher_relative, builder_relative)
offline_name = "offline-bin"
guard_name = "curl"
guard_bytes = (
    b"#!/bin/sh\n"
    b"printf '%s\\n' 'Phase 3 freeze reconstruction attempted network access' >&2\n"
    b"exit 97\n"
)
guard_stderr = b"Phase 3 freeze reconstruction attempted network access\n"
directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
guard_create_flags = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_CLOEXEC", 0)
    | os.O_NOFOLLOW
)
guard_retention_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | os.O_NOFOLLOW
)
bash_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
dependency_file_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


class OfflineReconstructionError(Exception):
    pass


@dataclass(frozen=True)
class ParentBinding:
    parent_fd: int
    name: str
    descriptor: int
    signature: tuple[int, int, int, int, int, int, int]
    relative: str


@dataclass(frozen=True)
class RetainedDependency:
    relative: str
    parent_fd: int
    name: str
    descriptor: int
    signature: tuple[int, int, int, int, int, int, int]
    parents: tuple[ParentBinding, ...]


def fail(message: str) -> None:
    raise OfflineReconstructionError(message)


def identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def metadata_signature(
    metadata: os.stat_result,
) -> tuple[int, int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_retained_file(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    blocks: list[bytes] = []
    while block := os.read(descriptor, 4096):
        blocks.append(block)
    return b"".join(blocks)


def close_parent_bindings(bindings: tuple[ParentBinding, ...]) -> None:
    for binding in reversed(bindings):
        os.close(binding.descriptor)


def verify_repository_root() -> None:
    if root_fd is None or root_signature is None:
        fail("repository root descriptor is unavailable")
    try:
        named = os.lstat(repository_root)
        retained = os.fstat(root_fd)
    except OSError as error:
        fail(f"repository root identity changed: {error}")
    if (
        not stat.S_ISDIR(named.st_mode)
        or not stat.S_ISDIR(retained.st_mode)
        or metadata_signature(named) != root_signature
        or metadata_signature(retained) != root_signature
    ):
        fail("repository root identity changed")


def open_dependency(relative: str) -> RetainedDependency:
    if root_fd is None:
        fail("repository root descriptor is unavailable")
    parts = relative.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        fail(f"unsafe dependency path: {relative}")
    verify_repository_root()
    current_fd = root_fd
    parents: list[ParentBinding] = []
    dependency_fd: int | None = None
    try:
        for index, name in enumerate(parts[:-1]):
            traversed = "/".join(parts[: index + 1])
            try:
                named = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            except OSError:
                fail(f"unsafe parent directory: {traversed}")
            if not stat.S_ISDIR(named.st_mode):
                fail(f"unsafe parent directory: {traversed}")
            try:
                descriptor = os.open(
                    name,
                    directory_flags,
                    dir_fd=current_fd,
                )
                retained = os.fstat(descriptor)
            except OSError:
                fail(f"cannot retain parent directory: {traversed}")
            signature = metadata_signature(named)
            if (
                not stat.S_ISDIR(retained.st_mode)
                or metadata_signature(retained) != signature
            ):
                os.close(descriptor)
                fail(f"parent directory identity changed: {traversed}")
            parents.append(
                ParentBinding(current_fd, name, descriptor, signature, traversed)
            )
            current_fd = descriptor

        name = parts[-1]
        try:
            named_dependency = os.stat(
                name,
                dir_fd=current_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            fail(f"missing dependency: {relative}")
        except OSError:
            fail(f"unsafe dependency: {relative}")
        if not stat.S_ISREG(named_dependency.st_mode):
            fail(f"dependency is not a regular file: {relative}")
        if named_dependency.st_nlink != 1:
            fail(f"dependency has a hardlink alias: {relative}")
        if relative == fetcher_relative and not named_dependency.st_mode & 0o111:
            fail(f"dependency is not executable: {relative}")
        try:
            dependency_fd = os.open(
                name,
                dependency_file_flags,
                dir_fd=current_fd,
            )
            retained_dependency = os.fstat(dependency_fd)
        except OSError:
            fail(f"cannot retain dependency: {relative}")
        signature = metadata_signature(named_dependency)
        if (
            not stat.S_ISREG(retained_dependency.st_mode)
            or retained_dependency.st_nlink != 1
            or metadata_signature(retained_dependency) != signature
        ):
            fail(f"dependency identity changed while opening: {relative}")
        result = RetainedDependency(
            relative,
            current_fd,
            name,
            dependency_fd,
            signature,
            tuple(parents),
        )
        dependency_fd = None
        parents = []
        return result
    finally:
        if dependency_fd is not None:
            os.close(dependency_fd)
        close_parent_bindings(tuple(parents))


def verify_dependency_file(dependency: RetainedDependency) -> None:
    try:
        named = os.stat(
            dependency.name,
            dir_fd=dependency.parent_fd,
            follow_symlinks=False,
        )
        retained = os.fstat(dependency.descriptor)
    except OSError:
        fail(f"dependency identity changed: {dependency.relative}")
    if (
        not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(retained.st_mode)
        or named.st_nlink != 1
        or retained.st_nlink != 1
        or metadata_signature(named) != dependency.signature
        or metadata_signature(retained) != dependency.signature
    ):
        fail(f"dependency identity changed: {dependency.relative}")


def verify_dependency_parents(dependency: RetainedDependency) -> None:
    for binding in dependency.parents:
        try:
            named = os.stat(
                binding.name,
                dir_fd=binding.parent_fd,
                follow_symlinks=False,
            )
            retained = os.fstat(binding.descriptor)
        except OSError:
            fail(f"parent directory identity changed: {binding.relative}")
        if (
            not stat.S_ISDIR(named.st_mode)
            or not stat.S_ISDIR(retained.st_mode)
            or metadata_signature(named) != binding.signature
            or metadata_signature(retained) != binding.signature
        ):
            fail(f"parent directory identity changed: {binding.relative}")


def verify_dependencies() -> None:
    verify_repository_root()
    for dependency in dependencies:
        verify_dependency_file(dependency)
    for dependency in dependencies:
        verify_dependency_parents(dependency)


def retained_path(dependency: RetainedDependency) -> str:
    return f"/proc/self/fd/{dependency.descriptor}"


run_fd: int | None = None
root_fd: int | None = None
offline_fd: int | None = None
guard_fd: int | None = None
bash_fd: int | None = None
offline_identity: tuple[int, int] | None = None
guard_identity: tuple[int, int] | None = None
owned_offline = False
owned_guard = False
failure: str | None = None
cleanup_failures: list[str] = []
fetcher_status: int | None = None
root_signature: tuple[int, int, int, int, int, int, int] | None = None
dependencies: list[RetainedDependency] = []


def verify_run_directory() -> None:
    if run_fd is None:
        fail("run directory descriptor is unavailable")
    try:
        named = os.lstat(run_directory)
        retained = os.fstat(run_fd)
    except OSError as error:
        fail(f"cannot revalidate run directory: {error}")
    if (
        not stat.S_ISDIR(named.st_mode)
        or not stat.S_ISDIR(retained.st_mode)
        or identity(named) != expected_run_identity
        or identity(retained) != expected_run_identity
        or stat.S_IMODE(named.st_mode) != 0o700
        or stat.S_IMODE(retained.st_mode) != 0o700
    ):
        fail("run directory identity or mode changed")


def verify_trusted_bash() -> None:
    if bash_fd is None:
        fail("trusted Bash descriptor is unavailable")
    trusted_path = Path(trusted_bash)
    try:
        named = os.lstat(trusted_path)
        retained = os.fstat(bash_fd)
    except OSError as error:
        fail(f"cannot revalidate trusted Bash: {error}")
    if (
        not trusted_path.is_absolute()
        or os.path.realpath(trusted_path) != trusted_bash
        or not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(retained.st_mode)
        or identity(named) != expected_bash_identity
        or identity(retained) != expected_bash_identity
        or not named.st_mode & 0o111
        or not retained.st_mode & 0o111
        or not os.access(trusted_path, os.X_OK)
    ):
        fail("trusted Bash identity changed or executable became unsafe")


def verify_offline_tree() -> None:
    if (
        run_fd is None
        or offline_fd is None
        or guard_fd is None
        or offline_identity is None
        or guard_identity is None
    ):
        fail("offline command descriptors are unavailable")
    verify_run_directory()
    try:
        named_offline = os.stat(
            offline_name,
            dir_fd=run_fd,
            follow_symlinks=False,
        )
        retained_offline = os.fstat(offline_fd)
    except OSError as error:
        fail(f"cannot revalidate offline command directory: {error}")
    if (
        not stat.S_ISDIR(named_offline.st_mode)
        or not stat.S_ISDIR(retained_offline.st_mode)
        or identity(named_offline) != offline_identity
        or identity(retained_offline) != offline_identity
        or stat.S_IMODE(named_offline.st_mode) != 0o700
        or stat.S_IMODE(retained_offline.st_mode) != 0o700
    ):
        fail("offline command directory identity or mode changed")
    try:
        entries = os.listdir(offline_fd)
    except OSError as error:
        fail(f"cannot list offline command directory: {error}")
    if entries != [guard_name]:
        fail("offline command directory does not contain exactly curl")
    try:
        named_guard = os.stat(
            guard_name,
            dir_fd=offline_fd,
            follow_symlinks=False,
        )
        retained_guard = os.fstat(guard_fd)
        retained_bytes = read_retained_file(guard_fd)
    except OSError as error:
        fail(f"cannot revalidate offline curl guard: {error}")
    if (
        not stat.S_ISREG(named_guard.st_mode)
        or not stat.S_ISREG(retained_guard.st_mode)
        or identity(named_guard) != guard_identity
        or identity(retained_guard) != guard_identity
        or named_guard.st_nlink != 1
        or retained_guard.st_nlink != 1
        or stat.S_IMODE(named_guard.st_mode) != 0o500
        or stat.S_IMODE(retained_guard.st_mode) != 0o500
        or retained_bytes != guard_bytes
    ):
        fail("offline curl guard identity, links, mode, or bytes changed")


try:
    if not run_directory.is_absolute():
        fail("run directory is not absolute")
    if offline_directory != run_directory / offline_name:
        fail("offline command directory escaped the run directory")
    try:
        named_run = os.lstat(run_directory)
        run_fd = os.open(run_directory, directory_flags)
    except OSError as error:
        fail(f"cannot retain run directory: {error}")
    retained_run = os.fstat(run_fd)
    if (
        not stat.S_ISDIR(named_run.st_mode)
        or identity(named_run) != expected_run_identity
        or identity(retained_run) != expected_run_identity
    ):
        fail("run directory identity changed while opening")
    verify_run_directory()

    if (
        not repository_root.is_absolute()
        or os.path.realpath(repository_root) != str(repository_root)
        or not os.path.isdir("/proc/self/fd")
    ):
        fail("supported Linux repository root or /proc/self/fd is unavailable")
    try:
        named_root = os.lstat(repository_root)
        root_fd = os.open(repository_root, directory_flags)
        retained_root = os.fstat(root_fd)
    except OSError as error:
        fail(f"cannot retain repository root: {error}")
    root_signature = metadata_signature(named_root)
    if (
        not stat.S_ISDIR(named_root.st_mode)
        or not stat.S_ISDIR(retained_root.st_mode)
        or metadata_signature(retained_root) != root_signature
    ):
        fail("repository root identity changed while opening")
    for relative in dependency_relatives:
        dependencies.append(open_dependency(relative))
    verify_dependencies()

    trusted_path = Path(trusted_bash)
    if not trusted_path.is_absolute() or os.path.realpath(trusted_path) != trusted_bash:
        fail("trusted Bash is not a physical absolute path")
    try:
        named_bash = os.lstat(trusted_path)
        bash_fd = os.open(trusted_path, bash_flags)
    except OSError as error:
        fail(f"cannot retain trusted Bash: {error}")
    retained_bash = os.fstat(bash_fd)
    if (
        not stat.S_ISREG(named_bash.st_mode)
        or identity(named_bash) != expected_bash_identity
        or identity(retained_bash) != expected_bash_identity
    ):
        fail("trusted Bash identity changed while opening")
    verify_trusted_bash()

    try:
        os.mkdir(offline_name, mode=0o700, dir_fd=run_fd)
    except FileExistsError:
        fail("offline command directory already exists")
    except OSError as error:
        fail(f"cannot create offline command directory: {error}")
    owned_offline = True
    try:
        named_offline = os.stat(
            offline_name,
            dir_fd=run_fd,
            follow_symlinks=False,
        )
        offline_identity = identity(named_offline)
        offline_fd = os.open(offline_name, directory_flags, dir_fd=run_fd)
        retained_offline = os.fstat(offline_fd)
        os.fchmod(offline_fd, 0o700)
        retained_offline = os.fstat(offline_fd)
    except OSError as error:
        fail(f"cannot retain offline command directory: {error}")
    if (
        not stat.S_ISDIR(named_offline.st_mode)
        or identity(named_offline) != identity(retained_offline)
        or stat.S_IMODE(retained_offline.st_mode) != 0o700
    ):
        fail("offline command directory changed while opening")
    offline_identity = identity(retained_offline)
    if os.listdir(offline_fd):
        fail("new offline command directory is not empty")

    try:
        guard_fd = os.open(
            guard_name,
            guard_create_flags,
            0o500,
            dir_fd=offline_fd,
        )
    except OSError as error:
        fail(f"cannot exclusively create offline curl guard: {error}")
    owned_guard = True
    initial_guard = os.fstat(guard_fd)
    guard_identity = identity(initial_guard)
    if not stat.S_ISREG(initial_guard.st_mode) or initial_guard.st_size != 0:
        fail("new offline curl guard is unsafe")
    view = memoryview(guard_bytes)
    while view:
        written = os.write(guard_fd, view)
        if written <= 0:
            fail("short write for offline curl guard")
        view = view[written:]
    os.fchmod(guard_fd, 0o500)
    os.fsync(guard_fd)
    retained_guard = os.fstat(guard_fd)
    if identity(retained_guard) != guard_identity:
        fail("offline curl guard identity changed while writing")
    try:
        retained_guard_fd = os.open(
            guard_name,
            guard_retention_flags,
            dir_fd=offline_fd,
        )
    except OSError as error:
        fail(f"cannot retain offline curl guard read-only: {error}")
    retained_guard = os.fstat(retained_guard_fd)
    if identity(retained_guard) != guard_identity:
        os.close(retained_guard_fd)
        fail("offline curl guard changed while retaining it read-only")
    os.close(guard_fd)
    guard_fd = retained_guard_fd

    system_tool_directories = (Path("/usr/bin"), Path("/bin"))
    required_system_commands = (
        "cmp",
        "flock",
        "gzip",
        "md5sum",
        "mkdir",
        "mktemp",
        "mv",
        "python3",
        "rm",
        "sha256sum",
        "stat",
        "wc",
    )
    tool_path_entries = (offline_directory, *system_tool_directories)
    if any(
        not str(directory)
        or not directory.is_absolute()
        or not directory.is_dir()
        for directory in tool_path_entries
    ):
        fail("offline tool path contains an unsafe directory")
    for command in required_system_commands:
        if not any(
            (directory / command).is_file()
            and os.access(directory / command, os.X_OK)
            for directory in system_tool_directories
        ):
            fail(f"offline tool path is missing required command: {command}")
    trusted_path = os.pathsep.join(str(directory) for directory in tool_path_entries)
    if not trusted_path:
        fail("offline tool path is empty")
    by_relative = {
        dependency.relative: dependency for dependency in dependencies
    }
    environment = {
        "LC_ALL": "C",
        "PATH": trusted_path,
        "PHASE3_AUTHENTICATED_RECONSTRUCTION": "phase3-offline-v1",
        "PHASE3_AUTHENTICATED_RECONSTRUCTION_BUILDER": retained_path(
            by_relative[builder_relative]
        ),
        "PHASE3_AUTHENTICATED_RECONSTRUCTION_FETCHER": retained_path(
            by_relative[fetcher_relative]
        ),
        "PHASE3_AUTHENTICATED_RECONSTRUCTION_ROOT": str(repository_root),
        "PHASE3_AUTHENTICATED_RECONSTRUCTION_ROOT_DESCRIPTOR": (
            f"/proc/self/fd/{root_fd}"
        ),
        "PYTHONNOUSERSITE": "1",
    }
    inherited_fds = tuple(
        sorted(
            {
                root_fd,
                bash_fd,
                *(dependency.descriptor for dependency in dependencies),
                *(
                    binding.descriptor
                    for dependency in dependencies
                    for binding in dependency.parents
                ),
            }
        )
    )
    bash_path = f"/proc/self/fd/{bash_fd}"
    verify_trusted_bash()
    verify_offline_tree()
    self_test = subprocess.run(
        [str(offline_directory / guard_name)],
        check=False,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if (
        self_test.returncode != 97
        or self_test.stdout != b""
        or self_test.stderr != guard_stderr
    ):
        fail("offline curl guard self-test did not fail with status 97")
    verify_trusted_bash()
    verify_offline_tree()

    verify_trusted_bash()
    verify_offline_tree()
    completed = subprocess.run(
        [bash_path, retained_path(by_relative[fetcher_relative])],
        env=environment,
        pass_fds=inherited_fds,
        check=False,
    )
    fetcher_status = completed.returncode
    verify_trusted_bash()
    verify_dependencies()
    verify_offline_tree()
except OfflineReconstructionError as error:
    failure = str(error)
except OSError as error:
    failure = f"operating-system error: {error}"
finally:
    if owned_guard and offline_fd is not None and guard_identity is not None:
        try:
            named_guard = os.stat(
                guard_name,
                dir_fd=offline_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        except OSError as error:
            cleanup_failures.append(f"cannot inspect owned curl guard: {error}")
        else:
            if identity(named_guard) == guard_identity:
                try:
                    os.unlink(guard_name, dir_fd=offline_fd)
                except OSError as error:
                    cleanup_failures.append(f"cannot remove owned curl guard: {error}")
            else:
                cleanup_failures.append("curl guard name no longer identifies owned guard")
    if guard_fd is not None:
        os.close(guard_fd)
    if owned_offline and run_fd is not None and offline_identity is not None:
        try:
            named_offline = os.stat(
                offline_name,
                dir_fd=run_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        except OSError as error:
            cleanup_failures.append(
                f"cannot inspect owned offline command directory: {error}"
            )
        else:
            if identity(named_offline) == offline_identity:
                try:
                    os.rmdir(offline_name, dir_fd=run_fd)
                except OSError as error:
                    cleanup_failures.append(
                        f"cannot remove owned offline command directory: {error}"
                    )
            else:
                cleanup_failures.append(
                    "offline command name no longer identifies owned directory"
                )
    if offline_fd is not None:
        os.close(offline_fd)
    if bash_fd is not None:
        os.close(bash_fd)
    for dependency in reversed(dependencies):
        os.close(dependency.descriptor)
        close_parent_bindings(dependency.parents)
    if root_fd is not None:
        os.close(root_fd)
    if run_fd is not None:
        os.close(run_fd)

if failure is not None:
    print(f"Phase 3 offline reconstruction failed: {failure}", file=sys.stderr)
for cleanup_failure in cleanup_failures:
    print(
        f"Phase 3 offline reconstruction cleanup failed: {cleanup_failure}",
        file=sys.stderr,
    )
if failure is not None or cleanup_failures:
    raise SystemExit(1)
if fetcher_status is None:
    raise SystemExit("Phase 3 offline reconstruction failed before fetcher execution")
if fetcher_status != 0:
    print(
        f"Phase 3 offline reconstruction fetcher exited with status {fetcher_status}",
        file=sys.stderr,
    )
    raise SystemExit(fetcher_status if 0 < fetcher_status < 256 else 1)
PY_OFFLINE_RECONSTRUCTION
  stream_cached_sources=1
  reconstruction_status="verified_from_complete_cache"
}
# END_PHASE3_OFFLINE_RECONSTRUCTION

require_source_cache_binding "$authoritative_source_cache_binding"
if ((cached_source_count == 4)); then
  validate_workspace_identity
  run_offline_reconstruction
  validate_workspace_identity
else
  reconstruction_status="skipped_incomplete_cache"
fi
require_source_cache_binding "$authoritative_source_cache_binding"
validate_workspace_identity
write_application_snapshot "$after_snapshot"
validate_workspace_identity
cmp -- "$before_snapshot" "$after_snapshot"
git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics Phase 3 application freeze checks OK"
echo "freeze_id=bioinformatics-phase3-application-v1-e8c5441c"
echo "manifest_sha256=e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
echo "query_count=50"
echo "target_count=668"
echo "pair_count=33400"
echo "query_total_nt=56381"
echo "target_total_bp=1670668"
echo "chr21_target_count=221"
echo "chr22_target_count=447"
echo "fasta_file_count=718"
echo "source_cache_count=$cached_source_count"
echo "source_stream_validation_delegated_to_fetcher=$stream_cached_sources"
echo "reconstruction_status=$reconstruction_status"
echo "application_execution_started=0"
