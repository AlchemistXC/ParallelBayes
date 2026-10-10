# Windows compact contract and difference validation

The compact design is a post-start resource amendment. The old full study was
stopped at a task boundary and preserved separately; its 990 valid, 16 numerical
failures and 4 unclassified output failures are not compact repetitions. See
`codex/windows-formal-delivery` commit `fbf7564` and `docs/WINDOWS-FORMAL-HOLD.md`.
No old full-grid driver is called by the new entry points.

## Distinct executable contracts

`compact_contract.py` checks the complete committed metadata design and byte
ledger before constructing a versioned executable plan. Formal identity is
`windows-compact-inference-v1`: 3,888 main tasks, 256 cache probes, 216 fresh
inputs, and three ordered main/cache batches (1,296 main each; 64/64/128 cache).
Technical identity `windows-compact-adapter-validation-v1` has G2/4096 and
W1/1024 only: 18 main, 16 cache, two new input files, zero formal repetitions.
Neither schema is accepted as the historical full-grid protocol. Each capsule
binds the full new source list, actual input hash and compact contract tag.

The transition kernels, affine geometry, independent NumPy oracle and accepted
native Job runtime are unchanged. Only worker request-loading seams are added
to the historical worker implementations; default historical contracts remain
strict. The reader has an explicit compact lifecycle adapter and allocation
branch. Initial and all three prepared cache calls must be valid and timed
before a median or paired ratio is available. Missing cost remains unknown.
Cache n=4 is descriptive, with no bootstrap interval. Main analysis retains
24 original four-chain repetitions, failure denominator 24 and minimum 20
usable observations for the existing pointwise BCa policy.

## Native environment and clean source gate

Use the existing native `D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe`,
`D:/Tools/R-4.6.1/bin/Rscript.exe`, and `D:/Tools/R-library-4.6`; never bootstrap
or change the frozen environment. Read the original external snapshot and lock
paths from the preserved formal receipts. The science lock remains
`D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock`.

All tracked numerical, runtime, analysis, fixture and test sources are committed
with canonical LF bytes before `compact_prepare.py`. The new native gate binds
the same complete list and full actual environment used by formal preparation.
The received native v2 gate (file SHA256 `1b71fc0809c5019140768778572681f076bfbf8e7810523f2aed92047c1dd173`)
is checked as an unchanged numerical/Job foundation, not as permission for new
source. A new `compact-native-acceptance-v1` gate is required for formal work.

## Actual entry points and ordering

```powershell
& $python scripts/windows/compact_prepare.py prepare --technical --output $technical --external $external --host-lock $lock --rscript $rscript --r-library $rlib
& $python scripts/windows/compact_prepare.py verify --bundle $technical
# Run all four compact portable test files and the four affected native cases
# under compact_command.py; save XML under the technical bundle. Ancillary
# tests use --lease $lock; the science driver must not be lease-wrapped.
& $python scripts/windows/compact_batch.py run --bundle $technical --batch 0 --phase main
& $python scripts/windows/compact_batch.py run --bundle $technical --batch 0 --phase cache
# Run main/cache --verify-only twice each; no new execution, task bytes unchanged.
```

`compact_command.py` owns the actual child process collection and persists Job
observations, PID/birth identities, stdout/stderr, source and elapsed cost. No
total duration cutoff is imposed. `compact_batch.py pause --bundle ... --reason ...`
requests a cooperative task-boundary pause: the current Job finishes and seals,
then the next task is not launched. An ended driver is required before explicit
`clear-pause`; it does not dispatch. `compact_sequence.py` persists the ordered
three main/cache stages and stops on open phase, pause or command/resource error.
Resume is explicit. Terminal tasks are verified; numerical failures are not
retried. Only one named main infrastructure retry is allowed by the native runtime.

Preparation reserves complete local capacity; each phase records actual tree
bytes and volume free space. The frozen local bundle allocation is 35 GiB
(technical 2 GiB), plus a planned Windows allowance of 40 GiB and receiver
allowance of 35 GiB, combined 75 GiB. These are separate volume allocations,
not a guarantee. Receiver free capacity must be checked at transfer time. The
unchanged RAM/RSS/Job commit/VRAM/disk guards remain; polling is not a hard RSS
peak and Job commitment is not VRAM.

## Bounded receive and full reconstruction

`compact_transfer.py` implements real `plan`, `emit`, `ingest`, `verify` commands.
Plan and block hashes bind every member and byte range. One block is emitted at
a time (default 256 MiB, maximum 1 GiB; copy buffers 1 MiB); no full tar is
created. Receiver state is outside its immutable data tree. Missing/corrupt/
out-of-order blocks, unsafe paths and conflicting partial prefixes are refused.
Completed files are never overwritten. Re-ingestion performs zero data writes.
Receive temporaries are in the sibling state tree so original failed `.partial`
assets and same-name completed files can both be preserved. The first actual
technical transfer preflight exposed this collision before scientific execution;
its frozen package and exit-1 evidence remain under attempt01.

```powershell
& $python scripts/windows/compact_transfer.py plan --root $technical --output $manifest
# Use the actual manifest file SHA and listed indices/names, sequentially:
& $python scripts/windows/compact_transfer.py emit --root $technical --manifest $manifest --manifest-sha256 $hash --index 0 --output $block
& $python scripts/windows/compact_transfer.py ingest --manifest $manifest --manifest-sha256 $hash --index 0 --chunk $block --output $delivery
& $python scripts/windows/compact_transfer.py verify --manifest $manifest --manifest-sha256 $hash --output $delivery
& $python scripts/analysis/formal_analyze.py index --delivery $delivery --bundle-relative '' --manifest-sha256 $returnManifestHash --output $index
& $python scripts/analysis/formal_analyze.py run --delivery $delivery --index $index --output $analysis --rscript $rscript --r-library $rlib
```

Retain first analysis summary, then explicitly resume and require all 34 rows
reused, zero new analysis and immutable task outputs. Technical receiver
simulation is on Windows and is not independent Mac intake. The new gate CLI
`compact_validate.py seal` requires those receipts, native/portable XML and actual
owned command proofs. Subsequent `verify` is read-only. Formal sampling is not
authorized until that gate qualifies. Full study and Mac final reproduction
remain separate milestones.

## Current evidence

Development receipts are in the independent compact worktree's
`output/compact-development-v1`. As of the candidate source review: 35 compact
portable checks and four affected native behavior cases pass. These development
commands do not constitute the clean-source finite scientific gate. The first
affected regression attempt is retained (53 passes, 2 skips, 18 setup errors);
its R environment arguments and artificial LF lock fixture were corrected.
Real technical and formal results are recorded separately in the work packages.
No private skills, environments or original arrays are Git assets.
