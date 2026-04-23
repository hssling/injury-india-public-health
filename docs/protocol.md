# Study Protocol
## Burden of Injuries in India: State-Level Fatal–Non-Fatal Decomposition, Inequality, and Surveillance–Burden Mismatch using GBD 2021 and Official Indian Secondary Data

**Version:** 1.0  
**Date:** 2026-04-23  
**Status:** Final Draft  

---

## 1. Title

**Primary:** Burden of injuries in India from a public health perspective: state-level fatal–non-fatal decomposition, inequality, and surveillance–burden mismatch using GBD 2021 and official Indian secondary data

**Alternates:**
1. Hidden disability within India's injury burden: a state-level public health analysis
2. Beyond injury deaths in India: state-level trends in DALYs, disability, and surveillance mismatch
3. State-level inequality in injury burden in India: a secondary-data public health analysis

---

## 2. Study Design

- **Design type:** Ecological longitudinal secondary-data analysis
- **Design rationale:** Individual-level data on all injury types and outcomes across all Indian states does not exist in a single unified source. Ecological panel analysis of state-level summary measures from GBD and administrative sources is the appropriate design for population-level burden quantification and inequality analysis.
- **Unit of analysis:** Indian state and union territory (n = up to 36, subject to data availability)
- **Time period:** 2000–2021 for GBD data; 2023 for administrative sources
- **Study population:** All residents of Indian states/UTs

---

## 3. Data Sources

### 3.1 Global Burden of Disease Study 2021 (GBD 2021) — Primary

**Source institution:** Institute for Health Metrics and Evaluation (IHME), University of Washington  
**Access platform:** Global Health Data Exchange (GHDx): https://ghdx.healthdata.org/gbd-results  
**License:** Free for non-commercial academic use  

**Required extracts:**

| Measure | Sex | Age Groups | Year | Location | Cause |
|---------|-----|-----------|------|----------|-------|
| Deaths | Both, Male, Female | All ages, age-standardized, 0–4, 5–14, 15–29, 30–49, 50–69, 70+ | 2000–2021 (5-year intervals + 2021) | India, all states/UTs | All injuries (GBD cause L1), injury subcauses (L2, L3 as available) |
| DALYs | Same | Same | Same | Same | Same |
| YLLs | Same | Same | Same | Same | Same |
| YLDs | Same | Same | Same | Same | Same |
| Incidence | Same | Same | 2021 | Same | Same |
| Prevalence | Same | Same | 2021 | Same | Same (where available) |

**GBD injury cause hierarchy (minimum required):**
- All injuries (Level 1)
- Transport injuries (Level 2)
  - Road injuries (Level 3)
  - Other transport (Level 3)
- Unintentional injuries (Level 2)
  - Falls
  - Drowning
  - Burns (fire, heat, and hot substances)
  - Poisonings (unintentional)
  - Other unintentional
- Intentional injuries (Level 2)
  - Self-harm
  - Interpersonal violence
  - Collective violence / legal intervention (where available)

**GBD metric types:**
- Number (absolute counts with uncertainty intervals)
- Rate (per 100,000 population)
- Age-standardized rate
- Percent (cause fraction, where available)

### 3.2 Ministry of Road Transport and Highways (MoRTH)

**Document:** Road Accidents in India 2023  
**Source:** https://road.transport.gov.in (official MoRTH website)  
**Format:** PDF with embedded tables  

**Required extracts:**
- State-wise road accidents (total)
- State-wise road injury deaths
- State-wise injured persons
- Road user categories (if extractable)
- Road type breakdown (National Highway, State Highway, other)
- Rural/urban breakdown (if available)
- Severity breakdown (fatal, grievous, simple, minor)

### 3.3 National Crime Records Bureau — Accidental Deaths and Suicides in India (NCRB ADSI) 2023

**Document:** ADSI 2023  
**Source:** https://ncrb.gov.in  
**Format:** PDF with embedded tables  

