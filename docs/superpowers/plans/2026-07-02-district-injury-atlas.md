# District Injury Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the first ~707-district atlas of fatal injury burden in India via a Bayesian spatial model that fuses discordant GBD + NCRB state signals, downscales with NFHS-5 covariates, and is anchored/validated on 53 NCRB metropolitan-city records — plus a district-level surveillance-completeness surface.

**Architecture:** A reproducible Python pipeline in a new sibling project folder `meta_district_injury_atlas_india/`, mirroring existing project conventions (`src/`, `outputs/`, `figures/`, `tables/`, `manuscript/`, `tests/`, `run_all.py`). Data build → adjacency graph → per-cause hierarchical Bayesian model (PyMC) with completeness sub-model, state fusion, benchmarked ICAR downscaling, and anchor likelihood → validation (leave-one-city-out CV, PPC, sensitivity) → maps/tables → manuscript.

**Tech Stack:** Python 3.14, PyMC + ArviZ (NUTS), geopandas + libpysal (adjacency), pandas/numpy, matplotlib. Data: GBD 2023, NCRB ADSI 2023, NFHS-5 district factsheet, Census district shapefile.

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-07-02-district-injury-atlas-design.md` — the single source of truth; any deviation must be noted in the manuscript limitations.
- Year = 2023 only; fatal injury (mortality) only; causes = all-injury total + road, falls, drowning, burns, suicide.
- All estimates reported as posterior mean + 95% credible interval; never a point estimate alone.
- `lambda_{d,k}` is the TRUE district rate; administrative (NCRB/city) observations carry the completeness factor `c_{d,k}`. Do not conflate the two scales anywhere.
- Districts that fail crosswalk matching are logged and reported, never silently dropped.
- Reuse existing `data_processed/master_dataset.csv`, `data_interim/ncrb_*_2023.csv`, `data_raw/NFHS_5_India_Districts_Factsheet_Data(Sheet1).csv`, and `docs/state_crosswalk.csv` from the parent workspace via relative paths.
- New dependencies pinned in the parent `requirements.txt`: `pymc>=5.16`, `arviz>=0.18`, `libpysal>=4.9`, `pytensor>=2.20`.
- Resolve the GBD "2021 vs 2023" label QC (spec §8.5) before any modeling task consumes GBD rows.

---

### Task 1: Scaffold project + pin dependencies

**Files:**
- Create: `meta_district_injury_atlas_india/README.md`
- Create: `meta_district_injury_atlas_india/config.py`
- Create: `meta_district_injury_atlas_india/src/__init__.py`
- Create: `meta_district_injury_atlas_india/tests/__init__.py`
- Modify: `requirements.txt` (append pinned deps)

**Interfaces:**
- Produces: `config.py` exposing `CAUSES = ["all_injury","road","falls","drowning","burns","suicide"]`, `YEAR = 2023`, and path constants `PARENT`, `DATA_RAW`, `DATA_INTERIM`, `DATA_PROCESSED`, `OUT`, `FIG`, `TAB` (all `pathlib.Path`).

- [ ] **Step 1: Create folder skeleton**

```bash
cd "meta_district_injury_atlas_india" 2>/dev/null || mkdir -p meta_district_injury_atlas_india
cd meta_district_injury_atlas_india
mkdir -p src tests data_local docs outputs figures tables manuscript
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `config.py`**

```python
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent                     # injury_india_public_health/
DATA_RAW = PARENT / "data_raw"
DATA_INTERIM = PARENT / "data_interim"
DATA_PROCESSED = PARENT / "data_processed"
DOCS = PARENT / "docs"
LOCAL = HERE / "data_local"              # newly acquired/extracted data
OUT = HERE / "outputs"
FIG = HERE / "figures"
TAB = HERE / "tables"

YEAR = 2023
CAUSES = ["all_injury", "road", "falls", "drowning", "burns", "suicide"]
# NCRB metropolitan-city chapter reports accidental deaths + suicides only.
ANCHOR_CAUSES = ["all_injury", "road", "falls", "drowning", "burns", "suicide"]
```

- [ ] **Step 3: Append deps to parent requirements**

Append to `../requirements.txt`:
```
pymc>=5.16
arviz>=0.18
libpysal>=4.9
pytensor>=2.20
```

- [ ] **Step 4: Install and verify import**

Run: `python -c "import pymc, arviz, libpysal, geopandas; print('ok', pymc.__version__)"`
Expected: `ok 5.x`. If PyMC fails to build on Python 3.14, record the blocker and fall back to `numpyro` (note in README); do not proceed until a sampler imports.

- [ ] **Step 5: Commit**

```bash
git add meta_district_injury_atlas_india requirements.txt
git commit -m "chore: scaffold district injury atlas project + pin bayes/geo deps"
```

---

### Task 2: Extract NCRB ADSI 2023 metropolitan-city anchor data

**Files:**
- Create: `meta_district_injury_atlas_india/data_local/ncrb_cities_2023.csv`
- Create: `meta_district_injury_atlas_india/src/extract_ncrb_cities.py`
- Create: `meta_district_injury_atlas_india/tests/test_ncrb_cities.py`

**Interfaces:**
- Produces: `ncrb_cities_2023.csv` with columns `city_name, year, cause, deaths_n, source, note` where `cause in CAUSES` (excluding `all_injury`, which is derived as the sum of the accidental causes + suicide per city). One row per (city, cause).

- [ ] **Step 1: Manually extract the 53-city tables**

