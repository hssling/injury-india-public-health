# Design Spec — A Bayesian Spatial Data-Fusion Atlas of Injury Mortality Across India's Districts

Date: 2026-07-02
Status: Approved design, pending implementation plan
Workspace: `injury_india_public_health`

## 1. Problem and novelty

India's injury burden evidence stops at the **state level**. GBD publishes state injury
estimates; NCRB ADSI publishes state (and, for accidental deaths and suicides, 53
metropolitan-city) administrative counts. The two disagree sharply and systematically —
national GBD-to-NCRB death ratios in this workspace are 8.75x (falls), 5.45x (burns),
1.42x (road), 1.32x (drowning), 0.27x (poisoning). No published work estimates injury
mortality **below the state level** for India, and no work maps **where injury
surveillance is most incomplete** at sub-state resolution.

Novelty scan (2026-07-02): Bayesian small-area estimation (SAE) to Indian districts exists
for fertility and all-cause/child mortality (Dwivedi et al., 2026, NFHS-based) and for a few
disease-burden pilots, but **not for injury mortality**. GBD injury work in India is
state-level. The government "100 high-risk districts" road program uses raw NCRB counts, not
a modeled burden with uncertainty. This project is therefore the first district-resolution
injury burden atlas of India, and the first sub-state map of injury surveillance
completeness.

**Research question.** What is the district-level burden of fatal injury across India's ~707
districts once discordant GBD-modeled and NCRB-administrative signals are reconciled, and
where is injury surveillance most incomplete?

## 2. Methodological value-adds (per the novelty requirement)

1. **Bayesian spatial data fusion** — a single hierarchical model that reconciles two
   conflicting state-level sources (GBD, NCRB) via cause-specific completeness parameters
   while simultaneously downscaling to districts.
2. **Benchmarked small-area estimation** — district log-rates with a BYM/ICAR spatial field
   and NFHS-5 covariates, constrained so population-weighted district rates reproduce the
   fused state rate (internal-consistency benchmarking).
3. **Surveillance-completeness surface** — completeness modeled as district-varying via a
   parsimonious sub-model (cause intercept + urbanicity/covariate + limited spatial
   smoothing), identified at the 53 anchor districts (where both true-scale and
   administrative-scale deaths are observed) and extrapolated elsewhere. Yields a
   district-varying GBD-implied vs administrative ratio with credible intervals — a genuinely
   new artifact.
4. **Anchored identification + spatial cross-validation** — the 53 NCRB metropolitan-city
   records (city = district) provide a direct district-level likelihood that identifies the
   covariate effects and enables leave-one-city-out validation, converting an otherwise
   untestable structure-transfer assumption into a calibrated, validated estimate.

## 3. Data

All local except two clearly-scoped acquisition tasks.

| Data | Source | Status | Role |
|---|---|---|---|
| State injury deaths (GBD 2023) | `data_processed/master_dataset.csv` | local | fusion input |
| State injury deaths (NCRB ADSI 2023) | `data_interim/ncrb_accidental_deaths_2023.csv`, `ncrb_suicides_2023.csv` | local | fusion input |
| District covariates (NFHS-5) | `data_raw/NFHS_5_India_Districts_Factsheet_Data(Sheet1).csv` (707 districts; alcohol/tobacco m/f + socioeconomic columns) | local | downscaling covariates |
| State geometry | `data_raw/india_states.geojson` | local | maps, QC |
| **District shapefile + population + % urban** | Census of India / SoI district boundaries | **acquire** | spatial adjacency (ICAR graph), `pop_d`, urbanicity covariate |
| **NCRB ADSI 2023 Metropolitan-Cities tables** (53 cities: accidental deaths by cause + suicides) | NCRB ADSI 2023 report | **extract** | district anchor likelihood + hold-out validation |

Crosswalks required: NFHS-5 district names <-> district-shapefile IDs; NCRB city names <->
district IDs. Store as CSVs under `docs/` alongside existing `state_crosswalk.csv`.

## 4. Model

Fit per cause: all-injury total + road, falls, drowning, burns, suicide.

Notation: state `s`, district `d`, cause `k`. `pop_d` = district population.

**(a) Completeness sub-model.** Administrative completeness is district- and cause-varying:
`logit(c_{d,k}) = gamma_k + eta_k * urbanicity_d + w_{d,k}`, where `w` is a lightly-smoothed
spatial/iid term. `gamma_k` has an informative prior centered on the workspace's national
GBD/NCRB ratios. State-level effective completeness `c_{s,k}` = population-weighted mean of
`c_{d,k}` over the state. Identification: `c_{d,k}` is pinned at the 53 anchor districts
(both scales observed) and at state aggregates (GBD true vs NCRB administrative); elsewhere
it follows the covariate/spatial structure. The urban-only anchor set means `eta_k` is the
key extrapolation assumption — see Risk 2.

