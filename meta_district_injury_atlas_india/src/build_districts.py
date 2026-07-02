"""Canonical district analytic frame + ICAR adjacency.

Frame = udit-001/india-maps-data district polygons (759 units; current
post-2014 Telangana split and current Ladakh/J&K split; state name given
directly by the source, sourced from LGD/Survey of India/Bhuvan/DataMeet).
Onto it we join:
  * harmonized state, mapped to the granularity GBD 2023 reports at (GBD
    reports Jammu & Kashmir and Ladakh as one combined unit, and the five
    smallest union territories as a single "Other Union Territories" unit;
    districts in those states are tagged accordingly so the fusion stage
    has a matching state-level GBD/NCRB estimate to downscale)
  * pop_d and pct_urban  (Census 2011 district table, fuzzy name+state match)
  * NFHS-5 alcohol/tobacco covariates (fuzzy name match)
Unmatched joins are state-mean imputed and logged. District populations are
rescaled within state so they sum to the state census total (removes
imputation bias in the benchmarking weights).
"""
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from rapidfuzz import process, fuzz
from libpysal.weights import Queen, KNN
from meta_district_injury_atlas_india.config import DATA_RAW, LOCAL, OUT

warnings.filterwarnings("ignore")

# source st_nm -> the state-level unit GBD 2023 actually reports (fusion granularity)
STATE_HARM = {
    "Jammu and Kashmir": "Jammu & Kashmir and Ladakh",
    "Ladakh": "Jammu & Kashmir and Ladakh",
    "Andaman and Nicobar Islands": "Other Union Territories",
    "Chandigarh": "Other Union Territories",
    "Dadra and Nagar Haveli and Daman and Diu": "Other Union Territories",
    "Lakshadweep": "Other Union Territories",
    "Puducherry": "Other Union Territories",
}
# small UTs with no separate GBD estimate: modelled off the pooled national
# "Other Union Territories" rate; flagged (not silently blank) on the maps.
POOLED_UT_STATES = {"Andaman and Nicobar Islands", "Chandigarh",
                    "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep", "Puducherry"}
NFHS_COVARS = {
    "Women age 15 years and above who consume alcohol (%)": "alc_f",
    "Men age 15 years and above who consume alcohol (%)": "alc_m",
    "Women age 15 years and above who use any kind of tobacco (%)": "tob_f",
    "Men age 15 years and above who use any kind of tobacco (%)": "tob_m",
}
COVAR_COLS = ["alc_f", "alc_m", "tob_f", "tob_m", "pct_urban"]


def _fuzzy(names, choices, cutoff=86):
    lut = {c.lower(): c for c in choices}
    keys = list(lut)
    out = []
    for n in names:
        hit = process.extractOne(str(n).lower(), keys, scorer=fuzz.WRatio)
        out.append(lut[hit[0]] if hit and hit[1] >= cutoff else None)
    return out