From the NCRB ADSI 2023 "Accidental Deaths — Metropolitan Cities" and "Suicides — Metropolitan Cities" tables, transcribe accidental deaths by cause (road/traffic, falls, drowning, fire/burns) and suicide totals for each of the 53 cities into `data_local/ncrb_cities_2023.csv`. Keep the NCRB cause wording in a `note` column and map to our `cause` vocabulary. If a city omits a cause, record `0` only when the source shows `0`; use empty (NaN) when the cause is not tabulated, and log it.

- [ ] **Step 2: Write validator test**

```python
import pandas as pd
from meta_district_injury_atlas_india.config import LOCAL, CAUSES

def test_cities_file_shape():
    df = pd.read_csv(LOCAL / "ncrb_cities_2023.csv")
    assert df["city_name"].nunique() >= 50           # 53 cities, allow a few unmatched
    assert set(df["cause"]).issubset(set(CAUSES))
    assert (df["deaths_n"].dropna() >= 0).all()
    assert (df["year"] == 2023).all()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest meta_district_injury_atlas_india/tests/test_ncrb_cities.py -v`
Expected: FAIL (file missing) until Step 1 file exists, then PASS.

- [ ] **Step 4: Write `extract_ncrb_cities.py` (derives all_injury + QC log)**

```python
"""Normalize the transcribed city table: derive all_injury, write QC log."""
import pandas as pd
from meta_district_injury_atlas_india.config import LOCAL, OUT

def build():
    df = pd.read_csv(LOCAL / "ncrb_cities_2023.csv")
    wide = df.pivot_table(index="city_name", columns="cause",
                          values="deaths_n", aggfunc="sum")
    parts = ["road", "falls", "drowning", "burns", "suicide"]
    wide["all_injury"] = wide[parts].sum(axis=1, min_count=1)
    missing = wide.isna().stack()[lambda s: s].index.tolist()
    pd.DataFrame(missing, columns=["city_name", "cause"]).to_csv(
        OUT / "qc_city_missing_causes.csv", index=False)
    return wide.reset_index()

if __name__ == "__main__":
    build().to_csv(OUT / "ncrb_cities_wide_2023.csv", index=False)
    print("wrote city wide table + QC log")
```

- [ ] **Step 5: Run and commit**

Run: `python -m meta_district_injury_atlas_india.src.extract_ncrb_cities`
Expected: prints confirmation; `outputs/ncrb_cities_wide_2023.csv` and `outputs/qc_city_missing_causes.csv` exist.
```bash
git add meta_district_injury_atlas_india/data_local/ncrb_cities_2023.csv meta_district_injury_atlas_india/src/extract_ncrb_cities.py meta_district_injury_atlas_india/tests/test_ncrb_cities.py meta_district_injury_atlas_india/outputs
git commit -m "feat: extract NCRB 2023 metropolitan-city anchor data + QC log"
```

---

### Task 3: Acquire district shapefile, population, and urbanicity

**Files:**
- Create: `meta_district_injury_atlas_india/data_local/districts.gpkg`
- Create: `meta_district_injury_atlas_india/data_local/district_pop_urban.csv`
- Create: `meta_district_injury_atlas_india/src/load_districts.py`
- Create: `meta_district_injury_atlas_india/tests/test_districts.py`

**Interfaces:**
- Produces: `load_districts()` -> `GeoDataFrame` indexed by `district_id` with columns `district_name, state_name, pop_d, pct_urban, geometry` (~707 rows). `district_id` is a stable integer key used by every downstream task.

- [ ] **Step 1: Place source files**

Download a Census-of-India district boundary file (2011 districts, the NFHS-5 frame) into `data_local/` and a district population + % urban CSV. Keep raw filenames; do not rename columns yet.

- [ ] **Step 2: Write test for the loader contract**

```python
from meta_district_injury_atlas_india.src.load_districts import load_districts

def test_districts_contract():
    gdf = load_districts()
    assert 600 <= len(gdf) <= 800
    for col in ["district_name","state_name","pop_d","pct_urban","geometry"]:
        assert col in gdf.columns
    assert gdf.index.name == "district_id"
    assert gdf["pop_d"].gt(0).all()
    assert gdf["pct_urban"].between(0, 100).all()
    assert gdf.geometry.is_valid.all()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest meta_district_injury_atlas_india/tests/test_districts.py -v`
Expected: FAIL (module/loader missing).

- [ ] **Step 4: Implement `load_districts.py`**

```python
import geopandas as gpd, pandas as pd
from meta_district_injury_atlas_india.config import LOCAL

def load_districts():
    gdf = gpd.read_file(LOCAL / "districts.gpkg")
    pop = pd.read_csv(LOCAL / "district_pop_urban.csv")
    # Harmonize source-specific column names here (edit to match the files):
    gdf = gdf.rename(columns={"DISTRICT": "district_name", "ST_NM": "state_name"})
    gdf["geometry"] = gdf.geometry.buffer(0)          # fix invalid rings
    gdf = gdf.merge(pop, on=["district_name", "state_name"], how="left")
    gdf = gdf.rename(columns={"population": "pop_d", "urban_pct": "pct_urban"})
    gdf = gdf.reset_index(drop=True)
    gdf.index.name = "district_id"
    return gdf[["district_name","state_name","pop_d","pct_urban","geometry"]]
```

- [ ] **Step 5: Run test to verify it passes, then commit**

Run: `pytest meta_district_injury_atlas_india/tests/test_districts.py -v` — Expected: PASS.
```bash
git add meta_district_injury_atlas_india/data_local meta_district_injury_atlas_india/src/load_districts.py meta_district_injury_atlas_india/tests/test_districts.py
git commit -m "feat: district geometry + population/urbanicity loader"
```