**(b) State source fusion.** Let `T_{s,k}` be true state deaths.
- NCRB: `y^{NCRB}_{s,k} ~ Poisson(T_{s,k} * c_{s,k})`.
- GBD: `y^{GBD}_{s,k} ~ LogNormal(log T_{s,k}, sigma^{GBD}_{s,k})` using GBD-reported UIs to set `sigma`.
- Yields posterior fused state rate `R_{s,k} = T_{s,k} / pop_s`.

**(c) District downscaling.** `lambda_{d,k}` is the **true** district rate:
`log lambda_{d,k} = alpha_k + X_d^T beta_k + u_{d,k} + v_{d,k}`
where `u` is a BYM/ICAR spatial term on the district adjacency graph, `v` is iid
heterogeneity, `X_d` are standardized NFHS-5 covariates.

**(d) Benchmarking constraint.** Within each state,
`sum_{d in s} pop_d * lambda_{d,k} / pop_s = R_{s,k}`
enforced via a soft (tight-prior) or hard reparameterized constraint so true district
estimates aggregate to the fused state true rate.

**(e) Anchor likelihood.** For the 53 city-districts `a` (administrative scale):
`y^{city}_{a,k} ~ Poisson(pop_a * lambda_{a,k} * c_{a,k})` — jointly identifies `beta_k`
(true-rate covariate effects) and `eta_k` (completeness structure) against real
district-level data.

**(f) Completeness surface.** The posterior `c_{d,k}` field, mapped with credible intervals.

Inference: PyMC or Stan (NumPyro acceptable). ICAR via sparse precision from the adjacency
graph. Report posterior means + 95% credible intervals throughout.

## 5. Validation

1. **Spatial leave-one-city-out CV** on the 53 anchors — predict held-out city rate,
   report coverage of 95% intervals, RMSE/MAE on the log scale.
2. **Posterior predictive checks** at state level (must recover observed GBD/NCRB after
   fusion) and city level.
3. **Benchmark reconciliation check** — confirm district aggregates reproduce fused state
   rates within tolerance.
4. **Sensitivity analyses** — completeness prior (tight vs diffuse), covariate set
   (full vs alcohol/tobacco only), spatial vs non-spatial (does ICAR improve CV?).

## 6. Outputs

- Per-cause district choropleths: burden rate, surveillance-completeness, uncertainty width.
- Ranked table of high-burden + high-uncertainty ("blind spot") districts.
- Model + CV results tables with credible intervals.
- Reproducible pipeline under `meta_district_injury_atlas_india/` mirroring existing
  project-folder conventions (`src/`, `outputs/`, `figures/`, `tables/`, run script).

## 7. Target journal

Primary: *Lancet Regional Health – Southeast Asia* or *Indian Journal of Medical Research*.
Fallback: *BMC Public Health* / *Indian Journal of Public Health*.

## 8. Risks and honest limitations

1. **Thin anchor set (n=53).** A national covariate model identified largely by 53 urban
   districts is the central limitation. Mitigations: strong spatial priors, benchmarking to
   fused state totals (which use all states), and explicit framing as the primary limitation.
   Report how much district variation is covariate- vs spatial-field- vs benchmark-driven.
2. **Urban/rural completeness differential.** The completeness slope `eta_k` is identified on
   53 urban anchors, yet extrapolated to rural districts — the load-bearing assumption of the
   completeness surface. Addressed by: an informative prior on `eta_k`; sensitivity to its
   prior width; a variant fixing completeness to state-constant (`eta_k=0`) to bound its
   influence; and explicit discussion that rural completeness is inferred, not observed.
3. **Boundary/name mismatches.** NFHS-5 vs shapefile vs NCRB district naming; resolved with
   explicit crosswalks and a reconciliation QC log; districts that cannot be matched are
   reported, not silently dropped.
4. **Ecological inference.** Covariate associations are ecological and not claimed as
   individual-level causal effects; framed as a downscaling structure, not an etiologic model.
5. **GBD 2021/2023 labeling QC** (flagged in the 2026-05-17 scan) must be resolved before use.

## 9. Scope boundaries (YAGNI)

- One year (2023). No time trends in v1.
- Fatal injury only (mortality). No YLD/DALY downscaling in v1 (possible follow-up).
- Five subcauses + total; no finer road-user or intent splits in v1.
- No individual-level or district-level etiologic causal claims.
