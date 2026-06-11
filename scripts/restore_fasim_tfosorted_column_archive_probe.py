#!/usr/bin/env python3
import argparse
import struct
from pathlib import Path


MAGIC = b"FATFOC1\0"
VERSION = 2
COMP = bytes.maketrans(b"ACGTNacgtn", b"TGCANtgcan")
CODE_TO_DIRECTION = {0: b"R", 1: b"L"}
CODE_TO_STRAND = {0: b"ParaPlus", 1: b"ParaMinus", 2: b"AntiPlus", 3: b"AntiMinus"}
HEADER = (
    b"QueryStart\tQueryEnd\tStartInSeq\tEndInSeq\tDirection\tChr\t"
    b"StartInGenome\tEndInGenome\tMeanStability\tMeanIdentity(%)\t"
    b"Strand\tRule\tScore\tNt(bp)\tClass\tMidPoint\tCenter\t"
    b"TFO sequence\tTTS sequence\n"
)


def read_fasta(path: Path) -> bytes:
    parts = []
    with path.open("rb") as handle:
        for line in handle:
            if not line.startswith(b">"):
                parts.append(line.strip().upper())
    return b"".join(parts)


def complement(seq: bytes) -> bytes:
    return seq.translate(COMP).upper()


def reverse_complement(seq: bytes) -> bytes:
    return complement(seq)[::-1]


def target_slice(target: bytes, start: int, end: int, strand_code: int) -> bytes:
    if strand_code == 0:
        return target[start - 1 : end]
    if strand_code == 1:
        return reverse_complement(target[start : end + 1])
    if strand_code == 2:
        return target[start : end + 1][::-1].upper()
    if strand_code == 3:
        return complement(target[start - 1 : end])
    raise SystemExit(f"unknown strand code: {strand_code}")


def get_varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise SystemExit("truncated varint")
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7


def unzigzag(value: int) -> int:
    if value & 1:
        return -((value + 1) >> 1)
    return value >> 1


def decode_delta_varints(payload: bytes, count: int) -> list[int]:
    values = []
    previous = 0
    pos = 0
    for _ in range(count):
        encoded, pos = get_varint(payload, pos)
        previous += unzigzag(encoded)
        values.append(previous)
    if pos != len(payload):
        raise SystemExit("extra delta payload")
    return values


def decode_varints(payload: bytes, count: int) -> list[int]:
    values = []
    pos = 0
    for _ in range(count):
        value, pos = get_varint(payload, pos)
        values.append(value)
    if pos != len(payload):
        raise SystemExit("extra varint payload")
    return values


def decode_bytes(payload: bytes, count: int) -> list[bytes]:
    values = []
    pos = 0
    for _ in range(count):
        size, pos = get_varint(payload, pos)
        value = payload[pos : pos + size]
        if len(value) != size:
            raise SystemExit("truncated bytes payload")
        values.append(value)
        pos += size
    if pos != len(payload):
        raise SystemExit("extra bytes payload")
    return values


def decode_dictionary(payload: bytes, count: int) -> list[bytes]:
    pos = 0
    dict_count, pos = get_varint(payload, pos)
    dictionary = []
    for _ in range(dict_count):
        size, pos = get_varint(payload, pos)
        value = payload[pos : pos + size]
        if len(value) != size:
            raise SystemExit("truncated dictionary value")
        dictionary.append(value)
        pos += size
    values = []
    for _ in range(count):
        idx, pos = get_varint(payload, pos)
        if idx >= len(dictionary):
            raise SystemExit("dictionary index out of range")
        values.append(dictionary[idx])
    if pos != len(payload):
        raise SystemExit("extra dictionary payload")
    return values


