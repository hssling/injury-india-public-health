# Analysis Plan
## Burden of Injuries in India — Step-by-Step Analytic Specification

**Version:** 1.0  
**Date:** 2026-04-23  

---

## Step 0: Environment Setup

```
Python >= 3.11
Libraries: pandas, numpy, scipy, matplotlib, seaborn, geopandas, openpyxl, tabula-py, camelot-py
R >= 4.3 (optional, for ineq package and ggplot cross-validation)
```

Run: `src/utils/setup_env.py` to verify environment.

---

## Step 1: Data Acquisition

**Script:** `src/ingest/01_download_plan.py`

### 1A: GBD 2021 Data
- Navigate to: https://ghdx.healthdata.org/gbd-results
- Select: Location = India + all subnational states/UTs; Cause = Injuries (all L1/L2/L3); Measures = Deaths, DALYs, YLLs, YLDs, Incidence; Years = 2000–2021; Sex = Both/Male/Female; Age = All ages + granular groups; Metric = Number + Rate
- Download as CSV; save to `data_raw/gbd/`
- Log: source URL, access date, file name, SHA256 checksum, size

### 1B: MoRTH 2023
- Navigate to: https://road.transport.gov.in/publications/road-accidents-in-india
- Download: "Road Accidents in India 2023" PDF
- Save to `data_raw/morth/`
- Log as above

### 1C: NCRB ADSI 2023
- Navigate to: https://ncrb.gov.in/adsi.html
- Download: "Accidental Deaths & Suicides in India 2023" PDF
- Save to `data_raw/ncrb/`
- Log as above

### 1D: Shapefile for India States
- Source: https://gadm.org (level 1 = states)
- Or: Government of India DIVA-GIS / GeoBoundaries
- Save to `data_raw/shapefiles/`

**Output:** `logs/acquisition_log.csv` with columns: source, file_name, url, access_date, sha256, size_bytes, status

---

## Step 2: Data Parsing and Extraction

### 2A: GBD CSV Parsing
**Script:** `src/ingest/02_parse_gbd.py`

- Read all CSV files from `data_raw/gbd/`
- Identify columns: location_name, cause_name, sex_label, age_name, year_id, measure_name, metric_name, val, lower, upper
- Filter to India locations only
- Validate: no null values in key fields; values within plausible range
- Output: `data_interim/gbd_raw_combined.parquet` and `.csv`

### 2B: MoRTH PDF Extraction
**Script:** `src/ingest/03_parse_morth.py`

- Use tabula-py or camelot-py to extract tables from MoRTH 2023 PDF
- Target tables: state-wise accidents, deaths, injuries
- If automated extraction fails: generate `data_raw/morth/manual_extraction_template.xlsx`
- QA check: sum of state totals vs. reported national total
- Output: `data_interim/morth_raw.csv`

### 2C: NCRB PDF Extraction
**Script:** `src/ingest/04_parse_ncrb.py`

- Extract accidental deaths by cause (state-wise)
- Extract suicides by method (state-wise)
- QA check: state totals vs. national total
- If extraction fails: generate `data_raw/ncrb/manual_extraction_template.xlsx`
- Output: `data_interim/ncrb_accidental_raw.csv`, `data_interim/ncrb_suicide_raw.csv`

---

## Step 3: Cleaning and Harmonization

### 3A: State Name Harmonization
**Script:** `src/clean/05_harmonize_states.py`

- Load `docs/state_crosswalk.csv` (master state name mapping)
- Apply to GBD, MoRTH, NCRB datasets
- Log all name changes in `logs/state_name_harmonization_log.csv`
- Flag unmatched state names as errors

### 3B: Cause Name Harmonization
**Script:** `src/clean/06_harmonize_causes.py`

- Map GBD cause names to analysis cause groups (see `docs/variable_dictionary.csv`)
- Map MoRTH cause categories to analysis groups
- Map NCRB cause categories to analysis groups
- Log all mappings in `logs/cause_harmonization_log.csv`

### 3C: Age Group Harmonization
**Script:** `src/clean/07_harmonize_ages.py`

- GBD age groups → analysis age groups: 0–4, 5–14, 15–29, 30–49, 50–69, 70+, all-ages
- Derived age groups: 15–49 (productive age), 15–64 (broader productive)
- Log any aggregation steps

### 3D: Master Dataset Assembly
**Script:** `src/clean/08_assemble_master.py`

- Combine cleaned GBD, MoRTH, NCRB into harmonized long-format master
- Schema: `state | year | sex | age_group | cause | measure | metric_type | value | lower_ui | upper_ui | source | note`
- Output: `data_processed/master_dataset.csv` and `.parquet`
- QC: check for duplicates, missingness, implausible values
- Log QC results: `logs/master_qc_log.txt`

---

## Step 4: Core Analyses

### 4A: National Summary
**Script:** `src/analysis/09_national_summary.py`

- Total deaths, DALYs, YLLs, YLDs for all injuries, India, 2000–2021
- Trend tables and figures
- Cause-specific shares (top 5 causes by DALY burden)
- Output: `outputs/national_summary.csv`, `tables/Table_S1_national_trends.xlsx`

