"""
Inequality Analysis (Step 4I)
Computes inter-state inequality in injury DALY rates across years.
Metrics: top:bottom ratio, CV, IQR, optional Gini.
"""

import pathlib
import pandas as pd
import numpy as np
import logging

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
OUTPUTS = PROJECT_ROOT / "outputs"
TABLES = PROJECT_ROOT / "tables"
LOGS = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "17_inequality.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def gini_coefficient(values: pd.Series) -> float:
    """Compute Gini coefficient from a series of non-negative values."""
    v = values.dropna().sort_values().values
    n = len(v)
    if n == 0 or v.sum() == 0:
        return np.nan
    cumsum = np.cumsum(v)
    return (n + 1 - 2 * cumsum.sum() / v.sum()) / n


def compute_inequality(df: pd.DataFrame, years=None, cause_group="all_injuries") -> pd.DataFrame:
    if years is None:
        years = [2000, 2005, 2010, 2015, 2019, 2021]

    gbd = df[
        (df["source"] == "gbd2021") &
        (df["sex"] == "Both") &
        (df["age_group"] == "All ages") &
        (df["cause_group"] == cause_group) &
        (df["measure"] == "DALYs") &
        (df["metric_type"] == "Rate") &
        (df["state_name_harmonized"] != "India")
    ].copy()

    if gbd.empty:
        log.warning(f"No GBD DALY rate data for inequality analysis (cause={cause_group})")
        return pd.DataFrame()

    rows = []
    for year in years:
        yr_data = gbd[gbd["year"] == year]["value"].dropna()
        if len(yr_data) < 3:
            log.warning(f"Year {year}: only {len(yr_data)} states — skipping")
            continue

        top_bottom_ratio = yr_data.max() / yr_data.min() if yr_data.min() > 0 else np.nan
        cv = yr_data.std() / yr_data.mean() if yr_data.mean() > 0 else np.nan
        iqr = yr_data.quantile(0.75) - yr_data.quantile(0.25)
        gini = gini_coefficient(yr_data)

        rows.append({
            "year": year,
            "cause_group": cause_group,
            "n_states": len(yr_data),
            "mean_daly_rate": yr_data.mean(),
            "median_daly_rate": yr_data.median(),
            "min_daly_rate": yr_data.min(),
            "max_daly_rate": yr_data.max(),
            "top_bottom_ratio": top_bottom_ratio,
            "cv": cv,
            "iqr": iqr,
            "gini": gini,
            "p25": yr_data.quantile(0.25),
            "p75": yr_data.quantile(0.75),
        })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    log.info(f"Inequality metrics computed for {len(result)} time points")

    if len(result) >= 2:
        first_cv = result.iloc[0]["cv"]
        last_cv = result.iloc[-1]["cv"]
        direction = "increased" if last_cv > first_cv else "decreased"
        log.info(f"Inequality (CV) {direction}: {first_cv:.3f} ({result.iloc[0]['year']}) → "
                 f"{last_cv:.3f} ({result.iloc[-1]['year']})")

    return result


def compute_inequality_ncrb() -> pd.DataFrame:
    """
    Compute inter-state inequality using NCRB 2023 accidental death rates (per lakh).
    Fallback when GBD injury-specific DALY rates are unavailable.
    Source: NCRB ADSI 2023 Table 11 — state accidental death rate per lakh population.
    National average: 31.9 per lakh.
    """
    DATA_INTERIM = PROJECT_ROOT / "data_interim"
    rates_path = DATA_INTERIM / "ncrb_accidental_death_rates_2023.csv"
    if not rates_path.exists():
        log.warning("NCRB rates file not found for inequality fallback.")
        return pd.DataFrame()

    rates = pd.read_csv(rates_path)
    col = "accidental_death_rate_per_lakh"
    # Exclude national average row if present
    vals = rates[rates["state_name_harmonized"] != "India"][col].dropna()

    top_bottom_ratio = vals.max() / vals.min() if vals.min() > 0 else np.nan
    cv = vals.std() / vals.mean() if vals.mean() > 0 else np.nan
    iqr = vals.quantile(0.75) - vals.quantile(0.25)
    gini = gini_coefficient(vals)

    row = {
        "year": 2023,
        "cause_group": "total_accidental",
        "data_source": "ncrb_adsi_2023",
        "n_states": len(vals),
        "mean_rate_per_lakh": round(vals.mean(), 2),
        "median_rate_per_lakh": round(vals.median(), 2),
        "min_rate_per_lakh": round(vals.min(), 2),
        "max_rate_per_lakh": round(vals.max(), 2),
        "top_bottom_ratio": round(top_bottom_ratio, 2),
        "cv": round(cv, 3),
        "iqr": round(iqr, 2),
        "gini": round(gini, 3),
        "p25": round(vals.quantile(0.25), 2),
        "p75": round(vals.quantile(0.75), 2),
        "note": "Inter-state inequality in accidental death rate per lakh pop. (NCRB 2023 Table 11); GBD DALY-based metrics pending injury-specific re-download",
    }
    log.info(f"NCRB inequality: CV={cv:.3f}, Gini={gini:.3f}, top:bottom={top_bottom_ratio:.1f}x")
    log.info(f"  States: n={len(vals)}, mean={vals.mean():.1f}, range=[{vals.min():.1f}–{vals.max():.1f}]")
    return pd.DataFrame([row])


def run():
    log.info("=== Inequality Analysis: Start ===")

    fpath = DATA_PROCESSED / "master_dataset.csv"
    if not fpath.exists():
        log.error("Master dataset not found.")
        return

    df = pd.read_csv(fpath, low_memory=False)

    # Try GBD-based inequality first
    ineq = compute_inequality(df, cause_group="all_injuries")

    if ineq.empty:
        log.info("Falling back to NCRB accidental death rate inequality...")
        ineq = compute_inequality_ncrb()

    if not ineq.empty:
        ineq.to_csv(OUTPUTS / "inequality.csv", index=False)
        try:
            with pd.ExcelWriter(str(TABLES / "Table_S2_inequality.xlsx"), engine="openpyxl") as w:
                ineq.to_excel(w, sheet_name="Inequality_AccidentalDeaths", index=False)
        except Exception as e:
            log.warning(f"Excel write failed: {e}")
        log.info(f"Inequality output: {OUTPUTS / 'inequality.csv'}")
    else:
        log.warning("No inequality results computed.")

    # Cause-specific (GBD-based; will be empty until re-download)
    cause_results = {}
    for cause in ["road", "falls", "self_harm"]:
        cause_ineq = compute_inequality(df, cause_group=cause)
        if not cause_ineq.empty:
            cause_results[cause] = cause_ineq

    if cause_results:
        all_ineq = pd.concat([ineq] + list(cause_results.values()), ignore_index=True)
        all_ineq.to_csv(OUTPUTS / "inequality_all_causes.csv", index=False)

    log.info("=== Inequality Analysis: Complete ===")
    return ineq


if __name__ == "__main__":
    run()
