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


def summarize(idata, d, cause, completeness_threshold=0.5):
    """Posterior summary per district, plus a genuine Bayesian blind-spot
    probability: the joint posterior probability, drawn jointly (not from
    independently collapsed means) that a district's rate exceeds the
    national posterior-median rate AND its completeness is below
    `completeness_threshold`, in the SAME posterior draw. This replaces a
    deterministic point-score with an uncertainty-aware quantity that can be
    read as "confidence this is a true blind spot", not just a ranking."""
    post = idata.posterior
    lam = post["lambda_d"].stack(s=("chain", "draw")).values * 1e5   # per 100k, districts x draws
    cdd = post["c_d"].stack(s=("chain", "draw")).values              # districts x draws
    meta = d["meta"]

    # Small, wildly heterogeneous pooled union-territory districts (e.g. Nicobars,
    # Chandigarh, Lakshadweep sharing one "Other Union Territories" GBD/NCRB bucket)
    # have no district-level anchor and no separate state estimate to identify their own
    # covariate/spatial effects; letting them float freely produced implausible outlier
    # rates. For these districts only, use the shared bucket-level (state) rate and
    # completeness posterior directly -- an honest "not separately resolved" estimate --
    # rather than a spuriously precise, unstable district-specific one.
    if "is_pooled_ut" in meta.columns and meta["is_pooled_ut"].any():
        R_state = post["R_state"].stack(s=("chain", "draw")).values * 1e5
        c_state = post["c_state"].stack(s=("chain", "draw")).values
        pooled_mask = meta["is_pooled_ut"].to_numpy()
        sidx = d["sidx"]
        lam = lam.copy(); cdd = cdd.copy()
        lam[pooled_mask, :] = R_state[sidx[pooled_mask], :]
        cdd[pooled_mask, :] = c_state[sidx[pooled_mask], :]

    national_median_draw = np.median(lam, axis=0)                    # one threshold per draw
    blindspot_draw = (lam > national_median_draw[None, :]) & (cdd < completeness_threshold)
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
        "p_blindspot": blindspot_draw.mean(axis=1),
        "is_pooled_ut": meta["is_pooled_ut"].to_numpy() if "is_pooled_ut" in meta.columns else False,
    })
    df["rate_ciw"] = df.rate_hi - df.rate_lo
    df["deaths_est"] = df.rate_mean / 1e5 * df.pop_d
    return df


def choropleth(gdf, col, title, path, cmap="viridis", pct_clip=99, footnote=None):
    """gdf must already be a LEFT join onto the full national district outline, so
    every one of India's districts is drawn; districts with no modelled value for
    this cause/column render grey (missing_kwds) rather than being silently
    omitted from the map."""
    fig, ax = plt.subplots(figsize=(7, 8.6))
    vmax = np.nanpercentile(gdf[col], pct_clip)
    gdf.plot(column=col, cmap=cmap, linewidth=0.05, edgecolor="0.6",
             legend=True, vmax=vmax, ax=ax,
             missing_kwds={"color": "lightgrey", "label": "No data"})
    ax.set_title(title, fontsize=11)
    ax.axis("off")
    n_missing = int(gdf[col].isna().sum())
    note = footnote or ""
    if n_missing:
        note = (note + f" Grey = no modelled estimate ({n_missing} of {len(gdf)} districts).").strip()
    if note:
        fig.text(0.02, 0.01, note, fontsize=6.5, ha="left", va="bottom", wrap=True)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def main(draws=1000, tune=1000, chains=2):
    OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
    from meta_district_injury_atlas_india.src.model import _load_frame
    frame = _load_frame()
    geom = frame[["district_id", "geometry"]]                     # full national outline
    n_pooled = int(frame["is_pooled_ut"].sum())
    ut_note = (f"{n_pooled} districts in small union territories share a single "
               f"pooled national estimate (no separate GBD figure exists for them).")
    all_est, conv = [], []
    for cause in CAUSES:
        idata, d = fit_cause(cause, draws=draws, tune=tune, chains=chains)
        s = az.summary(idata, var_names=["gamma", "eta", "beta", "alpha", "tau"])
        conv.append({"cause": cause, "max_rhat": float(s["r_hat"].max()),
                     "min_ess": float(s["ess_bulk"].min()),
                     "anchored": cause in ANCHOR_CAUSES})
        est = summarize(idata, d, cause)
        all_est.append(est)
        g = geom.merge(est, on="district_id", how="left")          # keep every district
        g = gpd.GeoDataFrame(g, geometry="geometry")
        choropleth(g, "rate_mean", f"Injury mortality — {cause} (per 100k, GBD-fused)",
                   FIG / f"map_{cause}_rate.png", "viridis", footnote=ut_note)
        choropleth(g, "rate_ciw", f"Uncertainty (95% CI width) — {cause}",
                   FIG / f"map_{cause}_uncertainty.png", "magma", footnote=ut_note)
        if cause in ANCHOR_CAUSES:
            choropleth(g, "completeness_mean",
                       f"Surveillance completeness (NCRB/true) — {cause}",
                       FIG / f"map_{cause}_completeness.png", "RdYlGn", footnote=ut_note)
        print(f"[{cause}] rhat={conv[-1]['max_rhat']:.3f} "
              f"rate/100k med={est.rate_mean.median():.1f} "
              f"completeness med={est.completeness_mean.median():.2f}")

    est = pd.concat(all_est, ignore_index=True)
    est.to_csv(TAB / "district_estimates.csv", index=False)
    pd.DataFrame(conv).to_csv(OUT / "convergence_summary.csv", index=False)

    # --- policy artifact: surveillance blind-spots (anchored causes) ---
    # Ranked by p_blindspot: the joint posterior probability (from paired draws) that
    # a district is simultaneously above-median burden and below-threshold completeness.
    a = est[est.cause.isin(ANCHOR_CAUSES)].copy()
    blind = (a.sort_values("p_blindspot", ascending=False)
             .groupby("cause").head(15)
             [["cause", "district_name", "state_name", "rate_mean", "rate_lo", "rate_hi",
               "completeness_mean", "p_blindspot"]])
    blind.to_csv(TAB / "blind_spots.csv", index=False)
    print("\nSaved district_estimates.csv, blind_spots.csv, convergence_summary.csv + maps")
    return est, pd.DataFrame(conv)


if __name__ == "__main__":
    main()
