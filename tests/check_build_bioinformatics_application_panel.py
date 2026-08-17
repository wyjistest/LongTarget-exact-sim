#!/usr/bin/env python3
from __future__ import annotations

import csv
import concurrent.futures
import gzip
import hashlib
import importlib.machinery
import importlib.util
import inspect
import io
import json
import multiprocessing
import os
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager, nullcontext
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path, PurePosixPath
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BUILDER_NAME = "build_application_panel.py"
FETCHER_NAME = "fetch_application_inputs.sh"
_AUTHENTICATED_DEPENDENCY_VARIABLES = {
    "builder": "PHASE3_AUTHENTICATED_BUILDER",
    "checker": "PHASE3_AUTHENTICATED_CHECKER",
    "fetcher": "PHASE3_AUTHENTICATED_FETCHER",
    "test": "PHASE3_AUTHENTICATED_TEST",
}
_authenticated_values = {
    name: os.environ.get(variable, "")
    for name, variable in _AUTHENTICATED_DEPENDENCY_VARIABLES.items()
}
if any(_authenticated_values.values()) and not all(_authenticated_values.values()):
    raise RuntimeError("incomplete Phase 3 authenticated dependency environment")
AUTHENTICATED_DEPENDENCY_FDS: tuple[int, ...] = ()
if all(_authenticated_values.values()):
    authenticated_fds: list[int] = []
    for name, value in _authenticated_values.items():
        prefix = "/proc/self/fd/"
        if not value.startswith(prefix) or not value[len(prefix) :].isdigit():
            raise RuntimeError(f"unsafe Phase 3 authenticated {name} dependency")
        descriptor = int(value[len(prefix) :])
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RuntimeError(f"unsafe Phase 3 authenticated {name} dependency")
        authenticated_fds.append(descriptor)
    AUTHENTICATED_DEPENDENCY_FDS = tuple(sorted(set(authenticated_fds)))


def authenticated_path(name: str, fallback: Path) -> Path:
    value = _authenticated_values[name]
    return Path(value) if value else fallback


