# GASAL2-LongTarget Small Example

The repository root includes the small `H19.fa` query and `testDNA.fa` target.
Safe mode uses the final verified-only routing decision: verified comparison
for eligible named contracts and CPU authority otherwise.
From the repository root, run a no-execution preflight:

```bash
python3 scripts/gasal2_longtarget.py \
  --mode safe \
  --query H19.fa \
  --target testDNA.fa \
  --output /tmp/gasal2-example-output \
  --report /tmp/gasal2-example-report.json \
  --dry-run
```

For a CPU authority smoke:

```bash
make build-fasim
python3 scripts/gasal2_longtarget.py \
  --mode cpu-authority \
  --query H19.fa \
  --target testDNA.fa \
  --output /tmp/gasal2-example-output \
  --report /tmp/gasal2-example-report.json
```

Remove or choose new output and report paths before a second run. The workflow
does not overwrite them without `--force`.
