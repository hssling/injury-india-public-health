"""Bayesian spatial data-fusion + benchmarked downscaling model (per cause).

Layers
------
1. State fusion    T_s ~ LogNormal(log GBD_s, sigma_s);
                   NCRB_s ~ Poisson(T_s * c_s),  c_s = pop-weighted mean of c_d.
2. Completeness    logit(c_d) = gamma + eta * urban_std_d + w_d.
3. Downscaling     log m_d = alpha + X_d beta + tau * phi_d (ICAR) + v_d;
                   benchmarked so pop-weighted mean of lambda_d over state s == T_s/pop_s.
4. Anchor          city_a ~ Poisson(pop_a * lambda_a * c_a)   [anchored causes only].

Sampled with the numpyro (JAX) NUTS backend — no C compiler required.
"""
import numpy as np
import pandas as pd
import scipy.sparse as sp
import geopandas as gpd
import pymc as pm
import pytensor.tensor as pt
import arviz as az

from meta_district_injury_atlas_india.config import LOCAL, OUT, ANCHOR_CAUSES
from meta_district_injury_atlas_india.src.state_inputs import state_inputs
from meta_district_injury_atlas_india.src.build_districts import COVAR_COLS
from meta_district_injury_atlas_india.src.extract_ncrb_cities import build as build_cities

# national GBD/NCRB ratio -> completeness prior mean (c = 1/ratio)
NAT_RATIO = {"all_injury": 1.55, "road": 2.80, "falls": 8.57,
             "drowning": 1.32, "burns": 5.42, "suicide": 2.36}
NAT_RATE = {"all_injury": 90e-5, "road": 18e-5, "falls": 8e-5,
            "drowning": 3e-5, "burns": 2e-5, "suicide": 14e-5}  # per-capita, weak prior


def _anchor_positions(meta):
    """Map the 53 NCRB cities to district_ids in the frame (fuzzy)."""
    from rapidfuzz import process, fuzz
    _, wide, _ = build_cities()
    wide = wide.reset_index()
    wide["key"] = (wide["city_name"].str.replace(r"\(CITY\)", "", regex=True)
                   .str.strip().str.lower())
    lut = {n.lower(): i for i, n in zip(meta.index, meta["district_name"])}
    keys = list(lut)
    citypop = pd.read_csv(LOCAL / "city_population_2023.csv")
    citypop["pop_a"] = citypop["pop_lakh"] * 1e5          # NCRB city population as exposure
    pos, rows = [], []
    for _, r in wide.iterrows():
        hit = process.extractOne(r["key"], keys, scorer=fuzz.WRatio)
        if hit and hit[1] >= 88:
            pos.append(lut[hit[0]]); rows.append(r)
    adf = pd.DataFrame(rows).reset_index(drop=True)
    adf["pos"] = pos
    adf = adf.merge(citypop[["city_name", "pop_a"]], on="city_name", how="left")
    return adf


def _load_frame():
    g = gpd.read_parquet(LOCAL / "districts_frame.parquet").reset_index()
    if "district_id" not in g.columns:
        g = g.rename(columns={"index": "district_id"})
    return g


def prep(cause):
    meta = _load_frame()

    # restrict to states with a finite GBD estimate for this cause (fusion needs it)
    si = state_inputs().reset_index()
    sc = si[si.cause == cause].set_index("state_name")
    gbd_states = set(sc.index[sc["gbd_deaths"].notna()])
    keep = meta["state_name"].isin(gbd_states).to_numpy()

    A = sp.load_npz(LOCAL / "adjacency.npz").tocsr()[keep][:, keep].tocoo()  # subset graph
    meta = meta.loc[keep].reset_index(drop=True)

    states = sorted(meta["state_name"].unique())
    sidx = meta["state_name"].map({s: i for i, s in enumerate(states)}).to_numpy()
    pop = meta["pop_d"].to_numpy(float)

    X = meta[COVAR_COLS].to_numpy(float)
    X = (X - X.mean(0)) / X.std(0)
    urban = (meta["pct_urban"].to_numpy(float) - meta["pct_urban"].mean()) / meta["pct_urban"].std()

    up = A.row < A.col
    edges = np.stack([A.row[up], A.col[up]])

    s = sc.reindex(states)
    gbd = s["gbd_deaths"].to_numpy(float)
    sig = np.clip((np.log(s["gbd_upper"]) - np.log(s["gbd_lower"])) / (2 * 1.96), 0.03, 1.0)
    sig = np.nan_to_num(sig, nan=0.3)
    ncrb = s["ncrb_deaths"].to_numpy(float)
    ncrb_mask = np.isfinite(ncrb)                     # exclude missing NCRB from likelihood
    ncrb = np.nan_to_num(ncrb, nan=0.0)
    pop_s = s["pop_s"].to_numpy(float)

    # sparse pop-weight state x district matrix: row s, col d = pop_d/pop_s
    Mrows, Mcols, Mvals = [], [], []
    for d in range(len(meta)):
        Mrows.append(sidx[d]); Mcols.append(d); Mvals.append(pop[d])
    M = sp.csr_matrix((Mvals, (Mrows, Mcols)), shape=(len(states), len(meta)))
    Mw = M.multiply(1.0 / M.sum(1)).tocsr()   # pop-weighted mean operator

    anchor = None
    if cause in ANCHOR_CAUSES:
        adf = _anchor_positions(meta)
        obs = adf[cause].to_numpy(float)
        keep = np.isfinite(obs) & np.isfinite(adf["pop_a"].to_numpy())
        anchor = dict(pos=adf["pos"].to_numpy()[keep], obs=obs[keep],
                      pop_a=adf["pop_a"].to_numpy(float)[keep])

    return dict(meta=meta, states=states, sidx=sidx, pop=pop, X=X, urban=urban,
                edges=edges, gbd=gbd, sig=sig, ncrb=ncrb, ncrb_mask=ncrb_mask,
                pop_s=pop_s, Mw=Mw, anchor=anchor)


