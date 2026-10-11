"""Copy unchanged v4 tables, scalar macros and first-party figures.

Run from a full project checkout; the resulting TeX directory is standalone.
This does not recompute data or overwrite any manuscript input.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANUSCRIPT = ROOT / "manuscript" / "software"
COPIES = {
    "manuscript/software/compact-scalars.generated.tex": "facts.tex",
    "manuscript/software/compact-outcomes.generated.tex": "outcomes.tex",
    "manuscript/software/compact-wells.generated.tex": "wells.tex",
    "manuscript/software/r-frontend.generated.tex": "r-timing.tex",
    "figures/compact-final-v1/ordinary-cost-overview.pdf": "figures/ordinary-cost-overview.pdf",
    "figures/manuscript-review-v2/error-cost-final/error-cost-overview.pdf": "figures/error-cost-overview.pdf",
    "figures/manuscript-review-v2/mixture/mixture-example.pdf": "figures/mixture-example.pdf",
}
EXTRA_SOURCES = [
    "manuscript/software/软件与基准研究.tex",
    "manuscript/software/补充材料.tex",
    "manuscript/software/revision-configuration.generated.tex",
    "manuscript/software/revision-reference.generated.tex",
    "manuscript/software/targeted-h1-main.generated.tex",
    "manuscript/software/targeted-h1-si.generated.tex",
    "manuscript/software/targeted-l2-main.generated.tex",
    "manuscript/software/targeted-l2-si.generated.tex",
    "manuscript/software/w1-enclosure-method.tex",
    "manuscript/software/w1-enclosure-results.tex",
    "manuscript/software/nuts-localization-si.generated.tex",
    "manuscript/software/review3-scalars.generated.tex",
    "manuscript/software/references.tex",
    "manuscript/software/w1-method-references.tex",
    "docs/SUBMISSION-RC1.md",
    "docs/SUBMISSION-REPRODUCE.md",
    "docs/AUTHOR-DECISIONS.md",
    "docs/WINDOWS-NUTS-MAC-REVIEW.md",
    "examples/paper-api.R",
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    entries = []
    for source, target in COPIES.items():
        src, dst = ROOT / source, HERE / target
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        assert sha(src) == sha(dst)
        entries.append({"source": source, "destination": target, "sha256": sha(src), "copied_unchanged": True})
    for source in EXTRA_SOURCES:
        entries.append({"source": source, "sha256": sha(ROOT / source), "copied_unchanged": False})

    keys = set("zoltowski grazzi stan bridgestan blackjax pyro comparemcmcs posterior parallelmcmc bayesforge gonzalez vehtari modrak owen arb dlmfquadrature".split())
    raw = (MANUSCRIPT / "references.tex").read_text() + "\n" + (MANUSCRIPT / "w1-method-references.tex").read_text()
    bib = []
    for line in raw.splitlines():
        m = re.match(r"\\bibitem\{([^}]+)\}", line)
        if m and m.group(1) in keys:
            bib.append(line)
    assert {re.match(r"\\bibitem\{([^}]+)\}", line).group(1) for line in bib} == keys
    (HERE / "references.tex").write_text("% Selected unchanged entries from frozen v4; scientific usage is described in the documents.\n\\begin{thebibliography}{99}\\small\\setlength{\\itemsep}{3pt}\n" + "\n".join(bib) + "\n\\end{thebibliography}\n")
    payload = {
        "schema": "parallelbayes-chinese-reports-v1",
        "date": "2026-10-12",
        "scientific_basis": "Chinese manuscript v4; submission-v4-rc1",
        "parent_candidate_commit": "b84e9663f2742a559e5fb353c475139e2fce8d97",
        "paper_build_commit": "699e645af9051a4ef47c3e40bedd28d741e2e689",
        "new_formal_sampling": 0,
        "new_gpu_measurements": 0,
        "sources": entries,
        "reference_policy": "Selected existing v4 entries; no new literature audit claimed.",
    }
    (HERE / "PROVENANCE.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"unchanged_copies": len(COPIES), "source_bindings": len(entries), "bibliography_entries": len(bib)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