def apply_mask(ungapped: bytes, aligned_len: int, mask: bytes) -> bytes:
    out = bytearray()
    pos = 0
    for i in range(aligned_len):
        if (mask[i // 8] >> (i % 8)) & 1:
            out.append(45)
        else:
            if pos >= len(ungapped):
                raise SystemExit("mask consumed beyond ungapped sequence")
            out.append(ungapped[pos])
            pos += 1
    if pos != len(ungapped):
        raise SystemExit(f"mask consumed {pos}, expected {len(ungapped)}")
    return bytes(out)


def parse_block(block: bytes) -> tuple[int, dict[str, list], int]:
    if len(block) < 8:
        raise SystemExit("truncated block header")
    row_count, payload_count = struct.unpack("<II", block[:8])
    if payload_count != 13:
        raise SystemExit(f"bad payload count: {payload_count}")
    pos = 8
    sizes = []
    for _ in range(payload_count):
        if pos + 4 > len(block):
            raise SystemExit("truncated payload size")
        (size,) = struct.unpack("<I", block[pos : pos + 4])
        sizes.append(size)
        pos += 4
    payloads = []
    for size in sizes:
        payload = block[pos : pos + size]
        if len(payload) != size:
            raise SystemExit("truncated payload")
        payloads.append(payload)
        pos += size
    if pos != len(block):
        raise SystemExit("extra block payload")
    values = {
        "q_start": decode_delta_varints(payloads[0], row_count),
        "seq_start": decode_delta_varints(payloads[1], row_count),
        "score": decode_delta_varints(payloads[2], row_count),
        "align_len": decode_delta_varints(payloads[3], row_count),
        "q_len": decode_varints(payloads[4], row_count),
        "target_len": decode_varints(payloads[5], row_count),
        "rule": decode_varints(payloads[6], row_count),
        "nt": decode_varints(payloads[7], row_count),
        "flags": bytes(payloads[8]),
        "stability": decode_dictionary(payloads[9], row_count),
        "identity": decode_dictionary(payloads[10], row_count),
        "tfo_masks": decode_bytes(payloads[11], row_count),
        "tts_masks": decode_bytes(payloads[12], row_count),
    }
    if len(values["flags"]) != row_count:
        raise SystemExit("bad flags payload")
    return row_count, values, 2


def restore_archive(src: Path, dst: Path, query: bytes, target: bytes) -> int:
    rows = 0
    dictionary_payloads = 0
    with src.open("rb") as archive, dst.open("wb") as out:
        if archive.read(len(MAGIC)) != MAGIC:
            raise SystemExit("bad magic")
        raw = archive.read(8)
        if len(raw) != 8:
            raise SystemExit("truncated archive header")
        version, _block_rows = struct.unpack("<II", raw)
        if version != VERSION:
            raise SystemExit(f"bad version: {version}")
        out.write(HEADER)
        while True:
            raw = archive.read(4)
            if len(raw) != 4:
                raise SystemExit("truncated block size")
            (block_size,) = struct.unpack("<I", raw)
            if block_size == 0:
                break
            block = archive.read(block_size)
            if len(block) != block_size:
                raise SystemExit("truncated block")
            row_count, v, block_dictionary_payloads = parse_block(block)
            dictionary_payloads += block_dictionary_payloads
            for i in range(row_count):
                qs = v["q_start"][i]
                ss = v["seq_start"][i]
                score = v["score"][i]
                align_len = v["align_len"][i]
                q_len = v["q_len"][i]
                t_len = v["target_len"][i]
                qe = qs + q_len - 1
                se = ss + t_len - 1
                flags = v["flags"][i]
                direction_code = flags & 0x1
                strand_code = (flags >> 1) & 0x3
                stability = v["stability"][i]
                identity = v["identity"][i]
                tfo_mask = v["tfo_masks"][i]
                tts_mask = v["tts_masks"][i]
                tfo = apply_mask(query[qs - 1 : qe], align_len, tfo_mask)
                tts = apply_mask(target_slice(target, ss, se, strand_code), align_len, tts_mask)
                midpoint = (qs + qe) // 2
                fields = [
                    str(qs).encode(),
                    str(qe).encode(),
                    str(ss).encode(),
                    str(se).encode(),
                    CODE_TO_DIRECTION[direction_code],
                    b"",
                    str(ss).encode(),
                    str(se).encode(),
                    stability,
                    identity,
                    CODE_TO_STRAND[strand_code],
                    str(v["rule"][i]).encode(),
                    str(score).encode(),
                    str(v["nt"][i]).encode(),
                    b"0",
                    str(midpoint).encode(),
                    str(midpoint).encode(),
                    tfo,
                    tts,
                ]
                out.write(b"\t".join(fields) + b"\n")
            rows += row_count
    return rows, dictionary_payloads


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query-fasta", required=True)
    parser.add_argument("--target-fasta", required=True)
    args = parser.parse_args()
    rows, dictionary_payloads = restore_archive(
        Path(args.archive),
        Path(args.output),
        read_fasta(Path(args.query_fasta)),
        read_fasta(Path(args.target_fasta)),
    )
    print(f"rows={rows}")
    print(f"dictionary_payloads={dictionary_payloads}")
    print(f"restored_bytes={Path(args.output).stat().st_size}")


if __name__ == "__main__":
    main()