def build_model(cause, d=None, hold_out_pos=None, eta_sd=0.5, fix_eta=False, use_icar=True):
    if d is None:
        d = prep(cause)
    Mw = pt.as_tensor(np.asarray(d["Mw"].todense()))
    sidx = d["sidx"]; pop = d["pop"]; e0, e1 = d["edges"]
    logit0 = np.log((1 / NAT_RATIO[cause]) / (1 - 1 / NAT_RATIO[cause]))

    with pm.Model() as m:
        # ---- fusion: true state deaths ----
        T = pm.LogNormal("T", mu=np.log(d["gbd"]), sigma=d["sig"], shape=len(d["states"]))
        R_state = pm.Deterministic("R_state", T / d["pop_s"])
        # ---- completeness sub-model ----
        gamma = pm.Normal("gamma", logit0, 0.5)
        eta = pm.Data("eta", 0.0) if fix_eta else pm.Normal("eta", 0.0, eta_sd)
        w = pm.Normal("w", 0.0, 0.3, shape=len(pop))
        c_d = pm.Deterministic("c_d", pm.math.sigmoid(gamma + eta * d["urban"] + w))
        c_state = pt.dot(Mw, c_d)
        nm = d["ncrb_mask"]
        pm.Poisson("ncrb_like", mu=(T * c_state)[nm], observed=d["ncrb"][nm])
        # ---- downscaling (true rate), benchmarked ----
        alpha = pm.Normal("alpha", np.log(NAT_RATE[cause]), 1.0)
        beta = pm.Normal("beta", 0.0, 0.5, shape=d["X"].shape[1])
        v = pm.Normal("v", 0.0, 0.3, shape=len(pop))
        raw = alpha + pt.dot(d["X"], beta) + v
        if use_icar:
            tau = pm.HalfNormal("tau", 1.0)
            phi = pm.Normal("phi", 0.0, 1.0, shape=len(pop))
            pm.Potential("icar", -0.5 * pt.sum((phi[e0] - phi[e1]) ** 2))
            pm.Potential("phi_soft", -0.5 * (pt.sum(phi) ** 2) / (0.001 * len(pop)) ** 0.5)
            raw = raw + tau * phi
        lam_raw = pt.exp(raw)
        denom = pt.dot(Mw, lam_raw)                       # pop-weighted state mean
        lam_d = pm.Deterministic("lambda_d", lam_raw * (R_state / denom)[sidx])
        # ---- anchor likelihood ----
        if d["anchor"] is not None:
            pos, obs = d["anchor"]["pos"], d["anchor"]["obs"]
            pop_a = d["anchor"]["pop_a"]
            if hold_out_pos is not None:
                mask = ~np.isin(pos, np.atleast_1d(hold_out_pos))
                pos, obs, pop_a = pos[mask], obs[mask], pop_a[mask]
            mu = pop_a * lam_d[pos] * c_d[pos]         # city population as exposure
            pm.Poisson("city_like", mu=mu, observed=obs)
    return m


def fit_cause(cause, draws=800, tune=800, chains=2, **kw):
    d = prep(cause)
    with build_model(cause, d=d, **kw):
        idata = pm.sample(draws=draws, tune=tune, chains=chains, target_accept=0.9,
                          nuts_sampler="numpyro", random_seed=42, progressbar=False)
    idata.to_netcdf(OUT / f"idata_{cause}.nc")
    return idata, d


if __name__ == "__main__":
    idata, d = fit_cause("road", draws=400, tune=400)
    s = az.summary(idata, var_names=["gamma", "eta", "beta", "tau", "alpha"])
    print(s[["mean", "sd", "r_hat", "ess_bulk"]].to_string())
    lam = idata.posterior["lambda_d"].mean(("chain", "draw")).values
    print(f"\ndistrict rate/100k: min {lam.min()*1e5:.1f} med {np.median(lam)*1e5:.1f} "
          f"max {lam.max()*1e5:.1f}")
    print(f"max r_hat={float(s['r_hat'].max()):.3f}")