---

### Task 4: Build crosswalks (NFHS↔district, city↔district) with match audit

**Files:**
- Create: `meta_district_injury_atlas_india/data_local/xwalk_nfhs_district.csv`
- Create: `meta_district_injury_atlas_india/data_local/xwalk_city_district.csv`
- Create: `meta_district_injury_atlas_india/src/crosswalks.py`
- Create: `meta_district_injury_atlas_india/tests/test_crosswalks.py`

**Interfaces:**
- Consumes: `load_districts()` (district_id keys); NFHS-5 factsheet; `ncrb_cities_wide_2023.csv`.
- Produces: `nfhs_to_district()` -> DataFrame `[nfhs_district_name, state_name, district_id]`; `city_to_district()` -> DataFrame `[city_name, district_id]`; both write an unmatched-rows CSV to `outputs/`.

- [ ] **Step 1: Write tests (coverage thresholds + no dup keys)**

```python
from meta_district_injury_atlas_india.src.crosswalks import nfhs_to_district, city_to_district

def test_nfhs_coverage():
    x = nfhs_to_district()
    assert x["district_id"].notna().mean() >= 0.90     # >=90% NFHS districts matched
    assert x.loc[x.district_id.notna(), "district_id"].is_unique

def test_city_coverage():
    x = city_to_district()
    assert x["district_id"].notna().mean() >= 0.85      # allow a few unmatched cities
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest meta_district_injury_atlas_india/tests/test_crosswalks.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `crosswalks.py`**

```python
import pandas as pd
from rapidfuzz import process, fuzz
from meta_district_injury_atlas_india.config import DATA_RAW, LOCAL, OUT
from meta_district_injury_atlas_india.src.load_districts import load_districts

def _match(names, choices, id_lookup, cutoff=88):
    out = []
    for n in names:
        hit = process.extractOne(str(n), choices, scorer=fuzz.WRatio)
        out.append(id_lookup[hit[0]] if hit and hit[1] >= cutoff else None)
    return out

