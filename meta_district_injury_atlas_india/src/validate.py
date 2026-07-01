"""Out-of-sample validation for anchored causes: 5-fold city cross-validation.

Each fold holds out ~1/5 of the 53 anchor cities from the city likelihood,
refits, and predicts the held-out cities' administrative-scale deaths
(pop_a * lambda_a * c_a). Reports log-scale RMSE/MAE and 95% interval coverage
— the honest test that the covariate + spatial structure generalizes to
districts the model did not see.
"""
import warnings
import numpy as np
import pandas as pd
import pymc as pm

from meta_district_injury_atlas_india.config import ANCHOR_CAUSES, OUT, TAB
from meta_district_injury_atlas_india.src.model import prep, build_model

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(7)


def cv_cause(cause, k=5, draws=600, tune=600):
    d = prep(cause)
    pos = d["anchor"]["pos"]; obs = d["anchor"]["obs"]
    pop = d["pop"]
    order = RNG.permutation(len(pos))
    folds = np.array_split(order, k)
    rows = []
    for f in folds:
        ho = pos[f]
        with build_model(cause, d=d, hold_out_pos=ho):
            idata = pm.sample(draws=draws, tune=tune, chains=2, target_accept=0.9,
                              nuts_sampler="numpyro", random_seed=1, progressbar=False)
        lam = idata.posterior["lambda_d"].stack(s=("chain", "draw")).values
        cdd = idata.posterior["c_d"].stack(s=("chain", "draw")).values
        for j in f:
            p = pos[j]
            pred = pop[p] * lam[p] * cdd[p]           # posterior predictive deaths
            rows.append({"cause": cause, "pos": int(p), "observed": obs[j],
                         "pred_mean": pred.mean(),
                         "pred_lo": np.percentile(pred, 2.5),
                         "pred_hi": np.percentile(pred, 97.5)})
    r = pd.DataFrame(rows)
    r["in95"] = (r.observed >= r.pred_lo) & (r.observed <= r.pred_hi)
    r["log_err"] = np.log(r.pred_mean.clip(1)) - np.log(r.observed.clip(1))
    return r


def main(k=5):
    OUT.mkdir(exist_ok=True); TAB.mkdir(exist_ok=True)
    all_r, metrics = [], []
    for cause in ANCHOR_CAUSES:
        r = cv_cause(cause, k=k)
        all_r.append(r)
        metrics.append({"cause": cause, "n_cities": len(r),
                        "coverage95": r.in95.mean(),
                        "log_rmse": np.sqrt((r.log_err ** 2).mean()),
                        "log_mae": r.log_err.abs().mean(),
                        "spearman": r[["observed", "pred_mean"]].corr("spearman").iloc[0, 1]})
        print(f"[{cause}] coverage95={metrics[-1]['coverage95']:.2f} "
              f"log_rmse={metrics[-1]['log_rmse']:.2f} "
              f"spearman={metrics[-1]['spearman']:.2f}")
    pd.concat(all_r, ignore_index=True).to_csv(OUT / "cv_predictions.csv", index=False)
    pd.DataFrame(metrics).to_csv(TAB / "cv_metrics.csv", index=False)
    return pd.DataFrame(metrics)


if __name__ == "__main__":
    main()
