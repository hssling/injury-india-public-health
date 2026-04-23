# Limitations and Risks Register
## Burden of Injuries in India Study

**Version:** 1.0  
**Date:** 2026-04-23  

---

## Methodological Limitations

### L1: GBD Modeled Estimates
**Description:** All GBD metrics (deaths, DALYs, YLLs, YLDs) are modeled estimates, not direct surveillance counts. They incorporate assumptions about cause-of-death attribution, disability weights, and incidence estimation.  
**Impact:** Moderate — estimates have uncertainty intervals; state-level estimates may have wider UIs than national  
**Mitigation:** Report UI at all key points; frame findings in terms of modeled estimates; triangulate with administrative sources  
**Manuscript language:** "GBD 2021 provides modeled estimates with 95% uncertainty intervals..."

### L2: Ecological Fallacy
**Description:** This is a state-level ecological analysis. Associations observed at state level cannot be attributed to individuals.  
**Impact:** High — must be clearly stated  
**Mitigation:** No individual-level causal language; explicitly state ecological design; include in limitations  
**Manuscript language:** "As an ecological analysis, findings cannot be extrapolated to individual-level conclusions..."

### L3: Year Mismatch Between Sources
**Description:** GBD estimates are for 2021; MoRTH and NCRB are for 2023. These are different years with different denominators.  
**Impact:** Moderate — rank and pattern comparisons are qualitative only  
**Mitigation:** Never compare raw numbers across sources; use only rank-based qualitative comparisons; state clearly  
**Manuscript language:** "Administrative data (2023) and GBD estimates (2021) cannot be directly compared numerically..."

### L4: Administrative Underreporting
**Description:** MoRTH and NCRB figures are subject to registration gaps, definitional inconsistencies, and state-level reporting variation.  
**Impact:** Moderate — administrative counts underestimate true burden  
**Mitigation:** Note explicitly; do not treat administrative counts as ground truth  
**Manuscript language:** "Administrative surveillance data are subject to known reporting limitations..."

### L5: GBD State Coverage Gaps
**Description:** Not all Indian union territories have independent subnational GBD estimates; some may be grouped or imputed.  
**Impact:** Low-moderate for UTs; negligible for major states  
**Mitigation:** Conduct sensitivity analysis excluding UTs; note which UTs have reliable estimates  

### L6: Cause Taxonomy Incompatibility
**Description:** GBD cause hierarchy, MoRTH categories, and NCRB categories are not directly equivalent. E.g., 'road injuries' in GBD includes pedestrians, cyclists; MoRTH classifies by road user and vehicle type.  
**Impact:** Moderate — prevents direct cause-level comparisons  
**Mitigation:** Use broad cause groupings; document all harmonization decisions; only qualitative rank comparison  

### L7: Disability Weight Assumptions
**Description:** GBD YLD calculations use disability weights derived from global studies. Weights may not fully reflect India-specific disability experience or health state preferences.  
**Impact:** Low-moderate — affects YLD/DALY decomposition results  
**Mitigation:** Acknowledge limitation; note that comparisons are relative (rank-based) rather than absolute  

### L8: Temporal Trend Caution
**Description:** GBD modeled trends incorporate model assumptions about temporal patterns. Observed trends partly reflect modeling choices.  
**Impact:** Low-moderate  
**Mitigation:** Focus on endpoints (2000 vs. 2021) rather than year-by-year changes; note modeling basis of trends  

---

## Data Acquisition Risks

### R1: GBD Download Complexity
**Risk:** GBD Results Tool requires manual selection of many parameters; large downloads may time out or be split across files  
**Probability:** High  
**Mitigation:** Detailed download instructions in `src/ingest/01_download_plan.py`; checksum validation; merge script for multiple files  

### R2: PDF Extraction Failure (MoRTH/NCRB)
**Risk:** PDF tables may be scan-based or have complex formatting that automated extraction (tabula, camelot) cannot parse cleanly  
**Probability:** Moderate-High  
**Mitigation:** Manual extraction templates generated if automated fails; QA checks against published totals; partial extraction flagged  

### R3: Shapefile Compatibility
**Risk:** GADM or other shapefiles may not have 2021 state boundaries (e.g., J&K bifurcation, Ladakh UT)  
**Probability:** Moderate  
**Mitigation:** Check shapefile version; use most recent available; note any boundary discrepancies  

### R4: State Name Mismatches
**Risk:** GBD, MoRTH, NCRB all use slightly different state names and may differ on UT treatment  
**Probability:** High  
**Mitigation:** Master crosswalk table; fuzzy matching with manual verification; audit log  

---

## Analytic Risks

### R5: Small Number Problems for Small UTs
**Risk:** Small UTs may have highly variable or suppressed GBD estimates; inequality metrics sensitive to outliers  
**Probability:** High for small UTs (Lakshadweep, Andaman, Dadra etc.)  
**Mitigation:** Sensitivity analyses excluding UTs; flag small-number states in tables  

### R6: Uncertainty Interval Propagation
**Risk:** GBD UIs are not independently propagable through derived metrics (e.g., YLD:YLL ratio); standard error cannot be simply computed  
**Probability:** High  
**Mitigation:** Report point estimates for derived metrics; note that UIs are for source metrics only; do not propagate UIs through ratios  

---

## Manuscript and Publication Risks

### R7: Journal Scope Fit
**Risk:** IJMR may prefer focused clinical papers; broad ecological analysis may need strong framing  
**Probability:** Moderate  
**Mitigation:** Lead with policy relevance and national significance; frame as secondary data methodology; clear limitations section  

### R8: Reference Verification Failure
**Risk:** Some cited papers may have changed DOIs, been retracted, or URLs may be broken  
**Probability:** Low-Moderate  
**Mitigation:** Automated DOI/URL validation; manual spot-check; flag uncertain references  

---

## Risk Register Summary

| ID | Type | Severity | Probability | Status |
|----|------|----------|-------------|--------|
| L1 | Methodological | Moderate | Certain | Managed |
| L2 | Methodological | High | Certain | Managed |
| L3 | Methodological | Moderate | Certain | Managed |
| L4 | Methodological | Moderate | Certain | Managed |
| L5 | Methodological | Low | Certain | Managed |
| L6 | Methodological | Moderate | Certain | Managed |
| L7 | Methodological | Low | Certain | Managed |
| L8 | Methodological | Low | Certain | Managed |
| R1 | Data | High | High | Monitor |
| R2 | Data | High | Moderate | Monitor |
| R3 | Data | Moderate | Moderate | Monitor |
| R4 | Data | High | High | Monitor |
| R5 | Analytic | Moderate | High | Monitor |
| R6 | Analytic | Moderate | High | Monitor |
| R7 | Publication | Moderate | Moderate | Monitor |
| R8 | Publication | Low | Low | Monitor |

---

*End of Limitations and Risks Register v1.0*