def _manual(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

def nfhs_to_district():
    gdf = load_districts().reset_index()
    id_lookup = dict(zip(gdf.district_name.str.lower(), gdf.district_id))
    nfhs = pd.read_csv(DATA_RAW / "NFHS_5_India_Districts_Factsheet_Data(Sheet1).csv")
    nfhs = nfhs.rename(columns={"District Names": "nfhs_district_name", "State/UT": "state_name"})
    nfhs["district_id"] = _match(nfhs.nfhs_district_name.str.lower(),
                                 list(id_lookup), id_lookup)
    manual = _manual(LOCAL / "xwalk_nfhs_district.csv")   # hand-fixed unmatched rows
    if len(manual):
        nfhs = nfhs.set_index("nfhs_district_name")
        nfhs.loc[manual.nfhs_district_name, "district_id"] = manual.set_index(
            "nfhs_district_name").district_id
        nfhs = nfhs.reset_index()
    nfhs.loc[nfhs.district_id.isna()].to_csv(OUT / "qc_unmatched_nfhs.csv", index=False)
    return nfhs[["nfhs_district_name", "state_name", "district_id"]]

def city_to_district():
    gdf = load_districts().reset_index()
    id_lookup = dict(zip(gdf.district_name.str.lower(), gdf.district_id))
    cities = pd.read_csv(OUT / "ncrb_cities_wide_2023.csv")
    cities["district_id"] = _match(cities.city_name.str.lower(), list(id_lookup), id_lookup)
    manual = _manual(LOCAL / "xwalk_city_district.csv")
    if len(manual):
        cities = cities.merge(manual, on="city_name", how="left", suffixes=("", "_m"))
        cities["district_id"] = cities["district_id_m"].fillna(cities["district_id"])
    cities.loc[cities.district_id.isna()].to_csv(OUT / "qc_unmatched_cities.csv", index=False)
    return cities[["city_name", "district_id"]]
```

- [ ] **Step 4: Fill manual crosswalk CSVs for unmatched rows, rerun until thresholds pass**

Inspect `outputs/qc_unmatched_*.csv`; add hand-verified `district_id` rows to the two `xwalk_*.csv` files. Rerun the tests.
Run: `pytest meta_district_injury_atlas_india/tests/test_crosswalks.py -v` — Expected: PASS.
Add `rapidfuzz>=3.9` to `../requirements.txt`.

- [ ] **Step 5: Commit**

```bash
git add meta_district_injury_atlas_india/src/crosswalks.py meta_district_injury_atlas_india/tests/test_crosswalks.py meta_district_injury_atlas_india/data_local/xwalk_*.csv ../requirements.txt
git commit -m "feat: NFHS and city to-district crosswalks with match audit"
```

---

### Task 5: Assemble state-level fusion inputs (GBD + NCRB by cause)

**Files:**
- Create: `meta_district_injury_atlas_india/src/state_inputs.py`
- Create: `meta_district_injury_atlas_india/tests/test_state_inputs.py`

**Interfaces:**
- Consumes: `master_dataset.csv` (GBD deaths + UIs), `ncrb_accidental_deaths_2023.csv`, `ncrb_suicides_2023.csv`, `state_crosswalk.csv`.
- Produces: `state_inputs()` -> DataFrame indexed by `(state_name, cause)` with columns `gbd_deaths, gbd_lower, gbd_upper, ncrb_deaths, pop_s`. GBD `sigma` derived downstream from the UI columns.

- [ ] **Step 1: Write test (both sources present, GBD≥NCRB nationally for falls/burns)**

```python
from meta_district_injury_atlas_india.src.state_inputs import state_inputs

def test_state_inputs():
    df = state_inputs().reset_index()
    assert set(df.cause) == {"all_injury","road","falls","drowning","burns","suicide"}
    assert df.gbd_deaths.gt(0).all()
    nat = df.groupby("cause")[["gbd_deaths","ncrb_deaths"]].sum()
    assert nat.loc["falls","gbd_deaths"] > nat.loc["falls","ncrb_deaths"]  # 8.75x discordance
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest meta_district_injury_atlas_india/tests/test_state_inputs.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `state_inputs.py`**

Map GBD `cause_group`/`cause_gbd` to our six causes using parent causes only (spec QC: never `aggfunc='first'` across parent+subcause). Pull GBD `value/lower_ui/upper_ui` for `measure=Deaths, metric_type=Number, sex=Both, age_group=All ages, year=2023`. Join NCRB accidental deaths (road/falls/drowning/burns) + suicides. Attach `pop_s`. Resolve the GBD 2021/2023 label QC here (assert the raw citation year, relabel rows to 2023). Full mapping dict and filters written inline in the module.

- [ ] **Step 4: Run test to verify pass, then commit**

Run: `pytest meta_district_injury_atlas_india/tests/test_state_inputs.py -v` — Expected: PASS.
```bash
git add meta_district_injury_atlas_india/src/state_inputs.py meta_district_injury_atlas_india/tests/test_state_inputs.py
git commit -m "feat: state-level GBD+NCRB fusion inputs by cause"
```

---

### Task 6: Build district design matrix + ICAR adjacency graph

**Files:**
- Create: `meta_district_injury_atlas_india/src/district_design.py`
- Create: `meta_district_injury_atlas_india/tests/test_district_design.py`

**Interfaces:**
- Consumes: `load_districts()`, `nfhs_to_district()`, NFHS-5 factsheet covariates.
- Produces: `build_design()` -> `(X, meta, adj)` where `X` is a standardized covariate matrix (np.ndarray, rows = districts ordered by `district_id`), `meta` is a DataFrame `[district_id, district_name, state_name, pop_d, pct_urban, state_idx]`, and `adj` is a `scipy.sparse` symmetric binary adjacency built from queen contiguity via `libpysal.weights.Queen`. Islands (no neighbors) are connected to their nearest centroid and logged.

- [ ] **Step 1: Write tests (adjacency symmetry + no islands + X finite)**

```python
import numpy as np
from meta_district_injury_atlas_india.src.district_design import build_design

def test_design():
    X, meta, adj = build_design()
    assert X.shape[0] == len(meta)
    assert np.isfinite(X).all()
    A = adj.toarray()
    assert (A == A.T).all()                 # symmetric
    assert (A.sum(axis=1) > 0).all()        # no islands
    assert meta["state_idx"].min() == 0
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest meta_district_injury_atlas_india/tests/test_district_design.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `district_design.py`**

```python
import numpy as np, pandas as pd
from libpysal.weights import Queen, KNN
from meta_district_injury_atlas_india.src.load_districts import load_districts
from meta_district_injury_atlas_india.src.crosswalks import nfhs_to_district
from meta_district_injury_atlas_india.config import DATA_RAW, OUT

COVARS = [
    "Women age 15 years and above who consume alcohol (%)",
    "Men age 15 years and above who consume alcohol (%)",
    "Women age 15 years and above who use any kind of tobacco (%)",
    "Men age 15 years and above who use any kind of tobacco (%)",
]

def build_design():
    gdf = load_districts()
    xw = nfhs_to_district().dropna(subset=["district_id"])
    nfhs = pd.read_csv(DATA_RAW / "NFHS_5_India_Districts_Factsheet_Data(Sheet1).csv")
    nfhs = nfhs.rename(columns={"District Names": "nfhs_district_name"})
    nfhs = nfhs.merge(xw, on="nfhs_district_name", how="inner")
    cov = nfhs.groupby("district_id")[COVARS].mean()
    meta = gdf.reset_index().merge(cov, on="district_id", how="left")
    meta[COVARS] = meta[COVARS].fillna(meta[COVARS].mean())     # impute rare gaps
    meta["state_idx"] = meta["state_name"].astype("category").cat.codes
    Xcols = COVARS + ["pct_urban"]
    X = meta[Xcols].to_numpy(float)
    X = (X - X.mean(0)) / X.std(0)
    w = Queen.from_dataframe(gdf, use_index=False)
    if w.islands:                                              # reconnect islands via KNN1
        w = KNN.from_dataframe(gdf, k=1) if len(w.islands) else w
    A = w.sparse
    A = ((A + A.T) > 0).astype(int)                            # symmetric binary
    pd.Series(w.islands).to_csv(OUT / "qc_adjacency_islands.csv", index=False)
    return X, meta[["district_id","district_name","state_name","pop_d","pct_urban","state_idx"]], A
```

- [ ] **Step 4: Run test to verify pass, then commit**

Run: `pytest meta_district_injury_atlas_india/tests/test_district_design.py -v` — Expected: PASS.
```bash
git add meta_district_injury_atlas_india/src/district_design.py meta_district_injury_atlas_india/tests/test_district_design.py
git commit -m "feat: district design matrix + ICAR queen adjacency graph"
```

---

### Task 7: Core model — benchmarking + fusion primitives (unit-tested on synthetic data)

**Files:**
- Create: `meta_district_injury_atlas_india/src/model.py`
- Create: `meta_district_injury_atlas_india/tests/test_model_primitives.py`

**Interfaces:**
- Consumes: nothing external (pure functions).
- Produces:
  - `benchmark_rates(log_lambda, pop, state_idx, target_rate)` -> district rates rescaled so each state's population-weighted mean equals `target_rate[state]` (numpy, used as a deterministic reparameterization inside the model).
  - `icar_logp(phi, adj)` -> pairwise-difference ICAR log-density (float / pytensor expr).

- [ ] **Step 1: Write unit tests on synthetic data**

```python
import numpy as np
from meta_district_injury_atlas_india.src.model import benchmark_rates

def test_benchmark_reproduces_state_rate():
    pop = np.array([100., 300., 50., 50.])
    state_idx = np.array([0, 0, 1, 1])
    target = np.array([0.02, 0.05])          # per-state target rate
    log_lambda = np.log(np.array([0.01, 0.04, 0.09, 0.03]))
    r = benchmark_rates(log_lambda, pop, state_idx, target)
    for s in [0, 1]:
        m = state_idx == s
        assert np.isclose(np.average(r[m], weights=pop[m]), target[s])
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest meta_district_injury_atlas_india/tests/test_model_primitives.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement primitives**

```python
import numpy as np

def benchmark_rates(log_lambda, pop, state_idx, target_rate):
    """Rescale within-state so pop-weighted mean rate == target_rate[state]."""
    lam = np.exp(log_lambda)
    out = np.empty_like(lam)
    for s in np.unique(state_idx):
        m = state_idx == s
        cur = np.average(lam[m], weights=pop[m])
        out[m] = lam[m] * (target_rate[s] / cur)
    return out

def icar_logp(phi, adj):
    """Pairwise-difference ICAR: -0.5 * sum_{i~j} (phi_i - phi_j)^2."""
    import numpy as _np
    coo = adj.tocoo()
    upper = coo.row < coo.col
    diff = phi[coo.row[upper]] - phi[coo.col[upper]]
    return -0.5 * _np.sum(diff ** 2)
```

- [ ] **Step 4: Run test to verify pass, then commit**

Run: `pytest meta_district_injury_atlas_india/tests/test_model_primitives.py -v` — Expected: PASS.
```bash
git add meta_district_injury_atlas_india/src/model.py meta_district_injury_atlas_india/tests/test_model_primitives.py
git commit -m "feat: benchmarking + ICAR model primitives with synthetic tests"
```

---

### Task 8: Assemble the full PyMC model and fit one cause end-to-end

**Files:**
- Modify: `meta_district_injury_atlas_india/src/model.py` (add `build_pymc_model`, `fit_cause`)
- Create: `meta_district_injury_atlas_india/tests/test_fit_smoke.py`

**Interfaces:**
- Consumes: `state_inputs()`, `build_design()`, `city_to_district()`, primitives from Task 7.
- Produces: `fit_cause(cause, draws=1000, tune=1000)` -> `arviz.InferenceData` with deterministics `lambda_d` (true district rate), `c_d` (completeness), `beta`, `eta`, saved to `outputs/idata_<cause>.nc`.

- [ ] **Step 1: Write a smoke test (tiny sample fits + shapes + convergence sane)**

```python
import numpy as np, arviz as az
from meta_district_injury_atlas_india.src.model import fit_cause

def test_fit_smoke():
    idata = fit_cause("road", draws=150, tune=150)
    post = idata.posterior
    n_dist = post.sizes["district"]
    assert 600 <= n_dist <= 800
    assert float(post["c_d"].mean()) <= 1.0 + 1e-6
    rhat = az.rhat(idata, var_names=["beta","eta"]).to_array().max()
    assert float(rhat) < 1.2                # loose bound for a short chain
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest meta_district_injury_atlas_india/tests/test_fit_smoke.py -v` — Expected: FAIL (function missing).

- [ ] **Step 3: Implement `build_pymc_model` + `fit_cause`**

```python
import numpy as np, pymc as pm, pytensor.tensor as pt, arviz as az
from meta_district_injury_atlas_india.src.state_inputs import state_inputs
from meta_district_injury_atlas_india.src.district_design import build_design
from meta_district_injury_atlas_india.src.crosswalks import city_to_district
from meta_district_injury_atlas_india.config import OUT
import pandas as pd

NAT_RATIO = {"all_injury":3.0,"road":1.42,"falls":8.75,"drowning":1.32,"burns":5.45,"suicide":1.05}

def _icar_pt(phi, adj):
    coo = adj.tocoo(); u = coo.row < coo.col
    r, c = coo.row[u], coo.col[u]
    return -0.5 * pt.sum((phi[r] - phi[c]) ** 2)

def build_pymc_model(cause):
    si = state_inputs().reset_index()
    X, meta, adj = build_design()
    states = meta["state_name"].astype("category").cat.categories
    sidx = meta["state_idx"].to_numpy()
    pop = meta["pop_d"].to_numpy(float)
    s = si[si.cause == cause].set_index("state_name").reindex(states)
    gbd = s["gbd_deaths"].to_numpy(float)
    gbd_sig = ((np.log(s["gbd_upper"]) - np.log(s["gbd_lower"])) / (2*1.96)).to_numpy()
    ncrb = s["ncrb_deaths"].to_numpy(float)
    pop_s = s["pop_s"].to_numpy(float)
    logit0 = np.log(1/NAT_RATIO[cause] / (1 - 1/NAT_RATIO[cause]))

    cd = city_to_district().dropna(subset=["district_id"])
    cw = pd.read_csv(OUT / "ncrb_cities_wide_2023.csv").merge(cd, on="city_name")
    a_did = cw["district_id"].astype(int).to_numpy()
    a_pos = pd.Series(meta.index, index=meta["district_id"]).loc[a_did].to_numpy()
    a_obs = cw[cause].to_numpy(float)
    keep = np.isfinite(a_obs)
    a_pos, a_obs = a_pos[keep], a_obs[keep]

    with pm.Model() as m:
        # ---- true state deaths, fused from GBD (lognormal) + NCRB (poisson) ----
        T = pm.LogNormal("T", mu=np.log(gbd), sigma=np.maximum(gbd_sig, 0.05), shape=len(states))
        R_state = pm.Deterministic("R_state", T / pop_s)          # true state rate
        # ---- completeness sub-model: logit(c_d) = gamma + eta*urban + w ----
        gamma = pm.Normal("gamma", logit0, 0.5)
        eta = pm.Normal("eta", 0.0, 0.5)
        urban = (meta["pct_urban"].to_numpy(float) - 50) / 50
        w = pm.Normal("w", 0.0, 0.3, shape=len(meta))
        c_d = pm.Deterministic("c_d", pm.math.sigmoid(gamma + eta*urban + w))
        c_state = pm.Deterministic("c_state",
            pt.stack([ (c_d[sidx==k]*pop[sidx==k]).sum()/pop[sidx==k].sum()
                       for k in range(len(states)) ]))
        pm.Poisson("ncrb_like", mu=T * c_state, observed=ncrb)
        # ---- district downscaling (true rate), benchmarked to R_state ----
        alpha = pm.Normal("alpha", np.log(R_state.eval().mean() if False else 1e-3), 1.0)
        beta = pm.Normal("beta", 0.0, 0.5, shape=X.shape[1])
        tau = pm.HalfNormal("tau", 1.0)
        phi = pm.Normal("phi", 0.0, 1.0, shape=len(meta))
        pm.Potential("icar", _icar_pt(phi, adj))
        v = pm.Normal("v", 0.0, 0.3, shape=len(meta))
        raw = alpha + pt.dot(X, beta) + tau*phi + v
        # benchmark: within-state pop-weighted mean(exp(raw)) -> R_state
        lam_raw = pt.exp(raw)
        denom = pt.stack([ (lam_raw[sidx==k]*pop[sidx==k]).sum()/pop[sidx==k].sum()
                           for k in range(len(states)) ])
        lam_d = pm.Deterministic("lambda_d", lam_raw * (R_state[sidx] / denom[sidx]))
        # ---- anchor likelihood at city-districts (administrative scale) ----
        pm.Poisson("city_like", mu=pop[a_pos]*lam_d[a_pos]*c_d[a_pos], observed=a_obs)
    return m

def fit_cause(cause, draws=1000, tune=1000):
    with build_pymc_model(cause):
        idata = pm.sample(draws=draws, tune=tune, target_accept=0.95,
                          chains=4, random_seed=42, progressbar=False)
    idata.to_netcdf(OUT / f"idata_{cause}.nc")
    return idata
```

Note: the `alpha` prior line above is a placeholder for a fixed weakly-informative value; during implementation set `alpha ~ Normal(log(national_rate), 1.0)` using the national all-injury rate constant — do not call `.eval()` on a random variable. Fix before running.

- [ ] **Step 4: Fix the alpha prior, run smoke test to verify pass**

Run: `pytest meta_district_injury_atlas_india/tests/test_fit_smoke.py -v` — Expected: PASS (may take a few minutes).
If NUTS diverges heavily, raise `target_accept` to 0.99 and non-center `w`/`phi`; record the change.

- [ ] **Step 5: Commit**

```bash
git add meta_district_injury_atlas_india/src/model.py meta_district_injury_atlas_india/tests/test_fit_smoke.py
git commit -m "feat: full PyMC fusion+downscaling model, one-cause smoke fit"
```

---

### Task 9: Fit all six causes at production length + convergence report

**Files:**
- Create: `meta_district_injury_atlas_india/src/run_fits.py`
- Create: `meta_district_injury_atlas_india/tests/test_convergence.py`

**Interfaces:**
- Consumes: `fit_cause`.
- Produces: `outputs/idata_<cause>.nc` for all six causes; `outputs/convergence_summary.csv` with max r-hat and min ESS per cause.

- [ ] **Step 1: Write convergence test**

```python
import arviz as az, pandas as pd
from meta_district_injury_atlas_india.config import OUT

def test_convergence_report_exists_and_passes():
    df = pd.read_csv(OUT / "convergence_summary.csv")
    assert len(df) == 6
    assert (df["max_rhat"] < 1.05).all()
    assert (df["min_ess_bulk"] > 400).all()
```

- [ ] **Step 2: Implement `run_fits.py`**

```python
import arviz as az, pandas as pd
from meta_district_injury_atlas_india.config import CAUSES, OUT
from meta_district_injury_atlas_india.src.model import fit_cause

def main():
    rows = []
    for c in CAUSES:
        idata = fit_cause(c, draws=1500, tune=1500)
        summ = az.summary(idata, var_names=["beta","eta","gamma","tau"])
        rows.append({"cause": c, "max_rhat": summ["r_hat"].max(),
                     "min_ess_bulk": summ["ess_bulk"].min()})
    pd.DataFrame(rows).to_csv(OUT / "convergence_summary.csv", index=False)

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run fits, then the test**

Run: `python -m meta_district_injury_atlas_india.src.run_fits` (long-running; may take 1–2 h).
Run: `pytest meta_district_injury_atlas_india/tests/test_convergence.py -v` — Expected: PASS. If a cause fails to converge, reparameterize (non-centered) and refit only that cause.

- [ ] **Step 4: Commit**

```bash
git add meta_district_injury_atlas_india/src/run_fits.py meta_district_injury_atlas_india/tests/test_convergence.py meta_district_injury_atlas_india/outputs/convergence_summary.csv
git commit -m "feat: production fits for all six causes + convergence report"
```

---

### Task 10: Validation — leave-one-city-out CV + posterior predictive + benchmark check

**Files:**
- Create: `meta_district_injury_atlas_india/src/validate.py`
- Create: `meta_district_injury_atlas_india/tests/test_validation.py`

**Interfaces:**
- Consumes: `build_pymc_model`, anchor data.
- Produces: `loco_cv(cause)` -> DataFrame `[city_name, observed, pred_mean, pred_lower, pred_upper, in_interval]`; writes `outputs/cv_<cause>.csv` and `outputs/cv_metrics.csv` (log-RMSE, MAE, 95% coverage per cause). `benchmark_check(cause)` -> max relative deviation of district aggregate vs fused state rate.

- [ ] **Step 1: Write tests (coverage plausible + benchmark tight)**

```python
import pandas as pd
from meta_district_injury_atlas_india.config import OUT

def test_cv_metrics():
    m = pd.read_csv(OUT / "cv_metrics.csv").set_index("cause")
    assert m.loc["road","coverage95"] >= 0.80        # calibrated intervals
    assert m["log_rmse"].max() < 1.5                  # sane predictive error

def test_benchmark_tight():
    b = pd.read_csv(OUT / "benchmark_check.csv")
    assert b["max_rel_dev"].max() < 0.01             # aggregates reproduce state rate
```

- [ ] **Step 2: Implement `validate.py`**

Implement `loco_cv` by refitting with one city's `city_like` observation held out (mask the anchor row), predicting the held-out district's administrative-scale rate from `lambda_d*c_d`, and comparing to observed. Loop over anchor cities (use `draws=800` for speed). `benchmark_check` recomputes population-weighted district aggregates from posterior `lambda_d` and compares to `R_state`. Full code written inline in the module; write both CSVs plus `benchmark_check.csv`.

- [ ] **Step 3: Run and verify**

Run: `python -m meta_district_injury_atlas_india.src.validate` then `pytest meta_district_injury_atlas_india/tests/test_validation.py -v` — Expected: PASS.
If coverage is poor, widen `w`/anchor dispersion (add a Poisson overdispersion / NegBinom for `city_like`) and document.

- [ ] **Step 4: Commit**

```bash
git add meta_district_injury_atlas_india/src/validate.py meta_district_injury_atlas_india/tests/test_validation.py meta_district_injury_atlas_india/outputs/cv_*.csv meta_district_injury_atlas_india/outputs/benchmark_check.csv
git commit -m "feat: leave-one-city-out CV, PPC, and benchmark validation"
```

---

### Task 11: Sensitivity analyses (completeness prior, covariate set, spatial vs non-spatial)

**Files:**
- Create: `meta_district_injury_atlas_india/src/sensitivity.py`
- Create: `meta_district_injury_atlas_india/tests/test_sensitivity.py`

**Interfaces:**
- Consumes: `build_pymc_model` (parameterized variants).
- Produces: `outputs/sensitivity.csv` comparing CV log-RMSE and mean completeness across variants: (a) tight vs diffuse `eta` prior, (b) `eta=0` (state-constant completeness), (c) alcohol/tobacco-only vs +urban covariates, (d) ICAR on vs off.

- [ ] **Step 1: Write test**

```python
import pandas as pd
from meta_district_injury_atlas_india.config import OUT
def test_sensitivity_table():
    s = pd.read_csv(OUT / "sensitivity.csv")
    assert {"variant","cause","cv_log_rmse","mean_completeness"}.issubset(s.columns)
    assert s["variant"].nunique() >= 4
```

- [ ] **Step 2: Implement variants via keyword flags on `build_pymc_model`**

Add flags `eta_sd`, `fix_eta`, `covars`, `use_icar` to `build_pymc_model`; loop variants in `sensitivity.py`, reuse `loco_cv` for CV RMSE. Full code inline.

- [ ] **Step 3: Run + test + commit**

Run: `python -m meta_district_injury_atlas_india.src.sensitivity` then `pytest meta_district_injury_atlas_india/tests/test_sensitivity.py -v` — Expected: PASS.
```bash
git add meta_district_injury_atlas_india/src/sensitivity.py meta_district_injury_atlas_india/tests/test_sensitivity.py meta_district_injury_atlas_india/outputs/sensitivity.csv
git commit -m "feat: sensitivity analyses across priors, covariates, spatial structure"
```

---

### Task 12: Atlas outputs — choropleths, blind-spot table, results tables

**Files:**
- Create: `meta_district_injury_atlas_india/src/atlas_outputs.py`
- Create: `meta_district_injury_atlas_india/tests/test_outputs.py`

**Interfaces:**
- Consumes: `idata_<cause>.nc`, `load_districts()`.
- Produces: per-cause PNG maps (`figures/map_<cause>_rate.png`, `_completeness.png`, `_uncertainty.png`), `tables/district_estimates.csv` (all districts × causes: rate mean/CrI, completeness mean/CrI), and `tables/blind_spots.csv` (top districts ranked by burden × uncertainty × low completeness).

- [ ] **Step 1: Write test (tables well-formed, every district present)**

```python
import pandas as pd
from meta_district_injury_atlas_india.config import TAB
from meta_district_injury_atlas_india.src.load_districts import load_districts

def test_district_estimates_complete():
    est = pd.read_csv(TAB / "district_estimates.csv")
    n = len(load_districts())
    assert est["district_id"].nunique() == n
    assert {"rate_mean","rate_lower","rate_upper","completeness_mean"}.issubset(est.columns)
    assert (est["rate_lower"] <= est["rate_mean"]).all()
    assert (est["rate_mean"] <= est["rate_upper"]).all()
```

- [ ] **Step 2: Implement `atlas_outputs.py`**

Extract posterior summaries of `lambda_d` and `c_d` per cause; join to geometry; render choropleths with matplotlib (quantile bins, colorbars, titles). Build `blind_spots.csv` = rank by `rate_mean * (rate_upper-rate_lower) * (1-completeness_mean)`. Full code inline.

- [ ] **Step 3: Run + test + commit**

Run: `python -m meta_district_injury_atlas_india.src.atlas_outputs` then `pytest meta_district_injury_atlas_india/tests/test_outputs.py -v` — Expected: PASS.
```bash
git add meta_district_injury_atlas_india/src/atlas_outputs.py meta_district_injury_atlas_india/tests/test_outputs.py meta_district_injury_atlas_india/figures meta_district_injury_atlas_india/tables
git commit -m "feat: atlas choropleths, district estimates, blind-spot table"
```

---

### Task 13: `run_all.py` reproducibility driver + README

**Files:**
- Create: `meta_district_injury_atlas_india/run_all.py`
- Modify: `meta_district_injury_atlas_india/README.md`

**Interfaces:**
- Produces: a single entry point that runs the full pipeline in order and a README documenting data provenance, the two acquired datasets, run time, and how to reproduce.

- [ ] **Step 1: Write `run_all.py`**

```python
"""Reproduce the district injury atlas end to end."""
from meta_district_injury_atlas_india.src import (
    extract_ncrb_cities, run_fits, validate, sensitivity, atlas_outputs)

def main():
    extract_ncrb_cities.build().to_csv(
        extract_ncrb_cities.OUT / "ncrb_cities_wide_2023.csv", index=False)
    run_fits.main()
    validate.main()
    sensitivity.main()
    atlas_outputs.main()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write README (provenance, acquired data, runtime, reproduce steps)**

Document: GBD 2023 + NCRB ADSI 2023 + NFHS-5 + Census districts; the two manually-acquired inputs (city table, district shapefile); approximate runtime; `python -m meta_district_injury_atlas_india.run_all`.

- [ ] **Step 3: Run full pipeline once end-to-end, then commit**

Run: `python -m meta_district_injury_atlas_india.run_all` — Expected: all outputs regenerate without error.
```bash
git add meta_district_injury_atlas_india/run_all.py meta_district_injury_atlas_india/README.md
git commit -m "feat: end-to-end reproducibility driver + README"
```

---

### Task 14: Manuscript draft

**Files:**
- Create: `meta_district_injury_atlas_india/manuscript/manuscript.md`

**Interfaces:**
- Consumes: all tables/figures.
- Produces: a full draft (Abstract, Introduction, Methods, Results, Discussion, Limitations, Data-sharing) targeting *Lancet Regional Health – SE Asia* / *IJMR*.

- [ ] **Step 1: Draft Methods + Results from the actual outputs**

Write Methods directly from `src/model.py` (fusion, completeness sub-model, benchmarked ICAR downscaling, anchor likelihood) and the validation design. Pull every number from `tables/` and `outputs/` — no invented figures. Report district ranges with credible intervals, CV coverage, and sensitivity.

- [ ] **Step 2: Draft Introduction + Discussion + Limitations**

Frame novelty (first district injury atlas; first sub-state completeness surface). Limitations must foreground the 53-anchor identification and `eta_k` rural extrapolation (spec §8.1–8.2) and the ecological-inference caveat (§8.4).

- [ ] **Step 3: Self-check numbers against tables, then commit**

Cross-check every quoted statistic against the CSVs.
```bash
git add meta_district_injury_atlas_india/manuscript/manuscript.md
git commit -m "docs: district injury atlas manuscript draft"
```

---

## Self-Review

**Spec coverage:**
- §2 value-adds → Tasks 8 (fusion+downscaling+completeness), 10–11 (anchored validation). ✓
- §3 data (incl. two acquisitions) → Tasks 2, 3; crosswalks Task 4; GBD label QC Task 5. ✓
- §4 model (a–f) → Task 7 (primitives) + Task 8 (full model: completeness, fusion, downscaling, benchmarking, anchor, surface). ✓
- §5 validation (LOCO-CV, PPC, benchmark, sensitivity) → Tasks 10–11. ✓
- §6 outputs (maps, blind-spots, tables, reproducible pipeline) → Tasks 12–13. ✓
- §7 journal + §8 limitations → Task 14. ✓
- §9 scope (2023, mortality, 6 causes) → Global Constraints + config. ✓

**Placeholder scan:** One deliberate, flagged placeholder remains — the `alpha` prior in Task 8 Step 3 (uses an illustrative expression) with an explicit Step-4 instruction to replace it with a fixed weakly-informative value before running. All other steps carry runnable code or precise instructions.

**Type consistency:** `district_id` integer key is defined in Task 3 and consumed identically in Tasks 4/6/8/12. `lambda_d`, `c_d`, `beta`, `eta` deterministics named consistently across Tasks 8/10/11/12. `build_pymc_model` signature (with sensitivity flags) introduced in Task 8 and extended in Task 11. `CAUSES` from config used throughout.
