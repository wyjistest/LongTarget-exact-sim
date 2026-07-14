#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from fasim_segment_ownership import segment_starts


ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "scripts" / "merge_fasim_segmented_tfosorted.py"
OWNERSHIP = ROOT / "scripts" / "fasim_segment_ownership.py"
COMPARE = ROOT / "scripts" / "compare_fasim_segmented_contract.py"


@dataclass(frozen=True)
class CandidateReceipt:
    name: str
    path: Path
    contract: dict[str, str]
    ownership: dict[str, str] | None = None


def _required_path(name: str, default: Path) -> Path:
    path = Path(os.environ.get(name, str(default))).resolve()
    if not path.is_file():
        raise SystemExit(f"missing {name}: {path}")
    return path


def _positive_int(name: str, default: int, *, allow_zero: bool = False) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer: {raw!r}") from exc
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise SystemExit(f"{name} must be >= {minimum}")
    return value


def _read_fasta(path: Path) -> tuple[str, str]:
    header = ""
    parts: list[str] = []
    records = 0
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                records += 1
                if records == 1:
                    header = line[1:].split()[0]
                continue
            parts.append(line.upper())
    if records != 1 or not parts:
        raise SystemExit(f"expected exactly one non-empty FASTA record: {path}")
    return header, "".join(parts)


