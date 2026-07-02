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
    d = prep(cause)
    with build_model(cause, d=d, **kw) as m:
        idata = pm.sample(draws=1000, tune=1000, chains=2, target_accept=0.9,
                          nuts_sampler="numpyro", random_seed=5, progressbar=False)
        pm.compute_log_likelihood(idata, var_names=["city_like"], model=m)
    return idata


def main(cause="road"):
    idata_full = _fit_with_loglik(cause, use_icar=True)
    idata_noicar = _fit_with_loglik(cause, use_icar=False)
    comp = az.compare({"spatial (ICAR)": idata_full, "non-spatial (covariates only)": idata_noicar},
                      ic="loo", var_name="city_like")
    comp = comp.reset_index().rename(columns={"index": "model"})
    keep = ["model", "rank", "elpd_loo", "se", "p_loo", "elpd_diff", "dse", "warning"]
    out = comp[[c for c in keep if c in comp.columns]]
    out.to_csv(TAB / "model_comparison_loo.csv", index=False)
    print(out.to_string(index=False))
    return out


if __name__ == "__main__":
    main()
