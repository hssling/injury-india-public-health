"""Fit all causes, build district estimate tables, blind-spot ranking, and maps."""
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import arviz as az
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from meta_district_injury_atlas_india.config import CAUSES, ANCHOR_CAUSES, LOCAL, OUT, FIG, TAB
from meta_district_injury_atlas_india.src.model import fit_cause, NAT_RATIO

warnings.filterwarnings("ignore")


def summarize(idata, d, cause):
    post = idata.posterior
    lam = post["lambda_d"].stack(s=("chain", "draw")).values * 1e5   # per 100k
    cdd = post["c_d"].stack(s=("chain", "draw")).values
    meta = d["meta"]
    df = pd.DataFrame({
        "district_id": meta["district_id"].values,
        "district_name": meta["district_name"].values,
        "state_name": meta["state_name"].values,
        "cause": cause,
        "pop_d": d["pop"],
        "rate_mean": lam.mean(1), "rate_lo": np.percentile(lam, 2.5, 1),
        "rate_hi": np.percentile(lam, 97.5, 1),
        "completeness_mean": cdd.mean(1),
        "completeness_lo": np.percentile(cdd, 2.5, 1),
        "completeness_hi": np.percentile(cdd, 97.5, 1),
    })
    df["rate_ciw"] = df.rate_hi - df.rate_lo
    df["deaths_est"] = df.rate_mean / 1e5 * df.pop_d
    return df


def choropleth(gdf, col, title, path, cmap="viridis", pct_clip=99):
    fig, ax = plt.subplots(figsize=(7, 8))
    vmax = np.nanpercentile(gdf[col], pct_clip)
    gdf.plot(column=col, cmap=cmap, linewidth=0.05, edgecolor="0.6",
             legend=True, vmax=vmax, ax=ax,
             missing_kwds={"color": "lightgrey"})
    ax.set_title(title, fontsize=11)
    ax.axis("off")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def main(draws=1000, tune=1000, chains=2):
    OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
    from meta_district_injury_atlas_india.src.model import _load_frame
    geom = _load_frame()[["district_id", "geometry"]]
    all_est, conv = [], []
    for cause in CAUSES:
        idata, d = fit_cause(cause, draws=draws, tune=tune, chains=chains)
        s = az.summary(idata, var_names=["gamma", "eta", "beta", "alpha", "tau"])
        conv.append({"cause": cause, "max_rhat": float(s["r_hat"].max()),
                     "min_ess": float(s["ess_bulk"].min()),
                     "anchored": cause in ANCHOR_CAUSES})
        est = summarize(idata, d, cause)
        all_est.append(est)
        g = geom.merge(est, on="district_id", how="right")
        g = gpd.GeoDataFrame(g, geometry="geometry")
        choropleth(g, "rate_mean", f"Injury mortality — {cause} (per 100k, GBD-fused)",
                   FIG / f"map_{cause}_rate.png", "viridis")
        choropleth(g, "rate_ciw", f"Uncertainty (95% CI width) — {cause}",
                   FIG / f"map_{cause}_uncertainty.png", "magma")
        if cause in ANCHOR_CAUSES:
            choropleth(g, "completeness_mean",
                       f"Surveillance completeness (NCRB/true) — {cause}",
                       FIG / f"map_{cause}_completeness.png", "RdYlGn")
        print(f"[{cause}] rhat={conv[-1]['max_rhat']:.3f} "
              f"rate/100k med={est.rate_mean.median():.1f} "
              f"completeness med={est.completeness_mean.median():.2f}")

    est = pd.concat(all_est, ignore_index=True)
    est.to_csv(TAB / "district_estimates.csv", index=False)
    pd.DataFrame(conv).to_csv(OUT / "convergence_summary.csv", index=False)

    # --- policy artifact: surveillance blind-spots (anchored causes) ---
    a = est[est.cause.isin(ANCHOR_CAUSES)].copy()
    a["blindspot_score"] = a.rate_mean * a.rate_ciw * (1 - a.completeness_mean)
    blind = (a.sort_values("blindspot_score", ascending=False)
             .groupby("cause").head(15)
             [["cause", "district_name", "state_name", "rate_mean", "rate_lo", "rate_hi",
               "completeness_mean", "blindspot_score"]])
    blind.to_csv(TAB / "blind_spots.csv", index=False)
    print("\nSaved district_estimates.csv, blind_spots.csv, convergence_summary.csv + maps")
    return est, pd.DataFrame(conv)


if __name__ == "__main__":
    main()
