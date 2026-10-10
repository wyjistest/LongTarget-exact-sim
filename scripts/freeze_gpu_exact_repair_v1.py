#!/usr/bin/env python3
"""Freeze an already-validated independent repair candidate and its evidence."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from check_gpu_exact_repair_v1 import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', required=True, type=Path)
    p.add_argument('--evidence', required=True, type=Path)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence = args.evidence.resolve()
    binary = args.binary.resolve()

    def git(*command):
        return subprocess.check_output(['git', '-C', str(root), *command])

    if git('status', '--porcelain').strip():
        raise RuntimeError('commit the isolated source before freezing')
    timed = json.loads((evidence / 'benchmark_final/summary.json').read_text())
    if len(timed) != 4 or not all(row['byte_equal'] for row in timed):
        raise RuntimeError('AB/BA exactness gate is incomplete')
    plan = json.loads((evidence / 'benchmark_final/plan.json').read_text())
    if sha(binary) != plan['candidate_binary_sha256']:
        raise RuntimeError('binary differs from timed candidate')
    for name in ('components_final', 'host_sanitizers04', 'gpu_memcheck04'):
        if 'cases=973 failures=0' not in (evidence / name / 'stderr.log').read_text():
            raise RuntimeError('component gate is incomplete: ' + name)
    if 'ERROR SUMMARY: 0 errors' not in (evidence / 'gpu_memcheck04/memcheck.log').read_text():
        raise RuntimeError('GPU memory check incomplete')
    faults = json.loads((evidence / 'faults04/summary.json').read_text())
    if len(faults) != 3 or not all(r['returncode'] != 0 and not r['output_published'] for r in faults):
        raise RuntimeError('negative controls failed')

    release = evidence / 'release'
    release.mkdir(exist_ok=False)
    shutil.copy2(binary, release / 'fasim_gpu_exact_repair_v1')
    shutil.copy2(root / 'docs/GPU_EXACT_REPAIR_V1.md', evidence / 'REPORT.md')
    (release / 'repair.patch').write_bytes(git('diff', '--binary', '6e11d3f', 'HEAD'))
    performance = json.loads((evidence / 'benchmark_final/performance.json').read_text())
    receipt = dict(epoch='gpu_exact_repair_20261010_v1', purpose='independent development candidate',
                   source_worktree=str(root), source_branch=git('branch', '--show-current').decode().strip(),
                   source_commit=git('rev-parse', 'HEAD').decode().strip(),
                   inherited_baseline_commit=git('rev-parse', '6e11d3f').decode().strip(),
                   binary_sha256=sha(binary), cuda_object_sha256=sha(root / 'cuda/prealign_cuda.o'),
                   gasal2_library_sha256=sha(root / '.tmp/GASAL2/lib/libgasal.a'),
                   original_dirty_patch_sha256=sha(evidence / 'baseline/inherited_worktree.patch'),
                   exact_output_sha256=timed[0]['output_sha256'], exact_output_data_rows=8291,
                   component_cases=973, performance=performance,
                   production_deployed=False, paper_acceptance_reopened=False,
                   gpu_cigar=False, strict_recomputed_cigar_score_gate=False,
                   limitations=['serial CPU baseline; no OpenMP comparison',
                                'reused development fixtures; no fresh acceptance',
                                'rare canonical-score-decrease branch lacks a natural production fixture'])
    (release / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    manifest = evidence / 'MANIFEST.sha256'
    paths = sorted(path for path in evidence.rglob('*') if path.is_file() and path != manifest)
    manifest.write_text(''.join(sha(path) + '  ' + str(path.relative_to(evidence)) + '\n' for path in paths))
    print(json.dumps(dict(release=str(release), source_commit=receipt['source_commit'],
                          binary_sha256=receipt['binary_sha256'], manifest_files=len(paths)), indent=2))


if __name__ == '__main__':
    main()
