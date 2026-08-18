#!/usr/bin/env python3
"""Prepare the development-only F0 cache and round profile.

The cache is an immutable, fixed-width copy of the already observed endpoint
trace.  It is only suitable for a physical-floor replay on the exact same
query/target epoch.  It is deliberately not a product artifact and contains
no code path that can silently fall back when a descriptor does not match.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import struct
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


MAGIC = b"LQF0CACH"
VERSION = 1
HEADER = struct.Struct("<8sIIIIQQ32s32s32s")
INDEX = struct.Struct("<QQQ")
RECORD = struct.Struct("<Q17i")
ZERO_DIGEST = "0" * 64
REQUIRED = (
    "task_id", "scoreinfo_index", "scoreinfo_position", "scoreinfo_score",
    "attempt_index", "identity_round", "start", "cutlength",
    "prealign_score", "forward_score", "reverse_score", "canonical_score",
    "query_end", "ref_end_local", "ref_end_global", "numeric_path",
    "padded_target_length", "query_length",
)


def integer(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid integer {key}={row.get(key)!r}") from exc


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest_ascii(value: str) -> bytes:
    value = value.strip().lower()
    if value == ZERO_DIGEST:
        return b"0" * 32
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"expected a SHA-256 hex digest, got {value!r}")
    return bytes.fromhex(value)


def replay_group(rows: list[dict[str, str]]) -> dict[str, object]:
    """Return the exact ordered prefix/reverse requests for one group."""

    if not rows:
        raise ValueError("empty group")
    best_score = 0
    best_index: int | None = None
    selected_index: int | None = None
    reason = "empty"
    reverse: set[int] = set()
    processed = 0
    for index, row in enumerate(rows):
        forward = integer(row, "forward_score")
        reverse_score = integer(row, "reverse_score")
        canonical = integer(row, "canonical_score")
        threshold = integer(row, "prealign_score")
        terminal = integer(row, "ref_end_local") == integer(row, "cutlength") - 1
        if canonical != min(forward, reverse_score):
            raise ValueError(f"canonical mismatch at group row {index}")
        if selected_index is not None:
            continue
        processed = index + 1
        if forward >= threshold:
            reverse.add(index)
            if canonical >= threshold:
                selected_index = index
                reason = "threshold"
            elif terminal and canonical > best_score:
                best_score = canonical
                best_index = index
        elif terminal and forward > best_score:
            reverse.add(index)
            if canonical > best_score:
                best_score = canonical
                best_index = index
    if selected_index is None:
        if best_index is not None:
            selected_index = best_index
            reason = "best_fallback"
        else:
            last = len(rows) - 1
            reverse.add(last)
            if integer(rows[last], "canonical_score") != 0:
                selected_index = last
                reason = "last"
    return {
        "processed": processed,
        "reverse": reverse,
        "selected": selected_index,
        "reason": reason,
    }


def iter_groups(reader: Iterable[dict[str, str]]):
    current_key: tuple[int, int] | None = None
    current: list[dict[str, str]] = []
    previous_attempt: dict[int, int] = {}
    for row in reader:
        key = (integer(row, "task_id"), integer(row, "scoreinfo_index"))
        attempt = integer(row, "attempt_index")
        if key[0] in previous_attempt and attempt <= previous_attempt[key[0]]:
            raise ValueError(f"attempt order is not increasing for task {key[0]}")
        previous_attempt[key[0]] = attempt
        if current_key is not None and key < current_key:
            raise ValueError("trace task/group order is not monotonic")
        if current_key is not None and key != current_key:
            yield current
            current = []
        current_key = key
        current.append(row)
    if current:
        yield current


def cut_bin(length: int) -> str:
    if length < 64:
        return "00_<64"
    if length < 128:
        return "01_64_127"
    if length < 256:
        return "02_128_255"
    if length < 512:
        return "03_256_511"
    if length < 1024:
        return "04_512_1023"
    if length < 2048:
        return "05_1024_2047"
    if length < 4096:
        return "06_2048_4095"
    return "07_>=4096"


def prepare(args: argparse.Namespace) -> dict[str, object]:
    trace_sha = digest_file(args.trace)
    profile: dict[str, object] = {
        "schema_version": "long_query_consumer_round_profile_v1",
        "trace_sha256": trace_sha,
        "rounds": {},
        "reasons": Counter(),
        "numeric_path": Counter(),
        "cutlength_bins": {},
        "groups": 0,
        "tasks": set(),
        "attempts": 0,
        "processed_forward_attempts": 0,
        "reverse_requests": 0,
        "full_forward_cells": 0,
        "minimum_forward_cells": 0,
        "full_reverse_cells": 0,
        "minimum_reverse_cells": 0,
        "active_groups_by_round": Counter(),
        "forward_attempts_by_round": Counter(),
        "forward_cells_by_round": Counter(),
        "reverse_requests_by_round": Counter(),
        "reverse_cells_by_round": Counter(),
    }
    # Build records in a temporary stream so the final file can contain its
    # header and task index without retaining 4.3M rows in Python memory.
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="f0-records-", dir=args.cache.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    task_ranges: dict[int, list[int]] = {}
    record_count = 0
    selected_signature = hashlib.sha256()
    try:
        with temp_path.open("wb") as record_out, args.trace.open(
            "r", encoding="utf-8", newline=""
        ) as trace_handle:
            reader = csv.DictReader(trace_handle, delimiter="\t")
            fields = tuple(reader.fieldnames or ())
            missing = [name for name in REQUIRED if name not in fields]
            if missing:
                raise ValueError(f"trace schema missing columns: {missing}")
            for rows in iter_groups(reader):
                group = replay_group(rows)
                task_id = integer(rows[0], "task_id")
                profile["tasks"].add(task_id)
                profile["groups"] += 1
                profile["attempts"] += len(rows)
                profile["processed_forward_attempts"] += int(group["processed"])
                profile["reverse_requests"] += len(group["reverse"])
                profile["reasons"][str(group["reason"])] += 1
                selected_local = group["selected"]
                selected_attempt = (
                    integer(rows[int(selected_local)], "attempt_index")
                    if selected_local is not None else None
                )
                selected_signature.update(
                    f"{task_id}:{selected_attempt}:{group['reason']}\n".encode()
                )
                profile["full_forward_cells"] += sum(integer(r, "forward_cells") for r in rows)
                profile["full_reverse_cells"] += sum(integer(r, "reverse_cells") for r in rows)
                profile["minimum_forward_cells"] += sum(
                    integer(r, "forward_cells") for r in rows[: int(group["processed"])]
                )
                profile["minimum_reverse_cells"] += sum(
                    integer(rows[i], "reverse_cells") for i in group["reverse"]
                )
                for row_index, r in enumerate(rows):
                    round_id = integer(r, "identity_round")
                    path = str(integer(r, "numeric_path"))
                    profile["numeric_path"][path] += 1
                    bucket = cut_bin(integer(r, "cutlength"))
                    bucket_data = profile["cutlength_bins"].setdefault(
                        bucket,
                        {"attempts": 0, "forward_cells": 0, "reverse_cells": 0,
                         "minimum_forward_cells": 0, "minimum_reverse_cells": 0},
                    )
                    bucket_data["attempts"] += 1
                    bucket_data["forward_cells"] += integer(r, "forward_cells")
                    bucket_data["reverse_cells"] += integer(r, "reverse_cells")
                    if row_index < int(group["processed"]):
                        bucket_data["minimum_forward_cells"] += integer(r, "forward_cells")
                    if row_index in group["reverse"]:
                        bucket_data["minimum_reverse_cells"] += integer(r, "reverse_cells")
                    if row_index < int(group["processed"]):
                        profile["forward_attempts_by_round"][round_id] += 1
                        profile["forward_cells_by_round"][round_id] += integer(r, "forward_cells")
                    if row_index in group["reverse"]:
                        profile["reverse_requests_by_round"][round_id] += 1
                        profile["reverse_cells_by_round"][round_id] += integer(r, "reverse_cells")
                    record_out.write(
                        RECORD.pack(
                            task_id,
                            integer(r, "scoreinfo_index"),
                            integer(r, "attempt_index"),
                            integer(r, "scoreinfo_position"),
                            integer(r, "scoreinfo_score"),
                            integer(r, "identity_round"),
                            integer(r, "start"),
                            integer(r, "cutlength"),
                            integer(r, "prealign_score"),
                            integer(r, "forward_score"),
                            integer(r, "reverse_score"),
                            integer(r, "canonical_score"),
                            integer(r, "query_end"),
                            integer(r, "ref_end_local"),
                            integer(r, "ref_end_global"),
                            integer(r, "numeric_path"),
                            integer(r, "padded_target_length"),
                            integer(r, "query_length"),
                        )
                    )
                    record_count += 1
                start = task_ranges.setdefault(task_id, [record_count - len(rows), 0])
                start[1] += len(rows)
                # Active means the ordered prefix still reaches this round.
                for round_id in range(4):
                    if int(group["processed"]) > round_id:
                        profile["active_groups_by_round"][round_id] += 1
        query_sha = digest_ascii(args.query_sha256)
        target_sha = digest_ascii(args.target_sha256)
        with args.cache.open("wb") as cache_out:
            cache_out.write(
                HEADER.pack(
                    MAGIC,
                    VERSION,
                    RECORD.size,
                    int(args.query_length),
                    0,
                    len(task_ranges),
                    record_count,
                    query_sha,
                    target_sha,
                    bytes.fromhex(trace_sha),
                )
            )
            for task_id in sorted(task_ranges):
                first, count = task_ranges[task_id]
                cache_out.write(INDEX.pack(task_id, first, count))
            with temp_path.open("rb") as record_in:
                shutil.copyfileobj(record_in, cache_out, length=8 * 1024 * 1024)
        os.chmod(args.cache, 0o644)
    finally:
        temp_path.unlink(missing_ok=True)

    # Convert counters/sets to deterministic JSON values and derive fractions.
    profile["tasks"] = sorted(profile["tasks"])
    for key in ("reasons", "numeric_path", "active_groups_by_round",
                "forward_attempts_by_round", "forward_cells_by_round",
                "reverse_requests_by_round", "reverse_cells_by_round"):
        profile[key] = {str(k): v for k, v in sorted(profile[key].items())}
    profile["task_count"] = len(profile["tasks"])
    profile["record_count"] = record_count
    round_ids = sorted(
        set(profile["active_groups_by_round"])
        | set(profile["forward_attempts_by_round"])
        | set(profile["reverse_requests_by_round"])
    )
    profile["rounds"] = {
        str(round_id): {
            "active_groups": profile["active_groups_by_round"].get(str(round_id), 0),
            "forward_attempts": profile["forward_attempts_by_round"].get(str(round_id), 0),
            "forward_cells": profile["forward_cells_by_round"].get(str(round_id), 0),
            "reverse_requests": profile["reverse_requests_by_round"].get(str(round_id), 0),
            "reverse_cells": profile["reverse_cells_by_round"].get(str(round_id), 0),
        }
        for round_id in round_ids
    }
    profile["selected_signature_sha256"] = selected_signature.hexdigest()
    profile["full_dp_cells"] = profile["full_forward_cells"] + profile["full_reverse_cells"]
    profile["minimum_dp_cells"] = profile["minimum_forward_cells"] + profile["minimum_reverse_cells"]
    profile["forward_cell_fraction"] = profile["minimum_forward_cells"] / profile["full_forward_cells"]
    profile["reverse_cell_fraction"] = profile["minimum_reverse_cells"] / profile["full_reverse_cells"]
    profile["combined_cell_fraction"] = profile["minimum_dp_cells"] / profile["full_dp_cells"]
    profile["cache"] = {
        "path": str(args.cache),
        "sha256": digest_file(args.cache),
        "format": "LQF0CACH-v1",
        "record_size": RECORD.size,
        "header_size": HEADER.size,
        "index_entry_size": INDEX.size,
        "records": record_count,
        "target_sha256": args.target_sha256,
        "query_sha256": args.query_sha256,
    }
    args.profile.parent.mkdir(parents=True, exist_ok=True)
    with args.profile.open("w", encoding="utf-8") as profile_out:
        json.dump(profile, profile_out, indent=2, sort_keys=True)
        profile_out.write("\n")
    return profile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--query-length", type=int, required=True)
    parser.add_argument("--query-sha256", default=ZERO_DIGEST)
    parser.add_argument("--target-sha256", default=ZERO_DIGEST)
    args = parser.parse_args()
    if not args.trace.is_file():
        parser.error(f"missing trace: {args.trace}")
    profile = prepare(args)
    print(json.dumps({
        "profile": str(args.profile),
        "cache": str(args.cache),
        "cache_sha256": profile["cache"]["sha256"],
        "tasks": profile["task_count"],
        "groups": profile["groups"],
        "attempts": profile["attempts"],
        "forward_cell_fraction": profile["forward_cell_fraction"],
        "reverse_cell_fraction": profile["reverse_cell_fraction"],
        "combined_cell_fraction": profile["combined_cell_fraction"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
