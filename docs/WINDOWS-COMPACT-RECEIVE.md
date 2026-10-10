# Compact bounded delivery and receiver commands

**Mac update, 2026-10-10:** all 21 components (232,755 files, 29,311,383,786 bytes) and the complete source bundle have now been received and verified. The 4,144-item independent reconstruction is running. Later paragraphs describing an active Windows study or pending catalog are dated sender-side history, not current commands. See [Mac intake](WINDOWS-COMPACT-MAC-INTAKE.md) for the current evidence boundary.

Sampling source stays at `3a37a891896faedc62c0d6af185bfad77696054f` in the
independent Windows execution tree `D:/workspace/ParallelBayes/c`. This delivery
branch adds documentation and a publisher only. It does not change the accepted
253-file sampling source, target, transition kernel, inputs, protocol or gate.
The publisher has a separate source identity and network-free safety tests.

## Components and space

Keep one Windows original and one complete Mac receive tree. Formal evidence,
outer command costs, the complete compact technical acceptance bundle, failures
before acceptance, quiescent registration receipts and source Git bundle are
separate manifest-bound components. A top-level delivery receipt records their
actual manifest SHA256, names, sizes, destinations and source identities. The
old stopped study and original native v2 archives stay at their old identities;
they are not copied as new scientific repetitions.

Do not run planning/hashing, reader analysis or upload bulk blocks concurrently
with scientific measurements. After all six phases close and real owned Jobs
end, perform terminal verify-only and registration snapshots. Freeze complete
member manifests then; a live progress snapshot is not that manifest. Every
failure, partial file and failure-reserve.bin remains in the original component.

The receiver must check its own actual volume and allow approximately 35 GiB
for the formal original plus bounded analysis derivatives, subject to the final
measured component sizes. The conditional 27.51 GiB ledger is not an upper bound.
Windows free bytes cannot supply a Mac volume. No full tar or third complete
formal receive tree is required. Transfer uses a single 256 MiB block cache,
maximum 1 GiB per block and 1 MiB copy buffers.

## Windows sender

These are the implemented commands. Use the final externally recorded manifest
SHA; never use an unverified value supplied by a downloaded file itself.

```powershell
& $pbPython scripts/windows/compact_transfer.py plan --root $component --output $manifest --block-bytes 268435456
& $pbPython scripts/windows/compact_transfer.py emit --root $component --manifest $manifest --manifest-sha256 $manifestHash --index $index --output $block
```

The final packet records exact values for each component and chunk. Block names
in the manifest are `part-000000.bin`, etc.; Release asset names have unique
component/source prefixes and are mapped explicitly to these local block names.
Do not rename a manifest member or silently change an ordinal. Hash failure
retains the failed block and original evidence. Never regenerate actual inputs.

`scripts/delivery/compact_draft_upload.py` is a delivery-only append tool. Its
explicit upload plan has this shape:

```json
{"schema":"compact-draft-assets-v1","assets":[{"name":"unique-asset-name.bin","path":"absolute/local/block/path","bytes":123,"sha256":"actual SHA256"}]}
```

```powershell
& $pbPython scripts/delivery/compact_draft_upload.py --plan $assetPlan --plan-sha256 $assetPlanHash --output $freshReceipt
```

This tool uses the existing authorized Git credential helper in memory. It only
GETs release 403644544 and its paginated assets, and POSTs new attachments to
that release's upload endpoint. It refuses a public/different release, unsafe
endpoint, case alias or a same-name asset with different bytes. Identical remote
assets are reused without upload. It checks GitHub's SHA256 digest and size,
all prior assets, and the final unchanged draft identity. It cannot overwrite,
delete, edit a Release or publish it. Each upload receipt is new; earlier receipts
and unsuccessful attachments are retained. No credential is written to evidence.

## Mac receiver, one complete data tree