def _parse_metrics(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            metrics[key] = value
    return metrics


def _write_metrics(path: Path, metrics: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for key, value in metrics.items():
            handle.write(f"{key}={value}\n")


def _run(command: list[str], stdout: Path, stderr: Path | None = None, allowed: set[int] = {0}) -> int:
    with stdout.open("w", encoding="utf-8") as output:
        if stderr is None:
            result = subprocess.run(command, cwd=ROOT, text=True, stdout=output, stderr=subprocess.PIPE)
        else:
            with stderr.open("w", encoding="utf-8") as error:
                result = subprocess.run(command, cwd=ROOT, text=True, stdout=output, stderr=error)
    if result.returncode not in allowed:
        detail = result.stderr.strip() if stderr is None and result.stderr else ""
        raise SystemExit(
            f"command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{detail}" if detail else "")
        )
    return result.returncode


def _find_output(directory: Path) -> Path:
    outputs = sorted(
        path for path in directory.iterdir() if path.is_file() and path.name.endswith("-TFOsorted")
    )
    if len(outputs) != 1:
        raise SystemExit(f"expected exactly one TFOsorted in {directory}; found {len(outputs)}")
    return outputs[0]


def _run_cpu(binary: Path, target: Path, query: Path, rule: int, output: Path) -> Path:
    output.mkdir(parents=True)
    environment = {key: value for key, value in os.environ.items() if not key.startswith("FASIM_")}
    environment.update({"FASIM_OUTPUT_MODE": "tfosorted", "FASIM_VERBOSE": "0"})
    with (output / "stdout.log").open("w", encoding="utf-8") as stdout, (
        output / "stderr.log"
    ).open("w", encoding="utf-8") as stderr:
        result = subprocess.run(
            [str(binary), "-f1", str(target), "-f2", str(query), "-r", str(rule), "-O", str(output)],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=stdout,
            stderr=stderr,
        )
    if result.returncode != 0:
        raise SystemExit(f"CPU authority command failed ({result.returncode}); see {output / 'stderr.log'}")
    return _find_output(output)


def _write_segment_fasta(
    path: Path,
    source_header: str,
    sequence: str,
    segment_id: int,
    shift: int,
    start: int,
    end: int,
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(
            f">{source_header}|segment_id={segment_id}|grid_shift={shift}|"
            f"global_query_start={start}|global_query_end={end}\n"
        )
        for offset in range(start, end, 80):
            handle.write(sequence[offset : min(offset + 80, end)] + "\n")


def _compare(authority: Path, candidate: Path, output: Path) -> dict[str, str]:
    _run(
        [
            sys.executable,
            str(COMPARE),
            "--baseline",
            str(authority),
            "--candidate",
            str(candidate),
            "--k",
            "5",
        ],
        output,
        allowed={0, 1},
    )
    return _parse_metrics(output)


def _candidate_clean(metrics: dict[str, str]) -> bool:
    return (
        metrics.get("full_missing_rows") == "0"
        and metrics.get("full_extra_rows") == "0"
        and metrics.get("all_three_top5_equal") == "1"
        and metrics.get("boundary_ties_equal") == "1"
    )


def main() -> int:
    if os.environ.get("FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW", "0") != "1":
        raise SystemExit("set FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=1 to run this shadow-only characterization")

    binary = _required_path("BIN", ROOT / ".tmp" / "fasim_longtarget_gasal2_direct")
    target = _required_path("TARGET", ROOT / "testDNA.fa")
    query = _required_path("RNA", ROOT / "H19.fa")
    rule = _positive_int("RULE", 0, allow_zero=True)
    segment_length = _positive_int("SEGMENT_LEN", 2048)
    segment_overlap = _positive_int("SEGMENT_OVERLAP", 512, allow_zero=True)
    if segment_overlap >= segment_length:
        raise SystemExit("SEGMENT_OVERLAP must be smaller than SEGMENT_LEN")
    try:
        shifts = [int(value) for value in os.environ.get("GRID_SHIFTS", "0 128 256").split()]
    except ValueError as exc:
        raise SystemExit("GRID_SHIFTS must contain integers") from exc
    if len(shifts) < 2 or len(set(shifts)) != len(shifts) or any(shift < 0 for shift in shifts):
        raise SystemExit("GRID_SHIFTS must contain at least two distinct non-negative shifts")

    work = Path(
        os.environ.get(
            "WORK", str(ROOT / ".tmp" / "characterize_fasim_segment_ownership_h19")
        )
    ).resolve()
    if work.exists():
        raise SystemExit(f"WORK already exists; refusing to overwrite evidence: {work}")
    work.mkdir(parents=True)
    grids = work / "grids"
    grids.mkdir()

    source_header, sequence = _read_fasta(query)
    query_length = len(sequence)
    authority = _run_cpu(binary, target, query, rule, work / "authority")
    with authority.open(newline="", encoding="utf-8") as handle:
        authority_rows = sum(1 for _ in csv.DictReader(handle, delimiter="\t"))

    candidates: list[CandidateReceipt] = []
    grid_merged: list[tuple[int, Path]] = []
    for shift in shifts:
        grid = grids / f"shift_{shift}"
        grid.mkdir()
        starts = segment_starts(
            query_length, segment_length, segment_overlap, shift
        )
        segment_manifest = grid / "segment_outputs.tsv"
        with segment_manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["segment_id", "global_start", "global_end", "tfosorted"])
            for segment_id, start in enumerate(starts):
                end = min(start + segment_length, query_length)
                fasta = grid / f"segment_{segment_id:03d}.fa"
                _write_segment_fasta(
                    fasta, source_header, sequence, segment_id, shift, start, end
                )
                tfosorted = _run_cpu(
                    binary, target, fasta, rule, grid / f"run_{segment_id}"
                )
                writer.writerow([segment_id, start, end, tfosorted])

        merged = grid / "merged-TFOsorted"
        _run(
            [
                sys.executable,
                str(MERGE),
                "--segments",
                str(segment_manifest),
                "--output",
                str(merged),
            ],
            grid / "merge-summary.txt",
        )
        grid_merged.append((shift, merged))
        merged_contract = _compare(authority, merged, grid / "merged-contract.txt")
        candidates.append(CandidateReceipt(f"shift_{shift}_merged", merged, merged_contract))

        descriptors = grid / "ownership-descriptors.tsv"
        _run(
            [
                sys.executable,
                str(OWNERSHIP),
                "derive",
                "--segments",
                str(segment_manifest),
                "--grid-shift",
                str(shift),
                "--query-length",
                str(query_length),
                "--output",
                str(descriptors),
            ],
            grid / "ownership-derive.txt",
        )
        ownership_output = grid / "ownership-TFOsorted"
        ownership_summary = grid / "ownership-summary.txt"
        _run(
            [
                sys.executable,
                str(OWNERSHIP),
                "shadow",
                "--segments",
                str(segment_manifest),
                "--descriptors",
                str(descriptors),
                "--authority",
                str(authority),
                "--output",
                str(ownership_output),
                "--db",
                str(grid / "ownership.sqlite"),
                "--summary",
                str(ownership_summary),
            ],
            grid / "ownership-stdout.txt",
        )
        ownership_metrics = _parse_metrics(ownership_summary)
        ownership_contract = _compare(
            authority, ownership_output, grid / "ownership-contract.txt"
        )
        candidates.append(
            CandidateReceipt(
                f"shift_{shift}_ownership",
                ownership_output,
                ownership_contract,
                ownership_metrics,
            )
        )

    dual = work / "dual-grid"
    dual.mkdir()
    dual_manifest = dual / "segment_outputs.tsv"
    with dual_manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["segment_id", "global_start", "global_end", "tfosorted"])
        for index, (shift, merged) in enumerate(grid_merged):
            writer.writerow([f"grid_{index}_shift_{shift}", 0, query_length, merged])
    dual_output = dual / "merged-TFOsorted"
    _run(
        [
            sys.executable,
            str(MERGE),
            "--segments",
            str(dual_manifest),
            "--output",
            str(dual_output),
        ],
        dual / "merge-summary.txt",
    )
    dual_contract = _compare(authority, dual_output, dual / "contract.txt")
    candidates.append(CandidateReceipt("dual_grid_merged", dual_output, dual_contract))

    matrix = work / "matrix.tsv"
    with matrix.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "candidate",
            "full_missing_rows",
            "full_extra_rows",
            "clustered_score_top5_equal",
            "clustered_stability_top5_equal",
            "clustered_nt_top5_equal",
            "all_three_top5_equal",
            "boundary_ties_equal",
            "rows_total",
            "rows_owned",
            "rows_no_owner",
            "rows_owner_mismatch_vs_authority",
            "potential_row_reduction_percent",
            "runtime_work_dropped",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            ownership = candidate.ownership or {}
            writer.writerow(
                {
                    "candidate": candidate.name,
                    **{
                        key: candidate.contract.get(key, "unavailable")
                        for key in fieldnames[1:8]
                    },
                    **{
                        key: ownership.get(key, "unavailable")
                        for key in fieldnames[8:]
                    },
                }
            )

    canonical = next(
        candidate for candidate in candidates if candidate.name == f"shift_{shifts[0]}_ownership"
    )
    assert canonical.ownership is not None
    multiple_shift_clean = all(_candidate_clean(candidate.contract) for candidate in candidates)
    short_missing = int(canonical.contract["full_missing_rows"])
    short_extra = int(canonical.contract["full_extra_rows"])
    rows_no_owner = int(canonical.ownership["rows_no_owner"])
    owner_unique = int(canonical.ownership["owner_is_unique"])
    all_three = int(canonical.contract["all_three_top5_equal"])
    boundary_ties = int(canonical.contract["boundary_ties_equal"])
    reduction = float(canonical.ownership["potential_row_reduction_percent"])
    hard_gate = (
        short_missing == 0
        and short_extra == 0
        and rows_no_owner == 0
        and owner_unique == 1
        and all_three == 1
        and boundary_ties == 1
        and multiple_shift_clean
    )
    promotion_gate = hard_gate and reduction >= 20.0
    decision = "pass" if promotion_gate else "no_go"

    summary: dict[str, object] = {
        "authority": authority,
        "authority_rows": authority_rows,
        "query_length": query_length,
        "segment_length": segment_length,
        "segment_overlap": segment_overlap,
        "grid_shifts": " ".join(str(shift) for shift in shifts),
        "grid_shift_count": len(shifts),
        "canonical_shift": shifts[0],
        "short_oracle_missing_rows": short_missing,
        "short_oracle_extra_rows": short_extra,
        "rows_no_owner": rows_no_owner,
        "owner_is_unique": owner_unique,
        "all_three_top5_equal": all_three,
        "boundary_ties_equal": boundary_ties,
        "multiple_shift_matrix_clean": int(multiple_shift_clean),
        "potential_duplicate_or_work_reduction_percent": f"{reduction:.2f}",
        "potential_exact_tasks_removed": "unavailable",
        "potential_tracebacks_removed": "unavailable",
        "runtime_work_dropped": 0,
        "hard_gate_pass": int(hard_gate),
        "promotion_gate_pass": int(promotion_gate),
        "grid_stability_implies_unsegmented_equivalence": 0,
        "phase2_decision": decision,
        "matrix": matrix,
    }
    _write_metrics(work / "summary.txt", summary)
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