BUILDER = authenticated_path(
    "builder",
    ROOT / "reproduce/bioinformatics" / BUILDER_NAME,
)
FETCHER = authenticated_path(
    "fetcher",
    ROOT / "reproduce/bioinformatics" / FETCHER_NAME,
)
CHECKER = authenticated_path(
    "checker",
    ROOT / "scripts/check_bioinformatics_phase3_freeze.sh",
)
TEST_MODULE = authenticated_path("test", Path(__file__).resolve())
MANIFEST_FIELDS = (
    "record_id",
    "record_role",
    "source_release",
    "assembly",
    "original_gene_id",
    "original_gene_name",
    "original_transcript_id",
    "selection_rule",
    "sequence_length",
    "chromosome",
    "strand",
    "tss",
    "region_start",
    "region_end",
    "sequence_sha256",
    "file_sha256",
    "path",
    "license_note",
    "split",
    "status",
)
HOLDOUT_MANIFEST_FIELDS = (
    "workload_id",
    "query_id",
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
    "target_id",
    "target_gene_id",
    "target_gene_name",
    "target_chromosome",
    "target_strand",
    "target_tss",
    "target_region_start",
    "target_region_end",
    "target_length_bp",
    "target_sequence_sha256",
    "target_file_sha256",
    "target_path",
    "assembly",
    "annotation_release",
    "selection_seed",
    "requested_contract",
    "run_modes",
    "repeat_count",
    "status",
)
HOLDOUT_QUERY_FIELDS = (
    "gene_id",
    "gene_name",
    "transcript_id",
    "query_length_nt",
    "length_stratum",
    "query_sequence_sha256",
    "query_file_sha256",
    "query_path",
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_manifest() -> list[dict[str, str]]:
    path = ROOT / "paper/bioinformatics/application_manifest.tsv"
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != MANIFEST_FIELDS:
            raise AssertionError("application manifest schema drift")
        return list(reader)


def fingerprint_tree_no_follow(root: Path) -> tuple[tuple[object, ...], ...]:
    entries: list[tuple[object, ...]] = []

    def visit(path: Path, relative: str) -> None:
        metadata = os.lstat(path)
        common = (relative, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns)
        if os.path.islink(path):
            entries.append((*common, "symlink", os.readlink(path)))
            return
        if os.path.isdir(path):
            entries.append((*common, "directory", ""))
            with os.scandir(path) as iterator:
                children = sorted(iterator, key=lambda entry: entry.name)
            for child in children:
                child_relative = child.name if relative == "." else f"{relative}/{child.name}"
                visit(Path(child.path), child_relative)
            return
        if os.path.isfile(path):
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                digest = hashlib.sha256()
                while block := os.read(descriptor, 1024 * 1024):
                    digest.update(block)
            finally:
                os.close(descriptor)
            entries.append((*common, "file", digest.hexdigest()))
            return
        entries.append((*common, "other", ""))

    visit(root, ".")
    return tuple(entries)


def build_freeze_process(
    module: object,
    inputs: object,
    outputs: object,
    pause_after_first: bool,
    first_step: object,
    release: object,
    done: object,
    results: object,
) -> None:
    def after_publish(step: int, _path: Path) -> None:
        if pause_after_first and step == 1:
            first_step.set()
            if not release.wait(15):
                raise RuntimeError("timed out waiting to release first publisher")

    try:
        result = module.build_freeze(inputs, outputs, after_publish=after_publish)
    except BaseException as error:
        results.put(("error", type(error).__name__, str(error)))
    else:
        results.put(("ok", result["freeze_id"]))
    finally:
        done.set()


class Phase3FreezeCheckpointTests(unittest.TestCase):
    FREEZE_ID = "bioinformatics-phase3-application-v1-e8c5441c"
    MANIFEST_SHA256 = (
        "e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
    )
    SOURCE_ARCHIVE_NAMES = (
        "gencode.v49.lncRNA_transcripts.fa.gz",
        "gencode.v49.annotation.gtf.gz",
        "chr21.fa.gz",
        "chr22.fa.gz",
    )

    def test_make_phase3_freeze_target_starts_from_exact_clean_environment(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-make-clean-bootstrap-"
        ) as temporary_name:
            temporary = Path(temporary_name)
            repository = temporary / "repository"
            scripts = repository / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(ROOT / "Makefile", repository / "Makefile")

            environment_dump = temporary / "checker-environment.json"
            exported_function_marker = temporary / "exported-function-ran"
            checker = scripts / "check_bioinformatics_phase3_freeze.sh"
            checker.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if declare -F phase3_exported_marker >/dev/null; then\n"
                "  phase3_exported_marker\n"
                "fi\n"
                f"/usr/bin/python3 - {shlex.quote(str(environment_dump))} <<'PY'\n"
                "import json\n"
                "import os\n"
                "from pathlib import Path\n"
                "import sys\n"
                "Path(sys.argv[1]).write_text(\n"
                "    json.dumps(dict(os.environ), sort_keys=True),\n"
                "    encoding='ascii',\n"
                ")\n"
                "PY\n"
                ":\n",
                encoding="ascii",
            )
            checker.chmod(0o755)

            marker_directory = temporary / "markers"
            marker_directory.mkdir()
            fake_bin = temporary / "fake-bin"
            fake_bin.mkdir()

            def write_wrapper(name: str, executable: str) -> None:
                marker = marker_directory / name
                wrapper = fake_bin / name
                wrapper.write_text(
                    "#!/bin/sh\n"
                    f"printf 'ran\\n' >{shlex.quote(str(marker))}\n"
                    f"exec {shlex.quote(executable)} \"$@\"\n",
                    encoding="ascii",
                )
                wrapper.chmod(0o755)

            write_wrapper("uname", "/usr/bin/uname")
            write_wrapper("mktemp", "/usr/bin/mktemp")
            write_wrapper("bash", "/usr/bin/bash")
            compiler = shutil.which("c++", path="/usr/bin:/bin")
            self.assertIsNotNone(compiler, "test requires a system C++ compiler")
            write_wrapper("phase3-cxx", compiler or "/usr/bin/c++")

            shell_startup_marker = marker_directory / "shell-startup"
            bash_environment = temporary / "bash-environment.sh"
            bash_environment.write_text(
                f"printf 'ran\\n' >{shlex.quote(str(shell_startup_marker))}\n",
                encoding="ascii",
            )
            python_startup_marker = marker_directory / "python-startup"
            python_startup = temporary / "python-startup"
            python_startup.mkdir()
            (python_startup / "sitecustomize.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(python_startup_marker)!r}).write_text(\n"
                "    'ran\\n', encoding='ascii'\n"
                ")\n",
                encoding="ascii",
            )
            work_reexecution_marker = marker_directory / "work-reexecuted"
            opaque_work = (
                f"$$(/usr/bin/touch {work_reexecution_marker})"
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "APPLICATION_PANEL_RESOURCE_PROBE": "caller-controlled",
                    "BASH_ENV": str(bash_environment),
                    "BASH_FUNC_phase3_exported_marker%%": (
                        "() {  /usr/bin/touch "
                        f"{exported_function_marker};\n"
                        "}"
                    ),
                    "CXX": str(fake_bin / "phase3-cxx"),
                    "ENV": str(bash_environment),
                    "MAKEFLAGS": "",
                    "MFLAGS": "",
                    "PATH": f"{fake_bin}:/usr/bin:/bin",
                    "PHASE3_AUTHENTICATED_BUILDER": "/caller/builder",
                    "PHASE3_AUTHENTICATED_CHECKER": "/caller/checker",
                    "PHASE3_AUTHENTICATED_FETCHER": "/caller/fetcher",
                    "PHASE3_AUTHENTICATED_TEST": "/caller/test",
                    "PYTHONPATH": str(python_startup),
                    "SOURCE_DIR": "/caller/source-cache",
                    "WORK": opaque_work,
                }
            )
            make = shutil.which("make", path="/usr/bin:/bin")
            self.assertIsNotNone(make, "test requires system make")
            completed = subprocess.run(
                [make or "/usr/bin/make", "check-bioinformatics-phase3-freeze"],
                cwd=repository,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            executed_markers = sorted(path.name for path in marker_directory.iterdir())
            self.assertEqual(
                executed_markers,
                [],
                "Phase 3 Make target executed caller-controlled hooks: "
                + ", ".join(executed_markers),
            )
            self.assertFalse(exported_function_marker.exists())
            checker_environment = json.loads(environment_dump.read_text(encoding="ascii"))
            self.assertEqual(
                set(checker_environment),
                {
                    "LC_ALL",
                    "PATH",
                    "PHASE3_FREEZE_CLEAN_BOOTSTRAP",
                    "PWD",
                    "SHLVL",
                    "WORK",
                    "_",
                },
            )
            self.assertEqual(checker_environment["LC_ALL"], "C")
            self.assertEqual(checker_environment["PATH"], "/usr/bin:/bin")
            self.assertEqual(
                checker_environment["PHASE3_FREEZE_CLEAN_BOOTSTRAP"],
                "phase3-freeze-v1",
            )
            self.assertEqual(checker_environment["PWD"], str(repository))
            self.assertRegex(checker_environment["SHLVL"], r"^[0-9]+$")
            self.assertEqual(checker_environment["WORK"], opaque_work)
            self.assertEqual(checker_environment["_"], "/usr/bin/python3")

            for marker in marker_directory.iterdir():
                marker.unlink()
            preserved = subprocess.run(
                [make or "/usr/bin/make", "-n", "build"],
                cwd=repository,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            self.assertNotEqual(
                preserved.returncode,
                0,
                "disposable repository unexpectedly contained build inputs",
            )
            self.assertTrue(
                {"uname", "mktemp", "phase3-cxx"}.issubset(
                    path.name for path in marker_directory.iterdir()
                ),
                "non-Phase-3 Make goals no longer use the existing probes",
            )

    def test_checker_rejects_unclean_bootstrap_before_external_commands(
        self,
    ) -> None:
        for label, contract in (("missing", None), ("malformed", "wrong-contract")):
            with self.subTest(contract=label), tempfile.TemporaryDirectory(
                prefix=f"phase3-checker-bootstrap-{label}-"
            ) as temporary_name:
                temporary = Path(temporary_name)
                repository = temporary / "repository"
                scripts = repository / "scripts"
                scripts.mkdir(parents=True)
                checker = scripts / "check_bioinformatics_phase3_freeze.sh"
                shutil.copy2(CHECKER, checker)
                checker.chmod(0o755)
                external_marker = temporary / "external-command-ran"
                fake_bin = temporary / "fake-bin"
                fake_bin.mkdir()
                for name in ("dirname", "python3"):
                    wrapper = fake_bin / name
                    wrapper.write_text(
                        "#!/bin/sh\n"
                        f"printf '%s\\n' {shlex.quote(name)} "
                        f">>{shlex.quote(str(external_marker))}\n"
                        f"exec /usr/bin/{name} \"$@\"\n",
                        encoding="ascii",
                    )
                    wrapper.chmod(0o755)
                environment = {
                    "LC_ALL": "C",
                    "PATH": f"{fake_bin}:/usr/bin:/bin",
                    "WORK": str(temporary / "work"),
                }
                if contract is not None:
                    environment["PHASE3_FREEZE_CLEAN_BOOTSTRAP"] = contract
                completed = subprocess.run(
                    ["/usr/bin/bash", "--noprofile", "--norc", str(checker)],
                    cwd=repository,
                    env=environment,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                    check=False,
                )

                self.assertFalse(
                    external_marker.exists(),
                    "checker executed external commands before rejecting "
                    f"{label} clean bootstrap: "
                    + (
                        external_marker.read_text(encoding="ascii").strip()
                        if external_marker.exists()
                        else ""
                    ),
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(
                    "Phase 3 checker clean bootstrap failed: "
                    "missing or malformed contract",
                    completed.stderr,
                )

    def run_checker_cache_preflight(
        self,
        configure: object,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="phase3-cache-preflight-") as temporary:
            temporary_root = Path(temporary)
            repository = temporary_root / "repository"
            scripts = repository / "scripts"
            scripts.mkdir(parents=True)
            checker = scripts / "check_bioinformatics_phase3_freeze.sh"
            shutil.copy2(
                CHECKER,
                checker,
            )
            checker.chmod(0o755)
            configure(repository, temporary_root)
            environment = {
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
                "PHASE3_FREEZE_CLEAN_BOOTSTRAP": "phase3-freeze-v1",
                "WORK": str(temporary_root / "checker-work"),
            }
            return subprocess.run(
                ["/usr/bin/bash", "--noprofile", "--norc", str(checker)],
                cwd=repository,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
            )

    def run_checker_work_preflight(
        self,
        work_path: object,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="phase3-work-preflight-") as temporary:
            temporary_root = Path(temporary)
            repository = temporary_root / "repository"
            scripts = repository / "scripts"
            scripts.mkdir(parents=True)
            checker = scripts / "check_bioinformatics_phase3_freeze.sh"
            shutil.copy2(
                CHECKER,
                checker,
            )
            checker.chmod(0o755)
            selected_work = work_path(repository, temporary_root)
            environment = {
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
                "PHASE3_FREEZE_CLEAN_BOOTSTRAP": "phase3-freeze-v1",
                "WORK": str(selected_work),
            }
            return subprocess.run(
                ["/usr/bin/bash", "--noprofile", "--norc", str(checker)],
                cwd=repository,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
            )

    def workspace_setup_source(self) -> str:
        checker = CHECKER.read_text(encoding="utf-8", errors="strict")
        marker = 'workspace_receipt="$(python3 - "$ROOT" "$WORK" <<\'PY_WORKSPACE\'\n'
        self.assertEqual(checker.count(marker), 1)
        start = checker.index(marker) + len(marker)
        end = checker.index("\nPY_WORKSPACE\n)\"", start)
        return checker[start:end]

    def offline_reconstruction_source(self) -> tuple[str, bool]:
        checker = CHECKER.read_text(encoding="utf-8", errors="strict")
        begin = "# BEGIN_PHASE3_OFFLINE_RECONSTRUCTION\n"
        end = "# END_PHASE3_OFFLINE_RECONSTRUCTION\n"
        if begin in checker:
            self.assertEqual(checker.count(begin), 1)
            self.assertEqual(checker.count(end), 1)
            return checker.split(begin, 1)[1].split(end, 1)[0], True
        start_marker = "if ((cached_source_count == 4)); then\n"
        end_marker = (
            "\nelse\n"
            '  reconstruction_status="skipped_incomplete_cache"\n'
            "fi"
        )
        self.assertEqual(checker.count(start_marker), 1)
        start = checker.index(start_marker) + len(start_marker)
        end_offset = checker.index(end_marker, start)
        return checker[start:end_offset], False

    def preexecution_dependency_source(self) -> str:
        checker = CHECKER.read_text(encoding="utf-8", errors="strict")
        begin = "# BEGIN_PHASE3_PREEXECUTION_DEPENDENCIES\n"
        end = "# END_PHASE3_PREEXECUTION_DEPENDENCIES\n"
        if begin in checker:
            self.assertEqual(checker.count(begin), 1)
            self.assertEqual(checker.count(end), 1)
            return checker.split(begin, 1)[1].split(end, 1)[0]
        legacy_begin = "for relative in \\\n  paper/bioinformatics/README.md \\\n"
        legacy_end = 'git -C "$ROOT" diff --cached --check\n'
        self.assertEqual(checker.count(legacy_begin), 1)
        start = checker.index(legacy_begin)
        finish = checker.index(legacy_end, start) + len(legacy_end)
        return checker[start:finish]

    def create_preexecution_dependency_repository(
        self,
        temporary: Path,
        marker: Path,
        *,
        test_dependency_source: str | None = None,
    ) -> tuple[Path, str]:
        repository = temporary / "repository"
        required_files = (
            "paper/bioinformatics/README.md",
            "paper/bioinformatics/application_input_summary.tsv",
            "paper/bioinformatics/application_manifest.tsv",
            "paper/bioinformatics/application_protocol.md",
            "paper/bioinformatics/application_selection.json",
            "paper/bioinformatics/application_sources.tsv",
            "paper/bioinformatics/claim_evidence.tsv",
            "paper/bioinformatics/development_query_exclusions.tsv",
            "paper/bioinformatics/holdout_manifest.tsv",
            "paper/bioinformatics/submission_manifest.tsv",
        )
        for relative in required_files:
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "{}\n" if path.suffix == ".json" else "fixture\n",
                encoding="ascii",
            )
        manifest = repository / "paper/bioinformatics/application_manifest.tsv"
        manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
        (repository / "paper/bioinformatics/application_manifest.sha256").write_text(
            f"{manifest_digest}  application_manifest.tsv\n",
            encoding="ascii",
        )
        (repository / "reproduce/bioinformatics/application_inputs").mkdir(
            parents=True
        )
        builder = repository / "reproduce/bioinformatics/build_application_panel.py"
        builder.write_text("pass\n", encoding="ascii")
        fetcher = repository / "reproduce/bioinformatics/fetch_application_inputs.sh"
        fetcher.write_text("#!/bin/bash\nexit 0\n", encoding="ascii")
        fetcher.chmod(0o755)
        checker = repository / "scripts/check_bioinformatics_phase3_freeze.sh"
        checker.parent.mkdir(parents=True)
        checker.write_text("#!/bin/bash\nexit 0\n", encoding="ascii")
        checker.chmod(0o755)
        for relative in (
            "config/gasal2_longtarget_contracts.json",
            "schemas/gasal2_longtarget_contracts.schema.json",
            "schemas/gasal2_longtarget_run_report.schema.json",
        ):
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="ascii")
        test_dependency = (
            repository / "tests/check_build_bioinformatics_application_panel.py"
        )
        test_dependency.parent.mkdir(parents=True)
        if test_dependency_source is None:
            test_dependency_source = (
                "from pathlib import Path\n"
                f"marker = Path({str(marker)!r})\n"
                "count = int(marker.read_text(encoding='ascii')) "
                "if marker.exists() else 0\n"
                "marker.write_text(str(count + 1), encoding='ascii')\n"
            )
        test_dependency.write_text(test_dependency_source, encoding="ascii")
        subprocess.run(
            ["git", "init", "-q", str(repository)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "config",
                "user.email",
                "phase3@test.invalid",
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "config",
                "user.name",
                "Phase 3 Test",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "add", "--all"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "commit", "-qm", "fixture"],
            check=True,
        )
        baseline = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        return repository, baseline

    def run_preexecution_dependency_harness(
        self,
        repository: Path,
        baseline: str,
        *,
        environment_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        trusted_bash = Path(os.environ.get("BASH", "/bin/bash")).resolve()
        trusted_metadata = os.lstat(trusted_bash)
        script = (
            "set -euo pipefail\n"
            'ROOT="$HARNESS_ROOT"\n'
            'BASELINE="$HARNESS_BASELINE"\n'
            'FETCHER="$ROOT/reproduce/bioinformatics/fetch_application_inputs.sh"\n'
            'TRUSTED_BASH="$HARNESS_TRUSTED_BASH"\n'
            'TRUSTED_BASH_DEVICE="$HARNESS_BASH_DEVICE"\n'
            'TRUSTED_BASH_INODE="$HARNESS_BASH_INODE"\n'
            f"{self.preexecution_dependency_source()}"
        )
        environment = os.environ.copy()
        environment.update(
            {
                "HARNESS_ROOT": str(repository),
                "HARNESS_BASELINE": baseline,
                "HARNESS_TRUSTED_BASH": str(trusted_bash),
                "HARNESS_BASH_DEVICE": str(trusted_metadata.st_dev),
                "HARNESS_BASH_INODE": str(trusted_metadata.st_ino),
            }
        )
        if environment_overrides is not None:
            environment.update(environment_overrides)
        return subprocess.run(
            [str(trusted_bash), "-c", script],
            cwd=repository,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )

    def source_cache_binding_source(self) -> str:
        checker = CHECKER.read_text(encoding="utf-8", errors="strict")
        begin = "# BEGIN_PHASE3_SOURCE_CACHE_BINDING\n"
        end = "# END_PHASE3_SOURCE_CACHE_BINDING\n"
        if begin in checker:
            self.assertEqual(checker.count(begin), 1)
            self.assertEqual(checker.count(end), 1)
            return checker.split(begin, 1)[1].split(end, 1)[0]
        legacy_begin = 'cached_source_count="$(python3 - "$ROOT" <<\'PY\'\n'
        self.assertEqual(checker.count(legacy_begin), 1)
        start = checker.index(legacy_begin) + len(legacy_begin)
        finish = checker.index("\nPY\n)\"", start)
        legacy_python = checker[start:finish]
        return (
            "capture_source_cache_binding() {\n"
            "  python3 - \"$ROOT\" <<'PY_LEGACY_SOURCE_CACHE'\n"
            f"{legacy_python}\n"
            "PY_LEGACY_SOURCE_CACHE\n"
            "}\n"
            "require_source_cache_binding() {\n"
            "  local expected=\"$1\"\n"
            "  local current\n"
            "  if ! current=\"$(capture_source_cache_binding)\"; then\n"
            "    echo \"Bioinformatics Phase 3 cache binding changed: "
            "fresh inspection failed\" >&2\n"
            "    return 1\n"
            "  fi\n"
            "  if [[ \"$current\" != \"$expected\" ]]; then\n"
            "    echo \"Bioinformatics Phase 3 cache binding changed: "
            "structural receipt differs\" >&2\n"
            "    return 1\n"
            "  fi\n"
            "}\n"
        )

    def run_source_cache_binding_harness(
        self,
        repository: Path,
        *,
        expected_binding: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        source = self.source_cache_binding_source()
        if expected_binding is None:
            invocation = "capture_source_cache_binding\n"
        else:
            invocation = (
                'require_source_cache_binding "$HARNESS_EXPECTED_BINDING"\n'
            )
        script = (
            "set -euo pipefail\n"
            'ROOT="$HARNESS_ROOT"\n'
            f"{source}\n"
            f"{invocation}"
        )
        trusted_bash = Path(os.environ.get("BASH", "/bin/bash")).resolve()
        environment = os.environ.copy()
        environment.update(
            {
                "HARNESS_ROOT": str(repository),
                "HARNESS_EXPECTED_BINDING": expected_binding or "",
            }
        )
        return subprocess.run(
            [str(trusted_bash), "-c", script],
            cwd=repository,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )

    def create_source_cache(self, repository: Path, *, complete: bool) -> Path:
        cache = repository / ".tmp/bioinformatics_application_sources"
        cache.mkdir(parents=True)
        if complete:
            for index, name in enumerate(self.SOURCE_ARCHIVE_NAMES, start=1):
                (cache / name).write_bytes(f"archive-{index}\n".encode("ascii"))
        return cache

    def run_offline_reconstruction_harness(
        self,
        *,
        temporary_root: Path,
        fetcher: Path,
        pre_invocation_source: str = "",
    ) -> subprocess.CompletedProcess[str]:
        source, requires_invocation = self.offline_reconstruction_source()
        repository = temporary_root / "repository"
        dependency_directory = repository / "reproduce/bioinformatics"
        dependency_directory.mkdir(parents=True)
        retained_fetcher = dependency_directory / FETCHER_NAME
        if fetcher.is_file():
            shutil.copy2(fetcher, retained_fetcher)
        else:
            retained_fetcher.write_text("#!/bin/bash\nexit 0\n", encoding="ascii")
            retained_fetcher.chmod(0o700)
        (dependency_directory / BUILDER_NAME).write_text(
            "pass\n",
            encoding="ascii",
        )
        work = temporary_root / "authenticated-run"
        work.mkdir(mode=0o700, exist_ok=True)
        work.chmod(0o700)
        work_metadata = os.lstat(work)
        trusted_bash = Path(os.environ.get("BASH", "/bin/bash")).resolve()
        trusted_metadata = os.lstat(trusted_bash)
        invocation = "run_offline_reconstruction\n" if requires_invocation else ""
        script = (
            "set -euo pipefail\n"
            'ROOT="$HARNESS_ROOT"\n'
            'WORK="$HARNESS_WORK"\n'
            'FETCHER="$ROOT/reproduce/bioinformatics/fetch_application_inputs.sh"\n'
            'TRUSTED_BASH="$HARNESS_TRUSTED_BASH"\n'
            'WORK_DEVICE="$HARNESS_WORK_DEVICE"\n'
            'WORK_INODE="$HARNESS_WORK_INODE"\n'
            'TRUSTED_BASH_DEVICE="$HARNESS_BASH_DEVICE"\n'
            'TRUSTED_BASH_INODE="$HARNESS_BASH_INODE"\n'
            "validate_workspace_identity() { :; }\n"
            "stream_cached_sources=0\n"
            "reconstruction_status=not-set\n"
            f"{source}\n"
            f"{pre_invocation_source}"
            f"{invocation}"
            'printf "reconstruction_status=%s\\n" "$reconstruction_status"\n'
        )
        environment = os.environ.copy()
        environment.update(
            {
                "HARNESS_ROOT": str(repository),
                "HARNESS_WORK": str(work),
                "HARNESS_TRUSTED_BASH": str(trusted_bash),
                "HARNESS_WORK_DEVICE": str(work_metadata.st_dev),
                "HARNESS_WORK_INODE": str(work_metadata.st_ino),
                "HARNESS_BASH_DEVICE": str(trusted_metadata.st_dev),
                "HARNESS_BASH_INODE": str(trusted_metadata.st_ino),
            }
        )
        return subprocess.run(
            [str(trusted_bash), "-c", script],
            cwd=temporary_root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )

    def create_retained_reconstruction_repository(
        self,
        temporary: Path,
        *,
        fail_verify: bool,
    ) -> dict[str, Path]:
        repository = temporary / "repository"
        script_directory = repository / "reproduce/bioinformatics"
        paper_directory = repository / "paper/bioinformatics"
        source_directory = repository / ".tmp/bioinformatics_application_sources"
        for directory in (script_directory, paper_directory, source_directory):
            directory.mkdir(parents=True)

        source_fields = (
            "source_id",
            "role",
            "provider",
            "release",
            "assembly",
            "url",
            "upstream_md5",
            "compressed_size_bytes",
            "compressed_sha256",
            "decompressed_size_bytes",
            "decompressed_sha256",
            "local_source_path",
            "license_or_terms",
            "redistribution_note",
            "download_command",
        )
        source_identities = (
            ("gencode_v49_lncrna", "gencode.v49.lncRNA_transcripts.fa.gz"),
            ("gencode_v49_gtf", "gencode.v49.annotation.gtf.gz"),
            ("ucsc_hg38_chr21", "chr21.fa.gz"),
            ("ucsc_hg38_chr22", "chr22.fa.gz"),
        )
        source_rows: list[dict[str, object]] = []
        for index, (source_id, name) in enumerate(source_identities, start=1):
            decompressed = f">fixture-{index}\n{'ACGT' * index}\n".encode("ascii")
            compressed = gzip.compress(decompressed, mtime=0)
            (source_directory / name).write_bytes(compressed)
            source_rows.append(
                {
                    "source_id": source_id,
                    "role": "fixture",
                    "provider": "fixture-provider",
                    "release": "fixture-release",
                    "assembly": "GRCh38",
                    "url": f"https://example.invalid/{name}",
                    "upstream_md5": hashlib.md5(compressed).hexdigest(),
                    "compressed_size_bytes": len(compressed),
                    "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
                    "decompressed_size_bytes": len(decompressed),
                    "decompressed_sha256": hashlib.sha256(decompressed).hexdigest(),
                    "local_source_path": (
                        ".tmp/bioinformatics_application_sources/" + name
                    ),
                    "license_or_terms": "fixture-terms",
                    "redistribution_note": "fixture-only",
                    "download_command": f"curl https://example.invalid/{name}",
                }
            )
        source_table_handle = io.StringIO(newline="")
        source_writer = csv.DictWriter(
            source_table_handle,
            fieldnames=source_fields,
            delimiter="\t",
            lineterminator="\n",
        )
        source_writer.writeheader()
        source_writer.writerows(source_rows)
        source_table = source_table_handle.getvalue()

        fetcher = script_directory / FETCHER_NAME
        shutil.copy2(FETCHER, fetcher)
        fetcher.chmod(0o755)
        builder_log = temporary / "builder-invocations.tsv"
        builder_entered = temporary / "builder-sources-entered"
        builder_release = temporary / "builder-sources-release"
        builder = script_directory / BUILDER_NAME
        builder.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "import time\n"
            f"SOURCE_TABLE = {source_table!r}\n"
            f"LOG = Path({str(builder_log)!r})\n"
            f"FAIL_VERIFY = {fail_verify!r}\n"
            f"ENTERED = Path({str(builder_entered)!r})\n"
            f"RELEASE = Path({str(builder_release)!r})\n"
            "command = sys.argv[1]\n"
            "with LOG.open('a', encoding='ascii') as handle:\n"
            "    handle.write(f'{sys.argv[0]}\\t{command}\\n')\n"
            "def option(name: str) -> Path:\n"
            "    return Path(sys.argv[sys.argv.index(name) + 1])\n"
            "if command == 'sources':\n"
            "    sys.stdout.write(SOURCE_TABLE)\n"
            "    sys.stdout.flush()\n"
            "    if FAIL_VERIFY:\n"
            "        ENTERED.touch()\n"
            "        while not RELEASE.exists():\n"
            "            time.sleep(0.001)\n"
            "elif command == 'select':\n"
            "    destination = option('--selection-receipt')\n"
            "    destination.parent.mkdir(parents=True, exist_ok=True)\n"
            "    destination.write_text('fixture-selection\\n', encoding='ascii')\n"
            "elif command == 'verify':\n"
            "    if FAIL_VERIFY:\n"
            "        raise SystemExit(23)\n"
            "else:\n"
            "    raise SystemExit(91)\n",
            encoding="ascii",
        )

        (paper_directory / "development_query_exclusions.tsv").write_text(
            "fixture\n", encoding="ascii"
        )
        (paper_directory / "holdout_manifest.tsv").write_text(
            "fixture\n", encoding="ascii"
        )
        (paper_directory / "application_selection.json").write_text(
            "fixture-selection\n", encoding="ascii"
        )
        (script_directory / "application_inputs").mkdir()
        for name in (
            "application_manifest.tsv",
            "application_manifest.sha256",
            "application_sources.tsv",
            "application_input_summary.tsv",
        ):
            (paper_directory / name).write_text(f"{name}\n", encoding="ascii")
        temporary_directory = temporary / "temporary"
        temporary_directory.mkdir()
        return {
            "temporary": temporary,
            "repository": repository,
            "fetcher": fetcher,
            "builder": builder,
            "builder_log": builder_log,
            "builder_entered": builder_entered,
            "builder_release": builder_release,
            "temporary_directory": temporary_directory,
        }

    def run_offline_reconstruction_dependency_race(
        self,
        fixture: dict[str, Path],
        *,
        dependency: str,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        source, requires_invocation = self.offline_reconstruction_source()
        temporary = fixture["temporary"]
        repository = fixture["repository"]
        work = temporary / "authenticated-run"
        work.mkdir(mode=0o700)
        work.chmod(0o700)
        work_metadata = os.lstat(work)
        trusted_bash = Path("/usr/bin/bash").resolve()
        trusted_metadata = os.lstat(trusted_bash)
        invocation = "run_offline_reconstruction\n" if requires_invocation else ""
        script = (
            "set -euo pipefail\n"
            'ROOT="$HARNESS_ROOT"\n'
            'WORK="$HARNESS_WORK"\n'
            'FETCHER="$HARNESS_FETCHER"\n'
            'TRUSTED_BASH="$HARNESS_TRUSTED_BASH"\n'
            'WORK_DEVICE="$HARNESS_WORK_DEVICE"\n'
            'WORK_INODE="$HARNESS_WORK_INODE"\n'
            'TRUSTED_BASH_DEVICE="$HARNESS_BASH_DEVICE"\n'
            'TRUSTED_BASH_INODE="$HARNESS_BASH_INODE"\n'
            "validate_workspace_identity() { :; }\n"
            "stream_cached_sources=0\n"
            "reconstruction_status=not-set\n"
            f"{source}\n"
            f"{invocation}"
            'printf "reconstruction_status=%s\\n" "$reconstruction_status"\n'
        )
        environment = {
            "HARNESS_ROOT": str(repository),
            "HARNESS_WORK": str(work),
            "HARNESS_FETCHER": str(fixture["fetcher"]),
            "HARNESS_TRUSTED_BASH": str(trusted_bash),
            "HARNESS_WORK_DEVICE": str(work_metadata.st_dev),
            "HARNESS_WORK_INODE": str(work_metadata.st_ino),
            "HARNESS_BASH_DEVICE": str(trusted_metadata.st_dev),
            "HARNESS_BASH_INODE": str(trusted_metadata.st_ino),
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
        }
        process = subprocess.Popen(
            [str(trusted_bash), "-c", script],
            cwd=repository,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stopped_child: int | None = None
        replacement_marker = temporary / f"replacement-{dependency}-ran"
        try:
            if dependency == "fetcher":
                deadline = time.monotonic() + 10
                children_path = Path(
                    f"/proc/{process.pid}/task/{process.pid}/children"
                )
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        child_ids = [
                            int(value) for value in children_path.read_text().split()
                        ]
                    except (FileNotFoundError, ProcessLookupError):
                        break
                    for child_id in child_ids:
                        descriptor_root = Path(f"/proc/{child_id}/fd")
                        try:
                            descriptors = tuple(descriptor_root.iterdir())
                        except FileNotFoundError:
                            continue
                        retained_bash = False
                        for descriptor in descriptors:
                            try:
                                metadata = os.stat(descriptor)
                            except OSError:
                                continue
                            if (metadata.st_dev, metadata.st_ino) == (
                                trusted_metadata.st_dev,
                                trusted_metadata.st_ino,
                            ):
                                retained_bash = True
                                break
                        if retained_bash:
                            try:
                                os.kill(child_id, signal.SIGSTOP)
                            except ProcessLookupError:
                                continue
                            stopped_child = child_id
                            break
                    if stopped_child is not None:
                        break
                    time.sleep(0.0005)
                self.assertIsNotNone(
                    stopped_child,
                    "did not observe offline reconstruction dependency-retention phase",
                )
                assert stopped_child is not None
                status_path = Path(f"/proc/{stopped_child}/status")
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        status = status_path.read_text(encoding="ascii")
                    except FileNotFoundError:
                        break
                    if "\nState:\tT" in "\n" + status:
                        break
                    time.sleep(0.0005)
                else:
                    self.fail("offline reconstruction child did not stop")
            else:
                deadline = time.monotonic() + 20
                while (
                    not fixture["builder_entered"].exists()
                    and time.monotonic() < deadline
                    and process.poll() is None
                ):
                    time.sleep(0.001)
                self.assertTrue(
                    fixture["builder_entered"].exists(),
                    "builder did not enter the first retained subcommand",
                )

            target = (
                fixture["builder"]
                if dependency == "builder-inplace"
                else fixture[dependency]
            )
            if dependency == "builder-inplace":
                original_bytes = target.read_bytes()
                original_metadata = os.stat(target)
                replacement_source = (
                    "from pathlib import Path\n"
                    "import os\n"
                    "import sys\n"
                    f"BUILDER = Path({str(target)!r})\n"
                    f"MARKER = Path({str(replacement_marker)!r})\n"
                    f"ORIGINAL = {original_bytes!r}\n"
                    f"ATIME_NS = {original_metadata.st_atime_ns}\n"
                    f"MTIME_NS = {original_metadata.st_mtime_ns}\n"
                    "MARKER.write_text('ran\\n', encoding='ascii')\n"
                    "BUILDER.write_bytes(ORIGINAL)\n"
                    "os.utime(BUILDER, ns=(ATIME_NS, MTIME_NS))\n"
                    "if sys.argv[1] == 'select':\n"
                    "    option = sys.argv.index('--selection-receipt') + 1\n"
                    "    destination = Path(sys.argv[option])\n"
                    "    destination.parent.mkdir(parents=True, exist_ok=True)\n"
                    "    destination.write_text(\n"
                    "        'fixture-selection\\n', encoding='ascii'\n"
                    "    )\n"
                    "else:\n"
                    "    raise SystemExit(92)\n"
                )
                time.sleep(0.01)
                target.write_text(replacement_source, encoding="ascii")
                self.assertEqual(
                    (os.stat(target).st_dev, os.stat(target).st_ino),
                    (original_metadata.st_dev, original_metadata.st_ino),
                )
            else:
                target.rename(temporary / f"retained-{target.name}")
            if dependency == "fetcher":
                target.write_text(
                    "#!/usr/bin/bash\n"
                    f"printf 'ran\\n' >{shlex.quote(str(replacement_marker))}\n"
                    "exit 89\n",
                    encoding="ascii",
                )
                target.chmod(0o755)
            elif dependency == "builder":
                target.write_text(
                    "from pathlib import Path\n"
                    f"Path({str(replacement_marker)!r}).write_text(\n"
                    "    'ran\\n', encoding='ascii'\n"
                    ")\n"
                    "raise SystemExit(91)\n",
                    encoding="ascii",
                )
            if dependency == "fetcher":
                os.kill(stopped_child, signal.SIGCONT)
                stopped_child = None
            else:
                fixture["builder_release"].touch()
            stdout, stderr = process.communicate(timeout=30)
        finally:
            if stopped_child is not None:
                try:
                    os.kill(stopped_child, signal.SIGCONT)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
                process.communicate()
        return (
            subprocess.CompletedProcess(
                process.args,
                process.returncode,
                stdout,
                stderr,
            ),
            replacement_marker,
        )

    def test_work_base_rejects_protected_repository_overlap_before_dependencies(
        self,
    ) -> None:
        def repository_root(repository: Path, _temporary: Path) -> Path:
            return repository

        def paper_directory(repository: Path, _temporary: Path) -> Path:
            path = repository / "paper/bioinformatics"
            path.mkdir(parents=True)
            return path

        def input_directory(repository: Path, _temporary: Path) -> Path:
            path = repository / "reproduce/bioinformatics/application_inputs"
            path.mkdir(parents=True)
            return path

        def intermediate_symlink(repository: Path, temporary: Path) -> Path:
            protected = repository / "paper/bioinformatics"
            protected.mkdir(parents=True)
            alias = temporary / "repository-alias"
            alias.symlink_to(repository, target_is_directory=True)
            return alias / "paper/bioinformatics"

        for label, select_work in (
            ("repository-root", repository_root),
            ("paper-directory", paper_directory),
            ("input-directory", input_directory),
            ("intermediate-symlink", intermediate_symlink),
        ):
            with self.subTest(work=label):
                completed = self.run_checker_work_preflight(select_work)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(
                    "Phase 3 checker work base overlaps protected repository paths",
                    completed.stderr,
                )
                self.assertNotIn("missing or unsafe Bioinformatics", completed.stderr)

    def test_workspace_setup_uses_exclusive_child_and_preserves_base_sentinel(
        self,
    ) -> None:
        source = self.workspace_setup_source()
        with tempfile.TemporaryDirectory(prefix="phase3-workspace-setup-") as temporary:
            temporary_root = Path(temporary)
            repository = temporary_root / "repository"
            repository.mkdir()
            work_base = temporary_root / "external-work"
            work_base.mkdir()
            sentinel = work_base / "application-freeze.before.json"
            sentinel.write_text("owner-sentinel\n", encoding="ascii")
            completed = subprocess.run(
                [sys.executable, "-c", source, str(repository), str(work_base)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = completed.stdout.strip().split("\t")
            self.assertEqual(len(receipt), 6)
            run_directory = Path(receipt[0])
            self.assertEqual(Path(receipt[1]), work_base.resolve())
            self.assertEqual(run_directory.parent, work_base.resolve())
            self.assertNotEqual(run_directory, work_base.resolve())
            self.assertTrue(run_directory.name.startswith("bioinformatics-phase3-freeze."))
            self.assertEqual(stat.S_IMODE(os.lstat(run_directory).st_mode), 0o700)
            self.assertEqual(sentinel.read_text(encoding="ascii"), "owner-sentinel\n")
            self.assertFalse((run_directory / sentinel.name).exists())

            symlink_base = temporary_root / "symlink-work"
            symlink_base.symlink_to(work_base, target_is_directory=True)
            rejected = subprocess.run(
                [sys.executable, "-c", source, str(repository), str(symlink_base)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("work base final component is a symlink", rejected.stderr)

    def test_workspace_rejects_source_cache_aliases_without_mutation(self) -> None:
        source = self.workspace_setup_source()
        scenarios = ("direct", "intermediate-alias", "final-alias")
        for scenario in scenarios:
            with self.subTest(work=scenario), tempfile.TemporaryDirectory(
                prefix=f"phase3-work-cache-{scenario}-"
            ) as temporary_name:
                temporary = Path(temporary_name)
                repository = temporary / "repository"
                repository.mkdir()
                cache = self.create_source_cache(repository, complete=True)
                before = fingerprint_tree_no_follow(cache)

                if scenario == "direct":
                    work = cache
                elif scenario == "intermediate-alias":
                    alias = temporary / "cache-alias"
                    alias.symlink_to(cache, target_is_directory=True)
                    work = alias / "nested-work"
                else:
                    alias = temporary / "cache-final-alias"
                    alias.symlink_to(cache, target_is_directory=True)
                    work = alias

                completed = subprocess.run(
                    [sys.executable, "-c", source, str(repository), str(work)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                    check=False,
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(
                    "work base overlaps Phase 3 source cache",
                    completed.stderr,
                )
                self.assertEqual(fingerprint_tree_no_follow(cache), before)
                self.assertFalse(
                    any(
                        path.name.startswith("bioinformatics-phase3-freeze.")
                        for path in cache.rglob("*")
                    )
                )

    def test_preexecution_dependencies_are_retained_before_repository_code(
        self,
    ) -> None:
        scenarios = (
            (
                "intermediate-parent-alias",
                "unsafe parent directory: tests",
            ),
            (
                "external-hardlink",
                "dependency has a hardlink alias: "
                "tests/check_build_bioinformatics_application_panel.py",
            ),
            ("valid", None),
        )
        for scenario, expected_error in scenarios:
            with self.subTest(dependency=scenario), tempfile.TemporaryDirectory(
                prefix=f"phase3-preexecution-{scenario}-"
            ) as temporary_name:
                temporary = Path(temporary_name)
                marker = temporary / "repository-code-ran"
                repository, baseline = self.create_preexecution_dependency_repository(
                    temporary,
                    marker,
                )
                test_dependency = (
                    repository / "tests/check_build_bioinformatics_application_panel.py"
                )
                if scenario == "intermediate-parent-alias":
                    outside = temporary / "outside-tests"
                    test_dependency.parent.rename(outside)
                    test_dependency.parent.symlink_to(outside, target_is_directory=True)
                elif scenario == "external-hardlink":
                    outside = temporary / "outside-test.py"
                    test_dependency.rename(outside)
                    os.link(outside, test_dependency)

                completed = self.run_preexecution_dependency_harness(
                    repository,
                    baseline,
                )

                if expected_error is None:
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(marker.read_text(encoding="ascii"), "1")
                else:
                    self.assertFalse(
                        marker.exists(),
                        "unsafe repository dependency executed before validation",
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(
                        "Phase 3 preexecution dependency failed: " + expected_error,
                        completed.stderr,
                    )

    def test_preexecution_runner_isolates_python_startup_and_caller_control(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-preexecution-python-env-"
        ) as temporary_name:
            temporary = Path(temporary_name)
            normal_marker = temporary / "normal-test-path-ran"
            control_marker = temporary / "caller-control-path-ran"
            startup_marker = temporary / "python-startup-hook-ran"
            startup_directory = temporary / "python-startup"
            startup_directory.mkdir()
            (startup_directory / "sitecustomize.py").write_text(
                "from pathlib import Path\n"
                f"marker = Path({str(startup_marker)!r})\n"
                "marker.write_text('ran', encoding='ascii')\n",
                encoding="ascii",
            )
            test_dependency_source = (
                "import os\n"
                "from pathlib import Path\n"
                f"normal = Path({str(normal_marker)!r})\n"
                f"controlled = Path({str(control_marker)!r})\n"
                "if os.environ.get('APPLICATION_PANEL_RESOURCE_PROBE'):\n"
                "    controlled.write_text('ran', encoding='ascii')\n"
                "else:\n"
                "    count = int(normal.read_text(encoding='ascii')) "
                "if normal.exists() else 0\n"
                "    normal.write_text(str(count + 1), encoding='ascii')\n"
            )
            repository, baseline = self.create_preexecution_dependency_repository(
                temporary,
                normal_marker,
                test_dependency_source=test_dependency_source,
            )

            completed = self.run_preexecution_dependency_harness(
                repository,
                baseline,
                environment_overrides={
                    "APPLICATION_PANEL_RESOURCE_PROBE": "caller-controlled",
                    "PYTHONPATH": str(startup_directory),
                },
            )

            normal_count = (
                normal_marker.read_text(encoding="ascii")
                if normal_marker.exists()
                else None
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                (
                    startup_marker.exists(),
                    control_marker.exists(),
                    normal_count,
                ),
                (False, False, "1"),
            )

    def test_preexecution_revalidates_identity_before_child_failure(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-preexecution-child-failure-"
        ) as temporary_name:
            temporary = Path(temporary_name)
            marker = temporary / "unused-normal-marker"
            repository = temporary / "repository"
            builder = (
                repository / "reproduce/bioinformatics/build_application_panel.py"
            )
            parked_builder = temporary / "parked-builder.py"
            test_dependency_source = (
                "import os\n"
                "from pathlib import Path\n"
                f"builder = Path({str(builder)!r})\n"
                f"parked = Path({str(parked_builder)!r})\n"
                "parent = builder.parent\n"
                "parent_metadata = parent.stat()\n"
                "builder.rename(parked)\n"
                "builder.write_text('replacement\\n', encoding='ascii')\n"
                "os.utime(parent, ns=(parent_metadata.st_atime_ns, "
                "parent_metadata.st_mtime_ns))\n"
                "raise SystemExit(23)\n"
            )
            created_repository, baseline = (
                self.create_preexecution_dependency_repository(
                    temporary,
                    marker,
                    test_dependency_source=test_dependency_source,
                )
            )
            self.assertEqual(created_repository, repository)

            completed = self.run_preexecution_dependency_harness(
                repository,
                baseline,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "Phase 3 preexecution dependency failed: dependency identity "
                "changed: reproduce/bioinformatics/build_application_panel.py",
                completed.stderr,
            )
            self.assertNotIn("application builder tests failed", completed.stderr)

    def test_offline_reconstruction_rejects_injected_command_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase3-offline-injected-") as temporary:
            temporary_root = Path(temporary)
            work = temporary_root / "authenticated-run"
            offline = work / "offline-bin"
            offline.mkdir(parents=True)
            fake_marker = temporary_root / "fake-bash-invoked"
            fake_bash = offline / "bash"
            fake_bash.write_text(
                "#!/bin/sh\n"
                'printf "invoked\\n" >"$FAKE_BASH_MARKER"\n'
                "exit 0\n",
                encoding="ascii",
            )
            fake_bash.chmod(0o700)
            environment_marker = os.environ.get("FAKE_BASH_MARKER")
            os.environ["FAKE_BASH_MARKER"] = str(fake_marker)
            try:
                completed = self.run_offline_reconstruction_harness(
                    temporary_root=temporary_root,
                    fetcher=temporary_root / "nonexistent-fetcher.sh",
                )
            finally:
                if environment_marker is None:
                    os.environ.pop("FAKE_BASH_MARKER", None)
                else:
                    os.environ["FAKE_BASH_MARKER"] = environment_marker
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(fake_marker.exists())
            self.assertNotIn("verified_from_complete_cache", completed.stdout)
            self.assertTrue(fake_bash.is_file())

    def test_offline_reconstruction_uses_exact_guard_and_cleans_owned_entries(
        self,
    ) -> None:
        expected_guard = (
            b"#!/bin/sh\n"
            b"printf '%s\\n' 'Phase 3 freeze reconstruction attempted network access' >&2\n"
            b"exit 97\n"
        )
        with tempfile.TemporaryDirectory(prefix="phase3-offline-clean-") as temporary:
            temporary_root = Path(temporary)
            fetch_marker = temporary_root / "fetcher-ran"
            expected_offline = temporary_root / "authenticated-run/offline-bin"
            fake_fetcher = temporary_root / "fake-fetcher.sh"
            fake_fetcher.write_text(
                "#!/bin/bash\n"
                "set -euo pipefail\n"
                'offline="${PATH%%:*}"\n'
                f'[[ "$offline" == {shlex.quote(str(expected_offline))} ]]\n'
                f"{shlex.quote(sys.executable)} - \"$offline/curl\" "
                f"{expected_guard.hex()} <<'PY'\n"
                "import os\n"
                "import stat\n"
                "import sys\n"
                "from pathlib import Path\n"
                "guard = Path(sys.argv[1])\n"
                "expected = bytes.fromhex(sys.argv[2])\n"
                "assert sorted(path.name for path in guard.parent.iterdir()) == ['curl']\n"
                "metadata = os.lstat(guard)\n"
                "assert stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1\n"
                "assert stat.S_IMODE(metadata.st_mode) == 0o500\n"
                "assert guard.read_bytes() == expected\n"
                "PY\n"
                f"printf 'ran\\n' >{shlex.quote(str(fetch_marker))}\n",
                encoding="ascii",
            )
            fake_fetcher.chmod(0o700)
            completed = self.run_offline_reconstruction_harness(
                temporary_root=temporary_root,
                fetcher=fake_fetcher,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(fetch_marker.is_file())
            self.assertFalse(
                (temporary_root / "authenticated-run/offline-bin").exists()
            )

    def test_offline_reconstruction_sanitizes_shell_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase3-offline-shell-env-") as temporary:
            temporary_root = Path(temporary)
            bash_env_marker = temporary_root / "bash-env-sourced"
            function_marker = temporary_root / "exported-curl-function-ran"
            bash_env = temporary_root / "hostile-bash-env.sh"
            bash_env.write_text(
                f"printf 'sourced\\n' >{shlex.quote(str(bash_env_marker))}\n",
                encoding="ascii",
            )
            fake_fetcher = temporary_root / "fake-fetcher.sh"
            fake_fetcher.write_text(
                "#!/bin/bash\n"
                "set -euo pipefail\n"
                "set +e\n"
                'guard_output="$(curl 2>&1)"\n'
                "guard_status=$?\n"
                "set -e\n"
                '[[ "$guard_output" == '
                '"Phase 3 freeze reconstruction attempted network access" ]]\n'
                '[[ "$guard_status" -eq 97 ]]\n',
                encoding="ascii",
            )
            fake_fetcher.chmod(0o700)
            pre_invocation_source = (
                f"BASH_ENV={shlex.quote(str(bash_env))}\n"
                "export BASH_ENV\n"
                "curl() {\n"
                f"  printf 'ran\\n' >{shlex.quote(str(function_marker))}\n"
                "  return 0\n"
                "}\n"
                "export -f curl\n"
            )

            completed = self.run_offline_reconstruction_harness(
                temporary_root=temporary_root,
                fetcher=fake_fetcher,
                pre_invocation_source=pre_invocation_source,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(bash_env_marker.exists())
            self.assertFalse(function_marker.exists())
            self.assertIn(
                "reconstruction_status=verified_from_complete_cache",
                completed.stdout,
            )
            self.assertFalse(
                (temporary_root / "authenticated-run/offline-bin").exists()
            )

    def test_offline_reconstruction_ignores_inherited_path_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="phase3-offline-path-") as temporary:
            temporary_root = Path(temporary)
            untrusted_bin = temporary_root / "untrusted-bin"
            untrusted_bin.mkdir()
            fake_tool_marker = temporary_root / "untrusted-stat-ran"
            fake_stat = untrusted_bin / "stat"
            fake_stat.write_text(
                "#!/bin/sh\n"
                f"printf 'ran\\n' >{shlex.quote(str(fake_tool_marker))}\n"
                "exec /usr/bin/stat \"$@\"\n",
                encoding="ascii",
            )
            fake_stat.chmod(0o700)
            fake_fetcher = temporary_root / "fake-fetcher.sh"
            fake_fetcher.write_text(
                "#!/bin/bash\n"
                "set -euo pipefail\n"
                "stat -c %s -- \"$0\" >/dev/null\n"
                "set +e\n"
                'guard_output="$(curl 2>&1)"\n'
                "guard_status=$?\n"
                "set -e\n"
                '[[ "$guard_output" == '
                '"Phase 3 freeze reconstruction attempted network access" ]]\n'
                '[[ "$guard_status" -eq 97 ]]\n',
                encoding="ascii",
            )
            fake_fetcher.chmod(0o700)
            pre_invocation_source = (
                f"PATH={shlex.quote(str(untrusted_bin))}:$PATH\n"
                "export PATH\n"
            )

            completed = self.run_offline_reconstruction_harness(
                temporary_root=temporary_root,
                fetcher=fake_fetcher,
                pre_invocation_source=pre_invocation_source,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(
                fake_tool_marker.exists(),
                "offline reconstruction selected a command from inherited PATH",
            )
            self.assertIn(
                "reconstruction_status=verified_from_complete_cache",
                completed.stdout,
            )
            self.assertFalse(
                (temporary_root / "authenticated-run/offline-bin").exists()
            )

    def test_offline_reconstruction_retains_named_fetcher_identity(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-offline-fetcher-identity-"
        ) as temporary_name:
            fixture = self.create_retained_reconstruction_repository(
                Path(temporary_name),
                fail_verify=False,
            )
            completed, replacement_marker = (
                self.run_offline_reconstruction_dependency_race(
                    fixture,
                    dependency="fetcher",
                )
            )

            self.assertFalse(
                replacement_marker.exists(),
                "replacement fetcher was consumed",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "dependency identity changed: "
                "reproduce/bioinformatics/fetch_application_inputs.sh",
                completed.stderr,
            )
            self.assertEqual(
                [
                    line.split("\t", 1)[1]
                    for line in fixture["builder_log"]
                    .read_text(encoding="ascii")
                    .splitlines()
                ],
                ["sources", "select", "verify"],
            )

    def test_offline_reconstruction_retains_builder_and_prioritizes_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-offline-builder-identity-"
        ) as temporary_name:
            fixture = self.create_retained_reconstruction_repository(
                Path(temporary_name),
                fail_verify=True,
            )
            completed, replacement_marker = (
                self.run_offline_reconstruction_dependency_race(
                    fixture,
                    dependency="builder",
                )
            )

            self.assertFalse(
                replacement_marker.exists(),
                "replacement builder was consumed",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "dependency identity changed: "
                "reproduce/bioinformatics/build_application_panel.py",
                completed.stderr,
            )
            self.assertNotIn("fetcher exited with status", completed.stderr)
            invocations = [
                line.split("\t", 1)
                for line in fixture["builder_log"]
                .read_text(encoding="ascii")
                .splitlines()
            ]
            self.assertEqual(
                [command for _path, command in invocations],
                ["sources", "select", "verify"],
            )
            self.assertTrue(
                all(path.startswith("/proc/self/fd/") for path, _command in invocations)
            )

    def test_offline_reconstruction_detects_same_inode_builder_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-offline-builder-inplace-"
        ) as temporary_name:
            fixture = self.create_retained_reconstruction_repository(
                Path(temporary_name),
                fail_verify=True,
            )
            initial = os.stat(fixture["builder"])
            completed, replacement_marker = (
                self.run_offline_reconstruction_dependency_race(
                    fixture,
                    dependency="builder-inplace",
                )
            )
            final = os.stat(fixture["builder"])

            self.assertTrue(
                replacement_marker.exists(),
                "same-inode replacement builder was not consumed",
            )
            self.assertEqual(
                (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns),
                (
                    initial.st_dev,
                    initial.st_ino,
                    initial.st_size,
                    initial.st_mtime_ns,
                ),
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "dependency identity changed: "
                "reproduce/bioinformatics/build_application_panel.py",
                completed.stderr,
            )
            self.assertNotIn("fetcher exited with status", completed.stderr)

    def test_direct_fetcher_keeps_named_builder_for_multiple_subcommands(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-direct-fetcher-builder-"
        ) as temporary_name:
            fixture = self.create_retained_reconstruction_repository(
                Path(temporary_name),
                fail_verify=False,
            )
            completed = subprocess.run(
                ["/usr/bin/bash", str(fixture["fetcher"])],
                cwd=fixture["repository"],
                env={
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin",
                    "TMPDIR": str(fixture["temporary_directory"]),
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            invocations = [
                line.split("\t", 1)
                for line in fixture["builder_log"]
                .read_text(encoding="ascii")
                .splitlines()
            ]
            self.assertEqual(
                [command for _path, command in invocations],
                ["sources", "select", "verify"],
            )
            self.assertEqual(
                {path for path, _command in invocations},
                {str(fixture["builder"])},
            )

    def test_source_cache_preflight_rejects_unsafe_layouts_before_dependencies(
        self,
    ) -> None:
        def cache_directory(repository: Path) -> Path:
            cache = repository / ".tmp/bioinformatics_application_sources"
            cache.mkdir(parents=True)
            return cache

        def extra_entry(repository: Path, _temporary: Path) -> None:
            (cache_directory(repository) / "unexpected.gz").write_bytes(b"extra")

        def partial_set(repository: Path, _temporary: Path) -> None:
            cache = cache_directory(repository)
            (cache / self.SOURCE_ARCHIVE_NAMES[0]).write_bytes(b"partial")

        def symlinked_cache(repository: Path, temporary: Path) -> None:
            temporary_parent = repository / ".tmp"
            temporary_parent.mkdir()
            outside = temporary / "outside-cache"
            outside.mkdir()
            (temporary_parent / "bioinformatics_application_sources").symlink_to(
                outside,
                target_is_directory=True,
            )

        def symlinked_temporary_parent(repository: Path, temporary: Path) -> None:
            outside = temporary / "outside-temporary-parent"
            outside.mkdir()
            (repository / ".tmp").symlink_to(outside, target_is_directory=True)

        def hardlinked_archive(repository: Path, temporary: Path) -> None:
            cache = cache_directory(repository)
            external = temporary / "external-archive.gz"
            external.write_bytes(b"hardlinked")
            os.link(external, cache / self.SOURCE_ARCHIVE_NAMES[0])
            for name in self.SOURCE_ARCHIVE_NAMES[1:]:
                (cache / name).write_bytes(name.encode("ascii"))

        def special_archive(repository: Path, _temporary: Path) -> None:
            cache = cache_directory(repository)
            os.mkfifo(cache / self.SOURCE_ARCHIVE_NAMES[0])
            for name in self.SOURCE_ARCHIVE_NAMES[1:]:
                (cache / name).write_bytes(name.encode("ascii"))

        scenarios = (
            ("extra", extra_entry, "unexpected Phase 3 source-cache entry"),
            ("partial", partial_set, "zero or exactly four canonical archives"),
            ("cache-symlink", symlinked_cache, "unsafe Phase 3 source-cache directory"),
            ("tmp-symlink", symlinked_temporary_parent, "unsafe Phase 3 source-cache parent"),
            ("hardlink", hardlinked_archive, "source-cache archive has a hardlink alias"),
            ("special", special_archive, "source-cache entry is not a regular file"),
        )
        for label, configure, expected_error in scenarios:
            with self.subTest(layout=label):
                completed = self.run_checker_cache_preflight(configure)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_error, completed.stderr)

    def test_source_cache_binding_receipt_is_structural_and_stable(self) -> None:
        for expected_count in (0, 4):
            with self.subTest(source_count=expected_count), tempfile.TemporaryDirectory(
                prefix="phase3-cache-binding-stable-"
            ) as temporary:
                repository = Path(temporary) / "repository"
                repository.mkdir()
                cache = self.create_source_cache(
                    repository,
                    complete=expected_count == 4,
                )
                first = self.run_source_cache_binding_harness(repository)
                second = self.run_source_cache_binding_harness(repository)
                self.assertEqual(first.returncode, 0, first.stderr)
                self.assertEqual(second.returncode, 0, second.stderr)
                self.assertEqual(first.stdout, second.stdout)
                receipt = json.loads(first.stdout)
                self.assertIsInstance(receipt, dict)
                self.assertEqual(
                    set(receipt),
                    {"archives", "cache", "count", "schema_version", "temporary"},
                )
                self.assertEqual(receipt["schema_version"], 1)
                self.assertEqual(receipt["count"], expected_count)
                temporary_metadata = os.lstat(repository / ".tmp")
                cache_metadata = os.lstat(cache)
                self.assertEqual(
                    receipt["temporary"],
                    {
                        "device": temporary_metadata.st_dev,
                        "inode": temporary_metadata.st_ino,
                        "present": True,
                    },
                )
                self.assertEqual(
                    receipt["cache"],
                    {
                        "device": cache_metadata.st_dev,
                        "inode": cache_metadata.st_ino,
                        "present": True,
                    },
                )
                self.assertEqual(len(receipt["archives"]), expected_count)
                for archive, name in zip(
                    receipt["archives"],
                    self.SOURCE_ARCHIVE_NAMES if expected_count == 4 else (),
                    strict=True,
                ):
                    metadata = os.lstat(cache / name)
                    self.assertEqual(
                        archive,
                        {
                            "device": metadata.st_dev,
                            "inode": metadata.st_ino,
                            "mode": metadata.st_mode,
                            "mtime_ns": metadata.st_mtime_ns,
                            "name": name,
                            "nlink": metadata.st_nlink,
                            "size": metadata.st_size,
                            "type": "regular",
                        },
                    )
                self.assertNotIn("atime", first.stdout.lower())
                rechecked = self.run_source_cache_binding_harness(
                    repository,
                    expected_binding=first.stdout.strip(),
                )
                self.assertEqual(rechecked.returncode, 0, rechecked.stderr)

    def test_source_cache_binding_recheck_rejects_structural_drift(self) -> None:
        def add_partial(repository: Path, cache: Path, temporary: Path) -> None:
            del repository, temporary
            (cache / self.SOURCE_ARCHIVE_NAMES[0]).write_bytes(b"partial\n")

        def replace_empty_cache(
            repository: Path,
            cache: Path,
            temporary: Path,
        ) -> None:
            del repository
            cache.rename(temporary / "parked-empty-cache")
            cache.mkdir()

        def add_extra(repository: Path, cache: Path, temporary: Path) -> None:
            del repository, temporary
            (cache / "unexpected.gz").write_bytes(b"extra\n")

        def replace_archive(
            repository: Path,
            cache: Path,
            temporary: Path,
        ) -> None:
            del repository
            archive = cache / self.SOURCE_ARCHIVE_NAMES[0]
            metadata = os.lstat(archive)
            contents = archive.read_bytes()
            archive.rename(temporary / "parked-canonical-archive.gz")
            archive.write_bytes(contents)
            archive.chmod(stat.S_IMODE(metadata.st_mode))
            os.utime(
                archive,
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
                follow_symlinks=False,
            )
            replacement = os.lstat(archive)
            self.assertNotEqual(replacement.st_ino, metadata.st_ino)
            self.assertEqual(replacement.st_mode, metadata.st_mode)
            self.assertEqual(replacement.st_size, metadata.st_size)
            self.assertEqual(replacement.st_mtime_ns, metadata.st_mtime_ns)

        scenarios = (
            ("empty-add-partial", False, add_partial),
            ("empty-replace-cache", False, replace_empty_cache),
            ("complete-add-extra", True, add_extra),
            ("complete-replace-archive", True, replace_archive),
        )
        for label, complete, mutate in scenarios:
            with self.subTest(mutation=label), tempfile.TemporaryDirectory(
                prefix=f"phase3-cache-binding-{label}-"
            ) as temporary_name:
                temporary = Path(temporary_name)
                repository = temporary / "repository"
                repository.mkdir()
                cache = self.create_source_cache(repository, complete=complete)
                captured = self.run_source_cache_binding_harness(repository)
                self.assertEqual(captured.returncode, 0, captured.stderr)
                mutate(repository, cache, temporary)
                rechecked = self.run_source_cache_binding_harness(
                    repository,
                    expected_binding=captured.stdout.strip(),
                )
                self.assertNotEqual(rechecked.returncode, 0)
                self.assertIn(
                    "Bioinformatics Phase 3 cache binding changed",
                    rechecked.stderr,
                )

    def semantic_validator_source(self) -> str:
        checker = CHECKER.read_text(encoding="utf-8", errors="strict")
        marker = 'python3 - "$ROOT" "$BASELINE" <<\'PY\'\n'
        self.assertEqual(checker.count(marker), 1)
        start = checker.index(marker) + len(marker)
        end = checker.index("\nPY\n", start)
        return checker[start:end]

    def application_snapshot_source(self) -> str:
        checker = CHECKER.read_text(encoding="utf-8", errors="strict")
        function_marker = "write_application_snapshot() {\n"
        self.assertEqual(checker.count(function_marker), 1)
        function = checker.split(function_marker, 1)[1]
        heredoc_marker = "<<'PY'\n"
        self.assertEqual(function.count(heredoc_marker), 1)
        start = function.index(heredoc_marker) + len(heredoc_marker)
        end = function.index("\nPY\n}", start)
        return function[start:end]

    def create_application_snapshot_repository(self, temporary: Path) -> Path:
        repository = temporary / "repository"
        frozen_files = (
            "Makefile",
            "goal-bioinformatics.md",
            "docs/superpowers/plans/"
            "2026-07-24-bioinformatics-phase3-application-freeze.md",
            "docs/superpowers/specs/"
            "2026-07-24-bioinformatics-phase3-application-design.md",
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
        for relative in frozen_files:
            path = repository / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{relative}\n", encoding="ascii")

        application_inputs = (
            repository / "reproduce/bioinformatics/application_inputs"
        )
        for relative in ("queries/aq001.fa", "targets/at0001.fa"):
            path = application_inputs / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f">{path.stem}\nACGT\n", encoding="ascii")

        git_sentinel = repository / ".git/HEAD"
        git_sentinel.parent.mkdir()
        git_sentinel.write_text("ref: refs/heads/fixture\n", encoding="ascii")
        cache_sentinel = (
            repository
            / ".tmp/bioinformatics_application_sources/ignored-source.fa.gz"
        )
        cache_sentinel.parent.mkdir(parents=True)
        cache_sentinel.write_bytes(b"ignored source cache\n")
        work_sentinel = (
            repository
            / ".tmp/check_bioinformatics_phase3_freeze/ignored-work-entry"
        )
        work_sentinel.parent.mkdir(parents=True)
        work_sentinel.write_text("ignored work\n", encoding="ascii")
        return repository

    def run_application_snapshot(
        self,
        repository: Path,
        work: Path,
        *,
        destination_name: str,
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        work.mkdir(mode=0o700)
        work.chmod(0o700)
        work_metadata = os.lstat(work)
        destination = work / destination_name
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                self.application_snapshot_source(),
                str(repository),
                str(destination),
                str(work),
                str(work_metadata.st_dev),
                str(work_metadata.st_ino),
            ],
            cwd=repository,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        return completed, destination

    def create_semantic_validator_repository(self, temporary: Path) -> Path:
        repository = temporary / "repository"
        shutil.copytree(
            ROOT / "paper/bioinformatics",
            repository / "paper/bioinformatics",
        )
        application_parent = repository / "reproduce/bioinformatics"
        application_parent.mkdir(parents=True)
        shutil.copytree(
            ROOT / "reproduce/bioinformatics/application_inputs",
            application_parent / "application_inputs",
        )
        return repository

    def run_semantic_validator(
        self,
        repository: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-c",
                self.semantic_validator_source(),
                str(repository),
                "bf94dc75c5fe3e996472a1e90d242f582da361bf",
            ],
            cwd=repository,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )

    def test_semantic_validator_rejects_intermediate_symlink_parent(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-semantic-parent-symlink-"
        ) as temporary_name:
            temporary = Path(temporary_name)
            repository = self.create_semantic_validator_repository(temporary)
            paper_directory = repository / "paper/bioinformatics"
            outside = temporary / "outside-bioinformatics"
            shutil.copytree(paper_directory, outside)
            paper_directory.rename(temporary / "parked-bioinformatics")
            paper_directory.symlink_to(outside, target_is_directory=True)
            completed = self.run_semantic_validator(repository)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("no-follow repository path failed", completed.stderr)
            self.assertNotIn("CalledProcessError", completed.stderr)

    def test_snapshot_rejects_directory_swap_during_retained_file_hash(
        self,
    ) -> None:
        if not Path("/proc/self/fd").is_dir():
            self.skipTest("snapshot descriptor observation requires /proc")
        with tempfile.TemporaryDirectory(
            prefix="phase3-snapshot-directory-swap-"
        ) as temporary_name:
            temporary = Path(temporary_name)
            repository = temporary / "repository"
            metadata_paths = (
                "application_input_summary.tsv",
                "application_manifest.sha256",
                "application_manifest.tsv",
                "application_protocol.md",
                "application_selection.json",
                "application_sources.tsv",
            )
            paper = repository / "paper/bioinformatics"
            paper.mkdir(parents=True)
            for name in metadata_paths:
                (paper / name).write_text(f"{name}\n", encoding="ascii")
            inputs = repository / "reproduce/bioinformatics/application_inputs"
            queries = inputs / "queries"
            targets = inputs / "targets"
            queries.mkdir(parents=True)
            targets.mkdir()
            slow = queries / "slow.fa"
            with slow.open("wb") as handle:
                handle.truncate(512 * 1024 * 1024)
            (targets / "original.fa").write_text("original\n", encoding="ascii")

            work = temporary / "authenticated-run"
            work.mkdir(mode=0o700)
            work.chmod(0o700)
            work_metadata = os.lstat(work)
            destination = work / "application-freeze.before.json"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    self.application_snapshot_source(),
                    str(repository),
                    str(destination),
                    str(work),
                    str(work_metadata.st_dev),
                    str(work_metadata.st_ino),
                ],
                cwd=temporary,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                descriptor_root = Path(f"/proc/{process.pid}/fd")
                deadline = time.monotonic() + 10
                observed = False
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        descriptors = list(descriptor_root.iterdir())
                    except FileNotFoundError:
                        break
                    for descriptor in descriptors:
                        try:
                            target = os.readlink(descriptor)
                        except OSError:
                            continue
                        if target == str(slow):
                            observed = True
                            break
                    if observed:
                        break
                    time.sleep(0.001)
                self.assertTrue(observed, "did not observe retained slow.fa descriptor")

                targets.rename(temporary / "parked-targets")
                targets.mkdir()
                (targets / "replacement.fa").write_text(
                    "replacement\n",
                    encoding="ascii",
                )
                stdout, stderr = process.communicate(timeout=30)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
            self.assertNotEqual(process.returncode, 0, stdout)
            self.assertIn("frozen directory child identity changed", stderr)
            self.assertFalse(destination.exists())

    def test_snapshot_covers_complete_checkpoint_dependencies_and_is_stable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="phase3-snapshot-completeness-"
        ) as temporary_name:
            temporary = Path(temporary_name)
            repository = self.create_application_snapshot_repository(temporary)

            first, first_path = self.run_application_snapshot(
                repository,
                temporary / "work-first",
                destination_name="application-freeze.before.json",
            )
            second, second_path = self.run_application_snapshot(
                repository,
                temporary / "work-second",
                destination_name="application-freeze.after.json",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            first_bytes = first_path.read_bytes()
            second_bytes = second_path.read_bytes()
            self.assertEqual(first_bytes, second_bytes)

            evidence = repository / "paper/bioinformatics/claim_evidence.tsv"
            evidence.write_text("changed evidence\n", encoding="ascii")
            evidence_run, evidence_path = self.run_application_snapshot(
                repository,
                temporary / "work-evidence",
                destination_name="application-freeze.after.json",
            )
            self.assertEqual(evidence_run.returncode, 0, evidence_run.stderr)
            evidence_bytes = evidence_path.read_bytes()
            with self.subTest(dependency="formerly-omitted-evidence"):
                self.assertNotEqual(second_bytes, evidence_bytes)

            builder = (
                repository / "reproduce/bioinformatics/build_application_panel.py"
            )
            builder.write_text("changed builder\n", encoding="ascii")
            code_run, code_path = self.run_application_snapshot(
                repository,
                temporary / "work-code",
                destination_name="application-freeze.after.json",
            )
            self.assertEqual(code_run.returncode, 0, code_run.stderr)
            code_bytes = code_path.read_bytes()
            with self.subTest(dependency="formerly-omitted-code"):
                self.assertNotEqual(evidence_bytes, code_bytes)

            expected_files = {
                "Makefile",
                "goal-bioinformatics.md",
                "docs/superpowers/plans/"
                "2026-07-24-bioinformatics-phase3-application-freeze.md",
                "docs/superpowers/specs/"
                "2026-07-24-bioinformatics-phase3-application-design.md",
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
                "reproduce/bioinformatics/application_inputs/queries/aq001.fa",
                "reproduce/bioinformatics/application_inputs/targets/at0001.fa",
            }
            snapshot_paths = {
                entry["path"] for entry in json.loads(code_bytes.decode("ascii"))
            }
            with self.subTest(dependency="complete-path-set"):
                self.assertTrue(expected_files <= snapshot_paths)
            self.assertFalse(
                any(
                    path == ".git"
                    or path.startswith(".git/")
                    or path == ".tmp/bioinformatics_application_sources"
                    or path.startswith(
                        ".tmp/bioinformatics_application_sources/"
                    )
                    or path == ".tmp/check_bioinformatics_phase3_freeze"
                    or path.startswith(
                        ".tmp/check_bioinformatics_phase3_freeze/"
                    )
                    for path in snapshot_paths
                )
            )

    def test_semantic_validator_binds_complete_phase3_receipts(self) -> None:
        def mutate_selection(
            repository: Path,
            update: object,
            *,
            indent: int = 2,
        ) -> None:
            path = repository / "paper/bioinformatics/application_selection.json"
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                selection = json.load(handle)
            update(selection)
            with path.open("w", encoding="utf-8", errors="strict") as handle:
                json.dump(selection, handle, ensure_ascii=True, indent=indent, sort_keys=True)
                handle.write("\n")

        def query_rule(repository: Path) -> None:
            mutate_selection(
                repository,
                lambda selection: selection.__setitem__(
                    "query_selection_rule",
                    "coherently mutated query selection rule",
                ),
            )

        def target_rule(repository: Path) -> None:
            mutate_selection(
                repository,
                lambda selection: selection.__setitem__(
                    "target_selection_rule",
                    "coherently mutated target selection rule",
                ),
            )

        def representative_query_count(repository: Path) -> None:
            def update(selection: dict[str, object]) -> None:
                counts = selection["query_counts"]
                assert isinstance(counts, dict)
                counts["representative_query_count"] = 27126

            mutate_selection(repository, update)

        def chromosome_target_counts(repository: Path) -> None:
            def update(selection: dict[str, object]) -> None:
                counts = selection["target_counts"]
                assert isinstance(counts, dict)
                counts["chr21_retained_target_count"] = 220
                counts["chr21_excluded_target_count"] = 1

            mutate_selection(repository, update)

        def duplicate_nested_json_key(repository: Path) -> None:
            path = repository / "paper/bioinformatics/application_selection.json"
            original = path.read_bytes()
            marker = b'  "query_counts": {\n'
            self.assertEqual(original.count(marker), 1)
            mutated = original.replace(
                marker,
                marker + b'    "representative_query_count": -1,\n',
                1,
            )
            path.write_bytes(mutated)

        def appended_phase9_application_row(repository: Path) -> None:
            path = repository / "paper/bioinformatics/submission_manifest.tsv"
            fields = (
                "artifact_id",
                "path",
                "phase",
                "artifact_class",
                "authority",
                "freeze_or_epoch",
                "required",
                "status",
            )
            with path.open(
                "a",
                encoding="utf-8",
                errors="strict",
                newline="",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fields,
                    delimiter="\t",
                    lineterminator="\n",
                )
                writer.writerow(
                    {
                        "artifact_id": "S0901",
                        "path": "paper/bioinformatics/application_results.tsv",
                        "phase": "9",
                        "artifact_class": "source_data",
                        "authority": "candidate_only_output",
                        "freeze_or_epoch": "postfreeze",
                        "required": "0",
                        "status": "pass",
                    }
                )

        def candidate_only_protocol_contradiction(repository: Path) -> None:
            path = repository / "paper/bioinformatics/application_protocol.md"
            with path.open("a", encoding="utf-8", errors="strict") as handle:
                handle.write(
                    "\nCandidate-only B speedup establishes the B3 biological "
                    "superiority claim.\n"
                )

        scenarios = (
            ("query-rule", query_rule, "selection query rule drifted"),
            ("target-rule", target_rule, "selection target rule drifted"),
            (
                "representative-query-count",
                representative_query_count,
                "selection query counts drifted",
            ),
            (
                "chromosome-target-counts",
                chromosome_target_counts,
                "selection target counts drifted",
            ),
            (
                "duplicate-nested-json-key",
                duplicate_nested_json_key,
                "application selection contains duplicate JSON key",
            ),
            (
                "phase9-application-row",
                appended_phase9_application_row,
                "submission manifest contains application row outside Phase 3 suffix",
            ),
            (
                "candidate-only-protocol-contradiction",
                candidate_only_protocol_contradiction,
                "application protocol checksum drift",
            ),
        )
        for label, mutate, expected_error in scenarios:
            with self.subTest(receipt_mutation=label), tempfile.TemporaryDirectory(
                prefix=f"phase3-semantic-{label}-"
            ) as temporary_name:
                repository = self.create_semantic_validator_repository(
                    Path(temporary_name)
                )
                mutate(repository)
                completed = self.run_semantic_validator(repository)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_error, completed.stderr)

    def test_semantic_validator_binds_entire_readme_bytes(self) -> None:
        def add_contradictory_execution_flag(repository: Path) -> None:
            path = repository / "paper/bioinformatics/README.md"
            readme = path.read_text(encoding="utf-8", errors="strict")
            marker = "application_execution_started = 0\n"
            self.assertEqual(readme.count(marker), 1)
            path.write_text(
                readme.replace(
                    marker,
                    marker + "application_execution_started = 1\n",
                    1,
                ),
                encoding="utf-8",
                errors="strict",
            )

        def append_completed_results_section(repository: Path) -> None:
            path = repository / "paper/bioinformatics/README.md"
            with path.open("a", encoding="utf-8", errors="strict") as handle:
                handle.write(
                    "\n## Phase 3 execution completed results\n\n"
                    "application_execution_started = 1\n"
                    "record_status = completed\n"
                    "results = published\n"
                )

        scenarios = (
            ("contradictory-execution-flag", add_contradictory_execution_flag),
            ("appended-completed-results", append_completed_results_section),
        )
        for label, mutate in scenarios:
            with self.subTest(readme_mutation=label), tempfile.TemporaryDirectory(
                prefix=f"phase3-readme-{label}-"
            ) as temporary_name:
                repository = self.create_semantic_validator_repository(
                    Path(temporary_name)
                )
                mutate(repository)
                completed = self.run_semantic_validator(repository)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("README checksum drift", completed.stderr)

    def test_source_ledger_provenance_fields_are_exact_authority_bound(self) -> None:
        validator = self.semantic_validator_source()
        for field in (
            "license_or_terms",
            "redistribution_note",
            "download_command",
        ):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory(
                    prefix=f"phase3-source-{field}-"
                ) as temporary:
                    repository = Path(temporary) / "repository"
                    shutil.copytree(
                        ROOT / "paper/bioinformatics",
                        repository / "paper/bioinformatics",
                    )
                    application_parent = repository / "reproduce/bioinformatics"
                    application_parent.mkdir(parents=True)
                    shutil.copytree(
                        ROOT / "reproduce/bioinformatics/application_inputs",
                        application_parent / "application_inputs",
                    )
                    ledger = repository / "paper/bioinformatics/application_sources.tsv"
                    with ledger.open(
                        "r",
                        encoding="utf-8",
                        errors="strict",
                        newline="",
                    ) as handle:
                        reader = csv.DictReader(handle, delimiter="\t")
                        fieldnames = reader.fieldnames
                        rows = list(reader)
                    self.assertIsNotNone(fieldnames)
                    self.assertIn(field, fieldnames or ())
                    rows[0][field] = f"coherently-mutated-{field}"
                    with ledger.open(
                        "w",
                        encoding="utf-8",
                        errors="strict",
                        newline="",
                    ) as handle:
                        writer = csv.DictWriter(
                            handle,
                            fieldnames=fieldnames,
                            delimiter="\t",
                            lineterminator="\n",
                        )
                        writer.writeheader()
                        writer.writerows(rows)
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            validator,
                            str(repository),
                            "bf94dc75c5fe3e996472a1e90d242f582da361bf",
                        ],
                        cwd=repository,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=30,
                        check=False,
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(
                        f"source authority drifted: gencode_v49_lncrna {field}",
                        completed.stderr,
                    )

    def test_phase3_freeze_has_no_execution_artifacts(self) -> None:
        forbidden = (
            ROOT / "reproduce/bioinformatics/run_application.py",
            ROOT / "reproduce/bioinformatics/application_backend.py",
            ROOT / "reproduce/bioinformatics/application_raw",
            ROOT / "reproduce/bioinformatics/application_outputs",
            ROOT / "paper/bioinformatics/source_data",
            ROOT / "paper/bioinformatics/application_attempt_results.tsv",
            ROOT / "paper/bioinformatics/application_workload_results.tsv",
            ROOT / "paper/bioinformatics/application_rank_results.tsv",
            ROOT / "paper/bioinformatics/application_mode_results.tsv",
            ROOT / "paper/bioinformatics/application_raw_artifacts.tsv",
            ROOT / "paper/bioinformatics/application_results.tsv",
            ROOT / "paper/bioinformatics/application_summary.json",
            ROOT / "paper/bioinformatics/application_retry_ledger.tsv",
            ROOT / "paper/bioinformatics/application_exclusion_ledger.tsv",
            ROOT / "paper/bioinformatics/phase3_decision.md",
        )
        self.assertEqual([path for path in forbidden if path.exists()], [])
        self.assertEqual(
            list((ROOT / ".paper-artifacts").glob("bioinformatics-phase3-*")),
            [],
        )
        rows = read_manifest()
        self.assertEqual(len(rows), 718)
        self.assertTrue(
            all(row["status"] == "preregistered_not_run" for row in rows)
        )

    def test_make_target_invokes_exact_offline_freeze_checker(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8", errors="strict")
        expected = (
            "check-bioinformatics-phase3-freeze: SHELL := /bin/sh\n"
            "check-bioinformatics-phase3-freeze:\n"
            "\t/usr/bin/env -i \\\n"
            "\t\tLC_ALL=C \\\n"
            "\t\tPATH=/usr/bin:/bin \\\n"
            "\t\tPHASE3_FREEZE_CLEAN_BOOTSTRAP=phase3-freeze-v1 \\\n"
            "\t\tWORK=\"$${WORK:-$(CURDIR)/.tmp/"
            "check_bioinformatics_phase3_freeze}\" \\\n"
            "\t\t/usr/bin/bash --noprofile --norc \\\n"
            "\t\t./scripts/check_bioinformatics_phase3_freeze.sh\n"
        )
        self.assertIn(expected, makefile)
        phony_lines = "\n".join(
            line.strip(" \\")
            for line in makefile.splitlines()
            if "check-bioinformatics" in line
        )
        self.assertIn("check-bioinformatics-phase3-freeze", phony_lines)

    def test_submission_manifest_has_exact_phase3_freeze_rows(self) -> None:
        rows = read_tsv(ROOT / "paper/bioinformatics/submission_manifest.tsv")
        phase3 = [row for row in rows if row["artifact_id"].startswith("S03")]
        expected = (
            (
                "S0301",
                "paper/bioinformatics/application_selection.json",
                "application_selection",
                "build_application_panel.py",
            ),
            (
                "S0302",
                "paper/bioinformatics/application_manifest.tsv",
                "application_manifest",
                "application_protocol.md",
            ),
            (
                "S0303",
                "paper/bioinformatics/application_manifest.sha256",
                "application_manifest_checksum",
                "application_manifest.tsv",
            ),
            (
                "S0304",
                "paper/bioinformatics/application_sources.tsv",
                "application_source_ledger",
                "provider_checksums_and_local_sha256",
            ),
            (
                "S0305",
                "paper/bioinformatics/application_protocol.md",
                "application_protocol",
                "goal-bioinformatics.md",
            ),
            (
                "S0306",
                "paper/bioinformatics/application_input_summary.tsv",
                "application_input_summary",
                "application_manifest.tsv",
            ),
            (
                "S0307",
                "reproduce/bioinformatics/build_application_panel.py",
                "application_builder",
                "application_protocol.md",
            ),
            (
                "S0308",
                "reproduce/bioinformatics/fetch_application_inputs.sh",
                "application_fetcher",
                "application_sources.tsv",
            ),
            (
                "S0309",
                "tests/check_build_bioinformatics_application_panel.py",
                "application_builder_tests",
                "goal-bioinformatics.md",
            ),
            (
                "S0310",
                "scripts/check_bioinformatics_phase3_freeze.sh",
                "preexecution_phase_gate",
                "goal-bioinformatics.md",
            ),
        )
        self.assertEqual(
            [
                (
                    row["artifact_id"],
                    row["path"],
                    row["artifact_class"],
                    row["authority"],
                )
                for row in phase3
            ],
            list(expected),
        )
        self.assertTrue(
            all(
                row["phase"] == "3"
                and row["freeze_or_epoch"] == self.FREEZE_ID
                and row["required"] == "1"
                and row["status"] == "pass"
                for row in phase3
            )
        )

    def test_readme_records_exact_pending_nonexecution_receipt(self) -> None:
        readme = (ROOT / "paper/bioinformatics/README.md").read_text(
            encoding="utf-8", errors="strict"
        )
        marker = "## Phase 3 input freeze receipt\n"
        self.assertIn(marker, readme)
        section = readme.split(marker, 1)[1].split("\n## ", 1)[0]
        for line in (
            f"freeze_id = {self.FREEZE_ID}",
            f"manifest_sha256 = {self.MANIFEST_SHA256}",
            "query_count = 50",
            "target_count = 668",
            "pair_count = 33400",
            "query_total_nt = 56381",
            "target_total_bp = 1670668",
            "chr21_target_count = 221",
            "chr22_target_count = 447",
            "fasta_file_count = 718",
            "record_status = preregistered_not_run",
            "application_execution_started = 0",
            "Phase 3 and claim B3 remain pending.",
        ):
            self.assertIn(line, section)
        self.assertNotRegex(
            section.lower(),
            r"\b(?:completed|decision|results?|speedup|no_go)\b",
        )

    def test_freeze_checker_exists_and_embodies_offline_boundaries(self) -> None:
        checker = CHECKER
        self.assertTrue(checker.is_file(), f"Phase 3 freeze checker is missing: {checker}")
        self.assertTrue(os.access(checker, os.X_OK), "Phase 3 freeze checker is not executable")
        text = checker.read_text(encoding="utf-8", errors="strict")
        for required in (
            "PHASE3_AUTHENTICATED_TEST",
            "compile_python_dependency",
            '[bash_path, "-n", retained_path(dependency)]',
            "python3 -m json.tool",
            'git -C "$ROOT" diff --check',
            'git -C "$ROOT" diff --cached --check',
            "bf94dc75c5fe3e996472a1e90d242f582da361bf",
            ".paper-artifacts/bioinformatics-phase3-",
            "cached_source_count",
            "fetch_application_inputs.sh",
            "run_application.py",
            "application_backend",
            "application_execution_started=0",
        ):
            self.assertIn(required, text)
        for forbidden in (
            "--create-freeze",
            "check_bioinformatics_phase2_preexecution",
        ):
            self.assertNotIn(forbidden, text)
        self.assertNotRegex(
            text,
            r"(?m)^\s*(?:exec\s+|env\s+)?(?:python3|bash|sh|make)\b[^\n]*"
            r"(?:run_application\.py|application_backend|gasal2_longtarget\.py|"
            r"Fasim-LongTarget|fasim_longtarget|GASAL2)",
        )

    def test_freeze_checker_declares_full_independent_validation_contract(self) -> None:
        text = CHECKER.read_text(encoding="utf-8", errors="strict")
        for required in (
            "MANIFEST_FIELDS = (",
            "SOURCE_AUTHORITIES = (",
            "expected 718 manifest records",
            "pair_count == 33400 and pair_count >= 15000",
            'chromosome_counts == {"chr21": 221, "chr22": 447}',
            "query sequence digests are not unique",
            "duplicate target digest does not share exact coordinates",
            "application query overlaps development identities",
            "application query overlaps Phase 2 holdout identities",
            'row["status"] == "preregistered_not_run"',
            "claim B3 is not pending",
            "allowed_checkpoint_path",
            "Phase 2 or core runtime path changed from bf94dc7",
        ):
            self.assertIn(required, text)

    def test_freeze_checker_snapshots_and_reconstructs_without_network(self) -> None:
        text = CHECKER.read_text(encoding="utf-8", errors="strict")
        for required in (
            "os.lstat",
            "metadata.st_nlink == 1",
            "application-freeze.before.json",
            "application-freeze.after.json",
            'cmp -- "$before_snapshot" "$after_snapshot"',
            "stream_cached_sources",
            'offline_bin="$WORK/offline-bin"',
            "TRUSTED_BASH_DEVICE",
            "TRUSTED_BASH_INODE",
            "os.O_CREAT",
            "os.O_EXCL",
            "os.O_NOFOLLOW",
            "[bash_path, retained_path(by_relative[fetcher_relative])]",
            "pass_fds=inherited_fds",
            'reconstruction_status="skipped_incomplete_cache"',
        ):
            self.assertIn(required, text)
        self.assertNotIn('PATH="$offline_bin:$PATH" bash "$FETCHER"', text)


class ApplicationPanelBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not BUILDER.is_file():
            raise AssertionError(f"application builder is missing: {BUILDER}")
        loader = importlib.machinery.SourceFileLoader(
            "build_application_panel",
            str(BUILDER),
        )
        spec = importlib.util.spec_from_loader("build_application_panel", loader)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load application builder")
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        try:
            spec.loader.exec_module(cls.module)
        except Exception:
            sys.modules.pop(spec.name, None)
            raise

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="bioinformatics-application-builder-")
        self.work = Path(self.temp.name)
        self.chromosome_sequence = "ACGT" * 7500
        self.plus_transcript = self.target_transcript(
            transcript_id="ENST_PLUS.1",
            gene_id="ENSG_PLUS.1",
            start=10000,
            end=11000,
            strand="+",
        )
        self.minus_transcript = self.target_transcript(
            transcript_id="ENST_MINUS.1",
            gene_id="ENSG_MINUS.1",
            start=9000,
            end=10000,
            strand="-",
        )
        self.near_start_transcript = self.target_transcript(
            transcript_id="ENST_NEAR_START.1",
            gene_id="ENSG_NEAR_START.1",
            start=100,
            end=900,
            strand="+",
        )
        self.near_end_transcript = self.target_transcript(
            transcript_id="ENST_NEAR_END.1",
            gene_id="ENSG_NEAR_END.1",
            start=29000,
            end=29900,
            strand="-",
        )
        priority_specs = (
            ("ENST_MANE.1", frozenset({"MANE_Select"}), 3, 101),
            ("ENST_CANONICAL.1", frozenset({"Ensembl_canonical"}), 1, 3001),
            ("ENST_APPRIS_1.1", frozenset({"appris_principal_1"}), 1, 3001),
            ("ENST_APPRIS_2.1", frozenset({"appris_principal_2"}), 1, 3001),
            ("ENST_BASIC.1", frozenset({"basic"}), 1, 3001),
            ("ENST_LEVEL_1.1", frozenset(), 1, 101),
            ("ENST_LONG.1", frozenset(), 2, 2001),
            ("ENST_ID_A.2", frozenset(), 2, 1001),
            ("ENST_ID_Z.1", frozenset(), 2, 1001),
        )
        self.same_target_gene = [
            self.target_transcript(
                transcript_id=transcript_id,
                gene_id="ENSG_PRIORITY.7",
                start=10000,
                end=10000 + span - 1,
                tags=tags,
                level=level,
            )
            for transcript_id, tags, level, span in reversed(priority_specs)
        ]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_text(self, name: str, text: str) -> Path:
        path = self.work / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_bytes(self, name: str, content: bytes) -> Path:
        path = self.work / name
        path.write_bytes(content)
        return path

    def write_gzip(self, name: str, text: str) -> Path:
        path = self.work / name
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def write_tsv(
        self,
        name: str,
        fieldnames: tuple[str, ...],
        rows: list[dict[str, str]],
    ) -> Path:
        path = self.work / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def prepare_fetch_harness(
        self,
        *,
        committed_outputs: bool,
        valid_cache: bool,
    ) -> dict[str, object]:
        self.assertTrue(FETCHER.is_file(), f"application fetcher is missing: {FETCHER}")
        repository = Path(
            tempfile.mkdtemp(
                prefix=f"fetch-{int(committed_outputs)}-{int(valid_cache)}-",
                dir=self.work,
            )
        )
        script_directory = repository / "reproduce/bioinformatics"
        paper_directory = repository / "paper/bioinformatics"
        source_directory = repository / ".tmp/bioinformatics_application_sources"
        download_directory = repository / "download-fixtures"
        temporary_directory = repository / "temporary"
        fake_bin = repository / "fake-bin"
        for directory in (
            script_directory,
            paper_directory,
            source_directory,
            download_directory,
            temporary_directory,
            fake_bin,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        fetch_text = FETCHER.read_text(encoding="utf-8", errors="strict")
        source_rows: list[dict[str, object]] = []
        for index, source in enumerate(self.module.SOURCE_SPECS, start=1):
            decompressed = (
                f">fixture_{index}_{source.source_id}\n"
                f"{'ACGT' * (index + 1)}\n"
            ).encode("ascii")
            compressed = gzip.compress(decompressed, mtime=0)
            row = {
                field: getattr(source, field)
                for field in self.module.SOURCE_SPEC_FIELDS
            }
            row.update(
                {
                    "upstream_md5": hashlib.md5(compressed).hexdigest(),
                    "compressed_size_bytes": len(compressed),
                    "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
                    "decompressed_size_bytes": len(decompressed),
                    "decompressed_sha256": hashlib.sha256(decompressed).hexdigest(),
                }
            )
            source_rows.append(row)
            (download_directory / Path(source.local_source_path).name).write_bytes(
                compressed
            )
            if valid_cache:
                destination = source_directory / Path(source.local_source_path).name
                destination.write_bytes(compressed)

        fetcher = script_directory / FETCHER_NAME
        fetcher.write_text(fetch_text, encoding="utf-8", newline="")
        fetcher.chmod(0o755)
        (script_directory / BUILDER_NAME).write_text(
            "raise AssertionError('real builder must not run in shell boundary tests')\n",
            encoding="ascii",
        )
        (paper_directory / "development_query_exclusions.tsv").write_text(
            "fixture\n",
            encoding="ascii",
        )
        (paper_directory / "holdout_manifest.tsv").write_text(
            "fixture\n",
            encoding="ascii",
        )
        source_specs = repository / "fixture-application-sources.tsv"
        with source_specs.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=self.module.SOURCE_SPEC_FIELDS,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(source_rows)

        output_paths = {
            "selection_receipt": paper_directory / "application_selection.json",
            "application_inputs": script_directory / "application_inputs",
            "manifest": paper_directory / "application_manifest.tsv",
            "manifest_checksum": paper_directory / "application_manifest.sha256",
            "source_ledger": paper_directory / "application_sources.tsv",
            "input_summary": paper_directory / "application_input_summary.tsv",
        }
        if committed_outputs:
            Path(output_paths["application_inputs"]).mkdir()
            for label, path in output_paths.items():
                if label == "application_inputs":
                    continue
                content = "fixture-selection\n" if label == "selection_receipt" else f"{label}\n"
                Path(path).write_text(content, encoding="ascii")

        curl_log = repository / "curl.log"
        python_log = repository / "python.log"
        fake_curl = fake_bin / "curl"
        fake_curl.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$*\" >>\"$FETCH_CURL_LOG\"\n"
            "output=''\n"
            "url=''\n"
            "while (($#)); do\n"
            "  if [[ \"$1\" == '--output' || \"$1\" == '-o' ]]; then\n"
            "    output=\"$2\"\n"
            "    shift 2\n"
            "  else\n"
            "    url=\"$1\"\n"
            "    shift\n"
            "  fi\n"
            "done\n"
            "[[ -n \"$output\" ]]\n"
            "if [[ \"${FETCH_CURL_MODE:-partial}\" == 'valid' ]]; then\n"
            "  cat -- \"$FETCH_DOWNLOAD_DIR/${url##*/}\" >\"$output\"\n"
            "else\n"
            "  printf 'incomplete-download' >\"$output\"\n"
            "fi\n"
            "exit \"${FETCH_CURL_STATUS:-23}\"\n",
            encoding="ascii",
        )
        fake_curl.chmod(0o755)
        fake_python = fake_bin / "python3"
        fake_python.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "builder=\"$1\"\n"
            "command_name=\"$2\"\n"
            "shift 2\n"
            "if [[ \"$command_name\" == 'cleanup-cache-entry' ]]; then\n"
            "  cache_directory_fd=''\n"
            "  entry_name=''\n"
            "  expected_device=''\n"
            "  expected_inode=''\n"
            "  while (($#)); do\n"
            "    key=\"$1\"\n"
            "    value=\"$2\"\n"
            "    case \"$key\" in\n"
            "      --cache-directory-fd) cache_directory_fd=\"$value\" ;;\n"
            "      --entry-name) entry_name=\"$value\" ;;\n"
            "      --expected-device) expected_device=\"$value\" ;;\n"
            "      --expected-inode) expected_inode=\"$value\" ;;\n"
            "    esac\n"
            "    shift 2\n"
            "  done\n"
            "  entry=\"/proc/self/fd/$cache_directory_fd/$entry_name\"\n"
            "  actual_identity=\"$("
            "stat -Lc '%d:%i' -- \"$entry\" 2>/dev/null || true)\"\n"
            "  if [[ \"$actual_identity\" == "
            "\"$expected_device:$expected_inode\" && ! -L \"$entry\" ]]; then\n"
            "    rm -f -- \"$entry\"\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' \"$command_name\" >>\"$FETCH_PYTHON_LOG\"\n"
            "if [[ \"$command_name\" == 'sources' ]]; then\n"
            "  cat -- \"$FETCH_SOURCE_SPECS\"\n"
            "  if [[ -n \"${FETCH_REMOVE_DURING_SOURCES:-}\" ]]; then\n"
            "    rm -f -- \"$FETCH_REMOVE_DURING_SOURCES\"\n"
            "  fi\n"
            "  if [[ -n \"${FETCH_SWAP_CACHE_PARENT_DURING_SOURCES:-}\" ]]; then\n"
            "    \"$FETCH_REAL_MV\" -- \"$FETCH_SWAP_CACHE_PARENT_DURING_SOURCES\" "
            "\"$FETCH_PARKED_CACHE_PARENT\"\n"
            "    \"$FETCH_REAL_LN\" -s -- \"$FETCH_OUTSIDE_CACHE_PARENT\" "
            "\"$FETCH_SWAP_CACHE_PARENT_DURING_SOURCES\"\n"
            "  fi\n"
            "  if [[ -n \"${FETCH_PAUSE_DURING_SOURCES:-}\" ]]; then\n"
            "    : >\"$FETCH_SOURCES_ENTERED\"\n"
            "    while [[ ! -e \"$FETCH_SOURCES_RELEASE\" ]]; do\n"
            "      \"$FETCH_REAL_SLEEP\" 0.01\n"
            "    done\n"
            "  fi\n"
            "  exit 0\n"
            "fi\n"
            "selection_receipt=''\n"
            "application_inputs=''\n"
            "manifest=''\n"
            "manifest_checksum=''\n"
            "source_ledger=''\n"
            "input_summary=''\n"
            "selection=''\n"
            "repository_root=''\n"
            "while (($#)); do\n"
            "  key=\"$1\"\n"
            "  value=\"$2\"\n"
            "  case \"$key\" in\n"
            "    --selection-receipt) selection_receipt=\"$value\" ;;\n"
            "    --application-inputs) application_inputs=\"$value\" ;;\n"
            "    --manifest) manifest=\"$value\" ;;\n"
            "    --manifest-checksum) manifest_checksum=\"$value\" ;;\n"
            "    --source-ledger) source_ledger=\"$value\" ;;\n"
            "    --input-summary) input_summary=\"$value\" ;;\n"
            "    --selection) selection=\"$value\" ;;\n"
            "    --repository-root) repository_root=\"$value\" ;;\n"
            "  esac\n"
            "  shift 2\n"
            "done\n"
            "publish_file() {\n"
            "  local path=\"$1\"\n"
            "  local content=\"$2\"\n"
            "  if [[ ! -e \"$path\" ]]; then\n"
            "    mkdir -p -- \"${path%/*}\"\n"
            "    printf '%s\\n' \"$content\" >\"$path\"\n"
            "  fi\n"
            "}\n"
            "case \"$command_name\" in\n"
            "  select)\n"
            "    if [[ -n \"${FETCH_CHECK_SELECTION_PARENT:-}\" ]]; then\n"
            "      printf '%s\\n' \"$repository_root\" "
            ">\"$FETCH_SELECTION_REPOSITORY_LOG\"\n"
            "      \"$FETCH_REAL_PYTHON\" -c 'import importlib.machinery, "
            "importlib.util, os, pathlib, sys; builder_path = pathlib.Path("
            "sys.argv[1]); repository_root = pathlib.Path(sys.argv[2]); loader = "
            "importlib.machinery.SourceFileLoader(\"selection_parent_builder\", "
            "str(builder_path)); spec = importlib.util.spec_from_loader("
            "\"selection_parent_builder\", loader); module = "
            "importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; "
            "spec.loader.exec_module(module); descriptor = "
            "module._open_output_directory(repository_root.parent, "
            "\"staging parent\"); os.close(descriptor); assert "
            "os.stat(repository_root.parent).st_uid == os.geteuid()' "
            "\"$FETCH_REAL_BUILDER\" \"$repository_root\"\n"
            "    fi\n"
            "    publish_file \"$selection_receipt\" 'fixture-selection'\n"
            "    ;;\n"
            "  verify)\n"
            "    [[ -d \"$application_inputs\" ]]\n"
            "    [[ \"$(cat -- \"$selection_receipt\")\" == 'fixture-selection' ]]\n"
            "    [[ \"$(cat -- \"$selection\")\" == 'fixture-selection' ]]\n"
            "    [[ -f \"$manifest\" ]]\n"
            "    [[ -f \"$manifest_checksum\" ]]\n"
            "    [[ -f \"$source_ledger\" ]]\n"
            "    [[ -f \"$input_summary\" ]]\n"
            "    ;;\n"
            "  materialize)\n"
            "    mkdir -p -- \"$application_inputs\"\n"
            "    publish_file \"$selection_receipt\" 'fixture-selection'\n"
            "    publish_file \"$manifest\" 'manifest'\n"
            "    publish_file \"$manifest_checksum\" 'manifest_checksum'\n"
            "    publish_file \"$source_ledger\" 'source_ledger'\n"
            "    publish_file \"$input_summary\" 'input_summary'\n"
            "    ;;\n"
            "  *) exit 91 ;;\n"
            "esac\n"
            "if [[ \"$command_name\" == "
            "\"${FETCH_SWAP_CACHE_PARENT_AFTER_COMMAND:-}\" ]]; then\n"
            "  \"$FETCH_REAL_MV\" -- \"$FETCH_SWAP_CACHE_PARENT\" "
            "\"$FETCH_PARKED_CACHE_PARENT\"\n"
            "  \"$FETCH_REAL_LN\" -s -- \"$FETCH_OUTSIDE_CACHE_PARENT\" "
            "\"$FETCH_SWAP_CACHE_PARENT\"\n"
            "fi\n",
            encoding="ascii",
        )
        fake_python.chmod(0o755)

        environment = os.environ.copy()
        environment.pop("SOURCE_DIR", None)
        environment.update(
            {
                "PATH": f"{fake_bin}:{environment['PATH']}",
                "TMPDIR": str(temporary_directory),
                "FETCH_CURL_LOG": str(curl_log),
                "FETCH_DOWNLOAD_DIR": str(download_directory),
                "FETCH_PYTHON_LOG": str(python_log),
                "FETCH_SOURCE_SPECS": str(source_specs),
            }
        )
        return {
            "repository": repository,
            "fetcher": fetcher,
            "source_directory": source_directory,
            "download_directory": download_directory,
            "temporary_directory": temporary_directory,
            "fake_bin": fake_bin,
            "environment": environment,
            "curl_log": curl_log,
            "python_log": python_log,
            "output_paths": output_paths,
        }

    def run_fetch_harness(
        self,
        harness: dict[str, object],
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/bash", str(harness["fetcher"]), *arguments],
            cwd=Path(harness["repository"]),
            env=dict(harness["environment"]) if environment is None else environment,
            pass_fds=AUTHENTICATED_DEPENDENCY_FDS,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

    @staticmethod
    def unique_query_sequence(index: int, length: int = 700) -> str:
        alphabet = "ACGT"
        value = index + 1
        prefix: list[str] = []
        for _ in range(12):
            prefix.append(alphabet[value % 4])
            value //= 4
        return "".join(prefix) + "A" * (length - len(prefix))

    def add_query_record(
        self,
        records: list[tuple[str, str]],
        transcripts: dict[str, object],
        *,
        transcript_id: str,
        gene_id: str,
        sequence: str,
        gene_name: str | None = None,
        gene_type: str = "lncRNA",
        chromosome: str = "chr1",
        level: int = 1,
        basic: bool = True,
        declared_length: str | None = None,
        description: str = "",
    ) -> None:
        name = gene_name or self.module.stable_id(gene_id)
        tags = frozenset({"basic"}) if basic else frozenset()
        transcripts[transcript_id] = self.module.Transcript(
            transcript_id=transcript_id,
            gene_id=gene_id,
            gene_name=name,
            gene_type=gene_type,
            chromosome=chromosome,
            start=100,
            end=100 + len(sequence) - 1,
            strand="+",
            level=level,
            tags=tags,
        )
        length_text = str(len(sequence)) if declared_length is None else declared_length
        records.append(
            (
                f"{transcript_id}|{gene_id}|-|-|{name}-201|{name}|{length_text}|{description}",
                sequence,
            )
        )

    def basic_query_fixture(
        self,
        count: int,
    ) -> tuple[list[tuple[str, str]], dict[str, object]]:
        records: list[tuple[str, str]] = []
        transcripts: dict[str, object] = {}
        for index in range(1, count + 1):
            self.add_query_record(
                records,
                transcripts,
                transcript_id=f"ENSTQ{index:05d}.1",
                gene_id=f"ENSGQ{index:05d}.1",
                gene_name=f"QUERY{index:05d}",
                sequence=self.unique_query_sequence(index),
            )
        return records, transcripts

    @staticmethod
    def no_development_exclusions() -> dict[str, set[str]]:
        return {"gene_id": set(), "gene_name": set(), "sequence_sha256": set()}

    @staticmethod
    def holdout_row(
        *,
        workload_id: str = "hq01_ht01",
        query_id: str = "hq01",
        gene_id: str = "ENSGHOLD.3",
        query_sequence_sha256: str = "a" * 64,
    ) -> dict[str, str]:
        row = {field: "fixture" for field in HOLDOUT_MANIFEST_FIELDS}
        row.update(
            {
                "workload_id": workload_id,
                "query_id": query_id,
                "gene_id": gene_id,
                "gene_name": "HOLDOUT",
                "transcript_id": "ENSTHOLD.1",
                "query_length_nt": "700",
                "length_stratum": "le_800",
                "query_sequence_sha256": query_sequence_sha256,
                "query_file_sha256": "b" * 64,
                "query_path": "reproduce/bioinformatics/holdout_inputs/queries/hq01.fa",
                "target_id": "ht01",
                "target_gene_id": "ENSGTARGET.1",
                "target_gene_name": "TARGET",
                "target_chromosome": "chr1",
                "target_strand": "+",
                "target_tss": "1000",
                "target_region_start": "1",
                "target_region_end": "2501",
                "target_length_bp": "2501",
                "target_sequence_sha256": "c" * 64,
                "target_file_sha256": "d" * 64,
                "target_path": "reproduce/bioinformatics/holdout_inputs/targets/ht01.fa",
                "assembly": "GRCh38",
                "annotation_release": "GENCODE v49",
                "selection_seed": "gasal2-longtarget-phase2-holdout-v1-20260724",
                "requested_contract": "all-ranked-top5",
                "run_modes": "authority,candidate,verified",
                "repeat_count": "1",
                "status": "preregistered_not_run",
            }
        )
        return row

    @staticmethod
    def transcript_row(
        *,
        chromosome: str = "chr21",
        start: str = "100",
        end: str = "900",
        strand: str = "+",
        attributes: str | None = None,
    ) -> str:
        attribute_text = attributes or (
            'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "QUERY"; '
            'gene_type "lncRNA"; level 2; tag "basic";'
        )
        return (
            f"{chromosome}\tHAVANA\ttranscript\t{start}\t{end}\t.\t{strand}\t.\t"
            f"{attribute_text}\n"
        )

    def target_transcript(
        self,
        *,
        transcript_id: str,
        gene_id: str,
        chromosome: str = "chr21",
        start: int = 10000,
        end: int = 10800,
        strand: str = "+",
        gene_name: str | None = None,
        gene_type: str = "protein_coding",
        level: int = 2,
        tags: frozenset[str] = frozenset(),
    ) -> object:
        return self.module.Transcript(
            transcript_id=transcript_id,
            gene_id=gene_id,
            gene_name=gene_name or self.module.stable_id(gene_id),
            gene_type=gene_type,
            chromosome=chromosome,
            start=start,
            end=end,
            strand=strand,
            level=level,
            tags=tags,
        )

    def target_selection_fixture(
        self,
        count: int = 300,
        chr21_count: int = 150,
    ) -> tuple[dict[str, object], dict[str, str]]:
        if not 0 <= chr21_count <= count:
            raise AssertionError("invalid synthetic chromosome split")
        transcripts: dict[str, object] = {}
        for index in range(1, count + 1):
            chromosome = "chr21" if index <= chr21_count else "chr22"
            base_tss = 10000 if chromosome == "chr21" else 15000
            tss = base_tss + index % 3 * 1000
            strand = "+" if index % 2 else "-"
            start = tss if strand == "+" else tss - 800
            end = tss + 800 if strand == "+" else tss
            transcript = self.target_transcript(
                transcript_id=f"ENST_TARGET_{index:04d}.1",
                gene_id=f"ENSG_TARGET_{index:04d}.7",
                gene_name=f"TARGET_{index:04d}",
                chromosome=chromosome,
                start=start,
                end=end,
                strand=strand,
                level=2,
                tags=frozenset({"basic"}),
            )
            transcripts[transcript.transcript_id] = transcript
        return transcripts, {
            "chr21": self.chromosome_sequence,
            "chr22": self.chromosome_sequence,
        }

    def prepare_freeze_fixture(self) -> None:
        sources = self.work / "sources"
        sources.mkdir()

        query_records, query_transcripts = self.basic_query_fixture(50)
        excluded_sequences = {
            name: self.unique_query_sequence(index)
            for name, index in (
                ("development_gene", 51),
                ("development_name", 52),
                ("development_digest", 53),
                ("holdout_gene", 54),
                ("holdout_digest", 55),
            )
        }
        excluded_query_specs = (
            ("ENST_DEV_GENE.1", "ENSGDEV.7", "DEV_GENE", "development_gene"),
            ("ENST_DEV_NAME.1", "ENSG_DEV_NAME.1", "DEVNAME", "development_name"),
            (
                "ENST_DEV_DIGEST.1",
                "ENSG_DEV_DIGEST.1",
                "DEV_DIGEST",
                "development_digest",
            ),
            ("ENST_HOLD_GENE.1", "ENSGHOLD.3", "HOLD_GENE", "holdout_gene"),
            (
                "ENST_HOLD_DIGEST.1",
                "ENSG_HOLD_DIGEST.1",
                "HOLD_DIGEST",
                "holdout_digest",
            ),
        )
        for transcript_id, gene_id, gene_name, sequence_name in excluded_query_specs:
            self.add_query_record(
                query_records,
                query_transcripts,
                transcript_id=transcript_id,
                gene_id=gene_id,
                gene_name=gene_name,
                sequence=excluded_sequences[sequence_name],
            )
        target_transcripts, chromosome_sequences = self.target_selection_fixture()
        excluded_targets = (
            self.target_transcript(
                transcript_id="ENST_TARGET_NONCANONICAL.1",
                gene_id="ENSG_TARGET_NONCANONICAL.1",
                chromosome="chr21",
                start=25000,
                end=25800,
            ),
            self.target_transcript(
                transcript_id="ENST_TARGET_EMPTY.1",
                gene_id="ENSG_TARGET_EMPTY.1",
                chromosome="chr22",
                start=30001,
                end=30801,
            ),
        )
        for transcript in excluded_targets:
            target_transcripts[transcript.transcript_id] = transcript
        chr21_sequence = list(chromosome_sequences["chr21"])
        chr21_sequence[24999] = "N"
        chromosome_sequences["chr21"] = "".join(chr21_sequence)

        lnc_rna_fasta = sources / "gencode.v49.lncRNA_transcripts.fa"
        lnc_rna_fasta.write_text(
            "".join(f">{header}\n{sequence}\n" for header, sequence in query_records),
            encoding="utf-8",
        )

        annotation_gtf = sources / "gencode.v49.annotation.gtf"
        gtf_rows: list[str] = []
        for transcript in (*query_transcripts.values(), *target_transcripts.values()):
            tags = "".join(f' tag "{tag}";' for tag in sorted(transcript.tags))
            attributes = (
                f'gene_id "{transcript.gene_id}"; '
                f'transcript_id "{transcript.transcript_id}"; '
                f'gene_name "{transcript.gene_name}"; '
                f'gene_type "{transcript.gene_type}"; '
                f"level {transcript.level};{tags}"
            )
            gtf_rows.append(
                self.transcript_row(
                    chromosome=transcript.chromosome,
                    start=str(transcript.start),
                    end=str(transcript.end),
                    strand=transcript.strand,
                    attributes=attributes,
                )
            )
        annotation_gtf.write_text("".join(gtf_rows), encoding="utf-8")

        chr21_fasta = sources / "chr21.fa"
        chr22_fasta = sources / "chr22.fa"
        chr21_fasta.write_text(
            f">chr21\n{chromosome_sequences['chr21']}\n",
            encoding="utf-8",
        )
        chr22_fasta.write_text(
            f">chr22\n{chromosome_sequences['chr22']}\n",
            encoding="utf-8",
        )
        development_exclusions = sources / "development_query_exclusions.tsv"
        development_exclusions.write_text(
            "exclusion_type\tvalue\treason\n"
            "gene_id\tENSGDEV.99\tdevelopment gene fixture\n"
            "gene_name\tDEVNAME\tdevelopment name fixture\n"
            f"sequence_sha256\t{hashlib.sha256(excluded_sequences['development_digest'].encode('ascii')).hexdigest()}\tdevelopment digest fixture\n",
            encoding="utf-8",
        )
        holdout_manifest = sources / "holdout_manifest.tsv"
        with holdout_manifest.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=HOLDOUT_MANIFEST_FIELDS,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(
                self.holdout_row(
                    query_sequence_sha256=hashlib.sha256(
                        excluded_sequences["holdout_digest"].encode("ascii")
                    ).hexdigest()
                )
            )

        biological_paths = (
            lnc_rna_fasta,
            annotation_gtf,
            chr21_fasta,
            chr22_fasta,
        )
        fixture_source_specs = tuple(
            self.fixture_source_spec(template, path)
            for template, path in zip(
                self.module.SOURCE_SPECS,
                biological_paths,
                strict=True,
            )
        )
        self.synthetic_inputs = self.module.SourceInputs(
            lncrna_fasta=lnc_rna_fasta,
            annotation_gtf=annotation_gtf,
            chr21_fasta=chr21_fasta,
            chr22_fasta=chr22_fasta,
            development_exclusions=development_exclusions,
            holdout_manifest=holdout_manifest,
            source_specs=fixture_source_specs,
        )
        self.output_paths = self.freeze_paths_for_repository("repository")
        self.sandbox = self.output_paths.repository_root

    def fixture_source_spec(self, template: object, path: Path) -> object:
        md5_digest = hashlib.md5()
        sha256_digest = hashlib.sha256()
        size_bytes = 0
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                md5_digest.update(block)
                sha256_digest.update(block)
                size_bytes += len(block)
        sha256 = sha256_digest.hexdigest()
        decompressed_size_bytes = size_bytes
        decompressed_sha256 = sha256
        if path.suffix == ".gz":
            decompressed_digest = hashlib.sha256()
            decompressed_size_bytes = 0
            with gzip.open(path, "rb") as handle:
                while block := handle.read(1024 * 1024):
                    decompressed_digest.update(block)
                    decompressed_size_bytes += len(block)
            decompressed_sha256 = decompressed_digest.hexdigest()
        return replace(
            template,
            provider="synthetic unit fixture",
            release="test-only",
            assembly="synthetic",
            url=f"https://fixtures.invalid/{template.source_id}/{path.name}",
            upstream_md5=md5_digest.hexdigest(),
            compressed_size_bytes=size_bytes,
            compressed_sha256=sha256,
            decompressed_size_bytes=decompressed_size_bytes,
            decompressed_sha256=decompressed_sha256,
            local_source_path=f"synthetic/{template.source_id}/{path.name}",
            license_or_terms="synthetic test fixture",
            redistribution_note="not for redistribution",
            download_command="fixture supplied directly by the unit test",
        )

    def freeze_paths_for_repository(
        self,
        name: str,
        *,
        create_paper: bool = True,
    ) -> object:
        repository = self.work / name
        repository.mkdir()
        paper = repository / "paper/bioinformatics"
        if create_paper:
            paper.mkdir(parents=True)
        return self.module.FreezePaths(
            repository_root=repository,
            selection_receipt=paper / "application_selection.json",
            application_inputs=(
                repository / "reproduce/bioinformatics/application_inputs"
            ),
            manifest=paper / "application_manifest.tsv",
            manifest_checksum=paper / "application_manifest.sha256",
            source_ledger=paper / "application_sources.tsv",
            input_summary=paper / "application_input_summary.tsv",
        )

    def freeze_cli_arguments(self) -> list[str]:
        return [
            "--repository-root",
            str(self.output_paths.repository_root),
            "--lncrna-fasta",
            str(self.synthetic_inputs.lncrna_fasta),
            "--annotation-gtf",
            str(self.synthetic_inputs.annotation_gtf),
            "--chr21-fasta",
            str(self.synthetic_inputs.chr21_fasta),
            "--chr22-fasta",
            str(self.synthetic_inputs.chr22_fasta),
            "--development-exclusions",
            str(self.synthetic_inputs.development_exclusions),
            "--holdout-manifest",
            str(self.synthetic_inputs.holdout_manifest),
            "--selection-receipt",
            str(self.output_paths.selection_receipt),
            "--application-inputs",
            str(self.output_paths.application_inputs),
            "--manifest",
            str(self.output_paths.manifest),
            "--manifest-checksum",
            str(self.output_paths.manifest_checksum),
            "--source-ledger",
            str(self.output_paths.source_ledger),
            "--input-summary",
            str(self.output_paths.input_summary),
        ]

    def run_resource_probe(self, scenario: str) -> dict[str, object]:
        environment = os.environ.copy()
        environment["APPLICATION_PANEL_RESOURCE_PROBE"] = scenario
        completed = subprocess.run(
            [sys.executable, str(TEST_MODULE)],
            cwd=ROOT,
            env=environment,
            pass_fds=AUTHENTICATED_DEPENDENCY_FDS,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"resource probe failed:\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        lines = [line for line in completed.stdout.splitlines() if line]
        self.assertEqual(len(lines), 1, completed.stdout)
        payload = json.loads(lines[0])
        self.assertIsInstance(payload, dict)
        return payload

    def test_materialize_writes_exact_record_manifest_and_summary(self) -> None:
        self.prepare_freeze_fixture()

        result = self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        rows = read_tsv(self.output_paths.manifest)

        self.assertEqual(tuple(rows[0]), self.module.MANIFEST_FIELDS)
        self.assertEqual(sum(row["record_role"] == "query" for row in rows), 50)
        self.assertGreaterEqual(
            sum(row["record_role"] == "target" for row in rows),
            300,
        )
        self.assertTrue(all(row["status"] == "preregistered_not_run" for row in rows))
        self.assertEqual(result["pair_count"], 50 * result["target_count"])

    def test_source_ledger_is_transaction_owned_and_byte_exact(self) -> None:
        self.prepare_freeze_fixture()
        self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        rows = read_tsv(self.output_paths.source_ledger)
        self.assertEqual(tuple(rows[0]), self.module.APPLICATION_SOURCE_FIELDS)
        self.assertEqual(
            [row["source_id"] for row in rows],
            [source.source_id for source in self.synthetic_inputs.source_specs],
        )
        for source, row in zip(self.synthetic_inputs.source_specs, rows, strict=True):
            with self.subTest(source_id=source.source_id):
                self.assertEqual(
                    row,
                    {
                        field: str(getattr(source, field))
                        if field != "status"
                        else "verified"
                        for field in self.module.APPLICATION_SOURCE_FIELDS
                    },
                )

        self.assertNotEqual(
            rows[0]["compressed_sha256"],
            self.module.SOURCE_SPECS[0].compressed_sha256,
        )

        rollback_outputs = self.freeze_paths_for_repository("source-ledger-rollback")
        before = fingerprint_tree_no_follow(rollback_outputs.repository_root)

        def fail_after_source_ledger(_step: int, path: Path) -> None:
            if path == rollback_outputs.source_ledger:
                raise RuntimeError("injected source ledger publication failure")

        with self.assertRaisesRegex(RuntimeError, "source ledger publication failure"):
            self.module.build_freeze(
                self.synthetic_inputs,
                rollback_outputs,
                after_publish=fail_after_source_ledger,
            )
        self.assertEqual(
            fingerprint_tree_no_follow(rollback_outputs.repository_root),
            before,
        )

        self.output_paths.source_ledger.write_text("drift\n", encoding="ascii")
        drifted = fingerprint_tree_no_follow(self.output_paths.repository_root)
        with self.assertRaisesRegex(ValueError, "existing source ledger drift"):
            self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        self.assertEqual(
            fingerprint_tree_no_follow(self.output_paths.repository_root),
            drifted,
        )

    def test_mismatched_biological_source_identity_cannot_publish_verified_ledger(
        self,
    ) -> None:
        self.prepare_freeze_fixture()
        mismatched = replace(
            self.synthetic_inputs,
            source_specs=self.module.SOURCE_SPECS,
        )
        before = fingerprint_tree_no_follow(self.output_paths.repository_root)

        with self.assertRaisesRegex(
            ValueError,
            "biological source identity mismatch.*gencode_v49_lncrna",
        ):
            self.module.build_freeze(mismatched, self.output_paths)

        self.assertEqual(
            fingerprint_tree_no_follow(self.output_paths.repository_root),
            before,
        )
        self.assertFalse(self.output_paths.source_ledger.exists())

    def test_gzip_decompressed_identity_is_bound_to_parser_consumed_stream(
        self,
    ) -> None:
        self.prepare_freeze_fixture()
        original_bytes = self.synthetic_inputs.lncrna_fasta.read_bytes()
        compressed_path = self.work / "lncrna-fixture.fa.gz"
        with compressed_path.open("wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                compressed.write(original_bytes)
        compressed_spec = self.fixture_source_spec(
            self.synthetic_inputs.source_specs[0],
            compressed_path,
        )
        correct_specs = (
            compressed_spec,
            *self.synthetic_inputs.source_specs[1:],
        )
        correct_inputs = replace(
            self.synthetic_inputs,
            lncrna_fasta=compressed_path,
            source_specs=correct_specs,
        )
        descriptor_directory = Path("/proc/self/fd")
        descriptors_before = (
            len(os.listdir(descriptor_directory))
            if descriptor_directory.is_dir()
            else None
        )

        cases = (
            (
                replace(compressed_spec, decompressed_size_bytes=1),
                "decompressed size",
            ),
            (
                replace(compressed_spec, decompressed_sha256="0" * 64),
                "decompressed sha256",
            ),
        )
        for index, (bad_spec, label) in enumerate(cases):
            with self.subTest(label=label):
                outputs = self.freeze_paths_for_repository(f"bad-decompressed-{index}")
                before = fingerprint_tree_no_follow(outputs.repository_root)
                bad_inputs = replace(
                    correct_inputs,
                    source_specs=(bad_spec, *correct_specs[1:]),
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "decompressed biological source identity mismatch.*"
                    "gencode_v49_lncrna",
                ):
                    self.module.build_freeze(bad_inputs, outputs)
                self.assertEqual(
                    fingerprint_tree_no_follow(outputs.repository_root),
                    before,
                )
                self.assertFalse(outputs.source_ledger.exists())

        outputs = self.freeze_paths_for_repository("valid-decompressed")
        result = self.module.build_freeze(correct_inputs, outputs)
        source_rows = read_tsv(outputs.source_ledger)
        self.assertEqual(result["freeze_id"], "bioinformatics-phase3-application-v1-06dbae75")
        self.assertEqual(
            source_rows[0]["decompressed_size_bytes"],
            str(len(original_bytes)),
        )
        self.assertEqual(
            source_rows[0]["decompressed_sha256"],
            hashlib.sha256(original_bytes).hexdigest(),
        )
        self.assertEqual(
            self.module.parse_fasta(compressed_path),
            self.module.parse_fasta(self.synthetic_inputs.lncrna_fasta),
        )
        if descriptors_before is not None:
            self.assertEqual(
                len(os.listdir(descriptor_directory)),
                descriptors_before,
            )

    def test_gzip_stream_validation_rejects_truncation_and_accepts_members(
        self,
    ) -> None:
        self.prepare_freeze_fixture()
        original_bytes = self.synthetic_inputs.lncrna_fasta.read_bytes()
        template = self.synthetic_inputs.source_specs[0]
        valid_path = self.work / "valid-gzip-source.fa.gz"
        valid_path.write_bytes(gzip.compress(original_bytes, mtime=0))
        valid_spec = self.fixture_source_spec(template, valid_path)

        with self.subTest(stream="corrupt_deflate_payload"):
            corrupt_path = self.work / "corrupt-gzip-source.fa.gz"
            corrupt_bytes = bytearray(valid_path.read_bytes())
            corrupt_bytes[10] = (corrupt_bytes[10] & ~0x06) | 0x06
            corrupt_path.write_bytes(corrupt_bytes)
            corrupt_spec = replace(
                valid_spec,
                upstream_md5=hashlib.md5(corrupt_bytes).hexdigest(),
                compressed_size_bytes=len(corrupt_bytes),
                compressed_sha256=hashlib.sha256(corrupt_bytes).hexdigest(),
                local_source_path=(
                    f"synthetic/{template.source_id}/{corrupt_path.name}"
                ),
            )
            corrupt_specs = (
                corrupt_spec,
                *self.synthetic_inputs.source_specs[1:],
            )
            arguments = self.freeze_cli_arguments()
            arguments[arguments.index("--lncrna-fasta") + 1] = str(corrupt_path)
            before = fingerprint_tree_no_follow(self.output_paths.repository_root)
            standard_error = io.StringIO()
            standard_output = io.StringIO()
            caught: BaseException | None = None
            result: int | None = None
            try:
                with mock.patch.object(
                    self.module,
                    "SOURCE_SPECS",
                    corrupt_specs,
                ), mock.patch("sys.stderr", standard_error), mock.patch(
                    "sys.stdout",
                    standard_output,
                ):
                    result = self.module.main(["materialize", *arguments])
            except BaseException as error:
                caught = error
            self.assertIsNone(caught, f"corrupt gzip escaped CLI handling: {caught}")
            self.assertEqual(result, 2)
            self.assertIn(
                "cannot decompress biological source",
                standard_error.getvalue(),
            )
            self.assertEqual(
                fingerprint_tree_no_follow(self.output_paths.repository_root),
                before,
            )

        with self.subTest(stream="truncated"):
            truncated_path = self.work / "truncated-gzip-source.fa.gz"
            truncated_bytes = valid_path.read_bytes()[:-8]
            truncated_path.write_bytes(truncated_bytes)
            truncated_spec = replace(
                valid_spec,
                upstream_md5=hashlib.md5(truncated_bytes).hexdigest(),
                compressed_size_bytes=len(truncated_bytes),
                compressed_sha256=hashlib.sha256(truncated_bytes).hexdigest(),
                local_source_path=(
                    f"synthetic/{template.source_id}/{truncated_path.name}"
                ),
            )
            truncated_inputs = replace(
                self.synthetic_inputs,
                lncrna_fasta=truncated_path,
                source_specs=(
                    truncated_spec,
                    *self.synthetic_inputs.source_specs[1:],
                ),
            )
            outputs = self.freeze_paths_for_repository("truncated-gzip")
            before = fingerprint_tree_no_follow(outputs.repository_root)
            caught: BaseException | None = None
            try:
                self.module.build_freeze(truncated_inputs, outputs)
            except BaseException as error:
                caught = error
            self.assertIsInstance(caught, ValueError)
            self.assertRegex(
                str(caught),
                "cannot decompress biological source.*truncated-gzip-source",
            )
            self.assertEqual(
                fingerprint_tree_no_follow(outputs.repository_root),
                before,
            )

        with self.subTest(stream="concatenated_members"):
            multiple_path = self.work / "multiple-member-source.fa.gz"
            midpoint = len(original_bytes) // 2
            with multiple_path.open("wb") as raw:
                for chunk in (
                    original_bytes[:midpoint],
                    original_bytes[midpoint:],
                ):
                    with gzip.GzipFile(
                        fileobj=raw,
                        mode="wb",
                        mtime=0,
                    ) as compressed:
                        compressed.write(chunk)
            multiple_spec = self.fixture_source_spec(template, multiple_path)
            multiple_inputs = replace(
                self.synthetic_inputs,
                lncrna_fasta=multiple_path,
                source_specs=(
                    multiple_spec,
                    *self.synthetic_inputs.source_specs[1:],
                ),
            )
            outputs = self.freeze_paths_for_repository("multiple-member-gzip")
            self.module.build_freeze(multiple_inputs, outputs)
            source_rows = read_tsv(outputs.source_ledger)
            self.assertEqual(
                source_rows[0]["decompressed_size_bytes"],
                str(len(original_bytes)),
            )
            self.assertEqual(
                source_rows[0]["decompressed_sha256"],
                hashlib.sha256(original_bytes).hexdigest(),
            )
            self.assertEqual(
                self.module.parse_fasta(multiple_path),
                self.module.parse_fasta(self.synthetic_inputs.lncrna_fasta),
            )

    def test_biological_source_specs_require_exact_ids_and_roles(self) -> None:
        self.prepare_freeze_fixture()
        specs = self.synthetic_inputs.source_specs
        cases = (
            (specs[:-1], "exactly four biological source specs"),
            ((specs[0], specs[0], specs[2], specs[3]), "source IDs and order"),
            (
                (replace(specs[0], role="wrong role"), *specs[1:]),
                "source role mismatch",
            ),
        )
        for index, (source_specs, message) in enumerate(cases):
            with self.subTest(index=index):
                outputs = self.freeze_paths_for_repository(f"bad-source-spec-{index}")
                before = fingerprint_tree_no_follow(outputs.repository_root)
                with self.assertRaisesRegex(ValueError, message):
                    self.module.build_freeze(
                        replace(self.synthetic_inputs, source_specs=source_specs),
                        outputs,
                    )
                self.assertEqual(
                    fingerprint_tree_no_follow(outputs.repository_root),
                    before,
                )

    def test_existing_different_freeze_is_rejected_without_mutation(self) -> None:
        self.prepare_freeze_fixture()
        self.output_paths.manifest.write_text("drift\n", encoding="utf-8")
        before = fingerprint_tree_no_follow(self.sandbox)

        with self.assertRaisesRegex(ValueError, "existing .* drift"):
            self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_manifest_rows_match_exact_fasta_records_and_selection_identities(self) -> None:
        self.prepare_freeze_fixture()
        self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        rows = read_tsv(self.output_paths.manifest)
        receipt = json.loads(self.output_paths.selection_receipt.read_text(encoding="utf-8"))
        selected_queries = {
            row["query_id"]: row for row in receipt["selected_queries"]
        }
        selected_targets = {
            row["target_id"]: row for row in receipt["selected_targets"]
        }
        actual_files = {
            path.relative_to(self.output_paths.application_inputs).as_posix()
            for path in self.output_paths.application_inputs.rglob("*")
            if path.is_file()
        }
        self.assertEqual(len(rows), 350)
        self.assertEqual(
            actual_files,
            {
                PurePosixPath(row["path"])
                .relative_to("reproduce/bioinformatics/application_inputs")
                .as_posix()
                for row in rows
            },
        )

        for row in rows:
            with self.subTest(record_id=row["record_id"]):
                path = PurePosixPath(row["path"])
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual(
                    path.parts[:3],
                    ("reproduce", "bioinformatics", "application_inputs"),
                )
                fasta = self.sandbox.joinpath(*path.parts)
                records = self.module.parse_fasta(fasta)
                self.assertEqual(len(records), 1)
                header, sequence = records[0]
                self.assertEqual(int(row["sequence_length"]), len(sequence))
                self.assertEqual(
                    row["sequence_sha256"],
                    hashlib.sha256(sequence.encode("ascii")).hexdigest(),
                )
                self.assertEqual(
                    row["file_sha256"],
                    hashlib.sha256(fasta.read_bytes()).hexdigest(),
                )
                self.assertEqual(row["source_release"], "GENCODE v49")
                self.assertEqual(row["assembly"], "GRCh38")
                self.assertEqual(row["split"], "application")
                self.assertEqual(row["status"], "preregistered_not_run")
                self.assertEqual(header.split("|", 1)[0], row["record_id"])

                if row["record_role"] == "query":
                    selected = selected_queries[row["record_id"]]
                    self.assertEqual(
                        tuple(row[field] for field in (
                            "chromosome",
                            "strand",
                            "tss",
                            "region_start",
                            "region_end",
                        )),
                        ("NA", "NA", "NA", "NA", "NA"),
                    )
                    self.assertEqual(row["license_note"], self.module.QUERY_LICENSE)
                    self.assertEqual(row["selection_rule"], self.module.QUERY_SELECTION_RULE)
                else:
                    selected = selected_targets[row["record_id"]]
                    self.assertEqual(
                        tuple(row[field] for field in (
                            "chromosome",
                            "strand",
                            "tss",
                            "region_start",
                            "region_end",
                        )),
                        tuple(
                            str(selected[field])
                            for field in (
                                "chromosome",
                                "strand",
                                "tss",
                                "region_start",
                                "region_end",
                            )
                        ),
                    )
                    self.assertEqual(row["license_note"], self.module.TARGET_LICENSE)
                    self.assertEqual(row["selection_rule"], self.module.TARGET_SELECTION_RULE)
                self.assertEqual(row["original_gene_id"], selected["original_gene_id"])
                self.assertEqual(row["original_gene_name"], selected["original_gene_name"])
                self.assertEqual(
                    row["original_transcript_id"],
                    selected["original_transcript_id"],
                )

        query_rows = [row for row in rows if row["record_role"] == "query"]
        target_rows = [row for row in rows if row["record_role"] == "target"]
        self.assertEqual(len({row["record_id"] for row in rows}), len(rows))
        self.assertEqual(len({row["path"] for row in rows}), len(rows))
        self.assertEqual(len({row["original_gene_id"].split(".", 1)[0] for row in query_rows}), 50)
        self.assertEqual(len({row["sequence_sha256"] for row in query_rows}), 50)
        self.assertEqual(
            len({row["original_gene_id"].split(".", 1)[0] for row in target_rows}),
            len(target_rows),
        )

    def test_summary_checksum_and_freeze_id_are_strictly_derived(self) -> None:
        self.prepare_freeze_fixture()
        result = self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        manifest_bytes = self.output_paths.manifest.read_bytes()
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        rows = read_tsv(self.output_paths.manifest)
        summary_rows = read_tsv(self.output_paths.input_summary)
        self.assertEqual(len(summary_rows), 1)
        self.assertEqual(tuple(summary_rows[0]), self.module.SUMMARY_FIELDS)
        summary = summary_rows[0]
        self.assertEqual(
            self.output_paths.manifest_checksum.read_text(encoding="ascii"),
            f"{manifest_sha256}  {self.output_paths.manifest.name}\n",
        )
        self.assertEqual(summary["manifest_sha256"], manifest_sha256)
        self.assertEqual(
            summary["freeze_id"],
            f"bioinformatics-phase3-application-v1-{manifest_sha256[:8]}",
        )

        query_rows = [row for row in rows if row["record_role"] == "query"]
        target_rows = [row for row in rows if row["record_role"] == "target"]
        derived = {
            "query_count": len(query_rows),
            "target_count": len(target_rows),
            "pair_count": len(query_rows) * len(target_rows),
            "query_total_bp": sum(int(row["sequence_length"]) for row in query_rows),
            "target_total_bp": sum(int(row["sequence_length"]) for row in target_rows),
            "chr21_target_count": sum(row["chromosome"] == "chr21" for row in target_rows),
            "chr22_target_count": sum(row["chromosome"] == "chr22" for row in target_rows),
            "min_query_length": min(int(row["sequence_length"]) for row in query_rows),
            "max_query_length": max(int(row["sequence_length"]) for row in query_rows),
        }
        transcripts = self.module.parse_gtf(self.synthetic_inputs.annotation_gtf)
        selected_targets, target_counts = self.module.select_targets(
            transcripts=transcripts,
            chromosome_sequences={
                "chr21": self.module.read_chromosome_fasta(
                    self.synthetic_inputs.chr21_fasta, "chr21"
                ),
                "chr22": self.module.read_chromosome_fasta(
                    self.synthetic_inputs.chr22_fasta, "chr22"
                ),
            },
        )
        self.assertEqual(len(selected_targets), len(target_rows))
        derived["annotation_target_candidate_count"] = target_counts[
            "annotation_target_candidate_count"
        ]
        derived["excluded_target_count"] = target_counts["excluded_target_count"]
        for field, expected in derived.items():
            with self.subTest(field=field):
                self.assertEqual(int(summary[field]), expected)
                self.assertEqual(result[field], expected)
        self.assertEqual(result["freeze_id"], summary["freeze_id"])
        self.assertEqual(result["manifest_sha256"], manifest_sha256)
        self.assertEqual(int(summary["query_count"]), 50)
        self.assertGreaterEqual(int(summary["target_count"]), 300)
        self.assertGreaterEqual(int(summary["pair_count"]), 15000)

    def test_selection_receipt_is_canonical_and_records_reconstructed_selection(self) -> None:
        self.prepare_freeze_fixture()
        result = self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        receipt_bytes = self.output_paths.selection_receipt.read_bytes()
        receipt = json.loads(receipt_bytes)
        self.assertEqual(
            receipt_bytes,
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("ascii"),
        )
        self.assertEqual(
            set(receipt),
            {
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
            },
        )
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["selection_seed"], self.module.SELECTION_SEED)
        self.assertEqual(receipt["query_selection_rule"], self.module.QUERY_SELECTION_RULE)
        self.assertEqual(receipt["target_selection_rule"], self.module.TARGET_SELECTION_RULE)
        self.assertEqual(receipt["proposed_freeze_id"], result["freeze_id"])
        self.assertEqual(receipt["final_freeze_id"], result["freeze_id"])
        self.assertEqual(receipt["manifest_sha256"], result["manifest_sha256"])
        self.assertEqual(receipt["query_counts"]["selected_query_count"], 50)
        self.assertEqual(receipt["target_counts"]["retained_target_count"], 300)
        self.assertEqual(
            {
                field: receipt["query_counts"][field]
                for field in (
                    "excluded_development_gene_id_count",
                    "excluded_development_gene_name_count",
                    "excluded_development_sequence_sha256_count",
                    "excluded_holdout_gene_id_count",
                    "excluded_holdout_sequence_sha256_count",
                )
            },
            {
                "excluded_development_gene_id_count": 1,
                "excluded_development_gene_name_count": 1,
                "excluded_development_sequence_sha256_count": 1,
                "excluded_holdout_gene_id_count": 1,
                "excluded_holdout_sequence_sha256_count": 1,
            },
        )
        self.assertEqual(receipt["target_counts"]["annotation_target_candidate_count"], 302)
        self.assertEqual(receipt["target_counts"]["excluded_target_count"], 2)
        self.assertEqual(receipt["target_counts"]["excluded_empty_promoter_count"], 1)
        self.assertEqual(receipt["target_counts"]["excluded_noncanonical_promoter_count"], 1)
        self.assertEqual(len(receipt["selected_queries"]), 50)
        self.assertEqual(len(receipt["selected_targets"]), 300)

        source_paths = {
            "annotation_gtf": self.synthetic_inputs.annotation_gtf,
            "chr21_fasta": self.synthetic_inputs.chr21_fasta,
            "chr22_fasta": self.synthetic_inputs.chr22_fasta,
            "development_exclusions": self.synthetic_inputs.development_exclusions,
            "lncrna_fasta": self.synthetic_inputs.lncrna_fasta,
            "phase2_holdout_manifest": self.synthetic_inputs.holdout_manifest,
        }
        self.assertEqual(set(receipt["source_identities"]), set(source_paths))
        for name, path in source_paths.items():
            with self.subTest(source=name):
                content = path.read_bytes()
                self.assertEqual(
                    receipt["source_identities"][name],
                    {
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "size_bytes": len(content),
                    },
                )

        fasta_records = self.module.parse_fasta(self.synthetic_inputs.lncrna_fasta)
        transcripts = self.module.parse_gtf(self.synthetic_inputs.annotation_gtf)
        holdout_gene_ids, holdout_digests = self.module.read_holdout_exclusions(
            self.synthetic_inputs.holdout_manifest
        )
        selected_queries, query_counts = self.module.select_queries(
            fasta_records=fasta_records,
            transcripts=transcripts,
            development_exclusions=self.module.read_development_exclusions(
                self.synthetic_inputs.development_exclusions
            ),
            holdout_gene_ids=holdout_gene_ids,
            holdout_sequence_sha256=holdout_digests,
        )
        selected_targets, target_counts = self.module.select_targets(
            transcripts=transcripts,
            chromosome_sequences={
                "chr21": self.module.read_chromosome_fasta(
                    self.synthetic_inputs.chr21_fasta, "chr21"
                ),
                "chr22": self.module.read_chromosome_fasta(
                    self.synthetic_inputs.chr22_fasta, "chr22"
                ),
            },
        )
        expected_queries = [
            {
                "query_id": row["query_id"],
                "original_gene_id": row["gene_id"],
                "original_gene_name": row["gene_name"],
                "original_transcript_id": row["transcript_id"],
                "selection_hash": row["selection_hash"],
                "sequence_length": row["sequence_length"],
                "sequence_sha256": row["sequence_sha256"],
            }
            for row in selected_queries
        ]
        expected_targets = [
            {
                "target_id": row["target_id"],
                "original_gene_id": row["gene_id"],
                "original_gene_name": row["gene_name"],
                "original_transcript_id": row["transcript_id"],
                "chromosome": row["chromosome"],
                "strand": row["strand"],
                "tss": row["tss"],
                "region_start": row["region_start"],
                "region_end": row["region_end"],
                "sequence_length": row["sequence_length"],
                "sequence_sha256": row["sequence_sha256"],
            }
            for row in selected_targets
        ]
        self.assertEqual(receipt["query_counts"], query_counts)
        self.assertEqual(receipt["target_counts"], target_counts)
        self.assertEqual(receipt["selected_queries"], expected_queries)
        self.assertEqual(receipt["selected_targets"], expected_targets)

    def test_select_and_materialize_cli_reconstruct_and_reject_stale_receipt(self) -> None:
        self.prepare_freeze_fixture()
        self.assertEqual(
            tuple(inspect.signature(self.module.select_freeze).parameters),
            ("inputs", "outputs"),
        )

        standard_output = io.StringIO()
        with mock.patch.object(
            self.module,
            "SOURCE_SPECS",
            self.synthetic_inputs.source_specs,
        ), mock.patch("sys.stdout", standard_output):
            self.assertEqual(
                self.module.main(["select", *self.freeze_cli_arguments()]),
                0,
            )
        receipt_bytes = self.output_paths.selection_receipt.read_bytes()
        self.assertEqual(
            receipt_bytes,
            (
                json.dumps(json.loads(receipt_bytes), indent=2, sort_keys=True) + "\n"
            ).encode("ascii"),
        )
        self.assertFalse(self.output_paths.application_inputs.exists())
        self.assertFalse(self.output_paths.manifest.exists())
        self.assertFalse(self.output_paths.manifest_checksum.exists())
        self.assertFalse(self.output_paths.input_summary.exists())

        stale = json.loads(receipt_bytes)
        stale["selected_queries"].pop()
        stale_path = self.work / "stale-selection.json"
        stale_path.write_text(
            json.dumps(stale, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        before = fingerprint_tree_no_follow(self.sandbox)
        standard_error = io.StringIO()
        with mock.patch.object(
            self.module,
            "SOURCE_SPECS",
            self.synthetic_inputs.source_specs,
        ), mock.patch("sys.stderr", standard_error):
            self.assertEqual(
                self.module.main(
                    [
                        "materialize",
                        *self.freeze_cli_arguments(),
                        "--selection",
                        str(stale_path),
                    ]
                ),
                2,
            )
        self.assertIn("selection receipt drift", standard_error.getvalue())
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

        standard_output = io.StringIO()
        with mock.patch.object(
            self.module,
            "SOURCE_SPECS",
            self.synthetic_inputs.source_specs,
        ), mock.patch("sys.stdout", standard_output):
            self.assertEqual(
                self.module.main(
                    [
                        "materialize",
                        *self.freeze_cli_arguments(),
                        "--selection",
                        str(self.output_paths.selection_receipt),
                    ]
                ),
                0,
            )
        self.assertEqual(self.output_paths.selection_receipt.read_bytes(), receipt_bytes)
        self.assertTrue(self.output_paths.application_inputs.is_dir())
        self.assertTrue(self.output_paths.manifest.is_file())
        self.assertIn("selected_queries=50", standard_output.getvalue())
        self.assertNotIn("subprocess", inspect.getsource(self.module))

    def test_verify_freeze_requires_complete_exact_outputs_without_mutation(
        self,
    ) -> None:
        self.prepare_freeze_fixture()
        expected = self.module.build_freeze(
            self.synthetic_inputs,
            self.output_paths,
        )
        verify_freeze = getattr(self.module, "verify_freeze", None)
        self.assertIsNotNone(verify_freeze, "verify_freeze is missing")
        self.assertEqual(
            tuple(inspect.signature(verify_freeze).parameters),
            ("inputs", "outputs", "selection"),
        )

        before = fingerprint_tree_no_follow(self.output_paths.repository_root)
        self.assertEqual(
            verify_freeze(
                self.synthetic_inputs,
                self.output_paths,
                self.output_paths.selection_receipt,
            ),
            expected,
        )
        self.assertEqual(
            fingerprint_tree_no_follow(self.output_paths.repository_root),
            before,
        )

        stale_selection = self.work / "stale-verify-selection.json"
        stale_selection.write_text("{}\n", encoding="ascii")
        before_stale = fingerprint_tree_no_follow(self.output_paths.repository_root)
        with self.assertRaisesRegex(ValueError, "selection receipt drift"):
            verify_freeze(
                self.synthetic_inputs,
                self.output_paths,
                stale_selection,
            )
        self.assertEqual(
            fingerprint_tree_no_follow(self.output_paths.repository_root),
            before_stale,
        )

        self.output_paths.source_ledger.unlink()
        before_missing = fingerprint_tree_no_follow(self.output_paths.repository_root)
        with self.assertRaisesRegex(
            ValueError,
            "existing freeze is incomplete: source ledger",
        ):
            verify_freeze(
                self.synthetic_inputs,
                self.output_paths,
                self.output_paths.selection_receipt,
            )
        self.assertEqual(
            fingerprint_tree_no_follow(self.output_paths.repository_root),
            before_missing,
        )
        self.assertFalse(self.output_paths.source_ledger.exists())

    def test_cache_cleanup_helper_unlinks_only_the_expected_inode(self) -> None:
        cleanup_entry = getattr(self.module, "_remove_owned_cache_entry", None)
        self.assertIsNotNone(cleanup_entry, "cache cleanup helper is missing")
        self.assertEqual(
            tuple(inspect.signature(cleanup_entry).parameters),
            ("cache_descriptor", "entry_name", "expected_identity"),
        )
        cache = self.work / "cleanup-cache"
        cache.mkdir()
        descriptor = os.open(
            cache,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            owned = cache / "owned.cache"
            owned.write_bytes(b"owned")
            owned_metadata = owned.stat()
            self.assertTrue(
                cleanup_entry(
                    descriptor,
                    owned.name,
                    (owned_metadata.st_dev, owned_metadata.st_ino),
                )
            )
            self.assertFalse(owned.exists())

            replaced = cache / "replaced.cache"
            replaced.write_bytes(b"original-owned")
            original_metadata = replaced.stat()
            parked = cache / "parked-owned.cache"
            replaced.rename(parked)
            replaced.write_bytes(b"unowned-replacement")
            self.assertFalse(
                cleanup_entry(
                    descriptor,
                    replaced.name,
                    (original_metadata.st_dev, original_metadata.st_ino),
                )
            )
            self.assertEqual(replaced.read_bytes(), b"unowned-replacement")
            self.assertEqual(parked.read_bytes(), b"original-owned")
        finally:
            os.close(descriptor)

    def test_cache_cleanup_cli_uses_inherited_directory_descriptor(self) -> None:
        cache = self.work / "cleanup-cache-cli"
        cache.mkdir()
        entry = cache / "owned.cache"
        entry.write_bytes(b"owned-by-cli")
        metadata = entry.stat()
        completed = subprocess.run(
            [
                "/bin/bash",
                "-c",
                (
                    "set -euo pipefail\n"
                    "cache=$1\n"
                    "builder=$2\n"
                    "entry_name=$3\n"
                    "expected_device=$4\n"
                    "expected_inode=$5\n"
                    "exec {cache_fd}<\"$cache\"\n"
                    "python3 \"$builder\" cleanup-cache-entry "
                    "--cache-directory-fd \"$cache_fd\" "
                    "--entry-name \"$entry_name\" "
                    "--expected-device \"$expected_device\" "
                    "--expected-inode \"$expected_inode\"\n"
                ),
                "cleanup-cache-cli",
                str(cache),
                str(BUILDER),
                entry.name,
                str(metadata.st_dev),
                str(metadata.st_ino),
            ],
            cwd=ROOT,
            pass_fds=AUTHENTICATED_DEPENDENCY_FDS,
            check=False,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(completed.stdout, b"")
        self.assertEqual(completed.stderr, b"")
        self.assertFalse(entry.exists())

    def test_cli_select_always_binds_canonical_source_specs(self) -> None:
        self.prepare_freeze_fixture()
        before = fingerprint_tree_no_follow(self.output_paths.repository_root)
        standard_error = io.StringIO()

        with mock.patch("sys.stderr", standard_error):
            self.assertEqual(
                self.module.main(["select", *self.freeze_cli_arguments()]),
                2,
            )

        self.assertIn(
            "biological source identity mismatch for gencode_v49_lncrna",
            standard_error.getvalue(),
        )
        self.assertEqual(
            fingerprint_tree_no_follow(self.output_paths.repository_root),
            before,
        )

    def test_select_publication_is_create_or_byte_identical(self) -> None:
        self.prepare_freeze_fixture()
        first = self.module.select_freeze(self.synthetic_inputs, self.output_paths)
        before = fingerprint_tree_no_follow(self.sandbox)
        second = self.module.select_freeze(self.synthetic_inputs, self.output_paths)
        self.assertEqual(second, first)
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

        self.output_paths.selection_receipt.write_text("{}\n", encoding="ascii")
        before = fingerprint_tree_no_follow(self.sandbox)
        with self.assertRaisesRegex(ValueError, "existing selection receipt drift"):
            self.module.select_freeze(self.synthetic_inputs, self.output_paths)
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_identical_rerun_is_byte_stable_and_performs_zero_publish_steps(self) -> None:
        self.prepare_freeze_fixture()
        first_steps: list[tuple[int, Path]] = []
        first_result = self.module.build_freeze(
            self.synthetic_inputs,
            self.output_paths,
            after_publish=lambda step, path: first_steps.append((step, path)),
        )
        self.assertEqual(
            first_steps,
            [
                (1, self.output_paths.application_inputs),
                (2, self.output_paths.selection_receipt),
                (3, self.output_paths.manifest),
                (4, self.output_paths.manifest_checksum),
                (5, self.output_paths.source_ledger),
                (6, self.output_paths.input_summary),
            ],
        )
        before = fingerprint_tree_no_follow(self.sandbox)
        rerun_steps: list[tuple[int, Path]] = []

        second_result = self.module.build_freeze(
            self.synthetic_inputs,
            self.output_paths,
            after_publish=lambda step, path: rerun_steps.append((step, path)),
        )

        self.assertEqual(second_result, first_result)
        self.assertEqual(rerun_steps, [])
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_identical_rerun_preserves_all_published_atime_and_mtime(self) -> None:
        self.prepare_freeze_fixture()
        self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        application = self.output_paths.application_inputs
        published_paths = [
            *sorted(application.rglob("*.fa")),
            application / "queries",
            application / "targets",
            application,
            self.output_paths.selection_receipt,
            self.output_paths.manifest,
            self.output_paths.manifest_checksum,
            self.output_paths.source_ledger,
            self.output_paths.input_summary,
        ]
        old_time = 946684800_000_000_000
        for index, path in enumerate(published_paths):
            timestamp = old_time + index
            os.utime(path, ns=(timestamp, timestamp), follow_symlinks=False)

        def timestamps() -> dict[Path, tuple[int, int]]:
            return {
                path: (os.lstat(path).st_atime_ns, os.lstat(path).st_mtime_ns)
                for path in published_paths
            }

        before = timestamps()
        callbacks: list[tuple[int, Path]] = []
        self.module.build_freeze(
            self.synthetic_inputs,
            self.output_paths,
            after_publish=lambda step, path: callbacks.append((step, path)),
        )
        self.assertEqual(callbacks, [])
        self.assertEqual(timestamps(), before)

    def test_extra_missing_or_different_fasta_rejects_without_mutation(self) -> None:
        self.prepare_freeze_fixture()
        self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        cases = ("extra", "missing", "different")
        for case in cases:
            with self.subTest(case=case):
                application_inputs = self.output_paths.application_inputs
                if case == "extra":
                    changed = application_inputs / "queries/extra.fa"
                    changed.write_text(">extra\nACGT\n", encoding="ascii")
                    restore = lambda: changed.unlink()
                else:
                    changed = next((application_inputs / "targets").glob("*.fa"))
                    original = changed.read_bytes()
                    if case == "missing":
                        changed.unlink()
                    else:
                        changed.write_bytes(original + b"A\n")
                    restore = lambda changed=changed, original=original: changed.write_bytes(original)
                before = fingerprint_tree_no_follow(self.sandbox)
                with self.assertRaisesRegex(ValueError, "existing application input tree drift"):
                    self.module.build_freeze(self.synthetic_inputs, self.output_paths)
                self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)
                restore()

    def test_existing_output_files_must_not_have_external_hardlinks(self) -> None:
        self.prepare_freeze_fixture()
        external = self.work / "external-hardlinks"
        external.mkdir()
        artifact_names = (
            "application_fasta",
            "selection_receipt",
            "manifest",
            "manifest_checksum",
            "source_ledger",
            "input_summary",
        )
        for artifact_name in artifact_names:
            with self.subTest(artifact=artifact_name):
                outputs = self.freeze_paths_for_repository(f"hardlink-{artifact_name}")
                self.module.build_freeze(self.synthetic_inputs, outputs)
                if artifact_name == "application_fasta":
                    artifact = next((outputs.application_inputs / "queries").glob("*.fa"))
                else:
                    artifact = getattr(outputs, artifact_name)
                os.link(artifact, external / f"{artifact_name}.linked")
                before = fingerprint_tree_no_follow(outputs.repository_root)
                with self.assertRaisesRegex(ValueError, "multiply-linked output"):
                    self.module.build_freeze(self.synthetic_inputs, outputs)
                self.assertEqual(
                    fingerprint_tree_no_follow(outputs.repository_root),
                    before,
                )

    def test_registration_failure_after_each_filesystem_mutation_rolls_back(self) -> None:
        self.prepare_freeze_fixture()
        original_record_created = self.module._PublicationJournal.record_created
        cases = (
            ("reproduce parent", "build", True, Path("reproduce")),
            (
                "application parent",
                "build",
                True,
                Path("reproduce/bioinformatics"),
            ),
            (
                "application tree",
                "build",
                True,
                Path("reproduce/bioinformatics/application_inputs"),
            ),
            ("paper parent", "select", False, Path("paper")),
            (
                "metadata parent",
                "select",
                False,
                Path("paper/bioinformatics"),
            ),
            (
                "selection receipt",
                "build",
                True,
                Path("paper/bioinformatics/application_selection.json"),
            ),
            (
                "manifest",
                "build",
                True,
                Path("paper/bioinformatics/application_manifest.tsv"),
            ),
            (
                "manifest checksum",
                "build",
                True,
                Path("paper/bioinformatics/application_manifest.sha256"),
            ),
            (
                "source ledger",
                "build",
                True,
                Path("paper/bioinformatics/application_sources.tsv"),
            ),
            (
                "input summary",
                "build",
                True,
                Path("paper/bioinformatics/application_input_summary.tsv"),
            ),
        )
        for label, operation, create_paper, relative_failure_path in cases:
            with self.subTest(label=label):
                outputs = self.freeze_paths_for_repository(
                    f"registration-{label.replace(' ', '-')}",
                    create_paper=create_paper,
                )
                failure_path = outputs.repository_root / relative_failure_path
                registration_failed = False

                def fail_selected_registration(
                    journal: object,
                    *,
                    parent_descriptor: int,
                    name: str,
                    display_path: Path,
                    recursive: bool,
                ) -> None:
                    nonlocal registration_failed
                    if display_path == failure_path and not registration_failed:
                        registration_failed = True
                        raise RuntimeError("injected post-mutation registration failure")
                    original_record_created(
                        journal,
                        parent_descriptor=parent_descriptor,
                        name=name,
                        display_path=display_path,
                        recursive=recursive,
                    )

                before = fingerprint_tree_no_follow(outputs.repository_root)
                with mock.patch.object(
                    self.module._PublicationJournal,
                    "record_created",
                    new=fail_selected_registration,
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "post-mutation registration failure",
                    ):
                        if operation == "select":
                            self.module.select_freeze(self.synthetic_inputs, outputs)
                        else:
                            self.module.build_freeze(self.synthetic_inputs, outputs)

                self.assertTrue(registration_failed)
                self.assertEqual(
                    fingerprint_tree_no_follow(outputs.repository_root),
                    before,
                )
                self.assertFalse(tuple(self.work.glob(".*.application-*-stage.*")))

    def test_failure_after_each_publish_step_rolls_back_exactly(self) -> None:
        self.prepare_freeze_fixture()
        baseline_steps: list[int] = []
        self.module.build_freeze(
            self.synthetic_inputs,
            self.output_paths,
            after_publish=lambda step, _path: baseline_steps.append(step),
        )
        self.assertEqual(baseline_steps, [1, 2, 3, 4, 5, 6])
        receipt_bytes = self.output_paths.selection_receipt.read_bytes()

        for preexisting_receipt, expected_steps in ((False, 6), (True, 5)):
            for failure_step in range(1, expected_steps + 1):
                with self.subTest(
                    preexisting_receipt=preexisting_receipt,
                    failure_step=failure_step,
                ):
                    outputs = self.freeze_paths_for_repository(
                        f"failure-{int(preexisting_receipt)}-{failure_step}"
                    )
                    if preexisting_receipt:
                        outputs.selection_receipt.write_bytes(receipt_bytes)
                    before = fingerprint_tree_no_follow(outputs.repository_root)
                    observed: list[tuple[int, Path]] = []

                    def fail_after_publish(step: int, path: Path) -> None:
                        observed.append((step, path))
                        if step == failure_step:
                            raise RuntimeError(f"injected failure after step {step}")

                    with self.assertRaisesRegex(
                        RuntimeError,
                        f"injected failure after step {failure_step}",
                    ):
                        self.module.build_freeze(
                            self.synthetic_inputs,
                            outputs,
                            after_publish=fail_after_publish,
                        )
                    self.assertEqual(
                        [step for step, _path in observed],
                        list(range(1, failure_step + 1)),
                    )
                    self.assertEqual(
                        fingerprint_tree_no_follow(outputs.repository_root),
                        before,
                    )
                    self.assertFalse(
                        tuple(self.work.glob(".*.application-freeze-stage.*"))
                    )

    def test_callback_rollback_retries_one_shot_published_entry_removal_failure(self) -> None:
        self.prepare_freeze_fixture()
        original_remove = self.module._remove_created_path
        removal_failed = False

        def fail_application_removal_once(path: Path) -> None:
            nonlocal removal_failed
            if path == self.output_paths.application_inputs and not removal_failed:
                removal_failed = True
                raise OSError("injected published-entry removal failure")
            original_remove(path)

        def fail_callback(step: int, _path: Path) -> None:
            if step == 3:
                raise RuntimeError("injected callback failure")

        with mock.patch.object(
            self.module,
            "_remove_created_path",
            side_effect=fail_application_removal_once,
        ):
            with self.assertRaises(BaseException) as captured:
                self.module.build_freeze(
                    self.synthetic_inputs,
                    self.output_paths,
                    after_publish=fail_callback,
                )

        self.assertTrue(removal_failed)
        self.assertFalse(
            self.output_paths.application_inputs.exists(),
            "one-shot rollback failure left the published application tree",
        )
        self.assertIsInstance(captured.exception, RuntimeError)
        self.assertIn("injected callback failure", str(captured.exception))
        for path in (
            self.output_paths.selection_receipt,
            self.output_paths.manifest,
            self.output_paths.manifest_checksum,
            self.output_paths.source_ledger,
            self.output_paths.input_summary,
        ):
            self.assertFalse(os.path.lexists(path))
        self.assertFalse(tuple(self.work.glob(".*.application-freeze-stage.*")))

    def test_callback_failure_does_not_leak_retained_parent_descriptors(self) -> None:
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        self.prepare_freeze_fixture()

        def fail_callback(step: int, _path: Path) -> None:
            if step == 3:
                raise RuntimeError("injected callback failure")

        descriptors_before = len(os.listdir(descriptor_directory))
        for attempt in range(4):
            outputs = self.freeze_paths_for_repository(f"descriptor-leak-{attempt}")
            with self.assertRaisesRegex(RuntimeError, "injected callback failure"):
                self.module.build_freeze(
                    self.synthetic_inputs,
                    outputs,
                    after_publish=fail_callback,
                )
        descriptors_after = len(os.listdir(descriptor_directory))

        self.assertEqual(descriptors_after, descriptors_before)

    def test_rollback_removes_renamed_metadata_and_preserves_replacement(self) -> None:
        self.prepare_freeze_fixture()

        metadata_outputs = self.freeze_paths_for_repository("rollback-renamed-metadata")
        renamed_receipt = metadata_outputs.selection_receipt.with_name(
            "renamed-application-selection.json"
        )

        def rename_metadata_and_replace_name(step: int, _path: Path) -> None:
            if step == 2:
                metadata_outputs.selection_receipt.rename(renamed_receipt)
                metadata_outputs.selection_receipt.write_text(
                    "unrelated replacement\n",
                    encoding="ascii",
                )
                raise RuntimeError("injected renamed metadata failure")

        with self.assertRaisesRegex(RuntimeError, "renamed metadata failure"):
            self.module.build_freeze(
                self.synthetic_inputs,
                metadata_outputs,
                after_publish=rename_metadata_and_replace_name,
            )
        self.assertFalse(
            os.path.lexists(renamed_receipt),
            "rollback reported success while the created metadata inode remained renamed",
        )
        self.assertEqual(
            metadata_outputs.selection_receipt.read_text(encoding="ascii"),
            "unrelated replacement\n",
        )
        self.assertFalse(metadata_outputs.application_inputs.exists())

    def test_rollback_reports_renamed_created_tree_with_added_child(self) -> None:
        self.prepare_freeze_fixture()
        descriptor_directory = Path("/proc/self/fd")
        descriptors_before = (
            len(os.listdir(descriptor_directory))
            if descriptor_directory.is_dir()
            else None
        )
        renamed_outputs = self.freeze_paths_for_repository("rollback-renamed-tree")
        renamed_tree = renamed_outputs.application_inputs.with_name(
            "renamed-application-inputs"
        )
        added_child = renamed_tree / "unrelated.txt"

        def rename_tree_and_add_child(step: int, _path: Path) -> None:
            if step == 1:
                renamed_outputs.application_inputs.rename(renamed_tree)
                added_child.write_text("unrelated\n", encoding="ascii")
                raise RuntimeError("injected renamed nonempty tree failure")

        with self.assertRaisesRegex(RuntimeError, "transaction recovery failed"):
            self.module.build_freeze(
                self.synthetic_inputs,
                renamed_outputs,
                after_publish=rename_tree_and_add_child,
            )
        self.assertEqual(added_child.read_text(encoding="ascii"), "unrelated\n")
        self.assertTrue(renamed_tree.is_dir())
        self.assertFalse(renamed_outputs.application_inputs.exists())
        if descriptors_before is not None:
            self.assertEqual(len(os.listdir(descriptor_directory)), descriptors_before)

    def test_rollback_reports_created_tree_with_replaced_child(self) -> None:
        self.prepare_freeze_fixture()
        descriptor_directory = Path("/proc/self/fd")
        descriptors_before = (
            len(os.listdir(descriptor_directory))
            if descriptor_directory.is_dir()
            else None
        )
        replaced_outputs = self.freeze_paths_for_repository("rollback-replaced-child")
        replacement_path: Path | None = None

        def replace_created_child(step: int, _path: Path) -> None:
            nonlocal replacement_path
            if step == 1:
                replacement_path = next(
                    (replaced_outputs.application_inputs / "queries").glob("*.fa")
                )
                replacement_path.unlink()
                replacement_path.write_text("unrelated\n", encoding="ascii")
                raise RuntimeError("injected replaced child failure")

        with self.assertRaisesRegex(RuntimeError, "transaction recovery failed"):
            self.module.build_freeze(
                self.synthetic_inputs,
                replaced_outputs,
                after_publish=replace_created_child,
            )
        self.assertIsNotNone(replacement_path)
        assert replacement_path is not None
        self.assertEqual(replacement_path.read_text(encoding="ascii"), "unrelated\n")
        self.assertTrue(replaced_outputs.application_inputs.is_dir())
        if descriptors_before is not None:
            self.assertEqual(len(os.listdir(descriptor_directory)), descriptors_before)

    def test_commit_tolerates_close_error_after_release_for_each_descriptor_class(self) -> None:
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        self.prepare_freeze_fixture()
        original_commit = self.module._PublicationJournal.commit
        original_close = self.module.os.close

        for descriptor_kind in ("entry parent", "entry object", "timestamp"):
            with self.subTest(descriptor_kind=descriptor_kind):
                outputs = self.freeze_paths_for_repository(
                    f"close-{descriptor_kind.replace(' ', '-')}"
                )
                observed_journals: list[object] = []
                close_failed = False

                def commit_with_one_shot_close_failure(journal: object) -> None:
                    nonlocal close_failed
                    observed_journals.append(journal)
                    if descriptor_kind == "entry parent":
                        target_descriptor = journal.created[0].parent_descriptor
                    elif descriptor_kind == "entry object":
                        target_descriptor = next(
                            entry.object_descriptor
                            for entry in journal.created
                            if entry.object_descriptor is not None
                        )
                    else:
                        target_descriptor = next(iter(journal.timestamps.values())).descriptor

                    def fail_target_once(descriptor: int) -> None:
                        nonlocal close_failed
                        if descriptor == target_descriptor and not close_failed:
                            close_failed = True
                            original_close(descriptor)
                            raise OSError("injected close error after descriptor release")
                        original_close(descriptor)

                    with mock.patch.object(
                        self.module.os,
                        "close",
                        side_effect=fail_target_once,
                    ):
                        original_commit(journal)

                descriptors_before = len(os.listdir(descriptor_directory))
                captured_error: BaseException | None = None
                with mock.patch.object(
                    self.module._PublicationJournal,
                    "commit",
                    new=commit_with_one_shot_close_failure,
                ):
                    try:
                        self.module.build_freeze(self.synthetic_inputs, outputs)
                    except BaseException as error:
                        captured_error = error
                descriptors_after = len(os.listdir(descriptor_directory))

                self.assertTrue(close_failed)
                self.assertEqual(
                    None
                    if captured_error is None
                    else (type(captured_error).__name__, str(captured_error)),
                    None,
                )
                self.assertEqual(descriptors_after, descriptors_before)
                self.assertEqual(len(observed_journals), 1)
                journal = observed_journals[0]
                self.assertFalse(journal.armed)
                self.assertTrue(
                    all(
                        entry.parent_descriptor is None
                        and entry.object_descriptor is None
                        for entry in journal.created
                    )
                )
                self.assertTrue(
                    all(record.descriptor is None for record in journal.timestamps.values())
                )
                self.assertTrue(outputs.application_inputs.is_dir())
                self.assertTrue(outputs.input_summary.is_file())

    def test_returned_parent_close_errors_after_release_do_not_fail_commit(self) -> None:
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        self.prepare_freeze_fixture()
        original_publish = self.module._publish_staged
        original_close = self.module.os.close

        for operation, descriptor_kind in (
            ("build", "application"),
            ("build", "metadata"),
            ("select", "metadata"),
        ):
            with self.subTest(operation=operation, descriptor_kind=descriptor_kind):
                outputs = self.freeze_paths_for_repository(
                    f"returned-parent-{operation}-{descriptor_kind}"
                )
                returned: dict[str, int | None] = {}
                close_failed = False

                def capture_returned_parents(
                    *arguments: object,
                    **keywords: object,
                ) -> tuple[int | None, int | None]:
                    application_parent, metadata_parent = original_publish(
                        *arguments,
                        **keywords,
                    )
                    returned["application"] = application_parent
                    returned["metadata"] = metadata_parent
                    return application_parent, metadata_parent

                def fail_selected_parent_once(descriptor: int) -> None:
                    nonlocal close_failed
                    if (
                        descriptor == returned.get(descriptor_kind)
                        and not close_failed
                    ):
                        close_failed = True
                        original_close(descriptor)
                        raise OSError("injected returned parent close error after release")
                    original_close(descriptor)

                descriptors_before = len(os.listdir(descriptor_directory))
                captured_error: BaseException | None = None
                with mock.patch.object(
                    self.module,
                    "_publish_staged",
                    side_effect=capture_returned_parents,
                ), mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=fail_selected_parent_once,
                ):
                    try:
                        if operation == "select":
                            self.module.select_freeze(self.synthetic_inputs, outputs)
                        else:
                            self.module.build_freeze(self.synthetic_inputs, outputs)
                    except BaseException as error:
                        captured_error = error
                descriptors_after = len(os.listdir(descriptor_directory))

                self.assertIsNotNone(returned.get(descriptor_kind))
                self.assertTrue(close_failed)
                self.assertIsNone(captured_error)
                self.assertEqual(descriptors_after, descriptors_before)
                if operation == "select":
                    self.assertTrue(outputs.selection_receipt.is_file())
                    self.assertFalse(outputs.application_inputs.exists())
                else:
                    self.assertTrue(outputs.application_inputs.is_dir())
                    self.assertTrue(outputs.input_summary.is_file())

    def test_staging_root_close_error_after_release_preserves_transaction_result(self) -> None:
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        self.prepare_freeze_fixture()
        original_open = self.module._open_directory_at
        original_close = self.module.os.close

        for operation, outcome in (
            ("build", "success"),
            ("select", "success"),
            ("build", "rollback"),
        ):
            with self.subTest(operation=operation, outcome=outcome):
                outputs = self.freeze_paths_for_repository(
                    f"stage-descriptor-{operation}-{outcome}"
                )
                retained: dict[str, int] = {}
                close_failed = False

                def capture_stage_descriptor(parent_descriptor: int, name: str) -> int:
                    descriptor = original_open(parent_descriptor, name)
                    if name.startswith(
                        f".{outputs.repository_root.name}.application-"
                    ) and "-stage." in name:
                        retained["descriptor"] = descriptor
                    return descriptor

                def fail_stage_close_once(descriptor: int) -> None:
                    nonlocal close_failed
                    if descriptor == retained.get("descriptor") and not close_failed:
                        close_failed = True
                        original_close(descriptor)
                        raise OSError("injected staging root close error after release")
                    original_close(descriptor)

                def fail_callback(step: int, _path: Path) -> None:
                    if step == 2:
                        raise RuntimeError("injected staging rollback failure")

                descriptors_before = len(os.listdir(descriptor_directory))
                captured_error: BaseException | None = None
                with mock.patch.object(
                    self.module,
                    "_open_directory_at",
                    side_effect=capture_stage_descriptor,
                ), mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=fail_stage_close_once,
                ):
                    try:
                        if operation == "select":
                            self.module.select_freeze(self.synthetic_inputs, outputs)
                        else:
                            self.module.build_freeze(
                                self.synthetic_inputs,
                                outputs,
                                after_publish=(
                                    fail_callback if outcome == "rollback" else None
                                ),
                            )
                    except BaseException as error:
                        captured_error = error
                descriptors_after = len(os.listdir(descriptor_directory))
                descriptor = retained.get("descriptor")
                if descriptor is not None:
                    try:
                        os.fstat(descriptor)
                    except OSError:
                        pass
                    else:
                        original_close(descriptor)

                self.assertIsNotNone(descriptor)
                self.assertTrue(close_failed)
                if outcome == "rollback":
                    self.assertIsInstance(captured_error, RuntimeError)
                    self.assertIn("injected staging rollback failure", str(captured_error))
                    self.assertFalse(outputs.application_inputs.exists())
                    self.assertFalse(os.path.lexists(outputs.selection_receipt))
                else:
                    self.assertIsNone(captured_error)
                    if operation == "select":
                        self.assertTrue(outputs.selection_receipt.is_file())
                        self.assertFalse(outputs.application_inputs.exists())
                    else:
                        self.assertTrue(outputs.application_inputs.is_dir())
                        self.assertTrue(outputs.input_summary.is_file())
                self.assertEqual(descriptors_after, descriptors_before)
                self.assertFalse(
                    tuple(
                        self.work.glob(
                            f".{outputs.repository_root.name}.application-*-stage.*"
                        )
                    )
                )

    def test_repository_guard_close_error_after_release_is_not_a_false_failure(self) -> None:
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        self.prepare_freeze_fixture()
        original_walk = self.module._open_file_and_chain_by_no_follow_walk
        original_close = self.module.os.close

        for operation, preexisting in (
            ("build", False),
            ("select", False),
            ("build", True),
            ("select", True),
        ):
            with self.subTest(operation=operation, preexisting=preexisting):
                outputs = self.freeze_paths_for_repository(
                    f"guard-descriptor-{operation}-{'existing' if preexisting else 'new'}"
                )
                if preexisting:
                    if operation == "select":
                        expected = self.module.select_freeze(
                            self.synthetic_inputs,
                            outputs,
                        )
                    else:
                        expected = self.module.build_freeze(
                            self.synthetic_inputs,
                            outputs,
                        )
                else:
                    expected = None
                retained: dict[str, int] = {}
                close_failed = False

                def capture_guard_descriptor(
                    path: Path,
                    flags: int,
                ) -> tuple[int, tuple[tuple[int, int], ...]]:
                    descriptor, chain = original_walk(path, flags)
                    if path == outputs.repository_root:
                        retained["descriptor"] = descriptor
                    return descriptor, chain

                def fail_guard_close_once(descriptor: int) -> None:
                    nonlocal close_failed
                    if descriptor == retained.get("descriptor") and not close_failed:
                        close_failed = True
                        original_close(descriptor)
                        raise OSError("injected repository guard close error after release")
                    original_close(descriptor)

                descriptors_before = len(os.listdir(descriptor_directory))
                captured_error: BaseException | None = None
                actual: dict[str, object] | None = None
                with mock.patch.object(
                    self.module,
                    "_open_file_and_chain_by_no_follow_walk",
                    side_effect=capture_guard_descriptor,
                ), mock.patch.object(
                    self.module.os,
                    "close",
                    side_effect=fail_guard_close_once,
                ):
                    try:
                        if operation == "select":
                            actual = self.module.select_freeze(
                                self.synthetic_inputs,
                                outputs,
                            )
                        else:
                            actual = self.module.build_freeze(
                                self.synthetic_inputs,
                                outputs,
                            )
                    except BaseException as error:
                        captured_error = error
                descriptors_after = len(os.listdir(descriptor_directory))
                descriptor = retained.get("descriptor")
                if descriptor is not None:
                    try:
                        os.fstat(descriptor)
                    except OSError:
                        pass
                    else:
                        original_close(descriptor)

                self.assertIsNotNone(descriptor)
                self.assertTrue(close_failed)
                self.assertIsNone(captured_error)
                self.assertIsNotNone(actual)
                if expected is not None:
                    self.assertEqual(actual, expected)
                self.assertEqual(descriptors_after, descriptors_before)
                if operation == "select":
                    self.assertTrue(outputs.selection_receipt.is_file())
                else:
                    self.assertTrue(outputs.application_inputs.is_dir())
                    self.assertTrue(outputs.input_summary.is_file())

    def test_publication_descriptor_usage_is_bounded_under_low_rlimit(self) -> None:
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")

        with self.subTest(scenario="valid build at 256 descriptors"):
            valid = self.run_resource_probe("fd-valid")
            self.assertTrue(valid["setup_complete"])
            self.assertIsNone(valid["error"])
            self.assertEqual(
                valid["freeze_id"],
                "bioinformatics-phase3-application-v1-06dbae75",
            )
            self.assertTrue(valid["application_exists"])
            self.assertEqual(valid["stage_names"], [])
            self.assertEqual(valid["fd_after"], valid["fd_before"])

        with self.subTest(scenario="rollback at exhausted historical boundary"):
            rollback = self.run_resource_probe("fd-rollback")
            self.assertTrue(rollback["setup_complete"])
            self.assertEqual(
                rollback["error"],
                ["RuntimeError", "injected low-fd rollback"],
            )
            self.assertTrue(rollback["repository_unchanged"])
            self.assertFalse(rollback["application_exists"])
            self.assertEqual(rollback["stage_names"], [])
            self.assertEqual(rollback["fd_after"], rollback["fd_before"])
            self.assertLessEqual(
                int(rollback["callback_fd_count"]) - int(rollback["fd_before"]),
                32,
            )

        def retained_descriptor_delta(name: str, count: int) -> int:
            root = self.work / name
            root.mkdir()
            for index in range(count):
                (root / f"record-{index:04d}.fa").write_bytes(b">record\nACGT\n")
            root_descriptor = self.module._open_output_directory(root, name)
            captured: dict[tuple[str, ...], object] = {}
            try:
                before = len(os.listdir(descriptor_directory))
                captured = self.module._capture_tree_identities(root_descriptor)
                return len(os.listdir(descriptor_directory)) - before
            finally:
                for entry in captured.values():
                    close = getattr(entry, "close", None)
                    if close is not None:
                        close()
                os.close(root_descriptor)

        with self.subTest(scenario="descriptor count does not scale with records"):
            small_delta = retained_descriptor_delta("capture-small", 5)
            large_delta = retained_descriptor_delta("capture-large", 200)
            self.assertLessEqual(large_delta, small_delta + 4)
            self.assertLessEqual(large_delta, 16)

        with self.subTest(scenario="reserve released after prepublication failure"):
            self.prepare_freeze_fixture()
            original_reserve = self.module._PublicationJournal.reserve_rollback_capacity
            observed_journals: list[object] = []

            def reserve_then_fail(journal: object, descriptor: int) -> None:
                original_reserve(journal, descriptor)
                observed_journals.append(journal)
                self.assertEqual(len(journal.rollback_reserve), 8)
                raise RuntimeError("injected failure after rollback reserve")

            before = fingerprint_tree_no_follow(self.output_paths.repository_root)
            descriptors_before = len(os.listdir(descriptor_directory))
            with mock.patch.object(
                self.module._PublicationJournal,
                "reserve_rollback_capacity",
                new=reserve_then_fail,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "injected failure after rollback reserve",
                ):
                    self.module.build_freeze(self.synthetic_inputs, self.output_paths)
            self.assertEqual(len(observed_journals), 1)
            journal = observed_journals[0]
            self.assertTrue(
                all(record.descriptor is None for record in journal.rollback_reserve)
            )
            self.assertTrue(
                all(record.descriptor is None for record in journal.owned_descriptors)
            )
            self.assertEqual(len(os.listdir(descriptor_directory)), descriptors_before)
            self.assertEqual(fingerprint_tree_no_follow(self.output_paths.repository_root), before)
            self.assertFalse(tuple(self.work.glob(".*.application-freeze-stage.*")))

    def test_close_after_release_never_retries_reused_descriptor(self) -> None:
        self.prepare_freeze_fixture()
        original_commit = self.module._PublicationJournal.commit
        original_close = self.module.os.close
        replacement: dict[str, int] = {}
        close_attempts = 0
        survived = False

        def commit_with_release_then_error(journal: object) -> None:
            nonlocal survived
            target_descriptor = journal.created[0].parent_descriptor
            self.assertIsNotNone(target_descriptor)

            def release_reuse_and_raise(descriptor: int) -> None:
                nonlocal close_attempts
                if descriptor == target_descriptor:
                    close_attempts += 1
                    if close_attempts == 1:
                        original_close(descriptor)
                        read_descriptor, write_descriptor = os.pipe()
                        if read_descriptor != target_descriptor:
                            os.dup2(read_descriptor, target_descriptor)
                            original_close(read_descriptor)
                            read_descriptor = target_descriptor
                        replacement["read"] = target_descriptor
                        replacement["write"] = write_descriptor
                        raise OSError("injected close error after descriptor release")
                original_close(descriptor)

            with mock.patch.object(
                self.module.os,
                "close",
                side_effect=release_reuse_and_raise,
            ):
                original_commit(journal)
                try:
                    os.fstat(replacement["read"])
                except OSError:
                    pass
                else:
                    survived = True

        captured_error: BaseException | None = None
        try:
            with mock.patch.object(
                self.module._PublicationJournal,
                "commit",
                new=commit_with_release_then_error,
            ):
                try:
                    self.module.build_freeze(self.synthetic_inputs, self.output_paths)
                except BaseException as error:
                    captured_error = error
        finally:
            for descriptor in replacement.values():
                try:
                    original_close(descriptor)
                except OSError:
                    pass

        self.assertIsNone(captured_error)
        self.assertEqual(
            (close_attempts, survived),
            (1, True),
            "journal retried and closed an immediately reused descriptor",
        )
        self.assertTrue(self.output_paths.application_inputs.is_dir())
        self.assertTrue(self.output_paths.input_summary.is_file())

    def test_stage_cleanup_preserves_replacement_and_removes_retained_inode(self) -> None:
        self.prepare_freeze_fixture()
        before = fingerprint_tree_no_follow(self.output_paths.repository_root)
        parked_stage = self.work / "renamed-retained-stage"
        replacement_stage: Path | None = None
        replacement_marker: Path | None = None

        def replace_stage_name_then_fail(step: int, _path: Path) -> None:
            nonlocal replacement_stage, replacement_marker
            if step != 1:
                return
            stages = tuple(self.work.glob(".*.application-freeze-stage.*"))
            self.assertEqual(len(stages), 1)
            replacement_stage = stages[0]
            replacement_stage.rename(parked_stage)
            replacement_stage.mkdir()
            replacement_marker = replacement_stage / "unrelated.txt"
            replacement_marker.write_text("unrelated replacement\n", encoding="ascii")
            raise RuntimeError("injected stage namespace replacement")

        with self.assertRaisesRegex(RuntimeError, "injected stage namespace replacement"):
            self.module.build_freeze(
                self.synthetic_inputs,
                self.output_paths,
                after_publish=replace_stage_name_then_fail,
            )

        self.assertEqual(fingerprint_tree_no_follow(self.output_paths.repository_root), before)
        self.assertIsNotNone(replacement_stage)
        self.assertIsNotNone(replacement_marker)
        assert replacement_stage is not None
        assert replacement_marker is not None
        self.assertTrue(replacement_stage.is_dir())
        self.assertEqual(
            replacement_marker.read_text(encoding="ascii"),
            "unrelated replacement\n",
        )
        self.assertFalse(parked_stage.exists(), "retained staging inode was not removed")

    def test_stage_cleanup_reports_original_moved_outside_retained_parent(self) -> None:
        self.prepare_freeze_fixture()
        before = fingerprint_tree_no_follow(self.output_paths.repository_root)
        external_temporary = tempfile.TemporaryDirectory(
            prefix="bioinformatics-escaped-stage-"
        )
        self.addCleanup(external_temporary.cleanup)
        escaped_stage = Path(external_temporary.name) / "escaped-stage"
        replacement_stage: Path | None = None
        replacement_marker: Path | None = None

        def move_stage_outside_then_fail(step: int, _path: Path) -> None:
            nonlocal replacement_stage, replacement_marker
            if step != 1:
                return
            stages = tuple(self.work.glob(".*.application-freeze-stage.*"))
            self.assertEqual(len(stages), 1)
            replacement_stage = stages[0]
            replacement_stage.rename(escaped_stage)
            replacement_stage.mkdir()
            replacement_marker = replacement_stage / "unrelated.txt"
            replacement_marker.write_text("unrelated replacement\n", encoding="ascii")
            raise RuntimeError("injected escaped stage failure")

        with self.assertRaisesRegex(RuntimeError, "transaction recovery failed"):
            self.module.build_freeze(
                self.synthetic_inputs,
                self.output_paths,
                after_publish=move_stage_outside_then_fail,
            )

        self.assertEqual(fingerprint_tree_no_follow(self.output_paths.repository_root), before)
        self.assertTrue(escaped_stage.is_dir())
        self.assertIsNotNone(replacement_stage)
        self.assertIsNotNone(replacement_marker)
        assert replacement_stage is not None
        assert replacement_marker is not None
        self.assertTrue(replacement_stage.is_dir())
        self.assertEqual(
            replacement_marker.read_text(encoding="ascii"),
            "unrelated replacement\n",
        )

    def test_stage_creation_open_failure_leaves_no_residue_or_descriptor_leak(self) -> None:
        self.prepare_freeze_fixture()
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        original_open = self.module.os.open
        original_stat = self.module.os.stat
        original_descriptor_identity = self.module._descriptor_identity

        for operation in ("build", "select"):
            for injection_point in ("stat", "open", "descriptor_identity"):
                with self.subTest(operation=operation, injection_point=injection_point):
                    outputs = self.freeze_paths_for_repository(
                        f"stage-create-{operation}-{injection_point}"
                    )
                    stage_kind = "freeze" if operation == "build" else "select"
                    stage_prefix = (
                        f".{outputs.repository_root.name}.application-{stage_kind}-stage."
                    )
                    before = fingerprint_tree_no_follow(outputs.repository_root)
                    descriptors_before = len(os.listdir(descriptor_directory))
                    injected = False

                    def is_stage_name(path: object) -> bool:
                        return Path(os.fsdecode(os.fspath(path))).name.startswith(
                            stage_prefix
                        )

                    def fail_stage_child_stat(
                        path: object,
                        *arguments: object,
                        **keywords: object,
                    ) -> object:
                        nonlocal injected
                        if not injected and is_stage_name(path):
                            injected = True
                            raise OSError("injected staging child stat failure")
                        return original_stat(path, *arguments, **keywords)

                    def fail_stage_child_open(
                        path: object,
                        flags: int,
                        *arguments: object,
                        **keywords: object,
                    ) -> int:
                        nonlocal injected
                        if (
                            not injected
                            and is_stage_name(path)
                            and flags & getattr(os, "O_DIRECTORY", 0)
                        ):
                            injected = True
                            raise OSError("injected staging child open failure")
                        return original_open(path, flags, *arguments, **keywords)

                    def fail_stage_descriptor_identity(descriptor: int) -> tuple[int, int]:
                        nonlocal injected
                        descriptor_name = Path(
                            os.readlink(descriptor_directory / str(descriptor))
                        ).name
                        if not injected and descriptor_name.startswith(stage_prefix):
                            injected = True
                            raise OSError("injected staging descriptor identity failure")
                        return original_descriptor_identity(descriptor)

                    patcher = {
                        "stat": mock.patch.object(
                            self.module.os,
                            "stat",
                            side_effect=fail_stage_child_stat,
                        ),
                        "open": mock.patch.object(
                            self.module.os,
                            "open",
                            side_effect=fail_stage_child_open,
                        ),
                        "descriptor_identity": mock.patch.object(
                            self.module,
                            "_descriptor_identity",
                            side_effect=fail_stage_descriptor_identity,
                        ),
                    }[injection_point]

                    with patcher:
                        with self.assertRaisesRegex(
                            (OSError, ValueError),
                            "staging|output directory",
                        ):
                            if operation == "build":
                                self.module.build_freeze(self.synthetic_inputs, outputs)
                            else:
                                self.module.select_freeze(self.synthetic_inputs, outputs)

                    self.assertTrue(injected)
                    self.assertEqual(
                        len(os.listdir(descriptor_directory)), descriptors_before
                    )
                    self.assertEqual(
                        fingerprint_tree_no_follow(outputs.repository_root), before
                    )
                    self.assertFalse(tuple(self.work.glob(f"{stage_prefix}*")))

    def test_stage_population_uses_retained_inode_and_preserves_name_replacement(
        self,
    ) -> None:
        self.prepare_freeze_fixture()
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")
        original_stage_freeze = self.module._stage_freeze
        original_write_staged_file = self.module._write_staged_file

        for operation in ("build", "select"):
            with self.subTest(operation=operation):
                outputs = self.freeze_paths_for_repository(f"stage-populate-{operation}")
                before = fingerprint_tree_no_follow(outputs.repository_root)
                descriptors_before = len(os.listdir(descriptor_directory))
                parked = self.work / f"stage-populate-{operation}-parked"
                replacement_path: Path | None = None
                replacement_before: tuple[tuple[object, ...], ...] | None = None

                def replace_stage(stage_or_path: object) -> None:
                    nonlocal replacement_path, replacement_before
                    if replacement_path is not None:
                        return
                    if isinstance(stage_or_path, Path):
                        stage_path = stage_or_path
                    else:
                        stage_path = stage_or_path.display_path
                    stage_path.rename(parked)
                    stage_path.mkdir()
                    (stage_path / "replacement-marker.txt").write_text(
                        "unrelated replacement\n",
                        encoding="ascii",
                    )
                    replacement_path = stage_path
                    replacement_before = fingerprint_tree_no_follow(stage_path)

                def replace_stage_then_build(
                    stage_or_path: object,
                    model: object,
                ) -> object:
                    replace_stage(stage_or_path)
                    result = original_stage_freeze(stage_or_path, model)
                    raise RuntimeError("injected failure after descriptor-bound staging")

                def replace_stage_then_write(
                    destination_or_stage: object,
                    *arguments: object,
                    **keywords: object,
                ) -> object:
                    if isinstance(destination_or_stage, Path):
                        replace_stage(destination_or_stage.parent)
                    else:
                        replace_stage(destination_or_stage)
                    original_write_staged_file(
                        destination_or_stage,
                        *arguments,
                        **keywords,
                    )
                    raise RuntimeError("injected failure after descriptor-bound staging")

                patcher = mock.patch.object(
                    self.module,
                    "_stage_freeze" if operation == "build" else "_write_staged_file",
                    side_effect=(
                        replace_stage_then_build
                        if operation == "build"
                        else replace_stage_then_write
                    ),
                )
                with patcher:
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "injected failure after descriptor-bound staging",
                    ):
                        if operation == "build":
                            self.module.build_freeze(self.synthetic_inputs, outputs)
                        else:
                            self.module.select_freeze(self.synthetic_inputs, outputs)

                self.assertIsNotNone(replacement_path)
                self.assertIsNotNone(replacement_before)
                assert replacement_path is not None
                assert replacement_before is not None
                self.assertEqual(
                    fingerprint_tree_no_follow(replacement_path),
                    replacement_before,
                    "pathname replacement was mutated by stage population",
                )
                self.assertEqual(
                    (replacement_path / "replacement-marker.txt").read_text(
                        encoding="ascii"
                    ),
                    "unrelated replacement\n",
                )
                self.assertFalse(parked.exists(), "retained staging inode was not cleaned")
                self.assertEqual(fingerprint_tree_no_follow(outputs.repository_root), before)
                self.assertEqual(len(os.listdir(descriptor_directory)), descriptors_before)

    def test_source_ingestion_streams_under_bounded_address_space(self) -> None:
        self.prepare_freeze_fixture()
        descriptor_directory = Path("/proc/self/fd")
        if not descriptor_directory.is_dir():
            self.skipTest("open descriptor inspection requires /proc/self/fd")

        with self.subTest(scenario="snapshots retain metadata rather than source bytes"):
            snapshot_fields = {field.name for field in fields(self.module._SourceSnapshot)}
            self.assertNotIn("content", snapshot_fields)
            descriptors_before = len(os.listdir(descriptor_directory))
            snapshots = self.module._snapshot_sources(self.synthetic_inputs)
            try:
                self.assertEqual(
                    len(os.listdir(descriptor_directory)) - descriptors_before,
                    6,
                )
                for snapshot in snapshots.values():
                    self.assertFalse(
                        any(
                            isinstance(value, (bytes, bytearray))
                            for value in vars(snapshot).values()
                        )
                    )
            finally:
                for snapshot in snapshots.values():
                    close = getattr(snapshot, "close", None)
                    if close is not None:
                        close()
            self.assertEqual(len(os.listdir(descriptor_directory)), descriptors_before)

        source_paths = {
            self.synthetic_inputs.annotation_gtf,
            self.synthetic_inputs.chr21_fasta,
            self.synthetic_inputs.chr22_fasta,
            self.synthetic_inputs.development_exclusions,
            self.synthetic_inputs.lncrna_fasta,
            self.synthetic_inputs.holdout_manifest,
        }
        original_open = self.module._open_file_and_chain_by_no_follow_walk
        original_prepare = self.module._prepare_freeze_from_snapshots
        for outcome in ("success", "failure"):
            with self.subTest(scenario=f"six source descriptors close on {outcome}"):
                outputs = self.freeze_paths_for_repository(f"source-fd-{outcome}")
                open_counts = {path: 0 for path in source_paths}

                def count_source_open(
                    path: Path,
                    flags: int,
                ) -> tuple[int, tuple[tuple[int, int], ...]]:
                    if path in open_counts:
                        open_counts[path] += 1
                    return original_open(path, flags)

                def prepare_or_fail(
                    snapshots: object,
                    freeze_outputs: object,
                    verified_sources: object,
                ) -> object:
                    if outcome == "failure":
                        raise RuntimeError("injected preparation failure with retained sources")
                    return original_prepare(
                        snapshots,
                        freeze_outputs,
                        verified_sources,
                    )

                descriptors_before = len(os.listdir(descriptor_directory))
                captured_error: BaseException | None = None
                with mock.patch.object(
                    self.module,
                    "_open_file_and_chain_by_no_follow_walk",
                    side_effect=count_source_open,
                ), mock.patch.object(
                    self.module,
                    "_prepare_freeze_from_snapshots",
                    side_effect=prepare_or_fail,
                ):
                    try:
                        self.module.build_freeze(self.synthetic_inputs, outputs)
                    except BaseException as error:
                        captured_error = error
                if outcome == "failure":
                    self.assertIsInstance(captured_error, RuntimeError)
                    self.assertIn("injected preparation failure", str(captured_error))
                    self.assertFalse(outputs.application_inputs.exists())
                else:
                    self.assertIsNone(captured_error)
                    self.assertTrue(outputs.application_inputs.is_dir())
                self.assertEqual(set(open_counts.values()), {1})
                self.assertEqual(len(os.listdir(descriptor_directory)), descriptors_before)

        with self.subTest(scenario="large ineligible FASTA under address-space limit"):
            result = self.run_resource_probe("memory-stream")
            self.assertTrue(result["setup_complete"])
            self.assertGreaterEqual(int(result["lncrna_size_bytes"]), 64 * 1024 * 1024)
            self.assertIsNone(result["error"])
            self.assertEqual(
                result["freeze_id"],
                "bioinformatics-phase3-application-v1-06dbae75",
            )
            self.assertEqual(result["fd_after"], result["fd_before"])
            self.assertTrue(result["application_exists"])

    def test_rollback_uses_retained_parent_when_application_parent_is_replaced(self) -> None:
        self.prepare_freeze_fixture()
        original_parent = self.output_paths.application_inputs.parent
        parked_parent = self.output_paths.repository_root / "parked-bioinformatics"
        replacement_marker = original_parent / "unrelated.txt"

        def replace_parent_then_fail(step: int, _path: Path) -> None:
            if step != 1:
                return
            original_parent.rename(parked_parent)
            original_parent.mkdir()
            replacement_marker.write_text("unrelated\n", encoding="ascii")
            raise RuntimeError("injected failure after application parent replacement")

        with self.assertRaisesRegex(RuntimeError, "transaction recovery failed"):
            self.module.build_freeze(
                self.synthetic_inputs,
                self.output_paths,
                after_publish=replace_parent_then_fail,
            )

        self.assertTrue(
            replacement_marker.is_file(),
            "path-based rollback deleted unrelated replacement content",
        )
        self.assertEqual(replacement_marker.read_text(encoding="ascii"), "unrelated\n")
        self.assertFalse((parked_parent / "application_inputs").exists())
        self.assertFalse(tuple(self.work.glob(".*.application-freeze-stage.*")))

    def test_metadata_publish_uses_retained_parent_during_transient_symlink_swap(self) -> None:
        self.prepare_freeze_fixture()
        metadata_parent = self.output_paths.selection_receipt.parent
        parked_parent = self.output_paths.repository_root / "parked-paper-bioinformatics"
        outside = self.work / "outside-metadata-publish"
        outside.mkdir()
        marker = outside / "unrelated.txt"
        marker.write_text("unrelated\n", encoding="ascii")
        original_link = self.module.os.link
        swapped = False

        def link_during_parent_swap(
            source: object,
            destination: object,
            *arguments: object,
            **keywords: object,
        ) -> None:
            nonlocal swapped
            if str(destination).endswith("application_selection.json") and not swapped:
                swapped = True
                metadata_parent.rename(parked_parent)
                metadata_parent.symlink_to(outside, target_is_directory=True)
                try:
                    original_link(source, destination, *arguments, **keywords)
                finally:
                    metadata_parent.unlink()
                    parked_parent.rename(metadata_parent)
                return
            original_link(source, destination, *arguments, **keywords)

        def fail_after_selection(step: int, _path: Path) -> None:
            if step == 2:
                raise RuntimeError("injected failure after selection publish")

        with mock.patch.object(self.module.os, "link", side_effect=link_during_parent_swap):
            with self.assertRaisesRegex(RuntimeError, "selection publish"):
                self.module.build_freeze(
                    self.synthetic_inputs,
                    self.output_paths,
                    after_publish=fail_after_selection,
                )

        self.assertTrue(swapped)
        self.assertEqual({path.name for path in outside.iterdir()}, {marker.name})
        self.assertFalse(self.output_paths.application_inputs.exists())
        self.assertFalse(self.output_paths.selection_receipt.exists())
        self.assertFalse(tuple(self.work.glob(".*.application-freeze-stage.*")))

    def test_failure_after_staging_publishes_nothing_and_leaves_no_residue(self) -> None:
        self.prepare_freeze_fixture()
        before = fingerprint_tree_no_follow(self.sandbox)
        original_stage = self.module._stage_freeze

        def fail_after_stage(stage: Path, model: object) -> object:
            original_stage(stage, model)
            raise RuntimeError("injected post-stage validation failure")

        with mock.patch.object(self.module, "_stage_freeze", side_effect=fail_after_stage):
            with self.assertRaisesRegex(RuntimeError, "post-stage validation failure"):
                self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)
        self.assertFalse(tuple(self.work.glob(".*.application-freeze-stage.*")))

    def test_transient_descriptor_relative_stage_cleanup_failure_is_retried(self) -> None:
        self.prepare_freeze_fixture()
        original_cleanup = self.module._remove_staging_tree_contents
        injected = False

        def fail_first_stage_cleanup(
            directory_descriptor: int,
            prefix: tuple[str, ...] = (),
        ) -> None:
            nonlocal injected
            if not prefix and not injected:
                injected = True
                raise OSError("injected staging cleanup failure")
            original_cleanup(directory_descriptor, prefix)

        with mock.patch.object(
            self.module,
            "_remove_staging_tree_contents",
            side_effect=fail_first_stage_cleanup,
        ):
            result = self.module.build_freeze(self.synthetic_inputs, self.output_paths)

        self.assertTrue(injected)
        self.assertEqual(
            result["freeze_id"],
            "bioinformatics-phase3-application-v1-06dbae75",
        )
        self.assertTrue(self.output_paths.application_inputs.is_dir())
        self.assertTrue(self.output_paths.input_summary.is_file())
        self.assertFalse(tuple(self.work.glob(".*.application-freeze-stage.*")))

    def test_corrupted_complete_stage_is_revalidated_before_publication(self) -> None:
        self.prepare_freeze_fixture()
        original_stage = self.module._stage_freeze
        for corruption in ("fasta", "summary"):
            with self.subTest(corruption=corruption):
                outputs = self.freeze_paths_for_repository(f"corrupt-stage-{corruption}")
                before = fingerprint_tree_no_follow(outputs.repository_root)

                def corrupt_stage(
                    stage: object,
                    model: object,
                ) -> dict[str, tuple[str, ...]]:
                    staged = original_stage(stage, model)
                    def overwrite(
                        relative: tuple[str, ...],
                        content: bytes,
                        *,
                        append: bool = False,
                    ) -> None:
                        parent = self.module._open_relative_directory(
                            stage.root_descriptor,
                            relative[:-1],
                        )
                        descriptor = os.open(
                            relative[-1],
                            os.O_WRONLY
                            | getattr(os, "O_NOFOLLOW", 0)
                            | (os.O_APPEND if append else os.O_TRUNC),
                            dir_fd=parent,
                        )
                        try:
                            self.assertEqual(os.write(descriptor, content), len(content))
                            os.fsync(descriptor)
                        finally:
                            os.close(descriptor)
                            os.close(parent)

                    if corruption == "fasta":
                        target = next(
                            relative
                            for relative in sorted(model.application_files)
                            if relative.startswith("targets/")
                        )
                        overwrite(
                            ("application_inputs", *Path(target).parts),
                            b"A\n",
                            append=True,
                        )
                    else:
                        overwrite(
                            staged["input summary"],
                            b"freeze_id\tmanifest_sha256\ncorrupt\tcorrupt\n",
                        )
                    return staged

                with mock.patch.object(
                    self.module,
                    "_stage_freeze",
                    side_effect=corrupt_stage,
                ):
                    with self.assertRaisesRegex(ValueError, "staged .* validation"):
                        self.module.build_freeze(self.synthetic_inputs, outputs)
                self.assertEqual(
                    fingerprint_tree_no_follow(outputs.repository_root),
                    before,
                )
                self.assertFalse(
                    tuple(self.work.glob(".*.application-freeze-stage.*"))
                )

    def test_symlink_destination_parent_and_tree_entry_are_rejected_no_follow(self) -> None:
        self.prepare_freeze_fixture()
        external = self.work / "external"
        external.mkdir()

        destination_outputs = self.freeze_paths_for_repository("symlink-destination")
        destination_outputs.application_inputs.parent.mkdir(parents=True)
        destination_outputs.application_inputs.symlink_to(external, target_is_directory=True)
        before = fingerprint_tree_no_follow(destination_outputs.repository_root)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            self.module.build_freeze(self.synthetic_inputs, destination_outputs)
        self.assertEqual(
            fingerprint_tree_no_follow(destination_outputs.repository_root),
            before,
        )

        parent_outputs = self.freeze_paths_for_repository(
            "symlink-parent",
            create_paper=False,
        )
        (parent_outputs.repository_root / "paper").symlink_to(
            external,
            target_is_directory=True,
        )
        before = fingerprint_tree_no_follow(parent_outputs.repository_root)
        with self.assertRaisesRegex(ValueError, "symbolic link component"):
            self.module.build_freeze(self.synthetic_inputs, parent_outputs)
        self.assertEqual(
            fingerprint_tree_no_follow(parent_outputs.repository_root),
            before,
        )

        self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        target = next((self.output_paths.application_inputs / "targets").glob("*.fa"))
        target.unlink()
        target.symlink_to(external / "missing.fa")
        before = fingerprint_tree_no_follow(self.sandbox)
        with self.assertRaisesRegex(ValueError, "existing application input tree drift"):
            self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_colliding_aliased_and_outside_destinations_fail_closed(self) -> None:
        self.prepare_freeze_fixture()
        invalid_outputs = (
            replace(
                self.output_paths,
                manifest=self.output_paths.selection_receipt,
            ),
            replace(
                self.output_paths,
                input_summary=self.work / "outside-summary.tsv",
            ),
            replace(
                self.output_paths,
                manifest=self.output_paths.application_inputs / "nested.tsv",
            ),
            replace(
                self.output_paths,
                source_ledger=self.output_paths.manifest,
            ),
        )
        for outputs in invalid_outputs:
            with self.subTest(outputs=outputs):
                before = fingerprint_tree_no_follow(self.sandbox)
                with self.assertRaisesRegex(ValueError, "collision|outside repository"):
                    self.module.build_freeze(self.synthetic_inputs, outputs)
                self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

        alias_outputs = self.freeze_paths_for_repository("hardlink-alias")
        alias_outputs.selection_receipt.write_bytes(b"alias")
        os.link(alias_outputs.selection_receipt, alias_outputs.manifest)
        before = fingerprint_tree_no_follow(alias_outputs.repository_root)
        with self.assertRaisesRegex(ValueError, "output path alias"):
            self.module.build_freeze(self.synthetic_inputs, alias_outputs)
        self.assertEqual(
            fingerprint_tree_no_follow(alias_outputs.repository_root),
            before,
        )

    def test_metadata_destinations_must_match_canonical_repository_paths(self) -> None:
        self.prepare_freeze_fixture()
        mutations = {
            "selection": lambda outputs: replace(
                outputs,
                selection_receipt=outputs.selection_receipt.with_name("selection.json"),
            ),
            "manifest": lambda outputs: replace(
                outputs,
                manifest=outputs.repository_root / "paper/application_manifest.tsv",
            ),
            "checksum": lambda outputs: replace(
                outputs,
                manifest_checksum=outputs.repository_root / "application_manifest.sha256",
            ),
            "sources": lambda outputs: replace(
                outputs,
                source_ledger=outputs.source_ledger.with_name("sources.tsv"),
            ),
            "summary": lambda outputs: replace(
                outputs,
                input_summary=outputs.input_summary.with_name("summary.tsv"),
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                outputs = mutate(self.freeze_paths_for_repository(f"canonical-{name}"))
                before = fingerprint_tree_no_follow(outputs.repository_root)
                with self.assertRaisesRegex(ValueError, "canonical output path"):
                    self.module.build_freeze(self.synthetic_inputs, outputs)
                self.assertEqual(
                    fingerprint_tree_no_follow(outputs.repository_root),
                    before,
                )

    def test_initial_build_validation_stays_bound_to_locked_repository_descriptor(self) -> None:
        self.prepare_freeze_fixture()
        original_preflight = self.module._preflight_existing

        initial_outputs = self.freeze_paths_for_repository("locked-build-initial")
        initial_alternate = self.freeze_paths_for_repository("locked-build-initial-alt")
        self.module.build_freeze(self.synthetic_inputs, initial_alternate)
        initial_parked = self.work / "locked-build-initial-parked"
        initial_swapped = False

        def swap_only_during_initial_preflight(
            *arguments: object,
            **keywords: object,
        ) -> object:
            nonlocal initial_swapped
            if not initial_swapped:
                initial_swapped = True
                initial_outputs.repository_root.rename(initial_parked)
                initial_alternate.repository_root.rename(initial_outputs.repository_root)
                try:
                    return original_preflight(*arguments, **keywords)
                finally:
                    initial_outputs.repository_root.rename(
                        initial_alternate.repository_root
                    )
                    initial_parked.rename(initial_outputs.repository_root)
            return original_preflight(*arguments, **keywords)

        with mock.patch.object(
            self.module,
            "_preflight_existing",
            side_effect=swap_only_during_initial_preflight,
        ):
            self.module.build_freeze(self.synthetic_inputs, initial_outputs)
        self.assertTrue(initial_swapped)
        self.assertTrue(initial_outputs.application_inputs.is_dir())
        self.assertTrue(initial_outputs.input_summary.is_file())

    def test_final_build_validation_stays_bound_to_locked_repository_descriptor(self) -> None:
        self.prepare_freeze_fixture()
        original_preflight = self.module._preflight_existing
        final_outputs = self.freeze_paths_for_repository("locked-build-final")
        final_alternate = self.freeze_paths_for_repository("locked-build-final-alt")
        self.module.build_freeze(self.synthetic_inputs, final_alternate)
        final_parked = self.work / "locked-build-final-parked"
        final_preflight_calls = 0
        final_swapped = False
        before = fingerprint_tree_no_follow(final_outputs.repository_root)

        def swap_only_during_final_preflight(
            *arguments: object,
            **keywords: object,
        ) -> object:
            nonlocal final_preflight_calls, final_swapped
            final_preflight_calls += 1
            if final_preflight_calls == 2:
                final_swapped = True
                final_outputs.repository_root.rename(final_parked)
                final_alternate.repository_root.rename(final_outputs.repository_root)
                try:
                    return original_preflight(*arguments, **keywords)
                finally:
                    final_outputs.repository_root.rename(final_alternate.repository_root)
                    final_parked.rename(final_outputs.repository_root)
            return original_preflight(*arguments, **keywords)

        def corrupt_created_manifest(step: int, _path: Path) -> None:
            if step == 5:
                final_outputs.manifest.write_text("corrupt\n", encoding="ascii")

        with mock.patch.object(
            self.module,
            "_preflight_existing",
            side_effect=swap_only_during_final_preflight,
        ):
            with self.assertRaisesRegex(ValueError, "drift|incomplete"):
                self.module.build_freeze(
                    self.synthetic_inputs,
                    final_outputs,
                    after_publish=corrupt_created_manifest,
                )
        self.assertTrue(final_swapped)
        self.assertEqual(fingerprint_tree_no_follow(final_outputs.repository_root), before)

    def test_final_build_validation_binds_each_retained_tree_inode(self) -> None:
        self.prepare_freeze_fixture()
        outputs = self.freeze_paths_for_repository("retained-tree-final")
        escaped = outputs.application_inputs.parent / "escaped-created-query.fa"
        replacement_path: Path | None = None
        expected_content: bytes | None = None

        def move_created_inode_and_install_exact_replacement(
            step: int,
            _path: Path,
        ) -> None:
            nonlocal replacement_path, expected_content
            if step == 5:
                replacement_path = next(
                    (outputs.application_inputs / "queries").glob("*.fa")
                )
                expected_content = replacement_path.read_bytes()
                replacement_path.rename(escaped)
                replacement_path.write_bytes(expected_content)

        with self.assertRaisesRegex(RuntimeError, "transaction recovery failed"):
            self.module.build_freeze(
                self.synthetic_inputs,
                outputs,
                after_publish=move_created_inode_and_install_exact_replacement,
            )
        self.assertIsNotNone(replacement_path)
        self.assertIsNotNone(expected_content)
        assert replacement_path is not None
        assert expected_content is not None
        self.assertEqual(replacement_path.read_bytes(), expected_content)
        self.assertEqual(escaped.read_bytes(), expected_content)

    def test_final_tree_read_rebinds_names_after_retained_identity_pass(self) -> None:
        self.prepare_freeze_fixture()
        outputs = self.freeze_paths_for_repository("retained-tree-read-window")
        escaped = outputs.application_inputs.parent / "escaped-after-identity-pass.fa"
        original_verify = self.module._verify_retained_tree_entries
        replacement_path: Path | None = None
        expected_content: bytes | None = None
        replaced = False

        def verify_then_replace_exact_bytes(
            root_descriptor: int,
            captured: object,
        ) -> None:
            nonlocal replacement_path, expected_content, replaced
            original_verify(root_descriptor, captured)
            if not replaced:
                replacement_path = next(
                    (outputs.application_inputs / "queries").glob("*.fa")
                )
                expected_content = replacement_path.read_bytes()
                replacement_path.rename(escaped)
                replacement_path.write_bytes(expected_content)
                replaced = True

        with mock.patch.object(
            self.module,
            "_verify_retained_tree_entries",
            side_effect=verify_then_replace_exact_bytes,
        ):
            with self.assertRaisesRegex(RuntimeError, "transaction recovery failed"):
                self.module.build_freeze(self.synthetic_inputs, outputs)
        self.assertTrue(replaced)
        self.assertIsNotNone(replacement_path)
        self.assertIsNotNone(expected_content)
        assert replacement_path is not None
        assert expected_content is not None
        self.assertEqual(replacement_path.read_bytes(), expected_content)
        self.assertEqual(escaped.read_bytes(), expected_content)

    def test_initial_select_validation_stays_bound_to_locked_repository_descriptor(self) -> None:
        self.prepare_freeze_fixture()
        original_read_existing = self.module._read_existing_output_file

        initial_outputs = self.freeze_paths_for_repository("locked-select-initial")
        initial_outputs.selection_receipt.write_text("drift\n", encoding="ascii")
        initial_alternate = self.freeze_paths_for_repository("locked-select-initial-alt")
        self.module.select_freeze(self.synthetic_inputs, initial_alternate)
        initial_parked = self.work / "locked-select-initial-parked"
        initial_swapped = False

        def read_during_initial_root_swap(
            *arguments: object,
            **keywords: object,
        ) -> bytes:
            nonlocal initial_swapped
            if not initial_swapped:
                initial_swapped = True
                initial_outputs.repository_root.rename(initial_parked)
                initial_alternate.repository_root.rename(initial_outputs.repository_root)
                try:
                    return original_read_existing(*arguments, **keywords)
                finally:
                    initial_outputs.repository_root.rename(
                        initial_alternate.repository_root
                    )
                    initial_parked.rename(initial_outputs.repository_root)
            return original_read_existing(*arguments, **keywords)

        with mock.patch.object(
            self.module,
            "_read_existing_output_file",
            side_effect=read_during_initial_root_swap,
        ):
            with self.assertRaisesRegex(ValueError, "selection receipt drift"):
                self.module.select_freeze(self.synthetic_inputs, initial_outputs)
        self.assertTrue(initial_swapped)
        self.assertEqual(
            initial_outputs.selection_receipt.read_text(encoding="ascii"),
            "drift\n",
        )

    def test_final_select_validation_stays_bound_to_locked_repository_descriptor(self) -> None:
        self.prepare_freeze_fixture()
        original_read_existing = self.module._read_existing_output_file
        final_outputs = self.freeze_paths_for_repository("locked-select-final")
        final_alternate = self.freeze_paths_for_repository("locked-select-final-alt")
        self.module.select_freeze(self.synthetic_inputs, final_alternate)
        final_parked = self.work / "locked-select-final-parked"
        original_publish = self.module._publish_staged
        final_swapped = False
        published_then_corrupted = False
        before = fingerprint_tree_no_follow(final_outputs.repository_root)

        def publish_then_corrupt(*arguments: object, **keywords: object) -> object:
            nonlocal published_then_corrupted
            result = original_publish(*arguments, **keywords)
            final_outputs.selection_receipt.write_text("corrupt\n", encoding="ascii")
            published_then_corrupted = True
            return result

        def read_during_final_root_swap(
            *arguments: object,
            **keywords: object,
        ) -> bytes:
            nonlocal final_swapped
            if published_then_corrupted and not final_swapped:
                final_swapped = True
                final_outputs.repository_root.rename(final_parked)
                final_alternate.repository_root.rename(final_outputs.repository_root)
                try:
                    return original_read_existing(*arguments, **keywords)
                finally:
                    final_outputs.repository_root.rename(final_alternate.repository_root)
                    final_parked.rename(final_outputs.repository_root)
            return original_read_existing(*arguments, **keywords)

        with mock.patch.object(
            self.module,
            "_publish_staged",
            side_effect=publish_then_corrupt,
        ), mock.patch.object(
            self.module,
            "_read_existing_output_file",
            side_effect=read_during_final_root_swap,
        ):
            with self.assertRaisesRegex(ValueError, "selection receipt.*drift"):
                self.module.select_freeze(self.synthetic_inputs, final_outputs)
        self.assertTrue(published_then_corrupted)
        self.assertTrue(final_swapped)
        self.assertEqual(fingerprint_tree_no_follow(final_outputs.repository_root), before)

    def test_success_rejects_persistent_repository_root_replacement_and_rolls_back(
        self,
    ) -> None:
        self.prepare_freeze_fixture()
        original_publish = self.module._publish_staged

        for operation in ("build", "select"):
            with self.subTest(operation=operation):
                outputs = self.freeze_paths_for_repository(f"persistent-root-{operation}")
                before = fingerprint_tree_no_follow(outputs.repository_root)
                parked = self.work / f"persistent-root-{operation}-parked"
                marker = outputs.repository_root / "replacement-marker.txt"
                replaced = False

                def replace_repository_root() -> None:
                    nonlocal replaced
                    if replaced:
                        return
                    outputs.repository_root.rename(parked)
                    outputs.repository_root.mkdir()
                    marker.write_text("unrelated replacement\n", encoding="ascii")
                    replaced = True

                def replace_after_first_publish(step: int, _path: Path) -> None:
                    if step == 1:
                        replace_repository_root()

                def publish_then_replace(
                    *arguments: object,
                    **keywords: object,
                ) -> object:
                    result = original_publish(*arguments, **keywords)
                    replace_repository_root()
                    return result

                context = (
                    mock.patch.object(
                        self.module,
                        "_publish_staged",
                        side_effect=publish_then_replace,
                    )
                    if operation == "select"
                    else nullcontext()
                )
                with context:
                    with self.assertRaisesRegex(ValueError, "repository root identity changed"):
                        if operation == "build":
                            self.module.build_freeze(
                                self.synthetic_inputs,
                                outputs,
                                after_publish=replace_after_first_publish,
                            )
                        else:
                            self.module.select_freeze(self.synthetic_inputs, outputs)

                self.assertTrue(replaced)
                self.assertEqual(marker.read_text(encoding="ascii"), "unrelated replacement\n")
                self.assertEqual(
                    fingerprint_tree_no_follow(parked),
                    before,
                    "publication was not rolled back through retained parents",
                )
                self.assertFalse(outputs.application_inputs.exists())
                self.assertFalse(outputs.selection_receipt.exists())

    def test_noop_rejects_persistent_repository_root_replacement(self) -> None:
        self.prepare_freeze_fixture()
        original_preflight = self.module._preflight_existing
        original_read_existing = self.module._read_existing_output_file

        for operation in ("build", "select"):
            with self.subTest(operation=operation):
                outputs = self.freeze_paths_for_repository(f"persistent-noop-{operation}")
                if operation == "build":
                    self.module.build_freeze(self.synthetic_inputs, outputs)
                else:
                    self.module.select_freeze(self.synthetic_inputs, outputs)
                before = fingerprint_tree_no_follow(outputs.repository_root)
                parked = self.work / f"persistent-noop-{operation}-parked"
                marker = outputs.repository_root / "replacement-marker.txt"
                replaced = False

                def replace_repository_root() -> None:
                    nonlocal replaced
                    if replaced:
                        return
                    outputs.repository_root.rename(parked)
                    outputs.repository_root.mkdir()
                    marker.write_text("unrelated replacement\n", encoding="ascii")
                    replaced = True

                def preflight_then_replace(
                    *arguments: object,
                    **keywords: object,
                ) -> object:
                    result = original_preflight(*arguments, **keywords)
                    if not result:
                        replace_repository_root()
                    return result

                def read_then_replace(
                    *arguments: object,
                    **keywords: object,
                ) -> object:
                    result = original_read_existing(*arguments, **keywords)
                    if result is not None:
                        replace_repository_root()
                    return result

                patcher = mock.patch.object(
                    self.module,
                    "_preflight_existing" if operation == "build" else "_read_existing_output_file",
                    side_effect=preflight_then_replace if operation == "build" else read_then_replace,
                )
                with patcher:
                    with self.assertRaisesRegex(ValueError, "repository root identity changed"):
                        if operation == "build":
                            self.module.build_freeze(self.synthetic_inputs, outputs)
                        else:
                            self.module.select_freeze(self.synthetic_inputs, outputs)

                self.assertTrue(replaced)
                self.assertEqual(marker.read_text(encoding="ascii"), "unrelated replacement\n")
                self.assertEqual(fingerprint_tree_no_follow(parked), before)

    def test_concurrent_identical_builds_publish_one_complete_freeze(self) -> None:
        self.prepare_freeze_fixture()
        callback_steps: list[tuple[int, Path]] = []

        def build() -> dict[str, object]:
            return self.module.build_freeze(
                self.synthetic_inputs,
                self.output_paths,
                after_publish=lambda step, path: callback_steps.append((step, path)),
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(build) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]

        self.assertEqual(results[0], results[1])
        self.assertEqual(
            [step for step, _path in callback_steps],
            [1, 2, 3, 4, 5, 6],
        )
        self.assertEqual(len(read_tsv(self.output_paths.manifest)), 350)
        self.assertEqual(
            len(list(self.output_paths.application_inputs.rglob("*.fa"))),
            350,
        )

    def test_multiprocess_publishers_are_serialized_before_preflight(self) -> None:
        self.prepare_freeze_fixture()
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("forced publication interleaving requires multiprocessing fork")
        context = multiprocessing.get_context("fork")
        first_step = context.Event()
        release = context.Event()
        first_done = context.Event()
        second_done = context.Event()
        results = context.Queue()
        first = context.Process(
            target=build_freeze_process,
            args=(
                self.module,
                self.synthetic_inputs,
                self.output_paths,
                True,
                first_step,
                release,
                first_done,
                results,
            ),
        )
        second = context.Process(
            target=build_freeze_process,
            args=(
                self.module,
                self.synthetic_inputs,
                self.output_paths,
                False,
                first_step,
                release,
                second_done,
                results,
            ),
        )
        try:
            first.start()
            self.assertTrue(first_step.wait(10), "first publisher never reached step one")
            second.start()
            second_finished_while_first_paused = second_done.wait(1)
            release.set()
            first.join(15)
            second.join(15)
            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
        finally:
            release.set()
            for process in (first, second):
                if process.is_alive():
                    process.terminate()
                process.join(5)

        self.assertFalse(
            second_finished_while_first_paused,
            "second process crossed preflight while the first publication was incomplete",
        )
        observed = sorted((results.get(timeout=5), results.get(timeout=5)))
        self.assertEqual([row[0] for row in observed], ["ok", "ok"])
        self.assertTrue(self.output_paths.application_inputs.is_dir())
        self.assertTrue(self.output_paths.selection_receipt.is_file())
        self.assertTrue(self.output_paths.manifest.is_file())
        self.assertTrue(self.output_paths.manifest_checksum.is_file())
        self.assertTrue(self.output_paths.source_ledger.is_file())
        self.assertTrue(self.output_paths.input_summary.is_file())
        self.assertEqual(len(read_tsv(self.output_paths.manifest)), 350)

    def test_materialize_receipt_and_publication_use_one_source_snapshot(self) -> None:
        self.prepare_freeze_fixture()
        self.module.select_freeze(self.synthetic_inputs, self.output_paths)
        expected_receipt = self.output_paths.selection_receipt.read_bytes()
        materialize_outputs = self.freeze_paths_for_repository("snapshot-materialize")
        self.output_paths = materialize_outputs
        original_prepare = self.module._prepare_freeze
        prepare_count = 0

        def prepare_then_mutate(inputs: object, outputs: object) -> object:
            nonlocal prepare_count
            model = original_prepare(inputs, outputs)
            prepare_count += 1
            if prepare_count == 1:
                with inputs.lncrna_fasta.open("ab") as handle:
                    handle.write(b"\n")
            return model

        with mock.patch.object(
            self.module,
            "_prepare_freeze",
            side_effect=prepare_then_mutate,
        ), mock.patch.object(
            self.module,
            "SOURCE_SPECS",
            self.synthetic_inputs.source_specs,
        ), mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(
                self.module.main(
                    [
                        "materialize",
                        *self.freeze_cli_arguments(),
                        "--selection",
                        str(self.work / "repository/paper/bioinformatics/application_selection.json"),
                    ]
                ),
                0,
            )
        self.assertEqual(prepare_count, 1)
        self.assertEqual(materialize_outputs.selection_receipt.read_bytes(), expected_receipt)

    def test_source_change_during_reconstruction_publishes_nothing(self) -> None:
        self.prepare_freeze_fixture()
        original_select_targets = self.module._select_targets_streaming
        original_source = self.synthetic_inputs.lncrna_fasta.read_bytes()
        before = fingerprint_tree_no_follow(self.sandbox)

        def select_then_mutate(**arguments: object) -> object:
            selected = original_select_targets(**arguments)
            with self.synthetic_inputs.lncrna_fasta.open("ab") as handle:
                handle.write(b"\n")
            return selected

        try:
            with mock.patch.object(
                self.module,
                "_select_targets_streaming",
                side_effect=select_then_mutate,
            ):
                with self.assertRaisesRegex(ValueError, "source changed during reconstruction"):
                    self.module.build_freeze(self.synthetic_inputs, self.output_paths)
            self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)
        finally:
            self.synthetic_inputs.lncrna_fasta.write_bytes(original_source)

    def test_source_parent_replacement_only_during_read_publishes_nothing(self) -> None:
        self.prepare_freeze_fixture()
        source = self.synthetic_inputs.lncrna_fasta
        source_directory = source.parent
        parked_directory = self.work / "parked-middle-read-sources"
        alternate_directory = self.work / "alternate-middle-read-sources"
        alternate_directory.mkdir()
        alternate_content = bytearray(source.read_bytes())
        sequence_offset = alternate_content.index(b"\n") + 1
        alternate_content[sequence_offset] = (
            ord("C") if alternate_content[sequence_offset] != ord("C") else ord("G")
        )
        (alternate_directory / source.name).write_bytes(bytes(alternate_content))
        original_open_text = self.module.open_text
        swapped = False

        @contextmanager
        def open_during_real_parent_replacement(path: object) -> object:
            nonlocal swapped
            snapshot_path = getattr(path, "path", path)
            if snapshot_path == source and not swapped:
                swapped = True
                source_directory.rename(parked_directory)
                alternate_directory.rename(source_directory)
                try:
                    with original_open_text(path) as handle:
                        yield handle
                finally:
                    source_directory.rename(alternate_directory)
                    parked_directory.rename(source_directory)
                return
            with original_open_text(path) as handle:
                yield handle

        before = fingerprint_tree_no_follow(self.sandbox)
        with mock.patch.object(
            self.module,
            "open_text",
            side_effect=open_during_real_parent_replacement,
        ):
            with self.assertRaisesRegex(ValueError, "source .*changed|source parent"):
                self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        self.assertTrue(swapped)
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_source_parent_symlink_swap_is_rejected_by_descriptor_walk(self) -> None:
        self.prepare_freeze_fixture()
        source = self.synthetic_inputs.lncrna_fasta
        source_directory = source.parent
        parked_directory = self.work / "parked-sources"
        alternate_directory = self.work / "alternate-sources"
        alternate_directory.mkdir()
        alternate_content = bytearray(source.read_bytes())
        sequence_offset = alternate_content.index(b"\n") + 1
        alternate_content[sequence_offset] = ord("C") if alternate_content[sequence_offset] != ord("C") else ord("G")
        (alternate_directory / source.name).write_bytes(bytes(alternate_content))
        original_open_text = self.module.open_text
        swapped = False

        @contextmanager
        def open_with_parent_swap(path: object) -> object:
            nonlocal swapped
            snapshot_path = getattr(path, "path", path)
            if snapshot_path == source and not swapped:
                swapped = True
                source_directory.rename(parked_directory)
                source_directory.symlink_to(alternate_directory, target_is_directory=True)
                try:
                    with original_open_text(path) as handle:
                        yield handle
                finally:
                    source_directory.unlink()
                    parked_directory.rename(source_directory)
                return
            with original_open_text(path) as handle:
                yield handle

        before = fingerprint_tree_no_follow(self.sandbox)
        with mock.patch.object(
            self.module,
            "open_text",
            side_effect=open_with_parent_swap,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "source changed|source parent|symbolic link",
            ):
                self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        self.assertTrue(swapped)
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_source_real_parent_substitution_is_rejected_even_for_same_file_inodes(self) -> None:
        self.prepare_freeze_fixture()
        source_directory = self.synthetic_inputs.lncrna_fasta.parent
        alternate_directory = self.work / "alternate-real-sources"
        parked_directory = self.work / "parked-real-sources"
        alternate_directory.mkdir()
        for source in source_directory.iterdir():
            os.link(source, alternate_directory / source.name)
        original_verify = self.module._verify_source_snapshots
        substituted = False

        def verify_with_real_parent_substitution(snapshots: object) -> None:
            nonlocal substituted
            substituted = True
            source_directory.rename(parked_directory)
            alternate_directory.rename(source_directory)
            try:
                original_verify(snapshots)
            finally:
                source_directory.rename(alternate_directory)
                parked_directory.rename(source_directory)

        before = fingerprint_tree_no_follow(self.sandbox)
        with mock.patch.object(
            self.module,
            "_verify_source_snapshots",
            side_effect=verify_with_real_parent_substitution,
        ):
            with self.assertRaisesRegex(ValueError, "source parent changed"):
                self.module.build_freeze(self.synthetic_inputs, self.output_paths)
        self.assertTrue(substituted)
        self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)

    def test_source_contract_is_fixed(self) -> None:
        self.assertEqual(
            self.module.SELECTION_SEED,
            "gasal2-longtarget-phase3-application-v1-20260724",
        )
        self.assertEqual(self.module.ASSEMBLY, "GRCh38")
        self.assertEqual(self.module.ANNOTATION_RELEASE, "GENCODE v49")
        self.assertEqual(
            self.module.PRIMARY_CHROMOSOMES,
            {f"chr{i}" for i in range(1, 23)} | {"chrX"},
        )
        self.assertEqual(self.module.TARGET_CHROMOSOMES, ("chr21", "chr22"))
        self.assertEqual(
            self.module.MANIFEST_FIELDS,
            (
                "record_id",
                "record_role",
                "source_release",
                "assembly",
                "original_gene_id",
                "original_gene_name",
                "original_transcript_id",
                "selection_rule",
                "sequence_length",
                "chromosome",
                "strand",
                "tss",
                "region_start",
                "region_end",
                "sequence_sha256",
                "file_sha256",
                "path",
                "license_note",
                "split",
                "status",
            ),
        )
        self.assertEqual(
            self.module.COMMON,
            {
                "source_release": "GENCODE v49",
                "assembly": "GRCh38",
                "split": "application",
                "status": "preregistered_not_run",
            },
        )
        self.assertEqual(
            self.module.QUERY_LICENSE,
            "GENCODE project data are open access; selected derived FASTA retained with "
            "source attribution; final redistribution approval remains owner-controlled",
        )
        self.assertEqual(
            self.module.TARGET_LICENSE,
            "UCSC data-use conditions and Genome Reference Consortium attribution apply; "
            "selected promoter FASTA retained; final redistribution approval remains owner-controlled",
        )
        self.assertEqual(
            self.module.SUMMARY_FIELDS,
            (
                "freeze_id",
                "manifest_sha256",
                "query_count",
                "target_count",
                "pair_count",
                "query_total_bp",
                "target_total_bp",
                "chr21_target_count",
                "chr22_target_count",
                "min_query_length",
                "max_query_length",
                "annotation_target_candidate_count",
                "excluded_target_count",
            ),
        )

    def test_exact_upstream_source_identities(self) -> None:
        expected_fields = (
            "source_id",
            "role",
            "provider",
            "release",
            "assembly",
            "url",
            "upstream_md5",
            "compressed_size_bytes",
            "compressed_sha256",
            "decompressed_size_bytes",
            "decompressed_sha256",
            "local_source_path",
            "license_or_terms",
            "redistribution_note",
            "download_command",
            "status",
        )
        self.assertEqual(self.module.APPLICATION_SOURCE_FIELDS, expected_fields)
        self.assertEqual(self.module.SOURCE_SPEC_FIELDS, expected_fields[:-1])
        self.assertEqual(
            tuple(field.name for field in fields(self.module.SourceSpec)),
            expected_fields[:-1],
        )
        expected = {
            "gencode_v49_lncrna": {
                "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
                "upstream_md5": "6d52ea2c72933c864e46a560fe0b5d4c",
                "compressed_size_bytes": 37870043,
                "compressed_sha256": "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4",
                "decompressed_size_bytes": 223740848,
                "decompressed_sha256": "4c632018e0198d76fe76471baa5511a1c07af86bf7bab6ce6747edb8d5add5ae",
            },
            "gencode_v49_gtf": {
                "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz",
                "upstream_md5": "0ef4a024ea2d35b1b88c12447b0b70b9",
                "compressed_size_bytes": 93374019,
                "compressed_sha256": "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4",
                "decompressed_size_bytes": 3323462848,
                "decompressed_sha256": "ff32fd55c6799b3b94fe10aa17b2b5d4da952fa1de12fe44afadf32e949ec914",
            },
            "ucsc_hg38_chr21": {
                "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz",
                "upstream_md5": "184df2bd9b812b6e6b6da16c6021369e",
                "compressed_size_bytes": 12709705,
                "compressed_sha256": "c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b",
                "decompressed_size_bytes": 47644190,
                "decompressed_sha256": "35c71b68436d1a278ecb6a1e875af3ba4020738a028a7feac769a6d62790ae1f",
            },
            "ucsc_hg38_chr22": {
                "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz",
                "upstream_md5": "41b47ce1cc21b558409c19b892e1c0d1",
                "compressed_size_bytes": 12255678,
                "compressed_sha256": "05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695",
                "decompressed_size_bytes": 51834845,
                "decompressed_sha256": "ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f",
            },
        }
        actual = {
            source.source_id: {
                field: getattr(source, field)
                for field in (
                    "url",
                    "upstream_md5",
                    "compressed_size_bytes",
                    "compressed_sha256",
                    "decompressed_size_bytes",
                    "decompressed_sha256",
                )
            }
            for source in self.module.SOURCE_SPECS
        }
        self.assertEqual(actual, expected)
        expected_local_paths = (
            ".tmp/bioinformatics_application_sources/gencode.v49.lncRNA_transcripts.fa.gz",
            ".tmp/bioinformatics_application_sources/gencode.v49.annotation.gtf.gz",
            ".tmp/bioinformatics_application_sources/chr21.fa.gz",
            ".tmp/bioinformatics_application_sources/chr22.fa.gz",
        )
        self.assertEqual(
            tuple(source.local_source_path for source in self.module.SOURCE_SPECS),
            expected_local_paths,
        )
        for source in self.module.SOURCE_SPECS:
            with self.subTest(source_command=source.source_id):
                self.assertTrue(
                    source.download_command.startswith("curl -fL --retry 3 --output ")
                )
                self.assertIn(source.url, source.download_command)
                self.assertIn(source.local_source_path, source.download_command)
                for forbidden in (
                    "gasal2_longtarget.py",
                    "run_application.py",
                    "run_holdout.py",
                    "Fasim",
                    "GASAL2",
                    ".paper-artifacts",
                ):
                    self.assertNotIn(forbidden, source.download_command)
        with self.assertRaises(FrozenInstanceError):
            self.module.SOURCE_SPECS[0].source_id = "drift"

    def test_source_specs_cli_emits_only_canonical_tsv(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(BUILDER), "sources"],
            cwd=ROOT,
            pass_fds=AUTHENTICATED_DEPENDENCY_FDS,
            check=False,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(
            completed.stdout,
            self.module._tsv_bytes(
                self.module.SOURCE_SPEC_FIELDS,
                self.module._source_spec_rows(self.module.SOURCE_SPECS),
            ),
        )

    def test_fetch_script_has_no_execution_command(self) -> None:
        self.assertTrue(FETCHER.is_file(), f"application fetcher is missing: {FETCHER}")
        text = FETCHER.read_text(encoding="utf-8", errors="strict")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("curl -fL --retry 3", text)
        self.assertIn("--create-freeze", text)
        self.assertIn(".partial.$$", text)
        self.assertIn("trap ", text)
        self.assertIn('flock -x "$source_directory_fd"', text)
        self.assertIn('cleanup-cache-entry', text)
        self.assertIn('python3 "$BUILDER" sources', text)
        self.assertIn('python3 "$BUILDER" select', text)
        self.assertIn('python3 "$BUILDER" verify', text)
        self.assertIn('python3 "$BUILDER" materialize', text)
        self.assertIn(
            'SOURCE_DIR="$ROOT/.tmp/bioinformatics_application_sources"',
            text,
        )
        self.assertNotIn('${SOURCE_DIR:-', text)
        self.assertNotIn("eval ", text)
        for source in self.module.SOURCE_SPECS:
            self.assertNotIn(source.compressed_sha256, text)
            self.assertNotIn(source.decompressed_sha256, text)
        for forbidden in (
            "gasal2_longtarget.py",
            "run_application.py",
            "run_holdout.py",
            "Fasim",
            "GASAL2",
            ".paper-artifacts",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_fetch_default_requires_all_committed_outputs_without_network(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        completed = self.run_fetch_harness(harness)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("committed application freeze output is missing", completed.stderr)
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertFalse(Path(harness["python_log"]).exists())

    def test_fetch_rejects_source_directory_override_before_acquisition(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=True,
        )
        redirected = Path(harness["repository"]) / "redirected-source-cache"
        environment = dict(harness["environment"])
        environment["SOURCE_DIR"] = str(redirected)

        completed = self.run_fetch_harness(
            harness,
            "--create-freeze",
            environment=environment,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("SOURCE_DIR override is not supported", completed.stderr)
        self.assertFalse(redirected.exists())
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertFalse(Path(harness["python_log"]).exists())

    def test_fetch_rejects_unsafe_cache_parent_before_sources_or_curl(self) -> None:
        for component in ("temporary_parent", "source_cache"):
            for entry_kind in ("symlink", "regular_file"):
                with self.subTest(component=component, entry_kind=entry_kind):
                    harness = self.prepare_fetch_harness(
                        committed_outputs=False,
                        valid_cache=False,
                    )
                    repository = Path(harness["repository"])
                    unsafe_entry = (
                        repository / ".tmp"
                        if component == "temporary_parent"
                        else Path(harness["source_directory"])
                    )
                    shutil.rmtree(unsafe_entry)
                    outside = self.work / f"outside-{component}-{entry_kind}"
                    if entry_kind == "symlink":
                        outside.mkdir()
                        unsafe_entry.symlink_to(outside, target_is_directory=True)
                    else:
                        unsafe_entry.write_text("not a directory\n", encoding="ascii")
                    environment = dict(harness["environment"])
                    environment.update(
                        {
                            "FETCH_CURL_MODE": "valid",
                            "FETCH_CURL_STATUS": "0",
                        }
                    )

                    completed = self.run_fetch_harness(
                        harness,
                        "--create-freeze",
                        environment=environment,
                    )

                    self.assertNotEqual(completed.returncode, 0)
                    expected_error = (
                        "source cache parent is unsafe"
                        if component == "temporary_parent"
                        else "source cache is unsafe"
                    )
                    self.assertIn(expected_error, completed.stderr)
                    self.assertFalse(Path(harness["curl_log"]).exists())
                    self.assertFalse(Path(harness["python_log"]).exists())
                    if entry_kind == "symlink":
                        self.assertEqual(tuple(outside.iterdir()), ())

    def test_fetch_rejects_cache_parent_replacement_after_sources(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        repository = Path(harness["repository"])
        outside = self.work / "outside-cache-parent-after-sources"
        outside.mkdir()
        parked = self.work / "parked-cache-parent-after-sources"
        environment = dict(harness["environment"])
        environment.update(
            {
                "FETCH_CURL_MODE": "valid",
                "FETCH_CURL_STATUS": "0",
                "FETCH_SWAP_CACHE_PARENT_DURING_SOURCES": str(repository / ".tmp"),
                "FETCH_PARKED_CACHE_PARENT": str(parked),
                "FETCH_OUTSIDE_CACHE_PARENT": str(outside),
                "FETCH_REAL_MV": str(shutil.which("mv")),
                "FETCH_REAL_LN": str(shutil.which("ln")),
            }
        )

        completed = self.run_fetch_harness(
            harness,
            "--create-freeze",
            environment=environment,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("source cache binding changed", completed.stderr)
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources"],
        )
        self.assertEqual(tuple(outside.iterdir()), ())

    def test_fetch_rechecks_cache_binding_after_final_verification(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=True,
            valid_cache=True,
        )
        repository = Path(harness["repository"])
        outside = self.work / "outside-cache-parent-after-verify"
        outside.mkdir()
        parked = self.work / "parked-cache-parent-after-verify"
        environment = dict(harness["environment"])
        environment.update(
            {
                "FETCH_SWAP_CACHE_PARENT_AFTER_COMMAND": "verify",
                "FETCH_SWAP_CACHE_PARENT": str(repository / ".tmp"),
                "FETCH_PARKED_CACHE_PARENT": str(parked),
                "FETCH_OUTSIDE_CACHE_PARENT": str(outside),
                "FETCH_REAL_MV": str(shutil.which("mv")),
                "FETCH_REAL_LN": str(shutil.which("ln")),
            }
        )

        completed = self.run_fetch_harness(harness, environment=environment)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("source cache binding changed after reconstruction", completed.stderr)
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "select", "verify"],
        )
        self.assertEqual(tuple(outside.iterdir()), ())

    def test_fetch_serializes_cache_users_with_retained_directory_lock(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        entered = Path(harness["repository"]) / "sources-entered"
        release = Path(harness["repository"]) / "sources-release"
        environment = dict(harness["environment"])
        environment.update(
            {
                "FETCH_PAUSE_DURING_SOURCES": "1",
                "FETCH_SOURCES_ENTERED": str(entered),
                "FETCH_SOURCES_RELEASE": str(release),
                "FETCH_REAL_SLEEP": str(shutil.which("sleep")),
            }
        )
        command = [
            "/bin/bash",
            str(harness["fetcher"]),
            "--create-freeze",
        ]
        first: subprocess.Popen[str] | None = None
        second: subprocess.Popen[str] | None = None
        first_result: tuple[str, str] | None = None
        second_result: tuple[str, str] | None = None
        try:
            first = subprocess.Popen(
                command,
                cwd=Path(harness["repository"]),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deadline = time.monotonic() + 5
            while not entered.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(entered.exists(), "first fetch never entered sources")

            second = subprocess.Popen(
                command,
                cwd=Path(harness["repository"]),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                second.wait(timeout=0.3)
            self.assertEqual(
                Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
                ["sources"],
            )
        finally:
            release.touch()
            for process_name, process in (("first", first), ("second", second)):
                if process is None:
                    continue
                try:
                    result = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    result = process.communicate(timeout=5)
                if process_name == "first":
                    first_result = result
                else:
                    second_result = result

        self.assertIsNotNone(first_result)
        self.assertIsNotNone(second_result)
        self.assertNotEqual(first.returncode, 0)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "sources"],
        )

    def test_fetch_default_reuses_valid_cache_and_verifies_only(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=True,
            valid_cache=True,
        )
        completed = self.run_fetch_harness(harness)
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "select", "verify"],
        )
        self.assertEqual(tuple(Path(harness["temporary_directory"]).iterdir()), ())

    def test_fetch_default_selection_repository_has_owned_staging_parent(
        self,
    ) -> None:
        self.assertNotEqual(os.stat("/tmp").st_uid, os.geteuid())
        harness = self.prepare_fetch_harness(
            committed_outputs=True,
            valid_cache=True,
        )
        output_paths = {
            label: Path(path)
            for label, path in dict(harness["output_paths"]).items()
        }
        outputs_before = {
            label: fingerprint_tree_no_follow(path)
            for label, path in output_paths.items()
        }
        source_directory = Path(harness["source_directory"])
        cache_before = fingerprint_tree_no_follow(source_directory)
        temporary_patterns = (
            "bioinformatics-application-selection.*",
            "bioinformatics-application-sources.*.tsv",
        )

        def temporary_entries() -> set[Path]:
            return {
                path
                for pattern in temporary_patterns
                for path in Path("/tmp").glob(pattern)
            }

        temporary_before = temporary_entries()
        selection_repository_log = (
            Path(harness["repository"]) / "selection-repository.log"
        )
        environment = dict(harness["environment"])
        environment.pop("TMPDIR", None)
        environment.update(
            {
                "FETCH_CHECK_SELECTION_PARENT": "1",
                "FETCH_REAL_BUILDER": str(BUILDER),
                "FETCH_REAL_PYTHON": sys.executable,
                "FETCH_SELECTION_REPOSITORY_LOG": str(selection_repository_log),
            }
        )

        completed = self.run_fetch_harness(harness, environment=environment)

        self.assertTrue(selection_repository_log.is_file())
        selection_repository = Path(
            selection_repository_log.read_text(encoding="ascii").strip()
        )
        self.assertFalse(selection_repository.exists())
        self.assertEqual(temporary_entries(), temporary_before)
        self.assertEqual(
            {
                label: fingerprint_tree_no_follow(path)
                for label, path in output_paths.items()
            },
            outputs_before,
        )
        self.assertEqual(
            fingerprint_tree_no_follow(source_directory),
            cache_before,
        )
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "select", "verify"],
        )

    def test_fetch_default_never_recreates_output_removed_after_precheck(
        self,
    ) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=True,
            valid_cache=True,
        )
        source_ledger = Path(dict(harness["output_paths"])["source_ledger"])
        environment = dict(harness["environment"])
        environment["FETCH_REMOVE_DURING_SOURCES"] = str(source_ledger)

        completed = self.run_fetch_harness(harness, environment=environment)

        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(source_ledger.exists())
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "select", "verify"],
        )

    def test_fetch_default_rejects_committed_selection_drift_before_verify(
        self,
    ) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=True,
            valid_cache=True,
        )
        selection = dict(harness["output_paths"])["selection_receipt"]
        Path(selection).write_text("drift\n", encoding="ascii")
        completed = self.run_fetch_harness(harness)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("committed application selection receipt drift", completed.stderr)
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "select"],
        )

    def test_fetch_cleans_pid_partial_after_curl_failure(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        completed = self.run_fetch_harness(harness, "--create-freeze")
        self.assertNotEqual(completed.returncode, 0)
        curl_log = Path(harness["curl_log"])
        self.assertTrue(curl_log.is_file())
        self.assertIn("-fL --retry 3 --output", curl_log.read_text(encoding="ascii"))
        self.assertFalse(
            tuple(Path(harness["source_directory"]).glob("*.partial.*")),
        )
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources"],
        )
        self.assertEqual(tuple(Path(harness["temporary_directory"]).iterdir()), ())

    def test_fetch_cleans_new_cache_after_post_move_verification_failure(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        real_sha256sum = shutil.which("sha256sum")
        self.assertIsNotNone(real_sha256sum)
        first_source = self.module.SOURCE_SPECS[0]
        destination = Path(harness["source_directory"]) / Path(
            first_source.local_source_path
        ).name
        fake_sha256sum = Path(harness["fake_bin"]) / "sha256sum"
        fake_sha256sum.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "actual_path=''\n"
            "if (($#)); then actual_path=\"${!#}\"; fi\n"
            "if [[ \"${actual_path##*/}\" == \"$FAIL_SHA256_NAME\" ]]; then\n"
            "  printf '%064d  %s\\n' 0 \"${!#}\"\n"
            "  exit 0\n"
            "fi\n"
            "exec \"$REAL_SHA256SUM\" \"$@\"\n",
            encoding="ascii",
        )
        fake_sha256sum.chmod(0o755)
        environment = dict(harness["environment"])
        environment.update(
            {
                "FETCH_CURL_MODE": "valid",
                "FETCH_CURL_STATUS": "0",
                "REAL_SHA256SUM": str(real_sha256sum),
                "FAIL_SHA256_NAME": destination.name,
            }
        )

        completed = self.run_fetch_harness(
            harness,
            "--create-freeze",
            environment=environment,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("published source cache identity mismatch", completed.stderr)
        self.assertFalse(destination.exists())
        self.assertFalse(
            tuple(Path(harness["source_directory"]).glob("*.partial.*")),
        )
        self.assertEqual(tuple(Path(harness["temporary_directory"]).iterdir()), ())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources"],
        )

    def test_fetch_never_overwrites_concurrent_cache_destination(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        first_source = self.module.SOURCE_SPECS[0]
        destination = Path(harness["source_directory"]) / Path(
            first_source.local_source_path
        ).name
        race_marker = Path(harness["repository"]) / "mv-race-injected"
        fake_mv = Path(harness["fake_bin"]) / "mv"
        fake_mv.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "destination=\"${!#}\"\n"
            "if [[ ! -e \"$FETCH_MV_RACE_MARKER\" ]]; then\n"
            "  printf 'concurrent-destination\\n' >\"$destination\"\n"
            "  : >\"$FETCH_MV_RACE_MARKER\"\n"
            "fi\n"
            "exec \"$REAL_MV\" \"$@\"\n",
            encoding="ascii",
        )
        fake_mv.chmod(0o755)
        environment = dict(harness["environment"])
        environment.update(
            {
                "FETCH_CURL_MODE": "valid",
                "FETCH_CURL_STATUS": "0",
                "FETCH_MV_RACE_MARKER": str(race_marker),
                "REAL_MV": str(shutil.which("mv")),
            }
        )

        completed = self.run_fetch_harness(
            harness,
            "--create-freeze",
            environment=environment,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("source destination appeared during publication", completed.stderr)
        self.assertEqual(destination.read_text(encoding="ascii"), "concurrent-destination\n")
        self.assertFalse(
            tuple(Path(harness["source_directory"]).glob("*.partial.*")),
        )

    def test_fetch_signal_after_cache_publication_cleans_owned_inode(self) -> None:
        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=False,
        )
        first_source = self.module.SOURCE_SPECS[0]
        destination = Path(harness["source_directory"]) / Path(
            first_source.local_source_path
        ).name
        signal_marker = Path(harness["repository"]) / "mv-signal-injected"
        fake_mv = Path(harness["fake_bin"]) / "mv"
        fake_mv.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "destination=\"${!#}\"\n"
            "\"$REAL_MV\" \"$@\"\n"
            "if [[ ! -e \"$FETCH_MV_SIGNAL_MARKER\" ]]; then\n"
            "  printf 'corrupt-after-publication\\n' >\"$destination\"\n"
            "  : >\"$FETCH_MV_SIGNAL_MARKER\"\n"
            "  kill -TERM \"$PPID\"\n"
            "fi\n",
            encoding="ascii",
        )
        fake_mv.chmod(0o755)
        environment = dict(harness["environment"])
        environment.update(
            {
                "FETCH_CURL_MODE": "valid",
                "FETCH_CURL_STATUS": "0",
                "FETCH_MV_SIGNAL_MARKER": str(signal_marker),
                "REAL_MV": str(shutil.which("mv")),
            }
        )

        interrupted = self.run_fetch_harness(
            harness,
            "--create-freeze",
            environment=environment,
        )

        self.assertNotEqual(interrupted.returncode, 0)
        self.assertFalse(destination.exists())
        self.assertFalse(
            tuple(Path(harness["source_directory"]).glob("*.partial.*")),
        )

        retried = self.run_fetch_harness(
            harness,
            "--create-freeze",
            environment=environment,
        )
        self.assertEqual(
            retried.returncode,
            0,
            f"stdout:\n{retried.stdout}\nstderr:\n{retried.stderr}",
        )
        self.assertTrue(destination.is_file())

    def test_fetch_rejects_symlinked_committed_output_and_cache(self) -> None:
        committed = self.prepare_fetch_harness(
            committed_outputs=True,
            valid_cache=True,
        )
        manifest = Path(dict(committed["output_paths"])["manifest"])
        outside_manifest = Path(committed["repository"]) / "outside-manifest.tsv"
        outside_manifest.write_text("outside\n", encoding="ascii")
        manifest.unlink()
        manifest.symlink_to(outside_manifest)
        completed = self.run_fetch_harness(committed)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("committed application freeze output is unsafe", completed.stderr)
        self.assertEqual(outside_manifest.read_text(encoding="ascii"), "outside\n")
        self.assertFalse(Path(committed["curl_log"]).exists())
        self.assertFalse(Path(committed["python_log"]).exists())

        cache = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=True,
        )
        first_source = self.module.SOURCE_SPECS[0]
        cached_source = Path(cache["source_directory"]) / Path(
            first_source.local_source_path
        ).name
        outside_cache = Path(cache["repository"]) / "outside-source.fa.gz"
        outside_cache.write_bytes(cached_source.read_bytes())
        cached_source.unlink()
        cached_source.symlink_to(outside_cache)
        completed = self.run_fetch_harness(cache, "--create-freeze")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cached source identity mismatch", completed.stderr)
        self.assertTrue(cached_source.is_symlink())
        self.assertTrue(outside_cache.is_file())
        self.assertFalse(Path(cache["curl_log"]).exists())
        self.assertEqual(
            Path(cache["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources"],
        )

    def test_fetch_create_flag_is_unique_and_publishes_only_missing_outputs(self) -> None:
        for arguments in (("--unknown",), ("--create-freeze", "--create-freeze")):
            with self.subTest(arguments=arguments):
                rejected = self.prepare_fetch_harness(
                    committed_outputs=False,
                    valid_cache=True,
                )
                completed = self.run_fetch_harness(rejected, *arguments)
                self.assertNotEqual(completed.returncode, 0)
                self.assertFalse(Path(rejected["curl_log"]).exists())
                self.assertFalse(Path(rejected["python_log"]).exists())

        harness = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=True,
        )
        completed = self.run_fetch_harness(harness, "--create-freeze")
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertFalse(Path(harness["curl_log"]).exists())
        self.assertEqual(
            Path(harness["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources", "select", "materialize"],
        )
        for output in dict(harness["output_paths"]).values():
            self.assertTrue(Path(output).exists(), output)
        self.assertEqual(tuple(Path(harness["temporary_directory"]).iterdir()), ())

    def test_fetch_rejects_wrong_cache_and_missing_tools(self) -> None:
        corrupt = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=True,
        )
        first_source = self.module.SOURCE_SPECS[0]
        bad_cache = Path(corrupt["source_directory"]) / Path(
            first_source.local_source_path
        ).name
        bad_cache.write_bytes(b"wrong-cache-bytes")
        completed = self.run_fetch_harness(corrupt, "--create-freeze")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cached source identity mismatch", completed.stderr)
        self.assertFalse(Path(corrupt["curl_log"]).exists())
        self.assertEqual(
            Path(corrupt["python_log"]).read_text(encoding="ascii").splitlines(),
            ["sources"],
        )

        missing_tool = self.prepare_fetch_harness(
            committed_outputs=False,
            valid_cache=True,
        )
        environment = dict(missing_tool["environment"])
        environment["PATH"] = str(missing_tool["fake_bin"])
        completed = self.run_fetch_harness(
            missing_tool,
            "--create-freeze",
            environment=environment,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("required command not found", completed.stderr)
        self.assertFalse(Path(missing_tool["curl_log"]).exists())
        self.assertFalse(Path(missing_tool["python_log"]).exists())

    def test_freeze_path_records_are_frozen_and_public_signatures_are_explicit(self) -> None:
        self.prepare_freeze_fixture()
        self.assertEqual(
            tuple(inspect.signature(self.module.SourceInputs).parameters),
            (
                "lncrna_fasta",
                "annotation_gtf",
                "chr21_fasta",
                "chr22_fasta",
                "development_exclusions",
                "holdout_manifest",
                "source_specs",
            ),
        )
        self.assertEqual(
            tuple(inspect.signature(self.module.FreezePaths).parameters),
            (
                "repository_root",
                "selection_receipt",
                "application_inputs",
                "manifest",
                "manifest_checksum",
                "source_ledger",
                "input_summary",
            ),
        )
        self.assertEqual(
            tuple(inspect.signature(self.module.build_freeze).parameters),
            ("inputs", "outputs", "after_publish"),
        )
        with self.assertRaises(FrozenInstanceError):
            self.synthetic_inputs.lncrna_fasta = self.work / "replacement.fa"
        with self.assertRaises(FrozenInstanceError):
            self.output_paths.manifest = self.work / "replacement.tsv"

    def test_transcript_records_are_frozen(self) -> None:
        transcript = self.module.Transcript(
            transcript_id="ENSTQ.1",
            gene_id="ENSGQ.1",
            gene_name="QUERY",
            gene_type="lncRNA",
            chromosome="chr21",
            start=100,
            end=900,
            strand="+",
            level=2,
            tags=frozenset({"basic"}),
        )
        with self.assertRaises(FrozenInstanceError):
            transcript.level = 1

    def test_hash_helpers_are_deterministic(self) -> None:
        content = b"strict-source\x00bytes\n"
        path = self.write_bytes("source.bin", content)
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual(self.module.sha256_file(path), expected)
        self.assertEqual(self.module.sha256_stream(io.BytesIO(content)), expected)
        self.assertEqual(
            self.module.sequence_sha256("ACGT"),
            hashlib.sha256(b"ACGT").hexdigest(),
        )

    def test_stable_id_strips_only_the_version_suffix(self) -> None:
        self.assertEqual(self.module.stable_id("ENST000001.17"), "ENST000001")
        self.assertEqual(self.module.stable_id("ENST000001"), "ENST000001")

    def test_open_text_reads_plain_and_gzip_sources(self) -> None:
        plain = self.write_text("source.txt", "alpha\nbeta\n")
        compressed = self.write_gzip("source.txt.gz", "alpha\nbeta\n")
        for path in (plain, compressed):
            with self.subTest(path=path.name), self.module.open_text(path) as handle:
                self.assertEqual(handle.read(), "alpha\nbeta\n")

    def test_parse_attributes_preserves_repeated_and_unquoted_values(self) -> None:
        attributes = self.module.parse_attributes(
            'gene_id "ENSGQ.1"; level 2; tag "basic"; tag "MANE_Select";'
        )
        self.assertEqual(attributes["gene_id"], ("ENSGQ.1",))
        self.assertEqual(attributes["level"], ("2",))
        self.assertEqual(attributes["tag"], ("basic", "MANE_Select"))

    def test_gtf_parser_retains_required_tags_and_strand(self) -> None:
        gtf = self.write_text(
            "fixture.gtf",
            "chr21\tHAVANA\ttranscript\t100\t900\t.\t+\t.\t"
            'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "Q"; '
            'gene_type "lncRNA"; level 2; tag "basic";\n'
            "chr22\tHAVANA\ttranscript\t2000\t4000\t.\t-\t.\t"
            'gene_id "ENSGT.1"; transcript_id "ENSTT.1"; gene_name "T"; '
            'gene_type "protein_coding"; tag "MANE_Select"; '
            'tag "Ensembl_canonical";\n',
        )

        transcripts = self.module.parse_gtf(gtf)

        self.assertEqual(transcripts["ENSTQ.1"].tags, frozenset({"basic"}))
        self.assertEqual(transcripts["ENSTQ.1"].level, 2)
        self.assertEqual(transcripts["ENSTT.1"].strand, "-")
        self.assertEqual(transcripts["ENSTT.1"].level, 99)
        self.assertEqual(
            transcripts["ENSTT.1"].tags,
            frozenset({"MANE_Select", "Ensembl_canonical"}),
        )

    def test_gtf_parser_level_domain_is_exact(self) -> None:
        for level in ("1", "2", "3"):
            with self.subTest(valid_level=level):
                attributes = (
                    'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "QUERY"; '
                    f'gene_type "lncRNA"; level {level};'
                )
                gtf = self.write_text(
                    f"level-{level}.gtf",
                    self.transcript_row(attributes=attributes),
                )
                self.assertEqual(self.module.parse_gtf(gtf)["ENSTQ.1"].level, int(level))

        missing_level = self.write_text(
            "missing-level.gtf",
            self.transcript_row(
                attributes=(
                    'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; '
                    'gene_name "QUERY"; gene_type "lncRNA";'
                )
            ),
        )
        self.assertEqual(self.module.parse_gtf(missing_level)["ENSTQ.1"].level, 99)

        for level in ("0", "4", "99", "-1", "01", "+1", "1.0"):
            with self.subTest(invalid_level=level):
                attributes = (
                    'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "QUERY"; '
                    f'gene_type "lncRNA"; level {level};'
                )
                gtf = self.write_text(
                    f"invalid-level-{level.replace('+', 'plus')}.gtf",
                    self.transcript_row(attributes=attributes),
                )
                with self.assertRaisesRegex(ValueError, "invalid GTF level"):
                    self.module.parse_gtf(gtf)

    def test_fasta_parser_uppercases_records_deterministically(self) -> None:
        fasta = self.write_gzip(
            "records.fa.gz",
            ">record one\nac\ngt\n>record two\nttaa\n",
        )
        self.assertEqual(
            self.module.parse_fasta(fasta),
            [("record one", "ACGT"), ("record two", "TTAA")],
        )

    def test_fasta_parser_preserves_padded_headers_for_selector_rejection(self) -> None:
        padded_headers = {
            "leading-after-marker": (
                " ENSTPARSER.1|ENSGPARSER.1|-|-|PARSER-201|PARSER|700|"
            ),
            "terminal-whitespace": (
                "ENSTPARSER.1|ENSGPARSER.1|-|-|PARSER-201|PARSER|700|   "
            ),
        }
        for name, padded_header in padded_headers.items():
            with self.subTest(name=name):
                records, transcripts = self.basic_query_fixture(50)
                self.add_query_record(
                    records,
                    transcripts,
                    transcript_id="ENSTPARSER.1",
                    gene_id="ENSGPARSER.1",
                    gene_name="PARSER",
                    sequence=self.unique_query_sequence(930),
                )
                records[-1] = (padded_header, records[-1][1])
                fasta = self.write_text(
                    f"padded-header-{name}.fa",
                    "".join(f">{header}\n{sequence}\n" for header, sequence in records),
                )

                parsed_records = self.module.parse_fasta(fasta)

                with self.assertRaisesRegex(ValueError, "GENCODE v49 FASTA"):
                    self.module.select_queries(
                        fasta_records=parsed_records,
                        transcripts=transcripts,
                        development_exclusions=self.no_development_exclusions(),
                        holdout_gene_ids=set(),
                        holdout_sequence_sha256=set(),
                    )

    def test_fasta_parser_requires_header_marker_in_first_column(self) -> None:
        fasta = self.write_text("indented-header.fa", "  >record\nACGT\n")
        with self.assertRaisesRegex(ValueError, "before FASTA header"):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_sequence_before_header(self) -> None:
        fasta = self.write_text("bad.fa", "ACGT\n")
        with self.assertRaisesRegex(ValueError, "before FASTA header"):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_invalid_utf8(self) -> None:
        fasta = self.write_bytes("bad-utf8.fa", b">record\nAC\xffGT\n")
        with self.assertRaises(UnicodeDecodeError):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_duplicate_full_headers(self) -> None:
        fasta = self.write_text(
            "duplicate.fa",
            ">record full description\nACGT\n>record full description\nTGCA\n",
        )
        with self.assertRaisesRegex(ValueError, "duplicate FASTA header"):
            self.module.parse_fasta(fasta)

    def test_fasta_parser_rejects_empty_records(self) -> None:
        fixtures = {
            "empty-file.fa": "",
            "empty-middle.fa": ">empty\n>nonempty\nACGT\n",
            "empty-final.fa": ">nonempty\nACGT\n>empty\n",
            "whitespace-header.fa": ">   \nACGT\n",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                fasta = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, "empty FASTA record"):
                    self.module.parse_fasta(fasta)

    def test_gtf_parser_rejects_invalid_utf8(self) -> None:
        gtf = self.write_bytes("bad-utf8.gtf", self.transcript_row().encode() + b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            self.module.parse_gtf(gtf)

    def test_gtf_parser_requires_exactly_nine_columns(self) -> None:
        valid_fields = self.transcript_row().rstrip("\n").split("\t")
        fixtures = {
            "eight.gtf": "\t".join(valid_fields[:-1]) + "\n",
            "ten.gtf": "\t".join([*valid_fields, "extra"]) + "\n",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                gtf = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, "exactly 9 columns"):
                    self.module.parse_gtf(gtf)

    def test_gtf_parser_rejects_nonpositive_and_reversed_coordinates(self) -> None:
        fixtures = {
            "zero-start.gtf": self.transcript_row(start="0"),
            "negative-end.gtf": self.transcript_row(end="-1"),
            "reversed.gtf": self.transcript_row(start="901", end="900"),
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                gtf = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, "invalid GTF coordinates"):
                    self.module.parse_gtf(gtf)

    def test_gtf_parser_rejects_invalid_transcript_strand(self) -> None:
        gtf = self.write_text("invalid-strand.gtf", self.transcript_row(strand="."))
        with self.assertRaisesRegex(ValueError, "invalid transcript strand"):
            self.module.parse_gtf(gtf)

    def test_gtf_parser_requires_identity_and_type_attributes(self) -> None:
        required = {
            "gene_id": 'gene_id "ENSGQ.1";',
            "transcript_id": 'transcript_id "ENSTQ.1";',
            "gene_name": 'gene_name "QUERY";',
            "gene_type": 'gene_type "lncRNA";',
        }
        complete = " ".join(required.values())
        for missing, clause in required.items():
            with self.subTest(missing=missing):
                attributes = complete.replace(clause, "")
                gtf = self.write_text(
                    f"missing-{missing}.gtf",
                    self.transcript_row(attributes=attributes),
                )
                with self.assertRaisesRegex(
                    ValueError,
                    f"missing required GTF attribute {missing}",
                ):
                    self.module.parse_gtf(gtf)

        for empty, clause in required.items():
            with self.subTest(empty=empty):
                attributes = complete.replace(clause, f'{empty} " ";')
                gtf = self.write_text(
                    f"empty-{empty}.gtf",
                    self.transcript_row(attributes=attributes),
                )
                with self.assertRaisesRegex(
                    ValueError,
                    f"missing required GTF attribute {empty}",
                ):
                    self.module.parse_gtf(gtf)

    def test_gtf_parser_rejects_differing_duplicate_transcript_metadata(self) -> None:
        gtf = self.write_text(
            "duplicate.gtf",
            self.transcript_row() + self.transcript_row(end="901"),
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate transcript ID ENSTQ.1 has differing metadata",
        ):
            self.module.parse_gtf(gtf)

    def test_gtf_parser_accepts_identical_duplicate_transcript_metadata(self) -> None:
        row = self.transcript_row()
        gtf = self.write_text("identical-duplicate.gtf", row + row)
        transcripts = self.module.parse_gtf(gtf)
        self.assertEqual(list(transcripts), ["ENSTQ.1"])

    def test_query_selection_public_signatures_are_explicit(self) -> None:
        expected_parameters = {
            "read_development_exclusions": ("path",),
            "read_holdout_exclusions": ("path",),
            "choose_query_representative": ("rows",),
            "query_representative_key": ("row",),
            "query_selection_hash": ("row",),
            "select_queries": (
                "fasta_records",
                "transcripts",
                "development_exclusions",
                "holdout_gene_ids",
                "holdout_sequence_sha256",
            ),
        }
        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                signature = inspect.signature(getattr(self.module, name))
                self.assertEqual(tuple(signature.parameters), parameters)
        select_signature = inspect.signature(self.module.select_queries)
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.KEYWORD_ONLY
                for parameter in select_signature.parameters.values()
            )
        )

    def test_development_exclusions_use_exact_schema_and_normalize_only_gene_ids(self) -> None:
        digest = "e" * 64
        path = self.write_text(
            "development.tsv",
            "exclusion_type\tvalue\treason\n"
            "gene_id\tENSGDEV.17\tused gene\n"
            "gene_name\tGENE.NAME.9\tused name\n"
            f"sequence_sha256\t{digest}\tused sequence\n",
        )

        exclusions = self.module.read_development_exclusions(path)

        self.assertEqual(
            exclusions,
            {
                "gene_id": {"ENSGDEV"},
                "gene_name": {"GENE.NAME.9"},
                "sequence_sha256": {digest},
            },
        )

    def test_development_exclusions_reject_wrong_schema_types_and_rows(self) -> None:
        fixtures = {
            "wrong-header.tsv": "type\tvalue\treason\ngene_id\tENSG1\tused\n",
            "unsupported-type.tsv": (
                "exclusion_type\tvalue\treason\ntranscript_id\tENST1\tused\n"
            ),
            "missing-column.tsv": "exclusion_type\tvalue\treason\ngene_id\tENSG1\n",
            "extra-column.tsv": (
                "exclusion_type\tvalue\treason\ngene_id\tENSG1\tused\textra\n"
            ),
            "blank-value.tsv": "exclusion_type\tvalue\treason\ngene_id\t\tused\n",
            "blank-reason.tsv": "exclusion_type\tvalue\treason\ngene_id\tENSG1\t\n",
            "padded-value.tsv": (
                "exclusion_type\tvalue\treason\ngene_name\t PADDED \tused\n"
            ),
            "padded-reason.tsv": (
                "exclusion_type\tvalue\treason\ngene_name\tPADDED\t used \n"
            ),
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                path = self.write_text(name, content)
                with self.assertRaises(ValueError):
                    self.module.read_development_exclusions(path)

    def test_holdout_exclusions_parse_exact_phase2_schema_and_stable_ids(self) -> None:
        first = self.holdout_row()
        repeated = self.holdout_row(workload_id="hq01_ht02")
        second = self.holdout_row(
            workload_id="hq02_ht01",
            query_id="hq02",
            gene_id="ENSGSECOND.8",
            query_sequence_sha256="f" * 64,
        )
        path = self.write_tsv(
            "holdout.tsv",
            HOLDOUT_MANIFEST_FIELDS,
            [first, repeated, second],
        )

        gene_ids, sequence_digests = self.module.read_holdout_exclusions(path)

        self.assertEqual(gene_ids, {"ENSGHOLD", "ENSGSECOND"})
        self.assertEqual(sequence_digests, {"a" * 64, "f" * 64})

    def test_committed_holdout_manifest_satisfies_the_reader_contract(self) -> None:
        gene_ids, sequence_digests = self.module.read_holdout_exclusions(
            ROOT / "paper/bioinformatics/holdout_manifest.tsv"
        )
        self.assertEqual(len(gene_ids), 12)
        self.assertEqual(len(sequence_digests), 12)
        self.assertIn("ENSG00000276454", gene_ids)
        self.assertIn(
            "e6f49cc6e21c70f84017c331f2b1096a79befef92e2f90948ab60f8409e5b3fa",
            sequence_digests,
        )

    def test_holdout_exclusions_reject_whitespace_padding_before_normalization(self) -> None:
        for field in HOLDOUT_MANIFEST_FIELDS:
            with self.subTest(field=field):
                row = self.holdout_row()
                row[field] = f" {row[field]}"
                path = self.write_tsv(
                    f"padded-holdout-{field}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [row],
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "whitespace-padded holdout manifest field",
                ):
                    self.module.read_holdout_exclusions(path)

    def test_holdout_exclusions_requires_lowercase_query_file_sha256(self) -> None:
        invalid_digests = {
            "malformed": "not-a-sha256",
            "uppercase": "A" * 64,
        }
        for name, digest in invalid_digests.items():
            with self.subTest(name=name):
                row = {**self.holdout_row(), "query_file_sha256": digest}
                path = self.write_tsv(
                    f"invalid-query-file-sha256-{name}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [row],
                )
                with self.assertRaisesRegex(ValueError, "query_file_sha256"):
                    self.module.read_holdout_exclusions(path)

    def test_holdout_exclusions_reject_wrong_schema_and_malformed_rows(self) -> None:
        wrong_fields = (*HOLDOUT_MANIFEST_FIELDS[:-1], "result_status")
        wrong_schema = self.write_tsv(
            "wrong-holdout-schema.tsv",
            wrong_fields,
            [{field: "fixture" for field in wrong_fields}],
        )
        with self.assertRaisesRegex(ValueError, "holdout manifest.*columns"):
            self.module.read_holdout_exclusions(wrong_schema)

        header = "\t".join(HOLDOUT_MANIFEST_FIELDS) + "\n"
        valid_values = [self.holdout_row()[field] for field in HOLDOUT_MANIFEST_FIELDS]
        malformed_widths = {
            "missing-holdout-column.tsv": "\t".join(valid_values[:-1]) + "\n",
            "extra-holdout-column.tsv": "\t".join([*valid_values, "extra"]) + "\n",
        }
        for name, row_text in malformed_widths.items():
            with self.subTest(name=name):
                path = self.write_text(name, header + row_text)
                with self.assertRaisesRegex(ValueError, "holdout manifest row"):
                    self.module.read_holdout_exclusions(path)

        malformed_values = {
            "blank-holdout-gene.tsv": self.holdout_row(gene_id=""),
            "blank-holdout-query.tsv": {
                **self.holdout_row(),
                "query_id": "",
            },
            "invalid-holdout-digest.tsv": self.holdout_row(
                query_sequence_sha256="not-a-sha256"
            ),
        }
        for name, row in malformed_values.items():
            with self.subTest(name=name):
                path = self.write_tsv(name, HOLDOUT_MANIFEST_FIELDS, [row])
                with self.assertRaisesRegex(ValueError, "holdout manifest row"):
                    self.module.read_holdout_exclusions(path)

        alternate_query_values = {
            "gene_id": "ENSGHOLD.8",
            "gene_name": "HOLDOUT_ALTERNATE",
            "transcript_id": "ENSTHOLD.2",
            "query_length_nt": "701",
            "length_stratum": "801_1600",
            "query_sequence_sha256": "f" * 64,
            "query_file_sha256": "e" * 64,
            "query_path": "reproduce/bioinformatics/holdout_inputs/queries/hq01-alternate.fa",
        }
        self.assertEqual(tuple(alternate_query_values), HOLDOUT_QUERY_FIELDS)
        for field, alternate in alternate_query_values.items():
            with self.subTest(conflicting_query_field=field):
                repeated = self.holdout_row(workload_id="hq01_ht02")
                repeated.update(
                    target_id="ht02",
                    target_gene_id="ENSGTARGET2.1",
                    target_gene_name="TARGET2",
                    target_chromosome="chr2",
                    target_sequence_sha256="1" * 64,
                    target_file_sha256="2" * 64,
                    target_path="reproduce/bioinformatics/holdout_inputs/targets/ht02.fa",
                )
                repeated[field] = alternate
                conflict = self.write_tsv(
                    f"conflicting-holdout-{field}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [self.holdout_row(), repeated],
                )
                with self.assertRaisesRegex(ValueError, "conflicting holdout query"):
                    self.module.read_holdout_exclusions(conflict)

        distinct_query = {
            **self.holdout_row(
                workload_id="hq02_ht01",
                query_id="hq02",
                gene_id="ENSGSECOND.1",
                query_sequence_sha256="f" * 64,
            ),
            "gene_name": "SECOND",
            "transcript_id": "ENSTSECOND.1",
            "query_file_sha256": "e" * 64,
            "query_path": "reproduce/bioinformatics/holdout_inputs/queries/hq02.fa",
        }
        aliases = {
            "stable gene ID": {
                **distinct_query,
                "gene_id": "ENSGHOLD.8",
            },
            "query sequence digest": {
                **distinct_query,
                "query_sequence_sha256": "a" * 64,
            },
        }
        for label, alias in aliases.items():
            with self.subTest(cross_query_alias=label):
                path = self.write_tsv(
                    f"aliased-holdout-{label.replace(' ', '-')}.tsv",
                    HOLDOUT_MANIFEST_FIELDS,
                    [self.holdout_row(), alias],
                )
                with self.assertRaisesRegex(ValueError, f"{label}.*multiple holdout queries"):
                    self.module.read_holdout_exclusions(path)

    def test_query_representative_prefers_level_basic_length_then_id(self) -> None:
        rows = [
            {
                "transcript_id": "ENST_LEVEL2_BASIC_LONG.1",
                "level": 2,
                "basic": True,
                "sequence_length": 1200,
            },
            {
                "transcript_id": "ENST_LEVEL1_NONBASIC_LONG.1",
                "level": 1,
                "basic": False,
                "sequence_length": 1300,
            },
            {
                "transcript_id": "ENST_LEVEL1_BASIC_SHORT.1",
                "level": 1,
                "basic": True,
                "sequence_length": 800,
            },
            {
                "transcript_id": "ENST_LEVEL1_BASIC_LONG_Z.1",
                "level": 1,
                "basic": True,
                "sequence_length": 1000,
            },
            {
                "transcript_id": "ENST_LEVEL1_BASIC_LONG.1",
                "level": 1,
                "basic": True,
                "sequence_length": 1000,
            },
        ]

        ordered = sorted(rows, key=self.module.query_representative_key)
        representative = self.module.choose_query_representative(rows)

        self.assertEqual(
            [row["transcript_id"] for row in ordered],
            [
                "ENST_LEVEL1_BASIC_LONG.1",
                "ENST_LEVEL1_BASIC_LONG_Z.1",
                "ENST_LEVEL1_BASIC_SHORT.1",
                "ENST_LEVEL1_NONBASIC_LONG.1",
                "ENST_LEVEL2_BASIC_LONG.1",
            ],
        )
        self.assertEqual(
            self.module.query_representative_key(rows[-1]),
            (1, 0, -1000, "ENST_LEVEL1_BASIC_LONG.1"),
        )
        self.assertIs(representative, rows[-1])
        with self.assertRaisesRegex(ValueError, "no query candidates"):
            self.module.choose_query_representative([])

    def test_query_representative_key_requires_real_boolean_basic(self) -> None:
        row = {
            "transcript_id": "ENST_BOOLEAN.1",
            "level": 1,
            "basic": True,
            "sequence_length": 700,
        }
        for invalid in ("False", 0, 1, None):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "basic must be bool"):
                    self.module.query_representative_key({**row, "basic": invalid})

    def test_query_selection_hash_uses_only_seed_and_stable_sequence_identity(self) -> None:
        digest = hashlib.sha256(b"ACGT").hexdigest()
        row = {
            "gene_id": "ENSGIDENTITY.17",
            "transcript_id": "ENSTIDENTITY.3",
            "sequence_sha256": digest,
            "gene_name": "BIOLOGY_NAME",
            "chromosome": "chr21",
            "runtime_seconds": 999,
            "result": "ignored",
        }
        payload = (
            "gasal2-longtarget-phase3-application-v1-20260724"
            f"|ENSGIDENTITY|ENSTIDENTITY|{digest}"
        )
        expected = hashlib.sha256(payload.encode("ascii")).hexdigest()

        self.assertEqual(self.module.query_selection_hash(row), expected)
        self.assertEqual(
            self.module.query_selection_hash(
                {
                    **row,
                    "gene_name": "DIFFERENT_NAME",
                    "chromosome": "chrX",
                    "runtime_seconds": 1,
                    "result": "different",
                }
            ),
            expected,
        )

    def test_query_selection_uses_priority_hash_and_both_exclusion_ledgers(self) -> None:
        records, transcripts = self.basic_query_fixture(55)
        representative_versions = [
            ("ENST_LEVEL2_BASIC_LONG.1", 2, True, 1200, 200),
            ("ENST_LEVEL1_NONBASIC_LONG.1", 1, False, 1300, 201),
            ("ENST_LEVEL1_BASIC_SHORT.1", 1, True, 800, 202),
            ("ENST_LEVEL1_BASIC_LONG_Z.1", 1, True, 1000, 203),
            ("ENST_LEVEL1_BASIC_LONG.1", 1, True, 1000, 204),
        ]
        for transcript_id, level, basic, length, sequence_index in representative_versions:
            self.add_query_record(
                records,
                transcripts,
                transcript_id=transcript_id,
                gene_id="ENSGPRIORITY.9",
                gene_name="PRIORITY",
                sequence=self.unique_query_sequence(sequence_index, length),
                level=level,
                basic=basic,
            )

        excluded_specs = [
            (
                "ENSTDEV.1",
                "ENSGDEV.7",
                "DEVELOPMENT_ID",
                self.unique_query_sequence(300),
            ),
            (
                "ENSTDEVNAME.1",
                "ENSGDEVNAME.1",
                "DEVELOPMENT_NAME",
                self.unique_query_sequence(301),
            ),
            ("ENSTDEVDIGEST.1", "ENSGDEVDIGEST.1", "DEV_DIGEST", "C" * 700),
            (
                "ENSTHOLD.1",
                "ENSGHOLD.3",
                "HOLDOUT_ID",
                self.unique_query_sequence(303),
            ),
            ("ENSTHOLDDIGEST.1", "ENSGHOLDDIGEST.1", "HOLD_DIGEST", "A" * 700),
        ]
        for transcript_id, gene_id, gene_name, sequence in excluded_specs:
            self.add_query_record(
                records,
                transcripts,
                transcript_id=transcript_id,
                gene_id=gene_id,
                gene_name=gene_name,
                sequence=sequence,
            )

        development = {
            "gene_id": {"ENSGDEV"},
            "gene_name": {"DEVELOPMENT_NAME"},
            "sequence_sha256": {self.module.sequence_sha256("C" * 700)},
        }
        selected, counts = self.module.select_queries(
            fasta_records=records,
            transcripts=transcripts,
            development_exclusions=development,
            holdout_gene_ids={"ENSGHOLD"},
            holdout_sequence_sha256={self.module.sequence_sha256("A" * 700)},
        )

        expected_records = {
            f"ENSTQ{index:05d}.1": self.unique_query_sequence(index)
            for index in range(1, 56)
        }
        expected_records["ENST_LEVEL1_BASIC_LONG.1"] = self.unique_query_sequence(204, 1000)
        expected_identities: list[tuple[str, str, str, str]] = []
        for transcript_id, sequence in expected_records.items():
            gene_id = (
                "ENSGPRIORITY"
                if transcript_id == "ENST_LEVEL1_BASIC_LONG.1"
                else transcript_id.replace("ENST", "ENSG").split(".", 1)[0]
            )
            stable_transcript_id = transcript_id.split(".", 1)[0]
            digest = hashlib.sha256(sequence.encode("ascii")).hexdigest()
            payload = "|".join(
                (
                    "gasal2-longtarget-phase3-application-v1-20260724",
                    gene_id,
                    stable_transcript_id,
                    digest,
                )
            )
            selection_hash = hashlib.sha256(payload.encode("ascii")).hexdigest()
            expected_identities.append((selection_hash, gene_id, transcript_id, digest))
        expected_identities.sort(key=lambda identity: identity[:3])
        expected_identities = expected_identities[:50]

        self.assertEqual(len(selected), 50)
        self.assertEqual(
            [row["query_id"] for row in selected],
            [f"aq{index:03d}" for index in range(1, 51)],
        )
        self.assertEqual(
            [
                (
                    row["selection_hash"],
                    self.module.stable_id(str(row["gene_id"])),
                    str(row["transcript_id"]),
                    row["sequence_sha256"],
                )
                for row in selected
            ],
            expected_identities,
        )
        selected_genes = {
            self.module.stable_id(str(row["gene_id"])) for row in selected
        }
        self.assertTrue(
            selected_genes.isdisjoint(
                {
                    "ENSGDEV",
                    "ENSGDEVNAME",
                    "ENSGDEVDIGEST",
                    "ENSGHOLD",
                    "ENSGHOLDDIGEST",
                }
            )
        )
        self.assertEqual(counts["input_query_record_count"], 65)
        self.assertEqual(counts["eligible_query_transcript_count"], 60)
        self.assertEqual(counts["representative_query_count"], 56)
        self.assertEqual(counts["selected_query_count"], 50)
        self.assertEqual(counts["excluded_development_gene_id_count"], 1)
        self.assertEqual(counts["excluded_development_gene_name_count"], 1)
        self.assertEqual(counts["excluded_development_sequence_sha256_count"], 1)
        self.assertEqual(counts["excluded_holdout_gene_id_count"], 1)
        self.assertEqual(counts["excluded_holdout_sequence_sha256_count"], 1)

    def test_query_selection_is_identical_under_reversed_fasta_order(self) -> None:
        records, transcripts = self.basic_query_fixture(55)
        forward_rows, forward_counts = self.module.select_queries(
            fasta_records=records,
            transcripts=transcripts,
            development_exclusions=self.no_development_exclusions(),
            holdout_gene_ids=set(),
            holdout_sequence_sha256=set(),
        )
        reverse_rows, reverse_counts = self.module.select_queries(
            fasta_records=reversed(records),
            transcripts=transcripts,
            development_exclusions=self.no_development_exclusions(),
            holdout_gene_ids=set(),
            holdout_sequence_sha256=set(),
        )

        self.assertEqual(reverse_rows, forward_rows)
        self.assertEqual(reverse_counts, forward_counts)

    def test_query_eligibility_accepts_endpoints_and_counts_biological_exclusions(self) -> None:
        records: list[tuple[str, str]] = []
        transcripts: dict[str, object] = {}
        for index in range(1, 51):
            length = 500 if index == 1 else 2812 if index == 2 else 700
            self.add_query_record(
                records,
                transcripts,
                transcript_id=f"ENSTBOUND{index:03d}.1",
                gene_id=f"ENSGBound{index:03d}.1",
                sequence=self.unique_query_sequence(400 + index, length),
            )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTTOOSHORT.1",
            gene_id="ENSGTOOSHORT.1",
            sequence=self.unique_query_sequence(500, 499),
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTTOOLONG.1",
            gene_id="ENSGTOOLONG.1",
            sequence=self.unique_query_sequence(501, 2813),
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTNONCANONICAL.1",
            gene_id="ENSGNONCANONICAL.1",
            sequence="A" * 699 + "N",
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTNONLNC.1",
            gene_id="ENSGNONLNC.1",
            sequence=self.unique_query_sequence(503),
            gene_type="protein_coding",
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTNONPRIMARY.1",
            gene_id="ENSGNONPRIMARY.1",
            sequence=self.unique_query_sequence(504),
            chromosome="chrM",
        )

        selected, counts = self.module.select_queries(
            fasta_records=records,
            transcripts=transcripts,
            development_exclusions=self.no_development_exclusions(),
            holdout_gene_ids=set(),
            holdout_sequence_sha256=set(),
        )

        selected_transcripts = {row["transcript_id"] for row in selected}
        self.assertIn("ENSTBOUND001.1", selected_transcripts)
        self.assertIn("ENSTBOUND002.1", selected_transcripts)
        self.assertEqual(counts["input_query_record_count"], 55)
        self.assertEqual(counts["eligible_query_transcript_count"], 50)
        self.assertEqual(counts["representative_query_count"], 50)
        self.assertEqual(counts["selected_query_count"], 50)
        self.assertEqual(counts["excluded_query_length_count"], 2)
        self.assertEqual(counts["excluded_noncanonical_sequence_count"], 1)
        self.assertEqual(counts["excluded_non_lncRNA_count"], 1)
        self.assertEqual(counts["excluded_non_primary_chromosome_count"], 1)

    def test_query_selection_fails_with_fewer_than_fifty_eligible_genes(self) -> None:
        records, transcripts = self.basic_query_fixture(49)
        with self.assertRaisesRegex(ValueError, "only 49 eligible.*50 required"):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_rejects_duplicate_selected_sequence_digests(self) -> None:
        records, transcripts = self.basic_query_fixture(50)
        records[1] = (records[1][0], records[0][1])
        with self.assertRaisesRegex(ValueError, "selected query sequence digests.*unique"):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_rejects_malformed_gencode_headers(self) -> None:
        sequence = self.unique_query_sequence(600)
        transcript = self.module.Transcript(
            transcript_id="ENSTHEADER.1",
            gene_id="ENSGHEADER.1",
            gene_name="HEADER",
            gene_type="lncRNA",
            chromosome="chr1",
            start=1,
            end=700,
            strand="+",
            level=1,
            tags=frozenset({"basic"}),
        )
        fixtures = {
            "too-few-fields": ("ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER|HEADER", "header"),
            "blank-transcript": ("|ENSGHEADER.1|-|-|HEADER|HEADER|700|", "transcript ID"),
            "blank-gene": ("ENSTHEADER.1||-|-|HEADER|HEADER|700|", "gene ID"),
            "nonnumeric-length": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER|HEADER|seven-hundred|",
                "declared length",
            ),
            "mismatched-length": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER|HEADER|701|",
                "declared length",
            ),
        }
        for name, (header, message) in fixtures.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, message):
                    self.module.select_queries(
                        fasta_records=[(header, sequence)],
                        transcripts={"ENSTHEADER.1": transcript},
                        development_exclusions=self.no_development_exclusions(),
                        holdout_gene_ids=set(),
                        holdout_sequence_sha256=set(),
                    )

    def test_query_selection_requires_exact_v49_header_and_joined_gene_name(self) -> None:
        malformed_headers = {
            "seven-fields": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|HEADER|700",
                False,
                "GENCODE v49 FASTA header",
            ),
            "nine-fields": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|HEADER|700||",
                False,
                "GENCODE v49 FASTA header",
            ),
            "nonempty-terminal-field": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|HEADER|700|description",
                False,
                "GENCODE v49 FASTA header",
            ),
            "gene-name-drift": (
                "ENSTHEADER.1|ENSGHEADER.1|-|-|HEADER-201|DRIFT|700|",
                True,
                "FASTA/GTF gene name mismatch",
            ),
        }
        for name, (header, include_metadata, message) in malformed_headers.items():
            with self.subTest(name=name):
                records, transcripts = self.basic_query_fixture(50)
                sequence = self.unique_query_sequence(900)
                if include_metadata:
                    transcripts["ENSTHEADER.1"] = self.module.Transcript(
                        transcript_id="ENSTHEADER.1",
                        gene_id="ENSGHEADER.1",
                        gene_name="HEADER",
                        gene_type="lncRNA",
                        chromosome="chr1",
                        start=1,
                        end=700,
                        strand="+",
                        level=1,
                        tags=frozenset({"basic"}),
                    )
                records.append((header, sequence))
                with self.assertRaisesRegex(ValueError, message):
                    self.module.select_queries(
                        fasta_records=records,
                        transcripts=transcripts,
                        development_exclusions=self.no_development_exclusions(),
                        holdout_gene_ids=set(),
                        holdout_sequence_sha256=set(),
                    )

    def test_query_selection_rejects_padded_or_blank_v49_identity_before_lookup(self) -> None:
        identity_fields = (
            "transcript ID",
            "gene ID",
            "Havana gene ID",
            "Havana transcript ID",
            "transcript name",
            "gene name",
        )
        mutations = {
            "leading": lambda value: f" {value}",
            "trailing": lambda value: f"{value} ",
            "blank": lambda value: "",
        }
        for index, label in enumerate(identity_fields):
            for mutation_name, mutate in mutations.items():
                with self.subTest(field=label, mutation=mutation_name):
                    records, transcripts = self.basic_query_fixture(50)
                    parts = [
                        "ENSTIDENTITY.1",
                        "ENSGIDENTITY.1",
                        "-",
                        "-",
                        "IDENTITY-201",
                        "IDENTITY",
                        "700",
                        "",
                    ]
                    parts[index] = mutate(parts[index])
                    records.append(("|".join(parts), self.unique_query_sequence(920)))
                    with self.assertRaisesRegex(
                        ValueError,
                        "invalid GENCODE v49 FASTA identity",
                    ):
                        self.module.select_queries(
                            fasta_records=records,
                            transcripts=transcripts,
                            development_exclusions=self.no_development_exclusions(),
                            holdout_gene_ids=set(),
                            holdout_sequence_sha256=set(),
                        )

    def test_query_selection_rejects_duplicate_biological_transcript_ids(self) -> None:
        sequence = self.unique_query_sequence(700)
        records: list[tuple[str, str]] = []
        transcripts: dict[str, object] = {}
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTDUPLICATE.1",
            gene_id="ENSGDUPLICATE.1",
            sequence=sequence,
        )
        records.append(
            (
                "ENSTDUPLICATE.1|ENSGDUPLICATE.1|-|-|ALTERNATE-202|"
                "ENSGDUPLICATE|700|",
                sequence,
            )
        )
        with self.assertRaisesRegex(ValueError, "duplicate biological transcript ID"):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_rejects_duplicate_stable_transcript_ids(self) -> None:
        records, transcripts = self.basic_query_fixture(50)
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTSTABLEALIAS.1",
            gene_id="ENSGSTABLEALIAS1.1",
            sequence=self.unique_query_sequence(910),
        )
        self.add_query_record(
            records,
            transcripts,
            transcript_id="ENSTSTABLEALIAS.2",
            gene_id="ENSGSTABLEALIAS2.1",
            sequence=self.unique_query_sequence(911),
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate stable transcript ID 'ENSTSTABLEALIAS'",
        ):
            self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_query_selection_counts_missing_gtf_transcripts_and_requires_gene_join(self) -> None:
        records, transcripts = self.basic_query_fixture(50)
        sequence = self.unique_query_sequence(800)
        missing_header = "ENSTMISSING.1|ENSGMISSING.1|-|-|MISSING-201|MISSING|700|"
        records.append((missing_header, sequence))

        try:
            selected, counts = self.module.select_queries(
                fasta_records=records,
                transcripts=transcripts,
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )
        except ValueError as error:
            self.fail(f"valid metadata-missing FASTA record was not excluded: {error}")

        self.assertEqual(len(selected), 50)
        self.assertEqual(counts["input_query_record_count"], 51)
        self.assertEqual(counts["excluded_missing_gtf_metadata_count"], 1)

        metadata = self.module.Transcript(
            transcript_id="ENSTMISSING.1",
            gene_id="ENSGGTF.1",
            gene_name="MISSING",
            gene_type="lncRNA",
            chromosome="chr1",
            start=1,
            end=700,
            strand="+",
            level=1,
            tags=frozenset({"basic"}),
        )
        with self.assertRaisesRegex(ValueError, "FASTA/GTF gene mismatch"):
            self.module.select_queries(
                fasta_records=[
                    ("ENSTMISSING.1|ENSGFASTA.1|-|-|MISSING-201|MISSING|700|", sequence)
                ],
                transcripts={"ENSTMISSING.1": metadata},
                development_exclusions=self.no_development_exclusions(),
                holdout_gene_ids=set(),
                holdout_sequence_sha256=set(),
            )

    def test_target_representative_priority_is_exact(self) -> None:
        chosen = self.module.choose_target_representative(self.same_target_gene)
        self.assertEqual(chosen.transcript_id, "ENST_MANE.1")
        ordered = sorted(self.same_target_gene, key=self.module.target_representative_key)
        self.assertEqual(
            [transcript.transcript_id for transcript in ordered],
            [
                "ENST_MANE.1",
                "ENST_CANONICAL.1",
                "ENST_APPRIS_1.1",
                "ENST_APPRIS_2.1",
                "ENST_BASIC.1",
                "ENST_LEVEL_1.1",
                "ENST_LONG.1",
                "ENST_ID_A.2",
                "ENST_ID_Z.1",
            ],
        )
        self.assertEqual(
            self.module.target_representative_key(chosen),
            (0, 1, 1, 1, 1, 3, -101, "ENST_MANE.1"),
        )
        self.assertEqual(
            self.module.choose_target_representative(reversed(self.same_target_gene)),
            chosen,
        )
        with self.assertRaisesRegex(ValueError, "no target candidates"):
            self.module.choose_target_representative([])

    def test_promoter_is_strand_aware_clipped_and_forward_genomic(self) -> None:
        plus = self.module.materialize_promoter(self.plus_transcript, "ACGT" * 7500)
        minus = self.module.materialize_promoter(self.minus_transcript, "ACGT" * 7500)
        clipped = self.module.materialize_promoter(
            self.near_start_transcript, "ACGT" * 7500
        )
        self.assertEqual((plus["region_start"], plus["region_end"]), (8000, 10500))
        self.assertEqual((minus["region_start"], minus["region_end"]), (9500, 12000))
        self.assertEqual(clipped["region_start"], 1)
        self.assertEqual(plus["sequence"], ("ACGT" * 7500)[7999:10500])
        self.assertEqual((plus["tss"], minus["tss"]), (10000, 10000))
        self.assertEqual(len(plus["sequence"]), 2501)
        self.assertEqual(minus["sequence"], ("ACGT" * 7500)[9499:12000])
        self.assertEqual(
            self.module.promoter_bounds(self.near_end_transcript, 30000),
            (29900, 29400, 30000),
        )

        directional_sequence = "A" * 10000 + "C" * 10000 + "G" * 10000
        directional_minus = self.module.materialize_promoter(
            self.minus_transcript, directional_sequence
        )
        reverse_complement = directional_minus["sequence"].translate(
            str.maketrans("ACGT", "TGCA")
        )[::-1]
        self.assertEqual(directional_minus["sequence"], directional_sequence[9499:12000])
        self.assertNotEqual(directional_minus["sequence"], reverse_complement)

    def test_out_of_range_promoter_uses_explicit_empty_sentinel(self) -> None:
        outside = self.target_transcript(
            transcript_id="ENST_OUTSIDE.1",
            gene_id="ENSG_OUTSIDE.1",
            start=11,
            end=11,
            strand="+",
        )
        materialized = self.module.materialize_promoter(outside, "ACGTACGTAC")
        self.assertEqual(
            materialized,
            {
                "transcript_id": "ENST_OUTSIDE.1",
                "gene_id": "ENSG_OUTSIDE.1",
                "gene_name": "ENSG_OUTSIDE",
                "chromosome": "chr21",
                "strand": "+",
                "tss": 11,
                "region_start": 0,
                "region_end": 0,
                "sequence_length": 0,
                "sequence": "",
            },
        )

    def test_target_selection_public_signatures_are_explicit(self) -> None:
        expected_parameters = {
            "read_chromosome_fasta": ("path", "requested_chromosome"),
            "target_representative_key": ("tx",),
            "choose_target_representative": ("transcripts",),
            "promoter_bounds": ("tx", "chromosome_length"),
            "materialize_promoter": ("tx", "chromosome_sequence"),
            "select_targets": ("transcripts", "chromosome_sequences"),
        }
        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                signature = inspect.signature(getattr(self.module, name))
                self.assertEqual(tuple(signature.parameters), parameters)
        select_signature = inspect.signature(self.module.select_targets)
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.KEYWORD_ONLY
                for parameter in select_signature.parameters.values()
            )
        )

    def test_chromosome_fasta_reader_requires_one_exact_requested_record(self) -> None:
        chr21 = self.write_text("chr21.fa", ">chr21\nacgt\n")
        chr22 = self.write_gzip("chr22.fa.gz", ">chr22\ntgca\n")
        self.assertEqual(self.module.read_chromosome_fasta(chr21, "chr21"), "ACGT")
        self.assertEqual(self.module.read_chromosome_fasta(chr22, "chr22"), "TGCA")

        invalid_sources = {
            "wrong-header.fa": (">chr22\nACGT\n", "named exactly 'chr21'"),
            "padded-header.fa": (">chr21 description\nACGT\n", "named exactly 'chr21'"),
            "multiple.fa": (">chr21\nACGT\n>chr22\nTGCA\n", "exactly one FASTA record"),
            "marker-not-first.fa": (" >chr21\nACGT\n", "sequence before FASTA header"),
        }
        for name, (content, message) in invalid_sources.items():
            with self.subTest(name=name):
                path = self.write_text(name, content)
                with self.assertRaisesRegex(ValueError, message):
                    self.module.read_chromosome_fasta(path, "chr21")
        with self.assertRaisesRegex(ValueError, "requested target chromosome"):
            self.module.read_chromosome_fasta(chr21, "chr20")

    def test_target_selection_retains_unique_canonical_genes_and_counts_exclusions(
        self,
    ) -> None:
        transcripts, chromosome_sequences = self.target_selection_fixture()
        duplicate = self.target_transcript(
            transcript_id="ENST_TARGET_DUPLICATE.1",
            gene_id="ENSG_TARGET_0001.7",
            gene_name="TARGET_0001",
            chromosome="chr21",
            start=11000,
            end=11900,
            tags=frozenset({"MANE_Select"}),
        )
        transcripts[duplicate.transcript_id] = duplicate
        noncanonical = self.target_transcript(
            transcript_id="ENST_TARGET_NONCANONICAL.1",
            gene_id="ENSG_TARGET_NONCANONICAL.1",
            chromosome="chr21",
            start=25000,
            end=25800,
        )
        empty = self.target_transcript(
            transcript_id="ENST_TARGET_EMPTY.1",
            gene_id="ENSG_TARGET_EMPTY.1",
            chromosome="chr22",
            start=30001,
            end=30801,
        )
        ignored_type = self.target_transcript(
            transcript_id="ENST_TARGET_LNCRNA.1",
            gene_id="ENSG_TARGET_LNCRNA.1",
            gene_type="lncRNA",
        )
        ignored_chromosome = self.target_transcript(
            transcript_id="ENST_TARGET_CHR20.1",
            gene_id="ENSG_TARGET_CHR20.1",
            chromosome="chr20",
        )
        for transcript in (noncanonical, empty, ignored_type, ignored_chromosome):
            transcripts[transcript.transcript_id] = transcript
        chr21 = list(chromosome_sequences["chr21"])
        chr21[24999] = "N"
        chromosome_sequences["chr21"] = "".join(chr21)

        selected, counts = self.module.select_targets(
            transcripts=transcripts,
            chromosome_sequences=chromosome_sequences,
        )

        self.assertEqual(len(selected), 300)
        stable_gene_ids = [self.module.stable_id(str(row["gene_id"])) for row in selected]
        self.assertEqual(len(set(stable_gene_ids)), 300)
        self.assertEqual(
            next(
                row["transcript_id"]
                for row in selected
                if self.module.stable_id(str(row["gene_id"])) == "ENSG_TARGET_0001"
            ),
            "ENST_TARGET_DUPLICATE.1",
        )
        self.assertTrue(all(row["chromosome"] in {"chr21", "chr22"} for row in selected))
        self.assertTrue(
            all(row["sequence"] and not (set(str(row["sequence"])) - set("ACGT")) for row in selected)
        )
        self.assertEqual(
            [row["target_id"] for row in selected],
            [f"at{index:04d}" for index in range(1, 301)],
        )
        ordering = [
            (
                int(str(row["chromosome"])[3:]),
                int(row["tss"]),
                self.module.stable_id(str(row["gene_id"])),
                str(row["transcript_id"]),
            )
            for row in selected
        ]
        self.assertEqual(ordering, sorted(ordering))
        self.assertEqual(
            counts,
            {
                "annotation_target_candidate_count": 302,
                "retained_target_count": 300,
                "excluded_target_count": 2,
                "excluded_empty_promoter_count": 1,
                "excluded_noncanonical_promoter_count": 1,
                "chr21_annotation_target_candidate_count": 151,
                "chr22_annotation_target_candidate_count": 151,
                "chr21_retained_target_count": 150,
                "chr22_retained_target_count": 150,
                "chr21_excluded_target_count": 1,
                "chr22_excluded_target_count": 1,
            },
        )

    def test_target_selection_counts_non_ascii_promoter_before_hashing(self) -> None:
        transcripts, chromosome_sequences = self.target_selection_fixture()
        non_ascii = self.target_transcript(
            transcript_id="ENST_TARGET_NON_ASCII.1",
            gene_id="ENSG_TARGET_NON_ASCII.1",
            chromosome="chr21",
            start=25000,
            end=25800,
        )
        transcripts[non_ascii.transcript_id] = non_ascii
        chr21 = list(chromosome_sequences["chr21"])
        chr21[24999] = "é"
        chromosome_sequences["chr21"] = "".join(chr21)

        materialized = self.module.materialize_promoter(
            non_ascii,
            chromosome_sequences["chr21"],
        )
        self.assertNotIn("sequence_sha256", materialized)
        selected, counts = self.module.select_targets(
            transcripts=transcripts,
            chromosome_sequences=chromosome_sequences,
        )

        self.assertEqual(len(selected), 300)
        self.assertEqual(counts["annotation_target_candidate_count"], 301)
        self.assertEqual(counts["retained_target_count"], 300)
        self.assertEqual(counts["excluded_target_count"], 1)
        self.assertEqual(counts["excluded_noncanonical_promoter_count"], 1)
        self.assertEqual(counts["excluded_empty_promoter_count"], 0)
        self.assertEqual(counts["chr21_excluded_target_count"], 1)
        self.assertTrue(
            all(
                row["sequence_sha256"]
                == self.module.sequence_sha256(str(row["sequence"]))
                for row in selected
            )
        )

    def test_target_selection_is_deterministic_under_mapping_reversal(self) -> None:
        transcripts, chromosome_sequences = self.target_selection_fixture()
        expected = self.module.select_targets(
            transcripts=transcripts,
            chromosome_sequences=chromosome_sequences,
        )
        reversed_transcripts = dict(reversed(tuple(transcripts.items())))
        reversed_chromosomes = dict(reversed(tuple(chromosome_sequences.items())))
        actual = self.module.select_targets(
            transcripts=reversed_transcripts,
            chromosome_sequences=reversed_chromosomes,
        )
        self.assertEqual(actual, expected)

    def test_target_selection_requires_minimum_and_both_chromosomes(self) -> None:
        too_few, chromosome_sequences = self.target_selection_fixture(299, 149)
        with self.assertRaisesRegex(ValueError, "only 299 retained targets; 300 required"):
            self.module.select_targets(
                transcripts=too_few,
                chromosome_sequences=chromosome_sequences,
            )

        one_chromosome, chromosome_sequences = self.target_selection_fixture(300, 300)
        with self.assertRaisesRegex(ValueError, "no retained target on chr22"):
            self.module.select_targets(
                transcripts=one_chromosome,
                chromosome_sequences=chromosome_sequences,
            )

    def test_target_selection_rejects_malformed_mappings_and_aliases(self) -> None:
        transcript = self.target_transcript(
            transcript_id="ENST_MAPPING.1",
            gene_id="ENSG_MAPPING.1",
        )
        chromosome_sequences = {
            "chr21": self.chromosome_sequence,
            "chr22": self.chromosome_sequence,
        }
        with self.assertRaisesRegex(ValueError, "chromosome sequences must contain exactly"):
            self.module.select_targets(
                transcripts={transcript.transcript_id: transcript},
                chromosome_sequences={"chr21": self.chromosome_sequence},
            )
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            self.module.select_targets(
                transcripts={transcript.transcript_id: transcript},
                chromosome_sequences={"chr21": "", "chr22": self.chromosome_sequence},
            )
        with self.assertRaisesRegex(ValueError, "transcript mapping key"):
            self.module.select_targets(
                transcripts={"ENST_ALIAS_KEY.1": transcript},
                chromosome_sequences=chromosome_sequences,
            )

        stable_transcript_aliases = {
            "ENST_STABLE_ALIAS.1": self.target_transcript(
                transcript_id="ENST_STABLE_ALIAS.1",
                gene_id="ENSG_ALIAS_ONE.1",
            ),
            "ENST_STABLE_ALIAS.2": self.target_transcript(
                transcript_id="ENST_STABLE_ALIAS.2",
                gene_id="ENSG_ALIAS_TWO.1",
            ),
        }
        with self.assertRaisesRegex(ValueError, "duplicate stable transcript ID"):
            self.module.select_targets(
                transcripts=stable_transcript_aliases,
                chromosome_sequences=chromosome_sequences,
            )

        stable_gene_aliases = {
            "ENST_GENE_ALIAS_ONE.1": self.target_transcript(
                transcript_id="ENST_GENE_ALIAS_ONE.1",
                gene_id="ENSG_GENE_ALIAS.1",
                gene_name="GENE_ALIAS",
            ),
            "ENST_GENE_ALIAS_TWO.1": self.target_transcript(
                transcript_id="ENST_GENE_ALIAS_TWO.1",
                gene_id="ENSG_GENE_ALIAS.2",
                gene_name="GENE_ALIAS",
            ),
        }
        with self.assertRaisesRegex(ValueError, "stable gene ID.*conflicting identity"):
            self.module.select_targets(
                transcripts=stable_gene_aliases,
                chromosome_sequences=chromosome_sequences,
            )

    def test_target_selection_rejects_out_of_domain_levels(self) -> None:
        valid_transcripts, chromosome_sequences = self.target_selection_fixture()
        for (transcript_id, transcript), level in zip(
            tuple(valid_transcripts.items())[:4],
            (1, 2, 3, 99),
            strict=True,
        ):
            valid_transcripts[transcript_id] = replace(transcript, level=level)
        selected, _ = self.module.select_targets(
            transcripts=valid_transcripts,
            chromosome_sequences=chromosome_sequences,
        )
        self.assertEqual(len(selected), 300)

        for invalid_level in (0, -1, 4, 98, 100):
            with self.subTest(invalid_level=invalid_level):
                transcripts, chromosome_sequences = self.target_selection_fixture()
                transcript_id = next(iter(transcripts))
                transcripts[transcript_id] = replace(
                    transcripts[transcript_id],
                    level=invalid_level,
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "target transcript level must be one of 1, 2, 3, 99",
                ):
                    self.module.select_targets(
                        transcripts=transcripts,
                        chromosome_sequences=chromosome_sequences,
                    )

    def test_target_selection_rejects_unhashable_strand_with_value_error(self) -> None:
        transcripts, chromosome_sequences = self.target_selection_fixture()
        transcript_id = next(iter(transcripts))
        transcripts[transcript_id] = replace(
            transcripts[transcript_id],
            strand=[],
        )
        with self.assertRaisesRegex(
            ValueError,
            "target transcript strand",
        ):
            self.module.select_targets(
                transcripts=transcripts,
                chromosome_sequences=chromosome_sequences,
            )


