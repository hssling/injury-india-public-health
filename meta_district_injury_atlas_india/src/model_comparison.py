"""Formal spatial-vs-non-spatial model comparison (LOO/WAIC), road cause.

The sensitivity analysis (sensitivity.py) already shows the ICAR spatial term
has a small effect on out-of-sample city cross-validation error. Here we make
that comparison formal: fit the full (ICAR) and no-ICAR variants with
pointwise log-likelihood tracked on the city-anchor observations (the only
likelihood term where between-district structure, spatial or not, is
directly tested against real data), then compare expected log pointwise
predictive density (ELPD) via PSIS-LOO and WAIC. This is the standard
Bayesian-workflow justification for retaining (or dropping) a spatial term,
and is reported as Table S3 in the supplementary material.
"""
import warnings
import pandas as pd
import pymc as pm
import arviz as az

from meta_district_injury_atlas_india.config import TAB
from meta_district_injury_atlas_india.src.model import prep, build_model

warnings.filterwarnings("ignore")


def _fit_with_loglik(cause, **kw):
    """Higher target_accept/chains/draws than the main production fits: this
    comparison is only two models, so the extra compute is affordable, and a
    well-mixed, divergence-free posterior is a precondition for a trustworthy
    PSIS-LOO Pareto-k diagnostic (a poorly tuned sampler degrades Pareto-k for
    reasons that have nothing to do with genuine model-comparison difficulty)."""
    d = prep(cause)
    with build_model(cause, d=d, **kw) as m:
        idata = pm.sample(draws=2000, tune=2000, chains=4, target_accept=0.995,
                          nuts_sampler="numpyro", random_seed=5, progressbar=False)
        n_div = int(idata.sample_stats.diverging.sum())
        pm.compute_log_likelihood(idata, var_names=["city_like"], model=m)
    try:
        import jax; jax.clear_caches()
    except Exception:
        pass
    return idata, n_div


def _pareto_k_summary(loo_result):
    k = loo_result.pareto_k.values
    n = len(k)
    return {"n_obs": n, "pct_good_k": round(100 * (k <= 0.7).mean(), 1),
            "pct_bad_or_worse_k": round(100 * (k > 0.7).mean(), 1)}


def main(cause="road"):
    fits = {"spatial (ICAR)": _fit_with_loglik(cause, use_icar=True),
            "non-spatial (covariates only)": _fit_with_loglik(cause, use_icar=False)}
    models = {name: idata for name, (idata, _) in fits.items()}

    rows = []
    for name, (idata, n_div) in fits.items():
        loo_res = az.loo(idata, var_name="city_like", pointwise=True)
        row = {"model": name, "elpd_loo": round(float(loo_res.elpd), 2),
              "se": round(float(loo_res.se), 2), "n_divergences": n_div}
        row.update(_pareto_k_summary(loo_res))
        rows.append(row)
    loo_table = pd.DataFrame(rows)

    comp = az.compare(models, var_name="city_like").reset_index().rename(columns={"index": "model"})
    keep = ["model", "rank", "elpd_diff", "dse"]
    comp = comp[[c for c in keep if c in comp.columns]]
    out = loo_table.merge(comp, on="model", how="left")
    out.to_csv(TAB / "model_comparison_loo.csv", index=False)
    print(out.to_string(index=False))
    reliable = (out["pct_bad_or_worse_k"] < 30).all()
    print(f"\nPSIS-LOO reliability (Pareto k<=0.7 in >=70% of points): "
         f"{'ADEQUATE' if reliable else 'LOW -- report as exploratory, not confirmatory'}")
    return out


if __name__ == "__main__":
    main()
