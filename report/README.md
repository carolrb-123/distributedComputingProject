# Report Package

This folder contains the report materials for the CSE354 distributed computing
project.

## Main Files

- `ieee_report.md`  
  Full IEEE-style report draft with tables, analysis, results, limitations, and
  references. This is the easiest file to edit.

- `ieee_report.tex`  
  IEEEtran LaTeX starter version of the report. Use this if your instructor
  requires an IEEE LaTeX/PDF submission.

- `screenshots_needed.md`  
  Exact screenshot checklist for the report and presentation.

- `evaluation_summary_table.csv`  
  Clean final table generated from the formal evaluation evidence.

- `figures/*.svg`  
  Generated graphs and architecture diagram.

## Regenerate Graphs

```bash
python3 scripts/generate_report_graphs.py
```

## Recommended Final Report Assembly

1. Use the IEEE conference template required by the course.
2. Copy the contents of `ieee_report.md` into the template.
3. Insert the figures from `report/figures/`.
4. Insert screenshots from `screenshots_needed.md`.
5. Keep the raw evaluation artifacts in `evaluation_results/` as appendix
   evidence.

## If Using LaTeX

IEEE LaTeX usually expects PDF, PNG, or EPS figures. The generated figures are
SVG because they are easy to inspect and import into Word/Google Docs. Convert
the selected SVGs to PDF or PNG before compiling `ieee_report.tex`.
