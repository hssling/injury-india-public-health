"""Sensitivity of the anchored-cause fit to model structure.

Variants (evaluated on `road`, the highest-volume anchored cause, via 5-fold
city CV log-RMSE and mean completeness):
  base      full model
  no_icar   drop the spatial ICAR term (covariates only)
  fix_eta   state-constant completeness (eta = 0)
  wide_eta  diffuse completeness slope prior (eta_sd = 1.5)
"""
import warnings
import numpy as np
import pandas as pd
import pymc as pm

from meta_district_injury_atlas_india.config import OUT, TAB
from meta_district_injury_atlas_india.src.model import prep, build_model

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(11)

VARIANTS = {
    "base": {}, "no_icar": {"use_icar": False},
    "fix_eta": {"fix_eta": True}, "wide_eta": {"eta_sd": 1.5},
}


def cv_rmse(cause, kw, k=5, draws=500, tune=500):
    d = prep(cause)
    pos, obs, pop = d["anchor"]["pos"], d["anchor"]["obs"], d["pop"]
    folds = np.array_split(RNG.permutation(len(pos)), k)
    errs, comp = [], []
    for f in folds:
        with build_model(cause, d=d, hold_out_pos=pos[f], **kw):
            idata = pm.sample(draws=draws, tune=tune, chains=2, target_accept=0.9,
                              nuts_sampler="numpyro", random_seed=3, progressbar=False)
        lam = idata.posterior["lambda_d"].stack(s=("chain", "draw")).values
        cdd = idata.posterior["c_d"].stack(s=("chain", "draw")).values
        comp.append(cdd.mean())
        for j in f:
            p = pos[j]
            pred = (pop[p] * lam[p] * cdd[p]).mean()
            errs.append(np.log(max(pred, 1)) - np.log(max(obs[j], 1)))
    return np.sqrt(np.mean(np.square(errs))), float(np.mean(comp))


def main(cause="road"):
    rows = []
    for name, kw in VARIANTS.items():
        rmse, comp = cv_rmse(cause, kw)
        rows.append({"variant": name, "cause": cause,
                     "cv_log_rmse": rmse, "mean_completeness": comp})
        print(f"[{name}] cv_log_rmse={rmse:.3f} mean_completeness={comp:.2f}")
    pd.DataFrame(rows).to_csv(TAB / "sensitivity.csv", index=False)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
