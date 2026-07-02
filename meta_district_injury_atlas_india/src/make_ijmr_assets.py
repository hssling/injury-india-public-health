"""Assemble IJMR submission assets from pipeline outputs.

Writes to submission_ijmr/:
  Table_1_state_fusion.csv     national GBD vs NCRB vs fused + completeness by cause
  Table_2_blindspots.csv       top surveillance blind-spot districts (anchored causes)
  Table_3_validation.csv       5-fold CV metrics + structural sensitivity
  figure_legends.md            legends for the choropleth panels
  numbers.json                 key statistics for filling the manuscript
"""
import json
import numpy as np
import pandas as pd
from meta_district_injury_atlas_india.config import TAB, OUT, HERE, CAUSES, ANCHOR_CAUSES
from meta_district_injury_atlas_india.src.state_inputs import state_inputs

SUB = HERE / "submission_ijmr"


def fmt_ci(m, lo, hi, d=1):
    return f"{m:.{d}f} ({lo:.{d}f}–{hi:.{d}f})"


def build():
    SUB.mkdir(exist_ok=True)
    est = pd.read_csv(TAB / "district_estimates.csv")
    si = state_inputs().reset_index()
    nat = si.groupby("cause")[["gbd_deaths", "ncrb_deaths"]].sum()

    # ---- Table 1: state fusion ----
    rows = []
    for c in CAUSES:
        e = est[est.cause == c]
        fused = e.deaths_est.sum()
        comp = e.completeness_mean
        rows.append({
            "Cause": c, "GBD deaths": int(nat.loc[c, "gbd_deaths"]),
            "NCRB deaths": int(nat.loc[c, "ncrb_deaths"]),
            "GBD/NCRB ratio": round(nat.loc[c, "gbd_deaths"] / nat.loc[c, "ncrb_deaths"], 2),
            "Fused true deaths": int(fused),
            "District completeness median (IQR)":
                f"{comp.median():.2f} ({comp.quantile(.25):.2f}–{comp.quantile(.75):.2f})",
            "Anchored": "Yes" if c in ANCHOR_CAUSES else "No (projected)"}
        )
    t1 = pd.DataFrame(rows)
    t1.to_csv(SUB / "Table_1_state_fusion.csv", index=False)

    # ---- Table 2: blind-spots ----
    b = pd.read_csv(TAB / "blind_spots.csv")
    b["Rate per 100k (95% CrI)"] = [fmt_ci(m, lo, hi) for m, lo, hi in
                                    zip(b.rate_mean, b.rate_lo, b.rate_hi)]
    b["Completeness"] = b.completeness_mean.round(2)
    b["P(blind spot)"] = b.p_blindspot.round(2)
    t2 = (b[["cause", "district_name", "state_name", "Rate per 100k (95% CrI)",
             "Completeness", "P(blind spot)"]]
          .rename(columns={"cause": "Cause", "district_name": "District", "state_name": "State"}))
    t2.to_csv(SUB / "Table_2_blindspots.csv", index=False)

    # ---- Table 3: validation + sensitivity ----
    parts = []
    if (TAB / "cv_metrics.csv").exists():
        cv = pd.read_csv(TAB / "cv_metrics.csv")
        cv["panel"] = "5-fold city CV"
        parts.append(cv)
    if (TAB / "sensitivity.csv").exists():
        parts.append(pd.read_csv(TAB / "sensitivity.csv").assign(panel="sensitivity (road)"))
    if parts:
        pd.concat(parts, ignore_index=True).to_csv(SUB / "Table_3_validation.csv", index=False)

    # ---- figure legends ----
    n_dist = int(est.district_id.nunique())
    n_pooled = int(est.get("is_pooled_ut", pd.Series(dtype=bool)).sum()) if "is_pooled_ut" in est.columns else 0
    (SUB / "figure_legends.md").write_text(
        f"**Figure 1.** District all-injury mortality rate per 100,000 (posterior mean, "
        f"GBD/NCRB-fused), {n_dist} districts. Districts in small union territories that share "
        f"a single pooled national estimate are footnoted, not blanked.\n\n"
        f"**Figure 2.** Surveillance completeness surface (NCRB administrative / fused true "
        f"deaths) for anchored causes (all-injury, road, suicide); green = complete, red = "
        f"severe under-capture.\n\n"
        f"**Figure 3.** Posterior uncertainty (95% credible-interval width) by district.\n",
        encoding="utf-8")

    # ---- key numbers ----
    ai = est[est.cause == "all_injury"]
    nums = {
        "n_districts": int(est.district_id.nunique()),
        "ai_rate_median": round(ai.rate_mean.median(), 1),
        "ai_rate_iqr": [round(ai.rate_mean.quantile(.25), 1), round(ai.rate_mean.quantile(.75), 1)],
        "ratio_falls": round(nat.loc["falls", "gbd_deaths"] / nat.loc["falls", "ncrb_deaths"], 1),
        "falls_completeness_median": round(est[est.cause == "falls"].completeness_mean.median(), 2),
        "ai_completeness_median": round(ai.completeness_mean.median(), 2),
    }
    if (TAB / "cv_metrics.csv").exists():
        cv = pd.read_csv(TAB / "cv_metrics.csv")
        nums["cv"] = cv.round(3).to_dict("records")
    (SUB / "numbers.json").write_text(json.dumps(nums, indent=2), encoding="utf-8")
    return t1, t2, nums


if __name__ == "__main__":
    t1, t2, nums = build()
    print(t1.to_string(index=False))
    print("\nKEY NUMBERS:", json.dumps(nums, indent=2))
