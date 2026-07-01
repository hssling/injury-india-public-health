# A Bayesian spatial data-fusion atlas of fatal injury across India's districts, with a sub-state map of surveillance completeness

*Target: Lancet Regional Health – Southeast Asia / Indian Journal of Medical Research*

## Abstract

**Background.** India's injury-burden evidence stops at the state level, and its two
principal data streams — the modelled Global Burden of Disease (GBD) estimates and the
administrative National Crime Records Bureau (NCRB) counts — disagree by up to
{{ratio_falls}}-fold for some causes. No district-resolution injury burden estimate, and
no sub-state measure of surveillance completeness, exists for the country.

**Methods.** We developed a hierarchical Bayesian model that (i) fuses GBD 2023 and NCRB
ADSI 2023 state signals through cause-specific completeness parameters, (ii) downscales the
fused burden to 735 districts using a benchmarked intrinsic conditional autoregressive
(ICAR) spatial field with Census-2011 and NFHS-5 covariates, and (iii) is anchored to and
validated against 53 NCRB metropolitan-city (district) records via five-fold spatial
cross-validation. Estimates are reported for all-injury, road, and suicide (anchored) and,
as covariate projections, for falls, drowning and burns.

**Findings.** {{n_districts}} districts were estimated. District all-injury mortality ranged
{{ai_range}} per 100,000. Surveillance completeness (NCRB/true) was lowest for
{{low_completeness_cause}} (median {{completeness_median}}). Cross-validated interval
coverage was {{coverage}} with log-RMSE {{log_rmse}}. We identify {{n_blindspots}}
high-burden, low-completeness "surveillance blind-spot" districts concentrated in
{{blindspot_states}}.

**Interpretation.** Injury priorities and surveillance gaps vary sharply *within* states.
A fusion-plus-downscaling approach yields actionable district targets that neither GBD nor
NCRB provides alone.

## 1. Introduction
- Injury as a leading cause of premature mortality in India; policy operates at district level
  (e.g. the government's high-risk-district road programme) yet evidence is state-level.
- The GBD vs NCRB discordance and what it implies about administrative under-capture.
- Gap: no district injury atlas; no sub-state completeness surface. Contribution statement.

## 2. Methods
### 2.1 Data
GBD 2023 state deaths + 95% UIs; NCRB ADSI 2023 state accidental deaths and suicides; NCRB
mega-city tables (Table 1.2 total accidental + population, Table 1A.2 road-accident deaths,
Table 2.3 suicides); geoBoundaries ADM2 (735 districts); Census 2011 population and
urbanicity; NFHS-5 district alcohol/tobacco.

### 2.2 Model
State fusion (T_s, completeness c); district completeness sub-model
logit(c_d)=γ+η·urban+w_d; benchmarked ICAR downscaling of the true rate λ_d; anchor Poisson
likelihood at the 53 city-districts. Priors, ICAR construction, benchmarking constraint,
and JAX/numpyro inference. (See `src/model.py`.)

### 2.3 Validation
Five-fold city cross-validation (coverage, log-RMSE, Spearman); structural sensitivity
(spatial vs non-spatial; state-constant vs varying completeness; completeness-prior width).

## 3. Results
- Table 1: state fusion — GBD vs NCRB vs fused, completeness by cause. {{table1}}
- District burden distribution and maps (Fig 1). {{results_burden}}
- Surveillance-completeness surface (Fig 2). {{results_completeness}}
- Blind-spot districts (Table 2). {{results_blindspots}}
- Validation and sensitivity (Table 3). {{results_validation}}

## 4. Discussion
Principal findings; policy implications (district targeting, where to strengthen the CRS/MCCD
and police reporting); comparison with state-level GBD/NCRB work; novelty.

### Limitations
- Identification of covariate effects leans on 53 urban anchor districts; the completeness
  slope η is extrapolated to rural districts (primary limitation).
- falls/drowning/burns are covariate-projected only (no district-level anchor in NCRB).
- Ecological covariate associations; not individual-level causal effects.
- 2011 population base for exposure; district boundary/name harmonisation across three frames.

## Data sharing
All inputs are public; code and derived tables in `meta_district_injury_atlas_india/`.
