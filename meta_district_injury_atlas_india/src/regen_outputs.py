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
    frame = _load_frame()
    geom = frame[["district_id", "geometry"]]
    n_pooled = int(frame["is_pooled_ut"].sum())
    ut_note = (f"{n_pooled} districts in small union territories share a single "
               f"pooled national estimate (no separate GBD figure exists for them).")
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
        g = gpd.GeoDataFrame(geom.merge(est, on="district_id", how="left"), geometry="geometry")
        choropleth(g, "rate_mean", f"Injury mortality — {cause} (per 100k, GBD-fused)",
                   FIG / f"map_{cause}_rate.png", "viridis", footnote=ut_note)
        choropleth(g, "rate_ciw", f"Uncertainty (95% CI width) — {cause}",
                   FIG / f"map_{cause}_uncertainty.png", "magma", footnote=ut_note)
        if cause in ANCHOR_CAUSES:
            choropleth(g, "completeness_mean", f"Surveillance completeness — {cause}",
                       FIG / f"map_{cause}_completeness.png", "RdYlGn", footnote=ut_note)
        print(f"[{cause}] rhat={conv[-1]['max_rhat']:.3f} med_rate={est.rate_mean.median():.1f} "
              f"max_rate={est.rate_mean.max():.0f} comp={est.completeness_mean.median():.2f}")

    est = pd.concat(all_est, ignore_index=True)
    est.to_csv(TAB / "district_estimates.csv", index=False)
    pd.DataFrame(conv).to_csv(OUT / "convergence_summary.csv", index=False)
    # pooled-UT districts share one identical bucket-level estimate; excluded from ranking
    a = est[est.cause.isin(ANCHOR_CAUSES) & ~est.get("is_pooled_ut", False)].copy()
    (a.sort_values("p_blindspot", ascending=False).groupby("cause").head(15)
     [["cause", "district_name", "state_name", "rate_mean", "rate_lo", "rate_hi",
       "completeness_mean", "p_blindspot"]]).to_csv(TAB / "blind_spots.csv", index=False)
    print("regenerated district_estimates, blind_spots, convergence, maps")


if __name__ == "__main__":
    main()
