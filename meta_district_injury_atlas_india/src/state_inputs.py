"""State-level GBD + NCRB death inputs by cause, for the fusion layer.

GBD 2023 deaths (Number) with 95% UIs from master_dataset; NCRB ADSI 2023
administrative deaths from the interim files. pop_s is taken as the sum of
district populations in the analytic frame (keeps benchmarking weights and
state rates internally consistent).
"""
import numpy as np
import pandas as pd
from meta_district_injury_atlas_india.config import DATA_PROCESSED, DATA_INTERIM, LOCAL, CAUSES

GBD_MAP = {"all_injury": "all_injuries", "road": "road", "falls": "falls",
           "drowning": "drowning", "burns": "burns", "suicide": "self_harm"}
# Within a cause_group the master dataset stores BOTH the aggregate cause and its
# GBD sub-categories (e.g. cause_group "road" holds "Road injuries" plus pedestrian/
# cyclist/motorcyclist/motor-vehicle/other; "self_harm" holds "Self-harm" plus its
# sub-means). Summing the whole group double-counts the aggregate. Select only the
# aggregate ("parent") cause_gbd label per cause so deaths are counted once.
GBD_PARENT = {"all_injury": "Injuries", "road": "Road injuries", "falls": "Falls",
              "drowning": "Drowning", "burns": "Fire, heat, and hot substances",
              "suicide": "Self-harm"}
NCRB_ACC = {"road": "road_accidents", "falls": "falls", "drowning": "drowning",
            "burns": "fire_burns"}
# NCRB reports J&K/Ladakh and the small UTs separately; GBD reports them as
# combined units. Collapse NCRB to the same granularity before fusion so both
# sources describe the identical population (must match build_districts.STATE_HARM).
_UT_HARM = {
    "Jammu & Kashmir": "Jammu & Kashmir and Ladakh", "Ladakh": "Jammu & Kashmir and Ladakh",
    "Andaman & Nicobar Islands": "Other Union Territories", "Chandigarh": "Other Union Territories",
    "Dadra & Nagar Haveli and Daman & Diu": "Other Union Territories",
    "Lakshadweep": "Other Union Territories", "Puducherry": "Other Union Territories",
}


def _gbd():
    d = pd.read_csv(DATA_PROCESSED / "master_dataset.csv", low_memory=False)
    d = d[(d.source == "gbd2021") & (d.measure == "Deaths") &
          (d.metric_type == "Number") & (d.year == 2023)]
    rows = []
    for cause, cg in GBD_MAP.items():
        grp = d[d.cause_group == cg]
        # keep only the aggregate cause row, not its sub-categories (avoids double count)
        grp = grp[grp.cause_gbd == GBD_PARENT[cause]]
        sub = grp.groupby("state_name_harmonized").agg(
            gbd_deaths=("value", "sum"), gbd_lower=("lower_ui", "sum"),
            gbd_upper=("upper_ui", "sum")).reset_index()
        sub["cause"] = cause
        rows.append(sub)
    return pd.concat(rows).rename(columns={"state_name_harmonized": "state_name"})


def _ncrb():
    acc = pd.read_csv(DATA_INTERIM / "ncrb_accidental_deaths_2023.csv")
    suic = pd.read_csv(DATA_INTERIM / "ncrb_suicides_2023.csv").rename(
        columns={"suicide_deaths_n": "ncrb_deaths"})[["state_name_harmonized", "ncrb_deaths"]]
    acc["state_name_harmonized"] = acc["state_name_harmonized"].replace(_UT_HARM)
    suic["state_name_harmonized"] = suic["state_name_harmonized"].replace(_UT_HARM)
    acc = acc.groupby(["state_name_harmonized", "cause_ncrb"], as_index=False)["deaths_n"].sum()
    suic = suic.groupby("state_name_harmonized", as_index=False)["ncrb_deaths"].sum()
    suic["cause"] = "suicide"
    tot = acc[acc.cause_ncrb == "total_accidental"][["state_name_harmonized", "deaths_n"]].copy()

    out = []
    for cause, nc in NCRB_ACC.items():
        s = acc[acc.cause_ncrb == nc][["state_name_harmonized", "deaths_n"]].copy()
        s = s.rename(columns={"deaths_n": "ncrb_deaths"}); s["cause"] = cause
        out.append(s)
    out.append(suic)
    # all_injury administrative = total accidental + suicides
    ai = tot.merge(suic[["state_name_harmonized", "ncrb_deaths"]], on="state_name_harmonized", how="left")
    ai["ncrb_deaths"] = ai["deaths_n"] + ai["ncrb_deaths"].fillna(0)
    ai["cause"] = "all_injury"
    out.append(ai[["state_name_harmonized", "ncrb_deaths", "cause"]])
    return pd.concat(out).rename(columns={"state_name_harmonized": "state_name"})


def state_inputs():
    g = build_frame_pop()
    df = _gbd().merge(_ncrb(), on=["state_name", "cause"], how="left")
    df = df.merge(g, on="state_name", how="inner")
    df = df[df.cause.isin(CAUSES)].set_index(["state_name", "cause"]).sort_index()
    return df


def build_frame_pop():
    import geopandas as gpd
    g = gpd.read_parquet(LOCAL / "districts_frame.parquet")
    return g.groupby("state_name")["pop_d"].sum().rename("pop_s").reset_index()


if __name__ == "__main__":
    df = state_inputs().reset_index()
    nat = df.groupby("cause")[["gbd_deaths", "ncrb_deaths"]].sum()
    nat["ratio"] = nat.gbd_deaths / nat.ncrb_deaths
    print(nat.round(2).to_string())
    print("\nstates per cause:", df.groupby("cause").size().to_dict())
