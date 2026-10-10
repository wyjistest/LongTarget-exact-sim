#!/usr/bin/env python3
"""Reuse the independent forward corpus and add the diagnosed full-query tie."""
import importlib.util
import argparse
import json
import random
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('repair_forward_cases', root / 'reproduce/ssw_cuda/run_phase6_forward.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
groups, _ = module.case_groups()
cases = sum((groups[name] for name in ('tiny_exhaustive', 'adversarial_compact', 'compact_fuzz', 'known_forward', 'large')), [])
parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--tie-receipt', type=Path, required=True)
args = parser.parse_args()
out = args.output
out.mkdir(parents=True, exist_ok=False)
data = module.input_tsv(cases)
extras = []
for case in json.loads(args.tie_receipt.read_text())['cases']:
    extras.append(('w010-' + case['name'], case['query'], case['target']))
rng = random.Random(20261010)
for length in (7, 8, 9, 15, 16, 17, 31, 32, 33, 49, 50, 51, 52, 63, 64, 65,
               127, 128, 129, 255, 256, 257, 491, 492, 493, 2811, 2812, 2813, 4095, 4096):
    query = ''.join(rng.choice('ACGT') for _ in range(length))
    extras.extend([
        ('boundary-match-' + str(length), query, query[:min(length, 128)]),
        ('boundary-random-' + str(length), query, ''.join(rng.choice('ACGTUNacgt') for _ in range(97))),
        ('boundary-repeat-' + str(length), 'A' * length, 'A' * min(length, 129)),
    ])
for number in range(256):
    length = rng.randrange(80, 700)
    query = ''.join(rng.choice('AAGGCT') for _ in range(length))
    start = rng.randrange(length - 50)
    target = list(query[start:start + rng.randrange(50, 160)])
    for _ in range(len(target) // 3):
        target[rng.randrange(len(target))] = rng.choice('ACGT')
    extras.append(('repair-fuzz-' + str(number), query, ''.join(target)))
for name, query, target in extras:
    data += ('\t'.join((name, '0', query.encode().hex(), target.encode().hex(),
                       '0', '0', '0', '0')) + '\n').encode()
(out / 'cases.tsv').write_bytes(data)
(out / 'manifest.json').write_text(json.dumps(dict(
    purpose='development regression; not fresh acceptance', seed=20261010,
    inherited_cases=len(cases), added_cases=len(extras),
    tie_receipt=str(args.tie_receipt.resolve())), indent=2) + '\n')
print(len(cases) + len(extras))