### 4B: State-Level Burden
**Script:** `src/analysis/10_state_burden.py`

- State-wise deaths, DALYs, YLLs, YLDs (all injuries, 2021)
- Age-standardized rates
- Top and bottom 5 states by each metric
- Output: `outputs/state_burden_2021.csv`, `tables/Table1_state_burden.xlsx`

### 4C: Fatal–Non-Fatal Decomposition
**Script:** `src/analysis/11_decomposition.py`

- Compute YLD fraction, YLL fraction, YLD:YLL ratio per state per cause
- Output: `outputs/decomposition.csv`, `tables/Table2_decomposition.xlsx`

### 4D: Hidden Disability Burden Index
**Script:** `src/analysis/12_hdbi.py`

- Compute HDBI Definition A: z(YLD rate) − z(death rate)
- Compute HDBI Definition B: rank(YLD rate) − rank(death rate)
- Sort states by HDBI
- Output: `outputs/hdbi.csv`, `tables/Table2b_hdbi.xlsx`

### 4E: State Typology
**Script:** `src/analysis/13_typology.py`

- Classify states into 4 quadrants (median thresholds)
- Sensitivity: 25th/75th percentile thresholds
- Output: `outputs/typology.csv`, `tables/Table3_typology.xlsx`

### 4F: Productive-Age Burden
**Script:** `src/analysis/14_productive_age.py`

- DALYs in 15–49 / all-age DALYs per state
- DALYs in 15–64 / all-age DALYs per state
- Output: `outputs/productive_age.csv`

### 4G: Cause-Specific Analysis
**Script:** `src/analysis/15_cause_specific.py`

- State-cause DALY rate matrix
- Top cause by DALY rate per state
- Road injuries, falls, self-harm, drowning, burns, poisoning, violence
- Output: `outputs/cause_specific.csv`, `tables/Table3_causes.xlsx`

### 4H: Sex and Age Disaggregation
**Script:** `src/analysis/16_sex_age.py`

- Male vs. female DALY rates by state and cause
- Age pyramid of injury burden
- Output: `outputs/sex_age.csv`, `tables/Table4_sex_age.xlsx`

### 4I: Inequality Metrics
**Script:** `src/analysis/17_inequality.py`

- Per year: top:bottom ratio, CV, IQR (of state DALY rates)
- Optional: Gini coefficient
- Trend 2000 vs. 2021
- Output: `outputs/inequality.csv`, `tables/Table_S2_inequality.xlsx`

### 4J: Surveillance–Burden Mismatch
**Script:** `src/analysis/18_mismatch.py`

- Rank states by MoRTH road deaths (2023)
- Rank states by GBD road injury DALYs (2021)
- Compute Spearman correlation; rank difference
- Compare NCRB cause order vs. GBD cause order
- Output: `outputs/mismatch.csv`, `tables/Table5_mismatch.xlsx`

---

## Step 5: Sensitivity Analyses

**Script:** `src/analysis/19_sensitivity.py`

- SA1: Exclude UTs
- SA2: Crude vs. age-standardized rates
- SA3: Alternate HDBI definitions
- SA4: Road injuries only
- SA5: Alternate typology thresholds
- SA6: Exclude data-sparse states
- SA7: Sex-stratified
- SA8: Period comparison
- Output: `outputs/sensitivity_results.csv`, `tables/Table6_sensitivity.xlsx`

---

## Step 6: Figures

**Script:** `src/viz/20_figures.py`

| Figure | Description | File |
|--------|-------------|------|
| Fig 1 | India choropleth: DALY rate by state | `figures/fig1_daly_map.png/svg/pdf` |
| Fig 2 | India choropleth: YLD:YLL ratio / HDBI | `figures/fig2_hdbi_map.png/svg/pdf` |
| Fig 3 | Heatmap: cause × state DALY rates | `figures/fig3_heatmap.png/svg/pdf` |
| Fig 4 | Trend lines: national DALYs 2000–2021 | `figures/fig4_trends.png/svg/pdf` |
| Fig 5 | Quadrant plot: YLL rate vs. YLD rate | `figures/fig5_quadrant.png/svg/pdf` |
| Fig 6 | Rank mismatch plot | `figures/fig6_mismatch.png/svg/pdf` |
| Fig 7 | Age-sex pyramid for injuries | `figures/fig7_age_sex.png/svg/pdf` |
| Fig S1–S5 | Supplementary figures | `figures/supplementary/` |

All figures: 600 dpi PNG, SVG, PDF.

---

## Step 7: QC and Cross-Reference

**Script:** `src/qc/21_qc_full.py`

- Check: all manuscript numbers traceable to output tables
- Check: figure labels match table entries
- Check: no duplicate records in master dataset
- Check: GBD uncertainty intervals are correctly carried
- Output: `outputs/qc_report.html`

---

## Step 8: Manuscript Generation

**Script:** `src/reporting/22_manuscript_draft.py`

- Populate manuscript template with actual numbers from output tables
- Generate `manuscript/manuscript_main_IJMR.md`
- Generate supplementary appendix

---

*End of Analysis Plan v1.0*
