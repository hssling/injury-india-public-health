"""
Fatal–Non-Fatal Decomposition (Step 4C)
Computes YLL fraction, YLD fraction, and YLD:YLL ratio per state and cause.
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
        logging.FileHandler(LOGS / "11_decomposition.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def run():
    log.info("=== Decomposition Analysis: Start ===")

    fpath = DATA_PROCESSED / "master_dataset.csv"
    if not fpath.exists():
        log.error("Master dataset not found. Run assembly step first.")
        return

    df = pd.read_csv(fpath, low_memory=False)

    # Filter: GBD, 2021, both sexes, all ages, state-level (not India national)
    gbd = df[
        (df["source"] == "gbd2021") &
        (df["year"] == 2021) &
        (df["sex"] == "Both") &
        (df["age_group"] == "All ages") &
        (df["metric_type"] == "Number") &
        (df["state_name_harmonized"] != "India")
    ].copy()

    if gbd.empty:
        log.warning("No GBD data for decomposition. Placeholder output created.")
        pd.DataFrame(columns=["state_name_harmonized", "cause_group", "dalys_n",
                               "ylls_n", "ylds_n", "yll_fraction", "yld_fraction",
                               "yld_yll_ratio"]).to_csv(OUTPUTS / "decomposition.csv", index=False)
        return

    # Pivot measures
    pivot = gbd.pivot_table(
        index=["state_name_harmonized", "cause_group"],
        columns="measure",
        values="value",
        aggfunc="first"
    ).reset_index()

    # Rename columns
    col_map = {}
    for c in pivot.columns:
        cl = c.lower()
        if "daly" in cl:
            col_map[c] = "dalys_n"
        elif "yll" in cl and "yld" not in cl:
            col_map[c] = "ylls_n"
        elif "yld" in cl:
            col_map[c] = "ylds_n"
        elif "death" in cl:
            col_map[c] = "deaths_n"
    pivot = pivot.rename(columns=col_map)

    # Compute decomposition metrics
    for col in ["dalys_n", "ylls_n", "ylds_n"]:
        if col not in pivot.columns:
            pivot[col] = np.nan

    pivot["yll_fraction"] = np.where(
        pivot["dalys_n"] > 0, pivot["ylls_n"] / pivot["dalys_n"], np.nan
    )
    pivot["yld_fraction"] = np.where(
        pivot["dalys_n"] > 0, pivot["ylds_n"] / pivot["dalys_n"], np.nan
    )
    pivot["yld_yll_ratio"] = np.where(
        pivot["ylls_n"] > 0, pivot["ylds_n"] / pivot["ylls_n"], np.nan
    )

    log.info(f"Decomposition computed: {len(pivot):,} rows")

    # Save
    pivot.to_csv(OUTPUTS / "decomposition.csv", index=False)
    log.info(f"Output: {OUTPUTS / 'decomposition.csv'}")

    try:
        with pd.ExcelWriter(str(TABLES / "Table2_decomposition.xlsx"), engine="openpyxl") as w:
            pivot.to_excel(w, sheet_name="Decomposition", index=False)
        log.info(f"Table 2: {TABLES / 'Table2_decomposition.xlsx'}")
    except Exception as e:
        log.warning(f"Excel write failed: {e}")

    # Summary stats
    all_inj = pivot[pivot["cause_group"] == "all_injuries"]
    if not all_inj.empty and "yld_fraction" in all_inj.columns:
        med_yld = all_inj["yld_fraction"].median()
        log.info(f"Median YLD fraction (all injuries, states): {med_yld:.3f}")

    log.info("=== Decomposition Analysis: Complete ===")
    return pivot


if __name__ == "__main__":
    run()
