# Commands and qualification

Source 7babac5. Run from the repository root; PYTHON is the existing plotting environment recorded in environment.json. OUTPUT is the ignored output/research-completion/formal-report-v1 directory. Private skills are installed separately; no skill code is distributed here.

```text
PYTHONDONTWRITEBYTECODE=1 PB_ALIGNMENT_QA=SKILL/scripts/audit_panel_alignment.py PYTHON -m pytest -p no:cacheprovider tests/handoff/test_formal_report.py --basetemp=OUTPUT/tests-04 --junitxml=OUTPUT/tests-04.xml -q
PYTHONDONTWRITEBYTECODE=1 PB_ALIGNMENT_QA=SKILL/scripts/audit_panel_alignment.py PYTHON -m pytest -p no:cacheprovider tests/handoff/test_formal_report.py -k 'rendered or full_layout or small_frame' --basetemp=OUTPUT/tests-05 --junitxml=OUTPUT/tests-05.xml -q
PYTHONDONTWRITEBYTECODE=1 PB_ALIGNMENT_QA=SKILL/scripts/audit_panel_alignment.py PYTHON -m pytest -p no:cacheprovider tests/handoff/test_formal_report.py -k 'rendered or full_layout' --basetemp=OUTPUT/tests-06 --junitxml=OUTPUT/tests-06.xml -q
PYTHON SKILL/scripts/validate_figure.py scripts/analysis/formal_plots.py
PYTHON SKILL/scripts/audit_pdf_text.py FIGURE.pdf --min-pt 5 --json
PYTHON SKILL/scripts/audit_figure_collisions.py FIGURE.pdf --json-out QA.json --overlay-pdf QA.pdf
PYTHON LATEX_PLUGIN/scripts/compile_latex.py OUTPUT/tests-06/test_rendered_figures_keep_zer0/rendered/report.tex --compiler tectonic --output-directory OUTPUT/build-06 --json
python scripts/analysis/formal_report.py --statistics-directory PREVIOUS_TECHNICAL_FIXTURE/statistics --manifest-sha256 VERIFIED_SHA256 --output OUTPUT/cli-technical --fixture --no-render
```

Exact final audit arguments for all eight PDFs appear in qa-06/SUMMARY.json, with strict panel alignment. The full private alignment auditor is enabled by PB_ALIGNMENT_QA; without it the public wrapper checks only limited edges, not full skill QA. Final PDFs still require font, collision and manual inspection.

Tests-04 passed all 10 checks. Tests-05/06 cover affected rendering/template changes, not additional independent tests. Tests-02 records the intermediate indentation failure; tests-01 includes subsequently fixed string escape warnings. Final tests retain one upstream matplotlib PyparsingDeprecationWarning. Compile-01 failed for a missing standard TeX cache; compile-04/05/06 succeeded. Compile-06 matches the final artificial PDF. A documentation-only staging attempt later failed with a stdin Unicode SyntaxError before execution; rewritten ASCII orchestration succeeded, no scientific artifact changed.

A git diff from a1cc588 is empty for scripts/completion, scripts/windows, r-package/inst/python, examples, benchmark/protocols and the formal Windows prompt. There was no numerical/Windows rerun. Hashes establish archive integrity, not scientific-data presence or convergence.
