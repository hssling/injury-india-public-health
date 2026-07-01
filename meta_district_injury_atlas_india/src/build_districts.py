"""Canonical district analytic frame + ICAR adjacency.

Frame = geoBoundaries IND ADM2 (735 polygons) so every modelled unit has
geometry (needed for the spatial term). Onto it we join:
  * harmonized state (spatial join to india_states.geojson, name-harmonized)
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

# old geojson state spelling -> harmonized (master_dataset) spelling
STATE_HARM = {
    "Orissa": "Odisha", "Uttaranchal": "Uttarakhand",
    "Jammu and Kashmir": "Jammu & Kashmir", "Andaman and Nicobar": "Andaman & Nicobar Islands",
    "Dadra and Nagar Haveli": "Dadra & Nagar Haveli and Daman & Diu",
    "Daman and Diu": "Dadra & Nagar Haveli and Daman & Diu",
    "Puducherry": "Puducherry", "Delhi": "Delhi",
}
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
    g = gpd.read_file(LOCAL / "districts_adm2.geojson").to_crs(4326).reset_index(drop=True)
    g = g.rename(columns={"shapeName": "district_name"})[["district_name", "geometry"]]

    # --- state via representative-point spatial join, then snap strays to nearest ---
    st = gpd.read_file(DATA_RAW / "india_states.geojson").to_crs(4326)[["NAME_1", "geometry"]]
    cent = g.copy(); cent["geometry"] = cent.geometry.representative_point()
    j = gpd.sjoin(cent, st, how="left", predicate="within").drop(columns="index_right")
    miss = j["NAME_1"].isna()
    if miss.any():
        for i in j[miss].index:
            d = st.distance(cent.geometry[i])
            j.loc[i, "NAME_1"] = st.loc[d.idxmin(), "NAME_1"]
    g["state_name"] = j["NAME_1"].replace(STATE_HARM).values

    # --- Census 2011: population + pct_urban + fuzzy match on name within state ---
    cen = pd.read_csv(LOCAL / "census2011.csv")
    cen["pct_urban"] = 100 * cen["Urban_Households"] / (
        cen["Urban_Households"] + cen["Rural_Households"]).replace(0, np.nan)
    cen["state_h"] = cen["State name"].str.title().replace({
        "Orissa": "Odisha", "Uttarakhand": "Uttarakhand", "Nct Of Delhi": "Delhi",
        "Jammu And Kashmir": "Jammu & Kashmir",
        "Andaman And Nicobar Islands": "Andaman & Nicobar Islands"})
    cen_pop, cen_urb = {}, {}
    g["_cid"] = None
    for stt, sub in g.groupby("state_name"):
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

    # --- impute (state mean -> national mean), log coverage ---
    cov = {"census_pop": g["pop_d"].notna().mean(), "nfhs": g["alc_m"].notna().mean()}
    for col in ["pop_d", "pct_urban"] + list(NFHS_COVARS.values()):
        g[col] = g.groupby("state_name")[col].transform(lambda s: s.fillna(s.mean()))
        g[col] = g[col].fillna(g[col].mean())

    # --- rescale district pop within state to sum to state census total ---
    state_tot = cen.groupby("state_h")["Population"].sum()
    def _rescale(sub):
        stt = sub["state_name"].iloc[0]
        tgt = state_tot.get(stt, sub["pop_d"].sum())
        return sub["pop_d"] * (tgt / sub["pop_d"].sum())
    g["pop_d"] = g.groupby("state_name", group_keys=False).apply(_rescale)

    g = g.drop(columns="_cid").reset_index(drop=True)
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
