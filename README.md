# Burden of Injuries in India: State-Level Public Health Analysis

**Provisional title:** Burden of injuries in India from a public health perspective: state-level fatal–non-fatal decomposition, inequality, and surveillance–burden mismatch using GBD 2021 and official Indian secondary data

**Target journal:** Indian Journal of Medical Research (IJMR)  
**Backup journals:** Indian Journal of Community Medicine (IJCM); National Journal of Community Medicine (NJCM)  
**Study type:** Ecological longitudinal secondary-data analysis  
**Data period:** 2000–2021 (GBD); 2023 (administrative)  
**Status:** Analysis pipeline run completed; publication package rebuilt from available local data outputs

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Check project status
```bash
python run_all.py --check
```

### 3. Download required data (MANUAL — see instructions below)

### 4. Run full analysis pipeline
```bash
python run_all.py
```

Or run phase by phase:
```bash
python run_all.py --phase 1   # File validation
python run_all.py --phase 2   # Parse and harmonize
python run_all.py --phase 3   # Analysis
python run_all.py --phase 4   # Figures
python run_all.py --phase 5   # QC
```

---

## Data Download Instructions

### REQUIRED: GBD 2021 Data
1. Go to: https://ghdx.healthdata.org/gbd-results
2. Create a free IHME account
3. Select parameters:
   - Location: India + all subnational
   - Cause: All injuries (Level 1) + subcauses (L2/L3)
   - Measure: Deaths, DALYs, YLLs, YLDs, Incidence
   - Metric: Number + Rate
   - Year: 2000–2021
   - Sex: Both, Male, Female
   - Age: All ages + granular groups
4. Download CSV and save to: `data_raw/gbd/`

### REQUIRED: MoRTH Road Accidents 2023
1. Go to: https://road.transport.gov.in/publications/road-accidents-in-india
2. Download: Road Accidents in India 2023 PDF
3. Save to: `data_raw/morth/road_accidents_india_2023.pdf`

### REQUIRED: NCRB ADSI 2023
1. Go to: https://ncrb.gov.in/adsi.html
2. Download: Accidental Deaths & Suicides in India 2023 PDF
3. Save to: `data_raw/ncrb/adsi_2023.pdf`

### REQUIRED: India Shapefile (for maps)
1. Go to: https://gadm.org/download_country.html
2. Select India → Level 1 → Download Shapefile
3. Save to: `data_raw/shapefiles/`

---

## If PDF Extraction Fails (MoRTH/NCRB)

If automated table extraction from PDFs fails:
1. Open the generated template: `data_raw/morth/manual_extraction_morth.xlsx`
2. Manually enter state-wise data from the PDF
3. Save and run: `python src/ingest/03_parse_morth.py --from-template`

Same process for NCRB:
1. `data_raw/ncrb/manual_extraction_ncrb.xlsx`
2. `python src/ingest/04_parse_ncrb.py --from-template`

---

## Project Structure

```
injury_india_public_health/
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── run_all.py                      # Master pipeline orchestrator
├── data_raw/
│   ├── gbd/                        # GBD 2021 CSV files (download here)
│   ├── morth/                      # MoRTH PDF + manual extraction template
│   ├── ncrb/                       # NCRB PDF + manual extraction template
│   ├── shapefiles/                 # India state shapefiles
│   └── population/                 # (optional) Census population data
├── data_interim/                   # Parsed, pre-harmonized data
├── data_processed/
│   └── master_dataset.csv          # Final harmonized analysis dataset
├── docs/
│   ├── concept_note.md             # Study concept and rationale
│   ├── protocol.md                 # Full study protocol
│   ├── analysis_plan.md            # Step-by-step analytic plan
│   ├── research_questions.md       # Structured research questions
│   ├── variable_dictionary.csv     # All variable definitions
│   ├── source_register.csv         # All data sources with provenance
│   ├── state_crosswalk.csv         # State name harmonization crosswalk
│   └── limitations_and_risks.md    # Pre-specified limitations register
├── src/
│   ├── ingest/
│   │   ├── 01_download_plan.py     # Download instructions + file validation
│   │   ├── 02_parse_gbd.py         # GBD CSV parser
│   │   ├── 03_parse_morth.py       # MoRTH PDF extractor
│   │   └── 04_parse_ncrb.py        # NCRB PDF extractor
│   ├── clean/
│   │   ├── 05_harmonize_states.py  # State name standardization
│   │   └── 08_assemble_master.py   # Master dataset assembly + QC
│   ├── analysis/
│   │   ├── 10_state_burden.py      # State-level burden (Table 1)
│   │   ├── 11_decomposition.py     # Fatal/non-fatal decomposition
│   │   ├── 12_hdbi.py              # Hidden Disability Burden Index
│   │   ├── 17_inequality.py        # Inter-state inequality metrics
│   │   └── 18_mismatch.py          # Surveillance–burden mismatch
│   ├── viz/
│   │   └── 20_figures.py           # All 7 manuscript figures
│   └── qc/
│       └── 21_qc_full.py           # Full QC report
├── outputs/                        # Analysis outputs (CSVs)
├── tables/                         # Manuscript tables (Excel)
├── figures/                        # Manuscript figures (PNG/SVG/PDF)
├── manuscript/
│   ├── manuscript_main_IJMR.md     # Main manuscript (IJMR format)
│   ├── cover_letter_IJMR.md        # Cover letter
│   ├── title_page_IJMR.md          # Title page
│   ├── declarations.md             # Ethics, funding, COI
│   └── plain_language_summary.md   # Plain language summary
├── submission/
│   ├── IJMR_submission_ready/      # Final IJMR package
│   ├── IJCM_submission_ready/      # Final IJCM package
│   └── NJCM_submission_ready/      # Final NJCM package
├── references/
│   ├── references_master.bib       # BibTeX reference database
│   └── citation_audit.csv          # DOI/URL verification tracker
└── logs/                           # All pipeline logs
```

---

## Expected Outputs

After successful pipeline run:
- `data_processed/master_dataset.csv` — harmonized analysis dataset
- `outputs/state_burden_2021.csv` — state-level burden rankings
- `outputs/decomposition.csv` — YLL/YLD decomposition by state
- `outputs/hdbi.csv` — Hidden Disability Burden Index
- `outputs/inequality.csv` — Inter-state inequality metrics
- `outputs/mismatch.csv` — Surveillance–burden mismatch ranking
- `outputs/qc_report.html` — Full QC report
- `figures/fig1_daly_map.*` through `fig6_mismatch.*` — Rebuilt manuscript and supplementary figures
- `tables/Table1_state_burden.xlsx` through `tables/Table6_sensitivity.xlsx`
- `manuscript/manuscript_main_IJMR.md` — Manuscript with populated results

---

## Scientific Integrity Statement

- All primary data are from publicly available, verifiable sources
- No data are fabricated or invented
- All GBD values are modelled estimates with uncertainty intervals
- Administrative data (MoRTH, NCRB) are not directly compared numerically to GBD estimates
- All transformations are logged
- Code is fully reproducible from raw data inputs

---

## Repository

Public repository: https://github.com/hssling/injury-india-public-health

## Data Sharing

See `DATA_SHARING_STATEMENT.md` for the repository-level data and code availability statement.

## Contact

For questions about this analysis, contact: Siddalingaiah H S (`hssling@yahoo.com`).
