# District Injury Atlas of India (2023)

First district-resolution (~710-district) atlas of fatal injury burden in India,
built by a Bayesian spatial model that **fuses** the discordant GBD-modelled and
NCRB-administrative state signals, **downscales** to districts with a benchmarked
ICAR + covariate model, and is **anchored/validated** on ~41 NCRB metropolitan-city
records. Also produces the first sub-state map of injury **surveillance completeness**.

## Data provenance

| Dataset | Source | Location |
|---|---|---|
| GBD 2023 state injury deaths + UIs | IHME GBD 2023 | `../data_processed/master_dataset.csv` |
| NCRB ADSI 2023 state accidental deaths + suicides | NCRB | `../data_interim/ncrb_*_2023.csv` |
| NCRB ADSI 2023 mega-city tables (1.2, 1A.2, 2.3) | NCRB ADSI 2023 PDF | `../data_raw/ncrb/ADSI_2023.pdf` → `data_local/ncrb_cities_2023.csv` |
| District boundaries (current, post-2014 State splits) | LGD/Survey of India/Bhuvan/DataMeet compilation | `data_local/districts_v2.geojson` |
| District population + urbanicity + covariates | Census of India 2011 | `data_local/census2011.csv` |
| District alcohol/tobacco prevalence | NFHS-5 district factsheet | `../data_raw/NFHS_5_India_Districts_Factsheet_Data(Sheet1).csv` |

## State-name harmonisation

GBD 2023 reports Jammu & Kashmir and Ladakh as one combined unit, and five small
union territories (Andaman & Nicobar Islands, Chandigarh, Dadra & Nagar Haveli and
Daman & Diu, Lakshadweep, Puducherry) as a single "Other Union Territories" unit.
Districts in those States are modelled at the level GBD actually reports (see
`STATE_HARM` in `src/build_districts.py`); for the five small, covariate-heterogeneous
union territories, which have no city anchor, the shared combined-unit rate and
completeness are reported directly rather than an unsupported district-level split.

## Anchoring note

NCRB tabulates mega-city (district) detail only for **total accidental deaths**,
**road-accident deaths**, and **suicides**. Therefore **all_injury, road, suicide**
are anchored and validated; **falls, drowning, burns** are covariate-projected only
(lower confidence — see manuscript limitations).

## Reproduce

```bash
python -m meta_district_injury_atlas_india.run_all
```

Steps: extract city anchors → build district frame + adjacency → fit 6 causes
(PyMC, numpyro/JAX NUTS backend; no C compiler required) → 5-fold city
cross-validation → structural sensitivity. Approximate runtime: ~20–40 min on CPU.

## Outputs

- `tables/district_estimates.csv` — per district × cause: rate (mean, 95% CrI),
  completeness (mean, 95% CrI), estimated deaths.
- `tables/blind_spots.csv` — districts ranked by burden × uncertainty × under-reporting.
- `tables/cv_metrics.csv`, `tables/sensitivity.csv` — validation.
- `figures/map_<cause>_{rate,uncertainty,completeness}.png` — choropleths.
