"""Regenerate estimate tables, maps, blind-spots, and convergence from saved
idata (numpy-backed, so no JAX device memory involved). Use when fits are done
but post-processing crashed."""
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import arviz as az

from meta_district_injury_atlas_india.config import CAUSES, ANCHOR_CAUSES, OUT, FIG, TAB
from meta_district_injury_atlas_india.src.model import prep, _load_frame
from meta_district_injury_atlas_india.src.run_pipeline import summarize, choropleth

warnings.filterwarnings("ignore")


def main():
    geom = _load_frame()[["district_id", "geometry"]]
    all_est, conv = [], []
    for cause in CAUSES:
        idata = az.from_netcdf(OUT / f"idata_{cause}.nc")
        d = prep(cause)
        s = az.summary(idata, var_names=["gamma", "eta", "beta", "alpha"])
        conv.append({"cause": cause, "max_rhat": float(s["r_hat"].max()),
                     "min_ess": float(s["ess_bulk"].min()),
                     "anchored": cause in ANCHOR_CAUSES})
        est = summarize(idata, d, cause)
        all_est.append(est)
        g = gpd.GeoDataFrame(geom.merge(est, on="district_id", how="right"), geometry="geometry")
        choropleth(g, "rate_mean", f"Injury mortality — {cause} (per 100k, GBD-fused)",
                   FIG / f"map_{cause}_rate.png", "viridis")
        choropleth(g, "rate_ciw", f"Uncertainty (95% CI width) — {cause}",
                   FIG / f"map_{cause}_uncertainty.png", "magma")
        if cause in ANCHOR_CAUSES:
            choropleth(g, "completeness_mean", f"Surveillance completeness — {cause}",
                       FIG / f"map_{cause}_completeness.png", "RdYlGn")
        print(f"[{cause}] rhat={conv[-1]['max_rhat']:.3f} med_rate={est.rate_mean.median():.1f} "
              f"max_rate={est.rate_mean.max():.0f} comp={est.completeness_mean.median():.2f}")

    est = pd.concat(all_est, ignore_index=True)
    est.to_csv(TAB / "district_estimates.csv", index=False)
    pd.DataFrame(conv).to_csv(OUT / "convergence_summary.csv", index=False)
    a = est[est.cause.isin(ANCHOR_CAUSES)].copy()
    a["blindspot_score"] = a.rate_mean * a.rate_ciw * (1 - a.completeness_mean)
    (a.sort_values("blindspot_score", ascending=False).groupby("cause").head(15)
     [["cause", "district_name", "state_name", "rate_mean", "rate_lo", "rate_hi",
       "completeness_mean", "blindspot_score"]]).to_csv(TAB / "blind_spots.csv", index=False)
    print("regenerated district_estimates, blind_spots, convergence, maps")


if __name__ == "__main__":
    main()