def _resource_probe_payload(scenario: str) -> dict[str, object]:
    import resource

    case_class = ApplicationPanelBuilderTests
    case_class.setUpClass()
    case = case_class(methodName="runTest")
    case.setUp()
    try:
        case.prepare_freeze_fixture()
        lncrna_size_bytes = case.synthetic_inputs.lncrna_fasta.stat().st_size
        if scenario == "memory-stream":
            record_size = 1024 * 1024
            sequence = "A" * record_size
            with case.synthetic_inputs.lncrna_fasta.open(
                "a",
                encoding="ascii",
            ) as handle:
                for index in range(64):
                    handle.write(
                        f">ENST_BULK_{index:05d}.1|ENSG_BULK_{index:05d}.1|-|-|"
                        f"BULK{index:05d}-201|BULK{index:05d}|{record_size}|\n"
                    )
                    handle.write(sequence)
                    handle.write("\n")
            del sequence
            lncrna_size_bytes = case.synthetic_inputs.lncrna_fasta.stat().st_size
            updated_specs = list(case.synthetic_inputs.source_specs)
            updated_specs[0] = case.fixture_source_spec(
                updated_specs[0],
                case.synthetic_inputs.lncrna_fasta,
            )
            case.synthetic_inputs = replace(
                case.synthetic_inputs,
                source_specs=tuple(updated_specs),
            )

        before = fingerprint_tree_no_follow(case.output_paths.repository_root)
        if scenario == "fd-valid":
            soft_limit = 256
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (soft_limit, resource.getrlimit(resource.RLIMIT_NOFILE)[1]),
            )
        elif scenario == "fd-rollback":
            soft_limit = 368
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (soft_limit, resource.getrlimit(resource.RLIMIT_NOFILE)[1]),
            )
        elif scenario == "memory-stream":
            address_limit = 128 * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (address_limit, resource.getrlimit(resource.RLIMIT_AS)[1]),
            )
        else:
            raise ValueError(f"unknown resource probe scenario: {scenario}")

        descriptor_directory = Path("/proc/self/fd")
        fd_before = len(os.listdir(descriptor_directory))
        callback_fd_count: int | None = None

        def after_publish(step: int, _path: Path) -> None:
            nonlocal callback_fd_count
            if step == 1:
                callback_fd_count = len(os.listdir(descriptor_directory))
                if scenario == "fd-rollback":
                    raise RuntimeError("injected low-fd rollback")

        error: list[str] | None = None
        result: dict[str, object] | None = None
        try:
            result = case.module.build_freeze(
                case.synthetic_inputs,
                case.output_paths,
                after_publish=after_publish,
            )
        except BaseException as caught:
            error = [type(caught).__name__, str(caught)]
        after = fingerprint_tree_no_follow(case.output_paths.repository_root)
        payload: dict[str, object] = {
            "setup_complete": True,
            "scenario": scenario,
            "error": error,
            "freeze_id": None if result is None else result["freeze_id"],
            "fd_before": fd_before,
            "fd_after": len(os.listdir(descriptor_directory)),
            "callback_fd_count": callback_fd_count,
            "repository_unchanged": before == after,
            "application_exists": case.output_paths.application_inputs.exists(),
            "stage_names": sorted(
                path.name
                for path in case.work.glob(".*.application-freeze-stage.*")
            ),
            "lncrna_size_bytes": lncrna_size_bytes,
        }
        return payload
    finally:
        case.tearDown()


if __name__ == "__main__":
    resource_probe = os.environ.get("APPLICATION_PANEL_RESOURCE_PROBE")
    if resource_probe is None:
        unittest.main(verbosity=2)
    else:
        print(json.dumps(_resource_probe_payload(resource_probe), sort_keys=True))
