# Contract-Aware GASAL2-LongTarget CLI

`scripts/gasal2_longtarget.py` is the single user entry point for the
submission software workflow. It wraps the existing Fasim authority and
GASAL2 candidate binaries without changing their runtime implementation.

The development version is `0.0.0+submission.1.dev`; it is not an
owner-approved release version.

## Build

CPU authority only:

```bash
make build-fasim
```

CPU authority plus the checked CUDA/GASAL2 candidate:

```bash
make build-fasim build-fasim-gasal2
```

The default binary paths are `./fasim_longtarget_x86` and
`./fasim_longtarget_gasal2`. `--authority-binary` and `--candidate-binary`
select explicit builds when needed.

## Modes

| Mode | Behavior |
| --- | --- |
| `safe` | Default verified-only routing. Uses `verified` for an eligible named contract; otherwise selects CPU authority before execution. `full-output` always selects authority. |
| `verified` | Runs candidate and authority in separate temporary directories. Publishes candidate only when the declared comparator contract is clean; mismatch, candidate failure, OOM or unknown comparator state publishes authority. |
| `fast-experimental` | Explicit opt-in GPU-only native-output path. Writes an `EXPERIMENTAL` stderr warning and `experimental_unverified` report status. It accepts only `--contract auto`, resolves to `experimental-native`, and emits a receipt that says no product contract was satisfied. |
| `cpu-authority` | Runs the existing CPU Fasim authority and publishes its output. |

`safe` eligibility is not a correctness proof. The current wrapper accepts
exactly one query and one target FASTA record per invocation; batch
orchestration must split records into separately reported calls. It also checks
canonical A/C/G/T FASTA, query length at most 2812, one process per GPU, at
least 24000 MiB device memory, compute capability 8.9, executable binaries and
writable non-colliding destinations. Static eligibility does not permit
GPU-only publication; final safety comes from verified comparison or CPU authority.

## Contracts

- `auto` currently resolves to `all-ranked-top5` in safe, verified and authority
  modes. In `fast-experimental`, it resolves to `experimental-native`.
- `score-top5` requires score-ranked clustered TFO1-TFO5 and tie evidence.
- `all-ranked-top5` separately requires score-, stability- and Nt-ranked
  clustered TFO1-TFO5 plus tie evidence.
- `full-output` requires TFOsorted row-set equality in verified mode and is not
  supported by `fast-experimental`.

Named product contracts are rejected in `fast-experimental`; raw unverified
candidate rows are never labelled as `score-top5`, `all-ranked-top5` or
`full-output`.

The post-holdout machine-readable registry records
`verified_only_contract`. All fast contracts remain experimental. `safe`
never treats static eligibility as permission for GPU-only output.

## Usage

```bash
python3 scripts/gasal2_longtarget.py \
  --mode safe \
  --contract auto \
  --query H19.fa \
  --target testDNA.fa \
  --output /tmp/gasal2-longtarget-output \
  --report /tmp/gasal2-longtarget-report.json
```

The report must be outside the output directory. Existing output or report
paths are rejected unless `--force` is explicit. `--dry-run` parses inputs,
checks environment and destinations, and writes a preflight report without
starting a backend or creating final output.

Optional `--assembly` and `--annotation-release` values are copied into the
report as biological metadata. Only rule 0, normal-triplex and top K = 5 are
accepted by this submission contract.

## Atomic publication

Candidate and authority never share an output directory. Each backend runs in
a process group under a private sibling directory named `.partial.*`. The
selected output is copied to a staged publication directory and renamed into
place. A report-write failure removes the new output and restores any
explicitly overwritten output. Signals and timeouts terminate the active
process group and remove only the current workflow's partial directory.

Subprocesses receive argv arrays; input paths are not interpreted by a shell.

For verified `score-top5` and `all-ranked-top5`, the published candidate result
is a contract-labelled canonical TSV generated from the comparator's clustered
candidate representatives. Raw candidate TFOsorted rows are not published
under a narrower top-5 contract. A clean `full-output` contract may publish the
validated candidate TFOsorted directory. Authority keeps its native semantics.
Experimental output includes `contract.json` with
`contract_id=experimental-native`, `status=experimental_unverified`, and
`product_contract_satisfied=false` beside the raw candidate artifact.

## Run report

The JSON report, including its nested input, environment, backend, comparator
and output fields, validates against
`schemas/gasal2_longtarget_run_report.schema.json`. It records input paths,
SHA-256 digests and sequence lengths; requested and resolved contracts;
backend commands, timestamps and wall times; CPU/GPU environment; comparator
results for score, stability and Nt; fallback, guard, OOM and timeout counts;
warnings; the published source; and output sizes and SHA-256 digests.

Unavailable peak RSS, peak GPU memory, CUDA toolkit or biological annotation
values are `null`, not zero. Backend stdout/stderr tails are retained in the
report. Complete streams accompany native authority or experimental output;
verified top-5 candidate publication deliberately excludes raw backend files.
Backend TFOsorted artifacts must also have the current 19-column shape,
parseable finite numeric fields, and valid direction, strand and rule domains
before they can be published or compared.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Final output satisfies the declared contract, or dry-run completed. |
| `2` | Invalid FASTA, unsupported contract or output collision. |
| `3` | Explicit candidate mode requested an unavailable or unchecked GPU environment. |
| `4` | Authority failed; no declared final result was published. |
| `5` | Candidate failed in GPU-only experimental mode; no safe fallback exists. |
| `6` | Comparator failed without a usable authority publication path. |
| `7` | Internal or report-schema failure. |
| `130` | Interrupted; no partial output is published. |

In verified mode, mismatch or candidate/comparator failure with a successful
authority run returns 0 because the published authority output satisfies the
declared contract. The report status and fallback counter retain the event.