**Required extracts (where reliable):**
- Accidental deaths by cause (state-wise): drowning, falls, poisoning, fire/burns, electrocution, road accidents, railway accidents, others
- Suicides by method (state-wise): hanging, poisoning, drowning, self-immolation, others
- Suicides by age and sex (state-wise)
- Total accidental deaths by state

### 3.4 India State-Level Disease Burden Initiative

**Source:** The Lancet, 2017–2021 (India SLDB papers); PHFI; IHME  
**Use:** Contextual framing, validation of GBD state hierarchy; not primary numeric source  
**Required:** Identify published SLDB papers for state-level injury burden; extract conceptual framing and comparison figures only

---

## 4. State and UT Coverage

**Target:** All 28 states + 8 union territories of India as of 2021 administrative boundaries  
**GBD note:** GBD 2021 covers 35 Indian states/UTs; some smaller UTs may be aggregated  
**Sensitivity:** Analyses will be run with and without union territories  
**State name harmonization:** A master crosswalk table will be maintained linking GBD state names, MoRTH state names, NCRB state names, and ISO codes

---

## 5. Outcomes and Variables

### 5.1 Primary Outcomes

| Variable | Definition | Source | Metric |
|----------|-----------|--------|--------|
| Deaths | All-cause injury deaths | GBD 2021 | Number, rate, age-standardized rate |
| DALYs | Disability-adjusted life years | GBD 2021 | Number, rate, age-standardized rate |
| YLLs | Years of life lost to premature mortality | GBD 2021 | Number, rate |
| YLDs | Years lived with disability | GBD 2021 | Number, rate |
| YLD:YLL ratio | Disability-to-mortality burden ratio | Derived | Ratio |
| DALY rate | DALYs per 100,000 | GBD 2021 | Rate |

### 5.2 Derived Variables

| Variable | Formula | Purpose |
|----------|---------|---------|
| YLD fraction | YLD / DALY | Disability share of total burden |
| YLL fraction | YLL / DALY | Mortality share of total burden |
| Hidden disability index | z(YLD rate) – z(death rate) | State comparison of disability vs. mortality prominence |
| Rank mismatch | rank(death burden) – rank(DALY burden) | Surveillance–burden ranking comparison |
| Productive age burden | DALYs in 15–49 / total DALYs | Economic burden concentration |

### 5.3 Administrative Comparison Variables

| Variable | Source | Note |
|----------|--------|------|
| Road accidents count | MoRTH 2023 | Administrative count |
| Road injury deaths | MoRTH 2023 | Administrative count |
| Injured persons | MoRTH 2023 | Administrative count |
| Accidental deaths by cause | NCRB 2023 | Administrative count |
| Suicide deaths by method | NCRB 2023 | Administrative count |

---

## 6. Analytical Methods

### 6.1 Descriptive Analysis

- National-level summary of all injury metrics, 2000–2021
- State-level summary tables with 95% uncertainty intervals (GBD)
- Trend visualization for key metrics

### 6.2 Fatal–Non-Fatal Decomposition

For each state i and cause j:
- YLL_ij / DALY_ij = mortality fraction
- YLD_ij / DALY_ij = disability fraction
- YLD:YLL ratio = YLD_ij / YLL_ij
- Classification: high/low based on national median thresholds

### 6.3 Hidden Disability Burden Index (HDBI)

**Definition A:** HDBI_i = z-score(YLD rate_i) − z-score(death rate_i)
- Positive HDBI: state has relatively more disability burden than its death burden suggests
- Negative HDBI: state's disability burden is proportionally lower than its death burden

**Definition B:** HDBI_rank_i = rank(YLD rate_i) − rank(death rate_i)
- Equivalent interpretation using ranks (more robust to outliers)

Both definitions will be reported; sensitivity analyses will use alternate thresholds.

### 6.4 State Typology (2×2 Matrix)

Quadrant classification using national median YLL rate and YLD rate:
- Q1: High YLL / High YLD — overall high burden
- Q2: High YLL / Low YLD — mortality-dominant
- Q3: Low YLL / High YLD — disability-dominant (priority for rehabilitation)
- Q4: Low YLL / Low YLD — relatively lower burden