Use the received Git bundle or pinned source branch in a separate source checkout.
Use the receiver's already verified native Python/NumPy/SciPy and R/posterior
environment. These commands are cross-platform Python CLIs; execute them on
Mac itself, not a Windows WSL environment. Download only the next block to the
bounded cache and verify its external manifest-bound SHA and size before ingest.
Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1` in that native receiving
shell before reading the immutable tree. Keep all index, analysis, statistics
and report outputs in separate fresh directories; do not create bytecode caches
inside the received source snapshot.

```text
python scripts/windows/compact_transfer.py ingest --manifest MANIFEST --manifest-sha256 VERIFIED_SHA --index ORDINAL --chunk DOWNLOADED_BLOCK --output FRESH_COMPONENT_DIRECTORY
python scripts/windows/compact_transfer.py verify --manifest MANIFEST --manifest-sha256 VERIFIED_SHA --output FRESH_COMPONENT_DIRECTORY
```

Ingest checks preceding block coverage, member paths, file sizes, individual
hashes and partial prefixes before appending. Missing blocks are rejected. Its
state is in a sibling `.receive-state` directory, not inside the delivered
scientific tree. Failed original `.partial` assets remain ordinary evidence
members and cannot collide with receive temporaries. Re-ingestion of a verified
block performs zero new data writes. Delete only the acknowledged disposable
block cache after verifying its exact path and hash; never delete original
Windows evidence or Mac members. The final `verify` supplies the normal
`WINDOWS-RETURN-MANIFEST.json` and its actual external receipt SHA256.

For the formal component received as the directory root:

```text
python scripts/analysis/formal_analyze.py index --delivery FORMAL_DIRECTORY --bundle-relative "" --manifest-sha256 RETURN_MANIFEST_SHA --output FRESH_INDEX
python scripts/analysis/formal_analyze.py run --delivery FORMAL_DIRECTORY --index INDEX --output FRESH_ANALYSIS --rscript NATIVE_RSCRIPT --r-library R_LIBRARY --cross-platform
python scripts/analysis/formal_statistics.py --delivery FORMAL_DIRECTORY --index INDEX --analysis ANALYSIS --output FRESH_STATISTICS
python scripts/analysis/formal_report.py --statistics-directory STATISTICS --manifest-sha256 STATISTICS_SHA256_FILE_HASH --output FRESH_REPORT
```

The Mac reader explicitly records cross-platform comparison. The Windows local
reader does not use that option. Each read processes one original task, never
all trajectories at once; the receiver does not call a sampler or reconstruct
random arrays from seeds. Exact received Windows input bytes remain binding.
All 3,888 main and 256 cache planned rows, failure denominators, known/unknown
costs, L2 unresolved references, W1 uncertified quadrature, NUTS divergences and
undefined diagnostics are retained. Cache initial plus all three prepared calls
must pass path/events and timing before a per-input median or paired ratio is
available; four-input cache summaries do not get BCa intervals.

Save the first analysis SUMMARY and task/output hash snapshot, then rerun the
same `formal_analyze.py run` with `--resume`. Require zero new analyses/sampler
calls and unchanged original analysis assets; SUMMARY is replaceable bookkeeping
and is recorded separately. Mac reconstruction and final figure/PDF review are
an independent gate; Windows technical receiver simulation is not that gate.

## One-component return with a single disposable block

The delivery-only finite wrapper below calls the existing frozen transport and
draft publisher. It uploads the explicit manifest, then emits/uploads/verifies
one block at a time. Only the exact disposable block is removed after its remote
SHA256, size and uploaded state have been acknowledged. The Windows originals
remain untouched. Any failure stops and retains the failed block and receipts;
the wrapper refuses an existing administrative output directory and does not
perform retries or publish the Release.

```powershell
& $pbPython scripts/delivery/compact_component_return.py --root $component --manifest $manifest --manifest-sha256 $manifestHash --prefix $uniqueAssetPrefix --output $freshReturnReceiptDirectory
```

The maximum live disposable block is 256 MiB and copy buffers are 1 MiB. Eight
new artificial transport/cache safety checks and the existing 17 publisher/report
scope checks passed together, 25/0/0, on 2026-10-10. A prior invocation used wrong
test paths and collected no tests (exit 4); its XML/log/native end record remain
in `output/compact-component-return-tests01`. The successful invocation and exact
source/command record are in `output/compact-component-return-tests02`.
These checks add no scientific repetitions and do not establish Mac intake.

The full formal manifest contains 180,582 files and is 73,565,154 bytes. For this
size, the delivery-only sender holds one fully validated metadata map instead
of reparsing a second map for every block. It rehashes both the external manifest
and the prepared map for every block, retains original source-path/size/content
checks, and verifies final identity. Four added cases compare every emitted byte
with the unchanged frozen sender and reject file/map/source tampering. The
joint suite now passes 29/0/0; the earlier 25-case evidence remains at its original
identity. Frozen C execution/transport/receiver source and payload schema remain
unchanged. The new sender has its own committed source hash and costs.

## Complete formal raw component, 2026-10-10

The full Windows reconstruction/statistics/report is also returned as
`windows-compact-postprocess-v3-3a37a89-v1-manifest.json`, external SHA256
`4a3f55e60bb13d1fe08b58deaeedad048d942c130f4433a62efb4c67e4055e3c`,
and part-000000 through part-000022 with that same prefix. Its 42,616 original
members total 6,070,464,691 bytes, including every R binary, reference replay,
bootstrap/statistics input, 45 figure originals, and zero-reanalysis hashes.
This Windows output is a comparison record, not the independent Mac reconstruction.
The final `windows-compact-complete-return-v1-catalog.json` and its separately
downloaded SHA256 enumerate all components and the three-branch source Git bundle.

The existing draft now contains the complete scientific raw component:
`windows-compact-formal-3a37a89-v1-manifest.json`, external SHA256
`38e68557b03e4e153a2321fe6b8e5210c99557500746c86f855480edc81ab75e`,
and `windows-compact-formal-3a37a89-v1-part-000000.bin` through
`windows-compact-formal-3a37a89-v1-part-000073.bin`. It holds 180,582 members,
19,671,228,544 bytes. Every asset's actual ID/size/SHA acknowledgement is in
`execution/windows-compact/receipts/formal-return-20261010/formal-component-upload.json`.
All 74 blocks were SHA-verified remotely; the native command Job ended at
2026-10-10 05:36:17 JST with zero active processes. Original members were not
removed. This is complete remote raw transport, not independent Mac intake.

Use the immutable execution branch `codex/windows-compact-study` at
`3a37a891896faedc62c0d6af185bfad77696054f` for `compact_transfer.py`. The draft
is `windows-completion-v2-20261005` in `AlchemistXC/ParallelBayes`; authorized
GitHub access is required. Download its manifest and verify the SHA above. For
each of the 74 ordinals, download only that named block into the disposable cache,
use its manifest SHA/size and the `ingest` command above, and retain the receipt
before removing that exact disposable block. Do not use overwrite download
options. Final `verify` supplies the receiver's own normal manifest SHA; use
that SHA for the read-only index, not Windows' origin-view manifest SHA.

Windows full-frame analysis and later postprocessing components are still
active/pending at this receipt. Their eventual complete catalog will bind all
technical/failure/cost/analysis/source-history components separately. Existing
draft attachments stay in place and the Release stays draft.

## Historical readiness before full-frame reconstruction

The Windows technical receiver actually reconstructed 34/34 planned rows,
then reused 34 with zero new analysis and unchanged 246 analysis files. Fifteen
additional publisher safety checks pass without network/scientific sampling.
The existing Release was read-only checked as draft with 52 original assets.
Formal measurements are active, so full formal manifests, blocks, statistical
tables and their final SHA values do not yet exist. Final return records must
replace these command variables with measured component addresses and digests;
this document does not claim they have been uploaded or independently received.
