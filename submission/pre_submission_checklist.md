# Pre-Submission Checklist
## Burden of Injuries in India — IJMR Submission

Complete all items before submitting. Mark each ✅ when done.

---

## Data Integrity

- [ ] All raw data files archived in `data_raw/` with SHA256 checksums logged in `logs/acquisition_log.csv`
- [ ] GBD 2021 download parameters documented in `src/ingest/01_download_plan.py`
- [ ] MoRTH 2023 and NCRB 2023 PDFs saved with checksums
- [ ] India shapefile downloaded and logged
- [ ] `data_raw/` is read-only (never modified)

## Reproducibility

- [ ] `python run_all.py` runs without errors on a fresh clone
- [ ] All output tables reproduce from code
- [ ] All figures reproduce from code
- [ ] `logs/` directory contains complete pipeline logs
- [ ] `outputs/qc_report.html` shows overall PASS

## Manuscript Numbers

- [ ] All numbers in Results section traced to output table rows
- [ ] All Table 1 numbers match `outputs/state_burden_2021.csv`
- [ ] All decomposition numbers match `outputs/decomposition.csv`
- [ ] HDBI results match `outputs/hdbi.csv`
- [ ] Inequality metrics match `outputs/inequality.csv`
- [ ] Mismatch results match `outputs/mismatch.csv`
- [ ] National totals cross-checked against GBD 2021 global publications
- [ ] No numbers remain in [BRACKET] placeholders in manuscript

## Figures

- [ ] Fig 1: India DALY choropleth — data-driven (not placeholder)
- [ ] Fig 2: HDBI choropleth — data-driven
- [ ] Fig 3: Cause × state heatmap — data-driven
- [ ] Fig 4: National trends 2000–2021 — data-driven
- [ ] Fig 5: Quadrant plot — data-driven
- [ ] Fig 6: Mismatch rank plot — data-driven
- [ ] Fig 7: Age-sex pyramid — data-driven
- [ ] All figures exported at 600 dpi PNG + SVG + PDF
- [ ] Figure legends complete and self-explanatory
- [ ] All axes labeled with units

## Tables

- [ ] Table 1: State burden — all states with UIs
- [ ] Table 2: Decomposition — YLL and YLD fractions
- [ ] Table 3: Cause-specific burden by state
- [ ] Table 4: Sex and age disaggregation
- [ ] Table 5: Surveillance–burden mismatch
- [ ] Table 6: Sensitivity analyses
- [ ] Supplementary Tables S1–SN complete
- [ ] All tables formatted for journal submission

## References

- [ ] All references in `references/citation_audit.csv` marked `doi_verified = PASS` or `url_verified = PASS`
- [ ] No unverifiable or invented references remain
- [ ] References numbered consecutively in Vancouver style
- [ ] All DOIs resolve correctly
- [ ] All URLs checked for access

## Manuscript Content

- [ ] Title < 250 characters
- [ ] Structured abstract ≤ 250 words (check IJMR guidelines)
- [ ] Keywords: 5–10 MeSH-aligned terms
- [ ] Introduction: objective stated clearly in final paragraph
- [ ] Methods: all components of analysis described
- [ ] Results: no interpretation, only reporting
- [ ] Discussion: principal findings, comparison with literature, implications, limitations
- [ ] Conclusion: addresses all objectives
- [ ] No tracked changes or comments remain
- [ ] British or American spelling consistent throughout (check IJMR preference)

## Author Details

- [ ] All authors listed with full names and affiliations
- [ ] Corresponding author email, phone, and postal address
- [ ] ORCID IDs for all authors (optional but recommended)
- [ ] Author contribution statement (ICMJE format) completed
- [ ] Conflict of interest declaration completed
- [ ] Funding statement completed
- [ ] Acknowledgements completed

## Ethics and Declarations

- [ ] Ethics statement: "No ethics approval required — public secondary data only"
- [ ] Data availability statement completed
- [ ] Code availability statement completed
- [ ] Copyright assignment / publishing agreement (check IJMR)

## Journal-Specific Requirements (IJMR)

- [ ] Check current IJMR author guidelines at https://www.ijmr.org.in
- [ ] Word count within IJMR limits for Original Articles
- [ ] Abstract format correct (Background, Methods, Results, Interpretation)
- [ ] Figure format meets IJMR technical requirements
- [ ] Manuscript file in required format (Word / PDF)
- [ ] All supplementary materials prepared
- [ ] Online submission system registration complete

## Final Review

- [ ] Senior author final read of complete manuscript
- [ ] Statistical analysis independently verified
- [ ] All co-authors have approved the final version
- [ ] Submission confirmation email received

---

*Checklist version 1.0 — 2026-04-23*
