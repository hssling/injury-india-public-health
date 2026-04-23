"""
Hidden Disability Burden Index (HDBI) — Step 4D
Computes two definitions:
  A: HDBI_z = z(YLD rate) - z(death rate)
  B: HDBI_rank = rank(YLD rate) - rank(death rate)

States with positive HDBI have disproportionate disability burden
relative to their mortality burden — the "hidden disability" phenomenon.
"""

import pathlib
import pandas as pd
import numpy as np
import logging
from scipy import stats

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
OUTPUTS = PROJECT_ROOT / "outputs"
TABLES = PROJECT_ROOT / "tables"
LOGS = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "12_hdbi.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def compute_hdbi(df: pd.DataFrame, year: int = 2021,
                  cause_group: str = "all_injuries") -> pd.DataFrame:
    """Compute HDBI for all states for a given year and cause."""
    gbd = df[
        (df["source"] == "gbd2021") &
        (df["year"] == year) &
        (df["sex"] == "Both") &
        (df["age_group"] == "All ages") &
        (df["cause_group"] == cause_group) &
        (df["state_name_harmonized"] != "India")
    ].copy()

    if gbd.empty:
        log.warning(f"No GBD data for HDBI (year={year}, cause={cause_group})")
        return pd.DataFrame()

    # Pivot to get YLD rate and death rate side by side
    gbd_rate = gbd[gbd["metric_type"] == "Rate"]
    pivot = gbd_rate.pivot_table(
        index="state_name_harmonized",
        columns="measure",
        values="value",
        aggfunc="first"
    ).reset_index()

    # Rename to standard
    col_map = {}
    for c in pivot.columns:
        cl = c.lower()
        if "yld" in cl:
            col_map[c] = "yld_rate"
        elif "yll" in cl and "yld" not in cl:
            col_map[c] = "yll_rate"
        elif "daly" in cl:
            col_map[c] = "daly_rate"
        elif "death" in cl:
            col_map[c] = "death_rate"
    pivot = pivot.rename(columns=col_map)

    if "yld_rate" not in pivot.columns or "death_rate" not in pivot.columns:
        log.warning("YLD rate or death rate columns not found in GBD data.")
        return pd.DataFrame()

    # Definition A: z-score based
    pivot["z_yld_rate"] = stats.zscore(pivot["yld_rate"].fillna(pivot["yld_rate"].mean()))
    pivot["z_death_rate"] = stats.zscore(pivot["death_rate"].fillna(pivot["death_rate"].mean()))
    pivot["hdbi_z"] = pivot["z_yld_rate"] - pivot["z_death_rate"]

    # Definition B: rank based (rank 1 = highest burden)
    pivot["rank_yld"] = pivot["yld_rate"].rank(ascending=False)
    pivot["rank_death"] = pivot["death_rate"].rank(ascending=False)
    pivot["hdbi_rank"] = pivot["rank_yld"] - pivot["rank_death"]
    # Positive: state ranks higher on YLD than deaths (hidden disability)
    # Negative: state ranks higher on deaths than YLD (mortality-prominent)

    # Classification
    pivot["hdbi_direction"] = pd.cut(
        pivot["hdbi_z"],
        bins=[-np.inf, -0.5, 0.5, np.inf],
        labels=["mortality_prominent", "balanced", "disability_prominent"]
    )

    pivot["cause_group"] = cause_group
    pivot["year"] = year

    log.info(f"HDBI computed: {len(pivot)} states")
    log.info(f"Disability-prominent states: "
             f"{(pivot['hdbi_direction'] == 'disability_prominent').sum()}")
    log.info(f"Mortality-prominent states: "
             f"{(pivot['hdbi_direction'] == 'mortality_prominent').sum()}")

    if "hdbi_z" in pivot.columns:
        top5_hidden = pivot.nlargest(5, "hdbi_z")[["state_name_harmonized", "hdbi_z", "hdbi_rank"]]
        log.info(f"Top 5 hidden disability states:\n{top5_hidden.to_string()}")

    return pivot.sort_values("hdbi_z", ascending=False).reset_index(drop=True)


def run():
    log.info("=== HDBI Analysis: Start ===")

    fpath = DATA_PROCESSED / "master_dataset.csv"
    if not fpath.exists():
        log.error("Master dataset not found.")
        return

    df = pd.read_csv(fpath, low_memory=False)

    # Main analysis: all injuries, 2021
    hdbi = compute_hdbi(df, year=2021, cause_group="all_injuries")

    results = []

    if not hdbi.empty:
        hdbi.to_csv(OUTPUTS / "hdbi.csv", index=False)
        log.info(f"HDBI output: {OUTPUTS / 'hdbi.csv'}")
        results.append(hdbi)

        try:
            with pd.ExcelWriter(str(TABLES / "Table2b_hdbi.xlsx"), engine="openpyxl") as w:
                hdbi.to_excel(w, sheet_name="HDBI_AllInjuries", index=False)
        except Exception as e:
            log.warning(f"Excel write failed: {e}")
    else:
        log.warning("No HDBI results — data not yet available.")

    # Sensitivity: cause-specific HDBI
    for cause in ["road", "falls", "self_harm"]:
        hdbi_cause = compute_hdbi(df, year=2021, cause_group=cause)
        if not hdbi_cause.empty:
            hdbi_cause.to_csv(OUTPUTS / f"hdbi_{cause}.csv", index=False)
            results.append(hdbi_cause)

    if results:
        all_hdbi = pd.concat(results, ignore_index=True)
        all_hdbi.to_csv(OUTPUTS / "hdbi_all_causes.csv", index=False)

    log.info("=== HDBI Analysis: Complete ===")
    return hdbi if not hdbi.empty else pd.DataFrame()


if __name__ == "__main__":
    run()