def build(save=True):
    g = gpd.read_file(LOCAL / "districts_v2.geojson").to_crs(4326).reset_index(drop=True)
    g = g.rename(columns={"district": "district_name", "st_nm": "admin_state_name"})
    g = g[g["district_name"].notna()]  # source carries one unnamed (dt_code=null) row per state
    dt_col = "dt_code" if "dt_code" in g.columns else None
    dedup_key = [dt_col] if dt_col else ["district_name", "admin_state_name"]
    g = g.drop_duplicates(subset=dedup_key, keep="first")  # source repeats a few single-district UTs
    g = g[["district_name", "admin_state_name", "geometry"]].copy()
    g["geometry"] = g.geometry.buffer(0)  # fix any invalid rings

    # state_name = the level GBD 2023 reports at (fusion granularity);
    # admin_state_name = the real administrative state (used for census/NFHS matching
    # and for map footnoting of pooled union territories).
    g["state_name"] = g["admin_state_name"].replace(STATE_HARM)
    g["is_pooled_ut"] = g["admin_state_name"].isin(POOLED_UT_STATES)

    # --- Census 2011: population + pct_urban + fuzzy match on name within admin state ---
    cen = pd.read_csv(LOCAL / "census2011.csv")
    cen["pct_urban"] = 100 * cen["Urban_Households"] / (
        cen["Urban_Households"] + cen["Rural_Households"]).replace(0, np.nan)
    cen["state_h"] = cen["State name"].str.title().replace({
        "Orissa": "Odisha", "Uttarakhand": "Uttarakhand", "Nct Of Delhi": "Delhi",
        "Jammu And Kashmir": "Jammu and Kashmir",
        "Andaman And Nicobar Islands": "Andaman and Nicobar Islands",
        "Dadra And Nagar Haveli And Daman And Diu": "Dadra and Nagar Haveli and Daman and Diu"})
    cen_pop, cen_urb = {}, {}
    for stt, sub in g.groupby("admin_state_name"):
        pool = cen[cen["state_h"].str.lower() == str(stt).lower()]
        if len(pool) == 0:
            pool = cen
        matched = _fuzzy(sub["district_name"], pool["District name"].tolist(), cutoff=80)
        lut_pop = dict(zip(pool["District name"], pool["Population"]))
        lut_urb = dict(zip(pool["District name"], pool["pct_urban"]))
        for idx, m in zip(sub.index, matched):
            if m is not None:
                cen_pop[idx] = lut_pop.get(m); cen_urb[idx] = lut_urb.get(m)
    g["pop_d"] = pd.Series(cen_pop)
    g["pct_urban"] = pd.Series(cen_urb)

    # --- NFHS-5 alcohol/tobacco, fuzzy match on district name (national pool) ---
    nfhs = pd.read_csv(DATA_RAW / "NFHS_5_India_Districts_Factsheet_Data(Sheet1).csv")
    nfhs = nfhs.rename(columns={"District Names": "nf_name", **NFHS_COVARS})
    nfhs_lut = {c: dict(zip(nfhs["nf_name"], nfhs[c])) for c in NFHS_COVARS.values()}
    match = _fuzzy(g["district_name"], nfhs["nf_name"].tolist(), cutoff=84)
    for c in NFHS_COVARS.values():
        g[c] = [nfhs_lut[c].get(m, np.nan) if m else np.nan for m in match]

    # --- impute (admin-state mean -> national mean), log coverage ---
    cov = {"census_pop": g["pop_d"].notna().mean(), "nfhs": g["alc_m"].notna().mean()}
    for col in ["pop_d", "pct_urban"] + list(NFHS_COVARS.values()):
        g[col] = g.groupby("admin_state_name")[col].transform(lambda s: s.fillna(s.mean()))
        g[col] = g[col].fillna(g[col].mean())

    # --- rescale district pop within admin state to sum to state census total ---
    state_tot = cen.groupby("state_h")["Population"].sum()
    def _rescale(sub):
        stt = sub["admin_state_name"].iloc[0]
        tgt = state_tot.get(stt, sub["pop_d"].sum())
        return sub["pop_d"] * (tgt / sub["pop_d"].sum())
    g["pop_d"] = g.groupby("admin_state_name", group_keys=False).apply(_rescale)

    g = g.reset_index(drop=True)
    g.index.name = "district_id"

    # --- queen adjacency, reconnect islands, symmetric binary ---
    w = Queen.from_dataframe(g, use_index=False)
    if w.islands:
        wk = KNN.from_dataframe(g, k=1)
        neigh = {i: list(set(w.neighbors[i]) | set(wk.neighbors[i])) for i in range(len(g))}
        from libpysal.weights import W
        w = W(neigh)
    A = (w.sparse + w.sparse.T)
    A = (A > 0).astype(int)

    if save:
        OUT.mkdir(exist_ok=True); LOCAL.mkdir(exist_ok=True)
        g.to_parquet(LOCAL / "districts_frame.parquet")
        import scipy.sparse as sp
        sp.save_npz(LOCAL / "adjacency.npz", A.tocsr())
        pd.DataFrame([cov]).to_csv(OUT / "qc_join_coverage.csv", index=False)
        pd.Series(w.islands if w.islands else [], dtype=object).to_csv(
            OUT / "qc_adjacency_islands.csv", index=False)
    return g, A, cov


if __name__ == "__main__":
    g, A, cov = build()
    print(f"districts={len(g)} states={g.state_name.nunique()} "
          f"census_cov={cov['census_pop']:.2f} nfhs_cov={cov['nfhs']:.2f}")
    print(f"adjacency nnz={A.nnz} mean_neighbors={A.sum()/len(g):.1f} "
          f"symmetric={(A!=A.T).nnz==0} islands={0}")
    print(g[["district_name","state_name","pop_d","pct_urban","alc_m","tob_m"]].head())
