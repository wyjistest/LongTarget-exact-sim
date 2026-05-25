#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_fasim_sharded_worker_gpu_env_hygiene"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/run"

cp "$ROOT/H19.fa" "$WORK/inputs/H19.fa"

python3 - "$ROOT/testDNA.fa" "$WORK/inputs/testDNA_multicontig.fa" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

lines = src.read_text().splitlines()
header = lines[0]
sequence = "".join(line.strip() for line in lines[1:] if line.strip())
mid = len(sequence) // 2
dst.write_text(
    f"{header.replace('chr11', 'chr11_left')}\n{sequence[:mid]}\n"
    f"{header.replace('chr11', 'chr11_right')}\n{sequence[mid:]}\n",
    encoding="utf-8",
)
PY

cat >"$WORK/fake_fasim.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
out_dir = Path(args[args.index("-O") + 1])
target = Path(args[args.index("-f1") + 1])
rna = Path(args[args.index("-f2") + 1])
out_dir.mkdir(parents=True, exist_ok=True)
payload = {
    "target": target.name,
    "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    "fasim_cuda_device": os.environ.get("FASIM_CUDA_DEVICE"),
    "fasim_cuda_devices_present": "FASIM_CUDA_DEVICES" in os.environ,
    "fasim_cuda_devices": os.environ.get("FASIM_CUDA_DEVICES"),
}
(out_dir / f"{target.stem}-{rna.stem}-TFOsorted.lite").write_text(
    "Chr\tStartInGenome\tEndInGenome\tStrand\tRule\tQueryStart\tQueryEnd\t"
    "StartInSeq\tEndInSeq\tDirection\tScore\tNt(bp)\tMeanIdentity(%)\t"
    "MeanStability\n",
    encoding="utf-8",
)
(out_dir / "env.json").write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
PY
chmod +x "$WORK/fake_fasim.py"

FASIM_CUDA_DEVICES=0,1 \
python3 "$ROOT/scripts/fasim_sharded_runner.py" \
  --fasim-bin "$WORK/fake_fasim.py" \
  --target "$WORK/inputs/testDNA_multicontig.fa" \
  --rna "$WORK/inputs/H19.fa" \
  --rule 1 \
  --work-dir "$WORK/run" \
  --manifest "$WORK/run/run_manifest.json" \
  --output-mode lite \
  --workers 2 \
  --gpu-ids 7,8 \
  >"$WORK/stdout.log" \
  2>"$WORK/stderr.log"

python3 - "$WORK/run/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
manifest = json.loads(Path(report["manifest"]).read_text())
seen = {}
for shard in report["per_shard"]:
    env_path = Path(shard["run"]["output_dir"]) / "env.json"
    payload = json.loads(env_path.read_text())
    gpu_id = shard["gpu_id"]
    seen[gpu_id] = payload
    assert payload["cuda_visible_devices"] == gpu_id, payload
    assert payload["fasim_cuda_device"] == "0", payload
    assert payload["fasim_cuda_devices_present"] is False, payload
    overrides = shard["run"]["env_overrides"]
    assert overrides["CUDA_VISIBLE_DEVICES"] == gpu_id, overrides
    assert overrides["FASIM_CUDA_DEVICE"] == "0", overrides
    assert "FASIM_CUDA_DEVICES" not in overrides, overrides

assert set(seen) == {"7", "8"}, seen

manifest_envs = {
    entry["gpu_id"]: entry["env_overrides"]
    for entry in manifest["per_shard"]
}
for gpu_id, overrides in manifest_envs.items():
    assert overrides["CUDA_VISIBLE_DEVICES"] == gpu_id, overrides
    assert overrides["FASIM_CUDA_DEVICE"] == "0", overrides
    assert "FASIM_CUDA_DEVICES" not in overrides, overrides
PY

echo "ok"