Sensitivity: repeat with 25th/75th percentile thresholds.

### 6.5 Productive-Age Burden

- Subset DALYs to ages 15–49 and 15–64
- Compute as fraction of all-age DALYs
- State-level and cause-specific

### 6.6 Inequality Metrics

For each year (2000, 2005, 2010, 2015, 2019, 2021):
- Top:bottom ratio (highest:lowest state DALY rate)
- Coefficient of variation (CV) of state DALY rates
- Interquartile range (IQR)
- Optional: Gini coefficient of state DALY distribution

Trend in inequality: compare CV 2000 vs. 2021

### 6.7 Surveillance–Burden Mismatch Analysis

**Method:**
1. Rank states by MoRTH road injury deaths (2023)
2. Rank states by GBD road injury DALYs (2021)
3. Compute rank difference and Spearman correlation
4. Identify states where rank differs by >5 positions (arbitrary but reported threshold)

**Secondary:** Compare NCRB cause ordering vs. GBD cause ordering for leading injury mechanisms

**Important caveat:** Administrative counts (MoRTH 2023) and GBD estimates (2021) differ in year and methodology. Comparisons are qualitative and rank-based, not numerical.

### 6.8 Optional Ecological Models

If data quality permits:
- Spearman correlation of state DALY rate with SDI proxy (literacy rate, per capita income, urbanization)
- Linear regression of DALY rate on covariates with state-level random effects
- Clearly labeled as exploratory/ecological; no causal language

### 6.9 Sensitivity Analyses

| SA# | Description |
|----|-------------|
| SA1 | Exclude UTs; repeat all analyses for states only |
| SA2 | Use crude vs. age-standardized rates |
| SA3 | Alternate HDBI definitions (Definition A vs. B; ±1 SD vs. median threshold) |
| SA4 | Road injury-only vs. all-injury analyses |
| SA5 | Alternate state typology thresholds (25th/75th vs. median) |
| SA6 | Exclusion of clearly data-sparse states with justification |
| SA7 | Sex-stratified analyses |
| SA8 | Period comparison: 2000–2010 vs. 2011–2021 |

---

## 7. Software

- **Python ≥ 3.11:** Data engineering, parsing, harmonization, analysis
- **R ≥ 4.3 (optional):** Inequality metrics, visualization cross-check
- **pandas, numpy, scipy, matplotlib, seaborn, geopandas:** Core libraries
- **camelot-py or tabula-py:** PDF table extraction
- **openpyxl, xlrd:** Excel handling
- **shapefile / India map:** State-level choropleth maps
- **All scripts version-controlled**

---

## 8. Quality Control

- Checksums for all raw files
- Automated duplicate and missingness checks
- State name standardization crosswalk with audit log
- Figure/text numeric cross-reference verification
- Uncertainty interval propagation from GBD

---

## 9. Ethics

This study uses exclusively publicly available, de-identified aggregate secondary data. No individual-level data is used. Institutional ethics approval is not required. A declaration of use of public secondary data will be included in the manuscript.

---

## 10. Limitations (Pre-specified)

1. **GBD modeled estimates:** All GBD values are modeled estimates with uncertainty intervals, not direct counts. They should not be compared directly to administrative counts.
2. **Ecological fallacy:** State-level analyses cannot be extrapolated to individual-level conclusions.
3. **Year mismatch:** GBD 2021 vs. MoRTH/NCRB 2023 — administrative comparisons are qualitative only.
4. **Administrative underreporting:** MoRTH and NCRB figures are subject to registration and reporting limitations.
5. **GBD state coverage:** Not all UTs may have independent GBD estimates.
6. **Cause grouping differences:** GBD and administrative cause taxonomies are not directly equivalent.
7. **Temporal lag:** GBD 2021 does not capture post-2021 changes.

---

*End of Protocol v1.0*
